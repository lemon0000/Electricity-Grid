"""End-to-end tests for the chronological RQ2 H2 holdout runner."""

from __future__ import annotations

import csv
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


def _raw_scenario(name: str, probability: float, *, holdout: bool) -> dict:
    return {
        "name": name,
        "probability": probability,
        "periods": ["q1", "q1", "q1", "q1"],
        "system_load_multiplier": [1.0, 1.0, 1.0, 1.0],
        "data_center_demand_mw": [80.0, 80.0, 80.0, 80.0],
        "network_call_active": [0, 1, 0, 0],
        "green_call_mw": [0.0, 40.0 if not holdout else 50.0, 0.0, 0.0],
        "connected_demand_mw": [80.0, 80.0, 80.0, 80.0],
        "recovery_headroom_mw": [0.0, 0.0, 100.0, 100.0],
        "completed_periods": ["q1"],
        "require_terminal_event_inactive": True,
        "boundary_state_status": "clean_boundary_with_zero_carry_in",
    }


def _config(tmp_path: Path) -> dict:
    result_dir = tmp_path / "result"
    return {
        "evaluation": {
            "id": "temporal_h2_test",
            "parameter_status": "synthetic_test_not_empirical",
            "security_certified": False,
            "formal_vma_published": False,
        },
        "scenario_source": "manual",
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
            "provisioning_cost_per_mw": 100.0,
            "lambda_risk": 0.0,
            "beta": 0.5,
            "service_shortfall_tolerance_mwh": 1.0e-6,
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
            "maximum_events_by_period": {"q1": 2},
            "maximum_curtailment_energy_mwh_by_period": {"q1": 200.0},
            "maximum_recovery_debt_mwh": 200.0,
            "maximum_recovery_power_mw": 100.0,
            "minimum_event_power_mw": 1.0,
            "response_time_hours": 1.0,
            "curtailment_ramp_mw_per_hour": 100.0,
            "recovery_efficiency": 1.0,
            "terminal_debt_limit_mwh_by_period": {"q1": 0.0},
            "parameter_status": "synthetic_test",
        },
        "training_scenarios": [
            _raw_scenario("train", 1.0, holdout=False)
        ],
        "holdout_scenarios": [
            _raw_scenario("holdout", 1.0, holdout=True)
        ],
        "validation": {
            "fail_closed_on_unresolved": True,
            "fail_closed_on_infeasible_training": True,
        },
        "output": {
            "leaves_path": str(result_dir / "leaves.csv"),
            "summary_path": str(result_dir / "summary.json"),
        },
    }


def test_runner_pins_temporal_policies_and_writes_auditable_outputs(
    tmp_path: Path, two_line_grid: Rts24Data, monkeypatch
):
    yaml = pytest.importorskip("yaml")
    from experiments import run_rq2_h2_temporal_holdout as runner

    config = _config(tmp_path)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setattr(runner, "load_rts24", lambda: two_line_grid)

    summary = runner.run(path)

    assert summary["gate_passed"]
    assert summary["security_certified"] is False
    assert summary["empirical_holdout_claimed"] is False
    assert summary["scenario_source"] == "manual"
    for method in ("minimum_curtailment", "overload_sensitivity"):
        result = summary["methods"][method]
        assert result["correct"]["committed_flexibility_mw"] == pytest.approx(
            80.0
        )
        assert result["b6"]["committed_flexibility_mw"] == pytest.approx(40.0)
        assert result["h2_b6_underdelivers_out_of_sample"]
        assert result["b6_extra_expected_shortfall_mwh"] == pytest.approx(40.0)
        assert result["network_provenance"]["training"]
        assert result["network_provenance"]["holdout"]
    assert json.loads(
        (tmp_path / "result" / "summary.json").read_text(encoding="utf-8")
    ) == summary
    with (tmp_path / "result" / "leaves.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 4
    assert {row["policy"] for row in rows} == {"correct", "b6"}
    assert all("terminal_grid_call_mw" in row for row in rows)
    assert all("terminal_active_event_duration_hours" in row for row in rows)
    assert all("terminal_interevent_rest_hours" in row for row in rows)
    assert all("terminal_has_prior_event" in row for row in rows)
    manifest = json.loads(
        (tmp_path / "result" / "SHA256SUMS.json").read_text(encoding="utf-8")
    )
    assert set(manifest) == {"leaves.csv", "summary.json"}


def test_runner_rejects_overlapping_train_holdout_names(
    tmp_path: Path, two_line_grid: Rts24Data, monkeypatch
):
    yaml = pytest.importorskip("yaml")
    from experiments import run_rq2_h2_temporal_holdout as runner

    config = _config(tmp_path)
    config["holdout_scenarios"][0]["name"] = "train"
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setattr(runner, "load_rts24", lambda: two_line_grid)

    with pytest.raises(ValueError, match="names must be disjoint"):
        runner.run(path)


def test_runner_freezes_both_plans_before_any_holdout_network_solve(
    tmp_path: Path, two_line_grid: Rts24Data, monkeypatch
):
    yaml = pytest.importorskip("yaml")
    from experiments import run_rq2_h2_temporal_holdout as runner

    config = _config(tmp_path)
    config["network"]["methods"] = ["minimum_curtailment"]
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setattr(runner, "load_rts24", lambda: two_line_grid)
    events = []
    real_derive = runner._derive_temporal_scenarios
    real_plan = runner.plan_temporal_economic_policies

    def record_derive(*args, **kwargs):
        events.append(
            "derive_holdout"
            if kwargs["raw_scenarios"][0]["name"].startswith("holdout")
            else "derive_training"
        )
        return real_derive(*args, **kwargs)

    def record_plan(*args, **kwargs):
        events.append("freeze_both_plans")
        return real_plan(*args, **kwargs)

    monkeypatch.setattr(runner, "_derive_temporal_scenarios", record_derive)
    monkeypatch.setattr(
        runner, "plan_temporal_economic_policies", record_plan
    )

    runner.run(path)

    assert events == [
        "derive_training",
        "freeze_both_plans",
        "derive_holdout",
    ]


def test_runner_rejects_unknown_scenario_source(
    tmp_path: Path,
):
    yaml = pytest.importorskip("yaml")
    from experiments import run_rq2_h2_temporal_holdout as runner

    config = _config(tmp_path)
    config["scenario_source"] = "empirical"
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")

    with pytest.raises(ValueError, match="scenario_source"):
        runner.run(path)


@pytest.mark.parametrize(
    ("source", "expected_count"),
    [("generated", 4), ("reduced", 2)],
)
def test_runner_supports_generated_and_reduced_temporal_training(
    tmp_path: Path,
    two_line_grid: Rts24Data,
    monkeypatch,
    source: str,
    expected_count: int,
):
    yaml = pytest.importorskip("yaml")
    from experiments import run_rq2_h2_temporal_holdout as runner

    trace = tmp_path / "trace.csv"
    trace.write_text(
        "grid,green\n"
        + "\n".join(
            f"{grid},{green}"
            for grid, green in (
                (0.1, 0.2),
                (0.8, 0.7),
                (0.2, 0.1),
                (0.7, 0.6),
                (0.1, 0.1),
                (0.9, 0.8),
                (0.2, 0.3),
                (1.0, 1.0),
                (0.1, 0.2),
                (0.8, 0.7),
                (0.2, 0.1),
                (0.7, 0.6),
            )
        )
        + "\n",
        encoding="utf-8",
    )
    config = _config(tmp_path)
    config["scenario_source"] = source
    config["network"]["methods"] = ["minimum_curtailment"]
    config["generator"] = {
        "parameter_status": "trace_derived_test_not_empirical",
        "split_fraction": 0.5,
        "core_window_hours": 2,
        "recovery_tail_hours": 2,
        "n_train": 4,
        "n_holdout": 3,
        "seed": 7,
        "period": "q1",
        "data_center_demand_mw": 80.0,
        "system_load_multiplier": 1.0,
        "green_call_scale_mw": 40.0,
        "network_activation_threshold": 0.5,
        "recovery_headroom_mw": 100.0,
        "grid_stress_shape": {"path": str(trace), "column": "grid"},
        "green_workload_shape": {"path": str(trace), "column": "green"},
    }
    config["reduction"] = {
        "target_count": 2,
        "ground_norm_order": 2.0,
        "component_scales": {
            "network_call_active": 1.0,
            "green_call_mw": 40.0,
            "data_center_demand_mw": 80.0,
            "system_load_multiplier": 1.0,
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setattr(runner, "load_rts24", lambda: two_line_grid)

    summary = runner.run(path)

    assert summary["scenario_source"] == source
    assert summary["gate_passed"]
    provenance = summary["scenario_source_provenance"]
    assert provenance["source"] == source
    assert "sha256=" in provenance["generator"]["sources"]["grid"]
    assert "sha256=" in provenance["generator"]["sources"]["green"]
    if source == "reduced":
        assert provenance["reduction"]["target_count"] == expected_count
        training_status = summary["methods"]["minimum_curtailment"][
            "training_source_parameter_status"
        ]
        assert "chronological_training_distribution_reduced" in training_status
    holdout_status = summary["methods"]["minimum_curtailment"][
        "holdout_source_parameter_status"
    ]
    assert "continuous_hourly_profiles_derived" in holdout_status
    assert "reduced_by_fast_forward" not in holdout_status
    with (tmp_path / "result" / "leaves.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        leaf_statuses = {
            row["parameter_status"] for row in csv.DictReader(handle)
        }
    assert all("continuous_hourly_profiles_derived" in item for item in leaf_statuses)
    assert all("reduced_by_fast_forward" not in item for item in leaf_statuses)
    assert "not_empirical" in summary["parameter_status"]


def test_atomic_publication_leaves_no_partial_directory_on_write_failure(
    tmp_path: Path, monkeypatch
):
    from experiments import run_rq2_h2_temporal_holdout as runner

    target = tmp_path / "result"

    def fail_write(*args, **kwargs):
        assert args or kwargs
        raise OSError("injected")

    monkeypatch.setattr(runner, "_write_leaves", fail_write)
    with pytest.raises(OSError, match="injected"):
        runner._publish_outputs(
            target,
            leaves_name="leaves.csv",
            summary_name="summary.json",
            leaves=[],
            summary={"gate_passed": True},
        )

    assert not target.exists()
    assert list(tmp_path.glob(".result.processing-*")) == []
