"""Tests for the temporal H2 training-source ablation runner."""

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


def _manual_training() -> list[dict]:
    return [
        {
            "name": "manual_train",
            "probability": 1.0,
            "periods": ["q1"] * 4,
            "system_load_multiplier": [1.0] * 4,
            "data_center_demand_mw": [80.0] * 4,
            "network_call_active": [0, 1, 0, 0],
            "green_call_mw": [0.0, 30.0, 0.0, 0.0],
            "connected_demand_mw": [80.0] * 4,
            "recovery_headroom_mw": [100.0] * 4,
            "completed_periods": ["q1"],
            "require_terminal_event_inactive": True,
            "boundary_state_status": "clean_boundary_with_zero_carry_in",
        }
    ]


def _config(tmp_path: Path) -> dict:
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
    return {
        "evaluation": {
            "id": "temporal_source_ablation_test",
            "parameter_status": "synthetic_test_not_empirical",
            "security_certified": False,
            "formal_vma_published": False,
        },
        "arms": ["manual", "generated", "reduced"],
        "network": {
            "case_name": "case24_ieee_rts",
            "poi_bus": 2,
            "balancing_bus": 1,
            "methods": ["minimum_curtailment"],
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
        "manual_training_scenarios": _manual_training(),
        "generator": {
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
        },
        "reduction": {
            "target_count": 2,
            "ground_norm_order": 2.0,
            "component_scales": {
                "network_call_active": 1.0,
                "green_call_mw": 40.0,
                "data_center_demand_mw": 80.0,
                "system_load_multiplier": 1.0,
            },
        },
        "validation": {
            "fail_closed_on_unresolved": True,
            "fail_closed_on_infeasible_training": True,
        },
        "output": {"directory": str(tmp_path / "result")},
    }


def _write_config(tmp_path: Path, config: dict) -> Path:
    yaml = pytest.importorskip("yaml")
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def test_ablation_uses_one_holdout_and_publishes_all_arms(
    tmp_path: Path, two_line_grid: Rts24Data, monkeypatch
):
    from experiments import run_rq2_h2_temporal_holdout as temporal_runner
    from experiments import run_rq2_h2_temporal_source_ablation as runner

    monkeypatch.setattr(temporal_runner, "load_rts24", lambda: two_line_grid)
    summary = runner.run(_write_config(tmp_path, _config(tmp_path)))

    assert summary["gate_passed"]
    assert summary["security_certified"] is False
    assert summary["shared_holdout_scenario_count"] == 3
    assert len(summary["shared_holdout_sha256"]) == 64
    assert len(summary["generated_draw_sha256"]) == 64
    assert set(summary["arm_results"]) == {"manual", "generated", "reduced"}
    robustness = summary["robustness_by_network_method"]["minimum_curtailment"]
    assert robustness["evaluable_arm_count"] == 3
    assert robustness["all_requested_arms_evaluable"] is True

    result_dir = tmp_path / "result"
    assert {
        path.name for path in result_dir.iterdir()
    } == {"arms.csv", "leaves.csv", "summary.json", "SHA256SUMS.json"}
    with (result_dir / "arms.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    assert [row["arm"] for row in rows] == [
        "manual",
        "generated",
        "reduced",
    ]
    assert rows[-1]["training_scenario_count"] == "2"
    assert all(row["security_certified"] == "False" for row in rows)
    with (result_dir / "leaves.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        leaves = list(csv.DictReader(handle))
    assert all(
        "continuous_hourly_profiles_derived" in row["parameter_status"]
        for row in leaves
    )
    assert all(
        "reduced_by_fast_forward" not in row["parameter_status"]
        for row in leaves
    )
    by_arm = {row["arm"]: row for row in rows}
    assert "chronological_training_distribution_reduced" in by_arm["reduced"][
        "training_parameter_status"
    ]
    assert "chronological_training_distribution_reduced" not in by_arm[
        "reduced"
    ]["holdout_parameter_status"]
    assert json.loads(
        (result_dir / "summary.json").read_text(encoding="utf-8")
    ) == summary


def test_noop_reduction_reports_actual_retained_count(
    tmp_path: Path, two_line_grid: Rts24Data, monkeypatch
):
    from experiments import run_rq2_h2_temporal_holdout as temporal_runner
    from experiments import run_rq2_h2_temporal_source_ablation as runner

    config = _config(tmp_path)
    config["arms"] = ["reduced"]
    config["reduction"]["target_count"] = 99
    monkeypatch.setattr(temporal_runner, "load_rts24", lambda: two_line_grid)

    runner.run(_write_config(tmp_path, config))

    with (tmp_path / "result" / "arms.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        row = next(csv.DictReader(handle))
    assert row["training_scenario_count"] == "4"


def test_robustness_requires_every_requested_arm_to_be_evaluable():
    from experiments import run_rq2_h2_temporal_source_ablation as runner

    result = runner._source_robustness(
        methods=["minimum_curtailment"],
        arms=["manual", "generated", "reduced"],
        arm_rows=[
            {
                "network_method": "minimum_curtailment",
                "h2_evaluated": True,
                "h2_b6_underdelivers_out_of_sample": True,
            },
            {
                "network_method": "minimum_curtailment",
                "h2_evaluated": False,
                "h2_b6_underdelivers_out_of_sample": False,
            },
            {
                "network_method": "minimum_curtailment",
                "h2_evaluated": True,
                "h2_b6_underdelivers_out_of_sample": True,
            },
        ],
    )["minimum_curtailment"]

    assert result["evaluable_arm_count"] == 2
    assert result["all_requested_arms_evaluable"] is False
    assert result["h2_robust_across_sources"] is False


def test_unknown_or_duplicate_arm_fails_closed(tmp_path: Path):
    from experiments import run_rq2_h2_temporal_source_ablation as runner

    config = _config(tmp_path)
    config["arms"] = ["manual", "manual"]
    with pytest.raises(ValueError, match="arms"):
        runner.run(_write_config(tmp_path, config))


def test_atomic_publication_removes_staging_after_failure(
    tmp_path: Path, monkeypatch
):
    from experiments import run_rq2_h2_temporal_source_ablation as runner

    def fail(*args, **kwargs):
        assert args or kwargs
        raise OSError("injected")

    monkeypatch.setattr(runner, "_write_csv", fail)
    target = tmp_path / "result"
    with pytest.raises(OSError, match="injected"):
        runner._publish(
            target,
            arm_rows=[],
            leaf_rows=[],
            leaf_fields=("arm",),
            summary={"gate_passed": True},
        )
    assert not target.exists()
    assert list(tmp_path.glob(".result.processing-*")) == []
