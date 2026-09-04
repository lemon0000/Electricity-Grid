from __future__ import annotations

import copy
import csv
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from experiments import (
    validate_rq2_joint_deliverability_preregistration_v1 as validator,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_joint_deliverability_preregistration_v1.yaml"
CONFIG = ROOT / "configs/rq2_joint_deliverability_preregistration_v1.yaml"
SPEC = ROOT / "docs/model_spec/rq2_joint_deliverability_estimands_v1.md"
PLAN = ROOT / "docs/plan/RQ2_联合服务可交付前沿确认性方案_v1.md"
INNER = ROOT / (
    "configs/rq2_joint_deliverability_preregistration_v1.SHA256SUMS.json"
)
OUTER = ROOT / (
    "configs/rq2_joint_deliverability_preregistration_v1.OUTER.SHA256SUMS.json"
)

EXPECTED_ARMS = [
    "network_only_shared",
    "cfe_only_shared",
    "joint_correct_shared",
    "joint_b6_separate_planning_shared_execution",
]
EXPECTED_FALSE_GATES = {
    "independent_R4_review_passed",
    "implementation_bound",
    "upstream_grid_package_ready",
    "user_formal_run_authorized",
    "formal_execution_ready",
    "formal_result",
    "paper_claim",
}


def _yaml(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def design() -> dict:
    return _yaml(CONFIG)


def test_research_question_and_primary_object_are_frozen(design: dict) -> None:
    assert design["schema"] == "rq2_joint_deliverability_preregistration_v1"
    assert design["version"] == 1
    assert design["scope"]["paper_role"] == "primary_RQ2_confirmatory_successor"
    assert (
        design["scope"]["scientific_object"]
        == "joint_temporal_deliverability_frontier"
    )
    assert design["research_question"]["id"] == "RQ2_joint_temporal_deliverability"
    assert design["research_question"]["external_replication_claimed"] is False


def test_read_only_validator_accepts_the_sealed_design(design: dict) -> None:
    report = validator.validate_design(design, require_sealed=True)
    assert report == {
        "design_valid": True,
        "registered_cell_count": 46,
        "arm_count": 4,
        "solver_calls": 0,
        "result_files_written": 0,
    }


def test_validator_rejects_cfe_request_truncation(design: dict) -> None:
    drifted = copy.deepcopy(design)
    drifted["hourly_cfe_target"]["service_call_expression"] = (
        "min(raw_deficit, available_flexibility)"
    )
    with pytest.raises(ValueError, match="CFE call"):
        validator.validate_design(drifted, require_sealed=True)


def test_predecessor_hashes_match_live_immutable_evidence(design: dict) -> None:
    predecessor = design["predecessor_evidence"]
    checks = (
        (
            predecessor["observed_phase_map"]["manifest_path"],
            predecessor["observed_phase_map"]["manifest_sha256"],
        ),
        (
            predecessor["observed_phase_map"]["summary_path"],
            predecessor["observed_phase_map"]["summary_sha256"],
        ),
        (
            predecessor["public_v6"]["preregistration_path"],
            predecessor["public_v6"]["preregistration_sha256"],
        ),
        (
            predecessor["public_v6"]["manifest_path"],
            predecessor["public_v6"]["manifest_sha256"],
        ),
        (
            predecessor["four_arm_v1"]["preregistration_path"],
            predecessor["four_arm_v1"]["preregistration_sha256"],
        ),
        (
            predecessor["four_arm_v1"]["manifest_path"],
            predecessor["four_arm_v1"]["manifest_sha256"],
        ),
    )
    for relative, expected in checks:
        assert _sha256(ROOT / relative) == expected


def test_primary_factorial_and_secondary_oat_have_46_unique_cells(
    design: dict,
) -> None:
    registered = design["registered_design"]
    factors = registered["primary_factorial"]["factors"]
    primary = {
        (
            alpha,
            flexible_fraction,
            headroom,
            registered["fixed_parameters"]["recovery_efficiency"],
            registered["fixed_parameters"]["maximum_event_duration_hours"],
            registered["fixed_parameters"]["maximum_event_count"],
            registered["fixed_parameters"]["normalized_energy_budget"],
            registered["fixed_parameters"]["normalized_debt_limit"],
        )
        for alpha in factors["hourly_cfe_target"]
        for flexible_fraction in factors["flexible_fraction"]
        for headroom in factors["normalized_recovery_headroom"]
    }
    assert len(primary) == registered["primary_factorial"]["cell_count"] == 36

    anchor = registered["secondary_oat"]["anchor"]
    key_order = (
        "hourly_cfe_target",
        "flexible_fraction",
        "normalized_recovery_headroom",
        "recovery_efficiency",
        "maximum_event_duration_hours",
        "maximum_event_count",
        "normalized_energy_budget",
        "normalized_debt_limit",
    )
    secondary = set()
    for parameter, levels in registered["secondary_oat"]["varied_levels"].items():
        for level in levels:
            candidate = dict(anchor)
            candidate[parameter] = level
            secondary.add(tuple(candidate[key] for key in key_order))
    anchor_key = tuple(anchor[key] for key in key_order)
    secondary.discard(anchor_key)
    assert len(secondary) == registered["secondary_oat"]["added_unique_cell_count"] == 10
    assert len(primary | secondary) == registered["exact_unique_cell_count"] == 46


def test_four_arm_inventory_and_projection_differences_are_exact(
    design: dict,
) -> None:
    arms = design["arms"]
    assert arms["canonical_order"] == EXPECTED_ARMS
    definitions = arms["definitions"]
    assert definitions["network_only_shared"]["cfe_call"] == "zero"
    assert definitions["cfe_only_shared"]["grid_call"] == "zero"
    assert definitions["joint_correct_shared"]["planning_envelope"] == "shared"
    assert (
        definitions["joint_b6_separate_planning_shared_execution"][
            "planning_envelope"
        ]
        == "separate_by_service_with_shared_connected_demand_cap"
    )
    assert {
        item["execution_envelope"] for item in definitions.values()
    } == {"shared"}


def test_capacity_decomposition_is_algebraically_complete(design: dict) -> None:
    estimands = design["registered_capacity_estimands"]
    assert estimands["joint_interaction_contrast"]["expression"] == (
        "D_J - max(D_N, D_C)"
    )
    assert estimands["separate_envelope_interaction"]["expression"] == (
        "D_B - max(D_N, D_C)"
    )
    assert estimands["b6_capacity_bias"]["expression"] == "D_J - D_B"
    assert estimands["exact_decomposition"]["expression"] == (
        "I_joint == I_sep + A_B6"
    )
    assert estimands["cross_arm_ordering_assumed"] is False

    d_n, d_c, d_b, d_j = 0.2, 0.3, 0.4, 0.6
    d_single = max(d_n, d_c)
    i_joint = d_j - d_single
    i_sep = d_b - d_single
    a_b6 = d_j - d_b
    assert i_joint == pytest.approx(i_sep + a_b6)

    d_b, d_j = 0.6, 0.4
    i_joint = d_j - d_single
    i_sep = d_b - d_single
    a_b6 = d_j - d_b
    assert i_joint == pytest.approx(i_sep + a_b6)
    assert a_b6 < 0.0


def test_predecessor_mixed_cell_refutes_cross_arm_ordering_assumption(
    design: dict,
) -> None:
    rows = list(
        csv.DictReader(
            (
                ROOT
                / "results/tables/rq2_three_region_phase_map_v1/cells.csv"
            ).open(encoding="utf-8")
        )
    )
    mixed = [row for row in rows if row["region"] == "diagnostic_mixed"]
    assert len(mixed) == 1
    assert float(mixed[0]["b6_committed_flexibility_mw"]) > float(
        mixed[0]["correct_committed_flexibility_mw"]
    )
    assert (
        design["registered_capacity_estimands"]["cross_arm_ordering_assumed"]
        is False
    )


def test_target_grid_is_inherited_and_grid_security_call_is_not_scaled(
    design: dict,
) -> None:
    target = design["hourly_cfe_target"]
    assert target["registered_levels"] == [0.50, 0.70, 0.85, 1.00]
    assert target["level_source"] == "inherited_exactly_from_predecessor_phase_map"
    assert target["service_call_expression"] == "raw_deficit"
    assert target["service_call_truncated_to_available_flexibility"] is False
    assert target["effective_recovery_headroom_expression"] == (
        "min(business_recovery_headroom, cfe_compatible_recovery_headroom)"
    )
    assert target["source_renewable_share_cap"] == 1.0
    assert target["alpha_1_role"] == "registered_stress_endpoint"
    assert target["network_call_scaled_with_alpha"] is False
    assert target["interpolation_between_registered_levels"] is False


def test_target_specific_cfe_call_and_recovery_have_expected_hand_calculation(
) -> None:
    renewable_share = 0.60
    business_headroom = 0.25

    target = 0.50
    deficit = max(target - renewable_share, 0.0) / target
    recovery = min(
        business_headroom,
        max(renewable_share / target - 1.0, 0.0),
    )
    assert deficit == pytest.approx(0.0)
    assert recovery == pytest.approx(0.20)

    target = 0.75
    deficit = max(target - renewable_share, 0.0) / target
    recovery = min(
        business_headroom,
        max(renewable_share / target - 1.0, 0.0),
    )
    assert deficit == pytest.approx(0.20)
    assert recovery == pytest.approx(0.0)


def test_training_and_holdout_rules_fail_closed(design: dict) -> None:
    planning = design["planning_contract"]
    assert (
        planning["representative_selection"][
            "common_power_and_workload_representative_ids_across_all_cells"
        ]
        is True
    )
    assert planning["full_evaluable_training_support_audit"] == "required"
    assert (
        planning["representative_candidate_fails_full_support"][
            "capacity_increase_or_reselection_allowed"
        ]
        is False
    )
    assert (
        planning["proven_infeasible_at_registered_cap"][
            "numeric_capacity_imputation"
        ]
        == "forbidden"
    )
    assert design["data_contract"]["split_policy"][
        "holdout_provision_reoptimization"
    ] is False
    assert design["data_contract"]["split_policy"][
        "holdout_recourse_reoptimization"
    ] is False


def test_attribution_is_nonexclusive_and_b6_is_diagnostic(design: dict) -> None:
    attribution = design["attribution_contract"]
    assert attribution["type"] == "nonexclusive_bottleneck_vector"
    assert set(attribution["labels"]) == {
        "network_single_service_binding",
        "cfe_single_service_binding",
        "joint_extra_requirement",
        "joint_portfolio_relief",
        "b6_capacity_underprovisioning",
        "b6_capacity_overprovisioning",
        "b6_operational_penalty",
        "b6_operational_relief",
    }
    assert attribution["one_label_suppresses_another"] is False
    assert attribution["b6_bias_is_independent_of_joint_interaction"] is False


def test_transport_is_holdout_robustness_layer_and_e0_is_separate(
    design: dict,
) -> None:
    uncertainty = design["holdout_uncertainty"]
    assert uncertainty["role"] == "robustness_layer"
    assert uncertainty["ambiguity_set"] == "complete_discrete_transport_polytope"
    assert uncertainty["multimetric_statement_requires_one_common_pi_witness"] is True
    assert uncertainty["exogenous_grid_infeasibility"] == {
        "state": "E0",
        "unconditional_mass_reported": True,
        "excluded_from_conditional_service_metrics": True,
    }
    assert uncertainty["population_joint_law_claimed"] is False


def test_execution_and_claim_gates_remain_closed(design: dict) -> None:
    gates = design["gates"]
    for key in EXPECTED_FALSE_GATES:
        assert gates[key] is False
    requirements = design["implementation_requirements"]
    assert requirements["implementation_path"] is None
    assert requirements["runner_path"] is None
    assert requirements["output_path"] is None
    assert design["scope"]["runs_solver"] is False
    assert design["scope"]["publishes_result"] is False


def test_live_scope_and_status_documents_reference_the_successor() -> None:
    required = {
        "agent.md": (
            "configs/rq2_joint_deliverability_preregistration_v1.yaml",
            "I_joint = D_J - max(D_N, D_C)",
        ),
        "README.md": (
            "RQ2_联合服务可交付前沿确认性方案_v1.md",
            "I_joint = D_J - max(D_N,D_C)",
        ),
        "docs/plan/RQ2_开发机任务与执行边界.md": (
            "RQ2_联合服务可交付前沿确认性方案_v1.md",
            "46-cell",
        ),
        "docs/model_spec/blocker_register.md": (
            "rq2_joint_deliverability_preregistration_v1.yaml",
            "I_joint=I_sep+A_B6",
        ),
        "paper/drafts/project_introduction.md": (
            "I_{joint}=D_J-\\max(D_N,D_C)=I_{sep}+A_{B6}",
            "共46个",
        ),
    }
    for relative, snippets in required.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        for snippet in snippets:
            assert snippet in text


def test_sealed_documents_and_manifests_are_consistent(design: dict) -> None:
    assert design["status"] == "SEALED_READY_FOR_INDEPENDENT_REVIEW"
    assert design["gates"]["pre_seal_audit_complete"] is True
    assert design["gates"]["sealed_ready_for_independent_review"] is True
    assert "`SEALED_READY_FOR_INDEPENDENT_REVIEW`" in SPEC.read_text(
        encoding="utf-8"
    )
    assert "`SEALED_READY_FOR_INDEPENDENT_REVIEW`" in PLAN.read_text(
        encoding="utf-8"
    )
    assert INNER.is_file()
    assert OUTER.is_file()
    report = validator.validate()
    assert report["validation_passed"] is True
    assert report["sealed_file_count"] == 5
    assert report["independent_R4_review_passed"] is False
    assert report["formal_execution_ready"] is False
