"""Execution-successor v1 worker with a real pre-loader review boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v1.json"
REVIEW_RECEIPT = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_review_pass_v1.json"
MODULE = "experiments.worker_rq2_public_grid_two_block_pilot_execution_controller_successor_v1"
CONTROLLER_MODULE = "experiments.run_rq2_public_grid_two_block_pilot_execution_controller_successor_v1"
MAX_FRAME = 256 * 1024 * 1024
EXECUTION_REVIEW_REQUIRED = True


class SuccessorWorkerRejected(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _read_exact(descriptor: int, count: int) -> bytes:
    chunks: list[bytes] = []
    remaining = count
    while remaining:
        chunk = os.read(descriptor, remaining)
        if not chunk:
            raise SuccessorWorkerRejected("controller pipe closed early")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_frame(descriptor: int) -> tuple[bytes, dict[str, Any]]:
    size = int.from_bytes(_read_exact(descriptor, 8), "big")
    if size <= 0 or size > MAX_FRAME:
        raise SuccessorWorkerRejected("controller frame length invalid")
    payload = _read_exact(descriptor, size)
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SuccessorWorkerRejected("controller frame JSON invalid") from exc
    if not isinstance(value, dict):
        raise SuccessorWorkerRejected("controller frame is not an object")
    return payload, value


def _write_frame(descriptor: int, value: object) -> bytes:
    payload = _canonical_bytes(value)
    frame = len(payload).to_bytes(8, "big") + payload
    offset = 0
    while offset < len(frame):
        offset += os.write(descriptor, frame[offset:])
    return payload


def _require_eof(descriptor: int) -> None:
    if os.name == "nt":
        import ctypes
        import msvcrt

        available = ctypes.c_ulong(0)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        ctypes.set_last_error(0)
        if not kernel.PeekNamedPipe(
            msvcrt.get_osfhandle(descriptor),
            None,
            0,
            None,
            ctypes.byref(available),
            None,
        ):
            error = ctypes.get_last_error()
            if error != 109:
                raise SuccessorWorkerRejected("EOF observation failed")
            return
        if available.value:
            raise SuccessorWorkerRejected("trailing capability bytes rejected")
        return
    if os.read(descriptor, 1) != b"":
        raise SuccessorWorkerRejected("trailing capability bytes rejected")


def _load_config() -> dict[str, Any]:
    try:
        value = json.loads(CONFIG.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise SuccessorWorkerRejected("successor config unreadable") from exc
    if not isinstance(value, dict) or value.get("status") != "execution_controller_successor_v1_review_closed":
        raise SuccessorWorkerRejected("successor config drifted")
    return value


def _strict_fixed_receipt() -> tuple[dict[str, Any], str]:
    current = Path(REVIEW_RECEIPT.anchor)
    for part in REVIEW_RECEIPT.parts[1:]:
        current /= part
        try:
            metadata = os.lstat(current)
        except OSError as exc:
            raise SuccessorWorkerRejected("fixed execution receipt absent") from exc
        attributes = int(getattr(metadata, "st_file_attributes", 0))
        if stat.S_ISLNK(metadata.st_mode) or attributes & 0x400:
            raise SuccessorWorkerRejected("fixed execution receipt alias rejected")
    first = REVIEW_RECEIPT.read_bytes()
    second = REVIEW_RECEIPT.read_bytes()
    if first != second:
        raise SuccessorWorkerRejected("fixed execution receipt changed during read")
    try:
        value = json.loads(first)
    except json.JSONDecodeError as exc:
        raise SuccessorWorkerRejected("fixed execution receipt malformed") from exc
    if not isinstance(value, dict):
        raise SuccessorWorkerRejected("fixed execution receipt is not an object")
    return value, hashlib.sha256(first).hexdigest()


def _process_creation_time_ns(pid: int) -> int:
    from experiments import (
        run_rq2_public_grid_two_block_pilot_activation_transport_v5 as v5,
    )

    return v5.predecessor._process_creation_time_ns(pid)


def _validate_envelope(
    envelope: Mapping[str, Any], *, config: Mapping[str, Any], read_handle: int, ack_handle: int
) -> None:
    parent_identity = envelope.get("parent_process_identity")
    worker_identity = envelope.get("worker_process_identity")
    if (
        not isinstance(parent_identity, dict)
        or not isinstance(worker_identity, dict)
        or envelope.get("schema") != "rq2_execution_successor_capability_v1"
        or envelope.get("authority") != config["chain_authority"]
        or envelope.get("parent_pid") != os.getppid()
        or envelope.get("parent_create_time_ns") != _process_creation_time_ns(os.getppid())
        or parent_identity.get("pid") != envelope.get("parent_pid")
        or parent_identity.get("create_time_ns")
        != envelope.get("parent_create_time_ns")
        or envelope.get("worker_pid") != os.getpid()
        or envelope.get("worker_create_time_ns") != _process_creation_time_ns(os.getpid())
        or worker_identity.get("pid") != envelope.get("worker_pid")
        or worker_identity.get("create_time_ns")
        != envelope.get("worker_create_time_ns")
        or envelope.get("working_directory") != str(ROOT)
        or str(Path.cwd().resolve()) != str(ROOT)
        or envelope.get("sanitized_environment") != dict(os.environ)
        or envelope.get("controller_sha256") != config["successor_identity"]["controller_sha256"]
        or envelope.get("worker_sha256") != config["successor_identity"]["worker_sha256"]
        or envelope.get("config_sha256") != _sha256(CONFIG)
    ):
        raise SuccessorWorkerRejected("successor envelope process/module authority drifted")
    expected_command = [
        config["runtime"]["locked_python_executable"],
        "-B",
        "-m",
        MODULE,
        "--internal-successor-worker",
        "--read-handle",
        str(read_handle),
        "--ack-handle",
        str(ack_handle),
    ]
    if envelope.get("worker_command") != expected_command:
        raise SuccessorWorkerRejected("successor worker argv authority drifted")
    expected_python = config["runtime"]["locked_python_executable"]
    expected_python_sha256 = config["runtime"]["locked_python_sha256"]
    if (
        worker_identity.get("command") != expected_command
        or worker_identity.get("executable_path") != expected_python
        or worker_identity.get("executable_sha256") != expected_python_sha256
        or parent_identity.get("executable_path") != expected_python
        or parent_identity.get("executable_sha256") != expected_python_sha256
        or not isinstance(parent_identity.get("command"), list)
        or not parent_identity["command"]
    ):
        raise SuccessorWorkerRejected("successor process identity authority drifted")
    index = envelope.get("execution_index")
    blocks = config["pilot"]["blocks"]
    if type(index) is not int or index not in {1, 2} or envelope.get("block_id") != blocks[index - 1]:
        raise SuccessorWorkerRejected("successor block/index drifted")
    nonce = envelope.get("nonce")
    if not isinstance(nonce, str) or len(nonce) != 64:
        raise SuccessorWorkerRejected("successor nonce malformed")
    mode = envelope.get("mode")
    if mode == "review_only_preloader_stop":
        if index != 1 or envelope.get("execution_authority") is not None:
            raise SuccessorWorkerRejected("review boundary authority drifted")
        return
    if mode != "production":
        raise SuccessorWorkerRejected("successor mode unregistered")
    expected_parent_command = [
        config["runtime"]["locked_python_executable"],
        "-B",
        "-m",
        config["successor_identity"]["bootstrap_module"],
        "--execute",
    ]
    if parent_identity.get("command") != expected_parent_command:
        raise SuccessorWorkerRejected("production parent is not the reviewed bootstrap")
    receipt, receipt_hash = _strict_fixed_receipt()
    authority = envelope.get("execution_authority")
    if (
        not isinstance(authority, dict)
        or authority.get("receipt") != receipt
        or authority.get("receipt_sha256") != receipt_hash
        or authority.get("successor_outer_sha256")
        != receipt.get("reviewed_outer", {}).get("sha256")
    ):
        raise SuccessorWorkerRejected("production execution authority drifted")


def _certificate_inventory(payload: Mapping[str, Any]) -> dict[str, Any]:
    outcomes = payload.get("outcomes")
    if not isinstance(outcomes, list):
        raise SuccessorWorkerRejected("scientific outcomes missing")
    return {
        "baseline_audit": payload.get("baseline_audit"),
        "hourly": [
            {
                "primary_certificate": row.get("primary_certificate"),
                "zero_dc_confirmation_certificate": row.get(
                    "zero_dc_confirmation_certificate"
                ),
            }
            for row in outcomes
            if isinstance(row, dict)
        ],
    }


def _production(envelope: Mapping[str, Any], config: Mapping[str, Any]) -> int:
    # These are the exact sealed primitives; there is no copied scientific logic.
    from experiments import run_rq2_public_grid_two_block_pilot_candidate_v4 as v4

    context = v4._stage_context()
    block_id = str(envelope["block_id"])
    data = v4._load_worker_data(context)
    payload = v4.recovery.v4._process_block(
        data,
        context["blocks"][block_id],
        dc_bus=int(context["config"]["model"]["dc_bus"]),
        dc_demand_mw=float(context["config"]["model"]["dc_reference_demand_mw"]),
        solver=context["config"]["solver"],
    )
    validated = v4.recovery._validate_scientific_payload(
        payload,
        block_id=block_id,
        expected_block=context["blocks"][block_id],
        config=context["config"],
    )
    result = v4._build_worker_result(envelope, validated)
    inventory = _certificate_inventory(validated)
    result["successor_certificate_inventory"] = inventory
    result["successor_counters"] = {
        "loader_calls": 1,
        "solver_calls": 1 + len(inventory["hourly"]),
        "result_writes": 2,
        "formal_writes": 0,
    }
    payload_path = Path(str(envelope["worker_payload_path"]))
    receipt_path = Path(str(envelope["attempt_receipt_path"]))
    expected_root = ROOT / config["paths"]["worker_root"] / block_id / str(envelope["nonce"])
    if payload_path != expected_root / "payload.json" or receipt_path != expected_root / "attempt_receipt.json":
        raise SuccessorWorkerRejected("successor worker output path drifted")
    payload_path.parent.mkdir(parents=True, exist_ok=False)
    v4.recovery._atomic_json(payload_path, result)
    v4.recovery._atomic_json(receipt_path, v4._build_attempt_receipt(envelope, payload_path))
    return 0 if validated.get("all_hours_resolved") is True else 3


def _worker(read_descriptor: int, ack_descriptor: int, *, read_handle: int, ack_handle: int) -> int:
    config = _load_config()
    hello = {
        "schema": "rq2_execution_successor_worker_hello_v1",
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "create_time_ns": _process_creation_time_ns(os.getpid()),
        "worker_module": MODULE,
        "worker_sha256": _sha256(Path(__file__).resolve()),
        "config_sha256": _sha256(CONFIG),
    }
    _write_frame(ack_descriptor, hello)
    envelope_bytes, envelope = _read_frame(read_descriptor)
    _require_eof(read_descriptor)
    _validate_envelope(envelope, config=config, read_handle=read_handle, ack_handle=ack_handle)
    if envelope["mode"] == "review_only_preloader_stop":
        _write_frame(
            ack_descriptor,
            {
                "schema": "rq2_execution_successor_review_ack_v1",
                "status": "NON_ACCEPTED_PRELOADER_BOUNDARY",
                "accepted": False,
                "envelope_sha256": hashlib.sha256(envelope_bytes).hexdigest(),
                "counters": {
                    "loader_calls": 0,
                    "solver_calls": 0,
                    "result_writes": 0,
                    "formal_writes": 0,
                },
                "mathematical_infeasibility_inferred": False,
            },
        )
        return 4
    exit_code = _production(envelope, config)
    from experiments import run_rq2_public_grid_two_block_pilot_candidate_v4 as v4

    _write_frame(ack_descriptor, v4._build_ack(envelope))
    return exit_code


def _parse(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--internal-successor-worker", action="store_true")
    parser.add_argument("--read-handle", type=int)
    parser.add_argument("--ack-handle", type=int)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse(argv)
    if not args.internal_successor_worker or args.read_handle is None or args.ack_handle is None:
        raise SuccessorWorkerRejected("public/malformed successor worker invocation rejected")
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
