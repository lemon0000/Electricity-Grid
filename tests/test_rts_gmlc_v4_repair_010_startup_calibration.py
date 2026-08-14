from __future__ import annotations

import json
import os
import sys
import textwrap
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import casadi as ca
import numpy as np
import pytest

from experiments import (
    run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_010_formal as formal,
)
from src.grid import rts_gmlc_ac_aware_commitment as core
from src.grid import rts_gmlc_ac_ipopt as shared_ipopt
from src.grid import (
    rts_gmlc_ac_aware_commitment_v4_repair_010_adapter as adapter,
)
from src.solvers.execution_lease import ExecutionLease, ExecutionLeaseUnavailable
from src.solvers.joint_ac_phase_contract import (
    CALIBRATION_REQUIRED_PHASES,
    load_verified_calibration_events,
)


def _hash(character: str) -> str:
    return character * 64


def _binding() -> dict[str, object]:
    return {
        "schema": "rts_gmlc_v4_repair_010_startup_calibration_binding_v1",
        "calibration_id": "tiny_calibration",
        "ipopt_options_sha256": _hash("b"),
        "software_identity": {"test": "tiny"},
    }


def _tiny_contract() -> dict[str, object]:
    contract = deepcopy(formal._read_config()["startup_calibration"])
    contract.update(
        {
            "calibration_max_wall_seconds": 5.0,
            "parent_poll_interval_seconds": 0.005,
            "post_stop_worker_exit_limit_seconds": 1.0,
            "termination_grace_seconds": 0.5,
        }
    )
    return contract


def _tiny_worker_script(tmp_path: Path) -> Path:
    script = tmp_path / "tiny_calibration_worker.py"
    script.write_text(
        textwrap.dedent("""
            import hashlib
            import json
            import os
            import sys
            from pathlib import Path

            sys.path.insert(0, sys.argv[3])
            from src.solvers.joint_ac_phase_contract import (
                DurablePhaseJournal,
                expression_fingerprint_sha256,
                solver_input_fingerprint_sha256,
            )

            registration_root = Path(sys.argv[1])
            mode = sys.argv[2]
            registration = json.loads(
                (registration_root / "calibration_registration.json").read_text()
            )
            binding = registration["binding"]
            journal = DurablePhaseJournal(
                Path(registration["phase_journal"]), binding=binding
            )
            journal.emit("worker_started")
            journal.emit("context_load_started")
            if mode == "fail_before_stop":
                raise SystemExit(7)
            journal.emit("context_load_completed")
            journal.emit("prepared_cases_completed")
            build = {
                "schema": "rts_gmlc_ac_aware_nlp_expression_fingerprint_v1",
                "variable_count": 2,
                "constraint_count": 1,
                "variable_order_sha256": "c" * 64,
                "objective_expression_sha256": "d" * 64,
                "constraint_order_and_expression_sha256": "e" * 64,
                "prepared_inputs_sha256": "a" * 64,
                "ipopt_options_sha256": binding["ipopt_options_sha256"],
            }
            build["expression_fingerprint_sha256"] = (
                expression_fingerprint_sha256(build)
            )
            journal.emit(
                "nlp_build_started",
                {
                    "prepared_inputs_sha256": build["prepared_inputs_sha256"],
                    "ipopt_options_sha256": build["ipopt_options_sha256"],
                },
            )
            journal.emit("nlp_build_completed", build)
            solve = {
                **build,
                "initial_point_sha256": "f" * 64,
                "variable_lower_sha256": "0" * 64,
                "variable_upper_sha256": "1" * 64,
                "constraint_lower_sha256": "2" * 64,
                "constraint_upper_sha256": "3" * 64,
            }
            solve["solver_input_fingerprint_sha256"] = (
                solver_input_fingerprint_sha256(solve)
            )
            journal.emit("calibration_pre_solver_stop", solve)
            result = Path(registration["worker_result"])
            result.mkdir()
            value = (str(os.getpid()) + "\\n").encode("ascii")
            (result / "pid.txt").write_bytes(value)
            digest = hashlib.sha256(value).hexdigest()
            (result / "SHA256SUMS").write_text(
                f"{digest}  pid.txt\\n", encoding="ascii"
            )
            """),
        encoding="utf-8",
    )
    return script


def _registered_tiny_calibration(
    tmp_path: Path,
) -> tuple[dict[str, object], Path, Path, Path, Path, Path]:
    binding = _binding()
    contract_root = tmp_path / "contract"
    registration = tmp_path / "registration"
    spawn = tmp_path / "spawn"
    journal = tmp_path / "logs" / "phase.jsonl"
    result = tmp_path / "result"
    process_log = tmp_path / "logs" / "worker.log"
    formal._publish_exact_artifact(
        contract_root,
        "contract.json",
        {"schema": "tiny_calibration_contract_v1"},
    )
    formal.register_startup_calibration(
        registration,
        binding=binding,
        contract_directory=contract_root,
        phase_journal=journal,
        worker_result=result,
        native_solver_log=tmp_path / "logs" / "native.log",
        worker_process_log=process_log,
        parent_pid=os.getpid(),
    )
    return binding, registration, spawn, journal, result, process_log


def _completed_tiny_sample(
    tmp_path: Path,
) -> tuple[
    formal.StartupCalibrationCompletion,
    dict[str, object],
    Path,
    Path,
    Path,
    Path,
    dict[str, object],
]:
    binding, registration, spawn, journal, result, process_log = (
        _registered_tiny_calibration(tmp_path)
    )
    contract = _tiny_contract()
    completion = formal.run_startup_calibration_process(
        command=(
            sys.executable,
            str(_tiny_worker_script(tmp_path)),
            str(registration),
            "success",
            str(Path.cwd()),
        ),
        registration_directory=registration,
        spawn_directory=spawn,
        phase_journal=journal,
        expected_binding=binding,
        worker_process_log=process_log,
        result_validator=lambda: int((result / "pid.txt").read_text(encoding="ascii")),
        calibration_contract=contract,
        on_incomplete=lambda reason: pytest.fail(reason),
    )
    return completion, binding, registration, spawn, journal, result, contract


def test_calibration_adapter_constructs_nlpsol_but_never_calls_solver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = SimpleNamespace(
        mode="distributed_committable",
        fixed_inputs_preserved=True,
        active_power_envelope="physical_envelope_no_response_time",
        source_case_sha256=_hash("1"),
        recovery_case_sha256=_hash("2"),
        case={
            "bus": np.array([[1.0, 3.0]]),
            "gen": np.array([[1.0, 2.0]]),
            "branch": np.array([[1.0, 2.0]]),
            "gencost": np.array([[2.0, 0.0]]),
        },
        target_generation_mw_by_row=(1.0,),
        generator_uid_by_row=("g1",),
        branch_uid_by_row=("b1",),
        adjustable_generator_rows=(0,),
        fixed_generator_rows=(),
        reference_generator_row=0,
        reference_generator_uid="g1",
        reference_bus=1,
        source_controller_vg_by_bus=((1, 1.0),),
    )
    unit = SimpleNamespace(
        generator_uid="g1",
        area=1,
        p_max_mw=2.0,
        ramp_mw_per_hour=1.0,
        ramp_mw_per_minute=1.0,
        reserve_eligible=True,
        initial_generation_mw=1.0,
        initial_commitment=True,
        commitment_by_hour=(True,),
        startup_by_hour=(False,),
        shutdown_by_hour=(False,),
    )
    chronology = SimpleNamespace(
        timestamps=(datetime(2020, 1, 1, tzinfo=UTC),),
        time_step_hours=1.0,
        units=(unit,),
        spin_up_requirement_by_hour_area_mw=({1: 0.0},),
    )
    calls = {"factory": 0, "solver": 0}

    class FakeSolver:
        def __call__(self, **_kwargs: object) -> object:
            calls["solver"] += 1
            return {}

        def stats(self) -> dict[str, object]:
            return {"success": True}

    def fake_factory(*_args: object, **_kwargs: object) -> FakeSolver:
        calls["factory"] += 1
        return FakeSolver()

    def fake_core_solve(
        _cases: object,
        _chronology: object,
        *,
        initial_strategy: str,
        solver_options: dict[str, object],
    ) -> object:
        x = ca.MX.sym("x", 1)
        solver = core.ca.nlpsol(
            "ac_aware_commitment",
            "ipopt",
            {"x": x, "f": x**2, "g": x},
            solver_options,
        )
        return solver(
            x0=np.array([0.0]),
            lbx=np.array([-1.0]),
            ubx=np.array([1.0]),
            lbg=np.array([0.0]),
            ubg=np.array([0.0]),
        )

    monkeypatch.setattr(core.ca, "nlpsol", fake_factory)
    monkeypatch.setattr(core, "solve_ac_aware_commitment", fake_core_solve)
    events: list[str] = []
    original_options = core._FROZEN_IPOPT_OPTIONS

    fingerprint = adapter.calibrate_ac_aware_commitment_v4_startup(
        (prepared,),
        chronology,
        base_options=shared_ipopt._FROZEN_IPOPT_OPTIONS,
        runtime_options={},
        phase_observer=lambda event, _payload: events.append(event),
    )

    assert calls == {"factory": 1, "solver": 0}
    assert events == [
        "nlp_build_started",
        "nlp_build_completed",
        "calibration_pre_solver_stop",
    ]
    assert len(fingerprint["solver_input_fingerprint_sha256"]) == 64
    assert core._FROZEN_IPOPT_OPTIONS is original_options
    assert core.ca.nlpsol is fake_factory


def test_single_sample_rule_is_frozen_deterministic_and_non_statistical() -> None:
    contract = formal._read_config()["startup_calibration"]

    assert contract["sample_count"] == 1
    assert contract["startup_limit_multiplier"] == 2.0
    assert contract["startup_limit_round_up_seconds"] == 300.0
    assert contract["statistical_tail_guarantee"] is False
    assert formal.derive_startup_limit_seconds(18_001.0, contract) == 36_300.0
    assert formal.derive_startup_limit_seconds(18_001.0, contract) == 36_300.0


def test_parent_timing_samples_bracket_popen_and_complete_phase_validation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    contract = _tiny_contract()
    binding, registration, spawn, journal, _result, process_log = (
        _registered_tiny_calibration(tmp_path)
    )
    order: list[str] = []
    clock_value = [10.0]

    class FakeProcess:
        pid = 43210

        def poll(self) -> int:
            order.append("poll")
            return 0

        def terminate(self) -> None:
            pytest.fail("completed fake process must not be terminated")

    def clock() -> float:
        order.append(f"clock:{clock_value[0]}")
        return clock_value[0]

    def popen(*_args: object, **_kwargs: object) -> FakeProcess:
        order.append("popen")
        return FakeProcess()

    def validate(*_args: object, **_kwargs: object) -> tuple[dict[str, str], ...]:
        order.append("validation_started")
        clock_value[0] = 16.0
        order.append("validation_completed")
        return tuple({"event": event} for event in CALIBRATION_REQUIRED_PHASES)

    monkeypatch.setattr(formal.time, "monotonic", clock)
    monkeypatch.setattr(formal.subprocess, "Popen", popen)
    monkeypatch.setattr(formal, "load_verified_calibration_events", validate)

    contract["calibration_max_wall_seconds"] = 10.0
    completion = formal.run_startup_calibration_process(
        command=("unused",),
        registration_directory=registration,
        spawn_directory=spawn,
        phase_journal=journal,
        expected_binding=binding,
        worker_process_log=process_log,
        result_validator=lambda: order.append("result_validated"),
        calibration_contract=contract,
        on_incomplete=lambda reason: pytest.fail(reason),
    )

    assert order[:5] == [
        "clock:10.0",
        "popen",
        "validation_started",
        "validation_completed",
        "clock:16.0",
    ]
    assert completion.observed_startup_elapsed_seconds == 6.0
    assert order.index("clock:16.0") < order.index("result_validated")


def test_tiny_fresh_parent_child_calibration_publishes_zero_call_receipt(
    tmp_path: Path,
) -> None:
    contract = _tiny_contract()
    binding, registration, spawn, journal, result, process_log = (
        _registered_tiny_calibration(tmp_path)
    )
    completion = formal.run_startup_calibration_process(
        command=(
            sys.executable,
            str(_tiny_worker_script(tmp_path)),
            str(registration),
            "success",
            str(Path.cwd()),
        ),
        registration_directory=registration,
        spawn_directory=spawn,
        phase_journal=journal,
        expected_binding=binding,
        worker_process_log=process_log,
        result_validator=lambda: int((result / "pid.txt").read_text(encoding="ascii")),
        calibration_contract=contract,
        on_incomplete=lambda reason: pytest.fail(reason),
    )
    completion_root = tmp_path / "completion"
    formal.register_startup_calibration_completion(
        completion_root,
        incomplete_directory=tmp_path / "incomplete",
        binding=binding,
        registration_directory=registration,
        spawn_directory=spawn,
        phase_journal=journal,
        worker_result=result,
        observed_startup_elapsed_seconds=(completion.observed_startup_elapsed_seconds),
        calibration_contract=contract,
    )

    events = load_verified_calibration_events(
        journal,
        expected_binding=binding,
        expected_worker_pid=completion.worker_pid,
    )
    receipt = formal.v4._load_json(completion_root, "calibration_completion.json")
    assert completion.result == completion.worker_pid
    assert completion.worker_pid != os.getpid()
    assert tuple(event["event"] for event in events) == CALIBRATION_REQUIRED_PHASES
    assert not any(event["event"] == "solver_started" for event in events)
    assert receipt["solver_callable_invocation_count"] == 0
    assert receipt["solver_call_count"] == 0
    assert receipt["is_infeasibility_evidence"] is False
    assert receipt["resume_allowed"] is False


def test_completion_postrename_exception_reconciles_to_only_committed_truth(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    completion, binding, registration, spawn, journal, result, contract = (
        _completed_tiny_sample(tmp_path)
    )
    completion_root = tmp_path / "completion"
    incomplete_root = tmp_path / "incomplete"
    original_publish = formal.v4._publish_immutable_payload

    def publish_then_raise(target: Path, writer: object) -> None:
        original_publish(target, writer)
        if target == completion_root:
            raise OSError("injected after atomic rename")

    monkeypatch.setattr(formal.v4, "_publish_immutable_payload", publish_then_raise)
    receipt = formal.finalize_startup_calibration(
        completion=completion,
        completion_directory=completion_root,
        incomplete_directory=incomplete_root,
        binding=binding,
        registration_directory=registration,
        spawn_directory=spawn,
        phase_journal=journal,
        worker_result=result,
        calibration_contract=contract,
        persist_incomplete=lambda reason: pytest.fail(reason),
    )

    assert receipt["solver_call_count"] == 0
    assert completion_root.is_dir()
    assert not incomplete_root.exists()


def test_completion_precommit_failure_persists_only_incomplete(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    completion, binding, registration, spawn, journal, result, contract = (
        _completed_tiny_sample(tmp_path)
    )
    completion_root = tmp_path / "completion"
    incomplete_root = tmp_path / "incomplete"
    original_publish = formal.v4._publish_immutable_payload

    def fail_before_completion_rename(target: Path, writer: object) -> None:
        if target == completion_root:
            raise OSError("injected before atomic rename")
        original_publish(target, writer)

    def persist(reason: str) -> None:
        formal.register_startup_calibration_incomplete(
            incomplete_root,
            completion_directory=completion_root,
            binding=binding,
            registration_directory=registration,
            spawn_directory=spawn,
            phase_journal=journal,
            reason=reason,
        )

    monkeypatch.setattr(
        formal.v4, "_publish_immutable_payload", fail_before_completion_rename
    )
    with pytest.raises(formal.StartupCalibrationIncompleteError):
        formal.finalize_startup_calibration(
            completion=completion,
            completion_directory=completion_root,
            incomplete_directory=incomplete_root,
            binding=binding,
            registration_directory=registration,
            spawn_directory=spawn,
            phase_journal=journal,
            worker_result=result,
            calibration_contract=contract,
            persist_incomplete=persist,
        )

    assert not completion_root.exists()
    assert incomplete_root.is_dir()


def test_completion_indeterminate_or_coexisting_state_is_permanently_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    completion, binding, registration, spawn, journal, result, contract = (
        _completed_tiny_sample(tmp_path)
    )
    completion_root = tmp_path / "completion"
    incomplete_root = tmp_path / "incomplete"
    original_publish = formal.v4._publish_immutable_payload

    def leave_unprovable_target(target: Path, writer: object) -> None:
        if target == completion_root:
            target.mkdir()
            (target / "uncommitted.txt").write_text("drift", encoding="ascii")
            raise OSError("injected indeterminate commit")
        original_publish(target, writer)

    monkeypatch.setattr(
        formal.v4, "_publish_immutable_payload", leave_unprovable_target
    )
    kwargs = {
        "completion": completion,
        "completion_directory": completion_root,
        "incomplete_directory": incomplete_root,
        "binding": binding,
        "registration_directory": registration,
        "spawn_directory": spawn,
        "phase_journal": journal,
        "worker_result": result,
        "calibration_contract": contract,
        "persist_incomplete": lambda reason: pytest.fail(reason),
    }
    with pytest.raises(formal.StartupCalibrationCompletionCommitIndeterminateError):
        formal.finalize_startup_calibration(**kwargs)
    assert completion_root.exists()
    assert not incomplete_root.exists()

    with pytest.raises(formal.StartupCalibrationCompletionCommitIndeterminateError):
        formal.finalize_startup_calibration(**kwargs)
    formal._publish_exact_artifact(
        incomplete_root,
        "calibration_incomplete.json",
        {"schema": "injected_coexisting_incomplete"},
    )
    with pytest.raises(
        formal.StartupCalibrationCompletionCommitIndeterminateError,
        match="coexist",
    ):
        formal.load_verified_startup_calibration_completion(
            completion_root,
            incomplete_directory=incomplete_root,
            binding=binding,
            registration_directory=registration,
            spawn_directory=spawn,
            phase_journal=journal,
            worker_result=result,
            calibration_contract=contract,
        )


def test_pre_solver_calibration_failure_persists_honest_incomplete(
    tmp_path: Path,
) -> None:
    binding, registration, spawn, journal, _result, process_log = (
        _registered_tiny_calibration(tmp_path)
    )
    incomplete = tmp_path / "incomplete"

    def persist(reason: str) -> None:
        formal.register_startup_calibration_incomplete(
            incomplete,
            completion_directory=tmp_path / "completion",
            binding=binding,
            registration_directory=registration,
            spawn_directory=spawn,
            phase_journal=journal,
            reason=reason,
        )

    with pytest.raises(formal.StartupCalibrationIncompleteError) as caught:
        formal.run_startup_calibration_process(
            command=(
                sys.executable,
                str(_tiny_worker_script(tmp_path)),
                str(registration),
                "fail_before_stop",
                str(Path.cwd()),
            ),
            registration_directory=registration,
            spawn_directory=spawn,
            phase_journal=journal,
            expected_binding=binding,
            worker_process_log=process_log,
            result_validator=lambda: pytest.fail("failed worker has no result"),
            calibration_contract=_tiny_contract(),
            on_incomplete=persist,
        )

    receipt = formal.v4._load_json(incomplete, "calibration_incomplete.json")
    assert caught.value.solver_call_count == 0
    assert receipt["solver_call_count"] == 0
    assert receipt["is_infeasibility_evidence"] is False
    assert receipt["resume_allowed"] is False


def test_duplicate_or_active_calibration_root_fails_before_audit_or_spawn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = deepcopy(formal._read_config())
    output = tmp_path / "calibration"
    logs = tmp_path / "logs"
    config["startup_calibration"]["output_directory"] = str(output)
    config["startup_calibration"]["logging_directory"] = str(logs)
    audit_calls: list[str] = []
    monkeypatch.setattr(formal, "_read_config", lambda *_args: config)
    monkeypatch.setattr(
        formal,
        "audit_configured_predecessor_frontier_source",
        lambda *_args: audit_calls.append("called"),
    )
    with ExecutionLease.acquire(
        output / "execution_lease",
        stage="repair010_startup_calibration",
        attempt_id="active",
    ):
        with pytest.raises(FileExistsError, match="retry/resume forbidden"):
            formal.run_startup_calibration()
        with pytest.raises(ExecutionLeaseUnavailable):
            ExecutionLease.acquire(
                output / "execution_lease",
                stage="repair010_startup_calibration",
                attempt_id="duplicate",
            )
    assert audit_calls == []


def test_formal_readiness_stays_closed_while_calibration_is_allowed() -> None:
    config = formal._read_config()

    formal._assert_startup_calibration_only(config)
    with pytest.raises(formal.SuccessorNotReadyError):
        formal._assert_successor_ready(config)
    assert config["joint_ac_successor"]["startup_limit_seconds"] is None
    assert config["joint_ac_successor"]["formal_execution_ready"] is False
    assert (
        config["preregistration"]["status"]
        == "blocked_before_repository_local_preregistration"
    )


def test_calibration_cli_dispatches_only_explicit_stage(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    observed: list[Path] = []
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "repair010",
            "--stage",
            "calibrate-startup",
            "--config",
            str(formal.DEFAULT_CONFIG_PATH),
        ],
    )
    monkeypatch.setattr(
        formal,
        "run_startup_calibration",
        lambda path, **_kwargs: observed.append(path) or {"schema": "tiny_calibration"},
    )

    formal.main()

    assert observed == [formal.DEFAULT_CONFIG_PATH]
    assert json.loads(capsys.readouterr().out)["schema"] == "tiny_calibration"


def test_launcher_postspawn_receipt_failure_stops_only_child_and_persists_failed(
    tmp_path: Path,
) -> None:
    launcher = tmp_path / "launcher"
    request = launcher / "request"
    pid_receipt = launcher / "pid"
    failed = launcher / "failed"
    formal._publish_exact_artifact(
        request, "launcher_request.json", {"schema": "tiny_request"}
    )
    request_manifest = formal._sha256(request / "SHA256SUMS")

    def publish_pid(pid: int) -> None:
        formal._publish_exact_artifact(
            pid_receipt,
            "launcher_pid.json",
            {
                "schema": "tiny_launcher_pid",
                "request_manifest_sha256": request_manifest,
                "pid": pid,
            },
        )

    def publish_failed(pid: int, return_code: int, reason: str) -> None:
        formal._publish_exact_artifact(
            failed,
            "launcher_failed.json",
            {
                "schema": "tiny_launcher_failed",
                "request_manifest_sha256": request_manifest,
                "pid_manifest_sha256": formal._sha256(pid_receipt / "SHA256SUMS"),
                "pid": pid,
                "return_code": return_code,
                "reason": reason,
                "child_exit_confirmed": True,
                "retry_or_resume_allowed": False,
            },
        )

    with pytest.raises(formal.StartupCalibrationLauncherFailedError) as caught:
        formal.run_startup_calibration_launcher_process(
            command=(sys.executable, "-c", "import time; time.sleep(60)"),
            stdout_path=launcher / "stdout.log",
            stderr_path=launcher / "stderr.log",
            termination_grace_seconds=2.0,
            on_pid=publish_pid,
            on_started=lambda _pid: (_ for _ in ()).throw(
                OSError("injected started publication failure")
            ),
            on_failed=publish_failed,
        )

    receipt = formal.v4._load_json(failed, "launcher_failed.json")
    assert caught.value.child_exit_confirmed is True
    assert formal.v4._load_json(pid_receipt, "launcher_pid.json")["pid"] == (
        caught.value.worker_pid
    )
    assert receipt["pid"] == caught.value.worker_pid
    assert receipt["child_exit_confirmed"] is True
    assert receipt["retry_or_resume_allowed"] is False
    with pytest.raises(formal.StartupCalibrationNoResumeError):
        formal._publish_launcher_artifact(
            request, filename="launcher_request.json", payload={"schema": "retry"}
        )


def test_direct_calibration_rejects_existing_launcher_before_audit_or_spawn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = deepcopy(formal._read_config())
    config["startup_calibration"]["output_directory"] = str(tmp_path / "output")
    config["startup_calibration"]["logging_directory"] = str(tmp_path / "logs")
    launcher = tmp_path / "launcher"
    config["startup_calibration"]["launcher_directory"] = str(launcher)
    launcher.mkdir()
    audit_calls: list[str] = []
    monkeypatch.setattr(formal, "_read_config", lambda *_args: config)
    monkeypatch.setattr(
        formal,
        "audit_configured_predecessor_frontier_source",
        lambda *_args: audit_calls.append("called"),
    )

    with pytest.raises(formal.StartupCalibrationNoResumeError):
        formal.run_startup_calibration()
    assert audit_calls == []


def test_windows_launcher_is_thin_runner_entry_and_root_isolated() -> None:
    config = formal._read_config()
    contract = config["startup_calibration"]
    calibration_output = Path(contract["output_directory"])
    calibration_logs = Path(contract["logging_directory"])
    launcher_root = Path(contract["launcher_directory"])
    formal_output = Path(config["output"]["directory"])
    formal_logs = Path(config["logging"]["directory"])

    assert calibration_output != formal_output
    assert calibration_logs != formal_logs
    assert not calibration_output.exists()
    assert not calibration_logs.exists()
    assert not launcher_root.exists()

    launcher = Path(
        "scripts/start_rts_gmlc_v4_repair_010_startup_calibration.ps1"
    ).read_text(encoding="utf-8")
    assert "--stage launch-startup-calibration" in launcher
    assert "Start-Process" not in launcher
    assert not calibration_output.exists()
    assert not calibration_logs.exists()
    assert not launcher_root.exists()
