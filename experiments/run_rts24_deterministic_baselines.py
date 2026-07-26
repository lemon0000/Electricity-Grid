"""Run the deterministic RTS-24 B0-B2 baseline gate."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from math import isfinite
from pathlib import Path
from typing import Mapping

import yaml

from src.grid import (
    build_security_states,
    load_rts24,
    non_islanding_branch_indices,
)
from src.models import (
    BaselinePolicy,
    ExistingBranchUpgrade,
    FixedPoi,
    FxQuarter,
    FxServiceEnvelope,
    solve_deterministic_baseline,
)
from src.scenarios.common_input_signature import (
    COMMON_INPUT_SIGNATURE_SCHEMA,
    build_common_input_signature,
    common_input_signature_sha256,
)


_DEMAND_PATH_SOURCE = "rts24_m2_frozen_nondecreasing_path"
_PLANNING_INDEXING = "quarter_root_only_no_state_or_scenario"
_POLICY_ORDER = (
    BaselinePolicy.B0_WAIT,
    BaselinePolicy.B1_FIRM,
    BaselinePolicy.B2_STATIC_FX,
)
_FROZEN_DEMAND_PATH_MW = (50.0, 100.0, 200.0, 250.0)
_FROZEN_HOURS = (2184.0, 2184.0, 2208.0, 2208.0)
_FROZEN_QUARTER_NAMES = ("q1", "q2", "q3", "q4")
_FROZEN_CONTINUOUS_VALIDATION_HOURS = (0.0, 0.0, 0.0, 0.0)
_FROZEN_DISCOUNT_FACTORS = (1.0, 1.0, 1.0, 1.0)
_PLANNING_STATUS = "synthetic_benchmark_not_site_evidence"
_EVIDENCE_LABEL = "synthetic_non_engineering_baseline_gate"
_SERVICE_STATUS = "synthetic_mw_only_envelope_not_contract_evidence"
_RESPONSE_MODEL = "mw_only_sustained_states_no_duration_or_energy_limits"
_WINDOW_STATUS = "not_validated_no_chronological_network_trajectory"
_RESPONSE_STATUS = "synthetic_sensitivity_not_for_certification"
_VALIDATION_STATUS = "synthetic_non_engineering_not_for_certification"
_AC_SCOPE = (
    "not_run_missing_expansion_mva_reactive_and_chronological_network_parameters"
)
_PLANNING_OBJECTIVES = "lexicographic_min_u_then_min_max_x_no_economic_weights"
_OBJECTIVE_UNIT_BASIS = "mwh_physical_planning_metrics"
_POSTHOC_COST_SCOPE = "displayed_minimum_x_plan_m3_dispatch_only"
_STATIC_MILESTONE_SCOPE = (
    "released_capacity_threshold_in_static_dc_state_set_with_declared_"
    "window_assumption"
)
_ENDPOINT_AUDIT_TOLERANCE = 1.0e-8
_MODEL_AUDIT_TOLERANCE = 1.0e-6
_EXPECTED_STAGE_ORDER = (
    "primary_access_shortfall",
    "minimum_x_exposure",
    "maximum_x_exposure",
    "x_exposure_interval_audit",
    "minimum_x_project_count",
    "minimum_x_commissioning_exposure",
    "minimum_x_endpoint_audit",
    "maximum_x_project_count",
    "maximum_x_commissioning_exposure",
    "maximum_x_endpoint_audit",
)
_DISPLAYED_PLAN_STATUS = (
    "deterministic_baseline_displayed_endpoint_non_economic_normalization"
)
_COMMON_INPUT_SIGNATURE_ID = "rts24_b0_b2_common_inputs_v1"
_ENDPOINT_FIELDS = (
    "run_feasible",
    "policy",
    "policy_feasible",
    "endpoint_name",
    "endpoint_is_displayed",
    "primary_access_shortfall_mwh",
    "primary_tolerance_mwh",
    "minimum_x_exposure_mwh",
    "maximum_x_exposure_mwh",
    "x_exposure_tolerance_mwh",
    "endpoint_access_shortfall_mwh",
    "endpoint_x_exposure_mwh",
    "project_started",
    "project_start_quarter",
    "normalization_label",
    "endpoint_audit_json",
    "stage_diagnostics_json",
    "runner_contract_audit_json",
    "m3_dispatch_diagnostics_json",
    "security_certified",
    "evidence_label",
)
_QUARTER_FIELDS = (
    "run_feasible",
    "policy",
    "policy_feasible",
    "endpoint_name",
    "endpoint_is_displayed",
    "quarter",
    "system_load_multiplier",
    "data_center_demand_mw",
    "operating_hours",
    "continuous_validation_hours",
    "firm_capacity_mw",
    "conditional_capacity_mw",
    "total_capacity_mw",
    "access_shortfall_mw",
    "project_commissioned",
    "state_call_mw_json",
    "state_poi_load_mw_json",
    "endpoint_primary_band_violation_mwh",
    "endpoint_x_band_violation_mwh",
    "endpoint_maximum_original_constraint_violation",
    "endpoint_maximum_integrality_violation",
    "runner_contract_audit_json",
    "milestone_metric_scope",
    "T_module_json",
    "T20_json",
    "T50_json",
    "T100_json",
    "continuous_capacity_milestones_certified",
    "security_certified",
    "evidence_label",
)


def _jsonable(item: object) -> object:
    if isinstance(item, Enum):
        return item.value
    if is_dataclass(item):
        return _jsonable(asdict(item))
    if isinstance(item, Mapping):
        return {str(key): _jsonable(value) for key, value in item.items()}
    if isinstance(item, (tuple, list, set, frozenset)):
        return [_jsonable(value) for value in item]
    if isinstance(item, float) and not isfinite(item):
        raise ValueError("Baseline outputs must not contain non-finite numbers")
    if hasattr(item, "__dict__"):
        return {
            str(key): _jsonable(value)
            for key, value in vars(item).items()
            if not str(key).startswith("_")
        }
    return item


def _write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned_rows = _jsonable(rows)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_rows)


def _compact_json(item: object) -> str:
    return json.dumps(
        _jsonable(item),
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _milestone(milestone: object | None) -> dict[str, object] | None:
    if milestone is None:
        return None
    return {
        "threshold_mw": getattr(milestone, "threshold_mw", None),
        "reached": getattr(milestone, "reached", None),
        "quarter": getattr(milestone, "quarter", None),
        "right_censored": getattr(milestone, "right_censored", None),
        "censor_quarter": getattr(milestone, "censor_quarter", None),
        "display_label": getattr(milestone, "display_label", None),
    }


def _milestone_diagnostics(dispatch: object | None) -> dict[str, object]:
    milestones = None if dispatch is None else getattr(dispatch, "milestones", None)
    return {
        "metric_scope": (
            None if milestones is None else getattr(milestones, "metric_scope", None)
        ),
        "T_module": (
            None
            if milestones is None
            else _milestone(getattr(milestones, "t_module", None))
        ),
        "T20": (
            None if milestones is None else _milestone(getattr(milestones, "t20", None))
        ),
        "T50": (
            None if milestones is None else _milestone(getattr(milestones, "t50", None))
        ),
        "T100": (
            None
            if milestones is None
            else _milestone(getattr(milestones, "t100", None))
        ),
        "continuous_capacity_milestones_certified": False,
    }


def _dispatch_diagnostics(dispatch: object | None) -> dict[str, object] | None:
    if dispatch is None:
        return None
    fields = (
        "feasible",
        "termination_condition",
        "solver_status",
        "solver_message",
        "objective",
        "primary_optimization_objective",
        "canonical_dispatch_primary_objective",
        "primary_qp_solver",
        "primary_qp_status",
        "primary_qp_iterations",
        "primary_qp_primal_residual",
        "primary_qp_dual_residual",
        "primary_qp_max_constraint_violation",
        "primary_qp_max_bound_projection",
        "primary_qp_solve_seconds",
        "primary_linear_repair_objective_deviation",
        "primary_linear_repair_objective_deviation_tolerance",
        "primary_linear_repair_total_generation_movement_mw",
        "primary_linear_repair_max_generation_movement_mw",
        "primary_linear_repair_generation_movement_tolerance_mw",
        "primary_linear_repair_acceptance_interpretation",
        "investment_cost",
        "operating_cost",
        "access_shortfall_cost",
        "minimum_call_certificate_mw_sum",
        "project_started",
        "start_quarter",
        "commissioned_by_quarter",
        "firm_capacity_mw",
        "conditional_capacity_mw",
        "total_capacity_mw",
        "connected_demand_mw",
        "firm_demand_mw",
        "active_conditional_demand_mw",
        "access_shortfall_mw",
        "actual_grid_curtailment_mw",
        "actual_poi_load_mw",
        "certified_grid_curtailment_mw",
        "certified_poi_load_mw",
        "firm_breach_mw",
        "conditional_breach_mw",
        "actual_state_results",
        "certified_state_results",
        "effective_branch_ratings_mw",
        "base_operating_cost_per_hour",
        "unused_capacity_mw_year",
        "cost_interpretation",
        "capacity_interpretation",
        "certified_dispatch_interpretation",
        "plan_parameter_status",
        "service_parameter_status",
        "response_model",
        "breach_diagnostics_enabled",
        "states",
        "excluded_branch_indices",
    )
    diagnostics = {
        field: _jsonable(getattr(dispatch, field, None)) for field in fields
    }
    diagnostics["milestones"] = _milestone_diagnostics(dispatch)
    return diagnostics


def _dispatch_csv_diagnostics(
    diagnostics: dict[str, object] | None,
) -> dict[str, object] | None:
    if diagnostics is None:
        return None
    fields = (
        "feasible",
        "termination_condition",
        "solver_status",
        "solver_message",
        "objective",
        "primary_optimization_objective",
        "canonical_dispatch_primary_objective",
        "primary_qp_solver",
        "primary_qp_status",
        "primary_qp_iterations",
        "primary_qp_primal_residual",
        "primary_qp_dual_residual",
        "primary_qp_max_constraint_violation",
        "primary_qp_max_bound_projection",
        "primary_qp_solve_seconds",
        "primary_linear_repair_objective_deviation",
        "primary_linear_repair_objective_deviation_tolerance",
        "primary_linear_repair_total_generation_movement_mw",
        "primary_linear_repair_max_generation_movement_mw",
        "primary_linear_repair_generation_movement_tolerance_mw",
        "primary_linear_repair_acceptance_interpretation",
        "project_started",
        "start_quarter",
        "commissioned_by_quarter",
        "firm_capacity_mw",
        "conditional_capacity_mw",
        "total_capacity_mw",
        "access_shortfall_mw",
        "cost_interpretation",
        "capacity_interpretation",
        "certified_dispatch_interpretation",
        "plan_parameter_status",
        "service_parameter_status",
        "response_model",
        "excluded_branch_indices",
        "milestones",
    )
    return {field: diagnostics.get(field) for field in fields}


def _endpoint_audit(endpoint: object | None) -> dict[str, object] | None:
    return None if endpoint is None else _jsonable(endpoint)


def _mapping_matches(
    first: object,
    second: object,
    *,
    tolerance: float = _MODEL_AUDIT_TOLERANCE,
) -> bool:
    if not isinstance(first, Mapping) or not isinstance(second, Mapping):
        return False
    if set(first) != set(second):
        return False
    try:
        return all(
            isfinite(float(first[key]))
            and isfinite(float(second[key]))
            and abs(float(first[key]) - float(second[key])) <= tolerance
            for key in first
        )
    except (TypeError, ValueError):
        return False


def _endpoint_contract_reasons(
    endpoint: object | None,
    *,
    primary_target_mwh: object,
    x_target_mwh: object,
) -> list[str]:
    if endpoint is None:
        return ["endpoint_missing"]
    reasons = []
    if getattr(endpoint, "planning_variable_indexing", None) != _PLANNING_INDEXING:
        reasons.append("endpoint_planning_indexing_mismatch")
    numeric_limits = (
        ("access_shortfall_mwh", None),
        ("conditional_capacity_exposure_mwh", None),
        ("primary_band_violation_mwh", _ENDPOINT_AUDIT_TOLERANCE),
        ("x_band_violation_mwh", _ENDPOINT_AUDIT_TOLERANCE),
        (
            "maximum_original_constraint_violation",
            _MODEL_AUDIT_TOLERANCE,
        ),
        ("maximum_integrality_violation", _MODEL_AUDIT_TOLERANCE),
    )
    for field, upper_limit in numeric_limits:
        try:
            number = float(getattr(endpoint, field))
        except (AttributeError, TypeError, ValueError):
            reasons.append(f"endpoint_{field}_missing_or_invalid")
            continue
        if not isfinite(number) or number < -_ENDPOINT_AUDIT_TOLERANCE:
            reasons.append(f"endpoint_{field}_nonfinite_or_negative")
        elif upper_limit is not None and number > upper_limit:
            reasons.append(f"endpoint_{field}_exceeds_tolerance")
    try:
        primary_deviation = abs(
            float(endpoint.primary_target_mwh) - float(primary_target_mwh)
        )
        x_deviation = abs(float(endpoint.x_exposure_target_mwh) - float(x_target_mwh))
    except (AttributeError, TypeError, ValueError):
        reasons.append("endpoint_target_missing_or_invalid")
    else:
        if not isfinite(primary_deviation) or primary_deviation > _ENDPOINT_AUDIT_TOLERANCE:
            reasons.append("endpoint_primary_target_mismatch")
        if not isfinite(x_deviation) or x_deviation > _ENDPOINT_AUDIT_TOLERANCE:
            reasons.append("endpoint_x_target_mismatch")
    return reasons


def _dispatch_state_audit(dispatch: object, quarter_names: tuple[str, ...]) -> dict:
    reasons = []
    states = tuple(getattr(dispatch, "states", ()))
    state_names = tuple(getattr(state, "name", None) for state in states)
    expected_state_results = len(quarter_names) * len(states)
    maximum_balance_residual = 0.0
    counts = {}
    for layer_name, field in (
        ("actual", "actual_state_results"),
        ("contract_counterfactual", "certified_state_results"),
    ):
        layer_results = getattr(dispatch, field, None)
        count = 0
        if not isinstance(layer_results, Mapping):
            reasons.append(f"{layer_name}_state_results_missing")
            counts[layer_name] = 0
            continue
        for quarter_name in quarter_names:
            quarter_results = layer_results.get(quarter_name)
            if not isinstance(quarter_results, Mapping):
                reasons.append(f"{layer_name}_{quarter_name}_state_results_missing")
                continue
            if tuple(quarter_results) != state_names:
                reasons.append(f"{layer_name}_{quarter_name}_state_set_mismatch")
            for state_result in quarter_results.values():
                count += 1
                if not bool(getattr(state_result, "feasible", False)):
                    reasons.append(f"{layer_name}_infeasible_state_result")
                try:
                    residual = float(state_result.max_balance_residual_mw)
                except (AttributeError, TypeError, ValueError):
                    reasons.append(f"{layer_name}_invalid_balance_residual")
                else:
                    if not isfinite(residual):
                        reasons.append(f"{layer_name}_nonfinite_balance_residual")
                    else:
                        maximum_balance_residual = max(
                            maximum_balance_residual,
                            residual,
                        )
        counts[layer_name] = count
        if count != expected_state_results:
            reasons.append(f"{layer_name}_state_result_count_mismatch")
    if not states:
        reasons.append("dispatch_states_missing")
    if maximum_balance_residual > _MODEL_AUDIT_TOLERANCE:
        reasons.append("dispatch_balance_residual_exceeds_tolerance")
    return {
        "passed": not reasons,
        "failure_reasons": reasons,
        "state_names": list(state_names),
        "expected_state_results_per_layer": expected_state_results,
        "state_result_counts": counts,
        "maximum_balance_residual_mw": maximum_balance_residual,
    }


def _result_contract_audit(
    result: object,
    *,
    policy: BaselinePolicy,
    quarters: tuple[FxQuarter, ...],
    poi: FixedPoi,
    service_envelope: FxServiceEnvelope,
) -> dict[str, object]:
    reasons = []
    if getattr(result, "policy", None) is not policy:
        reasons.append("returned_policy_mismatch")
    if not bool(getattr(result, "feasible", False)):
        reasons.append("baseline_core_not_feasible")
    if getattr(result, "failure_stage", None) is not None:
        reasons.append("baseline_failure_stage_not_clear")
    if getattr(result, "planning_variable_indexing", None) != _PLANNING_INDEXING:
        reasons.append("result_planning_indexing_mismatch")

    stages = tuple(getattr(result, "stage_diagnostics", ()))
    if tuple(getattr(stage, "stage", None) for stage in stages) != (
        _EXPECTED_STAGE_ORDER
    ):
        reasons.append("stage_order_or_completeness_mismatch")
    if not stages or not all(bool(getattr(stage, "accepted", False)) for stage in stages):
        reasons.append("one_or_more_stages_not_accepted")

    minimum_endpoint = getattr(result, "minimum_x_endpoint", None)
    maximum_endpoint = getattr(result, "maximum_x_endpoint", None)
    displayed = getattr(result, "displayed_endpoint", None)
    if displayed is None or displayed != minimum_endpoint:
        reasons.append("displayed_endpoint_is_not_minimum_x_endpoint")
    if getattr(result, "displayed_endpoint_name", None) != "minimum_x_endpoint":
        reasons.append("displayed_endpoint_name_mismatch")
    minimum_x = getattr(result, "minimum_x_exposure_mwh", None)
    maximum_x = getattr(result, "maximum_x_exposure_mwh", None)
    primary = getattr(result, "primary_access_shortfall_mwh", None)
    try:
        if not all(isfinite(float(number)) for number in (primary, minimum_x, maximum_x)):
            reasons.append("nonfinite_primary_or_x_endpoint")
        elif float(minimum_x) > float(maximum_x):
            reasons.append("x_interval_reversed")
    except (TypeError, ValueError):
        reasons.append("primary_or_x_endpoint_missing")
    reasons.extend(
        f"minimum_x:{reason}"
        for reason in _endpoint_contract_reasons(
            minimum_endpoint,
            primary_target_mwh=primary,
            x_target_mwh=minimum_x,
        )
    )
    reasons.extend(
        f"maximum_x:{reason}"
        for reason in _endpoint_contract_reasons(
            maximum_endpoint,
            primary_target_mwh=primary,
            x_target_mwh=maximum_x,
        )
    )

    dispatch = getattr(result, "dispatch_result", None)
    state_audit = {
        "passed": False,
        "failure_reasons": ["dispatch_missing"],
    }
    if dispatch is None or not bool(getattr(dispatch, "feasible", False)):
        reasons.append("displayed_m3_dispatch_not_feasible")
    elif minimum_endpoint is not None:
        if not _mapping_matches(
            getattr(dispatch, "firm_capacity_mw", None),
            minimum_endpoint.firm_capacity_mw,
        ):
            reasons.append("m3_firm_capacity_mismatch")
        if not _mapping_matches(
            getattr(dispatch, "conditional_capacity_mw", None),
            minimum_endpoint.conditional_capacity_mw,
        ):
            reasons.append("m3_conditional_capacity_mismatch")
        if not _mapping_matches(
            getattr(dispatch, "total_capacity_mw", None),
            minimum_endpoint.total_capacity_mw,
        ):
            reasons.append("m3_total_capacity_mismatch")
        if not _mapping_matches(
            getattr(dispatch, "access_shortfall_mw", None),
            minimum_endpoint.access_shortfall_mw,
        ):
            reasons.append("m3_access_shortfall_mismatch")
        if getattr(dispatch, "start_quarter", None) != (
            minimum_endpoint.project_start_quarter
        ):
            reasons.append("m3_project_start_mismatch")
        if getattr(dispatch, "commissioned_by_quarter", None) != (
            minimum_endpoint.commissioned_by_quarter
        ):
            reasons.append("m3_commissioning_mismatch")
        if getattr(dispatch, "plan_parameter_status", None) != _DISPLAYED_PLAN_STATUS:
            reasons.append("m3_displayed_plan_status_mismatch")
        if getattr(dispatch, "service_parameter_status", None) != (
            service_envelope.parameter_status
        ):
            reasons.append("m3_service_status_mismatch")
        if tuple(getattr(dispatch, "states", ())) != tuple(
            getattr(result, "states", ())
        ):
            reasons.append("m3_security_state_set_mismatch")
        state_audit = _dispatch_state_audit(
            dispatch,
            tuple(quarter.name for quarter in quarters),
        )
        if not state_audit["passed"]:
            reasons.append("m3_state_audit_failed")
        for breach_field in ("firm_breach_mw", "conditional_breach_mw"):
            breach = getattr(dispatch, breach_field, None)
            if not isinstance(breach, Mapping) or tuple(breach) != tuple(
                quarter.name for quarter in quarters
            ):
                reasons.append(f"m3_{breach_field}_quarter_set_mismatch")
                continue
            if any(
                not isinstance(breach[quarter.name], Mapping)
                or tuple(breach[quarter.name])
                != tuple(getattr(state, "name", None) for state in dispatch.states)
                for quarter in quarters
            ):
                reasons.append(f"m3_{breach_field}_state_set_mismatch")
                continue
            try:
                maximum_breach = max(
                    abs(float(number))
                    for quarter_values in breach.values()
                    for number in quarter_values.values()
                )
            except (AttributeError, TypeError, ValueError):
                reasons.append(f"m3_{breach_field}_missing_or_invalid")
            else:
                if not isfinite(maximum_breach) or maximum_breach > (
                    _MODEL_AUDIT_TOLERANCE
                ):
                    reasons.append(f"m3_{breach_field}_exceeds_tolerance")

        milestones = getattr(dispatch, "milestones", None)
        if milestones is None:
            reasons.append("m3_milestones_missing")
        else:
            if getattr(milestones, "metric_scope", None) != _STATIC_MILESTONE_SCOPE:
                reasons.append("m3_milestone_scope_mismatch")
            expected_thresholds = {
                "t_module": service_envelope.minimum_operational_block_mw,
                "t20": 0.20 * poi.application_capacity_mw,
                "t50": 0.50 * poi.application_capacity_mw,
                "t100": poi.application_capacity_mw,
            }
            for field, expected_threshold in expected_thresholds.items():
                milestone = getattr(milestones, field, None)
                if milestone is None:
                    reasons.append(f"m3_{field}_missing")
                elif bool(getattr(milestone, "reached", True)) or not bool(
                    getattr(milestone, "right_censored", False)
                ):
                    reasons.append(f"m3_{field}_must_be_right_censored")
                else:
                    try:
                        threshold = float(milestone.threshold_mw)
                    except (AttributeError, TypeError, ValueError):
                        reasons.append(f"m3_{field}_threshold_invalid")
                    else:
                        if not isfinite(threshold) or abs(
                            threshold - expected_threshold
                        ) > _ENDPOINT_AUDIT_TOLERANCE:
                            reasons.append(f"m3_{field}_threshold_mismatch")
                    if getattr(milestone, "quarter", None) is not None:
                        reasons.append(f"m3_{field}_quarter_must_be_none")
                    if getattr(milestone, "censor_quarter", None) != (
                        quarters[-1].name
                    ):
                        reasons.append(f"m3_{field}_censor_quarter_mismatch")

    return {
        "passed": not reasons,
        "failure_reasons": reasons,
        "stage_count": len(stages),
        "displayed_plan_matches_m3": not any(
            reason.startswith("m3_") and reason.endswith("mismatch")
            for reason in reasons
        ),
        "m3_state_audit": state_audit,
    }


def run(
    config_path: Path,
    *,
    _common_input_signature_only: bool = False,
) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["case"] != {"name": "case24_ieee_rts", "source": "pypower"}:
        raise ValueError("This experiment requires PYPOWER case24_ieee_rts")
    planning = config["planning"]
    if planning["model"] != "deterministic_b0_b2_lexicographic_access_baselines":
        raise ValueError("Unsupported deterministic baseline model")
    if planning["parameter_status"] != _PLANNING_STATUS:
        raise ValueError("Planning inputs must retain their synthetic status")
    if planning["evidence_label"] != _EVIDENCE_LABEL:
        raise ValueError("Planning evidence must remain explicitly non-engineering")
    if planning["demand_path_source"] != _DEMAND_PATH_SOURCE:
        raise ValueError("Baseline demand path must retain the frozen M2 source")
    if planning["planning_variable_indexing"] != _PLANNING_INDEXING:
        raise ValueError("Unsupported planning-variable indexing")
    policies = tuple(BaselinePolicy(name) for name in planning["policy_order"])
    if policies != _POLICY_ORDER:
        raise ValueError("Baseline policies must run in B0, B1, B2 order")
    quarters = tuple(
        FxQuarter(
            name=row["name"],
            system_load_multiplier=float(row["system_load_multiplier"]),
            data_center_demand_mw=float(row["data_center_demand_mw"]),
            operating_hours=float(row["operating_hours"]),
            continuous_validation_hours=float(row["continuous_validation_hours"]),
            discount_factor=float(row["discount_factor"]),
        )
        for row in planning["quarters"]
    )
    if tuple(quarter.data_center_demand_mw for quarter in quarters) != (
        _FROZEN_DEMAND_PATH_MW
    ):
        raise ValueError("Baseline demand must be the frozen 50/100/200/250 MW path")
    if tuple(quarter.name for quarter in quarters) != _FROZEN_QUARTER_NAMES:
        raise ValueError("Baseline quarter names must remain q1/q2/q3/q4")
    if tuple(quarter.operating_hours for quarter in quarters) != _FROZEN_HOURS:
        raise ValueError("Baseline quarter hours must match the frozen M2 path")
    if tuple(
        quarter.continuous_validation_hours for quarter in quarters
    ) != _FROZEN_CONTINUOUS_VALIDATION_HOURS:
        raise ValueError(
            "Static B0-B2 baselines must keep continuous validation hours at zero"
        )
    if tuple(quarter.discount_factor for quarter in quarters) != (
        _FROZEN_DISCOUNT_FACTORS
    ):
        raise ValueError("Baseline discount factors must remain 1.0")
    if any(quarter.system_load_multiplier != 0.8 for quarter in quarters):
        raise ValueError("Baseline system load multiplier must remain 0.8")

    poi_config = config["fixed_poi"]
    if poi_config["parameter_status"] != _PLANNING_STATUS:
        raise ValueError("POI inputs must retain their synthetic status")
    poi = FixedPoi(
        bus=int(poi_config["bus"]),
        initial_capacity_mw=float(poi_config["initial_capacity_mw"]),
        application_capacity_mw=float(poi_config["application_capacity_mw"]),
    )
    project_config = config["existing_branch_upgrade"]
    if project_config["parameter_status"] != _PLANNING_STATUS:
        raise ValueError("Project inputs must retain their synthetic status")
    project = ExistingBranchUpgrade(
        name=project_config["name"],
        lead_time_quarters=int(project_config["lead_time_quarters"]),
        rate_a_increase_mw={
            int(index): float(increase)
            for index, increase in project_config["rate_a_increase_mw"].items()
        },
        rate_c_increase_mw={
            int(index): float(increase)
            for index, increase in project_config["rate_c_increase_mw"].items()
        },
        poi_capacity_increase_mw=float(
            project_config["poi_capacity_increase_mw"]
        ),
        investment_cost=float(project_config["investment_cost"]),
        parameter_status=project_config["parameter_status"],
    )
    service_config = config["service_envelope"]
    if service_config["parameter_status"] != _SERVICE_STATUS:
        raise ValueError("Service envelope must retain its synthetic status")
    if service_config["response_model"] != _RESPONSE_MODEL:
        raise ValueError("Unsupported F/X response model")
    if service_config["continuous_window_status"] != _WINDOW_STATUS:
        raise ValueError("Continuous-window limitation must remain explicit")
    service_envelope = FxServiceEnvelope(
        max_conditional_capacity_mw=float(
            service_config["max_conditional_capacity_mw"]
        ),
        minimum_operational_block_mw=float(
            service_config["minimum_operational_block_mw"]
        ),
        minimum_validation_hours=float(
            service_config["minimum_validation_hours"]
        ),
        response_model=service_config["response_model"],
        parameter_status=service_config["parameter_status"],
    )

    data = load_rts24()
    security = config["security"]
    if security["branch_set"] != "all_non_islanding":
        raise ValueError("Unsupported branch contingency set")
    if security["generator_set"] != "all_positive_capacity":
        raise ValueError("Unsupported generator contingency set")
    if security["excluded_islanding_policy"] != "report_as_failure":
        raise ValueError("Unsupported islanding-contingency policy")
    if security["response_parameter_status"] != _RESPONSE_STATUS:
        raise ValueError("Redispatch status must remain non-certifying")
    redispatch_fraction = float(security["redispatch_fraction_pmax"])
    if not isfinite(redispatch_fraction) or not 0.0 <= redispatch_fraction <= 1.0:
        raise ValueError("Redispatch fraction must be finite and within [0, 1]")
    redispatch = {
        generator.index: redispatch_fraction * generator.p_max_mw
        for generator in data.generators
    }
    branch_indices = tuple(non_islanding_branch_indices(data))
    generator_indices = tuple(
        generator.index
        for generator in data.generators
        if generator.in_service and generator.p_max_mw > 0.0
    )
    project_branch_indices = set(project.rate_a_increase_mw) | set(
        project.rate_c_increase_mw
    )
    missing_project_contingencies = project_branch_indices - set(branch_indices)
    if missing_project_contingencies:
        raise ValueError(
            "Every upgraded branch must be in the formal N-1 set: "
            f"{sorted(missing_project_contingencies)}"
        )
    if config["validation"]["security_certified"] is not False:
        raise ValueError("This synthetic baseline gate cannot claim certification")

    objective = config["objective"]
    if objective["planning_objectives"] != _PLANNING_OBJECTIVES:
        raise ValueError("Unsupported non-economic planning objectives")
    if objective["unit_basis"] != _OBJECTIVE_UNIT_BASIS:
        raise ValueError("Planning objective units must remain physical MWh")
    if objective["posthoc_cost_scope"] != _POSTHOC_COST_SCOPE:
        raise ValueError("Costs may enter only displayed-plan posthoc dispatch")
    validation = config["validation"]
    if validation["evidence_status"] != _VALIDATION_STATUS:
        raise ValueError("Validation evidence must remain non-certifying")
    if validation["ac_scope"] != _AC_SCOPE:
        raise ValueError("Unsupported AC-validation scope")
    solver_name = config["solver"]["name"]
    security_states = build_security_states(
        branch_indices,
        generator_indices,
        security["immediate_branch_rating"],
        security["sustained_rating"],
    )
    common_input_signature = build_common_input_signature(
        case=config["case"],
        source_package=data.source_package,
        source_version=data.source_version,
        demand_path_source=planning["demand_path_source"],
        quarters=quarters,
        poi=poi,
        project=project,
        service_envelope=service_envelope,
        service_configuration=service_config,
        branch_indices=branch_indices,
        generator_indices=generator_indices,
        immediate_rating=security["immediate_branch_rating"],
        sustained_rating=security["sustained_rating"],
        security_configuration=security,
        security_states=security_states,
        redispatch_up_mw=redispatch,
        redispatch_down_mw=redispatch,
        objective=objective,
        solver=config["solver"],
    )
    common_input_signature_hash = common_input_signature_sha256(
        common_input_signature
    )
    if _common_input_signature_only:
        return {
            "common_input_signature_id": _COMMON_INPUT_SIGNATURE_ID,
            "common_input_signature_schema": COMMON_INPUT_SIGNATURE_SCHEMA,
            "common_input_signature_sha256": common_input_signature_hash,
            "common_input_signature": common_input_signature,
        }

    policy_runs = []
    for policy in policies:
        try:
            result = solve_deterministic_baseline(
                data,
                policy=policy,
                quarters=quarters,
                poi=poi,
                project=project,
                service_envelope=service_envelope,
                redispatch_up_mw=redispatch,
                redispatch_down_mw=redispatch,
                access_shortfall_cost_per_mwh=float(
                    objective["access_shortfall_cost_per_mwh"]
                ),
                branch_indices=branch_indices,
                generator_indices=generator_indices,
                immediate_rating=security["immediate_branch_rating"],
                sustained_rating=security["sustained_rating"],
                solver_name=solver_name,
            )
            dispatch = getattr(result, "dispatch_result", None)
            contract_audit = _result_contract_audit(
                result,
                policy=policy,
                quarters=quarters,
                poi=poi,
                service_envelope=service_envelope,
            )
            passed = bool(contract_audit["passed"])
            displayed = getattr(result, "displayed_endpoint", None) if passed else None
            policy_runs.append(
                {
                    "policy": policy,
                    "result": result,
                    "passed": passed,
                    "displayed": displayed,
                    "contract_audit": contract_audit,
                    "exception_type": None,
                    "exception_message": None,
                }
            )
        except Exception as error:  # policy-level fail-closed audit
            policy_runs.append(
                {
                    "policy": policy,
                    "result": None,
                    "passed": False,
                    "displayed": None,
                    "contract_audit": {
                        "passed": False,
                        "failure_reasons": ["policy_exception"],
                    },
                    "exception_type": type(error).__name__,
                    "exception_message": str(error),
                }
            )

    run_feasible = len(policy_runs) == len(policies) and all(
        bool(run["passed"]) for run in policy_runs
    )
    evidence_label = planning["evidence_label"]
    policy_summaries = []
    endpoint_rows = []
    quarter_rows = []
    for run_record in policy_runs:
        policy = run_record["policy"]
        result = run_record["result"]
        passed = bool(run_record["passed"])
        dispatch = None if result is None else getattr(result, "dispatch_result", None)
        milestones = _milestone_diagnostics(dispatch)
        minimum_endpoint = (
            None if result is None else getattr(result, "minimum_x_endpoint", None)
        )
        maximum_endpoint = (
            None if result is None else getattr(result, "maximum_x_endpoint", None)
        )
        displayed_name = (
            getattr(result, "displayed_endpoint_name", None)
            if passed and run_feasible
            else None
        )
        stage_diagnostics = (
            [] if result is None else _jsonable(getattr(result, "stage_diagnostics", ()))
        )
        dispatch_diagnostics = _dispatch_diagnostics(dispatch)
        policy_summary = {
            "policy": policy.value,
            "common_input_signature_id": _COMMON_INPUT_SIGNATURE_ID,
            "common_input_signature_schema": COMMON_INPUT_SIGNATURE_SCHEMA,
            "common_input_signature_sha256": common_input_signature_hash,
            "feasible": passed,
            "reported_core_feasible": (
                None if result is None else bool(getattr(result, "feasible", False))
            ),
            "termination_condition": (
                "policy_exception"
                if result is None
                else getattr(result, "termination_condition", None)
            ),
            "solver_status": (
                "warning" if result is None else getattr(result, "solver_status", None)
            ),
            "solver_message": (
                run_record["exception_message"]
                if result is None
                else getattr(result, "solver_message", None)
            ),
            "exception_type": run_record["exception_type"],
            "failure_stage": (
                None if result is None else getattr(result, "failure_stage", None)
            ),
            "primary_access_shortfall_mwh": (
                None
                if result is None
                else getattr(result, "primary_access_shortfall_mwh", None)
            ),
            "primary_tolerance_mwh": (
                None if result is None else getattr(result, "primary_tolerance_mwh", None)
            ),
            "minimum_x_exposure_mwh": (
                None
                if result is None
                else getattr(result, "minimum_x_exposure_mwh", None)
            ),
            "maximum_x_exposure_mwh": (
                None
                if result is None
                else getattr(result, "maximum_x_exposure_mwh", None)
            ),
            "x_exposure_tolerance_mwh": (
                None
                if result is None
                else getattr(result, "x_exposure_tolerance_mwh", None)
            ),
            "displayed_endpoint_name": displayed_name,
            "displayed_endpoint": _endpoint_audit(
                run_record["displayed"] if run_feasible else None
            ),
            "minimum_x_endpoint": _endpoint_audit(minimum_endpoint),
            "maximum_x_endpoint": _endpoint_audit(maximum_endpoint),
            "stage_diagnostics": stage_diagnostics,
            "runner_contract_audit": _jsonable(run_record["contract_audit"]),
            "m3_dispatch_diagnostics": dispatch_diagnostics,
            "milestones": milestones,
            "security_certified": False,
            "evidence_label": evidence_label,
        }
        policy_summaries.append(policy_summary)

        endpoints = (
            ("minimum_x_endpoint", minimum_endpoint),
            ("maximum_x_endpoint", maximum_endpoint),
        )
        if all(endpoint is None for _, endpoint in endpoints):
            endpoints = (("unavailable", None),)
        for endpoint_name, endpoint in endpoints:
            endpoint_audit = _endpoint_audit(endpoint)
            endpoint_rows.append(
                {
                    "run_feasible": run_feasible,
                    "policy": policy.value,
                    "policy_feasible": passed,
                    "endpoint_name": endpoint_name,
                    "endpoint_is_displayed": bool(
                        passed and endpoint_name == displayed_name
                    ),
                    "primary_access_shortfall_mwh": policy_summary[
                        "primary_access_shortfall_mwh"
                    ],
                    "primary_tolerance_mwh": policy_summary[
                        "primary_tolerance_mwh"
                    ],
                    "minimum_x_exposure_mwh": policy_summary[
                        "minimum_x_exposure_mwh"
                    ],
                    "maximum_x_exposure_mwh": policy_summary[
                        "maximum_x_exposure_mwh"
                    ],
                    "x_exposure_tolerance_mwh": policy_summary[
                        "x_exposure_tolerance_mwh"
                    ],
                    "endpoint_access_shortfall_mwh": (
                        None if endpoint is None else endpoint.access_shortfall_mwh
                    ),
                    "endpoint_x_exposure_mwh": (
                        None
                        if endpoint is None
                        else endpoint.conditional_capacity_exposure_mwh
                    ),
                    "project_started": (
                        None if endpoint is None else endpoint.project_started
                    ),
                    "project_start_quarter": (
                        None if endpoint is None else endpoint.project_start_quarter
                    ),
                    "normalization_label": (
                        None if endpoint is None else endpoint.normalization_label
                    ),
                    "endpoint_audit_json": _compact_json(endpoint_audit),
                    "stage_diagnostics_json": _compact_json(stage_diagnostics),
                    "runner_contract_audit_json": _compact_json(
                        run_record["contract_audit"]
                    ),
                    "m3_dispatch_diagnostics_json": _compact_json(
                        _dispatch_csv_diagnostics(dispatch_diagnostics)
                        if run_feasible and endpoint_name == displayed_name
                        else None
                    ),
                    "security_certified": False,
                    "evidence_label": evidence_label,
                }
            )
            if endpoint is None:
                continue
            for quarter in quarters:
                quarter_rows.append(
                    {
                        "run_feasible": run_feasible,
                        "policy": policy.value,
                        "policy_feasible": passed,
                        "endpoint_name": endpoint_name,
                        "endpoint_is_displayed": bool(
                            passed and endpoint_name == displayed_name
                        ),
                        "quarter": quarter.name,
                        "system_load_multiplier": quarter.system_load_multiplier,
                        "data_center_demand_mw": quarter.data_center_demand_mw,
                        "operating_hours": quarter.operating_hours,
                        "continuous_validation_hours": (
                            quarter.continuous_validation_hours
                        ),
                        "firm_capacity_mw": endpoint.firm_capacity_mw[quarter.name],
                        "conditional_capacity_mw": (
                            endpoint.conditional_capacity_mw[quarter.name]
                        ),
                        "total_capacity_mw": endpoint.total_capacity_mw[quarter.name],
                        "access_shortfall_mw": (
                            endpoint.access_shortfall_mw[quarter.name]
                        ),
                        "project_commissioned": (
                            endpoint.commissioned_by_quarter[quarter.name]
                        ),
                        "state_call_mw_json": _compact_json(
                            endpoint.state_call_mw[quarter.name]
                        ),
                        "state_poi_load_mw_json": _compact_json(
                            endpoint.state_poi_load_mw[quarter.name]
                        ),
                        "endpoint_primary_band_violation_mwh": getattr(
                            endpoint, "primary_band_violation_mwh", None
                        ),
                        "endpoint_x_band_violation_mwh": getattr(
                            endpoint, "x_band_violation_mwh", None
                        ),
                        "endpoint_maximum_original_constraint_violation": getattr(
                            endpoint,
                            "maximum_original_constraint_violation",
                            None,
                        ),
                        "endpoint_maximum_integrality_violation": getattr(
                            endpoint, "maximum_integrality_violation", None
                        ),
                        "runner_contract_audit_json": _compact_json(
                            run_record["contract_audit"]
                        ),
                        "milestone_metric_scope": milestones["metric_scope"],
                        "T_module_json": _compact_json(milestones["T_module"]),
                        "T20_json": _compact_json(milestones["T20"]),
                        "T50_json": _compact_json(milestones["T50"]),
                        "T100_json": _compact_json(milestones["T100"]),
                        "continuous_capacity_milestones_certified": False,
                        "security_certified": False,
                        "evidence_label": evidence_label,
                    }
                )

    blockers = [
        "synthetic_poi_project_service_and_redispatch_not_engineering_evidence",
        "security_certified_false",
        "ac_validation_not_run",
        "continuous_validation_hours_zero_static_states_do_not_certify_T_metrics",
        "deterministic_load_only_baselines_without_uncertainty_or_renewables",
    ]
    if not run_feasible:
        blockers.append("one_or_more_baseline_policies_failed_closed")
    summary = {
        "case": config["case"]["name"],
        "source_package": data.source_package,
        "source_version": data.source_version,
        "planning_model": planning["model"],
        "planning_parameter_status": planning["parameter_status"],
        "evidence_label": evidence_label,
        "evidence_status": validation["evidence_status"],
        "demand_path_source": planning["demand_path_source"],
        "demand_path_mw": [quarter.data_center_demand_mw for quarter in quarters],
        "quarter_operating_hours": [quarter.operating_hours for quarter in quarters],
        "continuous_validation_hours": [
            quarter.continuous_validation_hours for quarter in quarters
        ],
        "policy_order": [policy.value for policy in policies],
        "common_input_signature_id": _COMMON_INPUT_SIGNATURE_ID,
        "common_input_signature_schema": COMMON_INPUT_SIGNATURE_SCHEMA,
        "common_input_signature_sha256": common_input_signature_hash,
        "common_input_signature": common_input_signature,
        "all_policies_attempted": len(policy_runs) == len(policies),
        "all_policies_completed": len(policy_runs) == len(policies)
        and all(run["result"] is not None for run in policy_runs),
        "all_policies_feasible": run_feasible,
        "feasible": run_feasible,
        "run_status": (
            "completed_non_certifying" if run_feasible else "failed_closed"
        ),
        "policy_results": policy_summaries,
        "planning_objectives": objective["planning_objectives"],
        "planning_objective_unit_basis": objective["unit_basis"],
        "posthoc_cost_scope": objective["posthoc_cost_scope"],
        "service_parameter_status": service_envelope.parameter_status,
        "redispatch_fraction_pmax": redispatch_fraction,
        "redispatch_parameter_status": security["response_parameter_status"],
        "branch_indices": list(branch_indices),
        "generator_indices": list(generator_indices),
        "project_branch_indices": sorted(project_branch_indices),
        "project_branch_contingencies_included": True,
        "continuous_capacity_milestones_certified": False,
        "ac_validation_scope": validation["ac_scope"],
        "security_certified": False,
        "certification_blockers": blockers,
        "output_paths": dict(config["output"]),
    }

    _write_csv(
        Path(config["output"]["policy_endpoint_path"]),
        _ENDPOINT_FIELDS,
        endpoint_rows,
    )
    _write_csv(
        Path(config["output"]["quarter_path"]),
        _QUARTER_FIELDS,
        quarter_rows,
    )
    summary = _jsonable(summary)
    summary_path = Path(config["output"]["summary_path"])
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, allow_nan=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def common_input_signature_for_config(config_path: Path) -> dict[str, object]:
    """Validate common M4/M5 inputs and return their canonical signature."""

    return run(config_path, _common_input_signature_only=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rts24_deterministic_baselines.yaml"),
    )
    args = parser.parse_args()
    summary = run(args.config)
    print(
        json.dumps(
            _jsonable(summary),
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
    )
    if not summary["feasible"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
