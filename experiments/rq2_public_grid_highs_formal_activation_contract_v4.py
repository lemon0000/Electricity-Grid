"""Fail-closed contract for the block-zero HiGHS formal activation successor."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping
from importlib import metadata
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_highs_formal_activation_successor_v4.json"
FORMAL_CONFIG = (
    ROOT
    / "configs/rts_gmlc_public_grid_need_dispatch_v4_highs_process_isolated_formal_v5.yaml"
)
INNER = (
    ROOT
    / "configs/rq2_public_grid_highs_formal_activation_successor_v4.SHA256SUMS.json"
)
OUTER = (
    ROOT
    / "configs/rq2_public_grid_highs_formal_activation_successor_v4.OUTER.SHA256SUMS.json"
)
CLOSURE = (
    ROOT
    / "configs/rq2_public_grid_highs_formal_activation_successor_v4.EXECUTION_CLOSURE.SHA256SUMS.json"
)
POST_RESULT_PASS = (
    ROOT
    / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_post_result_review_pass_v8.json"
)
ACTIVATION_REVIEW_PASS = (
    ROOT / "configs/rq2_public_grid_highs_formal_activation_successor_review_pass_v4.json"
)
USER_FORMAL_RUN_AUTHORITY = (
    ROOT / "configs/rq2_public_grid_highs_formal_run_authority_v4.json"
)
PREDECESSOR_REWORK = (
    ROOT / "configs/rq2_public_grid_highs_formal_activation_successor_review_rework_v1.json"
)
PREDECESSOR_ESCALATE = (
    ROOT / "configs/rq2_public_grid_highs_formal_activation_successor_review_escalate_v3.json"
)
GIB = 1024**3
PREFLIGHT_THRESHOLD_BYTES = 10 * GIB
CHILD_PRIVATE_COMMIT_STOP_BYTES = 8 * GIB
SYSTEM_COMMIT_AVAILABLE_STOP_BYTES = 2 * GIB
FROZEN_COMPUTED_LOCAL_IMPORTS = {
    "experiments/rq2_public_grid_execution_runtime_contract_v3.py": {
        "candidate_v4_module": (
            "experiments.run_rq2_public_grid_two_block_pilot_candidate_v4"
        ),
        "recovery_module": (
            "experiments.run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_v1"
        ),
        "publication_v7_module": (
            "experiments.run_rq2_public_grid_two_block_pilot_candidate_v7"
        ),
    }
}


class FormalActivationRejected(RuntimeError):
    """The successor cannot prove a required activation invariant."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise FormalActivationRejected(f"{label} must be a mapping")
    return dict(value)


def _repo_path(raw: object, label: str) -> Path:
    if (
        not isinstance(raw, str)
        or not raw
        or Path(raw).is_absolute()
        or ".." in Path(raw).parts
    ):
        raise FormalActivationRejected(f"{label} must be repository-relative")
    return ROOT / Path(raw)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise FormalActivationRejected(f"{label} is not an ordinary file")
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise FormalActivationRejected(f"{label} is unreadable") from exc
    return _mapping(value, label)


def _load_yaml(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise FormalActivationRejected(f"{label} is not an ordinary file")
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise FormalActivationRejected(f"{label} is unreadable") from exc
    return _mapping(value, label)


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_stable(path: Path) -> bytes:
    first = path.read_bytes()
    second = path.read_bytes()
    if first != second:
        raise FormalActivationRejected(f"stable readback drifted: {path}")
    return first


def persist_json_stable(path: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(value)
    raw = canonical_bytes(payload)
    _atomic_write(path, raw)
    if _read_stable(path) != raw or json.loads(raw) != payload:
        raise FormalActivationRejected(f"atomic JSON stable readback failed: {path}")
    return payload


def persist_json_exclusive_stable(
    path: Path, value: Mapping[str, Any]
) -> tuple[dict[str, Any], bool]:
    """Atomically create immutable JSON, or return the stable existing value."""
    payload = dict(value)
    raw = canonical_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    created = False
    try:
        try:
            os.link(temporary, path)
            created = True
        except FileExistsError:
            created = False
    finally:
        temporary.unlink(missing_ok=True)
    try:
        existing_raw = _read_stable(path)
        existing = _mapping(json.loads(existing_raw), f"immutable JSON {path}")
    except (OSError, json.JSONDecodeError) as exc:
        raise FormalActivationRejected(
            f"immutable JSON stable readback failed: {path}"
        ) from exc
    if created and (existing_raw != raw or existing != payload):
        raise FormalActivationRejected(f"immutable JSON create drifted: {path}")
    return existing, created


def _process_identity(value: object, label: str) -> dict[str, int]:
    identity = _mapping(value, label)
    if (
        set(identity) != {"pid", "create_time_ns"}
        or type(identity.get("pid")) is not int
        or type(identity.get("create_time_ns")) is not int
        or identity["pid"] <= 0
        or identity["create_time_ns"] <= 0
    ):
        raise FormalActivationRejected(f"{label} PID/create-time malformed")
    return identity  # type: ignore[return-value]


STARTUP_BINDING_NAMES = {
    "formal_config",
    "controller",
    "outer",
    "execution_closure",
    "activation_review_pass",
    "user_formal_run_authority",
    "dynamic_authority",
    "preflight",
    "activation_receipt",
    "consumed_authority",
}


def _validate_startup_bindings(
    value: object, *, expected: Mapping[str, Mapping[str, str]]
) -> dict[str, dict[str, str]]:
    bindings = _mapping(value, "startup bindings")
    expected_value = {name: dict(binding) for name, binding in expected.items()}
    if set(bindings) != STARTUP_BINDING_NAMES or bindings != expected_value:
        raise FormalActivationRejected("startup binding mapping drifted")
    for name, raw in bindings.items():
        binding = _mapping(raw, f"startup binding {name}")
        if set(binding) != {"path", "sha256"}:
            raise FormalActivationRejected(f"startup binding malformed: {name}")
        path = Path(str(binding["path"]))
        if not path.is_absolute():
            path = ROOT / path
        verify_file_binding(path, binding["sha256"], label=f"startup {name}")
    return {name: dict(binding) for name, binding in expected_value.items()}


def build_startup_handshake(
    *,
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
    bindings: Mapping[str, Mapping[str, str]],
    command: list[str],
    cwd: str,
    environment: Mapping[str, str],
) -> dict[str, Any]:
    controller_pair = _process_identity(controller_identity, "controller identity")
    bootstrap_pair = _process_identity(bootstrap_identity, "bootstrap identity")
    checked_bindings = _validate_startup_bindings(bindings, expected=bindings)
    environment_value = {str(key): str(value) for key, value in environment.items()}
    return {
        "schema": "rq2_public_grid_highs_formal_controller_startup_handshake_v4",
        "version": 4,
        "wall_time_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
        "controller_identity": controller_pair,
        "bootstrap_identity": bootstrap_pair,
        "bindings": checked_bindings,
        "command": list(command),
        "cwd": cwd,
        "environment": environment_value,
        "environment_sha256": canonical_sha256(environment_value),
        "authority_checks": {
            "dynamic_authority_validated": True,
            "consumed_tombstone_validated": True,
            "exact_cwd_environment_python_validated": True,
            "authority_mapping_validated": True,
            "execution_closure_expected_hashes_validated": True,
            "independent_review_gate_validated": True,
            "user_formal_run_authority_gate_validated": True,
            "formal_roots_absent": True,
        },
        "science_hook_calls": 0,
        "solver_calls": 0,
        "formal_root_writes": 0,
        "formal_started": False,
        "mathematical_infeasibility_inferred": False,
        "claim": False,
        "security_certified": False,
    }


def validate_startup_handshake(
    value: object,
    *,
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
    bindings: Mapping[str, Mapping[str, str]],
    command: list[str],
    cwd: str,
    environment: Mapping[str, str],
) -> dict[str, Any]:
    handshake = _mapping(value, "startup handshake")
    controller_pair = _process_identity(controller_identity, "controller identity")
    bootstrap_pair = _process_identity(bootstrap_identity, "bootstrap identity")
    environment_value = {str(key): str(value) for key, value in environment.items()}
    expected_keys = {
        "schema",
        "version",
        "wall_time_ns",
        "monotonic_ns",
        "controller_identity",
        "bootstrap_identity",
        "bindings",
        "command",
        "cwd",
        "environment",
        "environment_sha256",
        "authority_checks",
        "science_hook_calls",
        "solver_calls",
        "formal_root_writes",
        "formal_started",
        "mathematical_infeasibility_inferred",
        "claim",
        "security_certified",
    }
    if (
        set(handshake) != expected_keys
        or handshake.get("schema")
        != "rq2_public_grid_highs_formal_controller_startup_handshake_v4"
        or handshake.get("version") != 4
        or type(handshake.get("wall_time_ns")) is not int
        or type(handshake.get("monotonic_ns")) is not int
        or handshake.get("controller_identity") != controller_pair
        or handshake.get("bootstrap_identity") != bootstrap_pair
        or handshake.get("command") != command
        or handshake.get("cwd") != cwd
        or handshake.get("environment") != environment_value
        or handshake.get("environment_sha256")
        != canonical_sha256(environment_value)
        or handshake.get("authority_checks")
        != {
            "dynamic_authority_validated": True,
            "consumed_tombstone_validated": True,
            "exact_cwd_environment_python_validated": True,
            "authority_mapping_validated": True,
            "execution_closure_expected_hashes_validated": True,
            "independent_review_gate_validated": True,
            "user_formal_run_authority_gate_validated": True,
            "formal_roots_absent": True,
        }
        or handshake.get("science_hook_calls") != 0
        or handshake.get("solver_calls") != 0
        or handshake.get("formal_root_writes") != 0
        or handshake.get("formal_started") is not False
        or handshake.get("mathematical_infeasibility_inferred") is not False
        or handshake.get("claim") is not False
        or handshake.get("security_certified") is not False
    ):
        raise FormalActivationRejected("startup handshake authority drifted")
    _validate_startup_bindings(handshake.get("bindings"), expected=bindings)
    return handshake


def build_startup_ack(
    *,
    handshake: Mapping[str, Any],
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
) -> dict[str, Any]:
    return {
        "schema": "rq2_public_grid_highs_formal_bootstrap_startup_ack_v4",
        "version": 4,
        "wall_time_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
        "handshake_sha256": canonical_sha256(handshake),
        "controller_identity": _process_identity(
            controller_identity, "controller identity"
        ),
        "bootstrap_identity": _process_identity(
            bootstrap_identity, "bootstrap identity"
        ),
        "startup_authority_accepted": True,
        "formal_started": False,
        "claim": False,
        "security_certified": False,
    }


def validate_startup_ack(
    value: object,
    *,
    handshake: Mapping[str, Any],
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
) -> dict[str, Any]:
    ack = _mapping(value, "startup ack")
    if (
        set(ack)
        != {
            "schema",
            "version",
            "wall_time_ns",
            "monotonic_ns",
            "handshake_sha256",
            "controller_identity",
            "bootstrap_identity",
            "startup_authority_accepted",
            "formal_started",
            "claim",
            "security_certified",
        }
        or ack.get("schema")
        != "rq2_public_grid_highs_formal_bootstrap_startup_ack_v4"
        or ack.get("version") != 4
        or type(ack.get("wall_time_ns")) is not int
        or type(ack.get("monotonic_ns")) is not int
        or ack.get("handshake_sha256") != canonical_sha256(handshake)
        or ack.get("controller_identity")
        != _process_identity(controller_identity, "controller identity")
        or ack.get("bootstrap_identity")
        != _process_identity(bootstrap_identity, "bootstrap identity")
        or ack.get("startup_authority_accepted") is not True
        or ack.get("formal_started") is not False
        or ack.get("claim") is not False
        or ack.get("security_certified") is not False
    ):
        raise FormalActivationRejected("startup ack authority drifted")
    return ack


def build_startup_ready(
    *,
    handshake: Mapping[str, Any],
    ack: Mapping[str, Any],
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
    authority_mapping_sha256: str,
    execution_closure_sha256: str,
) -> dict[str, Any]:
    if not _is_sha256(authority_mapping_sha256) or not _is_sha256(
        execution_closure_sha256
    ):
        raise FormalActivationRejected("startup READY hash malformed")
    return {
        "schema": "rq2_public_grid_highs_formal_controller_startup_ready_v4",
        "version": 4,
        "wall_time_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
        "handshake_sha256": canonical_sha256(handshake),
        "ack_sha256": canonical_sha256(ack),
        "controller_identity": _process_identity(
            controller_identity, "controller identity"
        ),
        "bootstrap_identity": _process_identity(
            bootstrap_identity, "bootstrap identity"
        ),
        "authority_mapping_sha256": authority_mapping_sha256,
        "execution_closure_sha256": execution_closure_sha256,
        "formal_roots_absent": True,
        "science_hook_calls": 0,
        "solver_calls": 0,
        "formal_root_writes": 0,
        "formal_started": False,
        "claim": False,
        "security_certified": False,
    }


def validate_startup_ready(
    value: object,
    *,
    handshake: Mapping[str, Any],
    ack: Mapping[str, Any],
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
    authority_mapping_sha256: str,
    execution_closure_sha256: str,
) -> dict[str, Any]:
    ready = _mapping(value, "startup ready")
    expected = build_startup_ready(
        handshake=handshake,
        ack=ack,
        controller_identity=controller_identity,
        bootstrap_identity=bootstrap_identity,
        authority_mapping_sha256=authority_mapping_sha256,
        execution_closure_sha256=execution_closure_sha256,
    )
    for volatile in ("wall_time_ns", "monotonic_ns"):
        expected[volatile] = ready.get(volatile)
    if ready != expected or any(
        type(ready.get(name)) is not int or int(ready[name]) <= 0
        for name in ("wall_time_ns", "monotonic_ns")
    ):
        raise FormalActivationRejected("startup ready authority drifted")
    return ready


def build_science_release(
    *,
    ready: Mapping[str, Any],
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
) -> dict[str, Any]:
    return {
        "schema": "rq2_public_grid_highs_formal_bootstrap_science_release_v4",
        "version": 4,
        "wall_time_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
        "ready_sha256": canonical_sha256(ready),
        "controller_identity": _process_identity(
            controller_identity, "controller identity"
        ),
        "bootstrap_identity": _process_identity(
            bootstrap_identity, "bootstrap identity"
        ),
        "science_start_authorized": True,
        "retry_allowed": False,
        "resume_allowed": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }


def validate_science_release(
    value: object,
    *,
    ready: Mapping[str, Any],
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
) -> dict[str, Any]:
    release = _mapping(value, "science release")
    expected = build_science_release(
        ready=ready,
        controller_identity=controller_identity,
        bootstrap_identity=bootstrap_identity,
    )
    for volatile in ("wall_time_ns", "monotonic_ns"):
        expected[volatile] = release.get(volatile)
    if release != expected or any(
        type(release.get(name)) is not int or int(release[name]) <= 0
        for name in ("wall_time_ns", "monotonic_ns")
    ):
        raise FormalActivationRejected("science release authority drifted")
    return release


def build_science_release_acceptance(
    *,
    release: Mapping[str, Any],
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
    execution_closure_sha256: str,
) -> dict[str, Any]:
    if not _is_sha256(execution_closure_sha256):
        raise FormalActivationRejected("release acceptance closure hash malformed")
    return {
        "schema": "rq2_public_grid_highs_formal_controller_science_release_accepted_v4",
        "version": 4,
        "wall_time_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
        "release_sha256": canonical_sha256(release),
        "controller_identity": _process_identity(
            controller_identity, "controller identity"
        ),
        "bootstrap_identity": _process_identity(
            bootstrap_identity, "bootstrap identity"
        ),
        "execution_closure_sha256": execution_closure_sha256,
        "release_accepted": True,
        "formal_roots_absent_at_acceptance": True,
        "formal_started_at_acceptance": False,
        "claim": False,
        "security_certified": False,
    }


def validate_science_release_acceptance(
    value: object,
    *,
    release: Mapping[str, Any],
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
    execution_closure_sha256: str,
) -> dict[str, Any]:
    accepted = _mapping(value, "science release acceptance")
    expected = build_science_release_acceptance(
        release=release,
        controller_identity=controller_identity,
        bootstrap_identity=bootstrap_identity,
        execution_closure_sha256=execution_closure_sha256,
    )
    for volatile in ("wall_time_ns", "monotonic_ns"):
        expected[volatile] = accepted.get(volatile)
    if accepted != expected or any(
        type(accepted.get(name)) is not int or int(accepted[name]) <= 0
        for name in ("wall_time_ns", "monotonic_ns")
    ):
        raise FormalActivationRejected("science release acceptance drifted")
    return accepted


def verify_file_binding(path: Path, expected: object, *, label: str) -> str:
    if not _is_sha256(expected):
        raise FormalActivationRejected(f"{label} expected hash is malformed")
    if not path.is_file() or path.is_symlink() or sha256_file(path) != expected:
        raise FormalActivationRejected(f"{label} drifted")
    return str(expected)


def load_config() -> dict[str, Any]:
    config = _load_json(CONFIG, "formal activation config")
    if (
        config.get("schema")
        != "rq2_public_grid_highs_formal_activation_successor_v4"
        or config.get("version") != 4
        or config.get("status")
        != "READY_FOR_INDEPENDENT_FORMAL_ACTIVATION_REVIEW"
        or config.get("gates", {}).get(
            "formal_activation_successor_implementation_complete"
        )
        is not True
    ):
        raise FormalActivationRejected("formal activation config identity drifted")
    return config


def _verify_sealed_bundle() -> None:
    inner = _load_json(INNER, "formal activation inner manifest")
    outer = _load_json(OUTER, "formal activation outer manifest")
    members = _mapping(inner.get("members"), "formal activation members")
    if (
        inner.get("schema")
        != "rq2_public_grid_highs_formal_activation_successor_v4_inner"
        or inner.get("version") != 4
        or outer
        != {
            "schema": (
                "rq2_public_grid_highs_formal_activation_successor_v4_outer"
            ),
            "version": 4,
            "inner": {
                "path": INNER.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(INNER),
            },
        }
    ):
        raise FormalActivationRejected("formal activation bundle drifted")
    for raw, expected in members.items():
        verify_file_binding(_repo_path(raw, raw), expected, label=raw)


def _verify_fresh_one_shot_authority() -> None:
    config = load_config()
    lease = _mapping(config["one_shot_authority"], "one-shot authority")
    fresh = _repo_path(lease["fresh_path"], "fresh one-shot authority")
    consumed = _repo_path(lease["consumed_path"], "consumed authority")
    verify_file_binding(fresh, lease["fresh_sha256"], label="fresh authority")
    value = _load_json(fresh, "fresh one-shot authority")
    if (
        consumed.exists()
        or value.get("schema")
        != "rq2_public_grid_highs_formal_activation_successor_v4_one_shot_authority"
        or value.get("version") != 4
        or value.get("authority_id") != lease["authority_id"]
        or value.get("state") != "fresh"
        or value.get("one_shot") is not True
        or value.get("formal_execution_authorized") is not False
        or value.get("security_certified") is not False
    ):
        raise FormalActivationRejected("fresh one-shot authority drifted")


def formal_roots() -> dict[str, Path]:
    paths = _mapping(load_config()["paths"], "formal paths")
    return {
        name: _repo_path(paths[key], key)
        for name, key in (
            ("checkpoint", "checkpoint_root"),
            ("worker", "worker_root"),
            ("log", "log_root"),
            ("output", "output_root"),
        )
    }


def activation_audit_root() -> Path:
    return _repo_path(load_config()["paths"]["activation_audit_root"], "audit root")


def observe_path(path: Path) -> dict[str, Any]:
    exists = path.exists()
    ordinary_files = 0
    if exists and path.is_dir() and not path.is_symlink():
        ordinary_files = sum(
            1 for item in path.rglob("*") if item.is_file() and not item.is_symlink()
        )
    return {
        "path": str(path),
        "exists": exists,
        "is_directory": exists and path.is_dir(),
        "is_symlink": path.is_symlink(),
        "ordinary_file_count": ordinary_files,
    }


def persist_post_release_unresolved(
    attempt_root: Path,
    *,
    reason: str,
    reporter: str,
    controller_identity: Mapping[str, int] | None,
    returncode: int | None,
    termination: Mapping[str, Any],
    release_path: Path,
    release_acceptance: Mapping[str, Any] | None,
    formal_roots_override: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    """Persist first-observer evidence after release; never overwrite a peer."""
    if not release_path.is_file() or release_path.is_symlink():
        raise FormalActivationRejected(
            "post-release unresolved requires persisted science release"
        )
    roots = dict(formal_roots_override or formal_roots())
    root_observations = {
        name: observe_path(path) for name, path in sorted(roots.items())
    }
    release_sha256 = sha256_file(release_path)
    outcome = {
        "schema": "rq2_public_grid_highs_formal_post_release_unresolved_v4",
        "version": 4,
        "wall_time_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
        "phase": "post_science_release_acceptance_lifecycle",
        "reason": reason,
        "reporter": reporter,
        "guarantee_scope": (
            "at_least_one_supervising_process_remains_alive_and_can_write_attempt_root"
        ),
        "release_persisted": True,
        "release_path": str(release_path),
        "release_sha256": release_sha256,
        "release_acceptance_proven": release_acceptance is not None,
        "release_acceptance": (
            dict(release_acceptance) if release_acceptance is not None else None
        ),
        "controller_identity": (
            dict(controller_identity) if controller_identity is not None else None
        ),
        "controller_returncode": returncode,
        "termination": dict(termination),
        "formal_root_observations": root_observations,
        "checkpoint_observation": root_observations.get("checkpoint"),
        "worker_observation": root_observations.get("worker"),
        "log_observation": root_observations.get("log"),
        "output_observation": root_observations.get("output"),
        "formal_controller_spawned": controller_identity is not None,
        "formal_started": None,
        "formal_start_status": "unresolved_after_science_release_acceptance",
        "one_shot_authority_remains_consumed": True,
        "retry_allowed": False,
        "resume_allowed": False,
        "formal_result_exists": False,
        "mathematical_infeasibility_inferred": False,
        "claim": False,
        "security_certified": False,
    }
    settings = _mapping(load_config()["startup_handshake"], "startup handshake")
    path = attempt_root / str(settings["post_release_unresolved_filename"])
    persisted, _ = persist_json_exclusive_stable(path, outcome)
    if (
        persisted.get("schema") != outcome["schema"]
        or persisted.get("release_path") != str(release_path)
        or persisted.get("release_sha256") != release_sha256
        or persisted.get("phase") != outcome["phase"]
        or persisted.get("formal_started") is not None
        or persisted.get("mathematical_infeasibility_inferred") is not False
    ):
        raise FormalActivationRejected("post-release unresolved identity drifted")
    prior_identity = persisted.get("controller_identity")
    if (
        controller_identity is not None
        and prior_identity is not None
        and prior_identity != dict(controller_identity)
    ):
        raise FormalActivationRejected("post-release controller identity drifted")
    return persisted


def persist_controller_terminal_success(
    attempt_root: Path,
    *,
    controller_identity: Mapping[str, int],
    release_path: Path,
    release_acceptance: Mapping[str, Any],
    result: Mapping[str, Any],
    formal_roots_override: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    """Persist the controller's only normal terminal marker before exit zero."""
    unresolved = attempt_root / str(
        load_config()["startup_handshake"]["post_release_unresolved_filename"]
    )
    if unresolved.exists():
        raise FormalActivationRejected("unresolved evidence precludes terminal success")
    roots = dict(formal_roots_override or formal_roots())
    payload = {
        "schema": "rq2_public_grid_highs_formal_controller_terminal_success_v4",
        "version": 4,
        "wall_time_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
        "controller_identity": _process_identity(
            controller_identity, "controller terminal identity"
        ),
        "release_path": str(release_path),
        "release_sha256": sha256_file(release_path),
        "release_acceptance_sha256": canonical_sha256(release_acceptance),
        "result_sha256": canonical_sha256(result),
        "formal_root_observations": {
            name: observe_path(path) for name, path in sorted(roots.items())
        },
        "controller_terminal_status": "completed_without_controller_exception",
        "mathematical_infeasibility_inferred": False,
        "claim": False,
        "security_certified": False,
    }
    settings = _mapping(load_config()["startup_handshake"], "startup handshake")
    path = attempt_root / str(settings["controller_terminal_success_filename"])
    persisted, created = persist_json_exclusive_stable(path, payload)
    if not created or persisted != payload:
        raise FormalActivationRejected("controller terminal success already existed")
    return persisted


def _verify_checkpoint_inventory(value: Mapping[str, Any]) -> None:
    directory = _repo_path(value.get("directory"), "protected checkpoint directory")
    files = _mapping(value.get("files"), "protected checkpoint files")
    observed = {
        path.name: sha256_file(path)
        for path in sorted(directory.iterdir())
        if path.is_file() and not path.is_symlink()
    }
    if observed != files or value.get("count") != len(files):
        raise FormalActivationRejected("protected checkpoint inventory drifted")
    rows = [f"{name}:{files[name]}" for name in sorted(files)]
    aggregate = hashlib.sha256("\n".join(rows).encode()).hexdigest()
    if aggregate != value.get("inventory_sha256"):
        raise FormalActivationRejected("protected checkpoint aggregate drifted")


def _source_package(relative: Path) -> tuple[str, ...]:
    if relative.name == "__init__.py":
        return relative.parent.parts
    return relative.with_suffix("").parent.parts


def _module_candidates(parts: tuple[str, ...]) -> set[Path]:
    """Return every ordinary local module/package file Python may import."""
    candidates: set[Path] = set()
    if not parts:
        return candidates
    for index in range(1, len(parts) + 1):
        package_init = Path(*parts[:index]) / "__init__.py"
        if (ROOT / package_init).is_file():
            candidates.add(package_init)
    module = Path(*parts).with_suffix(".py")
    package = Path(*parts) / "__init__.py"
    for candidate in (module, package):
        if (ROOT / candidate).is_file():
            candidates.add(candidate)
    return candidates


def _local_import_candidates(tree: ast.AST, *, source: Path) -> set[Path]:
    """Resolve static imports using Python's package/relative-import semantics."""
    candidates: set[Path] = set()
    package = _source_package(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                candidates.update(_module_candidates(tuple(alias.name.split("."))))
            continue
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level:
            if node.level > len(package):
                raise FormalActivationRejected(
                    f"relative import escapes local package: {source}"
                )
            prefix = package[: len(package) - node.level + 1]
        else:
            prefix = ()
        module = tuple(node.module.split(".")) if node.module else ()
        base = prefix + module
        candidates.update(_module_candidates(base))
        for alias in node.names:
            if alias.name != "*":
                # Imported names can be attributes or local submodules.  Only an
                # existing local module is included, so namespace packages and
                # ``from . import x`` are handled without inventing files.
                candidates.update(_module_candidates(base + (alias.name,)))
    expected_computed = dict(
        FROZEN_COMPUTED_LOCAL_IMPORTS.get(source.as_posix(), {})
    )
    observed_computed: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        is_dynamic = (
            isinstance(node.func, ast.Name) and node.func.id == "__import__"
        ) or (
            isinstance(node.func, ast.Attribute) and node.func.attr == "import_module"
        )
        if not is_dynamic:
            continue
        target = node.args[0]
        if isinstance(target, ast.Constant) and isinstance(target.value, str):
            candidates.update(_module_candidates(tuple(target.value.split("."))))
            continue
        if (
            isinstance(target, ast.Subscript)
            and isinstance(target.value, ast.Name)
            and target.value.id == "authority"
            and isinstance(target.slice, ast.Constant)
            and isinstance(target.slice.value, str)
            and target.slice.value in expected_computed
        ):
            key = target.slice.value
            observed_computed.add(key)
            candidates.update(
                _module_candidates(tuple(expected_computed[key].split(".")))
            )
            continue
        raise FormalActivationRejected(
            f"unfrozen computed dynamic import in execution closure: {source}:{node.lineno}"
        )
    if observed_computed != set(expected_computed):
        raise FormalActivationRejected(
            f"frozen computed dynamic import inventory drifted: {source}"
        )
    return candidates


def discover_execution_import_closure() -> set[str]:
    pending = [
        Path("experiments/bootstrap_rq2_public_grid_highs_formal_activation_successor_v4.py"),
        Path("experiments/rq2_public_grid_highs_formal_activation_contract_v4.py"),
        Path("experiments/run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_formal_v5.py"),
    ]
    observed: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in observed:
            continue
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise FormalActivationRejected(f"execution closure member missing: {relative}")
        observed.add(relative)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except (OSError, SyntaxError, UnicodeError) as exc:
            raise FormalActivationRejected(
                f"execution closure member cannot be parsed: {relative}"
            ) from exc
        pending.extend(_local_import_candidates(tree, source=relative) - observed)
    return {path.as_posix() for path in observed}


def verify_execution_closure() -> dict[str, Any]:
    config = load_config()
    binding = _mapping(config["execution_closure"], "execution closure")
    manifest_path = _repo_path(binding["manifest_path"], "execution closure manifest")
    verify_file_binding(
        manifest_path, binding["manifest_sha256"], label="execution closure manifest"
    )
    manifest = _load_json(manifest_path, "execution closure manifest")
    members = _mapping(manifest.get("members"), "execution closure members")
    if (
        manifest.get("schema")
        != "rq2_public_grid_highs_formal_activation_successor_v4_execution_closure"
        or manifest.get("version") != 4
        or manifest.get("derivation")
        != "python_relative_semantics_static_local_import_closure_v4"
        or set(members) != discover_execution_import_closure()
    ):
        raise FormalActivationRejected("execution import closure inventory drifted")
    for raw, expected in members.items():
        verify_file_binding(_repo_path(raw, raw), expected, label=f"closure {raw}")
    digest = canonical_sha256(dict(sorted(members.items())))
    if manifest.get("members_sha256") != digest or manifest.get("member_count") != len(
        members
    ):
        raise FormalActivationRejected("execution import closure digest drifted")
    return {
        "manifest_path": manifest_path.relative_to(ROOT).as_posix(),
        "manifest_sha256": sha256_file(manifest_path),
        "member_count": len(members),
        "members_sha256": digest,
        "expected_hashes_verified": True,
    }


def _verify_reviewed_v8_receipt() -> dict[str, Any]:
    receipt = _load_json(POST_RESULT_PASS, "V8 post-result PASS receipt")
    if (
        receipt.get("schema")
        != "rq2_public_grid_two_block_pilot_vnext_execution_successor_post_result_review_pass_v8"
        or receipt.get("reviewed_on") != "2026-09-01"
        or receipt.get("reviewer_agent") != "/root/pilot_post_result_review"
        or receipt.get("reviewer_role") != "independent_sol_reviewer"
        or receipt.get("verdict") != "PASS"
        or receipt.get("findings") != []
        or receipt.get("materialized_from_review_report") is not True
        or receipt.get("cryptographic_reviewer_signature_present") is not False
    ):
        raise FormalActivationRejected("V8 post-result PASS receipt drifted")
    bindings = [receipt["reviewed_v8_outer"], receipt["pre_run_review_pass"]]
    reviewed = _mapping(receipt["reviewed_result"], "reviewed result")
    bindings.extend(
        reviewed[name]
        for name in (
            "result_manifest",
            "result_tree",
            "published_tree",
            "published_success",
            "controller_receipt",
            "controller_attestation",
            "secret_free_tombstone",
        )
    )
    protected = _mapping(receipt["protected_formal_artifacts"], "protected formal")
    bindings.extend(
        protected[name]
        for name in (
            "base_science_runner",
            "process_isolated_predecessor_runner",
            "original_highs_candidate_config",
            "existing_activated_gurobi_config",
        )
    )
    for binding in bindings:
        item = _mapping(binding, "review binding")
        verify_file_binding(
            _repo_path(item.get("path"), "review binding path"),
            item.get("sha256"),
            label=str(item.get("path")),
        )
    tombstone = _mapping(reviewed["secret_free_tombstone"], "V8 tombstone")
    tombstone_value = _load_json(
        _repo_path(tombstone["path"], "V8 tombstone path"), "V8 tombstone"
    )
    if (
        tombstone.get("seed_present") is not False
        or tombstone.get("one_time_key_reusable") is not False
        or tombstone_value.get("seed_present") is not False
        or tombstone_value.get("one_time_key_reusable") is not False
    ):
        raise FormalActivationRejected("V8 tombstone is not secret-free/nonreusable")
    result_manifest = _load_json(
        _repo_path(reviewed["result_manifest"]["path"], "result manifest path"),
        "V8 result manifest",
    )
    attestation = _load_json(
        _repo_path(
            reviewed["controller_attestation"]["path"], "attestation path"
        ),
        "V8 controller attestation",
    )
    if (
        result_manifest.get("nonformal") is not True
        or result_manifest.get("claim") is not False
        or result_manifest.get("security_certified") is not False
        or result_manifest.get("controller_attestation_payload_sha256")
        != reviewed.get("lamport_attestation_payload_sha256")
        or result_manifest.get("controller_signature_sha256")
        != reviewed.get("lamport_signature_sha256")
        or attestation.get("payload_sha256")
        != reviewed.get("lamport_attestation_payload_sha256")
        or attestation.get("signature_sha256")
        != reviewed.get("lamport_signature_sha256")
    ):
        raise FormalActivationRejected("V8 Lamport/result binding drifted")
    _verify_checkpoint_inventory(protected["existing_gurobi_checkpoint_inventory"])
    effect = _mapping(receipt["effect"], "post-result effect")
    expected_effect = {
        "v8_post_result_independent_review_passed": True,
        "opens_formal_activation_successor_review_only": True,
        "formal_execution_authorized": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    if effect != expected_effect:
        raise FormalActivationRejected("V8 post-result review effect drifted")
    return receipt


def _verify_predecessor_rework(config: Mapping[str, Any]) -> dict[str, Any]:
    binding = _mapping(config["predecessor_rework"], "predecessor REWORK")
    receipt = _load_json(PREDECESSOR_REWORK, "predecessor REWORK receipt")
    v1_outer = _repo_path(binding["v1_outer_path"], "v1 outer")
    if (
        binding
        != {
            "v1_outer_path": (
                "configs/rq2_public_grid_highs_formal_activation_"
                "successor_v1.OUTER.SHA256SUMS.json"
            ),
            "v1_outer_sha256": (
                "b492e4babe182d38ad6be865df424d1cce59cef57c2c6a85b896cffddfad0b87"
            ),
            "receipt_path": PREDECESSOR_REWORK.relative_to(ROOT).as_posix(),
            "receipt_sha256": sha256_file(PREDECESSOR_REWORK),
            "verdict": "REWORK",
        }
        or sha256_file(v1_outer) != binding["v1_outer_sha256"]
        or receipt.get("verdict") != "REWORK"
        or receipt.get("reviewer_agent") != "/root/pilot_post_result_review"
        or receipt.get("reviewer_role") != "independent_sol_reviewer"
        or receipt.get("reviewed_on") != "2026-09-01"
        or receipt.get("cryptographic_reviewer_signature_present") is not False
        or receipt.get("v2_rework_authority", {}).get("authorized_by_reviewer_pass")
        is not False
        or receipt.get("effect", {}).get("formal_execution_authorized") is not False
    ):
        raise FormalActivationRejected("predecessor REWORK authority drifted")
    return receipt


def _verify_predecessor_escalate(config: Mapping[str, Any]) -> dict[str, Any]:
    binding = _mapping(config["predecessor_escalate"], "predecessor ESCALATE")
    receipt = _load_json(PREDECESSOR_ESCALATE, "predecessor ESCALATE receipt")
    v3_outer = _repo_path(binding["v3_outer_path"], "v3 outer")
    if (
        binding.get("v3_outer_sha256")
        != "087127892db1a55955ddc87b2491520a61a9b19d6d7f0e56040ce0c9d980ee3b"
        or sha256_file(v3_outer) != binding.get("v3_outer_sha256")
        or binding.get("receipt_path")
        != PREDECESSOR_ESCALATE.relative_to(ROOT).as_posix()
        or binding.get("receipt_sha256") != sha256_file(PREDECESSOR_ESCALATE)
        or binding.get("verdict") != "ESCALATE"
        or receipt.get("verdict") != "ESCALATE"
        or receipt.get("materialized_from_independent_review_report") is not True
        or receipt.get("cryptographic_reviewer_signature_present") is not False
        or receipt.get("reviewed_outer", {}).get("sha256")
        != binding.get("v3_outer_sha256")
        or receipt.get("formal_execution_authorized") is not False
        or len(receipt.get("critical_findings", [])) != 2
    ):
        raise FormalActivationRejected("predecessor ESCALATE authority drifted")
    return receipt


def _verify_formal_science_config(config: Mapping[str, Any]) -> dict[str, Any]:
    science = _mapping(config["formal_science"], "formal science")
    verify_file_binding(
        FORMAL_CONFIG, science["formal_config_sha256"], label="formal science config"
    )
    formal = _load_yaml(FORMAL_CONFIG, "formal science config")
    predecessor = _load_yaml(
        _repo_path(
            science["original_highs_candidate_config_path"], "original candidate"
        ),
        "original HiGHS candidate",
    )
    expected_solver = dict(_mapping(formal["solver"], "formal solver"))
    expected_solver["expected_runtime_api_version"] = "1.15.1"
    for key in ("input", "grid_source", "model", "solver", "provenance"):
        if formal.get(key) != predecessor.get(key):
            raise FormalActivationRejected(f"formal science section drifted: {key}")
    execution = _mapping(formal["execution"], "formal execution")
    process = _mapping(execution["process_isolation"], "formal process isolation")
    if (
        formal.get("schema")
        != "rts_gmlc_public_grid_need_dispatch_v4_highs_process_isolated_formal_v5"
        or execution.get("formal_execution_ready") is not False
        or execution.get("independent_R4_review_passed") is not False
        or execution.get("user_formal_run_authorized") is not False
        or execution.get("runtime_gate_state_source")
        != "external_fixed_path_review_and_user_authority_receipts"
        or execution.get("starts_from_block_zero") is not True
        or execution.get("resume_allowed") is not False
        or execution.get("predecessor_Gurobi_checkpoint_reuse_allowed") is not False
        or execution.get("predecessor_HiGHS_checkpoint_reuse_allowed") is not False
        or process.get("expected_block_count") != 1071
        or process.get("starts_from_block_zero") is not True
        or process.get("resume_allowed") is not False
        or process.get("resource_sample_interval_seconds") != 5.0
        or process.get("observation_jitter_budget_seconds") != 1.0
        or process.get("maximum_detection_overrun_seconds") != 1.0
        or process.get("owned_termination_grace_seconds") != 2.0
        or process.get("private_commit_limit_gib") != 8.0
        or process.get("minimum_system_commit_available_gib") != 2.0
        or process.get("external_watchdog_seconds") != 21600
        or process.get("two_block_full_process_pilot_post_result_passed") is not True
        or process.get("timeout_or_failure_is_mathematical_infeasibility") is not False
        or science.get("solver") != expected_solver
    ):
        raise FormalActivationRejected("formal process/science gate drifted")
    return formal


def static_authority_mapping() -> dict[str, str]:
    config = load_config()
    mapping: dict[str, str] = {
        CONFIG.relative_to(ROOT).as_posix(): sha256_file(CONFIG),
        POST_RESULT_PASS.relative_to(ROOT).as_posix(): sha256_file(POST_RESULT_PASS),
        FORMAL_CONFIG.relative_to(ROOT).as_posix(): sha256_file(FORMAL_CONFIG),
        CLOSURE.relative_to(ROOT).as_posix(): sha256_file(CLOSURE),
        PREDECESSOR_REWORK.relative_to(ROOT).as_posix(): sha256_file(
            PREDECESSOR_REWORK
        ),
        PREDECESSOR_ESCALATE.relative_to(ROOT).as_posix(): sha256_file(
            PREDECESSOR_ESCALATE
        ),
    }
    if INNER.is_file() and OUTER.is_file():
        mapping[INNER.relative_to(ROOT).as_posix()] = sha256_file(INNER)
        mapping[OUTER.relative_to(ROOT).as_posix()] = sha256_file(OUTER)
    for section_name in ("v8_evidence_authority",):
        for item in _mapping(config[section_name], section_name).values():
            binding = _mapping(item, "static V8 binding")
            mapping[str(binding["path"])] = str(binding["sha256"])
    science = _mapping(config["formal_science"], "formal science")
    for path_key, hash_key in (
        ("base_science_runner_path", "base_science_runner_sha256"),
        (
            "process_isolated_predecessor_runner_path",
            "process_isolated_predecessor_runner_sha256",
        ),
        ("original_highs_candidate_config_path", "original_highs_candidate_config_sha256"),
    ):
        mapping[str(science[path_key])] = str(science[hash_key])
    predecessor = _mapping(config["protected_predecessor_state"], "predecessor")
    mapping[str(predecessor["existing_activated_gurobi_config_path"])] = str(
        predecessor["existing_activated_gurobi_config_sha256"]
    )
    return dict(sorted(mapping.items()))


def preflight_authority_mapping() -> dict[str, str]:
    config = load_config()
    lease = _mapping(config["one_shot_authority"], "one-shot authority")
    mapping = dict(static_authority_mapping())
    mapping[ACTIVATION_REVIEW_PASS.relative_to(ROOT).as_posix()] = sha256_file(
        ACTIVATION_REVIEW_PASS
    )
    mapping[USER_FORMAL_RUN_AUTHORITY.relative_to(ROOT).as_posix()] = sha256_file(
        USER_FORMAL_RUN_AUTHORITY
    )
    mapping[str(lease["fresh_path"])] = str(lease["fresh_sha256"])
    return dict(sorted(mapping.items()))


def validate_static_authority(
    *, require_activation_review: bool = False
) -> dict[str, Any]:
    config = load_config()
    _verify_sealed_bundle()
    _verify_fresh_one_shot_authority()
    _verify_predecessor_rework(config)
    _verify_predecessor_escalate(config)
    _verify_reviewed_v8_receipt()
    _verify_formal_science_config(config)
    closure = verify_execution_closure()
    for raw, expected in static_authority_mapping().items():
        verify_file_binding(_repo_path(raw, raw), expected, label=raw)
    runtime = _mapping(config["runtime"], "runtime")
    for path_key, hash_key in (
        ("locked_python_executable", "locked_python_sha256"),
        ("highspy_package_init_path", "highspy_package_init_sha256"),
        ("highspy_python_source_path", "highspy_python_source_sha256"),
        ("highspy_binary_path", "highspy_binary_sha256"),
    ):
        verify_file_binding(
            Path(runtime[path_key]), runtime[hash_key], label=path_key
        )
    if metadata.version("highspy") != "1.15.1":
        raise FormalActivationRejected("installed highspy version drifted")
    review_present = ACTIVATION_REVIEW_PASS.is_file() and not ACTIVATION_REVIEW_PASS.is_symlink()
    user_authority_present = (
        USER_FORMAL_RUN_AUTHORITY.is_file()
        and not USER_FORMAL_RUN_AUTHORITY.is_symlink()
    )
    if require_activation_review:
        require_activation_review_pass()
    return {
        "schema": "rq2_public_grid_highs_formal_activation_static_validation_v4",
        "validation_passed": True,
        "v8_post_result_independent_review_passed": True,
        "v1_review_verdict": "REWORK",
        "formal_activation_review_receipt_present": review_present,
        "user_formal_run_authority_present": user_authority_present,
        "formal_execution_authorized": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
        "solver_calls": 0,
        "formal_root_writes": 0,
        "static_authority_mapping_sha256": canonical_sha256(
            static_authority_mapping()
        ),
        "execution_closure": closure,
    }


def require_activation_review_pass() -> dict[str, Any]:
    if not ACTIVATION_REVIEW_PASS.is_file() or ACTIVATION_REVIEW_PASS.is_symlink():
        raise FormalActivationRejected(
            "independent formal activation review PASS receipt is absent"
        )
    receipt = _load_json(ACTIVATION_REVIEW_PASS, "activation review PASS receipt")
    config = load_config()
    if (
        receipt.get("schema")
        != config["independent_formal_activation_review"]["schema"]
        or receipt.get("verdict") != "PASS"
        or receipt.get("reviewed_outer", {}).get("path")
        != config["bundle"]["outer_path"]
        or receipt.get("reviewed_outer", {}).get("sha256") != sha256_file(OUTER)
        or receipt.get("effect")
        != {
            "formal_activation_successor_independent_review_passed": True,
            "formal_execution_authorized": False,
            "formal_result_exists": False,
            "claim": False,
            "security_certified": False,
        }
    ):
        raise FormalActivationRejected("activation review PASS receipt drifted")
    return receipt


def require_user_formal_run_authority() -> dict[str, Any]:
    if (
        not USER_FORMAL_RUN_AUTHORITY.is_file()
        or USER_FORMAL_RUN_AUTHORITY.is_symlink()
    ):
        raise FormalActivationRejected("explicit user formal-run authority is absent")
    review = require_activation_review_pass()
    receipt = _load_json(USER_FORMAL_RUN_AUTHORITY, "user formal-run authority")
    config = load_config()
    lease = _mapping(config["one_shot_authority"], "one-shot authority")
    review_binding = {
        "path": ACTIVATION_REVIEW_PASS.relative_to(ROOT).as_posix(),
        "sha256": sha256_file(ACTIVATION_REVIEW_PASS),
    }
    outer_binding = {
        "path": OUTER.relative_to(ROOT).as_posix(),
        "sha256": sha256_file(OUTER),
    }
    config_binding = {
        "path": FORMAL_CONFIG.relative_to(ROOT).as_posix(),
        "sha256": sha256_file(FORMAL_CONFIG),
    }
    closure_binding = {
        "path": CLOSURE.relative_to(ROOT).as_posix(),
        "sha256": sha256_file(CLOSURE),
    }
    lease_binding = {
        "fresh_path": str(lease["fresh_path"]),
        "fresh_sha256": str(lease["fresh_sha256"]),
        "consumed_path": str(lease["consumed_path"]),
        "authority_id": str(lease["authority_id"]),
        "one_shot": True,
    }
    if (
        receipt.get("schema") != config["user_formal_run_authority"]["schema"]
        or receipt.get("version") != 4
        or receipt.get("authority_source") != "explicit_user_formal_run_authorization"
        or receipt.get("materialized_from_user_instruction") is not True
        or receipt.get("cryptographic_user_signature_present") is not False
        or receipt.get("review_pass") != review_binding
        or receipt.get("reviewed_outer") != outer_binding
        or receipt.get("formal_config") != config_binding
        or receipt.get("execution_closure") != closure_binding
        or receipt.get("controller_command_prefix")
        != config["runtime"]["controller_command_prefix"]
        or receipt.get("one_shot_authority") != lease_binding
        or receipt.get("effect")
        != {
            "formal_activation_successor_independent_review_passed": True,
            "user_formal_run_authorized": True,
            "formal_execution_authorized": True,
            "formal_result_exists": False,
            "claim": False,
            "security_certified": False,
        }
        or review.get("effect", {}).get("formal_execution_authorized") is not False
    ):
        raise FormalActivationRejected("user formal-run authority drifted")
    return receipt


def capture_preflight_evidence(
    attempt_root: Path,
    *,
    authority_mapping: Mapping[str, str],
    observed_available_commit_bytes: Callable[[], int],
    wall_time_ns: Callable[[], int] = time.time_ns,
    monotonic_ns: Callable[[], int] = time.monotonic_ns,
) -> dict[str, Any]:
    if attempt_root.exists():
        raise FormalActivationRejected("activation attempt root must not preexist")
    attempt_root.mkdir(parents=True, exist_ok=False)
    observed = observed_available_commit_bytes()
    wall = wall_time_ns()
    monotonic = monotonic_ns()
    if type(observed) is not int or observed < 0 or wall <= 0 or monotonic <= 0:
        raise FormalActivationRejected("system commit preflight observation malformed")
    mapping = dict(sorted(authority_mapping.items()))
    if any(not _is_sha256(value) for value in mapping.values()):
        raise FormalActivationRejected("preflight authority mapping malformed")
    payload = {
        "schema": "rq2_public_grid_highs_formal_activation_preflight_v4",
        "version": 4,
        "wall_time_ns": wall,
        "monotonic_ns": monotonic,
        "observed_available_commit_bytes": observed,
        "preflight_threshold_bytes": PREFLIGHT_THRESHOLD_BYTES,
        "child_private_commit_stop_bytes": CHILD_PRIVATE_COMMIT_STOP_BYTES,
        "system_commit_available_stop_bytes": SYSTEM_COMMIT_AVAILABLE_STOP_BYTES,
        "authority_mapping": mapping,
        "authority_mapping_sha256": canonical_sha256(mapping),
        "comparison": (
            "observed_available_commit_bytes >= preflight_threshold_bytes"
        ),
        "threshold_passed": observed >= PREFLIGHT_THRESHOLD_BYTES,
        "formal_roots_created": False,
        "authority_consumed": False,
        "formal_controller_spawned": False,
        "mathematical_infeasibility_inferred": False,
    }
    path = attempt_root / "preflight.json"
    raw = canonical_bytes(payload)
    _atomic_write(path, raw)
    if _read_stable(path) != raw:
        raise FormalActivationRejected("preflight stable readback failed")
    return {
        **payload,
        "persisted_path": str(path),
        "persisted_sha256": hashlib.sha256(raw).hexdigest(),
        "stable_readback_verified": True,
    }


def _powershell_related_processes(module_name: str) -> list[dict[str, object]]:
    escaped = module_name.replace("'", "''")
    script = (
        "$selfPid=$PID; Get-CimInstance Win32_Process | "
        f"Where-Object {{$_.ProcessId -ne $selfPid -and ([string]$_.CommandLine).Contains('{escaped}')}} | "
        "Select-Object ProcessId,Name | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", script],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    raw = completed.stdout.strip()
    if not raw:
        return []
    value = json.loads(raw)
    return [value] if isinstance(value, dict) else list(value)


def related_formal_processes() -> list[dict[str, object]]:
    module = str(load_config()["runtime"]["formal_controller_module"])
    return _powershell_related_processes(module)


def ensure_formal_roots_absent() -> None:
    existing = [name for name, path in formal_roots().items() if path.exists()]
    if existing:
        raise FormalActivationRejected(
            "formal roots must not preexist: " + ", ".join(existing)
        )


def ensure_no_related_formal_process() -> None:
    if related_formal_processes():
        raise FormalActivationRejected("related formal process is already active")


def next_attempt_root() -> Path:
    root = activation_audit_root()
    root.mkdir(parents=True, exist_ok=True)
    for _ in range(10):
        candidate = root / f"attempt_{time.time_ns()}"
        if not candidate.exists():
            return candidate
    raise FormalActivationRejected("could not allocate activation attempt root")


def startup_paths(attempt_root: Path) -> dict[str, str]:
    names = _mapping(load_config()["startup_handshake"], "startup handshake")
    return {
        key: str((attempt_root / str(names[field])).resolve())
        for key, field in (
            ("handshake", "handshake_filename"),
            ("bootstrap_ack", "bootstrap_ack_filename"),
            ("startup_ready", "startup_ready_filename"),
            ("science_release", "science_release_filename"),
            ("science_release_accepted", "science_release_accepted_filename"),
            ("launch_incomplete", "launch_incomplete_filename"),
            ("post_release_unresolved", "post_release_unresolved_filename"),
            ("controller_terminal_success", "controller_terminal_success_filename"),
        )
    }


def exact_controller_command(
    authority_path: Path, *, bootstrap_identity: Mapping[str, int]
) -> list[str]:
    prefix = list(load_config()["runtime"]["controller_command_prefix"])
    identity = _process_identity(bootstrap_identity, "bootstrap identity")
    paths = startup_paths(authority_path.resolve().parent)
    return [
        *prefix,
        str(authority_path.resolve()),
        "--bootstrap-pid",
        str(identity["pid"]),
        "--bootstrap-create-time-ns",
        str(identity["create_time_ns"]),
        "--startup-handshake",
        paths["handshake"],
        "--startup-ack",
        paths["bootstrap_ack"],
        "--startup-ready",
        paths["startup_ready"],
        "--science-release",
        paths["science_release"],
        "--science-release-accepted",
        paths["science_release_accepted"],
    ]


def exact_controller_environment() -> dict[str, str]:
    return {
        str(key): str(value)
        for key, value in load_config()["runtime"]["sanitized_environment"].items()
    }


def publish_dynamic_authority(
    preflight: Mapping[str, Any],
    *,
    review_receipt: Mapping[str, Any],
    user_run_authority: Mapping[str, Any],
    bootstrap_identity: Mapping[str, int],
) -> dict[str, Any]:
    preflight_path = Path(str(preflight["persisted_path"])).resolve()
    attempt_root = preflight_path.parent
    if (
        preflight.get("stable_readback_verified") is not True
        or sha256_file(preflight_path) != preflight.get("persisted_sha256")
    ):
        raise FormalActivationRejected("preflight persistence binding drifted")
    bootstrap_pair = _process_identity(bootstrap_identity, "bootstrap identity")
    command = exact_controller_command(
        attempt_root / "authority.json", bootstrap_identity=bootstrap_pair
    )
    environment = exact_controller_environment()
    payload = {
        "schema": "rq2_public_grid_highs_formal_dynamic_activation_authority_v4",
        "version": 4,
        "preflight": {
            "path": str(preflight_path),
            "sha256": preflight["persisted_sha256"],
            "wall_time_ns": preflight["wall_time_ns"],
            "monotonic_ns": preflight["monotonic_ns"],
            "observed_available_commit_bytes": preflight[
                "observed_available_commit_bytes"
            ],
            "threshold_passed": preflight["threshold_passed"],
        },
        "preflight_authority_mapping": dict(preflight["authority_mapping"]),
        "preflight_authority_mapping_sha256": preflight[
            "authority_mapping_sha256"
        ],
        "activation_review_receipt": {
            "path": str(ACTIVATION_REVIEW_PASS.relative_to(ROOT).as_posix()),
            "sha256": sha256_file(ACTIVATION_REVIEW_PASS),
            "verdict": review_receipt["verdict"],
        },
        "user_formal_run_authority": {
            "path": USER_FORMAL_RUN_AUTHORITY.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(USER_FORMAL_RUN_AUTHORITY),
            "formal_execution_authorized": user_run_authority["effect"][
                "formal_execution_authorized"
            ],
        },
        "execution_closure": verify_execution_closure(),
        "bootstrap_identity": bootstrap_pair,
        "startup_paths": startup_paths(attempt_root),
        "exact_command": command,
        "exact_cwd": str(ROOT),
        "exact_environment": environment,
        "exact_environment_sha256": canonical_sha256(environment),
        "formal_roots": {
            name: str(path) for name, path in formal_roots().items()
        },
        "starts_from_block_zero": True,
        "resume_allowed": False,
        "formal_execution_authorized": True,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    authority_path = attempt_root / "authority.json"
    raw = canonical_bytes(payload)
    _atomic_write(authority_path, raw)
    if _read_stable(authority_path) != raw:
        raise FormalActivationRejected("dynamic authority stable readback failed")
    receipt_payload = {
        "schema": "rq2_public_grid_highs_formal_activation_attempt_receipt_v4",
        "version": 4,
        "preflight_path": str(preflight_path),
        "preflight_sha256": preflight["persisted_sha256"],
        "authority_path": str(authority_path),
        "authority_sha256": hashlib.sha256(raw).hexdigest(),
        "threshold_passed": preflight["threshold_passed"],
        "authority_consumed": False,
        "formal_controller_spawned": False,
        "formal_result_exists": False,
        "mathematical_infeasibility_inferred": False,
        "claim": False,
        "security_certified": False,
    }
    receipt_path = attempt_root / "activation_receipt.json"
    receipt_raw = canonical_bytes(receipt_payload)
    _atomic_write(receipt_path, receipt_raw)
    if _read_stable(receipt_path) != receipt_raw:
        raise FormalActivationRejected("activation receipt stable readback failed")
    return {
        **payload,
        "authority_path": str(authority_path),
        "authority_sha256": hashlib.sha256(raw).hexdigest(),
        "activation_receipt_path": str(receipt_path),
        "activation_receipt_sha256": hashlib.sha256(receipt_raw).hexdigest(),
    }


def validate_dynamic_authority(path: Path) -> dict[str, Any]:
    value = _load_json(path, "dynamic activation authority")
    preflight = _mapping(value["preflight"], "dynamic preflight")
    preflight_path = Path(str(preflight["path"])).resolve()
    if (
        value.get("schema")
        != "rq2_public_grid_highs_formal_dynamic_activation_authority_v4"
        or preflight.get("threshold_passed") is not True
        or sha256_file(preflight_path) != preflight.get("sha256")
        or value.get("preflight_authority_mapping")
        != preflight_authority_mapping()
        or value.get("preflight_authority_mapping_sha256")
        != canonical_sha256(preflight_authority_mapping())
        or value.get("bootstrap_identity")
        != _process_identity(value.get("bootstrap_identity"), "bootstrap identity")
        or value.get("startup_paths") != startup_paths(path.resolve().parent)
        or value.get("exact_command")
        != exact_controller_command(
            path,
            bootstrap_identity=_process_identity(
                value.get("bootstrap_identity"), "bootstrap identity"
            ),
        )
        or value.get("exact_cwd") != str(ROOT)
        or value.get("exact_environment") != exact_controller_environment()
        or value.get("exact_environment_sha256")
        != canonical_sha256(exact_controller_environment())
        or value.get("starts_from_block_zero") is not True
        or value.get("resume_allowed") is not False
        or value.get("formal_execution_authorized") is not True
        or value.get("formal_result_exists") is not False
        or value.get("claim") is not False
        or value.get("security_certified") is not False
    ):
        raise FormalActivationRejected("dynamic activation authority drifted")
    review = require_activation_review_pass()
    binding = _mapping(value["activation_review_receipt"], "review binding")
    if (
        binding.get("path") != ACTIVATION_REVIEW_PASS.relative_to(ROOT).as_posix()
        or binding.get("sha256") != sha256_file(ACTIVATION_REVIEW_PASS)
        or binding.get("verdict") != review.get("verdict")
    ):
        raise FormalActivationRejected("dynamic review receipt binding drifted")
    user_authority = require_user_formal_run_authority()
    user_binding = _mapping(
        value["user_formal_run_authority"], "user formal-run authority binding"
    )
    if user_binding != {
        "path": USER_FORMAL_RUN_AUTHORITY.relative_to(ROOT).as_posix(),
        "sha256": sha256_file(USER_FORMAL_RUN_AUTHORITY),
        "formal_execution_authorized": user_authority["effect"][
            "formal_execution_authorized"
        ],
    }:
        raise FormalActivationRejected("dynamic user formal-run authority drifted")
    if value.get("execution_closure") != verify_execution_closure():
        raise FormalActivationRejected("dynamic execution closure drifted")
    return value


def consume_one_shot_authority(dynamic: Mapping[str, Any]) -> dict[str, Any]:
    config = load_config()
    lease = _mapping(config["one_shot_authority"], "one-shot authority")
    fresh = _repo_path(lease["fresh_path"], "fresh authority")
    consumed = _repo_path(lease["consumed_path"], "consumed authority")
    if (
        not fresh.is_file()
        or fresh.is_symlink()
        or consumed.exists()
        or sha256_file(fresh) != lease["fresh_sha256"]
    ):
        raise FormalActivationRejected("fresh one-shot authority is unavailable")
    value = _load_json(fresh, "fresh one-shot authority")
    if (
        value.get("authority_id") != lease["authority_id"]
        or value.get("state") != "fresh"
        or value.get("one_shot") is not True
    ):
        raise FormalActivationRejected("fresh one-shot authority drifted")
    authority_path = Path(str(dynamic["authority_path"])).resolve()
    if sha256_file(authority_path) != dynamic["authority_sha256"]:
        raise FormalActivationRejected("dynamic authority changed before consume")
    os.replace(fresh, consumed)
    tombstone = {
        "schema": "rq2_public_grid_highs_formal_activation_successor_v4_consumed_authority",
        "version": 4,
        "authority_id": lease["authority_id"],
        "state": "consumed",
        "one_shot_reusable": False,
        "dynamic_authority_path": str(authority_path),
        "dynamic_authority_sha256": dynamic["authority_sha256"],
        "activation_receipt_path": dynamic["activation_receipt_path"],
        "activation_receipt_sha256": dynamic["activation_receipt_sha256"],
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    raw = canonical_bytes(tombstone)
    try:
        _atomic_write(consumed, raw)
        if fresh.exists() or _read_stable(consumed) != raw:
            raise FormalActivationRejected("one-shot authority tombstone failed")
    except Exception:
        fresh.unlink(missing_ok=True)
        raise
    return tombstone
