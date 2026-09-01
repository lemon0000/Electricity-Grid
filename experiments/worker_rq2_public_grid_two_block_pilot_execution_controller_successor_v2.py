"""Worker for the review-closed execution-controller successor v2.

The frozen dependency closure is verified before importing any scientific,
resource-monitor, adapter, or publication module.  Review mode stops before
the data loader; production additionally requires the fixed external review
receipt and is unreachable while that receipt is absent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from experiments import rq2_public_grid_execution_dependency_closure_v2 as closure

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v2.json"
OUTER = ROOT / (
    "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v2"
    ".OUTER.SHA256SUMS.json"
)
REVIEW = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_review_pass_v2.json"
MODULE = "experiments.worker_rq2_public_grid_two_block_pilot_execution_controller_successor_v2"
CONTROLLER_MODULE = (
    "experiments.run_rq2_public_grid_two_block_pilot_execution_controller_successor_v2"
)
MAX_FRAME = 256 * 1024 * 1024


class SuccessorV2WorkerRejected(RuntimeError):
    """A fail-closed successor-v2 worker rejection."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(closure.read_stable_bytes(path)).hexdigest()


def _load_config() -> dict[str, Any]:
    try:
        value = json.loads(closure.read_stable_bytes(CONFIG))
    except (closure.ClosureRejected, json.JSONDecodeError) as exc:
        raise SuccessorV2WorkerRejected("successor-v2 config unavailable") from exc
    if (
        not isinstance(value, dict)
        or value.get("status") != "execution_controller_successor_v2_review_closed"
    ):
        raise SuccessorV2WorkerRejected("successor-v2 config identity drifted")
    return value


def verify_live_closure() -> tuple[str, ...]:
    try:
        return closure.verify_dependency_closure(ROOT, _load_config())
    except closure.ClosureRejected as exc:
        raise SuccessorV2WorkerRejected("frozen dependency closure rejected") from exc


def validate_review_receipt_for_entry(
    receipt: object, *, outer_sha256: str
) -> None:
    """Worker-entry receipt seam using the exact common receipt contract."""
    closure.validate_review_receipt_object(
        receipt,
        config=_load_config(),
        outer_relative=OUTER.relative_to(ROOT).as_posix(),
        outer_sha256=outer_sha256,
    )


def _read_exact(descriptor: int, count: int) -> bytes:
    chunks: list[bytes] = []
    while count:
        chunk = os.read(descriptor, count)
        if not chunk:
            raise SuccessorV2WorkerRejected("controller pipe closed early")
        chunks.append(chunk)
        count -= len(chunk)
    return b"".join(chunks)


def _read_frame(descriptor: int) -> tuple[bytes, dict[str, Any]]:
    size = int.from_bytes(_read_exact(descriptor, 8), "big")
    if size <= 0 or size > MAX_FRAME:
        raise SuccessorV2WorkerRejected("controller frame length invalid")
    raw = _read_exact(descriptor, size)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SuccessorV2WorkerRejected("controller frame JSON invalid") from exc
    if not isinstance(value, dict):
        raise SuccessorV2WorkerRejected("controller frame is not an object")
    return raw, value


def _write_frame(descriptor: int, value: object) -> bytes:
    payload = closure.canonical_bytes(value)
    if len(payload) > MAX_FRAME:
        raise SuccessorV2WorkerRejected("worker frame is too large")
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
                raise SuccessorV2WorkerRejected("EOF observation failed")
            return
        if available.value:
            raise SuccessorV2WorkerRejected("trailing capability bytes rejected")
        return
    if os.read(descriptor, 1) != b"":
        raise SuccessorV2WorkerRejected("trailing capability bytes rejected")


def _resource_authority() -> Any:
    from experiments import (
        run_rq2_public_grid_two_block_pilot_activation_transport_v5 as authority,
    )

    return authority


def _process_creation_time_ns(pid: int) -> int:
    return _resource_authority().predecessor._process_creation_time_ns(pid)


def _worker_command(config: Mapping[str, Any], read_handle: int, ack_handle: int) -> list[str]:
    return [
        config["runtime"]["locked_python_executable"],
        "-B",
        "-m",
        MODULE,
        "--internal-successor-v2-worker",
        "--read-handle",
        str(read_handle),
        "--ack-handle",
        str(ack_handle),
    ]


def _validate_envelope(
    envelope: Mapping[str, Any],
    *,
    config: Mapping[str, Any],
    read_handle: int,
    ack_handle: int,
) -> None:
    parent = envelope.get("parent_process_identity")
    worker = envelope.get("worker_process_identity")
    identity = config["successor_identity"]
    expected_command = _worker_command(config, read_handle, ack_handle)
    if (
        envelope.get("schema") != "rq2_execution_controller_successor_capability_v2"
        or envelope.get("authority") != closure.closure_binding(config)
        or not isinstance(parent, dict)
        or not isinstance(worker, dict)
        or parent.get("pid") != os.getppid()
        or parent.get("create_time_ns") != _process_creation_time_ns(os.getppid())
        or worker.get("pid") != os.getpid()
        or worker.get("create_time_ns") != _process_creation_time_ns(os.getpid())
        or worker.get("command") != expected_command
        or envelope.get("worker_command") != expected_command
        or envelope.get("working_directory") != str(ROOT)
        or str(Path.cwd()) != str(ROOT)
        or envelope.get("sanitized_environment") != dict(os.environ)
        or envelope.get("controller_sha256") != identity["controller_sha256"]
        or envelope.get("worker_sha256") != identity["worker_sha256"]
        or envelope.get("closure_sha256") != identity["closure_sha256"]
        or envelope.get("config_sha256") != _sha256(CONFIG)
    ):
        raise SuccessorV2WorkerRejected("worker envelope authority drifted")
    expected_python = config["runtime"]["locked_python_executable"]
    expected_python_hash = config["runtime"]["locked_python_sha256"]
    if (
        parent.get("executable_path") != expected_python
        or parent.get("executable_sha256") != expected_python_hash
        or worker.get("executable_path") != expected_python
        or worker.get("executable_sha256") != expected_python_hash
        or not isinstance(parent.get("command"), list)
        or not parent["command"]
    ):
        raise SuccessorV2WorkerRejected("worker process identity drifted")
    index = envelope.get("execution_index")
    blocks = config["pilot"]["blocks"]
    if (
        type(index) is not int
        or index not in {1, 2}
        or envelope.get("block_id") != blocks[index - 1]
    ):
        raise SuccessorV2WorkerRejected("worker block/index authority drifted")
    nonce = envelope.get("nonce")
    if not isinstance(nonce, str) or len(nonce) != 64:
        raise SuccessorV2WorkerRejected("worker nonce malformed")
    mode = envelope.get("mode")
    if mode == "review_only_preloader_stop":
        if index != 1 or envelope.get("execution_authority") is not None:
            raise SuccessorV2WorkerRejected("review-only authority drifted")
        return
    if mode != "production":
        raise SuccessorV2WorkerRejected("worker mode is unregistered")
    expected_parent = [
        expected_python,
        "-B",
        "-m",
        identity["bootstrap_module"],
        "--execute",
    ]
    if parent.get("command") != expected_parent:
        raise SuccessorV2WorkerRejected("production parent is not exact bootstrap")
    try:
        receipt, receipt_sha256 = closure.load_and_validate_review_receipt(
            REVIEW, config=config, outer_path=OUTER, root=ROOT
        )
    except closure.ClosureRejected as exc:
        raise SuccessorV2WorkerRejected("fixed execution review rejected") from exc
    authority = envelope.get("execution_authority")
    if authority != {
        "receipt": receipt,
        "receipt_sha256": receipt_sha256,
        "outer_sha256": _sha256(OUTER),
    }:
        raise SuccessorV2WorkerRejected("execution authority binding drifted")


def solver_call_accounting(payload: Mapping[str, Any]) -> dict[str, int]:
    """Mechanically count actual solver invocations represented by validated payload."""
    baseline = payload.get("baseline_audit")
    outcomes = payload.get("outcomes")
    if not isinstance(baseline, dict) or not isinstance(outcomes, list) or len(outcomes) != 24:
        raise SuccessorV2WorkerRejected("solver accounting inventory malformed")
    baseline_termination = baseline.get("termination_condition")
    if not isinstance(baseline_termination, str) or not baseline_termination:
        raise SuccessorV2WorkerRejected("baseline termination evidence missing")
    baseline_calls = int(baseline_termination != "not_applicable_no_active_outage")
    primary_calls = 0
    confirmation_calls = 0
    for outcome in outcomes:
        if not isinstance(outcome, dict):
            raise SuccessorV2WorkerRejected("hourly outcome malformed")
        primary = outcome.get("primary")
        certificate = outcome.get("primary_certificate")
        if not isinstance(primary, dict) or not isinstance(certificate, dict) or not certificate:
            raise SuccessorV2WorkerRejected("primary evidence incomplete")
        termination = primary.get("termination_condition")
        if not isinstance(termination, str) or not termination:
            raise SuccessorV2WorkerRejected("primary termination evidence missing")
        primary_calls += int(termination != "not_applicable_no_active_outage")
        zero = outcome.get("zero_dc_confirmation")
        zero_certificate = outcome.get("zero_dc_confirmation_certificate")
        if (zero is None) != (zero_certificate is None):
            raise SuccessorV2WorkerRejected("zero-DC solve/certificate pair inconsistent")
        if zero is not None:
            if (
                not isinstance(zero, dict)
                or not isinstance(zero_certificate, dict)
                or not zero_certificate
                or not isinstance(zero.get("termination_condition"), str)
                or not zero["termination_condition"]
            ):
                raise SuccessorV2WorkerRejected("zero-DC evidence malformed")
            confirmation_calls += 1
    return {
        "baseline_solver_calls": baseline_calls,
        "primary_solver_calls": primary_calls,
        "zero_dc_confirmation_solver_calls": confirmation_calls,
        "solver_calls": baseline_calls + primary_calls + confirmation_calls,
    }


def validate_solver_accounting(
    payload: Mapping[str, Any], claimed: Mapping[str, Any]
) -> None:
    if dict(claimed) != solver_call_accounting(payload):
        raise SuccessorV2WorkerRejected("solver-call accounting mismatch")


def production_preloader_closure_gate(loader: Any) -> Any:
    """Test seam: closure verification necessarily precedes the loader callback."""
    verify_live_closure()
    return loader()


def _production(envelope: Mapping[str, Any], config: Mapping[str, Any]) -> int:
    # Closure was verified before this function and is rechecked at the actual loader boundary.
    verify_live_closure()
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
    accounting = solver_call_accounting(validated)
    result = v4._build_worker_result(envelope, validated)
    result["solver_call_accounting"] = accounting
    payload_path = Path(str(envelope["worker_payload_path"]))
    receipt_path = Path(str(envelope["attempt_receipt_path"]))
    expected_root = ROOT / config["paths"]["worker_root"] / block_id / str(envelope["nonce"])
    if (
        payload_path != expected_root / "payload.json"
        or receipt_path != expected_root / "attempt_receipt.json"
    ):
        raise SuccessorV2WorkerRejected("worker output path drifted")
    payload_path.parent.mkdir(parents=True, exist_ok=False)
    v4.recovery._atomic_json(payload_path, result)
    v4.recovery._atomic_json(
        receipt_path, v4._build_attempt_receipt(envelope, payload_path)
    )
    return 0 if validated.get("all_hours_resolved") is True else 3


def _worker(
    read_descriptor: int,
    ack_descriptor: int,
    *,
    read_handle: int,
    ack_handle: int,
) -> int:
    # The full closure is verified before resource/scientific imports and again before loader.
    verify_live_closure()
    config = _load_config()
    hello = {
        "schema": "rq2_execution_controller_successor_worker_hello_v2",
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "create_time_ns": _process_creation_time_ns(os.getpid()),
        "worker_module": MODULE,
        "worker_sha256": _sha256(Path(__file__).resolve()),
        "closure_sha256": _sha256(Path(closure.__file__).resolve()),
        "config_sha256": _sha256(CONFIG),
    }
    _write_frame(ack_descriptor, hello)
    envelope_bytes, envelope = _read_frame(read_descriptor)
    _require_eof(read_descriptor)
    _validate_envelope(
        envelope, config=config, read_handle=read_handle, ack_handle=ack_handle
    )
    if envelope["mode"] == "review_only_preloader_stop":
        _write_frame(
            ack_descriptor,
            {
                "schema": "rq2_execution_controller_successor_review_ack_v2",
                "status": "NON_ACCEPTED_PRELOADER_BOUNDARY",
                "accepted": False,
                "envelope_sha256": hashlib.sha256(envelope_bytes).hexdigest(),
                "counters": {
                    "loader_calls": 0,
                    "solver_calls": 0,
                    "result_writes": 0,
                    "formal_writes": 0,
                },
                "dependency_closure_verified": True,
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
    parser.add_argument("--internal-successor-v2-worker", action="store_true")
    parser.add_argument("--read-handle", type=int)
    parser.add_argument("--ack-handle", type=int)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse(argv)
    if (
        not args.internal_successor_v2_worker
        or args.read_handle is None
        or args.ack_handle is None
    ):
        raise SuccessorV2WorkerRejected("public/malformed worker invocation rejected")
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
