"""Unit tests for the typed fault catalog, verified dispatch, and control/experiment pairing."""

from __future__ import annotations

import random
from dataclasses import replace

import pytest

from arise_x.agents.scripted import ScriptedAgent
from arise_x.chaos import catalog
from arise_x.chaos.catalog import FaultCatalogError, FaultFamily, FaultLevel
from arise_x.chaos.injector import dispatch_fault
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


def test_given_unknown_fault_id_when_resolve_fault_then_falls_back_to_baseline() -> None:
    # Act
    resolved = catalog.resolve_fault("does_not_exist")

    # Assert
    assert resolved == catalog.BASELINE


def test_given_catalog_when_checking_dispatched_ids_then_only_mvp_three_dispatched() -> None:
    # Assert
    assert catalog.DISPATCHED_FAULT_IDS == {"baseline", "latency_spike", "tool_degradation"}


def test_given_data_and_agent_level_faults_when_inspecting_then_none_are_dispatched() -> None:
    # Arrange
    future_levels = {FaultLevel.DATA, FaultLevel.AGENT}

    # Act
    future_faults = [fault for fault in catalog.CATALOG if fault.level in future_levels]

    # Assert
    assert future_faults
    assert all(not fault.runtime_dispatch for fault in future_faults)


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


def test_given_non_dispatched_fault_when_dispatch_fault_then_raises_not_implemented_error() -> None:
    # Act / Assert
    with pytest.raises(NotImplementedError):
        dispatch_fault(
            catalog.STALE_DATA,
            base_failure_rate=0.08,
            control_success=True,
            rng=random.Random(1),
        )


def test_given_guaranteed_trigger_and_successful_control_when_dispatch_then_verified() -> None:
    # Arrange
    fault = replace(catalog.LATENCY_SPIKE, failure_boost=1.0)

    # Act
    result = dispatch_fault(
        fault, base_failure_rate=0.0, control_success=True, rng=random.Random(1)
    )

    # Assert
    assert result.triggered is True
    assert result.verified is True


def test_given_guaranteed_trigger_and_failing_control_when_dispatch_fault_then_unverified() -> None:
    # Arrange
    fault = replace(catalog.LATENCY_SPIKE, failure_boost=1.0)

    # Act
    result = dispatch_fault(
        fault, base_failure_rate=0.0, control_success=False, rng=random.Random(1)
    )

    # Assert: the fault fired, but it cannot be credited with the failure
    # because the control response would have failed regardless -- a
    # triggered-but-unverified trigger, distinguishable from a verified one.
    assert result.triggered is True
    assert result.verified is False


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


def test_given_real_fault_active_when_run_control_and_experiment_then_latency_distribution_differs() -> (  # noqa: E501
    None
):
    # Arrange
    settings = load_settings()
    agent = ScriptedAgent(settings.scenario)

    # Act
    outcome = run_control_and_experiment(agent, settings.scenario, "task-1", "tool_degradation", 7)

    # Assert: both executions share a seed, so the underlying draw is
    # identical; tool_degradation's 1.4x latency_multiplier scales it away
    # from the unscaled (1.0x) baseline control, a differing outcome
    # distribution attributable only to the active fault.
    assert outcome.experiment.total_latency_ms == pytest.approx(
        outcome.control.total_latency_ms * 1.4
    )


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
