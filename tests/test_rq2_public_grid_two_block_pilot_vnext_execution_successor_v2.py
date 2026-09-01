from __future__ import annotations

import copy
import importlib
import json
import os
import subprocess
import threading
from pathlib import Path

import pytest

from experiments import (
    bootstrap_rq2_public_grid_two_block_pilot_vnext_execution_successor_v2 as bootstrap,
)
from experiments import (
    publish_rq2_public_grid_evidence_publication_successor_v3 as publisher,
)
from experiments import (
    rq2_public_grid_two_block_pilot_vnext_execution_contract_v2 as contract,
)
from experiments import (
    run_rq2_public_grid_two_block_pilot_activation_transport_v5 as resources,
)
from experiments import (
    run_rq2_public_grid_two_block_pilot_vnext_execution_successor_v2 as controller,
)


def test_candidate_modules_exist() -> None:
    for module in (
        "experiments.rq2_public_grid_two_block_pilot_vnext_execution_contract_v2",
        "experiments.run_rq2_public_grid_two_block_pilot_vnext_execution_successor_v2",
        "experiments.worker_rq2_public_grid_two_block_pilot_vnext_execution_successor_v2",
        "experiments.bootstrap_rq2_public_grid_two_block_pilot_vnext_execution_successor_v2",
    ):
        assert importlib.import_module(module)


def test_v2_self_bundle_verifier_reads_exact_seal_and_members() -> None:
    trace: list[str] = []
    mapping = contract.verify_self_bundle(trace=trace)
    config = contract.load_config()
    expected = {
        config["bundle"]["outer_path"],
        config["bundle"]["inner_path"],
        *config["bundle"]["members"],
    }
    assert set(mapping) == expected
    assert len(mapping) == config["bundle"]["self_mapping_exact_count"] == 9
    assert expected <= set(trace)
    for required in (
        "experiments/run_rq2_public_grid_two_block_pilot_vnext_execution_successor_v2.py",
        "experiments/worker_rq2_public_grid_two_block_pilot_vnext_execution_successor_v2.py",
        "experiments/bootstrap_rq2_public_grid_two_block_pilot_vnext_execution_successor_v2.py",
    ):
        assert required in trace


def test_v2_protocol_exact_validators_are_registered() -> None:
    for name in (
        "validate_worker_hello",
        "validate_worker_envelope",
        "validate_worker_ack",
        "validate_worker_result",
        "validate_attempt_receipt",
    ):
        assert callable(getattr(contract, name))


def _protocol_fixture() -> dict[str, object]:
    session_id = "a" * 64
    nonce = "b" * 64
    parent = {"pid": 101, "create_time_ns": 202}
    worker = {"pid": 303, "ppid": 101, "create_time_ns": 404}
    worker_read = {
        "raw_identifier": 501,
        "type": "anonymous_pipe",
        "role": "controller_to_worker",
        "direction": "read",
        "inherited": True,
    }
    worker_ack = {
        "raw_identifier": 502,
        "type": "anonymous_pipe",
        "role": "worker_to_controller",
        "direction": "write",
        "inherited": True,
    }
    command = contract.exact_worker_command(
        mode="science",
        read_handle=501,
        ack_handle=502,
        parent_pid=101,
        parent_create_time_ns=202,
        session_id=session_id,
        execution_index=1,
        block_id=contract.BLOCKS[0],
        predecessor_digest=None,
        nonce=nonce,
    )
    hello_args = {
        "mode": "science",
        "session_id": session_id,
        "execution_index": 1,
        "block_id": contract.BLOCKS[0],
        "predecessor_digest": None,
        "nonce": nonce,
        "parent_identity": parent,
        "worker_identity": worker,
        "command": command,
        "worker_read": worker_read,
        "worker_ack": worker_ack,
    }
    hello = contract.build_worker_hello(**hello_args)
    hello_raw = contract.exact_json_bytes(hello)
    pipe = {
        "worker_read": worker_read,
        "worker_ack": worker_ack,
        "controller_write": {
            "raw_identifier": 503,
            "type": "anonymous_pipe",
            "role": "controller_to_worker",
            "direction": "write",
            "inherited": False,
        },
        "controller_read": {
            "raw_identifier": 504,
            "type": "anonymous_pipe",
            "role": "worker_to_controller",
            "direction": "read",
            "inherited": False,
        },
    }
    attempt_root = str(contract.ROOT / "review_fixture" / session_id / nonce)
    envelope_args = {
        "hello": hello,
        "hello_raw": hello_raw,
        "pipe_authority": pipe,
        "attempt_root": attempt_root,
    }
    envelope = contract.build_worker_envelope(**envelope_args)
    envelope_raw = contract.exact_json_bytes(envelope)
    result_args = {
        "hello": hello,
        "hello_raw": hello_raw,
        "envelope": envelope,
        "envelope_raw": envelope_raw,
        "scientific_payload": {
            "block_id": contract.BLOCKS[0],
            "all_hours_resolved": True,
        },
        "solver_call_accounting": {
            "solver_calls": 3,
            "source": "validated_payload",
        },
    }
    result = contract.build_worker_result(**result_args)
    result_raw = contract.exact_json_bytes(result)
    receipt_args = {
        "hello": hello,
        "envelope": envelope,
        "result": result,
        "result_raw": result_raw,
        "result_path": str(Path(attempt_root) / "worker_result.json"),
    }
    receipt = contract.build_attempt_receipt(**receipt_args)
    receipt_raw = contract.exact_json_bytes(receipt)
    ack_args = {
        "hello": hello,
        "envelope": envelope,
        "result": result,
        "result_raw": result_raw,
        "receipt_raw": receipt_raw,
    }
    return {
        "hello": hello,
        "hello_args": hello_args,
        "envelope": envelope,
        "envelope_args": envelope_args,
        "result": result,
        "result_args": result_args,
        "receipt": receipt,
        "receipt_args": receipt_args,
        "ack": contract.build_worker_ack(**ack_args),
        "ack_args": ack_args,
    }


def test_exact_protocol_transcript_and_science_hash_chain() -> None:
    fixture = _protocol_fixture()
    hello = contract.validate_worker_hello(
        fixture["hello"], **fixture["hello_args"]
    )
    envelope = contract.validate_worker_envelope(
        fixture["envelope"], **fixture["envelope_args"]
    )
    result = contract.validate_worker_result(
        fixture["result"], **fixture["result_args"]
    )
    receipt = contract.validate_attempt_receipt(
        fixture["receipt"], **fixture["receipt_args"]
    )
    ack = contract.validate_worker_ack(fixture["ack"], **fixture["ack_args"])
    digest = result["scientific_payload_sha256"]
    assert ack["scientific_payload_sha256"] == digest
    assert receipt["scientific_payload_sha256"] == digest
    assert envelope["transport_context"] == contract.hello_transport_context(hello)


@pytest.mark.parametrize(
    ("message", "field", "replacement", "validator", "args"),
    [
        ("hello", "config_sha256", "0" * 64, "validate_worker_hello", "hello_args"),
        ("hello", "controller_source_sha256", "1" * 64, "validate_worker_hello", "hello_args"),
        ("hello", "worker_source_sha256", "2" * 64, "validate_worker_hello", "hello_args"),
        (
            "hello",
            "worker_read",
            {
                "raw_identifier": 999,
                "type": "anonymous_pipe",
                "role": "controller_to_worker",
                "direction": "read",
                "inherited": True,
            },
            "validate_worker_hello",
            "hello_args",
        ),
        ("envelope", "hello_sha256", "3" * 64, "validate_worker_envelope", "envelope_args"),
        ("result", "scientific_payload_sha256", "4" * 64, "validate_worker_result", "result_args"),
        ("receipt", "solver_call_accounting_sha256", "5" * 64, "validate_attempt_receipt", "receipt_args"),
        ("ack", "attempt_receipt_sha256", "6" * 64, "validate_worker_ack", "ack_args"),
    ],
)
def test_protocol_arbitrary_authority_or_cross_hash_rejected(
    message: str,
    field: str,
    replacement: object,
    validator: str,
    args: str,
) -> None:
    fixture = _protocol_fixture()
    forged = copy.deepcopy(fixture[message])
    forged[field] = replacement
    with pytest.raises(contract.ContractRejected):
        getattr(contract, validator)(forged, **fixture[args])


@pytest.mark.parametrize("message", ["hello", "envelope", "result", "receipt", "ack"])
def test_protocol_extra_missing_and_cross_protocol_keys_rejected(message: str) -> None:
    fixture = _protocol_fixture()
    validator = {
        "hello": contract.validate_worker_hello,
        "envelope": contract.validate_worker_envelope,
        "result": contract.validate_worker_result,
        "receipt": contract.validate_attempt_receipt,
        "ack": contract.validate_worker_ack,
    }[message]
    args = fixture[f"{message}_args"]
    extra = copy.deepcopy(fixture[message])
    extra["unregistered"] = True
    with pytest.raises(contract.ContractRejected):
        validator(extra, **args)
    missing = copy.deepcopy(fixture[message])
    missing.pop(next(iter(missing)))
    with pytest.raises(contract.ContractRejected):
        validator(missing, **args)
    wrong = copy.deepcopy(fixture[message])
    wrong["schema"] = "rq2_public_grid_cross_protocol_v1"
    with pytest.raises(contract.ContractRejected):
        validator(wrong, **args)


def test_v3_pass_receipt_binds_review_and_grants_no_execution() -> None:
    config = contract.load_config()
    receipt_path = contract.ROOT / config["predecessor_v3"]["pass_receipt_path"]
    raw = contract.read_stable(receipt_path)
    assert contract.sha256_bytes(raw) == config["predecessor_v3"]["pass_receipt_sha256"]
    receipt = json.loads(raw)
    assert receipt["verdict"] == "PASS"
    assert receipt["review_conclusion"]["sealed_execution_trace_exact_count"] == 68
    assert receipt["review_conclusion"]["successor_closure_exact_count"] == 95
    assert receipt["effect"]["versioned_nonformal_execution_successor_creation_authorized"] is True
    assert receipt["effect"]["successor_execution_authorized"] is False
    assert receipt["effect"]["pilot_execution_authorized"] is False
    assert receipt["effect"]["formal_execution_authorized"] is False


def test_live_authority_preserves_exact_v3_closure() -> None:
    config = contract.load_config()
    trace: list[str] = []
    mapping = contract.verify_live_authorities(trace=trace)
    v3_mapping = contract.v3.verify_full_live_closure()
    assert len(v3_mapping) == 95
    assert contract.v3.closure_mapping_sha256(v3_mapping) == config["predecessor_v3"][
        "closure_mapping_sha256"
    ]
    assert all(mapping[path] == digest for path, digest in v3_mapping.items())
    self_mapping = contract.verify_self_bundle()
    activated_config = config["formal_protection"]["activated_config_path"]
    assert set(mapping) == set(v3_mapping) | set(self_mapping) | {activated_config}
    assert len(mapping) == 105
    for required in (
        config["science_authority"]["execution_contract_path"],
        config["science_authority"]["candidate_v4_path"],
        config["science_authority"]["recovery_runner_path"],
        "experiments/publish_rq2_public_grid_evidence_publication_successor_v3.py",
    ):
        assert required in trace


def test_validate_only_is_closed_and_zero_execution() -> None:
    outcome = controller.validate_only()
    assert outcome["validation_passed"] is True
    assert outcome["v3_closure_inventory_count"] == 95
    assert outcome["execution_review_present"] is False
    assert outcome["execution_ready"] is False
    assert outcome["worker_processes_started"] == 0
    assert outcome["scientific_loader_calls"] == 0
    assert outcome["solver_calls"] == 0
    assert outcome["result_writes"] == 0
    assert outcome["pilot_executed"] is False
    assert outcome["formal_execution_ready"] is False


def test_execute_absent_receipt_rejects_before_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def forbidden() -> dict[str, object]:
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(controller, "run_two_block_nonformal", forbidden)
    with pytest.raises(contract.ContractRejected, match="receipt is absent"):
        controller.main(["--execute"])
    assert called is False


def test_future_review_receipt_is_external_to_noncyclic_bundle() -> None:
    config = contract.load_config()
    review = config["fixed_execution_review"]["path"]
    assert review not in config["bundle"]["members"]
    assert config["fixed_execution_review"]["present"] is False
    assert config["fixed_execution_review"]["path_cli_configurable"] is False
    assert config["fixed_execution_review"]["self_signing_allowed"] is False
    assert not (contract.ROOT / review).exists()


def test_bundle_seal_is_exact_and_noncyclic() -> None:
    config, outer_sha256 = bootstrap._verify_bundle()
    assert len(config["bundle"]["members"]) == 7
    assert config["fixed_execution_review"]["path"] not in config["bundle"]["members"]
    assert len(outer_sha256) == 64


def test_canonical_direct_script_validate_and_closed_execute() -> None:
    config = contract.load_config()
    command = [
        config["runtime"]["locked_python_executable"],
        "-B",
        str(contract.ROOT / "experiments/bootstrap_rq2_public_grid_two_block_pilot_vnext_execution_successor_v2.py"),
    ]
    validated = subprocess.run(
        [*command, "--validate-only"],
        cwd=contract.ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert validated.returncode == 0, validated.stderr
    value = json.loads(validated.stdout)
    assert value["validation_passed"] is True
    assert value["worker_processes_started"] == 0
    assert value["scientific_loader_calls"] == 0
    assert value["solver_calls"] == 0
    assert value["result_writes"] == 0
    rejected = subprocess.run(
        [*command, "--execute"],
        cwd=contract.ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert rejected.returncode != 0
    assert "fixed execution-review PASS receipt is absent" in rejected.stderr


def test_future_review_receipt_requires_exact_outer_chain_and_effect() -> None:
    config = contract.load_config()
    outer = config["bundle"]["outer_path"]
    predecessor = config["predecessor_v3"]
    value = {
        "schema": config["fixed_execution_review"]["schema"],
        "version": 2,
        "reviewed_on": "2026-08-31",
        "reviewer_role": "independent_sol_reviewer",
        "verdict": "PASS",
        "reviewed_outer": {
            "path": outer,
            "sha256": contract.sha256_bytes(contract.read_stable(contract.ROOT / outer)),
        },
        "bound_v3_outer": {
            "path": predecessor["outer_path"],
            "sha256": predecessor["outer_sha256"],
        },
        "bound_v3_pass_receipt": {
            "path": predecessor["pass_receipt_path"],
            "sha256": predecessor["pass_receipt_sha256"],
        },
        "findings": [],
        "effect": config["fixed_execution_review"]["effect"],
    }
    contract.validate_execution_review_object(value)
    forged = json.loads(json.dumps(value))
    forged["effect"]["formal_execution_authorized"] = True
    with pytest.raises(contract.ContractRejected):
        contract.validate_execution_review_object(forged)


def test_real_preloader_child_stops_before_loader_solver_and_writes() -> None:
    roots = [contract.ROOT / value for value in contract.load_config()["paths"].values()]
    assert all(not path.exists() for path in roots)
    outcome = controller.run_review_preloader_e2e()
    assert outcome["status"] == "NON_ACCEPTED_PRELOADER_BOUNDARY"
    assert outcome["accepted"] is False
    assert outcome["worker_exited"] is True
    assert outcome["command"][:4] == [
        contract.load_config()["runtime"]["locked_python_executable"],
        "-B",
        "-m",
        contract.load_config()["runtime"]["worker_module"],
    ]
    assert outcome["scientific_loader_calls"] == 0
    assert outcome["solver_calls"] == 0
    assert outcome["result_writes"] == 0
    assert all(not path.exists() for path in roots)


def test_registered_zero_solver_seam_proves_actual_science_hook_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from experiments import rq2_public_grid_execution_runtime_contract_v3 as science

    calls: list[str] = []
    payload = {"block_id": contract.BLOCKS[0], "all_hours_resolved": True}

    class Verifier:
        def verify(self, stage: str) -> None:
            calls.append(stage)

    class RecoveryV4:
        @staticmethod
        def _process_block(*args: object, **kwargs: object) -> dict[str, object]:
            calls.append("process_block")
            return dict(payload)

    class Recovery:
        v4 = RecoveryV4()

    class V4:
        recovery = Recovery()

        @staticmethod
        def _stage_context() -> dict[str, object]:
            calls.append("stage_context")
            return {
                "blocks": {contract.BLOCKS[0]: [object()]},
                "config": {
                    "model": {"dc_bus": 108, "dc_reference_demand_mw": 250.0},
                    "solver": {},
                },
            }

        @staticmethod
        def _load_worker_data(context: object) -> object:
            calls.append("load_worker_data")
            return object()

    class Integration:
        v4 = V4()

        @staticmethod
        def validate_scientific_payload(value: object, block_id: str) -> dict[str, object]:
            calls.append("validate_scientific_payload")
            assert block_id == contract.BLOCKS[0]
            return dict(payload)

    monkeypatch.setattr(contract, "require_execution_review", dict)
    monkeypatch.setattr(contract, "verify_live_authorities", dict)
    monkeypatch.setattr(science.StageAwareClosureVerifier, "production", lambda: Verifier())
    monkeypatch.setattr(science, "load_sealed_actual_integration", lambda verifier: Integration())
    monkeypatch.setattr(
        science,
        "solver_call_accounting",
        lambda value: {"solver_calls": 3},
    )
    observed, accounting = contract.run_actual_science(contract.BLOCKS[0])
    assert observed == payload
    assert accounting == {"solver_calls": 3}
    assert calls == [
        "worker_pre_loader",
        "stage_context",
        "load_worker_data",
        "process_block",
        "worker_post_solve_pre_validator",
        "validate_scientific_payload",
        "worker_post_validator_pre_write",
    ]


@pytest.mark.parametrize(
    ("private", "available", "reason"),
    [
        (8 * 1024**3 - 1, 2 * 1024**3 + 1, None),
        (8 * 1024**3, 2 * 1024**3 + 1, "private_commit_limit_reached"),
        (8 * 1024**3 + 1, 2 * 1024**3 + 1, "private_commit_limit_reached"),
        (8 * 1024**3 - 1, 2 * 1024**3 - 1, "system_commit_reserve_reached"),
        (8 * 1024**3 - 1, 2 * 1024**3, "system_commit_reserve_reached"),
        (8 * 1024**3, 2 * 1024**3, "private_and_system_commit_limits_reached"),
    ],
)
def test_resource_boundaries_are_exact_same_sample(
    private: int, available: int, reason: str | None
) -> None:
    assert resources._stop_reason(resources.ResourceSample(private, available)) == reason


def test_attempt_ledger_enforces_order_predecessor_and_no_retry() -> None:
    ledger = controller.AttemptLedger()
    assert ledger.consume(1) is None
    with pytest.raises(contract.ContractRejected):
        ledger.consume(1)
    ledger.finish(1, "accepted-0008")
    assert ledger.consume(2) == "accepted-0008"
    ledger.finish(2, "accepted-0009")
    with pytest.raises(contract.ContractRejected):
        ledger.consume(2)


def test_failed_0008_consumes_attempt_and_never_unlocks_0009() -> None:
    ledger = controller.AttemptLedger()
    assert ledger.consume(1) is None
    ledger.finish(1, None)
    with pytest.raises(contract.ContractRejected):
        ledger.consume(1)
    with pytest.raises(contract.ContractRejected):
        ledger.consume(2)


def test_concurrent_attempt_check_and_consume_allows_only_one() -> None:
    ledger = controller.AttemptLedger()
    barrier = threading.Barrier(3)
    results: list[str] = []

    def contender() -> None:
        barrier.wait()
        try:
            ledger.consume(1)
            results.append("accepted")
        except contract.ContractRejected:
            results.append("rejected")

    threads = [threading.Thread(target=contender) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=5)
    assert sorted(results) == ["accepted", "rejected"]


def test_science_and_publication_are_nonformal_and_formal_is_unreachable() -> None:
    config = contract.load_config()
    assert config["pilot"]["blocks"] == list(contract.BLOCKS)
    assert config["pilot"]["retry_resume_reorder_skip_allowed"] is False
    assert config["science_authority"]["solver"]["name"] == "highs"
    assert config["science_authority"]["solver"]["threads"] == 4
    assert config["science_authority"]["solver"]["time_limit_seconds"] is None
    assert config["resource_authority"]["watchdog_seconds_per_block"] == 21600.0
    assert config["gates"]["formal_execution_ready"] is False
    assert config["gates"]["claim"] is False
    assert config["gates"]["security_certified"] is False


def test_v3_atomic_publication_truth_table_is_retained_in_tmp(
    tmp_path: Path,
) -> None:
    paths = publisher.publication_paths(tmp_path / "result")
    initial = publisher.capture_presence(paths)
    assert publisher.classify_publication(
        initial, result_exact=False, success_exact=False
    ) == "honest_incomplete"
    staging = tmp_path / ".result.staging"
    staging.mkdir()
    publisher.atomic_write(staging / "summary.json", contract.exact_json_bytes({"nonformal": True}))
    publisher.atomic_write(
        staging / "SHA256SUMS.json",
        contract.exact_json_bytes(publisher.typed_tree(staging)),
    )
    os.replace(staging, paths.result)
    success_staging = tmp_path / ".success.staging"
    success_staging.mkdir()
    publisher.atomic_write(success_staging / "success.json", contract.exact_json_bytes({"published": True}))
    publisher.atomic_write(
        success_staging / "SHA256SUMS.json",
        contract.exact_json_bytes(publisher.typed_tree(success_staging)),
    )
    os.replace(success_staging, paths.success)
    final = publisher.capture_presence(paths)
    assert publisher.classify_publication(
        final, result_exact=True, success_exact=True
    ) == "committed_success"


def test_v3_cross_protocol_evidence_schema_cannot_equal_execution_schema() -> None:
    source = Path(controller.__file__).read_text(encoding="utf-8")
    assert "rq2_public_grid_accepted_evidence_vnext_execution_v2" in source
    assert "rq2_public_grid_accepted_evidence_vnext_v3" not in source
