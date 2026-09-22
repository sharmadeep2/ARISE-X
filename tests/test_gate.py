"""Unit tests for release-gate policy: geometric ARI, critical overrides, held-out-suite
validation, episode-level SLI classification, error-budget accounting, and the combined
release verdict (Step 5.2/5.3).
"""

from __future__ import annotations

import random
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from arise_x.drift.statistics import (
    DimensionTestConfig,
    DriftComparisonResult,
    RunObservation,
    compare_baseline_to_candidate,
)
from arise_x.scenarios import (
    DisruptionReference,
    EvaluationSuite,
    Horizon,
    Scenario,
    SuitePartition,
    SuiteReference,
    SuiteTask,
    Threshold,
)
from arise_x.telemetry.trajectory import (
    FaultTrigger,
    Outcome,
    OutcomeStatus,
    RecoveryEvidence,
    Step,
    Trajectory,
)
from arise_x.trust.gate import (
    CriticalMetricConfig,
    EpisodeSliOutcome,
    ErrorBudgetPolicy,
    ErrorBudgetState,
    GateOutcome,
    HeldOutSuiteError,
    ProductionEpisode,
    aggregate_reliability,
    classify_episode_sli,
    default_dimension_configs,
    evaluate_error_budget,
    evaluate_release,
    geometric_ari,
    production_window_policy,
    select_production_window,
    validate_held_out_suite,
)
from arise_x.trust.vector import (
    ConfidenceMetadata,
    DimensionScore,
    ReliabilityVector,
    VectorDimension,
)


def _score(
    dimension: VectorDimension,
    value: float,
    *,
    available: bool = True,
) -> DimensionScore:
    if not available:
        return DimensionScore.unavailable(dimension, evidence_total=1)
    return DimensionScore(
        dimension=dimension,
        value=value,
        available=True,
        evidence_count=1,
        evidence_total=1,
        confidence=ConfidenceMetadata(score=1.0, method="fixture_observation"),
        evidence_references=(f"fixture:{dimension.value}",),
    )


def _trajectory(
    task_id: str,
    cluster_id: str,
    *,
    repeat_id: str = "seed-0",
    suite_partition: str = "held_out",
    suite_id: str = "suite-1",
    suite_version: int = 1,
    goal_achieved: bool = True,
    policy_violations: int = 0,
    fault_id: str | None = None,
    fault_verified: bool = False,
    recovered: bool = False,
) -> Trajectory:
    fault = (
        FaultTrigger(
            fault_id=fault_id,
            verified=fault_verified,
            recovered=recovered if fault_verified else None,
            affected_evidence_references=(f"fixture:{task_id}:fault",) if fault_verified else (),
        )
        if fault_id
        else None
    )
    step = Step(
        index=0,
        action="decide",
        state_transition="idle->done",
        fault=fault,
        recovered=recovered,
        recovery=(
            RecoveryEvidence(
                fault_id=fault.fault_id,
                action="retry",
                successful=True,
                evidence_references=(f"fixture:{task_id}:recovery",),
            )
            if recovered and fault is not None and fault.verified
            else None
        ),
    )
    return Trajectory(
        run_id=f"run-{task_id}-{repeat_id}",
        task_id=task_id,
        family="procurement",
        cluster_id=cluster_id,
        suite_id=suite_id,
        suite_version=suite_version,
        suite_partition=suite_partition,
        repeat_id=repeat_id,
        scenario_name="procurement",
        scenario_version=1,
        agent_id="agent-1",
        agent_version="v1",
        steps=(step,),
        outcome=Outcome(
            goal_achieved=goal_achieved,
            label="done" if goal_achieved else "failed",
            status=OutcomeStatus.SUCCEEDED if goal_achieved else OutcomeStatus.FAILED,
            terminal_state="done",
            evidence_references=(f"fixture:{task_id}:outcome",),
        ),
        policy_violation_count=policy_violations,
    )


def _observation(
    task_id: str,
    cluster_id: str,
    dimension: VectorDimension,
    value: float,
    *,
    available: bool = True,
    suite_partition: str = "held_out",
    goal_achieved: bool = True,
    policy_violations: int = 0,
) -> RunObservation:
    trajectory = _trajectory(
        task_id,
        cluster_id,
        suite_partition=suite_partition,
        goal_achieved=goal_achieved,
        policy_violations=policy_violations,
    )
    scores = {
        dim.value: _score(dim, 0.5)
        for dim in VectorDimension
    }
    scores[dimension.value] = _score(dimension, value, available=available)
    return RunObservation(trajectory=trajectory, vector=ReliabilityVector(**scores))


def _scenario(*, suite_id: str = "suite-1", version: int = 1) -> Scenario:
    return Scenario(
        name="gate-test-scenario",
        version=1,
        objective="objective",
        constraints=(),
        expected_outcome="outcome",
        seed=1,
        horizons=(Horizon(label="24h"),),
        disruptions=(DisruptionReference(name="baseline"),),
        thresholds=(Threshold(name="trust", value=0.75), Threshold(name="drift", value=0.3)),
        suite_ref=SuiteReference(suite_id=suite_id, version=version),
    )


def _suite(
    *,
    suite_id: str = "suite-1",
    version: int = 1,
    rotation_deadline: str = "2099-12-31",
    held_out_tasks: tuple[SuiteTask, ...] = (SuiteTask(task_id="held-1", family="f", cluster="c"),),
) -> EvaluationSuite:
    return EvaluationSuite(
        suite_id=suite_id,
        version=version,
        owner="owner",
        rotation_deadline=rotation_deadline,
        access_policy="restricted",
        protected_payload_locator="locator",
        partitions=(
            SuitePartition(
                name="development",
                description="dev",
                tasks=(SuiteTask(task_id="dev-1", family="f", cluster="c"),),
            ),
            SuitePartition(name="held_out", description="held out", tasks=held_out_tasks),
        ),
    )


# --- Episode-level SLI classification -----------------------------------------------------


def test_given_success_no_violations_no_fault_when_classify_episode_sli_then_good() -> None:
    # Arrange
    trajectory = _trajectory("t1", "c1", goal_achieved=True, policy_violations=0)

    # Act
    outcome = classify_episode_sli(trajectory)

    # Assert
    assert outcome.eligible is True
    assert outcome.good is True


def test_given_goal_not_achieved_when_classify_episode_sli_then_bad() -> None:
    # Arrange
    trajectory = _trajectory("t1", "c1", goal_achieved=False)

    # Act
    outcome = classify_episode_sli(trajectory)

    # Assert
    assert outcome.good is False
    assert "goal" in outcome.reason


def test_given_safety_violation_when_classify_episode_sli_then_bad() -> None:
    # Arrange
    trajectory = _trajectory("t1", "c1", policy_violations=1)

    # Act
    outcome = classify_episode_sli(trajectory)

    # Assert
    assert outcome.good is False


def test_given_verified_fault_not_recovered_when_classify_episode_sli_then_bad() -> None:
    # Arrange
    trajectory = _trajectory(
        "t1", "c1", fault_id="latency_spike", fault_verified=True, recovered=False
    )

    # Act
    outcome = classify_episode_sli(trajectory)

    # Assert
    assert outcome.good is False
    assert "recovered" in outcome.reason


def test_given_verified_fault_recovered_when_classify_episode_sli_then_good() -> None:
    # Arrange
    trajectory = _trajectory(
        "t1", "c1", fault_id="latency_spike", fault_verified=True, recovered=True
    )

    # Act
    outcome = classify_episode_sli(trajectory)

    # Assert
    assert outcome.good is True


def test_given_unverified_fault_when_classify_episode_sli_then_recovery_not_required() -> None:
    # Arrange
    trajectory = _trajectory(
        "t1", "c1", fault_id="latency_spike", fault_verified=False, recovered=False
    )

    # Act
    outcome = classify_episode_sli(trajectory)

    # Assert
    assert outcome.good is True


# --- Error budget --------------------------------------------------------------------------


def test_given_budget_exactly_consumed_when_evaluate_error_budget_then_exhausted() -> None:
    # Arrange
    episodes = [
        EpisodeSliOutcome(task_id=f"t{i}", eligible=True, good=i < 18, reason="")
        for i in range(20)
    ]
    policy = ErrorBudgetPolicy(slo_target=0.9, window_episode_count=20)

    # Act
    state = evaluate_error_budget(episodes, policy)

    # Assert
    assert state.eligible_count == 20
    assert state.good_count == 18
    assert state.bad_count == 2
    assert state.allowed_bad == 2
    assert state.has_sufficient_data is True
    assert state.remaining_budget_ratio == pytest.approx(0.0)
    assert state.exhausted is True


def test_given_partial_consumption_when_evaluate_error_budget_then_ratio_reflects_remaining() -> (
    None
):
    # Arrange
    episodes = [
        EpisodeSliOutcome(task_id=f"t{i}", eligible=True, good=i < 19, reason="")
        for i in range(20)
    ]
    policy = ErrorBudgetPolicy(slo_target=0.9, window_episode_count=20)

    # Act
    state = evaluate_error_budget(episodes, policy)

    # Assert
    assert state.bad_count == 1
    assert state.allowed_bad == 2
    assert state.remaining_budget_ratio == pytest.approx(0.5)
    assert state.exhausted is False


def test_given_zero_eligible_episodes_when_evaluate_error_budget_then_no_data_state() -> None:
    # Arrange
    policy = ErrorBudgetPolicy(slo_target=0.9, window_episode_count=10)

    # Act
    state = evaluate_error_budget([], policy)

    # Assert
    assert state.eligible_count == 0
    assert state.has_sufficient_data is False
    assert state.remaining_budget_ratio is None
    assert state.exhausted is False


def test_given_fractional_budget_when_evaluate_error_budget_then_preserves_formula() -> None:
    # Arrange
    episodes = [EpisodeSliOutcome(task_id="t1", eligible=True, good=True, reason="")]
    policy = ErrorBudgetPolicy(slo_target=0.95, window_episode_count=1)

    # Act
    state = evaluate_error_budget(episodes, policy)

    # Assert
    assert state.allowed_bad == pytest.approx(0.05)
    assert state.has_sufficient_data is True
    assert state.remaining_budget_ratio == pytest.approx(1.0)


def test_given_slo_target_when_production_window_policy_then_uses_28_day_window() -> None:
    # Act
    policy = production_window_policy(0.95)

    # Assert
    assert policy.window_days == 28
    assert policy.window_episode_count is None


def test_given_timestamped_production_history_when_select_window_then_applies_calendar() -> None:
    # Arrange
    window_end = datetime(2026, 9, 22, tzinfo=UTC)
    episodes = tuple(
        ProductionEpisode(
            source_run_id="production",
            source_episode_id=f"episode-{index}",
            occurred_at=window_end - timedelta(days=age),
            outcome=EpisodeSliOutcome(f"task-{index}", True, True, "production"),
        )
        for index, age in enumerate((1, 10, 29))
    )
    policy = ErrorBudgetPolicy(0.95, window_days=28, minimum_eligible_count=2)

    # Act
    selected, inputs = select_production_window(episodes, policy, window_end=window_end)

    # Assert
    assert len(selected) == 2
    assert inputs["selected_episode_count"] == 2
    assert inputs["window_start"] == "2026-08-25T00:00:00+00:00"


# --- Geometric ARI --------------------------------------------------------------------------


def test_given_available_dimensions_when_geometric_ari_then_matches_manual_geometric_mean() -> (
    None
):
    # Arrange
    scores = (
        _score(VectorDimension.GOAL_SUCCESS, 0.9),
        _score(VectorDimension.SAFETY, 0.8),
        DimensionScore.unavailable(VectorDimension.RECOVERY),
    )

    # Act
    result = geometric_ari(scores)

    # Assert
    assert result == pytest.approx((0.9 * 0.8) ** 0.5)


def test_given_unavailable_dimension_when_geometric_ari_then_excluded_not_zero_or_one_filled() -> (
    None
):
    # Arrange
    scores = (
        _score(VectorDimension.GOAL_SUCCESS, 0.9),
        DimensionScore.unavailable(VectorDimension.SAFETY),
    )

    # Act
    result = geometric_ari(scores)

    # Assert
    assert result == pytest.approx(0.9)


def test_given_no_available_dimensions_when_geometric_ari_then_returns_none() -> None:
    # Arrange
    scores = (DimensionScore.unavailable(VectorDimension.GOAL_SUCCESS),)

    # Act
    result = geometric_ari(scores)

    # Assert
    assert result is None


def test_given_added_high_scoring_dimension_when_geometric_ari_then_does_not_collapse_like_raw_product() -> (  # noqa: E501
    None
):
    # Arrange
    base_scores = tuple(
        _score(dimension, 0.9)
        for dimension in (
            VectorDimension.GOAL_SUCCESS,
            VectorDimension.RESILIENCE,
            VectorDimension.BEHAVIORAL_STABILITY,
        )
    )
    extended_scores = base_scores + (
        _score(VectorDimension.EFFICIENCY, 0.95),
    )

    # Act
    base_ari = geometric_ari(base_scores)
    extended_ari = geometric_ari(extended_scores)
    raw_product_base = 0.9**3
    raw_product_extended = raw_product_base * 0.95

    # Assert: the geometric mean does not mechanically drop when a high-scoring
    # dimension is added (it can even rise), unlike the raw unadjusted product.
    assert extended_ari >= base_ari - 1e-9
    assert raw_product_extended < raw_product_base


# --- default_dimension_configs / aggregate_reliability --------------------------------------


def test_given_scenario_without_dimension_threshold_when_default_dimension_configs_then_uses_drift_fallback() -> (  # noqa: E501
    None
):
    # Arrange
    scenario = _scenario()

    # Act
    configs = default_dimension_configs(scenario, (VectorDimension.EFFICIENCY,))

    # Assert
    assert configs[VectorDimension.EFFICIENCY].tolerance == pytest.approx(0.3)
    assert configs[VectorDimension.EFFICIENCY].is_binary is False


def test_given_goal_success_when_default_dimension_configs_then_marked_binary() -> None:
    # Arrange
    scenario = _scenario()

    # Act
    configs = default_dimension_configs(scenario, (VectorDimension.GOAL_SUCCESS,))

    # Assert
    assert configs[VectorDimension.GOAL_SUCCESS].is_binary is True


def test_given_mixed_availability_vectors_when_aggregate_reliability_then_means_available_only() -> (  # noqa: E501
    None
):
    # Arrange
    first = ReliabilityVector(
        **{
            dim.value: _score(dim, 0.6)
            for dim in VectorDimension
        }
    )
    second_scores = {
        dim.value: _score(dim, 0.8)
        for dim in VectorDimension
    }
    second_scores[VectorDimension.SAFETY.value] = DimensionScore.unavailable(
        VectorDimension.SAFETY
    )
    second = ReliabilityVector(**second_scores)

    # Act
    aggregated = aggregate_reliability([first, second])

    # Assert
    aggregated_by_dimension = {score.dimension: score for score in aggregated}
    assert aggregated_by_dimension[VectorDimension.GOAL_SUCCESS].value == pytest.approx(0.7)
    assert aggregated_by_dimension[VectorDimension.SAFETY].value == pytest.approx(0.6)
    assert aggregated_by_dimension[VectorDimension.SAFETY].available is True


# --- Held-out-suite validation ---------------------------------------------------------------


def test_given_matching_suite_and_held_out_evidence_when_validate_held_out_suite_then_ok() -> None:
    # Arrange & Act & Assert (no raise)
    validate_held_out_suite(_scenario(), _suite(), evidence_partitions={"held_out"})


def test_given_development_only_evidence_when_validate_held_out_suite_then_raises() -> None:
    # Act & Assert
    with pytest.raises(HeldOutSuiteError, match="development"):
        validate_held_out_suite(_scenario(), _suite(), evidence_partitions={"development"})


def test_given_empty_held_out_partition_when_validate_held_out_suite_then_raises() -> None:
    # Arrange
    suite = _suite(held_out_tasks=())

    # Act & Assert
    with pytest.raises(HeldOutSuiteError, match="no tasks"):
        validate_held_out_suite(_scenario(), suite, evidence_partitions={"held_out"})


def test_given_expired_rotation_deadline_when_validate_held_out_suite_then_raises() -> None:
    # Arrange
    suite = _suite(rotation_deadline="2026-01-01")

    # Act & Assert
    with pytest.raises(HeldOutSuiteError, match="rotation deadline"):
        validate_held_out_suite(
            _scenario(), suite, evidence_partitions={"held_out"}, as_of=date(2027, 1, 1)
        )


def test_given_mismatched_suite_id_when_validate_held_out_suite_then_raises() -> None:
    # Arrange
    scenario = _scenario(suite_id="suite-1")
    suite = _suite(suite_id="suite-2")

    # Act & Assert
    with pytest.raises(HeldOutSuiteError, match="references suite"):
        validate_held_out_suite(scenario, suite, evidence_partitions={"held_out"})


def test_given_mismatched_suite_version_when_validate_held_out_suite_then_raises() -> None:
    # Arrange
    scenario = _scenario(version=1)
    suite = _suite(version=2)

    # Act & Assert
    with pytest.raises(HeldOutSuiteError, match="references suite"):
        validate_held_out_suite(scenario, suite, evidence_partitions={"held_out"})


# --- evaluate_release: pass / warn / block ---------------------------------------------------


def test_given_near_identical_baseline_and_candidate_when_evaluate_release_then_passes() -> None:
    # Arrange
    drift = _complete_comparison()
    production_budget = _independent_production_budget()

    # Act
    verdict = evaluate_release(
        drift, scenario=_scenario(), suite=_suite(), evidence_partitions={"held_out"},
        error_budget=production_budget,
    )

    # Assert
    assert verdict.outcome is GateOutcome.PASS
    assert verdict.critical_override_reasons == ()
    assert verdict.held_out_suite_reasons == ()
    assert verdict.non_critical_warning_reasons == ()
    assert verdict.error_budget is production_budget
    assert production_budget.remaining_budget_ratio == 1.0


def test_given_non_critical_material_drift_when_evaluate_release_then_warns() -> None:
    # Arrange
    rng = random.Random(2)
    baseline = []
    candidate = []
    for i in range(40):
        candidate_value = 0.5 - 0.3 + rng.uniform(-0.02, 0.02)
        baseline.append(_observation(
            f"task-{i}", f"cluster-{i}", VectorDimension.EFFICIENCY, 0.5
        ))
        candidate.append(
            _observation(
                f"task-{i}", f"cluster-{i}", VectorDimension.EFFICIENCY, candidate_value
            )
        )
    configs = {
        VectorDimension.EFFICIENCY: DimensionTestConfig(
            minimum_detectable_effect=0.05, tolerance=0.05
        ),
        VectorDimension.GOAL_SUCCESS: DimensionTestConfig(0.05, 0.05),
        VectorDimension.SAFETY: DimensionTestConfig(0.05, 0.05),
    }
    drift = compare_baseline_to_candidate("baseline-1", "candidate-1", baseline, candidate, configs)

    # Act
    verdict = evaluate_release(
        drift, scenario=_scenario(), suite=_suite(), evidence_partitions={"held_out"},
        error_budget=_independent_production_budget(),
    )

    # Assert
    assert verdict.outcome is GateOutcome.WARN
    assert verdict.non_critical_warning_reasons != ()
    assert verdict.critical_override_reasons == ()


@pytest.mark.parametrize("dimension", [VectorDimension.GOAL_SUCCESS, VectorDimension.SAFETY])
def test_given_critical_dimension_regression_when_evaluate_release_then_blocks(
    dimension: VectorDimension,
) -> None:
    # Arrange
    baseline = [_observation(f"task-{i}", "cluster-a", dimension, 1.0) for i in range(30)]
    candidate = [_observation(f"task-{i}", "cluster-a", dimension, 0.0) for i in range(30)]
    configs = {
        dimension: DimensionTestConfig(
            minimum_detectable_effect=0.05,
            tolerance=0.05,
            is_binary=(dimension.value == "goal_success"),
        )
    }
    drift = compare_baseline_to_candidate("baseline-1", "candidate-1", baseline, candidate, configs)

    # Act
    verdict = evaluate_release(
        drift, scenario=_scenario(), suite=_suite(), evidence_partitions={"held_out"}
    )

    # Assert
    assert verdict.outcome is GateOutcome.BLOCK
    assert len(verdict.critical_override_reasons) == 1
    assert dimension.value in verdict.critical_override_reasons[0]


def _independent_production_budget() -> ErrorBudgetState:
    """Already-windowed production fixture, never derived from candidate evidence."""
    return evaluate_error_budget(
        [EpisodeSliOutcome(f"production-{i}", True, True, "production") for i in range(20)],
        ErrorBudgetPolicy(slo_target=0.9, window_episode_count=20, minimum_eligible_count=20),
    )


def _complete_comparison() -> DriftComparisonResult:
    observations = [
        _observation(f"task-{i}", f"cluster-{i}", VectorDimension.GOAL_SUCCESS, 1.0)
        for i in range(20)
    ]
    configs = {dim: DimensionTestConfig(0.1, 0.05) for dim in (
        VectorDimension.GOAL_SUCCESS, VectorDimension.SAFETY, VectorDimension.EFFICIENCY
    )}
    return compare_baseline_to_candidate(
        "baseline", "candidate", observations, observations, configs
    )


@pytest.mark.parametrize("budget_kind", ["absent", "no-data", "below-minimum", "zero-allowed"])
def test_given_missing_production_evidence_when_gate_then_blocks(budget_kind) -> None:
    # Arrange
    budget = None
    if budget_kind != "absent":
        count = {"no-data": 0, "below-minimum": 10, "zero-allowed": 1}[budget_kind]
        budget = evaluate_error_budget(
            [EpisodeSliOutcome(f"production-{i}", True, True, "") for i in range(count)],
            ErrorBudgetPolicy(0.9, window_episode_count=20, minimum_eligible_count=20),
        )

    # Act
    verdict = evaluate_release(
        _complete_comparison(), scenario=_scenario(), suite=_suite(),
        evidence_partitions={"held_out"}, error_budget=budget,
    )

    # Assert
    assert verdict.blocked
    assert verdict.error_budget_reasons
    assert not verdict.error_budget_exhausted


@pytest.mark.parametrize(
    "gap", ["empty", "critical", "required", "underpowered", "task", "cluster"]
)
def test_given_release_evidence_gap_when_gate_then_blocks(gap) -> None:
    # Arrange
    drift = _complete_comparison()
    results = list(drift.dimension_results)
    if gap == "empty":
        results = []
    elif gap in {"critical", "required"}:
        missing = VectorDimension.SAFETY if gap == "critical" else VectorDimension.EFFICIENCY
        results = [result for result in results if result.dimension != missing]
    else:
        change = {
            "underpowered": {"insufficient_power": True, "achieved_power": 0.1},
            "task": {"paired_task_count": 1, "achieved_power": 1.0},
            "cluster": {"effective_cluster_count": 1, "achieved_power": 1.0},
        }[gap]
        results[-1] = replace(results[-1], **change)

    # Act
    verdict = evaluate_release(
        replace(drift, dimension_results=tuple(results)), scenario=_scenario(), suite=_suite(),
        evidence_partitions={"held_out"}, error_budget=_independent_production_budget(),
        required_dimensions=(VectorDimension.EFFICIENCY,),
    )

    # Assert
    assert verdict.blocked
    assert verdict.required_evidence_reasons


def test_given_mixed_partitions_when_validate_held_out_then_rejected() -> None:
    # Act & Assert
    with pytest.raises(HeldOutSuiteError):
        validate_held_out_suite(
            _scenario(), _suite(), evidence_partitions={"held_out", "development"}
        )


def test_given_critical_dimension_missing_evidence_when_evaluate_release_then_fails_safe() -> None:
    # Arrange: SAFETY is entirely unavailable for every task, so there is no
    # paired evidence for it at all.
    baseline = [
        _observation(f"task-{i}", "cluster-a", VectorDimension.SAFETY, 0.9, available=False)
        for i in range(10)
    ]
    candidate = [
        _observation(f"task-{i}", "cluster-a", VectorDimension.SAFETY, 0.9, available=False)
        for i in range(10)
    ]
    configs = {
        VectorDimension.SAFETY: DimensionTestConfig(minimum_detectable_effect=0.05, tolerance=0.05)
    }
    drift = compare_baseline_to_candidate("baseline-1", "candidate-1", baseline, candidate, configs)

    # Act
    verdict = evaluate_release(
        drift, scenario=_scenario(), suite=_suite(), evidence_partitions={"held_out"}
    )

    # Assert: absence of evidence must never silently pass.
    assert verdict.outcome is GateOutcome.BLOCK
    assert verdict.critical_override_reasons != ()


def test_given_critical_dimension_insufficient_power_when_evaluate_release_then_fails_safe() -> (
    None
):
    # Arrange: too few paired tasks for the requested minimum detectable effect.
    diffs = [0.28, 0.32, 0.29, 0.31]
    baseline = [
        _observation(f"task-{i}", "cluster-a", VectorDimension.SAFETY, 0.5) for i in range(4)
    ]
    candidate = [
        _observation(f"task-{i}", "cluster-a", VectorDimension.SAFETY, 0.5 + diffs[i])
        for i in range(4)
    ]
    configs = {
        VectorDimension.SAFETY: DimensionTestConfig(minimum_detectable_effect=0.01, tolerance=0.05)
    }
    drift = compare_baseline_to_candidate("baseline-1", "candidate-1", baseline, candidate, configs)
    assert drift.dimension(VectorDimension.SAFETY).insufficient_power is True

    # Act
    verdict = evaluate_release(
        drift, scenario=_scenario(), suite=_suite(), evidence_partitions={"held_out"}
    )

    # Assert: inadequate power for a critical dimension must never silently pass.
    assert verdict.outcome is GateOutcome.BLOCK
    assert verdict.critical_override_reasons != ()


def test_given_development_only_evidence_when_evaluate_release_then_blocks_with_held_out_reason() -> (  # noqa: E501
    None
):
    # Arrange
    baseline = [
        _observation(
            f"task-{i}",
            "cluster-a",
            VectorDimension.GOAL_SUCCESS,
            1.0,
            suite_partition="development",
        )
        for i in range(10)
    ]
    candidate = [
        _observation(
            f"task-{i}",
            "cluster-a",
            VectorDimension.GOAL_SUCCESS,
            1.0,
            suite_partition="development",
        )
        for i in range(10)
    ]
    configs = {
        VectorDimension.GOAL_SUCCESS: DimensionTestConfig(
            minimum_detectable_effect=0.05, tolerance=0.05, is_binary=True
        )
    }
    drift = compare_baseline_to_candidate("baseline-1", "candidate-1", baseline, candidate, configs)

    # Act
    verdict = evaluate_release(
        drift, scenario=_scenario(), suite=_suite(), evidence_partitions={"development"}
    )

    # Assert
    assert verdict.outcome is GateOutcome.BLOCK
    assert verdict.held_out_suite_reasons != ()
    assert verdict.critical_override_reasons != ()


def test_given_exhausted_error_budget_when_evaluate_release_then_blocks_independently_of_drift() -> (  # noqa: E501
    None
):
    # Arrange: a clean, non-regressing drift comparison, but an already
    # exhausted trailing production error budget.
    baseline = [
        _observation(f"task-{i}", f"cluster-{i}", VectorDimension.GOAL_SUCCESS, 1.0)
        for i in range(20)
    ]
    candidate = [
        _observation(f"task-{i}", f"cluster-{i}", VectorDimension.GOAL_SUCCESS, 1.0)
        for i in range(20)
    ]
    configs = {
        VectorDimension.GOAL_SUCCESS: DimensionTestConfig(
            minimum_detectable_effect=0.05, tolerance=0.05, is_binary=True
        )
    }
    drift = compare_baseline_to_candidate("baseline-1", "candidate-1", baseline, candidate, configs)
    error_budget = ErrorBudgetState(
        policy=ErrorBudgetPolicy(slo_target=0.9, window_episode_count=10),
        eligible_count=10,
        good_count=5,
        bad_count=5,
        allowed_bad=1,
        has_sufficient_data=True,
        remaining_budget_ratio=0.0,
        exhausted=True,
    )

    # Act
    verdict = evaluate_release(
        drift,
        scenario=_scenario(),
        suite=_suite(),
        evidence_partitions={"held_out"},
        error_budget=error_budget,
    )

    # Assert: the exhausted budget alone blocks, and is reported independently
    # of (not merged with) critical-dimension/held-out-suite reasons.
    assert verdict.outcome is GateOutcome.BLOCK
    assert verdict.error_budget_exhausted is True
    assert verdict.critical_override_reasons == ()
    assert verdict.held_out_suite_reasons == ()


def test_given_critical_regression_and_exhausted_budget_when_evaluate_release_then_reasons_independent() -> (  # noqa: E501
    None
):
    # Arrange: both a critical held-out regression and an exhausted budget.
    baseline = [
        _observation(f"task-{i}", "cluster-a", VectorDimension.GOAL_SUCCESS, 1.0)
        for i in range(30)
    ]
    candidate = [
        _observation(f"task-{i}", "cluster-a", VectorDimension.GOAL_SUCCESS, 0.0)
        for i in range(30)
    ]
    configs = {
        VectorDimension.GOAL_SUCCESS: DimensionTestConfig(
            minimum_detectable_effect=0.05, tolerance=0.05, is_binary=True
        )
    }
    drift = compare_baseline_to_candidate("baseline-1", "candidate-1", baseline, candidate, configs)
    error_budget = ErrorBudgetState(
        policy=ErrorBudgetPolicy(slo_target=0.9, window_episode_count=10),
        eligible_count=10,
        good_count=5,
        bad_count=5,
        allowed_bad=1,
        has_sufficient_data=True,
        remaining_budget_ratio=0.0,
        exhausted=True,
    )

    # Act
    verdict = evaluate_release(
        drift,
        scenario=_scenario(),
        suite=_suite(),
        evidence_partitions={"held_out"},
        error_budget=error_budget,
    )

    # Assert: both failure modes are present, reported as independent, separately
    # labeled reasons rather than merged into one opaque flag.
    assert verdict.outcome is GateOutcome.BLOCK
    assert verdict.critical_override_reasons != ()
    assert verdict.error_budget_exhausted is True
    assert not any("budget" in reason.lower() for reason in verdict.critical_override_reasons)


def test_given_critical_config_override_tolerance_when_evaluate_release_then_stricter_tolerance_applies() -> (  # noqa: E501
    None
):
    # Arrange: a small, statistically detectable regression that the base
    # tolerance would tolerate but a stricter critical override rejects.
    rng = random.Random(3)
    baseline = []
    candidate = []
    for i in range(60):
        candidate_value = 0.5 - 0.02 + rng.uniform(-0.001, 0.001)
        baseline.append(_observation(f"task-{i}", "cluster-a", VectorDimension.SAFETY, 0.5))
        candidate.append(
            _observation(f"task-{i}", "cluster-a", VectorDimension.SAFETY, candidate_value)
        )
    configs = {
        VectorDimension.SAFETY: DimensionTestConfig(minimum_detectable_effect=0.01, tolerance=0.05)
    }
    drift = compare_baseline_to_candidate("baseline-1", "candidate-1", baseline, candidate, configs)
    assert drift.dimension(VectorDimension.SAFETY).material_drift is False

    critical_config = CriticalMetricConfig(
        critical_dimensions=frozenset({VectorDimension.SAFETY}),
        regression_tolerance=((VectorDimension.SAFETY, 0.01),),
    )

    # Act
    verdict = evaluate_release(
        drift,
        scenario=_scenario(),
        suite=_suite(),
        evidence_partitions={"held_out"},
        critical_config=critical_config,
    )

    # Assert
    assert verdict.outcome is GateOutcome.BLOCK
