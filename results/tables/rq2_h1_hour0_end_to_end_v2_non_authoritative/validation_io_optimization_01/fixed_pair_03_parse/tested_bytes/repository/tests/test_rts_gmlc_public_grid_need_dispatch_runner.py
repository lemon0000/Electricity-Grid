from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path

import pytest
import yaml

import experiments.run_rts_gmlc_public_grid_need_dispatch as runner


def _row(block_id: str, split: str, hour: int) -> dict[str, str]:
    return {
        "block_id": block_id,
        "split": split,
        "block_probability": "1",
        "outage_seed": "7",
        "hour_offset": "0",
        "source_hour": str(hour),
        "timestamp": f"2020-01-01T{hour:02d}:00:00+00:00",
        "system_load_mw": "1000",
        "cfe_call_fraction": "0.25",
        "active_event_id": "",
        "active_component_type": "",
        "active_component_uid": "",
    }


def _config(tmp_path: Path, *, require_all: bool = True) -> tuple[Path, dict]:
    config = {
        "input": {
            "power_system_blocks_manifest_sha256": "a" * 64,
        },
        "execution": {
            "formal_execution_ready": True,
            "independent_R4_review_passed": True,
            "user_formal_run_authorized": True,
            "require_all_blocks_resolved": require_all,
            "checkpoint_directory": str(tmp_path / "checkpoints"),
        },
        "model": {
            "dc_bus": 108,
            "dc_reference_demand_mw": 250.0,
        },
        "solver": {"name": "highs"},
        "grid_source": {"base_mva": 100.0},
        "output": {
            "schema": "test_grid_need_dispatch",
            "directory": str(tmp_path / "output"),
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path, config


def _fake_preflight(config: dict):
    blocks = {
        "training_s7_0000": [_row("training_s7_0000", "training", 0)],
        "holdout_s7_0000": [_row("holdout_s7_0000", "holdout", 1)],
    }
    marginals = {
        "training": [{"id": "training_s7_0000", "probability": "1"}],
        "holdout": [{"id": "holdout_s7_0000", "probability": "1"}],
    }
    return config, Path("."), blocks, marginals


def _fake_result(block: list[dict[str, str]], *, resolved: bool = True):
    row = block[0]
    return {
        "block_id": row["block_id"],
        "split": row["split"],
        "baseline_audit": {"accepted": True},
        "all_hours_resolved": resolved,
        "outcomes": [],
        "rows": [
            {
                **row,
                "grid_need_mw": 0,
                "grid_need_fraction": 0,
                "dispatch_resolved": str(resolved).lower(),
                "dispatch_proven_infeasible": "false",
                "dispatch_termination_condition": (
                    "optimal" if resolved else "unknown"
                ),
                "dispatch_solver_status": "ok",
                "maximum_constraint_violation": 0,
            }
        ],
    }


def test_production_preflight_keeps_formal_execution_closed():
    result = runner.run(
        Path("configs/rts_gmlc_public_grid_need_dispatch_v1.yaml"),
        validate_only=True,
    )

    assert result["power_system_block_count"] == 1071
    assert result["training_block_count"] == 541
    assert result["holdout_block_count"] == 530
    assert not result["formal_execution_ready"]
    assert not result["independent_R4_review_passed"]
    assert not result["user_formal_run_authorized"]


def test_checkpoint_resume_and_atomic_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    config_path, config = _config(tmp_path)
    monkeypatch.setattr(runner, "_preflight", lambda _path: _fake_preflight(config))
    monkeypatch.setattr(
        runner,
        "load_rts_gmlc_chronological_data",
        lambda *_args, **_kwargs: object(),
    )
    calls = []

    def process(_data, block, **_kwargs):
        calls.append(block[0]["block_id"])
        return _fake_result(block)

    monkeypatch.setattr(runner, "_process_block", process)
    progress = runner.run(config_path, maximum_blocks=1)
    assert not progress["formal_result_published"]
    assert len(calls) == 1

    summary = runner.run(config_path)
    assert summary["all_blocks_resolved"]
    assert len(calls) == 2
    output = tmp_path / "output"
    with gzip.open(
        output / "dispatched_power_system_blocks.csv.gz",
        "rt",
        encoding="utf-8",
        newline="",
    ) as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == 2
    manifest = json.loads(
        (output / "SHA256SUMS.json").read_text(encoding="utf-8")
    )
    assert set(manifest) == {
        "block_status.csv.gz",
        "dispatched_power_system_blocks.csv.gz",
        "holdout_marginal.csv.gz",
        "summary.json",
        "training_marginal.csv.gz",
    }


def test_unresolved_block_prevents_formal_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    config_path, config = _config(tmp_path)
    monkeypatch.setattr(runner, "_preflight", lambda _path: _fake_preflight(config))
    monkeypatch.setattr(
        runner,
        "load_rts_gmlc_chronological_data",
        lambda *_args, **_kwargs: object(),
    )
    monkeypatch.setattr(
        runner,
        "_process_block",
        lambda _data, block, **_kwargs: _fake_result(block, resolved=False),
    )

    with pytest.raises(RuntimeError, match="remains unresolved"):
        runner.run(config_path)
    assert not (tmp_path / "output").exists()


def test_execution_requires_both_formal_gates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    config_path, config = _config(tmp_path)
    config["execution"]["user_formal_run_authorized"] = False
    monkeypatch.setattr(runner, "_preflight", lambda _path: _fake_preflight(config))

    with pytest.raises(ValueError, match="must all be true"):
        runner.run(config_path)
