"""Run the RQ2 L5 economic stochastic model (formulation.md sections 12-14).

This is the *formal entry point* that drives ``solve_economic_stochastic`` --
the L5 model that wires the section 10.1 shared MW flexibility budget and the
section 13 service-loss CVaR into the single section 14 economic objective

    min C^grid + C^op + lambda^risk * CVaR_beta(L).

For a frozen synthetic scenario tree it sweeps ``lambda^risk`` over the
correct shared-budget model and the B6 error baseline (which splits the
budget) and produces two falsifiable pieces of evidence under the *same*
inputs / scenarios / budget cap (agent.md section 9 fairness):

* **H1 (mechanism)** -- at the reference ``lambda`` the B6 error baseline
  provisions strictly less flexibility than the correct shared model for the
  same demands, because splitting the budget lets network curtailment and the
  green/CFE call each draw on the full ``D^flex`` independently. The gap
  ``D^flex_correct - D^flex_B6`` is the provisioning that B6 double-counts away
  (the ``X`` overestimation quantity).
* **H3 (evaluation)** -- along the frozen ``lambda`` grid the correct model's
  tail service loss ``CVaR_beta(L)`` is non-increasing while its expected
  planning cost ``C^grid + C^op`` is non-decreasing, i.e. a monotone
  cost <-> tail-risk trade-off rather than a single-weight artefact.

Every reported CVaR is cross-checked against the independent section 13
``evaluate_service_cvar`` recomputed from the realised dispatch; a mismatch or
(when configured) any infeasible run makes the entry point fail closed.

Honesty boundaries (agent.md sections 4/8):

* Mechanism-only and synthetic. Every coefficient, budget cap, price and
  scenario probability is a frozen synthetic parameter carried through
  ``parameter_status``; nothing here is a real outage probability, a contract
  capability, an hourly network certification or an engineering/AC result.
* ``security_certified`` is always ``False``. This entry point does not touch
  the frozen B3/B4/B5 baselines or the repair-010 certification chain, and it
  does not start a multi-stage formal long solve. The default config is a tiny
  synthetic case for pipeline/invariant verification; a larger formal case must
  keep the same schema and be tagged/run on the execution machine under user
  authorisation.
"""

from __future__ import annotations

import argparse
import csv
import json
from math import isfinite
from pathlib import Path

import yaml

from src.evaluation.service_risk import (
    ScenarioServiceLoss,
    ServiceLossCoefficients,
    evaluate_service_cvar,
)
from src.models import (
    EconomicScenario,
    EconomicStochasticInputs,
    solve_economic_stochastic,
)


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

_CORRECT_VARIANT = "correct_shared_budget"
_B6_VARIANT = "b6_error_split_budget"
_VARIANTS = (_CORRECT_VARIANT, _B6_VARIANT)

_RUN_FIELDS = (
    "model_variant",
    "enforce_joint_budget",
    "lambda_risk",
    "beta",
    "feasible",
    "termination_condition",
    "provisioned_flexibility_mw",
    "expansion_cost",
    "expected_operating_cost",
    "expected_planning_cost",
    "value_at_risk",
    "conditional_value_at_risk",
    "cvar_cross_check_abs_error",
    "objective",
    "parameter_status",
    "security_certified",
)
_FRONTIER_FIELDS = (
    "lambda_risk",
    "beta",
    "expected_planning_cost",
    "conditional_value_at_risk",
    "value_at_risk",
    "provisioned_flexibility_mw",
    "parameter_status",
    "security_certified",
)


def _resolve_path(configured: object) -> Path:
    path = Path(str(configured))
    return path if path.is_absolute() else _REPOSITORY_ROOT / path


def _number(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric, not boolean")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _nonnegative_number(value: object, label: str) -> float:
    number = _number(value, label)
    if number < 0.0:
        raise ValueError(f"{label} must be nonnegative")
    return number


def _strict_bool(value: object, label: str) -> bool:
    if value in (True, "True"):
        return True
    if value in (False, "False"):
        return False
    raise ValueError(f"{label} must be True or False")


def _require_uncertified(value: object, label: str) -> None:
    if _strict_bool(value, label) is not False:
        raise ValueError(f"{label} must be false: this entry point never certifies")


def _load_config(config_path: Path) -> dict[str, object]:
    parsed = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError("L5 config must be a YAML mapping")
    return parsed


def _build_coefficients(raw: object) -> ServiceLossCoefficients:
    if not isinstance(raw, dict):
        raise ValueError("coefficients must be a mapping")
    parameter_status = raw.get("parameter_status")
    if not isinstance(parameter_status, str) or not parameter_status:
        raise ValueError("coefficients.parameter_status must be a nonempty string")
    return ServiceLossCoefficients(
        kappa_access=_nonnegative_number(raw.get("kappa_access"), "kappa_access"),
        kappa_grid=_nonnegative_number(raw.get("kappa_grid"), "kappa_grid"),
        kappa_green=_nonnegative_number(raw.get("kappa_green"), "kappa_green"),
        kappa_drop=_nonnegative_number(raw.get("kappa_drop"), "kappa_drop"),
        kappa_breach_firm=_nonnegative_number(
            raw.get("kappa_breach_firm"), "kappa_breach_firm"
        ),
        kappa_breach_conditional=_nonnegative_number(
            raw.get("kappa_breach_conditional"), "kappa_breach_conditional"
        ),
        parameter_status=parameter_status,
    )


def _build_scenarios(raw: object) -> tuple[EconomicScenario, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("scenarios must be a nonempty list")
    scenarios: list[EconomicScenario] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"scenario[{index}] must be a mapping")
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"scenario[{index}].name must be a nonempty string")
        scenarios.append(
            EconomicScenario(
                name=name,
                probability=_number(entry.get("probability"), f"{name}.probability"),
                grid_need_mw=_nonnegative_number(
                    entry.get("grid_need_mw"), f"{name}.grid_need_mw"
                ),
                green_call_mw=_nonnegative_number(
                    entry.get("green_call_mw"), f"{name}.green_call_mw"
                ),
                connected_demand_mw=_nonnegative_number(
                    entry.get("connected_demand_mw"), f"{name}.connected_demand_mw"
                ),
                hours=_number(entry.get("hours"), f"{name}.hours"),
            )
        )
    return tuple(scenarios)


def _build_lambda_sweep(raw: object) -> tuple[float, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("lambda_sweep must be a nonempty list")
    sweep = tuple(
        _nonnegative_number(value, f"lambda_sweep[{index}]")
        for index, value in enumerate(raw)
    )
    if any(later < earlier for earlier, later in zip(sweep, sweep[1:])):
        raise ValueError("lambda_sweep must be non-decreasing (frozen before results)")
    if len(set(sweep)) != len(sweep):
        raise ValueError("lambda_sweep must not contain duplicates")
    return sweep


def _cross_check_cvar(
    inputs: EconomicStochasticInputs,
    dispatch: dict[str, object],
) -> float:
    """Recompute the section 13 CVaR from the realised dispatch and return the
    absolute difference against the L5 model's reported CVaR. The energies fold
    in ``hours`` exactly as ``economic_stochastic`` does, so an inconsistency is
    a correctness bug rather than a modelling choice."""

    loss_scenarios = []
    for scenario in inputs.scenarios:
        realised = dispatch[scenario.name]
        loss_scenarios.append(
            ScenarioServiceLoss(
                name=scenario.name,
                probability=scenario.probability,
                access_shortfall_mwh=realised.access_shortfall_mw * scenario.hours,
                grid_curtailment_mwh=realised.grid_curtailment_mw * scenario.hours,
                green_shift_mwh=realised.green_shift_mw * scenario.hours,
                permanent_drop_mwh=realised.permanent_drop_mw * scenario.hours,
                firm_breach_mwh=0.0,
                conditional_breach_mwh=0.0,
            )
        )
    independent = evaluate_service_cvar(
        loss_scenarios, inputs.coefficients, beta=inputs.beta
    )
    return independent.conditional_value_at_risk


def _write_csv(
    path: Path,
    fields: tuple[str, ...],
    rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def run(config_path: Path) -> dict[str, object]:
    config = _load_config(config_path)

    evaluation = config.get("evaluation")
    if not isinstance(evaluation, dict):
        raise ValueError("config.evaluation must be a mapping")
    evaluation_id = evaluation.get("id")
    if not isinstance(evaluation_id, str) or not evaluation_id:
        raise ValueError("evaluation.id must be a nonempty string")
    parameter_status = evaluation.get("parameter_status")
    if not isinstance(parameter_status, str) or not parameter_status:
        raise ValueError("evaluation.parameter_status must be a nonempty string")
    _require_uncertified(evaluation.get("security_certified"), "security_certified")
    _require_uncertified(
        evaluation.get("formal_economic_optimum_published", False),
        "formal_economic_optimum_published",
    )

    model = config.get("model")
    if not isinstance(model, dict):
        raise ValueError("config.model must be a mapping")
    max_budget = _nonnegative_number(
        model.get("max_flexibility_budget_mw"), "max_flexibility_budget_mw"
    )
    provisioning_cost = _nonnegative_number(
        model.get("provisioning_cost_per_mw"), "provisioning_cost_per_mw"
    )
    beta = _number(model.get("beta"), "beta")
    if not 0.0 <= beta < 1.0:
        raise ValueError("beta must lie in [0, 1)")
    solver_name = model.get("solver_name")
    if not isinstance(solver_name, str) or not solver_name:
        raise ValueError("model.solver_name must be a nonempty string")

    coefficients = _build_coefficients(config.get("coefficients"))
    scenarios = _build_scenarios(config.get("scenarios"))
    lambda_sweep = _build_lambda_sweep(config.get("lambda_sweep"))

    validation = config.get("validation") or {}
    if not isinstance(validation, dict):
        raise ValueError("config.validation must be a mapping")
    cvar_tolerance = _nonnegative_number(
        validation.get("cvar_cross_check_tolerance", 1.0e-6),
        "cvar_cross_check_tolerance",
    )
    fail_closed_on_infeasible = _strict_bool(
        validation.get("fail_closed_on_infeasible_run", True),
        "fail_closed_on_infeasible_run",
    )

    output = config.get("output")
    if not isinstance(output, dict):
        raise ValueError("config.output must be a mapping")
    runs_path = _resolve_path(output.get("runs_path"))
    frontier_path = _resolve_path(output.get("frontier_path"))
    summary_path = _resolve_path(output.get("summary_path"))

    # --- Sweep lambda over both the correct and the B6 models -------------
    run_rows: list[dict[str, object]] = []
    frontier_rows: list[dict[str, object]] = []
    # Keyed lookups so the H1/H3 gates read the exact numeric result rather
    # than re-deriving it from the CSV strings.
    results_by_key: dict[tuple[str, float], dict[str, object]] = {}
    all_feasible = True
    max_cross_check_error = 0.0

    for lambda_risk in lambda_sweep:
        for variant in _VARIANTS:
            enforce_joint = variant == _CORRECT_VARIANT
            inputs = EconomicStochasticInputs(
                scenarios=scenarios,
                coefficients=coefficients,
                provisioning_cost_per_mw=provisioning_cost,
                max_flexibility_budget_mw=max_budget,
                lambda_risk=lambda_risk,
                beta=beta,
                enforce_joint_budget=enforce_joint,
                parameter_status=parameter_status,
            )
            result = solve_economic_stochastic(inputs, solver_name=solver_name)

            cross_check_error: float | None = None
            expected_planning_cost: float | None = None
            if result.feasible:
                independent_cvar = _cross_check_cvar(inputs, result.scenario_dispatch)
                cross_check_error = abs(
                    independent_cvar - result.conditional_value_at_risk
                )
                max_cross_check_error = max(max_cross_check_error, cross_check_error)
                expected_planning_cost = (
                    result.expansion_cost + result.expected_operating_cost
                )
            else:
                all_feasible = False

            row = {
                "model_variant": variant,
                "enforce_joint_budget": enforce_joint,
                "lambda_risk": lambda_risk,
                "beta": beta,
                "feasible": result.feasible,
                "termination_condition": result.termination_condition,
                "provisioned_flexibility_mw": result.provisioned_flexibility_mw,
                "expansion_cost": result.expansion_cost,
                "expected_operating_cost": result.expected_operating_cost,
                "expected_planning_cost": expected_planning_cost,
                "value_at_risk": result.value_at_risk,
                "conditional_value_at_risk": result.conditional_value_at_risk,
                "cvar_cross_check_abs_error": cross_check_error,
                "objective": result.objective,
                "parameter_status": parameter_status,
                "security_certified": False,
            }
            run_rows.append(row)
            results_by_key[(variant, lambda_risk)] = row

            if variant == _CORRECT_VARIANT:
                frontier_rows.append(
                    {
                        "lambda_risk": lambda_risk,
                        "beta": beta,
                        "expected_planning_cost": expected_planning_cost,
                        "conditional_value_at_risk": result.conditional_value_at_risk,
                        "value_at_risk": result.value_at_risk,
                        "provisioned_flexibility_mw": result.provisioned_flexibility_mw,
                        "parameter_status": parameter_status,
                        "security_certified": False,
                    }
                )

    cvar_cross_check_passed = max_cross_check_error <= cvar_tolerance

    # --- H1: reference-lambda provisioning gap (correct vs B6) ------------
    reference_lambda = lambda_sweep[0]
    correct_ref = results_by_key[(_CORRECT_VARIANT, reference_lambda)]
    b6_ref = results_by_key[(_B6_VARIANT, reference_lambda)]
    h1_evaluated = bool(correct_ref["feasible"] and b6_ref["feasible"])
    h1_overestimation_mw: float | None = None
    h1_positive = False
    if h1_evaluated:
        h1_overestimation_mw = (
            correct_ref["provisioned_flexibility_mw"]
            - b6_ref["provisioned_flexibility_mw"]
        )
        h1_positive = h1_overestimation_mw > 1.0e-6

    # --- H3: monotone cost <-> tail-risk trade-off on the correct model ---
    feasible_frontier = [
        row for row in frontier_rows if row["conditional_value_at_risk"] is not None
    ]
    h3_evaluated = len(feasible_frontier) == len(frontier_rows) and (
        len(feasible_frontier) >= 2
    )
    monotone_tolerance = 1.0e-6
    cvar_non_increasing = all(
        later["conditional_value_at_risk"]
        <= earlier["conditional_value_at_risk"] + monotone_tolerance
        for earlier, later in zip(feasible_frontier, feasible_frontier[1:])
    )
    cost_non_decreasing = all(
        later["expected_planning_cost"]
        >= earlier["expected_planning_cost"] - monotone_tolerance
        for earlier, later in zip(feasible_frontier, feasible_frontier[1:])
    )
    h3_monotone_tradeoff = h3_evaluated and cvar_non_increasing and cost_non_decreasing

    # The pipeline gate is correctness-only: CVaR consistency and (optionally)
    # feasibility. H1/H3 are scientific findings, reported but not gated, so a
    # near-zero overestimation or a flat frontier is disclosed honestly rather
    # than tuned away (agent.md section 9 fairness).
    gate_passed = cvar_cross_check_passed and (
        all_feasible or not fail_closed_on_infeasible
    )

    _write_csv(runs_path, _RUN_FIELDS, run_rows)
    _write_csv(frontier_path, _FRONTIER_FIELDS, frontier_rows)

    summary = {
        "evaluation_id": evaluation_id,
        "role": evaluation.get("role"),
        "parameter_status": parameter_status,
        "risk_measure_scope": (
            "synthetic_mechanism_only_shared_budget_and_service_cvar"
        ),
        "solver_name": solver_name,
        "beta": beta,
        "max_flexibility_budget_mw": max_budget,
        "provisioning_cost_per_mw": provisioning_cost,
        "lambda_sweep": list(lambda_sweep),
        "scenario_count": len(scenarios),
        "scenarios": [
            {"name": s.name, "probability": s.probability} for s in scenarios
        ],
        "run_count": len(run_rows),
        "all_runs_feasible": all_feasible,
        "cvar_cross_check_tolerance": cvar_tolerance,
        "cvar_cross_check_max_abs_error": max_cross_check_error,
        "cvar_cross_check_passed": cvar_cross_check_passed,
        "gate_passed": gate_passed,
        "h1_reference_lambda": reference_lambda,
        "h1_evaluated": h1_evaluated,
        "h1_overestimation_mw": h1_overestimation_mw,
        "h1_shared_budget_rejects_b6_overprovision": h1_positive,
        "h3_evaluated": h3_evaluated,
        "h3_cvar_non_increasing": cvar_non_increasing if h3_evaluated else None,
        "h3_expected_cost_non_decreasing": (
            cost_non_decreasing if h3_evaluated else None
        ),
        "h3_monotone_cost_tail_risk_tradeoff": h3_monotone_tradeoff,
        "frontier": [
            {
                "lambda_risk": row["lambda_risk"],
                "expected_planning_cost": row["expected_planning_cost"],
                "conditional_value_at_risk": row["conditional_value_at_risk"],
                "provisioned_flexibility_mw": row["provisioned_flexibility_mw"],
            }
            for row in frontier_rows
        ],
        "random_seed": config.get("random_seed"),
        # Honesty gates (agent.md sections 4/8): mechanism/sensitivity evidence
        # only, never an engineering / contract / economic-optimum certification.
        "security_certified": False,
        "formal_economic_optimum_published": False,
        "formal_vma_published": False,
        "economic_optimum_claimed": False,
        "touches_frozen_baselines": False,
        "interpretation": (
            "synthetic_shared_budget_and_service_cvar_economic_mechanism_and_"
            "sensitivity_evidence_not_engineering_contract_or_economic_optimum_"
            "certification"
        ),
        "certification_blockers": [
            "synthetic_coefficients_budget_cap_and_scenario_probabilities_not_"
            "empirical",
            "temporal_envelopes_recovery_debt_duration_event_count_out_of_scope",
            "no_ac_or_n1_network_certification_in_this_entry_point",
        ],
        "output_paths": {
            "runs": str(runs_path),
            "frontier": str(frontier_path),
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
        default=Path("configs/rq2_l5_economic_stochastic.yaml"),
    )
    args = parser.parse_args()
    summary = run(args.config)
    print(json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2))
    if not summary["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
