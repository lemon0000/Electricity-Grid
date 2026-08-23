"""Run chronological RQ2 L5 recourse with RTS-24-derived event calls."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from dataclasses import asdict, replace
from math import isfinite
from numbers import Integral
from pathlib import Path

import yaml
from pyomo.environ import SolverFactory

from src.evaluation.flexibility_envelope import ChronologicalFlexibilityEnvelope
from src.evaluation.service_risk import ServiceLossCoefficients
from src.grid import (
    load_rts24,
    non_islanding_branch_indices,
    scale_rts24_demand,
    solve_dc_opf,
)
from src.grid.network_grid_need import (
    NETWORK_GRID_NEED_METHODS,
    NetworkGridNeedInputs,
    derive_network_grid_need,
)
from src.models.economic_temporal_stochastic import (
    TemporalEconomicInputs,
    TemporalEconomicScenario,
    solve_temporal_economic_stochastic,
)

_ROOT = Path(__file__).resolve().parents[1]


def _mapping(raw: object, label: str) -> dict:
    if not isinstance(raw, dict):
        raise TypeError(f"{label} must be a mapping")
    return raw


def _number(raw: object, label: str) -> float:
    if isinstance(raw, bool):
        raise TypeError(f"{label} must be numeric")
    try:
        number = float(raw)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _status(raw: object, label: str) -> str:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a nonempty string")
    return raw


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _network_data_sha256(data) -> str:
    payload = json.dumps(
        asdict(data), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return _sha256_bytes(payload)


def _solver_version(solver_name: str) -> str:
    solver = SolverFactory(solver_name)
    if not solver.available(exception_flag=False):
        raise RuntimeError(f"Solver '{solver_name}' is not available")
    raw = solver.version()
    return ".".join(str(item) for item in raw) if isinstance(raw, tuple) else str(raw)


def _validate_network_selection(
    data,
    *,
    poi_bus: int,
    balancing_bus: int,
    branch_indices: tuple[int, ...],
    generator_indices: tuple[int, ...],
    sustained_rating: str,
) -> None:
    buses = {bus.index for bus in data.buses}
    branches = {branch.index: branch for branch in data.branches}
    generators = {generator.index: generator for generator in data.generators}
    if poi_bus not in buses or balancing_bus not in buses:
        raise ValueError("POI and balancing buses must exist in the network")
    if poi_bus == balancing_bus:
        raise ValueError("POI and balancing buses must differ")
    if not branch_indices and not generator_indices:
        raise ValueError("at least one selected N-1 state is required")
    if set(branch_indices) - branches.keys():
        raise ValueError("branch_indices contains an unknown branch")
    if set(generator_indices) - generators.keys():
        raise ValueError("generator_indices contains an unknown generator")
    if set(branch_indices) - set(non_islanding_branch_indices(data)):
        raise ValueError("branch_indices contains an islanding branch")
    if any(
        not generators[index].in_service or generators[index].p_max_mw <= 0.0
        for index in generator_indices
    ):
        raise ValueError("generator_indices contains an invalid outage state")
    for branch in data.branches:
        branch.rating_mw(sustained_rating)


def _normal_state_check(
    data,
    *,
    system_load_multiplier: float,
    data_center_demand_mw: float,
    poi_bus: int,
    sustained_rating: str,
    solver_name: str,
) -> dict[str, object]:
    operating = scale_rts24_demand(data, system_load_multiplier)
    operating = replace(
        operating,
        buses=tuple(
            replace(
                bus,
                demand_mw=(
                    bus.demand_mw + data_center_demand_mw
                    if bus.index == poi_bus
                    else bus.demand_mw
                ),
            )
            for bus in operating.buses
        ),
    )
    result = solve_dc_opf(
        operating,
        branch_rating=sustained_rating,
        solver_name=solver_name,
    )
    if not result.feasible:
        raise RuntimeError(
            "normal-state DC-OPF failed for an hourly operating point: "
            f"{result.termination_condition}"
        )
    balance_residual = result.max_balance_residual_mw
    thermal_violation = max(
        (
            max(
                abs(result.branch_flows_mw[branch.index])
                - branch.rating_mw(sustained_rating),
                0.0,
            )
            for branch in operating.branches
            if branch.in_service
        ),
        default=0.0,
    )
    if (
        balance_residual is None
        or not isfinite(balance_residual)
        or not isfinite(thermal_violation)
        or balance_residual > 1.0e-6
        or thermal_violation > 1.0e-6
    ):
        raise RuntimeError("normal-state DC-OPF residual audit failed")
    return {
        "feasible": True,
        "termination_condition": result.termination_condition,
        "solver_status": result.solver_status,
        "objective": result.objective,
        "maximum_balance_residual_mw": balance_residual,
        "maximum_thermal_violation_mw": thermal_violation,
    }


def _number_tuple(raw: object, label: str) -> tuple[float, ...]:
    if not isinstance(raw, list):
        raise TypeError(f"{label} must be a list")
    return tuple(_number(item, f"{label}[{index}]") for index, item in enumerate(raw))


def _integer_tuple(raw: object, label: str) -> tuple[int, ...]:
    if not isinstance(raw, list) or any(
        isinstance(item, bool) or not isinstance(item, Integral) for item in raw
    ):
        raise TypeError(f"{label} must be an integer list")
    result = tuple(int(item) for item in raw)
    if len(result) != len(set(result)):
        raise ValueError(f"{label} must not contain duplicates")
    return result


def _integer(raw: object, label: str) -> int:
    if isinstance(raw, bool) or not isinstance(raw, Integral):
        raise TypeError(f"{label} must be an integer")
    return int(raw)


def _envelope(raw: object) -> ChronologicalFlexibilityEnvelope:
    values = _mapping(raw, "envelope")
    return ChronologicalFlexibilityEnvelope(
        time_step_hours=_number(values.get("time_step_hours"), "time_step_hours"),
        maximum_event_duration_hours=_number(
            values.get("maximum_event_duration_hours"),
            "maximum_event_duration_hours",
        ),
        minimum_recovery_hours=_number(
            values.get("minimum_recovery_hours"), "minimum_recovery_hours"
        ),
        maximum_events_by_period=dict(values.get("maximum_events_by_period", {})),
        maximum_curtailment_energy_mwh_by_period=dict(
            values.get("maximum_curtailment_energy_mwh_by_period", {})
        ),
        maximum_recovery_debt_mwh=_number(
            values.get("maximum_recovery_debt_mwh"),
            "maximum_recovery_debt_mwh",
        ),
        maximum_recovery_power_mw=_number(
            values.get("maximum_recovery_power_mw"),
            "maximum_recovery_power_mw",
        ),
        minimum_event_power_mw=_number(
            values.get("minimum_event_power_mw"), "minimum_event_power_mw"
        ),
        response_time_hours=_number(
            values.get("response_time_hours"), "response_time_hours"
        ),
        curtailment_ramp_mw_per_hour=_number(
            values.get("curtailment_ramp_mw_per_hour"),
            "curtailment_ramp_mw_per_hour",
        ),
        recovery_efficiency=_number(
            values.get("recovery_efficiency"), "recovery_efficiency"
        ),
        terminal_debt_limit_mwh_by_period=dict(
            values.get("terminal_debt_limit_mwh_by_period", {})
        ),
        parameter_status=_status(
            values.get("parameter_status"), "envelope.parameter_status"
        ),
    )


def _coefficients(raw: object) -> ServiceLossCoefficients:
    values = _mapping(raw, "coefficients")
    return ServiceLossCoefficients(
        kappa_access=_number(values.get("kappa_access"), "kappa_access"),
        kappa_grid=_number(values.get("kappa_grid"), "kappa_grid"),
        kappa_green=_number(values.get("kappa_green"), "kappa_green"),
        kappa_drop=_number(values.get("kappa_drop"), "kappa_drop"),
        kappa_breach_firm=_number(
            values.get("kappa_breach_firm"), "kappa_breach_firm"
        ),
        kappa_breach_conditional=_number(
            values.get("kappa_breach_conditional"),
            "kappa_breach_conditional",
        ),
        parameter_status=_status(
            values.get("parameter_status"), "coefficients.parameter_status"
        ),
    )


def _raw_scenarios(raw: object) -> tuple[dict, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("scenarios must be a nonempty list")
    result = []
    for scenario_index, item in enumerate(raw):
        scenario = _mapping(item, f"scenarios[{scenario_index}]")
        name = scenario.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("scenario name must be explicit")
        if "grid_need_mw" in scenario:
            raise ValueError(
                "temporal network runner forbids hand-entered grid_need_mw"
            )
        periods = scenario.get("periods")
        if (
            not isinstance(periods, list)
            or not periods
            or any(not isinstance(period, str) or not period for period in periods)
        ):
            raise ValueError(f"{name}.periods must be a nonempty list")
        arrays = {
            key: _number_tuple(scenario.get(key), f"{name}.{key}")
            for key in (
                "system_load_multiplier",
                "data_center_demand_mw",
                "network_call_active",
                "green_call_mw",
                "connected_demand_mw",
                "recovery_headroom_mw",
            )
        }
        lengths = {len(periods), *(len(values) for values in arrays.values())}
        if len(lengths) != 1:
            raise ValueError(f"{name} chronological arrays must have equal length")
        if any(value not in (0.0, 1.0) for value in arrays["network_call_active"]):
            raise ValueError("network_call_active must contain 0 or 1")
        if any(
            abs(dc - connected) > 1.0e-6
            for dc, connected in zip(
                arrays["data_center_demand_mw"],
                arrays["connected_demand_mw"],
            )
        ):
            raise ValueError(
                "connected_demand_mw must equal data_center_demand_mw"
            )
        completed = scenario.get("completed_periods")
        if not isinstance(completed, list) or any(
            not isinstance(period, str) or not period for period in completed
        ):
            raise TypeError("completed_periods must be a list")
        if "require_terminal_event_inactive" not in scenario:
            raise ValueError(
                "require_terminal_event_inactive must be explicit"
            )
        require_inactive = scenario["require_terminal_event_inactive"]
        if not isinstance(require_inactive, bool):
            raise TypeError("require_terminal_event_inactive must be boolean")
        boundary_status = scenario.get("boundary_state_status")
        if boundary_status != "clean_boundary_with_zero_carry_in":
            raise ValueError(
                "boundary_state_status must be "
                "clean_boundary_with_zero_carry_in"
            )
        result.append(
            {
                "name": name,
                "probability": _number(
                    scenario.get("probability"), f"{name}.probability"
                ),
                "periods": tuple(periods),
                **arrays,
                "completed_periods": frozenset(completed),
                "require_terminal_event_inactive": require_inactive,
                "boundary_state_status": boundary_status,
            }
        )
    return tuple(result)


def _derive_temporal_scenarios(
    *,
    data,
    raw_scenarios: tuple[dict, ...],
    method: str,
    poi_bus: int,
    balancing_bus: int,
    branch_indices: tuple[int, ...],
    generator_indices: tuple[int, ...],
    redispatch_fraction_of_pmax: float,
    sustained_rating: str,
    solver_name: str,
    parameter_status: str,
) -> tuple[tuple[TemporalEconomicScenario, ...], dict[str, object]]:
    cache = {}
    normal_cache = {}
    key_ids = {}
    unique_derivations = {}
    hour_references = {}
    temporal = []
    for scenario in raw_scenarios:
        grid_need = []
        scenario_references = []
        for index, active in enumerate(scenario["network_call_active"]):
            key = (
                scenario["system_load_multiplier"][index],
                scenario["data_center_demand_mw"][index],
            )
            if key not in key_ids:
                key_ids[key] = f"operating_point_{len(key_ids)}"
            operating_point_id = key_ids[key]
            if key not in normal_cache:
                normal_cache[key] = _normal_state_check(
                    data,
                    system_load_multiplier=key[0],
                    data_center_demand_mw=key[1],
                    poi_bus=poi_bus,
                    sustained_rating=sustained_rating,
                    solver_name=solver_name,
                )
                unique_derivations[operating_point_id] = {
                    "system_load_multiplier": key[0],
                    "data_center_demand_mw": key[1],
                    "normal_state": normal_cache[key],
                    "n1_result": None,
                }
            scenario_references.append(operating_point_id)
            if active == 0.0:
                grid_need.append(0.0)
                continue
            if key not in cache:
                cache[key] = derive_network_grid_need(
                    NetworkGridNeedInputs(
                        data=data,
                        poi_bus=poi_bus,
                        balancing_bus=balancing_bus,
                        system_load_multiplier=key[0],
                        data_center_demand_mw=key[1],
                        branch_indices=branch_indices,
                        generator_indices=generator_indices,
                        redispatch_fraction_of_pmax=redispatch_fraction_of_pmax,
                        sustained_rating=sustained_rating,
                        method=method,
                        parameter_status=parameter_status,
                        solver_name=solver_name,
                    )
                )
                unique_derivations[operating_point_id]["n1_result"] = asdict(
                    cache[key]
                )
            result = cache[key]
            if not result.feasible:
                raise RuntimeError(
                    f"network derivation failed for {scenario['name']}[{index}]"
                )
            grid_need.append(float(result.grid_need_mw))
        temporal.append(
            TemporalEconomicScenario(
                name=scenario["name"],
                probability=scenario["probability"],
                periods=scenario["periods"],
                grid_need_mw=tuple(grid_need),
                green_call_mw=scenario["green_call_mw"],
                connected_demand_mw=scenario["connected_demand_mw"],
                recovery_headroom_mw=scenario["recovery_headroom_mw"],
                completed_periods=scenario["completed_periods"],
                require_terminal_event_inactive=scenario[
                    "require_terminal_event_inactive"
                ],
                boundary_state_status=scenario["boundary_state_status"],
            )
        )
        hour_references[scenario["name"]] = scenario_references
    return tuple(temporal), {
        "network_method": method,
        "event_indicator_status": "synthetic_not_empirical_outage_timing",
        "network_source_package": data.source_package,
        "network_source_version": data.source_version,
        "network_data_sha256": _network_data_sha256(data),
        "solver_name": solver_name,
        "solver_version": _solver_version(solver_name),
        "unique_operating_point_derivations": unique_derivations,
        "scenario_hour_operating_point_reference": hour_references,
    }


def _result_dict(result) -> dict[str, object]:
    raw = asdict(result)
    maximum_excess = max(
        (
            dispatch.maximum_physical_budget_excess_mw
            for dispatch in result.scenario_dispatch.values()
        ),
        default=0.0,
    )
    raw["maximum_physical_budget_excess_mw"] = maximum_excess
    return raw


def run(config_path: Path) -> dict[str, object]:
    config_bytes = config_path.read_bytes()
    config = _mapping(yaml.safe_load(config_bytes), "config")
    evaluation = _mapping(config.get("evaluation"), "evaluation")
    if evaluation.get("security_certified") is not False:
        raise ValueError("evaluation.security_certified must remain false")
    status = evaluation.get("parameter_status")
    if not isinstance(status, str) or not status:
        raise ValueError("evaluation.parameter_status must be explicit")
    network = _mapping(config.get("network"), "network")
    if network.get("case_name") != "case24_ieee_rts":
        raise ValueError("runner supports only case24_ieee_rts")
    network_status = network.get("parameter_status")
    if not isinstance(network_status, str) or not network_status:
        raise ValueError("network.parameter_status must be explicit")
    methods = network.get("methods")
    if (
        not isinstance(methods, list)
        or not methods
        or any(not isinstance(method, str) for method in methods)
    ):
        raise ValueError("network.methods must be a nonempty list")
    if len(methods) != len(set(methods)):
        raise ValueError("network.methods must not contain duplicates")
    if set(methods) - set(NETWORK_GRID_NEED_METHODS):
        raise ValueError("network.methods contains an unknown method")
    poi_bus = _integer(network.get("poi_bus"), "network.poi_bus")
    balancing_bus = _integer(
        network.get("balancing_bus"), "network.balancing_bus"
    )
    branch_indices = _integer_tuple(
        network.get("branch_indices"), "network.branch_indices"
    )
    generator_indices = _integer_tuple(
        network.get("generator_indices"), "network.generator_indices"
    )
    redispatch_fraction = _number(
        network.get("redispatch_fraction_of_pmax"),
        "network.redispatch_fraction_of_pmax",
    )
    sustained_rating = network.get("sustained_rating")
    if not isinstance(sustained_rating, str) or not sustained_rating:
        raise ValueError("network.sustained_rating must be explicit")

    model = _mapping(config.get("model"), "model")
    solver_name = str(model.get("solver_name", ""))
    if not solver_name:
        raise ValueError("model.solver_name must be explicit")
    raw_scenarios = _raw_scenarios(config.get("scenarios"))
    envelope = _envelope(config.get("envelope"))
    coefficients = _coefficients(config.get("coefficients"))
    data = load_rts24()
    _validate_network_selection(
        data,
        poi_bus=poi_bus,
        balancing_bus=balancing_bus,
        branch_indices=branch_indices,
        generator_indices=generator_indices,
        sustained_rating=sustained_rating,
    )
    method_summaries = {}
    gate_passed = True
    for method in methods:
        scenarios, provenance = _derive_temporal_scenarios(
            data=data,
            raw_scenarios=raw_scenarios,
            method=method,
            poi_bus=poi_bus,
            balancing_bus=balancing_bus,
            branch_indices=branch_indices,
            generator_indices=generator_indices,
            redispatch_fraction_of_pmax=redispatch_fraction,
            sustained_rating=sustained_rating,
            solver_name=solver_name,
            parameter_status=f"{status}|{network_status}",
        )
        results = {}
        for label, joint in (("correct", True), ("b6", False)):
            results[label] = solve_temporal_economic_stochastic(
                TemporalEconomicInputs(
                    scenarios=scenarios,
                    envelope=envelope,
                    coefficients=coefficients,
                    provisioning_cost_per_mw=_number(
                        model.get("provisioning_cost_per_mw"),
                        "provisioning_cost_per_mw",
                    ),
                    max_flexibility_budget_mw=_number(
                        model.get("max_flexibility_budget_mw"),
                        "max_flexibility_budget_mw",
                    ),
                    lambda_risk=_number(
                        model.get("lambda_risk"), "lambda_risk"
                    ),
                    beta=_number(model.get("beta"), "beta"),
                    enforce_joint_budget=joint,
                    fixed_flexibility_mw=None,
                    parameter_status=f"{status}|{network_status}",
                ),
                solver_name=solver_name,
            )
        method_gate = results["correct"].feasible and results["b6"].feasible
        b6_physical_replay_passed = bool(results["b6"].scenario_dispatch) and all(
            dispatch.physical_envelope_feasible
            for dispatch in results["b6"].scenario_dispatch.values()
        )
        gate_passed = gate_passed and method_gate
        method_summaries[method] = {
            "gate_passed": method_gate,
            "solver_and_internal_audit_gate_passed": method_gate,
            "b6_physical_replay_passed": b6_physical_replay_passed,
            "derived_grid_need_mw": {
                scenario.name: list(scenario.grid_need_mw)
                for scenario in scenarios
            },
            "correct": _result_dict(results["correct"]),
            "b6": _result_dict(results["b6"]),
            "h1_b6_flexibility_underprovisioning_mw": (
                results["correct"].provisioned_flexibility_mw
                - results["b6"].provisioned_flexibility_mw
                if method_gate
                else None
            ),
            "network_provenance": provenance,
        }

    output = _mapping(config.get("output"), "output")
    summary_path = Path(str(output.get("summary_path")))
    if not summary_path.is_absolute():
        summary_path = _ROOT / summary_path
    effective_config = copy.deepcopy(config)
    effective_config["model"]["fixed_flexibility_mw"] = None
    summary = {
        "evaluation_id": evaluation.get("id"),
        "config_sha256": _sha256_bytes(config_bytes),
        "effective_config": effective_config,
        "methods": method_summaries,
        "gate_passed": gate_passed,
        "gate_definition": (
            "all_correct_and_b6_models_solved_and_passed_internal_constraints; "
            "expected_b6_physical_replay_failure_is_a_reported_finding_not_a_"
            "solver_gate_failure"
        ),
        "parameter_status": (
            f"{status}|{network_status}|derived_temporal_not_empirical_outage"
        ),
        "security_certified": False,
        "formal_economic_optimum_published": False,
        "interpretation": (
            "selected_n1_dc_event_magnitude_with_synthetic_event_timing_"
            "and_temporal_flexibility_recourse"
        ),
        "certification_blockers": [
            "network_event_timing_is_synthetic_not_empirical",
            "recovery_parameters_are_synthetic_not_observed",
            "selected_n1_dc_not_full_n1_or_ac",
        ],
        "output_paths": {"summary": str(summary_path)},
    }
    json_text = json.dumps(
        summary, ensure_ascii=False, allow_nan=False, sort_keys=True
    )
    summary = json.loads(json_text)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json_text + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            "configs/rq2_l5_economic_temporal_network_rts24.yaml"
        ),
    )
    args = parser.parse_args()
    summary = run(args.config)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not summary["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
