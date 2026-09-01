"""Zero-solver bootstrap for the reviewed HiGHS formal activation successor."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from experiments import rq2_public_grid_highs_formal_activation_contract_v2 as contract
from experiments import (
    run_rq2_public_grid_two_block_pilot_activation_transport_v4 as process_identity,
)
from experiments import (
    run_rq2_public_grid_two_block_pilot_activation_transport_v5 as resource_primitives,
)
from experiments import (
    run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_formal_v3 as controller,
)


def validate_only() -> dict[str, Any]:
    static = contract.validate_static_authority(require_activation_review=False)
    runtime = controller.validate_only()
    if static["solver_calls"] != 0 or runtime["solver_calls"] != 0:
        raise contract.FormalActivationRejected("validate-only solver gate drifted")
    if static["formal_root_writes"] != 0 or runtime["formal_root_writes"] != 0:
        raise contract.FormalActivationRejected("validate-only write gate drifted")
    return {
        "schema": "rq2_public_grid_highs_formal_activation_validation_v2",
        "status": "READY_FOR_INDEPENDENT_FORMAL_ACTIVATION_REVIEW",
        "v8_post_result_independent_review_passed": True,
        "formal_activation_review_receipt_present": static[
            "formal_activation_review_receipt_present"
        ],
        "formal_execution_authorized": False,
        "formal_controller_spawned": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
        "solver_calls": 0,
        "formal_root_writes": 0,
        "runtime": runtime,
    }


def _require_activation_review() -> dict[str, Any]:
    contract.validate_static_authority(require_activation_review=False)
    return contract.require_activation_review_pass()


def _require_clean_start() -> None:
    contract.ensure_formal_roots_absent()
    contract.ensure_no_related_formal_process()


def _capture_preflight() -> dict[str, Any]:
    return contract.capture_preflight_evidence(
        contract.next_attempt_root(),
        authority_mapping=contract.preflight_authority_mapping(),
        observed_available_commit_bytes=resource_primitives._system_commit_available_bytes,
    )


def _publish_dynamic_authority(preflight: Mapping[str, Any]) -> dict[str, Any]:
    return contract.publish_dynamic_authority(
        preflight,
        review_receipt=contract.require_activation_review_pass(),
        bootstrap_identity=_current_process_identity(),
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
    except Exception as exc:
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
    except Exception as exc:  # noqa: BLE001 - persist fail-closed termination evidence
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
            expected_mapping = controller.resource_contract.closure_mapping_sha256(
                controller._runtime_authority_mapping(dynamic_authority)
            )
            if (
                not isinstance(ready, dict)
                or ready.get("schema")
                != "rq2_public_grid_highs_formal_controller_startup_ready_v2"
                or ready.get("version") != 2
                or ready.get("handshake_sha256")
                != contract.canonical_sha256(handshake)
                or ready.get("ack_sha256") != contract.canonical_sha256(ack)
                or ready.get("controller_identity") != dict(controller_identity)
                or ready.get("bootstrap_identity") != dict(bootstrap_identity)
                or ready.get("authority_mapping_sha256") != expected_mapping
                or ready.get("formal_roots_absent") is not True
                or ready.get("science_hook_calls") != 0
                or ready.get("solver_calls") != 0
                or ready.get("formal_root_writes") != 0
                or ready.get("formal_started") is not False
                or ready.get("claim") is not False
                or ready.get("security_certified") is not False
            ):
                raise contract.FormalActivationRejected(
                    "startup ready authority drifted"
                )
            _assert_process_identity(process, controller_identity)
            return ready
        if time.monotonic() >= deadline:
            raise contract.FormalActivationRejected(
                "formal controller startup ready timed out"
            )
        time.sleep(0.01)


def _record_launch_incomplete(
    attempt_root: Path,
    *,
    phase: str,
    reason: str,
    controller_identity: Mapping[str, int] | None,
    returncode: int | None,
    termination: Mapping[str, Any],
) -> dict[str, Any]:
    outcome = {
        "schema": "rq2_public_grid_highs_formal_launch_incomplete_v2",
        "version": 2,
        "wall_time_ns": time.time_ns(),
        "monotonic_ns": time.monotonic_ns(),
        "phase": phase,
        "reason": reason,
        "controller_identity": (
            dict(controller_identity) if controller_identity is not None else None
        ),
        "controller_returncode": returncode,
        "termination": dict(termination),
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
    settings = contract.load_config()["startup_handshake"]
    path = attempt_root / str(settings["launch_incomplete_filename"])
    return contract.persist_json_stable(path, outcome)


def _spawn_controller(
    command: list[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    dynamic: Mapping[str, Any],
    bootstrap_identity: Mapping[str, int],
) -> dict[str, Any]:
    dynamic_authority = Path(str(dynamic["authority_path"])).resolve()
    attempt_root = dynamic_authority.parent
    stdout_path = attempt_root / "controller.stdout.log"
    stderr_path = attempt_root / "controller.stderr.log"
    process: subprocess.Popen[Any] | None = None
    controller_identity: dict[str, int] | None = None
    try:
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
        paths = {key: Path(str(value)) for key, value in dynamic["startup_paths"].items()}
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
        release = {
            "schema": "rq2_public_grid_highs_formal_bootstrap_science_release_v2",
            "version": 2,
            "wall_time_ns": time.time_ns(),
            "monotonic_ns": time.monotonic_ns(),
            "ready_sha256": contract.canonical_sha256(ready),
            "controller_identity": controller_identity,
            "bootstrap_identity": dict(bootstrap_identity),
            "science_start_authorized": True,
            "retry_allowed": False,
            "resume_allowed": False,
            "formal_result_exists": False,
            "claim": False,
            "security_certified": False,
        }
        contract.persist_json_stable(paths["science_release"], release)
        _assert_process_identity(process, controller_identity)
    except Exception as exc:
        termination: dict[str, Any] = {
            "attempted": False,
            "reason": "process_not_created",
            "returncode": None,
        }
        if process is not None:
            if controller_identity is not None:
                termination = _terminate_owned(process, controller_identity)
            else:
                process.poll()
                termination = {
                    "attempted": False,
                    "reason": "identity_not_observed",
                    "returncode": process.returncode,
                }
        _record_launch_incomplete(
            attempt_root,
            phase="controller_startup_handshake",
            reason=f"{type(exc).__name__}:{exc}",
            controller_identity=controller_identity,
            returncode=process.returncode if process is not None else None,
            termination=termination,
        )
        raise
    spawn = {
        "schema": "rq2_public_grid_highs_formal_activation_spawn_receipt_v2",
        "version": 2,
        "pid": controller_identity["pid"],
        "create_time_ns": controller_identity["create_time_ns"],
        "bootstrap_identity": dict(bootstrap_identity),
        "returncode": process.poll(),
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
        "controller_authority_accepted": True,
        "exact_pid_create_time_verified": True,
        "formal_controller_spawned": True,
        "formal_started_at_controller_ready": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    path = attempt_root / "spawn_receipt.json"
    contract._atomic_write(path, contract.canonical_bytes(spawn))
    if json.loads(contract._read_stable(path)) != spawn:
        raise contract.FormalActivationRejected("spawn receipt readback drifted")
    return spawn


def execute() -> dict[str, Any]:
    _require_activation_review()
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
        review_receipt=contract.require_activation_review_pass(),
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
        "schema": "rq2_public_grid_highs_formal_activation_bootstrap_result_v2",
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
