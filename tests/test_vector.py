"""Unit tests for the Agent Reliability Vector."""

from __future__ import annotations

import pytest

from arise_x.trust.vector import DimensionScore, ReliabilityVector, VectorDimension


def _score(
    dimension: VectorDimension,
    value: float,
    *,
    available: bool = True,
    evidence_count: int = 10,
) -> DimensionScore:
    return DimensionScore(
        dimension=dimension,
        value=value,
        available=available,
        evidence_count=evidence_count,
    )


def _full_vector(**overrides: DimensionScore) -> ReliabilityVector:
    defaults = {
        "goal_success": _score(VectorDimension.GOAL_SUCCESS, 0.9),
        "resilience": _score(VectorDimension.RESILIENCE, 0.8),
        "behavioral_stability": _score(VectorDimension.BEHAVIORAL_STABILITY, 0.7),
        "recovery": _score(VectorDimension.RECOVERY, 0.85),
        "safety": _score(VectorDimension.SAFETY, 1.0),
        "efficiency": _score(VectorDimension.EFFICIENCY, 0.6),
        "cost": _score(VectorDimension.COST, 0.5),
        "autonomy": _score(VectorDimension.AUTONOMY, 0.75),
    }
    defaults.update(overrides)
    return ReliabilityVector(**defaults)


def test_given_plausible_values_when_construct_vector_then_all_available() -> None:
    # Arrange & Act
    vector = _full_vector()

    # Assert
    assert vector.all_available() is True


def test_given_known_dimension_when_dimension_lookup_then_returns_matching_score() -> None:
    # Arrange
    vector = _full_vector()

    # Act
    result = vector.dimension(VectorDimension.RESILIENCE)

    # Assert
    assert result.value == pytest.approx(0.8)


def test_given_unknown_dimension_when_dimension_lookup_then_raises_key_error() -> None:
    # Arrange
    vector = _full_vector()

    # Act & Assert
    with pytest.raises(KeyError):
        vector.dimension("not_a_real_dimension")  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [-0.01, 1.01, -1.0, 2.0])
def test_given_out_of_range_value_when_construct_score_then_raises_value_error(
    value: float,
) -> None:
    # Act & Assert
    with pytest.raises(ValueError, match=r"within \[0\.0, 1\.0\]"):
        DimensionScore(
            dimension=VectorDimension.GOAL_SUCCESS,
            value=value,
            available=True,
            evidence_count=5,
        )


def test_given_negative_evidence_count_when_construct_score_then_raises_value_error() -> None:
    # Act & Assert
    with pytest.raises(ValueError, match="non-negative"):
        DimensionScore(
            dimension=VectorDimension.GOAL_SUCCESS,
            value=0.5,
            available=True,
            evidence_count=-1,
        )


def test_given_mismatched_dimension_field_when_construct_vector_then_raises_value_error() -> None:
    # Act & Assert
    with pytest.raises(ValueError, match="Expected dimension"):
        _full_vector(goal_success=_score(VectorDimension.SAFETY, 0.9))


def test_given_unavailable_safety_when_construct_vector_then_not_treated_as_perfect() -> None:
    # Arrange
    unavailable_safety = DimensionScore.unavailable(VectorDimension.SAFETY)
    vector = _full_vector(safety=unavailable_safety)

    # Act
    safety = vector.dimension(VectorDimension.SAFETY)

    # Assert: a missing dimension must not silently count as a perfect 1.0 score.
    assert safety.available is False
    assert safety.value != 1.0
    assert vector.all_available() is False


def test_given_stability_without_baseline_when_marked_unavailable_then_not_available() -> None:
    # Arrange: single-run behavioral stability has no historical baseline yet.
    unavailable_stability = DimensionScore.unavailable(VectorDimension.BEHAVIORAL_STABILITY)

    # Act
    vector = _full_vector(behavioral_stability=unavailable_stability)

    # Assert
    assert vector.dimension(VectorDimension.BEHAVIORAL_STABILITY).available is False
    assert vector.all_available() is False


def test_given_two_vectors_when_one_dimension_changes_then_others_are_unaffected() -> None:
    # Arrange
    baseline = _full_vector()

    # Act
    changed = _full_vector(cost=_score(VectorDimension.COST, 0.1))

    # Assert: changing cost must not affect any other dimension's stored value.
    assert changed.cost.value != baseline.cost.value
    assert changed.goal_success.value == baseline.goal_success.value
    assert changed.resilience.value == baseline.resilience.value
    assert changed.behavioral_stability.value == baseline.behavioral_stability.value
    assert changed.recovery.value == baseline.recovery.value
    assert changed.safety.value == baseline.safety.value
    assert changed.efficiency.value == baseline.efficiency.value
    assert changed.autonomy.value == baseline.autonomy.value
