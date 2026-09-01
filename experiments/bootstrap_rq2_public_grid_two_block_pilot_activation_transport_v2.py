"""Fail-closed bootstrap for activation/transport successor v2."""

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
CONFIG_REL = "configs/rq2_public_grid_two_block_pilot_activation_transport_v2.json"
RUNNER_REL = "experiments/run_rq2_public_grid_two_block_pilot_activation_transport_v2.py"
SELF_REL = "experiments/bootstrap_rq2_public_grid_two_block_pilot_activation_transport_v2.py"
TEST_REL = "tests/test_rq2_public_grid_two_block_pilot_activation_transport_v2.py"
REWORK_REL = "configs/rq2_public_grid_two_block_pilot_activation_review_rework_v1.json"
INNER_REL = "configs/rq2_public_grid_two_block_pilot_activation_transport_v2.SHA256SUMS.json"
OUTER_REL = "configs/rq2_public_grid_two_block_pilot_activation_transport_v2.OUTER.SHA256SUMS.json"
V1_BOOTSTRAP_REL = "experiments/bootstrap_rq2_public_grid_two_block_pilot_activation_candidate_v1.py"
V1_BOOTSTRAP_SHA256 = "c7928b06f7307c3eda001e5135dcbaae9696cd83bc44e3ff4c17e78b077a1590"
V1_OUTER_REL = "configs/rq2_public_grid_two_block_pilot_activation_candidate_v1.OUTER.SHA256SUMS.json"
V1_OUTER_SHA256 = "844f4a59527306962e97e7879e4ccb7abb1893b65a819b782c56110e4df073f2"
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
        payload = json.loads(path.read_text(encoding="utf-8"))
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
    spec = importlib.util.spec_from_file_location("_sealed_activation_v1_helper", path)
    if spec is None or spec.loader is None:
        raise BootstrapRejected("sealed v1 helper import specification unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(spec.name, None)
        raise BootstrapRejected("sealed v1 helper failed to load") from exc
    return module


def _verify_review_effect(payload: Mapping[str, Any], expected_outer: str) -> None:
    expected_effect = {
        "activation_candidate_independent_review_passed": True,
        "versioned_execution_wrapper_creation_authorized": True,
        "execution_wrapper_independent_review_passed": False,
        "activation_execution_authorized": False,
        "two_block_pilot_execution_authorized": False,
        "formal_activation_authorized": False,
        "formal_execution_ready": False,
        "user_formal_run_authorized": False,
        "claim": False,
        "security_certified": False,
    }
    if (
        payload.get("schema")
        != "rq2_public_grid_two_block_pilot_activation_transport_review_pass_v2"
        or payload.get("reviewer_role") != "independent_sol_reviewer"
        or payload.get("verdict") != "PASS"
        or payload.get("reviewed_outer")
        != {"path": OUTER_REL, "sha256": expected_outer}
        or payload.get("findings") != {"blocker": [], "major": [], "minor": []}
        or payload.get("effect") != expected_effect
    ):
        raise BootstrapRejected("future activation-v2 review receipt overauthorizes or drifts")


def _verify_contract(config: Mapping[str, Any]) -> None:
    gates = config.get("gates")
    if not isinstance(gates, dict):
        raise BootstrapRejected("activation-v2 gates malformed")
    required_false = {
        "activation_v1_review_passed",
        "activation_v2_independent_review_passed",
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
        raise BootstrapRejected("activation-v2 execution/result gates are not closed")
    transport = config.get("transport_contract")
    ledger = config.get("ledger_contract")
    review = config.get("future_activation_review")
    wrapper = config.get("future_execution_wrapper")
    primitives = config.get("sealed_scientific_primitive_authority")
    if (
        not isinstance(transport, dict)
        or transport.get("production_worker_enabled") is not False
        or transport.get("production_dispatch_permitted") is not False
        or transport.get("v4_dispatch_called") is not False
        or transport.get("v4_worker_called") is not False
        or transport.get("preloader_probe_enabled") is not True
        or transport.get("scientific_loader_calls_in_probe") != 0
        or transport.get("solver_calls_in_probe") != 0
        or transport.get("result_writes_in_probe") != 0
        or transport.get("formal_writes_in_probe") != 0
    ):
        raise BootstrapRejected("activation-v2 transport boundary drifted")
    if (
        not isinstance(ledger, dict)
        or ledger.get("blocks")
        != ["holdout_s20260822_0008", "holdout_s20260822_0009"]
        or ledger.get("execution_order") != ledger.get("blocks")
        or any(
            ledger.get(key) is not True
            for key in (
                "no_resume",
                "no_retry",
                "no_reorder",
                "no_skip",
                "fresh_in_memory_genesis_required",
                "caller_supplied_history_forbidden",
                "live_popen_attempt_capability_required",
                "one_shot_attempt_capability_required",
                "full_history_revalidated_before_every_read_append_and_predecessor",
                "current_session_hmac_acceptance_required",
                "second_block_requires_verified_first_digest",
                "controller_may_terminate_only_exact_pid_create_time",
            )
        )
    ):
        raise BootstrapRejected("activation-v2 ledger contract drifted")
    if (
        not isinstance(review, dict)
        or any(review.get(key) is not None for key in ("receipt_path", "receipt_sha256", "reviewed_activation_outer_sha256"))
        or review.get("receipt_may_authorize_execution_wrapper_creation") is not True
        or review.get("receipt_must_not_authorize_dispatch") is not True
        or review.get("expected_effect", {}).get("activation_execution_authorized") is not False
        or review.get("expected_effect", {}).get("two_block_pilot_execution_authorized") is not False
    ):
        raise BootstrapRejected("activation-v2 future review boundary drifted")
    if (
        not isinstance(wrapper, dict)
        or any(
            wrapper.get(key) is not None
            for key in (
                "wrapper_path",
                "wrapper_sha256",
                "wrapper_outer_sha256",
                "independent_review_receipt_path",
                "independent_review_receipt_sha256",
                "dispatch_authorization_receipt_path",
                "dispatch_authorization_receipt_sha256",
            )
        )
        or wrapper.get("human_dispatch_review_passed") is not False
        or wrapper.get("execution_ready") is not False
    ):
        raise BootstrapRejected("future execution-wrapper boundary drifted")
    if (
        not isinstance(primitives, dict)
        or primitives.get("forbidden_v4_gated_entrypoints")
        != ["_dispatch_one", "_worker_from_capability", "run"]
        or primitives.get("scientific_transport_ledger_publication_semantics_changed")
        is not False
    ):
        raise BootstrapRejected("sealed primitive boundary drifted")
    for path_key, hash_key in (
        ("v4_runner_path", "v4_runner_sha256"),
        ("v7_runner_path", "v7_runner_sha256"),
    ):
        _require_hash(str(primitives[path_key]), str(primitives[hash_key]))


def _verify_static_authority() -> tuple[dict[str, Any], ModuleType]:
    _require_hash(V1_OUTER_REL, V1_OUTER_SHA256)
    helper = _load_sealed_v1_helper()
    try:
        helper._verify_static_authority()
    except Exception as exc:
        raise BootstrapRejected("sealed activation-v1 authority drifted") from exc
    config = _json(ROOT / CONFIG_REL)
    if (
        config.get("schema")
        != "rq2_public_grid_two_block_pilot_activation_transport_v2"
        or config.get("status") != "activation_transport_v2_candidate_closed"
    ):
        raise BootstrapRejected("activation-v2 config identity drifted")
    predecessor = config.get("predecessor_authority")
    if not isinstance(predecessor, dict):
        raise BootstrapRejected("activation-v2 predecessor authority malformed")
    for path_key, hash_key in (
        ("activation_v1_inner_path", "activation_v1_inner_sha256"),
        ("activation_v1_outer_path", "activation_v1_outer_sha256"),
        ("activation_v1_rework_path", "activation_v1_rework_sha256"),
        ("successor_v2_outer_path", "successor_v2_outer_sha256"),
        ("successor_v2_review_pass_path", "successor_v2_review_pass_sha256"),
        ("v7_outer_path", "v7_outer_sha256"),
        ("v7_review_pass_path", "v7_review_pass_sha256"),
        ("user_authorization_path", "user_authorization_sha256"),
    ):
        _require_hash(str(predecessor[path_key]), str(predecessor[hash_key]))
    rework = _json(ROOT / str(predecessor["activation_v1_rework_path"]))
    if (
        rework.get("verdict") != "REWORK"
        or rework.get("reviewed_artifacts", {}).get(V1_OUTER_REL) != V1_OUTER_SHA256
        or rework.get("effect", {}).get("no_execution_authority") is not True
        or rework.get("effect", {}).get("activation_v2_creation_authorized") is not True
    ):
        raise BootstrapRejected("activation-v1 REWORK receipt scope drifted")
    _verify_contract(config)
    transport = config["transport_contract"]
    _require_hash(str(transport["runner_path"]), str(transport["runner_sha256"]))
    inner = _json(ROOT / INNER_REL)
    files = inner.get("files")
    expected_members = {CONFIG_REL, REWORK_REL, RUNNER_REL, SELF_REL, TEST_REL}
    if (
        inner.get("schema")
        != "rq2_public_grid_two_block_pilot_activation_transport_bundle_v2"
        or not isinstance(files, dict)
        or set(files) != expected_members
    ):
        raise BootstrapRejected("activation-v2 inner manifest drifted")
    for member, digest in files.items():
        if not isinstance(digest, str) or len(digest) != 64:
            raise BootstrapRejected("activation-v2 inner hash malformed")
        _require_hash(str(member), digest)
    inner_hash = _sha256(ROOT / INNER_REL)
    outer = _json(ROOT / OUTER_REL)
    if outer != {
        "schema": "rq2_public_grid_two_block_pilot_activation_transport_outer_v2",
        "files": {INNER_REL: inner_hash},
    }:
        raise BootstrapRejected("activation-v2 outer manifest drifted")
    formal = config.get("formal_invariants")
    if not isinstance(formal, dict):
        raise BootstrapRejected("formal invariant contract malformed")
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
        "schema": "rq2_public_grid_two_block_pilot_activation_transport_validation_v2",
        "validation_passed": True,
        "status": "READY_FOR_INDEPENDENT_REVIEW",
        "execution_ready": False,
        "activation_review_present": False,
        "execution_wrapper_present": False,
        "dispatch_authorization_present": False,
        "production_dispatch_permitted": False,
        "scientific_project_modules_imported": 0,
        "sealed_predecessor_bootstrap_helpers_loaded": 1,
        "production_workers_started": 0,
        "scientific_loader_calls": 0,
        "solver_calls": 0,
        "result_files_written": 0,
        "formal_writes": 0,
        "formal_execution_ready": False,
        "claim": False,
        "security_certified": False,
    }


def _require_execution_authority(config: Mapping[str, Any]) -> None:
    review = config["future_activation_review"]
    wrapper = config["future_execution_wrapper"]
    if (
        review["receipt_path"] is None
        or review["receipt_sha256"] is None
        or review["reviewed_activation_outer_sha256"] is None
        or wrapper["wrapper_path"] is None
        or wrapper["wrapper_sha256"] is None
        or wrapper["independent_review_receipt_path"] is None
        or wrapper["dispatch_authorization_receipt_path"] is None
        or wrapper["human_dispatch_review_passed"] is not True
        or wrapper["execution_ready"] is not True
    ):
        raise BootstrapRejected("activation-v2 execution wrapper/dispatch authority is absent")
    raise BootstrapRejected("activation-v2 candidate has no execution implementation")


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
    _require_execution_authority(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
