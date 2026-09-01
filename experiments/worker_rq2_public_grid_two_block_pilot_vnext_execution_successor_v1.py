"""Internal worker for the review-closed Vnext nonformal pilot successor."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from experiments import (
    rq2_public_grid_two_block_pilot_vnext_execution_contract_v1 as contract,
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
) -> dict[str, Any]:
    config = contract.load_config()
    mapping = contract.verify_live_authorities()
    return {
        "schema": "rq2_public_grid_worker_hello_vnext_execution_v1",
        "mode": mode,
        "worker_identity": {
            "pid": os.getpid(),
            "ppid": os.getppid(),
            "create_time_ns": contract.process_create_time_ns(os.getpid()),
        },
        "parent_identity": parent_identity,
        "parent_identity_verified": True,
        "command": list(command),
        "cwd": str(contract.ROOT),
        "config_sha256": contract.sha256_bytes(contract.read_stable(contract.CONFIG)),
        "worker_source_sha256": contract.sha256_bytes(contract.read_stable(Path(__file__))),
        "v3_closure_mapping_sha256": config["predecessor_v3"]["closure_mapping_sha256"],
        "live_authority_mapping_sha256": contract.closure_mapping_sha256(mapping),
        "worker_read": worker_read,
        "worker_ack": worker_ack,
    }


def _validate_envelope(
    value: dict[str, Any],
    *,
    hello: dict[str, Any],
    command: tuple[str, ...],
    worker_read: dict[str, object],
    worker_ack: dict[str, object],
) -> None:
    expected_keys = {
        "schema",
        "session_id",
        "execution_index",
        "block_id",
        "predecessor_digest",
        "nonce",
        "parent_identity",
        "worker_identity",
        "command",
        "cwd",
        "environment",
        "environment_sha256",
        "config_sha256",
        "controller_source_sha256",
        "worker_source_sha256",
        "v3_outer_sha256",
        "v3_pass_sha256",
        "v3_closure_mapping",
        "v3_closure_mapping_sha256",
        "live_authority_mapping",
        "live_authority_mapping_sha256",
        "pipe_authority",
        "pipe_authority_digest",
        "attempt_root",
        "science_authority",
        "nonformal",
        "claim",
    }
    config = contract.load_config()
    index = value.get("execution_index")
    pipe = value.get("pipe_authority")
    if (
        set(value) != expected_keys
        or value.get("schema") != "rq2_public_grid_worker_envelope_vnext_execution_v1"
        or type(index) is not int
        or index not in (1, 2)
        or value.get("block_id") != contract.BLOCKS[index - 1]
        or value.get("command") != list(command)
        or value.get("cwd") != str(contract.ROOT)
        or value.get("environment") != config["runtime"]["sanitized_environment"]
        or value.get("environment_sha256")
        != contract.sha256_bytes(contract.exact_json_bytes(value["environment"]))
        or value.get("parent_identity") != hello["parent_identity"]
        or value.get("worker_identity") != hello["worker_identity"]
        or value.get("config_sha256") != hello["config_sha256"]
        or value.get("worker_source_sha256") != hello["worker_source_sha256"]
        or value.get("v3_outer_sha256") != config["predecessor_v3"]["outer_sha256"]
        or value.get("v3_pass_sha256")
        != config["predecessor_v3"]["pass_receipt_sha256"]
        or value.get("v3_closure_mapping") != contract.v3.verify_full_live_closure()
        or value.get("v3_closure_mapping_sha256")
        != config["predecessor_v3"]["closure_mapping_sha256"]
        or value.get("live_authority_mapping") != contract.verify_live_authorities()
        or value.get("live_authority_mapping_sha256")
        != hello["live_authority_mapping_sha256"]
        or not isinstance(pipe, dict)
        or pipe.get("worker_read") != worker_read
        or pipe.get("worker_ack") != worker_ack
        or value.get("pipe_authority_digest")
        != contract.sha256_bytes(contract.exact_json_bytes(pipe))
        or value.get("science_authority") != config["science_authority"]
        or value.get("nonformal") is not True
        or value.get("claim") is not False
    ):
        raise WorkerRejected("worker envelope authority/schema drifted")
    if dict(os.environ) != config["runtime"]["sanitized_environment"] or Path.cwd() != contract.ROOT:
        raise WorkerRejected("worker live cwd/environment drifted")


def _run_science(
    read_descriptor: int,
    ack_descriptor: int,
    *,
    hello: dict[str, Any],
    command: tuple[str, ...],
    worker_read: dict[str, object],
    worker_ack: dict[str, object],
) -> int:
    envelope_raw, envelope = contract.read_frame(read_descriptor, "science envelope")
    contract.require_eof(read_descriptor)
    _validate_envelope(
        envelope,
        hello=hello,
        command=command,
        worker_read=worker_read,
        worker_ack=worker_ack,
    )
    payload, accounting = contract.run_actual_science(str(envelope["block_id"]))
    scientific_raw = contract.exact_json_bytes(payload)
    accepted = payload.get("all_hours_resolved") is True
    result = {
        "schema": "rq2_public_grid_worker_result_vnext_execution_v1",
        "session_id": envelope["session_id"],
        "execution_index": envelope["execution_index"],
        "block_id": envelope["block_id"],
        "predecessor_digest": envelope["predecessor_digest"],
        "nonce": envelope["nonce"],
        "hello_sha256": contract.sha256_bytes(contract.exact_json_bytes(hello)),
        "envelope_sha256": contract.sha256_bytes(envelope_raw),
        "pipe_authority_digest": envelope["pipe_authority_digest"],
        "v3_closure_mapping_sha256": envelope["v3_closure_mapping_sha256"],
        "live_authority_mapping_sha256": envelope["live_authority_mapping_sha256"],
        "scientific_payload": payload,
        "scientific_payload_sha256": contract.sha256_bytes(scientific_raw),
        "solver_call_accounting": accounting,
        "scientific_loader_calls": 1,
        "solver_calls": accounting["solver_calls"],
        "accepted_as_nonformal_result": accepted,
        "nonformal": True,
        "claim": False,
        "mathematical_infeasibility_inferred_from_failure": False,
        "status": "COMPLETE" if accepted else "HONEST_INCOMPLETE",
    }
    result_raw = contract.exact_json_bytes(result)
    attempt_root = Path(str(envelope["attempt_root"]))
    attempt_root.mkdir(parents=True, exist_ok=False)
    result_path = attempt_root / "worker_result.json"
    receipt_path = attempt_root / "attempt_receipt.json"
    _atomic_source(result_path, result_raw)
    receipt = {
        "schema": "rq2_public_grid_attempt_receipt_vnext_execution_v1",
        "session_id": envelope["session_id"],
        "execution_index": envelope["execution_index"],
        "block_id": envelope["block_id"],
        "nonce": envelope["nonce"],
        "result_path": str(result_path),
        "result_sha256": contract.sha256_bytes(result_raw),
        "scientific_payload_sha256": result["scientific_payload_sha256"],
        "pipe_authority_digest": envelope["pipe_authority_digest"],
        "v3_closure_mapping_sha256": envelope["v3_closure_mapping_sha256"],
        "controller_validated": False,
        "published": False,
        "nonformal": True,
        "claim": False,
    }
    receipt_raw = contract.exact_json_bytes(receipt)
    _atomic_source(receipt_path, receipt_raw)
    contract.verify_live_authorities()
    ack = {
        "schema": "rq2_public_grid_worker_ack_vnext_execution_v1",
        "session_id": envelope["session_id"],
        "execution_index": envelope["execution_index"],
        "block_id": envelope["block_id"],
        "nonce": envelope["nonce"],
        "worker_identity": hello["worker_identity"],
        "hello_sha256": result["hello_sha256"],
        "envelope_sha256": result["envelope_sha256"],
        "result_sha256": contract.sha256_bytes(result_raw),
        "attempt_receipt_sha256": contract.sha256_bytes(receipt_raw),
        "scientific_payload_sha256": result["scientific_payload_sha256"],
        "pipe_authority_digest": envelope["pipe_authority_digest"],
        "v3_closure_mapping_sha256": envelope["v3_closure_mapping_sha256"],
        "accepted_as_nonformal_result": accepted,
        "nonformal": True,
        "claim": False,
    }
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
    )
    parent_identity = {"pid": args.parent_pid, "create_time_ns": args.parent_create_time_ns}
    hello = _hello(
        mode=mode,
        command=command,
        parent_identity=parent_identity,
        worker_read=worker_read,
        worker_ack=worker_ack,
    )
    try:
        hello_raw = contract.write_frame(ack_descriptor, hello)
        if mode == "review-preloader":
            contract.write_frame(
                ack_descriptor,
                {
                    "schema": "rq2_public_grid_preloader_ack_vnext_execution_v1",
                    "status": "NON_ACCEPTED_PRELOADER_BOUNDARY",
                    "hello_sha256": contract.sha256_bytes(hello_raw),
                    "worker_identity": hello["worker_identity"],
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
            command=command,
            worker_read=worker_read,
            worker_ack=worker_ack,
        )
    finally:
        os.close(read_descriptor)
        os.close(ack_descriptor)


if __name__ == "__main__":
    raise SystemExit(main())
