"""Ordinary tmp/fake-monitor checks; no diagnostic attempt or numerical calls."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import time
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import staged_rts24_append_cost_probe_v1 as probe
from experiments.staged_rts24_append_cost_observer_v1 import Observation, modules


@pytest.fixture(autouse=True)
def numerical_denial(monkeypatch):
    import highspy
    import pyomo.environ as pyo
    def denied(*a, **kw): pytest.fail("ordinary cost-probe check requested a numerical factory")
    monkeypatch.setattr(highspy, "Highs", denied)
    monkeypatch.setattr(pyo, "SolverFactory", denied)


def test_all_alias_groups_count_once_and_restore_originals():
    m = modules()
    source = m["selective"].reference_requests
    old_pack = m["codec"].pack
    with Observation() as obs:
        assert all(m[key].reference_requests is m["selective"].reference_requests for key in ("v2", "v3", "policy", "audit"))
        fixture = probe.packet("full_temporal", m)["fixture"]
        m["v2"].reference_requests(fixture, "on_time", "late", "full_temporal", 0)
        m["v3"].reference_requests(fixture, "on_time", "late", "full_temporal", 1)
        probe.check_counts(obs.counts, 2, 7)
        assert obs.counts["pack.started"] == obs.counts["pack.returned"]
    assert all(m[key].reference_requests is source for key in ("v2", "v3", "policy", "audit", "selective"))
    assert m["codec"].pack is m["v2"].pack is m["v3"].pack is old_pack


def test_constructor_failure_restores_already_installed_wrappers(monkeypatch):
    m = modules()
    import highspy
    original = highspy.Highs
    monkeypatch.setattr(m["v3"], "reference_requests", lambda *a: None)
    with pytest.raises(ValueError, match="alias mismatch"): Observation()
    assert highspy.Highs is original


def test_exception_and_runtime_rebinding_are_observed_then_restored():
    m = modules()
    original = m["policy"].prepare_hour
    def raising(): raise OSError("ordinary controlled error")
    first, second = SimpleNamespace(fn=raising), SimpleNamespace(fn=raising)
    obs = Observation()
    obs.observe("controlled_error", [(first, "fn"), (second, "fn")])
    with pytest.raises(OSError): first.fn()
    assert obs.counts["controlled_error.started"] == obs.counts["controlled_error.raised"] == 1
    assert obs.counts["controlled_error.returned"] == 0 and obs.seconds["controlled_error"] >= 0
    m["policy"].prepare_hour = lambda *a: None
    with pytest.raises(ValueError, match="binding changed"): obs.snapshot()
    with pytest.raises(ValueError, match="drift"): obs.close()
    assert m["policy"].prepare_hour is original and first.fn is second.fn is raising


def test_readonly_mode_rejects_publication_models_full_queries_and_native(tmp_path):
    with Observation(readonly=True) as obs:
        import highspy
        import pyomo.environ as pyo
        for call in (lambda: obs.m["codec"].publish(tmp_path/"never", b"{}"),
                     lambda: obs.m["v3"].publish(tmp_path/"never", b"{}"),
                     lambda: obs.m["codec"].EvidenceStore.put(None, None),
                     lambda: obs.m["c"].hour_requests(None, None, None, None),
                     lambda: obs.m["c"].build_point_model(None),
                     lambda: highspy.Highs(), lambda: pyo.SolverFactory("highs")):
            with pytest.raises(RuntimeError, match="forbids"): call()
        assert obs.counts["forbidden_calls"] == 7 and list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("method", probe.METHODS)
def test_saved_inputs_are_independent_and_baseline_wire_is_frozen(method):
    with Observation() as obs:
        left, right = probe.packet(method, obs.m), probe.packet(method, obs.m)
        assert left["fixture"] is not right["fixture"] and left["payloads"][0] is not right["payloads"][0]
        wanted = probe.baseline(right, obs.m)
        probe.check_counts(obs.counts, 4, 6 if method == "instantaneous" else 14)
        assert wanted["state_ref"] == right["source_refs"][-1]
        assert sorted(key+".json" for key in wanted["wire"]) == wanted["cas_keys"]
        assert all(sha256(raw.encode()).hexdigest() == key for key, raw in wanted["wire"].items())
        assert wanted["cas_bytes"] == sum(len(raw.encode()) for raw in wanted["wire"].values())
        left["payloads"][0]["ordinary_mutation"] = True
        with pytest.raises(ValueError, match="packet mutated"): probe.packet_bookend(left, obs.m)
        probe.packet_bookend(right, obs.m)


@pytest.mark.parametrize("mutated", ["job_quiet_confirmed", "exit_code", "stop_reason", "all_handles_signaled", "complete_inventory", "total_processes", "active_processes", "final_pids"])
def test_monitor_refuses_incomplete_exit_or_historical_handle_closure(mutated):
    record = dict(exit_code=0, stop_reason=None, job_quiet_confirmed=True,
        quiescence_witness=dict(all_handles_signaled=True, complete_inventory=True,
            total_processes=26, observed_unique_member_handles=26, active_processes=0, final_pids=[]))
    probe.accepted_monitor(record)  # Logical roles need not equal physical processes.
    changes = dict(job_quiet_confirmed=False, exit_code=1, stop_reason="cleanup_unknown", all_handles_signaled=False,
        complete_inventory=False, total_processes=27, active_processes=1, final_pids=[99])
    if mutated in record: record[mutated] = changes[mutated]
    else: record["quiescence_witness"][mutated] = changes[mutated]
    with pytest.raises(ValueError, match="not successfully quiet"): probe.accepted_monitor(record)


def test_group_budget_reserves_cleanup_and_records_raised_phase(tmp_path, monkeypatch):
    clock = SimpleNamespace(now=0.)
    monkeypatch.setattr(probe, "BOOT", 0.)
    monkeypatch.setattr(probe, "time", SimpleNamespace(perf_counter=lambda: clock.now, process_time=lambda: clock.now))
    obs = SimpleNamespace(check=lambda: None, snapshot=lambda: dict(counts={}, inclusive_seconds={}))
    budget = probe.Budget(tmp_path, obs)
    def raised(): clock.now += 2.; raise OSError("ordinary timed failure")
    with pytest.raises(OSError): budget.phase("parent", "failed_operation", raised)
    assert budget.phases[-1]["outcome"] == "raised" and budget.spent["parent"] == 2.
    budget.spent["fresh"] = 96.
    with pytest.raises(ValueError, match="reservation"): budget.reserve_fresh()
    budget.spent["fresh"] = 0.
    clock.now = 260.
    with pytest.raises(ValueError): budget.reserve_fresh()


def test_json_sha_and_exclusive_output_cannot_be_reinterpreted(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "BASE", tmp_path)
    monkeypatch.setattr(probe, "PREP", tmp_path/"prep")
    monkeypatch.setattr(probe, "OUTPUT", tmp_path/"probe")
    monkeypatch.setattr(probe, "REGISTRATION", tmp_path/"registration.json")
    probe.PREP.mkdir()
    path = probe.PREP/"pin.json"
    probe.write(path, dict(value=1))
    identity = probe.stamp(path)["sha256"]
    with pytest.raises(FileExistsError): probe.write(path, dict(value=2))
    path.write_bytes(path.read_bytes()+b" ")
    with pytest.raises(ValueError, match="pin/size"): probe.load(path, identity)
    with pytest.raises((ValueError, FileNotFoundError)): probe.write(tmp_path/"elsewhere.json", {})


def test_fault_removal_is_limited_to_new_case_and_preserves_original_bytes(tmp_path, monkeypatch):
    m = modules()
    codec = m["codec"]
    case = tmp_path/"case"
    root = case/"journal"
    objects = root/"objects"
    objects.mkdir(parents=True)
    raw = b"ordinary removed fixture bytes"
    key = sha256(raw).hexdigest()
    victim = objects/(key+".json")
    victim.write_bytes(raw)
    (root/"genesis.json").write_bytes(codec.canonical(dict(fixture_ref=key)))
    session = SimpleNamespace(root=root)
    monkeypatch.setattr(probe, "OUTPUT", tmp_path)
    (tmp_path/"different/journal").mkdir(parents=True)
    # OUTPUT is fixed by design; an unrelated root must be rejected before deletion.
    with pytest.raises(ValueError): probe.remove_fixture(session, tmp_path/"different", codec)
    assert victim.read_bytes() == raw
    removed = probe.remove_fixture(session, case, codec)
    assert removed["sha256"] == key and not victim.exists() and (case/"removed_object.json").read_bytes() == raw


def test_nonquiet_child_is_not_read(tmp_path, monkeypatch):
    from src import staged_rts24_process_guard_v1 as guard
    monkeypatch.setattr(probe, "BASE", tmp_path)
    monkeypatch.setattr(probe, "OUTPUT", tmp_path/"probe")
    monkeypatch.setattr(probe, "PREP", tmp_path/"prep")
    probe.OUTPUT.mkdir(); probe.PREP.mkdir()
    monkeypatch.setattr(probe, "BOOT", time.perf_counter())
    m = modules()
    for key in ("v2", "v3"): monkeypatch.setattr(m[key], "runtime_identity", lambda: {"ordinary_test": "fixed"})
    with Observation() as obs:
        prepared = probe.baseline(probe.packet("full_temporal", obs.m), obs.m)
        probe.write(probe.PREP/"baseline.json", dict(full_temporal=prepared))
        monkeypatch.setattr(guard, "supervise", lambda *a, **kw: dict(exit_code=0, stop_reason=None, job_quiet_confirmed=False))
        original = probe.load
        def read(path, *a, **kw):
            if Path(path).name in ("fresh_result.json", "fresh_observations.json"): pytest.fail("read child data before quiet")
            return original(path, *a, **kw)
        monkeypatch.setattr(probe, "load", read)
        budget = probe.Budget(probe.OUTPUT, obs)
        case = next(case for case in probe.CASES if case["name"] == "v3_full_temporal")
        with pytest.raises(ValueError, match="not successfully quiet"): probe.run_case(case, "0"*64, budget)


@pytest.mark.parametrize("case", probe.CASES, ids=lambda case: case["name"])
def test_case_writer_and_fresh_logic_with_fake_owned_process(tmp_path, monkeypatch, case):
    from src import staged_rts24_process_guard_v1 as guard
    monkeypatch.setattr(probe, "BASE", tmp_path)
    monkeypatch.setattr(probe, "OUTPUT", tmp_path/"probe")
    monkeypatch.setattr(probe, "PREP", tmp_path/"prep")
    probe.OUTPUT.mkdir(); probe.PREP.mkdir()
    monkeypatch.setattr(probe, "BOOT", time.perf_counter())
    m = modules()
    for key in ("v2", "v3"): monkeypatch.setattr(m[key], "runtime_identity", lambda: {"ordinary_test": "fixed"})
    # Process transport and controlled-interpreter verification have dedicated
    # tests; this fake executes the real case/fresh logic without spawning.
    monkeypatch.setattr(probe, "verify_registration", lambda *a, **kw: {})
    with Observation() as obs:
        prepared = probe.baseline(probe.packet(case["method"], obs.m), obs.m)
        probe.write(probe.PREP/"baseline.json", {case["method"]: prepared})
        def monitor(argv, **kw):
            before = Counter(obs.counts)
            class ChildObservation:
                m = obs.m
                @property
                def counts(self): return Counter(obs.counts)-before
            case_sha = argv[argv.index("--case-sha")+1]
            intent_sha = argv[argv.index("--intent-sha")+1]
            with monkeypatch.context() as child_context:
                child_context.setattr(probe.sys, "orig_argv", argv)
                probe.fresh_worker("0"*64, case, case_sha, intent_sha, ChildObservation())
            probe.write(probe.OUTPUT/case["name"]/"fresh_observations.json", dict(
                counts=dict(Counter(obs.counts)-before), complete=True, bindings_valid=True))
            return dict(exit_code=0, stop_reason=None, job_quiet_confirmed=True,
                quiescence_witness=dict(all_handles_signaled=True, complete_inventory=True,
                    total_processes=2, observed_unique_member_handles=2, active_processes=0, final_pids=[]))
        monkeypatch.setattr(guard, "supervise", monitor)
        result = probe.run_case(case, "0"*64, probe.Budget(probe.OUTPUT, obs))
        assert result["case"] == case
        if case["kind"] == "success": assert result["fresh"]["state_ref"] == prepared["state_ref"]
        elif case["kind"] == "deletion": assert result["fresh"]["reader_refused_missing_closure"]


def test_fresh_intent_is_durable_exact_and_not_a_posthoc_monitor(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "BASE", tmp_path)
    monkeypatch.setattr(probe, "OUTPUT", tmp_path/"probe")
    case = probe.CASES[0]
    root = probe.OUTPUT/case["name"]
    root.mkdir(parents=True)
    case_sha, registration_sha = "1"*64, "2"*64
    intent = probe.fresh_intent(case, case_sha, registration_sha)
    probe.write(root/"fresh_intent.json", intent)
    identity = probe.stamp(root/"fresh_intent.json")["sha256"]
    argv = intent["argv_without_intent_sha"]+["--intent-sha", identity]
    monkeypatch.setattr(probe.sys, "orig_argv", argv)
    probe.verify_fresh_intent(identity, case, case_sha, registration_sha)
    monkeypatch.setattr(probe.sys, "orig_argv", argv+["--unexpected"])
    with pytest.raises(ValueError, match="exact argv"): probe.verify_fresh_intent(identity, case, case_sha, registration_sha)
    (root/"fresh_intent.json").write_bytes((root/"fresh_intent.json").read_bytes()+b" ")
    with pytest.raises(ValueError, match="pin/size"): probe.verify_fresh_intent(identity, case, case_sha, registration_sha)


@pytest.mark.parametrize("change", ["missing", "altered", "extra"])
def test_controller_requires_exact_core_bytes_before_trusting_report(tmp_path, monkeypatch, change):
    monkeypatch.setattr(probe, "BASE", tmp_path)
    monkeypatch.setattr(probe, "OUTPUT", tmp_path/"probe")
    probe.OUTPUT.mkdir()
    report = probe.OUTPUT/"report.json"
    probe.write(report, dict(ordinary=True))
    files = {"report.json": probe.stamp(report)}
    probe.write(probe.OUTPUT/"completion.json", dict(authority="DRAFT_NONAUTHORITATIVE", files=files,
        count=1, bytes=files["report.json"]["bytes"], official_verdict=None, seal=None, receipt=None))
    if change == "missing": report.unlink()
    elif change == "altered": report.write_bytes(report.read_bytes()+b" ")
    else: (probe.OUTPUT/"unexpected.json").write_bytes(b"{}")
    with pytest.raises(ValueError, match="completion/readback"): probe.controller_readback("0"*64, {})
    assert not (probe.OUTPUT/"controller_verification.json").exists()


@pytest.mark.skipif(os.name != "nt", reason="registered diagnostic uses Windows atomic Job ownership")
def test_real_owned_transport_keeps_exact_argv_and_controlled_environment(tmp_path):
    from src.staged_rts24_process_guard_v1 import supervise, controlled_environment
    destination = tmp_path/"child.json"
    code = ("import json,os,sys,time; from pathlib import Path; "
        +"Path("+repr(str(destination))+").write_text(json.dumps(dict(argv=sys.orig_argv,environment=dict(os.environ))),encoding='utf-8'); time.sleep(.6)")
    argv = [probe.sys.executable, "-B", "-s", "-c", code]
    monitor = supervise(argv, cwd=probe.ROOT, output=tmp_path, progress=destination,
        limits=dict(wall_seconds=5, no_progress_seconds=5, rss_bytes=1024**3, output_bytes=1024**2, files=20))
    probe.accepted_monitor(monitor)
    result = json.loads(destination.read_text(encoding="utf-8"))
    assert result["argv"] == argv
    assert all(result["environment"][key] == value for key, value in controlled_environment().items())


@pytest.mark.parametrize("mode", ["success", "owned_failure", "preflight_failure"])
def test_controller_timings_cover_success_and_failure_without_touching_old_target(tmp_path, monkeypatch, mode):
    monkeypatch.setattr(probe, "BASE", tmp_path)
    monkeypatch.setattr(probe, "OUTPUT", tmp_path/"probe")
    monkeypatch.setattr(probe, "PREP", tmp_path/"prep")
    probe.OUTPUT.mkdir()
    original = probe.OUTPUT/"preexisting.json"
    original.write_bytes(b"preserve this input")
    def core(*, preparation, expected_sha, timings):
        if mode == "preflight_failure": raise OSError("ordinary preflight rejection")
        timings.update(_owns_target=True, controller_preflight_seconds=.1, owned_monitor_seconds=.2,
            job_quiet_confirmed=True, post_quiet_started=time.perf_counter())
        if mode == "owned_failure": raise OSError("ordinary controller rejection")
        return dict(role="measurement", registration_sha="0"*64)
    monkeypatch.setattr(probe, "launch_core", core)
    if mode != "success":
        with pytest.raises(OSError): probe.launch(preparation=False, expected_sha="0"*64)
    else: probe.launch(preparation=False, expected_sha="0"*64)
    assert original.read_bytes() == b"preserve this input"
    target = probe.OUTPUT/"controller_timings.json"
    if mode == "preflight_failure": assert not target.exists()
    else:
        result = probe.load(target)
        assert result["accepted_success"] is (mode == "success")
        assert result["launcher_total_seconds"] >= 0 and result["post_quiet_readback_seconds"] >= 0
        assert result["controller_preflight_seconds"] == .1 and result["owned_monitor_seconds"] == .2


def test_historical_tree_budget_rejects_large_file_before_reading(tmp_path, monkeypatch):
    directory = tmp_path/"history"
    directory.mkdir()
    ordinary = directory/"known.json"
    ordinary.write_bytes(b"{}")
    monkeypatch.setattr(probe, "ROOT", tmp_path)
    monkeypatch.setattr(probe, "OLD_TREES", (directory,))
    assert probe.tree_pins() == {"history/known.json": probe.stamp(ordinary)}
    huge = directory/"too_large.bin"
    with huge.open("wb") as stream: stream.truncate(8*1024**2+1)
    original = probe.stamp
    def stamp(path):
        if Path(path).name == huge.name: pytest.fail("oversized history was read before the cap")
        return original(path)
    monkeypatch.setattr(probe, "stamp", stamp)
    with pytest.raises(ValueError, match="tree byte cap"): probe.tree_pins()


def capture_fixture(tmp_path, mode):
    relative = "results/tables/staged_rts24_append_cost_v1_non_authoritative/execution_observations_01/launch_capture.ps1"
    script = tmp_path/relative
    script.parent.mkdir(parents=True)
    script.write_bytes((probe.ROOT/relative).read_bytes())
    runner = tmp_path/"experiments/staged_rts24_append_cost_probe_v1.py"
    runner.parent.mkdir()
    runner.write_text("""from pathlib import Path
import json,time
from hashlib import sha256
root=Path.cwd()
relative="""+repr(relative)+"""
mode="""+repr(mode)+"""
script=root/relative
base=script.parent.parent
with (base/'calls.log').open('a') as f: f.write('one fake Python call\\n')
time.sleep(.6)
target=base/'cost_preparation_01'
target.mkdir()
identity=sha256(script.read_bytes()).hexdigest()
if mode=='unbound': identity='0'*64
(target/'request.json').write_text(json.dumps({'pins':{'direct':{relative:{'sha256':identity}}}}))
if mode!='missing': (target/'controller_timings.json').write_text(json.dumps({'accepted_success':mode!='false_timing'}))
if mode=='drift': script.write_bytes(script.read_bytes()+b'\\n# changed by ordinary fake child\\n')
print('fixed saved-cost transport test')
""", encoding="utf-8")
    return script, ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Role", "preparation"]


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell external observation")
@pytest.mark.parametrize("mode", ["success", "missing", "false_timing", "unbound", "drift"])
def test_external_capture_binds_prestart_script_and_refuses_incomplete_success(tmp_path, mode):
    script, argv = capture_fixture(tmp_path, mode)
    original = probe.stamp(script)
    child = subprocess.run(argv, capture_output=True, timeout=15)
    role = script.parent/"preparation_01"
    result, intent = (json.loads((role/name).read_bytes()) for name in ("capture.json", "intent.json"))
    assert child.returncode == (0 if mode == "success" else 90), child.stderr
    assert result["python_exit_code"] == 0 and result["accepted_success"] is (mode == "success")
    assert intent["script_pin"] == result["script_pin"] == original
    assert result["intent_pin"] == probe.stamp(role/"intent.json")
    assert result["log_pin"] == probe.stamp(role/"stdout.log")
    assert intent["no_retry"] and not intent["native_authorized"]
    assert (result["capture_error"] is None) is (mode == "success")
    assert (script.parent/"preparation_01.owner").read_bytes() == b"\x01"


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell atomic create-new capture ownership")
def test_external_capture_duplicate_launch_has_one_atomic_owner(tmp_path):
    script, argv = capture_fixture(tmp_path, "success")
    first = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    second = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    first.communicate(timeout=15)
    second.communicate(timeout=15)
    assert sorted((first.returncode, second.returncode)) == [0, 1]
    assert (script.parent.parent/"calls.log").read_text().splitlines() == ["one fake Python call"]
    result = json.loads((script.parent/"preparation_01/capture.json").read_bytes())
    assert result["accepted_success"] and result["log_pin"] == probe.stamp(script.parent/"preparation_01/stdout.log")
