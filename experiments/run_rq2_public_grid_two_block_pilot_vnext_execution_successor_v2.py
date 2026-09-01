"""Review-closed executable Vnext transport for the fixed nonformal two-block pilot."""

from __future__ import annotations

import concurrent.futures
import hmac
import json
import os
import secrets
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from experiments import (
    publish_rq2_public_grid_evidence_publication_successor_v3 as publisher,
)
from experiments import (
    rq2_public_grid_two_block_pilot_vnext_execution_contract_v2 as contract,
)


class HonestIncomplete(contract.ContractRejected):
    """A non-certifying execution failure stopped the session."""


class AttemptLedger:
    """Atomic one-shot 0008->0009 attempt state; it grants no evidence authority."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._attempted: set[int] = set()
        self._active = False
        self._accepted_predecessor: str | None = None

    def consume(self, index: int) -> str | None:
        with self._lock:
            if (
                self._active
                or index not in (1, 2)
                or index in self._attempted
                or index != len(self._attempted) + 1
                or (index == 2 and self._accepted_predecessor is None)
            ):
                raise contract.ContractRejected("concurrent/retry/reorder/skip rejected")
            self._attempted.add(index)
            self._active = True
            return self._accepted_predecessor

    def finish(self, index: int, accepted_digest: str | None) -> None:
        with self._lock:
            if not self._active or index != len(self._attempted):
                raise contract.ContractRejected("attempt completion state drifted")
            if index == 1 and accepted_digest is not None:
                self._accepted_predecessor = accepted_digest
            self._active = False


def _child_raw(descriptor: int) -> int:
    if os.name != "nt":
        return descriptor
    import msvcrt

    return int(msvcrt.get_osfhandle(descriptor))


def _popen(
    command: list[str],
    worker_read: int,
    worker_ack: int,
    environment: dict[str, str],
    *,
    review_capture_stderr: bool = False,
) -> subprocess.Popen[Any]:
    kwargs: dict[str, Any] = {
        "cwd": contract.ROOT,
        "env": dict(environment),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": None if review_capture_stderr else subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        startup = subprocess.STARTUPINFO()
        startup.lpAttributeList = {"handle_list": [worker_read, worker_ack]}
        kwargs["startupinfo"] = startup
    else:
        kwargs["pass_fds"] = (worker_read, worker_ack)
    return subprocess.Popen(command, **kwargs)


def run_review_preloader_e2e() -> dict[str, Any]:
    """Spawn the exact future worker command and stop before loader/solver access."""
    config = contract.load_config()
    contract.verify_live_authorities()
    parent = {
        "pid": os.getpid(),
        "create_time_ns": contract.process_create_time_ns(os.getpid()),
    }
    session_id = "review-preloader"
    execution_index = 0
    block_id = "review-preloader"
    predecessor_digest = None
    nonce = "review-preloader"
    controller_read, worker_ack_fd = os.pipe()
    worker_read_fd, controller_write = os.pipe()
    worker_read = _child_raw(worker_read_fd)
    worker_ack = _child_raw(worker_ack_fd)
    process: subprocess.Popen[Any] | None = None
    try:
        if os.name == "nt":
            os.set_handle_inheritable(worker_read, True)
            os.set_handle_inheritable(worker_ack, True)
        else:
            os.set_inheritable(worker_read_fd, True)
            os.set_inheritable(worker_ack_fd, True)
        command = list(
            contract.exact_worker_command(
                mode="review-preloader",
                read_handle=worker_read,
                ack_handle=worker_ack,
                parent_pid=parent["pid"],
                parent_create_time_ns=parent["create_time_ns"],
                session_id=session_id,
                execution_index=execution_index,
                block_id=block_id,
                predecessor_digest=predecessor_digest,
                nonce=nonce,
            )
        )
        observed_worker_read = contract.observe_pipe_endpoint(
            worker_read,
            role="controller_to_worker",
            direction="read",
            inherited=True,
        )
        observed_worker_ack = contract.observe_pipe_endpoint(
            worker_ack,
            role="worker_to_controller",
            direction="write",
            inherited=True,
        )
        contract.observe_pipe_endpoint(
            _child_raw(controller_write),
            role="controller_to_worker",
            direction="write",
            inherited=False,
        )
        contract.observe_pipe_endpoint(
            _child_raw(controller_read),
            role="worker_to_controller",
            direction="read",
            inherited=False,
        )
        try:
            contract.verify_live_authorities()
            process = _popen(
                command,
                worker_read,
                worker_ack,
                config["runtime"]["sanitized_environment"],
                review_capture_stderr=True,
            )
        finally:
            if os.name == "nt":
                os.set_handle_inheritable(worker_read, False)
                os.set_handle_inheritable(worker_ack, False)
            else:
                os.set_inheritable(worker_read_fd, False)
                os.set_inheritable(worker_ack_fd, False)
        expected_worker = {
            "pid": process.pid,
            "ppid": os.getpid(),
            "create_time_ns": contract.process_create_time_ns(process.pid),
        }
        os.close(worker_read_fd)
        worker_read_fd = -1
        os.close(worker_ack_fd)
        worker_ack_fd = -1
        try:
            hello_raw, hello = contract.read_frame(controller_read, "preloader HELLO")
        except Exception as exc:
            raise contract.ContractRejected("preloader child failed before HELLO") from exc
        ack_raw, ack = contract.read_frame(controller_read, "preloader ACK")
        contract.require_eof(controller_read)
        os.close(controller_write)
        controller_write = -1
        if process.wait(timeout=30) != 0:
            raise contract.ContractRejected("preloader child exit rejected")
        expected_command = contract.exact_worker_command(
            mode="review-preloader",
            read_handle=worker_read,
            ack_handle=worker_ack,
            parent_pid=parent["pid"],
            parent_create_time_ns=parent["create_time_ns"],
            session_id=session_id,
            execution_index=execution_index,
            block_id=block_id,
            predecessor_digest=predecessor_digest,
            nonce=nonce,
        )
        contract.validate_worker_hello(
            hello,
            mode="review-preloader",
            session_id=session_id,
            execution_index=execution_index,
            block_id=block_id,
            predecessor_digest=predecessor_digest,
            nonce=nonce,
            parent_identity=parent,
            worker_identity=expected_worker,
            command=expected_command,
            worker_read=observed_worker_read,
            worker_ack=observed_worker_ack,
        )
        contract.validate_preloader_ack(ack, hello=hello, hello_raw=hello_raw)
        contract.verify_live_authorities()
        return {
            "status": ack["status"],
            "accepted": False,
            "worker_pid": process.pid,
            "worker_exited": process.poll() is not None,
            "command": list(expected_command),
            "hello_sha256": contract.sha256_bytes(hello_raw),
            "ack_sha256": contract.sha256_bytes(ack_raw),
            "scientific_loader_calls": 0,
            "solver_calls": 0,
            "result_writes": 0,
        }
    finally:
        for descriptor in (controller_read, worker_ack_fd, worker_read_fd, controller_write):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def run_two_block_nonformal() -> dict[str, Any]:
    """Execute only after the fixed external review receipt opens this successor."""
    contract.require_execution_review()
    config = contract.load_config()
    authority_mapping = contract.verify_live_authorities()
    self_mapping = contract.verify_self_bundle()
    v3_mapping = contract.v3.verify_full_live_closure()
    paths = {key: contract.ROOT / value for key, value in config["paths"].items()}
    if any(path.exists() or path.is_symlink() for path in paths.values()):
        raise contract.ContractRejected("canonical execution roots must be clean absent")
    resources = contract.resource_authority()
    resources.preflight_available_commit()
    secret = secrets.token_bytes(32)
    session_id = secrets.token_hex(32)
    session_root = paths["worker_root"] / session_id
    session_root.mkdir(parents=True, exist_ok=False)
    ledger = AttemptLedger()
    records: list[dict[str, Any]] = []

    def sign(value: object) -> str:
        return hmac.new(secret, contract.exact_json_bytes(value), "sha256").hexdigest()

    def verify_record(record: dict[str, Any]) -> None:
        body = {key: value for key, value in record.items() if key not in {"record_digest", "controller_hmac"}}
        digest = contract.sha256_bytes(contract.exact_json_bytes(body))
        self_mapping = contract.verify_self_bundle()
        if (
            record.get("schema") != "rq2_public_grid_accepted_evidence_vnext_execution_v2"
            or record.get("record_digest") != digest
            or not hmac.compare_digest(record.get("controller_hmac", ""), sign({"body": body, "record_digest": digest}))
            or record.get("v3_closure_mapping") != v3_mapping
            or record.get("v3_closure_mapping_sha256")
            != config["predecessor_v3"]["closure_mapping_sha256"]
            or record.get("live_authority_mapping") != authority_mapping
            or record.get("live_authority_mapping_sha256")
            != contract.closure_mapping_sha256(authority_mapping)
            or record.get("self_bundle_mapping") != self_mapping
            or record.get("self_bundle_mapping_sha256")
            != contract.closure_mapping_sha256(self_mapping)
            or record.get("config_sha256")
            != self_mapping[contract.CONFIG.relative_to(contract.ROOT).as_posix()]
            or record.get("controller_source_sha256")
            != self_mapping[
                "experiments/run_rq2_public_grid_two_block_pilot_vnext_execution_successor_v2.py"
            ]
            or record.get("worker_source_sha256")
            != self_mapping[
                "experiments/worker_rq2_public_grid_two_block_pilot_vnext_execution_successor_v2.py"
            ]
            or record.get("bootstrap_source_sha256")
            != self_mapping[config["runtime"]["bootstrap_path"]]
            or record.get("nonformal") is not True
            or record.get("claim") is not False
        ):
            raise contract.ContractRejected("accepted evidence HMAC/authority rejected")
        hello_raw = bytes.fromhex(record["hello_hex"])
        envelope_raw = bytes.fromhex(record["envelope_hex"])
        result_raw = bytes.fromhex(record["result_hex"])
        receipt_raw = bytes.fromhex(record["attempt_receipt_hex"])
        ack_raw = bytes.fromhex(record["ack_hex"])
        hello = json.loads(hello_raw)
        envelope = json.loads(envelope_raw)
        result = json.loads(result_raw)
        receipt = json.loads(receipt_raw)
        ack = json.loads(ack_raw)
        if (
            record.get("hello") != hello
            or record.get("envelope") != envelope
            or record.get("ack") != ack
            or record.get("worker_result") != result
            or record.get("attempt_receipt") != receipt
        ):
            raise contract.ContractRejected("parsed/raw protocol evidence mismatch")
        contract.validate_worker_hello(
            hello,
            mode="science",
            session_id=record["session_id"],
            execution_index=record["execution_index"],
            block_id=record["block_id"],
            predecessor_digest=record["predecessor_digest"],
            nonce=record["nonce"],
            parent_identity=record["parent_identity"],
            worker_identity=record["worker_identity"],
            command=tuple(record["command"]),
            worker_read=record["pipe_authority"]["worker_read"],
            worker_ack=record["pipe_authority"]["worker_ack"],
        )
        result_path = Path(record["result_path"])
        contract.validate_worker_envelope(
            envelope,
            hello=hello,
            hello_raw=hello_raw,
            pipe_authority=record["pipe_authority"],
            attempt_root=str(result_path.parent),
        )
        contract.validate_worker_result(
            result,
            hello=hello,
            hello_raw=hello_raw,
            envelope=envelope,
            envelope_raw=envelope_raw,
            scientific_payload=result["scientific_payload"],
            solver_call_accounting=result["solver_call_accounting"],
        )
        contract.validate_attempt_receipt(
            receipt,
            hello=hello,
            envelope=envelope,
            result=result,
            result_raw=result_raw,
            result_path=str(result_path),
        )
        contract.validate_worker_ack(
            ack,
            hello=hello,
            envelope=envelope,
            result=result,
            result_raw=result_raw,
            receipt_raw=receipt_raw,
        )
        scientific = result.get("scientific_payload")
        if not isinstance(scientific, dict):
            raise contract.ContractRejected("scientific payload missing")
        validated, accounting = contract.validate_actual_science_payload(scientific, record["block_id"])
        if (
            validated != scientific
            or accounting != result.get("solver_call_accounting")
            or result.get("accepted_as_nonformal_result") is not True
            or result.get("all_hours_resolved", scientific.get("all_hours_resolved")) is not True
            or ack.get("accepted_as_nonformal_result") is not True
            or receipt.get("published") is not False
            or receipt.get("controller_validated") is not False
            or record.get("scientific_payload_sha256")
            != result.get("scientific_payload_sha256")
            or record.get("solver_call_accounting_sha256")
            != result.get("solver_call_accounting_sha256")
            or ack.get("scientific_payload_sha256")
            != record.get("scientific_payload_sha256")
            or receipt.get("scientific_payload_sha256")
            != record.get("scientific_payload_sha256")
            or contract.sha256_bytes(result_raw) != record["result_sha256"]
            or contract.sha256_bytes(receipt_raw) != record["attempt_receipt_sha256"]
            or contract.sha256_bytes(ack_raw) != record["ack_sha256"]
        ):
            raise contract.ContractRejected("accepted scientific/source evidence rejected")
        contract.verify_live_authorities()

    def dispatch(index: int) -> None:
        predecessor = ledger.consume(index)
        accepted_digest: str | None = None
        block_id = contract.BLOCKS[index - 1]
        nonce = secrets.token_hex(32)
        attempt_root = session_root / block_id / nonce
        parent = {
            "pid": os.getpid(),
            "create_time_ns": contract.process_create_time_ns(os.getpid()),
        }
        controller_read, worker_ack_fd = os.pipe()
        worker_read_fd, controller_write = os.pipe()
        worker_read = _child_raw(worker_read_fd)
        worker_ack = _child_raw(worker_ack_fd)
        process: subprocess.Popen[Any] | None = None
        monitor_future: concurrent.futures.Future[Any] | None = None
        try:
            if os.name == "nt":
                os.set_handle_inheritable(worker_read, True)
                os.set_handle_inheritable(worker_ack, True)
            else:
                os.set_inheritable(worker_read_fd, True)
                os.set_inheritable(worker_ack_fd, True)
            command = list(
                contract.exact_worker_command(
                    mode="science",
                    read_handle=worker_read,
                    ack_handle=worker_ack,
                    parent_pid=parent["pid"],
                    parent_create_time_ns=parent["create_time_ns"],
                    session_id=session_id,
                    execution_index=index,
                    block_id=block_id,
                    predecessor_digest=predecessor,
                    nonce=nonce,
                )
            )
            try:
                contract.verify_live_authorities()
                process = _popen(command, worker_read, worker_ack, config["runtime"]["sanitized_environment"])
            finally:
                if os.name == "nt":
                    os.set_handle_inheritable(worker_read, False)
                    os.set_handle_inheritable(worker_ack, False)
                else:
                    os.set_inheritable(worker_read_fd, False)
                    os.set_inheritable(worker_ack_fd, False)
            os.close(worker_read_fd)
            worker_read_fd = -1
            os.close(worker_ack_fd)
            worker_ack_fd = -1
            worker_identity = {
                "pid": process.pid,
                "ppid": os.getpid(),
                "create_time_ns": contract.process_create_time_ns(process.pid),
            }
            deadline = time.monotonic() + config["resource_authority"]["watchdog_seconds_per_block"]
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            monitor_future = executor.submit(
                resources.monitor_owned_child_resources,
                process,
                expected_pid=process.pid,
                expected_create_time_ns=worker_identity["create_time_ns"],
                sample_interval_seconds=config["resource_authority"]["sample_interval_seconds"],
                watchdog_deadline=deadline,
            )
            hello_raw, hello = contract.read_frame(controller_read, "science HELLO")
            worker_read_observed = {
                "raw_identifier": worker_read,
                "type": "anonymous_pipe",
                "role": "controller_to_worker",
                "direction": "read",
                "inherited": True,
            }
            worker_ack_observed = {
                "raw_identifier": worker_ack,
                "type": "anonymous_pipe",
                "role": "worker_to_controller",
                "direction": "write",
                "inherited": True,
            }
            contract.validate_worker_hello(
                hello,
                mode="science",
                session_id=session_id,
                execution_index=index,
                block_id=block_id,
                predecessor_digest=predecessor,
                nonce=nonce,
                parent_identity=parent,
                worker_identity=worker_identity,
                command=tuple(command),
                worker_read=worker_read_observed,
                worker_ack=worker_ack_observed,
            )
            contract.verify_live_authorities()
            pipe_authority = {
                "worker_read": worker_read_observed,
                "worker_ack": worker_ack_observed,
                "controller_write": contract.observe_pipe_endpoint(
                    _child_raw(controller_write), role="controller_to_worker", direction="write", inherited=False
                ),
                "controller_read": contract.observe_pipe_endpoint(
                    _child_raw(controller_read), role="worker_to_controller", direction="read", inherited=False
                ),
            }
            envelope = contract.build_worker_envelope(
                hello=hello,
                hello_raw=hello_raw,
                pipe_authority=pipe_authority,
                attempt_root=str(attempt_root),
            )
            envelope_raw = contract.write_frame(controller_write, envelope)
            contract.verify_live_authorities()
            os.close(controller_write)
            controller_write = -1
            ack_raw, ack = contract.read_frame(controller_read, "science ACK")
            contract.require_eof(controller_read)
            process.wait(timeout=max(1.0, deadline - time.monotonic()))
            resource_outcome = monitor_future.result(timeout=30)
            executor.shutdown(wait=True)
            if process.returncode != 0 or resource_outcome.status != "child_exited":
                raise HonestIncomplete(f"science child incomplete: {resource_outcome.status}")
            result_path = attempt_root / "worker_result.json"
            receipt_path = attempt_root / "attempt_receipt.json"
            result_raw = contract.read_stable(result_path)
            receipt_raw = contract.read_stable(receipt_path)
            result = json.loads(result_raw)
            receipt = json.loads(receipt_raw)
            scientific_raw = contract.exact_json_bytes(result["scientific_payload"])
            contract.validate_worker_result(
                result,
                hello=hello,
                hello_raw=hello_raw,
                envelope=envelope,
                envelope_raw=envelope_raw,
                scientific_payload=result["scientific_payload"],
                solver_call_accounting=result["solver_call_accounting"],
            )
            contract.validate_attempt_receipt(
                receipt,
                hello=hello,
                envelope=envelope,
                result=result,
                result_raw=result_raw,
                result_path=str(result_path),
            )
            contract.validate_worker_ack(
                ack,
                hello=hello,
                envelope=envelope,
                result=result,
                result_raw=result_raw,
                receipt_raw=receipt_raw,
            )
            if (
                ack["scientific_payload_sha256"]
                != result["scientific_payload_sha256"]
                or receipt["scientific_payload_sha256"]
                != result["scientific_payload_sha256"]
                or ack["solver_call_accounting_sha256"]
                != result["solver_call_accounting_sha256"]
                or receipt["solver_call_accounting_sha256"]
                != result["solver_call_accounting_sha256"]
            ):
                raise contract.ContractRejected(
                    "ACK/result/receipt science/accounting cross-binding drifted"
                )
            contract.verify_live_authorities()
            body = {
                "schema": "rq2_public_grid_accepted_evidence_vnext_execution_v2",
                "session_id": session_id,
                "execution_index": index,
                "block_id": block_id,
                "predecessor_digest": predecessor,
                "nonce": nonce,
                "parent_identity": parent,
                "worker_identity": worker_identity,
                "command": command,
                "cwd": str(contract.ROOT),
                "environment": config["runtime"]["sanitized_environment"],
                "config_sha256": hello["config_sha256"],
                "controller_source_sha256": hello["controller_source_sha256"],
                "worker_source_sha256": hello["worker_source_sha256"],
                "bootstrap_source_sha256": hello["bootstrap_source_sha256"],
                "self_outer_sha256": hello["self_outer_sha256"],
                "self_inner_sha256": hello["self_inner_sha256"],
                "self_bundle_mapping": hello["self_bundle_mapping"],
                "self_bundle_mapping_sha256": hello[
                    "self_bundle_mapping_sha256"
                ],
                "v3_outer_sha256": config["predecessor_v3"]["outer_sha256"],
                "v3_pass_sha256": config["predecessor_v3"]["pass_receipt_sha256"],
                "v3_closure_mapping": v3_mapping,
                "v3_closure_mapping_sha256": hello[
                    "v3_closure_mapping_sha256"
                ],
                "live_authority_mapping": authority_mapping,
                "live_authority_mapping_sha256": hello[
                    "live_authority_mapping_sha256"
                ],
                "pipe_authority": pipe_authority,
                "pipe_authority_digest": envelope["pipe_authority_digest"],
                "hello_hex": hello_raw.hex(),
                "hello": hello,
                "hello_sha256": contract.sha256_bytes(hello_raw),
                "envelope_hex": envelope_raw.hex(),
                "envelope": envelope,
                "envelope_sha256": contract.sha256_bytes(envelope_raw),
                "ack_hex": ack_raw.hex(),
                "ack": ack,
                "ack_sha256": contract.sha256_bytes(ack_raw),
                "result_path": str(result_path),
                "result_hex": result_raw.hex(),
                "worker_result": result,
                "result_sha256": contract.sha256_bytes(result_raw),
                "attempt_receipt_path": str(receipt_path),
                "attempt_receipt_hex": receipt_raw.hex(),
                "attempt_receipt": receipt,
                "attempt_receipt_sha256": contract.sha256_bytes(receipt_raw),
                "scientific_hex": scientific_raw.hex(),
                "scientific_sha256": contract.sha256_bytes(scientific_raw),
                "scientific_payload_sha256": result[
                    "scientific_payload_sha256"
                ],
                "solver_call_accounting_sha256": result[
                    "solver_call_accounting_sha256"
                ],
                "nonformal": True,
                "claim": False,
                "mathematical_infeasibility_inferred_from_failure": False,
            }
            digest = contract.sha256_bytes(contract.exact_json_bytes(body))
            record = {**body, "record_digest": digest, "controller_hmac": sign({"body": body, "record_digest": digest})}
            verify_record(record)
            if index == 2 and predecessor != records[0]["record_digest"]:
                raise contract.ContractRejected("0009 predecessor evidence drifted")
            records.append(record)
            accepted_digest = digest
            if index == 1:
                predecessor_file = session_root / "accepted_0008.json"
                publisher.atomic_write(predecessor_file, contract.exact_json_bytes(record))
                if json.loads(contract.read_stable(predecessor_file)) != record:
                    raise contract.ContractRejected("0008 immutable predecessor commit drifted")
        finally:
            ledger.finish(index, accepted_digest)
            for descriptor in (controller_read, worker_ack_fd, worker_read_fd, controller_write):
                if descriptor >= 0:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    def publish() -> dict[str, Any]:
        if len(records) != 2 or [r["block_id"] for r in records] != list(contract.BLOCKS):
            raise contract.ContractRejected("publication requires exact accepted 0008/0009 ledger")
        for record in records:
            verify_record(record)
        if contract.verify_live_authorities() != authority_mapping:
            raise contract.ContractRejected("pre-publication authority drifted")
        science_hashes = {
            record["block_id"]: record["scientific_payload_sha256"]
            for record in records
        }
        accounting_hashes = {
            record["block_id"]: record["solver_call_accounting_sha256"]
            for record in records
        }
        body = {
            "schema": "rq2_public_grid_controller_receipt_vnext_execution_v2",
            "session_id": session_id,
            "record_digests": [record["record_digest"] for record in records],
            "ledger_sha256": contract.sha256_bytes(contract.exact_json_bytes(records)),
            "scientific_payload_sha256s": science_hashes,
            "solver_call_accounting_sha256s": accounting_hashes,
            "self_bundle_mapping": self_mapping,
            "self_bundle_mapping_sha256": contract.closure_mapping_sha256(
                self_mapping
            ),
            "v3_closure_mapping_sha256": config["predecessor_v3"]["closure_mapping_sha256"],
            "live_authority_mapping_sha256": contract.closure_mapping_sha256(authority_mapping),
            "nonformal": True,
            "claim": False,
        }
        receipt = {**body, "controller_hmac": sign(body)}
        summary = {
            "schema": "rq2_public_grid_nonformal_two_block_summary_vnext_v3",
            "blocks": list(contract.BLOCKS),
            "record_count": 2,
            "scientific_payload_sha256s": science_hashes,
            "solver_call_accounting_sha256s": accounting_hashes,
            "self_bundle_mapping_sha256": contract.closure_mapping_sha256(
                self_mapping
            ),
            "nonformal": True,
            "claim": False,
            "mathematical_infeasibility_inferred_from_failure": False,
        }
        result_manifest: dict[str, Any] = {}

        def exact_result(root: Path) -> bool:
            try:
                if json.loads(contract.read_stable(root / "SHA256SUMS.json")) != publisher.typed_tree(root):
                    return False
                if contract.read_stable(root / "controller_receipt.json") != contract.exact_json_bytes(receipt):
                    return False
                if json.loads(contract.read_stable(root / "closure_mapping.json")) != v3_mapping:
                    return False
                if json.loads(contract.read_stable(root / "summary.json")) != summary:
                    return False
                if (
                    json.loads(contract.read_stable(root / "result_manifest.json"))
                    != result_manifest
                ):
                    return False
                for record in records:
                    verify_record(record)
                    source = root / "workers" / record["block_id"]
                    expected = {
                        "accepted_evidence.json": contract.exact_json_bytes(record),
                        "hello.json": bytes.fromhex(record["hello_hex"]),
                        "envelope.json": bytes.fromhex(record["envelope_hex"]),
                        "ack.json": bytes.fromhex(record["ack_hex"]),
                        "worker_result.json": bytes.fromhex(record["result_hex"]),
                        "attempt_receipt.json": bytes.fromhex(record["attempt_receipt_hex"]),
                        "scientific_payload.json": bytes.fromhex(record["scientific_hex"]),
                    }
                    for name, raw in expected.items():
                        if contract.read_stable(source / name) != raw:
                            return False
                return True
            except (OSError, ValueError, TypeError, KeyError, contract.ContractRejected):
                return False

        def exact_success(root: Path, expected: dict[str, Any]) -> bool:
            try:
                if json.loads(contract.read_stable(root / "SHA256SUMS.json")) != publisher.typed_tree(root):
                    return False
                return contract.read_stable(root / "success.json") == contract.exact_json_bytes(expected)
            except (OSError, ValueError, TypeError, contract.ContractRejected):
                return False

        result = paths["result_root"]
        success = paths["success_root"]
        terminal = paths["terminal_root"]
        staging = result.with_name(f".{result.name}.staging.{session_id}")
        success_staging = success.with_name(f".{success.name}.staging.{session_id}")
        appeared_result = False
        appeared_success = False
        try:
            initial = publisher.capture_presence(publisher.PublicationPaths(result, success, terminal))
            if publisher.classify_publication(initial, result_exact=False, success_exact=False) != "honest_incomplete":
                raise contract.ContractRejected("initial publication presence rejected")
            staging.mkdir(parents=True, exist_ok=False)
            (staging / "workers").mkdir()
            for record in records:
                destination = staging / "workers" / record["block_id"]
                destination.mkdir()
                for name, raw in (
                    ("accepted_evidence.json", contract.exact_json_bytes(record)),
                    ("hello.json", bytes.fromhex(record["hello_hex"])),
                    ("envelope.json", bytes.fromhex(record["envelope_hex"])),
                    ("ack.json", bytes.fromhex(record["ack_hex"])),
                    ("worker_result.json", bytes.fromhex(record["result_hex"])),
                    ("attempt_receipt.json", bytes.fromhex(record["attempt_receipt_hex"])),
                    ("scientific_payload.json", bytes.fromhex(record["scientific_hex"])),
                ):
                    publisher.atomic_write(destination / name, raw)
            publisher.atomic_write(staging / "controller_receipt.json", contract.exact_json_bytes(receipt))
            publisher.atomic_write(staging / "closure_mapping.json", contract.exact_json_bytes(v3_mapping))
            publisher.atomic_write(staging / "summary.json", contract.exact_json_bytes(summary))
            result_manifest.update(
                {
                    "schema": "rq2_public_grid_result_manifest_vnext_execution_v2",
                    "session_id": session_id,
                    "controller_receipt_sha256": contract.sha256_bytes(
                        contract.exact_json_bytes(receipt)
                    ),
                    "record_digests": [
                        record["record_digest"] for record in records
                    ],
                    "scientific_payload_sha256s": science_hashes,
                    "solver_call_accounting_sha256s": accounting_hashes,
                    "self_bundle_mapping_sha256": contract.closure_mapping_sha256(
                        self_mapping
                    ),
                    "live_authority_mapping_sha256": contract.closure_mapping_sha256(
                        authority_mapping
                    ),
                    "nonformal": True,
                    "claim": False,
                }
            )
            publisher.atomic_write(
                staging / "result_manifest.json",
                contract.exact_json_bytes(result_manifest),
            )
            publisher.atomic_write(staging / "SHA256SUMS.json", contract.exact_json_bytes(publisher.typed_tree(staging)))
            if not exact_result(staging):
                raise contract.ContractRejected("staged result exact-tree readback rejected")
            if contract.verify_live_authorities() != authority_mapping:
                raise contract.ContractRejected("pre-result closure drifted")
            os.replace(staging, result)
            appeared_result = True
            if not exact_result(result):
                raise contract.ContractRejected("committed result exact-tree readback rejected")
            if contract.verify_live_authorities() != authority_mapping:
                raise contract.ContractRejected("post-result closure drifted")
            success_staging.mkdir(parents=True, exist_ok=False)
            success_body = {
                "schema": "rq2_public_grid_success_commit_vnext_v3",
                "session_id": session_id,
                "classification": "committed_success",
                "published": True,
                "nonformal": True,
                "claim": False,
                "controller_receipt_sha256": contract.sha256_bytes(contract.exact_json_bytes(receipt)),
                "result_manifest_sha256": contract.sha256_bytes(contract.read_stable(result / "SHA256SUMS.json")),
                "vnext_result_manifest_sha256": contract.sha256_bytes(
                    contract.read_stable(result / "result_manifest.json")
                ),
                "scientific_payload_sha256s": science_hashes,
                "solver_call_accounting_sha256s": accounting_hashes,
                "self_bundle_mapping_sha256": contract.closure_mapping_sha256(
                    self_mapping
                ),
                "closure_mapping_sha256": config["predecessor_v3"]["closure_mapping_sha256"],
            }
            success_value = {**success_body, "controller_hmac": sign(success_body)}
            publisher.atomic_write(success_staging / "success.json", contract.exact_json_bytes(success_value))
            publisher.atomic_write(success_staging / "SHA256SUMS.json", contract.exact_json_bytes(publisher.typed_tree(success_staging)))
            if not exact_success(success_staging, success_value):
                raise contract.ContractRejected("staged success exact-tree readback rejected")
            if contract.verify_live_authorities() != authority_mapping:
                raise contract.ContractRejected("pre-success closure drifted")
            os.replace(success_staging, success)
            appeared_success = True
            if contract.verify_live_authorities() != authority_mapping:
                raise contract.ContractRejected("post-success closure drifted")
            result_exact = exact_result(result)
            success_exact = exact_success(success, success_value)
            final = publisher.capture_presence(publisher.PublicationPaths(result, success, terminal))
            classification = publisher.classify_publication(
                final,
                result_exact=result_exact,
                success_exact=success_exact,
            )
            if classification != "committed_success":
                raise contract.ContractRejected("final publication readback rejected")
            if contract.verify_live_authorities() != authority_mapping:
                raise contract.ContractRejected("final readback closure drifted")
            return {"classification": classification, "published": True, "claim": False, "formal": False}
        except Exception:
            if appeared_result or appeared_success:
                return {"classification": "commit_indeterminate", "published": False, "claim": False, "formal": False}
            for path in (staging, success_staging):
                if path.exists():
                    shutil.rmtree(path)
            raise

    try:
        dispatch(1)
        dispatch(2)
        return publish()
    except HonestIncomplete as exc:
        return {
            "classification": "honest_incomplete",
            "published": False,
            "claim": False,
            "formal": False,
            "mathematical_infeasibility_inferred": False,
            "reason": str(exc),
        }


def validate_only() -> dict[str, Any]:
    config = contract.load_config()
    mapping = contract.verify_live_authorities()
    self_mapping = contract.verify_self_bundle()
    return {
        "validation_passed": True,
        "status": config["status"],
        "v3_closure_inventory_count": config["predecessor_v3"]["closure_exact_count"],
        "v3_closure_mapping_sha256": config["predecessor_v3"]["closure_mapping_sha256"],
        "live_authority_inventory_count": len(mapping),
        "live_authority_mapping_sha256": contract.closure_mapping_sha256(mapping),
        "self_bundle_inventory_count": len(self_mapping),
        "self_bundle_mapping_sha256": contract.closure_mapping_sha256(
            self_mapping
        ),
        "execution_review_present": contract.REVIEW.exists(),
        "execution_ready": False,
        "worker_processes_started": 0,
        "scientific_loader_calls": 0,
        "solver_calls": 0,
        "result_writes": 0,
        "pilot_executed": False,
        "formal_execution_ready": False,
        "claim": False,
        "security_certified": False,
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list([] if argv is None else argv)
    if arguments == ["--validate-only"]:
        print(json.dumps(validate_only(), sort_keys=True))
        return 0
    if arguments == ["--execute"]:
        contract.require_execution_review()
        print(json.dumps(run_two_block_nonformal(), sort_keys=True))
        return 0
    raise contract.ContractRejected("only --validate-only or gated --execute is registered")


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
