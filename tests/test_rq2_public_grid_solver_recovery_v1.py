from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from experiments import activate_rq2_public_grid_solver_recovery_v1 as activator
from experiments import validate_rq2_public_grid_solver_recovery_v1 as validator


def _contracts() -> tuple[dict, dict, dict]:
    contract = yaml.safe_load(validator.CONTRACT.read_text(encoding="utf-8"))
    predecessor = yaml.safe_load(
        Path(contract["predecessor"]["activated_config_path"]).read_text(
            encoding="utf-8"
        )
    )
    template = yaml.safe_load(
        Path(contract["successor"]["template_path"]).read_text(encoding="utf-8")
    )
    return contract, predecessor, template


def test_solver_recovery_candidate_is_read_only_and_accepted() -> None:
    report = validator.validate()
    assert report["validation_passed"] is True
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["predecessor_checkpoint_count"] == 9
    assert report["accepted_blocks"] == [
        "holdout_s20260822_0008",
        "holdout_s20260822_0009",
    ]
    assert report["target_block_accepted"] is True
    assert report["starts_from_block_zero"] is True
    assert report["formal_execution_ready"] is False


def test_solver_recovery_rejects_gap_drift() -> None:
    contract, predecessor, template = _contracts()
    mutated = deepcopy(template)
    mutated["solver"]["mip_relative_gap"] = 1e-5
    with pytest.raises(ValueError, match="mip_relative_gap"):
        validator._verify_successor_template(
            contract["successor"], predecessor, mutated
        )


def test_solver_recovery_rejects_model_drift() -> None:
    contract, predecessor, template = _contracts()
    mutated = deepcopy(template)
    mutated["model"]["load_shedding_allowed"] = True
    with pytest.raises(ValueError, match="model drifted"):
        validator._verify_successor_template(
            contract["successor"], predecessor, mutated
        )


def test_solver_recovery_rejects_preexisting_target(tmp_path: Path) -> None:
    contract, _, _ = _contracts()
    successor = deepcopy(contract["successor"])
    successor["checkpoint_directory"] = "new/checkpoints"
    successor["output_directory"] = "new/output"
    successor["activated_config_path"] = "new/activation/grid.yaml"
    successor["activation_record_path"] = "new/activation/grid.activation.json"
    (tmp_path / "new/checkpoints").mkdir(parents=True)
    with pytest.raises(ValueError, match="checkpoint_directory"):
        validator._verify_fresh_targets(successor, root=tmp_path)


def test_solver_recovery_rejects_diagnostic_hash_drift() -> None:
    contract, _, _ = _contracts()
    mutated = deepcopy(contract["root_cause_evidence"])
    mutated["default_gurobi_summary_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="drifted"):
        validator._verify_root_cause_evidence(mutated)


def _isolated_activation_paths(tmp_path: Path):
    root = tmp_path / "activated"
    checkpoint = tmp_path / "checkpoint"
    output = tmp_path / "output"

    def fake_repo_path(raw: object, label: str) -> Path:
        if label == "checkpoint directory":
            return checkpoint
        if label == "output directory":
            return output
        if label == "activated config":
            return root / "grid.yaml"
        if label == "activation record":
            return root / "grid.activation.json"
        return activator.ROOT / Path(str(raw))

    return root, checkpoint, output, fake_repo_path


def test_recovery_activation_materializes_reviewed_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root, _, _, fake_repo_path = _isolated_activation_paths(tmp_path)
    monkeypatch.setattr(activator, "ACTIVATED_ROOT", root)
    monkeypatch.setattr(activator, "_repo_path", fake_repo_path)
    monkeypatch.setattr(
        activator,
        "validate",
        lambda: {
            "validation_passed": True,
            "formal_execution_ready": False,
        },
    )
    monkeypatch.setattr(
        activator,
        "_verify_review_receipt",
        lambda contract: {"verdict": "PASS"},
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
    monkeypatch.setattr(activator, "REVIEW", Path(__file__))
    record = activator.activate()
    target = root / "grid.yaml"
    activated = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert activated["execution"]["formal_execution_ready"] is True
    assert activated["execution"]["independent_R4_review_passed"] is True
    assert activated["solver"]["name"] == "highs"
    assert activated["solver"]["mip_relative_gap"] == 1e-6
    assert record["starts_from_block_zero"] is True
    assert record["predecessor_checkpoint_reuse_allowed"] is False
    assert record["formal_result_exists"] is False


def test_recovery_activation_refuses_preexisting_checkpoint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root, checkpoint, _, fake_repo_path = _isolated_activation_paths(tmp_path)
    checkpoint.mkdir()
    monkeypatch.setattr(activator, "ACTIVATED_ROOT", root)
    monkeypatch.setattr(activator, "_repo_path", fake_repo_path)
    monkeypatch.setattr(activator, "validate", dict)
    monkeypatch.setattr(
        activator,
        "_verify_review_receipt",
        lambda contract: {"verdict": "PASS"},
    )
    with pytest.raises(FileExistsError, match="checkpoint/output"):
        activator.activate()


def test_recovery_activation_cleans_partial_publication(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root, _, _, fake_repo_path = _isolated_activation_paths(tmp_path)
    monkeypatch.setattr(activator, "ACTIVATED_ROOT", root)
    monkeypatch.setattr(activator, "_repo_path", fake_repo_path)
    monkeypatch.setattr(activator, "validate", dict)
    monkeypatch.setattr(
        activator,
        "_verify_review_receipt",
        lambda contract: {"verdict": "PASS"},
    )
    monkeypatch.setattr(activator, "REVIEW", Path(__file__))
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

    def fail_record(path: Path, payload: object) -> None:
        raise OSError("injected record failure")

    monkeypatch.setattr(activator, "_write_json_atomic", fail_record)
    with pytest.raises(OSError, match="injected"):
        activator.activate()
    assert not root.exists()
