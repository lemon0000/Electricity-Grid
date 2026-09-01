"""Prepare or run the review-gated RQ2 confirmatory pilot v3 remediation."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import yaml

from experiments.run_rq2_public_solver_confirmatory_pilot_v2 import (
    EXPECTED_EVALUATOR_REPORT,
    EXPECTED_RUNS,
    PROCESS_EVIDENCE_SCOPE,
    RUN_IDENTITIES,
    _canonical_json_bytes,
    _load_json_strict,
    _load_json_strict_text,
    _mapping,
    _ordinary_empty_directory,
    _sha256,
    _sha256_bytes,
    _write_json_atomic,
)
from experiments.validate_rq2_public_solver_pilot_semantic_successor_v1 import (
    evaluate_runs,
)
from src.evaluation.execution_machine import require_execution_host

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_solver_confirmatory_pilot_v3.yaml"
BUNDLE = (
    ROOT / "configs/rq2_public_solver_confirmatory_pilot_bundle_v3.SHA256SUMS.json"
)
V2_CONFIG = ROOT / "configs/rq2_public_solver_confirmatory_pilot_v2.yaml"
V2_OUTER = (
    ROOT / "configs/rq2_public_solver_confirmatory_pilot_bundle_v2.OUTER.SHA256SUMS.json"
)
SEMANTIC_CONFIG = (
    ROOT / "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml"
)
MODULE = "experiments.run_rq2_public_solver_confirmatory_pilot_v3"
CONFIG_SCHEMA = "rq2_public_solver_confirmatory_pilot_config_v3"
CONTROLLER_SCHEMA = "rq2_public_solver_confirmatory_controller_receipt_v3"
PAYLOAD_SCHEMA = "rq2_public_solver_confirmatory_worker_payload_v3"
WORKER_REPORT_SCHEMA = "rq2_public_solver_confirmatory_worker_report_v3"
WORKER_RECEIPT_SCHEMA = "rq2_public_solver_confirmatory_worker_receipt_v3"
RESULT_SCHEMA = "rq2_public_solver_confirmatory_pilot_v3"
SEMANTIC_VALIDATION_SCHEMA = (
    "rq2_public_solver_confirmatory_semantic_validation_v3"
)
V2_OUTER_SHA256 = (
    "601c10c53daa80661db39fd356a7987dce58dcf4ce98bf9c77197f71eb448490"
)


def _bundle_files() -> dict[str, str]:
    bundle = _mapping(_load_json_strict(BUNDLE, "v3 bundle"), "v3 bundle")
    return _mapping(bundle.get("files"), "v3 bundle files")


def _load_config(config_path: Path = CONFIG) -> dict[str, Any]:
    if config_path.resolve() != CONFIG.resolve():
        raise ValueError("only the canonical v3 config is accepted")
    payload = _mapping(
        yaml.safe_load(config_path.read_text(encoding="utf-8")), "v3 config"
    )
    if payload.get("schema") != CONFIG_SCHEMA:
        raise ValueError("v3 config schema drifted")
    files = _bundle_files()
    for relative, path in (
        ("configs/rq2_public_solver_confirmatory_pilot_v3.yaml", config_path),
        ("experiments/run_rq2_public_solver_confirmatory_pilot_v3.py", Path(__file__)),
    ):
        if files.get(relative) != _sha256(path):
            raise ValueError(f"v3 runtime authority drifted: {relative}")
    return payload


def _load_scientific_parent(config: Mapping[str, Any]) -> dict[str, Any]:
    authority = _mapping(config.get("v2_predecessor_authority"), "v2 authority")
    registered = _mapping(authority.get("config"), "v2 config authority")
    if (
        registered.get("path")
        != "configs/rq2_public_solver_confirmatory_pilot_v2.yaml"
        or registered.get("sha256")
        != "d0a5c3a898d89ce869a6647b4d8f271f82921c89069cdd9dd98b4f54e7c9f1e0"
        or not V2_CONFIG.is_file()
        or V2_CONFIG.is_symlink()
        or _sha256(V2_CONFIG) != registered["sha256"]
    ):
        raise ValueError("v2 scientific parent authority drifted")
    parent = _mapping(
        yaml.safe_load(V2_CONFIG.read_text(encoding="utf-8")), "v2 config"
    )
    if parent.get("schema") != "rq2_public_solver_confirmatory_pilot_config_v2":
        raise ValueError("v2 scientific parent schema drifted")
    return parent


def _require_execution_gate(config: Mapping[str, Any]) -> None:
    gates = _mapping(config.get("gates"), "v3 gates")
    if (
        gates.get("independent_v3_implementation_review_passed") is not True
        or gates.get("v4_execution_successor_present") is not True
        or gates.get("confirmatory_execution_ready") is not True
    ):
        raise RuntimeError(
            "v3 is an ESCALATE remediation candidate with a closed execution gate; "
            "an independently reviewed, newly versioned v4 successor is required"
        )


def _run_identity(run_id: str) -> tuple[str, int]:
    try:
        return RUN_IDENTITIES[run_id]
    except KeyError as error:
        raise ValueError(f"unregistered v3 run_id: {run_id}") from error


def _execution_index(run_id: str) -> int:
    try:
        return EXPECTED_RUNS.index(run_id) + 1
    except ValueError as error:
        raise ValueError(f"unregistered v3 run_id: {run_id}") from error


def _controller_identity(receipt: Mapping[str, Any]) -> str:
    identity = {
        "controller_pid": receipt.get("controller_pid"),
        "controller_started_ns": receipt.get("controller_started_ns"),
        "controller_nonce": receipt.get("controller_nonce"),
    }
    return _sha256_bytes(_canonical_json_bytes(identity))


def _create_controller_receipt(
    staging: Path, config: Mapping[str, Any]
) -> dict[str, object]:
    receipt: dict[str, object] = {
        "schema": CONTROLLER_SCHEMA,
        "controller_pid": os.getpid(),
        "controller_started_ns": time.time_ns(),
        "controller_nonce": secrets.token_hex(32),
        "controller_identity_sha256": "",
        "v2_outer_sha256": V2_OUTER_SHA256,
        "config_sha256": _sha256(CONFIG),
        "runner_sha256": _sha256(Path(__file__)),
        "semantic_authority_sha256": config["semantic_authority"][
            "manifest_sha256"
        ],
        "execution_order": list(EXPECTED_RUNS),
        "process_evidence_scope": PROCESS_EVIDENCE_SCOPE,
    }
    receipt["controller_identity_sha256"] = _controller_identity(receipt)
    _write_json_atomic(staging / "controller_receipt.json", receipt)
    return receipt


def _expected_payload_fields(
    run_id: str, controller: Mapping[str, Any]
) -> dict[str, object]:
    solver, repetition = _run_identity(run_id)
    return {
        "schema": PAYLOAD_SCHEMA,
        "run_id": run_id,
        "execution_index": _execution_index(run_id),
        "solver_name": solver,
        "repetition": repetition,
        "worker_parent_pid": controller["controller_pid"],
        "worker_declared_exit_code": 0,
        "controller_pid": controller["controller_pid"],
        "controller_started_ns": controller["controller_started_ns"],
        "controller_nonce": controller["controller_nonce"],
        "controller_identity_sha256": controller["controller_identity_sha256"],
        "controller_receipt_sha256": controller["receipt_sha256"],
        "v2_outer_sha256": controller["v2_outer_sha256"],
        "config_sha256": controller["config_sha256"],
        "runner_sha256": controller["runner_sha256"],
        "semantic_authority_sha256": controller["semantic_authority_sha256"],
    }


def build_expected_worker_report(
    *,
    run_id: str,
    payload: Mapping[str, Any],
    controller: Mapping[str, Any],
    payload_sha256: str,
    observed_worker_pid: int,
    observed_returncode: int,
) -> dict[str, object]:
    """Build the sole worker-report authority from non-nested observations."""
    solver, repetition = _run_identity(run_id)
    if (
        isinstance(observed_worker_pid, bool)
        or not isinstance(observed_worker_pid, int)
        or observed_worker_pid <= 0
        or payload.get("worker_pid") != observed_worker_pid
    ):
        raise ValueError(f"{run_id} observed worker PID drifted")
    if observed_returncode != 0:
        raise ValueError(f"{run_id} nonzero exit cannot form a worker report")
    for field, expected in _expected_payload_fields(run_id, controller).items():
        if payload.get(field) != expected:
            raise ValueError(f"{run_id} payload {field} drifted")
    return {
        "schema": WORKER_REPORT_SCHEMA,
        "run_id": run_id,
        "execution_index": _execution_index(run_id),
        "solver_name": solver,
        "repetition": repetition,
        "worker_pid": observed_worker_pid,
        "worker_parent_pid": controller["controller_pid"],
        "controller_pid": controller["controller_pid"],
        "controller_started_ns": controller["controller_started_ns"],
        "controller_nonce": controller["controller_nonce"],
        "controller_identity_sha256": controller["controller_identity_sha256"],
        "controller_receipt_sha256": controller["receipt_sha256"],
        "v2_outer_sha256": controller["v2_outer_sha256"],
        "config_sha256": controller["config_sha256"],
        "runner_sha256": controller["runner_sha256"],
        "semantic_authority_sha256": controller["semantic_authority_sha256"],
        "worker_exit_code": 0,
        "payload_sha256": payload_sha256,
    }


def _execute_worker(
    config_path: Path,
    *,
    run_id: str,
    worker_root: Path,
    controller_receipt_path: Path,
    expected_parent_pid: int,
    expected_execution_index: int,
    expected_controller_receipt_sha256: str,
) -> dict[str, object]:
    from experiments.run_rq2_public_solver_pilot_v1 import (
        _preflight as _v1_preflight,
    )
    from experiments.run_rq2_public_solver_pilot_v1 import _run_block
    from experiments.validate_rq2_public_solver_confirmatory_pilot_v3 import validate
    from src.grid.rts_gmlc import load_rts_gmlc_chronological_data

    validate()
    config = _load_config(config_path)
    scientific = _load_scientific_parent(config)
    _require_execution_gate(config)
    require_execution_host(scientific["execution"])
    if os.getppid() != expected_parent_pid:
        raise RuntimeError("worker PPID does not match the registered controller")
    _ordinary_empty_directory(worker_root, "worker root")
    if (
        not controller_receipt_path.is_file()
        or controller_receipt_path.is_symlink()
        or _sha256(controller_receipt_path) != expected_controller_receipt_sha256
    ):
        raise ValueError("controller receipt authority drifted")
    controller = _validate_controller(
        controller_receipt_path.parent, config, _load_json_strict
    )
    if (
        controller.get("controller_pid") != expected_parent_pid
        or controller.get("receipt_sha256")
        != expected_controller_receipt_sha256
    ):
        raise ValueError("controller receipt PID or hash drifted")
    if _execution_index(run_id) != expected_execution_index:
        raise ValueError("worker execution index is not preregistered")
    solver_name, repetition = _run_identity(run_id)
    _, context = _v1_preflight(ROOT / "configs/rq2_public_solver_pilot_v1.yaml")
    data = load_rts_gmlc_chronological_data(
        context["grid_root"], base_mva=float(scientific["input"]["base_mva"])
    )
    blocks = []
    for pilot in scientific["pilot_blocks"]:
        result = _run_block(
            data,
            context["blocks"][pilot["block_id"]],
            solver_payload=scientific["solvers"][solver_name],
            dc_bus=int(scientific["model"]["dc_bus"]),
            dc_demand_mw=float(scientific["model"]["dc_reference_demand_mw"]),
            tolerance_mw=float(scientific["model"]["tolerance_mw"]),
        )
        result["role"] = pilot["role"]
        blocks.append(result)
    payload = {
        **_expected_payload_fields(run_id, controller),
        "worker_pid": os.getpid(),
        "run": {
            "run_id": run_id,
            "solver_name": solver_name,
            "repetition": repetition,
            "blocks": blocks,
        },
    }
    published = worker_root / "payload.json"
    _write_json_atomic(published, payload)
    return build_expected_worker_report(
        run_id=run_id,
        payload=payload,
        controller=controller,
        payload_sha256=_sha256(published),
        observed_worker_pid=os.getpid(),
        observed_returncode=0,
    )


def _validate_worker_directory(
    worker_root: Path,
    run_id: str,
    controller: Mapping[str, Any],
    *,
    load_json: Callable[[Path, str], Any] = _load_json_strict,
    expected_process_pid: int | None = None,
    expected_exit_code: int | None = None,
    report: Mapping[str, Any] | None = None,
    expected_previous_receipt_sha256: str | None = None,
    minimum_receipt_issued_ns: int = 0,
) -> tuple[dict[str, object], int, str | None, int | None]:
    if not worker_root.is_dir() or worker_root.is_symlink():
        raise ValueError(f"{run_id} worker directory is not ordinary")
    expected_names = {"payload.json"} if report is not None else {
        "payload.json",
        "receipt.json",
    }
    children = list(worker_root.iterdir())
    if {item.name for item in children} != expected_names or len(children) != len(
        expected_names
    ):
        raise ValueError(f"{run_id} worker inventory drifted")
    if any(not item.is_file() or item.is_symlink() for item in children):
        raise ValueError(f"{run_id} worker evidence must be ordinary files")
    payload_path = worker_root / "payload.json"
    payload = _mapping(load_json(payload_path, f"{run_id} payload"), "payload")
    expected_keys = {*_expected_payload_fields(run_id, controller), "worker_pid", "run"}
    if set(payload) != expected_keys:
        raise ValueError(f"{run_id} payload schema drifted")
    worker_pid = payload.get("worker_pid")
    if (
        isinstance(worker_pid, bool)
        or not isinstance(worker_pid, int)
        or worker_pid <= 0
        or worker_pid == controller["controller_pid"]
    ):
        raise ValueError(f"{run_id} worker PID is invalid")
    run = _mapping(payload.get("run"), f"{run_id} run")
    if set(run) != {"run_id", "solver_name", "repetition", "blocks"}:
        raise ValueError(f"{run_id} run schema drifted")
    for field in ("run_id", "solver_name", "repetition"):
        if run.get(field) != payload.get(field):
            raise ValueError(f"{run_id} run {field} drifted")
    payload_sha = _sha256(payload_path)
    if report is not None:
        if expected_process_pid is None or expected_exit_code is None:
            raise ValueError("live process observation is incomplete")
        expected_report = build_expected_worker_report(
            run_id=run_id,
            payload=payload,
            controller=controller,
            payload_sha256=payload_sha,
            observed_worker_pid=expected_process_pid,
            observed_returncode=expected_exit_code,
        )
        if dict(report) != expected_report:
            raise ValueError(f"{run_id} worker report drifted")
        return run, worker_pid, None, None

    receipt_path = worker_root / "receipt.json"
    receipt = _mapping(load_json(receipt_path, f"{run_id} receipt"), "receipt")
    expected_receipt_keys = {
        "schema",
        "run_id",
        "execution_index",
        "solver_name",
        "repetition",
        "worker_pid",
        "worker_parent_pid",
        "controller_pid",
        "controller_started_ns",
        "controller_nonce",
        "controller_identity_sha256",
        "controller_receipt_sha256",
        "v2_outer_sha256",
        "config_sha256",
        "runner_sha256",
        "semantic_authority_sha256",
        "worker_exit_code",
        "payload_sha256",
        "worker_report",
        "worker_report_sha256",
        "controller_receipt_sequence",
        "receipt_issued_ns",
        "previous_worker_receipt_sha256",
        "controller_validation_passed",
    }
    if set(receipt) != expected_receipt_keys:
        raise ValueError(f"{run_id} receipt schema drifted")
    receipt_issued_ns = receipt.get("receipt_issued_ns")
    if (
        isinstance(receipt_issued_ns, bool)
        or not isinstance(receipt_issued_ns, int)
        or receipt_issued_ns <= minimum_receipt_issued_ns
    ):
        raise ValueError(f"{run_id} controller receipt issue order drifted")
    expected_report = build_expected_worker_report(
        run_id=run_id,
        payload=payload,
        controller=controller,
        payload_sha256=payload_sha,
        observed_worker_pid=worker_pid,
        observed_returncode=0,
    )
    observed_report = _mapping(
        receipt.get("worker_report"), f"{run_id} stored worker report"
    )
    if observed_report != expected_report:
        raise ValueError(f"{run_id} nested worker report drifted")
    expected_receipt = {
        "schema": WORKER_RECEIPT_SCHEMA,
        "run_id": run_id,
        "execution_index": payload["execution_index"],
        "solver_name": payload["solver_name"],
        "repetition": payload["repetition"],
        "worker_pid": worker_pid,
        "worker_parent_pid": controller["controller_pid"],
        "controller_pid": controller["controller_pid"],
        "controller_started_ns": controller["controller_started_ns"],
        "controller_nonce": controller["controller_nonce"],
        "controller_identity_sha256": controller["controller_identity_sha256"],
        "controller_receipt_sha256": controller["receipt_sha256"],
        "v2_outer_sha256": controller["v2_outer_sha256"],
        "config_sha256": controller["config_sha256"],
        "runner_sha256": controller["runner_sha256"],
        "semantic_authority_sha256": controller["semantic_authority_sha256"],
        "worker_exit_code": 0,
        "payload_sha256": payload_sha,
        "worker_report": expected_report,
        "worker_report_sha256": _sha256_bytes(
            _canonical_json_bytes(expected_report)
        ),
        "controller_receipt_sequence": payload["execution_index"],
        "receipt_issued_ns": receipt_issued_ns,
        "previous_worker_receipt_sha256": expected_previous_receipt_sha256,
        "controller_validation_passed": True,
    }
    if receipt != expected_receipt:
        raise ValueError(f"{run_id} durable receipt drifted")
    return run, worker_pid, _sha256(receipt_path), receipt_issued_ns


def _publish_worker_receipt(
    worker_root: Path,
    run_id: str,
    controller: Mapping[str, Any],
    report: Mapping[str, Any],
    *,
    process_pid: int,
    process_returncode: int,
    previous_worker_receipt_sha256: str | None,
    previous_receipt_issued_ns: int,
) -> dict[str, object]:
    _validate_worker_directory(
        worker_root,
        run_id,
        controller,
        expected_process_pid=process_pid,
        expected_exit_code=process_returncode,
        report=report,
    )
    payload_path = worker_root / "payload.json"
    payload = _mapping(
        _load_json_strict(payload_path, f"{run_id} payload"), "payload"
    )
    expected_report = build_expected_worker_report(
        run_id=run_id,
        payload=payload,
        controller=controller,
        payload_sha256=_sha256(payload_path),
        observed_worker_pid=process_pid,
        observed_returncode=process_returncode,
    )
    receipt = {
        "schema": WORKER_RECEIPT_SCHEMA,
        "run_id": run_id,
        "execution_index": payload["execution_index"],
        "solver_name": payload["solver_name"],
        "repetition": payload["repetition"],
        "worker_pid": process_pid,
        "worker_parent_pid": controller["controller_pid"],
        "controller_pid": controller["controller_pid"],
        "controller_started_ns": controller["controller_started_ns"],
        "controller_nonce": controller["controller_nonce"],
        "controller_identity_sha256": controller["controller_identity_sha256"],
        "controller_receipt_sha256": controller["receipt_sha256"],
        "v2_outer_sha256": controller["v2_outer_sha256"],
        "config_sha256": controller["config_sha256"],
        "runner_sha256": controller["runner_sha256"],
        "semantic_authority_sha256": controller["semantic_authority_sha256"],
        "worker_exit_code": 0,
        "payload_sha256": _sha256(payload_path),
        "worker_report": expected_report,
        "worker_report_sha256": _sha256_bytes(
            _canonical_json_bytes(expected_report)
        ),
        "controller_receipt_sequence": payload["execution_index"],
        "receipt_issued_ns": max(time.time_ns(), previous_receipt_issued_ns + 1),
        "previous_worker_receipt_sha256": previous_worker_receipt_sha256,
        "controller_validation_passed": True,
    }
    _write_json_atomic(worker_root / "receipt.json", receipt)
    return receipt


def _dispatch_worker(
    config_path: Path,
    *,
    run_id: str,
    worker_root: Path,
    controller: Mapping[str, Any],
    controller_receipt_path: Path,
    python_executable: Path,
    watchdog_seconds: int,
    execution_index: int,
    previous_worker_receipt_sha256: str | None,
    previous_receipt_issued_ns: int,
) -> dict[str, object]:
    command = [
        str(python_executable),
        "-m",
        MODULE,
        "--config",
        str(config_path),
        "--worker",
        "--run-id",
        run_id,
        "--worker-output",
        str(worker_root),
        "--controller-receipt",
        str(controller_receipt_path),
        "--expected-parent-pid",
        str(controller["controller_pid"]),
        "--expected-execution-index",
        str(execution_index),
        "--expected-controller-receipt-sha256",
        str(controller["receipt_sha256"]),
    ]
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    try:
        stdout, stderr = process.communicate(timeout=watchdog_seconds)
    except subprocess.TimeoutExpired as error:
        process.kill()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired as termination_error:
            raise RuntimeError(
                f"worker {run_id} timeout termination is unconfirmed; no result "
                "may publish and this is not infeasibility evidence"
            ) from termination_error
        if process.poll() is None or process.returncode is None:
            raise RuntimeError(
                f"worker {run_id} termination has no confirmed return code"
            ) from error
        raise TimeoutError(
            f"worker {run_id} exceeded the external watchdog; timeout is not "
            "infeasibility evidence"
        ) from error
    if process.poll() is None or process.returncode is None:
        raise RuntimeError(f"worker {run_id} exit is unconfirmed")
    if process.returncode != 0:
        raise RuntimeError(
            f"worker {run_id} failed with exit code {process.returncode}; "
            f"unresolved/error is not infeasibility; stderr={stderr!r}"
        )
    report = _mapping(
        _load_json_strict_text(stdout, f"worker {run_id} report"), "worker report"
    )
    return _publish_worker_receipt(
        worker_root,
        run_id,
        controller,
        report,
        process_pid=process.pid,
        process_returncode=process.returncode,
        previous_worker_receipt_sha256=previous_worker_receipt_sha256,
        previous_receipt_issued_ns=previous_receipt_issued_ns,
    )


def _validate_controller(
    result_root: Path,
    config: Mapping[str, Any],
    load_json: Callable[[Path, str], Any],
) -> dict[str, Any]:
    path = result_root / "controller_receipt.json"
    if not path.is_file() or path.is_symlink():
        raise ValueError("controller receipt must be an ordinary file")
    receipt = _mapping(load_json(path, "controller receipt"), "controller receipt")
    expected_keys = {
        "schema",
        "controller_pid",
        "controller_started_ns",
        "controller_nonce",
        "controller_identity_sha256",
        "v2_outer_sha256",
        "config_sha256",
        "runner_sha256",
        "semantic_authority_sha256",
        "execution_order",
        "process_evidence_scope",
    }
    if set(receipt) != expected_keys:
        raise ValueError("controller receipt schema drifted")
    pid = receipt.get("controller_pid")
    started = receipt.get("controller_started_ns")
    nonce = receipt.get("controller_nonce")
    if (
        receipt.get("schema") != CONTROLLER_SCHEMA
        or isinstance(pid, bool)
        or not isinstance(pid, int)
        or pid <= 0
        or isinstance(started, bool)
        or not isinstance(started, int)
        or started <= 0
        or not isinstance(nonce, str)
        or len(nonce) != 64
        or any(character not in "0123456789abcdef" for character in nonce)
        or receipt.get("controller_identity_sha256") != _controller_identity(receipt)
        or receipt.get("v2_outer_sha256") != V2_OUTER_SHA256
        or receipt.get("config_sha256") != _sha256(CONFIG)
        or receipt.get("runner_sha256") != _sha256(Path(__file__))
        or receipt.get("semantic_authority_sha256")
        != config["semantic_authority"]["manifest_sha256"]
        or receipt.get("execution_order") != EXPECTED_RUNS
        or receipt.get("process_evidence_scope") != PROCESS_EVIDENCE_SCOPE
    ):
        raise ValueError("controller receipt authority drifted")
    receipt["receipt_sha256"] = _sha256(path)
    return receipt


def _reconstruct_runs(
    result_root: Path,
    config: Mapping[str, Any],
    *,
    load_json: Callable[[Path, str], Any] = _load_json_strict,
) -> tuple[list[dict[str, object]], list[int], dict[str, Any]]:
    controller = _validate_controller(result_root, config, load_json)
    workers = result_root / "workers"
    if not workers.is_dir() or workers.is_symlink():
        raise ValueError("workers root must be an ordinary directory")
    entries = list(workers.iterdir())
    if {item.name for item in entries} != set(EXPECTED_RUNS) or len(entries) != 4:
        raise ValueError("durable worker directory inventory drifted")
    runs: list[dict[str, object]] = []
    pids: list[int] = []
    previous_receipt_sha256: str | None = None
    previous_receipt_issued_ns = int(controller["controller_started_ns"])
    for run_id in EXPECTED_RUNS:
        run, pid, receipt_sha256, receipt_issued_ns = _validate_worker_directory(
            workers / run_id,
            run_id,
            controller,
            load_json=load_json,
            expected_previous_receipt_sha256=previous_receipt_sha256,
            minimum_receipt_issued_ns=previous_receipt_issued_ns,
        )
        if receipt_sha256 is None or receipt_issued_ns is None:
            raise ValueError(f"{run_id} durable receipt chain is incomplete")
        runs.append(run)
        pids.append(pid)
        previous_receipt_sha256 = receipt_sha256
        previous_receipt_issued_ns = receipt_issued_ns
    if len(set(pids)) != 4:
        raise ValueError("each run must have a unique fresh worker PID")
    return runs, pids, controller


def _assert_evaluator_report(report: object) -> dict[str, object]:
    observed = _mapping(report, "semantic evaluator report")
    if observed != EXPECTED_EVALUATOR_REPORT:
        raise ValueError("semantic evaluator report contract drifted")
    return observed


def _result_manifest(staging: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for path in sorted(staging.rglob("*")):
        if path.name == "SHA256SUMS.json":
            continue
        if path.is_symlink():
            raise ValueError("result tree contains a symlink")
        if path.is_file():
            manifest[path.relative_to(staging).as_posix()] = _sha256(path)
        elif not path.is_dir():
            raise ValueError("result tree contains a non-ordinary member")
    return manifest


def _write_result(
    staging: Path, config_path: Path, config: Mapping[str, Any]
) -> dict[str, object]:
    runs, worker_pids, controller = _reconstruct_runs(staging, config)
    semantic_config = _mapping(
        yaml.safe_load(SEMANTIC_CONFIG.read_text(encoding="utf-8")),
        "semantic successor config",
    )
    evaluator_report = _assert_evaluator_report(evaluate_runs(semantic_config, runs))
    semantic_validation = {
        "schema": SEMANTIC_VALIDATION_SCHEMA,
        "semantic_successor_config_sha256": _sha256(SEMANTIC_CONFIG),
        "semantic_authority_sha256": config["semantic_authority"][
            "manifest_sha256"
        ],
        "v2_outer_sha256": V2_OUTER_SHA256,
        "evaluator_report": evaluator_report,
        "fresh_execution_run_ids": EXPECTED_RUNS,
        "fresh_worker_pids": worker_pids,
        "controller_identity_sha256": controller["controller_identity_sha256"],
        "controller_receipt_sha256": controller["receipt_sha256"],
        "durable_process_provenance_verified": True,
        "nested_worker_reports_reconstructed_independently": True,
        "runs_reconstructed_exactly_from_worker_payloads": True,
        "process_evidence_scope": PROCESS_EVIDENCE_SCOPE,
        "semantic_contract_passed": True,
        "cross_solver_confirmation_completed": True,
        "formal_grid_execution_started": False,
        "security_certified": False,
    }
    summary = {
        "schema": RESULT_SCHEMA,
        "config_sha256": _sha256(config_path),
        "runner_sha256": _sha256(Path(__file__)),
        "semantic_authority_sha256": config["semantic_authority"][
            "manifest_sha256"
        ],
        "v2_outer_sha256": V2_OUTER_SHA256,
        "fresh_execution_status": "passed",
        "fresh_execution_passed": True,
        "fresh_execution_failed": False,
        "run_count": 4,
        "unique_worker_process_count": 4,
        "durable_process_provenance_verified": True,
        "nested_worker_reports_reconstructed_independently": True,
        "runs_reconstructed_exactly_from_worker_payloads": True,
        "semantic_contract_passed": True,
        "cross_solver_confirmation_completed": True,
        "formal_grid_execution_started": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    shutil.copyfile(config_path, staging / "config.yaml")
    _write_json_atomic(staging / "runs.json", runs)
    _write_json_atomic(staging / "semantic_validation.json", semantic_validation)
    _write_json_atomic(staging / "summary.json", summary)
    _write_json_atomic(staging / "SHA256SUMS.json", _result_manifest(staging))
    return summary


def _python_authority(scientific: Mapping[str, Any]) -> Path:
    authority = _mapping(
        scientific["execution"]["python_authority"], "Python authority"
    )
    variable = str(authority["environment_variable"])
    raw = os.environ.get(variable)
    if not raw:
        raise RuntimeError(f"{variable} must identify the executor Python")
    path = Path(raw)
    if (
        not path.is_absolute()
        or not path.is_file()
        or path.is_symlink()
        or path.resolve() != Path(sys.executable).resolve()
    ):
        raise RuntimeError("executor Python authority is not the current ordinary file")
    return path.resolve()


def run(
    config_path: Path = CONFIG, *, validate_only: bool = False
) -> dict[str, object]:
    from experiments.validate_rq2_public_solver_confirmatory_pilot_v3 import validate

    preflight = validate(config_path)
    if validate_only:
        return preflight
    config = _load_config(config_path)
    scientific = _load_scientific_parent(config)
    target = ROOT / str(config["output"]["directory"])
    if target.exists():
        raise FileExistsError(f"refusing to overwrite v3 output: {target}")
    _require_execution_gate(config)
    require_execution_host(scientific["execution"])
    python_executable = _python_authority(scientific)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{target.name}.staging.", dir=target.parent)
    )
    try:
        workers = staging / "workers"
        workers.mkdir()
        controller = _create_controller_receipt(staging, config)
        controller["receipt_sha256"] = _sha256(staging / "controller_receipt.json")
        previous_receipt_sha256: str | None = None
        previous_receipt_issued_ns = int(controller["controller_started_ns"])
        for execution_index, run_id in enumerate(EXPECTED_RUNS, start=1):
            worker_root = workers / run_id
            worker_root.mkdir()
            receipt = _dispatch_worker(
                config_path,
                run_id=run_id,
                worker_root=worker_root.resolve(),
                controller=controller,
                controller_receipt_path=(staging / "controller_receipt.json").resolve(),
                python_executable=python_executable,
                watchdog_seconds=int(
                    scientific["execution"]["external_watchdog_seconds"]
                ),
                execution_index=execution_index,
                previous_worker_receipt_sha256=previous_receipt_sha256,
                previous_receipt_issued_ns=previous_receipt_issued_ns,
            )
            previous_receipt_sha256 = _sha256(worker_root / "receipt.json")
            previous_receipt_issued_ns = int(receipt["receipt_issued_ns"])
        summary = _write_result(staging, config_path, config)
        if target.exists():
            raise FileExistsError("v3 output appeared before atomic publication")
        staging.rename(target)
    except Exception:
        try:
            shutil.rmtree(staging)
        except OSError as cleanup_error:
            raise RuntimeError(
                f"v3 staging cleanup could not be confirmed: {staging}"
            ) from cleanup_error
        raise
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--run-id", help=argparse.SUPPRESS)
    parser.add_argument("--worker-output", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--controller-receipt", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--expected-parent-pid", type=int, help=argparse.SUPPRESS)
    parser.add_argument(
        "--expected-execution-index", type=int, help=argparse.SUPPRESS
    )
    parser.add_argument(
        "--expected-controller-receipt-sha256", help=argparse.SUPPRESS
    )
    args = parser.parse_args()
    if args.worker:
        if (
            not args.run_id
            or args.worker_output is None
            or args.controller_receipt is None
            or args.expected_parent_pid is None
            or args.expected_execution_index is None
            or not args.expected_controller_receipt_sha256
            or args.validate_only
        ):
            parser.error("incomplete or invalid internal worker arguments")
        report = _execute_worker(
            args.config,
            run_id=args.run_id,
            worker_root=args.worker_output.resolve(),
            controller_receipt_path=args.controller_receipt.resolve(),
            expected_parent_pid=args.expected_parent_pid,
            expected_execution_index=args.expected_execution_index,
            expected_controller_receipt_sha256=(
                args.expected_controller_receipt_sha256
            ),
        )
        print(json.dumps(report, sort_keys=True))
        return
    print(json.dumps(run(args.config, validate_only=args.validate_only), indent=2))


if __name__ == "__main__":
    main()
