"""Secret-free public contract for closed evidence/publication successor v3."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_evidence_publication_successor_v3.json"
INNER = ROOT / "configs/rq2_public_grid_evidence_publication_successor_v3.SHA256SUMS.json"
OUTER = ROOT / "configs/rq2_public_grid_evidence_publication_successor_v3.OUTER.SHA256SUMS.json"
BLOCKS = ("holdout_s20260822_0008", "holdout_s20260822_0009")
STAGES = (
    "bootstrap_pre_controller_import",
    "worker_pre_fixture",
    "worker_post_validator_pre_write",
    "worker_post_write_pre_ack",
    "controller_post_child_pre_accept",
    "controller_post_block2_pre_result",
    "controller_post_result_pre_success",
    "controller_post_success_readback",
)
MAX_FRAME_BYTES = 8_000_000


class ContractRejected(RuntimeError):
    """A frozen authority, closure, transport, or schema failed closed."""


class LiveClosureDrift(ContractRejected):
    """A registered test boundary rejected the current closure."""


def exact_json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "ascii"
    )


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_stable(path: Path) -> bytes:
    try:
        before = path.lstat()
        first = path.read_bytes()
        middle = path.lstat()
        second = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise ContractRejected(f"authority unreadable: {path}") from exc
    if path.is_symlink() or not stat.S_ISREG(before.st_mode) or first != second:
        raise ContractRejected(f"authority is not one stable ordinary file: {path}")
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
    if identity(before) != identity(middle) or identity(middle) != identity(after):
        raise ContractRejected(f"authority changed while read: {path}")
    if getattr(before, "st_file_attributes", 0) & 0x400:
        raise ContractRejected(f"authority is a Windows reparse point: {path}")
    return first


def load_config() -> dict[str, Any]:
    try:
        value = json.loads(read_stable(CONFIG))
    except json.JSONDecodeError as exc:
        raise ContractRejected("v3 config JSON malformed") from exc
    if not isinstance(value, dict) or value.get("status") != (
        "evidence_publication_successor_v3_review_closed"
    ):
        raise ContractRejected("v3 config identity drifted")
    if tuple(value.get("blocks", ())) != BLOCKS:
        raise ContractRejected("v3 block order drifted")
    gates = value.get("gates")
    if not isinstance(gates, dict) or any(gates.values()):
        raise ContractRejected("v3 gates are not all closed")
    expected_truth = [
        {
            "condition": "result_clean_absent_and_success_clean_absent_and_terminal_clean_absent_with_ordinary_ancestors",
            "classification": "honest_incomplete",
        },
        {
            "condition": "exact_v3_result_and_exact_bound_success_and_terminal_clean_absent",
            "classification": "committed_success",
        },
        {
            "condition": "any_other_presence_alias_unreadable_corrupt_mismatch_or_dual_state",
            "classification": "commit_indeterminate",
        },
    ]
    if value.get("publication_truth_table") != expected_truth:
        raise ContractRejected("v3 publication truth table drifted")
    return value


def _add(mapping: dict[str, str], relative: str, expected: str) -> None:
    if not isinstance(relative, str) or not isinstance(expected, str):
        raise ContractRejected("closure binding malformed")
    raw = read_stable(ROOT / relative)
    observed = sha256_bytes(raw)
    if observed != expected:
        raise ContractRejected(f"live dependency drifted: {relative}")
    previous = mapping.setdefault(relative, observed)
    if previous != observed:
        raise ContractRejected(f"duplicate dependency binding drifted: {relative}")


def merge_exact_bindings(target: dict[str, str], source: dict[str, str]) -> None:
    """Merge one exact map; equal duplicates deduplicate and conflicts reject."""
    for relative, digest in source.items():
        if not isinstance(relative, str) or not isinstance(digest, str):
            raise ContractRejected("closure mapping entry malformed")
        previous = target.setdefault(relative, digest)
        if previous != digest:
            raise ContractRejected(f"duplicate closure binding drifted: {relative}")


def _exact_bundle(spec: dict[str, Any], *, version: int) -> dict[str, str]:
    outer_raw = read_stable(ROOT / spec["outer_path"])
    inner_raw = read_stable(ROOT / spec["inner_path"])
    if (
        sha256_bytes(outer_raw) != spec["outer_sha256"]
        or sha256_bytes(inner_raw) != spec["inner_sha256"]
    ):
        raise ContractRejected(f"v{version} bundle authority drifted")
    try:
        outer = json.loads(outer_raw)
        inner = json.loads(inner_raw)
    except json.JSONDecodeError as exc:
        raise ContractRejected(f"v{version} bundle JSON malformed") from exc
    expected_outer = {
        "schema": f"rq2_public_grid_evidence_publication_successor_outer_v{version}",
        "files": {spec["inner_path"]: spec["inner_sha256"]},
    }
    files = inner.get("files") if isinstance(inner, dict) else None
    if (
        outer != expected_outer
        or inner.get("schema") != spec["inner_schema"]
        or not isinstance(files, dict)
        or len(files) != spec["exact_member_count"]
    ):
        raise ContractRejected(f"v{version} exact bundle schema drifted")
    mapping = {
        spec["outer_path"]: spec["outer_sha256"],
        spec["inner_path"]: spec["inner_sha256"],
    }
    for relative, expected in files.items():
        _add(mapping, relative, expected)
    return mapping


def _execution_trace(config: dict[str, Any]) -> dict[str, str]:
    authority = config["closure_construction"]["execution_trace_authority"]
    _add({}, authority["module_path"], authority["module_sha256"])
    _add({}, authority["config_path"], authority["config_sha256"])
    from experiments import rq2_public_grid_execution_runtime_contract_v3 as sealed

    try:
        sealed_config = json.loads(read_stable(ROOT / authority["config_path"]))
    except json.JSONDecodeError as exc:
        raise ContractRejected("sealed execution-v3 config malformed") from exc
    observed: dict[str, str] = {}

    def trace(relative: str, digest: str) -> None:
        merge_exact_bindings(observed, {relative: digest})

    try:
        returned = sealed.verify_full_live_closure(
            ROOT, sealed_config, trace=trace
        )
    except Exception as exc:
        raise ContractRejected("sealed execution-v3 trace rejected") from exc
    if tuple(sorted(observed)) != returned:
        raise ContractRejected("sealed execution-v3 trace/return inventory drifted")
    if (
        len(observed) != authority["expected_exact_count"]
        or sealed.canonical_sha256(dict(sorted(observed.items())))
        != authority["expected_mapping_sha256"]
    ):
        raise ContractRejected("sealed execution-v3 exact trace drifted")
    return dict(sorted(observed.items()))


def _self_noncyclic_mapping(config: dict[str, Any]) -> dict[str, str]:
    try:
        inner_raw = read_stable(INNER)
        outer_raw = read_stable(OUTER)
        inner = json.loads(inner_raw)
        outer = json.loads(outer_raw)
    except (json.JSONDecodeError, ContractRejected) as exc:
        raise ContractRejected("v3 manifests unavailable") from exc
    inner_relative = INNER.relative_to(ROOT).as_posix()
    if outer != {
        "schema": "rq2_public_grid_evidence_publication_successor_outer_v3",
        "files": {inner_relative: sha256_bytes(inner_raw)},
    }:
        raise ContractRejected("v3 outer binding drifted")
    own_files = inner.get("files") if isinstance(inner, dict) else None
    expected_members = set(config["bundle"]["members"].values())
    if (
        inner.get("schema")
        != "rq2_public_grid_evidence_publication_successor_bundle_v3"
        or not isinstance(own_files, dict)
        or set(own_files) != expected_members
        or len(own_files) != config["bundle"]["exact_member_count"]
    ):
        raise ContractRejected("v3 inner inventory drifted")
    mapping: dict[str, str] = {}
    for relative in config["closure_construction"]["self_noncyclic_member_paths"]:
        expected = own_files.get(relative)
        if not isinstance(expected, str):
            raise ContractRejected("v3 self closure member missing from inner seal")
        _add(mapping, relative, expected)
    return mapping


def _construct_full_live_closure() -> dict[str, str]:
    config = load_config()
    construction = config["closure_construction"]
    mapping: dict[str, str] = {}
    merge_exact_bindings(mapping, _execution_trace(config))
    merge_exact_bindings(
        mapping, _exact_bundle(construction["v1_exact_bundle"], version=1)
    )
    merge_exact_bindings(
        mapping, _exact_bundle(construction["v2_exact_bundle"], version=2)
    )
    merge_exact_bindings(mapping, _self_noncyclic_mapping(config))
    required = construction["expected_required_paths"]
    if (
        not isinstance(required, list)
        or required != sorted(required)
        or len(required) != len(set(required))
        or set(mapping) != set(required)
        or len(mapping) != construction["expected_exact_count"]
    ):
        raise ContractRejected("v3 required-path exact set drifted")
    return dict(sorted(mapping.items()))


def verify_full_live_closure() -> dict[str, str]:
    """Return only the exact frozen 95-path provenance mapping."""
    config = load_config()
    mapping = _construct_full_live_closure()
    if closure_mapping_sha256(mapping) != config["closure_construction"][
        "expected_mapping_sha256"
    ]:
        raise ContractRejected("v3 canonical closure mapping digest drifted")
    return mapping


def closure_mapping_sha256(mapping: dict[str, str]) -> str:
    if not mapping or any(
        not isinstance(path, str) or not isinstance(digest, str) or len(digest) != 64
        for path, digest in mapping.items()
    ):
        raise ContractRejected("closure mapping malformed")
    return sha256_bytes(exact_json_bytes(dict(sorted(mapping.items()))))


class StageAwareClosureVerifier:
    def __init__(self, fault_stage: str | None = None) -> None:
        if fault_stage is not None and fault_stage not in STAGES:
            raise ContractRejected("unregistered closure stage")
        self.fault_stage = fault_stage
        self.stages: list[str] = []

    def verify(self, stage: str) -> dict[str, str]:
        if stage not in STAGES:
            raise ContractRejected("unregistered closure stage")
        mapping = verify_full_live_closure()
        self.stages.append(stage)
        if stage == self.fault_stage:
            raise LiveClosureDrift(f"injected live closure drift at {stage}")
        return mapping


def build_review_fixture_payload(block_id: str) -> dict[str, Any]:
    if block_id not in BLOCKS:
        raise ContractRejected("fixture block is unregistered")
    from experiments import rq2_public_grid_evidence_publication_contract_v1 as prior

    payload = prior.build_review_fixture_payload(block_id)
    raw = exact_json_bytes(payload)
    if sha256_bytes(raw) != load_config()["fixture"]["payload_sha256"][block_id]:
        raise ContractRejected("review fixture hash drifted")
    return payload


def validate_scientific_payload(payload: dict[str, Any], block_id: str) -> None:
    from experiments import rq2_public_grid_evidence_publication_contract_v1 as prior

    prior.validate_scientific_payload(payload, block_id)


def process_create_time_ns(pid: int) -> int:
    if pid <= 0:
        raise ContractRejected("invalid PID")
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetProcessTimes.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
        ]
        kernel32.GetProcessTimes.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            raise ContractRejected("process identity inaccessible")
        created = wintypes.FILETIME()
        exited = wintypes.FILETIME()
        kernel = wintypes.FILETIME()
        user = wintypes.FILETIME()
        try:
            if not kernel32.GetProcessTimes(
                handle,
                ctypes.byref(created),
                ctypes.byref(exited),
                ctypes.byref(kernel),
                ctypes.byref(user),
            ):
                raise ContractRejected("process creation time unavailable")
        finally:
            kernel32.CloseHandle(handle)
        return ((created.dwHighDateTime << 32) | created.dwLowDateTime) * 100
    try:
        return Path(f"/proc/{pid}").stat().st_ctime_ns
    except OSError as exc:
        if pid == os.getpid():
            return int(time.time_ns() - time.monotonic_ns())
        raise ContractRejected("process creation time unavailable") from exc


def observe_pipe_endpoint(
    identifier: int, *, role: str, direction: str, inherited: bool
) -> dict[str, object]:
    if type(identifier) is not int or identifier < 0:
        raise ContractRejected("pipe identifier malformed")
    observed_inherited: bool
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetFileType.argtypes = [wintypes.HANDLE]
        kernel32.GetFileType.restype = wintypes.DWORD
        kernel32.GetHandleInformation.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.GetHandleInformation.restype = wintypes.BOOL
        kernel32.PeekNamedPipe.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.PeekNamedPipe.restype = wintypes.BOOL
        kernel32.WriteFile.argtypes = [
            wintypes.HANDLE,
            wintypes.LPCVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPVOID,
        ]
        kernel32.WriteFile.restype = wintypes.BOOL
        handle = wintypes.HANDLE(identifier)
        if kernel32.GetFileType(handle) != 3:
            raise ContractRejected("Windows handle is not a pipe")
        flags = wintypes.DWORD(0)
        if not kernel32.GetHandleInformation(handle, ctypes.byref(flags)):
            raise ContractRejected("Windows pipe inheritance unavailable")
        observed_inherited = bool(flags.value & 1)
        transferred = wintypes.DWORD(0)
        if direction == "read":
            available = wintypes.DWORD(0)
            ok = kernel32.PeekNamedPipe(
                handle, None, 0, None, ctypes.byref(available), None
            )
        elif direction == "write":
            ok = kernel32.WriteFile(
                handle, None, 0, ctypes.byref(transferred), None
            )
        else:
            raise ContractRejected("pipe direction malformed")
        if not ok:
            raise ContractRejected("Windows pipe direction drifted")
    else:
        import fcntl

        observed = os.fstat(identifier)
        if not stat.S_ISFIFO(observed.st_mode):
            raise ContractRejected("descriptor is not an anonymous pipe")
        mode = fcntl.fcntl(identifier, fcntl.F_GETFL) & os.O_ACCMODE
        expected_mode = os.O_RDONLY if direction == "read" else os.O_WRONLY
        if mode != expected_mode:
            raise ContractRejected("POSIX pipe direction drifted")
        observed_inherited = os.get_inheritable(identifier)
    if observed_inherited is not inherited:
        raise ContractRejected("pipe inheritance drifted")
    return {
        "raw_identifier": identifier,
        "type": "anonymous_pipe",
        "role": role,
        "direction": direction,
        "inherited": inherited,
    }


def exact_worker_command(
    *, read_handle: int, ack_handle: int, parent_pid: int, parent_create_time_ns: int
) -> tuple[str, ...]:
    config = load_config()
    return (
        config["runtime"]["locked_python_executable"],
        "-B",
        "-m",
        config["runtime"]["worker_module"],
        "--internal-review-fixture-worker",
        "--read-handle",
        str(read_handle),
        "--ack-handle",
        str(ack_handle),
        "--parent-pid",
        str(parent_pid),
        "--parent-create-time-ns",
        str(parent_create_time_ns),
    )


def write_frame(descriptor: int, value: object) -> bytes:
    raw = exact_json_bytes(value)
    if len(raw) > MAX_FRAME_BYTES:
        raise ContractRejected("frame oversized")
    framed = len(raw).to_bytes(8, "big") + raw
    written = 0
    while written < len(framed):
        count = os.write(descriptor, framed[written:])
        if count <= 0:
            raise ContractRejected("frame write failed")
        written += count
    return raw


def _read_exact(descriptor: int, size: int) -> bytes:
    collected = bytearray()
    while len(collected) < size:
        chunk = os.read(descriptor, size - len(collected))
        if not chunk:
            raise ContractRejected("unexpected frame EOF")
        collected.extend(chunk)
    return bytes(collected)


def read_frame(descriptor: int, label: str) -> tuple[bytes, dict[str, Any]]:
    size = int.from_bytes(_read_exact(descriptor, 8), "big")
    if size <= 0 or size > MAX_FRAME_BYTES:
        raise ContractRejected(f"{label} frame size rejected")
    raw = _read_exact(descriptor, size)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ContractRejected(f"{label} JSON malformed") from exc
    if not isinstance(value, dict) or exact_json_bytes(value) != raw:
        raise ContractRejected(f"{label} canonical schema rejected")
    return raw, value


def require_eof(descriptor: int) -> None:
    if os.read(descriptor, 1) != b"":
        raise ContractRejected("trailing/replayed pipe byte rejected")
