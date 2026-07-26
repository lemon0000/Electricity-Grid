from __future__ import annotations

import json
from dataclasses import make_dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from pyomo.environ import ConcreteModel, Objective, Var, maximize, minimize

from experiments import benchmark_rts_gmlc_zero_dc_ac_aware_solver as benchmark


CONFIG = Path("configs/rts_gmlc_zero_dc_ac_aware_solver_benchmark.yaml")


def test_config_freezes_proxy_only_monolith_matrix() -> None:
    config = benchmark._read_config(CONFIG)

    assert config["formulation"]["included"] == ["full_state_monolith"]
    assert not config["formulation"][
        "exact_selected_state_constraint_generation_included"
    ]
    assert config["formulation"]["stages_constructed"] == [
        "proxy_maximization",
        "cost_normalization",
    ]
    assert config["formulation"]["stages_executed"] == ["proxy_maximization"]
    assert config["solver_matrix"]["threads"] == [1, 4, 8]
    assert config["solver_matrix"]["repetitions"] == 2
    assert config["solver_matrix"]["time_limit_seconds_per_stage"] == 120.0
    assert config["budget"]["relative_delta"] == 0.0075
    assert not config["budget"]["belongs_to_formal_v2_grid"]
    assert not config["selection"]["objective_value_used"]
    assert config["output"]["log_directory"] == (
        "results/logs/rts_gmlc_zero_dc_ac_aware_solver_benchmark_v1"
    )
    assert config["expected_model_size"] == {
        "base_variables": 53922,
        "base_constraints": 87508,
        "cost_cap_constraints_added": 1,
        "proxy_variables_added": 1,
        "reactive_proxy_constraints_added": 36,
        "proxy_stage_total_variables": 53923,
        "proxy_stage_total_constraints": 87545,
    }


def test_config_rejects_selection_by_objective(tmp_path: Path) -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["selection"]["objective_value_used"] = True
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="selection rule"):
        benchmark._read_config(path)


def test_parent_cost_reconstruction_uses_piecewise_and_transition_costs() -> None:
    generator = SimpleNamespace(
        uid="g1",
        dispatch_mode="committable",
        cost_breakpoints_mw=(10.0, 20.0, 30.0, 40.0),
        cost_values_usd_per_hour=(100.0, 150.0, 210.0, 280.0),
        cold_start_cost_usd=50.0,
        shutdown_cost_usd=7.0,
    )
    timestamps = ("h0", "h1", "h2")
    generation = {"h0": {"g1": 10.0}, "h1": {"g1": 25.0}, "h2": {"g1": 0.0}}
    commitment = {"h0": {"g1": True}, "h1": {"g1": True}, "h2": {"g1": False}}

    hourly = benchmark._reconstruct_hourly_costs(
        (generator,), timestamps, generation, commitment, {"g1": False}
    )

    assert hourly == pytest.approx((150.0, 180.0, 7.0))
    assert sum(hourly) == pytest.approx(337.0)


def test_request_truncation_slices_every_chronological_field() -> None:
    request_type = make_dataclass(
        "Request",
        [(field, tuple) for field in benchmark._SEQUENCE_FIELDS] + [("marker", str)],
        frozen=True,
    )
    request = request_type(
        **{field: tuple(range(8)) for field in benchmark._SEQUENCE_FIELDS},
        marker="unchanged",
    )

    observed = benchmark._truncate_request(request, 0, 6)

    assert all(getattr(observed, field) == tuple(range(6)) for field in benchmark._SEQUENCE_FIELDS)
    assert observed.marker == "unchanged"


def _record(threads: int, repetition: int, seconds: float, accepted: bool, objective: float):
    return {
        "threads": threads,
        "repetition": repetition,
        "solver_wall_seconds": seconds,
        "accepted": accepted,
        "proxy_fraction": objective,
    }


def test_selection_requires_both_repetitions_and_ignores_objective() -> None:
    records = [
        _record(1, 1, 9.0, True, 0.99),
        _record(1, 2, 10.0, False, 0.99),
        _record(4, 1, 6.0, True, 0.10),
        _record(4, 2, 8.0, True, 0.10),
        _record(8, 1, 7.0, True, 0.90),
        _record(8, 2, 9.0, True, 0.90),
    ]

    selection = benchmark._select_configuration(records, (1, 4, 8), 2)

    assert selection["selected_threads"] == 4
    assert not selection["objective_value_used"]
    assert not next(item for item in selection["configurations"] if item["threads"] == 1)["eligible"]


def test_cost_stage_activation_preserves_registered_proxy_floor() -> None:
    model = ConcreteModel()
    model.reactive_proxy = Var(bounds=(0.0, 1.0))
    model.operating_cost = Var()
    model.objective = Objective(expr=model.operating_cost, sense=minimize)
    model.reactive_proxy_objective = Objective(expr=model.reactive_proxy, sense=maximize)
    model.objective.deactivate()

    benchmark._activate_cost_normalization_stage(model, 0.7, 1.0e-7)

    assert model.objective.active
    assert not model.reactive_proxy_objective.active
    model.reactive_proxy.set_value(0.7 - 1.0e-7)
    assert model.reactive_proxy_floor.body() >= model.reactive_proxy_floor.lower()


def test_jsonl_events_are_complete_records(tmp_path: Path) -> None:
    path = tmp_path / "progress.jsonl"
    benchmark._append_jsonl(path, {"event": "started", "run": 1})
    benchmark._append_jsonl(path, {"event": "completed", "run": 1})

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows == [
        {"event": "started", "run": 1},
        {"event": "completed", "run": 1},
    ]


def test_prepare_hash_locks_inputs_without_running_benchmark(tmp_path: Path) -> None:
    output = tmp_path / "pilot"

    first = benchmark.prepare(CONFIG, output_directory=output)
    second = benchmark.prepare(CONFIG, output_directory=output)

    assert first == second
    assert first["status"] == "prepared_not_run"
    assert first["parent"]["operational_termination_manifest_sha256"]
    assert (output / "preparation" / "SHA256SUMS").is_file()
    assert not (output / "benchmark").exists()


def test_run_refuses_to_build_without_preparation(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="requires a published"):
        benchmark.run_benchmark(CONFIG, output_directory=tmp_path / "missing")
