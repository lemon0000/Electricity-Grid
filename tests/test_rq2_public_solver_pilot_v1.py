from __future__ import annotations

from types import SimpleNamespace

import pytest

from experiments import run_rq2_public_solver_pilot_v1 as pilot


def _solver_payload() -> dict[str, object]:
    return {
        "name": "highs",
        "expected_package_version": "1.15.1",
        "threads": 4,
        "mip_relative_gap": 1.0e-6,
        "feasibility_tolerance": 1.0e-6,
        "optimality_tolerance": 1.0e-6,
        "integer_feasibility_tolerance": 1.0e-6,
        "random_seed": 0,
        "time_limit_seconds": None,
        "tee": False,
    }


def _certificate() -> dict[str, object]:
    return {
        "objective_incumbent_mw": 1.0,
        "lower_bound_mw": 1.0,
        "upper_bound_mw": 1.0,
        "absolute_gap_mw": 0.0,
        "relative_gap": 0.0,
        "gap_tolerance_mw": 1.0e-6,
        "model_variables": 10,
        "model_constraints": 20,
    }


def _record(solver: str, repetition: int) -> dict[str, object]:
    return {
        "solver_name": solver,
        "repetition": repetition,
        "blocks": [
            {
                "block_id": "block",
                "total_wall_seconds": 1.0,
                "baseline_audit": {
                    "accepted": True,
                    "termination_condition": "optimal",
                    "solver_status": "ok",
                    "objective_usd": 10.0,
                    "lower_bound_usd": 10.0,
                    "upper_bound_usd": 10.0,
                    "absolute_gap_usd": 0.0,
                    "relative_gap": 0.0,
                    "gap_tolerance_usd": 1.0e-5,
                    "maximum_constraint_violation": 0.0,
                    "maximum_integrality_violation": 0.0,
                    "model_variables": 100,
                    "model_constraints": 200,
                },
                "hours": [
                    {
                        "source_hour": 1,
                        "state": "finite_grid_need",
                        "resolved_for_pipeline": True,
                        "primary": {
                            "grid_need_mw": 1.0,
                            "termination_condition": "optimal",
                            "solver_status": "ok",
                            "maximum_constraint_violation": 0.0,
                        },
                        "primary_certificate": _certificate(),
                        "zero_dc_confirmation": None,
                        "zero_dc_confirmation_certificate": None,
                    }
                ],
            }
        ],
    }


def _comparison_inputs():
    config = {
        "acceptance": {
            "maximum_baseline_objective_difference_usd": 1.0e-4,
            "maximum_finite_grid_need_difference_mw": 1.0e-5,
            "maximum_constraint_violation": 1.0e-6,
        },
        "solvers": {
            "highs": {"mip_relative_gap": 1.0e-6},
            "gurobi": {"mip_relative_gap": 1.0e-6},
        },
    }
    context = {"expected_exogenous_hours": {"block": ()}}
    runs = [
        _record("highs", 1),
        _record("gurobi", 1),
        _record("gurobi", 2),
        _record("highs", 2),
    ]
    return config, context, runs


def test_run_block_forwards_model_tolerance_to_normal_baseline(monkeypatch):
    observed = {}

    def fake_baseline(
        _data,
        _source_hours,
        *,
        dc_bus: int,
        dc_demand_mw: float,
        solver,
    ):
        assert 1 in _data.hourly_points
        assert _source_hours == (1,)
        assert dc_bus == 108
        assert dc_demand_mw == 250.0
        observed["solver"] = solver
        return (
            ({},),
            ({},),
            {
                "accepted": True,
                "maximum_constraint_violation": 0.0,
            },
        )

    monkeypatch.setattr(pilot, "_normal_baseline", fake_baseline)
    def fake_assessment(*_args, **_kwargs):
        assert _args
        assert _kwargs["source_hour"] == 1
        return {
            "state": "finite_grid_need",
            "resolved_for_pipeline": True,
        }

    monkeypatch.setattr(
        pilot,
        "assess_hourly_rts_gmlc_grid_need",
        fake_assessment,
    )
    monkeypatch.setattr(pilot, "asdict", lambda value: value)
    block = [
        {
            "block_id": "block",
            "source_hour": "1",
            "active_event_id": "",
        }
    ]

    pilot._run_block(
        SimpleNamespace(hourly_points={1: object()}),
        block,
        solver_payload=_solver_payload(),
        dc_bus=108,
        dc_demand_mw=250.0,
        tolerance_mw=2.0e-6,
    )

    assert observed["solver"]["tolerance_mw"] == 2.0e-6


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("baseline_audit", "lower_bound_usd"), 11.0),
        (("baseline_audit", "relative_gap"), 1.0e-3),
        (("baseline_audit", "relative_gap"), None),
        (("hours", 0, "primary", "solver_status"), "warning"),
        (
            ("hours", 0, "primary", "maximum_constraint_violation"),
            1.0e-3,
        ),
        (
            ("hours", 0, "primary_certificate", "lower_bound_mw"),
            2.0,
        ),
        (
            ("hours", 0, "primary_certificate", "relative_gap"),
            1.0e-3,
        ),
    ),
)
def test_certificate_drift_closes_gurobi_eligibility(path, value):
    config, context, runs = _comparison_inputs()
    target = runs[1]["blocks"][0]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    comparison = pilot._compare(config, context, runs)

    assert comparison["all_non_runtime_acceptance_checks_passed"] is False
    assert comparison["gurobi_eligible_for_formal_successor"] is False
    assert comparison["failed_checks"]


def test_matching_solver_certificates_are_eligible():
    config, context, runs = _comparison_inputs()

    comparison = pilot._compare(config, context, runs)

    assert comparison["all_non_runtime_acceptance_checks_passed"] is True
    assert comparison["gurobi_eligible_for_formal_successor"] is True


def test_zero_dc_certificate_drift_closes_e0_eligibility():
    config, _, runs = _comparison_inputs()
    context = {"expected_exogenous_hours": {"block": (1,)}}
    infeasible_certificate = {
        **_certificate(),
        "objective_incumbent_mw": None,
        "lower_bound_mw": None,
        "upper_bound_mw": None,
        "absolute_gap_mw": None,
        "relative_gap": None,
        "gap_tolerance_mw": None,
    }
    infeasible_result = {
        "grid_need_mw": None,
        "termination_condition": "infeasible",
        "solver_status": "warning",
        "maximum_constraint_violation": None,
    }
    for run in runs:
        hour = run["blocks"][0]["hours"][0]
        hour["state"] = "exogenous_grid_infeasibility"
        hour["primary"] = dict(infeasible_result)
        hour["primary_certificate"] = dict(infeasible_certificate)
        hour["zero_dc_confirmation"] = dict(infeasible_result)
        hour["zero_dc_confirmation_certificate"] = dict(
            infeasible_certificate
        )

    accepted = pilot._compare(config, context, runs)
    assert accepted["gurobi_eligible_for_formal_successor"] is True

    runs[1]["blocks"][0]["hours"][0][
        "zero_dc_confirmation_certificate"
    ]["model_constraints"] += 1
    rejected = pilot._compare(config, context, runs)
    assert rejected["gurobi_eligible_for_formal_successor"] is False
