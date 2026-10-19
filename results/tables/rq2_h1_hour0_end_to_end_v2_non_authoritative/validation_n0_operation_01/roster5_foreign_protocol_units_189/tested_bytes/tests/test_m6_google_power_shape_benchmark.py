import csv
import hashlib
from pathlib import Path

import pytest
import yaml

from experiments.build_m6_google_power_shape_benchmark import run

SHAPE_PATH = Path("data/processed/google_power_2019/v1/hourly_shape.csv")
FORMAL_OUTPUT = Path(
    "data/processed/model_inputs/m6_google_power_shape_no_flex_250mw_v1"
)


pytestmark = pytest.mark.skipif(
    not SHAPE_PATH.exists(),
    reason="Run experiments.process_google_power_data before this benchmark test",
)


def test_google_shape_enters_only_the_no_flex_m6_business_contract(tmp_path):
    summary = run(
        Path("configs/m6_google_power_shape_benchmark.yaml"),
        output_directory=tmp_path,
    )

    assert summary["model_business_input_contract_loaded"]
    assert summary["hours"] == 744
    assert summary["maximum_requested_demand_mw"] == pytest.approx(250.0)
    assert summary["minimum_requested_demand_mw"] == pytest.approx(216.647660719)
    assert (
        summary["business_chronology_sha256"]
        == "7c034fdf77381146c5633fcdef8ea2ba4f9e9f12366207e80b43cbb52ff0fee1"
    )
    assert (
        hashlib.sha256((tmp_path / "summary.json").read_bytes()).hexdigest()
        == "8a5d47118102675f59c3b537c4884398eb1ea0845a6a201ba1c75a333660d48d"
    )
    assert summary["flexible_demand_mw"] == 0.0
    assert summary["recoverable_flexible_mw"] == 0.0
    assert summary["evidence_status"] == "derived_benchmark"
    assert summary["requested_demand_semantics"] == (
        "scaled_realized_pdu_power_proxy_not_uncapped_request"
    )
    assert summary["physical_maximum_semantics"] == (
        "assumed_project_benchmark_peak_not_observed_capacity"
    )
    assert not summary["contract_semantics_available"]
    assert summary["normalization_allowed_use"] == (
        "fixed_replay_not_train_or_holdout_feature"
    )
    assert not summary["incident_chronology_available"]
    assert not summary["chronological_dispatch_request_built"]
    assert not summary["chronological_grid_dispatch_coupled"]
    assert not summary["security_certified"]

    with (tmp_path / "business_chronology.csv").open(
        "r", encoding="utf-8", newline=""
    ) as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 744
    assert {row["flexible_demand_mw"] for row in rows} == {"0"}
    assert {row["recoverable_flexible_mw"] for row in rows} == {"0"}

    artifact_names = (
        "business_chronology.csv",
        "recovery_parameters.json",
        "summary.json",
        "SHA256SUMS",
    )
    before = {name: (tmp_path / name).read_bytes() for name in artifact_names}
    invalid_config = yaml.safe_load(
        Path("configs/m6_google_power_shape_benchmark.yaml").read_text(encoding="utf-8")
    )
    invalid_config["expected"]["business_chronology_sha256"] = "0" * 64
    invalid_path = tmp_path / "invalid-hash.yaml"
    invalid_path.write_text(
        yaml.safe_dump(invalid_config, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="chronology hash drifted"):
        run(invalid_path, output_directory=tmp_path)
    assert {name: (tmp_path / name).read_bytes() for name in artifact_names} == before
    assert not list(tmp_path.parent.glob(f".{tmp_path.name}.processing-*"))


@pytest.mark.parametrize(
    ("section", "field", "value", "message"),
    (
        (
            "benchmark",
            "result_evidence_ceiling",
            "observed_site_security_certified",
            "evidence ceiling",
        ),
        (
            "source_shape",
            "source_time_semantics",
            "observed_utc_calendar",
            "source clock",
        ),
        (
            "mapping",
            "physical_maximum_semantics",
            "observed_pdu_capacity",
            "explicit assumption",
        ),
    ),
)
def test_google_benchmark_rejects_evidence_label_drift(
    tmp_path, section, field, value, message
):
    config = yaml.safe_load(
        Path("configs/m6_google_power_shape_benchmark.yaml").read_text(encoding="utf-8")
    )
    config[section][field] = value
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        run(path, output_directory=tmp_path / "output")


@pytest.mark.skipif(
    not (FORMAL_OUTPUT / "summary.json").exists(),
    reason="Build the formal Google no-flex benchmark artifacts first",
)
def test_formal_google_benchmark_artifacts_match_the_current_builder():
    assert (
        hashlib.sha256((FORMAL_OUTPUT / "summary.json").read_bytes()).hexdigest()
        == "8a5d47118102675f59c3b537c4884398eb1ea0845a6a201ba1c75a333660d48d"
    )
    for line in (FORMAL_OUTPUT / "SHA256SUMS").read_text(encoding="ascii").splitlines():
        expected, relative = line.split("  ", maxsplit=1)
        assert (
            hashlib.sha256((FORMAL_OUTPUT / relative).read_bytes()).hexdigest()
            == expected
        )
