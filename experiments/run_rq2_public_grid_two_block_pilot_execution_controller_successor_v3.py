"""Review-closed execution controller successor v3.

The executable pilot remains closed pending an external review receipt.  The
functions below bind controller acceptance and publication to the v3 staged
live-closure verifier and to the sealed v4/v7 implementations.
"""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from experiments import rq2_public_grid_execution_runtime_contract_v3 as contract

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v3.json"
REVIEW = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_review_pass_v3.json"


class SuccessorV3Rejected(RuntimeError):
    """The closed successor-v3 controller rejected an invocation."""


def _load_config() -> dict[str, Any]:
    value = json.loads(contract.predecessor.read_stable_bytes(CONFIG))
    if not isinstance(value, dict) or value.get("status") != (
        "execution_controller_successor_v3_review_closed"
    ):
        raise SuccessorV3Rejected("successor-v3 config identity drifted")
    return value


def verify_live_closure() -> tuple[str, ...]:
    return contract.verify_full_live_closure(ROOT, _load_config())


def accept_after_child(
    evidence: Any,
    *,
    ledger: Any,
    verifier: contract.StageAwareClosureVerifier,
) -> None:
    """Accept one sealed v4 evidence record only after a fresh full closure."""
    verifier.verify("controller_post_child_pre_accept")
    integration = contract.load_sealed_actual_integration(verifier)
    if not isinstance(evidence, integration.v4.AcceptedEvidence):
        raise SuccessorV3Rejected("child evidence type is not sealed AcceptedEvidence")
    if not isinstance(ledger, integration.v4.ControllerLedger):
        raise SuccessorV3Rejected("controller ledger type is not sealed ControllerLedger")
    ledger.accept(evidence)


def _indeterminate_after_postpublish_drift(
    *, ledger: Any, error: contract.LiveClosureDrift
) -> dict[str, object]:
    return {
        "classification": "commit_indeterminate",
        "published": False,
        "claim": False,
        "formal_execution_ready": False,
        "security_certified": False,
        "ledger_digest": ledger.digest,
        "reason": str(error),
        "artifact_cleanup_performed": False,
        "mathematical_infeasibility_inferred": False,
    }


def publish_with_stage_gates(
    *,
    staging: Path,
    target: Path,
    success: Path,
    terminal: Path,
    publication_config: Mapping[str, Any],
    controller_receipt: Mapping[str, Any],
    ledger: Any,
    verifier: contract.StageAwareClosureVerifier,
    registered_test_race: str | None = None,
) -> dict[str, object]:
    """Call the actual sealed v7 publisher behind both live-closure gates."""
    verifier.verify("controller_post_block2_pre_publish")
    integration = contract.load_sealed_actual_integration(verifier)
    if not isinstance(ledger, integration.v4.ControllerLedger) or len(ledger.records) != 2:
        raise SuccessorV3Rejected("publication requires exact sealed two-record ledger")
    for evidence in ledger.records:
        integration.v4._revalidate_memory_evidence(
            evidence,
            payload_path=evidence.source_payload_path,
            receipt_path=evidence.source_attempt_receipt_path,
        )
    expected_controller = integration.build_controller_receipt(
        publication_config, ledger
    )
    if dict(controller_receipt) != expected_controller:
        raise SuccessorV3Rejected("controller receipt binding drifted")

    post_commit_hook = None
    if registered_test_race is not None:
        if registered_test_race != "terminal_after_commit":
            raise SuccessorV3Rejected("unregistered publication race seam")

        def create_terminal_after_commit(_success: Path, _expectation: Any) -> None:
            terminal.mkdir(parents=False, exist_ok=False)

        post_commit_hook = create_terminal_after_commit

    outcome = integration.publish(
        staging,
        target,
        success,
        terminal,
        config=publication_config,
        controller=controller_receipt,
        ledger=ledger,
        post_commit_test_hook=post_commit_hook,
    )
    try:
        verifier.verify("controller_post_publish")
    except contract.LiveClosureDrift as exc:
        return _indeterminate_after_postpublish_drift(ledger=ledger, error=exc)
    return dict(outcome)


def _closed_runtime_status() -> dict[str, object]:
    config = _load_config()
    verify_live_closure()
    roots_absent = all(
        not os.path.lexists(ROOT / relative) for relative in config["paths"].values()
    )
    if not roots_absent:
        raise SuccessorV3Rejected("successor-v3 root appearance rejected")
    return {
        "validation_passed": True,
        "execution_review_present": REVIEW.exists(),
        "execution_ready": False,
        "dependency_closure_verified": True,
        "workers": 0,
        "loader_calls": 0,
        "solver_calls": 0,
        "result_writes": 0,
        "formal_writes": 0,
    }


def _parse(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse(argv)
    if args.validate_only and not args.execute:
        print(json.dumps(_closed_runtime_status(), sort_keys=True))
        return 0
    if args.execute and not args.validate_only:
        verify_live_closure()
        raise SuccessorV3Rejected("external v3 execution review receipt is absent")
    raise SuccessorV3Rejected("exactly one registered controller mode is required")


if __name__ == "__main__":
    raise SystemExit(main())
