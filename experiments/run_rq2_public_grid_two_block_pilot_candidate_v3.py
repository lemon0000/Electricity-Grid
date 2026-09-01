"""Closed RQ2 0008/0009 pilot remediation candidate v3.

The worker receives authority only through controller-created anonymous pipes.
There is no request-file CLI.  This design rejects file-level request forgery;
it does not claim protection from same-permission process injection or handle
duplication, an administrator, or the kernel.  The current candidate is sealed
closed and cannot start a worker or solver.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import os
import secrets
import shutil
import stat
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from ctypes import wintypes
from pathlib import Path
from typing import Any

from experiments import (
    run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_v1 as recovery,
)
from src.evaluation.execution_machine import (
    execution_host_status,
    require_execution_host,
)
from src.grid.rts_gmlc import load_rts_gmlc_chronological_data

ROOT = Path(__file__).resolve().parents[1]
MODULE = "experiments.run_rq2_public_grid_two_block_pilot_candidate_v3"
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v3.yaml"
AUTHORIZATION = ROOT / "configs/rq2_public_grid_two_block_pilot_user_authorization_v3.yaml"
BUNDLE = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v3.SHA256SUMS.json"
OUTER = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v3.OUTER.SHA256SUMS.json"
ESCALATION = ROOT / "configs/rq2_public_grid_two_block_pilot_pre_run_review_escalation_v2.yaml"
BASE_CONFIG = ROOT / "configs/rts_gmlc_public_grid_need_dispatch_v4_highs_process_isolated_v1.yaml"
RECOVERY_MANIFEST = ROOT / "configs/rq2_public_grid_solver_recovery_v2.SHA256SUMS.json"
RECOVERY_PASS = ROOT / "configs/rq2_public_grid_solver_recovery_implementation_review_pass_v2.yaml"
SEMANTIC_CONFIG = ROOT / "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml"
SEMANTIC_MANIFEST = ROOT / "configs/rq2_public_solver_pilot_semantic_successor_v1.SHA256SUMS.json"
SEMANTIC_VALIDATOR = ROOT / "experiments/validate_rq2_public_solver_pilot_semantic_successor_v1.py"
GUROBI_CONFIG = ROOT / "results/execution_configs/rq2_public_successor_v2/grid.yaml"
GUROBI_0008 = (
    ROOT
    / "results/checkpoints/rts_gmlc_public_grid_need_dispatch_v4_gurobi"
    / "holdout_s20260822_0008.json"
)

BLOCKS = ["holdout_s20260822_0008", "holdout_s20260822_0009"]
CONFIG_SCHEMA = "rq2_public_grid_two_block_pilot_candidate_v3"
ENVELOPE_SCHEMA = "rq2_public_grid_two_block_pilot_capability_envelope_v3"
HELLO_SCHEMA = "rq2_public_grid_two_block_pilot_worker_hello_v3"
ACK_SCHEMA = "rq2_public_grid_two_block_pilot_capability_ack_v3"
RESULT_SCHEMA = "rq2_public_grid_two_block_pilot_worker_result_v3"
RECEIPT_SCHEMA = "rq2_public_grid_two_block_pilot_worker_receipt_v3"
CONTROLLER_SCHEMA = "rq2_public_grid_two_block_pilot_controller_receipt_v3"
TREE_SCHEMA = "rq2_public_grid_two_block_pilot_typed_tree_v3"
MAX_FRAME_BYTES = 32 * 1024 * 1024

V1_INNER_SHA256 = "cdb70f0dc87eff25f0d2082d207bddfacb4701c75042065f1aa06e38a6a5fb15"
V1_OUTER_SHA256 = "7874a9bdb83d36de98e7626bbe259fd607f1d9d2f8e5669e9924c6f84a02306f"
V2_INNER_SHA256 = "fd7e0d92e78c92991602fe1dcd25c0a20e00fd6bc8f4f927a3431dda816b2598"
V2_OUTER_SHA256 = "fb2185a707e905480d6d0fc03b95c178420293807b309459548f99a31f782743"
ESCALATION_SHA256 = "4a683712730fc37dc19d757db83ed660efcf2652bf7b66808783f635c3cfd88b"
RECOVERY_MANIFEST_SHA256 = "b300a040fc481beea094702404f4d00eb176403e40f7909d2d704f7fd2195729"
RECOVERY_PASS_SHA256 = "3153d72000fb7ea87f55adc3eed63af5fdb0901a48ded6ae92a616924088c720"
AUTHORIZATION_SHA256 = "f696e76a1fedba8335af62e8914b12bb9385606525cf8170d0b11ffdb3900e52"
SEMANTIC_HASHES = {
    SEMANTIC_CONFIG: "cb0209a9a53962be8ebb6ee185d3bfbf3d004d7cd761e164b286a58e0c7887b0",
    SEMANTIC_MANIFEST: "c0b1a6a3074343ab5f281b268cd40898630ad1e2234830a4536189687832f471",
    SEMANTIC_VALIDATOR: "01b7f60a620c81a7a656ba6576c3b85af9e371b30d42dd5959f430ee220c80dd",
}
REGISTERED_RAW_STATUS = {
    "highs": {
        "optimal": {"ok"},
        "infeasible": {"error"},
        "not_applicable_no_active_outage": {"not_applicable"},
    },
    "gurobi": {
        "optimal": {"ok"},
        "infeasible": {"warning"},
        "not_applicable_no_active_outage": {"not_applicable"},
    },
}
V3_BUNDLE_INVENTORY = {
    "configs/rq2_public_grid_two_block_pilot_user_authorization_v3.yaml",
    "configs/rq2_public_grid_two_block_pilot_candidate_v3.yaml",
    "experiments/run_rq2_public_grid_two_block_pilot_candidate_v3.py",
    "experiments/validate_rq2_public_grid_two_block_pilot_candidate_v3.py",
    "tests/test_rq2_public_grid_two_block_pilot_candidate_v3.py",
}
_CONSUMED_ENVELOPES: set[str] = set()


def _load_yaml(path: Path, label: str) -> dict[str, Any]:
    return recovery._load_yaml_mapping(path, label)


def _load_json(path: Path, label: str) -> Any:
    return recovery._load_json_strict(path, label)


def _is_link_or_reparse(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return False
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse_flag)


def _resolve_after_alias_check(path: Path, *, must_exist: bool) -> Path:
    return path.resolve(strict=must_exist)


def _strict_path(path: Path, *, must_exist: bool, label: str) -> Path:
    """Reject aliases one lexical segment at a time before any resolve call."""

    candidate = Path(path)
    if not candidate.is_absolute():
        raise ValueError(f"{label} must be absolute")
    if any(part in {".", ".."} for part in candidate.parts):
        raise ValueError(f"{label} contains traversal")
    current = Path(candidate.anchor)
    for part in candidate.parts[1:]:
        current = current / part
        if os.path.lexists(current) and _is_link_or_reparse(current):
            raise ValueError(f"{label} contains symlink, junction, or reparse alias")
    if must_exist and not os.path.lexists(candidate):
        raise FileNotFoundError(f"{label} does not exist")
    return _resolve_after_alias_check(candidate, must_exist=must_exist)


def _ordinary_file(path: Path, label: str, expected_hash: str) -> None:
    canonical = _strict_path(path, must_exist=True, label=label)
    if not canonical.is_file() or recovery._sha256(canonical) != expected_hash:
        raise ValueError(f"{label} live authority drifted")


def _verify_bundle_pair(
    *,
    version: int,
    inner: Path,
    inner_sha256: str,
    outer: Path,
    outer_sha256: str,
    expected_count: int,
) -> dict[str, str]:
    _ordinary_file(inner, f"v{version} inner", inner_sha256)
    _ordinary_file(outer, f"v{version} outer", outer_sha256)
    outer_payload = recovery._mapping(_load_json(outer, f"v{version} outer"), "outer")
    if outer_payload != {
        "schema": f"rq2_public_grid_two_block_pilot_candidate_outer_v{version}",
        "files": {inner.relative_to(ROOT).as_posix(): inner_sha256},
    }:
        raise ValueError(f"v{version} outer exact binding drifted")
    inner_payload = recovery._mapping(_load_json(inner, f"v{version} inner"), "inner")
    if inner_payload.get("schema") != (
        f"rq2_public_grid_two_block_pilot_candidate_bundle_v{version}"
    ):
        raise ValueError(f"v{version} inner schema drifted")
    files = recovery._mapping(inner_payload.get("files"), f"v{version} files")
    if len(files) != expected_count:
        raise ValueError(f"v{version} member count drifted")
    for relative, expected in files.items():
        if not recovery._is_sha256(expected):
            raise ValueError(f"v{version} member hash malformed")
        _ordinary_file(ROOT / str(relative), f"v{version} member {relative}", str(expected))
    return {str(key): str(value) for key, value in files.items()}


def _verify_predecessor_authority() -> dict[str, object]:
    v1_files = _verify_bundle_pair(
        version=1,
        inner=ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v1.SHA256SUMS.json",
        inner_sha256=V1_INNER_SHA256,
        outer=ROOT
        / "configs/rq2_public_grid_two_block_pilot_candidate_v1.OUTER.SHA256SUMS.json",
        outer_sha256=V1_OUTER_SHA256,
        expected_count=6,
    )
    v2_files = _verify_bundle_pair(
        version=2,
        inner=ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v2.SHA256SUMS.json",
        inner_sha256=V2_INNER_SHA256,
        outer=ROOT
        / "configs/rq2_public_grid_two_block_pilot_candidate_v2.OUTER.SHA256SUMS.json",
        outer_sha256=V2_OUTER_SHA256,
        expected_count=6,
    )
    _ordinary_file(ESCALATION, "v2 ESCALATE receipt", ESCALATION_SHA256)
    escalation = _load_yaml(ESCALATION, "v2 ESCALATE receipt")
    if (
        escalation.get("verdict") != "ESCALATE"
        or escalation.get("review_status", {}).get("unresolved_finding_count") != 5
        or escalation.get("effect", {}).get("no_execution_authority") is not True
    ):
        raise ValueError("v2 ESCALATE semantics drifted")
    return {"v1_members": v1_files, "v2_members": v2_files}


def _verify_recovery_and_semantic_authority() -> None:
    _ordinary_file(RECOVERY_MANIFEST, "recovery manifest", RECOVERY_MANIFEST_SHA256)
    manifest = recovery._mapping(
        _load_json(RECOVERY_MANIFEST, "recovery manifest"), "recovery manifest"
    )
    if len(manifest) != 7:
        raise ValueError("recovery member count drifted")
    for relative, expected in manifest.items():
        _ordinary_file(ROOT / str(relative), f"recovery member {relative}", str(expected))
    _ordinary_file(RECOVERY_PASS, "recovery PASS", RECOVERY_PASS_SHA256)
    for path, expected in SEMANTIC_HASHES.items():
        _ordinary_file(path, f"semantic authority {path.name}", expected)
    semantic = recovery._mapping(
        _load_json(SEMANTIC_MANIFEST, "semantic manifest"), "semantic manifest"
    )
    files = recovery._mapping(semantic.get("files"), "semantic files")
    for path, expected in (
        (SEMANTIC_CONFIG, SEMANTIC_HASHES[SEMANTIC_CONFIG]),
        (SEMANTIC_VALIDATOR, SEMANTIC_HASHES[SEMANTIC_VALIDATOR]),
    ):
        if files.get(path.relative_to(ROOT).as_posix()) != expected:
            raise ValueError("semantic manifest live member binding drifted")


def _verify_v3_chain() -> dict[str, str]:
    bundle = recovery._mapping(_load_json(BUNDLE, "v3 bundle"), "v3 bundle")
    if bundle.get("schema") != "rq2_public_grid_two_block_pilot_candidate_bundle_v3":
        raise ValueError("v3 bundle schema drifted")
    files = recovery._mapping(bundle.get("files"), "v3 bundle files")
    if set(files) != V3_BUNDLE_INVENTORY:
        raise ValueError("v3 bundle exact inventory drifted")
    for relative, expected in files.items():
        if not recovery._is_sha256(expected):
            raise ValueError(f"v3 member hash malformed: {relative}")
        _ordinary_file(ROOT / str(relative), f"v3 member {relative}", str(expected))
    outer = recovery._mapping(_load_json(OUTER, "v3 outer"), "v3 outer")
    if outer != {
        "schema": "rq2_public_grid_two_block_pilot_candidate_outer_v3",
        "files": {BUNDLE.relative_to(ROOT).as_posix(): recovery._sha256(BUNDLE)},
    }:
        raise ValueError("v3 outer exact binding drifted")
    return {str(key): str(value) for key, value in files.items()}


def _authority_bindings() -> dict[str, object]:
    _verify_predecessor_authority()
    _verify_recovery_and_semantic_authority()
    files = _verify_v3_chain()
    return {
        "candidate_v1_inner_sha256": V1_INNER_SHA256,
        "candidate_v1_outer_sha256": V1_OUTER_SHA256,
        "candidate_v2_inner_sha256": V2_INNER_SHA256,
        "candidate_v2_outer_sha256": V2_OUTER_SHA256,
        "candidate_v2_escalation_sha256": ESCALATION_SHA256,
        "recovery_manifest_sha256": RECOVERY_MANIFEST_SHA256,
        "semantic_config_sha256": SEMANTIC_HASHES[SEMANTIC_CONFIG],
        "semantic_manifest_sha256": SEMANTIC_HASHES[SEMANTIC_MANIFEST],
        "semantic_validator_sha256": SEMANTIC_HASHES[SEMANTIC_VALIDATOR],
        "candidate_v3_config_sha256": files[CONFIG.relative_to(ROOT).as_posix()],
        "candidate_v3_authorization_sha256": files[
            AUTHORIZATION.relative_to(ROOT).as_posix()
        ],
        "candidate_v3_runner_sha256": files[Path(__file__).relative_to(ROOT).as_posix()],
        "candidate_v3_bundle_sha256": recovery._sha256(BUNDLE),
        "candidate_v3_outer_sha256": recovery._sha256(OUTER),
    }


def _load_authority() -> tuple[dict[str, Any], dict[str, Any]]:
    authority = _authority_bindings()
    config = _load_yaml(CONFIG, "candidate v3")
    authorization = _load_yaml(AUTHORIZATION, "user authorization v3")
    if config.get("schema") != CONFIG_SCHEMA or config.get("version") != 3:
        raise ValueError("candidate v3 identity drifted")
    if (
        config.get("user_authorization", {}).get("sha256") != AUTHORIZATION_SHA256
        or authority["candidate_v3_authorization_sha256"] != AUTHORIZATION_SHA256
        or authorization.get("status")
        != "remediation_authorized_future_execution_conditioned"
    ):
        raise ValueError("candidate v3 authorization binding drifted")
    return config, authorization


def _execution_authority_status(
    config: Mapping[str, Any], authorization: Mapping[str, Any]
) -> dict[str, bool]:
    gates = recovery._mapping(config.get("gates"), "candidate v3 gates")
    conditions = recovery._mapping(
        authorization.get("conditions_precedent"), "authorization conditions"
    )
    effect = recovery._mapping(authorization.get("effect"), "authorization effect")
    return {
        "independent_pre_run_review_passed": (
            gates.get("independent_pre_run_review_passed") is True
        ),
        "execution_successor_present": gates.get("execution_successor_present") is True,
        "pilot_ready": gates.get("two_block_pilot_execution_ready") is True,
        "conditional_user_authority_effective": (
            effect.get("conditional_authorization_effective") is True
            and all(value is True for value in conditions.values())
        ),
        "current_candidate_not_closed": effect.get("current_candidate_execution_authorized")
        is True,
    }


def _require_execution_authority() -> dict[str, Any]:
    config, authorization = _load_authority()
    failed = [
        key
        for key, value in _execution_authority_status(config, authorization).items()
        if not value
    ]
    if failed:
        raise RuntimeError("candidate v3 execution authority is closed: " + ", ".join(failed))
    require_execution_host(_load_yaml(BASE_CONFIG, "base config")["execution"])
    return config


def _stage_context() -> dict[str, Any]:
    context = recovery._stage_context(BASE_CONFIG)
    for block_id in BLOCKS:
        rows = context["blocks"].get(block_id)
        if (
            not isinstance(rows, list)
            or len(rows) != 24
            or [row["block_id"] for row in rows] != [block_id] * 24
            or [row["hour_offset"] for row in rows] != [str(i) for i in range(24)]
        ):
            raise ValueError(f"pilot 24-hour block inventory drifted: {block_id}")
    return context


def _pilot_roots(config: Mapping[str, Any]) -> dict[str, Path]:
    paths = recovery._mapping(config.get("paths"), "pilot v3 paths")
    roots = {
        name: _strict_path(ROOT / str(paths[key]), must_exist=False, label=f"pilot {name}")
        for name, key in (
            ("result", "result_directory"),
            ("worker", "worker_staging_directory"),
            ("log", "attempt_log_directory"),
        )
    }
    formal = recovery._mapping(config.get("immutable_formal_authority"), "formal authority")
    protected = [
        _strict_path(ROOT / str(formal[key]), must_exist=False, label=key)
        for key in (
            "gurobi_checkpoint_directory",
            "gurobi_output_directory",
            "recovery_checkpoint_directory",
            "recovery_output_directory",
        )
    ]
    for name, left in roots.items():
        for other_name, right in roots.items():
            if name != other_name and (
                recovery._same_or_descendant(left, right)
                or recovery._same_or_descendant(right, left)
            ):
                raise ValueError("pilot v3 roots overlap")
        for right in protected:
            if recovery._same_or_descendant(left, right) or recovery._same_or_descendant(
                right, left
            ):
                raise ValueError("pilot v3 root overlaps formal authority")
    return roots


def _formal_snapshot(config: Mapping[str, Any]) -> dict[str, object]:
    formal = recovery._mapping(config.get("immutable_formal_authority"), "formal authority")
    runner_path = _strict_path(
        ROOT / str(formal["formal_runner_path"]), must_exist=True, label="formal runner"
    )
    gurobi_config = _strict_path(
        ROOT / str(formal["activated_gurobi_config_path"]),
        must_exist=True,
        label="activated Gurobi config",
    )
    if (
        recovery._sha256(runner_path) != formal["formal_runner_sha256"]
        or recovery._sha256(gurobi_config) != formal["activated_gurobi_config_sha256"]
    ):
        raise ValueError("formal runner/config bytes drifted")
    checkpoint_root = _strict_path(
        ROOT / str(formal["gurobi_checkpoint_directory"]),
        must_exist=True,
        label="formal checkpoint root",
    )
    checkpoints = recovery._mapping(formal.get("checkpoint_sha256"), "formal checkpoints")
    if {path.name for path in checkpoint_root.glob("*.json")} != set(checkpoints):
        raise ValueError("formal checkpoint exact inventory drifted")
    for name, expected in checkpoints.items():
        _ordinary_file(checkpoint_root / str(name), f"formal checkpoint {name}", str(expected))
    protected: dict[str, object] = {}
    for key in (
        "gurobi_output_directory",
        "recovery_checkpoint_directory",
        "recovery_output_directory",
    ):
        path = _strict_path(ROOT / str(formal[key]), must_exist=False, label=key)
        protected[key] = {
            "exists": path.exists(),
            "tree": _typed_tree(path) if path.is_dir() else None,
        }
    return {
        "formal_runner_sha256": recovery._sha256(runner_path),
        "activated_gurobi_config_sha256": recovery._sha256(gurobi_config),
        "checkpoint_sha256": dict(checkpoints),
        "protected_roots": protected,
    }


def _process_creation_time_windows(handle: int) -> int:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    creation = wintypes.FILETIME()
    exit_time = wintypes.FILETIME()
    kernel = wintypes.FILETIME()
    user = wintypes.FILETIME()
    if not kernel32.GetProcessTimes(
        handle,
        ctypes.byref(creation),
        ctypes.byref(exit_time),
        ctypes.byref(kernel),
        ctypes.byref(user),
    ):
        raise OSError(ctypes.get_last_error(), "GetProcessTimes failed")
    return (int(creation.dwHighDateTime) << 32) | int(creation.dwLowDateTime)


def _windows_command_line(handle: int) -> list[str]:
    ntdll = ctypes.WinDLL("ntdll", use_last_error=True)
    ntdll.NtQueryInformationProcess.argtypes = [
        wintypes.HANDLE,
        wintypes.ULONG,
        wintypes.LPVOID,
        wintypes.ULONG,
        ctypes.POINTER(wintypes.ULONG),
    ]
    ntdll.NtQueryInformationProcess.restype = wintypes.LONG
    needed = wintypes.ULONG()
    status = ntdll.NtQueryInformationProcess(handle, 60, None, 0, ctypes.byref(needed))
    if status not in {0xC0000004, -1073741820} or needed.value <= 0:
        raise OSError(f"NtQueryInformationProcess size failed: {status}")
    buffer = ctypes.create_string_buffer(needed.value)
    status = ntdll.NtQueryInformationProcess(
        handle, 60, buffer, needed.value, ctypes.byref(needed)
    )
    if status != 0:
        raise OSError(f"NtQueryInformationProcess command failed: {status}")

    class UnicodeString(ctypes.Structure):
        _fields_ = [
            ("length", wintypes.USHORT),
            ("maximum_length", wintypes.USHORT),
            ("buffer", wintypes.LPWSTR),
        ]

    command = UnicodeString.from_buffer(buffer)
    raw = ctypes.wstring_at(command.buffer, command.length // 2)
    argc = ctypes.c_int()
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    shell32.CommandLineToArgvW.argtypes = [
        wintypes.LPCWSTR,
        ctypes.POINTER(ctypes.c_int),
    ]
    shell32.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
    argv = shell32.CommandLineToArgvW(raw, ctypes.byref(argc))
    if not argv:
        raise OSError(ctypes.get_last_error(), "CommandLineToArgvW failed")
    try:
        return [argv[index] for index in range(argc.value)]
    finally:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
        kernel32.LocalFree.restype = wintypes.HLOCAL
        kernel32.LocalFree(ctypes.cast(argv, wintypes.HLOCAL))


def _query_process_identity(pid: int) -> dict[str, object]:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise ValueError("process PID must be a positive integer")
    if os.name == "nt":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        access = 0x1000 | 0x0010
        handle = kernel32.OpenProcess(access, False, pid)
        if not handle:
            raise OSError(ctypes.get_last_error(), "OpenProcess failed")
        try:
            capacity = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(capacity.value)
            if not kernel32.QueryFullProcessImageNameW(
                handle, 0, buffer, ctypes.byref(capacity)
            ):
                raise OSError(ctypes.get_last_error(), "QueryFullProcessImageNameW failed")
            executable = _strict_path(
                Path(buffer.value), must_exist=True, label="process executable"
            )
            return {
                "pid": pid,
                "creation_time": _process_creation_time_windows(handle),
                "executable_path": str(executable),
                "executable_sha256": recovery._sha256(executable),
                "command": _windows_command_line(handle),
            }
        finally:
            kernel32.CloseHandle(handle)
    proc = Path("/proc") / str(pid)
    proc_executable = proc / "exe"
    executable_target = Path(os.readlink(proc_executable))
    if not executable_target.is_absolute():
        executable_target = proc / executable_target
    executable = _strict_path(
        executable_target, must_exist=True, label="process executable target"
    )
    command = (proc / "cmdline").read_bytes().rstrip(b"\0").split(b"\0")
    stat_fields = (proc / "stat").read_text(encoding="utf-8").split()
    return {
        "pid": pid,
        "creation_time": int(stat_fields[21]),
        "executable_path": str(executable),
        "executable_sha256": recovery._sha256(executable),
        "command": [item.decode(errors="strict") for item in command],
    }


def _expected_controller_command(python: Path) -> list[str]:
    return [str(python.resolve()), "-B", "-m", MODULE]


def _expected_worker_command(
    python: Path, *, read_handle: int, ack_handle: int
) -> list[str]:
    return [
        str(python.resolve()),
        "-B",
        "-m",
        MODULE,
        "--internal-worker",
        "--read-handle",
        str(read_handle),
        "--ack-handle",
        str(ack_handle),
    ]


def _sanitized_environment(
    source: Mapping[str, str] | None = None,
) -> dict[str, str]:
    environment = os.environ if source is None else source
    if "PYTHONPATH" in environment or "PYTHONHOME" in environment:
        raise ValueError("PYTHONPATH/PYTHONHOME are forbidden for the pilot worker")
    allowed = {
        "COMSPEC",
        "EXECUTION_MACHINE_CONFIRMED",
        "LANG",
        "LC_ALL",
        "PATH",
        "PATHEXT",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "WINDIR",
    }
    return {key: str(environment[key]) for key in sorted(allowed & set(environment))}


def _canonical_hash(payload: object) -> str:
    return recovery._canonical_sha256(payload)


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise OSError("anonymous pipe write ended early")
        offset += written


def _write_frame(descriptor: int, payload: Mapping[str, Any]) -> None:
    body = recovery._canonical_bytes(dict(payload))
    if len(body) > MAX_FRAME_BYTES:
        raise ValueError("capability frame exceeds frozen limit")
    _write_all(descriptor, len(body).to_bytes(8, "big") + body)


def _read_exact(descriptor: int, length: int) -> bytes:
    chunks: list[bytes] = []
    remaining = length
    while remaining:
        chunk = os.read(descriptor, remaining)
        if not chunk:
            raise EOFError("anonymous pipe frame ended early")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_frame(descriptor: int, label: str) -> dict[str, Any]:
    length = int.from_bytes(_read_exact(descriptor, 8), "big")
    if length <= 0 or length > MAX_FRAME_BYTES:
        raise ValueError(f"{label} frame length invalid")
    raw = _read_exact(descriptor, length)
    payload = json.loads(raw.decode("utf-8"))
    return recovery._mapping(payload, label)


def _require_anonymous_pipe(descriptor: int, label: str) -> None:
    if isinstance(descriptor, bool) or not isinstance(descriptor, int) or descriptor < 0:
        raise ValueError(f"{label} descriptor is invalid")
    if os.name == "nt":
        import msvcrt

        handle = msvcrt.get_osfhandle(descriptor)
        if ctypes.windll.kernel32.GetFileType(handle) != 3:  # type: ignore[attr-defined]
            raise ValueError(f"{label} is not an anonymous pipe")
    elif not stat.S_ISFIFO(os.fstat(descriptor).st_mode):
        raise ValueError(f"{label} is not an anonymous pipe")


_SYNTHETIC_PROBE_CODE = r"""
import hashlib,json,os,stat,sys
def exact(fd,n):
    out=b''
    while len(out)<n:
        chunk=os.read(fd,n-len(out))
        if not chunk: raise EOFError('short frame')
        out+=chunk
    return out
def read_frame(fd):
    n=int.from_bytes(exact(fd,8),'big')
    return json.loads(exact(fd,n).decode('utf-8'))
def write_frame(fd,payload):
    body=json.dumps(payload,sort_keys=True,separators=(',',':')).encode('utf-8')
    os.write(fd,len(body).to_bytes(8,'big')+body)
read_handle=int(sys.argv[1]); ack_handle=int(sys.argv[2])
if os.name=='nt':
    import msvcrt
    read_fd=msvcrt.open_osfhandle(read_handle,os.O_RDONLY)
    ack_fd=msvcrt.open_osfhandle(ack_handle,os.O_WRONLY)
    if __import__('ctypes').windll.kernel32.GetFileType(read_handle)!=3: sys.exit(21)
    if __import__('ctypes').windll.kernel32.GetFileType(ack_handle)!=3: sys.exit(21)
else:
    read_fd=read_handle; ack_fd=ack_handle
    if not stat.S_ISFIFO(os.fstat(read_fd).st_mode): sys.exit(21)
    if not stat.S_ISFIFO(os.fstat(ack_fd).st_mode): sys.exit(21)
write_frame(ack_fd,{'schema':'synthetic_capability_hello_v1','pid':os.getpid(),'ppid':os.getppid()})
envelope=read_frame(read_fd)
canonical=json.dumps(envelope,sort_keys=True,separators=(',',':')).encode('utf-8')
accepted=(envelope.get('schema')=='synthetic_capability_envelope_v1'
          and envelope.get('direction')=='controller_to_worker'
          and envelope.get('single_use') is True
          and envelope.get('worker_pid')==os.getpid()
          and envelope.get('parent_pid')==os.getppid())
extra=os.read(read_fd,1)
if extra: accepted=False
write_frame(ack_fd,{'schema':'synthetic_capability_ack_v1','accepted':accepted,
                    'envelope_sha256':hashlib.sha256(canonical).hexdigest(),
                    'replay_bytes_observed':len(extra)})
sys.exit(0 if accepted else 22)
"""


def _synthetic_capability_probe(
    *, mode: str = "valid"
) -> dict[str, object]:
    """Exercise only OS pipe inheritance and post-Popen identity binding."""

    if mode not in {"valid", "ordinary_file", "wrong_direction", "replay"}:
        raise ValueError("unregistered synthetic capability probe mode")
    request_read, request_write = os.pipe()
    ordinary_descriptor: int | None = None
    if mode == "ordinary_file":
        os.close(request_read)
        ordinary_descriptor = os.open(__file__, os.O_RDONLY)
        request_read = ordinary_descriptor
    ack_read, ack_write = os.pipe()
    os.set_inheritable(request_read, True)
    os.set_inheritable(ack_write, True)
    child_read = request_read
    child_ack = ack_write
    if os.name == "nt":
        import msvcrt

        child_read = msvcrt.get_osfhandle(request_read)
        child_ack = msvcrt.get_osfhandle(ack_write)
    command = [
        str(Path(sys.executable).resolve()),
        "-B",
        "-c",
        _SYNTHETIC_PROBE_CODE,
        str(child_read),
        str(child_ack),
    ]
    kwargs: dict[str, object] = {
        "cwd": ROOT,
        "env": _sanitized_environment(),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "text": False,
    }
    if os.name == "nt":
        kwargs.update(_windows_popen_kwargs(child_read, child_ack))
    else:
        kwargs.update({"pass_fds": (request_read, ack_write), "close_fds": True})
    process = subprocess.Popen(command, **kwargs)
    os.close(request_read)
    os.close(ack_write)
    writer: threading.Thread | None = None
    try:
        hello = _read_frame(ack_read, "synthetic capability hello")
        observed = _query_process_identity(process.pid)
        if hello != {
            "schema": "synthetic_capability_hello_v1",
            "pid": process.pid,
            "ppid": os.getpid(),
        }:
            raise ValueError("synthetic child hello identity drifted")
        envelope = {
            "schema": "synthetic_capability_envelope_v1",
            "direction": (
                "worker_to_controller" if mode == "wrong_direction" else "controller_to_worker"
            ),
            "single_use": True,
            "nonce": secrets.token_hex(32),
            "parent_pid": os.getpid(),
            "worker_pid": process.pid,
            "worker_creation_time": observed["creation_time"],
            "worker_executable_sha256": observed["executable_sha256"],
        }

        def write_once_or_replay() -> None:
            try:
                _write_frame(request_write, envelope)
                if mode == "replay":
                    _write_frame(request_write, envelope)
            finally:
                os.close(request_write)

        writer = threading.Thread(target=write_once_or_replay, daemon=False)
        writer.start()
        ack = _read_frame(ack_read, "synthetic capability ack")
        writer.join(timeout=10)
        if writer.is_alive():
            raise TimeoutError("synthetic capability writer did not close")
        exit_code = process.wait(timeout=10)
        if mode != "valid":
            raise ValueError(
                f"synthetic capability correctly rejected {mode}: exit={exit_code}, ack={ack}"
            )
        if (
            exit_code != 0
            or ack.get("accepted") is not True
            or ack.get("envelope_sha256") != _canonical_hash(envelope)
            or ack.get("replay_bytes_observed") != 0
        ):
            raise ValueError("synthetic capability valid probe failed")
        return {
            "probe_passed": True,
            "child_pid": process.pid,
            "child_creation_time": observed["creation_time"],
            "anonymous_pipe_transport": True,
            "post_popen_identity_bound": True,
            "single_use_acknowledged": True,
            "scientific_loader_calls": 0,
            "solver_calls": 0,
            "result_writes": 0,
            "formal_writes": 0,
        }
    finally:
        if writer is None:
            try:
                os.close(request_write)
            except OSError:
                pass
        try:
            os.close(ack_read)
        except OSError:
            pass
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)


def _block_input_sha256(context: Mapping[str, Any], block_id: str) -> str:
    return recovery._block_input_sha256(context["blocks"][block_id])


def _build_capability_envelope(
    config: Mapping[str, Any],
    *,
    block_id: str,
    parent_identity: Mapping[str, Any],
    worker_identity: Mapping[str, Any],
    result_path: Path,
    read_handle: int,
    ack_handle: int,
    environment: Mapping[str, str],
    nonce: str | None = None,
) -> dict[str, object]:
    context = _stage_context()
    python = Path(str(worker_identity["executable_path"]))
    return {
        "schema": ENVELOPE_SCHEMA,
        "nonce": nonce or secrets.token_hex(32),
        "issued_ns": time.time_ns(),
        "authority": _authority_bindings(),
        "parent_process_identity": dict(parent_identity),
        "worker_process_identity": dict(worker_identity),
        "parent_command": _expected_controller_command(python),
        "worker_command": _expected_worker_command(
            python, read_handle=read_handle, ack_handle=ack_handle
        ),
        "working_directory": str(ROOT),
        "sanitized_environment": dict(environment),
        "sanitized_environment_sha256": _canonical_hash(dict(environment)),
        "block_id": block_id,
        "block_input_sha256": _block_input_sha256(context, block_id),
        "stage": recovery.STAGE,
        "stage_base_provenance_sha256": context["stage_base_sha256"],
        "scientific_config_path": str(BASE_CONFIG),
        "scientific_config_sha256": recovery._sha256(BASE_CONFIG),
        "solver": recovery._solver_binding(context["config"]),
        "execution_host": execution_host_status(context["config"]["execution"]),
        "worker_result_path": str(result_path),
        "read_handle": read_handle,
        "ack_handle": ack_handle,
    }


def _validate_capability_envelope(
    envelope: Mapping[str, Any],
    *,
    config: Mapping[str, Any],
    read_handle: int,
    ack_handle: int,
) -> dict[str, Any]:
    expected_keys = {
        "schema",
        "nonce",
        "issued_ns",
        "authority",
        "parent_process_identity",
        "worker_process_identity",
        "parent_command",
        "worker_command",
        "working_directory",
        "sanitized_environment",
        "sanitized_environment_sha256",
        "block_id",
        "block_input_sha256",
        "stage",
        "stage_base_provenance_sha256",
        "scientific_config_path",
        "scientific_config_sha256",
        "solver",
        "execution_host",
        "worker_result_path",
        "read_handle",
        "ack_handle",
    }
    if set(envelope) != expected_keys or envelope.get("schema") != ENVELOPE_SCHEMA:
        raise ValueError("capability envelope schema drifted")
    nonce = envelope.get("nonce")
    if (
        not isinstance(nonce, str)
        or len(nonce) != 64
        or any(character not in "0123456789abcdef" for character in nonce)
    ):
        raise ValueError("capability nonce malformed")
    if isinstance(envelope.get("issued_ns"), bool) or not isinstance(
        envelope.get("issued_ns"), int
    ):
        raise TypeError("capability issued_ns must be an integer")
    envelope_hash = _canonical_hash(dict(envelope))
    if envelope_hash in _CONSUMED_ENVELOPES:
        raise ValueError("capability envelope was already consumed")
    authority = _authority_bindings()
    if envelope.get("authority") != authority:
        raise ValueError("capability sealed successor authority drifted")
    parent = recovery._mapping(envelope.get("parent_process_identity"), "parent identity")
    worker = recovery._mapping(envelope.get("worker_process_identity"), "worker identity")
    if parent != _query_process_identity(os.getppid()):
        raise ValueError("capability parent PID/create-time/executable/command drifted")
    if worker != _query_process_identity(os.getpid()):
        raise ValueError("capability worker PID/create-time/executable/command drifted")
    python = Path(str(worker["executable_path"]))
    if (
        envelope.get("parent_command") != _expected_controller_command(python)
        or envelope.get("worker_command")
        != _expected_worker_command(python, read_handle=read_handle, ack_handle=ack_handle)
        or parent.get("command") != envelope.get("parent_command")
        or worker.get("command") != envelope.get("worker_command")
        or envelope.get("read_handle") != read_handle
        or envelope.get("ack_handle") != ack_handle
    ):
        raise ValueError("capability exact command or handle binding drifted")
    environment = _sanitized_environment()
    if (
        envelope.get("sanitized_environment") != environment
        or envelope.get("sanitized_environment_sha256") != _canonical_hash(environment)
        or envelope.get("working_directory") != str(ROOT)
        or Path.cwd().resolve() != ROOT
    ):
        raise ValueError("capability cwd or sanitized environment drifted")
    context = _stage_context()
    block_id = envelope.get("block_id")
    if block_id not in BLOCKS:
        raise ValueError("capability block is not frozen")
    if (
        envelope.get("block_input_sha256") != _block_input_sha256(context, str(block_id))
        or envelope.get("stage") != recovery.STAGE
        or envelope.get("stage_base_provenance_sha256") != context["stage_base_sha256"]
        or envelope.get("scientific_config_sha256") != recovery._sha256(BASE_CONFIG)
        or envelope.get("solver") != recovery._solver_binding(context["config"])
        or envelope.get("execution_host")
        != execution_host_status(context["config"]["execution"])
    ):
        raise ValueError("capability scientific/stage/host binding drifted")
    scientific_path = _strict_path(
        Path(str(envelope.get("scientific_config_path"))),
        must_exist=True,
        label="capability scientific config",
    )
    result_path = _strict_path(
        Path(str(envelope.get("worker_result_path"))),
        must_exist=False,
        label="capability worker result",
    )
    worker_root = _pilot_roots(config)["worker"]
    if scientific_path != BASE_CONFIG or not recovery._same_or_descendant(
        result_path, worker_root
    ):
        raise ValueError("capability canonical path binding drifted")
    if result_path.exists():
        raise FileExistsError("capability result path preexists")
    _CONSUMED_ENVELOPES.add(envelope_hash)
    return context


def _load_worker_data(context: Mapping[str, Any]) -> Any:
    return load_rts_gmlc_chronological_data(
        context["grid_root"],
        base_mva=float(context["config"]["grid_source"]["base_mva"]),
    )


def _build_worker_result(
    envelope: Mapping[str, Any], payload: Mapping[str, Any]
) -> dict[str, object]:
    return {
        "schema": RESULT_SCHEMA,
        "status": "complete" if payload.get("all_hours_resolved") is True else "unresolved",
        "authority": envelope["authority"],
        "capability_envelope_sha256": _canonical_hash(dict(envelope)),
        "block_id": envelope["block_id"],
        "block_input_sha256": envelope["block_input_sha256"],
        "parent_process_identity": envelope["parent_process_identity"],
        "worker_process_identity": envelope["worker_process_identity"],
        "scientific_config_path": envelope["scientific_config_path"],
        "scientific_config_sha256": envelope["scientific_config_sha256"],
        "solver": envelope["solver"],
        "scientific_payload": dict(payload),
        "scientific_payload_sha256": _canonical_hash(dict(payload)),
        "all_hours_resolved": payload.get("all_hours_resolved") is True,
        "mathematical_infeasibility_inferred_from_failure": False,
    }


def _build_worker_receipt(
    envelope: Mapping[str, Any], payload_path: Path
) -> dict[str, object]:
    result = recovery._mapping(_load_json(payload_path, "worker payload"), "worker payload")
    return {
        "schema": RECEIPT_SCHEMA,
        "authority": envelope["authority"],
        "capability_envelope_sha256": _canonical_hash(dict(envelope)),
        "worker_payload_sha256": recovery._sha256(payload_path),
        "block_id": envelope["block_id"],
        "parent_process_identity": envelope["parent_process_identity"],
        "worker_process_identity": envelope["worker_process_identity"],
        "all_hours_resolved": result.get("all_hours_resolved") is True,
        "controller_validation_passed": True,
        "published_by_controller": True,
        "mathematical_infeasibility_inferred_from_failure": False,
    }


def _worker_from_capability(
    read_descriptor: int,
    ack_descriptor: int,
    *,
    read_handle: int | None = None,
    ack_handle: int | None = None,
) -> int:
    config = _require_execution_authority()
    _require_anonymous_pipe(read_descriptor, "controller-to-worker capability")
    _require_anonymous_pipe(ack_descriptor, "worker-to-controller acknowledgement")
    capability_read_handle = read_descriptor if read_handle is None else read_handle
    capability_ack_handle = ack_descriptor if ack_handle is None else ack_handle
    worker_identity = _query_process_identity(os.getpid())
    _write_frame(
        ack_descriptor,
        {
            "schema": HELLO_SCHEMA,
            "worker_process_identity": worker_identity,
            "candidate_v3_outer_sha256": recovery._sha256(OUTER),
        },
    )
    envelope = _read_frame(read_descriptor, "capability envelope")
    context = _validate_capability_envelope(
        envelope,
        config=config,
        read_handle=capability_read_handle,
        ack_handle=capability_ack_handle,
    )
    envelope_sha = _canonical_hash(envelope)
    _write_frame(
        ack_descriptor,
        {
            "schema": ACK_SCHEMA,
            "capability_envelope_sha256": envelope_sha,
            "worker_process_identity": worker_identity,
            "accepted_once": True,
        },
    )
    block_id = str(envelope["block_id"])
    data = _load_worker_data(context)
    payload = recovery.v4._process_block(
        data,
        context["blocks"][block_id],
        dc_bus=int(context["config"]["model"]["dc_bus"]),
        dc_demand_mw=float(context["config"]["model"]["dc_reference_demand_mw"]),
        solver=context["config"]["solver"],
    )
    result = _build_worker_result(envelope, payload)
    result_path = _strict_path(
        Path(str(envelope["worker_result_path"])),
        must_exist=False,
        label="worker result",
    )
    result_path.parent.mkdir(parents=True, exist_ok=False)
    recovery._atomic_json(result_path, result)
    return 0 if result["all_hours_resolved"] is True else 3


def _registered_raw_semantic(solver: str, termination: object, status: object) -> str:
    if not isinstance(termination, str) or not isinstance(status, str):
        raise TypeError("unregistered raw termination/status pair")
    if status not in REGISTERED_RAW_STATUS.get(solver, {}).get(termination, set()):
        raise ValueError(
            f"unregistered raw termination/status pair: {solver}/{termination}/{status}"
        )
    return termination


def _normalize_payload_raw_evidence(payload: Mapping[str, Any], solver: str) -> None:
    baseline = recovery._mapping(payload.get("baseline_audit"), f"{solver} baseline")
    if (
        _registered_raw_semantic(
            solver, baseline.get("termination_condition"), baseline.get("solver_status")
        )
        != "optimal"
    ):
        raise ValueError(f"{solver} baseline semantic is not optimal")
    outcomes = payload.get("outcomes")
    rows = payload.get("rows")
    if not isinstance(outcomes, list) or not isinstance(rows, list):
        raise TypeError("semantic rows/outcomes must be lists")
    for index, (outcome_raw, row_raw) in enumerate(zip(outcomes, rows, strict=True)):
        outcome = recovery._mapping(outcome_raw, f"{solver} outcome {index}")
        row = recovery._mapping(row_raw, f"{solver} row {index}")
        primary = recovery._mapping(outcome.get("primary"), f"{solver} primary {index}")
        semantic = _registered_raw_semantic(
            solver, primary.get("termination_condition"), primary.get("solver_status")
        )
        expected = (
            "not_applicable_no_active_outage"
            if not row.get("active_event_id")
            else "infeasible"
            if outcome.get("state") == "E0_infeasible_at_zero_dc"
            else "optimal"
        )
        if semantic != expected:
            raise ValueError(f"{solver} primary semantic mismatch at hour {index}")
        zero = outcome.get("zero_dc_confirmation")
        if expected == "infeasible":
            zero_map = recovery._mapping(zero, f"{solver} zero confirmation {index}")
            if (
                _registered_raw_semantic(
                    solver,
                    zero_map.get("termination_condition"),
                    zero_map.get("solver_status"),
                )
                != "infeasible"
            ):
                raise ValueError(f"{solver} zero confirmation mismatch at hour {index}")
        elif zero is not None:
            raise ValueError(f"{solver} unexpected zero confirmation at hour {index}")


def _interval(certificate: Mapping[str, Any], prefix: str) -> tuple[float, float, float]:
    raw = (
        certificate.get("objective_incumbent_mw"),
        certificate.get("lower_bound_mw"),
        certificate.get("upper_bound_mw"),
    )
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        for value in raw
    ):
        raise ValueError(f"{prefix} finite interval is incomplete")
    return tuple(float(value) for value in raw)  # type: ignore[return-value]


def _extract_gurobi_payload() -> dict[str, Any]:
    checkpoint = recovery._mapping(_load_json(GUROBI_0008, "Gurobi 0008"), "checkpoint")
    return {
        key: value
        for key, value in checkpoint.items()
        if key not in {"schema", "stage_base_provenance_sha256"}
    }


def compare_named_outage_0008(
    highs_payload: Mapping[str, Any], gurobi_payload: Mapping[str, Any]
) -> dict[str, object]:
    report: dict[str, object] = {
        "schema": "rq2_public_grid_two_block_pilot_named_outage_comparison_v3",
        "block_id": BLOCKS[0],
        "comparison_passed": False,
        "mathematical_infeasibility_inferred": False,
        "maximum_finite_grid_need_difference_mw": 1.0e-5,
        "maximum_baseline_incumbent_difference_usd": 1.0e-4,
        "raw_status_equality_required": False,
        "reason": None,
    }
    try:
        _verify_recovery_and_semantic_authority()
        context = _stage_context()
        gurobi_config = _load_yaml(GUROBI_CONFIG, "frozen Gurobi config")
        highs = recovery._validate_scientific_payload(
            recovery._mapping(highs_payload, "HiGHS 0008 payload"),
            block_id=BLOCKS[0],
            expected_block=context["blocks"][BLOCKS[0]],
            config=context["config"],
        )
        gurobi = recovery._validate_scientific_payload(
            recovery._mapping(gurobi_payload, "Gurobi 0008 payload"),
            block_id=BLOCKS[0],
            expected_block=context["blocks"][BLOCKS[0]],
            config=gurobi_config,
        )
        _normalize_payload_raw_evidence(highs, "highs")
        _normalize_payload_raw_evidence(gurobi, "gurobi")
        left_base = recovery._mapping(highs["baseline_audit"], "HiGHS baseline")
        right_base = recovery._mapping(gurobi["baseline_audit"], "Gurobi baseline")
        if abs(float(left_base["objective_usd"]) - float(right_base["objective_usd"])) > 1.0e-4:
            raise ValueError("baseline incumbents differ")
        lower = max(float(left_base["lower_bound_usd"]), float(right_base["lower_bound_usd"]))
        upper = min(float(left_base["upper_bound_usd"]), float(right_base["upper_bound_usd"]))
        if lower > upper and not math.isclose(lower, upper, rel_tol=1.0e-12, abs_tol=1.0e-12):
            raise ValueError("baseline certified intervals are disjoint")
        for index, (left_raw, right_raw) in enumerate(
            zip(highs["outcomes"], gurobi["outcomes"], strict=True)
        ):
            left = recovery._mapping(left_raw, "HiGHS outcome")
            right = recovery._mapping(right_raw, "Gurobi outcome")
            left_primary = recovery._mapping(left["primary"], "HiGHS primary")
            right_primary = recovery._mapping(right["primary"], "Gurobi primary")
            for key in ("source_hour", "event_id", "component_type", "component_uid"):
                if left_primary.get(key) != right_primary.get(key):
                    raise ValueError(f"hour {index} outage identity differs")
            if left.get("state") != right.get("state"):
                raise ValueError(f"hour {index} semantic state differs")
            left_cert = recovery._mapping(left["primary_certificate"], "HiGHS certificate")
            right_cert = recovery._mapping(right["primary_certificate"], "Gurobi certificate")
            for key in ("model_variables", "model_constraints"):
                if left_cert.get(key) != right_cert.get(key):
                    raise ValueError(f"hour {index} model scale differs")
            if left.get("state") == "finite_grid_need":
                if abs(float(left_primary["grid_need_mw"]) - float(right_primary["grid_need_mw"])) > 1.0e-5:
                    raise ValueError(f"hour {index} finite grid need differs")
                left_interval = _interval(left_cert, "HiGHS hourly")
                right_interval = _interval(right_cert, "Gurobi hourly")
                lower = max(left_interval[1], right_interval[1])
                upper = min(left_interval[2], right_interval[2])
                if lower > upper and not math.isclose(
                    lower, upper, rel_tol=1.0e-12, abs_tol=1.0e-10
                ):
                    raise ValueError(f"hour {index} certified intervals are disjoint")
            elif (left.get("zero_dc_confirmation") is None) != (
                right.get("zero_dc_confirmation") is None
            ):
                raise ValueError(f"hour {index} E0 zero confirmation differs")
        report["comparison_passed"] = True
    except (KeyError, TypeError, ValueError) as error:
        report["reason"] = str(error)
    return report


def _validate_worker_pair(
    payload_path: Path,
    receipt_path: Path,
    *,
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    payload_path = _strict_path(payload_path, must_exist=True, label="worker payload")
    receipt_path = _strict_path(receipt_path, must_exist=True, label="worker receipt")
    result = recovery._mapping(_load_json(payload_path, "worker payload"), "worker payload")
    receipt = recovery._mapping(_load_json(receipt_path, "worker receipt"), "worker receipt")
    expected_result_keys = {
        "schema",
        "status",
        "authority",
        "capability_envelope_sha256",
        "block_id",
        "block_input_sha256",
        "parent_process_identity",
        "worker_process_identity",
        "scientific_config_path",
        "scientific_config_sha256",
        "solver",
        "scientific_payload",
        "scientific_payload_sha256",
        "all_hours_resolved",
        "mathematical_infeasibility_inferred_from_failure",
    }
    if set(result) != expected_result_keys or result.get("schema") != RESULT_SCHEMA:
        raise ValueError("worker result schema drifted")
    authority = _authority_bindings()
    envelope_sha = _canonical_hash(dict(envelope))
    if (
        result.get("status") != "complete"
        or result.get("authority") != authority
        or result.get("authority") != envelope.get("authority")
        or result.get("capability_envelope_sha256") != envelope_sha
        or result.get("block_id") != envelope.get("block_id")
        or result.get("block_input_sha256") != envelope.get("block_input_sha256")
        or result.get("parent_process_identity") != envelope.get("parent_process_identity")
        or result.get("worker_process_identity") != envelope.get("worker_process_identity")
        or result.get("scientific_config_path") != envelope.get("scientific_config_path")
        or result.get("scientific_config_sha256") != envelope.get("scientific_config_sha256")
        or result.get("solver") != envelope.get("solver")
        or result.get("all_hours_resolved") is not True
        or result.get("mathematical_infeasibility_inferred_from_failure") is not False
    ):
        raise ValueError("worker result/capability/authority binding drifted")
    context = _stage_context()
    block_id = str(envelope["block_id"])
    payload = recovery._validate_scientific_payload(
        recovery._mapping(result.get("scientific_payload"), "scientific payload"),
        block_id=block_id,
        expected_block=context["blocks"][block_id],
        config=context["config"],
    )
    _normalize_payload_raw_evidence(payload, "highs")
    if result.get("scientific_payload_sha256") != _canonical_hash(payload):
        raise ValueError("scientific payload canonical hash drifted")
    expected_receipt = _build_worker_receipt(envelope, payload_path)
    if receipt != expected_receipt or receipt.get("worker_payload_sha256") != recovery._sha256(
        payload_path
    ):
        raise ValueError("worker receipt/payload binding drifted")
    return payload


def _typed_tree(root: Path) -> dict[str, object]:
    if not root.exists():
        raise FileNotFoundError("typed tree root is absent")
    root = _strict_path(root, must_exist=True, label="typed tree root")
    directories: list[str] = []
    files: dict[str, str] = {}

    def visit(directory: Path) -> None:
        with os.scandir(directory) as entries:
            ordered = sorted(entries, key=lambda entry: entry.name)
        for entry in ordered:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            if _is_link_or_reparse(path):
                raise ValueError(f"typed tree contains symlink/junction/reparse: {relative}")
            metadata = entry.stat(follow_symlinks=False)
            if stat.S_ISDIR(metadata.st_mode):
                directories.append(relative)
                visit(path)
            elif stat.S_ISREG(metadata.st_mode):
                if relative == "SHA256SUMS.json":
                    continue
                if path.name == "SHA256SUMS.json":
                    raise ValueError("typed tree contains nested manifest")
                files[relative] = recovery._sha256(path)
            else:
                raise ValueError(f"typed tree contains nonordinary member: {relative}")

    visit(root)
    return {
        "schema": TREE_SCHEMA,
        "directories": sorted(directories),
        "files": dict(sorted(files.items())),
    }


def _build_controller_receipt(
    config: Mapping[str, Any], parent_identity: Mapping[str, Any]
) -> dict[str, object]:
    return {
        "schema": CONTROLLER_SCHEMA,
        "status": "controller_initialized_nonformal_pilot",
        "authority": _authority_bindings(),
        "parent_process_identity": dict(parent_identity),
        "blocks": list(BLOCKS),
        "formal_snapshot_before": _formal_snapshot(config),
        "parent_solver_calls": 0,
        "post_result_review_passed": False,
        "formal_execution_ready": False,
        "claim": False,
        "security_certified": False,
    }


def _expected_result_tree() -> tuple[set[str], set[str]]:
    directories = {"workers", *(f"workers/{block_id}" for block_id in BLOCKS)}
    files = {
        "config.yaml",
        "controller_receipt.json",
        "comparison.json",
        "summary.json",
        *(f"workers/{block_id}/{name}" for block_id in BLOCKS for name in ("payload.json", "receipt.json")),
    }
    return directories, files


def _publish_result(
    staging: Path,
    target: Path,
    *,
    config: Mapping[str, Any],
    controller: Mapping[str, Any],
    sources: Mapping[str, tuple[Mapping[str, Any], Path, Path]],
    pre_rename_test_hook: Callable[[Path], None] | None = None,
) -> dict[str, object]:
    """Validate, copy, revalidate, reread, then atomically rename one result tree."""

    if target.exists():
        raise FileExistsError("pilot result target already exists")
    if staging.exists():
        raise FileExistsError("pilot staging path already exists")
    if list(sources) != BLOCKS:
        raise ValueError("pilot source order/inventory drifted")
    staging.mkdir(parents=True, exist_ok=False)
    try:
        authority = _authority_bindings()
        if controller.get("authority") != authority:
            raise ValueError("controller authority drifted")
        source_memory: dict[str, tuple[dict[str, Any], str, str]] = {}
        copied: dict[str, tuple[Mapping[str, Any], Path, Path]] = {}
        worker_root = staging / "workers"
        worker_root.mkdir()
        for block_id, (envelope, source_payload, source_receipt) in sources.items():
            validated = _validate_worker_pair(
                source_payload, source_receipt, envelope=envelope
            )
            payload_sha = recovery._sha256(source_payload)
            receipt_sha = recovery._sha256(source_receipt)
            source_memory[block_id] = (validated, payload_sha, receipt_sha)
            destination = worker_root / block_id
            destination.mkdir()
            copied_payload = destination / "payload.json"
            copied_receipt = destination / "receipt.json"
            shutil.copyfile(source_payload, copied_payload)
            shutil.copyfile(source_receipt, copied_receipt)
            if (
                recovery._sha256(copied_payload) != payload_sha
                or recovery._sha256(copied_receipt) != receipt_sha
            ):
                raise ValueError("source-to-staging worker evidence copy drifted")
            _validate_worker_pair(copied_payload, copied_receipt, envelope=envelope)
            copied[block_id] = (envelope, copied_payload, copied_receipt)
        comparison = compare_named_outage_0008(
            source_memory[BLOCKS[0]][0], _extract_gurobi_payload()
        )
        if comparison.get("comparison_passed") is not True:
            raise RuntimeError("named-outage comparison is unresolved or failed")
        summary = {
            "schema": "rq2_public_grid_two_block_pilot_result_v3",
            "status": "complete_nonformal_pilot",
            "blocks": list(BLOCKS),
            "all_blocks_resolved": True,
            "named_outage_comparison_passed": True,
            "parent_solver_calls": 0,
            "post_result_review_passed": False,
            "formal_execution_ready": False,
            "claim": False,
            "security_certified": False,
        }
        shutil.copyfile(CONFIG, staging / "config.yaml")
        recovery._atomic_json(staging / "controller_receipt.json", dict(controller))
        recovery._atomic_json(staging / "comparison.json", comparison)
        recovery._atomic_json(staging / "summary.json", summary)
        manifest = _typed_tree(staging)
        expected_directories, expected_files = _expected_result_tree()
        if (
            set(manifest["directories"]) != expected_directories
            or set(recovery._mapping(manifest["files"], "result files")) != expected_files
        ):
            raise ValueError("pre-manifest result typed tree inventory drifted")
        recovery._atomic_json(staging / "SHA256SUMS.json", manifest)
        if pre_rename_test_hook is not None:
            pre_rename_test_hook(staging)

        # Final boundary: no memory-only acceptance. Re-read every authority and byte.
        _verify_predecessor_authority()
        _verify_recovery_and_semantic_authority()
        _verify_v3_chain()
        copied_config = _strict_path(
            staging / "config.yaml", must_exist=True, label="published config copy"
        )
        if recovery._sha256(copied_config) != recovery._sha256(CONFIG):
            raise ValueError("published config authority drifted")
        final_controller = recovery._mapping(
            _load_json(staging / "controller_receipt.json", "final controller"),
            "final controller",
        )
        if final_controller != dict(controller):
            raise ValueError("final controller receipt drifted")
        if controller.get("formal_snapshot_before") != _formal_snapshot(config):
            raise ValueError("formal artifacts changed before publication")
        observed_manifest = recovery._mapping(
            _load_json(staging / "SHA256SUMS.json", "final typed manifest"),
            "final typed manifest",
        )
        final_tree = _typed_tree(staging)
        if observed_manifest != final_tree:
            raise ValueError("final typed manifest/tree drifted")
        if (
            set(final_tree["directories"]) != expected_directories
            or set(recovery._mapping(final_tree["files"], "final files")) != expected_files
        ):
            raise ValueError("final result exact tree inventory drifted")
        reread_payloads: dict[str, dict[str, Any]] = {}
        for block_id, (envelope, payload_path, receipt_path) in copied.items():
            reread_payloads[block_id] = _validate_worker_pair(
                payload_path, receipt_path, envelope=envelope
            )
        final_comparison = compare_named_outage_0008(
            reread_payloads[BLOCKS[0]], _extract_gurobi_payload()
        )
        observed_comparison = recovery._mapping(
            _load_json(staging / "comparison.json", "final comparison"),
            "final comparison",
        )
        if final_comparison != comparison or observed_comparison != comparison:
            raise ValueError("final named-outage comparison drifted")
        observed_summary = recovery._mapping(
            _load_json(staging / "summary.json", "final summary"), "final summary"
        )
        if observed_summary != summary:
            raise ValueError("final summary drifted")
        if target.exists():
            raise FileExistsError("pilot target appeared before atomic rename")
        staging.rename(target)
        return summary
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _windows_popen_kwargs(read_handle: int, ack_handle: int) -> dict[str, object]:
    startup = subprocess.STARTUPINFO()
    startup.lpAttributeList = {"handle_list": [read_handle, ack_handle]}
    return {"startupinfo": startup, "close_fds": True}


def _dispatch_one(
    config: Mapping[str, Any],
    *,
    block_id: str,
    roots: Mapping[str, Path],
) -> tuple[dict[str, Any], Path, Path]:
    """Future execution path; unreachable while candidate v3 gates remain closed."""

    _require_execution_authority()
    python = _strict_path(Path(sys.executable), must_exist=True, label="worker Python")
    parent = _query_process_identity(os.getpid())
    if parent.get("command") != _expected_controller_command(python):
        raise ValueError("controller exact command drifted")
    request_read, request_write = os.pipe()
    ack_read, ack_write = os.pipe()
    worker_handle_read = request_read
    worker_handle_ack = ack_write
    if os.name == "nt":
        import msvcrt

        worker_handle_read = msvcrt.get_osfhandle(request_read)
        worker_handle_ack = msvcrt.get_osfhandle(ack_write)
    for descriptor in (request_read, ack_write):
        os.set_inheritable(descriptor, True)
    command = _expected_worker_command(
        python, read_handle=worker_handle_read, ack_handle=worker_handle_ack
    )
    environment = _sanitized_environment()
    popen_kwargs: dict[str, object] = {
        "cwd": ROOT,
        "env": environment,
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": False,
    }
    if os.name == "nt":
        popen_kwargs.update(_windows_popen_kwargs(worker_handle_read, worker_handle_ack))
    else:
        popen_kwargs["pass_fds"] = (request_read, ack_write)
        popen_kwargs["close_fds"] = True
    process = subprocess.Popen(command, **popen_kwargs)
    os.close(request_read)
    os.close(ack_write)
    try:
        hello = _read_frame(ack_read, "worker hello")
        observed_worker = _query_process_identity(process.pid)
        if hello != {
            "schema": HELLO_SCHEMA,
            "worker_process_identity": observed_worker,
            "candidate_v3_outer_sha256": recovery._sha256(OUTER),
        }:
            raise ValueError("worker hello/PID/create-time identity drifted")
        nonce = secrets.token_hex(32)
        result_path = roots["worker"] / block_id / nonce / "payload.json"
        envelope = _build_capability_envelope(
            config,
            block_id=block_id,
            parent_identity=parent,
            worker_identity=observed_worker,
            result_path=result_path,
            read_handle=worker_handle_read,
            ack_handle=worker_handle_ack,
            environment=environment,
            nonce=nonce,
        )
        _write_frame(request_write, envelope)
        os.close(request_write)
        request_write = -1
        ack = _read_frame(ack_read, "worker capability ack")
        if ack != {
            "schema": ACK_SCHEMA,
            "capability_envelope_sha256": _canonical_hash(envelope),
            "worker_process_identity": observed_worker,
            "accepted_once": True,
        }:
            raise ValueError("worker one-time capability ack drifted")
        wait = recovery._wait_worker(
            process, _stage_context()["config"]["execution"]["process_isolation"]
        )
        if wait["status"] != "exited" or wait["exit_code"] != 0:
            raise RuntimeError(
                f"pilot worker ended {wait['status']}; unresolved, not infeasible"
            )
        receipt_path = result_path.with_name("receipt.json")
        recovery._atomic_json(
            receipt_path, _build_worker_receipt(envelope, result_path)
        )
        _validate_worker_pair(result_path, receipt_path, envelope=envelope)
        return envelope, result_path, receipt_path
    finally:
        for descriptor in (request_write, ack_read):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


def run(*, validate_only: bool = False) -> dict[str, object]:
    if validate_only:
        from experiments.validate_rq2_public_grid_two_block_pilot_candidate_v3 import (
            validate,
        )

        return validate()
    config = _require_execution_authority()
    roots = _pilot_roots(config)
    if any(path.exists() for path in roots.values()):
        raise FileExistsError("all pilot v3 roots must be fresh")
    parent = _query_process_identity(os.getpid())
    controller = _build_controller_receipt(config, parent)
    roots["worker"].mkdir(parents=True, exist_ok=False)
    roots["log"].mkdir(parents=True, exist_ok=False)
    sources = {
        block_id: _dispatch_one(config, block_id=block_id, roots=roots)
        for block_id in BLOCKS
    }
    staging = roots["result"].parent / f".{roots['result'].name}.staging.{secrets.token_hex(16)}"
    return _publish_result(
        staging,
        roots["result"],
        config=config,
        controller=controller,
        sources=sources,
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--internal-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--read-handle", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--ack-handle", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.internal_worker:
        if args.validate_only or args.read_handle is None or args.ack_handle is None:
            parser.error("internal worker requires exactly two inherited pipe handles")
    elif args.read_handle is not None or args.ack_handle is not None:
        parser.error("pipe handles require internal worker mode")
    return args


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.internal_worker:
        read_handle = int(args.read_handle)
        ack_handle = int(args.ack_handle)
        read_descriptor = read_handle
        ack_descriptor = ack_handle
        if os.name == "nt":
            import msvcrt

            read_descriptor = msvcrt.open_osfhandle(read_descriptor, os.O_RDONLY)
            ack_descriptor = msvcrt.open_osfhandle(ack_descriptor, os.O_WRONLY)
        raise SystemExit(
            _worker_from_capability(
                read_descriptor,
                ack_descriptor,
                read_handle=read_handle,
                ack_handle=ack_handle,
            )
        )
    report = run(validate_only=bool(args.validate_only))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
