"""Tests for the RQ2 L5 economic stochastic entry point.

These pin the *formal entry point* ``run_rq2_l5_economic_stochastic.run`` that
drives the L5 model over a frozen synthetic scenario tree. The scope is the
runner's contract, not the model internals (those are covered by
``tests/test_economic_stochastic.py``):

* the artifacts (runs / frontier CSV, summary JSON) are written with the
  frozen schemas and honesty tags;
* the reported CVaR is cross-checked against the independent section 13
  ``evaluate_service_cvar`` within tolerance;
* the H1 provisioning gap (correct shared model vs B6 error baseline) is
  strictly positive on the reference case;
* the H3 frontier is a monotone cost <-> tail-risk trade-off;
* every output carries ``security_certified = False`` and never claims an
  engineering / contract / economic-optimum certification;
* fail-closed behaviour: an infeasible run (hard grid_need above the budget
  cap) drops ``gate_passed`` to ``False`` and exits non-zero, and a config that
  self-certifies is rejected.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")
pytest.importorskip("pyomo")

from experiments import run_rq2_l5_economic_stochastic as runner


_BASE_CONFIG = {
    "evaluation": {
        "id": "rq2_l5_test",
        "role": "test",
        "parameter_status": "synthetic_test_only_not_for_engineering",
        "security_certified": False,
        "formal_economic_optimum_published": False,
    },
    "model": {
        "max_flexibility_budget_mw": 200.0,
        "provisioning_cost_per_mw": 500.0,
        "beta": 0.5,
        "solver_name": "highs",
    },
    "lambda_sweep": [0.0, 0.05, 0.1, 0.5, 1.0],
    "coefficients": {
        "kappa_access": 1000.0,
        "kappa_grid": 50.0,
        "kappa_green": 40.0,
        "kappa_drop": 2000.0,
        "kappa_breach_firm": 0.0,
        "kappa_breach_conditional": 0.0,
        "parameter_status": "synthetic_test_only_not_for_engineering",
    },
    "scenarios": [
        {
            "name": "mild",
            "probability": 0.5,
            "grid_need_mw": 20.0,
            "green_call_mw": 60.0,
            "connected_demand_mw": 1000.0,
            "hours": 1.0,
        },
        {
            "name": "stress",
            "probability": 0.5,
            "grid_need_mw": 40.0,
            "green_call_mw": 60.0,
            "connected_demand_mw": 1000.0,
            "hours": 1.0,
        },
    ],
    "validation": {
        "cvar_cross_check_tolerance": 1.0e-6,
        "fail_closed_on_infeasible_run": True,
    },
    "random_seed": None,
    "output": {
        "runs_path": "runs.csv",
        "frontier_path": "frontier.csv",
        "summary_path": "summary.json",
    },
}


def _write_config(tmp_path: Path, overrides=None) -> Path:
    import copy

    config = copy.deepcopy(_BASE_CONFIG)
    if overrides:
        overrides(config)
    config["output"] = {
        "runs_path": str(tmp_path / "runs.csv"),
        "frontier_path": str(tmp_path / "frontier.csv"),
        "summary_path": str(tmp_path / "summary.json"),
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


# ---------------------------------------------------------------------------
# Artifacts and schema
# ---------------------------------------------------------------------------
def test_run_writes_all_artifacts_with_frozen_schema(tmp_path):
    config_path = _write_config(tmp_path)
    summary = runner.run(config_path)

    runs_path = tmp_path / "runs.csv"
    frontier_path = tmp_path / "frontier.csv"
    summary_path = tmp_path / "summary.json"
    assert runs_path.exists() and frontier_path.exists() and summary_path.exists()

    run_rows = _read_csv(runs_path)
    # 5 lambdas x 2 variants.
    assert len(run_rows) == 10
    assert tuple(run_rows[0].keys()) == runner._RUN_FIELDS

    frontier_rows = _read_csv(frontier_path)
    assert len(frontier_rows) == 5
    assert tuple(frontier_rows[0].keys()) == runner._FRONTIER_FIELDS

    on_disk = json.loads(summary_path.read_text(encoding="utf-8"))
    assert on_disk == summary


def test_summary_carries_honesty_tags_and_never_certifies(tmp_path):
    summary = runner.run(_write_config(tmp_path))
    assert summary["security_certified"] is False
    assert summary["formal_economic_optimum_published"] is False
    assert summary["formal_vma_published"] is False
    assert summary["economic_optimum_claimed"] is False
    assert summary["touches_frozen_baselines"] is False
    assert "not_engineering_contract_or_economic_optimum" in summary["interpretation"]
    assert summary["certification_blockers"]
    # Every run row must also stamp security_certified = False.
    run_rows = _read_csv(tmp_path / "runs.csv")
    assert all(row["security_certified"] == "False" for row in run_rows)


# ---------------------------------------------------------------------------
# CVaR cross-check against the independent section 13 evaluator
# ---------------------------------------------------------------------------
def test_reported_cvar_matches_independent_section13_evaluator(tmp_path):
    summary = runner.run(_write_config(tmp_path))
    assert summary["cvar_cross_check_passed"] is True
    assert summary["cvar_cross_check_max_abs_error"] <= summary[
        "cvar_cross_check_tolerance"
    ]

    # Recompute the frontier CVaR at lambda = 1.0 fully independently from the
    # runs CSV dispatch would require the dispatch columns; instead assert the
    # runner's own per-run cross-check error is within tolerance for every
    # feasible run.
    run_rows = _read_csv(tmp_path / "runs.csv")
    for row in run_rows:
        if row["feasible"] == "True":
            assert abs(float(row["cvar_cross_check_abs_error"])) <= 1.0e-6


# ---------------------------------------------------------------------------
# H1: shared budget rejects the B6 over-provisioning
# ---------------------------------------------------------------------------
def test_h1_shared_model_provisions_more_than_b6(tmp_path):
    summary = runner.run(_write_config(tmp_path))
    assert summary["h1_evaluated"] is True
    assert summary["h1_overestimation_mw"] > 1.0e-6
    assert summary["h1_shared_budget_rejects_b6_overprovision"] is True

    run_rows = _read_csv(tmp_path / "runs.csv")
    ref = summary["h1_reference_lambda"]
    correct = next(
        row
        for row in run_rows
        if row["model_variant"] == runner._CORRECT_VARIANT
        and float(row["lambda_risk"]) == ref
    )
    b6 = next(
        row
        for row in run_rows
        if row["model_variant"] == runner._B6_VARIANT
        and float(row["lambda_risk"]) == ref
    )
    assert float(correct["provisioned_flexibility_mw"]) > float(
        b6["provisioned_flexibility_mw"]
    )


# ---------------------------------------------------------------------------
# H3: monotone cost <-> tail-risk trade-off on the frontier
# ---------------------------------------------------------------------------
def test_h3_frontier_is_monotone_tradeoff(tmp_path):
    summary = runner.run(_write_config(tmp_path))
    assert summary["h3_evaluated"] is True
    assert summary["h3_cvar_non_increasing"] is True
    assert summary["h3_expected_cost_non_decreasing"] is True
    assert summary["h3_monotone_cost_tail_risk_tradeoff"] is True

    frontier = summary["frontier"]
    cvars = [row["conditional_value_at_risk"] for row in frontier]
    costs = [row["expected_planning_cost"] for row in frontier]
    assert all(b <= a + 1.0e-6 for a, b in zip(cvars, cvars[1:]))
    assert all(b >= a - 1.0e-6 for a, b in zip(costs, costs[1:]))
    # The trade-off must be non-trivial: at least one strict move somewhere.
    assert cvars[0] > cvars[-1] + 1.0e-6


# ---------------------------------------------------------------------------
# Fail-closed behaviour
# ---------------------------------------------------------------------------
def test_infeasible_grid_need_fails_closed(tmp_path):
    def make_infeasible(config):
        # grid_need above the budget cap is a hard-security infeasibility that
        # the risk term cannot buy down.
        config["scenarios"][1]["grid_need_mw"] = 500.0

    summary = runner.run(_write_config(tmp_path, make_infeasible))
    assert summary["all_runs_feasible"] is False
    assert summary["gate_passed"] is False


def test_main_exits_nonzero_when_gate_fails(tmp_path, monkeypatch):
    def make_infeasible(config):
        config["scenarios"][1]["grid_need_mw"] = 500.0

    config_path = _write_config(tmp_path, make_infeasible)
    monkeypatch.setattr("sys.argv", ["run", "--config", str(config_path)])
    with pytest.raises(SystemExit) as excinfo:
        runner.main()
    assert excinfo.value.code == 1


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------
def test_self_certifying_config_is_rejected(tmp_path):
    def certify(config):
        config["evaluation"]["security_certified"] = True

    with pytest.raises(ValueError, match="security_certified"):
        runner.run(_write_config(tmp_path, certify))


def test_descending_lambda_sweep_is_rejected(tmp_path):
    def descend(config):
        config["lambda_sweep"] = [1.0, 0.5, 0.0]

    with pytest.raises(ValueError, match="non-decreasing"):
        runner.run(_write_config(tmp_path, descend))


def test_duplicate_lambda_is_rejected(tmp_path):
    def duplicate(config):
        config["lambda_sweep"] = [0.0, 0.0, 1.0]

    with pytest.raises(ValueError, match="duplicates"):
        runner.run(_write_config(tmp_path, duplicate))


def test_beta_out_of_range_is_rejected(tmp_path):
    def bad_beta(config):
        config["model"]["beta"] = 1.0

    with pytest.raises(ValueError, match="beta"):
        runner.run(_write_config(tmp_path, bad_beta))


def test_missing_parameter_status_is_rejected(tmp_path):
    def blank_status(config):
        config["evaluation"]["parameter_status"] = ""

    with pytest.raises(ValueError, match="parameter_status"):
        runner.run(_write_config(tmp_path, blank_status))
