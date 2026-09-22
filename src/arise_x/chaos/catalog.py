"""Typed fault taxonomy and bounded policy contracts for chaos experiments."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FaultCatalogError(ValueError):
    """Raised when a fault definition or catalog lookup is invalid."""


class FaultLevel(StrEnum):
    """Primary fault-taxonomy level a fault definition belongs to.

    Level 6 (Model) remains fully deferred to a later phase and
    intentionally has no member here.
    """

    INFRASTRUCTURE = "infrastructure"
    TOOL = "tool"
    DATA = "data"
    AGENT = "agent"
    MULTI_AGENT = "multi_agent"


class FaultFamily(StrEnum):
    """Cross-cutting fault family applied across levels rather than as its own level (DD-07)."""

    COST = "cost"
    SECURITY_ADVERSARIAL = "security_adversarial"
    HUMAN_IN_THE_LOOP = "human_in_the_loop"


class InjectionPoint(StrEnum):
    """Named stage in agent execution where a fault is injected.

    ``TASK_EXECUTION`` covers the single-agent runner, which executes
    exactly one step per task. ``COORDINATION`` covers the star-topology
    coordinator's per-worker assignment, information-exchange, and handoff
    stages (:mod:`arise_x.agents.multi_agent`).
    """

    TASK_EXECUTION = "task_execution"
    BEFORE_AGENT_EXECUTION = "before_agent_execution"
    TOOL_CALL = "tool_call"
    DATA_ACCESS = "data_access"
    OUTPUT_VERIFICATION = "output_verification"
    COORDINATION = "coordination"


class InjectionStrategy(StrEnum):
    """How repeatedly a fault applies once selected, per AgentChaos precedent."""

    SINGLE = "single"
    PERSISTENT = "persistent"
    INTERMITTENT = "intermittent"
    BURST = "burst"


class AbortCondition(StrEnum):
    """Executable condition that bounds repeated fault activation."""

    NEVER = "never"
    MAX_VERIFIED_TRIGGERS = "max_verified_triggers"


class AbortAction(StrEnum):
    """Action taken when an abort condition is met."""

    STOP_INJECTION = "stop_injection"


class BlastRadiusScope(StrEnum):
    """Maximum local scope a fault is allowed to affect."""

    NONE = "none"
    SINGLE_TASK = "single_task"
    SINGLE_WORKER = "single_worker"


class RuntimeCapability(StrEnum):
    """Runtime contract required to execute a catalog fault."""

    NONE = "none"
    LOCAL_CONTEXT_V1 = "local_context_v1"
    MULTI_AGENT_COORDINATION_V1 = "multi_agent_coordination_v1"


class ObservationSignal(StrEnum):
    """Observable local effects used to verify representative MVP faults."""

    NONE = "none"
    LOCAL_DEPENDENCY_DELAY = "local_dependency_delay"
    LOCAL_TOOL_DEGRADATION = "local_tool_degradation"
    LOCAL_STALE_DATA = "local_stale_data"
    LOCAL_VERIFICATION_SKIPPED = "local_verification_skipped"


@dataclass(frozen=True)
class FaultWindow:
    """Bounded activation duration expressed in local execution steps."""

    duration_steps: int = 1
    max_activations: int = 1

    def __post_init__(self) -> None:
        if self.duration_steps <= 0 or self.max_activations <= 0:
            raise FaultCatalogError("Fault windows require positive step and activation bounds.")


@dataclass(frozen=True)
class AbortPolicy:
    """Executable abort policy evaluated before a fault reaches its injection point."""

    condition: AbortCondition = AbortCondition.MAX_VERIFIED_TRIGGERS
    threshold: int = 3
    action: AbortAction = AbortAction.STOP_INJECTION

    def __post_init__(self) -> None:
        if self.condition is AbortCondition.NEVER:
            if self.threshold != 0:
                raise FaultCatalogError("The never abort condition requires threshold=0.")
        elif self.threshold <= 0:
            raise FaultCatalogError("Executable abort policies require a positive threshold.")

    def should_abort(self, *, verified_trigger_count: int) -> bool:
        """Return whether injection must stop for the supplied policy state."""

        if self.condition is AbortCondition.NEVER:
            return False
        return verified_trigger_count >= self.threshold


@dataclass(frozen=True)
class BlastRadiusPolicy:
    """Bound the number and scope of local targets affected by one activation."""

    scope: BlastRadiusScope = BlastRadiusScope.SINGLE_TASK
    max_targets: int = 1

    def __post_init__(self) -> None:
        if self.scope is BlastRadiusScope.NONE:
            if self.max_targets != 0:
                raise FaultCatalogError("A no-effect blast radius requires max_targets=0.")
        elif self.max_targets <= 0:
            raise FaultCatalogError("A bounded blast radius requires a positive max_targets.")

    @property
    def bounded(self) -> bool:
        """Return whether this policy imposes a finite positive target bound."""

        return self.scope is not BlastRadiusScope.NONE and self.max_targets > 0


@dataclass(frozen=True)
class ExpectedObservation:
    """Signal and verification rule required to establish a real fault effect."""

    signal: ObservationSignal = ObservationSignal.NONE
    verification: str = "runtime-specific evidence must match the configured injection point"

    def __post_init__(self) -> None:
        if not self.verification.strip():
            raise FaultCatalogError("Expected observations require a verification rule.")


@dataclass(frozen=True)
class FaultDefinition:
    """One catalog entry describing a typed, injectable fault.

    Args:
        fault_id: Unique identifier used to reference this fault from
            scenarios and dispatch.
        level: Primary taxonomy level (Infrastructure, Tool, Data, Agent, or
            Multi-Agent).
        description: Human-readable description of the fault's effect.
        injection_point: Execution stage this fault applies to.
        strategy: How repeatedly the fault applies once selected.
        abort_condition: Human-readable compatibility description of the
            executable ``abort_policy``.
        verification: What confirms this fault actually manifested, rather
            than merely being configured (AgentChaos trigger-verification
            methodology).
        family: Optional cross-cutting family (Cost, Security/Adversarial,
            Human-in-the-loop) this fault also belongs to.
        failure_boost: Additional failure probability this fault adds to the
            base failure rate. Only meaningful when ``runtime_dispatch`` is
            True.
        latency_multiplier: Latency scaling applied when this fault fires.
        runtime_dispatch: Whether :func:`arise_x.chaos.injector.dispatch_fault`
            has real sampling logic for this fault today. Faults cataloged
            for future dispatch (see the module docstring) are valid,
            correctly classified entries but are not yet wired into task
            execution.

    Raises:
        FaultCatalogError: If any field fails validation.
    """

    fault_id: str
    level: FaultLevel
    description: str
    injection_point: InjectionPoint
    strategy: InjectionStrategy
    abort_condition: str
    verification: str
    family: FaultFamily | None = None
    failure_boost: float = 0.0
    latency_multiplier: float = 1.0
    runtime_dispatch: bool = False
    intensity: float = 1.0
    window: FaultWindow = FaultWindow()
    abort_policy: AbortPolicy = AbortPolicy()
    blast_radius: BlastRadiusPolicy = BlastRadiusPolicy()
    expected_observation: ExpectedObservation = ExpectedObservation()
    external_side_effect: bool = False
    runtime_capability: RuntimeCapability = RuntimeCapability.NONE

    def __post_init__(self) -> None:
        if not self.fault_id:
            raise FaultCatalogError("Fault definition requires a non-empty fault_id.")
        if not self.description:
            raise FaultCatalogError(f"Fault '{self.fault_id}' requires a non-empty description.")
        if not self.abort_condition:
            raise FaultCatalogError(
                f"Fault '{self.fault_id}' requires a non-empty abort_condition."
            )
        if not self.verification:
            raise FaultCatalogError(
                f"Fault '{self.fault_id}' requires non-empty verification metadata."
            )
        if not 0.0 <= self.failure_boost <= 1.0:
            raise FaultCatalogError(
                f"Fault '{self.fault_id}' failure_boost must be within [0.0, 1.0]."
            )
        if self.latency_multiplier <= 0.0:
            raise FaultCatalogError(
                f"Fault '{self.fault_id}' latency_multiplier must be positive."
            )
        if not 0.0 < self.intensity <= 1.0:
            raise FaultCatalogError(
                f"Fault '{self.fault_id}' intensity must be within (0.0, 1.0]."
            )
        if self.runtime_dispatch and self.runtime_capability is RuntimeCapability.NONE:
            raise FaultCatalogError(
                f"Fault '{self.fault_id}' runtime dispatch requires a runtime capability."
            )
        if self.external_side_effect and (
            not self.blast_radius.bounded
            or self.abort_policy.condition is AbortCondition.NEVER
        ):
            raise FaultCatalogError(
                f"Fault '{self.fault_id}' has external side effects and requires a bounded "
                "blast radius plus an executable abort condition."
            )


# Dispatched today: mirror the pre-existing DisruptionProfile constants in
# chaos/injector.py, mapped into the typed Level 1/2 taxonomy.

BASELINE = FaultDefinition(
    fault_id="baseline",
    level=FaultLevel.INFRASTRUCTURE,
    description="No-fault control execution used as the baseline for control-vs-experiment comparison.",  # noqa: E501
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.SINGLE,
    abort_condition="not applicable: baseline injects no fault",
    verification="not applicable: baseline is the no-fault control",
    runtime_dispatch=True,
    intensity=1.0,
    window=FaultWindow(duration_steps=1, max_activations=1),
    abort_policy=AbortPolicy(condition=AbortCondition.NEVER, threshold=0),
    blast_radius=BlastRadiusPolicy(scope=BlastRadiusScope.NONE, max_targets=0),
    expected_observation=ExpectedObservation(
        signal=ObservationSignal.NONE,
        verification="baseline performs no injection and requires no trigger observation",
    ),
    runtime_capability=RuntimeCapability.LOCAL_CONTEXT_V1,
)

LATENCY_SPIKE = FaultDefinition(
    fault_id="latency_spike",
    level=FaultLevel.INFRASTRUCTURE,
    description="Elevated end-to-end latency and failure probability simulating a slow upstream dependency.",  # noqa: E501
    injection_point=InjectionPoint.BEFORE_AGENT_EXECUTION,
    strategy=InjectionStrategy.PERSISTENT,
    abort_condition="abort after 3 consecutive verified triggers in one run",
    verification="chaos sampling fired and the task would otherwise have succeeded",
    failure_boost=0.10,
    latency_multiplier=2.0,
    runtime_dispatch=True,
    intensity=0.5,
    expected_observation=ExpectedObservation(
        signal=ObservationSignal.LOCAL_DEPENDENCY_DELAY,
        verification="the local dependency delay is observed before agent execution",
    ),
    runtime_capability=RuntimeCapability.LOCAL_CONTEXT_V1,
)

TOOL_DEGRADATION = FaultDefinition(
    fault_id="tool_degradation",
    level=FaultLevel.TOOL,
    description="Simulated tool-call quality degradation increasing failure probability and latency.",  # noqa: E501
    injection_point=InjectionPoint.TOOL_CALL,
    strategy=InjectionStrategy.PERSISTENT,
    abort_condition="abort after 3 consecutive verified triggers in one run",
    verification="chaos sampling fired and the task would otherwise have succeeded",
    failure_boost=0.20,
    latency_multiplier=1.4,
    runtime_dispatch=True,
    intensity=0.5,
    expected_observation=ExpectedObservation(
        signal=ObservationSignal.LOCAL_TOOL_DEGRADATION,
        verification="the deterministic local tool returns a degraded first response",
    ),
    runtime_capability=RuntimeCapability.LOCAL_CONTEXT_V1,
)

# Cataloged for future dispatch: real, valid taxonomy entries with no
# runtime sampling logic yet (see module docstring).

_FUTURE_VERIFICATION_PREFIX = (
    "requires evidence beyond the single-step task-execution runner; deferred until"
)

TIMEOUT = FaultDefinition(
    fault_id="timeout",
    level=FaultLevel.INFRASTRUCTURE,
    description="Upstream dependency exceeds its response deadline before returning.",
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.INTERMITTENT,
    abort_condition="abort after 3 consecutive verified timeouts in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} per-call deadlines are modeled",
)

PACKET_LOSS = FaultDefinition(
    fault_id="packet_loss",
    level=FaultLevel.INFRASTRUCTURE,
    description="Network packets between the agent and a dependency are silently dropped.",
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.INTERMITTENT,
    abort_condition="abort after 3 consecutive verified packet-loss events in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} transport-level retry telemetry is modeled",
)

SERVICE_UNAVAILABLE = FaultDefinition(
    fault_id="service_unavailable",
    level=FaultLevel.INFRASTRUCTURE,
    description="A dependency returns a hard unavailable/5xx response for the fault window.",
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.BURST,
    abort_condition="abort after 3 consecutive verified unavailable responses in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} an explicit dependency-call injection point is modeled",  # noqa: E501
)

RATE_LIMITING = FaultDefinition(
    fault_id="rate_limiting",
    level=FaultLevel.INFRASTRUCTURE,
    description="A dependency throttles requests, rejecting calls above a sampled rate.",
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.INTERMITTENT,
    abort_condition="abort after 3 consecutive verified throttled requests in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} per-call request-rate tracking is modeled",
)

RESOURCE_EXHAUSTION = FaultDefinition(
    fault_id="resource_exhaustion",
    level=FaultLevel.INFRASTRUCTURE,
    description=(
        "CPU, memory, or disk pressure on the execution host degrades or fails the task "
        "(research-identified Level 1 gap)."
    ),
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.PERSISTENT,
    abort_condition="abort after 3 consecutive verified resource-exhaustion events in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} host-level resource telemetry is modeled",
)

CLOCK_SKEW = FaultDefinition(
    fault_id="clock_skew",
    level=FaultLevel.INFRASTRUCTURE,
    description=(
        "Execution-host clock drifts from the reference time, corrupting "
        "timestamp-dependent logic (research-identified Level 1 gap)."
    ),
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.SINGLE,
    abort_condition="abort after 3 consecutive verified clock-skew events in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} an injectable clock source is modeled",
)

COST_SPIKE = FaultDefinition(
    fault_id="cost_spike",
    level=FaultLevel.INFRASTRUCTURE,
    family=FaultFamily.COST,
    description=(
        "A dependency's billed usage spikes well above its expected rate for the task "
        "(research-identified missing cost/budget fault category)."
    ),
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.BURST,
    abort_condition="abort when cumulative verified cost exceeds the scenario cost budget",
    verification=(
        f"{_FUTURE_VERIFICATION_PREFIX} per-call cost telemetry replaces the heuristic "
        "token-length cost proxy the runner uses today"
    ),
)

WRONG_SCHEMA = FaultDefinition(
    fault_id="wrong_schema",
    level=FaultLevel.TOOL,
    description="A tool call returns a response that does not match its declared schema.",
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.INTERMITTENT,
    abort_condition="abort after 3 consecutive verified schema mismatches in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} tool-call/response evidence is modeled",
)

PARTIAL_RESPONSE = FaultDefinition(
    fault_id="partial_response",
    level=FaultLevel.TOOL,
    description="A tool call returns a truncated or incomplete response.",
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.INTERMITTENT,
    abort_condition="abort after 3 consecutive verified partial responses in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} tool-call/response evidence is modeled",
)

INCORRECT_RESPONSE = FaultDefinition(
    fault_id="incorrect_response",
    level=FaultLevel.TOOL,
    description="A tool call returns a well-formed but factually incorrect response.",
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.INTERMITTENT,
    abort_condition="abort after 3 consecutive verified incorrect responses in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} an oracle/expected-output comparison is modeled",
)

TOOL_UNAVAILABLE = FaultDefinition(
    fault_id="tool_unavailable",
    level=FaultLevel.TOOL,
    description="A required tool is unreachable for the duration of the fault window.",
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.BURST,
    abort_condition="abort after 3 consecutive verified tool-unavailable events in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} an explicit tool-call injection point is modeled",
)

TOOL_VERSION_CHANGE = FaultDefinition(
    fault_id="tool_version_change",
    level=FaultLevel.TOOL,
    description=(
        "A tool's interface or behavior changes version mid-run, simulating an "
        "unannounced upstream deployment."
    ),
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.SINGLE,
    abort_condition="abort after 1 verified tool-version-change event in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} tool-call version metadata is modeled",
)

STALE_DATA = FaultDefinition(
    fault_id="stale_data",
    level=FaultLevel.DATA,
    description="The agent reads data that is out of date relative to the current task state.",
    injection_point=InjectionPoint.DATA_ACCESS,
    strategy=InjectionStrategy.PERSISTENT,
    abort_condition="abort after 3 consecutive verified stale-data reads in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} data-freshness metadata is modeled",
    failure_boost=0.25,
    runtime_dispatch=True,
    intensity=0.5,
    expected_observation=ExpectedObservation(
        signal=ObservationSignal.LOCAL_STALE_DATA,
        verification="the local data source returns a stale version before refresh",
    ),
    runtime_capability=RuntimeCapability.LOCAL_CONTEXT_V1,
)

MISSING_DATA = FaultDefinition(
    fault_id="missing_data",
    level=FaultLevel.DATA,
    description="Expected data is absent from a source the agent depends on.",
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.INTERMITTENT,
    abort_condition="abort after 3 consecutive verified missing-data reads in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} data-source instrumentation is modeled",
)

CONTRADICTORY_DATA = FaultDefinition(
    fault_id="contradictory_data",
    level=FaultLevel.DATA,
    description="Two data sources the agent consults disagree on the same fact.",
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.INTERMITTENT,
    abort_condition="abort after 3 consecutive verified contradictory-data reads in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} multi-source cross-checking is modeled",
)

CORRUPTED_DATA = FaultDefinition(
    fault_id="corrupted_data",
    level=FaultLevel.DATA,
    description="Data is malformed or truncated in a way that breaks downstream parsing.",
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.INTERMITTENT,
    abort_condition="abort after 3 consecutive verified corrupted-data reads in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} parse-failure telemetry is modeled",
)

POISONED_DATA = FaultDefinition(
    fault_id="poisoned_data",
    level=FaultLevel.DATA,
    family=FaultFamily.SECURITY_ADVERSARIAL,
    description=(
        "Data is deliberately manipulated to bias or mislead the agent's decisions "
        "(adversarial data poisoning)."
    ),
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.SINGLE,
    abort_condition="abort after 1 verified poisoned-data read in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} provenance/integrity checking is modeled",
)

PROMPT_INJECTION = FaultDefinition(
    fault_id="prompt_injection",
    level=FaultLevel.DATA,
    family=FaultFamily.SECURITY_ADVERSARIAL,
    description=(
        "Adversarial instructions embedded in retrieved or user-supplied content attempt "
        "to hijack agent behavior (research-identified missing security/adversarial "
        "fault category)."
    ),
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.SINGLE,
    abort_condition="abort after 1 verified prompt-injection event in one run",
    verification=(
        f"{_FUTURE_VERIFICATION_PREFIX} content-provenance and instruction-boundary "
        "checking is modeled"
    ),
)

PLANNING_FAILURE = FaultDefinition(
    fault_id="planning_failure",
    level=FaultLevel.AGENT,
    description="The agent produces an internally inconsistent or infeasible plan for the task.",
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.INTERMITTENT,
    abort_condition="abort after 3 consecutive verified planning failures in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} multi-step plan evidence is modeled",
)

LOOP = FaultDefinition(
    fault_id="loop",
    level=FaultLevel.AGENT,
    description="The agent repeats the same action or state without making progress.",
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.PERSISTENT,
    abort_condition="abort after 3 consecutive verified loop detections in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} multi-step state-transition history is modeled",
)

GOAL_DRIFT = FaultDefinition(
    fault_id="goal_drift",
    level=FaultLevel.AGENT,
    description=(
        "The agent's pursued objective diverges from the scenario's declared "
        "objective over the episode."
    ),
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.PERSISTENT,
    abort_condition="abort after 1 verified goal-drift event in one run",
    verification=(
        f"{_FUTURE_VERIFICATION_PREFIX} a multi-step trajectory comparing pursued vs. "
        "declared objective over time is modeled"
    ),
)

CONTEXT_OVERFLOW = FaultDefinition(
    fault_id="context_overflow",
    level=FaultLevel.AGENT,
    description="The agent's context window is exceeded, causing silent truncation of earlier evidence.",  # noqa: E501
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.SINGLE,
    abort_condition="abort after 1 verified context-overflow event in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} context-window usage telemetry is modeled",
)

MEMORY_CORRUPTION = FaultDefinition(
    fault_id="memory_corruption",
    level=FaultLevel.AGENT,
    description="The agent's persisted memory/state is corrupted or overwritten with incorrect values.",  # noqa: E501
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.SINGLE,
    abort_condition="abort after 1 verified memory-corruption event in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} persisted-memory read/write evidence is modeled",
)

WRONG_TOOL_SELECTION = FaultDefinition(
    fault_id="wrong_tool_selection",
    level=FaultLevel.AGENT,
    description="The agent selects a tool that is not appropriate for the current step.",
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.INTERMITTENT,
    abort_condition="abort after 3 consecutive verified wrong-tool selections in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} tool-selection evidence is modeled",
)

VERIFICATION_FAILURE = FaultDefinition(
    fault_id="verification_failure",
    level=FaultLevel.AGENT,
    description=(
        "The agent fails to check its own output against the task's success criteria "
        "before finishing (research-identified Level 4 gap; MAST found task-verification "
        "failures account for roughly 21% of observed multi-agent failures)."
    ),
    injection_point=InjectionPoint.OUTPUT_VERIFICATION,
    strategy=InjectionStrategy.SINGLE,
    abort_condition="abort after 1 verified self-check omission in one run",
    verification=f"{_FUTURE_VERIFICATION_PREFIX} an explicit self-verification step is modeled",
    failure_boost=0.25,
    runtime_dispatch=True,
    intensity=1.0,
    expected_observation=ExpectedObservation(
        signal=ObservationSignal.LOCAL_VERIFICATION_SKIPPED,
        verification="the primary local output verification is skipped and observed",
    ),
    runtime_capability=RuntimeCapability.LOCAL_CONTEXT_V1,
)

HUMAN_ESCALATION_TIMEOUT = FaultDefinition(
    fault_id="human_escalation_timeout",
    level=FaultLevel.AGENT,
    family=FaultFamily.HUMAN_IN_THE_LOOP,
    description=(
        "The agent needs human input to proceed safely but the escalation goes "
        "unanswered within the required window (research-identified missing "
        "human-in-the-loop fault category)."
    ),
    injection_point=InjectionPoint.TASK_EXECUTION,
    strategy=InjectionStrategy.SINGLE,
    abort_condition="abort after 1 verified unanswered escalation in one run",
    verification=(
        f"{_FUTURE_VERIFICATION_PREFIX} a modeled human-escalation channel with "
        "response-timeout telemetry is modeled"
    ),
)

# Level 5 (Multi-Agent): the original vision's six faults plus three
# MAST-grounded "soft" coordination failures identified as a research gap
# (agent_disagreement, deadlock, conflicting_objectives, cascading_failure,
# malicious_agent, unrequested_clarification_missing,
# reasoning_action_mismatch are cataloged-but-not-yet-dispatched, matching
# the Data/Agent-level pattern above; message_loss and
# information_withholding have real dispatch through a separate mechanism,
# see the module docstring and arise_x.chaos.injector).

_FUTURE_MULTI_AGENT_VERIFICATION_PREFIX = (
    "requires evidence beyond the star-topology coordinator's rule-based "
    "verification; deferred until"
)

AGENT_DISAGREEMENT = FaultDefinition(
    fault_id="agent_disagreement",
    level=FaultLevel.MULTI_AGENT,
    description=(
        "Coordinator and worker agents reach incompatible conclusions about the "
        "correct course of action for the same sub-task (Level 5 vision fault)."
    ),
    injection_point=InjectionPoint.COORDINATION,
    strategy=InjectionStrategy.INTERMITTENT,
    abort_condition="abort after 3 consecutive verified disagreement events in one run",
    verification=(
        f"{_FUTURE_MULTI_AGENT_VERIFICATION_PREFIX} cross-agent conclusion comparison is modeled"
    ),
)

DEADLOCK = FaultDefinition(
    fault_id="deadlock",
    level=FaultLevel.MULTI_AGENT,
    description=(
        "Two or more agents wait on each other's output and no agent makes "
        "progress (Level 5 vision fault)."
    ),
    injection_point=InjectionPoint.COORDINATION,
    strategy=InjectionStrategy.PERSISTENT,
    abort_condition="abort after 1 verified deadlock event in one run",
    verification=(
        f"{_FUTURE_MULTI_AGENT_VERIFICATION_PREFIX} cross-agent wait-state tracking is modeled"
    ),
)

MESSAGE_LOSS = FaultDefinition(
    fault_id="message_loss",
    level=FaultLevel.MULTI_AGENT,
    description=(
        "A coordinator-to-worker message is dropped in transit and the worker "
        "never receives its sub-task assignment (Level 5 vision fault)."
    ),
    injection_point=InjectionPoint.COORDINATION,
    strategy=InjectionStrategy.INTERMITTENT,
    abort_condition="abort after 3 consecutive verified message-loss events in one run",
    verification=(
        "the star-topology coordinator's handoff milestone reports the worker's "
        "response as not received (see arise_x.chaos.injector.dispatch_message_loss)"
    ),
    failure_boost=0.25,
    runtime_capability=RuntimeCapability.MULTI_AGENT_COORDINATION_V1,
)

CONFLICTING_OBJECTIVES = FaultDefinition(
    fault_id="conflicting_objectives",
    level=FaultLevel.MULTI_AGENT,
    description=(
        "Worker agents pursue sub-goals that undermine each other or the shared "
        "scenario objective (Level 5 vision fault)."
    ),
    injection_point=InjectionPoint.COORDINATION,
    strategy=InjectionStrategy.PERSISTENT,
    abort_condition="abort after 1 verified conflicting-objectives event in one run",
    verification=f"{_FUTURE_MULTI_AGENT_VERIFICATION_PREFIX} per-worker goal tracking is modeled",
)

CASCADING_FAILURE = FaultDefinition(
    fault_id="cascading_failure",
    level=FaultLevel.MULTI_AGENT,
    description=(
        "One worker's failure propagates and degrades or fails downstream worker "
        "sub-tasks (Level 5 vision fault)."
    ),
    injection_point=InjectionPoint.COORDINATION,
    strategy=InjectionStrategy.BURST,
    abort_condition="abort after 1 verified cascading-failure event in one run",
    verification=(
        f"{_FUTURE_MULTI_AGENT_VERIFICATION_PREFIX} cross-worker failure-propagation "
        "tracking is modeled"
    ),
)

MALICIOUS_AGENT = FaultDefinition(
    fault_id="malicious_agent",
    level=FaultLevel.MULTI_AGENT,
    family=FaultFamily.SECURITY_ADVERSARIAL,
    description=(
        "A worker agent deliberately returns manipulated output to subvert the "
        "coordinator's objective (Level 5 vision fault)."
    ),
    injection_point=InjectionPoint.COORDINATION,
    strategy=InjectionStrategy.SINGLE,
    abort_condition="abort after 1 verified malicious-agent event in one run",
    verification=(
        f"{_FUTURE_MULTI_AGENT_VERIFICATION_PREFIX} provenance/integrity checking "
        "across agents is modeled"
    ),
)

INFORMATION_WITHHOLDING = FaultDefinition(
    fault_id="information_withholding",
    level=FaultLevel.MULTI_AGENT,
    description=(
        "The coordinator omits context a worker needed to complete its sub-task "
        "(MAST-grounded soft coordination failure identified as a Level 5 gap)."
    ),
    injection_point=InjectionPoint.COORDINATION,
    strategy=InjectionStrategy.INTERMITTENT,
    abort_condition=(
        "abort after 3 consecutive verified information-withholding events in one run"
    ),
    verification=(
        "the star-topology coordinator's information-exchange milestone reports "
        "withheld context for the worker (see "
        "arise_x.chaos.injector.dispatch_information_withholding)"
    ),
    failure_boost=0.25,
    runtime_capability=RuntimeCapability.MULTI_AGENT_COORDINATION_V1,
)

UNREQUESTED_CLARIFICATION_MISSING = FaultDefinition(
    fault_id="unrequested_clarification_missing",
    level=FaultLevel.MULTI_AGENT,
    description=(
        "A worker proceeds on an ambiguous sub-task instead of requesting the "
        "clarification it should have asked for (MAST-grounded soft coordination "
        "failure)."
    ),
    injection_point=InjectionPoint.COORDINATION,
    strategy=InjectionStrategy.INTERMITTENT,
    abort_condition=(
        "abort after 3 consecutive verified missing-clarification events in one run"
    ),
    verification=(
        f"{_FUTURE_MULTI_AGENT_VERIFICATION_PREFIX} an ambiguity/clarification-request "
        "signal is modeled"
    ),
)

REASONING_ACTION_MISMATCH = FaultDefinition(
    fault_id="reasoning_action_mismatch",
    level=FaultLevel.MULTI_AGENT,
    description=(
        "A worker's stated reasoning does not match the action or output it "
        "actually returns (MAST-grounded soft coordination failure)."
    ),
    injection_point=InjectionPoint.COORDINATION,
    strategy=InjectionStrategy.INTERMITTENT,
    abort_condition=(
        "abort after 3 consecutive verified reasoning/action mismatches in one run"
    ),
    verification=(
        f"{_FUTURE_MULTI_AGENT_VERIFICATION_PREFIX} separate reasoning-trace and "
        "action evidence is modeled"
    ),
)

CATALOG: tuple[FaultDefinition, ...] = (
    BASELINE,
    LATENCY_SPIKE,
    TOOL_DEGRADATION,
    TIMEOUT,
    PACKET_LOSS,
    SERVICE_UNAVAILABLE,
    RATE_LIMITING,
    RESOURCE_EXHAUSTION,
    CLOCK_SKEW,
    COST_SPIKE,
    WRONG_SCHEMA,
    PARTIAL_RESPONSE,
    INCORRECT_RESPONSE,
    TOOL_UNAVAILABLE,
    TOOL_VERSION_CHANGE,
    STALE_DATA,
    MISSING_DATA,
    CONTRADICTORY_DATA,
    CORRUPTED_DATA,
    POISONED_DATA,
    PROMPT_INJECTION,
    PLANNING_FAILURE,
    LOOP,
    GOAL_DRIFT,
    CONTEXT_OVERFLOW,
    MEMORY_CORRUPTION,
    WRONG_TOOL_SELECTION,
    VERIFICATION_FAILURE,
    HUMAN_ESCALATION_TIMEOUT,
    AGENT_DISAGREEMENT,
    DEADLOCK,
    MESSAGE_LOSS,
    CONFLICTING_OBJECTIVES,
    CASCADING_FAILURE,
    MALICIOUS_AGENT,
    INFORMATION_WITHHOLDING,
    UNREQUESTED_CLARIFICATION_MISSING,
    REASONING_ACTION_MISMATCH,
)



def _build_registry(faults: tuple[FaultDefinition, ...]) -> dict[str, FaultDefinition]:
    """Index catalog faults by fault_id, rejecting duplicate identifiers."""

    registry: dict[str, FaultDefinition] = {}
    for fault in faults:
        if fault.fault_id in registry:
            raise FaultCatalogError(f"Duplicate fault_id '{fault.fault_id}' in catalog.")
        registry[fault.fault_id] = fault
    return registry


_BY_ID = _build_registry(CATALOG)

DISPATCHED_FAULT_IDS: frozenset[str] = frozenset(
    fault.fault_id for fault in CATALOG if fault.runtime_dispatch
)


def get_fault(fault_id: str) -> FaultDefinition:
    """Return the catalog fault definition for ``fault_id``.

    Raises:
        FaultCatalogError: If no fault with ``fault_id`` is cataloged.
    """

    try:
        return _BY_ID[fault_id]
    except KeyError as exc:
        raise FaultCatalogError(f"No fault definition cataloged for fault_id '{fault_id}'.") from exc  # noqa: E501


def resolve_fault(fault_id: str) -> FaultDefinition:
    """Resolve ``fault_id`` to a definition without silently changing its meaning."""

    return get_fault(fault_id)
