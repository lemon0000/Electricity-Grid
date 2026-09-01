from __future__ import annotations

import hashlib
import inspect
import json
import os
import subprocess
from copy import deepcopy

import pytest

from experiments import (
    rq2_public_grid_two_block_pilot_vnext_execution_contract_v3 as contract,
)
from experiments import (
    run_rq2_public_grid_two_block_pilot_vnext_execution_successor_v3 as controller,
)


def test_lamport_public_anchor_and_signature_round_trip() -> None:
    seed = bytes.fromhex("11" * 32)
    public_key = contract.derive_lamport_public_key(seed)
    payload = {"schema": "test_payload", "value": 7}
    digest = hashlib.sha256(contract.exact_json_bytes(payload)).hexdigest()
    signature = contract.lamport_sign_digest(seed, digest)
    contract.verify_lamport_signature(digest, signature, public_key)


def test_resource_journal_requires_first_sample_and_recomputes_every_field() -> None:
    journal = contract.synthetic_resource_journal_for_test(
        pid=321,
        create_time_ns=654,
        private_values=(1024, 2048),
        available_values=(12 * 1024**3, 11 * 1024**3),
    )
    assert journal["sample_count"] == 2
    assert journal["first_sample_observed"] is True
    contract.validate_resource_journal(journal)
    tampered = json.loads(json.dumps(journal))
    tampered["samples"][1]["scheduled_monotonic_ns"] += 1
    with pytest.raises(contract.ContractRejected):
        contract.validate_resource_journal(tampered)


def test_v3_future_review_absent_and_canonical_roots_clean() -> None:
    config = contract.load_config()
    assert contract.REVIEW.exists() is False
    for relative in config["paths"].values():
        assert (contract.ROOT / relative).exists() is False


def test_private_seed_is_not_in_public_anchor() -> None:
    raw = contract.read_stable(contract.PUBLIC_KEY)
    value = json.loads(raw)
    assert "seed_hex" not in value
    assert set(value) == contract.PUBLIC_KEY_KEYS


def test_lamport_wrong_digest_public_key_and_signature_fail() -> None:
    seed = bytes.fromhex("22" * 32)
    digest = hashlib.sha256(b"original").hexdigest()
    signature = contract.lamport_sign_digest(seed, digest)
    public = contract.derive_lamport_public_key(seed)
    with pytest.raises(contract.ContractRejected):
        contract.verify_lamport_signature(
            hashlib.sha256(b"tampered").hexdigest(), signature, public
        )
    wrong_public = contract.derive_lamport_public_key(bytes.fromhex("33" * 32))
    with pytest.raises(contract.ContractRejected):
        contract.verify_lamport_signature(digest, signature, wrong_public)
    tampered = deepcopy(signature)
    tampered["selected_preimages"][0] = "00" * 32
    with pytest.raises(contract.ContractRejected):
        contract.verify_lamport_signature(digest, tampered, public)


def test_signed_digest_changes_when_resource_or_success_core_changes() -> None:
    seed = bytes.fromhex("44" * 32)
    public = contract.derive_lamport_public_key(seed)
    journals = {
        block: contract.synthetic_resource_journal_for_test(
            pid=100 + index,
            create_time_ns=200 + index,
            private_values=(1000 + index,),
            available_values=(12 * 1024**3,),
        )
        for index, block in enumerate(contract.BLOCKS)
    }
    payload = {
        "schema": "test_attestation_payload",
        "resource_journals": journals,
        "result_manifest_substantive_core": {"resource_journals": journals},
        "success_readback_substantive_core": {"resource_journals": journals},
    }
    digest = hashlib.sha256(contract.exact_json_bytes(payload)).hexdigest()
    signature = contract.lamport_sign_digest(seed, digest)
    contract.verify_lamport_signature(digest, signature, public)
    tampered = deepcopy(payload)
    tampered["success_readback_substantive_core"]["resource_journals"][
        contract.BLOCKS[0]
    ]["samples"][0]["child_private_commit_bytes"] += 1
    changed = hashlib.sha256(contract.exact_json_bytes(tampered)).hexdigest()
    with pytest.raises(contract.ContractRejected):
        contract.verify_lamport_signature(changed, signature, public)


class _FastProcess:
    pid = 1234

    def __init__(self) -> None:
        self.polls = 0

    def poll(self) -> int | None:
        self.polls += 1
        return None if self.polls == 1 else 0


def test_fast_child_monitor_has_sample_one_before_exit() -> None:
    process = _FastProcess()
    state = contract.ResourceMonitorState()
    monotonic_values = iter(
        (
            1_000_000_000_000,
            1_000_000_000_001,
            1_000_000_000_002,
            1_000_000_000_003,
            1_000_000_000_004,
        )
    )
    wall_values = iter(
        (2_000_000_000_000, 2_000_000_000_001, 2_000_000_000_002)
    )
    outcome = contract.monitor_owned_child_resources_journal(
        process,
        expected_pid=1234,
        expected_create_time_ns=999,
        watchdog_duration_ns=contract.WATCHDOG_NS,
        state=state,
        sample=lambda _pid, _created: (2048, 12 * 1024**3),
        monotonic_ns=lambda: next(monotonic_values),
        wall_time_ns=lambda: next(wall_values),
        sleep=lambda _seconds: pytest.fail("fast child should not sleep"),
        terminate=lambda *_args, **_kwargs: pytest.fail(
            "fast child should not terminate"
        ),
    )
    assert state.ready.is_set()
    assert state.first_sample_success is True
    assert outcome["status"] == "child_exited"
    assert outcome["sample_count"] == 1
    assert outcome["samples"][0]["owned_identity"] == {
        "pid": 1234,
        "create_time_ns": 999,
    }


@pytest.mark.parametrize(
    "mutator",
    [
        lambda value: value["samples"][0].__setitem__(
            "child_private_commit_bytes", -1
        ),
        lambda value: value["samples"][0].__setitem__(
            "system_commit_available_bytes", -1
        ),
        lambda value: value["samples"][0].__setitem__(
            "computed_stop_reason", "forged"
        ),
        lambda value: value["samples"][0].__setitem__("thresholds", {}),
        lambda value: value["samples"][0].__setitem__(
            "owned_identity", {"pid": 999, "create_time_ns": 456}
        ),
        lambda value: value["samples"][0].__setitem__("wall_time_ns", 0),
        lambda value: value["samples"][0].__setitem__("monotonic_ns", 0),
        lambda value: value["samples"][1].__setitem__(
            "scheduled_monotonic_ns",
            value["samples"][1]["scheduled_monotonic_ns"] + 1,
        ),
        lambda value: value.__setitem__("maximum_private_commit_bytes", 0),
        lambda value: value.__setitem__(
            "minimum_system_commit_available_bytes", 0
        ),
        lambda value: value.__setitem__("sample_count", 99),
        lambda value: value.__setitem__("first_sample_monotonic_ns", 1),
        lambda value: value.__setitem__("exit_observed_monotonic_ns", 1),
    ],
)
def test_resource_journal_tamper_fails_closed(mutator) -> None:
    journal = contract.synthetic_resource_journal_for_test(
        pid=123,
        create_time_ns=456,
        private_values=(100, 200),
        available_values=(12 * 1024**3, 11 * 1024**3),
    )
    tampered = deepcopy(journal)
    mutator(tampered)
    with pytest.raises(contract.ContractRejected):
        contract.validate_resource_journal(tampered)


def test_boundary_stop_reasons_are_exact() -> None:
    assert (
        contract.resource_stop_reason(
            contract.PRIVATE_COMMIT_LIMIT_BYTES,
            contract.SYSTEM_COMMIT_RESERVE_BYTES + 1,
        )
        == "private_commit_limit_reached"
    )
    assert (
        contract.resource_stop_reason(
            contract.PRIVATE_COMMIT_LIMIT_BYTES - 1,
            contract.SYSTEM_COMMIT_RESERVE_BYTES,
        )
        == "system_commit_reserve_reached"
    )
    assert (
        contract.resource_stop_reason(
            contract.PRIVATE_COMMIT_LIMIT_BYTES,
            contract.SYSTEM_COMMIT_RESERVE_BYTES,
        )
        == "private_and_system_commit_limits_reached"
    )


def test_actual_worker_time_highs_runtime_evidence() -> None:
    identity = {
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "create_time_ns": contract.process_create_time_ns(os.getpid()),
    }
    evidence = contract.collect_solver_runtime_evidence(identity)
    assert evidence["highspy_metadata_version"] == "1.15.1"
    assert evidence["highs_runtime_api_version"] == "1.15.1"
    assert evidence["threads"] == 4
    assert evidence["solver_solve_called_by_runtime_probe"] is False
    contract.validate_solver_runtime_evidence(evidence, worker_identity=identity)


def test_runtime_evidence_version_and_binary_tamper_fail() -> None:
    identity = {
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "create_time_ns": contract.process_create_time_ns(os.getpid()),
    }
    evidence = contract.collect_solver_runtime_evidence(identity)
    for key in (
        "highspy_metadata_version",
        "highs_runtime_api_version",
        "highspy_binary_sha256",
        "threads",
    ):
        tampered = deepcopy(evidence)
        tampered[key] = "forged"
        with pytest.raises(contract.ContractRejected):
            contract.validate_solver_runtime_evidence(
                tampered, worker_identity=identity
            )


def test_ordinary_import_surface_has_no_production_seed_or_lease_authority() -> None:
    forbidden = {
        "consume_private_lease",
        "finalize_consumed_lease_tombstone",
        "_validate_private_lease_value",
        "private_seed",
        "production_seed",
        "sign_with_production_key",
    }
    assert forbidden.isdisjoint(set(vars(contract)))
    assert forbidden.isdisjoint(set(vars(controller)))
    assert not any(
        isinstance(value, (bytes, bytearray)) and len(value) == 32
        for value in vars(contract).values()
    )
    source = inspect.getsource(controller)
    assert "def validate_and_consume_private_lease" in source
    assert "def tombstone_key" in source
    assert "return publish(key_seed)" in source


def test_execution_api_is_review_gated_before_private_lease_touch() -> None:
    config = contract.load_config()
    fresh = contract.ROOT / config["controller_authentication"][
        "private_lease_path"
    ]
    before = contract.read_stable(fresh)
    with pytest.raises(contract.ContractRejected, match="PASS receipt is absent"):
        controller.run_two_block_nonformal()
    assert contract.read_stable(fresh) == before


def test_one_time_key_reuse_guard_and_seed_free_tombstone_are_in_controller() -> None:
    source = inspect.getsource(controller.run_two_block_nonformal)
    assert "if consumed_lease.exists() or consumed_lease.is_symlink()" in source
    assert '"seed_present": False' in source
    assert '"one_time_key_reusable": False' in source
    assert "os.replace(fresh_lease, consumed_lease)" in source
    assert "os.replace(temporary, consumed_lease)" in source
    assert "key_seed[index] = 0" in source


def test_post_rename_path_requires_independent_public_readback() -> None:
    source = inspect.getsource(controller.run_two_block_nonformal)
    result_rename = source.index("os.replace(staging, result)")
    success_rename = source.index("os.replace(success_staging, success)")
    independent_readback = source.index("contract.verify_published_artifacts(")
    assert result_rename < success_rename < independent_readback
    assert '!= "committed_success"' in source[independent_readback:]


def test_v2_cross_protocol_publication_rejected_by_v3_readback() -> None:
    v2_result = (
        contract.ROOT
        / "results/tables/rq2_public_grid_two_block_pilot_vnext_execution_successor_v2"
    )
    v2_success = v2_result.with_name(f"{v2_result.name}.PUBLISHED")
    with pytest.raises(contract.ContractRejected):
        contract.verify_published_artifacts(v2_result, v2_success)


def test_post_result_receipt_and_all_v2_bytes_are_exact() -> None:
    mapping = contract.verify_post_result_rework_and_v2_artifacts()
    assert len(mapping) == 26
    receipt = json.loads(contract.read_stable(contract.POST_RESULT_REWORK))
    assert receipt["verdict"] == "REWORK"
    assert receipt["effect"]["v2_post_result_review_passed"] is False
    assert receipt["effect"]["formal_execution_authorized"] is False
    assert (
        receipt["remediation_boundary"][
            "same_os_user_pre_execution_lease_exfiltration_out_of_scope"
        ]
        is True
    )


def test_bundle_live_closure_and_new_roots() -> None:
    config = contract.load_config()
    self_mapping = contract.verify_self_bundle()
    live = contract.verify_live_authorities()
    assert len(self_mapping) == 11
    assert len(live) == 142
    assert contract.PUBLIC_KEY.relative_to(contract.ROOT).as_posix() in self_mapping
    for relative in config["paths"].values():
        assert not (contract.ROOT / relative).exists()


def test_real_fast_child_first_sample_gate_and_zero_solver() -> None:
    outcome = controller.run_review_resource_probe_e2e()
    assert outcome["worker_exited"] is True
    assert outcome["resource_journal"]["sample_count"] >= 1
    assert outcome["release_sent_monotonic_ns"] >= outcome["resource_journal"][
        "first_sample_monotonic_ns"
    ]
    assert outcome["scientific_loader_calls"] == 0
    assert outcome["solver_calls"] == 0
    assert outcome["result_writes"] == 0


def test_real_preloader_zero_solver() -> None:
    outcome = controller.run_review_preloader_e2e()
    assert outcome["worker_exited"] is True
    assert outcome["scientific_loader_calls"] == 0
    assert outcome["solver_calls"] == 0
    assert outcome["result_writes"] == 0


def test_canonical_validate_only_and_execute_fail_before_project_import() -> None:
    config = contract.load_config()
    env = config["runtime"]["sanitized_environment"]
    python = config["runtime"]["locked_python_executable"]
    bootstrap = config["runtime"]["bootstrap_path"]
    valid = subprocess.run(
        [python, "-B", bootstrap, "--validate-only"],
        cwd=contract.ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert valid.returncode == 0, valid.stderr
    value = json.loads(valid.stdout)
    assert value["validation_passed"] is True
    assert value["worker_processes_started"] == 0
    assert value["scientific_loader_calls"] == 0
    assert value["solver_calls"] == 0
    assert value["result_writes"] == 0
    assert value["execution_ready"] is False
    execute = subprocess.run(
        [python, "-B", bootstrap, "--execute"],
        cwd=contract.ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert execute.returncode != 0
    assert "fixed V3 execution-review PASS receipt is absent" in execute.stderr


def test_formal_assets_and_nine_checkpoints_unchanged() -> None:
    config = contract.load_config()["formal_protection"]
    assert (
        hashlib.sha256(
            contract.read_stable(contract.ROOT / config["formal_runner_path"])
        ).hexdigest()
        == config["formal_runner_sha256"]
    )
    assert (
        hashlib.sha256(
            contract.read_stable(contract.ROOT / config["activated_config_path"])
        ).hexdigest()
        == config["activated_config_sha256"]
    )
    checkpoints = list(
        (
            contract.ROOT
            / "results/checkpoints/rts_gmlc_public_grid_need_dispatch_v4_gurobi"
        ).glob("*.json")
    )
    assert len(checkpoints) == config["checkpoint_count"] == 9


def test_no_production_seed_appears_in_candidate_members() -> None:
    config = contract.load_config()
    lease = contract.ROOT / config["controller_authentication"][
        "private_lease_path"
    ]
    seed_hex = json.loads(contract.read_stable(lease))["seed_hex"]
    leaked_member_count = 0
    for relative in config["bundle"]["members"]:
        raw = contract.read_stable(contract.ROOT / relative).decode("utf-8")
        if seed_hex in raw:
            leaked_member_count += 1
    assert leaked_member_count == 0


def test_review_receipt_absent_and_threat_boundary_explicit() -> None:
    config = contract.load_config()
    assert not contract.REVIEW.exists()
    assert (
        config["controller_authentication"][
            "same_os_user_pre_execution_lease_exfiltration_out_of_scope"
        ]
        is True
    )
    assert config["controller_authentication"]["security_certified"] is False
