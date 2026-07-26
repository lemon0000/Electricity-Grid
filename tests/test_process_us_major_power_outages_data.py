import csv
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from experiments.process_us_major_power_outages_data import run


CONFIG = Path("configs/us_major_power_outages.yaml")
UPSTREAM_ROOT = Path("data/raw/us_major_power_outages/v1/upstream")
FORMAL_SUMMARY = Path("results/tables/us_major_power_outages_data_summary.json")


pytestmark = pytest.mark.skipif(
    not UPSTREAM_ROOT.exists(),
    reason="Run scripts/fetch_us_major_power_outages.ps1 to enable source-data tests",
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_processing_writes_only_to_requested_temp_root(tmp_path: Path):
    formal_hash_before = _sha256(FORMAL_SUMMARY)
    manifest_hash_before = _sha256(UPSTREAM_ROOT / "SHA256SUMS")

    summary = run(CONFIG, output_root=tmp_path)

    assert summary["source_rows"] == 1534
    assert summary["evidence"]["event_selection_rules_preregistered"] is True
    assert summary["evidence"]["independent_event_count_established"] is False
    assert summary["evidence"]["unconditional_frequency_or_duration_inference_allowed"] is False
    assert summary["candidate_groups"] == 1521
    assert summary["duplicate_candidate_event_groups"] == 10
    assert summary["duplicate_candidate_rows"] == 23
    assert summary["duplicate_candidate_excess_rows"] == 13
    assert summary["cohorts"]["primary_duration"]["candidate_groups"] == 1385
    assert summary["cohorts"]["primary_duration"]["source_rows"] == 1398
    assert summary["cohorts"]["known_loss_sensitivity"]["candidate_groups"] == 751
    assert summary["cohorts"]["positive_loss_sensitivity"]["candidate_groups"] == 611
    assert summary["cohorts"]["zero_duration_sensitivity"]["candidate_groups"] == 1463
    assert summary["cohorts"]["detail_complete_sensitivity"]["candidate_groups"] == 949
    assert summary["cohorts"]["single_nerc_sensitivity"]["candidate_groups"] == 1383
    assert summary["cohorts"]["source_rows_sensitivity"] == {
        "unit": "source_row",
        "rule": "same_flags_without_candidate_deduplication",
        "primary_duration_rows": 1398,
        "known_loss_rows": 756,
        "positive_loss_rows": 614,
        "zero_duration_rows": 1476,
    }
    assert summary["intersections"] == {
        "complete_timed_known_loss_candidate_groups": 799,
        "complete_timed_positive_loss_candidate_groups": 615,
        "complete_sustained_known_loss_candidate_groups": 751,
        "complete_sustained_positive_loss_candidate_groups": 611,
    }

    output_files = summary["output_files"]
    expected_hashes = {
        "source_rows": "f8b30a82ffddd9db89b90d8542d1b1f9fddf80a2c42fb58211f9fb2b39db550f",
        "candidate_groups": "4a82c60d9f0aca22133d729356a95c0d0de3b0b0253427f405c381443fdf24df",
        "cohort_membership": "ab2b1c7c1005e9925881792704dd50b99c8c8cd5071575a560804eab51928c90",
    }
    for name in ("source_rows", "candidate_groups", "cohort_membership"):
        output = tmp_path / output_files[name]["path"]
        assert output.parent == tmp_path
        assert output.is_file()
        assert output.stat().st_size == output_files[name]["bytes"]
        assert _sha256(output) == output_files[name]["sha256"]
        assert output_files[name]["sha256"] == expected_hashes[name]
    processing_summary = tmp_path / summary["outputs"]["processing_summary"]
    assert processing_summary == tmp_path / "processing_summary.json"
    assert processing_summary.is_file()
    assert json.loads(processing_summary.read_text(encoding="utf-8"))["source_rows"] == 1534
    assert (
        _sha256(processing_summary)
        == "5aa5f1114d6cee5a5a4ef91e15bd3a146b34841e780bcb4278aef5089ce99611"
    )
    manifest_before = (tmp_path / "SHA256SUMS").read_bytes()
    artifacts_before = {
        path.name: path.read_bytes() for path in tmp_path.iterdir() if path.is_file()
    }
    invalid_config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    invalid_config["processing"]["expected_output_sha256"]["source_rows"] = (
        "0" * 64
    )
    invalid_path = tmp_path / "invalid-outage.yaml"
    invalid_path.write_text(
        yaml.safe_dump(invalid_config, sort_keys=False),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="source_rows hash drifted"):
        run(invalid_path, output_root=tmp_path)
    assert (tmp_path / "SHA256SUMS").read_bytes() == manifest_before
    assert {
        path.name: path.read_bytes()
        for path in tmp_path.iterdir()
        if path.is_file() and path != invalid_path
    } == artifacts_before
    assert not list(tmp_path.parent.glob(f".{tmp_path.name}.processing-*"))

    assert _sha256(FORMAL_SUMMARY) == formal_hash_before
    assert _sha256(UPSTREAM_ROOT / "SHA256SUMS") == manifest_hash_before


def test_processing_preserves_rows_and_candidate_aggregation(tmp_path: Path):
    summary = run(CONFIG, output_root=tmp_path)
    outputs = summary["outputs"]
    source_rows = _read_csv(tmp_path / outputs["source_rows"])
    candidate_groups = _read_csv(tmp_path / outputs["candidate_groups"])
    memberships = _read_csv(tmp_path / outputs["cohort_membership"])

    assert len(source_rows) == 1534
    assert len(candidate_groups) == 1521
    assert len(memberships) == 1521
    assert len({row["OBS"] for row in source_rows}) == 1534
    assert all(row["candidate_group_id"] for row in source_rows)
    assert all(row["candidate_group_id"] for row in candidate_groups)
    assert {row["candidate_group_id"] for row in candidate_groups} == {
        row["candidate_group_id"] for row in memberships
    }

    la_group = next(
        row
        for row in candidate_groups
        if row["postal_code"] == "LA"
        and row["cause_category"] == "public appeal"
        and row["candidate_group_size"] == "4"
    )
    assert la_group["nerc_regions"] == "SERC;SPP"
    assert la_group["multi_nerc"] == "true"
    assert la_group["demand_loss_max_mw"] == "__MISSING__"
    assert la_group["customers_max"] == "__MISSING__"

    tx_group = next(
        row
        for row in candidate_groups
        if row["postal_code"] == "TX"
        and row["cause_category"] == "severe weather"
        and row["demand_loss_max_mw"] == "8087"
    )
    assert tx_group["candidate_group_size"] == "2"
    assert tx_group["demand_loss_min_mw"] == "8087"
    assert tx_group["source_obs_ids"] == "203;269"

    ohio_group = next(
        row
        for row in candidate_groups
        if row["postal_code"] == "OH"
        and row["cause_category"] == "severe weather"
        and row["source_obs_ids"] == "689;691"
    )
    assert ohio_group["demand_loss_max_mw"] == "392"
    assert ohio_group["demand_loss_min_mw"] == "177"
    assert ohio_group["customers_max"] == "281000"
    assert ohio_group["customers_min"] == "127000"

    primary_members = [
        row for row in memberships if row["primary_duration_member"] == "true"
    ]
    assert len(primary_members) == 1385
    assert sum(int(row["source_rows_primary_duration"]) for row in primary_members) == 1398
    assert all(
        row["source_rows_primary_duration"] == row["candidate_group_size"]
        for row in primary_members
    )


def test_processing_cli_contract_is_fail_closed_for_frozen_counts(tmp_path: Path):
    summary = run(CONFIG, output_root=tmp_path)
    assert summary["forbidden_inferences"] == [
        "independent_event_count",
        "unconditional_annual_outage_frequency",
        "unconditional_duration_distribution",
        "component_outage_rate",
        "rts_component_mapping",
        "same_clock_business_or_contract_failure",
    ]
    assert summary["duration_mismatch_minutes"] == {"-60": 14, "60": 17}
    assert summary["zero_duration_records"] == 78
    assert summary["zero_duration_timestamp_consistent_records"] == 78
