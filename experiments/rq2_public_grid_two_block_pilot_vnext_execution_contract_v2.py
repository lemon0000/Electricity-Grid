"""Fail-closed contract for the reviewed Vnext nonformal execution successor."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from experiments import rq2_public_grid_evidence_publication_contract_v3 as v3

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_v2.json"
REVIEW = ROOT / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_review_pass_v2.json"
INNER = ROOT / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_v2.SHA256SUMS.json"
OUTER = ROOT / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_v2.OUTER.SHA256SUMS.json"
BLOCKS = ("holdout_s20260822_0008", "holdout_s20260822_0009")


class ContractRejected(RuntimeError):
    """The candidate authority or execution contract failed closed."""


def exact_json_bytes(value: object) -> bytes:
    return v3.exact_json_bytes(value)


def sha256_bytes(raw: bytes) -> str:
    return v3.sha256_bytes(raw)


def read_stable(path: Path, *, trace: list[str] | None = None) -> bytes:
    try:
        raw = v3.read_stable(path)
    except Exception as exc:
        raise ContractRejected(f"stable ordinary-file read rejected: {path}") from exc
    if trace is not None:
        try:
            trace.append(path.relative_to(ROOT).as_posix())
        except ValueError:
            trace.append(str(path))
    return raw


def load_config() -> dict[str, Any]:
    try:
        value = json.loads(read_stable(CONFIG))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ContractRejected("candidate config JSON malformed") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema")
        != "rq2_public_grid_two_block_pilot_vnext_execution_successor_v2"
        or value.get("version") != 2
        or value.get("status") != "vnext_execution_successor_v2_review_closed"
    ):
        raise ContractRejected("candidate config identity drifted")
    if tuple(value.get("pilot", {}).get("blocks", ())) != BLOCKS:
        raise ContractRejected("fixed two-block order drifted")
    gates = value.get("gates")
    if not isinstance(gates, dict) or any(item is not False for item in gates.values()):
        raise ContractRejected("review-closed gates drifted")
    return value


def _verify_hash(
    relative: str, expected: str, *, trace: list[str] | None = None
) -> str:
    actual = sha256_bytes(read_stable(ROOT / relative, trace=trace))
    if actual != expected:
        raise ContractRejected(f"authority hash drifted: {relative}")
    return actual


def _validate_v3_pass(value: object, config: Mapping[str, Any]) -> None:
    if not isinstance(value, dict):
        raise ContractRejected("V3 PASS receipt object malformed")
    expected_keys = {
        "schema",
        "version",
        "reviewed_on",
        "reviewer_role",
        "verdict",
        "reviewed_outer",
        "review_conclusion",
        "verification_evidence",
        "effect",
    }
    predecessor = config["predecessor_v3"]
    effect = value.get("effect")
    if (
        set(value) != expected_keys
        or value.get("schema")
        != "rq2_public_grid_evidence_publication_successor_review_pass_v3"
        or value.get("version") != 3
        or value.get("reviewer_role") != "independent_sol_reviewer"
        or value.get("verdict") != "PASS"
        or value.get("reviewed_outer")
        != {
            "path": predecessor["outer_path"],
            "sha256": predecessor["outer_sha256"],
        }
        or not isinstance(effect, dict)
        or effect.get("v3_independent_review_passed") is not True
        or effect.get("versioned_nonformal_execution_successor_creation_authorized")
        is not True
        or effect.get("successor_execution_authorized") is not False
        or effect.get("pilot_execution_authorized") is not False
        or effect.get("formal_execution_authorized") is not False
        or effect.get("claim") is not False
        or effect.get("security_certified") is not False
        or effect.get("no_execution_authority") is not True
    ):
        raise ContractRejected("V3 PASS receipt binding/effect drifted")


def _validate_rework_receipt(value: object, config: Mapping[str, Any]) -> None:
    if not isinstance(value, dict):
        raise ContractRejected("V1 REWORK receipt object malformed")
    predecessor = config["predecessor_v1"]
    if (
        set(value)
        != {
            "schema",
            "version",
            "reviewed_on",
            "reviewer_role",
            "verdict",
            "reviewed_outer",
            "findings",
            "effect",
        }
        or value.get("schema")
        != "rq2_public_grid_two_block_pilot_vnext_execution_successor_review_rework_v1"
        or value.get("version") != 1
        or value.get("reviewer_role") != "independent_sol_reviewer"
        or value.get("verdict") != "REWORK"
        or value.get("reviewed_outer")
        != {
            "path": predecessor["outer_path"],
            "sha256": predecessor["outer_sha256"],
        }
        or not isinstance(value.get("findings"), list)
        or len(value["findings"]) != 2
        or value.get("effect", {}).get("execution_authorized") is not False
        or value.get("effect", {}).get("pilot_execution_authorized") is not False
        or value.get("effect", {}).get("formal_execution_authorized") is not False
        or value.get("effect", {}).get("no_execution_authority") is not True
    ):
        raise ContractRejected("V1 REWORK receipt binding/effect drifted")


def verify_self_bundle(*, trace: list[str] | None = None) -> dict[str, str]:
    """Verify the non-cyclic V2 outer->inner->exact-seven-member seal."""
    try:
        outer_raw = read_stable(OUTER, trace=trace)
        inner_raw = read_stable(INNER, trace=trace)
        config_raw = read_stable(CONFIG, trace=trace)
        outer = json.loads(outer_raw)
        inner = json.loads(inner_raw)
        config = json.loads(config_raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ContractRejected("V2 self bundle JSON malformed") from exc
    inner_relative = INNER.relative_to(ROOT).as_posix()
    expected_members = {
        "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_v2.json",
        "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_review_rework_v1.json",
        "experiments/rq2_public_grid_two_block_pilot_vnext_execution_contract_v2.py",
        "experiments/run_rq2_public_grid_two_block_pilot_vnext_execution_successor_v2.py",
        "experiments/worker_rq2_public_grid_two_block_pilot_vnext_execution_successor_v2.py",
        "experiments/bootstrap_rq2_public_grid_two_block_pilot_vnext_execution_successor_v2.py",
        "tests/test_rq2_public_grid_two_block_pilot_vnext_execution_successor_v2.py",
    }
    files = inner.get("files") if isinstance(inner, dict) else None
    if (
        not isinstance(config, dict)
        or config.get("schema")
        != "rq2_public_grid_two_block_pilot_vnext_execution_successor_v2"
        or config.get("version") != 2
        or config.get("status") != "vnext_execution_successor_v2_review_closed"
        or set(config.get("bundle", {}).get("members", ())) != expected_members
        or config.get("bundle", {}).get("exact_member_count") != 7
        or config.get("bundle", {}).get("self_mapping_exact_count") != 9
        or config.get("bundle", {}).get("inner_path") != inner_relative
        or config.get("bundle", {}).get("outer_path")
        != OUTER.relative_to(ROOT).as_posix()
        or not isinstance(outer, dict)
        or set(outer) != {"schema", "files"}
        or outer.get("schema")
        != "rq2_public_grid_two_block_pilot_vnext_execution_successor_outer_v2"
        or outer.get("files") != {inner_relative: sha256_bytes(inner_raw)}
        or not isinstance(inner, dict)
        or set(inner) != {"schema", "files"}
        or inner.get("schema")
        != "rq2_public_grid_two_block_pilot_vnext_execution_successor_bundle_v2"
        or not isinstance(files, dict)
        or set(files) != expected_members
        or len(files) != 7
        or files.get(CONFIG.relative_to(ROOT).as_posix()) != sha256_bytes(config_raw)
    ):
        raise ContractRejected("V2 self bundle identity/inventory drifted")
    mapping = {
        OUTER.relative_to(ROOT).as_posix(): sha256_bytes(outer_raw),
        inner_relative: sha256_bytes(inner_raw),
    }
    for relative in sorted(expected_members):
        mapping[relative] = _verify_hash(relative, str(files[relative]), trace=trace)
    receipt_relative = config["predecessor_v1"]["rework_receipt_path"]
    if (
        files.get(receipt_relative)
        != config["predecessor_v1"]["rework_receipt_sha256"]
        or config["predecessor_v1"]["outer_sha256"]
        != "f6874ef26b0ab13287fd6050c2617da65545fa19ffd3ea8bd92917af158fbb49"
    ):
        raise ContractRejected("V1 predecessor/REWORK seal drifted")
    try:
        _validate_rework_receipt(
            json.loads(read_stable(ROOT / receipt_relative, trace=trace)), config
        )
    except json.JSONDecodeError as exc:
        raise ContractRejected("V1 REWORK receipt JSON malformed") from exc
    if len(mapping) != 9:
        raise ContractRejected("V2 self mapping count drifted")
    return dict(sorted(mapping.items()))


def frozen_member_sha256(relative: str) -> str:
    mapping = verify_self_bundle()
    if relative not in mapping:
        raise ContractRejected(f"path is not a frozen V2 member: {relative}")
    return mapping[relative]


def verify_live_authorities(
    *, trace: list[str] | None = None
) -> dict[str, str]:
    """Verify V3, resource, science, interpreter and frozen formal authorities."""
    self_mapping = verify_self_bundle(trace=trace)
    config = load_config()
    predecessor = config["predecessor_v3"]
    _verify_hash(
        predecessor["outer_path"], predecessor["outer_sha256"], trace=trace
    )
    pass_raw = read_stable(ROOT / predecessor["pass_receipt_path"], trace=trace)
    if sha256_bytes(pass_raw) != predecessor["pass_receipt_sha256"]:
        raise ContractRejected("V3 PASS receipt hash drifted")
    try:
        _validate_v3_pass(json.loads(pass_raw), config)
    except json.JSONDecodeError as exc:
        raise ContractRejected("V3 PASS receipt JSON malformed") from exc
    mapping = v3.verify_full_live_closure()
    if (
        len(mapping) != predecessor["closure_exact_count"]
        or v3.closure_mapping_sha256(mapping)
        != predecessor["closure_mapping_sha256"]
    ):
        raise ContractRejected("V3 exact 95-item closure drifted")
    if trace is not None:
        trace.extend(mapping)

    bindings: dict[str, str] = {}
    for authority in ("resource_authority", "science_authority"):
        section = config[authority]
        for key, value in section.items():
            if key.endswith("_path"):
                hash_key = f"{key[:-5]}_sha256"
                if hash_key in section:
                    bindings[str(value)] = _verify_hash(
                        str(value), str(section[hash_key]), trace=trace
                    )
    formal = config["formal_protection"]
    for label in ("formal_runner", "activated_config"):
        path = str(formal[f"{label}_path"])
        bindings[path] = _verify_hash(
            path, str(formal[f"{label}_sha256"]), trace=trace
        )
    python_path = Path(config["runtime"]["locked_python_executable"])
    if not python_path.is_absolute():
        raise ContractRejected("locked Python path is not absolute")
    if (
        sha256_bytes(read_stable(python_path, trace=trace))
        != config["runtime"]["locked_python_sha256"]
    ):
        raise ContractRejected("locked Python hash drifted")
    merged = {**mapping, **bindings}
    for relative, digest in self_mapping.items():
        if relative in merged and merged[relative] != digest:
            raise ContractRejected("V2 self/predecessor mapping conflict")
        merged[relative] = digest
    return dict(sorted(merged.items()))


def closure_mapping_sha256(mapping: Mapping[str, str]) -> str:
    return sha256_bytes(exact_json_bytes(dict(sorted(mapping.items()))))


def _require_exact_object(
    value: object, expected: Mapping[str, Any], *, label: str
) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != set(expected)
        or value != dict(expected)
    ):
        raise ContractRejected(f"{label} exact schema/cross-binding drifted")
    return value


def _valid_hex(value: object, length: int = 64) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_protocol_identity(
    *,
    mode: str,
    session_id: str,
    execution_index: int,
    block_id: str,
    predecessor_digest: str | None,
    nonce: str,
    parent_identity: Mapping[str, Any],
    worker_identity: Mapping[str, Any],
) -> None:
    if (
        set(parent_identity) != {"pid", "create_time_ns"}
        or set(worker_identity) != {"pid", "ppid", "create_time_ns"}
        or any(type(parent_identity[key]) is not int for key in parent_identity)
        or any(type(worker_identity[key]) is not int for key in worker_identity)
        or worker_identity["ppid"] != parent_identity["pid"]
    ):
        raise ContractRejected("protocol process identity malformed")
    if mode == "science":
        if (
            not _valid_hex(session_id)
            or type(execution_index) is not int
            or execution_index not in (1, 2)
            or block_id != BLOCKS[execution_index - 1]
            or not _valid_hex(nonce)
            or (execution_index == 1 and predecessor_digest is not None)
            or (
                execution_index == 2
                and not _valid_hex(predecessor_digest)
            )
        ):
            raise ContractRejected("science protocol identity/order malformed")
    elif mode == "review-preloader":
        if (
            session_id != "review-preloader"
            or execution_index != 0
            or block_id != "review-preloader"
            or predecessor_digest is not None
            or nonce != "review-preloader"
        ):
            raise ContractRejected("preloader protocol identity malformed")
    else:
        raise ContractRejected("protocol mode unregistered")


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
    _validate_protocol_identity(
        mode=mode,
        session_id=session_id,
        execution_index=execution_index,
        block_id=block_id,
        predecessor_digest=predecessor_digest,
        nonce=nonce,
        parent_identity=parent_identity,
        worker_identity=worker_identity,
    )
    config = load_config()
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
        raise ContractRejected("worker command authority drifted")
    expected_worker_read = {
        "raw_identifier": worker_read["raw_identifier"],
        "type": "anonymous_pipe",
        "role": "controller_to_worker",
        "direction": "read",
        "inherited": True,
    }
    expected_worker_ack = {
        "raw_identifier": worker_ack["raw_identifier"],
        "type": "anonymous_pipe",
        "role": "worker_to_controller",
        "direction": "write",
        "inherited": True,
    }
    if worker_read != expected_worker_read or worker_ack != expected_worker_ack:
        raise ContractRejected("worker pipe role/type/direction/inheritance drifted")
    self_mapping = verify_self_bundle()
    live_mapping = verify_live_authorities()
    v3_mapping = v3.verify_full_live_closure()
    environment = config["runtime"]["sanitized_environment"]
    controller_path = (
        "experiments/run_rq2_public_grid_two_block_pilot_vnext_execution_successor_v2.py"
    )
    worker_path = (
        "experiments/worker_rq2_public_grid_two_block_pilot_vnext_execution_successor_v2.py"
    )
    bootstrap_path = config["runtime"]["bootstrap_path"]
    worker_pipe_authority = {
        "worker_read": worker_read,
        "worker_ack": worker_ack,
    }
    return {
        "schema": "rq2_public_grid_worker_hello_vnext_execution_v2",
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
        "environment": environment,
        "environment_sha256": sha256_bytes(exact_json_bytes(environment)),
        "config_sha256": self_mapping[CONFIG.relative_to(ROOT).as_posix()],
        "controller_source_sha256": self_mapping[controller_path],
        "worker_source_sha256": self_mapping[worker_path],
        "bootstrap_source_sha256": self_mapping[bootstrap_path],
        "self_outer_sha256": self_mapping[OUTER.relative_to(ROOT).as_posix()],
        "self_inner_sha256": self_mapping[INNER.relative_to(ROOT).as_posix()],
        "self_bundle_mapping": self_mapping,
        "self_bundle_mapping_sha256": closure_mapping_sha256(self_mapping),
        "v3_closure_mapping": v3_mapping,
        "v3_closure_mapping_sha256": config["predecessor_v3"][
            "closure_mapping_sha256"
        ],
        "live_authority_mapping": live_mapping,
        "live_authority_mapping_sha256": closure_mapping_sha256(live_mapping),
        "worker_read": worker_read,
        "worker_ack": worker_ack,
        "worker_pipe_authority_digest": sha256_bytes(
            exact_json_bytes(worker_pipe_authority)
        ),
    }


def validate_worker_hello(value: object, **identity: Any) -> dict[str, Any]:
    return _require_exact_object(
        value, build_worker_hello(**identity), label="worker HELLO"
    )


def build_preloader_ack(
    *, hello: dict[str, Any], hello_raw: bytes
) -> dict[str, Any]:
    return {
        "schema": "rq2_public_grid_preloader_ack_vnext_execution_v2",
        "status": "NON_ACCEPTED_PRELOADER_BOUNDARY",
        "transport_context": hello_transport_context(hello),
        "hello_sha256": sha256_bytes(hello_raw),
        "self_bundle_mapping_sha256": hello["self_bundle_mapping_sha256"],
        "live_authority_mapping_sha256": hello[
            "live_authority_mapping_sha256"
        ],
        "scientific_loader_calls": 0,
        "solver_calls": 0,
        "accepted": False,
        "nonformal": True,
        "claim": False,
    }


def validate_preloader_ack(value: object, **expected: Any) -> dict[str, Any]:
    return _require_exact_object(
        value, build_preloader_ack(**expected), label="preloader ACK"
    )


def hello_transport_context(hello: Mapping[str, Any]) -> dict[str, Any]:
    if hello.get("schema") != "rq2_public_grid_worker_hello_vnext_execution_v2":
        raise ContractRejected("worker HELLO schema unregistered")
    return {
        key: hello[key]
        for key in hello
        if key not in {"schema", "mode", "parent_identity_verified"}
    }


def build_worker_envelope(
    *,
    hello: dict[str, Any],
    hello_raw: bytes,
    pipe_authority: dict[str, Any],
    attempt_root: str,
) -> dict[str, Any]:
    config = load_config()
    expected_pipe_keys = {
        "worker_read",
        "worker_ack",
        "controller_write",
        "controller_read",
    }
    if (
        set(pipe_authority) != expected_pipe_keys
        or pipe_authority["worker_read"] != hello["worker_read"]
        or pipe_authority["worker_ack"] != hello["worker_ack"]
    ):
        raise ContractRejected("envelope pipe authority membership drifted")
    for key, role, direction, inherited in (
        ("controller_write", "controller_to_worker", "write", False),
        ("controller_read", "worker_to_controller", "read", False),
    ):
        endpoint = pipe_authority[key]
        if (
            not isinstance(endpoint, dict)
            or set(endpoint)
            != {"raw_identifier", "type", "role", "direction", "inherited"}
            or endpoint.get("type") != "anonymous_pipe"
            or endpoint.get("role") != role
            or endpoint.get("direction") != direction
            or endpoint.get("inherited") is not inherited
        ):
            raise ContractRejected("controller pipe role/type/direction drifted")
    return {
        "schema": "rq2_public_grid_worker_envelope_vnext_execution_v2",
        "transport_context": hello_transport_context(hello),
        "hello_sha256": sha256_bytes(hello_raw),
        "pipe_authority": pipe_authority,
        "pipe_authority_digest": sha256_bytes(exact_json_bytes(pipe_authority)),
        "attempt_root": attempt_root,
        "science_authority": config["science_authority"],
        "nonformal": True,
        "claim": False,
    }


def validate_worker_envelope(
    value: object,
    *,
    hello: dict[str, Any],
    hello_raw: bytes,
    pipe_authority: dict[str, Any],
    attempt_root: str,
) -> dict[str, Any]:
    return _require_exact_object(
        value,
        build_worker_envelope(
            hello=hello,
            hello_raw=hello_raw,
            pipe_authority=pipe_authority,
            attempt_root=attempt_root,
        ),
        label="worker envelope",
    )


def build_worker_result(
    *,
    hello: dict[str, Any],
    hello_raw: bytes,
    envelope: dict[str, Any],
    envelope_raw: bytes,
    scientific_payload: dict[str, Any],
    solver_call_accounting: dict[str, Any],
) -> dict[str, Any]:
    scientific_raw = exact_json_bytes(scientific_payload)
    accepted = scientific_payload.get("all_hours_resolved") is True
    return {
        "schema": "rq2_public_grid_worker_result_vnext_execution_v2",
        "transport_context": hello_transport_context(hello),
        "hello_sha256": sha256_bytes(hello_raw),
        "envelope_sha256": sha256_bytes(envelope_raw),
        "pipe_authority_digest": envelope["pipe_authority_digest"],
        "self_bundle_mapping": hello["self_bundle_mapping"],
        "self_bundle_mapping_sha256": hello["self_bundle_mapping_sha256"],
        "v3_closure_mapping": hello["v3_closure_mapping"],
        "v3_closure_mapping_sha256": hello["v3_closure_mapping_sha256"],
        "live_authority_mapping": hello["live_authority_mapping"],
        "live_authority_mapping_sha256": hello["live_authority_mapping_sha256"],
        "scientific_payload": scientific_payload,
        "scientific_payload_sha256": sha256_bytes(scientific_raw),
        "solver_call_accounting": solver_call_accounting,
        "solver_call_accounting_sha256": sha256_bytes(
            exact_json_bytes(solver_call_accounting)
        ),
        "scientific_loader_calls": 1,
        "solver_calls": solver_call_accounting["solver_calls"],
        "accepted_as_nonformal_result": accepted,
        "nonformal": True,
        "claim": False,
        "mathematical_infeasibility_inferred_from_failure": False,
        "status": "COMPLETE" if accepted else "HONEST_INCOMPLETE",
    }


def validate_worker_result(value: object, **expected: Any) -> dict[str, Any]:
    return _require_exact_object(
        value, build_worker_result(**expected), label="worker result"
    )


def build_attempt_receipt(
    *,
    hello: dict[str, Any],
    envelope: dict[str, Any],
    result: dict[str, Any],
    result_raw: bytes,
    result_path: str,
) -> dict[str, Any]:
    return {
        "schema": "rq2_public_grid_attempt_receipt_vnext_execution_v2",
        "transport_context": hello_transport_context(hello),
        "hello_sha256": result["hello_sha256"],
        "envelope_sha256": result["envelope_sha256"],
        "result_path": result_path,
        "result_sha256": sha256_bytes(result_raw),
        "scientific_payload_sha256": result["scientific_payload_sha256"],
        "solver_call_accounting_sha256": result["solver_call_accounting_sha256"],
        "pipe_authority_digest": envelope["pipe_authority_digest"],
        "self_bundle_mapping_sha256": result["self_bundle_mapping_sha256"],
        "v3_closure_mapping_sha256": result["v3_closure_mapping_sha256"],
        "live_authority_mapping_sha256": result["live_authority_mapping_sha256"],
        "controller_validated": False,
        "published": False,
        "nonformal": True,
        "claim": False,
    }


def validate_attempt_receipt(value: object, **expected: Any) -> dict[str, Any]:
    return _require_exact_object(
        value, build_attempt_receipt(**expected), label="attempt receipt"
    )


def build_worker_ack(
    *,
    hello: dict[str, Any],
    envelope: dict[str, Any],
    result: dict[str, Any],
    result_raw: bytes,
    receipt_raw: bytes,
) -> dict[str, Any]:
    return {
        "schema": "rq2_public_grid_worker_ack_vnext_execution_v2",
        "transport_context": hello_transport_context(hello),
        "hello_sha256": result["hello_sha256"],
        "envelope_sha256": result["envelope_sha256"],
        "result_sha256": sha256_bytes(result_raw),
        "attempt_receipt_sha256": sha256_bytes(receipt_raw),
        "scientific_payload_sha256": result["scientific_payload_sha256"],
        "solver_call_accounting_sha256": result["solver_call_accounting_sha256"],
        "pipe_authority_digest": envelope["pipe_authority_digest"],
        "self_bundle_mapping_sha256": result["self_bundle_mapping_sha256"],
        "v3_closure_mapping_sha256": result["v3_closure_mapping_sha256"],
        "live_authority_mapping_sha256": result["live_authority_mapping_sha256"],
        "accepted_as_nonformal_result": result[
            "accepted_as_nonformal_result"
        ],
        "nonformal": True,
        "claim": False,
    }


def validate_worker_ack(value: object, **expected: Any) -> dict[str, Any]:
    return _require_exact_object(
        value, build_worker_ack(**expected), label="worker ACK"
    )


def validate_execution_review_object(value: object) -> None:
    config = load_config()
    authority = config["fixed_execution_review"]
    if not isinstance(value, dict):
        raise ContractRejected("execution-review receipt object malformed")
    expected_keys = {
        "schema",
        "version",
        "reviewed_on",
        "reviewer_role",
        "verdict",
        "reviewed_outer",
        "bound_v3_outer",
        "bound_v3_pass_receipt",
        "findings",
        "effect",
    }
    outer = config["bundle"]["outer_path"]
    outer_hash = sha256_bytes(read_stable(ROOT / outer))
    predecessor = config["predecessor_v3"]
    if (
        set(value) != expected_keys
        or value.get("schema") != authority["schema"]
        or value.get("version") != 2
        or value.get("reviewer_role") != "independent_sol_reviewer"
        or value.get("verdict") != "PASS"
        or value.get("findings") != []
        or value.get("reviewed_outer") != {"path": outer, "sha256": outer_hash}
        or value.get("bound_v3_outer")
        != {
            "path": predecessor["outer_path"],
            "sha256": predecessor["outer_sha256"],
        }
        or value.get("bound_v3_pass_receipt")
        != {
            "path": predecessor["pass_receipt_path"],
            "sha256": predecessor["pass_receipt_sha256"],
        }
        or value.get("effect") != authority["effect"]
    ):
        raise ContractRejected("execution-review receipt binding/effect drifted")


def require_execution_review() -> dict[str, Any]:
    if not REVIEW.exists() or REVIEW.is_symlink():
        raise ContractRejected("fixed execution-review PASS receipt is absent")
    first = read_stable(REVIEW)
    try:
        value = json.loads(first)
    except json.JSONDecodeError as exc:
        raise ContractRejected("execution-review receipt JSON malformed") from exc
    validate_execution_review_object(value)
    if read_stable(REVIEW) != first:
        raise ContractRejected("execution-review receipt changed during validation")
    return value


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
    if mode not in {"review-preloader", "science"}:
        raise ContractRejected("worker mode unregistered")
    config = load_config()
    flag = "--internal-review-preloader-worker" if mode == "review-preloader" else "--internal-science-worker"
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
        predecessor_digest if predecessor_digest is not None else "NONE",
        "--nonce",
        nonce,
    )


def process_create_time_ns(pid: int) -> int:
    return v3.process_create_time_ns(pid)


def observe_pipe_endpoint(handle: int, **kwargs: Any) -> dict[str, object]:
    return v3.observe_pipe_endpoint(handle, **kwargs)


def write_frame(descriptor: int, value: object) -> bytes:
    return v3.write_frame(descriptor, value)


def read_frame(descriptor: int, label: str) -> tuple[bytes, dict[str, Any]]:
    return v3.read_frame(descriptor, label)


def require_eof(descriptor: int) -> None:
    v3.require_eof(descriptor)


def run_actual_science(block_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reach the sealed science implementation only after all execution gates pass."""
    require_execution_review()
    verify_live_authorities()
    if block_id not in BLOCKS:
        raise ContractRejected("science block is not frozen")
    from experiments import rq2_public_grid_execution_runtime_contract_v3 as science

    verifier = science.StageAwareClosureVerifier.production()
    integration = science.load_sealed_actual_integration(verifier)
    verify_live_authorities()
    verifier.verify("worker_pre_loader")
    context = integration.v4._stage_context()
    if block_id not in context["blocks"]:
        raise ContractRejected("frozen science block missing")
    data = integration.v4._load_worker_data(context)
    verify_live_authorities()
    payload = integration.v4.recovery.v4._process_block(
        data,
        context["blocks"][block_id],
        dc_bus=int(context["config"]["model"]["dc_bus"]),
        dc_demand_mw=float(context["config"]["model"]["dc_reference_demand_mw"]),
        solver=context["config"]["solver"],
    )
    verify_live_authorities()
    verifier.verify("worker_post_solve_pre_validator")
    validated = integration.validate_scientific_payload(payload, block_id)
    accounting = science.solver_call_accounting(validated)
    verify_live_authorities()
    verifier.verify("worker_post_validator_pre_write")
    return validated, accounting


def validate_actual_science_payload(
    payload: Mapping[str, Any], block_id: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Revalidate returned science bytes without re-solving."""
    require_execution_review()
    verify_live_authorities()
    from experiments import rq2_public_grid_execution_runtime_contract_v3 as science

    integration = science.load_sealed_actual_integration(
        science.StageAwareClosureVerifier.production()
    )
    validated = integration.validate_scientific_payload(payload, block_id)
    accounting = science.solver_call_accounting(validated)
    verify_live_authorities()
    return validated, accounting


def resource_authority() -> Any:
    verify_live_authorities()
    from experiments import run_rq2_public_grid_two_block_pilot_activation_transport_v5

    return run_rq2_public_grid_two_block_pilot_activation_transport_v5


def assert_live_environment() -> None:
    expected = load_config()["runtime"]["sanitized_environment"]
    if Path.cwd() != ROOT or dict(os.environ) != expected:
        raise ContractRejected("worker cwd/environment drifted")
