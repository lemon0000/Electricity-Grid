"""Fail-closed validator for the RQ2 confirmatory pilot v3 remediation."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from experiments.run_rq2_public_solver_confirmatory_pilot_v3 import (
    EXPECTED_RUNS,
    PROCESS_EVIDENCE_SCOPE,
    SEMANTIC_VALIDATION_SCHEMA,
    V2_OUTER_SHA256,
    _assert_evaluator_report,
    _reconstruct_runs,
)
from experiments.validate_rq2_public_solver_confirmatory_pilot_v2 import (
    _list,
    _load_json_strict,
    _mapping,
    _ordinary,
    _sha256,
)
from experiments.validate_rq2_public_solver_confirmatory_pilot_v2 import (
    validate as validate_v2,
)
from experiments.validate_rq2_public_solver_pilot_semantic_successor_v1 import (
    evaluate_runs,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = "configs/rq2_public_solver_confirmatory_pilot_v3.yaml"
BUNDLE_RELATIVE = (
    "configs/rq2_public_solver_confirmatory_pilot_bundle_v3.SHA256SUMS.json"
)
OUTER_RELATIVE = (
    "configs/rq2_public_solver_confirmatory_pilot_bundle_v3.OUTER.SHA256SUMS.json"
)
ESCALATION_RELATIVE = (
    "configs/rq2_public_solver_confirmatory_pilot_"
    "implementation_review_escalation_v3.yaml"
)
ACTIVATION_RELATIVE = (
    "configs/rq2_public_solver_confirmatory_pilot_activation_v3.yaml"
)
RUNNER_RELATIVE = "experiments/run_rq2_public_solver_confirmatory_pilot_v3.py"
VALIDATOR_RELATIVE = "experiments/validate_rq2_public_solver_confirmatory_pilot_v3.py"
TESTS_RELATIVE = "tests/test_rq2_public_solver_confirmatory_pilot_v3.py"
RESULT_RELATIVE = "results/tables/rq2_public_solver_confirmatory_pilot_v3"
V2_CONFIG_RELATIVE = "configs/rq2_public_solver_confirmatory_pilot_v2.yaml"
V2_BUNDLE_RELATIVE = (
    "configs/rq2_public_solver_confirmatory_pilot_bundle_v2.SHA256SUMS.json"
)
V2_OUTER_RELATIVE = (
    "configs/rq2_public_solver_confirmatory_pilot_bundle_v2.OUTER.SHA256SUMS.json"
)
SEMANTIC_CONFIG_RELATIVE = (
    "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml"
)
SEMANTIC_MANIFEST_RELATIVE = (
    "configs/rq2_public_solver_pilot_semantic_successor_v1.SHA256SUMS.json"
)
CONFIG = ROOT / CONFIG_RELATIVE
BUNDLE = ROOT / BUNDLE_RELATIVE
OUTER = ROOT / OUTER_RELATIVE
RESULT = ROOT / RESULT_RELATIVE
SEMANTIC_CONFIG = ROOT / SEMANTIC_CONFIG_RELATIVE
BUNDLE_INVENTORY = {
    CONFIG_RELATIVE,
    ESCALATION_RELATIVE,
    ACTIVATION_RELATIVE,
    RUNNER_RELATIVE,
    VALIDATOR_RELATIVE,
    TESTS_RELATIVE,
}
V2_HASHES = {
    V2_CONFIG_RELATIVE: (
        "d0a5c3a898d89ce869a6647b4d8f271f82921c89069cdd9dd98b4f54e7c9f1e0"
    ),
    "configs/rq2_public_solver_confirmatory_pilot_activation_v2.yaml": (
        "fd4e584b86de791f014e417499fa14c7db7de07f4e6e63adb8270b879c39a45b"
    ),
    "configs/rq2_public_solver_confirmatory_pilot_implementation_review_v2.yaml": (
        "4e06fefc95addda419d8e721e2be6963a685ee3c6e136acf36efc3c2d1cc5c13"
    ),
    "experiments/run_rq2_public_solver_confirmatory_pilot_v2.py": (
        "59a54f9fb1c987baffe0a12a11d9584081da7bd8db60800b4fe0fc0da6a43eaa"
    ),
    "experiments/validate_rq2_public_solver_confirmatory_pilot_v2.py": (
        "605936ccca949d9f022b7b29c9b96738a43f72a6b2072a4bfecf277b31412e4f"
    ),
    "tests/test_rq2_public_solver_confirmatory_pilot_v2.py": (
        "9b19e3f4be515d9a6c20380326efd21761f9268d735089567c72f3de34c4e1d7"
    ),
    V2_BUNDLE_RELATIVE: (
        "b356dfa1d58eeb416cbe81d6d840142d4e676b296d39a7372825f7f1d5cc6687"
    ),
    V2_OUTER_RELATIVE: V2_OUTER_SHA256,
}
SEMANTIC_HASHES = {
    SEMANTIC_CONFIG_RELATIVE: (
        "cb0209a9a53962be8ebb6ee185d3bfbf3d004d7cd761e164b286a58e0c7887b0"
    ),
    SEMANTIC_MANIFEST_RELATIVE: (
        "c0b1a6a3074343ab5f281b268cd40898630ad1e2234830a4536189687832f471"
    ),
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


def _validate_escalation(config: Mapping[str, Any]) -> None:
    escalation = _mapping(
        yaml.safe_load((ROOT / ESCALATION_RELATIVE).read_text(encoding="utf-8")),
        "v3 ESCALATE receipt",
    )
    if (
        escalation.get("schema")
        != "rq2_public_solver_confirmatory_implementation_review_escalation_v3"
        or escalation.get("reviewed_on") != "2026-08-28"
        or escalation.get("review_scope")
        != "rq2_public_solver_confirmatory_pilot_v2_durable_provenance"
        or escalation.get("reviewer_role") != "independent_sol_reviewer"
        or escalation.get("verdict") != "ESCALATE"
        or _artifact_map(
            escalation.get("reviewed_v2_artifacts"), "reviewed v2 artifacts"
        )
        != V2_HASHES
    ):
        raise ValueError("v3 ESCALATE receipt identity or binding drifted")
    finding = _mapping(escalation.get("finding"), "ESCALATE finding")
    if (
        finding.get("id") != "nested_worker_report_self_authority"
        or finding.get("severity") != "durable_provenance_gate_second_failure"
        or not isinstance(finding.get("observation"), str)
        or not isinstance(finding.get("required_remediation"), str)
    ):
        raise ValueError("v3 ESCALATE finding drifted")
    if escalation.get("effect") != {
        "v1_v2_and_semantic_predecessors_immutable": True,
        "v3_remediation_successor_authorized": True,
        "v3_independent_review_required": True,
        "independent_v3_implementation_review_passed": False,
        "confirmatory_execution_authorized": False,
        "cross_solver_confirmation_completed": False,
        "formal_execution_ready": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }:
        raise ValueError("v3 ESCALATE effect drifted")
    registered = _mapping(
        config.get("escalation_review_receipt"), "registered ESCALATE receipt"
    )
    if registered != {
        "path": ESCALATION_RELATIVE,
        "sha256": _sha256(ROOT / ESCALATION_RELATIVE),
        "verdict": "ESCALATE",
    }:
        raise ValueError("registered v3 ESCALATE receipt drifted")


def _validate_activation(config: Mapping[str, Any]) -> None:
    activation = _mapping(
        yaml.safe_load((ROOT / ACTIVATION_RELATIVE).read_text(encoding="utf-8")),
        "v3 activation",
    )
    if (
        activation.get("schema")
        != "rq2_public_solver_confirmatory_pilot_activation_v3"
        or activation.get("authorized_on") != "2026-08-28"
        or activation.get("status")
        != "escalation_remediation_candidate_only_independent_review_pending"
    ):
        raise ValueError("v3 activation identity drifted")
    if activation.get("user_authority") != {
        "explicit_authorization_observed": True,
        "authorization_record": "继续做/按路径全部做完",
        "authorized_scope": (
            "prepare_and_independently_review_v3_confirmatory_remediation"
        ),
        "external_watchdog_seconds": 21600,
    }:
        raise ValueError("v3 user authority drifted")
    if activation.get("escalation_authority") != {
        "receipt_path": ESCALATION_RELATIVE,
        "receipt_sha256": _sha256(ROOT / ESCALATION_RELATIVE),
        "verdict": "ESCALATE",
    }:
        raise ValueError("v3 escalation authority drifted")
    if activation.get("permissions") != {
        "prepare_versioned_v3_remediation_candidate": True,
        "independently_review_v3_candidate": True,
        "execute_v3_candidate": False,
        "add_complete_v4_execution_successor_after_exact_independent_pass": True,
        "execute_confirmatory_pilot_before_v4_gate": False,
        "execute_formal_grid": False,
        "execute_pairwise": False,
        "execute_identification": False,
        "make_formal_result_claim": False,
        "make_security_claim": False,
    }:
        raise ValueError("v3 activation permissions drifted")
    if activation.get("gates") != {
        "v3_remediation_candidate_ready": True,
        "independent_v3_implementation_review_passed": False,
        "v4_execution_successor_present": False,
        "confirmatory_execution_ready": False,
        "confirmatory_pilot_executed": False,
        "cross_solver_confirmation_completed": False,
        "formal_execution_ready": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }:
        raise ValueError("v3 activation gates drifted")
    if config.get("activation") != {
        "path": ACTIVATION_RELATIVE,
        "sha256": _sha256(ROOT / ACTIVATION_RELATIVE),
        "authorization_scope": (
            "prepare_and_independently_review_v3_confirmatory_remediation"
        ),
    }:
        raise ValueError("registered v3 activation drifted")


def _validate_config(config: Mapping[str, Any]) -> dict[str, Any]:
    if (
        config.get("schema") != "rq2_public_solver_confirmatory_pilot_config_v3"
        or config.get("version") != 3
        or config.get("frozen_on") != "2026-08-28"
        or config.get("status")
        != "escalation_remediation_candidate_independent_review_pending"
    ):
        raise ValueError("v3 config identity drifted")
    if config.get("scope") != {
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
    }:
        raise ValueError("v3 scope drifted")
    predecessor = _mapping(
        config.get("v2_predecessor_authority"), "v2 predecessor authority"
    )
    if predecessor.get("immutable") is not True:
        raise ValueError("v2 predecessor immutability drifted")
    observed_v2 = _artifact_map(
        {key: value for key, value in predecessor.items() if key != "immutable"},
        "v2 predecessor",
    )
    if observed_v2 != V2_HASHES:
        raise ValueError("v2 predecessor binding drifted")
    semantic = _mapping(config.get("semantic_authority"), "semantic authority")
    if semantic != {
        "config_path": SEMANTIC_CONFIG_RELATIVE,
        "config_sha256": SEMANTIC_HASHES[SEMANTIC_CONFIG_RELATIVE],
        "manifest_path": SEMANTIC_MANIFEST_RELATIVE,
        "manifest_sha256": SEMANTIC_HASHES[SEMANTIC_MANIFEST_RELATIVE],
        "review_verdict": "PASS",
        "evaluator_function": "evaluate_runs",
    }:
        raise ValueError("v3 semantic authority drifted")
    scientific = _mapping(config.get("scientific_inheritance"), "inheritance")
    if scientific != {
        "source": "v2_predecessor_config",
        "exact_fields": [
            "input",
            "model",
            "pilot_blocks",
            "solvers",
            "execution",
            "acceptance",
        ],
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
        raise ValueError("v3 scientific inheritance declaration drifted")
    v2 = _mapping(
        yaml.safe_load((ROOT / V2_CONFIG_RELATIVE).read_text(encoding="utf-8")),
        "v2 config",
    )
    execution = _mapping(v2.get("execution"), "v2 execution")
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
            for solver in v2["solvers"].values()
        )
        or v2["acceptance"].get("scientific_threshold_values_changed") is not False
    ):
        raise ValueError("inherited v2 science contract drifted")
    implementation = _mapping(config.get("implementation"), "implementation")
    if (
        implementation.get("runner_path") != RUNNER_RELATIVE
        or implementation.get("runner_hash_authority") != BUNDLE_RELATIVE
        or implementation.get("controller_calls_solver") is not False
        or implementation.get("expected_worker_report_constructor")
        != "build_expected_worker_report"
        or implementation.get("nested_worker_report_is_authority") is not False
        or implementation.get(
            "nested_worker_report_requires_exact_reconstructed_equality"
        )
        is not True
        or implementation.get(
            "nested_worker_report_sha_uses_reconstructed_expected_report"
        )
        is not True
        or implementation.get("result_reconstructed_from_durable_payloads")
        is not True
        or implementation.get("process_evidence_scope")
        != PROCESS_EVIDENCE_SCOPE
        or implementation.get("expected_report_inputs_live")
        != [
            "registered_run_identity",
            "payload",
            "controller_receipt",
            "payload_sha256",
            "popen_pid",
            "popen_returncode",
        ]
        or implementation.get("expected_report_inputs_post_result")
        != [
            "registered_run_identity",
            "payload",
            "controller_receipt",
            "payload_sha256",
            "registered_zero_exit_contract",
        ]
    ):
        raise ValueError("v3 implementation contract drifted")
    provenance = _mapping(config.get("provenance"), "provenance")
    if provenance != {
        "controller_receipt": "controller_receipt.json",
        "worker_root": "workers",
        "worker_files_per_run": ["payload.json", "receipt.json"],
        "exact_tree_required": True,
        "bind_controller_nonce_pid_and_start_identity": True,
        "bind_v2_outer_config_runner_semantic_authority_hashes": True,
        "bind_worker_pid_ppid_exit_code_payload_hash_and_execution_index": True,
        "controller_receipts_form_ordered_hash_chain": True,
        "controller_receipt_issue_times_strictly_increase": True,
        "unique_worker_pid_per_run": True,
        "worker_parent_pid_must_equal_controller_pid": True,
        "reconstruct_runs_from_payloads": True,
        "evidence_limit": PROCESS_EVIDENCE_SCOPE,
    }:
        raise ValueError("v3 provenance contract drifted")
    if config.get("output") != {
        "schema": "rq2_public_solver_confirmatory_pilot_v3",
        "directory": RESULT_RELATIVE,
        "directory_must_not_preexist": True,
        "publication": "same_parent_staging_then_atomic_rename",
        "top_level_inventory": [
            "config.yaml",
            "controller_receipt.json",
            "runs.json",
            "semantic_validation.json",
            "summary.json",
            "workers",
            "SHA256SUMS.json",
        ],
        "worker_directory_inventory": ["payload.json", "receipt.json"],
        "exact_recursive_manifest_required": True,
        "v1_or_v2_run_reuse_allowed": False,
    }:
        raise ValueError("v3 output contract drifted")
    successor = _mapping(
        config.get("gate_opening_successor_contract"), "v4 successor contract"
    )
    v4_paths = {
        "pass_receipt": (
            "configs/rq2_public_solver_confirmatory_pilot_"
            "implementation_review_pass_v4.yaml"
        ),
        "activation": (
            "configs/rq2_public_solver_confirmatory_pilot_activation_v4.yaml"
        ),
        "config": "configs/rq2_public_solver_confirmatory_pilot_v4.yaml",
        "runner": "experiments/run_rq2_public_solver_confirmatory_pilot_v4.py",
        "validator": (
            "experiments/validate_rq2_public_solver_confirmatory_pilot_v4.py"
        ),
        "tests": "tests/test_rq2_public_solver_confirmatory_pilot_v4.py",
        "bundle": (
            "configs/rq2_public_solver_confirmatory_pilot_bundle_v4.SHA256SUMS.json"
        ),
        "outer": (
            "configs/rq2_public_solver_confirmatory_pilot_"
            "bundle_v4.OUTER.SHA256SUMS.json"
        ),
    }
    if (
        successor.get("current_v3_bytes_become_immutable_after_sealing") is not True
        or successor.get("current_v3_execution_gate_remains_closed") is not True
        or successor.get("future_successor_version") != 4
        or successor.get("future_files_are_not_current_manifest_members") is not True
        or successor.get("v4_required_new_artifacts")
        != [
            "pass_receipt",
            "activation",
            "config",
            "runner",
            "validator",
            "tests",
            "bundle",
            "outer",
        ]
        or successor.get("v4_required_new_artifact_paths") != v4_paths
        or set(v4_paths.values()) & BUNDLE_INVENTORY
        or successor.get("v4_must_bind_exact_v3_outer_sha256") is not True
        or successor.get("v4_must_bind_exact_pass_receipt_sha256") is not True
        or successor.get("v4_may_authorize_only_fresh_confirmatory_pilot") is not True
        or successor.get("v4_output_directory")
        != "results/tables/rq2_public_solver_confirmatory_pilot_v4"
        or successor.get("modifying_v3_or_predecessor_bytes_forbidden") is not True
        or successor.get(
            "grid_pairwise_identification_formal_or_security_authority"
        )
        is not False
    ):
        raise ValueError("v4 successor contract drifted")
    if successor.get("independent_pass_receipt") != {
        "required_verdict": "PASS",
        "reviewer_role": "independent_sol_reviewer",
        "must_bind_exact_v3_hashes": [
            "config",
            "activation",
            "escalation_receipt",
            "runner",
            "validator",
            "tests",
            "bundle",
            "outer",
        ],
        "receipt_must_be_new_after_v3_outer_is_sealed": True,
    }:
        raise ValueError("future v3 PASS receipt contract drifted")
    if config.get("gates") != {
        "semantic_successor_review_passed": True,
        "user_confirmatory_authorization_recorded": True,
        "v3_remediation_candidate_ready": True,
        "independent_v3_implementation_review_passed": False,
        "v4_execution_successor_present": False,
        "confirmatory_execution_ready": False,
        "confirmatory_pilot_executed": False,
        "cross_solver_confirmation_completed": False,
        "formal_execution_ready": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }:
        raise ValueError("v3 gates drifted")
    for relative, expected in {**V2_HASHES, **SEMANTIC_HASHES}.items():
        _ordinary(relative, expected, "v3 predecessor authority")
    v2_outer = _mapping(
        _load_json_strict(ROOT / V2_OUTER_RELATIVE, "v2 outer"), "v2 outer"
    )
    if v2_outer != {
        "schema": "rq2_public_solver_confirmatory_outer_manifest_v2",
        "files": {V2_BUNDLE_RELATIVE: V2_HASHES[V2_BUNDLE_RELATIVE]},
    }:
        raise ValueError("v2 outer chain drifted")
    return v2


def _validate_bundle() -> tuple[dict[str, str], str]:
    bundle = _mapping(_load_json_strict(BUNDLE, "v3 bundle"), "v3 bundle")
    if bundle.get("schema") != "rq2_public_solver_confirmatory_bundle_manifest_v3":
        raise ValueError("v3 bundle schema drifted")
    files = _mapping(bundle.get("files"), "v3 bundle files")
    if set(files) != BUNDLE_INVENTORY:
        raise ValueError("v3 bundle inventory drifted")
    for relative, expected in files.items():
        _ordinary(relative, expected, "v3 bundle member")
    bundle_sha = _sha256(BUNDLE)
    outer = _mapping(_load_json_strict(OUTER, "v3 outer"), "v3 outer")
    if outer != {
        "schema": "rq2_public_solver_confirmatory_outer_manifest_v3",
        "files": {BUNDLE_RELATIVE: bundle_sha},
    }:
        raise ValueError("v3 outer manifest drifted")
    return files, bundle_sha


def _expected_result_members() -> set[str]:
    members = {
        "config.yaml",
        "controller_receipt.json",
        "runs.json",
        "semantic_validation.json",
        "summary.json",
    }
    for run_id in EXPECTED_RUNS:
        members.add(f"workers/{run_id}/payload.json")
        members.add(f"workers/{run_id}/receipt.json")
    return members


def _validate_result(config: Mapping[str, Any], result: Path = RESULT) -> dict[str, object]:
    if not result.exists():
        return {
            "result_present": False,
            "result_manifest_sha256": None,
            "confirmatory_pilot_executed": False,
            "cross_solver_confirmation_completed": False,
        }
    if not result.is_dir() or result.is_symlink():
        raise ValueError("v3 result path is not an ordinary directory")
    expected_top = {
        "config.yaml",
        "controller_receipt.json",
        "runs.json",
        "semantic_validation.json",
        "summary.json",
        "workers",
        "SHA256SUMS.json",
    }
    children = list(result.iterdir())
    if {item.name for item in children} != expected_top or len(children) != 7:
        raise ValueError("v3 result top-level inventory drifted")
    if any(item.is_symlink() for item in children):
        raise ValueError("v3 result top-level symlink is forbidden")
    manifest_path = result / "SHA256SUMS.json"
    manifest = _mapping(
        _load_json_strict(manifest_path, "v3 result manifest"), "result manifest"
    )
    if set(manifest) != _expected_result_members():
        raise ValueError("v3 result recursive manifest inventory drifted")
    observed_files = {
        path.relative_to(result).as_posix()
        for path in result.rglob("*")
        if path.is_file() and path != manifest_path
    }
    if observed_files != set(manifest):
        raise ValueError("v3 result exact file tree drifted")
    for relative, expected in manifest.items():
        path = result / relative
        if not path.is_file() or path.is_symlink() or _sha256(path) != expected:
            raise ValueError(f"v3 result member drifted: {relative}")
    if _sha256(result / "config.yaml") != _sha256(CONFIG):
        raise ValueError("published v3 config drifted")
    runs, worker_pids, controller = _reconstruct_runs(
        result, config, load_json=_load_json_strict
    )
    published_runs = _list(_load_json_strict(result / "runs.json", "runs"), "runs")
    if published_runs != runs:
        raise ValueError("runs.json is not an exact reconstruction of worker payloads")
    semantic_config = _mapping(
        yaml.safe_load(SEMANTIC_CONFIG.read_text(encoding="utf-8")),
        "semantic config",
    )
    evaluator_report = _assert_evaluator_report(evaluate_runs(semantic_config, runs))
    semantic = _mapping(
        _load_json_strict(result / "semantic_validation.json", "semantic"),
        "semantic",
    )
    expected_semantic = {
        "schema": SEMANTIC_VALIDATION_SCHEMA,
        "semantic_successor_config_sha256": _sha256(SEMANTIC_CONFIG),
        "semantic_authority_sha256": config["semantic_authority"][
            "manifest_sha256"
        ],
        "v2_outer_sha256": V2_OUTER_SHA256,
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
        raise ValueError("v3 semantic validation wrapper drifted")
    summary = _mapping(
        _load_json_strict(result / "summary.json", "summary"), "summary"
    )
    expected_summary = {
        "schema": "rq2_public_solver_confirmatory_pilot_v3",
        "config_sha256": _sha256(CONFIG),
        "runner_sha256": _sha256(ROOT / RUNNER_RELATIVE),
        "semantic_authority_sha256": config["semantic_authority"][
            "manifest_sha256"
        ],
        "v2_outer_sha256": V2_OUTER_SHA256,
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
        raise ValueError("v3 summary drifted")
    return {
        "result_present": True,
        "result_manifest_sha256": _sha256(manifest_path),
        "confirmatory_pilot_executed": True,
        "cross_solver_confirmation_completed": True,
    }


def validate(
    config_path: Path = CONFIG,
    bundle_path: Path = BUNDLE,
    outer_path: Path = OUTER,
) -> dict[str, object]:
    if (
        config_path.resolve() != CONFIG.resolve()
        or bundle_path.resolve() != BUNDLE.resolve()
        or outer_path.resolve() != OUTER.resolve()
    ):
        raise ValueError("only canonical v3 artifacts are accepted")
    files, bundle_sha = _validate_bundle()
    if files.get(CONFIG_RELATIVE) != _sha256(CONFIG):
        raise ValueError("canonical v3 config hash drifted")
    config = _mapping(
        yaml.safe_load(CONFIG.read_text(encoding="utf-8")), "v3 config"
    )
    _validate_config(config)
    _validate_escalation(config)
    _validate_activation(config)
    v2_report = validate_v2()
    result = _validate_result(config)
    return {
        "schema": "rq2_public_solver_confirmatory_preexecution_validation_v3",
        "config_sha256": _sha256(CONFIG),
        "bundle_manifest_sha256": bundle_sha,
        "outer_manifest_sha256": _sha256(OUTER),
        "bundle_member_count": len(files),
        "v2_outer_sha256": V2_OUTER_SHA256,
        "v2_predecessor_validation_passed": v2_report["validation_passed"],
        "escalation_verdict": "ESCALATE",
        "v3_remediation_candidate_ready": True,
        "independent_v3_implementation_review_passed": False,
        "v4_execution_successor_present": False,
        "implementation_ready": True,
        "execution_ready": False,
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
