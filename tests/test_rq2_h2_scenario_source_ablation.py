"""Tests for the RQ2 H2 scenario-source ablation entry point (agent.md 4/8/9).

These pin ``experiments.run_rq2_h2_scenario_source_ablation.run``: a controlled
ablation that holds the holdout test set fixed and varies only the training
scenario source (manual / generated / reduced), to test whether the H2 finding
(a B6 double-counting policy under-delivers service out of sample) is an
artifact of the training draw. The scope is the runner's contract, not the
generator or reducer internals (covered by their own tests):

* one shared holdout is used by every arm, and the arm results / summary are
  written with the frozen schema and honesty tags;
* each arm's holdout CVaR is cross-checked against the independent evaluator, so
  a corrupted CVaR fails that arm's gate;
* the H2 out-of-sample under-delivery of the B6 policy is reported per arm and
  aggregated into a robustness flag that is *not* gated;
* the generated / reduced arms propagate the generator / reduction honesty tags
  into the arm status, and every output carries ``security_certified = False``;
* fail-closed behaviour: an infeasible training plan drops ``gate_passed`` and
  exits non-zero; an unknown arm or a self-certifying config is rejected.
"""

from __future__ import annotations

import copy
import csv
import json
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")
pytest.importorskip("pyomo")

from experiments import run_rq2_h2_scenario_source_ablation as runner


_BASE_CONFIG = {
    "evaluation": {
        "id": "rq2_h2_ablation_test",
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
    "arms": ["manual", "generated", "reduced"],
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
    "generator": {
        "parameter_status": "synthetic_test_only_not_for_engineering",
        "split_fraction": 0.5,
        "window_hours": 24,
        "n_train": 16,
        "n_holdout": 6,
        "seed": 20260822,
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
    },
    "reduction": {"target_count": 8, "ground_norm_order": 2.0},
    "validation": {
        "cvar_cross_check_tolerance": 1.0e-6,
        "fail_closed_on_infeasible_training": True,
    },
    "random_seed": None,
    "output": {
        "arms_path": "arms.csv",
        "summary_path": "summary.json",
    },
}


def _write_config(tmp_path: Path, overrides=None) -> Path:
    config = copy.deepcopy(_BASE_CONFIG)
    if overrides:
        overrides(config)
    config["output"] = {
        "arms_path": str(tmp_path / "arms.csv"),
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
def test_run_writes_arms_and_summary_with_frozen_schema(tmp_path):
    summary = runner.run(_write_config(tmp_path))

    arms_path = tmp_path / "arms.csv"
    summary_path = tmp_path / "summary.json"
    assert arms_path.exists() and summary_path.exists()

    arm_rows = _read_csv(arms_path)
    assert len(arm_rows) == 3  # manual, generated, reduced
    assert tuple(arm_rows[0].keys()) == runner._ARM_FIELDS
    assert [r["arm"] for r in arm_rows] == ["manual", "generated", "reduced"]

    on_disk = json.loads(summary_path.read_text(encoding="utf-8"))
    assert on_disk == summary


def test_all_arms_share_one_fixed_holdout(tmp_path):
    summary = runner.run(_write_config(tmp_path))
    # The controlled variable is the training source; the holdout is the manual
    # holdout tree, identical for every arm.
    assert summary["shared_holdout_scenario_count"] == 3
    names = [s["name"] for s in summary["shared_holdout_scenarios"]]
    assert names == ["holdout_mild", "holdout_stress", "holdout_severe"]


def test_reduced_arm_has_target_count_and_records_distance(tmp_path):
    summary = runner.run(_write_config(tmp_path))
    by_arm = {r["arm"]: r for r in summary["arm_results"]}
    # Generated draws 16 training scenarios; reduced thins to 8 with a recorded,
    # nonnegative Kantorovich distance.
    assert by_arm["generated"]["training_scenario_count"] == 16
    assert by_arm["reduced"]["training_scenario_count"] == 8
    assert by_arm["reduced"]["reduction_kantorovich_distance"] >= 0.0
    assert by_arm["manual"]["reduction_kantorovich_distance"] is None


# ---------------------------------------------------------------------------
# H2 robustness (reported, not gated) and honesty tags
# ---------------------------------------------------------------------------
def test_h2_underdelivery_is_reported_per_arm(tmp_path):
    summary = runner.run(_write_config(tmp_path))
    # On this frozen mechanism point B6 must under-deliver out of sample in every
    # evaluable arm, so the robustness flag holds.
    for arm in summary["arm_results"]:
        assert arm["training_feasible"] is True
        assert arm["h2_b6_underdelivers_out_of_sample"] is True
    assert summary["h2_robust_across_sources"] is True
    assert summary["evaluable_arm_count"] == 3


def test_generated_and_reduced_arms_carry_honesty_tags(tmp_path):
    runner.run(_write_config(tmp_path))
    arm_rows = _read_csv(tmp_path / "arms.csv")
    by_arm = {r["arm"]: r for r in arm_rows}
    # Generated arm: MW-derived, sampling-weight, not-empirical tag present.
    gen_status = by_arm["generated"]["parameter_status"]
    assert "derived" in gen_status and "not_empirical_outage" in gen_status
    # Reduced arm: additionally carries the reduction (subset-of-input) tag.
    red_status = by_arm["reduced"]["parameter_status"]
    assert "derived" in red_status
    assert "reduced_by_fast_forward_selection" in red_status
    # Manual arm: labelled but never claims derived/empirical content.
    assert "manual_training_tree" in by_arm["manual"]["parameter_status"]


def test_summary_never_certifies(tmp_path):
    summary = runner.run(_write_config(tmp_path))
    assert summary["security_certified"] is False
    assert summary["formal_vma_published"] is False
    assert summary["empirical_holdout_claimed"] is False
    arm_rows = _read_csv(tmp_path / "arms.csv")
    assert all(r["security_certified"] == "False" for r in arm_rows)


def test_gate_passes_on_reference_case(tmp_path):
    summary = runner.run(_write_config(tmp_path))
    for arm in summary["arm_results"]:
        assert arm["cvar_cross_check_passed"] is True
    assert summary["gate_passed"] is True


# ---------------------------------------------------------------------------
# Arm subsetting
# ---------------------------------------------------------------------------
def test_manual_only_arm_runs_without_generator(tmp_path):
    def manual_only(config):
        config["arms"] = ["manual"]
        # A bad generator block must not matter when no generated/reduced arm is
        # requested (the generator is only read lazily by those arms).
        config.pop("generator", None)
        config.pop("reduction", None)

    summary = runner.run(_write_config(tmp_path, manual_only))
    assert [a["arm"] for a in summary["arm_results"]] == ["manual"]
    assert summary["gate_passed"] is True


# ---------------------------------------------------------------------------
# Fail-closed behaviour
# ---------------------------------------------------------------------------
def test_infeasible_training_fails_closed(tmp_path):
    def make_infeasible(config):
        # A training grid_need above the budget cap makes the manual plan itself
        # infeasible; that arm cannot form the H2 comparison, so the gate fails.
        config["arms"] = ["manual"]
        config["training_scenarios"][1]["grid_need_mw"] = 500.0

    summary = runner.run(_write_config(tmp_path, make_infeasible))
    manual = summary["arm_results"][0]
    assert manual["training_feasible"] is False
    assert summary["gate_passed"] is False
    # An arm that cannot be evaluated is excluded from the robustness test.
    assert summary["evaluable_arm_count"] == 0
    assert summary["h2_robust_across_sources"] is False


def test_unknown_arm_is_rejected(tmp_path):
    def bad_arm(config):
        config["arms"] = ["manual", "empirical"]

    with pytest.raises(ValueError, match="unknown arm"):
        runner.run(_write_config(tmp_path, bad_arm))


def test_duplicate_arms_are_rejected(tmp_path):
    def dup(config):
        config["arms"] = ["manual", "manual"]

    with pytest.raises(ValueError, match="unique"):
        runner.run(_write_config(tmp_path, dup))


def test_self_certifying_config_is_rejected(tmp_path):
    def certify(config):
        config["evaluation"]["security_certified"] = True

    with pytest.raises(ValueError, match="security_certified"):
        runner.run(_write_config(tmp_path, certify))


def test_reduced_arm_requires_reduction_block(tmp_path):
    def drop_reduction(config):
        config["arms"] = ["reduced"]
        config.pop("reduction", None)

    with pytest.raises(ValueError, match="reduction"):
        runner.run(_write_config(tmp_path, drop_reduction))


def test_main_exits_nonzero_when_gate_fails(tmp_path, monkeypatch):
    def make_infeasible(config):
        config["arms"] = ["manual"]
        config["training_scenarios"][1]["grid_need_mw"] = 500.0

    config_path = _write_config(tmp_path, make_infeasible)
    monkeypatch.setattr("sys.argv", ["run", "--config", str(config_path)])
    with pytest.raises(SystemExit) as excinfo:
        runner.main()
    assert excinfo.value.code == 1


def test_cross_check_failure_fails_arm_gate(tmp_path, monkeypatch):
    # If the module's reported CVaR is corrupted, the independent cross-check
    # must catch it and fail that arm's gate (correctness gate, not H2).
    original = runner._cross_check_policy_cvar

    def corrupt(inputs, policy):
        base = original(inputs, policy)
        if base is None:
            return None
        return base + 1.0  # inject a large discrepancy

    def manual_only(config):
        config["arms"] = ["manual"]

    monkeypatch.setattr(runner, "_cross_check_policy_cvar", corrupt)
    summary = runner.run(_write_config(tmp_path, manual_only))
    assert summary["arm_results"][0]["cvar_cross_check_passed"] is False
    assert summary["gate_passed"] is False
