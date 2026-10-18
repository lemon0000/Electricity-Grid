"""RQ2 H2 out-of-sample execution of a fixed flexibility policy.

This module quantifies the section-12 *scenario-external* claim H2 for the L5
economic stochastic model (``economic_stochastic``): a flexibility budget
``D^flex`` that was *planned* under the B6 double-counting error, when executed
against the *true* shared physical budget on unseen holdout scenarios,
under-delivers service (positive access shortfall, and on severe leaves a hard
network-curtailment failure) strictly more than a budget planned under the
correct shared model -- under identical inputs, scenarios and security set.

The identification is a clean two stage, fixed-policy design:

* **Plan (in sample).** Solve the L5 model on the *training* scenario tree for
  both the correct shared model (``enforce_joint_budget=True``) and the B6
  error baseline (``enforce_joint_budget=False``). Read off the single
  first-stage nonanticipative provisioning ``D^flex`` of each. The correct
  model provisions at least as much (this is exactly the H1 mechanism); B6
  provisions less because it believes the network call and the green/CFE call
  can each draw on the full budget independently.
* **Execute (out of sample).** *Pin* ``D^flex`` (no re-optimisation -- the
  provisioning was committed before the holdout scenario was revealed, so the
  execution is nonanticipative) and, on each unseen holdout leaf, choose only
  the recourse against the **true joint shared budget**
  ``c_grid + c_green + l_drop <= D^flex``. The execution physics is *always*
  the shared budget, regardless of which model planned the policy: B6's error
  lived only in planning. Its under-provisioned budget then cannot serve both
  needs on the same leaf, so the green/CFE call spills into access shortfall,
  and on a leaf whose network-curtailment need exceeds the committed budget the
  recourse is infeasible -- an honest hard-security failure, reported as such.

Reuse and honesty (``agent.md`` sections 4/8):

* The recourse is solved by the *same* ``solve_economic_stochastic`` model with
  ``fixed_flexibility_mw`` pinned and ``enforce_joint_budget=True``. The "same
  security set" is therefore structural, not re-derived: the hard
  ``c_grid >= grid_need`` requirement, the joint budget and the connected-demand
  cap are the identical constraints used in planning.
* Mechanism-only and synthetic. Every coefficient, budget cap, price and
  scenario probability is a frozen synthetic parameter carried through
  ``parameter_status``; nothing here is a real outage probability, a contract
  capability, an hourly network certification or an engineering/AC result.
* Temporal envelopes (recovery debt / maximum duration / event count,
  ``formulation.md`` sections 10.2/10.3) are out of scope for this increment,
  exactly as in the L5 model. Out-of-sample failure is measured on the MW
  budget only (access shortfall, hard-curtailment infeasibility, service loss);
  a leaf that passes here may still violate a temporal envelope.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real

from ..models.economic_stochastic import (
    EconomicScenario,
    EconomicStochasticInputs,
    solve_economic_stochastic,
)
from .service_risk import (
    ScenarioServiceLoss,
    ServiceLossCoefficients,
    evaluate_service_cvar,
)


ECONOMIC_HOLDOUT_SCOPE = (
    "synthetic_mechanism_only_out_of_sample_fixed_policy_execution_of_shared_"
    "budget_against_true_shared_physics_not_a_certification"
)

_PROBABILITY_TOLERANCE = 1.0e-9

_CORRECT_VARIANT = "correct_shared_budget"
_B6_VARIANT = "b6_error_split_budget"


def _finite(name: str, value_in: object) -> float:
    if isinstance(value_in, bool) or not isinstance(value_in, Real) or not isfinite(
        value_in
    ):
        raise ValueError(f"{name} must be a finite number")
    return float(value_in)


def _nonnegative_finite(name: str, value_in: object) -> float:
    number = _finite(name, value_in)
    if number < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return number


@dataclass(frozen=True)
class EconomicHoldoutInputs:
    """Frozen inputs for the H2 out-of-sample execution.

    ``training_scenarios`` are the in-sample paths the ``D^flex`` policy is
    planned on; ``holdout_scenarios`` are the unseen paths it is executed on.
    ``lambda_risk`` / ``beta`` parametrise the *training* plan exactly as in the
    L5 model (the execution recourse is a single-scenario cost minimisation and
    does not depend on ``lambda_risk``). ``service_shortfall_tolerance_mw`` is
    the MW threshold above which a feasible leaf counts as a service
    under-delivery.
    """

    training_scenarios: tuple[EconomicScenario, ...]
    holdout_scenarios: tuple[EconomicScenario, ...]
    coefficients: ServiceLossCoefficients
    provisioning_cost_per_mw: float
    max_flexibility_budget_mw: float
    lambda_risk: float
    beta: float
    parameter_status: str
    service_shortfall_tolerance_mw: float = 1.0e-6


@dataclass(frozen=True)
class HoldoutLeafOutcome:
    """One holdout leaf executed under a committed ``D^flex``."""

    name: str
    probability: float
    feasible: bool
    hard_security_failure: bool
    # ``solver_unresolved`` is True when the recourse solve neither found an
    # optimum nor *proved* infeasibility (timeout / solver failure). Such a leaf
    # is neither a feasible dispatch nor an honest hard-security failure, so it
    # is never counted as positive H2 evidence (agent.md sections 7/8).
    solver_unresolved: bool
    service_shortfall_failure: bool
    grid_curtailment_mw: float | None
    green_shift_mw: float | None
    permanent_drop_mw: float | None
    access_shortfall_mw: float | None
    scenario_loss: float | None


@dataclass(frozen=True)
class HoldoutPolicyEvaluation:
    """Out-of-sample outcome of one committed policy over all holdout leaves."""

    variant: str
    enforce_joint_budget_in_planning: bool
    training_feasible: bool
    committed_flexibility_mw: float | None
    leaf_outcomes: tuple[HoldoutLeafOutcome, ...]
    hard_infeasible_probability: float
    service_failure_probability: float
    total_failure_probability: float
    # Probability mass on holdout leaves whose recourse solve was unresolved
    # (timeout / solver failure). It is reported but excluded from the failure
    # channels so an unresolved solve is never minted into positive H2 evidence.
    solver_unresolved_probability: float
    expected_access_shortfall_mwh: float
    feasible_leaf_probability: float
    holdout_value_at_risk: float | None
    holdout_service_cvar: float | None
    parameter_status: str
    risk_measure_scope: str


@dataclass(frozen=True)
class EconomicHoldoutResult:
    """H2 comparison: does the B6-planned policy fail out of sample more?"""

    correct: HoldoutPolicyEvaluation
    b6: HoldoutPolicyEvaluation
    h2_evaluated: bool
    b6_extra_failure_probability: float | None
    b6_extra_expected_shortfall_mwh: float | None
    h2_b6_underdelivers_out_of_sample: bool
    parameter_status: str
    risk_measure_scope: str


def _validate_scenarios(
    scenarios: tuple[EconomicScenario, ...], label: str
) -> None:
    if not scenarios:
        raise ValueError(f"{label} must be a nonempty tuple")
    names = [s.name for s in scenarios]
    if any(not n for n in names) or len(set(names)) != len(names):
        raise ValueError(f"{label} names must be nonempty and unique")
    total = 0.0
    for scenario in scenarios:
        probability = _finite(f"{label}.probability[{scenario.name}]", scenario.probability)
        if probability <= 0.0:
            raise ValueError(f"{label} probabilities must be strictly positive")
        total += probability
        _nonnegative_finite(
            f"{label}.grid_need_mw[{scenario.name}]", scenario.grid_need_mw
        )
        _nonnegative_finite(
            f"{label}.green_call_mw[{scenario.name}]", scenario.green_call_mw
        )
        _nonnegative_finite(
            f"{label}.connected_demand_mw[{scenario.name}]",
            scenario.connected_demand_mw,
        )
        hours = _finite(f"{label}.hours[{scenario.name}]", scenario.hours)
        if hours <= 0.0:
            raise ValueError(f"{label} hours must be strictly positive")
    if abs(total - 1.0) > _PROBABILITY_TOLERANCE:
        raise ValueError(f"{label} probabilities must sum to one")


def _validate_inputs(inputs: EconomicHoldoutInputs) -> None:
    if not inputs.parameter_status:
        raise ValueError("parameter_status must be explicit")
    if not inputs.coefficients.parameter_status:
        raise ValueError("coefficient parameter_status must be explicit")
    _nonnegative_finite("provisioning_cost_per_mw", inputs.provisioning_cost_per_mw)
    _nonnegative_finite("max_flexibility_budget_mw", inputs.max_flexibility_budget_mw)
    _nonnegative_finite("lambda_risk", inputs.lambda_risk)
    _nonnegative_finite(
        "service_shortfall_tolerance_mw", inputs.service_shortfall_tolerance_mw
    )
    beta = _finite("beta", inputs.beta)
    if not 0.0 <= beta < 1.0:
        raise ValueError("CVaR confidence level beta must lie in [0, 1)")
    _validate_scenarios(inputs.training_scenarios, "training_scenarios")
    _validate_scenarios(inputs.holdout_scenarios, "holdout_scenarios")


def _plan_policy(
    inputs: EconomicHoldoutInputs,
    *,
    enforce_joint_budget: bool,
    solver_name: str,
) -> tuple[bool, float | None]:
    """Solve the L5 plan on the training tree and return committed ``D^flex``."""

    plan_inputs = EconomicStochasticInputs(
        scenarios=inputs.training_scenarios,
        coefficients=inputs.coefficients,
        provisioning_cost_per_mw=inputs.provisioning_cost_per_mw,
        max_flexibility_budget_mw=inputs.max_flexibility_budget_mw,
        lambda_risk=inputs.lambda_risk,
        beta=inputs.beta,
        enforce_joint_budget=enforce_joint_budget,
        parameter_status=inputs.parameter_status,
    )
    result = solve_economic_stochastic(plan_inputs, solver_name=solver_name)
    if not result.feasible:
        return False, None
    return True, result.provisioned_flexibility_mw


def _execute_leaf(
    inputs: EconomicHoldoutInputs,
    leaf: EconomicScenario,
    committed_flexibility_mw: float,
    *,
    solver_name: str,
) -> HoldoutLeafOutcome:
    """Execute the pinned policy on one unseen leaf against the true budget.

    The recourse is a single-scenario solve of the *same* L5 model with
    ``fixed_flexibility_mw`` pinned and the joint shared budget enforced. The
    scenario probability is set to one for the recourse solve (a single-scenario
    dispatch is independent of the probability weight); the *true* holdout
    probability is applied later for aggregation.
    """

    recourse_scenario = EconomicScenario(
        name=leaf.name,
        probability=1.0,
        grid_need_mw=leaf.grid_need_mw,
        green_call_mw=leaf.green_call_mw,
        connected_demand_mw=leaf.connected_demand_mw,
        hours=leaf.hours,
    )
    recourse_inputs = EconomicStochasticInputs(
        scenarios=(recourse_scenario,),
        coefficients=inputs.coefficients,
        provisioning_cost_per_mw=inputs.provisioning_cost_per_mw,
        max_flexibility_budget_mw=inputs.max_flexibility_budget_mw,
        # The recourse is a per-scenario cost minimisation; the tail weight does
        # not enter a single-scenario execution.
        lambda_risk=0.0,
        beta=inputs.beta,
        # The execution physics is always the true shared budget, whichever
        # model planned the committed provisioning.
        enforce_joint_budget=True,
        parameter_status=inputs.parameter_status,
        fixed_flexibility_mw=committed_flexibility_mw,
    )
    result = solve_economic_stochastic(recourse_inputs, solver_name=solver_name)

    if not result.feasible:
        if not result.proven_infeasible:
            # Unresolved recourse (timeout / solver failure): the solver stopped
            # without a proof. It is neither a feasible dispatch nor an honest
            # hard-security failure, so it must not be counted as positive H2
            # evidence. Surface it as its own channel and carry no dispatch.
            return HoldoutLeafOutcome(
                name=leaf.name,
                probability=leaf.probability,
                feasible=False,
                hard_security_failure=False,
                solver_unresolved=True,
                service_shortfall_failure=False,
                grid_curtailment_mw=None,
                green_shift_mw=None,
                permanent_drop_mw=None,
                access_shortfall_mw=None,
                scenario_loss=None,
            )
        # The committed budget cannot even meet the hard network-curtailment
        # need on this leaf: an honest scenario-external hard-security failure.
        # The budget is exhausted (and still short) on the hard grid need, so the
        # entire green/CFE call is unserved. Recording that full ``green_call`` as
        # access shortfall keeps a hard failure on the *under-delivery* side of
        # the energy ledger: it is at least as large as any feasible policy's
        # shortfall on the same leaf (which serves the grid need first and can
        # only shift *part* of the green call into shortfall), so a B6 hard
        # failure on a leaf where the correct policy is merely short cannot mask
        # into a false-negative H2 flag. It is kept out of the soft-shortfall
        # *probability* channel (``service_shortfall_failure=False``) so the hard
        # and soft failure probabilities stay disjoint and are not double counted.
        unserved_green = leaf.green_call_mw
        return HoldoutLeafOutcome(
            name=leaf.name,
            probability=leaf.probability,
            feasible=False,
            hard_security_failure=True,
            solver_unresolved=False,
            service_shortfall_failure=False,
            grid_curtailment_mw=None,
            green_shift_mw=None,
            permanent_drop_mw=None,
            access_shortfall_mw=unserved_green,
            scenario_loss=None,
        )

    dispatch = result.scenario_dispatch[leaf.name]
    shortfall_failure = (
        dispatch.access_shortfall_mw > inputs.service_shortfall_tolerance_mw
    )
    return HoldoutLeafOutcome(
        name=leaf.name,
        probability=leaf.probability,
        feasible=True,
        hard_security_failure=False,
        solver_unresolved=False,
        service_shortfall_failure=shortfall_failure,
        grid_curtailment_mw=dispatch.grid_curtailment_mw,
        green_shift_mw=dispatch.green_shift_mw,
        permanent_drop_mw=dispatch.permanent_drop_mw,
        access_shortfall_mw=dispatch.access_shortfall_mw,
        scenario_loss=dispatch.scenario_loss,
    )


def _holdout_cvar(
    inputs: EconomicHoldoutInputs,
    outcomes: tuple[HoldoutLeafOutcome, ...],
) -> tuple[float | None, float | None]:
    """Service-loss beta-CVaR over the holdout leaves.

    Well defined only when every leaf is feasible (the probabilities then sum to
    one and the loss distribution is complete). When any leaf fails hard, the
    tail is dominated by an unbounded-service failure that a finite service-loss
    CVaR cannot represent, so this returns ``None`` and the hard-failure
    probability carries the tail signal instead.
    """

    if any(not outcome.feasible for outcome in outcomes):
        return None, None
    loss_scenarios = []
    holdout = {s.name: s for s in inputs.holdout_scenarios}
    for outcome in outcomes:
        hours = holdout[outcome.name].hours
        loss_scenarios.append(
            ScenarioServiceLoss(
                name=outcome.name,
                probability=outcome.probability,
                access_shortfall_mwh=(outcome.access_shortfall_mw or 0.0) * hours,
                grid_curtailment_mwh=(outcome.grid_curtailment_mw or 0.0) * hours,
                green_shift_mwh=(outcome.green_shift_mw or 0.0) * hours,
                permanent_drop_mwh=(outcome.permanent_drop_mw or 0.0) * hours,
                firm_breach_mwh=0.0,
                conditional_breach_mwh=0.0,
            )
        )
    evaluated = evaluate_service_cvar(
        loss_scenarios, inputs.coefficients, beta=inputs.beta
    )
    return evaluated.value_at_risk, evaluated.conditional_value_at_risk


def _evaluate_policy(
    inputs: EconomicHoldoutInputs,
    *,
    variant: str,
    enforce_joint_budget: bool,
    solver_name: str,
) -> HoldoutPolicyEvaluation:
    training_feasible, committed = _plan_policy(
        inputs, enforce_joint_budget=enforce_joint_budget, solver_name=solver_name
    )

    if not training_feasible or committed is None:
        return HoldoutPolicyEvaluation(
            variant=variant,
            enforce_joint_budget_in_planning=enforce_joint_budget,
            training_feasible=False,
            committed_flexibility_mw=None,
            leaf_outcomes=(),
            hard_infeasible_probability=0.0,
            service_failure_probability=0.0,
            total_failure_probability=0.0,
            solver_unresolved_probability=0.0,
            expected_access_shortfall_mwh=0.0,
            feasible_leaf_probability=0.0,
            holdout_value_at_risk=None,
            holdout_service_cvar=None,
            parameter_status=inputs.parameter_status,
            risk_measure_scope=ECONOMIC_HOLDOUT_SCOPE,
        )

    outcomes = tuple(
        _execute_leaf(inputs, leaf, committed, solver_name=solver_name)
        for leaf in inputs.holdout_scenarios
    )

    hard_probability = sum(
        outcome.probability for outcome in outcomes if outcome.hard_security_failure
    )
    service_probability = sum(
        outcome.probability for outcome in outcomes if outcome.service_shortfall_failure
    )
    unresolved_probability = sum(
        outcome.probability for outcome in outcomes if outcome.solver_unresolved
    )
    feasible_probability = sum(
        outcome.probability for outcome in outcomes if outcome.feasible
    )
    # Expected access shortfall aggregates every leaf that carries a shortfall
    # energy, feasible or hard-failed. A hard-security leaf records its full
    # unserved green call as ``access_shortfall_mw``, so its under-delivery is
    # counted here too; only an *unresolved* solve (no proof, no dispatch) is
    # excluded, since its shortfall is unknown rather than zero.
    expected_shortfall_mwh = 0.0
    holdout = {s.name: s for s in inputs.holdout_scenarios}
    for outcome in outcomes:
        if outcome.solver_unresolved or outcome.access_shortfall_mw is None:
            continue
        expected_shortfall_mwh += (
            outcome.probability
            * outcome.access_shortfall_mw
            * holdout[outcome.name].hours
        )

    value_at_risk, cvar = _holdout_cvar(inputs, outcomes)

    return HoldoutPolicyEvaluation(
        variant=variant,
        enforce_joint_budget_in_planning=enforce_joint_budget,
        training_feasible=True,
        committed_flexibility_mw=committed,
        leaf_outcomes=outcomes,
        hard_infeasible_probability=hard_probability,
        service_failure_probability=service_probability,
        total_failure_probability=hard_probability + service_probability,
        solver_unresolved_probability=unresolved_probability,
        expected_access_shortfall_mwh=expected_shortfall_mwh,
        feasible_leaf_probability=feasible_probability,
        holdout_value_at_risk=value_at_risk,
        holdout_service_cvar=cvar,
        parameter_status=inputs.parameter_status,
        risk_measure_scope=ECONOMIC_HOLDOUT_SCOPE,
    )


def evaluate_economic_holdout(
    inputs: EconomicHoldoutInputs,
    *,
    solver_name: str = "highs",
) -> EconomicHoldoutResult:
    """Run the H2 out-of-sample execution for the correct and B6 policies.

    Both policies are planned on the same training tree and executed on the same
    holdout tree against the same true shared budget, so any difference in
    out-of-sample failure is attributable to the planning error alone
    (``agent.md`` section 9 fairness). Input-validation errors raise
    ``ValueError``; a proven-infeasible training plan or holdout recourse
    surfaces as ``training_feasible=False`` / a hard-security leaf failure rather
    than raising.
    """

    _validate_inputs(inputs)

    correct = _evaluate_policy(
        inputs,
        variant=_CORRECT_VARIANT,
        enforce_joint_budget=True,
        solver_name=solver_name,
    )
    b6 = _evaluate_policy(
        inputs,
        variant=_B6_VARIANT,
        enforce_joint_budget=False,
        solver_name=solver_name,
    )

    h2_evaluated = correct.training_feasible and b6.training_feasible
    extra_failure: float | None = None
    extra_shortfall: float | None = None
    h2_positive = False
    if h2_evaluated:
        extra_failure = (
            b6.total_failure_probability - correct.total_failure_probability
        )
        extra_shortfall = (
            b6.expected_access_shortfall_mwh - correct.expected_access_shortfall_mwh
        )
        # H2 holds when the B6-planned policy under-delivers out of sample by a
        # strictly larger margin on at least one channel (failure probability or
        # expected shortfall) and never does better on either.
        h2_positive = (
            extra_failure >= -1.0e-9
            and extra_shortfall >= -1.0e-9
            and (extra_failure > 1.0e-9 or extra_shortfall > 1.0e-9)
        )

    return EconomicHoldoutResult(
        correct=correct,
        b6=b6,
        h2_evaluated=h2_evaluated,
        b6_extra_failure_probability=extra_failure,
        b6_extra_expected_shortfall_mwh=extra_shortfall,
        h2_b6_underdelivers_out_of_sample=h2_positive,
        parameter_status=inputs.parameter_status,
        risk_measure_scope=ECONOMIC_HOLDOUT_SCOPE,
    )


__all__ = [
    "ECONOMIC_HOLDOUT_SCOPE",
    "EconomicHoldoutInputs",
    "EconomicHoldoutResult",
    "HoldoutLeafOutcome",
    "HoldoutPolicyEvaluation",
    "evaluate_economic_holdout",
]
