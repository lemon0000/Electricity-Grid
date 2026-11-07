"""Bounded tests of the replay successor; never formal results.

v2 fixes exactly one R3 review finding (r3_review.md, point one): a supplied q larger
than the hour's total service request used to be decomposed into
`grid_served + cfe_served < q`, produce two zero shortfalls, and be booked in full as
`incurred=q`. It is now rejected. Every q that `extract_actions()` can produce is at
most `grid/slope + green/slope`, so the guard must be unreachable on the D grid and the
successor must reproduce attempt_01's rows exactly.
"""
from fractions import Fraction as Q
import json
from pathlib import Path

import pytest

from src.staged_deliverability_development_v1 import (
    HourInput, Parameters, execute, initialize,
)
from src.staged_deliverability_replay_v1 import (
    extract_actions as extract_actions_v1, replay_full_temporal as replay_v1,
)
from src.staged_deliverability_replay_v2 import (
    extract_actions, replay_full_temporal, replay_step,
)
from src.staged_deliverability_d_grid_v2 import (
    GRID_BUSINESS, GRID_PATHS, CLEAN_PATHS, evaluate_cell, load_grid_case,
)
from src.staged_deliverability_development_v1 import ZERO, power_mapping

ROOT = Path(__file__).resolve().parents[1]
D_FIXTURE = ROOT / "configs/staged_deliverability_d_v1.DRAFT.yaml"


def _params(**overrides):
    base = dict(capacity=Q(1, 5), alpha=Q(1), eta=Q(1), beta=Q(1), facility_factor=Q(1),
                auxiliary_mw=Q(0), fixed_headroom=Q(1), max_recovery=Q(1), max_debt=Q(10),
                max_call_energy=Q(10), call_ramp=Q(1), max_events=4, max_duration=4,
                minimum_rest=0)
    base.update(overrides)
    return Parameters(**base)


def _hour(hour, **overrides):
    base = dict(hour=hour, due=hour, workload=Q(1), flexible_fraction=Q(1),
                compute_capacity=Q(2), idle_mw=Q(0), clean_mwh=Q(0), supply_mw=Q(10),
                equipment_online=("m1",), grid_online=True)
    base.update(overrides)
    return HourInput(**base)


def test_command_above_total_request_is_rejected():
    """q = 5 against grid + green = 1 is an illegal callback, not a shortfall."""
    params = _params()
    observation = _hour(0, workload=Q(1), clean_mwh=Q(0), supply_mw=Q(10))
    _, _, reference = power_mapping(params, observation)
    grid = max(reference - observation.supply_mw, ZERO)
    green = max(reference - observation.clean_mwh / params.alpha, ZERO)
    assert (grid, green) == (ZERO, Q(1))

    state = initialize(params, "full_temporal", "guard", first_hour=0)
    with pytest.raises(ValueError, match="total service request"):
        replay_step(params, state, observation, Q(5), Q(0))
    # The boundary itself stays legal.
    state, violations = replay_step(params, state, observation, Q(1), Q(0))
    assert violations == ()


def test_v1_swallowed_the_same_command():
    """Pin the defect the successor fixes, so the two semantics never drift back."""
    params = _params()
    observation = _hour(0, workload=Q(1), clean_mwh=Q(0), supply_mw=Q(10))
    v1_state = replay_v1(params, (observation,), [(Q(5), Q(0))])
    record = v1_state.records[-1]
    assert record.deferred == Q(1) < Q(5)
    assert (record.grid_shortfall_mw, record.cfe_call_shortfall_mw) == (ZERO, ZERO)


@pytest.mark.parametrize("business", GRID_BUSINESS)
@pytest.mark.parametrize("plan", GRID_PATHS)
@pytest.mark.parametrize("clean", CLEAN_PATHS)
def test_guard_is_unreachable_on_the_grid(business, plan, clean):
    """Every extracted q is at most the total request, so replay never trips the guard."""
    params, observations = load_grid_case(D_FIXTURE, business, plan, clean)
    for method in ("instantaneous", "fixed_headroom", "full_temporal"):
        native = execute(params, observations, method, f"{business}:{plan}:{clean}:{method}")
        for (hour, q, r) in extract_actions(native):
            observation = [o for o in observations if o.hour == hour][0]
            _, _, reference = power_mapping(params, observation)
            grid = max(reference - observation.supply_mw, ZERO)
            green = (max(reference - observation.clean_mwh / params.alpha, ZERO)
                     if params.alpha else ZERO)
            assert q <= grid / params.slope + green / params.slope


def test_v2_reproduces_every_attempt_01_row():
    """The successor must leave the recorded D grid byte-identical, cell by cell."""
    report_path = (ROOT / "results/tables/staged_deliverability_d_v1_non_authoritative"
                   / "attempt_01/report.json")
    recorded = {r["trajectory"]: r
                for r in json.loads(report_path.read_text(encoding="utf-8"))["rows"]}
    fields = ("business", "plan", "clean", "method", "label", "strategy_label",
              "method_verdict", "replay_verdict", "reference_verdict", "hours",
              "replay_stopped", "replay_observed_through",
              "replay_violation_count", "native_violation_count")
    for business, plan, clean in [(b, p, c) for b in GRID_BUSINESS
                                  for p in GRID_PATHS for c in CLEAN_PATHS]:
        for method in ("instantaneous", "fixed_headroom", "full_temporal"):
            row = evaluate_cell(D_FIXTURE, business, plan, clean, method)
            old = recorded[row["trajectory"]]
            for field in fields:
                assert row[field] == old[field], (row["trajectory"], field)
            params, observations = load_grid_case(D_FIXTURE, business, plan, clean)
            native = execute(params, observations, method, row["trajectory"])
            actions = list(extract_actions(native))
            assert actions == list(extract_actions_v1(native))
            old_state = replay_v1(params, observations, actions, trajectory_id="v1")
            new_state = replay_full_temporal(params, observations, actions,
                                             trajectory_id="v2")
            assert old_state.records == new_state.records
            assert old_state.stopped == new_state.stopped
