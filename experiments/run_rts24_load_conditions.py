"""Audit joint RTS-24 security across RTS-GMLC Area 1 load conditions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime
from math import isclose, isfinite
from pathlib import Path

import yaml

from src.grid import (
    RTS_GMLC_MANIFEST_SHA256,
    load_rts24,
    load_rts24_area1_load_multipliers,
    non_islanding_branch_indices,
    restore_ac_feasibility,
    scale_rts24_demand,
    solve_dc_opf,
    solve_security_constrained_dc_opf,
    validate_rts_gmlc_source_identity,
    verify_sha256_manifest,
)

_QUANTILE_PROBABILITIES = {
    "minimum": 0.0,
    "median": 0.5,
    "p95": 0.95,
    "maximum": 1.0,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _select_load_conditions(
    hourly: tuple[tuple[datetime, float], ...],
) -> dict[str, tuple[datetime, float]]:
    """Select observed hours using the lower order statistic."""

    if not hourly:
        raise ValueError("RTS-GMLC hourly load series is empty")
    sorted_hours = sorted(hourly, key=lambda item: item[1])
    return {
        name: sorted_hours[int(probability * (len(sorted_hours) - 1))]
        for name, probability in _QUANTILE_PROBABILITIES.items()
    }


def _diagnosis(
    *,
    demand_mw: float,
    online_pmin_mw: float,
    online_pmax_mw: float,
    commitment_model: str,
    base_feasible: bool,
    scopf_feasible: bool,
) -> str:
    if commitment_model == "fixed_online" and demand_mw < online_pmin_mw - 1.0e-6:
        return "demand_below_fixed_online_pmin_requires_commitment"
    if demand_mw > online_pmax_mw + 1.0e-6:
        return "demand_above_online_pmax"
    if not base_feasible:
        return "base_dc_opf_infeasible"
    if not scopf_feasible:
        return "security_constraints_infeasible_under_synthetic_response"
    return ""


def run(config_path: Path) -> list[dict[str, object]]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    source = config["source"]
    validate_rts_gmlc_source_identity(source)
    if source.get("manifest_sha256") != RTS_GMLC_MANIFEST_SHA256:
        raise ValueError("RTS-GMLC source manifest lock drifted")
    upstream_root = Path(source["path"])
    proxy = config["legacy_rts24_proxy"]
    audit = config["security_snapshot_audit"]
    manifest_path = upstream_root / "SHA256SUMS"
    if (
        not manifest_path.is_file()
        or _sha256(manifest_path) != source["manifest_sha256"]
    ):
        raise ValueError("RTS-GMLC source manifest SHA-256 drifted")
    if not verify_sha256_manifest(upstream_root):
        raise ValueError("RTS-GMLC source manifest validation failed")
    if int(proxy["load_region"]) != 1:
        raise ValueError("The legacy RTS-24 proxy currently supports only Area 1")

    base_data = load_rts24()
    static_peak_mw = float(proxy["static_peak_mw"])
    if not isclose(
        static_peak_mw,
        base_data.total_demand_mw,
        rel_tol=0.0,
        abs_tol=1.0e-6,
    ):
        raise ValueError("Proxy static peak must equal RTS-24 base demand")
    hourly = load_rts24_area1_load_multipliers(
        upstream_root,
        static_peak_mw=static_peak_mw,
    )
    if audit["quantile_method"] != "lower_order_statistic":
        raise ValueError("Unsupported load quantile method")
    selected = _select_load_conditions(hourly)
    conditions = tuple(audit["quantiles"])
    if not conditions or len(set(conditions)) != len(conditions):
        raise ValueError("Load conditions must be nonempty and unique")
    unknown_conditions = set(conditions) - selected.keys()
    if unknown_conditions:
        raise ValueError(f"Unknown load conditions: {sorted(unknown_conditions)}")

    fraction = float(audit["redispatch_fraction_pmax"])
    if not isfinite(fraction) or not 0.0 <= fraction <= 1.0:
        raise ValueError("Redispatch fraction must be finite and within [0, 1]")
    solver_name = audit["solver"]
    commitment_model = audit["commitment_model"]
    commitment_options = {
        "fixed_online": False,
        "single_snapshot_static_unit_selection": True,
    }
    if commitment_model not in commitment_options:
        raise ValueError("Unsupported generator commitment model")
    optimize_unit_selection = commitment_options[commitment_model]
    immediate_rating = audit["immediate_branch_rating"]
    sustained_rating = audit["sustained_rating"]
    cost_breakpoints = int(audit["cost_breakpoints"])
    if audit["excluded_islanding_policy"] != "report_as_failure":
        raise ValueError("Unsupported islanding-contingency policy")

    online_generators = tuple(
        generator for generator in base_data.generators if generator.in_service
    )
    online_pmin_mw = sum(generator.p_min_mw for generator in online_generators)
    online_pmax_mw = sum(generator.p_max_mw for generator in online_generators)
    branch_indices = non_islanding_branch_indices(base_data)
    excluded_branch_indices = tuple(
        branch.index
        for branch in base_data.branches
        if branch.in_service and branch.index not in branch_indices
    )
    generator_contingencies = sum(
        generator.in_service and generator.p_max_mw > 0.0
        for generator in base_data.generators
    )
    modeled_state_count = 1 + 2 * len(branch_indices) + generator_contingencies
    hours_below_online_pmin = sum(
        static_peak_mw * multiplier < online_pmin_mw - 1.0e-6
        for _, multiplier in hourly
    )
    common_blockers = (
        "synthetic_redispatch_without_response_time_evidence",
        "branch_10_unplanned_islanding_excluded",
        "contingency_ac_not_run_for_load_snapshots",
        "load_only_proxy_without_renewables",
        "chronological_commitment_not_modeled",
        "startup_cost_not_applied_no_prior_state",
        "minimum_up_down_times_not_modeled",
        "intertemporal_ramps_not_modeled",
    )
    rows = []
    generator_rows = []
    for name in conditions:
        timestamp, multiplier = selected[name]
        data = scale_rts24_demand(base_data, multiplier)
        limits = {
            generator.index: fraction * generator.p_max_mw
            for generator in data.generators
        }
        outside_generation_bounds = (
            not optimize_unit_selection
            and data.total_demand_mw < online_pmin_mw - 1.0e-6
        ) or data.total_demand_mw > online_pmax_mw + 1.0e-6
        base_diagnostic = None
        result = None
        if not outside_generation_bounds:
            result = solve_security_constrained_dc_opf(
                data,
                redispatch_up_mw=limits,
                redispatch_down_mw=limits,
                immediate_rating=immediate_rating,
                sustained_rating=sustained_rating,
                cost_breakpoints=cost_breakpoints,
                optimize_unit_selection=optimize_unit_selection,
                solver_name=solver_name,
            )
            if not result.feasible:
                if optimize_unit_selection:
                    base_diagnostic = solve_security_constrained_dc_opf(
                        data,
                        redispatch_up_mw=limits,
                        redispatch_down_mw=limits,
                        branch_indices=(),
                        generator_indices=(),
                        cost_breakpoints=cost_breakpoints,
                        optimize_unit_selection=True,
                        solver_name=solver_name,
                    )
                else:
                    base_diagnostic = solve_dc_opf(data, solver_name=solver_name)
        base_feasible = bool(
            (result and result.feasible)
            or (base_diagnostic and base_diagnostic.feasible)
        )
        scopf_feasible = bool(result and result.feasible)
        commitment = (
            result.generator_commitment
            if result is not None and result.feasible
            else None
        )
        committed_indices = tuple(
            index for index, committed in (commitment or {}).items() if committed
        )
        committed_pmin_mw = sum(
            data.generators[index].p_min_mw for index in committed_indices
        )
        committed_pmax_mw = sum(
            data.generators[index].p_max_mw for index in committed_indices
        )
        ac_result = None
        if commitment is not None and bool(audit["base_ac_restoration"]):
            ac_result = restore_ac_feasibility(
                data,
                result.base_result,
                generator_commitment=commitment,
                reference_generation_mw=result.base_result.generation_mw,
                redispatch_up_mw=limits,
                redispatch_down_mw=limits,
            )
        diagnosis = _diagnosis(
            demand_mw=data.total_demand_mw,
            online_pmin_mw=online_pmin_mw,
            online_pmax_mw=online_pmax_mw,
            commitment_model=commitment_model,
            base_feasible=base_feasible,
            scopf_feasible=scopf_feasible,
        )
        blockers = list(common_blockers)
        if diagnosis == "demand_below_fixed_online_pmin_requires_commitment":
            blockers.append("fixed_online_commitment_infeasible_at_this_load")
        if ac_result is not None and not ac_result.secure:
            blockers.append("base_snapshot_ac_restoration_failed")
        rows.append(
            {
                "condition": name,
                "quantile_method": audit["quantile_method"],
                "timestamp": timestamp.isoformat(),
                "load_multiplier": multiplier,
                "total_demand_mw": data.total_demand_mw,
                "online_pmin_mw": online_pmin_mw,
                "online_pmax_mw": online_pmax_mw,
                "annual_hours_below_fixed_online_pmin": hours_below_online_pmin,
                "base_snapshot_feasible": base_feasible,
                "commitment_method": commitment_model,
                "commitment_temporal_scope": "independent_single_snapshot",
                "commitment_parameter_source": (
                    "pypower_case24_gen_status_pmin_pmax_gencost"
                ),
                "polynomial_cost_treatment": (
                    "native_intercept_conditioned_on_commitment"
                ),
                "optimization_cost_model": (
                    f"convex_tangent_lower_envelope_{cost_breakpoints}_breakpoints"
                ),
                "reported_cost_treatment": (
                    "exact_polynomial_recalculation_at_selected_solution"
                ),
                "startup_cost_treatment": (
                    "available_in_source_not_applied_no_prior_state"
                ),
                "min_up_down_treatment": "not_available_not_modeled",
                "ramp_treatment": "rts24_missing_not_modeled",
                "rts_gmlc_generator_mapping_status": "forbidden",
                "committed_real_power_units": (
                    "" if commitment is None else len(committed_indices)
                ),
                "committed_generator_indices": (
                    ""
                    if commitment is None
                    else ";".join(str(index) for index in committed_indices)
                ),
                "committed_pmin_mw": ("" if commitment is None else committed_pmin_mw),
                "committed_pmax_mw": ("" if commitment is None else committed_pmax_mw),
                "load_shedding_allowed": False,
                "redispatch_fraction_pmax": fraction,
                "dc_scopf_feasible": scopf_feasible,
                "termination_condition": (
                    "precheck_infeasible"
                    if outside_generation_bounds
                    else result.termination_condition
                ),
                "base_production_cost_usd_per_hour_exact": (
                    ""
                    if result is None or result.objective is None
                    else result.objective
                ),
                "states_modeled": (
                    modeled_state_count if result is None else len(result.states)
                ),
                "states_solved": 0 if result is None else len(result.state_results),
                "excluded_branch_indices": ";".join(
                    str(index)
                    for index in (
                        excluded_branch_indices
                        if result is None
                        else result.excluded_branch_indices
                    )
                ),
                "response_parameter_status": audit["response_parameter_status"],
                "load_parameter_status": audit["load_parameter_status"],
                "ac_validation_scope": "base_snapshot_restoration_only",
                "base_ac_evaluated": bool(ac_result and ac_result.evaluated),
                "base_ac_converged": bool(ac_result and ac_result.converged),
                "base_ac_secure": bool(ac_result and ac_result.secure),
                "base_ac_status": (
                    "not_run" if ac_result is None else ac_result.status
                ),
                "base_ac_reference_bus": (
                    "" if ac_result is None else ac_result.reference_bus
                ),
                "base_ac_active_generator_indices": (
                    ""
                    if ac_result is None
                    else ";".join(
                        str(index) for index in ac_result.active_generator_indices
                    )
                ),
                "base_ac_losses_mw": (
                    "" if ac_result is None else ac_result.ac_losses_mw
                ),
                "base_ac_max_voltage_violation_pu": (
                    "" if ac_result is None else ac_result.max_voltage_violation_pu
                ),
                "base_ac_max_branch_loading_fraction": (
                    "" if ac_result is None else ac_result.max_branch_loading_fraction
                ),
                "base_ac_max_active_power_violation_mw": (
                    "" if ac_result is None else ac_result.max_active_power_violation_mw
                ),
                "base_ac_max_reactive_power_violation_mvar": (
                    ""
                    if ac_result is None
                    else ac_result.max_reactive_power_violation_mvar
                ),
                "security_certified": False,
                "certification_blockers": ";".join(blockers),
                "diagnosis": diagnosis,
            }
        )
        for generator in data.generators:
            committed = "" if commitment is None else commitment[generator.index]
            generation_mw = (
                ""
                if result is None or not result.feasible
                else result.base_result.generation_mw[generator.index]
            )
            production_cost = (
                ""
                if committed == ""
                else (
                    generator.cost_quadratic * generation_mw**2
                    + generator.cost_linear * generation_mw
                    + generator.cost_constant
                    if committed
                    else 0.0
                )
            )
            ac_generation_mw = (
                ""
                if ac_result is None or not ac_result.converged
                else ac_result.generation_mw[generator.index]
            )
            ac_reactive_generation_mvar = (
                ""
                if ac_result is None or not ac_result.converged
                else ac_result.reactive_generation_mvar[generator.index]
            )
            generator_rows.append(
                {
                    "condition": name,
                    "timestamp": timestamp.isoformat(),
                    "commitment_method": commitment_model,
                    "generator_index": generator.index,
                    "bus": generator.bus,
                    "source_in_service": generator.in_service,
                    "real_power_capable": generator.p_max_mw > 0.0,
                    "committed": committed,
                    "p_min_mw": generator.p_min_mw,
                    "p_max_mw": generator.p_max_mw,
                    "base_generation_mw": generation_mw,
                    "base_production_cost_usd_per_hour_exact": production_cost,
                    "base_ac_generation_mw": ac_generation_mw,
                    "base_ac_reactive_generation_mvar": (ac_reactive_generation_mvar),
                }
            )

    output_path = Path(config["output"]["security_snapshots"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    generator_output_path = Path(config["output"]["security_snapshot_generators"])
    generator_output_path.parent.mkdir(parents=True, exist_ok=True)
    with generator_output_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(generator_rows[0]))
        writer.writeheader()
        writer.writerows(generator_rows)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rts_gmlc.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, default=str))


if __name__ == "__main__":
    main()
