from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import experiments.validate_rq2_public_executor_environment_successor_v1 as validator
from experiments.validate_rq2_public_executor_environment_successor_v1 import (
    validate,
    validate_environment_spec,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_executor_environment_successor_v1.yaml"
V1 = ROOT / "environments/rq2_executor_v1.yml"
V2 = ROOT / "environments/rq2_executor_v2.yml"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v1_reproduces_unregistered_entry_import_dependencies():
    with pytest.raises(ValueError, match="pip direct dependency inventory drifted"):
        validate_environment_spec(V1)


def test_environment_successor_registers_exact_direct_dependencies():
    report = validate_environment_spec(V2)
    assert report["missing_v1_entry_import_packages_registered"] == [
        "osqp",
        "pypower",
    ]
    assert report["pip_direct_packages"] == {
        "gurobipy": "13.0.2",
        "osqp": "1.0.5",
        "pypower": "5.1.19",
        "ruff": "0.16.4",
    }


def test_entrypoint_import_temporarily_bootstraps_repository_root(monkeypatch):
    root = str(ROOT)
    original_path = list(sys.path)
    sys.path[:] = [entry for entry in sys.path if entry != root]
    observed: dict[str, object] = {}

    def _capture_import(name: str):
        observed["name"] = name
        observed["root_at_front"] = sys.path[0] == root
        return SimpleNamespace(__file__=ROOT / "scripts/rq2_public_executor.py")

    monkeypatch.setattr(validator.importlib, "import_module", _capture_import)
    try:
        validator._import_executor_entrypoint()
        observed["root_removed"] = root not in sys.path
    finally:
        sys.path[:] = original_path

    assert observed == {
        "name": "scripts.rq2_public_executor",
        "root_at_front": True,
        "root_removed": True,
    }


def test_entrypoint_import_promotes_existing_root_and_restores_path(monkeypatch):
    root = str(ROOT)
    original_path = ["UNTRUSTED_FIRST", root, "AFTER_ROOT"]
    sys.path[:] = original_path

    def _capture_import(_name: str):
        assert sys.path == [root, "UNTRUSTED_FIRST", "AFTER_ROOT"]
        return SimpleNamespace(__file__=ROOT / "scripts/rq2_public_executor.py")

    monkeypatch.setattr(validator.importlib, "import_module", _capture_import)
    validator._import_executor_entrypoint()
    assert sys.path == original_path


def test_entrypoint_import_rejects_wrong_module_and_restores_path(
    monkeypatch,
):
    original_path = list(sys.path)
    monkeypatch.setattr(
        validator.importlib,
        "import_module",
        lambda _name: SimpleNamespace(__file__=ROOT / "wrong.py"),
    )
    with pytest.raises(RuntimeError, match="not the frozen file"):
        validator._import_executor_entrypoint()
    assert sys.path == original_path


@pytest.mark.parametrize(
    ("section", "key", "value", "message"),
    [
        (None, "status", "ready", "status drifted"),
        (
            "observed_failure",
            "mathematical_infeasibility_evidence",
            True,
            "failure semantics drifted",
        ),
        ("successor", "runtime_validation_solver_calls", 1, "authority drifted"),
        ("successor", "manifest_path", "wrong.json", "authority drifted"),
        ("gates", "formal_execution_ready", True, "gates drifted"),
    ],
)
def test_environment_successor_rejects_safety_field_tampering(
    tmp_path,
    section,
    key,
    value,
    message,
):
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    target = config if section is None else config[section]
    target[key] = value
    tampered = tmp_path / "tampered.yaml"
    tampered.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        validate(tampered)


def test_environment_successor_preserves_frozen_authority_and_gates():
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert config["predecessor"]["immutable"] is True
    for relative, expected in config["predecessor"]["files"].items():
        assert _sha256(ROOT / relative) == expected
    assert config["successor"]["environment_spec_sha256"] == _sha256(V2)
    assert config["successor"]["scientific_design_changed"] is False
    assert config["successor"]["solver_or_algorithm_changed"] is False
    assert config["successor"]["threads_seed_or_thresholds_changed"] is False
    assert config["gates"] == {
        "environment_successor_runtime_validated": False,
        "runtime_receipt_published": False,
        "pilot_executed": False,
        "cross_solver_confirmation_completed": False,
        "formal_execution_ready": False,
        "formal_result_exists": False,
        "security_certified": False,
    }


def test_environment_successor_static_validator_is_solver_free():
    report = validate()
    assert report["validation_passed"] is True
    assert report["runtime_checked"] is False
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["pilot_executed"] is False
    assert report["formal_execution_started"] is False
