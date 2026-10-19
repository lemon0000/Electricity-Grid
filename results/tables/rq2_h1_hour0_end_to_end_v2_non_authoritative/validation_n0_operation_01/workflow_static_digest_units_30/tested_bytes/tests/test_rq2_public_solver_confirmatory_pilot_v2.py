from __future__ import annotations

import copy
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from experiments import run_rq2_public_solver_confirmatory_pilot_v2 as runner
from experiments import validate_rq2_public_solver_confirmatory_pilot_v2 as validator

ROOT = Path(__file__).resolve().parents[1]
V1_RUNS = ROOT / "results/tables/rq2_public_solver_pilot_v1/runs.json"


def _config() -> dict[str, object]:
    return yaml.safe_load(runner.CONFIG.read_text(encoding="utf-8"))


def _runs() -> list[dict[str, object]]:
    return validator._list(
        validator._load_json_strict(V1_RUNS, "frozen v1 runs"), "runs"
    )


def _fake_controller(result: Path, config: dict[str, object]) -> dict[str, object]:
    controller: dict[str, object] = {
        "schema": runner.CONTROLLER_SCHEMA,
        "controller_pid": 41000,
        "controller_started_ns": 1770000000000000000,
        "controller_nonce": "a" * 64,
        "controller_identity_sha256": "",
        "config_sha256": runner._sha256(runner.CONFIG),
        "runner_sha256": runner._sha256(Path(runner.__file__)),
        "semantic_authority_sha256": config["semantic_authority"][
            "manifest_sha256"
        ],
        "execution_order": runner.EXPECTED_RUNS,
        "process_evidence_scope": runner.PROCESS_EVIDENCE_SCOPE,
    }
    controller["controller_identity_sha256"] = runner._controller_identity(controller)
    runner._write_json_atomic(result / "controller_receipt.json", controller)
    controller["receipt_sha256"] = runner._sha256(
        result / "controller_receipt.json"
    )
    return controller


def _fake_worker(
    worker_root: Path,
    run: dict[str, object],
    controller: dict[str, object],
    pid: int,
    *,
    previous_worker_receipt_sha256: str | None,
    previous_receipt_issued_ns: int,
) -> dict[str, object]:
    worker_root.mkdir(exist_ok=True)
    assert not list(worker_root.iterdir())
    run_id = str(run["run_id"])
    solver, repetition = runner._run_identity(run_id)
    payload = {
        **runner._expected_payload_fields(run_id, controller),
        "worker_pid": pid,
        "run": copy.deepcopy(run),
    }
    runner._write_json_atomic(worker_root / "payload.json", payload)
    report = {
        "schema": runner.WORKER_REPORT_SCHEMA,
        "run_id": run_id,
        "execution_index": runner._execution_index(run_id),
        "solver_name": solver,
        "repetition": repetition,
        "worker_pid": pid,
        "worker_parent_pid": controller["controller_pid"],
        "controller_pid": controller["controller_pid"],
        "controller_identity_sha256": controller["controller_identity_sha256"],
        "controller_receipt_sha256": controller["receipt_sha256"],
        "config_sha256": controller["config_sha256"],
        "runner_sha256": controller["runner_sha256"],
        "semantic_authority_sha256": controller["semantic_authority_sha256"],
        "worker_exit_code": 0,
        "payload_sha256": runner._sha256(worker_root / "payload.json"),
    }
    return runner._publish_worker_receipt(
        worker_root,
        run_id,
        controller,
        report,
        process_pid=pid,
        process_returncode=0,
        previous_worker_receipt_sha256=previous_worker_receipt_sha256,
        previous_receipt_issued_ns=previous_receipt_issued_ns,
    )


def _build_result(result: Path) -> Path:
    result.mkdir()
    workers = result / "workers"
    workers.mkdir()
    config = _config()
    controller = _fake_controller(result, config)
    previous_receipt_sha256: str | None = None
    previous_receipt_issued_ns = int(controller["controller_started_ns"])
    for index, run in enumerate(_runs(), start=1):
        worker_root = workers / str(run["run_id"])
        receipt = _fake_worker(
            worker_root,
            run,
            controller,
            42000 + index,
            previous_worker_receipt_sha256=previous_receipt_sha256,
            previous_receipt_issued_ns=previous_receipt_issued_ns,
        )
        previous_receipt_sha256 = runner._sha256(worker_root / "receipt.json")
        previous_receipt_issued_ns = int(receipt["receipt_issued_ns"])
    runner._write_result(result, runner.CONFIG, config)
    return result


@pytest.fixture(scope="session")
def result_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _build_result(tmp_path_factory.mktemp("rq2_confirmatory_v2") / "result")


@pytest.fixture
def valid_result(tmp_path: Path, result_template: Path) -> Path:
    result = tmp_path / "result"
    shutil.copytree(result_template, result)
    return result


def _rehash(result: Path) -> None:
    runner._write_json_atomic(
        result / "SHA256SUMS.json", runner._result_manifest(result)
    )


def test_v2_preflight_is_canonical_zero_solver_zero_write_and_closed():
    assert not validator.RESULT.exists()
    report = validator.validate()
    assert report["validation_passed"] is True
    assert report["implementation_ready"] is True
    assert report["independent_v2_implementation_review_passed"] is False
    assert report["v3_execution_successor_present"] is False
    assert report["execution_ready"] is False
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["confirmatory_pilot_executed"] is False
    assert report["cross_solver_confirmation_completed"] is False
    assert report["formal_execution_ready"] is False
    assert report["security_certified"] is False
    assert not validator.RESULT.exists()


def test_validate_only_never_dispatches_or_calls_a_solver(monkeypatch: pytest.MonkeyPatch):
    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("validate-only dispatched a process")

    monkeypatch.setattr(runner.subprocess, "Popen", forbidden)
    report = runner.run(validate_only=True)
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0


def test_v2_inherits_scientific_inventory_options_thresholds_and_order_exactly():
    config = _config()
    v1 = yaml.safe_load(
        (ROOT / "configs/rq2_public_solver_pilot_v1.yaml").read_text(
            encoding="utf-8"
        )
    )
    for field in ("input", "model", "pilot_blocks", "solvers"):
        assert config[field] == v1[field]
    assert config["execution"]["execution_order"] == runner.EXPECTED_RUNS
    assert config["execution"]["external_watchdog_seconds"] == 21600
    for solver in config["solvers"].values():
        assert solver["threads"] == 4
        assert solver["random_seed"] == 0
        assert solver["time_limit_seconds"] is None
    assert config["acceptance"]["scientific_threshold_values_changed"] is False


def test_rework_receipt_is_not_pass_and_successor_route_is_reachable_by_addition():
    config = _config()
    review = yaml.safe_load(
        (ROOT / validator.REVIEW_RELATIVE).read_text(encoding="utf-8")
    )
    successor = config["gate_opening_successor_contract"]
    assert review["verdict"] == "REWORK"
    assert review["effect"]["independent_confirmatory_implementation_review_passed"] is False
    assert successor["current_v2_execution_gate_remains_closed"] is True
    assert successor["future_successor_version"] == 3
    assert successor["future_files_are_not_current_manifest_members"] is True
    assert successor["v3_must_bind_exact_v2_outer_sha256"] is True
    assert successor["v3_must_bind_exact_pass_receipt_sha256"] is True
    assert set(successor["v3_required_new_artifact_paths"]) == {
        "pass_receipt",
        "activation",
        "config",
        "runner",
        "validator",
        "tests",
        "bundle",
        "outer",
    }


def test_complete_durable_tree_reconstructs_runs_in_preregistered_order(
    valid_result: Path,
):
    config = _config()
    report = validator._validate_result(config, valid_result)
    runs, pids, controller = runner._reconstruct_runs(
        valid_result, config, load_json=validator._load_json_strict
    )
    assert report["cross_solver_confirmation_completed"] is True
    assert [run["run_id"] for run in runs] == runner.EXPECTED_RUNS
    assert len(pids) == len(set(pids)) == 4
    assert controller["process_evidence_scope"] == runner.PROCESS_EVIDENCE_SCOPE


def test_copying_v1_runs_and_only_changing_wall_time_cannot_bypass_provenance(
    valid_result: Path,
):
    copied = copy.deepcopy(_runs())
    copied[0]["blocks"][0]["baseline_wall_seconds"] += 1.0
    runner._write_json_atomic(valid_result / "runs.json", copied)
    _rehash(valid_result)
    with pytest.raises(ValueError, match="exact reconstruction"):
        validator._validate_result(_config(), valid_result)


@pytest.mark.parametrize(
    ("relative", "field", "value"),
    [
        ("workers/highs_r1/payload.json", "worker_pid", 99999),
        ("workers/highs_r1/payload.json", "worker_parent_pid", 99999),
        ("workers/highs_r1/payload.json", "execution_index", 4),
        ("workers/highs_r1/payload.json", "controller_nonce", "b" * 64),
        ("workers/highs_r1/receipt.json", "payload_sha256", "0" * 64),
        ("workers/highs_r1/receipt.json", "worker_exit_code", 7),
        ("workers/highs_r1/receipt.json", "controller_receipt_sequence", 4),
        ("workers/gurobi_r1/receipt.json", "previous_worker_receipt_sha256", "0" * 64),
    ],
)
def test_forged_worker_provenance_fails_closed(
    valid_result: Path, relative: str, field: str, value: object
):
    path = valid_result / relative
    payload = validator._mapping(validator._load_json_strict(path, relative), relative)
    payload[field] = value
    runner._write_json_atomic(path, payload)
    _rehash(valid_result)
    with pytest.raises(ValueError, match="drifted"):
        validator._validate_result(_config(), valid_result)


def test_forged_controller_nonce_fails_even_if_result_manifest_is_resealed(
    valid_result: Path,
):
    path = valid_result / "controller_receipt.json"
    receipt = validator._mapping(
        validator._load_json_strict(path, "controller"), "controller"
    )
    receipt["controller_nonce"] = "b" * 64
    runner._write_json_atomic(path, receipt)
    _rehash(valid_result)
    with pytest.raises(ValueError, match="controller receipt authority drifted"):
        validator._validate_result(_config(), valid_result)


def test_duplicate_worker_pid_is_rejected(valid_result: Path):
    left = valid_result / "workers/highs_r1/payload.json"
    right = valid_result / "workers/gurobi_r1/payload.json"
    left_payload = validator._mapping(
        validator._load_json_strict(left, "left payload"), "left payload"
    )
    right_payload = validator._mapping(
        validator._load_json_strict(right, "right payload"), "right payload"
    )
    right_payload["worker_pid"] = left_payload["worker_pid"]
    runner._write_json_atomic(right, right_payload)
    _rehash(valid_result)
    with pytest.raises(ValueError):
        validator._validate_result(_config(), valid_result)


def test_controller_receipt_issue_order_is_strictly_increasing(valid_result: Path):
    first = valid_result / "workers/highs_r1/receipt.json"
    second = valid_result / "workers/gurobi_r1/receipt.json"
    first_payload = validator._mapping(
        validator._load_json_strict(first, "first receipt"), "first receipt"
    )
    second_payload = validator._mapping(
        validator._load_json_strict(second, "second receipt"), "second receipt"
    )
    second_payload["receipt_issued_ns"] = first_payload["receipt_issued_ns"]
    runner._write_json_atomic(second, second_payload)
    _rehash(valid_result)
    with pytest.raises(ValueError, match="issue order drifted"):
        validator._validate_result(_config(), valid_result)


def test_first_worker_receipt_must_follow_controller_start(valid_result: Path):
    controller = validator._mapping(
        validator._load_json_strict(
            valid_result / "controller_receipt.json", "controller"
        ),
        "controller",
    )
    first = valid_result / "workers/highs_r1/receipt.json"
    receipt = validator._mapping(
        validator._load_json_strict(first, "first receipt"), "first receipt"
    )
    receipt["receipt_issued_ns"] = controller["controller_started_ns"]
    runner._write_json_atomic(first, receipt)
    _rehash(valid_result)
    with pytest.raises(ValueError, match="issue order drifted"):
        validator._validate_result(_config(), valid_result)


@pytest.mark.parametrize("mutation", ["extra", "missing"])
def test_extra_or_missing_worker_file_fails_closed(valid_result: Path, mutation: str):
    worker = valid_result / "workers/highs_r1"
    if mutation == "extra":
        (worker / "extra.json").write_text("{}\n", encoding="utf-8")
    else:
        (worker / "receipt.json").unlink()
    _rehash(valid_result)
    with pytest.raises(ValueError):
        validator._validate_result(_config(), valid_result)


def test_duplicate_run_directory_fails_closed(valid_result: Path):
    shutil.copytree(
        valid_result / "workers/highs_r1", valid_result / "workers/highs_r1_copy"
    )
    _rehash(valid_result)
    with pytest.raises(ValueError, match="inventory drifted"):
        validator._validate_result(_config(), valid_result)


def test_symlink_worker_evidence_is_rejected(
    valid_result: Path, monkeypatch: pytest.MonkeyPatch
):
    receipt = valid_result / "workers/highs_r1/receipt.json"
    original_is_symlink = Path.is_symlink

    def report_registered_receipt_as_symlink(path: Path) -> bool:
        return path == receipt or original_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", report_registered_receipt_as_symlink)
    with pytest.raises(ValueError, match="symlink|inventory|ordinary"):
        validator._validate_result(_config(), valid_result)


def test_duplicate_key_json_is_rejected_for_manifest_and_payload(
    valid_result: Path, tmp_path: Path
):
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"run_id":"a","run_id":"b"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate key"):
        validator._load_json_strict(duplicate, "payload")
    manifest = valid_result / "SHA256SUMS.json"
    manifest.write_text(
        '{"config.yaml":"0","config.yaml":"1"}\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="duplicate key"):
        validator._validate_result(_config(), valid_result)
    nonstandard = tmp_path / "nonstandard.json"
    nonstandard.write_text('{"value":NaN}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="non-standard JSON constant"):
        validator._load_json_strict(nonstandard, "payload")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema", "wrong_schema"),
        ("run_count", 3),
        ("block_run_count", 15),
        ("hour_run_count", 383),
        ("pairwise_block_comparison_count", 23),
        ("raw_status_inventory", []),
        ("diagnostic_semantic_consistency_observed", False),
        ("v1_eligibility_changed", True),
        ("confirmatory_pilot_required", False),
        ("cross_solver_confirmation_completed", True),
    ],
)
def test_exact_evaluator_contract_rejects_each_changed_field(
    result_template: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
):
    result = tmp_path / "candidate"
    shutil.copytree(result_template, result)
    shutil.copyfile(result_template / "config.yaml", result / "config.yaml")
    original = runner.evaluate_runs

    def changed(config: object, runs: object) -> dict[str, object]:
        report = original(config, runs)
        report[field] = value
        return report

    monkeypatch.setattr(runner, "evaluate_runs", changed)
    with pytest.raises(ValueError, match="evaluator report contract"):
        runner._write_result(result, runner.CONFIG, _config())


def test_completed_wrapper_requires_exact_provenance_reconstruction_and_evaluator(
    valid_result: Path,
):
    path = valid_result / "semantic_validation.json"
    semantic = validator._mapping(
        validator._load_json_strict(path, "semantic"), "semantic"
    )
    semantic["evaluator_report"]["v1_eligibility_changed"] = True
    runner._write_json_atomic(path, semantic)
    _rehash(valid_result)
    with pytest.raises(ValueError, match="wrapper drifted"):
        validator._validate_result(_config(), valid_result)


class _TimeoutProcess:
    pid = 50001

    def __init__(self) -> None:
        self.returncode: int | None = None
        self.killed = False

    def communicate(self, timeout: int) -> tuple[str, str]:
        if not self.killed:
            raise subprocess.TimeoutExpired(["worker"], timeout)
        self.returncode = -9
        return "", ""

    def kill(self) -> None:
        self.killed = True

    def poll(self) -> int | None:
        return self.returncode


class _ErrorProcess:
    pid = 50002
    returncode = 7

    def communicate(self, timeout: int) -> tuple[str, str]:
        return "", "unresolved"

    def poll(self) -> int:
        return self.returncode


class _UnkillableProcess:
    pid = 50003
    returncode = None

    def communicate(self, timeout: int) -> tuple[str, str]:
        raise subprocess.TimeoutExpired(["worker"], timeout)

    def kill(self) -> None:
        return None

    def poll(self) -> None:
        return None


def _dispatch_contract(tmp_path: Path) -> tuple[Path, dict[str, object], Path]:
    result = tmp_path / "staging"
    result.mkdir()
    worker = result / "worker"
    worker.mkdir()
    controller = _fake_controller(result, _config())
    return worker, controller, result / "controller_receipt.json"


def test_watchdog_kills_and_confirms_returncode_without_infeasibility_mapping(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    worker, controller, controller_path = _dispatch_contract(tmp_path)
    process = _TimeoutProcess()
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *args, **kwargs: process)
    with pytest.raises(TimeoutError, match="not infeasibility evidence"):
        runner._dispatch_worker(
            runner.CONFIG,
            run_id="highs_r1",
            worker_root=worker,
            controller=controller,
        controller_receipt_path=controller_path,
        python_executable=Path("python.exe"),
        watchdog_seconds=1,
        execution_index=1,
        previous_worker_receipt_sha256=None,
        previous_receipt_issued_ns=0,
        )
    assert process.killed is True
    assert process.returncode == -9


def test_worker_error_is_unresolved_not_infeasible(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    worker, controller, controller_path = _dispatch_contract(tmp_path)
    monkeypatch.setattr(
        runner.subprocess, "Popen", lambda *args, **kwargs: _ErrorProcess()
    )
    with pytest.raises(RuntimeError, match="not infeasibility"):
        runner._dispatch_worker(
            runner.CONFIG,
            run_id="highs_r1",
            worker_root=worker,
            controller=controller,
        controller_receipt_path=controller_path,
        python_executable=Path("python.exe"),
        watchdog_seconds=1,
        execution_index=1,
        previous_worker_receipt_sha256=None,
        previous_receipt_issued_ns=0,
        )


def test_watchdog_refuses_publication_when_termination_is_unconfirmed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    worker, controller, controller_path = _dispatch_contract(tmp_path)
    monkeypatch.setattr(
        runner.subprocess, "Popen", lambda *args, **kwargs: _UnkillableProcess()
    )
    with pytest.raises(RuntimeError, match="termination is unconfirmed"):
        runner._dispatch_worker(
            runner.CONFIG,
            run_id="highs_r1",
            worker_root=worker,
            controller=controller,
            controller_receipt_path=controller_path,
            python_executable=Path("python.exe"),
            watchdog_seconds=1,
            execution_index=1,
            previous_worker_receipt_sha256=None,
            previous_receipt_issued_ns=0,
        )
    assert not (worker / "receipt.json").exists()


def test_existing_output_is_rejected_before_gate_or_staging_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    target = tmp_path / validator.RESULT_RELATIVE
    target.mkdir(parents=True)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        runner.run()
    assert list(target.iterdir()) == []


def test_atomic_publication_failure_removes_staging_and_publishes_no_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    runs_by_id = {str(run["run_id"]): run for run in _runs()}
    observed_order: list[str] = []

    def fake_dispatch(
        config_path: Path,
        *,
        run_id: str,
        worker_root: Path,
        controller: dict[str, object],
        controller_receipt_path: Path,
        python_executable: Path,
        watchdog_seconds: int,
        execution_index: int,
        previous_worker_receipt_sha256: str | None,
        previous_receipt_issued_ns: int,
    ) -> dict[str, object]:
        observed_order.append(run_id)
        return _fake_worker(
            worker_root,
            runs_by_id[run_id],
            controller,
            43000 + len(observed_order),
            previous_worker_receipt_sha256=previous_worker_receipt_sha256,
            previous_receipt_issued_ns=previous_receipt_issued_ns,
        )

    original_rename = Path.rename

    def fail_publication(path: Path, target: Path) -> Path:
        if path.name.startswith(".rq2_public_solver_confirmatory_pilot_v2.staging."):
            raise OSError("simulated atomic publication failure")
        return original_rename(path, target)

    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "_require_execution_gate", lambda config: None)
    monkeypatch.setattr(runner, "require_execution_host", lambda config: None)
    monkeypatch.setattr(runner, "_python_authority", lambda config: Path("python.exe"))
    monkeypatch.setattr(runner, "_dispatch_worker", fake_dispatch)
    monkeypatch.setattr(Path, "rename", fail_publication)
    with pytest.raises(OSError, match="publication failure"):
        runner.run()
    assert observed_order == runner.EXPECTED_RUNS
    target = tmp_path / validator.RESULT_RELATIVE
    assert not target.exists()
    assert not list(target.parent.glob(".*.staging.*"))


def test_formal_and_security_claims_remain_false_in_valid_result(valid_result: Path):
    summary = validator._mapping(
        validator._load_json_strict(valid_result / "summary.json", "summary"),
        "summary",
    )
    semantic = validator._mapping(
        validator._load_json_strict(
            valid_result / "semantic_validation.json", "semantic"
        ),
        "semantic",
    )
    assert summary["formal_grid_execution_started"] is False
    assert summary["formal_result_exists"] is False
    assert summary["claim"] is False
    assert summary["security_certified"] is False
    assert semantic["formal_grid_execution_started"] is False
    assert semantic["security_certified"] is False
