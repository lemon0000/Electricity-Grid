"""Closed v6 presence-safe recovery gate for the RQ2 two-block pilot.

The sealed v4 publisher remains the scientific and pre-commit implementation.
V6 preserves the v5 exact commit protocol and changes only lexical path presence,
publication reconciliation, recovery acceptance, and outcome auditing.
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
V5_RUNNER = ROOT / "experiments/run_rq2_public_grid_two_block_pilot_candidate_v5.py"
V5_RUNNER_SHA256 = "41cdb2efab3ec96386be00c88f18ee5fa42233ddd3a88c78c81b3cc981bc9d48"


def _raw_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if _raw_sha256(V5_RUNNER) != V5_RUNNER_SHA256:
    raise ImportError("candidate v5 runner authority drifted before v6 import")

from experiments import (
    run_rq2_public_grid_two_block_pilot_candidate_v5 as predecessor,
)

v4 = predecessor.predecessor
recovery = predecessor.recovery
MODULE = "experiments.run_rq2_public_grid_two_block_pilot_candidate_v6"
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v6.yaml"
REWORK = ROOT / "configs/rq2_public_grid_two_block_pilot_pre_run_review_rework_v5.yaml"
BUNDLE = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v6.SHA256SUMS.json"
OUTER = ROOT / "configs/rq2_public_grid_two_block_pilot_candidate_v6.OUTER.SHA256SUMS.json"
V5_INNER = predecessor.BUNDLE
V5_OUTER = predecessor.OUTER
BLOCKS = list(predecessor.BLOCKS)
AcceptedEvidence = predecessor.AcceptedEvidence
ControllerLedger = predecessor.ControllerLedger

CONFIG_SCHEMA = "rq2_public_grid_two_block_pilot_candidate_v6"
SUCCESS_PAYLOAD_SCHEMA = "rq2_public_grid_two_block_pilot_success_commit_v6"
SUCCESS_MANIFEST_SCHEMA = "rq2_public_grid_two_block_pilot_success_manifest_v6"
OUTCOME_SCHEMA = "rq2_public_grid_two_block_pilot_publication_outcome_v6"

V5_INNER_SHA256 = "0d81d1ebe376969bac02d17aec9f4afa4bd077a9c71cdd906ae0538cb0793818"
V5_OUTER_SHA256 = "1be9ddd051da3ae71f7529fadf02745d5e3e58ee84649d0b557e0f14e9e65fac"
REWORK_SHA256 = "aa0e342be0a1938d69aaa1d02994d16fe19e343355490c3c551d2e34026dff7d"
V4_PUBLISH_SOURCE_SHA256 = predecessor.V4_PUBLISH_SOURCE_SHA256
V5_SOURCE_HASHES = {
    "_publish_result": "9e346f15d202aa7ad9a7a0701d6a66d8eac3158c53f4c7c986d85ba0cf2867c5",
    "_reconcile_publication": "51cb63e28d72253a93160c9144b50d81fa68272d0a823a9c4ac97c37675da2cf",
    "_outcome": "4bdf94b4f0e48b0953ad242b86a3ffb989fbf1be3c536f7feb4cc9416d93793f",
    "_verify_success_directory": "5fca80f7ec75c6c422c9687949a3cbaead736818e45d15a388243d58f4c186fb",
    "_validate_committed_result": "b33e6da49f9fa8338353f9dcbd50555356950a7befbc17c639ab0d0c69c4a616",
}
V6_BUNDLE_INVENTORY = {
    "configs/rq2_public_grid_two_block_pilot_candidate_v6.yaml",
    "configs/rq2_public_grid_two_block_pilot_pre_run_review_rework_v5.yaml",
    "experiments/run_rq2_public_grid_two_block_pilot_candidate_v6.py",
    "experiments/validate_rq2_public_grid_two_block_pilot_candidate_v6.py",
    "tests/test_rq2_public_grid_two_block_pilot_candidate_v6.py",
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
    chain = predecessor._inspect_v5_chain()
    if (
        chain["inner_sha256"] != V5_INNER_SHA256
        or chain["outer_sha256"] != V5_OUTER_SHA256
    ):
        raise ValueError("candidate v5 sealed chain drifted")
    _verify_file(REWORK, REWORK_SHA256, "candidate v5 REWORK")
    review = _load_yaml(REWORK, "candidate v5 REWORK")
    if (
        review.get("verdict") != "REWORK"
        or review.get("effect", {}).get("no_execution_authority") is not True
    ):
        raise ValueError("candidate v5 REWORK semantics drifted")
    for name, expected in V5_SOURCE_HASHES.items():
        observed = _sha256_bytes(
            inspect.getsource(getattr(predecessor, name)).encode("utf-8")
        )
        if observed != expected:
            raise ValueError(f"candidate v5 source authority drifted: {name}")
    if V4_PUBLISH_SOURCE_SHA256 != (
        "e014b73c608e2bce7ee59a486a718ec54149b66c7f9308b424b907155ae3d791"
    ):
        raise ValueError("candidate v4 publisher source authority drifted")
    return {"inherited": inherited, "v5": chain}


def _inspect_v6_chain() -> dict[str, object]:
    bundle_path = predecessor._strict_path(BUNDLE, must_exist=True, label="v6 inner")
    outer_path = predecessor._strict_path(OUTER, must_exist=True, label="v6 outer")
    bundle = recovery._mapping(_load_json(bundle_path, "v6 inner"), "v6 inner")
    if bundle.get("schema") != "rq2_public_grid_two_block_pilot_candidate_bundle_v6":
        raise ValueError("v6 inner schema drifted")
    files = recovery._mapping(bundle.get("files"), "v6 files")
    if set(files) != V6_BUNDLE_INVENTORY:
        raise ValueError("v6 inner exact inventory drifted")
    for relative, expected in files.items():
        if not recovery._is_sha256(expected):
            raise ValueError("v6 member hash malformed")
        _verify_file(ROOT / str(relative), str(expected), f"v6 member {relative}")
    inner_sha = _sha256(bundle_path)
    outer = recovery._mapping(_load_json(outer_path, "v6 outer"), "v6 outer")
    if outer != {
        "schema": "rq2_public_grid_two_block_pilot_candidate_outer_v6",
        "files": {BUNDLE.relative_to(ROOT).as_posix(): inner_sha},
    }:
        raise ValueError("v6 outer structural authority drifted")
    return {
        "files": {str(key): str(value) for key, value in files.items()},
        "inner_sha256": inner_sha,
        "outer_sha256": _sha256(outer_path),
    }


def _verify_v6_execution_chain(expected_outer_sha256: str | None) -> dict[str, object]:
    if expected_outer_sha256 is None or not recovery._is_sha256(expected_outer_sha256):
        raise ValueError("v6 external trust root is absent")
    chain = _inspect_v6_chain()
    if chain["outer_sha256"] != expected_outer_sha256:
        raise ValueError("v6 external trust root does not match reviewed outer")
    return chain


def _candidate_authority() -> dict[str, object]:
    _verify_predecessor_authority()
    chain = _inspect_v6_chain()
    return {
        "candidate_v5_inner_sha256": V5_INNER_SHA256,
        "candidate_v5_outer_sha256": V5_OUTER_SHA256,
        "candidate_v5_rework_sha256": REWORK_SHA256,
        "candidate_v6_inner_sha256": chain["inner_sha256"],
        "candidate_v6_outer_sha256": chain["outer_sha256"],
        "candidate_v4_publish_result_source_sha256": V4_PUBLISH_SOURCE_SHA256,
        "candidate_v5_source_sha256": dict(V5_SOURCE_HASHES),
        "external_reviewed_outer_sha256": None,
    }


def _load_config() -> dict[str, Any]:
    config = _load_yaml(CONFIG, "candidate v6 config")
    if (
        config.get("schema") != CONFIG_SCHEMA
        or config.get("version") != 6
        or config.get("status") != "presence_recovery_candidate_v6_execution_closed"
    ):
        raise ValueError("candidate v6 config identity drifted")
    return config


def _publication_config() -> dict[str, Any]:
    return predecessor._publication_config()


def _require_execution_authority() -> dict[str, Any]:
    _verify_predecessor_authority()
    config = _load_config()
    gates = recovery._mapping(config.get("gates"), "candidate v6 gates")
    trust = recovery._mapping(
        config.get("external_execution_trust_root"), "v6 external trust root"
    )
    if (
        gates.get("independent_pre_run_review_passed") is not True
        or gates.get("execution_successor_present") is not True
        or gates.get("two_block_pilot_execution_ready") is not True
        or trust.get("reviewed_outer_sha256") is None
    ):
        raise RuntimeError("candidate v6 execution authority is closed")
    _verify_v6_execution_chain(str(trust["reviewed_outer_sha256"]))
    raise RuntimeError("candidate v6 is permanently closed; an execution successor is required")


def _pilot_roots(config: Mapping[str, Any]) -> dict[str, Path]:
    paths = recovery._mapping(config.get("paths"), "v6 paths")
    roots = {
        "result": ROOT / str(paths["result_directory"]),
        "success_commit": ROOT / str(paths["success_commit_directory"]),
        "forbidden_terminal": ROOT / str(paths["forbidden_terminal_directory"]),
        "worker": ROOT / str(paths["worker_staging_directory"]),
        "log": ROOT / str(paths["attempt_log_directory"]),
    }
    if len(set(roots.values())) != len(roots):
        raise ValueError("v6 roots overlap")
    return roots


def _formal_snapshot() -> dict[str, object]:
    return predecessor._formal_snapshot()


def _exact_json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _lexists_for_presence(path: Path) -> bool:
    return os.path.lexists(path)


def _lstat_for_presence(path: Path) -> os.stat_result:
    return os.lstat(path)


def _ismount_for_presence(path: Path) -> bool:
    return os.path.ismount(path)


def _metadata_is_reparse(metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & flag)


@dataclasses.dataclass(frozen=True)
class PathPresence:
    label: str
    raw_path: str
    classification: str
    clean_absent: bool
    path_appearance: bool
    leaf_lexists: bool
    first_issue_path: str | None
    chain: tuple[Mapping[str, object], ...]

    def audit(self) -> dict[str, object]:
        return {
            "label": self.label,
            "raw_path": self.raw_path,
            "classification": self.classification,
            "clean_absent": self.clean_absent,
            "path_appearance": self.path_appearance,
            "leaf_lexists": self.leaf_lexists,
            "first_issue_path": self.first_issue_path,
            "chain": [dict(item) for item in self.chain],
        }


def _probe_path(path: Path, *, label: str) -> PathPresence:
    """Audit lexical presence without resolve and preserve broken aliases."""

    candidate = Path(path)
    if not candidate.is_absolute() or any(part in {".", ".."} for part in candidate.parts):
        return PathPresence(
            label=label,
            raw_path=str(candidate),
            classification="lexical_alias",
            clean_absent=False,
            path_appearance=True,
            leaf_lexists=False,
            first_issue_path=str(candidate),
            chain=(),
        )
    current = Path(candidate.anchor)
    segments = [current]
    for part in candidate.parts[1:]:
        current = current / part
        segments.append(current)
    chain: list[Mapping[str, object]] = []
    first_issue: tuple[str, str] | None = None
    leaf_lexists = False
    leaf_kind = "clean_absent"
    for index, current in enumerate(segments):
        is_leaf = index == len(segments) - 1
        try:
            lexists = bool(_lexists_for_presence(current))
        except OSError as error:
            lexists = False
            kind = "inaccessible"
            chain.append(
                {
                    "path": str(current),
                    "lexists": None,
                    "lstat_performed": False,
                    "kind": kind,
                    "error_type": type(error).__name__,
                }
            )
            if first_issue is None:
                first_issue = (kind, str(current))
            continue
        if is_leaf:
            leaf_lexists = lexists
        if not lexists:
            chain.append(
                {
                    "path": str(current),
                    "lexists": False,
                    "lstat_performed": False,
                    "kind": "absent",
                    "is_leaf": is_leaf,
                }
            )
            continue
        try:
            metadata = _lstat_for_presence(current)
        except OSError as error:
            kind = "inaccessible"
            chain.append(
                {
                    "path": str(current),
                    "lexists": True,
                    "lstat_performed": True,
                    "kind": kind,
                    "error_type": type(error).__name__,
                    "is_leaf": is_leaf,
                }
            )
            if first_issue is None:
                first_issue = (kind, str(current))
            continue
        reparse = _metadata_is_reparse(metadata)
        try:
            mount_alias = index != 0 and bool(_ismount_for_presence(current))
        except OSError:
            mount_alias = True
        if reparse:
            kind = "link_or_reparse"
        elif mount_alias:
            kind = "mount_alias"
        elif stat.S_ISDIR(metadata.st_mode):
            kind = "ordinary_directory"
        elif stat.S_ISREG(metadata.st_mode):
            kind = "ordinary_file"
        else:
            kind = "nonordinary_special"
        chain.append(
            {
                "path": str(current),
                "lexists": True,
                "lstat_performed": True,
                "kind": kind,
                "is_leaf": is_leaf,
                "reparse": reparse,
                "mount_alias": mount_alias,
            }
        )
        if is_leaf:
            leaf_kind = kind
        issue_kind: str | None = None
        if kind in {"link_or_reparse", "mount_alias", "nonordinary_special"}:
            issue_kind = kind
        elif not is_leaf and kind != "ordinary_directory":
            issue_kind = "ancestor_not_directory"
        if issue_kind is not None and first_issue is None:
            first_issue = (issue_kind, str(current))
    if first_issue is not None:
        classification = first_issue[0]
        first_issue_path = first_issue[1]
        clean_absent = False
        path_appearance = True
    elif not leaf_lexists:
        classification = "clean_absent"
        first_issue_path = None
        clean_absent = True
        path_appearance = False
    else:
        classification = leaf_kind
        first_issue_path = None
        clean_absent = False
        path_appearance = True
    return PathPresence(
        label=label,
        raw_path=str(candidate),
        classification=classification,
        clean_absent=clean_absent,
        path_appearance=path_appearance,
        leaf_lexists=leaf_lexists,
        first_issue_path=first_issue_path,
        chain=tuple(chain),
    )


@dataclasses.dataclass(frozen=True)
class SuccessCommitExpectation:
    payload: Mapping[str, object]
    payload_bytes: bytes
    payload_sha256: str
    manifest: Mapping[str, object]
    manifest_bytes: bytes
    manifest_sha256: str


class SuccessCommitIndeterminateError(RuntimeError):
    """Path appearance exists but exact committed truth cannot be proven."""

    def __init__(self, message: str, *, outcome: Mapping[str, object]) -> None:
        self.outcome = dict(outcome)
        self.classification = "commit_indeterminate"
        self.resume_allowed = False
        self.is_infeasibility_evidence = False
        super().__init__(message)


def _validate_committed_result(
    target: Path,
    *,
    config: Mapping[str, Any],
    controller: Mapping[str, Any],
    ledger: ControllerLedger,
) -> dict[str, object]:
    target_presence = _probe_path(target, label="committed result")
    if target_presence.classification != "ordinary_directory":
        raise ValueError("committed result is not an exact ordinary directory")
    return predecessor._validate_committed_result(
        target, config=config, controller=controller, ledger=ledger
    )


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
        raise ValueError("predecessor v4 seal payload drifted before v6 commit")
    payload: dict[str, object] = {
        "schema": SUCCESS_PAYLOAD_SCHEMA,
        "commit_protocol": "repair_010_exact_success_directory_presence_safe_v2",
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
    presence = _probe_path(success_directory, label="v6 success commit")
    if presence.classification != "ordinary_directory":
        raise ValueError("v6 success commit is not an exact ordinary directory")
    entries = {entry.name: entry for entry in os.scandir(success_directory)}
    if set(entries) != {"success.json", "SHA256SUMS.json"}:
        raise ValueError("v6 success commit exact inventory drifted")
    for name, entry in entries.items():
        member = _probe_path(Path(entry.path), label=f"v6 success member {name}")
        if member.classification != "ordinary_file" or not entry.is_file(
            follow_symlinks=False
        ):
            raise ValueError(f"v6 success commit member is not ordinary: {name}")
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
        raise ValueError("v6 success commit exact bytes/hash/payload drifted")
    return dict(expectation.payload)


def _publish_success_directory(
    success_directory: Path, expectation: SuccessCommitExpectation
) -> None:
    initial = _probe_path(success_directory, label="v6 success commit")
    if not initial.clean_absent:
        raise FileExistsError("v6 success commit path is not cleanly absent")
    parent = _probe_path(success_directory.parent, label="v6 success parent")
    if parent.clean_absent:
        success_directory.parent.mkdir(parents=True, exist_ok=True)
        parent = _probe_path(success_directory.parent, label="v6 success parent")
    if parent.classification != "ordinary_directory":
        raise ValueError("v6 success parent is not an ordinary directory")
    staging = success_directory.parent / (
        f".{success_directory.name}.staging.{secrets.token_hex(16)}"
    )
    if not _probe_path(staging, label="v6 success staging").clean_absent:
        raise FileExistsError("v6 success staging path is not cleanly absent")
    staging.mkdir(exist_ok=False)
    renamed = False
    try:
        _write_exact(staging / "success.json", expectation.payload_bytes)
        _write_exact(staging / "SHA256SUMS.json", expectation.manifest_bytes)
        _verify_success_directory(staging, expectation)
        if not _probe_path(success_directory, label="v6 success commit").clean_absent:
            raise FileExistsError("v6 success commit appeared before rename")
        staging.rename(success_directory)
        renamed = True
        _verify_success_directory(success_directory, expectation)
    finally:
        if not renamed:
            staging_presence = _probe_path(staging, label="v6 success staging cleanup")
            if staging_presence.classification == "ordinary_directory":
                shutil.rmtree(staging)


def _outcome(
    classification: str,
    *,
    target: Path,
    success_directory: Path,
    terminal_directory: Path,
    original_error: BaseException | None,
) -> dict[str, object]:
    target_presence = _probe_path(target, label="v6 result target")
    success_presence = _probe_path(success_directory, label="v6 success commit")
    terminal_presence = _probe_path(terminal_directory, label="v6 terminal state")
    committed = classification == "committed_success"
    return {
        "schema": OUTCOME_SCHEMA,
        "classification": classification,
        "published": committed,
        "success_commit_accepted": committed,
        "target_exists": target_presence.path_appearance,
        "success_commit_exists": success_presence.path_appearance,
        "terminal_state_exists": terminal_presence.path_appearance,
        "target_presence": target_presence.audit(),
        "success_commit_presence": success_presence.audit(),
        "terminal_state_presence": terminal_presence.audit(),
        "success_and_terminal_dual_state": (
            success_presence.path_appearance and terminal_presence.path_appearance
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
    target: Path,
    success_directory: Path,
    terminal_directory: Path,
    original_error: BaseException | None,
    cause: BaseException | None = None,
) -> None:
    outcome = _outcome(
        "commit_indeterminate",
        target=target,
        success_directory=success_directory,
        terminal_directory=terminal_directory,
        original_error=original_error,
    )
    error = SuccessCommitIndeterminateError(message, outcome=outcome)
    if cause is not None:
        raise error from cause
    if original_error is not None:
        raise error from original_error
    raise error


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
    terminal_presence = _probe_path(terminal_directory, label="v6 terminal state")
    success_presence = _probe_path(success_directory, label="v6 success commit")
    if not terminal_presence.clean_absent:
        _raise_indeterminate(
            "v6 terminal path appearance makes commit state indeterminate",
            target=target,
            success_directory=success_directory,
            terminal_directory=terminal_directory,
            original_error=original_error,
        )
    if success_presence.clean_absent:
        return _outcome(
            "honest_incomplete",
            target=target,
            success_directory=success_directory,
            terminal_directory=terminal_directory,
            original_error=original_error,
        )
    if success_presence.classification != "ordinary_directory":
        _raise_indeterminate(
            "v6 success path appearance is not an ordinary committed directory",
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
        final_terminal = _probe_path(terminal_directory, label="v6 terminal final")
        final_success = _probe_path(success_directory, label="v6 success final")
        if (
            not final_terminal.clean_absent
            or final_success.classification != "ordinary_directory"
        ):
            raise ValueError("v6 final presence changed during reconciliation")
    except BaseException as validation_error:  # noqa: BLE001 - fail-closed gate
        _raise_indeterminate(
            "v6 success path exists but exact committed bytes/bindings cannot be proven",
            target=target,
            success_directory=success_directory,
            terminal_directory=terminal_directory,
            original_error=original_error,
            cause=validation_error,
        )
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
    """Run exact v4 precommit logic, then apply v6 presence-safe commit."""

    _verify_predecessor_authority()
    _inspect_v6_chain()
    if config != _publication_config():
        raise ValueError("v6 publisher requires the exact sealed v4 precommit config")
    success_before = _probe_path(success_directory, label="v6 success preflight")
    terminal_before = _probe_path(terminal_directory, label="v6 terminal preflight")
    if not success_before.clean_absent or not terminal_before.clean_absent:
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
    real_atomic_json = v4.recovery._atomic_json
    real_load_json = v4._load_json

    def atomic_adapter(path: Path, payload: object) -> None:
        nonlocal expectation
        if Path(path) != Path(success_directory):
            real_atomic_json(path, payload)
            return
        if expectation is not None:
            raise RuntimeError("v6 success commit was attempted more than once")
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
        if Path(path) != Path(success_directory):
            return real_load_json(path, label)
        if expectation is None:
            raise ValueError("v6 success expectation is missing")
        success = _verify_success_directory(success_directory, expectation)
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
        except BaseException as error:  # noqa: BLE001 - exact commit reconciliation
            original_error = error
        finally:
            v4.recovery._atomic_json = real_atomic_json
            v4._load_json = real_load_json
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
    """Recovery accepts only exact ordinary success and clean-absent terminal."""

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
        raise ValueError("v6 exact success commit is cleanly absent; recovery forbidden")
    bindings = _validate_committed_result(
        target, config=config, controller=controller, ledger=ledger
    )
    v4_seal = {
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
        from experiments.validate_rq2_public_grid_two_block_pilot_candidate_v6 import (
            validate,
        )

        return validate()
    _require_execution_authority()
    raise RuntimeError("closed v6 candidate cannot run; execution successor required")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    print(json.dumps(run(validate_only=bool(args.validate_only)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
