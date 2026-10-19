from __future__ import annotations

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from experiments import run_rq2_public_solver_confirmatory_pilot_v3 as runner
from experiments import validate_rq2_public_solver_confirmatory_pilot_v3 as validator

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
        "controller_pid": 51000,
        "controller_started_ns": 1770000000000000000,
        "controller_nonce": "a" * 64,
        "controller_identity_sha256": "",
        "v2_outer_sha256": runner.V2_OUTER_SHA256,
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
    run_id = str(run["run_id"])
    payload = {
        **runner._expected_payload_fields(run_id, controller),
        "worker_pid": pid,
        "run": copy.deepcopy(run),
    }
    runner._write_json_atomic(worker_root / "payload.json", payload)
    report = runner.build_expected_worker_report(
        run_id=run_id,
        payload=payload,
        controller=controller,
        payload_sha256=runner._sha256(worker_root / "payload.json"),
        observed_worker_pid=pid,
        observed_returncode=0,
    )
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
            52000 + index,
            previous_worker_receipt_sha256=previous_receipt_sha256,
            previous_receipt_issued_ns=previous_receipt_issued_ns,
        )
        previous_receipt_sha256 = runner._sha256(worker_root / "receipt.json")
        previous_receipt_issued_ns = int(receipt["receipt_issued_ns"])
    runner._write_result(result, runner.CONFIG, config)
    return result


@pytest.fixture(scope="session")
def result_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _build_result(tmp_path_factory.mktemp("rq2_confirmatory_v3") / "result")


@pytest.fixture
def valid_result(tmp_path: Path, result_template: Path) -> Path:
    result = tmp_path / "result"
    shutil.copytree(result_template, result)
    return result


def _rehash(result: Path) -> None:
    runner._write_json_atomic(
        result / "SHA256SUMS.json", runner._result_manifest(result)
    )


def _last_receipt(result: Path) -> Path:
    return result / "workers/highs_r2/receipt.json"


def test_v3_preflight_is_zero_solver_zero_write_and_closed():
    assert not validator.RESULT.exists()
    report = validator.validate()
    assert report["validation_passed"] is True
    assert report["v2_outer_sha256"] == runner.V2_OUTER_SHA256
    assert report["escalation_verdict"] == "ESCALATE"
    assert report["independent_v3_implementation_review_passed"] is False
    assert report["v4_execution_successor_present"] is False
    assert report["execution_ready"] is False
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["result_present"] is False
    assert report["cross_solver_confirmation_completed"] is False
    assert report["formal_execution_ready"] is False
    assert not validator.RESULT.exists()


def test_validate_only_never_dispatches(monkeypatch: pytest.MonkeyPatch):
    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("validate-only dispatched a process")

    monkeypatch.setattr(runner.subprocess, "Popen", forbidden)
    report = runner.run(validate_only=True)
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0


def test_v3_exactly_binds_v2_and_inherits_science_without_changes():
    config = _config()
    observed = validator._artifact_map(
        {
            key: value
            for key, value in config["v2_predecessor_authority"].items()
            if key != "immutable"
        },
        "v2 predecessor",
    )
    assert observed == validator.V2_HASHES
    v2 = yaml.safe_load((ROOT / validator.V2_CONFIG_RELATIVE).read_text("utf-8"))
    inheritance = config["scientific_inheritance"]
    assert inheritance["exact_fields"] == [
        "input",
        "model",
        "pilot_blocks",
        "solvers",
        "execution",
        "acceptance",
    ]
    assert v2["execution"]["execution_order"] == runner.EXPECTED_RUNS
    assert v2["execution"]["external_watchdog_seconds"] == 21600
    for solver in v2["solvers"].values():
        assert solver["threads"] == 4
        assert solver["random_seed"] == 0
        assert solver["time_limit_seconds"] is None
    assert v2["acceptance"]["scientific_threshold_values_changed"] is False


def test_v3_is_closed_and_only_complete_v4_addition_can_open_future_gate():
    config = _config()
    with pytest.raises(RuntimeError, match="closed execution gate"):
        runner._require_execution_gate(config)
    successor = config["gate_opening_successor_contract"]
    assert successor["current_v3_execution_gate_remains_closed"] is True
    assert successor["future_successor_version"] == 4
    assert successor["future_files_are_not_current_manifest_members"] is True
    assert successor["v4_must_bind_exact_v3_outer_sha256"] is True
    assert successor["v4_must_bind_exact_pass_receipt_sha256"] is True
    assert set(successor["v4_required_new_artifact_paths"].values()).isdisjoint(
        validator.BUNDLE_INVENTORY
    )


def test_valid_tree_reconstructs_runs_only_from_payloads(valid_result: Path):
    config = _config()
    report = validator._validate_result(config, valid_result)
    runs, pids, controller = runner._reconstruct_runs(
        valid_result, config, load_json=validator._load_json_strict
    )
    assert report["cross_solver_confirmation_completed"] is True
    assert [run["run_id"] for run in runs] == runner.EXPECTED_RUNS
    assert len(pids) == len(set(pids)) == 4
    assert controller["v2_outer_sha256"] == runner.V2_OUTER_SHA256


def test_published_runs_must_equal_payload_reconstruction(valid_result: Path):
    runs = validator._list(
        validator._load_json_strict(valid_result / "runs.json", "runs"), "runs"
    )
    runs[0]["blocks"][0]["baseline_wall_seconds"] += 1.0
    runner._write_json_atomic(valid_result / "runs.json", runs)
    _rehash(valid_result)
    with pytest.raises(ValueError, match="exact reconstruction"):
        validator._validate_result(_config(), valid_result)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema", "wrong_schema"),
        ("run_id", "gurobi_r1"),
        ("execution_index", 1),
        ("solver_name", "gurobi"),
        ("repetition", 1),
        ("worker_pid", 99999),
        ("worker_parent_pid", 99998),
        ("controller_pid", 99997),
        ("controller_started_ns", 1),
        ("controller_nonce", "b" * 64),
        ("controller_identity_sha256", "0" * 64),
        ("controller_receipt_sha256", "1" * 64),
        ("v2_outer_sha256", "2" * 64),
        ("config_sha256", "3" * 64),
        ("runner_sha256", "4" * 64),
        ("semantic_authority_sha256", "5" * 64),
        ("worker_exit_code", 7),
        ("payload_sha256", "6" * 64),
    ],
)
def test_last_nested_worker_report_cannot_define_its_own_authority(
    valid_result: Path, field: str, value: object
):
    path = _last_receipt(valid_result)
    receipt = validator._mapping(
        validator._load_json_strict(path, "last receipt"), "last receipt"
    )
    report = validator._mapping(receipt["worker_report"], "nested report")
    report[field] = value
    receipt["worker_report"] = report
    receipt["worker_report_sha256"] = runner._sha256_bytes(
        runner._canonical_json_bytes(report)
    )
    runner._write_json_atomic(path, receipt)
    _rehash(valid_result)
    with pytest.raises(ValueError, match="nested worker report drifted"):
        validator._validate_result(_config(), valid_result)


@pytest.mark.parametrize("scope", ["top", "nested"])
@pytest.mark.parametrize("mutation", ["extra", "missing"])
def test_receipt_top_and_nested_schema_extra_or_missing_fail_closed(
    valid_result: Path, scope: str, mutation: str
):
    path = _last_receipt(valid_result)
    receipt = validator._mapping(
        validator._load_json_strict(path, "last receipt"), "last receipt"
    )
    target = receipt
    if scope == "nested":
        target = validator._mapping(receipt["worker_report"], "nested report")
    if mutation == "extra":
        target["unexpected"] = True
    else:
        target.pop("schema")
    if scope == "nested":
        receipt["worker_report"] = target
        receipt["worker_report_sha256"] = runner._sha256_bytes(
            runner._canonical_json_bytes(target)
        )
    runner._write_json_atomic(path, receipt)
    _rehash(valid_result)
    with pytest.raises(ValueError, match="schema drifted|nested worker report drifted"):
        validator._validate_result(_config(), valid_result)


@pytest.mark.parametrize("scope", ["top", "nested"])
def test_receipt_top_and_nested_duplicate_keys_fail_closed(
    valid_result: Path, scope: str
):
    path = _last_receipt(valid_result)
    receipt = validator._mapping(
        validator._load_json_strict(path, "last receipt"), "last receipt"
    )
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    indent = "  " if scope == "top" else "    "
    needle = f'{indent}"run_id": "highs_r2",\n'
    lines = text.splitlines(keepends=True)
    matches = [index for index, line in enumerate(lines) if line == needle]
    assert len(matches) == 1
    lines.insert(matches[0], needle)
    path.write_text("".join(lines), encoding="utf-8")
    _rehash(valid_result)
    with pytest.raises(ValueError, match="duplicate key"):
        validator._validate_result(_config(), valid_result)


@pytest.mark.parametrize("mutation", ["extra", "missing"])
def test_payload_schema_extra_or_missing_fails_closed(
    valid_result: Path, mutation: str
):
    path = valid_result / "workers/highs_r2/payload.json"
    payload = validator._mapping(
        validator._load_json_strict(path, "payload"), "payload"
    )
    if mutation == "extra":
        payload["unexpected"] = True
    else:
        payload.pop("schema")
    runner._write_json_atomic(path, payload)
    _rehash(valid_result)
    with pytest.raises(ValueError, match="payload schema drifted"):
        validator._validate_result(_config(), valid_result)


def test_duplicate_pid_and_receipt_chain_forgery_fail_closed(valid_result: Path):
    left = valid_result / "workers/gurobi_r2/payload.json"
    right = valid_result / "workers/highs_r2/payload.json"
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


def test_expected_report_constructor_ignores_nested_report_values(
    valid_result: Path
):
    config = _config()
    controller = runner._validate_controller(
        valid_result, config, validator._load_json_strict
    )
    payload_path = valid_result / "workers/highs_r2/payload.json"
    payload = validator._mapping(
        validator._load_json_strict(payload_path, "payload"), "payload"
    )
    receipt = validator._mapping(
        validator._load_json_strict(_last_receipt(valid_result), "receipt"),
        "receipt",
    )
    expected = runner.build_expected_worker_report(
        run_id="highs_r2",
        payload=payload,
        controller=controller,
        payload_sha256=runner._sha256(payload_path),
        observed_worker_pid=payload["worker_pid"],
        observed_returncode=0,
    )
    assert expected == receipt["worker_report"]
    forged = dict(receipt["worker_report"])
    forged["run_id"] = "gurobi_r1"
    assert expected != forged


def test_evaluator_contract_still_gates_wrapper(
    result_template: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    result = tmp_path / "candidate"
    shutil.copytree(result_template, result)
    original = runner.evaluate_runs

    def changed(config: object, runs: object) -> dict[str, object]:
        report = original(config, runs)
        report["cross_solver_confirmation_completed"] = True
        return report

    monkeypatch.setattr(runner, "evaluate_runs", changed)
    with pytest.raises(ValueError, match="evaluator report contract"):
        runner._write_result(result, runner.CONFIG, _config())


class _TimeoutProcess:
    pid = 53001

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


class _UnkillableProcess:
    pid = 53002
    returncode = None

    def communicate(self, timeout: int) -> tuple[str, str]:
        raise subprocess.TimeoutExpired(["worker"], timeout)

    def kill(self) -> None:
        return None

    def poll(self) -> None:
        return None


class _ErrorProcess:
    pid = 53003
    returncode = 7

    def communicate(self, timeout: int) -> tuple[str, str]:
        return "", "unresolved"

    def poll(self) -> int:
        return self.returncode


def _dispatch_contract(tmp_path: Path) -> tuple[Path, dict[str, object], Path]:
    result = tmp_path / "staging"
    result.mkdir()
    worker = result / "worker"
    worker.mkdir()
    controller = _fake_controller(result, _config())
    return worker, controller, result / "controller_receipt.json"


@pytest.mark.parametrize(
    ("process", "error_type", "pattern"),
    [
        (_TimeoutProcess(), TimeoutError, "not infeasibility evidence"),
        (_UnkillableProcess(), RuntimeError, "termination is unconfirmed"),
        (_ErrorProcess(), RuntimeError, "not infeasibility"),
    ],
)
def test_timeout_and_unresolved_never_map_to_infeasibility(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    process: object,
    error_type: type[Exception],
    pattern: str,
):
    worker, controller, controller_path = _dispatch_contract(tmp_path)
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *args, **kwargs: process)
    with pytest.raises(error_type, match=pattern):
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


def test_atomic_publication_failure_cleans_staging(
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
            54000 + len(observed_order),
            previous_worker_receipt_sha256=previous_worker_receipt_sha256,
            previous_receipt_issued_ns=previous_receipt_issued_ns,
        )

    original_rename = Path.rename

    def fail_publication(path: Path, target: Path) -> Path:
        if path.name.startswith(".rq2_public_solver_confirmatory_pilot_v3.staging."):
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


def test_formal_and_security_claims_remain_false(valid_result: Path):
    summary = validator._mapping(
        validator._load_json_strict(valid_result / "summary.json", "summary"),
        "summary",
    )
    assert summary["formal_grid_execution_started"] is False
    assert summary["formal_result_exists"] is False
    assert summary["claim"] is False
    assert summary["security_certified"] is False
