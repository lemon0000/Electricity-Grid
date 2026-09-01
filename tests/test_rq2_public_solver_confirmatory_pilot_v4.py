from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from experiments import run_rq2_public_solver_confirmatory_pilot_v4 as runner
from experiments import validate_rq2_public_solver_confirmatory_pilot_v4 as validator

ROOT = Path(__file__).resolve().parents[1]


def _config() -> dict[str, object]:
    return yaml.safe_load(runner.CONFIG.read_text(encoding="utf-8"))


def test_v4_validate_only_is_closed_to_solver_and_result_writes(monkeypatch: pytest.MonkeyPatch):
    assert not validator.RESULT.exists()
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *a, **k: pytest.fail("solver dispatch"))
    report = runner.run(validate_only=True)
    assert report["validation_passed"] is True
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["execution_ready"] is True
    assert report["confirmatory_pilot_executed"] is False


def test_v4_binds_exact_v3_artifacts_and_pass_receipt():
    config = _config()
    assert validator._artifact_map(
        {k: v for k, v in config["v3_predecessor_authority"].items() if k != "immutable"},
        "v3 predecessor",
    ) == validator.V3_HASHES
    assert config["pass_review_receipt"]["verdict"] == "PASS"
    validator._validate_pass_review(config)
    assert config["gates"]["confirmatory_execution_ready"] is True
    assert config["gates"]["formal_execution_ready"] is False


def test_v4_is_execution_successor_and_does_not_require_v5():
    contract = _config()["execution_successor_contract"]
    assert contract["current_v4_is_execution_successor"] is True
    assert contract["opens_only_confirmatory_execution_gate"] is True
    assert contract["no_future_successor_required_for_validation"] is True
    assert "future_successor_version" not in contract
    runner._require_execution_gate(_config())


def test_v4_scientific_inheritance_is_frozen():
    inherited = _config()["scientific_inheritance"]
    assert inherited["execution_order"] == ["highs_r1", "gurobi_r1", "gurobi_r2", "highs_r2"]
    assert inherited["repetitions"] == 2
    assert inherited["external_watchdog_seconds"] == 21600
    assert inherited["solver_time_limit_seconds"] is None
    assert inherited["solver_threads"] == 4
    assert inherited["solver_random_seed"] == 0
    assert inherited["scientific_threshold_values_changed"] is False


def test_v4_controller_report_reconstruction_rejects_nested_forgery(tmp_path: Path):
    controller = {
        "controller_pid": 101,
        "controller_started_ns": 200,
        "controller_nonce": "a" * 64,
        "receipt_sha256": "c" * 64,
        "v3_outer_sha256": runner.V3_OUTER_SHA256,
        "config_sha256": "d" * 64,
        "runner_sha256": "e" * 64,
        "semantic_authority_sha256": "f" * 64,
    }
    controller["controller_identity_sha256"] = runner._controller_identity(controller)
    payload = {
        **runner._expected_payload_fields("highs_r1", controller),
        "worker_pid": 303,
        "run": {"run_id": "highs_r1", "solver_name": "highs", "repetition": 1, "blocks": []},
    }
    expected = runner.build_expected_worker_report(
        run_id="highs_r1", payload=payload, controller=controller,
        payload_sha256="b" * 64, observed_worker_pid=303, observed_returncode=0,
    )
    forged = copy.deepcopy(expected)
    forged["run_id"] = "gurobi_r1"
    assert forged != expected
    assert expected["run_id"] == "highs_r1"


def test_v4_manifest_inventory_has_only_new_successor_members():
    assert validator.BUNDLE_INVENTORY == {
        validator.CONFIG_RELATIVE,
        validator.PASS_RECEIPT_RELATIVE,
        validator.ACTIVATION_RELATIVE,
        validator.RUNNER_RELATIVE,
        validator.VALIDATOR_RELATIVE,
        validator.TESTS_RELATIVE,
    }
    assert validator.RESULT_RELATIVE.endswith("_v4")


def test_v4_result_validator_reports_absent_without_writing(tmp_path: Path):
    result = tmp_path / "absent"
    report = validator._validate_result(_config(), result)
    assert report == {
        "result_present": False,
        "result_manifest_sha256": None,
        "confirmatory_pilot_executed": False,
        "cross_solver_confirmation_completed": False,
    }
    assert not result.exists()


def test_v4_rejects_config_hash_authority_drift(monkeypatch: pytest.MonkeyPatch):
    config = _config()
    config["implementation"]["runner_path"] = "experiments/not_v4.py"
    with pytest.raises(ValueError, match="implementation contract"):
        validator._validate_config(config)


def test_v4_activation_is_confirmatory_only():
    activation = yaml.safe_load(
        (ROOT / validator.ACTIVATION_RELATIVE).read_text(encoding="utf-8")
    )
    assert activation["permissions"]["execute_confirmatory_pilot"] is True
    assert activation["permissions"]["execute_formal_grid"] is False
    assert activation["permissions"]["execute_pairwise"] is False
    assert activation["permissions"]["execute_identification"] is False
    assert activation["permissions"]["make_security_claim"] is False
