"""Process-isolated execution successor for the RQ2 public-grid v4 stage.

The controller never invokes a solver.  Each scientific block is evaluated by
one fresh hidden worker.  A completed checkpoint is a single atomic envelope
containing both the scientific payload and the controller-issued execution
receipt.  Timeout, resource stop, nonzero exit, incomplete evidence, and an
unresolved scientific payload cannot create a completed checkpoint and are not
evidence of mathematical infeasibility.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from math import isclose, isfinite
from pathlib import Path
from typing import Any

import yaml

from experiments import run_rts_gmlc_public_grid_need_dispatch_v4 as v4
from src.evaluation.execution_machine import (
    execution_host_status,
    require_execution_host,
)
from src.evaluation.rq2_provenance_v3 import (
    canonical_sha256,
    sha256_file,
    stage_base_provenance,
    verify_checkpoint_inventory_bundle,
    write_json,
)
from src.grid.rts_gmlc import load_rts_gmlc_chronological_data
from src.grid.rts_gmlc_grid_need_successor import (
    EXOGENOUS_GRID_INFEASIBILITY,
    FINITE_GRID_NEED,
    UNRESOLVED_GRID_NEED,
)
from src.solvers.rq2_solver_adapter import solver_options, solver_spec

ROOT = Path(__file__).resolve().parents[1]
MODULE = "experiments.run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_v1"
STAGE = "grid_need_dispatch_v4"
REQUEST_SCHEMA = "rq2_grid_need_process_isolated_worker_request_v1"
RESULT_SCHEMA = "rq2_grid_need_process_isolated_worker_result_v1"
CHECKPOINT_SCHEMA = "rq2_grid_need_process_isolated_checkpoint_v1"
RECEIPT_SCHEMA = "rq2_grid_need_process_isolated_execution_receipt_v1"
AttemptIdentity = tuple[str, str]

V4_CORE = ROOT / "experiments/run_rts_gmlc_public_grid_need_dispatch_v4.py"
GRID_ADAPTER = ROOT / "src/grid/rts_gmlc_scuc_solver_successor.py"
SOLVER_ADAPTER = ROOT / "src/solvers/rq2_solver_adapter.py"
RESOURCE_GUARD = ROOT / "experiments/diagnose_rq2_grid_need_gurobi_block.py"
PREREGISTRATION = ROOT / "configs/rq2_public_grid_solver_recovery_preregistration_v2.yaml"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be an object")
    return dict(value)


def _load_yaml_mapping(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} must be an ordinary file")
    return _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), label)


def _load_json_strict(path: Path, label: str) -> Any:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} has duplicate key: {key}")
            result[key] = value
        return result

    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} must be an ordinary file")
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicates,
    )


def _atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite: {path}")
    fd, raw = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if _load_json_strict(temporary, "atomic staging file") != payload:
            raise ValueError("atomic staging readback drifted")
        if path.exists():
            raise FileExistsError(f"target appeared before publication: {path}")
        temporary.replace(path)
        if _load_json_strict(path, "published JSON") != payload:
            raise ValueError("atomic publication readback drifted")
    finally:
        temporary.unlink(missing_ok=True)


def _resolve(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(raw)
    return (path if path.is_absolute() else ROOT / path).resolve()


def _same_or_descendant(candidate: Path, parent: Path) -> bool:
    try:
        candidate.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _require_isolated_roots(config: Mapping[str, Any]) -> dict[str, Path]:
    execution = _mapping(config["execution"], "execution")
    process = _mapping(execution["process_isolation"], "process_isolation")
    roots = {
        "checkpoint": _resolve(execution["checkpoint_directory"], "checkpoint"),
        "output": _resolve(config["output"]["directory"], "output"),
        "worker": _resolve(process["worker_staging_directory"], "worker staging"),
        "attempt_log": _resolve(process["attempt_log_directory"], "attempt log"),
    }
    for left_name, left in roots.items():
        for right_name, right in roots.items():
            if left_name >= right_name:
                continue
            if _same_or_descendant(left, right) or _same_or_descendant(right, left):
                raise ValueError(
                    f"process-isolation roots overlap: {left_name}, {right_name}"
                )
    return roots


def _dispatch_authority_status(
    config_path: Path, config: Mapping[str, Any]
) -> dict[str, bool]:
    """Evaluate the canonical v2 dispatch gate without loading scientific data."""

    preregistration = _load_yaml_mapping(PREREGISTRATION, "v2 preregistration")
    if (
        preregistration.get("schema")
        != "rq2_public_grid_solver_recovery_preregistration_v2"
        or preregistration.get("status") != "frozen_candidate_execution_closed"
    ):
        raise ValueError("v2 preregistration authority drifted")
    successor = _mapping(preregistration["successor"], "v2 successor")
    artifacts = _mapping(preregistration["artifacts"], "v2 artifacts")
    template_artifact = _mapping(
        artifacts["successor_template"], "successor template artifact"
    )
    future = _mapping(preregistration["frozen_future_gates"], "future gates")
    execution = _mapping(config["execution"], "execution")
    process = _mapping(execution["process_isolation"], "process isolation")
    activation = _mapping(config["activation"], "activation")
    canonical_template = _resolve(successor["template_path"], "template path")
    preregistration_bindings = (
        future.get("independent_R4_implementation_review_receipt_path"),
        future.get("full_process_pilot_result_manifest_path"),
        future.get("named_outage_comparison_against_Gurobi_0008_path"),
        future.get("full_process_pilot_post_result_review_receipt_path"),
        future.get("activation_authority_path"),
    )
    config_bindings = (
        activation.get("independent_R4_pass_receipt_path"),
        activation.get("full_process_pilot_result_manifest_path"),
        activation.get("full_process_pilot_post_result_pass_receipt_path"),
        activation.get("activation_authority_path"),
    )
    binding_paths = (*preregistration_bindings, *config_bindings)
    binding_paths_are_ordinary = all(
        isinstance(raw, str)
        and bool(raw)
        and (path := _resolve(raw, "activation binding")).is_file()
        and not path.is_symlink()
        for raw in binding_paths
    )
    config_bindings_match = config_bindings == (
        preregistration_bindings[0],
        preregistration_bindings[1],
        preregistration_bindings[3],
        preregistration_bindings[4],
    )
    return {
        "canonical_config": config_path.resolve() == canonical_template,
        "config_hash_bound": (
            template_artifact.get("path") == successor["template_path"]
            and template_artifact.get("sha256") == _sha256(config_path)
        ),
        "formal_execution_ready": execution.get("formal_execution_ready") is True,
        "preregistered_formal_execution_ready": (
            future.get("formal_execution_ready") is True
        ),
        "independent_R4_review_passed": (
            execution.get("independent_R4_review_passed") is True
            and future.get("independent_R4_implementation_review_passed") is True
            and future.get("latest_independent_R4_review_verdict") == "PASS"
            and future.get("focused_repair_review_pending") is False
        ),
        "full_process_pilot_passed": (
            process.get("two_block_full_process_pilot_post_result_passed") is True
            and future.get("full_process_pilot_post_result_passed") is True
        ),
        "named_outage_comparison_passed": (
            process.get("named_outage_comparison_passed") is True
        ),
        "activation_allowed": (
            activation.get("activation_allowed") is True
            and future.get("activation_allowed") is True
        ),
        "activation_bindings_complete": (
            binding_paths_are_ordinary and config_bindings_match
        ),
        "user_formal_run_authorized": (
            execution.get("user_formal_run_authorized") is True
        ),
        "predecessor_reuse_forbidden": (
            execution.get("predecessor_Gurobi_checkpoint_reuse_allowed") is False
            and execution.get("predecessor_HiGHS_checkpoint_reuse_allowed") is False
        ),
    }


def _require_dispatch_authority(
    config_path: Path, config: Mapping[str, Any]
) -> dict[str, bool]:
    status = _dispatch_authority_status(config_path, config)
    failed = [name for name, passed in status.items() if not passed]
    if failed:
        raise ValueError(
            "process-isolated dispatch authority is closed: " + ", ".join(failed)
        )
    require_execution_host(config["execution"])
    return status


def _implementation_bindings() -> dict[str, dict[str, str]]:
    members = {
        "parent_runner": Path(__file__).resolve(),
        "worker_runner": Path(__file__).resolve(),
        "v4_core": V4_CORE,
        "grid_adapter": GRID_ADAPTER,
        "solver_adapter": SOLVER_ADAPTER,
        "resource_guard": RESOURCE_GUARD,
    }
    bindings: dict[str, dict[str, str]] = {}
    for name, path in members.items():
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"implementation member is not ordinary: {name}")
        bindings[name] = {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": _sha256(path),
        }
    return bindings


def _solver_binding(config: Mapping[str, Any]) -> dict[str, object]:
    solver = _mapping(config["solver"], "solver")
    specification = solver_spec(solver)
    return {
        "contract": solver,
        "options": solver_options(specification),
        "time_limit_is_unset": specification.time_limit_seconds is None,
    }


def _stage_context(config_path: Path) -> dict[str, Any]:
    config_path = config_path.resolve()
    config, grid_root, blocks, marginals, contract_identity = v4._preflight(
        config_path
    )
    stage_inputs = {
        "power_system_blocks_manifest_sha256": config["input"][
            "power_system_blocks_manifest_sha256"
        ],
        "rts_gmlc_source_manifest_sha256": config["grid_source"][
            "manifest_sha256"
        ],
    }
    stage_base = stage_base_provenance(
        stage=STAGE,
        config_path=config_path,
        contract_identity=contract_identity,
        inputs=stage_inputs,
    )
    return {
        "config_path": config_path,
        "config": config,
        "grid_root": grid_root,
        "blocks": blocks,
        "marginals": marginals,
        "contract_identity": contract_identity,
        "stage_inputs": stage_inputs,
        "stage_base": stage_base,
        "stage_base_sha256": canonical_sha256(stage_base),
    }


def _block_input_sha256(block: Sequence[Mapping[str, str]]) -> str:
    return _canonical_sha256([dict(row) for row in block])


def _python_authority(config: Mapping[str, Any]) -> Path:
    process = _mapping(
        config["execution"]["process_isolation"], "process isolation"
    )
    variable = str(process["python_authority_environment_variable"])
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
        raise RuntimeError("executor Python authority drifted")
    return path.resolve()


def _build_request(
    context: Mapping[str, Any],
    *,
    block_id: str,
    parent_pid: int,
    parent_dispatch_started_ns: int,
    nonce: str,
    python_executable: Path,
    worker_result_path: Path,
) -> dict[str, object]:
    block = context["blocks"][block_id]
    roots = _require_isolated_roots(context["config"])
    return {
        "schema": REQUEST_SCHEMA,
        "block_id": block_id,
        "block_input_sha256": _block_input_sha256(block),
        "config_path": str(context["config_path"]),
        "config_sha256": _sha256(context["config_path"]),
        "stage": STAGE,
        "stage_base_provenance_sha256": context["stage_base_sha256"],
        "parent_pid": parent_pid,
        "parent_dispatch_started_ns": parent_dispatch_started_ns,
        "nonce": nonce,
        "python_executable": str(python_executable),
        "python_executable_sha256": _sha256(python_executable),
        "implementation": _implementation_bindings(),
        "solver": _solver_binding(context["config"]),
        "formal_roots": {
            "checkpoint": str(roots["checkpoint"]),
            "output": str(roots["output"]),
        },
        "worker_result_path": str(worker_result_path.resolve()),
    }


def _validate_request(request: Mapping[str, Any], request_path: Path) -> dict[str, Any]:
    expected_keys = {
        "schema",
        "block_id",
        "block_input_sha256",
        "config_path",
        "config_sha256",
        "stage",
        "stage_base_provenance_sha256",
        "parent_pid",
        "parent_dispatch_started_ns",
        "nonce",
        "python_executable",
        "python_executable_sha256",
        "implementation",
        "solver",
        "formal_roots",
        "worker_result_path",
    }
    if set(request) != expected_keys or request.get("schema") != REQUEST_SCHEMA:
        raise ValueError("worker request schema drifted")
    if request.get("stage") != STAGE:
        raise ValueError("worker stage drifted")
    parent_pid = request.get("parent_pid")
    if isinstance(parent_pid, bool) or not isinstance(parent_pid, int) or parent_pid <= 0:
        raise ValueError("worker parent PID is invalid")
    parent_dispatch_started_ns = request.get("parent_dispatch_started_ns")
    if (
        isinstance(parent_dispatch_started_ns, bool)
        or not isinstance(parent_dispatch_started_ns, int)
        or parent_dispatch_started_ns <= 0
        or parent_dispatch_started_ns > time.time_ns()
    ):
        raise ValueError("parent dispatch start evidence is invalid")
    nonce = request.get("nonce")
    if (
        not isinstance(nonce, str)
        or len(nonce) != 64
        or any(character not in "0123456789abcdef" for character in nonce)
    ):
        raise ValueError("worker nonce is invalid")
    if _mapping(request["implementation"], "implementation") != _implementation_bindings():
        raise ValueError("worker implementation identity drifted")
    python = Path(str(request["python_executable"]))
    if (
        not python.is_file()
        or python.is_symlink()
        or python.resolve() != Path(sys.executable).resolve()
        or _sha256(python) != request["python_executable_sha256"]
    ):
        raise ValueError("worker Python identity drifted")
    if os.getppid() != parent_pid:
        raise ValueError("worker PPID does not match the registered parent")
    config_path = Path(str(request["config_path"])).resolve()
    if _sha256(config_path) != request["config_sha256"]:
        raise ValueError("worker config identity drifted")
    config = _load_yaml_mapping(config_path, "worker config")
    _require_dispatch_authority(config_path, config)
    result_path = Path(str(request["worker_result_path"])).resolve()
    if result_path.parent != request_path.resolve().parent:
        raise ValueError("worker result escaped its isolated request directory")
    declared_formal = _mapping(request["formal_roots"], "formal roots")
    if any(
        _same_or_descendant(result_path, Path(str(raw)).resolve())
        for raw in declared_formal.values()
    ):
        raise ValueError("worker result overlaps a formal root")
    if result_path.exists():
        raise FileExistsError("worker result already exists")
    context = _stage_context(config_path)
    block_id = str(request["block_id"])
    if block_id not in context["blocks"]:
        raise ValueError("worker block is not registered")
    if (
        context["config"] != config
        or _sha256(config_path) != request["config_sha256"]
        or context["stage_base_sha256"] != request["stage_base_provenance_sha256"]
        or _block_input_sha256(context["blocks"][block_id])
        != request["block_input_sha256"]
        or _solver_binding(context["config"]) != request["solver"]
    ):
        raise ValueError("worker scientific authority drifted")
    roots = _require_isolated_roots(context["config"])
    formal = _mapping(request["formal_roots"], "formal roots")
    if formal != {
        "checkpoint": str(roots["checkpoint"]),
        "output": str(roots["output"]),
    }:
        raise ValueError("worker formal-root binding drifted")
    return context


def _finite_nonnegative(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{label} must be numeric")
    number = float(value)
    if not isfinite(number) or number < 0.0:
        raise ValueError(f"{label} must be finite and nonnegative")
    return number


def _positive_int(value: object, label: str, *, allow_zero: bool) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    minimum = 0 if allow_zero else 1
    if value < minimum:
        raise ValueError(f"{label} must be at least {minimum}")
    return value


def _close(left: object, right: object, *, absolute: float = 1.0e-9) -> bool:
    if (
        isinstance(left, bool)
        or isinstance(right, bool)
        or not isinstance(left, (int, float))
        or not isinstance(right, (int, float))
    ):
        return False
    left_number = float(left)
    right_number = float(right)
    return isfinite(left_number) and isfinite(right_number) and isclose(
        left_number,
        right_number,
        rel_tol=1.0e-10,
        abs_tol=absolute,
    )


def _require_close(
    observed: object, expected: object, label: str, *, absolute: float = 1.0e-9
) -> None:
    if not _close(observed, expected, absolute=absolute):
        raise ValueError(f"{label} drifted")


def _validate_certificate(
    raw: object,
    *,
    label: str,
    mode: str,
    solver: Mapping[str, Any],
) -> dict[str, Any]:
    certificate = _mapping(raw, label)
    expected_keys = {
        "objective_incumbent_mw",
        "lower_bound_mw",
        "upper_bound_mw",
        "absolute_gap_mw",
        "relative_gap",
        "gap_tolerance_mw",
        "model_variables",
        "model_constraints",
    }
    if set(certificate) != expected_keys:
        raise ValueError(f"{label} fields drifted")
    allow_zero_scale = mode == "no_event"
    _positive_int(
        certificate["model_variables"],
        f"{label}.model_variables",
        allow_zero=allow_zero_scale,
    )
    _positive_int(
        certificate["model_constraints"],
        f"{label}.model_constraints",
        allow_zero=allow_zero_scale,
    )
    observed_gap = (
        None
        if certificate["absolute_gap_mw"] is None
        else _finite_nonnegative(
            certificate["absolute_gap_mw"], f"{label}.absolute_gap_mw"
        )
    )
    observed_relative = (
        None
        if certificate["relative_gap"] is None
        else _finite_nonnegative(
            certificate["relative_gap"], f"{label}.relative_gap"
        )
    )
    observed_gap_tolerance = (
        None
        if certificate["gap_tolerance_mw"] is None
        else _finite_nonnegative(
            certificate["gap_tolerance_mw"], f"{label}.gap_tolerance_mw"
        )
    )
    if mode == "no_event":
        expected = {
            "objective_incumbent_mw": 0.0,
            "lower_bound_mw": 0.0,
            "upper_bound_mw": 0.0,
            "absolute_gap_mw": 0.0,
            "relative_gap": 0.0,
            "gap_tolerance_mw": 0.0,
            "model_variables": 0,
            "model_constraints": 0,
        }
        if certificate != expected:
            raise ValueError(f"{label} no-event certificate drifted")
        return certificate

    lower_raw = certificate["lower_bound_mw"]
    upper_raw = certificate["upper_bound_mw"]
    lower = (
        None
        if lower_raw is None
        else _finite_nonnegative(lower_raw, f"{label}.lower_bound_mw")
    )
    upper = (
        None
        if upper_raw is None
        else _finite_nonnegative(upper_raw, f"{label}.upper_bound_mw")
    )
    tolerance = float(solver["tolerance_mw"])
    mip_gap = float(solver["mip_relative_gap"])
    if lower is not None and upper is not None:
        if lower > upper:
            raise ValueError(f"{label} bound order drifted")
        gap = upper - lower
        relative = gap / max(abs(upper), 1.0e-12)
        gap_tolerance = max(tolerance, mip_gap * max(abs(upper), 1.0))
        if observed_gap != gap:
            raise ValueError(f"{label}.absolute_gap drifted")
        if observed_relative != relative:
            raise ValueError(f"{label}.relative_gap drifted")
        if observed_gap_tolerance != gap_tolerance:
            raise ValueError(f"{label}.gap_tolerance drifted")
    else:
        if observed_gap is not None or observed_relative is not None:
            raise ValueError(f"{label} incomplete bounds cannot carry gap values")
        if upper is None:
            if observed_gap_tolerance is not None:
                raise ValueError(f"{label} missing upper bound cannot carry tolerance")
            gap_tolerance = None
        else:
            gap_tolerance = max(tolerance, mip_gap * max(abs(upper), 1.0))
            if observed_gap_tolerance != gap_tolerance:
                raise ValueError(f"{label}.gap_tolerance drifted")
    incumbent_raw = certificate["objective_incumbent_mw"]
    if mode == "infeasible_event":
        if incumbent_raw is not None:
            raise ValueError(f"{label} infeasible certificate cannot carry an incumbent")
        return certificate
    incumbent = _finite_nonnegative(incumbent_raw, f"{label}.objective_incumbent_mw")
    if lower is None or upper is None or gap_tolerance is None:
        raise ValueError(f"{label} finite certificate requires complete bounds")
    if not lower - gap_tolerance <= incumbent <= upper + gap_tolerance:
        raise ValueError(f"{label} incumbent falls outside certified bounds")
    if abs(incumbent - upper) > gap_tolerance + 1.0e-9:
        raise ValueError(f"{label} incumbent disagrees with the certified upper bound")
    if abs(upper - lower) > gap_tolerance + 1.0e-9:
        raise ValueError(f"{label} certified gap exceeds its frozen tolerance")
    return certificate


def _validate_baseline(
    raw: object,
    *,
    has_event: bool,
    solver: Mapping[str, Any],
) -> dict[str, Any]:
    baseline = _mapping(raw, "baseline audit")
    if not has_event:
        if baseline != {
            "accepted": True,
            "termination_condition": "not_applicable_no_active_outage",
        }:
            raise ValueError("no-event baseline audit drifted")
        return baseline
    expected_keys = {
        "accepted",
        "termination_condition",
        "solver_status",
        "solver_message",
        "objective_usd",
        "lower_bound_usd",
        "upper_bound_usd",
        "absolute_gap_usd",
        "relative_gap",
        "gap_tolerance_usd",
        "maximum_constraint_violation",
        "maximum_integrality_violation",
        "solver_threads",
        "configured_mip_relative_gap",
        "model_variables",
        "model_constraints",
        "solver_name",
        "solver_options",
    }
    if set(baseline) != expected_keys:
        raise ValueError("baseline audit fields drifted")
    if (
        baseline["accepted"] is not True
        or baseline["termination_condition"] not in {"optimal", "globallyOptimal"}
        or baseline["solver_status"] != "ok"
        or not isinstance(baseline["solver_message"], str)
        or not baseline["solver_message"]
        or baseline["solver_name"] != solver_spec(solver).name
        or baseline["solver_options"] != solver_options(solver_spec(solver))
        or baseline["solver_threads"] != solver["threads"]
    ):
        raise ValueError("baseline solver authority or acceptance drifted")
    _positive_int(baseline["model_variables"], "baseline.model_variables", allow_zero=False)
    _positive_int(
        baseline["model_constraints"], "baseline.model_constraints", allow_zero=False
    )
    observed_gap = _finite_nonnegative(
        baseline["absolute_gap_usd"], "baseline.absolute_gap_usd"
    )
    observed_relative = _finite_nonnegative(
        baseline["relative_gap"], "baseline.relative_gap"
    )
    observed_gap_tolerance = _finite_nonnegative(
        baseline["gap_tolerance_usd"], "baseline.gap_tolerance_usd"
    )
    configured_mip_gap = _finite_nonnegative(
        baseline["configured_mip_relative_gap"],
        "baseline.configured_mip_relative_gap",
    )
    frozen_mip_gap = _finite_nonnegative(
        solver["mip_relative_gap"], "solver.mip_relative_gap"
    )
    if configured_mip_gap != frozen_mip_gap:
        raise ValueError("baseline.configured_mip_relative_gap drifted")
    objective = _finite_nonnegative(baseline["objective_usd"], "baseline.objective")
    lower = _finite_nonnegative(baseline["lower_bound_usd"], "baseline.lower_bound")
    upper = _finite_nonnegative(baseline["upper_bound_usd"], "baseline.upper_bound")
    if lower > upper:
        raise ValueError("baseline objective or bound order drifted")
    gap = upper - lower
    relative = gap / max(abs(upper), 1.0e-12)
    scale = max(abs(lower), abs(upper), 1.0)
    tolerance = float(solver["tolerance_mw"])
    gap_tolerance = max(
        tolerance,
        max(float(solver["mip_relative_gap"]), 1.0e-8) * scale,
    )
    if not lower - gap_tolerance <= objective <= upper + gap_tolerance:
        raise ValueError("baseline objective or bound order drifted")
    if observed_gap != gap:
        raise ValueError("baseline.absolute_gap drifted")
    if observed_relative != relative:
        raise ValueError("baseline.relative_gap drifted")
    if observed_gap_tolerance != gap_tolerance:
        raise ValueError("baseline.gap_tolerance drifted")
    violation = _finite_nonnegative(
        baseline["maximum_constraint_violation"], "baseline.constraint_violation"
    )
    integrality = _finite_nonnegative(
        baseline["maximum_integrality_violation"], "baseline.integrality_violation"
    )
    if violation > tolerance or integrality > float(solver["integer_feasibility_tolerance"]):
        raise ValueError("baseline residual exceeds its frozen tolerance")
    if gap > gap_tolerance + 1.0e-9:
        raise ValueError("baseline gap exceeds its frozen tolerance")
    return baseline


def _row_matches(observed: object, expected: object) -> bool:
    if expected is None:
        return observed == ""
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return _close(observed, expected)
    return observed == expected


def _require_row_value(
    row: Mapping[str, Any], key: str, expected: object, label: str
) -> None:
    if not _row_matches(row.get(key), expected):
        raise ValueError(f"{label}.{key} drifted")


def _validate_hour(
    outcome_raw: object,
    output_row_raw: object,
    input_row: Mapping[str, str],
    *,
    solver: Mapping[str, Any],
    dc_demand_mw: float,
) -> str:
    outcome = _mapping(outcome_raw, "hourly outcome")
    output_row = _mapping(output_row_raw, "hourly output row")
    if set(outcome) != {
        "state",
        "resolved_for_pipeline",
        "primary",
        "primary_certificate",
        "zero_dc_confirmation",
        "zero_dc_confirmation_certificate",
        "solver_name",
        "solver_options",
    }:
        raise ValueError("hourly outcome fields drifted")
    if set(output_row) != set(v4._OUTPUT_FIELDS):
        raise ValueError("hourly output row fields drifted")
    for key in v4._BLOCK_FIELDS:
        if output_row.get(key) != input_row[key]:
            raise ValueError(f"hourly input identity drifted: {key}")
    primary = _mapping(outcome["primary"], "primary outcome")
    primary_keys = {
        "source_hour",
        "event_id",
        "component_type",
        "component_uid",
        "resolved",
        "proven_infeasible",
        "grid_need_mw",
        "termination_condition",
        "solver_status",
        "maximum_constraint_violation",
    }
    if set(primary) != primary_keys:
        raise ValueError("primary outcome fields drifted")
    active = bool(input_row["active_event_id"])
    expected_identity = {
        "source_hour": int(input_row["source_hour"]),
        "event_id": input_row["active_event_id"] or None,
        "component_type": input_row["active_component_type"] or None,
        "component_uid": input_row["active_component_uid"] or None,
    }
    if any(primary.get(key) != value for key, value in expected_identity.items()):
        raise ValueError("primary source-hour or outage identity drifted")
    expected_solver_name = solver_spec(solver).name
    expected_options = solver_options(solver_spec(solver)) if active else {}
    if (
        outcome["solver_name"] != expected_solver_name
        or outcome["solver_options"] != expected_options
        or outcome["resolved_for_pipeline"] is not True
        or outcome["state"] == UNRESOLVED_GRID_NEED
    ):
        raise ValueError("hourly solver, state, or resolution authority drifted")
    state = str(outcome["state"])
    tolerance = float(solver["tolerance_mw"])
    if state == FINITE_GRID_NEED:
        if (
            primary["resolved"] is not True
            or primary["proven_infeasible"] is not False
            or outcome["zero_dc_confirmation"] is not None
            or outcome["zero_dc_confirmation_certificate"] is not None
        ):
            raise ValueError("finite grid-need state is internally inconsistent")
        if active:
            if (
                primary["termination_condition"] not in {"optimal", "globallyOptimal"}
                or primary["solver_status"] != "ok"
            ):
                raise ValueError("finite event termination or status drifted")
            certificate_mode = "finite_event"
        else:
            if (
                primary["termination_condition"]
                != "not_applicable_no_active_outage"
                or primary["solver_status"] != "not_applicable"
            ):
                raise ValueError("no-event termination or status drifted")
            certificate_mode = "no_event"
        grid_need = _finite_nonnegative(primary["grid_need_mw"], "primary.grid_need_mw")
        violation = _finite_nonnegative(
            primary["maximum_constraint_violation"], "primary.constraint_violation"
        )
        if grid_need > dc_demand_mw + tolerance or violation > tolerance:
            raise ValueError("finite grid need or residual exceeds frozen bounds")
        if not active and (grid_need != 0.0 or violation != 0.0):
            raise ValueError("no-event grid need and residual must be exactly zero")
        certificate = _validate_certificate(
            outcome["primary_certificate"],
            label="primary certificate",
            mode=certificate_mode,
            solver=solver,
        )
        _require_close(
            certificate["objective_incumbent_mw"],
            grid_need,
            "primary incumbent/grid need",
            absolute=max(tolerance, float(certificate["gap_tolerance_mw"])),
        )
    elif state == EXOGENOUS_GRID_INFEASIBILITY:
        if not active:
            raise ValueError("E0 requires a registered outage event")
        if (
            primary["resolved"] is not False
            or primary["proven_infeasible"] is not True
            or primary["grid_need_mw"] is not None
            or primary["maximum_constraint_violation"] is not None
            or primary["termination_condition"] != "infeasible"
            or not isinstance(primary["solver_status"], str)
            or not primary["solver_status"]
        ):
            raise ValueError("E0 primary outcome is internally inconsistent")
        certificate = _validate_certificate(
            outcome["primary_certificate"],
            label="primary certificate",
            mode="infeasible_event",
            solver=solver,
        )
        zero = _mapping(outcome["zero_dc_confirmation"], "zero-DC confirmation")
        if set(zero) != primary_keys:
            raise ValueError("zero-DC confirmation fields drifted")
        if (
            any(zero.get(key) != value for key, value in expected_identity.items())
            or zero["resolved"] is not False
            or zero["proven_infeasible"] is not True
            or zero["grid_need_mw"] is not None
            or zero["termination_condition"] != "infeasible"
            or not isinstance(zero["solver_status"], str)
            or not zero["solver_status"]
            or zero["maximum_constraint_violation"] is not None
        ):
            raise ValueError("zero-DC E0 confirmation is internally inconsistent")
        zero_certificate = _validate_certificate(
            outcome["zero_dc_confirmation_certificate"],
            label="zero-DC certificate",
            mode="infeasible_event",
            solver=solver,
        )
    else:
        raise ValueError("unregistered hourly grid-need state")

    _require_row_value(output_row, "grid_need_mw", primary["grid_need_mw"], "row")
    _require_row_value(
        output_row,
        "grid_need_fraction",
        None if primary["grid_need_mw"] is None else float(primary["grid_need_mw"]) / dc_demand_mw,
        "row",
    )
    _require_row_value(output_row, "dispatch_resolved", str(primary["resolved"]).lower(), "row")
    _require_row_value(
        output_row,
        "dispatch_proven_infeasible",
        str(primary["proven_infeasible"]).lower(),
        "row",
    )
    _require_row_value(output_row, "dispatch_state", state, "row")
    for row_key, certificate_key in (
        ("dispatch_objective_incumbent_mw", "objective_incumbent_mw"),
        ("dispatch_lower_bound_mw", "lower_bound_mw"),
        ("dispatch_upper_bound_mw", "upper_bound_mw"),
        ("dispatch_absolute_gap_mw", "absolute_gap_mw"),
        ("dispatch_relative_gap", "relative_gap"),
        ("dispatch_gap_tolerance_mw", "gap_tolerance_mw"),
        ("dispatch_model_variables", "model_variables"),
        ("dispatch_model_constraints", "model_constraints"),
    ):
        _require_row_value(output_row, row_key, certificate[certificate_key], "row")
    _require_row_value(
        output_row, "dispatch_termination_condition", primary["termination_condition"], "row"
    )
    _require_row_value(output_row, "dispatch_solver_status", primary["solver_status"], "row")
    _require_row_value(
        output_row, "maximum_constraint_violation", primary["maximum_constraint_violation"], "row"
    )
    zero = outcome["zero_dc_confirmation"]
    zero_certificate = outcome["zero_dc_confirmation_certificate"]
    for row_key, expected in (
        (
            "zero_dc_confirmation_termination_condition",
            None if zero is None else zero["termination_condition"],
        ),
        (
            "zero_dc_confirmation_solver_status",
            None if zero is None else zero["solver_status"],
        ),
        (
            "zero_dc_confirmation_lower_bound_mw",
            None if zero_certificate is None else zero_certificate["lower_bound_mw"],
        ),
        (
            "zero_dc_confirmation_upper_bound_mw",
            None if zero_certificate is None else zero_certificate["upper_bound_mw"],
        ),
        (
            "zero_dc_confirmation_absolute_gap_mw",
            None if zero_certificate is None else zero_certificate["absolute_gap_mw"],
        ),
        (
            "zero_dc_confirmation_model_variables",
            None if zero_certificate is None else zero_certificate["model_variables"],
        ),
        (
            "zero_dc_confirmation_model_constraints",
            None if zero_certificate is None else zero_certificate["model_constraints"],
        ),
    ):
        _require_row_value(output_row, row_key, expected, "row")
    return state


def _validate_scientific_payload(
    payload: Mapping[str, Any],
    *,
    block_id: str,
    expected_block: Sequence[Mapping[str, str]],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    expected_keys = {
        "block_id",
        "split",
        "baseline_audit",
        "all_hours_resolved",
        "exogenous_grid_infeasibility_hour_count",
        "outcomes",
        "rows",
    }
    if set(payload) != expected_keys or payload.get("block_id") != block_id:
        raise ValueError("scientific payload schema or block identity drifted")
    if len(expected_block) != 24:
        raise ValueError("registered scientific block must contain exactly 24 hours")
    if any(set(row) != set(v4._BLOCK_FIELDS) for row in expected_block):
        raise ValueError("registered scientific row fields drifted")
    expected_offsets = [str(index) for index in range(24)]
    expected_source_hours = [str(int(expected_block[0]["source_hour"]) + index) for index in range(24)]
    if (
        [row["block_id"] for row in expected_block] != [block_id] * 24
        or [row["hour_offset"] for row in expected_block] != expected_offsets
        or [row["source_hour"] for row in expected_block] != expected_source_hours
    ):
        raise ValueError("registered 24-hour source inventory drifted")
    rows = payload.get("rows")
    outcomes = payload.get("outcomes")
    if not isinstance(rows, list) or not isinstance(outcomes, list):
        raise TypeError("scientific rows and outcomes must be lists")
    if len(rows) != 24 or len(outcomes) != 24:
        raise ValueError("scientific block must contain exactly 24 hours")
    has_event = any(row["active_event_id"] for row in expected_block)
    _validate_baseline(payload["baseline_audit"], has_event=has_event, solver=config["solver"])
    if payload.get("all_hours_resolved") is not True:
        raise ValueError("unresolved scientific block cannot publish")
    states = [
        _validate_hour(
            outcome,
            row,
            expected,
            solver=config["solver"],
            dc_demand_mw=float(config["model"]["dc_reference_demand_mw"]),
        )
        for outcome, row, expected in zip(outcomes, rows, expected_block, strict=True)
    ]
    expected_e0 = sum(state == EXOGENOUS_GRID_INFEASIBILITY for state in states)
    observed_e0 = payload.get("exogenous_grid_infeasibility_hour_count")
    if (
        isinstance(observed_e0, bool)
        or not isinstance(observed_e0, int)
        or observed_e0 != expected_e0
    ):
        raise ValueError("E0 hour count drifted")
    if payload.get("split") != expected_block[0]["split"]:
        raise ValueError("scientific block split drifted")
    return dict(payload)


def _worker(request_path: Path) -> int:
    worker_started_ns = time.time_ns()
    request_path = request_path.resolve()
    request = _mapping(_load_json_strict(request_path, "worker request"), "request")
    context = _validate_request(request, request_path)
    block_id = str(request["block_id"])
    data = load_rts_gmlc_chronological_data(
        context["grid_root"],
        base_mva=float(context["config"]["grid_source"]["base_mva"]),
    )
    payload = v4._process_block(
        data,
        context["blocks"][block_id],
        dc_bus=int(context["config"]["model"]["dc_bus"]),
        dc_demand_mw=float(
            context["config"]["model"]["dc_reference_demand_mw"]
        ),
        solver=context["config"]["solver"],
    )
    resolved = payload.get("all_hours_resolved") is True
    result = {
        "schema": RESULT_SCHEMA,
        "status": "complete" if resolved else "unresolved",
        "block_id": block_id,
        "request_sha256": _sha256(request_path),
        "config_sha256": request["config_sha256"],
        "stage_base_provenance_sha256": request[
            "stage_base_provenance_sha256"
        ],
        "parent_pid": request["parent_pid"],
        "worker_pid": os.getpid(),
        "worker_parent_pid": os.getppid(),
        "worker_started_ns": worker_started_ns,
        "nonce": request["nonce"],
        "python_executable": str(Path(sys.executable).resolve()),
        "python_executable_sha256": request["python_executable_sha256"],
        "implementation": request["implementation"],
        "solver": request["solver"],
        "scientific_payload": payload,
        "scientific_payload_sha256": _canonical_sha256(payload),
        "all_hours_resolved": resolved,
        "mathematical_infeasibility_inferred_from_failure": False,
    }
    _atomic_json(Path(str(request["worker_result_path"])), result)
    return 0 if resolved else 3


def _resource_probe(pid: int) -> dict[str, object]:
    from experiments.diagnose_rq2_grid_need_gurobi_block import (
        _windows_memory_sample,
    )

    return _windows_memory_sample(pid)


def _resource_stop_reason(
    sample: Mapping[str, object], process: Mapping[str, Any]
) -> str | None:
    if sample.get("sampling_available") is not True:
        return None
    private = sample.get("private_bytes")
    private_limit = int(float(process["private_commit_limit_gib"]) * 1024**3)
    if isinstance(private, int) and private >= private_limit:
        return "private_commit_limit_reached"
    available = sample.get("system_commit_available_bytes")
    reserve = int(
        float(process["minimum_system_commit_available_gib"]) * 1024**3
    )
    if isinstance(available, int) and available <= reserve:
        return "system_commit_reserve_reached"
    return None


def _terminate_confirmed(process: subprocess.Popen[object]) -> None:
    process.kill()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("worker termination could not be confirmed") from error
    if process.poll() is None:
        raise RuntimeError("worker termination remains unconfirmed")


def _wait_worker(
    process_handle: subprocess.Popen[object], process: Mapping[str, Any]
) -> dict[str, object]:
    started = time.monotonic()
    interval = float(process["resource_sample_interval_seconds"])
    watchdog = float(process["external_watchdog_seconds"])
    samples = 0
    while process_handle.poll() is None:
        elapsed = time.monotonic() - started
        if elapsed >= watchdog:
            _terminate_confirmed(process_handle)
            return {
                "status": "timeout",
                "reason": "external_watchdog_reached",
                "exit_code": process_handle.returncode,
                "resource_sample_count": samples,
                "mathematical_infeasibility_inferred": False,
            }
        sample = _resource_probe(process_handle.pid)
        samples += 1
        reason = _resource_stop_reason(sample, process)
        if reason is not None:
            _terminate_confirmed(process_handle)
            return {
                "status": "resource_stop",
                "reason": reason,
                "exit_code": process_handle.returncode,
                "resource_sample_count": samples,
                "mathematical_infeasibility_inferred": False,
            }
        time.sleep(min(interval, max(watchdog - elapsed, 0.05)))
    return {
        "status": "exited",
        "reason": None,
        "exit_code": process_handle.returncode,
        "resource_sample_count": samples,
        "mathematical_infeasibility_inferred": False,
    }


def _validate_worker_result(
    request: Mapping[str, Any],
    result: Mapping[str, Any],
    *,
    request_path: Path,
    observed_pid: int,
    observed_exit_code: int,
    prior_attempt_identities: set[AttemptIdentity],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    expected_keys = {
        "schema",
        "status",
        "block_id",
        "request_sha256",
        "config_sha256",
        "stage_base_provenance_sha256",
        "parent_pid",
        "worker_pid",
        "worker_parent_pid",
        "worker_started_ns",
        "nonce",
        "python_executable",
        "python_executable_sha256",
        "implementation",
        "solver",
        "scientific_payload",
        "scientific_payload_sha256",
        "all_hours_resolved",
        "mathematical_infeasibility_inferred_from_failure",
    }
    if set(result) != expected_keys or result.get("schema") != RESULT_SCHEMA:
        raise ValueError("worker result schema drifted")
    expected = {
        "status": "complete",
        "block_id": request["block_id"],
        "request_sha256": _sha256(request_path),
        "config_sha256": request["config_sha256"],
        "stage_base_provenance_sha256": request[
            "stage_base_provenance_sha256"
        ],
        "parent_pid": request["parent_pid"],
        "worker_pid": observed_pid,
        "worker_parent_pid": request["parent_pid"],
        "nonce": request["nonce"],
        "python_executable": request["python_executable"],
        "python_executable_sha256": request["python_executable_sha256"],
        "implementation": request["implementation"],
        "solver": request["solver"],
        "all_hours_resolved": True,
        "mathematical_infeasibility_inferred_from_failure": False,
    }
    worker_started_ns = result.get("worker_started_ns")
    if (
        observed_exit_code != 0
        or any(result.get(key) != value for key, value in expected.items())
        or isinstance(worker_started_ns, bool)
        or not isinstance(worker_started_ns, int)
        or worker_started_ns < request["parent_dispatch_started_ns"]
        or worker_started_ns > time.time_ns()
    ):
        raise ValueError("worker process identity, exit, or authority drifted")
    if observed_pid == request["parent_pid"]:
        raise ValueError("worker PID must differ from its live parent PID")
    attempt_identity = (str(request["nonce"]), _sha256(request_path))
    if any(
        nonce == attempt_identity[0] or request_hash == attempt_identity[1]
        for nonce, request_hash in prior_attempt_identities
    ):
        raise ValueError("worker attempt nonce or request hash was already consumed")
    payload = _validate_scientific_payload(
        _mapping(result["scientific_payload"], "scientific payload"),
        block_id=str(request["block_id"]),
        expected_block=context["blocks"][str(request["block_id"])],
        config=context["config"],
    )
    if result["scientific_payload_sha256"] != _canonical_sha256(payload):
        raise ValueError("scientific payload hash drifted")
    return payload


def _checkpoint_envelope(
    request: Mapping[str, Any],
    result: Mapping[str, Any],
    *,
    request_path: Path,
    result_path: Path,
    observed_pid: int,
) -> dict[str, object]:
    payload = _mapping(result["scientific_payload"], "scientific payload")
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "block_id": request["block_id"],
        "request_sha256": _sha256(request_path),
        "worker_result_sha256": _sha256(result_path),
        "config_sha256": request["config_sha256"],
        "stage_base_provenance_sha256": request[
            "stage_base_provenance_sha256"
        ],
        "block_input_sha256": request["block_input_sha256"],
        "parent_pid": request["parent_pid"],
        "parent_dispatch_started_ns": request["parent_dispatch_started_ns"],
        "worker_pid": observed_pid,
        "worker_parent_pid": request["parent_pid"],
        "worker_started_ns": result["worker_started_ns"],
        "nonce": request["nonce"],
        "python_executable": request["python_executable"],
        "python_executable_sha256": request["python_executable_sha256"],
        "implementation": request["implementation"],
        "solver": request["solver"],
        "worker_exit_code": 0,
        "all_hours_resolved": True,
        "parent_validation_passed": True,
        "published_by_parent": True,
        "mathematical_infeasibility_inferred_from_failure": False,
    }
    return {
        "schema": CHECKPOINT_SCHEMA,
        "block_id": request["block_id"],
        "config_sha256": request["config_sha256"],
        "stage_base_provenance_sha256": request[
            "stage_base_provenance_sha256"
        ],
        "block_input_sha256": request["block_input_sha256"],
        "scientific_payload": payload,
        "scientific_payload_sha256": _canonical_sha256(payload),
        "execution_receipt": receipt,
        "execution_receipt_sha256": _canonical_sha256(receipt),
    }


def _validate_checkpoint(
    checkpoint: Mapping[str, Any],
    *,
    block_id: str,
    context: Mapping[str, Any],
) -> tuple[dict[str, Any], AttemptIdentity]:
    expected_keys = {
        "schema",
        "block_id",
        "config_sha256",
        "stage_base_provenance_sha256",
        "block_input_sha256",
        "scientific_payload",
        "scientific_payload_sha256",
        "execution_receipt",
        "execution_receipt_sha256",
    }
    expected_identity = {
        "schema": CHECKPOINT_SCHEMA,
        "block_id": block_id,
        "config_sha256": _sha256(context["config_path"]),
        "stage_base_provenance_sha256": context["stage_base_sha256"],
        "block_input_sha256": _block_input_sha256(context["blocks"][block_id]),
    }
    if set(checkpoint) != expected_keys or any(
        checkpoint.get(key) != value for key, value in expected_identity.items()
    ):
        raise ValueError(f"checkpoint identity drifted: {block_id}")
    payload = _validate_scientific_payload(
        _mapping(checkpoint["scientific_payload"], "checkpoint payload"),
        block_id=block_id,
        expected_block=context["blocks"][block_id],
        config=context["config"],
    )
    if checkpoint["scientific_payload_sha256"] != _canonical_sha256(payload):
        raise ValueError(f"checkpoint payload hash drifted: {block_id}")
    receipt = _mapping(checkpoint["execution_receipt"], "execution receipt")
    receipt_keys = {
        "schema",
        "block_id",
        "request_sha256",
        "worker_result_sha256",
        "config_sha256",
        "stage_base_provenance_sha256",
        "block_input_sha256",
        "parent_pid",
        "parent_dispatch_started_ns",
        "worker_pid",
        "worker_parent_pid",
        "worker_started_ns",
        "nonce",
        "python_executable",
        "python_executable_sha256",
        "implementation",
        "solver",
        "worker_exit_code",
        "all_hours_resolved",
        "parent_validation_passed",
        "published_by_parent",
        "mathematical_infeasibility_inferred_from_failure",
    }
    if (
        set(receipt) != receipt_keys
        or checkpoint["execution_receipt_sha256"]
        != _canonical_sha256(receipt)
        or not _is_sha256(checkpoint["scientific_payload_sha256"])
        or not _is_sha256(checkpoint["execution_receipt_sha256"])
    ):
        raise ValueError(f"execution receipt is incomplete: {block_id}")
    receipt_hash_fields = (
        "request_sha256",
        "worker_result_sha256",
        "config_sha256",
        "stage_base_provenance_sha256",
        "block_input_sha256",
        "python_executable_sha256",
    )
    nonce = receipt.get("nonce")
    python = Path(str(receipt.get("python_executable")))
    parent_pid = receipt.get("parent_pid")
    parent_dispatch_started_ns = receipt.get("parent_dispatch_started_ns")
    worker_started_ns = receipt.get("worker_started_ns")
    if (
        receipt.get("schema") != RECEIPT_SCHEMA
        or any(receipt.get(key) != value for key, value in expected_identity.items() if key != "schema")
        or any(not _is_sha256(receipt.get(key)) for key in receipt_hash_fields)
        or not _is_sha256(nonce)
        or isinstance(parent_pid, bool)
        or not isinstance(parent_pid, int)
        or parent_pid <= 0
        or isinstance(parent_dispatch_started_ns, bool)
        or not isinstance(parent_dispatch_started_ns, int)
        or parent_dispatch_started_ns <= 0
        or isinstance(worker_started_ns, bool)
        or not isinstance(worker_started_ns, int)
        or worker_started_ns < parent_dispatch_started_ns
        or not python.is_file()
        or python.is_symlink()
        or python.resolve() != Path(sys.executable).resolve()
        or _sha256(python) != receipt.get("python_executable_sha256")
        or receipt.get("worker_exit_code") != 0
        or receipt.get("all_hours_resolved") is not True
        or receipt.get("parent_validation_passed") is not True
        or receipt.get("published_by_parent") is not True
        or receipt.get("mathematical_infeasibility_inferred_from_failure") is not False
        or receipt.get("implementation") != _implementation_bindings()
        or receipt.get("solver") != _solver_binding(context["config"])
    ):
        raise ValueError(f"execution receipt authority drifted: {block_id}")
    worker_pid = receipt.get("worker_pid")
    parent_pid = receipt.get("parent_pid")
    if (
        isinstance(worker_pid, bool)
        or not isinstance(worker_pid, int)
        or worker_pid <= 0
        or worker_pid == parent_pid
        or receipt.get("worker_parent_pid") != parent_pid
    ):
        raise ValueError(f"execution receipt PID drifted: {block_id}")
    return payload, (str(nonce), str(receipt["request_sha256"]))


def _resume_prefix(
    checkpoint_directory: Path,
    block_ids: Sequence[str],
    context: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], set[AttemptIdentity]]:
    if not checkpoint_directory.exists():
        return [], set()
    if not checkpoint_directory.is_dir() or checkpoint_directory.is_symlink():
        raise ValueError("checkpoint root must be an ordinary directory")
    entries = list(checkpoint_directory.iterdir())
    if any(not item.is_file() or item.is_symlink() or item.suffix != ".json" for item in entries):
        raise ValueError("checkpoint root contains an extra or non-ordinary member")
    observed = {item.name for item in entries}
    expected_names = [f"{block_id}.json" for block_id in block_ids]
    prefix_length = 0
    while prefix_length < len(expected_names) and expected_names[prefix_length] in observed:
        prefix_length += 1
    if observed != set(expected_names[:prefix_length]):
        raise ValueError("resume inventory is not one continuous prefix")
    payloads: list[dict[str, Any]] = []
    attempt_identities: set[AttemptIdentity] = set()
    for block_id in block_ids[:prefix_length]:
        checkpoint = _mapping(
            _load_json_strict(
                checkpoint_directory / f"{block_id}.json", "checkpoint"
            ),
            "checkpoint",
        )
        payload, attempt_identity = _validate_checkpoint(
            checkpoint, block_id=block_id, context=context
        )
        if any(
            nonce == attempt_identity[0] or request_hash == attempt_identity[1]
            for nonce, request_hash in attempt_identities
        ):
            raise ValueError("resume prefix reuses an attempt nonce or request hash")
        attempt_identities.add(attempt_identity)
        payloads.append(payload)
    return payloads, attempt_identities


def _publish_checkpoint_atomic(path: Path, envelope: Mapping[str, Any]) -> None:
    _atomic_json(path, dict(envelope))


def _dispatch_one(
    context: Mapping[str, Any],
    *,
    block_id: str,
    python_executable: Path,
    roots: Mapping[str, Path],
    prior_attempt_identities: set[AttemptIdentity],
) -> dict[str, Any]:
    nonce = secrets.token_hex(32)
    attempt = roots["worker"] / block_id / nonce
    attempt.mkdir(parents=True, exist_ok=False)
    result_path = attempt / "worker_result.json"
    request_path = attempt / "request.json"
    request = _build_request(
        context,
        block_id=block_id,
        parent_pid=os.getpid(),
        parent_dispatch_started_ns=time.time_ns(),
        nonce=nonce,
        python_executable=python_executable,
        worker_result_path=result_path,
    )
    _atomic_json(request_path, request)
    log_dir = roots["attempt_log"] / block_id / nonce
    log_dir.mkdir(parents=True, exist_ok=False)
    stdout_path = log_dir / "stdout.log"
    stderr_path = log_dir / "stderr.log"
    command = [
        str(python_executable),
        "-B",
        "-m",
        MODULE,
        "--worker-request",
        str(request_path),
    ]
    with (
        stdout_path.open("w", encoding="utf-8") as stdout,
        stderr_path.open("w", encoding="utf-8") as stderr,
    ):
        child = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=stdout,
            stderr=stderr,
            text=True,
        )
        wait_report = _wait_worker(
            child, context["config"]["execution"]["process_isolation"]
        )
    controller = {
        "schema": "rq2_grid_need_process_isolated_attempt_v1",
        "block_id": block_id,
        "request_sha256": _sha256(request_path),
        "parent_pid": os.getpid(),
        "worker_pid": child.pid,
        "wait": wait_report,
        "checkpoint_published": False,
        "mathematical_infeasibility_inferred": False,
    }
    _atomic_json(log_dir / "controller.json", controller)
    if wait_report["status"] != "exited" or wait_report["exit_code"] != 0:
        raise RuntimeError(
            f"worker {block_id} ended as {wait_report['status']}; block is unresolved, not infeasible"
        )
    if not result_path.is_file() or result_path.is_symlink():
        raise ValueError("successful worker did not publish an ordinary result")
    result = _mapping(_load_json_strict(result_path, "worker result"), "result")
    _validate_worker_result(
        request,
        result,
        request_path=request_path,
        observed_pid=child.pid,
        observed_exit_code=int(child.returncode),
        prior_attempt_identities=prior_attempt_identities,
        context=context,
    )
    envelope = _checkpoint_envelope(
        request,
        result,
        request_path=request_path,
        result_path=result_path,
        observed_pid=child.pid,
    )
    checkpoint = roots["checkpoint"] / f"{block_id}.json"
    _publish_checkpoint_atomic(checkpoint, envelope)
    return _mapping(result["scientific_payload"], "scientific payload")


def _finalize(
    context: Mapping[str, Any],
    checkpoints: Sequence[Mapping[str, Any]],
    checkpoint_directory: Path,
) -> dict[str, object]:
    config = context["config"]
    blocks = context["blocks"]
    if len(checkpoints) != 1071 or len(checkpoints) != len(blocks):
        raise RuntimeError("finalization requires the complete 1071-block inventory")
    if any(item.get("all_hours_resolved") is not True for item in checkpoints):
        raise RuntimeError("unresolved block prevents final publication")
    expected_files = {f"{block_id}.json" for block_id in blocks}
    observed_files = {
        path.relative_to(checkpoint_directory).as_posix()
        for path in checkpoint_directory.rglob("*.json")
    }
    if observed_files != expected_files:
        raise ValueError("final checkpoint inventory drifted")
    config_path = context["config_path"]
    config_sha = _sha256(config_path)
    target = _resolve(config["output"]["directory"], "output directory")
    if target.exists():
        raise FileExistsError(f"refusing to overwrite output: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    try:
        if _sha256(config_path) != config_sha:
            raise ValueError("config drifted during execution")
        shutil.copyfile(config_path, staging / "config.yaml")
        rows = [row for checkpoint in checkpoints for row in checkpoint["rows"]]
        v4._write_gzip_csv(
            staging / "dispatched_power_system_blocks.csv.gz",
            v4._OUTPUT_FIELDS,
            rows,
        )
        for split in ("training", "holdout"):
            v4._write_gzip_csv(
                staging / f"{split}_marginal.csv.gz",
                ("id", "probability"),
                context["marginals"][split],
            )
        block_status = [
            {
                "block_id": item["block_id"],
                "split": item["split"],
                "all_hours_resolved": item["all_hours_resolved"],
                "baseline_accepted": item["baseline_audit"]["accepted"],
                "exogenous_grid_infeasibility_hour_count": item[
                    "exogenous_grid_infeasibility_hour_count"
                ],
            }
            for item in checkpoints
        ]
        v4._write_gzip_csv(
            staging / "block_status.csv.gz",
            (
                "block_id",
                "split",
                "all_hours_resolved",
                "baseline_accepted",
                "exogenous_grid_infeasibility_hour_count",
            ),
            block_status,
        )
        inventory = {
            block_id: sha256_file(checkpoint_directory / f"{block_id}.json")
            for block_id in sorted(blocks)
        }
        write_json(staging / "checkpoint_inventory.json", inventory)
        provenance = {
            "base": context["stage_base"],
            "checkpoint_inventory": inventory,
            "checkpoint_inventory_sha256": canonical_sha256(inventory),
        }
        write_json(staging / "provenance.json", provenance)
        summary = {
            "schema": config["output"]["schema"],
            "config_sha256": config_sha,
            "stage_base_provenance_sha256": context["stage_base_sha256"],
            "provenance_sha256": sha256_file(staging / "provenance.json"),
            "checkpoint_inventory_sha256": canonical_sha256(inventory),
            "input_manifest_sha256": config["input"][
                "power_system_blocks_manifest_sha256"
            ],
            "block_count": len(checkpoints),
            "training_block_count": len(context["marginals"]["training"]),
            "holdout_block_count": len(context["marginals"]["holdout"]),
            "all_blocks_resolved": True,
            "finite_grid_need_scope": v4.RTS_GMLC_GRID_NEED_SCOPE,
            "exogenous_grid_infeasibility_block_count": sum(
                item["exogenous_grid_infeasibility_hour_count"] > 0
                for item in checkpoints
            ),
            "exogenous_grid_infeasibility_hour_count": sum(
                item["exogenous_grid_infeasibility_hour_count"]
                for item in checkpoints
            ),
            "exogenous_grid_infeasibility_has_finite_grid_need": False,
            "solver_name": solver_spec(config["solver"]).name,
            "normal_scuc_model_scales": sorted(
                {
                    (
                        int(item["baseline_audit"]["model_variables"]),
                        int(item["baseline_audit"]["model_constraints"]),
                    )
                    for item in checkpoints
                    if "model_variables" in item["baseline_audit"]
                }
            ),
            "corrective_lp_model_scales": sorted(
                {
                    (
                        int(outcome["primary_certificate"]["model_variables"]),
                        int(
                            outcome["primary_certificate"][
                                "model_constraints"
                            ]
                        ),
                    )
                    for item in checkpoints
                    for outcome in item["outcomes"]
                    if outcome["primary_certificate"]["model_variables"] > 0
                }
            ),
            "process_isolated_execution": True,
            "fresh_worker_process_count": len(checkpoints),
            "formal_execution_authorized": True,
            "empirical_outage_probability_claimed": False,
            "full_N_minus_one": False,
            "AC_security": False,
            "security_certified": False,
        }
        verify_checkpoint_inventory_bundle(
            provenance,
            inventory,
            summary,
            stage=STAGE,
            expected_config_sha256=config_sha,
            contract_identity=context["contract_identity"],
            expected_inputs=context["stage_inputs"],
            expected_checkpoint_keys=set(blocks),
        )
        write_json(staging / "summary.json", summary)
        names = (
            "block_status.csv.gz",
            "checkpoint_inventory.json",
            "config.yaml",
            "dispatched_power_system_blocks.csv.gz",
            "holdout_marginal.csv.gz",
            "provenance.json",
            "summary.json",
            "training_marginal.csv.gz",
        )
        write_json(
            staging / "SHA256SUMS.json",
            {name: _sha256(staging / name) for name in names},
        )
        if target.exists():
            raise FileExistsError("output appeared before atomic publication")
        staging.rename(target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return summary


def run(
    config_path: Path,
    *,
    validate_only: bool = False,
    maximum_blocks: int | None = None,
) -> dict[str, object]:
    config_path = config_path.resolve()
    candidate_config = _load_yaml_mapping(config_path, "controller config")
    dispatch_authority_config_sha256 = _sha256(config_path)
    dispatch_authority = _dispatch_authority_status(config_path, candidate_config)
    if not validate_only:
        _require_dispatch_authority(config_path, candidate_config)
    context = _stage_context(config_path)
    if not validate_only and (
        context["config"] != candidate_config
        or _sha256(config_path) != dispatch_authority_config_sha256
    ):
        raise ValueError("candidate config drifted after dispatch authorization")
    config = context["config"]
    roots = _require_isolated_roots(config)
    block_ids = sorted(context["blocks"])
    execution = _mapping(config["execution"], "execution")
    process = _mapping(execution["process_isolation"], "process isolation")
    report = {
        "schema": "rq2_grid_need_process_isolated_preflight_v1",
        "config_sha256": _sha256(context["config_path"]),
        "stage_base_provenance_sha256": context["stage_base_sha256"],
        "power_system_block_count": len(block_ids),
        "formal_execution_ready": execution["formal_execution_ready"],
        "independent_R4_review_passed": execution[
            "independent_R4_review_passed"
        ],
        "two_block_full_process_pilot_post_result_passed": process[
            "two_block_full_process_pilot_post_result_passed"
        ],
        "solver_calls": 0,
        "formal_writes": 0,
        "execution_host": execution_host_status(execution),
        "dispatch_authority": dispatch_authority,
    }
    if validate_only:
        return report
    if maximum_blocks is not None and (
        isinstance(maximum_blocks, bool) or maximum_blocks <= 0
    ):
        raise ValueError("maximum_blocks must be a positive integer")
    host_sample = _resource_probe(os.getpid())
    host_stop = _resource_stop_reason(host_sample, process)
    if host_stop is not None:
        raise RuntimeError(
            f"process-isolated start refused by resource gate: {host_stop}; "
            "this is not infeasibility evidence"
        )
    python = _python_authority(config)
    payloads, attempt_identities = _resume_prefix(
        roots["checkpoint"], block_ids, context
    )
    for processed, block_id in enumerate(block_ids[len(payloads) :], start=1):
        payload = _dispatch_one(
            context,
            block_id=block_id,
            python_executable=python,
            roots=roots,
            prior_attempt_identities=attempt_identities,
        )
        checkpoint = _mapping(
            _load_json_strict(
                roots["checkpoint"] / f"{block_id}.json", "new checkpoint"
            ),
            "new checkpoint",
        )
        _, attempt_identity = _validate_checkpoint(
            checkpoint, block_id=block_id, context=context
        )
        if any(
            nonce == attempt_identity[0] or request_hash == attempt_identity[1]
            for nonce, request_hash in attempt_identities
        ):
            raise ValueError("new checkpoint reuses an attempt nonce or request hash")
        attempt_identities.add(attempt_identity)
        payloads.append(payload)
        if maximum_blocks is not None and processed >= maximum_blocks:
            return {
                "schema": "rq2_grid_need_process_isolated_progress_v1",
                "processed_this_call": processed,
                "completed_prefix_count": len(payloads),
                "total_blocks": len(block_ids),
                "formal_result_published": False,
                "mathematical_infeasibility_inferred_from_incomplete": False,
            }
    return _finalize(context, payloads, roots["checkpoint"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            "configs/rts_gmlc_public_grid_need_dispatch_v4_highs_process_isolated_v1.yaml"
        ),
    )
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--maximum-blocks", type=int)
    parser.add_argument("--worker-request", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker_request is not None:
        if args.validate_only or args.maximum_blocks is not None:
            parser.error("hidden worker mode does not accept controller options")
        raise SystemExit(_worker(args.worker_request))
    print(
        json.dumps(
            run(
                args.config,
                validate_only=args.validate_only,
                maximum_blocks=args.maximum_blocks,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
