"""Wait for ifocus3 prepare PID to exit, then start generate if registration exists.

ASCII-only. Does not stop/restart the prepare process.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


PREPARE_PID = 47108
REPO = Path(__file__).resolve().parents[1]
PREREG = (
    REPO
    / "results"
    / "tables"
    / "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus3"
    / "preregistration"
    / "registration.json"
)
GENERATE_CMD = REPO / "scripts" / "run_repair_009_ifocus3_generate.cmd"
LOG_DIR = (
    REPO
    / "results"
    / "logs"
    / "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus3"
)
POLL_SECONDS = 60


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pid_alive(pid: int) -> bool:
    if os.name == "nt":
        # tasklist is reliable enough for this watcher
        completed = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        out = (completed.stdout or "") + (completed.stderr or "")
        return str(pid) in out and "No tasks" not in out
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def log(path: Path, message: str) -> None:
    line = f"[{utc_now()}] {message}"
    print(line, flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    chain_log = LOG_DIR / f"chain_prepare_to_generate_{stamp}.log"
    log(chain_log, f"watcher start pid={PREPARE_PID} prereg={PREREG}")

    while pid_alive(PREPARE_PID):
        log(
            chain_log,
            f"waiting prepare alive=1 prereg={'1' if PREREG.is_file() else '0'}",
        )
        time.sleep(POLL_SECONDS)

    log(chain_log, "prepare process exited")
    # Allow atomic publish to finish after process exit.
    for _ in range(30):
        if PREREG.is_file():
            break
        time.sleep(2)

    if not PREREG.is_file():
        log(chain_log, "ERROR: prepare exited without registration.json")
        print("PREPARE_FAILED_NO_REGISTRATION", flush=True)
        return 2

    log(chain_log, "PREPARE_OK_CHAINING_TO_GENERATE")
    print("PREPARE_OK_CHAINING_TO_GENERATE", flush=True)
    if not GENERATE_CMD.is_file():
        log(chain_log, f"ERROR: missing generate script {GENERATE_CMD}")
        return 3

    completed = subprocess.run(
        ["cmd", "/c", str(GENERATE_CMD)],
        cwd=str(REPO),
        check=False,
    )
    log(chain_log, f"generate exit={completed.returncode}")
    if completed.returncode == 0:
        print("GENERATE_OK", flush=True)
    else:
        print(f"GENERATE_FAILED exit={completed.returncode}", flush=True)
    return int(completed.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
