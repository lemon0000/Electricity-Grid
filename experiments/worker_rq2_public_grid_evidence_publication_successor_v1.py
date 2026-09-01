"""Internal zero-solver review worker for the closed Vnext bundle."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from experiments import rq2_public_grid_evidence_publication_contract_v1 as contract


class WorkerRejected(contract.ContractRejected):
    """The internal review worker failed closed."""


def _write_atomic(path: Path, raw: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise WorkerRejected("worker output already exists")
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise WorkerRejected("worker attempt root is not one ordinary directory")
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _frame(value: object) -> bytes:
    return contract.exact_json_bytes(value)


def _parse(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--internal-review-fixture-worker", action="store_true")
    return parser.parse_args(argv)


def _validate_envelope(value: object, hello: Mapping[str, object]) -> dict[str, object]:
    config = contract.load_config()
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "session_id",
        "execution_index",
        "block_id",
        "predecessor_digest",
        "nonce",
        "parent_pid",
        "parent_create_time_ns",
        "worker_pid",
        "worker_ppid",
        "worker_create_time_ns",
        "command",
        "cwd",
        "environment",
        "config_sha256",
        "chain_sha256",
        "worker_source_sha256",
        "attempt_root",
        "scientific_payload_sha256",
        "review_fixture",
        "nonformal",
        "claim",
    }:
        raise WorkerRejected("worker envelope schema drifted")
    index = value["execution_index"]
    if type(index) is not int or index not in (1, 2):
        raise WorkerRejected("worker envelope index malformed")
    block_id = value["block_id"]
    if block_id != contract.BLOCKS[index - 1]:
        raise WorkerRejected("worker envelope block/index drifted")
    if value["worker_pid"] != os.getpid() or value["worker_ppid"] != os.getppid():
        raise WorkerRejected("worker envelope PID/PPID drifted")
    if value["worker_create_time_ns"] != contract.process_create_time_ns(os.getpid()):
        raise WorkerRejected("worker creation-time drifted")
    if value["command"] != list(contract.exact_worker_command()):
        raise WorkerRejected("worker command drifted")
    if value["cwd"] != str(contract.ROOT) or str(Path.cwd()) != str(contract.ROOT):
        raise WorkerRejected("worker cwd drifted")
    if value["environment"] != config["runtime"]["sanitized_environment"]:
        raise WorkerRejected("worker environment authority drifted")
    if dict(os.environ) != value["environment"]:
        raise WorkerRejected("worker live environment drifted")
    if any(value[key] != hello[key] for key in ("worker_pid", "worker_ppid", "worker_create_time_ns", "worker_source_sha256", "config_sha256", "chain_sha256")):
        raise WorkerRejected("worker HELLO/envelope identity drifted")
    if value["review_fixture"] is not True or value["nonformal"] is not True or value["claim"] is not False:
        raise WorkerRejected("worker review boundary drifted")
    expected_hash = config["fixture"]["payload_sha256"][block_id]
    if value["scientific_payload_sha256"] != expected_hash:
        raise WorkerRejected("worker fixture hash authority drifted")
    return value


def _run_review_fixture() -> int:
    inventory = contract.verify_full_live_closure()
    config_raw = contract.read_stable(contract.CONFIG)
    worker_raw = contract.read_stable(Path(__file__))
    hello = {
        "schema": "rq2_public_grid_worker_hello_vnext_v1",
        "worker_pid": os.getpid(),
        "worker_ppid": os.getppid(),
        "worker_create_time_ns": contract.process_create_time_ns(os.getpid()),
        "worker_source_sha256": contract.sha256_bytes(worker_raw),
        "config_sha256": contract.sha256_bytes(config_raw),
        "chain_sha256": contract.sha256_bytes(contract.exact_json_bytes(list(inventory))),
    }
    sys.stdout.buffer.write(_frame(hello))
    sys.stdout.buffer.flush()
    line = sys.stdin.buffer.readline(2_000_000)
    if not line or len(line) >= 2_000_000:
        raise WorkerRejected("worker envelope missing/oversized")
    trailing = sys.stdin.buffer.read(1)
    if trailing != b"":
        raise WorkerRejected("worker capability replay/trailing byte rejected")
    try:
        envelope_object = json.loads(line)
    except json.JSONDecodeError as exc:
        raise WorkerRejected("worker envelope JSON malformed") from exc
    envelope = _validate_envelope(envelope_object, hello)
    envelope_raw = contract.exact_json_bytes(envelope)

    contract.StageAwareClosureVerifier().verify("worker_pre_loader")
    payload = contract.build_review_fixture_payload(str(envelope["block_id"]))
    contract.StageAwareClosureVerifier().verify("worker_post_solve_pre_validator")
    scientific_raw = contract.exact_json_bytes(payload)
    if contract.sha256_bytes(scientific_raw) != envelope["scientific_payload_sha256"]:
        raise WorkerRejected("worker scientific bytes drifted")
    contract.StageAwareClosureVerifier().verify("worker_post_validator_pre_write")
    result = {
        "schema": "rq2_public_grid_worker_result_vnext_v1",
        "protocol": contract.PROTOCOL,
        "session_id": envelope["session_id"],
        "execution_index": envelope["execution_index"],
        "block_id": envelope["block_id"],
        "nonce": envelope["nonce"],
        "envelope_sha256": contract.sha256_bytes(envelope_raw),
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
    result_raw = _frame(result)
    attempt_root = Path(str(envelope["attempt_root"]))
    result_path = attempt_root / "worker_result.json"
    receipt_path = attempt_root / "attempt_receipt.json"
    attempt_root.mkdir(parents=True, exist_ok=False)
    _write_atomic(result_path, result_raw)
    receipt = {
        "schema": "rq2_public_grid_attempt_receipt_vnext_v1",
        "session_id": envelope["session_id"],
        "execution_index": envelope["execution_index"],
        "block_id": envelope["block_id"],
        "nonce": envelope["nonce"],
        "result_path": str(result_path),
        "result_sha256": contract.sha256_bytes(result_raw),
        "scientific_payload_sha256": contract.sha256_bytes(scientific_raw),
        "review_fixture": True,
        "nonformal": True,
        "claim": False,
        "controller_validated": False,
        "published": False,
    }
    receipt_raw = _frame(receipt)
    _write_atomic(receipt_path, receipt_raw)
    contract.StageAwareClosureVerifier().verify("worker_post_write_pre_ack")
    ack = {
        "schema": "rq2_public_grid_worker_ack_vnext_v1",
        "session_id": envelope["session_id"],
        "execution_index": envelope["execution_index"],
        "block_id": envelope["block_id"],
        "nonce": envelope["nonce"],
        "worker_pid": os.getpid(),
        "worker_create_time_ns": hello["worker_create_time_ns"],
        "envelope_sha256": contract.sha256_bytes(envelope_raw),
        "result_sha256": contract.sha256_bytes(result_raw),
        "attempt_receipt_sha256": contract.sha256_bytes(receipt_raw),
        "scientific_payload_sha256": contract.sha256_bytes(scientific_raw),
        "accepted_for_review_ledger": True,
        "accepted_as_production_result": False,
        "review_fixture": True,
        "nonformal": True,
        "claim": False,
    }
    sys.stdout.buffer.write(_frame(ack))
    sys.stdout.buffer.flush()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse(argv)
    if not args.internal_review_fixture_worker:
        raise WorkerRejected("production/public worker entry is review closed")
    return _run_review_fixture()


if __name__ == "__main__":
    raise SystemExit(main())
