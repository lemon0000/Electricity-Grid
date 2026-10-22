from dataclasses import replace
from fractions import Fraction as Q
import json
from pathlib import Path
import subprocess
import sys

import pytest

import src.staged_termination_development_v1 as m
import src.staged_network_development_v1 as network
from src.staged_termination_audit_v1 import audit_termination

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/"configs/staged_deliverability_network_v1.DRAFT.yaml"


def setup(tmp_path,plan="on_time",clean="early",**boundaries):
    c=network.load_config(FIXTURE)
    p,obs=network.load_case(c,plan,clean)
    identity=f"{plan}:{clean}:B3"
    s=m.create_session(tmp_path/"store",c,p,plan,identity,**boundaries)
    return c,p,obs,identity,s


def advance(s,observations):
    for o in observations:
        s=m.commit_hour(s,o)
        if s.reason: break
    return s


def fault_at(phase,target="step_0004.json"):
    def hook(here,path):
        if here==phase and path.name==target: raise OSError("injected "+phase)
    return hook


@pytest.mark.parametrize("plan,clean,reason,accepted,miss",[
    ("on_time","early","observation_complete",10,Q(0)),
    ("on_time","late","observation_complete",10,Q(1,5)),
    ("delayed","early","policy_or_admission_rejected",5,Q(0))])
def test_terminal_outcomes_and_exact_fresh_replay(tmp_path,plan,clean,reason,accepted,miss):
    c,p,obs,identity,s=setup(tmp_path,plan,clean)
    s=m.finish(advance(s,obs))
    report=m.summary(s); audit=audit_termination(report)
    assert report["termination_reason"]==reason and audit["accepted_hours"]==accepted
    assert audit["known_primary_miss"]==miss
    attempt=obs[accepted] if plan=="delayed" else None
    reopened=m.reopen(s.root,c,p,obs[:accepted],plan,identity,attempt_observation=attempt)
    assert m.summary(reopened)==report
    if plan=="delayed":
        assert report["last_accepted_hour"]==2 and report["attempted_hour"]==3
        assert report["pending_arrival"]["status"]=="observed_pending_unaccepted"
        assert report["primary_remaining_debt"]=="1/5" and len(report["all_arrived_tasks"])==5
        assert report["all_arrived_tasks"][3]["status"]=="right_censored_before_deadline"


def test_missing_followup_never_creates_zero_input_or_future_tasks(tmp_path):
    c,p,obs,identity,s=setup(tmp_path)
    s=m.finish(advance(s,obs[:4])); r=m.summary(s)
    assert r["termination_reason"]=="missing_input" and r["next_required_hour"]==2
    assert r["pending_arrival"]==dict(status="not_observed",observation=None)
    assert r["primary_remaining_debt"]=="1/5" and len(r["all_arrived_tasks"])==4
    audit_termination(r)
    assert m.summary(m.reopen(s.root,c,p,obs[:4],"on_time",identity))==r


def test_skipped_hour_stops_before_observing_later_input(tmp_path):
    _,_,obs,_,s=setup(tmp_path)
    s=advance(s,obs[:4]); s=m.commit_hour(s,obs[5]); r=m.summary(s)
    assert r["termination_reason"]=="missing_input" and r["attempted_hour"] is None
    assert r["pending_arrival"]["status"]=="not_observed" and r["next_required_hour"]==2
    audit_termination(r)


@pytest.mark.parametrize("phase",["open","write","flush","fsync","close","pending_readback","publish","readback"])
def test_io_failure_never_adopts_candidate_or_repeats_debt(tmp_path,phase):
    c,p,obs,identity,s=setup(tmp_path)
    before=advance(s,obs[:4])
    failed=m.commit_hour(before,obs[4],hook=fault_at(phase))
    assert failed.state==before.state and failed.closed
    r=m.summary(failed); audit_termination(r)
    uncertain=phase in {"publish","readback"}
    assert r["termination_reason"]==("commit_outcome_unknown" if uncertain else "persistence_failure")
    assert r["last_accepted_hour"]==(None if uncertain else 1)
    assert r["primary_remaining_debt"]=="1/5"
    with pytest.raises(ValueError,match="closed"): m.commit_hour(failed,obs[4])
    if phase=="readback":
        recovered=m.reopen(before.root,c,p,obs[:5],"on_time",identity)
        assert recovered.state.business.next_hour==3 and recovered.state.business.ledger.debt==0
        assert len(recovered.state.business.records)==5
    else:
        # open failure creates no pending file, so the exact old accepted prefix is recoverable.
        if phase=="open":
            assert m.reopen(before.root,c,p,obs[:4],"on_time",identity).state==before.state
        else:
            recovered=m.reopen(before.root,c,p,obs[:4],"on_time",identity)
            assert recovered.state==before.state and recovered.reason=="incomplete_publication" and recovered.closed
            assert m.summary(recovered)["last_accepted_hour"]==1


def test_actual_rename_then_exception_is_adjudicated_by_reopen(tmp_path,monkeypatch):
    c,p,obs,identity,s=setup(tmp_path)
    s=advance(s,obs[:4]); original=m.os.rename

    def renamed_then_failed(a,b):
        original(a,b)
        raise OSError("rename returned ambiguously")

    monkeypatch.setattr(m.os,"rename",renamed_then_failed)
    failed=m.commit_hour(s,obs[4])
    assert failed.reason=="commit_outcome_unknown" and failed.state==s.state
    monkeypatch.setattr(m.os,"rename",original)
    recovered=m.reopen(s.root,c,p,obs[:5],"on_time",identity)
    assert recovered.state.business.next_hour==3


def test_reported_unknown_with_no_final_or_pending_cannot_guess_old_state(tmp_path):
    c,p,obs,identity,s=setup(tmp_path); s=advance(s,obs[:4])
    failed=m.commit_hour(s,obs[4],hook=fault_at("publish"))
    witness=m.recovery_witness(failed)
    (s.root/"step_0004.json.pending").unlink()
    with pytest.raises(m.ReopenError,match="no confirmed final") as error:
        m.reopen(s.root,c,p,obs[:4],"on_time",identity,publication_witness=witness)
    assert error.value.session.state==s.state


def test_checkpoint_close_requires_reopen_then_suffix_matches_continuous(tmp_path):
    c,p,obs,identity,s=setup(tmp_path)
    prefix=advance(s,obs[:4]); closed=m.checkpoint_and_close(prefix)
    with pytest.raises(ValueError,match="closed"): m.commit_hour(closed,obs[4])
    with pytest.raises(ValueError,match="checkpointed"): m.commit_hour(prefix,obs[4])
    reopened=m.reopen(s.root,c,p,obs[:4],"on_time",identity)
    final=m.finish(advance(reopened,obs[4:]))
    expected=network.execute_network(c,p,obs,"on_time",identity)
    assert final.state==expected
    audit_termination(m.summary(final))


def test_numerical_attempt_is_read_without_recreating_failure(tmp_path,monkeypatch):
    c,p,obs,identity,s=setup(tmp_path)
    s=advance(s,obs[:3]); original=network.dc_witness

    def unavailable(data,poi,load,*args,**kwargs):
        if load==Q(1,2): raise ArithmeticError("injected numerical failure")
        return original(data,poi,load,*args,**kwargs)

    monkeypatch.setattr(network,"dc_witness",unavailable)
    s=m.finish(m.commit_hour(s,obs[3])); report=m.summary(s)
    assert s.reason=="network_unresolved" and report["last_accepted_hour"]==0 and report["attempted_hour"]==1
    assert report["pending"]["b2_candidate_record"]["proposal"]["ledger_applied"] is False
    monkeypatch.setattr(network,"dc_witness",original)
    recovered=m.reopen(s.root,c,p,obs[:3],"on_time",identity,attempt_observation=obs[3])
    assert m.summary(recovered)==report
    audit_termination(report)


def test_uncommitted_deadline_and_late_recovery_do_not_erase_observed_history(tmp_path):
    _,_,obs,_,s=setup(tmp_path,clean="late")
    s=advance(s,obs[:6])
    assert s.state.business.next_hour==4
    failed=m.commit_hour(s,obs[6],hook=fault_at("close","step_0006.json"))
    r=m.summary(failed); audit_termination(r)
    assert r["business_prefix_assessment"]["observed_primary_deadline_miss"]=="1/5"
    assert r["primary_remaining_debt"]=="1/5"


@pytest.mark.parametrize("mutation",["digest","partial","gap","extra","directory","pending_and_final"])
def test_bad_journal_never_silently_returns_writable_old_prefix(tmp_path,mutation):
    c,p,obs,identity,s=setup(tmp_path); s=advance(s,obs[:4])
    path=s.root/"step_0003.json"
    if mutation=="digest":
        row=m.read_json(path); row["after_state_sha"]="0"*64; path.write_bytes(m.encoded(row))
    elif mutation=="partial": path.write_text('{"schema":',encoding="utf-8")
    elif mutation=="gap": path.rename(s.root/"step_0004.json")
    elif mutation=="extra": (s.root/"step_0004.json").write_bytes(path.read_bytes())
    elif mutation=="directory": (s.root/"extra").mkdir()
    else: (s.root/"step_0003.json.pending").write_bytes(path.read_bytes())
    with pytest.raises(m.ReopenError) as error: m.reopen(s.root,c,p,obs[:4],"on_time",identity)
    r=m.summary(error.value.session)
    assert r["state_certainty"]=="unresolved" and r["last_accepted_hour"] is None
    assert r["resume_permitted"] is False


def test_reopen_rejects_extra_caller_prefix_and_identity_drift(tmp_path):
    c,p,obs,identity,s=setup(tmp_path); s=advance(s,obs[:4])
    with pytest.raises(m.ReopenError): m.reopen(s.root,c,p,obs[:5],"on_time",identity)
    with pytest.raises(m.ReopenError): m.reopen(s.root,c,p,obs[:4],"on_time",identity+":other")
    with pytest.raises(m.ReopenError): m.reopen(s.root,c,replace(p,capacity=Q(3,10)),obs[:4],"on_time",identity)


def test_implementation_and_runtime_drift_return_typed_reopen_failure(tmp_path,monkeypatch):
    c,p,obs,identity,s=setup(tmp_path); s=advance(s,obs[:4])
    original=m.implementation_pins
    monkeypatch.setattr(m,"implementation_pins",lambda:dict(original(),changed=True))
    with pytest.raises(m.ReopenError,match="implementation drift"): m.reopen(s.root,c,p,obs[:4],"on_time",identity)
    monkeypatch.setattr(m,"implementation_pins",original)
    version=m.importlib.metadata.version
    monkeypatch.setattr(m.importlib.metadata,"version",lambda name:"changed" if name=="scipy" else version(name))
    with pytest.raises(m.ReopenError,match="package drift"): m.reopen(s.root,c,p,obs[:4],"on_time",identity)


def test_duplicate_hour_cannot_create_another_cohort_or_X_event(tmp_path):
    _,_,obs,_,s=setup(tmp_path); s=advance(s,obs[:4])
    before=m.encoded(s.state)
    with pytest.raises(ValueError,match="duplicate"): m.commit_hour(s,obs[3])
    assert m.encoded(s.state)==before
    assert s.state.x_events==1 and s.state.business.ledger.debt==Q(1,5)


@pytest.mark.parametrize("target",["checkpoint.json","terminal.json"])
def test_close_failure_of_checkpoint_or_terminal_preserves_accepted_tasks(tmp_path,target):
    c,p,obs,identity,s=setup(tmp_path); s=advance(s,obs[:4])
    failed=m.checkpoint_and_close(s,hook=fault_at("close",target)) if target=="checkpoint.json" else m.finish(s,hook=fault_at("close",target))
    assert failed.reason=="persistence_failure" and failed.state==s.state
    assert m.summary(failed)["last_accepted_hour"]==1
    audit_termination(m.summary(failed))
    recovered=m.reopen(s.root,c,p,obs[:4],"on_time",identity)
    assert recovered.closed and recovered.reason=="incomplete_publication" and recovered.state==s.state


def test_terminal_readback_failure_keeps_completed_accepted_state(tmp_path):
    c,p,obs,identity,s=setup(tmp_path); s=advance(s,obs)
    failed=m.finish(s,hook=fault_at("readback","terminal.json"))
    assert failed.reason=="publication_outcome_unknown" and failed.state.business.next_hour==8
    assert m.summary(failed)["last_accepted_hour"]==7
    recovered=m.reopen(s.root,c,p,obs,"on_time",identity)
    assert recovered.reason=="observation_complete" and recovered.state==s.state


def test_independent_audit_failure_preserves_steps_without_publishing_success(tmp_path,monkeypatch):
    import src.staged_termination_audit_v1 as oracle
    _,_,obs,_,s=setup(tmp_path); s=advance(s,obs[:4])
    monkeypatch.setattr(oracle,"audit_termination",lambda report:(_ for _ in ()).throw(AssertionError("injected audit failure")))
    failed=m.finish(s)
    assert failed.reason=="independent_audit_failure" and failed.closed
    assert m.summary(failed)["state_certainty"]=="known" and failed.audit_validity=="failed"
    assert len(list(s.root.glob("step_*.json")))==4 and not (s.root/"terminal.json").exists()


@pytest.mark.parametrize("field,value",[("hour",True),("ordinal",True),("after_state_sha","0"*64)])
def test_reopen_rejects_wrong_step_metadata(tmp_path,field,value):
    c,p,obs,identity,s=setup(tmp_path); s=advance(s,obs[:4])
    path=s.root/"step_0003.json"; row=m.read_json(path); row[field]=value; path.write_bytes(m.encoded(row))
    with pytest.raises(m.ReopenError): m.reopen(s.root,c,p,obs[:4],"on_time",identity)


def test_terminal_tamper_and_normal_end_do_not_override_primary_censoring(tmp_path):
    _,_,obs,_,s=setup(tmp_path,clean="late",registration_end=2,expected_last_hour=2)
    s=m.finish(advance(s,obs[:5])); r=m.summary(s)
    assert r["termination_reason"]=="followup_horizon_insufficient"
    audit_termination(r)
    r["termination_reason"]="observation_complete"; r["pending_arrival"]["status"]="none"
    with pytest.raises(AssertionError): audit_termination(r)


@pytest.mark.parametrize("phase",["open","write","flush","fsync","close","pending_readback","publish","readback"])
def test_attempt_publication_failure_is_separate_from_accepted_state(tmp_path,phase):
    c,p,obs,identity,s=setup(tmp_path,plan="delayed"); s=advance(s,obs[:5])
    failed=m.commit_hour(s,obs[5],hook=fault_at(phase,"attempt.json"))
    assert failed.state==s.state and m.summary(failed)["last_accepted_hour"]==2
    assert failed.reason==("publication_outcome_unknown" if phase in {"publish","readback"} else "persistence_failure")
    assert m.finish(failed) is failed and not (s.root/"terminal.json").exists()
    audit_termination(m.summary(failed))
    witness=m.recovery_witness(failed)
    recovered=m.reopen(s.root,c,p,obs[:5],"delayed",identity,publication_witness=witness,
                       attempt_observation=obs[5] if phase=="readback" else None)
    assert recovered.closed and recovered.state==s.state
    assert recovered.reason==("policy_or_admission_rejected" if phase=="readback" else "incomplete_publication")
    audit_termination(m.summary(recovered))


@pytest.mark.parametrize("kind",["step","attempt","checkpoint","terminal"])
def test_pending_only_keeps_known_state_but_final_and_pending_is_unresolved(tmp_path,kind):
    plan="delayed" if kind=="attempt" else "on_time"
    c,p,obs,identity,s=setup(tmp_path,plan=plan)
    prefix=5 if kind=="attempt" else 4
    s=advance(s,obs[:prefix]); target="step_0004.json" if kind=="step" else kind+".json"
    hook=fault_at("close",target)
    if kind in {"step","attempt"}: failed=m.commit_hour(s,obs[prefix],hook=hook)
    elif kind=="checkpoint": failed=m.checkpoint_and_close(s,hook)
    else: failed=m.finish(s,hook)
    recovered=m.reopen(s.root,c,p,obs[:prefix],plan,identity,publication_witness=m.recovery_witness(failed))
    assert recovered.reason=="incomplete_publication" and m.summary(recovered)["state_certainty"]=="known"
    assert m.summary(recovered)["last_accepted_hour"]==s.state.business.next_hour-1
    pending=s.root/(target+".pending")
    (s.root/target).write_bytes(pending.read_bytes())
    # A step final adds one record; bind the matching extended caller prefix.
    with pytest.raises(m.ReopenError):
        m.reopen(s.root,c,p,obs[:prefix+int(kind=="step")],plan,identity,
                 attempt_observation=obs[prefix] if kind=="attempt" else None)


def test_missing_terminal_after_reported_failure_does_not_return_writable_session(tmp_path):
    c,p,obs,identity,s=setup(tmp_path); s=advance(s,obs[:4])
    failed=m.finish(s,hook=fault_at("open","terminal.json"))
    assert not (s.root/"terminal.json").exists() and not (s.root/"terminal.json.pending").exists()
    recovered=m.reopen(s.root,c,p,obs[:4],"on_time",identity,publication_witness=m.recovery_witness(failed))
    assert recovered.closed and recovered.reason=="incomplete_publication"
    assert recovered.io_error["planned_reason"]=="missing_input"


def test_independent_audit_failure_on_reopen_preserves_verified_storage_head(tmp_path,monkeypatch):
    c,p,obs,identity,s=setup(tmp_path); s=advance(s,obs[:4])
    monkeypatch.setattr(m,"audit_network",lambda *a:(_ for _ in ()).throw(AssertionError("injected reader audit failure")))
    recovered=m.reopen(s.root,c,p,obs[:4],"on_time",identity)
    assert recovered.reason=="independent_audit_failure" and recovered.closed and recovered.state==s.state
    assert m.summary(recovered)["last_accepted_hour"]==1 and recovered.audit_validity=="failed"
    assert not (s.root/"audit_failure.json").exists()  # Reopen is read-only.


def test_last_hour_rejection_has_observed_arrival_and_no_unobserved_future_in_scope(tmp_path):
    _,_,obs,_,s=setup(tmp_path,plan="delayed",expected_last_hour=3)
    r=m.summary(m.finish(advance(s,obs[:6])))
    assert r["last_accepted_hour"]==2 and r["attempted_hour"]==3
    assert r["pending_arrival"]["status"]=="observed_pending_unaccepted"
    assert r["future_arrivals_unobserved"] is False
    audit_termination(r)


def test_live_append_rejects_changed_disk_head(tmp_path):
    _,_,obs,_,s=setup(tmp_path); s=advance(s,obs[:4])
    path=s.root/"step_0003.json"; path.write_bytes(path.read_bytes()+b" ")
    with pytest.raises(ValueError,match="disk head"): m.commit_hour(s,obs[4])
    assert not (s.root/"step_0004.json").exists()


def test_zero_step_checkpoint_can_reopen_without_inventing_hours(tmp_path):
    c,p,obs,identity,s=setup(tmp_path); m.checkpoint_and_close(s)
    recovered=m.reopen(s.root,c,p,(),"on_time",identity)
    assert recovered.state==s.state and recovered.state.business.next_hour==-2
    assert m.commit_hour(recovered,obs[0]).state.business.next_hour==-1


@pytest.mark.parametrize("target",["genesis.json","checkpoint.json"])
def test_noncanonical_bound_objects_are_rejected(tmp_path,target):
    c,p,obs,identity,s=setup(tmp_path)
    if target=="checkpoint.json": m.checkpoint_and_close(s)
    path=s.root/target; saved=m.read_json(path); path.write_text(json.dumps(saved,indent=2),encoding="utf-8")
    with pytest.raises(m.ReopenError,match="not canonical"): m.reopen(s.root,c,p,(),"on_time",identity)


@pytest.mark.parametrize("field,value",[("genesis_sha","bad"),("audit_validity","invented"),
                                       ("last_accepted_hour",True),("io_error",{"unknown":True})])
def test_independent_terminal_metadata_tampering_is_rejected(tmp_path,field,value):
    _,_,obs,_,s=setup(tmp_path); r=m.summary(m.finish(advance(s,obs[:4])))
    r[field]=value
    with pytest.raises(AssertionError): audit_termination(r)


def test_independent_auditor_remains_active_in_optimized_python():
    run=subprocess.run([sys.executable,"-B","-O","-c",
        "from src.staged_network_audit_v1 import check; check(False,'B3-audit-active')"],cwd=ROOT,capture_output=True,text=True,timeout=15)
    assert run.returncode!=0 and "B3-audit-active" in run.stderr


@pytest.mark.parametrize("wrong_target",["terminal.json","checkpoint.json","attempt.json"])
def test_unknown_step_witness_cannot_be_masked_by_other_pending_role(tmp_path,wrong_target):
    c,p,obs,identity,s=setup(tmp_path); s=advance(s,obs[:4])
    failed=m.commit_hour(s,obs[4],hook=fault_at("publish"))
    (s.root/"step_0004.json.pending").rename(s.root/(wrong_target+".pending"))
    with pytest.raises(m.ReopenError,match="target contradict"):
        m.reopen(s.root,c,p,obs[:4],"on_time",identity,publication_witness=m.recovery_witness(failed))


@pytest.mark.parametrize("plan,corrupt",[("on_time",False),("delayed",False),("on_time",True),("delayed",True)])
def test_pending_without_witness_preserves_observation_or_reports_unreadable(tmp_path,plan,corrupt):
    c,p,obs,identity,s=setup(tmp_path,plan=plan); length=5 if plan=="delayed" else 4
    s=advance(s,obs[:length]); target="attempt.json" if plan=="delayed" else "step_0004.json"
    m.commit_hour(s,obs[length],hook=fault_at("close",target))
    if corrupt: (s.root/(target+".pending")).write_bytes(b'{"truncated":')
    recovered=m.reopen(s.root,c,p,obs[:length],plan,identity); r=m.summary(recovered)
    assert recovered.audit_validity=="passed" and recovered.state==s.state
    assert r["pending_arrival"]["status"]==("evidence_unresolved" if corrupt else "observed_pending_unaccepted")
    assert r["attempted_hour"]==(None if corrupt else obs[length].hour)
    if corrupt: assert r["future_arrivals_unobserved"] is None and r["policy_outcome"]=="unresolved"
    audit_termination(r)


def test_unresolved_network_evidence_survives_terminal_storage_failure(tmp_path,monkeypatch):
    c,p,obs,identity,s=setup(tmp_path); s=advance(s,obs[:3]); original=network.dc_witness
    def unavailable(data,poi,load,*args,**kwargs):
        if load==Q(1,2): raise ArithmeticError("injected numerical failure")
        return original(data,poi,load,*args,**kwargs)
    monkeypatch.setattr(network,"dc_witness",unavailable)
    unresolved=m.commit_hour(s,obs[3]); monkeypatch.setattr(network,"dc_witness",original)
    failed=m.finish(unresolved,hook=fault_at("close","terminal.json"))
    assert failed.reason=="persistence_failure" and m.summary(failed)["policy_outcome"]=="unresolved"
    reopened=m.reopen(s.root,c,p,obs[:3],"on_time",identity,attempt_observation=obs[3])
    assert reopened.reason=="incomplete_publication" and m.summary(reopened)["policy_outcome"]=="unresolved"
    audit_termination(m.summary(reopened))


@pytest.mark.parametrize("phase",["open","write","flush","fsync","close","pending_readback","publish","readback"])
def test_genesis_failure_has_typed_zero_prefix_recovery(tmp_path,phase):
    c=network.load_config(FIXTURE); p,obs=network.load_case(c,"on_time","early"); root=tmp_path/"store"
    with pytest.raises(m.CreateError) as caught:
        m.create_session(root,c,p,"on_time","genesis-fault",hook=fault_at(phase,"genesis.json"))
    failed=caught.value.session; r=m.summary(failed)
    assert failed.reason=="initialization_failure" and failed.closed and not failed.state.records
    assert r["publication_outcome"]==("unresolved" if phase in {"publish","readback"} else "not_published")
    audit_termination(r)
    recovered=m.reopen(root,c,p,(),"on_time","genesis-fault",publication_witness=m.recovery_witness(failed))
    assert recovered.audit_validity=="passed" and not recovered.state.records
    assert recovered.reason==(None if phase=="readback" else "initialization_failure")
    if phase!="readback":
        assert recovered.closed
        audit_termination(m.summary(recovered))
    else: assert m.commit_hour(recovered,obs[0]).state.business.next_hour==-1


def test_missing_genesis_after_unknown_publication_stays_closed(tmp_path):
    c=network.load_config(FIXTURE); p,_=network.load_case(c,"on_time","early"); root=tmp_path/"store"
    with pytest.raises(m.CreateError) as caught:
        m.create_session(root,c,p,"on_time","genesis-missing",hook=fault_at("publish","genesis.json"))
    (root/"genesis.json.pending").unlink()
    recovered=m.reopen(root,c,p,(),"on_time","genesis-missing",publication_witness=m.recovery_witness(caught.value.session))
    assert recovered.closed and recovered.reason=="initialization_failure"
    assert m.summary(recovered)["publication_outcome"]=="unresolved"
    audit_termination(m.summary(recovered))


def test_repeat_finish_and_reopened_finish_are_byte_preserving(tmp_path):
    c,p,obs,identity,s=setup(tmp_path); s=advance(s,obs[:4]); finished=m.finish(s)
    before={v.name:v.read_bytes() for v in s.root.iterdir()}
    assert m.summary(m.finish(finished))==m.summary(finished)
    assert m.summary(m.finish(s))==m.summary(finished)
    reopened=m.reopen(s.root,c,p,obs[:4],"on_time",identity)
    assert m.summary(m.finish(reopened))==m.summary(finished)
    assert before=={v.name:v.read_bytes() for v in s.root.iterdir()}


@pytest.mark.parametrize("corrupt",[False,True])
def test_bare_caller_observation_cannot_override_pending_attempt(tmp_path,corrupt):
    c,p,obs,identity,s=setup(tmp_path,plan="delayed"); s=advance(s,obs[:5])
    m.commit_hour(s,obs[5],hook=fault_at("close","attempt.json"))
    if corrupt: (s.root/"attempt.json.pending").write_bytes(b"{truncated")
    altered=replace(obs[5],workload=obs[5].workload+Q(1,10))
    with pytest.raises(m.ReopenError,match="pending observation differ"):
        m.reopen(s.root,c,p,obs[:5],"delayed",identity,attempt_observation=altered)


def test_complete_pending_attempt_bytes_must_match_failure_witness(tmp_path):
    c,p,obs,identity,s=setup(tmp_path,plan="delayed"); s=advance(s,obs[:5])
    failed=m.commit_hour(s,obs[5],hook=fault_at("close","attempt.json"))
    path=s.root/"attempt.json.pending"; value=m.read_json(path)
    value["record"]["error"]="different evidence preserving observation"
    path.write_bytes(m.encoded(value))
    with pytest.raises(m.ReopenError,match="pending bytes and publication witness differ"):
        m.reopen(s.root,c,p,obs[:5],"delayed",identity,publication_witness=m.recovery_witness(failed))
