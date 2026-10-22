"""One-shot P1 launcher; --execute-p1 is an action, never implicit authorization."""
import argparse
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def execute(registration_sha):
    from experiments.staged_rts24_native_probe_v1 import OUTPUT, LIMITS, write, verify_registration, preserve
    from src.staged_rts24_process_guard_v1 import supervise
    registration = verify_registration(registration_sha)
    if registration["preserved"] != preserve(): raise ValueError("registered prior bytes differ")
    OUTPUT.mkdir(parents=True, exist_ok=False)
    argv = [sys.executable, "-B", str(ROOT/"experiments/staged_rts24_native_probe_v1.py"), "--worker", "--root", str(OUTPUT),
        "--registration-sha", registration_sha]
    with (OUTPUT/"launcher.stdout.log").open("x", encoding="utf-8") as out, (OUTPUT/"launcher.stderr.log").open("x", encoding="utf-8") as err:
        with redirect_stdout(out), redirect_stderr(err):
            record = None
            try:
                write(OUTPUT/"launcher_start.json", dict(package="staged_rts24_P1_v1", limits=LIMITS, argv=argv,
                    registration_sha=registration_sha, authority="DRAFT_NONAUTHORITATIVE",
                    authorization_source="external_explicit_user_instruction_required"))
                record = supervise(argv, cwd=ROOT, output=OUTPUT, progress=OUTPUT/"events.jsonl", limits=LIMITS)
                record["authority"] = "DRAFT_NONAUTHORITATIVE"
                write(OUTPUT/"launcher.json", record)
                return 0 if record["exit_code"] == 0 and record["stop_reason"] is None and record["job_quiet_confirmed"] else 1
            except BaseException as exc:
                import traceback
                traceback.print_exc(file=err)
                err.flush()
                try: write(OUTPUT/"launcher_failure.json", dict(type=type(exc).__name__, message=str(exc),
                    process_observation=record, accepted_success=False))
                except BaseException: traceback.print_exc(file=err); err.flush()
                return 3


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Requires separate explicit user authorization for exactly P1.")
    parser.add_argument("--execute-p1", action="store_true", required=True)
    parser.add_argument("--registration-sha", required=True)
    args = parser.parse_args()
    sys.exit(execute(args.registration_sha))
