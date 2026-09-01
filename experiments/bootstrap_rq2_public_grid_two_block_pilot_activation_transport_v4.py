"""Standard-library bootstrap for the closed activation-transport v4 candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_activation_transport_v4.json"
INNER = ROOT / "configs/rq2_public_grid_two_block_pilot_activation_transport_v4.SHA256SUMS.json"
OUTER = ROOT / "configs/rq2_public_grid_two_block_pilot_activation_transport_v4.OUTER.SHA256SUMS.json"


class BootstrapRejected(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise BootstrapRejected(f"unreadable artifact: {path}") from exc


def _strict_file(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            metadata = os.lstat(current)
        except OSError as exc:
            raise BootstrapRejected(f"artifact path unavailable: {path}") from exc
        attributes = int(getattr(metadata, "st_file_attributes", 0))
        if stat.S_ISLNK(metadata.st_mode) or attributes & 0x400:
            raise BootstrapRejected(f"artifact alias/reparse rejected: {path}")
    if not stat.S_ISREG(os.lstat(path).st_mode):
        raise BootstrapRejected(f"artifact is not an ordinary file: {path}")


def _json(path: Path) -> dict[str, Any]:
    _strict_file(path)
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise BootstrapRejected(f"malformed JSON artifact: {path}") from exc
    if not isinstance(value, dict):
        raise BootstrapRejected(f"JSON artifact is not an object: {path}")
    return value


def _verify_manifest(path: Path) -> dict[str, str]:
    value = _json(path)
    files = value.get("files")
    if not isinstance(files, dict) or not files:
        raise BootstrapRejected("bundle manifest inventory missing")
    for relative, digest in files.items():
        member = ROOT / str(relative)
        _strict_file(member)
        if not isinstance(digest, str) or _sha256(member) != digest:
            raise BootstrapRejected("bundle member hash drifted")
    return {str(key): str(value) for key, value in files.items()}


def validate_only() -> dict[str, Any]:
    config = _json(CONFIG)
    predecessor = config["predecessor_authority"]
    for path_key, hash_key in (
        ("activation_v3_outer_path", "activation_v3_outer_sha256"),
        ("activation_v3_inner_path", "activation_v3_inner_sha256"),
        ("activation_v3_rework_receipt_path", "activation_v3_rework_receipt_sha256"),
        ("user_authorization_path", "user_authorization_sha256"),
    ):
        candidate = ROOT / predecessor[path_key]
        _strict_file(candidate)
        if _sha256(candidate) != predecessor[hash_key]:
            raise BootstrapRejected("predecessor authority drifted")
    inner_hash = _sha256(INNER)
    outer = _json(OUTER)
    if outer.get("files") != {
        "configs/rq2_public_grid_two_block_pilot_activation_transport_v4.SHA256SUMS.json": inner_hash
    }:
        raise BootstrapRejected("outer manifest binding drifted")
    members = _verify_manifest(INNER)
    formal = config["formal_protection"]
    formal_runner = ROOT / formal["formal_runner_path"]
    _strict_file(formal_runner)
    if _sha256(formal_runner) != formal["formal_runner_sha256"]:
        raise BootstrapRejected("formal runner drifted")
    activated_config = ROOT / formal["activated_config_path"]
    _strict_file(activated_config)
    if _sha256(activated_config) != formal["activated_config_sha256"]:
        raise BootstrapRejected("activated formal config drifted")
    checkpoint = ROOT / formal["checkpoint_directory"]
    try:
        checkpoint_files = [entry for entry in checkpoint.iterdir() if entry.is_file()]
    except OSError as exc:
        raise BootstrapRejected("formal checkpoint inventory unavailable") from exc
    if len(checkpoint_files) != int(formal["checkpoint_count"]):
        raise BootstrapRejected("formal checkpoint inventory drifted")
    for root in formal["protected_roots"]:
        if os.path.lexists(ROOT / root):
            raise BootstrapRejected("protected v4 root appeared")
    gates = config["gates"]
    if any(
        gates.get(name) is not False
        for name in (
            "activation_v4_independent_review_passed",
            "execution_wrapper_present",
            "wrapper_independent_review_passed",
            "dispatch_authorization_present",
            "production_dispatch_permitted",
            "pilot_executed",
            "formal_execution_ready",
            "user_formal_run_authorized",
            "formal_result_exists",
            "claim",
            "security_certified",
        )
    ):
        raise BootstrapRejected("closed gates drifted")
    return {
        "validation_passed": True,
        "status": config["status"],
        "bundle_members": len(members),
        "activation_v4_independent_review_passed": False,
        "execution_ready": False,
        "project_imports": 0,
        "production_workers": 0,
        "scientific_loader_calls": 0,
        "solver_calls": 0,
        "result_writes": 0,
        "formal_writes": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.execute or not args.validate_only:
        raise BootstrapRejected(
            "v4 candidate is permanently closed; a new reviewed wrapper successor is required"
        )
    print(json.dumps(validate_only(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
