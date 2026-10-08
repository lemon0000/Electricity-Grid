import json
from pathlib import Path

import pytest

import experiments.audit_public_compute_supplements_v1 as audit


def test_downloaded_bundles_are_exactly_bound():
    google, google_hashes = audit._verify_bundle(audit.GOOGLE_ROOT)
    zeus, zeus_hashes = audit._verify_bundle(audit.ZEUS_ROOT)
    assert len(google_hashes) == 8
    assert len(zeus_hashes) == 9
    assert google["cell_bucket_inventory"]["objects"] == 15264
    assert zeus["commit"] == "f9db43227e1e5a3b4595bb4282f821890942b7bf"


def test_google_machine_events_preserve_unknown_capacity_and_mapping_scope():
    result = audit._audit_google_machine_events()
    assert result["rows"] == 49603
    assert result["machines"] == 12201
    assert result["time_zero"] == {
        "rows": 11392,
        "machines": 11392,
        "machines_with_multiple_rows": 0,
        "all_are_add_with_capacity": True,
        "interpretation": "pre_trace_snapshot_special_value_not_an_ordinary_timestamp",
    }
    assert result["capacity"]["rows_missing"] == 716
    assert result["capacity"]["missing_rows_that_are_first_nonzero_add"] == 716
    assert result["capacity"]["missing_rows_with_later_known_capacity"] == 716
    assert result["capacity"]["numeric_issue_counts"] == {}
    assert result["capacity"]["missing_intervals_must_remain_unknown"]
    assert result["missing_data_reason_presence"] == {"field_absent": 49603}
    assert result["mapping"]["cell_f_machines"] == 12203
    assert result["mapping"]["cell_f_mapped_machines_without_events"] == 2
    assert result["mapping"]["pdu17_mapped_machines"] == 1295
    assert result["mapping"]["pdu17_time_zero_snapshot_machines"] == 1221
    assert result["mapping"]["pdu17_time_zero_normalized_cpu_sum"] == "1220.5"
    assert not result["mapping"]["snapshot_is_complete_physical_capacity"]


def test_zeus_tables_preserve_failed_targets_and_single_power_measurements():
    result = audit._audit_zeus()
    assert result["train"]["rows"] == 3759
    assert result["train"]["dataset_network_pairs"] == 6
    assert result["train"]["configurations_with_fewer_than_4_distinct_runs"] == 6
    assert result["train"]["distinct_run_count_distribution"] == {"1": 2, "2": 2, "3": 2, "4": 5, "5": 35, "10": 17}
    assert result["train"]["target_epoch_sentinel_counts"] == {"nan": 849}
    assert not result["train"]["target_epoch_nan_interpretation_resolved"]
    assert result["train"]["invalid_nonpositive_or_nonfinite_core_numeric_rows"] == 0
    assert not result["train"]["target_epoch_is_business_deadline"]
    assert {gpu: table["rows"] for gpu, table in result["power"].items()} == {
        "a40": 453,
        "p100": 270,
        "rtx6000": 410,
        "v100": 476,
    }
    assert all(table["duplicate_configuration_rows"] == 0 for table in result["power"].values())
    assert all(table["invalid_nonpositive_or_nonfinite_numeric_values"] == 0 for table in result["power"].values())
    assert not result["power_measurements_are_repeated_samples"]
    assert not result["alibaba_mapping_is_observed_job_power_link"]


def test_parquet_candidates_are_transport_valid_but_not_content_verified():
    assert audit._parquet_magic(audit.GOOGLE_ROOT / "machine_events-000000000000.parquet.gz")
    assert audit._parquet_magic(audit.GOOGLE_ROOT / "instance_usage-000000000000.parquet.gz")


def test_real_summary_is_non_authoritative_and_no_overwrite(tmp_path):
    output = tmp_path / "audit" / "summary.json"
    summary = audit.run(output)
    assert json.loads(output.read_text(encoding="utf-8")) == summary
    assert summary["provenance"]["paid_queries"] == 0
    assert summary["provenance"]["solver_calls"] == 0
    assert summary["interpretation"]["google_machine_event_chronology_available"]
    assert not summary["interpretation"]["google_machine_capacity_complete"]
    assert not summary["interpretation"]["google_usage_pilot_content_verified"]
    assert not summary["interpretation"]["continuous_model_input_ready"]
    assert not summary["interpretation"]["formal_result"]
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        audit.run(output)


def test_bundle_hash_drift_fails_before_output(tmp_path, monkeypatch):
    original = audit._sha256

    def drift(path: Path) -> str:
        if path.name == "machine_events-000000000000.json.gz":
            return "0" * 64
        return original(path)

    monkeypatch.setattr(audit, "_sha256", drift)
    output = tmp_path / "audit" / "summary.json"
    with pytest.raises(RuntimeError, match="SHA-256 drifted"):
        audit.run(output)
    assert not output.parent.exists()
