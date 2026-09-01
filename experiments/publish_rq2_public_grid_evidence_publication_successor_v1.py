"""Vnext-only atomic publisher for the closed two-child review fixture."""

from __future__ import annotations

import dataclasses
import json
import os
import shutil
import stat
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from experiments import rq2_public_grid_evidence_publication_contract_v1 as contract
from experiments import run_rq2_public_grid_two_block_pilot_candidate_v7 as presence_v7


@dataclasses.dataclass(frozen=True, slots=True)
class PublicationPaths:
    result: Path
    success: Path
    terminal: Path

    def as_object(self) -> dict[str, str]:
        return {"result": str(self.result), "success": str(self.success), "terminal": str(self.terminal)}


def publication_paths(base: Path) -> PublicationPaths:
    return PublicationPaths(base, base.with_name(base.name + ".PUBLISHED"), base.with_name(base.name + ".TERMINAL"))


def _read_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise contract.ContractRejected(f"{label} JSON malformed") from exc
    if not isinstance(value, dict):
        raise contract.ContractRejected(f"{label} is not an object")
    return value


def _atomic_write(path: Path, raw: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise contract.ContractRejected("publication member already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    with temporary.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _typed_tree(root: Path) -> dict[str, object]:
    directories: list[str] = ["."]
    files: dict[str, str] = {}
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda item: item.name)
        except OSError as exc:
            raise contract.ContractRejected("publication tree unreadable") from exc
        for entry in entries:
            relative = Path(entry.path).relative_to(root).as_posix()
            try:
                observed = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise contract.ContractRejected("publication member unreadable") from exc
            if entry.is_symlink() or getattr(observed, "st_file_attributes", 0) & 0x400:
                raise contract.ContractRejected("publication alias/reparse rejected")
            if stat.S_ISDIR(observed.st_mode):
                directories.append(relative)
                stack.append(Path(entry.path))
            elif stat.S_ISREG(observed.st_mode):
                if relative == "SHA256SUMS.json":
                    continue
                files[relative] = contract.sha256_bytes(contract.read_stable(Path(entry.path)))
            else:
                raise contract.ContractRejected("publication special member rejected")
    return {
        "schema": "rq2_public_grid_evidence_publication_typed_tree_v1",
        "directories": sorted(directories),
        "files": dict(sorted(files.items())),
    }


def _validate_source(evidence: contract.AcceptedEvidenceVnext) -> tuple[dict[str, Any], dict[str, Any]]:
    result_path = Path(evidence.result_path)
    receipt_path = Path(evidence.attempt_receipt_path)
    if receipt_path != result_path.with_name("attempt_receipt.json") or result_path.name != "worker_result.json":
        raise contract.ContractRejected("evidence source path layout drifted")
    result_raw = contract.read_stable(result_path)
    receipt_raw = contract.read_stable(receipt_path)
    if result_raw != evidence.result_bytes or receipt_raw != evidence.attempt_receipt_bytes:
        raise contract.ContractRejected("source-memory evidence mismatch")
    if contract.sha256_bytes(result_raw) != evidence.result_sha256 or contract.sha256_bytes(receipt_raw) != evidence.attempt_receipt_sha256:
        raise contract.ContractRejected("source hash drifted")
    result = _read_json_bytes(result_raw, "worker result")
    receipt = _read_json_bytes(receipt_raw, "attempt receipt")
    scientific = result.get("scientific_payload")
    if not isinstance(scientific, dict) or contract.exact_json_bytes(scientific) != evidence.scientific_bytes:
        raise contract.ContractRejected("scientific source bytes drifted")
    if result.get("scientific_payload_sha256") != evidence.scientific_sha256:
        raise contract.ContractRejected("scientific result binding drifted")
    if receipt.get("result_sha256") != evidence.result_sha256 or receipt.get("scientific_payload_sha256") != evidence.scientific_sha256:
        raise contract.ContractRejected("attempt receipt binding drifted")
    if receipt.get("controller_validated") is not False or receipt.get("published") is not False:
        raise contract.ContractRejected("attempt receipt overclaims controller/publication state")
    contract.validate_scientific_payload(scientific, evidence.block_id)
    return result, receipt


def _validate_result_tree(
    root: Path,
    ledger: contract.ControllerLedgerVnext,
    receipt: contract.ControllerReceiptVnext,
) -> dict[str, Any]:
    manifest_path = root / "SHA256SUMS.json"
    manifest = _read_json_bytes(contract.read_stable(manifest_path), "result manifest")
    if manifest != _typed_tree(root):
        raise contract.ContractRejected("result typed manifest drifted")
    expected_dirs = {".", "workers", *(f"workers/{block}" for block in contract.BLOCKS)}
    expected_files = {
        "controller_receipt.json",
        "summary.json",
        "comparison.json",
        *(f"workers/{block}/{name}" for block in contract.BLOCKS for name in ("worker_result.json", "attempt_receipt.json", "accepted_evidence.json", "ack.json", "envelope.json", "hello.json")),
    }
    if set(manifest["directories"]) != expected_dirs or set(manifest["files"]) != expected_files:
        raise contract.ContractRejected("result exact inventory drifted")
    observed_receipt = _read_json_bytes(contract.read_stable(root / "controller_receipt.json"), "controller receipt")
    if observed_receipt != receipt.as_object():
        raise contract.ContractRejected("controller receipt copy drifted")
    for evidence in ledger.records:
        destination = root / "workers" / evidence.block_id
        pairs = {
            "worker_result.json": evidence.result_bytes,
            "attempt_receipt.json": evidence.attempt_receipt_bytes,
            "accepted_evidence.json": contract.exact_json_bytes(evidence.as_object()),
            "ack.json": evidence.ack_bytes,
            "envelope.json": evidence.envelope_bytes,
            "hello.json": evidence.hello_bytes,
        }
        for name, raw in pairs.items():
            if contract.read_stable(destination / name) != raw:
                raise contract.ContractRejected("published evidence bytes drifted")
    return manifest


def reconcile_publication(paths: PublicationPaths | Mapping[str, str]) -> dict[str, object]:
    if isinstance(paths, Mapping):
        paths = PublicationPaths(*(Path(paths[key]) for key in ("result", "success", "terminal")))
    snapshot = presence_v7._capture_publication_presence_snapshot(
        target=paths.result, success_directory=paths.success, terminal_directory=paths.terminal
    )
    state = presence_v7._snapshot_state(snapshot)
    if state == "honest_incomplete":
        if snapshot.result.exact_ordinary_directory:
            manifest_path = paths.result / "SHA256SUMS.json"
            try:
                appears = os.path.lexists(manifest_path)
            except OSError:
                appears = True
            if appears:
                try:
                    manifest = _read_json_bytes(
                        contract.read_stable(manifest_path), "unsealed result manifest"
                    )
                    if manifest != _typed_tree(paths.result):
                        raise contract.ContractRejected("unsealed result exact tree drifted")
                except (OSError, contract.ContractRejected):
                    return {
                        "classification": "commit_indeterminate",
                        "published": False,
                        "resume_allowed": False,
                        "infeasible": False,
                    }
        return {"classification": "honest_incomplete", "published": False, "resume_allowed": False, "infeasible": False}
    if state != "success_candidate":
        return {"classification": "commit_indeterminate", "published": False, "resume_allowed": False, "infeasible": False}
    try:
        success = _read_json_bytes(contract.read_stable(paths.success / "success.json"), "success commit")
        success_manifest = _read_json_bytes(contract.read_stable(paths.success / "SHA256SUMS.json"), "success manifest")
        expected_success_manifest = {
            "schema": "rq2_public_grid_success_commit_manifest_vnext_v1",
            "files": {"success.json": contract.sha256_bytes(contract.read_stable(paths.success / "success.json"))},
        }
        result_manifest_sha = contract.sha256_bytes(contract.read_stable(paths.result / "SHA256SUMS.json"))
        result_manifest = _read_json_bytes(
            contract.read_stable(paths.result / "SHA256SUMS.json"), "result manifest"
        )
        if result_manifest != _typed_tree(paths.result):
            raise contract.ContractRejected("committed result exact tree drifted")
        if success_manifest != expected_success_manifest or success != {
            "schema": "rq2_public_grid_success_commit_vnext_v1",
            "classification": "committed_success",
            "published": True,
            "review_fixture": True,
            "nonformal": True,
            "claim": False,
            "result_manifest_sha256": result_manifest_sha,
        }:
            raise contract.ContractRejected("success commit binding drifted")
    except (OSError, contract.ContractRejected):
        return {"classification": "commit_indeterminate", "published": False, "resume_allowed": False, "infeasible": False}
    return {"classification": "committed_success", "published": True, "resume_allowed": False, "infeasible": False}


def publish_review_fixture(
    ledger: contract.ControllerLedgerVnext,
    receipt: contract.ControllerReceiptVnext,
    paths: PublicationPaths,
    *,
    verifier: contract.StageAwareClosureVerifier | None = None,
    registered_test_hook: str | None = None,
) -> dict[str, object]:
    if type(ledger) is not contract.ControllerLedgerVnext:
        raise contract.ContractRejected("cross-protocol ledger rejected")
    ledger._verify_controller_receipt(receipt)
    contract.verify_frozen_ledger(ledger.records, receipt)
    for evidence in ledger.records:
        _validate_source(evidence)
    initial = reconcile_publication(paths)
    if initial["classification"] != "honest_incomplete":
        raise contract.ContractRejected("publication paths are not clean/eligible")
    if paths.result.exists() or paths.success.exists() or paths.terminal.exists():
        raise contract.ContractRejected("publication root appearance rejected")
    verifier = verifier or contract.StageAwareClosureVerifier()
    if registered_test_hook not in (None, "extra_after_copy", "extra_after_result_rename"):
        raise contract.ContractRejected("unregistered publication test hook")
    verifier.verify("controller_post_block2_pre_publish")
    staging = paths.result.with_name(f".{paths.result.name}.staging.{os.getpid()}")
    success_staging = paths.success.with_name(f".{paths.success.name}.staging.{os.getpid()}")
    if staging.exists() or success_staging.exists():
        raise contract.ContractRejected("publication staging appearance rejected")
    try:
        staging.mkdir(parents=True, exist_ok=False)
        for evidence in ledger.records:
            destination = staging / "workers" / evidence.block_id
            destination.mkdir(parents=True, exist_ok=False)
            for name, raw in {
                "worker_result.json": evidence.result_bytes,
                "attempt_receipt.json": evidence.attempt_receipt_bytes,
                "accepted_evidence.json": contract.exact_json_bytes(evidence.as_object()),
                "ack.json": evidence.ack_bytes,
                "envelope.json": evidence.envelope_bytes,
                "hello.json": evidence.hello_bytes,
            }.items():
                _atomic_write(destination / name, raw)
        _atomic_write(staging / "controller_receipt.json", contract.exact_json_bytes(receipt.as_object()))
        from experiments import (
            run_rq2_public_grid_two_block_pilot_candidate_v4 as candidate,
        )

        scientific_0008 = _read_json_bytes(ledger.records[0].scientific_bytes, "0008 science")
        comparison = candidate.predecessor.compare_named_outage_0008(
            scientific_0008, candidate.predecessor._extract_gurobi_payload()
        )
        _atomic_write(staging / "comparison.json", contract.exact_json_bytes(comparison))
        summary = {
            "schema": "rq2_public_grid_review_fixture_summary_vnext_v1",
            "record_count": 2,
            "blocks": list(contract.BLOCKS),
            "review_fixture": True,
            "nonformal": True,
            "claim": False,
            "scientific_loader_calls": 0,
            "solver_calls": 0,
            "comparison_passed": comparison.get("comparison_passed") is True,
        }
        _atomic_write(staging / "summary.json", contract.exact_json_bytes(summary))
        if comparison.get("comparison_passed") is not True:
            raise contract.ContractRejected("frozen 0008 named-outage comparison failed")
        if registered_test_hook == "extra_after_copy":
            (staging / "unexpected-empty-directory").mkdir()
        _atomic_write(staging / "SHA256SUMS.json", contract.exact_json_bytes(_typed_tree(staging)))
        _validate_result_tree(staging, ledger, receipt)
        os.replace(staging, paths.result)
        if registered_test_hook == "extra_after_result_rename":
            (paths.result / "unexpected-empty-directory").mkdir()
        _validate_result_tree(paths.result, ledger, receipt)
        # This full check is deliberately after result appearance and before the
        # unique success-directory commit point.
        verifier.verify("controller_post_publish")
        success_staging.mkdir(parents=True, exist_ok=False)
        success = {
            "schema": "rq2_public_grid_success_commit_vnext_v1",
            "classification": "committed_success",
            "published": True,
            "review_fixture": True,
            "nonformal": True,
            "claim": False,
            "result_manifest_sha256": contract.sha256_bytes(contract.read_stable(paths.result / "SHA256SUMS.json")),
        }
        success_raw = contract.exact_json_bytes(success)
        _atomic_write(success_staging / "success.json", success_raw)
        success_manifest = {
            "schema": "rq2_public_grid_success_commit_manifest_vnext_v1",
            "files": {"success.json": contract.sha256_bytes(success_raw)},
        }
        _atomic_write(success_staging / "SHA256SUMS.json", contract.exact_json_bytes(success_manifest))
        os.replace(success_staging, paths.success)
        outcome = reconcile_publication(paths)
        if outcome["classification"] != "committed_success":
            raise contract.ContractRejected("post-commit exact readback failed")
        contract.verify_full_live_closure()
        return outcome
    except contract.LiveClosureDrift:
        if paths.result.exists():
            return {"classification": "commit_indeterminate", "published": False, "resume_allowed": False, "infeasible": False}
        raise
    except Exception:
        # Never delete or overwrite an appeared result/success state. Only
        # private pre-appearance staging may be removed.
        if not paths.result.exists() and staging.exists():
            shutil.rmtree(staging)
        if not paths.success.exists() and success_staging.exists():
            shutil.rmtree(success_staging)
        raise
