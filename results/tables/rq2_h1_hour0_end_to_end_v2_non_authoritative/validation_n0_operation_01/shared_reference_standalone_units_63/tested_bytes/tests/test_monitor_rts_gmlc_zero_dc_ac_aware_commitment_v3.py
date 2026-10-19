from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from experiments.monitor_rts_gmlc_zero_dc_ac_aware_commitment_v3 import (
    build_status,
    main,
)

NOW = datetime(2026, 7, 19, 6, 0, tzinfo=timezone.utc)


def _event(
    event: str,
    *,
    age_seconds: float,
    elapsed_seconds: float,
    pid: int = 4321,
    **payload: object,
) -> dict[str, object]:
    return {
        "schema": "mip_progress_event_v1",
        "run_id": "attempt-001",
        "preregistration_id": ("rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3"),
        "input_contract_sha256": "a" * 64,
        "pid": pid,
        "timestamp_utc": (NOW - timedelta(seconds=age_seconds)).isoformat(),
        "monotonic_elapsed_seconds": elapsed_seconds,
        "event": event,
        **payload,
    }


def _write_progress(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in records),
        encoding="utf-8",
    )


def test_running_status_tracks_outer_and_exact_cg_state_and_deadline(
    tmp_path: Path,
) -> None:
    attempt = tmp_path / "attempt-001"
    deadline = NOW + timedelta(minutes=10)
    records = [
        _event("attempt_started", age_seconds=30, elapsed_seconds=0.0),
        _event(
            "candidate_started",
            age_seconds=25,
            elapsed_seconds=5.0,
            requested_candidate_id="delta_2",
            candidate_ordinal=2,
            completed_candidate_count=1,
            deadline_utc=deadline.isoformat(),
            total_limit_seconds=3600.0,
        ),
        _event(
            "exact_cg_stage_started",
            age_seconds=20,
            elapsed_seconds=10.0,
            stage="proxy_maximization",
        ),
        _event(
            "exact_cg_call_started",
            age_seconds=15,
            elapsed_seconds=15.0,
            stage="proxy_maximization",
            iteration=3,
            call_id="proxy_maximization.iteration_03.master",
            native_log="iteration_03_master.log",
            sense="maximize",
        ),
        _event(
            "heartbeat",
            age_seconds=10,
            elapsed_seconds=20.0,
            stage="proxy_maximization",
            iteration=3,
            call_id="proxy_maximization.iteration_03.master",
        ),
    ]
    _write_progress(attempt / "progress.jsonl", records)
    (attempt / "iteration_03_master.log").write_text(
        """
        Nodes      |    B&B Tree     |            Objective Bounds
Src  Proc. InQueue |  Leaves   Expl. | BestBound BestSol Gap
 R       0       0         0   0.00%   0.2963308991 0.2857142857 3.72% 40 8 3 9302 4.3s
        87      21        33   8.10%   0.2895104426 0.2857142857 1.33% 981 18 900 107394 120.0s

Solving report
  Status            Time limit reached
  Primal bound      0.285714285714
  Dual bound        0.289510442574
  Gap               1.33% (tolerance: 0.01%)
  Nodes             87
""",
        encoding="utf-8",
    )

    status = build_status(
        tmp_path,
        now=NOW,
        stale_after_seconds=60.0,
        process_probe=lambda _pid: True,
    )

    assert status["status"] == "running"
    assert status["alive"] is True
    assert status["current_candidate"] == "delta_2"
    assert status["current_stage"] == "proxy_maximization"
    assert status["current_cg_iteration"] == 3
    assert status["current_solve_label"] == ("proxy_maximization.iteration_03.master")
    assert status["elapsed_seconds"] == 20.0
    assert status["last_heartbeat_age_seconds"] == 10.0
    assert status["completed_candidate_count"] == 1
    assert status["hard_deadline_utc"] == deadline.isoformat()
    assert status["remaining_seconds"] == 600.0
    assert status["latest_incumbent"] == pytest.approx(0.285714285714)
    assert status["latest_lower_bound"] == pytest.approx(0.285714285714)
    assert status["latest_upper_bound"] == pytest.approx(0.289510442574)
    assert status["latest_absolute_gap"] == pytest.approx(
        0.289510442574 - 0.285714285714
    )
    assert status["latest_gap"] == pytest.approx(0.0133)
    assert status["latest_nodes"] == 87


def test_running_joint_call_reports_strategy_counts_deadline_and_native_log(
    tmp_path: Path,
) -> None:
    attempt = tmp_path / "joint-001"
    deadline = NOW + timedelta(minutes=20)
    native_log = attempt / "native" / "candidate_001__source.log"
    native_log.parent.mkdir(parents=True)
    native_log.write_text("Ipopt iteration log\n", encoding="utf-8")
    _write_progress(
        attempt / "progress.jsonl",
        [
            _event(
                "attempt_started",
                age_seconds=20,
                elapsed_seconds=0.0,
                stage="joint_ac",
                expected_joint_call_count=9,
                completed_joint_call_count=2,
            ),
            _event(
                "joint_call_started",
                age_seconds=10,
                elapsed_seconds=10.0,
                stage="joint_ac",
                call_id="joint_ac.candidate_001__source",
                candidate_id="candidate_001",
                initial_strategy="source",
                deadline_utc=deadline.isoformat(),
                native_log=str(native_log.resolve()),
            ),
            _event(
                "heartbeat",
                age_seconds=2,
                elapsed_seconds=18.0,
                stage="joint_ac",
                call_id="joint_ac.candidate_001__source",
                candidate_id="candidate_001",
                initial_strategy="source",
                deadline_utc=deadline.isoformat(),
                native_log=str(native_log.resolve()),
            ),
        ],
    )

    status = build_status(
        tmp_path,
        now=NOW,
        stale_after_seconds=60.0,
        process_probe=lambda _pid: True,
    )

    assert status["status"] == "running"
    assert status["current_candidate"] == "candidate_001"
    assert status["current_stage"] == "joint_ac"
    assert status["current_initial_strategy"] == "source"
    assert status["completed_joint_call_count"] == 2
    assert status["expected_joint_call_count"] == 9
    assert status["remaining_seconds"] == 1200.0
    assert status["native_log_path"] == str(native_log.resolve())


def test_joint_attempt_failure_is_terminal_and_clears_active_call(
    tmp_path: Path,
) -> None:
    _write_progress(
        tmp_path / "joint-001" / "progress.jsonl",
        [
            _event(
                "joint_call_started",
                age_seconds=3,
                elapsed_seconds=10.0,
                stage="joint_ac",
                call_id="joint_ac.candidate_001__source",
                candidate_id="candidate_001",
                initial_strategy="source",
            ),
            _event(
                "attempt_failed",
                age_seconds=1,
                elapsed_seconds=12.0,
                stage="joint_ac",
                error_type="TimeoutError",
                error_message="time limit",
                completed_joint_call_count=0,
                expected_joint_call_count=9,
            ),
        ],
    )

    status = build_status(tmp_path, now=NOW, process_probe=lambda _pid: True)

    assert status["status"] == "failed"
    assert status["current_candidate"] is None
    assert status["current_stage"] is None
    assert status["current_initial_strategy"] is None
    assert status["expected_joint_call_count"] == 9


def test_attempt_completion_is_terminal_even_if_recorded_pid_exists(
    tmp_path: Path,
) -> None:
    path = tmp_path / "attempt-001" / "progress.jsonl"
    _write_progress(
        path,
        [
            _event(
                "candidate_started",
                age_seconds=4,
                elapsed_seconds=10.0,
                requested_candidate_id="delta_1",
            ),
            _event(
                "candidate_completed",
                age_seconds=2,
                elapsed_seconds=20.0,
                requested_candidate_id="delta_1",
                completed_candidate_count=1,
                stage="cost_normalization",
                iteration=2,
            ),
            _event("attempt_completed", age_seconds=1, elapsed_seconds=21.0),
        ],
    )

    status = build_status(tmp_path, now=NOW, process_probe=lambda _pid: True)

    assert status["status"] == "completed"
    assert status["alive"] is False
    assert status["current_candidate"] is None
    assert status["current_stage"] is None
    assert status["current_cg_iteration"] is None
    assert status["current_solve_label"] is None
    assert status["completed_candidate_count"] == 1


def test_candidate_failure_is_terminal_even_without_attempt_failure_event(
    tmp_path: Path,
) -> None:
    path = tmp_path / "attempt-001" / "progress.jsonl"
    _write_progress(
        path,
        [
            _event(
                "candidate_started",
                age_seconds=4,
                elapsed_seconds=10.0,
                requested_candidate_id="delta_1",
            ),
            _event(
                "candidate_failed",
                age_seconds=2,
                elapsed_seconds=20.0,
                requested_candidate_id="delta_1",
                error_type="RuntimeError",
                error_message="checkpoint identity audit failed",
            ),
        ],
    )

    status = build_status(tmp_path, now=NOW, process_probe=lambda _pid: False)

    assert status["status"] == "failed"
    assert status["alive"] is False
    assert status["last_event"] == "candidate_failed"
    assert status["current_candidate"] is None
    assert status["current_stage"] is None
    assert status["current_solve_label"] is None


def test_parent_baseline_is_not_counted_as_a_completed_budget_candidate(
    tmp_path: Path,
) -> None:
    path = tmp_path / "attempt-001" / "progress.jsonl"
    _write_progress(
        path,
        [
            _event(
                "attempt_started",
                age_seconds=5,
                elapsed_seconds=0.0,
                candidate_count=6,
                completed_candidate_count=0,
            ),
            _event(
                "candidate_completed",
                age_seconds=4,
                elapsed_seconds=1.0,
                candidate_ordinal=0,
                requested_candidate_id="parent_zero_dc_selected_n1_dispatch",
                source="frozen_parent_zero_dc_dispatch",
                completed_candidate_count=1,
            ),
            _event(
                "candidate_started",
                age_seconds=3,
                elapsed_seconds=2.0,
                candidate_ordinal=1,
                requested_candidate_id="q_proxy_delta_0p0010",
                completed_candidate_count=1,
            ),
            _event(
                "candidate_failed",
                age_seconds=2,
                elapsed_seconds=3.0,
                candidate_ordinal=1,
                requested_candidate_id="q_proxy_delta_0p0010",
                completed_candidate_count=1,
            ),
        ],
    )

    status = build_status(tmp_path, now=NOW, process_probe=lambda _pid: False)

    assert status["completed_candidate_count"] == 1
    assert status["completed_budget_candidate_count"] == 0
    assert status["requested_budget_candidate_count"] == 6
    assert status["parent_baseline_completed"] is True


def test_stale_heartbeat_cannot_report_alive(tmp_path: Path) -> None:
    _write_progress(
        tmp_path / "attempt-001" / "progress.jsonl",
        [
            _event("attempt_started", age_seconds=400, elapsed_seconds=0.0),
            _event(
                "heartbeat",
                age_seconds=300,
                elapsed_seconds=100.0,
                stage="cost_normalization",
            ),
        ],
    )

    status = build_status(
        tmp_path,
        now=NOW,
        stale_after_seconds=60.0,
        process_probe=lambda _pid: True,
    )

    assert status["status"] == "stale"
    assert status["alive"] is False
    assert status["last_heartbeat_age_seconds"] == 300.0
    assert "latest progress event is stale" in status["warnings"]


def test_truncated_jsonl_preserves_last_complete_event_but_fails_clear(
    tmp_path: Path,
) -> None:
    path = tmp_path / "attempt-001" / "progress.jsonl"
    _write_progress(
        path,
        [
            _event("attempt_started", age_seconds=10, elapsed_seconds=0.0),
            _event(
                "heartbeat",
                age_seconds=5,
                elapsed_seconds=5.0,
                stage="proxy_maximization",
            ),
        ],
    )
    with path.open("a", encoding="utf-8") as output:
        output.write('{"event":"attempt_completed"')

    status = build_status(
        tmp_path,
        now=NOW,
        stale_after_seconds=60.0,
        process_probe=lambda _pid: True,
    )

    assert status["status"] == "malformed"
    assert status["alive"] is None
    assert status["last_event"] == "heartbeat"
    assert status["current_stage"] == "proxy_maximization"
    assert status["malformed_line_count"] == 1


def test_missing_log_root_is_explicitly_missing(tmp_path: Path) -> None:
    status = build_status(tmp_path / "absent", now=NOW)

    assert status["status"] == "missing"
    assert status["alive"] is None
    assert status["progress_path"] is None
    assert status["completed_candidate_count"] == 0


@pytest.mark.parametrize(
    ("probe_result", "expected_status", "expected_alive"),
    ((False, "stale", False), (None, "unknown", None)),
)
def test_pid_probe_never_guesses_liveness(
    tmp_path: Path,
    probe_result: bool | None,
    expected_status: str,
    expected_alive: bool | None,
) -> None:
    _write_progress(
        tmp_path / "attempt-001" / "progress.jsonl",
        [_event("heartbeat", age_seconds=1, elapsed_seconds=4.0)],
    )

    status = build_status(
        tmp_path,
        now=NOW,
        stale_after_seconds=60.0,
        process_probe=lambda _pid: probe_result,
    )

    assert status["status"] == expected_status
    assert status["alive"] is expected_alive


def test_pid_probe_failure_is_reported_as_unknown(tmp_path: Path) -> None:
    _write_progress(
        tmp_path / "attempt-001" / "progress.jsonl",
        [_event("heartbeat", age_seconds=1, elapsed_seconds=4.0)],
    )

    def failed_probe(_pid: int) -> bool:
        raise PermissionError("query denied")

    status = build_status(
        tmp_path,
        now=NOW,
        stale_after_seconds=60.0,
        process_probe=failed_probe,
    )

    assert status["status"] == "unknown"
    assert status["alive"] is None
    assert "PID liveness probe failed: query denied" in status["warnings"]


def test_explicit_remaining_time_is_aged_from_its_event(tmp_path: Path) -> None:
    _write_progress(
        tmp_path / "attempt-001" / "progress.jsonl",
        [
            _event(
                "heartbeat",
                age_seconds=10,
                elapsed_seconds=20.0,
                remaining_seconds=100.0,
            )
        ],
    )

    status = build_status(
        tmp_path,
        now=NOW,
        process_probe=lambda _pid: True,
    )

    assert status["remaining_seconds"] == 90.0
    assert status["hard_deadline_utc"] is None


def test_monitor_finds_nested_formal_candidate_native_log(tmp_path: Path) -> None:
    attempt = tmp_path / "attempt-001"
    _write_progress(
        attempt / "progress.jsonl",
        [
            _event(
                "solve_started",
                age_seconds=2,
                elapsed_seconds=3.0,
                native_log="proxy_maximization__iteration_01__master.log",
                sense="maximize",
            )
        ],
    )
    native = (
        attempt
        / "01_candidate"
        / "proxy_maximization"
        / "proxy_maximization__iteration_01__master.log"
    )
    native.parent.mkdir(parents=True)
    native.write_text(
        "         0       0         0   0.00%   0.81    0.80       1.25%        0      0      0     100     2.0s\n",
        encoding="utf-8",
    )

    status = build_status(
        tmp_path,
        now=NOW,
        process_probe=lambda _pid: True,
    )

    assert status["native_log_path"] == str(native.resolve())
    assert not any(
        "native solver log is missing" in item for item in status["warnings"]
    )


def test_stage_transition_does_not_mix_bounds_from_different_objectives(
    tmp_path: Path,
) -> None:
    attempt = tmp_path / "attempt-001"
    _write_progress(
        attempt / "progress.jsonl",
        [
            _event(
                "solve_completed",
                age_seconds=20,
                elapsed_seconds=10.0,
                solve_label="proxy_maximization.iteration_01.master",
                sense="maximize",
                certified_lower_bound=0.243,
                certified_upper_bound=0.243,
                incumbent_objective=0.243,
            ),
            _event(
                "exact_cg_call_started",
                age_seconds=5,
                elapsed_seconds=20.0,
                call_id="cost_normalization.iteration_01.master",
                stage="cost_normalization",
                sense="minimize",
            ),
            _event(
                "solve_started",
                age_seconds=4,
                elapsed_seconds=21.0,
                solve_label="cost_normalization.iteration_01.master",
                stage="cost_normalization",
                sense="minimize",
                native_log="cost_master.log",
            ),
        ],
    )
    (attempt / "cost_master.log").write_text(
        """Solving report
  Primal bound      inf
  Dual bound        1105010.942314
  Gap               inf
  Nodes             0
""",
        encoding="utf-8",
    )

    status = build_status(
        tmp_path,
        now=NOW,
        process_probe=lambda _pid: True,
    )

    assert status["current_stage"] == "cost_normalization"
    assert status["latest_incumbent"] is None
    assert status["latest_lower_bound"] == pytest.approx(1105010.942314)
    assert status["latest_upper_bound"] is None
    assert status["latest_gap"] is None


def test_completed_stage_certificate_overrides_auxiliary_fixed_lp_zero_gap(
    tmp_path: Path,
) -> None:
    attempt = tmp_path / "attempt-001"
    lower = 1_108_343.8498693602
    upper = 1_108_454.6110815334
    relative_gap = (upper - lower) / upper
    _write_progress(
        attempt / "progress.jsonl",
        [
            _event(
                "solve_started",
                age_seconds=5,
                elapsed_seconds=20.0,
                solve_label="cost_normalization.iteration_01.final_audit",
                stage="cost_normalization",
                sense="minimize",
                native_log="cost_final_audit.log",
            ),
            _event(
                "solve_completed",
                age_seconds=4,
                elapsed_seconds=21.0,
                solve_label="cost_normalization.iteration_01.final_audit",
                stage="cost_normalization",
                sense="minimize",
                certified_lower_bound=upper,
                certified_upper_bound=upper,
                incumbent_objective=upper,
                relative_gap_to_incumbent=0.0,
            ),
            _event(
                "exact_cg_stage_completed",
                age_seconds=3,
                elapsed_seconds=22.0,
                stage="cost_normalization",
                certificate={
                    "valid": True,
                    "lower_bound": lower,
                    "upper_bound": upper,
                    "absolute_gap": upper - lower,
                    "relative_gap": relative_gap,
                    "relative_gap_to_feasible_incumbent": relative_gap,
                },
            ),
            _event(
                "candidate_failed",
                age_seconds=2,
                elapsed_seconds=23.0,
                requested_candidate_id="q_proxy_delta_0p0010",
            ),
        ],
    )
    (attempt / "cost_final_audit.log").write_text(
        f"""Solving report
  Primal bound      {upper}
  Dual bound        {upper}
  Gap               0%
  Nodes             0
""",
        encoding="utf-8",
    )

    status = build_status(
        tmp_path,
        now=NOW,
        process_probe=lambda _pid: False,
    )

    assert status["status"] == "failed"
    assert status["latest_incumbent"] == pytest.approx(upper)
    assert status["latest_lower_bound"] == pytest.approx(lower)
    assert status["latest_upper_bound"] == pytest.approx(upper)
    assert status["latest_gap"] == pytest.approx(relative_gap)


def test_new_native_log_has_creation_grace_period(tmp_path: Path) -> None:
    _write_progress(
        tmp_path / "attempt-001" / "progress.jsonl",
        [
            _event(
                "solve_started",
                age_seconds=2,
                elapsed_seconds=3.0,
                solve_label="candidate_01.screen_02",
                native_log="screen_02.log",
                sense="maximize",
            )
        ],
    )

    status = build_status(
        tmp_path,
        now=NOW,
        process_probe=lambda _pid: True,
    )

    assert status["native_log_path"] is None
    assert not any(
        "native solver log is missing" in item for item in status["warnings"]
    )


def test_missing_native_log_warns_after_creation_grace_period(tmp_path: Path) -> None:
    _write_progress(
        tmp_path / "attempt-001" / "progress.jsonl",
        [
            _event(
                "solve_started",
                age_seconds=40,
                elapsed_seconds=3.0,
                solve_label="candidate_01.screen_02",
                native_log="screen_02.log",
                sense="maximize",
            )
        ],
    )

    status = build_status(
        tmp_path,
        now=NOW,
        process_probe=lambda _pid: True,
    )

    assert any("native solver log is missing" in item for item in status["warnings"])


def test_monitor_does_not_change_progress_or_native_log(tmp_path: Path) -> None:
    attempt = tmp_path / "attempt-001"
    progress = attempt / "progress.jsonl"
    native = attempt / "solver.log"
    _write_progress(
        progress,
        [
            _event(
                "solve_started",
                age_seconds=2,
                elapsed_seconds=3.0,
                solve_label="candidate_01.master",
                native_log="solver.log",
                sense="minimize",
            ),
            _event(
                "heartbeat",
                age_seconds=1,
                elapsed_seconds=4.0,
                solve_label="candidate_01.master",
            ),
        ],
    )
    native.write_text(
        """Solving report
  Primal bound      105
  Dual bound        100
  Gap               5% (tolerance: 0.01%)
  Nodes             12
""",
        encoding="utf-8",
    )
    fixed_timestamp = 1_700_000_000_000_000_000
    os.utime(progress, ns=(fixed_timestamp, fixed_timestamp))
    os.utime(native, ns=(fixed_timestamp, fixed_timestamp))
    before = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in (progress, native)
    }

    status = build_status(
        tmp_path,
        now=NOW,
        process_probe=lambda _pid: True,
    )

    after = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in (progress, native)
    }
    assert after == before
    assert status["latest_incumbent"] == 105.0
    assert status["latest_lower_bound"] == 100.0
    assert status["latest_upper_bound"] == 105.0
    assert status["latest_gap"] == 0.05
    assert status["latest_nodes"] == 12


def test_cli_requires_explicit_log_root_and_prints_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 2

    _write_progress(
        tmp_path / "attempt-001" / "progress.jsonl",
        [_event("attempt_completed", age_seconds=1, elapsed_seconds=2.0)],
    )
    assert main(["--log-root", str(tmp_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "completed"
    assert payload["alive"] is False
