"""Tests for the RQ2 H2 out-of-sample entry point.

These pin the *formal entry point* ``run_rq2_h2_stochastic_holdout.run`` that
plans the correct and B6 flexibility policies on a frozen training tree and
executes them pinned on a frozen unseen holdout tree. The scope is the runner's
contract, not the module internals (covered by ``tests/test_economic_holdout.py``):

* the artifacts (leaves / policies CSV, summary JSON) are written with the
  frozen schemas and honesty tags;
* the reported holdout CVaR is cross-checked against the independent section 13
  evaluator within tolerance for every feasible policy;
* the H2 out-of-sample under-delivery of the B6 policy is reported and positive
  on the reference case;
* every output carries ``security_certified = False`` and never claims an
  engineering / contract / empirical-VMA certification;
* fail-closed behaviour: an infeasible training plan drops ``gate_passed`` to
  ``False`` and exits non-zero, while a holdout hard-security failure (positive
  H2 evidence) does NOT fail the gate; a self-certifying config is rejected.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")
pytest.importorskip("pyomo")

from experiments import run_rq2_h2_stochastic_holdout as runner


_BASE_CONFIG = {
    "evaluation": {
        "id": "rq2_h2_test",
        "role": "test",
        "parameter_status": "synthetic_test_only_not_for_engineering",
        "security_certified": False,
        "formal_vma_published": False,
    },
    "model": {
        "max_flexibility_budget_mw": 200.0,
        "provisioning_cost_per_mw": 500.0,
        "lambda_risk": 0.1,
        "beta": 0.5,
        "service_shortfall_tolerance_mw": 1.0e-6,
        "solver_name": "highs",
    },
    "coefficients": {
        "kappa_access": 1000.0,
        "kappa_grid": 50.0,
        "kappa_green": 40.0,
        "kappa_drop": 2000.0,
        "kappa_breach_firm": 0.0,
        "kappa_breach_conditional": 0.0,
        "parameter_status": "synthetic_test_only_not_for_engineering",
    },
    "training_scenarios": [
        {
            "name": "train_mild",
            "probability": 0.5,
            "grid_need_mw": 20.0,
            "green_call_mw": 60.0,
            "connected_demand_mw": 1000.0,
            "hours": 1.0,
        },
        {
            "name": "train_stress",
            "probability": 0.5,
            "grid_need_mw": 40.0,
            "green_call_mw": 60.0,
            "connected_demand_mw": 1000.0,
            "hours": 1.0,
        },
    ],
    "holdout_scenarios": [
        {
            "name": "holdout_mild",
            "probability": 0.4,
            "grid_need_mw": 25.0,
            "green_call_mw": 60.0,
            "connected_demand_mw": 1000.0,
            "hours": 1.0,
        },
        {
            "name": "holdout_stress",
            "probability": 0.4,
            "grid_need_mw": 50.0,
            "green_call_mw": 60.0,
            "connected_demand_mw": 1000.0,
            "hours": 1.0,
        },
        {
            "name": "holdout_severe",
            "probability": 0.2,
            "grid_need_mw": 90.0,
            "green_call_mw": 60.0,
            "connected_demand_mw": 1000.0,
            "hours": 1.0,
        },
    ],
    "validation": {
        "cvar_cross_check_tolerance": 1.0e-6,
        "fail_closed_on_infeasible_training": True,
    },
    "random_seed": None,
    "output": {
        "leaves_path": "leaves.csv",
        "policies_path": "policies.csv",
        "summary_path": "summary.json",
    },
}


def _write_config(tmp_path: Path, overrides=None) -> Path:
    import copy

    config = copy.deepcopy(_BASE_CONFIG)
    if overrides:
        overrides(config)
    config["output"] = {
        "leaves_path": str(tmp_path / "leaves.csv"),
        "policies_path": str(tmp_path / "policies.csv"),
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

    leaves_path = tmp_path / "leaves.csv"
    policies_path = tmp_path / "policies.csv"
    summary_path = tmp_path / "summary.json"
    assert leaves_path.exists() and policies_path.exists() and summary_path.exists()

    leaf_rows = _read_csv(leaves_path)
    # 2 policies x 3 holdout leaves.
    assert len(leaf_rows) == 6
    assert tuple(leaf_rows[0].keys()) == runner._LEAF_FIELDS

    policy_rows = _read_csv(policies_path)
    assert len(policy_rows) == 2
    assert tuple(policy_rows[0].keys()) == runner._POLICY_FIELDS

    on_disk = json.loads(summary_path.read_text(encoding="utf-8"))
    assert on_disk == summary


def test_summary_carries_honesty_tags_and_never_certifies(tmp_path):
    summary = runner.run(_write_config(tmp_path))
    assert summary["security_certified"] is False
    assert summary["formal_vma_published"] is False
    assert summary["empirical_holdout_claimed"] is False
    assert summary["touches_frozen_baselines"] is False
    assert "not_an_empirical_vma_or_engineering_certification" in summary[
        "interpretation"
    ]
    assert summary["certification_blockers"]
    leaf_rows = _read_csv(tmp_path / "leaves.csv")
    assert all(row["security_certified"] == "False" for row in leaf_rows)


# ---------------------------------------------------------------------------
# CVaR cross-check against the independent section 13 evaluator
# ---------------------------------------------------------------------------
def test_reported_holdout_cvar_matches_independent_evaluator(tmp_path):
    summary = runner.run(_write_config(tmp_path))
    assert summary["cvar_cross_check_passed"] is True
    assert summary["cvar_cross_check_max_abs_error"] <= summary[
        "cvar_cross_check_tolerance"
    ]
    policy_rows = _read_csv(tmp_path / "policies.csv")
    for row in policy_rows:
        # The B6 policy has a hard-failure leaf, so its CVaR (and cross-check)
        # is intentionally blank; the correct policy must be within tolerance.
        if row["cvar_cross_check_abs_error"]:
            assert abs(float(row["cvar_cross_check_abs_error"])) <= 1.0e-6


# ---------------------------------------------------------------------------
# H2: out-of-sample under-delivery of the B6-planned policy
# ---------------------------------------------------------------------------
def test_h2_b6_underdelivers_out_of_sample(tmp_path):
    summary = runner.run(_write_config(tmp_path))
    assert summary["h2_evaluated"] is True
    assert summary["h2_b6_underdelivers_out_of_sample"] is True
    assert summary["h2_b6_extra_failure_probability"] > 1.0e-6
    assert summary["h2_b6_extra_expected_shortfall_mwh"] > 1.0e-6
    assert (
        summary["b6_policy"]["total_failure_probability"]
        > summary["correct_policy"]["total_failure_probability"] + 1e-9
    )
    # The B6 severe leaf is an honest hard-security failure.
    assert summary["b6_policy"]["hard_infeasible_probability"] == pytest.approx(
        0.2, abs=1e-9
    )
    assert summary["correct_policy"]["hard_infeasible_probability"] == pytest.approx(
        0.0, abs=1e-9
    )


def test_committed_budgets_reflect_h1_gap(tmp_path):
    summary = runner.run(_write_config(tmp_path))
    assert summary["correct_policy"]["committed_flexibility_mw"] == pytest.approx(
        100.0, abs=1e-6
    )
    assert summary["b6_policy"]["committed_flexibility_mw"] == pytest.approx(
        60.0, abs=1e-6
    )


# ---------------------------------------------------------------------------
# Fail-closed behaviour
# ---------------------------------------------------------------------------
def test_holdout_hard_failure_does_not_fail_the_gate(tmp_path):
    # The default case already has a B6 hard-security failure on the severe leaf;
    # that is positive H2 evidence and must NOT trip the correctness gate.
    summary = runner.run(_write_config(tmp_path))
    assert summary["b6_policy"]["hard_infeasible_probability"] > 0.0
    assert summary["gate_passed"] is True


def test_infeasible_training_fails_closed(tmp_path):
    def make_infeasible(config):
        # A training grid_need above the budget cap makes the plan itself
        # infeasible; the H2 comparison cannot be formed, so fail closed.
        config["training_scenarios"][1]["grid_need_mw"] = 500.0

    summary = runner.run(_write_config(tmp_path, make_infeasible))
    assert summary["training_feasible"] is False
    assert summary["gate_passed"] is False


def test_main_exits_nonzero_when_gate_fails(tmp_path, monkeypatch):
    def make_infeasible(config):
        config["training_scenarios"][1]["grid_need_mw"] = 500.0

    config_path = _write_config(tmp_path, make_infeasible)
    monkeypatch.setattr("sys.argv", ["run", "--config", str(config_path)])
    with pytest.raises(SystemExit) as excinfo:
        runner.main()
    assert excinfo.value.code == 1


# ---------------------------------------------------------------------------
# R3 finding 3: the CVaR cross-check is genuinely independent
# ---------------------------------------------------------------------------
def test_independent_service_cvar_matches_hand_calculation():
    # Four equiprobable losses {10, 40, 80, 160}, beta = 0.5. Cumulative prob
    # reaches 0.5 at loss 40, so VaR = 40. Tail = 0.25*(80-40) + 0.25*(160-40)
    # = 0.25*40 + 0.25*120 = 40. CVaR = 40 + 40/(1-0.5) = 40 + 80 = 120.
    losses = [(10.0, 0.25), (40.0, 0.25), (80.0, 0.25), (160.0, 0.25)]
    assert runner._independent_service_cvar(losses, beta=0.5) == pytest.approx(
        120.0, abs=1e-9
    )


def test_cross_check_detects_a_corrupted_reported_cvar(tmp_path, monkeypatch):
    # The cross-check must be a real independent recomputation: if the module
    # reported a wrong CVaR, the gate must catch it and fail closed. We corrupt
    # the reported holdout CVaR of every feasible policy and assert the error
    # exceeds tolerance and the gate fails.
    from dataclasses import replace

    import src.evaluation.economic_holdout as holdout

    real_evaluate = holdout.evaluate_economic_holdout

    def corrupt(inputs, *, solver_name="highs"):
        result = real_evaluate(inputs, solver_name=solver_name)
        corrupted_correct = result.correct
        if corrupted_correct.holdout_service_cvar is not None:
            corrupted_correct = replace(
                result.correct,
                holdout_service_cvar=result.correct.holdout_service_cvar + 1.0e6,
            )
        return replace(result, correct=corrupted_correct)

    monkeypatch.setattr(runner, "evaluate_economic_holdout", corrupt)
    summary = runner.run(_write_config(tmp_path))
    assert summary["cvar_cross_check_passed"] is False
    assert summary["cvar_cross_check_max_abs_error"] > summary[
        "cvar_cross_check_tolerance"
    ]
    assert summary["gate_passed"] is False


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------
def test_self_certifying_config_is_rejected(tmp_path):
    def certify(config):
        config["evaluation"]["security_certified"] = True

    with pytest.raises(ValueError, match="security_certified"):
        runner.run(_write_config(tmp_path, certify))


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


def test_empty_holdout_is_rejected(tmp_path):
    def empty_holdout(config):
        config["holdout_scenarios"] = []

    with pytest.raises(ValueError, match="holdout_scenarios"):
        runner.run(_write_config(tmp_path, empty_holdout))


# ---------------------------------------------------------------------------
# Generator-driven scenario source (scenario_source = "generated")
# ---------------------------------------------------------------------------
# These pin the *runner* branch that derives the training/holdout trees from the
# real shipped AI-workload traces via split-aware peak normalization. The point
# is not to re-test the generator internals (tests/test_trace_scenario_generator.py
# does that) but the runner-level contract: the module honesty tag survives into
# the on-disk summary, the run never certifies, provenance is recorded, and a
# malformed generator block fails closed. Without these, a future refactor could
# silently drop the ``::{generated_status}`` splice and let generated scenarios
# masquerade as empirical evidence (agent.md sections 4/8).
_N_HOLDOUT_GEN = 6


def _generated(config):
    config["scenario_source"] = "generated"
    config["generator"] = {
        "parameter_status": "synthetic_test_only_not_for_engineering",
        "split_fraction": 0.5,
        "window_hours": 24,
        "n_train": 8,
        "n_holdout": _N_HOLDOUT_GEN,
        "seed": 7,
        "grid_stress_scale_mw": 40.0,
        "green_call_scale_mw": 60.0,
        "connected_demand_mw": 1000.0,
        "grid_stress_shape": {
            "path": "data/processed/google_power_2019/v1/hourly_shape.csv",
            "column": "measured_power_util_unweighted_mean",
        },
        "green_workload_shape": {
            "path": "data/processed/alibaba_gpu_2020/v2020/"
            "relative_hourly_workload.csv.gz",
            "column": "requested_gpu_equivalents",
        },
    }


def test_generated_source_runs_and_records_provenance(tmp_path):
    summary = runner.run(_write_config(tmp_path, _generated))
    assert summary["scenario_source"] == "generated"

    provenance = summary["generator_provenance"]
    assert isinstance(provenance, dict) and provenance
    # A reviewer must be able to confirm from the artifact that no training MW
    # depends on a holdout hour: the normalization divisor and the split it was
    # estimated on are recorded, and the split matches the draw.
    assert provenance["split_fraction"] == pytest.approx(0.5, abs=1e-9)
    assert provenance["normalization"]["grid"]["split_fraction"] == pytest.approx(
        0.5, abs=1e-9
    )
    assert provenance["normalization"]["green"]["split_fraction"] == pytest.approx(
        0.5, abs=1e-9
    )
    assert provenance["windows"]["train"]["grid"]
    assert provenance["windows"]["holdout"]["green"]

    # n_holdout scenarios x 2 policies.
    leaf_rows = _read_csv(tmp_path / "leaves.csv")
    assert len(leaf_rows) == _N_HOLDOUT_GEN * 2


def test_generated_summary_carries_module_honesty_tag_and_never_certifies(tmp_path):
    summary = runner.run(_write_config(tmp_path, _generated))
    status = summary["parameter_status"]
    # The module honesty tag (MW derived, probabilities are Monte-Carlo sampling
    # weights, NOT empirical outage / engineering / contract evidence) must be
    # present in the on-disk summary, spliced onto the caller's own status.
    assert "derived" in status
    assert "not_empirical_outage" in status
    assert "sampling_weights" in status
    assert "not_for_engineering" in status  # caller status preserved too
    assert summary["security_certified"] is False
    leaf_rows = _read_csv(tmp_path / "leaves.csv")
    assert all(row["security_certified"] == "False" for row in leaf_rows)


def test_generated_source_requires_generator_block(tmp_path):
    def drop_generator(config):
        config["scenario_source"] = "generated"
        config.pop("generator", None)

    with pytest.raises(ValueError, match="generator"):
        runner.run(_write_config(tmp_path, drop_generator))


def test_generated_rejects_nonintegral_window_hours(tmp_path):
    def bad_window(config):
        _generated(config)
        config["generator"]["window_hours"] = "24"

    with pytest.raises(ValueError, match="window_hours"):
        runner.run(_write_config(tmp_path, bad_window))


def test_unknown_scenario_source_is_rejected(tmp_path):
    def bad_source(config):
        config["scenario_source"] = "empirical"

    with pytest.raises(ValueError, match="scenario_source"):
        runner.run(_write_config(tmp_path, bad_source))
