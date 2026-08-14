from __future__ import annotations

import json
import os
import re
import sys
import textwrap
import time
from copy import deepcopy
from collections.abc import Mapping
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
from src.grid import rts_gmlc_ac_aware_commitment_v4_adapter as shared_adapter
from src.grid import (
    rts_gmlc_ac_aware_commitment_v4_repair_010_adapter as dedicated_adapter,
)
from src.grid.rts_gmlc_ac_aware_commitment_v4_repair_010_adapter import (
    prepared_inputs_sha256,
    solve_ac_aware_commitment_v4_worker,
)
from src.solvers.joint_ac_phase_contract import (
    DurablePhaseJournal,
    PhaseContractError,
    PhaseTimingController,
    expression_fingerprint_sha256,
    classify_phase_contract_failure,
    load_verified_phase_events,
    solver_input_fingerprint_sha256,
)


def _hash(character: str) -> str:
    return character * 64


def _binding() -> dict[str, object]:
    return formal.build_worker_binding(
        preregistration_id="repair010",
        input_contract_sha256=_hash("1"),
        frontier_manifest_sha256=_hash("2"),
        call_manifest_sha256=_hash("3"),
        candidate_id="candidate_00",
        commitment_sha256=_hash("4"),
        dispatch_sha256=_hash("5"),
        initial_strategy="source",
        prepared_inputs_sha256=_hash("a"),
        ipopt_options_sha256=_hash("b"),
        software_identity={"test": "synthetic"},
    )


def _fingerprints() -> tuple[dict[str, object], dict[str, object]]:
    build = {
        "schema": "rts_gmlc_ac_aware_nlp_expression_fingerprint_v1",
        "variable_count": 2,
        "constraint_count": 1,
        "variable_order_sha256": _hash("c"),
        "objective_expression_sha256": _hash("d"),
        "constraint_order_and_expression_sha256": _hash("e"),
        "prepared_inputs_sha256": _hash("a"),
        "ipopt_options_sha256": _hash("b"),
    }
    build["expression_fingerprint_sha256"] = expression_fingerprint_sha256(build)
    solve = {
        **build,
        "initial_point_sha256": _hash("f"),
        "variable_lower_sha256": _hash("0"),
        "variable_upper_sha256": _hash("1"),
        "constraint_lower_sha256": _hash("2"),
        "constraint_upper_sha256": _hash("3"),
    }
    solve["solver_input_fingerprint_sha256"] = solver_input_fingerprint_sha256(solve)
    return build, solve


def _emit_through_solver_started(journal: DurablePhaseJournal) -> None:
    build, solve = _fingerprints()
    journal.emit("worker_started")
    journal.emit("context_load_started")
    journal.emit("context_load_completed")
    journal.emit("prepared_cases_completed")
    journal.emit(
        "nlp_build_started",
        {
            "prepared_inputs_sha256": build["prepared_inputs_sha256"],
            "ipopt_options_sha256": build["ipopt_options_sha256"],
        },
    )
    journal.emit("nlp_build_completed", build)
    journal.emit("solver_started", solve)


def _tiny_worker_script(tmp_path: Path) -> Path:
    script = tmp_path / "tiny_phase_worker.py"
    script.write_text(
        textwrap.dedent("""
            import json
            import os
            import sys
            import time
            from pathlib import Path

            sys.path.insert(0, sys.argv[3])
            from src.solvers.joint_ac_phase_contract import (
                DurablePhaseJournal,
                expression_fingerprint_sha256,
                solver_input_fingerprint_sha256,
            )

            registration = json.loads(
                (Path(sys.argv[1]) / "phase_call.json").read_text(encoding="utf-8")
            )
            binding = registration["binding"]
            journal = DurablePhaseJournal(
                Path(registration["phase_journal"]), binding=binding
            )
            mode = sys.argv[2]
            journal.emit("worker_started")
            journal.emit("context_load_started")
            if mode == "startup_timeout":
                time.sleep(5.0)
                raise SystemExit(9)
            time.sleep(0.12)
            journal.emit("context_load_completed")
            journal.emit("prepared_cases_completed")
            build = {
                "schema": "rts_gmlc_ac_aware_nlp_expression_fingerprint_v1",
                "variable_count": 2,
                "constraint_count": 1,
                "variable_order_sha256": "c" * 64,
                "objective_expression_sha256": "d" * 64,
                "constraint_order_and_expression_sha256": "e" * 64,
                "prepared_inputs_sha256": binding["prepared_inputs_sha256"],
                "ipopt_options_sha256": binding["ipopt_options_sha256"],
            }
            build["expression_fingerprint_sha256"] = (
                expression_fingerprint_sha256(build)
            )
            journal.emit(
                "nlp_build_started",
                {
                    "prepared_inputs_sha256": binding["prepared_inputs_sha256"],
                    "ipopt_options_sha256": binding["ipopt_options_sha256"],
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
            journal.emit("solver_started", solve)
            if mode == "solver_timeout":
                time.sleep(5.0)
                raise SystemExit(8)
            time.sleep(0.02)
            journal.emit("solver_finished", {**solve, "termination": "returned"})
            Path(registration["worker_result"]).write_text(
                str(os.getpid()), encoding="ascii"
            )
            """),
        encoding="utf-8",
    )
    return script


def _registered_tiny_call(
    tmp_path: Path,
) -> tuple[dict[str, object], Path, Path, Path]:
    binding = _binding()
    phase_journal = tmp_path / "phase.jsonl"
    worker_result = tmp_path / "worker_result.txt"
    process_log = tmp_path / "worker.log"
    registration = tmp_path / "phase_registration"
    manifest = formal.register_phase_worker_call(
        registration,
        binding=binding,
        phase_journal=phase_journal,
        worker_result=worker_result,
        native_solver_log=tmp_path / "native.log",
        worker_process_log=process_log,
        parent_pid=os.getpid(),
    )
    assert len(manifest) == 64
    return binding, registration, phase_journal, process_log


def test_startup_time_does_not_consume_solver_wall(tmp_path: Path) -> None:
    path = tmp_path / "phases.jsonl"
    binding = _binding()
    journal = DurablePhaseJournal(path, binding=binding)
    _emit_through_solver_started(journal)
    controller = PhaseTimingController(
        startup_started_monotonic=0.0,
        startup_limit_seconds=100.0,
        solver_wall_limit_seconds=7500.0,
    )

    state = controller.observe(
        path,
        expected_binding=binding,
        expected_worker_pid=os.getpid(),
        observed_monotonic=99.0,
    )

    assert state.solver_started_verified
    assert state.solver_deadline_monotonic == 7599.0
    assert controller.timeout(observed_monotonic=7598.999) is None
    timeout = controller.timeout(observed_monotonic=7599.0)
    assert timeout is not None
    assert timeout.reason == "solver_wall_timeout_after_verified_solver_started"
    assert timeout.solver_call_count == 1
    assert not timeout.is_infeasibility_evidence


def test_startup_timeout_before_solver_started_is_zero_call_incomplete() -> None:
    controller = PhaseTimingController(
        startup_started_monotonic=10.0,
        startup_limit_seconds=90.0,
        solver_wall_limit_seconds=7500.0,
    )

    timeout = controller.timeout(observed_monotonic=100.0)

    assert timeout is not None
    assert timeout.reason == "startup_timeout_before_verified_solver_started"
    assert timeout.solver_call_count == 0
    assert not timeout.is_infeasibility_evidence
    assert not timeout.resume_allowed


def test_fresh_parent_child_phase_orchestration_completes(tmp_path: Path) -> None:
    binding, registration, phase_journal, process_log = _registered_tiny_call(tmp_path)
    worker_result = tmp_path / "worker_result.txt"

    started = time.monotonic()
    completion = formal.run_isolated_worker_process(
        command=(
            sys.executable,
            str(_tiny_worker_script(tmp_path)),
            str(registration),
            "success",
            str(Path.cwd()),
        ),
        phase_journal=phase_journal,
        expected_binding=binding,
        worker_process_log=process_log,
        result_validator=lambda: int(worker_result.read_text(encoding="ascii")),
        startup_limit_seconds=5.0,
        solver_wall_limit_seconds=1.0,
        termination_grace_seconds=0.5,
        poll_interval_seconds=0.005,
    )

    assert time.monotonic() - started > 0.2
    assert completion.worker_pid != os.getpid()
    assert completion.result == completion.worker_pid
    assert completion.solver_call_count == 1
    assert process_log.is_file()


@pytest.mark.parametrize(
    ("mode", "startup_limit", "solver_limit", "expected_count", "reason"),
    (
        (
            "startup_timeout",
            0.08,
            1.0,
            0,
            "startup_timeout_before_verified_solver_started",
        ),
        (
            "solver_timeout",
            5.0,
            0.05,
            1,
            "solver_wall_timeout_after_verified_solver_started",
        ),
    ),
)
def test_parent_child_timeouts_are_honest_incomplete(
    tmp_path: Path,
    mode: str,
    startup_limit: float,
    solver_limit: float,
    expected_count: int,
    reason: str,
) -> None:
    binding, registration, phase_journal, process_log = _registered_tiny_call(tmp_path)
    persisted = []

    with pytest.raises(formal.IsolatedWorkerIncompleteError) as captured:
        formal.run_isolated_worker_process(
            command=(
                sys.executable,
                str(_tiny_worker_script(tmp_path)),
                str(registration),
                mode,
                str(Path.cwd()),
            ),
            phase_journal=phase_journal,
            expected_binding=binding,
            worker_process_log=process_log,
            result_validator=lambda: pytest.fail("incomplete worker has no result"),
            startup_limit_seconds=startup_limit,
            solver_wall_limit_seconds=solver_limit,
            termination_grace_seconds=0.5,
            poll_interval_seconds=0.005,
            on_incomplete=persisted.append,
        )

    assert persisted == [captured.value.outcome]
    assert captured.value.outcome.solver_call_count == expected_count
    assert captured.value.outcome.reason == reason
    assert not captured.value.outcome.is_infeasibility_evidence
    assert not captured.value.outcome.resume_allowed


def test_hash_or_phase_drift_fails_closed_before_solver_call(tmp_path: Path) -> None:
    path = tmp_path / "phases.jsonl"
    binding = _binding()
    journal = DurablePhaseJournal(path, binding=binding)
    journal.emit("worker_started")
    record = json.loads(path.read_text(encoding="utf-8"))
    record["binding"]["candidate_id"] = "drifted"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    with pytest.raises(PhaseContractError, match="identity/hash drifted"):
        load_verified_phase_events(
            path, expected_binding=binding, expected_worker_pid=os.getpid()
        )

    outcome = classify_phase_contract_failure(
        solver_started_was_verified=False, reason="phase_hash_drift"
    )
    assert outcome.solver_call_count == 0
    assert not outcome.is_infeasibility_evidence


def test_missing_required_phase_cannot_activate_solver_timer(tmp_path: Path) -> None:
    path = tmp_path / "phases.jsonl"
    binding = _binding()
    journal = DurablePhaseJournal(path, binding=binding)
    journal.emit("worker_started")
    journal.emit("context_load_started")
    journal.emit("context_load_completed")
    journal.emit("prepared_cases_completed")
    journal.emit("nlp_build_started", _fingerprints()[0])
    journal.emit("solver_started", _fingerprints()[1])

    with pytest.raises(PhaseContractError, match="required phase order drifted"):
        load_verified_phase_events(
            path, expected_binding=binding, expected_worker_pid=os.getpid()
        )


def test_solver_finished_must_preserve_solver_input_fingerprint(tmp_path: Path) -> None:
    path = tmp_path / "phases.jsonl"
    binding = _binding()
    journal = DurablePhaseJournal(path, binding=binding)
    _emit_through_solver_started(journal)
    drifted = {**_fingerprints()[1], "solver_input_fingerprint_sha256": _hash("9")}
    journal.emit("solver_finished", drifted)

    with pytest.raises(PhaseContractError, match="solver_finished hash drifted"):
        load_verified_phase_events(
            path, expected_binding=binding, expected_worker_pid=os.getpid()
        )


def test_expression_component_hash_is_recomputed(tmp_path: Path) -> None:
    path = tmp_path / "phases.jsonl"
    binding = _binding()
    journal = DurablePhaseJournal(path, binding=binding)
    _emit_through_solver_started(journal)
    records = [json.loads(line) for line in path.read_text().splitlines()]
    records[5]["payload"]["variable_count"] = 3
    path.write_text("\n".join(json.dumps(item) for item in records) + "\n")

    with pytest.raises(PhaseContractError, match="expression fingerprint drifted"):
        load_verified_phase_events(
            path, expected_binding=binding, expected_worker_pid=os.getpid()
        )

    records[5]["payload"]["variable_count"] = 2
    records[6]["payload"]["initial_point_sha256"] = _hash("9")
    path.write_text("\n".join(json.dumps(item) for item in records) + "\n")
    with pytest.raises(PhaseContractError, match="solver input fingerprint drifted"):
        load_verified_phase_events(
            path, expected_binding=binding, expected_worker_pid=os.getpid()
        )


def test_prepared_and_ipopt_hashes_must_equal_binding(tmp_path: Path) -> None:
    path = tmp_path / "phases.jsonl"
    binding = _binding()
    journal = DurablePhaseJournal(path, binding=binding)
    for event in (
        "worker_started",
        "context_load_started",
        "context_load_completed",
        "prepared_cases_completed",
    ):
        journal.emit(event)
    drifted = _fingerprints()[0]
    drifted["ipopt_options_sha256"] = _hash("9")
    drifted["expression_fingerprint_sha256"] = expression_fingerprint_sha256(drifted)
    journal.emit(
        "nlp_build_started",
        {
            "prepared_inputs_sha256": drifted["prepared_inputs_sha256"],
            "ipopt_options_sha256": drifted["ipopt_options_sha256"],
        },
    )
    journal.emit("nlp_build_completed", drifted)

    with pytest.raises(PhaseContractError, match="bound input fingerprint drifted"):
        load_verified_phase_events(
            path, expected_binding=binding, expected_worker_pid=os.getpid()
        )


def test_worker_pid_timestamp_and_monotonic_evidence_fail_closed(
    tmp_path: Path,
) -> None:
    binding = _binding()
    path = tmp_path / "phases.jsonl"
    journal = DurablePhaseJournal(path, binding=binding)
    journal.emit("worker_started")

    with pytest.raises(PhaseContractError, match="identity/hash drifted"):
        load_verified_phase_events(
            path, expected_binding=binding, expected_worker_pid=os.getpid() + 1
        )

    record = json.loads(path.read_text())
    record["timestamp_utc"] = "2026-08-12T00:00:00"
    path.write_text(json.dumps(record) + "\n")
    with pytest.raises(PhaseContractError, match="timestamp drifted"):
        load_verified_phase_events(
            path, expected_binding=binding, expected_worker_pid=os.getpid()
        )

    path.unlink()
    journal = DurablePhaseJournal(path, binding=binding)
    journal.emit("worker_started")
    journal.emit("context_load_started")
    records = [json.loads(line) for line in path.read_text().splitlines()]
    records[1]["worker_monotonic_elapsed_seconds"] = -0.1
    path.write_text("\n".join(json.dumps(item) for item in records) + "\n")
    with pytest.raises(PhaseContractError, match="identity/hash drifted"):
        load_verified_phase_events(
            path, expected_binding=binding, expected_worker_pid=os.getpid()
        )
    records[1]["worker_monotonic_elapsed_seconds"] = float("inf")
    path.write_text("\n".join(json.dumps(item) for item in records) + "\n")
    with pytest.raises(PhaseContractError, match="identity/hash drifted"):
        load_verified_phase_events(
            path, expected_binding=binding, expected_worker_pid=os.getpid()
        )


def test_adapter_observer_preserves_factory_and_solver_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_options = core._FROZEN_IPOPT_OPTIONS
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
    captures: list[tuple[str, object]] = []

    class FakeSolver:
        def __call__(self, **kwargs: object) -> dict[str, np.ndarray]:
            captures.append(
                (
                    "call",
                    {key: np.asarray(value).copy() for key, value in kwargs.items()},
                )
            )
            return {"x": np.array([0.0]), "g": np.array([0.0]), "f": 0.0}

        def stats(self) -> dict[str, object]:
            return {"success": True, "return_status": "ok", "iter_count": 0}

    def fake_factory(
        name: str,
        plugin: str,
        problem: dict[str, object],
        options: dict[str, object],
    ) -> FakeSolver:
        captures.append(
            (
                "factory",
                (
                    name,
                    plugin,
                    ca.Function(
                        "captured_x", [problem["x"]], [problem["x"]]
                    ).serialize(),
                    ca.Function(
                        "captured_f", [problem["x"]], [problem["f"]]
                    ).serialize(),
                    ca.Function(
                        "captured_g", [problem["x"]], [problem["g"]]
                    ).serialize(),
                    dict(options),
                ),
            )
        )
        return FakeSolver()

    def fake_core_solve(
        cases: object,
        observed_chronology: object,
        *,
        initial_strategy: str,
        solver_options: dict[str, object],
    ) -> tuple[object, object, str]:
        assert cases == (prepared,)
        assert observed_chronology is chronology
        x = ca.MX.sym("x", 1)
        solver = core.ca.nlpsol(
            "ac_aware_commitment", "ipopt", {"x": x, "f": x**2, "g": x}, solver_options
        )
        result = solver(
            x0=np.array([0.25]),
            lbx=np.array([-1.0]),
            ubx=np.array([1.0]),
            lbg=np.array([0.0]),
            ubg=np.array([0.0]),
        )
        return result, solver.stats(), initial_strategy

    monkeypatch.setattr(core.ca, "nlpsol", fake_factory)
    monkeypatch.setattr(core, "solve_ac_aware_commitment", fake_core_solve)
    baseline = solve_ac_aware_commitment_v4_worker(
        (prepared,),
        chronology,
        base_options=dict(shared_ipopt._FROZEN_IPOPT_OPTIONS),
        runtime_options={},
    )
    baseline_captures = list(captures)
    captures.clear()
    events: list[tuple[str, Mapping[str, object]]] = []

    observed = solve_ac_aware_commitment_v4_worker(
        (prepared,),
        chronology,
        base_options=dict(shared_ipopt._FROZEN_IPOPT_OPTIONS),
        runtime_options={},
        phase_observer=lambda event, payload: events.append((event, dict(payload))),
    )

    assert observed == baseline
    assert captures[0] == baseline_captures[0]
    assert captures[1][0] == baseline_captures[1][0] == "call"
    for key in captures[1][1]:
        np.testing.assert_array_equal(captures[1][1][key], baseline_captures[1][1][key])
    assert [event for event, _ in events] == [
        "nlp_build_started",
        "nlp_build_completed",
        "solver_started",
        "solver_finished",
    ]
    assert (
        events[1][1]["prepared_inputs_sha256"] == events[0][1]["prepared_inputs_sha256"]
    )
    assert events[0][1]["prepared_inputs_sha256"] == prepared_inputs_sha256(
        (prepared,), chronology
    )
    drifted_prepared = SimpleNamespace(
        **{**vars(prepared), "mode": "reference_provider"}
    )
    assert prepared_inputs_sha256(
        (drifted_prepared,), chronology
    ) != prepared_inputs_sha256((prepared,), chronology)
    assert (
        events[2][1]["expression_fingerprint_sha256"]
        == events[1][1]["expression_fingerprint_sha256"]
    )
    assert (
        events[3][1]["solver_input_fingerprint_sha256"]
        == events[2][1]["solver_input_fingerprint_sha256"]
    )
    assert core._FROZEN_IPOPT_OPTIONS is original_options
    assert core.ca.nlpsol is fake_factory


def test_repair010_config_and_formal_stages_are_fail_closed(tmp_path: Path) -> None:
    config = formal._read_config()

    assert (
        config["formal_successor"][
            "maximum_accepted_relative_gap_to_feasible_incumbent"
        ]
        == 1.0e-3
    )
    assert config["preregistration"]["candidate_frontier_outcomes_observed"] is True
    assert config["joint_ac_successor"]["startup_limit_seconds"] is None
    assert config["joint_ac_successor"]["context_artifact_mode"] == "disabled_unproven"
    assert (
        config["joint_ac_successor"]["fallback_mode"]
        == "fresh_rebuild_in_fresh_isolated_worker"
    )
    assert all(
        "artifact" not in reason
        for reason in config["joint_ac_successor"]["blocking_reasons"]
    )
    with pytest.raises(formal.SuccessorNotReadyError, match="fail-closed"):
        formal.prepare_preregistration(output_directory=tmp_path)
    with pytest.raises(formal.SuccessorNotReadyError, match="fail-closed"):
        formal.import_predecessor_frontier(output_directory=tmp_path)
    with pytest.raises(formal.SuccessorNotReadyError, match="fail-closed"):
        formal.run_joint_ac(output_directory=tmp_path, attempt_id="must_not_start")
    with pytest.raises(formal.SuccessorNotReadyError, match="fail-closed"):
        formal.run_joint_call_worker(
            formal.DEFAULT_CONFIG_PATH,
            output_directory=tmp_path,
            candidate_id="candidate_00",
            initial_strategy="source",
            result_directory=tmp_path / "result",
            native_solver_log=tmp_path / "ipopt.log",
            phase_journal=tmp_path / "phase.jsonl",
            phase_registration_directory=tmp_path / "phase_registration",
            call_registration_manifest_sha256=_hash("1"),
            phase_registration_manifest_sha256=_hash("2"),
        )
    assert list(tmp_path.iterdir()) == []


def test_repair010_worker_executor_calls_only_dedicated_adapter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = {"dedicated": 0, "shared": 0}
    observer_events: list[str] = []
    prepared_cases = (object(),)
    chronology = object()
    candidate = SimpleNamespace(candidate_id="candidate_00")
    context = SimpleNamespace(
        config={
            "joint_ac": {
                "ipopt_options": dict(shared_ipopt._FROZEN_IPOPT_OPTIONS),
                "runtime_control": {
                    "max_cpu_time_seconds_per_call": 7200.0,
                    "native_file_print_level": 5,
                },
            }
        }
    )
    native_log = tmp_path / "native.log"
    result_root = tmp_path / "worker_result"
    result = object()
    metadata = {"schema": "tiny_worker_metadata"}
    rows = ({"run": 1}, [], [], [], [], [])

    def dedicated_solve(
        observed_cases: object,
        observed_chronology: object,
        **kwargs: object,
    ) -> object:
        calls["dedicated"] += 1
        assert observed_cases is prepared_cases
        assert observed_chronology is chronology
        assert kwargs["initial_strategy"] == "source"
        assert kwargs["base_options"] == context.config["joint_ac"]["ipopt_options"]
        assert kwargs["runtime_options"] == {
            "ipopt.max_cpu_time": 7200.0,
            "ipopt.output_file": str(native_log.resolve()),
            "ipopt.file_print_level": 5,
        }
        phase_observer = kwargs["phase_observer"]
        assert callable(phase_observer)
        phase_observer("solver_started", {"test": "tiny"})
        phase_observer("solver_finished", {"test": "tiny"})
        native_log.write_text("not an IPOPT run", encoding="utf-8")
        return result

    def shared_solve(*_args: object, **_kwargs: object) -> object:
        calls["shared"] += 1
        raise AssertionError("repair-010 worker must not call the shared adapter")

    monkeypatch.setattr(
        dedicated_adapter, "solve_ac_aware_commitment_v4_worker", dedicated_solve
    )
    monkeypatch.setattr(
        shared_adapter, "solve_ac_aware_commitment_v4_worker", shared_solve
    )
    monkeypatch.setattr(v4 := formal.v4, "_joint_result_rows", lambda *_args: rows)
    monkeypatch.setattr(
        v4, "_validate_joint_result_rows", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(v4, "_joint_worker_metadata", lambda *_args: metadata)
    monkeypatch.setattr(
        v4,
        "_publish_immutable_payload",
        lambda _target, _writer, *, validator: None,
    )
    monkeypatch.setattr(v4, "_load_joint_worker_result", lambda *_args: (None, "m"))

    observed = formal._execute_repair010_joint_call_worker(
        context,
        candidate,
        "source",
        _hash("f"),
        result_root,
        native_log,
        _hash("c"),
        prepared_cases,
        chronology,
        lambda event, _payload: observer_events.append(event),
    )

    assert observed is metadata
    assert calls == {"dedicated": 1, "shared": 0}
    assert observer_events == ["solver_started", "solver_finished"]


def test_repair010_joint_worker_entry_wires_dedicated_adapter_and_observer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = deepcopy(formal._read_config())
    config["joint_ac_successor"]["startup_limit_seconds"] = 1.0
    config["joint_ac_successor"]["formal_execution_ready"] = True
    config["preregistration"]["status"] = "repository_local_not_externally_timestamped"
    output_root = tmp_path / "output"
    log_root = tmp_path / "logs" / "attempt"
    config["logging"]["directory"] = str(tmp_path / "logs")
    result_root = log_root / "worker_result"
    native_log = log_root / "native.log"
    process_log = log_root / "worker.log"
    phase_journal = log_root / "phase.jsonl"
    phase_registration = tmp_path / "phase_registration"
    phase_registration.mkdir()
    (phase_registration / "SHA256SUMS").write_text("phase", encoding="ascii")
    phase_manifest = formal._sha256(phase_registration / "SHA256SUMS")
    call_root = tmp_path / "call_registration"
    call_root.mkdir()
    parent_pid = os.getppid()
    candidate = SimpleNamespace(
        candidate_id="candidate_00",
        commitment_sha256=_hash("4"),
        dispatch_sha256=_hash("5"),
    )
    prepared_cases = (object(),)
    chronology = object()
    call_registration = {
        "parent_pid": parent_pid,
        "parent_attempt_id": "attempt",
        "worker_result_relative_path": "worker_result",
        "native_solver_log_relative_path": "native.log",
        "worker_process_log_relative_path": "worker.log",
    }
    (call_root / "call.json").write_text(
        json.dumps(call_registration), encoding="utf-8"
    )
    (call_root / "SHA256SUMS").write_text(
        f"{formal._sha256(call_root / 'call.json')}  call.json\n",
        encoding="ascii",
    )
    call_manifest = formal._sha256(call_root / "SHA256SUMS")
    binding = formal.build_worker_binding(
        preregistration_id=config["preregistration"]["id"],
        input_contract_sha256=_hash("1"),
        frontier_manifest_sha256=_hash("2"),
        call_manifest_sha256=call_manifest,
        candidate_id=candidate.candidate_id,
        commitment_sha256=candidate.commitment_sha256,
        dispatch_sha256=candidate.dispatch_sha256,
        initial_strategy="source",
        prepared_inputs_sha256=_hash("a"),
        ipopt_options_sha256=_hash("b"),
        software_identity={"test": "entry"},
    )
    registration = {
        "binding": binding,
        "phase_journal": str(phase_journal.resolve()),
        "worker_result": str(result_root.resolve()),
        "native_solver_log": str(native_log.resolve()),
        "worker_process_log": str(process_log.resolve()),
        "parent_pid": parent_pid,
    }
    lease_root = output_root / "execution_lease" / "active"
    lease_root.mkdir(parents=True)
    (lease_root / "lease.json").write_text(
        json.dumps(
            {
                "schema": "execution_lease_v1",
                "pid": parent_pid,
                "stage": "run_joint_ac",
                "attempt_id": "attempt",
            }
        ),
        encoding="utf-8",
    )
    context = SimpleNamespace(
        config={
            "preregistration": {"id": config["preregistration"]["id"]},
            "joint_ac": {
                "ipopt_options": dict(shared_ipopt._FROZEN_IPOPT_OPTIONS),
                "runtime_control": {
                    "max_cpu_time_seconds_per_call": 7200.0,
                    "native_file_print_level": 5,
                },
            },
        },
        input_contract_sha256=_hash("1"),
    )
    calls = {"dedicated": 0, "shared": 0}
    observer_events: list[str] = []
    metadata = {"schema": "entry_worker_metadata"}

    class NullWatchdog:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def __enter__(self) -> None:
            return None

        def __exit__(self, *_args: object) -> None:
            return None

    def fake_phase_worker(**kwargs: object) -> object:
        validator = kwargs["post_worker_start_validator"]
        assert callable(validator)
        validator()
        context_loader = kwargs["context_loader"]
        prepared_loader = kwargs["prepared_cases_loader"]
        operation = kwargs["worker_operation"]
        assert callable(context_loader)
        assert callable(prepared_loader)
        assert callable(operation)
        loaded_context = context_loader()
        loaded_cases, loaded_chronology = prepared_loader(loaded_context)
        return operation(
            loaded_context,
            loaded_cases,
            loaded_chronology,
            lambda event, _payload: observer_events.append(event),
        )

    def dedicated_solve(*args: object, **kwargs: object) -> object:
        calls["dedicated"] += 1
        assert args == (prepared_cases, chronology)
        observer = kwargs["phase_observer"]
        assert callable(observer)
        observer("solver_started", {})
        observer("solver_finished", {})
        native_log.parent.mkdir(parents=True, exist_ok=True)
        native_log.write_text("not an IPOPT run", encoding="utf-8")
        return object()

    def shared_solve(*_args: object, **_kwargs: object) -> object:
        calls["shared"] += 1
        raise AssertionError("shared adapter was reached")

    monkeypatch.setattr(formal, "_read_config", lambda _path: config)
    monkeypatch.setattr(formal, "_load_phase_registration", lambda _path: registration)
    monkeypatch.setattr(formal, "_build_context", lambda _path: context)
    monkeypatch.setattr(formal, "_require_preregistration", lambda *_args: None)
    monkeypatch.setattr(
        formal,
        "_load_successor_frontier_import",
        lambda *_args: ([candidate], _hash("2")),
    )
    monkeypatch.setattr(formal, "_software_identity", lambda: {"test": "entry"})
    monkeypatch.setattr(formal, "execute_phase_instrumented_worker", fake_phase_worker)
    monkeypatch.setattr(formal.v4, "ParentProcessWatchdog", NullWatchdog)
    monkeypatch.setattr(
        formal.v4, "_joint_call_registration_path", lambda *_args: call_root
    )
    monkeypatch.setattr(
        formal.v4,
        "_validate_joint_call_registration",
        lambda *_args: call_manifest,
    )
    monkeypatch.setattr(
        formal.v4,
        "_prepared_joint_cases",
        lambda *_args: prepared_cases,
    )
    monkeypatch.setattr(formal.v4, "_joint_chronology", lambda *_args: chronology)
    monkeypatch.setattr(
        dedicated_adapter, "prepared_inputs_sha256", lambda *_args: _hash("a")
    )
    monkeypatch.setattr(
        dedicated_adapter,
        "effective_ipopt_options_sha256",
        lambda **_kwargs: _hash("b"),
    )
    monkeypatch.setattr(
        dedicated_adapter, "solve_ac_aware_commitment_v4_worker", dedicated_solve
    )
    monkeypatch.setattr(
        shared_adapter, "solve_ac_aware_commitment_v4_worker", shared_solve
    )
    monkeypatch.setattr(
        formal.v4,
        "_joint_result_rows",
        lambda *_args: ({"run": 1}, [], [], [], [], []),
    )
    monkeypatch.setattr(
        formal.v4, "_validate_joint_result_rows", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(formal.v4, "_joint_worker_metadata", lambda *_args: metadata)
    monkeypatch.setattr(
        formal.v4,
        "_publish_immutable_payload",
        lambda _target, _writer, *, validator: None,
    )
    monkeypatch.setattr(
        formal.v4, "_load_joint_worker_result", lambda *_args: (None, "m")
    )

    observed = formal.run_joint_call_worker(
        formal.DEFAULT_CONFIG_PATH,
        output_directory=output_root,
        candidate_id="candidate_00",
        initial_strategy="source",
        result_directory=result_root,
        native_solver_log=native_log,
        phase_journal=phase_journal,
        phase_registration_directory=phase_registration,
        call_registration_manifest_sha256=call_manifest,
        phase_registration_manifest_sha256=phase_manifest,
    )

    assert observed is metadata
    assert calls == {"dedicated": 1, "shared": 0}
    assert observer_events == ["solver_started", "solver_finished"]


def test_disabled_artifact_does_not_block_fresh_rebuild_fallback() -> None:
    config = deepcopy(formal._read_config())
    config["joint_ac_successor"]["startup_limit_seconds"] = 1.0
    config["joint_ac_successor"]["formal_execution_ready"] = True
    config["preregistration"]["status"] = "repository_local_not_externally_timestamped"

    formal._assert_successor_ready(config)


def test_software_identity_binds_casadi_and_ipopt_binaries() -> None:
    identity = formal._software_identity()
    binary_hashes = identity["casadi_and_ipopt_binary_sha256"]

    assert "_casadi.pyd" in binary_hashes
    assert "libcasadi_nlpsol_ipopt.dll" in binary_hashes
    assert "libipopt-3.dll" in binary_hashes
    assert all(re.fullmatch(r"[0-9a-f]{64}", value) for value in binary_hashes.values())
    assert identity["ipopt_plugin_identity"] == "CasADi Nlpsol::ipopt"


def test_worker_command_requires_fresh_successor_process(tmp_path: Path) -> None:
    command = formal._joint_worker_command(
        python_executable=Path(sys.executable),
        config_path=formal.DEFAULT_CONFIG_PATH,
        output_root=tmp_path / "output",
        candidate_id="candidate_00",
        initial_strategy="source",
        worker_result=tmp_path / "worker",
        native_log=tmp_path / "native.log",
        phase_journal=tmp_path / "phases.jsonl",
        phase_registration_directory=tmp_path / "phase_registration",
        call_manifest_sha256=_hash("a"),
        phase_registration_manifest_sha256=_hash("b"),
    )

    assert command[:4] == [
        sys.executable,
        "-B",
        "-m",
        "experiments.run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_010_formal",
    ]
    assert "repair_009" not in " ".join(command)


def test_frontier_import_cli_rejects_worker_only_arguments_before_write(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "repair010",
            "--stage",
            "import-predecessor-frontier",
            "--output-directory",
            str(tmp_path),
            "--candidate-id",
            "candidate_00",
        ],
    )

    with pytest.raises(SystemExit) as caught:
        formal.main()

    assert caught.value.code == 2
    assert list(tmp_path.iterdir()) == []
