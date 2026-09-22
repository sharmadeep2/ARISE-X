"""Unit tests for the star-topology multi-agent coordinator, MACS milestones, and Level 5 faults."""

from __future__ import annotations

import random
from dataclasses import replace

import pytest

from arise_x.agents.base import AgentResponse
from arise_x.agents.multi_agent import (
    Coordinator,
    MacsComponents,
    MacsScore,
    MilestoneObservation,
    MultiAgentValidationError,
)
from arise_x.agents.scripted import ScriptedAgent
from arise_x.chaos import catalog
from arise_x.chaos.injector import (
    FaultDispatchResult,
    dispatch_information_withholding,
    dispatch_message_loss,
)
from arise_x.config import load_settings
from arise_x.evaluation.runner import run_multi_agent_reliability_loop


class _FailingWorker:
    """Deterministic worker whose response never satisfies rule-based verification."""

    version = "failing-worker-v1"

    def run_task(self, task_id: str, prompt: str) -> AgentResponse:
        return AgentResponse(task_id=task_id, output_text="unrelated response text", success=True)


def _scripted_workers(scenario, worker_ids: tuple[str, ...]) -> dict[str, ScriptedAgent]:
    return {worker_id: ScriptedAgent(scenario) for worker_id in worker_ids}


# --- Assignment, handoff, and response correlation ---------------------------------------------


def test_given_scripted_workers_when_run_episode_then_each_worker_assigned_a_unique_subtask() -> (
    None
):
    # Arrange
    settings = load_settings()
    coordinator = Coordinator()
    workers = _scripted_workers(settings.scenario, ("vendor_worker", "budget_worker"))

    # Act
    episode = coordinator.run_episode(settings.scenario, "task-1", workers, rng=random.Random(1))

    # Assert
    sub_task_ids = {assignment.role.sub_task_id for assignment in episode.assignments}
    assert sub_task_ids == {"task-1::vendor_worker", "task-1::budget_worker"}


def test_given_scripted_workers_when_run_episode_then_responses_correlate_to_assigned_worker() -> (
    None
):
    # Arrange
    settings = load_settings()
    coordinator = Coordinator()
    workers = _scripted_workers(settings.scenario, ("vendor_worker", "budget_worker"))

    # Act
    episode = coordinator.run_episode(settings.scenario, "task-1", workers, rng=random.Random(1))

    # Assert
    for assignment in episode.assignments:
        assert assignment.response is not None
        assert assignment.response.task_id == assignment.role.sub_task_id


def test_given_empty_workers_when_run_episode_then_raises_validation_error() -> None:
    # Arrange
    settings = load_settings()
    coordinator = Coordinator()

    # Act / Assert
    with pytest.raises(MultiAgentValidationError):
        coordinator.run_episode(settings.scenario, "task-1", {})


# --- MACS milestone components ------------------------------------------------------------------


def test_given_successful_episode_when_computing_macs_then_all_five_components_achieved() -> None:
    # Arrange
    settings = load_settings()
    coordinator = Coordinator()
    workers = _scripted_workers(settings.scenario, ("vendor_worker", "budget_worker"))

    # Act
    episode = coordinator.run_episode(settings.scenario, "task-1", workers, rng=random.Random(1))

    # Assert
    observations = episode.macs.components.observations()
    assert all(observation.available for observation in observations)
    assert all(observation.achieved for observation in observations)
    assert episode.success is True


def test_given_failing_worker_when_run_episode_then_verification_milestone_fails_independently() -> (  # noqa: E501
    None
):
    # Arrange
    settings = load_settings()
    coordinator = Coordinator()
    workers = {"vendor_worker": _FailingWorker(), "budget_worker": ScriptedAgent(settings.scenario)}

    # Act
    episode = coordinator.run_episode(settings.scenario, "task-1", workers, rng=random.Random(1))

    # Assert: assignment, information exchange, and handoff all still succeeded for both
    # workers -- only verification (and the objective completion it gates) reflects the
    # bad response, rather than every milestone silently degrading to failure.
    components = episode.macs.components
    assert components.assignment.achieved is True
    assert components.information_exchange.achieved is True
    assert components.handoff.achieved is True
    assert components.verification.achieved is False
    assert components.objective_completion.achieved is False
    assert episode.success is False


def test_given_no_available_components_when_computing_macs_score_then_aggregate_is_none() -> None:
    # Arrange
    unavailable = MilestoneObservation(name="unavailable", achieved=False, available=False)
    components = MacsComponents(
        assignment=unavailable,
        information_exchange=unavailable,
        handoff=unavailable,
        verification=unavailable,
        objective_completion=unavailable,
    )

    # Act
    macs = MacsScore.from_components(components)

    # Assert: missing evidence is excluded from the aggregate entirely rather than
    # silently counted as either success or failure.
    assert macs.diagnostic_aggregate is None
    assert macs.available_component_count == 0
    assert macs.achieved_component_count == 0


def test_given_partial_success_when_computing_macs_score_then_aggregate_is_achieved_over_available_only() -> (  # noqa: E501
    None
):
    # Arrange
    achieved = MilestoneObservation(name="achieved", achieved=True, available=True)
    failed = MilestoneObservation(name="failed", achieved=False, available=True)
    unavailable = MilestoneObservation(name="unavailable", achieved=False, available=False)
    components = MacsComponents(
        assignment=achieved,
        information_exchange=achieved,
        handoff=failed,
        verification=failed,
        objective_completion=unavailable,
    )

    # Act
    macs = MacsScore.from_components(components)

    # Assert: 2 achieved out of 4 available (the unavailable component is excluded).
    assert macs.available_component_count == 4
    assert macs.achieved_component_count == 2
    assert macs.diagnostic_aggregate == pytest.approx(0.5)


def test_given_achieved_without_available_when_constructing_milestone_observation_then_raises() -> (
    None
):
    # Act / Assert
    with pytest.raises(MultiAgentValidationError):
        MilestoneObservation(name="invalid", achieved=True, available=False)


# --- Level 5 (Multi-Agent) fault dispatch: message_loss and information_withholding -------------


def test_given_guaranteed_message_loss_fault_when_dispatch_message_loss_then_verified() -> None:
    # Arrange
    fault = replace(catalog.MESSAGE_LOSS, failure_boost=1.0)

    # Act
    result = dispatch_message_loss(fault, rng=random.Random(1))

    # Assert
    assert result.triggered is True
    assert result.verified is True


def test_given_zero_probability_message_loss_fault_when_dispatch_message_loss_then_never_triggered() -> (  # noqa: E501
    None
):
    # Arrange
    fault = replace(catalog.MESSAGE_LOSS, failure_boost=0.0)

    # Act
    result = dispatch_message_loss(fault, rng=random.Random(1))

    # Assert
    assert result.triggered is False
    assert result.verified is False


def test_given_guaranteed_information_withholding_fault_when_dispatch_then_verified() -> None:
    # Arrange
    fault = replace(catalog.INFORMATION_WITHHOLDING, failure_boost=1.0)

    # Act
    result = dispatch_information_withholding(fault, rng=random.Random(1))

    # Assert
    assert result.triggered is True
    assert result.verified is True


def test_given_verified_message_loss_when_run_episode_then_worker_response_not_collected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    settings = load_settings()
    forced = FaultDispatchResult(
        fault_id="message_loss", triggered=True, verified=True, latency_multiplier=1.0
    )
    monkeypatch.setattr(
        "arise_x.agents.multi_agent.dispatch_message_loss", lambda fault, *, rng: forced
    )
    coordinator = Coordinator()
    workers = _scripted_workers(settings.scenario, ("vendor_worker",))

    # Act
    episode = coordinator.run_episode(
        settings.scenario, "task-1", workers, fault_id="message_loss", rng=random.Random(1)
    )

    # Assert
    assert episode.assignments[0].response is None
    assert episode.handoffs[0].received is False
    assert episode.macs.components.handoff.achieved is False
    assert episode.fault_dispatches == (forced,)


def test_given_verified_information_withholding_when_run_episode_then_context_is_withheld(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    settings = load_settings()
    forced = FaultDispatchResult(
        fault_id="information_withholding", triggered=True, verified=True, latency_multiplier=1.0
    )
    monkeypatch.setattr(
        "arise_x.agents.multi_agent.dispatch_information_withholding",
        lambda fault, *, rng: forced,
    )
    coordinator = Coordinator()
    workers = _scripted_workers(settings.scenario, ("vendor_worker",))

    # Act
    episode = coordinator.run_episode(
        settings.scenario,
        "task-1",
        workers,
        fault_id="information_withholding",
        rng=random.Random(1),
    )

    # Assert
    assert episode.information_exchanges[0].withheld is True
    assert episode.macs.components.information_exchange.achieved is False


def test_given_all_messages_lost_when_computing_macs_then_missing_components_excluded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Arrange
    settings = load_settings()
    forced = FaultDispatchResult(
        fault_id="message_loss", triggered=True, verified=True, latency_multiplier=1.0
    )
    monkeypatch.setattr(
        "arise_x.agents.multi_agent.dispatch_message_loss", lambda fault, *, rng: forced
    )
    coordinator = Coordinator()
    workers = _scripted_workers(settings.scenario, ("vendor_worker", "budget_worker"))

    # Act
    episode = coordinator.run_episode(
        settings.scenario, "task-1", workers, fault_id="message_loss", rng=random.Random(1)
    )

    # Assert: objective completion has no responses to judge and is excluded from the
    # aggregate rather than counted as a failure or success.
    assert episode.macs.components.objective_completion.available is False
    assert episode.macs.available_component_count == 4
    assert episode.macs.diagnostic_aggregate == pytest.approx(2 / 4)


# --- evaluation.runner wiring --------------------------------------------------------------------


def test_given_run_multi_agent_reliability_loop_when_run_then_returns_matching_length_evidence() -> (  # noqa: E501
    None
):
    # Arrange
    settings = load_settings()
    scenario = settings.scenario
    workers = _scripted_workers(scenario, ("vendor_worker", "budget_worker"))

    # Act
    outcome = run_multi_agent_reliability_loop(scenario, workers, iterations=2, seed=7)

    # Assert
    assert len(outcome.episodes) == 2
    assert len(outcome.trajectories) == 2
    assert len(outcome.vectors) == 2
    assert len(outcome.macs_scores) == 2


def test_given_multi_agent_run_when_building_trajectory_then_one_step_per_worker() -> None:
    # Arrange
    settings = load_settings()
    scenario = settings.scenario
    workers = _scripted_workers(scenario, ("vendor_worker", "budget_worker"))

    # Act
    outcome = run_multi_agent_reliability_loop(scenario, workers, seed=3)

    # Assert
    trajectory = outcome.trajectories[0]
    assert len(trajectory.steps) == 2
    assert {step.tool.name for step in trajectory.steps if step.tool is not None} == {
        "worker:vendor_worker",
        "worker:budget_worker",
    }


def test_given_successful_multi_agent_run_when_building_vector_then_goal_success_available() -> (
    None
):
    # Arrange
    settings = load_settings()
    scenario = settings.scenario
    workers = _scripted_workers(scenario, ("vendor_worker", "budget_worker"))

    # Act
    outcome = run_multi_agent_reliability_loop(scenario, workers, seed=3)

    # Assert
    vector = outcome.vectors[0]
    assert vector.goal_success.available is True
    assert vector.goal_success.value == 1.0
