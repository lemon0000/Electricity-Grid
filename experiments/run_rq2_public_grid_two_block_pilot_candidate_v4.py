"""Closed v4 remediation candidate for the RQ2 0008/0009 pilot.

The candidate cannot execute.  A future execution successor must receive this
candidate's reviewed outer digest from an external trust root.  Attempt,
controller-validation, and post-rename publication evidence are separate
states.  Failures are honest incomplete states and never infeasibility proof.
"""

from __future__ import annotations

import argparse
import ctypes
import dataclasses
import json
import os
import queue
import secrets
import shutil
import stat
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Any

from experiments import run_rq2_public_grid_two_block_pilot_candidate_v3 as predecessor

recovery = predecessor.recovery
ROOT = Path(__file__).resolve().parents[1]
MODULE = "experiments.run_rq2_public_grid_two_block_pilot_candidate_v4"
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v4.yaml"
REWORK = ROOT / "configs/rq2_public_grid_two_block_pilot_pre_run_review_rework_v3.yaml"
BUNDLE = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v4.SHA256SUMS.json"
OUTER = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v4.OUTER.SHA256SUMS.json"
BASE_CONFIG = predecessor.BASE_CONFIG
BLOCKS = list(predecessor.BLOCKS)

CONFIG_SCHEMA = "rq2_public_grid_two_block_pilot_candidate_v4"
ENVELOPE_SCHEMA = "rq2_public_grid_two_block_pilot_capability_envelope_v4"
HELLO_SCHEMA = "rq2_public_grid_two_block_pilot_worker_hello_v4"
ACK_SCHEMA = "rq2_public_grid_two_block_pilot_capability_ack_v4"
RESULT_SCHEMA = "rq2_public_grid_two_block_pilot_worker_result_v4"
ATTEMPT_RECEIPT_SCHEMA = "rq2_public_grid_two_block_pilot_attempt_receipt_v4"
VALIDATION_RECEIPT_SCHEMA = "rq2_public_grid_two_block_pilot_validation_receipt_v4"
CONTROLLER_SCHEMA = "rq2_public_grid_two_block_pilot_controller_receipt_v4"
TREE_SCHEMA = "rq2_public_grid_two_block_pilot_typed_tree_v4"
SUCCESS_SEAL_SCHEMA = "rq2_public_grid_two_block_pilot_published_seal_v4"
MAX_FRAME_BYTES = 32 * 1024 * 1024

REWORK_SHA256 = "af9a2b52b9bd3597804d523a5a16d0cec607f6616c40aa8b8b1a3e0373448ba3"
V1_INNER_SHA256 = predecessor.V1_INNER_SHA256
V1_OUTER_SHA256 = predecessor.V1_OUTER_SHA256
V2_INNER_SHA256 = predecessor.V2_INNER_SHA256
V2_OUTER_SHA256 = predecessor.V2_OUTER_SHA256
V2_ESCALATION_SHA256 = predecessor.ESCALATION_SHA256
V3_INNER_SHA256 = "9c3e0318daa06d7cac830c3e65f7bc9950b26c63f775cdabbe7d0315a9dad1d0"
V3_OUTER_SHA256 = "d08b3049e43837397b1459edc9f4ecfa8d7e20419bcbbbf73f68d109f3dd10f9"
V3_MEMBER_HASHES = {
    "configs/rq2_public_grid_two_block_pilot_candidate_v3.yaml": "fd6f0c01a425c6a431a4ac384d723a1c61f5516f0056a4d17e451ff1ed490e01",
    "configs/rq2_public_grid_two_block_pilot_user_authorization_v3.yaml": "f696e76a1fedba8335af62e8914b12bb9385606525cf8170d0b11ffdb3900e52",
    "experiments/run_rq2_public_grid_two_block_pilot_candidate_v3.py": "4248eaf3e25293ad20fafd67c09ec9e5293bb15a23618a91ec49c764d4710f6b",
    "experiments/validate_rq2_public_grid_two_block_pilot_candidate_v3.py": "7c578276f6e3483223ca1830b3c6e8135f6464ff906e140cecc8e7e56d2bccb8",
    "tests/test_rq2_public_grid_two_block_pilot_candidate_v3.py": "3ba21a9933b4bd82bc6e8192103c17a2faaf30741031a534f3a60289efea04f1",
}
V4_BUNDLE_INVENTORY = {
    "configs/rq2_public_grid_two_block_pilot_candidate_v4.yaml",
    "configs/rq2_public_grid_two_block_pilot_pre_run_review_rework_v3.yaml",
    "experiments/run_rq2_public_grid_two_block_pilot_candidate_v4.py",
    "experiments/validate_rq2_public_grid_two_block_pilot_candidate_v4.py",
    "tests/test_rq2_public_grid_two_block_pilot_candidate_v4.py",
}


def _sha256(path: Path) -> str:
    return recovery._sha256(path)


def _sha256_bytes(payload: bytes) -> str:
    import hashlib

    return hashlib.sha256(payload).hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    return recovery._canonical_bytes(payload)


def _canonical_sha256(payload: object) -> str:
    return recovery._canonical_sha256(payload)


def _load_json(path: Path, label: str) -> Any:
    return recovery._load_json_strict(path, label)


def _load_yaml(path: Path, label: str) -> dict[str, Any]:
    return recovery._load_yaml_mapping(path, label)


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


def _verify_file(path: Path, expected: str, label: str) -> None:
    observed = _strict_path(path, must_exist=True, label=label)
    if not observed.is_file() or _sha256(observed) != expected:
        raise ValueError(f"{label} authority hash drifted")


def _verify_bundle(
    *, version: int, inner_sha: str, outer_sha: str, expected_count: int
) -> dict[str, str]:
    inner = ROOT / f"configs/rq2_public_grid_two_block_pilot_candidate_v{version}.SHA256SUMS.json"
    outer = ROOT / f"configs/rq2_public_grid_two_block_pilot_candidate_v{version}.OUTER.SHA256SUMS.json"
    _verify_file(inner, inner_sha, f"v{version} inner")
    _verify_file(outer, outer_sha, f"v{version} outer")
    outer_payload = recovery._mapping(_load_json(outer, "outer"), "outer")
    if outer_payload != {
        "schema": f"rq2_public_grid_two_block_pilot_candidate_outer_v{version}",
        "files": {inner.relative_to(ROOT).as_posix(): inner_sha},
    }:
        raise ValueError(f"v{version} outer authority drifted")
    inner_payload = recovery._mapping(_load_json(inner, "inner"), "inner")
    files = recovery._mapping(inner_payload.get("files"), "inner files")
    if len(files) != expected_count:
        raise ValueError(f"v{version} inner member inventory drifted")
    for relative, expected in files.items():
        _verify_file(ROOT / str(relative), str(expected), f"v{version} member {relative}")
    return {str(key): str(value) for key, value in files.items()}


def _verify_predecessor_authority() -> dict[str, object]:
    v1 = _verify_bundle(
        version=1,
        inner_sha=V1_INNER_SHA256,
        outer_sha=V1_OUTER_SHA256,
        expected_count=6,
    )
    v2 = _verify_bundle(
        version=2,
        inner_sha=V2_INNER_SHA256,
        outer_sha=V2_OUTER_SHA256,
        expected_count=6,
    )
    _verify_file(predecessor.ESCALATION, V2_ESCALATION_SHA256, "v2 ESCALATE")
    _verify_file(predecessor.RECOVERY_MANIFEST, predecessor.RECOVERY_MANIFEST_SHA256, "recovery manifest")
    recovery_manifest = recovery._mapping(
        _load_json(predecessor.RECOVERY_MANIFEST, "recovery manifest"),
        "recovery manifest",
    )
    if len(recovery_manifest) != 7:
        raise ValueError("recovery member inventory drifted")
    for relative, expected in recovery_manifest.items():
        _verify_file(ROOT / str(relative), str(expected), f"recovery member {relative}")
    _verify_file(predecessor.RECOVERY_PASS, predecessor.RECOVERY_PASS_SHA256, "recovery PASS")
    for path, expected in predecessor.SEMANTIC_HASHES.items():
        _verify_file(path, expected, f"semantic authority {path.name}")
    v3 = _verify_bundle(
        version=3,
        inner_sha=V3_INNER_SHA256,
        outer_sha=V3_OUTER_SHA256,
        expected_count=5,
    )
    if v3 != V3_MEMBER_HASHES:
        raise ValueError("v3 exact member authority drifted")
    _verify_file(REWORK, REWORK_SHA256, "v3 REWORK receipt")
    rework = _load_yaml(REWORK, "v3 REWORK receipt")
    if rework.get("verdict") != "REWORK" or rework.get("effect", {}).get(
        "no_execution_authority"
    ) is not True:
        raise ValueError("v3 REWORK authority semantics drifted")
    return {"v1": v1, "v2": v2, "v3": v3, "recovery": dict(recovery_manifest)}


def _inspect_v4_chain() -> dict[str, object]:
    bundle_path = _strict_path(BUNDLE, must_exist=True, label="v4 inner")
    outer_path = _strict_path(OUTER, must_exist=True, label="v4 outer")
    bundle = recovery._mapping(_load_json(bundle_path, "v4 inner"), "v4 inner")
    if bundle.get("schema") != "rq2_public_grid_two_block_pilot_candidate_bundle_v4":
        raise ValueError("v4 inner schema drifted")
    files = recovery._mapping(bundle.get("files"), "v4 files")
    if set(files) != V4_BUNDLE_INVENTORY:
        raise ValueError("v4 inner exact inventory drifted")
    for relative, expected in files.items():
        if not recovery._is_sha256(expected):
            raise ValueError("v4 member hash malformed")
        _verify_file(ROOT / str(relative), str(expected), f"v4 member {relative}")
    inner_sha = _sha256(bundle_path)
    outer = recovery._mapping(_load_json(outer_path, "v4 outer"), "v4 outer")
    if outer != {
        "schema": "rq2_public_grid_two_block_pilot_candidate_outer_v4",
        "files": {BUNDLE.relative_to(ROOT).as_posix(): inner_sha},
    }:
        raise ValueError("v4 outer structural authority drifted")
    return {
        "files": {str(key): str(value) for key, value in files.items()},
        "inner_sha256": inner_sha,
        "outer_sha256": _sha256(outer_path),
    }


def _verify_v4_execution_chain(expected_outer_sha256: str | None) -> dict[str, object]:
    if expected_outer_sha256 is None or not recovery._is_sha256(expected_outer_sha256):
        raise ValueError("v4 external trust root is absent")
    chain = _inspect_v4_chain()
    if chain["outer_sha256"] != expected_outer_sha256:
        raise ValueError("v4 external trust root does not match reviewed outer")
    return chain


def _candidate_authority() -> dict[str, object]:
    _verify_predecessor_authority()
    chain = _inspect_v4_chain()
    return {
        "v1_outer_sha256": V1_OUTER_SHA256,
        "v2_outer_sha256": V2_OUTER_SHA256,
        "v2_escalation_sha256": V2_ESCALATION_SHA256,
        "v3_inner_sha256": V3_INNER_SHA256,
        "v3_outer_sha256": V3_OUTER_SHA256,
        "v3_rework_receipt_sha256": REWORK_SHA256,
        "recovery_manifest_sha256": predecessor.RECOVERY_MANIFEST_SHA256,
        "semantic_manifest_sha256": predecessor.SEMANTIC_HASHES[
            predecessor.SEMANTIC_MANIFEST
        ],
        "candidate_v4_inner_sha256": chain["inner_sha256"],
        "candidate_v4_outer_sha256": chain["outer_sha256"],
        "external_reviewed_outer_sha256": None,
    }


def _load_config() -> dict[str, Any]:
    config = _load_yaml(CONFIG, "candidate v4 config")
    if (
        config.get("schema") != CONFIG_SCHEMA
        or config.get("version") != 4
        or config.get("status") != "rework_candidate_v4_execution_closed"
    ):
        raise ValueError("candidate v4 config identity drifted")
    return config


def _require_execution_authority() -> dict[str, Any]:
    _verify_predecessor_authority()
    config = _load_config()
    gates = recovery._mapping(config.get("gates"), "candidate v4 gates")
    trust = recovery._mapping(
        config.get("external_execution_trust_root"), "external trust root"
    )
    required_true = (
        "independent_pre_run_review_passed",
        "execution_successor_present",
        "two_block_pilot_execution_ready",
    )
    if (
        any(gates.get(key) is not True for key in required_true)
        or trust.get("reviewed_outer_sha256") is None
    ):
        raise RuntimeError("candidate v4 execution authority is closed")
    _verify_v4_execution_chain(str(trust["reviewed_outer_sha256"]))
    raise RuntimeError("candidate v4 is permanently closed; an execution successor is required")


def _stage_context() -> dict[str, Any]:
    return predecessor._stage_context()


def _pilot_roots(config: Mapping[str, Any]) -> dict[str, Path]:
    paths = recovery._mapping(config.get("paths"), "v4 paths")
    roots = {
        "result": _strict_path(
            ROOT / str(paths["result_directory"]), must_exist=False, label="v4 result"
        ),
        "success_seal": _strict_path(
            ROOT / str(paths["success_seal_path"]),
            must_exist=False,
            label="v4 success seal",
        ),
        "worker": _strict_path(
            ROOT / str(paths["worker_staging_directory"]),
            must_exist=False,
            label="v4 worker",
        ),
        "log": _strict_path(
            ROOT / str(paths["attempt_log_directory"]),
            must_exist=False,
            label="v4 log",
        ),
    }
    if len(set(roots.values())) != len(roots):
        raise ValueError("v4 roots overlap")
    return roots


def _formal_snapshot(config: Mapping[str, Any]) -> dict[str, object]:
    predecessor_config = _load_yaml(
        ROOT / str(config["scientific_authority"]["predecessor_config_path"]),
        "v3 scientific authority",
    )
    return predecessor._formal_snapshot(predecessor_config)


def _typed_tree(root: Path) -> dict[str, object]:
    root = _strict_path(root, must_exist=True, label="typed tree root")
    directories: list[str] = []
    files: dict[str, str] = {}

    def visit(directory: Path) -> None:
        with os.scandir(directory) as raw_entries:
            entries = sorted(raw_entries, key=lambda item: item.name)
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            if _is_link_or_reparse(path):
                raise ValueError(f"typed tree contains junction/symlink/reparse: {relative}")
            metadata = entry.stat(follow_symlinks=False)
            if stat.S_ISDIR(metadata.st_mode):
                directories.append(relative)
                visit(path)
            elif stat.S_ISREG(metadata.st_mode):
                if relative == "SHA256SUMS.json":
                    continue
                if path.name == "SHA256SUMS.json":
                    raise ValueError("typed tree contains nested manifest")
                files[relative] = _sha256(path)
            else:
                raise ValueError(f"typed tree contains nonordinary member: {relative}")
    visit(root)
    return {
        "schema": TREE_SCHEMA,
        "directories": sorted(directories),
        "files": dict(sorted(files.items())),
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


def _query_process_identity(pid: int) -> dict[str, object]:
    return predecessor._query_process_identity(pid)


def _sanitized_environment(
    source: Mapping[str, str] | None = None,
) -> dict[str, str]:
    return predecessor._sanitized_environment(source)


def _require_anonymous_pipe(descriptor: int, label: str, *, writable: bool) -> None:
    if isinstance(descriptor, bool) or not isinstance(descriptor, int) or descriptor < 0:
        raise ValueError(f"{label} descriptor is invalid")
    if os.name == "nt":
        import msvcrt

        handle = msvcrt.get_osfhandle(descriptor)
        if ctypes.windll.kernel32.GetFileType(handle) != 3:  # type: ignore[attr-defined]
            raise ValueError(f"{label} is not an anonymous pipe")
        transferred = ctypes.c_ulong(0)
        if writable:
            ok = ctypes.windll.kernel32.WriteFile(  # type: ignore[attr-defined]
                handle, None, 0, ctypes.byref(transferred), None
            )
        else:
            available = ctypes.c_ulong(0)
            ok = ctypes.windll.kernel32.PeekNamedPipe(  # type: ignore[attr-defined]
                handle, None, 0, None, ctypes.byref(available), None
            )
        if not ok:
            direction = "writable" if writable else "readable"
            raise ValueError(f"{label} has wrong direction; expected {direction}")
    else:
        if not stat.S_ISFIFO(os.fstat(descriptor).st_mode):
            raise ValueError(f"{label} is not an anonymous pipe")
        import fcntl

        access = fcntl.fcntl(descriptor, fcntl.F_GETFL) & os.O_ACCMODE
        expected = os.O_WRONLY if writable else os.O_RDONLY
        if access != expected:
            direction = "writable" if writable else "readable"
            raise ValueError(f"{label} has wrong direction; expected {direction}")


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise OSError("pipe write ended early")
        offset += written


def _write_frame(descriptor: int, payload: Mapping[str, Any]) -> None:
    body = _canonical_bytes(dict(payload))
    if len(body) <= 0 or len(body) > MAX_FRAME_BYTES:
        raise ValueError("capability frame size is invalid")
    _write_all(descriptor, len(body).to_bytes(8, "big") + body)


def _read_exact(descriptor: int, length: int) -> bytes:
    result = bytearray()
    while len(result) < length:
        chunk = os.read(descriptor, length - len(result))
        if not chunk:
            raise EOFError("pipe frame ended early")
        result.extend(chunk)
    return bytes(result)


def _read_frame(descriptor: int, label: str) -> dict[str, Any]:
    length = int.from_bytes(_read_exact(descriptor, 8), "big")
    if length <= 0 or length > MAX_FRAME_BYTES:
        raise ValueError(f"{label} frame length invalid")
    return recovery._mapping(
        json.loads(_read_exact(descriptor, length).decode("utf-8")), label
    )


def _call_with_timeout(call: Callable[[], Any], timeout: float, label: str) -> Any:
    if timeout <= 0:
        raise TimeoutError(f"{label} deadline expired")
    responses: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)

    def invoke() -> None:
        try:
            responses.put((True, call()))
        except Exception as error:  # noqa: BLE001 - propagate across deadline thread
            responses.put((False, error))

    thread = threading.Thread(target=invoke, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError(f"{label} timed out")
    ok, value = responses.get_nowait()
    if not ok:
        raise value
    return value


def _read_frame_with_deadline(
    descriptor: int, timeout: float, label: str
) -> dict[str, Any]:
    return _call_with_timeout(lambda: _read_frame(descriptor, label), timeout, label)


def _write_frame_with_deadline(
    descriptor: int, payload: Mapping[str, Any], timeout: float, label: str
) -> None:
    _call_with_timeout(lambda: _write_frame(descriptor, payload), timeout, label)


def _require_bounded_eof(descriptor: int, timeout: float) -> None:
    trailing = _call_with_timeout(
        lambda: os.read(descriptor, 1), timeout, "capability EOF verification"
    )
    if trailing != b"":
        raise ValueError("capability replay or trailing byte detected before ACK")


def _remaining(deadline: float, label: str) -> float:
    value = deadline - time.monotonic()
    if value <= 0:
        raise TimeoutError(f"{label} exceeded watchdog")
    return value


def _immutable_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(json.loads(json.dumps(dict(payload), sort_keys=True)))


@dataclasses.dataclass(frozen=True)
class AcceptedEvidence:
    block_id: str
    execution_index: int
    nonce: str
    envelope_bytes: bytes
    envelope_sha256: str
    ack_bytes: bytes
    ack_sha256: str
    popen_pid: int
    worker_creation_identity_bytes: bytes
    source_payload_path: Path
    source_payload_sha256: str
    source_attempt_receipt_path: Path
    source_attempt_receipt_sha256: str
    scientific_payload_sha256: str
    predecessor_accepted_evidence_digest: str | None
    accepted_evidence_digest: str

    @property
    def worker_creation_identity(self) -> Mapping[str, Any]:
        return _immutable_mapping(json.loads(self.worker_creation_identity_bytes))

    @property
    def envelope(self) -> Mapping[str, Any]:
        return _immutable_mapping(json.loads(self.envelope_bytes))

    @property
    def ack(self) -> Mapping[str, Any]:
        return _immutable_mapping(json.loads(self.ack_bytes))


def _accepted_digest_payload(evidence: AcceptedEvidence) -> dict[str, object]:
    return {
        "block_id": evidence.block_id,
        "execution_index": evidence.execution_index,
        "nonce": evidence.nonce,
        "envelope_sha256": evidence.envelope_sha256,
        "ack_sha256": evidence.ack_sha256,
        "popen_pid": evidence.popen_pid,
        "worker_creation_identity_sha256": _sha256_bytes(
            evidence.worker_creation_identity_bytes
        ),
        "source_payload_sha256": evidence.source_payload_sha256,
        "source_attempt_receipt_sha256": evidence.source_attempt_receipt_sha256,
        "scientific_payload_sha256": evidence.scientific_payload_sha256,
        "predecessor_accepted_evidence_digest": (
            evidence.predecessor_accepted_evidence_digest
        ),
    }


def _expected_accepted_digest(evidence: AcceptedEvidence) -> str:
    return _canonical_sha256(_accepted_digest_payload(evidence))


def _predecessor_binding(evidence: AcceptedEvidence) -> dict[str, object]:
    return {
        "block_id": evidence.block_id,
        "execution_index": evidence.execution_index,
        "accepted_evidence_digest": evidence.accepted_evidence_digest,
        "source_payload_sha256": evidence.source_payload_sha256,
        "source_attempt_receipt_sha256": evidence.source_attempt_receipt_sha256,
        "scientific_payload_sha256": evidence.scientific_payload_sha256,
        "ack_sha256": evidence.ack_sha256,
    }


class ControllerLedger:
    def __init__(self, records: Sequence[AcceptedEvidence] = ()) -> None:
        self._records = list(records)

    @property
    def records(self) -> tuple[AcceptedEvidence, ...]:
        return tuple(self._records)

    @property
    def digest(self) -> str:
        return _canonical_sha256(
            [_accepted_digest_payload(record) for record in self._records]
        )

    def predecessor_for(self, execution_index: int) -> dict[str, object] | None:
        if execution_index == 1:
            if self._records:
                raise ValueError("0008 index 1 requires an empty predecessor ledger")
            return None
        if execution_index == 2:
            if len(self._records) != 1:
                raise ValueError("0009 index 2 requires accepted 0008 predecessor evidence")
            return _predecessor_binding(self._records[0])
        raise ValueError("unregistered execution index")

    def accept(self, evidence: AcceptedEvidence) -> None:
        expected_index = len(self._records) + 1
        if expected_index > len(BLOCKS):
            raise ValueError("ledger rejects extra or replay evidence")
        if (
            evidence.execution_index != expected_index
            or evidence.block_id != BLOCKS[expected_index - 1]
            or evidence.accepted_evidence_digest != _expected_accepted_digest(evidence)
        ):
            raise ValueError("ledger block/index/digest replay drifted")
        expected_predecessor = (
            None if expected_index == 1 else self._records[0].accepted_evidence_digest
        )
        if evidence.predecessor_accepted_evidence_digest != expected_predecessor:
            raise ValueError("ledger predecessor accepted-evidence digest drifted")
        if any(
            record.nonce == evidence.nonce
            or record.envelope_sha256 == evidence.envelope_sha256
            for record in self._records
        ):
            raise ValueError("ledger replay detected")
        self._records.append(evidence)


def _block_input_sha256(block_id: str) -> str:
    context = _stage_context()
    return recovery._block_input_sha256(context["blocks"][block_id])


def _build_capability_envelope(
    config: Mapping[str, Any],
    *,
    ledger: ControllerLedger,
    block_id: str,
    execution_index: int,
    parent_identity: Mapping[str, Any],
    worker_identity: Mapping[str, Any],
    payload_path: Path,
    attempt_receipt_path: Path,
    read_handle: int,
    ack_handle: int,
    environment: Mapping[str, str],
    nonce: str | None = None,
) -> dict[str, object]:
    if execution_index not in {1, 2} or block_id != BLOCKS[execution_index - 1]:
        raise ValueError("block and execution index are inconsistent")
    predecessor_binding = ledger.predecessor_for(execution_index)
    context = _stage_context()
    python = Path(str(worker_identity["executable_path"]))
    return {
        "schema": ENVELOPE_SCHEMA,
        "authority": _candidate_authority(),
        "nonce": nonce or secrets.token_hex(32),
        "issued_ns": time.time_ns(),
        "block_id": block_id,
        "execution_index": execution_index,
        "predecessor_accepted_evidence": predecessor_binding,
        "ledger_digest_before": ledger.digest,
        "parent_process_identity": dict(parent_identity),
        "worker_process_identity": dict(worker_identity),
        "parent_command": _expected_controller_command(python),
        "worker_command": _expected_worker_command(
            python, read_handle=read_handle, ack_handle=ack_handle
        ),
        "read_handle": read_handle,
        "ack_handle": ack_handle,
        "working_directory": str(ROOT),
        "sanitized_environment": dict(environment),
        "sanitized_environment_sha256": _canonical_sha256(dict(environment)),
        "block_input_sha256": _block_input_sha256(block_id),
        "stage": recovery.STAGE,
        "stage_base_provenance_sha256": context["stage_base_sha256"],
        "scientific_config_path": str(BASE_CONFIG),
        "scientific_config_sha256": _sha256(BASE_CONFIG),
        "solver": recovery._solver_binding(context["config"]),
        "execution_host": predecessor.execution_host_status(
            context["config"]["execution"]
        ),
        "worker_payload_path": str(payload_path),
        "attempt_receipt_path": str(attempt_receipt_path),
    }


def _validate_attempt_paths(
    envelope: Mapping[str, Any], config: Mapping[str, Any]
) -> tuple[Path, Path]:
    block_id = str(envelope.get("block_id"))
    nonce = str(envelope.get("nonce"))
    worker_root = _pilot_roots(config)["worker"]
    expected_directory = worker_root / block_id / nonce
    expected_payload = expected_directory / "payload.json"
    expected_receipt = expected_directory / "attempt_receipt.json"
    payload = _strict_path(
        Path(str(envelope.get("worker_payload_path"))),
        must_exist=False,
        label="worker payload path",
    )
    receipt = _strict_path(
        Path(str(envelope.get("attempt_receipt_path"))),
        must_exist=False,
        label="attempt receipt path",
    )
    if payload != expected_payload or receipt != expected_receipt:
        raise ValueError("canonical attempt path drifted")
    return payload, receipt


def _validate_capability_envelope(
    envelope: Mapping[str, Any],
    *,
    config: Mapping[str, Any],
    ledger: ControllerLedger | None,
    read_handle: int,
    ack_handle: int,
) -> dict[str, Any]:
    expected_keys = {
        "schema",
        "authority",
        "nonce",
        "issued_ns",
        "block_id",
        "execution_index",
        "predecessor_accepted_evidence",
        "ledger_digest_before",
        "parent_process_identity",
        "worker_process_identity",
        "parent_command",
        "worker_command",
        "read_handle",
        "ack_handle",
        "working_directory",
        "sanitized_environment",
        "sanitized_environment_sha256",
        "block_input_sha256",
        "stage",
        "stage_base_provenance_sha256",
        "scientific_config_path",
        "scientific_config_sha256",
        "solver",
        "execution_host",
        "worker_payload_path",
        "attempt_receipt_path",
    }
    if (
        set(envelope) != expected_keys
        or envelope.get("schema") != ENVELOPE_SCHEMA
        or envelope.get("authority") != _candidate_authority()
    ):
        raise ValueError("capability schema or authority drifted")
    nonce = envelope.get("nonce")
    if (
        not isinstance(nonce, str)
        or len(nonce) != 64
        or any(character not in "0123456789abcdef" for character in nonce)
    ):
        raise ValueError("capability nonce malformed")
    execution_index = envelope.get("execution_index")
    block_id = envelope.get("block_id")
    if (
        isinstance(execution_index, bool)
        or not isinstance(execution_index, int)
        or execution_index not in {1, 2}
        or block_id != BLOCKS[execution_index - 1]
    ):
        raise ValueError("capability block/execution index drifted")
    issued_ns = envelope.get("issued_ns")
    if isinstance(issued_ns, bool) or not isinstance(issued_ns, int) or issued_ns <= 0:
        raise TypeError("capability issued_ns must be a positive integer")
    if ledger is not None:
        expected_predecessor = ledger.predecessor_for(execution_index)
        if (
            envelope.get("predecessor_accepted_evidence") != expected_predecessor
            or envelope.get("ledger_digest_before") != ledger.digest
        ):
            raise ValueError("capability immutable predecessor ledger drifted")
    elif execution_index == 1:
        if (
            envelope.get("predecessor_accepted_evidence") is not None
            or envelope.get("ledger_digest_before")
            != _canonical_sha256([])
        ):
            raise ValueError("0008 capability must have no predecessor evidence")
    else:
        predecessor_binding = recovery._mapping(
            envelope.get("predecessor_accepted_evidence"),
            "0009 predecessor accepted evidence",
        )
        expected_predecessor_keys = {
            "block_id",
            "execution_index",
            "accepted_evidence_digest",
            "source_payload_sha256",
            "source_attempt_receipt_sha256",
            "scientific_payload_sha256",
            "ack_sha256",
        }
        if (
            set(predecessor_binding) != expected_predecessor_keys
            or predecessor_binding.get("block_id") != BLOCKS[0]
            or predecessor_binding.get("execution_index") != 1
            or any(
                not recovery._is_sha256(predecessor_binding.get(key))
                for key in expected_predecessor_keys - {"block_id", "execution_index"}
            )
            or not recovery._is_sha256(envelope.get("ledger_digest_before"))
        ):
            raise ValueError("0009 predecessor evidence structure drifted")
    worker = recovery._mapping(envelope.get("worker_process_identity"), "worker identity")
    parent = recovery._mapping(envelope.get("parent_process_identity"), "parent identity")
    if worker != _query_process_identity(os.getpid()) or parent != _query_process_identity(
        os.getppid()
    ):
        raise ValueError("capability process identity drifted")
    python = Path(str(worker["executable_path"]))
    if (
        envelope.get("worker_command")
        != _expected_worker_command(python, read_handle=read_handle, ack_handle=ack_handle)
        or envelope.get("parent_command") != _expected_controller_command(python)
        or worker.get("command") != envelope.get("worker_command")
        or parent.get("command") != envelope.get("parent_command")
        or envelope.get("read_handle") != read_handle
        or envelope.get("ack_handle") != ack_handle
    ):
        raise ValueError("capability command/handle binding drifted")
    environment = _sanitized_environment()
    context = _stage_context()
    if (
        envelope.get("working_directory") != str(ROOT)
        or Path.cwd().resolve() != ROOT
        or envelope.get("sanitized_environment") != environment
        or envelope.get("sanitized_environment_sha256")
        != _canonical_sha256(environment)
        or envelope.get("block_input_sha256") != _block_input_sha256(str(block_id))
        or envelope.get("stage") != recovery.STAGE
        or envelope.get("stage_base_provenance_sha256") != context["stage_base_sha256"]
        or envelope.get("scientific_config_sha256") != _sha256(BASE_CONFIG)
        or envelope.get("solver") != recovery._solver_binding(context["config"])
        or envelope.get("execution_host")
        != predecessor.execution_host_status(context["config"]["execution"])
    ):
        raise ValueError("capability environment/scientific authority drifted")
    scientific_path = _strict_path(
        Path(str(envelope.get("scientific_config_path"))),
        must_exist=True,
        label="scientific config",
    )
    if scientific_path != BASE_CONFIG:
        raise ValueError("scientific config path drifted")
    _validate_attempt_paths(envelope, config)
    return context


def _build_ack(envelope: Mapping[str, Any]) -> dict[str, object]:
    return {
        "schema": ACK_SCHEMA,
        "capability_envelope_sha256": _canonical_sha256(dict(envelope)),
        "nonce": envelope["nonce"],
        "block_id": envelope["block_id"],
        "execution_index": envelope["execution_index"],
        "worker_process_identity": envelope["worker_process_identity"],
        "bounded_eof_verified_before_ack": True,
        "accepted_once": True,
    }


def _build_hello(worker_identity: Mapping[str, Any]) -> dict[str, object]:
    return {
        "schema": HELLO_SCHEMA,
        "worker_process_identity": dict(worker_identity),
        "candidate_v4_authority": _candidate_authority(),
    }


def _build_worker_result(
    envelope: Mapping[str, Any], scientific_payload: Mapping[str, Any]
) -> dict[str, object]:
    return {
        "schema": RESULT_SCHEMA,
        "status": (
            "complete"
            if scientific_payload.get("all_hours_resolved") is True
            else "unresolved"
        ),
        "authority": envelope["authority"],
        "capability_envelope_sha256": _canonical_sha256(dict(envelope)),
        "block_id": envelope["block_id"],
        "execution_index": envelope["execution_index"],
        "predecessor_accepted_evidence": envelope[
            "predecessor_accepted_evidence"
        ],
        "nonce": envelope["nonce"],
        "parent_process_identity": envelope["parent_process_identity"],
        "worker_process_identity": envelope["worker_process_identity"],
        "scientific_payload": dict(scientific_payload),
        "scientific_payload_sha256": _canonical_sha256(dict(scientific_payload)),
        "all_hours_resolved": scientific_payload.get("all_hours_resolved") is True,
        "mathematical_infeasibility_inferred_from_failure": False,
    }


def _build_attempt_receipt(
    envelope: Mapping[str, Any], payload_path: Path
) -> dict[str, object]:
    result = recovery._mapping(_load_json(payload_path, "worker result"), "worker result")
    return {
        "schema": ATTEMPT_RECEIPT_SCHEMA,
        "authority": envelope["authority"],
        "capability_envelope_sha256": _canonical_sha256(dict(envelope)),
        "block_id": envelope["block_id"],
        "execution_index": envelope["execution_index"],
        "nonce": envelope["nonce"],
        "worker_payload_sha256": _sha256(payload_path),
        "scientific_payload_sha256": result["scientific_payload_sha256"],
        "attempt_complete": result.get("all_hours_resolved") is True,
        "controller_validation_passed": False,
        "published": False,
        "mathematical_infeasibility_inferred_from_failure": False,
    }


def _load_worker_data(context: Mapping[str, Any]) -> Any:
    return predecessor._load_worker_data(context)


def _worker_from_capability(
    read_descriptor: int,
    ack_descriptor: int,
    *,
    read_handle: int | None = None,
    ack_handle: int | None = None,
    ledger: ControllerLedger | None = None,
    handshake_timeout_seconds: float | None = None,
) -> int:
    config = _require_execution_authority()
    _require_anonymous_pipe(
        read_descriptor, "controller-to-worker capability", writable=False
    )
    _require_anonymous_pipe(
        ack_descriptor, "worker-to-controller acknowledgement", writable=True
    )
    read_authority = read_descriptor if read_handle is None else read_handle
    ack_authority = ack_descriptor if ack_handle is None else ack_handle
    timeout = (
        float(config["pilot"]["external_watchdog_seconds"])
        if handshake_timeout_seconds is None
        else handshake_timeout_seconds
    )
    deadline = time.monotonic() + timeout
    worker_identity = _query_process_identity(os.getpid())
    _write_frame_with_deadline(
        ack_descriptor,
        _build_hello(worker_identity),
        _remaining(deadline, "worker hello"),
        "worker hello",
    )
    envelope = _read_frame_with_deadline(
        read_descriptor, _remaining(deadline, "capability frame"), "capability frame"
    )
    _require_bounded_eof(
        read_descriptor, _remaining(deadline, "capability bounded EOF")
    )
    context = _validate_capability_envelope(
        envelope,
        config=config,
        ledger=ledger,
        read_handle=read_authority,
        ack_handle=ack_authority,
    )
    ack = _build_ack(envelope)
    _write_frame_with_deadline(
        ack_descriptor,
        ack,
        _remaining(deadline, "capability ACK"),
        "capability ACK",
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
    payload_path, receipt_path = _validate_attempt_paths(envelope, config)
    payload_path.parent.mkdir(parents=True, exist_ok=False)
    recovery._atomic_json(payload_path, _build_worker_result(envelope, payload))
    recovery._atomic_json(
        receipt_path, _build_attempt_receipt(envelope, payload_path)
    )
    return 0 if payload.get("all_hours_resolved") is True else 3


def _validate_worker_result(
    payload_path: Path,
    receipt_path: Path,
    *,
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    payload_path = _strict_path(payload_path, must_exist=True, label="source payload")
    receipt_path = _strict_path(receipt_path, must_exist=True, label="source attempt receipt")
    result = recovery._mapping(_load_json(payload_path, "worker result"), "worker result")
    receipt = recovery._mapping(
        _load_json(receipt_path, "attempt receipt"), "attempt receipt"
    )
    if (
        result.get("schema") != RESULT_SCHEMA
        or result.get("status") != "complete"
        or result.get("authority") != envelope.get("authority")
        or result.get("capability_envelope_sha256")
        != _canonical_sha256(dict(envelope))
        or result.get("block_id") != envelope.get("block_id")
        or result.get("execution_index") != envelope.get("execution_index")
        or result.get("predecessor_accepted_evidence")
        != envelope.get("predecessor_accepted_evidence")
        or result.get("nonce") != envelope.get("nonce")
        or result.get("all_hours_resolved") is not True
        or result.get("mathematical_infeasibility_inferred_from_failure") is not False
    ):
        raise ValueError("worker result/envelope authority drifted")
    context = _stage_context()
    block_id = str(envelope["block_id"])
    scientific = recovery._validate_scientific_payload(
        recovery._mapping(result.get("scientific_payload"), "scientific payload"),
        block_id=block_id,
        expected_block=context["blocks"][block_id],
        config=context["config"],
    )
    predecessor._normalize_payload_raw_evidence(scientific, "highs")
    if result.get("scientific_payload_sha256") != _canonical_sha256(scientific):
        raise ValueError("scientific payload canonical hash drifted")
    expected_receipt = _build_attempt_receipt(envelope, payload_path)
    if receipt != expected_receipt:
        raise ValueError("attempt receipt/source payload drifted")
    if (
        receipt.get("controller_validation_passed") is not False
        or receipt.get("published") is not False
        or "published_by_controller" in receipt
    ):
        raise ValueError("attempt receipt contains premature success claim")
    return scientific


def _accept_worker_attempt(
    *,
    envelope: Mapping[str, Any],
    ack: Mapping[str, Any],
    payload_path: Path,
    attempt_receipt_path: Path,
    popen_identity: Mapping[str, Any],
    ledger: ControllerLedger,
) -> AcceptedEvidence:
    config = _load_config()
    execution_index = int(envelope["execution_index"])
    expected_predecessor = ledger.predecessor_for(execution_index)
    if (
        envelope.get("predecessor_accepted_evidence") != expected_predecessor
        or envelope.get("ledger_digest_before") != ledger.digest
    ):
        raise ValueError("attempt predecessor ledger drifted")
    if dict(ack) != _build_ack(envelope):
        raise ValueError("pipe ACK is missing or drifted")
    if dict(popen_identity) != envelope.get("worker_process_identity"):
        raise ValueError("Popen PID/create-time differs from worker evidence")
    _validate_attempt_paths(envelope, config)
    scientific = _validate_worker_result(
        payload_path, attempt_receipt_path, envelope=envelope
    )
    envelope_bytes = _canonical_bytes(dict(envelope))
    ack_bytes = _canonical_bytes(dict(ack))
    identity_bytes = _canonical_bytes(dict(popen_identity))
    provisional = AcceptedEvidence(
        block_id=str(envelope["block_id"]),
        execution_index=execution_index,
        nonce=str(envelope["nonce"]),
        envelope_bytes=envelope_bytes,
        envelope_sha256=_sha256_bytes(envelope_bytes),
        ack_bytes=ack_bytes,
        ack_sha256=_sha256_bytes(ack_bytes),
        popen_pid=int(popen_identity["pid"]),
        worker_creation_identity_bytes=identity_bytes,
        source_payload_path=payload_path,
        source_payload_sha256=_sha256(payload_path),
        source_attempt_receipt_path=attempt_receipt_path,
        source_attempt_receipt_sha256=_sha256(attempt_receipt_path),
        scientific_payload_sha256=_canonical_sha256(scientific),
        predecessor_accepted_evidence_digest=(
            None
            if expected_predecessor is None
            else str(expected_predecessor["accepted_evidence_digest"])
        ),
        accepted_evidence_digest="",
    )
    return dataclasses.replace(
        provisional, accepted_evidence_digest=_expected_accepted_digest(provisional)
    )


def _validation_receipt(evidence: AcceptedEvidence) -> dict[str, object]:
    return {
        "schema": VALIDATION_RECEIPT_SCHEMA,
        "block_id": evidence.block_id,
        "execution_index": evidence.execution_index,
        "accepted_evidence_digest": evidence.accepted_evidence_digest,
        "controller_validation_passed": True,
        "published": False,
        "mathematical_infeasibility_inferred_from_failure": False,
    }


def _revalidate_memory_evidence(
    evidence: AcceptedEvidence,
    *,
    payload_path: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    if evidence.accepted_evidence_digest != _expected_accepted_digest(evidence):
        raise ValueError("accepted evidence digest drifted")
    if not evidence.ack_bytes or evidence.ack_sha256 != _sha256_bytes(
        evidence.ack_bytes
    ):
        raise ValueError("accepted ACK bytes/hash drifted")
    envelope = recovery._mapping(json.loads(evidence.envelope_bytes), "accepted envelope")
    ack = recovery._mapping(json.loads(evidence.ack_bytes), "accepted ACK")
    if (
        evidence.envelope_sha256 != _sha256_bytes(evidence.envelope_bytes)
        or ack != _build_ack(envelope)
        or evidence.popen_pid != evidence.worker_creation_identity.get("pid")
        or evidence.source_payload_sha256 != _sha256(evidence.source_payload_path)
        or evidence.source_attempt_receipt_sha256
        != _sha256(evidence.source_attempt_receipt_path)
        or evidence.source_payload_sha256 != _sha256(payload_path)
        or evidence.source_attempt_receipt_sha256 != _sha256(receipt_path)
    ):
        raise ValueError("source/memory/ACK accepted evidence mismatch")
    scientific = _validate_worker_result(
        payload_path, receipt_path, envelope=envelope
    )
    if evidence.scientific_payload_sha256 != _canonical_sha256(scientific):
        raise ValueError("accepted scientific payload digest drifted")
    return scientific


def _build_controller_receipt(
    config: Mapping[str, Any], ledger: ControllerLedger
) -> dict[str, object]:
    if len(ledger.records) != 2:
        raise ValueError("controller receipt requires two accepted blocks")
    return {
        "schema": CONTROLLER_SCHEMA,
        "status": "controller_validated_attempts_not_published",
        "authority": _candidate_authority(),
        "blocks": list(BLOCKS),
        "accepted_evidence_digests": [
            record.accepted_evidence_digest for record in ledger.records
        ],
        "ledger_digest": ledger.digest,
        "formal_snapshot_before": _formal_snapshot(config),
        "parent_solver_calls": 0,
        "published": False,
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
        *(
            f"workers/{block_id}/{name}"
            for block_id in BLOCKS
            for name in (
                "payload.json",
                "attempt_receipt.json",
                "validation_receipt.json",
            )
        ),
    }
    return directories, files


def _publish_result(
    staging: Path,
    target: Path,
    success_seal: Path,
    *,
    config: Mapping[str, Any],
    controller: Mapping[str, Any],
    ledger: ControllerLedger,
    pre_rename_test_hook: Callable[[Path], None] | None = None,
) -> dict[str, object]:
    if target.exists() or success_seal.exists():
        raise FileExistsError("result target or success seal already exists")
    if staging.exists():
        raise FileExistsError("publication staging already exists")
    if len(ledger.records) != 2 or [record.block_id for record in ledger.records] != BLOCKS:
        raise ValueError("publication requires exact ordered accepted-evidence ledger")
    staging.mkdir(parents=True, exist_ok=False)
    renamed = False
    try:
        if controller != _build_controller_receipt(config, ledger):
            raise ValueError("controller receipt/ledger drifted")
        payloads: dict[str, dict[str, Any]] = {}
        worker_root = staging / "workers"
        worker_root.mkdir()
        for evidence in ledger.records:
            source_scientific = _revalidate_memory_evidence(
                evidence,
                payload_path=evidence.source_payload_path,
                receipt_path=evidence.source_attempt_receipt_path,
            )
            destination = worker_root / evidence.block_id
            destination.mkdir()
            copied_payload = destination / "payload.json"
            copied_receipt = destination / "attempt_receipt.json"
            shutil.copyfile(evidence.source_payload_path, copied_payload)
            shutil.copyfile(evidence.source_attempt_receipt_path, copied_receipt)
            payloads[evidence.block_id] = _revalidate_memory_evidence(
                evidence, payload_path=copied_payload, receipt_path=copied_receipt
            )
            if payloads[evidence.block_id] != source_scientific:
                raise ValueError("copied scientific payload differs from source memory")
            recovery._atomic_json(
                destination / "validation_receipt.json",
                _validation_receipt(evidence),
            )
        comparison = predecessor.compare_named_outage_0008(
            payloads[BLOCKS[0]], predecessor._extract_gurobi_payload()
        )
        if comparison.get("comparison_passed") is not True:
            raise ValueError("named-outage comparison failed or unresolved")
        summary = {
            "schema": "rq2_public_grid_two_block_pilot_result_v4",
            "status": "complete_nonformal_pilot",
            "blocks": list(BLOCKS),
            "ledger_digest": ledger.digest,
            "all_blocks_resolved": True,
            "named_outage_comparison_passed": True,
            "published": False,
            "parent_solver_calls": 0,
            "formal_execution_ready": False,
            "claim": False,
            "security_certified": False,
        }
        shutil.copyfile(CONFIG, staging / "config.yaml")
        recovery._atomic_json(staging / "controller_receipt.json", dict(controller))
        recovery._atomic_json(staging / "comparison.json", comparison)
        recovery._atomic_json(staging / "summary.json", summary)
        tree = _typed_tree(staging)
        expected_directories, expected_files = _expected_result_tree()
        if (
            set(tree["directories"]) != expected_directories
            or set(recovery._mapping(tree["files"], "tree files")) != expected_files
        ):
            raise ValueError("publication exact typed tree inventory drifted")
        recovery._atomic_json(staging / "SHA256SUMS.json", tree)
        if pre_rename_test_hook is not None:
            pre_rename_test_hook(staging)

        _verify_predecessor_authority()
        _inspect_v4_chain()
        observed_tree = recovery._mapping(
            _load_json(staging / "SHA256SUMS.json", "result manifest"),
            "result manifest",
        )
        if observed_tree != _typed_tree(staging):
            raise ValueError("final typed tree/manifest drifted")
        if (
            set(observed_tree["directories"]) != expected_directories
            or set(recovery._mapping(observed_tree["files"], "final files"))
            != expected_files
        ):
            raise ValueError("final result member inventory drifted")
        for evidence in ledger.records:
            destination = staging / "workers" / evidence.block_id
            _revalidate_memory_evidence(
                evidence,
                payload_path=destination / "payload.json",
                receipt_path=destination / "attempt_receipt.json",
            )
            validation = recovery._mapping(
                _load_json(destination / "validation_receipt.json", "validation receipt"),
                "validation receipt",
            )
            if validation != _validation_receipt(evidence) or validation.get(
                "published"
            ) is not False:
                raise ValueError("validation receipt contains publication drift")
        final_comparison = predecessor.compare_named_outage_0008(
            payloads[BLOCKS[0]], predecessor._extract_gurobi_payload()
        )
        if final_comparison != comparison:
            raise ValueError("final comparison drifted")
        if controller.get("formal_snapshot_before") != _formal_snapshot(config):
            raise ValueError("formal snapshot changed before publication")
        if target.exists() or success_seal.exists():
            raise FileExistsError("result target or success seal appeared before rename")
        staging.rename(target)
        renamed = True

        # Post-rename readback occurs before the only published=true evidence.
        final_manifest_path = target / "SHA256SUMS.json"
        final_manifest = recovery._mapping(
            _load_json(final_manifest_path, "post-rename manifest"),
            "post-rename manifest",
        )
        if final_manifest != _typed_tree(target):
            raise ValueError("post-rename result readback drifted")
        observed_summary = recovery._mapping(
            _load_json(target / "summary.json", "post-rename summary"),
            "post-rename summary",
        )
        if observed_summary != summary or observed_summary.get("published") is not False:
            raise ValueError("post-rename summary drifted")
        seal = {
            "schema": SUCCESS_SEAL_SCHEMA,
            "result_directory": str(target),
            "result_manifest_sha256": _sha256(final_manifest_path),
            "ledger_digest": ledger.digest,
            "published": True,
            "after_atomic_rename_readback_passed": True,
            "post_result_review_passed": False,
            "formal_execution_ready": False,
            "claim": False,
            "security_certified": False,
        }
        recovery._atomic_json(success_seal, seal)
        if recovery._mapping(_load_json(success_seal, "success seal"), "success seal") != seal:
            raise ValueError("post-rename success seal readback drifted")
        return summary
    except Exception:
        if not renamed:
            shutil.rmtree(staging, ignore_errors=True)
        raise


class DispatchFailure(RuntimeError):
    def __init__(self, message: str, *, child_pid: int, child_alive: bool) -> None:
        super().__init__(message)
        self.child_pid = child_pid
        self.child_alive = child_alive
        self.mathematical_infeasibility_inferred = False


def _terminate_process(process: subprocess.Popen[Any], timeout: float = 1.0) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("child survived terminate-wait-kill-wait cleanup") from error
    if process.poll() is None:
        raise RuntimeError("child remains live after bounded cleanup")


def _call_with_process_monitor(
    process: subprocess.Popen[Any],
    call: Callable[[], Any],
    *,
    deadline: float,
    process_contract: Mapping[str, Any],
    label: str,
) -> Any:
    responses: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)

    def invoke() -> None:
        try:
            responses.put((True, call()))
        except Exception as error:  # noqa: BLE001 - propagate across monitor thread
            responses.put((False, error))

    thread = threading.Thread(target=invoke, daemon=True)
    thread.start()
    interval = float(process_contract["resource_sample_interval_seconds"])
    while True:
        remaining = _remaining(deadline, label)
        try:
            ok, value = responses.get(timeout=min(interval, remaining, 0.25))
        except queue.Empty:
            if process.poll() is not None:
                raise RuntimeError(f"{label} ended because worker exited early")
            sample = recovery._resource_probe(process.pid)
            reason = recovery._resource_stop_reason(sample, process_contract)
            if reason is not None:
                raise RuntimeError(f"{label} resource stop: {reason}")
            continue
        if not ok:
            raise value
        return value


def _wait_process_monitored(
    process: subprocess.Popen[Any],
    *,
    deadline: float,
    process_contract: Mapping[str, Any],
) -> dict[str, object]:
    interval = float(process_contract["resource_sample_interval_seconds"])
    samples = 0
    while process.poll() is None:
        remaining = _remaining(deadline, "worker completion")
        try:
            process.wait(timeout=min(interval, remaining, 0.25))
        except subprocess.TimeoutExpired:
            sample = recovery._resource_probe(process.pid)
            samples += 1
            reason = recovery._resource_stop_reason(sample, process_contract)
            if reason is not None:
                return {
                    "status": "resource_stop",
                    "reason": reason,
                    "exit_code": process.poll(),
                    "resource_sample_count": samples,
                    "mathematical_infeasibility_inferred": False,
                }
    return {
        "status": "exited",
        "reason": None,
        "exit_code": process.returncode,
        "resource_sample_count": samples,
        "mathematical_infeasibility_inferred": False,
    }


def _dispatch_one(
    config: Mapping[str, Any],
    *,
    block_id: str,
    execution_index: int,
    roots: Mapping[str, Path],
    ledger: ControllerLedger,
) -> AcceptedEvidence:
    """Future controller path; unreachable while the v4 candidate is closed."""

    _require_execution_authority()
    if block_id != BLOCKS[execution_index - 1]:
        raise ValueError("dispatch block/execution index drifted")
    ledger.predecessor_for(execution_index)
    python = _strict_path(Path(sys.executable), must_exist=True, label="worker Python")
    parent = _query_process_identity(os.getpid())
    if parent.get("command") != _expected_controller_command(python):
        raise ValueError("controller exact command drifted")
    log_root = _strict_path(roots["log"], must_exist=True, label="pilot log root")
    worker_root = _strict_path(
        roots["worker"], must_exist=True, label="pilot worker root"
    )
    nonce = secrets.token_hex(32)
    payload_path = worker_root / block_id / nonce / "payload.json"
    receipt_path = worker_root / block_id / nonce / "attempt_receipt.json"
    stdout_path = log_root / f"{execution_index:02d}_{block_id}_{nonce}.stdout.log"
    stderr_path = log_root / f"{execution_index:02d}_{block_id}_{nonce}.stderr.log"
    request_read, request_write = os.pipe()
    ack_read, ack_write = os.pipe()
    child_read = request_read
    child_ack = ack_write
    if os.name == "nt":
        import msvcrt

        child_read = msvcrt.get_osfhandle(request_read)
        child_ack = msvcrt.get_osfhandle(ack_write)
    os.set_inheritable(request_read, True)
    os.set_inheritable(ack_write, True)
    command = _expected_worker_command(
        python, read_handle=child_read, ack_handle=child_ack
    )
    environment = _sanitized_environment()
    popen_kwargs: dict[str, object] = {
        "cwd": ROOT,
        "env": environment,
        "stdin": subprocess.DEVNULL,
        "text": False,
    }
    if os.name == "nt":
        popen_kwargs.update(_windows_popen_kwargs(child_read, child_ack))
    else:
        popen_kwargs.update({"pass_fds": (request_read, ack_write), "close_fds": True})
    process: subprocess.Popen[Any] | None = None
    process_contract = recovery._mapping(config.get("pilot"), "pilot process contract")
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        try:
            process = subprocess.Popen(
                command, stdout=stdout, stderr=stderr, **popen_kwargs
            )
            os.close(request_read)
            request_read = -1
            os.close(ack_write)
            ack_write = -1
            deadline = time.monotonic() + float(
                process_contract["external_watchdog_seconds"]
            )
            worker = _query_process_identity(process.pid)
            hello = _call_with_process_monitor(
                process,
                lambda: _read_frame(ack_read, "worker hello"),
                deadline=deadline,
                process_contract=process_contract,
                label="worker hello",
            )
            if hello != _build_hello(worker):
                raise ValueError("worker hello/PID/create-time authority drifted")
            envelope = _build_capability_envelope(
                config,
                ledger=ledger,
                block_id=block_id,
                execution_index=execution_index,
                parent_identity=parent,
                worker_identity=worker,
                payload_path=payload_path,
                attempt_receipt_path=receipt_path,
                read_handle=child_read,
                ack_handle=child_ack,
                environment=environment,
                nonce=nonce,
            )
            _call_with_process_monitor(
                process,
                lambda: _write_frame(request_write, envelope),
                deadline=deadline,
                process_contract=process_contract,
                label="capability frame",
            )
            os.close(request_write)
            request_write = -1
            ack = _call_with_process_monitor(
                process,
                lambda: _read_frame(ack_read, "capability ACK"),
                deadline=deadline,
                process_contract=process_contract,
                label="capability ACK",
            )
            wait = _wait_process_monitored(
                process, deadline=deadline, process_contract=process_contract
            )
            if wait["status"] != "exited" or wait["exit_code"] != 0:
                raise RuntimeError(
                    f"pilot worker ended {wait['status']}; unresolved, not infeasible"
                )
            evidence = _accept_worker_attempt(
                envelope=envelope,
                ack=recovery._mapping(ack, "capability ACK"),
                payload_path=payload_path,
                attempt_receipt_path=receipt_path,
                popen_identity=worker,
                ledger=ledger,
            )
            ledger.accept(evidence)
            return evidence
        except Exception as error:
            if process is not None:
                _terminate_process(process)
                child_pid = process.pid
                child_alive = process.poll() is None
            else:
                child_pid = -1
                child_alive = False
            raise DispatchFailure(
                f"pilot dispatch incomplete: {error}",
                child_pid=child_pid,
                child_alive=child_alive,
            ) from error
        finally:
            for descriptor in (request_read, request_write, ack_read, ack_write):
                if descriptor >= 0:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass


_SYNTHETIC_CHILD = r"""
import json,os,sys,time
mode=sys.argv[1]; rh=int(sys.argv[2]); ah=int(sys.argv[3])
if os.name=='nt':
 import msvcrt
 r=msvcrt.open_osfhandle(rh,os.O_RDONLY); a=msvcrt.open_osfhandle(ah,os.O_WRONLY)
else: r=rh; a=ah
def exact(fd,n):
 out=b''
 while len(out)<n:
  c=os.read(fd,n-len(out))
  if not c: raise EOFError
  out+=c
 return out
def readf(fd):
 n=int.from_bytes(exact(fd,8),'big'); return json.loads(exact(fd,n))
def writef(fd,p):
 b=json.dumps(p,sort_keys=True,separators=(',',':')).encode(); os.write(fd,len(b).to_bytes(8,'big')+b)
if mode=='silent': time.sleep(60); sys.exit(9)
if mode=='flood':
 os.write(1,b'o'*131072); os.write(2,b'e'*131072)
writef(a,{'schema':'synthetic_dispatch_hello_v4','pid':os.getpid(),'ppid':os.getppid()})
env=readf(r); trailing=os.read(r,1)
writef(a,{'schema':'synthetic_dispatch_ack_v4','nonce':env.get('nonce'),'eof':trailing==b''})
sys.exit(0 if trailing==b'' else 8)
"""


def _windows_popen_kwargs(read_handle: int, ack_handle: int) -> dict[str, object]:
    startup = subprocess.STARTUPINFO()
    startup.lpAttributeList = {"handle_list": [read_handle, ack_handle]}
    return {"startupinfo": startup, "close_fds": True}


def _synthetic_dispatch_probe(
    directory: Path, *, mode: str, timeout_seconds: float
) -> dict[str, object]:
    if mode not in {"silent", "flood"}:
        raise ValueError("unregistered synthetic dispatch mode")
    directory.mkdir(parents=True, exist_ok=True)
    stdout_path = directory / "stdout.log"
    stderr_path = directory / "stderr.log"
    if stdout_path.exists() or stderr_path.exists():
        raise FileExistsError("synthetic probe logs must be fresh")
    request_read, request_write = os.pipe()
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
        _SYNTHETIC_CHILD,
        mode,
        str(child_read),
        str(child_ack),
    ]
    kwargs: dict[str, object] = {
        "cwd": ROOT,
        "env": _sanitized_environment(),
        "stdin": subprocess.DEVNULL,
        "text": False,
    }
    if os.name == "nt":
        kwargs.update(_windows_popen_kwargs(child_read, child_ack))
    else:
        kwargs.update({"pass_fds": (request_read, ack_write), "close_fds": True})
    with (
        stdout_path.open("xb") as stdout,
        stderr_path.open("xb") as stderr,
    ):
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr, **kwargs)
        os.close(request_read)
        os.close(ack_write)
        deadline = time.monotonic() + timeout_seconds
        process_contract = dict(_load_config()["pilot"])
        process_contract["external_watchdog_seconds"] = timeout_seconds
        process_contract["resource_sample_interval_seconds"] = min(
            0.05, timeout_seconds
        )
        try:
            hello = _call_with_process_monitor(
                process,
                lambda: _read_frame(ack_read, "synthetic hello"),
                deadline=deadline,
                process_contract=process_contract,
                label="synthetic hello",
            )
            if hello != {
                "schema": "synthetic_dispatch_hello_v4",
                "pid": process.pid,
                "ppid": os.getpid(),
            }:
                raise ValueError("synthetic hello drifted")
            envelope = {"schema": "synthetic_dispatch_envelope_v4", "nonce": "a" * 64}
            _call_with_process_monitor(
                process,
                lambda: _write_frame(request_write, envelope),
                deadline=deadline,
                process_contract=process_contract,
                label="synthetic frame",
            )
            os.close(request_write)
            request_write = -1
            ack = _call_with_process_monitor(
                process,
                lambda: _read_frame(ack_read, "synthetic ACK"),
                deadline=deadline,
                process_contract=process_contract,
                label="synthetic ACK",
            )
            if ack != {
                "schema": "synthetic_dispatch_ack_v4",
                "nonce": "a" * 64,
                "eof": True,
            }:
                raise ValueError("synthetic ACK drifted")
            wait = _wait_process_monitored(
                process, deadline=deadline, process_contract=process_contract
            )
            if wait["status"] != "exited" or wait["exit_code"] != 0:
                raise RuntimeError("synthetic child nonzero exit")
            return {
                "probe_passed": True,
                "child_pid": process.pid,
                "child_alive": False,
                "exclusive_ordinary_logs": True,
                "scientific_loader_calls": 0,
                "solver_calls": 0,
                "result_writes": 0,
                "formal_writes": 0,
            }
        except Exception as error:
            _terminate_process(process)
            raise DispatchFailure(
                f"synthetic dispatch incomplete: {error}",
                child_pid=process.pid,
                child_alive=process.poll() is None,
            ) from error
        finally:
            for descriptor in (request_write, ack_read):
                if descriptor >= 0:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass


def run(*, validate_only: bool = False) -> dict[str, object]:
    if validate_only:
        from experiments.validate_rq2_public_grid_two_block_pilot_candidate_v4 import (
            validate,
        )

        return validate()
    _require_execution_authority()
    raise RuntimeError("closed v4 candidate cannot run; execution successor required")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--internal-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--read-handle", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--ack-handle", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.internal_worker and (
        args.validate_only or args.read_handle is None or args.ack_handle is None
    ):
        parser.error("internal worker requires two inherited handles")
    if not args.internal_worker and (
        args.read_handle is not None or args.ack_handle is not None
    ):
        parser.error("handles require internal worker mode")
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

            read_descriptor = msvcrt.open_osfhandle(read_handle, os.O_RDONLY)
            ack_descriptor = msvcrt.open_osfhandle(ack_handle, os.O_WRONLY)
        raise SystemExit(
            _worker_from_capability(
                read_descriptor,
                ack_descriptor,
                read_handle=read_handle,
                ack_handle=ack_handle,
            )
        )
    print(json.dumps(run(validate_only=bool(args.validate_only)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
