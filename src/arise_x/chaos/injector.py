"""Chaos injector: legacy probability-boost profiles plus typed catalog dispatch."""

from __future__ import annotations

import random
from dataclasses import dataclass

from arise_x.chaos.catalog import FaultDefinition


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
    """Receipt for one fault-dispatch attempt against a catalog fault definition.

    ``triggered`` reports whether the seeded chaos sample fired (AgentChaos's
    "fault configured/sampled" signal). ``verified`` additionally confirms
    the fault caused an observable effect: it only requires attention when
    the same response would otherwise have succeeded (``control_success``),
    so a fault that fires but coincides with a response that would have
    failed anyway is never miscounted as a verified, scored trigger. This is
    a dispatch-time receipt; :class:`arise_x.telemetry.trajectory.FaultTrigger`
    remains the step-level fault-evidence record it feeds.
    """

    fault_id: str
    triggered: bool
    verified: bool
    latency_multiplier: float


def dispatch_fault(
    fault: FaultDefinition,
    *,
    base_failure_rate: float,
    control_success: bool,
    rng: random.Random,
) -> FaultDispatchResult:
    """Sample whether ``fault`` fires and verify its effect actually manifested.

    Args:
        fault: Catalog fault definition to dispatch; must have
            ``runtime_dispatch=True``.
        base_failure_rate: Baseline probability of failure before disruption.
        control_success: Whether the same response would have succeeded with
            no fault active. Used to confirm the fault caused the observed
            failure rather than just crediting its configured probability.
        rng: Seeded random source; callers supply the same seed for
            reproducible sampling.

    Raises:
        NotImplementedError: If ``fault`` is cataloged for future dispatch
            (``runtime_dispatch=False``) and has no runtime sampling logic yet.
    """

    if not fault.runtime_dispatch:
        raise NotImplementedError(
            f"Fault '{fault.fault_id}' is cataloged for future dispatch and has no runtime "
            "sampling logic yet; see arise_x.chaos.catalog module docstring."
        )

    profile = DisruptionProfile(
        name=fault.fault_id,
        failure_boost=fault.failure_boost,
        latency_multiplier=fault.latency_multiplier,
    )
    triggered = sample_failure(base_failure_rate=base_failure_rate, profile=profile, rng=rng)
    verified = triggered and control_success
    return FaultDispatchResult(
        fault_id=fault.fault_id,
        triggered=triggered,
        verified=verified,
        latency_multiplier=profile.latency_multiplier,
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
        latency_multiplier=profile.latency_multiplier,
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
