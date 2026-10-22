"""Registered two-hour saved-evidence CAS/root-retention diagnostic, no solvers."""
import time
START = time.perf_counter()
import argparse
from pathlib import Path
import subprocess
import sys
ROOT = Path(__file__).absolute().parents[1]
sys.path.insert(0, str(ROOT))
from src import staged_rts24_journal_v2 as journal
from src import staged_rts24_evidence_store_v1 as codec
from src import staged_rts24_development_v1 as c
from experiments import staged_rts24_journal_diagnostic_v1 as old
from experiments.staged_rts24_causal_examples_v1 import analytic_fixture

OUTPUT = ROOT/"results/tables/staged_rts24_journal_v2_non_authoritative/closure_probe_01"
SOURCES = ("src/staged_rts24_journal_v2.py", "tests/test_staged_rts24_journal_v2.py",
    "experiments/staged_rts24_journal_closure_diagnostic_v2.py", "experiments/staged_rts24_journal_closure_launcher_v2.py",
    "docs/model_spec/staged_rts24_journal_retention_v2.md", "docs/plan/staged_deliverability_c_journal_retention_probe_v2.md")


def bindings():
    result = dict(runtime=journal.runtime_identity(), sources={n: old.stamp(ROOT/n) for n in SOURCES}, old_sources=old.bindings(),
        old_completion=old.stamp(old.OUTPUT/"completion.json"), old_report=old.stamp(old.OUTPUT/"report.json"),
        old_inputs={role: old.stamp(old.OUTPUT/"full_temporal/journal"/name) for role, name in
            (("genesis", "genesis.json"), ("hour_0_entry", "entry_000001.json"), ("hour_1_entry", "entry_000002.json"))})
    codec.require(len(result["sources"]) == 6 and len(result["old_sources"]["sources"]) == 13
        and len(result["runtime"]["sources"]) == 28 and len(result["runtime"]["external"]) == 10
        and "src/staged_rts24_journal_v2.py" in result["runtime"]["sources"], "registered source closure differs")
    return result


def verify_prior():
    completion = codec.parse(codec.read_bytes(old.OUTPUT/"completion.json"))
    codec.require(all(old.stamp(old.OUTPUT/n) == pin for n, pin in completion["files"].items()), "old saved core changed")
    return old.preservation()


def guards():
    counts = old.guards_and_counters()
    journal.reference_requests = old.selective.reference_requests
    journal.read_bytes, journal.publish = codec.read_bytes, codec.publish
    return counts


def child():
    counts = guards()
    expected = codec.parse(codec.read_bytes(OUTPUT/"success/trusted_binding.json"))
    result = journal.reopen(OUTPUT/"success/journal", analytic_fixture(late=True), "on_time", "late", "full_temporal", expected)
    codec.require((counts["selective_compiler_calls"], counts["selective_descriptions"], counts["full_compiler_calls"], counts["solver_or_native_requests"]) == (13, 44, 0, 0), "fresh accounting differs")
    old.write(OUTPUT/"success/fresh.json", dict(result=old.metrics(result), counts=dict(counts), elapsed=time.perf_counter()-START))


def main():
    codec.require(OUTPUT.is_dir() and {p.name for p in OUTPUT.iterdir()} == {"launcher_start.json", "stdout.log", "stderr.log"}, "one-shot launcher required")
    before, preserved = bindings(), verify_prior()
    import psutil
    snapshot = dict(git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
        git_branch=subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT).decode().strip(),
        git_status=subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=ROOT).decode("utf-8"),
        related_processes=old.process_snapshot(), runner_pid=psutil.Process().pid)
    old.write(OUTPUT/"start.json", dict(authority="DRAFT_NONAUTHORITATIVE", bindings=before, preserved=preserved,
        workspace_snapshot=snapshot,
        simulated_hours=2, methods=["full_temporal"], new_evidence_generation=False, solver_calls_allowed=0))
    counts = guards()
    def event(stage):
        with (OUTPUT/"events.jsonl").open("ab") as stream:
            stream.write(codec.canonical(dict(stage=stage, elapsed=time.perf_counter()-START))+b"\n")
        print(stage, flush=True)
    old_root = old.OUTPUT/"full_temporal/journal"
    store = codec.EvidenceStore(old_root)
    rows, expected_state = [], None
    for i in (1, 2):
        entry = codec.parse(codec.read_bytes(old_root/f"entry_{i:06d}.json"))
        rows.append(store.get(entry["payload_ref"])["row"])
        expected_state = store.get(entry["state_ref"])
    fixture = analytic_fixture(late=True)
    case = OUTPUT/"success"
    case.mkdir(exist_ok=False)
    session = journal.create_session(case/"journal", fixture, "on_time", "late", "full_temporal")
    for i, row in enumerate(rows):
        session = journal.commit_step(session, journal.begin_step(session, row["prepared"].evidence), row["actual"])
        codec.require(not session.closed, "unexpected closure failure")
        event("saved_hour_"+str(i))
    codec.require(session.state == expected_state, "scientific prefix changed")
    session = journal.finish(session)
    codec.require(session.closed and session.scientific_outcome == "missing_input", "prefix did not close")
    old.write(case/"trusted_binding.json", journal.trusted_binding(session))
    child_start = time.perf_counter()
    completed = subprocess.run([sys.executable, "-B", str(Path(__file__).absolute()), "--child"], cwd=ROOT, capture_output=True, timeout=30)
    old.write(case/"child_launch.json", dict(exit_code=completed.returncode, outer_seconds=time.perf_counter()-child_start,
        stdout=completed.stdout.decode("utf-8", "replace"), stderr=completed.stderr.decode("utf-8", "replace")))
    codec.require(completed.returncode == 0, "fresh closure child failed")
    fresh = codec.parse(codec.read_bytes(case/"fresh.json"))
    expected_metrics = codec.parse(codec.read_bytes(old.OUTPUT/"report.json"))["failure_probes"]["missing_input"]
    codec.require(fresh["result"]["state_sha"] == c.digest(expected_state)
        and fresh["result"]["state_cas_sha"] == codec.pack(expected_state)[0]
        and fresh["result"]["summary"]["primary_right_censored"]
        and fresh["result"]["summary"]["remaining_debt"] == "40", "fresh scientific/censor mismatch")
    for key in ("summary", "independent_audit", "scientific_outcome", "publication_outcome", "terminal_entry_present"):
        codec.require(fresh["result"][key] == expected_metrics[key], "fresh saved-prefix metric differs: "+key)
    event("fresh_success")
    codec.require((counts["selective_compiler_calls"], counts["selective_descriptions"]) == (13, 44), "saved prefix accounting differs")
    results = {}
    for name in ("deleted_before_begin", "deleted_after_entry", "unknown_with_intact_closure"):
        counts_before = counts.copy()
        case = OUTPUT/name
        case.mkdir(exist_ok=False)
        s = journal.create_session(case/"journal", fixture, "on_time", "late", "full_temporal")
        initial = s.state
        def remove_fixture():
            genesis = codec.parse(codec.read_bytes(s.root/"genesis.json"))
            codec.require(codec.SHA.fullmatch(genesis["fixture_ref"]), "invalid fault target CAS key")
            path = s.root/"objects"/(genesis["fixture_ref"]+".json")
            path.resolve(strict=True).relative_to(OUTPUT.resolve(strict=True))
            raw = codec.read_bytes(path)
            codec.require(codec.sha(raw) == genesis["fixture_ref"], "fault target CAS hash differs")
            with (case/"removed_object.json").open("xb") as stream: stream.write(raw)
            path.unlink()
        if name == "deleted_before_begin":
            remove_fixture()
            try: journal.begin_step(s, rows[0]["prepared"].evidence)
            except journal.SessionClosed as error: s = error.session
        else:
            pending = journal.begin_step(s, rows[0]["prepared"].evidence)
            def fault(stage, path):
                if path.name == "entry_000001.json" and stage == "after_rename":
                    if name == "deleted_after_entry": remove_fixture()
                    else: raise OSError("registered readback unknown")
            s = journal.commit_step(s, pending, rows[0]["actual"], hook=fault)
        codec.require(s.closed and s.state == initial, "failed writer adopted candidate")
        codec.require((s.publication_outcome, s.ordinal) == ("not_published" if name == "deleted_before_begin" else "unknown", 0),
                      "failed writer publication classification differs")
        trusted = journal.trusted_binding(s)
        old.write(case/"trusted_binding.json", trusted)
        try: result = journal.reopen(s.root, fixture, "on_time", "late", "full_temporal", trusted)
        except ValueError as error:
            codec.require(name != "unknown_with_intact_closure" and "retained CAS missing" in str(error), "unexpected rejection")
            results[name] = dict(writer_adopted=False, reader_state="unresolved_missing_retained_CAS", error=str(error))
        else:
            codec.require(name == "unknown_with_intact_closure" and len(result["state"].records) == 1
                and result["publication_outcome"] == "committed", "unknown closure adjudication differs")
            results[name] = old.metrics(result)
        delta = counts-counts_before
        expected = {"deleted_before_begin": (0, 0), "deleted_after_entry": (3, 9), "unknown_with_intact_closure": (8, 24)}[name]
        codec.require((delta["selective_compiler_calls"], delta["selective_descriptions"]) == expected, "failure path accounting differs")
        results[name]["counts"] = dict(delta)
        old.write(case/"result.json", results[name])
        event(name)
    codec.require((counts["selective_compiler_calls"], counts["selective_descriptions"], counts["full_compiler_calls"], counts["solver_or_native_requests"]) == (24, 77, 0, 0), "parent accounting differs")
    combined = counts.copy()
    combined.update(fresh["counts"])
    codec.require({k.removeprefix("selective_role_"): v for k, v in combined.items() if k.startswith("selective_role_")} ==
        dict(reference_base_P0=37, reference_raw_need=10, recovery_min_meter=37, recovery_max_meter=37), "role accounting differs")
    after, old_after = bindings(), verify_prior()
    codec.require(before == after and preserved == old_after, "source or old evidence bookend changed")
    old.write(OUTPUT/"report.json", dict(authority="DRAFT_NONAUTHORITATIVE", bindings=after, preserved=old_after,
        parent_counts=dict(counts), fresh=fresh, expected_old_prefix=expected_metrics, failure_cases=results, elapsed=time.perf_counter()-START,
        public_numeric_results=False, native_authorized=False, resource_admission=False, overall_performance_review_complete=False))
    event("report_bookend")
    excluded = {"completion.json", "launcher_start.json", "launcher.json", "stdout.log", "stderr.log"}
    manifest = {p.relative_to(OUTPUT).as_posix(): old.stamp(p) for p in OUTPUT.rglob("*")
                if p.is_file() and p.relative_to(OUTPUT).as_posix() not in excluded}
    old.write(OUTPUT/"completion.json", dict(authority="DRAFT_NONAUTHORITATIVE", files=manifest,
        manifest_files=len(manifest), logical_bytes=sum(v["bytes"] for v in manifest.values())))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--child", action="store_true")
    if parser.parse_args().child: child()
    else: main()
