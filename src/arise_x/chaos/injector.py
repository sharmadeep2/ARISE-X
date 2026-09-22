"""Deterministic preparation and verification for bounded local faults."""

from __future__ import annotations

import random
from dataclasses import dataclass

from arise_x.agents.base import FaultObservation, LocalExecutionContext
from arise_x.chaos.catalog import (
    BASELINE as CATALOG_BASELINE,
)
from arise_x.chaos.catalog import (
    FaultDefinition,
    InjectionPoint,
    RuntimeCapability,
)


class FaultDispatchError(RuntimeError):
    """Raised when a configured fault cannot execute through the local runtime."""


@dataclass(frozen=True)
class DisruptionProfile:
    """Defines disruption intensity used to perturb outcomes."""

    name: str
    failure_boost: float
    latency_multiplier: float


BASELINE = DisruptionProfile(name="baseline", failure_boost=0.0, latency_multiplier=1.0)
LATENCY_SPIKE = DisruptionProfile(name="latency_spike", failure_boost=0.10, latency_multiplier=2.0)
TOOL_DEGRADATION = DisruptionProfile(
    name="tool_degradation", failure_boost=0.20, latency_multiplier=1.4
)


def sample_failure(
    base_failure_rate: float, profile: DisruptionProfile, rng: random.Random
) -> bool:
    """Return whether a run fails under a disruption profile.

    Args:
        base_failure_rate: Baseline probability of failure before disruption.
        profile: Disruption profile whose failure_boost adjusts the rate.
        rng: Seeded random source; callers supply the same seed for
            reproducible sampling.
    """

    adjusted = min(1.0, max(0.0, base_failure_rate + profile.failure_boost))
    return rng.random() < adjusted


@dataclass(frozen=True)
class FaultDispatchResult:
    """Immutable receipt for one bounded fault attempt and its observed effect."""

    fault_id: str
    triggered: bool
    verified: bool
    latency_multiplier: float
    attempted: bool = True
    observed: bool | None = None
    recovered: bool | None = None
    aborted: bool = False
    injection_point: InjectionPoint = InjectionPoint.TASK_EXECUTION
    affected_evidence_references: tuple[str, ...] = ()
    policy_reason: str = ""
    runtime_capability: RuntimeCapability = RuntimeCapability.NONE

    def __post_init__(self) -> None:
        references = tuple(self.affected_evidence_references)
        object.__setattr__(self, "affected_evidence_references", references)
        observed = self.verified if self.observed is None else self.observed
        object.__setattr__(self, "observed", observed)
        if self.verified and not self.observed:
            raise FaultDispatchError("A verified fault receipt requires an observed effect.")
        if self.observed and not self.triggered:
            raise FaultDispatchError("An observed fault effect requires a triggered attempt.")
        if self.recovered is not None and not self.verified:
            raise FaultDispatchError("Recovery is available only for verified fault effects.")
        if self.aborted and (self.triggered or self.observed or self.verified):
            raise FaultDispatchError("An aborted fault cannot also be triggered or observed.")


@dataclass
class FaultPolicyState:
    """Mutable per-run policy state kept outside immutable receipts."""

    verified_trigger_count: int = 0


@dataclass(frozen=True)
class FaultDispatchAttempt:
    """Prepared injection decision made before agent execution."""

    fault: FaultDefinition
    receipt: FaultDispatchResult
    context: LocalExecutionContext | None


def dispatch_fault(
    fault: FaultDefinition,
    *,
    base_failure_rate: float,
    control_success: bool,
    rng: random.Random,
) -> FaultDispatchResult:
    """Compatibility wrapper that prepares a fault without claiming observation.

    Args:
        fault: Catalog fault definition to dispatch; must have
            ``runtime_dispatch=True``.
        base_failure_rate: Baseline probability of failure before disruption.
        control_success: Retained for call compatibility; never used as
            trigger verification because verification requires an observed
            effect at the injection point.
        rng: Seeded random source; callers supply the same seed for
            reproducible sampling.

    Raises:
        NotImplementedError: If ``fault`` is cataloged for future dispatch
            (``runtime_dispatch=False``) and has no runtime sampling logic yet.
    """

    del control_success
    return prepare_fault(
        fault,
        base_failure_rate=base_failure_rate,
        rng=rng,
        policy_state=FaultPolicyState(),
    ).receipt


def prepare_fault(
    fault: FaultDefinition,
    *,
    base_failure_rate: float,
    rng: random.Random,
    policy_state: FaultPolicyState,
) -> FaultDispatchAttempt:
    """Evaluate policy and sampling before the agent reaches the injection point."""

    if not fault.runtime_dispatch:
        raise NotImplementedError(
            f"Fault '{fault.fault_id}' is cataloged but has no single-agent local runtime "
            "implementation."
        )
    if fault.fault_id == CATALOG_BASELINE.fault_id:
        return FaultDispatchAttempt(
            fault=fault,
            receipt=FaultDispatchResult(
                fault_id=fault.fault_id,
                attempted=False,
                triggered=False,
                observed=False,
                verified=False,
                recovered=None,
                aborted=False,
                injection_point=fault.injection_point,
                latency_multiplier=1.0,
                policy_reason="baseline control: no fault attempted",
                runtime_capability=fault.runtime_capability,
            ),
            context=None,
        )
    if fault.abort_policy.should_abort(
        verified_trigger_count=policy_state.verified_trigger_count
    ):
        return FaultDispatchAttempt(
            fault=fault,
            receipt=FaultDispatchResult(
                fault_id=fault.fault_id,
                attempted=True,
                triggered=False,
                observed=False,
                verified=False,
                recovered=None,
                aborted=True,
                injection_point=fault.injection_point,
                latency_multiplier=1.0,
                policy_reason=(
                    f"abort policy {fault.abort_policy.condition.value} reached "
                    f"threshold {fault.abort_policy.threshold}"
                ),
                runtime_capability=fault.runtime_capability,
            ),
            context=None,
        )

    profile = DisruptionProfile(
        name=fault.fault_id,
        failure_boost=fault.failure_boost,
        latency_multiplier=fault.latency_multiplier,
    )
    triggered = sample_failure(base_failure_rate, profile, rng)
    receipt = FaultDispatchResult(
        fault_id=fault.fault_id,
        attempted=True,
        triggered=triggered,
        observed=False,
        verified=False,
        recovered=None,
        aborted=False,
        injection_point=fault.injection_point,
        latency_multiplier=fault.latency_multiplier if triggered else 1.0,
        policy_reason=(
            "seeded trigger selected for bounded local injection"
            if triggered
            else "seeded trigger did not select this fault"
        ),
        runtime_capability=fault.runtime_capability,
    )
    context = (
        LocalExecutionContext(
            fault_id=fault.fault_id,
            injection_point=fault.injection_point,
            expected_signal=fault.expected_observation.signal,
            intensity=fault.intensity,
            should_recover=fault.intensity < 1.0,
        )
        if triggered
        else None
    )
    return FaultDispatchAttempt(fault=fault, receipt=receipt, context=context)


def finalize_fault(
    attempt: FaultDispatchAttempt,
    observation: FaultObservation | None,
    *,
    policy_state: FaultPolicyState,
) -> FaultDispatchResult:
    """Verify a prepared attempt from the effect observed at its injection point."""

    receipt = attempt.receipt
    if not receipt.triggered:
        return receipt
    observed = (
        observation is not None
        and observation.fault_id == attempt.fault.fault_id
        and observation.injection_point is attempt.fault.injection_point
        and observation.signal is attempt.fault.expected_observation.signal
        and bool(observation.evidence_references)
    )
    if observed and observation is not None:
        policy_state.verified_trigger_count += 1
        return FaultDispatchResult(
            fault_id=receipt.fault_id,
            attempted=True,
            triggered=True,
            observed=True,
            verified=True,
            recovered=observation.recovered,
            aborted=False,
            injection_point=receipt.injection_point,
            affected_evidence_references=observation.evidence_references,
            policy_reason=observation.policy_reason,
            latency_multiplier=receipt.latency_multiplier,
            runtime_capability=receipt.runtime_capability,
        )
    return FaultDispatchResult(
        fault_id=receipt.fault_id,
        attempted=True,
        triggered=True,
        observed=False,
        verified=False,
        recovered=None,
        aborted=False,
        injection_point=receipt.injection_point,
        policy_reason="trigger selected but the injection point did not report the expected effect",
        latency_multiplier=receipt.latency_multiplier,
        runtime_capability=receipt.runtime_capability,
    )


def _dispatch_multi_agent_fault(
    fault: FaultDefinition, *, rng: random.Random
) -> FaultDispatchResult:
    """Sample a Multi-Agent-level fault against the star-topology coordinator.

    Shared by :func:`dispatch_message_loss` and
    :func:`dispatch_information_withholding`. Unlike :func:`dispatch_fault`,
    this does not gate on ``fault.runtime_dispatch``: that flag tracks
    whether the single-agent task-execution runner's ``dispatch_fault`` path
    has sampling logic for a fault, which is a separate question from
    whether the star-topology coordinator does. The coordinator always would
    have delivered the message/context absent the fault, so any sampled
    trigger is inherently a verified, real effect -- there is no
    control-vs-experiment ambiguity to resolve here.
    """

    profile = DisruptionProfile(
        name=fault.fault_id,
        failure_boost=fault.failure_boost,
        latency_multiplier=fault.latency_multiplier,
    )
    triggered = sample_failure(base_failure_rate=0.0, profile=profile, rng=rng)
    return FaultDispatchResult(
        fault_id=fault.fault_id,
        triggered=triggered,
        verified=triggered,
        observed=triggered,
        recovered=False if triggered else None,
        injection_point=fault.injection_point,
        affected_evidence_references=(
            f"coordination:{fault.fault_id}:observed",
        )
        if triggered
        else (),
        policy_reason=(
            "coordinator observed the selected local coordination effect"
            if triggered
            else "seeded trigger did not select this coordination fault"
        ),
        latency_multiplier=profile.latency_multiplier,
        runtime_capability=fault.runtime_capability,
    )


def dispatch_message_loss(fault: FaultDefinition, *, rng: random.Random) -> FaultDispatchResult:
    """Sample whether a coordinator-to-worker message is dropped (``message_loss``).

    Real runtime dispatch for the star-topology coordinator
    (:mod:`arise_x.agents.multi_agent`); see :func:`_dispatch_multi_agent_fault`.

    Args:
        fault: The ``message_loss`` catalog fault definition.
        rng: Seeded random source; callers supply the same seed for
            reproducible sampling.
    """

    return _dispatch_multi_agent_fault(fault, rng=rng)


def dispatch_information_withholding(
    fault: FaultDefinition, *, rng: random.Random
) -> FaultDispatchResult:
    """Sample whether the coordinator withholds context from a worker (``information_withholding``).

    Real runtime dispatch for the star-topology coordinator
    (:mod:`arise_x.agents.multi_agent`); see :func:`_dispatch_multi_agent_fault`.

    Args:
        fault: The ``information_withholding`` catalog fault definition.
        rng: Seeded random source; callers supply the same seed for
            reproducible sampling.
    """

    return _dispatch_multi_agent_fault(fault, rng=rng)
