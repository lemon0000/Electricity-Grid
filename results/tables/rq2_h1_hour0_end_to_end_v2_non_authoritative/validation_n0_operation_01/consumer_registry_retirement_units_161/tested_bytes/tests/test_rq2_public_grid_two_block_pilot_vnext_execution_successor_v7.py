from __future__ import annotations

import hashlib
import inspect
import json
import os
import subprocess
from copy import deepcopy

import pytest

from experiments import (
    rq2_public_grid_two_block_pilot_vnext_execution_contract_v7 as contract,
)
from experiments import (
    run_rq2_public_grid_two_block_pilot_vnext_execution_successor_v7 as controller,
)


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


_TEST_AUTHORITY_MAPPING = {"authority/test.json": "a" * 64}


def _sampler_prebinding(clock: _Clock) -> dict[str, object]:
    return {
        "schema": "rq2_public_grid_resource_sampler_prebinding_vnext_execution_v7",
        "version": 1,
        "binding_start_wall_time_ns": clock.wall_time_ns(),
        "binding_start_monotonic_ns": clock.monotonic_ns(),
        "binding_completed_wall_time_ns": clock.wall_time_ns(),
        "binding_completed_monotonic_ns": clock.monotonic_ns(),
        "expected_owned_identity": {"pid": 1234, "create_time_ns": 5678},
        "pre_monitor_authority_mapping_sha256": (
            contract.closure_mapping_sha256(_TEST_AUTHORITY_MAPPING)
        ),
        "sampler_scope": "one_owned_child_one_session_no_cross_child_or_session_reuse",
        "sampler_callback": "exact_pid_create_time_same_pair_observation_only",
        "resource_values_cached_between_slots": False,
        "sampler_reused_across_child_or_session": False,
    }


def _deadline_outcome(
    *, detection_overrun_ns: int, termination_duration_ns: int
) -> tuple[dict[str, object], dict[str, object]]:
    clock = _Clock()
    process = _OwnedProcess()
    state = contract.ResourceMonitorState()
    calls = 0

    def sample(_pid: int, _create_time_ns: int) -> tuple[int, int]:
        nonlocal calls
        calls += 1
        if calls == 2:
            clock.advance(
                contract.OBSERVATION_JITTER_BUDGET_NS + detection_overrun_ns
            )
        return 1024, 12 * 1024**3

    def terminate(
        _target: _OwnedProcess, **_identity: int
    ) -> dict[str, object]:
        clock.advance(termination_duration_ns)
        process.exited = True
        return {
            "termination_action": "terminate_only",
            "termination_completed": True,
        }

    path = "memory://deadline-boundary.json"

    def persist(journal: dict[str, object]) -> dict[str, object]:
        return {
            "schema": "rq2_public_grid_resource_monitor_persisted_outcome_vnext_execution_v7",
            "version": 1,
            "resource_journal": journal,
            "persisted_path": path,
            "persisted_sha256": contract.sha256_bytes(
                contract.exact_json_bytes(journal)
            ),
            "readback_verified": True,
            "authority_mapping_match": True,
            "controller_acceptable": True,
        }

    persisted = contract.monitor_owned_child_resources_journal(
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
        sampler_prebinding=_sampler_prebinding(clock),
        verify_post_authority=lambda: _TEST_AUTHORITY_MAPPING,
        persist=persist,
        persistence_path=path,
    )
    return persisted["resource_journal"], persisted


def test_early_sample_deadline_plus_one_ns_exact_two_second_termination_is_honest(
) -> None:
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
        clock.advance(2_000_000_000)
        process.exited = True
        return {
            "termination_action": "terminate_only",
            "termination_completed": True,
        }

    def persist(journal: dict[str, object]) -> dict[str, object]:
        return {
            "schema": "rq2_public_grid_resource_monitor_persisted_outcome_vnext_execution_v7",
            "version": 1,
            "resource_journal": journal,
            "persisted_path": "memory://exact-two-second.json",
            "persisted_sha256": contract.sha256_bytes(
                contract.exact_json_bytes(journal)
            ),
            "readback_verified": True,
            "authority_mapping_match": True,
            "controller_acceptable": True,
        }

    persisted = contract.monitor_owned_child_resources_journal(
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
        sampler_prebinding=_sampler_prebinding(clock),
        verify_post_authority=lambda: _TEST_AUTHORITY_MAPPING,
        persist=persist,
        persistence_path="memory://exact-two-second.json",
    )
    outcome = persisted["resource_journal"]
    assert outcome["status"] == "resource_sample_deadline_missed"
    assert outcome["reason"] == "resource_sample_deadline_missed"
    assert outcome["last_sample_to_exit_ns"] == 8_000_000_001
    assert outcome["termination"]["termination_duration_ns"] == 2_000_000_000
    assert outcome["deadline_missed"]["detection_overrun_ns"] == 1
    assert outcome["deadline_to_exit_observed_ns"] == 2_000_000_001
    assert outcome["last_sample_to_exit_ns"] == 8_000_000_001
    assert state.outcome == persisted


def test_v7_test_module_uses_detection_and_duration_not_fixed_exit_cap() -> None:
    assert contract.MAX_DETECTION_OVERRUN_NS == 1_000_000_000
    assert contract.OWNED_TERMINATION_GRACE_NS == 2_000_000_000
    assert not hasattr(contract, "TERMINATION_LAST_SAMPLE_TO_EXIT_MAX_NS")
    with pytest.raises(contract.ContractRejected):
        contract.validate_resource_journal({})


@pytest.mark.parametrize("duration_ns", [0, 1_000_000_000, 2_000_000_000])
def test_deadline_termination_duration_boundaries_are_accepted(
    duration_ns: int,
) -> None:
    journal, _persisted = _deadline_outcome(
        detection_overrun_ns=1, termination_duration_ns=duration_ns
    )
    assert journal["status"] == "resource_sample_deadline_missed"
    assert journal["termination_request_to_end_ns"] == duration_ns


def test_deadline_termination_duration_one_ns_above_grace_is_indeterminate() -> None:
    journal, _persisted = _deadline_outcome(
        detection_overrun_ns=1,
        termination_duration_ns=contract.OWNED_TERMINATION_GRACE_NS + 1,
    )
    assert journal["status"] == "termination_indeterminate"
    assert journal["reason"] == "owned_termination_grace_exceeded"


@pytest.mark.parametrize(
    ("overrun_ns", "expected_status"),
    [
        (contract.MAX_DETECTION_OVERRUN_NS, "resource_sample_deadline_missed"),
        (contract.MAX_DETECTION_OVERRUN_NS + 1, "termination_indeterminate"),
    ],
)
def test_deadline_detection_overrun_boundary(
    overrun_ns: int, expected_status: str
) -> None:
    journal, _persisted = _deadline_outcome(
        detection_overrun_ns=overrun_ns, termination_duration_ns=1
    )
    assert journal["status"] == expected_status
    if expected_status == "termination_indeterminate":
        assert journal["reason"] == "resource_sample_detection_overrun_exceeded"


def test_exact_timestamp_delta_tamper_is_rejected() -> None:
    journal, _persisted = _deadline_outcome(
        detection_overrun_ns=1, termination_duration_ns=2_000_000_000
    )
    journal["deadline_to_exit_observed_ns"] += 1
    with pytest.raises(contract.ContractRejected):
        contract.validate_resource_journal(journal)


def test_normal_child_exit_above_six_seconds_is_rejected() -> None:
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
    journal["last_sample_to_exit_ns"] += (
        contract.NORMAL_LAST_SAMPLE_TO_EXIT_MAX_NS + 1
    )
    with pytest.raises(contract.ContractRejected):
        contract.validate_resource_journal(journal)


def test_monitor_persistence_wrapper_binds_path_hash_and_readback(tmp_path) -> None:
    journal = contract.synthetic_deadline_missed_journal_for_test(
        pid=1234, create_time_ns=5678
    )
    path = tmp_path / "resource_journal.json"
    persisted = controller._persist_resource_journal(path, journal)
    assert contract.validate_resource_monitor_outcome(
        persisted, expected_path=str(path)
    ) == persisted
    assert path.read_bytes() == contract.exact_json_bytes(journal)
    for field, value in (
        ("persisted_sha256", "0" * 64),
        ("readback_verified", False),
        ("persisted_path", str(path.with_name("other.json"))),
        ("authority_mapping_match", False),
        ("controller_acceptable", False),
    ):
        tampered = dict(persisted)
        tampered[field] = value
        with pytest.raises(contract.ContractRejected):
            contract.validate_resource_monitor_outcome(
                tampered, expected_path=str(path)
            )


@pytest.mark.parametrize("post_mode", ["digest_mismatch", "verification_error"])
def test_post_monitor_authority_failure_is_persisted_before_fail_closed(
    post_mode: str, tmp_path
) -> None:
    clock = _Clock()
    process = _OwnedProcess()
    state = contract.ResourceMonitorState()

    def sample(pid: int, create_time_ns: int) -> tuple[int, int]:
        assert (pid, create_time_ns) == (1234, 5678)
        process.exited = True
        return 1024, 12 * 1024**3

    def verify_post() -> dict[str, str]:
        if post_mode == "verification_error":
            raise contract.ContractRejected("review fault")
        return {"authority/test.json": "b" * 64}

    path = tmp_path / f"{post_mode}.json"
    persisted = contract.monitor_owned_child_resources_journal(
        process,
        expected_pid=1234,
        expected_create_time_ns=5678,
        watchdog_duration_ns=contract.WATCHDOG_NS,
        state=state,
        sample=sample,
        monotonic_ns=clock.monotonic_ns,
        wall_time_ns=clock.wall_time_ns,
        sleep=clock.sleep,
        terminate=lambda *_args, **_kwargs: {
            "termination_action": "already_exited_before_signal",
            "termination_completed": True,
        },
        sampler_prebinding=_sampler_prebinding(clock),
        verify_post_authority=verify_post,
        persist=lambda journal: controller._persist_resource_journal(path, journal),
        persistence_path=str(path),
    )
    journal = persisted["resource_journal"]
    binding = journal["resource_sampler_binding"]
    assert journal["status"] == "child_exited"
    assert binding["authority_mapping_match"] is False
    assert persisted["controller_acceptable"] is False
    assert path.read_bytes() == contract.exact_json_bytes(journal)
    if post_mode == "verification_error":
        assert binding["post_monitor_authority_verification_status"] == (
            "verification_error"
        )
        assert binding["post_monitor_authority_verification_error"] == (
            "ContractRejected"
        )
    else:
        assert binding["post_monitor_authority_verification_status"] == "verified"
        assert binding["post_monitor_authority_mapping_sha256"] != binding[
            "pre_monitor_authority_mapping_sha256"
        ]


def test_real_controller_no_exit_notice_persists_incomplete_journal(
    tmp_path,
) -> None:
    outcome = controller.run_review_deadline_no_exit_probe_e2e(tmp_path)
    journal = outcome["resource_journal"]
    path = tmp_path / "controller_resource_journal.json"
    assert outcome["classification"] == "HONEST_INCOMPLETE"
    assert outcome["exit_notice_received"] is False
    assert outcome["worker_exited"] is True
    assert journal["status"] == "resource_sample_deadline_missed"
    assert journal["deadline_missed"]["detection_overrun_ns"] == 1
    assert journal["termination"]["termination_duration_ns"] == 2_000_000_000
    assert path.read_bytes() == contract.exact_json_bytes(journal)
    assert outcome["scientific_loader_calls"] == 0
    assert outcome["solver_calls"] == 0
    assert outcome["result_writes"] == 0
    assert outcome["success_writes"] == 0


def test_resource_authority_binding_delay_precedes_monitor_clock(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    process = _OwnedProcess()
    observed_identity: list[tuple[int, int]] = []

    class _Observed:
        child_private_commit_bytes = 1024
        system_commit_available_bytes = 12 * 1024**3

    class _DelayedAuthority:
        def sample_resource_pair(self, pid: int, create_time_ns: int) -> _Observed:
            observed_identity.append((pid, create_time_ns))
            process.exited = True
            return _Observed()

    def delayed_binding() -> _DelayedAuthority:
        import time

        time.sleep(1.05)
        return _DelayedAuthority()

    monkeypatch.setattr(contract, "resource_primitives", delayed_binding)
    monkeypatch.setattr(
        contract,
        "verify_live_authorities",
        lambda: {"authority/test.json": "a" * 64},
    )
    _state, executor, future, _deadline = controller._start_resource_monitor(
        process,
        {"pid": 1234, "ppid": 1, "create_time_ns": 5678},
        tmp_path / "controller_resource_journal.json",
        terminate=lambda *_args, **_kwargs: {
            "termination_action": "already_exited_before_signal",
            "termination_completed": True,
        },
    )
    try:
        persisted = future.result(timeout=10)
    finally:
        executor.shutdown(wait=True)
    journal = persisted["resource_journal"]
    assert journal["status"] == "child_exited"
    assert journal["sample_count"] == 1
    assert journal["samples"][0]["actual_observation_lateness_ns"] < (
        contract.OBSERVATION_JITTER_BUDGET_NS
    )
    assert journal["resource_sampler_binding"][
        "binding_completed_monotonic_ns"
    ] <= journal["monitor_start_monotonic_ns"]
    assert journal["resource_sampler_binding"]["authority_mapping_match"] is True
    assert observed_identity == [(1234, 5678)]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("binding_completed_monotonic_ns", 1_000_000_000_001),
        ("expected_owned_identity", {"pid": 9999, "create_time_ns": 5678}),
        ("pre_monitor_authority_mapping_sha256", "b" * 64),
        ("resource_values_cached_between_slots", True),
        ("sampler_reused_across_child_or_session", True),
    ],
)
def test_resource_sampler_binding_tamper_is_rejected(
    field: str, value: object
) -> None:
    journal = contract.synthetic_resource_journal_for_test(
        pid=1234,
        create_time_ns=5678,
        private_values=(1024,),
        available_values=(12 * 1024**3,),
    )
    journal["resource_sampler_binding"][field] = value
    with pytest.raises(contract.ContractRejected):
        contract.validate_resource_journal(journal)


def test_sampler_is_per_child_and_slot_callback_has_no_authority_rehash(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    authorities: list[object] = []
    observed: list[tuple[int, int, int]] = []

    class _Authority:
        def __init__(self) -> None:
            self.number = len(authorities)

        def sample_resource_pair(self, pid: int, create_time_ns: int):
            observed.append((self.number, pid, create_time_ns))
            processes[self.number].exited = True
            return type(
                "Observed",
                (),
                {
                    "child_private_commit_bytes": 1024,
                    "system_commit_available_bytes": 12 * 1024**3,
                },
            )()

    def new_authority() -> _Authority:
        authority = _Authority()
        authorities.append(authority)
        return authority

    processes = [_OwnedProcess(), _OwnedProcess()]
    monkeypatch.setattr(contract, "resource_primitives", new_authority)
    monkeypatch.setattr(
        contract, "verify_live_authorities", lambda: _TEST_AUTHORITY_MAPPING
    )
    for index, process in enumerate(processes):
        state, executor, future, _deadline = controller._start_resource_monitor(
            process,
            {"pid": 1234, "ppid": 1, "create_time_ns": 5678 + index},
            tmp_path / f"resource-{index}.json",
            terminate=lambda *_args, **_kwargs: {
                "termination_action": "already_exited_before_signal",
                "termination_completed": True,
            },
        )
        try:
            persisted = future.result(timeout=10)
        finally:
            executor.shutdown(wait=True)
        assert persisted["controller_acceptable"] is True
        assert state.first_sample_success is True
    assert len(authorities) == 2
    assert observed == [(0, 1234, 5678), (1, 1234, 5679)]
    start_source = inspect.getsource(controller._start_resource_monitor)
    callback_source = start_source[start_source.index("def sample_bound_pair") :]
    assert "contract.resource_primitives()" not in callback_source


@pytest.mark.parametrize(
    "mutation",
    ["hundred_second_gap", "two_second_catch_up", "missing_slot", "late_by_one"],
)
def test_inherited_scheduler_faults_remain_rejected(mutation: str) -> None:
    journal = contract.synthetic_resource_journal_for_test(
        pid=101,
        create_time_ns=202,
        private_values=(100, 200),
        available_values=(12 * 1024**3, 11 * 1024**3),
    )
    second = journal["samples"][1]
    if mutation == "hundred_second_gap":
        second["monotonic_ns"] = journal["samples"][0]["monotonic_ns"] + 100_000_000_000
        second["actual_observation_lateness_ns"] = (
            second["monotonic_ns"] - second["scheduled_monotonic_ns"]
        )
    elif mutation == "two_second_catch_up":
        second["monotonic_ns"] = journal["samples"][0]["monotonic_ns"] + 2_000_000_000
        second["actual_observation_lateness_ns"] = (
            second["monotonic_ns"] - second["scheduled_monotonic_ns"]
        )
    elif mutation == "missing_slot":
        second["scheduled_monotonic_ns"] += contract.SAMPLE_INTERVAL_NS
        second["sample_deadline_monotonic_ns"] += contract.SAMPLE_INTERVAL_NS
    else:
        second["monotonic_ns"] = (
            second["scheduled_monotonic_ns"]
            + contract.OBSERVATION_JITTER_BUDGET_NS
            + 1
        )
        second["actual_observation_lateness_ns"] = (
            contract.OBSERVATION_JITTER_BUDGET_NS + 1
        )
    with pytest.raises(contract.ContractRejected):
        contract.validate_resource_journal(journal)


@pytest.mark.parametrize("failure_mode", ["raised", "malformed"])
def test_termination_failure_persists_indeterminate_journal(
    failure_mode: str,
) -> None:
    clock = _Clock()
    process = _OwnedProcess()
    state = contract.ResourceMonitorState()
    calls = 0

    def sample(_pid: int, _created: int) -> tuple[int, int]:
        nonlocal calls
        calls += 1
        if calls == 2:
            clock.advance(contract.OBSERVATION_JITTER_BUDGET_NS + 1)
        return 1024, 12 * 1024**3

    def terminate(_target: _OwnedProcess, **_identity: int) -> dict[str, object]:
        if failure_mode == "raised":
            raise RuntimeError("synthetic identity failure")
        return {"unexpected": True}

    path = f"memory://termination-{failure_mode}.json"

    def persist(journal: dict[str, object]) -> dict[str, object]:
        return {
            "schema": "rq2_public_grid_resource_monitor_persisted_outcome_vnext_execution_v7",
            "version": 1,
            "resource_journal": journal,
            "persisted_path": path,
            "persisted_sha256": contract.sha256_bytes(
                contract.exact_json_bytes(journal)
            ),
            "readback_verified": True,
            "authority_mapping_match": True,
            "controller_acceptable": True,
        }

    persisted = contract.monitor_owned_child_resources_journal(
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
        sampler_prebinding=_sampler_prebinding(clock),
        verify_post_authority=lambda: _TEST_AUTHORITY_MAPPING,
        persist=persist,
        persistence_path=path,
    )
    journal = persisted["resource_journal"]
    assert journal["status"] == "termination_indeterminate"
    assert journal["reason"] == "owned_identity_or_termination_failed"
    assert journal["termination"]["termination_completed"] is False
    assert persisted["readback_verified"] is True


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
def test_lease_failure_points_leave_only_seed_free_tombstone(
    failure_point: str,
) -> None:
    outcome = controller.run_review_lease_acquire_probe(failure_point)
    assert outcome["failure_injected"] is True
    assert outcome["fresh_raw_seed_present"] is False
    assert outcome["consumed_raw_seed_present"] is False
    assert outcome["tombstone_present"] is True
    assert outcome["tombstone_seed_present"] is False
    assert outcome["returned_seed"] is False


def test_normal_review_sign_destroys_test_seed_and_reuse_is_rejected() -> None:
    outcome = controller.run_review_lease_acquire_probe(None)
    assert outcome["signature_verified"] is True
    assert outcome["fresh_raw_seed_present"] is False
    assert outcome["consumed_raw_seed_present"] is False
    assert outcome["tombstone_seed_present"] is False
    source = inspect.getsource(controller.run_two_block_nonformal)
    assert "one-time V7 key was already consumed" in source
    assert '"one_time_key_reusable": False' in source
    assert '"seed_present": False' in source


def test_ordinary_import_has_no_production_signing_authority() -> None:
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


def test_frozen_audit_values_and_science_thresholds_are_exact() -> None:
    config = contract.load_config()
    resource = config["resource_contract"]
    assert resource["sample_interval_ns"] == 5_000_000_000
    assert resource["observation_jitter_budget_ns"] == 1_000_000_000
    assert resource["normal_last_sample_to_exit_max_ns"] == 6_000_000_000
    assert resource["max_detection_overrun_ns"] == 1_000_000_000
    assert resource["owned_termination_grace_ns"] == 2_000_000_000
    assert resource["terminate_wait_ns"] == resource["kill_wait_ns"] == 1_000_000_000
    assert resource["catch_up_sampling_allowed"] is False
    assert resource["child_private_commit_stop_bytes"] == 8 * 1024**3
    assert resource["system_commit_available_stop_bytes"] == 2 * 1024**3
    assert config["science_authority"]["solver"]["expected_package_version"] == "1.15.1"
    assert config["science_authority"]["solver"]["threads"] == 4
    assert all(value is False for value in config["gates"].values())


def test_lamport_signature_valid_and_tamper_wrong_key_fail() -> None:
    seed = bytes.fromhex("11" * 32)
    public_key = contract.derive_lamport_public_key(seed)
    digest = hashlib.sha256(b"v7 synthetic payload").hexdigest()
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


def test_v7_public_anchor_has_no_private_material() -> None:
    value = json.loads(contract.read_stable(contract.PUBLIC_KEY))
    assert set(value) == contract.PUBLIC_KEY_KEYS
    assert "seed_hex" not in value
    assert value["key_id"] == (
        "187ee2628b0e6e1c4fb3985f34e02881a3fed3381a31c94e2d52f1d042419023"
    )
    assert value["public_key_sha256"] == (
        "8d5064c4b8b9f8f9377a65bf5a158774e0dd3659a2e512351dfa6aab0d8704ca"
    )
    assert value["security_certified"] is False


def test_resource_journal_and_success_readback_are_signed_substance() -> None:
    identity = {
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "create_time_ns": contract.process_create_time_ns(os.getpid()),
    }
    runtime = contract.collect_solver_runtime_evidence(identity)
    journals = {
        contract.BLOCKS[0]: contract.synthetic_resource_journal_for_test(
            pid=101,
            create_time_ns=201,
            private_values=(1001,),
            available_values=(12 * 1024**3,),
        ),
        contract.BLOCKS[1]: contract.synthetic_resource_journal_for_test(
            pid=102,
            create_time_ns=202,
            private_values=(1002,),
            available_values=(11 * 1024**3,),
        ),
    }
    core = {"resource_journals": journals}
    payload = contract.build_attestation_payload(
        session_id="test-session",
        entries={"summary.json": contract.exact_json_bytes(core)},
        resource_journals=journals,
        runtime_evidence={block: runtime for block in contract.BLOCKS},
        result_manifest_core=core,
        success_core=core,
        closure_mapping={},
    )
    seed = bytes.fromhex("44" * 32)
    public = contract.derive_lamport_public_key(seed)
    digest = contract.sha256_bytes(contract.exact_json_bytes(payload))
    signature = contract.lamport_sign_digest(seed, digest)
    contract.verify_lamport_signature(digest, signature, public)
    tampered = deepcopy(payload)
    tampered["success_readback_substantive_core"]["resource_journals"][
        contract.BLOCKS[1]
    ]["resource_sampler_binding"]["authority_mapping_match"] = False
    with pytest.raises(contract.ContractRejected):
        contract.verify_lamport_signature(
            contract.sha256_bytes(contract.exact_json_bytes(tampered)),
            signature,
            public,
        )
    incomplete = dict(journals)
    incomplete[contract.BLOCKS[1]] = (
        contract.synthetic_deadline_missed_journal_for_test(
            pid=102, create_time_ns=202
        )
    )
    with pytest.raises(contract.ContractRejected):
        contract.build_attestation_payload(
            session_id="test-session",
            entries={"summary.json": contract.exact_json_bytes(core)},
            resource_journals=incomplete,
            runtime_evidence={block: runtime for block in contract.BLOCKS},
            result_manifest_core=core,
            success_core=core,
            closure_mapping={},
        )


def test_actual_worker_time_highs_runtime_evidence_is_exact() -> None:
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
    value = journal["termination"][field]
    if isinstance(value, bool):
        journal["termination"][field] = not value
    elif isinstance(value, int):
        journal["termination"][field] = value + 1
    elif isinstance(value, str):
        journal["termination"][field] = "forged"
    else:
        journal["termination"][field] = {}
    with pytest.raises(contract.ContractRejected):
        contract.validate_resource_journal(journal)


def test_execution_review_gate_precedes_v7_production_lease_touch() -> None:
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


def test_v6_regression_and_seed_free_revocation_are_exact() -> None:
    contract.verify_v6_regression_and_revocation()
    frozen = contract.load_config()["predecessor_v6"]
    assert contract._sha_file(contract.ROOT / frozen["outer_path"]) == frozen[
        "outer_sha256"
    ]
    assert contract._sha_file(contract.ROOT / frozen["inner_path"]) == frozen[
        "inner_sha256"
    ]
    tombstone = json.loads(
        contract.read_stable(contract.ROOT / frozen["revoked_tombstone_path"])
    )
    assert tombstone["state"] == "revoked"
    assert tombstone["seed_present"] is False
    assert "seed_hex" not in tombstone
    assert not (
        contract.ROOT
        / frozen["revoked_tombstone_path"].replace(".consumed", ".lease")
    ).exists()


def test_bundle_live_closure_new_roots_and_review_absence() -> None:
    config = contract.load_config()
    self_mapping = contract.verify_self_bundle()
    live = contract.verify_live_authorities()
    assert len(self_mapping) == config["bundle"]["self_mapping_exact_count"] == 13
    assert len(live) == config["bundle"]["live_authority_exact_count"]
    assert contract.PUBLIC_KEY.relative_to(contract.ROOT).as_posix() in self_mapping
    assert contract.REVIEW.exists() is False
    for relative in config["paths"].values():
        assert not (contract.ROOT / relative).exists()


def test_fast_child_and_preloader_probes_make_zero_solver_calls() -> None:
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


def test_canonical_validate_only_and_execute_remain_review_gated() -> None:
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
    assert "fixed V7 execution-review PASS receipt is absent" in execute.stderr


def test_formal_assets_and_nine_checkpoints_unchanged() -> None:
    frozen = contract.load_config()["formal_protection"]
    assert contract._sha_file(contract.ROOT / frozen["formal_runner_path"]) == frozen[
        "formal_runner_sha256"
    ]
    assert contract._sha_file(
        contract.ROOT / frozen["activated_config_path"]
    ) == frozen["activated_config_sha256"]
    checkpoints = list(
        (
            contract.ROOT
            / "results/checkpoints/rts_gmlc_public_grid_need_dispatch_v4_gurobi"
        ).glob("*.json")
    )
    assert len(checkpoints) == frozen["checkpoint_count"] == 9


def test_post_rename_readback_and_cross_protocol_rejection_remain() -> None:
    source = inspect.getsource(controller.run_two_block_nonformal)
    assert source.index("os.replace(staging, result)") < source.index(
        "os.replace(success_staging, success)"
    ) < source.index("contract.verify_published_artifacts(")
    v2_config = json.loads(
        contract.read_stable(
            contract.ROOT
            / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_v2.json"
        )
    )
    with pytest.raises(contract.ContractRejected):
        contract.verify_published_artifacts(
            contract.ROOT / v2_config["paths"]["result_root"],
            contract.ROOT / v2_config["paths"]["success_root"],
        )
