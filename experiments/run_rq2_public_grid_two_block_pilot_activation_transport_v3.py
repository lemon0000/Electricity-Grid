"""Closed activation-v3 controller-owned production transport.

Only the controller creates the child, pipes, command, environment, envelope,
and ledger record.  No API accepts caller-provided Popen objects, transport
capabilities, ACK/source bytes, or evidence.  The review boundary spawns the
real production-worker command and stops before scientific data loading.
"""

from __future__ import annotations

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
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Any

ROOT = Path(r"D:\CUHKSZ\Research Project\electricity-grid")
MODULE = "experiments.run_rq2_public_grid_two_block_pilot_activation_transport_v3"
WORKER_MODULE = (
    "experiments.worker_rq2_public_grid_two_block_pilot_activation_transport_v3"
)
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_activation_transport_v3.json"
V2_OUTER = ROOT / "configs/rq2_public_grid_two_block_pilot_activation_transport_v2.OUTER.SHA256SUMS.json"
V2_ESCALATE = ROOT / "configs/rq2_public_grid_two_block_pilot_activation_transport_review_escalate_v2.json"
V3_OUTER = ROOT / "configs/rq2_public_grid_two_block_pilot_activation_transport_v3.OUTER.SHA256SUMS.json"
PRODUCTION_DISPATCH_PERMITTED = False
BLOCKS = ("holdout_s20260822_0008", "holdout_s20260822_0009")

HELLO_SCHEMA = "rq2_public_grid_activation_transport_worker_hello_v3"
ENVELOPE_SCHEMA = "rq2_public_grid_activation_transport_envelope_v3"
ACK_SCHEMA = "rq2_public_grid_activation_transport_worker_ack_v3"
SOURCE_SCHEMA = "rq2_public_grid_activation_transport_worker_source_v3"
RECORD_SCHEMA = "rq2_public_grid_activation_transport_accepted_record_v3"
MAX_FRAME_BYTES = 64 * 1024 * 1024


class TransportRejected(RuntimeError):
    """Fail-closed controller transport rejection."""


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


def _json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise TransportRejected(f"{label} is not JSON") from exc
    if not isinstance(value, dict) or _canonical_bytes(value) != raw:
        raise TransportRejected(f"{label} canonical bytes drifted")
    return value


def _load_config() -> dict[str, Any]:
    try:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TransportRejected("activation-v3 config unreadable") from exc
    if (
        not isinstance(payload, dict)
        or payload.get("schema")
        != "rq2_public_grid_two_block_pilot_activation_transport_v3"
        or payload.get("status") != "activation_transport_v3_candidate_closed"
    ):
        raise TransportRejected("activation-v3 config identity drifted")
    return payload


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
        except Exception as exc:  # noqa: BLE001 - cross-thread propagation
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
        raise TransportRejected("refusing to terminate unowned PID")
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


def _worker_command(config: Mapping[str, Any], read_handle: int, ack_handle: int) -> list[str]:
    return [
        str(config["bootstrap_contract"]["locked_python_executable"]),
        "-B",
        "-m",
        WORKER_MODULE,
        "--internal-production-worker",
        "--read-handle",
        str(read_handle),
        "--ack-handle",
        str(ack_handle),
    ]


def _spawn_exact(
    config: Mapping[str, Any], read_handle: int, ack_handle: int
) -> subprocess.Popen[Any]:
    command = _worker_command(config, read_handle, ack_handle)
    kwargs: dict[str, Any] = {
        "cwd": str(ROOT),
        "env": dict(config["bootstrap_contract"]["exact_environment"]),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        handles = [read_handle, ack_handle]
        for handle in handles:
            os.set_handle_inheritable(handle, True)
        startup = subprocess.STARTUPINFO()
        startup.lpAttributeList = {"handle_list": handles}
        kwargs["startupinfo"] = startup
    else:
        os.set_inheritable(read_handle, True)
        os.set_inheritable(ack_handle, True)
        kwargs["pass_fds"] = (read_handle, ack_handle)
    try:
        return subprocess.Popen(command, **kwargs)
    finally:
        if os.name == "nt":
            for handle in (read_handle, ack_handle):
                os.set_handle_inheritable(handle, False)
        else:
            for descriptor in (read_handle, ack_handle):
                os.set_inheritable(descriptor, False)


@dataclasses.dataclass(frozen=True, slots=True)
class AcceptedRecord:
    schema: str
    block_id: str
    execution_index: int
    nonce: str
    child_pid: int
    child_create_time_ns: int
    envelope_sha256: str
    ack_sha256: str
    source_sha256: str
    scientific_payload_sha256: str
    certificate_inventory_sha256: str
    predecessor_accepted_digest: str | None
    controller_session_id: str
    controller_mac: str
    accepted_record_digest: str


@dataclasses.dataclass(frozen=True, slots=True)
class AttemptOutcome:
    block_id: str
    execution_index: int
    status: str
    accepted: bool
    child_pid: int
    child_create_time_ns: int
    envelope_sha256: str
    ack_sha256: str
    source_sha256: str
    counters: Mapping[str, int]
    mathematical_infeasibility_inferred: bool


def _record_digest(record: AcceptedRecord) -> str:
    return _canonical_sha256(
        {
            "schema": record.schema,
            "block_id": record.block_id,
            "execution_index": record.execution_index,
            "nonce": record.nonce,
            "child_pid": record.child_pid,
            "child_create_time_ns": record.child_create_time_ns,
            "envelope_sha256": record.envelope_sha256,
            "ack_sha256": record.ack_sha256,
            "source_sha256": record.source_sha256,
            "scientific_payload_sha256": record.scientific_payload_sha256,
            "certificate_inventory_sha256": record.certificate_inventory_sha256,
            "predecessor_accepted_digest": record.predecessor_accepted_digest,
            "controller_session_id": record.controller_session_id,
        }
    )


def _verify_history(
    records: Sequence[AcceptedRecord], *, session_id: str, secret: bytes
) -> None:
    seen: dict[str, set[object]] = {
        "process": set(),
        "nonce": set(),
        "envelope": set(),
        "ack": set(),
        "source": set(),
        "scientific": set(),
        "certificate": set(),
    }
    predecessor: str | None = None
    for expected_index, record in enumerate(records, start=1):
        if (
            type(record) is not AcceptedRecord
            or expected_index > 2
            or record.schema != RECORD_SCHEMA
            or record.execution_index != expected_index
            or record.block_id != BLOCKS[expected_index - 1]
            or record.predecessor_accepted_digest != predecessor
            or record.controller_session_id != session_id
            or record.accepted_record_digest != _record_digest(record)
        ):
            raise TransportRejected("accepted ledger history identity/order drifted")
        expected_mac = hmac.new(
            secret,
            f"{session_id}:{record.accepted_record_digest}".encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(record.controller_mac, expected_mac):
            raise TransportRejected("accepted ledger record lacks session MAC")
        identities = {
            "process": (record.child_pid, record.child_create_time_ns),
            "nonce": record.nonce,
            "envelope": record.envelope_sha256,
            "ack": record.ack_sha256,
            "source": record.source_sha256,
            "scientific": record.scientific_payload_sha256,
            "certificate": record.certificate_inventory_sha256,
        }
        for label, identity in identities.items():
            if identity in seen[label]:
                raise TransportRejected(f"accepted ledger replay: {label}")
            seen[label].add(identity)
        predecessor = record.accepted_record_digest


def _validate_hello(
    hello: Mapping[str, Any], process: subprocess.Popen[Any], config: Mapping[str, Any]
) -> int:
    transport = config["transport_contract"]
    create_ns = _process_creation_time_ns(process.pid)
    if (
        set(hello)
        != {
            "schema",
            "worker_pid",
            "worker_parent_pid",
            "worker_create_time_ns",
            "worker_module",
            "worker_sha256",
            "config_sha256",
        }
        or hello.get("schema") != HELLO_SCHEMA
        or hello.get("worker_pid") != process.pid
        or hello.get("worker_parent_pid") != os.getpid()
        or hello.get("worker_create_time_ns") != create_ns
        or hello.get("worker_module") != WORKER_MODULE
        or hello.get("worker_sha256") != transport["worker_sha256"]
        or hello.get("config_sha256") != _sha256(CONFIG)
    ):
        raise TransportRejected("worker HELLO origin authority drifted")
    return create_ns


def _build_envelope(
    *,
    config: Mapping[str, Any],
    session_id: str,
    records: Sequence[AcceptedRecord],
    process: subprocess.Popen[Any],
    child_create_ns: int,
    read_handle: int,
    ack_handle: int,
    execution_index: int,
    mode: str,
    future_authority: Mapping[str, Any] | None,
) -> dict[str, Any]:
    transport = config["transport_contract"]
    predecessor = records[-1].accepted_record_digest if records else None
    return {
        "schema": ENVELOPE_SCHEMA,
        "mode": mode,
        "block_id": BLOCKS[execution_index - 1],
        "execution_index": execution_index,
        "nonce": secrets.token_hex(32),
        "issued_ns": time.time_ns(),
        "controller_session_id": session_id,
        "predecessor_accepted_digest": predecessor,
        "ledger_digest_before": _canonical_sha256(
            [record.accepted_record_digest for record in records]
        ),
        "parent_pid": os.getpid(),
        "parent_create_time_ns": _process_creation_time_ns(os.getpid()),
        "worker_pid": process.pid,
        "worker_create_time_ns": child_create_ns,
        "worker_command": _worker_command(config, read_handle, ack_handle),
        "read_handle": read_handle,
        "ack_handle": ack_handle,
        "working_directory": str(ROOT),
        "sanitized_environment": dict(config["bootstrap_contract"]["exact_environment"]),
        "controller_path": str(ROOT / str(transport["controller_path"])),
        "controller_sha256": transport["controller_sha256"],
        "worker_path": str(ROOT / str(transport["worker_path"])),
        "worker_sha256": transport["worker_sha256"],
        "config_path": str(CONFIG),
        "config_sha256": _sha256(CONFIG),
        "activation_v2_outer_sha256": config["predecessor_authority"][
            "activation_v2_outer_sha256"
        ],
        "activation_v2_escalate_sha256": config["predecessor_authority"][
            "activation_v2_escalate_sha256"
        ],
        "future_authority": None if future_authority is None else dict(future_authority),
    }


def _validate_ack(
    ack_bytes: bytes,
    *,
    envelope_bytes: bytes,
    envelope: Mapping[str, Any],
    process: subprocess.Popen[Any],
    child_create_ns: int,
    config: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes, bytes, bytes]:
    ack = _json_bytes(ack_bytes, "worker ACK")
    expected_keys = {
        "schema",
        "status",
        "accepted",
        "block_id",
        "execution_index",
        "nonce",
        "envelope_sha256",
        "worker_pid",
        "worker_create_time_ns",
        "bounded_eof_verified_before_ack",
        "source_base64",
        "source_sha256",
        "scientific_payload_base64",
        "certificate_inventory_base64",
        "counters",
    }
    try:
        source_bytes = base64.b64decode(ack.get("source_base64", ""), validate=True)
        scientific_bytes = base64.b64decode(
            ack.get("scientific_payload_base64", ""), validate=True
        )
        certificate_bytes = base64.b64decode(
            ack.get("certificate_inventory_base64", ""), validate=True
        )
    except (TypeError, ValueError) as exc:
        raise TransportRejected("worker ACK byte payload malformed") from exc
    if (
        set(ack) != expected_keys
        or ack.get("schema") != ACK_SCHEMA
        or ack.get("block_id") != envelope["block_id"]
        or ack.get("execution_index") != envelope["execution_index"]
        or ack.get("nonce") != envelope["nonce"]
        or ack.get("envelope_sha256") != hashlib.sha256(envelope_bytes).hexdigest()
        or ack.get("worker_pid") != process.pid
        or ack.get("worker_create_time_ns") != child_create_ns
        or ack.get("bounded_eof_verified_before_ack") is not True
        or ack.get("source_sha256") != hashlib.sha256(source_bytes).hexdigest()
    ):
        raise TransportRejected("worker ACK identity/origin drifted")
    source = _json_bytes(source_bytes, "worker source")
    expected_source = {
        "schema",
        "status",
        "accepted",
        "unlock_successor",
        "block_id",
        "execution_index",
        "nonce",
        "envelope_sha256",
        "scientific_payload_sha256",
        "certificate_inventory_sha256",
        "all_hours_resolved",
        "termination",
        "counters",
        "mathematical_infeasibility_inferred",
    }
    counters = source.get("counters")
    if (
        set(source) != expected_source
        or source.get("schema") != SOURCE_SCHEMA
        or source.get("block_id") != envelope["block_id"]
        or source.get("execution_index") != envelope["execution_index"]
        or source.get("nonce") != envelope["nonce"]
        or source.get("envelope_sha256") != hashlib.sha256(envelope_bytes).hexdigest()
        or source.get("counters") != ack.get("counters")
        or source.get("mathematical_infeasibility_inferred") is not False
        or not isinstance(counters, dict)
        or set(counters)
        != {
            "scientific_loader_calls",
            "solver_calls",
            "result_writes",
            "formal_writes",
        }
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in counters.values()
        )
    ):
        raise TransportRejected("worker source schema/counters drifted")
    if envelope["mode"] == "review_only_preloader_stop":
        if (
            ack.get("status") != "NON_ACCEPTED_PRELOADER_BOUNDARY"
            or ack.get("accepted") is not False
            or source.get("accepted") is not False
            or source.get("unlock_successor") is not False
            or source.get("status") != "NON_ACCEPTED_PRELOADER_BOUNDARY"
            or source.get("termination") != "preloader_stop"
            or source.get("all_hours_resolved") is not None
            or source.get("scientific_payload_sha256") is not None
            or source.get("certificate_inventory_sha256") is not None
            or scientific_bytes
            or certificate_bytes
            or any(counters.values())
        ):
            raise TransportRejected("review-only boundary falsely claims acceptance")
    else:
        if (
            ack.get("status") != "ACCEPTED_COMPLETE"
            or ack.get("accepted") is not True
            or source.get("accepted") is not True
            or source.get("unlock_successor") is not True
            or source.get("all_hours_resolved") is not True
            or not scientific_bytes
            or not certificate_bytes
            or source.get("scientific_payload_sha256")
            != hashlib.sha256(scientific_bytes).hexdigest()
            or source.get("certificate_inventory_sha256")
            != hashlib.sha256(certificate_bytes).hexdigest()
            or counters["scientific_loader_calls"] != 1
            or counters["solver_calls"] <= 0
            or counters["result_writes"] != 0
            or counters["formal_writes"] != 0
        ):
            raise TransportRejected("production result is incomplete or unresolved")
        _validate_sealed_scientific_bytes(
            scientific_bytes,
            certificate_bytes,
            str(envelope["block_id"]),
            config,
        )
    return source, source_bytes, scientific_bytes, certificate_bytes


def _validate_sealed_scientific_bytes(
    scientific_bytes: bytes,
    certificate_bytes: bytes,
    block_id: str,
    config: Mapping[str, Any],
) -> None:
    authority = config["sealed_scientific_primitive_authority"]
    for path_key, hash_key in (
        ("v4_runner_path", "v4_runner_sha256"),
        ("v7_outer_path", "v7_outer_sha256"),
        ("v7_review_pass_path", "v7_review_pass_sha256"),
    ):
        if _sha256(ROOT / str(authority[path_key])) != authority[hash_key]:
            raise TransportRejected("sealed scientific primitive authority drifted")
    payload = _json_bytes(scientific_bytes, "scientific payload")
    certificate = _json_bytes(certificate_bytes, "certificate inventory")
    from experiments import run_rq2_public_grid_two_block_pilot_candidate_v4 as v4

    context = v4._stage_context()
    validated = v4.recovery._validate_scientific_payload(
        payload,
        block_id=block_id,
        expected_block=context["blocks"][block_id],
        config=context["config"],
    )
    expected_certificate = {
        "baseline_audit": validated.get("baseline_audit"),
        "hourly": [
            {
                "primary_certificate": outcome.get("primary_certificate"),
                "zero_dc_confirmation_certificate": outcome.get(
                    "zero_dc_confirmation_certificate"
                ),
            }
            for outcome in validated["outcomes"]
        ],
    }
    if certificate != expected_certificate:
        raise TransportRejected("certificate inventory/scientific payload mismatch")


class ControllerSession:
    """Owns every spawn-to-append transition for one no-retry two-block session."""

    __slots__ = (
        "_active_index",
        "_attempted",
        "_records",
        "_secret",
        "_session_id",
    )

    def __init__(self) -> None:
        self._secret = secrets.token_bytes(32)
        self._session_id = hashlib.sha256(self._secret).hexdigest()
        self._records: tuple[AcceptedRecord, ...] = ()
        self._attempted: set[int] = set()
        self._active_index: int | None = None

    @property
    def records(self) -> tuple[AcceptedRecord, ...]:
        _verify_history(
            self._records, session_id=self._session_id, secret=self._secret
        )
        return self._records

    @property
    def attempted_indices(self) -> frozenset[int]:
        return frozenset(self._attempted)

    def run_review_preloader_boundary(
        self, *, timeout_seconds: float = 10.0
    ) -> AttemptOutcome:
        """Run exact 0008 worker transport and stop before the loader."""
        return self._dispatch_owned(
            execution_index=1,
            mode="review_only_preloader_stop",
            future_authority=None,
            timeout_seconds=timeout_seconds,
        )

    def run_two_block_pilot(
        self,
        *,
        activation_review_receipt: Path,
        wrapper_review_receipt: Path,
        dispatch_authorization_receipt: Path,
    ) -> tuple[AcceptedRecord, AcceptedRecord]:
        """Future wrapper interface; all three external receipts are mandatory."""
        config = _load_config()
        authority = _load_future_authority(
            activation_review_receipt=activation_review_receipt,
            wrapper_review_receipt=wrapper_review_receipt,
            dispatch_authorization_receipt=dispatch_authorization_receipt,
            config=config,
        )
        watchdog = float(config["resource_contract"]["external_watchdog_seconds_per_block"])
        for index in (1, 2):
            outcome = self._dispatch_owned(
                execution_index=index,
                mode="production",
                future_authority=authority,
                timeout_seconds=watchdog,
            )
            if not outcome.accepted:
                raise TransportRejected("production block did not produce accepted evidence")
        first, second = self.records
        return first, second

    def _dispatch_owned(
        self,
        *,
        execution_index: int,
        mode: str,
        future_authority: Mapping[str, Any] | None,
        timeout_seconds: float,
    ) -> AttemptOutcome:
        if execution_index not in {1, 2}:
            raise TransportRejected("execution index invalid")
        if self._active_index is not None:
            raise TransportRejected("single-active-attempt contract violated")
        if execution_index in self._attempted:
            raise TransportRejected("attempt index was already consumed; retry forbidden")
        records = self.records
        if execution_index != len(records) + 1:
            raise TransportRejected("block order or predecessor acceptance is incomplete")
        if mode == "review_only_preloader_stop" and execution_index != 1:
            raise TransportRejected("review boundary is fixed to block 0008")
        self._attempted.add(execution_index)
        self._active_index = execution_index
        try:
            try:
                return self._spawn_read_validate_append(
                    execution_index=execution_index,
                    mode=mode,
                    future_authority=future_authority,
                    timeout_seconds=timeout_seconds,
                )
            except TransportRejected:
                raise
            except Exception as exc:
                raise TransportRejected(
                    "controller-owned attempt failed without acceptance"
                ) from exc
        finally:
            self._active_index = None

    def _spawn_read_validate_append(
        self,
        *,
        execution_index: int,
        mode: str,
        future_authority: Mapping[str, Any] | None,
        timeout_seconds: float,
    ) -> AttemptOutcome:
        config = _load_config()
        controller_read, worker_write = os.pipe()
        worker_read, controller_write = os.pipe()
        process: subprocess.Popen[Any] | None = None
        child_create_ns: int | None = None
        worker_read_authority = worker_read
        worker_write_authority = worker_write
        if os.name == "nt":
            import msvcrt

            worker_read_authority = msvcrt.get_osfhandle(worker_read)
            worker_write_authority = msvcrt.get_osfhandle(worker_write)
        try:
            process = _spawn_exact(
                config, worker_read_authority, worker_write_authority
            )
            os.close(worker_read)
            worker_read = -1
            os.close(worker_write)
            worker_write = -1
            deadline = time.monotonic() + timeout_seconds
            _hello_bytes, hello = _threaded_call(
                process,
                lambda: _read_frame(controller_read, "worker HELLO"),
                deadline=deadline,
                label="worker HELLO",
            )
            child_create_ns = _validate_hello(hello, process, config)
            envelope = _build_envelope(
                config=config,
                session_id=self._session_id,
                records=self.records,
                process=process,
                child_create_ns=child_create_ns,
                read_handle=worker_read_authority,
                ack_handle=worker_write_authority,
                execution_index=execution_index,
                mode=mode,
                future_authority=future_authority,
            )
            envelope_bytes = _threaded_call(
                process,
                lambda: _write_frame(controller_write, envelope),
                deadline=deadline,
                label="controller envelope",
            )
            os.close(controller_write)
            controller_write = -1
            ack_bytes, _ack = _threaded_call(
                process,
                lambda: _read_frame(controller_read, "worker ACK"),
                deadline=deadline,
                label="worker ACK",
            )
            source, source_bytes, scientific_bytes, certificate_bytes = _validate_ack(
                ack_bytes,
                envelope_bytes=envelope_bytes,
                envelope=envelope,
                process=process,
                child_create_ns=child_create_ns,
                config=config,
            )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("worker exit exceeded watchdog")
            try:
                exit_code = process.wait(timeout=remaining)
            except subprocess.TimeoutExpired as exc:
                raise TimeoutError("worker exit exceeded watchdog") from exc
            expected_exit = 0 if source["accepted"] is True else 4
            if exit_code != expected_exit:
                raise TransportRejected("worker exit/status semantics drifted")
            if source["accepted"] is True:
                predecessor = (
                    self._records[-1].accepted_record_digest
                    if self._records
                    else None
                )
                provisional = AcceptedRecord(
                    schema=RECORD_SCHEMA,
                    block_id=str(envelope["block_id"]),
                    execution_index=execution_index,
                    nonce=str(envelope["nonce"]),
                    child_pid=process.pid,
                    child_create_time_ns=child_create_ns,
                    envelope_sha256=hashlib.sha256(envelope_bytes).hexdigest(),
                    ack_sha256=hashlib.sha256(ack_bytes).hexdigest(),
                    source_sha256=hashlib.sha256(source_bytes).hexdigest(),
                    scientific_payload_sha256=hashlib.sha256(
                        scientific_bytes
                    ).hexdigest(),
                    certificate_inventory_sha256=hashlib.sha256(
                        certificate_bytes
                    ).hexdigest(),
                    predecessor_accepted_digest=predecessor,
                    controller_session_id=self._session_id,
                    controller_mac="",
                    accepted_record_digest="",
                )
                digest = _record_digest(provisional)
                mac = hmac.new(
                    self._secret,
                    f"{self._session_id}:{digest}".encode("ascii"),
                    hashlib.sha256,
                ).hexdigest()
                record = dataclasses.replace(
                    provisional,
                    controller_mac=mac,
                    accepted_record_digest=digest,
                )
                candidate = (*self._records, record)
                _verify_history(
                    candidate,
                    session_id=self._session_id,
                    secret=self._secret,
                )
                self._records = candidate
            return AttemptOutcome(
                block_id=str(envelope["block_id"]),
                execution_index=execution_index,
                status=str(source["status"]),
                accepted=bool(source["accepted"]),
                child_pid=process.pid,
                child_create_time_ns=child_create_ns,
                envelope_sha256=hashlib.sha256(envelope_bytes).hexdigest(),
                ack_sha256=hashlib.sha256(ack_bytes).hexdigest(),
                source_sha256=hashlib.sha256(source_bytes).hexdigest(),
                counters=MappingProxyType(dict(source["counters"])),
                mathematical_infeasibility_inferred=False,
            )
        finally:
            for descriptor in (controller_read, worker_write, worker_read, controller_write):
                if descriptor >= 0:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass
            if process is not None and process.poll() is None:
                if child_create_ns is None:
                    child_create_ns = _process_creation_time_ns(process.pid)
                _terminate_owned_child(
                    process,
                    expected_pid=process.pid,
                    expected_create_ns=child_create_ns,
                )


def _strict_artifact_bytes(path: Path, label: str) -> bytes:
    candidate = Path(path)
    if not candidate.is_absolute() or any(part in {".", ".."} for part in candidate.parts):
        raise TransportRejected(f"{label} path is not canonical absolute")
    current = Path(candidate.anchor)
    for part in candidate.parts[1:]:
        current /= part
        try:
            metadata = os.lstat(current)
        except OSError as exc:
            raise TransportRejected(f"{label} path unreadable") from exc
        attributes = int(getattr(metadata, "st_file_attributes", 0))
        if stat.S_ISLNK(metadata.st_mode) or attributes & 0x400:
            raise TransportRejected(f"{label} path alias/reparse rejected")
    if not stat.S_ISREG(os.lstat(candidate).st_mode):
        raise TransportRejected(f"{label} must be an ordinary file")
    try:
        return candidate.read_bytes()
    except OSError as exc:
        raise TransportRejected(f"{label} unreadable") from exc


def _strict_receipt(path: Path, label: str) -> tuple[dict[str, Any], str]:
    raw = _strict_artifact_bytes(path, label)
    return _json_bytes(raw, label), hashlib.sha256(raw).hexdigest()


def _load_future_authority(
    *,
    activation_review_receipt: Path,
    wrapper_review_receipt: Path,
    dispatch_authorization_receipt: Path,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    review, review_hash = _strict_receipt(
        activation_review_receipt, "activation review receipt"
    )
    wrapper, wrapper_hash = _strict_receipt(
        wrapper_review_receipt, "wrapper review receipt"
    )
    dispatch, _dispatch_hash = _strict_receipt(
        dispatch_authorization_receipt, "dispatch authorization receipt"
    )
    schemas = config["future_execution_authority"]["required_receipt_schemas"]
    expected_effect = config["future_activation_review"]["expected_effect"]
    outer_hash = _sha256(V3_OUTER)
    user_hash = str(config["predecessor_authority"]["user_authorization_sha256"])
    wrapper_binding = wrapper.get("execution_wrapper")
    if not isinstance(wrapper_binding, dict):
        raise TransportRejected("future execution wrapper binding malformed")
    wrapper_path = Path(str(wrapper_binding.get("path")))
    observed_wrapper_hash = hashlib.sha256(
        _strict_artifact_bytes(wrapper_path, "execution wrapper")
    ).hexdigest()
    if (
        review.get("schema") != schemas["activation_review_receipt"]
        or review.get("verdict") != "PASS"
        or review.get("effect") != expected_effect
        or review.get("reviewed_outer")
        != {
            "path": "configs/rq2_public_grid_two_block_pilot_activation_transport_v3.OUTER.SHA256SUMS.json",
            "sha256": outer_hash,
        }
        or wrapper.get("schema") != schemas["wrapper_review_receipt"]
        or wrapper.get("verdict") != "PASS"
        or wrapper.get("activation_review_receipt_sha256") != review_hash
        or wrapper.get("reviewed_activation_outer_sha256") != outer_hash
        or set(wrapper_binding) != {"path", "sha256"}
        or wrapper_binding.get("sha256") != observed_wrapper_hash
        or dispatch.get("schema") != schemas["dispatch_authorization_receipt"]
        or dispatch.get("wrapper_review_receipt_sha256") != wrapper_hash
        or dispatch.get("activation_review_receipt_sha256") != review_hash
        or dispatch.get("reviewed_activation_outer_sha256") != outer_hash
        or dispatch.get("execution_wrapper_sha256") != observed_wrapper_hash
        or dispatch.get("user_authorization_sha256") != user_hash
        or dispatch.get("human_dispatch_review_passed") is not True
        or dispatch.get("two_block_pilot_execution_authorized") is not True
        or dispatch.get("formal_execution_authorized") is not False
    ):
        raise TransportRejected("future receipt chain is absent, malformed, or overbroad")
    return {
        "activation_review_receipt": review,
        "wrapper_review_receipt": wrapper,
        "dispatch_authorization_receipt": dispatch,
        "activation_outer_sha256": outer_hash,
        "activation_review_receipt_sha256": review_hash,
        "wrapper_review_receipt_sha256": wrapper_hash,
        "dispatch_authorization_receipt_sha256": _dispatch_hash,
        "user_authorization_sha256": user_hash,
    }
