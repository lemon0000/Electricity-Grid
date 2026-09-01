"""Internal worker for Vnext nonformal execution successor v4."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from experiments import (
    rq2_public_grid_two_block_pilot_vnext_execution_contract_v4 as contract,
)


class WorkerRejected(contract.ContractRejected):
    """The internal worker failed closed."""


def _parse(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--internal-review-preloader-worker", action="store_true")
    modes.add_argument("--internal-review-resource-probe-worker", action="store_true")
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


def _mode(args: argparse.Namespace) -> str:
    if args.internal_review_preloader_worker:
        return "review-preloader"
    if args.internal_review_resource_probe_worker:
        return "review-resource-probe"
    return "science"


def _run_science(
    read_descriptor: int,
    ack_descriptor: int,
    *,
    hello: dict[str, Any],
    hello_raw: bytes,
    worker_identity: dict[str, int],
) -> int:
    envelope_raw, envelope = contract.read_frame(read_descriptor, "science envelope")
    contract.require_eof(read_descriptor)
    config = contract.load_config()
    attempt_root = (
        contract.ROOT
        / config["paths"]["worker_root"]
        / hello["session_id"]
        / hello["block_id"]
        / hello["nonce"]
    )
    expected = contract.build_worker_envelope(
        hello=hello,
        hello_raw=hello_raw,
        pipe_authority=envelope.get("pipe_authority"),
        attempt_root=str(attempt_root),
    )
    contract.require_exact(envelope, expected, label="science envelope")
    if envelope["first_same_pair_resource_sample_succeeded_before_envelope"] is not True:
        raise WorkerRejected("science envelope preceded the resource first-sample gate")
    runtime = contract.collect_solver_runtime_evidence(worker_identity)
    payload, accounting = contract.run_actual_science(hello["block_id"])
    result = contract.build_worker_result(
        hello=hello,
        hello_raw=hello_raw,
        envelope=envelope,
        envelope_raw=envelope_raw,
        scientific_payload=payload,
        solver_call_accounting=accounting,
        solver_runtime_evidence=runtime,
    )
    result_raw = contract.exact_json_bytes(result)
    attempt_root.mkdir(parents=True, exist_ok=False)
    result_path = attempt_root / "worker_result.json"
    _atomic_source(result_path, result_raw)
    contract.verify_live_authorities()
    notice = contract.build_worker_exit_notice(
        hello=hello,
        envelope=envelope,
        result=result,
        result_raw=result_raw,
        result_path=str(result_path),
    )
    contract.write_frame(ack_descriptor, notice)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse(argv)
    mode = _mode(args)
    if (
        contract.process_create_time_ns(args.parent_pid) != args.parent_create_time_ns
        or os.getppid() != args.parent_pid
    ):
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
        raise WorkerRejected("worker raw pipe authority rejected") from exc
    read_descriptor = args.read_handle
    ack_descriptor = args.ack_handle
    if os.name == "nt":
        import msvcrt

        read_descriptor = msvcrt.open_osfhandle(args.read_handle, os.O_RDONLY)
        ack_descriptor = msvcrt.open_osfhandle(args.ack_handle, os.O_WRONLY)
    predecessor_digest = (
        None if args.predecessor_digest == "NONE" else args.predecessor_digest
    )
    command = contract.exact_worker_command(
        mode=mode,
        read_handle=args.read_handle,
        ack_handle=args.ack_handle,
        parent_pid=args.parent_pid,
        parent_create_time_ns=args.parent_create_time_ns,
        session_id=args.session_id,
        execution_index=args.execution_index,
        block_id=args.block_id,
        predecessor_digest=predecessor_digest,
        nonce=args.nonce,
    )
    parent_identity = {
        "pid": args.parent_pid,
        "create_time_ns": args.parent_create_time_ns,
    }
    worker_identity = {
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "create_time_ns": contract.process_create_time_ns(os.getpid()),
    }
    hello = contract.build_worker_hello(
        mode=mode,
        session_id=args.session_id,
        execution_index=args.execution_index,
        block_id=args.block_id,
        predecessor_digest=predecessor_digest,
        nonce=args.nonce,
        parent_identity=parent_identity,
        worker_identity=worker_identity,
        command=command,
        worker_read=worker_read,
        worker_ack=worker_ack,
    )
    try:
        hello_raw = contract.write_frame(ack_descriptor, hello)
        if mode == "review-preloader":
            contract.write_frame(
                ack_descriptor,
                {
                    "schema": "rq2_public_grid_preloader_ack_vnext_execution_v4",
                    "hello_sha256": contract.sha256_bytes(hello_raw),
                    "status": "NON_ACCEPTED_PRELOADER_BOUNDARY",
                    "scientific_loader_calls": 0,
                    "solver_calls": 0,
                    "accepted": False,
                    "nonformal": True,
                    "claim": False,
                },
            )
            return 0
        if mode == "review-resource-probe":
            release_raw, release = contract.read_frame(
                read_descriptor, "resource-probe release"
            )
            contract.require_eof(read_descriptor)
            expected = {
                "schema": "rq2_public_grid_resource_probe_release_vnext_execution_v4",
                "hello_sha256": contract.sha256_bytes(hello_raw),
                "first_same_pair_resource_sample_succeeded_before_release": True,
                "nonformal": True,
                "claim": False,
            }
            contract.require_exact(release, expected, label="resource-probe release")
            contract.write_frame(
                ack_descriptor,
                {
                    "schema": "rq2_public_grid_resource_probe_notice_vnext_execution_v4",
                    "hello_sha256": contract.sha256_bytes(hello_raw),
                    "release_sha256": contract.sha256_bytes(release_raw),
                    "status": "REVIEW_RESOURCE_PROBE_EXITING",
                    "scientific_loader_calls": 0,
                    "solver_calls": 0,
                    "accepted": False,
                    "nonformal": True,
                    "claim": False,
                },
            )
            return 0
        return _run_science(
            read_descriptor,
            ack_descriptor,
            hello=hello,
            hello_raw=hello_raw,
            worker_identity=worker_identity,
        )
    finally:
        os.close(read_descriptor)
        os.close(ack_descriptor)


if __name__ == "__main__":
    raise SystemExit(main())
