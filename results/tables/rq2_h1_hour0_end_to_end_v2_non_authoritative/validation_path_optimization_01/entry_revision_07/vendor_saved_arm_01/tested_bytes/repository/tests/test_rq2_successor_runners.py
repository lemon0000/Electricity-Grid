from __future__ import annotations

import csv
import gzip
import io
import json
from importlib.metadata import version
from pathlib import Path

import pytest
import yaml

import experiments.run_rq2_public_identification_grid_v4 as identification
import experiments.run_rq2_public_pairwise_replay_v4 as pairwise
import experiments.run_rts_gmlc_public_grid_need_dispatch_v4 as grid
from src.models.temporal_flexibility_capacity_successor import (
    MinimumFlexibilityCapacitySuccessor,
    MinimumFlexibilityPolicyPairSuccessor,
)
from src.scenarios.rq2_public_replay import (
    CausalPolicyOutcome,
    ParameterCell,
    TemporalBlock,
)
from src.scenarios.rq2_public_replay_successor import TrainingSupportAudit
from src.solvers.rq2_solver_adapter import Rq2SolverSpec


def _solver() -> Rq2SolverSpec:
    return Rq2SolverSpec(
        name="highs",
        expected_package_version=version("highspy"),
        threads=1,
        mip_relative_gap=0.0,
        feasibility_tolerance=1.0e-7,
        optimality_tolerance=1.0e-7,
        integer_feasibility_tolerance=1.0e-7,
        random_seed=0,
        time_limit_seconds=None,
        tee=False,
    )


def _contract() -> dict[str, object]:
    return {
        "contract_path": "configs/test_contract_v3.yaml",
        "contract_sha256": "1" * 64,
        "implementation": {
            "runner_sha256": "2" * 64,
            "module_sha256": {"successor": "3" * 64},
        },
        "software": {"highspy": version("highspy")},
    }


def _block(
    block_id: str,
    split: str,
    *,
    probability: float,
    power: bool,
) -> TemporalBlock:
    return TemporalBlock(
        block_id=block_id,
        split=split,
        probability=probability,
        first_source_hour=0,
        grid_need=(0.0, 0.0) if power else (),
        cfe_call=(0.1, 0.0) if power else (),
        workload=() if power else (1.0, 0.0),
    )


def _cell() -> ParameterCell:
    return ParameterCell(
        cell_id="base",
        varied_dimension="base",
        flexible_fraction=1.0,
        recovery_efficiency=1.0,
        normalized_recovery_headroom=1.0,
        maximum_event_duration_hours=1.0,
        maximum_event_count=1,
        normalized_energy_budget=1.0,
        normalized_debt_limit=1.0,
    )


def _capacity(joint: bool, capacity: float):
    return MinimumFlexibilityCapacitySuccessor(
        enforce_joint_budget=joint,
        feasible=True,
        proven_infeasible=False,
        minimum_capacity=capacity,
        termination_condition="optimal",
        solver_status="ok",
        maximum_residual=0.0,
        lower_bound=capacity,
        upper_bound=capacity,
        absolute_gap=0.0,
        relative_gap=0.0,
        gap_tolerance=1.0e-7,
        model_variables=10,
        model_constraints=20,
        solver_name="highs",
        solver_options={"threads": 1},
    )


def _outcome(name: str, committed: float) -> CausalPolicyOutcome:
    return CausalPolicyOutcome(
        name=name,
        committed_flexibility=committed,
        resolved=True,
        hard_grid_failure=False,
        physical_policy_failure=False,
        service_shortfall_failure=False,
        access_shortfall=0.0,
        peak_recovery_debt=0.0,
        terminal_recovery_debt=0.0,
        combined_call=(0.0, 0.0),
        green_served=(0.0, 0.0),
        physical_violations=(),
    )


def test_grid_v4_treats_E0_as_resolved_and_snapshots_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    config = {
        "input": {"power_system_blocks_manifest_sha256": "a" * 64},
        "grid_source": {"manifest_sha256": "b" * 64, "base_mva": 100.0},
        "model": {"dc_bus": 108, "dc_reference_demand_mw": 250.0},
        "solver": _solver().__dict__,
        "execution": {
            "formal_execution_ready": True,
            "independent_R4_review_passed": True,
            "user_formal_run_authorized": True,
            "require_all_blocks_resolved": True,
            "forbidden_hostnames": [],
            "required_environment_value": "TEST",
            "checkpoint_directory": str(tmp_path / "checkpoints"),
        },
        "output": {
            "schema": "test_grid_v4",
            "directory": str(tmp_path / "output"),
        },
    }
    config_path = tmp_path / "grid.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    blocks = {
        "training_b": [{"block_id": "training_b", "split": "training"}],
        "holdout_b": [{"block_id": "holdout_b", "split": "holdout"}],
    }
    marginals = {
        "training": [{"id": "training_b", "probability": 1.0}],
        "holdout": [{"id": "holdout_b", "probability": 1.0}],
    }
    monkeypatch.setattr(
        grid,
        "_preflight",
        lambda _path: (config, Path("."), blocks, marginals, _contract()),
    )
    monkeypatch.setattr(
        grid,
        "load_rts_gmlc_chronological_data",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(grid, "require_execution_host", lambda _execution: None)

    def result(_data, block, **_kwargs):
        return {
            "block_id": block[0]["block_id"],
            "split": block[0]["split"],
            "baseline_audit": {"accepted": True},
            "all_hours_resolved": True,
            "exogenous_grid_infeasibility_hour_count": (
                1 if block[0]["split"] == "holdout" else 0
            ),
            "outcomes": [],
            "rows": [],
        }

    monkeypatch.setattr(grid, "_process_block", result)
    summary = grid.run(config_path)

    assert summary["all_blocks_resolved"]
    assert summary["exogenous_grid_infeasibility_block_count"] == 1
    assert (tmp_path / "output/config.yaml").read_bytes() == config_path.read_bytes()
    manifest = json.loads(
        (tmp_path / "output/SHA256SUMS.json").read_text(encoding="utf-8")
    )
    assert "config.yaml" in manifest


def test_pairwise_v4_preserves_E0_mass_without_service_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    config = {
        "input": {
            "grid_need_dispatch_ready": True,
            "power_system_dispatch_manifest_sha256": "a" * 64,
            "workload_manifest_sha256": "b" * 64,
            "workload_config_sha256": "c" * 64,
            "workload_implementation_sha256": "d" * 64,
            "workload_source_sha256": "e" * 64,
        },
        "training_selection": {
            "power_system_representatives": 1,
            "workload_representatives": 1,
        },
        "fixed_policy": {
            "maximum_flexibility_budget": 1.0,
            "minimum_recovery_hours": 0.0,
            "minimum_event_power": 1.0e-8,
            "response_time_hours": 1.0,
            "curtailment_ramp_per_hour": 1.0,
            "service_shortfall_tolerance": 1.0e-6,
        },
        "solver": _solver().__dict__,
        "execution": {
            "formal_execution_ready": True,
            "independent_R4_review_passed": True,
            "user_formal_run_authorized": True,
            "require_all_training_plans_resolved": True,
            "require_all_pairwise_outcomes_resolved": True,
            "forbidden_hostnames": [],
            "required_environment_value": "TEST",
            "checkpoint_directory": str(tmp_path / "checkpoints"),
        },
        "output": {
            "schema": "test_pairwise_v4",
            "directory": str(tmp_path / "output"),
        },
    }
    config_path = tmp_path / "pairwise.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    training_power = (_block("pt", "training", probability=1.0, power=True),)
    holdout_power = (
        _block("pf", "holdout", probability=0.5, power=True),
        _block("pe", "holdout", probability=0.5, power=True),
    )
    training_workload = (
        _block("wt", "training", probability=1.0, power=False),
    )
    holdout_workload = (
        _block("wh", "holdout", probability=1.0, power=False),
    )
    context = {
        "report": {"schema": "test_preflight"},
        "power_training": training_power,
        "power_holdout": holdout_power,
        "workload_training": training_workload,
        "workload_holdout": holdout_workload,
        "cells": (_cell(),),
        "contract_identity": _contract(),
        "power_provenance_sha256": "f" * 64,
        "power_state_by_block": {
            "pt": "finite_grid_need",
            "pf": "finite_grid_need",
            "pe": "exogenous_grid_infeasibility",
        },
        "solver_specification": _solver(),
    }
    monkeypatch.setattr(pairwise, "_preflight", lambda _path: (config, context))
    monkeypatch.setattr(
        pairwise,
        "plan_minimum_flexibility_pair_with_spec",
        lambda *_args, **_kwargs: MinimumFlexibilityPolicyPairSuccessor(
            correct=_capacity(True, 0.2),
            b6=_capacity(False, 0.1),
        ),
    )
    monkeypatch.setattr(
        pairwise,
        "audit_training_support",
        lambda *_args, **_kwargs: (
            TrainingSupportAudit("correct", 1, ()),
            TrainingSupportAudit("b6", 1, ()),
        ),
    )
    monkeypatch.setattr(
        pairwise,
        "execute_causal_grid_first_policy",
        lambda scenario, _envelope, committed, **_kwargs: _outcome(
            scenario.name,
            committed,
        ),
    )
    monkeypatch.setattr(
        pairwise,
        "require_execution_host",
        lambda _execution: None,
    )

    summary = pairwise.run(config_path)

    assert summary["holdout_exogenous_grid_infeasibility_probability_mass"] == 0.5
    assert summary["exogenous_grid_infeasibility_pair_count"] == 1
    with gzip.open(
        tmp_path / "output/pairwise_outcomes.csv.gz",
        "rt",
        encoding="utf-8",
        newline="",
    ) as source:
        rows = list(csv.DictReader(source))
    e0 = next(row for row in rows if row["row_id"] == "pe")
    assert e0["outcome_status"] == "exogenous_grid_infeasibility"
    assert e0["flexibility_underprovisioning"] == ""
    assert e0["correct_failure"] == ""


def _write_gzip(
    path: Path,
    fields: tuple[str, ...],
    rows: list[dict[str, object]],
) -> None:
    with (
        path.open("wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed,
        io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text,
    ):
        writer = csv.DictWriter(text, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_identification_v4_conditions_transport_on_finite_grid_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    package = tmp_path / "pairwise"
    package.mkdir()
    _write_gzip(
        package / "power_system_holdout_marginal.csv.gz",
        ("id", "probability", "stress_score", "grid_evaluation_state"),
        [
            {
                "id": "pf",
                "probability": 0.5,
                "stress_score": 0.0,
                "grid_evaluation_state": "finite_grid_need",
            },
            {
                "id": "pe",
                "probability": 0.5,
                "stress_score": 1.0,
                "grid_evaluation_state": "exogenous_grid_infeasibility",
            },
        ],
    )
    _write_gzip(
        package / "workload_holdout_marginal.csv.gz",
        ("id", "probability", "stress_score", "grid_evaluation_state"),
        [
            {
                "id": "w0",
                "probability": 0.5,
                "stress_score": 0.0,
                "grid_evaluation_state": "",
            },
            {
                "id": "w1",
                "probability": 0.5,
                "stress_score": 1.0,
                "grid_evaluation_state": "",
            },
        ],
    )
    status = {
        "cell_id": "base",
        "varied_dimension": "base",
        "training_resolved": True,
        "correct_training_feasible": True,
        "correct_training_proven_infeasible": False,
        "b6_training_feasible": True,
        "b6_training_proven_infeasible": False,
        "pairwise_eligible": True,
        "pair_count_expected": 4,
        "pair_count_completed": 4,
        "all_pairwise_outcomes_resolved": True,
        "full_training_support_passed": True,
        "full_training_support_pair_count": 1,
        "full_training_support_failure_count": 0,
    }
    _write_gzip(
        package / "cell_status.csv.gz",
        identification._CELL_STATUS_FIELDS,
        [status],
    )
    policies = [
        pairwise._capacity_row(
            _cell(),
            variant,
            _capacity(variant == "correct", capacity),
        )
        for variant, capacity in (("correct", 0.2), ("b6", 0.1))
    ]
    _write_gzip(
        package / "policy_table.csv.gz",
        identification._POLICY_FIELDS,
        policies,
    )
    rows = []
    for power in ("pf", "pe"):
        for workload in ("w0", "w1"):
            if power == "pe":
                row = {field: "" for field in identification._PAIR_FIELDS}
                row.update(
                    {
                        "cell_id": "base",
                        "row_id": power,
                        "column_id": workload,
                        "outcome_resolved": True,
                        "outcome_status": "exogenous_grid_infeasibility",
                        "correct_flexibility_capacity": 0.2,
                        "b6_flexibility_capacity": 0.1,
                        "correct_solver_unresolved": False,
                        "b6_solver_unresolved": False,
                    }
                )
            else:
                conflict = workload == "w1"
                row = {
                    "cell_id": "base",
                    "row_id": power,
                    "column_id": workload,
                    "outcome_resolved": True,
                    "outcome_status": "finite_grid_need",
                    "correct_flexibility_capacity": 0.2,
                    "b6_flexibility_capacity": 0.1,
                    "flexibility_underprovisioning": 0.1,
                    "correct_failure": False,
                    "b6_failure": conflict,
                    "correct_shortfall": 0.0,
                    "b6_shortfall": float(conflict),
                    "correct_peak_debt": 0.0,
                    "b6_peak_debt": 0.0,
                    "correct_terminal_debt": 0.0,
                    "b6_terminal_debt": 0.0,
                    "correct_hard_temporal_failure": False,
                    "b6_hard_temporal_failure": False,
                    "correct_physical_policy_failure": False,
                    "b6_physical_policy_failure": False,
                    "correct_service_failure": False,
                    "b6_service_failure": conflict,
                    "correct_solver_unresolved": False,
                    "b6_solver_unresolved": False,
                }
            rows.append(row)
    _write_gzip(
        package / "pairwise_outcomes.csv.gz",
        identification._PAIR_FIELDS,
        rows,
    )
    config = {
        "input": {
            "pairwise_replay_ready": True,
            "pairwise_replay_manifest_sha256": "5" * 64,
            "expected_parameter_cells": 1,
            "expected_solver_name": "highs",
        },
        "classification": {
            "probability_tolerance": 1.0e-9,
            "outcome_tolerance": 1.0e-6,
        },
        "sampling_uncertainty": {
            "enabled": True,
            "bootstrap_replicates": 10,
            "seed": 7,
            "confidence_level": 0.9,
        },
        "execution": {
            "formal_execution_ready": True,
            "independent_R4_review_passed": True,
            "user_formal_run_authorized": True,
        },
        "output": {
            "schema": "test_identification_v4",
            "directory": str(tmp_path / "output"),
        },
    }
    config_path = tmp_path / "identification.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setattr(
        identification,
        "_preflight",
        lambda _path: (
            config,
            {
                "package": package,
                "summary": {
                    "all_eligible_pairwise_outcomes_resolved": True
                },
                "contract_identity": _contract(),
                "pairwise_provenance_sha256": "4" * 64,
            },
        ),
    )
    monkeypatch.setattr(
        identification,
        "require_execution_host",
        lambda _execution: None,
    )

    summary = identification.run(config_path)

    assert summary["holdout_exogenous_grid_infeasibility_probability_mass"] == 0.5
    assert summary["contract_risk_conditioning_probability_mass"] == 0.5
    assert summary["transport_identified_cell_count"] == 1
    assert summary["bootstrap_replicates"] == 10
