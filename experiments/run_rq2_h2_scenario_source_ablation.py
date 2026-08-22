"""RQ2 H2 scenario-source ablation: is the out-of-sample result an artifact of
how the training scenarios were built? (agent.md sections 4/8/9)

Why this entry point exists
--------------------------
``run_rq2_h2_stochastic_holdout`` answers *whether* a B6 (double-counting)
flexibility policy under-delivers service out of sample. The obvious reviewer
attack is that the finding is an artifact of the *particular* training tree --
"you drew scenarios that make B6 look bad". This entry point is the controlled
answer: it holds the **holdout test set fixed** and varies **only the training
scenario source**, then reports whether the H2 conclusion (B6 under-delivers out
of sample) survives every source. Because the treatment is a single knob (the
training distribution) and everything downstream -- the unseen holdout leaves,
the coefficients, the budget cap, the security set, the solver -- is identical
across arms, a stable H2 sign is attributable to the mechanism, not the draw
(agent.md section 9 fairness).

Three training-source arms, one shared holdout
---------------------------------------------
* ``manual`` -- the hand-crafted frozen training tree (the original design).
* ``generated`` -- training scenarios derived from the real AI-workload trace
  shapes, split-aware peak-normalized (Google 2019 PDU power -> grid stress,
  Alibaba 2020 GPU workload -> green/CFE call). Same generator as the H2 runner.
* ``reduced`` -- the *same* generated training scenarios thinned by classic
  fast-forward scenario reduction (optimal order-1 Kantorovich redistribution).
  A pure probability-mass transformation of the generated *training* tree; the
  holdout is never reduced.

Every arm is planned (correct and B6) and executed on the **one** shared
holdout tree, so the arms differ only in what the policies were planned on.

Gate and honesty (agent.md sections 4/7/8)
------------------------------------------
* Correctness-only gate. For every feasible policy in every arm the reported
  holdout service-loss CVaR is cross-checked against the self-contained
  closed-form recomputation reused from the H2 runner (a genuinely independent
  cross-validation). A CVaR mismatch, or (when configured) an infeasible
  training plan, fails the gate closed. H2 robustness itself is a *scientific
  finding* -- reported per arm and aggregated, never gated -- so a source that
  weakens the gap is disclosed honestly rather than dropped.
* ``security_certified`` is always ``False``. This entry point does not touch
  the frozen B3/B4/B5 baselines or any certification chain and starts no formal
  long solve. Every MW is a synthetic mechanism quantity or a trace-derived
  quantity carried through ``parameter_status``; the generated/reduced arms
  additionally propagate the generator / reduction honesty tags, so no artifact
  can mistake a derived or reduced tree for empirical evidence.
* Out-of-sample failure is measured on the MW budget only, exactly as in the L5
  model; temporal envelopes stay out of scope.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from src.evaluation.economic_holdout import (
    EconomicHoldoutInputs,
    evaluate_economic_holdout,
)
from src.scenarios import reduce_scenarios_fast_forward

from experiments.run_rq2_h2_stochastic_holdout import (
    _build_coefficients,
    _build_generated_scenarios,
    _build_scenarios,
    _cross_check_policy_cvar,
    _load_config,
    _nonnegative_number,
    _number,
    _positive_int,
    _require_uncertified,
    _resolve_path,
    _strict_bool,
)


_ARM_FIELDS = (
    "arm",
    "training_source",
    "training_scenario_count",
    "reduction_kantorovich_distance",
    "correct_committed_mw",
    "b6_committed_mw",
    "correct_total_failure_probability",
    "b6_total_failure_probability",
    "h2_b6_extra_failure_probability",
    "h2_b6_extra_expected_shortfall_mwh",
    "h2_b6_underdelivers_out_of_sample",
    "cvar_cross_check_max_abs_error",
    "cvar_cross_check_passed",
    "training_feasible",
    "parameter_status",
    "security_certified",
)


def _model_settings(config: dict) -> dict:
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
    return {
        "max_budget": max_budget,
        "provisioning_cost": provisioning_cost,
        "lambda_risk": lambda_risk,
        "beta": beta,
        "shortfall_tolerance": shortfall_tolerance,
        "solver_name": solver_name,
    }


def _build_reduced_training(
    generator_raw: object, reduction_raw: object
) -> tuple[tuple, str, dict]:
    """Generate training scenarios, then thin them by fast-forward reduction.

    The reduction is applied to the *generated training* tree only (the holdout
    is built separately and never reduced), so the section-9 train/holdout
    separation is preserved. Both the generator honesty tag and the reduction
    tag are propagated on the returned status.
    """

    (training, _holdout_unused, generated_status, _prov) = _build_generated_scenarios(
        generator_raw
    )
    if not isinstance(reduction_raw, dict):
        raise ValueError("reduction must be a mapping when the reduced arm is enabled")
    target_count = _positive_int(reduction_raw.get("target_count"), "reduction.target_count")
    ground_norm_order = _number(
        reduction_raw.get("ground_norm_order", 2.0), "reduction.ground_norm_order"
    )
    reduced = reduce_scenarios_fast_forward(
        training,
        target_count=target_count,
        ground_norm_order=ground_norm_order,
        parameter_status=generated_status,
    )
    return reduced.reduced_scenarios, reduced.parameter_status, reduced.provenance


def _evaluate_arm(
    *,
    arm: str,
    training_scenarios: tuple,
    holdout_scenarios: tuple,
    arm_parameter_status: str,
    coefficients,
    settings: dict,
    reduction_distance: float | None,
) -> tuple[dict, float, bool, bool]:
    """Plan + execute the correct/B6 policies for one training arm.

    Returns the arm summary row, the arm's max CVaR cross-check error, whether
    the cross-check passed, and whether the training plans were feasible.
    """

    inputs = EconomicHoldoutInputs(
        training_scenarios=training_scenarios,
        holdout_scenarios=holdout_scenarios,
        coefficients=coefficients,
        provisioning_cost_per_mw=settings["provisioning_cost"],
        max_flexibility_budget_mw=settings["max_budget"],
        lambda_risk=settings["lambda_risk"],
        beta=settings["beta"],
        parameter_status=arm_parameter_status,
        service_shortfall_tolerance_mw=settings["shortfall_tolerance"],
    )
    result = evaluate_economic_holdout(inputs, solver_name=settings["solver_name"])

    max_cross_check_error = 0.0
    for policy in (result.correct, result.b6):
        error = _cross_check_policy_cvar(inputs, policy)
        if error is not None:
            max_cross_check_error = max(max_cross_check_error, error)

    training_feasible = (
        result.correct.training_feasible and result.b6.training_feasible
    )
    row = {
        "arm": arm,
        "training_source": arm,
        "training_scenario_count": len(training_scenarios),
        "reduction_kantorovich_distance": reduction_distance,
        "correct_committed_mw": result.correct.committed_flexibility_mw,
        "b6_committed_mw": result.b6.committed_flexibility_mw,
        "correct_total_failure_probability": (
            result.correct.total_failure_probability
        ),
        "b6_total_failure_probability": result.b6.total_failure_probability,
        "h2_b6_extra_failure_probability": result.b6_extra_failure_probability,
        "h2_b6_extra_expected_shortfall_mwh": (
            result.b6_extra_expected_shortfall_mwh
        ),
        "h2_b6_underdelivers_out_of_sample": (
            result.h2_b6_underdelivers_out_of_sample
        ),
        "cvar_cross_check_max_abs_error": max_cross_check_error,
        "cvar_cross_check_passed": None,  # filled by caller against tolerance
        "training_feasible": training_feasible,
        "parameter_status": arm_parameter_status,
        "security_certified": False,
    }
    return row, max_cross_check_error, training_feasible, result.h2_evaluated


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict]) -> None:
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
    base_parameter_status = evaluation.get("parameter_status")
    if not isinstance(base_parameter_status, str) or not base_parameter_status:
        raise ValueError("evaluation.parameter_status must be a nonempty string")
    _require_uncertified(evaluation.get("security_certified"), "security_certified")
    _require_uncertified(
        evaluation.get("formal_vma_published", False), "formal_vma_published"
    )

    settings = _model_settings(config)
    coefficients = _build_coefficients(config.get("coefficients"))

    # One shared, fixed holdout test set for every arm (the controlled variable
    # is the *training* source only). It is the manual holdout tree so all arms
    # are compared on identical unseen leaves.
    holdout_scenarios = _build_scenarios(
        config.get("holdout_scenarios"), "holdout_scenarios"
    )

    arms = config.get("arms")
    if not isinstance(arms, list) or not arms:
        raise ValueError("config.arms must be a nonempty list of arm names")
    allowed = {"manual", "generated", "reduced"}
    unknown = [a for a in arms if a not in allowed]
    if unknown:
        raise ValueError(f"unknown arm(s) {unknown}; allowed: {sorted(allowed)}")
    if len(set(arms)) != len(arms):
        raise ValueError("arms must be unique")

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
    arms_path = _resolve_path(output.get("arms_path"))
    summary_path = _resolve_path(output.get("summary_path"))

    arm_rows: list[dict] = []
    gate_passed = True
    for arm in arms:
        if arm == "manual":
            training_scenarios = _build_scenarios(
                config.get("training_scenarios"), "training_scenarios"
            )
            arm_status = f"{base_parameter_status}::manual_training_tree"
            reduction_distance: float | None = None
        elif arm == "generated":
            (training_scenarios, _h, generated_status, _p) = _build_generated_scenarios(
                config.get("generator")
            )
            arm_status = f"{base_parameter_status}::{generated_status}"
            reduction_distance = None
        else:  # reduced
            (
                training_scenarios,
                reduced_status,
                reduction_prov,
            ) = _build_reduced_training(
                config.get("generator"), config.get("reduction")
            )
            arm_status = f"{base_parameter_status}::{reduced_status}"
            reduction_distance = reduction_prov["kantorovich_distance"]

        row, max_error, training_feasible, _h2_evaluated = _evaluate_arm(
            arm=arm,
            training_scenarios=training_scenarios,
            holdout_scenarios=holdout_scenarios,
            arm_parameter_status=arm_status,
            coefficients=coefficients,
            settings=settings,
            reduction_distance=reduction_distance,
        )
        arm_cross_check_passed = max_error <= cvar_tolerance
        row["cvar_cross_check_passed"] = arm_cross_check_passed
        arm_rows.append(row)

        arm_gate = arm_cross_check_passed and (
            training_feasible or not fail_closed_on_infeasible_training
        )
        gate_passed = gate_passed and arm_gate

    _write_csv(arms_path, _ARM_FIELDS, arm_rows)

    # H2 robustness across sources: reported, never gated. The conclusion is
    # robust when every *evaluable* arm shows the B6 policy under-delivering out
    # of sample; arms whose training plan was infeasible cannot form the H2
    # comparison and are excluded from the "all" test (and disclosed).
    evaluable = [r for r in arm_rows if r["training_feasible"]]
    h2_flags = [bool(r["h2_b6_underdelivers_out_of_sample"]) for r in evaluable]
    h2_robust_across_sources = bool(evaluable) and all(h2_flags)

    summary = {
        "evaluation_id": evaluation_id,
        "role": evaluation.get("role"),
        "base_parameter_status": base_parameter_status,
        "arms": list(arms),
        "shared_holdout_scenario_count": len(holdout_scenarios),
        "shared_holdout_scenarios": [
            {"name": s.name, "probability": s.probability}
            for s in holdout_scenarios
        ],
        "solver_name": settings["solver_name"],
        "beta": settings["beta"],
        "lambda_risk": settings["lambda_risk"],
        "max_flexibility_budget_mw": settings["max_budget"],
        "provisioning_cost_per_mw": settings["provisioning_cost"],
        "service_shortfall_tolerance_mw": settings["shortfall_tolerance"],
        "cvar_cross_check_tolerance": cvar_tolerance,
        "arm_results": [
            {
                "arm": r["arm"],
                "training_scenario_count": r["training_scenario_count"],
                "reduction_kantorovich_distance": (
                    r["reduction_kantorovich_distance"]
                ),
                "correct_committed_mw": r["correct_committed_mw"],
                "b6_committed_mw": r["b6_committed_mw"],
                "h2_b6_extra_failure_probability": (
                    r["h2_b6_extra_failure_probability"]
                ),
                "h2_b6_extra_expected_shortfall_mwh": (
                    r["h2_b6_extra_expected_shortfall_mwh"]
                ),
                "h2_b6_underdelivers_out_of_sample": (
                    r["h2_b6_underdelivers_out_of_sample"]
                ),
                "cvar_cross_check_max_abs_error": (
                    r["cvar_cross_check_max_abs_error"]
                ),
                "cvar_cross_check_passed": r["cvar_cross_check_passed"],
                "training_feasible": r["training_feasible"],
            }
            for r in arm_rows
        ],
        "h2_robust_across_sources": h2_robust_across_sources,
        "evaluable_arm_count": len(evaluable),
        "gate_passed": gate_passed,
        "random_seed": config.get("random_seed"),
        # Honesty gates (agent.md sections 4/8).
        "security_certified": False,
        "formal_vma_published": False,
        "empirical_holdout_claimed": False,
        "touches_frozen_baselines": False,
        "interpretation": (
            "synthetic_out_of_sample_ablation_that_holds_the_holdout_fixed_and_"
            "varies_only_the_training_scenario_source_manual_generated_reduced_"
            "to_test_whether_the_b6_under_delivery_finding_is_an_artifact_of_the_"
            "training_draw_not_an_empirical_vma_or_engineering_certification"
        ),
        "certification_blockers": [
            "synthetic_or_trace_derived_coefficients_budget_cap_and_scenario_"
            "probabilities_not_empirical",
            "holdout_tree_is_a_synthetic_unseen_scenario_set_not_an_empirical_"
            "vma_sample",
            "reduced_arm_is_a_probability_mass_transformation_of_the_generated_"
            "training_tree_not_new_data",
            "temporal_envelopes_recovery_debt_duration_event_count_out_of_scope",
            "no_ac_or_n1_network_certification_in_this_entry_point",
        ],
        "output_paths": {
            "arms": str(arms_path),
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
        default=Path("configs/rq2_h2_scenario_source_ablation.yaml"),
    )
    args = parser.parse_args()
    summary = run(args.config)
    print(json.dumps(summary, ensure_ascii=False, allow_nan=False, indent=2))
    if not summary["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
