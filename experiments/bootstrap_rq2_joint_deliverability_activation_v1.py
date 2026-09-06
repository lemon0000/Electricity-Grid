"""Stdlib-first bootstrap for RQ2 joint-deliverability activation v1."""

from __future__ import annotations

import argparse
import base64
import binascii
import datetime
import hashlib
import importlib.abc
import importlib.util
import json
import math
import os
import stat
import subprocess
import sys
import sysconfig
import tempfile
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = "configs/rq2_joint_deliverability_activation_successor_v1.json"
INNER_RELATIVE = (
    "configs/rq2_joint_deliverability_activation_successor_v1.SHA256SUMS.json"
)
OUTER_RELATIVE = (
    "configs/rq2_joint_deliverability_activation_successor_v1.OUTER.SHA256SUMS.json"
)
CONFIG = ROOT / CONFIG_RELATIVE
INNER = ROOT / INNER_RELATIVE
OUTER = ROOT / OUTER_RELATIVE
BOOTSTRAP_RELATIVE = "experiments/bootstrap_rq2_joint_deliverability_activation_v1.py"
CONTROLLER_RELATIVE = "experiments/run_rq2_joint_deliverability_activation_v1.py"
EXECUTION_CORE_RELATIVE = "src/rq2_joint_deliverability_execution_v3/core.py"
ACTIVATION_REVIEW_RELATIVE = (
    "configs/rq2_joint_deliverability_activation_review_pass_v1.json"
)
ACTIVATION_REVIEW_SCHEMA = "rq2_joint_deliverability_activation_review_pass_v1"
ACTIVATION_REVIEW_SCOPE = "rq2_joint_deliverability_activation_successor_v1_exact_outer"
ACTIVATION_REVIEW_MODEL = "gpt-5.6-sol"
ACTIVATION_REVIEW_EFFECT = {
    "independent_activation_R3_review_passed": True,
    "activation_review_gate_closed": True,
    "formal_execution_authorized": False,
    "formal_result_exists": False,
    "paper_claim": False,
    "security_certified": False,
}
EXECUTION_STATIC_AUTHORITY_SHA256 = (
    "b8fc7b3471d20e3efe6ca879de27379d3768ec31c1a978d2e538f98543004187"
)
_STAGE0_SOURCE = """\
import base64
import hashlib
import json
import sys

expected_sha256, bootstrap_relative, filename, pycache_prefix = sys.argv[1:5]
envelope_raw = sys.stdin.buffer.read()
if hashlib.sha256(envelope_raw).hexdigest() != expected_sha256:
    raise SystemExit("parent envelope digest mismatch")
envelope = json.loads(envelope_raw)
if envelope.get("schema") != "rq2_joint_deliverability_activation_parent_envelope_v1":
    raise SystemExit("parent envelope schema mismatch")
entry = envelope["python_sources"][bootstrap_relative]
source = base64.b64decode(entry["bytes_b64"], validate=True)
if hashlib.sha256(source).hexdigest() != entry["sha256"]:
    raise SystemExit("verified bootstrap digest mismatch")
sys.argv = [
    filename,
    "--internal-probe",
    "--expected-pycache-prefix",
    pycache_prefix,
]
main = sys.modules["__main__"]
main.__file__ = filename
main.__package__ = None
main.__cached__ = None
main._PARENT_ENVELOPE_RAW = envelope_raw
exec(compile(source, filename, "exec", dont_inherit=True), vars(main))
"""


class ActivationRejected(RuntimeError):
    """The activation boundary could not prove a required invariant."""


def _expected_activation_review_contract() -> dict[str, object]:
    return {
        "path": ACTIVATION_REVIEW_RELATIVE,
        "schema": ACTIVATION_REVIEW_SCHEMA,
        "review_scope": ACTIVATION_REVIEW_SCOPE,
        "reviewer_model": ACTIVATION_REVIEW_MODEL,
        "required_effect": dict(ACTIVATION_REVIEW_EFFECT),
        "present": False,
    }


def _reject_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ActivationRejected(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_constant(raw: str) -> None:
    raise ActivationRejected(f"non-finite JSON number: {raw}")


def _finite_float(raw: str) -> float:
    value = float(raw)
    if not math.isfinite(value):
        raise ActivationRejected(f"non-finite JSON number: {raw}")
    return value


def _json_bytes(raw: bytes, label: str) -> dict[str, object]:
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite_constant,
            parse_float=_finite_float,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        if isinstance(error, ActivationRejected):
            raise
        raise ActivationRejected(f"invalid JSON: {label}") from error
    if not isinstance(value, dict):
        raise ActivationRejected(f"JSON root is not an object: {label}")
    return value


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _is_digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _strict_file(path: Path) -> None:
    absolute = path.absolute()
    anchor = Path(absolute.anchor)
    current = anchor
    for part in absolute.parts[1:]:
        current /= part
        try:
            metadata = os.lstat(current)
        except OSError as error:
            raise ActivationRejected(f"required path is absent: {path}") from error
        attributes = int(getattr(metadata, "st_file_attributes", 0))
        if stat.S_ISLNK(metadata.st_mode) or attributes & 0x400:
            raise ActivationRejected(f"path alias or reparse point rejected: {path}")
    if not stat.S_ISREG(os.lstat(absolute).st_mode):
        raise ActivationRejected(f"ordinary file required: {path}")


def _path_is_present_or_aliased(path: Path) -> bool:
    absolute = path.absolute()
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            metadata = os.lstat(current)
        except FileNotFoundError:
            return False
        except OSError as error:
            raise ActivationRejected(
                f"path presence is indeterminate: {path}"
            ) from error
        attributes = int(getattr(metadata, "st_file_attributes", 0))
        if stat.S_ISLNK(metadata.st_mode) or attributes & 0x400:
            return True
    return True


def _metadata_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _stable(path: Path) -> bytes:
    _strict_file(path)
    absolute = path.absolute()
    try:
        before = os.lstat(absolute)
        flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
        flags |= int(getattr(os, "O_NOFOLLOW", 0))
        descriptor = os.open(absolute, flags)
    except OSError as error:
        raise ActivationRejected(f"artifact is unreadable: {path}") from error
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or not os.path.samestat(before, opened):
            raise ActivationRejected(f"artifact identity changed before read: {path}")
        handle = os.fdopen(descriptor, "rb", closefd=True)
        descriptor = -1
        with handle:
            first = handle.read()
            after_first = os.fstat(handle.fileno())
            handle.seek(0)
            second = handle.read()
            after_second = os.fstat(handle.fileno())
        after = os.lstat(absolute)
    except OSError as error:
        raise ActivationRejected(f"artifact descriptor read failed: {path}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if (
        first != second
        or not os.path.samestat(opened, after)
        or _metadata_identity(before) != _metadata_identity(opened)
        or _metadata_identity(opened) != _metadata_identity(after_first)
        or _metadata_identity(after_first) != _metadata_identity(after_second)
        or _metadata_identity(after_second) != _metadata_identity(after)
    ):
        raise ActivationRejected(f"stable readback drifted: {path}")
    return first


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ActivationRejected(f"{label} must be a mapping")
    return dict(value)


def _relative(raw: object, label: str) -> str:
    if (
        not isinstance(raw, str)
        or not raw
        or Path(raw).is_absolute()
        or ".." in Path(raw).parts
    ):
        raise ActivationRejected(f"{label} must be repository-relative")
    return raw


def _load_config() -> tuple[dict[str, object], bytes]:
    raw = _stable(CONFIG)
    config = _json_bytes(raw, CONFIG_RELATIVE)
    if (
        config.get("schema") != "rq2_joint_deliverability_activation_successor_v1"
        or config.get("version") != 1
    ):
        raise ActivationRejected("activation config identity drifted")
    return config, raw


def _verify_outer_chain(
    outer_path: Path,
    *,
    expected_outer_sha256: str | None = None,
    expected_outer_schema: str | None = None,
    expected_inner_schema: str | None = None,
    expected_version: int | None = None,
    expected_inner_path: str | None = None,
) -> dict[str, object]:
    outer_raw = _stable(outer_path)
    outer_sha256 = _sha256(outer_raw)
    if expected_outer_sha256 is not None and outer_sha256 != expected_outer_sha256:
        raise ActivationRejected("outer manifest SHA-256 drifted")
    outer = _json_bytes(outer_raw, str(outer_path))
    inner = _mapping(outer.get("inner"), "outer inner identity")
    if (
        set(outer) != {"schema", "version", "inner"}
        or set(inner) != {"path", "sha256"}
        or not _is_digest(inner.get("sha256"))
        or (
            expected_outer_schema is not None
            and outer.get("schema") != expected_outer_schema
        )
        or (expected_version is not None and outer.get("version") != expected_version)
    ):
        raise ActivationRejected("outer manifest identity drifted")
    inner_relative = _relative(inner.get("path"), "inner manifest path")
    if expected_inner_path is not None and inner_relative != expected_inner_path:
        raise ActivationRejected("inner manifest path drifted")
    inner_path = ROOT / inner_relative
    inner_raw = _stable(inner_path)
    if _sha256(inner_raw) != inner["sha256"]:
        raise ActivationRejected("inner manifest SHA-256 drifted")
    inner_value = _json_bytes(inner_raw, inner_relative)
    members = _mapping(inner_value.get("files"), "inner member inventory")
    if (
        set(inner_value) != {"schema", "version", "files"}
        or not members
        or (
            expected_inner_schema is not None
            and inner_value.get("schema") != expected_inner_schema
        )
        or (
            expected_version is not None
            and inner_value.get("version") != expected_version
        )
    ):
        raise ActivationRejected("inner member inventory is empty")
    member_bytes: dict[str, bytes] = {}
    for relative, expected in members.items():
        relative = _relative(relative, "inner member path")
        if not _is_digest(expected):
            raise ActivationRejected("inner member digest is invalid")
        raw_member = _stable(ROOT / relative)
        if _sha256(raw_member) != expected:
            raise ActivationRejected(f"sealed member SHA-256 drifted: {relative}")
        member_bytes[relative] = raw_member
    if _stable(outer_path) != outer_raw or _stable(inner_path) != inner_raw:
        raise ActivationRejected("sealed manifest chain changed during verification")
    for relative in reversed(tuple(member_bytes)):
        if _stable(ROOT / relative) != member_bytes[relative]:
            raise ActivationRejected(
                f"sealed member changed during chain verification: {relative}"
            )
    return {
        "outer_sha256": outer_sha256,
        "inner_sha256": str(inner["sha256"]),
        "member_count": len(members),
        "members": dict(members),
    }


def _verify_bundle(
    config: Mapping[str, object],
    *,
    require_sealed: bool,
) -> dict[str, object]:
    bundle = _mapping(config.get("bundle"), "activation bundle")
    members = bundle.get("members")
    if (
        bundle.get("inner_path") != INNER_RELATIVE
        or bundle.get("outer_path") != OUTER_RELATIVE
        or not isinstance(members, list)
        or any(not isinstance(item, str) for item in members)
        or len(members) != len(set(members))
    ):
        raise ActivationRejected("activation bundle contract drifted")
    expected_members = set(members)
    lifecycle = _mapping(config.get("lifecycle"), "activation lifecycle")
    if require_sealed:
        sealed_on = lifecycle.get("sealed_on")
        try:
            parsed_sealed_on = datetime.date.fromisoformat(str(sealed_on))
        except ValueError as error:
            raise ActivationRejected("sealed activation date drifted") from error
        if (
            set(lifecycle)
            != {
                "status",
                "sealed_on",
                "pre_seal_audit_complete",
                "sealed_ready_for_independent_review",
            }
            or lifecycle.get("status") != "SEALED_READY_FOR_INDEPENDENT_REVIEW"
            or not isinstance(sealed_on, str)
            or parsed_sealed_on.isoformat() != sealed_on
            or lifecycle.get("pre_seal_audit_complete") is not True
            or lifecycle.get("sealed_ready_for_independent_review") is not True
        ):
            raise ActivationRejected("sealed activation lifecycle drifted")
        chain = _verify_outer_chain(
            OUTER,
            expected_outer_schema=("rq2_joint_deliverability_activation_outer_v1"),
            expected_inner_schema=("rq2_joint_deliverability_activation_inner_v1"),
            expected_version=1,
            expected_inner_path=INNER_RELATIVE,
        )
        if (
            chain["member_count"] != len(expected_members)
            or set(chain["members"]) != expected_members
        ):
            raise ActivationRejected("activation sealed inventory drifted")
        return chain
    if lifecycle not in (
        {
            "status": "DRAFT_NONAUTHORITATIVE",
            "pre_seal_audit_complete": False,
            "sealed_ready_for_independent_review": False,
        },
        {
            "status": "PRE_SEAL_AUDIT",
            "pre_seal_audit_complete": False,
            "sealed_ready_for_independent_review": False,
        },
    ):
        raise ActivationRejected("draft activation lifecycle drifted")
    if _path_is_present_or_aliased(OUTER) or _path_is_present_or_aliased(INNER):
        raise ActivationRejected("draft activation must not have production manifests")
    for relative in expected_members:
        _stable(ROOT / _relative(relative, "activation bundle member"))
    return {
        "outer_sha256": None,
        "inner_sha256": None,
        "member_count": len(expected_members),
        "members": {},
    }


def _verify_execution_authority(
    config: Mapping[str, object],
) -> dict[str, str]:
    authority = _mapping(config.get("execution_authority"), "execution authority")
    expected_authority = {
        "outer_path": (
            "configs/rq2_joint_deliverability_execution_successor_v3."
            "OUTER.SHA256SUMS.json"
        ),
        "outer_sha256": (
            "b153f0320fe9dfe961575be4836f4bcf4044836be4fa66618119fc08d4cbce80"
        ),
        "review_path": "configs/rq2_joint_deliverability_execution_review_pass_v3.yaml",
        "review_sha256": (
            "1d8312e1458ce73dc76863a4b5c85f95506272ec53eaa088e523127b6ce0fa41"
        ),
        "static_authority_sha256": EXECUTION_STATIC_AUTHORITY_SHA256,
        "sealed_member_count": 22,
        "recursive_predecessors": [
            {
                "version": 2,
                "outer_path": (
                    "configs/rq2_joint_deliverability_execution_successor_v2."
                    "OUTER.SHA256SUMS.json"
                ),
                "outer_sha256": (
                    "ff70b138f61833908c84763c3a6df06ad255f6f6f26adfbf1e4051865a0e5f93"
                ),
                "sealed_member_count": 21,
            },
            {
                "version": 1,
                "outer_path": (
                    "configs/rq2_joint_deliverability_execution_successor_v1."
                    "OUTER.SHA256SUMS.json"
                ),
                "outer_sha256": (
                    "1ec234a1279b1c5a09b2beedb66ec1dfffcda28ed4a024df44d7d47060c976d2"
                ),
                "sealed_member_count": 19,
            },
        ],
    }
    if authority != expected_authority:
        raise ActivationRejected("execution authority contract drifted")
    outer_relative = _relative(authority.get("outer_path"), "execution outer path")
    review_relative = _relative(authority.get("review_path"), "execution review path")
    expected_outer = authority.get("outer_sha256")
    expected_review = authority.get("review_sha256")
    if not _is_digest(expected_outer) or not _is_digest(expected_review):
        raise ActivationRejected("execution authority digest is invalid")
    chain = _verify_outer_chain(
        ROOT / outer_relative,
        expected_outer_sha256=str(expected_outer),
        expected_outer_schema="rq2_joint_deliverability_execution_outer_v3",
        expected_inner_schema="rq2_joint_deliverability_execution_inner_v3",
        expected_version=3,
        expected_inner_path=(
            "configs/rq2_joint_deliverability_execution_successor_v3.SHA256SUMS.json"
        ),
    )
    if chain["member_count"] != authority.get("sealed_member_count"):
        raise ActivationRejected("execution authority member count drifted")
    if _sha256(_stable(ROOT / review_relative)) != expected_review:
        raise ActivationRejected("execution review SHA-256 drifted")
    predecessors = authority.get("recursive_predecessors")
    if not isinstance(predecessors, list) or [
        item.get("version") if isinstance(item, Mapping) else None
        for item in predecessors
    ] != [2, 1]:
        raise ActivationRejected("execution predecessor inventory drifted")
    for item in predecessors:
        predecessor = _mapping(item, "execution predecessor")
        version = predecessor.get("version")
        if (
            set(predecessor)
            != {
                "version",
                "outer_path",
                "outer_sha256",
                "sealed_member_count",
            }
            or type(version) is not int
            or version not in {1, 2}
        ):
            raise ActivationRejected("execution predecessor version drifted")
        expected_path = (
            "configs/rq2_joint_deliverability_execution_successor_"
            f"v{version}.OUTER.SHA256SUMS.json"
        )
        predecessor_path = _relative(
            predecessor.get("outer_path"),
            "execution predecessor outer path",
        )
        if predecessor_path != expected_path:
            raise ActivationRejected("execution predecessor path drifted")
        predecessor_sha256 = predecessor.get("outer_sha256")
        if not _is_digest(predecessor_sha256):
            raise ActivationRejected("execution predecessor digest is invalid")
        replayed = _verify_outer_chain(
            ROOT / predecessor_path,
            expected_outer_sha256=str(predecessor_sha256),
            expected_outer_schema=(
                f"rq2_joint_deliverability_execution_outer_v{version}"
            ),
            expected_inner_schema=(
                f"rq2_joint_deliverability_execution_inner_v{version}"
            ),
            expected_version=version,
            expected_inner_path=(
                "configs/rq2_joint_deliverability_execution_successor_"
                f"v{version}.SHA256SUMS.json"
            ),
        )
        if replayed["member_count"] != predecessor.get("sealed_member_count"):
            raise ActivationRejected("execution predecessor member count drifted")
    return {
        "execution_outer_sha256": str(expected_outer),
        "execution_review_sha256": str(expected_review),
        "static_authority_sha256": EXECUTION_STATIC_AUTHORITY_SHA256,
    }


def _python_closure_inventory(
    config: Mapping[str, object],
) -> dict[str, str]:
    closure = _mapping(config.get("python_closure"), "Python closure")
    members = _mapping(closure.get("members"), "Python closure members")
    roots = closure.get("roots")
    postimport_probe_members = closure.get("postimport_probe_members")
    if (
        closure.get("policy")
        != "stdlib_first_preimport_hash_then_verified_bytes_import"
        or not isinstance(roots, list)
        or any(not isinstance(item, str) for item in roots)
        or set(roots) - set(members)
        or not isinstance(postimport_probe_members, list)
        or any(not isinstance(item, str) for item in postimport_probe_members)
        or len(postimport_probe_members) != len(set(postimport_probe_members))
        or set(postimport_probe_members) - set(members)
        or closure.get("preimport_project_module_count") != 1
        or closure.get("isolated_interpreter_flags")
        != [
            "-I",
            "-B",
            "-S",
            "-X",
            "pycache_prefix=<fresh-empty-private-directory>",
        ]
        or closure.get("site_initialization_allowed") is not False
        or closure.get("dependency_path_policy")
        != "sysconfig_purelib_platlib_after_local_hash_verification"
        or closure.get("project_bytecode_cache_policy")
        != "fresh_empty_private_pycache_prefix"
        or closure.get("bootstrap_launch_policy")
        != "verified_bytes_over_stdin_to_isolated_stage0"
        or closure.get("project_source_import_policy")
        != "verified_bytes_in_memory_source_loader"
        or closure.get("caller_supplied_pythonpath_allowed") is not False
        or closure.get("postimport_unregistered_local_module_allowed") is not False
    ):
        raise ActivationRejected("Python closure contract drifted")
    expected_members: dict[str, str] = {}
    for raw_relative, expected in members.items():
        relative = _relative(raw_relative, "Python closure member")
        if not _is_digest(expected):
            raise ActivationRejected("Python closure digest is invalid")
        expected_members[relative] = str(expected)
    return expected_members


def _read_python_closure(
    config: Mapping[str, object],
) -> tuple[dict[str, str], dict[str, bytes]]:
    expected_members = _python_closure_inventory(config)
    verified: dict[str, str] = {}
    source_bytes: dict[str, bytes] = {}
    for relative, expected in expected_members.items():
        raw = _stable(ROOT / relative)
        if _sha256(raw) != expected:
            raise ActivationRejected(f"Python closure SHA-256 drifted: {relative}")
        verified[relative] = expected
        source_bytes[relative] = raw
    return verified, source_bytes


def _verify_python_closure(
    config: Mapping[str, object],
) -> dict[str, str]:
    verified, _source_bytes = _read_python_closure(config)
    return verified


def _bundle_identity(bundle: Mapping[str, object]) -> dict[str, object]:
    return {
        "outer_sha256": bundle.get("outer_sha256"),
        "inner_sha256": bundle.get("inner_sha256"),
        "member_count": bundle.get("member_count"),
    }


def _build_parent_envelope(
    *,
    config_raw: bytes,
    bundle: Mapping[str, object],
    execution: Mapping[str, str],
    closure: Mapping[str, str],
    source_bytes: Mapping[str, bytes],
) -> bytes:
    if set(closure) != set(source_bytes):
        raise ActivationRejected("parent source inventory drifted")
    sources = {
        relative: {
            "sha256": closure[relative],
            "bytes_b64": base64.b64encode(source_bytes[relative]).decode("ascii"),
        }
        for relative in sorted(closure, key=str.encode)
    }
    return _canonical_json_bytes(
        {
            "schema": "rq2_joint_deliverability_activation_parent_envelope_v1",
            "config": {
                "sha256": _sha256(config_raw),
                "bytes_b64": base64.b64encode(config_raw).decode("ascii"),
            },
            "activation_bundle": _bundle_identity(bundle),
            "execution_authority": dict(execution),
            "python_sources": sources,
        }
    )


def _decode_base64(raw: object, label: str) -> bytes:
    if not isinstance(raw, str):
        raise ActivationRejected(f"{label} is not base64 text")
    try:
        return base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as error:
        raise ActivationRejected(f"{label} is invalid base64") from error


def _decode_parent_envelope(
    raw: object,
) -> tuple[
    dict[str, object],
    bytes,
    dict[str, object],
    dict[str, str],
    dict[str, str],
    dict[str, bytes],
]:
    if not isinstance(raw, bytes):
        raise ActivationRejected("parent envelope was not supplied by stage-0")
    envelope = _json_bytes(raw, "parent envelope")
    if set(envelope) != {
        "schema",
        "config",
        "activation_bundle",
        "execution_authority",
        "python_sources",
    } or envelope.get("schema") != (
        "rq2_joint_deliverability_activation_parent_envelope_v1"
    ):
        raise ActivationRejected("parent envelope identity drifted")
    config_entry = _mapping(envelope.get("config"), "parent config entry")
    if set(config_entry) != {"sha256", "bytes_b64"} or not _is_digest(
        config_entry.get("sha256")
    ):
        raise ActivationRejected("parent config entry drifted")
    config_raw = _decode_base64(config_entry.get("bytes_b64"), "parent config")
    if _sha256(config_raw) != config_entry["sha256"]:
        raise ActivationRejected("parent config digest drifted")
    config = _json_bytes(config_raw, CONFIG_RELATIVE)
    if (
        config.get("schema") != "rq2_joint_deliverability_activation_successor_v1"
        or config.get("version") != 1
    ):
        raise ActivationRejected("parent config identity drifted")
    expected_sources = _python_closure_inventory(config)
    sources = _mapping(envelope.get("python_sources"), "parent Python sources")
    if set(sources) != set(expected_sources):
        raise ActivationRejected("parent Python source inventory drifted")
    source_bytes: dict[str, bytes] = {}
    for relative, expected in expected_sources.items():
        item = _mapping(sources.get(relative), f"parent source: {relative}")
        if set(item) != {"sha256", "bytes_b64"} or item.get("sha256") != expected:
            raise ActivationRejected(f"parent source identity drifted: {relative}")
        source = _decode_base64(item.get("bytes_b64"), f"parent source: {relative}")
        if _sha256(source) != expected:
            raise ActivationRejected(f"parent source digest drifted: {relative}")
        source_bytes[relative] = source
    bundle = _mapping(envelope.get("activation_bundle"), "parent activation bundle")
    configured_bundle = _mapping(config.get("bundle"), "activation bundle")
    configured_members = configured_bundle.get("members")
    if (
        set(bundle) != {"outer_sha256", "inner_sha256", "member_count"}
        or not isinstance(configured_members, list)
        or bundle.get("member_count") != len(configured_members)
        or (
            bundle.get("outer_sha256") is not None
            and not _is_digest(bundle.get("outer_sha256"))
        )
        or (
            bundle.get("inner_sha256") is not None
            and not _is_digest(bundle.get("inner_sha256"))
        )
    ):
        raise ActivationRejected("parent activation bundle identity drifted")
    execution_raw = _mapping(
        envelope.get("execution_authority"),
        "parent execution authority",
    )
    if set(execution_raw) != {
        "execution_outer_sha256",
        "execution_review_sha256",
        "static_authority_sha256",
    } or not all(_is_digest(value) for value in execution_raw.values()):
        raise ActivationRejected("parent execution authority drifted")
    execution = {key: str(value) for key, value in execution_raw.items()}
    return (
        config,
        config_raw,
        bundle,
        execution,
        expected_sources,
        source_bytes,
    )


def _verify_fresh_pycache_prefix(raw: object) -> tuple[Path, os.stat_result]:
    if not isinstance(raw, str) or not raw or not Path(raw).is_absolute():
        raise ActivationRejected("fresh bytecode-cache prefix is invalid")
    path = Path(raw)
    try:
        metadata = os.lstat(path)
        attributes = int(getattr(metadata, "st_file_attributes", 0))
        with os.scandir(path) as entries:
            first_entry = next(entries, None)
    except OSError as error:
        raise ActivationRejected(
            "fresh bytecode-cache prefix is unavailable"
        ) from error
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or attributes & 0x400
        or first_entry is not None
        or sys.pycache_prefix != raw
        or sys.flags.isolated != 1
        or sys.flags.dont_write_bytecode != 1
        or sys.flags.no_site != 1
    ):
        raise ActivationRejected("fresh bytecode-cache isolation drifted")
    return path, metadata


def _dependency_paths_after_verification() -> list[str]:
    paths: list[str] = []
    candidates = {
        raw
        for raw in (
            sysconfig.get_path("purelib"),
            sysconfig.get_path("platlib"),
        )
        if raw
    }
    for raw in sorted(candidates, key=str.encode):
        path = Path(raw).absolute()
        try:
            metadata = os.lstat(path)
        except OSError as error:
            raise ActivationRejected(
                f"dependency path is unavailable: {path}"
            ) from error
        attributes = int(getattr(metadata, "st_file_attributes", 0))
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or attributes & 0x400
        ):
            raise ActivationRejected(f"dependency path is not ordinary: {path}")
        paths.append(str(path))
    if not paths:
        raise ActivationRejected("no verified dependency path is available")
    return paths


def _module_name(relative: str) -> tuple[str, bool]:
    path = Path(relative)
    if path.suffix != ".py" or not path.parts:
        raise ActivationRejected(f"invalid Python source member: {relative}")
    if path.name == "__init__.py":
        parts = path.parts[:-1]
        is_package = True
    else:
        parts = (*path.parts[:-1], path.stem)
        is_package = False
    if not parts or any(not part.isidentifier() for part in parts):
        raise ActivationRejected(f"invalid Python module path: {relative}")
    return ".".join(parts), is_package


class _VerifiedSourceLoader(importlib.abc.Loader):
    def __init__(
        self,
        *,
        fullname: str,
        relative: str,
        raw: bytes,
        is_package: bool,
        executed: dict[str, str],
    ) -> None:
        self.fullname = fullname
        self.relative = relative
        self.raw = raw
        self.is_package = is_package
        self.executed = executed

    def create_module(self, spec: object) -> None:
        del spec

    def exec_module(self, module: object) -> None:
        namespace = vars(module)
        source_path = ROOT / self.relative
        namespace["__file__"] = str(source_path)
        namespace["__cached__"] = None
        if self.is_package:
            namespace["__path__"] = []
        self.executed[self.fullname] = self.relative
        code = compile(
            self.raw,
            str(source_path),
            "exec",
            dont_inherit=True,
        )
        exec(code, namespace)  # noqa: S102


class _VerifiedSourceFinder(importlib.abc.MetaPathFinder):
    def __init__(
        self,
        source_bytes: Mapping[str, bytes],
        executed: dict[str, str],
    ) -> None:
        self.sources: dict[str, tuple[str, bytes, bool]] = {}
        self.executed = executed
        self.protected_roots: set[str] = set()
        for relative, raw in source_bytes.items():
            fullname, is_package = _module_name(relative)
            if fullname in self.sources:
                raise ActivationRejected(f"duplicate Python module: {fullname}")
            self.sources[fullname] = (relative, raw, is_package)
            self.protected_roots.add(fullname.split(".", 1)[0])

    def find_spec(
        self,
        fullname: str,
        path: object = None,
        target: object = None,
    ) -> object:
        del path, target
        item = self.sources.get(fullname)
        if item is None:
            if fullname.split(".", 1)[0] in self.protected_roots:
                raise ModuleNotFoundError(
                    f"unregistered verified-source module blocked: {fullname}"
                )
            return None
        relative, raw, is_package = item
        loader = _VerifiedSourceLoader(
            fullname=fullname,
            relative=relative,
            raw=raw,
            is_package=is_package,
            executed=self.executed,
        )
        return importlib.util.spec_from_loader(
            fullname,
            loader,
            origin=str(ROOT / relative),
            is_package=is_package,
        )


def _local_module_paths() -> dict[str, str]:
    result: dict[str, str] = {}
    repository_root = ROOT.resolve()
    for name, module in tuple(sys.modules.items()):
        raw = getattr(module, "__file__", None)
        if not isinstance(raw, str):
            continue
        path = Path(raw)
        try:
            relative = path.resolve().relative_to(repository_root).as_posix()
        except (OSError, ValueError):
            continue
        if relative.endswith((".pyc", ".pyo")):
            relative = relative[:-1]
        result[name] = relative
    return result


def _require_clean_preimport() -> None:
    allowed = {BOOTSTRAP_RELATIVE}
    unexpected = set(_local_module_paths().values()) - allowed
    if unexpected:
        raise ActivationRejected(
            f"project module loaded before closure verification: {sorted(unexpected)}"
        )


def _verify_postimport_modules(
    closure: Mapping[str, str],
    *,
    expected_probe_members: set[str],
    source_bytes: Mapping[str, bytes],
    executed: Mapping[str, str],
) -> dict[str, object]:
    observed = _local_module_paths()
    observed_paths = set(observed.values())
    if observed_paths != expected_probe_members:
        raise ActivationRejected(
            "post-import project module inventory drifted: "
            f"missing={sorted(expected_probe_members - observed_paths)}, "
            f"extra={sorted(observed_paths - expected_probe_members)}"
        )
    required = {BOOTSTRAP_RELATIVE, CONTROLLER_RELATIVE, EXECUTION_CORE_RELATIVE}
    if not required.issubset(observed_paths):
        raise ActivationRejected("required post-import module is absent")
    expected_loaded = expected_probe_members - {BOOTSTRAP_RELATIVE}
    if set(executed.values()) != expected_loaded:
        raise ActivationRejected("verified source loader inventory drifted")
    for name, relative in observed.items():
        if relative != BOOTSTRAP_RELATIVE and executed.get(name) != relative:
            raise ActivationRejected(f"module bypassed verified source loader: {name}")
        raw = source_bytes[relative]
        if _sha256(raw) != closure[relative]:
            raise ActivationRejected(f"post-import module SHA-256 drifted: {relative}")
    return {
        "observed_module_count": len(observed_paths),
        "observed_modules": sorted(observed_paths, key=str.encode),
    }


def _isolated_python_flags(pycache_prefix: Path) -> list[str]:
    if not pycache_prefix.is_absolute():
        raise ActivationRejected("bytecode-cache prefix must be absolute")
    return [
        "-I",
        "-B",
        "-S",
        "-X",
        f"pycache_prefix={pycache_prefix}",
    ]


def _fresh_probe_command(
    pycache_prefix: Path,
    *,
    envelope_sha256: str,
) -> list[str]:
    if not _is_digest(envelope_sha256):
        raise ActivationRejected("parent envelope digest is invalid")
    return [
        sys.executable,
        *_isolated_python_flags(pycache_prefix),
        "-c",
        _STAGE0_SOURCE,
        envelope_sha256,
        BOOTSTRAP_RELATIVE,
        str(ROOT / BOOTSTRAP_RELATIVE),
        str(pycache_prefix),
    ]


def _terminate_probe(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    failures: list[BaseException] = []
    try:
        process.terminate()
    except BaseException as error:  # noqa: BLE001
        failures.append(error)
    try:
        process.wait(timeout=2)
    except BaseException as error:  # noqa: BLE001
        failures.append(error)
    if process.poll() is not None:
        return
    try:
        process.kill()
    except BaseException as error:  # noqa: BLE001
        failures.append(error)
    try:
        process.wait(timeout=2)
    except BaseException as error:  # noqa: BLE001
        failures.append(error)
    if process.poll() is None:
        cause = failures[-1] if failures else None
        raise ActivationRejected("fresh-process child could not be reaped") from cause


def _internal_probe(expected_pycache_prefix: str | None) -> dict[str, object]:
    (
        config,
        _config_raw,
        bundle,
        execution,
        closure,
        source_bytes,
    ) = _decode_parent_envelope(globals().get("_PARENT_ENVELOPE_RAW"))
    if _verify_execution_authority(config) != execution:
        raise ActivationRejected("child execution authority differs from parent")
    _require_clean_preimport()
    if "site" in sys.modules:
        raise ActivationRejected("site initialization ran before project verification")
    _pycache_path, pycache_before = _verify_fresh_pycache_prefix(
        expected_pycache_prefix
    )
    sys.path.extend(_dependency_paths_after_verification())
    executed: dict[str, str] = {}
    finder = _VerifiedSourceFinder(source_bytes, executed)
    sys.meta_path.insert(0, finder)
    try:
        from experiments import (
            run_rq2_joint_deliverability_activation_v1 as controller,
        )

        runtime = controller.validate_imported_runtime(
            execution,
            repository_root=ROOT,
        )

        _pycache_path_after, pycache_after = _verify_fresh_pycache_prefix(
            expected_pycache_prefix
        )
        if not os.path.samestat(pycache_before, pycache_after):
            raise ActivationRejected("fresh bytecode-cache identity drifted")
        closure_contract = _mapping(config.get("python_closure"), "Python closure")
        imported = _verify_postimport_modules(
            closure,
            expected_probe_members=set(closure_contract["postimport_probe_members"]),
            source_bytes=source_bytes,
            executed=executed,
        )
        executed_members = sorted(
            {BOOTSTRAP_RELATIVE, *executed.values()},
            key=str.encode,
        )
    finally:
        sys.meta_path.remove(finder)
    return {
        "schema": "rq2_joint_deliverability_activation_fresh_probe_v1",
        "bundle_member_count": bundle["member_count"],
        "python_closure_member_count": len(closure),
        **imported,
        "runtime": runtime,
        "verified_source_member_count": len(source_bytes),
        "verified_source_sha256s": dict(
            sorted(closure.items(), key=lambda item: item[0].encode())
        ),
        "executed_source_members": executed_members,
        "bootstrap_executed_from_verified_bytes": True,
        "project_modules_imported_from_verified_bytes": True,
        "project_bytecode_cache_files_consumed": 0,
        "solver_calls": 0,
        "formal_result_files_written": 0,
    }


def _run_fresh_probe(
    *,
    envelope_raw: bytes,
    expected_bundle: Mapping[str, object],
    expected_execution: Mapping[str, str],
    expected_closure: Mapping[str, str],
    expected_probe_members: list[str],
) -> dict[str, object]:
    envelope_sha256 = _sha256(envelope_raw)
    with tempfile.TemporaryDirectory(prefix="rq2-activation-pycache-") as raw_cache:
        pycache_prefix = Path(raw_cache).absolute()
        pycache_before = os.lstat(pycache_prefix)
        process = subprocess.Popen(
            _fresh_probe_command(
                pycache_prefix,
                envelope_sha256=envelope_sha256,
            ),
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            stdout, stderr = process.communicate(
                input=envelope_raw,
                timeout=60,
            )
        except subprocess.TimeoutExpired as error:
            _terminate_probe(process)
            raise ActivationRejected("fresh-process validation timed out") from error
        except BaseException:
            _terminate_probe(process)
            raise
        pycache_after = os.lstat(pycache_prefix)
        with os.scandir(pycache_prefix) as entries:
            if next(entries, None) is not None:
                raise ActivationRejected("parent observed bytecode-cache writes")
        if not os.path.samestat(pycache_before, pycache_after):
            raise ActivationRejected("parent bytecode-cache identity drifted")
    if process.returncode != 0:
        raise ActivationRejected(
            "fresh-process validation failed: "
            + stderr.decode("utf-8", errors="replace").strip()[-2000:]
        )
    try:
        payload = _json_bytes(stdout, "fresh probe output")
    except ActivationRejected as error:
        raise ActivationRejected("fresh-process output is invalid") from error
    expected_modules = sorted(expected_probe_members, key=str.encode)
    runtime = _mapping(payload.get("runtime"), "fresh-process runtime")
    if set(payload) != {
        "schema",
        "bundle_member_count",
        "python_closure_member_count",
        "observed_module_count",
        "observed_modules",
        "runtime",
        "verified_source_member_count",
        "verified_source_sha256s",
        "executed_source_members",
        "bootstrap_executed_from_verified_bytes",
        "project_modules_imported_from_verified_bytes",
        "project_bytecode_cache_files_consumed",
        "solver_calls",
        "formal_result_files_written",
    } or set(runtime) != {
        "schema",
        "execution_outer_sha256",
        "execution_review_sha256",
        "static_authority_sha256",
        "registered_inputs_ready",
        "public_stage_surface",
        "solver_calls",
        "formal_result_files_written",
    }:
        raise ActivationRejected("fresh-process output schema drifted")
    if (
        payload.get("schema") != "rq2_joint_deliverability_activation_fresh_probe_v1"
        or payload.get("bundle_member_count") != expected_bundle.get("member_count")
        or payload.get("python_closure_member_count") != len(expected_closure)
        or payload.get("verified_source_member_count") != len(expected_closure)
        or payload.get("verified_source_sha256s") != expected_closure
        or payload.get("observed_module_count") != len(expected_modules)
        or payload.get("observed_modules") != expected_modules
        or payload.get("executed_source_members") != expected_modules
        or payload.get("solver_calls") != 0
        or payload.get("formal_result_files_written") != 0
        or payload.get("bootstrap_executed_from_verified_bytes") is not True
        or payload.get("project_modules_imported_from_verified_bytes") is not True
        or payload.get("project_bytecode_cache_files_consumed") != 0
        or runtime.get("execution_outer_sha256")
        != expected_execution.get("execution_outer_sha256")
        or runtime.get("execution_review_sha256")
        != expected_execution.get("execution_review_sha256")
        or runtime.get("static_authority_sha256")
        != expected_execution.get("static_authority_sha256")
        or runtime.get("schema")
        != "rq2_joint_deliverability_activation_import_validation_v1"
        or runtime.get("registered_inputs_ready") is not False
        or runtime.get("public_stage_surface") != "closed"
        or runtime.get("solver_calls") != 0
        or runtime.get("formal_result_files_written") != 0
    ):
        raise ActivationRejected("fresh-process validation contract drifted")
    return payload


def _authority_path(
    config: Mapping[str, object],
    name: str,
) -> tuple[Path, dict[str, object]]:
    authorities = _mapping(config.get("external_authorities"), "external authorities")
    item = _mapping(authorities.get(name), f"{name} authority")
    relative = _relative(item.get("path"), f"{name} authority path")
    return ROOT / relative, item


def _authority_json(
    config: Mapping[str, object],
    name: str,
) -> tuple[dict[str, object], bytes, dict[str, object]]:
    path, contract = _authority_path(config, name)
    raw = _stable(path)
    value = _json_bytes(raw, name)
    if value.get("schema") != contract.get("schema"):
        raise ActivationRejected(f"{name} authority schema drifted")
    return value, raw, contract


def _require_activation_review(
    config: Mapping[str, object],
) -> tuple[dict[str, object], str]:
    authorities = _mapping(config.get("external_authorities"), "external authorities")
    configured_contract = _mapping(
        authorities.get("activation_review"),
        "activation review contract",
    )
    if configured_contract != _expected_activation_review_contract():
        raise ActivationRejected("activation review contract drifted")
    chain = _verify_bundle(config, require_sealed=True)
    value, raw, _contract = _authority_json(config, "activation_review")
    reviewed = _mapping(value.get("reviewed_subject"), "activation reviewed subject")
    effect = _mapping(value.get("effect"), "activation review effect")
    conclusion = _mapping(
        value.get("review_conclusion"), "activation review conclusion"
    )
    lifecycle = _mapping(config.get("lifecycle"), "activation lifecycle")
    sealed_on = lifecycle.get("sealed_on")
    reviewed_on = value.get("reviewed_on")
    try:
        parsed_sealed_on = datetime.date.fromisoformat(str(sealed_on))
        parsed_reviewed_on = datetime.date.fromisoformat(str(reviewed_on))
    except ValueError as error:
        raise ActivationRejected("activation review date drifted") from error
    if (
        set(value)
        != {
            "schema",
            "reviewed_on",
            "review_scope",
            "reviewer_role",
            "reviewer_model",
            "verdict",
            "reviewed_subject",
            "review_conclusion",
            "effect",
        }
        or value.get("schema") != ACTIVATION_REVIEW_SCHEMA
        or value.get("review_scope") != ACTIVATION_REVIEW_SCOPE
        or value.get("verdict") != "PASS"
        or value.get("reviewer_role") != "independent_sol_reviewer"
        or value.get("reviewer_model") != ACTIVATION_REVIEW_MODEL
        or not isinstance(sealed_on, str)
        or parsed_sealed_on.isoformat() != sealed_on
        or not isinstance(reviewed_on, str)
        or parsed_reviewed_on.isoformat() != reviewed_on
        or parsed_reviewed_on < parsed_sealed_on
        or set(reviewed)
        != {
            "outer_path",
            "outer_sha256",
            "inner_sha256",
            "sealed_member_count",
        }
        or reviewed.get("outer_path") != OUTER_RELATIVE
        or reviewed.get("outer_sha256") != chain["outer_sha256"]
        or reviewed.get("inner_sha256") != chain["inner_sha256"]
        or reviewed.get("sealed_member_count") != chain["member_count"]
        or set(conclusion)
        != {
            "blocker_findings",
            "major_findings",
            "minor_findings",
        }
        or conclusion.get("blocker_findings") != []
        or conclusion.get("major_findings") != []
        or conclusion.get("minor_findings") != []
        or effect != ACTIVATION_REVIEW_EFFECT
    ):
        raise ActivationRejected("activation review authority drifted")
    return value, _sha256(raw)


def _blockers(config: Mapping[str, object]) -> list[str]:
    names = (
        ("activation_review", "missing_activation_review_receipt"),
        ("dispatched_grid_manifest", "missing_dispatched_grid_package"),
        ("runtime", "missing_execution_machine_runtime_receipt"),
        ("execution_activation", "missing_execution_activation_authority"),
        ("formal_run", "missing_user_formal_run_authorization"),
    )
    blockers: list[str] = []
    for name, blocker in names:
        path, _contract = _authority_path(config, name)
        if _path_is_present_or_aliased(path):
            if name == "activation_review":
                _require_activation_review(config)
            else:
                raise ActivationRejected(
                    f"closed external authority unexpectedly exists: {name}"
                )
        else:
            blockers.append(blocker)
    return blockers


def validate_only() -> dict[str, object]:
    config, config_raw = _load_config()
    lifecycle = _mapping(config.get("lifecycle"), "activation lifecycle")
    require_sealed = lifecycle.get("status") == "SEALED_READY_FOR_INDEPENDENT_REVIEW"
    bundle = _verify_bundle(config, require_sealed=require_sealed)
    execution = _verify_execution_authority(config)
    closure, source_bytes = _read_python_closure(config)
    closure_contract = _mapping(config.get("python_closure"), "Python closure")
    expected_probe_members = list(closure_contract["postimport_probe_members"])
    envelope_raw = _build_parent_envelope(
        config_raw=config_raw,
        bundle=bundle,
        execution=execution,
        closure=closure,
        source_bytes=source_bytes,
    )
    probe = _run_fresh_probe(
        envelope_raw=envelope_raw,
        expected_bundle=bundle,
        expected_execution=execution,
        expected_closure=closure,
        expected_probe_members=expected_probe_members,
    )
    config_after, config_raw_after = _load_config()
    lifecycle_after = _mapping(config_after.get("lifecycle"), "activation lifecycle")
    bundle_after = _verify_bundle(
        config_after,
        require_sealed=(
            lifecycle_after.get("status") == "SEALED_READY_FOR_INDEPENDENT_REVIEW"
        ),
    )
    execution_after = _verify_execution_authority(config_after)
    closure_after, source_bytes_after = _read_python_closure(config_after)
    if (
        config_raw_after != config_raw
        or config_after != config
        or _bundle_identity(bundle_after) != _bundle_identity(bundle)
        or execution_after != execution
        or closure_after != closure
        or source_bytes_after != source_bytes
    ):
        raise ActivationRejected("parent state changed across fresh-process probe")
    return {
        "schema": "rq2_joint_deliverability_activation_validation_v1",
        "lifecycle": lifecycle["status"],
        "bundle_member_count": bundle["member_count"],
        "python_closure_member_count": len(closure),
        **execution,
        "fresh_process": probe,
        "blockers": _blockers(config),
        "formal_execution_ready": False,
        "formal_result": False,
        "paper_claim": False,
        "security_certified": False,
        "solver_calls": 0,
        "formal_result_files_written": 0,
    }


def execute() -> dict[str, object]:
    raise ActivationRejected(
        "activation v1 is review-only: sealed execution v3 keeps grid, runtime, "
        "and activation authorities null; a new bound execution successor and "
        "separate formal-run authorization are required"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--validate-only", action="store_true")
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--internal-probe", action="store_true")
    parser.add_argument("--expected-pycache-prefix")
    arguments = parser.parse_args(argv)
    if arguments.validate_only:
        payload = validate_only()
    elif arguments.execute:
        payload = execute()
    else:
        payload = _internal_probe(arguments.expected_pycache_prefix)
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
