"""RQ2 H2 out-of-sample fixed-policy execution (formulation.md section 12).

These tests pin the core module ``evaluate_economic_holdout``: a flexibility
budget ``D^flex`` is *planned* on a training scenario tree (correct shared model
vs the B6 error baseline), then *executed* pinned on an unseen holdout tree
against the true shared budget. The scientific contract asserted here is H2 --
the B6-planned policy under-delivers service out of sample by a strictly larger
margin than the correctly-planned one, under the same inputs / scenarios /
security set -- plus the invariants that make the comparison honest:

* the pinned execution is nonanticipative (one committed ``D^flex`` per policy,
  reused unchanged on every holdout leaf);
* the execution physics is always the true joint shared budget, whichever model
  planned the policy;
* a holdout leaf whose hard network-curtailment need exceeds the committed
  budget is an honest hard-security failure, not a silently relaxed limit;
* the holdout service-loss CVaR (defined only when all leaves are feasible)
  matches the independent section 13 evaluator.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

pytest.importorskip("pyomo")

from src.evaluation.economic_holdout import (
    EconomicHoldoutInputs,
    evaluate_economic_holdout,
)
from src.evaluation.service_risk import (
    ScenarioServiceLoss,
    ServiceLossCoefficients,
    evaluate_service_cvar,
)
from src.models.economic_stochastic import EconomicScenario


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
    hours: float = 1.0,
) -> EconomicScenario:
    return EconomicScenario(
        name=name,
        probability=probability,
        grid_need_mw=grid_need_mw,
        green_call_mw=green_call_mw,
        connected_demand_mw=connected_demand_mw,
        hours=hours,
    )


@pytest.fixture
def training_tree():
    # green_call competes with grid_need for the same budget, so the correct
    # model provisions grid+green (stress: 40+60=100) while B6 provisions only
    # max(grid, green)=60 -> a positive H1 gap that must propagate out of sample.
    return (
        _scenario("train_mild", 0.5, grid_need_mw=20.0, green_call_mw=60.0),
        _scenario("train_stress", 0.5, grid_need_mw=40.0, green_call_mw=60.0),
    )


@pytest.fixture
def holdout_tree():
    # Unseen leaves: a mild/stress pair where both policies leave some shortfall
    # but B6 leaves more, and a severe leaf whose 90 MW hard need exceeds the B6
    # 60 MW budget -> B6 hard-security failure, correct policy still feasible.
    return (
        _scenario("holdout_mild", 0.4, grid_need_mw=25.0, green_call_mw=60.0),
        _scenario("holdout_stress", 0.4, grid_need_mw=50.0, green_call_mw=60.0),
        _scenario("holdout_severe", 0.2, grid_need_mw=90.0, green_call_mw=60.0),
    )


def _inputs(training, holdout, **overrides) -> EconomicHoldoutInputs:
    base = dict(
        training_scenarios=tuple(training),
        holdout_scenarios=tuple(holdout),
        coefficients=_coefficients(),
        provisioning_cost_per_mw=500.0,
        max_flexibility_budget_mw=200.0,
        lambda_risk=0.1,
        beta=0.5,
        parameter_status=PARAMETER_STATUS,
    )
    base.update(overrides)
    return EconomicHoldoutInputs(**base)


# ---------------------------------------------------------------------------
# H1 -> H2: the planned provisioning gap and its out-of-sample consequence
# ---------------------------------------------------------------------------


def test_plans_reflect_h1_provisioning_gap(training_tree, holdout_tree):
    result = evaluate_economic_holdout(
        _inputs(training_tree, holdout_tree), solver_name="highs"
    )
    assert result.h2_evaluated
    # Correct model provisions grid+green; B6 splits and under-provisions.
    assert result.correct.committed_flexibility_mw == pytest.approx(100.0, abs=1e-6)
    assert result.b6.committed_flexibility_mw == pytest.approx(60.0, abs=1e-6)


def test_b6_underdelivers_out_of_sample(training_tree, holdout_tree):
    result = evaluate_economic_holdout(
        _inputs(training_tree, holdout_tree), solver_name="highs"
    )
    assert result.h2_b6_underdelivers_out_of_sample is True
    # B6 fails on strictly more scenario mass and leaves a larger expected
    # shortfall than the correctly-planned policy.
    assert (
        result.b6.total_failure_probability
        > result.correct.total_failure_probability + 1e-9
    )
    assert (
        result.b6.expected_access_shortfall_mwh
        > result.correct.expected_access_shortfall_mwh + 1e-9
    )
    assert result.b6_extra_failure_probability > 1e-9
    assert result.b6_extra_expected_shortfall_mwh > 1e-9


def test_severe_leaf_is_a_hard_security_failure_for_b6_only(
    training_tree, holdout_tree
):
    result = evaluate_economic_holdout(
        _inputs(training_tree, holdout_tree), solver_name="highs"
    )
    b6_severe = next(
        o for o in result.b6.leaf_outcomes if o.name == "holdout_severe"
    )
    correct_severe = next(
        o for o in result.correct.leaf_outcomes if o.name == "holdout_severe"
    )
    # B6's 60 MW budget cannot meet the 90 MW hard need: honest infeasibility.
    assert b6_severe.feasible is False
    assert b6_severe.hard_security_failure is True
    # The correct 100 MW budget meets the hard need; only the green call spills.
    assert correct_severe.feasible is True
    assert correct_severe.hard_security_failure is False
    assert result.b6.hard_infeasible_probability == pytest.approx(0.2, abs=1e-9)
    assert result.correct.hard_infeasible_probability == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Nonanticipativity: one committed policy, reused unchanged on every leaf
# ---------------------------------------------------------------------------


def test_execution_is_nonanticipative(training_tree, holdout_tree):
    # The committed D^flex is planned on the training tree only; the holdout
    # leaves must never change it. We verify by re-running on a holdout tree
    # with a *different* severe leaf and checking the committed value is
    # unchanged (it depends only on the training tree).
    base = evaluate_economic_holdout(
        _inputs(training_tree, holdout_tree), solver_name="highs"
    )
    harsher = (
        _scenario("holdout_mild", 0.4, grid_need_mw=25.0, green_call_mw=60.0),
        _scenario("holdout_stress", 0.4, grid_need_mw=50.0, green_call_mw=60.0),
        _scenario("holdout_severe", 0.2, grid_need_mw=150.0, green_call_mw=90.0),
    )
    alt = evaluate_economic_holdout(
        _inputs(training_tree, harsher), solver_name="highs"
    )
    assert (
        base.correct.committed_flexibility_mw
        == pytest.approx(alt.correct.committed_flexibility_mw, abs=1e-9)
    )
    assert (
        base.b6.committed_flexibility_mw
        == pytest.approx(alt.b6.committed_flexibility_mw, abs=1e-9)
    )


def test_execution_respects_true_shared_budget(training_tree, holdout_tree):
    # Every feasible holdout leaf must satisfy the true joint shared budget
    # c_grid + c_green + l_drop <= committed D^flex, for BOTH policies. The B6
    # error was only in planning; execution physics is always shared.
    result = evaluate_economic_holdout(
        _inputs(training_tree, holdout_tree), solver_name="highs"
    )
    for policy in (result.correct, result.b6):
        budget = policy.committed_flexibility_mw
        for outcome in policy.leaf_outcomes:
            if outcome.feasible:
                used = (
                    outcome.grid_curtailment_mw
                    + outcome.green_shift_mw
                    + outcome.permanent_drop_mw
                )
                assert used <= budget + 1e-6, (policy.variant, outcome.name)


# ---------------------------------------------------------------------------
# Holdout CVaR matches the independent section 13 evaluator
# ---------------------------------------------------------------------------


def test_holdout_cvar_matches_section13_when_all_feasible(training_tree, holdout_tree):
    # The correct policy is feasible on every holdout leaf, so its holdout
    # service-loss CVaR is defined and must equal the independent evaluator's.
    result = evaluate_economic_holdout(
        _inputs(training_tree, holdout_tree), solver_name="highs"
    )
    assert result.correct.holdout_service_cvar is not None
    holdout = {s.name: s for s in holdout_tree}
    losses = [
        ScenarioServiceLoss(
            name=o.name,
            probability=o.probability,
            access_shortfall_mwh=(o.access_shortfall_mw or 0.0) * holdout[o.name].hours,
            grid_curtailment_mwh=(o.grid_curtailment_mw or 0.0) * holdout[o.name].hours,
            green_shift_mwh=(o.green_shift_mw or 0.0) * holdout[o.name].hours,
            permanent_drop_mwh=(o.permanent_drop_mw or 0.0) * holdout[o.name].hours,
            firm_breach_mwh=0.0,
            conditional_breach_mwh=0.0,
        )
        for o in result.correct.leaf_outcomes
    ]
    reference = evaluate_service_cvar(losses, _coefficients(), beta=0.5)
    assert result.correct.holdout_service_cvar == pytest.approx(
        reference.conditional_value_at_risk, rel=1e-6, abs=1e-6
    )


def test_holdout_cvar_is_none_when_any_leaf_fails_hard(training_tree, holdout_tree):
    # B6 has a hard-security failure on the severe leaf, so a finite service-loss
    # CVaR is undefined: the module must report None rather than a spurious value.
    result = evaluate_economic_holdout(
        _inputs(training_tree, holdout_tree), solver_name="highs"
    )
    assert result.b6.holdout_service_cvar is None
    assert result.b6.holdout_value_at_risk is None


# ---------------------------------------------------------------------------
# R3 finding 1: a B6 hard-security failure must count toward under-delivery,
# never mask into a false-negative H2 flag
# ---------------------------------------------------------------------------


def test_hard_failure_leaf_counts_as_shortfall_energy(training_tree, holdout_tree):
    # On the severe holdout leaf B6 fails hard (90 MW need > 60 MW budget). Its
    # full unserved green call (60 MW) must be recorded as access-shortfall
    # energy so the hard failure lands on the *under-delivery* side of the
    # ledger, not silently dropped. The correct policy serves the hard need and
    # only spills part of the green call, so B6's expected shortfall is strictly
    # larger -- H2 cannot be masked into a false negative.
    result = evaluate_economic_holdout(
        _inputs(training_tree, holdout_tree), solver_name="highs"
    )
    b6_severe = next(o for o in result.b6.leaf_outcomes if o.name == "holdout_severe")
    assert b6_severe.hard_security_failure is True
    assert b6_severe.solver_unresolved is False
    # The unserved green call is booked as shortfall energy (60 MW * 1 h).
    assert b6_severe.access_shortfall_mw == pytest.approx(60.0, abs=1e-9)
    assert (
        result.b6.expected_access_shortfall_mwh
        > result.correct.expected_access_shortfall_mwh + 1e-9
    )
    assert result.h2_b6_underdelivers_out_of_sample is True


def test_hard_and_soft_probability_channels_are_disjoint(training_tree, holdout_tree):
    # A hard-failure leaf must not be double counted in both the hard-infeasible
    # and the soft-shortfall probability channels: total = hard + soft with no
    # overlap, and the severe leaf sits only in the hard channel.
    result = evaluate_economic_holdout(
        _inputs(training_tree, holdout_tree), solver_name="highs"
    )
    b6_severe = next(o for o in result.b6.leaf_outcomes if o.name == "holdout_severe")
    assert b6_severe.hard_security_failure is True
    assert b6_severe.service_shortfall_failure is False
    assert result.b6.total_failure_probability == pytest.approx(
        result.b6.hard_infeasible_probability
        + result.b6.service_failure_probability,
        abs=1e-9,
    )


# ---------------------------------------------------------------------------
# R3 finding 2 (downstream): an unresolved recourse solve is never minted into
# a hard-security failure / positive H2 evidence
# ---------------------------------------------------------------------------


def test_unresolved_recourse_is_not_a_hard_failure(
    training_tree, holdout_tree, monkeypatch
):
    from pyomo.opt import TerminationCondition

    import src.models.economic_stochastic as econ

    class _StubResults:
        def __init__(self, termination):
            self.solver = type(
                "_S", (), {"termination_condition": termination, "status": "warning"}
            )()

    class _StubSolver:
        def solve(self, model, tee=False, load_solutions=False):
            return _StubResults(TerminationCondition.maxTimeLimit)

    # Force every solve (planning and recourse) to time out.
    monkeypatch.setattr(econ, "SolverFactory", lambda name: _StubSolver())
    result = evaluate_economic_holdout(
        _inputs(training_tree, holdout_tree), solver_name="highs"
    )
    # Planning itself is unresolved -> training treated as not feasible; H2 is
    # not evaluated and nothing is minted into a hard-security failure.
    assert result.h2_evaluated is False
    assert result.correct.training_feasible is False
    assert result.b6.training_feasible is False


# ---------------------------------------------------------------------------
# Fairness: when B6 does not under-provision, H2 must not be claimed
# ---------------------------------------------------------------------------


def test_no_h2_claim_when_budgets_coincide():
    # With a zero green call the network need alone drives provisioning, the
    # split and joint budgets coincide, both policies commit the same D^flex and
    # execute identically -> no out-of-sample gap, H2 flag must be False.
    training = (
        _scenario("t_mild", 0.5, grid_need_mw=20.0, green_call_mw=0.0),
        _scenario("t_stress", 0.5, grid_need_mw=40.0, green_call_mw=0.0),
    )
    holdout = (
        _scenario("h_mild", 0.5, grid_need_mw=25.0, green_call_mw=0.0),
        _scenario("h_stress", 0.5, grid_need_mw=45.0, green_call_mw=0.0),
    )
    result = evaluate_economic_holdout(_inputs(training, holdout), solver_name="highs")
    assert result.correct.committed_flexibility_mw == pytest.approx(
        result.b6.committed_flexibility_mw, abs=1e-6
    )
    assert result.b6_extra_failure_probability == pytest.approx(0.0, abs=1e-9)
    assert result.b6_extra_expected_shortfall_mwh == pytest.approx(0.0, abs=1e-9)
    assert result.h2_b6_underdelivers_out_of_sample is False


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_training_probabilities_must_sum_to_one(training_tree, holdout_tree):
    bad = (
        replace(training_tree[0], probability=0.5),
        replace(training_tree[1], probability=0.4),
    )
    with pytest.raises(ValueError):
        evaluate_economic_holdout(_inputs(bad, holdout_tree), solver_name="highs")


def test_holdout_probabilities_must_sum_to_one(training_tree, holdout_tree):
    bad = (
        replace(holdout_tree[0], probability=0.4),
        replace(holdout_tree[1], probability=0.4),
        replace(holdout_tree[2], probability=0.1),
    )
    with pytest.raises(ValueError):
        evaluate_economic_holdout(_inputs(training_tree, bad), solver_name="highs")


def test_beta_out_of_range_rejected(training_tree, holdout_tree):
    with pytest.raises(ValueError, match="beta"):
        evaluate_economic_holdout(
            _inputs(training_tree, holdout_tree, beta=1.0), solver_name="highs"
        )


def test_missing_parameter_status_rejected(training_tree, holdout_tree):
    with pytest.raises(ValueError, match="parameter_status"):
        evaluate_economic_holdout(
            _inputs(training_tree, holdout_tree, parameter_status=""),
            solver_name="highs",
        )


def test_empty_holdout_rejected(training_tree):
    with pytest.raises(ValueError, match="holdout_scenarios"):
        evaluate_economic_holdout(_inputs(training_tree, ()), solver_name="highs")
