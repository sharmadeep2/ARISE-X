"""Per-dimension statistical comparison of baseline vs. candidate reliability evidence.

This module implements the corrected Step 5.1 statistical design (see planning
log decisions DD-08, DD-10, DD-11 and research Scenario 5): the *task* is the
analysis unit, tests are matched to each dimension's data type, exact McNemar
is restricted to one independent binary pair per task, sample size is derived
from a power analysis rather than an arbitrary fixture count, Holm-Bonferroni
corrects for testing multiple dimensions at once, cluster-aware bootstrap
resampling accounts for correlated task-family evidence, and downstream-impact
priority is reported as a signal separate from (and never suppressing) the
drift classification.

``arise_x.drift.detector`` remains the unchanged legacy per-event severity
facade; ``detector.compare_baseline_to_candidate`` is a thin wrapper that
delegates to :func:`compare_baseline_to_candidate` below.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from scipy import stats

from arise_x.telemetry.trajectory import Trajectory
from arise_x.trust.vector import NORMALIZATION_VERSION, ReliabilityVector, VectorDimension

DEFAULT_ALPHA = 0.02
DEFAULT_TARGET_POWER = 0.80
DEFAULT_BOOTSTRAP_ITERATIONS = 500
DEFAULT_PERMUTATION_RESAMPLES = 999
DEFAULT_RANDOM_SEED = 0
_MINIMUM_IMPACT_SAMPLE = 10


class SamplingDesignError(ValueError):
    """Raised when baseline/candidate evidence cannot be validly paired or compared."""


class SamplingDesign(StrEnum):
    """Whether evidence for a comparison is paired (matched by task) or independent."""

    PAIRED = "paired"
    INDEPENDENT = "independent"


class DriftTestMethod(StrEnum):
    """Statistical test actually selected and executed for a dimension."""

    WILCOXON_SIGNED_RANK = "wilcoxon_signed_rank"
    PAIRED_PERMUTATION = "paired_permutation"
    PAIRED_CLUSTER_PERMUTATION = "paired_cluster_permutation"
    EXACT_MCNEMAR = "exact_mcnemar"


@dataclass(frozen=True)
class RunObservation:
    """One executed episode's trajectory and reliability-vector evidence."""

    trajectory: Trajectory
    vector: ReliabilityVector


@dataclass(frozen=True)
class DimensionTestConfig:
    """Per-dimension configuration required to run and gate a statistical test.

    Args:
        minimum_detectable_effect: Smallest true mean paired difference this
            dimension's test must be powered to detect.
        tolerance: Practical-effect-size threshold; a dimension is only
            "material drift" when its effect size *also* exceeds this, even
            if statistically significant (Kayenta-style tolerance band).
        is_binary: Whether this dimension's per-execution values are raw
            binary (0.0/1.0) outcomes. Only relevant for selecting exact
            McNemar; binary dimensions with repeated executions per task are
            always aggregated to rates and analyzed like continuous data.
    """

    minimum_detectable_effect: float
    tolerance: float
    is_binary: bool = False
    pilot_standard_deviation: float | None = None
    minimum_cluster_count: int = 2

    def __post_init__(self) -> None:
        if not math.isfinite(self.minimum_detectable_effect) or self.minimum_detectable_effect <= 0:
            msg = (
                "minimum_detectable_effect must be positive, got "
                f"{self.minimum_detectable_effect}"
            )
            raise ValueError(msg)
        if not math.isfinite(self.tolerance) or self.tolerance < 0:
            msg = f"tolerance must be non-negative, got {self.tolerance}"
            raise ValueError(msg)
        if self.pilot_standard_deviation is not None and (
            not math.isfinite(self.pilot_standard_deviation)
            or self.pilot_standard_deviation <= 0
        ):
            raise ValueError("pilot_standard_deviation must be positive when supplied")
        if self.minimum_cluster_count < 2:
            raise ValueError("minimum_cluster_count must be at least 2")


@dataclass(frozen=True)
class DownstreamImpactPriority:
    """Separate signal: historical association between a dimension and negative outcomes.

    This is reported alongside, but must never suppress or downgrade, a
    dimension's `material_drift` classification -- especially for the
    critical `goal_success` and `safety` dimensions. Callers (including any
    future release-gate policy) must not use `insufficient_evidence` or a
    low `confidence` here to weaken a critical dimension's verdict.
    """

    dimension: VectorDimension
    association: float | None
    confidence: float | None
    sample_count: int
    insufficient_evidence: bool


@dataclass(frozen=True)
class DimensionDriftResult:
    """Full statistical comparison outcome for one reliability-vector dimension."""

    dimension: VectorDimension
    sampling_design: SamplingDesign
    test_method: DriftTestMethod | None
    paired_task_count: int
    effective_cluster_count: int
    coverage: float
    confidence_level: float
    target_power: float
    achieved_power: float | None
    required_observations: int
    power_analysis_unit: str
    cluster_sufficient: bool
    raw_p_value: float | None
    corrected_p_value: float | None
    significant: bool
    effect_size: float | None
    confidence_interval: tuple[float, float] | None
    tolerance_threshold: float
    material_drift: bool
    has_sufficient_data: bool
    insufficient_power: bool
    downstream_impact: DownstreamImpactPriority


@dataclass(frozen=True)
class DriftComparisonResult:
    """All per-dimension results for one baseline-vs-candidate comparison."""

    baseline_run_id: str
    candidate_run_id: str
    compared_at: str
    dimension_results: tuple[DimensionDriftResult, ...]

    def dimension(self, name: VectorDimension) -> DimensionDriftResult:
        """Look up a dimension result by name.

        Raises:
            KeyError: If `name` was not part of this comparison.
        """
        for result in self.dimension_results:
            if result.dimension == name:
                return result
        msg = f"Dimension {name} was not part of this comparison"
        raise KeyError(msg)


@dataclass(frozen=True)
class _PendingDimensionOutcome:
    """Intermediate per-dimension outcome before multiple-test correction is applied."""

    dimension: VectorDimension
    sampling_design: SamplingDesign
    test_method: DriftTestMethod | None
    paired_task_count: int
    effective_cluster_count: int
    coverage: float
    confidence_level: float
    target_power: float
    achieved_power: float | None
    required_observations: int
    power_analysis_unit: str
    cluster_sufficient: bool
    raw_p_value: float | None
    effect_size: float | None
    confidence_interval: tuple[float, float] | None
    tolerance_threshold: float
    has_sufficient_data: bool
    insufficient_power: bool
    downstream_impact: DownstreamImpactPriority


def holm_bonferroni_correction(p_values: Sequence[float], alpha: float) -> tuple[float, ...]:
    """Compute Holm-Bonferroni step-down adjusted p-values.

    Standard Holm (1979) step-down procedure: sort p-values ascending, scale
    the i-th smallest (0-indexed) by `(m - i)`, enforce monotonicity with a
    running maximum, and cap each adjusted value at 1.0. A hypothesis is
    significant when its adjusted p-value is `<= alpha`. Order of the
    returned tuple matches the order of `p_values`.

    Args:
        p_values: Raw two-sided p-values for every dimension tested together.
        alpha: Family-wise significance level used only to document intent;
            the correction itself does not depend on `alpha`.

    Returns:
        Adjusted p-values in the same order as `p_values`.
    """

    del alpha  # Documented for intent; Holm's adjustment itself is alpha-independent.
    count = len(p_values)
    order = sorted(range(count), key=lambda i: p_values[i])
    adjusted = [0.0] * count
    running_max = 0.0
    for rank, index in enumerate(order):
        candidate = (count - rank) * p_values[index]
        running_max = max(running_max, min(candidate, 1.0))
        adjusted[index] = running_max
    return tuple(adjusted)


def required_sample_size(
    minimum_detectable_effect: float,
    std_estimate: float,
    *,
    alpha: float = DEFAULT_ALPHA,
    power: float = DEFAULT_TARGET_POWER,
) -> int:
    """Approximate the number of paired tasks required to detect `minimum_detectable_effect`.

    Uses the standard normal-approximation sample-size formula for a paired
    (one-sample) difference test::

        n = ((z_{alpha/2} + z_{power})^2 * sigma_d^2) / delta^2

    where `sigma_d` is the paired-difference standard deviation and `delta`
    is the minimum detectable effect. This is the textbook paired t-test
    formula; it is used here as a Wilcoxon-signed-rank-equivalent estimate
    because the asymptotic relative efficiency of Wilcoxon signed-rank vs.
    the paired t-test is ~0.955 under normal differences (Pitman ARE), so
    the t-test formula is a close, slightly conservative approximation.

    Args:
        minimum_detectable_effect: Smallest true mean difference to detect.
        std_estimate: Pilot/baseline estimate of the paired-difference
            standard deviation.
        alpha: Two-sided family-wise significance level (default 0.02).
        power: Target statistical power (default 0.80).

    Returns:
        The required paired-task sample size, at least 1.
    """

    if std_estimate <= 0:
        return 1
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = stats.norm.ppf(power)
    n = ((z_alpha + z_power) ** 2) * (std_estimate**2) / (minimum_detectable_effect**2)
    return max(1, math.ceil(n))


def achieved_power(
    paired_task_count: int,
    minimum_detectable_effect: float,
    std_estimate: float,
    *,
    alpha: float = DEFAULT_ALPHA,
) -> float:
    """Estimate the statistical power actually achieved with the available sample.

    Inverts the sample-size formula documented in :func:`required_sample_size`
    to estimate power for a given `paired_task_count`.

    Returns:
        Estimated power in `[0.0, 1.0]`.
    """

    if paired_task_count <= 0 or std_estimate <= 0:
        return 1.0 if std_estimate <= 0 and paired_task_count > 0 else 0.0
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z = math.sqrt(paired_task_count) * minimum_detectable_effect / std_estimate - z_alpha
    return float(stats.norm.cdf(z))


def compute_downstream_impact_priority(
    dimension: VectorDimension,
    baseline: Sequence[RunObservation],
    *,
    minimum_sample: int = _MINIMUM_IMPACT_SAMPLE,
) -> DownstreamImpactPriority:
    """Estimate a dimension's historical association with negative outcomes.

    This is a separate, MVP-level signal (a point-biserial correlation
    between per-execution dimension value and a negative-outcome indicator
    over the baseline sample). It is reported for prioritization only and
    must never be used to suppress or downgrade a drift classification --
    critical dimensions (`goal_success`, `safety`) in particular must retain
    their statistical/practical classification regardless of impact
    confidence.

    Args:
        dimension: The reliability-vector dimension to evaluate.
        baseline: Baseline evidence to estimate the association from.
        minimum_sample: Minimum number of available observations (with both
            outcome classes and non-degenerate dimension values) required
            before reporting an estimate instead of "insufficient evidence".
    """

    values: list[float] = []
    outcomes: list[float] = []
    for observation in baseline:
        score = observation.vector.dimension(dimension)
        if not score.available:
            continue
        values.append(score.value)
        outcomes.append(1.0 if _has_negative_outcome(observation.trajectory) else 0.0)

    sample_count = len(values)
    if sample_count < minimum_sample or len(set(outcomes)) < 2 or len(set(values)) < 2:
        return DownstreamImpactPriority(
            dimension=dimension,
            association=None,
            confidence=None,
            sample_count=sample_count,
            insufficient_evidence=True,
        )

    correlation, p_value = stats.pointbiserialr(outcomes, values)
    return DownstreamImpactPriority(
        dimension=dimension,
        association=float(correlation),
        confidence=float(max(0.0, 1.0 - p_value)),
        sample_count=sample_count,
        insufficient_evidence=False,
    )


def compare_dimension(
    dimension: VectorDimension,
    baseline: Sequence[RunObservation],
    candidate: Sequence[RunObservation],
    config: DimensionTestConfig,
    *,
    alpha: float = DEFAULT_ALPHA,
    target_power: float = DEFAULT_TARGET_POWER,
    bootstrap_iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
    permutation_resamples: int = DEFAULT_PERMUTATION_RESAMPLES,
    random_seed: int = DEFAULT_RANDOM_SEED,
    sampling_design: SamplingDesign = SamplingDesign.PAIRED,
) -> DimensionDriftResult:
    """Compare one dimension between baseline and candidate evidence.

    Convenience single-dimension entry point; Holm-Bonferroni correction with
    a family of one dimension is a no-op (equal to the raw p-value capped at
    1.0). Use :func:`compare_baseline_to_candidate` to correct jointly across
    multiple dimensions.
    """

    result = compare_baseline_to_candidate(
        baseline_run_id="",
        candidate_run_id="",
        baseline=baseline,
        candidate=candidate,
        dimension_configs={dimension: config},
        alpha=alpha,
        target_power=target_power,
        bootstrap_iterations=bootstrap_iterations,
        permutation_resamples=permutation_resamples,
        random_seed=random_seed,
        sampling_design=sampling_design,
    )
    return result.dimension_results[0]


def compare_baseline_to_candidate(
    baseline_run_id: str,
    candidate_run_id: str,
    baseline: Sequence[RunObservation],
    candidate: Sequence[RunObservation],
    dimension_configs: Mapping[VectorDimension, DimensionTestConfig],
    *,
    alpha: float = DEFAULT_ALPHA,
    target_power: float = DEFAULT_TARGET_POWER,
    bootstrap_iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
    permutation_resamples: int = DEFAULT_PERMUTATION_RESAMPLES,
    random_seed: int = DEFAULT_RANDOM_SEED,
    sampling_design: SamplingDesign = SamplingDesign.PAIRED,
    compared_at: str | None = None,
) -> DriftComparisonResult:
    """Compare baseline and candidate evidence across every configured dimension.

    Applies Holm-Bonferroni multiple-test correction jointly across all
    dimensions in `dimension_configs` before finalizing each dimension's
    `significant`/`material_drift` verdict.

    Raises:
        SamplingDesignError: If `sampling_design` is not `PAIRED`, or if
            baseline and candidate do not reference the same task IDs for
            some dimension.
    """

    if not 0.0 < alpha < 1.0 or not 0.0 < target_power <= 1.0:
        raise ValueError("alpha must be in (0, 1) and target_power in (0, 1].")
    if bootstrap_iterations < 1 or permutation_resamples < 1:
        raise ValueError("Bootstrap iterations and permutation resamples must be positive.")
    if sampling_design is not SamplingDesign.PAIRED:
        raise SamplingDesignError("Only paired-sample diagnostics are supported.")
    validate_paired_observations(baseline, candidate)

    pending: dict[VectorDimension, _PendingDimensionOutcome] = {
        dimension: _analyze_dimension(
            dimension,
            baseline,
            candidate,
            config,
            alpha=alpha,
            target_power=target_power,
            bootstrap_iterations=bootstrap_iterations,
            permutation_resamples=permutation_resamples,
            random_seed=random_seed,
            sampling_design=sampling_design,
        )
        for dimension, config in dimension_configs.items()
    }

    ordered_dimensions = list(dimension_configs)
    correction_targets = [d for d in ordered_dimensions if pending[d].raw_p_value is not None]
    raw_p_values = [pending[d].raw_p_value for d in correction_targets]
    corrected = (
        holm_bonferroni_correction(raw_p_values, alpha) if raw_p_values else ()  # type: ignore[arg-type]
    )
    corrected_by_dimension = dict(zip(correction_targets, corrected, strict=True))

    dimension_results = tuple(
        _finalize(pending[dimension], corrected_by_dimension.get(dimension), alpha)
        for dimension in ordered_dimensions
    )
    return DriftComparisonResult(
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
        compared_at=compared_at or datetime.now(UTC).isoformat(),
        dimension_results=dimension_results,
    )


def validate_paired_observations(
    baseline: Sequence[RunObservation], candidate: Sequence[RunObservation]
) -> None:
    """Reject incompatible or duplicate pairs without requiring a release partition.

    Repeat IDs carry episode seed identity in the current trajectory contract.
    Run-level numeric seeds are checked separately at release transport boundaries.
    Development-only matched evidence remains usable for standalone diagnostics.
    """
    identity_fields = (
        "family", "cluster_id", "suite_id", "suite_version", "suite_partition",
        "scenario_name", "scenario_version",
    )
    indexed = []
    contexts = set()
    task_contexts: dict[str, tuple[object, ...]] = {}
    for observations in (baseline, candidate):
        pairs: dict[tuple[str, str], tuple[object, ...]] = {}
        for observation in observations:
            trajectory, vector = observation.trajectory, observation.vector
            key = (trajectory.task_id, trajectory.repeat_id)
            if key in pairs:
                raise SamplingDesignError("Duplicate task/repeat evidence is not independent.")
            identity = tuple(getattr(trajectory, name) for name in identity_fields)
            pairs[key] = identity
            previous = task_contexts.setdefault(trajectory.task_id, identity)
            if previous != identity:
                raise SamplingDesignError(
                    "Paired task family/cluster/suite/scenario identity differs."
                )
            contexts.add((trajectory.suite_id, trajectory.suite_version,
                          trajectory.suite_partition, trajectory.scenario_name,
                          trajectory.scenario_version))
            if vector.schema_version != NORMALIZATION_VERSION:
                raise SamplingDesignError("Unsupported reliability vector schema version.")
            if any(vector.dimension(dim).normalization_version != NORMALIZATION_VERSION
                   for dim in VectorDimension):
                raise SamplingDesignError("Unsupported reliability normalization version.")
        indexed.append(pairs)
    if indexed[0] != indexed[1]:
        raise SamplingDesignError("Baseline/candidate task/repeat pairs and identity must match.")
    if len(contexts) > 1:
        raise SamplingDesignError("Mixed suite/partition/scenario evidence is not comparable.")


def _finalize(
    pending: _PendingDimensionOutcome, corrected_p_value: float | None, alpha: float
) -> DimensionDriftResult:
    significant = corrected_p_value is not None and corrected_p_value <= alpha
    material_drift = (
        pending.has_sufficient_data
        and significant
        and pending.effect_size is not None
        and abs(pending.effect_size) >= pending.tolerance_threshold
    )
    return DimensionDriftResult(
        dimension=pending.dimension,
        sampling_design=pending.sampling_design,
        test_method=pending.test_method,
        paired_task_count=pending.paired_task_count,
        effective_cluster_count=pending.effective_cluster_count,
        coverage=pending.coverage,
        confidence_level=pending.confidence_level,
        target_power=pending.target_power,
        achieved_power=pending.achieved_power,
        required_observations=pending.required_observations,
        power_analysis_unit=pending.power_analysis_unit,
        cluster_sufficient=pending.cluster_sufficient,
        raw_p_value=pending.raw_p_value,
        corrected_p_value=corrected_p_value,
        significant=significant,
        effect_size=pending.effect_size,
        confidence_interval=pending.confidence_interval,
        tolerance_threshold=pending.tolerance_threshold,
        material_drift=material_drift,
        has_sufficient_data=pending.has_sufficient_data,
        insufficient_power=pending.insufficient_power,
        downstream_impact=pending.downstream_impact,
    )


def _analyze_dimension(
    dimension: VectorDimension,
    baseline: Sequence[RunObservation],
    candidate: Sequence[RunObservation],
    config: DimensionTestConfig,
    *,
    alpha: float,
    target_power: float,
    bootstrap_iterations: int,
    permutation_resamples: int,
    random_seed: int,
    sampling_design: SamplingDesign,
) -> _PendingDimensionOutcome:
    if sampling_design is not SamplingDesign.PAIRED:
        msg = (
            "drift.statistics only implements the paired-sample analysis path; "
            f"got sampling_design={sampling_design!r} for dimension {dimension}"
        )
        raise SamplingDesignError(msg)

    baseline_task_ids = {observation.trajectory.task_id for observation in baseline}
    candidate_task_ids = {observation.trajectory.task_id for observation in candidate}
    if baseline_task_ids != candidate_task_ids:
        missing_in_candidate = sorted(baseline_task_ids - candidate_task_ids)
        missing_in_baseline = sorted(candidate_task_ids - baseline_task_ids)
        msg = (
            f"Baseline and candidate must reference the same held-out task IDs for {dimension}. "
            f"Missing in candidate: {missing_in_candidate}; missing in baseline: "
            f"{missing_in_baseline}"
        )
        raise SamplingDesignError(msg)

    downstream_impact = compute_downstream_impact_priority(dimension, baseline)

    paired_observations = zip(baseline, candidate, strict=True)
    complete_pair_count = sum(
        1
        for baseline_observation, candidate_observation in paired_observations
        if baseline_observation.vector.dimension(dimension).available
        and baseline_observation.vector.dimension(dimension).evidence_count > 0
        and candidate_observation.vector.dimension(dimension).available
        and candidate_observation.vector.dimension(dimension).evidence_count > 0
    )
    expected_pair_count = len(baseline)
    coverage = complete_pair_count / expected_pair_count if expected_pair_count else 0.0
    complete_coverage = coverage == 1.0
    if config.is_binary and any(
        observation.vector.dimension(dimension).available
        and observation.vector.dimension(dimension).value not in (0.0, 1.0)
        for observation in (*baseline, *candidate)
    ):
        raise SamplingDesignError("Observed binary values must be exactly 0 or 1, not rates.")

    baseline_values = _group_task_values(baseline, dimension)
    candidate_values = _group_task_values(candidate, dimension)
    task_clusters = _task_clusters(baseline)

    paired_baseline: list[float] = []
    paired_candidate: list[float] = []
    clusters: list[str] = []
    repeats_present = False
    for task_id in sorted(baseline_task_ids):
        base_values = baseline_values.get(task_id, [])
        cand_values = candidate_values.get(task_id, [])
        if not base_values or not cand_values:
            continue
        if len(base_values) > 1 or len(cand_values) > 1:
            repeats_present = True
        paired_baseline.append(sum(base_values) / len(base_values))
        paired_candidate.append(sum(cand_values) / len(cand_values))
        clusters.append(task_clusters[task_id])

    paired_task_count = len(paired_baseline)
    if paired_task_count == 0:
        return _PendingDimensionOutcome(
            dimension=dimension,
            sampling_design=SamplingDesign.PAIRED,
            test_method=None,
            paired_task_count=0,
            effective_cluster_count=0,
            coverage=coverage,
            confidence_level=1.0 - alpha,
            target_power=target_power,
            achieved_power=None,
            required_observations=1,
            power_analysis_unit="task",
            cluster_sufficient=False,
            raw_p_value=None,
            effect_size=None,
            confidence_interval=None,
            tolerance_threshold=config.tolerance,
            has_sufficient_data=False,
            insufficient_power=True,
            downstream_impact=downstream_impact,
        )

    diffs = [
        cand - base for base, cand in zip(paired_baseline, paired_candidate, strict=True)
    ]

    unique_clusters = sorted(set(clusters))
    cluster_sizes = {cluster: clusters.count(cluster) for cluster in unique_clusters}
    correlated_clusters = any(size > 1 for size in cluster_sizes.values())
    cluster_sufficient = len(unique_clusters) >= config.minimum_cluster_count
    if correlated_clusters and cluster_sufficient:
        test_method = DriftTestMethod.PAIRED_CLUSTER_PERMUTATION
        raw_p_value = _paired_cluster_permutation_p_value(
            diffs,
            clusters,
            n_resamples=permutation_resamples,
            random_seed=random_seed,
        )
    elif config.is_binary and not repeats_present and not correlated_clusters:
        test_method = DriftTestMethod.EXACT_MCNEMAR
        raw_p_value = _exact_mcnemar_p_value(paired_baseline, paired_candidate)
    else:
        test_method, raw_p_value = _wilcoxon_or_permutation(
            paired_baseline,
            paired_candidate,
            diffs,
            permutation_resamples=permutation_resamples,
            random_seed=random_seed,
        )

    effect_size = sum(diffs) / paired_task_count

    use_cluster_bootstrap = cluster_sufficient and correlated_clusters
    if use_cluster_bootstrap:
        confidence_interval = _cluster_bootstrap_ci(
            diffs, clusters, alpha=alpha, iterations=bootstrap_iterations, random_seed=random_seed
        )
    else:
        confidence_interval = _naive_bootstrap_ci(
            diffs, alpha=alpha, iterations=bootstrap_iterations, random_seed=random_seed
        )

    if correlated_clusters:
        power_values = _cluster_means(diffs, clusters)
        power_analysis_unit = "cluster"
    else:
        power_values = diffs
        power_analysis_unit = "task"
    observed_std = _sample_std(power_values)
    power_std = config.pilot_standard_deviation or max(
        observed_std, config.minimum_detectable_effect
    )
    required_observations = required_sample_size(
        config.minimum_detectable_effect,
        power_std,
        alpha=alpha,
        power=target_power,
    )
    power_now = achieved_power(
        len(power_values), config.minimum_detectable_effect, power_std, alpha=alpha
    )

    return _PendingDimensionOutcome(
        dimension=dimension,
        sampling_design=SamplingDesign.PAIRED,
        test_method=test_method,
        paired_task_count=paired_task_count,
        effective_cluster_count=len(unique_clusters),
        coverage=coverage,
        confidence_level=1.0 - alpha,
        target_power=target_power,
        achieved_power=power_now,
        required_observations=required_observations,
        power_analysis_unit=power_analysis_unit,
        cluster_sufficient=cluster_sufficient,
        raw_p_value=raw_p_value,
        effect_size=effect_size,
        confidence_interval=confidence_interval,
        tolerance_threshold=config.tolerance,
        has_sufficient_data=complete_coverage,
        insufficient_power=power_now < target_power,
        downstream_impact=downstream_impact,
    )


def _group_task_values(
    observations: Sequence[RunObservation], dimension: VectorDimension
) -> dict[str, list[float]]:
    grouped: dict[str, list[float]] = {}
    for observation in observations:
        score = observation.vector.dimension(dimension)
        if not score.available or score.evidence_count <= 0:
            continue
        grouped.setdefault(observation.trajectory.task_id, []).append(score.value)
    return grouped


def _task_clusters(observations: Sequence[RunObservation]) -> dict[str, str]:
    clusters: dict[str, str] = {}
    for observation in observations:
        trajectory = observation.trajectory
        clusters.setdefault(trajectory.task_id, f"{trajectory.family}/{trajectory.cluster_id}")
    return clusters


def _has_negative_outcome(trajectory: Trajectory) -> bool:
    goal_failed = not trajectory.outcome.goal_achieved
    safety_violation = trajectory.policy_violation_count > 0
    unrecovered_fault = any(
        step.fault is not None and step.fault.verified and not step.recovered
        for step in trajectory.steps
    )
    return goal_failed or safety_violation or unrecovered_fault


def _exact_mcnemar_p_value(
    baseline_values: Sequence[float], candidate_values: Sequence[float]
) -> float:
    """Exact McNemar test: binomial test on discordant baseline/candidate pairs."""

    baseline_only = 0  # baseline=1, candidate=0
    candidate_only = 0  # baseline=0, candidate=1
    for base, cand in zip(baseline_values, candidate_values, strict=True):
        if base not in (0.0, 1.0) or cand not in (0.0, 1.0):
            raise SamplingDesignError("McNemar requires observed binary values exactly 0 or 1.")
        base_positive = base == 1.0
        cand_positive = cand == 1.0
        if base_positive and not cand_positive:
            baseline_only += 1
        elif not base_positive and cand_positive:
            candidate_only += 1

    discordant = baseline_only + candidate_only
    if discordant == 0:
        return 1.0
    result = stats.binomtest(
        k=min(baseline_only, candidate_only), n=discordant, p=0.5, alternative="two-sided"
    )
    return float(result.pvalue)


def _wilcoxon_or_permutation(
    paired_baseline: Sequence[float],
    paired_candidate: Sequence[float],
    diffs: Sequence[float],
    *,
    permutation_resamples: int,
    random_seed: int,
) -> tuple[DriftTestMethod, float]:
    if all(abs(diff) < 1e-12 for diff in diffs):
        return DriftTestMethod.WILCOXON_SIGNED_RANK, 1.0
    try:
        _, p_value = stats.wilcoxon(diffs, zero_method="wilcox", mode="auto")
        return DriftTestMethod.WILCOXON_SIGNED_RANK, float(p_value)
    except ValueError:
        # Wilcoxon's assumptions are violated (e.g. it cannot handle the
        # remaining zero-difference structure for this sample); fall back to
        # a paired sign-flip permutation test, which has no such restriction.
        p_value = _paired_permutation_p_value(
            paired_baseline,
            paired_candidate,
            n_resamples=permutation_resamples,
            random_seed=random_seed,
        )
        return DriftTestMethod.PAIRED_PERMUTATION, p_value


def _paired_permutation_p_value(
    paired_baseline: Sequence[float],
    paired_candidate: Sequence[float],
    *,
    n_resamples: int,
    random_seed: int,
) -> float:
    def statistic(candidate_sample: Sequence[float], baseline_sample: Sequence[float]) -> float:
        return sum(
            c - b for c, b in zip(candidate_sample, baseline_sample, strict=True)
        ) / len(candidate_sample)

    result = stats.permutation_test(
        (paired_candidate, paired_baseline),
        statistic=statistic,
        permutation_type="samples",
        vectorized=False,
        n_resamples=n_resamples,
        alternative="two-sided",
        random_state=random_seed,
    )
    return float(result.pvalue)


def _cluster_means(diffs: Sequence[float], clusters: Sequence[str]) -> list[float]:
    """Aggregate paired task differences to independent cluster analysis units."""

    grouped: dict[str, list[float]] = {}
    for diff, cluster in zip(diffs, clusters, strict=True):
        grouped.setdefault(cluster, []).append(diff)
    return [sum(grouped[cluster]) / len(grouped[cluster]) for cluster in sorted(grouped)]


def _paired_cluster_permutation_p_value(
    diffs: Sequence[float],
    clusters: Sequence[str],
    *,
    n_resamples: int,
    random_seed: int,
) -> float:
    """Two-sided sign-flip permutation test over independent cluster means."""

    cluster_diffs = _cluster_means(diffs, clusters)
    observed = abs(sum(cluster_diffs) / len(cluster_diffs))
    if observed < 1e-12:
        return 1.0

    permutation_count = 2 ** len(cluster_diffs)
    if permutation_count <= n_resamples:
        sign_patterns = (
            tuple(
                1.0 if mask & (1 << index) else -1.0
                for index in range(len(cluster_diffs))
            )
            for mask in range(permutation_count)
        )
        permuted = [
            abs(
                sum(
                    sign * diff
                    for sign, diff in zip(signs, cluster_diffs, strict=True)
                )
                / len(cluster_diffs)
            )
            for signs in sign_patterns
        ]
        return sum(value >= observed - 1e-12 for value in permuted) / len(permuted)

    rng = random.Random(random_seed)
    extreme_count = 0
    for _ in range(n_resamples):
        permuted_mean = sum(
            rng.choice((-1.0, 1.0)) * diff for diff in cluster_diffs
        ) / len(cluster_diffs)
        extreme_count += abs(permuted_mean) >= observed - 1e-12
    return (extreme_count + 1) / (n_resamples + 1)


def _sample_std(values: Sequence[float]) -> float:
    count = len(values)
    if count < 2:
        return 0.0
    mean_value = sum(values) / count
    variance = sum((value - mean_value) ** 2 for value in values) / (count - 1)
    return math.sqrt(variance)


def _naive_bootstrap_ci(
    diffs: Sequence[float], *, alpha: float, iterations: int, random_seed: int
) -> tuple[float, float]:
    """Per-task bootstrap CI treating every paired task as independent."""

    rng = random.Random(random_seed)
    count = len(diffs)
    means = [sum(rng.choices(diffs, k=count)) / count for _ in range(iterations)]
    return _percentile_interval(means, alpha)


def _cluster_bootstrap_ci(
    diffs: Sequence[float], clusters: Sequence[str], *, alpha: float, iterations: int,
    random_seed: int,
) -> tuple[float, float]:
    """Paired cluster bootstrap CI: resample whole task-family clusters with replacement."""

    rng = random.Random(random_seed)
    diffs_by_cluster: dict[str, list[float]] = {}
    for diff, cluster in zip(diffs, clusters, strict=True):
        diffs_by_cluster.setdefault(cluster, []).append(diff)
    unique_clusters = sorted(diffs_by_cluster)

    means: list[float] = []
    for _ in range(iterations):
        sampled_clusters = rng.choices(unique_clusters, k=len(unique_clusters))
        pooled: list[float] = []
        for cluster in sampled_clusters:
            pooled.extend(diffs_by_cluster[cluster])
        means.append(sum(pooled) / len(pooled))
    return _percentile_interval(means, alpha)


def _percentile_interval(values: Sequence[float], alpha: float) -> tuple[float, float]:
    ordered = sorted(values)
    count = len(ordered)
    lower_index = max(0, min(count - 1, int((alpha / 2) * count)))
    upper_index = max(0, min(count - 1, int((1 - alpha / 2) * count) - 1))
    if upper_index < lower_index:
        upper_index = lower_index
    return (ordered[lower_index], ordered[upper_index])
