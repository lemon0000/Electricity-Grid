"""One registered analytic, no-solver journal integration probe; never public results."""
import time
START = time.perf_counter()
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).absolute().parents[1]
sys.path.insert(0, str(ROOT))
from src import staged_rts24_development_v1 as c
from src import staged_rts24_causal_v2 as policy
from src import staged_rts24_causal_audit_v2 as independent
from src import staged_rts24_reference_queries_v1 as selective
from src import staged_rts24_journal_v1 as journal
from src import staged_rts24_evidence_store_v1 as codec
from src.staged_rts24_evidence_store_v1 import canonical, sha, read_bytes, parse, pack, require
from experiments.staged_rts24_causal_examples_v1 import analytic_fixture, analytic_hour, analytic_actual
import experiments.staged_rts24_build_diagnostic_v1 as prior

OUTPUT = ROOT/"results/tables/staged_rts24_journal_v1_non_authoritative/attempt_01"
SOURCES = (
    "src/staged_rts24_reference_queries_v1.py", "src/staged_rts24_causal_v2.py", "src/staged_rts24_causal_audit_v2.py",
    "src/staged_rts24_evidence_store_v1.py", "src/staged_rts24_journal_v1.py",
    "experiments/staged_rts24_journal_diagnostic_v1.py", "experiments/staged_rts24_journal_launcher_v1.py",
    "tests/test_staged_rts24_reference_queries_v1.py", "tests/test_staged_rts24_journal_v1.py",
    "docs/model_spec/staged_rts24_journal_development_v1.md", "docs/plan/staged_deliverability_c_journal_probe_contract_v1.md",
    "experiments/staged_rts24_causal_examples_v1.py",
    "experiments/staged_rts24_build_diagnostic_v1.py",
)


def write(path, value):
    with path.open("xb") as stream:
        stream.write(canonical(c.plain(value)))
        stream.flush()


def stamp(path):
    data = read_bytes(path, allow_links=True)
    return dict(bytes=len(data), sha256=sha(data))


def bindings():
    return dict(runtime=journal.runtime_identity(), sources={name: stamp(ROOT/name) for name in SOURCES},
                psutil=prior.version("psutil"))


def preservation():
    old = prior.preserved()
    build = json.loads((prior.OUTPUT/"report.json").read_text(encoding="utf-8"))
    require(prior.fingerprints() == build["fingerprints"], "old build source/runtime changed")
    prior.verify_completion(prior.OUTPUT, ("launcher.json", "postcheck.py", "verification.json", "preseal_findings.json", "validation_report.md"))
    verified = json.loads((ROOT/"results/tables/staged_rts24_causal_v1_non_authoritative/development_checks_01/verification.json").read_text(encoding="utf-8"))
    require(all(stamp(ROOT/name) == pin for name, pin in verified["new_bound_sources"].items()), "old causal bound sources changed")
    original_c = json.loads((ROOT/"results/tables/staged_deliverability_c_v1_non_authoritative/saved_audit_01/start.json").read_text(encoding="utf-8"))["bindings"]
    require(all(stamp(ROOT/name) == pin for name, pin in original_c.items()), "old C bound sources changed")
    return dict(b1_b3_files=old["files"], repository_pins=old["repository_pins"], unique=old["unique_files"],
                selected_external=old["selected_external"], old_c_bindings=original_c,
                public_build_checked=True, causal_sources=len(verified["new_bound_sources"]))


def guards_and_counters():
    counts = Counter()
    def forbidden(*args, **kwargs):
        counts["solver_or_native_requests"] += 1
        raise RuntimeError("solver/native request prohibited by journal probe")
    for name in ("pyomo.environ", "src.grid.dc_opf", "src.grid.network_grid_need", "src.grid.scopf"):
        module = __import__(name, fromlist=["SolverFactory"])
        module.SolverFactory = forbidden
    import src.grid.rts_gmlc_scuc as scuc
    scuc.Highs = forbidden
    old_full, old_selective = c.hour_requests, selective.reference_requests
    def full(*args, **kwargs):
        result = old_full(*args, **kwargs)
        counts["full_compiler_calls"] += 1
        counts["full_descriptions"] += len(result["requests"])
        counts.update("full_role_"+r.role for r in result["requests"])
        return result
    def selected(*args, **kwargs):
        result = old_selective(*args, **kwargs)
        counts["selective_compiler_calls"] += 1
        counts["selective_descriptions"] += len(result["requests"])
        counts.update("selective_role_"+r.role for r in result["requests"])
        return result
    c.hour_requests = full
    selective.reference_requests = policy.reference_requests = independent.reference_requests = journal.reference_requests = selected
    old_read, old_publish = codec.read_bytes, codec.publish
    def read(*args, **kwargs):
        raw = old_read(*args, **kwargs)
        counts["bounded_file_reads"] += 1
        counts["bounded_file_read_bytes"] += len(raw)
        return raw
    def publication(path, raw, hook=None):
        prefix = "cas" if Path(path).parent.name == "objects" else "journal"
        counts[prefix+"_publish_attempts"] += 1
        def stages(phase, target):
            counts[prefix+"_"+phase] += 1
            if hook is not None: hook(phase, target)
        result = old_publish(path, raw, stages)
        counts[prefix+"_publish_returned"] += 1
        counts[prefix+"_published_bytes"] += len(raw)
        return result
    codec.read_bytes = journal.read_bytes = read
    codec.publish = journal.publish = publication
    return counts


def metrics(result):
    return dict(state_sha=result["state_sha"], state_cas_sha=pack(result["state"])[0], summary=c.plain(result["summary"]),
        independent_audit=c.plain(result["independent_audit"]), scientific_outcome=result["scientific_outcome"],
        publication_outcome=result["publication_outcome"], state_certainty=result["state_certainty"],
        terminal_entry_present=result["terminal_entry_present"], final_entries=result["final_entries"],
        pending_terminal=result["pending_terminal_checkpoint"] is not None,
        unaccepted_status=(result["unaccepted_attempt"].get("status", "saved_unresolved_attempt") if result["unaccepted_attempt"] else None),
        pending_cas=len(result["pending_cas_objects"]), unreferenced_cas=len(result["unreferenced_final_cas_objects"]),
        resume_permitted=result["resume_permitted"])


def child(case):
    counts = guards_and_counters()
    binding = parse(read_bytes(case/"trusted_binding.json"))
    method = case.name
    fixture = analytic_fixture(late=True)
    result = journal.reopen(case/"journal", fixture, "on_time", "late", method, binding)
    require(counts["solver_or_native_requests"] == counts["full_compiler_calls"] == 0, "fresh generated new evidence")
    write(case/"fresh.json", dict(result=metrics(result), counts=dict(counts), elapsed=time.perf_counter()-START))


def process_snapshot():
    import psutil
    result = []
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            item = process.info
            name = item["name"] or ""
            if any(word in name.lower() for word in ("python", "gurobi", "cplex", "highs", "ipopt")):
                command = item["cmdline"] or []
                result.append(dict(pid=item["pid"], name=name, argv_sha256=sha(canonical(command)),
                    mentions_repository=str(ROOT).casefold() in " ".join(command).casefold()))
        except (psutil.NoSuchProcess, psutil.AccessDenied): continue
    return result


def main():
    require(OUTPUT.is_dir() and {p.name for p in OUTPUT.iterdir()} == {"launcher_start.json", "stdout.log", "stderr.log"}, "one-shot launcher directory required")
    before, old_before = bindings(), preservation()
    import psutil
    snapshot = dict(git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        git_branch=subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT).decode().strip(),
        git_status=subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=ROOT).decode("utf-8"),
        related_processes=process_snapshot(), runner_pid=psutil.Process().pid)
    write(OUTPUT/"start.json", dict(authority="DRAFT_NONAUTHORITATIVE", bindings=before, preserved=old_before,
        workspace_snapshot=snapshot,
        simulated_hours_per_success_case=5, methods=c.METHODS, actual_network="explicit_analytic_three_bus",
        public_numeric_results=False, solver_calls_allowed=0))
    counts = guards_and_counters()
    stages, baseline, reports = [], {}, {}
    def event(name, **values):
        with (OUTPUT/"events.jsonl").open("ab") as stream:
            stream.write(canonical(dict(stage=name, elapsed=time.perf_counter()-START, **values))+b"\n")
            stream.flush()
        print(name, flush=True)
    def phase(name, action):
        start, old = time.perf_counter(), counts.copy()
        result = action()
        stages.append(dict(stage=name, wall_seconds=time.perf_counter()-start, counts=dict(counts-old)))
        event(name)
        return result
    fixture = analytic_fixture(late=True)
    def reference(method):
        state = policy.initialize_execution(fixture, "on_time", "late", method)
        packets = []
        for hour in range(5):
            evidence = analytic_hour(fixture, state)
            prepared = policy.prepare_hour(fixture, state, evidence)
            proposal = policy.propose_hour(state, prepared)
            actual = analytic_actual(prepared, proposal)
            state = policy.accept_hour(fixture, state, prepared, proposal, actual)
            packets.append((evidence, actual))
            event("reference_hour", method=method, hour=hour)
        return state, packets, policy.execution_summary(fixture, state), independent.audit_execution(fixture, state)
    for method in c.METHODS: baseline[method] = phase("reference_"+method, lambda m=method: reference(m))
    for method in c.METHODS:
        case = OUTPUT/method
        case.mkdir(exist_ok=False)
        def saved():
            session = journal.create_session(case/"journal", fixture, "on_time", "late", method)
            for hour, (evidence, actual) in enumerate(baseline[method][1]):
                item = journal.begin_step(session, evidence)
                session = journal.commit_step(session, item, actual)
                require(not session.closed, "unexpected journal failure")
                event("saved_hour", method=method, hour=hour)
            session = journal.finish(session)
            require(session.closed and session.scientific_outcome == "complete" and session.state == baseline[method][0], "saved reference state differs")
            write(case/"trusted_binding.json", journal.trusted_binding(session))
            return session
        session = phase("save_"+method, saved)
        child_start = time.perf_counter()
        completed = subprocess.run([sys.executable, "-B", str(Path(__file__).absolute()), "--child", str(case)],
            cwd=ROOT, capture_output=True, timeout=45)
        write(case/"child_launch.json", dict(exit_code=completed.returncode, outer_seconds=time.perf_counter()-child_start,
            stdout=completed.stdout.decode("utf-8", "replace"), stderr=completed.stderr.decode("utf-8", "replace")))
        require(completed.returncode == 0, "fresh child failed")
        fresh = parse(read_bytes(case/"fresh.json"))
        require(fresh["result"]["state_sha"] == c.digest(session.state) and fresh["result"]["state_cas_sha"] == pack(session.state)[0]
                and fresh["result"]["summary"] == c.plain(baseline[method][2])
                and fresh["result"]["independent_audit"] == c.plain(baseline[method][3]), "fresh full typed state/audit differs")
        reports[method] = fresh
        event("fresh_"+method)
    probes = {}
    for name in ("reference_unresolved", "actual_unresolved", "prepublish", "postpublish", "missing_input"):
        case = OUTPUT/name
        case.mkdir(exist_ok=False)
        def failure_case():
            session = journal.create_session(case/"journal", fixture, "on_time", "late", "full_temporal")
            packets = baseline["full_temporal"][1]
            if name == "reference_unresolved":
                try: journal.begin_step(session, None)
                except journal.SessionClosed as error: session = error.session
            elif name == "missing_input":
                for evidence, actual in packets[:2]: session = journal.commit_step(session, journal.begin_step(session, evidence), actual)
                session = journal.finish(session)
            else:
                item = journal.begin_step(session, packets[0][0])
                def fault(phase, path):
                    if path.name.startswith("entry_") and phase == ("before_rename" if name == "prepublish" else "after_rename"):
                        raise OSError("registered local publication probe")
                session = journal.commit_step(session, item, None if name == "actual_unresolved" else packets[0][1],
                    hook=fault if name in ("prepublish", "postpublish") else None)
            require(session.closed, "failure/missing-input case did not close")
            trusted = journal.trusted_binding(session)
            write(case/"trusted_binding.json", trusted)
            result = journal.reopen(case/"journal", fixture, "on_time", "late", "full_temporal", trusted)
            expected = {"reference_unresolved": (0, "committed"), "actual_unresolved": (0, "committed"),
                        "prepublish": (0, "not_published"), "postpublish": (1, "committed"), "missing_input": (2, "committed")}[name]
            require((len(result["state"].records), result["publication_outcome"]) == expected, "failure adjudication differs")
            if name == "missing_input": require(result["summary"]["primary_right_censored"] and len(result["summary"]["tasks"]) == 2, "censor differs")
            write(case/"replay.json", metrics(result))
            return metrics(result)
        probes[name] = phase(name, failure_case)
    after, old_after = bindings(), preservation()
    require(before == after and old_before == old_after and counts["solver_or_native_requests"] == 0, "bookend changed or solver requested")
    require(counts["full_compiler_calls"] == 15, "provider full compiler count differs")
    require(counts["full_descriptions"] == 83 and counts["selective_compiler_calls"] == 335
            and counts["selective_descriptions"] == 897, "parent descriptor accounting differs")
    require(sum(item["counts"]["selective_compiler_calls"] for item in reports.values()) == 165
            and sum(item["counts"]["selective_descriptions"] for item in reports.values()) == 427, "fresh descriptor accounting differs")
    expected_failures = {"reference_unresolved": (4, 12), "actual_unresolved": (6, 18), "prepublish": (6, 18),
                         "postpublish": (8, 24), "missing_input": (26, 88)}
    for stage in stages:
        name, values = stage["stage"], stage["counts"]
        if name in expected_failures:
            require((values["selective_compiler_calls"], values["selective_descriptions"]) == expected_failures[name], "failure stage accounting differs")
        elif name.startswith("reference_"):
            method = name.removeprefix("reference_")
            require((values["selective_compiler_calls"], values["selective_descriptions"]) == (40, 50 if method == "instantaneous" else 130), "reference stage accounting differs")
        elif name.startswith("save_"):
            method = name.removeprefix("save_")
            require((values["selective_compiler_calls"], values["selective_descriptions"]) == (55, 69 if method == "instantaneous" else 179), "save stage accounting differs")
    combined = counts.copy()
    for method, item in reports.items():
        values = item["counts"]
        require((values["selective_compiler_calls"], values["selective_descriptions"]) == (55, 69 if method == "instantaneous" else 179), "fresh stage accounting differs")
        combined.update(values)
    require({k.removeprefix("selective_role_"): v for k, v in combined.items() if k.startswith("selective_role_")} ==
        dict(reference_base_P0=500, reference_raw_need=124, recovery_min_meter=350, recovery_max_meter=350), "selective role accounting differs")
    require({k.removeprefix("full_role_"): v for k, v in combined.items() if k.startswith("full_role_")} ==
        dict(normal_contract_C=15, fault_firm_F=15, fault_raw_need=15, reference_base_P0=15, reference_raw_need=3,
             recovery_min_meter=10, recovery_max_meter=10), "provider role accounting differs")
    report = dict(authority="DRAFT_NONAUTHORITATIVE", bindings=after, preserved=old_after, stages=stages,
        parent_counts=dict(counts), success_cases=reports, failure_probes=probes, elapsed=time.perf_counter()-START,
        limits=dict(public_numeric_results=False, C_D_E_resource_admission=False, overall_performance_review_complete=False,
                    rigorous_bound_certified=False, native_execution_authorized=False))
    event("report_bookend")
    write(OUTPUT/"report.json", report)
    excluded = {"launcher_start.json", "stdout.log", "stderr.log", "launcher.json", "completion.json"}
    manifest = {str(path.relative_to(OUTPUT)).replace("\\", "/"): stamp(path)
                for path in OUTPUT.rglob("*") if path.is_file() and str(path.relative_to(OUTPUT)) not in excluded}
    write(OUTPUT/"completion.json", dict(authority="DRAFT_NONAUTHORITATIVE", files=manifest,
        logical_bytes=sum(item["bytes"] for item in manifest.values()), manifest_files=len(manifest)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", type=Path)
    args = parser.parse_args()
    if args.child is not None: child(args.child)
    else: main()
