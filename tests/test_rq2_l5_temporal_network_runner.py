"""End-to-end tests for the network-derived chronological RQ2 L5 runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.grid import Branch, Bus, Generator, Rts24Data


@pytest.fixture
def two_line_grid() -> Rts24Data:
    return Rts24Data(
        base_mva=100.0,
        buses=(Bus(1, 0.0), Bus(2, 0.0)),
        generators=(
            Generator(0, 1, 0.0, 100.0, 0.0, 10.0, 0.0, None, None, True),
        ),
        branches=(
            Branch(0, 1, 2, 0.1, 40.0, 40.0, 80.0, 1.0, 0.0, True),
            Branch(1, 1, 2, 0.1, 40.0, 40.0, 80.0, 1.0, 0.0, True),
        ),
        reference_bus=1,
        source_package="synthetic_test",
        source_version="1",
    )


def test_runner_derives_event_hour_need_and_quantifies_b6_underprovision(
    tmp_path: Path, two_line_grid: Rts24Data, monkeypatch
):
    yaml = pytest.importorskip("yaml")
    from experiments import run_rq2_l5_economic_temporal_network as runner

    output = tmp_path / "summary.json"
    config = {
        "evaluation": {
            "id": "temporal_network_test",
            "parameter_status": "synthetic_test_derived_not_empirical",
            "security_certified": False,
        },
        "network": {
            "case_name": "case24_ieee_rts",
            "poi_bus": 2,
            "balancing_bus": 1,
            "methods": ["minimum_curtailment", "overload_sensitivity"],
            "branch_indices": [0],
            "generator_indices": [],
            "redispatch_fraction_of_pmax": 1.0,
            "sustained_rating": "rate_a",
            "parameter_status": "derived_not_empirical_outage",
        },
        "model": {
            "max_flexibility_budget_mw": 100.0,
            "provisioning_cost_per_mw": 10.0,
            "lambda_risk": 0.0,
            "beta": 0.5,
            "solver_name": "highs",
        },
        "coefficients": {
            "kappa_access": 1000.0,
            "kappa_grid": 10.0,
            "kappa_green": 5.0,
            "kappa_drop": 2000.0,
            "kappa_breach_firm": 0.0,
            "kappa_breach_conditional": 0.0,
            "parameter_status": "synthetic_test",
        },
        "envelope": {
            "time_step_hours": 1.0,
            "maximum_event_duration_hours": 2.0,
            "minimum_recovery_hours": 1.0,
            "maximum_events_by_period": {"q1": 1},
            "maximum_curtailment_energy_mwh_by_period": {"q1": 100.0},
            "maximum_recovery_debt_mwh": 100.0,
            "maximum_recovery_power_mw": 60.0,
            "minimum_event_power_mw": 1.0,
            "response_time_hours": 1.0,
            "curtailment_ramp_mw_per_hour": 100.0,
            "recovery_efficiency": 1.0,
            "terminal_debt_limit_mwh_by_period": {"q1": 0.0},
            "parameter_status": "synthetic_test",
        },
        "scenarios": [
            {
                "name": "stress",
                "probability": 1.0,
                "periods": ["q1", "q1", "q1", "q1"],
                "system_load_multiplier": [1.0, 1.0, 1.0, 1.0],
                "data_center_demand_mw": [80.0, 80.0, 80.0, 80.0],
                "network_call_active": [0, 1, 0, 0],
                "green_call_mw": [0.0, 20.0, 0.0, 0.0],
                "connected_demand_mw": [80.0, 80.0, 80.0, 80.0],
                "recovery_headroom_mw": [0.0, 0.0, 60.0, 60.0],
                "completed_periods": ["q1"],
                "require_terminal_event_inactive": True,
                "boundary_state_status": "clean_boundary_with_zero_carry_in",
            }
        ],
        "output": {"summary_path": str(output)},
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setattr(runner, "load_rts24", lambda: two_line_grid)

    summary = runner.run(path)

    assert summary["gate_passed"]
    assert summary["security_certified"] is False
    assert summary["effective_config"]["evaluation"]["id"] == (
        "temporal_network_test"
    )
    assert summary["effective_config"]["model"]["fixed_flexibility_mw"] is None
    assert len(summary["config_sha256"]) == 64
    for method in ("minimum_curtailment", "overload_sensitivity"):
        method_result = summary["methods"][method]
        assert method_result["derived_grid_need_mw"]["stress"] == pytest.approx(
            [0.0, 40.0, 0.0, 0.0]
        )
        assert method_result["correct"]["provisioned_flexibility_mw"] == (
            pytest.approx(60.0)
        )
        assert method_result["b6"]["provisioned_flexibility_mw"] == (
            pytest.approx(40.0)
        )
        assert method_result[
            "h1_b6_flexibility_underprovisioning_mw"
        ] == pytest.approx(20.0)
        assert method_result["solver_and_internal_audit_gate_passed"]
        assert method_result["b6_physical_replay_passed"] is False
        assert method_result["b6"]["maximum_physical_budget_excess_mw"] == (
            pytest.approx(20.0)
        )
        b6_dispatch = method_result["b6"]["scenario_dispatch"]["stress"]
        assert b6_dispatch["physical_envelope_feasible"] is False
        assert any(
            "call_limit_exceeded" in violation
            for violation in b6_dispatch["physical_envelope_violations"]
        )
    assert json.loads(output.read_text(encoding="utf-8")) == summary


def test_runner_rejects_nonbinary_network_call_indicator(tmp_path: Path):
    yaml = pytest.importorskip("yaml")
    from experiments import run_rq2_l5_economic_temporal_network as runner

    config = {
        "evaluation": {
            "id": "bad",
            "parameter_status": "synthetic",
            "security_certified": False,
        },
        "network": {
            "case_name": "case24_ieee_rts",
            "poi_bus": 8,
            "balancing_bus": 13,
            "methods": ["minimum_curtailment"],
            "branch_indices": [0],
            "generator_indices": [],
            "redispatch_fraction_of_pmax": 0.5,
            "sustained_rating": "rate_a",
            "parameter_status": "synthetic",
        },
        "model": {
            "max_flexibility_budget_mw": 100.0,
            "provisioning_cost_per_mw": 10.0,
            "lambda_risk": 0.0,
            "beta": 0.5,
            "solver_name": "highs",
        },
        "coefficients": {
            "kappa_access": 1.0,
            "kappa_grid": 1.0,
            "kappa_green": 1.0,
            "kappa_drop": 1.0,
            "kappa_breach_firm": 0.0,
            "kappa_breach_conditional": 0.0,
            "parameter_status": "synthetic",
        },
        "envelope": {
            "time_step_hours": 1.0,
            "maximum_event_duration_hours": 1.0,
            "minimum_recovery_hours": 1.0,
            "maximum_events_by_period": {"q1": 1},
            "maximum_curtailment_energy_mwh_by_period": {"q1": 100.0},
            "maximum_recovery_debt_mwh": 100.0,
            "maximum_recovery_power_mw": 100.0,
            "minimum_event_power_mw": 1.0,
            "response_time_hours": 1.0,
            "curtailment_ramp_mw_per_hour": 100.0,
            "recovery_efficiency": 1.0,
            "terminal_debt_limit_mwh_by_period": {"q1": 0.0},
            "parameter_status": "synthetic",
        },
        "scenarios": [
            {
                "name": "bad",
                "probability": 1.0,
                "periods": ["q1"],
                "system_load_multiplier": [0.8],
                "data_center_demand_mw": [50.0],
                "network_call_active": [0.5],
                "green_call_mw": [0.0],
                "connected_demand_mw": [50.0],
                "recovery_headroom_mw": [0.0],
                "completed_periods": ["q1"],
                "boundary_state_status": "clean_boundary_with_zero_carry_in",
            }
        ],
        "output": {"summary_path": str(tmp_path / "summary.json")},
    }
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")

    with pytest.raises(ValueError, match="network_call_active must contain 0 or 1"):
        runner.run(path)


def test_network_indices_reject_fractional_values():
    from experiments import run_rq2_l5_economic_temporal_network as runner

    for bad in ([1.5], [True]):
        with pytest.raises(TypeError, match="integer list"):
            runner._integer_tuple(bad, "branch_indices")
    for bad in (8.9, True):
        with pytest.raises(TypeError, match="must be an integer"):
            runner._integer(bad, "poi_bus")


def test_temporal_runner_rejects_hand_entered_grid_need():
    from experiments import run_rq2_l5_economic_temporal_network as runner

    with pytest.raises(ValueError, match="forbids hand-entered grid_need_mw"):
        runner._raw_scenarios(
            [
                {
                    "name": "forbidden",
                    "grid_need_mw": [40.0],
                }
            ]
        )


def test_network_selection_is_validated_before_event_activation(two_line_grid):
    from experiments import run_rq2_l5_economic_temporal_network as runner

    with pytest.raises(ValueError, match="unknown branch"):
        runner._validate_network_selection(
            two_line_grid,
            poi_bus=2,
            balancing_bus=1,
            branch_indices=(999,),
            generator_indices=(),
            sustained_rating="rate_a",
        )


def test_inactive_hour_still_requires_normal_state_feasibility(two_line_grid):
    from experiments import run_rq2_l5_economic_temporal_network as runner

    with pytest.raises(RuntimeError, match="normal-state DC-OPF failed"):
        runner._derive_temporal_scenarios(
            data=two_line_grid,
            raw_scenarios=(
                {
                    "name": "inactive_but_normal_infeasible",
                    "probability": 1.0,
                    "periods": ("q1",),
                    "system_load_multiplier": (1.0,),
                    "data_center_demand_mw": (200.0,),
                    "network_call_active": (0.0,),
                    "green_call_mw": (0.0,),
                    "connected_demand_mw": (200.0,),
                    "recovery_headroom_mw": (0.0,),
                    "completed_periods": frozenset(),
                    "require_terminal_event_inactive": True,
                    "boundary_state_status": (
                        "clean_boundary_with_zero_carry_in"
                    ),
                },
            ),
            method="minimum_curtailment",
            poi_bus=2,
            balancing_bus=1,
            branch_indices=(0,),
            generator_indices=(),
            redispatch_fraction_of_pmax=1.0,
            sustained_rating="rate_a",
            solver_name="highs",
            parameter_status="synthetic_test",
        )


def test_rts24_temporal_config_is_local_honest_and_bus8_pinned():
    yaml = pytest.importorskip("yaml")
    path = (
        Path(__file__).resolve().parents[1]
        / "configs"
        / "rq2_l5_economic_temporal_network_rts24.yaml"
    )
    config = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert config["network"]["poi_bus"] == 8
    assert config["evaluation"]["security_certified"] is False
    assert config["network"]["methods"] == [
        "minimum_curtailment",
        "overload_sensitivity",
    ]
    scenario = config["scenarios"][0]
    assert set(scenario["network_call_active"]) <= {0, 1}
    assert sum(scenario["network_call_active"]) == 1
    assert scenario["data_center_demand_mw"] == scenario["connected_demand_mw"]
    assert scenario["boundary_state_status"] == (
        "clean_boundary_with_zero_carry_in"
    )
