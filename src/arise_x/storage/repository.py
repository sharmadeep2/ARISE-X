"""Versioned, schema-tagged repository for simulation run results."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from arise_x.evaluation.runner import IterationResult
from arise_x.telemetry.trajectory import (
    FaultTrigger,
    Outcome,
    Step,
    ToolInvocation,
    Trajectory,
    UsageMetrics,
)
from arise_x.trust.vector import (
    NORMALIZATION_VERSION,
    DimensionScore,
    ReliabilityVector,
    VectorDimension,
)

# Schema 2 adds "trajectories" and "vectors" alongside "results" under the run
# envelope. Runs persisted under schema 1 predate that shape; read_run()
# rejects them with UnsupportedSchemaVersionError rather than guessing at a
# migration, since 0.1.0 has no external consumers yet.
SCHEMA_VERSION = 2

_VALID_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class RepositoryError(Exception):
    """Base error for run-repository failures."""


class RunNotFoundError(RepositoryError):
    """Raised when no run artifact exists for a given run ID."""


class CorruptRunError(RepositoryError):
    """Raised when a persisted run payload cannot be parsed or is missing required fields."""


class UnsupportedSchemaVersionError(RepositoryError):
    """Raised when a persisted run's schema version is not supported by this reader."""


@dataclass(frozen=True)
class RunMetadata:
    """Identity and provenance metadata for one persisted run.

    ``scenario_version``, ``agent_version``, ``config_fingerprint``, and
    ``source_revision`` are simple optional strings until the scenario and
    agent contracts land in later phases.
    """

    run_id: str
    schema_version: int
    created_at: str
    scenario_version: str | None = None
    agent_version: str | None = None
    config_fingerprint: str | None = None
    seed: int | None = None
    source_revision: str | None = None


@dataclass(frozen=True)
class RunRecord:
    """A persisted run's metadata paired with its iteration results, trajectories, and vectors."""

    metadata: RunMetadata
    results: list[IterationResult]
    trajectories: list[Trajectory] = field(default_factory=list)
    vectors: list[ReliabilityVector] = field(default_factory=list)


def write_results(path: Path, results: list[IterationResult]) -> None:
    """Persist iteration results as JSON for downstream analysis."""

    payload = [asdict(item) for item in results]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _step_from_dict(raw: dict) -> Step:
    """Reconstruct a Step from its serialized dict form."""

    tool_raw = raw.get("tool")
    fault_raw = raw.get("fault")
    usage_raw = raw.get("usage") or {}
    return Step(
        index=raw["index"],
        action=raw["action"],
        state_transition=raw["state_transition"],
        tool=ToolInvocation(**tool_raw) if tool_raw is not None else None,
        fault=FaultTrigger(**fault_raw) if fault_raw is not None else None,
        recovered=raw.get("recovered", False),
        usage=UsageMetrics(**usage_raw),
        prompt_text=raw.get("prompt_text"),
        output_text=raw.get("output_text"),
    )


def _trajectory_from_dict(raw: dict) -> Trajectory:
    """Reconstruct a Trajectory from its serialized dict form."""

    steps = tuple(_step_from_dict(step) for step in raw["steps"])
    outcome_raw = raw["outcome"]
    outcome = Outcome(goal_achieved=outcome_raw["goal_achieved"], label=outcome_raw["label"])
    return Trajectory(
        run_id=raw["run_id"],
        task_id=raw["task_id"],
        family=raw["family"],
        cluster_id=raw["cluster_id"],
        suite_id=raw["suite_id"],
        suite_version=raw["suite_version"],
        suite_partition=raw["suite_partition"],
        repeat_id=raw["repeat_id"],
        scenario_name=raw["scenario_name"],
        scenario_version=raw["scenario_version"],
        agent_id=raw["agent_id"],
        agent_version=raw["agent_version"],
        steps=steps,
        outcome=outcome,
        intervention_count=raw.get("intervention_count", 0),
        policy_violation_count=raw.get("policy_violation_count", 0),
    )


def _dimension_score_from_dict(raw: dict) -> DimensionScore:
    """Reconstruct a DimensionScore from its serialized dict form."""

    return DimensionScore(
        dimension=VectorDimension(raw["dimension"]),
        value=raw["value"],
        available=raw["available"],
        evidence_count=raw["evidence_count"],
        normalization_version=raw.get("normalization_version", NORMALIZATION_VERSION),
    )


def _vector_from_dict(raw: dict) -> ReliabilityVector:
    """Reconstruct a ReliabilityVector from its serialized dict form."""

    return ReliabilityVector(
        goal_success=_dimension_score_from_dict(raw["goal_success"]),
        resilience=_dimension_score_from_dict(raw["resilience"]),
        behavioral_stability=_dimension_score_from_dict(raw["behavioral_stability"]),
        recovery=_dimension_score_from_dict(raw["recovery"]),
        safety=_dimension_score_from_dict(raw["safety"]),
        efficiency=_dimension_score_from_dict(raw["efficiency"]),
        cost=_dimension_score_from_dict(raw["cost"]),
        autonomy=_dimension_score_from_dict(raw["autonomy"]),
        schema_version=raw.get("schema_version", NORMALIZATION_VERSION),
    )


class RunRepository:
    """Versioned, schema-tagged store for completed reliability runs.

    Each run is persisted as its own artifact keyed by an immutable run ID,
    rather than overwriting a single shared file.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def write_run(
        self,
        results: list[IterationResult],
        *,
        run_id: str | None = None,
        scenario_version: str | None = None,
        agent_version: str | None = None,
        config_fingerprint: str | None = None,
        seed: int | None = None,
        source_revision: str | None = None,
        trajectories: list[Trajectory] | None = None,
        vectors: list[ReliabilityVector] | None = None,
    ) -> RunMetadata:
        """Persist a completed run, including any trajectory/vector evidence, under an
        explicit or generated immutable run ID."""

        resolved_run_id = run_id if run_id is not None else _generate_run_id()
        _validate_run_id(resolved_run_id)

        metadata = RunMetadata(
            run_id=resolved_run_id,
            schema_version=SCHEMA_VERSION,
            created_at=datetime.now(UTC).isoformat(),
            scenario_version=scenario_version,
            agent_version=agent_version,
            config_fingerprint=config_fingerprint,
            seed=seed,
            source_revision=source_revision,
        )
        payload = {
            "metadata": asdict(metadata),
            "results": [asdict(item) for item in results],
            "trajectories": [asdict(item) for item in (trajectories or [])],
            "vectors": [asdict(item) for item in (vectors or [])],
        }
        self._run_path(resolved_run_id).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return metadata

    def read_run(self, run_id: str) -> RunRecord:
        """Read a persisted run by its immutable run ID."""

        run_path = self._run_path(run_id)
        if not run_path.exists():
            raise RunNotFoundError(f"No run persisted for run_id={run_id!r}")

        try:
            payload = json.loads(run_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise CorruptRunError(f"Run {run_id!r} payload is not valid JSON") from error

        if not isinstance(payload, dict):
            raise CorruptRunError(f"Run {run_id!r} payload must be a JSON object")

        raw_metadata = payload.get("metadata")
        raw_results = payload.get("results")
        if not isinstance(raw_metadata, dict) or not isinstance(raw_results, list):
            raise CorruptRunError(
                f"Run {run_id!r} payload is missing required 'metadata' or 'results' fields"
            )

        schema_version = raw_metadata.get("schema_version")
        if schema_version != SCHEMA_VERSION:
            raise UnsupportedSchemaVersionError(
                f"Run {run_id!r} has unsupported schema_version={schema_version!r}; "
                f"expected {SCHEMA_VERSION}"
            )

        raw_trajectories = payload.get("trajectories", [])
        raw_vectors = payload.get("vectors", [])
        if not isinstance(raw_trajectories, list) or not isinstance(raw_vectors, list):
            raise CorruptRunError(
                f"Run {run_id!r} payload has malformed 'trajectories' or 'vectors' fields"
            )

        try:
            metadata = RunMetadata(**raw_metadata)
            results = [IterationResult(**item) for item in raw_results]
            trajectories = [_trajectory_from_dict(item) for item in raw_trajectories]
            vectors = [_vector_from_dict(item) for item in raw_vectors]
        except (TypeError, KeyError, ValueError) as error:
            raise CorruptRunError(
                f"Run {run_id!r} payload has malformed metadata, results, trajectories, or vectors"
            ) from error

        return RunRecord(
            metadata=metadata, results=results, trajectories=trajectories, vectors=vectors
        )

    def list_runs(self) -> list[RunMetadata]:
        """List metadata for every persisted run, ordered deterministically by run ID."""

        run_ids = sorted(path.stem for path in self._base_dir.glob("*.json"))
        return [self.read_run(run_id).metadata for run_id in run_ids]

    def run_exists(self, run_id: str) -> bool:
        """Look up whether a run artifact exists for the given run ID."""

        return self._run_path(run_id).exists()

    def _run_path(self, run_id: str) -> Path:
        return self._base_dir / f"{run_id}.json"


def _generate_run_id() -> str:
    """Generate a sortable, unique run identifier from a UTC timestamp and random suffix."""

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    return f"{timestamp}-{uuid4().hex[:8]}"


def _validate_run_id(run_id: str) -> None:
    """Reject run IDs that could escape the repository directory."""

    if not run_id or not _VALID_RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError(
            "run_id must be a non-empty string of letters, digits, '.', '_', or '-'; "
            f"got {run_id!r}"
        )
