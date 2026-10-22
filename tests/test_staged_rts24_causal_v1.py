from dataclasses import replace
from fractions import Fraction as Q
import json

import pytest

from experiments.staged_rts24_causal_examples_v1 import analytic_fixture, analytic_hour, analytic_actual
from src import staged_rts24_development_v1 as c
from src.staged_rts24_causal_v1 import (
    initialize_execution, prepare_hour, propose_hour, accept_hour, execution_summary, reported_quantity,
)
from src.staged_rts24_causal_audit_v1 import audit_execution


@pytest.fixture(autouse=True)
def no_solver(monkeypatch):
    import pyomo.environ as pyo
    import src.grid.dc_opf as dc
    import src.grid.network_grid_need as need
    import src.grid.scopf as security

    def denied(*args, **kwargs): pytest.fail("solver requested by ordinary causal test")
    for module in (pyo, dc, need, security): monkeypatch.setattr(module, "SolverFactory", denied)


def step(fixture, state):
    prepared = prepare_hour(fixture, state, analytic_hour(fixture, state))
    proposal = propose_hour(state, prepared)
    excluded = any(code.startswith("network_projection_") or code == "connection_capacity" for code in proposal.violations)
    actual = None if excluded else analytic_actual(prepared, proposal)
    return accept_hour(fixture, state, prepared, proposal, actual)


def run(fixture, method="full_temporal", clean="early", count=5):
    state = initialize_execution(fixture, "on_time", clean, method)
    for _ in range(count):
        state = step(fixture, state)
        if state.stopped: break
    return state


def test_continuous_actual_closed_loop_preserves_work_event_and_stage_carry():
    fixture = analytic_fixture()
    state = run(fixture)
    assert not state.stopped and state.next_hour == 5
    assert [row["proposal"].deferred for row in state.records] == [0, 40, 0, 0, 0]
    assert [row["proposal"].recovery for row in state.records] == [0, 0, 40, 0, 0]
    assert [row["proposal"].power_mw for row in state.records] == [100, 60, 140, 100, 100]
    assert all(row["actual_accepted"] and row["proposal_ledger_applied"] for row in state.records)
    assert state.x_energy == state.call_energy == 40 and state.events == state.x_events == 1
    assert state.records[1]["prepared"].observation.commissioned is False
    assert state.records[2]["prepared"].observation.commissioned is True
    assert state.ledger.cohorts[0].remaining == state.ledger.cohorts[0].missed_at_deadline == 0
    summary = execution_summary(fixture, state)
    assert summary["method_conditions_satisfied"] and summary["full_replay_conditions_satisfied"]
    assert summary["fx_contract_status"] == "not_evaluated_by_actual_path_step"
    for task in summary["tasks"]: assert task["original"] == task["immediate"]+task["recovered"]+task["remaining"]


def test_three_methods_have_separate_continuous_ledgers_and_actual_acceptance():
    fixture = analytic_fixture()
    states = {method: run(fixture, method) for method in c.METHODS}
    assert len({s.trajectory_identity for s in states.values()}) == 3
    instant = execution_summary(fixture, states["instantaneous"])
    assert instant["method_conditions_satisfied"] is True
    assert instant["full_replay_conditions_satisfied"] is False and instant["observed_primary_deadline_miss"] == 40
    for method in ("instantaneous", "fixed_headroom"):
        state = states[method]
        assert all(row["proposal_ledger_applied"] and not row["actual_accepted"] for row in state.records)
        assert execution_summary(fixture, state)["actual_accepted_hours"] == 0
    assert execution_summary(fixture, states["full_temporal"])["actual_accepted_hours"] == 5


def test_fixed_recovery_false_positive_and_permanent_late_deadline_miss():
    fixture = analytic_fixture(late=True)
    fixed = run(fixture, "fixed_headroom", "late")
    full = run(fixture, "full_temporal", "late")
    approximate = execution_summary(fixture, fixed)
    actual = execution_summary(fixture, full)
    assert approximate["method_conditions_satisfied"] is True and approximate["full_replay_conditions_satisfied"] is False
    assert fixed.records[2]["proposal"].recovery == 40 and "hourly_cfe" in fixed.records[2]["violations"]
    assert actual["method_conditions_satisfied"] is False and actual["observed_primary_deadline_miss"] == 40
    assert full.records[4]["proposal"].recovery == 40 and full.ledger.debt == 0
    assert full.ledger.cohorts[0].missed_at_deadline == 40


def test_no_future_clean_path_information_can_change_current_actions():
    fixture = analytic_fixture(late=True)
    early = run(fixture, clean="early", count=2)
    late = run(fixture, clean="late", count=2)
    assert early.trajectory_identity != late.trajectory_identity
    for a, b in zip(early.records, late.records):
        assert a["prepared"].observation == b["prepared"].observation
        assert (a["proposal"].grid_deferred, a["proposal"].cfe_deferred, a["proposal"].recovery, a["proposal"].power_mw) == (
            b["proposal"].grid_deferred, b["proposal"].cfe_deferred, b["proposal"].recovery, b["proposal"].power_mw)
    a = step(fixture, early); b = step(fixture, late)
    assert a.records[-1]["proposal"].recovery == 40 and b.records[-1]["proposal"].recovery == 0


def test_positive_network_lower_endpoint_blocks_overdeferral_without_advancing_actual_ledger():
    fixture = analytic_fixture()
    business = json.loads(fixture.business_json)
    business["clean_paths"]["early"][1] = "0"
    fixture = replace(fixture, business_json=json.dumps(business), parameters=replace(fixture.parameters, capacity=Q(100), call_ramp=Q(100)),
                      source_identity="analytic_excess_cfe_deferral")
    state = run(fixture, count=2)
    assert state.stopped and state.next_hour == 1 and state.ledger.debt == 0
    row = state.records[-1]
    assert row["proposal"].power_mw == 0 and "network_projection_lower" in row["violations"]
    assert row["actual"] is None and not row["proposal_ledger_applied"] and not row["actual_accepted"]
    summary = execution_summary(fixture, state)
    assert summary["stopped"] and summary["attempted_through"] == 1 and summary["accepted_through"] == 0
    assert summary["unapplied_attempts"][0]["observation"].workload == 100
    assert summary["unapplied_attempts"][0]["proposal"].cfe_call_shortfall_mw == 40
    assert summary["physical_replay_violations"] == ((1, row["violations"]),)
    assert summary["method_relevant_violations"] == summary["physical_replay_violations"]
    assert summary["terminal_violations"] == row["violations"]


def test_actual_evidence_is_required_and_cannot_add_curtailment_or_change_power():
    fixture = analytic_fixture()
    state = initialize_execution(fixture, "on_time", "early", "full_temporal")
    prepared = prepare_hour(fixture, state, analytic_hour(fixture, state))
    proposal = propose_hour(state, prepared)
    with pytest.raises(ValueError, match="missing_actual"): accept_hour(fixture, state, prepared, proposal)
    actual = analytic_actual(prepared, proposal)
    with pytest.raises(ValueError, match="curtailment"):
        accept_hour(fixture, state, prepared, proposal, replace(actual, point=replace(actual.point, curtailment_mw=1.)))
    wrong = replace(actual, query=replace(actual.query, request=replace(actual.query.request, meter_min=Q(99), meter_max=Q(99))))
    with pytest.raises(ValueError, match="binding"): accept_hour(fixture, state, prepared, proposal, wrong)
    assert not state.records and state.next_hour == 0


def test_invalid_actual_point_preserves_last_accepted_full_state():
    fixture = analytic_fixture()
    state = run(fixture, count=1)
    prepared = prepare_hour(fixture, state, analytic_hour(fixture, state))
    proposal = propose_hour(state, prepared)
    actual = analytic_actual(prepared, proposal)
    bad = replace(actual, point=replace(actual.point, flows_mw=((0, 60.), (1, 60.), (2, 1.))))
    rejected = accept_hour(fixture, state, prepared, proposal, bad)
    assert rejected.stopped and rejected.ledger == state.ledger and rejected.x_energy == state.x_energy
    assert rejected.next_hour == state.next_hour and "actual_network_point" in rejected.records[-1]["violations"]


def test_prepared_or_proposal_tampering_is_rejected_at_acceptance():
    fixture = analytic_fixture()
    state = run(fixture, count=1)
    prepared = prepare_hour(fixture, state, analytic_hour(fixture, state))
    proposal = propose_hour(state, prepared)
    forged = replace(prepared, grid_request_mw=Q(0))
    with pytest.raises(ValueError, match="prepared"):
        accept_hour(fixture, state, forged, propose_hour(state, forged))
    with pytest.raises(ValueError, match="causal policy"):
        accept_hour(fixture, state, prepared, replace(proposal, recovery=Q(1)))


@pytest.mark.parametrize("role", ["raw", "lower", "upper"])
def test_missing_or_nonoptimal_prepolicy_evidence_cannot_be_used(role):
    fixture = analytic_fixture()
    state = run(fixture, count=1)
    evidence = analytic_hour(fixture, state)
    with pytest.raises(ValueError): prepare_hour(fixture, state, replace(evidence, **{role: None}))
    item = getattr(evidence, role)
    bad = replace(item, child_lp=replace(item.child_lp, point_sha="0"*64))
    with pytest.raises(ValueError): prepare_hour(fixture, state, replace(evidence, **{role: bad}))


def test_raw_request_stays_complete_and_X_energy_survives_stage_boundary():
    fixture = analytic_fixture()
    x = json.loads(fixture.x_envelope_json)
    x["max_energy_mwh"] = "39"
    tight = replace(fixture, x_envelope_json=json.dumps(x), source_identity="analytic_X_energy_39")
    state = run(tight, count=1)
    with pytest.raises(ValueError, match="raw_request_exceeds_legal_X"):
        prepare_hour(tight, state, analytic_hour(tight, state))
    complete = run(fixture, count=3)
    assert complete.x_energy == 40 and complete.call_energy == 40


def test_partial_horizon_is_censored_and_public_fixture_has_no_fabricated_parent():
    fixture = analytic_fixture()
    prefix = run(fixture, count=2)
    summary = execution_summary(fixture, prefix)
    assert summary["method_conditions_satisfied"] is None and summary["primary_right_censored"]
    public = c.load_fixture()
    state = initialize_execution(public, "on_time", "early", "full_temporal")
    with pytest.raises(ValueError, match="evidence"): prepare_hour(public, state, None)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1., True])
def test_reported_decision_numbers_are_finite_nonnegative_and_not_rounded(value):
    with pytest.raises(ValueError): reported_quantity(value)
    assert reported_quantity(.1) == Q(1, 10)
    assert reported_quantity(1.0000001) == Q("1.0000001")


@pytest.mark.parametrize("attribute,value", [("plan", "delayed"), ("clean_path", "late"), ("method", "fixed_headroom")])
def test_trajectory_labels_cannot_be_spliced_into_a_different_execution(attribute, value):
    fixture = analytic_fixture(late=True)
    state = run(fixture, count=1)
    changed = replace(state, **{attribute: value})
    with pytest.raises(ValueError, match="trajectory"):
        prepare_hour(fixture, changed, analytic_hour(fixture, changed))
    with pytest.raises(ValueError, match="trajectory"): execution_summary(fixture, changed)


def test_summary_cannot_relabel_an_incomplete_prefix_with_shorter_boundaries():
    fixture = analytic_fixture()
    state = run(fixture, count=2)
    summary = execution_summary(fixture, state)
    assert summary["coverage_complete"] is False and summary["method_conditions_satisfied"] is None
    with pytest.raises(ValueError, match="horizon"):
        execution_summary(replace(fixture, registration_end=1, observation_end=2), state)
    with pytest.raises(TypeError): execution_summary(state, 1, 2)


@pytest.mark.parametrize("field,value", [("call_energy", Q(0)), ("events", 0), ("x_energy", Q(0)), ("x_events", 0), ("rest", 99)])
def test_unreachable_carry_is_rejected_before_selecting_the_next_action(field, value):
    fixture = analytic_fixture()
    state = run(fixture, count=2)
    bad = replace(state, **{field: value})
    with pytest.raises(ValueError, match="carry"):
        prepare_hour(fixture, bad, analytic_hour(fixture, bad))


@pytest.mark.parametrize("method,clean", [("full_temporal", "early"), ("full_temporal", "late"),
                                         ("instantaneous", "late"), ("fixed_headroom", "late")])
def test_independent_policy_work_power_deadline_and_carry_audit(method, clean, monkeypatch):
    fixture = analytic_fixture(late=True)
    state = run(fixture, method, clean)
    import src.staged_rts24_causal_v1 as policy

    def forbidden(*args, **kwargs): pytest.fail("independent auditor called writer policy")
    for name in ("prepare_hour", "propose_hour", "accept_hour", "initialize_execution"):
        monkeypatch.setattr(policy, name, forbidden)
    result = audit_execution(fixture, state)
    assert result["record_consistency_satisfied"] and result["fixed_policy_selection_recomputed"]
    assert result["rows"] == 5
    assert result["method"] == method
    assert result["ledger_scope"] == ("accepted_static_dc_policy_execution" if method == "full_temporal" else "hypothetical_approximation")
    assert result["accepted_through"] == (4 if method == "full_temporal" else None)


def test_independent_audit_rejects_tampered_action_power_or_deadline_history():
    fixture = analytic_fixture(late=True)
    state = run(fixture, clean="late")
    row = dict(state.records[-1])
    row["proposal"] = replace(row["proposal"], power_mw=Q(99))
    with pytest.raises(ValueError, match="balance"):
        audit_execution(fixture, replace(state, records=state.records[:-1]+(row,)))
    ledger = replace(state.ledger, cohorts=tuple(replace(cohort, missed_at_deadline=Q(0)) for cohort in state.ledger.cohorts))
    with pytest.raises(ValueError, match="carry"):
        audit_execution(fixture, replace(state, ledger=ledger))
