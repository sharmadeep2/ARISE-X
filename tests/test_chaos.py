"""Unit tests for the typed fault catalog, verified dispatch, and control/experiment pairing."""

from __future__ import annotations

import random
from dataclasses import FrozenInstanceError, replace

import pytest

from arise_x.agents.scripted import ScriptedAgent
from arise_x.chaos import catalog
from arise_x.chaos.catalog import (
    AbortCondition,
    AbortPolicy,
    FaultCatalogError,
    FaultFamily,
    FaultLevel,
    RuntimeCapability,
)
from arise_x.chaos.injector import (
    FaultPolicyState,
    dispatch_fault,
    finalize_fault,
    prepare_fault,
)
from arise_x.config import load_settings
from arise_x.evaluation.runner import run_control_and_experiment


def test_given_catalog_when_inspecting_levels_then_all_four_levels_represented() -> None:
    # Act
    levels = {fault.level for fault in catalog.CATALOG}

    # Assert
    assert levels == set(FaultLevel)


def test_given_catalog_when_inspecting_families_then_all_three_families_represented() -> None:
    # Act
    families = {fault.family for fault in catalog.CATALOG if fault.family is not None}

    # Assert
    assert families == set(FaultFamily)


@pytest.mark.parametrize(
    ("fault_id", "expected_level"),
    [
        ("baseline", FaultLevel.INFRASTRUCTURE),
        ("latency_spike", FaultLevel.INFRASTRUCTURE),
        ("resource_exhaustion", FaultLevel.INFRASTRUCTURE),
        ("clock_skew", FaultLevel.INFRASTRUCTURE),
        ("tool_degradation", FaultLevel.TOOL),
        ("tool_version_change", FaultLevel.TOOL),
        ("stale_data", FaultLevel.DATA),
        ("poisoned_data", FaultLevel.DATA),
        ("planning_failure", FaultLevel.AGENT),
        ("verification_failure", FaultLevel.AGENT),
    ],
)
def test_given_known_fault_id_when_get_fault_then_level_matches_taxonomy(
    fault_id: str, expected_level: FaultLevel
) -> None:
    # Act
    fault = catalog.get_fault(fault_id)

    # Assert
    assert fault.level == expected_level


@pytest.mark.parametrize(
    ("fault_id", "expected_family"),
    [
        ("cost_spike", FaultFamily.COST),
        ("poisoned_data", FaultFamily.SECURITY_ADVERSARIAL),
        ("prompt_injection", FaultFamily.SECURITY_ADVERSARIAL),
        ("human_escalation_timeout", FaultFamily.HUMAN_IN_THE_LOOP),
    ],
)
def test_given_cross_cutting_fault_id_when_get_fault_then_family_matches(
    fault_id: str, expected_family: FaultFamily
) -> None:
    # Act
    fault = catalog.get_fault(fault_id)

    # Assert
    assert fault.family == expected_family


def test_given_unknown_fault_id_when_get_fault_then_raises_catalog_error() -> None:
    # Act / Assert
    with pytest.raises(FaultCatalogError):
        catalog.get_fault("does_not_exist")


def test_given_unknown_fault_id_when_resolve_fault_then_raises_catalog_error() -> None:
    # Act / Assert
    with pytest.raises(FaultCatalogError, match="does_not_exist"):
        catalog.resolve_fault("does_not_exist")


def test_given_catalog_when_checking_dispatched_ids_then_representative_levels_are_local() -> None:
    # Assert
    assert catalog.DISPATCHED_FAULT_IDS == {
        "baseline",
        "latency_spike",
        "tool_degradation",
        "stale_data",
        "verification_failure",
    }


@pytest.mark.parametrize(
    ("fault_id", "level"),
    [
        ("latency_spike", FaultLevel.INFRASTRUCTURE),
        ("tool_degradation", FaultLevel.TOOL),
        ("stale_data", FaultLevel.DATA),
        ("verification_failure", FaultLevel.AGENT),
    ],
)
def test_given_mvp_fault_when_inspecting_then_level_has_local_runtime(
    fault_id: str,
    level: FaultLevel,
) -> None:
    # Act
    fault = catalog.get_fault(fault_id)

    # Assert
    assert fault.level is level
    assert fault.runtime_dispatch is True
    assert fault.runtime_capability is RuntimeCapability.LOCAL_CONTEXT_V1
    assert fault.external_side_effect is False


def test_given_duplicate_fault_id_when_building_registry_then_raises_catalog_error() -> None:
    # Arrange
    duplicate = (catalog.BASELINE, replace(catalog.LATENCY_SPIKE, fault_id="baseline"))

    # Act / Assert
    with pytest.raises(FaultCatalogError):
        catalog._build_registry(duplicate)


def test_given_empty_description_when_constructing_fault_definition_then_raises() -> None:
    # Act / Assert
    with pytest.raises(FaultCatalogError):
        replace(catalog.BASELINE, description="")


def test_given_external_side_effect_without_bounds_when_constructing_fault_then_raises() -> None:
    # Act / Assert
    with pytest.raises(FaultCatalogError, match="external side effects"):
        replace(catalog.BASELINE, external_side_effect=True)


def test_given_catalog_fault_when_inspecting_then_has_typed_policy_contract() -> None:
    # Act
    fault = catalog.TOOL_DEGRADATION

    # Assert
    assert fault.intensity > 0.0
    assert fault.window.duration_steps == 1
    assert fault.abort_policy.condition is AbortCondition.MAX_VERIFIED_TRIGGERS
    assert fault.blast_radius.bounded is True
    assert fault.expected_observation.signal is not catalog.ObservationSignal.NONE


def test_given_non_dispatched_fault_when_dispatch_fault_then_raises_not_implemented_error() -> None:
    # Act / Assert
    with pytest.raises(NotImplementedError):
        dispatch_fault(
            catalog.MISSING_DATA,
            base_failure_rate=0.08,
            control_success=True,
            rng=random.Random(1),
        )


def test_given_guaranteed_trigger_when_dispatch_then_not_verified_without_observation() -> None:
    # Arrange
    fault = replace(catalog.LATENCY_SPIKE, failure_boost=1.0)

    # Act
    result = dispatch_fault(
        fault, base_failure_rate=0.0, control_success=True, rng=random.Random(1)
    )

    # Assert
    assert result.triggered is True
    assert result.observed is False
    assert result.verified is False


def test_given_control_success_change_when_dispatch_then_verification_is_unchanged() -> None:
    # Arrange
    fault = replace(catalog.LATENCY_SPIKE, failure_boost=1.0)

    # Act
    successful_control = dispatch_fault(
        fault, base_failure_rate=0.0, control_success=True, rng=random.Random(1)
    )
    failing_control = dispatch_fault(
        fault, base_failure_rate=0.0, control_success=False, rng=random.Random(1)
    )

    # Assert
    assert successful_control == failing_control
    assert failing_control.verified is False


def test_given_zero_probability_fault_when_dispatch_fault_then_never_triggered() -> None:
    # Arrange
    fault = replace(catalog.LATENCY_SPIKE, failure_boost=0.0)

    # Act
    result = dispatch_fault(
        fault, base_failure_rate=0.0, control_success=True, rng=random.Random(1)
    )

    # Assert
    assert result.triggered is False
    assert result.verified is False


def test_given_same_seed_when_dispatch_fault_twice_then_results_are_identical() -> None:
    # Act
    first = dispatch_fault(
        catalog.TOOL_DEGRADATION,
        base_failure_rate=0.08,
        control_success=True,
        rng=random.Random(42),
    )
    second = dispatch_fault(
        catalog.TOOL_DEGRADATION,
        base_failure_rate=0.08,
        control_success=True,
        rng=random.Random(42),
    )

    # Assert
    assert first == second


def test_given_abort_threshold_reached_when_prepare_fault_then_aborted_without_trigger() -> None:
    # Arrange
    fault = replace(
        catalog.TOOL_DEGRADATION,
        abort_policy=AbortPolicy(
            condition=AbortCondition.MAX_VERIFIED_TRIGGERS,
            threshold=1,
        ),
    )

    # Act
    attempt = prepare_fault(
        fault,
        base_failure_rate=0.0,
        rng=random.Random(1),
        policy_state=FaultPolicyState(verified_trigger_count=1),
    )

    # Assert
    assert attempt.context is None
    assert attempt.receipt.aborted is True
    assert attempt.receipt.triggered is False


def test_given_observation_at_wrong_injection_point_when_finalize_then_not_verified() -> None:
    # Arrange
    settings = load_settings()
    agent = ScriptedAgent(settings.scenario)
    attempt = prepare_fault(
        replace(catalog.TOOL_DEGRADATION, failure_boost=1.0),
        base_failure_rate=0.0,
        rng=random.Random(1),
        policy_state=FaultPolicyState(),
    )
    response = agent.run_task_with_context("task-1", "prompt", attempt.context)
    mismatched = replace(
        response.fault_observation,
        injection_point=catalog.InjectionPoint.DATA_ACCESS,
    )

    # Act
    receipt = finalize_fault(
        attempt,
        mismatched,
        policy_state=FaultPolicyState(),
    )

    # Assert
    assert receipt.triggered is True
    assert receipt.observed is False
    assert receipt.verified is False


def test_given_receipt_when_mutation_attempted_then_is_immutable() -> None:
    # Arrange
    receipt = dispatch_fault(
        catalog.TOOL_DEGRADATION,
        base_failure_rate=0.0,
        control_success=True,
        rng=random.Random(2),
    )

    # Act / Assert
    with pytest.raises(FrozenInstanceError):
        receipt.triggered = True


def test_given_real_fault_active_when_run_control_and_experiment_then_control_never_records_a_fault() -> (  # noqa: E501
    None
):
    # Arrange
    settings = load_settings()
    agent = ScriptedAgent(settings.scenario)

    # Act
    outcome = run_control_and_experiment(agent, settings.scenario, "task-1", "tool_degradation", 7)

    # Assert
    assert outcome.control.triggered_fault_ids == ()


def test_given_triggered_tool_fault_when_run_pair_then_receipt_is_verified_and_recovered() -> (  # noqa: E501
    None
):
    # Arrange
    settings = load_settings()
    agent = ScriptedAgent(settings.scenario)

    # Act
    outcome = run_control_and_experiment(agent, settings.scenario, "task-1", "tool_degradation", 1)

    # Assert
    receipt = outcome.experiment.steps[0].fault
    assert receipt is not None
    assert receipt.verified is True
    assert receipt.recovered is True
    assert outcome.experiment.steps[0].recovered is True
    assert outcome.experiment.outcome.goal_achieved is True


def test_given_triggered_verification_fault_when_run_pair_then_verified_failure_recorded() -> None:
    # Arrange
    settings = load_settings()
    agent = ScriptedAgent(settings.scenario)

    # Act
    outcome = run_control_and_experiment(
        agent,
        settings.scenario,
        "task-1",
        "verification_failure",
        1,
    )

    # Assert
    receipt = outcome.experiment.steps[0].fault
    assert receipt is not None
    assert receipt.verified is True
    assert receipt.recovered is False
    assert outcome.experiment.outcome.goal_achieved is False


def test_given_untriggered_fault_when_run_pair_then_recovery_is_unavailable() -> None:
    # Arrange
    settings = load_settings()
    agent = ScriptedAgent(settings.scenario)

    # Act
    outcome = run_control_and_experiment(agent, settings.scenario, "task-1", "tool_degradation", 2)

    # Assert
    receipt = outcome.experiment.steps[0].fault
    assert receipt is not None
    assert receipt.triggered is False
    assert receipt.recovered is None
    assert outcome.experiment_vector.recovery.available is False


def test_given_same_pair_inputs_when_replayed_then_receipts_are_equivalent() -> None:
    # Arrange
    settings = load_settings()
    agent = ScriptedAgent(settings.scenario)

    # Act
    first = run_control_and_experiment(agent, settings.scenario, "task-1", "stale_data", 1)
    second = run_control_and_experiment(agent, settings.scenario, "task-1", "stale_data", 1)

    # Assert
    assert first.experiment.steps[0].fault == second.experiment.steps[0].fault


def test_given_run_pair_when_inspecting_receipts_then_pair_provenance_correlates() -> None:
    # Arrange
    settings = load_settings()
    agent = ScriptedAgent(settings.scenario)

    # Act
    outcome = run_control_and_experiment(agent, settings.scenario, "task-1", "stale_data", 1)

    # Assert
    control = outcome.control.steps[0].fault
    experiment = outcome.experiment.steps[0].fault
    assert control is not None
    assert experiment is not None
    assert control.control_pair_id == experiment.control_pair_id
    assert control.control_role == "control"
    assert experiment.control_role == "experiment"
    assert experiment.control_outcome is outcome.control.outcome.goal_achieved


# --- Level 5 (Multi-Agent) catalog additions (Phase 6, additive) -------------------------------


@pytest.mark.parametrize(
    "fault_id",
    [
        "agent_disagreement",
        "deadlock",
        "message_loss",
        "conflicting_objectives",
        "cascading_failure",
        "malicious_agent",
        "information_withholding",
        "unrequested_clarification_missing",
        "reasoning_action_mismatch",
    ],
)
def test_given_multi_agent_fault_id_when_get_fault_then_level_is_multi_agent(fault_id: str) -> None:
    # Act
    fault = catalog.get_fault(fault_id)

    # Assert
    assert fault.level == FaultLevel.MULTI_AGENT


def test_given_malicious_agent_fault_when_get_fault_then_family_is_security_adversarial() -> None:
    # Act
    fault = catalog.get_fault("malicious_agent")

    # Assert
    assert fault.family == FaultFamily.SECURITY_ADVERSARIAL


def test_given_multi_agent_level_faults_when_inspecting_then_none_use_the_runtime_dispatch_flag() -> (  # noqa: E501
    None
):
    # Arrange
    multi_agent_faults = [
        fault for fault in catalog.CATALOG if fault.level == FaultLevel.MULTI_AGENT
    ]

    # Assert: message_loss and information_withholding have real dispatch through
    # dedicated arise_x.chaos.injector functions (see test_multi_agent.py), not through
    # this single-agent runtime_dispatch/dispatch_fault gate.
    assert multi_agent_faults
    assert all(not fault.runtime_dispatch for fault in multi_agent_faults)


def test_given_multi_agent_catalog_entries_when_inspecting_then_use_coordination_injection_point() -> (  # noqa: E501
    None
):
    # Arrange
    multi_agent_faults = [
        fault for fault in catalog.CATALOG if fault.level == FaultLevel.MULTI_AGENT
    ]

    # Assert
    assert all(
        fault.injection_point == catalog.InjectionPoint.COORDINATION for fault in multi_agent_faults
    )
