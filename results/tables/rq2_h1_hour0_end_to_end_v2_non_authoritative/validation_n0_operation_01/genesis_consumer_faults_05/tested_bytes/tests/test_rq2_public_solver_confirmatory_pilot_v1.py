from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from experiments import run_rq2_public_solver_confirmatory_pilot_v1 as runner
from experiments import validate_rq2_public_solver_confirmatory_pilot_v1 as validator
from experiments.validate_rq2_public_solver_pilot_semantic_successor_v1 import (
    evaluate_runs,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_solver_confirmatory_pilot_v1.yaml"
V1_RUNS = ROOT / "results/tables/rq2_public_solver_pilot_v1/runs.json"
SEMANTIC_CONFIG = (
    ROOT / "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml"
)


def _config() -> dict[str, object]:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def _payload(
    run_id: str = "highs_r1",
    solver: str = "highs",
    repetition: int = 1,
    worker_pid: int = 1234,
    parent_pid: int = 5678,
) -> dict[str, object]:
    run = {
        "run_id": run_id,
        "solver_name": solver,
        "repetition": repetition,
        "blocks": [],
    }
    return {
        "schema": runner.WORKER_SCHEMA,
        "run_id": run_id,
        "solver_name": solver,
        "repetition": repetition,
        "worker_pid": worker_pid,
        "worker_parent_pid": parent_pid,
        "parent_contract_sha256": "p" * 64,
        "config_sha256": "c" * 64,
        "implementation_sha256": "i" * 64,
        "run": run,
    }


def _write_payload(root: Path, payload: dict[str, object]) -> dict[str, object]:
    path = root / "run.json"
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "schema": runner.WORKER_RECEIPT_SCHEMA,
        "run_id": payload["run_id"],
        "worker_pid": payload["worker_pid"],
        "worker_parent_pid": payload["worker_parent_pid"],
        "parent_contract_sha256": payload["parent_contract_sha256"],
        "payload_sha256": runner._sha256(path),
    }


def _validate_payload(
    root: Path,
    receipt: dict[str, object],
    *,
    seen_run_ids: set[str] | None = None,
    seen_worker_pids: set[int] | None = None,
) -> dict[str, object]:
    return runner._validate_worker_payload(
        root,
        receipt,
        expected_run_id="highs_r1",
        expected_solver="highs",
        expected_repetition=1,
        expected_worker_pid=1234,
        expected_parent_pid=5678,
        expected_parent_contract_sha256="p" * 64,
        expected_config_sha256="c" * 64,
        expected_implementation_sha256="i" * 64,
        seen_run_ids=set() if seen_run_ids is None else seen_run_ids,
        seen_worker_pids=set() if seen_worker_pids is None else seen_worker_pids,
    )


def test_confirmatory_config_exactly_inherits_v1_science_and_order():
    config = _config()
    v1 = yaml.safe_load(
        (ROOT / "configs/rq2_public_solver_pilot_v1.yaml").read_text(
            encoding="utf-8"
        )
    )
    for field in ("input", "model", "pilot_blocks", "solvers"):
        assert config[field] == v1[field]
    assert config["execution"]["execution_order"] == [
        "highs_r1",
        "gurobi_r1",
        "gurobi_r2",
        "highs_r2",
    ]
    assert config["execution"]["external_watchdog_seconds"] == 21600
    assert all(
        solver["threads"] == 4
        and solver["random_seed"] == 0
        and solver["time_limit_seconds"] is None
        for solver in config["solvers"].values()
    )
    acceptance = config["acceptance"]
    assert acceptance["maximum_baseline_objective_difference_usd"] == 1.0e-4
    assert acceptance["maximum_finite_grid_need_difference_mw"] == 1.0e-5
    assert acceptance["maximum_constraint_violation"] == 1.0e-6
    assert acceptance["scientific_threshold_values_changed"] is False


def test_validate_only_is_zero_solver_zero_write_and_review_pending(monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("validate-only must not start a subprocess")

    monkeypatch.setattr(runner.subprocess, "Popen", forbidden)
    report = runner.run(validate_only=True)
    assert report["implementation_ready"] is True
    assert report["execution_ready"] is False
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["confirmatory_pilot_executed"] is False
    assert report["cross_solver_confirmation_completed"] is False
    assert report["formal_execution_ready"] is False
    assert report["security_certified"] is False


def test_pre_execution_gate_prevents_solver_dispatch(monkeypatch):
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *_a, **_k: pytest.fail())
    with pytest.raises(RuntimeError, match="awaits independent review"):
        runner.run()


def test_mock_dispatch_preserves_order_and_uses_fresh_unique_processes(
    monkeypatch, tmp_path: Path
):
    config = _config()
    pids = iter((4101, 4102, 4103, 4104))
    observed_commands: list[list[str]] = []

    class FakeProcess:
        def __init__(self, command: list[str], **_kwargs):
            self.command = command
            self.pid = next(pids)
            self.returncode = 0
            observed_commands.append(command)

        def communicate(self, timeout: int):
            assert timeout == 21600
            run_id = self.command[self.command.index("--run-id") + 1]
            root = Path(
                self.command[self.command.index("--worker-output") + 1]
            )
            solver, repetition = runner._run_identity(config, run_id)
            payload = _payload(
                run_id,
                solver,
                repetition,
                self.pid,
                os.getpid(),
            )
            payload["parent_contract_sha256"] = config["semantic_authority"][
                "manifest_sha256"
            ]
            payload["config_sha256"] = "c" * 64
            payload["implementation_sha256"] = "i" * 64
            receipt = _write_payload(root, payload)
            return json.dumps(receipt), ""

    monkeypatch.setattr(runner.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(runner, "_load_config", lambda _path: config)
    seen_runs: set[str] = set()
    seen_pids: set[int] = set()
    for run_id in config["execution"]["execution_order"]:
        root = tmp_path / run_id
        root.mkdir()
        record = runner._dispatch_worker(
            CONFIG,
            run_id=run_id,
            worker_root=root,
            python_executable=Path(os.sys.executable),
            watchdog_seconds=21600,
            expected_config_sha256="c" * 64,
            expected_implementation_sha256="i" * 64,
            seen_run_ids=seen_runs,
            seen_worker_pids=seen_pids,
        )
        assert record["run_id"] == run_id
    assert [
        command[command.index("--run-id") + 1] for command in observed_commands
    ] == config["execution"]["execution_order"]
    assert seen_pids == {4101, 4102, 4103, 4104}
    assert all("-m" in command and runner.MODULE in command for command in observed_commands)


@pytest.mark.parametrize("drift", ["extra", "missing", "hash", "schema"])
def test_worker_payload_inventory_hash_and_schema_drift_fail_closed(
    drift: str, tmp_path: Path
):
    root = tmp_path / "worker"
    root.mkdir()
    payload = _payload()
    if drift == "schema":
        payload["unexpected"] = True
    receipt = _write_payload(root, payload)
    if drift == "extra":
        (root / "extra.txt").write_text("drift", encoding="utf-8")
    elif drift == "missing":
        (root / "run.json").unlink()
    elif drift == "hash":
        receipt["payload_sha256"] = "0" * 64
    message = {
        "extra": "inventory drifted",
        "missing": "inventory drifted",
        "hash": "hash drifted",
        "schema": "schema drifted",
    }[drift]
    with pytest.raises(ValueError, match=message):
        _validate_payload(root, receipt)


def test_worker_payload_symlink_fails_closed(monkeypatch, tmp_path: Path):
    root = tmp_path / "worker"
    root.mkdir()
    receipt = _write_payload(root, _payload())
    original = Path.is_symlink

    def marked(path: Path) -> bool:
        return path.name == "run.json" or original(path)

    monkeypatch.setattr(Path, "is_symlink", marked)
    with pytest.raises(ValueError, match="non-symlink"):
        _validate_payload(root, receipt)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("parent_contract_sha256", "0" * 64, "parent_contract_sha256 drifted"),
        ("config_sha256", "0" * 64, "config_sha256 drifted"),
        ("implementation_sha256", "0" * 64, "implementation_sha256 drifted"),
        ("worker_pid", 4321, "worker_pid drifted"),
        ("worker_parent_pid", 8765, "worker_parent_pid drifted"),
    ],
)
def test_worker_parent_config_implementation_and_process_identity_drift_fails_closed(
    field: str,
    value: object,
    message: str,
    tmp_path: Path,
):
    root = tmp_path / "worker"
    root.mkdir()
    payload = _payload()
    payload[field] = value
    receipt = _write_payload(root, payload)
    with pytest.raises(ValueError, match=message):
        _validate_payload(root, receipt)


@pytest.mark.parametrize("duplicate", ["run", "pid"])
def test_duplicate_run_or_worker_pid_fails_closed(duplicate: str, tmp_path: Path):
    root = tmp_path / "worker"
    root.mkdir()
    receipt = _write_payload(root, _payload())
    seen_runs = {"highs_r1"} if duplicate == "run" else set()
    seen_pids = {1234} if duplicate == "pid" else set()
    with pytest.raises(ValueError, match="duplicate"):
        _validate_payload(
            root,
            receipt,
            seen_run_ids=seen_runs,
            seen_worker_pids=seen_pids,
        )


def _minimal_execution_config() -> dict[str, object]:
    return {
        "execution": {
            "execution_order": ["highs_r1"],
            "external_watchdog_seconds": 21600,
        },
        "output": {
            "directory": "results/tables/rq2_public_solver_confirmatory_pilot_v1"
        },
        "implementation": {"runner_sha256": runner._sha256(Path(runner.__file__))},
    }


def test_existing_output_is_rejected_before_worker_dispatch(monkeypatch, tmp_path: Path):
    target = tmp_path / "results/tables/rq2_public_solver_confirmatory_pilot_v1"
    target.mkdir(parents=True)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "_load_config", lambda _path: _minimal_execution_config())
    monkeypatch.setattr(runner, "_require_execution_gate", lambda _config: None)
    monkeypatch.setattr(runner, "require_execution_host", lambda _execution: None)
    monkeypatch.setattr(runner, "_python_authority", lambda _config: Path(os.sys.executable))
    monkeypatch.setattr(runner, "_dispatch_worker", lambda *_a, **_k: pytest.fail())
    monkeypatch.setattr(
        validator,
        "validate",
        lambda *_a, **_k: {"implementation_ready": True},
    )
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        runner.run(CONFIG)


def test_atomic_publication_failure_leaves_no_success_result(monkeypatch, tmp_path: Path):
    config = _minimal_execution_config()
    target = tmp_path / config["output"]["directory"]
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "_load_config", lambda _path: config)
    monkeypatch.setattr(runner, "_require_execution_gate", lambda _config: None)
    monkeypatch.setattr(runner, "require_execution_host", lambda _execution: None)
    monkeypatch.setattr(runner, "_python_authority", lambda _config: Path(os.sys.executable))
    monkeypatch.setattr(
        validator,
        "validate",
        lambda *_a, **_k: {"implementation_ready": True},
    )

    def dispatch(*_args, seen_run_ids: set[str], seen_worker_pids: set[int], **_kwargs):
        seen_run_ids.add("highs_r1")
        seen_worker_pids.add(9876)
        return {
            "run_id": "highs_r1",
            "solver_name": "highs",
            "repetition": 1,
            "blocks": [],
        }

    def write_result(staging: Path, *_args, **_kwargs):
        for name in (
            "config.yaml",
            "runs.json",
            "semantic_validation.json",
            "summary.json",
            "SHA256SUMS.json",
        ):
            (staging / name).write_text("{}\n", encoding="utf-8")
        return {"fresh_execution_status": "passed"}

    original_rename = Path.rename

    def fail_publication(path: Path, destination: Path):
        if path.name.startswith(".rq2_public_solver_confirmatory_pilot_v1.staging."):
            raise OSError("simulated atomic publication failure")
        return original_rename(path, destination)

    monkeypatch.setattr(runner, "_dispatch_worker", dispatch)
    monkeypatch.setattr(runner, "_write_result", write_result)
    monkeypatch.setattr(Path, "rename", fail_publication)
    with pytest.raises(OSError, match="simulated atomic"):
        runner.run(CONFIG)
    assert not target.exists()
    assert not list(target.parent.glob(".*.staging.*"))


def test_timeout_is_reported_as_unresolved_not_infeasibility(monkeypatch, tmp_path: Path):
    config = _config()
    root = tmp_path / "worker"
    root.mkdir()

    class TimeoutProcess:
        pid = 4321
        returncode = None

        def __init__(self, *_args, **_kwargs):
            self.calls = 0

        def communicate(self, timeout: int):
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired("worker", timeout)
            return "", ""

        def kill(self):
            self.returncode = -9

    monkeypatch.setattr(runner.subprocess, "Popen", TimeoutProcess)
    monkeypatch.setattr(runner, "_load_config", lambda _path: config)
    with pytest.raises(TimeoutError, match="not infeasibility evidence"):
        runner._dispatch_worker(
            CONFIG,
            run_id="highs_r1",
            worker_root=root,
            python_executable=Path(os.sys.executable),
            watchdog_seconds=21600,
            expected_config_sha256="c" * 64,
            expected_implementation_sha256="i" * 64,
            seen_run_ids=set(),
            seen_worker_pids=set(),
        )


def test_unresolved_semantic_record_cannot_complete_confirmation():
    semantic = yaml.safe_load(SEMANTIC_CONFIG.read_text(encoding="utf-8"))
    runs = json.loads(V1_RUNS.read_text(encoding="utf-8"))
    target = runs[1]["blocks"][1]["hours"][0]
    target["resolved_for_pipeline"] = False
    with pytest.raises(ValueError, match="unresolved hour"):
        evaluate_runs(semantic, runs)


def test_activation_authorizes_only_confirmatory_and_keeps_claims_closed():
    activation = yaml.safe_load(
        (
            ROOT
            / "configs/rq2_public_solver_confirmatory_pilot_activation_v1.yaml"
        ).read_text(encoding="utf-8")
    )
    permissions = activation["permissions"]
    assert permissions[
        "execute_confirmatory_pilot_after_independent_implementation_review"
    ] is True
    assert permissions["execute_formal_grid"] is False
    assert permissions["execute_pairwise"] is False
    assert permissions["execute_identification"] is False
    assert permissions["make_formal_result_claim"] is False
    assert permissions["make_security_claim"] is False
    assert activation["gates"]["security_certified"] is False


def test_post_result_summary_with_formal_or_security_claim_fails_closed(
    monkeypatch, tmp_path: Path
):
    config = _config()
    result = tmp_path / validator.RESULT_RELATIVE
    result.mkdir(parents=True)
    (result / "config.yaml").write_bytes(CONFIG.read_bytes())
    runs = json.loads(V1_RUNS.read_text(encoding="utf-8"))
    runs[0]["blocks"][0]["total_wall_seconds"] += 1.0e-9
    (result / "runs.json").write_text(
        json.dumps(runs, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    semantic_config = yaml.safe_load(SEMANTIC_CONFIG.read_text(encoding="utf-8"))
    semantic_report = evaluate_runs(semantic_config, runs)
    semantic = {
        "schema": "rq2_public_solver_confirmatory_semantic_validation_v1",
        "semantic_successor_config_sha256": runner._sha256(SEMANTIC_CONFIG),
        "evaluator_report": semantic_report,
        "fresh_execution_run_ids": validator.EXPECTED_RUNS,
        "fresh_worker_pids": [1001, 1002, 1003, 1004],
        "fresh_process_isolation_verified": True,
        "semantic_contract_passed": True,
        "cross_solver_confirmation_completed": True,
        "formal_grid_execution_started": False,
        "security_certified": False,
    }
    (result / "semantic_validation.json").write_text(
        json.dumps(semantic, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = {
        "schema": "rq2_public_solver_confirmatory_pilot_v1",
        "config_sha256": validator.CONFIG_SHA256,
        "implementation_sha256": config["implementation"]["runner_sha256"],
        "fresh_execution_status": "passed",
        "fresh_execution_passed": True,
        "fresh_execution_failed": False,
        "run_count": 4,
        "unique_worker_process_count": 4,
        "semantic_contract_passed": True,
        "cross_solver_confirmation_completed": True,
        "formal_grid_execution_started": True,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    (result / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = {
        name: runner._sha256(result / name)
        for name in validator.RESULT_MEMBERS
    }
    (result / "SHA256SUMS.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    semantic_copy = (
        tmp_path / "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml"
    )
    semantic_copy.parent.mkdir(parents=True)
    shutil.copyfile(SEMANTIC_CONFIG, semantic_copy)
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="summary drifted"):
        validator._validate_result(config)


def test_canonical_only_validator_rejects_substitution(tmp_path: Path):
    substitute = tmp_path / CONFIG.name
    substitute.write_bytes(CONFIG.read_bytes())
    with pytest.raises(ValueError, match="only canonical"):
        validator.validate(substitute)
