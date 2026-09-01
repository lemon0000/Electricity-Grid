"""Fail-closed RQ2 0008/0009 pilot candidate v2.

This candidate is reviewable but never executable.  A separately sealed
successor must bind a future independent pre-run PASS receipt before either the
controller or hidden worker can reach data loading or solver dispatch.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import os
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from ctypes import wintypes
from pathlib import Path
from typing import Any

from experiments import run_rq2_public_grid_two_block_pilot_candidate_v1 as predecessor
from experiments import (
    run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_v1 as recovery,
)
from src.evaluation.execution_machine import (
    execution_host_status,
    require_execution_host,
)
from src.grid.rts_gmlc import load_rts_gmlc_chronological_data

ROOT = Path(__file__).resolve().parents[1]
MODULE = "experiments.run_rq2_public_grid_two_block_pilot_candidate_v2"
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v2.yaml"
ACTIVATION = ROOT / "configs/rq2_public_grid_two_block_pilot_user_activation_v2.yaml"
REWORK_RECEIPT = ROOT / "configs/rq2_public_grid_two_block_pilot_review_rework_v1.yaml"
PASS_RECEIPT = (
    ROOT / "configs/rq2_public_grid_solver_recovery_implementation_review_pass_v2.yaml"
)
RECOVERY_MANIFEST = ROOT / "configs/rq2_public_grid_solver_recovery_v2.SHA256SUMS.json"
BUNDLE = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v2.SHA256SUMS.json"
OUTER = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v2.OUTER.SHA256SUMS.json"
BASE_CONFIG = (
    ROOT / "configs/rts_gmlc_public_grid_need_dispatch_v4_highs_process_isolated_v1.yaml"
)
SEMANTIC_CONFIG = ROOT / "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml"
SEMANTIC_MANIFEST = (
    ROOT / "configs/rq2_public_solver_pilot_semantic_successor_v1.SHA256SUMS.json"
)
SEMANTIC_VALIDATOR = (
    ROOT / "experiments/validate_rq2_public_solver_pilot_semantic_successor_v1.py"
)
GUROBI_CONFIG = ROOT / "results/execution_configs/rq2_public_successor_v2/grid.yaml"
GUROBI_0008 = (
    ROOT
    / "results/checkpoints/rts_gmlc_public_grid_need_dispatch_v4_gurobi"
    / "holdout_s20260822_0008.json"
)

BLOCKS = ["holdout_s20260822_0008", "holdout_s20260822_0009"]
CONFIG_SCHEMA = "rq2_public_grid_two_block_pilot_candidate_v2"
REQUEST_SCHEMA = "rq2_public_grid_two_block_pilot_worker_request_candidate_v2"
RESULT_SCHEMA = "rq2_public_grid_two_block_pilot_worker_result_candidate_v2"
RECEIPT_SCHEMA = "rq2_public_grid_two_block_pilot_worker_receipt_candidate_v2"
CONTROLLER_SCHEMA = "rq2_public_grid_two_block_pilot_controller_receipt_candidate_v2"

V1_OUTER_SHA256 = "7874a9bdb83d36de98e7626bbe259fd607f1d9d2f8e5669e9924c6f84a02306f"
REWORK_SHA256 = "8fd6f56403c593255ea2e7c36cbfc0c94329af7d716a6f4b336e8f0aff2d4d6a"
RECOVERY_MANIFEST_SHA256 = (
    "b300a040fc481beea094702404f4d00eb176403e40f7909d2d704f7fd2195729"
)
RECOVERY_MEMBERS = {
    "configs/rq2_public_grid_solver_recovery_preregistration_v2.yaml": "a767708dfd1bcb243df9d0466a092a7d7cf090c6583af162119e72cadc919e59",
    "configs/rq2_public_grid_solver_recovery_review_rework_v1.yaml": "cfe8d1f5fb7cef9514ab995b19b20bed43f3604af5ad84ab6433ae84a9810834",
    "configs/rq2_public_pipeline_provenance_contract_v4_process_isolated_v1.yaml": "cb6ae7c07a7745f90288cefafedb7df82221d06205b3d2aab68580e0587a89b1",
    "configs/rts_gmlc_public_grid_need_dispatch_v4_highs_process_isolated_v1.yaml": "e1306a375bba5d19d687cb2728a981528662064226b4661a0b74f894b647f3bd",
    "experiments/run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_v1.py": "c90f796aa9c9043d48560599b892681455b7c7ddee3881501ce449bfa1c3833e",
    "experiments/validate_rq2_public_grid_solver_recovery_v2.py": "cf563d95ea024b38587350cfae73af0c597d8d491544e2306def214b7a296fe1",
    "tests/test_rq2_public_grid_solver_recovery_v2.py": "56eb993a3ad3856447690776b3d8a6f7ef08faad04a1fc85744f2004546561bb",
}
SEMANTIC_HASHES = {
    "semantic_config_sha256": "cb0209a9a53962be8ebb6ee185d3bfbf3d004d7cd761e164b286a58e0c7887b0",
    "semantic_manifest_sha256": "c0b1a6a3074343ab5f281b268cd40898630ad1e2234830a4536189687832f471",
    "semantic_validator_sha256": "01b7f60a620c81a7a656ba6576c3b85af9e371b30d42dd5959f430ee220c80dd",
}
REGISTERED_RAW_STATUS = {
    "highs": {
        "optimal": {"ok"},
        "infeasible": {"error"},
        "not_applicable_no_active_outage": {"not_applicable"},
    },
    "gurobi": {
        "optimal": {"ok"},
        "infeasible": {"warning"},
        "not_applicable_no_active_outage": {"not_applicable"},
    },
}
BUNDLE_INVENTORY = {
    "configs/rq2_public_grid_two_block_pilot_review_rework_v1.yaml",
    "configs/rq2_public_grid_two_block_pilot_candidate_v2.yaml",
    "configs/rq2_public_grid_two_block_pilot_user_activation_v2.yaml",
    "experiments/run_rq2_public_grid_two_block_pilot_candidate_v2.py",
    "experiments/validate_rq2_public_grid_two_block_pilot_candidate_v2.py",
    "tests/test_rq2_public_grid_two_block_pilot_candidate_v2.py",
}


def _load_yaml(path: Path, label: str) -> dict[str, Any]:
    return recovery._load_yaml_mapping(path, label)


def _load_json(path: Path, label: str) -> Any:
    return recovery._load_json_strict(path, label)


def _is_link_or_reparse(path: Path) -> bool:
    """Return true for POSIX symlinks and Windows symlink/junction reparse points."""

    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return False
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse_flag)


def _ordinary_file(path: Path, label: str, expected_hash: str) -> None:
    if (
        not path.is_file()
        or _is_link_or_reparse(path)
        or path.resolve() != path.absolute()
        or recovery._sha256(path) != expected_hash
    ):
        raise ValueError(f"{label} live authority drifted")


def _verify_recovery_authority() -> None:
    _ordinary_file(RECOVERY_MANIFEST, "recovery manifest", RECOVERY_MANIFEST_SHA256)
    manifest = recovery._mapping(
        _load_json(RECOVERY_MANIFEST, "recovery manifest"), "recovery manifest"
    )
    if manifest != RECOVERY_MEMBERS:
        raise ValueError("recovery manifest exact member inventory drifted")
    for relative, expected in RECOVERY_MEMBERS.items():
        _ordinary_file(ROOT / relative, f"recovery member {relative}", expected)
    _ordinary_file(
        PASS_RECEIPT,
        "recovery implementation PASS receipt",
        "3153d72000fb7ea87f55adc3eed63af5fdb0901a48ded6ae92a616924088c720",
    )


def _verify_semantic_authority() -> None:
    for path, key in (
        (SEMANTIC_CONFIG, "semantic_config_sha256"),
        (SEMANTIC_MANIFEST, "semantic_manifest_sha256"),
        (SEMANTIC_VALIDATOR, "semantic_validator_sha256"),
    ):
        _ordinary_file(path, key, SEMANTIC_HASHES[key])
    manifest = recovery._mapping(
        _load_json(SEMANTIC_MANIFEST, "semantic manifest"), "semantic manifest"
    )
    files = recovery._mapping(manifest.get("files"), "semantic manifest files")
    if (
        files.get(SEMANTIC_CONFIG.relative_to(ROOT).as_posix())
        != SEMANTIC_HASHES["semantic_config_sha256"]
        or files.get(SEMANTIC_VALIDATOR.relative_to(ROOT).as_posix())
        != SEMANTIC_HASHES["semantic_validator_sha256"]
    ):
        raise ValueError("semantic manifest member binding drifted")


def _verify_bundle_chain() -> dict[str, str]:
    bundle = recovery._mapping(_load_json(BUNDLE, "candidate bundle"), "bundle")
    if bundle.get("schema") != "rq2_public_grid_two_block_pilot_candidate_bundle_v2":
        raise ValueError("candidate bundle schema drifted")
    files = recovery._mapping(bundle.get("files"), "candidate bundle files")
    if set(files) != BUNDLE_INVENTORY:
        raise ValueError("candidate bundle inventory drifted")
    for relative, expected in files.items():
        if not recovery._is_sha256(expected):
            raise ValueError(f"candidate bundle hash malformed: {relative}")
        _ordinary_file(ROOT / relative, f"candidate bundle member {relative}", expected)
    outer = recovery._mapping(_load_json(OUTER, "candidate outer"), "outer")
    expected_outer = {
        "schema": "rq2_public_grid_two_block_pilot_candidate_outer_v2",
        "files": {
            BUNDLE.relative_to(ROOT).as_posix(): recovery._sha256(BUNDLE),
        },
    }
    if outer != expected_outer:
        raise ValueError("candidate outer manifest drifted")
    return {str(key): str(value) for key, value in files.items()}


def _authority_bindings() -> dict[str, object]:
    _verify_recovery_authority()
    _verify_semantic_authority()
    files = _verify_bundle_chain()
    return {
        "rejected_candidate_v1_outer_sha256": V1_OUTER_SHA256,
        "predecessor_rework_receipt_sha256": REWORK_SHA256,
        "recovery_manifest_sha256": RECOVERY_MANIFEST_SHA256,
        "recovery_live_members": dict(RECOVERY_MEMBERS),
        **SEMANTIC_HASHES,
        "candidate_config_sha256": files[CONFIG.relative_to(ROOT).as_posix()],
        "candidate_activation_sha256": files[ACTIVATION.relative_to(ROOT).as_posix()],
        "candidate_runner_sha256": files[Path(__file__).relative_to(ROOT).as_posix()],
        "candidate_bundle_sha256": recovery._sha256(BUNDLE),
        "candidate_outer_sha256": recovery._sha256(OUTER),
    }


def _load_authority() -> tuple[dict[str, Any], dict[str, Any]]:
    authority = _authority_bindings()
    config = _load_yaml(CONFIG, "candidate config")
    activation = _load_yaml(ACTIVATION, "candidate activation")
    if config.get("schema") != CONFIG_SCHEMA or config.get("version") != 2:
        raise ValueError("candidate config identity drifted")
    if (
        config.get("predecessor_rework_authority", {}).get("rework_receipt_sha256")
        != REWORK_SHA256
        or activation.get("candidate_authority", {}).get("config_sha256")
        != authority["candidate_config_sha256"]
        or activation.get("candidate_authority", {}).get(
            "predecessor_rework_receipt_sha256"
        )
        != REWORK_SHA256
    ):
        raise ValueError("candidate activation or REWORK binding drifted")
    return config, activation


def _execution_authority_status(
    config: Mapping[str, Any], activation: Mapping[str, Any]
) -> dict[str, bool]:
    gates = recovery._mapping(config.get("gates"), "candidate gates")
    activation_gates = recovery._mapping(activation.get("gates"), "activation gates")
    return {
        "recovery_implementation_passed": (
            gates.get("recovery_v2_implementation_review_passed") is True
            and activation_gates.get("recovery_v2_implementation_review_passed") is True
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
    config, activation = _load_authority()
    failed = [
        name
        for name, passed in _execution_authority_status(config, activation).items()
        if not passed
    ]
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


def _formal_snapshot(config: Mapping[str, Any]) -> dict[str, object]:
    return predecessor._formal_snapshot(config)


def _pilot_roots(config: Mapping[str, Any]) -> dict[str, Path]:
    paths = recovery._mapping(config.get("paths"), "pilot paths")
    roots = {
        "result": recovery._resolve(paths["result_directory"], "pilot result"),
        "worker": recovery._resolve(paths["worker_staging_directory"], "pilot worker"),
        "log": recovery._resolve(paths["attempt_log_directory"], "pilot log"),
    }
    formal = recovery._mapping(config.get("immutable_formal_authority"), "formal authority")
    protected = [
        recovery._resolve(formal[key], key)
        for key in (
            "gurobi_checkpoint_directory",
            "gurobi_output_directory",
            "recovery_checkpoint_directory",
            "recovery_output_directory",
        )
    ]
    for left in roots.values():
        for right in [*roots.values(), *protected]:
            if left == right:
                if right in roots.values():
                    continue
                raise ValueError("pilot and formal roots overlap")
            if recovery._same_or_descendant(left, right) or recovery._same_or_descendant(
                right, left
            ):
                raise ValueError("pilot roots are not isolated")
    return roots


def _canonical_controller_receipt_path(
    path: Path, config: Mapping[str, Any]
) -> bool:
    target = _pilot_roots(config)["result"]
    staging = path.parent
    return (
        path.name == "controller_receipt.json"
        and staging.parent == target.parent
        and staging.name.startswith(f".{target.name}.staging.")
        and len(staging.name) > len(f".{target.name}.staging.")
    )


def _canonical_worker_root(path: Path, config: Mapping[str, Any]) -> bool:
    return path == _pilot_roots(config)["worker"]


def _extract_gurobi_payload() -> dict[str, Any]:
    checkpoint = recovery._mapping(_load_json(GUROBI_0008, "Gurobi 0008"), "checkpoint")
    return {
        key: value
        for key, value in checkpoint.items()
        if key not in {"schema", "stage_base_provenance_sha256"}
    }


def _registered_raw_semantic(solver: str, termination: object, status: object) -> str:
    if not isinstance(termination, str) or not isinstance(status, str):
        raise TypeError("unregistered raw termination/status pair")
    registered = REGISTERED_RAW_STATUS.get(solver, {})
    if status not in registered.get(termination, set()):
        raise ValueError(
            f"unregistered raw termination/status pair: {solver}/{termination}/{status}"
        )
    return termination


def _normalize_payload_raw_evidence(payload: Mapping[str, Any], solver: str) -> None:
    baseline = recovery._mapping(payload.get("baseline_audit"), f"{solver} baseline")
    if (
        _registered_raw_semantic(
            solver,
            baseline.get("termination_condition"),
            baseline.get("solver_status"),
        )
        != "optimal"
    ):
        raise ValueError(f"{solver} baseline semantic is not optimal")
    for index, (outcome_raw, row_raw) in enumerate(
        zip(payload.get("outcomes", []), payload.get("rows", []), strict=True)
    ):
        outcome = recovery._mapping(outcome_raw, f"{solver} outcome {index}")
        row = recovery._mapping(row_raw, f"{solver} row {index}")
        primary = recovery._mapping(outcome.get("primary"), f"{solver} primary {index}")
        semantic = _registered_raw_semantic(
            solver, primary.get("termination_condition"), primary.get("solver_status")
        )
        expected = (
            "not_applicable_no_active_outage"
            if not row.get("active_event_id")
            else "infeasible"
            if outcome.get("state") == "E0_infeasible_at_zero_dc"
            else "optimal"
        )
        if semantic != expected:
            raise ValueError(f"{solver} primary semantic mismatch at hour {index}")
        zero = outcome.get("zero_dc_confirmation")
        if expected == "infeasible":
            zero_map = recovery._mapping(zero, f"{solver} zero confirmation {index}")
            if (
                _registered_raw_semantic(
                    solver,
                    zero_map.get("termination_condition"),
                    zero_map.get("solver_status"),
                )
                != "infeasible"
            ):
                raise ValueError(f"{solver} zero confirmation mismatch at hour {index}")
        elif zero is not None:
            raise ValueError(f"{solver} unexpected zero confirmation at hour {index}")


def _interval(certificate: Mapping[str, Any], prefix: str) -> tuple[float, float, float]:
    values = (
        certificate.get("objective_incumbent_mw"),
        certificate.get("lower_bound_mw"),
        certificate.get("upper_bound_mw"),
    )
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        for value in values
    ):
        raise ValueError(f"{prefix} finite interval is incomplete")
    return tuple(float(value) for value in values)  # type: ignore[return-value]


def compare_named_outage_0008(
    highs_payload: Mapping[str, Any], gurobi_payload: Mapping[str, Any]
) -> dict[str, object]:
    report: dict[str, object] = {
        "schema": "rq2_public_grid_two_block_pilot_named_outage_comparison_v2",
        "block_id": BLOCKS[0],
        "comparison_passed": False,
        "mathematical_infeasibility_inferred": False,
        "maximum_finite_grid_need_difference_mw": 1.0e-5,
        "maximum_baseline_incumbent_difference_usd": 1.0e-4,
        "raw_status_equality_required": False,
        "reason": None,
    }
    try:
        _verify_semantic_authority()
        context = _stage_context()
        gurobi_config = _load_yaml(GUROBI_CONFIG, "frozen Gurobi config")
        highs = recovery._validate_scientific_payload(
            recovery._mapping(highs_payload, "HiGHS 0008 payload"),
            block_id=BLOCKS[0],
            expected_block=context["blocks"][BLOCKS[0]],
            config=context["config"],
        )
        gurobi = recovery._validate_scientific_payload(
            recovery._mapping(gurobi_payload, "Gurobi 0008 payload"),
            block_id=BLOCKS[0],
            expected_block=context["blocks"][BLOCKS[0]],
            config=gurobi_config,
        )
        _normalize_payload_raw_evidence(highs, "highs")
        _normalize_payload_raw_evidence(gurobi, "gurobi")
        left_base = recovery._mapping(highs["baseline_audit"], "HiGHS baseline")
        right_base = recovery._mapping(gurobi["baseline_audit"], "Gurobi baseline")
        if abs(float(left_base["objective_usd"]) - float(right_base["objective_usd"])) > 1.0e-4:
            raise ValueError("baseline incumbents differ")
        overlap_lower = max(
            float(left_base["lower_bound_usd"]), float(right_base["lower_bound_usd"])
        )
        overlap_upper = min(
            float(left_base["upper_bound_usd"]), float(right_base["upper_bound_usd"])
        )
        if overlap_lower > overlap_upper and not math.isclose(
            overlap_lower, overlap_upper, rel_tol=1.0e-12, abs_tol=1.0e-12
        ):
            raise ValueError("baseline certified intervals are disjoint")
        for index, (left_raw, right_raw) in enumerate(
            zip(highs["outcomes"], gurobi["outcomes"], strict=True)
        ):
            left = recovery._mapping(left_raw, "HiGHS outcome")
            right = recovery._mapping(right_raw, "Gurobi outcome")
            left_primary = recovery._mapping(left["primary"], "HiGHS primary")
            right_primary = recovery._mapping(right["primary"], "Gurobi primary")
            for key in ("source_hour", "event_id", "component_type", "component_uid"):
                if left_primary.get(key) != right_primary.get(key):
                    raise ValueError(f"hour {index} outage identity differs")
            if left.get("state") != right.get("state"):
                raise ValueError(f"hour {index} semantic state differs")
            left_cert = recovery._mapping(left["primary_certificate"], "HiGHS certificate")
            right_cert = recovery._mapping(right["primary_certificate"], "Gurobi certificate")
            for key in ("model_variables", "model_constraints"):
                if left_cert.get(key) != right_cert.get(key):
                    raise ValueError(f"hour {index} model scale differs")
            if left.get("state") == "finite_grid_need":
                if (
                    abs(
                        float(left_primary["grid_need_mw"])
                        - float(right_primary["grid_need_mw"])
                    )
                    > 1.0e-5
                ):
                    raise ValueError(f"hour {index} finite grid need differs")
                left_interval = _interval(left_cert, "HiGHS hourly")
                right_interval = _interval(right_cert, "Gurobi hourly")
                overlap_lower = max(left_interval[1], right_interval[1])
                overlap_upper = min(left_interval[2], right_interval[2])
                if overlap_lower > overlap_upper and not math.isclose(
                    overlap_lower,
                    overlap_upper,
                    rel_tol=1.0e-12,
                    abs_tol=1.0e-10,
                ):
                    raise ValueError(f"hour {index} certified intervals are disjoint")
            elif (left.get("zero_dc_confirmation") is None) != (
                right.get("zero_dc_confirmation") is None
            ):
                raise ValueError(f"hour {index} E0 zero confirmation differs")
        report["comparison_passed"] = True
    except (KeyError, TypeError, ValueError) as error:
        report["reason"] = str(error)
    return report


def _process_identity(pid: int) -> dict[str, int]:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise ValueError("process PID is invalid")
    if os.name != "nt":
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()
        return {"pid": pid, "creation_time_100ns": int(stat[21])}
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetProcessTimes.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
        ctypes.POINTER(wintypes.FILETIME),
    ]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        raise OSError(ctypes.get_last_error(), "OpenProcess failed")
    try:
        creation = wintypes.FILETIME()
        exit_time = wintypes.FILETIME()
        kernel = wintypes.FILETIME()
        user = wintypes.FILETIME()
        if not kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            raise OSError(ctypes.get_last_error(), "GetProcessTimes failed")
        created = (int(creation.dwHighDateTime) << 32) | int(creation.dwLowDateTime)
        return {"pid": pid, "creation_time_100ns": created}
    finally:
        kernel32.CloseHandle(handle)


def _build_controller_receipt(
    config: Mapping[str, Any],
    *,
    controller_pid: int,
    controller_creation_time_100ns: int,
    controller_receipt_path: Path,
) -> dict[str, object]:
    return {
        "schema": CONTROLLER_SCHEMA,
        "authority": _authority_bindings(),
        "controller_process_identity": {
            "pid": controller_pid,
            "creation_time_100ns": controller_creation_time_100ns,
        },
        "controller_started_ns": time.time_ns(),
        "controller_nonce": secrets.token_hex(32),
        "controller_receipt_path": str(controller_receipt_path.resolve()),
        "scientific_config_path": str(BASE_CONFIG.resolve()),
        "scientific_config_sha256": recovery._sha256(BASE_CONFIG),
        "execution_order": list(BLOCKS),
        "solver": recovery._solver_binding(_load_yaml(BASE_CONFIG, "base config")),
        "formal_snapshot_before": _formal_snapshot(config),
        "parent_solver_calls": 0,
    }


def _build_request(
    context: Mapping[str, Any],
    *,
    block_id: str,
    controller: Mapping[str, Any],
    controller_receipt_path: Path,
    worker_root: Path,
    python: Path,
    result_path: Path,
    nonce: str | None = None,
) -> dict[str, object]:
    nonce = nonce or secrets.token_hex(32)
    return {
        "schema": REQUEST_SCHEMA,
        "authority": _authority_bindings(),
        "block_id": block_id,
        "execution_index": BLOCKS.index(block_id) + 1,
        "block_input_sha256": recovery._block_input_sha256(context["blocks"][block_id]),
        "stage": recovery.STAGE,
        "stage_base_provenance_sha256": context["stage_base_sha256"],
        "parent_process_identity": controller["controller_process_identity"],
        "parent_dispatch_started_ns": time.time_ns(),
        "controller_nonce": controller["controller_nonce"],
        "controller_receipt_path": str(controller_receipt_path.resolve()),
        "controller_receipt_sha256": recovery._sha256(controller_receipt_path),
        "nonce": nonce,
        "worker_root": str(worker_root.resolve()),
        "worker_result_path": str(result_path.resolve()),
        "scientific_config_path": str(BASE_CONFIG.resolve()),
        "scientific_config_sha256": recovery._sha256(BASE_CONFIG),
        "python_executable": str(python.resolve()),
        "python_executable_sha256": recovery._sha256(python),
        "execution_host": execution_host_status(context["config"]["execution"]),
        "implementation": recovery._implementation_bindings(),
        "solver": recovery._solver_binding(context["config"]),
    }


def _strict_path(path: Path, *, must_exist: bool, label: str) -> Path:
    absolute = path.absolute()
    if not path.is_absolute() or path != path.resolve(strict=False):
        raise ValueError(f"{label} is not canonical")
    if must_exist and not absolute.exists():
        raise ValueError(f"{label} does not exist")
    current = absolute
    while True:
        if current.exists() and _is_link_or_reparse(current):
            raise ValueError(f"{label} contains a symlink")
        if current.parent == current:
            break
        current = current.parent
    return absolute


def _validate_controller_receipt(
    request: Mapping[str, Any], expected_authority: Mapping[str, Any]
) -> dict[str, Any]:
    path = _strict_path(
        Path(str(request["controller_receipt_path"])),
        must_exist=True,
        label="controller receipt",
    )
    receipt = recovery._mapping(_load_json(path, "controller receipt"), "controller receipt")
    config = _load_yaml(CONFIG, "candidate config")
    expected_keys = {
        "schema",
        "authority",
        "controller_process_identity",
        "controller_started_ns",
        "controller_nonce",
        "controller_receipt_path",
        "scientific_config_path",
        "scientific_config_sha256",
        "execution_order",
        "solver",
        "formal_snapshot_before",
        "parent_solver_calls",
    }
    if set(receipt) != expected_keys or receipt.get("schema") != CONTROLLER_SCHEMA:
        raise ValueError("controller receipt schema drifted")
    if (
        recovery._sha256(path) != request.get("controller_receipt_sha256")
        or receipt.get("authority") != expected_authority
        or receipt.get("controller_process_identity")
        != request.get("parent_process_identity")
        or receipt.get("controller_nonce") != request.get("controller_nonce")
        or receipt.get("controller_receipt_path") != str(path)
        or not _canonical_controller_receipt_path(path, config)
        or receipt.get("scientific_config_path") != str(BASE_CONFIG.resolve())
        or receipt.get("scientific_config_sha256") != recovery._sha256(BASE_CONFIG)
        or receipt.get("execution_order") != BLOCKS
        or receipt.get("solver")
        != recovery._solver_binding(_load_yaml(BASE_CONFIG, "base config"))
        or receipt.get("formal_snapshot_before") != _formal_snapshot(config)
        or receipt.get("parent_solver_calls") != 0
    ):
        raise ValueError("controller receipt authority drifted")
    started = receipt.get("controller_started_ns")
    if isinstance(started, bool) or not isinstance(started, int) or started <= 0:
        raise ValueError("controller receipt start time is invalid")
    return receipt


def _validate_request(request: Mapping[str, Any], request_path: Path) -> dict[str, Any]:
    _require_execution_authority()
    expected_authority = _authority_bindings()
    expected_keys = {
        "schema",
        "authority",
        "block_id",
        "execution_index",
        "block_input_sha256",
        "stage",
        "stage_base_provenance_sha256",
        "parent_process_identity",
        "parent_dispatch_started_ns",
        "controller_nonce",
        "controller_receipt_path",
        "controller_receipt_sha256",
        "nonce",
        "worker_root",
        "worker_result_path",
        "scientific_config_path",
        "scientific_config_sha256",
        "python_executable",
        "python_executable_sha256",
        "execution_host",
        "implementation",
        "solver",
    }
    if set(request) != expected_keys or request.get("schema") != REQUEST_SCHEMA:
        raise ValueError("pilot worker request schema drifted")
    if request.get("authority") != expected_authority:
        raise ValueError("pilot worker authority drifted")
    block_id = request.get("block_id")
    if block_id not in BLOCKS or request.get("execution_index") != BLOCKS.index(block_id) + 1:
        raise ValueError("pilot worker block identity drifted")
    for key in ("controller_nonce", "nonce", "controller_receipt_sha256"):
        if not recovery._is_sha256(request.get(key)):
            raise ValueError(f"pilot worker {key} drifted")
    parent = recovery._mapping(request.get("parent_process_identity"), "parent identity")
    parent_pid = parent.get("pid")
    parent_creation = parent.get("creation_time_100ns")
    if (
        isinstance(parent_pid, bool)
        or not isinstance(parent_pid, int)
        or parent_pid <= 0
        or isinstance(parent_creation, bool)
        or not isinstance(parent_creation, int)
        or parent_creation <= 0
        or os.getppid() != parent_pid
        or _process_identity(parent_pid) != parent
    ):
        raise ValueError("pilot worker parent PID/creation identity drifted")
    dispatch = request.get("parent_dispatch_started_ns")
    if (
        isinstance(dispatch, bool)
        or not isinstance(dispatch, int)
        or dispatch <= 0
        or dispatch > time.time_ns()
    ):
        raise ValueError("parent dispatch start time is invalid")
    receipt = _validate_controller_receipt(request, expected_authority)
    if dispatch < receipt["controller_started_ns"]:
        raise ValueError("dispatch predates controller receipt")
    worker_root = _strict_path(
        Path(str(request["worker_root"])), must_exist=True, label="worker root"
    )
    config = _load_yaml(CONFIG, "candidate config")
    if not _canonical_worker_root(worker_root, config):
        raise ValueError("worker root is not the canonical configured root")
    request_path = _strict_path(request_path, must_exist=True, label="worker request")
    expected_attempt = worker_root / str(block_id) / str(request["nonce"])
    if request_path != expected_attempt / "request.json":
        raise ValueError("worker request path traversal or identity drifted")
    result_path = _strict_path(
        Path(str(request["worker_result_path"])),
        must_exist=False,
        label="worker result",
    )
    if result_path != expected_attempt / "payload.json" or result_path.exists():
        raise ValueError("worker result path is not a fresh canonical sibling")
    inventory = {path.name for path in expected_attempt.iterdir()}
    if inventory != {"request.json"}:
        raise ValueError("worker attempt contains extra or preexisting paths")
    scientific = _strict_path(
        Path(str(request["scientific_config_path"])),
        must_exist=True,
        label="scientific config",
    )
    if (
        scientific != BASE_CONFIG.resolve()
        or request.get("scientific_config_sha256") != recovery._sha256(BASE_CONFIG)
    ):
        raise ValueError("scientific config path/hash drifted")
    python = _strict_path(
        Path(str(request["python_executable"])), must_exist=True, label="Python"
    )
    if (
        python != Path(sys.executable).resolve()
        or request.get("python_executable_sha256") != recovery._sha256(python)
    ):
        raise ValueError("worker Python identity drifted")
    context = _stage_context()
    if (
        request.get("stage") != recovery.STAGE
        or request.get("stage_base_provenance_sha256") != context["stage_base_sha256"]
        or request.get("block_input_sha256")
        != recovery._block_input_sha256(context["blocks"][str(block_id)])
        or request.get("implementation") != recovery._implementation_bindings()
        or request.get("solver") != recovery._solver_binding(context["config"])
        or request.get("execution_host")
        != execution_host_status(context["config"]["execution"])
    ):
        raise ValueError("worker scientific/implementation/host authority drifted")
    return context


def _worker(request_path: Path) -> int:
    request_path = request_path.resolve()
    request = recovery._mapping(_load_json(request_path, "pilot request"), "request")
    context = _validate_request(request, request_path)
    block_id = str(request["block_id"])
    worker_identity = _process_identity(os.getpid())
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
        "authority": request["authority"],
        "request_sha256": recovery._canonical_sha256(dict(request)),
        "block_id": block_id,
        "block_input_sha256": request["block_input_sha256"],
        "parent_process_identity": request["parent_process_identity"],
        "worker_process_identity": worker_identity,
        "controller_receipt_sha256": request["controller_receipt_sha256"],
        "nonce": request["nonce"],
        "scientific_config_path": request["scientific_config_path"],
        "scientific_config_sha256": request["scientific_config_sha256"],
        "solver": request["solver"],
        "scientific_payload": payload,
        "scientific_payload_sha256": recovery._canonical_sha256(payload),
        "all_hours_resolved": resolved,
        "mathematical_infeasibility_inferred_from_failure": False,
    }
    recovery._atomic_json(Path(str(request["worker_result_path"])), result)
    return 0 if resolved else 3


def _validate_copied_worker_pair(
    payload_path: Path,
    receipt_path: Path,
    *,
    expected_authority: Mapping[str, Any],
    request: Mapping[str, Any] | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result = recovery._mapping(_load_json(payload_path, "copied worker payload"), "result")
    receipt = recovery._mapping(_load_json(receipt_path, "copied worker receipt"), "receipt")
    if receipt.get("worker_payload_sha256") != recovery._sha256(payload_path):
        raise ValueError("copied worker payload/receipt hash mismatch")
    if result.get("authority") != expected_authority or receipt.get("authority") != expected_authority:
        raise ValueError("copied worker authority drifted")
    if request is None or context is None:
        raise ValueError("complete request/context required for copied evidence validation")
    expected_result_keys = {
        "schema",
        "status",
        "authority",
        "request_sha256",
        "block_id",
        "block_input_sha256",
        "parent_process_identity",
        "worker_process_identity",
        "controller_receipt_sha256",
        "nonce",
        "scientific_config_path",
        "scientific_config_sha256",
        "solver",
        "scientific_payload",
        "scientific_payload_sha256",
        "all_hours_resolved",
        "mathematical_infeasibility_inferred_from_failure",
    }
    if set(result) != expected_result_keys or result.get("schema") != RESULT_SCHEMA:
        raise ValueError("copied worker result schema drifted")
    if (
        result.get("status") != "complete"
        or result.get("request_sha256") != recovery._canonical_sha256(dict(request))
        or result.get("block_id") != request.get("block_id")
        or result.get("block_input_sha256") != request.get("block_input_sha256")
        or result.get("parent_process_identity") != request.get("parent_process_identity")
        or result.get("controller_receipt_sha256")
        != request.get("controller_receipt_sha256")
        or result.get("nonce") != request.get("nonce")
        or result.get("scientific_config_path") != request.get("scientific_config_path")
        or result.get("scientific_config_sha256")
        != request.get("scientific_config_sha256")
        or result.get("solver") != request.get("solver")
        or result.get("all_hours_resolved") is not True
        or result.get("mathematical_infeasibility_inferred_from_failure") is not False
    ):
        raise ValueError("copied worker result/request binding drifted")
    worker_identity = recovery._mapping(
        result.get("worker_process_identity"), "worker process identity"
    )
    if (
        not isinstance(worker_identity.get("pid"), int)
        or not isinstance(worker_identity.get("creation_time_100ns"), int)
        or worker_identity == request.get("parent_process_identity")
    ):
        raise ValueError("copied worker process identity drifted")
    payload = recovery._validate_scientific_payload(
        recovery._mapping(result.get("scientific_payload"), "scientific payload"),
        block_id=str(request["block_id"]),
        expected_block=context["blocks"][str(request["block_id"])],
        config=context["config"],
    )
    _normalize_payload_raw_evidence(payload, "highs")
    if result.get("scientific_payload_sha256") != recovery._canonical_sha256(payload):
        raise ValueError("copied scientific payload canonical hash drifted")
    expected_receipt = {
        "schema": RECEIPT_SCHEMA,
        "authority": expected_authority,
        "request_sha256": result["request_sha256"],
        "worker_payload_sha256": recovery._sha256(payload_path),
        "block_id": result["block_id"],
        "parent_process_identity": result["parent_process_identity"],
        "worker_process_identity": result["worker_process_identity"],
        "controller_receipt_sha256": result["controller_receipt_sha256"],
        "all_hours_resolved": True,
        "controller_validation_passed": True,
        "published_by_controller": True,
        "mathematical_infeasibility_inferred_from_failure": False,
    }
    if receipt != expected_receipt:
        raise ValueError("copied worker receipt/result binding drifted")
    return payload


def _result_manifest(staging: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted(staging.rglob("*")):
        if path.name == "SHA256SUMS.json":
            continue
        if path.is_symlink():
            raise ValueError("pilot result contains symlink")
        if path.is_file():
            result[path.relative_to(staging).as_posix()] = recovery._sha256(path)
        elif not path.is_dir():
            raise ValueError("pilot result contains non-ordinary member")
    return result


def _dispatch_one(
    context: Mapping[str, Any],
    *,
    block_id: str,
    controller: Mapping[str, Any],
    controller_receipt_path: Path,
    python: Path,
    roots: Mapping[str, Path],
) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
    nonce = secrets.token_hex(32)
    attempt = roots["worker"] / block_id / nonce
    attempt.mkdir(parents=True, exist_ok=False)
    request_path = attempt / "request.json"
    result_path = attempt / "payload.json"
    request = _build_request(
        context,
        block_id=block_id,
        controller=controller,
        controller_receipt_path=controller_receipt_path,
        worker_root=roots["worker"],
        python=python,
        result_path=result_path,
        nonce=nonce,
    )
    recovery._atomic_json(request_path, request)
    log_dir = roots["log"] / block_id / nonce
    log_dir.mkdir(parents=True, exist_ok=False)
    with (
        (log_dir / "stdout.log").open("x", encoding="utf-8") as stdout,
        (log_dir / "stderr.log").open("x", encoding="utf-8") as stderr,
    ):
        process = subprocess.Popen(
            [str(python), "-B", "-m", MODULE, "--worker-request", str(request_path)],
            cwd=ROOT,
            stdout=stdout,
            stderr=stderr,
            text=True,
        )
        observed_worker_identity = _process_identity(process.pid)
        wait = recovery._wait_worker(
            process, context["config"]["execution"]["process_isolation"]
        )
    if wait["status"] != "exited" or wait["exit_code"] != 0:
        raise RuntimeError(
            f"pilot worker {block_id} ended {wait['status']}; unresolved, not infeasible"
        )
    result = recovery._mapping(_load_json(result_path, "worker result"), "worker result")
    if result.get("worker_process_identity") != observed_worker_identity:
        raise ValueError("worker PID/creation identity differs from dispatch evidence")
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "authority": request["authority"],
        "request_sha256": recovery._canonical_sha256(request),
        "worker_payload_sha256": recovery._sha256(result_path),
        "block_id": block_id,
        "parent_process_identity": request["parent_process_identity"],
        "worker_process_identity": observed_worker_identity,
        "controller_receipt_sha256": request["controller_receipt_sha256"],
        "all_hours_resolved": True,
        "controller_validation_passed": True,
        "published_by_controller": True,
        "mathematical_infeasibility_inferred_from_failure": False,
    }
    receipt_path = attempt / "receipt.json"
    recovery._atomic_json(receipt_path, receipt)
    payload = _validate_copied_worker_pair(
        result_path,
        receipt_path,
        expected_authority=_authority_bindings(),
        request=request,
        context=context,
    )
    return request, payload, result_path, receipt_path


def _publish_result(
    staging: Path,
    *,
    config: Mapping[str, Any],
    controller: Mapping[str, Any],
    accepted: Mapping[str, tuple[Mapping[str, Any], Path, Path]],
    comparison: Mapping[str, Any],
    formal_after: Mapping[str, Any],
) -> dict[str, object]:
    if list(accepted) != BLOCKS or comparison.get("comparison_passed") is not True:
        raise RuntimeError("complete ordered payloads and passing comparison are required")
    if controller.get("formal_snapshot_before") != formal_after:
        raise ValueError("formal artifacts changed during pilot")
    authority = _authority_bindings()
    payloads: dict[str, dict[str, Any]] = {}
    for block_id, (request, payload_path, receipt_path) in accepted.items():
        payloads[block_id] = _validate_copied_worker_pair(
            payload_path,
            receipt_path,
            expected_authority=authority,
            request=request,
            context=_stage_context(),
        )
    copied_controller = recovery._mapping(
        _load_json(staging / "controller_receipt.json", "copied controller receipt"),
        "controller receipt",
    )
    if copied_controller != dict(controller):
        raise ValueError("copied controller receipt drifted")
    summary = {
        "schema": "rq2_public_grid_two_block_pilot_result_v2",
        "status": "complete_nonformal_pilot",
        "blocks": BLOCKS,
        "all_blocks_resolved": True,
        "named_outage_comparison_passed": True,
        "parent_solver_calls": 0,
        "post_result_review_passed": False,
        "formal_execution_ready": False,
        "claim": False,
        "security_certified": False,
    }
    shutil.copyfile(CONFIG, staging / "config.yaml")
    recovery._atomic_json(staging / "comparison.json", dict(comparison))
    recovery._atomic_json(staging / "summary.json", summary)
    recovery._atomic_json(staging / "SHA256SUMS.json", _result_manifest(staging))
    manifest = recovery._mapping(
        _load_json(staging / "SHA256SUMS.json", "result manifest"), "result manifest"
    )
    expected_inventory = {
        "config.yaml",
        "controller_receipt.json",
        "comparison.json",
        "summary.json",
        *{
            f"workers/{block_id}/{name}"
            for block_id in BLOCKS
            for name in ("payload.json", "receipt.json")
        },
    }
    if set(manifest) != expected_inventory or manifest != _result_manifest(staging):
        raise ValueError("ready-to-rename result bytes drifted")
    for request, payload_path, receipt_path in accepted.values():
        _validate_copied_worker_pair(
            payload_path,
            receipt_path,
            expected_authority=authority,
            request=request,
            context=_stage_context(),
        )
    final_controller = recovery._mapping(
        _load_json(staging / "controller_receipt.json", "final controller receipt"),
        "controller receipt",
    )
    if final_controller != dict(controller) or manifest != _result_manifest(staging):
        raise ValueError("final staging reread drifted before atomic rename")
    return summary


def run(*, validate_only: bool = False) -> dict[str, object]:
    if validate_only:
        from experiments.validate_rq2_public_grid_two_block_pilot_candidate_v2 import (
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
    python = recovery._python_authority(context["config"])
    roots["result"].parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{roots['result'].name}.staging.", dir=roots["result"].parent
        )
    )
    try:
        roots["worker"].mkdir(parents=True, exist_ok=False)
        roots["log"].mkdir(parents=True, exist_ok=False)
        controller_path = staging / "controller_receipt.json"
        controller = _build_controller_receipt(
            config,
            controller_pid=os.getpid(),
            controller_creation_time_100ns=_process_identity(os.getpid())[
                "creation_time_100ns"
            ],
            controller_receipt_path=controller_path,
        )
        recovery._atomic_json(controller_path, controller)
        worker_dir = staging / "workers"
        worker_dir.mkdir()
        accepted: dict[str, tuple[dict[str, Any], Path, Path]] = {}
        payloads: dict[str, dict[str, Any]] = {}
        for block_id in BLOCKS:
            request, payload, source_payload, source_receipt = _dispatch_one(
                context,
                block_id=block_id,
                controller=controller,
                controller_receipt_path=controller_path,
                python=python,
                roots=roots,
            )
            destination = worker_dir / block_id
            destination.mkdir()
            copied_payload = destination / "payload.json"
            copied_receipt = destination / "receipt.json"
            shutil.copyfile(source_payload, copied_payload)
            shutil.copyfile(source_receipt, copied_receipt)
            accepted[block_id] = (request, copied_payload, copied_receipt)
            payloads[block_id] = payload
        comparison = compare_named_outage_0008(
            payloads[BLOCKS[0]], _extract_gurobi_payload()
        )
        summary = _publish_result(
            staging,
            config=config,
            controller=controller,
            accepted=accepted,
            comparison=comparison,
            formal_after=_formal_snapshot(config),
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
