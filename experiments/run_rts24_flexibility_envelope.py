"""Run the M6 F1--F3 temporal-flexibility mechanism gate."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from dataclasses import replace
from math import isfinite
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


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_LAYERS = ("actual", "contract_counterfactual")
_TRACES = ("network_minimum_call_replay", "full_x_contract_stress")
_ABLATIONS = ("F1_mw_only", "F2_temporal_no_recovery", "F3_full_recovery")
_QUARTERS = ("q1", "q2", "q3", "q4")
_QUARTER_FIELDS = (
    "gate_passed",
    "trace",
    "layer",
    "ablation",
    "quarter",
    "source_network_call_mw",
    "stress_call_mw",
    "executed_call_mw",
    "call_limit_mw",
    "recovery_headroom_mw",
    "feasible",
    "violations",
    "event_count",
    "curtailment_energy_mwh",
    "terminal_recovery_debt_mwh",
    "temporally_qualified_capacity_mw",
    "security_certified",
)
_HOURLY_FIELDS = (
    "timestamp",
    "quarter",
    "trace",
    "layer",
    "ablation",
    "timeline_load_multiplier_not_used_as_business_data",
    "grid_call_mw",
    "call_limit_mw",
    "recovery_headroom_mw",
    "recovery_power_mw",
    "recovery_debt_mwh",
    "parameter_status",
    "security_certified",
)


def _resolve_path(configured: object) -> Path:
    path = Path(str(configured))
    return path if path.is_absolute() else _REPOSITORY_ROOT / path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_hash(path: Path, expected: object, label: str) -> str:
    expected = str(expected).lower()
    actual = _sha256(path)
    if len(expected) != 64 or actual != expected:
        raise ValueError(f"{label} SHA-256 does not match the M6 freeze")
    return actual


def _number(value: object, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _strict_bool(value: object, label: str) -> bool:
    if value in (True, "True"):
        return True
    if value in (False, "False"):
        return False
    raise ValueError(f"{label} must be True or False")


def _strict_json(path: Path) -> dict[str, object]:
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError(f"Non-finite JSON value: {value}")

    parsed = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicates,
        parse_constant=reject_constant,
    )
    if not isinstance(parsed, dict):
        raise ValueError("M3 summary must be a JSON object")
    return parsed


def _write_csv(
    path: Path,
    fields: tuple[str, ...],
    rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _quarter(timestamp) -> str:
    return f"q{(timestamp.month - 1) // 3 + 1}"


def _milestone_dict(milestone) -> dict[str, object]:
    return {
        "threshold_mw": milestone.threshold_mw,
        "reached": milestone.reached,
        "quarter": milestone.quarter,
        "right_censored": milestone.right_censored,
        "censor_quarter": milestone.censor_quarter,
        "display_label": milestone.display_label,
    }


def _load_source(config, state_path: Path, summary_path: Path):
    validation = config["validation"]
    call_tolerance = _number(validation["call_tolerance_mw"], "Call tolerance")
    balance_tolerance = _number(
        validation["source_balance_tolerance_mw"],
        "Source balance tolerance",
    )
    with state_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected_count = int(config["source"]["required_security_state_count"])
    if len(rows) != len(_QUARTERS) * len(_LAYERS) * expected_count:
        raise ValueError("M3 source state table does not contain 4 x 2 x 107 rows")
    grouped = {(quarter, layer): [] for quarter in _QUARTERS for layer in _LAYERS}
    for row in rows:
        key = (row["quarter"], row["layer"])
        if key not in grouped:
            raise ValueError("M3 source contains an unknown quarter or layer")
        if not _strict_bool(row["constraints_satisfied"], "Source constraints"):
            raise ValueError("M3 source contains a failed state audit")
        if _strict_bool(row["security_certified"], "Source certification"):
            raise ValueError("M3 source cannot claim security certification")
        if abs(_number(row["firm_breach_mw"], "Firm breach")) > call_tolerance:
            raise ValueError("M3 source contains a firm breach")
        if (
            abs(_number(row["conditional_breach_mw"], "Conditional breach"))
            > call_tolerance
        ):
            raise ValueError("M3 source contains a conditional breach")
        if (
            _number(row["max_balance_residual_mw"], "Balance residual")
            > balance_tolerance
        ):
            raise ValueError("M3 source balance residual exceeds the M6 tolerance")
        grouped[key].append(row)

    source = {}
    for key, group in grouped.items():
        if len(group) != expected_count or len({row["state"] for row in group}) != expected_count:
            raise ValueError("M3 source security-state set is incomplete")

        def unique_number(field: str) -> float:
            values = {_number(row[field], field) for row in group}
            if len(values) != 1:
                raise ValueError(f"M3 source field varies within a quarter/layer: {field}")
            return values.pop()

        bounded_calls = [
            _number(row["grid_curtailment_mw"], "Grid call")
            for row in group
            if row["response_mode"] == "bounded"
        ]
        if not bounded_calls:
            raise ValueError("M3 source contains no bounded-response states")
        source[key] = {
            "network_call_mw": max(bounded_calls),
            "call_limit_mw": unique_number("call_limit_mw"),
            "firm_capacity_mw": unique_number("firm_capacity_mw"),
            "conditional_capacity_mw": unique_number("conditional_capacity_mw"),
            "total_capacity_mw": unique_number("total_capacity_mw"),
            "connected_demand_mw": unique_number("connected_demand_mw"),
        }

    summary = _strict_json(summary_path)
    if summary.get("feasible") is not True:
        raise ValueError("Frozen M3 summary is not feasible")
    if summary.get("security_certified") is not False:
        raise ValueError("Frozen M3 summary cannot claim certification")
    minimum_call = _number(
        summary.get("minimum_call_certificate_mw_sum"),
        "Minimum-call certificate",
    )
    source_sum = sum(value["network_call_mw"] for value in source.values())
    if minimum_call <= call_tolerance and source_sum > call_tolerance:
        raise ValueError("M3 summary and source table disagree on zero minimum call")
    return source


def _envelope(config, *, recovery_enabled: bool):
    values = config["envelope"]
    envelope = ChronologicalFlexibilityEnvelope(
        time_step_hours=_number(config["timeline"]["time_step_hours"], "Time step"),
        maximum_event_duration_hours=_number(
            values["maximum_event_duration_hours"], "Maximum event duration"
        ),
        minimum_recovery_hours=_number(
            values["minimum_recovery_hours"], "Minimum recovery hours"
        ),
        maximum_events_by_period={
            str(key): int(value)
            for key, value in values["maximum_events_by_period"].items()
        },
        maximum_curtailment_energy_mwh_by_period={
            str(key): _number(value, "Maximum curtailment energy")
            for key, value in values[
                "maximum_curtailment_energy_mwh_by_period"
            ].items()
        },
        maximum_recovery_debt_mwh=_number(
            values["maximum_recovery_debt_mwh"], "Maximum recovery debt"
        ),
        maximum_recovery_power_mw=_number(
            values["maximum_recovery_power_mw"], "Maximum recovery power"
        ),
        minimum_event_power_mw=_number(
            values["minimum_event_power_mw"], "Minimum event power"
        ),
        response_time_hours=_number(
            values["response_time_hours"], "Response time"
        ),
        curtailment_ramp_mw_per_hour=_number(
            values["curtailment_ramp_mw_per_hour"], "Curtailment ramp"
        ),
        recovery_efficiency=_number(
            values["recovery_efficiency"], "Recovery efficiency"
        ),
        terminal_debt_limit_mwh_by_period={
            str(key): _number(value, "Terminal debt limit")
            for key, value in values[
                "terminal_debt_limit_mwh_by_period"
            ].items()
        },
        parameter_status=str(values["parameter_status"]),
    )
    if recovery_enabled:
        return envelope
    return replace(
        envelope,
        maximum_recovery_debt_mwh=1.0e12,
        terminal_debt_limit_mwh_by_period={},
    )


def _mw_only(trace, tolerance: float, time_step_hours: float):
    if not isfinite(time_step_hours) or time_step_hours <= 0.0:
        raise ValueError("MW-only time step must be positive")
    if not isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("MW-only tolerance must be finite and nonnegative")
    violations_by_period = {quarter: [] for quarter in _QUARTERS}
    event_count_by_period = {quarter: 0 for quarter in _QUARTERS}
    previous_call = 0.0
    for index, (period, call, limit) in enumerate(
        zip(trace.periods, trace.grid_call_mw, trace.call_limit_mw)
    ):
        if not isfinite(call) or not isfinite(limit) or call < 0.0 or limit < 0.0:
            raise ValueError("MW-only calls and limits must be finite and nonnegative")
        if call > limit + tolerance:
            violations_by_period[period].append(f"call_limit_exceeded_at_step_{index}")
        if call > tolerance and previous_call <= tolerance:
            event_count_by_period[period] += 1
        previous_call = call
    return {
        "feasible": not any(violations_by_period.values()),
        "feasible_by_period": {
            quarter: not violations_by_period[quarter] for quarter in _QUARTERS
        },
        "violations_by_period": violations_by_period,
        "event_count_by_period": event_count_by_period,
        "curtailment_energy_mwh_by_period": {
            quarter: sum(
                call * time_step_hours
                for period, call in zip(trace.periods, trace.grid_call_mw)
                if period == quarter
            )
            for quarter in _QUARTERS
        },
        "terminal_recovery_debt_mwh_by_period": {
            quarter: None for quarter in _QUARTERS
        },
    }


def run(config_path: Path) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    evaluation = config["evaluation"]
    if evaluation["role"] != "network_call_replay_and_full_x_temporal_ablation":
        raise ValueError("Unsupported M6 evaluation role")
    if evaluation["security_certified"] is not False:
        raise ValueError("M6 synthetic gate cannot claim security certification")
    if evaluation["chronological_grid_security_certified"] is not False:
        raise ValueError("M6 replay cannot claim chronological grid certification")
    if tuple(config["source"]["required_layers"]) != _LAYERS:
        raise ValueError("M6 must retain actual and contract-counterfactual layers")
    if config["source"]["call_aggregation"] != (
        "maximum_minimum_call_across_bounded_security_states_by_quarter_and_layer"
    ):
        raise ValueError("Unsupported network-call aggregation")
    if config["source"]["state_enumeration_interpretation"] != (
        "mutually_exclusive_security_checks_not_event_frequency"
    ):
        raise ValueError("N-1 states cannot be treated as event frequency")
    if tuple(config["ablation"]["order"]) != _ABLATIONS:
        raise ValueError("M6 ablation order must remain F1, F2, F3")
    if config["timeline"]["load_values_used_as_business_data"] is not False:
        raise ValueError("System load cannot stand in for business recovery data")

    source_config_path = _resolve_path(config["source"]["fixed_policy_config"])
    fixed_config = yaml.safe_load(source_config_path.read_text(encoding="utf-8"))
    state_path = _resolve_path(config["source"]["m3_state_path"])
    summary_path = _resolve_path(config["source"]["m3_summary_path"])
    state_hash = _validate_hash(
        state_path, config["source"]["m3_state_sha256"], "M3 state table"
    )
    summary_hash = _validate_hash(
        summary_path, config["source"]["m3_summary_sha256"], "M3 summary"
    )
    source = _load_source(config, state_path, summary_path)

    timeline = load_rts24_area1_load_multipliers(
        _resolve_path(config["timeline"]["path"])
    )
    timestamps = tuple(timestamp for timestamp, _value in timeline)
    unused_load_values = tuple(value for _timestamp, value in timeline)
    periods = tuple(_quarter(timestamp) for timestamp in timestamps)
    hours_by_period = Counter(periods)
    if hours_by_period != {"q1": 2184, "q2": 2184, "q3": 2208, "q4": 2208}:
        raise ValueError("M6 timeline does not contain the frozen 2020 quarter hours")
    first_index = {quarter: periods.index(quarter) for quarter in _QUARTERS}
    dt = _number(config["timeline"]["time_step_hours"], "Time step")
    duration = _number(config["timeline"]["event_duration_hours"], "Event duration")
    duration_steps = round(duration / dt)
    if duration_steps <= 0 or abs(duration_steps * dt - duration) > 1.0e-9:
        raise ValueError("M6 event duration must be a positive time-step multiple")

    traces = {}
    for trace_name in _TRACES:
        for layer in _LAYERS:
            calls = [0.0] * len(timestamps)
            limits_by_quarter = {
                quarter: source[quarter, layer]["call_limit_mw"]
                for quarter in _QUARTERS
            }
            source_calls = {
                quarter: source[quarter, layer]["network_call_mw"]
                for quarter in _QUARTERS
            }
            magnitudes = (
                source_calls
                if trace_name == "network_minimum_call_replay"
                else limits_by_quarter
            )
            for quarter in _QUARTERS:
                if magnitudes[quarter] <= 0.0:
                    continue
                start = first_index[quarter]
                for index in range(start, start + duration_steps):
                    calls[index] = magnitudes[quarter]
            baseline = {
                quarter: (
                    source[quarter, layer]["connected_demand_mw"]
                    if layer == "actual"
                    else source[quarter, layer]["total_capacity_mw"]
                )
                for quarter in _QUARTERS
            }
            headroom = {
                quarter: source[quarter, layer]["total_capacity_mw"] - baseline[quarter]
                for quarter in _QUARTERS
            }
            traces[trace_name, layer] = ChronologicalFlexibilityTrace(
                name=f"{trace_name}_{layer}",
                timestamps=timestamps,
                periods=periods,
                grid_call_mw=tuple(calls),
                call_limit_mw=tuple(limits_by_quarter[period] for period in periods),
                recovery_headroom_mw=tuple(headroom[period] for period in periods),
                boundary_state_status="clean_boundary_with_zero_carry_in",
                completed_periods=frozenset(_QUARTERS),
                initial_has_prior_event=False,
            )

    temporal_envelope = _envelope(config, recovery_enabled=False)
    full_envelope = _envelope(config, recovery_enabled=True)
    tolerance = _number(config["validation"]["call_tolerance_mw"], "Call tolerance")
    results = {}
    for key, trace in traces.items():
        results[key, "F1_mw_only"] = _mw_only(trace, tolerance, dt)
        results[key, "F2_temporal_no_recovery"] = evaluate_chronological_flexibility(
            trace, temporal_envelope, tolerance=tolerance
        )
        results[key, "F3_full_recovery"] = evaluate_chronological_flexibility(
            trace, full_envelope, tolerance=tolerance
        )

    firm = {
        quarter: source[quarter, "contract_counterfactual"]["firm_capacity_mw"]
        for quarter in _QUARTERS
    }
    conditional = {
        quarter: source[quarter, "contract_counterfactual"][
            "conditional_capacity_mw"
        ]
        for quarter in _QUARTERS
    }
    qualified = {}
    milestones = {}
    for trace_name in _TRACES:
        for ablation in _ABLATIONS:
            pass_by_quarter = {
                quarter: all(
                    (
                        results[(trace_name, layer), ablation]["feasible_by_period"][
                            quarter
                        ]
                        if ablation == "F1_mw_only"
                        else results[(trace_name, layer), ablation].feasible_by_period[
                            quarter
                        ]
                    )
                    for layer in _LAYERS
                )
                for quarter in _QUARTERS
            }
            qualified[trace_name, ablation] = {
                quarter: firm[quarter]
                + (conditional[quarter] if pass_by_quarter[quarter] else 0.0)
                for quarter in _QUARTERS
            }
            milestones[trace_name, ablation] = calculate_capacity_milestones(
                quarter_names=_QUARTERS,
                total_capacity_mw=qualified[trace_name, ablation],
                model_validated_by_quarter={quarter: True for quarter in _QUARTERS},
                continuous_validation_hours=dict(hours_by_period),
                application_capacity_mw=float(
                    fixed_config["fixed_poi"]["application_capacity_mw"]
                ),
                minimum_operational_block_mw=float(
                    fixed_config["service_envelope"]["minimum_operational_block_mw"]
                ),
                minimum_validation_hours=float(
                    fixed_config["service_envelope"]["minimum_validation_hours"]
                ),
                metric_scope=CHRONOLOGICAL_SENSITIVITY_METRIC_SCOPE,
            )

    expected_pattern = config["ablation"]["mechanism_gate_expectation"]

    def feasible_value(trace_name: str, layer: str, ablation: str) -> bool:
        result = results[(trace_name, layer), ablation]
        return result["feasible"] if ablation == "F1_mw_only" else result.feasible

    gate_passed = True
    for trace_name in _TRACES:
        if set(expected_pattern.get(trace_name, {})) != set(_ABLATIONS):
            raise ValueError("M6 mechanism expectation is incomplete")
        for ablation in _ABLATIONS:
            if set(expected_pattern[trace_name][ablation]) != set(_LAYERS):
                raise ValueError("M6 layer expectation is incomplete")
            for layer in _LAYERS:
                expected = expected_pattern[trace_name][ablation][layer]
                if not isinstance(expected, bool):
                    raise ValueError("M6 mechanism expectations must be booleans")
                gate_passed = gate_passed and (
                    feasible_value(trace_name, layer, ablation) is expected
                )
    quarter_rows = []
    for trace_name in _TRACES:
        for layer in _LAYERS:
            for ablation in _ABLATIONS:
                result = results[(trace_name, layer), ablation]
                for quarter in _QUARTERS:
                    if ablation == "F1_mw_only":
                        feasible = result["feasible_by_period"][quarter]
                        violations = result["violations_by_period"][quarter]
                        events = result["event_count_by_period"][quarter]
                        energy = result["curtailment_energy_mwh_by_period"][quarter]
                        debt = result["terminal_recovery_debt_mwh_by_period"][quarter]
                    else:
                        feasible = result.feasible_by_period[quarter]
                        violations = result.violations_by_period[quarter]
                        events = result.event_count_by_period[quarter]
                        energy = result.curtailment_energy_mwh_by_period[quarter]
                        debt = result.terminal_recovery_debt_mwh_by_period[quarter]
                    trace = traces[trace_name, layer]
                    indices = [
                        index for index, period in enumerate(periods) if period == quarter
                    ]
                    quarter_rows.append(
                        {
                            "gate_passed": gate_passed,
                            "trace": trace_name,
                            "layer": layer,
                            "ablation": ablation,
                            "quarter": quarter,
                            "source_network_call_mw": source[quarter, layer][
                                "network_call_mw"
                            ],
                            "stress_call_mw": source[quarter, layer]["call_limit_mw"],
                            "executed_call_mw": max(
                                trace.grid_call_mw[index] for index in indices
                            ),
                            "call_limit_mw": source[quarter, layer]["call_limit_mw"],
                            "recovery_headroom_mw": max(
                                trace.recovery_headroom_mw[index] for index in indices
                            ),
                            "feasible": feasible,
                            "violations": json.dumps(list(violations), separators=(",", ":")),
                            "event_count": events,
                            "curtailment_energy_mwh": energy,
                            "terminal_recovery_debt_mwh": debt,
                            "temporally_qualified_capacity_mw": qualified[
                                trace_name, ablation
                            ][quarter],
                            "security_certified": False,
                        }
                    )

    hourly_rows = []
    for trace_name in _TRACES:
        for layer in _LAYERS:
            trace = traces[trace_name, layer]
            for ablation in ("F2_temporal_no_recovery", "F3_full_recovery"):
                result = results[(trace_name, layer), ablation]
                for index, timestamp in enumerate(timestamps):
                    hourly_rows.append(
                        {
                            "timestamp": timestamp.isoformat(),
                            "quarter": periods[index],
                            "trace": trace_name,
                            "layer": layer,
                            "ablation": ablation,
                            "timeline_load_multiplier_not_used_as_business_data": (
                                unused_load_values[index]
                            ),
                            "grid_call_mw": trace.grid_call_mw[index],
                            "call_limit_mw": trace.call_limit_mw[index],
                            "recovery_headroom_mw": trace.recovery_headroom_mw[index],
                            "recovery_power_mw": result.recovery_power_mw[index],
                            "recovery_debt_mwh": result.recovery_debt_mwh[index],
                            "parameter_status": evaluation["parameter_status"],
                            "security_certified": False,
                        }
                    )

    output = config["output"]
    quarter_path = _resolve_path(output["quarter_path"])
    hourly_path = _resolve_path(output["hourly_path"])
    summary_path_out = _resolve_path(output["summary_path"])
    _write_csv(quarter_path, _QUARTER_FIELDS, quarter_rows)
    _write_csv(hourly_path, _HOURLY_FIELDS, hourly_rows)
    summary = {
        "evaluation_id": evaluation["id"],
        "parameter_status": evaluation["parameter_status"],
        "m3_state_sha256": state_hash,
        "m3_summary_sha256": summary_hash,
        "source_security_state_count": int(
            config["source"]["required_security_state_count"]
        ),
        "state_enumeration_interpretation": config["source"][
            "state_enumeration_interpretation"
        ],
        "timeline_hours": len(timestamps),
        "timeline_hours_by_quarter": dict(hours_by_period),
        "timeline_load_values_used_as_business_data": False,
        "network_call_magnitude_coupled": True,
        "chronological_grid_dispatch_coupled": False,
        "network_call_mw_by_layer_quarter": {
            layer: {
                quarter: source[quarter, layer]["network_call_mw"]
                for quarter in _QUARTERS
            }
            for layer in _LAYERS
        },
        "network_replay_is_degenerate_zero_call": all(
            source[quarter, layer]["network_call_mw"] <= tolerance
            for quarter in _QUARTERS
            for layer in _LAYERS
        ),
        "ablation_results": {
            trace_name: {
                ablation: {
                    "actual_feasible": (
                        results[(trace_name, "actual"), ablation]["feasible"]
                        if ablation == "F1_mw_only"
                        else results[(trace_name, "actual"), ablation].feasible
                    ),
                    "contract_counterfactual_feasible": (
                        results[
                            (trace_name, "contract_counterfactual"), ablation
                        ]["feasible"]
                        if ablation == "F1_mw_only"
                        else results[
                            (trace_name, "contract_counterfactual"), ablation
                        ].feasible
                    ),
                    "temporally_qualified_capacity_mw": qualified[
                        trace_name, ablation
                    ],
                    "T20": _milestone_dict(milestones[trace_name, ablation].t20),
                    "T50": _milestone_dict(milestones[trace_name, ablation].t50),
                    "T100": _milestone_dict(milestones[trace_name, ablation].t100),
                }
                for ablation in _ABLATIONS
            }
            for trace_name in _TRACES
        },
        "m6_mechanism_gate_passed": gate_passed,
        "security_certified": False,
        "interpretation": (
            "network_call_magnitude_replay_plus_synthetic_full_x_temporal_"
            "ablation_not_chronological_grid_or_contract_evidence"
        ),
        "remaining_blockers": [
            "frozen_m3_minimum_network_call_is_zero_in_all_quarters",
            "network_security_states_are_not_an_event_chronology",
            "data_center_hourly_workload_and_recovery_headroom_are_not_observed",
            "failure_timing_and_frequency_are_not_observed",
            "hourly_trace_is_not_coupled_to_scuc_sced_or_ac_security",
            "envelope_parameters_are_synthetic_sensitivities",
        ],
        "output_paths": {
            "quarter": str(quarter_path),
            "hourly": str(hourly_path),
            "summary": str(summary_path_out),
        },
    }
    summary_path_out.parent.mkdir(parents=True, exist_ok=True)
    summary_path_out.write_text(
        json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rts24_flexibility_envelope.yaml"),
    )
    args = parser.parse_args()
    summary = run(args.config)
    print(json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2))
    if not summary["m6_mechanism_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
