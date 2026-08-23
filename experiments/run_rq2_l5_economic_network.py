"""Run RQ2 L5 with RTS-24-derived hard ``grid_need_mw`` values.

The runner derives every scenario's network need under both registered
definitions, then delegates the unchanged shared-budget/CVaR optimization to
``run_rq2_l5_economic_stochastic``. It publishes derived DC sensitivity
evidence only and can never set ``security_certified``.
"""

from __future__ import annotations

import argparse
import copy
import json
import tempfile
from math import isfinite
from pathlib import Path

import yaml

from experiments import run_rq2_l5_economic_stochastic as l5_runner
from src.grid import load_rts24
from src.grid.network_grid_need import (
    METHOD_MINIMUM_CURTAILMENT,
    METHOD_OVERLOAD_SENSITIVITY,
    NETWORK_GRID_NEED_METHODS,
)
from src.models.rq2_network_grid_need import (
    NetworkEconomicScenarioSpec,
    build_network_derived_economic_scenarios,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _resolve_path(raw: object) -> Path:
    path = Path(str(raw))
    return path if path.is_absolute() else _REPOSITORY_ROOT / path


def _mapping(raw: object, label: str) -> dict:
    if not isinstance(raw, dict):
        raise TypeError(f"{label} must be a mapping")
    return raw


def _number(raw: object, label: str, *, nonnegative: bool = False) -> float:
    if isinstance(raw, bool):
        raise TypeError(f"{label} must be numeric")
    try:
        number = float(raw)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not isfinite(number):
        raise ValueError(f"{label} must be finite")
    if nonnegative and number < 0.0:
        raise ValueError(f"{label} must be nonnegative")
    return number


def _integer_tuple(raw: object, label: str) -> tuple[int, ...]:
    if not isinstance(raw, list):
        raise TypeError(f"{label} must be a list")
    if any(isinstance(item, bool) for item in raw):
        raise ValueError(f"{label} must contain integers, not booleans")
    values = tuple(int(item) for item in raw)
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must not contain duplicates")
    return values


def _scenario_specs(raw: object) -> tuple[NetworkEconomicScenarioSpec, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("scenarios must be a nonempty list")
    specs = []
    for index, item in enumerate(raw):
        row = _mapping(item, f"scenarios[{index}]")
        if "grid_need_mw" in row:
            raise ValueError(
                "Network runner forbids hand-entered grid_need_mw; it is derived"
            )
        name = row.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"scenarios[{index}].name must be nonempty")
        specs.append(
            NetworkEconomicScenarioSpec(
                name=name,
                probability=_number(row.get("probability"), f"{name}.probability"),
                system_load_multiplier=_number(
                    row.get("system_load_multiplier"),
                    f"{name}.system_load_multiplier",
                    nonnegative=True,
                ),
                data_center_demand_mw=_number(
                    row.get("data_center_demand_mw"),
                    f"{name}.data_center_demand_mw",
                    nonnegative=True,
                ),
                green_call_mw=_number(
                    row.get("green_call_mw"),
                    f"{name}.green_call_mw",
                    nonnegative=True,
                ),
                connected_demand_mw=_number(
                    row.get("connected_demand_mw"),
                    f"{name}.connected_demand_mw",
                    nonnegative=True,
                ),
                hours=_number(row.get("hours"), f"{name}.hours", nonnegative=True),
            )
        )
    return tuple(specs)


def run(config_path: Path) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config = _mapping(config, "config")
    evaluation = _mapping(config.get("evaluation"), "evaluation")
    if evaluation.get("security_certified") is not False:
        raise ValueError("evaluation.security_certified must remain false")
    if evaluation.get("formal_economic_optimum_published", False) is not False:
        raise ValueError("formal_economic_optimum_published must remain false")
    status = evaluation.get("parameter_status")
    if not isinstance(status, str) or not status:
        raise ValueError("evaluation.parameter_status must be explicit")

    network = _mapping(config.get("network"), "network")
    if network.get("case_name") != "case24_ieee_rts":
        raise ValueError("Network RQ2 runner supports only case24_ieee_rts")
    network_status = network.get("parameter_status")
    if not isinstance(network_status, str) or not network_status:
        raise ValueError("network.parameter_status must be explicit")
    methods_raw = network.get("methods")
    if not isinstance(methods_raw, list) or not methods_raw:
        raise ValueError("network.methods must be a nonempty list")
    methods = tuple(str(method) for method in methods_raw)
    if len(methods) != len(set(methods)):
        raise ValueError("network.methods must not contain duplicates")
    unknown_methods = set(methods) - set(NETWORK_GRID_NEED_METHODS)
    if unknown_methods:
        raise ValueError(f"Unknown network methods: {sorted(unknown_methods)}")

    poi_bus = int(network.get("poi_bus"))
    balancing_bus = int(network.get("balancing_bus"))
    branch_indices = _integer_tuple(
        network.get("branch_indices"), "network.branch_indices"
    )
    generator_indices = _integer_tuple(
        network.get("generator_indices"), "network.generator_indices"
    )
    redispatch_fraction = _number(
        network.get("redispatch_fraction_of_pmax"),
        "network.redispatch_fraction_of_pmax",
        nonnegative=True,
    )
    sustained_rating = network.get("sustained_rating")
    if not isinstance(sustained_rating, str) or not sustained_rating:
        raise ValueError("network.sustained_rating must be explicit")

    model = _mapping(config.get("model"), "model")
    solver_name = model.get("solver_name")
    if not isinstance(solver_name, str) or not solver_name:
        raise ValueError("model.solver_name must be explicit")
    specs = _scenario_specs(config.get("scenarios"))
    output = _mapping(config.get("output"), "output")
    output_root = _resolve_path(output.get("root"))
    summary_path = _resolve_path(output.get("summary_path"))

    data = load_rts24()
    method_summaries: dict[str, object] = {}
    network_provenance: dict[str, object] = {}
    all_passed = True

    for method in methods:
        built = build_network_derived_economic_scenarios(
            data=data,
            scenario_specs=specs,
            poi_bus=poi_bus,
            balancing_bus=balancing_bus,
            branch_indices=branch_indices,
            generator_indices=generator_indices,
            redispatch_fraction_of_pmax=redispatch_fraction,
            sustained_rating=sustained_rating,
            method=method,
            solver_name=solver_name,
            parameter_status=f"{status}|{network_status}",
        )
        network_provenance[method] = built.provenance
        if not built.feasible:
            method_summaries[method] = {
                "gate_passed": False,
                "network_derivation_feasible": False,
                "security_certified": False,
            }
            all_passed = False
            continue

        effective = copy.deepcopy(config)
        effective.pop("network", None)
        effective["evaluation"]["id"] = (
            f"{evaluation.get('id')}__{method}"
        )
        effective["evaluation"]["parameter_status"] = built.parameter_status
        effective["scenarios"] = [
            {
                "name": scenario.name,
                "probability": scenario.probability,
                "grid_need_mw": scenario.grid_need_mw,
                "green_call_mw": scenario.green_call_mw,
                "connected_demand_mw": scenario.connected_demand_mw,
                "hours": scenario.hours,
            }
            for scenario in built.scenarios
        ]
        method_root = output_root / method
        effective["output"] = {
            "runs_path": str(method_root / "runs.csv"),
            "frontier_path": str(method_root / "frontier.csv"),
            "summary_path": str(method_root / "summary.json"),
        }
        with tempfile.TemporaryDirectory(prefix="rq2_network_") as temporary:
            effective_path = Path(temporary) / "effective.yaml"
            effective_path.write_text(
                yaml.safe_dump(effective, sort_keys=False), encoding="utf-8"
            )
            method_summary = l5_runner.run(effective_path)
        method_summary["network_grid_need_method"] = method
        method_summary["network_grid_need_provenance"] = built.provenance
        method_summary["security_certified"] = False
        method_summary_path = method_root / "summary.json"
        method_summary_path.write_text(
            json.dumps(
                method_summary, ensure_ascii=False, allow_nan=False, indent=2
            )
            + "\n",
            encoding="utf-8",
        )
        method_summaries[method] = method_summary
        all_passed = all_passed and bool(method_summary["gate_passed"])

    scenario_comparison = {}
    if set(methods) == set(NETWORK_GRID_NEED_METHODS):
        primary = network_provenance[NETWORK_GRID_NEED_METHODS[0]][
            "scenario_grid_need_mw"
        ]
        comparator = network_provenance[NETWORK_GRID_NEED_METHODS[1]][
            "scenario_grid_need_mw"
        ]
        scenario_comparison = {
            name: {
                METHOD_MINIMUM_CURTAILMENT: primary[name],
                METHOD_OVERLOAD_SENSITIVITY: comparator[name],
                "difference_mw": comparator[name] - primary[name],
            }
            for name in primary
            if primary[name] is not None and comparator[name] is not None
        }

    summary = {
        "evaluation_id": evaluation.get("id"),
        "methods": list(methods),
        "method_summaries": method_summaries,
        "network_provenance": network_provenance,
        "scenario_method_comparison": scenario_comparison,
        "gate_passed": all_passed,
        "parameter_status": (
            f"{status}|{network_status}|derived|not_empirical_outage"
        ),
        "security_certified": False,
        "formal_economic_optimum_published": False,
        "formal_vma_published": False,
        "interpretation": (
            "selected_sustained_n1_dc_derived_grid_need_sensitivity_"
            "not_full_n1_not_ac_not_engineering_certification"
        ),
        "certification_blockers": [
            "selected_sustained_n1_dc_only",
            "overload_sensitivity_is_a_diagnostic_approximation",
            "no_ac_voltage_reactive_or_engineering_equipment_validation",
            "scenario_probabilities_not_empirical_outage_probabilities",
        ],
        "output_paths": {
            "root": str(output_root),
            "summary": str(summary_path),
        },
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rq2_l5_economic_network_rts24.yaml"),
    )
    args = parser.parse_args()
    summary = run(args.config)
    print(json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2))
    if not summary["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
