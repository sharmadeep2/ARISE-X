"""FastAPI app exposing a minimal reliability run endpoint."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from arise_x.config import load_settings
from arise_x.drift.statistics import (
    DEFAULT_ALPHA,
    DEFAULT_TARGET_POWER,
    DriftComparisonResult,
    RunObservation,
    compare_baseline_to_candidate,
)
from arise_x.evaluation.runner import execute_and_persist_run
from arise_x.storage.repository import RunNotFoundError, RunRecord, RunRepository
from arise_x.trust.gate import (
    CriticalMetricConfig,
    aggregate_reliability,
    default_dimension_configs,
    evaluate_release,
)
from arise_x.trust.vector import ReliabilityVector, VectorDimension

app = FastAPI(title="ARISE-X API", version="0.1.0")


class RunRequest(BaseModel):
    iterations: int = Field(default=3, ge=1, le=200)
    scenario: str | None = Field(
        default=None, description="Reserved for future scenario overrides; unused for now."
    )
    seed: int | None = Field(
        default=None, description="Override the scenario's deterministic seed."
    )


class GateRequest(BaseModel):
    baseline_run_id: str
    candidate_run_id: str


def _vector_summary(vector: ReliabilityVector) -> dict[str, dict[str, object]]:
    """Bounded per-dimension value/availability summary; never raw trajectory evidence."""

    return {
        dimension.value: {
            "value": vector.dimension(dimension).value,
            "available": vector.dimension(dimension).available,
        }
        for dimension in VectorDimension
    }


def _observations(record: RunRecord) -> list[RunObservation]:
    """Pair a persisted run's trajectories and reliability vectors into RunObservation evidence."""

    return [
        RunObservation(trajectory=trajectory, vector=vector)
        for trajectory, vector in zip(record.trajectories, record.vectors, strict=True)
    ]


def _dimension_summary(drift: DriftComparisonResult) -> list[dict[str, object]]:
    """Bounded per-dimension gate rationale; never raw trajectory/step evidence."""

    return [
        {
            "dimension": result.dimension.value,
            "effect_size": result.effect_size,
            "significant": result.significant,
            "material_drift": result.material_drift,
            "has_sufficient_data": result.has_sufficient_data,
        }
        for result in drift.dimension_results
    ]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run")
def run_loop(request: RunRequest) -> dict[str, object]:
    settings = load_settings()
    repository = RunRepository(settings.output_dir)
    outcome = execute_and_persist_run(request.iterations, settings, repository, seed=request.seed)
    return {
        "iterations": request.iterations,
        "trustworthy_count": sum(1 for item in outcome.results if item.trustworthy),
        "results": [item.__dict__ for item in outcome.results],
        "run_id": outcome.run_id,
        "scenario_version": outcome.scenario_version,
        "agent_version": outcome.agent_version,
        "config_fingerprint": outcome.config_fingerprint,
        "seed": outcome.seed,
        "reliability_vectors": [_vector_summary(vector) for vector in outcome.vectors],
    }


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, object]:
    """Return full trajectory and vector detail for one persisted run.

    Detail retrieval is explicit/opt-in; the default ``POST /run`` response
    stays bounded to per-dimension vector summaries only.
    """

    settings = load_settings()
    repository = RunRepository(settings.output_dir)
    try:
        record = repository.read_run(run_id)
    except RunNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return {
        "run_id": record.metadata.run_id,
        "metadata": asdict(record.metadata),
        "results": [asdict(item) for item in record.results],
        "trajectories": [asdict(item) for item in record.trajectories],
        "vectors": [asdict(item) for item in record.vectors],
    }


@app.post("/gate")
def gate(request: GateRequest) -> dict[str, object]:
    """Compare two persisted runs and return a bounded release-gate verdict.

    Returns HTTP 200 for every completed evaluation, including a blocking
    verdict -- the response body's ``verdict`` field (``"pass"``/``"warn"``/
    ``"block"``) is the source of truth for the release decision, matching
    this API's existing pattern of reporting evaluation outcomes in the
    response body rather than via HTTP status. Only an unknown run ID raises
    an ``HTTPException`` (404), matching ``GET /runs/{run_id}``.
    """

    settings = load_settings()
    repository = RunRepository(settings.output_dir)
    try:
        baseline_record = repository.read_run(request.baseline_run_id)
        candidate_record = repository.read_run(request.candidate_run_id)
    except RunNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    baseline_observations = _observations(baseline_record)
    candidate_observations = _observations(candidate_record)

    dimension_configs = default_dimension_configs(settings.scenario)
    alpha = DEFAULT_ALPHA
    target_power = DEFAULT_TARGET_POWER
    critical_config = CriticalMetricConfig()
    if settings.gate_policy is not None:
        dimension_configs.update(settings.gate_policy.dimension_config_map())
        alpha = settings.gate_policy.alpha
        target_power = settings.gate_policy.target_power
        critical_config = settings.gate_policy.critical_metric_config()

    drift = compare_baseline_to_candidate(
        request.baseline_run_id,
        request.candidate_run_id,
        baseline_observations,
        candidate_observations,
        dimension_configs,
        alpha=alpha,
        target_power=target_power,
    )

    evidence_partitions = {
        observation.trajectory.suite_partition
        for observation in (*baseline_observations, *candidate_observations)
    }
    candidate_vectors = [observation.vector for observation in candidate_observations]
    ari_source = aggregate_reliability(candidate_vectors) if candidate_vectors else None

    verdict = evaluate_release(
        drift,
        scenario=settings.scenario,
        suite=settings.evaluation_suite,
        evidence_partitions=evidence_partitions,
        critical_config=critical_config,
        ari_source=ari_source,
    )

    return {
        "baseline_run_id": request.baseline_run_id,
        "candidate_run_id": request.candidate_run_id,
        "verdict": verdict.outcome.value,
        "geometric_ari": verdict.geometric_ari,
        "dimensions": _dimension_summary(drift),
        "critical_override_reasons": list(verdict.critical_override_reasons),
        "held_out_suite_reasons": list(verdict.held_out_suite_reasons),
        "non_critical_warning_reasons": list(verdict.non_critical_warning_reasons),
        "error_budget": None,
    }
