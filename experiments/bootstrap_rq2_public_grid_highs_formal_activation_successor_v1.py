"""Zero-solver bootstrap for the reviewed HiGHS formal activation successor."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from experiments import rq2_public_grid_highs_formal_activation_contract_v1 as contract
from experiments import (
    run_rq2_public_grid_two_block_pilot_activation_transport_v5 as resource_primitives,
)
from experiments import (
    run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_formal_v2 as controller,
)


def validate_only() -> dict[str, Any]:
    static = contract.validate_static_authority(require_activation_review=False)
    runtime = controller.validate_only()
    if static["solver_calls"] != 0 or runtime["solver_calls"] != 0:
        raise contract.FormalActivationRejected("validate-only solver gate drifted")
    if static["formal_root_writes"] != 0 or runtime["formal_root_writes"] != 0:
        raise contract.FormalActivationRejected("validate-only write gate drifted")
    return {
        "schema": "rq2_public_grid_highs_formal_activation_validation_v1",
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
    )


def _consume_one_shot_authority(dynamic: Mapping[str, Any]) -> dict[str, Any]:
    path = Path(str(dynamic["authority_path"])).resolve()
    validated = contract.validate_dynamic_authority(path)
    if any(dynamic.get(key) != value for key, value in validated.items()):
        raise contract.FormalActivationRejected(
            "dynamic authority changed before one-shot consume"
        )
    return contract.consume_one_shot_authority(dynamic)


def _spawn_controller(
    command: list[str], *, cwd: Path, environment: Mapping[str, str]
) -> dict[str, Any]:
    dynamic_authority = Path(command[-1]).resolve()
    attempt_root = dynamic_authority.parent
    stdout_path = attempt_root / "controller.stdout.log"
    stderr_path = attempt_root / "controller.stderr.log"
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
    spawn = {
        "schema": "rq2_public_grid_highs_formal_activation_spawn_receipt_v1",
        "version": 1,
        "pid": process.pid,
        "returncode": process.poll(),
        "dynamic_authority_path": str(dynamic_authority),
        "dynamic_authority_sha256": contract.sha256_file(dynamic_authority),
        "command": command,
        "cwd": str(cwd),
        "environment_sha256": contract.canonical_sha256(dict(environment)),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "formal_controller_spawned": True,
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
    dynamic = _publish_dynamic_authority(preflight)
    _require_clean_start()
    tombstone = _consume_one_shot_authority(dynamic)
    command = contract.exact_controller_command(
        Path(str(dynamic["authority_path"]))
    )
    spawn = _spawn_controller(
        command,
        cwd=contract.ROOT,
        environment=contract.exact_controller_environment(),
    )
    return {
        "schema": "rq2_public_grid_highs_formal_activation_bootstrap_result_v1",
        "preflight_path": preflight["persisted_path"],
        "preflight_sha256": preflight["persisted_sha256"],
        "dynamic_authority_path": dynamic["authority_path"],
        "dynamic_authority_sha256": dynamic["authority_sha256"],
        "authority_consumed": tombstone.get("state") == "consumed",
        "formal_controller_spawned": True,
        "controller_pid": spawn["pid"],
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
