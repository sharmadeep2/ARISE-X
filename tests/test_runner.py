"""Unit tests for the simulation runner."""

from __future__ import annotations

import random
from dataclasses import replace

import pytest

from arise_x.agents.base import AgentResponse, FaultObservation, LocalExecutionContext
from arise_x.agents.scripted import ScriptedAgent
from arise_x.chaos import catalog
from arise_x.chaos.catalog import AbortCondition, AbortPolicy, RuntimeCapability
from arise_x.chaos.injector import FaultDispatchError
from arise_x.config import load_settings
from arise_x.evaluation.runner import (
    execute_and_persist_run,
    run_control_and_experiment,
    run_reliability_loop,
)
from arise_x.scenarios import DisruptionReference
from arise_x.storage.repository import RunRepository
from arise_x.telemetry.events import RunEvent
from arise_x.telemetry.trajectory import ContentKind, RedactionMarker
from arise_x.trust.vector import VectorDimension


class _CountingAgent:
    """Counts run_task invocations while delegating to a wrapped agent."""

    def __init__(self, wrapped: ScriptedAgent) -> None:
        self._wrapped = wrapped
        self.call_count = 0

    def run_task(self, task_id: str, prompt: str) -> AgentResponse:
        self.call_count += 1
        return self._wrapped.run_task(task_id, prompt)


class _ObservedOutcomeAgent:
    """Returns fixed evidence so runner-side mutations are observable."""

    version = "observed-outcome-v1"

    def __init__(self, *, success: bool) -> None:
        self._success = success
        self.call_count = 0

    def run_task(self, task_id: str, prompt: str) -> AgentResponse:
        self.call_count += 1
        return AgentResponse(
            task_id=task_id,
            output_text="observed response",
            success=self._success,
            policy_violations=2,
            interventions=1,
        )


class _StatefulCapableAgent:
    """Records per-instance calls so pair isolation can be asserted."""

    runtime_capabilities = frozenset({RuntimeCapability.LOCAL_CONTEXT_V1})

    def __init__(self, forks: list[_StatefulCapableAgent] | None = None) -> None:
        self.forks = [] if forks is None else forks
        self.call_count = 0

    def fork_for_run(self, seed: int) -> _StatefulCapableAgent:
        fork = _StatefulCapableAgent(self.forks)
        self.forks.append(fork)
        return fork

    def run_task(self, task_id: str, prompt: str) -> AgentResponse:
        self.call_count += 1
        return AgentResponse(task_id=task_id, output_text="control", success=True)

    def run_task_with_context(
        self,
        task_id: str,
        prompt: str,
        context: LocalExecutionContext,
    ) -> AgentResponse:
        self.call_count += 1
        return AgentResponse(
            task_id=task_id,
            output_text="experiment",
            success=True,
            fault_observation=FaultObservation(
                fault_id=context.fault_id,
                injection_point=context.injection_point,
                signal=context.expected_signal,
                recovered=True,
                evidence_references=(f"stateful:{task_id}:fault",),
                policy_reason="test double observed and recovered the local effect",
            ),
        )


def _baseline_only_settings():
    """Return settings whose scenario exercises only the minimum agent protocol."""

    settings = load_settings()
    scenario = replace(
        settings.scenario,
        disruptions=(DisruptionReference(name=catalog.BASELINE.fault_id),),
    )
    return replace(settings, scenario=scenario)


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
    settings = _baseline_only_settings()
    counting_agent = _CountingAgent(ScriptedAgent(settings.scenario))

    # Act
    run_reliability_loop(4, settings, agent=counting_agent)

    # Assert
    assert counting_agent.call_count == 4


def test_given_minimum_agent_when_non_baseline_fault_requested_then_rejected_before_call() -> None:
    # Arrange
    settings = load_settings()
    agent = _ObservedOutcomeAgent(success=True)

    # Act / Assert
    with pytest.raises(FaultDispatchError, match="local-capability"):
        run_control_and_experiment(
            agent,
            settings.scenario,
            "task-1",
            catalog.TOOL_DEGRADATION.fault_id,
            1,
        )
    assert agent.call_count == 0


def test_given_stateful_capable_agent_when_run_pair_then_fresh_instances_are_isolated() -> None:
    # Arrange
    settings = load_settings()
    agent = _StatefulCapableAgent()

    # Act
    run_control_and_experiment(
        agent,
        settings.scenario,
        "task-1",
        catalog.STALE_DATA.fault_id,
        1,
    )

    # Assert
    assert agent.call_count == 0
    assert len(agent.forks) == 2
    assert agent.forks[0] is not agent.forks[1]
    assert [fork.call_count for fork in agent.forks] == [1, 1]


def test_given_abort_threshold_reached_when_run_then_aborted_agent_is_not_called(
    tmp_path,
    monkeypatch,
) -> None:
    # Arrange
    settings = load_settings()
    scenario = replace(
        settings.scenario,
        disruptions=(DisruptionReference(name=catalog.VERIFICATION_FAILURE.fault_id),),
    )
    settings = replace(settings, scenario=scenario)
    forced_fault = replace(
        catalog.VERIFICATION_FAILURE,
        failure_boost=1.0,
        abort_policy=AbortPolicy(
            condition=AbortCondition.MAX_VERIFIED_TRIGGERS,
            threshold=1,
        ),
    )
    original_resolve = catalog.resolve_fault
    monkeypatch.setattr(
        catalog,
        "resolve_fault",
        lambda fault_id: (
            forced_fault
            if fault_id == forced_fault.fault_id
            else original_resolve(fault_id)
        ),
    )
    agent = _StatefulCapableAgent()

    # Act
    outcome = execute_and_persist_run(
        2,
        settings,
        RunRepository(tmp_path),
        agent=agent,
        seed=1,
    )

    # Assert
    second_receipt = outcome.trajectories[1].steps[0].fault
    assert second_receipt is not None
    assert second_receipt.aborted is True
    assert [fork.call_count for fork in agent.forks] == [1, 1, 1, 0]


@pytest.mark.parametrize("success", [True, False])
def test_given_observed_agent_evidence_when_run_then_runner_does_not_mutate_it(
    tmp_path, success
) -> None:
    # Arrange
    settings = _baseline_only_settings()
    repository = RunRepository(tmp_path)
    agent = _ObservedOutcomeAgent(success=success)

    # Act
    outcome = execute_and_persist_run(3, settings, repository, agent=agent, seed=31)

    # Assert
    assert agent.call_count == 3
    assert all(trajectory.outcome.goal_achieved is success for trajectory in outcome.trajectories)
    assert all(trajectory.policy_violation_count == 2 for trajectory in outcome.trajectories)
    assert all(trajectory.intervention_count == 1 for trajectory in outcome.trajectories)
    assert all(trajectory.total_latency_ms == 0.0 for trajectory in outcome.trajectories)
    assert all(
        vector.dimension(VectorDimension.EFFICIENCY).available is False
        for vector in outcome.vectors
    )
    assert all(
        vector.dimension(VectorDimension.COST).available is False for vector in outcome.vectors
    )


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


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [("seed", 7), ("trust_threshold", 0.6), ("drift_threshold", 0.2)],
)
def test_given_effective_execution_input_when_changed_then_fingerprint_changes(
    tmp_path, field_name, replacement
) -> None:
    # Arrange
    settings = load_settings()
    repository = RunRepository(tmp_path)

    # Act
    baseline = execute_and_persist_run(1, settings, repository, run_id="baseline")
    if field_name == "seed":
        changed = execute_and_persist_run(
            1, settings, repository, seed=replacement, run_id="changed"
        )
    else:
        changed_settings = replace(settings, **{field_name: replacement})
        changed = execute_and_persist_run(
            1, changed_settings, repository, run_id="changed"
        )

    # Assert
    assert changed.config_fingerprint != baseline.config_fingerprint


def test_given_persisted_outcome_when_read_by_returned_id_then_metadata_matches(tmp_path) -> None:
    # Arrange
    settings = load_settings()
    repository = RunRepository(tmp_path)

    # Act
    outcome = execute_and_persist_run(2, settings, repository, seed=17)
    record = repository.read_run(outcome.run_id)

    # Assert
    assert record.metadata.run_id == outcome.run_id
    assert record.metadata.seed == outcome.seed
    assert record.metadata.config_fingerprint == outcome.config_fingerprint
    assert record.metadata.trust_threshold == outcome.trust_threshold
    assert record.metadata.drift_threshold == outcome.drift_threshold


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


def test_given_iterations_when_execute_and_persist_run_then_one_event_per_task(
    tmp_path,
) -> None:
    # Arrange
    settings = load_settings()
    repository = RunRepository(tmp_path)

    # Act
    outcome = execute_and_persist_run(3, settings, repository)

    # Assert
    assert outcome.events == [
        RunEvent.from_trajectory(trajectory) for trajectory in outcome.trajectories
    ]
    assert repository.read_run(outcome.run_id).events == outcome.events


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


def test_given_agent_content_when_persist_run_then_raw_content_is_redacted_by_default(
    tmp_path,
) -> None:
    # Arrange
    settings = load_settings()
    repository = RunRepository(tmp_path)
    agent = _ObservedOutcomeAgent(success=True)

    # Act
    outcome = execute_and_persist_run(1, settings, repository, agent=agent, seed=31)
    persisted = (tmp_path / f"{outcome.run_id}.json").read_text(encoding="utf-8")
    step = repository.read_run(outcome.run_id).trajectories[0].steps[0]

    # Assert
    assert "observed response" not in persisted
    assert step.prompt_text is not None
    assert step.prompt_text.kind is ContentKind.PROMPT
    assert step.prompt_text.marker is RedactionMarker.REDACTED
    assert step.output_text is not None
    assert step.output_text.kind is ContentKind.OUTPUT
    assert step.output_text.marker is RedactionMarker.REDACTED


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


def test_given_observed_evidence_when_vector_built_then_dimensions_reference_source_fields(
    tmp_path,
) -> None:
    # Arrange
    settings = load_settings()
    repository = RunRepository(tmp_path)

    class _MeasuredAgent:
        def run_task(self, task_id: str, prompt: str) -> AgentResponse:
            return AgentResponse(
                task_id=task_id,
                output_text="measured",
                latency_ms=25.0,
                cost_usd=0.002,
            )

    # Act
    outcome = execute_and_persist_run(1, settings, repository, agent=_MeasuredAgent())

    # Assert
    vector = outcome.vectors[0]
    expected_suffixes = {
        VectorDimension.GOAL_SUCCESS: ":outcome",
        VectorDimension.SAFETY: ":policy_violation_count",
        VectorDimension.EFFICIENCY: ":usage:latency_ms",
        VectorDimension.COST: ":usage:cost_usd",
        VectorDimension.AUTONOMY: ":intervention_count",
    }
    for dimension, suffix in expected_suffixes.items():
        score = vector.dimension(dimension)
        assert score.available is True
        assert all(reference.endswith(suffix) for reference in score.evidence_references)
    assert vector.dimension(VectorDimension.RECOVERY).available is False


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

