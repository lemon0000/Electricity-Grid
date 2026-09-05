"""Validate the focused RQ2 joint-deliverability scientific successor v3."""

from __future__ import annotations

import argparse
import hashlib
import json
from itertools import product
from pathlib import Path
from typing import Any

import yaml

from experiments import (
    validate_rq2_joint_deliverability_preregistration_amendment_v2 as predecessor,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = (
    "configs/rq2_joint_deliverability_preregistration_successor_v3.yaml"
)
REVIEW_RELATIVE = (
    "configs/rq2_joint_deliverability_preregistration_review_rework_v2.yaml"
)
SPEC_RELATIVE = "docs/model_spec/rq2_joint_deliverability_estimands_v2.md"
PLAN_RELATIVE = "docs/plan/RQ2_联合服务可交付前沿确认性方案_v3.md"
VALIDATOR_RELATIVE = (
    "experiments/validate_rq2_joint_deliverability_preregistration_successor_v3.py"
)
TEST_RELATIVE = (
    "tests/test_rq2_joint_deliverability_preregistration_successor_v3.py"
)
INNER_RELATIVE = (
    "configs/rq2_joint_deliverability_preregistration_successor_v3."
    "SHA256SUMS.json"
)
OUTER_RELATIVE = (
    "configs/rq2_joint_deliverability_preregistration_successor_v3."
    "OUTER.SHA256SUMS.json"
)

CONFIG = ROOT / CONFIG_RELATIVE
REVIEW = ROOT / REVIEW_RELATIVE
SPEC = ROOT / SPEC_RELATIVE
PLAN = ROOT / PLAN_RELATIVE
INNER = ROOT / INNER_RELATIVE
OUTER = ROOT / OUTER_RELATIVE

PREDECESSOR_OUTER = (
    ROOT
    / "configs/rq2_joint_deliverability_preregistration_amendment_v2."
    "OUTER.SHA256SUMS.json"
)
PREDECESSOR_OUTER_SHA256 = (
    "ae1e8a8a5c4c276e5c0d54900636de94e5402f29923817cf8cb70067b90c90f7"
)
PREDECESSOR_CONFIG = (
    ROOT / "configs/rq2_joint_deliverability_preregistration_v1.yaml"
)
PREDECESSOR_CONFIG_SHA256 = (
    "2efd3fa275cccde2aee701662bb2718386b2fb54d2846b090d0828d8409bdc4f"
)
PREDECESSOR_SPEC = (
    ROOT / "docs/model_spec/rq2_joint_deliverability_estimands_v1.md"
)
PREDECESSOR_SPEC_SHA256 = (
    "28d38744d782aa9e9a8db239801b8ec44ef6290d41c4635ea6b76c208c9b5883"
)
REVIEW_SHA256 = (
    "4eebadc7c9bee12e03e625b6ae19765e3e08e5cef2cee5a9e55f2a3fd9ae85f4"
)

EXPECTED_SUPERSEDED_PATHS = {
    "hourly_cfe_target.effective_recovery_headroom_expression",
    "hourly_cfe_target.alpha_1_role",
    "arms.definitions",
    "arms.forbidden_arm_specific_overrides",
    "registered_design.fixed_parameters",
    "planning_contract.representative_selection",
    "registered_capacity_estimands.signed_capacity_classification",
    "frontier_outputs.target_status",
    "fixed_policy_holdout",
    "holdout_uncertainty",
    "decision_rules",
    "implementation_requirements.required_output_schemas",
}
EXPECTED_FALSE_GATES = {
    "independent_R4_review_passed",
    "implementation_bound",
    "upstream_grid_package_ready",
    "user_formal_run_authorized",
    "formal_execution_ready",
    "formal_result",
    "paper_claim",
}
EXPECTED_INNER_MEMBERS = {
    CONFIG_RELATIVE,
    REVIEW_RELATIVE,
    SPEC_RELATIVE,
    PLAN_RELATIVE,
    VALIDATOR_RELATIVE,
    TEST_RELATIVE,
}
ARM_ORDER = (
    "network_only_shared",
    "cfe_only_shared",
    "joint_correct_shared",
    "joint_b6_separate_planning_shared_execution",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be a mapping")
    return value


def _sequence(value: object, label: str) -> list[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise TypeError(f"{label} must be a list")
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    return _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), str(path))


def _load_json(path: Path) -> dict[str, Any]:
    return _mapping(json.loads(path.read_text(encoding="utf-8")), str(path))


def _equal(observed: object, expected: object, label: str) -> None:
    if observed != expected:
        raise ValueError(
            f"{label} drifted: expected {expected!r}, observed {observed!r}"
        )


def _validate_predecessor(design: dict[str, Any]) -> None:
    authority = _mapping(design.get("predecessor"), "predecessor")
    expected = {
        "reviewed_outer_path": (
            "configs/rq2_joint_deliverability_preregistration_amendment_v2."
            "OUTER.SHA256SUMS.json"
        ),
        "reviewed_outer_sha256": PREDECESSOR_OUTER_SHA256,
        "scientific_config_path": (
            "configs/rq2_joint_deliverability_preregistration_v1.yaml"
        ),
        "scientific_config_sha256": PREDECESSOR_CONFIG_SHA256,
        "specification_path": (
            "docs/model_spec/rq2_joint_deliverability_estimands_v1.md"
        ),
        "specification_sha256": PREDECESSOR_SPEC_SHA256,
        "review_receipt_path": REVIEW_RELATIVE,
        "review_receipt_sha256": REVIEW_SHA256,
        "review_verdict": "REWORK",
    }
    _equal(authority, expected, "predecessor authority")
    for path, digest in (
        (PREDECESSOR_OUTER, PREDECESSOR_OUTER_SHA256),
        (PREDECESSOR_CONFIG, PREDECESSOR_CONFIG_SHA256),
        (PREDECESSOR_SPEC, PREDECESSOR_SPEC_SHA256),
        (REVIEW, REVIEW_SHA256),
    ):
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"authority member is missing or unsafe: {path}")
        _equal(_sha256(path), digest, f"authority hash {path}")
    review = _load_yaml(REVIEW)
    _equal(review.get("verdict"), "REWORK", "review verdict")
    _equal(len(_sequence(review.get("findings"), "review findings")), 5, "Major count")
    if any(item.get("severity") != "major" for item in review["findings"]):
        raise ValueError("review finding severity drifted")
    report = predecessor.validate()
    _equal(report.get("validation_passed"), True, "predecessor validation")
    _equal(
        report.get("outer_manifest_sha256"),
        PREDECESSOR_OUTER_SHA256,
        "predecessor validator outer",
    )
    _equal(
        report.get("independent_R4_review_passed"),
        False,
        "predecessor review gate",
    )


def _validate_scope_and_inheritance(design: dict[str, Any]) -> None:
    _equal(
        design.get("schema"),
        "rq2_joint_deliverability_preregistration_successor_v3",
        "schema",
    )
    _equal(design.get("version"), 3, "version")
    scope = _mapping(design.get("scope"), "scope")
    expected_true = {
        "changes_scientific_protocol",
        "changes_recovery_semantics",
        "changes_alpha_1_status_semantics",
        "changes_capacity_sign_classification",
        "completes_operational_estimands",
    }
    for field in expected_true:
        _equal(scope.get(field), True, f"scope {field}")
    for field in (
        "changes_research_question",
        "changes_registered_target_levels",
        "changes_registered_cell_count",
        "changes_arm_inventory",
        "changes_solver_contract",
        "runs_solver",
        "publishes_result",
        "formal_result",
        "claim",
    ):
        _equal(scope.get(field), False, f"scope {field}")
    inheritance = _mapping(design.get("inheritance"), "inheritance")
    _equal(
        set(_sequence(inheritance.get("superseded_paths"), "superseded paths")),
        EXPECTED_SUPERSEDED_PATHS,
        "superseded path inventory",
    )
    rule = str(inheritance.get("rule"))
    if "does not claim a zero-change amendment" not in rule:
        raise ValueError("inheritance rule must acknowledge scientific changes")


def _validate_cells(design: dict[str, Any]) -> None:
    cells = _mapping(design.get("registered_cells"), "registered cells")
    primary = _mapping(cells.get("primary_factorial"), "primary factorial")
    alpha = _sequence(primary.get("hourly_cfe_target"), "alpha levels")
    flexible = _sequence(primary.get("flexible_fraction"), "flexible levels")
    headroom = _sequence(
        primary.get("normalized_recovery_headroom"), "headroom levels"
    )
    _equal(alpha, [0.50, 0.70, 0.85, 1.00], "alpha levels")
    _equal(flexible, [0.05, 0.20, 0.50], "flexible levels")
    _equal(headroom, [0.00, 0.10, 0.30], "headroom levels")
    primary_tuples = set(product(alpha, flexible, headroom))
    _equal(len(primary_tuples), 36, "primary unique cell count")
    _equal(primary.get("exact_cell_count"), 36, "registered primary count")

    secondary = _mapping(cells.get("secondary_oat"), "secondary OAT")
    anchor = _mapping(secondary.get("anchor"), "OAT anchor")
    envelope = _mapping(design.get("temporal_envelope"), "temporal envelope")
    levels = _mapping(envelope.get("oat_levels"), "OAT levels")
    dimensions = _sequence(
        secondary.get("varied_dimensions"), "OAT dimensions"
    )
    _equal(set(dimensions), set(levels), "OAT dimension inventory")
    tuples = []
    keys = tuple(anchor)
    for dimension in dimensions:
        values = _sequence(levels.get(dimension), f"{dimension} levels")
        if anchor[dimension] not in values:
            raise ValueError(f"OAT anchor is absent from {dimension}")
        for value in values:
            if value == anchor[dimension]:
                continue
            item = dict(anchor)
            item[dimension] = value
            tuples.append(tuple(item[key] for key in keys))
    _equal(len(tuples), 10, "OAT added cell count")
    _equal(len(set(tuples)), 10, "OAT unique cell count")
    _equal(secondary.get("exact_added_cell_count"), 10, "registered OAT count")
    _equal(cells.get("exact_unique_cell_count"), 46, "registered total count")


def _validate_recovery_and_envelope(design: dict[str, Any]) -> None:
    recovery = _mapping(design.get("cfe_and_recovery"), "CFE and recovery")
    _equal(
        recovery.get("raw_call_truncated_to_available_flexibility"),
        False,
        "raw CFE call truncation",
    )
    _equal(
        recovery.get("cfe_service_recovery_headroom_expression"),
        "min(business_recovery_headroom, cfe_compatible_recovery_headroom)",
        "CFE recovery expression",
    )
    arms = _mapping(design.get("arm_semantics"), "arm semantics")
    _equal(tuple(arms.get("canonical_order", ())), ARM_ORDER, "arm order")
    expected = {
        "network_only_shared": {
            "tracks": ["shared"],
            "planning": {"shared": "business_recovery_headroom"},
            "execution": "business_recovery_headroom",
        },
        "cfe_only_shared": {
            "tracks": ["shared"],
            "planning": {"shared": "cfe_service_recovery_headroom"},
            "execution": "cfe_service_recovery_headroom",
        },
        "joint_correct_shared": {
            "tracks": ["shared"],
            "planning": {"shared": "cfe_service_recovery_headroom"},
            "execution": "cfe_service_recovery_headroom",
        },
        "joint_b6_separate_planning_shared_execution": {
            "tracks": ["grid", "cfe"],
            "planning": {
                "grid": "business_recovery_headroom",
                "cfe": "cfe_service_recovery_headroom",
            },
            "execution": "cfe_service_recovery_headroom",
        },
    }
    for arm_id, contract in expected.items():
        arm = _mapping(arms.get(arm_id), arm_id)
        _equal(arm.get("planning_tracks"), contract["tracks"], f"{arm_id} tracks")
        _equal(
            arm.get("planning_recovery_by_track"),
            contract["planning"],
            f"{arm_id} planning recovery",
        )
        _equal(
            arm.get("execution_recovery"),
            contract["execution"],
            f"{arm_id} execution recovery",
        )
    network = _mapping(arms["network_only_shared"], "network-only")
    _equal(
        network.get("canonical_capacity_key_excludes"),
        ["hourly_cfe_target"],
        "network-only alpha invariance",
    )
    b6 = _mapping(
        arms["joint_b6_separate_planning_shared_execution"], "B6 arm"
    )
    for field in (
        "shared_connected_demand_cap",
        "separate_available_flexibility_cap_by_track",
        "separate_event_energy_and_debt_states_by_track",
    ):
        _equal(b6.get(field), True, f"B6 {field}")

    envelope = _mapping(design.get("temporal_envelope"), "temporal envelope")
    expected_envelope = {
        "maximum_flexibility_budget": 1.0,
        "minimum_recovery_hours": 1.0,
        "minimum_event_power": 1.0e-6,
        "response_time_hours": 1.0,
        "curtailment_ramp_per_hour": 1.0,
        "service_shortfall_tolerance": 1.0e-6,
    }
    for field, value in expected_envelope.items():
        _equal(envelope.get(field), value, f"temporal envelope {field}")
    boundary = _mapping(
        design.get("normalization_and_boundary"),
        "normalization and boundary",
    )
    _equal(boundary.get("initial_recovery_debt"), 0.0, "initial debt")
    _equal(
        boundary.get("terminal_recovery_debt_limit"),
        0.0,
        "terminal debt",
    )


def _validate_selection_and_capacity(design: dict[str, Any]) -> None:
    selection = _mapping(
        design.get("representative_selection"), "representative selection"
    )
    exact = {
        "input_split": "training_only",
        "power_input_rows": "finite_grid_need_only",
        "finite_power_probabilities_renormalized_before_selection": True,
        "ordering": "ascending_score_then_ascii_block_id",
        "quantile_targets_expression": "(k + 0.5) / 8 for k in 0..7",
        "quantile_selection_rule": (
            "first_ordered_block_with_cumulative_probability_at_least_target"
        ),
        "duplicate_quantile_rule": (
            "preserve_first_then_fill_from_remaining_ordered_blocks"
        ),
        "mass_reassignment_rule": (
            "nearest_selected_score_then_ascii_block_id"
        ),
        "selected_ids_frozen_once_for_all_46_cells": True,
        "holdout_used": False,
    }
    for field, value in exact.items():
        _equal(selection.get(field), value, f"selection {field}")
    _equal(
        selection.get("count_by_margin"),
        {"power": 8, "workload": 8},
        "representative counts",
    )

    capacity = _mapping(
        design.get("capacity_certification"), "capacity certification"
    )
    _equal(
        capacity.get("contrast_intervals"),
        {
            "D_single": "[max(L_N,L_C), max(U_N,U_C)]",
            "I_joint": "[L_J-max(U_N,U_C), U_J-max(L_N,L_C)]",
            "I_sep": "[L_B-max(U_N,U_C), U_B-max(L_N,L_C)]",
            "A_B6": "[L_J-U_B, U_J-L_B]",
        },
        "contrast interval formulas",
    )
    _equal(
        capacity.get("sign_classification"),
        {
            "robust_positive": "interval_lower_greater_than_1e-6",
            "robust_negative": "interval_upper_less_than_negative_1e-6",
            "certified_near_zero": (
                "interval_contained_in_closed_negative_1e-6_positive_1e-6"
            ),
            "numerically_indeterminate": "all_other_resolved_intervals",
        },
        "capacity sign classification",
    )
    _equal(
        capacity.get("point_sign_without_interval_support_forbidden"),
        True,
        "point-only sign gate",
    )


def _validate_endpoint_and_holdout(design: dict[str, Any]) -> None:
    endpoint = _mapping(
        design.get("alpha_1_structural_endpoint"), "alpha=1 endpoint"
    )
    for field in (
        "remains_registered",
        "solver_call_after_witness",
        "numeric_capacity_imputation",
        "four_arm_contrast_when_any_arm_undefined",
    ):
        expected = field == "remains_registered"
        _equal(endpoint.get(field), expected, f"alpha=1 {field}")
    _equal(
        endpoint.get("status"),
        "structural_recovery_infeasible_estimand_undefined",
        "alpha=1 status",
    )
    _equal(
        set(_sequence(endpoint.get("required_witness_fields"), "witness fields")),
        {
            "arm_id",
            "track_id",
            "total_required_call_energy",
            "maximum_effective_recovery_headroom",
            "initial_recovery_debt",
            "terminal_recovery_debt_limit",
            "analytic_identity",
        },
        "alpha=1 witness inventory",
    )

    policy = _mapping(design.get("holdout_policy"), "holdout policy")
    _equal(policy.get("capacity_reoptimization"), False, "holdout capacity")
    _equal(policy.get("representative_reselection"), False, "holdout selection")
    _equal(policy.get("current_state_only"), True, "holdout information")
    _equal(
        policy.get("per_hour_lexicographic_action"),
        [
            "maximize_grid_service_subject_to_current_shared_envelope_state",
            "maximize_cfe_service_from_remaining_current_feasible_set",
            "if_total_call_is_zero_maximize_registered_recovery",
        ],
        "holdout action",
    )
    metrics = _mapping(policy.get("metric_definitions"), "metric definitions")
    _equal(
        metrics.get("total_service_shortfall"),
        "grid_shortfall+cfe_shortfall",
        "total shortfall",
    )
    if "recovery_completion_failure" not in str(
        metrics.get("joint_service_failure")
    ):
        raise ValueError("joint failure must include recovery completion")

    identification = _mapping(
        design.get("holdout_identification"), "holdout identification"
    )
    e0 = _mapping(identification.get("E0"), "E0")
    _equal(e0.get("reported_unconditionally_once"), True, "E0 reporting")
    _equal(e0.get("pairwise_service_metrics_defined"), False, "E0 metrics")
    _equal(
        e0.get("excluded_from_finite_service_numerator_and_denominator"),
        True,
        "E0 denominator",
    )
    bootstrap = _mapping(identification.get("bootstrap"), "bootstrap")
    _equal(bootstrap.get("replicates"), 200, "bootstrap replicates")
    _equal(bootstrap.get("seed"), 20260825, "bootstrap seed")
    _equal(bootstrap.get("power_draw_count"), 530, "power draw count")
    _equal(bootstrap.get("workload_draw_count"), 34, "workload draw count")
    _equal(
        bootstrap.get("any_replicate_without_finite_support"),
        "bootstrap_interval_unresolved",
        "bootstrap empty finite support",
    )


def validate_design(
    design: dict[str, Any],
    *,
    require_sealed: bool,
) -> dict[str, Any]:
    _validate_predecessor(design)
    _validate_scope_and_inheritance(design)
    _validate_cells(design)
    _validate_recovery_and_envelope(design)
    _validate_selection_and_capacity(design)
    _validate_endpoint_and_holdout(design)
    gates = _mapping(design.get("gates"), "gates")
    for field in EXPECTED_FALSE_GATES:
        _equal(gates.get(field), False, f"gate {field}")
    _equal(
        gates.get("first_official_R4_verdict_recorded"),
        True,
        "R4 verdict gate",
    )
    if require_sealed:
        _equal(
            design.get("status"),
            "SEALED_READY_FOR_INDEPENDENT_REVIEW",
            "status",
        )
        _equal(gates.get("pre_seal_audit_complete"), True, "pre-seal gate")
        _equal(
            gates.get("sealed_ready_for_independent_review"),
            True,
            "sealed review gate",
        )
    return {
        "design_valid": True,
        "corrected_major_findings": 5,
        "declared_scientific_changes": True,
        "registered_cell_count": 46,
        "arm_count": 4,
        "solver_calls": 0,
        "result_files_written": 0,
    }


def _validate_documents() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    for required in (
        "network-only`不读取alpha",
        "structural_recovery_infeasible_estimand_undefined",
        "numerically_indeterminate",
        "当前状态",
        "E0",
    ):
        if required not in spec and required not in plan:
            raise ValueError(f"successor documents omit required term: {required}")
    if "SEALED_READY_FOR_INDEPENDENT_REVIEW" not in spec:
        raise ValueError("specification status drifted")
    if "SEALED_READY_FOR_INDEPENDENT_REVIEW" not in plan:
        raise ValueError("plan status drifted")


def _validate_manifests() -> dict[str, Any]:
    inner = _load_json(INNER)
    outer = _load_json(OUTER)
    _equal(
        inner.get("schema"),
        "rq2_joint_deliverability_preregistration_successor_manifest_v3",
        "inner schema",
    )
    files = _mapping(inner.get("files"), "inner files")
    _equal(set(files), EXPECTED_INNER_MEMBERS, "inner inventory")
    for relative, expected in files.items():
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"sealed member is missing or unsafe: {relative}")
        _equal(_sha256(path), expected, f"sealed member hash {relative}")
    _equal(
        outer.get("schema"),
        "rq2_joint_deliverability_preregistration_successor_outer_v3",
        "outer schema",
    )
    _equal(outer.get("version"), 3, "outer version")
    outer_inner = _mapping(outer.get("inner"), "outer inner")
    _equal(outer_inner.get("path"), INNER_RELATIVE, "outer inner path")
    _equal(outer_inner.get("sha256"), _sha256(INNER), "outer inner hash")
    return {
        "inner_manifest_sha256": _sha256(INNER),
        "outer_manifest_sha256": _sha256(OUTER),
        "sealed_file_count": len(files),
    }


def validate() -> dict[str, Any]:
    design = _load_yaml(CONFIG)
    report = validate_design(design, require_sealed=True)
    _validate_documents()
    report.update(_validate_manifests())
    report.update(
        {
            "validation_passed": True,
            "status": design["status"],
            "independent_R4_review_passed": False,
            "implementation_bound": False,
            "formal_execution_ready": False,
            "formal_result": False,
        }
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    print(json.dumps(validate(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
