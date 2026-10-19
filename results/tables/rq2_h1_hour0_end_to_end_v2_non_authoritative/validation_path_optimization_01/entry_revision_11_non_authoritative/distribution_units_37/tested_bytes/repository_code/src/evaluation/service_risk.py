"""Service/business-loss CVaR post-processing (formulation.md section 13).

This module evaluates the section 13 service-loss risk measure

    L_omega = sum over (k, w, t) of weight * dt * (
        kappa_access * u_access + kappa_grid * c_grid + kappa_green * c_green
        + kappa_drop * l_drop + kappa_breach_F * u_F + kappa_breach_X * u_X )

    zeta_omega >= L_omega - eta_VaR,  zeta_omega >= 0
    CVaR_beta(L) = eta_VaR + 1 / (1 - beta) * sum_omega p_omega * zeta_omega

as a deterministic post-processing metric over a *given* discrete scenario
loss distribution. It does not choose planning decisions and it is not wired
into any optimizer objective here; wiring CVaR into
``min C^grid + C^op + lambda^risk * CVaR_beta(L)`` (section 14) changes the
frozen B3/B4 objective and must be done under a formal re-run, not on this
metric-only path.

Two invariants from ``agent.md`` section 8 / section 14 are enforced
structurally: CVaR is computed **only** from service and business-loss
energies (access shortfall, grid curtailment, green/CFE shifting, permanent
drop, firm breach and conditional breach); no thermal, branch, transformer,
POI or N-1 limit ever enters this measure, so it cannot relax hard security.
The result is a synthetic derived risk metric, not a certification.

The Rockafellar-Uryasev objective ``g(eta) = eta + 1 / (1 - beta) *
sum_omega p_omega * (L_omega - eta)^+`` is piecewise-linear and convex in the
free variable ``eta``, with breakpoints only at the realised loss levels, so
its minimiser (the beta-VaR) and minimum (the beta-CVaR) are attained at one
of those distinct levels. This lets the linear program in section 13 be
solved in closed form, which keeps the metric exactly reproducible without a
solver.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import Iterable


SERVICE_LOSS_RISK_SCOPE = (
    "synthetic_service_and_business_loss_cvar_post_processing_metric_"
    "not_a_thermal_or_n1_relaxation_and_not_a_certification"
)

_PROBABILITY_TOLERANCE = 1.0e-9


@dataclass(frozen=True)
class ServiceLossCoefficients:
    """Section 13/14 service and business-loss cost coefficients (per MWh).

    Every coefficient is a cost weight applied to a service/business-loss
    energy. ``agent.md`` section 14 requires these ranges to be frozen before
    results are seen; the caller owns that freeze and records it through
    ``parameter_status``. No thermal, security or investment quantity is
    admitted here, so this measure cannot relax a hard limit.
    """

    kappa_access: float
    kappa_grid: float
    kappa_green: float
    kappa_drop: float
    kappa_breach_firm: float
    kappa_breach_conditional: float
    parameter_status: str


@dataclass(frozen=True)
class ScenarioServiceLoss:
    """One long-horizon path ``omega`` with its aggregated loss energies.

    Each energy is the (k, w, t) aggregate in MWh that already folds in the
    representative-week weight and the time step ``dt``. ``probability`` is the
    scenario probability ``p_omega`` used in the outer CVaR expectation; it is
    kept separate from the inner week weight so the two are never conflated.
    """

    name: str
    probability: float
    access_shortfall_mwh: float
    grid_curtailment_mwh: float
    green_shift_mwh: float
    permanent_drop_mwh: float
    firm_breach_mwh: float
    conditional_breach_mwh: float


@dataclass(frozen=True)
class ServiceCvarResult:
    beta: float
    expected_loss: float
    value_at_risk: float
    conditional_value_at_risk: float
    loss_by_scenario: dict[str, float]
    tail_excess_by_scenario: dict[str, float]
    tail_probability: float
    scenario_count: int
    coefficient_parameter_status: str
    risk_measure_scope: str


def _finite(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def _nonnegative_finite(name: str, value: object) -> float:
    number = _finite(name, value)
    if number < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return number


def _validate_coefficients(
    coefficients: ServiceLossCoefficients,
) -> ServiceLossCoefficients:
    if not coefficients.parameter_status:
        raise ValueError("Service loss coefficient parameter status must be explicit")
    for name, value in (
        ("kappa_access", coefficients.kappa_access),
        ("kappa_grid", coefficients.kappa_grid),
        ("kappa_green", coefficients.kappa_green),
        ("kappa_drop", coefficients.kappa_drop),
        ("kappa_breach_firm", coefficients.kappa_breach_firm),
        ("kappa_breach_conditional", coefficients.kappa_breach_conditional),
    ):
        _nonnegative_finite(name, value)
    return coefficients


def service_loss_value(
    coefficients: ServiceLossCoefficients,
    scenario: ScenarioServiceLoss,
) -> float:
    """Return the section 13 aggregated loss ``L_omega`` for one scenario."""
    _validate_coefficients(coefficients)
    return (
        coefficients.kappa_access
        * _nonnegative_finite("access_shortfall_mwh", scenario.access_shortfall_mwh)
        + coefficients.kappa_grid
        * _nonnegative_finite("grid_curtailment_mwh", scenario.grid_curtailment_mwh)
        + coefficients.kappa_green
        * _nonnegative_finite("green_shift_mwh", scenario.green_shift_mwh)
        + coefficients.kappa_drop
        * _nonnegative_finite("permanent_drop_mwh", scenario.permanent_drop_mwh)
        + coefficients.kappa_breach_firm
        * _nonnegative_finite("firm_breach_mwh", scenario.firm_breach_mwh)
        + coefficients.kappa_breach_conditional
        * _nonnegative_finite(
            "conditional_breach_mwh", scenario.conditional_breach_mwh
        )
    )


def evaluate_service_cvar(
    scenarios: Iterable[ScenarioServiceLoss],
    coefficients: ServiceLossCoefficients,
    *,
    beta: float,
) -> ServiceCvarResult:
    """Evaluate the section 13 beta-CVaR of the service/business loss.

    The measure is computed in closed form as the minimum of the
    Rockafellar-Uryasev objective over its loss-level breakpoints, which is
    exactly the linear program in section 13. ``beta`` in ``[0, 1)`` selects
    the tail: ``beta = 0`` returns the expected loss and larger ``beta`` moves
    toward the worst realised loss.
    """

    coefficients = _validate_coefficients(coefficients)
    beta = _finite("beta", beta)
    if not 0.0 <= beta < 1.0:
        raise ValueError("CVaR confidence level beta must lie in [0, 1)")

    scenarios = tuple(scenarios)
    if not scenarios:
        raise ValueError("At least one scenario loss is required")
    names = tuple(scenario.name for scenario in scenarios)
    if any(not name for name in names) or len(set(names)) != len(names):
        raise ValueError("Scenario names must be nonempty and unique")

    probabilities = {}
    losses = {}
    for scenario in scenarios:
        probability = _finite(f"probability[{scenario.name}]", scenario.probability)
        if probability <= 0.0:
            raise ValueError("Scenario probabilities must be strictly positive")
        probabilities[scenario.name] = probability
        losses[scenario.name] = service_loss_value(coefficients, scenario)
    total_probability = sum(probabilities.values())
    if abs(total_probability - 1.0) > _PROBABILITY_TOLERANCE:
        raise ValueError("Scenario probabilities must sum to one")

    expected_loss = sum(
        probabilities[name] * losses[name] for name in names
    )

    def ru_objective(eta: float) -> float:
        excess = sum(
            probabilities[name] * max(losses[name] - eta, 0.0) for name in names
        )
        return eta + excess / (1.0 - beta)

    # g(eta) is piecewise-linear and convex, and its set of minimisers is a
    # closed interval whose left endpoint is the beta-VaR quantile (Rockafellar
    # & Uryasev 2000). So the beta-VaR is the smallest realised loss level
    # whose cumulative probability reaches beta, and evaluating g there gives
    # the closed-form beta-CVaR minimum.
    distinct_losses = sorted(set(losses.values()))
    probability_by_loss: dict[float, float] = {}
    for name in names:
        probability_by_loss[losses[name]] = (
            probability_by_loss.get(losses[name], 0.0) + probabilities[name]
        )
    cumulative = 0.0
    value_at_risk = distinct_losses[-1]
    for candidate in distinct_losses:
        cumulative += probability_by_loss[candidate]
        if cumulative >= beta - _PROBABILITY_TOLERANCE:
            value_at_risk = candidate
            break

    conditional_value_at_risk = ru_objective(value_at_risk)
    tail_excess = {
        name: max(losses[name] - value_at_risk, 0.0) for name in names
    }
    tail_probability = sum(
        probabilities[name] for name in names if losses[name] > value_at_risk
    )

    return ServiceCvarResult(
        beta=beta,
        expected_loss=expected_loss,
        value_at_risk=value_at_risk,
        conditional_value_at_risk=conditional_value_at_risk,
        loss_by_scenario=dict(losses),
        tail_excess_by_scenario=tail_excess,
        tail_probability=tail_probability,
        scenario_count=len(scenarios),
        coefficient_parameter_status=coefficients.parameter_status,
        risk_measure_scope=SERVICE_LOSS_RISK_SCOPE,
    )


__all__ = [
    "SERVICE_LOSS_RISK_SCOPE",
    "ScenarioServiceLoss",
    "ServiceCvarResult",
    "ServiceLossCoefficients",
    "evaluate_service_cvar",
    "service_loss_value",
]
