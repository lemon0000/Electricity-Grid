"""Sealed activation-v3 production-worker entry.

The candidate is execution-closed.  Its review-only authority performs the
real production-worker pipe handshake and stops before importing scientific
code.  A future independently reviewed wrapper and dispatch receipt may select
the scientific branch; this module never calls predecessor dispatch/worker
entrypoints.
"""

from __future__ import annotations

import argparse
import base64
import ctypes
import hashlib
import json
import os
import stat
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(r"D:\CUHKSZ\Research Project\electricity-grid")
MODULE = "experiments.worker_rq2_public_grid_two_block_pilot_activation_transport_v3"
CONTROLLER_MODULE = (
    "experiments.run_rq2_public_grid_two_block_pilot_activation_transport_v3"
)
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_activation_transport_v3.json"
PRODUCTION_DISPATCH_PERMITTED = False
BLOCKS = ("holdout_s20260822_0008", "holdout_s20260822_0009")

HELLO_SCHEMA = "rq2_public_grid_activation_transport_worker_hello_v3"
ENVELOPE_SCHEMA = "rq2_public_grid_activation_transport_envelope_v3"
ACK_SCHEMA = "rq2_public_grid_activation_transport_worker_ack_v3"
SOURCE_SCHEMA = "rq2_public_grid_activation_transport_worker_source_v3"
MAX_FRAME_BYTES = 64 * 1024 * 1024


class WorkerRejected(RuntimeError):
    """Fail-closed worker rejection."""


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
        raise WorkerRejected(f"authority unreadable: {path}") from exc
    return digest.hexdigest()


def _load_config() -> dict[str, Any]:
    try:
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WorkerRejected("activation-v3 config unreadable") from exc
    if (
        not isinstance(payload, dict)
        or payload.get("schema")
        != "rq2_public_grid_two_block_pilot_activation_transport_v3"
        or payload.get("status") != "activation_transport_v3_candidate_closed"
    ):
        raise WorkerRejected("activation-v3 config identity drifted")
    return payload


def _process_creation_time_ns(pid: int) -> int:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise WorkerRejected("process PID is invalid")
    if os.name != "nt":
        try:
            return os.stat(f"/proc/{pid}", follow_symlinks=False).st_ctime_ns
        except OSError as exc:
            raise WorkerRejected("process creation identity unavailable") from exc

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
        raise WorkerRejected("process creation identity unavailable")
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
            raise WorkerRejected("process creation identity unavailable")
    finally:
        kernel32.CloseHandle(handle)
    return creation.ticks * 100


def _require_pipe(descriptor: int, label: str, *, writable: bool) -> None:
    if isinstance(descriptor, bool) or not isinstance(descriptor, int) or descriptor < 0:
        raise WorkerRejected(f"{label} descriptor is invalid")
    if os.name == "nt":
        import msvcrt

        handle = msvcrt.get_osfhandle(descriptor)
        if ctypes.windll.kernel32.GetFileType(handle) != 3:  # type: ignore[attr-defined]
            raise WorkerRejected(f"{label} is not a pipe")
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
            raise WorkerRejected(f"{label} has wrong pipe direction")
        return
    if not stat.S_ISFIFO(os.fstat(descriptor).st_mode):
        raise WorkerRejected(f"{label} is not an anonymous pipe")


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
        raise WorkerRejected(f"{label} frame size rejected")
    raw = _read_exact(descriptor, size)
    try:
        payload = json.loads(raw.decode("ascii"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise WorkerRejected(f"{label} is not JSON") from exc
    if not isinstance(payload, dict) or _canonical_bytes(payload) != raw:
        raise WorkerRejected(f"{label} canonical bytes drifted")
    return raw, payload


def _write_frame(descriptor: int, payload: Mapping[str, Any]) -> bytes:
    raw = _canonical_bytes(dict(payload))
    frame = len(raw).to_bytes(8, "big") + raw
    offset = 0
    while offset < len(frame):
        written = os.write(descriptor, frame[offset:])
        if written <= 0:
            raise WorkerRejected("frame write failed")
        offset += written
    return raw


def _require_bounded_eof(descriptor: int, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    if os.name == "nt":
        import msvcrt

        handle = msvcrt.get_osfhandle(descriptor)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        while time.monotonic() < deadline:
            available = ctypes.c_ulong(0)
            ctypes.set_last_error(0)
            ok = kernel32.PeekNamedPipe(
                handle, None, 0, None, ctypes.byref(available), None
            )
            if ok and available.value:
                raise WorkerRejected("trailing or replay capability bytes rejected")
            if not ok:
                error = ctypes.get_last_error()
                if error in {109, 232}:  # broken/no-data pipe after writer close
                    return
                raise WorkerRejected("capability EOF status unavailable")
            time.sleep(0.005)
        raise WorkerRejected("capability EOF timeout")
    import select

    ready, _, _ = select.select([descriptor], [], [], timeout_seconds)
    if not ready:
        raise WorkerRejected("capability EOF timeout")
    if os.read(descriptor, 1) != b"":
        raise WorkerRejected("trailing or replay capability bytes rejected")


def _expected_orig_argv(read_handle: int, ack_handle: int) -> list[str]:
    config = _load_config()
    python = str(config["bootstrap_contract"]["locked_python_executable"])
    return [
        python,
        "-B",
        "-m",
        MODULE,
        "--internal-production-worker",
        "--read-handle",
        str(read_handle),
        "--ack-handle",
        str(ack_handle),
    ]


def _validate_self_authority(config: Mapping[str, Any]) -> None:
    transport = config.get("transport_contract")
    if not isinstance(transport, dict):
        raise WorkerRejected("transport contract malformed")
    worker_path = ROOT / str(transport.get("worker_path"))
    controller_path = ROOT / str(transport.get("controller_path"))
    if (
        worker_path != Path(__file__).resolve()
        or _sha256(worker_path) != transport.get("worker_sha256")
        or _sha256(controller_path) != transport.get("controller_sha256")
        or Path.cwd().resolve() != ROOT
    ):
        raise WorkerRejected("sealed module/cwd authority drifted")


def _validate_envelope(
    envelope: Mapping[str, Any],
    *,
    config: Mapping[str, Any],
    read_handle: int,
    ack_handle: int,
) -> None:
    expected_keys = {
        "schema",
        "mode",
        "block_id",
        "execution_index",
        "nonce",
        "issued_ns",
        "controller_session_id",
        "predecessor_accepted_digest",
        "ledger_digest_before",
        "parent_pid",
        "parent_create_time_ns",
        "worker_pid",
        "worker_create_time_ns",
        "worker_command",
        "read_handle",
        "ack_handle",
        "working_directory",
        "sanitized_environment",
        "controller_path",
        "controller_sha256",
        "worker_path",
        "worker_sha256",
        "config_path",
        "config_sha256",
        "activation_v2_outer_sha256",
        "activation_v2_escalate_sha256",
        "future_authority",
    }
    index = envelope.get("execution_index")
    if (
        set(envelope) != expected_keys
        or envelope.get("schema") != ENVELOPE_SCHEMA
        or envelope.get("mode") not in {"review_only_preloader_stop", "production"}
        or isinstance(index, bool)
        or not isinstance(index, int)
        or index not in {1, 2}
        or envelope.get("block_id") != BLOCKS[index - 1]
        or envelope.get("read_handle") != read_handle
        or envelope.get("ack_handle") != ack_handle
    ):
        raise WorkerRejected("worker envelope schema/block/handle drifted")
    transport = config["transport_contract"]
    expected_command = _expected_orig_argv(read_handle, ack_handle)
    if (
        list(sys.orig_argv) != expected_command
        or envelope.get("worker_command") != expected_command
        or envelope.get("worker_pid") != os.getpid()
        or envelope.get("worker_create_time_ns")
        != _process_creation_time_ns(os.getpid())
        or envelope.get("parent_pid") != os.getppid()
        or envelope.get("parent_create_time_ns")
        != _process_creation_time_ns(os.getppid())
        or envelope.get("working_directory") != str(ROOT)
        or envelope.get("sanitized_environment") != dict(os.environ)
        or envelope.get("controller_path")
        != str(ROOT / str(transport["controller_path"]))
        or envelope.get("controller_sha256") != transport["controller_sha256"]
        or envelope.get("worker_path") != str(ROOT / str(transport["worker_path"]))
        or envelope.get("worker_sha256") != transport["worker_sha256"]
        or envelope.get("config_path") != str(CONFIG)
        or envelope.get("config_sha256") != _sha256(CONFIG)
        or envelope.get("activation_v2_outer_sha256")
        != config["predecessor_authority"]["activation_v2_outer_sha256"]
        or envelope.get("activation_v2_escalate_sha256")
        != config["predecessor_authority"]["activation_v2_escalate_sha256"]
    ):
        raise WorkerRejected("worker process/module/environment authority drifted")
    nonce = envelope.get("nonce")
    if (
        not isinstance(nonce, str)
        or len(nonce) != 64
        or any(character not in "0123456789abcdef" for character in nonce)
    ):
        raise WorkerRejected("worker nonce malformed")
    if envelope.get("mode") == "review_only_preloader_stop":
        if (
            config["review_boundary"]["enabled"] is not True
            or envelope.get("future_authority") is not None
            or index != 1
            or envelope.get("predecessor_accepted_digest") is not None
        ):
            raise WorkerRejected("review-only preloader authority drifted")
    else:
        _verify_future_authority(envelope.get("future_authority"), config)


def _verify_future_authority(value: object, config: Mapping[str, Any]) -> None:
    if not isinstance(value, dict):
        raise WorkerRejected("future execution authority absent")
    expected = config["future_execution_authority"]["required_receipt_schemas"]
    if set(value) != {
        "activation_review_receipt",
        "wrapper_review_receipt",
        "dispatch_authorization_receipt",
        "activation_outer_sha256",
        "activation_review_receipt_sha256",
        "wrapper_review_receipt_sha256",
        "dispatch_authorization_receipt_sha256",
        "user_authorization_sha256",
    }:
        raise WorkerRejected("future execution authority inventory drifted")
    for key, schema in expected.items():
        receipt = value.get(key)
        if not isinstance(receipt, dict) or receipt.get("schema") != schema:
            raise WorkerRejected("future execution receipt malformed")
    if value["activation_review_receipt"]["effect"] != config[
        "future_activation_review"
    ]["expected_effect"]:
        raise WorkerRejected("activation review overauthorizes execution")
    dispatch = value["dispatch_authorization_receipt"]
    wrapper = value["wrapper_review_receipt"]
    review = value["activation_review_receipt"]
    if (
        review.get("reviewed_outer", {}).get("sha256")
        != value["activation_outer_sha256"]
        or wrapper.get("reviewed_activation_outer_sha256")
        != value["activation_outer_sha256"]
        or wrapper.get("activation_review_receipt_sha256")
        != value["activation_review_receipt_sha256"]
        or dispatch.get("reviewed_activation_outer_sha256")
        != value["activation_outer_sha256"]
        or dispatch.get("activation_review_receipt_sha256")
        != value["activation_review_receipt_sha256"]
        or dispatch.get("wrapper_review_receipt_sha256")
        != value["wrapper_review_receipt_sha256"]
        or dispatch.get("user_authorization_sha256")
        != value["user_authorization_sha256"]
        or dispatch.get("human_dispatch_review_passed") is not True
        or dispatch.get("two_block_pilot_execution_authorized") is not True
        or dispatch.get("formal_execution_authorized") is not False
    ):
        raise WorkerRejected("dispatch authority is not exact")


def _certificate_inventory(payload: Mapping[str, Any]) -> dict[str, Any]:
    outcomes = payload.get("outcomes")
    if not isinstance(outcomes, list):
        raise WorkerRejected("scientific outcomes missing")
    return {
        "baseline_audit": payload.get("baseline_audit"),
        "hourly": [
            {
                "primary_certificate": outcome.get("primary_certificate"),
                "zero_dc_confirmation_certificate": outcome.get(
                    "zero_dc_confirmation_certificate"
                ),
            }
            for outcome in outcomes
            if isinstance(outcome, dict)
        ],
    }


def _run_sealed_scientific_block(
    block_id: str, config: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, int]]:
    authority = config["sealed_scientific_primitive_authority"]
    for path_key, hash_key in (
        ("v4_runner_path", "v4_runner_sha256"),
        ("v7_outer_path", "v7_outer_sha256"),
        ("v7_review_pass_path", "v7_review_pass_sha256"),
    ):
        if _sha256(ROOT / str(authority[path_key])) != authority[hash_key]:
            raise WorkerRejected("sealed scientific primitive authority drifted")
    from experiments import run_rq2_public_grid_two_block_pilot_candidate_v4 as v4

    context = v4._stage_context()
    data = v4._load_worker_data(context)
    payload = v4.recovery.v4._process_block(
        data,
        context["blocks"][block_id],
        dc_bus=int(context["config"]["model"]["dc_bus"]),
        dc_demand_mw=float(
            context["config"]["model"]["dc_reference_demand_mw"]
        ),
        solver=context["config"]["solver"],
    )
    validated = v4.recovery._validate_scientific_payload(
        payload,
        block_id=block_id,
        expected_block=context["blocks"][block_id],
        config=context["config"],
    )
    inventory = _certificate_inventory(validated)
    solver_calls = 1 + len(inventory["hourly"]) + sum(
        row["zero_dc_confirmation_certificate"] is not None
        for row in inventory["hourly"]
    )
    return validated, {
        "scientific_loader_calls": 1,
        "solver_calls": solver_calls,
        "result_writes": 0,
        "formal_writes": 0,
    }


def _source_for_envelope(
    envelope: Mapping[str, Any], config: Mapping[str, Any]
) -> tuple[bytes, bytes, bytes]:
    if envelope["mode"] == "review_only_preloader_stop":
        scientific_bytes = b""
        certificate_bytes = b""
        counters = {
            "scientific_loader_calls": 0,
            "solver_calls": 0,
            "result_writes": 0,
            "formal_writes": 0,
        }
        status = "NON_ACCEPTED_PRELOADER_BOUNDARY"
        accepted = False
        resolved: bool | None = None
    else:
        payload, counters = _run_sealed_scientific_block(
            str(envelope["block_id"]), config
        )
        scientific_bytes = _canonical_bytes(payload)
        certificate_bytes = _canonical_bytes(_certificate_inventory(payload))
        status = "ACCEPTED_COMPLETE"
        accepted = True
        resolved = True
    source = {
        "schema": SOURCE_SCHEMA,
        "status": status,
        "accepted": accepted,
        "unlock_successor": accepted,
        "block_id": envelope["block_id"],
        "execution_index": envelope["execution_index"],
        "nonce": envelope["nonce"],
        "envelope_sha256": _canonical_sha256(dict(envelope)),
        "scientific_payload_sha256": (
            hashlib.sha256(scientific_bytes).hexdigest() if scientific_bytes else None
        ),
        "certificate_inventory_sha256": (
            hashlib.sha256(certificate_bytes).hexdigest() if certificate_bytes else None
        ),
        "all_hours_resolved": resolved,
        "termination": "preloader_stop" if not accepted else "complete",
        "counters": counters,
        "mathematical_infeasibility_inferred": False,
    }
    return _canonical_bytes(source), scientific_bytes, certificate_bytes


def _worker(
    read_descriptor: int,
    ack_descriptor: int,
    *,
    read_handle: int,
    ack_handle: int,
) -> int:
    _require_pipe(read_descriptor, "controller-to-worker", writable=False)
    _require_pipe(ack_descriptor, "worker-to-controller", writable=True)
    config = _load_config()
    _validate_self_authority(config)
    hello = {
        "schema": HELLO_SCHEMA,
        "worker_pid": os.getpid(),
        "worker_parent_pid": os.getppid(),
        "worker_create_time_ns": _process_creation_time_ns(os.getpid()),
        "worker_module": MODULE,
        "worker_sha256": _sha256(Path(__file__).resolve()),
        "config_sha256": _sha256(CONFIG),
    }
    _write_frame(ack_descriptor, hello)
    envelope_bytes, envelope = _read_frame(read_descriptor, "production envelope")
    _require_bounded_eof(
        read_descriptor, float(config["review_boundary"]["eof_timeout_seconds"])
    )
    _validate_envelope(
        envelope, config=config, read_handle=read_handle, ack_handle=ack_handle
    )
    source_bytes, scientific_bytes, certificate_bytes = _source_for_envelope(
        envelope, config
    )
    source = json.loads(source_bytes)
    ack = {
        "schema": ACK_SCHEMA,
        "status": source["status"],
        "accepted": source["accepted"],
        "block_id": envelope["block_id"],
        "execution_index": envelope["execution_index"],
        "nonce": envelope["nonce"],
        "envelope_sha256": hashlib.sha256(envelope_bytes).hexdigest(),
        "worker_pid": os.getpid(),
        "worker_create_time_ns": _process_creation_time_ns(os.getpid()),
        "bounded_eof_verified_before_ack": True,
        "source_base64": base64.b64encode(source_bytes).decode("ascii"),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "scientific_payload_base64": base64.b64encode(scientific_bytes).decode(
            "ascii"
        ),
        "certificate_inventory_base64": base64.b64encode(
            certificate_bytes
        ).decode("ascii"),
        "counters": source["counters"],
    }
    _write_frame(ack_descriptor, ack)
    return 0 if source["accepted"] else 4


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--internal-production-worker", action="store_true", help=argparse.SUPPRESS
    )
    parser.add_argument("--read-handle", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--ack-handle", type=int, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if (
        not args.internal_production_worker
        or args.read_handle is None
        or args.ack_handle is None
    ):
        raise WorkerRejected("public worker invocation is forbidden")
    read_handle = int(args.read_handle)
    ack_handle = int(args.ack_handle)
    read_descriptor = read_handle
    ack_descriptor = ack_handle
    if os.name == "nt":
        import msvcrt

        read_descriptor = msvcrt.open_osfhandle(read_handle, os.O_RDONLY)
        ack_descriptor = msvcrt.open_osfhandle(ack_handle, os.O_WRONLY)
    return _worker(
        read_descriptor,
        ack_descriptor,
        read_handle=read_handle,
        ack_handle=ack_handle,
    )


if __name__ == "__main__":
    raise SystemExit(main())
