"""RQ2 shared flexibility budget and the B6 double-commit error baseline.

These tests exercise the formulation.md section 8 (certified shared budget)
and section 10.1 (operational shared MW budget and the B6 error baseline)
extensions on the deterministic F/X evaluator. They deliberately use the
two-line synthetic grid so the certified sustained-state curtailment that a
full contract requires is hand-computable: with one corridor line out and a
sustained rating of 40 MW, certifying the full 80 MW contract forces exactly
40 MW of certified grid curtailment.

The scientific point is mechanism-only and synthetic: it shows that a positive
green/CFE deferral call that shares the same MW budget reduces the network
curtailment headroom, so the correct joint budget refuses an X level that the
B6 split-budget baseline still certifies. It is not a probability, a contract
capability, or an hourly network certification.
"""

from dataclasses import replace

import pytest

from src.grid import Branch, Bus, Generator, Rts24Data
from src.models import (
    ExistingBranchUpgrade,
    FixedFxPlan,
    FixedPoi,
    FxQuarter,
    FxServiceEnvelope,
    SharedFlexibilityBudget,
    evaluate_deterministic_fx_plan,
)


PARAMETER_STATUS = "synthetic_test_only_not_for_engineering"
RESPONSE_MODEL = "mw_only_sustained_states_no_duration_or_energy_limits"


@pytest.fixture
def two_line_grid():
    return Rts24Data(
        base_mva=100.0,
        buses=(
            Bus(index=1, demand_mw=0.0),
            Bus(index=2, demand_mw=0.0),
        ),
        generators=(
            Generator(
                index=0,
                bus=1,
                p_min_mw=0.0,
                p_max_mw=100.0,
                cost_quadratic=0.0,
                cost_linear=10.0,
                cost_constant=0.0,
                ramp_10_mw=None,
                ramp_30_mw=None,
                in_service=True,
            ),
        ),
        branches=tuple(
            Branch(
                index=index,
                from_bus=1,
                to_bus=2,
                reactance_pu=0.1,
                rate_a_mw=40.0,
                rate_b_mw=40.0,
                rate_c_mw=80.0,
                tap_ratio=1.0,
                phase_shift_rad=0.0,
                in_service=True,
            )
            for index in range(2)
        ),
        reference_bus=1,
        source_package="synthetic_test",
        source_version="1",
    )


def _quarters(demands_mw):
    return tuple(
        FxQuarter(
            name=f"q{index}",
            system_load_multiplier=1.0,
            data_center_demand_mw=float(demand),
            operating_hours=1.0,
            continuous_validation_hours=1.0,
            discount_factor=1.0,
        )
        for index, demand in enumerate(demands_mw)
    )


def _poi():
    return FixedPoi(
        bus=2,
        initial_capacity_mw=80.0,
        application_capacity_mw=80.0,
    )


def _project():
    return ExistingBranchUpgrade(
        name="two_line_corridor_upgrade",
        lead_time_quarters=1,
        rate_a_increase_mw={0: 0.0, 1: 0.0},
        rate_c_increase_mw={0: 0.0, 1: 0.0},
        poi_capacity_increase_mw=0.0,
        investment_cost=0.0,
        parameter_status=PARAMETER_STATUS,
    )


def _service_envelope():
    return FxServiceEnvelope(
        max_conditional_capacity_mw=40.0,
        minimum_operational_block_mw=40.0,
        minimum_validation_hours=1.0,
        response_model=RESPONSE_MODEL,
        parameter_status=PARAMETER_STATUS,
    )


def _plan(firm, conditional, *, project_start_quarter=None):
    return FixedFxPlan(
        firm_capacity_mw=firm,
        conditional_capacity_mw=conditional,
        project_start_quarter=project_start_quarter,
        parameter_status=PARAMETER_STATUS,
    )


def _budget(
    *,
    flexibility_budget_mw,
    green_call_mw,
    enforce_joint_budget,
    certified_flexibility_budget_mw=None,
    connected_demand_budget_mw=None,
):
    return SharedFlexibilityBudget(
        flexibility_budget_mw=flexibility_budget_mw,
        certified_flexibility_budget_mw=(
            flexibility_budget_mw
            if certified_flexibility_budget_mw is None
            else certified_flexibility_budget_mw
        ),
        green_call_mw=green_call_mw,
        connected_demand_budget_mw=connected_demand_budget_mw,
        enforce_joint_budget=enforce_joint_budget,
        parameter_status=PARAMETER_STATUS,
    )


def _evaluate(data, *, quarters, plan, shared_flexibility_budget=None):
    redispatch = {
        generator.index: generator.p_max_mw for generator in data.generators
    }
    return evaluate_deterministic_fx_plan(
        data,
        quarters=quarters,
        poi=_poi(),
        project=_project(),
        plan=plan,
        service_envelope=_service_envelope(),
        redispatch_up_mw=redispatch,
        redispatch_down_mw=redispatch,
        access_shortfall_cost_per_mwh=1_000.0,
        branch_indices=(0, 1),
        generator_indices=(),
        immediate_rating="rate_c",
        sustained_rating="rate_a",
        primary_objective_tolerance=1.0e-7,
        solver_name="highs",
        shared_flexibility_budget=shared_flexibility_budget,
    )


def test_slack_budget_reproduces_the_no_budget_certification(two_line_grid):
    """A budget wider than any call must not change the certified result."""
    quarters = _quarters((80.0,))
    plan = _plan({"q0": 40.0}, {"q0": 40.0})

    baseline = _evaluate(two_line_grid, quarters=quarters, plan=plan)
    with_slack = _evaluate(
        two_line_grid,
        quarters=quarters,
        plan=plan,
        shared_flexibility_budget=_budget(
            flexibility_budget_mw={"q0": 1_000.0},
            green_call_mw={"q0": 0.0},
            enforce_joint_budget=True,
        ),
    )

    assert baseline.feasible
    assert with_slack.feasible
    for state in ("branch_0_sustained", "branch_1_sustained"):
        assert with_slack.certified_grid_curtailment_mw["q0"][state] == (
            pytest.approx(
                baseline.certified_grid_curtailment_mw["q0"][state]
            )
        )
        assert with_slack.actual_grid_curtailment_mw["q0"][state] == (
            pytest.approx(baseline.actual_grid_curtailment_mw["q0"][state])
        )


def test_joint_budget_rejects_x_that_b6_double_commits(two_line_grid):
    """The RQ2 mechanism: the correct joint budget refuses an X level that
    the B6 split-budget baseline certifies by double-committing the budget.

    Certifying the full 80 MW contract needs 40 MW of sustained-state grid
    curtailment. With a shared certified budget of 40 MW and a competing 20 MW
    green/CFE deferral call, the joint constraint leaves only 20 MW for grid
    curtailment, which cannot deliver the contract under one-line-out ratings,
    so the correct model is infeasible. B6 drops the joint constraint and lets
    grid curtailment use the full 40 MW while the green call also draws on it,
    so B6 wrongly certifies the same X.
    """
    quarters = _quarters((80.0,))
    plan = _plan({"q0": 40.0}, {"q0": 40.0})

    correct = _evaluate(
        two_line_grid,
        quarters=quarters,
        plan=plan,
        shared_flexibility_budget=_budget(
            flexibility_budget_mw={"q0": 40.0},
            green_call_mw={"q0": 20.0},
            enforce_joint_budget=True,
        ),
    )
    b6 = _evaluate(
        two_line_grid,
        quarters=quarters,
        plan=plan,
        shared_flexibility_budget=_budget(
            flexibility_budget_mw={"q0": 40.0},
            green_call_mw={"q0": 20.0},
            enforce_joint_budget=False,
        ),
    )

    assert not correct.feasible
    assert b6.feasible
    for state in ("branch_0_sustained", "branch_1_sustained"):
        assert b6.certified_grid_curtailment_mw["q0"][state] == pytest.approx(
            40.0
        )
        assert b6.certified_poi_load_mw["q0"][state] == pytest.approx(40.0)


def test_joint_budget_still_certifies_when_headroom_is_sufficient(
    two_line_grid,
):
    """When the shared budget covers both the grid and green calls, the
    correct joint model certifies exactly the same X as the no-budget case."""
    quarters = _quarters((80.0,))
    plan = _plan({"q0": 40.0}, {"q0": 40.0})

    correct = _evaluate(
        two_line_grid,
        quarters=quarters,
        plan=plan,
        shared_flexibility_budget=_budget(
            flexibility_budget_mw={"q0": 60.0},
            green_call_mw={"q0": 20.0},
            enforce_joint_budget=True,
        ),
    )

    assert correct.feasible
    for state in ("branch_0_sustained", "branch_1_sustained"):
        assert correct.certified_grid_curtailment_mw["q0"][state] == (
            pytest.approx(40.0)
        )
        assert correct.certified_poi_load_mw["q0"][state] == pytest.approx(
            40.0
        )


def test_actual_operation_shares_the_budget_with_green_calls(two_line_grid):
    """Section 10.1 also constrains the actual-operation curtailment. With
    the full 80 MW demand connected, the actual sustained-state curtailment of
    40 MW plus a 20 MW green call exceeds a 40 MW joint budget, so the correct
    model is infeasible while B6 remains feasible."""
    quarters = _quarters((80.0,))
    plan = _plan({"q0": 40.0}, {"q0": 40.0})

    correct = _evaluate(
        two_line_grid,
        quarters=quarters,
        plan=plan,
        shared_flexibility_budget=_budget(
            flexibility_budget_mw={"q0": 40.0},
            green_call_mw={"q0": 20.0},
            enforce_joint_budget=True,
        ),
    )
    b6 = _evaluate(
        two_line_grid,
        quarters=quarters,
        plan=plan,
        shared_flexibility_budget=_budget(
            flexibility_budget_mw={"q0": 40.0},
            green_call_mw={"q0": 20.0},
            enforce_joint_budget=False,
        ),
    )

    assert not correct.feasible
    assert b6.feasible
    for state in ("branch_0_sustained", "branch_1_sustained"):
        assert b6.actual_grid_curtailment_mw["q0"][state] == pytest.approx(
            40.0
        )


def test_budget_keys_must_match_quarters(two_line_grid):
    quarters = _quarters((80.0,))
    plan = _plan({"q0": 40.0}, {"q0": 40.0})

    with pytest.raises(ValueError, match="every quarter"):
        _evaluate(
            two_line_grid,
            quarters=quarters,
            plan=plan,
            shared_flexibility_budget=_budget(
                flexibility_budget_mw={"q9": 40.0},
                green_call_mw={"q0": 0.0},
                enforce_joint_budget=True,
            ),
        )


def test_budget_rejects_negative_values(two_line_grid):
    quarters = _quarters((80.0,))
    plan = _plan({"q0": 40.0}, {"q0": 40.0})

    with pytest.raises(ValueError):
        _evaluate(
            two_line_grid,
            quarters=quarters,
            plan=plan,
            shared_flexibility_budget=_budget(
                flexibility_budget_mw={"q0": -1.0},
                green_call_mw={"q0": 0.0},
                enforce_joint_budget=True,
            ),
        )


def test_budget_parameter_status_must_be_explicit(two_line_grid):
    quarters = _quarters((80.0,))
    plan = _plan({"q0": 40.0}, {"q0": 40.0})

    with pytest.raises(ValueError, match="parameter status"):
        _evaluate(
            two_line_grid,
            quarters=quarters,
            plan=plan,
            shared_flexibility_budget=replace(
                _budget(
                    flexibility_budget_mw={"q0": 40.0},
                    green_call_mw={"q0": 0.0},
                    enforce_joint_budget=True,
                ),
                parameter_status="",
            ),
        )
