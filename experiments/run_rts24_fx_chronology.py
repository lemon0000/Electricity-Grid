"""Audit the fixed M3 policy against one explicit chronological X-call trace."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import yaml

from src.evaluation import (
    CHRONOLOGICAL_SENSITIVITY_METRIC_SCOPE,
    ChronologicalFlexibilityEnvelope,
    ChronologicalFlexibilityTrace,
    calculate_capacity_milestones,
    evaluate_chronological_flexibility,
)
from src.grid import load_rts24_area1_load_multipliers


_PARAMETER_STATUS = "synthetic_chronological_witness_not_contract_or_event_evidence"
_TRACE_DEFINITION = (
    "one_full_active_x_call_at_first_hour_of_each_positive_x_quarter"
)


def _milestone_dict(milestone: object) -> dict[str, object]:
    return {
        "threshold_mw": milestone.threshold_mw,
        "reached": milestone.reached,
        "quarter": milestone.quarter,
        "right_censored": milestone.right_censored,
        "censor_quarter": milestone.censor_quarter,
        "display_label": milestone.display_label,
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _quarter(timestamp: object) -> str:
    return f"q{(timestamp.month - 1) // 3 + 1}"


def run(config_path: Path) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    sensitivity = config["chronological_sensitivity"]
    if sensitivity["parameter_status"] != _PARAMETER_STATUS:
        raise ValueError("Chronological parameters must retain their synthetic status")
    if sensitivity["trace_definition"] != _TRACE_DEFINITION:
        raise ValueError("Unsupported chronological witness trace")
    if sensitivity["load_values_used_in_envelope"] is not False:
        raise ValueError("RTS-GMLC load values cannot stand in for business flexibility")
    if sensitivity["recovery_headroom_basis"] != (
        "released_capacity_minus_flat_layer_baseline"
    ):
        raise ValueError("Unsupported recovery-headroom basis")

    planning_quarters = config["planning"]["quarters"]
    quarter_names = tuple(str(row["name"]) for row in planning_quarters)
    if quarter_names != ("q1", "q2", "q3", "q4"):
        raise ValueError("The pinned 2020 chronology requires q1 through q4")
    demand = {
        str(row["name"]): float(row["data_center_demand_mw"])
        for row in planning_quarters
    }
    firm = {
        str(name): float(capacity)
        for name, capacity in config["fixed_fx_plan"]["firm_capacity_mw"].items()
    }
    conditional = {
        str(name): float(capacity)
        for name, capacity in config["fixed_fx_plan"][
            "conditional_capacity_mw"
        ].items()
    }
    total = {name: firm[name] + conditional[name] for name in quarter_names}
    connected = {name: min(demand[name], total[name]) for name in quarter_names}
    firm_demand = {name: min(demand[name], firm[name]) for name in quarter_names}
    active_conditional = {
        name: connected[name] - firm_demand[name] for name in quarter_names
    }

    timeline = load_rts24_area1_load_multipliers(Path(sensitivity["timeline_path"]))
    timestamps = tuple(timestamp for timestamp, _ in timeline)
    load_multipliers = tuple(multiplier for _, multiplier in timeline)
    periods = tuple(_quarter(timestamp) for timestamp in timestamps)
    hours_by_period = Counter(periods)
    expected_hours = {"q1": 2184, "q2": 2184, "q3": 2208, "q4": 2208}
    if hours_by_period != expected_hours:
        raise ValueError(f"Unexpected RTS-GMLC quarter hours: {hours_by_period}")

    dt = float(sensitivity["time_step_hours"])
    duration = float(sensitivity["call_duration_hours"])
    duration_steps = round(duration / dt)
    if duration_steps <= 0 or abs(duration_steps * dt - duration) > 1.0e-9:
        raise ValueError("Call duration must be a positive multiple of the time step")
    first_index = {name: periods.index(name) for name in quarter_names}

    envelope = ChronologicalFlexibilityEnvelope(
        time_step_hours=dt,
        maximum_event_duration_hours=float(
            sensitivity["maximum_event_duration_hours"]
        ),
        minimum_recovery_hours=float(sensitivity["minimum_recovery_hours"]),
        maximum_events_by_period={
            str(name): int(limit)
            for name, limit in sensitivity["maximum_events_by_period"].items()
        },
        maximum_curtailment_energy_mwh_by_period={
            str(name): float(limit)
            for name, limit in sensitivity[
                "maximum_curtailment_energy_mwh_by_period"
            ].items()
        },
        maximum_recovery_debt_mwh=float(
            sensitivity["maximum_recovery_debt_mwh"]
        ),
        maximum_recovery_power_mw=float(
            sensitivity["maximum_recovery_power_mw"]
        ),
        minimum_event_power_mw=float(sensitivity["minimum_event_power_mw"]),
        response_time_hours=float(sensitivity["response_time_hours"]),
        curtailment_ramp_mw_per_hour=float(
            sensitivity["curtailment_ramp_mw_per_hour"]
        ),
        recovery_efficiency=float(sensitivity["recovery_efficiency"]),
        terminal_debt_limit_mwh_by_period={
            str(name): float(limit)
            for name, limit in sensitivity[
                "terminal_debt_limit_mwh_by_period"
            ].items()
        },
        parameter_status=sensitivity["parameter_status"],
    )

    layer_inputs = {
        "actual": {
            "call_limit": active_conditional,
            "baseline": connected,
        },
        "contract_counterfactual": {
            "call_limit": conditional,
            "baseline": total,
        },
    }
    results = {}
    traces = {}
    for layer, layer_input in layer_inputs.items():
        calls = [0.0] * len(timestamps)
        for name in quarter_names:
            call_limit = layer_input["call_limit"][name]
            if call_limit <= 0.0:
                continue
            start = first_index[name]
            for index in range(start, start + duration_steps):
                calls[index] = call_limit
        call_limits = tuple(layer_input["call_limit"][period] for period in periods)
        recovery_headroom = tuple(
            total[period] - layer_input["baseline"][period] for period in periods
        )
        trace = ChronologicalFlexibilityTrace(
            name=f"{layer}_{_TRACE_DEFINITION}",
            timestamps=timestamps,
            periods=periods,
            grid_call_mw=tuple(calls),
            call_limit_mw=call_limits,
            recovery_headroom_mw=recovery_headroom,
            boundary_state_status="clean_boundary_with_zero_carry_in",
            completed_periods=frozenset(quarter_names),
            initial_has_prior_event=False,
        )
        traces[layer] = trace
        results[layer] = evaluate_chronological_flexibility(trace, envelope)

    full_trace_pass = {
        name: all(result.feasible_by_period[name] for result in results.values())
        for name in quarter_names
    }
    temporally_qualified_capacity = {
        name: firm[name] + (conditional[name] if full_trace_pass[name] else 0.0)
        for name in quarter_names
    }
    milestones = calculate_capacity_milestones(
        quarter_names=quarter_names,
        total_capacity_mw=temporally_qualified_capacity,
        model_validated_by_quarter={name: True for name in quarter_names},
        continuous_validation_hours={
            name: float(hours_by_period[name]) for name in quarter_names
        },
        application_capacity_mw=float(
            config["fixed_poi"]["application_capacity_mw"]
        ),
        minimum_operational_block_mw=float(
            config["service_envelope"]["minimum_operational_block_mw"]
        ),
        minimum_validation_hours=float(
            config["service_envelope"]["minimum_validation_hours"]
        ),
        metric_scope=CHRONOLOGICAL_SENSITIVITY_METRIC_SCOPE,
    )

    hourly_rows = []
    for layer, trace in traces.items():
        result = results[layer]
        for index, timestamp in enumerate(timestamps):
            hourly_rows.append(
                {
                    "timestamp": timestamp.isoformat(),
                    "quarter": periods[index],
                    "layer": layer,
                    "timeline_load_multiplier_not_used_in_envelope": (
                        load_multipliers[index]
                    ),
                    "grid_call_mw": trace.grid_call_mw[index],
                    "call_limit_mw": trace.call_limit_mw[index],
                    "recovery_headroom_mw": trace.recovery_headroom_mw[index],
                    "recovery_power_mw": result.recovery_power_mw[index],
                    "recovery_debt_mwh": result.recovery_debt_mwh[index],
                    "parameter_status": envelope.parameter_status,
                    "security_certified": False,
                }
            )
    _write_csv(Path(sensitivity["hourly_output_path"]), hourly_rows)

    layer_summary = {}
    for layer, result in results.items():
        layer_summary[layer] = {
            "feasible": result.feasible,
            "feasible_by_quarter": result.feasible_by_period,
            "violations": list(result.violations),
            "violations_by_quarter": {
                name: list(values)
                for name, values in result.violations_by_period.items()
            },
            "event_count_by_quarter": result.event_count_by_period,
            "curtailment_energy_mwh_by_quarter": (
                result.curtailment_energy_mwh_by_period
            ),
            "terminal_recovery_debt_mwh_by_quarter": (
                result.terminal_recovery_debt_mwh_by_period
            ),
            "peak_recovery_debt_mwh": result.peak_recovery_debt_mwh,
        }
    summary = {
        "timeline_source": sensitivity["timeline_source"],
        "timeline_hours": len(timestamps),
        "timeline_hours_by_quarter": dict(hours_by_period),
        "timeline_load_values_used_in_envelope": False,
        "trace_definition": sensitivity["trace_definition"],
        "recovery_headroom_basis": sensitivity["recovery_headroom_basis"],
        "parameter_status": envelope.parameter_status,
        "firm_capacity_mw": firm,
        "conditional_capacity_mw": conditional,
        "actual_active_conditional_demand_mw": active_conditional,
        "full_trace_pass_by_quarter": full_trace_pass,
        "temporally_qualified_capacity_mw": temporally_qualified_capacity,
        "layer_results": layer_summary,
        "milestone_metric_scope": milestones.metric_scope,
        "T_module": _milestone_dict(milestones.t_module),
        "T20": _milestone_dict(milestones.t20),
        "T50": _milestone_dict(milestones.t50),
        "T100": _milestone_dict(milestones.t100),
        "network_hourly_coupling": False,
        "security_certified": False,
        "interpretation": (
            "mechanism_sensitivity_on_one_explicit_call_trace_not_event_frequency_"
            "evidence_or_chronological_grid_security_certification"
        ),
        "remaining_blockers": [
            "data_center_hourly_workload_and_recovery_headroom_are_not_observed",
            "failure_timing_and_frequency_are_not_observed",
            "hourly_trace_is_not_coupled_to_chronological_unit_commitment_or_ac_security",
            "envelope_parameters_are_synthetic_sensitivities",
        ],
    }
    summary_path = Path(sensitivity["summary_output_path"])
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
        default=Path("configs/rts24_deterministic_fx.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
