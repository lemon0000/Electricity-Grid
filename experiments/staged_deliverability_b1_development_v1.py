"""Bounded zero-solver B1 diagnostic; see its development contract before use."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import psutil
import yaml

from src.staged_deliverability_development_v1 import (
    METHODS, advance, assessment, initialize, load_small_case, plain,
    read_checkpoint, save_checkpoint, task_balances,
)
from src.staged_deliverability_audit_v1 import audit_records, offline_recovery_check

FIXTURE = ROOT / "configs/staged_deliverability_small_case_v1.DRAFT.yaml"
BASE = ROOT / "results/tables/staged_deliverability_b1_v1_non_authoritative"
SOURCES = (
    FIXTURE, Path(__file__), ROOT / "src/staged_deliverability_development_v1.py",
    ROOT / "src/staged_deliverability_audit_v1.py",
    ROOT / "src/rq2_joint_deliverability_boundary_v1/debt_cohorts.py",
    ROOT / "tests/test_staged_deliverability_development_v1.py",
    ROOT / "docs/plan/staged_deliverability_b1_development_contract_v1.md",
    ROOT / "docs/plan/staged_deliverability_small_case_plan_v1.md",
    ROOT / "docs/model_spec/staged_deliverability_minimum_spec_v1.md",
)


def dump(path, value):
    data = json.dumps(plain(value), sort_keys=True, indent=2, allow_nan=False) + "\n"
    if len(data.encode("utf-8")) > 1024 * 1024:
        raise ValueError("output file exceeds 1 MiB")
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(data)


def pins():
    return {str(p.resolve().relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in SOURCES}


def child(args):
    checkpoint, result = args.reopen.resolve(), args.result.resolve()
    stem = f"{args.plan}_{args.clean}_{args.method}"
    if (checkpoint.parent != result.parent or checkpoint.parent.parent != BASE.resolve()
            or checkpoint.name != f"{stem}_checkpoint.json" or result.name != f"{stem}_terminal.json"):
        raise ValueError("child paths must match the dedicated attempt and declared case")
    p, observations = load_small_case(FIXTURE, args.plan, args.clean)
    identity = f"{args.plan}:{args.clean}:{args.method}"
    state = read_checkpoint(args.reopen, p, observations[:4], args.method, identity)
    for o in observations[4:]:
        state = advance(p, state, o)
    audit = audit_records(plain(p), plain(state.records), state.method)
    dump(result, dict(status="DRAFT_NONAUTHORITATIVE", scope="B1 scalar mechanism only",
                      state=state, audit=audit, policy_steps=10, audit_steps=10))


def run(output):
    output = output.resolve()
    if output.parent != BASE.resolve():
        raise ValueError("attempt must be directly under the dedicated non-authoritative output root")
    output.mkdir(parents=True, exist_ok=False)
    start, peak = time.perf_counter(), 0
    current_child = None
    stage_times, counts = {}, dict(policy_steps=0, audit_steps=0, child_processes=0, offline_oracles=0)
    events = output / "events.jsonl"

    def guard(stage):
        nonlocal peak
        process = psutil.Process()
        members = [process, *process.children(recursive=True)]
        rss = 0
        for member in members:
            try:
                rss += member.memory_info().rss
            except psutil.NoSuchProcess:
                pass
        peak = max(peak, rss)
        size = sum(p.stat().st_size for p in output.iterdir() if p.is_file())
        elapsed = time.perf_counter() - start
        if elapsed > 60 or rss > 512 * 1024**2 or size > 16 * 1024**2:
            raise RuntimeError(f"B1 resource limit at {stage}")
        return elapsed

    def event(stage):
        elapsed = guard(stage)
        with events.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(dict(stage=stage, elapsed=elapsed, counts=counts)) + "\n")

    def timed(name, operation):
        begin = time.perf_counter()
        result = operation()
        stage_times[name] = stage_times.get(name, 0) + time.perf_counter() - begin
        event(name)
        return result

    try:
        if FIXTURE.stat().st_size > 1024**2:
            raise ValueError("fixture exceeds input limit")
        before = timed("source_hash_before", pins)
        dump(output / "start.json", dict(status="DRAFT_NONAUTHORITATIVE", source_sha256=before,
             environment=dict(python=sys.version, platform=platform.platform(), yaml=yaml.__version__,
                              psutil=psutil.__version__), contract="docs/plan/staged_deliverability_b1_development_contract_v1.md"))
        summaries, oracles = [], []
        for plan, clean in (("on_time", "early"), ("on_time", "late"), ("delayed", "early")):
            p, observations = timed("input_load", lambda: load_small_case(FIXTURE, plan, clean))
            for method in METHODS:
                identity = f"{plan}:{clean}:{method}"
                stem = identity.replace(":", "_")
                state = initialize(p, method, identity, observations[0].hour)
                prefix = None
                begin = time.perf_counter()
                for o in observations:
                    state = advance(p, state, o)
                    counts["policy_steps"] += 1
                    if o.hour == 1:
                        prefix = state
                    guard("policy_step")
                    if state.stopped:
                        raise RuntimeError("unexpected full-policy stop in declared diagnostic fixture")
                stage_times["continuous_policy"] = stage_times.get("continuous_policy", 0) + time.perf_counter() - begin
                audit = timed("parent_audit", lambda: audit_records(plain(p), plain(state.records), state.method))
                counts["audit_steps"] += len(state.records)
                checkpoint, terminal = output / f"{stem}_checkpoint.json", output / f"{stem}_terminal.json"
                timed("checkpoint_save", lambda: save_checkpoint(checkpoint, p, prefix))
                command = [sys.executable, "-B", str(Path(__file__).resolve()), "--reopen", str(checkpoint),
                           "--result", str(terminal), "--plan", plan, "--clean", clean, "--method", method]
                begin = time.perf_counter()
                current_child = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                counts["child_processes"] += 1
                while current_child.poll() is None:
                    guard("fresh_child")
                    if time.perf_counter() - begin > 15:
                        raise TimeoutError("B1 fresh child exceeded 15 seconds")
                    time.sleep(.05)
                _, error = current_child.communicate()
                if current_child.returncode:
                    raise RuntimeError(error.decode("utf-8", errors="replace"))
                current_child = None
                stage_times["fresh_process_reopen_audit"] = stage_times.get("fresh_process_reopen_audit", 0) + time.perf_counter() - begin
                saved = json.loads(terminal.read_text(encoding="utf-8"))
                if (saved.get("status") != "DRAFT_NONAUTHORITATIVE"
                        or saved.get("scope") != "B1 scalar mechanism only"
                        or saved["state"] != plain(state) or saved["audit"] != plain(audit)):
                    raise ArithmeticError("fresh-process terminal differs from continuous reference")
                counts["policy_steps"] += saved["policy_steps"]
                counts["audit_steps"] += saved["audit_steps"]
                summaries.append(dict(plan=plan, clean=clean, assessment=assessment(state), tasks=task_balances(state),
                                      first_full_contract_rejection=audit["first_full_contract_rejection"],
                                      debt_before_rejection=audit["debt_before_full_contract_rejection"]))
                if plan == "on_time" and method == "full_temporal":
                    result = timed("offline_oracle", lambda: offline_recovery_check(plain(p), plain(observations), audit["calls"]))
                    oracles.append(dict(clean=clean, result=result))
                    counts["offline_oracles"] += 1
                event(stem)
        after = timed("source_hash_after", pins)
        if before != after:
            raise RuntimeError("source changed during diagnostic")
        if counts != dict(policy_steps=180, audit_steps=180, child_processes=9, offline_oracles=2):
            raise ArithmeticError("actual work count differs from registered diagnostic")
        dump(output / "report.json", dict(status="development_diagnostic_completed", authority="DRAFT_NONAUTHORITATIVE",
             source_sha256=after, counts=counts, stage_wall_seconds=stage_times,
             elapsed_seconds=guard("report"), sampled_process_tree_peak_rss_bytes=peak,
             scope="B1 scalar mechanism only; B2 and full main-experiment budget unknown",
             known_unmeasured="cost of I/O failure cleanup; actual network; native/solver",
             summaries=summaries, offline_oracles=oracles))
        event("completed")
        print(json.dumps(dict(status="development_diagnostic_completed", counts=counts,
                              elapsed_seconds=time.perf_counter() - start, output=str(output))))
    except BaseException as error:
        if current_child is not None:
            if current_child.poll() is None:
                current_child.kill()
            current_child.communicate(timeout=5)
        dump(output / "failure.json", dict(status="development_diagnostic_failed", error=str(error),
             counts=counts, elapsed_seconds=time.perf_counter() - start))
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--reopen", type=Path)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--plan", choices=("on_time", "delayed"))
    parser.add_argument("--clean", choices=("early", "late"))
    parser.add_argument("--method", choices=METHODS)
    args = parser.parse_args()
    if args.reopen:
        child(args)
    elif args.output:
        run(args.output)
    else:
        parser.error("--output or --reopen required")


if __name__ == "__main__":
    main()
