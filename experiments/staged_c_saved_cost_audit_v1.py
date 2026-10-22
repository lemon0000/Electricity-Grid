"""Read-only accounting of B1-B3 saved evidence; no simulation or solver imports."""
import time

START = time.perf_counter()
BUDGET_ACTIVE = False

import ast
import hashlib
from importlib.metadata import distribution, version
import json
from pathlib import Path
import platform
import sys

import psutil

ROOT = Path(__file__).resolve().parents[1]
BASE = "results/tables/staged_deliverability_{}_v1_non_authoritative/attempt_01"
OUTPUT = ROOT / "results/tables/staged_deliverability_c_v1_non_authoritative/saved_audit_01"
PLAN = "docs/plan/staged_deliverability_c_dag_and_cost_review_v1.md"
LIMITS = dict(wall_seconds=60, rss_bytes=512 * 1024**2, input_bytes=32 * 1024**2,
              single_bytes=8 * 1024**2, files=250, output_bytes=4 * 1024**2)
CASES = ("on_time_early", "on_time_late", "delayed_early")
PROBES = ("missing_input", "network_unresolved", "save_before_publish", "save_after_publish")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def guard():
    if not BUDGET_ACTIVE:
        return
    require(time.perf_counter() - START <= LIMITS["wall_seconds"], "audit wall limit")
    require(psutil.Process().memory_info().rss <= LIMITS["rss_bytes"], "audit RSS limit")


def blob(path):
    guard()
    require(path.is_file() and not path.is_symlink(), "nonregular input: " + str(path))
    require(path.stat().st_size <= LIMITS["single_bytes"], "input size limit")
    data = path.read_bytes()
    require(len(data) <= LIMITS["single_bytes"], "input grew beyond limit")
    return data


def stamp(path):
    data = blob(path)
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def read(path):
    return json.loads(blob(path).decode("utf-8"))


def inventory(root):
    result = {}
    for package in ("b1", "b2", "b3"):
        folder = root / BASE.format(package)
        require(folder.is_dir() and not folder.is_symlink(), "missing saved package")
        for path in sorted(folder.rglob("*")):
            require(not path.is_symlink(), "symlink in saved package")
            if path.is_file():
                result[path.relative_to(root).as_posix()] = stamp(path)
                require(len(result) <= LIMITS["files"], "input file count limit")
                require(sum(v["bytes"] for v in result.values()) <= LIMITS["input_bytes"],
                        "aggregate input size limit")
    return result


def check_completion(root, folder, snapshot):
    saved = read(folder / "completion.json")
    require(saved["status"] == "development_diagnostic_completed"
            and saved["authority"] == "DRAFT_NONAUTHORITATIVE", "invalid saved completion")
    require(not (folder / "failure.json").exists(), "saved package has failure marker")
    require(saved["artifact_bytes_before_completion"] == sum(v["bytes"] for v in saved["artifacts"].values()),
            "saved inventory byte sum differs")
    for name, expected in saved["artifacts"].items():
        path = folder / name
        require(not Path(name).is_absolute() and ".." not in Path(name).parts, "invalid saved path")
        require(snapshot.get(path.relative_to(root).as_posix()) == expected,
                "saved artifact differs: " + name)
    allowed = set(saved["artifacts"]) | {"completion.json", "validation_report.md", "verification.json"}
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
    require(actual == allowed, "unexpected/missing saved supplemental or artifact")
    return len(saved["artifacts"])


def point_count(row):
    """Count compute roles once: the normal scenario aliases contract.normal."""
    contract = row["contract"]
    total = int(contract["normal"] is not None)
    for scenario in contract["scenarios"]:
        if scenario["outages"]:
            total += int(scenario["firm_point"] is not None)
            total += int(scenario["post_call_point"] is not None)
        else:
            require(scenario["firm_point"] is None
                    and scenario["post_call_point"] == contract["normal"], "normal point alias differs")
    return total + int(row["reference_point"] is not None) + int(row["actual_point"] is not None)


def work(state):
    rows = state["records"]
    return dict(pypower_flows=sum(point_count(r) for r in rows), network_attempts=len(rows),
                business_steps=sum(r["proposal"] is not None for r in rows))


def attempted_state(child):
    state = dict(child["state"], records=list(child["state"]["records"]))
    candidate = (child["summary"]["pending"] or {}).get("b2_candidate_record")
    if candidate is not None:
        state["records"].append(candidate)
        state["stopped"] = True
    return state


def recorded_expected(root):
    tree = ast.parse(blob(root / "experiments/staged_termination_b3_development_v1.py"))
    call = next(n.value for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "EXPECTED" for t in n.targets))
    require(isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
            and call.func.id == "dict" and not call.args, "saved runner counter schema differs")
    return {k.arg: ast.literal_eval(k.value) for k in call.keywords}


def public_case_shape():
    path = Path(distribution("PYPOWER").locate_file("pypower/case24_ieee_rts.py"))
    tree = ast.parse(blob(path))
    shapes = {n.targets[0].slice.value: len(n.value.args[0].elts) for n in ast.walk(tree)
              if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Subscript)
              and isinstance(n.targets[0].slice, ast.Constant)
              and n.targets[0].slice.value in ("bus", "gen", "branch") and isinstance(n.value, ast.Call)}
    require(shapes == dict(bus=24, gen=33, branch=38), "bundled public case shape differs")
    return dict(path=str(path), source=stamp(path), array_rows=shapes, method="AST only; case not executed")


def probe_work(saved, probe):
    before_reason, reopened_reason, length = {
        "missing_input": ("missing_input", "missing_input", 4),
        "network_unresolved": ("network_unresolved", "network_unresolved", 3),
        "save_before_publish": ("persistence_failure", "incomplete_publication", 4),
        "save_after_publish": ("commit_outcome_unknown", None, 4),
    }[probe]
    before = saved["before_reopen"]
    state, reopened = before["last_verified_state"], saved["reopened_state"]
    require(before["termination_reason"] == before_reason and saved["reopened_reason"] == reopened_reason,
            "probe recovery reason differs: " + probe)
    require(len(state["records"]) == length, "probe accepted prefix length differs")
    pending = before["pending"] or {}
    candidate = pending.get("b2_candidate_record")
    require((candidate is not None) == (probe != "missing_input"), "probe candidate presence differs")
    if candidate is not None:
        role, adoption, has_state = {
            "network_unresolved": ("network_attempt", "not_adopted", False),
            "save_before_publish": ("step", "not_adopted", True),
            "save_after_publish": ("step", "unknown", True),
        }[probe]
        require(pending["role"] == role and pending["adoption"] == adoption
                and (pending.get("b2_candidate_state") is not None) == has_state, "probe pending disposition differs")
    else:
        require(before["pending"] is None, "missing-input probe gained pending candidate evidence")
    if probe == "save_after_publish":
        require(reopened == pending["b2_candidate_state"]
                and reopened["records"] == state["records"] + [candidate], "published candidate adoption differs")
    else:
        require(reopened == state, "unaccepted candidate entered recovered state")
    if candidate is not None:
        require(candidate["committed"] is (probe != "network_unresolved"), "probe candidate status differs")
    initial, replay = work(state), work(reopened)
    extra = work(dict(records=[candidate])) if candidate is not None else dict.fromkeys(initial, 0)
    return {k: initial[k] + replay[k] + extra[k] for k in initial}


def derive_work(root):
    folder = root / BASE.format("b3")
    groups = {}
    for case in CASES:
        reference = read(folder / (case + "_reference.json"))
        child = read(folder / (case + "_terminal.json"))
        require(reference["state"] == attempted_state(child)
                and reference["audit"] == child["audit"]["network_audit"],
                "saved parent/child science differs")
        item = work(reference["state"])
        require(all(child["counts"][k] == v for k, v in item.items()), "child work differs")
        groups[case] = {k: 2 * v for k, v in item.items()}
    for probe in PROBES:
        saved = read(folder / (probe + "_probe.json"))
        groups[probe] = probe_work(saved, probe)
    totals = {k: sum(g[k] for g in groups.values()) for k in next(iter(groups.values()))}
    report = read(folder / "report.json")
    expected = recorded_expected(root)
    require(all(report["counts"][k] == v for k, v in expected.items()), "registered B3 counts differ")
    require(all(report["counts"][k] == v for k, v in totals.items()), "independently derived work differs")
    return dict(groups=groups, derived_totals=totals, registered_counts=expected,
                recorded_observations=report["counts"])


def structural_budget(hours, outages, reopen_lengths=(), trajectories=1):
    """Arithmetic for successful B2-shaped paths only; never a wall-time estimate."""
    values = (hours, outages, trajectories, *reopen_lengths)
    require(all(type(v) is int and v >= 0 for v in values) and trajectories > 0,
            "nonnegative integer dimensions required")
    require(all(v <= hours for v in reopen_lengths), "reopen exceeds accepted horizon")
    weighted = hours + sum(reopen_lengths)
    return dict(network_hour_visits=trajectories * weighted,
                point_compute_roles=trajectories * (3 + 2 * outages) * weighted,
                initial_digest_record_visits=trajectories * hours**2,
                reopen_after_digest_record_visits=trajectories * sum(n * (n + 1) // 2 for n in reopen_lengths),
                wall_seconds=None, within_existing_horizon_and_outage_limits=hours <= 10 and outages == 2)


def verify_inputs(root, bindings=None):
    before = inventory(root)
    reports = {k: read(root / BASE.format(k) / "report.json") for k in ("b1", "b2", "b3")}
    fp = reports["b3"]["fingerprints"]
    pins = dict(fp["repository_sha256"])
    for source in (reports["b1"]["source_sha256"], reports["b2"]["fingerprints"]["repository_sha256"],
                   fp["reused_b1_source_sha256"]):
        for name, sha in source.items():
            name = name.replace("\\", "/")
            require(name not in pins or pins[name] == sha, "conflicting saved source pin")
            pins[name] = sha
    sources = {name: stamp(root / name) for name in pins}
    require(all(sources[n]["sha256"] == sha for n, sha in pins.items()), "bound repository source drift")
    external = {name: stamp(Path(item["path"])) for name, item in fp["external_selected"].items()}
    require(all(external[n]["sha256"] == item["sha256"] for n, item in fp["external_selected"].items()),
            "selected external source drift")
    public_case = public_case_shape()
    combined = dict(before, **sources)
    combined.update({"external:" + n: s for n, s in external.items()})
    combined["public_case"] = public_case["source"]
    combined.update(bindings or {})
    require(len(combined) <= LIMITS["files"]
            and sum(v["bytes"] for v in combined.values()) <= LIMITS["input_bytes"], "bound input scope limit")
    versions = {name: version(name) for name in fp["versions"]}
    require(versions == fp["versions"] and sys.version == fp["python"]
            and sys.executable == fp["executable"] and platform.platform() == fp["platform"],
            "selected environment differs; old timings cannot be reused")
    completed = {k: check_completion(root, root / BASE.format(k), before) for k in ("b2", "b3")}
    counts = derive_work(root)
    require(before == inventory(root), "B1-B3 saved bytes changed during audit")
    require(sources == {n: stamp(root / n) for n in pins}, "bound source changed during audit")
    require(external == {n: stamp(Path(v["path"])) for n, v in fp["external_selected"].items()},
            "selected dependency changed during audit")
    require(public_case["source"] == stamp(Path(public_case["path"])), "public case source changed during audit")
    return dict(saved_files=before, repository_pins=sources, selected_external=external,
                public_case_static_source=public_case, versions=versions, completion_artifact_counts=completed, counts=counts,
                b1_b2_b3_bytes_preserved=True, bookend_scope="observable byte snapshots; no lock or ABA guarantee")


def save(path, value):
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")
    require(len(data) <= LIMITS["output_bytes"], "audit output size limit")
    with path.open("xb") as stream:
        stream.write(data)


def main():
    global BUDGET_ACTIVE
    OUTPUT.mkdir(parents=True, exist_ok=False)
    BUDGET_ACTIVE = True
    try:
        bindings = {n: stamp(ROOT / n) for n in (PLAN, "experiments/staged_c_saved_cost_audit_v1.py",
                                                "tests/test_staged_c_saved_cost_audit_v1.py")}
        save(OUTPUT / "start.json", dict(authority="DRAFT_NONAUTHORITATIVE", limits=LIMITS,
             bindings=bindings, executable=sys.executable, python=sys.version, platform=platform.platform()))
        result = verify_inputs(ROOT, bindings)
        result.update(status="saved_evidence_audit_completed", authority="DRAFT_NONAUTHORITATIVE",
                      scope="saved_evidence_and_structural_accounting_only",
                      new_pypower_calls=0, new_solver_calls=0, new_children=0,
                      main_experiment_performance_review_complete=False,
                      structural_examples={str(t): structural_budget(t, 2, (t,)) for t in (10, 24, 192)},
                      elapsed_before_report_seconds=time.perf_counter() - START,
                      observed_rss_bytes=psutil.Process().memory_info().rss)
        guard()
        require(bindings == {n: stamp(ROOT / n) for n in bindings}, "audit implementation/plan drift")
        save(OUTPUT / "audit.json", result)
        guard()
        print(json.dumps(dict(status="saved_audit_completed", elapsed_seconds=time.perf_counter() - START,
                              saved_files=len(result["saved_files"]), derived=result["counts"]["derived_totals"])))
    except BaseException as error:
        save(OUTPUT / "failure.json", dict(status="saved_audit_failed", error=repr(error),
             elapsed_seconds=time.perf_counter() - START))
        raise
    finally:
        BUDGET_ACTIVE = False


if __name__ == "__main__":
    main()
