"""Trust score computation for release-gate style decisions."""

from __future__ import annotations

from dataclasses import dataclass

from arise_x.drift.detector import DriftResult
from arise_x.telemetry.events import RunEvent


@dataclass(frozen=True)
class TrustDecision:
    """Composite trust score and pass or fail verdict."""

    score: float
    trustworthy: bool


def score_trust(event: RunEvent, drift: DriftResult, threshold: float) -> TrustDecision:
    """Compute trust score where 1.0 is best and 0.0 is worst."""

    reliability = 1.0 if event.success else 0.0
    safety = max(0.0, 1.0 - (event.policy_violations * 0.1))
    stability = max(0.0, 1.0 - drift.score)
    composite = (0.45 * reliability) + (0.30 * safety) + (0.25 * stability)
    return TrustDecision(score=composite, trustworthy=composite >= threshold)
