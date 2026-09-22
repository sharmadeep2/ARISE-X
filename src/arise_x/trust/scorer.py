"""Legacy additive trust diagnostic retained for compatibility."""

from __future__ import annotations

from dataclasses import dataclass

from arise_x.drift.detector import DriftResult
from arise_x.telemetry.events import RunEvent


@dataclass(frozen=True)
class TrustDecision:
    """Legacy additive diagnostic score and threshold verdict."""

    score: float
    trustworthy: bool


def score_trust(event: RunEvent, drift: DriftResult, threshold: float) -> TrustDecision:
    """Compute the compatibility diagnostic; this score is not the ARI."""

    reliability = 1.0 if event.success else 0.0
    safety = max(0.0, 1.0 - (event.policy_violations * 0.1))
    stability = max(0.0, 1.0 - drift.score)
    composite = (0.45 * reliability) + (0.30 * safety) + (0.25 * stability)
    return TrustDecision(score=composite, trustworthy=composite >= threshold)
