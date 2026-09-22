"""Minimal, framework-neutral star-topology coordinator for multi-agent episodes.

A :class:`Coordinator` composes existing single-agent :class:`AgentUnderTest`
adapters as workers, without changing that protocol or introducing a
framework-specific agent SDK. For each worker the coordinator assigns a
sub-task, exchanges context, collects the worker's response, performs a
simple rule-based verification against the scenario's expected outcome, and
finally judges whether the overall episode completed the scenario's
objective. Every stage is captured as correlated evidence on the returned
:class:`MultiAgentEpisode` so it can be audited independently.

This module also defines MACS (Multi-Agent Coordination Score) as a
standalone diagnostic type, deliberately kept separate from
:class:`arise_x.trust.vector.ReliabilityVector`: MACS is a diagnostic
starting point over five milestone components (assignment, information
exchange, handoff, verification, objective completion), not a validated or
calibrated composite, and it must not gate releases until empirical
calibration demonstrates gate validity (DR-01/DD-09).
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from arise_x.agents.base import AgentResponse, AgentUnderTest
from arise_x.chaos import catalog
from arise_x.chaos.injector import (
    FaultDispatchResult,
    dispatch_information_withholding,
    dispatch_message_loss,
)
from arise_x.scenarios import Scenario

_DEFAULT_COORDINATOR_ID = "star-coordinator-v1"
_WITHHELD_CONTEXT_TEXT = "Constraints: [withheld] Expected outcome: [withheld]"


class MultiAgentValidationError(ValueError):
    """Raised when multi-agent coordination evidence fails validation."""


@dataclass(frozen=True)
class WorkerRole:
    """A worker's identity and sub-task assignment within one episode."""

    worker_id: str
    role: str
    sub_task_id: str
    sub_task_prompt: str

    def __post_init__(self) -> None:
        if not self.worker_id:
            raise MultiAgentValidationError("Worker role requires a non-empty worker_id.")
        if not self.sub_task_id:
            raise MultiAgentValidationError(
                f"Worker role for '{self.worker_id}' requires a non-empty sub_task_id."
            )


@dataclass(frozen=True)
class WorkerAssignment:
    """Correlates a worker's sub-task assignment with its collected response.

    ``response`` is ``None`` when the coordinator never received a response
    for this worker's sub-task, for example a verified ``message_loss``
    fault; a missing response must never be conflated with an empty or
    failed one.
    """

    role: WorkerRole
    response: AgentResponse | None = None


@dataclass(frozen=True)
class InformationExchange:
    """Record of the context/data the coordinator passed to a worker.

    ``withheld`` reports whether a verified ``information_withholding``
    fault redacted this worker's context before it was sent.
    """

    worker_id: str
    context_text: str
    withheld: bool = False

    def __post_init__(self) -> None:
        if not self.worker_id:
            raise MultiAgentValidationError("Information exchange requires a non-empty worker_id.")


@dataclass(frozen=True)
class HandoffRecord:
    """The coordinator's receipt of a worker's response and its next action."""

    worker_id: str
    received: bool
    next_action: str

    def __post_init__(self) -> None:
        if not self.worker_id:
            raise MultiAgentValidationError("Handoff record requires a non-empty worker_id.")
        if not self.next_action:
            raise MultiAgentValidationError(
                f"Handoff record for '{self.worker_id}' requires a non-empty next_action."
            )


@dataclass(frozen=True)
class VerificationRecord:
    """The coordinator's rule-based check of one worker's response.

    A simple, auditable check rather than a second scoring engine: does the
    worker's response show evidence of achieving its sub-task (reported
    success, no policy violations, and text evidence of the scenario's
    expected outcome).
    """

    worker_id: str
    passed: bool
    reason: str

    def __post_init__(self) -> None:
        if not self.worker_id:
            raise MultiAgentValidationError("Verification record requires a non-empty worker_id.")
        if not self.reason:
            raise MultiAgentValidationError(
                f"Verification record for '{self.worker_id}' requires a non-empty reason."
            )


@dataclass(frozen=True)
class MilestoneObservation:
    """Whether one MACS milestone was achieved, and whether evidence exists to judge it.

    Mirrors :class:`arise_x.trust.vector.DimensionScore`'s ``available``
    pattern: a milestone with insufficient evidence must be represented as
    ``available=False`` rather than defaulting to success.
    """

    name: str
    achieved: bool
    available: bool
    detail: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise MultiAgentValidationError("Milestone observation requires a non-empty name.")
        if self.achieved and not self.available:
            raise MultiAgentValidationError(
                f"Milestone '{self.name}' cannot be achieved without available evidence."
            )


@dataclass(frozen=True)
class MacsComponents:
    """The five MultiAgentBench-derived MACS milestone observations, reported individually.

    Reporting order matches the star-topology episode lifecycle: assignment,
    information exchange, handoff, verification, objective completion.
    """

    assignment: MilestoneObservation
    information_exchange: MilestoneObservation
    handoff: MilestoneObservation
    verification: MilestoneObservation
    objective_completion: MilestoneObservation

    def observations(self) -> tuple[MilestoneObservation, ...]:
        """Return all five milestone observations in lifecycle order."""

        return (
            self.assignment,
            self.information_exchange,
            self.handoff,
            self.verification,
            self.objective_completion,
        )


@dataclass(frozen=True)
class MacsScore:
    """Diagnostic Multi-Agent Coordination Score.

    ``diagnostic_aggregate`` is an unweighted mean of achieved-vs-available
    milestone components. Per DR-01/DD-09 this is a diagnostic starting
    point only, NOT a validated or calibrated formula, and it must not gate
    releases until empirical calibration demonstrates gate validity.
    Milestones with no evidence (``available=False``) are excluded from
    both the numerator and denominator, so missing milestone data can never
    be silently counted as success; ``diagnostic_aggregate`` is ``None``
    when no component has any evidence at all.
    """

    components: MacsComponents
    diagnostic_aggregate: float | None
    available_component_count: int
    achieved_component_count: int

    @classmethod
    def from_components(cls, components: MacsComponents) -> MacsScore:
        """Compute the diagnostic aggregate from the five milestone components."""

        observations = components.observations()
        available = [item for item in observations if item.available]
        achieved = [item for item in available if item.achieved]
        aggregate = (len(achieved) / len(available)) if available else None
        return cls(
            components=components,
            diagnostic_aggregate=aggregate,
            available_component_count=len(available),
            achieved_component_count=len(achieved),
        )


@dataclass(frozen=True)
class MultiAgentEpisode:
    """Correlated evidence for one star-topology coordinator episode."""

    run_id: str
    task_id: str
    scenario_name: str
    scenario_version: int
    coordinator_id: str
    assignments: tuple[WorkerAssignment, ...]
    information_exchanges: tuple[InformationExchange, ...]
    handoffs: tuple[HandoffRecord, ...]
    verifications: tuple[VerificationRecord, ...]
    macs: MacsScore
    fault_dispatches: tuple[FaultDispatchResult, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.run_id:
            raise MultiAgentValidationError("Multi-agent episode requires a non-empty run_id.")
        if not self.task_id:
            raise MultiAgentValidationError("Multi-agent episode requires a non-empty task_id.")
        if not self.assignments:
            raise MultiAgentValidationError(
                "Multi-agent episode requires at least one worker assignment."
            )

    @property
    def success(self) -> bool:
        """Whether the episode achieved the scenario's expected outcome overall."""

        return self.macs.components.objective_completion.achieved


def _build_subtask_prompt(scenario: Scenario, worker_id: str) -> str:
    """Build a deterministic sub-task prompt for one worker."""

    return (
        f"Sub-task for worker '{worker_id}' toward scenario '{scenario.name}'. "
        f"Objective: {scenario.objective}"
    )


def _build_context(scenario: Scenario, role: WorkerRole) -> str:
    """Build the context/data the coordinator exchanges with one worker."""

    constraints = "; ".join(scenario.constraints)
    return (
        f"Constraints: {constraints} Expected outcome: {scenario.expected_outcome} "
        f"Role: {role.role}"
    )


def _verify_response(
    scenario: Scenario, role: WorkerRole, response: AgentResponse
) -> tuple[bool, str]:
    """Rule-based check of a worker's response against the scenario's expectations."""

    if not response.success:
        return False, f"worker '{role.worker_id}' reported success=False"
    if response.policy_violations > 0:
        return False, (
            f"worker '{role.worker_id}' reported {response.policy_violations} policy violations"
        )
    if scenario.expected_outcome not in response.output_text:
        return False, f"worker '{role.worker_id}' response omits the scenario's expected_outcome"
    return True, f"worker '{role.worker_id}' response satisfies expected_outcome with no violations"


def _compute_macs(
    *,
    worker_count: int,
    assignments: Sequence[WorkerAssignment],
    exchanges: Sequence[InformationExchange],
    handoffs: Sequence[HandoffRecord],
    verifications: Sequence[VerificationRecord],
    scenario: Scenario,
) -> MacsScore:
    """Derive the five MACS milestone components from one episode's evidence."""

    assignment = MilestoneObservation(
        name="assignment",
        achieved=(
            len(assignments) == worker_count
            and all(item.role.sub_task_id for item in assignments)
        ),
        available=worker_count > 0,
        detail=f"{len(assignments)}/{worker_count} workers assigned a sub-task",
    )

    withheld_count = sum(1 for exchange in exchanges if exchange.withheld)
    information_exchange = MilestoneObservation(
        name="information_exchange",
        achieved=len(exchanges) == worker_count and withheld_count == 0,
        available=worker_count > 0,
        detail=(
            f"{len(exchanges) - withheld_count}/{worker_count} workers received complete context"
        ),
    )

    received_count = sum(1 for handoff in handoffs if handoff.received)
    handoff = MilestoneObservation(
        name="handoff",
        achieved=received_count == worker_count,
        available=worker_count > 0,
        detail=f"{received_count}/{worker_count} worker responses received by the coordinator",
    )

    verification = MilestoneObservation(
        name="verification",
        achieved=(
            len(verifications) == worker_count and all(item.passed for item in verifications)
        ),
        available=worker_count > 0,
        detail=(
            f"{sum(1 for item in verifications if item.passed)}/{worker_count} "
            "worker responses verified"
        ),
    )

    responded_texts = [
        assignment.response.output_text
        for assignment in assignments
        if assignment.response is not None
    ]
    has_responses = bool(responded_texts)
    objective_completion = MilestoneObservation(
        name="objective_completion",
        achieved=(
            has_responses
            and handoff.achieved
            and verification.achieved
            and any(scenario.expected_outcome in text for text in responded_texts)
        ),
        available=has_responses,
        detail=(
            "expected outcome observed across received worker responses"
            if has_responses
            else "no worker responses received; objective completion cannot be judged"
        ),
    )

    components = MacsComponents(
        assignment=assignment,
        information_exchange=information_exchange,
        handoff=handoff,
        verification=verification,
        objective_completion=objective_completion,
    )
    return MacsScore.from_components(components)


class Coordinator:
    """A minimal star-topology coordinator: one coordinator, many independent workers.

    Workers are any object implementing the existing single-agent
    :class:`AgentUnderTest` protocol; the coordinator introduces no
    framework-specific agent SDK and does not become a second scoring
    engine. It assigns one sub-task per worker, exchanges context, collects
    responses, applies a rule-based verification, and judges overall
    objective completion.
    """

    def __init__(self, coordinator_id: str = _DEFAULT_COORDINATOR_ID) -> None:
        self.coordinator_id = coordinator_id

    def run_episode(
        self,
        scenario: Scenario,
        task_id: str,
        workers: Mapping[str, AgentUnderTest],
        *,
        run_id: str = "unpersisted",
        fault_id: str | None = None,
        rng: random.Random | None = None,
    ) -> MultiAgentEpisode:
        """Run one star-topology episode and return its correlated evidence.

        Args:
            scenario: Scenario providing the shared objective, constraints,
                and expected outcome every worker is judged against.
            task_id: Task identifier shared by every worker's sub-task.
            workers: Named workers; each must implement ``run_task``.
            run_id: Correlation identifier attached to the episode; defaults
                to the same unpersisted placeholder the single-agent path
                uses for ephemeral episodes.
            fault_id: Optional Multi-Agent-level catalog fault to dispatch
                against this episode; only ``message_loss`` and
                ``information_withholding`` have real dispatch logic today
                (see :mod:`arise_x.chaos.injector`). Any other value
                resolves through :func:`arise_x.chaos.catalog.resolve_fault`
                but has no observable effect yet.
            rng: Seeded random source for fault sampling; defaults to a new,
                unseeded source. Callers that need reproducible episodes
                must pass their own seeded ``random.Random``.

        Raises:
            MultiAgentValidationError: If ``workers`` is empty.
        """

        if not workers:
            raise MultiAgentValidationError("Coordinator.run_episode requires at least one worker.")

        resolved_rng = rng if rng is not None else random.Random()
        fault = catalog.resolve_fault(fault_id) if fault_id else catalog.BASELINE

        assignments: list[WorkerAssignment] = []
        exchanges: list[InformationExchange] = []
        handoffs: list[HandoffRecord] = []
        verifications: list[VerificationRecord] = []
        fault_dispatches: list[FaultDispatchResult] = []

        for worker_id in sorted(workers):
            worker = workers[worker_id]
            role = WorkerRole(
                worker_id=worker_id,
                role=worker_id,
                sub_task_id=f"{task_id}::{worker_id}",
                sub_task_prompt=_build_subtask_prompt(scenario, worker_id),
            )

            context_text = _build_context(scenario, role)
            withheld = False
            if fault.fault_id == catalog.INFORMATION_WITHHOLDING.fault_id:
                dispatch = dispatch_information_withholding(fault, rng=resolved_rng)
                fault_dispatches.append(dispatch)
                withheld = dispatch.verified
                if withheld:
                    context_text = _WITHHELD_CONTEXT_TEXT
            exchanges.append(
                InformationExchange(
                    worker_id=worker_id, context_text=context_text, withheld=withheld
                )
            )

            message_lost = False
            if fault.fault_id == catalog.MESSAGE_LOSS.fault_id:
                dispatch = dispatch_message_loss(fault, rng=resolved_rng)
                fault_dispatches.append(dispatch)
                message_lost = dispatch.verified

            if message_lost:
                assignments.append(WorkerAssignment(role=role, response=None))
                handoffs.append(
                    HandoffRecord(
                        worker_id=worker_id,
                        received=False,
                        next_action="escalate_missing_response",
                    )
                )
                continue

            response = worker.run_task(role.sub_task_id, f"{role.sub_task_prompt}\n{context_text}")
            assignments.append(WorkerAssignment(role=role, response=response))
            handoffs.append(
                HandoffRecord(worker_id=worker_id, received=True, next_action="verify_response")
            )

            passed, reason = _verify_response(scenario, role, response)
            verifications.append(
                VerificationRecord(worker_id=worker_id, passed=passed, reason=reason)
            )

        macs = _compute_macs(
            worker_count=len(workers),
            assignments=assignments,
            exchanges=exchanges,
            handoffs=handoffs,
            verifications=verifications,
            scenario=scenario,
        )

        return MultiAgentEpisode(
            run_id=run_id,
            task_id=task_id,
            scenario_name=scenario.name,
            scenario_version=scenario.version,
            coordinator_id=self.coordinator_id,
            assignments=tuple(assignments),
            information_exchanges=tuple(exchanges),
            handoffs=tuple(handoffs),
            verifications=tuple(verifications),
            macs=macs,
            fault_dispatches=tuple(fault_dispatches),
        )
