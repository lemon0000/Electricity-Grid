"""Publish a non-authoritative, zero-solver RQ2 boundary diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import yaml

from src.rq2_joint_deliverability_boundary_v1.audit import (
    audit_raw_training_support,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = (
    ROOT / "configs/rq2_joint_deliverability_boundary_successor_v1.DRAFT.yaml"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _configured_output(config_path: Path) -> Path:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    raw = config["output"]["directory"]
    if not isinstance(raw, str) or not raw:
        raise ValueError("diagnostic output directory must be explicit")
    target = Path(raw)
    return target if target.is_absolute() else ROOT / target


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def write_diagnostic(
    config_path: Path,
    *,
    output_override: Path | None = None,
) -> dict[str, object]:
    """Write a single-writer diagnostic bundle and reject a pre-existing target."""

    config_path = config_path.resolve()
    result = audit_raw_training_support(config_path)
    summary = result["summary"]
    if not isinstance(summary, dict):
        raise TypeError("diagnostic summary must be a mapping")
    target = (
        output_override.resolve()
        if output_override is not None
        else _configured_output(config_path).resolve()
    )
    if target.exists():
        raise FileExistsError(f"refusing to overwrite diagnostic output: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    try:
        (staging / "summary.json").write_bytes(_json_bytes(summary))
        (staging / "cells.json").write_bytes(_json_bytes(result["cells"]))
        manifest = {
            name: _sha256(staging / name) for name in ("cells.json", "summary.json")
        }
        (staging / "SHA256SUMS.json").write_bytes(_json_bytes(manifest))
        staging.rename(target)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args()
    print(json.dumps(write_diagnostic(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
