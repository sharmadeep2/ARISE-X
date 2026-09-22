"""Base protocol for autonomous agents under evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AgentResponse:
    """Standardized response shape for evaluated agent outputs."""

    task_id: str
    output_text: str
    success: bool = True
    policy_violations: int = 0
    interventions: int = 0


class AgentUnderTest(Protocol):
    """Protocol implemented by any agent integrated with ARISE-X."""

    def run_task(self, task_id: str, prompt: str) -> AgentResponse:
        """Run a task and return a structured response."""
