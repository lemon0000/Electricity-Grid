"""Integrity checks for the unified RQ2 data-readiness report."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experiments.build_rq2_data_readiness import (
    _validate_gate_logic,
    _verify_package,
)

PACKAGE = Path("data/processed/model_inputs/rq2_data_readiness_v2")
PREDECESSOR = Path("data/processed/model_inputs/rq2_data_readiness_v1")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_readiness_manifest_and_package_inventory():
    manifest = json.loads((PACKAGE / "SHA256SUMS.json").read_text(encoding="utf-8"))
    report = json.loads(
        (PACKAGE / "data_readiness.json").read_text(encoding="utf-8")
    )

    assert all(_sha256(PACKAGE / name) == digest for name, digest in manifest.items())
    assert report["schema"] == "rq2_data_readiness_v2"
    assert set(report["packages"]) == {
        "alibaba_gpu_telemetry",
        "alibaba_job_execution_envelopes",
        "nlr_genai_power_profiles",
        "rts_gmlc_cfe_deficit",
        "rts_gmlc_joint_data",
        "wattgpu_power_reference",
    }
    assert {
        name: source["entries"]
        for name, source in report["source_manifests"].items()
    } == {
        "alibaba_gpu_2020": 12,
        "alibaba_gpu_2020_telemetry": 4,
        "nlr_genai_power_2026": 1,
        "rts_gmlc": 25,
        "wattgpu_2026": 8,
    }
    assert report["config_sha256"] == _sha256(
        Path("configs/rq2_data_readiness_v2.yaml")
    )
    assert report["implementation_sha256"] == _sha256(
        Path("experiments/build_rq2_data_readiness.py")
    )
    assert report["predecessor"] == {
        "manifest_path": (
            "data/processed/model_inputs/rq2_data_readiness_v1/SHA256SUMS.json"
        ),
        "manifest_sha256": _sha256(PREDECESSOR / "SHA256SUMS.json"),
        "schema": "rq2_data_readiness_v1",
        "status": "superseded_by_live_provenance_validation",
    }


def test_all_package_provenance_hashes_match_live_files():
    report = json.loads(
        (PACKAGE / "data_readiness.json").read_text(encoding="utf-8")
    )
    observed_keys = set()
    for package_name, package in report["packages"].items():
        assert package["live_provenance"]
        for summary_key, provenance in package["live_provenance"].items():
            observed_keys.add((package_name, summary_key))
            assert _sha256(Path(provenance["path"])) == provenance["sha256"]
    assert (
        "rts_gmlc_cfe_deficit",
        "derivation_module_sha256",
    ) in observed_keys
    assert (
        "rts_gmlc_joint_data",
        "reliability_module_sha256",
    ) in observed_keys


def test_package_verifier_rejects_live_provenance_drift(tmp_path):
    live_file = tmp_path / "implementation.py"
    live_file.write_text("current implementation\n", encoding="utf-8")
    summary = {
        "schema": "test_schema",
        "implementation_sha256": "0" * 64,
    }
    summary_path = tmp_path / "summary.json"
    summary_path.write_text(json.dumps(summary) + "\n", encoding="utf-8")
    manifest = {"summary.json": _sha256(summary_path)}
    manifest_path = tmp_path / "SHA256SUMS.json"
    manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="package provenance drifted"):
        _verify_package(
            "test",
            {
                "directory": str(tmp_path),
                "manifest_sha256": _sha256(manifest_path),
                "expected_schema": "test_schema",
                "live_provenance": {
                    "implementation_sha256": str(live_file),
                },
            },
        )


def test_readiness_gates_do_not_overstate_available_evidence():
    report = json.loads(
        (PACKAGE / "data_readiness.json").read_text(encoding="utf-8")
    )
    gates = report["gates"]

    assert gates["source_archives_verified"]
    assert gates["job_execution_envelopes_ready"]
    assert gates["observed_gpu_utilization_covariate_ready"]
    assert gates["synchronized_grid_cfe_reliability_benchmark_ready"]
    assert gates["measured_power_calibration_reference_ready"]
    assert gates["t4_hardware_overlap_power_reference_ready"]
    assert not gates["direct_job_to_power_mapping_ready"]
    assert not gates["flexibility_contract_parameters_ready"]
    assert not gates["empirical_joint_distribution_ready"]
    assert not gates["allocated_cfe_portfolio_ready"]
    assert not gates["outage_to_grid_need_dispatch_ready"]
    assert not gates["full_rq2_experiment_input_ready"]
    assert not gates["formal_experiment_authorized"]


def test_high_risk_gates_cannot_be_enabled_by_configuration():
    report = json.loads(
        (PACKAGE / "data_readiness.json").read_text(encoding="utf-8")
    )
    packages = {
        name: {
            "summary": json.loads(
                (
                    Path(package["directory"]) / "summary.json"
                ).read_text(encoding="utf-8")
            )
        }
        for name, package in report["packages"].items()
    }
    gates = dict(report["gates"])
    gates["direct_job_to_power_mapping_ready"] = True

    with pytest.raises(ValueError, match="must remain false"):
        _validate_gate_logic(packages, gates)
