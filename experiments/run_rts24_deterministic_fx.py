"""Run the fixed-policy deterministic RTS-24 F/X mechanism benchmark."""

from __future__ import annotations

import argparse
import csv
import json
from math import isfinite
from pathlib import Path

import yaml

from src.grid import load_rts24, non_islanding_branch_indices
from src.models import (
    ExistingBranchUpgrade,
    FixedFxPlan,
    FixedPoi,
    FxQuarter,
    FxServiceEnvelope,
    evaluate_deterministic_fx_plan,
)


_PLANNING_STATUS = "synthetic_benchmark_not_site_evidence"
_PLAN_STATUS = "synthetic_fixed_policy_mechanism_test_not_optimized"
_SERVICE_STATUS = "synthetic_mw_only_envelope_not_contract_evidence"
_RESPONSE_MODEL = "mw_only_sustained_states_no_duration_or_energy_limits"
_WINDOW_STATUS = "not_validated_no_chronological_network_trajectory"
_OBJECTIVE_UNIT_BASIS = "synthetic_objective_units_not_calibrated_currency_year"


def _write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _milestone_dict(milestone: object) -> dict[str, object]:
    return {
        "threshold_mw": milestone.threshold_mw,
        "reached": milestone.reached,
        "quarter": milestone.quarter,
        "right_censored": milestone.right_censored,
        "censor_quarter": milestone.censor_quarter,
        "display_label": milestone.display_label,
    }


def run(config_path: Path) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["case"] != {"name": "case24_ieee_rts", "source": "pypower"}:
        raise ValueError("This experiment requires PYPOWER case24_ieee_rts")

    planning = config["planning"]
    if planning["model"] != "deterministic_fixed_fx_policy_mw_only":
        raise ValueError("Unsupported F/X planning model")
    if planning["parameter_status"] != _PLANNING_STATUS:
        raise ValueError("Planning inputs must retain their synthetic status")
    quarters = tuple(
        FxQuarter(
            name=row["name"],
            system_load_multiplier=float(row["system_load_multiplier"]),
            data_center_demand_mw=float(row["data_center_demand_mw"]),
            operating_hours=float(row["operating_hours"]),
            continuous_validation_hours=float(
                row["continuous_validation_hours"]
            ),
            discount_factor=float(row["discount_factor"]),
        )
        for row in planning["quarters"]
    )
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
        raise ValueError("Expansion inputs must retain their synthetic status")
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
    plan_config = config["fixed_fx_plan"]
    if plan_config["parameter_status"] != _PLAN_STATUS:
        raise ValueError("F/X plan must remain explicitly fixed and synthetic")
    plan = FixedFxPlan(
        firm_capacity_mw={
            str(name): float(capacity)
            for name, capacity in plan_config["firm_capacity_mw"].items()
        },
        conditional_capacity_mw={
            str(name): float(capacity)
            for name, capacity in plan_config["conditional_capacity_mw"].items()
        },
        project_start_quarter=plan_config["project_start_quarter"],
        parameter_status=plan_config["parameter_status"],
    )
    service_config = config["service_envelope"]
    if service_config["parameter_status"] != _SERVICE_STATUS:
        raise ValueError("F/X service envelope must retain its synthetic status")
    if service_config["response_model"] != _RESPONSE_MODEL:
        raise ValueError("Unsupported F/X response model")
    if service_config["continuous_window_status"] != _WINDOW_STATUS:
        raise ValueError("Continuous-window assumption must remain explicit")
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
    if (
        security["response_parameter_status"]
        != "synthetic_sensitivity_not_for_certification"
    ):
        raise ValueError("Redispatch status must remain non-certifying")
    fraction = float(security["redispatch_fraction_pmax"])
    if not isfinite(fraction) or not 0.0 <= fraction <= 1.0:
        raise ValueError("Redispatch fraction must be finite and within [0, 1]")
    redispatch = {
        generator.index: fraction * generator.p_max_mw
        for generator in data.generators
    }
    branch_indices = non_islanding_branch_indices(data)
    project_branch_indices = set(project.rate_a_increase_mw) | set(
        project.rate_c_increase_mw
    )
    missing_project_contingencies = project_branch_indices - set(branch_indices)
    if missing_project_contingencies:
        raise ValueError(
            "Every upgraded branch must be in the formal N-1 set: "
            f"{sorted(missing_project_contingencies)}"
        )
    generator_indices = tuple(
        generator.index
        for generator in data.generators
        if generator.in_service and generator.p_max_mw > 0.0
    )

    objective = config["objective"]
    if objective["unit_basis"] != _OBJECTIVE_UNIT_BASIS:
        raise ValueError("Objective unit basis must remain synthetic")
    if (
        objective["contingency_call_treatment"]
        != "minimum_call_feasibility_certificate_not_event_cost"
    ):
        raise ValueError("Unsupported contingency-call treatment")
    if (
        objective["reported_cost"]
        != "direct_convex_qp_numerical_solution_with_l1_linear_feasibility_"
        "projection"
    ):
        raise ValueError("Unsupported reported-cost treatment")
    result = evaluate_deterministic_fx_plan(
        data,
        quarters=quarters,
        poi=poi,
        project=project,
        plan=plan,
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
        primary_objective_tolerance=float(
            objective["primary_objective_tolerance"]
        ),
        solver_name=config["solver"]["name"],
    )

    validation = config["validation"]
    expected_ac_scope = (
        "not_run_missing_expansion_mva_reactive_and_chronological_network_parameters"
    )
    if validation["ac_scope"] != expected_ac_scope:
        raise ValueError("Unsupported AC-validation scope")
    power_tolerance = float(validation["power_tolerance_mw"])
    loading_tolerance = float(validation["loading_tolerance_fraction"])
    if not isfinite(power_tolerance) or power_tolerance < 0.0:
        raise ValueError("Power tolerance must be finite and nonnegative")
    if not isfinite(loading_tolerance) or loading_tolerance < 0.0:
        raise ValueError("Loading tolerance must be finite and nonnegative")

    state_by_name = {state.name: state for state in result.states}
    quarter_rows = []
    state_rows = []
    generator_rows = []
    for quarter in quarters:
        if not result.feasible:
            break
        quarter_state_rows = []
        for layer_name, layer_results, calls, poi_loads in (
            (
                "actual",
                result.actual_state_results,
                result.actual_grid_curtailment_mw,
                result.actual_poi_load_mw,
            ),
            (
                "contract_counterfactual",
                result.certified_state_results,
                result.certified_grid_curtailment_mw,
                result.certified_poi_load_mw,
            ),
        ):
            base = layer_results[quarter.name]["base"]
            for state_name, state_result in layer_results[quarter.name].items():
                state = state_by_name[state_name]
                ratings = result.effective_branch_ratings_mw[quarter.name][
                    state_name
                ]
                active_loadings = {
                    branch.index: abs(state_result.branch_flows_mw[branch.index])
                    / ratings[branch.index]
                    for branch in data.branches
                    if branch.in_service
                    and branch.index not in state.outaged_branch_indices
                }
                max_branch = max(active_loadings, key=active_loadings.get)
                max_loading = active_loadings[max_branch]
                max_outaged_branch_flow = max(
                    (
                        abs(state_result.branch_flows_mw[index])
                        for index in state.outaged_branch_indices
                    ),
                    default=0.0,
                )
                max_outaged_generator_output = max(
                    (
                        abs(state_result.generation_mw[index])
                        for index in state.outaged_generator_indices
                    ),
                    default=0.0,
                )
                generator_bound_violation = 0.0
                response_violation = 0.0
                for generator in data.generators:
                    unavailable = (
                        not generator.in_service
                        or generator.index in state.outaged_generator_indices
                    )
                    lower = 0.0 if unavailable else generator.p_min_mw
                    upper = 0.0 if unavailable else generator.p_max_mw
                    generation = state_result.generation_mw[generator.index]
                    generator_bound_error = max(
                        lower - generation,
                        generation - upper,
                        0.0,
                    )
                    generator_bound_violation = max(
                        generator_bound_violation,
                        generator_bound_error,
                    )
                    base_generation = base.generation_mw[generator.index]
                    change = generation - base_generation
                    response_applicable = (
                        state.response_mode != "base" and not unavailable
                    )
                    if not response_applicable:
                        generator_response_violation = 0.0
                    elif state.response_mode == "fixed":
                        generator_response_violation = abs(change)
                    else:
                        generator_response_violation = max(
                            change - redispatch[generator.index],
                            -change - redispatch[generator.index],
                            0.0,
                        )
                    response_violation = max(
                        response_violation,
                        generator_response_violation,
                    )
                    generator_rows.append(
                        {
                            "planning_parameter_status": planning[
                                "parameter_status"
                            ],
                            "fixed_plan_parameter_status": plan.parameter_status,
                            "service_parameter_status": (
                                service_envelope.parameter_status
                            ),
                            "quarter": quarter.name,
                            "layer": layer_name,
                            "state": state.name,
                            "response_mode": state.response_mode,
                            "generator_index": generator.index,
                            "bus": generator.bus,
                            "outaged": generator.index
                            in state.outaged_generator_indices,
                            "in_service": generator.in_service,
                            "p_min_mw": lower,
                            "p_max_mw": upper,
                            "layer_base_generation_mw": base_generation,
                            "state_generation_mw": generation,
                            "change_from_layer_base_mw": change,
                            "response_applicable": response_applicable,
                            "redispatch_up_limit_mw": redispatch[generator.index],
                            "redispatch_down_limit_mw": redispatch[
                                generator.index
                            ],
                            "generator_bound_violation_mw": (
                                generator_bound_error
                            ),
                            "corrective_response_violation_mw": (
                                generator_response_violation
                            ),
                            "termination_condition": (
                                state_result.termination_condition
                            ),
                            "security_certified": False,
                        }
                    )
                call = calls[quarter.name][state_name]
                poi_load = poi_loads[quarter.name][state_name]
                if layer_name == "actual":
                    firm_breach = result.firm_breach_mw[quarter.name][state_name]
                    conditional_breach = result.conditional_breach_mw[
                        quarter.name
                    ][state_name]
                    expected_load = (
                        result.connected_demand_mw[quarter.name]
                        - call
                        - firm_breach
                        - conditional_breach
                    )
                    call_limit = result.active_conditional_demand_mw[quarter.name]
                    service_floor = result.firm_demand_mw[quarter.name]
                    poi_load_basis = "actual_connected_demand"
                else:
                    firm_breach = 0.0
                    conditional_breach = 0.0
                    expected_load = result.total_capacity_mw[quarter.name] - call
                    call_limit = result.conditional_capacity_mw[quarter.name]
                    service_floor = result.firm_capacity_mw[quarter.name]
                    poi_load_basis = "full_contract_capacity_counterfactual"
                pre_response_call = (
                    abs(call) if state.response_mode in {"base", "fixed"} else 0.0
                )
                call_limit_violation = max(call - call_limit, 0.0)
                service_floor_violation = max(service_floor - poi_load, 0.0)
                service_balance_residual = abs(poi_load - expected_load)
                constraints_satisfied = (
                    state_result.max_balance_residual_mw <= power_tolerance
                    and max_loading <= 1.0 + loading_tolerance
                    and max_outaged_branch_flow <= power_tolerance
                    and max_outaged_generator_output <= power_tolerance
                    and generator_bound_violation <= power_tolerance
                    and response_violation <= power_tolerance
                    and pre_response_call <= power_tolerance
                    and call_limit_violation <= power_tolerance
                    and service_floor_violation <= power_tolerance
                    and service_balance_residual <= power_tolerance
                    and abs(firm_breach) <= power_tolerance
                    and abs(conditional_breach) <= power_tolerance
                )
                row = {
                    "planning_parameter_status": planning["parameter_status"],
                    "fixed_plan_parameter_status": plan.parameter_status,
                    "service_parameter_status": service_envelope.parameter_status,
                    "quarter": quarter.name,
                    "layer": layer_name,
                    "poi_load_basis": poi_load_basis,
                    "state": state.name,
                    "kind": state.kind,
                    "element_index": ""
                    if state.element_index is None
                    else state.element_index,
                    "response_mode": state.response_mode,
                    "branch_rating": state.branch_rating,
                    "firm_capacity_mw": result.firm_capacity_mw[quarter.name],
                    "conditional_capacity_mw": (
                        result.conditional_capacity_mw[quarter.name]
                    ),
                    "total_capacity_mw": result.total_capacity_mw[quarter.name],
                    "data_center_demand_mw": quarter.data_center_demand_mw,
                    "connected_demand_mw": result.connected_demand_mw[
                        quarter.name
                    ],
                    "firm_demand_mw": result.firm_demand_mw[quarter.name],
                    "active_conditional_demand_mw": (
                        result.active_conditional_demand_mw[quarter.name]
                    ),
                    "access_shortfall_mw": result.access_shortfall_mw[
                        quarter.name
                    ],
                    "grid_curtailment_mw": call,
                    "firm_breach_mw": firm_breach,
                    "conditional_breach_mw": conditional_breach,
                    "breach_diagnostics_enabled": (
                        result.breach_diagnostics_enabled
                    ),
                    "poi_load_mw": poi_load,
                    "service_floor_mw": service_floor,
                    "call_limit_mw": call_limit,
                    "service_balance_residual_mw": service_balance_residual,
                    "service_floor_violation_mw": service_floor_violation,
                    "call_limit_violation_mw": call_limit_violation,
                    "pre_response_call_violation_mw": pre_response_call,
                    "max_balance_residual_mw": (
                        state_result.max_balance_residual_mw
                    ),
                    "max_loading_fraction": max_loading,
                    "max_loaded_branch_index": max_branch,
                    "max_outaged_branch_flow_mw": max_outaged_branch_flow,
                    "max_outaged_generator_output_mw": (
                        max_outaged_generator_output
                    ),
                    "max_generator_bound_violation_mw": (
                        generator_bound_violation
                    ),
                    "max_corrective_response_violation_mw": response_violation,
                    "constraints_satisfied": constraints_satisfied,
                    "security_certified": False,
                }
                state_rows.append(row)
                quarter_state_rows.append(row)
        quarter_rows.append(
            {
                "planning_parameter_status": planning["parameter_status"],
                "fixed_plan_parameter_status": plan.parameter_status,
                "service_parameter_status": service_envelope.parameter_status,
                "quarter": quarter.name,
                "system_load_multiplier": quarter.system_load_multiplier,
                "native_system_demand_mw": (
                    data.total_demand_mw * quarter.system_load_multiplier
                ),
                "data_center_demand_mw": quarter.data_center_demand_mw,
                "firm_capacity_mw": result.firm_capacity_mw[quarter.name],
                "conditional_capacity_mw": (
                    result.conditional_capacity_mw[quarter.name]
                ),
                "total_capacity_mw": result.total_capacity_mw[quarter.name],
                "connected_demand_mw": result.connected_demand_mw[quarter.name],
                "firm_demand_mw": result.firm_demand_mw[quarter.name],
                "active_conditional_demand_mw": (
                    result.active_conditional_demand_mw[quarter.name]
                ),
                "access_shortfall_mw": result.access_shortfall_mw[quarter.name],
                "project_commissioned": result.commissioned_by_quarter[
                    quarter.name
                ],
                "continuous_validation_hours": (
                    quarter.continuous_validation_hours
                ),
                "states_checked_per_layer": len(result.states),
                "layers_checked": 2,
                "max_actual_grid_curtailment_mw": max(
                    result.actual_grid_curtailment_mw[quarter.name].values()
                ),
                "max_contract_counterfactual_grid_curtailment_mw": max(
                    result.certified_grid_curtailment_mw[quarter.name].values()
                ),
                "max_state_balance_residual_mw": max(
                    row["max_balance_residual_mw"] for row in quarter_state_rows
                ),
                "max_state_loading_fraction": max(
                    row["max_loading_fraction"] for row in quarter_state_rows
                ),
                "all_modeled_layers_constraints_satisfied": all(
                    row["constraints_satisfied"] for row in quarter_state_rows
                ),
                "security_certified": False,
            }
        )

    quarter_fields = tuple(quarter_rows[0]) if quarter_rows else (
        "planning_parameter_status",
        "quarter",
    )
    state_fields = tuple(state_rows[0]) if state_rows else (
        "planning_parameter_status",
        "quarter",
        "layer",
        "state",
    )
    _write_csv(Path(config["output"]["quarterly_path"]), quarter_fields, quarter_rows)
    _write_csv(Path(config["output"]["state_path"]), state_fields, state_rows)
    generator_fields = tuple(generator_rows[0]) if generator_rows else (
        "planning_parameter_status",
        "quarter",
        "layer",
        "state",
        "generator_index",
    )
    _write_csv(
        Path(config["output"]["generator_path"]),
        generator_fields,
        generator_rows,
    )

    all_constraints_satisfied = bool(state_rows) and all(
        row["constraints_satisfied"] for row in state_rows
    )
    milestones = result.milestones
    blockers = [
        "fixed_fx_policy_is_synthetic_and_not_optimized",
        "static_network_gate_is_mw_only_temporal_envelope_evaluated_separately",
        "static_m3_has_zero_chronologically_validated_hours",
        "synthetic_redispatch_without_response_time_evidence",
        "branch_10_unplanned_islanding_excluded",
        "expansion_and_fx_ac_validation_not_run_missing_engineering_parameters",
        "fixed_online_generators_without_chronological_commitment",
        "deterministic_load_only_quarters_without_renewables_or_uncertainty",
        "synthetic_objective_units_not_calibrated_to_currency_year",
        "generator_outages_have_no_separate_immediate_frequency_state",
    ]
    summary = {
        "case": config["case"]["name"],
        "source_package": data.source_package,
        "source_version": data.source_version,
        "planning_model": planning["model"],
        "planning_parameter_status": planning["parameter_status"],
        "fixed_plan_parameter_status": plan.parameter_status,
        "fixed_policy_optimized": False,
        "service_parameter_status": service_envelope.parameter_status,
        "response_model": result.response_model,
        "continuous_window_status": service_config["continuous_window_status"],
        "chronological_sensitivity_evaluated_separately": True,
        "chronological_sensitivity_summary_path": config[
            "chronological_sensitivity"
        ]["summary_output_path"],
        "capacity_interpretation": result.capacity_interpretation,
        "contract_counterfactual_dispatch_interpretation": (
            result.certified_dispatch_interpretation
        ),
        "cost_interpretation": result.cost_interpretation,
        "breach_diagnostics_enabled": result.breach_diagnostics_enabled,
        "feasible": result.feasible,
        "termination_condition": result.termination_condition,
        "solver_status": result.solver_status,
        "project_name": project.name,
        "project_start_quarter": result.start_quarter,
        "project_commissioned_by_quarter": result.commissioned_by_quarter,
        "project_branch_indices": sorted(project_branch_indices),
        "project_branch_contingencies_included": True,
        "firm_capacity_mw": result.firm_capacity_mw,
        "conditional_capacity_mw": result.conditional_capacity_mw,
        "total_capacity_mw": result.total_capacity_mw,
        "connected_demand_mw": result.connected_demand_mw,
        "firm_demand_mw": result.firm_demand_mw,
        "active_conditional_demand_mw": result.active_conditional_demand_mw,
        "access_shortfall_mw": result.access_shortfall_mw,
        "unused_capacity_mw_year": result.unused_capacity_mw_year,
        "objective_unit_basis": objective["unit_basis"],
        "objective_at_repaired_numerical_qp_dispatch_synthetic_units": (
            result.objective
        ),
        "primary_repaired_numerical_qp_objective_synthetic_units": (
            result.primary_optimization_objective
        ),
        "canonical_dispatch_primary_objective_synthetic_units": (
            result.canonical_dispatch_primary_objective
        ),
        "canonical_dispatch_primary_cost_deviation_synthetic_units": (
            None
            if result.primary_optimization_objective is None
            else result.canonical_dispatch_primary_objective
            - result.primary_optimization_objective
        ),
        "investment_cost_synthetic_units": result.investment_cost,
        "operating_cost_exact_recalculation_synthetic_units": (
            result.operating_cost
        ),
        "access_shortfall_cost_synthetic_units": result.access_shortfall_cost,
        "primary_qp_solver": result.primary_qp_solver,
        "primary_qp_status": result.primary_qp_status,
        "primary_qp_iterations": result.primary_qp_iterations,
        "primary_qp_primal_residual": result.primary_qp_primal_residual,
        "primary_qp_dual_residual": result.primary_qp_dual_residual,
        "primary_qp_max_constraint_violation": (
            result.primary_qp_max_constraint_violation
        ),
        "primary_qp_max_bound_projection": (
            result.primary_qp_max_bound_projection
        ),
        "primary_qp_solve_seconds": result.primary_qp_solve_seconds,
        "primary_linear_repair_objective_deviation_synthetic_units": (
            result.primary_linear_repair_objective_deviation
        ),
        "primary_linear_repair_objective_deviation_tolerance_synthetic_units": (
            result.primary_linear_repair_objective_deviation_tolerance
        ),
        "primary_linear_repair_total_generation_movement_mw": (
            result.primary_linear_repair_total_generation_movement_mw
        ),
        "primary_linear_repair_max_generation_movement_mw": (
            result.primary_linear_repair_max_generation_movement_mw
        ),
        "primary_linear_repair_generation_movement_tolerance_mw": (
            result.primary_linear_repair_generation_movement_tolerance_mw
        ),
        "primary_linear_repair_acceptance_interpretation": (
            result.primary_linear_repair_acceptance_interpretation
        ),
        "minimum_call_certificate_mw_sum": (
            result.minimum_call_certificate_mw_sum
        ),
        "contingency_call_treatment": objective["contingency_call_treatment"],
        "minimum_call_certificate_interpretation": (
            "global_sum_relative_to_layer_specific_reference_dispatches_across_"
            "mutually_exclusive_states_and_two_layers_for_tie_break_only"
        ),
        "milestone_metric_scope": (
            None if milestones is None else milestones.metric_scope
        ),
        "T_module": (
            None if milestones is None else _milestone_dict(milestones.t_module)
        ),
        "T20": None if milestones is None else _milestone_dict(milestones.t20),
        "T50": None if milestones is None else _milestone_dict(milestones.t50),
        "T100": None if milestones is None else _milestone_dict(milestones.t100),
        "modeled_states_per_layer_quarter": len(result.states),
        "modeled_state_layer_rows": len(state_rows),
        "generator_state_layer_rows": len(generator_rows),
        "redispatch_fraction_pmax": fraction,
        "redispatch_parameter_status": security["response_parameter_status"],
        "excluded_islanding_branches": list(result.excluded_branch_indices),
        "all_modeled_layers_constraints_satisfied": all_constraints_satisfied,
        "native_load_shedding_allowed": False,
        "firm_breach_allowed": False,
        "conditional_breach_after_contract_call_allowed": False,
        "power_tolerance_mw": power_tolerance,
        "loading_tolerance_fraction": loading_tolerance,
        "ac_validation_scope": validation["ac_scope"],
        "security_certified": False,
        "certification_blockers": blockers,
    }
    summary_path = Path(config["output"]["summary_path"])
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rts24_deterministic_fx.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
