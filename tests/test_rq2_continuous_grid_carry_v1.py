"""Synthetic analytical checks for draft cross-chunk generator chronology."""

from dataclasses import FrozenInstanceError, replace

import pytest

from src.rq2_joint_deliverability_boundary_v1.grid_carry import (
    GridCarry, GridHour, GridIdentity, UnitLimits, UnitPoint,
    advance_grid_carry, replay_grid_chunk,
)


IDENTITY = GridIdentity("training", "synthetic-grid", 7, "1" * 64)
LIMIT = UnitLimits("G1", 10., 100., 20., 3., 2.)


def initial(committed=True, power=30., age=1):
    return GridCarry(IDENTITY, 23, (LIMIT,), (UnitPoint("G1", committed, power),),
                     (age,), "mechanism_assumption")


def row(hour, committed=True, power=30.):
    return GridHour(IDENTITY, hour, (UnitPoint("G1", committed, power),))


def test_whole_and_chunked_history_agree_with_hand_computed_dwell():
    rows = (row(24, power=50.), row(25, power=30.), row(26, False, 0.),
            row(27, False, 0.), row(28, True, 70.))
    state = initial()
    expected_ages = (2, 3, 1, 2, 1)
    for hour, expected in zip(rows, expected_ages, strict=True):
        state = advance_grid_carry(state, hour)
        assert state.elapsed_state_hours == (expected,)
    for split in range(len(rows) + 1):
        prefix = replay_grid_chunk(initial(), rows[:split])
        assert replay_grid_chunk(prefix, rows[split:]) == state
    assert state == replay_grid_chunk(initial(), rows)
    assert state.limits == initial().limits and state.identity == IDENTITY


@pytest.mark.parametrize("before,after", [
    (initial(), row(24, False, 0.)),
    (initial(False, 0., 1), row(24, True, 30.)),
])
def test_midnight_does_not_reset_or_forgive_residual_minimum_dwell(before, after):
    with pytest.raises(ValueError, match="carried minimum dwell"):
        advance_grid_carry(before, after)
    assert before.source_hour == 23 and before.elapsed_state_hours == (1,)


@pytest.mark.parametrize("power", [50.01, 9.99])
def test_cross_chunk_ramp_and_power_bounds_are_checked(power):
    with pytest.raises(ValueError, match="ramp|power bound"):
        advance_grid_carry(initial(), row(24, power=power))


def test_downward_ramp_and_fractional_minimum_hours():
    with pytest.raises(ValueError, match="ramp"):
        advance_grid_carry(initial(power=80.), row(24, power=50.))
    before = replace(initial(age=2), limits=(replace(LIMIT, minimum_up_hours=2.1),))
    with pytest.raises(ValueError, match="minimum dwell"):
        advance_grid_carry(before, row(24, False, 0.))
    advanced = advance_grid_carry(before, row(24))
    assert advance_grid_carry(advanced, row(25, False, 0.)).elapsed_state_hours == (1,)


def test_startup_shutdown_allowances_do_not_remove_dwell_requirements():
    started = advance_grid_carry(initial(False, 0., 2), row(24, True, 100.))
    assert started.elapsed_state_hours == (1,)
    with pytest.raises(ValueError, match="minimum dwell"):
        advance_grid_carry(started, row(25, False, 0.))
    assert advance_grid_carry(initial(power=100., age=3), row(24, False, 0.)).points == row(24, False, 0.).points


@pytest.mark.parametrize("field,value", [
    ("split", "holdout"), ("trajectory_id", "another"),
    ("outage_seed", 8), ("source_sha256", "2" * 64),
])
def test_cross_chunk_identity_change_is_rejected(field, value):
    hour = replace(row(24), identity=replace(IDENTITY, **{field: value}))
    with pytest.raises(ValueError, match="identity changed"):
        advance_grid_carry(initial(), hour)


@pytest.mark.parametrize("hour", [23, 25])
def test_source_hour_must_be_exact_successor(hour):
    with pytest.raises(ValueError, match="source-hour gap"):
        advance_grid_carry(initial(), row(hour))


def test_multiunit_inventory_and_independent_histories():
    before = GridCarry(IDENTITY, 23, (LIMIT, replace(LIMIT, uid="G2")),
                      (UnitPoint("G1", True, 30.), UnitPoint("G2", False, 0.)),
                      (3, 2), "mechanism_assumption")
    hour = GridHour(IDENTITY, 24, (UnitPoint("G1", False, 0.), UnitPoint("G2", True, 30.)))
    assert advance_grid_carry(before, hour).elapsed_state_hours == (1, 1)
    with pytest.raises(ValueError, match="inventory changed"):
        advance_grid_carry(before, row(24))
    with pytest.raises(ValueError, match="unique sorted"):
        GridHour(IDENTITY, 24, tuple(reversed(hour.points)))


@pytest.mark.parametrize("mutation", [
    {"elapsed_state_hours": ()}, {"elapsed_state_hours": (True,)},
    {"elapsed_state_hours": (-1,)}, {"elapsed_state_hours": (1.5,)},
    {"initial_history_role": "observed_without_evidence"},
    {"points": (UnitPoint("G1", False, 10.),)},
])
def test_invalid_initial_history_fails_before_future_recovery(mutation):
    with pytest.raises(ValueError):
        replace(initial(), **mutation)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1., True])
def test_nonphysical_unit_parameters_are_rejected(bad):
    with pytest.raises(ValueError, match="finite nonnegative"):
        replace(LIMIT, ramp_mw_per_hour=bad)
    with pytest.raises(ValueError, match="finite nonnegative"):
        UnitPoint("G1", True, bad)


def test_limits_are_immutable_and_chunk_has_no_reset_or_clock_advance():
    before = initial()
    assert replay_grid_chunk(before, ()) is before
    with pytest.raises(FrozenInstanceError):
        before.limits = (replace(LIMIT, ramp_mw_per_hour=1000.),)
    with pytest.raises(ValueError, match="immutable chunk"):
        replay_grid_chunk(before, [row(24)])
