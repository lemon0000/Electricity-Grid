"""Pure-read validator for the closed RQ2 two-block pilot candidate v4."""

from __future__ import annotations

import json

from experiments import run_rq2_public_grid_two_block_pilot_candidate_v4 as runner
from experiments import (
    validate_rq2_public_grid_solver_recovery_v2 as recovery_validator,
)


def validate() -> dict[str, object]:
    predecessor = runner._verify_predecessor_authority()
    chain = runner._inspect_v4_chain()
    config = runner._load_config()
    if config.get("status") != "rework_candidate_v4_execution_closed":
        raise ValueError("candidate v4 closed status drifted")
    gates = runner.recovery._mapping(config.get("gates"), "candidate v4 gates")
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
            raise ValueError(f"candidate v4 gate is not closed: {key}")
    trust = runner.recovery._mapping(
        config.get("external_execution_trust_root"), "external trust root"
    )
    if (
        trust.get("required_for_any_future_execution") is not True
        or trust.get("reviewed_outer_path") is not None
        or trust.get("reviewed_outer_sha256") is not None
        or trust.get("dynamic_self_acceptance_forbidden") is not True
        or trust.get("future_execution_successor_required") is not True
    ):
        raise ValueError("candidate v4 external trust root is not fail-closed")
    try:
        runner._verify_v4_execution_chain(None)
    except ValueError as error:
        if "external trust root" not in str(error):
            raise
    else:
        raise ValueError("candidate v4 accepted a missing external trust root")
    base = runner._load_yaml(runner.BASE_CONFIG, "scientific source")
    if config.get("scientific_authority", {}).get("solver") != base.get("solver"):
        raise ValueError("candidate v4 solver contract is not exact inheritance")
    context = runner._stage_context()
    roots = runner._pilot_roots(config)
    if any(path.exists() for path in roots.values()):
        raise ValueError("candidate v4 fresh pilot root already exists")
    formal = runner._formal_snapshot(config)
    recovery_report = recovery_validator.validate()
    return {
        "schema": "rq2_public_grid_two_block_pilot_candidate_validation_v4",
        "validation_passed": True,
        "candidate_v1_live_member_count": len(predecessor["v1"]),
        "candidate_v2_live_member_count": len(predecessor["v2"]),
        "candidate_v3_live_member_count": len(predecessor["v3"]),
        "candidate_v4_bundle_member_count": len(chain["files"]),
        "candidate_v4_inner_sha256": chain["inner_sha256"],
        "candidate_v4_outer_sha256": chain["outer_sha256"],
        "recovery_v2_validation_passed": recovery_report["validation_passed"],
        "capability_transport": "duplex_anonymous_pipes_no_request_file",
        "single_frame_bounded_eof_before_ack": True,
        "ordered_immutable_accepted_evidence_ledger": True,
        "exclusive_ordinary_child_logs": True,
        "attempt_validation_publication_states_separated": True,
        "exact_recursive_typed_tree": True,
        "pilot_implementation_ready_for_independent_review": True,
        "independent_pre_run_review_passed": False,
        "external_reviewed_outer_sha256": None,
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
