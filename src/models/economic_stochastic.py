"""RQ2 L5 economic stochastic model (formulation.md sections 12-14).

This is the *first increment* of the L5 model. It wires the section 10.1
shared MW flexibility budget and the section 13 service-loss CVaR into the
single section 14 economic objective

    min C^grid + C^op + lambda^risk * CVaR_beta(L),

so that the CVaR enters the planning decision rather than being a
post-processing metric.

Scope and honesty boundaries (``agent.md`` sections 4/8):

* Mechanism-only and synthetic. Every coefficient, budget cap and price is a
  frozen synthetic parameter carried through ``parameter_status``; nothing
  here is a probability of a real outage, a contract capability, an hourly
  network certification or an engineering/AC result.
* First stage: a single nonanticipative flexibility provisioning ``D^flex``
  (root decision, one value shared by all scenarios) priced at
  ``provisioning_cost_per_mw`` -> ``C^grid``.
* Per scenario ``omega``: the model must meet an exogenous network
  curtailment need ``grid_need`` (a stand-in for the N-1/thermal-driven
  required curtailment) and an exogenous green/CFE deferral call
  ``green_call``, both drawn from the *shared* budget. Whatever the budget
  cannot cover on the green call becomes access shortfall and is charged in
  the loss ``L``.
* ``grid_need`` is a hard requirement: ``c_grid >= grid_need`` in every
  scenario. It is never relaxed against cost or CVaR (``agent.md`` section 8:
  CVaR is only for service/business loss, never for a thermal/N-1 limit). If
  the provisionable budget cannot cover the need, the model is infeasible, and
  that infeasibility is an honest H1 signal, not something the risk term buys
  down.

The correct model enforces the joint budget
``c_grid + c_green + l_drop <= D^flex``; the B6 error baseline
(``enforce_joint_budget=False``) drops it and caps ``c_grid + l_drop`` and
``c_green`` each by ``D^flex`` independently, so both draw on the full budget
and a strictly smaller provisioned budget serves the same demands.

Recovery-debt / maximum-duration / event-count temporal envelopes
(``formulation.md`` sections 10.2/10.3) are intentionally out of scope for
this increment and are left to a later increment that reuses
``flexibility_envelope``. This module does not touch the frozen B3/B4/B5
baselines or the repair-010 certification chain.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real

from pyomo.environ import (
    ConcreteModel,
    Constraint,
    NonNegativeReals,
    Objective,
    Reals,
    Set,
    SolverFactory,
    Var,
    minimize,
    value,
)
from pyomo.opt import TerminationCondition

from ..evaluation.service_risk import ServiceLossCoefficients


ECONOMIC_STOCHASTIC_SCOPE = (
    "synthetic_mechanism_only_shared_budget_and_service_cvar_economic_model_"
    "not_a_thermal_or_n1_relaxation_and_not_a_certification"
)

_PROBABILITY_TOLERANCE = 1.0e-9

_OPTIMAL_CONDITIONS = (
    TerminationCondition.optimal,
    TerminationCondition.globallyOptimal,
    TerminationCondition.locallyOptimal,
)
_INFEASIBLE_CONDITIONS = (
    TerminationCondition.infeasible,
    TerminationCondition.infeasibleOrUnbounded,
    TerminationCondition.unbounded,
)
# Only a *proven* infeasibility (the solver certified the feasible set is empty)
# is an honest hard-security failure. ``infeasibleOrUnbounded`` and ``unbounded``
# are not proofs that the security set is empty, so they are excluded: they
# surface as ``feasible=False`` but ``proven_infeasible=False`` (agent.md
# sections 7/8 -- never mint a non-certified status into a hard failure).
_PROVEN_INFEASIBLE_CONDITIONS = (TerminationCondition.infeasible,)


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
class EconomicScenario:
    """One long-horizon path ``omega`` with its exogenous demands.

    ``grid_need_mw`` is the network curtailment the scenario forces (hard
    security requirement); ``green_call_mw`` is the exogenous green/CFE
    deferral call competing for the same budget; ``connected_demand_mw`` is
    the optional ``D^conn`` cap; ``hours`` converts MW quantities to the MWh
    energies the loss coefficients are defined on. All are synthetic mechanism
    parameters.
    """

    name: str
    probability: float
    grid_need_mw: float
    green_call_mw: float
    connected_demand_mw: float
    hours: float


@dataclass(frozen=True)
class EconomicStochasticInputs:
    """Frozen inputs for the L5 economic stochastic model.

    ``coefficients`` are the section 13/14 per-MWh service-loss weights (also
    used for the ``C^op`` service-loss terms so the operating cost and the
    CVaR loss share one coefficient set). ``provisioning_cost_per_mw`` prices
    the first-stage ``D^flex`` into ``C^grid``. ``max_flexibility_budget_mw``
    caps provisionable flexibility. ``lambda_risk`` (>= 0) weights the CVaR;
    ``beta`` in ``[0, 1)`` selects the tail. ``enforce_joint_budget`` selects
    the correct shared model (True) or the B6 error baseline (False).
    """

    scenarios: tuple[EconomicScenario, ...]
    coefficients: ServiceLossCoefficients
    provisioning_cost_per_mw: float
    max_flexibility_budget_mw: float
    lambda_risk: float
    beta: float
    enforce_joint_budget: bool
    parameter_status: str
    # Out-of-sample execution (H2). When set, the first-stage ``D^flex`` is not
    # optimised but *pinned* to this already-committed value, and only the
    # per-scenario recourse is chosen. This is how a fixed, nonanticipative
    # provisioning policy is executed against unseen holdout scenarios: the
    # provisioning was decided before the scenario was revealed, so it cannot
    # react to it. ``None`` keeps the ordinary planning behaviour (``D^flex``
    # free within its cap).
    fixed_flexibility_mw: float | None = None


@dataclass(frozen=True)
class ScenarioDispatch:
    """Realised per-scenario operation (MW), the loss inputs for section 13."""

    grid_curtailment_mw: float
    green_shift_mw: float
    permanent_drop_mw: float
    access_shortfall_mw: float
    scenario_loss: float


@dataclass(frozen=True)
class EconomicStochasticResult:
    feasible: bool
    # ``proven_infeasible`` is True only when the solver *certified* the model
    # infeasible (an honest hard-security failure). A timeout / solver failure /
    # any other non-optimal termination leaves ``feasible=False`` but
    # ``proven_infeasible=False`` so it is never reinterpreted as a hard limit
    # violation (agent.md sections 7/8).
    proven_infeasible: bool
    termination_condition: str
    solver_status: str
    objective: float | None
    expansion_cost: float | None
    expected_operating_cost: float | None
    conditional_value_at_risk: float | None
    value_at_risk: float | None
    provisioned_flexibility_mw: float | None
    scenario_dispatch: dict[str, ScenarioDispatch]
    enforce_joint_budget: bool
    parameter_status: str
    risk_measure_scope: str


def _validate_inputs(inputs: EconomicStochasticInputs) -> None:
    if not inputs.parameter_status:
        raise ValueError("parameter_status must be explicit")
    if not inputs.coefficients.parameter_status:
        raise ValueError("coefficient parameter_status must be explicit")
    _nonnegative_finite("provisioning_cost_per_mw", inputs.provisioning_cost_per_mw)
    _nonnegative_finite("max_flexibility_budget_mw", inputs.max_flexibility_budget_mw)
    _nonnegative_finite("lambda_risk", inputs.lambda_risk)
    beta = _finite("beta", inputs.beta)
    if not 0.0 <= beta < 1.0:
        raise ValueError("CVaR confidence level beta must lie in [0, 1)")

    if inputs.fixed_flexibility_mw is not None:
        pinned = _nonnegative_finite(
            "fixed_flexibility_mw", inputs.fixed_flexibility_mw
        )
        if pinned > inputs.max_flexibility_budget_mw + _PROBABILITY_TOLERANCE:
            raise ValueError(
                "fixed_flexibility_mw must not exceed max_flexibility_budget_mw"
            )

    # Loss coefficients: reuse the service_risk validation semantics (all
    # nonnegative). Access/grid/green/drop are the only channels this increment
    # populates; firm/conditional breach are held at zero (u^F = u^X = 0).
    for name, coeff in (
        ("kappa_access", inputs.coefficients.kappa_access),
        ("kappa_grid", inputs.coefficients.kappa_grid),
        ("kappa_green", inputs.coefficients.kappa_green),
        ("kappa_drop", inputs.coefficients.kappa_drop),
        ("kappa_breach_firm", inputs.coefficients.kappa_breach_firm),
        ("kappa_breach_conditional", inputs.coefficients.kappa_breach_conditional),
    ):
        _nonnegative_finite(name, coeff)

    if not inputs.scenarios:
        raise ValueError("At least one scenario is required")
    names = [s.name for s in inputs.scenarios]
    if any(not n for n in names) or len(set(names)) != len(names):
        raise ValueError("Scenario names must be nonempty and unique")
    total_probability = 0.0
    for scenario in inputs.scenarios:
        probability = _finite(f"probability[{scenario.name}]", scenario.probability)
        if probability <= 0.0:
            raise ValueError("Scenario probabilities must be strictly positive")
        total_probability += probability
        _nonnegative_finite(f"grid_need_mw[{scenario.name}]", scenario.grid_need_mw)
        _nonnegative_finite(f"green_call_mw[{scenario.name}]", scenario.green_call_mw)
        _nonnegative_finite(
            f"connected_demand_mw[{scenario.name}]", scenario.connected_demand_mw
        )
        hours = _finite(f"hours[{scenario.name}]", scenario.hours)
        if hours <= 0.0:
            raise ValueError("Scenario hours must be strictly positive")
    if abs(total_probability - 1.0) > _PROBABILITY_TOLERANCE:
        raise ValueError("Scenario probabilities must sum to one")


def _build_model(inputs: EconomicStochasticInputs) -> ConcreteModel:
    coeff = inputs.coefficients
    scenarios = {s.name: s for s in inputs.scenarios}
    names = tuple(scenarios)

    model = ConcreteModel()
    model.scenarios = Set(initialize=names, ordered=True)

    # --- First stage: shared flexibility provisioning D^flex (root value) ---
    model.flex_budget = Var(
        bounds=(0.0, inputs.max_flexibility_budget_mw), domain=NonNegativeReals
    )
    if inputs.fixed_flexibility_mw is not None:
        # Out-of-sample execution: the provisioning was committed before the
        # scenario was revealed, so it is pinned rather than optimised. The
        # recourse (curtailment / shifting / drop / shortfall) is still chosen
        # per scenario, against the *same* physics and security set below.
        model.flex_budget.fix(float(inputs.fixed_flexibility_mw))

    # --- Per-scenario operation ---
    model.grid_curtailment = Var(model.scenarios, domain=NonNegativeReals)
    model.green_shift = Var(model.scenarios, domain=NonNegativeReals)
    model.permanent_drop = Var(model.scenarios, domain=NonNegativeReals)
    model.access_shortfall = Var(model.scenarios, domain=NonNegativeReals)

    # --- CVaR linearisation variables (section 13): eta free, zeta >= 0 ---
    model.var_eta = Var(domain=Reals)
    model.zeta = Var(model.scenarios, domain=NonNegativeReals)

    # Hard security: the exogenous network curtailment need must be met. This
    # is never traded against cost or CVaR (agent.md section 8).
    def grid_need_rule(m, w):
        return m.grid_curtailment[w] >= scenarios[w].grid_need_mw

    model.grid_need = Constraint(model.scenarios, rule=grid_need_rule)

    # The green/CFE deferral call is met either by shifting out of the shared
    # budget or, when the budget is short, by access shortfall (charged in L).
    def green_call_rule(m, w):
        return m.green_shift[w] + m.access_shortfall[w] == scenarios[w].green_call_mw

    model.green_call = Constraint(model.scenarios, rule=green_call_rule)

    # Connected-demand cap D^conn applies to both models.
    def connected_cap_rule(m, w):
        return (
            m.grid_curtailment[w] + m.green_shift[w] + m.permanent_drop[w]
            <= scenarios[w].connected_demand_mw
        )

    model.connected_cap = Constraint(model.scenarios, rule=connected_cap_rule)

    if inputs.enforce_joint_budget:
        # Correct model: single shared budget (formulation.md section 10.1).
        def joint_budget_rule(m, w):
            return (
                m.grid_curtailment[w] + m.green_shift[w] + m.permanent_drop[w]
                <= m.flex_budget
            )

        model.shared_budget = Constraint(model.scenarios, rule=joint_budget_rule)
    else:
        # B6 error baseline: split budget, each capped by the full D^flex.
        def b6_grid_rule(m, w):
            return m.grid_curtailment[w] + m.permanent_drop[w] <= m.flex_budget

        def b6_green_rule(m, w):
            return m.green_shift[w] <= m.flex_budget

        model.b6_grid_budget = Constraint(model.scenarios, rule=b6_grid_rule)
        model.b6_green_budget = Constraint(model.scenarios, rule=b6_green_rule)

    # --- Section 13 loss L_omega (service/business loss only, MWh) ---
    # No thermal/branch/POI/N-1 limit ever enters this expression.
    def scenario_loss_expr(m, w):
        s = scenarios[w]
        return s.hours * (
            coeff.kappa_access * m.access_shortfall[w]
            + coeff.kappa_grid * m.grid_curtailment[w]
            + coeff.kappa_green * m.green_shift[w]
            + coeff.kappa_drop * m.permanent_drop[w]
        )

    model.scenario_loss_expr = scenario_loss_expr

    # CVaR epigraph: zeta_omega >= L_omega - eta.
    def cvar_epigraph_rule(m, w):
        return m.zeta[w] >= scenario_loss_expr(m, w) - m.var_eta

    model.cvar_epigraph = Constraint(model.scenarios, rule=cvar_epigraph_rule)

    # --- Objective: C^grid + C^op + lambda * CVaR_beta(L) ---
    expansion_cost = inputs.provisioning_cost_per_mw * model.flex_budget

    operating_cost = sum(
        scenarios[w].probability * scenario_loss_expr(model, w) for w in names
    )

    cvar = model.var_eta + (1.0 / (1.0 - inputs.beta)) * sum(
        scenarios[w].probability * model.zeta[w] for w in names
    )

    model.expansion_cost_expr = expansion_cost
    model.operating_cost_expr = operating_cost
    model.cvar_expr = cvar

    model.total_cost = Objective(
        expr=expansion_cost + operating_cost + inputs.lambda_risk * cvar,
        sense=minimize,
    )
    return model


def _infeasible_result(
    inputs: EconomicStochasticInputs,
    termination: str,
    solver_status: str,
    *,
    proven_infeasible: bool,
) -> EconomicStochasticResult:
    return EconomicStochasticResult(
        feasible=False,
        proven_infeasible=proven_infeasible,
        termination_condition=termination,
        solver_status=solver_status,
        objective=None,
        expansion_cost=None,
        expected_operating_cost=None,
        conditional_value_at_risk=None,
        value_at_risk=None,
        provisioned_flexibility_mw=None,
        scenario_dispatch={},
        enforce_joint_budget=inputs.enforce_joint_budget,
        parameter_status=inputs.parameter_status,
        risk_measure_scope=ECONOMIC_STOCHASTIC_SCOPE,
    )


def solve_economic_stochastic(
    inputs: EconomicStochasticInputs,
    *,
    solver_name: str = "highs",
    tee: bool = False,
) -> EconomicStochasticResult:
    """Solve the L5 economic stochastic model and report the objective split.

    Returns a result with ``feasible=False`` (rather than raising) for any
    non-optimal termination. Only a solver-*certified* infeasibility sets
    ``proven_infeasible=True`` (an honest hard-security failure); a timeout,
    solver failure or any other unresolved termination keeps
    ``proven_infeasible=False`` and preserves the true termination string, so it
    is never reinterpreted as a hard limit violation. Input-validation errors
    still raise ``ValueError``.
    """

    _validate_inputs(inputs)
    scenarios = {s.name: s for s in inputs.scenarios}
    model = _build_model(inputs)

    solver = SolverFactory(solver_name)
    # load_solutions=False so a proven-infeasible model returns a legacy
    # SolverResults (with .solver.termination_condition) instead of raising;
    # the solution is loaded manually only when the run is optimal.
    results = solver.solve(model, tee=tee, load_solutions=False)
    termination = results.solver.termination_condition
    solver_status = str(results.solver.status)

    if termination in _INFEASIBLE_CONDITIONS:
        # A proven-infeasible termination is an honest hard-security failure;
        # ``infeasibleOrUnbounded`` / ``unbounded`` are not certificates that the
        # security set is empty, so they surface as unresolved instead.
        return _infeasible_result(
            inputs,
            str(termination),
            solver_status,
            proven_infeasible=termination in _PROVEN_INFEASIBLE_CONDITIONS,
        )
    if termination not in _OPTIMAL_CONDITIONS:
        # Timeout / solver failure / any other non-optimal, non-infeasible
        # termination is unresolved: the solver stopped without a proof. It must
        # never be minted into a hard-security (proven-infeasible) failure.
        return _infeasible_result(
            inputs, str(termination), solver_status, proven_infeasible=False
        )

    model.solutions.load_from(results)

    # Extract the solution and recompute the reported quantities from it so the
    # reported split is exactly consistent with the realised dispatch.
    provisioned = float(value(model.flex_budget))

    dispatch: dict[str, ScenarioDispatch] = {}
    expected_operating_cost = 0.0
    losses: list[tuple[float, float]] = []  # (loss, probability)
    for name in scenarios:
        s = scenarios[name]
        c_grid = float(value(model.grid_curtailment[name]))
        c_green = float(value(model.green_shift[name]))
        l_drop = float(value(model.permanent_drop[name]))
        u_access = float(value(model.access_shortfall[name]))
        loss = s.hours * (
            inputs.coefficients.kappa_access * u_access
            + inputs.coefficients.kappa_grid * c_grid
            + inputs.coefficients.kappa_green * c_green
            + inputs.coefficients.kappa_drop * l_drop
        )
        dispatch[name] = ScenarioDispatch(
            grid_curtailment_mw=c_grid,
            green_shift_mw=c_green,
            permanent_drop_mw=l_drop,
            access_shortfall_mw=u_access,
            scenario_loss=loss,
        )
        expected_operating_cost += s.probability * loss
        losses.append((loss, s.probability))

    # Report the CVaR from the closed-form beta-VaR of the realised losses
    # rather than from the solver's eta. When lambda_risk = 0 the eta/zeta
    # variables drop out of the objective and the solver leaves eta at an
    # arbitrary vertex, which would overstate the CVaR of the dispatch. The
    # Rockafellar-Uryasev minimum g(VaR) = VaR + 1/(1-beta) * sum p * (L-VaR)^+
    # is the true CVaR of this loss distribution and coincides with the
    # solver's optimal eta whenever lambda_risk > 0, so the reported split
    # stays consistent with the dispatch at every lambda and beta.
    value_at_risk = _value_at_risk(losses, inputs.beta)
    cvar_tail = sum(
        probability * max(loss - value_at_risk, 0.0) for loss, probability in losses
    )
    conditional_value_at_risk = value_at_risk + cvar_tail / (1.0 - inputs.beta)
    expansion_cost = inputs.provisioning_cost_per_mw * provisioned
    objective = (
        expansion_cost
        + expected_operating_cost
        + inputs.lambda_risk * conditional_value_at_risk
    )

    return EconomicStochasticResult(
        feasible=True,
        proven_infeasible=False,
        termination_condition=str(termination),
        solver_status=solver_status,
        objective=objective,
        expansion_cost=expansion_cost,
        expected_operating_cost=expected_operating_cost,
        conditional_value_at_risk=conditional_value_at_risk,
        value_at_risk=value_at_risk,
        provisioned_flexibility_mw=provisioned,
        scenario_dispatch=dispatch,
        enforce_joint_budget=inputs.enforce_joint_budget,
        parameter_status=inputs.parameter_status,
        risk_measure_scope=ECONOMIC_STOCHASTIC_SCOPE,
    )


def _value_at_risk(losses: list[tuple[float, float]], beta: float) -> float:
    """Closed-form beta-VaR: smallest realised loss whose cumulative
    probability reaches beta (matches service_risk.evaluate_service_cvar)."""

    probability_by_loss: dict[float, float] = {}
    for loss, probability in losses:
        probability_by_loss[loss] = probability_by_loss.get(loss, 0.0) + probability
    distinct = sorted(probability_by_loss)
    cumulative = 0.0
    var = distinct[-1]
    for candidate in distinct:
        cumulative += probability_by_loss[candidate]
        if cumulative >= beta - _PROBABILITY_TOLERANCE:
            var = candidate
            break
    return var
