from __future__ import annotations

import importlib
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def runner():
    return importlib.import_module(
        "experiments.run_rq2_public_grid_two_block_pilot_activation_transport_v5"
    )


@pytest.fixture(scope="module")
def worker():
    return importlib.import_module(
        "experiments.worker_rq2_public_grid_two_block_pilot_activation_transport_v5"
    )


def test_v5_module_exists_and_production_remains_closed() -> None:
    runner = importlib.import_module(
        "experiments.run_rq2_public_grid_two_block_pilot_activation_transport_v5"
    )
    assert runner.PRODUCTION_CLOSED is True


def test_v4_escalate_receipt_binds_exact_outer_and_grants_no_execution() -> None:
    receipt = json.loads(
        (
            ROOT
            / "configs/rq2_public_grid_two_block_pilot_activation_transport_review_escalate_v4.json"
        ).read_bytes()
    )
    assert receipt["verdict"] == "ESCALATE"
    assert receipt["reviewed_outer"]["sha256"] == (
        "9ba787c2d3b1ae3db64c675be2409a2a5d1cf2b2fe6b703133885c27efa5d16d"
    )
    assert receipt["review_effect"]["v4_execution_authorized"] is False
    assert receipt["review_effect"]["v5_closed_candidate_creation_authorized"] is True
    assert receipt["review_effect"]["production_worker_authorized"] is False


@pytest.mark.parametrize("method", ["run_two_block_pilot", "run_production_block"])
def test_v5_inherits_literal_pre_pipe_production_close(
    runner, monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    effects = {"pipe": 0, "popen": 0}

    def forbidden_pipe():
        effects["pipe"] += 1
        raise AssertionError

    class ForbiddenPopen:
        def __init__(self, *_args, **_kwargs):
            effects["popen"] += 1
            raise AssertionError

    monkeypatch.setattr(os, "pipe", forbidden_pipe)
    monkeypatch.setattr(subprocess, "Popen", ForbiddenPopen)
    session = runner.ControllerSession()
    with pytest.raises(runner.ProductionClosed):
        getattr(session, method)(
            activation_review_receipt="forged",
            wrapper_review_receipt="self-consistent",
            dispatch_authorization_receipt="caller-path",
        )
    assert effects == {"pipe": 0, "popen": 0}
    assert session.attempted_indices == frozenset()


def test_v5_worker_is_closed_before_handles_or_imports(worker) -> None:
    source = Path(worker.__file__).read_text(encoding="utf-8")
    assert "from experiments" not in source
    with pytest.raises(worker.WorkerV5Rejected, match="permanently closed"):
        worker.main(
            [
                "--internal-production-worker",
                "--read-handle",
                "123",
                "--ack-handle",
                "456",
            ]
        )


class _FakeProcess:
    def __init__(self, pid: int = 50123) -> None:
        self.pid = pid
        self.alive = True
        self.terminate_calls = 0
        self.kill_calls = 0

    def poll(self):
        return None if self.alive else 0

    def terminate(self):
        self.terminate_calls += 1
        self.alive = False

    def kill(self):
        self.kill_calls += 1
        self.alive = False

    def wait(self, timeout: float):
        assert timeout == 1.0
        self.alive = False
        return 0


def _run_boundary_sample(runner, private: int, available: int):
    process = _FakeProcess()
    stop_expected = (
        private >= runner.PRIVATE_COMMIT_LIMIT_BYTES
        or available <= runner.SYSTEM_COMMIT_RESERVE_BYTES
    )

    def sample(_pid: int, _created: int):
        if not stop_expected:
            process.alive = False
        return runner.ResourceSample(private, available)

    terminated: list[tuple[int, int]] = []

    def terminate(_process, *, expected_pid: int, expected_create_time_ns: int):
        terminated.append((expected_pid, expected_create_time_ns))
        process.terminate()

    original = runner.terminate_exact_owned_child
    runner.terminate_exact_owned_child = terminate
    try:
        outcome = runner.monitor_owned_child_resources(
            process,
            expected_pid=process.pid,
            expected_create_time_ns=778899,
            sample=sample,
            sleep=lambda _seconds: None,
        )
    finally:
        runner.terminate_exact_owned_child = original
    return outcome, terminated


@pytest.mark.parametrize(
    ("private", "expected_status"),
    [
        (8 * 1024**3 - 1, "child_exited"),
        (8 * 1024**3, "resource_stop"),
        (8 * 1024**3 + 1, "resource_stop"),
    ],
)
def test_private_commit_boundary_is_greater_equal(
    runner, private: int, expected_status: str
) -> None:
    outcome, terminated = _run_boundary_sample(runner, private, 2 * 1024**3 + 1)
    assert outcome.status == expected_status
    assert outcome.mathematical_infeasibility_inferred is False
    if expected_status == "resource_stop":
        assert outcome.reason == "private_commit_limit_reached"
        assert terminated == [(50123, 778899)]
    else:
        assert terminated == []


@pytest.mark.parametrize(
    ("available", "expected_status"),
    [
        (2 * 1024**3 - 1, "resource_stop"),
        (2 * 1024**3, "resource_stop"),
        (2 * 1024**3 + 1, "child_exited"),
    ],
)
def test_system_commit_boundary_is_less_equal(
    runner, available: int, expected_status: str
) -> None:
    outcome, terminated = _run_boundary_sample(runner, 8 * 1024**3 - 1, available)
    assert outcome.status == expected_status
    assert outcome.mathematical_infeasibility_inferred is False
    if expected_status == "resource_stop":
        assert outcome.reason == "system_commit_reserve_reached"
        assert terminated == [(50123, 778899)]
    else:
        assert terminated == []


def test_combined_private_and_system_thresholds_use_one_sample(runner) -> None:
    outcome, terminated = _run_boundary_sample(runner, 8 * 1024**3, 2 * 1024**3)
    assert outcome.status == "resource_stop"
    assert outcome.reason == "private_and_system_commit_limits_reached"
    assert outcome.samples == 1
    assert terminated == [(50123, 778899)]


@pytest.mark.parametrize("kind", ["exception", "malformed", "negative"])
def test_sampling_error_terminates_owned_child_honestly(runner, kind: str) -> None:
    process = _FakeProcess()
    terminated: list[int] = []

    def terminate(_process, *, expected_pid: int, expected_create_time_ns: int):
        assert expected_create_time_ns == 9001
        terminated.append(expected_pid)
        process.terminate()

    if kind == "exception":
        sample = lambda _pid, _created: (_ for _ in ()).throw(OSError("denied"))
    elif kind == "malformed":
        sample = lambda _pid, _created: {"private": 1}
    else:
        sample = lambda _pid, _created: runner.ResourceSample(-1, 3 * 1024**3)
    original = runner.terminate_exact_owned_child
    runner.terminate_exact_owned_child = terminate
    try:
        outcome = runner.monitor_owned_child_resources(
            process,
            expected_pid=process.pid,
            expected_create_time_ns=9001,
            sample=sample,
            sleep=lambda _seconds: None,
        )
    finally:
        runner.terminate_exact_owned_child = original
    assert outcome.status == "sampling_error"
    assert outcome.honest_incomplete is True
    assert outcome.mathematical_infeasibility_inferred is False
    assert terminated == [process.pid]


def test_watchdog_terminates_owned_child_honestly(runner) -> None:
    process = _FakeProcess()
    terminated: list[int] = []

    def terminate(_process, *, expected_pid: int, expected_create_time_ns: int):
        assert expected_create_time_ns == 9002
        terminated.append(expected_pid)
        process.terminate()

    original = runner.terminate_exact_owned_child
    runner.terminate_exact_owned_child = terminate
    try:
        outcome = runner.monitor_owned_child_resources(
            process,
            expected_pid=process.pid,
            expected_create_time_ns=9002,
            sample=lambda _pid, _created: pytest.fail("sample after watchdog"),
            clock=lambda: 5.0,
            watchdog_deadline=4.0,
        )
    finally:
        runner.terminate_exact_owned_child = original
    assert outcome.status == "timeout"
    assert outcome.honest_incomplete is True
    assert outcome.mathematical_infeasibility_inferred is False
    assert terminated == [process.pid]


def test_foreign_pid_and_identity_drift_never_terminate_unowned_process(
    runner, monkeypatch: pytest.MonkeyPatch
) -> None:
    foreign = _FakeProcess(pid=60001)
    with pytest.raises(runner.ResourceOwnershipIndeterminate, match="not the expected"):
        runner.monitor_owned_child_resources(
            foreign,
            expected_pid=60002,
            expected_create_time_ns=1,
            sample=lambda _pid, _created: pytest.fail("sampled foreign PID"),
        )
    assert foreign.terminate_calls == 0

    target = _FakeProcess(pid=60003)
    monkeypatch.setattr(
        runner.predecessor, "_process_creation_time_ns", lambda _pid: 999
    )
    with pytest.raises(runner.ResourceOwnershipIndeterminate, match="identity drifted") as exc:
        runner.monitor_owned_child_resources(
            target,
            expected_pid=target.pid,
            expected_create_time_ns=111,
            sample=lambda _pid, _created: (_ for _ in ()).throw(OSError("sample")),
        )
    assert exc.value.honest_incomplete is True
    assert exc.value.mathematical_infeasibility_inferred is False
    assert target.terminate_calls == 0


@pytest.mark.skipif(os.name != "nt", reason="native Windows ownership E2E")
def test_real_windows_owned_child_native_sample_and_exact_stop(runner) -> None:
    python = Path(r"D:\conda_envs\rq2-executor-v2-audit\python.exe")
    command = [str(python), "-I", "-B", "-c", "import time; time.sleep(30)"]
    target = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    bystander = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    target_created = runner.predecessor._process_creation_time_ns(target.pid)
    bystander_created = runner.predecessor._process_creation_time_ns(bystander.pid)
    try:
        native = runner.sample_resource_pair(target.pid, target_created)
        assert native.child_private_commit_bytes >= 0
        assert native.system_commit_available_bytes >= 0
        outcome = runner.monitor_owned_child_resources(
            target,
            expected_pid=target.pid,
            expected_create_time_ns=target_created,
            sample=lambda _pid, _created: runner.ResourceSample(
                runner.PRIVATE_COMMIT_LIMIT_BYTES,
                runner.SYSTEM_COMMIT_RESERVE_BYTES + 1,
            ),
            sleep=lambda _seconds: None,
        )
        assert outcome.status == "resource_stop"
        assert target.poll() is not None
        assert bystander.poll() is None
        assert outcome.mathematical_infeasibility_inferred is False
    finally:
        if target.poll() is None:
            runner.terminate_exact_owned_child(
                target,
                expected_pid=target.pid,
                expected_create_time_ns=target_created,
            )
        if bystander.poll() is None:
            runner.terminate_exact_owned_child(
                bystander,
                expected_pid=bystander.pid,
                expected_create_time_ns=bystander_created,
            )
    assert target.poll() is not None
    assert bystander.poll() is not None


def test_preflight_still_requires_ten_gib_and_is_not_runtime_reserve(runner) -> None:
    assert (
        runner.preflight_available_commit(
            observe=lambda: runner.PREFLIGHT_AVAILABLE_COMMIT_BYTES
        )
        == runner.PREFLIGHT_AVAILABLE_COMMIT_BYTES
    )
    with pytest.raises(runner.TransportV5Rejected, match="below"):
        runner.preflight_available_commit(
            observe=lambda: runner.PREFLIGHT_AVAILABLE_COMMIT_BYTES - 1
        )
    contract = dict(runner.future_wrapper_contract())
    assert contract["preflight_10_gib_does_not_replace_runtime_reserve"] is True


def test_future_successor_contract_cannot_omit_reviewed_invariants(runner) -> None:
    contract = dict(runner.future_wrapper_contract())
    assert contract["must_use_resource_monitor_v5"] is True
    assert contract["resource_sample_interval_seconds"] == 5.0
    assert contract["child_private_commit_stop_is_greater_equal_8_gib"] is True
    assert contract["system_commit_available_stop_is_less_equal_2_gib"] is True
    assert contract["each_sample_observes_private_and_system_commit"] is True
    assert contract["must_preserve_atomic_no_retry_v4"] is True
    assert contract["must_preserve_scientific_dependency_closure_v4"] is True
    assert contract["mathematical_infeasibility_inferred_from_failure"] is False
    assert contract["successor_tests_and_independent_review_must_cover_every_field"] is True


def test_science_closure_and_review_only_boundary_remain_non_accepting(runner) -> None:
    signatures = runner.verify_scientific_dependency_closure()
    assert set(signatures) == {"stage", "load", "process", "validate"}
    outcome = runner.ControllerSession().run_review_preloader_boundary(
        timeout_seconds=10.0
    )
    assert outcome.accepted is False
    assert outcome.status == "NON_ACCEPTED_PRELOADER_BOUNDARY"
    assert dict(outcome.counters) == {
        "scientific_loader_calls": 0,
        "solver_calls": 0,
        "result_writes": 0,
        "formal_writes": 0,
    }


def test_validate_only_reports_zero_execution(runner, capsys) -> None:
    assert runner.main(["--validate-only"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["validation_passed"] is True
    assert value["execution_ready"] is False
    assert value["production_workers"] == 0
    assert value["loader_calls"] == 0
    assert value["solver_calls"] == 0
    assert value["result_writes"] == 0
    assert value["formal_writes"] == 0
    with pytest.raises(runner.ProductionClosed):
        runner.main([])


def test_bootstrap_seal_is_closed_and_zero_effect() -> None:
    bootstrap = importlib.import_module(
        "experiments.bootstrap_rq2_public_grid_two_block_pilot_activation_transport_v5"
    )
    value = bootstrap.validate_only()
    assert value["validation_passed"] is True
    assert value["bundle_members"] == 6
    assert value["activation_v5_independent_review_passed"] is False
    assert value["execution_ready"] is False
    assert value["project_imports"] == 0
    assert value["production_workers"] == 0
    assert value["scientific_loader_calls"] == 0
    assert value["solver_calls"] == 0
    assert value["result_writes"] == 0
    assert value["formal_writes"] == 0
    with pytest.raises(bootstrap.BootstrapV5Rejected, match="permanently closed"):
        bootstrap.main(["--execute"])
