"""Run the fixed-POI deterministic quarterly expansion benchmark."""

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
    FixedPoi,
    PlanningQuarter,
    solve_deterministic_expansion,
)


def _write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run(config_path: Path) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["case"] != {"name": "case24_ieee_rts", "source": "pypower"}:
        raise ValueError("This experiment requires PYPOWER case24_ieee_rts")

    planning = config["planning"]
    expected_parameter_status = "synthetic_benchmark_not_site_evidence"
    if planning["model"] != "deterministic_quarterly_fixed_poi_firm_only":
        raise ValueError("Unsupported deterministic planning model")
    if planning["parameter_status"] != expected_parameter_status:
        raise ValueError("Planning inputs must retain their synthetic status")
    quarters = tuple(
        PlanningQuarter(
            name=row["name"],
            system_load_multiplier=float(row["system_load_multiplier"]),
            data_center_demand_mw=float(row["data_center_demand_mw"]),
            operating_hours=float(row["operating_hours"]),
            discount_factor=float(row["discount_factor"]),
        )
        for row in planning["quarters"]
    )
    poi_config = config["fixed_poi"]
    if poi_config["parameter_status"] != expected_parameter_status:
        raise ValueError("POI inputs must retain their synthetic status")
    poi = FixedPoi(
        bus=int(poi_config["bus"]),
        initial_capacity_mw=float(poi_config["initial_capacity_mw"]),
        application_capacity_mw=float(poi_config["application_capacity_mw"]),
    )
    project_config = config["existing_branch_upgrade"]
    if project_config["parameter_status"] != expected_parameter_status:
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

    data = load_rts24()
    security = config["security"]
    if security["branch_set"] != "all_non_islanding":
        raise ValueError("Unsupported branch contingency set")
    if security["generator_set"] != "all_positive_capacity":
        raise ValueError("Unsupported generator contingency set")
    if security["excluded_islanding_policy"] != "report_as_failure":
        raise ValueError("Unsupported islanding-contingency policy")
    expected_response_status = "synthetic_sensitivity_not_for_certification"
    if security["response_parameter_status"] != expected_response_status:
        raise ValueError("Redispatch inputs must retain their synthetic status")
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
            "Every upgraded branch must be included in the formal N-1 set: "
            f"{sorted(missing_project_contingencies)}"
        )
    generator_indices = tuple(
        generator.index
        for generator in data.generators
        if generator.in_service and generator.p_max_mw > 0.0
    )
    objective = config["objective"]
    unit_basis = "synthetic_objective_units_not_calibrated_currency_year"
    if objective["unit_basis"] != unit_basis:
        raise ValueError("Objective unit basis must retain its synthetic status")
    if (
        objective["reported_cost"]
        != "original_quadratic_evaluated_at_repaired_numerical_solution"
    ):
        raise ValueError("Unsupported reported-cost treatment")
    if (
        objective["investment_cost_timing"]
        != "input_cost_discounted_at_start_quarter"
    ):
        raise ValueError("Unsupported investment-cost timing")
    access_shortfall_cost_per_mwh = float(
        objective["access_shortfall_cost_per_mwh"]
    )
    solver = config["solver"]
    if solver["qp_name"] != "osqp":
        raise ValueError("The fixed-start candidate QPs require OSQP")
    result = solve_deterministic_expansion(
        data,
        quarters=quarters,
        poi=poi,
        project=project,
        redispatch_up_mw=redispatch,
        redispatch_down_mw=redispatch,
        branch_indices=branch_indices,
        generator_indices=generator_indices,
        immediate_rating=security["immediate_branch_rating"],
        sustained_rating=security["sustained_rating"],
        access_shortfall_cost_per_mwh=access_shortfall_cost_per_mwh,
        solver_name=solver["linear_repair_name"],
    )

    validation = config["validation"]
    expected_ac_scope = (
        "not_run_missing_expansion_mva_and_reactive_engineering_parameters"
    )
    if validation["ac_scope"] != expected_ac_scope:
        raise ValueError("Unsupported AC-validation scope")
    power_tolerance_mw = float(validation["power_tolerance_mw"])
    loading_tolerance_fraction = float(validation["loading_tolerance_fraction"])
    if not isfinite(power_tolerance_mw) or power_tolerance_mw < 0.0:
        raise ValueError("Power tolerance must be finite and nonnegative")
    if (
        not isfinite(loading_tolerance_fraction)
        or loading_tolerance_fraction < 0.0
    ):
        raise ValueError("Loading tolerance must be finite and nonnegative")
    quarter_rows = []
    state_rows = []
    state_by_name = {state.name: state for state in result.states}
    for quarter in quarters:
        if not result.feasible:
            break
        quarter_states = result.state_results[quarter.name]
        base = quarter_states["base"]
        quarter_state_rows = []
        for state_name, state_result in quarter_states.items():
            state = state_by_name[state_name]
            ratings = result.effective_branch_ratings_mw[quarter.name][state_name]
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
            lower_bound_violations = []
            upper_bound_violations = []
            for generator in data.generators:
                unavailable = (
                    not generator.in_service
                    or generator.index in state.outaged_generator_indices
                )
                lower = 0.0 if unavailable else generator.p_min_mw
                upper = 0.0 if unavailable else generator.p_max_mw
                generation = state_result.generation_mw[generator.index]
                lower_bound_violations.append(max(lower - generation, 0.0))
                upper_bound_violations.append(max(generation - upper, 0.0))
            max_generator_lower_bound_violation = max(lower_bound_violations)
            max_generator_upper_bound_violation = max(upper_bound_violations)
            max_generator_bound_violation = max(
                max_generator_lower_bound_violation,
                max_generator_upper_bound_violation,
            )
            if state.response_mode == "base":
                max_corrective_response_violation = 0.0
            elif state.response_mode == "fixed":
                max_corrective_response_violation = max(
                    abs(
                        state_result.generation_mw[generator.index]
                        - base.generation_mw[generator.index]
                    )
                    for generator in data.generators
                    if generator.index not in state.outaged_generator_indices
                )
            elif state.response_mode == "bounded":
                response_violations = []
                for generator in data.generators:
                    if generator.index in state.outaged_generator_indices:
                        continue
                    change = (
                        state_result.generation_mw[generator.index]
                        - base.generation_mw[generator.index]
                    )
                    response_violations.extend(
                        (
                            max(change - redispatch[generator.index], 0.0),
                            max(-change - redispatch[generator.index], 0.0),
                        )
                    )
                max_corrective_response_violation = max(
                    response_violations,
                    default=0.0,
                )
            else:
                raise ValueError(f"Unknown response mode '{state.response_mode}'")
            dc_constraints_satisfied = (
                state_result.max_balance_residual_mw <= power_tolerance_mw
                and max_loading <= 1.0 + loading_tolerance_fraction
                and max_outaged_branch_flow <= power_tolerance_mw
                and max_outaged_generator_output <= power_tolerance_mw
                and max_generator_bound_violation <= power_tolerance_mw
                and max_corrective_response_violation <= power_tolerance_mw
            )
            state_row = {
                "planning_parameter_status": planning["parameter_status"],
                "connected_capacity_interpretation": (
                    result.capacity_interpretation
                ),
                "quarter": quarter.name,
                "state": state.name,
                "kind": state.kind,
                "element_index": ""
                if state.element_index is None
                else state.element_index,
                "response_mode": state.response_mode,
                "branch_rating": state.branch_rating,
                "project_commissioned": result.commissioned_by_quarter[
                    quarter.name
                ],
                "connected_capacity_mw": result.connected_capacity_mw[
                    quarter.name
                ],
                "state_generation_cost_original_quadratic_evaluation_"
                "synthetic_units_per_hour": (
                    state_result.objective
                ),
                "max_balance_residual_mw": state_result.max_balance_residual_mw,
                "max_loading_fraction": max_loading,
                "max_loaded_branch_index": max_branch,
                "outaged_branch_indices": ";".join(
                    str(index) for index in sorted(state.outaged_branch_indices)
                ),
                "max_outaged_branch_flow_mw": max_outaged_branch_flow,
                "outaged_generator_indices": ";".join(
                    str(index) for index in sorted(state.outaged_generator_indices)
                ),
                "max_outaged_generator_output_mw": max_outaged_generator_output,
                "max_generator_lower_bound_violation_mw": (
                    max_generator_lower_bound_violation
                ),
                "max_generator_upper_bound_violation_mw": (
                    max_generator_upper_bound_violation
                ),
                "max_generator_bound_violation_mw": max_generator_bound_violation,
                "max_corrective_response_violation_mw": (
                    max_corrective_response_violation
                ),
                "power_tolerance_mw": power_tolerance_mw,
                "loading_tolerance_fraction": loading_tolerance_fraction,
                "dc_constraints_satisfied": dc_constraints_satisfied,
                "security_certified": False,
            }
            state_rows.append(state_row)
            quarter_state_rows.append(state_row)
        max_state_residual = max(
            row["max_balance_residual_mw"] for row in quarter_state_rows
        )
        max_state_loading = max(
            row["max_loading_fraction"] for row in quarter_state_rows
        )
        quarter_rows.append(
            {
                "planning_parameter_status": planning["parameter_status"],
                "connected_capacity_interpretation": (
                    result.capacity_interpretation
                ),
                "quarter": quarter.name,
                "system_load_multiplier": quarter.system_load_multiplier,
                "native_system_demand_mw": (
                    data.total_demand_mw * quarter.system_load_multiplier
                ),
                "data_center_demand_mw": quarter.data_center_demand_mw,
                "connected_capacity_mw": result.connected_capacity_mw[
                    quarter.name
                ],
                "access_shortfall_mw": result.access_shortfall_mw[quarter.name],
                "project_started": result.project_started,
                "start_quarter": result.start_quarter or "",
                "project_commissioned": result.commissioned_by_quarter[
                    quarter.name
                ],
                "base_generation_mw": sum(base.generation_mw.values()),
                "base_generation_cost_original_quadratic_evaluation_"
                "synthetic_units_per_hour": base.objective,
                "states_checked": len(quarter_states),
                "max_state_balance_residual_mw": max_state_residual,
                "max_state_loading_fraction": max_state_loading,
                "max_state_outaged_branch_flow_mw": max(
                    row["max_outaged_branch_flow_mw"]
                    for row in quarter_state_rows
                ),
                "max_state_outaged_generator_output_mw": max(
                    row["max_outaged_generator_output_mw"]
                    for row in quarter_state_rows
                ),
                "max_state_generator_bound_violation_mw": max(
                    row["max_generator_bound_violation_mw"]
                    for row in quarter_state_rows
                ),
                "max_state_corrective_response_violation_mw": max(
                    row["max_corrective_response_violation_mw"]
                    for row in quarter_state_rows
                ),
                "power_tolerance_mw": power_tolerance_mw,
                "loading_tolerance_fraction": loading_tolerance_fraction,
                "all_modeled_states_dc_secure": all(
                    row["dc_constraints_satisfied"] for row in quarter_state_rows
                ),
                "security_certified": False,
            }
        )

    quarter_fields = (
        "planning_parameter_status",
        "connected_capacity_interpretation",
        "quarter",
        "system_load_multiplier",
        "native_system_demand_mw",
        "data_center_demand_mw",
        "connected_capacity_mw",
        "access_shortfall_mw",
        "project_started",
        "start_quarter",
        "project_commissioned",
        "base_generation_mw",
        "base_generation_cost_original_quadratic_evaluation_"
        "synthetic_units_per_hour",
        "states_checked",
        "max_state_balance_residual_mw",
        "max_state_loading_fraction",
        "max_state_outaged_branch_flow_mw",
        "max_state_outaged_generator_output_mw",
        "max_state_generator_bound_violation_mw",
        "max_state_corrective_response_violation_mw",
        "power_tolerance_mw",
        "loading_tolerance_fraction",
        "all_modeled_states_dc_secure",
        "security_certified",
    )
    state_fields = (
        "planning_parameter_status",
        "connected_capacity_interpretation",
        "quarter",
        "state",
        "kind",
        "element_index",
        "response_mode",
        "branch_rating",
        "project_commissioned",
        "connected_capacity_mw",
        "state_generation_cost_original_quadratic_evaluation_"
        "synthetic_units_per_hour",
        "max_balance_residual_mw",
        "max_loading_fraction",
        "max_loaded_branch_index",
        "outaged_branch_indices",
        "max_outaged_branch_flow_mw",
        "outaged_generator_indices",
        "max_outaged_generator_output_mw",
        "max_generator_lower_bound_violation_mw",
        "max_generator_upper_bound_violation_mw",
        "max_generator_bound_violation_mw",
        "max_corrective_response_violation_mw",
        "power_tolerance_mw",
        "loading_tolerance_fraction",
        "dc_constraints_satisfied",
        "security_certified",
    )
    candidate_rows = []
    candidate_field_order = []
    for diagnostic in result.candidate_diagnostics:
        row = dict(diagnostic)
        for field, field_value in tuple(row.items()):
            if isinstance(field_value, (dict, list, tuple)):
                row[field] = json.dumps(
                    field_value,
                    separators=(",", ":"),
                    sort_keys=True,
                )
        candidate_rows.append(row)
        for field in row:
            if field not in candidate_field_order:
                candidate_field_order.append(field)
    candidate_fields = tuple(candidate_field_order)
    _write_csv(Path(config["output"]["quarterly_path"]), quarter_fields, quarter_rows)
    _write_csv(Path(config["output"]["state_path"]), state_fields, state_rows)
    _write_csv(
        Path(config["output"]["candidate_path"]),
        candidate_fields,
        candidate_rows,
    )

    blockers = [
        "synthetic_poi_lead_time_cost_and_rating_increases_not_site_evidence",
        "synthetic_redispatch_without_response_time_evidence",
        "branch_10_unplanned_islanding_excluded",
        "expansion_ac_validation_not_run_missing_mva_and_reactive_parameters",
        "fixed_online_generators_without_chronological_commitment",
        "deterministic_load_only_quarters_without_renewables_or_uncertainty",
        "synthetic_objective_units_not_calibrated_to_currency_year",
        "numerical_qp_with_linear_repair_without_explicit_optimality_gap_"
        "certificate",
    ]
    expected_candidate_count = len(quarters) + 1
    actual_candidate_count = len(result.candidate_diagnostics)
    expected_candidate_starts = [None, *(quarter.name for quarter in quarters)]
    actual_candidate_starts = [
        diagnostic["start_quarter"]
        for diagnostic in result.candidate_diagnostics
    ]
    candidate_order_canonical = actual_candidate_starts == expected_candidate_starts
    resolved_candidate_count = sum(
        bool(diagnostic["resolved"])
        for diagnostic in result.candidate_diagnostics
    )
    feasible_candidate_count = sum(
        bool(diagnostic["feasible"])
        for diagnostic in result.candidate_diagnostics
    )
    selected_candidate_count = sum(
        bool(diagnostic["selected"])
        for diagnostic in result.candidate_diagnostics
    )
    enumeration_complete = (
        actual_candidate_count == expected_candidate_count
        and resolved_candidate_count == expected_candidate_count
        and candidate_order_canonical
    )
    if not enumeration_complete and selected_candidate_count:
        raise RuntimeError("An incomplete fixed-start enumeration cannot select a candidate")
    if result.feasible and (
        not enumeration_complete or selected_candidate_count != 1
    ):
        raise RuntimeError(
            "A feasible M2 result requires one selected candidate from a complete "
            "fixed-start enumeration"
        )
    if not result.feasible and selected_candidate_count:
        raise RuntimeError("An infeasible M2 result cannot select a candidate")
    if not enumeration_complete:
        blockers.append("fixed_start_enumeration_incomplete")
        cost_interpretation = (
            "no_selected_cost_fixed_start_enumeration_incomplete"
        )
    elif not result.feasible:
        blockers.append("no_feasible_fixed_start_candidate")
        cost_interpretation = (
            "complete_fixed_start_enumeration_found_no_feasible_candidate"
        )
    else:
        cost_interpretation = (
            "original_quadratic_evaluated_at_best_repaired_numerical_solution_"
            "from_complete_fixed_start_enumeration_without_explicit_"
            "optimality_gap_certificate"
        )
    feasible_diagnostics = [
        diagnostic
        for diagnostic in result.candidate_diagnostics
        if diagnostic["feasible"]
    ]
    selected_diagnostics = [
        diagnostic
        for diagnostic in result.candidate_diagnostics
        if diagnostic["selected"]
    ]
    repair_envelopes = [
        float(diagnostic["repair_objective_deviation_threshold"])
        for diagnostic in feasible_diagnostics
        if diagnostic.get("repair_objective_deviation_threshold") is not None
    ]
    maximum_repair_envelope = max(repair_envelopes, default=None)
    if len(selected_diagnostics) == 1:
        selected_diagnostic = selected_diagnostics[0]
        selected_objective = float(selected_diagnostic["objective"])
        unselected_feasible = [
            diagnostic
            for diagnostic in feasible_diagnostics
            if not diagnostic["selected"]
        ]
        objective_separation = min(
            (
                float(diagnostic["objective"]) - selected_objective
                for diagnostic in unselected_feasible
            ),
            default=None,
        )
        selected_envelope = float(
            selected_diagnostic.get("repair_objective_deviation_threshold") or 0.0
        )
        selection_exceeds_pairwise_envelopes = all(
            float(diagnostic["objective"]) - selected_objective
            > selected_envelope
            + float(diagnostic.get("repair_objective_deviation_threshold") or 0.0)
            for diagnostic in unselected_feasible
        )
    else:
        objective_separation = None
        selection_exceeds_pairwise_envelopes = None
    all_modeled_states_dc_secure = bool(state_rows) and all(
        row["dc_constraints_satisfied"] for row in state_rows
    )
    max_balance_residual_mw = max(
        (row["max_balance_residual_mw"] for row in state_rows),
        default=None,
    )
    max_loading_fraction = max(
        (row["max_loading_fraction"] for row in state_rows),
        default=None,
    )
    max_outaged_branch_flow_mw = max(
        (row["max_outaged_branch_flow_mw"] for row in state_rows),
        default=None,
    )
    max_outaged_generator_output_mw = max(
        (row["max_outaged_generator_output_mw"] for row in state_rows),
        default=None,
    )
    max_generator_bound_violation_mw = max(
        (row["max_generator_bound_violation_mw"] for row in state_rows),
        default=None,
    )
    max_corrective_response_violation_mw = max(
        (row["max_corrective_response_violation_mw"] for row in state_rows),
        default=None,
    )
    summary = {
        "case": config["case"]["name"],
        "source_package": data.source_package,
        "source_version": data.source_version,
        "planning_model": planning["model"],
        "planning_parameter_status": planning["parameter_status"],
        "connected_capacity_interpretation": result.capacity_interpretation,
        "project_name": project.name,
        "project_parameter_status": project.parameter_status,
        "project_branch_indices": sorted(project_branch_indices),
        "project_branch_contingencies_included": True,
        "project_started": result.project_started,
        "start_quarter": result.start_quarter,
        "lead_time_quarters": project.lead_time_quarters,
        "project_commissioned_by_quarter": result.commissioned_by_quarter,
        "feasible": result.feasible,
        "termination_condition": result.termination_condition,
        "solver_status": result.solver_status,
        "solver_message": result.solver_message,
        "qp_solver": solver["qp_name"],
        "linear_repair_solver": solver["linear_repair_name"],
        "enumeration_method": result.enumeration_method,
        "expected_candidate_count": expected_candidate_count,
        "actual_candidate_count": actual_candidate_count,
        "candidate_order_canonical": candidate_order_canonical,
        "enumeration_complete": enumeration_complete,
        "resolved_candidate_count": resolved_candidate_count,
        "feasible_candidate_count": feasible_candidate_count,
        "selected_candidate_count": selected_candidate_count,
        "selected_objective_separation_to_next_feasible_candidate": (
            objective_separation
        ),
        "maximum_candidate_numerical_repair_acceptance_envelope": (
            maximum_repair_envelope
        ),
        "selected_candidate_separation_exceeds_pairwise_repair_envelopes": (
            selection_exceeds_pairwise_envelopes
        ),
        "candidate_diagnostics": result.candidate_diagnostics,
        "objective_unit_basis": unit_basis,
        "reported_cost_treatment": objective["reported_cost"],
        "cost_interpretation": cost_interpretation,
        "investment_cost_timing": objective["investment_cost_timing"],
        "access_shortfall_cost_synthetic_units_per_mwh": (
            access_shortfall_cost_per_mwh
        ),
        "objective_original_quadratic_evaluation_at_repaired_numerical_"
        "solution_synthetic_units": result.objective,
        "selected_candidate_repaired_objective_synthetic_units": (
            result.optimization_objective
        ),
        "investment_cost_synthetic_units": result.investment_cost,
        "operating_cost_original_quadratic_evaluation_synthetic_units": (
            result.operating_cost
        ),
        "access_shortfall_cost_synthetic_units": result.access_shortfall_cost,
        "connected_capacity_mw": result.connected_capacity_mw,
        "access_shortfall_mw": result.access_shortfall_mw,
        "modeled_states_per_quarter": len(result.states),
        "modeled_state_quarters": len(state_rows),
        "excluded_islanding_branches": list(result.excluded_branch_indices),
        "excluded_islanding_policy": security["excluded_islanding_policy"],
        "redispatch_fraction_pmax": fraction,
        "redispatch_parameter_status": security["response_parameter_status"],
        "native_load_shedding_allowed": False,
        "data_center_shedding_after_connection_allowed": False,
        "ac_validation_scope": validation["ac_scope"],
        "power_tolerance_mw": power_tolerance_mw,
        "loading_tolerance_fraction": loading_tolerance_fraction,
        "max_balance_residual_mw": max_balance_residual_mw,
        "max_loading_fraction": max_loading_fraction,
        "max_outaged_branch_flow_mw": max_outaged_branch_flow_mw,
        "max_outaged_generator_output_mw": max_outaged_generator_output_mw,
        "max_generator_bound_violation_mw": max_generator_bound_violation_mw,
        "max_corrective_response_violation_mw": (
            max_corrective_response_violation_mw
        ),
        "all_outaged_branch_flows_zero": bool(state_rows)
        and max_outaged_branch_flow_mw <= power_tolerance_mw,
        "all_outaged_generator_outputs_zero": bool(state_rows)
        and max_outaged_generator_output_mw <= power_tolerance_mw,
        "all_generator_bounds_satisfied": bool(state_rows)
        and max_generator_bound_violation_mw <= power_tolerance_mw,
        "all_corrective_response_bounds_satisfied": bool(state_rows)
        and max_corrective_response_violation_mw <= power_tolerance_mw,
        "all_modeled_states_dc_secure": all_modeled_states_dc_secure,
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
        default=Path("configs/rts24_deterministic_expansion.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
