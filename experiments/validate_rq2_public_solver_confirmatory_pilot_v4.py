"""Fail-closed validator for the reviewed RQ2 confirmatory pilot v4 successor."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from experiments.run_rq2_public_solver_confirmatory_pilot_v4 import (
    EXPECTED_RUNS,
    PROCESS_EVIDENCE_SCOPE,
    SEMANTIC_VALIDATION_SCHEMA,
    V3_OUTER_SHA256,
    _assert_evaluator_report,
    _load_scientific_parent,
    _reconstruct_runs,
)
from experiments.validate_rq2_public_solver_confirmatory_pilot_v3 import (
    _list,
    _load_json_strict,
    _mapping,
    _ordinary,
    _sha256,
)
from experiments.validate_rq2_public_solver_confirmatory_pilot_v3 import (
    validate as validate_v3,
)
from experiments.validate_rq2_public_solver_pilot_semantic_successor_v1 import (
    evaluate_runs,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = "configs/rq2_public_solver_confirmatory_pilot_v4.yaml"
BUNDLE_RELATIVE = "configs/rq2_public_solver_confirmatory_pilot_bundle_v4.SHA256SUMS.json"
OUTER_RELATIVE = "configs/rq2_public_solver_confirmatory_pilot_bundle_v4.OUTER.SHA256SUMS.json"
PASS_RECEIPT_RELATIVE = "configs/rq2_public_solver_confirmatory_pilot_implementation_review_pass_v4.yaml"
ACTIVATION_RELATIVE = "configs/rq2_public_solver_confirmatory_pilot_activation_v4.yaml"
RUNNER_RELATIVE = "experiments/run_rq2_public_solver_confirmatory_pilot_v4.py"
VALIDATOR_RELATIVE = "experiments/validate_rq2_public_solver_confirmatory_pilot_v4.py"
TESTS_RELATIVE = "tests/test_rq2_public_solver_confirmatory_pilot_v4.py"
RESULT_RELATIVE = "results/tables/rq2_public_solver_confirmatory_pilot_v4"
RESULT_SCHEMA = "rq2_public_solver_confirmatory_pilot_v4"
V3_CONFIG_RELATIVE = "configs/rq2_public_solver_confirmatory_pilot_v3.yaml"
V3_BUNDLE_RELATIVE = "configs/rq2_public_solver_confirmatory_pilot_bundle_v3.SHA256SUMS.json"
V3_OUTER_RELATIVE = "configs/rq2_public_solver_confirmatory_pilot_bundle_v3.OUTER.SHA256SUMS.json"
SEMANTIC_CONFIG_RELATIVE = "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml"
SEMANTIC_MANIFEST_RELATIVE = "configs/rq2_public_solver_pilot_semantic_successor_v1.SHA256SUMS.json"
CONFIG = ROOT / CONFIG_RELATIVE
BUNDLE = ROOT / BUNDLE_RELATIVE
OUTER = ROOT / OUTER_RELATIVE
RESULT = ROOT / RESULT_RELATIVE
SEMANTIC_CONFIG = ROOT / SEMANTIC_CONFIG_RELATIVE
BUNDLE_INVENTORY = {
    CONFIG_RELATIVE,
    PASS_RECEIPT_RELATIVE,
    ACTIVATION_RELATIVE,
    RUNNER_RELATIVE,
    VALIDATOR_RELATIVE,
    TESTS_RELATIVE,
}
V3_HASHES = {
    V3_CONFIG_RELATIVE: "3f7a1fd1e93ec46a608e8cd164abb685365fd04d4575a7f8890f0832791415ca",
    "configs/rq2_public_solver_confirmatory_pilot_activation_v3.yaml": "da07e16c7bca60a44c97803bd60919a6f9f3a83042da58065af4c5a7836763e9",
    "configs/rq2_public_solver_confirmatory_pilot_implementation_review_escalation_v3.yaml": "4561e17bf16f89a33efbde0b5cc9eee706bf53c82712dee6258bae5e451796d9",
    "experiments/run_rq2_public_solver_confirmatory_pilot_v3.py": "7dd844ab96cb1db8c20a945d6ba60ec5133469a9e66b3d5d8200d792b9d1f7bf",
    "experiments/validate_rq2_public_solver_confirmatory_pilot_v3.py": "7cd52649133d97ab7e06c8f72d3fd3334227e2346b4bb633873a530c96909877",
    "tests/test_rq2_public_solver_confirmatory_pilot_v3.py": "46fc54b090f2cd7de36310421a7b7418df9fc6d58d6b8931815e76bb77b986c0",
    V3_BUNDLE_RELATIVE: "d393c33b037457250eb14e5263dabc6277d6c9b9bd6a9e3697bf2c38b321c8a5",
    V3_OUTER_RELATIVE: V3_OUTER_SHA256,
}
SEMANTIC_HASHES = {
    SEMANTIC_CONFIG_RELATIVE: "cb0209a9a53962be8ebb6ee185d3bfbf3d004d7cd761e164b286a58e0c7887b0",
    SEMANTIC_MANIFEST_RELATIVE: "c0b1a6a3074343ab5f281b268cd40898630ad1e2234830a4536189687832f471",
}


def _artifact_map(value: object, label: str) -> dict[str, str]:
    payload = _mapping(value, label)
    observed: dict[str, str] = {}
    for name, item in payload.items():
        artifact = _mapping(item, f"{label} {name}")
        if set(artifact) != {"path", "sha256"}:
            raise ValueError(f"{label} {name} schema drifted")
        observed[str(artifact["path"])] = str(artifact["sha256"])
    return observed


def _validate_pass_review(config: Mapping[str, Any]) -> None:
    receipt = _mapping(
        yaml.safe_load((ROOT / PASS_RECEIPT_RELATIVE).read_text(encoding="utf-8")),
        "v4 PASS receipt",
    )
    if (
        receipt.get("schema") != "rq2_public_solver_confirmatory_implementation_review_pass_v4"
        or receipt.get("reviewed_on") not in {"2026-08-28", "2026-08-29"}
        or receipt.get("review_scope") != "rq2_public_solver_confirmatory_pilot_v3_execution_successor"
        or receipt.get("reviewer_role") != "independent_sol_reviewer"
        or receipt.get("verdict") != "PASS"
        or _artifact_map(receipt.get("reviewed_v3_artifacts"), "reviewed v3 artifacts")
        != V3_HASHES
    ):
        raise ValueError("v4 PASS receipt identity or binding drifted")
    finding = _mapping(receipt.get("finding"), "PASS finding")
    if (
        finding.get("id") != "v3_durable_provenance_remediation_complete"
        or finding.get("severity") != "execution_successor_gate"
        or not isinstance(finding.get("observation"), str)
        or not isinstance(finding.get("required_remediation"), str)
    ):
        raise ValueError("v4 PASS finding drifted")
    if receipt.get("effect") != {
        "v3_bytes_immutable": True,
        "independent_v3_review_passed": True,
        "v4_execution_successor_authorized": True,
        "confirmatory_execution_authorized_only": True,
        "grid_pairwise_identification_formal_or_security_authorized": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }:
        raise ValueError("v4 PASS effect drifted")
    registered = _mapping(config.get("pass_review_receipt"), "registered PASS receipt")
    if registered != {
        "path": PASS_RECEIPT_RELATIVE,
        "sha256": _sha256(ROOT / PASS_RECEIPT_RELATIVE),
        "verdict": "PASS",
        "reviewer_role": "independent_sol_reviewer",
        "reviewed_on": "2026-08-28",
    }:
        raise ValueError("registered v4 PASS receipt drifted")


def _validate_activation(config: Mapping[str, Any]) -> None:
    activation = _mapping(
        yaml.safe_load((ROOT / ACTIVATION_RELATIVE).read_text(encoding="utf-8")),
        "v4 activation",
    )
    if (
        activation.get("schema") != "rq2_public_solver_confirmatory_pilot_activation_v4"
        or activation.get("authorized_on") != "2026-08-28"
        or activation.get("status") != "reviewed_successor_confirmatory_execution_ready"
    ):
        raise ValueError("v4 activation identity drifted")
    if activation.get("user_authority") != {
        "explicit_authorization_observed": True,
        "authorization_record": "继续做/按路径全部做完",
        "authorized_scope": "prepare_and_execute_fresh_v4_confirmatory_pilot_only",
        "external_watchdog_seconds": 21600,
    }:
        raise ValueError("v4 user authority drifted")
    if activation.get("independent_review_authority") != {
        "receipt_path": PASS_RECEIPT_RELATIVE,
        "receipt_sha256": _sha256(ROOT / PASS_RECEIPT_RELATIVE),
        "verdict": "PASS",
        "reviewer_role": "independent_sol_reviewer",
    }:
        raise ValueError("v4 independent review authority drifted")
    if activation.get("permissions") != {
        "prepare_v4_execution_successor": True,
        "independently_review_v3_artifacts": True,
        "execute_confirmatory_pilot": True,
        "execute_formal_grid": False,
        "execute_pairwise": False,
        "execute_identification": False,
        "make_formal_result_claim": False,
        "make_security_claim": False,
    }:
        raise ValueError("v4 activation permissions drifted")
    if activation.get("gates") != {
        "independent_v4_implementation_review_passed": True,
        "v4_execution_successor_present": True,
        "confirmatory_execution_ready": True,
        "confirmatory_pilot_executed": False,
        "cross_solver_confirmation_completed": False,
        "formal_execution_ready": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }:
        raise ValueError("v4 activation gates drifted")
    if config.get("activation") != {
        "path": ACTIVATION_RELATIVE,
        "authorization_scope": "prepare_and_execute_fresh_v4_confirmatory_pilot_only",
    }:
        raise ValueError("registered v4 activation drifted")


def _validate_config(config: Mapping[str, Any]) -> dict[str, Any]:
    if (
        config.get("schema") != "rq2_public_solver_confirmatory_pilot_config_v4"
        or config.get("version") != 4
        or config.get("frozen_on") != "2026-08-28"
        or config.get("status") != "reviewed_successor_candidate_confirmatory_execution_ready"
    ):
        raise ValueError("v4 config identity drifted")
    expected_scope = {
        "task_risk": "R3_R4_gate_boundary",
        "evidence_level": "nonformal_cross_solver_confirmatory_pilot",
        "fresh_solver_execution_required": True,
        "source_outcomes_observed": True,
        "confirmatory_outcomes_observed": False,
        "changes_model_formulation": False,
        "changes_solver_algorithm_threads_seed_or_tolerances": False,
        "changes_pilot_blocks_or_repetitions": False,
        "changes_only_durable_provenance_validation": True,
        "formal_grid_execution": False,
        "formal_pairwise_execution": False,
        "formal_identification_execution": False,
        "formal_claim_authorized": False,
        "security_claim_authorized": False,
    }
    if config.get("scope") != expected_scope:
        raise ValueError("v4 scope drifted")
    predecessor = _mapping(config.get("v3_predecessor_authority"), "v3 predecessor authority")
    if predecessor.get("immutable") is not True or _artifact_map(
        {key: value for key, value in predecessor.items() if key != "immutable"},
        "v3 predecessor",
    ) != V3_HASHES:
        raise ValueError("v3 predecessor binding drifted")
    semantic = _mapping(config.get("semantic_authority"), "semantic authority")
    if semantic != {
        "config_path": SEMANTIC_CONFIG_RELATIVE,
        "config_sha256": SEMANTIC_HASHES[SEMANTIC_CONFIG_RELATIVE],
        "manifest_path": SEMANTIC_MANIFEST_RELATIVE,
        "manifest_sha256": SEMANTIC_HASHES[SEMANTIC_MANIFEST_RELATIVE],
        "review_verdict": "PASS",
        "evaluator_function": "evaluate_runs",
    }:
        raise ValueError("v4 semantic authority drifted")
    inheritance = _mapping(config.get("scientific_inheritance"), "inheritance")
    if inheritance != {
        "source": "v3_predecessor_config_via_v2_scientific_parent",
        "exact_fields": ["input", "model", "pilot_blocks", "solvers", "execution", "acceptance"],
        "execution_order": EXPECTED_RUNS,
        "repetitions": 2,
        "external_watchdog_seconds": 21600,
        "solver_time_limit_seconds": None,
        "solver_threads": 4,
        "solver_random_seed": 0,
        "timeout_is_infeasibility_evidence": False,
        "unresolved_is_infeasibility_evidence": False,
        "scientific_threshold_values_changed": False,
    }:
        raise ValueError("v4 scientific inheritance declaration drifted")
    v3 = _mapping(yaml.safe_load((ROOT / V3_CONFIG_RELATIVE).read_text(encoding="utf-8")), "v3 config")
    scientific_parent = _load_scientific_parent(config)
    execution = _mapping(scientific_parent.get("execution"), "scientific execution")
    if (
        execution.get("execution_order") != EXPECTED_RUNS
        or execution.get("repetitions") != 2
        or execution.get("external_watchdog_seconds") != 21600
        or execution.get("timeout_is_infeasibility_evidence") is not False
        or execution.get("unresolved_is_infeasibility_evidence") is not False
        or any(
            solver.get("threads") != 4
            or solver.get("random_seed") != 0
            or solver.get("time_limit_seconds") is not None
            for solver in _mapping(scientific_parent.get("solvers"), "scientific solvers").values()
        )
        or _mapping(scientific_parent.get("acceptance"), "scientific acceptance").get("scientific_threshold_values_changed") is not False
    ):
        raise ValueError("inherited v3 science contract drifted")
    implementation = _mapping(config.get("implementation"), "implementation")
    if (
        implementation.get("runner_path") != RUNNER_RELATIVE
        or implementation.get("runner_hash_authority") != BUNDLE_RELATIVE
        or implementation.get("controller_calls_solver") is not False
        or implementation.get("expected_worker_report_constructor") != "build_expected_worker_report"
        or implementation.get("nested_worker_report_is_authority") is not False
        or implementation.get("nested_worker_report_requires_exact_reconstructed_equality") is not True
        or implementation.get("nested_worker_report_sha_uses_reconstructed_expected_report") is not True
        or implementation.get("result_reconstructed_from_durable_payloads") is not True
        or implementation.get("process_evidence_scope") != PROCESS_EVIDENCE_SCOPE
        or implementation.get("expected_report_inputs_live") != ["registered_run_identity", "payload", "controller_receipt", "payload_sha256", "popen_pid", "popen_returncode"]
        or implementation.get("expected_report_inputs_post_result") != ["registered_run_identity", "payload", "controller_receipt", "payload_sha256", "registered_zero_exit_contract"]
    ):
        raise ValueError("v4 implementation contract drifted")
    provenance = _mapping(config.get("provenance"), "provenance")
    if provenance != {
        "controller_receipt": "controller_receipt.json",
        "worker_root": "workers",
        "worker_files_per_run": ["payload.json", "receipt.json"],
        "exact_tree_required": True,
        "bind_controller_nonce_pid_and_start_identity": True,
        "bind_v3_outer_config_runner_semantic_authority_hashes": True,
        "bind_worker_pid_ppid_exit_code_payload_hash_and_execution_index": True,
        "controller_receipts_form_ordered_hash_chain": True,
        "controller_receipt_issue_times_strictly_increase": True,
        "unique_worker_pid_per_run": True,
        "worker_parent_pid_must_equal_controller_pid": True,
        "reconstruct_runs_from_payloads": True,
        "evidence_limit": PROCESS_EVIDENCE_SCOPE,
    }:
        raise ValueError("v4 provenance contract drifted")
    if config.get("output") != {
        "schema": RESULT_SCHEMA,
        "directory": RESULT_RELATIVE,
        "directory_must_not_preexist": True,
        "publication": "same_parent_staging_then_atomic_rename",
        "top_level_inventory": ["config.yaml", "controller_receipt.json", "runs.json", "semantic_validation.json", "summary.json", "workers", "SHA256SUMS.json"],
        "worker_directory_inventory": ["payload.json", "receipt.json"],
        "exact_recursive_manifest_required": True,
        "v1_or_v2_or_v3_run_reuse_allowed": False,
    }:
        raise ValueError("v4 output contract drifted")
    successor = _mapping(config.get("execution_successor_contract"), "execution successor contract")
    if successor != {
        "current_v4_is_execution_successor": True,
        "opens_only_confirmatory_execution_gate": True,
        "no_future_successor_required_for_validation": True,
        "grid_pairwise_identification_formal_or_security_authority": False,
        "modifying_v3_or_predecessor_bytes_forbidden": True,
    }:
        raise ValueError("v4 execution successor contract drifted")
    if config.get("gates") != {
        "semantic_successor_review_passed": True,
        "user_confirmatory_authorization_recorded": True,
        "v3_remediation_candidate_ready": True,
        "independent_v3_implementation_review_passed": True,
        "v4_execution_successor_present": True,
        "independent_v4_implementation_review_passed": True,
        "confirmatory_execution_ready": True,
        "confirmatory_pilot_executed": False,
        "cross_solver_confirmation_completed": False,
        "formal_execution_ready": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }:
        raise ValueError("v4 gates drifted")
    for relative, expected in {**V3_HASHES, **SEMANTIC_HASHES}.items():
        _ordinary(relative, expected, "v4 predecessor authority")
    v3_outer = _mapping(_load_json_strict(ROOT / V3_OUTER_RELATIVE, "v3 outer"), "v3 outer")
    if v3_outer != {
        "schema": "rq2_public_solver_confirmatory_outer_manifest_v3",
        "files": {V3_BUNDLE_RELATIVE: V3_HASHES[V3_BUNDLE_RELATIVE]},
    }:
        raise ValueError("v3 outer chain drifted")
    return v3


def _validate_bundle() -> tuple[dict[str, str], str]:
    bundle = _mapping(_load_json_strict(BUNDLE, "v4 bundle"), "v4 bundle")
    if bundle.get("schema") != "rq2_public_solver_confirmatory_bundle_manifest_v4":
        raise ValueError("v4 bundle schema drifted")
    files = _mapping(bundle.get("files"), "v4 bundle files")
    if set(files) != BUNDLE_INVENTORY:
        raise ValueError("v4 bundle inventory drifted")
    for relative, expected in files.items():
        _ordinary(relative, expected, "v4 bundle member")
    bundle_sha = _sha256(BUNDLE)
    outer = _mapping(_load_json_strict(OUTER, "v4 outer"), "v4 outer")
    if outer != {"schema": "rq2_public_solver_confirmatory_outer_manifest_v4", "files": {BUNDLE_RELATIVE: bundle_sha}}:
        raise ValueError("v4 outer manifest drifted")
    return files, bundle_sha


def _expected_result_members() -> set[str]:
    members = {"config.yaml", "controller_receipt.json", "runs.json", "semantic_validation.json", "summary.json"}
    for run_id in EXPECTED_RUNS:
        members.add(f"workers/{run_id}/payload.json")
        members.add(f"workers/{run_id}/receipt.json")
    return members


def _validate_result(config: Mapping[str, Any], result: Path = RESULT) -> dict[str, object]:
    if not result.exists():
        return {"result_present": False, "result_manifest_sha256": None, "confirmatory_pilot_executed": False, "cross_solver_confirmation_completed": False}
    if not result.is_dir() or result.is_symlink():
        raise ValueError("v4 result path is not an ordinary directory")
    expected_top = {"config.yaml", "controller_receipt.json", "runs.json", "semantic_validation.json", "summary.json", "workers", "SHA256SUMS.json"}
    children = list(result.iterdir())
    if {item.name for item in children} != expected_top or len(children) != 7 or any(item.is_symlink() for item in children):
        raise ValueError("v4 result top-level inventory drifted")
    manifest_path = result / "SHA256SUMS.json"
    manifest = _mapping(_load_json_strict(manifest_path, "v4 result manifest"), "result manifest")
    if set(manifest) != _expected_result_members():
        raise ValueError("v4 result recursive manifest inventory drifted")
    observed_files = {path.relative_to(result).as_posix() for path in result.rglob("*") if path.is_file() and path != manifest_path}
    if observed_files != set(manifest):
        raise ValueError("v4 result exact file tree drifted")
    for relative, expected in manifest.items():
        path = result / relative
        if not path.is_file() or path.is_symlink() or _sha256(path) != expected:
            raise ValueError(f"v4 result member drifted: {relative}")
    if _sha256(result / "config.yaml") != _sha256(CONFIG):
        raise ValueError("published v4 config drifted")
    runs, worker_pids, controller = _reconstruct_runs(result, config, load_json=_load_json_strict)
    published_runs = _list(_load_json_strict(result / "runs.json", "runs"), "runs")
    if published_runs != runs:
        raise ValueError("runs.json is not an exact reconstruction of worker payloads")
    semantic_config = _mapping(yaml.safe_load(SEMANTIC_CONFIG.read_text(encoding="utf-8")), "semantic config")
    evaluator_report = _assert_evaluator_report(evaluate_runs(semantic_config, runs))
    semantic = _mapping(_load_json_strict(result / "semantic_validation.json", "semantic"), "semantic")
    expected_semantic = {
        "schema": SEMANTIC_VALIDATION_SCHEMA,
        "semantic_successor_config_sha256": _sha256(SEMANTIC_CONFIG),
        "semantic_authority_sha256": config["semantic_authority"]["manifest_sha256"],
        "v3_outer_sha256": V3_OUTER_SHA256,
        "evaluator_report": evaluator_report,
        "fresh_execution_run_ids": EXPECTED_RUNS,
        "fresh_worker_pids": worker_pids,
        "controller_identity_sha256": controller["controller_identity_sha256"],
        "controller_receipt_sha256": controller["receipt_sha256"],
        "durable_process_provenance_verified": True,
        "nested_worker_reports_reconstructed_independently": True,
        "runs_reconstructed_exactly_from_worker_payloads": True,
        "process_evidence_scope": PROCESS_EVIDENCE_SCOPE,
        "semantic_contract_passed": True,
        "cross_solver_confirmation_completed": True,
        "formal_grid_execution_started": False,
        "security_certified": False,
    }
    if semantic != expected_semantic:
        raise ValueError("v4 semantic validation wrapper drifted")
    summary = _mapping(_load_json_strict(result / "summary.json", "summary"), "summary")
    expected_summary = {
        "schema": RESULT_SCHEMA,
        "config_sha256": _sha256(CONFIG),
        "runner_sha256": _sha256(ROOT / RUNNER_RELATIVE),
        "semantic_authority_sha256": config["semantic_authority"]["manifest_sha256"],
        "v3_outer_sha256": V3_OUTER_SHA256,
        "fresh_execution_status": "passed",
        "fresh_execution_passed": True,
        "fresh_execution_failed": False,
        "run_count": 4,
        "unique_worker_process_count": 4,
        "durable_process_provenance_verified": True,
        "nested_worker_reports_reconstructed_independently": True,
        "runs_reconstructed_exactly_from_worker_payloads": True,
        "semantic_contract_passed": True,
        "cross_solver_confirmation_completed": True,
        "formal_grid_execution_started": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    if summary != expected_summary:
        raise ValueError("v4 summary drifted")
    return {"result_present": True, "result_manifest_sha256": _sha256(manifest_path), "confirmatory_pilot_executed": True, "cross_solver_confirmation_completed": True}


def validate(config_path: Path = CONFIG, bundle_path: Path = BUNDLE, outer_path: Path = OUTER) -> dict[str, object]:
    if config_path.resolve() != CONFIG.resolve() or bundle_path.resolve() != BUNDLE.resolve() or outer_path.resolve() != OUTER.resolve():
        raise ValueError("only canonical v4 artifacts are accepted")
    files, bundle_sha = _validate_bundle()
    if files.get(CONFIG_RELATIVE) != _sha256(CONFIG):
        raise ValueError("canonical v4 config hash drifted")
    config = _mapping(yaml.safe_load(CONFIG.read_text(encoding="utf-8")), "v4 config")
    _validate_config(config)
    _validate_pass_review(config)
    _validate_activation(config)
    v3_report = validate_v3()
    result = _validate_result(config)
    return {
        "schema": "rq2_public_solver_confirmatory_preexecution_validation_v4",
        "config_sha256": _sha256(CONFIG),
        "bundle_manifest_sha256": bundle_sha,
        "outer_manifest_sha256": _sha256(OUTER),
        "bundle_member_count": len(files),
        "v3_outer_sha256": V3_OUTER_SHA256,
        "v3_predecessor_validation_passed": v3_report["validation_passed"],
        "pass_review_verdict": "PASS",
        "v3_remediation_candidate_ready": True,
        "independent_v3_implementation_review_passed": True,
        "v4_execution_successor_present": True,
        "independent_v4_implementation_review_passed": True,
        "implementation_ready": True,
        "execution_ready": True,
        "solver_calls": 0,
        "result_files_written": 0,
        **result,
        "formal_execution_ready": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
        "validation_passed": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--bundle", type=Path, default=BUNDLE)
    parser.add_argument("--outer", type=Path, default=OUTER)
    args = parser.parse_args()
    print(json.dumps(validate(args.config, args.bundle, args.outer), indent=2))


if __name__ == "__main__":
    main()
