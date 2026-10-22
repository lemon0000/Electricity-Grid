import json
from pathlib import Path

import pytest

import experiments.staged_termination_b3_development_v1 as r


def complete(path,monkeypatch):
    artifacts=r.inventory(path)
    monkeypatch.setattr(r,"expected_artifact_paths",lambda:set(artifacts))
    value=dict(status="development_diagnostic_completed",authority="DRAFT_NONAUTHORITATIVE",scope=r.journal.SCOPE,
        artifacts=artifacts,artifact_bytes_before_completion=sum(v["bytes"] for v in artifacts.values()),
        elapsed_before_completion_write=1.,sampled_process_tree_peak_rss_bytes=1024)
    r.prior.dump(path/"completion.json",value)
    return value


def test_output_must_be_registered_and_exclusive(tmp_path,monkeypatch):
    monkeypatch.setattr(r,"BASE",tmp_path)
    with pytest.raises(ValueError,match="registered"): r.run(tmp_path/"attempt_02")
    path=tmp_path/"attempt_01"; path.mkdir()
    with pytest.raises(FileExistsError): r.run(path)
    assert not list(path.iterdir())


def empty_run(monkeypatch,tmp_path):
    monkeypatch.setattr(r,"LAUNCH",r.time.perf_counter())
    monkeypatch.setattr(r,"BASE",tmp_path)
    monkeypatch.setattr(r,"fingerprints",lambda:{})
    monkeypatch.setattr(r.network,"load_config",lambda path:None)
    monkeypatch.setattr(r,"CASES",{})
    monkeypatch.setattr(r,"PROBES",())
    monkeypatch.setattr(r,"EXPECTED",{key:0 for key in r.EXPECTED})


def test_resource_refusal_preserves_failure_and_restores_meter(tmp_path,monkeypatch):
    empty_run(monkeypatch,tmp_path); original=r.journal.encoded
    monkeypatch.setattr(r,"LIMITS",dict(r.LIMITS,wall_seconds=-1))
    with pytest.raises(ValueError,match="resource limit"): r.run(tmp_path/"attempt_01")
    failure=r.journal.read_json(tmp_path/"attempt_01/failure.json")
    assert failure["counts"]["child_processes"]==0 and failure["last_accepted"] is None
    assert r.journal.encoded is original


def test_last_event_failure_prevents_completion(tmp_path,monkeypatch):
    empty_run(monkeypatch,tmp_path); path=tmp_path/"attempt_01"; original=Path.open
    def inject(self,*args,**kwargs):
        if self.name=="events.jsonl" and (path/"report.json").exists(): raise OSError("final event failure")
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,"open",inject)
    with pytest.raises(OSError,match="final event failure"): r.run(path)
    assert (path/"failure.json").exists() and not (path/"completion.json").exists()


def test_post_completion_resource_check_can_invalidate_marker(tmp_path,monkeypatch):
    empty_run(monkeypatch,tmp_path); path=tmp_path/"attempt_01"; original=r.verify_completion
    def exceed_after_verify(*args,**kwargs):
        result=original(*args,**kwargs)
        monkeypatch.setattr(r,"LIMITS",dict(r.LIMITS,wall_seconds=-1))
        return result
    monkeypatch.setattr(r,"verify_completion",exceed_after_verify)
    with pytest.raises(ValueError,match="resource limit"): r.run(path)
    assert (path/"completion.json").exists() and (path/"failure.json").exists()
    with pytest.raises(ValueError): original(path)


def test_nested_inventory_binds_pending_and_rejects_exclusion_or_tamper(tmp_path,monkeypatch):
    store=tmp_path/"save_before_publish"; store.mkdir()
    record=store/"step_0000.json.pending"; r.prior.dump(record,{"pending":True})
    complete(tmp_path,monkeypatch); r.verify_completion(tmp_path)
    with pytest.raises(ValueError,match="exclusions"):
        r.verify_completion(tmp_path,supplemental=("save_before_publish/step_0000.json.pending",))
    record.write_bytes(b"{}")
    with pytest.raises(ValueError,match="inventory differs"): r.verify_completion(tmp_path)


@pytest.mark.parametrize("kind",["unknown_dir","nested_dir","unknown_journal_file"])
def test_inventory_rejects_undeclared_or_nested_outputs(tmp_path,kind):
    if kind=="unknown_dir": (tmp_path/"other").mkdir()
    else:
        store=tmp_path/"on_time_early"; store.mkdir()
        if kind=="nested_dir": (store/"nested").mkdir()
        else: (store/"unknown.json").write_bytes(b"{}")
    with pytest.raises(ValueError): r.inventory(tmp_path)


def test_resource_sampling_tolerates_only_disappeared_paths(tmp_path,monkeypatch):
    store=tmp_path/"on_time_early"; store.mkdir(); pending=store/"step_0000.json.pending"
    r.prior.dump(pending,{})
    original=Path.lstat
    def renamed(self,*args,**kwargs):
        if self==pending: raise FileNotFoundError("child renamed pending")
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,"lstat",renamed)
    assert r.sampled_sizes(tmp_path)==[]
    with pytest.raises(FileNotFoundError): r.inventory(tmp_path)


@pytest.mark.parametrize("field,value",[("authority","formal"),("artifact_bytes_before_completion",True),
    ("elapsed_before_completion_write",True),("sampled_process_tree_peak_rss_bytes",-1),("extra",None)])
def test_completion_schema_is_strict(tmp_path,monkeypatch,field,value):
    saved=complete(tmp_path,monkeypatch); saved[field]=value
    (tmp_path/"completion.json").write_text(json.dumps(saved),encoding="utf-8")
    with pytest.raises(ValueError): r.verify_completion(tmp_path)


def test_completion_refuses_failure_and_uninventoried_files(tmp_path,monkeypatch):
    complete(tmp_path,monkeypatch); r.prior.dump(tmp_path/"failure.json",{})
    with pytest.raises(ValueError): r.verify_completion(tmp_path)


def test_meter_preserves_bytes_and_counts_exception_publication(tmp_path):
    counts={key:0 for key in r.EXPECTED}; original=r.journal.encoded
    restores=r.meter(counts)
    try:
        assert r.journal.encoded({"value":1})==original({"value":1})
        r.journal.publish(tmp_path/"first.json",{})
        with pytest.raises(ValueError): r.journal.publish(tmp_path/"first.json",{})
    finally:
        for restore in restores: restore()
    assert r.journal.encoded is original and counts["journal_publish_calls"]==2
    assert counts["journal_publish_return_success"]==1 and counts["journal_publish_errors"]==1


def test_child_exiting_zero_just_after_budget_is_still_refused(monkeypatch):
    monkeypatch.setattr(r.time,"perf_counter",lambda:15.001)
    with pytest.raises(ValueError,match="child time limit"): r.check_child_exit(0,0)


def test_extra_top_level_file_before_completion_is_refused(tmp_path,monkeypatch):
    complete(tmp_path,monkeypatch)
    r.prior.dump(tmp_path/"mystery.json",{})
    value=r.journal.read_json(tmp_path/"completion.json"); value["artifacts"]=r.inventory(tmp_path)
    value["artifact_bytes_before_completion"]=sum(v["bytes"] for v in value["artifacts"].values())
    (tmp_path/"completion.json").write_text(json.dumps(value),encoding="utf-8")
    with pytest.raises(ValueError,match="artifact roles differ"): r.verify_completion(tmp_path)


def test_failure_after_reopen_reports_newly_confirmed_accepted_step(tmp_path,monkeypatch):
    monkeypatch.setattr(r,"LAUNCH",r.time.perf_counter())
    monkeypatch.setattr(r,"BASE",tmp_path)
    monkeypatch.setattr(r,"fingerprints",lambda:{})
    monkeypatch.setattr(r,"CASES",{})
    monkeypatch.setattr(r,"PROBES",("save_after_publish",))
    monkeypatch.setattr(r,"EXPECTED",{key:0 for key in r.EXPECTED})
    path=tmp_path/"attempt_01"
    with pytest.raises(ValueError,match="counts differ"): r.run(path)
    failure=r.journal.read_json(path/"failure.json")
    assert len(failure["last_accepted"]["state"]["business"]["records"])==5
    assert failure["last_summary"] is None and failure["completed_children"]==[]


def test_late_reopen_error_preserves_its_verified_prefix(tmp_path,monkeypatch):
    monkeypatch.setattr(r,"LAUNCH",r.time.perf_counter()); monkeypatch.setattr(r,"BASE",tmp_path)
    monkeypatch.setattr(r,"fingerprints",lambda:{}); monkeypatch.setattr(r,"CASES",{})
    monkeypatch.setattr(r,"PROBES",("save_after_publish",))
    original=r.journal.reopen
    def late_error(*args,**kwargs):
        recovered=original(*args,**kwargs)
        raise r.journal.ReopenError(recovered,ValueError("late integrity error after fifth step"))
    monkeypatch.setattr(r.journal,"reopen",late_error)
    path=tmp_path/"attempt_01"
    with pytest.raises(r.journal.ReopenError,match="late integrity error"): r.run(path)
    failure=r.journal.read_json(path/"failure.json")
    assert len(failure["last_accepted"]["state"]["business"]["records"])==5
    assert failure["last_accepted"]["scope"]=="last_verified_prefix"
    assert failure["last_summary"]["state_certainty"]=="unresolved"
