"""Stdlib-first bootstrap for the review-closed v3 execution controller."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v3.json"
INNER = ROOT / (
    "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v3"
    ".SHA256SUMS.json"
)
OUTER = ROOT / (
    "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v3"
    ".OUTER.SHA256SUMS.json"
)
REVIEW = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_review_pass_v3.json"
CONTRACT_MODULE = "experiments.rq2_public_grid_execution_runtime_contract_v3"
CONTROLLER_MODULE = (
    "experiments.run_rq2_public_grid_two_block_pilot_execution_controller_successor_v3"
)


class BootstrapV3Rejected(RuntimeError):
    """The v3 stdlib bootstrap failed closed."""


def _is_reparse(metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    return bool(attributes & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)))


def _strict_file(path: Path) -> None:
    raw = str(path)
    if not os.path.isabs(raw) or os.path.normpath(raw) != raw:
        raise BootstrapV3Rejected(f"bootstrap path is not canonical absolute: {path}")
    drive, tail = os.path.splitdrive(raw)
    current = Path(drive + os.sep)
    final = None
    for segment in [item for item in tail.split(os.sep) if item]:
        current /= segment
        try:
            metadata = os.lstat(current)
        except OSError as exc:
            raise BootstrapV3Rejected(f"bootstrap path is inaccessible: {current}") from exc
        if stat.S_ISLNK(metadata.st_mode) or _is_reparse(metadata):
            raise BootstrapV3Rejected(f"bootstrap alias/reparse rejected: {current}")
        if current != Path(drive + os.sep) and os.path.ismount(current):
            raise BootstrapV3Rejected(f"bootstrap nested mount rejected: {current}")
        final = metadata
    if final is None or not stat.S_ISREG(final.st_mode):
        raise BootstrapV3Rejected(f"bootstrap member is not an ordinary file: {path}")


def _stable(path: Path) -> bytes:
    _strict_file(path)
    try:
        first = path.read_bytes()
        second = path.read_bytes()
    except OSError as exc:
        raise BootstrapV3Rejected(f"bootstrap member unreadable: {path}") from exc
    if first != second:
        raise BootstrapV3Rejected(f"bootstrap member changed during double-read: {path}")
    return first


def _digest(path: Path) -> str:
    return hashlib.sha256(_stable(path)).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(_stable(path))
    except json.JSONDecodeError as exc:
        raise BootstrapV3Rejected(f"bootstrap JSON malformed: {path}") from exc
    if not isinstance(value, dict):
        raise BootstrapV3Rejected(f"bootstrap JSON is not an object: {path}")
    return value


def _config() -> dict[str, Any]:
    value = _json(CONFIG)
    if value.get("status") != "execution_controller_successor_v3_review_closed":
        raise BootstrapV3Rejected("v3 config identity drifted")
    return value


def _verify_successor_bundle(config: dict[str, Any]) -> str:
    outer = _json(OUTER)
    inner_hash = _digest(INNER)
    relative_inner = INNER.relative_to(ROOT).as_posix()
    if outer != {
        "schema": "rq2_public_grid_two_block_pilot_execution_controller_successor_outer_v3",
        "files": {relative_inner: inner_hash},
    }:
        raise BootstrapV3Rejected("v3 outer binding drifted")
    inner = _json(INNER)
    expected_files = inner.get("files")
    if (
        inner.get("schema")
        != "rq2_public_grid_two_block_pilot_execution_controller_successor_bundle_v3"
        or not isinstance(expected_files, dict)
        or len(expected_files) != 7
    ):
        raise BootstrapV3Rejected("v3 inner schema drifted")
    for relative, expected in expected_files.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise BootstrapV3Rejected("v3 inner member binding malformed")
        if _digest(ROOT / relative) != expected:
            raise BootstrapV3Rejected(f"v3 bundle member drifted: {relative}")
    identity = config["successor_identity"]
    for label in ("contract", "bootstrap", "controller", "worker"):
        relative = identity[f"{label}_path"]
        if expected_files.get(relative) != identity[f"{label}_sha256"]:
            raise BootstrapV3Rejected(f"v3 {label} identity drifted")
    return _digest(OUTER)


def _contract_after_bundle(config: dict[str, Any]) -> Any:
    if any(name.startswith("experiments.run_rq2_public_grid_two_block_pilot_execution_controller_successor_v3") for name in sys.modules):
        raise BootstrapV3Rejected("controller was imported before bootstrap closure gate")
    module = importlib.import_module(CONTRACT_MODULE)
    module.StageAwareClosureVerifier.production().verify(
        "bootstrap_pre_controller_import"
    )
    return module


def _review(config: dict[str, Any], contract: Any, outer_hash: str) -> dict[str, Any] | None:
    if not REVIEW.exists():
        return None
    receipt = _json(REVIEW)
    return contract.validate_review_receipt_object(
        receipt,
        outer_relative=OUTER.relative_to(ROOT).as_posix(),
        outer_sha256=outer_hash,
    )


def validate_only() -> dict[str, object]:
    config = _config()
    outer_hash = _verify_successor_bundle(config)
    contract = _contract_after_bundle(config)
    review = _review(config, contract, outer_hash)
    if any(os.path.lexists(ROOT / path) for path in config["paths"].values()):
        raise BootstrapV3Rejected("v3 result/root appearance rejected")
    return {
        "validation_passed": True,
        "execution_review_present": review is not None,
        "execution_ready": False,
        "dependency_closure_verified": True,
        "workers": 0,
        "loader_calls": 0,
        "solver_calls": 0,
        "result_writes": 0,
        "formal_writes": 0,
    }


def _parse(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    if args.validate_only and not args.execute:
        print(json.dumps(validate_only(), sort_keys=True))
        return 0
    if args.execute and not args.validate_only:
        config = _config()
        outer_hash = _verify_successor_bundle(config)
        contract = _contract_after_bundle(config)
        if _review(config, contract, outer_hash) is None:
            raise BootstrapV3Rejected(
                "external v3 execution review receipt is absent before controller import"
            )
        controller = importlib.import_module(CONTROLLER_MODULE)
        return int(controller.main(["--execute"]))
    raise BootstrapV3Rejected("exactly one registered bootstrap mode is required")


if __name__ == "__main__":
    raise SystemExit(main())
