from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from experiments import activate_rq2_public_grid_v2 as activator
from experiments import validate_rq2_public_grid_activation_v2 as validator


def test_grid_activation_v2_is_read_only_and_binds_pilot() -> None:
    report = validator.validate()
    assert report["validation_passed"] is True
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["pilot_result_manifest_sha256"] == (
        "70003e18566c208631768dd028d573cd0c5e45d4f8fb0e7104ec1f1158d98a58"
    )
    assert len(report["activation_subject_sha256"]) == 64
    assert len(report["grid_activation_review_sha256"]) == 64


def test_grid_activation_review_rejects_config_subject_drift() -> None:
    config = yaml.safe_load(
        Path("configs/rq2_public_grid_need_activation_v2.yaml").read_text(
            encoding="utf-8"
        )
    )
    mutated = deepcopy(config)
    mutated["execution"]["require_all_blocks_resolved"] = False
    with pytest.raises(ValueError, match="subject drifted"):
        validator._verify_grid_review_receipt(
            mutated,
            mutated["frozen_scientific_authority"],
            mutated["grid_stage"],
        )


def test_grid_activation_refuses_preexisting_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    template = yaml.safe_load(
        Path("configs/rts_gmlc_public_grid_need_dispatch_v4.yaml").read_text(encoding="utf-8")
    )
    original = validator.CONFIG
    assert original.exists()
    output = tmp_path / "output"
    output.mkdir()
    monkeypatch.setattr(activator, "ACTIVATED_ROOT", tmp_path / "activated")
    monkeypatch.setattr(activator, "validate", lambda: {"validation_passed": True})
    def fake_path(raw: object, label: str) -> Path:
        if label == "output directory":
            return output
        if label == "checkpoint directory":
            return tmp_path / "checkpoint"
        return activator.ROOT / Path(str(raw))

    monkeypatch.setattr(activator, "_path", fake_path)
    with pytest.raises(FileExistsError):
        activator.activate()
    assert template["execution"]["formal_execution_ready"] is False


def _isolated_activation_paths(tmp_path: Path):
    root = tmp_path / "activated"
    checkpoint = tmp_path / "checkpoints"
    output = tmp_path / "output"

    def fake_path(raw: object, label: str) -> Path:
        if label == "checkpoint directory":
            return checkpoint
        if label == "output directory":
            return output
        if label == "activated grid config":
            return root / "grid.yaml"
        if label == "grid activation record":
            return root / "grid.activation.json"
        return activator.ROOT / Path(str(raw))

    return root, fake_path


def test_grid_activation_materializes_and_records_runner_validation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root, fake_path = _isolated_activation_paths(tmp_path)
    monkeypatch.setattr(activator, "ACTIVATED_ROOT", root)
    monkeypatch.setattr(activator, "_path", fake_path)
    monkeypatch.setattr(
        activator,
        "validate",
        lambda: {"activation_subject_sha256": "a" * 64},
    )

    def fake_runner(path: Path, *, validate_only: bool) -> dict[str, object]:
        assert validate_only is True
        return {
            "config_sha256": activator._sha256(path),
            "formal_execution_ready": True,
            "independent_R4_review_passed": True,
            "user_formal_run_authorized": True,
            "power_system_block_count": 1071,
        }

    monkeypatch.setattr(activator, "run_grid", fake_runner)
    record = activator.activate()
    target = root / "grid.yaml"
    record_target = root / "grid.activation.json"
    activated = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert activated["execution"]["formal_execution_ready"] is True
    assert activated["execution"]["independent_R4_review_passed"] is True
    assert activated["execution"]["predecessor_HiGHS_checkpoint_reuse_allowed"] is False
    assert activated["activation_authority"]["grid_activation_review_sha256"] == (
        validator._load_yaml(
            Path("configs/rq2_public_grid_need_activation_v2.yaml"), "activation"
        )["grid_activation_review"]["receipt_sha256"]
    )
    stored_record = json.loads(record_target.read_text(encoding="utf-8"))
    assert stored_record == record
    assert stored_record["activated_config_sha256"] == activator._sha256(target)
    assert stored_record["runner_validate_only"]["power_system_block_count"] == 1071


def test_grid_activation_removes_config_if_record_publication_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root, fake_path = _isolated_activation_paths(tmp_path)
    monkeypatch.setattr(activator, "ACTIVATED_ROOT", root)
    monkeypatch.setattr(activator, "_path", fake_path)
    monkeypatch.setattr(
        activator,
        "validate",
        lambda: {"activation_subject_sha256": "a" * 64},
    )
    monkeypatch.setattr(
        activator,
        "run_grid",
        lambda path, *, validate_only: {
            "config_sha256": activator._sha256(path),
            "formal_execution_ready": True,
            "independent_R4_review_passed": True,
            "user_formal_run_authorized": True,
            "power_system_block_count": 1071,
        },
    )

    def fail_record(*args, **kwargs):
        raise OSError("injected record publication failure")

    monkeypatch.setattr(activator, "_write_atomic", fail_record)
    with pytest.raises(OSError, match="injected"):
        activator.activate()
    assert not (root / "grid.yaml").exists()
    assert not (root / "grid.activation.json").exists()
