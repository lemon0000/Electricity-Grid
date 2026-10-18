import csv
import json
from pathlib import Path
from types import SimpleNamespace

import yaml

from experiments import run_rts24_deterministic_expansion as runner


def _candidate(index, start_quarter, *, resolved, feasible):
    quarter_names = ("q1", "q2", "q3", "q4")
    return {
        "candidate_index": index,
        "candidate": (
            "no_start" if start_quarter is None else f"start_{start_quarter}"
        ),
        "start_quarter": start_quarter,
        "commissioned_by_quarter": {name: False for name in quarter_names},
        "resolved": resolved,
        "feasible": feasible,
        "selected": False,
        "objective": 100.0 if feasible else None,
        "qp_settings": {
            "eps_abs": 1.0e-6,
            "eps_rel": 1.0e-8,
        },
        "qp_status": "solved" if resolved and feasible else "maximum iterations",
        "qp_status_value": 1 if resolved and feasible else 7,
        "qp_iterations": 25 if resolved and feasible else 500_000,
        "qp_extraction_seconds": 0.1,
        "qp_setup_seconds": 0.2,
        "qp_solve_seconds": 0.3,
        "qp_primal_residual": 1.0e-8 if resolved and feasible else 1.0,
        "qp_dual_residual": 2.0e-9 if resolved and feasible else 1.0,
        "qp_max_constraint_violation": 3.0e-9 if resolved and feasible else None,
        "qp_max_bound_projection": 0.0,
        "repair_termination_condition": "optimal" if feasible else None,
        "repair_solve_seconds": 0.4 if feasible else None,
        "candidate_solver_seconds": 1.0,
        "repair_max_constraint_violation": 4.0e-9 if feasible else None,
        "repair_objective_deviation": 5.0e-8 if feasible else None,
    }


def test_runner_writes_numerical_enumeration_schema(monkeypatch, tmp_path):
    config = yaml.safe_load(
        Path("configs/rts24_deterministic_expansion.yaml").read_text(
            encoding="utf-8"
        )
    )
    config["output"] = {
        "quarterly_path": str(tmp_path / "quarters.csv"),
        "state_path": str(tmp_path / "states.csv"),
        "candidate_path": str(tmp_path / "candidates.csv"),
        "summary_path": str(tmp_path / "summary.json"),
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False),
        encoding="utf-8",
    )

    data = SimpleNamespace(
        generators=(
            SimpleNamespace(index=0, p_max_mw=100.0, in_service=True),
        ),
        branches=(),
        source_package="synthetic_test",
        source_version="1",
        total_demand_mw=0.0,
    )
    diagnostics = (
        _candidate(0, None, resolved=True, feasible=True),
        _candidate(1, "q1", resolved=False, feasible=False),
        _candidate(2, "q2", resolved=False, feasible=False),
        _candidate(3, "q3", resolved=False, feasible=False),
        _candidate(4, "q4", resolved=False, feasible=False),
    )
    result = SimpleNamespace(
        feasible=False,
        termination_condition="enumeration_incomplete",
        solver_status="warning",
        solver_message="At least one fixed-start candidate was not resolved",
        objective=None,
        optimization_objective=None,
        investment_cost=None,
        operating_cost=None,
        access_shortfall_cost=None,
        project_started=None,
        start_quarter=None,
        commissioned_by_quarter={},
        connected_capacity_mw={},
        access_shortfall_mw={},
        states=(),
        excluded_branch_indices=(10,),
        candidate_diagnostics=diagnostics,
        enumeration_method=(
            "exhaustive_fixed_start_candidates_direct_numerical_convex_qp_"
            "with_linear_feasibility_repair"
        ),
        capacity_interpretation=(
            "firm_connected_and_operating_demand_capped_by_quarter_request"
        ),
    )
    solve_kwargs = {}

    def fake_solve(*_args, **kwargs):
        solve_kwargs.update(kwargs)
        return result

    monkeypatch.setattr(runner, "load_rts24", lambda: data)
    monkeypatch.setattr(
        runner,
        "non_islanding_branch_indices",
        lambda _data: (11, 12),
    )
    monkeypatch.setattr(runner, "solve_deterministic_expansion", fake_solve)

    summary = runner.run(config_path)

    assert "cost_breakpoints" not in solve_kwargs
    assert solve_kwargs["solver_name"] == "highs"
    assert summary["qp_solver"] == "osqp"
    assert summary["linear_repair_solver"] == "highs"
    assert summary["expected_candidate_count"] == 5
    assert summary["actual_candidate_count"] == 5
    assert summary["candidate_order_canonical"]
    assert summary["resolved_candidate_count"] == 1
    assert summary["feasible_candidate_count"] == 1
    assert summary["selected_candidate_count"] == 0
    assert summary[
        "selected_objective_separation_to_next_feasible_candidate"
    ] is None
    assert summary[
        "selected_candidate_separation_exceeds_pairwise_repair_envelopes"
    ] is None
    assert not summary["enumeration_complete"]
    assert summary["cost_interpretation"] == (
        "no_selected_cost_fixed_start_enumeration_incomplete"
    )
    assert "fixed_start_enumeration_incomplete" in summary[
        "certification_blockers"
    ]
    assert summary["candidate_diagnostics"] == diagnostics
    assert "optimization_objective_pwl_synthetic_units" not in summary
    assert "objective_exact_recalculation_synthetic_units" not in summary
    assert all(
        "pwl" not in blocker and "miqp" not in blocker
        for blocker in summary["certification_blockers"]
    )

    saved_summary = json.loads(
        (tmp_path / "summary.json").read_text(encoding="utf-8")
    )
    assert len(saved_summary["candidate_diagnostics"]) == 5
    with (tmp_path / "candidates.csv").open(
        encoding="utf-8",
        newline="",
    ) as candidate_file:
        candidate_rows = list(csv.DictReader(candidate_file))
    assert len(candidate_rows) == 5
    assert json.loads(candidate_rows[0]["commissioned_by_quarter"]) == {
        "q1": False,
        "q2": False,
        "q3": False,
        "q4": False,
    }
    assert json.loads(candidate_rows[0]["qp_settings"]) == {
        "eps_abs": 1.0e-6,
        "eps_rel": 1.0e-8,
    }
    assert candidate_rows[0]["qp_primal_residual"] == "1e-08"
    assert candidate_rows[0]["repair_objective_deviation"] == "5e-08"
