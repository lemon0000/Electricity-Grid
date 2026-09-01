"""Validate the RQ2 four-arm robustness design without running a solver."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
PREREGISTRATION = (
    ROOT / "configs/rq2_public_baseline_robustness_preregistration_v1.yaml"
)
MANIFEST = ROOT / (
    "configs/rq2_public_baseline_robustness_preregistration_v1."
    "SHA256SUMS.json"
)
PREREGISTRATION_RELATIVE = (
    "configs/rq2_public_baseline_robustness_preregistration_v1.yaml"
)
MANIFEST_RELATIVE = (
    "configs/rq2_public_baseline_robustness_preregistration_v1."
    "SHA256SUMS.json"
)

EXPECTED_ARMS = [
    "network_only_shared",
    "cfe_only_shared",
    "joint_correct_shared",
    "joint_b6_separate_planning_shared_execution",
]
EXPECTED_STAGE_ORDER = [
    "verified_v6_grid_package",
    "four_arm_planning_pairwise_package",
    "four_arm_identification_package",
    "baseline_robustness_report_package",
]
EXPECTED_PRIORITY_ORDER = [
    "unresolved",
    "training_infeasible_estimand_undefined",
    "single_service_insufficiency_supported",
    "joint_only_interaction_supported",
    "b6_specific_underprovisioning_supported",
    "partially_identified",
    "no_registered_mechanism_supported",
]
EXPECTED_GLOBAL_PRECONDITIONS = [
    "all_four_arm_training_statuses_resolved",
    "all_required_pairwise_rows_and_E0_rows_present_and_resolved",
    "all_transport_endpoints_attained_with_valid_marginals",
    "every_multimetric_region_has_one_common_pi_witness",
    "configuration_and_upstream_hashes_verified",
]
EXPECTED_REGION_COUNTS = {
    "R1": 0,
    "R2": 0,
    "R3": 69,
    "mixed": 1,
    "unresolved": 0,
}
SUMMARY_REGION_KEYS = {
    "R1": "R1_no_conflict",
    "R2": "R2_double_commitment_risk",
    "R3": "R3_common_insufficiency",
    "mixed": "diagnostic_mixed",
    "unresolved": "unresolved",
}
FALSE_GATES = {
    "implementation_bound",
    "independent_R4_review_passed",
    "user_formal_run_authorized",
    "formal_execution_ready",
    "formal_result",
}
EXPECTED_CLAIMS = {
    "empirical_contract_overlap_or_incidence",
    "population_joint_law",
    "causal_attribution",
    "interconnection_capacity_X_overstatement",
    "absolute_Alibaba_MW",
    "empirical_outage_probability",
    "full_N_minus_1_security_certification",
    "AC_security_certification",
    "security_certification",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be a mapping")
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    return _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), str(path))


def _load_json(path: Path) -> dict[str, Any]:
    return _mapping(json.loads(path.read_text(encoding="utf-8")), str(path))


def _assert_equal(observed: object, expected: object, label: str) -> None:
    if observed != expected:
        raise ValueError(
            f"{label} drifted: expected {expected!r}, observed {observed!r}"
        )


def _expected_oat_cell_count(cells: dict[str, Any]) -> int:
    levels = _mapping(cells.get("levels"), "registered cell levels")
    return 1 + sum(len(values) - 1 for values in levels.values())


def _validate_predecessor(
    preregistration: dict[str, Any], summary: dict[str, Any]
) -> None:
    predecessor = _mapping(
        preregistration.get("predecessor_evidence"), "predecessor_evidence"
    )
    phase_map = _mapping(
        predecessor.get("observed_phase_map"), "observed_phase_map"
    )
    _assert_equal(phase_map.get("total_cells"), 70, "predecessor cell count")
    _assert_equal(
        phase_map.get("region_counts"),
        EXPECTED_REGION_COUNTS,
        "declared predecessor region counts",
    )
    summary_counts = _mapping(summary.get("region_counts"), "summary counts")
    normalized_counts = {
        short: summary_counts.get(long)
        for short, long in SUMMARY_REGION_KEYS.items()
    }
    _assert_equal(
        normalized_counts, EXPECTED_REGION_COUNTS, "observed predecessor counts"
    )
    _assert_equal(summary.get("published_cell_count"), 70, "published cells")
    for key in (
        "original_positive_H2_supported",
        "formal_result",
        "v6_pilot_observed",
        "v6_formal_result_observed",
    ):
        owner = phase_map if key in phase_map else predecessor
        _assert_equal(owner.get(key), False, key)
    _assert_equal(summary.get("formal_result"), False, "summary formal_result")


def _validate_inheritance(
    preregistration: dict[str, Any],
    pairwise: dict[str, Any],
    identification: dict[str, Any],
) -> None:
    inherited = _mapping(
        preregistration.get("same_design_inheritance"),
        "same_design_inheritance",
    )
    source_input = _mapping(pairwise.get("input"), "pairwise input")
    splits = _mapping(inherited.get("block_splits"), "block_splits")
    for key in (
        "power_training_blocks",
        "power_holdout_blocks",
        "workload_training_blocks",
        "workload_holdout_blocks",
    ):
        _assert_equal(splits.get(key), source_input.get(key), f"split {key}")
    _assert_equal(
        inherited.get("block_hours"), source_input.get("block_hours"), "block_hours"
    )
    _assert_equal(
        inherited.get("representative_selection"),
        pairwise.get("training_selection"),
        "representative selection",
    )
    _assert_equal(
        inherited.get("registered_cells"),
        pairwise.get("registered_cells"),
        "registered cells",
    )
    cells = _mapping(inherited.get("registered_cells"), "registered cells")
    _assert_equal(
        inherited.get("parameter_cell_count"),
        _expected_oat_cell_count(cells),
        "OAT cell count",
    )
    _assert_equal(
        inherited.get("fixed_policy"), pairwise.get("fixed_policy"), "fixed policy"
    )
    _assert_equal(inherited.get("solver"), pairwise.get("solver"), "solver")

    identification_input = _mapping(
        identification.get("input"), "identification input"
    )
    _assert_equal(
        identification_input.get("expected_parameter_cells"),
        inherited.get("parameter_cell_count"),
        "identification parameter cells",
    )
    _assert_equal(
        identification_input.get("expected_power_holdout_blocks"),
        splits.get("power_holdout_blocks"),
        "identification power holdout",
    )
    _assert_equal(
        identification_input.get("expected_workload_holdout_blocks"),
        splits.get("workload_holdout_blocks"),
        "identification workload holdout",
    )
    ambiguity = _mapping(
        identification.get("ambiguity_set"), "identification ambiguity set"
    )
    _assert_equal(
        ambiguity.get("type"),
        preregistration["coupling_contract"]["ambiguity_set"],
        "transport ambiguity set",
    )


def _validate_arms(preregistration: dict[str, Any]) -> None:
    arms = preregistration.get("arms")
    if not isinstance(arms, list):
        raise TypeError("arms must be a list")
    _assert_equal([arm.get("id") for arm in arms], EXPECTED_ARMS, "arm IDs")
    expected_service_calls = {
        "network_only_shared": ("inherited_active", "fixed_zero"),
        "cfe_only_shared": ("fixed_zero", "inherited_active"),
        "joint_correct_shared": ("inherited_active", "inherited_active"),
        "joint_b6_separate_planning_shared_execution": (
            "inherited_active",
            "inherited_active",
        ),
    }
    for arm in arms:
        arm_id = arm["id"]
        expected_grid, expected_green = expected_service_calls[arm_id]
        _assert_equal(arm.get("grid_call"), expected_grid, f"{arm_id} grid call")
        _assert_equal(
            arm.get("green_call"), expected_green, f"{arm_id} green call"
        )
        _assert_equal(
            arm.get("execution_envelope"), "shared", f"{arm_id} execution"
        )
        _assert_equal(arm.get("parameter_overrides"), {}, f"{arm_id} overrides")
        _assert_equal(
            arm.get("E0_handling"),
            "retained_separately_and_excluded_from_service_metrics",
            f"{arm_id} E0 handling",
        )
    _assert_equal(arms[2].get("planning_envelope"), "shared", "correct planning")
    _assert_equal(
        arms[3].get("planning_envelope"),
        "separate_by_service_then_combined",
        "B6 planning",
    )


def _validate_estimands_and_attribution(preregistration: dict[str, Any]) -> None:
    estimands = _mapping(
        preregistration.get("registered_estimands"), "registered_estimands"
    )
    _assert_equal(
        estimands["joint_interaction_capacity"].get("expression"),
        "D_joint_correct - max(D_network_only, D_cfe_only)",
        "joint interaction estimand",
    )
    _assert_equal(
        estimands["b6_underprovisioning"].get("expression"),
        "D_joint_correct - D_joint_B6",
        "B6 underprovisioning estimand",
    )
    _assert_equal(
        estimands["b6_equals_maximum_single_arm_capacity"].get("status"),
        "identity_to_be_tested_not_assumed",
        "B6 identity status",
    )
    fixed_policy = _mapping(
        estimands.get("fixed_policy_metrics"), "fixed_policy_metrics"
    )
    _assert_equal(
        fixed_policy.get("service_risk_metrics"),
        ["failure_probability", "expected_shortfall"],
        "service-risk metrics",
    )
    _assert_equal(
        fixed_policy.get("descriptive_state_metrics"),
        ["peak_recovery_debt", "terminal_recovery_debt"],
        "descriptive-state metrics",
    )
    expected_service_contrasts = {
        "joint_correct_minus_network_only": {
            "left_arm": "joint_correct_shared",
            "right_arm": "network_only_shared",
            "expressions": {
                "failure_probability": (
                    "failure_probability_joint_correct - "
                    "failure_probability_network_only"
                ),
                "expected_shortfall": (
                    "expected_shortfall_joint_correct - "
                    "expected_shortfall_network_only"
                ),
            },
            "positive_direction": (
                "left_arm_has_more_service_risk_than_right_arm"
            ),
            "category_deciding": True,
        },
        "joint_correct_minus_cfe_only": {
            "left_arm": "joint_correct_shared",
            "right_arm": "cfe_only_shared",
            "expressions": {
                "failure_probability": (
                    "failure_probability_joint_correct - "
                    "failure_probability_cfe_only"
                ),
                "expected_shortfall": (
                    "expected_shortfall_joint_correct - "
                    "expected_shortfall_cfe_only"
                ),
            },
            "positive_direction": (
                "left_arm_has_more_service_risk_than_right_arm"
            ),
            "category_deciding": True,
        },
        "joint_b6_minus_joint_correct": {
            "left_arm": "joint_b6_separate_planning_shared_execution",
            "right_arm": "joint_correct_shared",
            "expressions": {
                "failure_probability": (
                    "failure_probability_joint_B6 - "
                    "failure_probability_joint_correct"
                ),
                "expected_shortfall": (
                    "expected_shortfall_joint_B6 - "
                    "expected_shortfall_joint_correct"
                ),
            },
            "positive_direction": (
                "left_arm_has_more_service_risk_than_right_arm"
            ),
            "category_deciding": True,
        },
    }
    _assert_equal(
        fixed_policy.get("service_risk_contrasts"),
        expected_service_contrasts,
        "service-risk contrasts",
    )
    expected_debt_contrasts = {
        name: {
            "left_arm": service["left_arm"],
            "right_arm": service["right_arm"],
            "expressions": {
                "peak_recovery_debt": (
                    f"peak_recovery_debt_{suffixes[0]} - "
                    f"peak_recovery_debt_{suffixes[1]}"
                ),
                "terminal_recovery_debt": (
                    f"terminal_recovery_debt_{suffixes[0]} - "
                    f"terminal_recovery_debt_{suffixes[1]}"
                ),
            },
            "positive_direction": (
                "left_arm_has_more_recorded_debt_than_right_arm"
            ),
            "category_deciding": False,
        }
        for name, service, suffixes in (
            (
                "joint_correct_minus_network_only",
                expected_service_contrasts["joint_correct_minus_network_only"],
                ("joint_correct", "network_only"),
            ),
            (
                "joint_correct_minus_cfe_only",
                expected_service_contrasts["joint_correct_minus_cfe_only"],
                ("joint_correct", "cfe_only"),
            ),
            (
                "joint_b6_minus_joint_correct",
                expected_service_contrasts["joint_b6_minus_joint_correct"],
                ("joint_B6", "joint_correct"),
            ),
        )
    }
    _assert_equal(
        fixed_policy.get("descriptive_state_contrasts"),
        expected_debt_contrasts,
        "descriptive-state contrasts",
    )
    _assert_equal(
        fixed_policy.get("descriptive_state_rule"),
        {
            "positive_debt_is_service_failure": False,
            "debt_offsets_or_reverses_service_risk_conclusions": False,
            "right_censored_terminal_debt_is_failure": False,
        },
        "descriptive-state rule",
    )
    expected_future_channels = {
        name: {
            "planned_machine_field": name,
            "machine_field_registered_in_v1": False,
            "requires_non_right_censored_window": True,
            "category_deciding_in_v1": False,
        }
        for name in ("debt_limit_violation", "terminal_condition_violation")
    }
    _assert_equal(
        fixed_policy.get("future_failure_channels"),
        expected_future_channels,
        "future failure channels",
    )
    coupling = _mapping(
        preregistration.get("coupling_contract"), "coupling_contract"
    )
    _assert_equal(coupling.get("primary"), "full_transport_sharp_bounds", "primary")
    _assert_equal(
        coupling.get("multimetric_attribution_requires_one_common_pi_witness"),
        True,
        "common-pi rule",
    )
    t1 = _mapping(coupling.get("t1_mw_only_reference"), "T1 reference")
    for key in (
        "substitutes_for_full_temporal_arm",
        "current_pairwise_v4_contains_required_raw_trajectories",
        "implementation_bound",
    ):
        _assert_equal(t1.get(key), False, f"T1 {key}")
    _assert_equal(t1.get("future_implementation_path"), None, "T1 future path")

    attribution = _mapping(preregistration.get("attribution"), "attribution")
    _assert_equal(
        attribution.get("robust_positive_rule"),
        "transport_LB_greater_than_tolerance",
        "robust-positive rule",
    )
    _assert_equal(
        attribution.get("robust_nonpositive_rule"),
        "transport_UB_less_than_or_equal_to_tolerance",
        "robust-nonpositive rule",
    )
    _assert_equal(
        attribution.get("partial_identification_rule"),
        (
            "transport_LB_less_than_or_equal_to_tolerance_and_"
            "UB_greater_than_tolerance"
        ),
        "partial-identification rule",
    )
    _assert_equal(
        attribution.get("global_preconditions"),
        EXPECTED_GLOBAL_PRECONDITIONS,
        "global preconditions",
    )
    _assert_equal(
        attribution.get("exclusive_priority_order"),
        EXPECTED_PRIORITY_ORDER,
        "exclusive attribution priority",
    )
    expected_categories = {
        "unresolved": {
            "conditions": {
                "any_of": [
                    "global_precondition_failed",
                    "required_result_unparsed",
                ]
            },
            "allowed_metric_domains": [],
            "claim_gates": {
                "registered_attribution_allowed": False,
                "empirical_causal_claim_allowed": False,
            },
        },
        "training_infeasible_estimand_undefined": {
            "conditions": {
                "all_of": [
                    "arm_training_problem_proven_infeasible_under_frozen_"
                    "solver_contract"
                ],
                "excludes": [
                    "timeout",
                    "missing_certificate",
                    "local_solver_failure",
                ],
            },
            "allowed_metric_domains": [],
            "claim_gates": {
                "fixed_policy_attribution_allowed": False,
                "empirical_causal_claim_allowed": False,
            },
        },
        "single_service_insufficiency_supported": {
            "conditions": {
                "all_of": [
                    "global_preconditions_hold",
                    "common_pi_witness_for_every_combined_service_risk_"
                    "statement",
                ],
                "any_of": [
                    "network_only_service_risk_robust_positive",
                    "cfe_only_service_risk_robust_positive",
                ],
            },
            "allowed_metric_domains": ["service_risk"],
            "forbidden_metric_domains": ["descriptive_state"],
            "claim_gates": {
                "registered_attribution_allowed": True,
                "empirical_causal_claim_allowed": False,
                "joint_only_or_b6_specific_claim_allowed": False,
            },
        },
        "joint_only_interaction_supported": {
            "conditions": {
                "all_of": [
                    "global_preconditions_hold",
                    "both_single_service_arms_service_risk_robust_"
                    "nonpositive",
                    "common_pi_witness_for_every_combined_service_risk_"
                    "statement",
                ],
                "any_of": [
                    "joint_interaction_capacity_positive",
                    "joint_correct_service_risk_robust_positive",
                ],
            },
            "allowed_metric_domains": ["capacity", "service_risk"],
            "forbidden_metric_domains": ["descriptive_state"],
            "assumptions": {"b6_identity_assumed": False},
            "claim_gates": {
                "registered_attribution_allowed": True,
                "empirical_causal_claim_allowed": False,
            },
        },
        "b6_specific_underprovisioning_supported": {
            "conditions": {
                "all_of": [
                    "global_preconditions_hold",
                    "single_service_and_joint_correct_service_risk_robust_"
                    "nonpositive",
                    "common_pi_witness_for_every_combined_service_risk_"
                    "statement",
                ],
                "any_of": [
                    "b6_underprovisioning_positive",
                    "joint_b6_minus_joint_correct_service_risk_robust_"
                    "positive",
                ],
            },
            "allowed_metric_domains": ["capacity", "service_risk"],
            "forbidden_metric_domains": ["descriptive_state"],
            "assumptions": {"b6_identity_assumed": False},
            "claim_gates": {
                "registered_attribution_allowed": True,
                "empirical_causal_claim_allowed": False,
            },
        },
        "partially_identified": {
            "conditions": {
                "all_of": [
                    "global_preconditions_hold",
                    "no_earlier_supported_category_applies",
                ],
                "any_of": [
                    "capacity_or_service_risk_sign_crosses_tolerance",
                    "category_requires_incompatible_coupling_witnesses",
                ],
            },
            "allowed_metric_domains": ["capacity", "service_risk"],
            "forbidden_metric_domains": ["descriptive_state"],
            "claim_gates": {
                "registered_attribution_allowed": False,
                "empirical_causal_claim_allowed": False,
            },
        },
        "no_registered_mechanism_supported": {
            "conditions": {
                "all_of": [
                    "global_preconditions_hold",
                    "no_earlier_supported_category_applies",
                    "all_category_deciding_capacity_and_service_risk_"
                    "contrasts_robust_nonpositive",
                ]
            },
            "allowed_metric_domains": ["capacity", "service_risk"],
            "forbidden_metric_domains": ["descriptive_state"],
            "claim_gates": {
                "registered_null_label_allowed": True,
                "empirical_causal_claim_allowed": False,
            },
        },
    }
    _assert_equal(
        attribution.get("categories"), expected_categories, "attribution rules"
    )
    _assert_equal(
        attribution.get("E0_rule"),
        {
            "preserve_unconditional_mass": True,
            "exclude_from_conditional_service_metrics": True,
            "include_in_R3_common_insufficiency": False,
            "missing_or_unresolved_E0_blocks_formal_attribution": True,
        },
        "E0 attribution rule",
    )


def _validate_closed_gates_and_chain(
    preregistration: dict[str, Any],
    v6_preregistration: dict[str, Any],
    grid_config: dict[str, Any],
) -> None:
    gates = _mapping(preregistration.get("execution_gates"), "execution_gates")
    _assert_equal(set(gates), FALSE_GATES, "execution gate names")
    for key in FALSE_GATES:
        _assert_equal(gates.get(key), False, f"execution gate {key}")
    claims = _mapping(preregistration.get("claim_gates"), "claim_gates")
    _assert_equal(set(claims), EXPECTED_CLAIMS, "claim gate names")
    for key in EXPECTED_CLAIMS:
        _assert_equal(claims.get(key), False, f"claim gate {key}")

    chain = _mapping(preregistration.get("result_chain"), "result_chain")
    _assert_equal(chain.get("stage_order"), EXPECTED_STAGE_ORDER, "stage order")
    stages = _mapping(chain.get("stages"), "result stages")
    _assert_equal(set(stages), set(EXPECTED_STAGE_ORDER), "result stage IDs")
    expected_requirements = [
        "config_sha256",
        "upstream_manifest_and_provenance_sha256",
        "checkpoint_inventory",
        "declared_machine_readable_schemas",
        "all_registered_cells_including_negative_and_unresolved",
        "sha256_manifest",
    ]
    _assert_equal(
        chain.get("common_stage_requirements"),
        expected_requirements,
        "stage requirements",
    )
    frozen_inputs = _mapping(
        v6_preregistration.get("frozen_inputs"), "v6 frozen inputs"
    )
    grid_output = _mapping(grid_config.get("output"), "grid output")
    expected_first_stage = {
        "binding_status": "existing_v6_authority_chain_runtime_not_verified",
        "implementation_path": frozen_inputs["grid_need_successor"]["path"],
        "config_path": frozen_inputs["grid_config"]["path"],
        "runner_path": frozen_inputs["grid_runner"]["path"],
        "output_path": grid_output["directory"],
        "expected_schema": grid_output["schema"],
        "runtime_receipt_path": None,
        "runtime_provenance_manifest_sha256": None,
        "ready": False,
    }
    _assert_equal(
        stages.get("verified_v6_grid_package"),
        expected_first_stage,
        "verified v6 grid stage binding",
    )
    v6_gates = _mapping(
        v6_preregistration.get("activation_gates"), "v6 activation gates"
    )
    _assert_equal(
        v6_gates.get("grid_need_dispatch_ready"),
        False,
        "v6 grid runtime readiness",
    )
    for name in EXPECTED_STAGE_ORDER[1:]:
        stage = _mapping(stages.get(name), name)
        for key in (
            "implementation_path",
            "config_path",
            "runner_path",
            "output_path",
        ):
            _assert_equal(stage.get(key), None, f"{name} {key}")
        _assert_equal(stage.get("ready"), False, f"{name} ready")
        if not stage.get("expected_schema") and not stage.get("expected_schemas"):
            raise ValueError(f"{name} must declare an expected schema")


def validate_design(
    preregistration: dict[str, Any],
    pairwise: dict[str, Any],
    identification: dict[str, Any],
    summary: dict[str, Any],
    v6_preregistration: dict[str, Any],
    grid_config: dict[str, Any],
) -> None:
    """Validate frozen scientific semantics using already-loaded mappings."""

    _assert_equal(
        preregistration.get("schema"),
        "rq2_public_baseline_robustness_preregistration_v1",
        "schema",
    )
    _assert_equal(
        preregistration.get("status"), "design_only_not_executable", "status"
    )
    purpose = _mapping(preregistration.get("purpose"), "purpose")
    _assert_equal(
        purpose.get("post_hoc_retuning_of_observed_phase_map"),
        False,
        "post-hoc retuning flag",
    )
    _assert_equal(
        purpose.get("upgrades_predecessor_evidence"),
        False,
        "predecessor evidence upgrade flag",
    )
    _validate_predecessor(preregistration, summary)
    _validate_inheritance(preregistration, pairwise, identification)
    _validate_arms(preregistration)
    _validate_estimands_and_attribution(preregistration)
    _validate_closed_gates_and_chain(
        preregistration, v6_preregistration, grid_config
    )


def _manifest_inventory(preregistration: dict[str, Any]) -> dict[str, str]:
    inventory = {PREREGISTRATION_RELATIVE: ""}
    authorities = _mapping(
        preregistration.get("authority_inputs"), "authority_inputs"
    )
    for authority in authorities.values():
        item = _mapping(authority, "authority input")
        inventory[item["path"]] = item["sha256"]
    phase_map = preregistration["predecessor_evidence"]["observed_phase_map"]
    inventory[phase_map["manifest_path"]] = phase_map["manifest_sha256"]
    inventory[phase_map["summary_path"]] = phase_map["summary_sha256"]
    return inventory


def validate(
    preregistration_path: Path = PREREGISTRATION,
    manifest_path: Path = MANIFEST,
) -> dict[str, object]:
    """Read and verify the design, its authorities, and its exact manifest."""

    preregistration = _load_yaml(preregistration_path)
    authorities = _mapping(
        preregistration.get("authority_inputs"), "authority_inputs"
    )
    pairwise = _load_yaml(ROOT / authorities["pairwise_v4"]["path"])
    identification = _load_yaml(
        ROOT / authorities["identification_v4"]["path"]
    )
    v6_preregistration = _load_yaml(
        ROOT / authorities["v6_preregistration"]["path"]
    )
    v6_frozen_inputs = _mapping(
        v6_preregistration.get("frozen_inputs"), "v6 frozen inputs"
    )
    for label in ("grid_config", "grid_runner", "grid_need_successor"):
        authority = _mapping(v6_frozen_inputs.get(label), f"v6 {label}")
        _assert_equal(
            _sha256(ROOT / authority["path"]),
            authority["sha256"],
            f"v6 {label} authority hash",
        )
    grid_config = _load_yaml(ROOT / v6_frozen_inputs["grid_config"]["path"])
    phase_map = preregistration["predecessor_evidence"]["observed_phase_map"]
    summary = _load_json(ROOT / phase_map["summary_path"])
    validate_design(
        preregistration,
        pairwise,
        identification,
        summary,
        v6_preregistration,
        grid_config,
    )

    expected_inventory = _manifest_inventory(preregistration)
    expected_inventory[PREREGISTRATION_RELATIVE] = _sha256(preregistration_path)
    manifest = _load_json(manifest_path)
    _assert_equal(
        manifest.get("schema"),
        "rq2_public_baseline_robustness_preregistration_manifest_v1",
        "manifest schema",
    )
    files = _mapping(manifest.get("files"), "manifest files")
    _assert_equal(files, expected_inventory, "manifest inventory")
    if MANIFEST_RELATIVE in files:
        raise ValueError("manifest must not contain itself")
    for relative, expected in files.items():
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts:
            raise ValueError(f"unsafe manifest path: {relative}")
        observed = _sha256(ROOT / relative)
        _assert_equal(observed, expected, f"hash for {relative}")

    return {
        "schema": "rq2_public_baseline_robustness_validation_v1",
        "validation_passed": True,
        "arm_count": len(EXPECTED_ARMS),
        "registered_cell_count": 15,
        "manifest_file_count": len(files),
        "solver_calls": 0,
        "result_files_written": 0,
        "formal_execution_ready": False,
        "formal_result": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preregistration", type=Path, default=PREREGISTRATION)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args()
    print(
        json.dumps(
            validate(args.preregistration, args.manifest),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
