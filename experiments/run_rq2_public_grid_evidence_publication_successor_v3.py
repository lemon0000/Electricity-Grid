"""Closed V3 controller with runtime-local evidence and publication authority."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from experiments import (
    publish_rq2_public_grid_evidence_publication_successor_v3 as publisher,
)
from experiments import rq2_public_grid_evidence_publication_contract_v3 as contract


def run_review_fixture_e2e(
    root: Path, *, registered_test_case: str | None = None
) -> publisher.ReviewOutcome:
    """Run the sealed nonformal fixture and return no evidence or authority state."""
    import concurrent.futures
    import hmac
    import secrets
    import shutil

    allowed_cases = {
        None,
        "zero_worker_complete_forgery",
        "tamper_hello",
        "tamper_envelope",
        "tamper_ack",
        "tamper_result",
        "tamper_attempt_receipt",
        "tamper_closure_mapping",
        "cross_protocol_v1",
        "cross_protocol_v2",
        "cross_session",
        "replay_0008",
        "swap_blocks",
        "co_tamper_sources",
        "closure_pre_result",
        "extra_before_result_rename",
        "closure_post_result",
        "extra_post_result",
        "closure_post_success",
        "corrupt_post_success",
    }
    if registered_test_case not in allowed_cases:
        raise contract.ContractRejected("unregistered V3 review test case")
    if root.exists() or root.is_symlink():
        raise contract.ContractRejected("V3 review root must be clean absent")
    root.mkdir(parents=True, exist_ok=False)
    session_root = root / "session"
    session_root.mkdir()
    paths = publisher.publication_paths(root / "published")
    config = contract.load_config()
    auth_material = secrets.token_bytes(32)
    session_id = secrets.token_hex(32)
    records: list[dict[str, Any]] = []
    attempted: set[int] = set()
    active = False
    worker_pids: list[int] = []
    pipe_digests: list[str] = []
    fault_stage = {
        "closure_pre_result": "controller_post_block2_pre_result",
        "closure_post_result": "controller_post_result_pre_success",
        "closure_post_success": "controller_post_success_readback",
    }.get(registered_test_case)
    verifier = contract.StageAwareClosureVerifier(fault_stage)

    def outcome(classification: str, *, published: bool) -> publisher.ReviewOutcome:
        return publisher.ReviewOutcome(
            classification=classification,
            published=published,
            review_fixture=True,
            nonformal=True,
            claim=False,
            mathematical_infeasibility_inferred=False,
            worker_processes_started=len(worker_pids),
            worker_pids=tuple(worker_pids),
            pipe_authority_digests=tuple(pipe_digests),
            pipe_authority_verified=bool(pipe_digests),
            parent_identity_verified=bool(pipe_digests),
            raw_handle_roles_verified=bool(pipe_digests),
            scientific_loader_calls=0,
            solver_calls=0,
            result_path=str(paths.result),
            success_path=str(paths.success),
            terminal_path=str(paths.terminal),
        )

    def authentication(value: object) -> str:
        return hmac.new(
            auth_material, contract.exact_json_bytes(value), "sha256"
        ).hexdigest()

    def decode_exact(raw_hex: object, label: str) -> tuple[bytes, dict[str, Any]]:
        if not isinstance(raw_hex, str):
            raise contract.ContractRejected(f"{label} raw hex missing")
        try:
            raw = bytes.fromhex(raw_hex)
            value = json.loads(raw)
        except (ValueError, json.JSONDecodeError) as exc:
            raise contract.ContractRejected(f"{label} raw JSON malformed") from exc
        if not isinstance(value, dict) or contract.exact_json_bytes(value) != raw:
            raise contract.ContractRejected(f"{label} raw bytes are not canonical")
        return raw, value

    def record_body(record: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in record.items()
            if key not in {"record_digest", "controller_hmac"}
        }

    def verify_record(record: dict[str, Any]) -> None:
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
            "closure_mapping",
            "closure_mapping_sha256",
            "pipe_authority",
            "pipe_authority_digest",
            "hello_hex",
            "hello_sha256",
            "envelope_hex",
            "envelope_sha256",
            "ack_hex",
            "ack_sha256",
            "result_path",
            "result_hex",
            "result_sha256",
            "attempt_receipt_path",
            "attempt_receipt_hex",
            "attempt_receipt_sha256",
            "scientific_hex",
            "scientific_sha256",
            "review_fixture",
            "nonformal",
            "claim",
            "scientific_loader_calls",
            "solver_calls",
            "record_digest",
            "controller_hmac",
        }
        if set(record) != expected_keys or record["schema"] != (
            "rq2_public_grid_accepted_evidence_vnext_v3"
        ):
            raise contract.ContractRejected("V3 record exact schema drifted")
        body = record_body(record)
        digest = contract.sha256_bytes(contract.exact_json_bytes(body))
        if record["record_digest"] != digest:
            raise contract.ContractRejected("V3 record digest drifted")
        expected_mac = authentication({"body": body, "record_digest": digest})
        if not hmac.compare_digest(record["controller_hmac"], expected_mac):
            raise contract.ContractRejected("V3 record HMAC rejected")
        index = record["execution_index"]
        if type(index) is not int or index not in (1, 2):
            raise contract.ContractRejected("V3 record index malformed")
        if record["block_id"] != contract.BLOCKS[index - 1]:
            raise contract.ContractRejected("V3 record block/index drifted")
        mapping = contract.verify_full_live_closure()
        mapping_sha = contract.closure_mapping_sha256(mapping)
        if record["closure_mapping"] != mapping or record[
            "closure_mapping_sha256"
        ] != mapping_sha:
            raise contract.ContractRejected("V3 record closure mapping drifted")
        config_raw = contract.read_stable(contract.CONFIG)
        controller_raw = contract.read_stable(Path(__file__))
        worker_path = contract.ROOT / config["bundle"]["members"]["worker"]
        if (
            record["config_sha256"] != contract.sha256_bytes(config_raw)
            or record["controller_source_sha256"]
            != contract.sha256_bytes(controller_raw)
            or record["worker_source_sha256"]
            != contract.sha256_bytes(contract.read_stable(worker_path))
        ):
            raise contract.ContractRejected("V3 module/config identity drifted")
        hello_raw, hello = decode_exact(record["hello_hex"], "HELLO")
        envelope_raw, envelope = decode_exact(record["envelope_hex"], "envelope")
        ack_raw, ack = decode_exact(record["ack_hex"], "ACK")
        result_raw, result = decode_exact(record["result_hex"], "result")
        receipt_raw, receipt = decode_exact(
            record["attempt_receipt_hex"], "attempt receipt"
        )
        scientific_raw, scientific = decode_exact(
            record["scientific_hex"], "scientific payload"
        )
        byte_bindings = (
            (hello_raw, record["hello_sha256"]),
            (envelope_raw, record["envelope_sha256"]),
            (ack_raw, record["ack_sha256"]),
            (result_raw, record["result_sha256"]),
            (receipt_raw, record["attempt_receipt_sha256"]),
            (scientific_raw, record["scientific_sha256"]),
        )
        if any(contract.sha256_bytes(raw) != digest for raw, digest in byte_bindings):
            raise contract.ContractRejected("V3 raw byte/hash binding drifted")
        hello_keys = {
            "schema",
            "worker_identity",
            "parent_identity",
            "parent_identity_verified",
            "command",
            "cwd",
            "config_sha256",
            "worker_source_sha256",
            "closure_mapping_sha256",
            "worker_read",
            "worker_ack",
        }
        envelope_keys = {
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
        ack_keys = {
            "schema",
            "session_id",
            "execution_index",
            "block_id",
            "nonce",
            "worker_identity",
            "hello_sha256",
            "envelope_sha256",
            "result_sha256",
            "attempt_receipt_sha256",
            "scientific_payload_sha256",
            "pipe_authority_digest",
            "closure_mapping_sha256",
            "review_fixture",
            "nonformal",
            "claim",
            "accepted_for_review_ledger",
            "accepted_as_production_result",
        }
        result_keys = {
            "schema",
            "session_id",
            "execution_index",
            "block_id",
            "nonce",
            "hello_sha256",
            "envelope_sha256",
            "pipe_authority_digest",
            "closure_mapping_sha256",
            "scientific_payload",
            "scientific_payload_sha256",
            "review_fixture",
            "nonformal",
            "claim",
            "accepted_for_review_ledger",
            "accepted_as_production_result",
            "scientific_loader_calls",
            "solver_calls",
            "status",
        }
        receipt_keys = {
            "schema",
            "session_id",
            "execution_index",
            "block_id",
            "nonce",
            "result_path",
            "result_sha256",
            "scientific_payload_sha256",
            "pipe_authority_digest",
            "closure_mapping_sha256",
            "review_fixture",
            "nonformal",
            "claim",
            "controller_validated",
            "published",
        }
        if (
            set(hello) != hello_keys
            or set(envelope) != envelope_keys
            or set(ack) != ack_keys
            or set(result) != result_keys
            or set(receipt) != receipt_keys
        ):
            raise contract.ContractRejected("V3 transport/source exact keyset drifted")
        expected_command = contract.exact_worker_command(
            read_handle=int(record["pipe_authority"]["worker_read"]["raw_identifier"]),
            ack_handle=int(record["pipe_authority"]["worker_ack"]["raw_identifier"]),
            parent_pid=int(record["parent_identity"]["pid"]),
            parent_create_time_ns=int(record["parent_identity"]["create_time_ns"]),
        )
        if record["command"] != list(expected_command) or hello[
            "command"
        ] != list(expected_command) or envelope["command"] != list(expected_command):
            raise contract.ContractRejected("V3 exact argv drifted")
        expected_environment = config["runtime"]["sanitized_environment"]
        if (
            record["cwd"] != str(contract.ROOT)
            or envelope["cwd"] != str(contract.ROOT)
            or record["environment"] != expected_environment
            or envelope["environment"] != expected_environment
            or record["environment_sha256"]
            != contract.sha256_bytes(contract.exact_json_bytes(expected_environment))
        ):
            raise contract.ContractRejected("V3 cwd/environment authority drifted")
        pipe = record["pipe_authority"]
        if (
            not isinstance(pipe, dict)
            or set(pipe)
            != {"worker_read", "worker_ack", "controller_write", "controller_read"}
            or contract.sha256_bytes(contract.exact_json_bytes(pipe))
            != record["pipe_authority_digest"]
            or envelope["pipe_authority"] != pipe
            or envelope["pipe_authority_digest"] != record["pipe_authority_digest"]
            or ack["pipe_authority_digest"] != record["pipe_authority_digest"]
            or result["pipe_authority_digest"] != record["pipe_authority_digest"]
            or receipt["pipe_authority_digest"] != record["pipe_authority_digest"]
        ):
            raise contract.ContractRejected("V3 pipe authority binding drifted")
        expected_pipe = config["pipe_authority"]
        for label in pipe:
            observed = pipe[label]
            expected = expected_pipe[label]
            if (
                observed.get("type") != "anonymous_pipe"
                or observed.get("role") != expected["role"]
                or observed.get("direction") != expected["direction"]
                or observed.get("inherited") is not expected["inherited"]
                or type(observed.get("raw_identifier")) is not int
            ):
                raise contract.ContractRejected("V3 pipe role/type/direction drifted")
        common = ("session_id", "execution_index", "block_id", "nonce")
        if any(
            value[key] != record[key]
            for value in (envelope, ack, result, receipt)
            for key in common
        ):
            raise contract.ContractRejected("V3 frame/source identity drifted")
        if (
            hello["worker_identity"] != record["worker_identity"]
            or envelope["worker_identity"] != record["worker_identity"]
            or ack["worker_identity"] != record["worker_identity"]
            or hello["parent_identity"] != record["parent_identity"]
            or envelope["parent_identity"] != record["parent_identity"]
            or hello["parent_identity_verified"] is not True
        ):
            raise contract.ContractRejected("V3 PID/PPID/create-time binding drifted")
        if (
            envelope["closure_mapping"] != mapping
            or envelope["closure_mapping_sha256"] != mapping_sha
            or ack["closure_mapping_sha256"] != mapping_sha
            or result["closure_mapping_sha256"] != mapping_sha
            or receipt["closure_mapping_sha256"] != mapping_sha
        ):
            raise contract.ContractRejected("V3 frame closure binding drifted")
        if (
            ack["hello_sha256"] != record["hello_sha256"]
            or result["hello_sha256"] != record["hello_sha256"]
            or ack["envelope_sha256"] != record["envelope_sha256"]
            or result["envelope_sha256"] != record["envelope_sha256"]
            or ack["result_sha256"] != record["result_sha256"]
            or receipt["result_sha256"] != record["result_sha256"]
            or ack["attempt_receipt_sha256"]
            != record["attempt_receipt_sha256"]
        ):
            raise contract.ContractRejected("V3 frame/source hash cross-binding drifted")
        if (
            result["scientific_payload"] != scientific
            or contract.exact_json_bytes(scientific) != scientific_raw
            or any(
                value["scientific_payload_sha256"] != record["scientific_sha256"]
                for value in (envelope, ack, result, receipt)
            )
        ):
            raise contract.ContractRejected("V3 scientific byte binding drifted")
        contract.validate_scientific_payload(scientific, record["block_id"])
        if (
            record["review_fixture"] is not True
            or record["nonformal"] is not True
            or record["claim"] is not False
            or record["scientific_loader_calls"] != 0
            or record["solver_calls"] != 0
            or ack["accepted_for_review_ledger"] is not True
            or ack["accepted_as_production_result"] is not False
            or result["accepted_for_review_ledger"] is not True
            or result["accepted_as_production_result"] is not False
            or receipt["controller_validated"] is not False
            or receipt["published"] is not False
        ):
            raise contract.ContractRejected("V3 review/claim semantics drifted")
        result_path = Path(record["result_path"])
        receipt_path = Path(record["attempt_receipt_path"])
        if (
            result_path.name != "worker_result.json"
            or receipt_path != result_path.with_name("attempt_receipt.json")
            or result_path
            != Path(envelope["attempt_root"]) / "worker_result.json"
            or contract.read_stable(result_path) != result_raw
            or contract.read_stable(receipt_path) != receipt_raw
            or receipt["result_path"] != str(result_path)
        ):
            raise contract.ContractRejected("V3 source path/bytes drifted")

    def verify_history(candidate: list[dict[str, Any]]) -> None:
        if len(candidate) not in (1, 2):
            raise contract.ContractRejected("V3 history inventory rejected")
        seen_nonce: set[str] = set()
        seen_pid: set[int] = set()
        predecessor: str | None = None
        for index, record in enumerate(candidate, 1):
            verify_record(record)
            if (
                record["session_id"] != session_id
                or record["execution_index"] != index
                or record["block_id"] != contract.BLOCKS[index - 1]
                or record["predecessor_digest"] != predecessor
                or record["nonce"] in seen_nonce
                or record["worker_identity"]["pid"] in seen_pid
            ):
                raise contract.ContractRejected("V3 history replay/order/session rejected")
            seen_nonce.add(record["nonce"])
            seen_pid.add(record["worker_identity"]["pid"])
            predecessor = record["record_digest"]

    def controller_receipt(candidate: list[dict[str, Any]]) -> dict[str, Any]:
        verify_history(candidate)
        if len(candidate) != 2:
            raise contract.ContractRejected("V3 controller receipt requires two records")
        mapping = contract.verify_full_live_closure()
        body = {
            "schema": "rq2_public_grid_controller_receipt_vnext_v3",
            "session_id": session_id,
            "purpose": "review_fixture_zero_solver",
            "record_digests": [item["record_digest"] for item in candidate],
            "ledger_sha256": contract.sha256_bytes(contract.exact_json_bytes(candidate)),
            "closure_mapping": mapping,
            "closure_mapping_sha256": contract.closure_mapping_sha256(mapping),
            "review_fixture": True,
            "nonformal": True,
            "claim": False,
        }
        return {**body, "controller_hmac": authentication(body)}

    def verify_receipt(receipt: dict[str, Any], candidate: list[dict[str, Any]]) -> None:
        expected = controller_receipt(candidate)
        if receipt != expected or not hmac.compare_digest(
            receipt["controller_hmac"], expected["controller_hmac"]
        ):
            raise contract.ContractRejected("V3 controller receipt HMAC rejected")

    def bounded_call(
        process: subprocess.Popen[Any], function: Any, *, deadline: float, label: str
    ) -> Any:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise contract.ContractRejected(f"{label} exceeded watchdog")
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(function)
            try:
                return future.result(timeout=remaining)
            except concurrent.futures.TimeoutError as exc:
                if process.poll() is None:
                    process.terminate()
                raise contract.ContractRejected(f"{label} exceeded watchdog") from exc

    def child_raw(descriptor: int) -> int:
        if os.name != "nt":
            return descriptor
        import msvcrt

        return int(msvcrt.get_osfhandle(descriptor))

    def dispatch(index: int) -> None:
        nonlocal active
        if active or index in attempted or index != len(attempted) + 1:
            raise contract.ContractRejected("V3 concurrent/retry/reorder rejected")
        if index == 2 and len(records) != 1:
            raise contract.ContractRejected("V3 0009 requires accepted 0008")
        attempted.add(index)
        active = True
        from experiments import (
            run_rq2_public_grid_two_block_pilot_activation_transport_v5 as resources,
        )

        resources.preflight_available_commit()
        mapping = contract.verify_full_live_closure()
        mapping_sha = contract.closure_mapping_sha256(mapping)
        block_id = contract.BLOCKS[index - 1]
        nonce = secrets.token_hex(32)
        parent_identity = {
            "pid": os.getpid(),
            "create_time_ns": contract.process_create_time_ns(os.getpid()),
        }
        controller_read, worker_ack_descriptor = os.pipe()
        worker_read_descriptor, controller_write = os.pipe()
        worker_read_handle = child_raw(worker_read_descriptor)
        worker_ack_handle = child_raw(worker_ack_descriptor)
        controller_read_handle = child_raw(controller_read)
        controller_write_handle = child_raw(controller_write)
        process: subprocess.Popen[Any] | None = None
        try:
            if os.name == "nt":
                os.set_handle_inheritable(worker_read_handle, True)
                os.set_handle_inheritable(worker_ack_handle, True)
            else:
                os.set_inheritable(worker_read_descriptor, True)
                os.set_inheritable(worker_ack_descriptor, True)
            worker_read_observed = contract.observe_pipe_endpoint(
                worker_read_handle,
                role="controller_to_worker",
                direction="read",
                inherited=True,
            )
            worker_ack_observed = contract.observe_pipe_endpoint(
                worker_ack_handle,
                role="worker_to_controller",
                direction="write",
                inherited=True,
            )
            controller_write_observed = contract.observe_pipe_endpoint(
                controller_write_handle,
                role="controller_to_worker",
                direction="write",
                inherited=False,
            )
            controller_read_observed = contract.observe_pipe_endpoint(
                controller_read_handle,
                role="worker_to_controller",
                direction="read",
                inherited=False,
            )
            command = list(
                contract.exact_worker_command(
                    read_handle=worker_read_handle,
                    ack_handle=worker_ack_handle,
                    parent_pid=parent_identity["pid"],
                    parent_create_time_ns=parent_identity["create_time_ns"],
                )
            )
            kwargs: dict[str, Any] = {
                "cwd": contract.ROOT,
                "env": dict(config["runtime"]["sanitized_environment"]),
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL,
                "close_fds": True,
            }
            if os.name == "nt":
                startup = subprocess.STARTUPINFO()
                startup.lpAttributeList = {
                    "handle_list": [worker_read_handle, worker_ack_handle]
                }
                kwargs["startupinfo"] = startup
            else:
                kwargs["pass_fds"] = (
                    worker_read_descriptor,
                    worker_ack_descriptor,
                )
            try:
                process = subprocess.Popen(command, **kwargs)
            finally:
                if os.name == "nt":
                    os.set_handle_inheritable(worker_read_handle, False)
                    os.set_handle_inheritable(worker_ack_handle, False)
                else:
                    os.set_inheritable(worker_read_descriptor, False)
                    os.set_inheritable(worker_ack_descriptor, False)
            worker_pids.append(process.pid)
            os.close(worker_read_descriptor)
            worker_read_descriptor = -1
            os.close(worker_ack_descriptor)
            worker_ack_descriptor = -1
            deadline = time.monotonic() + float(config["runtime"]["watchdog_seconds"])
            hello_raw, hello = bounded_call(
                process,
                lambda: contract.read_frame(controller_read, "worker HELLO"),
                deadline=deadline,
                label="worker HELLO",
            )
            expected_worker_identity = {
                "pid": process.pid,
                "ppid": os.getpid(),
                "create_time_ns": contract.process_create_time_ns(process.pid),
            }
            expected_hello = {
                "schema": "rq2_public_grid_worker_hello_vnext_v3",
                "worker_identity": expected_worker_identity,
                "parent_identity": parent_identity,
                "parent_identity_verified": True,
                "command": command,
                "cwd": str(contract.ROOT),
                "config_sha256": contract.sha256_bytes(
                    contract.read_stable(contract.CONFIG)
                ),
                "worker_source_sha256": contract.sha256_bytes(
                    contract.read_stable(
                        contract.ROOT / config["bundle"]["members"]["worker"]
                    )
                ),
                "closure_mapping_sha256": mapping_sha,
                "worker_read": worker_read_observed,
                "worker_ack": worker_ack_observed,
            }
            if registered_test_case == "tamper_hello":
                hello["parent_identity_verified"] = False
            if hello != expected_hello:
                raise contract.ContractRejected("V3 worker HELLO rejected")
            pipe_authority = {
                "worker_read": worker_read_observed,
                "worker_ack": worker_ack_observed,
                "controller_write": controller_write_observed,
                "controller_read": controller_read_observed,
            }
            pipe_digest = contract.sha256_bytes(
                contract.exact_json_bytes(pipe_authority)
            )
            pipe_digests.append(pipe_digest)
            attempt_root = session_root / "workers" / block_id / nonce
            envelope = {
                "schema": "rq2_public_grid_worker_envelope_vnext_v3",
                "session_id": session_id,
                "execution_index": index,
                "block_id": block_id,
                "predecessor_digest": (
                    None if index == 1 else records[-1]["record_digest"]
                ),
                "nonce": nonce,
                "parent_identity": parent_identity,
                "worker_identity": expected_worker_identity,
                "command": command,
                "cwd": str(contract.ROOT),
                "environment": config["runtime"]["sanitized_environment"],
                "environment_sha256": contract.sha256_bytes(
                    contract.exact_json_bytes(
                        config["runtime"]["sanitized_environment"]
                    )
                ),
                "config_sha256": expected_hello["config_sha256"],
                "worker_source_sha256": expected_hello["worker_source_sha256"],
                "controller_source_sha256": contract.sha256_bytes(
                    contract.read_stable(Path(__file__))
                ),
                "closure_mapping": mapping,
                "closure_mapping_sha256": mapping_sha,
                "pipe_authority": pipe_authority,
                "pipe_authority_digest": pipe_digest,
                "attempt_root": str(attempt_root),
                "scientific_payload_sha256": config["fixture"]["payload_sha256"][
                    block_id
                ],
                "review_fixture": True,
                "nonformal": True,
                "claim": False,
            }
            if registered_test_case == "tamper_envelope":
                envelope["session_id"] = "tampered"
            if registered_test_case == "tamper_closure_mapping":
                envelope["closure_mapping"] = {"forged": "0" * 64}
            envelope_raw = bounded_call(
                process,
                lambda: contract.write_frame(controller_write, envelope),
                deadline=deadline,
                label="controller envelope",
            )
            os.close(controller_write)
            controller_write = -1
            ack_raw, ack = bounded_call(
                process,
                lambda: contract.read_frame(controller_read, "worker ACK"),
                deadline=deadline,
                label="worker ACK",
            )
            bounded_call(
                process,
                lambda: contract.require_eof(controller_read),
                deadline=deadline,
                label="worker ACK EOF",
            )
            if registered_test_case == "tamper_ack":
                ack["pipe_authority_digest"] = "0" * 64
                ack_raw = contract.exact_json_bytes(ack)
            remaining = deadline - time.monotonic()
            if remaining <= 0 or process.wait(timeout=remaining) != 0:
                raise contract.ContractRejected("V3 worker exit rejected")
            resources.monitor_owned_child_resources(
                process,
                expected_pid=process.pid,
                expected_create_time_ns=expected_worker_identity["create_time_ns"],
                watchdog_deadline=deadline,
            )
            verifier.verify("controller_post_child_pre_accept")
            result_path = attempt_root / "worker_result.json"
            receipt_path = attempt_root / "attempt_receipt.json"
            result_raw = contract.read_stable(result_path)
            receipt_raw = contract.read_stable(receipt_path)
            result = json.loads(result_raw)
            receipt = json.loads(receipt_raw)
            if registered_test_case == "tamper_result":
                result["solver_calls"] = 1
                result_raw = contract.exact_json_bytes(result)
            if registered_test_case == "tamper_attempt_receipt":
                receipt["published"] = True
                receipt_raw = contract.exact_json_bytes(receipt)
            scientific = result.get("scientific_payload")
            if not isinstance(scientific, dict):
                raise contract.ContractRejected("V3 worker scientific payload missing")
            scientific_raw = contract.exact_json_bytes(scientific)
            body = {
                "schema": "rq2_public_grid_accepted_evidence_vnext_v3",
                "session_id": session_id,
                "execution_index": index,
                "block_id": block_id,
                "predecessor_digest": (
                    None if index == 1 else records[-1]["record_digest"]
                ),
                "nonce": nonce,
                "parent_identity": parent_identity,
                "worker_identity": expected_worker_identity,
                "command": command,
                "cwd": str(contract.ROOT),
                "environment": config["runtime"]["sanitized_environment"],
                "environment_sha256": envelope["environment_sha256"],
                "config_sha256": envelope["config_sha256"],
                "controller_source_sha256": envelope[
                    "controller_source_sha256"
                ],
                "worker_source_sha256": envelope["worker_source_sha256"],
                "closure_mapping": mapping,
                "closure_mapping_sha256": mapping_sha,
                "pipe_authority": pipe_authority,
                "pipe_authority_digest": pipe_digest,
                "hello_hex": hello_raw.hex(),
                "hello_sha256": contract.sha256_bytes(hello_raw),
                "envelope_hex": envelope_raw.hex(),
                "envelope_sha256": contract.sha256_bytes(envelope_raw),
                "ack_hex": ack_raw.hex(),
                "ack_sha256": contract.sha256_bytes(ack_raw),
                "result_path": str(result_path),
                "result_hex": result_raw.hex(),
                "result_sha256": contract.sha256_bytes(result_raw),
                "attempt_receipt_path": str(receipt_path),
                "attempt_receipt_hex": receipt_raw.hex(),
                "attempt_receipt_sha256": contract.sha256_bytes(receipt_raw),
                "scientific_hex": scientific_raw.hex(),
                "scientific_sha256": contract.sha256_bytes(scientific_raw),
                "review_fixture": True,
                "nonformal": True,
                "claim": False,
                "scientific_loader_calls": 0,
                "solver_calls": 0,
            }
            digest = contract.sha256_bytes(contract.exact_json_bytes(body))
            record = {
                **body,
                "record_digest": digest,
                "controller_hmac": authentication(
                    {"body": body, "record_digest": digest}
                ),
            }
            verify_record(record)
            verify_history([*records, record])
            records.append(record)
        finally:
            active = False
            for descriptor in (
                controller_read,
                worker_ack_descriptor,
                worker_read_descriptor,
                controller_write,
            ):
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

    def exact_result(root_path: Path, candidate: list[dict[str, Any]], receipt: dict[str, Any]) -> bool:
        try:
            manifest = json.loads(contract.read_stable(root_path / "SHA256SUMS.json"))
            if manifest != publisher.typed_tree(root_path):
                return False
            if json.loads(contract.read_stable(root_path / "controller_receipt.json")) != receipt:
                return False
            if json.loads(contract.read_stable(root_path / "closure_mapping.json")) != contract.verify_full_live_closure():
                return False
            for record in candidate:
                destination = root_path / "workers" / record["block_id"]
                if json.loads(contract.read_stable(destination / "accepted_evidence.json")) != record:
                    return False
                for name, key in (
                    ("hello.json", "hello_hex"),
                    ("envelope.json", "envelope_hex"),
                    ("ack.json", "ack_hex"),
                    ("worker_result.json", "result_hex"),
                    ("attempt_receipt.json", "attempt_receipt_hex"),
                    ("scientific_payload.json", "scientific_hex"),
                ):
                    if contract.read_stable(destination / name) != bytes.fromhex(record[key]):
                        return False
                verify_record(record)
            verify_receipt(receipt, candidate)
            return True
        except Exception:  # noqa: BLE001 - exact readback fails closed
            return False

    def exact_success(success_path: Path, receipt: dict[str, Any]) -> bool:
        try:
            success = json.loads(contract.read_stable(success_path / "success.json"))
            manifest = json.loads(contract.read_stable(success_path / "SHA256SUMS.json"))
            if manifest != publisher.typed_tree(success_path):
                return False
            body = {
                key: value for key, value in success.items() if key != "controller_hmac"
            }
            if set(success) != {
                "schema",
                "session_id",
                "classification",
                "published",
                "review_fixture",
                "nonformal",
                "claim",
                "controller_receipt_sha256",
                "result_manifest_sha256",
                "closure_mapping",
                "closure_mapping_sha256",
                "controller_hmac",
            }:
                return False
            return (
                body["schema"] == "rq2_public_grid_success_commit_vnext_v3"
                and body["session_id"] == session_id
                and body["classification"] == "committed_success"
                and body["published"] is True
                and body["review_fixture"] is True
                and body["nonformal"] is True
                and body["claim"] is False
                and body["controller_receipt_sha256"]
                == contract.sha256_bytes(contract.exact_json_bytes(receipt))
                and body["result_manifest_sha256"]
                == contract.sha256_bytes(
                    contract.read_stable(paths.result / "SHA256SUMS.json")
                )
                and body["closure_mapping"] == contract.verify_full_live_closure()
                and body["closure_mapping_sha256"]
                == contract.closure_mapping_sha256(body["closure_mapping"])
                and hmac.compare_digest(success["controller_hmac"], authentication(body))
            )
        except Exception:  # noqa: BLE001 - exact readback fails closed
            return False

    def commit(candidate: list[dict[str, Any]], receipt: dict[str, Any]) -> publisher.ReviewOutcome:
        appeared_result = False
        appeared_success = False
        staging = paths.result.with_name(f".{paths.result.name}.staging.{os.getpid()}")
        success_staging = paths.success.with_name(
            f".{paths.success.name}.staging.{os.getpid()}"
        )
        try:
            verify_history(candidate)
            verify_receipt(receipt, candidate)
            initial = publisher.capture_presence(paths)
            if publisher.classify_publication(
                initial, result_exact=False, success_exact=False
            ) != "honest_incomplete":
                raise contract.ContractRejected("V3 initial publication presence rejected")
            if any(
                path.exists() or path.is_symlink()
                for path in (paths.result, paths.success, paths.terminal)
            ):
                raise contract.ContractRejected("V3 publication path appearance rejected")
            for record in candidate:
                verify_record(record)
            verifier.verify("controller_post_block2_pre_result")
            staging.mkdir(parents=True, exist_ok=False)
            (staging / "workers").mkdir()
            for record in candidate:
                destination = staging / "workers" / record["block_id"]
                destination.mkdir()
                for name, raw in (
                    ("accepted_evidence.json", contract.exact_json_bytes(record)),
                    ("hello.json", bytes.fromhex(record["hello_hex"])),
                    ("envelope.json", bytes.fromhex(record["envelope_hex"])),
                    ("ack.json", bytes.fromhex(record["ack_hex"])),
                    ("worker_result.json", bytes.fromhex(record["result_hex"])),
                    (
                        "attempt_receipt.json",
                        bytes.fromhex(record["attempt_receipt_hex"]),
                    ),
                    (
                        "scientific_payload.json",
                        bytes.fromhex(record["scientific_hex"]),
                    ),
                ):
                    publisher.atomic_write(destination / name, raw)
            publisher.atomic_write(
                staging / "controller_receipt.json", contract.exact_json_bytes(receipt)
            )
            publisher.atomic_write(
                staging / "closure_mapping.json",
                contract.exact_json_bytes(contract.verify_full_live_closure()),
            )
            publisher.atomic_write(
                staging / "summary.json",
                contract.exact_json_bytes(
                    {
                        "schema": "rq2_public_grid_review_fixture_summary_vnext_v3",
                        "record_count": 2,
                        "blocks": list(contract.BLOCKS),
                        "review_fixture": True,
                        "nonformal": True,
                        "claim": False,
                        "scientific_loader_calls": 0,
                        "solver_calls": 0,
                    }
                ),
            )
            publisher.atomic_write(
                staging / "SHA256SUMS.json",
                contract.exact_json_bytes(publisher.typed_tree(staging)),
            )
            if registered_test_case == "extra_before_result_rename":
                (staging / "unexpected-empty-directory").mkdir()
            if not exact_result(staging, candidate, receipt):
                raise contract.ContractRejected("V3 staging exact reread rejected")
            os.replace(staging, paths.result)
            appeared_result = True
            if registered_test_case == "extra_post_result":
                (paths.result / "unexpected-empty-directory").mkdir()
            if not exact_result(paths.result, candidate, receipt):
                raise contract.ContractRejected("V3 result exact reread rejected")
            verifier.verify("controller_post_result_pre_success")
            success_staging.mkdir(parents=True, exist_ok=False)
            mapping = contract.verify_full_live_closure()
            success_body = {
                "schema": "rq2_public_grid_success_commit_vnext_v3",
                "session_id": session_id,
                "classification": "committed_success",
                "published": True,
                "review_fixture": True,
                "nonformal": True,
                "claim": False,
                "controller_receipt_sha256": contract.sha256_bytes(
                    contract.exact_json_bytes(receipt)
                ),
                "result_manifest_sha256": contract.sha256_bytes(
                    contract.read_stable(paths.result / "SHA256SUMS.json")
                ),
                "closure_mapping": mapping,
                "closure_mapping_sha256": contract.closure_mapping_sha256(mapping),
            }
            success = {
                **success_body,
                "controller_hmac": authentication(success_body),
            }
            publisher.atomic_write(
                success_staging / "success.json", contract.exact_json_bytes(success)
            )
            publisher.atomic_write(
                success_staging / "SHA256SUMS.json",
                contract.exact_json_bytes(publisher.typed_tree(success_staging)),
            )
            os.replace(success_staging, paths.success)
            appeared_success = True
            if registered_test_case == "corrupt_post_success":
                (paths.success / "unexpected-empty-directory").mkdir()
            result_exact = exact_result(paths.result, candidate, receipt)
            success_exact = exact_success(paths.success, receipt)
            verifier.verify("controller_post_success_readback")
            final = publisher.capture_presence(paths)
            classification = publisher.classify_publication(
                final, result_exact=result_exact, success_exact=success_exact
            )
            if classification != "committed_success":
                raise contract.ContractRejected("V3 final publication truth rejected")
            return outcome("committed_success", published=True)
        except Exception:  # noqa: BLE001 - publication state is reconciled below
            if appeared_success:
                return outcome("commit_indeterminate", published=False)
            if appeared_result:
                return outcome("commit_indeterminate", published=False)
            if staging.exists():
                shutil.rmtree(staging)
            if success_staging.exists():
                shutil.rmtree(success_staging)
            return outcome("rejected_before_result", published=False)

    try:
        if registered_test_case == "zero_worker_complete_forgery":
            mapping = contract.verify_full_live_closure()
            mapping_sha = contract.closure_mapping_sha256(mapping)
            parent_identity = {
                "pid": os.getpid(),
                "create_time_ns": contract.process_create_time_ns(os.getpid()),
            }
            forged: list[dict[str, Any]] = []
            for index, block_id in enumerate(contract.BLOCKS, 1):
                nonce = f"forged-{index}"
                worker_identity = {
                    "pid": os.getpid() + index,
                    "ppid": os.getpid(),
                    "create_time_ns": parent_identity["create_time_ns"] + index,
                }
                pipe = {
                    label: {**binding, "raw_identifier": 100 + offset}
                    for offset, (label, binding) in enumerate(
                        config["pipe_authority"].items()
                    )
                }
                pipe_digest = contract.sha256_bytes(contract.exact_json_bytes(pipe))
                command = list(
                    contract.exact_worker_command(
                        read_handle=pipe["worker_read"]["raw_identifier"],
                        ack_handle=pipe["worker_ack"]["raw_identifier"],
                        parent_pid=parent_identity["pid"],
                        parent_create_time_ns=parent_identity["create_time_ns"],
                    )
                )
                attempt_root = session_root / f"forged-{block_id}"
                scientific = contract.build_review_fixture_payload(block_id)
                scientific_raw = contract.exact_json_bytes(scientific)
                common = {
                    "session_id": session_id,
                    "execution_index": index,
                    "block_id": block_id,
                    "nonce": nonce,
                }
                hello = {
                    "schema": "rq2_public_grid_worker_hello_vnext_v3",
                    "worker_identity": worker_identity,
                    "parent_identity": parent_identity,
                    "parent_identity_verified": True,
                    "command": command,
                    "cwd": str(contract.ROOT),
                    "config_sha256": contract.sha256_bytes(
                        contract.read_stable(contract.CONFIG)
                    ),
                    "worker_source_sha256": contract.sha256_bytes(
                        contract.read_stable(
                            contract.ROOT / config["bundle"]["members"]["worker"]
                        )
                    ),
                    "closure_mapping_sha256": mapping_sha,
                    "worker_read": pipe["worker_read"],
                    "worker_ack": pipe["worker_ack"],
                }
                hello_raw = contract.exact_json_bytes(hello)
                envelope = {
                    "schema": "rq2_public_grid_worker_envelope_vnext_v3",
                    **common,
                    "predecessor_digest": (
                        None if index == 1 else forged[-1]["record_digest"]
                    ),
                    "parent_identity": parent_identity,
                    "worker_identity": worker_identity,
                    "command": command,
                    "cwd": str(contract.ROOT),
                    "environment": config["runtime"]["sanitized_environment"],
                    "environment_sha256": contract.sha256_bytes(
                        contract.exact_json_bytes(
                            config["runtime"]["sanitized_environment"]
                        )
                    ),
                    "config_sha256": hello["config_sha256"],
                    "worker_source_sha256": hello["worker_source_sha256"],
                    "controller_source_sha256": contract.sha256_bytes(
                        contract.read_stable(Path(__file__))
                    ),
                    "closure_mapping": mapping,
                    "closure_mapping_sha256": mapping_sha,
                    "pipe_authority": pipe,
                    "pipe_authority_digest": pipe_digest,
                    "attempt_root": str(attempt_root),
                    "scientific_payload_sha256": contract.sha256_bytes(scientific_raw),
                    "review_fixture": True,
                    "nonformal": True,
                    "claim": False,
                }
                envelope_raw = contract.exact_json_bytes(envelope)
                result_path = attempt_root / "worker_result.json"
                receipt_path = attempt_root / "attempt_receipt.json"
                result = {
                    "schema": "rq2_public_grid_worker_result_vnext_v3",
                    **common,
                    "hello_sha256": contract.sha256_bytes(hello_raw),
                    "envelope_sha256": contract.sha256_bytes(envelope_raw),
                    "pipe_authority_digest": pipe_digest,
                    "closure_mapping_sha256": mapping_sha,
                    "scientific_payload": scientific,
                    "scientific_payload_sha256": contract.sha256_bytes(scientific_raw),
                    "review_fixture": True,
                    "nonformal": True,
                    "claim": False,
                    "accepted_for_review_ledger": True,
                    "accepted_as_production_result": False,
                    "scientific_loader_calls": 0,
                    "solver_calls": 0,
                    "status": "REVIEW_FIXTURE_COMPLETE",
                }
                result_raw = contract.exact_json_bytes(result)
                receipt = {
                    "schema": "rq2_public_grid_worker_attempt_receipt_vnext_v3",
                    **common,
                    "result_path": str(result_path),
                    "result_sha256": contract.sha256_bytes(result_raw),
                    "scientific_payload_sha256": contract.sha256_bytes(scientific_raw),
                    "pipe_authority_digest": pipe_digest,
                    "closure_mapping_sha256": mapping_sha,
                    "review_fixture": True,
                    "nonformal": True,
                    "claim": False,
                    "controller_validated": False,
                    "published": False,
                }
                receipt_raw = contract.exact_json_bytes(receipt)
                ack = {
                    "schema": "rq2_public_grid_worker_ack_vnext_v3",
                    **common,
                    "worker_identity": worker_identity,
                    "hello_sha256": contract.sha256_bytes(hello_raw),
                    "envelope_sha256": contract.sha256_bytes(envelope_raw),
                    "result_sha256": contract.sha256_bytes(result_raw),
                    "attempt_receipt_sha256": contract.sha256_bytes(receipt_raw),
                    "scientific_payload_sha256": contract.sha256_bytes(scientific_raw),
                    "pipe_authority_digest": pipe_digest,
                    "closure_mapping_sha256": mapping_sha,
                    "review_fixture": True,
                    "nonformal": True,
                    "claim": False,
                    "accepted_for_review_ledger": True,
                    "accepted_as_production_result": False,
                }
                ack_raw = contract.exact_json_bytes(ack)
                body = {
                    "schema": "rq2_public_grid_accepted_evidence_vnext_v3",
                    **common,
                    "predecessor_digest": envelope["predecessor_digest"],
                    "parent_identity": parent_identity,
                    "worker_identity": worker_identity,
                    "command": command,
                    "cwd": str(contract.ROOT),
                    "environment": config["runtime"]["sanitized_environment"],
                    "environment_sha256": envelope["environment_sha256"],
                    "config_sha256": hello["config_sha256"],
                    "controller_source_sha256": envelope[
                        "controller_source_sha256"
                    ],
                    "worker_source_sha256": hello["worker_source_sha256"],
                    "closure_mapping": mapping,
                    "closure_mapping_sha256": mapping_sha,
                    "pipe_authority": pipe,
                    "pipe_authority_digest": pipe_digest,
                    "hello_hex": hello_raw.hex(),
                    "hello_sha256": contract.sha256_bytes(hello_raw),
                    "envelope_hex": envelope_raw.hex(),
                    "envelope_sha256": contract.sha256_bytes(envelope_raw),
                    "ack_hex": ack_raw.hex(),
                    "ack_sha256": contract.sha256_bytes(ack_raw),
                    "result_path": str(result_path),
                    "result_hex": result_raw.hex(),
                    "result_sha256": contract.sha256_bytes(result_raw),
                    "attempt_receipt_path": str(receipt_path),
                    "attempt_receipt_hex": receipt_raw.hex(),
                    "attempt_receipt_sha256": contract.sha256_bytes(receipt_raw),
                    "scientific_hex": scientific_raw.hex(),
                    "scientific_sha256": contract.sha256_bytes(scientific_raw),
                    "review_fixture": True,
                    "nonformal": True,
                    "claim": False,
                    "scientific_loader_calls": 0,
                    "solver_calls": 0,
                }
                record_digest = contract.sha256_bytes(contract.exact_json_bytes(body))
                forged.append(
                    {
                        **body,
                        "record_digest": record_digest,
                        "controller_hmac": "0" * 64,
                    }
                )
            forged_receipt = {
                "schema": "rq2_public_grid_controller_receipt_vnext_v3",
                "session_id": session_id,
                "purpose": "review_fixture_zero_solver",
                "record_digests": [item["record_digest"] for item in forged],
                "ledger_sha256": contract.sha256_bytes(
                    contract.exact_json_bytes(forged)
                ),
                "closure_mapping": mapping,
                "closure_mapping_sha256": mapping_sha,
                "review_fixture": True,
                "nonformal": True,
                "claim": False,
                "controller_hmac": "0" * 64,
            }
            return commit(forged, forged_receipt)
        dispatch(1)
        dispatch(2)
        if registered_test_case == "cross_session":
            records[1]["session_id"] = "forged-cross-session"
        elif registered_test_case == "replay_0008":
            records[1] = dict(records[0])
        elif registered_test_case == "swap_blocks":
            records[:] = [records[1], records[0]]
        elif registered_test_case == "cross_protocol_v1":
            records[0]["schema"] = "rq2_public_grid_accepted_evidence_vnext_v1"
        elif registered_test_case == "cross_protocol_v2":
            records[0]["schema"] = "rq2_public_grid_accepted_evidence_vnext_v2"
        elif registered_test_case == "co_tamper_sources":
            first = records[0]
            source = Path(first["result_path"])
            value = json.loads(source.read_bytes())
            value["solver_calls"] = 1
            source.write_bytes(contract.exact_json_bytes(value))
            first["result_hex"] = source.read_bytes().hex()
            first["result_sha256"] = contract.sha256_bytes(source.read_bytes())
        verify_history(records)
        receipt = controller_receipt(records)
        return commit(records, receipt)
    except Exception:  # noqa: BLE001 - review fixture rejects every unexpected failure
        return outcome("rejected_before_result", published=False)


def main(argv: list[str] | None = None) -> int:
    arguments = list([] if argv is None else argv)
    if arguments != ["--validate-only"]:
        raise contract.ContractRejected(
            "V3 remains review closed; production/pilot/formal execution is forbidden"
        )
    mapping = contract.verify_full_live_closure()
    print(
        json.dumps(
            {
                "validation_passed": True,
                "status": "evidence_publication_successor_v3_review_closed",
                "closure_inventory_count": len(mapping),
                "closure_mapping_sha256": contract.closure_mapping_sha256(mapping),
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
