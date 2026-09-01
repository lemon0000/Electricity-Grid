"""Pure-read validator for the closed RQ2 0008/0009 pilot candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from experiments import run_rq2_public_grid_two_block_pilot_candidate_v1 as runner
from experiments import (
    validate_rq2_public_grid_solver_recovery_v2 as recovery_validator,
)

ROOT = Path(__file__).resolve().parents[1]


def _validate_pass_receipt() -> dict[str, Any]:
    receipt = runner._load_yaml(runner.PASS_RECEIPT, "implementation PASS receipt")
    if (
        receipt.get("schema")
        != "rq2_public_grid_solver_recovery_implementation_review_pass_v2"
        or receipt.get("reviewed_on") != "2026-08-30"
        or receipt.get("reviewer_role") != "independent_sol_reviewer"
        or receipt.get("verdict") != "PASS"
    ):
        raise ValueError("implementation PASS receipt identity drifted")
    reviewed = runner.recovery._mapping(receipt.get("reviewed_bundle"), "reviewed bundle")
    if (
        reviewed.get("path")
        != "configs/rq2_public_grid_solver_recovery_v2.SHA256SUMS.json"
        or reviewed.get("sha256")
        != "b300a040fc481beea094702404f4d00eb176403e40f7909d2d704f7fd2195729"
        or reviewed.get("exact_member_count") != 7
    ):
        raise ValueError("implementation PASS bundle binding drifted")
    manifest = runner.recovery._mapping(
        runner._load_json(ROOT / str(reviewed["path"]), "recovery v2 manifest"),
        "recovery v2 manifest",
    )
    if manifest != reviewed.get("members") or runner.recovery._sha256(
        ROOT / str(reviewed["path"])
    ) != reviewed["sha256"]:
        raise ValueError("implementation PASS live member binding drifted")
    for relative, expected in manifest.items():
        path = ROOT / relative
        if not path.is_file() or path.is_symlink() or runner.recovery._sha256(path) != expected:
            raise ValueError(f"recovery v2 reviewed member drifted: {relative}")
    effect = runner.recovery._mapping(receipt.get("effect"), "PASS effect")
    if (
        effect.get("recovery_v2_implementation_review_passed") is not True
        or effect.get("two_block_pilot_implementation_authorized") is not True
        or effect.get("two_block_pilot_execution_authorized") is not False
        or effect.get("formal_execution_ready") is not False
        or effect.get("claim") is not False
        or effect.get("security_certified") is not False
    ):
        raise ValueError("implementation PASS effect drifted")
    return receipt


def _validate_science(config: dict[str, Any]) -> dict[str, Any]:
    authority = runner.recovery._mapping(
        config.get("scientific_authority"), "scientific authority"
    )
    if (
        authority.get("config_path")
        != "configs/rts_gmlc_public_grid_need_dispatch_v4_highs_process_isolated_v1.yaml"
        or authority.get("config_sha256")
        != "e1306a375bba5d19d687cb2728a981528662064226b4661a0b74f894b647f3bd"
        or authority.get("exact_inherited_fields")
        != ["input", "grid_source", "model", "solver"]
        or runner.recovery._sha256(runner.BASE_CONFIG) != authority["config_sha256"]
    ):
        raise ValueError("scientific source binding drifted")
    base = runner._load_yaml(runner.BASE_CONFIG, "scientific source")
    if authority.get("solver") != base.get("solver"):
        raise ValueError("HiGHS solver contract is not exact inheritance")
    process = base["execution"]["process_isolation"]
    pilot = runner.recovery._mapping(config.get("pilot"), "pilot")
    expected_resources = {
        "external_watchdog_seconds": 21600,
        "resource_sample_interval_seconds": 5.0,
        "private_commit_limit_gib": 8.0,
        "minimum_system_commit_available_gib": 2.0,
    }
    if any(pilot.get(key) != value or process.get(key) != value for key, value in expected_resources.items()):
        raise ValueError("pilot resource inheritance drifted")
    if (
        pilot.get("blocks") != runner.BLOCKS
        or pilot.get("execution_order") != runner.BLOCKS
        or pilot.get("one_fresh_python_worker_per_block") is not True
        or pilot.get("controller_calls_solver") is not False
        or pilot.get("worker_calls_complete_v4_process_block") is not True
    ):
        raise ValueError("pilot execution contract drifted")
    context = runner._stage_context()
    for block_id in runner.BLOCKS:
        rows = context["blocks"][block_id]
        if (
            len(rows) != 24
            or [row["block_id"] for row in rows] != [block_id] * 24
            or [row["hour_offset"] for row in rows] != [str(index) for index in range(24)]
        ):
            raise ValueError(f"pilot 24-hour inventory drifted: {block_id}")
    return base


def _validate_semantics(config: dict[str, Any]) -> None:
    semantic = runner.recovery._mapping(
        config.get("semantic_authority"), "semantic authority"
    )
    expected = {
        "config_path": "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml",
        "config_sha256": "cb0209a9a53962be8ebb6ee185d3bfbf3d004d7cd761e164b286a58e0c7887b0",
        "manifest_path": "configs/rq2_public_solver_pilot_semantic_successor_v1.SHA256SUMS.json",
        "manifest_sha256": "c0b1a6a3074343ab5f281b268cd40898630ad1e2234830a4536189687832f471",
        "validator_path": "experiments/validate_rq2_public_solver_pilot_semantic_successor_v1.py",
        "validator_sha256": "01b7f60a620c81a7a656ba6576c3b85af9e371b30d42dd5959f430ee220c80dd",
        "review_verdict": "PASS",
    }
    if semantic != expected:
        raise ValueError("semantic authority declaration drifted")
    for key in ("config", "manifest", "validator"):
        path = ROOT / semantic[f"{key}_path"]
        if not path.is_file() or path.is_symlink() or runner.recovery._sha256(path) != semantic[f"{key}_sha256"]:
            raise ValueError(f"semantic {key} authority drifted")
    comparison = runner.recovery._mapping(
        config.get("named_outage_comparison"), "comparison contract"
    )
    if (
        comparison.get("block_id") != runner.BLOCKS[0]
        or comparison.get("maximum_finite_grid_need_difference_mw") != 1.0e-5
        or comparison.get("maximum_baseline_incumbent_difference_usd") != 1.0e-4
        or comparison.get("require_finite_certificate_intervals_overlap") is not True
        or comparison.get("require_baseline_intervals_overlap") is not True
        or comparison.get("require_E0_and_zero_confirmation_semantics_equal") is not True
        or comparison.get("compare_raw_status_for_equality") is not False
        or comparison.get("block_0009_cross_solver_comparison_required") is not False
        or comparison.get("comparison_failure_is_infeasibility_evidence") is not False
    ):
        raise ValueError("named-outage comparison contract drifted")
    for path_key, hash_key in (
        ("frozen_gurobi_checkpoint_path", "frozen_gurobi_checkpoint_sha256"),
        ("frozen_gurobi_config_path", "frozen_gurobi_config_sha256"),
    ):
        path = ROOT / comparison[path_key]
        if not path.is_file() or path.is_symlink() or runner.recovery._sha256(path) != comparison[hash_key]:
            raise ValueError(f"comparison authority drifted: {path_key}")


def _validate_activation_and_gates(
    config: dict[str, Any], activation: dict[str, Any]
) -> None:
    if (
        activation.get("schema")
        != "rq2_public_grid_two_block_pilot_user_activation_v1"
        or activation.get("status") != "user_authorized_candidate_pre_run_review_pending"
        or activation.get("user_authority", {}).get("user_two_block_pilot_authorized")
        is not True
        or activation.get("user_authority", {}).get("user_formal_run_authorized")
        is not False
        or activation.get("candidate_authority", {}).get("pre_run_review_receipt_path")
        is not None
    ):
        raise ValueError("candidate user activation drifted")
    gates = runner.recovery._mapping(config.get("gates"), "candidate gates")
    if (
        gates.get("recovery_v2_implementation_review_passed") is not True
        or gates.get("user_two_block_pilot_authorized") is not True
        or gates.get("candidate_implementation_ready") is not True
        or any(
            gates.get(key) is not False
            for key in (
                "independent_pre_run_review_passed", "execution_successor_present",
                "two_block_pilot_execution_ready", "two_block_pilot_executed",
                "named_outage_comparison_passed", "post_result_review_passed",
                "formal_execution_ready", "user_formal_run_authorized",
                "formal_result_exists", "claim", "security_certified",
            )
        )
    ):
        raise ValueError("candidate gate is not closed")
    status = runner._execution_authority_status(config, activation)
    if (
        status["independent_pre_run_review_passed"] is not False
        or status["execution_successor_present"] is not False
        or status["two_block_pilot_execution_ready"] is not False
        or status["formal_execution_closed"] is not True
        or status["claims_closed"] is not True
    ):
        raise ValueError("runtime execution authority is not fail-closed")


def _validate_roots(config: dict[str, Any]) -> tuple[dict[str, Path], int]:
    roots = runner._pilot_roots(config)
    for name, path in roots.items():
        if path.exists():
            raise ValueError(f"fresh pilot root already exists: {name}")
    existing_results = sum(
        item.is_dir() for item in (ROOT / "results/tables").iterdir()
    )
    return roots, existing_results


def validate() -> dict[str, object]:
    files = runner._verify_bundle_chain()
    config, activation = runner._load_authority()
    if (
        config.get("status") != "pre_run_review_candidate_execution_closed"
        or config.get("version") != 1
        or config.get("frozen_on") != "2026-08-30"
    ):
        raise ValueError("candidate identity drifted")
    _validate_pass_receipt()
    recovery_report = recovery_validator.validate()
    base = _validate_science(config)
    _validate_semantics(config)
    _validate_activation_and_gates(config, activation)
    roots, existing_result_count = _validate_roots(config)
    formal = runner._formal_snapshot(config)
    return {
        "schema": "rq2_public_grid_two_block_pilot_candidate_validation_v1",
        "validation_passed": True,
        "candidate_outer_sha256": runner.recovery._sha256(runner.OUTER),
        "bundle_member_count": len(files),
        "implementation_pass_receipt_valid": True,
        "recovery_v2_validation_passed": recovery_report["validation_passed"],
        "pilot_implementation_ready": True,
        "user_two_block_pilot_authorized": True,
        "independent_pre_run_review_passed": False,
        "execution_successor_present": False,
        "execution_ready": False,
        "pilot_executed": False,
        "post_result_review_passed": False,
        "solver_name": base["solver"]["name"],
        "solver_expected_package_version": base["solver"]["expected_package_version"],
        "pilot_blocks": runner.BLOCKS,
        "fresh_roots_absent": all(not path.exists() for path in roots.values()),
        "existing_result_directory_count_checked": existing_result_count,
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
