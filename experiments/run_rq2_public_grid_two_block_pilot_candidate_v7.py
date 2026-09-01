"""Closed v7 immutable publication-presence snapshot candidate.

The sealed v4 publisher remains the scientific/pre-commit implementation. V7
changes only publication presence observation, reconciliation, recovery, and
outcome auditing. It is permanently execution-closed pending independent review.
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
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
V6_RUNNER = ROOT / "experiments/run_rq2_public_grid_two_block_pilot_candidate_v6.py"
V6_RUNNER_SHA256 = "21c315f046b3bf62f1c8b16eb834e9bf172dfeb8f361fae17a7d2433e49151fa"


def _raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _raw_sha256(V6_RUNNER) != V6_RUNNER_SHA256:
    raise ImportError("candidate v6 runner authority drifted before v7 import")

from experiments import (
    run_rq2_public_grid_two_block_pilot_candidate_v6 as predecessor,
)

v5 = predecessor.predecessor
v4 = predecessor.v4
recovery = predecessor.recovery
MODULE = "experiments.run_rq2_public_grid_two_block_pilot_candidate_v7"
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v7.yaml"
ESCALATION = (
    ROOT / "configs/rq2_public_grid_two_block_pilot_pre_run_review_escalation_v6.yaml"
)
BUNDLE = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v7.SHA256SUMS.json"
OUTER = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v7.OUTER.SHA256SUMS.json"
V6_INNER = predecessor.BUNDLE
V6_OUTER = predecessor.OUTER
BLOCKS = list(predecessor.BLOCKS)
AcceptedEvidence = predecessor.AcceptedEvidence
ControllerLedger = predecessor.ControllerLedger

CONFIG_SCHEMA = "rq2_public_grid_two_block_pilot_candidate_v7"
SUCCESS_PAYLOAD_SCHEMA = "rq2_public_grid_two_block_pilot_success_commit_v7"
SUCCESS_MANIFEST_SCHEMA = "rq2_public_grid_two_block_pilot_success_manifest_v7"
OUTCOME_SCHEMA = "rq2_public_grid_two_block_pilot_publication_outcome_v7"

V6_INNER_SHA256 = "990a9f5bec908a32d41b5d0c7fdecba064cb8e8df6b129295ef2489a82e468a9"
V6_OUTER_SHA256 = "ab9bfb5d89a383a6b68ee8630c9ca14df819bd9f885899e2fd07f76f136dfb20"
ESCALATION_SHA256 = "c26afa1ddf77c98e5048609bc6cf17e30231e6417c8208069acce42a803754bd"
V4_PUBLISH_SOURCE_SHA256 = predecessor.V4_PUBLISH_SOURCE_SHA256
V6_SOURCE_HASHES = {
    "_publish_result": "b74b019f6914cb5f14e1496f61602f482008248d77188c13b73e6cc7dd1d47fa",
    "_reconcile_publication": "95d69a0b6ee461c29f4ad8f8a48e4ead1cd978a8450087da4b12ffcdfdf51275",
    "_outcome": "9f8741bf889f226729141c7d402919929f16501445f112b1505321ba5ec7d3d9",
    "_verify_success_directory": "3a010ca3eddeb07d2e7e7e35a37f86bbaf553fd6ed7eaf26b6e6f869fee54802",
    "_validate_committed_result": "8f517cd776503bcb92bfebadcc3c904b6e8f4d4a86a5cfd632211d96f3f02faa",
    "_probe_path": "28d7425b0d6e037e5c04728037c3831589bad907774f3fb98157e3e615c17c2c",
}
V7_BUNDLE_INVENTORY = {
    "configs/rq2_public_grid_two_block_pilot_candidate_v7.yaml",
    "configs/rq2_public_grid_two_block_pilot_pre_run_review_escalation_v6.yaml",
    "experiments/run_rq2_public_grid_two_block_pilot_candidate_v7.py",
    "experiments/validate_rq2_public_grid_two_block_pilot_candidate_v7.py",
    "tests/test_rq2_public_grid_two_block_pilot_candidate_v7.py",
}
_PUBLICATION_LOCK = threading.Lock()


def _sha256(path: Path) -> str:
    return recovery._sha256(path)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load_json(path: Path, label: str) -> Any:
    return recovery._load_json_strict(path, label)


def _load_yaml(path: Path, label: str) -> dict[str, Any]:
    return recovery._load_yaml_mapping(path, label)


def _verify_file(path: Path, expected: str, label: str) -> None:
    predecessor._verify_file(path, expected, label)


def _verify_predecessor_authority() -> dict[str, object]:
    inherited = predecessor._verify_predecessor_authority()
    chain = predecessor._inspect_v6_chain()
    if (
        chain["inner_sha256"] != V6_INNER_SHA256
        or chain["outer_sha256"] != V6_OUTER_SHA256
    ):
        raise ValueError("candidate v6 sealed chain drifted")
    _verify_file(ESCALATION, ESCALATION_SHA256, "candidate v6 ESCALATE")
    review = _load_yaml(ESCALATION, "candidate v6 ESCALATE")
    if (
        review.get("verdict") != "ESCALATE"
        or review.get("effect", {}).get("no_execution_authority") is not True
    ):
        raise ValueError("candidate v6 ESCALATE semantics drifted")
    for name, expected in V6_SOURCE_HASHES.items():
        observed = _sha256_bytes(
            inspect.getsource(getattr(predecessor, name)).encode("utf-8")
        )
        if observed != expected:
            raise ValueError(f"candidate v6 source authority drifted: {name}")
    return {"inherited": inherited, "v6": chain}


def _inspect_v7_chain() -> dict[str, object]:
    bundle_path = v5._strict_path(BUNDLE, must_exist=True, label="v7 inner")
    outer_path = v5._strict_path(OUTER, must_exist=True, label="v7 outer")
    bundle = recovery._mapping(_load_json(bundle_path, "v7 inner"), "v7 inner")
    if bundle.get("schema") != "rq2_public_grid_two_block_pilot_candidate_bundle_v7":
        raise ValueError("v7 inner schema drifted")
    files = recovery._mapping(bundle.get("files"), "v7 files")
    if set(files) != V7_BUNDLE_INVENTORY:
        raise ValueError("v7 inner exact inventory drifted")
    for relative, expected in files.items():
        if not recovery._is_sha256(expected):
            raise ValueError("v7 member hash malformed")
        _verify_file(ROOT / str(relative), str(expected), f"v7 member {relative}")
    inner_sha = _sha256(bundle_path)
    outer = recovery._mapping(_load_json(outer_path, "v7 outer"), "v7 outer")
    if outer != {
        "schema": "rq2_public_grid_two_block_pilot_candidate_outer_v7",
        "files": {BUNDLE.relative_to(ROOT).as_posix(): inner_sha},
    }:
        raise ValueError("v7 outer structural authority drifted")
    return {
        "files": {str(key): str(value) for key, value in files.items()},
        "inner_sha256": inner_sha,
        "outer_sha256": _sha256(outer_path),
    }


def _verify_v7_execution_chain(expected_outer_sha256: str | None) -> dict[str, object]:
    if expected_outer_sha256 is None or not recovery._is_sha256(expected_outer_sha256):
        raise ValueError("v7 external trust root is absent")
    chain = _inspect_v7_chain()
    if chain["outer_sha256"] != expected_outer_sha256:
        raise ValueError("v7 external trust root does not match reviewed outer")
    return chain


def _candidate_authority() -> dict[str, object]:
    _verify_predecessor_authority()
    chain = _inspect_v7_chain()
    return {
        "candidate_v6_inner_sha256": V6_INNER_SHA256,
        "candidate_v6_outer_sha256": V6_OUTER_SHA256,
        "candidate_v6_escalation_sha256": ESCALATION_SHA256,
        "candidate_v7_inner_sha256": chain["inner_sha256"],
        "candidate_v7_outer_sha256": chain["outer_sha256"],
        "candidate_v4_publish_result_source_sha256": V4_PUBLISH_SOURCE_SHA256,
        "candidate_v6_source_sha256": dict(V6_SOURCE_HASHES),
        "external_reviewed_outer_sha256": None,
    }


def _load_config() -> dict[str, Any]:
    config = _load_yaml(CONFIG, "candidate v7 config")
    if (
        config.get("schema") != CONFIG_SCHEMA
        or config.get("version") != 7
        or config.get("status")
        != "publication_presence_snapshot_candidate_v7_execution_closed"
    ):
        raise ValueError("candidate v7 config identity drifted")
    return config


def _publication_config() -> dict[str, Any]:
    return predecessor._publication_config()


def _pilot_roots(config: Mapping[str, Any]) -> dict[str, Path]:
    paths = recovery._mapping(config.get("paths"), "v7 paths")
    roots = {
        "result": ROOT / str(paths["result_directory"]),
        "success_commit": ROOT / str(paths["success_commit_directory"]),
        "forbidden_terminal": ROOT / str(paths["forbidden_terminal_directory"]),
        "worker": ROOT / str(paths["worker_staging_directory"]),
        "log": ROOT / str(paths["attempt_log_directory"]),
    }
    if len(set(roots.values())) != len(roots):
        raise ValueError("v7 roots overlap")
    return roots


def _formal_snapshot() -> dict[str, object]:
    return predecessor._formal_snapshot()


def _require_execution_authority() -> dict[str, Any]:
    _verify_predecessor_authority()
    config = _load_config()
    gates = recovery._mapping(config.get("gates"), "candidate v7 gates")
    trust = recovery._mapping(
        config.get("external_execution_trust_root"), "v7 external trust root"
    )
    if (
        gates.get("independent_pre_run_review_passed") is not True
        or gates.get("execution_successor_present") is not True
        or gates.get("two_block_pilot_execution_ready") is not True
        or trust.get("reviewed_outer_sha256") is None
    ):
        raise RuntimeError("candidate v7 execution authority is closed")
    _verify_v7_execution_chain(str(trust["reviewed_outer_sha256"]))
    raise RuntimeError("candidate v7 is permanently closed; an execution successor is required")


def _exact_json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


@dataclasses.dataclass(frozen=True)
class PathSegmentPresence:
    path: str
    lexists: bool | None
    lstat_performed: bool
    kind: str
    is_leaf: bool
    reparse: bool | None
    mount_alias: bool | None
    error_type: str | None

    def audit(self) -> dict[str, object]:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class FrozenPathPresence:
    label: str
    raw_path: str
    classification: str
    clean_absent: bool
    path_appearance: bool
    leaf_lexists: bool
    first_issue_path: str | None
    chain: tuple[PathSegmentPresence, ...]

    @property
    def ancestors_ordinary(self) -> bool:
        ancestors = tuple(item for item in self.chain if not item.is_leaf)
        return bool(ancestors) and all(
            item.lexists is True
            and item.lstat_performed
            and item.kind == "ordinary_directory"
            and item.reparse is False
            and item.mount_alias is False
            for item in ancestors
        )

    @property
    def eligible_clean_absent(self) -> bool:
        return self.clean_absent and self.ancestors_ordinary

    @property
    def exact_ordinary_directory(self) -> bool:
        return self.classification == "ordinary_directory" and self.ancestors_ordinary

    def audit(self) -> dict[str, object]:
        return {
            "label": self.label,
            "raw_path": self.raw_path,
            "classification": self.classification,
            "clean_absent": self.clean_absent,
            "eligible_clean_absent": self.eligible_clean_absent,
            "path_appearance": self.path_appearance,
            "leaf_lexists": self.leaf_lexists,
            "first_issue_path": self.first_issue_path,
            "ancestors_ordinary": self.ancestors_ordinary,
            "chain": [item.audit() for item in self.chain],
        }


def _freeze_presence(observed: predecessor.PathPresence) -> FrozenPathPresence:
    segments = tuple(
        PathSegmentPresence(
            path=str(item.get("path")),
            lexists=item.get("lexists") if item.get("lexists") is None else bool(item.get("lexists")),
            lstat_performed=bool(item.get("lstat_performed", False)),
            kind=str(item.get("kind")),
            is_leaf=bool(item.get("is_leaf", False)),
            reparse=(None if "reparse" not in item else bool(item.get("reparse"))),
            mount_alias=(
                None if "mount_alias" not in item else bool(item.get("mount_alias"))
            ),
            error_type=(
                None if item.get("error_type") is None else str(item.get("error_type"))
            ),
        )
        for item in observed.chain
    )
    return FrozenPathPresence(
        label=observed.label,
        raw_path=observed.raw_path,
        classification=observed.classification,
        clean_absent=observed.clean_absent,
        path_appearance=observed.path_appearance,
        leaf_lexists=observed.leaf_lexists,
        first_issue_path=observed.first_issue_path,
        chain=segments,
    )


def _probe_one_path(path: Path, *, label: str) -> FrozenPathPresence:
    return _freeze_presence(predecessor._probe_path(Path(path), label=label))


@dataclasses.dataclass(frozen=True)
class PublicationPresenceSnapshot:
    captured_ns: int
    result: FrozenPathPresence
    success: FrozenPathPresence
    terminal: FrozenPathPresence
    snapshot_sha256: str

    def audit(self) -> dict[str, object]:
        return {
            "captured_ns": self.captured_ns,
            "result": self.result.audit(),
            "success": self.success.audit(),
            "terminal": self.terminal.audit(),
            "snapshot_sha256": self.snapshot_sha256,
        }


def _capture_publication_presence_snapshot(
    *, target: Path, success_directory: Path, terminal_directory: Path
) -> PublicationPresenceSnapshot:
    captured_ns = time.time_ns()
    result = _probe_one_path(target, label="v7 result target")
    success = _probe_one_path(success_directory, label="v7 success commit")
    terminal = _probe_one_path(terminal_directory, label="v7 terminal state")
    body = {
        "captured_ns": captured_ns,
        "result": result.audit(),
        "success": success.audit(),
        "terminal": terminal.audit(),
    }
    return PublicationPresenceSnapshot(
        captured_ns=captured_ns,
        result=result,
        success=success,
        terminal=terminal,
        snapshot_sha256=_sha256_bytes(_exact_json_bytes(body)),
    )


def _snapshot_state(snapshot: PublicationPresenceSnapshot) -> str:
    if not snapshot.terminal.eligible_clean_absent:
        return "commit_indeterminate"
    if snapshot.success.eligible_clean_absent:
        if snapshot.result.eligible_clean_absent:
            return "honest_incomplete"
        if snapshot.result.exact_ordinary_directory:
            return "honest_incomplete"
        return "commit_indeterminate"
    if snapshot.success.exact_ordinary_directory:
        if snapshot.result.exact_ordinary_directory:
            return "success_candidate"
        return "commit_indeterminate"
    return "commit_indeterminate"


@dataclasses.dataclass(frozen=True)
class SuccessCommitExpectation:
    payload: Mapping[str, object]
    payload_bytes: bytes
    payload_sha256: str
    manifest: Mapping[str, object]
    manifest_bytes: bytes
    manifest_sha256: str


@dataclasses.dataclass(frozen=True)
class PublicationDecision:
    outcome: Mapping[str, object]
    payload: Mapping[str, Any] | None
    snapshot: PublicationPresenceSnapshot


class SuccessCommitIndeterminateError(RuntimeError):
    """Publication appearance exists but exact committed truth is unprovable."""

    def __init__(self, message: str, *, outcome: Mapping[str, object]) -> None:
        self.outcome = dict(outcome)
        self.classification = "commit_indeterminate"
        self.resume_allowed = False
        self.is_infeasibility_evidence = False
        super().__init__(message)


def _validate_result_contents(
    target: Path,
    *,
    snapshot: PublicationPresenceSnapshot,
    config: Mapping[str, Any],
    controller: Mapping[str, Any],
    ledger: ControllerLedger,
) -> dict[str, object]:
    if snapshot.result.raw_path != str(target) or not snapshot.result.exact_ordinary_directory:
        raise ValueError("v7 result is not the snapshot-bound ordinary directory")
    if config != _publication_config():
        raise ValueError("publication config is not exact sealed v4 config")
    if controller != v4._build_controller_receipt(config, ledger):
        raise ValueError("committed controller/ledger authority drifted")
    manifest = recovery._mapping(
        _load_json(target / "SHA256SUMS.json", "committed result manifest"),
        "committed result manifest",
    )
    if manifest != v4._typed_tree(target):
        raise ValueError("committed result typed tree drifted")
    expected_directories, expected_files = v4._expected_result_tree()
    if (
        set(manifest["directories"]) != expected_directories
        or set(recovery._mapping(manifest["files"], "committed files"))
        != expected_files
    ):
        raise ValueError("committed result inventory drifted")
    for evidence in ledger.records:
        destination = target / "workers" / evidence.block_id
        v4._revalidate_memory_evidence(
            evidence,
            payload_path=destination / "payload.json",
            receipt_path=destination / "attempt_receipt.json",
        )
        validation = recovery._mapping(
            _load_json(destination / "validation_receipt.json", "validation receipt"),
            "validation receipt",
        )
        if validation != v4._validation_receipt(evidence):
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
    expected_comparison = v4.predecessor.compare_named_outage_0008(
        scientific, v4.predecessor._extract_gurobi_payload()
    )
    if (
        observed_controller != dict(controller)
        or observed_summary != v5._expected_summary(ledger)
        or observed_comparison != expected_comparison
        or observed_comparison.get("comparison_passed") is not True
        or controller.get("formal_snapshot_before") != v4._formal_snapshot(config)
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
    snapshot: PublicationPresenceSnapshot,
    config: Mapping[str, Any],
    controller: Mapping[str, Any],
    ledger: ControllerLedger,
    predecessor_v4_seal: Mapping[str, Any],
) -> SuccessCommitExpectation:
    bindings = _validate_result_contents(
        target,
        snapshot=snapshot,
        config=config,
        controller=controller,
        ledger=ledger,
    )
    expected_v4_seal = {
        "schema": v4.SUCCESS_SEAL_SCHEMA,
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
        raise ValueError("predecessor v4 seal payload drifted before v7 commit")
    payload: dict[str, object] = {
        "schema": SUCCESS_PAYLOAD_SCHEMA,
        "commit_protocol": "repair_010_exact_success_directory_single_snapshot_v3",
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


def _read_success_member(path: Path) -> bytes:
    return path.read_bytes()


def _verify_success_contents(
    success_directory: Path,
    expectation: SuccessCommitExpectation,
    *,
    snapshot: PublicationPresenceSnapshot,
) -> dict[str, Any]:
    if (
        snapshot.success.raw_path != str(success_directory)
        or not snapshot.success.exact_ordinary_directory
    ):
        raise ValueError("v7 success is not the snapshot-bound ordinary directory")
    entries = {entry.name: entry for entry in os.scandir(success_directory)}
    if set(entries) != {"success.json", "SHA256SUMS.json"}:
        raise ValueError("v7 success commit exact inventory drifted")
    for name, entry in entries.items():
        path = Path(entry.path)
        if v4._is_link_or_reparse(path) or not entry.is_file(follow_symlinks=False):
            raise ValueError(f"v7 success commit member is not ordinary: {name}")
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
        raise ValueError("v7 success commit exact bytes/hash/payload drifted")
    return dict(expectation.payload)


def _write_exact(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _publish_success_directory(
    success_directory: Path,
    expectation: SuccessCommitExpectation,
    *,
    snapshot: PublicationPresenceSnapshot,
) -> None:
    if (
        snapshot.success.raw_path != str(success_directory)
        or not snapshot.success.eligible_clean_absent
        or not snapshot.result.exact_ordinary_directory
        or not snapshot.terminal.eligible_clean_absent
    ):
        raise ValueError("v7 success publication snapshot is not eligible")
    staging = success_directory.parent / (
        f".{success_directory.name}.staging.{secrets.token_hex(16)}"
    )
    staging_presence = _probe_one_path(staging, label="v7 success staging")
    if not staging_presence.eligible_clean_absent:
        raise FileExistsError("v7 success staging path is not cleanly absent")
    staging.mkdir(exist_ok=False)
    renamed = False
    try:
        _write_exact(staging / "success.json", expectation.payload_bytes)
        _write_exact(staging / "SHA256SUMS.json", expectation.manifest_bytes)
        staged_presence = dataclasses.replace(
            snapshot,
            success=_probe_one_path(staging, label="v7 staged success"),
        )
        _verify_success_contents(staging, expectation, snapshot=staged_presence)
        staging.rename(success_directory)
        renamed = True
    finally:
        if not renamed:
            cleanup = _probe_one_path(staging, label="v7 success staging cleanup")
            if cleanup.exact_ordinary_directory:
                shutil.rmtree(staging)


def _outcome(
    classification: str,
    *,
    snapshot: PublicationPresenceSnapshot,
    original_error: BaseException | None,
) -> dict[str, object]:
    committed = classification == "committed_success"
    return {
        "schema": OUTCOME_SCHEMA,
        "classification": classification,
        "published": committed,
        "success_commit_accepted": committed,
        "target_exists": snapshot.result.path_appearance,
        "success_commit_exists": snapshot.success.path_appearance,
        "terminal_state_exists": snapshot.terminal.path_appearance,
        "target_presence": snapshot.result.audit(),
        "success_commit_presence": snapshot.success.audit(),
        "terminal_state_presence": snapshot.terminal.audit(),
        "publication_presence_snapshot": snapshot.audit(),
        "publication_presence_snapshot_sha256": snapshot.snapshot_sha256,
        "success_and_terminal_dual_state": (
            snapshot.success.path_appearance and snapshot.terminal.path_appearance
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


def _raise_indeterminate(
    message: str,
    *,
    snapshot: PublicationPresenceSnapshot,
    original_error: BaseException | None,
    cause: BaseException | None = None,
) -> None:
    outcome = _outcome(
        "commit_indeterminate", snapshot=snapshot, original_error=original_error
    )
    error = SuccessCommitIndeterminateError(message, outcome=outcome)
    if cause is not None:
        raise error from cause
    if original_error is not None:
        raise error from original_error
    raise error


def _expected_v4_seal(
    target: Path, *, bindings: Mapping[str, object], ledger: ControllerLedger
) -> dict[str, object]:
    return {
        "schema": v4.SUCCESS_SEAL_SCHEMA,
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


def _reconcile_publication(
    *,
    snapshot: PublicationPresenceSnapshot,
    target: Path,
    success_directory: Path,
    terminal_directory: Path,
    config: Mapping[str, Any],
    controller: Mapping[str, Any],
    ledger: ControllerLedger,
    expectation: SuccessCommitExpectation | None,
    original_error: BaseException | None,
) -> PublicationDecision:
    if (
        snapshot.result.raw_path != str(target)
        or snapshot.success.raw_path != str(success_directory)
        or snapshot.terminal.raw_path != str(terminal_directory)
    ):
        _raise_indeterminate(
            "v7 snapshot paths do not match reconciliation paths",
            snapshot=snapshot,
            original_error=original_error,
        )
    state = _snapshot_state(snapshot)
    if state == "honest_incomplete":
        outcome = _outcome(
            "honest_incomplete", snapshot=snapshot, original_error=original_error
        )
        return PublicationDecision(outcome=outcome, payload=None, snapshot=snapshot)
    if state != "success_candidate":
        _raise_indeterminate(
            "v7 publication presence truth table is indeterminate",
            snapshot=snapshot,
            original_error=original_error,
        )
    try:
        bindings = _validate_result_contents(
            target,
            snapshot=snapshot,
            config=config,
            controller=controller,
            ledger=ledger,
        )
        v4_seal = _expected_v4_seal(target, bindings=bindings, ledger=ledger)
        observed_expectation = _build_success_expectation(
            target,
            snapshot=snapshot,
            config=config,
            controller=controller,
            ledger=ledger,
            predecessor_v4_seal=v4_seal,
        )
        if expectation is not None and expectation != observed_expectation:
            raise ValueError("v7 in-memory success expectation drifted")
        _verify_success_contents(
            success_directory, observed_expectation, snapshot=snapshot
        )
    except BaseException as validation_error:  # noqa: BLE001 - fail closed
        _raise_indeterminate(
            "v7 candidate success contents/bindings cannot be proven",
            snapshot=snapshot,
            original_error=original_error,
            cause=validation_error,
        )

    final_snapshot = _capture_publication_presence_snapshot(
        target=target,
        success_directory=success_directory,
        terminal_directory=terminal_directory,
    )
    if _snapshot_state(final_snapshot) != "success_candidate":
        _raise_indeterminate(
            "v7 final publication snapshot changed before acceptance",
            snapshot=final_snapshot,
            original_error=original_error,
        )
    try:
        final_bindings = _validate_result_contents(
            target,
            snapshot=final_snapshot,
            config=config,
            controller=controller,
            ledger=ledger,
        )
        final_expectation = _build_success_expectation(
            target,
            snapshot=final_snapshot,
            config=config,
            controller=controller,
            ledger=ledger,
            predecessor_v4_seal=_expected_v4_seal(
                target, bindings=final_bindings, ledger=ledger
            ),
        )
        if final_expectation != observed_expectation:
            raise ValueError("v7 final expectation drifted")
        payload = _verify_success_contents(
            success_directory, final_expectation, snapshot=final_snapshot
        )
    except BaseException as validation_error:  # noqa: BLE001 - fail closed
        _raise_indeterminate(
            "v7 final exact contents/bindings cannot be proven",
            snapshot=final_snapshot,
            original_error=original_error,
            cause=validation_error,
        )
    outcome = _outcome(
        "committed_success", snapshot=final_snapshot, original_error=original_error
    )
    return PublicationDecision(outcome=outcome, payload=payload, snapshot=final_snapshot)


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
    post_commit_test_hook: Callable[[Path, SuccessCommitExpectation], None] | None = None,
) -> dict[str, object]:
    """Run exact sealed v4 precommit logic, then v7 snapshot reconciliation."""

    _verify_predecessor_authority()
    _inspect_v7_chain()
    if config != _publication_config():
        raise ValueError("v7 publisher requires the exact sealed v4 precommit config")
    preflight = _capture_publication_presence_snapshot(
        target=target,
        success_directory=success_directory,
        terminal_directory=terminal_directory,
    )
    preflight_state = _snapshot_state(preflight)
    if preflight_state == "commit_indeterminate":
        _raise_indeterminate(
            "v7 publication preflight is indeterminate",
            snapshot=preflight,
            original_error=None,
        )
    if preflight.result.exact_ordinary_directory:
        return dict(
            _reconcile_publication(
                snapshot=preflight,
                target=target,
                success_directory=success_directory,
                terminal_directory=terminal_directory,
                config=config,
                controller=controller,
                ledger=ledger,
                expectation=None,
                original_error=None,
            ).outcome
        )

    expectation: SuccessCommitExpectation | None = None
    original_error: BaseException | None = None
    real_atomic_json = v4.recovery._atomic_json
    real_load_json = v4._load_json

    def atomic_adapter(path: Path, payload: object) -> None:
        nonlocal expectation
        if Path(path) != Path(success_directory):
            real_atomic_json(path, payload)
            return
        if expectation is not None:
            raise RuntimeError("v7 success commit was attempted more than once")
        commit_snapshot = _capture_publication_presence_snapshot(
            target=target,
            success_directory=success_directory,
            terminal_directory=terminal_directory,
        )
        if (
            _snapshot_state(commit_snapshot) != "honest_incomplete"
            or not commit_snapshot.result.exact_ordinary_directory
        ):
            raise ValueError("v7 commit-boundary snapshot is not eligible")
        v4_seal = recovery._mapping(payload, "predecessor v4 success seal")
        expectation = _build_success_expectation(
            target,
            snapshot=commit_snapshot,
            config=config,
            controller=controller,
            ledger=ledger,
            predecessor_v4_seal=v4_seal,
        )
        _publish_success_directory(
            success_directory, expectation, snapshot=commit_snapshot
        )
        if post_commit_test_hook is not None:
            post_commit_test_hook(success_directory, expectation)

    def load_adapter(path: Path, label: str) -> Any:
        if Path(path) != Path(success_directory):
            return real_load_json(path, label)
        if expectation is None:
            raise ValueError("v7 success expectation is missing")
        readback_snapshot = _capture_publication_presence_snapshot(
            target=target,
            success_directory=success_directory,
            terminal_directory=terminal_directory,
        )
        if _snapshot_state(readback_snapshot) != "success_candidate":
            raise ValueError("v7 success readback presence is not exact")
        success = _verify_success_contents(
            success_directory, expectation, snapshot=readback_snapshot
        )
        return recovery._mapping(
            success.get("predecessor_v4_seal"), "predecessor v4 success seal"
        )

    with _PUBLICATION_LOCK:
        v4.recovery._atomic_json = atomic_adapter
        v4._load_json = load_adapter
        try:
            v4._publish_result(
                staging,
                target,
                success_directory,
                config=config,
                controller=controller,
                ledger=ledger,
                pre_rename_test_hook=pre_rename_test_hook,
            )
        except BaseException as error:  # noqa: BLE001 - exact reconciliation
            original_error = error
        finally:
            v4.recovery._atomic_json = real_atomic_json
            v4._load_json = real_load_json
    reconciliation_snapshot = _capture_publication_presence_snapshot(
        target=target,
        success_directory=success_directory,
        terminal_directory=terminal_directory,
    )
    decision = _reconcile_publication(
        snapshot=reconciliation_snapshot,
        target=target,
        success_directory=success_directory,
        terminal_directory=terminal_directory,
        config=config,
        controller=controller,
        ledger=ledger,
        expectation=expectation,
        original_error=original_error,
    )
    return dict(decision.outcome)


def load_verified_success_commit(
    *,
    target: Path,
    success_directory: Path,
    terminal_directory: Path,
    config: Mapping[str, Any],
    controller: Mapping[str, Any],
    ledger: ControllerLedger,
) -> dict[str, Any]:
    """Recovery consumes one snapshot and accepts only final-snapshot exact success."""

    snapshot = _capture_publication_presence_snapshot(
        target=target,
        success_directory=success_directory,
        terminal_directory=terminal_directory,
    )
    decision = _reconcile_publication(
        snapshot=snapshot,
        target=target,
        success_directory=success_directory,
        terminal_directory=terminal_directory,
        config=config,
        controller=controller,
        ledger=ledger,
        expectation=None,
        original_error=None,
    )
    if decision.outcome["classification"] != "committed_success" or decision.payload is None:
        raise ValueError("v7 exact success commit is absent; recovery forbidden")
    return dict(decision.payload)


def run(*, validate_only: bool = False) -> dict[str, object]:
    if validate_only:
        from experiments.validate_rq2_public_grid_two_block_pilot_candidate_v7 import (
            validate,
        )

        return validate()
    _require_execution_authority()
    raise RuntimeError("closed v7 candidate cannot run; execution successor required")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    print(json.dumps(run(validate_only=bool(args.validate_only)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
