"""Supplement the preserved first readback with exact sets and per-case roles."""
from collections import Counter
import json
from pathlib import Path
import runpy
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT))


def verify():
    started = time.perf_counter()
    old = runpy.run_path(str(HERE/"postcheck.py"))
    result = old["verify"]()
    read, stamp, counts, duration = (old[key] for key in ("read","stamp","counts","duration"))
    from experiments import staged_rts24_append_cost_probe_v1 as p
    before = old["inventory"](p.OUTPUT)
    c, v, report, wt = (read(p.OUTPUT/name) for name in ("completion.json","controller_verification.json","report.json","worker_timing.json"))
    last = {"controller_verification.json","controller_timings.json"}
    late = {"completion.json","launcher.json","launcher.stdout.log","launcher.stderr.log","worker.stdout.log","worker.stderr.log"}
    assert c["files"] == {name:pin for name,pin in before.items() if name not in last|late}
    assert v["files"] == {name:pin for name,pin in before.items() if name not in last}
    assert v["timing_excludes"] == "this_verification_publication_final_scan_and_console_exit"
    duration(v["launcher_wall_through_readback"])
    assert v["launcher_wall_through_readback"] >= v["readback_seconds"]
    duration(wt["elapsed"],270)
    for record in (report,wt):
        assert set(record["group_seconds"]) <= set(p.GROUPS)
        for group,value in record["group_seconds"].items(): duration(value,p.GROUPS[group])
        for phase in record["phases"]:
            for value in phase["inclusive_seconds"].values(): duration(value)
    for case in p.CASES:
        if case["kind"] == "success":
            expected = (13,18,13,5,0,0) if case["method"] == "instantaneous" else (13,44,13,5,13,13)
            parent_expected = expected
        elif case["kind"] == "unknown": expected,parent_expected = (5,15,5,0,5,5),(3,9,3,0,3,3)
        elif case["kind"] == "deletion": expected,parent_expected = (0,0,0,0,0,0),(3,9,3,0,3,3)
        else: expected = parent_expected = (2,6,2,0,2,2)
        child = read(p.OUTPUT/case["name"]/"fresh_observations.json")
        counts(child["counts"],expected)
        parent = Counter()
        for phase in wt["phases"]:
            if phase["group"] == "parent" and phase["stage"].startswith(case["name"]+"_"): parent.update(phase["counts"])
        counts(parent,parent_expected)
    assert old["inventory"](p.OUTPUT) == before
    first = read(HERE/"verification.json")
    assert first["files"] == result["files"] and first["preparation_files"] == result["preparation_files"]
    assert first["postcheck_source_pin"] == stamp(HERE/"postcheck.py")
    result.update(exact_core_and_controller_maps=True,per_case_parent_and_fresh_roles_checked=True,
        supplementary_timing_checks=True,first_verification_pin=stamp(HERE/"verification.json"),
        supplementary_postcheck_pin=stamp(__file__),postcheck_wall_seconds=time.perf_counter()-started)
    return result


if __name__ == "__main__":
    result = verify()
    with (HERE/"verification_v2.json").open("xb") as stream:
        stream.write((json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode())
    print(json.dumps({key:result[key] for key in ("all_files_hash_matched","exact_core_and_controller_maps","per_case_parent_and_fresh_roles_checked","supplementary_timing_checks","postcheck_wall_seconds")},sort_keys=True))
