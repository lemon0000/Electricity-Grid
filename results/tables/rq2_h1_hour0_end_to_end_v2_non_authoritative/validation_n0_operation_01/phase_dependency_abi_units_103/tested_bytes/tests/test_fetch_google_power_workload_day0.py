import csv
import gzip
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from experiments.fetch_google_power_workload_day0 import (
    _mapping_fingerprint,
    _run_dry_run,
    _validate_acquisition_budget,
    _validate_existing_output,
    _validate_job_query_parameters,
    _write_result,
)

HOURLY_FIELDS = [
    "record_type",
    "hour_index",
    "collection_type",
    "priority_tier",
    "observed_cpu_ncu_lower",
    "observed_cpu_ncu_upper",
    "observed_cpu_time_ncu_seconds_lower",
    "observed_cpu_time_ncu_seconds_upper",
    "observed_cpu_overlap_seconds",
    "missing_cpu_overlap_seconds",
    "cpu_conflict_overlap_seconds",
    "fragment_piece_count",
    "usage_group_count",
    "cpu_conflict_usage_group_count",
    "exact_duplicate_usage_group_count",
    "synthesized_cpu_time_ncu_seconds_lower",
    "synthesized_cpu_time_ncu_seconds_upper",
    "machine_event_time",
    "machine_id",
    "machine_event_type",
    "capacity_cpus",
    "machine_missing_data_reason",
    "audit_json",
]
TIERS = (
    "1_free",
    "2_beb",
    "3_mid",
    "4_production",
    "5_monitoring",
    "ambiguous",
    "unknown",
)


def _config(expected_bytes=123):
    return {
        "source": {"location": "US"},
        "parameters": {
            "cell": "f",
            "pdu": "pdu17",
            "window_start_us": 0,
            "window_end_us": 86_400_000_000,
        },
        "cost_gate": {
            "expected_dry_run_bytes": expected_bytes,
            "maximum_bytes_billed": expected_bytes,
            "monthly_scan_budget_bytes": 1_099_511_627_776,
        },
    }


class _DryRunClient:
    def __init__(self, total_bytes):
        self.total_bytes = total_bytes

    def query(self, _sql, *, job_config, location):
        assert job_config.dry_run
        assert location == "US"
        return SimpleNamespace(
            dry_run=True,
            total_bytes_processed=self.total_bytes,
        )


def test_dry_run_gate_rejects_scan_drift():
    with pytest.raises(RuntimeError, match="dry-run bytes drifted"):
        _run_dry_run(_DryRunClient(124), "SELECT 1", _config())


def test_three_stage_budget_is_rejected_before_paid_queries():
    config = _config()
    config["cost_gate"].update(
        expected_compact_dry_run_bytes=20,
        expected_hourly_dry_run_bytes=30,
        monthly_scan_budget_bytes=172,
    )

    with pytest.raises(RuntimeError, match="monthly scan budget"):
        _validate_acquisition_budget(config)


def test_mapping_fingerprint_is_sorted_and_cell_pdu_scoped(tmp_path):
    path = tmp_path / "mapping.csv.gz"
    with gzip.open(path, "wt", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=("machine_id", "pdu", "cell"),
        )
        writer.writeheader()
        writer.writerows(
            (
                {"machine_id": 9, "pdu": "pdu17", "cell": "f"},
                {"machine_id": 2, "pdu": "pdu17", "cell": "f"},
                {"machine_id": 9, "pdu": "pdu17", "cell": "f"},
                {"machine_id": 1, "pdu": "pdu16", "cell": "f"},
            )
        )

    count, digest = _mapping_fingerprint(path, cell="f", pdu="pdu17")

    assert count == 2
    assert digest == "ae31561f75a23a3cdd7b48350df50df10d672271e89f2c9defe8a816ac10c623"


def test_resume_gate_rejects_different_query_parameters():
    expected = [
        SimpleNamespace(name="cell", type_="STRING", value="f"),
        SimpleNamespace(name="pdu", type_="STRING", value="pdu17"),
    ]
    job = SimpleNamespace(
        query_parameters=[
            SimpleNamespace(name="cell", type_="STRING", value="f"),
            SimpleNamespace(name="pdu", type_="STRING", value="pdu16"),
        ]
    )

    with pytest.raises(RuntimeError, match="different query parameters"):
        _validate_job_query_parameters(job, expected)


@pytest.mark.skipif(
    not Path("data/raw/google_power_workload_2019/v1/upstream").exists(),
    reason="Run the guarded BigQuery day-0 acquisition to enable this test",
)
def test_existing_output_contract_matches_the_frozen_acquisition():
    config = yaml.safe_load(
        Path("configs/google_power_workload_day0.yaml").read_text(encoding="utf-8")
    )
    output_root = Path(config["source"]["output_directory"])
    metadata = json.loads(
        (output_root / "SOURCE_METADATA.json").read_text(encoding="utf-8")
    )

    _validate_existing_output(
        output_root,
        metadata,
        config,
        mapping_count=int(config["expected"]["mapping_machine_count"]),
        mapping_sha=config["expected"]["mapping_machine_ids_sha256"],
        extract_job_id="cb350a47-cfa1-449e-a4e5-f1cf1ec6a916",
        compact_job_id="004b5224-ae3b-40a9-904f-ddf1a4dc2ce3",
    )

    metadata["query_parameters"] = {
        **metadata["query_parameters"],
        "pdu": "pdu16",
    }
    with pytest.raises(RuntimeError, match="different parameters"):
        _validate_existing_output(
            output_root,
            metadata,
            config,
            mapping_count=int(config["expected"]["mapping_machine_count"]),
            mapping_sha=config["expected"]["mapping_machine_ids_sha256"],
            extract_job_id=None,
            compact_job_id=None,
        )


def test_result_writer_validates_and_writes_all_record_types(tmp_path):
    empty = {field: None for field in HOURLY_FIELDS}
    rows = []
    for hour in range(24):
        for collection_type in (0, 1):
            for tier in TIERS:
                rows.append(
                    {
                        **empty,
                        "record_type": "hourly_usage",
                        "hour_index": hour,
                        "collection_type": collection_type,
                        "priority_tier": tier,
                        "observed_cpu_ncu_lower": 0.5,
                        "observed_cpu_ncu_upper": 0.5,
                        "observed_cpu_time_ncu_seconds_lower": 1800.0,
                        "observed_cpu_time_ncu_seconds_upper": 1800.0,
                        "observed_cpu_overlap_seconds": 3600,
                        "missing_cpu_overlap_seconds": 0,
                        "cpu_conflict_overlap_seconds": 0,
                        "fragment_piece_count": 1,
                        "usage_group_count": 1,
                        "cpu_conflict_usage_group_count": 0,
                        "exact_duplicate_usage_group_count": 0,
                        "synthesized_cpu_time_ncu_seconds_lower": 0.0,
                        "synthesized_cpu_time_ncu_seconds_upper": 0.0,
                    }
                )
    rows.extend(
        (
            {
                **empty,
                "record_type": "machine_event",
                "machine_event_time": 0,
                "machine_id": 20,
                "machine_event_type": 1,
                "capacity_cpus": 1.0,
                "machine_missing_data_reason": 0,
            },
            {
                **empty,
                "record_type": "audit",
                "audit_json": '{"usage_quality":{},"machine_quality":{}}',
            },
        )
    )
    output = tmp_path / "records.csv.gz"

    summary = _write_result(
        output,
        rows,
        HOURLY_FIELDS,
        window_start_us=0,
        window_end_us=86_400_000_000,
    )

    assert summary["rows"] == 338
    assert summary["record_counts"] == {
        "audit": 1,
        "hourly_usage": 336,
        "machine_event": 1,
    }
    with gzip.open(output, "rt", encoding="utf-8", newline="") as source:
        assert len(list(csv.DictReader(source))) == 338


def test_result_writer_does_not_publish_inconsistent_hourly_cpu(tmp_path):
    row = {field: None for field in HOURLY_FIELDS}
    row.update(
        record_type="hourly_usage",
        hour_index=0,
        collection_type=0,
        priority_tier="1_free",
        observed_cpu_ncu_lower=1.0,
        observed_cpu_ncu_upper=1.0,
        observed_cpu_time_ncu_seconds_lower=1.0,
        observed_cpu_time_ncu_seconds_upper=1.0,
        observed_cpu_overlap_seconds=1,
        missing_cpu_overlap_seconds=0,
        cpu_conflict_overlap_seconds=0,
        fragment_piece_count=1,
        usage_group_count=1,
        cpu_conflict_usage_group_count=0,
        exact_duplicate_usage_group_count=0,
        synthesized_cpu_time_ncu_seconds_lower=0.0,
        synthesized_cpu_time_ncu_seconds_upper=0.0,
    )

    with pytest.raises(ValueError, match="CPU average and CPU-time"):
        _write_result(
            tmp_path / "invalid.csv.gz",
            [row],
            HOURLY_FIELDS,
            window_start_us=0,
            window_end_us=200,
        )


def test_result_writer_rejects_duplicate_hourly_keys(tmp_path):
    base = {field: None for field in HOURLY_FIELDS}
    base.update(
        record_type="hourly_usage",
        hour_index=0,
        collection_type=0,
        priority_tier="1_free",
        observed_cpu_ncu_lower=1.0,
        observed_cpu_ncu_upper=1.0,
        observed_cpu_time_ncu_seconds_lower=3600.0,
        observed_cpu_time_ncu_seconds_upper=3600.0,
        observed_cpu_overlap_seconds=3600,
        missing_cpu_overlap_seconds=0,
        cpu_conflict_overlap_seconds=0,
        fragment_piece_count=1,
        usage_group_count=1,
        cpu_conflict_usage_group_count=0,
        exact_duplicate_usage_group_count=0,
        synthesized_cpu_time_ncu_seconds_lower=0.0,
        synthesized_cpu_time_ncu_seconds_upper=0.0,
    )

    with pytest.raises(ValueError, match="Duplicate hourly usage key"):
        _write_result(
            tmp_path / "duplicate.csv.gz",
            [base, dict(base)],
            HOURLY_FIELDS,
            window_start_us=0,
            window_end_us=86_400_000_000,
        )
