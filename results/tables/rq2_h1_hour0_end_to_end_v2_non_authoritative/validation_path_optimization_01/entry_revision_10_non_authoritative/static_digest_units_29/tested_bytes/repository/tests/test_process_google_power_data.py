import csv
import gzip
import hashlib
from pathlib import Path

import pytest
import yaml

from experiments.process_google_power_data import _domain_hour_means, run


UPSTREAM_ROOT = Path("data/raw/google_power_2019/2019/upstream")


def test_domain_hour_requires_all_twelve_valid_samples_and_sorts_time(tmp_path):
    path = tmp_path / "domain.csv.gz"
    rows = [
        {
            "time": str(index * 300_000_000),
            "measured_power_util": str(index),
            "bad_measurement_data": str(index == 3).lower(),
        }
        for index in reversed(range(24))
    ]
    with gzip.open(path, "wt", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    times, hourly = _domain_hour_means(
        path,
        metric="measured_power_util",
        quality_flag="bad_measurement_data",
        samples_per_hour=12,
    )

    assert times == sorted(times)
    assert hourly == [None, pytest.approx(17.5)]


@pytest.mark.skipif(
    not UPSTREAM_ROOT.exists(),
    reason="Run scripts/fetch_google_power_2019.ps1 to enable processing tests",
)
def test_google_power_processing_builds_a_source_bounded_hourly_shape(tmp_path):
    summary = run(
        Path("configs/google_power_2019.yaml"),
        output_directory=tmp_path,
    )

    assert summary["hours"] == 744
    assert summary["eligible_domains"] == 55
    assert summary["complete_domain_hours"] == 40896
    assert summary["full_window_domains"] == 38
    assert summary["minimum_complete_valid_domains_per_hour"] == 54
    assert summary["maximum_complete_valid_domains_per_hour"] == 55
    assert summary["normalization_uses_future_window_peak"]
    assert summary["normalization_allowed_use"] == (
        "fixed_replay_not_train_or_holdout_feature"
    )
    assert (
        summary["hourly_shape_sha256"]
        == "1089b409c06ad9a1ce1c0cfa9ceea4110a0b74c9a40cfe65e7614610f9f23931"
    )
    assert (
        summary["domain_quality_sha256"]
        == "709adfbf7d55ce2aa36a53ceeecaf4e5ac83fec9145ab2f26a72952163ee2c83"
    )
    assert (
        hashlib.sha256((tmp_path / "summary.json").read_bytes()).hexdigest()
        == "e281329a62cb6cfe693688eb9a0de05906955c51f3302fcf8593a5656f48068f"
    )
    assert not summary["capacity_weighted_aggregation"]
    assert not summary["imputation_used"]
    assert not summary["absolute_power_mw_available"]
    assert not summary["model_input_ready_without_separate_mw_mapping"]

    with (tmp_path / "hourly_shape.csv").open(
        "r", encoding="utf-8", newline=""
    ) as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 744
    assert rows[0]["relative_hour"] == "0"
    assert rows[-1]["relative_hour"] == "743"
    assert max(float(row["peak_normalized_unweighted_mean"]) for row in rows) == 1.0

    artifact_names = (
        "domain_quality.csv",
        "hourly_shape.csv",
        "summary.json",
        "SHA256SUMS",
    )
    before = {name: (tmp_path / name).read_bytes() for name in artifact_names}
    invalid_config = yaml.safe_load(
        Path("configs/google_power_2019.yaml").read_text(encoding="utf-8")
    )
    invalid_config["processing"]["expected_hourly_shape_sha256"] = "0" * 64
    invalid_path = tmp_path / "invalid-google.yaml"
    invalid_path.write_text(
        yaml.safe_dump(invalid_config, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="shape hash drifted"):
        run(invalid_path, output_directory=tmp_path)
    assert {name: (tmp_path / name).read_bytes() for name in artifact_names} == before
    assert not list(tmp_path.parent.glob(f".{tmp_path.name}.processing-*"))
