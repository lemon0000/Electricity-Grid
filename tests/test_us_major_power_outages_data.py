from pathlib import Path

import pytest

from experiments.validate_us_major_power_outages_data import run


UPSTREAM_ROOT = Path("data/raw/us_major_power_outages/v1/upstream")


pytestmark = pytest.mark.skipif(
    not UPSTREAM_ROOT.exists(),
    reason="Run scripts/fetch_us_major_power_outages.ps1 to enable source-data tests",
)


def test_us_major_power_outage_source_rows_are_complete_and_source_verified():
    summary = run(
        Path("configs/us_major_power_outages.yaml"),
        write_output=False,
    )

    assert all(summary["checks"].values())
    assert summary["source_rows"] == 1534
    assert (summary["first_year"], summary["last_year"]) == (2000, 2016)
    assert summary["postal_jurisdiction_count"] == 50
    assert "DC" in summary["postal_jurisdictions"]
    assert "RI" not in summary["postal_jurisdictions"]
    assert summary["duplicate_candidate_event_groups"] == 10
    assert summary["duplicate_candidate_excess_rows"] == 13
    assert summary["complete_temporal_records"] == 1476
    assert summary["duration_mismatch_minutes"] == {"-60": 14, "60": 17}
    assert summary["zero_duration_timestamp_consistent_records"] == 78
    assert summary["negative_timestamp_duration_records"] == 0
    assert summary["zero_duration_cause_counts"]["intentional attack"] == 71
    assert summary["missing"]["DEMAND.LOSS.MW"] == 705
    assert summary["known_demand_loss_records"] == 829
    assert summary["positive_demand_loss_records"] == 633
    assert summary["evidence"]["event_selection_rules_preregistered"] is True
    assert not summary["evidence"]["independent_event_count_established"]
    assert not summary["evidence"]["unconditional_frequency_or_duration_inference_allowed"]
    assert not summary["evidence"]["rts_component_mapping_allowed"]
