"""Unit tests for the simulation runner."""

from __future__ import annotations

import random

import pytest

from arise_x.agents.base import AgentResponse
from arise_x.agents.scripted import ScriptedAgent
from arise_x.chaos import catalog
from arise_x.config import load_settings
from arise_x.evaluation.runner import execute_and_persist_run, run_reliability_loop
from arise_x.storage.repository import RunRepository
from arise_x.trust.vector import VectorDimension


class _CountingAgent:
    """Counts run_task invocations while delegating to a wrapped agent."""

    def __init__(self, wrapped: ScriptedAgent) -> None:
        self._wrapped = wrapped
        self.call_count = 0

    def run_task(self, task_id: str, prompt: str) -> AgentResponse:
        self.call_count += 1
        return self._wrapped.run_task(task_id, prompt)


def test_given_iterations_when_run_reliability_loop_then_returns_same_count() -> None:
    # Arrange
    settings = load_settings()

    # Act
    results = run_reliability_loop(6, settings)

    # Assert
    assert len(results) == 6


def test_given_iterations_when_run_reliability_loop_then_uses_known_disruptions() -> None:
    # Arrange
    settings = load_settings()

    # Act
    results = run_reliability_loop(3, settings)

    # Assert
    assert {item.disruption for item in results} <= {
        "baseline",
        "latency_spike",
        "tool_degradation",
    }


def test_given_injected_agent_when_run_reliability_loop_then_agent_is_called() -> None:
    # Arrange
    settings = load_settings()
    counting_agent = _CountingAgent(ScriptedAgent(settings.scenario))

    # Act
    run_reliability_loop(4, settings, agent=counting_agent)

    # Assert
    assert counting_agent.call_count == 4


def test_given_same_scenario_and_seed_when_run_twice_then_results_are_identical() -> None:
    # Arrange
    settings = load_settings()

    # Act
    first = run_reliability_loop(5, settings, random_source=random.Random(settings.scenario.seed))
    second = run_reliability_loop(
        5, settings, random_source=random.Random(settings.scenario.seed)
    )

    # Assert
    assert first == second


def test_given_default_random_when_run_twice_then_results_match() -> None:
    # Arrange
    settings = load_settings()

    # Act
    first = run_reliability_loop(5, settings)
    second = run_reliability_loop(5, settings)

    # Assert
    assert first == second


def test_given_iterations_when_execute_and_persist_run_then_one_trajectory_per_task(
    tmp_path,
) -> None:
    # Arrange
    settings = load_settings()
    repository = RunRepository(tmp_path)

    # Act
    outcome = execute_and_persist_run(3, settings, repository)

    # Assert
    assert [trajectory.task_id for trajectory in outcome.trajectories] == [
        result.task_id for result in outcome.results
    ]


def test_given_iterations_when_execute_and_persist_run_then_one_vector_per_task(
    tmp_path,
) -> None:
    # Arrange
    settings = load_settings()
    repository = RunRepository(tmp_path)

    # Act
    outcome = execute_and_persist_run(3, settings, repository)

    # Assert
    assert len(outcome.vectors) == 3


def test_given_execute_and_persist_run_when_inspecting_trajectory_then_run_id_matches_outcome(
    tmp_path,
) -> None:
    # Arrange
    settings = load_settings()
    repository = RunRepository(tmp_path)

    # Act
    outcome = execute_and_persist_run(2, settings, repository)

    # Assert
    assert all(trajectory.run_id == outcome.run_id for trajectory in outcome.trajectories)


def test_given_execute_and_persist_run_when_inspecting_trajectory_then_reflects_agent_response(
    tmp_path,
) -> None:
    # Arrange
    settings = load_settings()
    repository = RunRepository(tmp_path)

    # Act
    outcome = execute_and_persist_run(1, settings, repository)

    # Assert
    trajectory = outcome.trajectories[0]
    assert trajectory.steps[0].output_text is not None
    assert len(trajectory.steps) == 1


def test_given_no_baseline_established_when_execute_and_persist_run_then_stability_unavailable(
    tmp_path,
) -> None:
    # Arrange
    settings = load_settings()
    repository = RunRepository(tmp_path)

    # Act
    outcome = execute_and_persist_run(3, settings, repository)

    # Assert: behavioral_stability requires a historical baseline that does not exist yet.
    assert all(
        vector.dimension(VectorDimension.BEHAVIORAL_STABILITY).available is False
        for vector in outcome.vectors
    )


def test_given_trajectory_outcome_when_execute_and_persist_run_then_goal_success_matches(
    tmp_path,
) -> None:
    # Arrange
    settings = load_settings()
    repository = RunRepository(tmp_path)

    # Act
    outcome = execute_and_persist_run(4, settings, repository)

    # Assert
    for trajectory, vector in zip(outcome.trajectories, outcome.vectors, strict=True):
        expected = 1.0 if trajectory.outcome.goal_achieved else 0.0
        assert vector.dimension(VectorDimension.GOAL_SUCCESS).value == pytest.approx(expected)


def test_given_non_baseline_disruption_when_execute_and_persist_run_then_fault_id_is_cataloged(
    tmp_path,
) -> None:
    # Arrange
    settings = load_settings()
    repository = RunRepository(tmp_path)

    # Act
    outcome = execute_and_persist_run(6, settings, repository)

    # Assert
    for trajectory in outcome.trajectories:
        fault = trajectory.steps[0].fault
        if fault is not None:
            assert fault.fault_id in catalog.DISPATCHED_FAULT_IDS


def test_given_execute_and_persist_run_when_fault_recorded_then_recovery_availability_matches_verified(  # noqa: E501
    tmp_path,
) -> None:
    # Arrange
    settings = load_settings()
    repository = RunRepository(tmp_path)

    # Act
    outcome = execute_and_persist_run(6, settings, repository)

    # Assert: only asserted for non-baseline tasks, since a recorded fault is
    # the only case _build_reliability_vector's recovery derivation is meant
    # to gate on catalog-verified status; baseline tasks never record a
    # fault at all.
    for trajectory, vector in zip(outcome.trajectories, outcome.vectors, strict=True):
        fault = trajectory.steps[0].fault
        if fault is not None:
            assert vector.dimension(VectorDimension.RECOVERY).available is fault.verified

