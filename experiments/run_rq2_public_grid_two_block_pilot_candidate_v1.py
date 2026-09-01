"""Closed, reviewable candidate for the RQ2 0008/0009 process pilot.

The canonical candidate cannot execute.  A later versioned execution successor
must bind this candidate's outer manifest and an independent pre-run PASS
receipt.  Both controller and hidden-worker paths check that authority before
scientific preflight, data loading, or solver dispatch.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from experiments import (
    run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_v1 as recovery,
)
from src.evaluation.execution_machine import (
    execution_host_status,
    require_execution_host,
)
from src.grid.rts_gmlc import load_rts_gmlc_chronological_data

ROOT = Path(__file__).resolve().parents[1]
MODULE = "experiments.run_rq2_public_grid_two_block_pilot_candidate_v1"
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v1.yaml"
ACTIVATION = ROOT / "configs/rq2_public_grid_two_block_pilot_user_activation_v1.yaml"
PASS_RECEIPT = (
    ROOT / "configs/rq2_public_grid_solver_recovery_implementation_review_pass_v2.yaml"
)
BUNDLE = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v1.SHA256SUMS.json"
OUTER = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v1.OUTER.SHA256SUMS.json"
BASE_CONFIG = (
    ROOT / "configs/rts_gmlc_public_grid_need_dispatch_v4_highs_process_isolated_v1.yaml"
)
SEMANTIC_CONFIG = ROOT / "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml"
SEMANTIC_MANIFEST = (
    ROOT / "configs/rq2_public_solver_pilot_semantic_successor_v1.SHA256SUMS.json"
)
Gurobi_CONFIG = ROOT / "results/execution_configs/rq2_public_successor_v2/grid.yaml"
Gurobi_0008 = (
    ROOT
    / "results/checkpoints/rts_gmlc_public_grid_need_dispatch_v4_gurobi/holdout_s20260822_0008.json"
)

BLOCKS = ["holdout_s20260822_0008", "holdout_s20260822_0009"]
CONFIG_SCHEMA = "rq2_public_grid_two_block_pilot_candidate_v1"
REQUEST_SCHEMA = "rq2_public_grid_two_block_pilot_worker_request_candidate_v1"
RESULT_SCHEMA = "rq2_public_grid_two_block_pilot_worker_result_candidate_v1"
RECEIPT_SCHEMA = "rq2_public_grid_two_block_pilot_worker_receipt_candidate_v1"
CONTROLLER_SCHEMA = "rq2_public_grid_two_block_pilot_controller_receipt_candidate_v1"
PILOT_RESULT_SCHEMA = "rq2_public_grid_two_block_pilot_result_v1"

BUNDLE_INVENTORY = {
    "configs/rq2_public_grid_solver_recovery_implementation_review_pass_v2.yaml",
    "configs/rq2_public_grid_two_block_pilot_user_activation_v1.yaml",
    "configs/rq2_public_grid_two_block_pilot_candidate_v1.yaml",
    "experiments/run_rq2_public_grid_two_block_pilot_candidate_v1.py",
    "experiments/validate_rq2_public_grid_two_block_pilot_candidate_v1.py",
    "tests/test_rq2_public_grid_two_block_pilot_candidate_v1.py",
}


def _load_yaml(path: Path, label: str) -> dict[str, Any]:
    return recovery._load_yaml_mapping(path, label)


def _load_json(path: Path, label: str) -> Any:
    return recovery._load_json_strict(path, label)


def _verify_bundle_chain() -> dict[str, str]:
    bundle = recovery._mapping(_load_json(BUNDLE, "candidate bundle"), "bundle")
    if bundle.get("schema") != "rq2_public_grid_two_block_pilot_candidate_bundle_v1":
        raise ValueError("candidate bundle schema drifted")
    files = recovery._mapping(bundle.get("files"), "candidate bundle files")
    if set(files) != BUNDLE_INVENTORY:
        raise ValueError("candidate bundle inventory drifted")
    for relative, expected in files.items():
        path = ROOT / relative
        if (
            not recovery._is_sha256(expected)
            or not path.is_file()
            or path.is_symlink()
            or recovery._sha256(path) != expected
        ):
            raise ValueError(f"candidate bundle member drifted: {relative}")
    outer = recovery._mapping(_load_json(OUTER, "candidate outer"), "outer")
    if outer != {
        "schema": "rq2_public_grid_two_block_pilot_candidate_outer_v1",
        "files": {
            "configs/rq2_public_grid_two_block_pilot_candidate_v1.SHA256SUMS.json": recovery._sha256(BUNDLE)
        },
    }:
        raise ValueError("candidate outer manifest drifted")
    return {str(key): str(value) for key, value in files.items()}


def _load_authority() -> tuple[dict[str, Any], dict[str, Any]]:
    files = _verify_bundle_chain()
    config = _load_yaml(CONFIG, "candidate config")
    activation = _load_yaml(ACTIVATION, "candidate activation")
    if config.get("schema") != CONFIG_SCHEMA:
        raise ValueError("candidate config schema drifted")
    if files[CONFIG.relative_to(ROOT).as_posix()] != recovery._sha256(CONFIG):
        raise ValueError("candidate config hash authority drifted")
    if activation.get("candidate_authority", {}).get("config_sha256") != recovery._sha256(CONFIG):
        raise ValueError("candidate activation config binding drifted")
    receipt = _load_yaml(PASS_RECEIPT, "recovery implementation PASS receipt")
    recovery_authority = recovery._mapping(
        config.get("recovery_implementation_authority"), "recovery authority"
    )
    if (
        receipt.get("schema")
        != "rq2_public_grid_solver_recovery_implementation_review_pass_v2"
        or receipt.get("reviewer_role") != "independent_sol_reviewer"
        or receipt.get("verdict") != "PASS"
        or recovery_authority.get("pass_receipt_sha256")
        != recovery._sha256(PASS_RECEIPT)
        or recovery_authority.get("recovery_bundle_sha256")
        != "b300a040fc481beea094702404f4d00eb176403e40f7909d2d704f7fd2195729"
    ):
        raise ValueError("recovery implementation PASS authority drifted")
    return config, activation


def _execution_authority_status(
    config: Mapping[str, Any], activation: Mapping[str, Any]
) -> dict[str, bool]:
    gates = recovery._mapping(config.get("gates"), "candidate gates")
    activation_gates = recovery._mapping(
        activation.get("gates"), "activation gates"
    )
    return {
        "canonical_candidate": CONFIG.is_file() and not CONFIG.is_symlink(),
        "recovery_implementation_passed": (
            gates.get("recovery_v2_implementation_review_passed") is True
            and activation_gates.get("recovery_v2_implementation_review_passed")
            is True
        ),
        "user_pilot_authorized": (
            gates.get("user_two_block_pilot_authorized") is True
            and activation_gates.get("user_two_block_pilot_authorized") is True
        ),
        "independent_pre_run_review_passed": (
            gates.get("independent_pre_run_review_passed") is True
            and activation_gates.get("independent_pre_run_review_passed") is True
            and activation.get("candidate_authority", {}).get(
                "pre_run_review_receipt_path"
            )
            is not None
        ),
        "execution_successor_present": (
            gates.get("execution_successor_present") is True
            and activation_gates.get("execution_successor_present") is True
        ),
        "two_block_pilot_execution_ready": (
            gates.get("two_block_pilot_execution_ready") is True
            and activation_gates.get("two_block_pilot_execution_ready") is True
        ),
        "formal_execution_closed": (
            gates.get("formal_execution_ready") is False
            and gates.get("user_formal_run_authorized") is False
            and activation_gates.get("formal_execution_ready") is False
        ),
        "claims_closed": (
            gates.get("formal_result_exists") is False
            and gates.get("claim") is False
            and gates.get("security_certified") is False
        ),
    }


def _require_execution_authority() -> tuple[dict[str, Any], dict[str, Any]]:
    """Fail before scientific preflight or data loading for the closed candidate."""

    config, activation = _load_authority()
    status = _execution_authority_status(config, activation)
    failed = [name for name, passed in status.items() if not passed]
    if failed:
        raise RuntimeError("candidate pilot execution authority is closed: " + ", ".join(failed))
    base = _load_yaml(BASE_CONFIG, "scientific source config")
    require_execution_host(base["execution"])
    return config, activation


def _stage_context() -> dict[str, Any]:
    context = recovery._stage_context(BASE_CONFIG)
    for block_id in BLOCKS:
        if block_id not in context["blocks"] or len(context["blocks"][block_id]) != 24:
            raise ValueError(f"pilot block inventory drifted: {block_id}")
    return context


def _implementation_bindings() -> dict[str, dict[str, str]]:
    bindings = {
        "pilot_parent_runner": Path(__file__).resolve(),
        "pilot_worker_runner": Path(__file__).resolve(),
    }
    result = {
        name: {"path": path.relative_to(ROOT).as_posix(), "sha256": recovery._sha256(path)}
        for name, path in bindings.items()
    }
    result.update({f"recovery_{key}": value for key, value in recovery._implementation_bindings().items()})
    return result


def _pilot_roots(config: Mapping[str, Any]) -> dict[str, Path]:
    paths = recovery._mapping(config.get("paths"), "pilot paths")
    roots = {
        "result": recovery._resolve(paths["result_directory"], "pilot result"),
        "worker": recovery._resolve(paths["worker_staging_directory"], "pilot worker"),
        "log": recovery._resolve(paths["attempt_log_directory"], "pilot log"),
    }
    formal = recovery._mapping(
        config.get("immutable_formal_authority"), "formal authority"
    )
    formal_roots = {
        "gurobi_checkpoint": recovery._resolve(
            formal["gurobi_checkpoint_directory"], "Gurobi checkpoint"
        ),
        "gurobi_output": recovery._resolve(
            formal["gurobi_output_directory"], "Gurobi output"
        ),
        "recovery_checkpoint": recovery._resolve(
            formal["recovery_checkpoint_directory"], "recovery checkpoint"
        ),
        "recovery_output": recovery._resolve(
            formal["recovery_output_directory"], "recovery output"
        ),
    }
    combined = {**roots, **formal_roots}
    for left_name, left in combined.items():
        for right_name, right in combined.items():
            if left_name >= right_name:
                continue
            if recovery._same_or_descendant(left, right) or recovery._same_or_descendant(right, left):
                raise ValueError(f"pilot/formal roots overlap: {left_name}, {right_name}")
    tables = ROOT / "results/tables"
    if tables.is_dir():
        for existing in tables.iterdir():
            if existing.resolve() == roots["result"]:
                continue
            if recovery._same_or_descendant(roots["result"], existing) or recovery._same_or_descendant(existing, roots["result"]):
                raise ValueError(f"pilot result overlaps existing result: {existing}")
    return roots


def _formal_snapshot(config: Mapping[str, Any]) -> dict[str, object]:
    authority = recovery._mapping(
        config.get("immutable_formal_authority"), "formal authority"
    )
    for path_key, hash_key in (
        ("formal_runner_path", "formal_runner_sha256"),
        ("activated_gurobi_config_path", "activated_gurobi_config_sha256"),
    ):
        path = recovery._resolve(authority[path_key], path_key)
        if not path.is_file() or path.is_symlink() or recovery._sha256(path) != authority[hash_key]:
            raise ValueError(f"immutable formal authority drifted: {path_key}")
    checkpoint_root = recovery._resolve(
        authority["gurobi_checkpoint_directory"], "Gurobi checkpoint root"
    )
    observed = {
        path.name: recovery._sha256(path)
        for path in checkpoint_root.iterdir()
        if path.is_file() and not path.is_symlink()
    }
    if observed != authority["checkpoint_sha256"] or len(observed) != 9:
        raise ValueError("immutable nine-checkpoint inventory drifted")
    root_states: dict[str, object] = {}
    for key in (
        "gurobi_checkpoint_directory",
        "gurobi_output_directory",
        "recovery_checkpoint_directory",
        "recovery_output_directory",
    ):
        path = recovery._resolve(authority[key], key)
        if key != "gurobi_checkpoint_directory" and path.exists():
            raise ValueError(f"formal root unexpectedly exists: {key}")
        root_states[key] = {
            "path": path.relative_to(ROOT).as_posix(),
            "exists": path.exists(),
            "inventory": observed if key == "gurobi_checkpoint_directory" else {},
        }
    return {
        "formal_runner_sha256": authority["formal_runner_sha256"],
        "activated_gurobi_config_sha256": authority["activated_gurobi_config_sha256"],
        "formal_roots": root_states,
    }


def _controller_receipt(config: Mapping[str, Any]) -> dict[str, object]:
    receipt: dict[str, object] = {
        "schema": CONTROLLER_SCHEMA,
        "controller_pid": os.getpid(),
        "controller_started_ns": time.time_ns(),
        "controller_nonce": secrets.token_hex(32),
        "config_sha256": recovery._sha256(CONFIG),
        "activation_sha256": recovery._sha256(ACTIVATION),
        "pass_receipt_sha256": recovery._sha256(PASS_RECEIPT),
        "bundle_sha256": recovery._sha256(BUNDLE),
        "outer_sha256": recovery._sha256(OUTER),
        "implementation": _implementation_bindings(),
        "solver": recovery._solver_binding(_load_yaml(BASE_CONFIG, "base config")),
        "execution_order": BLOCKS,
        "formal_snapshot_before": _formal_snapshot(config),
        "parent_solver_calls": 0,
    }
    return receipt


def _python_authority(base: Mapping[str, Any]) -> Path:
    return recovery._python_authority(base)


def _build_request(
    context: Mapping[str, Any],
    *,
    block_id: str,
    controller: Mapping[str, Any],
    python: Path,
    result_path: Path,
) -> dict[str, object]:
    return {
        "schema": REQUEST_SCHEMA,
        "block_id": block_id,
        "execution_index": BLOCKS.index(block_id) + 1,
        "block_input_sha256": recovery._block_input_sha256(context["blocks"][block_id]),
        "config_sha256": recovery._sha256(CONFIG),
        "activation_sha256": recovery._sha256(ACTIVATION),
        "pass_receipt_sha256": recovery._sha256(PASS_RECEIPT),
        "bundle_sha256": recovery._sha256(BUNDLE),
        "outer_sha256": recovery._sha256(OUTER),
        "scientific_config_path": str(BASE_CONFIG.resolve()),
        "scientific_config_sha256": recovery._sha256(BASE_CONFIG),
        "stage": recovery.STAGE,
        "stage_base_provenance_sha256": context["stage_base_sha256"],
        "parent_pid": controller["controller_pid"],
        "parent_dispatch_started_ns": time.time_ns(),
        "controller_nonce": controller["controller_nonce"],
        "controller_receipt_sha256": controller["receipt_sha256"],
        "nonce": secrets.token_hex(32),
        "python_executable": str(python),
        "python_executable_sha256": recovery._sha256(python),
        "execution_host": execution_host_status(context["config"]["execution"]),
        "implementation": _implementation_bindings(),
        "solver": recovery._solver_binding(context["config"]),
        "worker_result_path": str(result_path.resolve()),
    }


def _result_authority(request: Mapping[str, Any]) -> dict[str, object]:
    return {
        key: request[key]
        for key in (
            "block_id",
            "execution_index",
            "block_input_sha256",
            "config_sha256",
            "activation_sha256",
            "pass_receipt_sha256",
            "bundle_sha256",
            "outer_sha256",
            "scientific_config_sha256",
            "stage",
            "stage_base_provenance_sha256",
            "parent_pid",
            "parent_dispatch_started_ns",
            "controller_nonce",
            "controller_receipt_sha256",
            "nonce",
            "python_executable",
            "python_executable_sha256",
            "execution_host",
            "implementation",
            "solver",
        )
    }


def _validate_request(request: Mapping[str, Any], request_path: Path) -> dict[str, Any]:
    expected_keys = {
        "schema", "block_id", "execution_index", "block_input_sha256",
        "config_sha256", "activation_sha256", "pass_receipt_sha256",
        "bundle_sha256", "outer_sha256", "scientific_config_path",
        "scientific_config_sha256", "stage", "stage_base_provenance_sha256",
        "parent_pid", "parent_dispatch_started_ns", "controller_nonce", "nonce",
        "controller_receipt_sha256",
        "python_executable", "python_executable_sha256", "execution_host",
        "implementation", "solver", "worker_result_path",
    }
    if set(request) != expected_keys or request.get("schema") != REQUEST_SCHEMA:
        raise ValueError("pilot worker request schema drifted")
    _require_execution_authority()
    block_id = str(request.get("block_id"))
    if block_id not in BLOCKS or request.get("execution_index") != BLOCKS.index(block_id) + 1:
        raise ValueError("pilot worker block identity drifted")
    parent_pid = request.get("parent_pid")
    if isinstance(parent_pid, bool) or not isinstance(parent_pid, int) or parent_pid <= 0 or os.getppid() != parent_pid:
        raise ValueError("pilot worker parent identity drifted")
    for key in ("controller_nonce", "nonce"):
        if not recovery._is_sha256(request.get(key)):
            raise ValueError(f"pilot worker {key} drifted")
    python = Path(str(request["python_executable"]))
    if (
        not python.is_file() or python.is_symlink()
        or python.resolve() != Path(sys.executable).resolve()
        or recovery._sha256(python) != request["python_executable_sha256"]
    ):
        raise ValueError("pilot worker Python identity drifted")
    expected_hashes = {
        "config_sha256": recovery._sha256(CONFIG),
        "activation_sha256": recovery._sha256(ACTIVATION),
        "pass_receipt_sha256": recovery._sha256(PASS_RECEIPT),
        "bundle_sha256": recovery._sha256(BUNDLE),
        "outer_sha256": recovery._sha256(OUTER),
        "scientific_config_sha256": recovery._sha256(BASE_CONFIG),
    }
    if any(request.get(key) != value for key, value in expected_hashes.items()):
        raise ValueError("pilot worker hash authority drifted")
    result_path = Path(str(request["worker_result_path"])).resolve()
    if result_path.parent != request_path.resolve().parent or result_path.exists():
        raise ValueError("pilot worker result path is not a fresh isolated sibling")
    context = _stage_context()
    if (
        request.get("stage") != recovery.STAGE
        or request.get("stage_base_provenance_sha256") != context["stage_base_sha256"]
        or request.get("block_input_sha256")
        != recovery._block_input_sha256(context["blocks"][block_id])
        or request.get("implementation") != _implementation_bindings()
        or request.get("solver") != recovery._solver_binding(context["config"])
        or request.get("execution_host")
        != execution_host_status(context["config"]["execution"])
    ):
        raise ValueError("pilot worker scientific or implementation authority drifted")
    return context


def _worker(request_path: Path) -> int:
    started_ns = time.time_ns()
    request_path = request_path.resolve()
    request = recovery._mapping(_load_json(request_path, "pilot request"), "request")
    context = _validate_request(request, request_path)
    block_id = str(request["block_id"])
    data = load_rts_gmlc_chronological_data(
        context["grid_root"], base_mva=float(context["config"]["grid_source"]["base_mva"])
    )
    payload = recovery.v4._process_block(
        data,
        context["blocks"][block_id],
        dc_bus=int(context["config"]["model"]["dc_bus"]),
        dc_demand_mw=float(context["config"]["model"]["dc_reference_demand_mw"]),
        solver=context["config"]["solver"],
    )
    resolved = payload.get("all_hours_resolved") is True
    result = {
        "schema": RESULT_SCHEMA,
        "status": "complete" if resolved else "unresolved",
        **_result_authority(request),
        "request_sha256": recovery._sha256(request_path),
        "worker_pid": os.getpid(),
        "worker_parent_pid": os.getppid(),
        "worker_started_ns": started_ns,
        "scientific_payload": payload,
        "scientific_payload_sha256": recovery._canonical_sha256(payload),
        "all_hours_resolved": resolved,
        "mathematical_infeasibility_inferred_from_failure": False,
    }
    recovery._atomic_json(Path(str(request["worker_result_path"])), result)
    return 0 if resolved else 3


def _validate_worker_result(
    request: Mapping[str, Any],
    result: Mapping[str, Any],
    *,
    request_path: Path,
    observed_pid: int,
    observed_exit_code: int,
    context: Mapping[str, Any],
) -> dict[str, Any]:
    expected_keys = {
        "schema", "status", "request_sha256", "worker_pid", "worker_parent_pid",
        "worker_started_ns", "scientific_payload",
        "scientific_payload_sha256", "all_hours_resolved",
        "mathematical_infeasibility_inferred_from_failure",
        *_result_authority(request),
    }
    if set(result) != expected_keys or result.get("schema") != RESULT_SCHEMA:
        raise ValueError("pilot worker result schema drifted")
    expected = {
        "status": "complete",
        **_result_authority(request),
        "request_sha256": recovery._sha256(request_path),
        "worker_pid": observed_pid, "worker_parent_pid": request["parent_pid"],
        "all_hours_resolved": True,
        "mathematical_infeasibility_inferred_from_failure": False,
    }
    started = result.get("worker_started_ns")
    published_request = recovery._mapping(
        _load_json(request_path, "published pilot request"), "published request"
    )
    if published_request != dict(request):
        raise ValueError("published pilot request drifted after dispatch")
    if (
        observed_exit_code != 0
        or observed_pid == request["parent_pid"]
        or any(result.get(key) != value for key, value in expected.items())
        or isinstance(started, bool) or not isinstance(started, int)
        or started < request["parent_dispatch_started_ns"] or started > time.time_ns()
    ):
        raise ValueError("pilot worker process or authority drifted")
    block_id = str(request["block_id"])
    payload = recovery._validate_scientific_payload(
        recovery._mapping(result["scientific_payload"], "pilot payload"),
        block_id=block_id,
        expected_block=context["blocks"][block_id],
        config=context["config"],
    )
    if result["scientific_payload_sha256"] != recovery._canonical_sha256(payload):
        raise ValueError("pilot scientific payload hash drifted")
    return payload


def _receipt(
    request: Mapping[str, Any], result: Mapping[str, Any], *, request_path: Path,
    result_path: Path, observed_pid: int
) -> dict[str, object]:
    return {
        "schema": RECEIPT_SCHEMA,
        **_result_authority(request),
        "request_sha256": recovery._sha256(request_path),
        "worker_payload_sha256": recovery._sha256(result_path),
        "worker_pid": observed_pid,
        "worker_parent_pid": request["parent_pid"],
        "worker_started_ns": result["worker_started_ns"],
        "worker_exit_code": 0,
        "all_hours_resolved": True,
        "controller_validation_passed": True,
        "published_by_controller": True,
        "mathematical_infeasibility_inferred_from_failure": False,
    }


def _dispatch_one(
    context: Mapping[str, Any], *, block_id: str, controller: Mapping[str, Any],
    python: Path, roots: Mapping[str, Path]
) -> tuple[dict[str, Any], Path, Path]:
    nonce = secrets.token_hex(32)
    attempt = roots["worker"] / block_id / nonce
    attempt.mkdir(parents=True, exist_ok=False)
    request_path = attempt / "request.json"
    result_path = attempt / "payload.json"
    request = _build_request(
        context, block_id=block_id, controller=controller, python=python,
        result_path=result_path,
    )
    recovery._atomic_json(request_path, request)
    log_dir = roots["log"] / block_id / nonce
    log_dir.mkdir(parents=True, exist_ok=False)
    with (
        (log_dir / "stdout.log").open("w", encoding="utf-8") as stdout,
        (log_dir / "stderr.log").open("w", encoding="utf-8") as stderr,
    ):
        process = subprocess.Popen(
            [str(python), "-B", "-m", MODULE, "--worker-request", str(request_path)],
            cwd=ROOT, stdout=stdout, stderr=stderr, text=True,
        )
        wait = recovery._wait_worker(
            process, context["config"]["execution"]["process_isolation"]
        )
    if wait["status"] != "exited" or wait["exit_code"] != 0:
        raise RuntimeError(
            f"pilot worker {block_id} ended {wait['status']}; unresolved, not infeasible"
        )
    result = recovery._mapping(_load_json(result_path, "pilot worker result"), "result")
    payload = _validate_worker_result(
        request, result, request_path=request_path, observed_pid=process.pid,
        observed_exit_code=int(process.returncode), context=context,
    )
    receipt_path = attempt / "receipt.json"
    recovery._atomic_json(
        receipt_path,
        _receipt(request, result, request_path=request_path, result_path=result_path, observed_pid=process.pid),
    )
    return payload, result_path, receipt_path


def _extract_gurobi_payload() -> dict[str, Any]:
    checkpoint = recovery._mapping(_load_json(Gurobi_0008, "Gurobi 0008"), "checkpoint")
    return {
        key: value
        for key, value in checkpoint.items()
        if key not in {"schema", "stage_base_provenance_sha256"}
    }


def _interval(certificate: Mapping[str, Any], prefix: str) -> tuple[float, float, float]:
    values = (
        certificate.get("objective_incumbent_mw"),
        certificate.get("lower_bound_mw"),
        certificate.get("upper_bound_mw"),
    )
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
        raise ValueError(f"{prefix} finite interval is incomplete")
    return tuple(float(value) for value in values)  # type: ignore[return-value]


def compare_named_outage_0008(
    highs_payload: Mapping[str, Any], gurobi_payload: Mapping[str, Any]
) -> dict[str, object]:
    """Pure fail-closed comparison using the sealed semantic-v1 thresholds."""

    report: dict[str, object] = {
        "schema": "rq2_public_grid_two_block_pilot_named_outage_comparison_v1",
        "block_id": BLOCKS[0],
        "comparison_passed": False,
        "mathematical_infeasibility_inferred": False,
        "maximum_finite_grid_need_difference_mw": 1.0e-5,
        "maximum_baseline_incumbent_difference_usd": 1.0e-4,
        "raw_status_equality_required": False,
        "reason": None,
    }
    try:
        context = _stage_context()
        gurobi_config = _load_yaml(Gurobi_CONFIG, "frozen Gurobi config")
        highs = recovery._validate_scientific_payload(
            recovery._mapping(highs_payload, "HiGHS 0008 payload"),
            block_id=BLOCKS[0], expected_block=context["blocks"][BLOCKS[0]],
            config=context["config"],
        )
        gurobi = recovery._validate_scientific_payload(
            recovery._mapping(gurobi_payload, "Gurobi 0008 payload"),
            block_id=BLOCKS[0], expected_block=context["blocks"][BLOCKS[0]],
            config=gurobi_config,
        )
        left_base = recovery._mapping(highs["baseline_audit"], "HiGHS baseline")
        right_base = recovery._mapping(gurobi["baseline_audit"], "Gurobi baseline")
        if abs(float(left_base["objective_usd"]) - float(right_base["objective_usd"])) > 1.0e-4:
            raise ValueError("baseline incumbents differ")
        baseline_overlap_lower = max(
            float(left_base["lower_bound_usd"]), float(right_base["lower_bound_usd"])
        )
        baseline_overlap_upper = min(
            float(left_base["upper_bound_usd"]), float(right_base["upper_bound_usd"])
        )
        if baseline_overlap_lower > baseline_overlap_upper and not math.isclose(
            baseline_overlap_lower,
            baseline_overlap_upper,
            rel_tol=1.0e-12,
            abs_tol=1.0e-12,
        ):
            raise ValueError("baseline certified intervals are disjoint")
        for index, (left_raw, right_raw) in enumerate(
            zip(highs["outcomes"], gurobi["outcomes"], strict=True)
        ):
            left = recovery._mapping(left_raw, "HiGHS outcome")
            right = recovery._mapping(right_raw, "Gurobi outcome")
            left_primary = recovery._mapping(left["primary"], "HiGHS primary")
            right_primary = recovery._mapping(right["primary"], "Gurobi primary")
            identity = ("source_hour", "event_id", "component_type", "component_uid")
            if any(left_primary[key] != right_primary[key] for key in identity):
                raise ValueError(f"hour {index} outage identity differs")
            if left["state"] != right["state"]:
                raise ValueError(f"hour {index} semantic state differs")
            left_certificate = recovery._mapping(left["primary_certificate"], "HiGHS certificate")
            right_certificate = recovery._mapping(right["primary_certificate"], "Gurobi certificate")
            scale = ("model_variables", "model_constraints")
            if any(left_certificate[key] != right_certificate[key] for key in scale):
                raise ValueError(f"hour {index} model scale differs")
            if left["state"] == "finite_grid_need":
                if abs(float(left_primary["grid_need_mw"]) - float(right_primary["grid_need_mw"])) > 1.0e-5:
                    raise ValueError(f"hour {index} finite grid need differs")
                left_interval = _interval(left_certificate, "HiGHS hourly")
                right_interval = _interval(right_certificate, "Gurobi hourly")
                overlap_lower = max(left_interval[1], right_interval[1])
                overlap_upper = min(left_interval[2], right_interval[2])
                if overlap_lower > overlap_upper and not math.isclose(
                    overlap_lower,
                    overlap_upper,
                    rel_tol=1.0e-12,
                    abs_tol=1.0e-10,
                ):
                    raise ValueError(f"hour {index} certified intervals are disjoint")
            else:
                if (left["zero_dc_confirmation"] is None) != (right["zero_dc_confirmation"] is None):
                    raise ValueError(f"hour {index} E0 zero confirmation differs")
        report["comparison_passed"] = True
        report["reason"] = None
    except (KeyError, TypeError, ValueError) as error:
        report["reason"] = str(error)
    return report


def _result_manifest(staging: Path) -> dict[str, str]:
    manifest: dict[str, str] = {}
    for path in sorted(staging.rglob("*")):
        if path.name == "SHA256SUMS.json":
            continue
        if path.is_symlink():
            raise ValueError("pilot result contains a symlink")
        if path.is_file():
            manifest[path.relative_to(staging).as_posix()] = recovery._sha256(path)
        elif not path.is_dir():
            raise ValueError("pilot result contains a non-ordinary member")
    return manifest


def _publish_result(
    staging: Path, *, config: Mapping[str, Any], controller: Mapping[str, Any],
    payloads: Mapping[str, Mapping[str, Any]], comparison: Mapping[str, Any],
    formal_after: Mapping[str, Any]
) -> dict[str, object]:
    if list(payloads) != BLOCKS or comparison.get("comparison_passed") is not True:
        raise RuntimeError("complete ordered payloads and passing comparison are required")
    if controller["formal_snapshot_before"] != formal_after:
        raise ValueError("formal artifacts changed during pilot")
    expected_before = {"controller_receipt.json"}
    for block_id in BLOCKS:
        expected_before.update(
            {
                f"workers/{block_id}/payload.json",
                f"workers/{block_id}/receipt.json",
            }
        )
    observed_before = {
        path.relative_to(staging).as_posix()
        for path in staging.rglob("*")
        if path.is_file()
    }
    if observed_before != expected_before:
        raise ValueError("pilot prepublication staging inventory drifted")
    summary = {
        "schema": PILOT_RESULT_SCHEMA,
        "status": "complete_nonformal_pilot",
        "blocks": BLOCKS,
        "all_blocks_resolved": True,
        "named_outage_comparison_passed": True,
        "block_0009_cross_solver_comparison_required": False,
        "fresh_worker_process_count": 2,
        "parent_solver_calls": 0,
        "post_result_review_passed": False,
        "formal_execution_ready": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    shutil.copyfile(CONFIG, staging / "config.yaml")
    recovery._atomic_json(staging / "comparison.json", dict(comparison))
    recovery._atomic_json(staging / "summary.json", summary)
    expected_before.update({"config.yaml", "comparison.json", "summary.json"})
    observed_ready = {
        path.relative_to(staging).as_posix()
        for path in staging.rglob("*")
        if path.is_file()
    }
    if observed_ready != expected_before:
        raise ValueError("pilot ready-to-publish inventory drifted")
    recovery._atomic_json(staging / "SHA256SUMS.json", _result_manifest(staging))
    return summary


def run(*, validate_only: bool = False) -> dict[str, object]:
    if validate_only:
        from experiments.validate_rq2_public_grid_two_block_pilot_candidate_v1 import (
            validate,
        )

        return validate()
    config, _ = _require_execution_authority()
    context = _stage_context()
    roots = _pilot_roots(config)
    if any(path.exists() for path in roots.values()):
        raise FileExistsError("all canonical pilot roots must be fresh")
    host_sample = recovery._resource_probe(os.getpid())
    stop = recovery._resource_stop_reason(
        host_sample, context["config"]["execution"]["process_isolation"]
    )
    if stop is not None:
        raise RuntimeError(f"pilot resource gate stopped execution: {stop}; not infeasible")
    python = _python_authority(context["config"])
    roots["result"].parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{roots['result'].name}.", dir=roots["result"].parent))
    try:
        roots["worker"].mkdir(parents=True, exist_ok=False)
        roots["log"].mkdir(parents=True, exist_ok=False)
        controller = _controller_receipt(config)
        controller_path = staging / "controller_receipt.json"
        recovery._atomic_json(controller_path, controller)
        controller["receipt_sha256"] = recovery._sha256(controller_path)
        result_workers = staging / "workers"
        result_workers.mkdir()
        payloads: dict[str, dict[str, Any]] = {}
        for block_id in BLOCKS:
            payload, payload_path, receipt_path = _dispatch_one(
                context, block_id=block_id, controller=controller, python=python, roots=roots
            )
            payloads[block_id] = payload
            accepted = result_workers / block_id
            accepted.mkdir()
            shutil.copyfile(payload_path, accepted / "payload.json")
            shutil.copyfile(receipt_path, accepted / "receipt.json")
        comparison = compare_named_outage_0008(payloads[BLOCKS[0]], _extract_gurobi_payload())
        summary = _publish_result(
            staging, config=config, controller=controller, payloads=payloads,
            comparison=comparison, formal_after=_formal_snapshot(config),
        )
        if roots["result"].exists():
            raise FileExistsError("pilot target appeared before atomic publication")
        staging.rename(roots["result"])
        return summary
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--worker-request", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker_request is not None:
        if args.validate_only:
            parser.error("hidden worker mode does not accept controller options")
        raise SystemExit(_worker(args.worker_request))
    print(json.dumps(run(validate_only=args.validate_only), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
