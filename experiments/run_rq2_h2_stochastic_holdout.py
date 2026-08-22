"""Run the RQ2 H2 out-of-sample execution of a fixed flexibility policy.

This is the *formal entry point* that drives ``evaluate_economic_holdout`` --
the section-12 scenario-external test for the L5 economic stochastic model. It
plans one flexibility budget ``D^flex`` under the correct shared model and one
under the B6 error baseline on a frozen *training* scenario tree, then executes
each pinned (nonanticipative) policy on a frozen *unseen holdout* tree against
the *true* shared budget, and reports:

* **H2 (concept).** The B6-planned policy under-delivers service out of sample
  by a strictly larger margin than the correctly-planned policy -- a higher
  scenario-external failure probability (hard network-curtailment infeasibility
  plus service shortfall) and/or a larger expected access shortfall -- under the
  *same* inputs, scenarios and security set (agent.md section 9 fairness).

For each policy that is feasible on the holdout tree the reported holdout
service-loss CVaR is cross-checked against a *self-contained* closed-form
recomputation (``_independent_service_cvar``) that shares no code path with the
module's CVaR -- a genuine independent cross-validation, not the same evaluator
re-run on the same inputs. The gate is correctness-only: a CVaR mismatch, or
(when configured) a training plan that is infeasible, makes the entry point fail
closed. H2 itself is a scientific finding -- reported but not gated -- so a
near-zero out-of-sample gap is disclosed honestly rather than tuned away.

Honesty boundaries (agent.md sections 4/8):

* Mechanism-only and synthetic. Every coefficient, budget cap, price and
  scenario probability is a frozen synthetic parameter carried through
  ``parameter_status``; nothing here is a real outage probability, a contract
  capability, an hourly network certification or an engineering/AC result. The
  holdout tree is a synthetic unseen scenario set, not an empirical VMA sample.
* ``security_certified`` is always ``False``. This entry point does not touch
  the frozen B3/B4/B5 baselines or the repair-010 certification chain, and it
  does not start a multi-stage formal long solve. The default config is a tiny
  synthetic case for pipeline/invariant verification; a larger formal case must
  keep the same schema and be tagged/run on the execution machine under user
  authorisation.
* Out-of-sample failure is measured on the MW budget only (access shortfall,
  hard-curtailment infeasibility, service loss). Temporal envelopes (recovery
  debt / maximum duration / event count) remain out of scope, exactly as in the
  L5 model.
"""

from __future__ import annotations

import argparse
import csv
import json
from math import isfinite
from pathlib import Path

import yaml

from src.evaluation.economic_holdout import (
    EconomicHoldoutInputs,
    HoldoutPolicyEvaluation,
    evaluate_economic_holdout,
)
from src.evaluation.service_risk import ServiceLossCoefficients
from src.models import EconomicScenario
from src.scenarios import (
    TraceScenarioConfig,
    generate_holdout_scenarios,
    load_peak_normalized_shape_from_csv,
)


_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

_LEAF_FIELDS = (
    "model_variant",
    "enforce_joint_budget_in_planning",
    "committed_flexibility_mw",
    "holdout_leaf",
    "probability",
    "grid_need_mw",
    "green_call_mw",
    "feasible",
    "hard_security_failure",
    "solver_unresolved",
    "service_shortfall_failure",
    "grid_curtailment_mw",
    "green_shift_mw",
    "permanent_drop_mw",
    "access_shortfall_mw",
    "scenario_loss",
    "parameter_status",
    "security_certified",
)
_POLICY_FIELDS = (
    "model_variant",
    "enforce_joint_budget_in_planning",
    "training_feasible",
    "committed_flexibility_mw",
    "hard_infeasible_probability",
    "service_failure_probability",
    "total_failure_probability",
    "solver_unresolved_probability",
    "expected_access_shortfall_mwh",
    "feasible_leaf_probability",
    "holdout_value_at_risk",
    "holdout_service_cvar",
    "cvar_cross_check_abs_error",
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
        raise ValueError("H2 config must be a YAML mapping")
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


def _build_scenarios(raw: object, label: str) -> tuple[EconomicScenario, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{label} must be a nonempty list")
    scenarios: list[EconomicScenario] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"{label}[{index}] must be a mapping")
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"{label}[{index}].name must be a nonempty string")
        scenarios.append(
            EconomicScenario(
                name=name,
                probability=_number(entry.get("probability"), f"{label}.{name}.probability"),
                grid_need_mw=_nonnegative_number(
                    entry.get("grid_need_mw"), f"{label}.{name}.grid_need_mw"
                ),
                green_call_mw=_nonnegative_number(
                    entry.get("green_call_mw"), f"{label}.{name}.green_call_mw"
                ),
                connected_demand_mw=_nonnegative_number(
                    entry.get("connected_demand_mw"),
                    f"{label}.{name}.connected_demand_mw",
                ),
                hours=_number(entry.get("hours"), f"{label}.{name}.hours"),
            )
        )
    return tuple(scenarios)


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer")
    if value < 1:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _build_generated_scenarios(
    raw: object,
) -> tuple[tuple[EconomicScenario, ...], tuple[EconomicScenario, ...], str, dict]:
    """Build (training, holdout) scenarios from real trace shapes.

    This is the *generator-driven* scenario source: instead of a hand-crafted
    frozen tree, the two demand dimensions are derived from the observed
    AI-workload trace *shapes* the project ships (Google 2019 PDU power ->
    grid-stress ``grid_need_mw``; Alibaba 2020 GPU workload -> green/CFE call
    ``green_call_mw``). Each raw column is peak-normalized *split-aware* (the
    divisor is the training-segment peak, never the full-window peak), so no
    training scenario depends on a holdout hour. The block-bootstrap draw is
    reproducible under ``seed`` and the honesty tag (MW derived, probabilities
    are sampling weights, not empirical outage) is propagated downstream.
    """

    if not isinstance(raw, dict):
        raise ValueError("generator must be a mapping when scenario_source=generated")
    parameter_status = raw.get("parameter_status")
    if not isinstance(parameter_status, str) or not parameter_status:
        raise ValueError("generator.parameter_status must be a nonempty string")

    split_fraction = _number(raw.get("split_fraction", 0.5), "generator.split_fraction")
    window_hours = _positive_int(raw.get("window_hours"), "generator.window_hours")
    n_train = _positive_int(raw.get("n_train"), "generator.n_train")
    n_holdout = _positive_int(raw.get("n_holdout"), "generator.n_holdout")
    seed = _positive_int(raw.get("seed"), "generator.seed")

    def _shape(section: str):
        block = raw.get(section)
        if not isinstance(block, dict):
            raise ValueError(f"generator.{section} must be a mapping")
        external_peak = block.get("external_peak")
        return load_peak_normalized_shape_from_csv(
            _resolve_path(block.get("path")),
            column=str(block.get("column")),
            name=section,
            split_fraction=None if external_peak is not None else split_fraction,
            external_peak=(
                _number(external_peak, f"generator.{section}.external_peak")
                if external_peak is not None
                else None
            ),
        )

    grid_shape = _shape("grid_stress_shape")
    green_shape = _shape("green_workload_shape")

    cfg = TraceScenarioConfig(
        grid_stress_shape=grid_shape,
        green_workload_shape=green_shape,
        grid_stress_scale_mw=_number(
            raw.get("grid_stress_scale_mw"), "generator.grid_stress_scale_mw"
        ),
        green_call_scale_mw=_number(
            raw.get("green_call_scale_mw"), "generator.green_call_scale_mw"
        ),
        connected_demand_mw=_nonnegative_number(
            raw.get("connected_demand_mw"), "generator.connected_demand_mw"
        ),
        window_hours=window_hours,
        n_train=n_train,
        n_holdout=n_holdout,
        seed=seed,
        parameter_status=parameter_status,
        split_fraction=split_fraction,
    )
    generated = generate_holdout_scenarios(cfg)
    return (
        generated.training_scenarios,
        generated.holdout_scenarios,
        generated.parameter_status,
        generated.provenance,
    )


def _independent_service_cvar(
    losses: list[tuple[float, float]],
    beta: float,
) -> float:
    """Closed-form beta-CVaR of a discrete loss distribution, computed here
    from scratch so it shares no code path with the module under test.

    ``losses`` is a list of ``(loss, probability)`` pairs. This is the
    Rockafellar-Uryasev evaluation

        VaR_beta = min { l : sum_{L <= l} p >= beta },
        CVaR_beta = VaR_beta + 1 / (1 - beta) * sum_omega p_omega (L_omega - VaR)^+,

    deliberately re-derived rather than delegated to ``evaluate_service_cvar``,
    so a bug shared between the module and its evaluator cannot pass unnoticed.
    """

    probability_by_loss: dict[float, float] = {}
    for loss, probability in losses:
        probability_by_loss[loss] = probability_by_loss.get(loss, 0.0) + probability
    distinct = sorted(probability_by_loss)
    cumulative = 0.0
    var = distinct[-1]
    for candidate in distinct:
        cumulative += probability_by_loss[candidate]
        if cumulative >= beta - 1.0e-9:
            var = candidate
            break
    tail = sum(
        probability * max(loss - var, 0.0) for loss, probability in losses
    )
    return var + tail / (1.0 - beta)


def _cross_check_policy_cvar(
    inputs: EconomicHoldoutInputs,
    policy: HoldoutPolicyEvaluation,
) -> float | None:
    """Recompute the holdout service-loss CVaR from the executed dispatch with a
    self-contained closed form and return the absolute difference against the
    module's reported value.

    Defined only when the module reported a CVaR (all holdout leaves feasible).
    The per-scenario losses are recomputed directly from the dispatch energies
    and the loss coefficients (``kappa * energy``), and the CVaR is evaluated by
    ``_independent_service_cvar`` -- neither step calls ``evaluate_service_cvar``,
    so the check is a genuine independent cross-validation rather than the same
    function re-run on the same inputs (R3 finding 3). A hard-security leaf
    failure leaves the service-loss CVaR undefined, so the check is skipped there
    and the hard-failure probability carries the tail signal instead."""

    if policy.holdout_service_cvar is None:
        return None
    coeff = inputs.coefficients
    holdout = {s.name: s for s in inputs.holdout_scenarios}
    losses: list[tuple[float, float]] = []
    for outcome in policy.leaf_outcomes:
        hours = holdout[outcome.name].hours
        loss = hours * (
            coeff.kappa_access * (outcome.access_shortfall_mw or 0.0)
            + coeff.kappa_grid * (outcome.grid_curtailment_mw or 0.0)
            + coeff.kappa_green * (outcome.green_shift_mw or 0.0)
            + coeff.kappa_drop * (outcome.permanent_drop_mw or 0.0)
        )
        losses.append((loss, outcome.probability))
    independent_cvar = _independent_service_cvar(losses, inputs.beta)
    return abs(independent_cvar - policy.holdout_service_cvar)


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


def _leaf_rows(
    inputs: EconomicHoldoutInputs,
    policy: HoldoutPolicyEvaluation,
    parameter_status: str,
) -> list[dict[str, object]]:
    holdout = {s.name: s for s in inputs.holdout_scenarios}
    rows: list[dict[str, object]] = []
    for outcome in policy.leaf_outcomes:
        leaf = holdout[outcome.name]
        rows.append(
            {
                "model_variant": policy.variant,
                "enforce_joint_budget_in_planning": (
                    policy.enforce_joint_budget_in_planning
                ),
                "committed_flexibility_mw": policy.committed_flexibility_mw,
                "holdout_leaf": outcome.name,
                "probability": outcome.probability,
                "grid_need_mw": leaf.grid_need_mw,
                "green_call_mw": leaf.green_call_mw,
                "feasible": outcome.feasible,
                "hard_security_failure": outcome.hard_security_failure,
                "solver_unresolved": outcome.solver_unresolved,
                "service_shortfall_failure": outcome.service_shortfall_failure,
                "grid_curtailment_mw": outcome.grid_curtailment_mw,
                "green_shift_mw": outcome.green_shift_mw,
                "permanent_drop_mw": outcome.permanent_drop_mw,
                "access_shortfall_mw": outcome.access_shortfall_mw,
                "scenario_loss": outcome.scenario_loss,
                "parameter_status": parameter_status,
                "security_certified": False,
            }
        )
    return rows


def _policy_row(
    policy: HoldoutPolicyEvaluation,
    cross_check_error: float | None,
    parameter_status: str,
) -> dict[str, object]:
    return {
        "model_variant": policy.variant,
        "enforce_joint_budget_in_planning": policy.enforce_joint_budget_in_planning,
        "training_feasible": policy.training_feasible,
        "committed_flexibility_mw": policy.committed_flexibility_mw,
        "hard_infeasible_probability": policy.hard_infeasible_probability,
        "service_failure_probability": policy.service_failure_probability,
        "total_failure_probability": policy.total_failure_probability,
        "solver_unresolved_probability": policy.solver_unresolved_probability,
        "expected_access_shortfall_mwh": policy.expected_access_shortfall_mwh,
        "feasible_leaf_probability": policy.feasible_leaf_probability,
        "holdout_value_at_risk": policy.holdout_value_at_risk,
        "holdout_service_cvar": policy.holdout_service_cvar,
        "cvar_cross_check_abs_error": cross_check_error,
        "parameter_status": parameter_status,
        "security_certified": False,
    }


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
        evaluation.get("formal_vma_published", False),
        "formal_vma_published",
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
    lambda_risk = _nonnegative_number(model.get("lambda_risk"), "lambda_risk")
    beta = _number(model.get("beta"), "beta")
    if not 0.0 <= beta < 1.0:
        raise ValueError("beta must lie in [0, 1)")
    shortfall_tolerance = _nonnegative_number(
        model.get("service_shortfall_tolerance_mw", 1.0e-6),
        "service_shortfall_tolerance_mw",
    )
    solver_name = model.get("solver_name")
    if not isinstance(solver_name, str) or not solver_name:
        raise ValueError("model.solver_name must be a nonempty string")

    coefficients = _build_coefficients(config.get("coefficients"))

    # Scenario source: hand-crafted frozen tree (default, backward compatible) or
    # the data-driven generator that derives scenarios from real trace shapes.
    # ``generated`` mode also *augments* the evaluation status with the
    # generator's honesty tag (MW derived, probabilities are sampling weights),
    # so no downstream artifact can mistake generated scenarios for empirical
    # evidence (agent.md sections 4/8).
    scenario_source = config.get("scenario_source", "manual")
    if scenario_source not in ("manual", "generated"):
        raise ValueError("scenario_source must be 'manual' or 'generated'")
    generator_provenance: dict | None = None
    if scenario_source == "generated":
        (
            training_scenarios,
            holdout_scenarios,
            generated_status,
            generator_provenance,
        ) = _build_generated_scenarios(config.get("generator"))
        parameter_status = f"{parameter_status}::{generated_status}"
    else:
        training_scenarios = _build_scenarios(
            config.get("training_scenarios"), "training_scenarios"
        )
        holdout_scenarios = _build_scenarios(
            config.get("holdout_scenarios"), "holdout_scenarios"
        )

    validation = config.get("validation") or {}
    if not isinstance(validation, dict):
        raise ValueError("config.validation must be a mapping")
    cvar_tolerance = _nonnegative_number(
        validation.get("cvar_cross_check_tolerance", 1.0e-6),
        "cvar_cross_check_tolerance",
    )
    fail_closed_on_infeasible_training = _strict_bool(
        validation.get("fail_closed_on_infeasible_training", True),
        "fail_closed_on_infeasible_training",
    )

    output = config.get("output")
    if not isinstance(output, dict):
        raise ValueError("config.output must be a mapping")
    leaves_path = _resolve_path(output.get("leaves_path"))
    policies_path = _resolve_path(output.get("policies_path"))
    summary_path = _resolve_path(output.get("summary_path"))

    inputs = EconomicHoldoutInputs(
        training_scenarios=training_scenarios,
        holdout_scenarios=holdout_scenarios,
        coefficients=coefficients,
        provisioning_cost_per_mw=provisioning_cost,
        max_flexibility_budget_mw=max_budget,
        lambda_risk=lambda_risk,
        beta=beta,
        parameter_status=parameter_status,
        service_shortfall_tolerance_mw=shortfall_tolerance,
    )
    result = evaluate_economic_holdout(inputs, solver_name=solver_name)

    # --- Correctness gate: CVaR cross-check + (optional) training feasibility -
    max_cross_check_error = 0.0
    leaf_rows: list[dict[str, object]] = []
    policy_rows: list[dict[str, object]] = []
    for policy in (result.correct, result.b6):
        cross_check_error = _cross_check_policy_cvar(inputs, policy)
        if cross_check_error is not None:
            max_cross_check_error = max(max_cross_check_error, cross_check_error)
        leaf_rows.extend(_leaf_rows(inputs, policy, parameter_status))
        policy_rows.append(
            _policy_row(policy, cross_check_error, parameter_status)
        )

    cvar_cross_check_passed = max_cross_check_error <= cvar_tolerance
    training_feasible = (
        result.correct.training_feasible and result.b6.training_feasible
    )
    gate_passed = cvar_cross_check_passed and (
        training_feasible or not fail_closed_on_infeasible_training
    )

    _write_csv(leaves_path, _LEAF_FIELDS, leaf_rows)
    _write_csv(policies_path, _POLICY_FIELDS, policy_rows)

    summary = {
        "evaluation_id": evaluation_id,
        "role": evaluation.get("role"),
        "parameter_status": parameter_status,
        "scenario_source": scenario_source,
        "generator_provenance": generator_provenance,
        "risk_measure_scope": result.risk_measure_scope,
        "solver_name": solver_name,
        "beta": beta,
        "lambda_risk": lambda_risk,
        "max_flexibility_budget_mw": max_budget,
        "provisioning_cost_per_mw": provisioning_cost,
        "service_shortfall_tolerance_mw": shortfall_tolerance,
        "training_scenario_count": len(training_scenarios),
        "holdout_scenario_count": len(holdout_scenarios),
        "training_scenarios": [
            {"name": s.name, "probability": s.probability}
            for s in training_scenarios
        ],
        "holdout_scenarios": [
            {"name": s.name, "probability": s.probability}
            for s in holdout_scenarios
        ],
        "cvar_cross_check_tolerance": cvar_tolerance,
        "cvar_cross_check_max_abs_error": max_cross_check_error,
        "cvar_cross_check_passed": cvar_cross_check_passed,
        "training_feasible": training_feasible,
        "gate_passed": gate_passed,
        "correct_policy": {
            "committed_flexibility_mw": result.correct.committed_flexibility_mw,
            "total_failure_probability": result.correct.total_failure_probability,
            "hard_infeasible_probability": (
                result.correct.hard_infeasible_probability
            ),
            "service_failure_probability": (
                result.correct.service_failure_probability
            ),
            "solver_unresolved_probability": (
                result.correct.solver_unresolved_probability
            ),
            "expected_access_shortfall_mwh": (
                result.correct.expected_access_shortfall_mwh
            ),
            "holdout_service_cvar": result.correct.holdout_service_cvar,
        },
        "b6_policy": {
            "committed_flexibility_mw": result.b6.committed_flexibility_mw,
            "total_failure_probability": result.b6.total_failure_probability,
            "hard_infeasible_probability": result.b6.hard_infeasible_probability,
            "service_failure_probability": result.b6.service_failure_probability,
            "solver_unresolved_probability": (
                result.b6.solver_unresolved_probability
            ),
            "expected_access_shortfall_mwh": (
                result.b6.expected_access_shortfall_mwh
            ),
            "holdout_service_cvar": result.b6.holdout_service_cvar,
        },
        "h2_evaluated": result.h2_evaluated,
        "h2_b6_extra_failure_probability": result.b6_extra_failure_probability,
        "h2_b6_extra_expected_shortfall_mwh": (
            result.b6_extra_expected_shortfall_mwh
        ),
        "h2_b6_underdelivers_out_of_sample": (
            result.h2_b6_underdelivers_out_of_sample
        ),
        "random_seed": config.get("random_seed"),
        # Honesty gates (agent.md sections 4/8): scenario-external mechanism
        # evidence only, never an engineering / contract / empirical-VMA result.
        "security_certified": False,
        "formal_vma_published": False,
        "empirical_holdout_claimed": False,
        "touches_frozen_baselines": False,
        "interpretation": (
            "synthetic_out_of_sample_fixed_policy_execution_showing_the_b6_"
            "double_counting_error_underdelivers_service_against_the_true_shared_"
            "budget_not_an_empirical_vma_or_engineering_certification"
        ),
        "certification_blockers": [
            "synthetic_coefficients_budget_cap_and_scenario_probabilities_not_"
            "empirical",
            "holdout_tree_is_a_synthetic_unseen_scenario_set_not_an_empirical_"
            "vma_sample",
            "temporal_envelopes_recovery_debt_duration_event_count_out_of_scope",
            "no_ac_or_n1_network_certification_in_this_entry_point",
        ],
        "output_paths": {
            "leaves": str(leaves_path),
            "policies": str(policies_path),
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
        default=Path("configs/rq2_h2_stochastic_holdout.yaml"),
    )
    args = parser.parse_args()
    summary = run(args.config)
    print(json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2))
    if not summary["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
