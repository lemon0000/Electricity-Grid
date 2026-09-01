"""Standard-library bootstrap for the closed activation-transport v5 candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_activation_transport_v5.json"
INNER = ROOT / "configs/rq2_public_grid_two_block_pilot_activation_transport_v5.SHA256SUMS.json"
OUTER = ROOT / "configs/rq2_public_grid_two_block_pilot_activation_transport_v5.OUTER.SHA256SUMS.json"


class BootstrapV5Rejected(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise BootstrapV5Rejected(f"unreadable artifact: {path}") from exc


def _strict_file(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            metadata = os.lstat(current)
        except OSError as exc:
            raise BootstrapV5Rejected(f"artifact path unavailable: {path}") from exc
        attributes = int(getattr(metadata, "st_file_attributes", 0))
        if stat.S_ISLNK(metadata.st_mode) or attributes & 0x400:
            raise BootstrapV5Rejected(f"artifact alias/reparse rejected: {path}")
    if not stat.S_ISREG(os.lstat(path).st_mode):
        raise BootstrapV5Rejected(f"artifact is not an ordinary file: {path}")


def _json(path: Path) -> dict[str, Any]:
    _strict_file(path)
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise BootstrapV5Rejected(f"malformed JSON artifact: {path}") from exc
    if not isinstance(value, dict):
        raise BootstrapV5Rejected(f"JSON artifact is not an object: {path}")
    return value


def _verify_manifest(path: Path) -> int:
    files = _json(path).get("files")
    if not isinstance(files, dict) or not files:
        raise BootstrapV5Rejected("bundle manifest inventory missing")
    for relative, digest in files.items():
        member = ROOT / str(relative)
        _strict_file(member)
        if not isinstance(digest, str) or _sha256(member) != digest:
            raise BootstrapV5Rejected("bundle member hash drifted")
    return len(files)


def validate_only() -> dict[str, Any]:
    config = _json(CONFIG)
    predecessor = config["predecessor_authority"]
    for path_key, hash_key in (
        ("activation_v4_outer_path", "activation_v4_outer_sha256"),
        ("activation_v4_escalate_receipt_path", "activation_v4_escalate_receipt_sha256"),
        ("activation_v4_controller_path", "activation_v4_controller_sha256"),
        ("user_authorization_path", "user_authorization_sha256"),
    ):
        candidate = ROOT / predecessor[path_key]
        _strict_file(candidate)
        if _sha256(candidate) != predecessor[hash_key]:
            raise BootstrapV5Rejected("predecessor authority drifted")
    inner_hash = _sha256(INNER)
    if _json(OUTER).get("files") != {
        "configs/rq2_public_grid_two_block_pilot_activation_transport_v5.SHA256SUMS.json": inner_hash
    }:
        raise BootstrapV5Rejected("outer manifest binding drifted")
    members = _verify_manifest(INNER)
    resources = config["resource_contract"]
    if (
        resources.get("resource_sample_interval_seconds") != 5.0
        or resources.get("child_private_commit_limit_gib") != 8.0
        or resources.get("child_private_commit_stop_comparison")
        != "greater_than_or_equal"
        or resources.get("minimum_system_commit_available_gib") != 2.0
        or resources.get("system_commit_available_stop_comparison")
        != "less_than_or_equal"
        or resources.get("preflight_minimum_available_commit_gib") != 10.0
        or resources.get("preflight_replaces_runtime_reserve_monitor") is not False
        or resources.get("same_sample_observes_private_and_system_commit") is not True
        or resources.get("mathematical_infeasibility_inferred") is not False
    ):
        raise BootstrapV5Rejected("frozen dual-resource contract drifted")
    frozen_resource = ROOT / resources["frozen_authority_path"]
    _strict_file(frozen_resource)
    if _sha256(frozen_resource) != resources["frozen_authority_sha256"]:
        raise BootstrapV5Rejected("frozen recovery-v2 resource authority drifted")
    formal = config["formal_protection"]
    for path_key, hash_key in (
        ("formal_runner_path", "formal_runner_sha256"),
        ("activated_config_path", "activated_config_sha256"),
    ):
        candidate = ROOT / formal[path_key]
        _strict_file(candidate)
        if _sha256(candidate) != formal[hash_key]:
            raise BootstrapV5Rejected("formal authority drifted")
    checkpoint = ROOT / formal["checkpoint_directory"]
    try:
        checkpoint_files = [entry for entry in checkpoint.iterdir() if entry.is_file()]
    except OSError as exc:
        raise BootstrapV5Rejected("formal checkpoint inventory unavailable") from exc
    if len(checkpoint_files) != int(formal["checkpoint_count"]):
        raise BootstrapV5Rejected("formal checkpoint inventory drifted")
    for root in formal["protected_roots"]:
        if os.path.lexists(ROOT / root):
            raise BootstrapV5Rejected("protected v5 root appeared")
    gates = config["gates"]
    if any(
        gates.get(name) is not False
        for name in (
            "activation_v5_independent_review_passed",
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
        raise BootstrapV5Rejected("closed gates drifted")
    return {
        "validation_passed": True,
        "status": config["status"],
        "bundle_members": members,
        "activation_v5_independent_review_passed": False,
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
        raise BootstrapV5Rejected(
            "v5 candidate is permanently closed; a new reviewed successor is required"
        )
    print(json.dumps(validate_only(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
