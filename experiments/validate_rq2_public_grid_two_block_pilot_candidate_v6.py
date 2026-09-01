"""Pure-read validator for the closed RQ2 two-block pilot candidate v6."""

from __future__ import annotations

import json

from experiments import run_rq2_public_grid_two_block_pilot_candidate_v6 as runner
from experiments import (
    validate_rq2_public_grid_two_block_pilot_candidate_v5 as v5_validator,
)


def validate() -> dict[str, object]:
    predecessor = runner._verify_predecessor_authority()
    chain = runner._inspect_v6_chain()
    config = runner._load_config()
    if config.get("status") != "presence_recovery_candidate_v6_execution_closed":
        raise ValueError("candidate v6 closed status drifted")
    gates = runner.recovery._mapping(config.get("gates"), "candidate v6 gates")
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
            raise ValueError(f"candidate v6 gate is not closed: {key}")
    trust = runner.recovery._mapping(
        config.get("external_execution_trust_root"), "v6 external trust root"
    )
    if (
        trust.get("reviewed_outer_path") is not None
        or trust.get("reviewed_outer_sha256") is not None
        or trust.get("dynamic_self_acceptance_forbidden") is not True
        or trust.get("future_execution_successor_required") is not True
    ):
        raise ValueError("candidate v6 external trust root is not fail-closed")
    try:
        runner._verify_v6_execution_chain(None)
    except ValueError as error:
        if "external trust root" not in str(error):
            raise
    else:
        raise ValueError("candidate v6 accepted a missing external trust root")
    contract = runner.recovery._mapping(
        config.get("presence_recovery_contract"), "v6 presence contract"
    )
    for key in (
        "inspect_every_ancestor",
        "reject_posix_symlink",
        "reject_windows_junction_or_reparse",
        "reject_nonanchor_mount",
        "ordinary_terminal_file_or_directory_is_commit_indeterminate",
        "any_terminal_path_appearance_is_commit_indeterminate",
        "clean_absent_success_and_terminal_is_honest_incomplete",
        "committed_success_requires_exact_ordinary_success_directory",
        "committed_success_requires_terminal_chain_clean_absent",
        "outcome_exists_fields_mean_lexical_path_appearance",
        "failure_target_is_never_deleted_or_overwritten",
        "commit_indeterminate_blocks_resume",
    ):
        if contract.get(key) is not True:
            raise ValueError(f"v6 presence contract drifted: {key}")
    if contract.get("broken_alias_is_clean_absent") is not False:
        raise ValueError("v6 broken-alias semantics drifted")
    roots = runner._pilot_roots(config)
    root_presence = {
        key: runner._probe_path(path, label=f"v6 {key} root").audit()
        for key, path in roots.items()
    }
    if any(not item["clean_absent"] for item in root_presence.values()):
        raise ValueError("candidate v6 fresh pilot root is not cleanly absent")
    v5_report = v5_validator.validate()
    return {
        "schema": "rq2_public_grid_two_block_pilot_candidate_validation_v6",
        "validation_passed": True,
        "candidate_v5_inner_sha256": predecessor["v5"]["inner_sha256"],
        "candidate_v5_outer_sha256": predecessor["v5"]["outer_sha256"],
        "candidate_v6_bundle_member_count": len(chain["files"]),
        "candidate_v6_inner_sha256": chain["inner_sha256"],
        "candidate_v6_outer_sha256": chain["outer_sha256"],
        "v5_validation_passed": v5_report["validation_passed"],
        "v4_precommit_source_sha256": runner.V4_PUBLISH_SOURCE_SHA256,
        "v5_source_sha256": dict(runner.V5_SOURCE_HASHES),
        "presence_recovery_gate_bound": True,
        "path_presence_uses_lexists_lstat_before_resolve": True,
        "fresh_root_presence": root_presence,
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
