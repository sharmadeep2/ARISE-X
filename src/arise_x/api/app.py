"""FastAPI app exposing a minimal reliability run endpoint."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from arise_x.config import ConfigurationError, load_settings
from arise_x.drift.statistics import SamplingDesignError
from arise_x.evaluation.runner import execute_and_persist_run
from arise_x.storage.repository import RepositoryError, RunNotFoundError, RunRepository
from arise_x.trust.gate import GateService, HeldOutSuiteError
from arise_x.trust.vector import ReliabilityVector, VectorDimension

app = FastAPI(title="ARISE-X API", version="0.1.0")


class RunRequest(BaseModel):
    iterations: int = Field(default=3, ge=1, le=200)
    scenario: str | None = Field(
        default=None, description="Scenario name; defaults to the configured scenario."
    )
    seed: int | None = Field(
        default=None, description="Override the scenario's deterministic seed."
    )


class GateRequest(BaseModel):
    baseline_run_id: str = Field(min_length=1, max_length=250)
    candidate_run_id: str = Field(min_length=1, max_length=250)
    production_history_run_id: str | None = Field(default=None, min_length=1, max_length=250)


def _vector_summary(vector: ReliabilityVector) -> dict[str, dict[str, object]]:
    """Bounded per-dimension value/availability summary; never raw trajectory evidence."""

    return {
        dimension.value: {
            "value": vector.dimension(dimension).value,
            "available": vector.dimension(dimension).available,
        }
        for dimension in VectorDimension
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run")
def run_loop(request: RunRequest) -> dict[str, object]:
    settings = load_settings()
    if request.scenario is not None and (
        settings.scenario is None or request.scenario != settings.scenario.name
    ):
        configured_name = settings.scenario.name if settings.scenario is not None else None
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unknown scenario {request.scenario!r}; configured scenario is "
                f"{configured_name!r}."
            ),
        )
    repository = RunRepository(settings.output_dir)
    outcome = execute_and_persist_run(
        request.iterations,
        settings,
        repository,
        scenario=settings.scenario,
        seed=request.seed,
    )
    return {
        "iterations": request.iterations,
        "trustworthy_count": sum(1 for item in outcome.results if item.trustworthy),
        "results": [item.__dict__ for item in outcome.results],
        "run_id": outcome.run_id,
        "scenario_version": outcome.scenario_version,
        "agent_version": outcome.agent_version,
        "config_fingerprint": outcome.config_fingerprint,
        "seed": outcome.seed,
        "trust_threshold": outcome.trust_threshold,
        "drift_threshold": outcome.drift_threshold,
        "compatibility_event_count": len(outcome.events),
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
        "events": [asdict(item) for item in record.events],
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

    try:
        settings = load_settings()
        service = GateService(
            RunRepository(settings.output_dir),
            scenario=settings.scenario,
            suite=settings.evaluation_suite,
            policy=settings.gate_policy,
        )
        decision = service.evaluate(
            request.baseline_run_id,
            request.candidate_run_id,
            production_history_run_id=request.production_history_run_id,
        )
    except RunNotFoundError as error:
        raise HTTPException(status_code=404, detail="Gate input run was not found.") from error
    except ConfigurationError as error:
        raise HTTPException(status_code=422, detail="Gate configuration is invalid.") from error
    except (RepositoryError, SamplingDesignError, HeldOutSuiteError, ValueError) as error:
        raise HTTPException(
            status_code=422,
            detail="Gate evidence is invalid or incomplete.",
        ) from error

    return {
        "decision_id": decision.decision_id,
        "baseline_run_id": decision.baseline_run_id,
        "candidate_run_id": decision.candidate_run_id,
        "production_history_run_id": decision.production_history_run_id,
        "verdict": decision.verdict,
        "geometric_ari": decision.geometric_ari,
        "policy_version": decision.policy_version,
        "policy_fingerprint": decision.policy_fingerprint,
        "suite_version": decision.suite_version,
        "suite_fingerprint": decision.suite_fingerprint,
        "dimensions": list(decision.dimension_rationale),
        "critical_override_reasons": list(decision.critical_override_reasons),
        "held_out_suite_reasons": list(decision.held_out_suite_reasons),
        "required_evidence_reasons": list(decision.required_evidence_reasons),
        "non_critical_warning_reasons": list(decision.non_critical_warning_reasons),
        "error_budget_reasons": list(decision.error_budget_reasons),
        "error_budget": decision.error_budget,
        "window_inputs": decision.window_inputs,
    }
