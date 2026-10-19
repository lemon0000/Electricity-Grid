import csv
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from experiments.run_rts_gmlc_day0_scuc import (
    _build_request,
    _load_business,
    _read_config,
)
from src.evaluation import EvidenceSource, IncidentChronology
from src.grid import load_rts_gmlc_chronological_data

CONFIG_PATH = Path("configs/rts_gmlc_google_day0_scuc.yaml")
FULL24_CONFIG_PATH = Path("configs/rts_gmlc_google_day0_full24h_scuc.yaml")
UPSTREAM_ROOT = Path("data/raw/rts_gmlc/v0.2.3/upstream")
FORMAL_OUTPUT = Path(
    "results/tables/rts_gmlc_google_day0_first6h_selected_n1_dc_scuc_v1"
)
FULL24_FORMAL_OUTPUT = Path(
    "results/tables/rts_gmlc_google_day0_full24h_selected_n1_dc_scuc_v1"
)


requires_upstream = pytest.mark.skipif(
    not UPSTREAM_ROOT.exists(),
    reason="Run scripts/fetch_rts_gmlc.ps1 before the native chronology tests",
)


def _empty_incidents():
    return IncidentChronology(
        schema="m6_incident_chronology_v1",
        incidents=(),
        source=EvidenceSource(
            dataset_id="empty_runner_test",
            source_kind="synthetic_sensitivity",
            citation="empty runner test incident window",
            version="test",
            sha256="0" * 64,
        ),
    )


@requires_upstream
def test_runner_request_keeps_grid_load_separate_from_the_no_flex_business():
    config = _read_config(CONFIG_PATH)
    data = load_rts_gmlc_chronological_data(UPSTREAM_ROOT)
    business = _load_business(config)
    business = replace(
        business,
        points=business.points[: config["model"]["horizon_hours"]],
    )
    request = _build_request(data, business, _empty_incidents(), config["model"])

    assert len(request.timestamps) == 6
    assert all(len(demand) == 73 for demand in request.system_demand_by_bus_mw)
    assert sum(request.system_demand_by_bus_mw[0].values()) == pytest.approx(
        sum(data.hourly_points[0].demand_by_bus_mw.values())
    )
    assert request.dc_requested_mw[0] == pytest.approx(173.104166666667)
    assert sum(request.system_demand_by_bus_mw[0].values()) == pytest.approx(
        3337.3318842
    )
    assert set(request.dc_call_limit_mw) == {0.0}
    assert set(request.dc_flexible_demand_mw) == {0.0}
    assert set(request.dc_recoverable_flexible_mw) == {0.0}
    assert set(request.recovery_headroom_mw) == {0.0}
    assert request.completed_periods == frozenset()
    disabled = {generator.uid for generator in data.generators if not generator.enabled}
    assert disabled == {
        "114_SYNC_COND_1",
        "212_CSP_1",
        "214_SYNC_COND_1",
        "313_STORAGE_1",
        "314_SYNC_COND_1",
    }
    assert all(
        not availability[uid]
        for availability in request.generator_availability
        for uid in disabled
    )


def test_runner_rejects_an_evidence_upgrade_before_solving(tmp_path):
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config["benchmark"]["security_certified"] = True
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="evidence contract drifted"):
        _read_config(path)


def test_runner_accepts_the_registered_full_24h_contract():
    config = _read_config(FULL24_CONFIG_PATH)

    assert config["model"]["horizon_hours"] == 24
    assert config["model"]["source_window"] == (
        "complete_day0_24_continuous_hours_fixed_replay"
    )
    assert config["benchmark"]["id"] == (
        "rts_gmlc_google_day0_full24h_selected_n1_dc_scuc_v1"
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("repository", "https://example.com/not-rts-gmlc"),
        ("release", "v0.2.2"),
        ("commit", "0" * 40),
    ),
)
def test_runner_rejects_grid_source_identity_drift(tmp_path, field, value):
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config["grid_source"][field] = value
    path = tmp_path / "invalid-grid-source.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="source identity drifted"):
        _read_config(path)


@pytest.mark.parametrize("field", ("repository", "release", "commit"))
def test_runner_rejects_missing_grid_source_identity(tmp_path, field):
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config["grid_source"].pop(field)
    path = tmp_path / "missing-grid-source.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="source identity drifted"):
        _read_config(path)


def test_runner_rejects_grid_source_manifest_identity_drift(tmp_path):
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config["grid_source"]["manifest_sha256"] = "0" * 64
    path = tmp_path / "invalid-grid-source-manifest.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="manifest identity drifted"):
        _read_config(path)


@pytest.mark.skipif(
    not (FORMAL_OUTPUT / "summary.json").exists(),
    reason="Run the formal native RTS-GMLC day-0 benchmark first",
)
def test_formal_rts_gmlc_day0_artifacts_match_the_frozen_config():
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    expected = config["expected"]["artifact_sha256"]
    expected_names = set(expected) | {"SHA256SUMS"}
    assert {path.name for path in FORMAL_OUTPUT.iterdir()} == expected_names
    for name, digest in expected.items():
        assert hashlib.sha256((FORMAL_OUTPUT / name).read_bytes()).hexdigest() == digest

    expected_manifest = "".join(
        f"{digest}  {name}\n" for name, digest in sorted(expected.items())
    )
    manifest_path = FORMAL_OUTPUT / "SHA256SUMS"
    assert manifest_path.read_text(encoding="ascii") == expected_manifest
    assert (
        hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        == config["expected"]["artifact_manifest_sha256"]
    )

    summary = json.loads((FORMAL_OUTPUT / "summary.json").read_text(encoding="utf-8"))
    assert summary["schema"] == config["benchmark"]["artifact_schema"]
    assert summary["evidence_status"] == config["benchmark"]["evidence_status"]
    assert (
        summary["result_evidence_ceiling"]
        == config["benchmark"]["result_evidence_ceiling"]
    )
    assert summary["grid_source_repository"] == config["grid_source"]["repository"]
    assert summary["grid_source_release"] == config["grid_source"]["release"]
    assert summary["grid_source_commit"] == config["grid_source"]["commit"]
    assert (
        summary["business_recovery_parameters_sha256"]
        == config["business_input"]["recovery_sha256"]
    )
    assert (
        summary["business_source_summary_sha256"]
        == config["business_input"]["summary_sha256"]
    )
    assert summary["completed_periods"] == []
    assert summary["security_states_per_hour_including_normal"] == 12
    assert summary["contingency_states_per_hour"] == 11
    assert summary["artifact_row_counts"] == {
        "generator_dispatch.csv": 948,
        "hourly_dispatch.csv": 6,
        "incident_chronology.csv": 0,
        "initial_state.csv": 158,
        "normal_branch_flows.csv": 720,
        "security_audit.csv": 72,
        "security_branch_flows.csv": 7920,
        "security_generator_dispatch.csv": 10428,
    }
    assert summary["empty_incident_chronology_source"]["dataset_id"] == (
        "rts_gmlc_day0_empty_incident_window_v1"
    )
    assert summary["empty_incident_chronology_source"]["source_kind"] == (
        "synthetic_sensitivity"
    )
    assert summary["empty_incident_chronology_source"]["version"] == "v1"

    with (FORMAL_OUTPUT / "hourly_dispatch.csv").open(
        "r", encoding="utf-8", newline=""
    ) as source:
        rows = list(csv.DictReader(source))
    zero_flexibility_fields = {
        "data_center_flexible_demand_mw",
        "data_center_recoverable_flexible_mw",
        "data_center_call_limit_mw",
        "data_center_recovery_headroom_mw",
        "data_center_grid_call_mw",
        "data_center_recovery_power_mw",
    }
    assert zero_flexibility_fields <= set(rows[0])
    assert {
        "native_grid_demand_mw",
        "data_center_requested_mw",
        "data_center_physical_maximum_mw",
        "data_center_connected_capacity_mw",
        "data_center_power_mw",
        "total_demand_mw",
        "generation_balance_residual_mw",
        "hvdc_dc1_flow_mw",
    } <= set(rows[0])
    assert summary["all_flexibility_fields_zero"] == all(
        float(row[field]) == 0.0 for row in rows for field in zero_flexibility_fields
    )
    for row in rows:
        assert float(row["total_demand_mw"]) == pytest.approx(
            float(row["native_grid_demand_mw"]) + float(row["data_center_power_mw"])
        )
        assert float(row["generation_balance_residual_mw"]) == pytest.approx(
            float(row["total_generation_mw"])
            - float(row["total_demand_mw"])
            - float(row["network_losses_mw"]),
            abs=1.0e-9,
        )


@pytest.mark.skipif(
    not (FULL24_FORMAL_OUTPUT / "summary.json").exists(),
    reason="Run the formal 24-hour native RTS-GMLC benchmark first",
)
def test_formal_full24h_artifacts_and_certificate_match_the_frozen_config():
    config = _read_config(FULL24_CONFIG_PATH)
    expected = config["expected"]["artifact_sha256"]
    assert {path.name for path in FULL24_FORMAL_OUTPUT.iterdir()} == set(expected) | {
        "SHA256SUMS"
    }
    for name, digest in expected.items():
        assert (
            hashlib.sha256((FULL24_FORMAL_OUTPUT / name).read_bytes()).hexdigest()
            == digest
        )

    expected_manifest = "".join(
        f"{digest}  {name}\n" for name, digest in sorted(expected.items())
    )
    manifest_path = FULL24_FORMAL_OUTPUT / "SHA256SUMS"
    assert manifest_path.read_text(encoding="ascii") == expected_manifest
    assert (
        hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        == config["expected"]["artifact_manifest_sha256"]
    )

    summary = json.loads(
        (FULL24_FORMAL_OUTPUT / "summary.json").read_text(encoding="utf-8")
    )
    assert summary["benchmark_id"] == config["benchmark"]["id"]
    assert summary["hours"] == 24
    assert summary["first_timestamp"] == "2020-01-01T00:00:00+00:00"
    assert summary["last_timestamp"] == "2020-01-01T23:00:00+00:00"
    assert summary["critical_branch_uids"] == config["expected"]["critical_branch_uids"]
    assert (
        summary["critical_generator_uids"]
        == config["expected"]["critical_generator_uids"]
    )
    assert summary["artifact_row_counts"] == {
        "generator_dispatch.csv": 3792,
        "hourly_dispatch.csv": 24,
        "incident_chronology.csv": 0,
        "initial_state.csv": 158,
        "normal_branch_flows.csv": 2880,
        "security_audit.csv": 288,
        "security_branch_flows.csv": 31680,
        "security_generator_dispatch.csv": 41712,
    }

    constraint_generation = summary["constraint_generation_audit"]
    assert constraint_generation["converged"]
    assert len(constraint_generation["iterations"]) == 3
    assert constraint_generation["verified_state_ids"] == (
        constraint_generation["pre_registered_state_ids"]
    )
    assert constraint_generation["certified_absolute_gap_usd"] <= (
        summary["scuc_audit"]["gap_tolerance_usd"] + 1.0e-6
    )
    assert summary["fixed_commitment_ed_audit"]["accepted"]
    assert summary["fixed_commitment_ed_audit"]["termination_condition"] == ("optimal")

    residual = summary["residual_audit"]
    maxima = (value for key, value in residual.items() if key.startswith("maximum_"))
    assert max(maxima) <= config["solver"]["tolerance_mw"]
    assert all(
        all(flags) for key, flags in residual.items() if key.endswith("_by_step")
    )
    assert not summary["full_n_minus_one"]
    assert not summary["ac_security"]
    assert not summary["security_certified"]
