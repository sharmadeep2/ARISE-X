"""Base protocol for autonomous agents under evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from arise_x.chaos.catalog import InjectionPoint, ObservationSignal, RuntimeCapability


@dataclass(frozen=True)
class AgentResponse:
    """Standardized response shape for evaluated agent outputs."""

    task_id: str
    output_text: str
    success: bool = True
    policy_violations: int = 0
    interventions: int = 0
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None
    fault_observation: FaultObservation | None = None


@dataclass(frozen=True)
class FaultObservation:
    """Agent-reported local effect observed at an explicit injection point."""

    fault_id: str
    injection_point: InjectionPoint
    signal: ObservationSignal
    recovered: bool
    evidence_references: tuple[str, ...]
    policy_reason: str


@dataclass(frozen=True)
class LocalExecutionContext:
    """Bounded in-process fault context supplied only to capable agents."""

    fault_id: str
    injection_point: InjectionPoint
    expected_signal: ObservationSignal
    intensity: float
    should_recover: bool


class AgentUnderTest(Protocol):
    """Protocol implemented by any agent integrated with ARISE-X."""

    def run_task(self, task_id: str, prompt: str) -> AgentResponse:
        """Run a task and return a structured response."""


@runtime_checkable
class LocalFaultCapableAgent(Protocol):
    """Optional protocol for deterministic bounded local fault execution."""

    @property
    def runtime_capabilities(self) -> frozenset[RuntimeCapability]:
        """Return the fault runtime capabilities implemented by this adapter."""

    def fork_for_run(self, seed: int) -> LocalFaultCapableAgent:
        """Return an isolated deterministic agent instance for one execution."""

    def run_task_with_context(
        self,
        task_id: str,
        prompt: str,
        context: LocalExecutionContext,
    ) -> AgentResponse:
        """Run a task with one bounded local fault context."""
