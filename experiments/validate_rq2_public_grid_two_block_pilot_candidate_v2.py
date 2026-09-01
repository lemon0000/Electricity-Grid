"""Pure-read validator for the permanently closed RQ2 two-block pilot v2 candidate."""

from __future__ import annotations

import json

from experiments import run_rq2_public_grid_two_block_pilot_candidate_v2 as runner
from experiments import (
    validate_rq2_public_grid_solver_recovery_v2 as recovery_validator,
)


def validate() -> dict[str, object]:
    files = runner._verify_bundle_chain()
    runner._verify_recovery_authority()
    runner._verify_semantic_authority()
    config, activation = runner._load_authority()
    if (
        config.get("status") != "pre_run_rework_successor_execution_closed"
        or activation.get("status")
        != "user_authorized_rework_candidate_pre_run_review_pending"
    ):
        raise ValueError("candidate v2 closed status drifted")
    gates = runner.recovery._mapping(config.get("gates"), "candidate gates")
    for key in (
        "independent_pre_run_review_passed",
        "execution_successor_present",
        "two_block_pilot_execution_ready",
        "two_block_pilot_executed",
        "named_outage_comparison_passed",
        "post_result_review_passed",
        "formal_execution_ready",
        "user_formal_run_authorized",
        "formal_result_exists",
        "claim",
        "security_certified",
    ):
        if gates.get(key) is not False:
            raise ValueError(f"candidate v2 gate is not closed: {key}")
    if activation.get("candidate_authority", {}).get("pre_run_review_receipt_path") is not None:
        raise ValueError("candidate v2 cannot carry a pre-run PASS receipt")
    status = runner._execution_authority_status(config, activation)
    if (
        status["independent_pre_run_review_passed"] is not False
        or status["execution_successor_present"] is not False
        or status["two_block_pilot_execution_ready"] is not False
        or status["formal_execution_closed"] is not True
        or status["claims_closed"] is not True
    ):
        raise ValueError("candidate v2 runtime authority is not fail-closed")
    base = runner._load_yaml(runner.BASE_CONFIG, "scientific source")
    if config.get("scientific_authority", {}).get("solver") != base.get("solver"):
        raise ValueError("candidate v2 solver contract is not exact inheritance")
    context = runner._stage_context()
    for block_id in runner.BLOCKS:
        rows = context["blocks"][block_id]
        if (
            len(rows) != 24
            or [row["block_id"] for row in rows] != [block_id] * 24
            or [row["hour_offset"] for row in rows] != [str(index) for index in range(24)]
        ):
            raise ValueError(f"candidate v2 block inventory drifted: {block_id}")
    roots = runner._pilot_roots(config)
    if any(path.exists() for path in roots.values()):
        raise ValueError("candidate v2 fresh pilot root already exists")
    formal = runner._formal_snapshot(config)
    recovery_report = recovery_validator.validate()
    return {
        "schema": "rq2_public_grid_two_block_pilot_candidate_validation_v2",
        "validation_passed": True,
        "rejected_candidate_v1_outer_sha256": runner.V1_OUTER_SHA256,
        "candidate_outer_sha256": runner.recovery._sha256(runner.OUTER),
        "bundle_member_count": len(files),
        "recovery_v2_validation_passed": recovery_report["validation_passed"],
        "recovery_v2_live_member_count": len(runner.RECOVERY_MEMBERS),
        "semantic_v1_authority_valid": True,
        "pilot_implementation_ready_for_independent_review": True,
        "user_two_block_pilot_authorized": True,
        "independent_pre_run_review_passed": False,
        "execution_successor_present": False,
        "execution_ready": False,
        "pilot_executed": False,
        "fresh_roots_absent": True,
        "pilot_blocks": runner.BLOCKS,
        "formal_snapshot": formal,
        "solver_calls": 0,
        "result_files_written": 0,
        "formal_writes": 0,
        "formal_execution_ready": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }


def main() -> None:
    print(json.dumps(validate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
