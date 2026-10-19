from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest
import yaml

from experiments import (
    validate_rq2_public_baseline_robustness_preregistration_v1 as validator,
)


def _yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def design_inputs() -> tuple[dict, dict, dict, dict, dict, dict]:
    preregistration = _yaml(validator.PREREGISTRATION)
    pairwise = _yaml(Path("configs/rq2_public_pairwise_replay_v4.yaml"))
    identification = _yaml(
        Path("configs/rq2_public_identification_grid_v4.yaml")
    )
    summary = _json(
        Path("results/tables/rq2_three_region_phase_map_v1/summary.json")
    )
    v6_preregistration = _yaml(
        Path(
            "configs/rq2_public_data_robust_identification_"
            "preregistration_v6.yaml"
        )
    )
    grid_config = _yaml(
        Path("configs/rts_gmlc_public_grid_need_dispatch_v4.yaml")
    )
    return (
        preregistration,
        pairwise,
        identification,
        summary,
        v6_preregistration,
        grid_config,
    )


def test_frozen_design_and_manifest_validate_without_solver_or_result_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_write(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("validator must not write files")

    monkeypatch.setattr(Path, "write_text", fail_write)
    monkeypatch.setattr(Path, "write_bytes", fail_write)
    report = validator.validate()
    assert report["validation_passed"] is True
    assert report["arm_count"] == 4
    assert report["registered_cell_count"] == 15
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["formal_execution_ready"] is False
    assert report["formal_result"] is False

    tree = ast.parse(
        Path(validator.__file__).read_text(encoding="utf-8")
    )
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imported_roots <= {
        "__future__",
        "argparse",
        "hashlib",
        "json",
        "pathlib",
        "typing",
        "yaml",
    }


def test_arm_drift_fails_closed(design_inputs: tuple[dict, ...]) -> None:
    mutated = copy.deepcopy(design_inputs)
    preregistration = mutated[0]
    preregistration["arms"][0]["green_call"] = "inherited_active"
    with pytest.raises(ValueError, match="network_only_shared green call"):
        validator.validate_design(*mutated)


def test_execution_gate_elevation_fails_closed(
    design_inputs: tuple[dict, ...],
) -> None:
    mutated = copy.deepcopy(design_inputs)
    preregistration = mutated[0]
    preregistration["execution_gates"]["formal_execution_ready"] = True
    with pytest.raises(ValueError, match="formal_execution_ready"):
        validator.validate_design(*mutated)


def test_observed_70_cell_status_drift_fails_closed(
    design_inputs: tuple[dict, ...],
) -> None:
    mutated = copy.deepcopy(design_inputs)
    preregistration = mutated[0]
    preregistration["predecessor_evidence"]["observed_phase_map"][
        "region_counts"
    ]["R2"] = 1
    with pytest.raises(ValueError, match="declared predecessor region counts"):
        validator.validate_design(*mutated)


def test_post_hoc_parameter_drift_fails_closed(
    design_inputs: tuple[dict, ...],
) -> None:
    mutated = copy.deepcopy(design_inputs)
    preregistration = mutated[0]
    preregistration["same_design_inheritance"]["registered_cells"]["base"][
        "flexible_fraction"
    ] = 0.21
    with pytest.raises(ValueError, match="registered cells"):
        validator.validate_design(*mutated)


def test_priority_reversal_fails_closed(
    design_inputs: tuple[dict, ...],
) -> None:
    mutated = copy.deepcopy(design_inputs)
    priority = mutated[0]["attribution"]["exclusive_priority_order"]
    priority[2], priority[3] = priority[3], priority[2]
    with pytest.raises(ValueError, match="exclusive attribution priority"):
        validator.validate_design(*mutated)


def test_robust_sign_rule_drift_fails_closed(
    design_inputs: tuple[dict, ...],
) -> None:
    mutated = copy.deepcopy(design_inputs)
    mutated[0]["attribution"]["robust_positive_rule"] = (
        "transport_UB_greater_than_tolerance"
    )
    with pytest.raises(ValueError, match="robust-positive rule"):
        validator.validate_design(*mutated)


def test_common_pi_gate_drift_fails_closed(
    design_inputs: tuple[dict, ...],
) -> None:
    mutated = copy.deepcopy(design_inputs)
    mutated[0]["coupling_contract"][
        "multimetric_attribution_requires_one_common_pi_witness"
    ] = False
    with pytest.raises(ValueError, match="common-pi rule"):
        validator.validate_design(*mutated)


def test_e0_unresolved_blocker_drift_fails_closed(
    design_inputs: tuple[dict, ...],
) -> None:
    mutated = copy.deepcopy(design_inputs)
    mutated[0]["attribution"]["E0_rule"][
        "missing_or_unresolved_E0_blocks_formal_attribution"
    ] = False
    with pytest.raises(ValueError, match="E0 attribution rule"):
        validator.validate_design(*mutated)


def test_single_service_always_true_condition_fails_closed(
    design_inputs: tuple[dict, ...],
) -> None:
    mutated = copy.deepcopy(design_inputs)
    category = mutated[0]["attribution"]["categories"][
        "single_service_insufficiency_supported"
    ]
    category["conditions"]["any_of"] = ["always_true"]
    with pytest.raises(ValueError, match="attribution rules"):
        validator.validate_design(*mutated)


def test_descriptive_debt_cannot_enter_service_risk_domain(
    design_inputs: tuple[dict, ...],
) -> None:
    mutated = copy.deepcopy(design_inputs)
    fixed_policy = mutated[0]["registered_estimands"]["fixed_policy_metrics"]
    fixed_policy["service_risk_metrics"].append("peak_recovery_debt")
    with pytest.raises(ValueError, match="service-risk metrics"):
        validator.validate_design(*mutated)


def test_contrast_direction_drift_fails_closed(
    design_inputs: tuple[dict, ...],
) -> None:
    mutated = copy.deepcopy(design_inputs)
    contrast = mutated[0]["registered_estimands"]["fixed_policy_metrics"][
        "service_risk_contrasts"
    ]["joint_b6_minus_joint_correct"]
    contrast["positive_direction"] = "left_arm_has_less_service_risk"
    with pytest.raises(ValueError, match="service-risk contrasts"):
        validator.validate_design(*mutated)


@pytest.mark.parametrize(
    ("field", "drifted_value"),
    [
        ("expected_schema", "rts_gmlc_public_grid_need_dispatch_v5"),
        ("config_path", "configs/nonexistent_grid_config.yaml"),
    ],
)
def test_existing_grid_stage_binding_drift_fails_closed(
    design_inputs: tuple[dict, ...], field: str, drifted_value: str
) -> None:
    mutated = copy.deepcopy(design_inputs)
    stage = mutated[0]["result_chain"]["stages"][
        "verified_v6_grid_package"
    ]
    stage[field] = drifted_value
    with pytest.raises(ValueError, match="verified v6 grid stage binding"):
        validator.validate_design(*mutated)


def test_manifest_hash_drift_fails_closed(tmp_path: Path) -> None:
    manifest = _json(validator.MANIFEST)
    manifest["files"][validator.PREREGISTRATION_RELATIVE] = "0" * 64
    drifted_manifest = tmp_path / "SHA256SUMS.json"
    drifted_manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="manifest inventory"):
        validator.validate(manifest_path=drifted_manifest)


def test_manifest_is_exact_and_non_circular() -> None:
    preregistration = _yaml(validator.PREREGISTRATION)
    manifest = _json(validator.MANIFEST)
    expected = validator._manifest_inventory(preregistration)
    expected[validator.PREREGISTRATION_RELATIVE] = validator._sha256(
        validator.PREREGISTRATION
    )
    assert manifest["files"] == expected
    assert validator.MANIFEST_RELATIVE not in manifest["files"]
    assert all(value is not None for value in manifest["files"].values())
