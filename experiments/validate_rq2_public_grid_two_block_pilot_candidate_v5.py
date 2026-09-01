"""Pure-read validator for the closed RQ2 two-block pilot candidate v5."""

from __future__ import annotations

import json

from experiments import run_rq2_public_grid_two_block_pilot_candidate_v5 as runner
from experiments import (
    validate_rq2_public_grid_two_block_pilot_candidate_v4 as v4_validator,
)


def validate() -> dict[str, object]:
    predecessor = runner._verify_predecessor_authority()
    chain = runner._inspect_v5_chain()
    config = runner._load_config()
    if config.get("status") != "postcommit_remediation_candidate_v5_execution_closed":
        raise ValueError("candidate v5 closed status drifted")
    gates = runner.recovery._mapping(config.get("gates"), "candidate v5 gates")
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
            raise ValueError(f"candidate v5 gate is not closed: {key}")
    trust = runner.recovery._mapping(
        config.get("external_execution_trust_root"), "v5 external trust root"
    )
    if (
        trust.get("reviewed_outer_path") is not None
        or trust.get("reviewed_outer_sha256") is not None
        or trust.get("dynamic_self_acceptance_forbidden") is not True
        or trust.get("future_execution_successor_required") is not True
    ):
        raise ValueError("candidate v5 external trust root is not fail-closed")
    try:
        runner._verify_v5_execution_chain(None)
    except ValueError as error:
        if "external trust root" not in str(error):
            raise
    else:
        raise ValueError("candidate v5 accepted a missing external trust root")
    rule = runner.recovery._mapping(
        config.get("repair_010_commit_rule"), "repair-010 commit rule"
    )
    for key in (
        "exact_commit_after_exception_is_success",
        "absent_seal_is_honest_incomplete",
        "existing_unprovable_seal_is_commit_indeterminate",
        "terminal_after_exact_success_forbidden",
        "terminal_during_commit_indeterminate_forbidden",
    ):
        if rule.get(key) is not True:
            raise ValueError(f"repair-010 commit rule drifted: {key}")
    roots = runner._pilot_roots(config)
    if any(path.exists() for path in roots.values()):
        raise ValueError("candidate v5 fresh pilot root already exists")
    v4_report = v4_validator.validate()
    return {
        "schema": "rq2_public_grid_two_block_pilot_candidate_validation_v5",
        "validation_passed": True,
        "candidate_v4_inner_sha256": predecessor["v4"]["inner_sha256"],
        "candidate_v4_outer_sha256": predecessor["v4"]["outer_sha256"],
        "candidate_v5_bundle_member_count": len(chain["files"]),
        "candidate_v5_inner_sha256": chain["inner_sha256"],
        "candidate_v5_outer_sha256": chain["outer_sha256"],
        "v4_validation_passed": v4_report["validation_passed"],
        "v4_precommit_source_sha256": runner.V4_PUBLISH_SOURCE_SHA256,
        "repair_010_exact_commit_rule_bound": True,
        "unique_success_commit_point": "exact_immutable_success_directory_rename",
        "success_commit_member_inventory": ["SHA256SUMS.json", "success.json"],
        "pilot_implementation_ready_for_independent_review": True,
        "independent_pre_run_review_passed": False,
        "external_reviewed_outer_sha256": None,
        "execution_successor_present": False,
        "execution_ready": False,
        "pilot_executed": False,
        "fresh_roots_absent": True,
        "formal_snapshot": runner._formal_snapshot(),
        "worker_processes_started": 0,
        "scientific_loader_calls": 0,
        "solver_calls": 0,
        "result_files_written": 0,
        "formal_writes": 0,
        "mathematical_infeasibility_inferred": False,
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
