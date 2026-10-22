from dataclasses import replace
from fractions import Fraction as Q
import json
from pathlib import Path
import subprocess
import sys

import pytest
import yaml

import src.staged_network_development_v1 as m
from src.staged_deliverability_development_v1 import assessment, plain, task_balances
from src.staged_network_audit_v1 import audit_network

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "configs/staged_deliverability_network_v1.DRAFT.yaml"


def case(plan="on_time", clean="early"):
    c = m.load_config(FIXTURE)
    p, obs = m.load_case(c, plan, clean)
    counts = {}
    s = m.execute_network(c, p, obs, plan, f"{plan}:{clean}:B2", counts=counts)
    return c, p, obs, s, counts


def audited(c, p, state):
    return audit_network(plain(c), plain(p), plain(state))


@pytest.mark.parametrize("online,normal,fault", [(False, Q(27,20), Q(5,8)), (True, Q(19,10), Q(9,10))])
def test_exact_network_bounds_and_actual_pypower_points(online, normal, fault):
    c = m.load_config(FIXTURE)
    data = c.after if online else c.before
    assert m.poi_capacity(data, c.poi_bus, (), c.angle_limit) == normal
    for outage in ((), (0,), (1,)):
        upper = normal if not outage else fault
        assert m.poi_capacity(data, c.poi_bus, outage, c.angle_limit) == upper
        point = m.dc_witness(data, c.poi_bus, upper, outage, c.angle_limit)
        assert point["numerical_conditions_satisfied"]
        assert point["residuals"]["balance_mw"] < 1e-12
        assert point["generation_mw"] == pytest.approx(float(upper + Q(1,10)))
        assert sum(point["branch_flows_mw"]) == pytest.approx(float(upper+Q(1,10)))
        assert not m.dc_witness(data, c.poi_bus, upper + Q(1,1000), outage, c.angle_limit)["numerical_conditions_satisfied"]


def test_preventive_actual_call_protects_f_but_cfe_can_use_less_f():
    c, p, obs, s, counts = case()
    r = next(r for r in s.records if r["hour"] == 1)
    proposal = r["proposal"]
    assert r["raw_grid_mw"] == Q(1,8) and r["active_x_mw"] == Q(3,20)
    assert proposal.grid_served == proposal.cfe_served == Q(1,10)
    assert r["reference_mw"] - p.slope * proposal.grid_served == Q(5,8) >= r["firm"]
    assert proposal.power_mw == Q(1,2) < r["firm"]
    assert r["actual_point"]["branch_flows_mw"] == pytest.approx((0., .6))
    assert r["committed"] and s.x_events == 1 and s.x_energy == Q(1,8)
    assert counts == dict(pypower_flows=70, business_steps=10, network_attempts=10)


def test_full_contract_network_witness_does_not_certify_business_backing():
    _, _, _, s, _ = case()
    pre = next(r for r in s.records if r["hour"] == 1)["contract"]
    post = next(r for r in s.records if r["hour"] == 2)["contract"]
    assert pre["normal"]["load"] == Q(4,5)
    assert pre["scenarios"][1]["required_grid_mw"] == Q(7,40)
    assert post["scenarios"][1]["required_grid_mw"] == Q(2,5)
    assert pre["network_conditions_satisfied"] and post["network_conditions_satisfied"]
    assert not pre["business_necessary"] and not post["business_necessary"]
    assert not post["enrolled_X_backing_necessary"]
    assert post["scenarios"][0]["business_necessary"]
    assert not post["scenarios"][1]["business_necessary"]
    assert post["scenarios"][1]["required_grid_mw"] > Q(1,4)
    assert not any(r["contract"]["aggregate_contract_release"] for r in s.records)


def test_early_late_recovery_and_original_deadline_history():
    _, _, _, early, _ = case()
    _, _, _, late, _ = case(clean="late")
    assert not early.stopped and not late.stopped
    assert assessment(early.business)["observed_primary_deadline_miss"] == 0
    assert assessment(late.business)["observed_primary_deadline_miss"] == Q(1,5)
    assert late.business.ledger.debt == 0
    assert next(r for r in late.records if r["hour"] == 4)["proposal"].recovery == Q(1,5)


def test_delayed_reference_admission_is_not_a_false_normal_X_call():
    _, p, obs, delayed, counts = case(plan="delayed")
    last = delayed.records[-1]
    assert delayed.stopped and last["hour"] == 3 and last["status"] == "reference_connection_shortfall"
    assert last["connection_shortfall_mw"] == Q(1,4)
    assert last["raw_grid_mw"] == 0 and last["physical_cap"] == Q(27,20)
    assert last["reference_point"]["numerical_conditions_satisfied"]
    assert last["proposal"] is None and not last["committed"]
    assert delayed.business.next_hour == 3 and delayed.business.ledger.debt == Q(1,5)
    assert assessment(delayed.business)["primary_right_censored"]
    assert counts == dict(pypower_flows=41, business_steps=5, network_attempts=6)


def test_actual_network_or_response_rejection_never_commits_candidate_ledger(monkeypatch):
    c = m.load_config(FIXTURE)
    p, inputs = m.load_case(c, "on_time", "early")
    before = m.execute_network(c, p, inputs[:3], "on_time", "atomic")
    original = m.dc_witness

    def fail_actual(data, poi, load, *args, **kw):
        result = original(data, poi, load, *args, **kw)
        if load == Q(1,2):
            result["numerical_conditions_satisfied"] = False
        return result

    monkeypatch.setattr(m, "dc_witness", fail_actual)
    after = m.advance_network(p, before, inputs[3])
    assert after.stopped and after.business == before.business
    assert not after.records[-1]["proposal"].ledger_applied
    assert after.x_energy == before.x_energy


def test_numerical_failure_is_unresolved_and_preserves_state(monkeypatch):
    c = m.load_config(FIXTURE)
    p, inputs = m.load_case(c, "on_time", "early")
    before = m.execute_network(c, p, inputs[:3], "on_time", "atomic")
    monkeypatch.setattr(m, "dcpf", lambda *a, **kw: (_ for _ in ()).throw(ArithmeticError("synthetic numerical failure")))
    after = m.execute_network(c, p, inputs[3:], "on_time", "atomic", state=before)
    assert after.records[-1]["status"] == "upstream_network_unresolved"
    assert after.business == before.business and after.stopped
    assert after.records[-1]["raw_grid_mw"] == Q(1,8)
    assert after.records[-1]["failure_stage"] == "contract_checks"
    audited(c,p,after)


def test_cfe_curtailment_is_separate_from_legal_X_response():
    c = replace(m.load_config(FIXTURE), max_x_call=Q(3,20))
    p, inputs = m.load_case(c,"on_time","early")
    state=m.execute_network(c,p,inputs,"on_time","separate-X")
    row=state.records[3]
    assert row["committed"] and row["x_call_mw"]==Q(1,8)
    assert row["reference_mw"]-row["proposal"].power_mw==Q(1,4)>c.max_x_call
    audited(c,p,state)


def test_entire_X_backing_is_separate_from_each_scenario_necessary_condition():
    c=replace(m.load_config(FIXTURE),rights_after=(Q(4,5),Q(3,10)))
    p,inputs=m.load_case(c,"on_time","early")
    state=m.execute_network(c,p,inputs,"on_time","whole-X")
    contract=state.records[4]["contract"]
    assert contract["network_conditions_satisfied"]
    assert all(s["business_necessary"] for s in contract["scenarios"])
    assert not contract["enrolled_X_backing_necessary"] and not contract["business_necessary"]
    assert contract["joint_temporal_support"]=="necessary_condition_failed"
    audited(c,p,state)
    saved=plain(state)
    saved["records"][4]["contract"]["joint_temporal_support"]="unresolved"
    with pytest.raises(AssertionError): audit_network(plain(c),plain(p),saved)


def test_actual_flow_exception_preserves_proposal_and_all_precommit_state(monkeypatch):
    c=m.load_config(FIXTURE)
    p,inputs=m.load_case(c,"on_time","early")
    before=m.execute_network(c,p,inputs[:3],"on_time","actual-failure")
    original=m.dc_witness

    def fail_actual(data,poi,load,*args,**kwargs):
        if load==Q(1,2): raise ArithmeticError("injected actual-flow failure")
        return original(data,poi,load,*args,**kwargs)

    monkeypatch.setattr(m,"dc_witness",fail_actual)
    after=m.advance_network(p,before,inputs[3])
    row=after.records[-1]
    assert row["status"]=="upstream_network_unresolved" and row["failure_stage"]=="actual_flow"
    assert row["contract"]["status"]=="evaluated" and row["raw_grid_mw"]==Q(1,8)
    assert row["proposal"].grid_served==Q(1,10) and not row["proposal"].ledger_applied
    assert row["reference_point"] is not None and row["actual_point"] is None
    assert replace(after,records=before.records,stopped=False)==before
    audited(c,p,after)


def test_partial_contract_audit_rejects_tampering(monkeypatch):
    c=m.load_config(FIXTURE)
    p,inputs=m.load_case(c,"on_time","early")
    before=m.execute_network(c,p,inputs[:3],"on_time","partial-failure")
    original=m.dc_witness

    def fail_firm(data,poi,load,*args,**kwargs):
        if load==Q(3,5): raise ArithmeticError("injected firm-flow failure")
        return original(data,poi,load,*args,**kwargs)

    monkeypatch.setattr(m,"dc_witness",fail_firm)
    after=m.advance_network(p,before,inputs[3])
    audited(c,p,after)
    original_state=plain(after)
    changes=(lambda s:s.update(counterfactual_workload="99"),
             lambda s:s.update(business_necessary=not s["business_necessary"]),
             lambda s:s.update(extra="unregistered"))
    for change in changes:
        saved=json.loads(json.dumps(original_state))
        change(saved["records"][-1]["contract"]["scenarios"][-1])
        with pytest.raises(AssertionError): audit_network(plain(c),plain(p),saved)
    saved=json.loads(json.dumps(original_state))
    saved["records"][-1]["contract"]["scenarios"].pop()
    with pytest.raises(AssertionError): audit_network(plain(c),plain(p),saved)


def test_business_failure_propagates_without_being_mislabeled_as_network(monkeypatch):
    c=m.load_config(FIXTURE)
    p,inputs=m.load_case(c,"on_time","early")
    before=m.initialize_network(c,p,"on_time","business-failure")
    monkeypatch.setattr(m,"advance",lambda *a,**kw: (_ for _ in ()).throw(RuntimeError("business failure")))
    with pytest.raises(RuntimeError,match="business failure"):
        m.advance_network(p,before,inputs[0])
    assert not before.records and not before.stopped


def test_stopped_checkpoint_binds_exact_consumed_prefix(tmp_path):
    c,p,inputs,state,_=case("delayed")
    path=tmp_path/"stopped.json"
    m.save_network_checkpoint(path,state)
    identity="delayed:early:B2"
    assert m.read_network_checkpoint(path,c,p,inputs[:6],"delayed",identity)==state
    with pytest.raises(ValueError,match="unconsumed hours"):
        m.read_network_checkpoint(path,c,p,inputs[:7],"delayed",identity)


@pytest.mark.parametrize("plan,clean",[("on_time","early"),("on_time","late"),("delayed","early")])
def test_independent_audit_covers_full_state_and_rejects_carry_tampering(plan,clean):
    c,p,inputs,state,_=case(plan,clean)
    report=audited(c,p,state)
    assert report["accepted_business_hours"]==len(state.business.records)
    for field,value in (("x_energy","0"),("previous_generation","99"),("x_events",True)):
        saved=plain(state); saved[field]=value
        with pytest.raises(AssertionError): audit_network(plain(c),plain(p),saved)
    saved=plain(state); saved["business"]["ledger"]["cohorts"][0]["remaining"]="99"
    with pytest.raises(AssertionError): audit_network(plain(c),plain(p),saved)


@pytest.mark.parametrize("field,value,status",[("hourly_ramp",Q(1,10),"X_or_source_response_rejected"),
                                               ("max_x_events",0,"request_exceeds_legal_X"),
                                               ("max_x_energy",Q(1,10),"request_exceeds_legal_X")])
def test_source_and_X_rejections_are_auditable_without_state_commit(field,value,status):
    c=replace(m.load_config(FIXTURE),**{field:value})
    p,inputs=m.load_case(c,"on_time","early")
    before=m.execute_network(c,p,inputs[:3],"on_time","response-reject")
    after=m.advance_network(p,before,inputs[3])
    assert after.records[-1]["status"]==status
    assert replace(after,records=before.records,stopped=False)==before
    audited(c,p,after)


def test_independent_audit_is_active_under_python_optimized_mode():
    script="from src.staged_network_audit_v1 import check; check(False, 'audit-active')"
    run=subprocess.run([sys.executable,"-B","-O","-c",script],cwd=ROOT,capture_output=True,text=True,timeout=15)
    assert run.returncode!=0 and "AssertionError: audit-active" in run.stderr


def test_nonconsecutive_bus_ids_and_islanding_are_handled_explicitly():
    c = m.load_config(FIXTURE)
    d = c.before
    d = replace(d, buses=(replace(d.buses[0], index=13), replace(d.buses[1], index=47)),
                reference_bus=13, generators=(replace(d.generators[0], bus=13),),
                branches=tuple(replace(b, from_bus=13, to_bus=47) for b in d.branches))
    assert m.dc_witness(d, 47, Q(3,4))["branch_flows_mw"] == pytest.approx((.425,.425))
    with pytest.raises(ValueError, match="islanded"):
        m.dc_witness(d, 47, Q(1,2), (0,1))
    with pytest.raises(ValueError, match="shift"):
        m.dc_witness(replace(d, branches=(replace(d.branches[0], phase_shift_rad=.1),d.branches[1])),47,Q(1,2))


@pytest.mark.parametrize("plan,clean", [("on_time","early"),("on_time","late"),("delayed","early")])
def test_network_checkpoint_replay_and_suffix_equal_continuous(tmp_path, plan, clean):
    c, p, inputs, continuous, _ = case(plan, clean)
    identity = f"{plan}:{clean}:B2"
    prefix = m.execute_network(c, p, inputs[:4], plan, identity)
    path = tmp_path / "checkpoint.json"
    m.save_network_checkpoint(path, prefix)
    reopened = m.read_network_checkpoint(path,c,p,inputs[:4],plan,identity)
    assert m.execute_network(c,p,inputs[4:],plan,identity,state=reopened) == continuous
    saved=json.loads(path.read_text())
    saved["state"]["x_energy"]="0"
    path.write_text(json.dumps(saved),encoding="utf-8")
    with pytest.raises(ValueError,match="replay differs"):
        m.read_network_checkpoint(path,c,p,inputs[:4],plan,identity)


def test_future_network_delays_do_not_change_current_actions():
    c,p,inputs,a,_ = case()
    _,_,late,b,_=case(plan="delayed")
    assert [r["proposal"] for r in a.records[:4]] == [r["proposal"] for r in b.records[:4]]


@pytest.mark.parametrize("field,value", [("background_mw",True),("line_rating_before_mw",.725),("project_lead",True)])
def test_network_fixture_rejects_ambiguous_values(tmp_path,field,value):
    raw=yaml.safe_load(FIXTURE.read_text())
    raw["network"][field]=value
    path=tmp_path/'invalid.yaml'; path.write_text(yaml.safe_dump(raw),encoding="utf-8")
    with pytest.raises(ValueError): m.load_config(path)
