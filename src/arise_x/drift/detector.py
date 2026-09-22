"""Legacy per-event severity facade, plus the baseline-vs-candidate comparison entry point.

`DriftResult`, `compute_drift_score`, and `detect_drift` below are an unchanged
legacy severity heuristic kept for `evaluation/runner.py`. The statistically
rigorous baseline-vs-candidate comparison (task-level pairing, matched test
selection, power analysis, Holm-Bonferroni correction, cluster-aware
bootstrap CIs, and downstream-impact priority) lives in
`arise_x.drift.statistics`; `compare_baseline_to_candidate` below is a thin
re-export so both entry points are importable from this module.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from arise_x.drift import statistics
from arise_x.drift.statistics import (
    DEFAULT_ALPHA,
    DEFAULT_BOOTSTRAP_ITERATIONS,
    DEFAULT_PERMUTATION_RESAMPLES,
    DEFAULT_RANDOM_SEED,
    DEFAULT_TARGET_POWER,
    DimensionTestConfig,
    DriftComparisonResult,
    RunObservation,
    SamplingDesign,
)
from arise_x.telemetry.events import RunEvent
from arise_x.trust.vector import VectorDimension


@dataclass(frozen=True)
class DriftResult:
    """Drift output including score and threshold verdict."""

    score: float
    is_drifting: bool


def compute_drift_score(event: RunEvent) -> float:
    """Compute a bounded drift score from operational signals."""

    score = 0.0
    if not event.success:
        score += 0.4
    score += min(0.2, event.policy_violations * 0.05)
    score += min(0.2, event.interventions * 0.04)
    score += min(0.2, event.latency_ms / 4000.0)
    return min(1.0, score)


def detect_drift(event: RunEvent, threshold: float) -> DriftResult:
    """Detect drift for a given telemetry event and threshold."""

    score = compute_drift_score(event)
    return DriftResult(score=score, is_drifting=score >= threshold)


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
    """Compare baseline and candidate reliability-vector evidence per dimension.

    Thin wrapper delegating to `arise_x.drift.statistics.compare_baseline_to_candidate`;
    see that module for the full paired-sample, power, correction, and
    cluster-bootstrap statistical design. Unrelated to, and does not affect,
    `compute_drift_score`/`detect_drift` above.
    """

    return statistics.compare_baseline_to_candidate(
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
        baseline=baseline,
        candidate=candidate,
        dimension_configs=dimension_configs,
        alpha=alpha,
        target_power=target_power,
        bootstrap_iterations=bootstrap_iterations,
        permutation_resamples=permutation_resamples,
        random_seed=random_seed,
        sampling_design=sampling_design,
        compared_at=compared_at,
    )
