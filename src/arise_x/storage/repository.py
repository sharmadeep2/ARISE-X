"""Versioned, schema-tagged repository for simulation run results."""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field, fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from arise_x.evaluation.runner import IterationResult
from arise_x.fingerprints import canonical_json_fingerprint
from arise_x.telemetry.events import RunEvent
from arise_x.telemetry.trajectory import (
    ContentKind,
    FaultTrigger,
    Outcome,
    OutcomeStatus,
    RecoveryEvidence,
    RedactedContent,
    RedactionMarker,
    Step,
    ToolInvocation,
    Trajectory,
    UsageMetrics,
)
from arise_x.trust.vector import (
    NORMALIZATION_VERSION,
    ConfidenceMetadata,
    DimensionScore,
    ReliabilityVector,
    VectorDimension,
)

# Schema 4 retains the RunEvent compatibility projection alongside strict
# trajectory/vector evidence. Older schemas are rejected explicitly rather
# than inferring evidence that was not persisted.
SCHEMA_VERSION = 4
GATE_DECISION_SCHEMA_VERSION = 1

_VALID_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
_MAX_RUN_ID_LENGTH = 250
_WINDOWS_RESERVED_NAMES = {
    "AUX",
    "CON",
    "NUL",
    "PRN",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


class RepositoryError(Exception):
    """Base error for run-repository failures."""


class RunNotFoundError(RepositoryError):
    """Raised when no run artifact exists for a given run ID."""


class GateDecisionNotFoundError(RepositoryError):
    """Raised when no immutable gate decision exists for a decision ID."""


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
    trust_threshold: float | None = None
    drift_threshold: float | None = None


@dataclass(frozen=True)
class RunRecord:
    """A persisted run's correlated summary and primary evidence."""

    metadata: RunMetadata
    results: list[IterationResult]
    events: list[RunEvent] = field(default_factory=list)
    trajectories: list[Trajectory] = field(default_factory=list)
    vectors: list[ReliabilityVector] = field(default_factory=list)


@dataclass(frozen=True)
class GateDecisionRecord:
    """Reconstructable immutable release-gate decision and its input snapshots."""

    decision_id: str
    schema_version: int
    created_at: str
    baseline_run_id: str
    candidate_run_id: str
    production_history_run_id: str | None
    policy_version: str
    policy_fingerprint: str
    policy_snapshot: dict[str, Any]
    suite_version: int
    suite_fingerprint: str
    suite_snapshot: dict[str, Any]
    verdict: str
    geometric_ari: float | None
    dimension_rationale: tuple[dict[str, Any], ...]
    critical_override_reasons: tuple[str, ...]
    held_out_suite_reasons: tuple[str, ...]
    required_evidence_reasons: tuple[str, ...]
    non_critical_warning_reasons: tuple[str, ...]
    error_budget_reasons: tuple[str, ...]
    error_budget: dict[str, Any] | None
    window_inputs: dict[str, Any]
    rationale_version: str = "v1"


def write_results(path: Path, results: list[IterationResult]) -> None:
    """Persist iteration results as JSON for downstream analysis."""

    payload = [asdict(item) for item in results]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _step_from_dict(raw: dict) -> Step:
    """Reconstruct a Step from its serialized dict form."""

    tool_raw = raw.get("tool")
    fault_raw = raw.get("fault")
    recovery_raw = raw.get("recovery")
    usage_raw = raw.get("usage") or {}

    def content(value: dict | None) -> RedactedContent | None:
        if value is None:
            return None
        if not isinstance(value, dict):
            raise TypeError("Redacted content must be an object")
        return RedactedContent(
            kind=ContentKind(value["kind"]),
            reference_id=value["reference_id"],
            marker=RedactionMarker(value["marker"]),
        )

    tool = None
    if tool_raw is not None:
        if not isinstance(tool_raw, dict):
            raise TypeError("Tool invocation must be an object")
        tool = ToolInvocation(
            call_id=tool_raw["call_id"],
            name=tool_raw["name"],
            call_payload=content(tool_raw.get("call_payload")),
            response_payload=content(tool_raw.get("response_payload")),
        )
    return Step(
        index=raw["index"],
        action=raw["action"],
        state_transition=raw["state_transition"],
        tool=tool,
        fault=FaultTrigger(**fault_raw) if fault_raw is not None else None,
        recovered=raw.get("recovered", False),
        recovery=RecoveryEvidence(**recovery_raw) if recovery_raw is not None else None,
        usage=UsageMetrics(**usage_raw),
        prompt_text=content(raw.get("prompt_text")),
        output_text=content(raw.get("output_text")),
    )


def _trajectory_from_dict(raw: dict) -> Trajectory:
    """Reconstruct a Trajectory from its serialized dict form."""

    steps = tuple(_step_from_dict(step) for step in raw["steps"])
    outcome_raw = raw["outcome"]
    outcome = Outcome(
        goal_achieved=outcome_raw["goal_achieved"],
        label=outcome_raw["label"],
        status=OutcomeStatus(outcome_raw["status"]),
        terminal_state=outcome_raw["terminal_state"],
        evidence_references=outcome_raw["evidence_references"],
    )
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
        evidence_total=raw["evidence_total"],
        confidence=(
            ConfidenceMetadata(**raw["confidence"])
            if raw["confidence"] is not None
            else None
        ),
        evidence_references=raw["evidence_references"],
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


def _validate_iteration_result(raw: Any, *, context: str) -> None:
    """Validate the serialized IterationResult contract without coercing values."""

    expected_fields = {"task_id", "disruption", "drift_score", "trust_score", "trustworthy"}
    if not isinstance(raw, dict) or set(raw) != expected_fields:
        raise CorruptRunError(f"{context} is not a serialized IterationResult")
    if not isinstance(raw["task_id"], str) or not raw["task_id"]:
        raise CorruptRunError(f"{context} has an invalid task_id")
    if not isinstance(raw["disruption"], str) or not raw["disruption"]:
        raise CorruptRunError(f"{context} has an invalid disruption")
    for field_name in ("drift_score", "trust_score"):
        value = raw[field_name]
        if (
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(value)
        ):
            raise CorruptRunError(f"{context} has an invalid {field_name}")
    if not isinstance(raw["trustworthy"], bool):
        raise CorruptRunError(f"{context} has an invalid trustworthy flag")


def _validate_run_event(raw: Any, *, context: str) -> None:
    """Validate one serialized RunEvent without coercing values."""

    expected_fields = {
        "task_id",
        "disruption",
        "success",
        "policy_violations",
        "interventions",
        "latency_ms",
    }
    if not isinstance(raw, dict) or set(raw) != expected_fields:
        raise CorruptRunError(f"{context} is not a serialized RunEvent")
    for field_name in ("task_id", "disruption"):
        if not isinstance(raw[field_name], str) or not raw[field_name]:
            raise CorruptRunError(f"{context} has an invalid {field_name}")
    if not isinstance(raw["success"], bool):
        raise CorruptRunError(f"{context} has an invalid success flag")
    for field_name in ("policy_violations", "interventions"):
        value = raw[field_name]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise CorruptRunError(f"{context} has an invalid {field_name}")
    latency_ms = raw["latency_ms"]
    if (
        isinstance(latency_ms, bool)
        or not isinstance(latency_ms, int | float)
        or not math.isfinite(latency_ms)
        or latency_ms < 0
    ):
        raise CorruptRunError(f"{context} has an invalid latency_ms")


def _validate_metadata(raw: dict, run_id: str) -> None:
    """Validate envelope metadata and its identity against the artifact name."""

    if raw.get("schema_version") != SCHEMA_VERSION:
        raise UnsupportedSchemaVersionError(
            f"Run {run_id!r} has unsupported schema_version={raw.get('schema_version')!r}; "
            f"expected {SCHEMA_VERSION}"
        )
    if raw.get("run_id") != run_id:
        raise CorruptRunError(
            f"Run artifact {run_id!r} contains metadata for run_id={raw.get('run_id')!r}"
        )
    if not isinstance(raw.get("created_at"), str) or not raw["created_at"]:
        raise CorruptRunError(f"Run {run_id!r} metadata has an invalid created_at")
    for field_name in (
        "scenario_version",
        "agent_version",
        "config_fingerprint",
        "source_revision",
    ):
        value = raw.get(field_name)
        if value is not None and (not isinstance(value, str) or not value):
            raise CorruptRunError(f"Run {run_id!r} metadata has an invalid {field_name}")
    seed = raw.get("seed")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise CorruptRunError(f"Run {run_id!r} metadata has an invalid seed")
    for field_name in ("trust_threshold", "drift_threshold"):
        value = raw.get(field_name)
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(value)
            or not 0.0 <= value <= 1.0
        ):
            raise CorruptRunError(f"Run {run_id!r} metadata has an invalid {field_name}")


def _validate_nested_schemas(raw_vectors: list, run_id: str) -> None:
    """Reject vectors produced under unsupported schemas or normalization rules."""

    dimension_fields = tuple(dimension.value for dimension in VectorDimension)
    expected_vector_fields = {*dimension_fields, "schema_version"}
    expected_score_fields = {
        "dimension",
        "value",
        "available",
        "evidence_count",
        "evidence_total",
        "confidence",
        "evidence_references",
        "normalization_version",
    }
    for vector_index, raw_vector in enumerate(raw_vectors):
        if not isinstance(raw_vector, dict):
            raise CorruptRunError(f"Run {run_id!r} vector {vector_index} must be an object")
        if raw_vector.get("schema_version") != NORMALIZATION_VERSION:
            raise UnsupportedSchemaVersionError(
                f"Run {run_id!r} vector {vector_index} has unsupported schema_version="
                f"{raw_vector.get('schema_version')!r}"
            )
        if set(raw_vector) != expected_vector_fields:
            raise CorruptRunError(
                f"Run {run_id!r} vector {vector_index} has unexpected or missing fields"
            )
        for field_name in dimension_fields:
            raw_score = raw_vector.get(field_name)
            if not isinstance(raw_score, dict):
                raise CorruptRunError(
                    f"Run {run_id!r} vector {vector_index} is missing dimension {field_name!r}"
                )
            if raw_score.get("normalization_version") != NORMALIZATION_VERSION:
                raise UnsupportedSchemaVersionError(
                    f"Run {run_id!r} vector {vector_index} dimension {field_name!r} has "
                    f"unsupported normalization_version="
                    f"{raw_score.get('normalization_version')!r}"
                )
            if set(raw_score) != expected_score_fields:
                raise CorruptRunError(
                    f"Run {run_id!r} vector {vector_index} dimension {field_name!r} "
                    "has unexpected or missing fields"
                )


def _validate_raw_trajectories(raw_trajectories: list, run_id: str) -> None:
    """Validate serialized trajectory keys and identity value types."""

    expected_fields = {
        "run_id",
        "task_id",
        "family",
        "cluster_id",
        "suite_id",
        "suite_version",
        "suite_partition",
        "repeat_id",
        "scenario_name",
        "scenario_version",
        "agent_id",
        "agent_version",
        "steps",
        "outcome",
        "intervention_count",
        "policy_violation_count",
    }
    string_fields = {
        "run_id",
        "task_id",
        "family",
        "cluster_id",
        "suite_id",
        "suite_partition",
        "repeat_id",
        "scenario_name",
        "agent_id",
        "agent_version",
    }
    for trajectory_index, raw_trajectory in enumerate(raw_trajectories):
        if not isinstance(raw_trajectory, dict) or set(raw_trajectory) != expected_fields:
            raise CorruptRunError(
                f"Run {run_id!r} trajectory {trajectory_index} has unexpected or missing fields"
            )
        if any(
            not isinstance(raw_trajectory[field_name], str) or not raw_trajectory[field_name]
            for field_name in string_fields
        ):
            raise CorruptRunError(
                f"Run {run_id!r} trajectory {trajectory_index} has invalid identity fields"
            )


def _validate_evidence_alignment(
    metadata: RunMetadata,
    results: list[IterationResult],
    events: list[RunEvent],
    trajectories: list[Trajectory],
    vectors: list[ReliabilityVector],
) -> None:
    """Validate one-to-one ordered correlation across persisted evidence sections."""

    if not events and not trajectories and not vectors:
        return
    if (
        not results
        or len(results) != len(events)
        or len(results) != len(trajectories)
        or len(results) != len(vectors)
    ):
        raise CorruptRunError(
            "Run evidence requires equal non-zero result, event, trajectory, and vector counts"
        )

    result_task_ids = [result.task_id for result in results]
    event_task_ids = [event.task_id for event in events]
    trajectory_task_ids = [trajectory.task_id for trajectory in trajectories]
    if len(set(result_task_ids)) != len(result_task_ids):
        raise CorruptRunError("Run evidence contains duplicate task identities")
    if result_task_ids != event_task_ids or result_task_ids != trajectory_task_ids:
        raise CorruptRunError(
            "Run results, events, and trajectories must have identical ordered task identities"
        )

    for event, trajectory in zip(events, trajectories, strict=True):
        if trajectory.run_id != metadata.run_id:
            raise CorruptRunError(
                f"Trajectory {trajectory.task_id!r} belongs to run_id={trajectory.run_id!r}, "
                f"not {metadata.run_id!r}"
            )
        if (
            metadata.agent_version is not None
            and trajectory.agent_version != metadata.agent_version
        ):
            raise CorruptRunError(
                f"Trajectory {trajectory.task_id!r} agent version does not match run metadata"
            )
        expected_scenario = f"{trajectory.scenario_name}@{trajectory.scenario_version}"
        if metadata.scenario_version is not None and expected_scenario != metadata.scenario_version:
            raise CorruptRunError(
                f"Trajectory {trajectory.task_id!r} scenario version does not match run metadata"
            )
        if event != RunEvent.from_trajectory(trajectory):
            raise CorruptRunError(
                f"RunEvent {event.task_id!r} does not match its trajectory projection"
            )


def _is_legacy_summary(payload: Any) -> bool:
    """Return whether payload is a well-formed legacy write_results JSON list."""

    if not isinstance(payload, list):
        return False
    for index, raw_result in enumerate(payload):
        _validate_iteration_result(raw_result, context=f"Legacy result {index}")
    return True


class RunRepository:
    """Versioned, schema-tagged store for completed reliability runs.

    Each run is persisted as its own artifact keyed by an immutable run ID,
    rather than overwriting a single shared file.
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
        if not self._base_dir.is_dir():
            raise ValueError(f"Run repository base path must be a directory: {base_dir}")
        self._resolved_base_dir = self._base_dir.resolve()
        self._decision_dir = self._base_dir / "decisions"
        if self._decision_dir.is_symlink():
            raise ValueError(f"Decision directory must not be a symlink: {self._decision_dir}")
        self._decision_dir.mkdir(exist_ok=True)
        if not self._decision_dir.is_dir():
            raise ValueError(f"Decision repository path must be a directory: {self._decision_dir}")
        self._resolved_decision_dir = self._decision_dir.resolve()
        try:
            self._resolved_decision_dir.relative_to(self._resolved_base_dir)
        except ValueError as error:
            raise ValueError(
                f"Decision directory escapes the repository directory: {self._decision_dir}"
            ) from error

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
        trust_threshold: float | None = None,
        drift_threshold: float | None = None,
        events: list[RunEvent] | None = None,
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
            trust_threshold=trust_threshold,
            drift_threshold=drift_threshold,
        )
        resolved_trajectories = trajectories or []
        resolved_events = (
            events
            if events is not None
            else [RunEvent.from_trajectory(item) for item in resolved_trajectories]
        )
        payload = {
            "metadata": asdict(metadata),
            "results": [asdict(item) for item in results],
            "events": [asdict(item) for item in resolved_events],
            "trajectories": [asdict(item) for item in resolved_trajectories],
            "vectors": [asdict(item) for item in (vectors or [])],
        }
        serialized = json.dumps(payload, indent=2)
        self._record_from_payload(payload, resolved_run_id)
        run_path = self._run_path(resolved_run_id)
        if run_path.exists() and not run_path.is_file():
            raise ValueError(f"Run path must be a regular file: {run_path}")
        with run_path.open("x", encoding="utf-8") as run_file:
            run_file.write(serialized)
        return metadata

    def read_run(self, run_id: str) -> RunRecord:
        """Read a persisted run by its immutable run ID."""

        run_path = self._run_path(run_id)
        if not run_path.exists():
            raise RunNotFoundError(f"No run persisted for run_id={run_id!r}")
        if not run_path.is_file():
            raise ValueError(f"Run path must be a regular file: {run_path}")

        try:
            payload = json.loads(run_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            raise CorruptRunError(f"Run {run_id!r} payload is not valid JSON") from error

        return self._record_from_payload(payload, run_id)

    def _record_from_payload(self, payload: Any, run_id: str) -> RunRecord:
        """Validate and reconstruct one versioned run envelope."""

        if not isinstance(payload, dict):
            raise CorruptRunError(f"Run {run_id!r} payload must be a JSON object")
        raw_metadata = payload.get("metadata")
        if not isinstance(raw_metadata, dict):
            raise CorruptRunError(f"Run {run_id!r} payload is missing required metadata")
        _validate_metadata(raw_metadata, run_id)

        expected_sections = {"metadata", "results", "events", "trajectories", "vectors"}
        if set(payload) != expected_sections:
            raise CorruptRunError(
                f"Run {run_id!r} payload has unexpected or missing envelope sections"
            )

        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            raise CorruptRunError(
                f"Run {run_id!r} payload is missing required 'results' fields"
            )

        for result_index, raw_result in enumerate(raw_results):
            _validate_iteration_result(raw_result, context=f"Run {run_id!r} result {result_index}")

        raw_events = payload["events"]
        raw_trajectories = payload["trajectories"]
        raw_vectors = payload["vectors"]
        if (
            not isinstance(raw_events, list)
            or not isinstance(raw_trajectories, list)
            or not isinstance(raw_vectors, list)
        ):
            raise CorruptRunError(
                f"Run {run_id!r} payload has malformed evidence fields"
            )
        for event_index, raw_event in enumerate(raw_events):
            _validate_run_event(raw_event, context=f"Run {run_id!r} event {event_index}")
        _validate_raw_trajectories(raw_trajectories, run_id)
        _validate_nested_schemas(raw_vectors, run_id)

        try:
            metadata = RunMetadata(**raw_metadata)
            results = [IterationResult(**item) for item in raw_results]
            events = [RunEvent(**item) for item in raw_events]
            trajectories = [_trajectory_from_dict(item) for item in raw_trajectories]
            vectors = [_vector_from_dict(item) for item in raw_vectors]
        except (TypeError, KeyError, ValueError) as error:
            raise CorruptRunError(
                f"Run {run_id!r} payload has malformed metadata, results, trajectories, or vectors"
            ) from error

        _validate_evidence_alignment(metadata, results, events, trajectories, vectors)

        return RunRecord(
            metadata=metadata,
            results=results,
            events=events,
            trajectories=trajectories,
            vectors=vectors,
        )

    def list_runs(self) -> list[RunMetadata]:
        """List metadata for every persisted run, ordered deterministically by run ID."""

        metadata: list[RunMetadata] = []
        for path in sorted(self._base_dir.glob("*.json"), key=lambda candidate: candidate.name):
            run_path = self._checked_path(path.stem)
            if not run_path.exists() or not run_path.is_file():
                raise ValueError(f"Run path must be a regular file: {run_path}")
            try:
                payload = json.loads(run_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as error:
                raise CorruptRunError(f"Run {path.stem!r} payload is not valid JSON") from error
            if _is_legacy_summary(payload):
                continue
            if not isinstance(payload, dict):
                raise CorruptRunError(
                    f"JSON artifact {path.name!r} is neither a versioned run nor a legacy summary"
                )
            metadata.append(self._record_from_payload(payload, path.stem).metadata)
        return metadata

    def run_exists(self, run_id: str) -> bool:
        """Look up whether a run artifact exists for the given run ID."""

        run_path = self._run_path(run_id)
        if run_path.exists() and not run_path.is_file():
            raise ValueError(f"Run path must be a regular file: {run_path}")
        return run_path.exists()

    def write_gate_decision(self, decision: GateDecisionRecord) -> GateDecisionRecord:
        """Persist one immutable gate decision using exclusive-create semantics."""

        self._validate_gate_decision(decision)
        decision_path = self._decision_path(decision.decision_id)
        if decision_path.exists() and not decision_path.is_file():
            raise ValueError(f"Decision path must be a regular file: {decision_path}")
        serialized = json.dumps(asdict(decision), indent=2, sort_keys=True)
        with decision_path.open("x", encoding="utf-8") as decision_file:
            decision_file.write(serialized)
        return decision

    def read_gate_decision(self, decision_id: str) -> GateDecisionRecord:
        """Read and validate an immutable gate decision by its exclusive identity."""

        decision_path = self._decision_path(decision_id)
        if not decision_path.exists():
            raise GateDecisionNotFoundError(
                f"No gate decision persisted for decision_id={decision_id!r}"
            )
        if not decision_path.is_file():
            raise ValueError(f"Decision path must be a regular file: {decision_path}")
        try:
            payload = json.loads(decision_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as error:
            raise CorruptRunError(
                f"Gate decision {decision_id!r} payload is not valid JSON"
            ) from error
        return self._gate_decision_from_payload(payload, decision_id)

    def gate_decision_exists(self, decision_id: str) -> bool:
        """Return whether an immutable gate decision exists for the decision ID."""

        decision_path = self._decision_path(decision_id)
        if decision_path.exists() and not decision_path.is_file():
            raise ValueError(f"Decision path must be a regular file: {decision_path}")
        return decision_path.exists()

    def _gate_decision_from_payload(
        self, payload: Any, decision_id: str
    ) -> GateDecisionRecord:
        """Validate and reconstruct one versioned gate decision envelope."""

        if not isinstance(payload, dict) or set(payload) != {
            item.name for item in fields(GateDecisionRecord)
        }:
            raise CorruptRunError(
                f"Gate decision {decision_id!r} has unexpected or missing fields"
            )
        if payload.get("decision_id") != decision_id:
            raise CorruptRunError(
                f"Decision artifact {decision_id!r} contains decision_id="
                f"{payload.get('decision_id')!r}"
            )
        if payload.get("schema_version") != GATE_DECISION_SCHEMA_VERSION:
            raise UnsupportedSchemaVersionError(
                f"Gate decision {decision_id!r} has unsupported schema_version="
                f"{payload.get('schema_version')!r}; expected {GATE_DECISION_SCHEMA_VERSION}"
            )
        try:
            decision = GateDecisionRecord(
                **{
                    **payload,
                    "dimension_rationale": tuple(payload["dimension_rationale"]),
                    "critical_override_reasons": tuple(payload["critical_override_reasons"]),
                    "held_out_suite_reasons": tuple(payload["held_out_suite_reasons"]),
                    "required_evidence_reasons": tuple(payload["required_evidence_reasons"]),
                    "non_critical_warning_reasons": tuple(
                        payload["non_critical_warning_reasons"]
                    ),
                    "error_budget_reasons": tuple(payload["error_budget_reasons"]),
                }
            )
        except (KeyError, TypeError, ValueError) as error:
            raise CorruptRunError(
                f"Gate decision {decision_id!r} payload is malformed"
            ) from error
        try:
            self._validate_gate_decision(decision)
        except ValueError as error:
            raise CorruptRunError(
                f"Gate decision {decision_id!r} payload is malformed: {error}"
            ) from error
        return decision

    @staticmethod
    def _validate_gate_decision(decision: GateDecisionRecord) -> None:
        """Validate gate-decision identity and required reconstructability fields."""

        if decision.schema_version != GATE_DECISION_SCHEMA_VERSION:
            raise UnsupportedSchemaVersionError(
                f"Unsupported gate decision schema_version={decision.schema_version!r}"
            )
        for identifier in (
            decision.decision_id,
            decision.baseline_run_id,
            decision.candidate_run_id,
        ):
            _validate_run_id(identifier)
        if decision.production_history_run_id is not None:
            _validate_run_id(decision.production_history_run_id)
        if not decision.created_at or not decision.policy_version or not decision.rationale_version:
            raise ValueError("Gate decisions require timestamps and versioned rationale/policy")
        if decision.verdict not in {"pass", "warn", "block"}:
            raise ValueError(f"Unsupported gate verdict: {decision.verdict!r}")
        for snapshot_name, snapshot, fingerprint in (
            ("policy_snapshot", decision.policy_snapshot, decision.policy_fingerprint),
            ("suite_snapshot", decision.suite_snapshot, decision.suite_fingerprint),
        ):
            if not isinstance(fingerprint, str) or not re.fullmatch(
                r"sha256:[0-9a-f]{64}", fingerprint
            ):
                raise ValueError("Gate decision fingerprints must be canonical sha256 values")
            if not isinstance(snapshot, dict):
                raise ValueError(f"Gate decision {snapshot_name} must be a JSON object")
            try:
                computed_fingerprint = canonical_json_fingerprint(snapshot)
            except ValueError as error:
                raise ValueError(
                    f"Gate decision {snapshot_name} is not JSON-compatible: {error}"
                ) from error
            if fingerprint != computed_fingerprint:
                raise ValueError(
                    f"Gate decision {snapshot_name} fingerprint mismatch: "
                    f"stored {fingerprint!r}, computed {computed_fingerprint!r}"
                )

    def _run_path(self, run_id: str) -> Path:
        _validate_run_id(run_id)
        return self._checked_path(run_id)

    def _decision_path(self, decision_id: str) -> Path:
        """Build a confined decision path and reject symlink escapes."""

        _validate_run_id(decision_id)
        if self._decision_dir.is_symlink():
            raise ValueError(f"Decision directory must not be a symlink: {self._decision_dir}")
        candidate = self._decision_dir / f"{decision_id}.json"
        if candidate.is_symlink():
            raise ValueError(f"Decision path must not be a symlink: {candidate}")
        resolved_candidate = candidate.resolve()
        try:
            resolved_candidate.relative_to(self._resolved_decision_dir)
        except ValueError as error:
            raise ValueError(
                f"Decision path escapes the repository directory: {candidate}"
            ) from error
        return candidate

    def _checked_path(self, run_id: str) -> Path:
        """Build a run path and reject symlink or resolved-path escapes."""

        _validate_run_id(run_id)
        candidate = self._base_dir / f"{run_id}.json"
        if candidate.is_symlink():
            raise ValueError(f"Run path must not be a symlink: {candidate}")
        resolved_candidate = candidate.resolve()
        try:
            resolved_candidate.relative_to(self._resolved_base_dir)
        except ValueError as error:
            raise ValueError(f"Run path escapes the repository directory: {candidate}") from error
        return candidate


def _generate_run_id() -> str:
    """Generate a sortable, unique run identifier from a UTC timestamp and random suffix."""

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    return f"{timestamp}-{uuid4().hex[:8]}"


def _validate_run_id(run_id: str) -> None:
    """Reject run IDs that could escape the repository directory."""

    reserved_name = run_id.split(".", maxsplit=1)[0].upper() if run_id else ""
    if (
        not run_id
        or len(run_id) > _MAX_RUN_ID_LENGTH
        or run_id in {".", ".."}
        or run_id.endswith(".")
        or reserved_name in _WINDOWS_RESERVED_NAMES
        or not _VALID_RUN_ID_PATTERN.fullmatch(run_id)
    ):
        raise ValueError(
            "run_id must be a safe non-reserved identifier of at most 250 letters, digits, "
            "'.', '_', or '-' characters; "
            f"got {run_id!r}"
        )
