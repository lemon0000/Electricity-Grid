"""Section 13 service/business-loss CVaR post-processing tests.

The analytic targets are hand-computed from the Rockafellar-Uryasev formula

    CVaR_beta(L) = min_eta [ eta + 1 / (1 - beta) * sum_omega p_omega (L_omega - eta)^+ ]

so the closed-form implementation is checked against the definition rather
than against itself. The scientific point is mechanism-only: CVaR is a tail
statistic of a *given* service/business-loss distribution and never touches a
thermal or N-1 limit.
"""

from dataclasses import replace

import pytest

from src.evaluation import (
    SERVICE_LOSS_RISK_SCOPE,
    ScenarioServiceLoss,
    ServiceLossCoefficients,
    evaluate_service_cvar,
    service_loss_value,
)


PARAMETER_STATUS = "synthetic_test_only_not_for_engineering"


def _coefficients(**overrides):
    base = dict(
        kappa_access=1.0,
        kappa_grid=0.0,
        kappa_green=0.0,
        kappa_drop=0.0,
        kappa_breach_firm=0.0,
        kappa_breach_conditional=0.0,
        parameter_status=PARAMETER_STATUS,
    )
    base.update(overrides)
    return ServiceLossCoefficients(**base)


def _access_scenario(name, probability, access_mwh):
    return ScenarioServiceLoss(
        name=name,
        probability=probability,
        access_shortfall_mwh=access_mwh,
        grid_curtailment_mwh=0.0,
        green_shift_mwh=0.0,
        permanent_drop_mwh=0.0,
        firm_breach_mwh=0.0,
        conditional_breach_mwh=0.0,
    )


def _uniform_ladder():
    """Four equiprobable scenarios with losses 10, 20, 30, 40 MWh-cost."""
    return tuple(
        _access_scenario(f"s{index}", 0.25, loss)
        for index, loss in enumerate((10.0, 20.0, 30.0, 40.0))
    )


def test_beta_zero_returns_the_expected_loss():
    result = evaluate_service_cvar(_uniform_ladder(), _coefficients(), beta=0.0)
    assert result.expected_loss == pytest.approx(25.0)
    assert result.conditional_value_at_risk == pytest.approx(25.0)
    assert result.value_at_risk == pytest.approx(10.0)
    assert result.risk_measure_scope == SERVICE_LOSS_RISK_SCOPE


def test_median_tail_averages_the_worst_half():
    result = evaluate_service_cvar(_uniform_ladder(), _coefficients(), beta=0.5)
    # VaR is the 0.5-quantile = 20; the tail beyond it is {30, 40} with equal
    # weight, so CVaR is their mean, 35.
    assert result.value_at_risk == pytest.approx(20.0)
    assert result.conditional_value_at_risk == pytest.approx(35.0)
    assert result.tail_probability == pytest.approx(0.5)


def test_upper_quartile_tail_isolates_the_worst_scenario():
    result = evaluate_service_cvar(_uniform_ladder(), _coefficients(), beta=0.75)
    # The 0.75-quantile is 30 and the mass strictly above it is exactly 1-beta,
    # so CVaR equals the single worst loss, 40.
    assert result.value_at_risk == pytest.approx(30.0)
    assert result.conditional_value_at_risk == pytest.approx(40.0)
    assert result.tail_probability == pytest.approx(0.25)
    assert result.tail_excess_by_scenario["s3"] == pytest.approx(10.0)
    assert result.tail_excess_by_scenario["s2"] == pytest.approx(0.0)


def test_cvar_is_nondecreasing_in_beta_and_dominates_the_mean():
    scenarios = _uniform_ladder()
    coefficients = _coefficients()
    previous = evaluate_service_cvar(scenarios, coefficients, beta=0.0)
    for beta in (0.25, 0.5, 0.75, 0.9):
        current = evaluate_service_cvar(scenarios, coefficients, beta=beta)
        assert (
            current.conditional_value_at_risk
            >= previous.conditional_value_at_risk - 1.0e-9
        )
        assert (
            current.conditional_value_at_risk
            >= current.expected_loss - 1.0e-9
        )
        assert (
            current.conditional_value_at_risk
            >= current.value_at_risk - 1.0e-9
        )
        previous = current


def test_nonuniform_tail_matches_the_closed_form():
    scenarios = (
        _access_scenario("calm", 0.9, 0.0),
        _access_scenario("crisis", 0.1, 100.0),
    )
    coefficients = _coefficients()

    at_80 = evaluate_service_cvar(scenarios, coefficients, beta=0.8)
    # VaR = 0 (its cumulative mass 0.9 already covers beta); CVaR = 0 +
    # (1/0.2) * 0.1 * 100 = 50.
    assert at_80.value_at_risk == pytest.approx(0.0)
    assert at_80.conditional_value_at_risk == pytest.approx(50.0)

    at_95 = evaluate_service_cvar(scenarios, coefficients, beta=0.95)
    # Once beta exceeds the calm mass, only the crisis loss remains in the
    # tail, so CVaR saturates at the worst realisation.
    assert at_95.value_at_risk == pytest.approx(100.0)
    assert at_95.conditional_value_at_risk == pytest.approx(100.0)


def test_single_scenario_is_degenerate():
    result = evaluate_service_cvar(
        (_access_scenario("only", 1.0, 42.0),),
        _coefficients(),
        beta=0.9,
    )
    assert result.expected_loss == pytest.approx(42.0)
    assert result.value_at_risk == pytest.approx(42.0)
    assert result.conditional_value_at_risk == pytest.approx(42.0)
    assert result.tail_probability == pytest.approx(0.0)


def test_all_loss_components_are_aggregated():
    coefficients = _coefficients(
        kappa_access=1.0,
        kappa_grid=2.0,
        kappa_green=0.5,
        kappa_drop=3.0,
        kappa_breach_firm=10.0,
        kappa_breach_conditional=4.0,
    )
    scenario = ScenarioServiceLoss(
        name="mix",
        probability=1.0,
        access_shortfall_mwh=1.0,
        grid_curtailment_mwh=2.0,
        green_shift_mwh=4.0,
        permanent_drop_mwh=1.0,
        firm_breach_mwh=0.5,
        conditional_breach_mwh=1.0,
    )
    # 1*1 + 2*2 + 0.5*4 + 3*1 + 10*0.5 + 4*1 = 1 + 4 + 2 + 3 + 5 + 4 = 19.
    assert service_loss_value(coefficients, scenario) == pytest.approx(19.0)
    result = evaluate_service_cvar((scenario,), coefficients, beta=0.5)
    assert result.conditional_value_at_risk == pytest.approx(19.0)


def test_probabilities_must_sum_to_one():
    with pytest.raises(ValueError, match="sum to one"):
        evaluate_service_cvar(
            (
                _access_scenario("a", 0.4, 10.0),
                _access_scenario("b", 0.4, 20.0),
            ),
            _coefficients(),
            beta=0.5,
        )


def test_probabilities_must_be_positive():
    with pytest.raises(ValueError, match="strictly positive"):
        evaluate_service_cvar(
            (
                _access_scenario("a", 1.0, 10.0),
                _access_scenario("b", 0.0, 20.0),
            ),
            _coefficients(),
            beta=0.5,
        )


def test_beta_must_be_in_unit_interval():
    scenarios = _uniform_ladder()
    for beta in (-0.1, 1.0, 1.5):
        with pytest.raises(ValueError, match="beta"):
            evaluate_service_cvar(scenarios, _coefficients(), beta=beta)


def test_scenario_names_must_be_unique():
    with pytest.raises(ValueError, match="unique"):
        evaluate_service_cvar(
            (
                _access_scenario("dup", 0.5, 10.0),
                _access_scenario("dup", 0.5, 20.0),
            ),
            _coefficients(),
            beta=0.5,
        )


def test_empty_scenarios_are_rejected():
    with pytest.raises(ValueError, match="At least one scenario"):
        evaluate_service_cvar((), _coefficients(), beta=0.5)


def test_negative_coefficients_are_rejected():
    with pytest.raises(ValueError, match="kappa_grid"):
        evaluate_service_cvar(
            _uniform_ladder(),
            _coefficients(kappa_grid=-1.0),
            beta=0.5,
        )


def test_negative_energies_are_rejected():
    with pytest.raises(ValueError, match="access_shortfall_mwh"):
        evaluate_service_cvar(
            (_access_scenario("a", 1.0, -5.0),),
            _coefficients(),
            beta=0.5,
        )


def test_coefficient_parameter_status_must_be_explicit():
    with pytest.raises(ValueError, match="parameter status"):
        evaluate_service_cvar(
            _uniform_ladder(),
            replace(_coefficients(), parameter_status=""),
            beta=0.5,
        )
