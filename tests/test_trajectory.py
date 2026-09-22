"""Unit tests for immutable trajectory evidence."""

from __future__ import annotations

import dataclasses

import pytest

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
    TrajectoryValidationError,
    UsageMetrics,
)

_IDENTITY_FIELDS = (
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
)


def _make_step(
    index: int,
    *,
    fault_id: str | None = None,
    verified: bool = False,
    latency_ms: float = 100.0,
) -> Step:
    fault = (
        FaultTrigger(
            fault_id=fault_id,
            verified=verified,
            affected_evidence_references=(f"step:{index}:fault",) if verified else (),
        )
        if fault_id
        else None
    )
    recovery = (
        RecoveryEvidence(
            fault_id=fault_id,
            action="retry",
            successful=True,
            evidence_references=[f"step:{index}:recovery"],
        )
        if fault_id and verified
        else None
    )
    return Step(
        index=index,
        action="decide",
        state_transition="idle->searching",
        tool=ToolInvocation(
            call_id=f"call-{index}",
            name="search_tool",
            call_payload=RedactedContent(
                kind=ContentKind.TOOL_PAYLOAD,
                reference_id=f"step:{index}:tool-payload",
            ),
            response_payload=RedactedContent(
                kind=ContentKind.TOOL_RESPONSE,
                reference_id=f"step:{index}:tool-response",
            ),
        ),
        fault=fault,
        recovered=verified,
        recovery=recovery,
        usage=UsageMetrics(
            latency_ms=latency_ms, prompt_tokens=10, completion_tokens=5, cost_usd=0.01
        ),
    )


def _make_trajectory(*, steps: tuple[Step, ...] | None = None, **overrides: object) -> Trajectory:
    defaults: dict[str, object] = {
        "run_id": "run-1",
        "task_id": "task-1",
        "family": "procurement",
        "cluster_id": "vendor-comparison",
        "suite_id": "procurement-suite",
        "suite_version": 1,
        "suite_partition": "development",
        "repeat_id": "seed-42",
        "scenario_name": "procurement-baseline",
        "scenario_version": 1,
        "agent_id": "scripted-agent",
        "agent_version": "1.0.0",
        "steps": steps if steps is not None else (_make_step(0),),
        "outcome": Outcome(
            goal_achieved=True,
            label="purchase_order_created",
            status=OutcomeStatus.SUCCEEDED,
            terminal_state="searching",
            evidence_references=["trajectory:outcome"],
        ),
    }
    defaults.update(overrides)
    return Trajectory(**defaults)  # type: ignore[arg-type]


def test_given_ordered_steps_when_construct_trajectory_then_succeeds() -> None:
    # Arrange
    steps = (_make_step(0), _make_step(1), _make_step(2))

    # Act
    trajectory = _make_trajectory(steps=steps)

    # Assert
    assert len(trajectory.steps) == 3


def test_given_valid_fields_when_construct_trajectory_then_identifiers_preserved() -> None:
    # Arrange & Act
    trajectory = _make_trajectory()

    # Assert
    assert trajectory.run_id == "run-1"
    assert trajectory.task_id == "task-1"
    assert trajectory.family == "procurement"
    assert trajectory.cluster_id == "vendor-comparison"
    assert trajectory.suite_id == "procurement-suite"
    assert trajectory.suite_version == 1
    assert trajectory.suite_partition == "development"
    assert trajectory.repeat_id == "seed-42"
    assert trajectory.scenario_name == "procurement-baseline"
    assert trajectory.agent_id == "scripted-agent"
    assert trajectory.agent_version == "1.0.0"


@pytest.mark.parametrize("field_name", _IDENTITY_FIELDS)
def test_given_empty_identifier_when_construct_trajectory_then_raises(field_name: str) -> None:
    # Act & Assert
    with pytest.raises(TrajectoryValidationError):
        _make_trajectory(**{field_name: ""})


@pytest.mark.parametrize("version_field", ["suite_version", "scenario_version"])
def test_given_non_positive_version_when_construct_trajectory_then_raises(
    version_field: str,
) -> None:
    # Act & Assert
    with pytest.raises(TrajectoryValidationError):
        _make_trajectory(**{version_field: 0})


def test_given_no_steps_when_construct_trajectory_then_raises() -> None:
    # Act & Assert
    with pytest.raises(TrajectoryValidationError):
        _make_trajectory(steps=())


def test_given_duplicate_step_indices_when_construct_trajectory_then_raises() -> None:
    # Arrange
    steps = (_make_step(0), _make_step(0))

    # Act & Assert
    with pytest.raises(TrajectoryValidationError):
        _make_trajectory(steps=steps)


def test_given_non_sequential_step_indices_when_construct_trajectory_then_raises() -> None:
    # Arrange
    steps = (_make_step(0), _make_step(2))

    # Act & Assert
    with pytest.raises(TrajectoryValidationError):
        _make_trajectory(steps=steps)


def test_given_reversed_step_indices_when_construct_trajectory_then_raises() -> None:
    # Arrange
    steps = (_make_step(1), _make_step(0))

    # Act & Assert
    with pytest.raises(TrajectoryValidationError):
        _make_trajectory(steps=steps)


def test_given_negative_intervention_count_when_construct_trajectory_then_raises() -> None:
    # Act & Assert
    with pytest.raises(TrajectoryValidationError):
        _make_trajectory(intervention_count=-1)


def test_given_negative_policy_violation_count_when_construct_trajectory_then_raises() -> None:
    # Act & Assert
    with pytest.raises(TrajectoryValidationError):
        _make_trajectory(policy_violation_count=-1)


def test_given_negative_index_when_construct_step_then_raises() -> None:
    # Act & Assert
    with pytest.raises(TrajectoryValidationError):
        Step(index=-1, action="decide", state_transition="idle->searching")


def test_given_empty_action_when_construct_step_then_raises() -> None:
    # Act & Assert
    with pytest.raises(TrajectoryValidationError):
        Step(index=0, action="", state_transition="idle->searching")


def test_given_empty_state_transition_when_construct_step_then_raises() -> None:
    # Act & Assert
    with pytest.raises(TrajectoryValidationError):
        Step(index=0, action="decide", state_transition="")


def test_given_empty_tool_name_when_construct_tool_invocation_then_raises() -> None:
    # Act & Assert
    with pytest.raises(TrajectoryValidationError):
        ToolInvocation(call_id="call-1", name="")


def test_given_empty_fault_id_when_construct_fault_trigger_then_raises() -> None:
    # Act & Assert
    with pytest.raises(TrajectoryValidationError):
        FaultTrigger(fault_id="")


def test_given_negative_latency_when_construct_usage_metrics_then_raises() -> None:
    # Act & Assert
    with pytest.raises(TrajectoryValidationError):
        UsageMetrics(latency_ms=-1.0)


def test_given_empty_outcome_label_when_construct_outcome_then_raises() -> None:
    # Act & Assert
    with pytest.raises(TrajectoryValidationError):
        Outcome(
            goal_achieved=True,
            label="",
            status=OutcomeStatus.SUCCEEDED,
            terminal_state="done",
            evidence_references=("outcome",),
        )


def test_given_no_raw_text_fields_when_construct_step_then_succeeds_for_redaction() -> None:
    # Act
    step = Step(index=0, action="decide", state_transition="idle->searching")

    # Assert
    assert step.prompt_text is None
    assert step.output_text is None
    assert step.tool is None


def test_given_no_call_or_response_payload_when_construct_tool_invocation_then_succeeds() -> None:
    # Act
    tool = ToolInvocation(call_id="call-1", name="search_tool")

    # Assert
    assert tool.call_payload is None
    assert tool.response_payload is None


@pytest.mark.parametrize(
    ("field_name", "kind"),
    [
        ("prompt_text", ContentKind.PROMPT),
        ("output_text", ContentKind.OUTPUT),
    ],
)
def test_given_raw_step_content_when_construct_step_then_rejects_unredacted_content(
    field_name: str,
    kind: ContentKind,
) -> None:
    # Arrange
    values = {field_name: "raw secret"}

    # Act & Assert
    with pytest.raises(TrajectoryValidationError, match="RedactedContent"):
        Step(index=0, action="decide", state_transition="idle->done", **values)

    marker = RedactedContent(kind=kind, reference_id=f"step:0:{field_name}")
    assert marker.marker is RedactionMarker.REDACTED


def test_given_raw_tool_payload_when_construct_tool_then_rejects_unredacted_content() -> None:
    # Act & Assert
    with pytest.raises(TrajectoryValidationError, match="RedactedContent"):
        ToolInvocation(call_id="call-1", name="search", call_payload="raw secret")


def test_given_recovered_step_without_verified_fault_when_construct_step_then_raises() -> None:
    # Arrange
    recovery = RecoveryEvidence(
        fault_id="latency_spike",
        action="retry",
        successful=True,
        evidence_references=("step:0:recovery",),
    )

    # Act & Assert
    with pytest.raises(TrajectoryValidationError, match="verified fault"):
        Step(
            index=0,
            action="retry",
            state_transition="failed->done",
            recovered=True,
            recovery=recovery,
        )


def test_given_fault_identity_mismatch_when_construct_step_then_raises() -> None:
    # Arrange
    recovery = RecoveryEvidence(
        fault_id="other_fault",
        action="retry",
        successful=True,
        evidence_references=("step:0:recovery",),
    )

    # Act & Assert
    with pytest.raises(TrajectoryValidationError, match="fault_id"):
        Step(
            index=0,
            action="retry",
            state_transition="failed->done",
            fault=FaultTrigger(
                fault_id="latency_spike",
                verified=True,
                affected_evidence_references=("step:0:fault",),
            ),
            recovered=True,
            recovery=recovery,
        )


def test_given_invalid_usage_type_when_construct_step_then_raises() -> None:
    # Act & Assert
    with pytest.raises(TrajectoryValidationError, match="UsageMetrics"):
        Step(index=0, action="decide", state_transition="idle->done", usage=object())


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_given_non_finite_usage_when_construct_usage_then_raises(value: float) -> None:
    # Act & Assert
    with pytest.raises(TrajectoryValidationError, match="finite"):
        UsageMetrics(latency_ms=value)


def test_given_caller_owned_step_list_when_construct_trajectory_then_recursively_freezes() -> None:
    # Arrange
    caller_steps = [_make_step(0)]

    # Act
    trajectory = _make_trajectory(steps=caller_steps)  # type: ignore[arg-type]
    caller_steps.append(_make_step(1))

    # Assert
    assert isinstance(trajectory.steps, tuple)
    assert len(trajectory.steps) == 1


def test_given_terminal_state_mismatch_when_construct_trajectory_then_raises() -> None:
    # Arrange
    outcome = Outcome(
        goal_achieved=True,
        label="done",
        status=OutcomeStatus.SUCCEEDED,
        terminal_state="different-state",
        evidence_references=("outcome",),
    )

    # Act & Assert
    with pytest.raises(TrajectoryValidationError, match="terminal state"):
        _make_trajectory(outcome=outcome)


def test_given_outcome_status_mismatch_when_construct_outcome_then_raises() -> None:
    # Act & Assert
    with pytest.raises(TrajectoryValidationError, match="goal_achieved"):
        Outcome(
            goal_achieved=True,
            label="failed",
            status=OutcomeStatus.FAILED,
            terminal_state="done",
            evidence_references=("outcome",),
        )


def test_given_multi_step_trajectory_when_read_totals_then_sums_per_step_usage() -> None:
    # Arrange
    steps = (
        _make_step(0, latency_ms=100.0),
        _make_step(1, latency_ms=200.0),
    )

    # Act
    trajectory = _make_trajectory(steps=steps)

    # Assert
    assert trajectory.total_latency_ms == pytest.approx(300.0)
    assert trajectory.total_prompt_tokens == 20
    assert trajectory.total_completion_tokens == 10
    assert trajectory.total_cost_usd == pytest.approx(0.02)


def test_given_verified_fault_step_when_read_triggered_fault_ids_then_includes_fault() -> None:
    # Arrange
    steps = (_make_step(0), _make_step(1, fault_id="latency_spike", verified=True))

    # Act
    trajectory = _make_trajectory(steps=steps)

    # Assert
    assert trajectory.triggered_fault_ids == ("latency_spike",)


def test_given_unverified_fault_step_when_read_triggered_fault_ids_then_excludes_fault() -> None:
    # Arrange
    steps = (_make_step(0, fault_id="latency_spike", verified=False),)

    # Act
    trajectory = _make_trajectory(steps=steps)

    # Assert
    assert trajectory.triggered_fault_ids == ()


def test_given_trajectory_when_mutate_run_id_then_raises_frozen_instance_error() -> None:
    # Arrange
    trajectory = _make_trajectory()

    # Act & Assert
    with pytest.raises(dataclasses.FrozenInstanceError):
        trajectory.run_id = "changed"  # type: ignore[misc]


def test_given_step_when_mutate_action_then_raises_frozen_instance_error() -> None:
    # Arrange
    step = _make_step(0)

    # Act & Assert
    with pytest.raises(dataclasses.FrozenInstanceError):
        step.action = "changed"  # type: ignore[misc]


def test_given_trajectory_with_triggered_fault_when_from_trajectory_then_matches_summary() -> None:
    # Arrange
    steps = (
        _make_step(0, latency_ms=100.0),
        _make_step(1, fault_id="latency_spike", verified=True, latency_ms=200.0),
    )
    trajectory = _make_trajectory(steps=steps, intervention_count=2, policy_violation_count=1)

    # Act
    event = RunEvent.from_trajectory(trajectory)

    # Assert
    assert event.task_id == "task-1"
    assert event.disruption == "latency_spike"
    assert event.success is True
    assert event.policy_violations == 1
    assert event.interventions == 2
    assert event.latency_ms == pytest.approx(300.0)


def test_given_trajectory_no_fault_when_from_trajectory_then_disruption_is_baseline() -> None:
    # Arrange
    trajectory = _make_trajectory()

    # Act
    event = RunEvent.from_trajectory(trajectory)

    # Assert
    assert event.disruption == "baseline"


def test_given_failed_outcome_when_from_trajectory_then_success_is_false() -> None:
    # Arrange
    trajectory = _make_trajectory(
        outcome=Outcome(
            goal_achieved=False,
            label="budget_exceeded",
            status=OutcomeStatus.FAILED,
            terminal_state="searching",
            evidence_references=("trajectory:outcome",),
        )
    )

    # Act
    event = RunEvent.from_trajectory(trajectory)

    # Assert
    assert event.success is False
