"""Closed activation-candidate bootstrap for the nonformal two-block pilot.

This module validates authority and host preconditions.  It has no execution
entry point and deliberately imports no project package, loader, worker, or
solver.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import platform
import socket
import stat
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Any

PROJECT_IMPORTS_PERMITTED = False
ROOT = Path(r"D:\CUHKSZ\Research Project\electricity-grid")
CONFIG_REL = "configs/rq2_public_grid_two_block_pilot_activation_candidate_v1.json"
INNER_REL = (
    "configs/rq2_public_grid_two_block_pilot_activation_candidate_v1.SHA256SUMS.json"
)
OUTER_REL = (
    "configs/rq2_public_grid_two_block_pilot_activation_candidate_v1.OUTER.SHA256SUMS.json"
)
PASS_REL = "configs/rq2_public_grid_two_block_pilot_pre_run_review_pass_v7.json"
PASS_EXPECTED_SHA256 = "a98298f270e57b699808dad0e5b97cd9475a688e6d9ca7b263428ca95aa233a4"
V1_INNER_REL = (
    "configs/rq2_public_grid_two_block_pilot_execution_successor_v1.SHA256SUMS.json"
)
V1_INNER_EXPECTED_SHA256 = (
    "15a86b1fc2aad3112dedc71af17ff857b02236c5d75b05e347398c9e3ab851b2"
)
V1_OUTER_REL = (
    "configs/rq2_public_grid_two_block_pilot_execution_successor_v1.OUTER.SHA256SUMS.json"
)
V1_OUTER_EXPECTED_SHA256 = (
    "c89b8baaa5ec1b52595aa6297d53dc0780a380b59a96455032f8b449a95329a7"
)
REWORK_REL = (
    "configs/rq2_public_grid_two_block_pilot_execution_successor_review_rework_v1.json"
)
REWORK_EXPECTED_SHA256 = (
    "a238cc81845cdecc6a09812932889a19d8dddd7b991b4f3bb17d023ec74183f4"
)
V2_INNER_REL = (
    "configs/rq2_public_grid_two_block_pilot_execution_successor_v2.SHA256SUMS.json"
)
V2_INNER_EXPECTED_SHA256 = (
    "9cf0e626beb00e6fe6fa06acb600fe8406b04bc99bdc1327ec8089610b919bf9"
)
V2_OUTER_REL = (
    "configs/rq2_public_grid_two_block_pilot_execution_successor_v2.OUTER.SHA256SUMS.json"
)
V2_OUTER_EXPECTED_SHA256 = (
    "5b9cdb826f6ae44c1e134574d7b9563e4353dd9bd28c3eebd32e487e57d2a311"
)
V2_PASS_REL = (
    "configs/rq2_public_grid_two_block_pilot_execution_successor_review_pass_v2.json"
)
V2_PASS_EXPECTED_SHA256 = (
    "ad692bfdfec2b90cda49dfc54dc08fd1383bf9e2a4524775676f0f31025ce855"
)
V7_OUTER_REL = "configs/rq2_public_grid_two_block_pilot_candidate_v7.OUTER.SHA256SUMS.json"
V7_OUTER_EXPECTED_SHA256 = (
    "101c0c1399505c9ddf9f1613afc3981139aedf85645a6e8797cc86d217faed35"
)
V7_INNER_REL = "configs/rq2_public_grid_two_block_pilot_candidate_v7.SHA256SUMS.json"
V7_INNER_EXPECTED_SHA256 = (
    "06ad8f34bbe5e9f52755431506e495a670e740092636305b8c12f1f495c6a976"
)
USER_AUTH_REL = "configs/rq2_public_grid_two_block_pilot_user_authorization_v3.yaml"
USER_AUTH_EXPECTED_SHA256 = (
    "f696e76a1fedba8335af62e8914b12bb9385606525cf8170d0b11ffdb3900e52"
)
SELF_REL = "experiments/bootstrap_rq2_public_grid_two_block_pilot_activation_candidate_v1.py"
TEST_REL = "tests/test_rq2_public_grid_two_block_pilot_activation_candidate_v1.py"
_PROJECT_PREFIXES = ("src", "experiments")
_PREIMPORT_PROJECT_MODULES = tuple(
    sorted(
        name
        for name in sys.modules
        if (
            name == "src"
            or name.startswith("src.")
            or (
                name.startswith("experiments.")
                and name != __name__
            )
        )
    )
)


class BootstrapRejected(RuntimeError):
    """A fail-closed successor bootstrap rejection."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise BootstrapRejected(f"authority is unreadable: {path}") from exc
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    _strict_existing(path, regular_file=True)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BootstrapRejected(f"invalid JSON authority: {path}") from exc
    if not isinstance(payload, dict):
        raise BootstrapRejected(f"JSON authority is not an object: {path}")
    return payload


def _is_reparse(path: Path, info: os.stat_result) -> bool:
    attributes = int(getattr(info, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return bool(attributes & reparse_flag)


def _lstat_or_absent(path: Path) -> os.stat_result | None:
    try:
        return os.lstat(path)
    except FileNotFoundError as exc:
        winerror = getattr(exc, "winerror", None)
        if winerror in (2, 3) or exc.errno == errno.ENOENT:
            return None
        raise BootstrapRejected(f"path presence is indeterminate: {path}") from exc
    except OSError as exc:
        raise BootstrapRejected(f"path presence is indeterminate: {path}") from exc


def _path_is_mount(path: Path) -> bool:
    try:
        return os.path.ismount(path)
    except OSError as exc:
        raise BootstrapRejected(f"mount status is indeterminate: {path}") from exc


def _strict_existing(path: Path, *, regular_file: bool) -> None:
    raw = str(path)
    if not os.path.isabs(raw) or os.path.normpath(raw) != raw:
        raise BootstrapRejected(f"non-canonical authority path: {raw}")
    drive, tail = os.path.splitdrive(raw)
    current = Path(drive + os.sep)
    final_info: os.stat_result | None = None
    for segment in [part for part in tail.split(os.sep) if part]:
        current = current / segment
        info = _lstat_or_absent(current)
        if info is None:
            raise BootstrapRejected(f"authority path is absent: {current}")
        if stat.S_ISLNK(info.st_mode) or _is_reparse(current, info):
            raise BootstrapRejected(f"authority path alias/reparse rejected: {current}")
        if _path_is_mount(current) and current != Path(drive + os.sep):
            raise BootstrapRejected(f"nested mount rejected: {current}")
        final_info = info
    if final_info is None:
        final_info = _lstat_or_absent(path)
    if final_info is None:
        raise BootstrapRejected(f"authority path is absent: {path}")
    if regular_file and not stat.S_ISREG(final_info.st_mode):
        raise BootstrapRejected(f"authority is not a regular file: {path}")
    if not regular_file and not stat.S_ISDIR(final_info.st_mode):
        raise BootstrapRejected(f"authority is not a directory: {path}")


def _strict_absent(path: Path) -> None:
    raw = str(path)
    if not os.path.isabs(raw) or os.path.normpath(raw) != raw:
        raise BootstrapRejected(f"non-canonical root path: {raw}")
    drive, tail = os.path.splitdrive(raw)
    current = Path(drive + os.sep)
    parts = [part for part in tail.split(os.sep) if part]
    for index, segment in enumerate(parts):
        current = current / segment
        info = _lstat_or_absent(current)
        if info is None:
            return
        if stat.S_ISLNK(info.st_mode) or _is_reparse(current, info):
            raise BootstrapRejected(f"root ancestor alias/reparse rejected: {current}")
        if _path_is_mount(current) and current != Path(drive + os.sep):
            raise BootstrapRejected(f"root ancestor mount rejected: {current}")
        if index < len(parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise BootstrapRejected(f"root ancestor is not a directory: {current}")
    raise BootstrapRejected(f"fresh root has an existing appearance: {path}")


def _require_hash(relative: str, expected: str) -> Path:
    path = ROOT / relative
    _strict_existing(path, regular_file=True)
    if _sha256(path) != expected:
        raise BootstrapRejected(f"authority hash drift: {relative}")
    return path


def _require_exact_manifest(
    relative: str, schema: str, expected_files: Mapping[str, str]
) -> None:
    payload = _json(ROOT / relative)
    if payload != {"schema": schema, "files": dict(expected_files)}:
        raise BootstrapRejected(f"manifest schema/inventory mismatch: {relative}")
    for member, expected in expected_files.items():
        _require_hash(member, expected)


def _audit_checkpoint_inventory(path: Path, expected: Mapping[str, str]) -> None:
    _strict_existing(path, regular_file=False)
    if len(expected) != 9 or any(
        not isinstance(name, str)
        or not isinstance(digest, str)
        or len(digest) != 64
        for name, digest in expected.items()
    ):
        raise BootstrapRejected("checkpoint hash inventory malformed")
    observed: dict[str, Path] = {}
    try:
        with os.scandir(path) as iterator:
            while True:
                try:
                    entry = next(iterator)
                except StopIteration:
                    break
                except OSError as exc:
                    raise BootstrapRejected("checkpoint enumeration failed") from exc
                if entry.name in observed:
                    raise BootstrapRejected("duplicate checkpoint lexical entry")
                entry_path = Path(entry.path)
                try:
                    info = entry.stat(follow_symlinks=False)
                except OSError as exc:
                    raise BootstrapRejected(
                        f"checkpoint entry is inaccessible: {entry.name}"
                    ) from exc
                if (
                    stat.S_ISLNK(info.st_mode)
                    or _is_reparse(entry_path, info)
                    or not stat.S_ISREG(info.st_mode)
                ):
                    raise BootstrapRejected(
                        f"checkpoint entry is not an ordinary file: {entry.name}"
                    )
                _strict_existing(entry_path, regular_file=True)
                observed[entry.name] = entry_path
    except BootstrapRejected:
        raise
    except OSError as exc:
        raise BootstrapRejected("checkpoint directory enumeration failed") from exc
    if set(observed) != set(expected):
        raise BootstrapRejected("formal checkpoint exact inventory drift")
    for name, checkpoint_path in observed.items():
        if _sha256(checkpoint_path) != expected[name]:
            raise BootstrapRejected(f"checkpoint hash drift: {name}")


def _reject_project_preimport(modules: Sequence[str] | None = None) -> None:
    observed = tuple(_PREIMPORT_PROJECT_MODULES if modules is None else modules)
    if observed:
        raise BootstrapRejected(f"project module preimport rejected: {observed}")


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _verify_activation_contract(config: Mapping[str, Any]) -> None:
    pilot = config.get("nonformal_pilot_contract")
    expected_pilot = {
        "pilot_kind": "nonformal_two_block_pilot",
        "blocks": ["holdout_s20260822_0008", "holdout_s20260822_0009"],
        "execution_order": [
            "holdout_s20260822_0008",
            "holdout_s20260822_0009",
        ],
        "one_fresh_worker_per_block": True,
        "resume_allowed": False,
        "retry_allowed": False,
        "reorder_allowed": False,
        "skip_allowed": False,
        "second_block_requires_first_accepted_evidence": True,
        "external_watchdog_seconds_per_block": 21600,
        "resource_sample_interval_seconds": 5.0,
        "child_private_commit_limit_gib": 8.0,
        "minimum_host_commit_reserve_gib": 2.0,
        "controller_solver_calls": 0,
        "worker_python_path": r"D:\conda_envs\rq2-executor-v2-audit\python.exe",
        "worker_python_sha256": "91df9733b71b293eec9945cc8c5388bbfe1abc5e6ee94a14333076e5f55cb6bf",
    }
    if pilot != expected_pilot:
        raise BootstrapRejected("nonformal pilot contract drifted")

    production = config.get("sealed_production_authority")
    expected_production = {
        "controller_runner_path": "experiments/run_rq2_public_grid_two_block_pilot_candidate_v7.py",
        "controller_runner_sha256": "165b3ef4b1ef4f894b2d1740948ee92033776d547d90b74e02855820227ab105",
        "controller_module": "experiments.run_rq2_public_grid_two_block_pilot_candidate_v7",
        "candidate_config_path": "configs/rq2_public_grid_two_block_pilot_candidate_v7.yaml",
        "candidate_config_sha256": "9a5f1f342e4c4982b1b7bcdf13e71ed204cb2319fc2c29b5a49a7d4fdab8da17",
        "transport_worker_runner_path": "experiments/run_rq2_public_grid_two_block_pilot_candidate_v4.py",
        "transport_worker_runner_sha256": "3b6e55605f56cee1e871d72b15ddfec0963ce727ec863a08f4cbac441d7541e9",
        "dispatch_callable": "v7.v4._dispatch_one",
        "worker_callable": "v7.v4._worker_from_capability",
        "publication_callable": "v7._publish_result",
        "recovery_callable": "v7.load_verified_success_commit",
        "scientific_semantics_copied_into_activation": False,
        "future_wrapper_must_import_only_after_authority_pass": True,
    }
    if production != expected_production:
        raise BootstrapRejected("sealed production authority drifted")
    _require_hash(
        expected_production["controller_runner_path"],
        expected_production["controller_runner_sha256"],
    )
    _require_hash(
        expected_production["candidate_config_path"],
        expected_production["candidate_config_sha256"],
    )
    _require_hash(
        expected_production["transport_worker_runner_path"],
        expected_production["transport_worker_runner_sha256"],
    )

    ledger = config.get("attempt_ledger_contract")
    expected_fields = [
        "execution_index",
        "block_id",
        "child_pid",
        "child_create_time_ns",
        "nonce",
        "request_sha256",
        "ack_sha256",
        "attempt_receipt_sha256",
        "payload_sha256",
        "accepted_evidence_sha256",
        "predecessor_accepted_evidence_sha256",
        "proven_infeasible",
        "classification",
    ]
    if (
        not isinstance(ledger, dict)
        or ledger.get("required_fields") != expected_fields
        or ledger.get("immutable_after_acceptance") is not True
        or ledger.get("accepted_classification") != "accepted"
        or ledger.get("fresh_pid_required_between_blocks") is not True
        or ledger.get("controller_may_terminate_only_owned_child") is not True
        or ledger.get("ownership_binding_fields")
        != ["child_pid", "child_create_time_ns", "nonce", "request_sha256"]
    ):
        raise BootstrapRejected("attempt-ledger contract drifted")
    expected_failure = {
        "timeout": "honest_incomplete",
        "resource_stop": "honest_incomplete",
        "nonzero_exit": "honest_incomplete",
        "missing_incumbent": "honest_incomplete",
        "unresolved": "honest_incomplete",
        "invalid_or_raced_publication": "commit_indeterminate",
        "any_failure_is_mathematical_infeasibility_evidence": False,
    }
    if config.get("failure_semantics") != expected_failure:
        raise BootstrapRejected("failure semantics drifted")

    formal = config.get("formal_invariants")
    if (
        not isinstance(formal, dict)
        or formal.get("formal_entrypoints_reachable") is not False
        or formal.get("gurobi_entrypoints_reachable") is not False
        or formal.get("recovery_activation_entrypoints_reachable") is not False
    ):
        raise BootstrapRejected("formal entrypoints are not unreachable")


def _verify_static_authority() -> dict[str, Any]:
    _strict_existing(ROOT, regular_file=False)
    v1_outer = _require_hash(V1_OUTER_REL, V1_OUTER_EXPECTED_SHA256)
    _require_hash(V1_INNER_REL, V1_INNER_EXPECTED_SHA256)
    rework_path = _require_hash(REWORK_REL, REWORK_EXPECTED_SHA256)
    if _json(v1_outer) != {
        "schema": "rq2_public_grid_two_block_pilot_execution_successor_outer_v1",
        "files": {V1_INNER_REL: V1_INNER_EXPECTED_SHA256},
    }:
        raise BootstrapRejected("execution-successor v1 outer authority mismatch")
    v1_members = {
        "configs/rq2_public_grid_two_block_pilot_execution_successor_v1.json": "9761ba5f2d384c22ed7f79b8d32aedf9f1a8292c94ded77b262273978f4e1836",
        PASS_REL: PASS_EXPECTED_SHA256,
        "experiments/bootstrap_rq2_public_grid_two_block_pilot_execution_successor_v1.py": "38dfb0a5608a98f1709ac9d25f77db1a3bb22334599af21ef8b06856ae70408d",
        "tests/test_rq2_public_grid_two_block_pilot_execution_successor_v1.py": "766326b728295999b90a3ecb6d2323427b3b06e101326c8ff2d457710c23ca04",
    }
    if _json(ROOT / V1_INNER_REL) != {
        "schema": "rq2_public_grid_two_block_pilot_execution_successor_bundle_v1",
        "files": v1_members,
    }:
        raise BootstrapRejected("execution-successor v1 inner authority mismatch")
    for member, expected in v1_members.items():
        _require_hash(member, expected)
    rework = _json(rework_path)
    rework_effect = rework.get("effect")
    if (
        rework.get("verdict") != "REWORK"
        or not isinstance(rework_effect, dict)
        or rework_effect.get("no_execution_authority") is not True
        or rework_effect.get("successor_execution_authorized") is not False
        or rework.get("reviewed_artifacts", {}).get(V1_OUTER_REL)
        != V1_OUTER_EXPECTED_SHA256
    ):
        raise BootstrapRejected("execution-successor v1 REWORK scope mismatch")
    v2_outer = _require_hash(V2_OUTER_REL, V2_OUTER_EXPECTED_SHA256)
    _require_hash(V2_INNER_REL, V2_INNER_EXPECTED_SHA256)
    v2_pass_path = _require_hash(V2_PASS_REL, V2_PASS_EXPECTED_SHA256)
    if _json(v2_outer) != {
        "schema": "rq2_public_grid_two_block_pilot_execution_successor_outer_v2",
        "files": {V2_INNER_REL: V2_INNER_EXPECTED_SHA256},
    }:
        raise BootstrapRejected("execution-successor v2 outer authority mismatch")
    v2_members = {
        "configs/rq2_public_grid_two_block_pilot_execution_successor_v2.json": "4b88cdccabdb731607b7064ac60a73994b8c9df0948a99b4462f1594c7277245",
        REWORK_REL: REWORK_EXPECTED_SHA256,
        "experiments/bootstrap_rq2_public_grid_two_block_pilot_execution_successor_v2.py": "97b092ec84f97dc2334b9c8fddc5df037f6a7efc3502701b7f6fb540cd1dad80",
        "tests/test_rq2_public_grid_two_block_pilot_execution_successor_v2.py": "6e494152dfdb5721d4ec877ea630cabea73f61d5768dd8835fccbb55676dd312",
    }
    if _json(ROOT / V2_INNER_REL) != {
        "schema": "rq2_public_grid_two_block_pilot_execution_successor_bundle_v2",
        "files": v2_members,
    }:
        raise BootstrapRejected("execution-successor v2 inner authority mismatch")
    for member, expected in v2_members.items():
        _require_hash(member, expected)
    v2_review = _json(v2_pass_path)
    v2_effect = v2_review.get("effect")
    if (
        v2_review.get("verdict") != "PASS"
        or v2_review.get("reviewer_role") != "independent_sol_reviewer"
        or v2_review.get("reviewed_artifacts", {}).get(V2_OUTER_REL)
        != V2_OUTER_EXPECTED_SHA256
        or not isinstance(v2_effect, dict)
        or v2_effect.get("no_execution_authority") is not True
        or v2_effect.get("activation_execution_authorized") is not False
        or v2_effect.get("versioned_activation_candidate_creation_authorized")
        is not True
    ):
        raise BootstrapRejected("execution-successor v2 PASS scope mismatch")
    pass_path = _require_hash(PASS_REL, PASS_EXPECTED_SHA256)
    v7_outer = _require_hash(V7_OUTER_REL, V7_OUTER_EXPECTED_SHA256)
    _require_hash(V7_INNER_REL, V7_INNER_EXPECTED_SHA256)
    _require_hash(USER_AUTH_REL, USER_AUTH_EXPECTED_SHA256)

    v7_inner = _json(ROOT / V7_INNER_REL)
    v7_outer_payload = _json(v7_outer)
    if v7_outer_payload != {
        "schema": "rq2_public_grid_two_block_pilot_candidate_outer_v7",
        "files": {V7_INNER_REL: V7_INNER_EXPECTED_SHA256},
    }:
        raise BootstrapRejected("v7 outer authority mismatch")
    expected_v7_members = {
        "configs/rq2_public_grid_two_block_pilot_candidate_v7.yaml": "9a5f1f342e4c4982b1b7bcdf13e71ed204cb2319fc2c29b5a49a7d4fdab8da17",
        "configs/rq2_public_grid_two_block_pilot_pre_run_review_escalation_v6.yaml": "c26afa1ddf77c98e5048609bc6cf17e30231e6417c8208069acce42a803754bd",
        "experiments/run_rq2_public_grid_two_block_pilot_candidate_v7.py": "165b3ef4b1ef4f894b2d1740948ee92033776d547d90b74e02855820227ab105",
        "experiments/validate_rq2_public_grid_two_block_pilot_candidate_v7.py": "d84a9ba2919ff8ed59aa42c67e3f6f2f8a58c064007e9d755405217735cb0c92",
        "tests/test_rq2_public_grid_two_block_pilot_candidate_v7.py": "052a2d11757656398538a0ab705a9abebf7fed165edb557b869d6f8adaced99d",
    }
    if v7_inner != {
        "schema": "rq2_public_grid_two_block_pilot_candidate_bundle_v7",
        "files": expected_v7_members,
    }:
        raise BootstrapRejected("v7 inner authority mismatch")
    for member, expected in expected_v7_members.items():
        _require_hash(member, expected)

    review = _json(pass_path)
    reviewed = review.get("reviewed_artifacts")
    effect = review.get("effect")
    if (
        review.get("verdict") != "PASS"
        or not isinstance(reviewed, dict)
        or reviewed.get(V7_OUTER_REL) != V7_OUTER_EXPECTED_SHA256
        or not isinstance(effect, dict)
        or effect.get("no_execution_authority") is not True
        or effect.get("successor_execution_authorized") is not False
        or effect.get("two_block_pilot_execution_authorized") is not False
        or effect.get("formal_execution_ready") is not False
    ):
        raise BootstrapRejected("v7 PASS receipt scope mismatch")

    config_path = ROOT / CONFIG_REL
    _strict_existing(config_path, regular_file=True)
    config = _json(config_path)
    if (
        config.get("schema")
        != "rq2_public_grid_two_block_pilot_activation_candidate_v1"
        or config.get("status")
        != "nonformal_two_block_pilot_activation_candidate_closed"
        or config.get("scientific_transport_ledger_postcommit_or_frozen_formal_semantics_changed")
        is not False
    ):
        raise BootstrapRejected("activation config identity mismatch")
    predecessor = config.get("predecessor_authority")
    expected_predecessor = {
        "successor_v2_inner_path": V2_INNER_REL,
        "successor_v2_inner_sha256": V2_INNER_EXPECTED_SHA256,
        "successor_v2_outer_path": V2_OUTER_REL,
        "successor_v2_outer_sha256": V2_OUTER_EXPECTED_SHA256,
        "successor_v2_review_pass_path": V2_PASS_REL,
        "successor_v2_review_pass_sha256": V2_PASS_EXPECTED_SHA256,
        "successor_v1_outer_path": V1_OUTER_REL,
        "successor_v1_outer_sha256": V1_OUTER_EXPECTED_SHA256,
        "successor_v1_rework_path": REWORK_REL,
        "successor_v1_rework_sha256": REWORK_EXPECTED_SHA256,
        "v7_outer_path": V7_OUTER_REL,
        "v7_outer_sha256": V7_OUTER_EXPECTED_SHA256,
        "v7_review_pass_path": PASS_REL,
        "v7_review_pass_sha256": PASS_EXPECTED_SHA256,
        "user_authorization_path": USER_AUTH_REL,
        "user_authorization_sha256": USER_AUTH_EXPECTED_SHA256,
        "user_authorization_scope": "future_conditional_authority_only_after_pilot_postreview_and_activation_pass",
    }
    if predecessor != expected_predecessor:
        raise BootstrapRejected("activation predecessor authority mismatch")
    gates = config.get("gates")
    activation = config.get("future_external_activation_review")
    if not isinstance(gates, dict) or not isinstance(activation, dict):
        raise BootstrapRejected("activation gates malformed")
    required_false = {
        "activation_candidate_independent_review_passed",
        "activation_review_present",
        "activation_execution_ready",
        "two_block_pilot_execution_ready",
        "two_block_pilot_executed",
        "formal_activation_present",
        "formal_execution_ready",
        "user_formal_run_authorized",
        "formal_result_exists",
        "claim",
        "security_certified",
    }
    if any(gates.get(name) is not False for name in required_false):
        raise BootstrapRejected("activation execution/claim gates are not closed")
    if (
        activation.get("receipt_path") is not None
        or activation.get("receipt_sha256") is not None
        or activation.get("reviewed_activation_outer_sha256") is not None
        or activation.get("future_execution_wrapper_path") is not None
        or activation.get("future_execution_wrapper_sha256") is not None
        or activation.get("receipt_hash_must_be_bound_by_future_wrapper") is not True
        or activation.get("double_read_before_project_import_required") is not True
        or activation.get("dynamic_self_acceptance_forbidden") is not True
    ):
        raise BootstrapRejected("future activation-review boundary mismatch")

    _verify_activation_contract(config)

    inner = _json(ROOT / INNER_REL)
    inner_files = inner.get("files")
    if (
        inner.get("schema")
        != "rq2_public_grid_two_block_pilot_activation_candidate_bundle_v1"
        or not isinstance(inner_files, dict)
        or set(inner_files) != {CONFIG_REL, V2_PASS_REL, SELF_REL, TEST_REL}
    ):
        raise BootstrapRejected("activation inner manifest mismatch")
    for member, expected in inner_files.items():
        if not isinstance(expected, str) or len(expected) != 64:
            raise BootstrapRejected("successor inner hash malformed")
        _require_hash(member, expected)
    inner_hash = _sha256(ROOT / INNER_REL)
    _require_exact_manifest(
        OUTER_REL,
        "rq2_public_grid_two_block_pilot_activation_candidate_outer_v1",
        {INNER_REL: inner_hash},
    )

    formal = config.get("formal_invariants")
    if not isinstance(formal, dict):
        raise BootstrapRejected("formal invariant contract malformed")
    _require_hash(str(formal["formal_runner_path"]), str(formal["formal_runner_sha256"]))
    _require_hash(
        str(formal["activated_formal_config_path"]),
        str(formal["activated_formal_config_sha256"]),
    )
    checkpoint_hashes = formal.get("checkpoint_sha256")
    if not isinstance(checkpoint_hashes, dict):
        raise BootstrapRejected("checkpoint hash inventory malformed")
    _audit_checkpoint_inventory(
        ROOT / str(formal["checkpoint_directory"]), checkpoint_hashes
    )
    return config


class _PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_ulong),
        ("cntUsage", ctypes.c_ulong),
        ("th32ProcessID", ctypes.c_ulong),
        ("th32DefaultHeapID", ctypes.c_void_p),
        ("th32ModuleID", ctypes.c_ulong),
        ("cntThreads", ctypes.c_ulong),
        ("th32ParentProcessID", ctypes.c_ulong),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", ctypes.c_ulong),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


class _WindowsToolhelpAPI:
    def __init__(self) -> None:
        if os.name != "nt":
            raise BootstrapRejected("locked successor requires Windows")
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
        self.kernel32.CreateToolhelp32Snapshot.argtypes = [
            ctypes.c_ulong,
            ctypes.c_ulong,
        ]
        self.kernel32.Process32FirstW.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_PROCESSENTRY32W),
        ]
        self.kernel32.Process32NextW.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(_PROCESSENTRY32W),
        ]
        self.kernel32.CloseHandle.argtypes = [ctypes.c_void_p]

    def create_snapshot(self) -> object:
        snapshot = self.kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
        if snapshot == ctypes.c_void_p(-1).value:
            raise BootstrapRejected("process inventory snapshot failed")
        return snapshot

    def first(self, snapshot: object, entry: _PROCESSENTRY32W) -> bool:
        ctypes.set_last_error(0)
        return bool(self.kernel32.Process32FirstW(snapshot, ctypes.byref(entry)))

    def next(self, snapshot: object, entry: _PROCESSENTRY32W) -> bool:
        ctypes.set_last_error(0)
        return bool(self.kernel32.Process32NextW(snapshot, ctypes.byref(entry)))

    @staticmethod
    def last_error() -> int:
        return int(ctypes.get_last_error())

    def close(self, snapshot: object) -> None:
        self.kernel32.CloseHandle(snapshot)


def _windows_processes(api: Any | None = None) -> list[tuple[int, str]]:
    toolhelp = _WindowsToolhelpAPI() if api is None else api
    snapshot = toolhelp.create_snapshot()
    entry = _PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    rows: list[tuple[int, str]] = []
    try:
        if not toolhelp.first(snapshot, entry):
            raise BootstrapRejected("Process32FirstW failed")
        while True:
            rows.append((int(entry.th32ProcessID), str(entry.szExeFile).lower()))
            if toolhelp.next(snapshot, entry):
                continue
            error = toolhelp.last_error()
            if error == 18:
                break
            raise BootstrapRejected(f"Process32NextW failed with error {error}")
    finally:
        toolhelp.close(snapshot)
    if not any(pid == os.getpid() for pid, _name in rows):
        raise BootstrapRejected("process inventory omits current PID")
    return rows


def _process_age_seconds() -> float:
    if os.name != "nt":
        raise BootstrapRejected("locked successor requires Windows")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", ctypes.c_ulong), ("dwHighDateTime", ctypes.c_ulong)]

        @property
        def ticks(self) -> int:
            return (int(self.dwHighDateTime) << 32) | int(self.dwLowDateTime)

    creation = FILETIME()
    exit_time = FILETIME()
    kernel = FILETIME()
    user = FILETIME()
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    kernel32.GetProcessTimes.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(FILETIME),
        ctypes.POINTER(FILETIME),
        ctypes.POINTER(FILETIME),
        ctypes.POINTER(FILETIME),
    ]
    if not kernel32.GetProcessTimes(
        kernel32.GetCurrentProcess(),
        ctypes.byref(creation),
        ctypes.byref(exit_time),
        ctypes.byref(kernel),
        ctypes.byref(user),
    ):
        raise BootstrapRejected("current process creation time unavailable")
    created_epoch = (creation.ticks - 116444736000000000) / 10_000_000
    return max(0.0, time.time() - created_epoch)


def _available_virtual_bytes() -> int:
    if os.name != "nt":
        raise BootstrapRejected("locked successor requires Windows")

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(status)
    if not ctypes.WinDLL("kernel32", use_last_error=True).GlobalMemoryStatusEx(
        ctypes.byref(status)
    ):
        raise BootstrapRejected("virtual memory status unavailable")
    return int(status.ullAvailPageFile)


def _runtime_observation() -> dict[str, Any]:
    executable_path = Path(sys.executable)
    _strict_existing(executable_path, regular_file=True)
    return {
        "executable": sys.executable,
        "executable_sha256": _sha256(executable_path),
        "version": platform.python_version(),
        "orig_argv": list(sys.orig_argv),
        "cwd": os.getcwd(),
        "hostname": socket.gethostname(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "environment": dict(os.environ),
        "process_age_seconds": _process_age_seconds(),
        "processes": _windows_processes(),
        "available_virtual_bytes": _available_virtual_bytes(),
    }


def _verify_locked_python(contract: Mapping[str, Any]) -> None:
    executable = Path(str(contract["locked_python_executable"]))
    _strict_existing(executable, regular_file=True)
    if _sha256(executable) != contract["locked_python_sha256"]:
        raise BootstrapRejected("locked Python executable hash drift")


def _verify_runtime(config: Mapping[str, Any], observed: Mapping[str, Any]) -> None:
    contract = config.get("bootstrap_contract")
    if not isinstance(contract, dict):
        raise BootstrapRejected("bootstrap contract malformed")
    _verify_locked_python(contract)
    executable = str(contract["locked_python_executable"])
    entry = str(ROOT / str(contract["entry_script"]))
    expected_argv = [executable, *list(contract["validate_only_argv_suffix"])]
    exact = {
        "executable": executable,
        "executable_sha256": contract["locked_python_sha256"],
        "version": contract["locked_python_version"],
        "orig_argv": expected_argv,
        "cwd": contract["exact_cwd"],
        "hostname": contract["host"]["hostname"],
        "system": contract["host"]["system"],
        "release": contract["host"]["release"],
        "machine": contract["host"]["machine"],
        "environment": contract["exact_environment"],
    }
    if expected_argv[3] != entry:
        raise BootstrapRejected("configured entry script mismatch")
    for key, expected in exact.items():
        if observed.get(key) != expected:
            raise BootstrapRejected(f"runtime identity mismatch: {key}")
    age = observed.get("process_age_seconds")
    if not isinstance(age, (int, float)) or not 0.0 <= float(age) <= float(
        contract["maximum_process_age_seconds"]
    ):
        raise BootstrapRejected("process is not fresh")
    processes = observed.get("processes")
    if not isinstance(processes, list):
        raise BootstrapRejected("process inventory malformed")
    rejected_names = {str(name).lower() for name in contract["reject_other_process_image_names"]}
    current_pid = os.getpid()
    active = [
        (pid, name)
        for pid, name in processes
        if int(pid) != current_pid and str(name).lower() in rejected_names
    ]
    if active:
        raise BootstrapRejected(f"active related process rejected: {active}")
    available = observed.get("available_virtual_bytes")
    minimum = int(float(contract["minimum_available_virtual_memory_gib"]) * 1024**3)
    if not isinstance(available, int) or available < minimum:
        raise BootstrapRejected("insufficient available virtual memory")


def _activation_review_chain(config: Mapping[str, Any]) -> dict[str, str]:
    predecessor = config["predecessor_authority"]
    return {
        str(predecessor["successor_v2_inner_path"]): str(
            predecessor["successor_v2_inner_sha256"]
        ),
        str(predecessor["successor_v2_outer_path"]): str(
            predecessor["successor_v2_outer_sha256"]
        ),
        str(predecessor["successor_v2_review_pass_path"]): str(
            predecessor["successor_v2_review_pass_sha256"]
        ),
        str(predecessor["successor_v1_outer_path"]): str(
            predecessor["successor_v1_outer_sha256"]
        ),
        str(predecessor["successor_v1_rework_path"]): str(
            predecessor["successor_v1_rework_sha256"]
        ),
        str(predecessor["v7_outer_path"]): str(predecessor["v7_outer_sha256"]),
        str(predecessor["v7_review_pass_path"]): str(
            predecessor["v7_review_pass_sha256"]
        ),
        str(predecessor["user_authorization_path"]): str(
            predecessor["user_authorization_sha256"]
        ),
    }


def _validate_external_activation_review(
    payload: Mapping[str, Any],
    *,
    expected_outer_sha256: str,
    config: Mapping[str, Any],
) -> None:
    """Validate a future independent receipt; this does not grant authority here."""

    expected_effect = {
        "activation_candidate_independent_review_passed": True,
        "activation_execution_authorized": True,
        "two_block_pilot_execution_authorized": True,
        "formal_activation_authorized": False,
        "formal_execution_ready": False,
        "user_formal_run_authorized": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
        "no_formal_execution_authority": True,
    }
    reviewed_activation = payload.get("reviewed_activation")
    if (
        payload.get("schema")
        != "rq2_public_grid_two_block_pilot_activation_review_pass_v1"
        or payload.get("version") != 1
        or payload.get("reviewer_role") != "independent_sol_reviewer"
        or payload.get("verdict") != "PASS"
        or payload.get("findings") != {"blocker": [], "major": [], "minor": []}
        or reviewed_activation
        != {"outer_path": OUTER_REL, "outer_sha256": expected_outer_sha256}
        or payload.get("reviewed_chain") != _activation_review_chain(config)
        or payload.get("user_authorization_scope")
        != config["predecessor_authority"]["user_authorization_scope"]
        or payload.get("effect") != expected_effect
    ):
        raise BootstrapRejected("external activation-review receipt mismatch")


def _read_review_receipt(path: Path) -> tuple[bytes, dict[str, Any]]:
    _strict_existing(path, regular_file=True)
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BootstrapRejected("external activation-review receipt is unreadable") from exc
    if not isinstance(payload, dict):
        raise BootstrapRejected("external activation-review receipt is not an object")
    return raw, payload


def _load_external_activation_review_twice(
    path: Path,
    *,
    expected_receipt_sha256: str,
    expected_outer_sha256: str,
    config: Mapping[str, Any],
    post_first_read: Any | None = None,
) -> dict[str, Any]:
    """Double-read a wrapper-bound receipt and reject path/content races."""

    if not _is_sha256(expected_receipt_sha256) or not _is_sha256(
        expected_outer_sha256
    ):
        raise BootstrapRejected("future wrapper receipt binding is malformed")
    first_raw, first_payload = _read_review_receipt(path)
    if hashlib.sha256(first_raw).hexdigest() != expected_receipt_sha256:
        raise BootstrapRejected("external activation-review receipt hash mismatch")
    _validate_external_activation_review(
        first_payload,
        expected_outer_sha256=expected_outer_sha256,
        config=config,
    )
    if post_first_read is not None:
        post_first_read()
    second_raw, second_payload = _read_review_receipt(path)
    if second_raw != first_raw or second_payload != first_payload:
        raise BootstrapRejected("external activation-review receipt changed during check")
    if hashlib.sha256(second_raw).hexdigest() != expected_receipt_sha256:
        raise BootstrapRejected("external activation-review receipt hash drift")
    _validate_external_activation_review(
        second_payload,
        expected_outer_sha256=expected_outer_sha256,
        config=config,
    )
    return second_payload


def _require_execution_authority(
    config: Mapping[str, Any], receipt_path: str | None
) -> None:
    """Fail closed until a later immutable wrapper binds review path/hash/outer."""

    binding = config.get("future_external_activation_review")
    if not isinstance(binding, dict):
        raise BootstrapRejected("future activation-review binding malformed")
    if (
        binding.get("receipt_path") is None
        or binding.get("receipt_sha256") is None
        or binding.get("reviewed_activation_outer_sha256") is None
        or binding.get("future_execution_wrapper_path") is None
        or binding.get("future_execution_wrapper_sha256") is None
    ):
        raise BootstrapRejected(
            "activation review is not bound by an immutable execution wrapper"
        )
    if receipt_path != binding["receipt_path"]:
        raise BootstrapRejected("activation-review receipt path is not wrapper-bound")
    _load_external_activation_review_twice(
        ROOT / str(receipt_path),
        expected_receipt_sha256=str(binding["receipt_sha256"]),
        expected_outer_sha256=str(binding["reviewed_activation_outer_sha256"]),
        config=config,
    )
    raise BootstrapRejected("closed activation candidate has no execution entry point")


def _valid_attempt_record(
    record: Mapping[str, Any], required_fields: Sequence[str]
) -> None:
    if set(record) != set(required_fields):
        raise BootstrapRejected("attempt-ledger record inventory mismatch")
    if (
        not isinstance(record["execution_index"], int)
        or isinstance(record["execution_index"], bool)
        or record["execution_index"] not in (1, 2)
        or not isinstance(record["child_pid"], int)
        or isinstance(record["child_pid"], bool)
        or record["child_pid"] <= 0
        or not isinstance(record["child_create_time_ns"], int)
        or isinstance(record["child_create_time_ns"], bool)
        or record["child_create_time_ns"] <= 0
        or not isinstance(record["nonce"], str)
        or not record["nonce"]
        or record["proven_infeasible"] is not False
        or record["classification"]
        not in {"accepted", "honest_incomplete", "commit_indeterminate"}
    ):
        raise BootstrapRejected("attempt-ledger record value mismatch")
    for field in (
        "request_sha256",
        "ack_sha256",
        "attempt_receipt_sha256",
        "payload_sha256",
        "accepted_evidence_sha256",
    ):
        if not _is_sha256(record[field]):
            raise BootstrapRejected(f"attempt-ledger hash malformed: {field}")
    predecessor = record["predecessor_accepted_evidence_sha256"]
    if predecessor is not None and not _is_sha256(predecessor):
        raise BootstrapRejected("predecessor accepted-evidence hash malformed")


def _append_attempt(
    ledger: Sequence[Mapping[str, Any]],
    record: Mapping[str, Any],
    config: Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    """Append exactly one preregistered attempt to an immutable two-block ledger."""

    if len(ledger) >= 2:
        raise BootstrapRejected("retry or extra attempt rejected")
    contract = config["attempt_ledger_contract"]
    required = contract["required_fields"]
    _valid_attempt_record(record, required)
    blocks = config["nonformal_pilot_contract"]["execution_order"]
    expected_index = len(ledger) + 1
    if (
        record["execution_index"] != expected_index
        or record["block_id"] != blocks[expected_index - 1]
    ):
        raise BootstrapRejected("pilot block order/index mismatch")
    if expected_index == 1:
        if record["predecessor_accepted_evidence_sha256"] is not None:
            raise BootstrapRejected("first attempt has a predecessor")
    else:
        first = ledger[0]
        if first.get("classification") != contract["accepted_classification"]:
            raise BootstrapRejected("second block requires accepted first-block evidence")
        if record["predecessor_accepted_evidence_sha256"] != first.get(
            "accepted_evidence_sha256"
        ):
            raise BootstrapRejected("second-block predecessor evidence mismatch")
        if record["child_pid"] == first.get("child_pid"):
            raise BootstrapRejected("fresh worker PID required between blocks")
    immutable = MappingProxyType(dict(record))
    return (*ledger, immutable)


def _classify_failure(reason: str, config: Mapping[str, Any]) -> str:
    semantics = config["failure_semantics"]
    if reason not in semantics or reason == "any_failure_is_mathematical_infeasibility_evidence":
        raise BootstrapRejected("unregistered failure reason")
    classification = semantics[reason]
    if classification not in {"honest_incomplete", "commit_indeterminate"}:
        raise BootstrapRejected("failure classification is unsafe")
    return str(classification)


def _owned_child_matches(
    expected: Mapping[str, Any], observed: Mapping[str, Any], config: Mapping[str, Any]
) -> bool:
    fields = config["attempt_ledger_contract"]["ownership_binding_fields"]
    if set(expected) != set(fields) or set(observed) != set(fields):
        raise BootstrapRejected("child ownership inventory mismatch")
    return all(expected[field] == observed[field] for field in fields)


def _future_execution_plan(config: Mapping[str, Any]) -> Mapping[str, Any]:
    pilot = config["nonformal_pilot_contract"]
    production = config["sealed_production_authority"]
    formal = config["formal_invariants"]
    return MappingProxyType(
        {
            "blocks": tuple(pilot["execution_order"]),
            "fresh_worker_per_block": pilot["one_fresh_worker_per_block"],
            "dispatch_callable": production["dispatch_callable"],
            "worker_callable": production["worker_callable"],
            "publication_callable": production["publication_callable"],
            "recovery_callable": production["recovery_callable"],
            "formal_entrypoints_reachable": formal["formal_entrypoints_reachable"],
            "gurobi_entrypoints_reachable": formal["gurobi_entrypoints_reachable"],
            "recovery_activation_entrypoints_reachable": formal[
                "recovery_activation_entrypoints_reachable"
            ],
        }
    )


def _verify_roots(config: Mapping[str, Any], appearances: Mapping[str, bool] | None) -> None:
    relative_roots = list(config.get("fresh_roots", []))
    if len(relative_roots) != 5 or len(set(relative_roots)) != 5:
        raise BootstrapRejected("exact five-root inventory required")
    formal = config.get("formal_invariants")
    if not isinstance(formal, dict):
        raise BootstrapRejected("formal invariant roots malformed")
    relative_roots.extend(list(formal["protected_roots_clean_absent"]))
    for relative in relative_roots:
        target = ROOT / str(relative)
        if appearances is None:
            _strict_absent(target)
        elif appearances.get(str(relative)) is not False:
            raise BootstrapRejected(f"root appearance rejected: {relative}")


def validate(
    *,
    preimport_modules: Sequence[str] | None = None,
    runtime: Mapping[str, Any] | None = None,
    root_appearances: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    """Validate the closed activation candidate without project code or execution."""

    _reject_project_preimport(preimport_modules)
    config = _verify_static_authority()
    observed = _runtime_observation() if runtime is None else runtime
    _verify_runtime(config, observed)
    _verify_roots(config, root_appearances)
    return {
        "schema": "rq2_public_grid_two_block_pilot_activation_candidate_validation_v1",
        "validation_passed": True,
        "status": "READY_FOR_INDEPENDENT_REVIEW",
        "execution_ready": False,
        "successor_v2_independent_review_passed": True,
        "activation_candidate_independent_review_passed": False,
        "activation_review_present": False,
        "project_modules_imported": 0,
        "worker_processes_started": 0,
        "scientific_loader_calls": 0,
        "solver_calls": 0,
        "result_files_written": 0,
        "formal_writes": 0,
        "formal_execution_ready": False,
        "claim": False,
        "security_certified": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--activation-review-receipt")
    args = parser.parse_args(argv)
    if args.validate_only:
        if args.activation_review_receipt is not None:
            raise BootstrapRejected("validate-only rejects activation-review receipt")
        print(json.dumps(validate(), indent=2, sort_keys=True))
        return 0
    _reject_project_preimport()
    config = _verify_static_authority()
    _require_execution_authority(config, args.activation_review_receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
