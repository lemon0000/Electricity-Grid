"""Stdlib-first bootstrap for execution-controller successor v2."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import stat
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v2.json"
INNER = ROOT / (
    "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v2"
    ".SHA256SUMS.json"
)
OUTER = ROOT / (
    "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v2"
    ".OUTER.SHA256SUMS.json"
)
REVIEW = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_review_pass_v2.json"
CONTROLLER_MODULE = (
    "experiments.run_rq2_public_grid_two_block_pilot_execution_controller_successor_v2"
)
CLOSURE_MODULE = "experiments.rq2_public_grid_execution_dependency_closure_v2"
PREDECESSOR_BOOTSTRAP_MODULE = (
    "experiments.bootstrap_rq2_public_grid_two_block_pilot_execution_controller_successor_v1"
)
_INITIAL_PROJECT_IMPORTS = tuple(
    sorted(
        name
        for name in sys.modules
        if (
            name == "src"
            or name.startswith("src.")
            or (name.startswith("experiments.") and name != __name__)
        )
    )
)


class BootstrapV2Rejected(RuntimeError):
    """A fail-closed successor-v2 bootstrap rejection."""


def _is_reparse(metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    return bool(attributes & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)))


def _strict_file(path: Path) -> None:
    raw = str(path)
    if not os.path.isabs(raw) or os.path.normpath(raw) != raw:
        raise BootstrapV2Rejected(f"artifact path is not canonical: {raw}")
    drive, tail = os.path.splitdrive(raw)
    root = Path(drive + os.sep)
    current = root
    final: os.stat_result | None = None
    for segment in [part for part in tail.split(os.sep) if part]:
        current /= segment
        try:
            metadata = os.lstat(current)
        except OSError as exc:
            raise BootstrapV2Rejected(f"artifact path unavailable: {current}") from exc
        if stat.S_ISLNK(metadata.st_mode) or _is_reparse(metadata):
            raise BootstrapV2Rejected(f"artifact alias/reparse rejected: {current}")
        try:
            mounted = os.path.ismount(current)
        except OSError as exc:
            raise BootstrapV2Rejected(f"artifact mount status indeterminate: {current}") from exc
        if current != root and mounted:
            raise BootstrapV2Rejected(f"artifact nested mount rejected: {current}")
        final = metadata
    if final is None or not stat.S_ISREG(final.st_mode):
        raise BootstrapV2Rejected(f"artifact is not an ordinary file: {path}")


def _stable_bytes(path: Path) -> bytes:
    _strict_file(path)
    try:
        first = path.read_bytes()
        second = path.read_bytes()
    except OSError as exc:
        raise BootstrapV2Rejected(f"artifact unreadable: {path}") from exc
    if first != second:
        raise BootstrapV2Rejected(f"artifact changed during double-read: {path}")
    return first


def _sha256(path: Path) -> str:
    return hashlib.sha256(_stable_bytes(path)).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(_stable_bytes(path))
    except json.JSONDecodeError as exc:
        raise BootstrapV2Rejected(f"artifact JSON malformed: {path}") from exc
    if not isinstance(value, dict):
        raise BootstrapV2Rejected(f"artifact JSON is not an object: {path}")
    return value


def _config() -> dict[str, Any]:
    value = _json(CONFIG)
    if value.get("status") != "execution_controller_successor_v2_review_closed":
        raise BootstrapV2Rejected("successor-v2 status drifted")
    return value


def _verify_successor_bundle(config: Mapping[str, Any]) -> int:
    identity = config["successor_identity"]
    outer = _json(OUTER)
    expected_outer = {
        "schema": "rq2_public_grid_two_block_pilot_execution_controller_successor_outer_v2",
        "files": {INNER.relative_to(ROOT).as_posix(): _sha256(INNER)},
    }
    if outer != expected_outer:
        raise BootstrapV2Rejected("successor-v2 outer inventory drifted")
    inner = _json(INNER)
    expected_paths = {
        "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v2.json",
        "configs/rq2_public_grid_two_block_pilot_execution_controller_review_rework_v1.json",
        identity["closure_path"],
        identity["bootstrap_path"],
        identity["controller_path"],
        identity["worker_path"],
        "tests/test_rq2_public_grid_two_block_pilot_execution_controller_successor_v2.py",
    }
    if (
        not isinstance(inner.get("files"), dict)
        or inner.get("schema")
        != "rq2_public_grid_two_block_pilot_execution_controller_successor_bundle_v2"
        or set(inner["files"]) != expected_paths
    ):
        raise BootstrapV2Rejected("successor-v2 exact seven-member inventory drifted")
    for relative, digest in inner["files"].items():
        if not isinstance(digest, str) or _sha256(ROOT / relative) != digest:
            raise BootstrapV2Rejected(f"successor-v2 member drifted: {relative}")
    if any(
        _sha256(ROOT / identity[key.removesuffix("_sha256") + "_path"])
        != identity[key]
        for key in ("closure_sha256", "bootstrap_sha256", "controller_sha256", "worker_sha256")
    ):
        raise BootstrapV2Rejected("successor-v2 embedded identity drifted")
    return len(inner["files"])


def _verified_closure(config: Mapping[str, Any]) -> Any:
    identity = config["successor_identity"]
    closure_path = ROOT / identity["closure_path"]
    if _sha256(closure_path) != identity["closure_sha256"]:
        raise BootstrapV2Rejected("closure helper drifted before import")
    module = importlib.import_module(CLOSURE_MODULE)
    try:
        module.verify_dependency_closure(ROOT, config)
    except module.ClosureRejected as exc:
        raise BootstrapV2Rejected("full dependency closure rejected") from exc
    return module


def _predecessor_bootstrap(config: Mapping[str, Any]) -> Any:
    """Load only after its exact bytes were verified through the frozen closure."""
    predecessor_member = next(
        item
        for item in config["dependency_closure"]["bundles"]
        if item["name"] == "execution_controller_successor_v1"
    )["members"]
    relative = "experiments/bootstrap_rq2_public_grid_two_block_pilot_execution_controller_successor_v1.py"
    if _sha256(ROOT / relative) != predecessor_member[relative]:
        raise BootstrapV2Rejected("predecessor bootstrap drifted before import")
    return importlib.import_module(PREDECESSOR_BOOTSTRAP_MODULE)


def _verify_runtime_and_protected_state(config: Mapping[str, Any]) -> None:
    predecessor = _predecessor_bootstrap(config)
    try:
        predecessor._verify_runtime(config)
        for relative in config["paths"].values():
            predecessor._strict_absent(ROOT / relative)
        formal = config["formal_protection"]
        for path_key, hash_key in (
            ("formal_runner_path", "formal_runner_sha256"),
            ("activated_config_path", "activated_config_sha256"),
        ):
            artifact = ROOT / formal[path_key]
            predecessor._strict_file(artifact)
            if predecessor._sha256(artifact) != formal[hash_key]:
                raise BootstrapV2Rejected("formal authority drifted")
        predecessor._audit_checkpoint_inventory(
            ROOT / formal["checkpoint_directory"], formal["checkpoint_sha256"]
        )
    except predecessor.BootstrapRejected as exc:
        raise BootstrapV2Rejected("runtime/protected-state gate rejected") from exc


def _fixed_review(config: Mapping[str, Any], closure_module: Any) -> dict[str, Any]:
    try:
        receipt, _digest = closure_module.load_and_validate_review_receipt(
            REVIEW, config=config, outer_path=OUTER, root=ROOT
        )
    except closure_module.ClosureRejected as exc:
        raise BootstrapV2Rejected("fixed execution review receipt rejected") from exc
    return receipt


def validate_review_receipt_for_entry(
    receipt: object, *, outer_sha256: str, closure_module: Any
) -> None:
    """Bootstrap-entry receipt seam using the exact common receipt contract."""
    closure_module.validate_review_receipt_object(
        receipt,
        config=_config(),
        outer_relative=OUTER.relative_to(ROOT).as_posix(),
        outer_sha256=outer_sha256,
    )


def validate_only() -> dict[str, Any]:
    if _INITIAL_PROJECT_IMPORTS:
        raise BootstrapV2Rejected(
            f"project module preimport rejected: {_INITIAL_PROJECT_IMPORTS}"
        )
    config = _config()
    members = _verify_successor_bundle(config)
    closure_module = _verified_closure(config)
    _verify_runtime_and_protected_state(config)
    gates = config["gates"]
    if (
        gates.get("successor_v2_independent_review_passed") is not False
        or gates.get("fixed_execution_review_receipt_present") is not False
        or gates.get("execution_ready") is not False
        or gates.get("pilot_executed") is not False
        or gates.get("formal_execution_ready") is not False
        or gates.get("user_formal_run_authorized") is not False
        or gates.get("formal_result_exists") is not False
        or gates.get("claim") is not False
        or gates.get("security_certified") is not False
    ):
        raise BootstrapV2Rejected("review-closed gates drifted")
    review_present = False
    try:
        os.lstat(REVIEW)
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise BootstrapV2Rejected("review receipt presence indeterminate") from exc
    else:
        _fixed_review(config, closure_module)
        review_present = True
    return {
        "validation_passed": True,
        "bundle_members": members,
        "dependency_closure_verified": True,
        "execution_review_present": review_present,
        "execution_ready": False,
        "project_imports_before_closure": 0,
        "workers": 0,
        "loader_calls": 0,
        "solver_calls": 0,
        "result_writes": 0,
        "formal_writes": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.validate_only == args.execute:
        raise BootstrapV2Rejected("exactly one bootstrap mode is required")
    report = validate_only()
    if args.validate_only:
        print(json.dumps(report, sort_keys=True))
        return 0
    config = _config()
    closure_module = _verified_closure(config)
    _fixed_review(config, closure_module)
    controller = importlib.import_module(CONTROLLER_MODULE)
    return int(controller.main(["--execute"]))


if __name__ == "__main__":
    raise SystemExit(main())
