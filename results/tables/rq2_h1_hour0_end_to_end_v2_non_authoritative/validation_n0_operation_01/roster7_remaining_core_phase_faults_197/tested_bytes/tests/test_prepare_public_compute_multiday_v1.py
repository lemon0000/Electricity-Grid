from __future__ import annotations

import gzip
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pytest

pytest.importorskip("pyarrow")

from experiments import prepare_public_compute_multiday_v1 as target


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonl(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    first = tmp_path_factory.mktemp("public-multiday-a") / "result"
    second = tmp_path_factory.mktemp("public-multiday-b") / "result"
    summary = target.run(first)
    target.run(second)
    return summary, first, second


def test_machine_formats_and_pdu17_hourly_balance(prepared):
    summary, output, _ = prepared
    assert summary["machine_events_format_equivalence"] == {
        "rows_each_format": 49603,
        "row_order_exact_equal": True,
        "content_multiset_equal": True,
        "json_sha256": "a4fd1c97ddda3d5f8e66e8542b317f4e214f7ec4b29130b2be67c5fcfa56fcbe",
        "parquet_sha256": "57b62825d86600762b8b44053e54e742753c2001bfd1c3eb95bde52673635d3c",
        "pyarrow_version": "23.0.1",
    }
    capacity = list(_jsonl(output / "pdu17_hourly_normalized_capacity.jsonl.gz"))
    assert len(capacity) == 744
    assert [row["hour_index"] for row in capacity] == list(range(744))
    assert all(row["mapped_machine_seconds"] == "4662000" for row in capacity)
    assert sum(Decimal(row["unknown_active_machine_seconds"]) for row in capacity) == Decimal("117.081411")
    assert summary["pdu17_hourly_capacity"]["missing_capacity_add_segments"] == 72
    assert summary["pdu17_hourly_capacity"]["invalid_state_transitions"] == 0
    assert summary["pdu17_hourly_capacity"]["missing_capacity_filled"] is False


def test_all_power_values_and_flags_are_retained(prepared):
    summary, output, _ = prepared
    power = summary["google_power"]
    assert power["domains"] == 57
    assert power["rows"] == 57 * 8928
    assert power["raw_interval"] == [600000000, 2679000000000]
    assert power["all_domains_continuous_complete_5_minute_grid"] is True
    assert power["quality_filter_applied"] is False
    assert power["flag_true_means_low_confidence_resolved"] is False
    rows = _jsonl(output / "google_power_57_domains_unfiltered.jsonl.gz")
    assert sum(1 for _ in rows) == 57 * 8928


def test_footer_probe_is_bounded_and_does_not_claim_complete_cpu(prepared):
    summary, _, _ = prepared
    audit = summary["usage_footer_audit"]
    assert audit["sampled_objects"] == 8
    assert audit["all_sampled_row_groups_unprunable_by_time_or_pdu17_range"] is True
    assert audit["required_columns_have_any_page_index_in_sample"] is False
    assert audit["supports_proof_for_all_12259_objects"] is False
    assert audit["complete_pdu17_usage_extracted"] is False
    assert 70_000_000_000 < audit["indicative_full_table_six_column_transfer_bytes"] < 75_000_000_000
    assert all(
        not group["prunable_by_full_trace_time_or_pdu17_machine_range_stats"]
        for item in audit["details"]
        for group in item["row_groups"]
    )


@pytest.mark.parametrize(
    ("start_min", "end_max", "machine_min", "machine_max", "expected"),
    [
        (50, 150, 1, 20, False),
        (0, 100, 1, 20, True),
        (200, 250, 1, 20, True),
        (50, 250, 20, 30, True),
        (None, None, None, None, False),
    ],
)
def test_interval_row_group_pruning_is_disjoint_only(start_min, end_max, machine_min, machine_max, expected):
    assert target._row_group_prunable(
        start_min=start_min,
        end_max=end_max,
        machine_min=machine_min,
        machine_max=machine_max,
        target_start=100,
        target_end=200,
        target_machines={5, 10},
    ) is expected


def test_zeus_join_and_operational_scope(prepared):
    summary, output, _ = prepared
    assert summary["zeus_four_gpu_power"]["rows_by_gpu"] == {
        "a40": 453,
        "p100": 270,
        "rtx6000": 410,
        "v100": 476,
    }
    rows = list(_jsonl(output / "zeus_four_gpu_power_performance.jsonl.gz"))
    assert len(rows) == 1609
    assert all(Decimal(row["derived_energy_per_epoch_joule"]) > 0 for row in rows)
    evidence = summary["operational_evidence"]
    assert evidence["disclosed_europe_window_local_clock"] == "17:00-21:00"
    assert evidence["system_design_completion_within_day_disclosed"] is True
    assert evidence["identifies_2019_cell_f_job_deadline"] is False
    assert evidence["authorized_as_model_parameter"] is False


def test_outputs_are_byte_stable_and_gates_remain_closed(prepared):
    summary, first, second = prepared
    for name in (*summary["output_files"], "summary.json"):
        assert _digest(first / name) == _digest(second / name)
    interpretation = summary["interpretation"]
    assert interpretation["all_power_source_values_and_flags_prepared"] is True
    assert interpretation["pdu17_normalized_capacity_time_integral_prepared"] is True
    assert interpretation["zeus_controlled_gpu_performance_prepared"] is True
    for gate in (
        "complete_pdu17_multiday_cpu_usage_prepared",
        "quality_flag_semantics_resolved",
        "absolute_power_mw_available",
        "observed_job_flexibility_available",
        "true_job_deadline_observed",
        "true_recovery_deadline_observed",
        "shared_flexibility_budget_observed",
        "continuous_model_input_ready",
        "formal_result",
        "paper_claim",
        "security_certified",
    ):
        assert interpretation[gate] is False


def test_refuses_overwrite_and_source_hash_drift(prepared, monkeypatch, tmp_path):
    _, output, _ = prepared
    with pytest.raises(FileExistsError):
        target.run(output)
    real_sha256 = target._sha256

    def drift(path):
        if Path(path) == target.MAPPING_PATH:
            return "0" * 64
        return real_sha256(Path(path))

    monkeypatch.setattr(target, "_sha256", drift)
    with pytest.raises(RuntimeError, match="Protected source drifted"):
        target.run(tmp_path / "must-not-exist")
    assert not (tmp_path / "must-not-exist").exists()
