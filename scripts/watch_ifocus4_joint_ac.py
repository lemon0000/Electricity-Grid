"""Monitor ifocus4 run-joint-ac until lease/attempt appears or process exits."""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PID = 13700
OUTPUT = (
    REPO
    / "results"
    / "tables"
    / "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus4"
)
LOG_DIR = (
    REPO
    / "results"
    / "logs"
    / "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus4"
)
POLL = 60


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def pid_alive(pid: int) -> bool:
    completed = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
        capture_output=True,
        text=True,
        check=False,
    )
    out = (completed.stdout or "") + (completed.stderr or "")
    return str(pid) in out and "No tasks" not in out


def latest_joint_log() -> Path | None:
    logs = sorted(LOG_DIR.glob("joint_ac_*.log"), key=lambda p: p.stat().st_mtime)
    return logs[-1] if logs else None


def find_attempt() -> Path | None:
    attempts = sorted(
        [p for p in LOG_DIR.glob("joint_*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
    )
    return attempts[-1] if attempts else None


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    watch_log = LOG_DIR / f"watch_joint_ac_{stamp}.log"

    def emit(msg: str) -> None:
        line = f"[{utc_now()}] {msg}"
        print(line, flush=True)
        with watch_log.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    emit(f"watch start pid={PID}")
    while pid_alive(PID):
        lease = OUTPUT / "execution_lease" / "active" / "lease.json"
        attempt = find_attempt()
        joint = OUTPUT / "joint_ac"
        log = latest_joint_log()
        bits = [
            f"alive=1",
            f"lease={'1' if lease.is_file() else '0'}",
            f"attempt={'1' if attempt else '0'}",
            f"joint_ac={'1' if joint.exists() else '0'}",
            f"log_bytes={log.stat().st_size if log and log.is_file() else 0}",
        ]
        if attempt and (attempt / "progress.jsonl").is_file():
            # last non-empty event type
            last = None
            for line in (attempt / "progress.jsonl").read_text(encoding="utf-8").splitlines():
                if line.strip():
                    last = json.loads(line)
            if last:
                bits.append(f"last_event={last.get('event')}")
                bits.append(f"stage={last.get('stage')}")
        emit(" ".join(bits))
        if lease.is_file() and attempt is not None:
            emit(f"JOINT_AC_LEASE_AND_ATTEMPT_READY attempt={attempt.name}")
            print("JOINT_AC_LEASE_AND_ATTEMPT_READY", flush=True)
            # keep watching until process exits
        time.sleep(POLL)

    emit("process exited")
    log = latest_joint_log()
    if log and log.is_file():
        tail = log.read_text(encoding="utf-8", errors="replace")[-2000:]
        emit(f"log_tail:\n{tail}")
    if (OUTPUT / "joint_ac").exists():
        emit("JOINT_AC_PUBLISHED")
        print("JOINT_AC_PUBLISHED", flush=True)
        return 0
    emit("JOINT_AC_FAILED_OR_INCOMPLETE")
    print("JOINT_AC_FAILED_OR_INCOMPLETE", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
