from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest
import yaml

from experiments import (
    validate_rq2_joint_deliverability_preregistration_successor_v3 as validator,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT / "configs/rq2_joint_deliverability_preregistration_successor_v3.yaml"
)
REVIEW = (
    ROOT / "configs/rq2_joint_deliverability_preregistration_review_rework_v2.yaml"
)
INNER = ROOT / (
    "configs/rq2_joint_deliverability_preregistration_successor_v3."
    "SHA256SUMS.json"
)
OUTER = ROOT / (
    "configs/rq2_joint_deliverability_preregistration_successor_v3."
    "OUTER.SHA256SUMS.json"
)


def _design() -> dict:
    value = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_successor_accepts_declared_scientific_changes() -> None:
    report = validator.validate_design(_design(), require_sealed=True)
    assert report == {
        "design_valid": True,
        "corrected_major_findings": 5,
        "declared_scientific_changes": True,
        "registered_cell_count": 46,
        "arm_count": 4,
        "solver_calls": 0,
        "result_files_written": 0,
    }


def test_review_receipt_binds_exact_rework_subject() -> None:
    review = yaml.safe_load(REVIEW.read_text(encoding="utf-8"))
    assert review["verdict"] == "REWORK"
    assert len(review["findings"]) == 5
    assert {item["severity"] for item in review["findings"]} == {"major"}
    assert review["reviewed_subject"]["outer_sha256"] == (
        "ae1e8a8a5c4c276e5c0d54900636de94e5402f29923817cf8cb70067b90c90f7"
    )


def test_network_only_and_b6_recovery_semantics_are_distinct() -> None:
    arms = _design()["arm_semantics"]
    network = arms["network_only_shared"]
    cfe = arms["cfe_only_shared"]
    joint = arms["joint_correct_shared"]
    b6 = arms["joint_b6_separate_planning_shared_execution"]

    assert network["planning_recovery_by_track"] == {
        "shared": "business_recovery_headroom"
    }
    assert network["canonical_capacity_key_excludes"] == [
        "hourly_cfe_target"
    ]
    assert cfe["planning_recovery_by_track"] == {
        "shared": "cfe_service_recovery_headroom"
    }
    assert joint["planning_recovery_by_track"] == {
        "shared": "cfe_service_recovery_headroom"
    }
    assert b6["planning_recovery_by_track"] == {
        "grid": "business_recovery_headroom",
        "cfe": "cfe_service_recovery_headroom",
    }
    assert b6["separate_event_energy_and_debt_states_by_track"] is True
    assert b6["execution_recovery"] == "cfe_service_recovery_headroom"


def test_network_recovery_alpha_contamination_fails_closed() -> None:
    drifted = copy.deepcopy(_design())
    drifted["arm_semantics"]["network_only_shared"][
        "planning_recovery_by_track"
    ]["shared"] = "cfe_service_recovery_headroom"
    with pytest.raises(ValueError, match="network_only_shared planning recovery"):
        validator.validate_design(drifted, require_sealed=True)


def test_b6_track_recovery_collapse_fails_closed() -> None:
    drifted = copy.deepcopy(_design())
    drifted["arm_semantics"][
        "joint_b6_separate_planning_shared_execution"
    ]["planning_recovery_by_track"]["grid"] = "cfe_service_recovery_headroom"
    with pytest.raises(ValueError, match="planning recovery"):
        validator.validate_design(drifted, require_sealed=True)


def test_alpha_one_structural_status_and_witness_are_mandatory() -> None:
    endpoint = _design()["alpha_1_structural_endpoint"]
    assert endpoint["status"] == (
        "structural_recovery_infeasible_estimand_undefined"
    )
    assert endpoint["solver_call_after_witness"] is False
    assert endpoint["numeric_capacity_imputation"] is False
    assert endpoint["four_arm_contrast_when_any_arm_undefined"] is False
    assert {
        "total_required_call_energy",
        "maximum_effective_recovery_headroom",
        "terminal_recovery_debt_limit",
        "analytic_identity",
    }.issubset(endpoint["required_witness_fields"])


def test_alpha_one_numeric_imputation_fails_closed() -> None:
    drifted = copy.deepcopy(_design())
    drifted["alpha_1_structural_endpoint"][
        "numeric_capacity_imputation"
    ] = True
    with pytest.raises(ValueError, match="numeric_capacity_imputation"):
        validator.validate_design(drifted, require_sealed=True)


def test_capacity_intervals_propagate_all_four_certificates() -> None:
    capacity = _design()["capacity_certification"]
    assert capacity["contrast_intervals"] == {
        "D_single": "[max(L_N,L_C), max(U_N,U_C)]",
        "I_joint": "[L_J-max(U_N,U_C), U_J-max(L_N,L_C)]",
        "I_sep": "[L_B-max(U_N,U_C), U_B-max(L_N,L_C)]",
        "A_B6": "[L_J-U_B, U_J-L_B]",
    }
    assert capacity["sign_classification"] == {
        "robust_positive": "interval_lower_greater_than_1e-6",
        "robust_negative": "interval_upper_less_than_negative_1e-6",
        "certified_near_zero": (
            "interval_contained_in_closed_negative_1e-6_positive_1e-6"
        ),
        "numerically_indeterminate": "all_other_resolved_intervals",
    }
    assert capacity["point_sign_without_interval_support_forbidden"] is True


def test_point_only_sign_rule_fails_closed() -> None:
    drifted = copy.deepcopy(_design())
    drifted["capacity_certification"][
        "point_sign_without_interval_support_forbidden"
    ] = False
    with pytest.raises(ValueError, match="point-only sign gate"):
        validator.validate_design(drifted, require_sealed=True)


def test_temporal_and_representative_algorithms_are_exact() -> None:
    design = _design()
    envelope = design["temporal_envelope"]
    assert envelope["minimum_recovery_hours"] == 1.0
    assert envelope["minimum_event_power"] == 1.0e-6
    assert envelope["response_time_hours"] == 1.0
    assert envelope["curtailment_ramp_per_hour"] == 1.0
    selection = design["representative_selection"]
    assert selection["ordering"] == "ascending_score_then_ascii_block_id"
    assert selection["quantile_targets_expression"] == (
        "(k + 0.5) / 8 for k in 0..7"
    )
    assert selection["duplicate_quantile_rule"] == (
        "preserve_first_then_fill_from_remaining_ordered_blocks"
    )
    assert selection["mass_reassignment_rule"] == (
        "nearest_selected_score_then_ascii_block_id"
    )


def test_cell_inventory_is_exactly_36_plus_10() -> None:
    cells = _design()["registered_cells"]
    assert cells["primary_factorial"]["exact_cell_count"] == 36
    assert cells["secondary_oat"]["exact_added_cell_count"] == 10
    assert cells["exact_unique_cell_count"] == 46
    assert cells["duplicates_forbidden"] is True


def test_holdout_policy_metrics_and_E0_denominator_are_explicit() -> None:
    design = _design()
    policy = design["holdout_policy"]
    assert policy["per_hour_lexicographic_action"] == [
        "maximize_grid_service_subject_to_current_shared_envelope_state",
        "maximize_cfe_service_from_remaining_current_feasible_set",
        "if_total_call_is_zero_maximize_registered_recovery",
    ]
    metrics = policy["metric_definitions"]
    assert metrics["total_service_shortfall"] == (
        "grid_shortfall+cfe_shortfall"
    )
    assert "recovery_completion_failure" in metrics["joint_service_failure"]
    e0 = design["holdout_identification"]["E0"]
    assert e0["reported_unconditionally_once"] is True
    assert e0["pairwise_service_metrics_defined"] is False
    assert e0[
        "excluded_from_finite_service_numerator_and_denominator"
    ] is True


def test_bootstrap_empty_finite_support_is_unresolved() -> None:
    bootstrap = _design()["holdout_identification"]["bootstrap"]
    assert bootstrap["replicates"] == 200
    assert bootstrap["seed"] == 20260825
    assert bootstrap["power_draw_count"] == 530
    assert bootstrap["workload_draw_count"] == 34
    assert bootstrap["any_replicate_without_finite_support"] == (
        "bootstrap_interval_unresolved"
    )


def test_scientific_changes_cannot_be_relabelled_as_zero_change() -> None:
    drifted = copy.deepcopy(_design())
    drifted["scope"]["changes_scientific_protocol"] = False
    with pytest.raises(ValueError, match="changes_scientific_protocol"):
        validator.validate_design(drifted, require_sealed=True)


def test_all_execution_and_claim_gates_remain_closed() -> None:
    design = _design()
    for field in validator.EXPECTED_FALSE_GATES:
        assert design["gates"][field] is False
    assert design["scope"]["runs_solver"] is False
    assert design["scope"]["publishes_result"] is False


def test_validator_imports_no_solver_or_runtime_model() -> None:
    tree = ast.parse(Path(validator.__file__).read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(
        name.startswith(("gurobi", "pyomo", "src.models", "src.solvers"))
        for name in imports
    )


def test_exact_manifests_and_full_validator_pass() -> None:
    assert INNER.is_file()
    assert OUTER.is_file()
    report = validator.validate()
    assert report["validation_passed"] is True
    assert report["sealed_file_count"] == 6
    assert report["registered_cell_count"] == 46
    assert report["corrected_major_findings"] == 5
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["independent_R4_review_passed"] is False
    assert report["formal_execution_ready"] is False
