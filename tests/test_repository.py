"""Unit tests for the versioned run repository."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from arise_x.evaluation.runner import IterationResult
from arise_x.fingerprints import canonical_json_fingerprint
from arise_x.storage.repository import (
    GATE_DECISION_SCHEMA_VERSION,
    SCHEMA_VERSION,
    CorruptRunError,
    GateDecisionNotFoundError,
    GateDecisionRecord,
    RunNotFoundError,
    RunRepository,
    UnsupportedSchemaVersionError,
    write_results,
)
from arise_x.telemetry.events import RunEvent
from arise_x.telemetry.trajectory import (
    ContentKind,
    Outcome,
    OutcomeStatus,
    RedactedContent,
    Step,
    Trajectory,
    UsageMetrics,
)
from arise_x.trust.vector import (
    ConfidenceMetadata,
    DimensionScore,
    ReliabilityVector,
    VectorDimension,
)


def _sample_results() -> list[IterationResult]:
    return [
        IterationResult(
            task_id="task-1",
            disruption="baseline",
            drift_score=0.1,
            trust_score=0.9,
            trustworthy=True,
        ),
        IterationResult(
            task_id="task-2",
            disruption="latency_spike",
            drift_score=0.4,
            trust_score=0.6,
            trustworthy=False,
        ),
    ]


def _sample_trajectory(task_id: str = "task-1") -> Trajectory:
    step = Step(
        index=0,
        action="run_task",
        state_transition="dispatched->completed",
        usage=UsageMetrics(
            latency_ms=120.0, prompt_tokens=10, completion_tokens=5, cost_usd=0.001
        ),
        prompt_text=RedactedContent(
            kind=ContentKind.PROMPT,
            reference_id=f"trajectory:run-1:{task_id}:step:0:prompt",
        ),
        output_text=RedactedContent(
            kind=ContentKind.OUTPUT,
            reference_id=f"trajectory:run-1:{task_id}:step:0:output",
        ),
    )
    return Trajectory(
        run_id="run-1",
        task_id=task_id,
        family="procurement",
        cluster_id="vendor-comparison",
        suite_id="procurement-baseline-suite",
        suite_version=1,
        suite_partition="development",
        repeat_id="seed-42",
        scenario_name="procurement-baseline",
        scenario_version=1,
        agent_id="ScriptedAgent",
        agent_version="scripted-agent-v1",
        steps=(step,),
        outcome=Outcome(
            goal_achieved=True,
            label="goal_achieved",
            status=OutcomeStatus.SUCCEEDED,
            terminal_state="completed",
            evidence_references=(f"trajectory:run-1:{task_id}:outcome",),
        ),
    )


def _sample_vector() -> ReliabilityVector:
    def score(dimension: VectorDimension, value: float) -> DimensionScore:
        return DimensionScore(
            dimension=dimension,
            value=value,
            available=True,
            evidence_count=1,
            evidence_total=1,
            confidence=ConfidenceMetadata(score=1.0, method="direct_observation"),
            evidence_references=(f"trajectory:run-1:task-1:{dimension.value}",),
        )

    return ReliabilityVector(
        goal_success=score(VectorDimension.GOAL_SUCCESS, 1.0),
        resilience=score(VectorDimension.RESILIENCE, 1.0),
        behavioral_stability=DimensionScore.unavailable(VectorDimension.BEHAVIORAL_STABILITY),
        recovery=DimensionScore.unavailable(VectorDimension.RECOVERY),
        safety=score(VectorDimension.SAFETY, 1.0),
        efficiency=score(VectorDimension.EFFICIENCY, 0.9),
        cost=score(VectorDimension.COST, 0.95),
        autonomy=score(VectorDimension.AUTONOMY, 1.0),
    )


def _sample_gate_decision(decision_id: str = "decision-1") -> GateDecisionRecord:
    """Build one reconstructable decision fixture without raw trajectory content."""

    policy_snapshot = {"version": "gate-v1", "alpha": 0.02}
    suite_snapshot = {"suite_id": "suite-1", "version": 1}
    return GateDecisionRecord(
        decision_id=decision_id,
        schema_version=GATE_DECISION_SCHEMA_VERSION,
        created_at="2026-09-22T00:00:00+00:00",
        baseline_run_id="baseline",
        candidate_run_id="candidate",
        production_history_run_id="production",
        policy_version="gate-v1",
        policy_fingerprint=canonical_json_fingerprint(policy_snapshot),
        policy_snapshot=policy_snapshot,
        suite_version=1,
        suite_fingerprint=canonical_json_fingerprint(suite_snapshot),
        suite_snapshot=suite_snapshot,
        verdict="pass",
        geometric_ari=1.0,
        dimension_rationale=({"dimension": "goal_success", "effect_size": 0.0},),
        critical_override_reasons=(),
        held_out_suite_reasons=(),
        required_evidence_reasons=(),
        non_critical_warning_reasons=(),
        error_budget_reasons=(),
        error_budget={"eligible_count": 30, "allowed_bad": 1.5},
        window_inputs={"window_days": 28, "window_end": "2026-09-22T00:00:00+00:00"},
    )


def test_given_written_run_when_read_run_then_results_round_trip(tmp_path) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    results = _sample_results()
    repository.write_run(results, run_id="run-1")

    # Act
    record = repository.read_run("run-1")

    # Assert
    assert record.results == results


def test_given_metadata_fields_when_write_run_then_persists_provided_metadata(tmp_path) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    results = _sample_results()

    # Act
    metadata = repository.write_run(
        results,
        run_id="run-2",
        scenario_version="scenario-1.0",
        agent_version="agent-1.0",
        config_fingerprint="fingerprint-abc",
        seed=42,
        source_revision="deadbeef",
        trust_threshold=0.8,
        drift_threshold=0.2,
    )
    record = repository.read_run("run-2")

    # Assert
    assert record.metadata == metadata
    assert record.metadata.schema_version == SCHEMA_VERSION
    assert record.metadata.scenario_version == "scenario-1.0"
    assert record.metadata.agent_version == "agent-1.0"
    assert record.metadata.config_fingerprint == "fingerprint-abc"
    assert record.metadata.seed == 42
    assert record.metadata.source_revision == "deadbeef"
    assert record.metadata.trust_threshold == pytest.approx(0.8)
    assert record.metadata.drift_threshold == pytest.approx(0.2)


def test_given_no_run_id_when_write_run_then_generates_unique_run_id(tmp_path) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    results = _sample_results()

    # Act
    first_metadata = repository.write_run(results)
    second_metadata = repository.write_run(results)

    # Assert
    assert first_metadata.run_id != second_metadata.run_id


def test_given_multiple_runs_when_list_runs_then_returns_deterministic_ordering(tmp_path) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    results = _sample_results()
    repository.write_run(results, run_id="run-b")
    repository.write_run(results, run_id="run-a")
    repository.write_run(results, run_id="run-c")

    # Act
    listed_run_ids = [metadata.run_id for metadata in repository.list_runs()]

    # Assert
    assert listed_run_ids == ["run-a", "run-b", "run-c"]


def test_given_missing_run_id_when_read_run_then_raises_run_not_found_error(tmp_path) -> None:
    # Arrange
    repository = RunRepository(tmp_path)

    # Act & Assert
    with pytest.raises(RunNotFoundError):
        repository.read_run("does-not-exist")


def test_given_invalid_json_when_read_run_then_raises_corrupt_run_error(tmp_path) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    (tmp_path / "broken.json").write_text("{not valid json", encoding="utf-8")

    # Act & Assert
    with pytest.raises(CorruptRunError):
        repository.read_run("broken")


def test_given_unsupported_schema_version_when_read_run_then_raises_unsupported_schema_error(
    tmp_path,
) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    payload = {
        "metadata": {
            "run_id": "old-run",
            "schema_version": SCHEMA_VERSION + 1,
            "created_at": "2020-01-01T00:00:00+00:00",
        },
        "results": [],
    }
    (tmp_path / "old-run.json").write_text(json.dumps(payload), encoding="utf-8")

    # Act & Assert
    with pytest.raises(UnsupportedSchemaVersionError):
        repository.read_run("old-run")


def test_given_pre_trajectory_schema_version_when_read_run_then_raises_unsupported_schema_error(
    tmp_path,
) -> None:
    # Arrange: schema_version=1 predates trajectory/vector persistence support; runs
    # written under that schema are rejected rather than silently upgraded.
    repository = RunRepository(tmp_path)
    payload = {
        "metadata": {
            "run_id": "legacy-run",
            "schema_version": 1,
            "created_at": "2026-01-01T00:00:00+00:00",
        },
        "results": [],
    }
    (tmp_path / "legacy-run.json").write_text(json.dumps(payload), encoding="utf-8")

    # Act & Assert
    with pytest.raises(UnsupportedSchemaVersionError):
        repository.read_run("legacy-run")


def test_given_current_schema_with_missing_event_section_when_read_then_rejects(tmp_path) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    repository.write_run([], run_id="run-1")
    path = tmp_path / "run-1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    del payload["events"]
    path.write_text(json.dumps(payload), encoding="utf-8")

    # Act & Assert
    with pytest.raises(CorruptRunError, match="envelope sections"):
        repository.read_run("run-1")


def test_given_trajectories_and_vectors_when_write_and_read_run_then_round_trips(tmp_path) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    results = _sample_results()[:1]
    trajectories = [_sample_trajectory()]
    vectors = [_sample_vector()]
    events = [RunEvent.from_trajectory(trajectories[0])]

    # Act
    repository.write_run(
        results,
        run_id="run-1",
        events=events,
        trajectories=trajectories,
        vectors=vectors,
    )
    record = repository.read_run("run-1")

    # Assert
    assert record.trajectories == trajectories
    assert record.vectors == vectors
    assert record.events == events


def test_given_no_trajectories_or_vectors_when_write_run_then_read_run_returns_empty_lists(
    tmp_path,
) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    results = _sample_results()

    # Act
    repository.write_run(results, run_id="run-without-evidence")
    record = repository.read_run("run-without-evidence")

    # Assert
    assert record.trajectories == []
    assert record.vectors == []


def test_given_existing_callers_when_write_results_then_persists_legacy_json_list(tmp_path) -> None:
    # Arrange
    output_path = tmp_path / "legacy" / "results.json"
    results = _sample_results()

    # Act
    write_results(output_path, results)
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    # Assert
    assert payload == [
        {
            "task_id": "task-1",
            "disruption": "baseline",
            "drift_score": 0.1,
            "trust_score": 0.9,
            "trustworthy": True,
        },
        {
            "task_id": "task-2",
            "disruption": "latency_spike",
            "drift_score": 0.4,
            "trust_score": 0.6,
            "trustworthy": False,
        },
    ]


def test_given_existing_run_when_rewritten_then_original_bytes_remain(tmp_path) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    repository.write_run(_sample_results(), run_id="run-1", seed=1)
    original = (tmp_path / "run-1.json").read_bytes()

    # Act & Assert
    with pytest.raises(FileExistsError):
        repository.write_run([], run_id="run-1", seed=2)
    assert (tmp_path / "run-1.json").read_bytes() == original


def test_given_competing_writers_when_creating_run_then_only_one_succeeds(tmp_path) -> None:
    # Arrange
    repository = RunRepository(tmp_path)

    def write(seed: int) -> int | None:
        try:
            repository.write_run([], run_id="shared", seed=seed)
        except FileExistsError:
            return None
        return seed

    # Act
    with ThreadPoolExecutor(max_workers=4) as pool:
        winners = [seed for seed in pool.map(write, range(4)) if seed is not None]

    # Assert
    assert len(winners) == 1
    assert repository.read_run("shared").metadata.seed == winners[0]


@pytest.mark.parametrize("operation", ["read_run", "run_exists", "write_run"])
@pytest.mark.parametrize(
    "run_id",
    [
        "", ".", "..", "../neighbor", "..\\neighbor", "/absolute", "C:\\absolute",
        "C:relative", "\\\\server\\share", "run:stream", "trailing.", "with space",
        "CON", "nul", "AUX.backup", "PRN", "COM1", "lpt9", "a" * 251, "bad\n",
    ],
)
def test_given_unsafe_id_when_accessing_run_then_rejects(tmp_path, operation, run_id) -> None:
    # Arrange
    repository = RunRepository(tmp_path)

    # Act & Assert
    with pytest.raises(ValueError):
        if operation == "write_run":
            repository.write_run([], run_id=run_id)
        else:
            getattr(repository, operation)(run_id)


def test_given_missing_or_written_run_when_lookup_then_returns_existence(tmp_path) -> None:
    # Arrange
    repository = RunRepository(tmp_path)

    # Act & Assert
    assert repository.run_exists("run-1") is False
    repository.write_run([], run_id="run-1")
    assert repository.run_exists("run-1") is True


@pytest.mark.parametrize("operation", ["read_run", "run_exists", "write_run", "list_runs"])
@pytest.mark.parametrize("target_exists", [True, False])
def test_given_symlink_when_accessing_run_then_rejects_without_touching_target(
    tmp_path, operation, target_exists
) -> None:
    # Arrange
    repository = RunRepository(tmp_path / "runs")
    target = tmp_path / "neighbor.json"
    if target_exists:
        target.write_bytes(b"external sentinel")
    try:
        (tmp_path / "runs" / "linked.json").symlink_to(target)
    except OSError as error:
        if getattr(error, "winerror", None) == 1314:
            pytest.skip("Windows symlink privilege is unavailable")
        raise

    # Act & Assert
    with pytest.raises(ValueError, match="path|symlink|directory"):
        if operation == "write_run":
            repository.write_run([], run_id="linked")
        elif operation == "list_runs":
            repository.list_runs()
        else:
            getattr(repository, operation)("linked")
    assert target.read_bytes() == b"external sentinel" if target_exists else not target.exists()


def test_given_legacy_summaries_when_listing_then_only_versioned_runs_are_returned(
    tmp_path,
) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    repository.write_run([], run_id="run-1")
    write_results(tmp_path / "latest-run.json", _sample_results())
    write_results(tmp_path / "empty-summary.json", [])

    # Act & Assert
    assert [metadata.run_id for metadata in repository.list_runs()] == ["run-1"]
    with pytest.raises(CorruptRunError):
        repository.read_run("latest-run")


@pytest.mark.parametrize("payload", [{}, [42], [{"task_id": "task-1"}], [
    {**asdict(_sample_results()[0]), "trustworthy": "yes"},
], {"metadata": {"schema_version": SCHEMA_VERSION}, "results": []}])
def test_given_unrecognized_json_when_listing_then_does_not_silently_skip(
    tmp_path, payload,
) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    (tmp_path / "latest-run.json").write_text(json.dumps(payload), encoding="utf-8")

    # Act & Assert
    with pytest.raises(CorruptRunError):
        repository.list_runs()


@pytest.fixture
def evidence_payload(tmp_path) -> dict:
    """A valid persisted envelope that tests can corrupt without bypassing a write failure."""
    repository = RunRepository(tmp_path)
    repository.write_run(
        _sample_results()[:1], run_id="run-1",
        trajectories=[_sample_trajectory()], vectors=[_sample_vector()],
    )
    return json.loads((tmp_path / "run-1.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("field", ["schema_version", "normalization_version"])
@pytest.mark.parametrize("version", ["unsupported-v99", None])
def test_given_unsupported_nested_schema_when_read_then_rejects(
    tmp_path, evidence_payload, field, version
) -> None:
    # Arrange
    raw = evidence_payload["vectors"][0]
    if field == "normalization_version":
        raw = raw["safety"]
    if version is None:
        del raw[field]
    else:
        raw[field] = version
    (tmp_path / "run-1.json").write_text(json.dumps(evidence_payload), encoding="utf-8")

    # Act & Assert
    with pytest.raises(UnsupportedSchemaVersionError):
        RunRepository(tmp_path).read_run("run-1")


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("metadata", "run_id", "other-run"),
        ("trajectories", "run_id", "other-run"),
        ("trajectories", "task_id", "other-task"),
        ("trajectories", "suite_id", 42),
        ("trajectories", "repeat_id", []),
        ("trajectories", "schema_version", "unsupported-v99"),
        ("vectors", "task_id", "other-task"),
    ],
)
def test_given_identity_or_contract_mismatch_when_read_then_rejects(
    tmp_path, evidence_payload, section, field, value
) -> None:
    # Arrange
    raw = evidence_payload[section]
    if isinstance(raw, list):
        raw = raw[0]
    raw[field] = value
    (tmp_path / "run-1.json").write_text(json.dumps(evidence_payload), encoding="utf-8")

    # Act & Assert
    with pytest.raises(CorruptRunError):
        RunRepository(tmp_path).read_run("run-1")


@pytest.mark.parametrize("section", ["results", "events", "trajectories", "vectors"])
def test_given_incomplete_evidence_when_read_then_rejects(
    tmp_path, evidence_payload, section,
) -> None:
    # Arrange
    evidence_payload[section] = []
    (tmp_path / "run-1.json").write_text(json.dumps(evidence_payload), encoding="utf-8")

    # Act & Assert
    with pytest.raises(CorruptRunError):
        RunRepository(tmp_path).read_run("run-1")


def test_given_raw_prompt_in_persisted_trajectory_when_read_then_rejects(
    tmp_path,
    evidence_payload,
) -> None:
    # Arrange
    evidence_payload["trajectories"][0]["steps"][0]["prompt_text"] = "raw secret"
    (tmp_path / "run-1.json").write_text(
        json.dumps(evidence_payload),
        encoding="utf-8",
    )

    # Act & Assert
    with pytest.raises(CorruptRunError):
        RunRepository(tmp_path).read_run("run-1")


@pytest.mark.parametrize("mismatch", ["run", "task", "count", "vector-schema", "normalization"])
def test_given_invalid_evidence_when_write_then_rejects_before_creating_file(
    tmp_path, mismatch,
) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    trajectory = _sample_trajectory()
    vector = _sample_vector()
    results = _sample_results()[:1]
    if mismatch == "run":
        trajectory = replace(trajectory, run_id="other-run")
    elif mismatch == "task":
        trajectory = replace(trajectory, task_id="other-task")
    elif mismatch == "count":
        results = _sample_results()

    # Act & Assert
    with pytest.raises((CorruptRunError, UnsupportedSchemaVersionError, ValueError)):
        if mismatch == "vector-schema":
            vector = replace(vector, schema_version="unsupported-v99")
        elif mismatch == "normalization":
            vector = replace(
                vector,
                safety=replace(vector.safety, normalization_version="v99"),
            )
        repository.write_run(results, run_id="run-1", trajectories=[trajectory], vectors=[vector])
    assert not (tmp_path / "run-1.json").exists()


def test_given_unserializable_result_when_write_then_does_not_reserve_id(tmp_path) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    invalid = replace(_sample_results()[0], disruption=Path("not-json"))

    # Act & Assert
    with pytest.raises((TypeError, CorruptRunError)):
        repository.write_run([invalid], run_id="run-1")
    assert not (tmp_path / "run-1.json").exists()
    repository.write_run([], run_id="run-1")
    assert repository.read_run("run-1").results == []


@pytest.mark.parametrize("operation", ["read_run", "run_exists", "write_run"])
@pytest.mark.parametrize("guard", ["symlink", "escape"])
def test_given_unsafe_resolved_path_when_accessing_then_rejects(
    tmp_path, monkeypatch, operation, guard,
) -> None:
    # Arrange: exercise guards even on hosts without permission to create symlinks.
    repository = RunRepository(tmp_path)
    original_resolve = Path.resolve
    original_is_symlink = Path.is_symlink
    target = tmp_path / "run-1.json"
    if guard == "escape":
        monkeypatch.setattr(
            Path, "resolve",
            lambda path: tmp_path.parent / "outside.json" if path == target
            else original_resolve(path),
        )
    else:
        monkeypatch.setattr(
            Path, "is_symlink", lambda path: path == target or original_is_symlink(path),
        )

    # Act & Assert
    with pytest.raises(ValueError, match="path"):
        if operation == "write_run":
            repository.write_run([], run_id="run-1")
        else:
            getattr(repository, operation)("run-1")


@pytest.mark.parametrize("operation", ["read_run", "run_exists", "write_run", "list_runs"])
def test_given_directory_at_run_path_when_accessing_then_rejects(tmp_path, operation) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    (tmp_path / "run-1.json").mkdir()

    # Act & Assert
    with pytest.raises(ValueError, match="regular file"):
        if operation == "write_run":
            repository.write_run([], run_id="run-1")
        elif operation == "list_runs":
            repository.list_runs()
        else:
            getattr(repository, operation)("run-1")


@pytest.mark.parametrize("mismatch", ["order", "duplicates", "agent", "scenario"])
@pytest.mark.parametrize("operation", ["read", "write"])
def test_given_misaligned_correlation_when_persisting_then_rejects(
    tmp_path, mismatch, operation,
) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    results = _sample_results()
    trajectories = [_sample_trajectory(result.task_id) for result in results]
    vectors = [_sample_vector(), _sample_vector()]
    if mismatch == "order":
        trajectories.reverse()
    elif mismatch == "duplicates":
        results[1] = results[0]
        trajectories[1] = trajectories[0]
    elif mismatch == "agent":
        trajectories[0] = replace(trajectories[0], agent_version="other-agent")
    else:
        trajectories[0] = replace(trajectories[0], scenario_version=2)
    metadata = {
        "run_id": "run-1", "schema_version": SCHEMA_VERSION,
        "created_at": "2026-09-09T00:00:00+00:00",
        "agent_version": "scripted-agent-v1", "scenario_version": "procurement-baseline@1",
    }
    if operation == "read":
        payload = {
            "metadata": metadata, "results": [asdict(result) for result in results],
            "trajectories": [asdict(trajectory) for trajectory in trajectories],
            "vectors": [asdict(vector) for vector in vectors],
        }
        (tmp_path / "run-1.json").write_text(json.dumps(payload), encoding="utf-8")

    # Act & Assert
    with pytest.raises(CorruptRunError):
        if operation == "read":
            repository.read_run("run-1")
        else:
            repository.write_run(
                results, run_id="run-1", trajectories=trajectories, vectors=vectors,
                agent_version="scripted-agent-v1", scenario_version="procurement-baseline@1",
            )
    if operation == "write":
        assert not (tmp_path / "run-1.json").exists()


def test_given_full_correlated_evidence_when_round_trip_then_preserves_record(tmp_path) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    results = _sample_results()
    trajectories = [_sample_trajectory(result.task_id) for result in results]
    vectors = [_sample_vector(), _sample_vector()]

    # Act
    metadata = repository.write_run(
        results, run_id="run-1", trajectories=trajectories, vectors=vectors,
        scenario_version="procurement-baseline@1", agent_version="scripted-agent-v1", seed=42,
    )
    record = repository.read_run("run-1")

    # Assert
    assert record.metadata == metadata
    assert record.results == results
    assert record.trajectories == trajectories
    assert record.vectors == vectors


@pytest.mark.parametrize("operation", ["read_run", "list_runs"])
def test_given_versioned_corruption_with_legacy_summary_when_reading_then_rejects(
    tmp_path, operation,
) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    repository.write_run([], run_id="old")
    path = tmp_path / "old.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["metadata"]["schema_version"] = 1
    path.write_text(json.dumps(payload), encoding="utf-8")
    write_results(tmp_path / "latest-run.json", [])

    # Act & Assert
    with pytest.raises(UnsupportedSchemaVersionError):
        if operation == "read_run":
            repository.read_run("old")
        else:
            repository.list_runs()


def test_given_existing_legacy_file_when_write_results_then_keeps_overwrite_behavior(
    tmp_path,
) -> None:
    # Arrange
    path = tmp_path / "latest-run.json"
    write_results(path, _sample_results())

    # Act
    write_results(path, [])

    # Assert
    assert json.loads(path.read_text(encoding="utf-8")) == []


def test_given_gate_decision_when_written_then_round_trips_reconstructable_record(tmp_path) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    decision = _sample_gate_decision()

    # Act
    repository.write_gate_decision(decision)
    restored = repository.read_gate_decision(decision.decision_id)

    # Assert
    assert restored == decision
    assert repository.gate_decision_exists(decision.decision_id)
    assert repository.list_runs() == []


def test_given_persisted_gate_decision_when_policy_snapshot_tampered_then_rejected(
    tmp_path,
) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    decision = _sample_gate_decision()
    repository.write_gate_decision(decision)
    path = tmp_path / "decisions" / "decision-1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["policy_snapshot"]["alpha"] = 0.03
    path.write_text(json.dumps(payload), encoding="utf-8")

    # Act & Assert
    with pytest.raises(CorruptRunError, match="policy_snapshot fingerprint mismatch"):
        repository.read_gate_decision(decision.decision_id)


def test_given_persisted_gate_decision_when_suite_snapshot_tampered_then_rejected(
    tmp_path,
) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    decision = _sample_gate_decision()
    repository.write_gate_decision(decision)
    path = tmp_path / "decisions" / "decision-1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["suite_snapshot"]["version"] = 2
    path.write_text(json.dumps(payload), encoding="utf-8")

    # Act & Assert
    with pytest.raises(CorruptRunError, match="suite_snapshot fingerprint mismatch"):
        repository.read_gate_decision(decision.decision_id)


def test_given_persisted_gate_decision_when_snapshot_is_not_json_then_rejected(
    tmp_path,
) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    decision = _sample_gate_decision()
    repository.write_gate_decision(decision)
    path = tmp_path / "decisions" / "decision-1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["policy_snapshot"]["alpha"] = float("nan")
    path.write_text(json.dumps(payload), encoding="utf-8")

    # Act & Assert
    with pytest.raises(
        CorruptRunError,
        match="policy_snapshot is not JSON-compatible",
    ):
        repository.read_gate_decision(decision.decision_id)


def test_given_existing_gate_decision_when_rewritten_then_original_bytes_remain(tmp_path) -> None:
    # Arrange
    repository = RunRepository(tmp_path)
    decision = _sample_gate_decision()
    repository.write_gate_decision(decision)
    path = tmp_path / "decisions" / "decision-1.json"
    original = path.read_bytes()

    # Act & Assert
    with pytest.raises(FileExistsError):
        repository.write_gate_decision(replace(decision, verdict="block"))
    assert path.read_bytes() == original


def test_given_unknown_or_unsafe_decision_when_accessed_then_fails_safely(tmp_path) -> None:
    # Arrange
    repository = RunRepository(tmp_path)

    # Act & Assert
    with pytest.raises(GateDecisionNotFoundError):
        repository.read_gate_decision("missing")
    with pytest.raises(ValueError):
        repository.read_gate_decision("../outside")
