from __future__ import annotations

import pytest

from src.evaluation.rq2_identification_bounds import (
    IDENTIFIED_R1,
    IDENTIFIED_R2,
    IDENTIFIED_R3,
    PARTIALLY_IDENTIFIED,
    UNRESOLVED,
    IdentificationInputs,
    Interval,
    classify_identification_bounds,
)


def _inputs(**overrides) -> IdentificationInputs:
    values = {
        "delta_failure_probability": Interval(0.0, 0.0),
        "delta_expected_shortfall": Interval(0.0, 0.0),
        "flexibility_underprovisioning": Interval(0.0, 0.0),
        "correct_failure_probability": Interval(0.0, 0.0),
        "correct_expected_shortfall": Interval(0.0, 0.0),
        "all_optimization_resolved": True,
    }
    values.update(overrides)
    return IdentificationInputs(**values)


def test_identifies_no_conflict_only_when_equivalence_and_success_are_robust():
    result = classify_identification_bounds(_inputs())

    assert result.classification == IDENTIFIED_R1
    assert result.identified


def test_identifies_double_commitment_only_with_uniform_dominance():
    result = classify_identification_bounds(
        _inputs(
            delta_expected_shortfall=Interval(2.0, 8.0),
            flexibility_underprovisioning=Interval(0.0, 4.0),
        )
    )

    assert result.classification == IDENTIFIED_R2
    assert result.compatible_regions == ("R2_double_commitment_risk",)


def test_recovery_debt_difference_prevents_false_no_conflict_classification():
    result = classify_identification_bounds(
        _inputs(delta_peak_recovery_debt=Interval(0.1, 0.4))
    )

    assert result.classification == IDENTIFIED_R2


def test_identifies_common_insufficiency_under_robust_equivalent_failure():
    result = classify_identification_bounds(
        _inputs(
            correct_failure_probability=Interval(0.4, 1.0),
            correct_expected_shortfall=Interval(5.0, 20.0),
        )
    )

    assert result.classification == IDENTIFIED_R3


def test_sign_crossing_interval_is_partially_identified():
    result = classify_identification_bounds(
        _inputs(
            delta_expected_shortfall=Interval(-2.0, 4.0),
            correct_failure_probability=Interval(0.0, 0.5),
        )
    )

    assert result.classification == PARTIALLY_IDENTIFIED
    assert not result.identified
    assert "R1_no_conflict" in result.compatible_regions
    assert "R2_double_commitment_risk" in result.compatible_regions
    assert "R3_common_insufficiency" in result.compatible_regions


def test_negative_only_difference_excludes_zero_difference_regions():
    result = classify_identification_bounds(
        _inputs(
            delta_peak_recovery_debt=Interval(-0.4, -0.1),
            correct_failure_probability=Interval(0.0, 0.5),
        )
    )

    assert result.classification == PARTIALLY_IDENTIFIED
    assert "R1_no_conflict" not in result.compatible_regions
    assert "R2_double_commitment_risk" not in result.compatible_regions
    assert "R3_common_insufficiency" not in result.compatible_regions


def test_unresolved_optimization_never_becomes_a_scientific_region():
    result = classify_identification_bounds(
        _inputs(all_optimization_resolved=False)
    )

    assert result.classification == UNRESOLVED
    assert not result.compatible_regions


def test_invalid_interval_fails_closed():
    with pytest.raises(ValueError, match="lower bound exceeds"):
        classify_identification_bounds(
            _inputs(delta_expected_shortfall=Interval(2.0, 1.0))
        )
