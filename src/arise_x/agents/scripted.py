"""Deterministic, provider-neutral scripted agent for evaluated scenarios."""

from __future__ import annotations

from arise_x.agents.base import AgentResponse, FaultObservation, LocalExecutionContext
from arise_x.chaos.catalog import ObservationSignal, RuntimeCapability
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

    @property
    def runtime_capabilities(self) -> frozenset[RuntimeCapability]:
        """Return the bounded local fault capability implemented by this adapter."""

        return frozenset({RuntimeCapability.LOCAL_CONTEXT_V1})

    def fork_for_run(self, seed: int) -> ScriptedAgent:
        """Return an isolated deterministic adapter for a control or experiment run."""

        del seed
        return ScriptedAgent(self._scenario)

    def run_task(self, task_id: str, prompt: str) -> AgentResponse:
        """Return a deterministic response derived from the scenario and task."""

        return self._execute_local_pipeline(task_id, prompt, context=None)

    def _execute_local_pipeline(
        self,
        task_id: str,
        prompt: str,
        *,
        context: LocalExecutionContext | None,
    ) -> AgentResponse:
        """Execute deterministic local dependency, tool, data, and verification stages."""

        dependency_ready = True
        tool_result_complete = True
        data_is_current = True
        output_verified = True
        observation: FaultObservation | None = None

        if context is not None:
            if context.expected_signal is ObservationSignal.LOCAL_DEPENDENCY_DELAY:
                dependency_ready = False
            elif context.expected_signal is ObservationSignal.LOCAL_TOOL_DEGRADATION:
                tool_result_complete = False
            elif context.expected_signal is ObservationSignal.LOCAL_STALE_DATA:
                data_is_current = False
            elif context.expected_signal is ObservationSignal.LOCAL_VERIFICATION_SKIPPED:
                output_verified = False
            else:
                raise NotImplementedError(
                    f"ScriptedAgent does not implement signal '{context.expected_signal.value}'."
                )

            observed_before_recovery = not all(
                (dependency_ready, tool_result_complete, data_is_current, output_verified)
            )
            if context.should_recover:
                dependency_ready = True
                tool_result_complete = True
                data_is_current = True
                output_verified = True
            recovered = all(
                (dependency_ready, tool_result_complete, data_is_current, output_verified)
            )
            if observed_before_recovery:
                observation = FaultObservation(
                    fault_id=context.fault_id,
                    injection_point=context.injection_point,
                    signal=context.expected_signal,
                    recovered=recovered,
                    evidence_references=(
                        f"local:{task_id}:{context.injection_point.value}:"
                        f"{context.expected_signal.value}",
                    ),
                    policy_reason=(
                        "bounded local effect observed and recovered by deterministic fallback"
                        if recovered
                        else "bounded local effect observed with recovery disabled by intensity"
                    ),
                )

        success = all(
            (dependency_ready, tool_result_complete, data_is_current, output_verified)
        )
        constraints = "; ".join(self._scenario.constraints)
        output_text = (
            (
                f"[{task_id}] {prompt} => objective '{self._scenario.objective}' "
                f"satisfied under constraints ({constraints}); "
                f"outcome: {self._scenario.expected_outcome}"
            )
            if success
            else f"[{task_id}] local execution did not complete after a bounded fault"
        )
        return AgentResponse(
            task_id=task_id,
            output_text=output_text,
            success=success,
            policy_violations=0,
            interventions=0,
            fault_observation=observation,
        )

    def run_task_with_context(
        self,
        task_id: str,
        prompt: str,
        context: LocalExecutionContext,
    ) -> AgentResponse:
        """Execute one representative fault through a deterministic local pipeline."""

        return self._execute_local_pipeline(task_id, prompt, context=context)
