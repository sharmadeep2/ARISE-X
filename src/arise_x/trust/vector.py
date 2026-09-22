"""Agent Reliability Vector: per-dimension, independently auditable reliability evidence.

The vector is the primary analytic artifact for agent reliability. Each dimension
is normalized and reported separately with its own evidence coverage so that no
single hidden weighted, multiplicative, or geometric composite hides trade-offs
between dimensions. A gating scalar (Agent Reliability Index) is derived from
this vector in a later phase; it is intentionally not computed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

NORMALIZATION_VERSION = "v1"


class VectorDimension(StrEnum):
    """Named dimensions of the Agent Reliability Vector."""

    GOAL_SUCCESS = "goal_success"
    RESILIENCE = "resilience"
    BEHAVIORAL_STABILITY = "behavioral_stability"
    RECOVERY = "recovery"
    SAFETY = "safety"
    EFFICIENCY = "efficiency"
    COST = "cost"
    AUTONOMY = "autonomy"


@dataclass(frozen=True)
class DimensionScore:
    """Normalized score for a single reliability-vector dimension.

    Args:
        dimension: Which named dimension this score represents.
        value: Normalized score in [0.0, 1.0]. Only meaningful when `available`
            is True; callers must check `available` before trusting `value`.
        available: Whether sufficient evidence exists to trust `value`. A
            missing or insufficient-evidence dimension must be represented as
            `available=False` rather than defaulting to a perfect score.
        evidence_count: Count of underlying observations backing this score.
        normalization_version: Version identifier for the normalization scheme
            used to compute `value`.

    Raises:
        ValueError: If `value` is outside [0.0, 1.0] or `evidence_count` is negative.
    """

    dimension: VectorDimension
    value: float
    available: bool
    evidence_count: int
    normalization_version: str = NORMALIZATION_VERSION

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 1.0:
            msg = f"Dimension value must be within [0.0, 1.0], got {self.value}"
            raise ValueError(msg)
        if self.evidence_count < 0:
            msg = f"Evidence count must be non-negative, got {self.evidence_count}"
            raise ValueError(msg)

    @classmethod
    def unavailable(
        cls,
        dimension: VectorDimension,
        *,
        normalization_version: str = NORMALIZATION_VERSION,
    ) -> DimensionScore:
        """Construct a score explicitly marking a dimension as unavailable.

        Args:
            dimension: Which named dimension is unavailable.
            normalization_version: Version identifier for the normalization scheme.

        Returns:
            A `DimensionScore` with `available=False` and no evidence, so
            downstream consumers cannot mistake it for a perfect score.
        """
        return cls(
            dimension=dimension,
            value=0.0,
            available=False,
            evidence_count=0,
            normalization_version=normalization_version,
        )


@dataclass(frozen=True)
class ReliabilityVector:
    """Agent Reliability Vector aggregating one score per named dimension.

    This vector intentionally contains no weighted, multiplicative, or
    geometric composite score. It is the auditable, per-dimension analytic
    artifact; a gating scalar is derived separately in a later phase.

    Raises:
        ValueError: If any field's `DimensionScore.dimension` does not match
            the field it is assigned to.
    """

    goal_success: DimensionScore
    resilience: DimensionScore
    behavioral_stability: DimensionScore
    recovery: DimensionScore
    safety: DimensionScore
    efficiency: DimensionScore
    cost: DimensionScore
    autonomy: DimensionScore
    schema_version: str = NORMALIZATION_VERSION

    def __post_init__(self) -> None:
        for expected, score in zip(VectorDimension, self._scores(), strict=True):
            if score.dimension != expected:
                msg = f"Expected dimension {expected} for field but got {score.dimension}"
                raise ValueError(msg)

    def dimension(self, name: VectorDimension) -> DimensionScore:
        """Look up a dimension score by name.

        Args:
            name: The named dimension to retrieve.

        Returns:
            The `DimensionScore` for the requested dimension.

        Raises:
            KeyError: If `name` is not a recognized vector dimension.
        """
        for score in self._scores():
            if score.dimension == name:
                return score
        msg = f"Unknown reliability vector dimension: {name}"
        raise KeyError(msg)

    def all_available(self) -> bool:
        """Return True only when every dimension has sufficient evidence."""
        return all(score.available for score in self._scores())

    def _scores(self) -> tuple[DimensionScore, ...]:
        return (
            self.goal_success,
            self.resilience,
            self.behavioral_stability,
            self.recovery,
            self.safety,
            self.efficiency,
            self.cost,
            self.autonomy,
        )
