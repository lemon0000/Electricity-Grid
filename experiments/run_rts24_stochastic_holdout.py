"""Execute frozen B3/B4 endpoints on the M5c synthetic holdout paths."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import replace
from pathlib import Path

from experiments.run_rts24_stochastic_baselines import _common_inputs
from src.evaluation import (
    StochasticHoldoutProtocol,
    load_stochastic_holdout_protocol,
    map_fixed_policy_path,
)
from src.models import FixedFxPlan, evaluate_deterministic_fx_plan


_POLICIES = ("B3", "B4")
_ENDPOINTS = ("minimum_x", "maximum_x")
_PATH_FIELDS = (
    "run_feasible",
    "execution_passed",
    "policy",
    "endpoint",
    "holdout_leaf",
    "leaf_probability",
    "demand_path",
    "project_state",
    "extra_lead_time_quarters",
    "quarter",
    "demand_mw",
    "mapped_demand_class",
    "mapped_terminal_outcome",
    "mapped_project_state",
    "decision_group",
    "firm_capacity_mw",
    "conditional_capacity_mw",
    "total_capacity_mw",
    "project_start",
    "project_start_quarter",
    "project_commissioned",
    "connected_demand_mw",
    "firm_demand_mw",
    "active_conditional_demand_mw",
    "access_shortfall_mw",
    "path_access_shortfall_mwh",
    "security_state_count",
    "maximum_power_balance_residual_mw",
    "maximum_firm_breach_mw",
    "maximum_conditional_breach_mw",
    "termination_condition",
    "exception_type",
    "security_certified",
)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=_PATH_FIELDS,
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)


def _nested_max(values) -> float:
    flattened = [float(value) for quarter in values.values() for value in quarter.values()]
    return max(flattened, default=0.0)


def _execution_audit(
    result,
    mapped,
    quarters,
    protocol: StochasticHoldoutProtocol,
) -> dict[str, object]:
    reasons = []
    quarter_names = tuple(quarter.name for quarter in quarters)
    if not result.feasible:
        reasons.append("m3_fixed_policy_execution_infeasible")
    if len(result.states) != 107:
        reasons.append("security_state_count_not_107")
    expected_quarters = set(quarter_names)
    for field in (
        "firm_capacity_mw",
        "conditional_capacity_mw",
        "total_capacity_mw",
        "connected_demand_mw",
        "firm_demand_mw",
        "active_conditional_demand_mw",
        "access_shortfall_mw",
        "commissioned_by_quarter",
    ):
        if set(getattr(result, field, {})) != expected_quarters:
            reasons.append(f"{field}_quarter_set_mismatch")

    tolerance = protocol.contract_breach_tolerance_mw
    for quarter in quarters:
        name = quarter.name
        if name not in getattr(result, "firm_capacity_mw", {}):
            continue
        if abs(result.firm_capacity_mw[name] - mapped.firm_capacity_mw[name]) > tolerance:
            reasons.append(f"firm_capacity_mismatch:{name}")
        if (
            abs(
                result.conditional_capacity_mw[name]
                - mapped.conditional_capacity_mw[name]
            )
            > tolerance
        ):
            reasons.append(f"conditional_capacity_mismatch:{name}")
        expected_connected = min(
            quarter.data_center_demand_mw,
            mapped.total_capacity_mw[name],
        )
        if abs(result.connected_demand_mw[name] - expected_connected) > tolerance:
            reasons.append(f"connected_demand_mismatch:{name}")
        expected_shortfall = quarter.data_center_demand_mw - expected_connected
        if abs(result.access_shortfall_mw[name] - expected_shortfall) > tolerance:
            reasons.append(f"access_shortfall_mismatch:{name}")

    state_names = {state.name for state in result.states}
    maximum_balance = 0.0
    for field in ("actual_state_results", "certified_state_results"):
        layer_results = getattr(result, field, {})
        if set(layer_results) != expected_quarters:
            reasons.append(f"{field}_quarter_set_mismatch")
            continue
        for quarter in quarter_names:
            state_results = layer_results[quarter]
            if set(state_results) != state_names:
                reasons.append(f"{field}_state_set_mismatch:{quarter}")
                continue
            for state_result in state_results.values():
                if not state_result.feasible:
                    reasons.append(f"{field}_state_infeasible:{quarter}")
                maximum_balance = max(
                    maximum_balance,
                    float(state_result.max_balance_residual_mw),
                )
    if maximum_balance > protocol.power_balance_tolerance_mw:
        reasons.append("power_balance_tolerance_exceeded")

    firm_breach = _nested_max(getattr(result, "firm_breach_mw", {}))
    conditional_breach = _nested_max(
        getattr(result, "conditional_breach_mw", {})
    )
    if firm_breach > tolerance:
        reasons.append("firm_breach_tolerance_exceeded")
    if conditional_breach > tolerance:
        reasons.append("conditional_breach_tolerance_exceeded")

    state_by_name = {state.name: state for state in result.states}
    for quarter in quarter_names:
        for state_name in state_names:
            if quarter not in getattr(result, "actual_grid_curtailment_mw", {}):
                continue
            actual_call = result.actual_grid_curtailment_mw[quarter][state_name]
            contract_call = result.certified_grid_curtailment_mw[quarter][state_name]
            state = state_by_name[state_name]
            if state.response_mode in {"base", "fixed"}:
                if abs(actual_call) > tolerance or abs(contract_call) > tolerance:
                    reasons.append(f"forbidden_call:{quarter}:{state_name}")
            else:
                if (
                    actual_call
                    > result.active_conditional_demand_mw[quarter] + tolerance
                ):
                    reasons.append(f"actual_call_exceeds_active_x:{quarter}:{state_name}")
                if (
                    contract_call
                    > result.conditional_capacity_mw[quarter] + tolerance
                ):
                    reasons.append(f"contract_call_exceeds_x:{quarter}:{state_name}")

    return {
        "passed": not reasons,
        "failure_reasons": sorted(set(reasons)),
        "maximum_power_balance_residual_mw": maximum_balance,
        "maximum_firm_breach_mw": firm_breach,
        "maximum_conditional_breach_mw": conditional_breach,
    }


def _path_rows(records, run_feasible: bool) -> list[dict[str, object]]:
    rows = []
    for record in records:
        protocol = record["protocol"]
        leaf = record["leaf"]
        demand_path = protocol.demand_path(leaf.demand_path)
        project_state = protocol.project_state(leaf.project_state)
        mapped = record["mapped"]
        result = record["result"]
        audit = record["audit"]
        for quarter, demand in zip(protocol.quarters, demand_path.demand_mw):
            rows.append(
                {
                    "run_feasible": run_feasible,
                    "execution_passed": audit["passed"],
                    "policy": mapped.policy,
                    "endpoint": mapped.endpoint,
                    "holdout_leaf": leaf.name,
                    "leaf_probability": leaf.probability,
                    "demand_path": leaf.demand_path,
                    "project_state": leaf.project_state,
                    "extra_lead_time_quarters": (
                        project_state.extra_lead_time_quarters
                    ),
                    "quarter": quarter,
                    "demand_mw": demand,
                    "mapped_demand_class": mapped.mapped_demand_class,
                    "mapped_terminal_outcome": mapped.mapped_terminal_outcome,
                    "mapped_project_state": mapped.mapped_project_state,
                    "decision_group": mapped.decision_group_by_quarter[quarter],
                    "firm_capacity_mw": mapped.firm_capacity_mw[quarter],
                    "conditional_capacity_mw": (
                        mapped.conditional_capacity_mw[quarter]
                    ),
                    "total_capacity_mw": mapped.total_capacity_mw[quarter],
                    "project_start": mapped.project_start_by_quarter[quarter],
                    "project_start_quarter": mapped.project_start_quarter,
                    "project_commissioned": (
                        None
                        if result is None
                        else result.commissioned_by_quarter.get(quarter)
                    ),
                    "connected_demand_mw": (
                        None
                        if result is None
                        else result.connected_demand_mw.get(quarter)
                    ),
                    "firm_demand_mw": (
                        None if result is None else result.firm_demand_mw.get(quarter)
                    ),
                    "active_conditional_demand_mw": (
                        None
                        if result is None
                        else result.active_conditional_demand_mw.get(quarter)
                    ),
                    "access_shortfall_mw": (
                        None
                        if result is None
                        else result.access_shortfall_mw.get(quarter)
                    ),
                    "path_access_shortfall_mwh": record["path_shortfall_mwh"],
                    "security_state_count": (
                        None if result is None else len(result.states)
                    ),
                    "maximum_power_balance_residual_mw": audit[
                        "maximum_power_balance_residual_mw"
                    ],
                    "maximum_firm_breach_mw": audit["maximum_firm_breach_mw"],
                    "maximum_conditional_breach_mw": audit[
                        "maximum_conditional_breach_mw"
                    ],
                    "termination_condition": (
                        "execution_exception"
                        if result is None
                        else result.termination_condition
                    ),
                    "exception_type": record["exception_type"],
                    "security_certified": False,
                }
            )
    return rows


def run(config_path: Path) -> dict[str, object]:
    protocol = load_stochastic_holdout_protocol(config_path)
    (
        data,
        common,
        training_quarters,
        poi,
        project,
        service_envelope,
        branch_indices,
        generator_indices,
        redispatch,
    ) = _common_inputs(protocol.training_tree)
    security = common["security"]
    objective = common["objective"]
    records = []
    completed = 0
    for policy in _POLICIES:
        for endpoint in _ENDPOINTS:
            for leaf in protocol.leaves:
                demand_path = protocol.demand_path(leaf.demand_path)
                project_state = protocol.project_state(leaf.project_state)
                mapped = map_fixed_policy_path(
                    protocol,
                    policy=policy,
                    endpoint=endpoint,
                    holdout_leaf=leaf.name,
                )
                quarters = tuple(
                    replace(quarter, data_center_demand_mw=demand)
                    for quarter, demand in zip(
                        training_quarters,
                        demand_path.demand_mw,
                    )
                )
                realized_project = replace(
                    project,
                    lead_time_quarters=(
                        project.lead_time_quarters
                        + project_state.extra_lead_time_quarters
                    ),
                )
                plan = FixedFxPlan(
                    firm_capacity_mw=mapped.firm_capacity_mw,
                    conditional_capacity_mw=mapped.conditional_capacity_mw,
                    project_start_quarter=mapped.project_start_quarter,
                    parameter_status=mapped.parameter_status,
                )
                result = None
                exception_type = None
                exception_message = None
                try:
                    result = evaluate_deterministic_fx_plan(
                        data,
                        quarters=quarters,
                        poi=poi,
                        project=realized_project,
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
                        primary_objective_tolerance=(
                            protocol.primary_objective_tolerance
                        ),
                        solver_name=common["solver"]["name"],
                    )
                except Exception as error:
                    exception_type = type(error).__name__
                    exception_message = str(error)
                if result is None:
                    audit = {
                        "passed": False,
                        "failure_reasons": ["execution_exception"],
                        "maximum_power_balance_residual_mw": None,
                        "maximum_firm_breach_mw": None,
                        "maximum_conditional_breach_mw": None,
                    }
                    path_shortfall = None
                else:
                    audit = _execution_audit(result, mapped, quarters, protocol)
                    path_shortfall = sum(
                        quarter.operating_hours
                        * result.access_shortfall_mw[quarter.name]
                        for quarter in quarters
                    )
                records.append(
                    {
                        "protocol": protocol,
                        "leaf": leaf,
                        "mapped": mapped,
                        "result": result,
                        "audit": audit,
                        "path_shortfall_mwh": path_shortfall,
                        "exception_type": exception_type,
                        "exception_message": exception_message,
                    }
                )
                completed += 1
                print(
                    f"M5c execution {completed}/48: {policy}/{endpoint}/{leaf.name} "
                    f"passed={audit['passed']}",
                    file=sys.stderr,
                    flush=True,
                )

    run_feasible = all(record["audit"]["passed"] for record in records)
    endpoint_shortfall = None
    paired_values = None
    value_interval = None
    if run_feasible:
        endpoint_shortfall = {
            policy: {
                endpoint: sum(
                    record["leaf"].probability
                    * record["path_shortfall_mwh"]
                    for record in records
                    if record["mapped"].policy == policy
                    and record["mapped"].endpoint == endpoint
                )
                for endpoint in _ENDPOINTS
            }
            for policy in _POLICIES
        }
        paired_values = {
            endpoint: (
                endpoint_shortfall["B3"][endpoint]
                - endpoint_shortfall["B4"][endpoint]
            )
            for endpoint in _ENDPOINTS
        }
        all_differences = tuple(
            endpoint_shortfall["B3"][b3_endpoint]
            - endpoint_shortfall["B4"][b4_endpoint]
            for b3_endpoint in _ENDPOINTS
            for b4_endpoint in _ENDPOINTS
        )
        value_interval = [min(all_differences), max(all_differences)]

    path_rows = _path_rows(records, run_feasible)
    _write_csv(protocol.path_output, path_rows)
    summary = {
        "evaluation_id": protocol.id,
        "parameter_status": protocol.parameter_status,
        "probability_basis": protocol.probability_basis,
        "selection_rule": protocol.selection_rule,
        "training_scenario_tree_id": protocol.training_tree.id,
        "training_summary_sha256": protocol.training_summary_sha256,
        "training_endpoint_sha256": protocol.training_endpoint_sha256,
        "common_input_signature_id": protocol.training_tree.common_input_signature_id,
        "common_input_signature_schema": (
            protocol.training_tree.common_input_signature_schema
        ),
        "common_input_signature_sha256": (
            protocol.training_tree.common_input_signature_sha256
        ),
        "policy_order": list(_POLICIES),
        "endpoint_order": list(_ENDPOINTS),
        "holdout_demand_path_count": len(protocol.demand_paths),
        "holdout_project_state_count": len(protocol.project_states),
        "holdout_leaf_count": len(protocol.leaves),
        "execution_count": len(records),
        "all_executions_attempted": len(records) == 48,
        "all_executions_feasible": run_feasible,
        "runtime_recourse_only": True,
        "planning_reoptimization_allowed": False,
        "security_state_count": 107,
        "endpoint_expected_access_shortfall_mwh": endpoint_shortfall,
        "paired_endpoint_adaptivity_value_mwh": paired_values,
        "set_valued_holdout_adaptivity_value_interval_mwh": value_interval,
        "value_orientation": "B3_minus_B4_positive_means_multistage_improves",
        "synthetic_holdout_value_published": run_feasible,
        "formal_vma_published": False,
        "economic_optimum_claimed": False,
        "security_certified": False,
        "certification_blockers": [
            "deterministic_balanced_holdout_weights_not_empirical_probability",
            "frequency_response_and_branch_10_unresolved",
            "expansion_ac_parameters_missing",
            "chronological_scuc_sced_not_modeled",
            "continuous_validation_hours_zero",
        ],
        "execution_results": [
            {
                "policy": record["mapped"].policy,
                "endpoint": record["mapped"].endpoint,
                "holdout_leaf": record["leaf"].name,
                "leaf_probability": record["leaf"].probability,
                "passed": record["audit"]["passed"],
                "failure_reasons": record["audit"]["failure_reasons"],
                "path_access_shortfall_mwh": record["path_shortfall_mwh"],
                "maximum_power_balance_residual_mw": record["audit"][
                    "maximum_power_balance_residual_mw"
                ],
                "maximum_firm_breach_mw": record["audit"][
                    "maximum_firm_breach_mw"
                ],
                "maximum_conditional_breach_mw": record["audit"][
                    "maximum_conditional_breach_mw"
                ],
                "termination_condition": (
                    "execution_exception"
                    if record["result"] is None
                    else record["result"].termination_condition
                ),
                "exception_type": record["exception_type"],
                "exception_message": record["exception_message"],
            }
            for record in records
        ],
        "output_paths": {
            "path_results": str(protocol.path_output),
            "summary": str(protocol.summary_output),
        },
    }
    protocol.summary_output.parent.mkdir(parents=True, exist_ok=True)
    protocol.summary_output.write_text(
        json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rts24_stochastic_holdout.yaml"),
    )
    args = parser.parse_args()
    summary = run(args.config)
    print(json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2))
    if not summary["all_executions_feasible"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
