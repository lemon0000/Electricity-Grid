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
            handle, fieldnames=_LEAF_FIELDS, extrasaction="raise"
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
    if scenario_source != "manual":
        raise ValueError(
            "temporal H2 currently supports only manual chronological "
            "scenarios; scalar generated/reduced scenarios cannot be promoted "
            "to temporal evidence"
        )

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
    raw_training = _raw_scenarios(config.get("training_scenarios"))
    raw_holdout = _raw_scenarios(config.get("holdout_scenarios"))
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
            parameter_status=f"{status}|{network_status}|training",
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
            parameter_status=f"{status}|{network_status}",
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
            parameter_status=f"{status}|{network_status}|holdout",
        )
        inputs = replace(
            planning_inputs, holdout_scenarios=holdout
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
        "methods": method_summaries,
        "gate_passed": gate_passed,
        "parameter_status": (
            f"{status}|{network_status}|fixed_policy_temporal_holdout_"
            "synthetic_not_empirical"
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
            "manual_chronologies_and_probabilities_are_synthetic",
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
