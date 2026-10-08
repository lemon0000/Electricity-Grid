from __future__ import annotations

import csv
import gzip
import json
from decimal import Decimal, DivisionByZero, InvalidOperation, ROUND_DOWN, getcontext
from pathlib import Path

import pytest
import yaml

from experiments import process_google_power_workload_multiday_pair_v1 as target


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/google_power_workload_multiday_pair_v1.DRAFT.yaml"


@pytest.fixture(scope="module")
def paired(tmp_path_factory):
    first = tmp_path_factory.mktemp("google-month-pair-a") / "result"
    second = tmp_path_factory.mktemp("google-month-pair-b") / "result"
    context = getcontext()
    saved = context.copy()
    try:
        context.prec = 7
        context.rounding = ROUND_DOWN
        context.traps[DivisionByZero] = True
        context.traps[InvalidOperation] = True
        summary = target.run(CONFIG_PATH, first)
        target.run(CONFIG_PATH, second)
    finally:
        context.prec = saved.prec
        context.rounding = saved.rounding
        context.traps = saved.traps.copy()
    return summary, first, second


def _jsonl(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def test_real_sources_align_to_fixed_hour_grid(paired) -> None:
    summary, output, _ = paired
    assert summary["coverage"]["hours"] == 744
    assert summary["coverage"]["cpu_strata_rows"] == 10_416
    assert summary["coverage"]["power_samples"] == 8_928
    assert summary["coverage"]["capacity_rows"] == 744
    assert len(summary["coverage"]["raw_origin_24h_blocks"]) == 31
    assert summary["coverage"]["natural_calendar_days_identified"] is False
    assert summary["quality_audit"]["power_bad_flag_pair_counts"] == {
        "00": 6621,
        "01": 2307,
        "10": 0,
        "11": 0,
    }
    assert summary["quality_audit"]["hours_with_any_bad_production_flag"] == 194
    assert summary["quality_audit"]["hours_with_cpu_conflict_overlap"] == 711
    assert summary["quality_audit"]["hours_with_missing_cpu_overlap"] == 0
    assert summary["quality_audit"]["hours_with_unknown_tier_usage"] == 21
    assert summary["quality_audit"]["hours_with_unknown_active_capacity"] == 16
    assert summary["quality_audit"]["unknown_active_capacity_machine_seconds"] == "117.081411"
    assert summary["interpretation"]["unfiltered_alignment_available"] is True
    assert summary["interpretation"]["continuous_model_input_ready"] is False
    assert (output / "summary.json").is_file()


def test_output_rows_preserve_strata_flags_capacity_and_raw_boundaries(paired) -> None:
    _, output, _ = paired
    rows = list(_jsonl(output / "aligned_hourly.jsonl.gz"))
    assert len(rows) == 744
    assert rows[0]["raw_interval_start_us"] == 600_000_000
    assert rows[-1]["raw_interval_end_us"] == 2_679_000_000_000
    assert [row["hour_index"] for row in rows] == list(range(744))
    for row in rows:
        assert row["cpu"]["source_strata_count"] == 14
        assert len(row["cpu"]["strata"]) == 14
        assert row["power"]["sample_count"] == 12
        assert sum(row["power"]["bad_flag_pair_counts"].values()) == 12
        assert row["power"]["quality_filter_applied"] is False
        capacity = row["capacity"]
        assert (
            Decimal(capacity["known_active_machine_seconds"])
            + Decimal(capacity["unknown_active_machine_seconds"])
            + Decimal(capacity["inactive_machine_seconds"])
            == Decimal(capacity["mapped_machine_seconds"])
        )
        assert "cpu_capacity_ratio" not in row
        assert "headroom" not in row
    blocks = json.loads((output / "summary.json").read_text(encoding="utf-8"))["coverage"][
        "raw_origin_24h_blocks"
    ]
    assert blocks[0]["raw_interval_start_us"] == 600_000_000
    assert blocks[-1]["raw_interval_end_us"] == 2_679_000_000_000
    assert all(block["aligned_hours"] == 24 for block in blocks)
    assert all(block["natural_calendar_day_identified"] is False for block in blocks)


def test_serialized_outputs_are_ambient_context_independent(paired) -> None:
    first_summary, first, second = paired
    assert (first / "aligned_hourly.jsonl.gz").read_bytes() == (
        second / "aligned_hourly.jsonl.gz"
    ).read_bytes()
    assert (first / "summary.json").read_bytes() == (second / "summary.json").read_bytes()
    assert first_summary["output_bindings"]["aligned_hourly_sha256"] == target._sha256(
        first / "aligned_hourly.jsonl.gz"
    )


def _power_rows() -> list[dict]:
    return [
        {
            "raw_interval_start_us": target.WINDOW_START_US + index * target.POWER_STEP_US,
            "raw_interval_end_us": target.WINDOW_START_US + (index + 1) * target.POWER_STEP_US,
            "measured_power_util": str(index / 100),
            "production_power_util": str((index + 1) / 100),
            "bad_measurement_data": False,
            "bad_production_power_data": index == 11,
            "cell": "f",
            "pdu": "pdu17",
            "source_object": "cellf_pdu17.csv.gz",
            "trace_relative_start_us": index * target.POWER_STEP_US,
        }
        for index in range(12)
    ]


def test_power_kernel_is_order_independent_and_rejects_missing_duplicate_or_shifted() -> None:
    rows = _power_rows()
    assert target._power_hours(rows, hours=1) == target._power_hours(reversed(rows), hours=1)
    with pytest.raises(RuntimeError, match="missing or shifted"):
        target._power_hours(rows[:-1], hours=1)
    with pytest.raises(RuntimeError, match="Duplicate"):
        target._power_hours(rows + [rows[0]], hours=1)
    shifted = [dict(row) for row in rows]
    shifted[0]["raw_interval_start_us"] += 1
    with pytest.raises(RuntimeError, match="cadence"):
        target._power_hours(shifted, hours=1)
    extra = [dict(row) for row in rows]
    extra[0]["unexpected"] = 1
    with pytest.raises(RuntimeError, match="schema"):
        target._power_hours(extra, hours=1)


def _capacity_row(hour: int) -> dict:
    return {
        "hour_index": hour,
        "raw_interval_start_us": target.WINDOW_START_US + hour * target.HOUR_US,
        "raw_interval_end_us": target.WINDOW_START_US + (hour + 1) * target.HOUR_US,
        "mapped_machine_seconds": "4662000",
        "known_active_machine_seconds": "4661999",
        "unknown_active_machine_seconds": "1",
        "inactive_machine_seconds": "0",
        "known_active_normalized_cpu_seconds": "4661000",
        "known_active_normalized_memory_seconds": "2330500",
    }


def test_capacity_kernel_rejects_missing_duplicate_or_unbalanced() -> None:
    assert target._capacity_hours([_capacity_row(0)], hours=1)[0][
        "unknown_active_machine_seconds"
    ] == "1"
    with pytest.raises(RuntimeError, match="duplicated"):
        target._capacity_hours([_capacity_row(0), _capacity_row(0)], hours=1)
    with pytest.raises(RuntimeError, match="missing"):
        target._capacity_hours([], hours=1)
    bad = _capacity_row(0)
    bad["known_active_machine_seconds"] = "0"
    with pytest.raises(RuntimeError, match="do not balance"):
        target._capacity_hours([bad], hours=1)
    extra = _capacity_row(0)
    extra["unexpected"] = "0"
    with pytest.raises(RuntimeError, match="schema"):
        target._capacity_hours([extra], hours=1)


def test_cpu_reader_rejects_missing_or_duplicate_stratum(tmp_path: Path) -> None:
    source = ROOT / "data/raw/google_power_workload_2019/multiday_v1_non_authoritative/upstream/records.csv.gz"
    with gzip.open(source, "rt", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
        fields = rows[0].keys()
    for changed in (rows[:-2] + rows[-1:], rows[:-1] + [rows[0], rows[-1]]):
        path = tmp_path / f"cpu-{len(list(tmp_path.iterdir()))}.csv.gz"
        with gzip.open(path, "wt", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(changed)
        with pytest.raises(RuntimeError, match="missing or duplicated"):
            target._read_cpu(path)
    bad_fields = [field for field in fields if field != "audit_json"]
    bad_schema = tmp_path / "cpu-bad-schema.csv.gz"
    with gzip.open(bad_schema, "wt", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=bad_fields, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(RuntimeError, match="schema"):
        target._read_cpu(bad_schema)


def test_source_hash_drift_and_existing_output_fail_closed(tmp_path: Path, paired) -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config["source"]["power_sha256"] = "0" * 64
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    with pytest.raises(RuntimeError, match="Source hash drifted"):
        target.run(path, tmp_path / "new")
    with pytest.raises(RuntimeError, match="overwrite"):
        target.run(CONFIG_PATH, paired[1])


def test_interpretation_gate_drift_is_rejected(tmp_path: Path) -> None:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config["interpretation"]["headroom_computed"] = True
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    with pytest.raises(RuntimeError, match="interpretation"):
        target._load_config(path)
