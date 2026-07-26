from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml
from pyomo.environ import (
    Binary,
    Constraint,
    ConcreteModel,
    Integers,
    Objective,
    SolverFactory,
    Var,
    maximize,
)

from experiments import benchmark_rts_gmlc_zero_dc_ac_aware_warmstart as benchmark

_CONFIG = Path("configs/rts_gmlc_zero_dc_ac_aware_warmstart_benchmark.yaml")


def test_config_freezes_nonformal_objective_independent_matrix() -> None:
    config = benchmark._read_config(_CONFIG)

    assert (
        config["preregistration"]["id"]
        == "rts_gmlc_google_day0_zero_dc_ac_aware_warmstart_benchmark_v3"
    )
    assert (
        config["preregistration"]["schema"]
        == "rts_gmlc_zero_dc_ac_aware_warmstart_benchmark_v3"
    )
    assert not config["provenance"]["superseded_v1_competitive_solve_executed"]
    assert not config["provenance"][
        "superseded_v2_completed_runs_allowed_for_successor_selection"
    ]
    assert config["provenance"][
        "superseded_v2_successor_must_rerun_complete_registered_matrix"
    ]
    assert config["preregistration"]["v3_runtime_outcome_used_to_motivate_pilot"]
    assert not config["preregistration"]["v3_objective_value_used_for_method_selection"]
    assert config["benchmark"]["execution_order"] == [
        "highs_cold_start_r1",
        "appsi_highs_full_mip_start_r1",
        "appsi_highs_full_mip_start_r2",
        "highs_cold_start_r2",
    ]
    assert config["benchmark"]["attempt_id"] == (
        "warmstart_benchmark_v3_registered_run1"
    )
    assert config["solver"]["time_limit_seconds_per_run"] == 3600.0
    assert config["warm_start"]["submission_scope"] == "every_solver_column"
    assert not config["warm_start"]["missing_values_allowed"]
    assert not config["selection"]["objective_value_used"]
    assert config["output"]["directory"] == (
        "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_warmstart_benchmark_v3"
    )
    assert config["output"]["log_directory"] == (
        "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_warmstart_benchmark_v3"
    )


def test_v3_provenance_requires_published_v2_invalidation() -> None:
    config = benchmark._read_config(_CONFIG)

    verified = benchmark._verify_provenance(config)

    assert verified["superseded_v2_completed_solve_count"] == 2
    assert verified["superseded_v2_planned_solve_count"] == 4
    assert verified["superseded_v2_completed_runs_are_diagnostic_only"]
    assert not verified["superseded_v2_completed_runs_allowed_for_successor_selection"]
    assert verified["superseded_v2_successor_must_rerun_complete_registered_matrix"]
    assert verified["superseded_v2_invalidation_manifest_sha256"] == (
        "2d899b57a665048518f61866f1643f8bdd72b50e87d2ef7b9d9c59c4692a69ac"
    )


def test_v3_provenance_rejects_tampered_v2_invalidation_manifest() -> None:
    config = benchmark._read_config(_CONFIG)
    config["provenance"]["superseded_v2_invalidation_manifest_sha256"] = "0" * 64

    with pytest.raises(RuntimeError, match="superseded v2 invalidation manifest"):
        benchmark._verify_provenance(config)


def test_config_rejects_missing_value_zero_fill(tmp_path: Path) -> None:
    config = yaml.safe_load(_CONFIG.read_text(encoding="utf-8"))
    config["warm_start"]["zero_fill_missing_values_allowed"] = True
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="frozen contract"):
        benchmark._read_config(path)


def test_native_log_parser_records_acceptance_and_first_incumbent(
    tmp_path: Path,
) -> None:
    path = tmp_path / "highs.log"
    path.write_text(
        "MIP start solution is feasible, objective value is 0.243281471\n"
        " X       0       0         0   0.00%   0.26  0.243281471  6.87%"
        " 0 0 0 12 3.4s\n",
        encoding="utf-8",
    )

    parsed = benchmark._parse_native_log(
        path,
        acceptance_text="MIP start solution is feasible, objective value is",
        rejection_text="MIP start solution is infeasible",
    )

    assert parsed["mip_start_acceptance_line_count"] == 1
    assert parsed["mip_start_rejection_line_count"] == 0
    assert parsed["mip_start_accepted_objective"] == pytest.approx(0.243281471)
    assert parsed["first_finite_incumbent_seconds"] == 3.4
    assert parsed["first_finite_incumbent_source"] == "X"


def test_native_log_parser_does_not_accept_rejected_start(tmp_path: Path) -> None:
    path = tmp_path / "highs.log"
    path.write_text("MIP start solution is infeasible\n", encoding="utf-8")

    parsed = benchmark._parse_native_log(
        path,
        acceptance_text="MIP start solution is feasible, objective value is",
        rejection_text="MIP start solution is infeasible",
    )

    assert parsed["mip_start_acceptance_line_count"] == 0
    assert parsed["mip_start_rejection_line_count"] == 1
    assert parsed["first_finite_incumbent_seconds"] is None


def test_audited_appsi_hook_submits_every_mapped_column() -> None:
    model = ConcreteModel()
    model.x = Var(initialize=1.25)
    model.y = Var(initialize=-2.5)

    class FakeHighs:
        def setSolution(self, solution):
            self.values = np.asarray(solution.col_value)
            return SimpleNamespace(__str__=lambda _self: "HighsStatus.kOk")

    fake_highs = FakeHighs()
    solver = SimpleNamespace(
        _pyomo_var_to_solver_var_map={id(model.x): 1, id(model.y): 0},
        _vars={id(model.x): (model.x,), id(model.y): (model.y,)},
        _solver_model=fake_highs,
    )
    benchmark._install_audited_appsi_warm_start(solver)

    solver._warm_start()

    assert fake_highs.values.tolist() == [-2.5, 1.25]
    assert solver._warmstart_submitted_column_count == 2


def test_appsi_legacy_warmstart_preserves_bounds_load_and_native_evidence(
    tmp_path: Path,
) -> None:
    model = ConcreteModel()
    model.x1 = Var(domain=Integers, bounds=(0, 10), initialize=4)
    model.x2 = Var(bounds=(0, 10), initialize=4.5)
    model.x3 = Var(domain=Binary, initialize=True)
    model.objective = Objective(
        expr=3 * model.x1 + 2 * model.x2 + 4 * model.x3, sense=maximize
    )
    model.c1 = Constraint(expr=model.x1 + model.x2 <= 9)
    model.c2 = Constraint(expr=3 * model.x1 + model.x2 <= 18)
    native_log = tmp_path / "appsi_highs.log"
    solver = SolverFactory("appsi_highs")
    benchmark._install_audited_appsi_warm_start(solver)

    results = solver.solve(
        model,
        load_solutions=False,
        warmstart=True,
        options={"log_file": str(native_log), "mip_rel_gap": 1.0e-4},
    )

    assert str(solver._warmstart_submission_status) == "HighsStatus.kOk"
    assert results.problem.lower_bound is not None
    assert results.problem.upper_bound is not None
    model.solutions.load_from(results)
    parsed = benchmark._parse_native_log(
        native_log,
        acceptance_text="MIP start solution is feasible, objective value is",
        rejection_text="MIP start solution is infeasible",
    )
    assert parsed["mip_start_acceptance_line_count"] == 1
    assert parsed["mip_start_rejection_line_count"] == 0


def test_selection_uses_runtime_not_objective_values() -> None:
    config = benchmark._read_config(_CONFIG)
    runs = []
    for method, first_seconds, solve_seconds, objective in (
        ("highs_cold_start", 100.0, 120.0, 999.0),
        ("appsi_highs_full_mip_start", 2.0, 20.0, -999.0),
    ):
        for repetition in (1, 2):
            runs.append(
                {
                    "method": method,
                    "repetition": repetition,
                    "eligible": True,
                    "solve_seconds": solve_seconds + repetition,
                    "incumbent_objective": objective,
                    "native_log_evidence": {
                        "first_finite_incumbent_seconds": first_seconds + repetition
                    },
                }
            )

    selection = benchmark._select_method(config, runs)

    assert selection["selected_method"] == "appsi_highs_full_mip_start"
    assert not selection["objective_value_used"]


def test_parent_dispatch_covers_and_audits_every_master_column() -> None:
    config = benchmark._read_config(_CONFIG)
    benchmark._verify_provenance(config)
    problem, handle = benchmark._build_handle(config)

    audit = benchmark._assign_parent_start(config, problem, handle)

    assert audit["passed"]
    assert audit["variable_count"] == 88969
    assert audit["missing_variable_count"] == 0
    assert audit["maximum_constraint_violation"] <= 1.0e-6
    assert audit["maximum_integrality_violation"] <= 1.0e-8
    assert audit["residual_audit"]["passed"]
    assert audit["reactive_proxy"] == pytest.approx(0.24328147100424327)
