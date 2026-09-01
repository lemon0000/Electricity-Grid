from __future__ import annotations

import hashlib
import importlib
import json
import os
import subprocess
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def controller():
    return importlib.import_module(
        "experiments.run_rq2_public_grid_two_block_pilot_execution_controller_successor_v1"
    )


@pytest.fixture(scope="module")
def worker():
    return importlib.import_module(
        "experiments.worker_rq2_public_grid_two_block_pilot_execution_controller_successor_v1"
    )


@pytest.fixture(scope="module")
def bootstrap():
    return importlib.import_module(
        "experiments.bootstrap_rq2_public_grid_two_block_pilot_execution_controller_successor_v1"
    )


def test_successor_modules_exist() -> None:
    controller = importlib.import_module(
        "experiments.run_rq2_public_grid_two_block_pilot_execution_controller_successor_v1"
    )
    worker = importlib.import_module(
        "experiments.worker_rq2_public_grid_two_block_pilot_execution_controller_successor_v1"
    )
    assert controller.EXECUTION_REVIEW_REQUIRED is True
    assert worker.EXECUTION_REVIEW_REQUIRED is True


def test_v5_pass_receipt_binds_exact_outer_and_does_not_execute() -> None:
    receipt = json.loads(
        (
            ROOT
            / "configs/rq2_public_grid_two_block_pilot_activation_transport_review_pass_v5.json"
        ).read_bytes()
    )
    assert receipt["verdict"] == "PASS"
    assert receipt["reviewed_outer"]["sha256"] == (
        "2afd26332d4965de625e46d8fdac3083559e5b6d8925876c00866ff368451e48"
    )
    assert receipt["effect"]["versioned_execution_controller_worker_successor_creation_authorized"] is True
    assert receipt["effect"]["successor_execution_authorized"] is False
    assert receipt["effect"]["pilot_execution_authorized"] is False


def test_fixed_execution_review_receipt_is_absent_and_not_cli_configurable() -> None:
    config = json.loads(
        (
            ROOT
            / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v1.json"
        ).read_bytes()
    )
    review = config["fixed_execution_review"]
    assert review["present"] is False
    assert review["receipt_path_is_cli_configurable"] is False
    assert review["receipt_self_signing_allowed"] is False
    assert not (ROOT / review["path"]).exists()


def test_bootstrap_execute_missing_receipt_rejects_before_controller_import() -> None:
    config = json.loads(
        (
            ROOT
            / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v1.json"
        ).read_bytes()
    )
    command = [
        config["runtime"]["locked_python_executable"],
        "-B",
        "-m",
        "experiments.bootstrap_rq2_public_grid_two_block_pilot_execution_controller_successor_v1",
        "--execute",
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=config["runtime"]["sanitized_environment"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert completed.returncode != 0
    assert (
        "fixed execution review receipt is absent" in completed.stderr
        or "active related process rejected" in completed.stderr
    )
    for relative in config["paths"].values():
        assert not os.path.lexists(ROOT / relative)


def test_execute_missing_receipt_rejects_before_pipe_popen_or_science_import(
    controller, monkeypatch: pytest.MonkeyPatch
) -> None:
    effects = {"pipe": 0, "popen": 0, "science": 0}

    def forbidden_pipe():
        effects["pipe"] += 1
        raise AssertionError

    class ForbiddenPopen:
        def __init__(self, *_args, **_kwargs):
            effects["popen"] += 1
            raise AssertionError

    monkeypatch.setattr(controller.os, "pipe", forbidden_pipe)
    monkeypatch.setattr(controller.subprocess, "Popen", ForbiddenPopen)
    with pytest.raises(controller.SuccessorRejected, match="path unavailable"):
        controller.ControllerSession().run_two_block_pilot()
    assert effects == {"pipe": 0, "popen": 0, "science": 0}


def test_direct_controller_cannot_bypass_exact_bootstrap_after_review(
    controller, monkeypatch: pytest.MonkeyPatch
) -> None:
    effects = {"resource_import": 0, "pipe": 0}
    monkeypatch.setattr(controller, "_load_execution_authority", dict)
    monkeypatch.setattr(
        controller.sys,
        "orig_argv",
        [controller.sys.executable, "-B", "-m", controller.MODULE, "--execute"],
    )

    def forbidden_resource():
        effects["resource_import"] += 1
        raise AssertionError

    def forbidden_pipe():
        effects["pipe"] += 1
        raise AssertionError

    monkeypatch.setattr(controller, "_resource_authority", forbidden_resource)
    monkeypatch.setattr(controller.os, "pipe", forbidden_pipe)
    with pytest.raises(controller.SuccessorRejected, match="exact reviewed bootstrap"):
        controller.ControllerSession().run_two_block_pilot()
    assert effects == {"resource_import": 0, "pipe": 0}


def test_real_exact_worker_reaches_only_nonaccepting_preloader_boundary(controller) -> None:
    session = controller.ControllerSession()
    outcome = session.run_review_preloader_boundary(timeout_seconds=10.0)
    assert outcome.status == "NON_ACCEPTED_PRELOADER_BOUNDARY"
    assert outcome.accepted is False
    assert dict(outcome.counters) == {
        "loader_calls": 0,
        "solver_calls": 0,
        "result_writes": 0,
        "formal_writes": 0,
    }
    assert outcome.mathematical_infeasibility_inferred is False
    assert session.attempted_indices == frozenset({1})


def test_review_child_command_cwd_and_environment_are_exact(controller) -> None:
    config = controller._load_config()
    command = controller._worker_command(config, 101, 202)
    assert command == [
        config["runtime"]["locked_python_executable"],
        "-B",
        "-m",
        controller.WORKER_MODULE,
        "--internal-successor-worker",
        "--read-handle",
        "101",
        "--ack-handle",
        "202",
    ]
    assert config["runtime"]["exact_cwd"] == str(ROOT)
    assert "PYTHONPATH" not in config["runtime"]["sanitized_environment"]
    assert "PYTHONHOME" not in config["runtime"]["sanitized_environment"]


def test_worker_public_or_malformed_invocation_rejected(worker) -> None:
    with pytest.raises(worker.SuccessorWorkerRejected, match="public/malformed"):
        worker.main([])


@pytest.mark.parametrize(
    "mutation",
    ["parent", "argv", "environment", "controller_hash", "worker_hash", "config_hash"],
)
def test_worker_authority_mutations_fail_before_science(
    controller, worker, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    config = controller._load_config()

    class Process:
        pid = 3333

    created = 4444
    envelope = controller._build_envelope(
        config=config,
        process=Process(),
        child_create_ns=created,
        execution_index=1,
        mode="review_only_preloader_stop",
        ledger=None,
        authority=None,
        read_handle=101,
        ack_handle=202,
    )
    envelope["parent_pid"] = 2222
    envelope["parent_create_time_ns"] = 1111
    envelope["parent_process_identity"]["pid"] = 2222
    envelope["parent_process_identity"]["create_time_ns"] = 1111
    # ``worker.os`` is the process-global ``os`` module, so build the controller
    # envelope before replacing the worker identity probes.
    monkeypatch.setattr(worker.os, "getpid", lambda: Process.pid)
    monkeypatch.setattr(worker.os, "getppid", lambda: 2222)
    monkeypatch.setattr(
        worker,
        "_process_creation_time_ns",
        lambda pid: {2222: 1111, 3333: created}[pid],
    )
    monkeypatch.setattr(
        worker.os, "environ", dict(config["runtime"]["sanitized_environment"])
    )
    monkeypatch.setattr(worker.Path, "cwd", staticmethod(lambda: ROOT))
    if mutation == "parent":
        envelope["parent_pid"] = 9999
    elif mutation == "argv":
        envelope["worker_command"] = ["sleep.exe"]
    elif mutation == "environment":
        envelope["sanitized_environment"] = {"PYTHONPATH": "forged"}
    elif mutation == "controller_hash":
        envelope["controller_sha256"] = "0" * 64
    elif mutation == "worker_hash":
        envelope["worker_sha256"] = "0" * 64
    elif mutation == "config_hash":
        envelope["config_sha256"] = "0" * 64
    with pytest.raises(worker.SuccessorWorkerRejected):
        worker._validate_envelope(envelope, config=config, read_handle=101, ack_handle=202)


def test_RLock_attempt_consumption_is_atomic_and_no_retry(
    controller, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = threading.Barrier(3)
    entered = threading.Event()
    release = threading.Event()
    calls: list[int] = []

    def dispatch(**_kwargs):
        calls.append(1)
        entered.set()
        assert release.wait(5)
        return (
            controller.ReviewOutcome(
                "NON_ACCEPTED_PRELOADER_BOUNDARY", False, 1, {}, False
            ),
            {},
        )

    monkeypatch.setattr(controller, "_dispatch_transport", dispatch)
    session = controller.ControllerSession()
    observed: list[object] = []

    def invoke():
        started.wait()
        try:
            observed.append(session.run_review_preloader_boundary())
        except controller.SuccessorRejected as exc:
            observed.append(exc)

    threads = [threading.Thread(target=invoke) for _ in range(2)]
    for thread in threads:
        thread.start()
    started.wait()
    assert entered.wait(5)
    release.set()
    for thread in threads:
        thread.join(5)
        assert not thread.is_alive()
    assert len(calls) == 1
    assert sum(isinstance(value, controller.ReviewOutcome) for value in observed) == 1
    assert sum(isinstance(value, controller.SuccessorRejected) for value in observed) == 1
    with pytest.raises(controller.SuccessorRejected, match="no-retry"):
        session.run_review_preloader_boundary()


def test_zero_solver_orchestration_enforces_0008_then_0009_and_v7_shape(controller) -> None:
    calls: list[tuple[str, int, str | None]] = []

    def dispatch(block: str, index: int, predecessor: str | None):
        calls.append((block, index, predecessor))
        return {
            "block_id": block,
            "execution_index": index,
            "predecessor_digest": predecessor,
            "accepted": True,
            "all_hours_resolved": True,
            "certificate_valid": True,
            "mathematical_infeasibility_inferred": False,
        }

    publications: list[tuple[dict, ...]] = []

    def publish(records):
        publications.append(tuple(dict(record) for record in records))
        return {
            "publisher": "sealed_v7_unified_snapshot_atomic_publication",
            "classification": "committed_success_shape_only",
            "writes": 0,
        }

    seam = controller.register_zero_solver_orchestration_seam(
        dispatch=dispatch, publish_v7=publish
    )
    result = dict(controller.audit_zero_solver_orchestration(seam))
    assert [row[:2] for row in calls] == [
        ("holdout_s20260822_0008", 1),
        ("holdout_s20260822_0009", 2),
    ]
    assert calls[0][2] is None
    assert calls[1][2] is not None
    assert len(publications) == 1
    assert result["dispatch_calls"] == 2
    assert result["publication_calls"] == 1
    assert result["solver_calls"] == 0
    assert result["writes"] == 0
    assert result["accepted_for_execution"] is False


def test_unresolved_0008_stops_before_0009_and_publication(controller) -> None:
    calls: list[int] = []
    publications: list[int] = []

    def dispatch(_block: str, index: int, _predecessor: str | None):
        calls.append(index)
        return {
            "block_id": "holdout_s20260822_0008",
            "execution_index": 1,
            "predecessor_digest": None,
            "accepted": False,
            "all_hours_resolved": False,
            "certificate_valid": False,
            "mathematical_infeasibility_inferred": False,
        }

    seam = controller.register_zero_solver_orchestration_seam(
        dispatch=dispatch,
        publish_v7=lambda _records: publications.append(1),
    )
    with pytest.raises(controller.SuccessorRejected, match="unresolved"):
        controller.audit_zero_solver_orchestration(seam)
    assert calls == [1]
    assert publications == []


def test_production_source_uses_sealed_science_and_v7_publication_only(
    controller, worker
) -> None:
    controller_source = Path(controller.__file__).read_text(encoding="utf-8")
    worker_source = Path(worker.__file__).read_text(encoding="utf-8")
    assert "v7._publish_result(" in controller_source
    assert "v4._build_controller_receipt(" in controller_source
    assert "v4.AcceptedEvidence(" in controller_source
    assert "v4._expected_accepted_digest(" in controller_source
    assert "_stage_context()" in worker_source
    assert "_load_worker_data(context)" in worker_source
    assert "recovery.v4._process_block(" in worker_source
    assert "recovery._validate_scientific_payload(" in worker_source
    assert "_dispatch_one(" not in controller_source + worker_source
    assert "_worker_from_capability(" not in controller_source + worker_source


def test_successor_envelope_is_accepted_by_sealed_v4_result_and_ack_adapters(
    controller,
) -> None:
    v4 = importlib.import_module(
        "experiments.run_rq2_public_grid_two_block_pilot_candidate_v4"
    )
    config = controller._load_config()

    class Process:
        pid = 123456

    envelope = controller._build_envelope(
        config=config,
        process=Process(),
        child_create_ns=987654321,
        execution_index=1,
        mode="review_only_preloader_stop",
        ledger=None,
        authority=None,
        read_handle=101,
        ack_handle=202,
    )
    result = v4._build_worker_result(envelope, {"all_hours_resolved": True})
    ack = v4._build_ack(envelope)
    assert result["parent_process_identity"] == envelope["parent_process_identity"]
    assert result["worker_process_identity"] == envelope["worker_process_identity"]
    assert ack["worker_process_identity"] == envelope["worker_process_identity"]
    assert result["all_hours_resolved"] is True


def test_v5_dual_monitor_and_preflight_are_mandatory_in_production_source(controller) -> None:
    source = Path(controller.__file__).read_text(encoding="utf-8")
    assert "resource_authority.preflight_available_commit(" in source
    assert "resource_authority.monitor_owned_child_resources(" in source
    config = controller._load_config()
    resources = config["resources"]
    assert resources["sample_interval_seconds"] == 5.0
    assert resources["child_private_commit_stop_gib"] == 8.0
    assert resources["child_private_commit_stop_comparison"] == "greater_than_or_equal"
    assert resources["system_commit_available_stop_gib"] == 2.0
    assert resources["system_commit_available_stop_comparison"] == "less_than_or_equal"
    assert resources["preflight_available_commit_gib"] == 10.0


def test_validate_only_and_arbitrary_argv_are_closed(controller, capsys) -> None:
    assert controller.main(["--validate-only"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["execution_review_present"] is False
    assert value["execution_ready"] is False
    assert value["project_science_imports"] == 0
    assert value["production_workers"] == 0
    assert value["loader_calls"] == 0
    assert value["solver_calls"] == 0
    assert value["result_writes"] == 0
    assert value["formal_writes"] == 0
    with pytest.raises(controller.SuccessorRejected, match="argv"):
        controller.main(["--execute", "--receipt", "forged.json"])


def test_no_successor_roots_or_review_receipt_exist(controller) -> None:
    config = controller._load_config()
    assert not controller.EXECUTION_REVIEW_RECEIPT.exists()
    for relative in config["paths"].values():
        assert not os.path.lexists(ROOT / relative)


class _FakeToolhelp:
    def __init__(self, rows, *, first_ok=True, terminal_error=18):
        self.rows = list(rows)
        self.first_ok = first_ok
        self.terminal_error = terminal_error
        self.index = 0
        self.closed = False

    def create_snapshot(self):
        return object()

    def _write(self, entry, row):
        entry.th32ProcessID = row[0]
        entry.szExeFile = row[1]

    def first(self, _snapshot, entry):
        if not self.first_ok or not self.rows:
            return False
        self._write(entry, self.rows[0])
        return True

    def next(self, _snapshot, entry):
        self.index += 1
        if self.index >= len(self.rows):
            return False
        self._write(entry, self.rows[self.index])
        return True

    def last_error(self):
        return self.terminal_error

    def close(self, _snapshot):
        self.closed = True


def test_bootstrap_toolhelp_distinguishes_first_mid_error_and_normal_eof(
    bootstrap,
) -> None:
    normal = _FakeToolhelp([(os.getpid(), "python.exe")])
    assert bootstrap._windows_processes(normal) == [(os.getpid(), "python.exe")]
    assert normal.closed is True
    first = _FakeToolhelp([], first_ok=False)
    with pytest.raises(bootstrap.BootstrapRejected, match="Process32FirstW"):
        bootstrap._windows_processes(first)
    assert first.closed is True
    mid = _FakeToolhelp([(os.getpid(), "python.exe")], terminal_error=5)
    with pytest.raises(bootstrap.BootstrapRejected, match="error 5"):
        bootstrap._windows_processes(mid)
    assert mid.closed is True
    missing = _FakeToolhelp([(999999, "python.exe")])
    with pytest.raises(bootstrap.BootstrapRejected, match="omits current PID"):
        bootstrap._windows_processes(missing)


def test_bootstrap_strict_absence_permission_error_is_indeterminate(
    bootstrap, monkeypatch: pytest.MonkeyPatch
) -> None:
    def inaccessible(_path):
        raise PermissionError("denied")

    monkeypatch.setattr(bootstrap.os, "lstat", inaccessible)
    with pytest.raises(bootstrap.BootstrapRejected, match="presence is indeterminate"):
        bootstrap._strict_absent(ROOT / "results/tables/future-successor-root")


def test_bootstrap_checkpoint_inventory_rejects_extra_directory(
    bootstrap, tmp_path: Path
) -> None:
    expected = {}
    for index in range(9):
        path = tmp_path / f"holdout_{index:04d}.json"
        path.write_bytes(f"{index}\n".encode())
        expected[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (tmp_path / "extra-empty-directory").mkdir()
    with pytest.raises(bootstrap.BootstrapRejected, match="not ordinary"):
        bootstrap._audit_checkpoint_inventory(tmp_path, expected)
