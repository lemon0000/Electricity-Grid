"""Tests for the RQ2 three-region classification contract."""

from __future__ import annotations

from dataclasses import replace

from src.evaluation.rq2_phase_regions import (
    REGION_COMMON_INSUFFICIENCY,
    REGION_DOUBLE_COMMITMENT,
    REGION_MIXED,
    REGION_NO_CONFLICT,
    REGION_UNRESOLVED,
    PhaseRegionInputs,
    classify_phase_region,
)


def _inputs(**overrides) -> PhaseRegionInputs:
    values = {
        "correct_training_feasible": True,
        "b6_training_feasible": True,
        "correct_training_unresolved": False,
        "b6_training_unresolved": False,
        "h2_evaluated": True,
        "correct_failure_probability": 0.0,
        "b6_failure_probability": 0.0,
        "correct_expected_shortfall_mwh": 0.0,
        "b6_expected_shortfall_mwh": 0.0,
        "correct_committed_flexibility_mw": 40.0,
        "b6_committed_flexibility_mw": 40.0,
    }
    values.update(overrides)
    return PhaseRegionInputs(**values)


def test_no_conflict_requires_equivalent_success():
    result = classify_phase_region(_inputs())

    assert result.region == REGION_NO_CONFLICT
    assert result.scientific_region


def test_double_commitment_accepts_capacity_or_service_dominance():
    capacity = classify_phase_region(
        _inputs(
            correct_committed_flexibility_mw=76.8,
            b6_committed_flexibility_mw=40.0,
        )
    )
    service = classify_phase_region(
        _inputs(
            correct_failure_probability=0.0,
            b6_failure_probability=0.2,
            correct_expected_shortfall_mwh=0.0,
            b6_expected_shortfall_mwh=10.0,
        )
    )

    assert capacity.region == REGION_DOUBLE_COMMITMENT
    assert service.region == REGION_DOUBLE_COMMITMENT


def test_common_insufficiency_requires_equivalent_policy_failure():
    result = classify_phase_region(
        _inputs(
            correct_failure_probability=1.0,
            b6_failure_probability=1.0,
            correct_expected_shortfall_mwh=400.0,
            b6_expected_shortfall_mwh=400.0,
        )
    )
    planning = classify_phase_region(
        _inputs(
            correct_training_feasible=False,
            b6_training_feasible=False,
            h2_evaluated=False,
            correct_committed_flexibility_mw=None,
            b6_committed_flexibility_mw=None,
        )
    )

    assert result.region == REGION_COMMON_INSUFFICIENCY
    assert planning.region == REGION_COMMON_INSUFFICIENCY


def test_capacity_gap_takes_cell_out_of_common_insufficiency():
    result = classify_phase_region(
        _inputs(
            correct_failure_probability=1.0,
            b6_failure_probability=1.0,
            correct_expected_shortfall_mwh=100.0,
            b6_expected_shortfall_mwh=100.0,
            correct_committed_flexibility_mw=80.0,
            b6_committed_flexibility_mw=40.0,
        )
    )

    assert result.region == REGION_DOUBLE_COMMITMENT
    assert result.reason == ("b6_weakly_dominated_with_strict_capacity_or_service_loss")


def test_unresolved_and_mixed_are_not_forced_into_three_regions():
    unresolved = classify_phase_region(
        replace(_inputs(), correct_training_unresolved=True)
    )
    mixed = classify_phase_region(
        _inputs(
            correct_failure_probability=0.5,
            b6_failure_probability=0.0,
        )
    )

    assert unresolved.region == REGION_UNRESOLVED
    assert not unresolved.scientific_region
    assert mixed.region == REGION_MIXED
    assert not mixed.scientific_region
