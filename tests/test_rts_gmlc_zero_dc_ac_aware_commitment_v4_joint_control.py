"""Control-plane tests; full AC row reconstruction is deliberately stubbed."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import run_rts_gmlc_zero_dc_ac_aware_commitment_v4 as runner


def _context(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        config_path=tmp_path / "config.yaml",
        output_root=tmp_path / "unused-results",
        input_contract_sha256="a" * 64,
        config={
            "preregistration": {"id": "joint-control-v4"},
            "joint_ac": {
                "engine": "casadi-ipopt",
                "ipopt_options": {"tol": 1.0e-6},
                "initial_strategies": ["source"],
                "runtime_control": {
                    "max_wall_time_seconds_per_call": 1.0,
                    "heartbeat_interval_seconds": 0.1,
                    "termination_grace_seconds": 0.1,
                    "parent_watchdog_interval_seconds": 0.1,
                    "log_directory": str(tmp_path / "logs"),
                },
            },
            "interpretation": {
                "successful_claim": "witness found",
                "unsuccessful_claim": "witness not found",
            },
            "evidence": {"formal_candidate_result": False},
        },
    )


def _candidate() -> runner._LoadedCandidate:
    return runner._LoadedCandidate(
        candidate_id="candidate_1",
        requested_candidate_id="delta_1",
        relative_cost_budget_delta=0.01,
        operating_cost_usd=100.0,
        reactive_proxy_fraction=0.5,
        commitment_sha256="b" * 64,
        dispatch_sha256="c" * 64,
        commitment=(),
        startup=(),
        shutdown=(),
        generation_mw=(),
        branch_flows_mw=(),
        dc_flows_mw=(),
    )


def _empty_joint_rows() -> runner._JointRows:
    return runner._JointRows(
        runs=(),
        hours=(),
        generators=(),
        buses=(),
        branches=(),
        reserves=(),
    )


def _register(
    context: SimpleNamespace,
    output_root: Path,
    candidate: runner._LoadedCandidate,
    strategy: str,
    frontier_manifest: str,
) -> str:
    paths = runner._joint_worker_paths(
        Path(context.config["joint_ac"]["runtime_control"]["log_directory"])
        / "joint-test",
        candidate.candidate_id,
        strategy,
    )
    return runner._register_joint_call(
        context,
        output_root,
        candidate,
        strategy,
        frontier_manifest,
        parent_attempt_id="joint-test",
        parent_pid=1234,
        worker_result_directory=paths[0],
        native_solver_log=paths[1],
        worker_process_log=paths[2],
    )


def _publish_worker_result(
    context: SimpleNamespace,
    output_root: Path,
    candidate: runner._LoadedCandidate,
    strategy: str,
    frontier_manifest: str,
    registration_manifest: str,
    rows: runner._JointRows,
) -> tuple[Path, str]:
    registration = runner._load_json(
        runner._joint_call_registration_path(
            output_root, candidate.candidate_id, strategy
        ),
        "call.json",
    )
    worker_root, native_log, _ = runner._registered_joint_worker_paths(
        context, registration
    )
    native_log.parent.mkdir(parents=True, exist_ok=True)
    native_log.write_text("Ipopt test log\n", encoding="utf-8")
    metadata = runner._joint_worker_metadata(
        context,
        candidate,
        strategy,
        frontier_manifest,
        registration_manifest,
        runner._sha256(native_log),
    )

    def writer(staging: Path) -> None:
        runner._write_joint_rows(staging, rows)
        runner._write_exact_json(staging / "worker.json", metadata)

    runner._publish_immutable_payload(worker_root, writer)
    return native_log, runner._sha256(worker_root / "SHA256SUMS")


@pytest.fixture
def stub_complex_ac_reconstruction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep persistence tests scoped to control-plane behavior."""
    monkeypatch.setattr(runner, "_validate_joint_result_rows", lambda *_a, **_k: None)


def test_registration_is_published_before_execution_and_blocks_retry(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    candidate = _candidate()
    frontier_manifest = "d" * 64

    registration_manifest = _register(
        context, tmp_path, candidate, "source", frontier_manifest
    )
    registration = runner._joint_call_registration_path(
        tmp_path, candidate.candidate_id, "source"
    )
    checkpoint = runner._joint_checkpoint_path(
        tmp_path, candidate.candidate_id, "source"
    )

    assert (registration / "call.json").is_file()
    assert (registration / "SHA256SUMS").is_file()
    assert registration_manifest == runner._sha256(registration / "SHA256SUMS")
    assert not checkpoint.exists()
    assert (
        json.loads((registration / "call.json").read_text(encoding="utf-8"))[
            "retry_allowed"
        ]
        is False
    )

    assert (
        runner._load_joint_checkpoint(
            context,
            tmp_path,
            candidate,
            "source",
            frontier_manifest,
            (),
            SimpleNamespace(),
        )
        is None
    )


def test_completed_checkpoint_reloads_and_failed_semantic_staging_is_removed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stub_complex_ac_reconstruction: None,
) -> None:
    context = _context(tmp_path)
    candidate = _candidate()
    frontier_manifest = "d" * 64
    rows = _empty_joint_rows()
    chronology = SimpleNamespace()
    source_registration = _register(
        context, tmp_path, candidate, "source", frontier_manifest
    )
    native_log, worker_manifest = _publish_worker_result(
        context,
        tmp_path,
        candidate,
        "source",
        frontier_manifest,
        source_registration,
        rows,
    )

    saved_rows, checkpoint_manifest, observed_registration = (
        runner._save_joint_checkpoint(
            context,
            tmp_path,
            candidate,
            "source",
            frontier_manifest,
            source_registration,
            (),
            chronology,
            rows,
            native_log,
            worker_manifest,
        )
    )
    checkpoint = runner._joint_checkpoint_path(
        tmp_path, candidate.candidate_id, "source"
    )

    assert saved_rows == rows
    assert observed_registration == source_registration
    assert checkpoint_manifest == runner._sha256(checkpoint / "SHA256SUMS")
    assert (checkpoint / "ipopt.log").read_bytes() == native_log.read_bytes()
    assert (checkpoint / "checkpoint.json").is_file()
    assert (checkpoint / "SHA256SUMS").is_file()
    assert runner._load_joint_checkpoint(
        context,
        tmp_path,
        candidate,
        "source",
        frontier_manifest,
        (),
        chronology,
    ) == (rows, checkpoint_manifest, source_registration)
    registration = runner._load_json(
        runner._joint_call_registration_path(
            tmp_path, candidate.candidate_id, "source"
        ),
        "call.json",
    )
    worker_root, _, _ = runner._registered_joint_worker_paths(context, registration)
    native_log.unlink()
    shutil.rmtree(worker_root)
    assert runner._load_joint_checkpoint(
        context,
        tmp_path,
        candidate,
        "source",
        frontier_manifest,
        (),
        chronology,
    ) == (rows, checkpoint_manifest, source_registration)

    midpoint_registration = _register(
        context, tmp_path, candidate, "midpoint", frontier_manifest
    )
    midpoint_native_log, midpoint_worker_manifest = _publish_worker_result(
        context,
        tmp_path,
        candidate,
        "midpoint",
        frontier_manifest,
        midpoint_registration,
        rows,
    )

    def reject_semantics(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("semantic validation failed")

    monkeypatch.setattr(runner, "_validate_joint_result_rows", reject_semantics)
    midpoint_checkpoint = runner._joint_checkpoint_path(
        tmp_path, candidate.candidate_id, "midpoint"
    )
    with pytest.raises(RuntimeError, match="semantic validation failed"):
        runner._save_joint_checkpoint(
            context,
            tmp_path,
            candidate,
            "midpoint",
            frontier_manifest,
            midpoint_registration,
            (),
            chronology,
            rows,
            midpoint_native_log,
            midpoint_worker_manifest,
        )

    assert not midpoint_checkpoint.exists()
    assert not tuple(
        midpoint_checkpoint.parent.glob(f".{midpoint_checkpoint.name}.processing-*")
    )


@pytest.mark.parametrize("needs_kill", (False, True))
def test_joint_worker_timeout_terminates_then_kills_if_needed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    needs_kill: bool,
) -> None:
    context = _context(tmp_path)

    class NoopHeartbeat:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def __enter__(self) -> "NoopHeartbeat":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def raise_if_failed(self) -> None:
            return None

    class TimedOutProcess:
        pid = 1234
        returncode = None

        def __init__(self) -> None:
            self.wait_count = 0
            self.terminated = False
            self.killed = False

        def wait(self, timeout: float) -> int:
            self.wait_count += 1
            if needs_kill and self.terminated and not self.killed:
                raise subprocess.TimeoutExpired("joint-worker", timeout)
            self.returncode = 0
            return 0

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            self.terminated = True

        def kill(self) -> None:
            self.killed = True

    process = TimedOutProcess()
    monkeypatch.setattr(runner, "_CheckedProgressHeartbeat", NoopHeartbeat)
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *_a, **_k: process)
    monotonic_values = iter((0.0, 2.0))
    monkeypatch.setattr(runner, "monotonic", lambda: next(monotonic_values))

    with pytest.raises(TimeoutError, match="exceeded 1.0 seconds"):
        runner._run_joint_worker_process(
            context,
            tmp_path / "results",
            _candidate(),
            "source",
            "d" * 64,
            (),
            SimpleNamespace(),
            tmp_path / "worker-logs",
            SimpleNamespace(emit=lambda *_a, **_k: None),
            "e" * 64,
        )

    assert process.terminated
    assert process.killed is needs_kill
    assert process.wait_count == (2 if needs_kill else 1)


def test_joint_attempt_failure_is_logged_and_lease_is_archived(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = _context(tmp_path)
    output_root = tmp_path / "results"
    attempt_id = "joint-failure"
    monkeypatch.setattr(runner, "_build_context", lambda _path: context)
    monkeypatch.setattr(
        runner,
        "_require_preregistration",
        lambda _context, _root: {
            "input_contract_sha256": context.input_contract_sha256
        },
    )
    monkeypatch.setattr(
        runner,
        "_load_candidate_frontier",
        lambda _context, _root: ([_candidate()], "d" * 64),
    )

    def fail_attempt(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise RuntimeError("joint failed")

    monkeypatch.setattr(runner, "_run_joint_ac_attempt", fail_attempt)

    with pytest.raises(RuntimeError, match="joint failed"):
        runner.run_joint_ac(
            context.config_path,
            output_directory=output_root,
            attempt_id=attempt_id,
        )

    progress_path = Path(context.config["joint_ac"]["runtime_control"]["log_directory"])
    progress_rows = [
        json.loads(line)
        for line in (progress_path / attempt_id / "progress.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert progress_rows[-1]["event"] == "attempt_failed"
    assert progress_rows[-1]["error_type"] == "RuntimeError"
    assert progress_rows[-1]["error_message"] == "joint failed"

    lease_root = output_root / "execution_lease"
    failed_history = tuple((lease_root / "history").glob("*.failed"))
    assert len(failed_history) == 1
    terminal = json.loads(
        (failed_history[0] / "terminal.json").read_text(encoding="utf-8")
    )
    assert terminal["status"] == "failed"
    assert terminal["error_type"] == "RuntimeError"
    assert terminal["error_message"] == "joint failed"
    assert not (lease_root / "active").exists()


def test_joint_summary_binds_checkpoint_and_call_registration_manifests(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path)
    candidate = _candidate()
    key = runner._joint_call_key(candidate.candidate_id, "source")
    checkpoint_manifests = {key: "e" * 64}
    call_manifests = {key: "f" * 64}
    run_row = {
        "candidate_id": candidate.candidate_id,
        "initial_strategy": "source",
        "solver_success": True,
        "feasibility_witnessed": True,
        "return_status": "Solve_Succeeded",
        "iterations": 7,
        "maximum_nlp_constraint_violation": 0.0,
        "maximum_nlp_variable_bound_violation": 0.0,
        "maximum_ramp_violation_mw": 0.0,
        "maximum_reserve_bound_violation_mw": 0.0,
        "maximum_reserve_headroom_violation_mw": 0.0,
        "maximum_reserve_shortfall_mw": 0.0,
    }

    summary = runner._joint_summary(
        context,
        {"input_contract_sha256": context.input_contract_sha256},
        (candidate,),
        "d" * 64,
        (run_row,),
        checkpoint_manifests,
        call_manifests,
    )

    assert summary["schema"] == "rts_gmlc_zero_dc_ac_aware_joint_ac_results_v4"
    assert summary["joint_checkpoint_schema"] == runner._JOINT_CHECKPOINT_SCHEMA
    assert summary["joint_call_registration_schema"] == runner._JOINT_CALL_SCHEMA
    assert summary["joint_checkpoint_manifest_sha256s"] == checkpoint_manifests
    assert summary["joint_call_registration_manifest_sha256s"] == call_manifests
