import csv
import gzip
import hashlib
from pathlib import Path

import pytest
import yaml

from experiments.process_google_power_workload_day0 import (
    _build_capacity_hours,
    _build_power_hours,
    _publish_directory,
    _share_bounds,
    run,
)

RAW_ROOT = Path("data/raw/google_power_workload_2019/v1/upstream")


def test_priority_share_uses_crossed_subset_and_complement_bounds():
    lower, upper = _share_bounds(2.0, 4.0, 5.0, 9.0)

    assert lower == pytest.approx(2.0 / 7.0)
    assert upper == pytest.approx(4.0 / 7.0)
    assert _share_bounds(0.0, 0.0, 0.0, 0.0) == (None, None)


def test_machine_capacity_state_does_not_backfill_a_future_update():
    events = [
        {
            "machine_event_time": "0",
            "machine_id": "1",
            "machine_event_type": "1",
            "capacity_cpus": "2",
            "machine_missing_data_reason": "",
        },
        {
            "machine_event_time": "1800000000",
            "machine_id": "1",
            "machine_event_type": "2",
            "capacity_cpus": "",
            "machine_missing_data_reason": "",
        },
        {
            "machine_event_time": "3600000000",
            "machine_id": "1",
            "machine_event_type": "1",
            "capacity_cpus": "",
            "machine_missing_data_reason": "",
        },
        {
            "machine_event_time": "4500000000",
            "machine_id": "1",
            "machine_event_type": "3",
            "capacity_cpus": "4",
            "machine_missing_data_reason": "",
        },
    ]

    hours, summary = _build_capacity_hours(
        events,
        {1, 2},
        window_end_us=7_200_000_000,
    )

    assert hours[0]["active_machine_count_time_average"] == pytest.approx(0.5)
    assert hours[0]["known_machine_capacity_ncu_time_average"] == pytest.approx(1.0)
    assert hours[1]["unknown_capacity_machine_seconds"] == pytest.approx(900.0)
    assert hours[1]["known_machine_capacity_ncu_time_average"] == pytest.approx(3.0)
    assert not hours[1]["machine_capacity_complete"]
    assert summary["mapping_machines_without_events"] == 1
    assert summary["capacity_incomplete_hours"] == [1]


def test_machine_capacity_rejects_an_update_while_inactive():
    event = {
        "machine_event_time": "0",
        "machine_id": "1",
        "machine_event_type": "3",
        "capacity_cpus": "1",
        "machine_missing_data_reason": "",
    }

    with pytest.raises(RuntimeError, match="UPDATE occurred while.*inactive"):
        _build_capacity_hours([event], {1}, window_end_us=3_600_000_000)


def test_power_day_sorts_samples_and_rejects_bad_measurements(tmp_path):
    path = tmp_path / "power.csv.gz"
    rows = [
        {
            "time": str(600_000_000 + index * 300_000_000),
            "cell": "f",
            "pdu": "pdu17",
            "measured_power_util": str(0.5 + index / 1000),
            "production_power_util": "0.4",
            "bad_measurement_data": "false",
            "bad_production_power_data": "true",
        }
        for index in reversed(range(12))
    ]
    with gzip.open(path, "wt", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    mean_value = sum(float(row["measured_power_util"]) for row in rows) / 12
    fingerprint_payload = (
        f"0,600000000,3900000000,{mean_value:.12f}".rstrip("0").rstrip(".") + "\n"
    )
    config = {
        "source_time_offset_us": 600_000_000,
        "samples": 12,
        "hours": 1,
        "samples_per_hour": 12,
        "time_step_us": 300_000_000,
        "first_time_us": 600_000_000,
        "last_time_us": 3_900_000_000,
        "bad_measurement_rows": 0,
        "bad_production_rows": 12,
        "minimum_measured_power_util": 0.5,
        "maximum_measured_power_util": 0.511,
        "hourly_power_sha256": hashlib.sha256(
            fingerprint_payload.encode("ascii")
        ).hexdigest(),
    }

    hours, _fingerprint = _build_power_hours(
        path,
        config,
        cell="f",
        pdu="pdu17",
    )
    assert hours[0]["valid_samples"] == 12
    assert hours[0]["mean"] == pytest.approx(mean_value)

    rows[0]["bad_measurement_data"] = "true"
    with gzip.open(path, "wt", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(RuntimeError, match="measurement quality drifted"):
        _build_power_hours(path, config, cell="f", pdu="pdu17")


def test_directory_publish_rolls_back_if_the_swap_fails(tmp_path, monkeypatch):
    output_root = tmp_path / "output"
    staging = tmp_path / "staging"
    for root, value in ((output_root, "old"), (staging, "new")):
        root.mkdir()
        payload = root / "payload.txt"
        payload.write_text(value, encoding="ascii")
        digest = hashlib.sha256(payload.read_bytes()).hexdigest()
        (root / "SHA256SUMS").write_text(f"{digest}  payload.txt\n", encoding="ascii")
    original_replace = Path.replace
    failed = False

    def fail_new_directory_swap(path, target):
        nonlocal failed
        if path == staging and Path(target) == output_root and not failed:
            failed = True
            raise OSError("injected directory swap failure")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_new_directory_swap)

    with pytest.raises(OSError, match="injected directory swap failure"):
        _publish_directory(staging, output_root)
    assert (output_root / "payload.txt").read_text(encoding="ascii") == "old"
    assert not (tmp_path / ".output.previous").exists()


def test_directory_publish_accepts_a_precreated_empty_output(tmp_path):
    output_root = tmp_path / "output"
    staging = tmp_path / "staging"
    output_root.mkdir()
    staging.mkdir()
    payload = staging / "payload.txt"
    payload.write_text("new", encoding="ascii")
    digest = hashlib.sha256(payload.read_bytes()).hexdigest()
    (staging / "SHA256SUMS").write_text(f"{digest}  payload.txt\n", encoding="ascii")

    _publish_directory(staging, output_root)

    assert (output_root / "payload.txt").read_text(encoding="ascii") == "new"
    assert not (tmp_path / ".output.previous").exists()


@pytest.mark.skipif(
    not RAW_ROOT.exists(),
    reason="Run the guarded BigQuery day-0 acquisition to enable this test",
)
def test_real_day0_processing_is_bounded_and_atomic(tmp_path):
    config_path = Path("configs/google_power_workload_day0.yaml")
    output_root = tmp_path / "processed"
    summary = run(config_path, output_directory=output_root)

    assert summary["hours"] == 24
    assert summary["priority_rows"] == 168
    assert summary["power_valid_samples"] == 288
    assert summary["observed_cpu_time_ncu_seconds_lower"] == pytest.approx(
        65_620_667.38184452
    )
    assert summary["observed_cpu_time_ncu_seconds_upper"] == pytest.approx(
        65_620_667.50039005
    )
    assert summary["ambiguous_priority_cpu_time_ncu_seconds_lower"] == pytest.approx(
        99_678.1343436757
    )
    assert summary["unknown_priority_cpu_time_ncu_seconds_upper"] == 0.0
    assert summary["synthesized_priority_cpu_time_ncu_seconds_lower"] == pytest.approx(
        3_224_428.513876031
    )
    assert summary["capacity_incomplete_hours"] == [18, 19]
    assert summary["unknown_capacity_machine_seconds"] == pytest.approx(44.908767)
    assert summary["mapping_machines_without_events"] == 45
    assert not summary["population_is_complete_pdu_workload"]
    assert not summary["absolute_power_mw_available"]
    assert not summary["flexibility_observed"]
    assert not summary["model_input_ready"]

    with (output_root / "hourly_pair.csv").open(
        "r", encoding="utf-8", newline=""
    ) as source:
        assert len(list(csv.DictReader(source))) == 24
    with (output_root / "hourly_priority_usage.csv").open(
        "r", encoding="utf-8", newline=""
    ) as source:
        assert len(list(csv.DictReader(source))) == 168

    names = (
        "hourly_pair.csv",
        "hourly_priority_usage.csv",
        "summary.json",
        "SHA256SUMS",
    )
    before = {name: (output_root / name).read_bytes() for name in names}
    invalid = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    invalid["processing"]["expected_artifact_sha256"]["hourly_pair.csv"] = "0" * 64
    invalid_path = tmp_path / "invalid.yaml"
    invalid_path.write_text(yaml.safe_dump(invalid, sort_keys=False), encoding="utf-8")

    with pytest.raises(RuntimeError, match="artifact hashes drifted"):
        run(invalid_path, output_directory=output_root)
    assert {name: (output_root / name).read_bytes() for name in names} == before
    assert not list(tmp_path.glob(".processed.processing-*"))
