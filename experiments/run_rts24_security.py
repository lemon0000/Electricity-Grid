"""Run the evidence-aware RTS-24 M1 security audit."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from src.grid import (
    load_rts24,
    screen_generator_n_minus_one,
    screen_n_minus_one,
    solve_dc_opf,
    validate_ac_power_flow,
)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _optional(value: Any) -> Any:
    return "" if value is None else value


def _redispatch_limits(data: Any, fraction: float) -> dict[int, float]:
    return {
        generator.index: fraction * generator.p_max_mw
        for generator in data.generators
    }


def _branch_row(
    outcome: Any,
    *,
    stage: str,
    fraction: float | None,
    parameter_status: str,
) -> dict[str, Any]:
    result = outcome.result
    return {
        "stage": stage,
        "contingency_kind": "branch",
        "element_index": outcome.outaged_branch_index,
        "from_bus": outcome.from_bus,
        "to_bus": outcome.to_bus,
        "generator_bus": "",
        "redispatch_fraction_pmax": _optional(fraction),
        "parameter_status": parameter_status,
        "branch_rating": result.branch_rating,
        "feasible": result.feasible,
        "termination_condition": result.termination_condition,
        "topology_connected": len(result.reference_buses) == 1,
        "max_balance_residual_mw": _optional(result.max_balance_residual_mw),
        "max_loading_fraction": _optional(outcome.max_loading_fraction),
        "max_loaded_branch_index": _optional(outcome.max_loaded_branch_index),
        "max_redispatch_mw": _optional(outcome.max_redispatch_mw),
        "outaged_element_flow_or_generation_mw": _optional(
            result.branch_flows_mw.get(outcome.outaged_branch_index)
        ),
    }


def _generator_row(
    outcome: Any,
    *,
    fraction: float,
    parameter_status: str,
) -> dict[str, Any]:
    result = outcome.result
    return {
        "stage": "sustained_post_response",
        "contingency_kind": "generator",
        "element_index": outcome.outaged_generator_index,
        "from_bus": "",
        "to_bus": "",
        "generator_bus": outcome.bus,
        "redispatch_fraction_pmax": fraction,
        "parameter_status": parameter_status,
        "branch_rating": result.branch_rating,
        "feasible": result.feasible,
        "termination_condition": result.termination_condition,
        "topology_connected": True,
        "max_balance_residual_mw": _optional(result.max_balance_residual_mw),
        "max_loading_fraction": _optional(outcome.max_loading_fraction),
        "max_loaded_branch_index": _optional(outcome.max_loaded_branch_index),
        "max_redispatch_mw": _optional(outcome.max_redispatch_mw),
        "outaged_element_flow_or_generation_mw": _optional(
            result.generation_mw.get(outcome.outaged_generator_index)
        ),
    }


def _ac_row(label: str, result: Any, data: Any) -> dict[str, Any]:
    validation = validate_ac_power_flow(
        data,
        result,
        branch_rating=result.branch_rating,
    )
    return {"case": label, **asdict(validation)}


def run(config_path: Path) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["case"]["name"] != "case24_ieee_rts":
        raise ValueError("M1 currently supports only PYPOWER case24_ieee_rts")
    if config["redispatch"]["response_minutes"] is not None:
        raise ValueError("RTS-24 has no response-time data for this sensitivity")

    solver_name = config["solver"]["name"]
    sustained_rating = config["network"]["normal_and_sustained_rating"]
    immediate_rating = config["network"]["immediate_post_contingency_rating"]
    allow_islanding = bool(config["network"]["allow_unplanned_islanding"])
    fractions = tuple(float(value) for value in config["redispatch"]["fractions"])
    if not fractions or fractions != tuple(sorted(set(fractions))):
        raise ValueError("Redispatch fractions must be unique and increasing")
    if min(fractions) < 0.0 or max(fractions) > 1.0:
        raise ValueError("Redispatch fractions must lie between zero and one")

    parameter_status = config["redispatch"]["parameter_status"]
    output_directory = Path(config["output"]["directory"])
    prefix = config["output"]["prefix"]
    output_directory.mkdir(parents=True, exist_ok=True)

    data = load_rts24()
    base_result = solve_dc_opf(
        data,
        branch_rating=sustained_rating,
        solver_name=solver_name,
    )
    if not base_result.feasible:
        raise RuntimeError(f"Base DC-OPF failed: {base_result.termination_condition}")

    zero_limits = _redispatch_limits(data, 0.0)
    immediate_branches = screen_n_minus_one(
        data,
        branch_rating=immediate_rating,
        reference_generation_mw=base_result.generation_mw,
        redispatch_up_mw=zero_limits,
        redispatch_down_mw=zero_limits,
        allow_islanding=allow_islanding,
        solver_name=solver_name,
    )
    security_rows = [
        _branch_row(
            outcome,
            stage="immediate_post_contingency",
            fraction=0.0,
            parameter_status="rating_available_response_dynamics_not_modeled",
        )
        for outcome in immediate_branches
    ]

    sensitivity_summary = []
    upper_branch_outcomes = ()
    upper_generator_outcomes = ()
    for fraction in fractions:
        limits = _redispatch_limits(data, fraction)
        branch_outcomes = screen_n_minus_one(
            data,
            branch_rating=sustained_rating,
            reference_generation_mw=base_result.generation_mw,
            redispatch_up_mw=limits,
            redispatch_down_mw=limits,
            allow_islanding=allow_islanding,
            solver_name=solver_name,
        )
        generator_outcomes = screen_generator_n_minus_one(
            data,
            reference_generation_mw=base_result.generation_mw,
            redispatch_up_mw=limits,
            redispatch_down_mw=limits,
            branch_rating=sustained_rating,
            solver_name=solver_name,
        )
        security_rows.extend(
            _branch_row(
                outcome,
                stage="sustained_post_response",
                fraction=fraction,
                parameter_status=parameter_status,
            )
            for outcome in branch_outcomes
        )
        security_rows.extend(
            _generator_row(
                outcome,
                fraction=fraction,
                parameter_status=parameter_status,
            )
            for outcome in generator_outcomes
        )
        sensitivity_summary.append(
            {
                "redispatch_fraction_pmax": fraction,
                "branch_feasible": sum(item.result.feasible for item in branch_outcomes),
                "branch_checked": len(branch_outcomes),
                "generator_feasible": sum(
                    item.result.feasible for item in generator_outcomes
                ),
                "generator_checked": len(generator_outcomes),
            }
        )
        if fraction == max(fractions):
            upper_branch_outcomes = branch_outcomes
            upper_generator_outcomes = generator_outcomes

    _write_csv(output_directory / f"{prefix}_security_sensitivity.csv", security_rows)

    ac_rows = [_ac_row("base", base_result, data)]
    if config["ac_validation"]["enabled"]:
        worst_immediate = max(
            (item for item in immediate_branches if item.result.feasible),
            key=lambda item: item.max_loading_fraction,
        )
        worst_branch = max(
            (item for item in upper_branch_outcomes if item.result.feasible),
            key=lambda item: item.max_loading_fraction,
        )
        worst_generator = max(
            (item for item in upper_generator_outcomes if item.result.feasible),
            key=lambda item: item.max_loading_fraction,
        )
        ac_rows.extend(
            (
                _ac_row(
                    f"immediate_branch_{worst_immediate.outaged_branch_index}",
                    worst_immediate.result,
                    data,
                ),
                _ac_row(
                    f"sustained_branch_{worst_branch.outaged_branch_index}",
                    worst_branch.result,
                    data,
                ),
                _ac_row(
                    f"generator_{worst_generator.outaged_generator_index}",
                    worst_generator.result,
                    data,
                ),
            )
        )
    _write_csv(output_directory / f"{prefix}_ac_validation.csv", ac_rows)

    ramp_10_complete = all(
        generator.ramp_10_mw is not None
        for generator in data.generators
        if generator.in_service and generator.p_max_mw > 0.0
    )
    islanding_failures = sum(
        item.result.termination_condition == "islanding"
        for item in immediate_branches
    )
    ac_failures = sum(row["evaluated"] and not row["secure"] for row in ac_rows)
    failing_ac_cases = [
        row["case"] for row in ac_rows if row["evaluated"] and not row["secure"]
    ]
    certification_blockers = [
        "Generator response limits and response time are absent from the RTS-24 case",
        "The case is a single operating snapshot without chronological conditions",
    ]
    if islanding_failures:
        certification_blockers.append("Branch 10 (7-8) creates an unplanned island")
    if ac_failures:
        certification_blockers.append(
            "Representative AC checks failed: " + ", ".join(failing_ac_cases)
        )
    summary = {
        "case": config["case"]["name"],
        "source_package": data.source_package,
        "source_version": data.source_version,
        "base_objective": base_result.objective,
        "branch_ratings": {
            "normal_and_sustained": sustained_rating,
            "immediate_post_contingency": immediate_rating,
            "rate_b_retained_but_unmapped": True,
        },
        "ramp_10_data_complete": ramp_10_complete,
        "redispatch_parameter_status": parameter_status,
        "security_certified": False,
        "certification_blockers": certification_blockers,
        "generator_immediate_response_evaluated": False,
        "chronological_conditions_evaluated": False,
        "immediate_branch_checked": len(immediate_branches),
        "immediate_branch_feasible": sum(
            item.result.feasible for item in immediate_branches
        ),
        "unplanned_islanding_rejected": islanding_failures,
        "redispatch_sensitivity": sensitivity_summary,
        "ac_cases_evaluated": sum(row["evaluated"] for row in ac_rows),
        "ac_cases_secure": sum(row["secure"] for row in ac_rows),
        "ac_cases_failed": ac_failures,
    }
    (output_directory / f"{prefix}_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rts24_security.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
