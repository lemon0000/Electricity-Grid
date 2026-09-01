"""Review-closed worker for execution-controller successor v3."""

from __future__ import annotations

import argparse
import json
import os
import secrets
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from experiments import rq2_public_grid_execution_runtime_contract_v3 as contract

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v3.json"
REVIEW = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_review_pass_v3.json"


class SuccessorV3WorkerRejected(RuntimeError):
    """The successor-v3 worker failed closed."""


def _load_config() -> dict[str, Any]:
    value = json.loads(contract.predecessor.read_stable_bytes(CONFIG))
    if not isinstance(value, dict) or value.get("status") != (
        "execution_controller_successor_v3_review_closed"
    ):
        raise SuccessorV3WorkerRejected("successor-v3 config identity drifted")
    return value


def verify_live_closure() -> tuple[str, ...]:
    return contract.verify_full_live_closure(ROOT, _load_config())


def build_test_envelope(*, block_id: str, output_root: Path) -> dict[str, object]:
    """Build only the fields consumed by the sealed v4 result constructors."""
    if block_id not in _load_config()["pilot"]["blocks"]:
        raise SuccessorV3WorkerRejected("test envelope block is unregistered")
    integration = contract.load_sealed_actual_integration(
        contract.StageAwareClosureVerifier.production()
    )
    nonce = secrets.token_hex(32)
    execution_index = _load_config()["pilot"]["blocks"].index(block_id) + 1
    attempt_root = output_root / block_id / nonce
    return {
        "authority": integration.v4._candidate_authority(),
        "block_id": block_id,
        "execution_index": execution_index,
        "predecessor_accepted_evidence": None,
        "nonce": nonce,
        "parent_process_identity": {"pid": os.getpid()},
        "worker_process_identity": {"pid": os.getpid()},
        "worker_payload_path": str(attempt_root / "payload.json"),
        "attempt_receipt_path": str(attempt_root / "attempt_receipt.json"),
    }


def finalize_existing_scientific_payload_for_test(
    *,
    envelope: Mapping[str, Any],
    payload: Mapping[str, Any],
    verifier: contract.StageAwareClosureVerifier,
) -> dict[str, object]:
    """Exercise the real post-solve validator/write/ACK boundaries without solving."""
    verifier.verify("worker_post_solve_pre_validator")
    integration = contract.load_sealed_actual_integration(verifier)
    block_id = str(envelope["block_id"])
    validated = integration.validate_scientific_payload(payload, block_id)
    accounting = contract.solver_call_accounting(validated)
    verifier.verify("worker_post_validator_pre_write")

    payload_path = Path(str(envelope["worker_payload_path"]))
    receipt_path = Path(str(envelope["attempt_receipt_path"]))
    expected_root = payload_path.parent
    if receipt_path != expected_root / "attempt_receipt.json" or payload_path.name != "payload.json":
        raise SuccessorV3WorkerRejected("worker result paths drifted")
    expected_root.mkdir(parents=True, exist_ok=False)
    result = integration.v4._build_worker_result(envelope, validated)
    integration.v4.recovery._atomic_json(payload_path, result)
    integration.v4.recovery._atomic_json(
        receipt_path,
        integration.v4._build_attempt_receipt(envelope, payload_path),
    )
    verifier.verify("worker_post_write_pre_ack")
    ack = integration.v4._build_ack(envelope)
    return {
        "ack": ack,
        "solver_call_accounting": accounting,
        "accepted": validated.get("all_hours_resolved") is True,
    }


def _production(
    envelope: Mapping[str, Any], verifier: contract.StageAwareClosureVerifier
) -> dict[str, object]:
    verifier.verify("worker_pre_loader")
    integration = contract.load_sealed_actual_integration(verifier)
    context = integration.v4._stage_context()
    block_id = str(envelope["block_id"])
    data = integration.v4._load_worker_data(context)
    payload = integration.v4.recovery.v4._process_block(
        data,
        context["blocks"][block_id],
        dc_bus=int(context["config"]["model"]["dc_bus"]),
        dc_demand_mw=float(context["config"]["model"]["dc_reference_demand_mw"]),
        solver=context["config"]["solver"],
    )
    return finalize_existing_scientific_payload_for_test(
        envelope=envelope, payload=payload, verifier=verifier
    )


def _parse(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--internal-successor-v3-worker", action="store_true")
    parser.add_argument("--read-handle", type=int)
    parser.add_argument("--ack-handle", type=int)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse(argv)
    verify_live_closure()
    if (
        not args.internal_successor_v3_worker
        or args.read_handle is None
        or args.ack_handle is None
    ):
        raise SuccessorV3WorkerRejected("public/malformed worker invocation rejected")
    if not REVIEW.exists():
        raise SuccessorV3WorkerRejected(
            "external v3 execution review receipt is absent before pipe/data load"
        )
    raise SuccessorV3WorkerRejected("v3 production transport is review closed")


if __name__ == "__main__":
    raise SystemExit(main())
