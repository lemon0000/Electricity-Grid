"""Write the single-writer, non-authoritative RQ2 continuation diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from src.rq2_joint_deliverability_boundary_v1.continuation_audit import (
    DEFAULT_CONFIG,
    audit_continuation_availability,
)

ROOT = Path(__file__).resolve().parents[1]


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_diagnostic(
    config_path: Path = DEFAULT_CONFIG,
    *,
    output_override: Path | None = None,
) -> dict[str, Any]:
    result = audit_continuation_availability(config_path)
    output = (
        ROOT
        / "results/tables/rq2_joint_deliverability_continuation_availability_v1_non_authoritative"
        if output_override is None
        else output_override.resolve()
    )
    if output.exists():
        raise FileExistsError(f"refusing to overwrite diagnostic output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    try:
        (staging / "summary.json").write_bytes(_json_bytes(result["summary"]))
        (staging / "chains.json").write_bytes(_json_bytes(result["chains"]))
        manifest = {
            name: _sha256(staging / name) for name in ("chains.json", "summary.json")
        }
        (staging / "SHA256SUMS.json").write_bytes(_json_bytes(manifest))
        staging.rename(output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return result["summary"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(json.dumps(write_diagnostic(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
