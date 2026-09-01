"""Stdlib-only frozen dependency and review-receipt verifier for successor v2."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import stat
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


class ClosureRejected(RuntimeError):
    """A fail-closed dependency or receipt rejection."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _is_reparse(metadata: os.stat_result) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    return bool(attributes & int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)))


def _lstat(path: Path) -> os.stat_result:
    try:
        return os.lstat(path)
    except FileNotFoundError as exc:
        if getattr(exc, "winerror", None) in (2, 3) or exc.errno == errno.ENOENT:
            raise ClosureRejected(f"required closure path is absent: {path}") from exc
        raise ClosureRejected(f"closure path presence is indeterminate: {path}") from exc
    except OSError as exc:
        raise ClosureRejected(f"closure path presence is indeterminate: {path}") from exc


def strict_file(path: Path) -> None:
    raw = str(path)
    if not os.path.isabs(raw) or os.path.normpath(raw) != raw:
        raise ClosureRejected(f"closure path is not canonical absolute: {raw}")
    drive, tail = os.path.splitdrive(raw)
    root = Path(drive + os.sep)
    current = root
    final: os.stat_result | None = None
    for segment in [part for part in tail.split(os.sep) if part]:
        current /= segment
        metadata = _lstat(current)
        if stat.S_ISLNK(metadata.st_mode) or _is_reparse(metadata):
            raise ClosureRejected(f"closure alias/reparse rejected: {current}")
        try:
            mounted = os.path.ismount(current)
        except OSError as exc:
            raise ClosureRejected(f"closure mount status indeterminate: {current}") from exc
        if current != root and mounted:
            raise ClosureRejected(f"closure nested mount rejected: {current}")
        final = metadata
    if final is None or not stat.S_ISREG(final.st_mode):
        raise ClosureRejected(f"closure member is not an ordinary file: {path}")


def read_stable_bytes(path: Path) -> bytes:
    strict_file(path)
    try:
        first = path.read_bytes()
        second = path.read_bytes()
    except OSError as exc:
        raise ClosureRejected(f"closure member is unreadable: {path}") from exc
    if first != second:
        raise ClosureRejected(f"closure member changed during double-read: {path}")
    return first


def _json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ClosureRejected(f"{label} JSON is malformed") from exc
    if not isinstance(value, dict):
        raise ClosureRejected(f"{label} JSON is not an object")
    return value


def _verify_hash(
    root: Path,
    relative: str,
    expected: str,
    *,
    trace: Callable[[str, str], None] | None,
) -> bytes:
    path = root / relative
    raw = read_stable_bytes(path)
    observed = hashlib.sha256(raw).hexdigest()
    if observed != expected:
        raise ClosureRejected(f"dependency hash drifted: {relative}")
    if trace is not None:
        trace(relative, observed)
    return raw


def verify_dependency_closure(
    root: Path,
    config: Mapping[str, Any],
    *,
    trace: Callable[[str, str], None] | None = None,
) -> tuple[str, ...]:
    """Expand every frozen manifest and verify every live member exactly once."""
    closure = config.get("dependency_closure")
    if not isinstance(closure, dict) or set(closure) != {
        "bundles",
        "flat_manifests",
        "transitive_files",
        "named_runner_paths",
    }:
        raise ClosureRejected("dependency closure contract is malformed")
    hashed: set[str] = set()

    def verify(relative: str, expected: str) -> bytes:
        raw = _verify_hash(root, relative, expected, trace=trace)
        hashed.add(relative)
        return raw

    bundles = closure["bundles"]
    if not isinstance(bundles, list) or len(bundles) != 4:
        raise ClosureRejected("exact four recursive bundles are required")
    for bundle in bundles:
        if not isinstance(bundle, dict) or set(bundle) != {
            "name",
            "outer_path",
            "outer_sha256",
            "outer_schema",
            "inner_path",
            "inner_sha256",
            "inner_schema",
            "members",
        }:
            raise ClosureRejected("recursive bundle contract is malformed")
        outer = _json_bytes(
            verify(bundle["outer_path"], bundle["outer_sha256"]),
            f"{bundle['name']} outer",
        )
        if outer != {
            "schema": bundle["outer_schema"],
            "files": {bundle["inner_path"]: bundle["inner_sha256"]},
        }:
            raise ClosureRejected(f"{bundle['name']} outer inventory drifted")
        inner = _json_bytes(
            verify(bundle["inner_path"], bundle["inner_sha256"]),
            f"{bundle['name']} inner",
        )
        members = bundle["members"]
        if inner != {"schema": bundle["inner_schema"], "files": members}:
            raise ClosureRejected(f"{bundle['name']} inner inventory drifted")
        for relative, digest in members.items():
            verify(relative, digest)

    flat = closure["flat_manifests"]
    if not isinstance(flat, list) or len(flat) != 1:
        raise ClosureRejected("exact recovery-v2 flat manifest is required")
    recovery = flat[0]
    if not isinstance(recovery, dict) or set(recovery) != {
        "name",
        "path",
        "sha256",
        "members",
    }:
        raise ClosureRejected("flat recovery manifest contract is malformed")
    manifest = _json_bytes(
        verify(recovery["path"], recovery["sha256"]), recovery["name"]
    )
    if manifest != recovery["members"] or len(manifest) != 7:
        raise ClosureRejected("recovery-v2 exact seven-member inventory drifted")
    for relative, digest in recovery["members"].items():
        verify(relative, digest)

    transitive = closure["transitive_files"]
    if not isinstance(transitive, dict) or len(transitive) != 12:
        raise ClosureRejected("provenance transitive inventory is not exact")
    for relative, digest in transitive.items():
        verify(relative, digest)

    named = closure["named_runner_paths"]
    if not isinstance(named, list) or len(named) < 4 or any(path not in hashed for path in named):
        raise ClosureRejected("reviewer-named runner hash trace is incomplete")
    return tuple(sorted(hashed))


def closure_binding(config: Mapping[str, Any]) -> dict[str, Any]:
    closure = config["dependency_closure"]
    return {
        "dependency_closure_sha256": canonical_sha256(closure),
        "named_runner_paths": list(closure["named_runner_paths"]),
    }


def validate_review_receipt_object(
    receipt: object,
    *,
    config: Mapping[str, Any],
    outer_relative: str,
    outer_sha256: str,
) -> None:
    expected = config["fixed_execution_review"]
    if not isinstance(receipt, dict) or set(receipt) != set(expected["exact_keyset"]):
        raise ClosureRejected("fixed review receipt keyset is not exact")
    if (
        receipt["schema"] != expected["schema"]
        or receipt["version"] != 2
        or not isinstance(receipt["reviewed_on"], str)
        or not receipt["reviewed_on"]
        or receipt["reviewer_role"] != "independent_sol_reviewer"
        or receipt["verdict"] != "PASS"
        or receipt["reviewed_outer"]
        != {"path": outer_relative, "sha256": outer_sha256}
        or receipt["bound_predecessor"] != config["predecessor"]
        or receipt["bound_dependency_closure"] != closure_binding(config)
        or receipt["findings"] != []
        or receipt["effect"] != expected["exact_effect"]
    ):
        raise ClosureRejected("fixed review receipt object/effect is not exact")


def load_and_validate_review_receipt(
    path: Path,
    *,
    config: Mapping[str, Any],
    outer_path: Path,
    root: Path,
) -> tuple[dict[str, Any], str]:
    raw = read_stable_bytes(path)
    receipt = _json_bytes(raw, "fixed review receipt")
    outer_raw = read_stable_bytes(outer_path)
    validate_review_receipt_object(
        receipt,
        config=config,
        outer_relative=outer_path.relative_to(root).as_posix(),
        outer_sha256=hashlib.sha256(outer_raw).hexdigest(),
    )
    return receipt, hashlib.sha256(raw).hexdigest()
