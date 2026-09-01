"""Fail-closed contract for the reviewed Vnext nonformal execution successor."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from experiments import rq2_public_grid_evidence_publication_contract_v3 as v3

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_v1.json"
REVIEW = ROOT / "configs/rq2_public_grid_two_block_pilot_vnext_execution_successor_review_pass_v1.json"
BLOCKS = ("holdout_s20260822_0008", "holdout_s20260822_0009")


class ContractRejected(RuntimeError):
    """The candidate authority or execution contract failed closed."""


def exact_json_bytes(value: object) -> bytes:
    return v3.exact_json_bytes(value)


def sha256_bytes(raw: bytes) -> str:
    return v3.sha256_bytes(raw)


def read_stable(path: Path) -> bytes:
    try:
        return v3.read_stable(path)
    except Exception as exc:
        raise ContractRejected(f"stable ordinary-file read rejected: {path}") from exc


def load_config() -> dict[str, Any]:
    try:
        value = json.loads(read_stable(CONFIG))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ContractRejected("candidate config JSON malformed") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema")
        != "rq2_public_grid_two_block_pilot_vnext_execution_successor_v1"
        or value.get("status") != "vnext_execution_successor_v1_review_closed"
    ):
        raise ContractRejected("candidate config identity drifted")
    if tuple(value.get("pilot", {}).get("blocks", ())) != BLOCKS:
        raise ContractRejected("fixed two-block order drifted")
    gates = value.get("gates")
    if not isinstance(gates, dict) or any(item is not False for item in gates.values()):
        raise ContractRejected("review-closed gates drifted")
    return value


def _verify_hash(relative: str, expected: str) -> str:
    actual = sha256_bytes(read_stable(ROOT / relative))
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


def verify_live_authorities() -> dict[str, str]:
    """Verify V3, resource, science, interpreter and frozen formal authorities."""
    config = load_config()
    predecessor = config["predecessor_v3"]
    _verify_hash(predecessor["outer_path"], predecessor["outer_sha256"])
    pass_raw = read_stable(ROOT / predecessor["pass_receipt_path"])
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

    bindings: dict[str, str] = {}
    for authority in ("resource_authority", "science_authority"):
        section = config[authority]
        for key, value in section.items():
            if key.endswith("_path"):
                hash_key = f"{key[:-5]}_sha256"
                if hash_key in section:
                    bindings[str(value)] = _verify_hash(str(value), str(section[hash_key]))
    formal = config["formal_protection"]
    for label in ("formal_runner", "activated_config"):
        path = str(formal[f"{label}_path"])
        bindings[path] = _verify_hash(path, str(formal[f"{label}_sha256"]))
    python_path = Path(config["runtime"]["locked_python_executable"])
    if not python_path.is_absolute():
        raise ContractRejected("locked Python path is not absolute")
    if sha256_bytes(read_stable(python_path)) != config["runtime"]["locked_python_sha256"]:
        raise ContractRejected("locked Python hash drifted")
    return dict(sorted({**mapping, **bindings}.items()))


def closure_mapping_sha256(mapping: Mapping[str, str]) -> str:
    return sha256_bytes(exact_json_bytes(dict(sorted(mapping.items()))))


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
        or value.get("version") != 1
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
    verifier.verify("worker_pre_loader")
    context = integration.v4._stage_context()
    if block_id not in context["blocks"]:
        raise ContractRejected("frozen science block missing")
    data = integration.v4._load_worker_data(context)
    payload = integration.v4.recovery.v4._process_block(
        data,
        context["blocks"][block_id],
        dc_bus=int(context["config"]["model"]["dc_bus"]),
        dc_demand_mw=float(context["config"]["model"]["dc_reference_demand_mw"]),
        solver=context["config"]["solver"],
    )
    verifier.verify("worker_post_solve_pre_validator")
    validated = integration.validate_scientific_payload(payload, block_id)
    accounting = science.solver_call_accounting(validated)
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
    return validated, science.solver_call_accounting(validated)


def resource_authority() -> Any:
    verify_live_authorities()
    from experiments import run_rq2_public_grid_two_block_pilot_activation_transport_v5

    return run_rq2_public_grid_two_block_pilot_activation_transport_v5


def assert_live_environment() -> None:
    expected = load_config()["runtime"]["sanitized_environment"]
    if Path.cwd() != ROOT or dict(os.environ) != expected:
        raise ContractRejected("worker cwd/environment drifted")
