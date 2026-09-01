"""Pre-project-import bootstrap for execution-controller successor v1."""

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

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v1.json"
INNER = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v1.SHA256SUMS.json"
OUTER = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v1.OUTER.SHA256SUMS.json"
REVIEW = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_review_pass_v1.json"
CONTROLLER_MODULE = "experiments.run_rq2_public_grid_two_block_pilot_execution_controller_successor_v1"
_PREIMPORT_PROJECT_MODULES = tuple(
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


class BootstrapRejected(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise BootstrapRejected(f"unreadable artifact: {path}") from exc


def _is_reparse(metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    return bool(attributes & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)))


def _lstat_or_absent(path: Path) -> os.stat_result | None:
    try:
        return os.lstat(path)
    except FileNotFoundError as exc:
        if getattr(exc, "winerror", None) in (2, 3) or exc.errno == errno.ENOENT:
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
        raise BootstrapRejected(f"non-canonical artifact path: {raw}")
    drive, tail = os.path.splitdrive(raw)
    root = Path(drive + os.sep)
    current = root
    final: os.stat_result | None = None
    for segment in [part for part in tail.split(os.sep) if part]:
        current /= segment
        metadata = _lstat_or_absent(current)
        if metadata is None:
            raise BootstrapRejected(f"artifact path unavailable: {current}")
        if stat.S_ISLNK(metadata.st_mode) or _is_reparse(metadata):
            raise BootstrapRejected(f"artifact alias/reparse rejected: {current}")
        if current != root and _path_is_mount(current):
            raise BootstrapRejected(f"nested mount rejected: {current}")
        final = metadata
    if final is None:
        final = _lstat_or_absent(path)
    if final is None:
        raise BootstrapRejected(f"artifact path unavailable: {path}")
    if regular_file and not stat.S_ISREG(final.st_mode):
        raise BootstrapRejected(f"artifact is not ordinary: {path}")
    if not regular_file and not stat.S_ISDIR(final.st_mode):
        raise BootstrapRejected(f"artifact is not a directory: {path}")


def _strict_file(path: Path) -> None:
    _strict_existing(path, regular_file=True)


def _strict_absent(path: Path) -> None:
    raw = str(path)
    if not os.path.isabs(raw) or os.path.normpath(raw) != raw:
        raise BootstrapRejected(f"non-canonical root path: {raw}")
    drive, tail = os.path.splitdrive(raw)
    root = Path(drive + os.sep)
    current = root
    parts = [part for part in tail.split(os.sep) if part]
    for index, segment in enumerate(parts):
        current /= segment
        metadata = _lstat_or_absent(current)
        if metadata is None:
            return
        if stat.S_ISLNK(metadata.st_mode) or _is_reparse(metadata):
            raise BootstrapRejected(f"root alias/reparse rejected: {current}")
        if current != root and _path_is_mount(current):
            raise BootstrapRejected(f"root nested mount rejected: {current}")
        if index < len(parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
            raise BootstrapRejected(f"root ancestor is not a directory: {current}")
    raise BootstrapRejected(f"fresh root already appears: {path}")


def _json(path: Path) -> dict[str, Any]:
    _strict_file(path)
    first = path.read_bytes()
    second = path.read_bytes()
    if first != second:
        raise BootstrapRejected(f"artifact changed during double-read: {path}")
    try:
        value = json.loads(first)
    except json.JSONDecodeError as exc:
        raise BootstrapRejected(f"artifact JSON malformed: {path}") from exc
    if not isinstance(value, dict):
        raise BootstrapRejected(f"artifact JSON is not an object: {path}")
    return value


def _verify_manifest(path: Path) -> int:
    files = _json(path).get("files")
    if not isinstance(files, dict) or not files:
        raise BootstrapRejected("successor bundle inventory missing")
    for relative, digest in files.items():
        member = ROOT / str(relative)
        _strict_file(member)
        if not isinstance(digest, str) or _sha256(member) != digest:
            raise BootstrapRejected("successor bundle member drifted")
    return len(files)


def _audit_checkpoint_inventory(path: Path, expected: Mapping[str, str]) -> None:
    _strict_existing(path, regular_file=False)
    if len(expected) != 9:
        raise BootstrapRejected("checkpoint exact nine-file inventory required")
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
                    metadata = entry.stat(follow_symlinks=False)
                except OSError as exc:
                    raise BootstrapRejected(
                        f"checkpoint entry inaccessible: {entry.name}"
                    ) from exc
                if (
                    stat.S_ISLNK(metadata.st_mode)
                    or _is_reparse(metadata)
                    or not stat.S_ISREG(metadata.st_mode)
                ):
                    raise BootstrapRejected(
                        f"checkpoint entry is not ordinary: {entry.name}"
                    )
                _strict_file(entry_path)
                observed[entry.name] = entry_path
    except BootstrapRejected:
        raise
    except OSError as exc:
        raise BootstrapRejected("checkpoint directory enumeration failed") from exc
    if set(observed) != set(expected):
        raise BootstrapRejected("formal checkpoint exact inventory drifted")
    for name, checkpoint in observed.items():
        if _sha256(checkpoint) != expected[name]:
            raise BootstrapRejected(f"formal checkpoint hash drifted: {name}")


def _reject_project_preimport(modules: Sequence[str] | None = None) -> None:
    observed = tuple(_PREIMPORT_PROJECT_MODULES if modules is None else modules)
    if observed:
        raise BootstrapRejected(f"project module preimport rejected: {observed}")


def _available_commit() -> int:
    class MemoryStatus(ctypes.Structure):
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

    value = MemoryStatus()
    value.dwLength = ctypes.sizeof(value)
    if os.name != "nt" or not ctypes.WinDLL(
        "kernel32", use_last_error=True
    ).GlobalMemoryStatusEx(ctypes.byref(value)):
        raise BootstrapRejected("available commit observation failed")
    return int(value.ullAvailPageFile)


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
        self.kernel32.CreateToolhelp32Snapshot.argtypes = [ctypes.c_ulong, ctypes.c_ulong]
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
    observed: list[tuple[int, str]] = []
    try:
        if not toolhelp.first(snapshot, entry):
            raise BootstrapRejected("Process32FirstW failed")
        while True:
            observed.append((int(entry.th32ProcessID), str(entry.szExeFile).lower()))
            if toolhelp.next(snapshot, entry):
                continue
            error = toolhelp.last_error()
            if error == 18:
                break
            raise BootstrapRejected(f"Process32NextW failed with error {error}")
    finally:
        toolhelp.close(snapshot)
    if not any(pid == os.getpid() for pid, _name in observed):
        raise BootstrapRejected("process inventory omits current PID")
    return observed


def _process_age_seconds() -> float:
    if os.name != "nt":
        raise BootstrapRejected("locked successor requires Windows")

    class FILETIME(ctypes.Structure):
        _fields_ = [
            ("dwLowDateTime", ctypes.c_ulong),
            ("dwHighDateTime", ctypes.c_ulong),
        ]

        @property
        def ticks(self) -> int:
            return (int(self.dwHighDateTime) << 32) | int(self.dwLowDateTime)

    creation = FILETIME()
    exit_time = FILETIME()
    kernel = FILETIME()
    user = FILETIME()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
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


def _verify_runtime(config: Mapping[str, Any]) -> None:
    runtime = config["runtime"]
    python = Path(str(runtime["locked_python_executable"]))
    _strict_file(python)
    expected_validate = [
        str(python),
        "-B",
        "-m",
        str(config["successor_identity"]["bootstrap_module"]),
        "--validate-only",
    ]
    expected_execute = [*expected_validate[:-1], "--execute"]
    if list(sys.orig_argv) not in (expected_validate, expected_execute):
        raise BootstrapRejected("bootstrap exact module argv drifted")
    exact = {
        "executable": str(python),
        "executable_sha256": runtime["locked_python_sha256"],
        "version": runtime["locked_python_version"],
        "cwd": runtime["exact_cwd"],
        "hostname": runtime["host"]["hostname"],
        "system": runtime["host"]["system"],
        "release": runtime["host"]["release"],
        "machine": runtime["host"]["machine"],
        "environment": runtime["sanitized_environment"],
    }
    observed = {
        "executable": sys.executable,
        "executable_sha256": _sha256(Path(sys.executable)),
        "version": platform.python_version(),
        "cwd": os.getcwd(),
        "hostname": socket.gethostname(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "environment": dict(os.environ),
    }
    for key, expected in exact.items():
        if observed[key] != expected:
            raise BootstrapRejected(f"runtime identity mismatch: {key}")
    if not 0.0 <= _process_age_seconds() <= 30.0:
        raise BootstrapRejected("bootstrap process is not fresh")
    processes = _windows_processes()
    rejected = {"python.exe", "pythonw.exe", "highs.exe", "gurobi_cl.exe"}
    active = [
        (pid, name)
        for pid, name in processes
        if pid != os.getpid() and name in rejected
    ]
    if active:
        raise BootstrapRejected(f"active related process rejected: {active}")
    if _available_commit() < 10 * 1024**3:
        raise BootstrapRejected("successor host commit below 10 GiB preflight")


def validate_only() -> dict[str, Any]:
    _reject_project_preimport()
    _strict_existing(ROOT, regular_file=False)
    config = _json(CONFIG)
    if config.get("status") != "execution_controller_successor_v1_review_closed":
        raise BootstrapRejected("successor status drifted")
    chain = config["chain_authority"]
    for binding in chain.values():
        candidate = ROOT / binding["path"]
        _strict_file(candidate)
        if _sha256(candidate) != binding["sha256"]:
            raise BootstrapRejected("successor chain authority drifted")
    if _json(OUTER) != {
        "schema": "rq2_public_grid_two_block_pilot_execution_controller_successor_outer_v1",
        "files": {INNER.relative_to(ROOT).as_posix(): _sha256(INNER)},
    }:
        raise BootstrapRejected("successor outer binding drifted")
    members = _verify_manifest(INNER)
    _verify_runtime(config)
    for relative in config["paths"].values():
        _strict_absent(ROOT / relative)
    formal = config["formal_protection"]
    for path_key, hash_key in (
        ("formal_runner_path", "formal_runner_sha256"),
        ("activated_config_path", "activated_config_sha256"),
    ):
        artifact = ROOT / formal[path_key]
        _strict_file(artifact)
        if _sha256(artifact) != formal[hash_key]:
            raise BootstrapRejected("formal authority drifted")
    _audit_checkpoint_inventory(
        ROOT / formal["checkpoint_directory"], formal["checkpoint_sha256"]
    )
    gates = config["gates"]
    if (
        gates.get("successor_independent_review_passed") is not False
        or gates.get("fixed_execution_review_receipt_present") is not False
        or gates.get("execution_ready") is not False
        or gates.get("pilot_executed") is not False
        or gates.get("formal_execution_ready") is not False
        or gates.get("claim") is not False
        or gates.get("security_certified") is not False
    ):
        raise BootstrapRejected("successor review-closed gates drifted")
    review_metadata = _lstat_or_absent(REVIEW)
    if review_metadata is not None:
        _strict_file(REVIEW)
    return {
        "validation_passed": True,
        "bundle_members": members,
        "execution_review_present": review_metadata is not None,
        "execution_ready": False,
        "project_imports": 0,
        "workers": 0,
        "loader_calls": 0,
        "solver_calls": 0,
        "result_writes": 0,
        "formal_writes": 0,
    }


def _require_fixed_review_before_import() -> None:
    if _lstat_or_absent(REVIEW) is None:
        raise BootstrapRejected("fixed execution review receipt is absent")
    receipt = _json(REVIEW)
    config = _json(CONFIG)
    if (
        receipt.get("schema") != config["fixed_execution_review"]["schema"]
        or receipt.get("verdict") != "PASS"
        or receipt.get("reviewed_outer")
        != {"path": OUTER.relative_to(ROOT).as_posix(), "sha256": _sha256(OUTER)}
        or receipt.get("bound_chain") != config["chain_authority"]
    ):
        raise BootstrapRejected("fixed execution review receipt is inexact")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.validate_only == args.execute:
        raise BootstrapRejected("exactly one registered bootstrap mode is required")
    if args.validate_only:
        print(json.dumps(validate_only(), sort_keys=True))
        return 0
    validate_only()
    _require_fixed_review_before_import()
    module = __import__(CONTROLLER_MODULE, fromlist=["main"])
    return int(module.main(["--execute"]))


if __name__ == "__main__":
    raise SystemExit(main())
