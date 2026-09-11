"""V5 lifecycle bootstrap with production wiring behind fail-closed gates."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from experiments import rq2_public_grid_highs_formal_activation_contract_v5 as contract
from experiments import (
    run_rq2_public_grid_two_block_pilot_activation_transport_v4 as process_identity,
)
from experiments import (
    run_rq2_public_grid_two_block_pilot_activation_transport_v5 as resource_primitives,
)
from experiments import (
    run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_formal_v6 as controller,
)


def validate_only() -> dict[str, Any]:
    static = contract.validate_only()
    runtime = controller.validate_only()
    if static["solver_calls"] != 0 or runtime["solver_calls"] != 0:
        raise contract.FormalActivationRejected("validate-only solver gate drifted")
    if static["formal_root_writes"] != 0 or runtime["formal_root_writes"] != 0:
        raise contract.FormalActivationRejected("validate-only write gate drifted")
    config = contract.load_config()
    if static["status"] != config["status"]:
        raise contract.FormalActivationRejected("validate-only lifecycle drifted")
    sealed = config["status"] == "SEALED_READY_FOR_INDEPENDENT_REVIEW"
    production = contract._mapping(
        config["production_artifacts"], "production artifacts"
    )

    def artifact_present(name: str) -> bool:
        raw = production.get(name)
        return raw is not None and contract._entry_exists(
            contract._repo_path(raw, f"production artifact {name}")
        )

    return {
        "schema": (
            "rq2_public_grid_highs_formal_activation_validation_v5_sealed"
            if sealed
            else "rq2_public_grid_highs_formal_activation_validation_v5_draft"
        ),
        "status": config["status"],
        "v8_post_result_independent_review_passed": True,
        "formal_activation_review_receipt_present": artifact_present(
            "activation_review_receipt"
        ),
        "user_formal_run_authority_present": artifact_present(
            "user_formal_run_authority"
        ),
        "formal_execution_authorized": False,
        "formal_controller_spawned": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
        "solver_calls": 0,
        "formal_root_writes": 0,
        "runtime": runtime,
    }


def _require_execution_gates() -> tuple[dict[str, Any], dict[str, Any]]:
    contract.require_sealed_for_execution()
    review = contract.require_activation_review_pass()
    user_authority = contract.require_user_formal_run_authority()
    return review, user_authority


def _require_clean_start() -> None:
    contract.ensure_formal_roots_absent()
    contract.ensure_no_related_formal_process()


def _capture_preflight() -> dict[str, Any]:
    return contract.capture_preflight_evidence(
        contract.next_attempt_root(),
        authority_mapping=contract.preflight_authority_mapping(),
        observed_available_commit_bytes=resource_primitives.available_commit_bytes,
    )


def _consume_one_shot_authority(dynamic: Mapping[str, Any]) -> dict[str, Any]:
    path = Path(str(dynamic["authority_path"])).resolve()
    validated = contract.validate_dynamic_authority(path)
    if any(dynamic.get(key) != value for key, value in validated.items()):
        raise contract.FormalActivationRejected(
            "dynamic authority changed before one-shot consume"
        )
    return contract.consume_one_shot_authority(dynamic)


def _current_process_identity() -> dict[str, int]:
    return {
        "pid": os.getpid(),
        "create_time_ns": process_identity._process_creation_time_ns(os.getpid()),
    }


def _observe_process_identity(process: subprocess.Popen[Any]) -> dict[str, int]:
    if process.poll() is not None:
        raise contract.FormalActivationRejected(
            "formal controller exited before PID/create-time observation"
        )
    identity = {
        "pid": process.pid,
        "create_time_ns": process_identity._process_creation_time_ns(process.pid),
    }
    _assert_process_identity(process, identity)
    return identity


def _assert_process_identity(
    process: subprocess.Popen[Any], identity: Mapping[str, int]
) -> None:
    pair = contract._process_identity(identity, "controller identity")
    if process.pid != pair["pid"]:
        raise contract.FormalActivationRejected("controller PID drifted")
    if process.poll() is not None:
        raise contract.FormalActivationRejected(
            "formal controller exited before startup handshake"
        )
    try:
        observed = process_identity._process_creation_time_ns(process.pid)
    except BaseException as exc:
        raise contract.FormalActivationRejected(
            "formal controller exited before startup handshake"
        ) from exc
    if observed != pair["create_time_ns"]:
        raise contract.FormalActivationRejected(
            "formal controller create-time drifted (possible PID reuse)"
        )


def _terminate_owned(
    process: subprocess.Popen[Any], identity: Mapping[str, int]
) -> dict[str, Any]:
    pair = contract._process_identity(identity, "controller identity")
    if process.poll() is not None:
        return {
            "attempted": False,
            "reason": "already_exited",
            "returncode": process.returncode,
        }
    try:
        _assert_process_identity(process, pair)
        process_identity.terminate_exact_owned_child(
            process,
            expected_pid=pair["pid"],
            expected_create_time_ns=pair["create_time_ns"],
        )
    except BaseException as exc:  # noqa: BLE001 - recovery must survive KI/SystemExit
        return {
            "attempted": False,
            "reason": f"identity_or_termination_indeterminate:{type(exc).__name__}",
            "returncode": process.poll(),
        }
    return {
        "attempted": True,
        "reason": "exact_owned_child_terminated",
        "returncode": process.returncode,
    }


def _wait_for_controller_stop_proof(
    process: subprocess.Popen[Any],
    *,
    dynamic_authority: Path,
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
) -> dict[str, Any]:
    """Do not release supervision until death or a strict controller stop ACK."""
    attempt_root = dynamic_authority.resolve().parent
    paths = {
        key: Path(value) for key, value in contract.startup_paths(attempt_root).items()
    }
    settings = contract.load_config()["startup_handshake"]
    poll = float(settings["poll_interval_seconds"])
    deadline = time.monotonic() + float(settings["bootstrap_wait_timeout_seconds"])
    while True:
        if process.poll() is not None:
            return {
                "proof": "exact_child_death_observed",
                "returncode": process.returncode,
            }
        try:
            if paths["controller_cancellation_ack"].is_file():
                acknowledgement = contract.validate_controller_stop_ack(
                    paths["controller_cancellation_ack"],
                    dynamic_authority=dynamic_authority,
                    controller_identity=controller_identity,
                    bootstrap_identity=bootstrap_identity,
                )
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    _terminate_owned(process, controller_identity)
                return {
                    "proof": "strict_controller_stop_acknowledgement",
                    "returncode": process.poll(),
                    "acknowledgement": acknowledgement,
                }
            if time.monotonic() >= deadline:
                _terminate_owned(process, controller_identity)
                deadline = time.monotonic() + float(
                    settings["bootstrap_wait_timeout_seconds"]
                )
        except BaseException:  # noqa: BLE001 - supervision cannot be abandoned
            if process.poll() is not None:
                return {
                    "proof": "exact_child_death_observed",
                    "returncode": process.returncode,
                }
        time.sleep(poll)


def _recover_post_release_baseexception(
    process: subprocess.Popen[Any],
    *,
    dynamic_authority: Path,
    dynamic: Mapping[str, Any],
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
    release_path: Path,
    release_acceptance: Mapping[str, Any] | None,
    exception: BaseException,
    recovery_identity_override: Mapping[str, int] | None = None,
    injected_termination_failure: bool = False,
    recovery_fault_hook: Any | None = None,
    spawn_receipt_committed: bool = False,
) -> dict[str, Any]:
    """Close every post-release exception under one durable recovery protocol."""
    attempt_root = dynamic_authority.resolve().parent
    formal_roots = {
        name: Path(str(path))
        for name, path in contract._mapping(
            dynamic["formal_roots"], "formal roots"
        ).items()
    }
    if spawn_receipt_committed:
        lifecycle = contract.claim_lifecycle_decision(
            attempt_root,
            lifecycle_class="cancelled_before_science",
            controller_identity=controller_identity,
            bootstrap_identity=bootstrap_identity,
            formal_roots_override=formal_roots,
        )
        if lifecycle["outcome"]["lifecycle_class"] == "controller_owned_lifecycle":
            deferred = contract.persist_deferred_supervisor_interruption(
                attempt_root,
                exception=exception,
                formal_roots_override=formal_roots,
            )
            terminal = _supervise_controller_authoritative_terminal(
                process,
                controller_identity=controller_identity,
                release_path=release_path,
                release_acceptance=release_acceptance,
                terminal_outcome_path=Path(
                    contract.startup_paths(attempt_root)["terminal_outcome"]
                ),
                formal_roots_override=formal_roots,
                defer_baseexceptions=True,
            )
            return {
                "lifecycle_decision": lifecycle,
                "deferred_supervisor_interruption": deferred,
                "terminal_outcome": terminal,
            }
    cancellation_error: BaseException | None = None
    cancellation: dict[str, Any] | None = None
    try:
        cancellation = contract.persist_controller_cancellation(
            attempt_root,
            dynamic_authority=dynamic_authority,
            controller_identity=controller_identity,
            bootstrap_identity=bootstrap_identity,
            reason=f"{type(exception).__name__}:{exception}",
        )
    except BaseException as exc:  # noqa: BLE001 - recovery must continue
        cancellation_error = exc

    recovery_error: BaseException | None = None
    try:
        if injected_termination_failure:
            raise RuntimeError("injected termination adapter failure")
        termination = _terminate_owned(
            process,
            recovery_identity_override or controller_identity,
        )
    except BaseException as exc:  # noqa: BLE001 - recovery must continue
        recovery_error = exc
        termination = {
            "attempted": False,
            "reason": f"recovery_baseexception:{type(exc).__name__}",
            "returncode": process.poll(),
        }
    else:
        if recovery_fault_hook is not None:
            try:
                recovery_fault_hook("recovery_after_owned_termination")
            except BaseException as exc:  # noqa: BLE001 - recovery must continue
                recovery_error = exc
                termination["reason"] = (
                    str(termination["reason"])
                    + ";secondary_recovery_baseexception:"
                    + type(exc).__name__
                )

    reason = f"{type(exception).__name__}:{exception}"
    if cancellation_error is not None:
        reason += (
            f";cancellation={type(cancellation_error).__name__}:{cancellation_error}"
        )
    if recovery_error is not None:
        reason += f";recovery={type(recovery_error).__name__}:{recovery_error}"
    terminal = _record_post_release_unresolved(
        attempt_root,
        reason=reason,
        reporter="bootstrap_supervisor",
        controller_identity=controller_identity,
        returncode=process.returncode,
        termination=termination,
        release_path=release_path,
        release_acceptance=release_acceptance,
        formal_roots_override=formal_roots,
    )
    stop_proof = _wait_for_controller_stop_proof(
        process,
        dynamic_authority=dynamic_authority,
        controller_identity=controller_identity,
        bootstrap_identity=bootstrap_identity,
    )
    return {
        "cancellation": cancellation,
        "termination": termination,
        "terminal_outcome": terminal,
        "stop_proof": stop_proof,
    }


def _wait_for_controller_handshake(
    process: subprocess.Popen[Any],
    *,
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
    handshake_path: Path,
    bindings: Mapping[str, Mapping[str, str]],
    command: list[str],
    cwd: str,
    environment: Mapping[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while True:
        _assert_process_identity(process, controller_identity)
        if handshake_path.is_file():
            raw = contract._read_stable(handshake_path)
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise contract.FormalActivationRejected(
                    "startup handshake malformed"
                ) from exc
            validated = contract.validate_startup_handshake(
                value,
                controller_identity=controller_identity,
                bootstrap_identity=bootstrap_identity,
                bindings=bindings,
                command=command,
                cwd=cwd,
                environment=environment,
            )
            _assert_process_identity(process, controller_identity)
            return validated
        if time.monotonic() >= deadline:
            raise contract.FormalActivationRejected(
                "formal controller startup handshake timed out"
            )
        time.sleep(0.01)


def _publish_startup_ack(
    path: Path,
    *,
    handshake: Mapping[str, Any],
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
) -> dict[str, Any]:
    ack = contract.build_startup_ack(
        handshake=handshake,
        controller_identity=controller_identity,
        bootstrap_identity=bootstrap_identity,
    )
    return contract.persist_json_stable(path, ack)


def _wait_for_startup_ready(
    process: subprocess.Popen[Any],
    *,
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
    path: Path,
    handshake: Mapping[str, Any],
    ack: Mapping[str, Any],
    dynamic_authority: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while True:
        _assert_process_identity(process, controller_identity)
        if path.is_file():
            ready = json.loads(contract._read_stable(path))
            expected_mapping = contract.canonical_sha256(
                contract.runtime_authority_mapping(dynamic_authority)
            )
            closure = contract.verify_execution_closure()
            ready = contract.validate_startup_ready(
                ready,
                handshake=handshake,
                ack=ack,
                controller_identity=controller_identity,
                bootstrap_identity=bootstrap_identity,
                authority_mapping_sha256=expected_mapping,
                execution_closure_sha256=str(closure["members_sha256"]),
            )
            _assert_process_identity(process, controller_identity)
            return ready
        if time.monotonic() >= deadline:
            raise contract.FormalActivationRejected(
                "formal controller startup ready timed out"
            )
        time.sleep(0.01)


def _wait_for_release_acceptance(
    process: subprocess.Popen[Any],
    *,
    controller_identity: Mapping[str, int],
    bootstrap_identity: Mapping[str, int],
    path: Path,
    release: Mapping[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    closure = contract.verify_execution_closure()
    while True:
        if path.is_file():
            accepted = contract.validate_science_release_acceptance(
                json.loads(contract._read_stable(path)),
                release=release,
                controller_identity=controller_identity,
                bootstrap_identity=bootstrap_identity,
                execution_closure_sha256=str(closure["members_sha256"]),
            )
            _assert_process_identity(process, controller_identity)
            return accepted
        _assert_process_identity(process, controller_identity)
        if time.monotonic() >= deadline:
            raise contract.FormalActivationRejected(
                "science release acceptance timed out"
            )
        time.sleep(0.01)


def _observe_root(path: Path) -> dict[str, Any]:
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


def _record_post_release_unresolved(
    attempt_root: Path,
    *,
    reason: str,
    controller_identity: Mapping[str, int] | None,
    returncode: int | None,
    termination: Mapping[str, Any],
    release_path: Path,
    release_acceptance: Mapping[str, Any] | None,
    formal_roots_override: Mapping[str, Path] | None = None,
    reporter: str = "bootstrap_supervisor",
) -> dict[str, Any]:
    return contract.persist_post_release_unresolved(
        attempt_root,
        reason=reason,
        reporter=reporter,
        controller_identity=controller_identity,
        returncode=returncode,
        termination=termination,
        release_path=release_path,
        release_acceptance=release_acceptance,
        formal_roots_override=formal_roots_override,
    )


def _record_launch_incomplete(
    attempt_root: Path,
    *,
    phase: str,
    reason: str,
    controller_identity: Mapping[str, int] | None,
    returncode: int | None,
    termination: Mapping[str, Any],
) -> dict[str, Any]:
    settings = contract.load_config()["startup_handshake"]
    if (attempt_root / str(settings["science_release_filename"])).exists():
        raise contract.FormalActivationRejected(
            "launch_incomplete is forbidden after science release persistence"
        )
    outcome = {
        "schema": "rq2_public_grid_highs_formal_launch_incomplete_v4",
        "version": 4,
        "wall_time_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
        "phase": phase,
        "reason": reason,
        "controller_identity": (
            dict(controller_identity) if controller_identity is not None else None
        ),
        "controller_returncode": returncode,
        "termination": dict(termination),
        "release_persisted": False,
        "one_shot_authority_remains_consumed": True,
        "retry_allowed": False,
        "resume_allowed": False,
        "formal_controller_spawned": False,
        "formal_started": False,
        "formal_result_exists": False,
        "mathematical_infeasibility_inferred": False,
        "claim": False,
        "security_certified": False,
    }
    path = attempt_root / str(settings["launch_incomplete_filename"])
    return contract.persist_json_stable(path, outcome)


def _supervise_controller_authoritative_terminal(
    process: subprocess.Popen[Any],
    *,
    controller_identity: Mapping[str, int],
    release_path: Path,
    release_acceptance: Mapping[str, Any],
    terminal_outcome_path: Path,
    formal_roots_override: Mapping[str, Path] | None = None,
    defer_baseexceptions: bool = False,
) -> dict[str, Any]:
    """Supervise until exact death and validate either authoritative terminal class."""
    settings = contract.load_config()["startup_handshake"]
    poll = float(settings["poll_interval_seconds"])
    while process.poll() is None:
        try:
            _assert_process_identity(process, controller_identity)
            time.sleep(poll)
        except BaseException:
            if not defer_baseexceptions:
                raise
    if not terminal_outcome_path.is_file() or terminal_outcome_path.is_symlink():
        raise contract.FormalActivationRejected(
            "controller exited without authoritative terminal evidence"
        )
    terminal = contract.validate_terminal_outcome(
        terminal_outcome_path, formal_roots_override=formal_roots_override
    )["outcome"]
    if (
        terminal.get("controller_identity") != dict(controller_identity)
        or terminal.get("release_path") != str(release_path)
        or terminal.get("release_sha256") != contract.sha256_file(release_path)
        or terminal.get("release_acceptance_sha256")
        != contract.sha256_file(
            release_path.parent / str(settings["science_release_accepted_filename"])
        )
    ):
        raise contract.FormalActivationRejected(
            "controller authoritative terminal evidence drifted"
        )
    if (
        process.returncode == 0
        and terminal.get("terminal_class") != "success"
        or process.returncode != 0
        and terminal.get("terminal_class") != "unresolved"
    ):
        raise contract.FormalActivationRejected(
            "controller return code and terminal class disagree"
        )
    return terminal


def _supervise_controller_after_acceptance(
    process: subprocess.Popen[Any],
    *,
    controller_identity: Mapping[str, int],
    release_path: Path,
    release_acceptance: Mapping[str, Any],
    terminal_outcome_path: Path,
    formal_roots_override: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    terminal = _supervise_controller_authoritative_terminal(
        process,
        controller_identity=controller_identity,
        release_path=release_path,
        release_acceptance=release_acceptance,
        terminal_outcome_path=terminal_outcome_path,
        formal_roots_override=formal_roots_override,
    )
    if (
        terminal.get("terminal_class") != "success"
        or terminal.get("controller_terminal_status")
        != "completed_without_controller_exception"
    ):
        raise contract.FormalActivationRejected(
            "controller terminal success evidence drifted"
        )
    return terminal


def _spawn_controller(
    command: list[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    dynamic: Mapping[str, Any],
    bootstrap_identity: Mapping[str, int],
    fault_hook: Any | None = None,
    recovery_identity_override: Mapping[str, int] | None = None,
    injected_termination_failure: bool = False,
    recovery_fault_hook: Any | None = None,
) -> dict[str, Any]:
    dynamic_authority = Path(str(dynamic["authority_path"])).resolve()
    attempt_root = dynamic_authority.parent
    stdout_path = attempt_root / "controller.stdout.log"
    stderr_path = attempt_root / "controller.stderr.log"
    process: subprocess.Popen[Any] | None = None
    controller_identity: dict[str, int] | None = None
    paths = {key: Path(str(value)) for key, value in dynamic["startup_paths"].items()}
    hook = fault_hook or (lambda _stage: None)
    release_acceptance: dict[str, Any] | None = None
    spawn_receipt_path = paths["spawn_receipt"]
    spawn_receipt_committed = False
    spawn: dict[str, Any] | None = None
    try:
        contract.verify_execution_closure()
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=dict(environment),
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                close_fds=True,
            )
        controller_identity = _observe_process_identity(process)
        bindings = controller._startup_bindings(dynamic_authority)
        settings = contract.load_config()["startup_handshake"]
        timeout = float(settings["bootstrap_wait_timeout_seconds"])
        handshake = _wait_for_controller_handshake(
            process,
            controller_identity=controller_identity,
            bootstrap_identity=bootstrap_identity,
            handshake_path=paths["handshake"],
            bindings=bindings,
            command=command,
            cwd=str(cwd),
            environment=environment,
            timeout_seconds=timeout,
        )
        contract.verify_execution_closure()
        ack = _publish_startup_ack(
            paths["bootstrap_ack"],
            handshake=handshake,
            controller_identity=controller_identity,
            bootstrap_identity=bootstrap_identity,
        )
        ready = _wait_for_startup_ready(
            process,
            controller_identity=controller_identity,
            bootstrap_identity=bootstrap_identity,
            path=paths["startup_ready"],
            handshake=handshake,
            ack=ack,
            dynamic_authority=dynamic_authority,
            timeout_seconds=timeout,
        )
        contract.verify_execution_closure()
        release = contract.build_science_release(
            ready=ready,
            controller_identity=controller_identity,
            bootstrap_identity=bootstrap_identity,
        )
        release_raw = contract.canonical_bytes(release)
        contract._atomic_write(paths["science_release"], release_raw)
        hook("release_after_atomic_commit_before_stable_readback")
        if contract._read_stable(paths["science_release"]) != release_raw:
            raise contract.FormalActivationRejected("science release readback drifted")
        hook("release_after_stable_readback_before_phase_return")
        release_acceptance = _wait_for_release_acceptance(
            process,
            controller_identity=controller_identity,
            bootstrap_identity=bootstrap_identity,
            path=paths["science_release_accepted"],
            release=release,
            timeout_seconds=timeout,
        )
        hook("post_acceptance_before_spawn_receipt")
        path = paths["spawn_receipt"]
        _assert_process_identity(process, controller_identity)
        spawn = {
            "schema": (
                "rq2_public_grid_highs_formal_activation_spawn_receipt_v5_preseal"
                if str(dynamic["schema"]).endswith("_preseal")
                else "rq2_public_grid_highs_formal_activation_spawn_receipt_v5"
            ),
            "version": 5,
            "pid": controller_identity["pid"],
            "create_time_ns": controller_identity["create_time_ns"],
            "bootstrap_identity": dict(bootstrap_identity),
            "returncode": None,
            "dynamic_authority_path": str(dynamic_authority),
            "dynamic_authority_sha256": contract.sha256_file(dynamic_authority),
            "command": command,
            "cwd": str(cwd),
            "environment_sha256": contract.canonical_sha256(dict(environment)),
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "startup_handshake_path": str(paths["handshake"]),
            "startup_handshake_sha256": contract.sha256_file(paths["handshake"]),
            "startup_ack_path": str(paths["bootstrap_ack"]),
            "startup_ack_sha256": contract.sha256_file(paths["bootstrap_ack"]),
            "startup_ready_path": str(paths["startup_ready"]),
            "startup_ready_sha256": contract.sha256_file(paths["startup_ready"]),
            "science_release_path": str(paths["science_release"]),
            "science_release_sha256": contract.sha256_file(paths["science_release"]),
            "science_release_accepted_path": str(paths["science_release_accepted"]),
            "science_release_accepted_sha256": contract.sha256_file(
                paths["science_release_accepted"]
            ),
            "release_acceptance_proven": release_acceptance is not None,
            "controller_authority_accepted": True,
            "exact_pid_create_time_verified": True,
            "formal_controller_spawned": True,
            "formal_started_at_controller_ready": False,
            "formal_start_status": "released_and_controller_acceptance_proven",
            "formal_result_exists": False,
            "claim": False,
            "security_certified": False,
        }
        prospective = contract.validate_spawn_receipt_payload(
            spawn, attempt_root=attempt_root
        )
        if prospective["receipt"] != spawn:
            raise contract.FormalActivationRejected(
                "prospective spawn receipt identity drifted"
            )
        _assert_process_identity(process, controller_identity)
        persisted_spawn, created = contract.persist_json_exclusive_stable(path, spawn)
        spawn_receipt_committed = True
        if not created or persisted_spawn != spawn:
            raise contract.FormalActivationRejected("spawn receipt identity drifted")
        hook("spawn_receipt_after_atomic_commit")
        if contract.validate_spawn_receipt(path)["receipt"] != spawn:
            raise contract.FormalActivationRejected(
                "committed spawn receipt identity drifted"
            )
        terminal = _supervise_controller_after_acceptance(
            process,
            controller_identity=controller_identity,
            release_path=paths["science_release"],
            release_acceptance=release_acceptance,
            terminal_outcome_path=paths["terminal_outcome"],
            formal_roots_override={
                name: Path(str(path))
                for name, path in contract._mapping(
                    dynamic["formal_roots"], "formal roots"
                ).items()
            },
        )
    except BaseException as exc:
        phase: dict[str, Any] | None = None
        if paths["science_release"].is_file() and controller_identity is not None:
            closure = contract.verify_execution_closure()

            def validate_release(value: Mapping[str, Any]) -> dict[str, Any]:
                return contract.validate_science_release(
                    value,
                    ready=ready,
                    controller_identity=controller_identity,
                    bootstrap_identity=bootstrap_identity,
                )

            def validate_acceptance(
                value: Mapping[str, Any], release_value: Mapping[str, Any]
            ) -> dict[str, Any]:
                return contract.validate_science_release_acceptance(
                    value,
                    release=release_value,
                    controller_identity=controller_identity,
                    bootstrap_identity=bootstrap_identity,
                    execution_closure_sha256=str(closure["members_sha256"]),
                )

            phase = contract.observe_release_acceptance_authority(
                paths["science_release"],
                paths["science_release_accepted"],
                validate_release=validate_release,
                validate_acceptance=validate_acceptance,
            )
            release_acceptance = phase["release_acceptance"]
        if (
            not spawn_receipt_committed
            and spawn_receipt_path.is_file()
            and spawn is not None
        ):
            try:
                spawn_receipt_committed = (
                    contract.validate_spawn_receipt(spawn_receipt_path)["receipt"]
                    == spawn
                )
            except BaseException:  # noqa: BLE001 - invalid receipt stays untrusted
                spawn_receipt_committed = False
        if (
            phase is not None
            and process is not None
            and controller_identity is not None
        ):
            _recover_post_release_baseexception(
                process,
                dynamic_authority=dynamic_authority,
                dynamic=dynamic,
                controller_identity=controller_identity,
                bootstrap_identity=bootstrap_identity,
                release_path=paths["science_release"],
                release_acceptance=release_acceptance,
                exception=exc,
                recovery_identity_override=recovery_identity_override,
                injected_termination_failure=injected_termination_failure,
                recovery_fault_hook=recovery_fault_hook,
                spawn_receipt_committed=spawn_receipt_committed,
            )
        else:
            termination: dict[str, Any] = {
                "attempted": False,
                "reason": "process_not_created",
                "returncode": None,
            }
            if process is not None and controller_identity is not None:
                termination = _terminate_owned(
                    process,
                    recovery_identity_override or controller_identity,
                )
            _record_launch_incomplete(
                attempt_root,
                phase="controller_startup_handshake",
                reason=f"{type(exc).__name__}:{exc}",
                controller_identity=controller_identity,
                returncode=process.returncode if process is not None else None,
                termination=termination,
            )
        raise
    if spawn is None:
        raise contract.FormalActivationRejected("spawn receipt was not constructed")
    return {**spawn, "terminal_outcome": terminal}


def _execute_preseal_startup_probe(
    attempt_root: Path,
    *,
    fault_phase: str | None = None,
    fault_type: str | None = None,
    termination_identity_mismatch: bool = False,
    injected_termination_failure: bool = False,
    recovery_fault_type: str | None = None,
) -> dict[str, Any]:
    """Exercise the real two-process startup wiring with no science/solver call."""
    if fault_phase is not None and fault_type not in {
        "KeyboardInterrupt",
        "SystemExit",
    }:
        raise contract.FormalActivationRejected("pre-seal fault type is not registered")
    bootstrap_identity = _current_process_identity()
    dynamic, tombstone = contract.prepare_preseal_authority(
        attempt_root,
        bootstrap_identity=bootstrap_identity,
        fault_phase=fault_phase,
        fault_type=fault_type,
    )

    def inject(stage: str) -> None:
        if stage != fault_phase:
            return
        if fault_type == "KeyboardInterrupt":
            raise KeyboardInterrupt(f"injected:{stage}")
        if fault_type == "SystemExit":
            raise SystemExit(f"injected:{stage}")

    def inject_recovery(stage: str) -> None:
        if recovery_fault_type == "KeyboardInterrupt":
            raise KeyboardInterrupt(f"injected:{stage}")
        if recovery_fault_type == "SystemExit":
            raise SystemExit(f"injected:{stage}")

    recovery_identity = None
    if termination_identity_mismatch:
        recovery_identity = {
            "pid": os.getpid(),
            "create_time_ns": process_identity._process_creation_time_ns(os.getpid()),
        }

    spawn = _spawn_controller(
        list(dynamic["exact_command"]),
        cwd=contract.ROOT,
        environment=contract._mapping(
            dynamic["exact_environment"], "exact environment"
        ),
        dynamic=dynamic,
        bootstrap_identity=bootstrap_identity,
        fault_hook=inject,
        recovery_identity_override=recovery_identity,
        injected_termination_failure=injected_termination_failure,
        recovery_fault_hook=inject_recovery
        if recovery_fault_type is not None
        else None,
    )
    terminal = contract._mapping(spawn["terminal_outcome"], "terminal outcome")
    result = contract._mapping(terminal["class_evidence"], "terminal evidence")
    return {
        "schema": "rq2_v5_preseal_real_startup_probe",
        "status": "NONAUTHORITATIVE_ZERO_SOLVER_PROBE_COMPLETE",
        "preflight_captured": True,
        "authority_consumed": tombstone.get("state") == "consumed",
        "controller_spawned": True,
        "release_acceptance_proven": terminal["release_acceptance_proven"],
        "terminal_class": terminal["terminal_class"],
        "power_system_block_count": 1071,
        "fresh_worker_process_per_block_wiring_present": callable(
            controller._dispatch_one
        ),
        "resource_journal_wiring_present": callable(
            controller._persist_resource_journal
        ),
        "checkpoint_and_finalize_wiring_present": callable(
            controller._run_released_block_lifecycle
        ),
        "result_sha256": result.get("result_sha256"),
        "solver_calls": 0,
        "formal_root_writes": 0,
        "formal_execution_authorized": False,
        "claim": False,
        "security_certified": False,
    }


def execute() -> dict[str, Any]:
    review, user_authority = _require_execution_gates()
    contract.verify_execution_closure()
    _require_clean_start()
    preflight = _capture_preflight()
    if (
        preflight.get("stable_readback_verified") is not True
        or preflight.get("threshold_passed") is not True
    ):
        raise contract.FormalActivationRejected(
            "system commit preflight did not meet the frozen 10 GiB threshold"
        )
    bootstrap_identity = _current_process_identity()
    dynamic = contract.publish_dynamic_authority(
        preflight,
        review_receipt=review,
        user_run_authority=user_authority,
        bootstrap_identity=bootstrap_identity,
    )
    _require_clean_start()
    tombstone = _consume_one_shot_authority(dynamic)
    command = contract.exact_controller_command(
        Path(str(dynamic["authority_path"])),
        bootstrap_identity=bootstrap_identity,
    )
    spawn = _spawn_controller(
        command,
        cwd=contract.ROOT,
        environment=contract.exact_controller_environment(),
        dynamic=dynamic,
        bootstrap_identity=bootstrap_identity,
    )
    return {
        "schema": "rq2_public_grid_highs_formal_activation_bootstrap_result_v4",
        "preflight_path": preflight["persisted_path"],
        "preflight_sha256": preflight["persisted_sha256"],
        "dynamic_authority_path": dynamic["authority_path"],
        "dynamic_authority_sha256": dynamic["authority_sha256"],
        "authority_consumed": tombstone.get("state") == "consumed",
        "formal_controller_spawned": True,
        "controller_pid": spawn["pid"],
        "controller_create_time_ns": spawn["create_time_ns"],
        "controller_authority_accepted": True,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.validate_only == args.execute:
        raise SystemExit("choose exactly one of --validate-only or --execute")
    report = execute() if args.execute else validate_only()
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
