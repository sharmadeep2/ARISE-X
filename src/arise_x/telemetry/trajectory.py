"""Immutable, correlated, and redacted trajectory evidence for ARISE-X episodes."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum

from arise_x.chaos.catalog import InjectionPoint


class TrajectoryValidationError(ValueError):
    """Raised when trajectory or step evidence fails validation."""


class ContentKind(StrEnum):
    """Sensitive content surfaces represented by explicit redaction markers."""

    PROMPT = "prompt"
    TOOL_PAYLOAD = "tool_payload"
    TOOL_RESPONSE = "tool_response"
    OUTPUT = "output"


class RedactionMarker(StrEnum):
    """Allowed persisted representations for sensitive content."""

    REDACTED = "redacted"
    OMITTED = "omitted"


class OutcomeStatus(StrEnum):
    """Terminal execution status consistent with goal achievement."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"


def _require_non_empty_string(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise TrajectoryValidationError(f"{name} must be a non-empty string.")


def _freeze_references(references: object, name: str) -> tuple[str, ...]:
    if isinstance(references, str) or not isinstance(references, list | tuple):
        raise TrajectoryValidationError(f"{name} must be a sequence of reference strings.")
    frozen = tuple(references)
    if any(not isinstance(reference, str) or not reference.strip() for reference in frozen):
        raise TrajectoryValidationError(f"{name} must contain only non-empty strings.")
    if len(set(frozen)) != len(frozen):
        raise TrajectoryValidationError(f"{name} must not contain duplicate references.")
    return frozen


@dataclass(frozen=True)
class RedactedContent:
    """Persistable marker for sensitive content without retaining the raw value."""

    kind: ContentKind
    reference_id: str
    marker: RedactionMarker = RedactionMarker.REDACTED

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ContentKind):
            raise TrajectoryValidationError("Redacted content kind must be a ContentKind.")
        _require_non_empty_string(self.reference_id, "Redacted content reference_id")
        if not isinstance(self.marker, RedactionMarker):
            raise TrajectoryValidationError("Redacted content marker must be a RedactionMarker.")


@dataclass(frozen=True)
class ToolInvocation:
    """A correlated tool call and response represented without raw content."""

    call_id: str
    name: str
    call_payload: RedactedContent | None = None
    response_payload: RedactedContent | None = None

    def __post_init__(self) -> None:
        _require_non_empty_string(self.call_id, "Tool invocation call_id")
        _require_non_empty_string(self.name, "Tool invocation name")
        self._validate_content(self.call_payload, ContentKind.TOOL_PAYLOAD, "call_payload")
        self._validate_content(
            self.response_payload,
            ContentKind.TOOL_RESPONSE,
            "response_payload",
        )

    @staticmethod
    def _validate_content(
        content: RedactedContent | None,
        expected_kind: ContentKind,
        field_name: str,
    ) -> None:
        if content is not None and not isinstance(content, RedactedContent):
            raise TrajectoryValidationError(
                f"Tool {field_name} must be RedactedContent or None; raw content is forbidden."
            )
        if content is not None and content.kind is not expected_kind:
            raise TrajectoryValidationError(
                f"Tool {field_name} must use content kind {expected_kind.value!r}."
            )


@dataclass(frozen=True)
class FaultTrigger:
    """Immutable fault receipt correlated to one trajectory step."""

    fault_id: str
    verified: bool = False
    attempted: bool = True
    triggered: bool | None = None
    observed: bool | None = None
    recovered: bool | None = None
    aborted: bool = False
    injection_point: InjectionPoint = InjectionPoint.TASK_EXECUTION
    affected_evidence_references: tuple[str, ...] = ()
    policy_reason: str = ""
    control_pair_id: str | None = None
    control_role: str | None = None
    control_outcome: bool | None = None
    control_evidence_reference: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_string(self.fault_id, "Fault trigger fault_id")
        if not isinstance(self.verified, bool):
            raise TrajectoryValidationError("Fault trigger verified must be a bool.")
        for field_name in ("attempted", "aborted"):
            if not isinstance(getattr(self, field_name), bool):
                raise TrajectoryValidationError(f"Fault trigger {field_name} must be a bool.")
        triggered = self.verified if self.triggered is None else self.triggered
        observed = self.verified if self.observed is None else self.observed
        object.__setattr__(self, "triggered", triggered)
        object.__setattr__(self, "observed", observed)
        if not isinstance(triggered, bool) or not isinstance(observed, bool):
            raise TrajectoryValidationError("Fault trigger states must be bool values.")
        if self.verified and not observed:
            raise TrajectoryValidationError("Verified fault receipts require an observed effect.")
        if observed and not triggered:
            raise TrajectoryValidationError("Observed fault effects require a triggered attempt.")
        if self.recovered is not None and (
            not isinstance(self.recovered, bool) or not self.verified
        ):
            raise TrajectoryValidationError(
                "Fault recovery is available only as a bool for verified effects."
            )
        if self.aborted and (triggered or observed or self.verified):
            raise TrajectoryValidationError("Aborted faults cannot be triggered or observed.")
        if not isinstance(self.injection_point, InjectionPoint):
            try:
                object.__setattr__(self, "injection_point", InjectionPoint(self.injection_point))
            except ValueError as exc:
                raise TrajectoryValidationError(
                    "Fault trigger injection_point must be a known InjectionPoint."
                ) from exc
        references = _freeze_references(
            self.affected_evidence_references,
            "Fault trigger affected_evidence_references",
        )
        object.__setattr__(self, "affected_evidence_references", references)
        if self.verified and not references:
            raise TrajectoryValidationError(
                "Verified fault receipts require affected evidence references."
            )
        if not isinstance(self.policy_reason, str):
            raise TrajectoryValidationError("Fault trigger policy_reason must be a string.")
        if self.control_pair_id is not None:
            _require_non_empty_string(self.control_pair_id, "Fault trigger control_pair_id")
            if self.control_role not in {"control", "experiment"}:
                raise TrajectoryValidationError(
                    "Paired fault receipts require control_role='control' or 'experiment'."
                )
        elif self.control_role is not None:
            raise TrajectoryValidationError("Fault trigger control_role requires control_pair_id.")
        if self.control_outcome is not None and not isinstance(self.control_outcome, bool):
            raise TrajectoryValidationError("Fault trigger control_outcome must be bool or None.")
        if self.control_evidence_reference is not None:
            _require_non_empty_string(
                self.control_evidence_reference,
                "Fault trigger control_evidence_reference",
            )
        if self.control_role == "experiment" and (
            self.control_outcome is None or self.control_evidence_reference is None
        ):
            raise TrajectoryValidationError(
                "Experiment receipts require the paired control outcome and evidence reference."
            )


@dataclass(frozen=True)
class RecoveryEvidence:
    """A recovery attempt correlated to a verified fault."""

    fault_id: str
    action: str
    successful: bool
    evidence_references: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_non_empty_string(self.fault_id, "Recovery fault_id")
        _require_non_empty_string(self.action, "Recovery action")
        if not isinstance(self.successful, bool):
            raise TrajectoryValidationError("Recovery successful must be a bool.")
        references = _freeze_references(
            self.evidence_references,
            "Recovery evidence_references",
        )
        if not references:
            raise TrajectoryValidationError("Recovery evidence requires at least one reference.")
        object.__setattr__(self, "evidence_references", references)


@dataclass(frozen=True)
class UsageMetrics:
    """Per-step timing, token, and cost roll-ups."""

    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0

    def __post_init__(self) -> None:
        for field_name in ("latency_ms", "cost_usd"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise TrajectoryValidationError(f"{field_name} must be a finite number.")
            if not math.isfinite(value):
                raise TrajectoryValidationError(f"{field_name} must be finite.")
            if value < 0:
                raise TrajectoryValidationError(f"{field_name} must be non-negative, got {value}.")
        for field_name in ("prompt_tokens", "completion_tokens"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TrajectoryValidationError(f"{field_name} must be an integer.")
            if value < 0:
                raise TrajectoryValidationError(f"{field_name} must be non-negative.")


@dataclass(frozen=True)
class Step:
    """One ordered State -> Action -> Tool -> Response -> Recovery transition."""

    index: int
    action: str
    state_transition: str
    tool: ToolInvocation | None = None
    fault: FaultTrigger | None = None
    recovered: bool = False
    recovery: RecoveryEvidence | None = None
    usage: UsageMetrics = field(default_factory=UsageMetrics)
    prompt_text: RedactedContent | None = None
    output_text: RedactedContent | None = None

    def __post_init__(self) -> None:
        if isinstance(self.index, bool) or not isinstance(self.index, int) or self.index < 0:
            raise TrajectoryValidationError(
                f"Step index must be a non-negative integer, got {self.index!r}."
            )
        _require_non_empty_string(self.action, "Step action")
        _require_non_empty_string(self.state_transition, "Step state_transition")
        parts = self.state_transition.split("->")
        if len(parts) != 2 or any(not part.strip() for part in parts):
            raise TrajectoryValidationError(
                "Step state_transition must use the non-empty 'state->state' form."
            )
        if self.tool is not None and not isinstance(self.tool, ToolInvocation):
            raise TrajectoryValidationError("Step tool must be a ToolInvocation or None.")
        if self.fault is not None and not isinstance(self.fault, FaultTrigger):
            raise TrajectoryValidationError("Step fault must be a FaultTrigger or None.")
        if not isinstance(self.recovered, bool):
            raise TrajectoryValidationError("Step recovered must be a bool.")
        if self.recovery is not None and not isinstance(self.recovery, RecoveryEvidence):
            raise TrajectoryValidationError("Step recovery must be RecoveryEvidence or None.")
        if not isinstance(self.usage, UsageMetrics):
            raise TrajectoryValidationError("Step usage must be UsageMetrics.")
        self._validate_content(self.prompt_text, ContentKind.PROMPT, "prompt_text")
        self._validate_content(self.output_text, ContentKind.OUTPUT, "output_text")
        self._validate_recovery()

    @property
    def initial_state(self) -> str:
        """Return the state before this step's action."""

        return self.state_transition.split("->", maxsplit=1)[0].strip()

    @property
    def final_state(self) -> str:
        """Return the state after this step's response and recovery."""

        return self.state_transition.split("->", maxsplit=1)[1].strip()

    def _validate_content(
        self,
        content: RedactedContent | None,
        expected_kind: ContentKind,
        field_name: str,
    ) -> None:
        if content is not None and not isinstance(content, RedactedContent):
            raise TrajectoryValidationError(
                f"Step {field_name} must be RedactedContent or None; raw content is forbidden."
            )
        if content is not None and content.kind is not expected_kind:
            raise TrajectoryValidationError(
                f"Step {field_name} must use content kind {expected_kind.value!r}."
            )

    def _validate_recovery(self) -> None:
        if self.recovered and (
            self.fault is None
            or not self.fault.verified
            or self.recovery is None
            or not self.recovery.successful
        ):
            raise TrajectoryValidationError(
                "Step recovered=True requires successful recovery evidence for a verified fault."
            )
        if self.recovery is None:
            return
        if self.fault is None or not self.fault.verified:
            raise TrajectoryValidationError("Recovery evidence requires a verified fault.")
        if self.recovery.fault_id != self.fault.fault_id:
            raise TrajectoryValidationError("Recovery fault_id must match the verified fault_id.")
        if self.recovered != self.recovery.successful:
            raise TrajectoryValidationError(
                "Step recovered must match recovery successful evidence."
            )


@dataclass(frozen=True)
class Outcome:
    """Verified terminal trajectory result and final state."""

    goal_achieved: bool
    label: str
    status: OutcomeStatus
    terminal_state: str
    evidence_references: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.goal_achieved, bool):
            raise TrajectoryValidationError("Outcome goal_achieved must be a bool.")
        _require_non_empty_string(self.label, "Outcome label")
        if not isinstance(self.status, OutcomeStatus):
            raise TrajectoryValidationError("Outcome status must be an OutcomeStatus.")
        _require_non_empty_string(self.terminal_state, "Outcome terminal_state")
        references = _freeze_references(
            self.evidence_references,
            "Outcome evidence_references",
        )
        if not references:
            raise TrajectoryValidationError("Outcome requires at least one evidence reference.")
        object.__setattr__(self, "evidence_references", references)
        expected_goal = self.status is OutcomeStatus.SUCCEEDED
        if self.goal_achieved is not expected_goal:
            raise TrajectoryValidationError(
                "Outcome goal_achieved must agree with the terminal status."
            )


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
    """Ordered, correlated evidence for a single agent episode."""

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
            _require_non_empty_string(getattr(self, name), f"Trajectory {name}")
        for name in ("suite_version", "scenario_version"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise TrajectoryValidationError(
                    f"{name} must be a positive integer, got {value!r}."
                )
        if isinstance(self.steps, str) or not isinstance(self.steps, list | tuple):
            raise TrajectoryValidationError("Trajectory steps must be a sequence of Step evidence.")
        steps = tuple(self.steps)
        if not steps:
            raise TrajectoryValidationError("Trajectory must contain at least one step.")
        if any(not isinstance(step, Step) for step in steps):
            raise TrajectoryValidationError("Trajectory steps must contain only Step evidence.")
        object.__setattr__(self, "steps", steps)
        expected_indices = tuple(range(len(steps)))
        actual_indices = tuple(step.index for step in steps)
        if actual_indices != expected_indices:
            raise TrajectoryValidationError(
                "Step indices must be ordered and unique starting from 0, "
                f"got {actual_indices}."
            )
        if not isinstance(self.outcome, Outcome):
            raise TrajectoryValidationError("Trajectory outcome must be an Outcome.")
        if steps[-1].final_state != self.outcome.terminal_state:
            raise TrajectoryValidationError(
                "Outcome terminal state must match the final step state."
            )
        for name in ("intervention_count", "policy_violation_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise TrajectoryValidationError(f"{name} must be a non-negative integer.")

    @property
    def total_latency_ms(self) -> float:
        """Sum per-step latency across the trajectory."""

        return sum(step.usage.latency_ms for step in self.steps)

    @property
    def total_prompt_tokens(self) -> int:
        """Sum per-step prompt tokens across the trajectory."""

        return sum(step.usage.prompt_tokens for step in self.steps)

    @property
    def total_completion_tokens(self) -> int:
        """Sum per-step completion tokens across the trajectory."""

        return sum(step.usage.completion_tokens for step in self.steps)

    @property
    def total_cost_usd(self) -> float:
        """Sum per-step cost across the trajectory."""

        return sum(step.usage.cost_usd for step in self.steps)

    @property
    def triggered_fault_ids(self) -> tuple[str, ...]:
        """Return ordered, de-duplicated verified fault IDs."""

        seen: dict[str, None] = {}
        for step in self.steps:
            if step.fault is not None and step.fault.verified:
                seen.setdefault(step.fault.fault_id, None)
        return tuple(seen)
