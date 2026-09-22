"""Unit tests for trust score behavior."""

from __future__ import annotations

from arise_x.drift.detector import DriftResult
from arise_x.telemetry.events import RunEvent
from arise_x.trust.scorer import score_trust


def test_given_healthy_event_when_score_trust_then_returns_trustworthy() -> None:
    # Arrange
    event = RunEvent(
        task_id="t-1",
        disruption="baseline",
        success=True,
        policy_violations=0,
        interventions=0,
        latency_ms=400,
    )
    drift = DriftResult(score=0.05, is_drifting=False)

    # Act
    decision = score_trust(event, drift, threshold=0.75)

    # Assert
    assert decision.trustworthy is True


def test_given_failed_event_when_score_trust_then_returns_untrustworthy() -> None:
    # Arrange
    event = RunEvent(
        task_id="t-2",
        disruption="tool_degradation",
        success=False,
        policy_violations=2,
        interventions=2,
        latency_ms=2500,
    )
    drift = DriftResult(score=0.80, is_drifting=True)

    # Act
    decision = score_trust(event, drift, threshold=0.75)

    # Assert
    assert decision.trustworthy is False
