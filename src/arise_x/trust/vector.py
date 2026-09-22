"""Eight independently auditable dimensions of agent reliability evidence."""

from __future__ import annotations

import math
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
class ConfidenceMetadata:
    """Confidence assigned to a dimension and the method that produced it."""

    score: float
    method: str

    def __post_init__(self) -> None:
        if isinstance(self.score, bool) or not isinstance(self.score, int | float):
            raise ValueError("Confidence score must be a finite number")
        if not math.isfinite(self.score) or not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Confidence score must be within [0.0, 1.0], got {self.score}")
        if not isinstance(self.method, str) or not self.method.strip():
            raise ValueError("Confidence method must be a non-empty string")


@dataclass(frozen=True)
class DimensionScore:
    """Normalized score with explicit coverage, confidence, and evidence references."""

    dimension: VectorDimension
    value: float
    available: bool
    evidence_count: int
    evidence_total: int
    confidence: ConfidenceMetadata | None
    evidence_references: tuple[str, ...]
    normalization_version: str = NORMALIZATION_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.dimension, VectorDimension):
            raise ValueError("Dimension must be a VectorDimension")
        if isinstance(self.value, bool) or not isinstance(self.value, int | float):
            raise ValueError("Dimension value must be a finite number")
        if not math.isfinite(self.value) or not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Dimension value must be within [0.0, 1.0], got {self.value}")
        if not isinstance(self.available, bool):
            raise ValueError("Dimension available must be a bool")
        for field_name in ("evidence_count", "evidence_total"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer, got {value!r}")
        if self.evidence_count > self.evidence_total:
            raise ValueError("Evidence coverage denominator cannot be below evidence count")
        if isinstance(self.evidence_references, str) or not isinstance(
            self.evidence_references,
            list | tuple,
        ):
            raise ValueError("Evidence references must be a sequence of strings")
        references = tuple(self.evidence_references)
        if any(not isinstance(reference, str) or not reference.strip() for reference in references):
            raise ValueError("Evidence references must contain non-empty strings")
        if len(set(references)) != len(references):
            raise ValueError("Evidence references must be unique")
        object.__setattr__(self, "evidence_references", references)
        if (
            not isinstance(self.normalization_version, str)
            or not self.normalization_version.strip()
        ):
            raise ValueError("Normalization version must be a non-empty string")
        if self.available:
            if self.evidence_count <= 0:
                raise ValueError("Available dimensions require positive evidence")
            if self.confidence is None or not isinstance(self.confidence, ConfidenceMetadata):
                raise ValueError("Available dimensions require confidence metadata")
            if len(references) != self.evidence_count:
                raise ValueError("Available dimensions require one reference per evidence item")
        elif (
            self.value != 0.0
            or self.evidence_count != 0
            or references
            or self.confidence is not None
        ):
            raise ValueError(
                "Unavailable dimensions must use zero value/count and no confidence or references"
            )

    @property
    def evidence_coverage(self) -> float:
        """Return covered evidence divided by the explicit denominator."""

        return self.evidence_count / self.evidence_total if self.evidence_total else 0.0

    @classmethod
    def unavailable(
        cls,
        dimension: VectorDimension,
        *,
        evidence_total: int = 0,
        normalization_version: str = NORMALIZATION_VERSION,
    ) -> DimensionScore:
        """Construct an explicitly unavailable dimension without a perfect score."""

        return cls(
            dimension=dimension,
            value=0.0,
            available=False,
            evidence_count=0,
            evidence_total=evidence_total,
            confidence=None,
            evidence_references=(),
            normalization_version=normalization_version,
        )


@dataclass(frozen=True)
class ReliabilityVector:
    """Exactly one independently reported score for each reliability dimension."""

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
        if not isinstance(self.schema_version, str) or not self.schema_version.strip():
            raise ValueError("Reliability vector schema_version must be non-empty")
        scores = self._scores()
        if any(not isinstance(score, DimensionScore) for score in scores):
            raise ValueError("Reliability vector fields must be DimensionScore instances")
        for expected, score in zip(VectorDimension, scores, strict=True):
            if score.dimension is not expected:
                raise ValueError(
                    f"Expected dimension {expected} for field but got {score.dimension}"
                )
            if score.normalization_version != self.schema_version:
                raise ValueError(
                    f"Dimension {expected} normalization version does not match vector schema"
                )
        identities = tuple(score.dimension for score in scores)
        if len(set(identities)) != len(VectorDimension):
            raise ValueError("Reliability vector dimension identities must be unique")

    def dimension(self, name: VectorDimension) -> DimensionScore:
        """Look up a dimension score by identity."""

        if not isinstance(name, VectorDimension):
            raise KeyError(f"Unknown reliability vector dimension: {name}")
        for score in self._scores():
            if score.dimension is name:
                return score
        raise KeyError(f"Unknown reliability vector dimension: {name}")

    def all_available(self) -> bool:
        """Return whether all eight dimensions have valid evidence."""

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
