"""Pure-read validator for the closed RQ2 two-block pilot candidate v7."""

from __future__ import annotations

import json

from experiments import run_rq2_public_grid_two_block_pilot_candidate_v7 as runner
from experiments import (
    validate_rq2_public_grid_two_block_pilot_candidate_v6 as v6_validator,
)


def validate() -> dict[str, object]:
    predecessor = runner._verify_predecessor_authority()
    chain = runner._inspect_v7_chain()
    config = runner._load_config()
    if (
        config.get("status")
        != "publication_presence_snapshot_candidate_v7_execution_closed"
    ):
        raise ValueError("candidate v7 closed status drifted")
    gates = runner.recovery._mapping(config.get("gates"), "candidate v7 gates")
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
            raise ValueError(f"candidate v7 gate is not closed: {key}")
    trust = runner.recovery._mapping(
        config.get("external_execution_trust_root"), "v7 external trust root"
    )
    if (
        trust.get("reviewed_outer_path") is not None
        or trust.get("reviewed_outer_sha256") is not None
        or trust.get("dynamic_self_acceptance_forbidden") is not True
        or trust.get("future_execution_successor_required") is not True
    ):
        raise ValueError("candidate v7 external trust root is not fail-closed")
    try:
        runner._verify_v7_execution_chain(None)
    except ValueError as error:
        if "external trust root" not in str(error):
            raise
    else:
        raise ValueError("candidate v7 accepted a missing external trust root")
    contract = runner.recovery._mapping(
        config.get("publication_presence_snapshot_contract"), "v7 snapshot contract"
    )
    for key in (
        "immutable_deep_snapshot",
        "capture_before_any_classification_branch_or_resolve",
        "inspect_every_ancestor",
        "independent_reprobe_within_decision_forbidden",
        "any_terminal_appearance_is_commit_indeterminate",
        "any_file_alias_reparse_mount_inaccessible_or_nonordinary_is_commit_indeterminate",
        "corrupt_mismatch_or_dual_state_is_commit_indeterminate",
        "committed_success_requires_exact_complete_result_and_bound_success",
        "committed_success_requires_clean_absent_terminal",
        "final_acceptance_requires_one_new_complete_snapshot_and_full_revalidation",
        "snapshot_is_logically_consistent_not_os_transactional",
    ):
        if contract.get(key) is not True:
            raise ValueError(f"v7 snapshot contract drifted: {key}")
    if contract.get("same_privilege_adversarial_process_race_resistance_claimed") is not False:
        raise ValueError("v7 snapshot threat model drifted")

    roots = runner._pilot_roots(config)
    publication_snapshot = runner._capture_publication_presence_snapshot(
        target=roots["result"],
        success_directory=roots["success_commit"],
        terminal_directory=roots["forbidden_terminal"],
    )
    if runner._snapshot_state(publication_snapshot) != "honest_incomplete" or not all(
        presence.eligible_clean_absent
        for presence in (
            publication_snapshot.result,
            publication_snapshot.success,
            publication_snapshot.terminal,
        )
    ):
        raise ValueError("candidate v7 publication roots are not cleanly absent")
    auxiliary_presence = {
        key: runner._probe_one_path(path, label=f"v7 {key} root").audit()
        for key, path in roots.items()
        if key in {"worker", "log"}
    }
    if any(not item["clean_absent"] for item in auxiliary_presence.values()):
        raise ValueError("candidate v7 auxiliary root is not cleanly absent")
    v6_report = v6_validator.validate()
    return {
        "schema": "rq2_public_grid_two_block_pilot_candidate_validation_v7",
        "validation_passed": True,
        "candidate_v6_inner_sha256": predecessor["v6"]["inner_sha256"],
        "candidate_v6_outer_sha256": predecessor["v6"]["outer_sha256"],
        "candidate_v7_bundle_member_count": len(chain["files"]),
        "candidate_v7_inner_sha256": chain["inner_sha256"],
        "candidate_v7_outer_sha256": chain["outer_sha256"],
        "v6_validation_passed": v6_report["validation_passed"],
        "v4_precommit_source_sha256": runner.V4_PUBLISH_SOURCE_SHA256,
        "v6_source_sha256": dict(runner.V6_SOURCE_HASHES),
        "immutable_publication_presence_snapshot_bound": True,
        "publication_snapshot": publication_snapshot.audit(),
        "auxiliary_root_presence": auxiliary_presence,
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
