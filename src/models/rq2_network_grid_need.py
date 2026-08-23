"""Bridge network-derived curtailment needs into the RQ2 L5 scenarios."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from math import isfinite

from pyomo.environ import SolverFactory

from ..grid.network_grid_need import (
    NETWORK_GRID_NEED_AUDIT_TOLERANCE_MW,
    NetworkGridNeedInputs,
    NetworkGridNeedResult,
    derive_network_grid_need,
)
from ..grid.rts24 import Rts24Data
from .economic_stochastic import EconomicScenario


@dataclass(frozen=True)
class NetworkEconomicScenarioSpec:
    name: str
    probability: float
    system_load_multiplier: float
    data_center_demand_mw: float
    green_call_mw: float
    connected_demand_mw: float
    hours: float


@dataclass(frozen=True)
class NetworkDerivedEconomicScenarios:
    feasible: bool
    scenarios: tuple[EconomicScenario, ...]
    grid_need_results: dict[str, NetworkGridNeedResult]
    parameter_status: str
    security_certified: bool
    provenance: dict[str, object]


def _finite_nonnegative(name: str, raw: object) -> float:
    if isinstance(raw, bool):
        raise TypeError(f"{name} must be numeric")
    try:
        number = float(raw)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be numeric") from error
    if not isfinite(number) or number < 0.0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return number


def _network_data_sha256(data: Rts24Data) -> str:
    payload = json.dumps(
        asdict(data),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _solver_version(solver_name: str) -> str:
    solver = SolverFactory(solver_name)
    if not solver.available(exception_flag=False):
        raise RuntimeError(f"Solver '{solver_name}' is not available")
    raw = solver.version()
    if isinstance(raw, tuple):
        return ".".join(str(part) for part in raw)
    return str(raw)


def build_network_derived_economic_scenarios(
    *,
    data: Rts24Data,
    scenario_specs: tuple[NetworkEconomicScenarioSpec, ...],
    poi_bus: int,
    balancing_bus: int,
    branch_indices: tuple[int, ...],
    generator_indices: tuple[int, ...],
    redispatch_fraction_of_pmax: float,
    sustained_rating: str,
    method: str,
    solver_name: str,
    parameter_status: str,
    tee: bool = False,
) -> NetworkDerivedEconomicScenarios:
    """Replace hand-entered ``grid_need_mw`` with a DC N-1 derivation."""

    if not scenario_specs:
        raise ValueError("At least one network economic scenario is required")
    if not parameter_status:
        raise ValueError("parameter_status must be explicit")
    names = [spec.name for spec in scenario_specs]
    if any(not name for name in names) or len(set(names)) != len(names):
        raise ValueError("Scenario names must be nonempty and unique")

    results: dict[str, NetworkGridNeedResult] = {}
    scenarios: list[EconomicScenario] = []
    for spec in scenario_specs:
        _finite_nonnegative(f"{spec.name}.probability", spec.probability)
        _finite_nonnegative(
            f"{spec.name}.system_load_multiplier", spec.system_load_multiplier
        )
        _finite_nonnegative(
            f"{spec.name}.data_center_demand_mw", spec.data_center_demand_mw
        )
        _finite_nonnegative(f"{spec.name}.green_call_mw", spec.green_call_mw)
        _finite_nonnegative(
            f"{spec.name}.connected_demand_mw", spec.connected_demand_mw
        )
        hours = _finite_nonnegative(f"{spec.name}.hours", spec.hours)
        if spec.probability <= 0.0:
            raise ValueError("Scenario probabilities must be strictly positive")
        if hours <= 0.0:
            raise ValueError("Scenario hours must be strictly positive")
        if (
            abs(spec.connected_demand_mw - spec.data_center_demand_mw)
            > NETWORK_GRID_NEED_AUDIT_TOLERANCE_MW
        ):
            raise ValueError(
                f"{spec.name}.connected_demand_mw must equal "
                "data_center_demand_mw for the single-POI network bridge"
            )

        result = derive_network_grid_need(
            NetworkGridNeedInputs(
                data=data,
                poi_bus=poi_bus,
                balancing_bus=balancing_bus,
                system_load_multiplier=spec.system_load_multiplier,
                data_center_demand_mw=spec.data_center_demand_mw,
                branch_indices=branch_indices,
                generator_indices=generator_indices,
                redispatch_fraction_of_pmax=redispatch_fraction_of_pmax,
                sustained_rating=sustained_rating,
                method=method,
                parameter_status=parameter_status,
                solver_name=solver_name,
                tee=tee,
            )
        )
        results[spec.name] = result
        if result.feasible:
            scenarios.append(
                EconomicScenario(
                    name=spec.name,
                    probability=spec.probability,
                    grid_need_mw=float(result.grid_need_mw),
                    green_call_mw=spec.green_call_mw,
                    connected_demand_mw=spec.connected_demand_mw,
                    hours=spec.hours,
                )
            )

    feasible = all(result.feasible for result in results.values())
    status_values = sorted({result.parameter_status for result in results.values()})
    combined_status = "|".join(status_values)
    provenance = {
        "schema": "rq2_network_grid_need_provenance_v1",
        "method": method,
        "poi_bus": poi_bus,
        "balancing_bus": balancing_bus,
        "selected_branch_indices": list(branch_indices),
        "selected_generator_indices": list(generator_indices),
        "selected_state_count": len(branch_indices) + len(generator_indices),
        "redispatch_fraction_of_pmax": redispatch_fraction_of_pmax,
        "sustained_rating": sustained_rating,
        "base_dispatch_policy": (
            "least_cost_normal_dc_opf_with_full_data_center_load"
        ),
        "state_aggregation": "maximum_state_required_curtailment_mw",
        "definition_a": (
            "statewise_minimum_poi_curtailment_with_hard_dc_thermal_limits"
        ),
        "definition_b": (
            "statewise_outage_topology_poi_ptdf_thermal_relief_estimate"
        ),
        "scenario_grid_need_mw": {
            name: result.grid_need_mw for name, result in results.items()
        },
        "scenario_critical_state": {
            name: result.critical_state for name, result in results.items()
        },
        "scenario_results": {
            name: asdict(result) for name, result in results.items()
        },
        "scenario_inputs": [asdict(spec) for spec in scenario_specs],
        "network_source_package": data.source_package,
        "network_source_version": data.source_version,
        "network_data_sha256": _network_data_sha256(data),
        "solver_name": solver_name,
        "solver_version": _solver_version(solver_name),
        "solution_audit_tolerance_mw": NETWORK_GRID_NEED_AUDIT_TOLERANCE_MW,
        "parameter_status": combined_status,
        "security_certified": False,
        "probability_status": "scenario_weights_not_empirical_outage_probability",
    }
    return NetworkDerivedEconomicScenarios(
        feasible=feasible,
        scenarios=tuple(scenarios) if feasible else (),
        grid_need_results=results,
        parameter_status=combined_status,
        security_certified=False,
        provenance=provenance,
    )
