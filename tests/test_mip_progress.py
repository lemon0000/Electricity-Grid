from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from src.solvers.mip_progress import (
    JsonlProgressWriter,
    ProgressHeartbeat,
    certified_bound_interval,
    highs_runtime_options,
)


def test_certified_bound_interval_reports_actual_gap() -> None:
    interval = certified_bound_interval(9.5, 10.0)

    assert interval.lower_bound == 9.5
    assert interval.upper_bound == 10.0
    assert interval.absolute_gap == 0.5
    assert interval.relative_gap == 0.05


def test_certified_bound_interval_rejects_invalid_bounds() -> None:
    with pytest.raises(ValueError, match="finite"):
        certified_bound_interval(float("nan"), 1.0)
    with pytest.raises(ValueError, match="exceeds"):
        certified_bound_interval(2.0, 1.0)
    with pytest.raises(ValueError, match="exceeds"):
        certified_bound_interval(1.0 + 1.0e-15, 1.0)


def test_highs_runtime_options_include_native_incremental_log(tmp_path: Path) -> None:
    options = highs_runtime_options(
        mip_relative_gap=1.0e-4,
        threads=4,
        random_seed=0,
        feasibility_tolerance=1.0e-6,
        time_limit_seconds=120.0,
        log_file=tmp_path / "solver.log",
        mip_min_logging_interval_seconds=5.0,
    )

    assert options["threads"] == 4
    assert options["time_limit"] == 120.0
    assert options["log_to_console"] is False
    assert options["output_flag"] is True
    assert options["log_file"] == str((tmp_path / "solver.log").resolve())


def test_jsonl_progress_is_durable_and_refuses_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "progress.jsonl"
    writer = JsonlProgressWriter(
        path,
        run_id="attempt-001",
        preregistration_id="experiment-v3",
        input_contract_sha256="a" * 64,
    )

    writer.emit("solve_started", solve_ordinal=1)
    writer.emit("solve_finished", solve_ordinal=1, lower_bound=1.0, upper_bound=1.0)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    assert [row["event"] for row in rows] == ["solve_started", "solve_finished"]
    assert all(row["run_id"] == "attempt-001" for row in rows)
    with pytest.raises(FileExistsError):
        JsonlProgressWriter(
            path,
            run_id="attempt-002",
            preregistration_id="experiment-v3",
            input_contract_sha256="b" * 64,
        )


@pytest.mark.parametrize("reserved", ("run_id", "input_contract_sha256"))
def test_jsonl_progress_rejects_reserved_payload_fields(
    tmp_path: Path, reserved: str
) -> None:
    writer = JsonlProgressWriter(
        tmp_path / f"{reserved}.jsonl",
        run_id="attempt-001",
        preregistration_id="experiment-v3",
        input_contract_sha256="a" * 64,
    )

    with pytest.raises(ValueError, match="reserved"):
        writer.emit("solve_started", **{reserved: "overridden"})


def test_jsonl_progress_event_cannot_be_overridden(tmp_path: Path) -> None:
    writer = JsonlProgressWriter(
        tmp_path / "event.jsonl",
        run_id="attempt-001",
        preregistration_id="experiment-v3",
        input_contract_sha256="a" * 64,
    )

    with pytest.raises(TypeError, match="multiple values"):
        writer.emit("solve_started", event="overridden")


def test_progress_heartbeat_records_liveness(tmp_path: Path) -> None:
    path = tmp_path / "heartbeat.jsonl"
    writer = JsonlProgressWriter(
        path,
        run_id="attempt-001",
        preregistration_id="experiment-v3",
        input_contract_sha256="a" * 64,
    )

    with ProgressHeartbeat(
        writer,
        interval_seconds=0.01,
        payload={"stage": "joint_ac", "solve_ordinal": 2},
    ):
        time.sleep(0.035)

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows
    assert all(row["event"] == "heartbeat" for row in rows)
    assert all(row["stage"] == "joint_ac" for row in rows)
