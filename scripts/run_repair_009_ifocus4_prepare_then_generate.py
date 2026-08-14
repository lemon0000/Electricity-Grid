"""Run ifocus4 prepare, then automatically start generate-candidates.

ASCII-only. Does not touch ifocus3 artifacts.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PYTHON = Path(r"D:\conda_envs\compute\python.exe")
CONFIG = REPO / "configs" / "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009.yaml"
RUNNER = (
    REPO
    / "experiments"
    / "run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal.py"
)
OUTPUT_ROOT = (
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
PREREG = OUTPUT_ROOT / "preregistration" / "registration.json"
GENERATE_CMD = REPO / "scripts" / "run_repair_009_ifocus4_generate.cmd"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    prepare_log = LOG_DIR / f"prepare_{stamp}.log"

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(REPO)

    if PREREG.is_file():
        log(chain_log, "preregistration already present; skipping prepare")
    else:
        log(chain_log, f"starting prepare log={prepare_log}")
        print("PREPARE_STARTING", flush=True)
        with prepare_log.open("w", encoding="utf-8") as handle:
            completed = subprocess.run(
                [
                    str(PYTHON),
                    "-u",
                    "-B",
                    str(RUNNER),
                    "--config",
                    str(CONFIG),
                    "--stage",
                    "prepare",
                ],
                cwd=str(REPO),
                env=env,
                stdout=handle,
                stderr=subprocess.STDOUT,
                check=False,
            )
        log(chain_log, f"prepare exit={completed.returncode}")
        if completed.returncode != 0 or not PREREG.is_file():
            print("PREPARE_FAILED", flush=True)
            return int(completed.returncode or 2)
        print("PREPARE_OK_CHAINING_TO_GENERATE", flush=True)

    log(chain_log, "starting generate")
    completed = subprocess.run(
        ["cmd", "/c", str(GENERATE_CMD)],
        cwd=str(REPO),
        env=env,
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
