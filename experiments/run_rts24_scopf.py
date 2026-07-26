"""Run joint RTS-24 SCOPF sensitivities and full-state AC restoration."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import yaml

from src.grid import (
    load_rts24,
    non_islanding_branch_indices,
    restore_ac_feasibility,
    solve_security_constrained_dc_opf,
)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _limits(data: Any, fraction: float) -> dict[int, float]:
    return {
        generator.index: fraction * generator.p_max_mw
        for generator in data.generators
    }


def _state_metrics(data: Any, state: Any, result: Any, base: Any) -> dict[str, Any]:
    active_branches = (
        branch
        for branch in data.branches
        if branch.in_service and branch.index not in state.outaged_branch_indices
    )
    max_loaded = max(
        active_branches,
        key=lambda branch: abs(result.branch_flows_mw[branch.index])
        / branch.rating_mw(result.branch_rating),
    )
    redispatch = [
        abs(result.generation_mw[generator.index] - base.generation_mw[generator.index])
        for generator in data.generators
        if generator.index not in state.outaged_generator_indices
    ]
    return {
        "state": state.name,
        "kind": state.kind,
        "element_index": "" if state.element_index is None else state.element_index,
        "response_mode": state.response_mode,
        "branch_rating": state.branch_rating,
        "objective": result.objective,
        "max_balance_residual_mw": result.max_balance_residual_mw,
        "max_loading_fraction": (
            abs(result.branch_flows_mw[max_loaded.index])
            / max_loaded.rating_mw(result.branch_rating)
        ),
        "max_loaded_branch_index": max_loaded.index,
        "max_redispatch_mw": max(redispatch),
        "outaged_branch_flow_mw": (
            ""
            if not state.outaged_branch_indices
            else result.branch_flows_mw[next(iter(state.outaged_branch_indices))]
        ),
        "outaged_generator_mw": (
            ""
            if not state.outaged_generator_indices
            else result.generation_mw[next(iter(state.outaged_generator_indices))]
        ),
    }


def _ac_row(state: Any, result: Any, restored: Any) -> dict[str, Any]:
    return {
        "state": state.name,
        "kind": state.kind,
        "element_index": "" if state.element_index is None else state.element_index,
        "response_mode": state.response_mode,
        "branch_rating": restored.branch_rating,
        "evaluated": restored.evaluated,
        "converged": restored.converged,
        "secure": restored.secure,
        "status": restored.status,
        "max_voltage_violation_pu": (
            ""
            if restored.max_voltage_violation_pu is None
            else restored.max_voltage_violation_pu
        ),
        "min_voltage_pu": (
            "" if not restored.bus_voltage_pu else min(restored.bus_voltage_pu.values())
        ),
        "max_branch_loading_fraction": (
            ""
            if restored.max_branch_loading_fraction is None
            else restored.max_branch_loading_fraction
        ),
        "max_loaded_branch_index": (
            ""
            if restored.max_loaded_branch_index is None
            else restored.max_loaded_branch_index
        ),
        "max_active_power_violation_mw": (
            ""
            if restored.max_active_power_violation_mw is None
            else restored.max_active_power_violation_mw
        ),
        "max_reactive_power_violation_mvar": (
            ""
            if restored.max_reactive_power_violation_mvar is None
            else restored.max_reactive_power_violation_mvar
        ),
        "max_target_deviation_mw": (
            ""
            if restored.max_target_deviation_mw is None
            else restored.max_target_deviation_mw
        ),
        "max_reference_redispatch_mw": (
            ""
            if restored.max_reference_redispatch_mw is None
            else restored.max_reference_redispatch_mw
        ),
        "total_up_redispatch_mw": (
            ""
            if restored.total_up_redispatch_mw is None
            else restored.total_up_redispatch_mw
        ),
        "total_down_redispatch_mw": (
            ""
            if restored.total_down_redispatch_mw is None
            else restored.total_down_redispatch_mw
        ),
        "ac_losses_mw": "" if restored.ac_losses_mw is None else restored.ac_losses_mw,
        "minimum_deviation_solved": restored.minimum_deviation_solved,
        "economic_seed_used": restored.fallback_seed_used,
        "dc_max_balance_residual_mw": result.max_balance_residual_mw,
    }


def run(config_path: Path) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["case"]["name"] != "case24_ieee_rts":
        raise ValueError("Joint SCOPF currently supports only case24_ieee_rts")
    if config["security"]["branch_set"] != "all_non_islanding":
        raise ValueError("Unsupported SCOPF branch set")
    if config["security"]["generator_set"] != "all_positive_capacity":
        raise ValueError("Unsupported SCOPF generator set")
    if config["redispatch"]["response_minutes"] is not None:
        raise ValueError("RTS-24 response time is unavailable and must remain unset")

    data = load_rts24()
    solver_name = config["solver"]["name"]
    fractions = tuple(float(value) for value in config["redispatch"]["fractions"])
    if fractions != tuple(sorted(set(fractions))) or not fractions:
        raise ValueError("Redispatch fractions must be unique and increasing")
    immediate_rating = config["security"]["immediate_branch_rating"]
    sustained_rating = config["security"]["sustained_rating"]
    cost_breakpoints = int(config["objective"]["cost_breakpoints"])
    output_directory = Path(config["output"]["directory"])
    prefix = config["output"]["prefix"]
    output_directory.mkdir(parents=True, exist_ok=True)

    sensitivity_rows = []
    state_rows = []
    feasible_results = {}
    for fraction in fractions:
        limits = _limits(data, fraction)
        result = solve_security_constrained_dc_opf(
            data,
            redispatch_up_mw=limits,
            redispatch_down_mw=limits,
            immediate_rating=immediate_rating,
            sustained_rating=sustained_rating,
            cost_breakpoints=cost_breakpoints,
            solver_name=solver_name,
        )
        sensitivity_rows.append(
            {
                "redispatch_fraction_pmax": fraction,
                "feasible": result.feasible,
                "termination_condition": result.termination_condition,
                "solver_status": result.solver_status,
                "base_objective": "" if result.objective is None else result.objective,
                "joint_states": len(result.states),
                "excluded_branch_indices": ";".join(
                    str(index) for index in result.excluded_branch_indices
                ),
                "parameter_status": config["redispatch"]["parameter_status"],
            }
        )
        if not result.feasible:
            continue
        feasible_results[fraction] = result
        for state in result.states:
            state_rows.append(
                {
                    "redispatch_fraction_pmax": fraction,
                    **_state_metrics(
                        data,
                        state,
                        result.state_results[state.name],
                        result.base_result,
                    ),
                }
            )

    _write_csv(output_directory / f"{prefix}_sensitivity.csv", sensitivity_rows)
    _write_csv(output_directory / f"{prefix}_states.csv", state_rows)

    ac_rows = []
    ac_summaries = []
    remedial_config = config["provisional_remedial_actions"]
    remedial_actions = {
        int(name.removeprefix("branch_")): values
        for name, values in remedial_config.items()
        if name.startswith("branch_")
    }
    for ac_fraction_value in config["ac_restoration"][
        "redispatch_fractions_pmax"
    ]:
        ac_fraction = float(ac_fraction_value)
        if ac_fraction not in feasible_results:
            raise RuntimeError(
                f"Configured AC fraction {ac_fraction} lacks a feasible joint SCOPF"
            )
        ac_scopf = feasible_results[ac_fraction]
        ac_limits = _limits(data, ac_fraction)
        base_ac = restore_ac_feasibility(data, ac_scopf.base_result)
        if not base_ac.secure:
            raise RuntimeError("Normal-state AC restoration failed")

        fraction_rows = []
        for state in ac_scopf.states:
            dc_state = ac_scopf.state_results[state.name]
            target = {
                generator.index: (
                    0.0
                    if generator.index in state.outaged_generator_indices
                    else base_ac.generation_mw[generator.index]
                    + dc_state.generation_mw[generator.index]
                    - ac_scopf.base_result.generation_mw[generator.index]
                )
                for generator in data.generators
            }
            restored = (
                base_ac
                if state.kind == "base"
                else restore_ac_feasibility(
                    data,
                    dc_state,
                    target_generation_mw=target,
                    reference_generation_mw=base_ac.generation_mw,
                    redispatch_up_mw=ac_limits,
                    redispatch_down_mw=ac_limits,
                )
            )
            action = (
                remedial_actions.get(state.element_index)
                if state.kind == "branch"
                else None
            )
            remediated = restored
            if action and not restored.secure:
                remediated = restore_ac_feasibility(
                    data,
                    dc_state,
                    target_generation_mw=target,
                    reference_generation_mw=base_ac.generation_mw,
                    redispatch_up_mw=ac_limits,
                    redispatch_down_mw=ac_limits,
                    corrective_open_branch_indices=action.get(
                        "corrective_open_branch_indices", ()
                    ),
                    shunt_injections_mvar=action.get("shunt_injections_mvar"),
                    branch_rating_overrides_mva=action.get(
                        "branch_rating_overrides_mva"
                    ),
                )
            row = {
                "redispatch_fraction_pmax": ac_fraction,
                **_ac_row(state, dc_state, restored),
                "remedial_action": "" if not action else json.dumps(action),
                "remedial_parameter_status": (
                    "" if not action else remedial_config["parameter_status"]
                ),
                "post_remediation_secure": remediated.secure,
                "post_remediation_status": remediated.status,
                "post_remediation_min_voltage_pu": (
                    ""
                    if not remediated.bus_voltage_pu
                    else min(remediated.bus_voltage_pu.values())
                ),
                "post_remediation_max_loading_fraction": (
                    ""
                    if remediated.max_branch_loading_fraction is None
                    else remediated.max_branch_loading_fraction
                ),
            }
            fraction_rows.append(row)
            ac_rows.append(row)
        raw_failed = [row["state"] for row in fraction_rows if not row["secure"]]
        post_failed = [
            row["state"]
            for row in fraction_rows
            if not row["post_remediation_secure"]
        ]
        ac_summaries.append(
            {
                "redispatch_fraction_pmax": ac_fraction,
                "base_losses_mw": base_ac.ac_losses_mw,
                "states_checked": len(fraction_rows),
                "raw_states_secure": len(fraction_rows) - len(raw_failed),
                "raw_failed_states": raw_failed,
                "post_remediation_states_secure": len(fraction_rows)
                - len(post_failed),
                "post_remediation_failed_states": post_failed,
            }
        )
    _write_csv(output_directory / f"{prefix}_ac_full.csv", ac_rows)

    failed_ac_states = [
        f"{row['redispatch_fraction_pmax']}:{row['state']}"
        for row in ac_rows
        if not row["post_remediation_secure"]
    ]
    non_islanding = non_islanding_branch_indices(data)
    excluded = tuple(
        branch.index
        for branch in data.branches
        if branch.in_service and branch.index not in non_islanding
    )
    summary = {
        "case": config["case"]["name"],
        "source_package": data.source_package,
        "source_version": data.source_version,
        "joint_state_count": len(next(iter(feasible_results.values())).states),
        "main_branch_contingencies": len(non_islanding),
        "generator_contingencies": sum(
            generator.in_service and generator.p_max_mw > 0.0
            for generator in data.generators
        ),
        "excluded_islanding_branches": list(excluded),
        "excluded_islanding_policy": config["security"][
            "excluded_islanding_policy"
        ],
        "redispatch_parameter_status": config["redispatch"]["parameter_status"],
        "scopf_sensitivity": sensitivity_rows,
        "ac_restoration": ac_summaries,
        "ac_states_checked": len(ac_rows),
        "ac_states_secure_before_remediation": sum(row["secure"] for row in ac_rows),
        "ac_states_secure_after_remediation": sum(
            row["post_remediation_secure"] for row in ac_rows
        ),
        "ac_states_failed": len(failed_ac_states),
        "ac_failed_states": failed_ac_states,
        "security_certified": False,
        "certification_blockers": [
            "Redispatch limits are synthetic sensitivities without response-time evidence",
            "Branch 10 (7-8) is an unresolved unplanned-islanding contingency",
            "Chronological load and renewable conditions are not yet included",
            *(
                ["Some joint states could not be restored to AC feasibility"]
                if failed_ac_states
                else []
            ),
        ],
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
        default=Path("configs/rts24_scopf.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
