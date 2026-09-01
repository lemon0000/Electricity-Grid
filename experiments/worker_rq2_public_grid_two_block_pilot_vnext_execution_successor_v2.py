"""Internal worker for the review-closed Vnext nonformal pilot successor."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from experiments import (
    rq2_public_grid_two_block_pilot_vnext_execution_contract_v2 as contract,
)


class WorkerRejected(contract.ContractRejected):
    """The internal worker failed closed."""


def _parse(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--internal-review-preloader-worker", action="store_true")
    modes.add_argument("--internal-science-worker", action="store_true")
    parser.add_argument("--read-handle", type=int, required=True)
    parser.add_argument("--ack-handle", type=int, required=True)
    parser.add_argument("--parent-pid", type=int, required=True)
    parser.add_argument("--parent-create-time-ns", type=int, required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--execution-index", type=int, required=True)
    parser.add_argument("--block-id", required=True)
    parser.add_argument("--predecessor-digest", required=True)
    parser.add_argument("--nonce", required=True)
    return parser.parse_args(argv)


def _atomic_source(path: Path, raw: bytes) -> None:
    if path.exists() or path.is_symlink() or not path.parent.is_dir():
        raise WorkerRejected("worker source path appearance/layout rejected")
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _hello(
    *,
    mode: str,
    command: tuple[str, ...],
    parent_identity: dict[str, int],
    worker_read: dict[str, object],
    worker_ack: dict[str, object],
    session_id: str,
    execution_index: int,
    block_id: str,
    predecessor_digest: str | None,
    nonce: str,
) -> dict[str, Any]:
    worker_identity = {
            "pid": os.getpid(),
            "ppid": os.getppid(),
            "create_time_ns": contract.process_create_time_ns(os.getpid()),
    }
    return contract.build_worker_hello(
        mode=mode,
        session_id=session_id,
        execution_index=execution_index,
        block_id=block_id,
        predecessor_digest=predecessor_digest,
        nonce=nonce,
        parent_identity=parent_identity,
        worker_identity=worker_identity,
        command=command,
        worker_read=worker_read,
        worker_ack=worker_ack,
    )


def _validate_envelope(
    value: dict[str, Any],
    *,
    hello: dict[str, Any],
    hello_raw: bytes,
    command: tuple[str, ...],
    worker_read: dict[str, object],
    worker_ack: dict[str, object],
) -> None:
    config = contract.load_config()
    context = hello["transport_context"] if "transport_context" in hello else contract.hello_transport_context(hello)
    expected_attempt = (
        contract.ROOT
        / config["paths"]["worker_root"]
        / str(context["session_id"])
        / str(context["block_id"])
        / str(context["nonce"])
    )
    contract.validate_worker_envelope(
        value,
        hello=hello,
        hello_raw=hello_raw,
        pipe_authority=value.get("pipe_authority"),
        attempt_root=str(expected_attempt),
    )
    if (
        value["pipe_authority"]["worker_read"] != worker_read
        or value["pipe_authority"]["worker_ack"] != worker_ack
        or dict(os.environ) != config["runtime"]["sanitized_environment"]
        or Path.cwd() != contract.ROOT
        or tuple(value["transport_context"]["command"]) != command
    ):
        raise WorkerRejected("worker live cwd/environment drifted")


def _run_science(
    read_descriptor: int,
    ack_descriptor: int,
    *,
    hello: dict[str, Any],
    hello_raw: bytes,
    command: tuple[str, ...],
    worker_read: dict[str, object],
    worker_ack: dict[str, object],
) -> int:
    envelope_raw, envelope = contract.read_frame(read_descriptor, "science envelope")
    contract.require_eof(read_descriptor)
    _validate_envelope(
        envelope,
        hello=hello,
        hello_raw=hello_raw,
        command=command,
        worker_read=worker_read,
        worker_ack=worker_ack,
    )
    payload, accounting = contract.run_actual_science(
        str(envelope["transport_context"]["block_id"])
    )
    result = contract.build_worker_result(
        hello=hello,
        hello_raw=hello_raw,
        envelope=envelope,
        envelope_raw=envelope_raw,
        scientific_payload=payload,
        solver_call_accounting=accounting,
    )
    result_raw = contract.exact_json_bytes(result)
    attempt_root = Path(str(envelope["attempt_root"]))
    attempt_root.mkdir(parents=True, exist_ok=False)
    result_path = attempt_root / "worker_result.json"
    receipt_path = attempt_root / "attempt_receipt.json"
    _atomic_source(result_path, result_raw)
    contract.verify_live_authorities()
    receipt = contract.build_attempt_receipt(
        hello=hello,
        envelope=envelope,
        result=result,
        result_raw=result_raw,
        result_path=str(result_path),
    )
    receipt_raw = contract.exact_json_bytes(receipt)
    _atomic_source(receipt_path, receipt_raw)
    contract.verify_live_authorities()
    ack = contract.build_worker_ack(
        hello=hello,
        envelope=envelope,
        result=result,
        result_raw=result_raw,
        receipt_raw=receipt_raw,
    )
    contract.verify_live_authorities()
    contract.write_frame(ack_descriptor, ack)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse(argv)
    mode = "review-preloader" if args.internal_review_preloader_worker else "science"
    if contract.process_create_time_ns(args.parent_pid) != args.parent_create_time_ns or os.getppid() != args.parent_pid:
        raise WorkerRejected("parent PID/create-time drifted before pipe conversion")
    contract.verify_live_authorities()
    if mode == "science":
        contract.require_execution_review()
    try:
        worker_read = contract.observe_pipe_endpoint(
            args.read_handle,
            role="controller_to_worker",
            direction="read",
            inherited=True,
        )
        worker_ack = contract.observe_pipe_endpoint(
            args.ack_handle,
            role="worker_to_controller",
            direction="write",
            inherited=True,
        )
    except Exception as exc:
        raise WorkerRejected(
            f"worker raw pipe authority rejected: read={args.read_handle}, ack={args.ack_handle}"
        ) from exc
    read_descriptor = args.read_handle
    ack_descriptor = args.ack_handle
    if os.name == "nt":
        import msvcrt

        read_descriptor = msvcrt.open_osfhandle(args.read_handle, os.O_RDONLY)
        ack_descriptor = msvcrt.open_osfhandle(args.ack_handle, os.O_WRONLY)
    command = contract.exact_worker_command(
        mode=mode,
        read_handle=args.read_handle,
        ack_handle=args.ack_handle,
        parent_pid=args.parent_pid,
        parent_create_time_ns=args.parent_create_time_ns,
        session_id=args.session_id,
        execution_index=args.execution_index,
        block_id=args.block_id,
        predecessor_digest=(
            None if args.predecessor_digest == "NONE" else args.predecessor_digest
        ),
        nonce=args.nonce,
    )
    parent_identity = {"pid": args.parent_pid, "create_time_ns": args.parent_create_time_ns}
    predecessor_digest = None if args.predecessor_digest == "NONE" else args.predecessor_digest
    hello = _hello(
        mode=mode,
        command=command,
        parent_identity=parent_identity,
        worker_read=worker_read,
        worker_ack=worker_ack,
        session_id=args.session_id,
        execution_index=args.execution_index,
        block_id=args.block_id,
        predecessor_digest=predecessor_digest,
        nonce=args.nonce,
    )
    try:
        hello_raw = contract.write_frame(ack_descriptor, hello)
        if mode == "review-preloader":
            contract.write_frame(
                ack_descriptor,
                contract.build_preloader_ack(hello=hello, hello_raw=hello_raw),
            )
            return 0
        return _run_science(
            read_descriptor,
            ack_descriptor,
            hello=hello,
            hello_raw=hello_raw,
            command=command,
            worker_read=worker_read,
            worker_ack=worker_ack,
        )
    finally:
        os.close(read_descriptor)
        os.close(ack_descriptor)


if __name__ == "__main__":
    raise SystemExit(main())
