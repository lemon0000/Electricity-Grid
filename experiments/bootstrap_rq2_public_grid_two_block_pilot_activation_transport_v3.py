"""Fail-closed bootstrap for activation/transport successor v3."""

from __future__ import annotations

import argparse
import errno
import hashlib
import importlib.util
import json
import os
import stat
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

PROJECT_IMPORTS_PERMITTED = False
ROOT = Path(r"D:\CUHKSZ\Research Project\electricity-grid")
CONFIG_REL = "configs/rq2_public_grid_two_block_pilot_activation_transport_v3.json"
CONTROLLER_REL = "experiments/run_rq2_public_grid_two_block_pilot_activation_transport_v3.py"
WORKER_REL = "experiments/worker_rq2_public_grid_two_block_pilot_activation_transport_v3.py"
SELF_REL = "experiments/bootstrap_rq2_public_grid_two_block_pilot_activation_transport_v3.py"
TEST_REL = "tests/test_rq2_public_grid_two_block_pilot_activation_transport_v3.py"
ESCALATE_REL = "configs/rq2_public_grid_two_block_pilot_activation_transport_review_escalate_v2.json"
INNER_REL = "configs/rq2_public_grid_two_block_pilot_activation_transport_v3.SHA256SUMS.json"
OUTER_REL = "configs/rq2_public_grid_two_block_pilot_activation_transport_v3.OUTER.SHA256SUMS.json"
V1_BOOTSTRAP_REL = "experiments/bootstrap_rq2_public_grid_two_block_pilot_activation_candidate_v1.py"
V1_BOOTSTRAP_SHA256 = "c7928b06f7307c3eda001e5135dcbaae9696cd83bc44e3ff4c17e78b077a1590"
V2_OUTER_REL = "configs/rq2_public_grid_two_block_pilot_activation_transport_v2.OUTER.SHA256SUMS.json"
V2_OUTER_SHA256 = "24a1d75d43e7d1db8c59449781b947fdfb370e6658e8a5985e6b97656b96ed6a"
_PREIMPORT_PROJECT_MODULES = tuple(
    sorted(
        name
        for name in sys.modules
        if name == "src"
        or name.startswith("src.")
        or (name.startswith("experiments.") and name != __name__)
    )
)


class BootstrapRejected(RuntimeError):
    """Fail-closed bootstrap rejection."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise BootstrapRejected(f"authority unreadable: {path}") from exc
    return digest.hexdigest()


def _is_reparse(info: os.stat_result) -> bool:
    attributes = int(getattr(info, "st_file_attributes", 0))
    return bool(attributes & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)))


def _lstat(path: Path) -> os.stat_result | None:
    try:
        return os.lstat(path)
    except FileNotFoundError as exc:
        if getattr(exc, "winerror", None) in (2, 3) or exc.errno == errno.ENOENT:
            return None
        raise BootstrapRejected(f"path presence indeterminate: {path}") from exc
    except OSError as exc:
        raise BootstrapRejected(f"path presence indeterminate: {path}") from exc


def _strict_file(path: Path) -> None:
    raw = str(path)
    if not os.path.isabs(raw) or os.path.normpath(raw) != raw:
        raise BootstrapRejected(f"noncanonical authority path: {path}")
    drive, tail = os.path.splitdrive(raw)
    current = Path(drive + os.sep)
    final: os.stat_result | None = None
    for segment in [part for part in tail.split(os.sep) if part]:
        current /= segment
        info = _lstat(current)
        if info is None:
            raise BootstrapRejected(f"authority path absent: {current}")
        if stat.S_ISLNK(info.st_mode) or _is_reparse(info):
            raise BootstrapRejected(f"authority alias/reparse rejected: {current}")
        try:
            mounted = os.path.ismount(current)
        except OSError as exc:
            raise BootstrapRejected(f"mount status indeterminate: {current}") from exc
        if mounted and current != Path(drive + os.sep):
            raise BootstrapRejected(f"nested mount rejected: {current}")
        final = info
    if final is None or not stat.S_ISREG(final.st_mode):
        raise BootstrapRejected(f"authority is not an ordinary file: {path}")


def _json(path: Path) -> dict[str, Any]:
    _strict_file(path)
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BootstrapRejected(f"invalid JSON authority: {path}") from exc
    if not isinstance(payload, dict):
        raise BootstrapRejected(f"JSON authority is not an object: {path}")
    return payload


def _require_hash(relative: str, expected: str) -> Path:
    path = ROOT / relative
    _strict_file(path)
    if _sha256(path) != expected:
        raise BootstrapRejected(f"authority hash drift: {relative}")
    return path


def _reject_project_preimport(modules: Sequence[str] | None = None) -> None:
    observed = _PREIMPORT_PROJECT_MODULES if modules is None else tuple(modules)
    if observed:
        raise BootstrapRejected(f"project module preimport rejected: {observed}")


def _load_sealed_v1_helper() -> ModuleType:
    path = _require_hash(V1_BOOTSTRAP_REL, V1_BOOTSTRAP_SHA256)
    spec = importlib.util.spec_from_file_location("_sealed_activation_v1_helper_v3", path)
    if spec is None or spec.loader is None:
        raise BootstrapRejected("sealed helper import specification unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(spec.name, None)
        raise BootstrapRejected("sealed helper failed to load") from exc
    return module


def _verify_review_effect(payload: Mapping[str, Any], expected_outer: str) -> None:
    config = _json(ROOT / CONFIG_REL)
    if (
        payload.get("schema")
        != "rq2_public_grid_activation_transport_review_pass_v3"
        or payload.get("reviewer_role") != "independent_sol_reviewer"
        or payload.get("verdict") != "PASS"
        or payload.get("reviewed_outer")
        != {"path": OUTER_REL, "sha256": expected_outer}
        or payload.get("findings") != {"blocker": [], "major": [], "minor": []}
        or payload.get("effect")
        != config["future_activation_review"]["expected_effect"]
    ):
        raise BootstrapRejected("future activation-v3 review receipt overauthorizes")


def _verify_contract(config: Mapping[str, Any]) -> None:
    gates = config.get("gates")
    transport = config.get("transport_contract")
    ledger = config.get("ledger_contract")
    review = config.get("future_activation_review")
    future = config.get("future_execution_authority")
    threat = config.get("threat_model")
    if not all(isinstance(value, dict) for value in (gates, transport, ledger, review, future, threat)):
        raise BootstrapRejected("activation-v3 contract sections malformed")
    required_false = {
        "activation_v3_independent_review_passed",
        "activation_review_present",
        "execution_wrapper_present",
        "execution_wrapper_independent_review_passed",
        "dispatch_authorization_present",
        "production_dispatch_permitted",
        "two_block_pilot_execution_ready",
        "two_block_pilot_executed",
        "formal_execution_ready",
        "user_formal_run_authorized",
        "formal_result_exists",
        "claim",
        "security_certified",
    }
    if any(gates.get(key) is not False for key in required_false):
        raise BootstrapRejected("activation-v3 execution/result gates are not closed")
    if (
        transport.get("controller_exclusive_spawn_pipe_validate_append") is not True
        or transport.get("caller_popen_capability_ack_source_evidence_api_present")
        is not False
        or transport.get("internal_production_worker_api_present") is not True
        or transport.get("review_preloader_boundary_enabled") is not True
        or transport.get("production_dispatch_permitted") is not False
        or transport.get("v4_dispatch_called") is not False
        or transport.get("v4_worker_called") is not False
    ):
        raise BootstrapRejected("activation-v3 transport contract drifted")
    required_ledger_true = {
        "single_active_attempt",
        "attempt_consumed_before_spawn",
        "failed_attempt_consumed",
        "no_resume",
        "no_retry",
        "no_reorder",
        "no_skip",
        "fresh_in_memory_genesis_required",
        "caller_supplied_history_forbidden",
        "full_history_revalidated_before_every_read_and_dispatch",
        "current_session_hmac_acceptance_required",
        "second_block_requires_internal_accepted_first_record",
    }
    if (
        ledger.get("blocks")
        != ["holdout_s20260822_0008", "holdout_s20260822_0009"]
        or ledger.get("execution_order") != ledger.get("blocks")
        or any(ledger.get(key) is not True for key in required_ledger_true)
    ):
        raise BootstrapRejected("activation-v3 ledger contract drifted")
    if (
        threat.get("claims_code_and_os_pipe_origin_assurance") is not True
        or threat.get("claims_resistance_to_same_privilege_parent_memory_tampering")
        is not False
        or threat.get("security_certified") is not False
    ):
        raise BootstrapRejected("activation-v3 threat boundary drifted")
    if (
        any(
            review.get(key) is not None
            for key in ("receipt_path", "receipt_sha256", "reviewed_activation_outer_sha256")
        )
        or review.get("receipt_may_authorize_execution_wrapper_creation") is not True
        or review.get("receipt_must_not_authorize_dispatch") is not True
        or review["expected_effect"]["activation_execution_authorized"] is not False
        or review["expected_effect"]["two_block_pilot_execution_authorized"] is not False
        or any(
            future.get(key) is not None
            for key in (
                "execution_wrapper_path",
                "execution_wrapper_sha256",
                "wrapper_review_receipt_path",
                "dispatch_authorization_receipt_path",
            )
        )
        or future.get("human_dispatch_review_passed") is not False
        or future.get("execution_ready") is not False
    ):
        raise BootstrapRejected("future review/wrapper/dispatch boundary drifted")


def _verify_static_authority() -> tuple[dict[str, Any], ModuleType]:
    _require_hash(V2_OUTER_REL, V2_OUTER_SHA256)
    helper = _load_sealed_v1_helper()
    config = _json(ROOT / CONFIG_REL)
    if (
        config.get("schema")
        != "rq2_public_grid_two_block_pilot_activation_transport_v3"
        or config.get("status") != "activation_transport_v3_candidate_closed"
    ):
        raise BootstrapRejected("activation-v3 config identity drifted")
    predecessor = config.get("predecessor_authority")
    if not isinstance(predecessor, dict):
        raise BootstrapRejected("activation-v3 predecessor authority malformed")
    for path_key, hash_key in (
        ("activation_v2_inner_path", "activation_v2_inner_sha256"),
        ("activation_v2_outer_path", "activation_v2_outer_sha256"),
        ("activation_v2_escalate_path", "activation_v2_escalate_sha256"),
        ("successor_v2_outer_path", "successor_v2_outer_sha256"),
        ("successor_v2_review_pass_path", "successor_v2_review_pass_sha256"),
        ("v7_outer_path", "v7_outer_sha256"),
        ("v7_review_pass_path", "v7_review_pass_sha256"),
        ("user_authorization_path", "user_authorization_sha256"),
    ):
        _require_hash(str(predecessor[path_key]), str(predecessor[hash_key]))
    escalation = _json(ROOT / str(predecessor["activation_v2_escalate_path"]))
    if (
        escalation.get("verdict") != "ESCALATE"
        or escalation.get("reviewed_artifacts", {}).get(V2_OUTER_REL)
        != V2_OUTER_SHA256
        or escalation.get("effect", {}).get("no_execution_authority") is not True
        or escalation.get("effect", {}).get("activation_transport_v3_creation_authorized")
        is not True
    ):
        raise BootstrapRejected("activation-v2 ESCALATE receipt scope drifted")
    _verify_contract(config)
    transport = config["transport_contract"]
    _require_hash(str(transport["controller_path"]), str(transport["controller_sha256"]))
    _require_hash(str(transport["worker_path"]), str(transport["worker_sha256"]))
    primitives = config["sealed_scientific_primitive_authority"]
    for path_key, hash_key in (
        ("v4_runner_path", "v4_runner_sha256"),
        ("v7_outer_path", "v7_outer_sha256"),
        ("v7_review_pass_path", "v7_review_pass_sha256"),
    ):
        _require_hash(str(primitives[path_key]), str(primitives[hash_key]))
    inner = _json(ROOT / INNER_REL)
    files = inner.get("files")
    expected_members = {
        CONFIG_REL,
        ESCALATE_REL,
        CONTROLLER_REL,
        WORKER_REL,
        SELF_REL,
        TEST_REL,
    }
    if (
        inner.get("schema")
        != "rq2_public_grid_two_block_pilot_activation_transport_bundle_v3"
        or not isinstance(files, dict)
        or set(files) != expected_members
    ):
        raise BootstrapRejected("activation-v3 inner manifest drifted")
    for member, digest in files.items():
        _require_hash(str(member), str(digest))
    inner_hash = _sha256(ROOT / INNER_REL)
    outer = _json(ROOT / OUTER_REL)
    if outer != {
        "schema": "rq2_public_grid_two_block_pilot_activation_transport_outer_v3",
        "files": {INNER_REL: inner_hash},
    }:
        raise BootstrapRejected("activation-v3 outer manifest drifted")
    formal = config["formal_invariants"]
    _require_hash(str(formal["formal_runner_path"]), str(formal["formal_runner_sha256"]))
    _require_hash(
        str(formal["activated_formal_config_path"]),
        str(formal["activated_formal_config_sha256"]),
    )
    helper._audit_checkpoint_inventory(
        ROOT / str(formal["checkpoint_directory"]), formal["checkpoint_sha256"]
    )
    return config, helper


def validate(
    *,
    preimport_modules: Sequence[str] | None = None,
    runtime: Mapping[str, Any] | None = None,
    root_appearances: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    _reject_project_preimport(preimport_modules)
    config, helper = _verify_static_authority()
    observed = helper._runtime_observation() if runtime is None else runtime
    helper._verify_runtime(config, observed)
    helper._verify_roots(config, root_appearances)
    return {
        "schema": "rq2_public_grid_two_block_pilot_activation_transport_validation_v3",
        "validation_passed": True,
        "status": "READY_FOR_INDEPENDENT_REVIEW",
        "execution_ready": False,
        "activation_review_present": False,
        "execution_wrapper_present": False,
        "dispatch_authorization_present": False,
        "production_dispatch_permitted": False,
        "scientific_project_modules_imported": 0,
        "production_workers_started": 0,
        "scientific_loader_calls": 0,
        "solver_calls": 0,
        "result_files_written": 0,
        "formal_writes": 0,
        "formal_execution_ready": False,
        "claim": False,
        "security_certified": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.validate_only:
        print(json.dumps(validate(), indent=2, sort_keys=True))
        return 0
    _reject_project_preimport()
    config, _helper = _verify_static_authority()
    if (
        config["future_activation_review"]["receipt_path"] is None
        or config["future_execution_authority"]["execution_wrapper_path"] is None
        or config["future_execution_authority"]["dispatch_authorization_receipt_path"]
        is None
    ):
        raise BootstrapRejected("activation-v3 review/wrapper/dispatch authority is absent")
    raise BootstrapRejected("activation-v3 candidate bootstrap never dispatches")


if __name__ == "__main__":
    raise SystemExit(main())
