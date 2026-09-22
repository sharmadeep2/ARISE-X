"""Unit tests for per-dimension statistical baseline-vs-candidate drift comparison.

These cover the corrected Step 5.1 statistical design (task-level pairing,
matched test selection, exact McNemar restricted to one binary pair per task,
power-derived sample sizing, Holm-Bonferroni correction, cluster-aware
bootstrap uncertainty, and separate downstream-impact priority). They are
distinct from the legacy per-event severity heuristic covered elsewhere.
"""

from __future__ import annotations

import random
from dataclasses import replace

import pytest

from arise_x.drift import detector
from arise_x.drift import statistics as drift_statistics
from arise_x.drift.statistics import (
    DimensionTestConfig,
    DriftTestMethod,
    RunObservation,
    SamplingDesign,
    SamplingDesignError,
    compare_baseline_to_candidate,
    compare_dimension,
    holm_bonferroni_correction,
)
from arise_x.telemetry.trajectory import Outcome, Step, Trajectory
from arise_x.trust.vector import DimensionScore, ReliabilityVector, VectorDimension


def _trajectory(
    task_id: str,
    cluster_id: str,
    *,
    repeat_id: str = "seed-0",
    goal_achieved: bool = True,
    policy_violations: int = 0,
) -> Trajectory:
    step = Step(index=0, action="decide", state_transition="idle->done")
    return Trajectory(
        run_id=f"run-{task_id}-{repeat_id}",
        task_id=task_id,
        family="procurement",
        cluster_id=cluster_id,
        suite_id="suite-1",
        suite_version=1,
        suite_partition="held_out",
        repeat_id=repeat_id,
        scenario_name="procurement",
        scenario_version=1,
        agent_id="agent-1",
        agent_version="v1",
        steps=(step,),
        outcome=Outcome(goal_achieved=goal_achieved, label="done" if goal_achieved else "failed"),
        policy_violation_count=policy_violations,
    )


def _vector_with(values: dict[VectorDimension, float]) -> ReliabilityVector:
    scores = {
        dim.value: DimensionScore(
            dimension=dim, value=values.get(dim, 0.5), available=True, evidence_count=1
        )
        for dim in VectorDimension
    }
    return ReliabilityVector(**scores)


def _observation_with(
    task_id: str,
    cluster_id: str,
    values: dict[VectorDimension, float],
    *,
    repeat_id: str = "seed-0",
    goal_achieved: bool = True,
    policy_violations: int = 0,
) -> RunObservation:
    trajectory = _trajectory(
        task_id,
        cluster_id,
        repeat_id=repeat_id,
        goal_achieved=goal_achieved,
        policy_violations=policy_violations,
    )
    return RunObservation(trajectory=trajectory, vector=_vector_with(values))


def _observation(
    task_id: str,
    cluster_id: str,
    dimension: VectorDimension,
    value: float,
    *,
    repeat_id: str = "seed-0",
    available: bool = True,
    goal_achieved: bool = True,
    policy_violations: int = 0,
) -> RunObservation:
    trajectory = _trajectory(
        task_id,
        cluster_id,
        repeat_id=repeat_id,
        goal_achieved=goal_achieved,
        policy_violations=policy_violations,
    )
    scores = {
        dim.value: DimensionScore(dimension=dim, value=0.5, available=True, evidence_count=1)
        for dim in VectorDimension
    }
    scores[dimension.value] = DimensionScore(
        dimension=dimension, value=value, available=available, evidence_count=1
    )
    return RunObservation(trajectory=trajectory, vector=ReliabilityVector(**scores))


def test_given_identical_baseline_and_candidate_when_compare_dimension_then_no_material_drift() -> (
    None
):
    # Arrange
    dimension = VectorDimension.EFFICIENCY
    baseline = [_observation(f"task-{i}", "cluster-a", dimension, 0.7) for i in range(10)]
    candidate = [_observation(f"task-{i}", "cluster-a", dimension, 0.7) for i in range(10)]
    config = DimensionTestConfig(minimum_detectable_effect=0.05, tolerance=0.05)

    # Act
    result = compare_dimension(dimension, baseline, candidate, config)

    # Assert
    assert result.material_drift is False
    assert result.raw_p_value == pytest.approx(1.0)
    assert result.has_sufficient_data is True


def test_given_significant_but_trivial_effect_when_compare_dimension_then_no_material_drift() -> (
    None
):
    # Arrange
    dimension = VectorDimension.EFFICIENCY
    rng = random.Random(1)
    baseline = []
    candidate = []
    for i in range(60):
        candidate_value = 0.700 + 0.004 + rng.uniform(-0.0005, 0.0005)
        baseline.append(_observation(f"task-{i}", "cluster-a", dimension, 0.700))
        candidate.append(_observation(f"task-{i}", "cluster-a", dimension, candidate_value))
    config = DimensionTestConfig(minimum_detectable_effect=0.05, tolerance=0.03)

    # Act
    result = compare_dimension(dimension, baseline, candidate, config)

    # Assert
    assert result.significant is True
    assert result.material_drift is False


def test_given_too_few_samples_when_compare_dimension_then_insufficient_power() -> None:
    # Arrange
    dimension = VectorDimension.EFFICIENCY
    diffs = [0.28, 0.32, 0.29, 0.31]
    baseline = [_observation(f"task-{i}", "cluster-a", dimension, 0.5) for i in range(4)]
    candidate = [
        _observation(f"task-{i}", "cluster-a", dimension, 0.5 + diffs[i]) for i in range(4)
    ]
    config = DimensionTestConfig(minimum_detectable_effect=0.01, tolerance=0.05)

    # Act
    result = compare_dimension(dimension, baseline, candidate, config)

    # Assert
    assert result.significant is False
    assert result.material_drift is False
    assert result.insufficient_power is True


def test_given_large_consistent_difference_when_compare_dimension_then_material_drift() -> None:
    # Arrange
    dimension = VectorDimension.EFFICIENCY
    rng = random.Random(2)
    baseline = []
    candidate = []
    for i in range(40):
        candidate_value = 0.5 + 0.3 + rng.uniform(-0.02, 0.02)
        baseline.append(_observation(f"task-{i}", "cluster-a", dimension, 0.5))
        candidate.append(_observation(f"task-{i}", "cluster-a", dimension, candidate_value))
    config = DimensionTestConfig(minimum_detectable_effect=0.05, tolerance=0.05)

    # Act
    result = compare_dimension(dimension, baseline, candidate, config)

    # Assert
    assert result.significant is True
    assert result.material_drift is True
    assert result.test_method == DriftTestMethod.WILCOXON_SIGNED_RANK
    assert result.insufficient_power is False


def test_given_wilcoxon_raises_when_compare_dimension_then_falls_back_to_permutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    dimension = VectorDimension.EFFICIENCY
    baseline = [_observation(f"task-{i}", "cluster-a", dimension, 0.5) for i in range(10)]
    candidate = [
        _observation(f"task-{i}", "cluster-a", dimension, 0.5 + 0.01 * (i + 1)) for i in range(10)
    ]
    config = DimensionTestConfig(minimum_detectable_effect=0.05, tolerance=0.05)

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise ValueError("wilcoxon assumptions violated")

    monkeypatch.setattr(drift_statistics.stats, "wilcoxon", _raise)

    # Act
    result = compare_dimension(dimension, baseline, candidate, config)

    # Assert
    assert result.test_method == DriftTestMethod.PAIRED_PERMUTATION
    assert result.raw_p_value is not None
    assert 0.0 <= result.raw_p_value <= 1.0


def test_given_one_pair_per_task_binary_when_compare_dimension_then_selects_exact_mcnemar() -> (
    None
):
    # Arrange
    dimension = VectorDimension.GOAL_SUCCESS
    baseline_values = [1.0] * 10
    candidate_values = [1.0] * 7 + [0.0] * 3
    baseline = [
        _observation(f"task-{i}", "cluster-a", dimension, baseline_values[i]) for i in range(10)
    ]
    candidate = [
        _observation(f"task-{i}", "cluster-a", dimension, candidate_values[i]) for i in range(10)
    ]
    config = DimensionTestConfig(minimum_detectable_effect=0.1, tolerance=0.1, is_binary=True)

    # Act
    result = compare_dimension(dimension, baseline, candidate, config)

    # Assert
    assert result.test_method == DriftTestMethod.EXACT_MCNEMAR


def test_given_binary_repeats_when_compare_dimension_then_does_not_select_mcnemar() -> None:
    # Arrange: DD-11 -- repeats for a binary dimension must aggregate to task-level
    # rates and use Wilcoxon/permutation, never exact McNemar on the aggregated rate.
    dimension = VectorDimension.GOAL_SUCCESS
    baseline = []
    candidate = []
    for i in range(10):
        for repeat, candidate_value in enumerate((0.0, 1.0)):
            baseline.append(
                _observation(f"task-{i}", "cluster-a", dimension, 1.0, repeat_id=f"seed-{repeat}")
            )
            candidate.append(
                _observation(
                    f"task-{i}", "cluster-a", dimension, candidate_value, repeat_id=f"seed-{repeat}"
                )
            )
    config = DimensionTestConfig(minimum_detectable_effect=0.1, tolerance=0.1, is_binary=True)

    # Act
    result = compare_dimension(dimension, baseline, candidate, config)

    # Assert
    assert result.test_method != DriftTestMethod.EXACT_MCNEMAR
    assert result.test_method in (
        DriftTestMethod.WILCOXON_SIGNED_RANK,
        DriftTestMethod.PAIRED_PERMUTATION,
    )


def test_given_mismatched_task_ids_when_compare_dimension_then_raises_sampling_design_error() -> (
    None
):
    # Arrange
    dimension = VectorDimension.EFFICIENCY
    baseline = [_observation("task-a", "cluster-a", dimension, 0.5)]
    candidate = [_observation("task-b", "cluster-a", dimension, 0.5)]
    config = DimensionTestConfig(minimum_detectable_effect=0.05, tolerance=0.05)

    # Act & Assert
    with pytest.raises(SamplingDesignError):
        compare_dimension(dimension, baseline, candidate, config)


def test_given_independent_design_when_compare_dimension_then_raises_sampling_error() -> None:
    # Arrange
    dimension = VectorDimension.EFFICIENCY
    baseline = [_observation("task-a", "cluster-a", dimension, 0.5)]
    candidate = [_observation("task-a", "cluster-a", dimension, 0.5)]
    config = DimensionTestConfig(minimum_detectable_effect=0.05, tolerance=0.05)

    # Act & Assert
    with pytest.raises(SamplingDesignError):
        compare_dimension(
            dimension, baseline, candidate, config, sampling_design=SamplingDesign.INDEPENDENT
        )


def test_given_correlated_clusters_when_compare_dimension_then_cluster_ci_wider_than_naive() -> (
    None
):
    # Arrange
    dimension = VectorDimension.EFFICIENCY
    rng = random.Random(3)
    config = DimensionTestConfig(minimum_detectable_effect=0.05, tolerance=0.02)

    clustered_baseline: list[RunObservation] = []
    clustered_candidate: list[RunObservation] = []
    naive_baseline: list[RunObservation] = []
    naive_candidate: list[RunObservation] = []
    for i in range(20):
        cluster_sign = 0.05 if i < 10 else -0.05
        diff = cluster_sign + rng.uniform(-0.005, 0.005)
        cluster_id = "cluster-a" if i < 10 else "cluster-b"
        clustered_baseline.append(_observation(f"task-{i}", cluster_id, dimension, 0.5))
        clustered_candidate.append(_observation(f"task-{i}", cluster_id, dimension, 0.5 + diff))
        naive_baseline.append(_observation(f"task-{i}", f"solo-{i}", dimension, 0.5))
        naive_candidate.append(_observation(f"task-{i}", f"solo-{i}", dimension, 0.5 + diff))

    # Act
    clustered_result = compare_dimension(
        dimension, clustered_baseline, clustered_candidate, config, random_seed=7
    )
    naive_result = compare_dimension(
        dimension, naive_baseline, naive_candidate, config, random_seed=7
    )

    # Assert
    assert clustered_result.effective_cluster_count == 2
    assert naive_result.effective_cluster_count == 20
    assert clustered_result.confidence_interval is not None
    assert naive_result.confidence_interval is not None
    clustered_low, clustered_high = clustered_result.confidence_interval
    naive_low, naive_high = naive_result.confidence_interval
    assert (clustered_high - clustered_low) >= (naive_high - naive_low)


def test_given_borderline_p_values_when_holm_bonferroni_correction_then_flips_significance() -> (
    None
):
    # Arrange
    alpha = 0.02
    raw_p_values = [0.015, 0.03]

    # Act
    corrected = holm_bonferroni_correction(raw_p_values, alpha)

    # Assert
    assert raw_p_values[0] <= alpha
    assert corrected[0] > alpha
    assert corrected == pytest.approx((0.03, 0.03))


def test_given_multiple_dimensions_when_compare_baseline_to_candidate_then_correction_applied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    dim_a = VectorDimension.EFFICIENCY
    dim_b = VectorDimension.COST
    baseline = [
        _observation_with(f"task-{i}", "cluster-a", {dim_a: 0.5, dim_b: 0.5}) for i in range(10)
    ]
    candidate = [
        _observation_with(f"task-{i}", "cluster-a", {dim_a: 0.55, dim_b: 0.52}) for i in range(10)
    ]
    dimension_configs = {
        dim_a: DimensionTestConfig(minimum_detectable_effect=0.01, tolerance=0.01),
        dim_b: DimensionTestConfig(minimum_detectable_effect=0.01, tolerance=0.01),
    }
    canned_p_values = iter([0.015, 0.03])

    def _fake_wilcoxon_or_permutation(
        _paired_baseline: object,
        _paired_candidate: object,
        _diffs: object,
        *,
        permutation_resamples: int,
        random_seed: int,
    ) -> tuple[DriftTestMethod, float]:
        del permutation_resamples, random_seed
        return DriftTestMethod.WILCOXON_SIGNED_RANK, next(canned_p_values)

    monkeypatch.setattr(
        drift_statistics, "_wilcoxon_or_permutation", _fake_wilcoxon_or_permutation
    )

    # Act
    result = compare_baseline_to_candidate(
        "baseline-1", "candidate-1", baseline, candidate, dimension_configs, alpha=0.02
    )

    # Assert
    dim_a_result = result.dimension(dim_a)
    dim_b_result = result.dimension(dim_b)
    assert dim_a_result.raw_p_value == pytest.approx(0.015)
    assert dim_a_result.corrected_p_value == pytest.approx(0.03)
    assert dim_a_result.significant is False
    assert dim_b_result.raw_p_value == pytest.approx(0.03)


def test_given_low_impact_confidence_when_compare_critical_dimension_then_unaffected() -> None:
    # Arrange: SAFETY is a critical dimension; baseline outcomes have no variance,
    # so downstream-impact association is "insufficient evidence" -- this must not
    # suppress or downgrade the (otherwise material) drift classification.
    dimension = VectorDimension.SAFETY
    rng = random.Random(4)
    baseline = []
    candidate = []
    for i in range(40):
        candidate_value = 0.9 - 0.3 + rng.uniform(-0.01, 0.01)
        baseline.append(_observation(f"task-{i}", "cluster-a", dimension, 0.9))
        candidate.append(_observation(f"task-{i}", "cluster-a", dimension, candidate_value))
    config = DimensionTestConfig(minimum_detectable_effect=0.05, tolerance=0.05)

    # Act
    result = compare_dimension(dimension, baseline, candidate, config)

    # Assert
    assert result.downstream_impact.insufficient_evidence is True
    assert result.material_drift is True


def test_given_unavailable_dimension_scores_when_compare_dimension_then_returns_no_data() -> None:
    # Arrange
    dimension = VectorDimension.EFFICIENCY
    baseline = [
        _observation(f"task-{i}", "cluster-a", dimension, 0.5, available=False) for i in range(5)
    ]
    candidate = [
        _observation(f"task-{i}", "cluster-a", dimension, 0.5, available=False) for i in range(5)
    ]
    config = DimensionTestConfig(minimum_detectable_effect=0.05, tolerance=0.05)

    # Act
    result = compare_dimension(dimension, baseline, candidate, config)

    # Assert
    assert result.has_sufficient_data is False
    assert result.test_method is None
    assert result.material_drift is False
    assert result.significant is False


def test_given_explicit_timestamp_when_compare_baseline_to_candidate_then_uses_provided_value() -> (
    None
):
    # Arrange
    dimension = VectorDimension.EFFICIENCY
    baseline = [_observation("task-0", "cluster-a", dimension, 0.5)]
    candidate = [_observation("task-0", "cluster-a", dimension, 0.5)]
    config = DimensionTestConfig(minimum_detectable_effect=0.05, tolerance=0.05)

    # Act
    result = compare_baseline_to_candidate(
        "baseline-run",
        "candidate-run",
        baseline,
        candidate,
        {dimension: config},
        compared_at="2026-08-25T00:00:00+00:00",
    )

    # Assert
    assert result.compared_at == "2026-08-25T00:00:00+00:00"
    assert result.baseline_run_id == "baseline-run"
    assert result.candidate_run_id == "candidate-run"


def test_given_unknown_dimension_when_dimension_lookup_then_raises_key_error() -> None:
    # Arrange
    dimension = VectorDimension.EFFICIENCY
    baseline = [_observation("task-0", "cluster-a", dimension, 0.5)]
    candidate = [_observation("task-0", "cluster-a", dimension, 0.5)]
    config = DimensionTestConfig(minimum_detectable_effect=0.05, tolerance=0.05)
    result = compare_baseline_to_candidate("b", "c", baseline, candidate, {dimension: config})

    # Act & Assert
    with pytest.raises(KeyError):
        result.dimension(VectorDimension.SAFETY)


def test_given_baseline_candidate_evidence_when_detector_wrapper_then_delegates_to_statistics() -> (
    None
):
    # Arrange
    dimension = VectorDimension.EFFICIENCY
    baseline = [_observation("task-0", "cluster-a", dimension, 0.5)]
    candidate = [_observation("task-0", "cluster-a", dimension, 0.6)]
    config = DimensionTestConfig(minimum_detectable_effect=0.05, tolerance=0.05)

    # Act
    result = detector.compare_baseline_to_candidate(
        "baseline-run",
        "candidate-run",
        baseline,
        candidate,
        {dimension: config},
        compared_at="ts",
    )

    # Assert
    assert result.baseline_run_id == "baseline-run"
    assert result.dimension(dimension).effect_size == pytest.approx(0.1)


def test_given_legacy_facade_when_detect_drift_then_unchanged_behavior() -> None:
    # Arrange: guards that the legacy severity facade remains byte-for-byte unchanged.
    from arise_x.telemetry.events import RunEvent

    event = RunEvent(
        task_id="t-1",
        disruption="baseline",
        success=True,
        policy_violations=0,
        interventions=0,
        latency_ms=100,
    )

    # Act
    result = detector.detect_drift(event, threshold=0.5)

    # Assert
    assert result.is_drifting is False
    assert result.score == pytest.approx(0.025)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("repeat_id", "seed-99"), ("family", "other"), ("cluster_id", "other"),
        ("suite_id", "other"), ("suite_version", 2),
        ("suite_partition", "development"), ("scenario_name", "other"),
        ("scenario_version", 2),
    ],
)
def test_given_mismatched_pair_identity_when_compare_then_rejected(field, value) -> None:
    # Arrange
    baseline = _observation("t1", "c1", VectorDimension.SAFETY, 1.0)
    candidate = replace(baseline, trajectory=replace(baseline.trajectory, **{field: value}))

    # Act & Assert
    with pytest.raises(SamplingDesignError):
        compare_dimension(
            VectorDimension.SAFETY, [baseline], [candidate], DimensionTestConfig(0.1, 0.05)
        )


@pytest.mark.parametrize("change", ["schema", "normalization", "duplicate", "missing-repeat"])
def test_given_incompatible_observations_when_compare_then_rejected(change: str) -> None:
    # Arrange
    observation = _observation("t1", "c1", VectorDimension.SAFETY, 1.0)
    baseline = [observation]
    candidate = [observation]
    if change == "schema":
        candidate = [replace(observation, vector=replace(observation.vector, schema_version="v2"))]
    elif change == "normalization":
        score = replace(observation.vector.safety, normalization_version="v2")
        candidate = [replace(observation, vector=replace(observation.vector, safety=score))]
    elif change == "duplicate":
        baseline *= 2
        candidate *= 2
    else:
        baseline.append(replace(observation, trajectory=replace(
            observation.trajectory, repeat_id="seed-1"
        )))

    # Act & Assert
    with pytest.raises(SamplingDesignError):
        compare_dimension(
            VectorDimension.SAFETY, baseline, candidate, DimensionTestConfig(0.1, 0.05)
        )


@pytest.mark.parametrize("repeated", [False, True])
def test_given_nonbinary_observed_values_when_binary_comparison_then_rejected(repeated) -> None:
    # Arrange
    observations = [_observation("t1", "c1", VectorDimension.GOAL_SUCCESS, 0.7)]
    if repeated:
        observations.append(_observation(
            "t1", "c1", VectorDimension.GOAL_SUCCESS, 1.0, repeat_id="seed-1"
        ))

    # Act & Assert
    with pytest.raises(SamplingDesignError, match="binary"):
        compare_dimension(
            VectorDimension.GOAL_SUCCESS, observations, observations,
            DimensionTestConfig(0.1, 0.05, is_binary=True),
        )


@pytest.mark.parametrize("missing", ["unavailable", "zero-count"])
def test_given_incomplete_dimension_coverage_when_compare_then_insufficient(missing) -> None:
    # Arrange
    observations = [_observation(f"t{i}", f"c{i}", VectorDimension.SAFETY, 1.0) for i in range(3)]
    score = replace(observations[0].vector.safety, evidence_count=0,
                    available=missing != "unavailable")
    candidate = [replace(observations[0], vector=replace(observations[0].vector, safety=score)),
                 *observations[1:]]

    # Act
    result = compare_dimension(
        VectorDimension.SAFETY, observations, candidate, DimensionTestConfig(0.1, 0.05)
    )

    # Assert
    assert result.has_sufficient_data is False


def test_given_development_pairs_when_compare_then_diagnostics_remain_available() -> None:
    # Arrange
    observation = _observation("t1", "c1", VectorDimension.SAFETY, 1.0)
    observation = replace(observation, trajectory=replace(
        observation.trajectory, suite_partition="development"
    ))

    # Act
    result = compare_dimension(
        VectorDimension.SAFETY, [observation], [observation], DimensionTestConfig(0.1, 0.05)
    )

    # Assert
    assert result.raw_p_value == 1.0
