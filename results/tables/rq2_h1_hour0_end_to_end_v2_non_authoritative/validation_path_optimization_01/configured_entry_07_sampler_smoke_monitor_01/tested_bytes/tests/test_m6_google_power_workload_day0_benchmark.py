import csv
import hashlib
from pathlib import Path

import pytest
import yaml

from experiments.build_m6_google_power_workload_day0_benchmark import run

PAIR_PATH = Path("data/processed/google_power_workload_2019/v1/hourly_pair.csv")
CONFIG_PATH = Path("configs/m6_google_power_workload_day0_benchmark.yaml")
FORMAL_OUTPUT = Path(
    "data/processed/model_inputs/m6_google_power_workload_day0_no_flex_250mw_v1"
)


pytestmark = pytest.mark.skipif(
    not PAIR_PATH.exists(),
    reason="Run the paired Google day-0 processor before this benchmark test",
)


def test_day0_pair_enters_only_the_no_flex_m6_business_contract(tmp_path):
    summary = run(CONFIG_PATH, output_directory=tmp_path)

    assert summary["model_business_input_contract_loaded"]
    assert summary["hours"] == 24
    assert summary["assumed_reference_capacity_mw"] == 250.0
    assert summary["minimum_requested_demand_mw"] == pytest.approx(172.770833333333)
    assert summary["maximum_requested_demand_mw"] == pytest.approx(189.729166666667)
    assert summary["flexible_demand_mw"] == 0.0
    assert summary["recoverable_flexible_mw"] == 0.0
    assert summary["recovery_headroom_mw"] == 0.0
    assert summary["evidence_status"] == "derived_benchmark"
    assert not summary["assumed_reference_capacity_observed"]
    assert not summary["candidate_proxy_used_as_flexibility"]
    assert not summary["cpu_share_mapped_to_power"]
    assert summary["capacity_incomplete_hours"] == [18, 19]
    assert not summary["full_m6_model_input_ready"]
    assert not summary["incident_chronology_available"]
    assert not summary["chronological_dispatch_request_built"]
    assert not summary["chronological_grid_dispatch_coupled"]
    assert not summary["security_certified"]

    with (tmp_path / "business_chronology.csv").open(
        "r", encoding="utf-8", newline=""
    ) as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 24
    assert float(rows[0]["requested_demand_mw"]) == pytest.approx(173.104166666667)
    assert float(rows[-1]["requested_demand_mw"]) == pytest.approx(183.0)
    assert {row["flexible_demand_mw"] for row in rows} == {"0"}
    assert {row["recoverable_flexible_mw"] for row in rows} == {"0"}
    assert {row["recovery_headroom_mw"] for row in rows} == {"0"}

    with (tmp_path / "candidate_proxy_audit.csv").open(
        "r", encoding="utf-8", newline=""
    ) as source:
        audit_rows = list(csv.DictReader(source))
    assert len(audit_rows) == 24
    assert {row["candidate_proxy_used_as_flexibility"] for row in audit_rows} == {
        "false"
    }
    incomplete = [
        int(row["hour_index"])
        for row in audit_rows
        if row["machine_capacity_complete"] == "false"
    ]
    assert incomplete == [18, 19]

    artifact_names = (
        "business_chronology.csv",
        "candidate_proxy_audit.csv",
        "recovery_parameters.json",
        "summary.json",
        "SHA256SUMS",
    )
    before = {name: (tmp_path / name).read_bytes() for name in artifact_names}
    invalid = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    invalid["expected"]["artifact_sha256"]["summary.json"] = "0" * 64
    invalid_path = tmp_path.parent / "invalid-day0-benchmark.yaml"
    invalid_path.write_text(yaml.safe_dump(invalid, sort_keys=False), encoding="utf-8")

    with pytest.raises(RuntimeError, match="artifact hashes drifted"):
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
            "evidence contract",
        ),
        (
            "mapping",
            "assumed_reference_capacity_observed",
            True,
            "reference capacity is not observed",
        ),
        (
            "mapping",
            "assumed_reference_capacity_mw",
            249.0,
            "must match the 250 MW benchmark ID",
        ),
        (
            "candidate_proxy",
            "candidate_proxy_used_as_flexibility",
            True,
            "cannot be upgraded to flexibility",
        ),
    ),
)
def test_day0_benchmark_rejects_evidence_label_drift(
    tmp_path, section, field, value, message
):
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config[section][field] = value
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        run(path, output_directory=tmp_path / "output")


@pytest.mark.skipif(
    not (FORMAL_OUTPUT / "summary.json").exists(),
    reason="Build the formal paired Google day-0 benchmark artifacts first",
)
def test_formal_day0_benchmark_artifacts_match_the_current_builder():
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    expected = config["expected"]["artifact_sha256"]
    for name, digest in expected.items():
        assert hashlib.sha256((FORMAL_OUTPUT / name).read_bytes()).hexdigest() == digest
