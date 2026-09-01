"""Closed activation-v2 controller/worker transport and pre-loader probe.

The module owns its command, anonymous-pipe handshake, evidence, and in-memory
ledger contracts.  Its only runnable worker mode is a synthetic pre-loader
probe; production dispatch is deliberately absent pending a reviewed immutable
execution wrapper and a later dispatch-authorization receipt.
"""

from __future__ import annotations

import argparse
import base64
import ctypes
import dataclasses
import hashlib
import hmac
import json
import os
import queue
import secrets
import stat
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\CUHKSZ\Research Project\electricity-grid")
MODULE = "experiments.run_rq2_public_grid_two_block_pilot_activation_transport_v2"
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_activation_transport_v2.json"
V1_OUTER = ROOT / "configs/rq2_public_grid_two_block_pilot_activation_candidate_v1.OUTER.SHA256SUMS.json"
V1_REWORK = ROOT / "configs/rq2_public_grid_two_block_pilot_activation_review_rework_v1.json"
V1_OUTER_SHA256 = "844f4a59527306962e97e7879e4ccb7abb1893b65a819b782c56110e4df073f2"
BLOCKS = ("holdout_s20260822_0008", "holdout_s20260822_0009")
PRODUCTION_DISPATCH_PERMITTED = False

HELLO_SCHEMA = "rq2_public_grid_activation_transport_hello_v2"
ENVELOPE_SCHEMA = "rq2_public_grid_activation_transport_envelope_v2"
ACK_SCHEMA = "rq2_public_grid_activation_transport_ack_v2"
SOURCE_SCHEMA = "rq2_public_grid_activation_transport_source_v2"
ATTEMPT_SCHEMA = "rq2_public_grid_activation_transport_attempt_receipt_v2"
EVIDENCE_SCHEMA = "rq2_public_grid_activation_transport_accepted_evidence_v2"
MAX_FRAME_BYTES = 1024 * 1024
_ENVIRONMENT_ALLOWLIST = (
    "COMSPEC",
    "NO_COLOR",
    "PROCESSOR_ARCHITECTURE",
    "SYSTEMDRIVE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "WINDIR",
)


class TransportRejected(RuntimeError):
    """Fail-closed transport rejection."""


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise TransportRejected(f"authority unreadable: {path}") from exc
    return digest.hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _json_bytes(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise TransportRejected(f"{label} is not canonical JSON") from exc
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise TransportRejected(f"{label} canonical bytes drifted")
    return value


def _load_config() -> dict[str, Any]:
    try:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TransportRejected("activation-v2 config unreadable") from exc
    if not isinstance(payload, dict):
        raise TransportRejected("activation-v2 config is not an object")
    if (
        payload.get("schema")
        != "rq2_public_grid_two_block_pilot_activation_transport_v2"
        or payload.get("status") != "activation_transport_v2_candidate_closed"
    ):
        raise TransportRejected("activation-v2 config identity drifted")
    return payload


def _sanitized_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    observed = os.environ if source is None else source
    environment = {
        key: str(observed[key]) for key in _ENVIRONMENT_ALLOWLIST if key in observed
    }
    environment["NO_COLOR"] = "1"
    if set(environment) != set(_ENVIRONMENT_ALLOWLIST):
        raise TransportRejected("worker environment allowlist is incomplete")
    return environment


def _process_creation_time_ns(pid: int) -> int:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise TransportRejected("process PID is invalid")
    if os.name != "nt":
        try:
            return os.stat(f"/proc/{pid}", follow_symlinks=False).st_ctime_ns
        except OSError as exc:
            raise TransportRejected("process creation identity unavailable") from exc

    class FILETIME(ctypes.Structure):
        _fields_ = [("low", ctypes.c_ulong), ("high", ctypes.c_ulong)]

        @property
        def ticks(self) -> int:
            return (int(self.high) << 32) | int(self.low)

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    handle = kernel32.OpenProcess(0x1000, 0, pid)
    if not handle:
        raise TransportRejected("process creation identity unavailable")
    creation = FILETIME()
    exit_time = FILETIME()
    kernel = FILETIME()
    user = FILETIME()
    try:
        if not kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            raise TransportRejected("process creation identity unavailable")
    finally:
        kernel32.CloseHandle(handle)
    return creation.ticks * 100


def _expected_worker_command(python: Path, read_handle: int, ack_handle: int) -> list[str]:
    return [
        str(python),
        "-B",
        "-m",
        MODULE,
        "--internal-probe-worker",
        "--read-handle",
        str(read_handle),
        "--ack-handle",
        str(ack_handle),
    ]


def _require_anonymous_pipe(descriptor: int, label: str, *, writable: bool) -> None:
    if isinstance(descriptor, bool) or not isinstance(descriptor, int) or descriptor < 0:
        raise TransportRejected(f"{label} descriptor is invalid")
    if os.name == "nt":
        import msvcrt

        handle = msvcrt.get_osfhandle(descriptor)
        if ctypes.windll.kernel32.GetFileType(handle) != 3:  # type: ignore[attr-defined]
            raise TransportRejected(f"{label} is not a pipe")
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
            raise TransportRejected(f"{label} has the wrong pipe direction")
        return
    metadata = os.fstat(descriptor)
    if not stat.S_ISFIFO(metadata.st_mode):
        raise TransportRejected(f"{label} is not an anonymous pipe")


def _read_exact(descriptor: int, size: int) -> bytes:
    payload = bytearray()
    while len(payload) < size:
        chunk = os.read(descriptor, size - len(payload))
        if not chunk:
            raise EOFError("unexpected frame EOF")
        payload.extend(chunk)
    return bytes(payload)


def _read_frame(descriptor: int, label: str) -> tuple[bytes, dict[str, Any]]:
    size = int.from_bytes(_read_exact(descriptor, 8), "big")
    if size <= 0 or size > MAX_FRAME_BYTES:
        raise TransportRejected(f"{label} frame size rejected")
    raw = _read_exact(descriptor, size)
    return raw, _json_bytes(raw, label)


def _write_frame(descriptor: int, payload: Mapping[str, Any]) -> bytes:
    raw = _canonical_bytes(dict(payload))
    frame = len(raw).to_bytes(8, "big") + raw
    offset = 0
    while offset < len(frame):
        written = os.write(descriptor, frame[offset:])
        if written <= 0:
            raise TransportRejected("frame write failed")
        offset += written
    return raw


def _threaded_call(
    process: subprocess.Popen[Any], call: Callable[[], Any], *, deadline: float, label: str
) -> Any:
    responses: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)

    def invoke() -> None:
        try:
            responses.put((True, call()))
        except Exception as exc:  # noqa: BLE001 - propagate across monitor thread
            responses.put((False, exc))

    threading.Thread(target=invoke, daemon=True).start()
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(f"{label} exceeded watchdog")
        try:
            ok, value = responses.get(timeout=min(0.05, remaining))
        except queue.Empty:
            if process.poll() is not None:
                raise TransportRejected(f"{label} worker exited early")
            continue
        if not ok:
            raise value
        return value


def _terminate_owned_child(
    process: subprocess.Popen[Any], *, expected_pid: int, expected_create_ns: int
) -> None:
    if process.pid != expected_pid:
        raise TransportRejected("refusing to terminate an unowned PID")
    if process.poll() is not None:
        return
    if _process_creation_time_ns(process.pid) != expected_create_ns:
        raise TransportRejected("refusing to terminate PID-reused child")
    process.terminate()
    try:
        process.wait(timeout=1.0)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired as exc:
            raise TransportRejected("owned child survived terminate/kill") from exc


def _source_objects(envelope: Mapping[str, Any]) -> tuple[bytes, bytes]:
    source = {
        "schema": SOURCE_SCHEMA,
        "evidence_kind": "preloader_probe",
        "block_id": envelope["block_id"],
        "execution_index": envelope["execution_index"],
        "nonce": envelope["nonce"],
        "envelope_sha256": _canonical_sha256(dict(envelope)),
        "scientific_payload_sha256": None,
        "preloader_cut": True,
        "all_hours_resolved": None,
        "mathematical_infeasibility_inferred": False,
    }
    source_bytes = _canonical_bytes(source)
    receipt = {
        "schema": ATTEMPT_SCHEMA,
        "evidence_kind": "preloader_probe",
        "block_id": envelope["block_id"],
        "execution_index": envelope["execution_index"],
        "nonce": envelope["nonce"],
        "envelope_sha256": source["envelope_sha256"],
        "source_payload_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "scientific_payload_sha256": None,
        "controller_validation_passed": False,
        "published": False,
        "scientific_loader_calls": 0,
        "solver_calls": 0,
        "result_writes": 0,
        "formal_writes": 0,
        "mathematical_infeasibility_inferred": False,
    }
    return source_bytes, _canonical_bytes(receipt)


@dataclasses.dataclass(frozen=True, slots=True)
class AcceptedEvidence:
    schema: str
    evidence_kind: str
    block_id: str
    execution_index: int
    nonce: str
    envelope_bytes: bytes
    envelope_sha256: str
    ack_bytes: bytes
    ack_sha256: str
    popen_pid: int
    worker_create_time_ns: int
    source_payload_bytes: bytes
    source_payload_sha256: str
    source_attempt_receipt_bytes: bytes
    source_attempt_receipt_sha256: str
    scientific_payload_sha256: str | None
    predecessor_accepted_evidence_digest: str | None
    controller_session_id: str
    controller_acceptance_mac: str | None
    accepted_evidence_digest: str


@dataclasses.dataclass(frozen=True, slots=True)
class AttemptCapability:
    controller_session_id: str
    token_id: str
    block_id: str
    execution_index: int
    nonce: str
    child_pid: int
    child_create_time_ns: int


def _evidence_digest_payload(evidence: AcceptedEvidence) -> dict[str, Any]:
    return {
        "schema": evidence.schema,
        "evidence_kind": evidence.evidence_kind,
        "block_id": evidence.block_id,
        "execution_index": evidence.execution_index,
        "nonce": evidence.nonce,
        "envelope_sha256": evidence.envelope_sha256,
        "ack_sha256": evidence.ack_sha256,
        "popen_pid": evidence.popen_pid,
        "worker_create_time_ns": evidence.worker_create_time_ns,
        "source_payload_sha256": evidence.source_payload_sha256,
        "source_attempt_receipt_sha256": evidence.source_attempt_receipt_sha256,
        "scientific_payload_sha256": evidence.scientific_payload_sha256,
        "predecessor_accepted_evidence_digest": (
            evidence.predecessor_accepted_evidence_digest
        ),
        "controller_session_id": evidence.controller_session_id,
    }


def _verify_evidence(
    evidence: AcceptedEvidence,
    *,
    expected_index: int,
    expected_predecessor: str | None,
    expected_ledger_digest: str,
    required_kind: str,
) -> None:
    if type(evidence) is not AcceptedEvidence:
        raise TransportRejected("evidence must be the exact frozen dataclass")
    if (
        evidence.schema != EVIDENCE_SCHEMA
        or evidence.evidence_kind != required_kind
        or evidence.execution_index != expected_index
        or evidence.block_id != BLOCKS[expected_index - 1]
        or evidence.predecessor_accepted_evidence_digest != expected_predecessor
        or isinstance(evidence.popen_pid, bool)
        or evidence.popen_pid <= 0
        or isinstance(evidence.worker_create_time_ns, bool)
        or evidence.worker_create_time_ns <= 0
        or not _is_sha256(evidence.controller_session_id)
    ):
        raise TransportRejected("evidence identity/order/predecessor drifted")
    if (
        not isinstance(evidence.nonce, str)
        or len(evidence.nonce) != 64
        or any(character not in "0123456789abcdef" for character in evidence.nonce)
    ):
        raise TransportRejected("evidence nonce malformed")
    envelope = _json_bytes(evidence.envelope_bytes, "evidence envelope")
    ack = _json_bytes(evidence.ack_bytes, "evidence ACK")
    source = _json_bytes(evidence.source_payload_bytes, "evidence source payload")
    receipt = _json_bytes(
        evidence.source_attempt_receipt_bytes, "evidence attempt receipt"
    )
    observed_hashes = {
        "envelope": hashlib.sha256(evidence.envelope_bytes).hexdigest(),
        "ack": hashlib.sha256(evidence.ack_bytes).hexdigest(),
        "source": hashlib.sha256(evidence.source_payload_bytes).hexdigest(),
        "receipt": hashlib.sha256(evidence.source_attempt_receipt_bytes).hexdigest(),
    }
    if observed_hashes != {
        "envelope": evidence.envelope_sha256,
        "ack": evidence.ack_sha256,
        "source": evidence.source_payload_sha256,
        "receipt": evidence.source_attempt_receipt_sha256,
    }:
        raise TransportRejected("evidence source/envelope/ACK byte identity drifted")
    expected_envelope_keys = {
        "schema", "mode", "block_id", "execution_index", "nonce", "issued_ns",
        "controller_session_id", "predecessor_accepted_evidence_digest",
        "ledger_digest_before", "parent_pid", "parent_create_time_ns", "worker_pid",
        "worker_create_time_ns", "worker_command", "read_handle", "ack_handle",
        "working_directory", "sanitized_environment", "transport_module_path",
        "transport_module_sha256", "config_path", "config_sha256",
        "activation_v1_outer_path", "activation_v1_outer_sha256",
        "activation_v1_rework_path", "activation_v1_rework_sha256",
        "production_dispatch_permitted",
    }
    if (
        set(envelope) != expected_envelope_keys
        or envelope.get("schema") != ENVELOPE_SCHEMA
        or envelope.get("mode") != required_kind
        or envelope.get("block_id") != evidence.block_id
        or envelope.get("execution_index") != evidence.execution_index
        or envelope.get("nonce") != evidence.nonce
        or envelope.get("predecessor_accepted_evidence_digest")
        != expected_predecessor
        or envelope.get("ledger_digest_before") != expected_ledger_digest
        or envelope.get("worker_pid") != evidence.popen_pid
        or envelope.get("worker_create_time_ns") != evidence.worker_create_time_ns
        or envelope.get("controller_session_id") != evidence.controller_session_id
        or isinstance(envelope.get("issued_ns"), bool)
        or not isinstance(envelope.get("issued_ns"), int)
        or int(envelope["issued_ns"]) <= 0
        or isinstance(envelope.get("parent_pid"), bool)
        or not isinstance(envelope.get("parent_pid"), int)
        or int(envelope["parent_pid"]) <= 0
        or isinstance(envelope.get("parent_create_time_ns"), bool)
        or not isinstance(envelope.get("parent_create_time_ns"), int)
        or int(envelope["parent_create_time_ns"]) <= 0
        or not isinstance(envelope.get("worker_command"), list)
        or not isinstance(envelope.get("read_handle"), int)
        or isinstance(envelope.get("read_handle"), bool)
        or int(envelope["read_handle"]) < 0
        or not isinstance(envelope.get("ack_handle"), int)
        or isinstance(envelope.get("ack_handle"), bool)
        or int(envelope["ack_handle"]) < 0
        or not _is_sha256(envelope.get("transport_module_sha256"))
        or not _is_sha256(envelope.get("config_sha256"))
        or not _is_sha256(envelope.get("activation_v1_outer_sha256"))
        or not _is_sha256(envelope.get("activation_v1_rework_sha256"))
        or type(envelope.get("production_dispatch_permitted")) is not bool
        or envelope.get("production_dispatch_permitted")
        != (required_kind == "production_accepted")
    ):
        raise TransportRejected("evidence envelope history/process binding drifted")
    expected_ack_keys = {
        "schema",
        "mode",
        "block_id",
        "execution_index",
        "nonce",
        "envelope_sha256",
        "worker_pid",
        "worker_create_time_ns",
        "bounded_eof_verified_before_ack",
        "accepted_once",
        "source_payload_base64",
        "source_payload_sha256",
        "source_attempt_receipt_base64",
        "source_attempt_receipt_sha256",
        "scientific_loader_calls",
        "solver_calls",
        "result_writes",
        "formal_writes",
    }
    try:
        ack_source = base64.b64decode(ack.get("source_payload_base64", ""), validate=True)
        ack_receipt = base64.b64decode(
            ack.get("source_attempt_receipt_base64", ""), validate=True
        )
    except (ValueError, TypeError) as exc:
        raise TransportRejected("ACK source bytes are malformed") from exc
    if (
        set(ack) != expected_ack_keys
        or ack.get("schema") != ACK_SCHEMA
        or ack.get("mode") != required_kind
        or ack.get("block_id") != evidence.block_id
        or ack.get("execution_index") != evidence.execution_index
        or ack.get("nonce") != evidence.nonce
        or ack.get("envelope_sha256") != evidence.envelope_sha256
        or ack.get("worker_pid") != evidence.popen_pid
        or ack.get("worker_create_time_ns") != evidence.worker_create_time_ns
        or ack.get("bounded_eof_verified_before_ack") is not True
        or ack.get("accepted_once") is not True
        or ack_source != evidence.source_payload_bytes
        or ack_receipt != evidence.source_attempt_receipt_bytes
        or ack.get("source_payload_sha256") != evidence.source_payload_sha256
        or ack.get("source_attempt_receipt_sha256")
        != evidence.source_attempt_receipt_sha256
        or any(ack.get(key) != 0 for key in ("scientific_loader_calls", "solver_calls", "result_writes", "formal_writes"))
    ):
        raise TransportRejected("ACK/evidence/source authority drifted")
    expected_common = {
        "evidence_kind": required_kind,
        "block_id": evidence.block_id,
        "execution_index": evidence.execution_index,
        "nonce": evidence.nonce,
        "envelope_sha256": evidence.envelope_sha256,
        "scientific_payload_sha256": evidence.scientific_payload_sha256,
        "mathematical_infeasibility_inferred": False,
    }
    expected_source_keys = {
        "schema", "evidence_kind", "block_id", "execution_index", "nonce",
        "envelope_sha256", "scientific_payload_sha256", "preloader_cut",
        "all_hours_resolved", "mathematical_infeasibility_inferred",
    }
    expected_receipt_keys = {
        "schema", "evidence_kind", "block_id", "execution_index", "nonce",
        "envelope_sha256", "source_payload_sha256", "scientific_payload_sha256",
        "controller_validation_passed", "published", "scientific_loader_calls",
        "solver_calls", "result_writes", "formal_writes",
        "mathematical_infeasibility_inferred",
    }
    if (
        set(source) != expected_source_keys
        or set(receipt) != expected_receipt_keys
        or source.get("schema") != SOURCE_SCHEMA
        or any(source.get(key) != value for key, value in expected_common.items())
        or receipt.get("schema") != ATTEMPT_SCHEMA
        or any(receipt.get(key) != value for key, value in expected_common.items())
        or receipt.get("source_payload_sha256") != evidence.source_payload_sha256
        or receipt.get("controller_validation_passed") is not False
        or receipt.get("published") is not False
        or any(receipt.get(key) != 0 for key in ("scientific_loader_calls", "solver_calls", "result_writes", "formal_writes"))
    ):
        raise TransportRejected("source payload/receipt identity drifted")
    if required_kind == "preloader_probe":
        if (
            evidence.scientific_payload_sha256 is not None
            or source.get("preloader_cut") is not True
            or source.get("all_hours_resolved") is not None
        ):
            raise TransportRejected("pre-loader probe semantics drifted")
    elif required_kind == "production_accepted":
        if (
            not _is_sha256(evidence.scientific_payload_sha256)
            or source.get("preloader_cut") is not False
            or source.get("all_hours_resolved") is not True
        ):
            raise TransportRejected("production evidence is incomplete")
    else:
        raise TransportRejected("unregistered evidence kind")
    if evidence.accepted_evidence_digest != _canonical_sha256(
        _evidence_digest_payload(evidence)
    ):
        raise TransportRejected("accepted-evidence digest drifted")


def _ledger_digest(records: Sequence[AcceptedEvidence]) -> str:
    return _canonical_sha256(
        [record.accepted_evidence_digest for record in records]
    )


def _full_history_verify(
    records: Sequence[AcceptedEvidence], *, session_id: str, secret: bytes
) -> None:
    seen: dict[str, set[object]] = {
        "process": set(),
        "nonce": set(),
        "envelope": set(),
        "ack": set(),
        "source": set(),
        "receipt": set(),
    }
    prefix: list[AcceptedEvidence] = []
    for expected_index, record in enumerate(records, start=1):
        if expected_index > len(BLOCKS):
            raise TransportRejected("ledger contains an extra/retry record")
        predecessor = None if expected_index == 1 else prefix[-1].accepted_evidence_digest
        _verify_evidence(
            record,
            expected_index=expected_index,
            expected_predecessor=predecessor,
            expected_ledger_digest=_ledger_digest(prefix),
            required_kind="production_accepted",
        )
        expected_mac = hmac.new(
            secret,
            f"{session_id}:{record.accepted_evidence_digest}".encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if record.controller_session_id != session_id or not hmac.compare_digest(
            str(record.controller_acceptance_mac), expected_mac
        ):
            raise TransportRejected("ledger record lacks current-session acceptance")
        identities = {
            "process": (record.popen_pid, record.worker_create_time_ns),
            "nonce": record.nonce,
            "envelope": record.envelope_sha256,
            "ack": record.ack_sha256,
            "source": record.source_payload_sha256,
            "receipt": record.source_attempt_receipt_sha256,
        }
        for label, identity in identities.items():
            if identity in seen[label]:
                raise TransportRejected(f"ledger replay detected: {label}")
            seen[label].add(identity)
        prefix.append(record)


class ControllerLedger:
    """Fresh, in-memory, no-resume ledger that revalidates from genesis."""

    __slots__ = ("_active_attempts", "_records", "_secret", "_session_id")

    def __init__(self) -> None:
        self._records: tuple[AcceptedEvidence, ...] = ()
        self._secret = secrets.token_bytes(32)
        self._session_id = hashlib.sha256(self._secret).hexdigest()
        self._active_attempts: dict[str, AttemptCapability] = {}

    @property
    def records(self) -> tuple[AcceptedEvidence, ...]:
        _full_history_verify(
            self._records, session_id=self._session_id, secret=self._secret
        )
        return self._records

    @property
    def digest(self) -> str:
        return _ledger_digest(self.records)

    @property
    def session_id(self) -> str:
        return self._session_id

    def predecessor_for(self, execution_index: int) -> str | None:
        records = self.records
        if execution_index == 1 and not records:
            return None
        if execution_index == 2 and len(records) == 1:
            return records[0].accepted_evidence_digest
        raise TransportRejected("ledger does not authorize the requested execution index")

    def begin_transport_attempt(
        self,
        process: subprocess.Popen[Any],
        *,
        block_id: str,
        execution_index: int,
        nonce: str,
    ) -> AttemptCapability:
        if type(process) is not subprocess.Popen or process.poll() is not None:
            raise TransportRejected("transport attempt requires an exact live Popen child")
        if (
            isinstance(execution_index, bool)
            or not isinstance(execution_index, int)
            or execution_index not in (1, 2)
        ):
            raise TransportRejected("transport attempt execution index is invalid")
        if block_id != BLOCKS[execution_index - 1]:
            raise TransportRejected("transport attempt block/index drifted")
        self.predecessor_for(execution_index)
        if (
            not isinstance(nonce, str)
            or len(nonce) != 64
            or any(character not in "0123456789abcdef" for character in nonce)
        ):
            raise TransportRejected("transport attempt nonce malformed")
        create_ns = _process_creation_time_ns(process.pid)
        token = AttemptCapability(
            controller_session_id=self._session_id,
            token_id=secrets.token_hex(32),
            block_id=block_id,
            execution_index=execution_index,
            nonce=nonce,
            child_pid=process.pid,
            child_create_time_ns=create_ns,
        )
        self._active_attempts[token.token_id] = token
        return token

    def accept_verified_transport(
        self, evidence: AcceptedEvidence, capability: AttemptCapability
    ) -> AcceptedEvidence:
        if type(capability) is not AttemptCapability:
            raise TransportRejected("current-session transport capability is required")
        registered = self._active_attempts.pop(capability.token_id, None)
        if registered is not capability:
            raise TransportRejected("transport capability is absent, forged, or replayed")
        if (
            capability.controller_session_id != self._session_id
            or capability.block_id != evidence.block_id
            or capability.execution_index != evidence.execution_index
            or capability.nonce != evidence.nonce
            or capability.child_pid != evidence.popen_pid
            or capability.child_create_time_ns != evidence.worker_create_time_ns
        ):
            raise TransportRejected("transport capability/evidence identity drifted")
        records = self.records
        expected_index = len(records) + 1
        predecessor = None if expected_index == 1 else records[-1].accepted_evidence_digest
        _verify_evidence(
            evidence,
            expected_index=expected_index,
            expected_predecessor=predecessor,
            expected_ledger_digest=_ledger_digest(records),
            required_kind="production_accepted",
        )
        mac = hmac.new(
            self._secret,
            f"{self._session_id}:{evidence.accepted_evidence_digest}".encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        sealed = dataclasses.replace(evidence, controller_acceptance_mac=mac)
        candidate = (*records, sealed)
        _full_history_verify(
            candidate, session_id=self._session_id, secret=self._secret
        )
        self._records = candidate
        return sealed


def _build_probe_envelope(
    *,
    config: Mapping[str, Any],
    ledger: ControllerLedger,
    worker_pid: int,
    worker_create_time_ns: int,
    worker_command: Sequence[str],
    read_handle: int,
    ack_handle: int,
) -> dict[str, Any]:
    if ledger.records:
        raise TransportRejected("pre-loader probe requires an empty fresh ledger")
    return {
        "schema": ENVELOPE_SCHEMA,
        "mode": "preloader_probe",
        "block_id": BLOCKS[0],
        "execution_index": 1,
        "nonce": secrets.token_hex(32),
        "issued_ns": time.time_ns(),
        "controller_session_id": ledger.session_id,
        "predecessor_accepted_evidence_digest": None,
        "ledger_digest_before": ledger.digest,
        "parent_pid": os.getpid(),
        "parent_create_time_ns": _process_creation_time_ns(os.getpid()),
        "worker_pid": worker_pid,
        "worker_create_time_ns": worker_create_time_ns,
        "worker_command": list(worker_command),
        "read_handle": read_handle,
        "ack_handle": ack_handle,
        "working_directory": str(ROOT),
        "sanitized_environment": _sanitized_environment(),
        "transport_module_path": str(Path(__file__).resolve()),
        "transport_module_sha256": _sha256(Path(__file__).resolve()),
        "config_path": str(CONFIG),
        "config_sha256": _sha256(CONFIG),
        "activation_v1_outer_path": str(V1_OUTER),
        "activation_v1_outer_sha256": V1_OUTER_SHA256,
        "activation_v1_rework_path": str(V1_REWORK),
        "activation_v1_rework_sha256": str(
            config["predecessor_authority"]["activation_v1_rework_sha256"]
        ),
        "production_dispatch_permitted": False,
    }


def _validate_probe_envelope(
    envelope: Mapping[str, Any], *, read_handle: int, ack_handle: int
) -> None:
    config = _load_config()
    expected_keys = {
        "schema", "mode", "block_id", "execution_index", "nonce", "issued_ns",
        "controller_session_id", "predecessor_accepted_evidence_digest",
        "ledger_digest_before", "parent_pid", "parent_create_time_ns", "worker_pid",
        "worker_create_time_ns", "worker_command", "read_handle", "ack_handle",
        "working_directory", "sanitized_environment", "transport_module_path",
        "transport_module_sha256", "config_path", "config_sha256",
        "activation_v1_outer_path", "activation_v1_outer_sha256",
        "activation_v1_rework_path", "activation_v1_rework_sha256",
        "production_dispatch_permitted",
    }
    python = Path(sys.executable)
    if (
        set(envelope) != expected_keys
        or envelope.get("schema") != ENVELOPE_SCHEMA
        or envelope.get("mode") != "preloader_probe"
        or envelope.get("block_id") != BLOCKS[0]
        or envelope.get("execution_index") != 1
        or envelope.get("predecessor_accepted_evidence_digest") is not None
        or envelope.get("ledger_digest_before") != _canonical_sha256([])
        or envelope.get("worker_pid") != os.getpid()
        or envelope.get("worker_create_time_ns") != _process_creation_time_ns(os.getpid())
        or envelope.get("parent_pid") != os.getppid()
        or envelope.get("parent_create_time_ns") != _process_creation_time_ns(os.getppid())
        or envelope.get("worker_command")
        != _expected_worker_command(python, read_handle, ack_handle)
        or list(sys.orig_argv) != envelope.get("worker_command")
        or envelope.get("read_handle") != read_handle
        or envelope.get("ack_handle") != ack_handle
        or envelope.get("working_directory") != str(ROOT)
        or Path.cwd() != ROOT
        or envelope.get("sanitized_environment") != _sanitized_environment()
        or envelope.get("transport_module_path") != str(Path(__file__).resolve())
        or envelope.get("transport_module_sha256") != _sha256(Path(__file__).resolve())
        or envelope.get("config_path") != str(CONFIG)
        or envelope.get("config_sha256") != _sha256(CONFIG)
        or envelope.get("activation_v1_outer_path") != str(V1_OUTER)
        or envelope.get("activation_v1_outer_sha256") != V1_OUTER_SHA256
        or _sha256(V1_OUTER) != V1_OUTER_SHA256
        or envelope.get("activation_v1_rework_path") != str(V1_REWORK)
        or envelope.get("activation_v1_rework_sha256")
        != config["predecessor_authority"]["activation_v1_rework_sha256"]
        or _sha256(V1_REWORK) != envelope.get("activation_v1_rework_sha256")
        or envelope.get("production_dispatch_permitted") is not False
    ):
        raise TransportRejected("pre-loader capability authority drifted")
    if not _is_sha256(envelope.get("controller_session_id")):
        raise TransportRejected("controller session identity malformed")


def _worker_probe(
    read_descriptor: int,
    ack_descriptor: int,
    *,
    read_handle: int,
    ack_handle: int,
) -> int:
    _require_anonymous_pipe(read_descriptor, "capability input", writable=False)
    _require_anonymous_pipe(ack_descriptor, "ACK output", writable=True)
    identity = {
        "schema": HELLO_SCHEMA,
        "worker_pid": os.getpid(),
        "worker_parent_pid": os.getppid(),
        "worker_create_time_ns": _process_creation_time_ns(os.getpid()),
        "transport_module_sha256": _sha256(Path(__file__).resolve()),
        "production_dispatch_permitted": False,
    }
    _write_frame(ack_descriptor, identity)
    _raw, envelope = _read_frame(read_descriptor, "capability envelope")
    if os.read(read_descriptor, 1) != b"":
        raise TransportRejected("capability replay/trailing bytes rejected")
    _validate_probe_envelope(
        envelope, read_handle=read_handle, ack_handle=ack_handle
    )
    source, receipt = _source_objects(envelope)
    ack = {
        "schema": ACK_SCHEMA,
        "mode": "preloader_probe",
        "block_id": envelope["block_id"],
        "execution_index": envelope["execution_index"],
        "nonce": envelope["nonce"],
        "envelope_sha256": _canonical_sha256(dict(envelope)),
        "worker_pid": os.getpid(),
        "worker_create_time_ns": _process_creation_time_ns(os.getpid()),
        "bounded_eof_verified_before_ack": True,
        "accepted_once": True,
        "source_payload_base64": base64.b64encode(source).decode("ascii"),
        "source_payload_sha256": hashlib.sha256(source).hexdigest(),
        "source_attempt_receipt_base64": base64.b64encode(receipt).decode("ascii"),
        "source_attempt_receipt_sha256": hashlib.sha256(receipt).hexdigest(),
        "scientific_loader_calls": 0,
        "solver_calls": 0,
        "result_writes": 0,
        "formal_writes": 0,
    }
    _write_frame(ack_descriptor, ack)
    return 0


def _windows_popen_kwargs(read_handle: int, ack_handle: int) -> dict[str, Any]:
    startup = subprocess.STARTUPINFO()
    startup.lpAttributeList = {"handle_list": [read_handle, ack_handle]}
    return {"startupinfo": startup, "close_fds": True}


def run_preloader_probe(*, timeout_seconds: float = 10.0) -> AcceptedEvidence:
    """Run one real fresh child through the new transport, stopping pre-loader."""

    if timeout_seconds <= 0:
        raise TransportRejected("probe timeout must be positive")
    config = _load_config()
    if config["gates"]["production_dispatch_permitted"] is not False:
        raise TransportRejected("production dispatch gate drifted")
    ledger = ControllerLedger()
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
    python = Path(sys.executable)
    command = _expected_worker_command(python, child_read, child_ack)
    kwargs: dict[str, Any] = {
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
    process: subprocess.Popen[Any] | None = None
    child_create_ns = -1
    try:
        process = subprocess.Popen(command, **kwargs)
        child_create_ns = _process_creation_time_ns(process.pid)
        os.close(request_read)
        request_read = -1
        os.close(ack_write)
        ack_write = -1
        deadline = time.monotonic() + timeout_seconds
        _hello_raw, hello = _threaded_call(
            process,
            lambda: _read_frame(ack_read, "worker hello"),
            deadline=deadline,
            label="worker hello",
        )
        if hello != {
            "schema": HELLO_SCHEMA,
            "worker_pid": process.pid,
            "worker_parent_pid": os.getpid(),
            "worker_create_time_ns": child_create_ns,
            "transport_module_sha256": _sha256(Path(__file__).resolve()),
            "production_dispatch_permitted": False,
        }:
            raise TransportRejected("worker hello/fresh-process identity drifted")
        envelope = _build_probe_envelope(
            config=config,
            ledger=ledger,
            worker_pid=process.pid,
            worker_create_time_ns=child_create_ns,
            worker_command=command,
            read_handle=child_read,
            ack_handle=child_ack,
        )
        envelope_raw = _write_frame(request_write, envelope)
        os.close(request_write)
        request_write = -1
        ack_raw, ack = _threaded_call(
            process,
            lambda: _read_frame(ack_read, "worker ACK"),
            deadline=deadline,
            label="worker ACK",
        )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("worker completion exceeded watchdog")
        process.wait(timeout=remaining)
        if process.returncode != 0:
            raise TransportRejected("pre-loader worker exited nonzero")
        source = base64.b64decode(ack["source_payload_base64"], validate=True)
        receipt = base64.b64decode(
            ack["source_attempt_receipt_base64"], validate=True
        )
        provisional = AcceptedEvidence(
            schema=EVIDENCE_SCHEMA,
            evidence_kind="preloader_probe",
            block_id=BLOCKS[0],
            execution_index=1,
            nonce=str(envelope["nonce"]),
            envelope_bytes=envelope_raw,
            envelope_sha256=hashlib.sha256(envelope_raw).hexdigest(),
            ack_bytes=ack_raw,
            ack_sha256=hashlib.sha256(ack_raw).hexdigest(),
            popen_pid=process.pid,
            worker_create_time_ns=child_create_ns,
            source_payload_bytes=source,
            source_payload_sha256=hashlib.sha256(source).hexdigest(),
            source_attempt_receipt_bytes=receipt,
            source_attempt_receipt_sha256=hashlib.sha256(receipt).hexdigest(),
            scientific_payload_sha256=None,
            predecessor_accepted_evidence_digest=None,
            controller_session_id=ledger.session_id,
            controller_acceptance_mac=None,
            accepted_evidence_digest="",
        )
        evidence = dataclasses.replace(
            provisional,
            accepted_evidence_digest=_canonical_sha256(
                _evidence_digest_payload(provisional)
            ),
        )
        _verify_evidence(
            evidence,
            expected_index=1,
            expected_predecessor=None,
            expected_ledger_digest=_canonical_sha256([]),
            required_kind="preloader_probe",
        )
        return evidence
    except Exception:
        if process is not None and process.poll() is None and child_create_ns > 0:
            _terminate_owned_child(
                process,
                expected_pid=process.pid,
                expected_create_ns=child_create_ns,
            )
        raise
    finally:
        for descriptor in (request_read, request_write, ack_read, ack_write):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--internal-probe-worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--read-handle", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--ack-handle", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not args.internal_probe_worker:
        parser.error("activation transport v2 has no public execution CLI")
    if args.read_handle is None or args.ack_handle is None:
        parser.error("internal probe worker requires inherited handles")
    return args


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    read_handle = int(args.read_handle)
    ack_handle = int(args.ack_handle)
    read_descriptor = read_handle
    ack_descriptor = ack_handle
    if os.name == "nt":
        import msvcrt

        read_descriptor = msvcrt.open_osfhandle(read_handle, os.O_RDONLY)
        ack_descriptor = msvcrt.open_osfhandle(ack_handle, os.O_WRONLY)
    raise SystemExit(
        _worker_probe(
            read_descriptor,
            ack_descriptor,
            read_handle=read_handle,
            ack_handle=ack_handle,
        )
    )


if __name__ == "__main__":
    main()
