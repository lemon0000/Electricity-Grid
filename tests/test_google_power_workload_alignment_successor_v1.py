import csv
import gzip
import hashlib
import subprocess
import sys
from decimal import ROUND_DOWN, Inexact, localcontext
from pathlib import Path

import pytest
import yaml

from experiments.process_google_power_workload_alignment_successor_v1 import (
    _aggregate_cpu_rows,
    _build_aligned_rows,
    _index_power_rows,
    _pair_csv_bytes,
    _publish_diagnostic,
    run,
)

HOUR_US = 3_600_000_000
CONFIG_PATH = Path("configs/google_power_workload_alignment_successor_v1.DRAFT.yaml")


def test_legacy_windows_reproduce_fixed_ten_minute_misalignment():
    config = yaml.safe_load(
        Path("configs/google_power_workload_day0.yaml").read_text(encoding="utf-8")
    )

    cpu_hour_zero = (
        int(config["parameters"]["window_start_us"]),
        HOUR_US,
    )
    power_hour_zero = (
        int(config["power_day0"]["source_time_offset_us"]),
        int(config["power_day0"]["source_time_offset_us"]) + HOUR_US,
    )

    assert cpu_hour_zero == (0, HOUR_US)
    assert power_hour_zero == (600_000_000, HOUR_US + 600_000_000)
    assert power_hour_zero[0] - cpu_hour_zero[0] == 600_000_000


def test_successor_rejects_the_partially_covered_raw_hour_zero(tmp_path):
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config["alignment"].update(
        common_raw_start_us=0,
        common_raw_end_us=HOUR_US,
        expected_complete_hours=1,
        expected_power_samples=12,
    )
    config_path = tmp_path / "partial-hour.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(RuntimeError, match="maximal complete raw-hour intersection"):
        run(config_path, output_directory=tmp_path / "output")


def test_source_indexing_is_order_independent_and_fail_closed():
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    source = config["source"]
    contract = config["source_contract"]
    with gzip.open(source["workload_records_path"], "rt", encoding="utf-8", newline="") as stream:
        workload_rows = list(csv.DictReader(stream))
    kwargs = {
        "expected_hours": range(contract["source_hour_start"], contract["source_hour_end_exclusive"]),
        "collection_types": tuple(contract["collection_types"]),
        "priority_tiers": tuple(contract["priority_tiers"]),
    }
    cpu_forward = _aggregate_cpu_rows(workload_rows, **kwargs)
    cpu_reverse = _aggregate_cpu_rows(reversed(workload_rows), **kwargs)
    assert cpu_forward == cpu_reverse

    with gzip.open(source["power_path"], "rt", encoding="utf-8", newline="") as stream:
        power_rows = list(csv.DictReader(stream))
    forward = _index_power_rows(power_rows, cell="f", pdu="pdu17")
    reverse = _index_power_rows(reversed(power_rows), cell="f", pdu="pdu17")
    assert forward == reverse
    cpu_forward.pop(-1)
    cpu_reverse.pop(-1)
    alignment = config["alignment"]
    build_kwargs = {
        "start_us": alignment["common_raw_start_us"],
        "end_us": alignment["common_raw_end_us"],
        "trace_start_us": alignment["trace_start_raw_us"],
        "step_us": alignment["power_step_us"],
        "decimal_places": config["serialization"]["measured_power_mean_decimal_places"],
    }
    forward_bytes = _pair_csv_bytes(_build_aligned_rows(cpu_forward, forward, **build_kwargs))
    reverse_bytes = _pair_csv_bytes(_build_aligned_rows(cpu_reverse, reverse, **build_kwargs))
    assert forward_bytes == reverse_bytes

    wrong = dict(power_rows[0], pdu="wrong")
    with pytest.raises(RuntimeError, match="different cell or PDU"):
        _index_power_rows([wrong], cell="f", pdu="pdu17")
    with pytest.raises(RuntimeError, match="Duplicate power timestamp"):
        _index_power_rows([power_rows[0], power_rows[0]], cell="f", pdu="pdu17")
    above_documented_range = dict(power_rows[0], measured_power_util="1.0001")
    with pytest.raises(RuntimeError, match=r"documented \[0,1\] range"):
        _index_power_rows([above_documented_range], cell="f", pdu="pdu17")


def test_real_successor_is_exactly_23_complete_hours_and_deterministic(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_summary = run(CONFIG_PATH, output_directory=first)
    with localcontext() as ambient:
        ambient.prec = 3
        ambient.rounding = ROUND_DOWN
        ambient.traps[Inexact] = True
        run(CONFIG_PATH, output_directory=second)

    for name in ("aligned_hourly_pair.csv", "summary.json"):
        assert (first / name).read_bytes() == (second / name).read_bytes()
    with (first / "aligned_hourly_pair.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))

    assert len(rows) == 23
    assert rows[0]["source_hour_index"] == "1"
    assert rows[0]["common_raw_start_us"] == "3600000000"
    assert rows[0]["trace_relative_start_us"] == "3000000000"
    assert rows[-1]["source_hour_index"] == "23"
    assert rows[-1]["common_raw_end_us"] == "86400000000"
    assert all(row["power_sample_count"] == "12" for row in rows)
    assert first_summary["complete_hours"] == 23
    assert first_summary["common_interval_duration_us"] == 23 * HOUR_US
    assert first_summary["aligned_power_samples"] == 276
    assert first_summary["trace_relative_start_minutes"] == 50
    assert first_summary["trace_relative_end_minutes"] == 1430
    assert first_summary["excluded_power_samples_before_common_interval"] == 10
    assert first_summary["excluded_power_samples_after_common_interval"] == 2
    assert not first_summary["power_quality_flag_semantics_resolved"]
    assert first_summary["power_unit"] == "normalized_pdu_utilization_ratio"
    assert first_summary["cpu_bounds_scope"] == "extracted_population_only"
    assert not first_summary["population_is_complete_pdu_workload"]
    assert not first_summary["absolute_power_mw_available"]
    assert not first_summary["flexibility_observed"]
    assert not first_summary["deadline_observed"]
    assert not first_summary["recovery_parameters_observed"]
    assert not first_summary["cpu_subhour_disaggregation_performed"]
    assert not first_summary["priority_strata_reconstructed"]
    assert first_summary["priority_evidence_remains_in_bound_source"]
    assert not first_summary["machine_capacity_reconstructed"]
    assert not first_summary["machine_capacity_completeness_resolved"]
    assert not first_summary["capacity_used_to_normalize_cpu"]
    assert not first_summary["complete_24h_pair"]
    assert not first_summary["model_input_ready"]
    assert first_summary["aligned_hourly_pair_sha256"] == hashlib.sha256(
        (first / "aligned_hourly_pair.csv").read_bytes()
    ).hexdigest()


def test_successor_rejects_source_hash_drift(tmp_path):
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config["source"]["workload_records_sha256"] = "0" * 64
    config_path = tmp_path / "drifted.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(RuntimeError, match="Input hash drifted for workload_records"):
        run(config_path, output_directory=tmp_path / "output")


@pytest.mark.parametrize(
    ("section", "field", "value"),
    (
        ("alignment", "power_step_us", 600_000_000),
        ("alignment", "trace_start_raw_us", 0),
        ("source_contract", "legacy_power_window_start_us", 900_000_000),
        ("source_contract", "legacy_power_window_end_us", 86_400_000_000),
    ),
)
def test_successor_rejects_source_clock_contract_drift(
    tmp_path, section, field, value
):
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config[section][field] = value
    config_path = tmp_path / f"drifted-{field}.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(RuntimeError, match="Google source clock contract drifted"):
        run(config_path, output_directory=tmp_path / "output")


def test_two_independent_processes_emit_identical_bytes(tmp_path):
    outputs = [tmp_path / "process-a", tmp_path / "process-b"]
    for output in outputs:
        subprocess.run(
            [
                sys.executable,
                "-B",
                "experiments/process_google_power_workload_alignment_successor_v1.py",
                "--config",
                str(CONFIG_PATH),
                "--output-dir",
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    for name in ("aligned_hourly_pair.csv", "summary.json"):
        assert (outputs[0] / name).read_bytes() == (outputs[1] / name).read_bytes()


def test_diagnostic_publication_cleans_partial_staging(tmp_path, monkeypatch):
    output = tmp_path / "diagnostic"
    original_write_bytes = Path.write_bytes

    def fail_summary(path: Path, payload: bytes) -> int:
        if path.name == "summary.json":
            raise OSError("injected summary write failure")
        return original_write_bytes(path, payload)

    monkeypatch.setattr(Path, "write_bytes", fail_summary)
    with pytest.raises(OSError, match="injected summary write failure"):
        _publish_diagnostic(
            output,
            {"pair.csv": b"pair", "summary.json": b"summary"},
        )

    assert not output.exists()
    assert not list(tmp_path.glob(".diagnostic.processing-*"))
