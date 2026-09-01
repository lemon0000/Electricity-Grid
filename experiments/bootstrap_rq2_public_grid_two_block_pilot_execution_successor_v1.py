"""Closed, standard-library-only bootstrap for the reviewed v7 pilot successor.

This module validates authority and host preconditions.  It has no execution
entry point and deliberately imports no project package, loader, worker, or
solver.
"""

from __future__ import annotations

import argparse
import ctypes
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
CONFIG_REL = "configs/rq2_public_grid_two_block_pilot_execution_successor_v1.json"
INNER_REL = (
    "configs/rq2_public_grid_two_block_pilot_execution_successor_v1.SHA256SUMS.json"
)
OUTER_REL = (
    "configs/rq2_public_grid_two_block_pilot_execution_successor_v1.OUTER.SHA256SUMS.json"
)
PASS_REL = "configs/rq2_public_grid_two_block_pilot_pre_run_review_pass_v7.json"
PASS_EXPECTED_SHA256 = "a98298f270e57b699808dad0e5b97cd9475a688e6d9ca7b263428ca95aa233a4"
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
SELF_REL = "experiments/bootstrap_rq2_public_grid_two_block_pilot_execution_successor_v1.py"
TEST_REL = "tests/test_rq2_public_grid_two_block_pilot_execution_successor_v1.py"
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
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
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


def _strict_existing(path: Path, *, regular_file: bool) -> None:
    raw = str(path)
    if not os.path.isabs(raw) or os.path.normpath(raw) != raw:
        raise BootstrapRejected(f"non-canonical authority path: {raw}")
    drive, tail = os.path.splitdrive(raw)
    current = Path(drive + os.sep)
    for segment in [part for part in tail.split(os.sep) if part]:
        current = current / segment
        if not os.path.lexists(current):
            raise BootstrapRejected(f"authority path is absent: {current}")
        try:
            info = os.lstat(current)
        except OSError as exc:
            raise BootstrapRejected(f"authority path is inaccessible: {current}") from exc
        if stat.S_ISLNK(info.st_mode) or _is_reparse(current, info):
            raise BootstrapRejected(f"authority path alias/reparse rejected: {current}")
        if os.path.ismount(current) and current != Path(drive + os.sep):
            raise BootstrapRejected(f"nested mount rejected: {current}")
    info = os.lstat(path)
    if regular_file and not stat.S_ISREG(info.st_mode):
        raise BootstrapRejected(f"authority is not a regular file: {path}")
    if not regular_file and not stat.S_ISDIR(info.st_mode):
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
        if not os.path.lexists(current):
            return
        try:
            info = os.lstat(current)
        except OSError as exc:
            raise BootstrapRejected(f"root ancestor is inaccessible: {current}") from exc
        if stat.S_ISLNK(info.st_mode) or _is_reparse(current, info):
            raise BootstrapRejected(f"root ancestor alias/reparse rejected: {current}")
        if os.path.ismount(current) and current != Path(drive + os.sep):
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


def _reject_project_preimport(modules: Sequence[str] | None = None) -> None:
    observed = tuple(_PREIMPORT_PROJECT_MODULES if modules is None else modules)
    if observed:
        raise BootstrapRejected(f"project module preimport rejected: {observed}")


def _verify_static_authority() -> dict[str, Any]:
    _strict_existing(ROOT, regular_file=False)
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
        != "rq2_public_grid_two_block_pilot_execution_successor_v1"
        or config.get("status") != "execution_successor_candidate_closed"
        or config.get("scientific_transport_ledger_postcommit_or_frozen_formal_semantics_changed")
        is not False
    ):
        raise BootstrapRejected("successor config identity mismatch")
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
        != "rq2_public_grid_two_block_pilot_execution_successor_bundle_v1"
        or not isinstance(inner_files, dict)
        or set(inner_files) != {CONFIG_REL, PASS_REL, SELF_REL, TEST_REL}
    ):
        raise BootstrapRejected("successor inner manifest mismatch")
    for member, expected in inner_files.items():
        if not isinstance(expected, str) or len(expected) != 64:
            raise BootstrapRejected("successor inner hash malformed")
        _require_hash(member, expected)
    inner_hash = _sha256(ROOT / INNER_REL)
    _require_exact_manifest(
        OUTER_REL,
        "rq2_public_grid_two_block_pilot_execution_successor_outer_v1",
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
    checkpoint_dir = ROOT / str(formal["checkpoint_directory"])
    _strict_existing(checkpoint_dir, regular_file=False)
    checkpoint_hashes = formal.get("checkpoint_sha256")
    if not isinstance(checkpoint_hashes, dict):
        raise BootstrapRejected("checkpoint hash inventory malformed")
    observed_files = sorted(
        item.name for item in checkpoint_dir.iterdir() if item.is_file()
    )
    if observed_files != sorted(checkpoint_hashes):
        raise BootstrapRejected("formal checkpoint inventory drift")
    for name, expected in checkpoint_hashes.items():
        _require_hash(f"{formal['checkpoint_directory']}/{name}", str(expected))
    return config


def _windows_processes() -> list[tuple[int, str]]:
    if os.name != "nt":
        raise BootstrapRejected("locked successor requires Windows")

    class PROCESSENTRY32W(ctypes.Structure):
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

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    kernel32.CreateToolhelp32Snapshot.argtypes = [ctypes.c_ulong, ctypes.c_ulong]
    kernel32.Process32FirstW.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(PROCESSENTRY32W),
    ]
    kernel32.Process32NextW.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(PROCESSENTRY32W),
    ]
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise BootstrapRejected("process inventory snapshot failed")
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    rows: list[tuple[int, str]] = []
    try:
        ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            rows.append((int(entry.th32ProcessID), str(entry.szExeFile).lower()))
            ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
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
    return {
        "executable": sys.executable,
        "executable_sha256": _sha256(Path(sys.executable)),
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


def _verify_runtime(config: Mapping[str, Any], observed: Mapping[str, Any]) -> None:
    contract = config.get("bootstrap_contract")
    if not isinstance(contract, dict):
        raise BootstrapRejected("bootstrap contract malformed")
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
        "schema": "rq2_public_grid_two_block_pilot_execution_successor_validation_v1",
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
