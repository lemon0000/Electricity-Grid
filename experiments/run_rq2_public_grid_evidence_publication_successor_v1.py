"""Closed controller owning the Vnext zero-solver review-fixture transport."""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from experiments import (
    publish_rq2_public_grid_evidence_publication_successor_v1 as publisher,
)
from experiments import rq2_public_grid_evidence_publication_contract_v1 as contract


class ControllerRejected(contract.ContractRejected):
    """The controller could not prove one exact owned attempt."""


def _json_line(stream: Any, label: str) -> tuple[dict[str, Any], bytes]:
    raw = stream.readline(2_000_000)
    if not raw or len(raw) >= 2_000_000:
        raise ControllerRejected(f"{label} missing/oversized")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ControllerRejected(f"{label} JSON malformed") from exc
    if not isinstance(value, dict):
        raise ControllerRejected(f"{label} is not an object")
    if raw != contract.exact_json_bytes(value):
        raise ControllerRejected(f"{label} is not canonical")
    return value, raw


def _validate_hello(
    hello: dict[str, Any], process: subprocess.Popen[bytes], inventory: tuple[str, ...]
) -> None:
    config = contract.load_config()
    expected = {
        "schema": "rq2_public_grid_worker_hello_vnext_v1",
        "worker_pid": process.pid,
        "worker_ppid": os.getpid(),
        "worker_create_time_ns": contract.process_create_time_ns(process.pid),
        "worker_source_sha256": contract.sha256_bytes(
            contract.read_stable(contract.ROOT / config["bundle"]["members"]["worker"])
        ),
        "config_sha256": contract.sha256_bytes(contract.read_stable(contract.CONFIG)),
        "chain_sha256": contract.sha256_bytes(contract.exact_json_bytes(list(inventory))),
    }
    if hello != expected:
        raise ControllerRejected("worker HELLO identity/hash drifted")


class ReviewController:
    """Sole creator of subprocess, pipe envelope, accepted evidence, and ledger."""

    def __init__(
        self,
        root: Path,
        *,
        verifier: contract.StageAwareClosureVerifier | None = None,
    ) -> None:
        if root.exists() or root.is_symlink():
            raise ControllerRejected("review session root must be clean absent")
        root.mkdir(parents=True, exist_ok=False)
        self._root = root
        self._verifier = verifier or contract.StageAwareClosureVerifier()
        self._ledger = contract.ControllerLedgerVnext()
        self._lock = threading.RLock()
        self._attempted: set[int] = set()
        self._active: int | None = None
        self._receipt: contract.ControllerReceiptVnext | None = None
        self._worker_pids: list[int] = []
        self._preflight: list[int] = []

    @property
    def ledger(self) -> contract.ControllerLedgerVnext:
        return self._ledger

    @property
    def worker_pids(self) -> tuple[int, ...]:
        return tuple(self._worker_pids)

    def _consume_attempt(self) -> int:
        with self._lock:
            if self._active is not None:
                raise ControllerRejected("concurrent attempt rejected")
            index = len(self._attempted) + 1
            if index not in (1, 2) or index in self._attempted:
                raise ControllerRejected("retry/extra attempt rejected")
            if index == 2 and len(self._ledger.records) != 1:
                raise ControllerRejected("0009 requires accepted 0008 evidence")
            self._attempted.add(index)
            self._active = index
            return index

    def dispatch_next_review_fixture(self) -> contract.AcceptedEvidenceVnext:
        index = self._consume_attempt()
        try:
            return self._spawn_and_accept(index)
        finally:
            with self._lock:
                self._active = None

    def _spawn_and_accept(self, index: int) -> contract.AcceptedEvidenceVnext:
        from experiments import (
            run_rq2_public_grid_two_block_pilot_activation_transport_v5 as resources,
        )

        config = contract.load_config()
        available = resources.preflight_available_commit()
        self._preflight.append(available)
        inventory = contract.verify_full_live_closure()
        block_id = contract.BLOCKS[index - 1]
        nonce = os.urandom(32).hex()
        predecessor_digest = None if index == 1 else contract.evidence_digest(self._ledger.records[-1])
        attempt_root = self._root / "workers" / block_id / nonce
        command = list(contract.exact_worker_command())
        environment = dict(config["runtime"]["sanitized_environment"])
        stderr_root = self._root / "logs"
        stderr_root.mkdir(parents=True, exist_ok=True)
        stderr_path = stderr_root / f"{index:02d}_{block_id}_{nonce}.stderr.log"
        parent_pid = os.getpid()
        parent_create_time = contract.process_create_time_ns(parent_pid)
        with stderr_path.open("xb") as stderr_stream:
            process = subprocess.Popen(
                command,
                cwd=contract.ROOT,
                env=environment,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=stderr_stream,
            )
            self._worker_pids.append(process.pid)
            try:
                assert process.stdin is not None and process.stdout is not None
                hello, hello_raw = _json_line(process.stdout, "worker HELLO")
                _validate_hello(hello, process, inventory)
                envelope = {
                    "schema": "rq2_public_grid_worker_envelope_vnext_v1",
                    "session_id": self._ledger.session_id,
                    "execution_index": index,
                    "block_id": block_id,
                    "predecessor_digest": predecessor_digest,
                    "nonce": nonce,
                    "parent_pid": parent_pid,
                    "parent_create_time_ns": parent_create_time,
                    "worker_pid": process.pid,
                    "worker_ppid": parent_pid,
                    "worker_create_time_ns": hello["worker_create_time_ns"],
                    "command": command,
                    "cwd": str(contract.ROOT),
                    "environment": environment,
                    "config_sha256": hello["config_sha256"],
                    "chain_sha256": hello["chain_sha256"],
                    "worker_source_sha256": hello["worker_source_sha256"],
                    "attempt_root": str(attempt_root),
                    "scientific_payload_sha256": config["fixture"]["payload_sha256"][block_id],
                    "review_fixture": True,
                    "nonformal": True,
                    "claim": False,
                }
                envelope_raw = contract.exact_json_bytes(envelope)
                process.stdin.write(envelope_raw)
                process.stdin.flush()
                process.stdin.close()
                ack, ack_raw = _json_line(process.stdout, "worker ACK")
                trailing = process.stdout.read(1)
                if trailing != b"":
                    raise ControllerRejected("worker stdout trailing byte/replay rejected")
                return_code = process.wait(timeout=30)
                if return_code != 0:
                    raise ControllerRejected("review worker returned nonzero")
                # Frozen v5 monitor is still the authority. A short review worker
                # is normally already exited, yielding a zero-sample child_exited.
                resource_outcome = resources.monitor_owned_child_resources(
                    process,
                    expected_pid=process.pid,
                    expected_create_time_ns=int(hello["worker_create_time_ns"]),
                    watchdog_deadline=time.monotonic() + config["runtime"]["watchdog_seconds"],
                )
                if resource_outcome.status != "child_exited":
                    raise ControllerRejected("review worker resource outcome was incomplete")
            except Exception:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                raise

        self._verifier.verify("controller_post_child_pre_accept")
        result_path = attempt_root / "worker_result.json"
        receipt_path = attempt_root / "attempt_receipt.json"
        result_raw = contract.read_stable(result_path)
        receipt_raw = contract.read_stable(receipt_path)
        result = json.loads(result_raw)
        attempt_receipt = json.loads(receipt_raw)
        if not isinstance(result, dict) or not isinstance(attempt_receipt, dict):
            raise ControllerRejected("worker source schema malformed")
        scientific = result.get("scientific_payload")
        if not isinstance(scientific, dict):
            raise ControllerRejected("worker scientific payload missing")
        scientific_raw = contract.exact_json_bytes(scientific)
        result_sha = contract.sha256_bytes(result_raw)
        receipt_sha = contract.sha256_bytes(receipt_raw)
        envelope_sha = contract.sha256_bytes(envelope_raw)
        scientific_sha = contract.sha256_bytes(scientific_raw)
        expected_ack = {
            "schema": "rq2_public_grid_worker_ack_vnext_v1",
            "session_id": self._ledger.session_id,
            "execution_index": index,
            "block_id": block_id,
            "nonce": nonce,
            "worker_pid": process.pid,
            "worker_create_time_ns": hello["worker_create_time_ns"],
            "envelope_sha256": envelope_sha,
            "result_sha256": result_sha,
            "attempt_receipt_sha256": receipt_sha,
            "scientific_payload_sha256": scientific_sha,
            "accepted_for_review_ledger": True,
            "accepted_as_production_result": False,
            "review_fixture": True,
            "nonformal": True,
            "claim": False,
        }
        if ack != expected_ack:
            raise ControllerRejected("worker ACK/source binding drifted")
        if (
            result.get("envelope_sha256") != envelope_sha
            or result.get("scientific_payload_sha256") != scientific_sha
            or attempt_receipt.get("result_sha256") != result_sha
            or attempt_receipt.get("scientific_payload_sha256") != scientific_sha
        ):
            raise ControllerRejected("worker result/receipt binding drifted")
        contract.validate_scientific_payload(scientific, block_id)
        fields: dict[str, object] = {
            "protocol": contract.PROTOCOL,
            "session_id": self._ledger.session_id,
            "execution_index": index,
            "block_id": block_id,
            "predecessor_digest": predecessor_digest,
            "nonce": nonce,
            "parent_pid": parent_pid,
            "parent_create_time_ns": parent_create_time,
            "worker_pid": process.pid,
            "worker_ppid": parent_pid,
            "worker_create_time_ns": int(hello["worker_create_time_ns"]),
            "command": tuple(command),
            "cwd": str(contract.ROOT),
            "environment_sha256": contract.sha256_bytes(contract.exact_json_bytes(environment)),
            "config_sha256": str(hello["config_sha256"]),
            "chain_sha256": str(hello["chain_sha256"]),
            "worker_source_sha256": str(hello["worker_source_sha256"]),
            "hello_bytes": hello_raw,
            "hello_sha256": contract.sha256_bytes(hello_raw),
            "envelope_bytes": envelope_raw,
            "envelope_sha256": envelope_sha,
            "ack_bytes": ack_raw,
            "ack_sha256": contract.sha256_bytes(ack_raw),
            "result_path": str(result_path),
            "result_bytes": result_raw,
            "result_sha256": result_sha,
            "attempt_receipt_path": str(receipt_path),
            "attempt_receipt_bytes": receipt_raw,
            "attempt_receipt_sha256": receipt_sha,
            "scientific_bytes": scientific_raw,
            "scientific_sha256": scientific_sha,
            "review_fixture": True,
            "nonformal": True,
            "claim": False,
            "scientific_loader_calls": 0,
            "solver_calls": 0,
        }
        evidence = self._ledger._new_evidence(fields)
        self._ledger._append_controller(evidence, token=contract._FACTORY_TOKEN)
        return evidence

    def seal_receipt(self) -> contract.ControllerReceiptVnext:
        if self._receipt is None:
            self._receipt = self._ledger._seal_controller(contract.verify_full_live_closure())
        return self._receipt

    def publish(self, paths: publisher.PublicationPaths) -> dict[str, object]:
        receipt = self.seal_receipt()
        return publisher.publish_review_fixture(
            self._ledger, receipt, paths, verifier=self._verifier
        )


def run_review_fixture_e2e(root: Path) -> dict[str, object]:
    session = ReviewController(root / "session")
    session.dispatch_next_review_fixture()
    session.dispatch_next_review_fixture()
    receipt = session.seal_receipt()
    paths = publisher.publication_paths(root / "published")
    outcome = session.publish(paths)
    return {
        **outcome,
        "review_fixture": True,
        "nonformal": True,
        "claim": False,
        "worker_processes_started": len(session.worker_pids),
        "worker_pids": list(session.worker_pids),
        "scientific_loader_calls": 0,
        "solver_calls": 0,
        "ledger_record_count": len(session.ledger.records),
        "ledger": session.ledger,
        "receipt": receipt,
        "paths": paths.as_object(),
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list([] if argv is None else argv)
    if arguments != ["--validate-only"]:
        raise contract.ContractRejected(
            "Vnext is review closed; no production/pilot/formal execution is authorized"
        )
    inventory = contract.verify_full_live_closure()
    print(
        json.dumps(
            {
                "validation_passed": True,
                "status": "evidence_publication_successor_v1_review_closed",
                "closure_inventory_count": len(inventory),
                "execution_ready": False,
                "worker_processes_started": 0,
                "scientific_loader_calls": 0,
                "solver_calls": 0,
                "result_writes": 0,
                "pilot_executed": False,
                "formal_execution_ready": False,
                "claim": False,
                "security_certified": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
