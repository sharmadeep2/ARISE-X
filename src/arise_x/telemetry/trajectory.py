"""Immutable trajectory evidence for ARISE-X long-horizon episodes.

A :class:`Trajectory` models an episode as ordered, correlated evidence -
the State -> Action -> Tool -> Response -> Recovery -> Final State sequence
described in the ARISE-X requirement - rather than a single flat success or
failure event. Each :class:`Step` records what happened at one point in the
episode; the :class:`Trajectory` aggregates the steps together with the
correlation identifiers (run, task, cluster, suite, agent) needed to compare
runs later. :class:`arise_x.telemetry.events.RunEvent` remains the flat,
existing summary shape consumed by ``drift/detector.py`` and
``trust/scorer.py``; see ``RunEvent.from_trajectory`` for the projection.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class TrajectoryValidationError(ValueError):
    """Raised when trajectory or step evidence fails validation."""


@dataclass(frozen=True)
class ToolInvocation:
    """A tool call and its response within a single step.

    ``call_payload`` and ``response_payload`` are optional raw text fields and
    may be omitted/redacted for held-out or sensitive tasks; a valid
    invocation only requires the tool ``name``.
    """

    name: str
    call_payload: str | None = None
    response_payload: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise TrajectoryValidationError("Tool invocation requires a non-empty name.")


@dataclass(frozen=True)
class FaultTrigger:
    """A configured fault checked for at a step, and whether it was verified."""

    fault_id: str
    verified: bool = False

    def __post_init__(self) -> None:
        if not self.fault_id:
            raise TrajectoryValidationError("Fault trigger requires a non-empty fault_id.")


@dataclass(frozen=True)
class UsageMetrics:
    """Per-step timing, token, and cost roll-ups."""

    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0

    def __post_init__(self) -> None:
        if self.latency_ms < 0:
            raise TrajectoryValidationError(
                f"latency_ms must be non-negative, got {self.latency_ms}."
            )
        if self.prompt_tokens < 0 or self.completion_tokens < 0:
            raise TrajectoryValidationError("Token counts must be non-negative.")
        if self.cost_usd < 0:
            raise TrajectoryValidationError(f"cost_usd must be non-negative, got {self.cost_usd}.")


@dataclass(frozen=True)
class Step:
    """A single ordered unit of trajectory evidence.

    ``prompt_text`` and ``output_text`` are optional raw text fields and may
    be omitted/redacted for held-out or sensitive tasks; a valid step never
    requires raw prompt or output content.
    """

    index: int
    action: str
    state_transition: str
    tool: ToolInvocation | None = None
    fault: FaultTrigger | None = None
    recovered: bool = False
    usage: UsageMetrics = field(default_factory=UsageMetrics)
    prompt_text: str | None = None
    output_text: str | None = None

    def __post_init__(self) -> None:
        if self.index < 0:
            raise TrajectoryValidationError(f"Step index must be non-negative, got {self.index}.")
        if not self.action:
            raise TrajectoryValidationError("Step action must not be empty.")
        if not self.state_transition:
            raise TrajectoryValidationError("Step state_transition must not be empty.")


@dataclass(frozen=True)
class Outcome:
    """The final trajectory outcome: goal achievement plus a short label."""

    goal_achieved: bool
    label: str

    def __post_init__(self) -> None:
        if not self.label:
            raise TrajectoryValidationError("Outcome label must not be empty.")


_REQUIRED_IDENTITY_FIELDS = (
    "run_id",
    "task_id",
    "family",
    "cluster_id",
    "suite_id",
    "suite_partition",
    "repeat_id",
    "scenario_name",
    "agent_id",
    "agent_version",
)


@dataclass(frozen=True)
class Trajectory:
    """Ordered, correlated evidence for a single agent episode.

    Aggregates the correlation identifiers needed to compare runs (run, task,
    task-family/cluster, suite version/partition, repeat/seed, scenario,
    agent) with the ordered :class:`Step` evidence and the final
    :class:`Outcome`. Total timing and cost are derived from the steps rather
    than stored redundantly.
    """

    run_id: str
    task_id: str
    family: str
    cluster_id: str
    suite_id: str
    suite_version: int
    suite_partition: str
    repeat_id: str
    scenario_name: str
    scenario_version: int
    agent_id: str
    agent_version: str
    steps: tuple[Step, ...]
    outcome: Outcome
    intervention_count: int = 0
    policy_violation_count: int = 0

    def __post_init__(self) -> None:
        for name in _REQUIRED_IDENTITY_FIELDS:
            if not getattr(self, name):
                raise TrajectoryValidationError(f"Trajectory requires a non-empty {name}.")
        if self.suite_version <= 0:
            raise TrajectoryValidationError(
                f"suite_version must be positive, got {self.suite_version}."
            )
        if self.scenario_version <= 0:
            raise TrajectoryValidationError(
                f"scenario_version must be positive, got {self.scenario_version}."
            )
        if not self.steps:
            raise TrajectoryValidationError("Trajectory must contain at least one step.")
        expected_indices = tuple(range(len(self.steps)))
        actual_indices = tuple(step.index for step in self.steps)
        if actual_indices != expected_indices:
            raise TrajectoryValidationError(
                "Step indices must be ordered and unique starting from 0, "
                f"got {actual_indices}."
            )
        if self.intervention_count < 0:
            raise TrajectoryValidationError("intervention_count must be non-negative.")
        if self.policy_violation_count < 0:
            raise TrajectoryValidationError("policy_violation_count must be non-negative.")

    @property
    def total_latency_ms(self) -> float:
        """Sum of per-step latency across the trajectory."""

        return sum(step.usage.latency_ms for step in self.steps)

    @property
    def total_prompt_tokens(self) -> int:
        """Sum of per-step prompt tokens across the trajectory."""

        return sum(step.usage.prompt_tokens for step in self.steps)

    @property
    def total_completion_tokens(self) -> int:
        """Sum of per-step completion tokens across the trajectory."""

        return sum(step.usage.completion_tokens for step in self.steps)

    @property
    def total_cost_usd(self) -> float:
        """Sum of per-step cost across the trajectory."""

        return sum(step.usage.cost_usd for step in self.steps)

    @property
    def triggered_fault_ids(self) -> tuple[str, ...]:
        """Ordered, de-duplicated IDs of faults verified as triggered during the run."""

        seen: dict[str, None] = {}
        for step in self.steps:
            if step.fault is not None and step.fault.verified:
                seen.setdefault(step.fault.fault_id, None)
        return tuple(seen)
