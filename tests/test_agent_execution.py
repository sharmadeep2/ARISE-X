"""Unit tests for the deterministic scripted agent execution path."""

from __future__ import annotations

from dataclasses import replace

import pytest

from arise_x.agents.base import AgentResponse
from arise_x.agents.scripted import ScriptedAgent
from arise_x.config import load_settings
from arise_x.evaluation.runner import run_reliability_loop
from arise_x.scenarios import DisruptionReference


class _RecordingAgent:
    """Wraps an agent and records every run_task invocation for assertions."""

    def __init__(self, wrapped: ScriptedAgent) -> None:
        self._wrapped = wrapped
        self.calls: list[tuple[str, str]] = []

    def run_task(self, task_id: str, prompt: str) -> AgentResponse:
        self.calls.append((task_id, prompt))
        return self._wrapped.run_task(task_id, prompt)


class _FailingAgent:
    """Raises a stable error whenever a task is executed."""

    def run_task(self, task_id: str, prompt: str) -> AgentResponse:
        raise RuntimeError(f"agent failed for {task_id}")


def _baseline_only_settings():
    """Return settings whose scenario exercises only the minimum agent protocol."""

    settings = load_settings()
    scenario = replace(
        settings.scenario,
        disruptions=(DisruptionReference(name="baseline"),),
    )
    return replace(settings, scenario=scenario)


def test_given_same_task_when_run_task_called_twice_then_response_is_deterministic() -> None:
    # Arrange
    settings = load_settings()
    agent = ScriptedAgent(settings.scenario)

    # Act
    first = agent.run_task("procurement-dev-001", "Evaluate vendor options within budget.")
    second = agent.run_task("procurement-dev-001", "Evaluate vendor options within budget.")

    # Assert
    assert first == second


def test_given_procurement_scenario_when_run_task_called_then_response_is_successful() -> None:
    # Arrange
    settings = load_settings()
    agent = ScriptedAgent(settings.scenario)

    # Act
    response = agent.run_task("procurement-dev-001", "Evaluate vendor options within budget.")

    # Assert
    assert response.success is True
    assert response.policy_violations == 0
    assert response.interventions == 0


def test_given_reliability_loop_when_run_then_agent_invoked_with_expected_task_ids() -> None:
    # Arrange
    settings = _baseline_only_settings()
    recording_agent = _RecordingAgent(ScriptedAgent(settings.scenario))

    # Act
    results = run_reliability_loop(3, settings, agent=recording_agent)

    # Assert
    assert [task_id for task_id, _ in recording_agent.calls] == ["task-1", "task-2", "task-3"]
    assert len(results) == 3


def test_given_reliability_loop_when_run_then_prompts_derive_from_scenario() -> None:
    # Arrange
    settings = _baseline_only_settings()
    recording_agent = _RecordingAgent(ScriptedAgent(settings.scenario))

    # Act
    run_reliability_loop(2, settings, agent=recording_agent)

    # Assert
    assert all(settings.scenario.objective in prompt for _, prompt in recording_agent.calls)
    assert all(settings.scenario.expected_outcome in prompt for _, prompt in recording_agent.calls)


def test_given_agent_exception_when_run_then_exception_is_surfaced() -> None:
    # Arrange
    settings = load_settings()

    # Act & Assert
    with pytest.raises(RuntimeError, match="agent failed for task-1"):
        run_reliability_loop(1, settings, agent=_FailingAgent())
