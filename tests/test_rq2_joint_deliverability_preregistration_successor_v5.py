from __future__ import annotations

import ast
import copy
import math
from pathlib import Path

import pytest

from experiments import (
    validate_rq2_joint_deliverability_preregistration_successor_v5 as validator,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_joint_deliverability_preregistration_successor_v5.yaml"
SPEC = ROOT / "docs/model_spec/rq2_joint_deliverability_estimands_v4.md"
PLAN = ROOT / "docs/plan/RQ2_联合服务可交付前沿确认性方案_v5.md"
INNER = ROOT / (
    "configs/rq2_joint_deliverability_preregistration_successor_v5.SHA256SUMS.json"
)
OUTER = ROOT / (
    "configs/rq2_joint_deliverability_preregistration_successor_v5."
    "OUTER.SHA256SUMS.json"
)


def _design() -> dict:
    return validator._load_yaml(CONFIG)


def _mutated(path: tuple[object, ...], value: object) -> dict:
    design = copy.deepcopy(_design())
    target = design
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    return design


def _is_sealed(design: dict) -> bool:
    return design["lifecycle"]["status"] == "SEALED_READY_FOR_INDEPENDENT_REVIEW"


def _execute_registered_holdout_probe(
    design: dict,
    **overrides: object,
) -> dict[str, object]:
    probe = design["holdout_policy"]["deterministic_probe"]
    temporal = design["temporal_envelope"]
    arguments = {
        "committed_capacity": probe["committed_capacity"],
        "grid_request": probe["grid_request"],
        "cfe_request": probe["cfe_request"],
        "available_flexibility": probe["available_flexibility"],
        "connected_demand": probe["connected_demand"],
        "current_recovery_headroom": probe["current_recovery_headroom"],
        "maximum_recovery_power": probe["maximum_recovery_power"],
        "recovery_efficiency": probe["recovery_efficiency"],
        "maximum_event_duration_hours": probe["maximum_event_duration_hours"],
        "maximum_event_count": probe["maximum_event_count"],
        "minimum_recovery_hours": probe["minimum_recovery_hours"],
        "normalized_energy_budget": probe["normalized_energy_budget"],
        "normalized_debt_limit": probe["normalized_debt_limit"],
        "terminal_recovery_debt_limit": temporal["terminal_recovery_debt_limit"],
        "time_step_hours": design["data_contract"]["time_step_hours"],
        "minimum_event_power": temporal["minimum_event_power"],
        "curtailment_ramp_per_hour": temporal["curtailment_ramp_per_hour"],
        "response_time_hours": temporal["response_time_hours"],
        "service_shortfall_tolerance": temporal["service_shortfall_tolerance"],
    }
    arguments.update(overrides)
    return validator.execute_holdout_policy(**arguments)


def test_complete_self_contained_design_validates() -> None:
    design = _design()
    report = validator.validate_design(
        design,
        require_sealed=_is_sealed(design),
    )
    assert report["design_valid"] is True
    assert report["complete_self_contained_authority"] is True
    assert report["semantic_payload_sha256"] == (
        "31be646a725f9aef7498fd57b140b404828bfba4afa9c98912c20346aae4b8e4"
    )
    assert report["registered_cell_count"] == 46
    assert report["arm_count"] == 4
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0


def test_v4_predecessor_is_provenance_only_and_hash_bound() -> None:
    authority = _design()["authority"]
    assert authority["mode"] == "complete_self_contained_replacement"
    assert authority["predecessor_scientific_fields_inherited_by_omission"] is False
    assert authority["prior_versions_may_define_current_semantics"] is False
    assert (
        validator._sha256(validator.V4_OUTER)
        == (authority["reviewed_v4_outer"]["sha256"])
    )
    assert (
        validator._sha256(validator.V4_REWORK)
        == (authority["v4_rework_receipt"]["sha256"])
    )


def test_exact_46_cell_inventory_is_unique() -> None:
    cells = validator.expand_registered_cells(_design())
    assert len(cells) == 46
    assert len({item["cell_id"] for item in cells}) == 46
    assert len({tuple(sorted(item["values"].items())) for item in cells}) == 46
    assert sum(item["family"] == "primary_factorial" for item in cells) == 36
    assert sum(item["family"] == "secondary_oat" for item in cells) == 10


def test_network_only_is_alpha_invariant_and_B6_tracks_are_distinct() -> None:
    arms = _design()["arm_contract"]
    definitions = arms["definitions"]
    network = definitions["network_only_shared"]
    b6 = definitions["joint_b6_separate_planning_shared_execution"]
    assert network["cfe_call"] == "zero"
    assert network["planning_recovery_by_track"] == {
        "shared": "business_recovery_headroom"
    }
    assert network["canonical_capacity_key_excludes"] == ["hourly_cfe_target"]
    assert b6["planning_tracks"] == ["grid", "cfe"]
    assert b6["planning_recovery_by_track"] == {
        "grid": "business_recovery_headroom",
        "cfe": "cfe_service_recovery_headroom",
    }
    assert b6["execution_tracks"] == ["shared"]


def test_planning_feasible_sets_are_explicit_and_track_specific() -> None:
    formulation = _design()["planning_formulation"]
    assert "on" in formulation["variables"]
    assert True not in formulation["variables"]
    assert formulation["service_constraints"] == {
        "network_active": ("x_grid_greater_than_or_equal_to_effective_grid_request"),
        "network_inactive": "x_grid_equal_to_zero",
        "cfe_active": "x_cfe_equal_to_effective_cfe_request",
        "cfe_inactive": "x_cfe_equal_to_zero",
        "service_shortfall_variable_present": False,
        "excess_cfe_service_allowed": False,
        "excess_grid_service_allowed": True,
    }
    assert formulation["track_call_mapping"] == {
        "shared": "q_equals_x_grid_plus_x_cfe",
        "grid": "q_equals_x_grid",
        "cfe": "q_equals_x_cfe",
    }
    assert (
        formulation["physical_caps"]["shared_arm_available_flexibility"]
        == "x_grid_plus_x_cfe_less_than_or_equal_to_available_flexibility"
    )
    assert (
        formulation["physical_caps"]["B6_grid_available_flexibility"]
        == "x_grid_less_than_or_equal_to_available_flexibility"
    )
    assert (
        formulation["physical_caps"]["B6_cfe_available_flexibility"]
        == "x_cfe_less_than_or_equal_to_available_flexibility"
    )
    assert formulation["terminal_constraints"] == {
        "terminal_on": "on_at_hour_23_equals_zero",
        "terminal_debt": "debt_at_hour_23_less_than_or_equal_to_zero",
    }
    assert (
        formulation["B6_simultaneous_track_semantics"][
            "one_track_may_recover_while_other_track_calls"
        ]
        is True
    )


def test_input_mapping_and_E0_block_lifting_are_exact() -> None:
    schema = _design()["input_schema_contract"]
    assert schema["power_hourly_file"] == ("dispatched_power_system_blocks.csv.gz")
    assert schema["power_field_mapping"]["cfe_call_fraction_at_alpha_1"] == {
        "source_column": "cfe_call_fraction",
        "parse": "finite_float64_closed_0_1",
    }
    assert schema["workload_field_mapping"]["raw_workload_fraction"] == {
        "source_column": "workload_fraction",
        "parse": "finite_float64_nonnegative",
    }
    assert (
        validator.lift_power_block_state(["finite_grid_need"] * 24)
        == "finite_grid_need"
    )
    assert (
        validator.lift_power_block_state(
            ["finite_grid_need"] * 23 + ["exogenous_grid_infeasibility"]
        )
        == "exogenous_grid_infeasibility"
    )
    with pytest.raises(ValueError, match="unregistered hourly state"):
        validator.lift_power_block_state(["finite_grid_need"] * 23 + ["unresolved"])
    assert validator.e0_mass_by_unique_block(
        [("p0", 0.25), ("p1", 0.75)],
        {
            "p0": "exogenous_grid_infeasibility",
            "p1": "finite_grid_need",
        },
    ) == pytest.approx(0.25)
    assert validator.finite_conditioning_denominator(0.25) == pytest.approx(0.75)
    assert validator.finite_conditioning_denominator(1.0) is None
    with pytest.raises(ValueError, match="duplicate block ID"):
        validator.e0_mass_by_unique_block(
            [("p0", 0.25), ("p0", 0.75)],
            {"p0": "exogenous_grid_infeasibility"},
        )


def test_global_zero_recovery_precheck_detects_every_trigger_route() -> None:
    common = {
        "maximum_recovery_power": 0.5,
        "recovery_efficiency": 0.85,
        "initial_recovery_debt": 0.0,
        "terminal_recovery_debt_limit": 0.0,
        "time_step_hours": 1.0,
        "service_tolerance": 1.0e-6,
        "tolerance": 1.0e-12,
    }
    assert validator.zero_recovery_structural_trigger(
        [0.0, 0.2, 0.0],
        [0.0, 0.0, 0.0],
        **common,
    )
    assert validator.zero_recovery_structural_trigger(
        [0.1, 0.0],
        [0.0, 0.0],
        **common,
    )
    assert not validator.zero_recovery_structural_trigger(
        [0.0, 0.0],
        [0.0, 0.0],
        **common,
    )
    assert not validator.zero_recovery_structural_trigger(
        [0.2, 0.0],
        [0.0, 0.3],
        **common,
    )
    assert validator.zero_recovery_structural_trigger(
        [1.0, 0.0],
        [1.0, 0.0],
        **common,
    )
    assert not validator.zero_recovery_structural_trigger(
        [1.0e-6],
        [1.0],
        **common,
    )
    assert validator.zero_recovery_structural_trigger(
        [1.000001e-6],
        [1.0],
        **common,
    )
    precheck = _design()["zero_recovery_structural_precheck"]
    assert precheck["scope"] == (
        "every_arm_track_cell_over_full_evaluable_training_cartesian_support"
    )
    assert precheck["alpha_1_role"] == ("sufficient_input_route_not_exclusive_scope")
    assert precheck["track_required_call"] == {
        "network_only_shared": {"shared": "effective_grid_call"},
        "cfe_only_shared": {"shared": "effective_cfe_call"},
        "joint_correct_shared": {
            "shared": "effective_grid_call_plus_effective_cfe_call"
        },
        "joint_b6_separate_planning_shared_execution": {
            "grid": "effective_grid_call",
            "cfe": "effective_cfe_call",
        },
    }


def test_capacity_interval_propagation_and_all_sign_states() -> None:
    observed = validator.contrast_intervals(
        {
            "D_N": (0.1, 0.2),
            "D_C": (0.3, 0.4),
            "D_J": (0.5, 0.6),
            "D_B": (0.45, 0.55),
        }
    )
    assert observed["D_single"] == pytest.approx((0.3, 0.4))
    assert observed["I_joint"] == pytest.approx((0.1, 0.3))
    assert observed["I_sep"] == pytest.approx((0.05, 0.25))
    assert observed["A_B6"] == pytest.approx((-0.05, 0.15))
    assert validator.classify_interval((0.1, 0.2)) == "robust_positive"
    assert validator.classify_interval((-0.2, -0.1)) == "robust_negative"
    assert validator.classify_interval((-1.0e-7, 1.0e-7)) == ("certified_near_zero")
    assert validator.classify_interval((-0.1, 0.2)) == ("numerically_indeterminate")


def test_frontier_and_all_capacity_labels_are_interval_supported() -> None:
    design = _design()
    frontier = design["frontier_outputs"]
    assert (
        "certified I_joint interval"
        in frontier["first_registered_robust_positive_joint_interaction"]
    )
    assert frontier["structural_status_is_numeric_frontier_point"] is False
    labels = design["attribution_contract"]["labels"]
    for label in validator.ALL_CAPACITY_LABELS:
        assert "certified_" in labels[label]["condition"]
    assert design["capacity_estimands"]["point_sign_used_for_label_or_claim"] is False
    attribution = design["attribution_contract"]
    assert attribution["evaluation_order"] == [
        "status_based_single_service_labels",
        "signed_capacity_labels_if_all_four_arms_resolved",
        "operational_labels_if_holdout_and_transport_resolved",
    ]
    assert (
        attribution["status_based_single_service_labels_require_all_four_resolved"]
        is False
    )
    assert attribution["signed_capacity_labels_require_all_four_resolved"] is True
    assert attribution["truth_table"]["D_N_structural_or_cap_infeasible"] == {
        "network_single_service_binding": True,
        "signed_capacity_labels": "not_evaluable",
        "operational_labels": "not_evaluable",
    }
    assert attribution["truth_table"]["all_four_resolved_holdout_not_resolved"] == {
        "status_based_single_service_labels": "not_evaluable",
        "signed_capacity_labels": "evaluate_from_certified_intervals",
        "operational_labels": "not_evaluable",
    }


def test_holdout_is_current_state_only_and_includes_recovery_completion() -> None:
    policy = _design()["holdout_policy"]
    assert policy["future_calls_or_states_used"] is False
    assert (
        "maximum_recovery_debt" in policy["current_shared_feasible_action_set_includes"]
    )
    assert policy["state_transition_order"] == [
        "determine_served_grid_and_cfe",
        "derive_active_start_and_stop",
        "compute_debt_before_recovery",
        "choose_recovery_if_inactive",
        "compute_debt_after_recovery",
        "update_duration_event_count_rest_energy_and_prior_event",
    ]
    assert (
        "recovery_completion_failure"
        in policy["metric_definitions"]["joint_service_failure"]
    )


def test_holdout_golden_trajectory_is_deterministic_and_grid_first() -> None:
    design = _design()
    observed = _execute_registered_holdout_probe(design)
    trajectory = observed["trajectory"]
    assert [row["grid_served"] for row in trajectory] == pytest.approx(
        [0.3, 0.0, 0.2, 0.0, 0.0]
    )
    assert [row["cfe_served"] for row in trajectory] == pytest.approx(
        [0.2, 0.0, 0.3, 0.0, 0.0]
    )
    assert [row["event_start"] for row in trajectory] == [
        True,
        False,
        True,
        False,
        False,
    ]
    assert trajectory[-1]["recovery_debt"] == pytest.approx(0.0)
    metrics = observed["metrics"]
    assert metrics["grid_shortfall"] == pytest.approx(0.0)
    assert metrics["cfe_shortfall"] == pytest.approx(0.1)
    assert metrics["total_service_shortfall"] == pytest.approx(0.1)
    assert metrics["hard_grid_failure"] is False
    assert metrics["cfe_service_failure"] is True
    assert metrics["recovery_completion_failure"] is False
    assert metrics["joint_service_failure"] is True
    assert validator.holdout_probe_sha256(design) == (
        "3a6f2cf0169d238f884ebd26bbf1d383c3c444923831610a39216e684a18c453"
    )


def test_subthreshold_requests_are_zero_in_planning_and_holdout() -> None:
    design = _design()
    tolerance = design["temporal_envelope"]["service_shortfall_tolerance"]
    formulation = design["planning_formulation"]
    assert formulation["effective_service_requests"] == {
        "grid": ("0 if grid_request <= service_shortfall_tolerance, else grid_request"),
        "cfe": (
            "0 if raw_cfe_request <= service_shortfall_tolerance, else raw_cfe_request"
        ),
        "raw_requests_retained_for_audit": True,
    }
    observed = _execute_registered_holdout_probe(
        design,
        grid_request=[0.0] * 5,
        cfe_request=[tolerance] + [0.0] * 4,
    )
    assert all(row["total_call"] == 0.0 for row in observed["trajectory"])
    assert observed["metrics"]["total_service_shortfall"] == 0.0
    assert observed["metrics"]["joint_service_failure"] is False


def test_E0_transport_and_operational_quantifiers_are_exact() -> None:
    identification = _design()["holdout_identification"]
    e0 = identification["E0"]
    assert e0["reported_unconditionally_once"] is True
    assert e0["pairwise_service_metrics_defined"] is False
    assert e0["excluded_from_finite_service_numerator"] is True
    assert e0["excluded_from_finite_service_denominator"] is True
    transport = identification["transport"]
    assert "all nonnegative finite matrices pi" in transport["ambiguity_set"]
    quantifiers = transport["operational_label_quantifiers"]
    assert quantifiers["quantifier_order"] == (
        "exists_registered_metric_then_for_all_admissible_pi"
    )
    assert quantifiers["existential_common_pi_witness_used"] is False
    statements = quantifiers["registered_statements"]
    assert set(statements) == {
        "b6_operational_penalty",
        "b6_operational_relief",
    }
    assert statements["b6_operational_penalty"]["metrics"] == list(
        validator.OPERATIONAL_METRICS
    )
    assert statements["b6_operational_penalty"]["endpoint_test"] == (
        "certified_lower_bound_greater_than_1e-6"
    )
    assert statements["b6_operational_relief"]["endpoint_test"] == (
        "certified_upper_bound_less_than_negative_1e-6"
    )
    crossing_zero = {metric: (-0.2, 0.3) for metric in validator.OPERATIONAL_METRICS}
    assert validator.operational_labels_from_transport_intervals(crossing_zero) == {
        "b6_operational_penalty": False,
        "b6_operational_relief": False,
    }
    robust_both = {
        validator.OPERATIONAL_METRICS[0]: (0.1, 0.2),
        validator.OPERATIONAL_METRICS[1]: (-0.3, -0.2),
        validator.OPERATIONAL_METRICS[2]: (-0.1, 0.1),
    }
    assert validator.operational_labels_from_transport_intervals(robust_both) == {
        "b6_operational_penalty": True,
        "b6_operational_relief": True,
    }
    assert validator.transport_probe_sha256(_design()) == (
        "716e489913b2dff47c1299b560568d1aa1e3615ac2ac1301431ff6af1e9449d5"
    )
    payload = validator.transport_probe_payload(_design())
    assert float.fromhex(payload["lower"]["endpoint_value"]) == pytest.approx(0.2)
    assert float.fromhex(payload["upper"]["endpoint_value"]) == pytest.approx(1.4)


def test_operational_label_thresholds_are_strict_at_float_boundaries() -> None:
    tolerance = 1.0e-6
    neutral = {
        metric: (-tolerance, tolerance) for metric in validator.OPERATIONAL_METRICS
    }

    penalty_at_threshold = dict(neutral)
    penalty_at_threshold[validator.OPERATIONAL_METRICS[0]] = (
        tolerance,
        2.0 * tolerance,
    )
    assert (
        validator.operational_labels_from_transport_intervals(penalty_at_threshold)[
            "b6_operational_penalty"
        ]
        is False
    )

    penalty_above_threshold = dict(neutral)
    penalty_above_threshold[validator.OPERATIONAL_METRICS[0]] = (
        math.nextafter(tolerance, math.inf),
        2.0 * tolerance,
    )
    assert (
        validator.operational_labels_from_transport_intervals(penalty_above_threshold)[
            "b6_operational_penalty"
        ]
        is True
    )

    relief_at_threshold = dict(neutral)
    relief_at_threshold[validator.OPERATIONAL_METRICS[0]] = (
        -2.0 * tolerance,
        -tolerance,
    )
    assert (
        validator.operational_labels_from_transport_intervals(relief_at_threshold)[
            "b6_operational_relief"
        ]
        is False
    )

    relief_below_threshold = dict(neutral)
    relief_below_threshold[validator.OPERATIONAL_METRICS[0]] = (
        -2.0 * tolerance,
        math.nextafter(-tolerance, -math.inf),
    )
    assert (
        validator.operational_labels_from_transport_intervals(relief_below_threshold)[
            "b6_operational_relief"
        ]
        is True
    )


def test_bootstrap_contract_and_deterministic_probe() -> None:
    bootstrap = _design()["bootstrap_contract"]
    assert bootstrap["software"] == {
        "python": "3.11.15",
        "numpy": "1.26.4",
    }
    assert bootstrap["pseudorandom_generator"] == {
        "api": "numpy.random.Generator",
        "bit_generator": "numpy.random.PCG64DXSM",
        "seed": 20260825,
        "one_generator_for_complete_run": True,
        "reset_between_replicates": False,
    }
    assert bootstrap["percentile"]["method"] == "linear"
    assert "every bootstrap endpoint" in bootstrap["empty_finite_support_rule"]
    assert validator.bootstrap_probe_sha256(_design()) == (
        "f2a5ed36b6bb1c263b16c5888efe6a36b6072d3caf0c98d7ad50fdfca296c9d9"
    )


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (
            (
                "arm_contract",
                "definitions",
                "network_only_shared",
                "cfe_call",
            ),
            "target_specific_raw_active",
        ),
        (
            (
                "temporal_envelope",
                "fixed_parameters",
                "recovery_efficiency",
            ),
            0.86,
        ),
        (
            ("zero_recovery_structural_precheck", "scope"),
            "alpha_1_cells_only",
        ),
        (
            ("bootstrap_contract", "role"),
            "unspecified_resampling",
        ),
        (
            (
                "holdout_identification",
                "transport",
                "ambiguity_set",
            ),
            "independence_coupling_only",
        ),
        (
            (
                "frontier_outputs",
                "first_registered_robust_positive_joint_interaction",
            ),
            "minimum alpha with point I_joint > 1e-6",
        ),
        (
            (
                "attribution_contract",
                "labels",
                "joint_extra_requirement",
                "condition",
            ),
            "point_I_joint_greater_than_1e-6",
        ),
        (
            (
                "holdout_identification",
                "E0",
                "excluded_from_finite_service_denominator",
            ),
            False,
        ),
        (
            ("holdout_policy", "future_calls_or_states_used"),
            True,
        ),
        (
            (
                "planning_formulation",
                "effective_service_requests",
                "cfe",
            ),
            "raw_cfe_request",
        ),
        (
            (
                "holdout_identification",
                "empty_finite_support",
                "transport_solver_called",
            ),
            True,
        ),
        (
            (
                "holdout_identification",
                "transport",
                "operational_label_quantifiers",
                "existential_common_pi_witness_used",
            ),
            True,
        ),
        (
            (
                "bootstrap_contract",
                "pseudorandom_generator",
                "bit_generator",
            ),
            "numpy.random.PCG64",
        ),
    ],
)
def test_complete_semantic_digest_rejects_adversarial_mutation(
    path: tuple[object, ...],
    value: object,
) -> None:
    with pytest.raises(ValueError, match="complete semantic payload digest"):
        validator.validate_design(
            _mutated(path, value),
            require_sealed=_is_sealed(_design()),
        )


def test_removing_maximum_recovery_debt_fails_closed() -> None:
    drifted = copy.deepcopy(_design())
    drifted["holdout_policy"]["current_shared_feasible_action_set_includes"].remove(
        "maximum_recovery_debt"
    )
    with pytest.raises(ValueError, match="complete semantic payload digest"):
        validator.validate_design(
            drifted,
            require_sealed=_is_sealed(_design()),
        )


def test_unknown_nested_field_fails_closed() -> None:
    drifted = copy.deepcopy(_design())
    drifted["bootstrap_contract"]["unregistered_method"] = "other"
    with pytest.raises(ValueError, match="complete semantic payload digest"):
        validator.validate_design(
            drifted,
            require_sealed=_is_sealed(_design()),
        )


def test_duplicate_yaml_key_and_integer_boolean_fail_closed() -> None:
    duplicate = CONFIG.read_text(encoding="utf-8") + "\nschema: duplicate\n"
    with pytest.raises(ValueError, match="duplicate YAML key"):
        validator._load_yaml_text(duplicate, "duplicate config")

    drifted = copy.deepcopy(_design())
    drifted["lifecycle"]["formal_result"] = 0
    with pytest.raises(ValueError, match="lifecycle formal_result drifted"):
        validator.validate_design(
            drifted,
            require_sealed=_is_sealed(_design()),
        )


def test_document_replacement_and_stale_status_fail_closed() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    sealed = _is_sealed(_design())
    current_status = (
        "SEALED_READY_FOR_INDEPENDENT_REVIEW" if sealed else "DRAFT_NONAUTHORITATIVE"
    )
    stale_status = (
        "DRAFT_NONAUTHORITATIVE" if sealed else "SEALED_READY_FOR_INDEPENDENT_REVIEW"
    )
    validator._validate_document_texts(
        spec,
        plan,
        require_sealed=sealed,
    )
    with pytest.raises(ValueError, match="specification semantic digest"):
        validator._validate_document_texts(
            spec.replace("网络安全调用", "网络调用", 1),
            plan,
            require_sealed=sealed,
        )
    with pytest.raises(ValueError, match="plan lifecycle status"):
        validator._validate_document_texts(
            spec,
            plan.replace(
                f"> 状态：`{current_status}`",
                f"> 状态：`{stale_status}`",
                1,
            ),
            require_sealed=sealed,
        )


def test_manifest_unknown_keys_duplicate_json_and_symlink_fail_closed(
    tmp_path: Path,
) -> None:
    digest = "0" * 64
    inner = {
        "schema": ("rq2_joint_deliverability_preregistration_successor_manifest_v5"),
        "files": {relative: digest for relative in validator.EXPECTED_INNER_MEMBERS},
    }
    outer = {
        "schema": ("rq2_joint_deliverability_preregistration_successor_outer_v5"),
        "version": 5,
        "inner": {
            "path": validator.INNER_RELATIVE,
            "sha256": digest,
        },
    }
    validator._validate_manifest_shapes(
        inner,
        outer,
        inner_sha256=digest,
    )

    invalid_inner = copy.deepcopy(inner)
    invalid_inner["unknown"] = False
    with pytest.raises(ValueError, match="inner manifest exact keyset"):
        validator._validate_manifest_shapes(
            invalid_inner,
            outer,
            inner_sha256=digest,
        )
    invalid_outer = copy.deepcopy(outer)
    invalid_outer["inner"]["unknown"] = False
    with pytest.raises(ValueError, match="outer inner exact keyset"):
        validator._validate_manifest_shapes(
            inner,
            invalid_outer,
            inner_sha256=digest,
        )
    with pytest.raises(ValueError, match="duplicate JSON key"):
        validator._load_json_text('{"schema":"a","schema":"b"}', "manifest")

    target = tmp_path / "target"
    target.write_text("member", encoding="utf-8")
    alias = tmp_path / "alias"
    alias.symlink_to(target)
    with pytest.raises(ValueError, match="missing or unsafe"):
        validator._require_regular_file(alias, "manifest member")
    real_directory = tmp_path / "real"
    real_directory.mkdir()
    nested = real_directory / "member"
    nested.write_text("member", encoding="utf-8")
    directory_alias = tmp_path / "directory_alias"
    directory_alias.symlink_to(real_directory, target_is_directory=True)
    with pytest.raises(ValueError, match="unsafe ancestor"):
        validator._require_regular_file(
            directory_alias / "member",
            "manifest member",
        )


def test_document_and_manifest_lifecycle_is_consistent() -> None:
    design = _design()
    sealed = _is_sealed(design)
    expected_status = (
        "SEALED_READY_FOR_INDEPENDENT_REVIEW" if sealed else "DRAFT_NONAUTHORITATIVE"
    )
    assert expected_status in SPEC.read_text(encoding="utf-8")
    assert expected_status in PLAN.read_text(encoding="utf-8")
    if sealed:
        assert INNER.is_file()
        assert OUTER.is_file()
    else:
        assert not INNER.exists()
        assert not OUTER.exists()


def test_validator_is_read_only_and_imports_no_solver_or_runtime_model() -> None:
    tree = ast.parse(Path(validator.__file__).read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(
        name.startswith(
            (
                "gurobi",
                "pyomo",
                "src.models",
                "src.solvers",
                "scipy",
            )
        )
        for name in imports
    )
    source = Path(validator.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "write_text(",
        "write_bytes(",
        'open("w',
        "solver.solve(",
        "linprog(",
    ):
        assert forbidden not in source


def test_current_lifecycle_validator_passes_without_execution() -> None:
    report = validator.validate()
    assert report["validation_passed"] is True
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["independent_R4_review_passed"] is False
    assert report["implementation_bound"] is False
    if report["status"] == "DRAFT_NONAUTHORITATIVE":
        assert report["pre_seal_audit_complete"] is False
        assert report["sealed_file_count"] == 0
    else:
        assert report["status"] == "SEALED_READY_FOR_INDEPENDENT_REVIEW"
        assert report["pre_seal_audit_complete"] is True
        assert report["sealed_file_count"] == 5
