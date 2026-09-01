"""Fail-closed evidence contract for isolated Vnext successor V8.

V8 changes only resource-monitor control priority: watchdog and due-slot
classification precede child-exit polling, while a clean child exit remains
valid before the next scheduled slot.  The scientific protocol, thresholds,
order, solver semantics, and security status remain unchanged.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import stat
import threading
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from experiments import (
    rq2_public_grid_two_block_pilot_vnext_execution_contract_v7 as predecessor,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_v8.json"
INNER = ROOT / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_v8.SHA256SUMS.json"
OUTER = ROOT / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_v8.OUTER.SHA256SUMS.json"
REVIEW = ROOT / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_review_pass_v8.json"
PUBLIC_KEY = ROOT / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_v8_ots_public_key.json"
V7_REVIEW_ESCALATE = ROOT / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_review_escalate_v7.json"
V7_REVIEW_EVIDENCE = ROOT / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_review_evidence_escalate_v7.json"
V7_KEY_REVOCATION = ROOT / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_v7_ots_key_revocation_v1.json"
BLOCKS = predecessor.BLOCKS
RESOURCE_SAMPLE_INTERVAL_NS = 5_000_000_000
SAMPLE_INTERVAL_NS = RESOURCE_SAMPLE_INTERVAL_NS
OBSERVATION_JITTER_BUDGET_NS = 1_000_000_000
MONITOR_POLL_INTERVAL_NS = 50_000_000
OWNED_TERMINATION_GRACE_NS = 2_000_000_000
NORMAL_LAST_SAMPLE_TO_EXIT_MAX_NS = 6_000_000_000
MAX_DETECTION_OVERRUN_NS = 1_000_000_000
OWNED_TERMINATION_SOURCE = {
    "path": "experiments/run_rq2_public_grid_two_block_pilot_activation_transport_v4.py",
    "sha256": "04bfb1ac4deb51e1708c1eb668317b26e4cf2f3af68c35f18b96fb79f3af78a3",
}
PRIVATE_COMMIT_LIMIT_BYTES = 8 * 1024**3
SYSTEM_COMMIT_RESERVE_BYTES = 2 * 1024**3
WATCHDOG_NS = 21_600 * 1_000_000_000
PUBLIC_KEY_KEYS = {
    "schema",
    "version",
    "algorithm",
    "digest_algorithm",
    "secret_derivation",
    "public_derivation",
    "public_key_commitment",
    "signature_representation",
    "key_id",
    "public_key_sha256",
    "one_time",
    "same_os_user_pre_execution_lease_exfiltration_out_of_scope",
    "security_certified",
}


class ContractRejected(RuntimeError):
    """A frozen evidence or execution invariant failed closed."""


exact_json_bytes = predecessor.exact_json_bytes
sha256_bytes = predecessor.sha256_bytes
process_create_time_ns = predecessor.process_create_time_ns
observe_pipe_endpoint = predecessor.observe_pipe_endpoint
write_frame = predecessor.write_frame
read_frame = predecessor.read_frame
require_eof = predecessor.require_eof


def read_stable(path: Path) -> bytes:
    try:
        return predecessor.read_stable(path)
    except Exception as exc:
        raise ContractRejected(f"stable ordinary-file read rejected: {path}") from exc


def _sha_file(path: Path) -> str:
    return sha256_bytes(read_stable(path))


def closure_mapping_sha256(mapping: Mapping[str, str]) -> str:
    if not isinstance(mapping, Mapping) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in mapping.items()
    ):
        raise ContractRejected("closure mapping malformed")
    return sha256_bytes(exact_json_bytes(dict(sorted(mapping.items()))))


def _load_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(read_stable(path))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ContractRejected(f"{label} JSON malformed") from exc
    if not isinstance(value, dict):
        raise ContractRejected(f"{label} object malformed")
    return value


def load_config() -> dict[str, Any]:
    value = _load_json(CONFIG, label="V8 config")
    resource = value.get("resource_contract", {})
    if (
        value.get("schema")
        != "rq2_public_grid_two_block_pilot_vnext_execution_successor_v8"
        or value.get("version") != 8
        or value.get("status")
        != "vnext_execution_successor_v8_ready_for_independent_review"
        or tuple(value.get("pilot", {}).get("blocks", ())) != BLOCKS
        or value.get("remediation_scope")
        != "new_isolated_versioned_v8_due_slot_poll_priority_not_v7_mutation_or_resume"
        or any(item is not False for item in value.get("gates", {}).values())
        or value.get("controller_authentication", {}).get("security_certified")
        is not False
        or resource.get("resource_authority_binding_before_monitor_start")
        is not True
        or resource.get(
            "resource_authority_pre_and_post_mapping_digest_must_match"
        )
        is not True
        or resource.get("resource_sampler_scope")
        != "one_owned_child_one_session_no_cross_child_or_session_reuse"
        or resource.get("resource_sampler_callback")
        != "exact_pid_create_time_same_pair_observation_only"
        or resource.get("resource_values_cached_between_slots") is not False
        or resource.get("global_watchdog_checked_before_child_exit_poll")
        is not True
        or resource.get("child_exit_poll_allowed_only_before_scheduled_slot")
        is not True
        or resource.get(
            "due_or_overdue_slot_cannot_be_bypassed_by_child_exit_poll"
        )
        is not True
        or resource.get("monitor_loop_priority")
        != "now_then_global_watchdog_then_slot_deadline_then_pre_slot_poll_then_strict_overdue_then_inclusive_exact_sample"
    ):
        raise ContractRejected("V8 config identity/gates drifted")
    return value


def _ordinary_tree_mapping(root: Path) -> dict[str, str]:
    if not root.is_dir() or root.is_symlink():
        raise ContractRejected(f"sealed artifact root unavailable: {root}")
    mapping: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        try:
            info = os.lstat(path)
        except OSError as exc:
            raise ContractRejected(f"sealed artifact unreadable: {path}") from exc
        if stat.S_ISDIR(info.st_mode):
            if path.is_symlink():
                raise ContractRejected(f"sealed artifact directory alias: {path}")
            continue
        if not stat.S_ISREG(info.st_mode) or path.is_symlink():
            raise ContractRejected(f"sealed artifact non-ordinary member: {path}")
        relative = path.relative_to(ROOT).as_posix()
        if relative in mapping:
            raise ContractRejected("sealed artifact duplicate path")
        mapping[relative] = _sha_file(path)
    return dict(sorted(mapping.items()))


def verify_v7_escalate_and_revocation() -> None:
    config = load_config()
    frozen = config["predecessor_v7"]
    named = {
        V7_REVIEW_ESCALATE: frozen["review_receipt_sha256"],
        V7_REVIEW_EVIDENCE: frozen["review_evidence_sha256"],
        V7_KEY_REVOCATION: frozen["key_revocation_sha256"],
        ROOT / frozen["revoked_tombstone_path"]: frozen[
            "revoked_tombstone_sha256"
        ],
    }
    if any(_sha_file(path) != digest for path, digest in named.items()):
        raise ContractRejected("sealed V7 review/revocation bytes drifted")
    review = _load_json(V7_REVIEW_ESCALATE, label="V7 ESCALATE receipt")
    evidence = _load_json(V7_REVIEW_EVIDENCE, label="V7 ESCALATE evidence")
    findings = review.get("findings")
    if (
        review.get("schema")
        != "rq2_public_grid_two_block_pilot_vnext_execution_successor_review_escalate_v7"
        or review.get("version") != 7
        or review.get("reviewer_role") != "independent_sol_reviewer"
        or review.get("verdict") != "ESCALATE"
        or review.get("reviewed_v7", {}).get("outer_sha256")
        != frozen["outer_sha256"]
        or review.get("reviewed_v7", {}).get("inner_sha256")
        != frozen["inner_sha256"]
        or review.get("reviewed_v7", {}).get("public_anchor_sha256")
        != frozen["public_anchor_sha256"]
        or review.get("reviewed_v7", {}).get("key_id") != frozen["key_id"]
        or not isinstance(findings, list)
        or len(findings) != 1
        or not isinstance(findings[0], Mapping)
        or findings[0].get("finding_id")
        != "DUE_RESOURCE_SLOT_BYPASSED_BY_CHILD_EXIT_POLL"
        or review.get("effect", {}).get("v7_execution_authorized") is not False
        or review.get("effect", {}).get("v8_versioned_cycle_only") is not True
        or evidence.get("schema")
        != "rq2_public_grid_two_block_pilot_vnext_execution_successor_review_evidence_escalate_v7"
        or evidence.get("version") != 1
        or evidence.get("authority") is not False
        or evidence.get("reviewed_outer_sha256") != frozen["outer_sha256"]
        or evidence.get("finding_id")
        != "DUE_RESOURCE_SLOT_BYPASSED_BY_CHILD_EXIT_POLL"
        or evidence.get("independent_reproducer", {}).get("persist_calls") != 0
        or evidence.get("independent_reproducer", {}).get(
            "resource_monitor_state_outcome"
        )
        is not None
        or evidence.get("effect", {}).get("opens_execution_gate") is not False
        or evidence.get("effect", {}).get("v8_versioned_cycle_only") is not True
    ):
        raise ContractRejected("V7 ESCALATE evidence binding/effect drifted")
    revocation = _load_json(V7_KEY_REVOCATION, label="V7 key revocation")
    tombstone = _load_json(
        ROOT / frozen["revoked_tombstone_path"], label="V7 revoked tombstone"
    )
    if (
        revocation.get("schema")
        != "rq2_public_grid_vnext_execution_successor_v7_ots_key_revocation_v1"
        or revocation.get("key_id") != frozen["key_id"]
        or revocation.get("public_key_sha256") != frozen["public_key_sha256"]
        or revocation.get("bound_review_receipt_sha256")
        != frozen["review_receipt_sha256"]
        or revocation.get("bound_review_evidence_sha256")
        != frozen["review_evidence_sha256"]
        or revocation.get("revoked_tombstone_sha256")
        != frozen["revoked_tombstone_sha256"]
        or revocation.get("operation", {}).get("private_seed_read") is not False
        or revocation.get("operation", {}).get("private_seed_copied") is not False
        or revocation.get("operation", {}).get("tombstone_contains_seed")
        is not False
        or revocation.get("effect", {}).get("state") != "REVOKED"
        or revocation.get("effect", {}).get("never_authorized") is not True
        or revocation.get("effect", {}).get("never_used_to_sign") is not True
        or tombstone.get("state") != "revoked"
        or tombstone.get("seed_present") is not False
        or tombstone.get("key_id") != frozen["key_id"]
        or (ROOT / frozen["revoked_tombstone_path"].replace(".consumed", ".lease")).exists()
    ):
        raise ContractRejected("V7 review evidence/key revocation drifted")


def verify_self_bundle() -> dict[str, str]:
    config = load_config()
    outer = _load_json(OUTER, label="V8 outer")
    inner_raw = read_stable(INNER)
    inner = _load_json(INNER, label="V8 inner")
    expected_members = set(config["bundle"]["members"])
    inner_relative = INNER.relative_to(ROOT).as_posix()
    if (
        set(outer) != {"schema", "files"}
        or outer.get("schema")
        != "rq2_public_grid_two_block_pilot_vnext_execution_successor_outer_v8"
        or outer.get("files") != {inner_relative: sha256_bytes(inner_raw)}
        or set(inner) != {"schema", "files"}
        or inner.get("schema")
        != "rq2_public_grid_two_block_pilot_vnext_execution_successor_bundle_v8"
        or set(inner.get("files", {})) != expected_members
        or len(expected_members) != config["bundle"]["exact_member_count"]
    ):
        raise ContractRejected("V8 non-cyclic bundle identity/inventory drifted")
    mapping = {
        OUTER.relative_to(ROOT).as_posix(): _sha_file(OUTER),
        inner_relative: sha256_bytes(inner_raw),
    }
    for relative in sorted(expected_members):
        digest = _sha_file(ROOT / relative)
        if inner["files"].get(relative) != digest:
            raise ContractRejected(f"V8 bundle member hash drifted: {relative}")
        mapping[relative] = digest
    if len(mapping) != config["bundle"]["self_mapping_exact_count"]:
        raise ContractRejected("V8 self mapping count drifted")
    return dict(sorted(mapping.items()))


def _merge_exact(*mappings: Mapping[str, str]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for mapping in mappings:
        for path, digest in mapping.items():
            if path in merged and merged[path] != digest:
                raise ContractRejected(f"authority duplicate hash conflict: {path}")
            merged[path] = digest
    return dict(sorted(merged.items()))


def verify_live_authorities() -> dict[str, str]:
    config = load_config()
    verify_v7_escalate_and_revocation()
    try:
        predecessor_mapping = predecessor.verify_live_authorities()
    except Exception as exc:
        raise ContractRejected("sealed V7/V8 live authority drifted") from exc
    mapping = _merge_exact(
        predecessor_mapping,
        verify_self_bundle(),
    )
    if len(mapping) != config["bundle"]["live_authority_exact_count"]:
        raise ContractRejected("V8 live authority exact count drifted")
    resource = config["resource_contract"]
    for path_key, hash_key in (
        ("owned_termination_source_path", "owned_termination_source_sha256"),
        (
            "owned_termination_source_outer_path",
            "owned_termination_source_outer_sha256",
        ),
    ):
        if _sha_file(ROOT / resource[path_key]) != resource[hash_key]:
            raise ContractRejected(f"owned termination source drifted: {path_key}")
    runtime = config["runtime"]
    for path_key, hash_key in (
        ("locked_python_executable", "locked_python_sha256"),
        ("highspy_package_init_path", "highspy_package_init_sha256"),
        ("highspy_python_source_path", "highspy_python_source_sha256"),
        ("highspy_binary_path", "highspy_binary_sha256"),
    ):
        path = Path(runtime[path_key])
        if _sha_file(path) != runtime[hash_key]:
            raise ContractRejected(f"locked runtime hash drifted: {path_key}")
    return mapping


def _lamport_secret(seed: bytes, index: int, bit: int) -> bytes:
    if len(seed) != 32 or not (0 <= index < 256) or bit not in (0, 1):
        raise ContractRejected("Lamport private input malformed")
    return hashlib.sha256(
        b"rq2-lamport-ots-v1/secret\0"
        + seed
        + index.to_bytes(2, "big")
        + bytes([bit])
    ).digest()


def _lamport_public(secret: bytes) -> str:
    return hashlib.sha256(b"rq2-lamport-ots-v1/public\0" + secret).hexdigest()


def _lamport_bits(digest_sha256: str) -> tuple[int, ...]:
    try:
        raw = bytes.fromhex(digest_sha256)
    except ValueError as exc:
        raise ContractRejected("Lamport message digest malformed") from exc
    if len(raw) != 32 or digest_sha256 != digest_sha256.lower():
        raise ContractRejected("Lamport message digest malformed")
    return tuple((raw[index // 8] >> (7 - index % 8)) & 1 for index in range(256))


def derive_lamport_public_key(seed: bytes) -> dict[str, str]:
    hashes = [
        [_lamport_public(_lamport_secret(seed, index, bit)) for bit in (0, 1)]
        for index in range(256)
    ]
    commitment = sha256_bytes(
        exact_json_bytes(
            {"algorithm": "lamport_sha256_seeded_v1", "public_hashes": hashes}
        )
    )
    key_id = hashlib.sha256(
        b"rq2-lamport-ots-v1/key-id\0" + bytes.fromhex(commitment)
    ).hexdigest()
    return {"key_id": key_id, "public_key_sha256": commitment}


def load_public_key() -> dict[str, Any]:
    config = load_config()
    value = _load_json(PUBLIC_KEY, label="Lamport public key")
    authority = config["controller_authentication"]
    if (
        set(value) != PUBLIC_KEY_KEYS
        or value.get("schema")
        != "rq2_public_grid_vnext_execution_successor_v8_lamport_ots_public_key"
        or value.get("version") != 1
        or value.get("algorithm") != "lamport_sha256_seeded_v1"
        or value.get("digest_algorithm") != "sha256"
        or value.get("key_id") != authority["key_id"]
        or value.get("public_key_sha256") != authority["public_key_sha256"]
        or value.get("one_time") is not True
        or value.get("same_os_user_pre_execution_lease_exfiltration_out_of_scope")
        is not True
        or value.get("security_certified") is not False
        or _sha_file(PUBLIC_KEY) != authority["public_key_file_sha256"]
    ):
        raise ContractRejected("Lamport public anchor drifted")
    expected_key_id = hashlib.sha256(
        b"rq2-lamport-ots-v1/key-id\0"
        + bytes.fromhex(value["public_key_sha256"])
    ).hexdigest()
    if expected_key_id != value["key_id"]:
        raise ContractRejected("Lamport public key id drifted")
    return value


def lamport_sign_digest(seed: bytes, digest_sha256: str) -> dict[str, Any]:
    public = derive_lamport_public_key(seed)
    selected: list[str] = []
    unselected: list[str] = []
    for index, bit in enumerate(_lamport_bits(digest_sha256)):
        selected.append(_lamport_secret(seed, index, bit).hex())
        unselected.append(_lamport_public(_lamport_secret(seed, index, 1 - bit)))
    return {
        "schema": "rq2_public_grid_vnext_execution_v8_lamport_signature",
        "algorithm": "lamport_sha256_seeded_v1",
        "key_id": public["key_id"],
        "digest_sha256": digest_sha256,
        "selected_preimages": selected,
        "unselected_public_hashes": unselected,
    }


def verify_lamport_signature(
    digest_sha256: str,
    signature: Mapping[str, Any],
    public_key: Mapping[str, Any] | None = None,
) -> None:
    public = load_public_key() if public_key is None else public_key
    expected_keys = {
        "schema",
        "algorithm",
        "key_id",
        "digest_sha256",
        "selected_preimages",
        "unselected_public_hashes",
    }
    if (
        not isinstance(signature, Mapping)
        or set(signature) != expected_keys
        or signature.get("schema")
        != "rq2_public_grid_vnext_execution_v8_lamport_signature"
        or signature.get("algorithm") != "lamport_sha256_seeded_v1"
        or signature.get("key_id") != public.get("key_id")
        or signature.get("digest_sha256") != digest_sha256
        or not isinstance(signature.get("selected_preimages"), list)
        or not isinstance(signature.get("unselected_public_hashes"), list)
        or len(signature["selected_preimages"]) != 256
        or len(signature["unselected_public_hashes"]) != 256
    ):
        raise ContractRejected("Lamport signature schema/binding rejected")
    hashes: list[list[str]] = []
    for index, bit in enumerate(_lamport_bits(digest_sha256)):
        try:
            selected = bytes.fromhex(signature["selected_preimages"][index])
        except (TypeError, ValueError) as exc:
            raise ContractRejected("Lamport signature preimage malformed") from exc
        other = signature["unselected_public_hashes"][index]
        if len(selected) != 32 or not isinstance(other, str) or len(other) != 64:
            raise ContractRejected("Lamport signature member malformed")
        pair = ["", ""]
        pair[bit] = _lamport_public(selected)
        pair[1 - bit] = other
        hashes.append(pair)
    commitment = sha256_bytes(
        exact_json_bytes(
            {"algorithm": "lamport_sha256_seeded_v1", "public_hashes": hashes}
        )
    )
    if commitment != public.get("public_key_sha256"):
        raise ContractRejected("Lamport signature verification failed")


PRIVATE_LEASE_KEYS = {
    "schema",
    "version",
    "state",
    "key_id",
    "public_key_sha256",
    "seed_hex",
    "one_time",
    "same_os_user_pre_execution_lease_exfiltration_out_of_scope",
    "security_certified",
}


RESOURCE_THRESHOLDS = {
    "child_private_commit_stop_bytes": PRIVATE_COMMIT_LIMIT_BYTES,
    "child_private_stop_comparison": "greater_than_or_equal",
    "system_commit_available_stop_bytes": SYSTEM_COMMIT_RESERVE_BYTES,
    "system_available_stop_comparison": "less_than_or_equal",
}


def resource_stop_reason(private_bytes: int, available_bytes: int) -> str | None:
    if type(private_bytes) is not int or private_bytes < 0 or type(available_bytes) is not int or available_bytes < 0:
        raise ContractRejected("resource sample value malformed")
    private = private_bytes >= PRIVATE_COMMIT_LIMIT_BYTES
    system = available_bytes <= SYSTEM_COMMIT_RESERVE_BYTES
    if private and system:
        return "private_and_system_commit_limits_reached"
    if private:
        return "private_commit_limit_reached"
    if system:
        return "system_commit_reserve_reached"
    return None


RESOURCE_SAMPLE_KEYS = {
    "sequence_index",
    "wall_time_ns",
    "monotonic_ns",
    "scheduled_monotonic_ns",
    "sample_deadline_monotonic_ns",
    "actual_observation_lateness_ns",
    "owned_identity",
    "child_private_commit_bytes",
    "system_commit_available_bytes",
    "thresholds",
    "computed_stop_reason",
}
DEADLINE_MISSED_KEYS = {
    "sequence_index",
    "scheduled_monotonic_ns",
    "sample_deadline_monotonic_ns",
    "detection_monotonic_ns",
    "detection_wall_time_ns",
    "detection_overrun_ns",
    "max_detection_overrun_ns",
    "phase",
    "owned_identity",
}
MISSED_SLOT_KEYS = {
    "sequence_index",
    "scheduled_monotonic_ns",
    "sample_deadline_monotonic_ns",
}
TERMINATION_EVIDENCE_KEYS = {
    "schema",
    "version",
    "termination_requested",
    "termination_request_monotonic_ns",
    "termination_request_wall_time_ns",
    "termination_end_monotonic_ns",
    "termination_end_wall_time_ns",
    "termination_duration_ns",
    "termination_action",
    "termination_completed",
    "termination_within_grace",
    "exact_owned_identity",
    "trigger_status",
    "trigger_reason",
    "missed_slot",
    "expected_due_sample_count",
    "actual_sample_count",
    "unobserved_due_slot_count",
    "owned_termination_grace_ns",
    "termination_duration_cap_ns",
    "sealed_owned_termination_source",
    "failure_reason",
}
TERMINATION_ACTIONS = {
    "terminate_only",
    "terminate_then_kill",
    "already_exited_before_signal",
    "termination_failed",
    "termination_result_malformed",
}
RESOURCE_JOURNAL_KEYS = {
    "schema",
    "version",
    "owned_identity",
    "resource_sampler_binding",
    "monitor_start_wall_time_ns",
    "monitor_start_monotonic_ns",
    "first_sample_observed",
    "first_sample_wall_time_ns",
    "first_sample_monotonic_ns",
    "exit_observed_wall_time_ns",
    "exit_observed_monotonic_ns",
    "watchdog_deadline_monotonic_ns",
    "watchdog_duration_ns",
    "sample_interval_ns",
    "observation_jitter_budget_ns",
    "scheduled_cadence_is_exact",
    "catch_up_sampling_allowed",
    "actual_observation_time_recorded_separately",
    "expected_sample_count_at_exit",
    "last_sample_wall_time_ns",
    "last_sample_monotonic_ns",
    "last_sample_to_exit_ns",
    "normal_last_sample_to_exit_max_ns",
    "max_detection_overrun_ns",
    "owned_termination_grace_ns",
    "deadline_to_detection_ns",
    "detection_to_termination_request_ns",
    "termination_request_to_end_ns",
    "termination_end_to_exit_observed_ns",
    "deadline_to_exit_observed_ns",
    "deadline_missed",
    "termination",
    "status",
    "reason",
    "honest_incomplete",
    "mathematical_infeasibility_inferred",
    "maximum_private_commit_bytes",
    "minimum_system_commit_available_bytes",
    "sample_count",
    "samples",
}
RESOURCE_SAMPLER_BINDING_KEYS = {
    "schema",
    "version",
    "binding_start_wall_time_ns",
    "binding_start_monotonic_ns",
    "binding_completed_wall_time_ns",
    "binding_completed_monotonic_ns",
    "monitor_start_after_binding",
    "expected_owned_identity",
    "pre_monitor_authority_mapping_sha256",
    "post_monitor_authority_mapping_sha256",
    "post_monitor_authority_verification_status",
    "post_monitor_authority_verification_error",
    "authority_mapping_match",
    "sampler_scope",
    "sampler_callback",
    "resource_values_cached_between_slots",
    "sampler_reused_across_child_or_session",
}


def _valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_resource_sampler_binding(
    value: Any, *, identity: Mapping[str, int], monitor_start_mono: int
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != RESOURCE_SAMPLER_BINDING_KEYS:
        raise ContractRejected("resource sampler authority binding keyset malformed")
    start_wall = value.get("binding_start_wall_time_ns")
    start_mono = value.get("binding_start_monotonic_ns")
    completed_wall = value.get("binding_completed_wall_time_ns")
    completed_mono = value.get("binding_completed_monotonic_ns")
    post_digest = value.get("post_monitor_authority_mapping_sha256")
    status = value.get("post_monitor_authority_verification_status")
    error = value.get("post_monitor_authority_verification_error")
    match = value.get("authority_mapping_match")
    if (
        value.get("schema")
        != "rq2_public_grid_resource_sampler_authority_binding_vnext_execution_v8"
        or value.get("version") != 1
        or any(
            type(item) is not int or item <= 0
            for item in (start_wall, start_mono, completed_wall, completed_mono)
        )
        or completed_wall < start_wall
        or completed_mono < start_mono
        or completed_mono > monitor_start_mono
        or value.get("monitor_start_after_binding") is not True
        or value.get("expected_owned_identity") != identity
        or not _valid_sha256(value.get("pre_monitor_authority_mapping_sha256"))
        or status not in {"verified", "verification_error"}
        or type(match) is not bool
        or value.get("sampler_scope")
        != "one_owned_child_one_session_no_cross_child_or_session_reuse"
        or value.get("sampler_callback")
        != "exact_pid_create_time_same_pair_observation_only"
        or value.get("resource_values_cached_between_slots") is not False
        or value.get("sampler_reused_across_child_or_session") is not False
    ):
        raise ContractRejected("resource sampler authority binding malformed")
    if status == "verified":
        if (
            not _valid_sha256(post_digest)
            or error is not None
            or match
            is not (
                post_digest == value.get("pre_monitor_authority_mapping_sha256")
            )
        ):
            raise ContractRejected("resource sampler post-authority binding drifted")
    elif (
        post_digest is not None
        or not isinstance(error, str)
        or not error
        or match is not False
    ):
        raise ContractRejected("resource sampler post-authority error malformed")
    return dict(value)


def validate_resource_journal(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != RESOURCE_JOURNAL_KEYS:
        raise ContractRejected("resource journal keyset malformed")
    identity = value.get("owned_identity")
    samples = value.get("samples")
    if (
        value.get("schema") != "rq2_public_grid_resource_journal_vnext_execution_v8"
        or value.get("version") != 8
        or not isinstance(identity, dict)
        or set(identity) != {"pid", "create_time_ns"}
        or any(type(identity[key]) is not int or identity[key] <= 0 for key in identity)
        or value.get("sample_interval_ns") != RESOURCE_SAMPLE_INTERVAL_NS
        or value.get("observation_jitter_budget_ns")
        != OBSERVATION_JITTER_BUDGET_NS
        or value.get("watchdog_duration_ns") != WATCHDOG_NS
        or value.get("scheduled_cadence_is_exact") is not True
        or value.get("catch_up_sampling_allowed") is not False
        or value.get("actual_observation_time_recorded_separately") is not True
        or not isinstance(samples, list)
        or value.get("sample_count") != len(samples)
        or value.get("mathematical_infeasibility_inferred") is not False
        or value.get("normal_last_sample_to_exit_max_ns")
        != NORMAL_LAST_SAMPLE_TO_EXIT_MAX_NS
        or value.get("max_detection_overrun_ns") != MAX_DETECTION_OVERRUN_NS
        or value.get("owned_termination_grace_ns")
        != OWNED_TERMINATION_GRACE_NS
    ):
        raise ContractRejected("resource journal identity/cadence malformed")
    start_mono = value["monitor_start_monotonic_ns"]
    start_wall = value["monitor_start_wall_time_ns"]
    deadline = value["watchdog_deadline_monotonic_ns"]
    if (
        any(type(item) is not int or item <= 0 for item in (start_mono, start_wall, deadline))
        or deadline != start_mono + WATCHDOG_NS
    ):
        raise ContractRejected("resource journal monitor timestamps malformed")
    _validate_resource_sampler_binding(
        value.get("resource_sampler_binding"),
        identity=identity,
        monitor_start_mono=start_mono,
    )
    maximum = 0
    minimum: int | None = None
    last_actual = start_mono - 1
    stop: str | None = None
    for index, sample in enumerate(samples):
        if not isinstance(sample, dict) or set(sample) != RESOURCE_SAMPLE_KEYS:
            raise ContractRejected("resource sample keyset malformed")
        private = sample["child_private_commit_bytes"]
        available = sample["system_commit_available_bytes"]
        expected_stop = resource_stop_reason(private, available)
        scheduled = start_mono + index * RESOURCE_SAMPLE_INTERVAL_NS
        sample_deadline = scheduled + OBSERVATION_JITTER_BUDGET_NS
        actual = sample["monotonic_ns"]
        lateness = actual - scheduled
        if (
            sample["sequence_index"] != index
            or sample["owned_identity"] != identity
            or sample["thresholds"] != RESOURCE_THRESHOLDS
            or sample["computed_stop_reason"] != expected_stop
            or sample["scheduled_monotonic_ns"] != scheduled
            or sample["sample_deadline_monotonic_ns"] != sample_deadline
            or sample["actual_observation_lateness_ns"] != lateness
            or not 0 <= lateness <= OBSERVATION_JITTER_BUDGET_NS
            or type(sample["wall_time_ns"]) is not int
            or sample["wall_time_ns"] <= 0
            or type(sample["monotonic_ns"]) is not int
            or actual <= last_actual
        ):
            raise ContractRejected("resource sample value/identity/timestamp/cadence drifted")
        if index > 0 and not (
            RESOURCE_SAMPLE_INTERVAL_NS - OBSERVATION_JITTER_BUDGET_NS
            <= actual - last_actual
            <= RESOURCE_SAMPLE_INTERVAL_NS + OBSERVATION_JITTER_BUDGET_NS
        ):
            raise ContractRejected("actual resource observation gap drifted")
        if stop is not None:
            raise ContractRejected("resource samples continued after stop")
        stop = expected_stop
        maximum = max(maximum, private)
        minimum = available if minimum is None else min(minimum, available)
        last_actual = actual
    if samples:
        if (
            value["first_sample_observed"] is not True
            or value["first_sample_wall_time_ns"] != samples[0]["wall_time_ns"]
            or value["first_sample_monotonic_ns"] != samples[0]["monotonic_ns"]
        ):
            raise ContractRejected("resource first-sample binding drifted")
    elif (
        value["first_sample_observed"] is not False
        or value["first_sample_wall_time_ns"] is not None
        or value["first_sample_monotonic_ns"] is not None
    ):
        raise ContractRejected("empty resource journal first-sample drifted")
    exit_mono = value["exit_observed_monotonic_ns"]
    if (
        value["maximum_private_commit_bytes"] != maximum
        or value["minimum_system_commit_available_bytes"] != minimum
        or type(value["exit_observed_wall_time_ns"]) is not int
        or type(value["exit_observed_monotonic_ns"]) is not int
        or exit_mono < last_actual
    ):
        raise ContractRejected("resource journal aggregate/exit binding drifted")
    expected_sample_count = (exit_mono - start_mono) // RESOURCE_SAMPLE_INTERVAL_NS + 1
    last_to_exit = exit_mono - last_actual if samples else None
    if (
        value["expected_sample_count_at_exit"] != expected_sample_count
        or value["last_sample_wall_time_ns"]
        != (samples[-1]["wall_time_ns"] if samples else None)
        or value["last_sample_monotonic_ns"]
        != (samples[-1]["monotonic_ns"] if samples else None)
        or value["last_sample_to_exit_ns"] != last_to_exit
    ):
        raise ContractRejected("resource expected-slot/exit-gap binding drifted")
    deadline_missed = value["deadline_missed"]
    if deadline_missed is not None and (
        not isinstance(deadline_missed, dict)
        or set(deadline_missed) != DEADLINE_MISSED_KEYS
        or deadline_missed["sequence_index"] != len(samples)
        or deadline_missed["owned_identity"] != identity
        or deadline_missed["scheduled_monotonic_ns"]
        != start_mono + len(samples) * RESOURCE_SAMPLE_INTERVAL_NS
        or deadline_missed["sample_deadline_monotonic_ns"]
        != deadline_missed["scheduled_monotonic_ns"]
        + OBSERVATION_JITTER_BUDGET_NS
        or deadline_missed["detection_monotonic_ns"]
        <= deadline_missed["sample_deadline_monotonic_ns"]
        or deadline_missed["detection_overrun_ns"]
        != deadline_missed["detection_monotonic_ns"]
        - deadline_missed["sample_deadline_monotonic_ns"]
        or deadline_missed["max_detection_overrun_ns"]
        != MAX_DETECTION_OVERRUN_NS
        or type(deadline_missed["detection_wall_time_ns"]) is not int
        or deadline_missed["detection_wall_time_ns"] <= 0
        or deadline_missed["phase"] not in {"before_sample", "sample_completion"}
    ):
        raise ContractRejected("resource deadline-missed evidence drifted")
    termination = value["termination"]
    if termination is not None:
        if not isinstance(termination, dict) or set(termination) != TERMINATION_EVIDENCE_KEYS:
            raise ContractRejected("resource termination evidence keyset malformed")
        request_mono = termination["termination_request_monotonic_ns"]
        end_mono = termination["termination_end_monotonic_ns"]
        duration = end_mono - request_mono
        missed_slot = termination["missed_slot"]
        if (
            termination["schema"]
            != "rq2_public_grid_owned_termination_evidence_vnext_execution_v8"
            or termination["version"] != 1
            or termination["termination_requested"] is not True
            or type(request_mono) is not int
            or type(end_mono) is not int
            or request_mono < start_mono
            or end_mono < request_mono
            or end_mono > exit_mono
            or type(termination["termination_request_wall_time_ns"]) is not int
            or type(termination["termination_end_wall_time_ns"]) is not int
            or termination["termination_request_wall_time_ns"] <= 0
            or termination["termination_end_wall_time_ns"]
            < termination["termination_request_wall_time_ns"]
            or termination["termination_duration_ns"] != duration
            or termination["termination_action"] not in TERMINATION_ACTIONS
            or type(termination["termination_completed"]) is not bool
            or termination["termination_within_grace"]
            is not (duration <= OWNED_TERMINATION_GRACE_NS)
            or termination["exact_owned_identity"] != identity
            or termination["expected_due_sample_count"] != expected_sample_count
            or termination["actual_sample_count"] != len(samples)
            or termination["unobserved_due_slot_count"]
            != expected_sample_count - len(samples)
            or termination["unobserved_due_slot_count"] < 0
            or termination["owned_termination_grace_ns"]
            != OWNED_TERMINATION_GRACE_NS
            or termination["termination_duration_cap_ns"]
            != OWNED_TERMINATION_GRACE_NS
            or termination["sealed_owned_termination_source"]
            != OWNED_TERMINATION_SOURCE
            or (
                termination["termination_completed"]
                and termination["termination_action"]
                in {"termination_failed", "termination_result_malformed"}
            )
            or (
                not termination["termination_completed"]
                and (
                    termination["termination_action"]
                    not in {"termination_failed", "termination_result_malformed"}
                    or not isinstance(termination["failure_reason"], str)
                    or not termination["failure_reason"]
                )
            )
            or (
                termination["termination_completed"]
                and termination["failure_reason"] is not None
            )
        ):
            raise ContractRejected("resource termination evidence drifted")
        if missed_slot is not None and (
            not isinstance(missed_slot, dict)
            or set(missed_slot) != MISSED_SLOT_KEYS
            or missed_slot["sequence_index"] != len(samples)
            or missed_slot["scheduled_monotonic_ns"]
            != start_mono + len(samples) * RESOURCE_SAMPLE_INTERVAL_NS
            or missed_slot["sample_deadline_monotonic_ns"]
            != missed_slot["scheduled_monotonic_ns"]
            + OBSERVATION_JITTER_BUDGET_NS
        ):
            raise ContractRejected("termination missed-slot evidence drifted")
        trigger_status = termination["trigger_status"]
        trigger_reason = termination["trigger_reason"]
        if (
            trigger_status
            not in {
                "resource_stop",
                "resource_sample_deadline_missed",
                "sampling_error",
                "timeout",
            }
            or (
                trigger_status == "resource_stop"
                and trigger_reason
                not in {
                    "private_commit_limit_reached",
                    "system_commit_reserve_reached",
                    "private_and_system_commit_limits_reached",
                }
            )
            or (
                trigger_status == "resource_sample_deadline_missed"
                and trigger_reason != "resource_sample_deadline_missed"
            )
            or (
                trigger_status == "sampling_error"
                and trigger_reason != "resource_sample_failed"
            )
            or (
                trigger_status == "timeout"
                and trigger_reason != "external_watchdog_reached"
            )
            or (
                deadline_missed is not None
                and request_mono < deadline_missed["detection_monotonic_ns"]
            )
        ):
            raise ContractRejected("resource termination trigger drifted")
    expected_deadline_to_detection = (
        deadline_missed["detection_overrun_ns"]
        if deadline_missed is not None
        else None
    )
    expected_detection_to_request = (
        termination["termination_request_monotonic_ns"]
        - deadline_missed["detection_monotonic_ns"]
        if deadline_missed is not None and termination is not None
        else None
    )
    expected_request_to_end = (
        termination["termination_duration_ns"] if termination is not None else None
    )
    expected_end_to_exit = (
        exit_mono - termination["termination_end_monotonic_ns"]
        if termination is not None
        else None
    )
    expected_deadline_to_exit = (
        exit_mono - deadline_missed["sample_deadline_monotonic_ns"]
        if deadline_missed is not None
        else None
    )
    if (
        value["deadline_to_detection_ns"] != expected_deadline_to_detection
        or value["detection_to_termination_request_ns"]
        != expected_detection_to_request
        or value["termination_request_to_end_ns"] != expected_request_to_end
        or value["termination_end_to_exit_observed_ns"] != expected_end_to_exit
        or value["deadline_to_exit_observed_ns"] != expected_deadline_to_exit
        or (expected_detection_to_request is not None and expected_detection_to_request < 0)
        or (expected_end_to_exit is not None and expected_end_to_exit < 0)
    ):
        raise ContractRejected("resource exact timestamp delta binding drifted")
    status = value["status"]
    reason = value["reason"]
    if status == "child_exited":
        if (
            not samples
            or stop is not None
            or reason is not None
            or value["honest_incomplete"] is not False
            or deadline_missed is not None
            or termination is not None
            or len(samples) != expected_sample_count
            or last_to_exit is None
            or not 0 <= last_to_exit <= NORMAL_LAST_SAMPLE_TO_EXIT_MAX_NS
        ):
            raise ContractRejected("successful resource outcome malformed")
    elif status == "resource_stop":
        if (
            stop is None
            or reason != stop
            or value["honest_incomplete"] is not True
            or deadline_missed is not None
            or termination is None
            or termination["trigger_status"] != status
            or termination["trigger_reason"] != reason
            or termination["missed_slot"] is not None
            or termination["termination_completed"] is not True
            or termination["termination_within_grace"] is not True
            or len(samples) != expected_sample_count
            or last_to_exit is None
            or last_to_exit < 0
        ):
            raise ContractRejected("resource-stop aggregate malformed")
    elif status == "resource_sample_deadline_missed":
        if (
            reason != "resource_sample_deadline_missed"
            or value["honest_incomplete"] is not True
            or deadline_missed is None
            or termination is None
            or termination["trigger_status"] != status
            or termination["trigger_reason"] != reason
            or termination["missed_slot"]
            != {
                key: deadline_missed[key]
                for key in MISSED_SLOT_KEYS
            }
            or termination["termination_completed"] is not True
            or termination["termination_within_grace"] is not True
            or not 0
            < deadline_missed["detection_overrun_ns"]
            <= MAX_DETECTION_OVERRUN_NS
            or len(samples) != expected_sample_count - 1
            or termination["unobserved_due_slot_count"] != 1
            or (samples and (last_to_exit is None or last_to_exit < 0))
        ):
            raise ContractRejected("deadline-missed resource outcome malformed")
    elif status in {"sampling_error", "timeout"}:
        expected_reason = {
            "sampling_error": "resource_sample_failed",
            "timeout": "external_watchdog_reached",
        }[status]
        if (
            reason != expected_reason
            or value["honest_incomplete"] is not True
            or deadline_missed is not None
            or termination is None
            or termination["trigger_status"] != status
            or termination["trigger_reason"] != reason
            or termination["missed_slot"] is None
            or termination["termination_completed"] is not True
            or termination["termination_within_grace"] is not True
            or len(samples) != expected_sample_count - 1
            or termination["unobserved_due_slot_count"] != 1
            or (samples and (last_to_exit is None or last_to_exit < 0))
        ):
            raise ContractRejected("incomplete resource outcome malformed")
    elif status == "child_exited_before_first_sample":
        if (
            reason != "no_successful_same_pair_sample"
            or value["honest_incomplete"] is not True
            or deadline_missed is not None
            or termination is not None
            or samples
        ):
            raise ContractRejected("pre-sample child exit outcome malformed")
    elif status == "termination_indeterminate":
        if (
            reason
            not in {
                "owned_identity_or_termination_failed",
                "owned_termination_grace_exceeded",
                "resource_sample_detection_overrun_exceeded",
            }
            or value["honest_incomplete"] is not True
            or termination is None
            or (
                reason == "resource_sample_detection_overrun_exceeded"
                and (
                    deadline_missed is None
                    or deadline_missed["detection_overrun_ns"]
                    <= MAX_DETECTION_OVERRUN_NS
                )
            )
            or (
                reason == "owned_termination_grace_exceeded"
                and termination["termination_within_grace"] is not False
            )
            or (
                reason == "owned_identity_or_termination_failed"
                and termination["termination_completed"] is not False
            )
        ):
            raise ContractRejected("termination-indeterminate outcome malformed")
    else:
        raise ContractRejected("resource journal status unregistered")
    return dict(value)


def validate_success_resource_journal(value: Mapping[str, Any]) -> dict[str, Any]:
    journal = validate_resource_journal(value)
    if (
        journal["status"] != "child_exited"
        or journal["honest_incomplete"] is not False
        or journal["resource_sampler_binding"]["authority_mapping_match"]
        is not True
    ):
        raise ContractRejected("successful resource authority/cadence gate failed")
    return journal


def synthetic_resource_journal_for_test(
    *,
    pid: int,
    create_time_ns: int,
    private_values: tuple[int, ...],
    available_values: tuple[int, ...],
    actual_offsets_ns: tuple[int, ...] | None = None,
) -> dict[str, Any]:
    if len(private_values) != len(available_values) or not private_values:
        raise ContractRejected("synthetic journal input malformed")
    start_mono = 1_000_000_000_000
    start_wall = 2_000_000_000_000
    offsets = actual_offsets_ns or tuple(0 for _ in private_values)
    if len(offsets) != len(private_values):
        raise ContractRejected("synthetic journal offset input malformed")
    identity = {"pid": pid, "create_time_ns": create_time_ns}
    sampler_binding = _synthetic_resource_sampler_binding(
        identity=identity, monitor_start_mono=start_mono, monitor_start_wall=start_wall
    )
    samples = []
    for index, (private, available, offset) in enumerate(
        zip(private_values, available_values, offsets, strict=True)
    ):
        scheduled = start_mono + index * RESOURCE_SAMPLE_INTERVAL_NS
        actual = scheduled + offset
        samples.append(
            {
                "sequence_index": index,
                "wall_time_ns": start_wall + index * RESOURCE_SAMPLE_INTERVAL_NS + offset,
                "monotonic_ns": actual,
                "scheduled_monotonic_ns": scheduled,
                "sample_deadline_monotonic_ns": scheduled
                + OBSERVATION_JITTER_BUDGET_NS,
                "actual_observation_lateness_ns": offset,
                "owned_identity": identity,
                "child_private_commit_bytes": private,
                "system_commit_available_bytes": available,
                "thresholds": RESOURCE_THRESHOLDS,
                "computed_stop_reason": resource_stop_reason(private, available),
            }
        )
    stop = samples[-1]["computed_stop_reason"]
    status = "resource_stop" if stop else "child_exited"
    exit_mono = samples[-1]["monotonic_ns"] + 1
    expected_count = (exit_mono - start_mono) // RESOURCE_SAMPLE_INTERVAL_NS + 1
    termination = None
    if stop is not None:
        termination = _synthetic_termination_evidence(
            identity=identity,
            trigger_status="resource_stop",
            trigger_reason=stop,
            request_mono=samples[-1]["monotonic_ns"],
            request_wall=samples[-1]["wall_time_ns"],
            duration_ns=1,
            missed_slot=None,
            expected_count=expected_count,
            actual_count=len(samples),
        )
    value = {
        "schema": "rq2_public_grid_resource_journal_vnext_execution_v8",
        "version": 8,
        "owned_identity": identity,
        "resource_sampler_binding": sampler_binding,
        "monitor_start_wall_time_ns": start_wall,
        "monitor_start_monotonic_ns": start_mono,
        "first_sample_observed": True,
        "first_sample_wall_time_ns": samples[0]["wall_time_ns"],
        "first_sample_monotonic_ns": samples[0]["monotonic_ns"],
        "exit_observed_wall_time_ns": samples[-1]["wall_time_ns"] + 1,
        "exit_observed_monotonic_ns": exit_mono,
        "watchdog_deadline_monotonic_ns": start_mono + WATCHDOG_NS,
        "watchdog_duration_ns": WATCHDOG_NS,
        "sample_interval_ns": RESOURCE_SAMPLE_INTERVAL_NS,
        "observation_jitter_budget_ns": OBSERVATION_JITTER_BUDGET_NS,
        "scheduled_cadence_is_exact": True,
        "catch_up_sampling_allowed": False,
        "actual_observation_time_recorded_separately": True,
        "expected_sample_count_at_exit": expected_count,
        "last_sample_wall_time_ns": samples[-1]["wall_time_ns"],
        "last_sample_monotonic_ns": samples[-1]["monotonic_ns"],
        "last_sample_to_exit_ns": 1,
        "normal_last_sample_to_exit_max_ns": NORMAL_LAST_SAMPLE_TO_EXIT_MAX_NS,
        "max_detection_overrun_ns": MAX_DETECTION_OVERRUN_NS,
        "owned_termination_grace_ns": OWNED_TERMINATION_GRACE_NS,
        "deadline_to_detection_ns": None,
        "detection_to_termination_request_ns": None,
        "termination_request_to_end_ns": (
            termination["termination_duration_ns"] if termination else None
        ),
        "termination_end_to_exit_observed_ns": (
            exit_mono - termination["termination_end_monotonic_ns"]
            if termination
            else None
        ),
        "deadline_to_exit_observed_ns": None,
        "deadline_missed": None,
        "termination": termination,
        "status": status,
        "reason": stop,
        "honest_incomplete": bool(stop),
        "mathematical_infeasibility_inferred": False,
        "maximum_private_commit_bytes": max(private_values),
        "minimum_system_commit_available_bytes": min(available_values),
        "sample_count": len(samples),
        "samples": samples,
    }
    return validate_resource_journal(value)


def _synthetic_termination_evidence(
    *,
    identity: dict[str, int],
    trigger_status: str,
    trigger_reason: str,
    request_mono: int,
    request_wall: int,
    duration_ns: int,
    missed_slot: dict[str, int] | None,
    expected_count: int,
    actual_count: int,
    action: str = "terminate_only",
    completed: bool = True,
    failure_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": "rq2_public_grid_owned_termination_evidence_vnext_execution_v8",
        "version": 1,
        "termination_requested": True,
        "termination_request_monotonic_ns": request_mono,
        "termination_request_wall_time_ns": request_wall,
        "termination_end_monotonic_ns": request_mono + duration_ns,
        "termination_end_wall_time_ns": request_wall + duration_ns,
        "termination_duration_ns": duration_ns,
        "termination_action": action,
        "termination_completed": completed,
        "termination_within_grace": duration_ns <= OWNED_TERMINATION_GRACE_NS,
        "exact_owned_identity": identity,
        "trigger_status": trigger_status,
        "trigger_reason": trigger_reason,
        "missed_slot": missed_slot,
        "expected_due_sample_count": expected_count,
        "actual_sample_count": actual_count,
        "unobserved_due_slot_count": expected_count - actual_count,
        "owned_termination_grace_ns": OWNED_TERMINATION_GRACE_NS,
        "termination_duration_cap_ns": OWNED_TERMINATION_GRACE_NS,
        "sealed_owned_termination_source": OWNED_TERMINATION_SOURCE,
        "failure_reason": failure_reason,
    }


def _synthetic_resource_sampler_binding(
    *, identity: dict[str, int], monitor_start_mono: int, monitor_start_wall: int
) -> dict[str, Any]:
    mapping_digest = "a" * 64
    return {
        "schema": (
            "rq2_public_grid_resource_sampler_authority_binding_"
            "vnext_execution_v8"
        ),
        "version": 1,
        "binding_start_wall_time_ns": monitor_start_wall - 2,
        "binding_start_monotonic_ns": monitor_start_mono - 2,
        "binding_completed_wall_time_ns": monitor_start_wall - 1,
        "binding_completed_monotonic_ns": monitor_start_mono - 1,
        "monitor_start_after_binding": True,
        "expected_owned_identity": identity,
        "pre_monitor_authority_mapping_sha256": mapping_digest,
        "post_monitor_authority_mapping_sha256": mapping_digest,
        "post_monitor_authority_verification_status": "verified",
        "post_monitor_authority_verification_error": None,
        "authority_mapping_match": True,
        "sampler_scope": "one_owned_child_one_session_no_cross_child_or_session_reuse",
        "sampler_callback": "exact_pid_create_time_same_pair_observation_only",
        "resource_values_cached_between_slots": False,
        "sampler_reused_across_child_or_session": False,
    }


def synthetic_deadline_missed_journal_for_test(
    *, pid: int, create_time_ns: int
) -> dict[str, Any]:
    start_mono = 1_000_000_000_000
    start_wall = 2_000_000_000_000
    observed = start_mono + OBSERVATION_JITTER_BUDGET_NS + 1
    identity = {"pid": pid, "create_time_ns": create_time_ns}
    missed_slot = {
        "sequence_index": 0,
        "scheduled_monotonic_ns": start_mono,
        "sample_deadline_monotonic_ns": (
            start_mono + OBSERVATION_JITTER_BUDGET_NS
        ),
    }
    termination = _synthetic_termination_evidence(
        identity=identity,
        trigger_status="resource_sample_deadline_missed",
        trigger_reason="resource_sample_deadline_missed",
        request_mono=observed,
        request_wall=start_wall + OBSERVATION_JITTER_BUDGET_NS + 1,
        duration_ns=1,
        missed_slot=missed_slot,
        expected_count=1,
        actual_count=0,
    )
    value = {
        "schema": "rq2_public_grid_resource_journal_vnext_execution_v8",
        "version": 8,
        "owned_identity": identity,
        "resource_sampler_binding": _synthetic_resource_sampler_binding(
            identity=identity,
            monitor_start_mono=start_mono,
            monitor_start_wall=start_wall,
        ),
        "monitor_start_wall_time_ns": start_wall,
        "monitor_start_monotonic_ns": start_mono,
        "first_sample_observed": False,
        "first_sample_wall_time_ns": None,
        "first_sample_monotonic_ns": None,
        "exit_observed_wall_time_ns": start_wall
        + OBSERVATION_JITTER_BUDGET_NS
        + 2,
        "exit_observed_monotonic_ns": observed + 1,
        "watchdog_deadline_monotonic_ns": start_mono + WATCHDOG_NS,
        "watchdog_duration_ns": WATCHDOG_NS,
        "sample_interval_ns": RESOURCE_SAMPLE_INTERVAL_NS,
        "observation_jitter_budget_ns": OBSERVATION_JITTER_BUDGET_NS,
        "scheduled_cadence_is_exact": True,
        "catch_up_sampling_allowed": False,
        "actual_observation_time_recorded_separately": True,
        "expected_sample_count_at_exit": 1,
        "last_sample_wall_time_ns": None,
        "last_sample_monotonic_ns": None,
        "last_sample_to_exit_ns": None,
        "normal_last_sample_to_exit_max_ns": NORMAL_LAST_SAMPLE_TO_EXIT_MAX_NS,
        "max_detection_overrun_ns": MAX_DETECTION_OVERRUN_NS,
        "owned_termination_grace_ns": OWNED_TERMINATION_GRACE_NS,
        "deadline_to_detection_ns": 1,
        "detection_to_termination_request_ns": 0,
        "termination_request_to_end_ns": 1,
        "termination_end_to_exit_observed_ns": 0,
        "deadline_to_exit_observed_ns": 2,
        "deadline_missed": {
            "sequence_index": 0,
            "scheduled_monotonic_ns": start_mono,
            "sample_deadline_monotonic_ns": start_mono
            + OBSERVATION_JITTER_BUDGET_NS,
            "detection_monotonic_ns": observed,
            "detection_wall_time_ns": start_wall
            + OBSERVATION_JITTER_BUDGET_NS
            + 1,
            "detection_overrun_ns": 1,
            "max_detection_overrun_ns": MAX_DETECTION_OVERRUN_NS,
            "phase": "before_sample",
            "owned_identity": identity,
        },
        "termination": termination,
        "status": "resource_sample_deadline_missed",
        "reason": "resource_sample_deadline_missed",
        "honest_incomplete": True,
        "mathematical_infeasibility_inferred": False,
        "maximum_private_commit_bytes": 0,
        "minimum_system_commit_available_bytes": None,
        "sample_count": 0,
        "samples": [],
    }
    return validate_resource_journal(value)


RESOURCE_MONITOR_OUTCOME_KEYS = {
    "schema",
    "version",
    "resource_journal",
    "persisted_path",
    "persisted_sha256",
    "readback_verified",
    "authority_mapping_match",
    "controller_acceptable",
}


def validate_resource_monitor_outcome(
    value: Mapping[str, Any], *, expected_path: str | None = None
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != RESOURCE_MONITOR_OUTCOME_KEYS:
        raise ContractRejected("resource monitor persisted outcome keyset malformed")
    journal = validate_resource_journal(value.get("resource_journal"))
    path = value.get("persisted_path")
    if (
        value.get("schema")
        != "rq2_public_grid_resource_monitor_persisted_outcome_vnext_execution_v8"
        or value.get("version") != 1
        or not isinstance(path, str)
        or not path
        or (expected_path is not None and path != expected_path)
        or value.get("persisted_sha256")
        != sha256_bytes(exact_json_bytes(journal))
        or value.get("readback_verified") is not True
        or value.get("authority_mapping_match")
        is not journal["resource_sampler_binding"]["authority_mapping_match"]
        or value.get("controller_acceptable")
        is not journal["resource_sampler_binding"]["authority_mapping_match"]
    ):
        raise ContractRejected("resource monitor persistence/readback binding drifted")
    return dict(value)


class ResourceMonitorState:
    """Controller-visible first-sample gate without exposing publication authority."""

    def __init__(self) -> None:
        self.ready = threading.Event()
        self.first_sample_success = False
        self.outcome: dict[str, Any] | None = None


RESOURCE_SAMPLER_PREBINDING_KEYS = {
    "schema",
    "version",
    "binding_start_wall_time_ns",
    "binding_start_monotonic_ns",
    "binding_completed_wall_time_ns",
    "binding_completed_monotonic_ns",
    "expected_owned_identity",
    "pre_monitor_authority_mapping_sha256",
    "sampler_scope",
    "sampler_callback",
    "resource_values_cached_between_slots",
    "sampler_reused_across_child_or_session",
}


def _validate_resource_sampler_prebinding(
    value: Mapping[str, Any], *, identity: Mapping[str, int]
) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != RESOURCE_SAMPLER_PREBINDING_KEYS:
        raise ContractRejected("resource sampler prebinding keyset malformed")
    start_wall = value.get("binding_start_wall_time_ns")
    start_mono = value.get("binding_start_monotonic_ns")
    completed_wall = value.get("binding_completed_wall_time_ns")
    completed_mono = value.get("binding_completed_monotonic_ns")
    if (
        value.get("schema")
        != "rq2_public_grid_resource_sampler_prebinding_vnext_execution_v8"
        or value.get("version") != 1
        or any(
            type(item) is not int or item <= 0
            for item in (start_wall, start_mono, completed_wall, completed_mono)
        )
        or completed_wall < start_wall
        or completed_mono < start_mono
        or value.get("expected_owned_identity") != identity
        or not _valid_sha256(value.get("pre_monitor_authority_mapping_sha256"))
        or value.get("sampler_scope")
        != "one_owned_child_one_session_no_cross_child_or_session_reuse"
        or value.get("sampler_callback")
        != "exact_pid_create_time_same_pair_observation_only"
        or value.get("resource_values_cached_between_slots") is not False
        or value.get("sampler_reused_across_child_or_session") is not False
    ):
        raise ContractRejected("resource sampler prebinding malformed")
    return dict(value)


def monitor_owned_child_resources_journal(
    process: Any,
    *,
    expected_pid: int,
    expected_create_time_ns: int,
    watchdog_duration_ns: int = WATCHDOG_NS,
    state: ResourceMonitorState,
    sample: Callable[[int, int], tuple[int, int]],
    monotonic_ns: Callable[[], int] = time.monotonic_ns,
    wall_time_ns: Callable[[], int] = time.time_ns,
    sleep: Callable[[float], None] = time.sleep,
    terminate: Callable[..., Mapping[str, Any]],
    sampler_prebinding: Mapping[str, Any],
    verify_post_authority: Callable[[], Mapping[str, str]],
    persist: Callable[[dict[str, Any]], Mapping[str, Any]],
    persistence_path: str,
) -> dict[str, Any]:
    if process.pid != expected_pid:
        raise ContractRejected("resource monitor target PID drifted")
    identity = {"pid": expected_pid, "create_time_ns": expected_create_time_ns}
    prebinding = _validate_resource_sampler_prebinding(
        sampler_prebinding, identity=identity
    )
    start_mono = monotonic_ns()
    start_wall = wall_time_ns()
    if prebinding["binding_completed_monotonic_ns"] > start_mono:
        raise ContractRejected("resource authority binding completed after monitor start")
    if watchdog_duration_ns != WATCHDOG_NS:
        raise ContractRejected("resource watchdog duration drifted")
    watchdog_deadline_monotonic_ns = start_mono + watchdog_duration_ns
    samples: list[dict[str, Any]] = []
    status = "child_exited"
    reason: str | None = None
    honest = False
    index = 0
    deadline_missed: dict[str, Any] | None = None
    termination: dict[str, Any] | None = None

    def missed_slot_for(current_index: int) -> dict[str, int]:
        scheduled = start_mono + current_index * RESOURCE_SAMPLE_INTERVAL_NS
        return {
            "sequence_index": current_index,
            "scheduled_monotonic_ns": scheduled,
            "sample_deadline_monotonic_ns": (
                scheduled + OBSERVATION_JITTER_BUDGET_NS
            ),
        }

    def request_termination(
        *,
        trigger_status: str,
        trigger_reason: str,
        missed_slot: dict[str, int] | None,
    ) -> dict[str, Any]:
        request_mono = monotonic_ns()
        request_wall = wall_time_ns()
        action = "termination_failed"
        completed = False
        failure_reason: str | None = None
        try:
            result = terminate(
                process,
                expected_pid=expected_pid,
                expected_create_time_ns=expected_create_time_ns,
            )
            if (
                not isinstance(result, Mapping)
                or set(result) != {"termination_action", "termination_completed"}
                or result.get("termination_action")
                not in {
                    "terminate_only",
                    "terminate_then_kill",
                    "already_exited_before_signal",
                }
                or result.get("termination_completed") is not True
            ):
                action = "termination_result_malformed"
                failure_reason = "termination_callback_result_malformed"
            else:
                action = str(result["termination_action"])
                completed = True
        except Exception as exc:  # noqa: BLE001 - preserve fail-closed evidence
            failure_reason = f"termination_callback_raised:{type(exc).__name__}"
        end_mono = monotonic_ns()
        end_wall = wall_time_ns()
        duration = end_mono - request_mono
        return {
            "schema": (
                "rq2_public_grid_owned_termination_evidence_vnext_execution_v8"
            ),
            "version": 1,
            "termination_requested": True,
            "termination_request_monotonic_ns": request_mono,
            "termination_request_wall_time_ns": request_wall,
            "termination_end_monotonic_ns": end_mono,
            "termination_end_wall_time_ns": end_wall,
            "termination_duration_ns": duration,
            "termination_action": action,
            "termination_completed": completed,
            "termination_within_grace": duration <= OWNED_TERMINATION_GRACE_NS,
            "exact_owned_identity": identity,
            "trigger_status": trigger_status,
            "trigger_reason": trigger_reason,
            "missed_slot": missed_slot,
            "expected_due_sample_count": 0,
            "actual_sample_count": len(samples),
            "unobserved_due_slot_count": 0,
            "owned_termination_grace_ns": OWNED_TERMINATION_GRACE_NS,
            "termination_duration_cap_ns": OWNED_TERMINATION_GRACE_NS,
            "sealed_owned_termination_source": OWNED_TERMINATION_SOURCE,
            "failure_reason": failure_reason,
        }
    try:
        while True:
            now = monotonic_ns()
            if now >= watchdog_deadline_monotonic_ns:
                status = "timeout"
                reason = "external_watchdog_reached"
                honest = True
                termination = request_termination(
                    trigger_status=status,
                    trigger_reason=reason,
                    missed_slot=missed_slot_for(index),
                )
                break
            scheduled = start_mono + index * RESOURCE_SAMPLE_INTERVAL_NS
            sample_deadline = scheduled + OBSERVATION_JITTER_BUDGET_NS
            if now < scheduled:
                if process.poll() is not None:
                    if not samples:
                        status = "child_exited_before_first_sample"
                        reason = "no_successful_same_pair_sample"
                        honest = True
                    break
                sleep(
                    min(
                        scheduled - now,
                        MONITOR_POLL_INTERVAL_NS,
                    )
                    / 1_000_000_000
                )
                continue
            if now > sample_deadline:
                deadline_missed = {
                    "sequence_index": index,
                    "scheduled_monotonic_ns": scheduled,
                    "sample_deadline_monotonic_ns": sample_deadline,
                    "detection_monotonic_ns": now,
                    "detection_wall_time_ns": wall_time_ns(),
                    "detection_overrun_ns": now - sample_deadline,
                    "max_detection_overrun_ns": MAX_DETECTION_OVERRUN_NS,
                    "phase": "before_sample",
                    "owned_identity": identity,
                }
                status = "resource_sample_deadline_missed"
                reason = "resource_sample_deadline_missed"
                honest = True
                termination = request_termination(
                    trigger_status=status,
                    trigger_reason=reason,
                    missed_slot=missed_slot_for(index),
                )
                break
            try:
                private, available = sample(expected_pid, expected_create_time_ns)
                observed_mono = monotonic_ns()
                observed_wall = wall_time_ns()
                stop = resource_stop_reason(private, available)
            except Exception:  # noqa: BLE001 - any sample failure is fail closed
                status = "sampling_error"
                reason = "resource_sample_failed"
                honest = True
                termination = request_termination(
                    trigger_status=status,
                    trigger_reason=reason,
                    missed_slot=missed_slot_for(index),
                )
                break
            if observed_mono > sample_deadline:
                deadline_missed = {
                    "sequence_index": index,
                    "scheduled_monotonic_ns": scheduled,
                    "sample_deadline_monotonic_ns": sample_deadline,
                    "detection_monotonic_ns": observed_mono,
                    "detection_wall_time_ns": observed_wall,
                    "detection_overrun_ns": observed_mono - sample_deadline,
                    "max_detection_overrun_ns": MAX_DETECTION_OVERRUN_NS,
                    "phase": "sample_completion",
                    "owned_identity": identity,
                }
                status = "resource_sample_deadline_missed"
                reason = "resource_sample_deadline_missed"
                honest = True
                termination = request_termination(
                    trigger_status=status,
                    trigger_reason=reason,
                    missed_slot=missed_slot_for(index),
                )
                break
            event = {
                "sequence_index": index,
                "wall_time_ns": observed_wall,
                "monotonic_ns": observed_mono,
                "scheduled_monotonic_ns": scheduled,
                "sample_deadline_monotonic_ns": sample_deadline,
                "actual_observation_lateness_ns": observed_mono - scheduled,
                "owned_identity": identity,
                "child_private_commit_bytes": private,
                "system_commit_available_bytes": available,
                "thresholds": RESOURCE_THRESHOLDS,
                "computed_stop_reason": stop,
            }
            samples.append(event)
            if index == 0:
                state.first_sample_success = stop is None
                state.ready.set()
            if stop is not None:
                status = "resource_stop"
                reason = stop
                honest = True
                termination = request_termination(
                    trigger_status=status,
                    trigger_reason=reason,
                    missed_slot=None,
                )
                break
            index += 1
        exit_mono = monotonic_ns()
        exit_wall = wall_time_ns()
        post_mapping_digest: str | None = None
        post_verification_status = "verification_error"
        post_verification_error: str | None = None
        mapping_match = False
        try:
            post_mapping = verify_post_authority()
            if not isinstance(post_mapping, Mapping):
                raise ContractRejected("post-monitor authority mapping malformed")
            post_mapping_digest = closure_mapping_sha256(post_mapping)
            post_verification_status = "verified"
            mapping_match = (
                post_mapping_digest
                == prebinding["pre_monitor_authority_mapping_sha256"]
            )
        except Exception as exc:  # noqa: BLE001 - persist fail-closed audit state
            post_verification_error = type(exc).__name__
        sampler_binding = {
            "schema": (
                "rq2_public_grid_resource_sampler_authority_binding_"
                "vnext_execution_v8"
            ),
            "version": 1,
            "binding_start_wall_time_ns": prebinding[
                "binding_start_wall_time_ns"
            ],
            "binding_start_monotonic_ns": prebinding[
                "binding_start_monotonic_ns"
            ],
            "binding_completed_wall_time_ns": prebinding[
                "binding_completed_wall_time_ns"
            ],
            "binding_completed_monotonic_ns": prebinding[
                "binding_completed_monotonic_ns"
            ],
            "monitor_start_after_binding": True,
            "expected_owned_identity": identity,
            "pre_monitor_authority_mapping_sha256": prebinding[
                "pre_monitor_authority_mapping_sha256"
            ],
            "post_monitor_authority_mapping_sha256": post_mapping_digest,
            "post_monitor_authority_verification_status": (
                post_verification_status
            ),
            "post_monitor_authority_verification_error": (
                post_verification_error
            ),
            "authority_mapping_match": mapping_match,
            "sampler_scope": prebinding["sampler_scope"],
            "sampler_callback": prebinding["sampler_callback"],
            "resource_values_cached_between_slots": prebinding[
                "resource_values_cached_between_slots"
            ],
            "sampler_reused_across_child_or_session": prebinding[
                "sampler_reused_across_child_or_session"
            ],
        }
        expected_count = (
            (exit_mono - start_mono) // RESOURCE_SAMPLE_INTERVAL_NS + 1
        )
        last_to_exit = (
            exit_mono - samples[-1]["monotonic_ns"] if samples else None
        )
        if termination is not None:
            termination["expected_due_sample_count"] = expected_count
            termination["actual_sample_count"] = len(samples)
            termination["unobserved_due_slot_count"] = expected_count - len(samples)
            if not termination["termination_completed"]:
                status = "termination_indeterminate"
                reason = "owned_identity_or_termination_failed"
            elif not termination["termination_within_grace"]:
                status = "termination_indeterminate"
                reason = "owned_termination_grace_exceeded"
            elif (
                deadline_missed is not None
                and deadline_missed["detection_overrun_ns"]
                > MAX_DETECTION_OVERRUN_NS
            ):
                status = "termination_indeterminate"
                reason = "resource_sample_detection_overrun_exceeded"
        outcome = {
            "schema": "rq2_public_grid_resource_journal_vnext_execution_v8",
            "version": 8,
            "owned_identity": identity,
            "resource_sampler_binding": sampler_binding,
            "monitor_start_wall_time_ns": start_wall,
            "monitor_start_monotonic_ns": start_mono,
            "first_sample_observed": bool(samples),
            "first_sample_wall_time_ns": samples[0]["wall_time_ns"] if samples else None,
            "first_sample_monotonic_ns": samples[0]["monotonic_ns"] if samples else None,
            "exit_observed_wall_time_ns": exit_wall,
            "exit_observed_monotonic_ns": exit_mono,
            "watchdog_deadline_monotonic_ns": watchdog_deadline_monotonic_ns,
            "watchdog_duration_ns": watchdog_duration_ns,
            "sample_interval_ns": RESOURCE_SAMPLE_INTERVAL_NS,
            "observation_jitter_budget_ns": OBSERVATION_JITTER_BUDGET_NS,
            "scheduled_cadence_is_exact": True,
            "catch_up_sampling_allowed": False,
            "actual_observation_time_recorded_separately": True,
            "expected_sample_count_at_exit": expected_count,
            "last_sample_wall_time_ns": (
                samples[-1]["wall_time_ns"] if samples else None
            ),
            "last_sample_monotonic_ns": (
                samples[-1]["monotonic_ns"] if samples else None
            ),
            "last_sample_to_exit_ns": last_to_exit,
            "normal_last_sample_to_exit_max_ns": (
                NORMAL_LAST_SAMPLE_TO_EXIT_MAX_NS
            ),
            "max_detection_overrun_ns": MAX_DETECTION_OVERRUN_NS,
            "owned_termination_grace_ns": OWNED_TERMINATION_GRACE_NS,
            "deadline_to_detection_ns": (
                deadline_missed["detection_overrun_ns"]
                if deadline_missed is not None
                else None
            ),
            "detection_to_termination_request_ns": (
                termination["termination_request_monotonic_ns"]
                - deadline_missed["detection_monotonic_ns"]
                if deadline_missed is not None and termination is not None
                else None
            ),
            "termination_request_to_end_ns": (
                termination["termination_duration_ns"]
                if termination is not None
                else None
            ),
            "termination_end_to_exit_observed_ns": (
                exit_mono - termination["termination_end_monotonic_ns"]
                if termination is not None
                else None
            ),
            "deadline_to_exit_observed_ns": (
                exit_mono - deadline_missed["sample_deadline_monotonic_ns"]
                if deadline_missed is not None
                else None
            ),
            "deadline_missed": deadline_missed,
            "termination": termination,
            "status": status,
            "reason": reason,
            "honest_incomplete": honest,
            "mathematical_infeasibility_inferred": False,
            "maximum_private_commit_bytes": max(
                (item["child_private_commit_bytes"] for item in samples), default=0
            ),
            "minimum_system_commit_available_bytes": min(
                (item["system_commit_available_bytes"] for item in samples), default=None
            ),
            "sample_count": len(samples),
            "samples": samples,
        }
        journal = validate_resource_journal(outcome)
        persisted = dict(persist(journal))
        state.outcome = validate_resource_monitor_outcome(
            persisted, expected_path=persistence_path
        )
        return state.outcome
    finally:
        state.ready.set()


def collect_solver_runtime_evidence(worker_identity: Mapping[str, int]) -> dict[str, Any]:
    config = load_config()
    runtime = config["runtime"]
    solver = config["science_authority"]["solver"]
    if set(worker_identity) != {"pid", "ppid", "create_time_ns"}:
        raise ContractRejected("solver runtime worker identity malformed")
    import highspy

    instance = highspy.Highs()
    value = {
        "schema": "rq2_public_grid_solver_runtime_evidence_vnext_execution_v8",
        "worker_identity": dict(worker_identity),
        "observed_wall_time_ns": time.time_ns(),
        "observed_monotonic_ns": time.monotonic_ns(),
        "locked_python_executable": str(Path(os.sys.executable).resolve()),
        "locked_python_sha256": _sha_file(Path(os.sys.executable)),
        "highspy_metadata_version": importlib.metadata.version("highspy"),
        "highs_runtime_api_version": instance.version(),
        "highs_runtime_version_components": {
            "major": instance.versionMajor(),
            "minor": instance.versionMinor(),
            "patch": instance.versionPatch(),
        },
        "highspy_package_init_path": str(Path(highspy.__file__).resolve()),
        "highspy_package_init_sha256": _sha_file(Path(highspy.__file__).resolve()),
        "highspy_python_source_path": runtime["highspy_python_source_path"],
        "highspy_python_source_sha256": _sha_file(Path(runtime["highspy_python_source_path"])),
        "highspy_binary_path": runtime["highspy_binary_path"],
        "highspy_binary_sha256": _sha_file(Path(runtime["highspy_binary_path"])),
        "frozen_solver_options": solver,
        "threads": solver["threads"],
        "solver_instance_created": True,
        "solver_solve_called_by_runtime_probe": False,
        "security_certified": False,
    }
    return validate_solver_runtime_evidence(value, worker_identity=worker_identity)


def validate_solver_runtime_evidence(
    value: Mapping[str, Any], *, worker_identity: Mapping[str, int]
) -> dict[str, Any]:
    config = load_config()
    runtime = config["runtime"]
    solver = config["science_authority"]["solver"]
    expected_keys = {
        "schema",
        "worker_identity",
        "observed_wall_time_ns",
        "observed_monotonic_ns",
        "locked_python_executable",
        "locked_python_sha256",
        "highspy_metadata_version",
        "highs_runtime_api_version",
        "highs_runtime_version_components",
        "highspy_package_init_path",
        "highspy_package_init_sha256",
        "highspy_python_source_path",
        "highspy_python_source_sha256",
        "highspy_binary_path",
        "highspy_binary_sha256",
        "frozen_solver_options",
        "threads",
        "solver_instance_created",
        "solver_solve_called_by_runtime_probe",
        "security_certified",
    }
    if (
        not isinstance(value, Mapping)
        or set(value) != expected_keys
        or value.get("schema")
        != "rq2_public_grid_solver_runtime_evidence_vnext_execution_v8"
        or value.get("worker_identity") != dict(worker_identity)
        or type(value.get("observed_wall_time_ns")) is not int
        or type(value.get("observed_monotonic_ns")) is not int
        or value.get("locked_python_executable")
        != str(Path(runtime["locked_python_executable"]).resolve())
        or value.get("locked_python_sha256") != runtime["locked_python_sha256"]
        or value.get("highspy_metadata_version") != solver["expected_package_version"]
        or value.get("highs_runtime_api_version") != solver["expected_runtime_api_version"]
        or value.get("highs_runtime_version_components")
        != {"major": 1, "minor": 15, "patch": 1}
        or value.get("highspy_package_init_path")
        != runtime["highspy_package_init_path"]
        or value.get("highspy_package_init_sha256")
        != runtime["highspy_package_init_sha256"]
        or value.get("highspy_python_source_path")
        != runtime["highspy_python_source_path"]
        or value.get("highspy_python_source_sha256")
        != runtime["highspy_python_source_sha256"]
        or value.get("highspy_binary_path") != runtime["highspy_binary_path"]
        or value.get("highspy_binary_sha256") != runtime["highspy_binary_sha256"]
        or value.get("frozen_solver_options") != solver
        or value.get("threads") != 4
        or value.get("solver_instance_created") is not True
        or value.get("solver_solve_called_by_runtime_probe") is not False
        or value.get("security_certified") is not False
    ):
        raise ContractRejected("actual solver runtime evidence drifted")
    return dict(value)


def exact_worker_command(
    *,
    mode: str,
    read_handle: int,
    ack_handle: int,
    parent_pid: int,
    parent_create_time_ns: int,
    session_id: str,
    execution_index: int,
    block_id: str,
    predecessor_digest: str | None,
    nonce: str,
) -> tuple[str, ...]:
    if mode not in {
        "review-preloader",
        "review-resource-probe",
        "review-deadline-no-exit-probe",
        "science",
    }:
        raise ContractRejected("worker mode unregistered")
    flag = {
        "review-preloader": "--internal-review-preloader-worker",
        "review-resource-probe": "--internal-review-resource-probe-worker",
        "review-deadline-no-exit-probe": (
            "--internal-review-deadline-no-exit-probe-worker"
        ),
        "science": "--internal-science-worker",
    }[mode]
    config = load_config()
    return (
        config["runtime"]["locked_python_executable"],
        "-B",
        "-m",
        config["runtime"]["worker_module"],
        flag,
        "--read-handle",
        str(read_handle),
        "--ack-handle",
        str(ack_handle),
        "--parent-pid",
        str(parent_pid),
        "--parent-create-time-ns",
        str(parent_create_time_ns),
        "--session-id",
        session_id,
        "--execution-index",
        str(execution_index),
        "--block-id",
        block_id,
        "--predecessor-digest",
        predecessor_digest or "NONE",
        "--nonce",
        nonce,
    )


def _transport_identity(
    *,
    mode: str,
    session_id: str,
    execution_index: int,
    block_id: str,
    predecessor_digest: str | None,
    nonce: str,
) -> None:
    if mode == "science":
        if (
            len(session_id) != 64
            or len(nonce) != 64
            or execution_index not in (1, 2)
            or block_id != BLOCKS[execution_index - 1]
            or (execution_index == 1 and predecessor_digest is not None)
            or (execution_index == 2 and (not isinstance(predecessor_digest, str) or len(predecessor_digest) != 64))
        ):
            raise ContractRejected("science transport identity/order malformed")
    elif mode in {
        "review-preloader",
        "review-resource-probe",
        "review-deadline-no-exit-probe",
    }:
        expected = mode
        if (session_id, execution_index, block_id, predecessor_digest, nonce) != (
            expected,
            0,
            expected,
            None,
            expected,
        ):
            raise ContractRejected("review transport identity malformed")
    else:
        raise ContractRejected("transport mode unregistered")


def build_worker_hello(
    *,
    mode: str,
    session_id: str,
    execution_index: int,
    block_id: str,
    predecessor_digest: str | None,
    nonce: str,
    parent_identity: dict[str, int],
    worker_identity: dict[str, int],
    command: tuple[str, ...],
    worker_read: dict[str, object],
    worker_ack: dict[str, object],
) -> dict[str, Any]:
    _transport_identity(
        mode=mode,
        session_id=session_id,
        execution_index=execution_index,
        block_id=block_id,
        predecessor_digest=predecessor_digest,
        nonce=nonce,
    )
    if (
        set(parent_identity) != {"pid", "create_time_ns"}
        or set(worker_identity) != {"pid", "ppid", "create_time_ns"}
        or worker_identity["ppid"] != parent_identity["pid"]
        or worker_read
        != {
            "raw_identifier": worker_read.get("raw_identifier"),
            "type": "anonymous_pipe",
            "role": "controller_to_worker",
            "direction": "read",
            "inherited": True,
        }
        or worker_ack
        != {
            "raw_identifier": worker_ack.get("raw_identifier"),
            "type": "anonymous_pipe",
            "role": "worker_to_controller",
            "direction": "write",
            "inherited": True,
        }
    ):
        raise ContractRejected("HELLO process/pipe authority malformed")
    expected_command = exact_worker_command(
        mode=mode,
        read_handle=int(worker_read["raw_identifier"]),
        ack_handle=int(worker_ack["raw_identifier"]),
        parent_pid=parent_identity["pid"],
        parent_create_time_ns=parent_identity["create_time_ns"],
        session_id=session_id,
        execution_index=execution_index,
        block_id=block_id,
        predecessor_digest=predecessor_digest,
        nonce=nonce,
    )
    if command != expected_command:
        raise ContractRejected("HELLO exact command drifted")
    config = load_config()
    self_mapping = verify_self_bundle()
    live_mapping = verify_live_authorities()
    v3_mapping = (
        predecessor.predecessor.predecessor.predecessor.predecessor.predecessor.v3.verify_full_live_closure()
    )
    return {
        "schema": "rq2_public_grid_worker_hello_vnext_execution_v8",
        "mode": mode,
        "session_id": session_id,
        "execution_index": execution_index,
        "block_id": block_id,
        "predecessor_digest": predecessor_digest,
        "nonce": nonce,
        "worker_identity": worker_identity,
        "parent_identity": parent_identity,
        "parent_identity_verified": True,
        "command": list(command),
        "cwd": str(ROOT),
        "environment": config["runtime"]["sanitized_environment"],
        "environment_sha256": sha256_bytes(exact_json_bytes(config["runtime"]["sanitized_environment"])),
        "config_sha256": self_mapping[CONFIG.relative_to(ROOT).as_posix()],
        "controller_source_sha256": self_mapping[
            "experiments/run_rq2_public_grid_two_block_pilot_vnext_execution_successor_v8.py"
        ],
        "worker_source_sha256": self_mapping[
            "experiments/worker_rq2_public_grid_two_block_pilot_vnext_execution_successor_v8.py"
        ],
        "bootstrap_source_sha256": self_mapping[config["runtime"]["bootstrap_path"]],
        "self_bundle_mapping": self_mapping,
        "self_bundle_mapping_sha256": closure_mapping_sha256(self_mapping),
        "v3_closure_mapping": v3_mapping,
        "v3_closure_mapping_sha256": (
            predecessor.predecessor.predecessor.predecessor.predecessor.predecessor.v3.closure_mapping_sha256(
                v3_mapping
            )
        ),
        "live_authority_mapping": live_mapping,
        "live_authority_mapping_sha256": closure_mapping_sha256(live_mapping),
        "public_key": load_public_key(),
        "worker_read": worker_read,
        "worker_ack": worker_ack,
    }


def hello_transport_context(hello: Mapping[str, Any]) -> dict[str, Any]:
    if hello.get("schema") != "rq2_public_grid_worker_hello_vnext_execution_v8":
        raise ContractRejected("HELLO schema unregistered")
    return {key: hello[key] for key in hello if key not in {"schema", "mode", "parent_identity_verified"}}


def require_exact(value: object, expected: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or value != expected:
        raise ContractRejected(f"{label} exact schema/cross-binding rejected")
    return value


def build_worker_envelope(
    *, hello: dict[str, Any], hello_raw: bytes, pipe_authority: dict[str, Any], attempt_root: str
) -> dict[str, Any]:
    if set(pipe_authority) != {"worker_read", "worker_ack", "controller_write", "controller_read"}:
        raise ContractRejected("envelope pipe authority keyset drifted")
    if pipe_authority["worker_read"] != hello["worker_read"] or pipe_authority["worker_ack"] != hello["worker_ack"]:
        raise ContractRejected("envelope worker pipe cross-binding drifted")
    return {
        "schema": "rq2_public_grid_worker_envelope_vnext_execution_v8",
        "transport_context": hello_transport_context(hello),
        "hello_sha256": sha256_bytes(hello_raw),
        "pipe_authority": pipe_authority,
        "pipe_authority_digest": sha256_bytes(exact_json_bytes(pipe_authority)),
        "attempt_root": attempt_root,
        "science_authority": load_config()["science_authority"],
        "resource_contract": load_config()["resource_contract"],
        "first_same_pair_resource_sample_succeeded_before_envelope": True,
        "nonformal": True,
        "claim": False,
    }


def build_worker_result(
    *,
    hello: dict[str, Any],
    hello_raw: bytes,
    envelope: dict[str, Any],
    envelope_raw: bytes,
    scientific_payload: dict[str, Any],
    solver_call_accounting: dict[str, Any],
    solver_runtime_evidence: dict[str, Any],
) -> dict[str, Any]:
    accepted = scientific_payload.get("all_hours_resolved") is True
    return {
        "schema": "rq2_public_grid_worker_result_vnext_execution_v8",
        "transport_context": hello_transport_context(hello),
        "hello_sha256": sha256_bytes(hello_raw),
        "envelope_sha256": sha256_bytes(envelope_raw),
        "pipe_authority_digest": envelope["pipe_authority_digest"],
        "scientific_payload": scientific_payload,
        "scientific_payload_sha256": sha256_bytes(exact_json_bytes(scientific_payload)),
        "solver_call_accounting": solver_call_accounting,
        "solver_call_accounting_sha256": sha256_bytes(exact_json_bytes(solver_call_accounting)),
        "solver_runtime_evidence": solver_runtime_evidence,
        "solver_runtime_evidence_sha256": sha256_bytes(exact_json_bytes(solver_runtime_evidence)),
        "scientific_loader_calls": 1,
        "solver_calls": solver_call_accounting["solver_calls"],
        "accepted_as_nonformal_result": accepted,
        "nonformal": True,
        "claim": False,
        "mathematical_infeasibility_inferred_from_failure": False,
        "status": "COMPLETE" if accepted else "HONEST_INCOMPLETE",
    }


def build_worker_exit_notice(
    *, hello: dict[str, Any], envelope: dict[str, Any], result: dict[str, Any], result_raw: bytes, result_path: str
) -> dict[str, Any]:
    return {
        "schema": "rq2_public_grid_worker_exit_notice_vnext_execution_v8",
        "transport_context": hello_transport_context(hello),
        "hello_sha256": result["hello_sha256"],
        "envelope_sha256": result["envelope_sha256"],
        "pipe_authority_digest": envelope["pipe_authority_digest"],
        "result_path": result_path,
        "result_sha256": sha256_bytes(result_raw),
        "scientific_payload_sha256": result["scientific_payload_sha256"],
        "solver_call_accounting_sha256": result["solver_call_accounting_sha256"],
        "solver_runtime_evidence_sha256": result["solver_runtime_evidence_sha256"],
        "worker_ready_to_exit": True,
        "nonformal": True,
        "claim": False,
    }


def build_attempt_receipt(
    *, hello: dict[str, Any], envelope: dict[str, Any], result: dict[str, Any], result_raw: bytes,
    exit_notice: dict[str, Any], exit_notice_raw: bytes, result_path: str,
    resource_journal: dict[str, Any]
) -> dict[str, Any]:
    validate_success_resource_journal(resource_journal)
    return {
        "schema": "rq2_public_grid_attempt_receipt_vnext_execution_v8",
        "transport_context": hello_transport_context(hello),
        "hello_sha256": result["hello_sha256"],
        "envelope_sha256": result["envelope_sha256"],
        "exit_notice_sha256": sha256_bytes(exit_notice_raw),
        "result_path": result_path,
        "result_sha256": sha256_bytes(result_raw),
        "scientific_payload_sha256": result["scientific_payload_sha256"],
        "solver_call_accounting_sha256": result["solver_call_accounting_sha256"],
        "solver_runtime_evidence": result["solver_runtime_evidence"],
        "solver_runtime_evidence_sha256": result["solver_runtime_evidence_sha256"],
        "resource_journal": resource_journal,
        "resource_journal_sha256": sha256_bytes(exact_json_bytes(resource_journal)),
        "resource_outcome_status": resource_journal["status"],
        "resource_outcome_reason": resource_journal["reason"],
        "resource_honest_incomplete": resource_journal["honest_incomplete"],
        "maximum_private_commit_bytes": resource_journal["maximum_private_commit_bytes"],
        "minimum_system_commit_available_bytes": resource_journal["minimum_system_commit_available_bytes"],
        "resource_sample_count": resource_journal["sample_count"],
        "controller_validated": True,
        "published": False,
        "nonformal": True,
        "claim": False,
    }


def build_controller_ack(
    *, hello: dict[str, Any], envelope: dict[str, Any], result: dict[str, Any], result_raw: bytes,
    exit_notice_raw: bytes, receipt: dict[str, Any], receipt_raw: bytes,
    resource_journal: dict[str, Any]
) -> dict[str, Any]:
    return {
        "schema": "rq2_public_grid_controller_ack_vnext_execution_v8",
        "transport_context": hello_transport_context(hello),
        "hello_sha256": result["hello_sha256"],
        "envelope_sha256": result["envelope_sha256"],
        "exit_notice_sha256": sha256_bytes(exit_notice_raw),
        "result_sha256": sha256_bytes(result_raw),
        "attempt_receipt_sha256": sha256_bytes(receipt_raw),
        "scientific_payload_sha256": result["scientific_payload_sha256"],
        "solver_call_accounting_sha256": result["solver_call_accounting_sha256"],
        "solver_runtime_evidence": result["solver_runtime_evidence"],
        "solver_runtime_evidence_sha256": result["solver_runtime_evidence_sha256"],
        "resource_journal": resource_journal,
        "resource_journal_sha256": receipt["resource_journal_sha256"],
        "resource_outcome_status": resource_journal["status"],
        "resource_outcome_reason": resource_journal["reason"],
        "resource_honest_incomplete": resource_journal["honest_incomplete"],
        "maximum_private_commit_bytes": resource_journal["maximum_private_commit_bytes"],
        "minimum_system_commit_available_bytes": resource_journal["minimum_system_commit_available_bytes"],
        "resource_sample_count": resource_journal["sample_count"],
        "accepted_as_nonformal_result": result["accepted_as_nonformal_result"],
        "controller_generated_after_worker_exit_observed": True,
        "nonformal": True,
        "claim": False,
    }


def validate_execution_review_object(value: object) -> None:
    config = load_config()
    if not isinstance(value, dict):
        raise ContractRejected("V8 execution-review receipt malformed")
    expected_keys = {
        "schema", "version", "reviewed_on", "reviewer_role", "verdict",
        "reviewed_outer", "bound_v7_outer", "bound_v7_escalate_receipt",
        "bound_v7_public_key", "bound_public_key", "findings", "effect"
    }
    if (
        set(value) != expected_keys
        or value.get("schema") != config["fixed_execution_review"]["schema"]
        or value.get("version") != 8
        or value.get("reviewer_role") != "independent_sol_reviewer"
        or value.get("verdict") != "PASS"
        or value.get("findings") != []
        or value.get("reviewed_outer")
        != {"path": config["bundle"]["outer_path"], "sha256": _sha_file(OUTER)}
        or value.get("bound_v7_outer")
        != {"path": config["predecessor_v7"]["outer_path"], "sha256": config["predecessor_v7"]["outer_sha256"]}
        or value.get("bound_v7_escalate_receipt")
        != {"path": config["predecessor_v7"]["review_receipt_path"], "sha256": config["predecessor_v7"]["review_receipt_sha256"]}
        or value.get("bound_v7_public_key")
        != {"path": config["predecessor_v7"]["public_anchor_path"], "sha256": config["predecessor_v7"]["public_anchor_sha256"], "key_id": config["predecessor_v7"]["key_id"]}
        or value.get("bound_public_key")
        != {"path": config["controller_authentication"]["public_key_path"], "sha256": config["controller_authentication"]["public_key_file_sha256"], "key_id": config["controller_authentication"]["key_id"]}
        or value.get("effect") != config["fixed_execution_review"]["effect"]
    ):
        raise ContractRejected("V8 execution-review receipt binding/effect drifted")


def require_execution_review() -> dict[str, Any]:
    if not REVIEW.exists() or REVIEW.is_symlink():
        raise ContractRejected("fixed V8 execution-review PASS receipt is absent")
    raw = read_stable(REVIEW)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ContractRejected("V8 execution-review receipt JSON malformed") from exc
    validate_execution_review_object(value)
    if read_stable(REVIEW) != raw:
        raise ContractRejected("V8 execution-review receipt changed during validation")
    return value


def assert_live_environment() -> None:
    config = load_config()
    if Path.cwd() != ROOT or dict(os.environ) != config["runtime"]["sanitized_environment"]:
        raise ContractRejected("worker cwd/environment drifted")


def run_actual_science(block_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    require_execution_review()
    verify_live_authorities()
    return predecessor.predecessor.predecessor.predecessor.predecessor.predecessor.run_actual_science(block_id)


def validate_actual_science_payload(
    payload: Mapping[str, Any], block_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    require_execution_review()
    verify_live_authorities()
    return predecessor.predecessor.predecessor.predecessor.predecessor.predecessor.validate_actual_science_payload(
        payload, block_id
    )


def resource_primitives() -> Any:
    verify_live_authorities()
    return predecessor.predecessor.predecessor.predecessor.predecessor.predecessor.resource_authority()


def substantive_entry(raw: bytes) -> dict[str, Any]:
    return {"sha256": sha256_bytes(raw), "length_bytes": len(raw)}


def build_attestation_payload(
    *, session_id: str, entries: Mapping[str, bytes], resource_journals: Mapping[str, dict[str, Any]],
    runtime_evidence: Mapping[str, dict[str, Any]], result_manifest_core: dict[str, Any],
    success_core: dict[str, Any], closure_mapping: Mapping[str, str]
) -> dict[str, Any]:
    if set(resource_journals) != set(BLOCKS) or set(runtime_evidence) != set(BLOCKS):
        raise ContractRejected("attestation block membership drifted")
    for journal in resource_journals.values():
        validate_success_resource_journal(journal)
    for block, evidence in runtime_evidence.items():
        worker_identity = evidence.get("worker_identity")
        validate_solver_runtime_evidence(evidence, worker_identity=worker_identity)
        if block not in BLOCKS:
            raise ContractRejected("attestation runtime block drifted")
    mapping = {name: substantive_entry(raw) for name, raw in sorted(entries.items())}
    return {
        "schema": "rq2_public_grid_controller_attestation_payload_vnext_execution_v8",
        "session_id": session_id,
        "substantive_byte_mapping": mapping,
        "resource_journals": dict(resource_journals),
        "runtime_evidence": dict(runtime_evidence),
        "result_manifest_substantive_core": result_manifest_core,
        "success_readback_substantive_core": success_core,
        "closure_mapping": dict(closure_mapping),
        "closure_mapping_sha256": closure_mapping_sha256(closure_mapping),
        "same_os_user_pre_execution_lease_exfiltration_out_of_scope": True,
        "nonformal": True,
        "claim": False,
        "security_certified": False,
    }


def build_attestation(payload: dict[str, Any], seed: bytes | bytearray) -> dict[str, Any]:
    payload_raw = exact_json_bytes(payload)
    digest = sha256_bytes(payload_raw)
    signature = lamport_sign_digest(bytes(seed), digest)
    verify_lamport_signature(digest, signature)
    return {
        "schema": "rq2_public_grid_controller_attestation_vnext_execution_v8",
        "public_key": load_public_key(),
        "payload": payload,
        "payload_sha256": digest,
        "signature": signature,
        "signature_sha256": sha256_bytes(exact_json_bytes(signature)),
        "same_os_user_pre_execution_lease_exfiltration_out_of_scope": True,
        "security_certified": False,
    }


def verify_attestation(value: Mapping[str, Any]) -> dict[str, Any]:
    if (
        not isinstance(value, Mapping)
        or set(value)
        != {"schema", "public_key", "payload", "payload_sha256", "signature", "signature_sha256", "same_os_user_pre_execution_lease_exfiltration_out_of_scope", "security_certified"}
        or value.get("schema")
        != "rq2_public_grid_controller_attestation_vnext_execution_v8"
        or value.get("public_key") != load_public_key()
        or value.get("payload_sha256") != sha256_bytes(exact_json_bytes(value.get("payload")))
        or value.get("signature_sha256") != sha256_bytes(exact_json_bytes(value.get("signature")))
        or value.get("same_os_user_pre_execution_lease_exfiltration_out_of_scope") is not True
        or value.get("security_certified") is not False
    ):
        raise ContractRejected("controller attestation schema/binding rejected")
    verify_lamport_signature(value["payload_sha256"], value["signature"], value["public_key"])
    payload = value["payload"]
    if payload.get("same_os_user_pre_execution_lease_exfiltration_out_of_scope") is not True or payload.get("security_certified") is not False:
        raise ContractRejected("attestation threat boundary drifted")
    return dict(value)


def verify_published_artifacts(
    result_root: Path | None = None, success_root: Path | None = None
) -> dict[str, Any]:
    """Independently verify V8 publication using only sealed public material."""
    from experiments import (
        publish_rq2_public_grid_evidence_publication_successor_v3 as publisher,
    )

    config = load_config()
    result = result_root or ROOT / config["paths"]["result_root"]
    success = success_root or ROOT / config["paths"]["success_root"]
    terminal = ROOT / config["paths"]["terminal_root"]
    try:
        result_tree = json.loads(read_stable(result / "SHA256SUMS.json"))
        success_tree = json.loads(read_stable(success / "SHA256SUMS.json"))
        result_manifest = json.loads(read_stable(result / "result_manifest.json"))
        success_value = json.loads(read_stable(success / "success.json"))
        attestation = verify_attestation(
            json.loads(read_stable(result / "controller_attestation.json"))
        )
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ContractRejected("published V8 artifact missing or malformed") from exc
    if result_tree != publisher.typed_tree(result) or success_tree != publisher.typed_tree(success):
        raise ContractRejected("published V8 typed tree drifted")
    payload = attestation["payload"]
    expected_entries = {
        "controller_receipt.json",
        "summary.json",
        "closure_mapping.json",
    }
    for block in BLOCKS:
        expected_entries.update(
            {
                f"workers/{block}/accepted_evidence.json",
                f"workers/{block}/hello.json",
                f"workers/{block}/envelope.json",
                f"workers/{block}/exit_notice.json",
                f"workers/{block}/worker_result.json",
                f"workers/{block}/attempt_receipt.json",
                f"workers/{block}/ack.json",
                f"workers/{block}/scientific_payload.json",
                f"workers/{block}/resource_journal.json",
                f"workers/{block}/solver_runtime_evidence.json",
            }
        )
    substantive = payload.get("substantive_byte_mapping")
    if not isinstance(substantive, dict) or set(substantive) != expected_entries:
        raise ContractRejected("attestation substantive path inventory drifted")
    for relative, identity in substantive.items():
        candidate = (result / relative).resolve()
        try:
            candidate.relative_to(result.resolve())
        except ValueError as exc:
            raise ContractRejected("attestation path escaped result root") from exc
        raw = read_stable(candidate)
        if identity != substantive_entry(raw):
            raise ContractRejected(f"attested substantive bytes drifted: {relative}")
    resource_journals = payload.get("resource_journals")
    runtime_evidence = payload.get("runtime_evidence")
    if (
        not isinstance(resource_journals, dict)
        or set(resource_journals) != set(BLOCKS)
        or not isinstance(runtime_evidence, dict)
        or set(runtime_evidence) != set(BLOCKS)
    ):
        raise ContractRejected("attested resource/runtime block inventory drifted")
    accepted_records: list[dict[str, Any]] = []
    for execution_index, block in enumerate(BLOCKS, start=1):
        validate_success_resource_journal(resource_journals[block])
        worker_identity = runtime_evidence[block].get("worker_identity")
        validate_solver_runtime_evidence(
            runtime_evidence[block], worker_identity=worker_identity
        )
        if json.loads(read_stable(result / f"workers/{block}/resource_journal.json")) != resource_journals[block]:
            raise ContractRejected("resource journal file/attestation drifted")
        if json.loads(read_stable(result / f"workers/{block}/solver_runtime_evidence.json")) != runtime_evidence[block]:
            raise ContractRejected("runtime evidence file/attestation drifted")
        base = result / "workers" / block
        receipt = json.loads(read_stable(base / "attempt_receipt.json"))
        ack = json.loads(read_stable(base / "ack.json"))
        evidence = json.loads(read_stable(base / "accepted_evidence.json"))
        for container in (receipt, ack, evidence):
            if (
                container.get("resource_journal") != resource_journals[block]
                or container.get("solver_runtime_evidence") != runtime_evidence[block]
                or container.get("resource_sample_count")
                != resource_journals[block]["sample_count"]
                or container.get("maximum_private_commit_bytes")
                != resource_journals[block]["maximum_private_commit_bytes"]
                or container.get("minimum_system_commit_available_bytes")
                != resource_journals[block]["minimum_system_commit_available_bytes"]
            ):
                raise ContractRejected("resource/runtime evidence chain drifted")
        if (
            evidence.get("schema")
            != "rq2_public_grid_accepted_evidence_vnext_execution_v8"
            or evidence.get("session_id") != payload.get("session_id")
            or evidence.get("execution_index") != execution_index
            or evidence.get("block_id") != block
            or evidence.get("predecessor_digest")
            != (None if execution_index == 1 else accepted_records[0]["record_digest"])
            or evidence.get("nonformal") is not True
            or evidence.get("claim") is not False
            or evidence.get("security_certified") is not False
        ):
            raise ContractRejected("accepted evidence identity/order drifted")
        raw_names = {
            "hello": "hello.json",
            "envelope": "envelope.json",
            "exit_notice": "exit_notice.json",
            "result": "worker_result.json",
            "attempt_receipt": "attempt_receipt.json",
            "ack": "ack.json",
        }
        parsed: dict[str, dict[str, Any]] = {}
        raw_values: dict[str, bytes] = {}
        try:
            for name, filename in raw_names.items():
                raw = read_stable(base / filename)
                if raw != bytes.fromhex(evidence[f"{name}_hex"]):
                    raise ContractRejected(f"accepted {name} raw/file drifted")
                if sha256_bytes(raw) != evidence[f"{name}_sha256"]:
                    raise ContractRejected(f"accepted {name} digest drifted")
                parsed[name] = json.loads(raw)
                raw_values[name] = raw
                if parsed[name] != evidence[name]:
                    raise ContractRejected(f"accepted {name} parsed/raw drifted")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ContractRejected("accepted protocol raw evidence malformed") from exc
        hello = parsed["hello"]
        envelope = parsed["envelope"]
        worker_result = parsed["result"]
        exit_notice = parsed["exit_notice"]
        expected_hello = build_worker_hello(
            mode="science",
            session_id=evidence["session_id"],
            execution_index=execution_index,
            block_id=block,
            predecessor_digest=evidence["predecessor_digest"],
            nonce=evidence["nonce"],
            parent_identity=evidence["parent_identity"],
            worker_identity=evidence["worker_identity"],
            command=tuple(evidence["command"]),
            worker_read=evidence["pipe_authority"]["worker_read"],
            worker_ack=evidence["pipe_authority"]["worker_ack"],
        )
        require_exact(hello, expected_hello, label="published HELLO")
        if (
            evidence.get("self_bundle_mapping")
            != hello.get("self_bundle_mapping")
            or evidence.get("live_authority_mapping")
            != payload.get("closure_mapping")
            or evidence.get("self_bundle_mapping_sha256")
            != hello.get("self_bundle_mapping_sha256")
            or evidence.get("live_authority_mapping_sha256")
            != payload.get("closure_mapping_sha256")
        ):
            raise ContractRejected("accepted evidence authority mapping drifted")
        expected_envelope = build_worker_envelope(
            hello=hello,
            hello_raw=raw_values["hello"],
            pipe_authority=evidence["pipe_authority"],
            attempt_root=str(Path(evidence["result_path"]).parent),
        )
        require_exact(envelope, expected_envelope, label="published envelope")
        expected_result = build_worker_result(
            hello=hello,
            hello_raw=raw_values["hello"],
            envelope=envelope,
            envelope_raw=raw_values["envelope"],
            scientific_payload=worker_result["scientific_payload"],
            solver_call_accounting=worker_result["solver_call_accounting"],
            solver_runtime_evidence=runtime_evidence[block],
        )
        require_exact(worker_result, expected_result, label="published worker result")
        expected_notice = build_worker_exit_notice(
            hello=hello,
            envelope=envelope,
            result=worker_result,
            result_raw=raw_values["result"],
            result_path=evidence["result_path"],
        )
        require_exact(exit_notice, expected_notice, label="published exit notice")
        expected_receipt = build_attempt_receipt(
            hello=hello,
            envelope=envelope,
            result=worker_result,
            result_raw=raw_values["result"],
            exit_notice=exit_notice,
            exit_notice_raw=raw_values["exit_notice"],
            result_path=evidence["result_path"],
            resource_journal=resource_journals[block],
        )
        require_exact(receipt, expected_receipt, label="published attempt receipt")
        expected_ack = build_controller_ack(
            hello=hello,
            envelope=envelope,
            result=worker_result,
            result_raw=raw_values["result"],
            exit_notice_raw=raw_values["exit_notice"],
            receipt=receipt,
            receipt_raw=raw_values["attempt_receipt"],
            resource_journal=resource_journals[block],
        )
        require_exact(ack, expected_ack, label="published ACK")
        for field, filename in (
            ("scientific", "scientific_payload.json"),
            ("resource_journal", "resource_journal.json"),
            ("solver_runtime_evidence", "solver_runtime_evidence.json"),
        ):
            raw = read_stable(base / filename)
            if raw != bytes.fromhex(evidence[f"{field}_hex"]):
                raise ContractRejected(f"accepted {field} raw/file drifted")
        if (
            json.loads(read_stable(base / "scientific_payload.json"))
            != worker_result["scientific_payload"]
            or evidence["resource_journal"] != resource_journals[block]
            or evidence["solver_runtime_evidence"] != runtime_evidence[block]
        ):
            raise ContractRejected("published scientific/resource/runtime drifted")
        record_body = {
            key: item
            for key, item in evidence.items()
            if key not in {"record_digest", "controller_hmac"}
        }
        if (
            evidence.get("record_digest")
            != sha256_bytes(exact_json_bytes(record_body))
            or not isinstance(evidence.get("controller_hmac"), str)
            or len(evidence["controller_hmac"]) != 64
        ):
            raise ContractRejected("signed accepted record digest/HMAC shape drifted")
        try:
            bytes.fromhex(evidence["controller_hmac"])
        except ValueError as exc:
            raise ContractRejected("accepted record HMAC malformed") from exc
        accepted_records.append(evidence)
    closure = json.loads(read_stable(result / "closure_mapping.json"))
    if (
        closure != payload.get("closure_mapping")
        or closure_mapping_sha256(closure)
        != payload.get("closure_mapping_sha256")
        or closure != verify_live_authorities()
    ):
        raise ContractRejected("attested live closure drifted")
    science_hashes = {
        record["block_id"]: record["scientific_payload_sha256"]
        for record in accepted_records
    }
    accounting_hashes = {
        record["block_id"]: record["solver_call_accounting_sha256"]
        for record in accepted_records
    }
    resource_hashes = {
        block: sha256_bytes(exact_json_bytes(resource_journals[block]))
        for block in BLOCKS
    }
    runtime_hashes = {
        block: sha256_bytes(exact_json_bytes(runtime_evidence[block]))
        for block in BLOCKS
    }
    controller_receipt = json.loads(read_stable(result / "controller_receipt.json"))
    controller_receipt_body = {
        "schema": "rq2_public_grid_controller_receipt_vnext_execution_v8",
        "session_id": payload["session_id"],
        "record_digests": [record["record_digest"] for record in accepted_records],
        "ledger_sha256": sha256_bytes(exact_json_bytes(accepted_records)),
        "scientific_payload_sha256s": science_hashes,
        "solver_call_accounting_sha256s": accounting_hashes,
        "resource_journal_sha256s": resource_hashes,
        "solver_runtime_evidence_sha256s": runtime_hashes,
        "resource_journals": resource_journals,
        "solver_runtime_evidence": runtime_evidence,
        "self_bundle_mapping_sha256": closure_mapping_sha256(
            verify_self_bundle()
        ),
        "live_authority_mapping_sha256": closure_mapping_sha256(closure),
        "same_os_user_pre_execution_lease_exfiltration_out_of_scope": True,
        "nonformal": True,
        "claim": False,
        "security_certified": False,
    }
    if (
        {
            key: item
            for key, item in controller_receipt.items()
            if key != "controller_hmac"
        }
        != controller_receipt_body
        or not isinstance(controller_receipt.get("controller_hmac"), str)
        or len(controller_receipt["controller_hmac"]) != 64
    ):
        raise ContractRejected("signed controller receipt drifted")
    try:
        bytes.fromhex(controller_receipt["controller_hmac"])
    except ValueError as exc:
        raise ContractRejected("controller receipt HMAC malformed") from exc
    summary = json.loads(read_stable(result / "summary.json"))
    expected_summary = {
        "schema": "rq2_public_grid_nonformal_two_block_summary_vnext_execution_v8",
        "blocks": list(BLOCKS),
        "record_count": 2,
        "scientific_payload_sha256s": science_hashes,
        "solver_call_accounting_sha256s": accounting_hashes,
        "resource_journal_sha256s": resource_hashes,
        "solver_runtime_evidence_sha256s": runtime_hashes,
        "resource_journals": resource_journals,
        "solver_runtime_evidence": runtime_evidence,
        "nonformal": True,
        "claim": False,
        "mathematical_infeasibility_inferred_from_failure": False,
        "security_certified": False,
    }
    if summary != expected_summary:
        raise ContractRejected("signed controller summary drifted")
    expected_result_core = {
        "schema": "rq2_public_grid_result_manifest_substantive_core_vnext_execution_v8",
        "session_id": payload["session_id"],
        "controller_receipt_sha256": sha256_bytes(
            exact_json_bytes(controller_receipt)
        ),
        "record_digests": [record["record_digest"] for record in accepted_records],
        "scientific_payload_sha256s": science_hashes,
        "solver_call_accounting_sha256s": accounting_hashes,
        "resource_journal_sha256s": resource_hashes,
        "solver_runtime_evidence_sha256s": runtime_hashes,
        "resource_journals": resource_journals,
        "solver_runtime_evidence": runtime_evidence,
        "public_key": load_public_key(),
        "same_os_user_pre_execution_lease_exfiltration_out_of_scope": True,
        "nonformal": True,
        "claim": False,
        "security_certified": False,
    }
    expected_success_core = {
        "schema": "rq2_public_grid_success_readback_substantive_core_vnext_execution_v8",
        "session_id": payload["session_id"],
        "classification": "committed_success",
        "published": True,
        "controller_receipt_sha256": expected_result_core[
            "controller_receipt_sha256"
        ],
        "scientific_payload_sha256s": science_hashes,
        "solver_call_accounting_sha256s": accounting_hashes,
        "resource_journal_sha256s": resource_hashes,
        "solver_runtime_evidence_sha256s": runtime_hashes,
        "resource_journals": resource_journals,
        "solver_runtime_evidence": runtime_evidence,
        "public_key": load_public_key(),
        "same_os_user_pre_execution_lease_exfiltration_out_of_scope": True,
        "nonformal": True,
        "formal": False,
        "claim": False,
        "security_certified": False,
    }
    result_core = payload.get("result_manifest_substantive_core")
    success_core = payload.get("success_readback_substantive_core")
    if result_core != expected_result_core or success_core != expected_success_core:
        raise ContractRejected("signed result/success substantive core drifted")
    expected_result = {
        "schema": "rq2_public_grid_result_manifest_vnext_execution_v8",
        "substantive_core": result_core,
        "controller_attestation_payload_sha256": attestation["payload_sha256"],
        "controller_signature_sha256": attestation["signature_sha256"],
        "public_key": load_public_key(),
        "nonformal": True,
        "claim": False,
        "security_certified": False,
    }
    expected_success = {
        "schema": "rq2_public_grid_success_commit_vnext_execution_v8",
        "substantive_core": success_core,
        "controller_attestation_payload_sha256": attestation["payload_sha256"],
        "controller_signature_sha256": attestation["signature_sha256"],
        "public_key": load_public_key(),
        "nonformal": True,
        "formal": False,
        "claim": False,
        "security_certified": False,
    }
    if result_manifest != expected_result or success_value != expected_success:
        raise ContractRejected("deterministic result/success wrapper drifted")
    presence = publisher.capture_presence(
        publisher.PublicationPaths(result, success, terminal)
    )
    if publisher.classify_publication(presence, result_exact=True, success_exact=True) != "committed_success":
        raise ContractRejected("published V8 presence classification drifted")
    for path in result.rglob("*.json"):
        if '"seed_hex"' in read_stable(path).decode("utf-8"):
            raise ContractRejected("private seed leaked into V8 publication")
    if '"seed_hex"' in read_stable(success / "success.json").decode("utf-8"):
        raise ContractRejected("private seed leaked into V8 success readback")
    return {
        "classification": "committed_success",
        "attestation_payload_sha256": attestation["payload_sha256"],
        "signature_sha256": attestation["signature_sha256"],
        "resource_sample_counts": {
            block: resource_journals[block]["sample_count"] for block in BLOCKS
        },
        "security_certified": False,
    }
