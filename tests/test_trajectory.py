"""Unit tests for immutable trajectory evidence."""

from __future__ import annotations

import dataclasses

import pytest

from arise_x.telemetry.events import RunEvent
from arise_x.telemetry.trajectory import (
    FaultTrigger,
    Outcome,
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
    fault = FaultTrigger(fault_id=fault_id, verified=verified) if fault_id else None
    return Step(
        index=index,
        action="decide",
        state_transition="idle->searching",
        tool=ToolInvocation(name="search_tool", call_payload="query", response_payload="results"),
        fault=fault,
        recovered=verified,
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
        "outcome": Outcome(goal_achieved=True, label="purchase_order_created"),
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
        ToolInvocation(name="")


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
        Outcome(goal_achieved=True, label="")


def test_given_no_raw_text_fields_when_construct_step_then_succeeds_for_redaction() -> None:
    # Act
    step = Step(index=0, action="decide", state_transition="idle->searching")

    # Assert
    assert step.prompt_text is None
    assert step.output_text is None
    assert step.tool is None


def test_given_no_call_or_response_payload_when_construct_tool_invocation_then_succeeds() -> None:
    # Act
    tool = ToolInvocation(name="search_tool")

    # Assert
    assert tool.call_payload is None
    assert tool.response_payload is None


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
    trajectory = _make_trajectory(outcome=Outcome(goal_achieved=False, label="budget_exceeded"))

    # Act
    event = RunEvent.from_trajectory(trajectory)

    # Assert
    assert event.success is False
