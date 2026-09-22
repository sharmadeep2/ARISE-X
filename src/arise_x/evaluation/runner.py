"""Reliability run orchestrator for ARISE-X."""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING
from uuid import uuid4

from arise_x.agents.base import AgentResponse, AgentUnderTest
from arise_x.agents.multi_agent import Coordinator, MacsScore, MultiAgentEpisode
from arise_x.agents.scripted import ScriptedAgent
from arise_x.chaos import catalog
from arise_x.chaos.injector import FaultDispatchResult, dispatch_fault
from arise_x.config import Settings
from arise_x.drift.detector import detect_drift
from arise_x.scenarios import EvaluationSuite, Scenario
from arise_x.telemetry.events import RunEvent
from arise_x.telemetry.trajectory import (
    FaultTrigger,
    Outcome,
    Step,
    ToolInvocation,
    Trajectory,
    UsageMetrics,
)
from arise_x.trust.scorer import score_trust
from arise_x.trust.vector import DimensionScore, ReliabilityVector, VectorDimension

if TYPE_CHECKING:
    from arise_x.storage.repository import RunRepository

_BASE_FAILURE_RATE = 0.08

# run_reliability_loop() keeps its list[IterationResult] return contract for
# compatibility, so trajectories built there are never persisted; they use
# this fixed placeholder instead of a real run ID. Use
# execute_and_persist_run() to obtain trajectories/vectors tied to a real,
# persisted run ID.
_UNPERSISTED_RUN_ID = "unpersisted"

# Per-task cluster attribution is not modeled yet: every task in a run is
# tagged with the scenario's first declared cluster reference (or this
# default when the scenario declares none) rather than a task-specific one.
_DEFAULT_CLUSTER_FAMILY = "unclustered"
_DEFAULT_CLUSTER_ID = "unclustered"

# Loop-generated tasks are treated as tuning-visible synthetic runs, not the
# evaluation suite's held-out partition, until suite-driven task selection
# lands.
_DEFAULT_SUITE_PARTITION = "development"

# Heuristic token/cost/latency proxies: the scripted agent reports no real
# model billing or token usage, so cost and efficiency are derived from
# response text length and measured latency instead.
_TOKEN_COST_USD = 0.000002
_EFFICIENCY_LATENCY_BUDGET_MS = 2500.0
_COST_BUDGET_USD = 0.01


@dataclass(frozen=True)
class IterationResult:
    """Summary for one simulation iteration."""

    task_id: str
    disruption: str
    drift_score: float
    trust_score: float
    trustworthy: bool


@dataclass(frozen=True)
class RunOutcome:
    """Persisted run identity, provenance metadata, and iteration results."""

    run_id: str
    scenario_version: str
    agent_version: str
    config_fingerprint: str
    seed: int
    results: list[IterationResult]
    trajectories: list[Trajectory] = field(default_factory=list)
    vectors: list[ReliabilityVector] = field(default_factory=list)


@dataclass(frozen=True)
class _TaskExecution:
    """One task's iteration result paired with its trajectory and reliability vector."""

    result: IterationResult
    trajectory: Trajectory
    vector: ReliabilityVector


def default_agent(scenario: Scenario) -> AgentUnderTest:
    """Return the deterministic scripted agent used when no agent is injected."""

    return ScriptedAgent(scenario)


def _build_prompt(scenario: Scenario, task_id: str) -> str:
    """Build a deterministic prompt for a task from the scenario definition."""

    constraints = "; ".join(scenario.constraints)
    return (
        f"Task {task_id} for scenario '{scenario.name}'. Objective: {scenario.objective} "
        f"Constraints: {constraints} Expected outcome: {scenario.expected_outcome}"
    )


def _resolve_cluster(scenario: Scenario) -> tuple[str, str]:
    """Resolve the task-family/cluster identifier used for trajectory evidence.

    Uses the scenario's first declared cluster reference, since per-task
    cluster assignment is not modeled yet; falls back to a stable
    "unclustered" default when the scenario declares none.
    """

    if scenario.cluster_refs:
        cluster = scenario.cluster_refs[0]
        return cluster.family, cluster.cluster_id
    return _DEFAULT_CLUSTER_FAMILY, _DEFAULT_CLUSTER_ID


def _clamp_unit(value: float) -> float:
    """Clamp a value into the [0.0, 1.0] range required by DimensionScore."""

    return max(0.0, min(1.0, value))


def _usage_metrics(prompt: str, output_text: str, *, latency_ms: float) -> UsageMetrics:
    """Heuristic token/cost usage shared by single-agent and multi-agent trajectory building.

    Derived from prompt/response text length and measured latency, since no
    real model billing or token usage exists yet.
    """

    prompt_tokens = len(prompt.split())
    completion_tokens = len(output_text.split())
    return UsageMetrics(
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=(prompt_tokens + completion_tokens) * _TOKEN_COST_USD,
    )


def _build_trajectory(
    *,
    agent: AgentUnderTest,
    scenario: Scenario,
    run_id: str,
    task_id: str,
    disruption: str,
    seed: int,
    prompt: str,
    response: AgentResponse,
    dispatch_result: FaultDispatchResult,
    latency_ms: float,
    success: bool,
    policy_violations: int,
    interventions: int,
) -> Trajectory:
    """Build a single-step trajectory correlating one task's execution evidence.

    Each task currently produces exactly one State -> Action -> Response ->
    Final State step because the deterministic scripted agent returns a
    single response per task; multi-step, tool-using trajectories will
    appear once tool-using agents are introduced. Token and cost usage are
    heuristic proxies derived from response text length, since no real model
    billing exists yet.
    """

    family, cluster_id = _resolve_cluster(scenario)
    agent_id = type(agent).__name__
    agent_version = str(getattr(agent, "version", agent_id))

    # A fault is only "checked for" when a non-baseline disruption profile is
    # active; verified reflects the catalog dispatch's trigger-verification
    # outcome (arise_x.chaos.injector.dispatch_fault), not just the raw
    # sampled trigger.
    fault = (
        FaultTrigger(fault_id=dispatch_result.fault_id, verified=dispatch_result.verified)
        if disruption != catalog.BASELINE.fault_id
        else None
    )
    usage = _usage_metrics(prompt, response.output_text, latency_ms=latency_ms)
    step = Step(
        index=0,
        action="run_task",
        state_transition="dispatched->completed",
        fault=fault,
        recovered=fault is not None and fault.verified and success,
        usage=usage,
        prompt_text=prompt,
        output_text=response.output_text,
    )
    outcome = Outcome(goal_achieved=success, label="goal_achieved" if success else "goal_failed")

    return Trajectory(        run_id=run_id,
        task_id=task_id,
        family=family,
        cluster_id=cluster_id,
        suite_id=scenario.suite_ref.suite_id,
        suite_version=scenario.suite_ref.version,
        suite_partition=_DEFAULT_SUITE_PARTITION,
        repeat_id=f"seed-{seed}",
        scenario_name=scenario.name,
        scenario_version=scenario.version,
        agent_id=agent_id,
        agent_version=agent_version,
        steps=(step,),
        outcome=outcome,
        intervention_count=interventions,
        policy_violation_count=policy_violations,
    )


def _build_reliability_vector(
    trajectory: Trajectory, *, chaos_triggered: bool
) -> ReliabilityVector:
    """Derive a per-task Agent Reliability Vector from trajectory evidence.

    This is a simple, task-scoped derivation, not the verified
    fault-injection or statistical-baseline semantics that land in later
    phases:

    * goal_success/safety come directly from the trajectory outcome and
      policy-violation count.
    * resilience reflects whether the task still succeeded under whatever
      disruption profile was active.
    * recovery is only reported when a configured fault's trigger was
      verified (see ``dispatch_fault``'s control-vs-experiment check); it is
      unavailable otherwise so a fault-free task never fabricates a recovery
      value.
    * behavioral_stability has no historical baseline yet (Phase 5 drift
      work) and is always reported unavailable here.
    * efficiency/cost/autonomy are heuristic proxies derived from the
      trajectory's timing/usage roll-up and intervention count.
    """

    evidence_count = len(trajectory.steps)
    success = trajectory.outcome.goal_achieved

    goal_success = DimensionScore(
        dimension=VectorDimension.GOAL_SUCCESS,
        value=1.0 if success else 0.0,
        available=True,
        evidence_count=evidence_count,
    )
    resilience = DimensionScore(
        dimension=VectorDimension.RESILIENCE,
        value=1.0 if success else 0.0,
        available=True,
        evidence_count=evidence_count,
    )
    behavioral_stability = DimensionScore.unavailable(VectorDimension.BEHAVIORAL_STABILITY)
    recovery = (
        DimensionScore(
            dimension=VectorDimension.RECOVERY,
            value=1.0 if success else 0.0,
            available=True,
            evidence_count=evidence_count,
        )
        if chaos_triggered
        else DimensionScore.unavailable(VectorDimension.RECOVERY)
    )
    safety = DimensionScore(
        dimension=VectorDimension.SAFETY,
        value=_clamp_unit(1.0 - trajectory.policy_violation_count * 0.2),
        available=True,
        evidence_count=evidence_count,
    )
    efficiency = DimensionScore(
        dimension=VectorDimension.EFFICIENCY,
        value=_clamp_unit(1.0 - trajectory.total_latency_ms / _EFFICIENCY_LATENCY_BUDGET_MS),
        available=True,
        evidence_count=evidence_count,
    )
    cost = DimensionScore(
        dimension=VectorDimension.COST,
        value=_clamp_unit(1.0 - trajectory.total_cost_usd / _COST_BUDGET_USD),
        available=True,
        evidence_count=evidence_count,
    )
    autonomy = DimensionScore(
        dimension=VectorDimension.AUTONOMY,
        value=_clamp_unit(1.0 - trajectory.intervention_count * 0.25),
        available=True,
        evidence_count=evidence_count,
    )

    return ReliabilityVector(
        goal_success=goal_success,
        resilience=resilience,
        behavioral_stability=behavioral_stability,
        recovery=recovery,
        safety=safety,
        efficiency=efficiency,
        cost=cost,
        autonomy=autonomy,
    )


def _execute_task(
    agent: AgentUnderTest,
    scenario: Scenario,
    run_id: str,
    task_id: str,
    disruption: str,
    seed: int,
    random_source: random.Random,
) -> tuple[Trajectory, ReliabilityVector]:
    """Execute one task through the agent and dispatch the resolved catalog fault."""

    prompt = _build_prompt(scenario, task_id)
    response = agent.run_task(task_id, prompt)

    fault_definition = catalog.resolve_fault(disruption)
    dispatch_result = dispatch_fault(
        fault_definition,
        base_failure_rate=_BASE_FAILURE_RATE,
        control_success=response.success,
        rng=random_source,
    )
    latency = random_source.uniform(300, 1200) * dispatch_result.latency_multiplier

    success = response.success and not dispatch_result.triggered
    policy_violations = response.policy_violations + (
        random_source.randint(0, 2) if dispatch_result.triggered else 0
    )
    interventions = response.interventions + (
        random_source.randint(1, 3) if dispatch_result.triggered else 0
    )

    trajectory = _build_trajectory(
        agent=agent,
        scenario=scenario,
        run_id=run_id,
        task_id=task_id,
        disruption=disruption,
        seed=seed,
        prompt=prompt,
        response=response,
        dispatch_result=dispatch_result,
        latency_ms=latency,
        success=success,
        policy_violations=policy_violations,
        interventions=interventions,
    )
    vector = _build_reliability_vector(trajectory, chaos_triggered=dispatch_result.verified)
    return trajectory, vector


@dataclass(frozen=True)
class ControlExperimentResult:
    """Paired no-fault control and faulted-experiment evidence for one task.

    Both executions use an independent ``random.Random(seed)`` instance so
    the agent's own response and any non-chaos randomness are aligned; only
    the active fault differs, isolating its effect for control-vs-experiment
    comparison. Neither execution is persisted; callers that need persisted
    evidence should use ``execute_and_persist_run`` separately.
    """

    control: Trajectory
    control_vector: ReliabilityVector
    experiment: Trajectory
    experiment_vector: ReliabilityVector


def run_control_and_experiment(
    agent: AgentUnderTest,
    scenario: Scenario,
    task_id: str,
    fault_id: str,
    seed: int,
    *,
    run_id: str = _UNPERSISTED_RUN_ID,
) -> ControlExperimentResult:
    """Execute one task twice: a fault-free control and an experiment with ``fault_id`` active.

    Args:
        agent: Agent under test.
        scenario: Scenario the task belongs to.
        task_id: Task identifier shared by both executions.
        fault_id: Catalog fault_id (see :mod:`arise_x.chaos.catalog`) to
            activate for the experiment execution; resolves through
            :func:`arise_x.chaos.catalog.resolve_fault` like any other
            disruption reference.
        seed: Seed shared by both executions' independent random sources.
        run_id: Correlation identifier attached to both trajectories;
            defaults to the same unpersisted placeholder ``run_reliability_loop``
            uses.
    """

    control_trajectory, control_vector = _execute_task(
        agent, scenario, run_id, task_id, catalog.BASELINE.fault_id, seed, random.Random(seed)
    )
    experiment_trajectory, experiment_vector = _execute_task(
        agent, scenario, run_id, task_id, fault_id, seed, random.Random(seed)
    )
    return ControlExperimentResult(
        control=control_trajectory,
        control_vector=control_vector,
        experiment=experiment_trajectory,
        experiment_vector=experiment_vector,
    )


def _run_tasks(
    iterations: int,
    scenario: Scenario,
    agent: AgentUnderTest,
    random_source: random.Random,
    settings: Settings,
    *,
    run_id: str,
    seed: int,
) -> list[_TaskExecution]:
    """Execute every task in the loop, pairing each result with its trajectory/vector evidence."""

    disruptions = [reference.resolved_fault_id for reference in scenario.disruptions]
    executions: list[_TaskExecution] = []

    for index in range(iterations):
        task_id = f"task-{index + 1}"
        disruption = disruptions[index % len(disruptions)]
        trajectory, vector = _execute_task(
            agent, scenario, run_id, task_id, disruption, seed, random_source
        )
        event = RunEvent.from_trajectory(trajectory)
        drift = detect_drift(event, threshold=settings.drift_threshold)
        trust = score_trust(event, drift, threshold=settings.trust_threshold)
        result = IterationResult(
            task_id=task_id,
            disruption=disruption,
            drift_score=drift.score,
            trust_score=trust.score,
            trustworthy=trust.trustworthy,
        )
        executions.append(_TaskExecution(result=result, trajectory=trajectory, vector=vector))

    return executions


def run_reliability_loop(
    iterations: int,
    settings: Settings,
    *,
    agent: AgentUnderTest | None = None,
    scenario: Scenario | None = None,
    random_source: random.Random | None = None,
) -> list[IterationResult]:
    """Run baseline and disruption scenarios for a fixed number of iterations.

    Args:
        iterations: Number of tasks to execute.
        settings: Loaded application settings; ``settings.scenario`` supplies the
            default scenario, thresholds, and disruption sequence when
            ``scenario`` is not provided.
        agent: Agent under test; defaults to a deterministic scripted agent
            built from the resolved scenario.
        scenario: Overrides ``settings.scenario`` when provided.
        random_source: Seeded random source for chaos sampling; defaults to
            ``random.Random(scenario.seed)`` so repeated calls with the same
            scenario and seed are fully reproducible.

    Each task also produces a trajectory and reliability vector internally
    (see :mod:`arise_x.telemetry.trajectory` and :mod:`arise_x.trust.vector`),
    but this function's return type stays the 5-field ``IterationResult``
    list for compatibility with existing callers. Use
    ``execute_and_persist_run`` to retrieve trajectory/vector evidence tied
    to a real, persisted run ID.

    Raises:
        ValueError: If neither ``scenario`` nor ``settings.scenario`` is available.
    """

    resolved_scenario = scenario if scenario is not None else settings.scenario
    if resolved_scenario is None:
        raise ValueError(
            "run_reliability_loop requires a scenario; pass scenario= explicitly or "
            "use Settings produced by load_settings()."
        )

    resolved_agent = agent if agent is not None else default_agent(resolved_scenario)
    resolved_random = (
        random_source if random_source is not None else random.Random(resolved_scenario.seed)
    )

    executions = _run_tasks(
        iterations,
        resolved_scenario,
        resolved_agent,
        resolved_random,
        settings,
        run_id=_UNPERSISTED_RUN_ID,
        seed=resolved_scenario.seed,
    )
    return [execution.result for execution in executions]


def _config_fingerprint(scenario: Scenario, evaluation_suite: EvaluationSuite | None) -> str:
    """Compute a deterministic content hash covering scenario and suite configuration."""

    payload: dict[str, object] = {"scenario": asdict(scenario)}
    if evaluation_suite is not None:
        payload["suite"] = asdict(evaluation_suite)
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def execute_and_persist_run(
    iterations: int,
    settings: Settings,
    repository: RunRepository,
    *,
    agent: AgentUnderTest | None = None,
    scenario: Scenario | None = None,
    seed: int | None = None,
    run_id: str | None = None,
) -> RunOutcome:
    """Run the reliability loop and persist it with deterministic provenance metadata.

    Args:
        iterations: Number of tasks to execute.
        settings: Loaded application settings.
        repository: Versioned run repository used for persistence.
        agent: Agent under test; defaults to a deterministic scripted agent.
        scenario: Overrides ``settings.scenario`` when provided.
        seed: Overrides the resolved scenario's seed for chaos sampling.
        run_id: Overrides the repository-generated run identifier.

    Raises:
        ValueError: If neither ``scenario`` nor ``settings.scenario`` is available.
    """

    resolved_scenario = scenario if scenario is not None else settings.scenario
    if resolved_scenario is None:
        raise ValueError(
            "execute_and_persist_run requires a scenario; pass scenario= explicitly or "
            "use Settings produced by load_settings()."
        )

    resolved_agent = agent if agent is not None else default_agent(resolved_scenario)
    resolved_seed = seed if seed is not None else resolved_scenario.seed
    resolved_run_id = run_id if run_id is not None else uuid4().hex
    random_source = random.Random(resolved_seed)

    executions = _run_tasks(
        iterations,
        resolved_scenario,
        resolved_agent,
        random_source,
        settings,
        run_id=resolved_run_id,
        seed=resolved_seed,
    )
    results = [execution.result for execution in executions]
    trajectories = [execution.trajectory for execution in executions]
    vectors = [execution.vector for execution in executions]

    agent_version = str(getattr(resolved_agent, "version", type(resolved_agent).__name__))
    scenario_version = f"{resolved_scenario.name}@{resolved_scenario.version}"
    config_fingerprint = _config_fingerprint(resolved_scenario, settings.evaluation_suite)

    metadata = repository.write_run(
        results,
        run_id=resolved_run_id,
        scenario_version=scenario_version,
        agent_version=agent_version,
        config_fingerprint=config_fingerprint,
        seed=resolved_seed,
        trajectories=trajectories,
        vectors=vectors,
    )

    return RunOutcome(
        run_id=metadata.run_id,
        scenario_version=scenario_version,
        agent_version=agent_version,
        config_fingerprint=config_fingerprint,
        seed=resolved_seed,
        results=results,
        trajectories=trajectories,
        vectors=vectors,
    )


@dataclass(frozen=True)
class MultiAgentRunOutcome:
    """Result of one or more star-topology multi-agent episodes.

    Strictly additive and opt-in: single-agent execution
    (``run_reliability_loop``, ``execute_and_persist_run``) is unchanged and
    unaffected by this type or by :func:`run_multi_agent_reliability_loop`.
    Episodes are ephemeral in this phase -- ``storage/repository.py`` does
    not persist them (see docs/architecture.md for the scope rationale);
    callers that need durable multi-agent evidence must persist the
    returned trajectories/vectors/episodes themselves.
    """

    episodes: list[MultiAgentEpisode]
    trajectories: list[Trajectory]
    vectors: list[ReliabilityVector]
    macs_scores: list[MacsScore]


def _build_multi_agent_trajectory(
    episode: MultiAgentEpisode,
    *,
    scenario: Scenario,
    run_id: str,
    seed: int,
) -> Trajectory:
    """Build a multi-step trajectory correlating one multi-agent episode's evidence.

    One :class:`~arise_x.telemetry.trajectory.Step` per worker assignment
    records that worker's sub-task prompt and response as a
    :class:`~arise_x.telemetry.trajectory.ToolInvocation` -- workers are
    treated as the "tool" the coordinator invokes -- so the shared
    single-agent identity/step machinery in this module needs no structural
    changes for multi-agent evidence. A step's ``fault`` is populated only
    when the episode dispatched exactly one Multi-Agent fault per worker
    (``message_loss`` or ``information_withholding``), which preserves a
    stable per-worker correlation between dispatch results and steps.
    """

    family, cluster_id = _resolve_cluster(scenario)
    per_worker_dispatches = (
        episode.fault_dispatches
        if len(episode.fault_dispatches) == len(episode.assignments)
        else ()
    )

    steps: list[Step] = []
    total_policy_violations = 0
    total_interventions = 0
    for index, assignment in enumerate(episode.assignments):
        response = assignment.response
        dispatch = per_worker_dispatches[index] if per_worker_dispatches else None
        fault = (
            FaultTrigger(fault_id=dispatch.fault_id, verified=dispatch.verified)
            if dispatch is not None
            else None
        )
        tool = ToolInvocation(
            name=f"worker:{assignment.role.worker_id}",
            call_payload=assignment.role.sub_task_prompt,
            response_payload=response.output_text if response is not None else None,
        )
        usage = _usage_metrics(
            assignment.role.sub_task_prompt,
            response.output_text if response is not None else "",
            latency_ms=0.0,
        )
        steps.append(
            Step(
                index=index,
                action="multi_agent_handoff",
                state_transition="assigned->verified" if response is not None else "assigned->lost",
                tool=tool,
                fault=fault,
                recovered=fault is not None and fault.verified and response is not None,
                usage=usage,
                prompt_text=assignment.role.sub_task_prompt,
                output_text=response.output_text if response is not None else None,
            )
        )
        if response is not None:
            total_policy_violations += response.policy_violations
            total_interventions += response.interventions

    outcome = Outcome(
        goal_achieved=episode.success,
        label="goal_achieved" if episode.success else "goal_failed",
    )

    return Trajectory(
        run_id=run_id,
        task_id=episode.task_id,
        family=family,
        cluster_id=cluster_id,
        suite_id=scenario.suite_ref.suite_id,
        suite_version=scenario.suite_ref.version,
        suite_partition=_DEFAULT_SUITE_PARTITION,
        repeat_id=f"seed-{seed}",
        scenario_name=scenario.name,
        scenario_version=scenario.version,
        agent_id=episode.coordinator_id,
        agent_version=episode.coordinator_id,
        steps=tuple(steps),
        outcome=outcome,
        intervention_count=total_interventions,
        policy_violation_count=total_policy_violations,
    )


def run_multi_agent_reliability_loop(
    scenario: Scenario,
    workers: Mapping[str, AgentUnderTest],
    *,
    iterations: int = 1,
    fault_id: str | None = None,
    seed: int | None = None,
    coordinator: Coordinator | None = None,
) -> MultiAgentRunOutcome:
    """Run one or more star-topology multi-agent episodes and derive their evidence.

    Additive, opt-in multi-agent counterpart to ``run_reliability_loop``:
    single-agent scenarios and callers are completely unaffected. Reuses
    ``_build_reliability_vector`` unchanged (it only reads generic
    trajectory fields) and a shared ``_build_multi_agent_trajectory`` helper
    that parallels ``_build_trajectory`` without duplicating its usage-heuristic
    logic (see ``_usage_metrics``).

    Args:
        scenario: Scenario supplying the shared objective, constraints, and
            expected outcome every worker is judged against.
        workers: Named workers; each must implement ``AgentUnderTest.run_task``.
        iterations: Number of episodes to run.
        fault_id: Optional Multi-Agent-level catalog fault forwarded to
            ``Coordinator.run_episode`` for every episode.
        seed: Overrides ``scenario.seed`` for the shared random source.
        coordinator: Overrides the default :class:`Coordinator` instance.

    Raises:
        arise_x.agents.multi_agent.MultiAgentValidationError: If ``workers`` is empty.
    """

    resolved_seed = seed if seed is not None else scenario.seed
    random_source = random.Random(resolved_seed)
    resolved_coordinator = coordinator if coordinator is not None else Coordinator()

    episodes: list[MultiAgentEpisode] = []
    trajectories: list[Trajectory] = []
    vectors: list[ReliabilityVector] = []
    macs_scores: list[MacsScore] = []

    for index in range(iterations):
        task_id = f"multi-agent-task-{index + 1}"
        episode = resolved_coordinator.run_episode(
            scenario,
            task_id,
            workers,
            run_id=_UNPERSISTED_RUN_ID,
            fault_id=fault_id,
            rng=random_source,
        )
        trajectory = _build_multi_agent_trajectory(
            episode, scenario=scenario, run_id=_UNPERSISTED_RUN_ID, seed=resolved_seed
        )
        chaos_triggered = any(dispatch.verified for dispatch in episode.fault_dispatches)
        vector = _build_reliability_vector(trajectory, chaos_triggered=chaos_triggered)

        episodes.append(episode)
        trajectories.append(trajectory)
        vectors.append(vector)
        macs_scores.append(episode.macs)

    return MultiAgentRunOutcome(
        episodes=episodes, trajectories=trajectories, vectors=vectors, macs_scores=macs_scores
    )
