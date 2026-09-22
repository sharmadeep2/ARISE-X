"""Event structures emitted by experiment runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from arise_x.telemetry.trajectory import Trajectory

_BASELINE_DISRUPTION = "baseline"


@dataclass(frozen=True)
class RunEvent:
    """Telemetry unit for a single task execution."""

    task_id: str
    disruption: str
    success: bool
    policy_violations: int
    interventions: int
    latency_ms: float

    @classmethod
    def from_trajectory(cls, trajectory: Trajectory) -> RunEvent:
        """Project an ordered :class:`Trajectory` down to a flat summary event.

        ``disruption`` is the first fault ID verified as triggered during the
        trajectory, or ``"baseline"`` when no fault was triggered. This keeps
        ``drift/detector.py`` and ``trust/scorer.py`` working against the
        existing flat shape while richer evidence migrates to
        :mod:`arise_x.telemetry.trajectory`.
        """

        triggered = trajectory.triggered_fault_ids
        return cls(
            task_id=trajectory.task_id,
            disruption=triggered[0] if triggered else _BASELINE_DISRUPTION,
            success=trajectory.outcome.goal_achieved,
            policy_violations=trajectory.policy_violation_count,
            interventions=trajectory.intervention_count,
            latency_ms=trajectory.total_latency_ms,
        )
