from pathlib import Path

import pytest

from experiments.validate_google_power_data import run


UPSTREAM_ROOT = Path("data/raw/google_power_2019/2019/upstream")


pytestmark = pytest.mark.skipif(
    not UPSTREAM_ROOT.exists(),
    reason="Run scripts/fetch_google_power_2019.ps1 to enable source-data tests",
)


def test_google_power_data_is_complete_and_verified():
    summary = run(Path("configs/google_power_2019.yaml"), write_output=False)

    assert all(summary["checks"].values())
    assert summary["power_domains"] == 57
    assert summary["workload_linkable_power_domains"] == 55
    assert summary["power_only_mvpp_domains"] == 2
    assert summary["samples_per_domain"] == [8928]
    assert summary["compressed_bytes"] == 3254733
    assert (
        summary["object_manifest_sha256"]
        == "bf820bc974b76432f8aa4c1865336e20833ffd4e961accde6a49cd7ff4881ca4"
    )
    assert summary["mapping_rows"] == 96616
    assert summary["valid_measurement_rows"] == 508872
    assert summary["valid_production_rows"] == 392379
    assert len(summary["domain_quality"]) == 57
    assert summary["cell_scoped_machine_keys"] == 96614
    assert summary["multi_pdu_cell_machine_keys"] == 2
    assert not summary["evidence"]["absolute_power_mw_available"]
