"""Independent metadata/artifact readback; never imports scientific code."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
AUDIT_SHA = "0644a06315612eaab1cf855be437d230a919fb8af64b742aeb07e52df13e26bd"


def stamp(path):
    data = Path(path).read_bytes()
    return dict(bytes=len(data),sha256=sha256(data).hexdigest())


def read(path): return json.loads(Path(path).read_bytes())


def verify():
    started = time.perf_counter()
    audit_path = BASE/"audit_01/audit.json"
    before = stamp(audit_path)
    assert before["sha256"] == AUDIT_SHA
    audit = read(audit_path)
    assert audit["authority"] == "DRAFT_NONAUTHORITATIVE"
    assert audit["source_and_artifact_bookends"] and audit["static_source_bytes_revalidated"]
    assert audit["environment_revalidated"] is False
    assert audit["native_calls_in_this_audit"] == audit["scientific_compiler_calls_in_this_audit"] == audit["model_builds_in_this_audit"] == 0
    assert all(audit[k] is False for k in ("p1_attempt_created","overall_performance_review_complete","resource_admission","formal_result"))
    assert all(audit[k] is None for k in ("official_verdict","seal","receipt"))
    assert audit["logical_input_reads"] == 1364 and audit["logical_input_bytes"] == 8147368
    assert 0 <= audit["metadata_audit_wall_seconds"] <= 20
    assert audit["metadata_interpreter"]["no_user_site"] and audit["metadata_interpreter"]["dont_write_bytecode"]
    pins = audit["input_pins"]
    assert len(pins) == 677
    for _ in range(2):
        for name,pin in pins.items():
            path = ROOT/name
            assert time.perf_counter()-started <= 20 and path.is_file() and not path.is_symlink()
            assert path.resolve().is_relative_to(ROOT) and path.stat().st_size <= 2*1024**2
            assert stamp(path) == pin
    native_name = "results/tables/staged_rts24_native_v1_non_authoritative/registration_v1.json"
    native = read(ROOT/native_name)
    assert pins[native_name]["sha256"] == "23577e5d79d3284a260decbfe2258a3103252617953452565a9feeffafbd94e2"
    assert native["native_authorized"] is False and not (ROOT/native_name).parent.joinpath("p1_01").exists()
    roles = ("reference_base_P0","reference_raw_need","recovery_min_meter","recovery_max_meter")
    hourly = [[row["role"] for row in native["schedule"] if row["hour"] == h and row["role"] in roles] for h in range(-2,3)]
    journal = []
    for i in range(5):
        for _ in range(2): journal.extend(range(i)); journal.append(i)
        journal.extend(range(i+1))
    journal.extend(range(5)); journal.extend(range(5))
    one = list(range(5))
    phases = dict(registration_preparation=one,launcher_preflight=one,worker=one+one+journal+journal,
        point_children=[],fresh=journal)
    p1 = audit["p1"]
    total = []
    for name,visits in phases.items():
        counts = Counter(role for hour in visits for role in hourly[hour])
        expected = p1["phases"][name]["selective"]
        assert expected["calls"] == len(visits) and expected["descriptions"] == sum(counts.values())
        assert expected["roles"] == {role:counts[role] for role in roles}
        assert expected["hour_calls"] == [visits.count(i) for i in range(5)]
        total.extend(visits)
    assert len(journal) == 55 and len(total) == 185
    descriptors = sum(len(hourly[i]) for i in total)
    assert descriptors == 583 and p1["selective_total_including_historical_registration"]["descriptions"] == descriptors
    assert p1["selective_execution_only"]["calls"] == 180 and p1["selective_execution_only"]["descriptions"] == 567
    assert p1["full_calls_including_registration"] == 8 and p1["full_descriptions_including_registration"] == 4*sum(139+len(hourly[i]) for i in (3,4)) == 1140
    assert p1["numeric_compile"] == p1["pyomo_build"] == sum(row["numeric_compile"] for row in p1["phases"].values()) == 124
    assert p1["imports"] == sum(row["imports"] for row in p1["phases"].values()) == 62
    assert p1["fingerprints_calls"] == sum(row["fingerprints"] for row in p1["phases"].values()) == 131
    assert p1["preserve_calls"] == sum(row["preserve"] for row in p1["phases"].values()) == 5
    assert p1["reopens"] == 2 and p1["audit_row_visits"] == sum(p1["audit_row_visits_per_hour"]) == 135
    assert p1["audit_execution_calls"] == dict(worker=35,fresh=17,total=52)
    assert p1["native_measured"] is False and p1["wall_estimate_seconds"] is None
    caps = audit["public_request_caps"]
    assert caps["D_points"] is caps["E_holdout_paths"] is caps["total_resource_estimate"] is None
    assert caps["three_method_actual_representative"]["per_method"] == [21,41,41]
    for name,expected in (("P2_two_contract_frames",(319,160,159)),("single_method_all_ten_frames",(1431,720,711)),("three_methods_all_ten_frames",(4273,2160,2113))):
        row = caps[name]
        assert tuple(row[k] for k in ("total","qp","lp")) == expected
        assert row["total"] == row["actual"]+row["contract"] == row["qp"]+row["lp"]
        assert row["runtime_implemented"] is False and row["wall_estimate_seconds"] is None
    dev = read(BASE/"development_checks_01/development_checks.json")
    assert dev["distinct_ordinary_checks"] == 24 and all(stamp(ROOT/name) == pin for name,pin in dev["source_pins"].items())
    assert all(stamp(BASE/"development_checks_01"/name) == pin for name,pin in dev["artifacts"].items())
    for item in dev["checks"]:
        raw = (BASE/"development_checks_01"/item["log"]).read_bytes()
        text = raw.decode("utf-16" if raw.startswith(b"\xff\xfe") else "utf-8-sig")
        assert item["exit_code"] == 0 and str(item["passed"])+" passed" in text
    assert stamp(audit_path) == before
    return dict(authority="DRAFT_NONAUTHORITATIVE",audit_pin=before,input_files_checked=len(pins),input_hash_passes=2,
        independent_selective_calls=len(total),independent_descriptions=descriptors,ordinary_checks_distinct=24,
        p1_attempt_created=False,native_calls=0,source_and_artifact_hashes_match=True,
        postcheck_wall_seconds=time.perf_counter()-started,postcheck_source_pin=stamp(__file__),
        overall_performance_review_complete=False,resource_admission=False,official_verdict=None,seal=None,receipt=None)


if __name__ == "__main__":
    result = verify()
    with (BASE/"verification_01.json").open("xb") as stream:
        stream.write((json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode())
    print(json.dumps(result,sort_keys=True))
