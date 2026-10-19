from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.grid.rts_gmlc_exact_cg_runner import ExactCgCall
from src.grid.rts_gmlc_formal_cg_adapter import FormalCgModelAdapter


def test_level_set_adapter_accepts_api_lower_bound_without_incumbent(
    tmp_path: Path, monkeypatch
) -> None:
    handle = SimpleNamespace(
        formulation_variables=10,
        formulation_constraints=20,
    )
    monkeypatch.setattr(
        "src.grid.rts_gmlc_formal_cg_adapter.pilot._build_model_handle",
        lambda *_args, **_kwargs: handle,
    )
    monkeypatch.setattr(
        "src.grid.rts_gmlc_formal_cg_adapter.pilot._solve_handle",
        lambda *_args, **_kwargs: {
            "incumbent_usable": False,
            "maximum_integrality_violation": None,
            "bound_valid": False,
            "dual_bound": None,
            "raw_lower_bound": 101.0,
        },
    )
    events = []
    adapter = FormalCgModelAdapter(
        problem=object(),
        formal_solver={
            "solver": {
                "name": "highs",
                "threads": 4,
                "random_seed": 0,
                "feasibility_tolerance": 1.0e-6,
                "bound_consistency_tolerance": 1.0e-6,
            },
            "progress_logging": {
                "native_solver_log_interval_seconds": 5.0,
                "heartbeat_interval_seconds": 30.0,
            },
            "expected_full_model_size": {},
        },
        candidate_frontier={"cost_cap_absolute_tolerance_usd": 1.0e-4},
        snapshot_contract={
            "maximum_distance_to_nearest_binary_before_normalization": 1.0e-8
        },
        progress=SimpleNamespace(
            emit=lambda event, **payload: events.append((event, payload))
        ),
        log_root=tmp_path,
    )
    call = ExactCgCall(
        call_id="level_set_cost_minimization.iteration_01.master",
        kind="master",
        stage="level_set_cost_minimization",
        iteration=1,
        active_state_ids=("normal",),
        all_state_ids=("normal", "s1"),
        time_limit_seconds=30.0,
        target_relative_gap=1.0e-4,
        proxy_floor=0.6,
    )

    result = adapter.solve_master(call)

    assert not result.incumbent_usable
    assert result.bound_valid
    assert result.dual_bound == 101.0
    assert not result.residual_audit_passed
    assert events[0][0] == "formal_master_built"


@pytest.mark.parametrize(
    (
        "solver_api",
        "termination_condition",
        "certified_by_solver_api",
        "expected_global_infeasibility",
    ),
    (
        (
            "pyomo.contrib.solver.highs_v2",
            "TerminationCondition.provenInfeasible",
            True,
            True,
        ),
        (
            "pyomo.contrib.solver.highs_v2",
            "TerminationCondition.provenInfeasible",
            False,
            False,
        ),
        (
            "pyomo.environ.SolverFactory.highs_legacy",
            "TerminationCondition.provenInfeasible",
            True,
            False,
        ),
        (
            "pyomo.contrib.solver.highs_v2",
            "TerminationCondition.maxTimeLimit",
            True,
            False,
        ),
        (
            "pyomo.contrib.solver.highs_v2",
            "TerminationCondition.objectiveLimit",
            False,
            False,
        ),
        (
            "pyomo.contrib.solver.highs_v2",
            "TerminationCondition.infeasibleOrUnbounded",
            True,
            False,
        ),
        (
            "pyomo.contrib.solver.highs_v2",
            "TerminationCondition.unknown",
            True,
            False,
        ),
    ),
)
def test_budget_decision_adapter_accepts_only_v2_proven_infeasibility(
    tmp_path: Path,
    monkeypatch,
    solver_api: str,
    termination_condition: str,
    certified_by_solver_api: bool,
    expected_global_infeasibility: bool,
) -> None:
    handle = SimpleNamespace(
        formulation_variables=10,
        formulation_constraints=20,
    )
    monkeypatch.setattr(
        "src.grid.rts_gmlc_formal_cg_adapter.pilot._build_model_handle",
        lambda *_args, **_kwargs: handle,
    )
    monkeypatch.setattr(
        "src.grid.rts_gmlc_formal_cg_adapter.pilot._solve_handle",
        lambda *_args, **_kwargs: {
            "incumbent_usable": False,
            "maximum_integrality_violation": None,
            "bound_valid": False,
            "dual_bound": None,
            "raw_lower_bound": None,
            "solver_status": None,
            "solver_api": solver_api,
            "termination_condition": termination_condition,
            "global_infeasibility_certified": certified_by_solver_api,
            "decision_objective_target_usd": 100.0001,
            "solver_api_solution_status": (
                "SolutionStatus.feasible"
                if termination_condition == "TerminationCondition.objectiveLimit"
                else None
            ),
        },
    )
    adapter = FormalCgModelAdapter(
        problem=SimpleNamespace(cost_budget_usd=100.0),
        formal_solver={
            "solver": {
                "name": "highs",
                "threads": 4,
                "random_seed": 0,
                "feasibility_tolerance": 1.0e-6,
                "bound_consistency_tolerance": 1.0e-6,
            },
            "progress_logging": {
                "native_solver_log_interval_seconds": 5.0,
                "heartbeat_interval_seconds": 30.0,
            },
            "expected_full_model_size": {},
        },
        candidate_frontier={"cost_cap_absolute_tolerance_usd": 1.0e-4},
        snapshot_contract={
            "maximum_distance_to_nearest_binary_before_normalization": 1.0e-8
        },
        progress=SimpleNamespace(emit=lambda *_args, **_kwargs: None),
        log_root=tmp_path,
    )
    call = ExactCgCall(
        call_id="level_set_budget_feasibility.iteration_01.master",
        kind="master",
        stage="level_set_budget_feasibility",
        iteration=1,
        active_state_ids=("normal",),
        all_state_ids=("normal", "s1"),
        time_limit_seconds=30.0,
        target_relative_gap=1.0e-4,
        proxy_floor=0.6,
    )

    result = adapter.solve_master(call)

    assert result.globally_infeasible is expected_global_infeasibility
    assert result.decision_budget_cap_usd == pytest.approx(100.0001)
    assert not result.bound_valid
    assert result.dual_bound is None
    assert result.record["decision_mip"]["solver_api"] == solver_api
    assert result.record["decision_mip"]["solver_status_raw"] is None
    assert result.record["decision_mip"]["schema"] == (
        "rts_gmlc_level_set_budget_decision_mip_v2"
    )
    assert result.record["decision_mip"]["objective_target_usd"] == pytest.approx(
        100.0001
    )
    assert result.record["decision_mip"]["objective_limit_is_feasible_only"] is (
        termination_condition == "TerminationCondition.objectiveLimit"
    )
    assert not result.record["decision_mip"][
        "objective_limit_is_optimality_certificate"
    ]
    assert (
        result.record["decision_mip"]["termination_is_global_infeasible"]
        is expected_global_infeasibility
    )
