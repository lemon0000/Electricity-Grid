"""RQ2 L5 economic stochastic model (formulation.md sections 12-14).

These tests pin the *first increment* of the L5 model that wires the shared
MW flexibility budget and the section 13 service-loss CVaR into a single
economic objective

    min C^grid + C^op + lambda^risk * CVaR_beta(L).

The scope is deliberately narrow and mechanism-only (synthetic parameters,
no engineering/AC certification):

* a first-stage nonanticipative flexibility provisioning ``D^flex`` priced as
  ``C^grid``;
* per-scenario operation that must meet an exogenous network curtailment need
  ``grid_need`` (a stand-in for the N-1/thermal-driven required curtailment)
  and an exogenous green/CFE deferral call ``green_call`` out of the *shared*
  budget;
* the section 13 CVaR of the service/business loss, linearised with decision
  variables ``eta`` and ``zeta_omega`` so it enters the objective rather than
  being a post-processing metric.

Two hard invariants from ``agent.md`` sections 8/14 are asserted directly:
the correct model enforces ``c_grid + c_green + l_drop <= D_flex`` jointly
while the B6 error baseline splits the budget, and no thermal/N-1 limit ever
enters the loss ``L`` that CVaR is taken over. Recovery debt / duration /
event-count envelopes are out of scope for this increment and are left to a
later increment reusing ``flexibility_envelope``.
"""

from dataclasses import replace

import pytest

from src.evaluation.service_risk import (
    ScenarioServiceLoss,
    ServiceLossCoefficients,
    evaluate_service_cvar,
)
from src.models.economic_stochastic import (
    EconomicScenario,
    EconomicStochasticInputs,
    EconomicStochasticResult,
    solve_economic_stochastic,
)


PARAMETER_STATUS = "synthetic_test_only_not_for_engineering"


def _coefficients(**overrides) -> ServiceLossCoefficients:
    base = dict(
        kappa_access=1000.0,
        kappa_grid=50.0,
        kappa_green=40.0,
        kappa_drop=2000.0,
        kappa_breach_firm=0.0,
        kappa_breach_conditional=0.0,
        parameter_status=PARAMETER_STATUS,
    )
    base.update(overrides)
    return ServiceLossCoefficients(**base)


def _scenario(
    name: str,
    probability: float,
    *,
    grid_need_mw: float,
    green_call_mw: float,
    connected_demand_mw: float = 1000.0,
) -> EconomicScenario:
    return EconomicScenario(
        name=name,
        probability=probability,
        grid_need_mw=grid_need_mw,
        green_call_mw=green_call_mw,
        connected_demand_mw=connected_demand_mw,
        hours=1.0,
    )


def _inputs(
    scenarios,
    *,
    lambda_risk: float,
    beta: float,
    enforce_joint_budget: bool,
    provisioning_cost_per_mw: float = 10.0,
    max_flexibility_budget_mw: float = 200.0,
    coefficients=None,
) -> EconomicStochasticInputs:
    return EconomicStochasticInputs(
        scenarios=tuple(scenarios),
        coefficients=coefficients or _coefficients(),
        provisioning_cost_per_mw=provisioning_cost_per_mw,
        max_flexibility_budget_mw=max_flexibility_budget_mw,
        lambda_risk=lambda_risk,
        beta=beta,
        enforce_joint_budget=enforce_joint_budget,
        parameter_status=PARAMETER_STATUS,
    )


@pytest.fixture
def two_scenarios():
    # Two equiprobable long-horizon paths with different network curtailment
    # needs. The high-need path drives the tail loss the CVaR sees.
    return (
        _scenario("mild", 0.5, grid_need_mw=20.0, green_call_mw=10.0),
        _scenario("stress", 0.5, grid_need_mw=120.0, green_call_mw=10.0),
    )


# --------------------------------------------------------------------------
# Solvability and basic structure
# --------------------------------------------------------------------------


def test_solves_and_reports_objective_split(two_scenarios):
    inputs = _inputs(
        two_scenarios, lambda_risk=1.0, beta=0.5, enforce_joint_budget=True
    )
    result = solve_economic_stochastic(inputs, solver_name="highs")
    assert isinstance(result, EconomicStochasticResult)
    assert result.feasible
    # Objective must decompose exactly into the three reported pieces.
    recomposed = (
        result.expansion_cost
        + result.expected_operating_cost
        + inputs.lambda_risk * result.conditional_value_at_risk
    )
    assert result.objective == pytest.approx(recomposed, rel=1e-6, abs=1e-6)
    # Provisioned budget must respect its cap and be nonnegative.
    assert 0.0 <= result.provisioned_flexibility_mw <= inputs.max_flexibility_budget_mw + 1e-6


# --------------------------------------------------------------------------
# Shared budget hard constraint vs the B6 error baseline (H1 mechanism)
# --------------------------------------------------------------------------


def test_shared_budget_couples_grid_and_green(two_scenarios):
    # The correct model must satisfy c_grid + c_green + l_drop <= D_flex in
    # every scenario. With a positive green call, the provisioned budget has to
    # cover the sum, not each term separately.
    inputs = _inputs(
        two_scenarios, lambda_risk=0.0, beta=0.5, enforce_joint_budget=True
    )
    result = solve_economic_stochastic(inputs, solver_name="highs")
    assert result.feasible
    d_flex = result.provisioned_flexibility_mw
    for name, sc in result.scenario_dispatch.items():
        assert (
            sc.grid_curtailment_mw + sc.green_shift_mw + sc.permanent_drop_mw
            <= d_flex + 1e-6
        ), name


def test_b6_splits_budget_and_underprovisions(two_scenarios):
    # B6 removes the joint constraint and caps c_grid+l_drop and c_green each by
    # D_flex independently. For the SAME grid_need/green_call, B6 can serve both
    # demands from a strictly smaller provisioned budget than the joint model.
    joint = solve_economic_stochastic(
        _inputs(two_scenarios, lambda_risk=0.0, beta=0.5, enforce_joint_budget=True),
        solver_name="highs",
    )
    b6 = solve_economic_stochastic(
        _inputs(two_scenarios, lambda_risk=0.0, beta=0.5, enforce_joint_budget=False),
        solver_name="highs",
    )
    assert joint.feasible and b6.feasible
    # Both must fully meet the same exogenous grid need (hard security), so any
    # difference shows up as provisioned flexibility, not as unmet need.
    assert b6.provisioned_flexibility_mw < joint.provisioned_flexibility_mw - 1e-6


# --------------------------------------------------------------------------
# CVaR is embedded in the objective and matches the closed-form evaluator
# --------------------------------------------------------------------------


def test_cvar_matches_closed_form_evaluator_at_fixed_dispatch(two_scenarios):
    # With lambda_risk = 0 the optimiser ignores the tail, so we recompute the
    # section 13 CVaR of the realised losses with the independent closed-form
    # evaluator and require the model to report the same number for the same
    # beta and the same realised per-scenario losses.
    inputs = _inputs(
        two_scenarios, lambda_risk=0.0, beta=0.5, enforce_joint_budget=True
    )
    result = solve_economic_stochastic(inputs, solver_name="highs")
    assert result.feasible
    losses = []
    for sc in two_scenarios:
        d = result.scenario_dispatch[sc.name]
        losses.append(
            ScenarioServiceLoss(
                name=sc.name,
                probability=sc.probability,
                access_shortfall_mwh=d.access_shortfall_mw * sc.hours,
                grid_curtailment_mwh=d.grid_curtailment_mw * sc.hours,
                green_shift_mwh=d.green_shift_mw * sc.hours,
                permanent_drop_mwh=d.permanent_drop_mw * sc.hours,
                firm_breach_mwh=0.0,
                conditional_breach_mwh=0.0,
            )
        )
    reference = evaluate_service_cvar(losses, inputs.coefficients, beta=inputs.beta)
    assert result.conditional_value_at_risk == pytest.approx(
        reference.conditional_value_at_risk, rel=1e-5, abs=1e-5
    )
    assert result.value_at_risk == pytest.approx(
        reference.value_at_risk, rel=1e-5, abs=1e-5
    )


def test_lambda_increases_risk_weight_lowers_tail(two_scenarios):
    # H3 mechanism: raising lambda_risk cannot increase the optimal CVaR and the
    # expected operating cost cannot go down (a monotone risk/cost trade-off).
    low = solve_economic_stochastic(
        _inputs(two_scenarios, lambda_risk=0.0, beta=0.8, enforce_joint_budget=True),
        solver_name="highs",
    )
    high = solve_economic_stochastic(
        _inputs(two_scenarios, lambda_risk=100.0, beta=0.8, enforce_joint_budget=True),
        solver_name="highs",
    )
    assert low.feasible and high.feasible
    assert high.conditional_value_at_risk <= low.conditional_value_at_risk + 1e-6
    assert high.expected_operating_cost >= low.expected_operating_cost - 1e-6


def test_cvar_report_matches_closed_form_at_lambda_zero_small_beta():
    # Regression for the lambda=0 CVaR reporting path. With four equiprobable
    # scenarios (max p = 0.25) and beta = 0.3 < 1 - max p = 0.75, the eta/zeta
    # variables drop out of the objective at lambda=0 and the solver leaves eta
    # at an arbitrary vertex. The reported CVaR must still equal the closed-form
    # Rockafellar-Uryasev value of the realised dispatch, not the solver's eta.
    scenarios = tuple(
        _scenario(f"s{i}", 0.25, grid_need_mw=need, green_call_mw=0.0)
        for i, need in enumerate((10.0, 40.0, 80.0, 160.0))
    )
    inputs = _inputs(
        scenarios,
        lambda_risk=0.0,
        beta=0.3,
        enforce_joint_budget=True,
        max_flexibility_budget_mw=500.0,
    )
    result = solve_economic_stochastic(inputs, solver_name="highs")
    assert result.feasible
    losses = [
        ScenarioServiceLoss(
            name=sc.name,
            probability=sc.probability,
            access_shortfall_mwh=result.scenario_dispatch[sc.name].access_shortfall_mw
            * sc.hours,
            grid_curtailment_mwh=result.scenario_dispatch[sc.name].grid_curtailment_mw
            * sc.hours,
            green_shift_mwh=result.scenario_dispatch[sc.name].green_shift_mw * sc.hours,
            permanent_drop_mwh=result.scenario_dispatch[sc.name].permanent_drop_mw
            * sc.hours,
            firm_breach_mwh=0.0,
            conditional_breach_mwh=0.0,
        )
        for sc in scenarios
    ]
    reference = evaluate_service_cvar(losses, inputs.coefficients, beta=inputs.beta)
    assert result.conditional_value_at_risk == pytest.approx(
        reference.conditional_value_at_risk, rel=1e-6, abs=1e-6
    )
    assert result.value_at_risk == pytest.approx(
        reference.value_at_risk, rel=1e-6, abs=1e-6
    )


# --------------------------------------------------------------------------
# Hard-security invariant: exogenous grid need must be met, CVaR cannot buy it
# --------------------------------------------------------------------------


def test_grid_need_is_hard_and_not_traded_against_cvar():
    # A single scenario whose grid need exceeds the maximum provisionable budget
    # must be infeasible: the network curtailment requirement is a hard limit,
    # not a cost the CVaR term can pay down.
    scenario = _scenario("overload", 1.0, grid_need_mw=500.0, green_call_mw=0.0)
    inputs = _inputs(
        [scenario],
        lambda_risk=10.0,
        beta=0.5,
        enforce_joint_budget=True,
        max_flexibility_budget_mw=100.0,
    )
    result = solve_economic_stochastic(inputs, solver_name="highs")
    assert not result.feasible


# --------------------------------------------------------------------------
# Input validation
# --------------------------------------------------------------------------


def test_probabilities_must_sum_to_one(two_scenarios):
    bad = (
        replace(two_scenarios[0], probability=0.5),
        replace(two_scenarios[1], probability=0.4),
    )
    with pytest.raises(ValueError):
        solve_economic_stochastic(
            _inputs(bad, lambda_risk=1.0, beta=0.5, enforce_joint_budget=True),
            solver_name="highs",
        )


def test_beta_out_of_range_rejected(two_scenarios):
    with pytest.raises(ValueError):
        solve_economic_stochastic(
            _inputs(two_scenarios, lambda_risk=1.0, beta=1.0, enforce_joint_budget=True),
            solver_name="highs",
        )


def test_negative_lambda_rejected(two_scenarios):
    with pytest.raises(ValueError):
        solve_economic_stochastic(
            _inputs(two_scenarios, lambda_risk=-1.0, beta=0.5, enforce_joint_budget=True),
            solver_name="highs",
        )


def test_missing_parameter_status_rejected(two_scenarios):
    inputs = _inputs(
        two_scenarios, lambda_risk=1.0, beta=0.5, enforce_joint_budget=True
    )
    with pytest.raises(ValueError):
        solve_economic_stochastic(
            replace(inputs, parameter_status=""), solver_name="highs"
        )


def test_missing_coefficient_parameter_status_rejected(two_scenarios):
    inputs = _inputs(
        two_scenarios,
        lambda_risk=1.0,
        beta=0.5,
        enforce_joint_budget=True,
        coefficients=_coefficients(parameter_status=""),
    )
    with pytest.raises(ValueError):
        solve_economic_stochastic(inputs, solver_name="highs")


def test_nonpositive_hours_rejected(two_scenarios):
    bad = (
        replace(two_scenarios[0], hours=0.0),
        two_scenarios[1],
    )
    with pytest.raises(ValueError):
        solve_economic_stochastic(
            _inputs(bad, lambda_risk=1.0, beta=0.5, enforce_joint_budget=True),
            solver_name="highs",
        )


def test_negative_grid_need_rejected(two_scenarios):
    bad = (
        replace(two_scenarios[0], grid_need_mw=-1.0),
        two_scenarios[1],
    )
    with pytest.raises(ValueError):
        solve_economic_stochastic(
            _inputs(bad, lambda_risk=1.0, beta=0.5, enforce_joint_budget=True),
            solver_name="highs",
        )


def test_duplicate_scenario_names_rejected(two_scenarios):
    bad = (
        two_scenarios[0],
        replace(two_scenarios[1], name=two_scenarios[0].name),
    )
    with pytest.raises(ValueError):
        solve_economic_stochastic(
            _inputs(bad, lambda_risk=1.0, beta=0.5, enforce_joint_budget=True),
            solver_name="highs",
        )


# --------------------------------------------------------------------------
# Fixed (pinned) provisioning for out-of-sample execution (H2 support)
# --------------------------------------------------------------------------


def test_fixed_flexibility_pins_the_first_stage(two_scenarios):
    # When fixed_flexibility_mw is set the model must not optimise D^flex; it
    # reports exactly the pinned value regardless of what the free optimum would
    # be. This is the nonanticipative execution primitive H2 relies on. The pin
    # (150) sits above the hard grid_need (120) so the recourse stays feasible
    # and above the free optimum so we can see the pin actually bind.
    pinned = 150.0
    inputs = replace(
        _inputs(two_scenarios, lambda_risk=1.0, beta=0.5, enforce_joint_budget=True),
        fixed_flexibility_mw=pinned,
    )
    result = solve_economic_stochastic(inputs, solver_name="highs")
    assert result.feasible
    assert result.provisioned_flexibility_mw == pytest.approx(pinned, abs=1e-9)

    # Sanity: the free optimum provisions strictly less than the pin, so the pin
    # is genuinely overriding the optimiser rather than coinciding with it.
    free = solve_economic_stochastic(
        _inputs(two_scenarios, lambda_risk=1.0, beta=0.5, enforce_joint_budget=True),
        solver_name="highs",
    )
    assert free.provisioned_flexibility_mw < pinned - 1e-6


def test_fixed_flexibility_below_need_is_infeasible():
    # Pinning D^flex below the hard grid_need must be infeasible: the pinned
    # budget cannot serve the network curtailment and the risk term cannot buy
    # it down. This is exactly the out-of-sample hard-security failure of an
    # under-provisioned (B6) policy on a severe unseen leaf.
    scenario = _scenario("severe", 1.0, grid_need_mw=90.0, green_call_mw=60.0)
    inputs = replace(
        _inputs(
            [scenario],
            lambda_risk=0.0,
            beta=0.5,
            enforce_joint_budget=True,
            max_flexibility_budget_mw=200.0,
        ),
        fixed_flexibility_mw=60.0,
    )
    result = solve_economic_stochastic(inputs, solver_name="highs")
    assert not result.feasible
    # A proven-infeasible model is an honest hard-security failure: the solver
    # certified there is no feasible dispatch, not merely that it gave up.
    assert result.proven_infeasible is True


# --------------------------------------------------------------------------
# Honest solver-status mapping (agent.md sections 7/13): a timeout / solver
# failure / any non-optimal-non-infeasible termination must NOT be reinterpreted
# as mathematical (hard-security) infeasibility.
# --------------------------------------------------------------------------


class _StubResults:
    def __init__(self, termination, status="warning"):
        self.solver = type(
            "_S", (), {"termination_condition": termination, "status": status}
        )()


class _StubSolver:
    def __init__(self, termination):
        self._termination = termination

    def solve(self, model, tee=False, load_solutions=False):
        return _StubResults(self._termination)


def test_optimal_run_is_not_flagged_proven_infeasible(two_scenarios):
    result = solve_economic_stochastic(
        _inputs(two_scenarios, lambda_risk=1.0, beta=0.5, enforce_joint_budget=True),
        solver_name="highs",
    )
    assert result.feasible
    assert result.proven_infeasible is False


def test_timeout_is_unresolved_not_proven_infeasible(two_scenarios, monkeypatch):
    # A maxTimeLimit termination is a stopped solve, not a proof of infeasibility.
    # It must surface as feasible=False AND proven_infeasible=False, and carry the
    # true termination string, so downstream code cannot mint it into a hard
    # security failure (positive H2 evidence).
    from pyomo.opt import TerminationCondition

    import src.models.economic_stochastic as econ

    monkeypatch.setattr(
        econ,
        "SolverFactory",
        lambda name: _StubSolver(TerminationCondition.maxTimeLimit),
    )
    result = solve_economic_stochastic(
        _inputs(two_scenarios, lambda_risk=1.0, beta=0.5, enforce_joint_budget=True),
        solver_name="highs",
    )
    assert result.feasible is False
    assert result.proven_infeasible is False
    assert "maxTimeLimit" in result.termination_condition


def test_fixed_flexibility_above_cap_is_rejected(two_scenarios):
    inputs = replace(
        _inputs(
            two_scenarios,
            lambda_risk=1.0,
            beta=0.5,
            enforce_joint_budget=True,
            max_flexibility_budget_mw=100.0,
        ),
        fixed_flexibility_mw=101.0,
    )
    with pytest.raises(ValueError, match="fixed_flexibility_mw"):
        solve_economic_stochastic(inputs, solver_name="highs")
