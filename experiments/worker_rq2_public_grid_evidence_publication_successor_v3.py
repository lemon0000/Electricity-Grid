"""Internal anonymous-pipe review worker for closed successor v3."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from experiments import rq2_public_grid_evidence_publication_contract_v3 as contract


class WorkerRejected(contract.ContractRejected):
    """The internal worker failed closed before acceptance."""


def _parse(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--internal-review-fixture-worker", action="store_true")
    parser.add_argument("--read-handle", type=int)
    parser.add_argument("--ack-handle", type=int)
    parser.add_argument("--parent-pid", type=int)
    parser.add_argument("--parent-create-time-ns", type=int)
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


def _validate_envelope(
    value: dict[str, Any],
    *,
    hello: dict[str, Any],
    expected_command: tuple[str, ...],
    worker_read_observation: dict[str, object],
    worker_ack_observation: dict[str, object],
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
        "worker_source_sha256",
        "controller_source_sha256",
        "closure_mapping",
        "closure_mapping_sha256",
        "pipe_authority",
        "pipe_authority_digest",
        "attempt_root",
        "scientific_payload_sha256",
        "review_fixture",
        "nonformal",
        "claim",
    }
    if set(value) != expected_keys or value.get("schema") != (
        "rq2_public_grid_worker_envelope_vnext_v3"
    ):
        raise WorkerRejected("worker envelope exact schema drifted")
    index = value["execution_index"]
    if type(index) is not int or index not in (1, 2):
        raise WorkerRejected("worker execution index malformed")
    if value["block_id"] != contract.BLOCKS[index - 1]:
        raise WorkerRejected("worker block/index drifted")
    if value["command"] != list(expected_command):
        raise WorkerRejected("worker command authority drifted")
    config = contract.load_config()
    if value["cwd"] != str(contract.ROOT) or Path.cwd() != contract.ROOT:
        raise WorkerRejected("worker cwd drifted")
    if value["environment"] != config["runtime"]["sanitized_environment"]:
        raise WorkerRejected("worker environment object drifted")
    if dict(os.environ) != value["environment"]:
        raise WorkerRejected("worker live environment drifted")
    if value["environment_sha256"] != contract.sha256_bytes(
        contract.exact_json_bytes(value["environment"])
    ):
        raise WorkerRejected("worker environment hash drifted")
    mapping = contract.verify_full_live_closure()
    if value["closure_mapping"] != mapping or value[
        "closure_mapping_sha256"
    ] != contract.closure_mapping_sha256(mapping):
        raise WorkerRejected("worker full closure mapping drifted")
    worker_identity = value["worker_identity"]
    if not isinstance(worker_identity, dict) or worker_identity != {
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "create_time_ns": contract.process_create_time_ns(os.getpid()),
    }:
        raise WorkerRejected("worker process identity drifted")
    if value["parent_identity"] != hello["parent_identity"]:
        raise WorkerRejected("worker parent identity drifted")
    if any(
        value[key] != hello[key]
        for key in (
            "config_sha256",
            "worker_source_sha256",
            "closure_mapping_sha256",
        )
    ):
        raise WorkerRejected("HELLO/envelope authority drifted")
    pipe = value["pipe_authority"]
    if not isinstance(pipe, dict) or pipe.get("worker_read") != (
        worker_read_observation
    ) or pipe.get("worker_ack") != worker_ack_observation:
        raise WorkerRejected("worker raw pipe roles drifted")
    if value["pipe_authority_digest"] != contract.sha256_bytes(
        contract.exact_json_bytes(pipe)
    ):
        raise WorkerRejected("worker pipe authority digest drifted")
    if value["scientific_payload_sha256"] != config["fixture"]["payload_sha256"][
        value["block_id"]
    ]:
        raise WorkerRejected("worker fixture hash authority drifted")
    if value["review_fixture"] is not True or value["nonformal"] is not True:
        raise WorkerRejected("worker review-only boundary drifted")
    if value["claim"] is not False:
        raise WorkerRejected("worker claim boundary drifted")


def _run(
    *,
    read_descriptor: int,
    ack_descriptor: int,
    read_handle: int,
    ack_handle: int,
    parent_pid: int,
    parent_create_time_ns: int,
    worker_read_observation: dict[str, object],
    worker_ack_observation: dict[str, object],
) -> int:
    mapping = contract.verify_full_live_closure()
    config_raw = contract.read_stable(contract.CONFIG)
    source_raw = contract.read_stable(Path(__file__))
    command = contract.exact_worker_command(
        read_handle=read_handle,
        ack_handle=ack_handle,
        parent_pid=parent_pid,
        parent_create_time_ns=parent_create_time_ns,
    )
    hello = {
        "schema": "rq2_public_grid_worker_hello_vnext_v3",
        "worker_identity": {
            "pid": os.getpid(),
            "ppid": os.getppid(),
            "create_time_ns": contract.process_create_time_ns(os.getpid()),
        },
        "parent_identity": {
            "pid": parent_pid,
            "create_time_ns": parent_create_time_ns,
        },
        "parent_identity_verified": True,
        "command": list(command),
        "cwd": str(contract.ROOT),
        "config_sha256": contract.sha256_bytes(config_raw),
        "worker_source_sha256": contract.sha256_bytes(source_raw),
        "closure_mapping_sha256": contract.closure_mapping_sha256(mapping),
        "worker_read": worker_read_observation,
        "worker_ack": worker_ack_observation,
    }
    hello_raw = contract.write_frame(ack_descriptor, hello)
    envelope_raw, envelope = contract.read_frame(read_descriptor, "worker envelope")
    contract.require_eof(read_descriptor)
    _validate_envelope(
        envelope,
        hello=hello,
        expected_command=command,
        worker_read_observation=worker_read_observation,
        worker_ack_observation=worker_ack_observation,
    )
    contract.StageAwareClosureVerifier().verify("worker_pre_fixture")
    payload = contract.build_review_fixture_payload(str(envelope["block_id"]))
    contract.validate_scientific_payload(payload, str(envelope["block_id"]))
    scientific_raw = contract.exact_json_bytes(payload)
    if contract.sha256_bytes(scientific_raw) != envelope["scientific_payload_sha256"]:
        raise WorkerRejected("worker scientific bytes drifted")
    contract.StageAwareClosureVerifier().verify("worker_post_validator_pre_write")
    result = {
        "schema": "rq2_public_grid_worker_result_vnext_v3",
        "session_id": envelope["session_id"],
        "execution_index": envelope["execution_index"],
        "block_id": envelope["block_id"],
        "nonce": envelope["nonce"],
        "hello_sha256": contract.sha256_bytes(hello_raw),
        "envelope_sha256": contract.sha256_bytes(envelope_raw),
        "pipe_authority_digest": envelope["pipe_authority_digest"],
        "closure_mapping_sha256": envelope["closure_mapping_sha256"],
        "scientific_payload": payload,
        "scientific_payload_sha256": contract.sha256_bytes(scientific_raw),
        "review_fixture": True,
        "nonformal": True,
        "claim": False,
        "accepted_for_review_ledger": True,
        "accepted_as_production_result": False,
        "scientific_loader_calls": 0,
        "solver_calls": 0,
        "status": "REVIEW_FIXTURE_VALIDATED_NONPRODUCTION",
    }
    result_raw = contract.exact_json_bytes(result)
    attempt_root = Path(str(envelope["attempt_root"]))
    attempt_root.mkdir(parents=True, exist_ok=False)
    result_path = attempt_root / "worker_result.json"
    receipt_path = attempt_root / "attempt_receipt.json"
    _atomic_source(result_path, result_raw)
    receipt = {
        "schema": "rq2_public_grid_attempt_receipt_vnext_v3",
        "session_id": envelope["session_id"],
        "execution_index": envelope["execution_index"],
        "block_id": envelope["block_id"],
        "nonce": envelope["nonce"],
        "result_path": str(result_path),
        "result_sha256": contract.sha256_bytes(result_raw),
        "scientific_payload_sha256": contract.sha256_bytes(scientific_raw),
        "pipe_authority_digest": envelope["pipe_authority_digest"],
        "closure_mapping_sha256": envelope["closure_mapping_sha256"],
        "review_fixture": True,
        "nonformal": True,
        "claim": False,
        "controller_validated": False,
        "published": False,
    }
    receipt_raw = contract.exact_json_bytes(receipt)
    _atomic_source(receipt_path, receipt_raw)
    contract.StageAwareClosureVerifier().verify("worker_post_write_pre_ack")
    ack = {
        "schema": "rq2_public_grid_worker_ack_vnext_v3",
        "session_id": envelope["session_id"],
        "execution_index": envelope["execution_index"],
        "block_id": envelope["block_id"],
        "nonce": envelope["nonce"],
        "worker_identity": hello["worker_identity"],
        "hello_sha256": contract.sha256_bytes(hello_raw),
        "envelope_sha256": contract.sha256_bytes(envelope_raw),
        "result_sha256": contract.sha256_bytes(result_raw),
        "attempt_receipt_sha256": contract.sha256_bytes(receipt_raw),
        "scientific_payload_sha256": contract.sha256_bytes(scientific_raw),
        "pipe_authority_digest": envelope["pipe_authority_digest"],
        "closure_mapping_sha256": envelope["closure_mapping_sha256"],
        "review_fixture": True,
        "nonformal": True,
        "claim": False,
        "accepted_for_review_ledger": True,
        "accepted_as_production_result": False,
    }
    contract.write_frame(ack_descriptor, ack)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse(argv)
    if (
        not args.internal_review_fixture_worker
        or args.read_handle is None
        or args.ack_handle is None
        or args.parent_pid is None
        or args.parent_create_time_ns is None
    ):
        raise WorkerRejected("public/malformed worker entry is review closed")
    if contract.process_create_time_ns(args.parent_pid) != args.parent_create_time_ns:
        raise WorkerRejected("parent PID/create-time drifted before handle conversion")
    if os.getppid() != args.parent_pid:
        raise WorkerRejected("worker parent PID drifted before handle conversion")
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
    read_descriptor = args.read_handle
    ack_descriptor = args.ack_handle
    if os.name == "nt":
        import msvcrt

        read_descriptor = msvcrt.open_osfhandle(args.read_handle, os.O_RDONLY)
        ack_descriptor = msvcrt.open_osfhandle(args.ack_handle, os.O_WRONLY)
    try:
        return _run(
            read_descriptor=read_descriptor,
            ack_descriptor=ack_descriptor,
            read_handle=args.read_handle,
            ack_handle=args.ack_handle,
            parent_pid=args.parent_pid,
            parent_create_time_ns=args.parent_create_time_ns,
            worker_read_observation=worker_read,
            worker_ack_observation=worker_ack,
        )
    finally:
        os.close(read_descriptor)
        os.close(ack_descriptor)


if __name__ == "__main__":
    raise SystemExit(main())
