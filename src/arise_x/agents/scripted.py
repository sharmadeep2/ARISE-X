"""Deterministic, provider-neutral scripted agent for evaluated scenarios."""

from __future__ import annotations

from arise_x.agents.base import AgentResponse
from arise_x.scenarios import Scenario


class ScriptedAgent:
    """Deterministic agent that scripts responses from a scenario definition.

    Produces the same :class:`AgentResponse` for a given task ID and prompt on
    every call. It never calls an external LLM or network service; responses
    are derived purely from the injected scenario's objective, constraints,
    and expected outcome.
    """

    version = "scripted-agent-v1"

    def __init__(self, scenario: Scenario) -> None:
        self._scenario = scenario

    def run_task(self, task_id: str, prompt: str) -> AgentResponse:
        """Return a deterministic response derived from the scenario and task."""

        constraints = "; ".join(self._scenario.constraints)
        output_text = (
            f"[{task_id}] {prompt} => objective '{self._scenario.objective}' "
            f"satisfied under constraints ({constraints}); "
            f"outcome: {self._scenario.expected_outcome}"
        )
        return AgentResponse(
            task_id=task_id,
            output_text=output_text,
            success=True,
            policy_violations=0,
            interventions=0,
        )
