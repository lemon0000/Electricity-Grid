from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest
import yaml

import experiments.run_rq2_public_pairwise_replay_v3 as runner
from src.models.temporal_flexibility_capacity import (
    MinimumFlexibilityCapacity,
    MinimumFlexibilityPolicyPair,
)
from src.scenarios.rq2_public_replay import (
    CausalPolicyOutcome,
    ParameterCell,
    TemporalBlock,
)


def _config(tmp_path: Path) -> tuple[Path, dict]:
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
            "minimum_event_power": 1.0e-6,
            "response_time_hours": 1.0,
            "curtailment_ramp_per_hour": 1.0,
            "service_shortfall_tolerance": 1.0e-6,
        },
        "solver": {
            "name": "highs",
            "expected_highspy_version": "1.15.1",
            "expected_pyomo_version": "6.10.1",
            "tee": False,
        },
        "execution": {
            "formal_execution_ready": True,
            "independent_R4_review_passed": True,
            "user_formal_run_authorized": True,
            "require_all_training_plans_resolved": True,
            "require_all_pairwise_outcomes_resolved": True,
            "checkpoint_directory": str(tmp_path / "checkpoints"),
        },
        "output": {
            "schema": "test_pairwise_replay_v3",
            "directory": str(tmp_path / "output"),
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path, config


def _block(
    block_id: str,
    split: str,
    *,
    power: bool,
) -> TemporalBlock:
    return TemporalBlock(
        block_id=block_id,
        split=split,
        probability=1.0,
        first_source_hour=0,
        grid_need=(0.0,) if power else (),
        cfe_call=(0.1,) if power else (),
        workload=() if power else (1.0,),
    )


def _cell() -> ParameterCell:
    return ParameterCell(
        cell_id="base",
        varied_dimension="base",
        flexible_fraction=0.2,
        recovery_efficiency=1.0,
        normalized_recovery_headroom=0.0,
        maximum_event_duration_hours=1.0,
        maximum_event_count=1,
        normalized_energy_budget=1.0,
        normalized_debt_limit=1.0,
    )


def _contract_identity(module_sha: str = "2" * 64) -> dict[str, object]:
    return {
        "contract_path": "configs/test_contract_v2.yaml",
        "contract_sha256": "1" * 64,
        "implementation": {
            "runner_sha256": "0" * 64,
            "module_sha256": {"public_replay": module_sha},
        },
        "software": {"highspy": "1.15.1", "pyomo": "6.10.1"},
    }


def _context(
    config: dict,
    *,
    module_sha: str = "2" * 64,
) -> tuple[dict, dict[str, object]]:
    return config, {
        "report": {"schema": "test_preflight"},
        "power_training": (_block("pt", "training", power=True),),
        "power_holdout": (_block("ph", "holdout", power=True),),
        "workload_training": (_block("wt", "training", power=False),),
        "workload_holdout": (_block("wh", "holdout", power=False),),
        "cells": (_cell(),),
        "contract_identity": _contract_identity(module_sha),
        "power_provenance_sha256": "f" * 64,
    }


def _capacity(joint: bool, value: float) -> MinimumFlexibilityCapacity:
    return MinimumFlexibilityCapacity(
        enforce_joint_budget=joint,
        feasible=True,
        proven_infeasible=False,
        minimum_capacity=value,
        termination_condition="optimal",
        solver_status="ok",
        maximum_residual=0.0,
    )


def _outcome(
    name: str,
    committed: float,
    *,
    resolved: bool = True,
) -> CausalPolicyOutcome:
    return CausalPolicyOutcome(
        name=name,
        committed_flexibility=committed,
        resolved=resolved,
        hard_grid_failure=False,
        physical_policy_failure=False,
        service_shortfall_failure=False,
        access_shortfall=0.0,
        peak_recovery_debt=0.0,
        terminal_recovery_debt=0.0,
        combined_call=(0.0,),
        green_served=(0.0,),
        physical_violations=(),
    )


def test_production_preflight_keeps_replay_closed():
    successor = runner.run(
        Path("configs/rq2_public_pairwise_replay_v3.yaml"),
        validate_only=True,
    )

    assert successor["parameter_cells"] == 15
    assert successor["workload_training_blocks"] == 34
    assert successor["workload_holdout_blocks"] == 34
    assert not successor["grid_need_dispatch_ready"]
    assert not successor["formal_execution_ready"]
    assert not successor["independent_R4_review_passed"]


def test_checkpoint_resume_and_atomic_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    config_path, config = _config(tmp_path)
    monkeypatch.setattr(runner, "_preflight", lambda _path: _context(config))
    monkeypatch.setattr(
        runner,
        "plan_minimum_flexibility_pair",
        lambda *_args, **_kwargs: MinimumFlexibilityPolicyPair(
            correct=_capacity(True, 0.2),
            b6=_capacity(False, 0.1),
        ),
    )
    calls = []

    def execute(scenario, _envelope, committed, **_kwargs):
        calls.append(committed)
        return _outcome(scenario.name, committed)

    monkeypatch.setattr(runner, "execute_causal_grid_first_policy", execute)

    progress = runner.run(config_path, maximum_pairs=1)
    assert not progress["formal_result_published"]
    assert len(calls) == 2

    summary = runner.run(config_path)
    assert summary["complete_cartesian_for_every_registered_cell"]
    assert len(calls) == 2
    output = tmp_path / "output"
    with gzip.open(
        output / "pairwise_outcomes.csv.gz",
        "rt",
        encoding="utf-8",
    ) as source:
        assert len(source.readlines()) == 2
    manifest = json.loads(
        (output / "SHA256SUMS.json").read_text(encoding="utf-8")
    )
    assert set(manifest) == {
        "cell_status.csv.gz",
        "checkpoint_inventory.json",
        "pairwise_outcomes.csv.gz",
        "policy_table.csv.gz",
        "power_system_holdout_marginal.csv.gz",
        "provenance.json",
        "summary.json",
        "workload_holdout_marginal.csv.gz",
    }


def test_unresolved_pair_prevents_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    config_path, config = _config(tmp_path)
    monkeypatch.setattr(runner, "_preflight", lambda _path: _context(config))
    monkeypatch.setattr(
        runner,
        "plan_minimum_flexibility_pair",
        lambda *_args, **_kwargs: MinimumFlexibilityPolicyPair(
            correct=_capacity(True, 0.2),
            b6=_capacity(False, 0.1),
        ),
    )
    monkeypatch.setattr(
        runner,
        "execute_causal_grid_first_policy",
        lambda scenario, _envelope, committed, **_kwargs: _outcome(
            scenario.name,
            committed,
            resolved=False,
        ),
    )

    with pytest.raises(RuntimeError, match="pairwise outcome remains unresolved"):
        runner.run(config_path)
    assert not (tmp_path / "output").exists()


def test_pair_checkpoint_is_bound_to_the_frozen_policy_capacity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    config_path, config = _config(tmp_path)
    monkeypatch.setattr(runner, "_preflight", lambda _path: _context(config))
    capacities = {"correct": 0.2}
    monkeypatch.setattr(
        runner,
        "plan_minimum_flexibility_pair",
        lambda *_args, **_kwargs: MinimumFlexibilityPolicyPair(
            correct=_capacity(True, capacities["correct"]),
            b6=_capacity(False, 0.1),
        ),
    )
    monkeypatch.setattr(
        runner,
        "execute_causal_grid_first_policy",
        lambda scenario, _envelope, committed, **_kwargs: _outcome(
            scenario.name,
            committed,
        ),
    )
    runner.run(config_path, maximum_pairs=1)
    policy_checkpoint = (
        tmp_path / "checkpoints" / "policies" / "base.json"
    )
    policy_checkpoint.unlink()
    capacities["correct"] = 0.3

    with pytest.raises(ValueError, match="checkpoint identity drifted"):
        runner.run(config_path)


def test_policy_checkpoint_rejects_module_identity_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    config_path, config = _config(tmp_path)
    module_sha = {"value": "2" * 64}
    monkeypatch.setattr(
        runner,
        "_preflight",
        lambda _path: _context(config, module_sha=module_sha["value"]),
    )
    monkeypatch.setattr(
        runner,
        "plan_minimum_flexibility_pair",
        lambda *_args, **_kwargs: MinimumFlexibilityPolicyPair(
            correct=_capacity(True, 0.2),
            b6=_capacity(False, 0.1),
        ),
    )
    monkeypatch.setattr(
        runner,
        "execute_causal_grid_first_policy",
        lambda scenario, _envelope, committed, **_kwargs: _outcome(
            scenario.name,
            committed,
        ),
    )

    runner.run(config_path, maximum_pairs=1)
    module_sha["value"] = "3" * 64

    with pytest.raises(ValueError, match="checkpoint identity drifted"):
        runner.run(config_path)


def test_execution_requires_all_formal_gates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    config_path, config = _config(tmp_path)
    config["execution"]["user_formal_run_authorized"] = False
    monkeypatch.setattr(runner, "_preflight", lambda _path: _context(config))

    with pytest.raises(ValueError, match="must all be true"):
        runner.run(config_path)
