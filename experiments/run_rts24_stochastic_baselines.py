"""Run the frozen RTS-24 B3--B5 stochastic mechanism gate."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping

import yaml

from experiments.run_rts24_deterministic_baselines import (
    common_input_signature_for_config,
)
from src.grid import load_rts24
from src.grid.scopf import non_islanding_branch_indices
from src.models import (
    ExistingBranchUpgrade,
    FixedPoi,
    FxQuarter,
    FxServiceEnvelope,
    StochasticBaselinePolicy,
    solve_stochastic_baseline,
)
from src.scenarios import load_frozen_scenario_tree


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_MODEL = "stochastic_b3_b5_physical_lexicographic_baselines"
_POLICY_ORDER = tuple(StochasticBaselinePolicy)
_PLANNING_SCOPE = "policy_decision_groups_F_X_z_start_only"
_SERVICE_VALIDATION = (
    "embedded_actual_and_contract_counterfactual_all_security_states"
)
_DISPATCH_INTERPRETATION = "feasibility_witness_not_canonical_cost_dispatch"
_EVIDENCE_STATUS = (
    "synthetic_scenario_structure_mechanism_gate_not_site_evidence"
)
_ORDERING_TOLERANCE_MWH = 1.0e-6
_POLICY_FIELDS = (
    "policy",
    "role",
    "implementable",
    "feasible",
    "primary_access_shortfall_mwh",
    "minimum_contract_exposure_mwh",
    "maximum_contract_exposure_mwh",
    "minimum_x_exposure_mwh",
    "maximum_x_exposure_mwh",
    "displayed_endpoint_name",
    "stage_count",
    "all_stages_accepted",
    "embedded_state_rows",
    "maximum_original_constraint_violation",
    "maximum_integrality_violation",
    "failure_stage",
    "termination_condition",
)
_ENDPOINT_FIELDS = (
    "policy",
    "role",
    "implementable",
    "endpoint",
    "leaf",
    "leaf_probability",
    "quarter",
    "demand_mw",
    "decision_group",
    "firm_capacity_mw",
    "conditional_capacity_mw",
    "total_capacity_mw",
    "connected_demand_mw",
    "firm_demand_mw",
    "active_conditional_demand_mw",
    "access_shortfall_mw",
    "project_start",
    "project_start_quarter",
    "project_available",
    "normalization_label",
)


def _jsonable(value: object) -> object:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def _write_csv(path: Path, fieldnames: tuple[str, ...], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _output_path(configured: object) -> Path:
    path = Path(str(configured))
    return path if path.is_absolute() else _REPOSITORY_ROOT / path


def _common_inputs(tree) -> tuple[
    object,
    dict[str, object],
    tuple[FxQuarter, ...],
    FixedPoi,
    ExistingBranchUpgrade,
    FxServiceEnvelope,
    tuple[int, ...],
    tuple[int, ...],
    dict[int, float],
]:
    common_path = _output_path(tree.common_input_config)
    live_signature = common_input_signature_for_config(common_path)
    expected_signature = {
        "common_input_signature_id": tree.common_input_signature_id,
        "common_input_signature_schema": tree.common_input_signature_schema,
        "common_input_signature_sha256": tree.common_input_signature_sha256,
    }
    for field, expected in expected_signature.items():
        if live_signature[field] != expected:
            raise ValueError(f"Live common input {field} does not match M5 freeze")

    common = yaml.safe_load(common_path.read_text(encoding="utf-8"))
    planning = common["planning"]
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
    poi_config = common["fixed_poi"]
    poi = FixedPoi(
        bus=int(poi_config["bus"]),
        initial_capacity_mw=float(poi_config["initial_capacity_mw"]),
        application_capacity_mw=float(poi_config["application_capacity_mw"]),
    )
    project_config = common["existing_branch_upgrade"]
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
    service_config = common["service_envelope"]
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
    branch_indices = tuple(non_islanding_branch_indices(data))
    generator_indices = tuple(
        generator.index
        for generator in data.generators
        if generator.in_service and generator.p_max_mw > 0.0
    )
    response_fraction = float(common["security"]["redispatch_fraction_pmax"])
    redispatch = {
        generator.index: response_fraction * generator.p_max_mw
        for generator in data.generators
    }
    return (
        data,
        common,
        quarters,
        poi,
        project,
        service_envelope,
        branch_indices,
        generator_indices,
        redispatch,
    )


def _policy_row(result) -> dict[str, object]:
    endpoint = result.displayed_endpoint
    return {
        "policy": result.policy.value,
        "role": result.role,
        "implementable": result.implementable,
        "feasible": result.feasible,
        "primary_access_shortfall_mwh": result.primary_access_shortfall_mwh,
        "minimum_contract_exposure_mwh": result.minimum_contract_exposure_mwh,
        "maximum_contract_exposure_mwh": result.maximum_contract_exposure_mwh,
        "minimum_x_exposure_mwh": result.minimum_x_exposure_mwh,
        "maximum_x_exposure_mwh": result.maximum_x_exposure_mwh,
        "displayed_endpoint_name": result.displayed_endpoint_name,
        "stage_count": len(result.stage_diagnostics),
        "all_stages_accepted": bool(result.stage_diagnostics)
        and all(stage.accepted for stage in result.stage_diagnostics),
        "embedded_state_rows": result.embedded_state_rows,
        "maximum_original_constraint_violation": (
            None if endpoint is None else endpoint.maximum_original_constraint_violation
        ),
        "maximum_integrality_violation": (
            None if endpoint is None else endpoint.maximum_integrality_violation
        ),
        "failure_stage": result.failure_stage,
        "termination_condition": result.termination_condition,
    }


def _endpoint_rows(tree, result) -> list[dict[str, object]]:
    demand_by_name = {state.name: state for state in tree.demand_states}
    leaf_by_name = {leaf.name: leaf for leaf in tree.leaves}
    rows = []
    for endpoint_name, endpoint in (
        ("minimum_x", result.minimum_x_endpoint),
        ("maximum_x", result.maximum_x_endpoint),
    ):
        if endpoint is None:
            continue
        for leaf in tree.leaf_names:
            demand_path = demand_by_name[leaf_by_name[leaf].demand_state].demand_mw
            for quarter, demand in zip(tree.quarters, demand_path):
                rows.append(
                    {
                        "policy": result.policy.value,
                        "role": result.role,
                        "implementable": result.implementable,
                        "endpoint": endpoint_name,
                        "leaf": leaf,
                        "leaf_probability": leaf_by_name[leaf].probability,
                        "quarter": quarter,
                        "demand_mw": demand,
                        "decision_group": endpoint.decision_group_by_quarter[leaf][
                            quarter
                        ],
                        "firm_capacity_mw": endpoint.firm_capacity_mw[leaf][quarter],
                        "conditional_capacity_mw": (
                            endpoint.conditional_capacity_mw[leaf][quarter]
                        ),
                        "total_capacity_mw": endpoint.total_capacity_mw[leaf][
                            quarter
                        ],
                        "connected_demand_mw": endpoint.connected_demand_mw[leaf][
                            quarter
                        ],
                        "firm_demand_mw": endpoint.firm_demand_mw[leaf][quarter],
                        "active_conditional_demand_mw": (
                            endpoint.active_conditional_demand_mw[leaf][quarter]
                        ),
                        "access_shortfall_mw": endpoint.access_shortfall_mw[leaf][
                            quarter
                        ],
                        "project_start": endpoint.project_start_by_quarter[leaf][
                            quarter
                        ],
                        "project_start_quarter": endpoint.project_start_quarter[leaf],
                        "project_available": (
                            endpoint.project_available_by_quarter[leaf][quarter]
                        ),
                        "normalization_label": endpoint.normalization_label,
                    }
                )
    return rows


def run(config_path: Path) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    tree = load_frozen_scenario_tree(config_path)
    execution = config["execution"]
    if execution["model"] != _MODEL:
        raise ValueError("Unsupported stochastic baseline model")
    policies = tuple(StochasticBaselinePolicy(name) for name in execution["policy_order"])
    if policies != _POLICY_ORDER:
        raise ValueError("Stochastic policies must run in B3, B4, B5 order")
    if execution["planning_variable_scope"] != _PLANNING_SCOPE:
        raise ValueError("Unsupported stochastic planning-variable scope")
    if execution["service_validation"] != _SERVICE_VALIDATION:
        raise ValueError("Embedded actual/contract validation must remain enabled")
    if execution["dispatch_interpretation"] != _DISPATCH_INTERPRETATION:
        raise ValueError("Dispatch witness interpretation must remain explicit")
    if execution["evidence_status"] != _EVIDENCE_STATUS:
        raise ValueError("Stochastic evidence status must remain synthetic")
    if execution["security_certified"] is not False or tree.security_certified:
        raise ValueError("M5 synthetic mechanism gate cannot claim certification")

    (
        data,
        common,
        quarters,
        poi,
        project,
        service_envelope,
        branch_indices,
        generator_indices,
        redispatch,
    ) = _common_inputs(tree)
    security = common["security"]
    solver_name = common["solver"]["name"]
    results = []
    for policy in policies:
        results.append(
            solve_stochastic_baseline(
                data,
                policy=policy,
                tree=tree,
                quarters=quarters,
                poi=poi,
                project=project,
                service_envelope=service_envelope,
                redispatch_up_mw=redispatch,
                redispatch_down_mw=redispatch,
                branch_indices=branch_indices,
                generator_indices=generator_indices,
                immediate_rating=security["immediate_branch_rating"],
                sustained_rating=security["sustained_rating"],
                solver_name=solver_name,
            )
        )

    policy_rows = [_policy_row(result) for result in results]
    endpoint_rows = [
        row for result in results for row in _endpoint_rows(tree, result)
    ]
    all_feasible = all(result.feasible for result in results)
    shortfall = {
        result.policy: result.primary_access_shortfall_mwh for result in results
    }
    ordering_passed = bool(
        all_feasible
        and shortfall[StochasticBaselinePolicy.B5]
        <= shortfall[StochasticBaselinePolicy.B4] + _ORDERING_TOLERANCE_MWH
        and shortfall[StochasticBaselinePolicy.B4]
        <= shortfall[StochasticBaselinePolicy.B3] + _ORDERING_TOLERANCE_MWH
    )
    summary = {
        "model": _MODEL,
        "scenario_tree_id": tree.id,
        "parameter_status": tree.parameter_status,
        "probability_basis": tree.probability_basis,
        "common_input_signature_id": tree.common_input_signature_id,
        "common_input_signature_schema": tree.common_input_signature_schema,
        "common_input_signature_sha256": tree.common_input_signature_sha256,
        "policy_order": [policy.value for policy in policies],
        "natural_node_counts": {
            quarter: len(tree.nodes_for_quarter(quarter))
            for quarter in tree.quarters
        },
        "decision_group_counts": {
            policy.value: {
                quarter: len(tree.decision_groups(policy.value, quarter))
                for quarter in tree.quarters
            }
            for policy in policies
        },
        "leaf_count": len(tree.leaves),
        "security_state_count": len(results[0].states) if results else 0,
        "service_validation": _SERVICE_VALIDATION,
        "dispatch_interpretation": _DISPATCH_INTERPRETATION,
        "all_policies_feasible": all_feasible,
        "information_ordering_passed": ordering_passed,
        "formal_endpoints_published": all_feasible and ordering_passed,
        "security_certified": False,
        "certification_blockers": [
            "synthetic_tree_probabilities_not_empirical",
            "frequency_response_and_branch_10_unresolved",
            "expansion_ac_parameters_missing",
            "chronological_scuc_sced_not_modeled",
            "continuous_validation_hours_zero",
        ],
        "policy_results": [
            {
                **row,
                "stage_diagnostics": _jsonable(result.stage_diagnostics),
                "minimum_x_endpoint_audit": (
                    None
                    if result.minimum_x_endpoint is None
                    else {
                        "primary_deviation_mwh": (
                            result.minimum_x_endpoint.primary_deviation_mwh
                        ),
                        "contract_exposure_deviation_mwh": (
                            result.minimum_x_endpoint.contract_exposure_deviation_mwh
                        ),
                        "x_exposure_deviation_mwh": (
                            result.minimum_x_endpoint.x_exposure_deviation_mwh
                        ),
                        "maximum_original_constraint_violation": (
                            result.minimum_x_endpoint.maximum_original_constraint_violation
                        ),
                        "maximum_integrality_violation": (
                            result.minimum_x_endpoint.maximum_integrality_violation
                        ),
                    }
                ),
            }
            for row, result in zip(policy_rows, results)
        ],
    }

    output = config["output"]
    _write_csv(_output_path(output["policy_path"]), _POLICY_FIELDS, policy_rows)
    _write_csv(
        _output_path(output["endpoint_path"]),
        _ENDPOINT_FIELDS,
        endpoint_rows if summary["formal_endpoints_published"] else [],
    )
    summary_path = _output_path(output["summary_path"])
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(_jsonable(summary), ensure_ascii=False, indent=2, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    summary = run(args.config)
    print(json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
