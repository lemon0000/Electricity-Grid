"""Tests for the RTS-GMLC CFE source-ablation adapter."""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from experiments import run_rq2_h2_temporal_cfe_source_ablation as runner

CONFIG = Path("configs/rq2_h2_temporal_cfe_source_ablation_rts24_v1.yaml")


def _config() -> dict:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def test_cfe_adapter_validates_profile_and_summary_contract():
    generator, summary = runner._validate_cfe_source(_config())

    assert generator["green_call_scale_mw"] == generator["data_center_demand_mw"]
    assert summary["schema"] == "rts_gmlc_hourly_cfe_deficit_v1"
    assert summary["hours"] == 8784
    assert summary["hourly_cfe_target"] == 1.0
    assert summary["security_certified"] is False


def test_cfe_adapter_rejects_rescaling_or_profile_drift():
    config = _config()
    config["generator"]["green_call_scale_mw"] = 249.0
    with pytest.raises(ValueError, match="green_call_scale_mw = D_DC"):
        runner._validate_cfe_source(config)

    config = _config()
    config["generator"]["green_cfe_metadata"]["profile_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="profile SHA-256 drifted"):
        runner._validate_cfe_source(config)


def test_corrected_provenance_removes_legacy_cluster_semantics():
    provenance = {
        "sources": {"green": "profile.csv"},
        "normalization": {"green": {"peak": 1.0, "split_fraction": None}},
        "trace_pairing": "independent_marginal_windows_from_different_clusters",
    }
    summary = {
        "hourly_cfe_target": 1.0,
        "formula": "formula",
    }

    corrected = runner._correct_provenance(copy.deepcopy(provenance), summary)

    assert corrected["green_call_source_mode"] == (
        "rts_gmlc_renewable_scarcity_absolute_mw"
    )
    assert corrected["trace_pairing"] == (
        "independent_marginal_windows_between_google_stress_and_rts_gmlc_cfe"
    )
    assert corrected["normalization"]["green"]["scale_equals_dc_demand_mw"] is True
