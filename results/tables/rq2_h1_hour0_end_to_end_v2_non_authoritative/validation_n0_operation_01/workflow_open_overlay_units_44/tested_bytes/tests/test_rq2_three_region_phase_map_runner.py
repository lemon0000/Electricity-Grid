"""End-to-end test for the local RQ2 three-region phase-map runner."""

from __future__ import annotations

import hashlib
import json
from csv import DictReader
from pathlib import Path
from types import SimpleNamespace

import yaml

from experiments import run_rq2_three_region_phase_map as runner

BASE_CONFIG = Path("configs/rq2_three_region_phase_map_v1.yaml")
PREREGISTRATION = Path("configs/rq2_three_region_phase_map_preregistration_v1.yaml")


def test_phase_map_runner_publishes_one_hash_bound_cell(tmp_path: Path):
    config = yaml.safe_load(BASE_CONFIG.read_text(encoding="utf-8"))
    config["evaluation"]["id"] = "phase_map_test"
    config["evaluation"]["parameter_status"] = "explicit_test_config"
    config["evaluation"]["enforce_preregistration"] = False
    config["design"]["expected_unique_cell_count"] = 1
    config["design"]["n_train"] = 2
    config["design"]["n_holdout"] = 2
    config["design"]["families"] = [
        {
            "name": "test",
            "poi_buses": [8],
            "network_methods": ["minimum_curtailment"],
            "hourly_cfe_targets": [0.7],
            "threshold_labels": ["q90"],
            "business_recovery_headroom_mw": [40.0],
            "max_flexibility_budget_mw": [150.0],
            "seeds": [20260822],
        }
    ]
    output = tmp_path / "result"
    config["output"]["directory"] = str(output)
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    summary = runner.run(config_path)

    assert summary["published_cell_count"] == 1
    assert summary["gate_passed"]
    assert sum(summary["region_counts"].values()) == 1
    manifest = json.loads((output / "SHA256SUMS.json").read_text(encoding="utf-8"))
    assert all(
        hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
        for name, digest in manifest.items()
    )
    with (output / "cells.csv").open(encoding="utf-8", newline="") as handle:
        row = next(DictReader(handle))
    assert row["correct_training_termination_condition"] == "optimal"
    assert row["b6_training_termination_condition"] == "optimal"
    assert row["correct_training_proven_infeasible"] == "False"
    assert row["b6_training_proven_infeasible"] == "False"


def test_network_derivation_failure_is_published_as_unresolved(
    tmp_path: Path, monkeypatch
):
    config = yaml.safe_load(BASE_CONFIG.read_text(encoding="utf-8"))
    config["evaluation"]["id"] = "phase_map_network_failure_test"
    config["evaluation"]["parameter_status"] = "explicit_test_config"
    config["evaluation"]["enforce_preregistration"] = False
    config["design"]["expected_unique_cell_count"] = 1
    config["design"]["families"] = [
        {
            "name": "test",
            "poi_buses": [8],
            "network_methods": ["minimum_curtailment"],
            "hourly_cfe_targets": [0.7],
            "threshold_labels": ["q90"],
            "business_recovery_headroom_mw": [40.0],
            "max_flexibility_budget_mw": [150.0],
            "seeds": [20260822],
        }
    ]
    output = tmp_path / "failed"
    config["output"]["directory"] = str(output)
    config_path = tmp_path / "failure.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    failed = SimpleNamespace(
        feasible=False,
        proven_infeasible=False,
        grid_need_mw=None,
        critical_state=None,
        direct_physical_dispatch_witness=False,
        base_termination_condition="optimal",
        base_solver_status="ok",
        state_results={
            "branch_11_sustained": SimpleNamespace(
                feasible=False,
                termination_condition="maxTimeLimit",
                solver_status="aborted",
                proven_infeasible=False,
            )
        },
    )
    monkeypatch.setattr(runner, "derive_network_grid_need", lambda _: failed)

    summary = runner.run(config_path)

    assert not summary["gate_passed"]
    assert summary["published_cell_count"] == 1
    assert summary["region_counts"]["unresolved"] == 1
    with (output / "cells.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["region"] == "unresolved"
    assert rows[0]["region_reason"] == (
        "network_derivation_branch_11_sustained:maxTimeLimit"
    )


def test_phase_map_config_expands_to_frozen_cell_count():
    config = yaml.safe_load(BASE_CONFIG.read_text(encoding="utf-8"))
    grid = runner.load_peak_normalized_shape_from_csv(
        Path(config["sources"]["grid"]["path"]),
        column=config["sources"]["grid"]["column"],
        name="grid",
        split_fraction=config["sources"]["split_fraction"],
        source="test",
    )
    thresholds = runner._thresholds(
        config["design"],
        grid_values=grid.values,
        split_fraction=config["sources"]["split_fraction"],
    )

    cells = runner._expand_cells(config["design"], thresholds)

    assert len(cells) == config["design"]["expected_unique_cell_count"] == 70


def test_phase_map_preregistration_hashes_are_current():
    prereg = yaml.safe_load(PREREGISTRATION.read_text(encoding="utf-8"))
    paths = {
        "config_sha256": BASE_CONFIG,
        "runner_sha256": Path("experiments/run_rq2_three_region_phase_map.py"),
        "classifier_sha256": Path("src/evaluation/rq2_phase_regions.py"),
        "scenario_builder_sha256": Path("src/scenarios/rq2_phase_map.py"),
        "cfe_derivation_sha256": Path("src/scenarios/rts_gmlc_cfe_deficit.py"),
        "temporal_holdout_sha256": Path("src/evaluation/temporal_economic_holdout.py"),
        "temporal_model_sha256": Path("src/models/economic_temporal_stochastic.py"),
        "network_grid_need_sha256": Path("src/grid/network_grid_need.py"),
        "temporal_runner_helpers_sha256": Path(
            "experiments/run_rq2_l5_economic_temporal_network.py"
        ),
        "trace_loader_sha256": Path("src/scenarios/trace_scenario_generator.py"),
        "flexibility_envelope_sha256": Path("src/evaluation/flexibility_envelope.py"),
        "service_risk_sha256": Path("src/evaluation/service_risk.py"),
        "rts24_sha256": Path("src/grid/rts24.py"),
        "dc_opf_sha256": Path("src/grid/dc_opf.py"),
        "scopf_sha256": Path("src/grid/scopf.py"),
        "cfe_profile_sha256": Path(
            "data/processed/model_inputs/"
            "rts_gmlc_hourly_cfe_deficit_250mw_v1/"
            "hourly_cfe_deficit.csv"
        ),
        "google_trace_sha256": Path(
            "data/processed/google_power_2019/v1/hourly_shape.csv"
        ),
    }

    for key, path in paths.items():
        assert (
            hashlib.sha256(path.read_bytes()).hexdigest()
            == prereg["frozen_inputs"][key]
        )


def test_phase_map_runtime_preregistration_gate_passes():
    config = yaml.safe_load(BASE_CONFIG.read_text(encoding="utf-8"))

    prereg_sha256, status = runner._validate_preregistration(
        config_path=BASE_CONFIG.resolve(),
        config=config,
        evaluation=config["evaluation"],
    )

    manifest_path = Path(
        config["evaluation"]["preregistration_manifest_path"]
    )
    assert status == (
        f"enforced_manifest={hashlib.sha256(manifest_path.read_bytes()).hexdigest()}"
    )
    assert prereg_sha256 == hashlib.sha256(PREREGISTRATION.read_bytes()).hexdigest()


def test_phase_map_external_manifest_is_complete():
    config = yaml.safe_load(BASE_CONFIG.read_text(encoding="utf-8"))
    manifest_path = Path(config["evaluation"]["preregistration_manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert str(BASE_CONFIG) in manifest
    assert str(PREREGISTRATION) in manifest
    for path, expected in manifest.items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
