from __future__ import annotations

import hashlib
import inspect
import json
import os
import subprocess
from copy import deepcopy

import pytest

from experiments import (
    rq2_public_grid_two_block_pilot_vnext_execution_contract_v4 as contract,
)
from experiments import (
    run_rq2_public_grid_two_block_pilot_vnext_execution_successor_v4 as controller,
)


def test_arbitrary_100s_actual_observation_gap_is_rejected() -> None:
    journal = contract.synthetic_resource_journal_for_test(
        pid=101,
        create_time_ns=202,
        private_values=(100, 200),
        available_values=(12 * 1024**3, 11 * 1024**3),
    )
    journal["samples"][1]["monotonic_ns"] = (
        journal["samples"][0]["monotonic_ns"] + 100_000_000_000
    )
    journal["samples"][1]["actual_observation_lateness_ns"] = (
        journal["samples"][1]["monotonic_ns"]
        - journal["samples"][1]["scheduled_monotonic_ns"]
    )
    journal["exit_observed_monotonic_ns"] = (
        journal["samples"][1]["monotonic_ns"] + 1
    )
    with pytest.raises(contract.ContractRejected):
        contract.validate_resource_journal(journal)


def test_two_second_catch_up_samples_are_rejected() -> None:
    journal = contract.synthetic_resource_journal_for_test(
        pid=101,
        create_time_ns=202,
        private_values=(100, 200),
        available_values=(12 * 1024**3, 11 * 1024**3),
    )
    journal["samples"][1]["monotonic_ns"] = (
        journal["samples"][0]["monotonic_ns"] + 2_000_000_000
    )
    journal["samples"][1]["actual_observation_lateness_ns"] = (
        journal["samples"][1]["monotonic_ns"]
        - journal["samples"][1]["scheduled_monotonic_ns"]
    )
    with pytest.raises(contract.ContractRejected):
        contract.validate_resource_journal(journal)


def test_missing_scheduled_slot_is_rejected() -> None:
    journal = contract.synthetic_resource_journal_for_test(
        pid=101,
        create_time_ns=202,
        private_values=(100, 200),
        available_values=(12 * 1024**3, 11 * 1024**3),
    )
    journal["samples"][1]["scheduled_monotonic_ns"] += contract.SAMPLE_INTERVAL_NS
    journal["samples"][1]["sample_deadline_monotonic_ns"] += (
        contract.SAMPLE_INTERVAL_NS
    )
    with pytest.raises(contract.ContractRejected):
        contract.validate_resource_journal(journal)


@pytest.mark.parametrize(
    "offsets",
    [
        (contract.OBSERVATION_JITTER_BUDGET_NS, 0),
        (0, contract.OBSERVATION_JITTER_BUDGET_NS),
    ],
)
def test_actual_lateness_and_gap_boundaries_are_accepted(
    offsets: tuple[int, int],
) -> None:
    journal = contract.synthetic_resource_journal_for_test(
        pid=101,
        create_time_ns=202,
        private_values=(100, 200),
        available_values=(12 * 1024**3, 11 * 1024**3),
        actual_offsets_ns=offsets,
    )
    contract.validate_resource_journal(journal)


def test_actual_lateness_one_ns_above_budget_is_rejected() -> None:
    journal = contract.synthetic_resource_journal_for_test(
        pid=101,
        create_time_ns=202,
        private_values=(100,),
        available_values=(12 * 1024**3,),
    )
    sample = journal["samples"][0]
    sample["monotonic_ns"] = (
        sample["scheduled_monotonic_ns"]
        + contract.OBSERVATION_JITTER_BUDGET_NS
        + 1
    )
    sample["actual_observation_lateness_ns"] = (
        contract.OBSERVATION_JITTER_BUDGET_NS + 1
    )
    with pytest.raises(contract.ContractRejected):
        contract.validate_resource_journal(journal)


def test_exit_expected_slot_count_and_last_sample_gap_are_strict() -> None:
    journal = contract.synthetic_resource_journal_for_test(
        pid=101,
        create_time_ns=202,
        private_values=(100,),
        available_values=(12 * 1024**3,),
    )
    accepted = deepcopy(journal)
    accepted["exit_observed_monotonic_ns"] = (
        accepted["samples"][-1]["monotonic_ns"]
        + contract.SAMPLE_INTERVAL_NS
        - 1
    )
    accepted["expected_sample_count_at_exit"] = 1
    accepted["last_sample_to_exit_ns"] = (
        accepted["exit_observed_monotonic_ns"]
        - accepted["samples"][-1]["monotonic_ns"]
    )
    contract.validate_resource_journal(accepted)
    missed = deepcopy(accepted)
    missed["exit_observed_monotonic_ns"] = (
        missed["monitor_start_monotonic_ns"] + contract.SAMPLE_INTERVAL_NS
    )
    missed["expected_sample_count_at_exit"] = 2
    missed["last_sample_to_exit_ns"] = (
        missed["exit_observed_monotonic_ns"]
        - missed["samples"][-1]["monotonic_ns"]
    )
    with pytest.raises(contract.ContractRejected):
        contract.validate_resource_journal(missed)


def test_deadline_missed_journal_is_honest_incomplete() -> None:
    journal = contract.synthetic_deadline_missed_journal_for_test(
        pid=101, create_time_ns=202
    )
    assert journal["status"] == "resource_sample_deadline_missed"
    assert journal["honest_incomplete"] is True
    assert journal["mathematical_infeasibility_inferred"] is False
    contract.validate_resource_journal(journal)


@pytest.mark.parametrize(
    "failure_point",
    [
        "after_rename",
        "consumed_readback",
        "consumed_json",
        "consumed_schema",
        "consumed_derive",
        "consumed_public_mismatch",
        "unexpected_after_rename",
    ],
)
def test_acquire_failure_after_rename_always_leaves_seed_free_tombstone(
    failure_point: str,
) -> None:
    outcome = controller.run_review_lease_acquire_probe(failure_point)
    assert outcome["failure_injected"] is True
    assert outcome["fresh_raw_seed_present"] is False
    assert outcome["consumed_raw_seed_present"] is False
    assert outcome["tombstone_present"] is True
    assert outcome["tombstone_seed_present"] is False
    assert outcome["returned_seed"] is False


def test_normal_review_sign_also_destroys_test_seed() -> None:
    outcome = controller.run_review_lease_acquire_probe(None)
    assert outcome["signature_verified"] is True
    assert outcome["fresh_raw_seed_present"] is False
    assert outcome["consumed_raw_seed_present"] is False
    assert outcome["tombstone_present"] is True
    assert outcome["tombstone_seed_present"] is False
    assert outcome["returned_seed"] is False


def test_ordinary_import_surface_has_no_production_lease_authority() -> None:
    forbidden = {
        "acquire_private_lease",
        "consume_private_lease",
        "production_seed",
        "private_seed",
        "sign_with_production_key",
    }
    assert forbidden.isdisjoint(vars(contract))
    assert forbidden.isdisjoint(vars(controller))
    source = inspect.getsource(controller.run_two_block_nonformal)
    assert "def acquire_private_lease" in source
    assert "finally:" in source
    assert "tombstone_key" in source


def test_frozen_scheduler_values_are_audit_only() -> None:
    config = contract.load_config()
    resource = config["resource_contract"]
    assert resource["sample_interval_ns"] == contract.SAMPLE_INTERVAL_NS == 5_000_000_000
    assert resource["observation_jitter_budget_ns"] == 1_000_000_000
    assert (
        resource["jitter_budget_role"]
        == "pre_run_os_scheduling_audit_threshold_not_science_parameter"
    )
    assert resource["actual_observation_gap_min_ns"] == 4_000_000_000
    assert resource["actual_observation_gap_max_ns"] == 6_000_000_000
    assert resource["catch_up_sampling_allowed"] is False
    assert resource["child_private_commit_stop_bytes"] == 8 * 1024**3
    assert resource["system_commit_available_stop_bytes"] == 2 * 1024**3
    assert config["gates"]["formal_execution_ready"] is False
    assert config["gates"]["security_certified"] is False


def test_lamport_public_anchor_and_synthetic_signature_round_trip() -> None:
    seed = bytes.fromhex("11" * 32)
    public_key = contract.derive_lamport_public_key(seed)
    digest = hashlib.sha256(b"v4 synthetic payload").hexdigest()
    signature = contract.lamport_sign_digest(seed, digest)
    contract.verify_lamport_signature(digest, signature, public_key)
    with pytest.raises(contract.ContractRejected):
        contract.verify_lamport_signature(
            hashlib.sha256(b"tampered payload").hexdigest(), signature, public_key
        )
    with pytest.raises(contract.ContractRejected):
        contract.verify_lamport_signature(
            digest,
            signature,
            contract.derive_lamport_public_key(bytes.fromhex("22" * 32)),
        )
    altered = deepcopy(signature)
    altered["selected_preimages"][0] = "00" * 32
    with pytest.raises(contract.ContractRejected):
        contract.verify_lamport_signature(digest, altered, public_key)


def test_v4_public_anchor_has_no_private_material() -> None:
    value = json.loads(contract.read_stable(contract.PUBLIC_KEY))
    assert set(value) == contract.PUBLIC_KEY_KEYS
    assert "seed_hex" not in value
    assert value["key_id"] == (
        "d488f9ef76e86ac1cc7d385252937df76190adcb0fe10332ecf3504bed07b7ac"
    )
    assert value["public_key_sha256"] == (
        "ab4930c4bbb229686c19dd59e17a9a0866ca3f96b559f7710d3f32dade50c0d0"
    )
    assert value["security_certified"] is False


def test_resource_sequence_and_success_readback_change_signed_digest() -> None:
    identity = {
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "create_time_ns": contract.process_create_time_ns(os.getpid()),
    }
    runtime = contract.collect_solver_runtime_evidence(identity)
    journals = {
        block: contract.synthetic_resource_journal_for_test(
            pid=100 + index,
            create_time_ns=200 + index,
            private_values=(1000 + index,),
            available_values=(12 * 1024**3,),
        )
        for index, block in enumerate(contract.BLOCKS)
    }
    result_core = {"resource_journals": journals}
    success_core = {"resource_journals": journals}
    payload = contract.build_attestation_payload(
        session_id="test-session",
        entries={"summary.json": contract.exact_json_bytes(success_core)},
        resource_journals=journals,
        runtime_evidence={block: runtime for block in contract.BLOCKS},
        result_manifest_core=result_core,
        success_core=success_core,
        closure_mapping={},
    )
    assert payload["resource_journals"] == journals
    assert payload["result_manifest_substantive_core"] == result_core
    assert payload["success_readback_substantive_core"] == success_core
    seed = bytes.fromhex("44" * 32)
    public = contract.derive_lamport_public_key(seed)
    digest = contract.sha256_bytes(contract.exact_json_bytes(payload))
    signature = contract.lamport_sign_digest(seed, digest)
    contract.verify_lamport_signature(digest, signature, public)
    tampered = deepcopy(payload)
    tampered["success_readback_substantive_core"]["resource_journals"][
        contract.BLOCKS[0]
    ]["samples"][0]["child_private_commit_bytes"] += 1
    changed = contract.sha256_bytes(contract.exact_json_bytes(tampered))
    with pytest.raises(contract.ContractRejected):
        contract.verify_lamport_signature(changed, signature, public)


class _FastProcess:
    pid = 1234

    def __init__(self) -> None:
        self.polls = 0

    def poll(self) -> int | None:
        self.polls += 1
        return None if self.polls == 1 else 0


def test_fast_child_monitor_has_one_sample_before_exit() -> None:
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
    assert outcome["expected_sample_count_at_exit"] == 1


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
        lambda value: value.__setitem__("maximum_private_commit_bytes", 0),
        lambda value: value.__setitem__("minimum_system_commit_available_bytes", 0),
        lambda value: value.__setitem__("sample_count", 99),
        lambda value: value.__setitem__("first_sample_monotonic_ns", 1),
        lambda value: value.__setitem__("exit_observed_monotonic_ns", 1),
        lambda value: value.__setitem__("observation_jitter_budget_ns", 2),
        lambda value: value.__setitem__("catch_up_sampling_allowed", True),
    ],
)
def test_full_resource_journal_tamper_fails_closed(mutator) -> None:
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


def test_execution_is_review_gated_before_v4_lease_touch() -> None:
    config = contract.load_config()
    fresh = contract.ROOT / config["controller_authentication"]["private_lease_path"]
    before = (fresh.stat().st_size, fresh.stat().st_mtime_ns)
    with pytest.raises(contract.ContractRejected, match="PASS receipt is absent"):
        controller.run_two_block_nonformal()
    assert (fresh.stat().st_size, fresh.stat().st_mtime_ns) == before
    assert not (
        contract.ROOT
        / config["controller_authentication"]["consumed_private_lease_path"]
    ).exists()


def test_v3_escalation_and_seed_free_revocation_are_exact() -> None:
    contract.verify_v3_escalation_and_revocation()
    config = contract.load_config()["predecessor_v3"]
    assert contract._sha_file(contract.ROOT / config["outer_path"]) == config[
        "outer_sha256"
    ]
    assert contract._sha_file(contract.ROOT / config["inner_path"]) == config[
        "inner_sha256"
    ]
    tombstone = json.loads(
        contract.read_stable(contract.ROOT / config["revoked_tombstone_path"])
    )
    assert tombstone["state"] == "revoked"
    assert tombstone["seed_present"] is False
    assert "seed_hex" not in tombstone
    assert not (
        contract.ROOT
        / config["revoked_tombstone_path"].replace(".consumed", ".lease")
    ).exists()


def test_bundle_live_closure_new_roots_and_review_absence() -> None:
    config = contract.load_config()
    self_mapping = contract.verify_self_bundle()
    live = contract.verify_live_authorities()
    assert len(self_mapping) == config["bundle"]["self_mapping_exact_count"] == 13
    assert len(live) == config["bundle"]["live_authority_exact_count"] == 155
    assert contract.PUBLIC_KEY.relative_to(contract.ROOT).as_posix() in self_mapping
    assert contract.REVIEW.exists() is False
    for relative in config["paths"].values():
        assert not (contract.ROOT / relative).exists()


def test_real_fast_child_gate_and_preloader_make_zero_solver_calls() -> None:
    resource = controller.run_review_resource_probe_e2e()
    assert resource["worker_exited"] is True
    assert resource["resource_journal"]["sample_count"] >= 1
    assert resource["release_sent_monotonic_ns"] >= resource["resource_journal"][
        "first_sample_monotonic_ns"
    ]
    assert resource["scientific_loader_calls"] == 0
    assert resource["solver_calls"] == 0
    assert resource["result_writes"] == 0
    preloader = controller.run_review_preloader_e2e()
    assert preloader["worker_exited"] is True
    assert preloader["scientific_loader_calls"] == 0
    assert preloader["solver_calls"] == 0
    assert preloader["result_writes"] == 0


def test_canonical_validate_only_and_execute_fail_before_project_import() -> None:
    config = contract.load_config()
    valid = subprocess.run(
        [
            config["runtime"]["locked_python_executable"],
            "-B",
            config["runtime"]["bootstrap_path"],
            "--validate-only",
        ],
        cwd=contract.ROOT,
        env=config["runtime"]["sanitized_environment"],
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
        [
            config["runtime"]["locked_python_executable"],
            "-B",
            config["runtime"]["bootstrap_path"],
            "--execute",
        ],
        cwd=contract.ROOT,
        env=config["runtime"]["sanitized_environment"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert execute.returncode != 0
    assert "fixed V4 execution-review PASS receipt is absent" in execute.stderr


def test_formal_assets_and_nine_checkpoints_unchanged() -> None:
    config = contract.load_config()["formal_protection"]
    assert contract._sha_file(contract.ROOT / config["formal_runner_path"]) == config[
        "formal_runner_sha256"
    ]
    assert contract._sha_file(
        contract.ROOT / config["activated_config_path"]
    ) == config["activated_config_sha256"]
    checkpoints = list(
        (
            contract.ROOT
            / "results/checkpoints/rts_gmlc_public_grid_need_dispatch_v4_gurobi"
        ).glob("*.json")
    )
    assert len(checkpoints) == config["checkpoint_count"] == 9


def test_post_rename_requires_independent_v4_readback_and_v3_protocol_rejected() -> None:
    source = inspect.getsource(controller.run_two_block_nonformal)
    result_rename = source.index("os.replace(staging, result)")
    success_rename = source.index("os.replace(success_staging, success)")
    independent_readback = source.index("contract.verify_published_artifacts(")
    assert result_rename < success_rename < independent_readback
    v3_config = json.loads(
        contract.read_stable(
            contract.ROOT
            / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_v3.json"
        )
    )
    v3_result = contract.ROOT / v3_config["paths"]["result_root"]
    v3_success = contract.ROOT / v3_config["paths"]["success_root"]
    if v3_result.exists() or v3_success.exists():
        with pytest.raises(contract.ContractRejected):
            contract.verify_published_artifacts(v3_result, v3_success)
