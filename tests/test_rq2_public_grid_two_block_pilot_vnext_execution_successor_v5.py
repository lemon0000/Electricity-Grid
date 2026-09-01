from __future__ import annotations

import hashlib
import inspect
import json
import os
import subprocess
from copy import deepcopy

import pytest

from experiments import (
    rq2_public_grid_two_block_pilot_vnext_execution_contract_v5 as contract,
)
from experiments import (
    run_rq2_public_grid_two_block_pilot_vnext_execution_successor_v5 as controller,
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
    journal["samples"][1]["scheduled_monotonic_ns"] += (
        contract.SAMPLE_INTERVAL_NS
    )
    journal["samples"][1]["sample_deadline_monotonic_ns"] += (
        contract.SAMPLE_INTERVAL_NS
    )
    with pytest.raises(contract.ContractRejected):
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


def test_deadline_missed_journal_tamper_is_rejected() -> None:
    journal = contract.synthetic_deadline_missed_journal_for_test(
        pid=101, create_time_ns=202
    )
    tampered = deepcopy(journal)
    tampered["termination"]["missed_slot"]["sequence_index"] += 1
    with pytest.raises(contract.ContractRejected):
        contract.validate_resource_journal(tampered)


class _Clock:
    def __init__(self) -> None:
        self.now_ns = 1_000_000_000_000

    def monotonic_ns(self) -> int:
        return self.now_ns

    def wall_time_ns(self) -> int:
        return self.now_ns + 1_000_000_000_000

    def advance(self, nanoseconds: int) -> None:
        self.now_ns += nanoseconds

    def sleep(self, seconds: float) -> None:
        self.advance(round(seconds * 1_000_000_000))


class _OwnedProcess:
    pid = 1234

    def __init__(self) -> None:
        self.exited = False

    def poll(self) -> int | None:
        return 0 if self.exited else None


def test_delayed_deadline_termination_returns_persistable_honest_journal() -> None:
    clock = _Clock()
    process = _OwnedProcess()
    state = contract.ResourceMonitorState()
    calls = 0

    def sample(pid: int, create_time_ns: int) -> tuple[int, int]:
        nonlocal calls
        assert (pid, create_time_ns) == (1234, 5678)
        calls += 1
        if calls == 2:
            clock.advance(contract.OBSERVATION_JITTER_BUDGET_NS + 1)
        return 1024, 12 * 1024**3

    def terminate(
        target: _OwnedProcess, *, expected_pid: int, expected_create_time_ns: int
    ) -> dict[str, object]:
        assert target is process
        assert (expected_pid, expected_create_time_ns) == (1234, 5678)
        clock.advance(1_000_000_000)
        process.exited = True
        return {
            "termination_action": "terminate_only",
            "termination_completed": True,
        }

    try:
        outcome = contract.monitor_owned_child_resources_journal(
            process,
            expected_pid=1234,
            expected_create_time_ns=5678,
            watchdog_duration_ns=contract.WATCHDOG_NS,
            state=state,
            sample=sample,
            monotonic_ns=clock.monotonic_ns,
            wall_time_ns=clock.wall_time_ns,
            sleep=clock.sleep,
            terminate=terminate,
        )
    except contract.ContractRejected:
        pytest.fail(f"deadline journal was lost: state.outcome={state.outcome!r}")
    assert outcome["status"] == "resource_sample_deadline_missed"
    assert outcome["honest_incomplete"] is True
    assert outcome["mathematical_infeasibility_inferred"] is False
    assert outcome["sample_count"] == 1
    assert outcome["expected_sample_count_at_exit"] == 2
    assert outcome["last_sample_to_exit_ns"] == 7_000_000_001
    assert outcome["termination"]["termination_duration_ns"] == 1_000_000_000
    assert outcome["termination"]["termination_action"] == "terminate_only"
    assert outcome["termination"]["missed_slot"] == {
        "sequence_index": 1,
        "scheduled_monotonic_ns": 1_005_000_000_000,
        "sample_deadline_monotonic_ns": 1_006_000_000_000,
    }
    assert state.outcome == outcome


@pytest.mark.parametrize(
    ("termination_duration_ns", "expected_status", "expected_reason"),
    [
        (0, "resource_sample_deadline_missed", "resource_sample_deadline_missed"),
        (
            1_000_000_000,
            "resource_sample_deadline_missed",
            "resource_sample_deadline_missed",
        ),
        (
            2_000_000_000,
            "resource_sample_deadline_missed",
            "resource_sample_deadline_missed",
        ),
        (
            2_000_000_001,
            "termination_indeterminate",
            "owned_termination_grace_exceeded",
        ),
    ],
)
def test_deadline_termination_grace_boundaries_are_explicit(
    termination_duration_ns: int,
    expected_status: str,
    expected_reason: str,
) -> None:
    clock = _Clock()
    process = _OwnedProcess()
    state = contract.ResourceMonitorState()
    calls = 0

    def sample(pid: int, create_time_ns: int) -> tuple[int, int]:
        nonlocal calls
        assert (pid, create_time_ns) == (1234, 5678)
        calls += 1
        clock.advance(contract.OBSERVATION_JITTER_BUDGET_NS)
        if calls == 2:
            clock.advance(1)
        return 1024, 12 * 1024**3

    def terminate(
        target: _OwnedProcess, *, expected_pid: int, expected_create_time_ns: int
    ) -> dict[str, object]:
        assert target is process
        assert (expected_pid, expected_create_time_ns) == (1234, 5678)
        clock.advance(termination_duration_ns)
        process.exited = True
        return {
            "termination_action": "terminate_only",
            "termination_completed": True,
        }

    outcome = contract.monitor_owned_child_resources_journal(
        process,
        expected_pid=1234,
        expected_create_time_ns=5678,
        watchdog_duration_ns=contract.WATCHDOG_NS,
        state=state,
        sample=sample,
        monotonic_ns=clock.monotonic_ns,
        wall_time_ns=clock.wall_time_ns,
        sleep=clock.sleep,
        terminate=terminate,
    )
    assert outcome["status"] == expected_status
    assert outcome["reason"] == expected_reason
    assert outcome["honest_incomplete"] is True
    assert outcome["mathematical_infeasibility_inferred"] is False
    assert outcome["termination"]["termination_duration_ns"] == (
        termination_duration_ns
    )
    assert outcome["termination"]["termination_within_grace"] is (
        termination_duration_ns <= contract.OWNED_TERMINATION_GRACE_NS
    )
    assert state.outcome == outcome


def test_normal_child_exit_beyond_six_seconds_is_rejected() -> None:
    journal = contract.synthetic_resource_journal_for_test(
        pid=1234,
        create_time_ns=5678,
        private_values=(1024,),
        available_values=(12 * 1024**3,),
    )
    journal["exit_observed_monotonic_ns"] += (
        contract.NORMAL_LAST_SAMPLE_TO_EXIT_MAX_NS + 1
    )
    journal["exit_observed_wall_time_ns"] += (
        contract.NORMAL_LAST_SAMPLE_TO_EXIT_MAX_NS + 1
    )
    journal["expected_sample_count_at_exit"] = 2
    journal["last_sample_to_exit_ns"] = (
        contract.NORMAL_LAST_SAMPLE_TO_EXIT_MAX_NS + 2
    )
    with pytest.raises(contract.ContractRejected):
        contract.validate_resource_journal(journal)


@pytest.mark.parametrize("failure_mode", ["raised", "malformed"])
def test_termination_failure_still_returns_indeterminate_journal(
    failure_mode: str,
) -> None:
    clock = _Clock()
    process = _OwnedProcess()
    state = contract.ResourceMonitorState()
    calls = 0

    def sample(pid: int, create_time_ns: int) -> tuple[int, int]:
        nonlocal calls
        calls += 1
        if calls == 2:
            clock.advance(contract.OBSERVATION_JITTER_BUDGET_NS + 1)
        return 1024, 12 * 1024**3

    def terminate(
        target: _OwnedProcess, *, expected_pid: int, expected_create_time_ns: int
    ) -> dict[str, object]:
        if failure_mode == "raised":
            raise RuntimeError("synthetic exact-identity failure")
        return {"unexpected": True}

    outcome = contract.monitor_owned_child_resources_journal(
        process,
        expected_pid=1234,
        expected_create_time_ns=5678,
        watchdog_duration_ns=contract.WATCHDOG_NS,
        state=state,
        sample=sample,
        monotonic_ns=clock.monotonic_ns,
        wall_time_ns=clock.wall_time_ns,
        sleep=clock.sleep,
        terminate=terminate,
    )
    assert outcome["status"] == "termination_indeterminate"
    assert outcome["reason"] == "owned_identity_or_termination_failed"
    assert outcome["termination"]["termination_completed"] is False
    assert outcome["termination"]["termination_action"] == {
        "raised": "termination_failed",
        "malformed": "termination_result_malformed",
    }[failure_mode]
    assert state.outcome == outcome


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
def test_acquire_failure_after_rename_leaves_seed_free_tombstone(
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


def test_ordinary_import_surface_has_no_production_signing_authority() -> None:
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
    assert '"one_time_key_reusable": False' in source


def test_frozen_scheduler_and_termination_values_are_audit_only() -> None:
    config = contract.load_config()
    resource = config["resource_contract"]
    assert resource["sample_interval_ns"] == 5_000_000_000
    assert resource["observation_jitter_budget_ns"] == 1_000_000_000
    assert resource["normal_last_sample_to_exit_max_ns"] == 6_000_000_000
    assert resource["owned_termination_grace_ns"] == 2_000_000_000
    assert resource["termination_last_sample_to_exit_max_ns"] == 8_000_000_000
    assert resource["terminate_wait_ns"] == resource["kill_wait_ns"] == 1_000_000_000
    assert (
        resource["termination_grace_role"]
        == "pre_run_owned_termination_audit_cap_not_science_parameter"
    )
    assert resource["catch_up_sampling_allowed"] is False
    assert resource["child_private_commit_stop_bytes"] == 8 * 1024**3
    assert resource["system_commit_available_stop_bytes"] == 2 * 1024**3
    assert config["gates"]["formal_execution_ready"] is False
    assert config["gates"]["security_certified"] is False


def test_lamport_signature_valid_wrong_key_signature_and_payload() -> None:
    seed = bytes.fromhex("11" * 32)
    public_key = contract.derive_lamport_public_key(seed)
    digest = hashlib.sha256(b"v5 synthetic payload").hexdigest()
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


def test_v5_public_anchor_has_no_private_material() -> None:
    value = json.loads(contract.read_stable(contract.PUBLIC_KEY))
    assert set(value) == contract.PUBLIC_KEY_KEYS
    assert "seed_hex" not in value
    assert value["key_id"] == (
        "96c07d7bbde974606a3b097e7de499b5a8a5aeee9df2dd88ac121afa39ed613b"
    )
    assert value["public_key_sha256"] == (
        "8344976a4758b431c091a0170f194803085fbf247e40fb352021ca3650d6a9d5"
    )
    assert value["security_certified"] is False


def test_termination_journal_and_success_readback_change_signed_digest() -> None:
    identity = {
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "create_time_ns": contract.process_create_time_ns(os.getpid()),
    }
    runtime = contract.collect_solver_runtime_evidence(identity)
    normal = contract.synthetic_resource_journal_for_test(
        pid=101,
        create_time_ns=201,
        private_values=(1001,),
        available_values=(12 * 1024**3,),
    )
    deadline = contract.synthetic_deadline_missed_journal_for_test(
        pid=102, create_time_ns=202
    )
    journals = {contract.BLOCKS[0]: normal, contract.BLOCKS[1]: deadline}
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
    assert payload["success_readback_substantive_core"] == success_core
    seed = bytes.fromhex("44" * 32)
    public = contract.derive_lamport_public_key(seed)
    digest = contract.sha256_bytes(contract.exact_json_bytes(payload))
    signature = contract.lamport_sign_digest(seed, digest)
    contract.verify_lamport_signature(digest, signature, public)
    tampered = deepcopy(payload)
    tampered["success_readback_substantive_core"]["resource_journals"][
        contract.BLOCKS[1]
    ]["termination"]["termination_duration_ns"] += 1
    changed = contract.sha256_bytes(contract.exact_json_bytes(tampered))
    with pytest.raises(contract.ContractRejected):
        contract.verify_lamport_signature(changed, signature, public)


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


@pytest.mark.parametrize(
    "field",
    [
        "termination_request_monotonic_ns",
        "termination_end_monotonic_ns",
        "termination_duration_ns",
        "termination_action",
        "termination_completed",
        "termination_within_grace",
        "exact_owned_identity",
        "expected_due_sample_count",
        "actual_sample_count",
        "unobserved_due_slot_count",
        "owned_termination_grace_ns",
        "termination_duration_cap_ns",
        "sealed_owned_termination_source",
    ],
)
def test_full_termination_evidence_tamper_fails_closed(field: str) -> None:
    journal = contract.synthetic_deadline_missed_journal_for_test(
        pid=123, create_time_ns=456
    )
    tampered = deepcopy(journal)
    value = tampered["termination"][field]
    if isinstance(value, bool):
        tampered["termination"][field] = not value
    elif isinstance(value, int):
        tampered["termination"][field] = value + 1
    elif isinstance(value, str):
        tampered["termination"][field] = "forged"
    else:
        tampered["termination"][field] = {}
    with pytest.raises(contract.ContractRejected):
        contract.validate_resource_journal(tampered)


def test_resource_boundary_stop_reasons_are_exact() -> None:
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


def test_execution_is_review_gated_before_v5_lease_touch() -> None:
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


def test_v4_rework_and_seed_free_revocation_are_exact() -> None:
    contract.verify_v4_rework_and_revocation()
    config = contract.load_config()["predecessor_v4"]
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


def test_deadline_journal_is_persisted_before_incomplete_gate() -> None:
    source = inspect.getsource(controller.run_two_block_nonformal)
    persisted = source.index('"controller_resource_journal.json"')
    status_gate = source.index('resource_journal["status"] != "child_exited"')
    assert persisted < status_gate
    assert "persistence/readback drifted" in source


def test_key_reuse_is_rejected_and_tombstone_has_no_seed() -> None:
    source = inspect.getsource(controller.run_two_block_nonformal)
    assert "one-time V5 key was already consumed" in source
    assert '"one_time_key_reusable": False' in source
    assert '"seed_present": False' in source


def test_bundle_live_closure_new_roots_and_review_absence() -> None:
    config = contract.load_config()
    self_mapping = contract.verify_self_bundle()
    live = contract.verify_live_authorities()
    assert len(self_mapping) == config["bundle"]["self_mapping_exact_count"] == 13
    assert len(live) == config["bundle"]["live_authority_exact_count"] == 168
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
    assert "fixed V5 execution-review PASS receipt is absent" in execute.stderr


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


def test_post_rename_requires_independent_v5_readback_and_v2_is_rejected() -> None:
    source = inspect.getsource(controller.run_two_block_nonformal)
    result_rename = source.index("os.replace(staging, result)")
    success_rename = source.index("os.replace(success_staging, success)")
    independent_readback = source.index("contract.verify_published_artifacts(")
    assert result_rename < success_rename < independent_readback
    v2_config = json.loads(
        contract.read_stable(
            contract.ROOT
            / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_v2.json"
        )
    )
    v2_result = contract.ROOT / v2_config["paths"]["result_root"]
    v2_success = contract.ROOT / v2_config["paths"]["success_root"]
    assert v2_result.exists() and v2_success.exists()
    with pytest.raises(contract.ContractRejected):
        contract.verify_published_artifacts(v2_result, v2_success)
