"""Block-zero HiGHS formal controller with V8 exact-slot resource journals."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import secrets
import subprocess
import sys
import time
from collections.abc import Mapping
from importlib import metadata
from pathlib import Path
from typing import Any

from experiments import (
    rq2_public_grid_highs_formal_activation_contract_v2 as authority,
)
from experiments import (
    rq2_public_grid_two_block_pilot_vnext_execution_contract_v8 as resource_contract,
)
from experiments import (
    run_rq2_public_grid_two_block_pilot_activation_transport_v4 as resource_identity,
)
from experiments import (
    run_rq2_public_grid_two_block_pilot_activation_transport_v5 as resource_primitives,
)
from experiments import (
    run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_v1 as predecessor,
)
from src.grid.rts_gmlc import load_rts_gmlc_chronological_data

ROOT = Path(__file__).resolve().parents[1]
CONFIG = authority.FORMAL_CONFIG
MODULE = (
    "experiments."
    "run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_formal_v3"
)
REQUEST_SCHEMA = "rq2_grid_need_process_isolated_worker_request_formal_v3"
RELEASE_SCHEMA = "rq2_grid_need_process_isolated_worker_release_formal_v3"


class HonestIncomplete(RuntimeError):
    """A stopped or incomplete formal block is unresolved, never infeasible."""


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise authority.FormalActivationRejected(f"{label} must be a mapping")
    return dict(value)


def _atomic_json(path: Path, value: object) -> None:
    authority._atomic_write(path, authority.canonical_bytes(value))
    if json.loads(authority._read_stable(path)) != value:
        raise authority.FormalActivationRejected(f"atomic JSON readback drifted: {path}")


def _implementation_bindings() -> dict[str, dict[str, str]]:
    members = {
        "formal_controller_and_worker": Path(__file__).resolve(),
        "formal_activation_contract": Path(authority.__file__).resolve(),
        "process_isolated_science_predecessor": Path(predecessor.__file__).resolve(),
        "v8_exact_slot_resource_contract": Path(resource_contract.__file__).resolve(),
        "owned_process_identity": Path(resource_identity.__file__).resolve(),
        "resource_primitive": Path(resource_primitives.__file__).resolve(),
    }
    return {
        name: {
            "path": path.relative_to(ROOT).as_posix(),
            "sha256": authority.sha256_file(path),
        }
        for name, path in members.items()
    }


def _runtime_authority_mapping(dynamic_authority: Path) -> dict[str, str]:
    config = authority.load_config()
    one_shot = _mapping(config["one_shot_authority"], "one-shot authority")
    consumed = authority._repo_path(one_shot["consumed_path"], "consumed authority")
    authority.validate_dynamic_authority(dynamic_authority)
    mapping = dict(authority.static_authority_mapping())
    mapping[dynamic_authority.relative_to(ROOT).as_posix()] = authority.sha256_file(
        dynamic_authority
    )
    receipt = dynamic_authority.parent / "activation_receipt.json"
    if not receipt.is_file() or receipt.is_symlink():
        raise authority.FormalActivationRejected(
            "activation attempt receipt is unavailable"
        )
    mapping[receipt.relative_to(ROOT).as_posix()] = authority.sha256_file(receipt)
    mapping[consumed.relative_to(ROOT).as_posix()] = authority.sha256_file(consumed)
    for item in _implementation_bindings().values():
        mapping[item["path"]] = item["sha256"]
    return dict(sorted(mapping.items()))


def _require_consumed_controller_authority(dynamic_authority: Path) -> dict[str, Any]:
    dynamic_authority = dynamic_authority.resolve()
    dynamic = authority.validate_dynamic_authority(dynamic_authority)
    config = authority.load_config()
    one_shot = _mapping(config["one_shot_authority"], "one-shot authority")
    fresh = authority._repo_path(one_shot["fresh_path"], "fresh authority")
    consumed = authority._repo_path(one_shot["consumed_path"], "consumed authority")
    receipt = dynamic_authority.parent / "activation_receipt.json"
    if fresh.exists() or not consumed.is_file() or consumed.is_symlink():
        raise authority.FormalActivationRejected("one-shot authority was not consumed")
    tombstone = authority._load_json(consumed, "consumed authority")
    if (
        tombstone.get("schema")
        != "rq2_public_grid_highs_formal_activation_successor_v2_consumed_authority"
        or tombstone.get("authority_id") != one_shot["authority_id"]
        or tombstone.get("state") != "consumed"
        or tombstone.get("one_shot_reusable") is not False
        or tombstone.get("dynamic_authority_path") != str(dynamic_authority)
        or tombstone.get("dynamic_authority_sha256")
        != authority.sha256_file(dynamic_authority)
        or tombstone.get("activation_receipt_path")
        != str(receipt)
        or tombstone.get("activation_receipt_sha256")
        != authority.sha256_file(receipt)
    ):
        raise authority.FormalActivationRejected("consumed authority drifted")
    return dynamic


def _assert_exact_runtime_environment() -> None:
    if Path.cwd() != ROOT or dict(os.environ) != authority.exact_controller_environment():
        raise authority.FormalActivationRejected("formal cwd/environment drifted")
    runtime = authority.load_config()["runtime"]
    if (
        Path(sys.executable).resolve()
        != Path(str(runtime["locked_python_executable"])).resolve()
        or authority.sha256_file(Path(sys.executable))
        != runtime["locked_python_sha256"]
    ):
        raise authority.FormalActivationRejected("locked Python identity drifted")


def _startup_bindings(dynamic_authority: Path) -> dict[str, dict[str, str]]:
    config = authority.load_config()
    one_shot = _mapping(config["one_shot_authority"], "one-shot authority")
    dynamic = authority.validate_dynamic_authority(dynamic_authority)
    paths = {
        "formal_config": CONFIG,
        "controller": Path(__file__).resolve(),
        "outer": authority.OUTER,
        "dynamic_authority": dynamic_authority.resolve(),
        "preflight": Path(str(dynamic["preflight"]["path"])).resolve(),
        "activation_receipt": dynamic_authority.resolve().parent
        / "activation_receipt.json",
        "consumed_authority": authority._repo_path(
            one_shot["consumed_path"], "consumed authority"
        ),
    }
    return {
        name: {"path": str(path), "sha256": authority.sha256_file(path)}
        for name, path in paths.items()
    }


def _load_stable_json(path: Path, label: str) -> dict[str, Any]:
    raw = authority._read_stable(path)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise authority.FormalActivationRejected(f"{label} is malformed") from exc
    return _mapping(value, label)


def _validate_startup_ack(
    path: Path,
    *,
    handshake: Mapping[str, Any],
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
) -> dict[str, Any]:
    return authority.validate_startup_ack(
        _load_stable_json(path, "startup ack"),
        handshake=handshake,
        controller_identity=controller_identity,
        bootstrap_identity=bootstrap_identity,
    )


def _assert_live_pair(identity: Mapping[str, int], *, label: str) -> None:
    pair = authority._process_identity(identity, label)
    try:
        observed = resource_identity._process_creation_time_ns(pair["pid"])
    except Exception as exc:
        raise authority.FormalActivationRejected(
            f"{label} process is not live"
        ) from exc
    if observed != pair["create_time_ns"]:
        raise authority.FormalActivationRejected(f"{label} create-time drifted")


def _wait_for_file(path: Path, *, own_identity: Mapping[str, int]) -> None:
    settings = _mapping(
        authority.load_config()["startup_handshake"], "startup handshake"
    )
    deadline = time.monotonic() + float(
        settings["controller_wait_timeout_seconds"]
    )
    while not path.is_file():
        _assert_live_pair(own_identity, label="bootstrap")
        if time.monotonic() >= deadline:
            raise authority.FormalActivationRejected(
                f"startup control timed out: {path.name}"
            )
        time.sleep(float(settings["poll_interval_seconds"]))


def _complete_startup_handshake(
    dynamic_authority: Path,
    *,
    bootstrap_identity: Mapping[str, int],
    handshake_path: Path,
    ack_path: Path,
    ready_path: Path,
    release_path: Path,
) -> dict[str, Any]:
    _assert_exact_runtime_environment()
    dynamic = _require_consumed_controller_authority(dynamic_authority)
    _runtime_authority_mapping(dynamic_authority)
    authority.ensure_formal_roots_absent()
    bootstrap_pair = authority._process_identity(
        bootstrap_identity, "bootstrap identity"
    )
    if os.getppid() != bootstrap_pair["pid"]:
        raise authority.FormalActivationRejected("bootstrap parent PID drifted")
    _assert_live_pair(bootstrap_pair, label="bootstrap")
    controller_pair = {
        "pid": os.getpid(),
        "create_time_ns": resource_identity._process_creation_time_ns(os.getpid()),
    }
    expected_paths = authority.startup_paths(dynamic_authority.resolve().parent)
    observed_paths = {
        "handshake": str(handshake_path.resolve()),
        "bootstrap_ack": str(ack_path.resolve()),
        "startup_ready": str(ready_path.resolve()),
        "science_release": str(release_path.resolve()),
        "launch_incomplete": expected_paths["launch_incomplete"],
    }
    command = authority.exact_controller_command(
        dynamic_authority, bootstrap_identity=bootstrap_pair
    )
    if dynamic.get("startup_paths") != observed_paths or dynamic.get("exact_command") != command:
        raise authority.FormalActivationRejected("startup argv/path authority drifted")
    bindings = _startup_bindings(dynamic_authority)
    handshake = authority.build_startup_handshake(
        controller_identity=controller_pair,
        bootstrap_identity=bootstrap_pair,
        bindings=bindings,
        command=command,
        cwd=str(ROOT),
        environment=authority.exact_controller_environment(),
    )
    authority.persist_json_stable(handshake_path, handshake)
    _wait_for_file(ack_path, own_identity=bootstrap_pair)
    ack = _validate_startup_ack(
        ack_path,
        handshake=handshake,
        controller_identity=controller_pair,
        bootstrap_identity=bootstrap_pair,
    )
    authority.ensure_formal_roots_absent()
    ready = {
        "schema": "rq2_public_grid_highs_formal_controller_startup_ready_v2",
        "version": 2,
        "wall_time_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
        "handshake_sha256": authority.canonical_sha256(handshake),
        "ack_sha256": authority.canonical_sha256(ack),
        "controller_identity": controller_pair,
        "bootstrap_identity": bootstrap_pair,
        "authority_mapping_sha256": resource_contract.closure_mapping_sha256(
            _runtime_authority_mapping(dynamic_authority)
        ),
        "formal_roots_absent": True,
        "science_hook_calls": 0,
        "solver_calls": 0,
        "formal_root_writes": 0,
        "formal_started": False,
        "claim": False,
        "security_certified": False,
    }
    authority.persist_json_stable(ready_path, ready)
    _wait_for_file(release_path, own_identity=bootstrap_pair)
    release = _load_stable_json(release_path, "science release")
    if (
        release.get("schema")
        != "rq2_public_grid_highs_formal_bootstrap_science_release_v2"
        or release.get("version") != 2
        or release.get("ready_sha256") != authority.canonical_sha256(ready)
        or release.get("controller_identity") != controller_pair
        or release.get("bootstrap_identity") != bootstrap_pair
        or release.get("science_start_authorized") is not True
        or release.get("retry_allowed") is not False
        or release.get("resume_allowed") is not False
    ):
        raise authority.FormalActivationRejected("science release authority drifted")
    _assert_live_pair(bootstrap_pair, label="bootstrap")
    return {
        "dynamic_authority": dynamic,
        "handshake": handshake,
        "ack": ack,
        "ready": ready,
        "release": release,
    }


def _build_request(
    context: Mapping[str, Any],
    *,
    block_id: str,
    nonce: str,
    python_executable: Path,
    result_path: Path,
    runtime_evidence_path: Path,
    release_path: Path,
    dynamic_authority: Path,
) -> dict[str, Any]:
    base = predecessor._build_request(
        context,
        block_id=block_id,
        parent_pid=os.getpid(),
        parent_dispatch_started_ns=time.time_ns(),
        nonce=nonce,
        python_executable=python_executable,
        worker_result_path=result_path,
    )
    base["schema"] = REQUEST_SCHEMA
    base["implementation"] = _implementation_bindings()
    base["release_path"] = str(release_path.resolve())
    base["solver_runtime_evidence_path"] = str(runtime_evidence_path.resolve())
    base["dynamic_activation_authority_path"] = str(dynamic_authority.resolve())
    base["dynamic_activation_authority_sha256"] = authority.sha256_file(
        dynamic_authority
    )
    base["starts_from_block_zero"] = True
    base["resume_allowed"] = False
    return base


def _validate_request(request: Mapping[str, Any], request_path: Path) -> dict[str, Any]:
    expected = {
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
        "solver_runtime_evidence_path",
        "release_path",
        "dynamic_activation_authority_path",
        "dynamic_activation_authority_sha256",
        "starts_from_block_zero",
        "resume_allowed",
    }
    if set(request) != expected or request.get("schema") != REQUEST_SCHEMA:
        raise authority.FormalActivationRejected("worker request schema drifted")
    if (
        request.get("stage") != predecessor.STAGE
        or request.get("implementation") != _implementation_bindings()
        or request.get("starts_from_block_zero") is not True
        or request.get("resume_allowed") is not False
    ):
        raise authority.FormalActivationRejected("worker request authority drifted")
    parent_pid = request.get("parent_pid")
    started = request.get("parent_dispatch_started_ns")
    nonce = request.get("nonce")
    if (
        type(parent_pid) is not int
        or parent_pid <= 0
        or os.getppid() != parent_pid
        or type(started) is not int
        or started <= 0
        or started > time.time_ns()
        or not authority._is_sha256(nonce)
    ):
        raise authority.FormalActivationRejected("worker parent/nonce drifted")
    python = Path(str(request["python_executable"])).resolve()
    if (
        python != Path(sys.executable).resolve()
        or not python.is_file()
        or python.is_symlink()
        or authority.sha256_file(python) != request["python_executable_sha256"]
    ):
        raise authority.FormalActivationRejected("worker Python identity drifted")
    dynamic = Path(str(request["dynamic_activation_authority_path"])).resolve()
    if (
        authority.sha256_file(dynamic)
        != request["dynamic_activation_authority_sha256"]
    ):
        raise authority.FormalActivationRejected("worker dynamic authority drifted")
    _require_consumed_controller_authority(dynamic)
    config_path = Path(str(request["config_path"])).resolve()
    if config_path != CONFIG or authority.sha256_file(config_path) != request["config_sha256"]:
        raise authority.FormalActivationRejected("worker formal config drifted")
    result_path = Path(str(request["worker_result_path"])).resolve()
    runtime_evidence_path = Path(
        str(request["solver_runtime_evidence_path"])
    ).resolve()
    release_path = Path(str(request["release_path"])).resolve()
    if (
        result_path.parent != request_path.resolve().parent
        or runtime_evidence_path.parent != result_path.parent
        or release_path.parent != result_path.parent
        or result_path.exists()
        or runtime_evidence_path.exists()
        or release_path.exists()
    ):
        raise authority.FormalActivationRejected("worker isolated paths drifted")
    context = predecessor._stage_context(config_path)
    block_id = str(request["block_id"])
    if (
        block_id not in context["blocks"]
        or context["stage_base_sha256"]
        != request["stage_base_provenance_sha256"]
        or predecessor._block_input_sha256(context["blocks"][block_id])
        != request["block_input_sha256"]
        or predecessor._solver_binding(context["config"]) != request["solver"]
    ):
        raise authority.FormalActivationRejected("worker scientific authority drifted")
    return context


def _wait_for_release(request: Mapping[str, Any], request_path: Path) -> None:
    release_path = Path(str(request["release_path"])).resolve()
    deadline = time.monotonic() + 30.0
    while not release_path.is_file():
        if time.monotonic() >= deadline:
            raise HonestIncomplete("first-sample release was not received")
        time.sleep(0.01)
    release = authority._load_json(release_path, "worker release")
    if (
        release.get("schema") != RELEASE_SCHEMA
        or release.get("request_sha256") != authority.sha256_file(request_path)
        or release.get("dynamic_activation_authority_sha256")
        != request["dynamic_activation_authority_sha256"]
        or release.get("first_same_pair_resource_sample_passed") is not True
    ):
        raise authority.FormalActivationRejected("worker release authority drifted")


def _collect_formal_solver_runtime_evidence(
    worker_identity: Mapping[str, int], context: Mapping[str, Any]
) -> dict[str, Any]:
    import highspy

    runtime = _mapping(authority.load_config()["runtime"], "runtime")
    instance = highspy.Highs()
    evidence = {
        "schema": "rq2_public_grid_highs_formal_solver_runtime_evidence_v1",
        "version": 1,
        "worker_identity": dict(worker_identity),
        "observed_wall_time_ns": time.time_ns(),
        "observed_monotonic_ns": time.monotonic_ns(),
        "locked_python_executable": str(Path(sys.executable).resolve()),
        "locked_python_sha256": authority.sha256_file(Path(sys.executable)),
        "highspy_metadata_version": metadata.version("highspy"),
        "highs_runtime_api_version": instance.version(),
        "highs_runtime_version_components": {
            "major": instance.versionMajor(),
            "minor": instance.versionMinor(),
            "patch": instance.versionPatch(),
        },
        "highspy_package_init_path": str(Path(highspy.__file__).resolve()),
        "highspy_package_init_sha256": authority.sha256_file(
            Path(highspy.__file__).resolve()
        ),
        "highspy_python_source_path": runtime["highspy_python_source_path"],
        "highspy_python_source_sha256": authority.sha256_file(
            Path(runtime["highspy_python_source_path"])
        ),
        "highspy_binary_path": runtime["highspy_binary_path"],
        "highspy_binary_sha256": authority.sha256_file(
            Path(runtime["highspy_binary_path"])
        ),
        "formal_solver_binding": predecessor._solver_binding(context["config"]),
        "threads": context["config"]["solver"]["threads"],
        "solver_instance_created": True,
        "solver_solve_called_by_runtime_probe": False,
        "security_certified": False,
    }
    return _validate_formal_solver_runtime_evidence(
        evidence, worker_identity=worker_identity, context=context
    )


def _validate_formal_solver_runtime_evidence(
    value: Mapping[str, Any],
    *,
    worker_identity: Mapping[str, int],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    runtime = _mapping(authority.load_config()["runtime"], "runtime")
    expected_keys = {
        "schema",
        "version",
        "worker_identity",
        "observed_wall_time_ns",
        "observed_monotonic_ns",
        "locked_python_executable",
        "locked_python_sha256",
        "highspy_metadata_version",
        "highs_runtime_api_version",
        "highs_runtime_version_components",
        "highspy_package_init_path",
        "highspy_package_init_sha256",
        "highspy_python_source_path",
        "highspy_python_source_sha256",
        "highspy_binary_path",
        "highspy_binary_sha256",
        "formal_solver_binding",
        "threads",
        "solver_instance_created",
        "solver_solve_called_by_runtime_probe",
        "security_certified",
    }
    if (
        set(value) != expected_keys
        or value.get("schema")
        != "rq2_public_grid_highs_formal_solver_runtime_evidence_v1"
        or value.get("version") != 1
        or value.get("worker_identity") != dict(worker_identity)
        or type(value.get("observed_wall_time_ns")) is not int
        or type(value.get("observed_monotonic_ns")) is not int
        or value.get("locked_python_executable")
        != str(Path(runtime["locked_python_executable"]).resolve())
        or value.get("locked_python_sha256") != runtime["locked_python_sha256"]
        or value.get("highspy_metadata_version") != "1.15.1"
        or value.get("highs_runtime_api_version") != "1.15.1"
        or value.get("highs_runtime_version_components")
        != {"major": 1, "minor": 15, "patch": 1}
        or value.get("highspy_package_init_path")
        != runtime["highspy_package_init_path"]
        or value.get("highspy_package_init_sha256")
        != runtime["highspy_package_init_sha256"]
        or value.get("highspy_python_source_path")
        != runtime["highspy_python_source_path"]
        or value.get("highspy_python_source_sha256")
        != runtime["highspy_python_source_sha256"]
        or value.get("highspy_binary_path") != runtime["highspy_binary_path"]
        or value.get("highspy_binary_sha256") != runtime["highspy_binary_sha256"]
        or value.get("formal_solver_binding")
        != predecessor._solver_binding(context["config"])
        or value.get("threads") != 4
        or value.get("solver_instance_created") is not True
        or value.get("solver_solve_called_by_runtime_probe") is not False
        or value.get("security_certified") is not False
    ):
        raise authority.FormalActivationRejected(
            "actual formal solver runtime evidence drifted"
        )
    return dict(value)


def _worker(request_path: Path) -> int:
    worker_started_ns = time.time_ns()
    request_path = request_path.resolve()
    request = _mapping(
        predecessor._load_json_strict(request_path, "worker request"), "request"
    )
    context = _validate_request(request, request_path)
    _wait_for_release(request, request_path)
    block_id = str(request["block_id"])
    worker_identity = {
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "create_time_ns": resource_identity._process_creation_time_ns(os.getpid()),
    }
    runtime_evidence = _collect_formal_solver_runtime_evidence(
        worker_identity, context
    )
    _atomic_json(
        Path(str(request["solver_runtime_evidence_path"])), runtime_evidence
    )
    data = load_rts_gmlc_chronological_data(
        context["grid_root"],
        base_mva=float(context["config"]["grid_source"]["base_mva"]),
    )
    payload = predecessor.v4._process_block(
        data,
        context["blocks"][block_id],
        dc_bus=int(context["config"]["model"]["dc_bus"]),
        dc_demand_mw=float(context["config"]["model"]["dc_reference_demand_mw"]),
        solver=context["config"]["solver"],
    )
    resolved = payload.get("all_hours_resolved") is True
    result = {
        "schema": predecessor.RESULT_SCHEMA,
        "status": "complete" if resolved else "unresolved",
        "block_id": block_id,
        "request_sha256": authority.sha256_file(request_path),
        "config_sha256": request["config_sha256"],
        "stage_base_provenance_sha256": request["stage_base_provenance_sha256"],
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
        "scientific_payload_sha256": predecessor._canonical_sha256(payload),
        "all_hours_resolved": resolved,
        "mathematical_infeasibility_inferred_from_failure": False,
    }
    _atomic_json(Path(str(request["worker_result_path"])), result)
    return 0 if resolved else 3


class _TerminationAuditProxy:
    def __init__(self, process: subprocess.Popen[Any]) -> None:
        self._process = process
        self.pid = process.pid
        self.action: str | None = None

    def poll(self) -> int | None:
        return self._process.poll()

    def terminate(self) -> None:
        self.action = "terminate_only"
        self._process.terminate()

    def kill(self) -> None:
        self.action = "terminate_then_kill"
        self._process.kill()

    def wait(self, timeout: float | None = None) -> int:
        return self._process.wait(timeout=timeout)


def _terminate_exact(
    process: subprocess.Popen[Any], **identity: int
) -> dict[str, object]:
    audited = _TerminationAuditProxy(process)
    resource_primitives.terminate_exact_owned_child(audited, **identity)
    return {
        "termination_action": audited.action or "already_exited_before_signal",
        "termination_completed": True,
    }


def _persist_resource_journal(path: Path, journal: dict[str, Any]) -> dict[str, Any]:
    raw = resource_contract.exact_json_bytes(journal)
    authority._atomic_write(path, raw)
    if authority._read_stable(path) != raw:
        raise authority.FormalActivationRejected("resource journal readback drifted")
    match = journal["resource_sampler_binding"]["authority_mapping_match"]
    return {
        "schema": (
            "rq2_public_grid_resource_monitor_persisted_outcome_"
            "vnext_execution_v8"
        ),
        "version": 1,
        "resource_journal": journal,
        "persisted_path": str(path),
        "persisted_sha256": resource_contract.sha256_bytes(raw),
        "readback_verified": True,
        "authority_mapping_match": match,
        "controller_acceptable": match,
    }


def _start_resource_monitor(
    process: subprocess.Popen[Any],
    *,
    create_time_ns: int,
    dynamic_authority: Path,
    persistence_path: Path,
) -> tuple[
    resource_contract.ResourceMonitorState,
    concurrent.futures.ThreadPoolExecutor,
    concurrent.futures.Future[dict[str, Any]],
]:
    identity = {"pid": process.pid, "create_time_ns": create_time_ns}
    start_mono = time.monotonic_ns()
    start_wall = time.time_ns()
    mapping = _runtime_authority_mapping(dynamic_authority)
    resource = resource_primitives
    completed_mono = time.monotonic_ns()
    completed_wall = time.time_ns()
    prebinding = {
        "schema": "rq2_public_grid_resource_sampler_prebinding_vnext_execution_v8",
        "version": 1,
        "binding_start_wall_time_ns": start_wall,
        "binding_start_monotonic_ns": start_mono,
        "binding_completed_wall_time_ns": completed_wall,
        "binding_completed_monotonic_ns": completed_mono,
        "expected_owned_identity": identity,
        "pre_monitor_authority_mapping_sha256": (
            resource_contract.closure_mapping_sha256(mapping)
        ),
        "sampler_scope": "one_owned_child_one_session_no_cross_child_or_session_reuse",
        "sampler_callback": "exact_pid_create_time_same_pair_observation_only",
        "resource_values_cached_between_slots": False,
        "sampler_reused_across_child_or_session": False,
    }

    def sample_pair(pid: int, expected_create_time_ns: int) -> tuple[int, int]:
        if {"pid": pid, "create_time_ns": expected_create_time_ns} != identity:
            raise authority.FormalActivationRejected("resource sampler identity drifted")
        observed = resource.sample_resource_pair(pid, expected_create_time_ns)
        return (
            observed.child_private_commit_bytes,
            observed.system_commit_available_bytes,
        )

    state = resource_contract.ResourceMonitorState()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(
        resource_contract.monitor_owned_child_resources_journal,
        process,
        expected_pid=process.pid,
        expected_create_time_ns=create_time_ns,
        watchdog_duration_ns=resource_contract.WATCHDOG_NS,
        state=state,
        sample=sample_pair,
        terminate=_terminate_exact,
        sampler_prebinding=prebinding,
        verify_post_authority=lambda: _runtime_authority_mapping(dynamic_authority),
        persist=lambda journal: _persist_resource_journal(persistence_path, journal),
        persistence_path=str(persistence_path),
    )
    return state, executor, future


def attach_resource_journal_for_test(
    envelope: Mapping[str, Any], journal: Mapping[str, Any], *, persisted_path: str
) -> dict[str, Any]:
    value = dict(envelope)
    receipt = _mapping(value["execution_receipt"], "execution receipt")
    resource = dict(journal)
    digest = authority.canonical_sha256(resource)
    receipt.update(
        {
            "resource_journal": resource,
            "resource_journal_sha256": digest,
            "resource_journal_persisted_path": persisted_path,
            "resource_journal_stable_readback_verified": True,
            "mathematical_infeasibility_inferred_from_resource_failure": False,
        }
    )
    value["execution_receipt"] = receipt
    value["execution_receipt_sha256"] = predecessor._canonical_sha256(receipt)
    value["resource_journal"] = resource
    value["resource_journal_sha256"] = digest
    value["resource_journal_persisted_path"] = persisted_path
    return value


def _attach_runtime_evidence(
    envelope: Mapping[str, Any],
    runtime_evidence: Mapping[str, Any],
    *,
    persisted_path: str,
) -> dict[str, Any]:
    value = dict(envelope)
    receipt = _mapping(value["execution_receipt"], "execution receipt")
    evidence = dict(runtime_evidence)
    digest = authority.canonical_sha256(evidence)
    receipt.update(
        {
            "solver_runtime_evidence": evidence,
            "solver_runtime_evidence_sha256": digest,
            "solver_runtime_evidence_persisted_path": persisted_path,
            "actual_highspy_version_verified": True,
            "actual_highs_runtime_api_version_verified": True,
        }
    )
    value["execution_receipt"] = receipt
    value["execution_receipt_sha256"] = predecessor._canonical_sha256(receipt)
    value["solver_runtime_evidence"] = evidence
    value["solver_runtime_evidence_sha256"] = digest
    value["solver_runtime_evidence_persisted_path"] = persisted_path
    return value


def _dispatch_one(
    context: Mapping[str, Any],
    *,
    block_id: str,
    python_executable: Path,
    roots: Mapping[str, Path],
    dynamic_authority: Path,
    prior_attempt_identities: set[predecessor.AttemptIdentity],
) -> dict[str, Any]:
    nonce = secrets.token_hex(32)
    attempt = roots["worker"] / block_id / nonce
    attempt.mkdir(parents=True, exist_ok=False)
    request_path = attempt / "request.json"
    result_path = attempt / "worker_result.json"
    runtime_evidence_path = attempt / "solver_runtime_evidence.json"
    release_path = attempt / "release.json"
    request = _build_request(
        context,
        block_id=block_id,
        nonce=nonce,
        python_executable=python_executable,
        result_path=result_path,
        runtime_evidence_path=runtime_evidence_path,
        release_path=release_path,
        dynamic_authority=dynamic_authority,
    )
    _atomic_json(request_path, request)
    log_dir = roots["log"] / block_id / nonce
    log_dir.mkdir(parents=True, exist_ok=False)
    journal_path = log_dir / "resource_journal.json"
    command = [
        str(python_executable),
        "-B",
        "-m",
        MODULE,
        "--worker-request",
        str(request_path),
    ]
    with (
        (log_dir / "stdout.log").open("w", encoding="utf-8") as stdout,
        (log_dir / "stderr.log").open("w", encoding="utf-8") as stderr,
    ):
        child = subprocess.Popen(
            command,
            cwd=ROOT,
            env=authority.exact_controller_environment(),
            stdout=stdout,
            stderr=stderr,
            text=True,
        )
        create_time_ns = resource_identity._process_creation_time_ns(child.pid)
        state, executor, future = _start_resource_monitor(
            child,
            create_time_ns=create_time_ns,
            dynamic_authority=dynamic_authority,
            persistence_path=journal_path,
        )
        try:
            if not state.ready.wait(timeout=30) or not state.first_sample_success:
                outcome = future.result(timeout=10) if future.done() else None
                raise HonestIncomplete(
                    f"first same-pair sample failed; outcome={outcome}"
                )
            release = {
                "schema": RELEASE_SCHEMA,
                "request_sha256": authority.sha256_file(request_path),
                "dynamic_activation_authority_sha256": authority.sha256_file(
                    dynamic_authority
                ),
                "first_same_pair_resource_sample_passed": True,
                "release_wall_time_ns": time.time_ns(),
                "release_monotonic_ns": time.monotonic_ns(),
            }
            _atomic_json(release_path, release)
            persisted = future.result(
                timeout=resource_contract.WATCHDOG_NS / 1_000_000_000 + 10
            )
        finally:
            executor.shutdown(wait=True, cancel_futures=True)
    monitor_outcome = resource_contract.validate_resource_monitor_outcome(
        persisted, expected_path=str(journal_path)
    )
    journal = resource_contract.validate_resource_journal(
        _mapping(monitor_outcome["resource_journal"], "resource journal")
    )
    child.wait(timeout=10)
    runtime_evidence: dict[str, Any] | None = None
    if runtime_evidence_path.is_file() and not runtime_evidence_path.is_symlink():
        candidate = _mapping(
            predecessor._load_json_strict(
                runtime_evidence_path, "solver runtime evidence"
            ),
            "solver runtime evidence",
        )
        runtime_evidence = _validate_formal_solver_runtime_evidence(
            candidate,
            worker_identity={
                "pid": child.pid,
                "ppid": os.getpid(),
                "create_time_ns": create_time_ns,
            },
            context=context,
        )
    controller_receipt = {
        "schema": "rq2_grid_need_process_isolated_attempt_formal_v3",
        "block_id": block_id,
        "request_sha256": authority.sha256_file(request_path),
        "worker_pid": child.pid,
        "worker_create_time_ns": create_time_ns,
        "worker_exit_code": child.returncode,
        "resource_journal_path": str(journal_path),
        "resource_journal_sha256": authority.sha256_file(journal_path),
        "resource_status": journal["status"],
        "resource_sample_count": journal["sample_count"],
        "solver_runtime_evidence_path": (
            str(runtime_evidence_path) if runtime_evidence is not None else None
        ),
        "solver_runtime_evidence_sha256": (
            authority.sha256_file(runtime_evidence_path)
            if runtime_evidence is not None
            else None
        ),
        "solver_runtime_evidence_complete": runtime_evidence is not None,
        "mathematical_infeasibility_inferred": False,
    }
    _atomic_json(log_dir / "controller.json", controller_receipt)
    if journal["status"] != "child_exited" or journal["honest_incomplete"] is not False:
        raise HonestIncomplete(
            f"resource monitor stopped {block_id}: {journal['status']}; "
            "unresolved, not infeasible"
        )
    resource_contract.validate_success_resource_journal(journal)
    if child.returncode != 0:
        raise HonestIncomplete(
            f"worker {block_id} exited {child.returncode}; unresolved, not infeasible"
        )
    if runtime_evidence is None:
        raise HonestIncomplete(
            f"worker {block_id} omitted solver runtime evidence; unresolved, not infeasible"
        )
    result = _mapping(
        predecessor._load_json_strict(result_path, "worker result"), "worker result"
    )
    payload = predecessor._validate_worker_result(
        request,
        result,
        request_path=request_path,
        observed_pid=child.pid,
        observed_exit_code=int(child.returncode),
        prior_attempt_identities=prior_attempt_identities,
        context=context,
    )
    envelope = predecessor._checkpoint_envelope(
        request,
        result,
        request_path=request_path,
        result_path=result_path,
        observed_pid=child.pid,
    )
    envelope = attach_resource_journal_for_test(
        envelope, journal, persisted_path=str(journal_path)
    )
    envelope = _attach_runtime_evidence(
        envelope,
        runtime_evidence,
        persisted_path=str(runtime_evidence_path),
    )
    checkpoint = roots["checkpoint"] / f"{block_id}.json"
    _atomic_json(checkpoint, envelope)
    if json.loads(authority._read_stable(checkpoint)) != envelope:
        raise authority.FormalActivationRejected("checkpoint readback drifted")
    prior_attempt_identities.add((nonce, authority.sha256_file(request_path)))
    return payload


def validate_only(config_path: Path = CONFIG) -> dict[str, Any]:
    if config_path.resolve() != CONFIG.resolve():
        raise authority.FormalActivationRejected("only canonical formal config is accepted")
    static = authority.validate_static_authority(require_activation_review=False)
    context = predecessor._stage_context(CONFIG)
    config = context["config"]
    execution = _mapping(config["execution"], "execution")
    process = _mapping(execution["process_isolation"], "process isolation")
    solver = _mapping(config["solver"], "solver")
    if len(context["blocks"]) != 1071:
        raise authority.FormalActivationRejected("formal block inventory drifted")
    return {
        "schema": "rq2_grid_need_process_isolated_formal_preflight_v3",
        "validation_passed": True,
        "config_sha256": authority.sha256_file(CONFIG),
        "power_system_block_count": len(context["blocks"]),
        "starts_from_block_zero": execution["starts_from_block_zero"],
        "resume_allowed": execution["resume_allowed"],
        "predecessor_gurobi_checkpoint_reuse_allowed": execution[
            "predecessor_Gurobi_checkpoint_reuse_allowed"
        ],
        "predecessor_highs_checkpoint_reuse_allowed": execution[
            "predecessor_HiGHS_checkpoint_reuse_allowed"
        ],
        "solver_name": solver["name"],
        "highspy_version": metadata.version("highspy"),
        "threads": solver["threads"],
        "sample_interval_seconds": process["resource_sample_interval_seconds"],
        "solver_calls": 0,
        "formal_root_writes": 0,
        "formal_execution_authorized": False,
        "static_authority": static,
    }


def run(
    config_path: Path,
    dynamic_authority: Path,
    *,
    bootstrap_identity: Mapping[str, int],
    handshake_path: Path,
    ack_path: Path,
    ready_path: Path,
    release_path: Path,
) -> dict[str, object]:
    if config_path.resolve() != CONFIG.resolve():
        raise authority.FormalActivationRejected("only canonical formal config is accepted")
    _complete_startup_handshake(
        dynamic_authority,
        bootstrap_identity=bootstrap_identity,
        handshake_path=handshake_path,
        ack_path=ack_path,
        ready_path=ready_path,
        release_path=release_path,
    )
    _assert_exact_runtime_environment()
    _require_consumed_controller_authority(dynamic_authority)
    authority.ensure_formal_roots_absent()
    context = predecessor._stage_context(CONFIG)
    block_ids = sorted(context["blocks"])
    if len(block_ids) != 1071:
        raise authority.FormalActivationRejected("formal block inventory drifted")
    roots = predecessor._require_isolated_roots(context["config"])
    for name in ("checkpoint", "worker", "attempt_log"):
        roots[name].mkdir(parents=True, exist_ok=False)
    if roots["output"].exists():
        raise authority.FormalActivationRejected("formal output root appeared")
    python = predecessor._python_authority(context["config"])
    payloads: list[dict[str, Any]] = []
    attempts: set[predecessor.AttemptIdentity] = set()
    for block_id in block_ids:
        payload = _dispatch_one(
            context,
            block_id=block_id,
            python_executable=python,
            roots=roots,
            dynamic_authority=dynamic_authority,
            prior_attempt_identities=attempts,
        )
        payloads.append(payload)
    return predecessor._finalize(context, payloads, roots["checkpoint"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--activation-authority", type=Path)
    parser.add_argument("--bootstrap-pid", type=int)
    parser.add_argument("--bootstrap-create-time-ns", type=int)
    parser.add_argument("--startup-handshake", type=Path)
    parser.add_argument("--startup-ack", type=Path)
    parser.add_argument("--startup-ready", type=Path)
    parser.add_argument("--science-release", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--worker-request", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker_request is not None:
        if args.validate_only or any(
            value is not None
            for value in (
                args.activation_authority,
                args.bootstrap_pid,
                args.bootstrap_create_time_ns,
                args.startup_handshake,
                args.startup_ack,
                args.startup_ready,
                args.science_release,
            )
        ):
            parser.error("worker mode accepts only --worker-request")
        raise SystemExit(_worker(args.worker_request))
    if args.validate_only:
        if any(
            value is not None
            for value in (
                args.activation_authority,
                args.bootstrap_pid,
                args.bootstrap_create_time_ns,
                args.startup_handshake,
                args.startup_ack,
                args.startup_ready,
                args.science_release,
            )
        ):
            parser.error("validate-only does not accept startup authority")
        print(json.dumps(validate_only(args.config), indent=2, sort_keys=True))
        return
    required = (
        args.activation_authority,
        args.bootstrap_pid,
        args.bootstrap_create_time_ns,
        args.startup_handshake,
        args.startup_ack,
        args.startup_ready,
        args.science_release,
    )
    if any(value is None for value in required):
        parser.error("formal controller requires complete startup authority")
    print(
        json.dumps(
            run(
                args.config,
                args.activation_authority,
                bootstrap_identity={
                    "pid": args.bootstrap_pid,
                    "create_time_ns": args.bootstrap_create_time_ns,
                },
                handshake_path=args.startup_handshake,
                ack_path=args.startup_ack,
                ready_path=args.startup_ready,
                release_path=args.science_release,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
