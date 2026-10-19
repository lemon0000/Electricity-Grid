"""RQ2 network-derived ``grid_need_mw`` tests.

The two-line corridor is hand-computable. With 80 MW at bus 2 and either
parallel 40 MW line out, the remaining line carries 80 MW. Restoring the
sustained N-1 limit therefore requires exactly 40 MW of POI curtailment.
The overload/sensitivity comparator sees the same 40 MW overload and a
1 MW/MW relief factor, so it must also return 40 MW.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

import src.grid.network_grid_need as network_grid_need_module
from src.grid import (
    Branch,
    Bus,
    Generator,
    Rts24Data,
    load_rts24,
    non_islanding_branch_indices,
)
from src.grid.network_grid_need import (
    METHOD_MINIMUM_CURTAILMENT,
    METHOD_OVERLOAD_SENSITIVITY,
    NetworkGridNeedInputs,
    derive_network_grid_need,
)
from src.models.rq2_network_grid_need import (
    NetworkEconomicScenarioSpec,
    build_network_derived_economic_scenarios,
)

PARAMETER_STATUS = "synthetic_test_network_derived_not_empirical"


def test_empty_audit_set_fails_closed():
    assert network_grid_need_module._audit_passes(()) is False


@pytest.fixture
def two_line_grid() -> Rts24Data:
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


def _inputs(data: Rts24Data, method: str) -> NetworkGridNeedInputs:
    return NetworkGridNeedInputs(
        data=data,
        poi_bus=2,
        balancing_bus=1,
        system_load_multiplier=1.0,
        data_center_demand_mw=80.0,
        branch_indices=(0,),
        generator_indices=(),
        redispatch_fraction_of_pmax=1.0,
        sustained_rating="rate_a",
        method=method,
        parameter_status=PARAMETER_STATUS,
    )


@pytest.mark.parametrize(
    "method",
    (METHOD_MINIMUM_CURTAILMENT, METHOD_OVERLOAD_SENSITIVITY),
)
def test_hand_calculated_two_line_need_is_40_mw(two_line_grid, method):
    result = derive_network_grid_need(_inputs(two_line_grid, method))

    assert result.feasible
    assert result.grid_need_mw == pytest.approx(40.0, abs=1.0e-7)
    assert result.critical_state == "branch_0_sustained"
    assert result.security_certified is False
    assert "derived" in result.parameter_status
    assert "not_empirical" in result.parameter_status

    state = result.state_results["branch_0_sustained"]
    assert state.feasible
    if method == METHOD_MINIMUM_CURTAILMENT:
        assert state.minimum_curtailment_mw == pytest.approx(40.0, abs=1.0e-7)
        assert state.maximum_thermal_violation_mw <= 1.0e-7
    else:
        assert result.direct_physical_dispatch_witness is False
        assert state.physically_deliverable is False
        assert state.peak_overload_mw == pytest.approx(40.0, abs=1.0e-7)
        assert state.critical_branch_index == 1
        assert state.poi_relief_sensitivity == pytest.approx(1.0, abs=1.0e-9)
        assert state.maximum_thermal_violation_mw <= 1.0e-7


def test_islanding_contingency_is_rejected_fail_closed():
    one_line = Rts24Data(
        base_mva=100.0,
        buses=(Bus(1, 0.0), Bus(2, 0.0)),
        generators=(
            Generator(0, 1, 0.0, 100.0, 0.0, 1.0, 0.0, None, None, True),
        ),
        branches=(Branch(0, 1, 2, 0.1, 40.0, 40.0, 40.0, 1.0, 0.0, True),),
        reference_bus=1,
        source_package="synthetic_test",
        source_version="1",
    )

    with pytest.raises(ValueError, match="islanding"):
        derive_network_grid_need(_inputs(one_line, METHOD_MINIMUM_CURTAILMENT))


def test_unknown_poi_and_equal_balancing_bus_are_rejected(two_line_grid):
    with pytest.raises(ValueError, match="Unknown POI"):
        derive_network_grid_need(
            NetworkGridNeedInputs(
                **{
                    **_inputs(two_line_grid, METHOD_MINIMUM_CURTAILMENT).__dict__,
                    "poi_bus": 99,
                }
            )
        )
    with pytest.raises(ValueError, match="must differ"):
        derive_network_grid_need(
            NetworkGridNeedInputs(
                **{
                    **_inputs(
                        two_line_grid, METHOD_OVERLOAD_SENSITIVITY
                    ).__dict__,
                    "balancing_bus": 2,
                }
            )
        )


def test_generator_outage_need_is_supply_shortfall_not_thermal_relaxation():
    grid = Rts24Data(
        base_mva=100.0,
        buses=(Bus(1, 0.0), Bus(2, 0.0)),
        generators=(
            Generator(0, 1, 0.0, 80.0, 0.0, 1.0, 0.0, None, None, True),
            Generator(1, 1, 0.0, 50.0, 0.0, 2.0, 0.0, None, None, True),
        ),
        branches=(
            Branch(0, 1, 2, 0.1, 100.0, 100.0, 100.0, 1.0, 0.0, True),
            Branch(1, 1, 2, 0.1, 100.0, 100.0, 100.0, 1.0, 0.0, True),
        ),
        reference_bus=1,
        source_package="synthetic_test",
        source_version="1",
    )
    result = derive_network_grid_need(
        NetworkGridNeedInputs(
            data=grid,
            poi_bus=2,
            balancing_bus=1,
            system_load_multiplier=1.0,
            data_center_demand_mw=80.0,
            branch_indices=(),
            generator_indices=(0,),
            redispatch_fraction_of_pmax=1.0,
            sustained_rating="rate_a",
            method=METHOD_MINIMUM_CURTAILMENT,
            parameter_status=PARAMETER_STATUS,
        )
    )

    assert result.feasible
    assert result.direct_physical_dispatch_witness is True
    assert result.grid_need_mw == pytest.approx(30.0, abs=1.0e-7)
    state = result.state_results["generator_0_sustained"]
    assert state.maximum_balance_residual_mw <= 1.0e-7
    assert state.maximum_thermal_violation_mw <= 1.0e-7


def test_sensitivity_need_above_poi_load_is_not_physically_deliverable(
    two_line_grid,
):
    loaded = replace(
        two_line_grid,
        buses=(
            two_line_grid.buses[0],
            replace(two_line_grid.buses[1], demand_mw=60.0),
        ),
    )
    inputs = replace(
        _inputs(loaded, METHOD_OVERLOAD_SENSITIVITY),
        data_center_demand_mw=10.0,
    )

    result = derive_network_grid_need(inputs)

    assert not result.feasible
    assert result.grid_need_mw == pytest.approx(30.0, abs=1.0e-7)
    state = result.state_results["branch_0_sustained"]
    assert state.physically_deliverable is False
    assert state.termination_condition == "estimated_curtailment_exceeds_poi_load"
    assert state.curtailment_bound_violation_mw == pytest.approx(20.0)


@pytest.mark.parametrize("bad_residual", [1.0, float("nan")])
def test_solution_audit_failure_clears_physical_deliverability(
    two_line_grid, monkeypatch, bad_residual
):
    real_solve_state = network_grid_need_module._solve_state

    def inject_bad_balance(*args, **kwargs):
        solved = real_solve_state(*args, **kwargs)
        return replace(solved, maximum_balance_residual_mw=bad_residual)

    monkeypatch.setattr(network_grid_need_module, "_solve_state", inject_bad_balance)
    result = derive_network_grid_need(
        _inputs(two_line_grid, METHOD_MINIMUM_CURTAILMENT)
    )

    state = result.state_results["branch_0_sustained"]
    assert not result.feasible
    assert state.feasible is False
    assert state.physically_deliverable is False
    assert state.termination_condition == "solution_audit_failed"


def test_nonfinite_base_audit_fails_closed(two_line_grid, monkeypatch):
    real_solve_dc_opf = network_grid_need_module.solve_dc_opf

    def inject_nan_balance(*args, **kwargs):
        result = real_solve_dc_opf(*args, **kwargs)
        residuals = dict(result.power_balance_residuals_mw)
        residuals[next(iter(residuals))] = float("nan")
        return replace(
            result,
            power_balance_residuals_mw=residuals,
        )

    monkeypatch.setattr(
        network_grid_need_module, "solve_dc_opf", inject_nan_balance
    )
    result = derive_network_grid_need(
        _inputs(two_line_grid, METHOD_MINIMUM_CURTAILMENT)
    )

    assert not result.feasible
    assert result.base_termination_condition == "base_solution_audit_failed"
    assert result.state_results == {}


def test_bridge_replaces_hand_entered_grid_need_with_derived_value(two_line_grid):
    specs = (
        NetworkEconomicScenarioSpec(
            name="stress",
            probability=1.0,
            system_load_multiplier=1.0,
            data_center_demand_mw=80.0,
            green_call_mw=20.0,
            connected_demand_mw=80.0,
            hours=1.0,
        ),
    )
    built = build_network_derived_economic_scenarios(
        data=two_line_grid,
        scenario_specs=specs,
        poi_bus=2,
        balancing_bus=1,
        branch_indices=(0,),
        generator_indices=(),
        redispatch_fraction_of_pmax=1.0,
        sustained_rating="rate_a",
        method=METHOD_MINIMUM_CURTAILMENT,
        solver_name="highs",
        parameter_status=PARAMETER_STATUS,
    )

    assert built.feasible
    assert built.scenarios[0].grid_need_mw == pytest.approx(40.0, abs=1.0e-7)
    assert built.scenarios[0].green_call_mw == pytest.approx(20.0)
    assert built.provenance["poi_bus"] == 2
    assert built.provenance["method"] == METHOD_MINIMUM_CURTAILMENT
    assert built.provenance["security_certified"] is False
    assert built.provenance["network_source_package"] == "synthetic_test"
    assert len(built.provenance["network_data_sha256"]) == 64
    assert built.provenance["solution_audit_tolerance_mw"] == pytest.approx(1.0e-6)
    assert built.provenance["scenario_inputs"][0]["data_center_demand_mw"] == 80.0


def test_bridge_rejects_dconn_that_differs_from_physical_poi_load(two_line_grid):
    spec = NetworkEconomicScenarioSpec(
        name="mismatch",
        probability=1.0,
        system_load_multiplier=1.0,
        data_center_demand_mw=80.0,
        green_call_mw=0.0,
        connected_demand_mw=100.0,
        hours=1.0,
    )
    with pytest.raises(ValueError, match="must equal data_center_demand_mw"):
        build_network_derived_economic_scenarios(
            data=two_line_grid,
            scenario_specs=(spec,),
            poi_bus=2,
            balancing_bus=1,
            branch_indices=(0,),
            generator_indices=(),
            redispatch_fraction_of_pmax=1.0,
            sustained_rating="rate_a",
            method=METHOD_MINIMUM_CURTAILMENT,
            solver_name="highs",
            parameter_status=PARAMETER_STATUS,
        )


def test_network_runner_records_both_methods_and_never_certifies(
    tmp_path: Path,
    two_line_grid: Rts24Data,
    monkeypatch,
):
    yaml = pytest.importorskip("yaml")
    from experiments import run_rq2_l5_economic_network as runner

    output_root = tmp_path / "network"
    config = {
        "evaluation": {
            "id": "rq2_network_test",
            "role": "test",
            "parameter_status": PARAMETER_STATUS,
            "security_certified": False,
            "formal_economic_optimum_published": False,
        },
        "network": {
            "case_name": "case24_ieee_rts",
            "poi_bus": 2,
            "balancing_bus": 1,
            "methods": [
                METHOD_MINIMUM_CURTAILMENT,
                METHOD_OVERLOAD_SENSITIVITY,
            ],
            "branch_indices": [0],
            "generator_indices": [],
            "redispatch_fraction_of_pmax": 1.0,
            "sustained_rating": "rate_a",
            "parameter_status": PARAMETER_STATUS,
        },
        "model": {
            "max_flexibility_budget_mw": 100.0,
            "provisioning_cost_per_mw": 10.0,
            "beta": 0.5,
            "solver_name": "highs",
        },
        "lambda_sweep": [0.0],
        "coefficients": {
            "kappa_access": 1000.0,
            "kappa_grid": 1.0,
            "kappa_green": 1.0,
            "kappa_drop": 2000.0,
            "kappa_breach_firm": 0.0,
            "kappa_breach_conditional": 0.0,
            "parameter_status": PARAMETER_STATUS,
        },
        "scenarios": [
            {
                "name": "stress",
                "probability": 1.0,
                "system_load_multiplier": 1.0,
                "data_center_demand_mw": 80.0,
                "green_call_mw": 20.0,
                "connected_demand_mw": 80.0,
                "hours": 1.0,
            }
        ],
        "validation": {
            "cvar_cross_check_tolerance": 1.0e-6,
            "fail_closed_on_infeasible_run": True,
        },
        "random_seed": None,
        "output": {
            "root": str(output_root),
            "summary_path": str(output_root / "summary.json"),
        },
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setattr(runner, "load_rts24", lambda: two_line_grid)

    summary = runner.run(config_path)

    assert summary["gate_passed"] is True
    assert summary["security_certified"] is False
    assert set(summary["methods"]) == {
        METHOD_MINIMUM_CURTAILMENT,
        METHOD_OVERLOAD_SENSITIVITY,
    }
    for method in summary["methods"]:
        provenance = summary["network_provenance"][method]
        assert provenance["scenario_grid_need_mw"]["stress"] == pytest.approx(40.0)
        assert provenance["security_certified"] is False
        assert summary["method_summaries"][method]["security_certified"] is False
    assert json.loads((output_root / "summary.json").read_text()) == summary


def test_rts24_config_freezes_bus8_and_full_selected_state_set():
    yaml = pytest.importorskip("yaml")
    config_path = (
        Path(__file__).resolve().parents[1]
        / "configs"
        / "rq2_l5_economic_network_rts24.yaml"
    )
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert config["network"]["poi_bus"] == 8
    assert config["network"]["balancing_bus"] == 13
    assert len(config["network"]["branch_indices"]) == 37
    assert 10 not in config["network"]["branch_indices"]
    assert len(config["network"]["generator_indices"]) == 32
    assert config["evaluation"]["security_certified"] is False
    assert all("grid_need_mw" not in scenario for scenario in config["scenarios"])


def test_rts24_bus8_full_selected_set_pins_ab_value_and_audits():
    data = load_rts24()
    branches = non_islanding_branch_indices(data)
    generators = tuple(
        generator.index
        for generator in data.generators
        if generator.in_service and generator.p_max_mw > 0.0
    )

    results = {
        method: derive_network_grid_need(
            NetworkGridNeedInputs(
                data=data,
                poi_bus=8,
                balancing_bus=13,
                system_load_multiplier=0.8,
                data_center_demand_mw=250.0,
                branch_indices=branches,
                generator_indices=generators,
                redispatch_fraction_of_pmax=0.5,
                sustained_rating="rate_a",
                method=method,
                parameter_status=PARAMETER_STATUS,
            )
        )
        for method in (METHOD_MINIMUM_CURTAILMENT, METHOD_OVERLOAD_SENSITIVITY)
    }

    for result in results.values():
        assert result.feasible
        assert result.grid_need_mw == pytest.approx(36.8, abs=1.0e-7)
        assert result.critical_state == "branch_11_sustained"
        assert len(result.state_results) == 69
        assert result.base_maximum_balance_residual_mw <= 1.0e-6
        assert result.base_maximum_thermal_violation_mw <= 1.0e-6
        assert result.base_maximum_generation_bound_violation_mw <= 1.0e-6
        assert result.base_maximum_flow_equation_residual_mw <= 1.0e-6
        for state in result.state_results.values():
            assert state.maximum_balance_residual_mw <= 1.0e-6
            assert state.maximum_thermal_violation_mw <= 1.0e-6
            assert state.maximum_generation_bound_violation_mw <= 1.0e-6
            assert state.maximum_redispatch_violation_mw <= 1.0e-6
            assert state.maximum_outage_generation_mw <= 1.0e-6
            assert state.maximum_flow_equation_residual_mw <= 1.0e-6
            assert state.curtailment_bound_violation_mw <= 1.0e-6


def test_network_runner_rejects_hand_entered_grid_need(tmp_path: Path):
    yaml = pytest.importorskip("yaml")
    from experiments import run_rq2_l5_economic_network as runner

    config = {
        "evaluation": {
            "id": "bad",
            "parameter_status": PARAMETER_STATUS,
            "security_certified": False,
        },
        "network": {
            "case_name": "case24_ieee_rts",
            "poi_bus": 8,
            "balancing_bus": 13,
            "methods": [METHOD_MINIMUM_CURTAILMENT],
            "branch_indices": [0],
            "generator_indices": [],
            "redispatch_fraction_of_pmax": 0.5,
            "sustained_rating": "rate_a",
            "parameter_status": PARAMETER_STATUS,
        },
        "model": {"solver_name": "highs"},
        "scenarios": [
            {
                "name": "forbidden",
                "probability": 1.0,
                "system_load_multiplier": 0.8,
                "data_center_demand_mw": 50.0,
                "grid_need_mw": 20.0,
                "green_call_mw": 0.0,
                "connected_demand_mw": 50.0,
                "hours": 1.0,
            }
        ],
        "output": {
            "root": str(tmp_path / "out"),
            "summary_path": str(tmp_path / "out" / "summary.json"),
        },
    }
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")

    with pytest.raises(ValueError, match="forbids hand-entered grid_need_mw"):
        runner.run(path)
