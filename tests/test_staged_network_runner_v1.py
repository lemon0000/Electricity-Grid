from pathlib import Path
import json

import pytest

import experiments.staged_network_b2_development_v1 as runner


def test_runner_rejects_output_outside_dedicated_attempt_root(tmp_path):
    with pytest.raises(ValueError,match="outside dedicated"):
        runner.run(tmp_path/"attempt")
    assert not (tmp_path/"attempt").exists()


def test_runner_output_is_exclusive_and_size_bounded(tmp_path):
    path=tmp_path/"record.json"
    runner.dump(path,{"complete":True})
    with pytest.raises(FileExistsError): runner.dump(path,{"complete":False})
    with pytest.raises(ValueError,match="size limit"):
        runner.dump(tmp_path/"large.json",{"payload":"x"*(2*1024**2)})
    assert not (tmp_path/"large.json").exists()


def test_resource_stop_preserves_failure_without_launching_child(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,"BASE",tmp_path)
    monkeypatch.setattr(runner,"fingerprints",lambda:{"synthetic":"resource refusal only"})
    monkeypatch.setattr(runner,"LIMITS",dict(runner.LIMITS,wall_seconds=-1))
    path=tmp_path/"attempt_01"
    with pytest.raises(RuntimeError,match="resource limit"):
        runner.run(path)
    failure=json.loads((path/"failure.json").read_text(encoding="utf-8"))
    assert failure["status"]=="development_diagnostic_failed"
    assert failure["counts"]["child_processes"]==0 and failure["last_state"] is None


def test_runner_rejects_unregistered_attempt_name(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,"BASE",tmp_path)
    with pytest.raises(ValueError,match="registered attempt_01"): runner.run(tmp_path/"attempt_02")
    assert not (tmp_path/"attempt_02").exists()


@pytest.mark.parametrize("attempt,stem",[("attempt_02","on_time_early"),("attempt_01","delayed_early")])
def test_child_rejects_wrong_attempt_or_stem(tmp_path,monkeypatch,attempt,stem):
    from argparse import Namespace
    monkeypatch.setattr(runner,"BASE",tmp_path)
    args=Namespace(reopen=tmp_path/attempt/(stem+"_checkpoint.json"),
                   result=tmp_path/attempt/(stem+"_terminal.json"),plan="on_time",clean="early")
    with pytest.raises(ValueError,match="child paths"): runner.child(args)


def test_final_event_failure_cannot_create_completion_marker(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,"BASE",tmp_path)
    monkeypatch.setattr(runner,"fingerprints",lambda:{})
    monkeypatch.setattr(runner,"load_config",lambda p:None)
    monkeypatch.setattr(runner,"CASES",())
    monkeypatch.setattr(runner,"EXPECTED",{key:0 for key in runner.EXPECTED})
    path=tmp_path/"attempt_01"
    original=Path.open

    def fail_last_event(self,*args,**kwargs):
        if self.name=="events.jsonl" and (path/"report.json").exists():
            raise OSError("injected final event failure")
        return original(self,*args,**kwargs)

    monkeypatch.setattr(Path,"open",fail_last_event)
    with pytest.raises(OSError,match="final event failure"): runner.run(path)
    assert (path/"failure.json").exists() and not (path/"completion.json").exists()
    assert json.loads((path/"report.json").read_text())["status"]=="development_diagnostic_evaluated"


def test_completion_inventory_detects_tampering_and_extra_files(tmp_path):
    runner.dump(tmp_path/"report.json",{"evaluated":True})
    complete(tmp_path)
    runner.verify_completion(tmp_path)
    with pytest.raises(ValueError,match="bound artifact"):
        runner.verify_completion(tmp_path,supplemental=("report.json",))
    runner.dump(tmp_path/"extra.json",{})
    with pytest.raises(ValueError,match="inventory differs"): runner.verify_completion(tmp_path)
    (tmp_path/"extra.json").unlink()
    (tmp_path/"report.json").write_text("{}",encoding="utf-8")
    with pytest.raises(ValueError,match="inventory differs"): runner.verify_completion(tmp_path)


def complete(path):
    artifacts=runner.inventory(path)
    value=dict(status="development_diagnostic_completed",authority="DRAFT_NONAUTHORITATIVE",scope=runner.SCOPE,
               artifacts=artifacts,artifact_bytes_before_completion=sum(v["bytes"] for v in artifacts.values()),
               elapsed_before_completion_write=1.,sampled_process_tree_peak_rss_bytes=1024)
    runner.dump(path/"completion.json",value)
    return value


@pytest.mark.parametrize("field,value",[("scope","other"),("artifact_bytes_before_completion",99),
                                       ("extra",True),("elapsed_before_completion_write",True),
                                       ("sampled_process_tree_peak_rss_bytes",-1)])
def test_completion_schema_and_resource_fields_are_strict(tmp_path,field,value):
    runner.dump(tmp_path/"report.json",{})
    saved=complete(tmp_path); saved[field]=value
    (tmp_path/"completion.json").write_text(json.dumps(saved),encoding="utf-8")
    with pytest.raises(ValueError): runner.verify_completion(tmp_path)


@pytest.mark.parametrize("invalid",['{"status":0,"status":1}','{"status":NaN}'])
def test_completion_rejects_duplicate_keys_and_nonfinite_json(tmp_path,invalid):
    (tmp_path/"completion.json").write_text(invalid,encoding="utf-8")
    with pytest.raises(ValueError): runner.verify_completion(tmp_path)


def test_completion_rejects_extra_directory(tmp_path):
    complete(tmp_path)
    (tmp_path/"nested").mkdir()
    with pytest.raises(ValueError,match="regular files"): runner.verify_completion(tmp_path)


def test_completion_rejects_symlinks_when_supported(tmp_path):
    target=tmp_path/"target.json"; runner.dump(target,{})
    complete(tmp_path)
    try: (tmp_path/"alias.json").symlink_to(target)
    except OSError: pytest.skip("symlink privilege unavailable")
    with pytest.raises(ValueError,match="regular files"): runner.verify_completion(tmp_path)
