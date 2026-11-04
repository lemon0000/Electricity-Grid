"""Bounded tests of D-tier action replay; never formal results.

The load-bearing property is that replaying a full-temporal method's own actions
reproduces its own records exactly. Without that, "method verdict vs. replayed
verdict" comparisons in D would be measuring the replay implementation, not the
simplification.
"""
from dataclasses import replace
from fractions import Fraction as Q
from pathlib import Path

import pytest

from src.staged_deliverability_development_v1 import (
    METHODS, HourInput, Parameters, execute, initialize, load_small_case,
)
from src.staged_deliverability_replay_v1 import (
    extract_actions, identity_check, replay_full_temporal, replay_step, verdicts,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "configs/staged_deliverability_small_case_v1.DRAFT.yaml"
SCENARIOS = [("on_time", "early"), ("on_time", "late"),
             ("delayed", "early"), ("delayed", "late")]


def _case(plan="on_time", clean="early", method="full_temporal"):
    params, observations = load_small_case(FIXTURE, plan, clean)
    return params, observations, execute(params, observations, method, f"{plan}:{clean}:{method}")


@pytest.mark.parametrize("plan,clean", SCENARIOS)
def test_replay_reproduces_full_temporal_records(plan, clean):
    """P4: a full-temporal method's own actions must replay to identical records."""
    params, observations, _ = _case(plan, clean)
    result = identity_check(params, observations, method="full_temporal", trajectory_id="p4")
    assert result["records_identical"] is True
    assert result["stop_identical"] is True
    assert result["verdict_identical"] is True
    assert result["hour_count"] == len(observations)


@pytest.mark.parametrize("plan,clean", SCENARIOS)
def test_extract_actions_matches_replayed_actions(plan, clean):
    """Replay must execute the given command, never re-plan it."""
    params, observations, native = _case(plan, clean)
    actions = extract_actions(native)
    assert len(actions) == len(native.records)
    replayed = replay_full_temporal(params, observations, actions, trajectory_id="fidelity")
    assert extract_actions(replayed) == actions


def test_replay_accepts_a_prefix_command():
    """A method that stopped early issues a prefix; replay mirrors that, honestly."""
    params, observations, native = _case()
    actions = extract_actions(native)[:-1]
    replayed = replay_full_temporal(params, observations, actions)
    assert len(extract_actions(replayed)) <= len(actions)


def test_replay_rejects_more_actions_than_observations():
    params, observations, native = _case()
    actions = list(extract_actions(native))
    actions.append((observations[-1].hour + 1, Q(0), Q(0)))
    with pytest.raises(ValueError, match="action count exceeds"):
        replay_full_temporal(params, observations, actions)


def test_replay_rejects_hour_mismatch():
    params, observations, native = _case()
    actions = list(extract_actions(native))
    hour, q, r = actions[2]
    actions[2] = (hour + 1, q, r)
    with pytest.raises(ValueError, match="action hour differs"):
        replay_full_temporal(params, observations, actions)


def test_instantaneous_defers_and_never_recovers():
    """The instantaneous method's own schedule leaves work deferred; replay exposes it."""
    params, observations, native = _case("on_time", "early", "instantaneous")
    assert all(record.recovery == 0 for record in native.records)
    replayed = replay_full_temporal(params, observations, extract_actions(native))
    verdict = verdicts(native, replayed)
    assert verdict["method_verdict"] is True
    assert verdict["label"] == "D1_false_pass"


def test_full_temporal_replay_agrees_on_pass():
    params, observations, native = _case("on_time", "early", "full_temporal")
    replayed = replay_full_temporal(params, observations, extract_actions(native))
    verdict = verdicts(native, replayed)
    assert verdict["method_verdict"] == verdict["replay_verdict"]
    assert verdict["label"] in {"D3_agree_pass", "D4_agree_fail"}


def test_fixed_headroom_replay_records_at_least_as_many_violations():
    """Constant headroom can only over-claim recovery room, never under-claim it."""
    for plan, clean in SCENARIOS:
        params, observations, native = _case(plan, clean, "fixed_headroom")
        replayed = replay_full_temporal(params, observations, extract_actions(native))
        native_v = sum(len(r.violations) for r in native.records)
        replay_v = sum(len(r.violations) for r in replayed.records)
        assert replay_v >= native_v


def _tight_params(**overrides):
    base = dict(capacity=Q(1, 5), alpha=Q(0), eta=Q(1), beta=Q(1), facility_factor=Q(1),
                auxiliary_mw=Q(0), fixed_headroom=Q(1), max_recovery=Q(1), max_debt=Q(2),
                max_call_energy=Q(2), call_ramp=Q(1), max_events=4, max_duration=4,
                minimum_rest=0)
    base.update(overrides)
    return Parameters(**base)


def _hour(hour, **overrides):
    base = dict(hour=hour, due=hour, workload=Q(1), flexible_fraction=Q(1),
                compute_capacity=Q(1), idle_mw=Q(0), clean_mwh=Q(0), supply_mw=Q(10),
                equipment_online=("m1",), grid_online=True)
    base.update(overrides)
    return HourInput(**base)


def test_recovery_above_real_headroom_is_a_violation():
    """A given r exceeding the full-temporal headroom fires recovery_headroom.

    Hour 1 has compute_capacity == workload, so full temporal offers no recovery room at
    all. A fixed-headroom plan that still commands recovery here is exactly the failure
    mode the constant-headroom simplification can hide.
    """
    params = _tight_params()
    observations = [_hour(0, workload=Q(1), compute_capacity=Q(1), due=1),
                    _hour(1, workload=Q(1), compute_capacity=Q(1), due=1)]
    state = initialize(params, "full_temporal", "headroom", first_hour=0)
    state, first = replay_step(params, state, observations[0], Q(1, 2), Q(0))
    assert not first
    state, violations = replay_step(params, state, observations[1], Q(0), Q(1, 2))
    assert "recovery_headroom" in violations


def test_stopped_state_refuses_further_replay():
    params = _tight_params(capacity=Q(1, 5), max_call_energy=Q(1, 5))
    observations = [_hour(0, workload=Q(1))]
    state = replay_full_temporal(params, observations, [(Q(1), Q(0))])
    assert state.stopped is True
    with pytest.raises(ValueError, match="stopped or nonconsecutive"):
        replay_step(params, state, _hour(1), Q(0), Q(0))


def test_verdicts_rejects_unknown_method():
    params, observations, native = _case()
    replayed = replay_full_temporal(params, observations, extract_actions(native))
    forged = replace(native, method="not_a_method")
    with pytest.raises(ValueError, match="unknown method"):
        verdicts(forged, replayed)


def test_verdicts_requires_full_temporal_replay_state():
    params, observations, native = _case("on_time", "early", "instantaneous")
    with pytest.raises(ValueError, match="full temporal"):
        verdicts(native, native)


@pytest.mark.parametrize("method", METHODS)
def test_every_method_yields_a_defined_label(method):
    params, observations, native = _case("delayed", "late", method)
    replayed = replay_full_temporal(params, observations, extract_actions(native))
    verdict = verdicts(native, replayed)
    assert verdict["label"] in {"D1_false_pass", "D2_false_reject",
                                "D3_agree_pass", "D4_agree_fail", "D5_undetermined"}
