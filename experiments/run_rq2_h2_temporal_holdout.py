"""Run chronological RQ2 H2 fixed-policy holdout execution."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import tempfile
from dataclasses import asdict, replace
from pathlib import Path

import yaml

from experiments.run_rq2_l5_economic_temporal_network import (
    _coefficients,
    _derive_temporal_scenarios,
    _envelope,
    _integer,
    _integer_tuple,
    _mapping,
    _number,
    _raw_scenarios,
    _validate_network_selection,
)
from src.evaluation.temporal_economic_holdout import (
    TemporalEconomicHoldoutInputs,
    execute_temporal_economic_holdout,
    plan_temporal_economic_policies,
)
from src.grid import load_rts24
from src.grid.network_grid_need import NETWORK_GRID_NEED_METHODS
from src.scenarios.temporal_scenario_reduction import (
    reduce_temporal_scenarios_fast_forward,
)
from src.scenarios.temporal_trace_scenario_generator import (
    TemporalNetworkScenario,
    TemporalTraceScenarioConfig,
    generate_temporal_holdout_scenarios,
)
from src.scenarios.trace_scenario_generator import (
    load_peak_normalized_shape_from_csv,
)

_ROOT = Path(__file__).resolve().parents[1]
_LEAF_FIELDS = (
    "network_method",
    "policy",
    "holdout_leaf",
    "probability",
    "committed_flexibility_mw",
    "feasible",
    "proven_hard_temporal_failure",
    "solver_unresolved",
    "service_shortfall_failure",
    "right_censored",
    "mw_budget_failure",
    "minimum_event_power_failure",
    "response_or_ramp_failure",
    "duration_failure",
    "event_count_or_rest_failure",
    "energy_failure",
    "recovery_debt_failure",
    "terminal_boundary_failure",
    "physical_violations_json",
    "access_shortfall_mwh",
    "peak_recovery_debt_mwh",
    "terminal_recovery_debt_mwh",
    "terminal_grid_call_mw",
    "terminal_active_event_duration_hours",
    "terminal_interevent_rest_hours",
    "terminal_has_prior_event",
    "maximum_event_duration_hours",
    "event_count_by_period_json",
    "curtailment_energy_mwh_by_period_json",
    "scenario_loss",
    "parameter_status",
    "security_certified",
)


def _strict_bool(raw: object, label: str) -> bool:
    if not isinstance(raw, bool):
        raise TypeError(f"{label} must be boolean")
    return raw


def _path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(raw)
    return path if path.is_absolute() else _ROOT / path


def _write_leaves(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=_LEAF_FIELDS,
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _publish_outputs(
    target: Path,
    *,
    leaves_name: str,
    summary_name: str,
    leaves: list[dict[str, object]],
    summary: dict[str, object],
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"immutable result directory already exists: {target}")
    staging = Path(
        tempfile.mkdtemp(
            dir=target.parent, prefix=f".{target.name}.processing-"
        )
    )
    try:
        leaves_path = staging / leaves_name
        summary_path = staging / summary_name
        _write_leaves(leaves_path, leaves)
        summary_path.write_text(
            json.dumps(
                summary,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        observed_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if observed_summary != summary:
            raise RuntimeError("staged summary round-trip drifted")
        with leaves_path.open(encoding="utf-8", newline="") as handle:
            if len(list(csv.DictReader(handle))) != len(leaves):
                raise RuntimeError("staged leaf table row count drifted")
        manifest = {
            leaves_name: _sha256(leaves_path),
            summary_name: _sha256(summary_path),
        }
        manifest_path = staging / "SHA256SUMS.json"
        manifest_path.write_text(
            json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
        )
        if json.loads(manifest_path.read_text(encoding="utf-8")) != manifest:
            raise RuntimeError("staged manifest round-trip drifted")
        if target.exists():
            raise FileExistsError(
                f"immutable result directory already exists: {target}"
            )
        staging.rename(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _leaf_rows(method: str, result) -> list[dict[str, object]]:
    rows = []
    for policy_name, policy in (
        ("correct", result.correct),
        ("b6", result.b6),
    ):
        for leaf in policy.leaf_outcomes:
            rows.append(
                {
                    "network_method": method,
                    "policy": policy_name,
                    "holdout_leaf": leaf.name,
                    "probability": leaf.probability,
                    "committed_flexibility_mw": (
                        leaf.committed_flexibility_mw
                    ),
                    "feasible": leaf.feasible,
                    "proven_hard_temporal_failure": (
                        leaf.proven_hard_temporal_failure
                    ),
                    "solver_unresolved": leaf.solver_unresolved,
                    "service_shortfall_failure": (
                        leaf.service_shortfall_failure
                    ),
                    "right_censored": leaf.right_censored,
                    "mw_budget_failure": leaf.mw_budget_failure,
                    "minimum_event_power_failure": (
                        leaf.minimum_event_power_failure
                    ),
                    "response_or_ramp_failure": (
                        leaf.response_or_ramp_failure
                    ),
                    "duration_failure": leaf.duration_failure,
                    "event_count_or_rest_failure": (
                        leaf.event_count_or_rest_failure
                    ),
                    "energy_failure": leaf.energy_failure,
                    "recovery_debt_failure": leaf.recovery_debt_failure,
                    "terminal_boundary_failure": (
                        leaf.terminal_boundary_failure
                    ),
                    "physical_violations_json": json.dumps(
                        leaf.physical_violations,
                        separators=(",", ":"),
                    ),
                    "access_shortfall_mwh": leaf.access_shortfall_mwh,
                    "peak_recovery_debt_mwh": (
                        leaf.peak_recovery_debt_mwh
                    ),
                    "terminal_recovery_debt_mwh": (
                        leaf.terminal_recovery_debt_mwh
                    ),
                    "terminal_grid_call_mw": leaf.terminal_grid_call_mw,
                    "terminal_active_event_duration_hours": (
                        leaf.terminal_active_event_duration_hours
                    ),
                    "terminal_interevent_rest_hours": (
                        leaf.terminal_interevent_rest_hours
                    ),
                    "terminal_has_prior_event": leaf.terminal_has_prior_event,
                    "maximum_event_duration_hours": (
                        leaf.maximum_event_duration_hours
                    ),
                    "event_count_by_period_json": json.dumps(
                        leaf.event_count_by_period,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    "curtailment_energy_mwh_by_period_json": json.dumps(
                        leaf.curtailment_energy_mwh_by_period,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    "scenario_loss": leaf.scenario_loss,
                    "parameter_status": result.parameter_status,
                    "security_certified": False,
                }
            )
    return rows


def _policy_summary(policy) -> dict[str, object]:
    raw = asdict(policy)
    raw.pop("leaf_outcomes")
    return raw


def _positive_integer(raw: object, label: str) -> int:
    value = _integer(raw, label)
    if value < 1:
        raise ValueError(f"{label} must be positive")
    return value


def _trace_shape(raw: object, label: str, split_fraction: float):
    block = _mapping(raw, label)
    path = _path(block.get("path"), f"{label}.path")
    column = block.get("column")
    if not isinstance(column, str) or not column:
        raise ValueError(f"{label}.column must be explicit")
    external_peak = block.get("external_peak")
    return load_peak_normalized_shape_from_csv(
        path,
        column=column,
        name=label.rsplit(".", 1)[-1],
        split_fraction=split_fraction if external_peak is None else None,
        external_peak=(
            _number(external_peak, f"{label}.external_peak")
            if external_peak is not None
            else None
        ),
        source=f"{block.get('path')}::{column}::sha256={_sha256(path)}",
    )


def _scenario_to_raw(scenario: TemporalNetworkScenario) -> dict[str, object]:
    return {
        "name": scenario.name,
        "probability": scenario.probability,
        "periods": list(scenario.periods),
        "system_load_multiplier": list(scenario.system_load_multiplier),
        "data_center_demand_mw": list(scenario.data_center_demand_mw),
        "network_call_active": list(scenario.network_call_active),
        "green_call_mw": list(scenario.green_call_mw),
        "connected_demand_mw": list(scenario.connected_demand_mw),
        "recovery_headroom_mw": list(scenario.recovery_headroom_mw),
        "completed_periods": sorted(scenario.completed_periods),
        "require_terminal_event_inactive": (
            scenario.require_terminal_event_inactive
        ),
        "boundary_state_status": scenario.boundary_state_status,
    }


def _generated_temporal_scenarios(raw: object):
    generator = _mapping(raw, "generator")
    status = generator.get("parameter_status")
    if not isinstance(status, str) or not status:
        raise ValueError("generator.parameter_status must be explicit")
    period = generator.get("period")
    if not isinstance(period, str) or not period:
        raise ValueError("generator.period must be explicit")
    split_fraction = _number(
        generator.get("split_fraction"), "generator.split_fraction"
    )
    generated = generate_temporal_holdout_scenarios(
        TemporalTraceScenarioConfig(
            grid_stress_shape=_trace_shape(
                generator.get("grid_stress_shape"),
                "generator.grid_stress_shape",
                split_fraction,
            ),
            green_workload_shape=_trace_shape(
                generator.get("green_workload_shape"),
                "generator.green_workload_shape",
                split_fraction,
            ),
            data_center_demand_mw=_number(
                generator.get("data_center_demand_mw"),
                "generator.data_center_demand_mw",
            ),
            system_load_multiplier=_number(
                generator.get("system_load_multiplier"),
                "generator.system_load_multiplier",
            ),
            green_call_scale_mw=_number(
                generator.get("green_call_scale_mw"),
                "generator.green_call_scale_mw",
            ),
            network_activation_threshold=_number(
                generator.get("network_activation_threshold"),
                "generator.network_activation_threshold",
            ),
            recovery_headroom_mw=_number(
                generator.get("recovery_headroom_mw"),
                "generator.recovery_headroom_mw",
            ),
            core_window_hours=_positive_integer(
                generator.get("core_window_hours"),
                "generator.core_window_hours",
            ),
            recovery_tail_hours=_positive_integer(
                generator.get("recovery_tail_hours"),
                "generator.recovery_tail_hours",
            ),
            n_train=_positive_integer(
                generator.get("n_train"), "generator.n_train"
            ),
            n_holdout=_positive_integer(
                generator.get("n_holdout"), "generator.n_holdout"
            ),
            seed=_integer(generator.get("seed"), "generator.seed"),
            period=period,
            parameter_status=status,
            split_fraction=split_fraction,
        )
    )
    return generated


def _source_scenarios(
    config: dict,
    scenario_source: str,
) -> tuple[
    tuple[dict, ...],
    tuple[dict, ...],
    str,
    str,
    dict[str, object],
]:
    if scenario_source == "manual":
        training = _raw_scenarios(config.get("training_scenarios"))
        holdout = _raw_scenarios(config.get("holdout_scenarios"))
        manual_status = (
            "manual_chronological_scenarios_synthetic_not_empirical"
        )
        training_status = config.get(
            "training_parameter_status", manual_status
        )
        holdout_status = config.get("holdout_parameter_status", manual_status)
        if not isinstance(training_status, str) or not training_status:
            raise ValueError("training_parameter_status must be explicit")
        if not isinstance(holdout_status, str) or not holdout_status:
            raise ValueError("holdout_parameter_status must be explicit")
        return (
            training,
            holdout,
            training_status,
            holdout_status,
            {
                "source": "manual",
                "training_parameter_status": training_status,
                "holdout_parameter_status": holdout_status,
                "reduction": None,
            },
        )
    if scenario_source not in {"generated", "reduced"}:
        raise ValueError(
            "scenario_source must be 'manual', 'generated', or 'reduced'"
        )
    generated = _generated_temporal_scenarios(config.get("generator"))
    training = generated.training_scenarios
    source_status = generated.parameter_status
    reduction_provenance = None
    if scenario_source == "reduced":
        reduction = _mapping(config.get("reduction"), "reduction")
        scales = _mapping(
            reduction.get("component_scales"),
            "reduction.component_scales",
        )
        reduced = reduce_temporal_scenarios_fast_forward(
            training,
            target_count=_positive_integer(
                reduction.get("target_count"), "reduction.target_count"
            ),
            component_scales={
                key: _number(value, f"reduction.component_scales.{key}")
                for key, value in scales.items()
            },
            ground_norm_order=_number(
                reduction.get("ground_norm_order", 2.0),
                "reduction.ground_norm_order",
            ),
            parameter_status=source_status,
        )
        training = reduced.reduced_scenarios
        source_status = reduced.parameter_status
        reduction_provenance = reduced.provenance
    return (
        _raw_scenarios(
            [_scenario_to_raw(scenario) for scenario in training]
        ),
        _raw_scenarios(
            [
                _scenario_to_raw(scenario)
                for scenario in generated.holdout_scenarios
            ]
        ),
        source_status,
        generated.parameter_status,
        {
            "source": scenario_source,
            "training_parameter_status": source_status,
            "holdout_parameter_status": generated.parameter_status,
            "generator": generated.provenance,
            "reduction": reduction_provenance,
        },
    )


def run(config_path: Path) -> dict[str, object]:
    config_bytes = config_path.read_bytes()
    config = _mapping(yaml.safe_load(config_bytes), "config")
    evaluation = _mapping(config.get("evaluation"), "evaluation")
    evaluation_id = evaluation.get("id")
    if not isinstance(evaluation_id, str) or not evaluation_id:
        raise ValueError("evaluation.id must be explicit")
    status = evaluation.get("parameter_status")
    if not isinstance(status, str) or not status:
        raise ValueError("evaluation.parameter_status must be explicit")
    if evaluation.get("security_certified") is not False:
        raise ValueError("security_certified must remain false")
    if evaluation.get("formal_vma_published") is not False:
        raise ValueError("formal_vma_published must remain false")
    scenario_source = config.get("scenario_source")
    if not isinstance(scenario_source, str):
        raise TypeError("scenario_source must be a string")

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
        or len(methods) != len(set(methods))
        or set(methods) - set(NETWORK_GRID_NEED_METHODS)
    ):
        raise ValueError("network.methods must be unique known methods")
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
    solver_name = model.get("solver_name")
    if not isinstance(solver_name, str) or not solver_name:
        raise ValueError("model.solver_name must be explicit")
    envelope = _envelope(config.get("envelope"))
    coefficients = _coefficients(config.get("coefficients"))
    (
        raw_training,
        raw_holdout,
        training_source_status,
        holdout_source_status,
        source_provenance,
    ) = _source_scenarios(config, scenario_source)
    if {item["name"] for item in raw_training} & {
        item["name"] for item in raw_holdout
    }:
        raise ValueError("training and holdout scenario names must be disjoint")

    validation = _mapping(config.get("validation"), "validation")
    fail_on_unresolved = _strict_bool(
        validation.get("fail_closed_on_unresolved"),
        "validation.fail_closed_on_unresolved",
    )
    fail_on_training = _strict_bool(
        validation.get("fail_closed_on_infeasible_training"),
        "validation.fail_closed_on_infeasible_training",
    )
    data = load_rts24()
    _validate_network_selection(
        data,
        poi_bus=poi_bus,
        balancing_bus=balancing_bus,
        branch_indices=branch_indices,
        generator_indices=generator_indices,
        sustained_rating=sustained_rating,
    )

    leaves = []
    method_summaries = {}
    gate_passed = True
    for method in methods:
        training, training_provenance = _derive_temporal_scenarios(
            data=data,
            raw_scenarios=raw_training,
            method=method,
            poi_bus=poi_bus,
            balancing_bus=balancing_bus,
            branch_indices=branch_indices,
            generator_indices=generator_indices,
            redispatch_fraction_of_pmax=redispatch_fraction,
            sustained_rating=sustained_rating,
            solver_name=solver_name,
            parameter_status=(
                f"{status}|{network_status}|{training_source_status}|training"
            ),
        )
        planning_inputs = TemporalEconomicHoldoutInputs(
            training_scenarios=training,
            holdout_scenarios=(),
            envelope=envelope,
            coefficients=coefficients,
            provisioning_cost_per_mw=_number(
                model.get("provisioning_cost_per_mw"),
                "model.provisioning_cost_per_mw",
            ),
            max_flexibility_budget_mw=_number(
                model.get("max_flexibility_budget_mw"),
                "model.max_flexibility_budget_mw",
            ),
            lambda_risk=_number(
                model.get("lambda_risk"), "model.lambda_risk"
            ),
            beta=_number(model.get("beta"), "model.beta"),
            parameter_status=(
                f"{status}|{network_status}|{training_source_status}"
            ),
            service_shortfall_tolerance_mwh=_number(
                model.get("service_shortfall_tolerance_mwh"),
                "model.service_shortfall_tolerance_mwh",
            ),
        )
        plans = plan_temporal_economic_policies(
            planning_inputs, solver_name=solver_name
        )
        holdout, holdout_provenance = _derive_temporal_scenarios(
            data=data,
            raw_scenarios=raw_holdout,
            method=method,
            poi_bus=poi_bus,
            balancing_bus=balancing_bus,
            branch_indices=branch_indices,
            generator_indices=generator_indices,
            redispatch_fraction_of_pmax=redispatch_fraction,
            sustained_rating=sustained_rating,
            solver_name=solver_name,
            parameter_status=(
                f"{status}|{network_status}|{holdout_source_status}|holdout"
            ),
        )
        inputs = replace(
            planning_inputs,
            holdout_scenarios=holdout,
            parameter_status=(
                f"{status}|{network_status}|{holdout_source_status}"
            ),
        )
        result = execute_temporal_economic_holdout(
            inputs, plans, solver_name=solver_name
        )
        unresolved = (
            result.correct.training_solver_unresolved
            or result.b6.training_solver_unresolved
            or result.correct.solver_unresolved_probability > 0.0
            or result.b6.solver_unresolved_probability > 0.0
        )
        training_feasible = (
            result.correct.training_feasible and result.b6.training_feasible
        )
        method_gate = (
            (training_feasible or not fail_on_training)
            and (not unresolved or not fail_on_unresolved)
        )
        gate_passed = gate_passed and method_gate
        leaves.extend(_leaf_rows(method, result))
        method_summaries[method] = {
            "gate_passed": method_gate,
            "training_source_parameter_status": training_source_status,
            "holdout_source_parameter_status": holdout_source_status,
            "correct": _policy_summary(result.correct),
            "b6": _policy_summary(result.b6),
            "h2_evaluated": result.h2_evaluated,
            "b6_extra_failure_probability": (
                result.b6_extra_failure_probability
            ),
            "b6_extra_expected_shortfall_mwh": (
                result.b6_extra_expected_shortfall_mwh
            ),
            "b6_extra_expected_terminal_debt_mwh": (
                result.b6_extra_expected_terminal_debt_mwh
            ),
            "h2_b6_underdelivers_out_of_sample": (
                result.h2_b6_underdelivers_out_of_sample
            ),
            "network_provenance": {
                "training": training_provenance,
                "holdout": holdout_provenance,
            },
        }

    output = _mapping(config.get("output"), "output")
    leaves_path = _path(output.get("leaves_path"), "output.leaves_path")
    summary_path = _path(output.get("summary_path"), "output.summary_path")
    if leaves_path == summary_path:
        raise ValueError("leaves_path and summary_path must differ")
    if leaves_path.parent != summary_path.parent:
        raise ValueError("all outputs must share one immutable result directory")
    if leaves_path.name == "SHA256SUMS.json" or summary_path.name == "SHA256SUMS.json":
        raise ValueError("output filenames must not collide with the manifest")
    summary = {
        "evaluation_id": evaluation_id,
        "scenario_source": scenario_source,
        "scenario_source_provenance": source_provenance,
        "methods": method_summaries,
        "gate_passed": gate_passed,
        "parameter_status": (
            f"{status}|{network_status}|"
            f"training_source={training_source_status}|"
            f"holdout_source={holdout_source_status}|"
            "fixed_policy_temporal_holdout_synthetic_not_empirical"
        ),
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "effective_config": config,
        "security_certified": False,
        "formal_vma_published": False,
        "empirical_holdout_claimed": False,
        "touches_frozen_baselines": False,
        "interpretation": (
            "chronological_fixed_policy_holdout_execution_of_correct_and_b6_"
            "planned_flexibility_against_the_true_shared_temporal_envelope"
        ),
        "certification_blockers": [
            "chronologies_and_probabilities_are_synthetic_or_trace_derived",
            "network_event_timing_is_not_empirical",
            "recovery_headroom_and_envelope_parameters_are_synthetic",
            "selected_n1_dc_not_full_n1_or_ac_security",
        ],
        "output_paths": {
            "leaves": str(leaves_path),
            "summary": str(summary_path),
        },
    }
    summary = json.loads(
        json.dumps(summary, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )
    _publish_outputs(
        leaves_path.parent,
        leaves_name=leaves_path.name,
        summary_name=summary_path.name,
        leaves=leaves,
        summary=summary,
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rq2_h2_temporal_holdout_rts24.yaml"),
    )
    args = parser.parse_args()
    summary = run(args.config)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not summary["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
