"""Run the declared D grid once into a dedicated attempt directory.

DRAFT_NONAUTHORITATIVE. Zero solver calls, zero external downloads. Writes only
into a freshly created attempt directory and refuses to overwrite an existing one.
No production manifest, lease, seal or official result is created.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.staged_deliverability_d_grid_v1 import (  # noqa: E402
    CLEAN_PATHS, GRID_BUSINESS, GRID_PATHS, run_matrix, summarize,
)

DEFAULT_FIXTURE = ROOT / "configs/staged_deliverability_d_v1.DRAFT.yaml"
B1_FIXTURE = ROOT / "configs/staged_deliverability_small_case_v1.DRAFT.yaml"
ROOT_OUT = ROOT / "results/tables/staged_deliverability_d_v1_non_authoritative"
SOURCES = (
    "src/staged_deliverability_d_grid_v1.py",
    "src/staged_deliverability_replay_v1.py",
    "src/staged_deliverability_development_v1.py",
    "experiments/staged_deliverability_d_v1.py",
)


def _json_default(value):
    """Exact rationals travel as strings; the model never emits floats for quantities."""
    from fractions import Fraction
    if isinstance(value, Fraction):
        return str(value)
    raise TypeError(f"not serializable: {type(value).__name__}")


def pin(path: Path) -> dict:
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT)
            else str(path), "bytes": len(data), "sha256": sha256(data).hexdigest()}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", default=None,
                        help="attempt directory name under the D results root")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args(argv)

    name = args.attempt or "attempt_01"
    target = ROOT_OUT / name
    if target.exists():
        raise SystemExit(f"refusing to overwrite existing attempt: {target}")
    target.mkdir(parents=True)

    started = datetime.now(timezone.utc)
    rows = run_matrix(args.fixture)
    summary = summarize(rows)

    report = {
        "authority": "DRAFT_NONAUTHORITATIVE",
        "scope": "staged_deliverability_d_v1_grid",
        "created_utc": started.isoformat(),
        "formal_result": False,
        "resource_admission": False,
        "security_certified": False,
        "aggregate_contract_release": False,
        "solver_calls": 0,
        "external_downloads": 0,
        "grid": {
            "business": list(GRID_BUSINESS),
            "grid": list(GRID_PATHS),
            "clean": list(CLEAN_PATHS),
            "methods": ["instantaneous", "fixed_headroom", "full_temporal"],
            "cells": len(GRID_BUSINESS) * len(GRID_PATHS) * len(CLEAN_PATHS),
            "evaluations": len(rows),
        },
        "inputs": [pin(args.fixture), pin(B1_FIXTURE)],
        "sources": [pin(ROOT / name) for name in SOURCES],
        "summary": summary,
        "rows": rows,
        "axes": {
            "replay": "method verdict vs its own arrangement replayed under full temporal constraints",
            "strategy": "method verdict vs the complete temporal strategy verdict on the same plan",
        },
    }

    (target / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=_json_default) + "\n",
        encoding="utf-8")
    (target / "report.sha256").write_text(
        sha256((target / "report.json").read_bytes()).hexdigest() + "\n", encoding="utf-8")
    print(json.dumps({"attempt": name, "evaluations": len(rows),
                      "replay": summary["counts"],
                      "strategy": summary["strategy_counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
