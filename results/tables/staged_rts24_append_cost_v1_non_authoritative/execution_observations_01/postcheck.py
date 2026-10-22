"""Read original diagnostic bytes; publish one separate verification record."""
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent


def read(path): return json.loads(Path(path).read_bytes())


def stamp(path):
    raw = Path(path).read_bytes()
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def inventory(root):
    return {path.relative_to(root).as_posix(): stamp(path) for path in sorted(root.rglob("*")) if path.is_file()}


def counts(value, expected):
    value = Counter(value)
    calls, descriptions, p0, raw, lower, upper = expected
    assert value["selective.started"] == value["selective.returned"] == calls
    assert value["selective.raised"] == value["forbidden_calls"] == 0
    assert value["descriptions"] == descriptions == p0+raw+lower+upper
    assert [value["role."+name] for name in ("reference_base_P0", "reference_raw_need", "recovery_min_meter", "recovery_max_meter")] == [p0, raw, lower, upper]


def duration(value, upper=None):
    assert math.isfinite(value) and value >= 0 and (upper is None or value <= upper)


def timing(value, identity):
    assert value["authority"] == "DRAFT_NONAUTHORITATIVE" and value["registration_sha"] == identity
    assert value["accepted_success"] and value["job_quiet_confirmed"] and value["error"] is None
    assert value["timing_scope"] == "launch_entry_through_last_record_excludes_own_publication_console_and_process_exit"
    assert "_owns_target" not in value and "post_quiet_started" not in value
    for key in ("controller_preflight_seconds", "owned_monitor_seconds", "post_monitor_processing_seconds", "post_quiet_readback_seconds", "launcher_total_seconds"): duration(value[key])
    assert value["post_quiet_readback_seconds"] == value["post_monitor_processing_seconds"]
    assert sum(value[key] for key in ("controller_preflight_seconds", "owned_monitor_seconds", "post_monitor_processing_seconds")) <= value["launcher_total_seconds"]+1e-8


def verify():
    from experiments import staged_rts24_append_cost_probe_v1 as p
    from experiments.staged_rts24_append_cost_observer_v1 import Observation
    started = time.perf_counter()
    identity = stamp(p.REGISTRATION)["sha256"]
    assert identity == "aebdd0be608c771b0571622d710b54641804a9173183252fc1424577137b9dd1"
    before, preparation_before = inventory(p.OUTPUT), inventory(p.PREP)
    completion, v, report = (read(p.OUTPUT/name) for name in ("completion.json", "controller_verification.json", "report.json"))
    late = {"launcher.json", "launcher.stdout.log", "launcher.stderr.log", "worker.stdout.log", "worker.stderr.log"}
    assert set(v["files"]) == set(completion["files"]) | {"completion.json"} | late
    assert before == {**v["files"], "controller_verification.json":stamp(p.OUTPUT/"controller_verification.json"), "controller_timings.json":stamp(p.OUTPUT/"controller_timings.json")}
    assert all(before[name] == pin for name, pin in completion["files"].items())
    assert completion["count"] == len(completion["files"]) and completion["bytes"] == sum(pin["bytes"] for pin in completion["files"].values())
    assert len(before) <= p.LIMITS["files"] and sum(pin["bytes"] for pin in before.values()) <= p.LIMITS["output_bytes"]
    for record in (completion, v):
        assert record["authority"] == "DRAFT_NONAUTHORITATIVE" and all(record[k] is None for k in ("official_verdict", "seal", "receipt"))
    assert v["registration_sha"] == report["registration_sha"] == identity
    assert v["all_core_and_late_files_read_back"] and v["source_and_old_trees_unchanged"]
    assert [v[k] for k in ("cases", "selective_calls", "descriptions", "measured_selective_calls", "measured_descriptions", "native_calls", "numerical_factories")] == [12,198,548,186,514,0,0]
    duration(v["readback_seconds"],45)
    assert report["authority"] == "DRAFT_NONAUTHORITATIVE"
    assert report["fixed_order_single_descriptive_observation"] and report["preparation_measured_separately"]
    assert all(report[k] is False for k in ("overall_performance_review_complete", "public_numeric_results", "native_authorized", "resource_admission"))
    assert [row["case"] for row in report["cases"]] == list(p.CASES)
    prep, parent = read(p.PREP/"prepare_observations.json"), read(p.OUTPUT/"worker_observations.json")
    for obs in (prep, parent): assert obs["complete"] and obs["bindings_valid"]
    counts(prep["counts"], (12,34,12,6,8,8))
    counts(parent["counts"], (94,260,94,30,68,68))
    fresh_total = Counter()
    with Observation(readonly=True) as obs:
        registration = p.verify_registration(identity, obs.m, full=True)
        for case, row in zip(p.CASES, report["cases"]):
            assert time.perf_counter()-started < 60
            root = p.OUTPUT/case["name"]
            original, launch, intent, fresh, child = (read(root/name) for name in ("case.json", "fresh_launch.json", "fresh_intent.json", "fresh_result.json", "fresh_observations.json"))
            assert row["writer"] == original["trusted_binding"] == read(root/"trusted_binding.json")
            assert row["fresh"] == fresh and row["observations"] == child and child["complete"] and child["bindings_valid"]
            assert intent["case_sha"] == stamp(root/"case.json")["sha256"] and intent["registration_sha"] == identity
            intent_sha = stamp(root/"fresh_intent.json")["sha256"]
            assert launch["intent_sha"] == intent_sha and launch["argv"] == intent["argv_without_intent_sha"]+["--intent-sha",intent_sha]
            p.accepted_monitor(launch["monitor"])
            p.check_counts(child["counts"],*p.expected_counts(case,fresh=True))
            assert not child["counts"].get("selective.raised",0)
            fresh_total.update(child["counts"])
            packet = p.packet(case["method"],obs.m)
            expected = p.registered_packet(packet)
            if case["kind"] == "success":
                excluded = {"source_refs","root_shas","terminal_ref","cas_keys","cas_bytes","wire"}
                assert all(fresh[k] == expected[k] for k in expected if k not in excluded)
                objects = root/"journal/objects"
                assert {x.name:x.read_bytes() for x in objects.iterdir()} == {k+".json":s.encode("utf-8") for k,s in expected["wire"].items()}
                for hour in (1,2):
                    entry = read(root/"journal"/f"entry_{hour:06d}.json")
                    assert entry["payload_ref"] == packet["source_refs"][hour+1] and entry["state_ref"] == packet["source_refs"][hour+3]
            else:
                assert p.inspect_failure(case,packet,obs.m,original["trusted_binding"]) == row["writer_inspection"] == fresh["writer_inspection"]
            p.packet_bookend(packet,obs.m)
        p.verify_registration(identity,obs.m,full=True)
        assert obs.counts.get("selective.started",0) == obs.counts.get("forbidden_calls",0) == 0
    counts(fresh_total,(92,254,92,30,66,66))
    measured = Counter(parent["counts"])+fresh_total
    # Counter addition removes zeros; preserve zero-valued keys for exact record equality.
    raw_measured = Counter(parent["counts"])
    for row in report["cases"]: raw_measured.update(row["observations"]["counts"])
    counts(measured,(186,514,186,60,134,134))
    assert dict(raw_measured) == report["measured_counts_including_fresh"]
    raw_measured.update(prep["counts"])
    counts(raw_measured,(198,548,198,66,142,142))
    assert dict(raw_measured) == report["combined_counts"]
    wt = read(p.OUTPUT/"worker_timing.json")
    assert wt["phases"][:-1] == report["phases"]
    assert {k:wt["phases"][-1][k] for k in ("group","stage","outcome")} == dict(group="report",stage="saved_report",outcome="returned")
    assert wt["excludes"] == "this_record_observations_and_terminal_manifest_publication"
    for phase in wt["phases"]:
        assert phase["outcome"] == "returned" and phase["group"] in p.GROUPS
        duration(phase["wall_seconds"]); duration(phase["cpu_seconds"])
    for group,value in wt["group_seconds"].items(): duration(value,p.GROUPS[group])
    pt, mt = read(p.PREP/"controller_timings.json"), read(p.OUTPUT/"controller_timings.json")
    timing(pt,identity); timing(mt,identity)
    assert report["preparation_controller_timings"] == pt
    externals = {}
    for role,target,internal in (("preparation",p.PREP,pt),("measurement",p.OUTPUT,mt)):
        root = HERE/(role+"_01")
        capture, intent = read(root/"capture.json"), read(root/"intent.json")
        assert set(x.name for x in root.iterdir()) == {"capture.json","intent.json","stdout.log"}
        assert (HERE/(role+"_01.owner")).read_bytes() == b"\x01"
        assert capture["accepted_success"] and capture["python_exit_code"] == capture["exit_code"] == 0 and capture["capture_error"] is None
        assert capture["script_pin"] == intent["script_pin"] == stamp(HERE/"launch_capture.ps1")
        assert capture["intent_pin"] == stamp(root/"intent.json") and capture["log_pin"] == stamp(root/"stdout.log")
        assert capture["controller_timing_pin"] == stamp(target/"controller_timings.json")
        assert capture["argv"] == intent["argv"] and capture["external_wall_seconds"] >= internal["launcher_total_seconds"]
        if role == "measurement": assert capture["argv"][-2:] == ["--registration-sha",identity]
        duration(capture["external_wall_seconds"])
        monitor = read(target/"launcher.json")
        p.accepted_monitor(monitor)
        duration(monitor["outer_seconds"],30 if role=="preparation" else 300)
        externals[role] = dict(external_wall_seconds=capture["external_wall_seconds"],controller=internal,monitor=monitor,
            final_controller_pin=capture["controller_timing_pin"],capture_pin=stamp(root/"capture.json"))
    assert inventory(p.OUTPUT) == before and inventory(p.PREP) == preparation_before
    assert not (p.P1.parent/"p1_01").exists()
    return dict(authority="DRAFT_NONAUTHORITATIVE",registration_sha=identity,files=before,preparation_files=preparation_before,
        all_files_hash_matched=True,cases=12,selective_calls=198,descriptions=548,measurement_calls=186,measurement_descriptions=514,
        native_calls=0,solver_calls=0,source_and_old_trees_unchanged=True,p1_attempt_created=False,
        timings=externals,postcheck_wall_seconds=time.perf_counter()-started,postcheck_source_pin=stamp(__file__),
        fixed_order_single_descriptive_observation=True,overall_performance_review_complete=False,resource_admission=False,
        official_verdict=None,seal=None,receipt=None)


if __name__ == "__main__":
    result = verify()
    raw = (json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
    with (HERE/"verification.json").open("xb") as stream: stream.write(raw)
    print(json.dumps({k:result[k] for k in ("authority","cases","selective_calls","descriptions","native_calls","all_files_hash_matched","postcheck_wall_seconds")},sort_keys=True))
