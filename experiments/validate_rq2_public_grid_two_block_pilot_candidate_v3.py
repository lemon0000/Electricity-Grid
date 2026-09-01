"""Pure-read validator for the closed RQ2 two-block pilot candidate v3."""

from __future__ import annotations

import json

from experiments import run_rq2_public_grid_two_block_pilot_candidate_v3 as runner
from experiments import (
    validate_rq2_public_grid_solver_recovery_v2 as recovery_validator,
)


def validate() -> dict[str, object]:
    predecessor = runner._verify_predecessor_authority()
    runner._verify_recovery_and_semantic_authority()
    files = runner._verify_v3_chain()
    config, authorization = runner._load_authority()
    if config.get("status") != "remediation_candidate_v3_execution_closed":
        raise ValueError("candidate v3 closed status drifted")
    if authorization.get("effect", {}).get("no_execution_authority") is not True:
        raise ValueError("candidate v3 authorization is not fail-closed")
    gates = runner.recovery._mapping(config.get("gates"), "candidate v3 gates")
    for key in (
        "independent_pre_run_review_passed",
        "execution_successor_present",
        "two_block_pilot_execution_ready",
        "two_block_pilot_executed",
        "named_outage_comparison_passed",
        "post_result_review_passed",
        "formal_activation_present",
        "formal_execution_ready",
        "user_formal_run_authorized",
        "formal_result_exists",
        "claim",
        "security_certified",
    ):
        if gates.get(key) is not False:
            raise ValueError(f"candidate v3 gate is not closed: {key}")
    status = runner._execution_authority_status(config, authorization)
    if any(status.values()):
        raise ValueError("candidate v3 runtime execution status is not wholly closed")
    base = runner._load_yaml(runner.BASE_CONFIG, "scientific source")
    if config.get("scientific_authority", {}).get("solver") != base.get("solver"):
        raise ValueError("candidate v3 solver contract is not exact inheritance")
    context = runner._stage_context()
    roots = runner._pilot_roots(config)
    if any(path.exists() for path in roots.values()):
        raise ValueError("candidate v3 fresh pilot root already exists")
    formal = runner._formal_snapshot(config)
    recovery_report = recovery_validator.validate()
    return {
        "schema": "rq2_public_grid_two_block_pilot_candidate_validation_v3",
        "validation_passed": True,
        "candidate_v1_live_member_count": len(predecessor["v1_members"]),
        "candidate_v2_live_member_count": len(predecessor["v2_members"]),
        "candidate_v3_bundle_member_count": len(files),
        "candidate_v3_outer_sha256": runner.recovery._sha256(runner.OUTER),
        "recovery_v2_validation_passed": recovery_report["validation_passed"],
        "capability_transport": "duplex_anonymous_pipes_no_request_file",
        "file_level_request_bypass_rejected": True,
        "same_permission_process_injection_resisted": False,
        "exact_recursive_typed_tree": True,
        "pilot_implementation_ready_for_independent_review": True,
        "independent_pre_run_review_passed": False,
        "execution_successor_present": False,
        "execution_ready": False,
        "pilot_executed": False,
        "fresh_roots_absent": True,
        "pilot_blocks": list(runner.BLOCKS),
        "block_hour_counts": {
            block_id: len(context["blocks"][block_id]) for block_id in runner.BLOCKS
        },
        "formal_snapshot": formal,
        "worker_processes_started": 0,
        "solver_calls": 0,
        "result_files_written": 0,
        "formal_writes": 0,
        "formal_execution_ready": False,
        "user_formal_run_authorized": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }


def main() -> None:
    print(json.dumps(validate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
