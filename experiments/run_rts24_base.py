"""Run the L0 RTS-24 base DC-OPF and all configured N-1 outages."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import yaml

from src.grid import load_rts24, screen_n_minus_one, solve_dc_opf


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _optional_number(value: float | None) -> float | str:
    return "" if value is None else value


def run(config_path: Path) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["case"]["name"] != "case24_ieee_rts":
        raise ValueError("L0 currently supports only PYPOWER case24_ieee_rts")
    if config["network"]["contingency_rating"] != "rate_a":
        raise ValueError("L0 currently supports RATE_A for all network states")
    if config["contingencies"]["redispatch"] != "independent_within_unit_bounds":
        raise ValueError("Unsupported contingency redispatch mode")

    solver_name = config["solver"]["name"]
    tolerance_mw = float(config["validation"]["tolerance_mw"])
    output_directory = Path(config["output"]["directory"])
    prefix = str(config["output"]["prefix"])
    output_directory.mkdir(parents=True, exist_ok=True)

    data = load_rts24()
    base_result = solve_dc_opf(data, solver_name=solver_name)
    if not base_result.feasible:
        raise RuntimeError(
            f"Base DC-OPF failed: {base_result.termination_condition}"
        )
    if base_result.max_balance_residual_mw > tolerance_mw:
        raise RuntimeError("Base DC-OPF violates the power-balance tolerance")

    branch_selection = config["contingencies"]["branches"]
    selected_branches = None if branch_selection == "all_active" else branch_selection
    outcomes = screen_n_minus_one(
        data,
        branch_indices=selected_branches,
        branch_rating=config["network"]["contingency_rating"],
        allow_islanding=config["network"]["allow_unplanned_islanding"],
        solver_name=solver_name,
    )

    generator_rows = []
    for generator in data.generators:
        generator_rows.append(
            {
                "generator_index": generator.index,
                "bus": generator.bus,
                "generation_mw": base_result.generation_mw[generator.index],
                "p_min_mw": generator.p_min_mw,
                "p_max_mw": generator.p_max_mw,
            }
        )
    _write_csv(
        output_directory / f"{prefix}_generators.csv",
        list(generator_rows[0]),
        generator_rows,
    )

    branch_rows = []
    for branch in data.branches:
        flow = base_result.branch_flows_mw[branch.index]
        branch_rows.append(
            {
                "branch_index": branch.index,
                "from_bus": branch.from_bus,
                "to_bus": branch.to_bus,
                "flow_mw": flow,
                "rate_a_mw": branch.rate_a_mw,
                "loading_fraction": abs(flow) / branch.rate_a_mw,
            }
        )
    _write_csv(
        output_directory / f"{prefix}_branches.csv",
        list(branch_rows[0]),
        branch_rows,
    )

    contingency_rows = []
    branch_by_index = {branch.index: branch for branch in data.branches}
    for outcome in outcomes:
        result = outcome.result
        max_loaded_branch = (
            branch_by_index[outcome.max_loaded_branch_index]
            if outcome.max_loaded_branch_index is not None
            else None
        )
        contingency_rows.append(
            {
                "outaged_branch_index": outcome.outaged_branch_index,
                "from_bus": outcome.from_bus,
                "to_bus": outcome.to_bus,
                "feasible": result.feasible,
                "termination_condition": result.termination_condition,
                "connected_components": len(result.reference_buses),
                "topology_connected": len(result.reference_buses) == 1,
                "objective": _optional_number(result.objective),
                "max_balance_residual_mw": _optional_number(
                    result.max_balance_residual_mw
                ),
                "max_loading_fraction": _optional_number(
                    outcome.max_loading_fraction
                ),
                "max_loaded_branch_index": _optional_number(
                    outcome.max_loaded_branch_index
                ),
                "max_loaded_from_bus": (
                    "" if max_loaded_branch is None else max_loaded_branch.from_bus
                ),
                "max_loaded_to_bus": (
                    "" if max_loaded_branch is None else max_loaded_branch.to_bus
                ),
                "outaged_branch_flow_mw": _optional_number(
                    result.branch_flows_mw.get(outcome.outaged_branch_index)
                ),
            }
        )
    _write_csv(
        output_directory / f"{prefix}_n_minus_one.csv",
        list(contingency_rows[0]),
        contingency_rows,
    )

    maximum_base_loading = max(row["loading_fraction"] for row in branch_rows)
    summary = {
        "case": config["case"]["name"],
        "source_package": data.source_package,
        "source_version": data.source_version,
        "solver": solver_name,
        "base_feasible": base_result.feasible,
        "base_objective": base_result.objective,
        "base_generation_mw": sum(base_result.generation_mw.values()),
        "base_demand_mw": data.total_demand_mw,
        "base_max_balance_residual_mw": base_result.max_balance_residual_mw,
        "base_max_loading_fraction": maximum_base_loading,
        "contingencies_checked": len(outcomes),
        "contingencies_feasible": sum(outcome.result.feasible for outcome in outcomes),
        "contingencies_islanding": sum(
            len(outcome.result.reference_buses) > 1 for outcome in outcomes
        ),
        "contingencies_topology_rejected": sum(
            outcome.result.termination_condition == "islanding"
            for outcome in outcomes
        ),
        "contingency_max_loading_fraction": max(
            outcome.max_loading_fraction
            for outcome in outcomes
            if outcome.max_loading_fraction is not None
        ),
        "contingency_redispatch": config["contingencies"]["redispatch"],
        "contingency_parameter_status": config["contingencies"][
            "parameter_status"
        ],
        "contingency_rating": config["network"]["contingency_rating"],
    }
    summary_path = output_directory / f"{prefix}_summary.json"
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
        default=Path("configs/rts24_base.yaml"),
    )
    args = parser.parse_args()
    summary = run(args.config)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
