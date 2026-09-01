"""Closed, standard-library-only bootstrap for execution-successor v2.

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
from typing import Any

PROJECT_IMPORTS_PERMITTED = False
ROOT = Path(r"D:\CUHKSZ\Research Project\electricity-grid")
CONFIG_REL = "configs/rq2_public_grid_two_block_pilot_execution_successor_v2.json"
INNER_REL = (
    "configs/rq2_public_grid_two_block_pilot_execution_successor_v2.SHA256SUMS.json"
)
OUTER_REL = (
    "configs/rq2_public_grid_two_block_pilot_execution_successor_v2.OUTER.SHA256SUMS.json"
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
SELF_REL = "experiments/bootstrap_rq2_public_grid_two_block_pilot_execution_successor_v2.py"
TEST_REL = "tests/test_rq2_public_grid_two_block_pilot_execution_successor_v2.py"
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
        != "rq2_public_grid_two_block_pilot_execution_successor_v2"
        or config.get("status") != "execution_successor_v2_candidate_closed"
        or config.get("scientific_transport_ledger_postcommit_or_frozen_formal_semantics_changed")
        is not False
    ):
        raise BootstrapRejected("successor config identity mismatch")
    predecessor = config.get("predecessor_authority")
    expected_predecessor = {
        "execution_successor_v1_inner_path": V1_INNER_REL,
        "execution_successor_v1_inner_sha256": V1_INNER_EXPECTED_SHA256,
        "execution_successor_v1_outer_path": V1_OUTER_REL,
        "execution_successor_v1_outer_sha256": V1_OUTER_EXPECTED_SHA256,
        "execution_successor_v1_rework_receipt_path": REWORK_REL,
        "execution_successor_v1_rework_receipt_sha256": REWORK_EXPECTED_SHA256,
        "v7_inner_path": V7_INNER_REL,
        "v7_inner_sha256": V7_INNER_EXPECTED_SHA256,
        "v7_outer_path": V7_OUTER_REL,
        "v7_outer_sha256": V7_OUTER_EXPECTED_SHA256,
        "v7_pass_receipt_path": PASS_REL,
        "user_authorization_path": USER_AUTH_REL,
        "user_authorization_sha256": USER_AUTH_EXPECTED_SHA256,
        "user_authorization_scope": "future_conditional_authority_only_after_pilot_postreview_and_activation_pass",
    }
    if predecessor != expected_predecessor:
        raise BootstrapRejected("successor predecessor authority mismatch")
    gates = config.get("gates")
    activation = config.get("future_external_activation")
    if not isinstance(gates, dict) or not isinstance(activation, dict):
        raise BootstrapRejected("successor gates malformed")
    required_false = {
        "successor_independent_review_passed",
        "successor_activation_present",
        "successor_execution_ready",
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
        raise BootstrapRejected("successor execution/claim gates are not closed")
    if (
        activation.get("independent_successor_review_receipt_path") is not None
        or activation.get("independent_successor_review_receipt_sha256") is not None
        or activation.get("activation_wrapper_path") is not None
        or activation.get("activation_wrapper_sha256") is not None
        or activation.get("dynamic_self_acceptance_forbidden") is not True
    ):
        raise BootstrapRejected("future external activation boundary mismatch")

    inner = _json(ROOT / INNER_REL)
    inner_files = inner.get("files")
    if (
        inner.get("schema")
        != "rq2_public_grid_two_block_pilot_execution_successor_bundle_v2"
        or not isinstance(inner_files, dict)
        or set(inner_files) != {CONFIG_REL, REWORK_REL, SELF_REL, TEST_REL}
    ):
        raise BootstrapRejected("successor inner manifest mismatch")
    for member, expected in inner_files.items():
        if not isinstance(expected, str) or len(expected) != 64:
            raise BootstrapRejected("successor inner hash malformed")
        _require_hash(member, expected)
    inner_hash = _sha256(ROOT / INNER_REL)
    _require_exact_manifest(
        OUTER_REL,
        "rq2_public_grid_two_block_pilot_execution_successor_outer_v2",
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
    expected_argv = [executable, *list(contract["exact_argv_suffix"])]
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
    """Validate the closed successor without importing or executing project code."""

    _reject_project_preimport(preimport_modules)
    config = _verify_static_authority()
    observed = _runtime_observation() if runtime is None else runtime
    _verify_runtime(config, observed)
    _verify_roots(config, root_appearances)
    return {
        "schema": "rq2_public_grid_two_block_pilot_execution_successor_validation_v2",
        "validation_passed": True,
        "status": "READY_FOR_INDEPENDENT_REVIEW",
        "execution_ready": False,
        "independent_successor_review_passed": False,
        "activation_present": False,
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
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.validate_only:
        raise BootstrapRejected("closed successor supports validate-only mode exclusively")
    print(json.dumps(validate(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
