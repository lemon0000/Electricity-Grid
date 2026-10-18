from __future__ import annotations

import pytest

from src.models.robust_shared_flexibility import (
    instantaneous_commitment_bound,
    recovery_debt_bound,
)


def test_instantaneous_gap_is_exact_for_overlapping_calls():
    result = instantaneous_commitment_bound((4.0, 0.0), (3.0, 0.0))

    assert result.shared_required_capacity == 7.0
    assert result.separately_committed_capacity == 4.0
    assert result.duplicate_commitment_gap == 3.0
    assert result.gap_upper_bound == 3.0
    assert result.peak_overlap_witness_index == 0


def test_nonoverlapping_peaks_have_no_instantaneous_gap():
    result = instantaneous_commitment_bound((4.0, 0.0), (0.0, 3.0))

    assert result.shared_required_capacity == 4.0
    assert result.separately_committed_capacity == 4.0
    assert result.duplicate_commitment_gap == 0.0


def test_gap_never_exceeds_smaller_individual_peak():
    result = instantaneous_commitment_bound(
        (2.0, 5.0, 1.0),
        (4.0, 3.0, 7.0),
    )

    assert 0.0 <= result.duplicate_commitment_gap <= result.gap_upper_bound


def test_recovery_bound_greedily_minimizes_prefix_debt():
    result = recovery_debt_bound(
        (4.0, 0.0, 0.0),
        (0.0, 1.0, 2.0),
        time_step_hours=1.0,
        recovery_efficiency=1.0,
        maximum_debt=3.5,
        terminal_debt_limit=0.5,
    )

    assert result.minimum_peak_debt == 4.0
    assert result.terminal_debt_lower_bound == 1.0
    assert result.infeasible_under_debt_limit
    assert result.infeasible_under_terminal_limit


def test_analytic_inputs_fail_closed():
    with pytest.raises(ValueError, match="equal length"):
        instantaneous_commitment_bound((1.0,), (1.0, 2.0))
    with pytest.raises(ValueError, match="finite and nonnegative"):
        instantaneous_commitment_bound((float("nan"),), (1.0,))
