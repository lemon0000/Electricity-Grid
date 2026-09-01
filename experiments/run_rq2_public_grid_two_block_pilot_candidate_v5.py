"""Closed v5 post-commit remediation for the RQ2 two-block pilot.

All scientific, transport, ledger, and pre-commit publication behavior is
delegated to the sealed v4 publisher.  V5 interposes only the success-seal I/O
and applies the repair-010 exact-commit reconciliation rule.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import inspect
import json
import os
import secrets
import shutil
import stat
import threading
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
V4_RUNNER = ROOT / "experiments/run_rq2_public_grid_two_block_pilot_candidate_v4.py"
V4_RUNNER_SHA256 = "3b6e55605f56cee1e871d72b15ddfec0963ce727ec863a08f4cbac441d7541e9"


def _raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _raw_sha256(V4_RUNNER) != V4_RUNNER_SHA256:
    raise ImportError("candidate v4 runner authority drifted before v5 import")

from experiments import (
    run_rq2_public_grid_two_block_pilot_candidate_v4 as predecessor,
)

recovery = predecessor.recovery
MODULE = "experiments.run_rq2_public_grid_two_block_pilot_candidate_v5"
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v5.yaml"
ESCALATION = (
    ROOT / "configs/rq2_public_grid_two_block_pilot_pre_run_review_escalation_v4.yaml"
)
BUNDLE = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v5.SHA256SUMS.json"
OUTER = (
    ROOT
    / "configs/rq2_public_grid_two_block_pilot_candidate_v5.OUTER.SHA256SUMS.json"
)
V4_INNER = predecessor.BUNDLE
V4_OUTER = predecessor.OUTER
V4_CONFIG = predecessor.CONFIG
BLOCKS = list(predecessor.BLOCKS)
AcceptedEvidence = predecessor.AcceptedEvidence
ControllerLedger = predecessor.ControllerLedger

CONFIG_SCHEMA = "rq2_public_grid_two_block_pilot_candidate_v5"
SUCCESS_PAYLOAD_SCHEMA = "rq2_public_grid_two_block_pilot_success_commit_v5"
SUCCESS_MANIFEST_SCHEMA = "rq2_public_grid_two_block_pilot_success_manifest_v5"
OUTCOME_SCHEMA = "rq2_public_grid_two_block_pilot_publication_outcome_v5"

V4_INNER_SHA256 = "1f03580ef26467c069206a1144e8f6f575f03cb44565c7c82fe82360f128dfdb"
V4_OUTER_SHA256 = "a4fa236bec8e6009bee75772e012fcccd09372068287674725c4d5a4fe8afd7b"
ESCALATION_SHA256 = "9288bc637f7ad9d7f4876e8dce2846597e56f288324b825d0cb9330dc007bcc9"
V4_PUBLISH_SOURCE_SHA256 = (
    "e014b73c608e2bce7ee59a486a718ec54149b66c7f9308b424b907155ae3d791"
)
REPAIR_010_HASHES = {
    ROOT
    / "experiments/run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_010_formal.py": (
        "0195d5dfebf59fdbb740891223beea6bb3aaf7c065de4e344274d58357a40204"
    ),
    ROOT / "tests/test_rts_gmlc_v4_repair_010_recovery_import.py": (
        "c9465f104172dbc9d6fccda9a9066588b05d4e13d6e413f455f64c6a55c49a2d"
    ),
    ROOT / "tests/test_rts_gmlc_v4_repair_010_startup_calibration.py": (
        "699538e12497c133c13285ae7353e7a1b9ec13f550c969391153ba063bada515"
    ),
}
V5_BUNDLE_INVENTORY = {
    "configs/rq2_public_grid_two_block_pilot_candidate_v5.yaml",
    "configs/rq2_public_grid_two_block_pilot_pre_run_review_escalation_v4.yaml",
    "experiments/run_rq2_public_grid_two_block_pilot_candidate_v5.py",
    "experiments/validate_rq2_public_grid_two_block_pilot_candidate_v5.py",
    "tests/test_rq2_public_grid_two_block_pilot_candidate_v5.py",
}
_PUBLICATION_LOCK = threading.Lock()


def _sha256(path: Path) -> str:
    return recovery._sha256(path)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_sha256(payload: object) -> str:
    return recovery._canonical_sha256(payload)


def _load_json(path: Path, label: str) -> Any:
    return recovery._load_json_strict(path, label)


def _load_yaml(path: Path, label: str) -> dict[str, Any]:
    return recovery._load_yaml_mapping(path, label)


def _strict_path(path: Path, *, must_exist: bool, label: str) -> Path:
    return predecessor._strict_path(path, must_exist=must_exist, label=label)


def _verify_file(path: Path, expected: str, label: str) -> None:
    predecessor._verify_file(path, expected, label)


def _verify_predecessor_authority() -> dict[str, object]:
    inherited = predecessor._verify_predecessor_authority()
    chain = predecessor._inspect_v4_chain()
    if (
        chain["inner_sha256"] != V4_INNER_SHA256
        or chain["outer_sha256"] != V4_OUTER_SHA256
    ):
        raise ValueError("candidate v4 sealed chain drifted")
    _verify_file(ESCALATION, ESCALATION_SHA256, "candidate v4 ESCALATE")
    escalation = _load_yaml(ESCALATION, "candidate v4 ESCALATE")
    if (
        escalation.get("verdict") != "ESCALATE"
        or escalation.get("effect", {}).get("no_execution_authority") is not True
    ):
        raise ValueError("candidate v4 ESCALATE semantics drifted")
    source_sha = _sha256_bytes(
        inspect.getsource(predecessor._publish_result).encode("utf-8")
    )
    if source_sha != V4_PUBLISH_SOURCE_SHA256:
        raise ValueError("candidate v4 precommit publisher source drifted")
    for path, expected in REPAIR_010_HASHES.items():
        _verify_file(path, expected, f"repair-010 authority {path.name}")
    return {"inherited": inherited, "v4": chain}


def _inspect_v5_chain() -> dict[str, object]:
    bundle_path = _strict_path(BUNDLE, must_exist=True, label="v5 inner")
    outer_path = _strict_path(OUTER, must_exist=True, label="v5 outer")
    bundle = recovery._mapping(_load_json(bundle_path, "v5 inner"), "v5 inner")
    if bundle.get("schema") != "rq2_public_grid_two_block_pilot_candidate_bundle_v5":
        raise ValueError("v5 inner schema drifted")
    files = recovery._mapping(bundle.get("files"), "v5 files")
    if set(files) != V5_BUNDLE_INVENTORY:
        raise ValueError("v5 inner exact inventory drifted")
    for relative, expected in files.items():
        if not recovery._is_sha256(expected):
            raise ValueError("v5 member hash malformed")
        _verify_file(ROOT / str(relative), str(expected), f"v5 member {relative}")
    inner_sha = _sha256(bundle_path)
    outer = recovery._mapping(_load_json(outer_path, "v5 outer"), "v5 outer")
    if outer != {
        "schema": "rq2_public_grid_two_block_pilot_candidate_outer_v5",
        "files": {BUNDLE.relative_to(ROOT).as_posix(): inner_sha},
    }:
        raise ValueError("v5 outer structural authority drifted")
    return {
        "files": {str(key): str(value) for key, value in files.items()},
        "inner_sha256": inner_sha,
        "outer_sha256": _sha256(outer_path),
    }


def _verify_v5_execution_chain(expected_outer_sha256: str | None) -> dict[str, object]:
    if expected_outer_sha256 is None or not recovery._is_sha256(expected_outer_sha256):
        raise ValueError("v5 external trust root is absent")
    chain = _inspect_v5_chain()
    if chain["outer_sha256"] != expected_outer_sha256:
        raise ValueError("v5 external trust root does not match reviewed outer")
    return chain


def _candidate_authority() -> dict[str, object]:
    _verify_predecessor_authority()
    chain = _inspect_v5_chain()
    return {
        "candidate_v4_inner_sha256": V4_INNER_SHA256,
        "candidate_v4_outer_sha256": V4_OUTER_SHA256,
        "candidate_v4_escalation_sha256": ESCALATION_SHA256,
        "candidate_v5_inner_sha256": chain["inner_sha256"],
        "candidate_v5_outer_sha256": chain["outer_sha256"],
        "repair_010_implementation_sha256": next(
            value
            for path, value in REPAIR_010_HASHES.items()
            if path.name.endswith("repair_010_formal.py")
        ),
        "external_reviewed_outer_sha256": None,
    }


def _load_config() -> dict[str, Any]:
    config = _load_yaml(CONFIG, "candidate v5 config")
    if (
        config.get("schema") != CONFIG_SCHEMA
        or config.get("version") != 5
        or config.get("status")
        != "postcommit_remediation_candidate_v5_execution_closed"
    ):
        raise ValueError("candidate v5 config identity drifted")
    return config


def _publication_config() -> dict[str, Any]:
    config = predecessor._load_config()
    if _sha256(V4_CONFIG) != "d71069e242ba90f6ce8c7af8a77fd470f4e45c794c849f04786faf763baa0fe1":
        raise ValueError("candidate v4 publication config drifted")
    return config


def _require_execution_authority() -> dict[str, Any]:
    _verify_predecessor_authority()
    config = _load_config()
    gates = recovery._mapping(config.get("gates"), "candidate v5 gates")
    trust = recovery._mapping(
        config.get("external_execution_trust_root"), "v5 external trust root"
    )
    if (
        gates.get("independent_pre_run_review_passed") is not True
        or gates.get("execution_successor_present") is not True
        or gates.get("two_block_pilot_execution_ready") is not True
        or trust.get("reviewed_outer_sha256") is None
    ):
        raise RuntimeError("candidate v5 execution authority is closed")
    _verify_v5_execution_chain(str(trust["reviewed_outer_sha256"]))
    raise RuntimeError("candidate v5 is permanently closed; an execution successor is required")


def _pilot_roots(config: Mapping[str, Any]) -> dict[str, Path]:
    paths = recovery._mapping(config.get("paths"), "v5 paths")
    roots = {
        "result": _strict_path(
            ROOT / str(paths["result_directory"]), must_exist=False, label="v5 result"
        ),
        "success_commit": _strict_path(
            ROOT / str(paths["success_commit_directory"]),
            must_exist=False,
            label="v5 success commit",
        ),
        "forbidden_terminal": _strict_path(
            ROOT / str(paths["forbidden_terminal_directory"]),
            must_exist=False,
            label="v5 forbidden terminal",
        ),
        "worker": _strict_path(
            ROOT / str(paths["worker_staging_directory"]),
            must_exist=False,
            label="v5 worker",
        ),
        "log": _strict_path(
            ROOT / str(paths["attempt_log_directory"]),
            must_exist=False,
            label="v5 log",
        ),
    }
    if len(set(roots.values())) != len(roots):
        raise ValueError("v5 roots overlap")
    return roots


def _formal_snapshot() -> dict[str, object]:
    return predecessor._formal_snapshot(_publication_config())


def _exact_json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


@dataclasses.dataclass(frozen=True)
class SuccessCommitExpectation:
    payload: Mapping[str, object]
    payload_bytes: bytes
    payload_sha256: str
    manifest: Mapping[str, object]
    manifest_bytes: bytes
    manifest_sha256: str


class SuccessCommitIndeterminateError(RuntimeError):
    """A success path exists but exact committed truth cannot be proven."""

    def __init__(self, message: str, *, outcome: Mapping[str, object]) -> None:
        self.outcome = dict(outcome)
        self.classification = "commit_indeterminate"
        self.resume_allowed = False
        self.is_infeasibility_evidence = False
        super().__init__(message)


def _expected_summary(ledger: ControllerLedger) -> dict[str, object]:
    return {
        "schema": "rq2_public_grid_two_block_pilot_result_v4",
        "status": "complete_nonformal_pilot",
        "blocks": list(BLOCKS),
        "ledger_digest": ledger.digest,
        "all_blocks_resolved": True,
        "named_outage_comparison_passed": True,
        "published": False,
        "parent_solver_calls": 0,
        "formal_execution_ready": False,
        "claim": False,
        "security_certified": False,
    }


def _validate_committed_result(
    target: Path,
    *,
    config: Mapping[str, Any],
    controller: Mapping[str, Any],
    ledger: ControllerLedger,
) -> dict[str, object]:
    target = _strict_path(target, must_exist=True, label="committed result")
    if not target.is_dir():
        raise ValueError("committed result is not a directory")
    if config != _publication_config():
        raise ValueError("publication config is not exact sealed v4 config")
    if controller != predecessor._build_controller_receipt(config, ledger):
        raise ValueError("committed controller/ledger authority drifted")
    manifest = recovery._mapping(
        _load_json(target / "SHA256SUMS.json", "committed result manifest"),
        "committed result manifest",
    )
    if manifest != predecessor._typed_tree(target):
        raise ValueError("committed result typed tree drifted")
    expected_directories, expected_files = predecessor._expected_result_tree()
    if (
        set(manifest["directories"]) != expected_directories
        or set(recovery._mapping(manifest["files"], "committed files"))
        != expected_files
    ):
        raise ValueError("committed result inventory drifted")
    for evidence in ledger.records:
        destination = target / "workers" / evidence.block_id
        predecessor._revalidate_memory_evidence(
            evidence,
            payload_path=destination / "payload.json",
            receipt_path=destination / "attempt_receipt.json",
        )
        validation = recovery._mapping(
            _load_json(destination / "validation_receipt.json", "validation receipt"),
            "validation receipt",
        )
        if validation != predecessor._validation_receipt(evidence):
            raise ValueError("committed validation receipt drifted")
    observed_controller = recovery._mapping(
        _load_json(target / "controller_receipt.json", "controller receipt"),
        "controller receipt",
    )
    observed_summary = recovery._mapping(
        _load_json(target / "summary.json", "result summary"), "result summary"
    )
    observed_comparison = recovery._mapping(
        _load_json(target / "comparison.json", "named-outage comparison"),
        "named-outage comparison",
    )
    first_payload = recovery._mapping(
        _load_json(target / "workers" / BLOCKS[0] / "payload.json", "0008 result"),
        "0008 result",
    )
    scientific = recovery._mapping(
        first_payload.get("scientific_payload"), "0008 scientific payload"
    )
    expected_comparison = predecessor.predecessor.compare_named_outage_0008(
        scientific, predecessor.predecessor._extract_gurobi_payload()
    )
    if (
        observed_controller != dict(controller)
        or observed_summary != _expected_summary(ledger)
        or observed_comparison != expected_comparison
        or observed_comparison.get("comparison_passed") is not True
        or controller.get("formal_snapshot_before") != predecessor._formal_snapshot(config)
    ):
        raise ValueError("committed result scientific/controller binding drifted")
    return {
        "result_manifest_sha256": _sha256(target / "SHA256SUMS.json"),
        "result_summary_sha256": _sha256(target / "summary.json"),
        "controller_receipt_sha256": _sha256(target / "controller_receipt.json"),
    }


def _build_success_expectation(
    target: Path,
    *,
    config: Mapping[str, Any],
    controller: Mapping[str, Any],
    ledger: ControllerLedger,
    predecessor_v4_seal: Mapping[str, Any],
) -> SuccessCommitExpectation:
    bindings = _validate_committed_result(
        target, config=config, controller=controller, ledger=ledger
    )
    expected_v4_seal = {
        "schema": predecessor.SUCCESS_SEAL_SCHEMA,
        "result_directory": str(target),
        "result_manifest_sha256": bindings["result_manifest_sha256"],
        "ledger_digest": ledger.digest,
        "published": True,
        "after_atomic_rename_readback_passed": True,
        "post_result_review_passed": False,
        "formal_execution_ready": False,
        "claim": False,
        "security_certified": False,
    }
    if dict(predecessor_v4_seal) != expected_v4_seal:
        raise ValueError("predecessor v4 seal payload drifted before v5 commit")
    payload: dict[str, object] = {
        "schema": SUCCESS_PAYLOAD_SCHEMA,
        "commit_protocol": "repair_010_exact_success_directory_v1",
        "authority": _candidate_authority(),
        "predecessor_v4_seal": expected_v4_seal,
        **bindings,
        "ledger_digest": ledger.digest,
        "accepted_evidence_digests": [
            evidence.accepted_evidence_digest for evidence in ledger.records
        ],
        "published": True,
        "unique_irreversible_commit_point": True,
        "terminal_state_created": False,
        "resume_allowed": False,
        "mathematical_infeasibility_inferred": False,
        "post_result_review_passed": False,
        "formal_execution_ready": False,
        "claim": False,
        "security_certified": False,
    }
    payload_bytes = _exact_json_bytes(payload)
    manifest: dict[str, object] = {
        "schema": SUCCESS_MANIFEST_SCHEMA,
        "files": {"success.json": _sha256_bytes(payload_bytes)},
    }
    manifest_bytes = _exact_json_bytes(manifest)
    return SuccessCommitExpectation(
        payload=payload,
        payload_bytes=payload_bytes,
        payload_sha256=_sha256_bytes(payload_bytes),
        manifest=manifest,
        manifest_bytes=manifest_bytes,
        manifest_sha256=_sha256_bytes(manifest_bytes),
    )


def _write_exact(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _read_success_member(path: Path) -> bytes:
    return path.read_bytes()


def _verify_success_directory(
    success_directory: Path, expectation: SuccessCommitExpectation
) -> dict[str, Any]:
    success_directory = _strict_path(
        success_directory, must_exist=True, label="v5 success commit"
    )
    metadata = os.lstat(success_directory)
    if not stat.S_ISDIR(metadata.st_mode):
        raise ValueError("v5 success commit is not an ordinary directory")
    entries = {entry.name: entry for entry in os.scandir(success_directory)}
    if set(entries) != {"success.json", "SHA256SUMS.json"}:
        raise ValueError("v5 success commit exact inventory drifted")
    for name, entry in entries.items():
        path = Path(entry.path)
        if predecessor._is_link_or_reparse(path) or not entry.is_file(
            follow_symlinks=False
        ):
            raise ValueError(f"v5 success commit member is not ordinary: {name}")
    payload_bytes = _read_success_member(success_directory / "success.json")
    manifest_bytes = _read_success_member(success_directory / "SHA256SUMS.json")
    if (
        payload_bytes != expectation.payload_bytes
        or manifest_bytes != expectation.manifest_bytes
        or _sha256_bytes(payload_bytes) != expectation.payload_sha256
        or _sha256_bytes(manifest_bytes) != expectation.manifest_sha256
        or _load_json(success_directory / "success.json", "success payload")
        != dict(expectation.payload)
        or _load_json(success_directory / "SHA256SUMS.json", "success manifest")
        != dict(expectation.manifest)
    ):
        raise ValueError("v5 success commit exact bytes/hash/payload drifted")
    return dict(expectation.payload)


def _publish_success_directory(
    success_directory: Path, expectation: SuccessCommitExpectation
) -> None:
    success_directory = _strict_path(
        success_directory, must_exist=False, label="v5 success commit"
    )
    if success_directory.exists():
        raise FileExistsError("v5 success commit already exists")
    success_directory.parent.mkdir(parents=True, exist_ok=True)
    staging = success_directory.parent / (
        f".{success_directory.name}.staging.{secrets.token_hex(16)}"
    )
    if staging.exists():
        raise FileExistsError("v5 success staging already exists")
    staging.mkdir(exist_ok=False)
    renamed = False
    try:
        _write_exact(staging / "success.json", expectation.payload_bytes)
        _write_exact(staging / "SHA256SUMS.json", expectation.manifest_bytes)
        _verify_success_directory(staging, expectation)
        if success_directory.exists():
            raise FileExistsError("v5 success commit appeared before rename")
        staging.rename(success_directory)
        renamed = True
        _verify_success_directory(success_directory, expectation)
    finally:
        if not renamed:
            shutil.rmtree(staging, ignore_errors=True)


def _outcome(
    classification: str,
    *,
    target: Path,
    success_directory: Path,
    terminal_directory: Path,
    original_error: BaseException | None,
) -> dict[str, object]:
    committed = classification == "committed_success"
    return {
        "schema": OUTCOME_SCHEMA,
        "classification": classification,
        "published": committed,
        "success_commit_accepted": committed,
        "target_exists": target.exists(),
        "success_commit_exists": success_directory.exists(),
        "terminal_state_exists": terminal_directory.exists(),
        "success_and_terminal_dual_state": (
            success_directory.exists() and terminal_directory.exists()
        ),
        "terminal_state_created": False,
        "resume_allowed": False,
        "mathematical_infeasibility_inferred": False,
        "original_error_type": (
            None if original_error is None else type(original_error).__name__
        ),
        "formal_execution_ready": False,
        "claim": False,
        "security_certified": False,
    }


def _reconcile_publication(
    *,
    target: Path,
    success_directory: Path,
    terminal_directory: Path,
    config: Mapping[str, Any],
    controller: Mapping[str, Any],
    ledger: ControllerLedger,
    expectation: SuccessCommitExpectation | None,
    original_error: BaseException | None,
) -> dict[str, object]:
    if terminal_directory.exists():
        outcome = _outcome(
            "commit_indeterminate",
            target=target,
            success_directory=success_directory,
            terminal_directory=terminal_directory,
            original_error=original_error,
        )
        raise SuccessCommitIndeterminateError(
            "v5 forbidden terminal state exists; success/terminal classification is indeterminate",
            outcome=outcome,
        ) from original_error
    if not success_directory.exists():
        return _outcome(
            "honest_incomplete",
            target=target,
            success_directory=success_directory,
            terminal_directory=terminal_directory,
            original_error=original_error,
        )
    try:
        if expectation is None:
            bindings = _validate_committed_result(
                target, config=config, controller=controller, ledger=ledger
            )
            v4_seal = {
                "schema": predecessor.SUCCESS_SEAL_SCHEMA,
                "result_directory": str(target),
                "result_manifest_sha256": bindings["result_manifest_sha256"],
                "ledger_digest": ledger.digest,
                "published": True,
                "after_atomic_rename_readback_passed": True,
                "post_result_review_passed": False,
                "formal_execution_ready": False,
                "claim": False,
                "security_certified": False,
            }
            expectation = _build_success_expectation(
                target,
                config=config,
                controller=controller,
                ledger=ledger,
                predecessor_v4_seal=v4_seal,
            )
        _verify_success_directory(success_directory, expectation)
        _validate_committed_result(
            target, config=config, controller=controller, ledger=ledger
        )
    except BaseException as validation_error:
        outcome = _outcome(
            "commit_indeterminate",
            target=target,
            success_directory=success_directory,
            terminal_directory=terminal_directory,
            original_error=original_error,
        )
        raise SuccessCommitIndeterminateError(
            "v5 success path exists but exact committed bytes/bindings cannot be proven",
            outcome=outcome,
        ) from validation_error
    return _outcome(
        "committed_success",
        target=target,
        success_directory=success_directory,
        terminal_directory=terminal_directory,
        original_error=original_error,
    )


def _publish_result(
    staging: Path,
    target: Path,
    success_directory: Path,
    terminal_directory: Path,
    *,
    config: Mapping[str, Any],
    controller: Mapping[str, Any],
    ledger: ControllerLedger,
    pre_rename_test_hook: Callable[[Path], None] | None = None,
    post_commit_test_hook: (
        Callable[[Path, SuccessCommitExpectation], None] | None
    ) = None,
) -> dict[str, object]:
    """Delegate exact v4 precommit logic and reconcile the unique v5 commit."""

    _verify_predecessor_authority()
    _inspect_v5_chain()
    if config != _publication_config():
        raise ValueError("v5 publisher requires the exact sealed v4 precommit config")
    success_directory = _strict_path(
        success_directory, must_exist=False, label="v5 success commit"
    )
    terminal_directory = _strict_path(
        terminal_directory, must_exist=False, label="v5 forbidden terminal"
    )
    if terminal_directory.exists():
        return _reconcile_publication(
            target=target,
            success_directory=success_directory,
            terminal_directory=terminal_directory,
            config=config,
            controller=controller,
            ledger=ledger,
            expectation=None,
            original_error=None,
        )
    expectation: SuccessCommitExpectation | None = None
    original_error: BaseException | None = None
    real_atomic_json = predecessor.recovery._atomic_json
    real_load_json = predecessor._load_json

    def atomic_adapter(path: Path, payload: object) -> None:
        nonlocal expectation
        if Path(path) != success_directory:
            real_atomic_json(path, payload)
            return
        if expectation is not None:
            raise RuntimeError("v5 success commit was attempted more than once")
        v4_seal = recovery._mapping(payload, "predecessor v4 success seal")
        expectation = _build_success_expectation(
            target,
            config=config,
            controller=controller,
            ledger=ledger,
            predecessor_v4_seal=v4_seal,
        )
        _publish_success_directory(success_directory, expectation)
        if post_commit_test_hook is not None:
            post_commit_test_hook(success_directory, expectation)

    def load_adapter(path: Path, label: str) -> Any:
        if Path(path) != success_directory:
            return real_load_json(path, label)
        if expectation is None:
            raise ValueError("v5 success expectation is missing")
        success = _verify_success_directory(success_directory, expectation)
        return recovery._mapping(
            success.get("predecessor_v4_seal"), "predecessor v4 success seal"
        )

    with _PUBLICATION_LOCK:
        predecessor.recovery._atomic_json = atomic_adapter
        predecessor._load_json = load_adapter
        try:
            predecessor._publish_result(
                staging,
                target,
                success_directory,
                config=config,
                controller=controller,
                ledger=ledger,
                pre_rename_test_hook=pre_rename_test_hook,
            )
        except BaseException as error:  # noqa: BLE001 - reconcile exact commit
            original_error = error
        finally:
            predecessor.recovery._atomic_json = real_atomic_json
            predecessor._load_json = real_load_json
    return _reconcile_publication(
        target=target,
        success_directory=success_directory,
        terminal_directory=terminal_directory,
        config=config,
        controller=controller,
        ledger=ledger,
        expectation=expectation,
        original_error=original_error,
    )


def load_verified_success_commit(
    *,
    target: Path,
    success_directory: Path,
    terminal_directory: Path,
    config: Mapping[str, Any],
    controller: Mapping[str, Any],
    ledger: ControllerLedger,
) -> dict[str, Any]:
    """Recovery accepts only an exact committed seal and never file appearance."""

    outcome = _reconcile_publication(
        target=target,
        success_directory=success_directory,
        terminal_directory=terminal_directory,
        config=config,
        controller=controller,
        ledger=ledger,
        expectation=None,
        original_error=None,
    )
    if outcome["classification"] != "committed_success":
        raise ValueError("v5 exact success commit is missing; recovery forbidden")
    bindings = _validate_committed_result(
        target, config=config, controller=controller, ledger=ledger
    )
    v4_seal = {
        "schema": predecessor.SUCCESS_SEAL_SCHEMA,
        "result_directory": str(target),
        "result_manifest_sha256": bindings["result_manifest_sha256"],
        "ledger_digest": ledger.digest,
        "published": True,
        "after_atomic_rename_readback_passed": True,
        "post_result_review_passed": False,
        "formal_execution_ready": False,
        "claim": False,
        "security_certified": False,
    }
    expectation = _build_success_expectation(
        target,
        config=config,
        controller=controller,
        ledger=ledger,
        predecessor_v4_seal=v4_seal,
    )
    return _verify_success_directory(success_directory, expectation)


def run(*, validate_only: bool = False) -> dict[str, object]:
    if validate_only:
        from experiments.validate_rq2_public_grid_two_block_pilot_candidate_v5 import (
            validate,
        )

        return validate()
    _require_execution_authority()
    raise RuntimeError("closed v5 candidate cannot run; execution successor required")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    print(json.dumps(run(validate_only=bool(args.validate_only)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
