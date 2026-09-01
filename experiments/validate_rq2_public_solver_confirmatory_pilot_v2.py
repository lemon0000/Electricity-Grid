"""Fail-closed validator for the RQ2 confirmatory pilot v2 review candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from experiments.run_rq2_public_solver_confirmatory_pilot_v2 import (
    EXPECTED_RUNS,
    PROCESS_EVIDENCE_SCOPE,
    SEMANTIC_VALIDATION_SCHEMA,
    _assert_evaluator_report,
    _reconstruct_runs,
)
from experiments.validate_rq2_public_executor_environment_successor_v1 import (
    validate as validate_environment_successor,
)
from experiments.validate_rq2_public_solver_confirmatory_pilot_v1 import (
    validate as validate_confirmatory_v1,
)
from experiments.validate_rq2_public_solver_pilot_semantic_successor_v1 import (
    evaluate_runs,
)
from experiments.validate_rq2_public_solver_pilot_semantic_successor_v1 import (
    validate as validate_semantic_successor,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = "configs/rq2_public_solver_confirmatory_pilot_v2.yaml"
BUNDLE_RELATIVE = (
    "configs/rq2_public_solver_confirmatory_pilot_bundle_v2.SHA256SUMS.json"
)
OUTER_RELATIVE = (
    "configs/rq2_public_solver_confirmatory_pilot_bundle_v2.OUTER.SHA256SUMS.json"
)
REVIEW_RELATIVE = (
    "configs/rq2_public_solver_confirmatory_pilot_implementation_review_v2.yaml"
)
ACTIVATION_RELATIVE = (
    "configs/rq2_public_solver_confirmatory_pilot_activation_v2.yaml"
)
RUNNER_RELATIVE = "experiments/run_rq2_public_solver_confirmatory_pilot_v2.py"
VALIDATOR_RELATIVE = "experiments/validate_rq2_public_solver_confirmatory_pilot_v2.py"
TESTS_RELATIVE = "tests/test_rq2_public_solver_confirmatory_pilot_v2.py"
RESULT_RELATIVE = "results/tables/rq2_public_solver_confirmatory_pilot_v2"
CONFIG = ROOT / CONFIG_RELATIVE
BUNDLE = ROOT / BUNDLE_RELATIVE
OUTER = ROOT / OUTER_RELATIVE
RESULT = ROOT / RESULT_RELATIVE
SEMANTIC_CONFIG = (
    ROOT / "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml"
)
BUNDLE_INVENTORY = {
    CONFIG_RELATIVE,
    REVIEW_RELATIVE,
    ACTIVATION_RELATIVE,
    RUNNER_RELATIVE,
    VALIDATOR_RELATIVE,
    TESTS_RELATIVE,
}
SEMANTIC_HASHES = {
    "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml": (
        "cb0209a9a53962be8ebb6ee185d3bfbf3d004d7cd761e164b286a58e0c7887b0"
    ),
    "experiments/validate_rq2_public_solver_pilot_semantic_successor_v1.py": (
        "01b7f60a620c81a7a656ba6576c3b85af9e371b30d42dd5959f430ee220c80dd"
    ),
    "tests/test_rq2_public_solver_pilot_semantic_successor_v1.py": (
        "0137c3dfe6c71b183893dae1007f3e782eceec6030babb5a77dad8cc27c78584"
    ),
    "configs/rq2_public_solver_pilot_semantic_successor_v1.SHA256SUMS.json": (
        "c0b1a6a3074343ab5f281b268cd40898630ad1e2234830a4536189687832f471"
    ),
}
V1_CONFIRMATORY_HASHES = {
    "configs/rq2_public_solver_confirmatory_pilot_v1.yaml": (
        "c78bd3b901fdf9ff8dc1cc66c9adda6156ed1f889d3cc37a5870021b38ac3975"
    ),
    "configs/rq2_public_solver_confirmatory_pilot_activation_v1.yaml": (
        "b28a8254d93e8173e5cd9e62ad0200735ad6d3813b45401e42037266bc8ccc3f"
    ),
    "experiments/run_rq2_public_solver_confirmatory_pilot_v1.py": (
        "9f09327acb31b9ab174918a011a2fa0902e206731e898b8b150a6bbdc7eab007"
    ),
    "experiments/validate_rq2_public_solver_confirmatory_pilot_v1.py": (
        "7a4ab4e2afa9ffeabd3895d0152cb3bb7f438b06005058998257a70196064c7b"
    ),
    "tests/test_rq2_public_solver_confirmatory_pilot_v1.py": (
        "3ef675cbb8163304ad72c3ba6450797e7bd7d524b0b93360d265c6f43b599222"
    ),
    "configs/rq2_public_solver_confirmatory_pilot_bundle_v1.SHA256SUMS.json": (
        "ea3957c0ee3dd01f34efd6112db88fbfdec982e026aaec65e4780599db76dfe2"
    ),
    "configs/rq2_public_solver_confirmatory_pilot_bundle_v1.OUTER.SHA256SUMS.json": (
        "3bea21c2e1905d7a930c80da0dbf138cd130d85c221e436e961eb8965074205f"
    ),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return dict(value)


def _list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError(f"{label} must be a list")
    return value


def _load_json_strict_text(payload: str, label: str) -> Any:
    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} contains duplicate key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(
            payload,
            object_pairs_hook=no_duplicates,
            parse_constant=lambda value: (_ for _ in ()).throw(
                ValueError(f"{label} contains non-standard JSON constant: {value}")
            ),
        )
    except json.JSONDecodeError as error:
        raise ValueError(f"cannot parse {label}") from error


def _load_json_strict(path: Path, label: str) -> Any:
    try:
        payload = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError(f"cannot load {label}") from error
    return _load_json_strict_text(payload, label)


def _ordinary(relative: str, expected_sha256: str, label: str) -> None:
    path = ROOT / relative
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} is not an ordinary file: {relative}")
    if _sha256(path) != expected_sha256:
        raise ValueError(f"{label} hash drifted: {relative}")
    if path.suffix.lower() == ".json":
        _load_json_strict(path, label)


def _authority_hashes(config: Mapping[str, Any]) -> dict[str, str]:
    predecessor = _mapping(config["predecessor_authority"], "predecessor")
    v1 = _mapping(predecessor["v1_pilot"], "v1 pilot")
    windows = _mapping(predecessor["windows_executor_v2"], "Windows executor")
    environment = _mapping(
        predecessor["fresh_environment_successor"], "environment successor"
    )
    return {
        **SEMANTIC_HASHES,
        **V1_CONFIRMATORY_HASHES,
        config["rework_review_receipt"]["path"]: config[
            "rework_review_receipt"
        ]["sha256"],
        config["activation"]["path"]: config["activation"]["sha256"],
        v1["config_path"]: v1["config_sha256"],
        v1["runner_path"]: v1["runner_sha256"],
        v1["input_package_manifest_path"]: v1[
            "input_package_manifest_sha256"
        ],
        windows["handoff_path"]: windows["handoff_sha256"],
        windows["bundle_path"]: windows["bundle_sha256"],
        windows["outer_manifest_path"]: windows["outer_manifest_sha256"],
        windows["executor_path"]: windows["executor_sha256"],
        windows["run_entry_path"]: windows["run_entry_sha256"],
        environment["config_path"]: environment["config_sha256"],
        environment["manifest_path"]: environment["manifest_sha256"],
        environment["environment_path"]: environment["environment_sha256"],
        environment["validator_path"]: environment["validator_sha256"],
    }


def _validate_review_and_activation(config: Mapping[str, Any]) -> None:
    review = _mapping(
        yaml.safe_load((ROOT / REVIEW_RELATIVE).read_text(encoding="utf-8")),
        "REWORK receipt",
    )
    if (
        review.get("schema")
        != "rq2_public_solver_confirmatory_implementation_review_receipt_v2"
        or review.get("reviewed_on") != "2026-08-28"
        or review.get("reviewer_role") != "independent_sol_reviewer"
        or review.get("verdict") != "REWORK"
    ):
        raise ValueError("v2 REWORK receipt identity drifted")
    reviewed = _mapping(review.get("reviewed_bundle"), "reviewed v1 bundle")
    observed = {
        item["path"]: item["sha256"]
        for item in reviewed.values()
        if isinstance(item, Mapping)
    }
    if observed != V1_CONFIRMATORY_HASHES:
        raise ValueError("REWORK receipt v1 binding drifted")
    finding_ids = {
        item.get("id")
        for item in _list(review.get("findings"), "REWORK findings")
        if isinstance(item, Mapping)
    }
    if finding_ids != {
        "reachable_review_gate",
        "durable_per_run_process_provenance",
        "freshness_not_proven_by_runs_hash_difference",
        "exact_semantic_evaluator_contract",
        "strict_duplicate_key_json_loading",
        "watchdog_termination_confirmation",
        "canonical_module_entry_documentation",
    }:
        raise ValueError("REWORK findings drifted")
    effect = _mapping(review.get("effect"), "REWORK effect")
    if (
        effect.get("v1_bytes_remain_frozen") is not True
        or effect.get("v2_remediation_candidate_authorized") is not True
        or effect.get("v2_remediation_completed") is not False
        or effect.get("independent_v2_rereview_required") is not True
        or any(
            effect.get(field) is not False
            for field in (
                "independent_confirmatory_implementation_review_passed",
                "confirmatory_execution_authorized",
                "cross_solver_confirmation_completed",
                "formal_execution_ready",
                "formal_result_exists",
                "claim",
                "security_certified",
            )
        )
    ):
        raise ValueError("REWORK receipt effect drifted")
    activation = _mapping(
        yaml.safe_load((ROOT / ACTIVATION_RELATIVE).read_text(encoding="utf-8")),
        "v2 activation",
    )
    user = _mapping(activation.get("user_authority"), "user authority")
    if (
        activation.get("schema")
        != "rq2_public_solver_confirmatory_pilot_activation_v2"
        or activation.get("authorized_on") != "2026-08-28"
        or activation.get("status")
        != "remediation_candidate_only_independent_rereview_pending"
        or user.get("explicit_authorization_observed") is not True
        or user.get("authorization_record") != "继续做/按路径全部做完"
        or user.get("authorized_scope")
        != "prepare_and_independently_review_fresh_rq2_confirmatory_successor"
        or user.get("external_watchdog_seconds") != 21600
    ):
        raise ValueError("v2 activation identity drifted")
    rework = _mapping(activation.get("rework_authority"), "rework authority")
    if rework != {
        "receipt_path": REVIEW_RELATIVE,
        "receipt_sha256": config["rework_review_receipt"]["sha256"],
        "verdict": "REWORK",
    }:
        raise ValueError("v2 activation REWORK authority drifted")
    permissions = _mapping(activation.get("permissions"), "v2 permissions")
    if permissions != {
        "prepare_versioned_v2_remediation_candidate": True,
        "independently_review_v2_candidate": True,
        "execute_v2_candidate": False,
        "add_versioned_v3_execution_successor_after_exact_independent_pass": True,
        "execute_confirmatory_pilot_before_v3_gate": False,
        "execute_formal_grid": False,
        "execute_pairwise": False,
        "execute_identification": False,
        "make_formal_result_claim": False,
        "make_security_claim": False,
    }:
        raise ValueError("v2 activation permissions drifted")
    if activation.get("gates") != {
        "v2_remediation_candidate_ready": True,
        "independent_v2_implementation_review_passed": False,
        "v3_execution_successor_present": False,
        "confirmatory_execution_ready": False,
        "confirmatory_pilot_executed": False,
        "cross_solver_confirmation_completed": False,
        "formal_execution_ready": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }:
        raise ValueError("v2 activation gates drifted")


def _validate_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("schema") != "rq2_public_solver_confirmatory_pilot_config_v2"
        or config.get("version") != 2
        or config.get("frozen_on") != "2026-08-28"
        or config.get("status")
        != "remediation_candidate_ready_independent_rereview_pending"
    ):
        raise ValueError("v2 config identity drifted")
    scope = _mapping(config.get("scope"), "v2 scope")
    if scope != {
        "task_risk": "R3",
        "evidence_level": "nonformal_cross_solver_confirmatory_pilot",
        "fresh_solver_execution_required": True,
        "source_outcomes_observed": True,
        "confirmatory_outcomes_observed": False,
        "changes_model_formulation": False,
        "changes_solver_algorithm_threads_seed_or_tolerances": False,
        "changes_pilot_blocks_or_repetitions": False,
        "formal_grid_execution": False,
        "formal_pairwise_execution": False,
        "formal_identification_execution": False,
        "formal_claim_authorized": False,
        "security_claim_authorized": False,
    }:
        raise ValueError("v2 scope drifted")
    semantic = _mapping(config.get("semantic_authority"), "semantic authority")
    observed_semantic = {
        semantic["config_path"]: semantic["config_sha256"],
        semantic["validator_path"]: semantic["validator_sha256"],
        semantic["tests_path"]: semantic["tests_sha256"],
        semantic["manifest_path"]: semantic["manifest_sha256"],
    }
    if (
        observed_semantic != SEMANTIC_HASHES
        or semantic.get("review_verdict") != "PASS"
        or semantic.get("evaluator_function") != "evaluate_runs"
    ):
        raise ValueError("semantic authority drifted")
    v1 = _mapping(
        yaml.safe_load(
            (ROOT / "configs/rq2_public_solver_pilot_v1.yaml").read_text(
                encoding="utf-8"
            )
        ),
        "v1 config",
    )
    for field in ("input", "model", "pilot_blocks", "solvers"):
        if config.get(field) != v1.get(field):
            raise ValueError(f"v2 {field} does not inherit v1 exactly")
    execution = _mapping(config.get("execution"), "v2 execution")
    v1_execution = _mapping(v1.get("execution"), "v1 execution")
    if (
        execution.get("repetitions") != v1_execution.get("repetitions")
        or execution.get("pilot_execution_authorized_by_user") is not True
        or execution.get("independent_implementation_review_required") is not True
        or execution.get("execution_order") != EXPECTED_RUNS
        or execution.get("execution_order") != v1_execution.get("execution_order")
        or execution.get("forbidden_hostnames")
        != v1_execution.get("forbidden_hostnames")
        or execution.get("required_environment_value")
        != v1_execution.get("required_environment_value")
        or execution.get("external_watchdog_seconds") != 21600
        or execution.get("timeout_is_infeasibility_evidence") is not False
        or execution.get("unresolved_is_infeasibility_evidence") is not False
        or execution.get("python_authority")
        != {
            "source": "windows_executor_v2",
            "environment_variable": "RQ2_EXECUTOR_PYTHON_EXE",
            "absolute_regular_non_symlink_file_required": True,
            "must_equal_controller_sys_executable": True,
        }
    ):
        raise ValueError("v2 execution contract drifted")
    if any(
        solver.get("threads") != 4
        or solver.get("random_seed") != 0
        or solver.get("time_limit_seconds") is not None
        for solver in config["solvers"].values()
    ):
        raise ValueError("v2 solver threads, seed, or time limit drifted")
    acceptance = _mapping(config.get("acceptance"), "v2 acceptance")
    v1_acceptance = _mapping(v1.get("acceptance"), "v1 acceptance")
    expected_acceptance = {
        "semantic_contract_source": (
            "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml"
        ),
        "require_all_baselines_accepted": True,
        "require_all_hours_resolved_for_pipeline": True,
        "require_identical_semantic_state_classification": True,
        "require_expected_E0_hour_sets": True,
        "require_identical_model_scale": True,
        "maximum_baseline_objective_difference_usd": v1_acceptance[
            "maximum_baseline_objective_difference_usd"
        ],
        "maximum_finite_grid_need_difference_mw": v1_acceptance[
            "maximum_finite_grid_need_difference_mw"
        ],
        "maximum_constraint_violation": v1_acceptance[
            "maximum_constraint_violation"
        ],
        "solver_relative_gap": 1.0e-6,
        "numeric_serialization_consistency_tolerance": 1.0e-12,
        "hourly_solver_report_absolute_tolerance_mw": 1.0e-10,
        "timeout_is_infeasibility_evidence": False,
        "unresolved_is_infeasibility_evidence": False,
        "missing_or_incomplete_certificate_is_confirmation": False,
        "scientific_threshold_values_changed": False,
    }
    if acceptance != expected_acceptance:
        raise ValueError("v2 acceptance thresholds or gates drifted")
    implementation = _mapping(config.get("implementation"), "implementation")
    if implementation != {
        "runner_path": RUNNER_RELATIVE,
        "runner_hash_authority": BUNDLE_RELATIVE,
        "controller_calls_solver": False,
        "worker_process_model": (
            "one_fresh_independent_python_subprocess_per_run_id"
        ),
        "worker_output_model": (
            "one_registered_payload_then_parent_issued_receipt_per_run_id"
        ),
        "durable_worker_evidence": True,
        "result_reconstructed_from_durable_payloads": True,
        "process_evidence_scope": (
            "controller_observed_execution_evidence_not_third_party_os_attestation"
        ),
    }:
        raise ValueError("v2 implementation contract drifted")
    provenance = _mapping(config.get("provenance"), "provenance")
    if provenance != {
        "controller_receipt": "controller_receipt.json",
        "worker_root": "workers",
        "worker_files_per_run": ["payload.json", "receipt.json"],
        "payload_written_by_worker": True,
        "receipt_written_by_controller_after_exit_zero_and_validation": True,
        "exact_tree_required": True,
        "bind_controller_nonce_pid_and_start_identity": True,
        "bind_config_runner_semantic_authority_hashes": True,
        "bind_worker_pid_ppid_exit_code_payload_hash_and_execution_index": True,
        "controller_receipts_form_ordered_hash_chain": True,
        "controller_receipt_issue_times_strictly_increase": True,
        "unique_worker_pid_per_run": True,
        "worker_parent_pid_must_equal_controller_pid": True,
        "reconstruct_runs_from_payloads": True,
        "evidence_limit": (
            "execution_time_controller_observation_not_external_os_or_hardware_attestation"
        ),
    }:
        raise ValueError("v2 provenance contract drifted")
    output = _mapping(config.get("output"), "output")
    if output != {
        "schema": "rq2_public_solver_confirmatory_pilot_v2",
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
        "v1_run_reuse_allowed": False,
    }:
        raise ValueError("v2 output contract drifted")
    successor = _mapping(
        config.get("gate_opening_successor_contract"), "successor contract"
    )
    if (
        successor.get("current_v2_bytes_become_immutable_after_sealing") is not True
        or successor.get("current_v2_execution_gate_remains_closed") is not True
        or successor.get("future_successor_version") != 3
        or successor.get("future_files_are_not_current_manifest_members") is not True
        or successor.get("v3_required_new_artifacts")
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
        or successor.get("v3_required_new_artifact_paths")
        != {
            "pass_receipt": (
                "configs/rq2_public_solver_confirmatory_pilot_"
                "implementation_review_pass_v3.yaml"
            ),
            "activation": (
                "configs/rq2_public_solver_confirmatory_pilot_activation_v3.yaml"
            ),
            "config": "configs/rq2_public_solver_confirmatory_pilot_v3.yaml",
            "runner": "experiments/run_rq2_public_solver_confirmatory_pilot_v3.py",
            "validator": (
                "experiments/validate_rq2_public_solver_confirmatory_pilot_v3.py"
            ),
            "tests": "tests/test_rq2_public_solver_confirmatory_pilot_v3.py",
            "bundle": (
                "configs/rq2_public_solver_confirmatory_pilot_"
                "bundle_v3.SHA256SUMS.json"
            ),
            "outer": (
                "configs/rq2_public_solver_confirmatory_pilot_"
                "bundle_v3.OUTER.SHA256SUMS.json"
            ),
        }
        or successor.get("v3_must_bind_exact_v2_outer_sha256") is not True
        or successor.get("v3_must_bind_exact_pass_receipt_sha256") is not True
        or successor.get("v3_may_authorize_only_fresh_confirmatory_pilot") is not True
        or successor.get("v3_output_directory")
        != "results/tables/rq2_public_solver_confirmatory_pilot_v3"
        or successor.get("modifying_v2_or_predecessor_bytes_forbidden") is not True
        or successor.get(
            "grid_pairwise_identification_formal_or_security_authority"
        )
        is not False
    ):
        raise ValueError("reachable v3 successor contract drifted")
    pass_receipt = _mapping(
        successor.get("independent_pass_receipt"), "future PASS receipt contract"
    )
    if pass_receipt != {
        "required_verdict": "PASS",
        "reviewer_role": "independent_sol_reviewer",
        "must_bind_exact_v2_hashes": [
            "config",
            "activation",
            "runner",
            "validator",
            "tests",
            "bundle",
            "outer",
        ],
        "receipt_must_be_new_after_v2_outer_is_sealed": True,
    }:
        raise ValueError("future PASS receipt contract drifted")
    gates = _mapping(config.get("gates"), "v2 gates")
    if gates != {
        "semantic_successor_review_passed": True,
        "user_confirmatory_authorization_recorded": True,
        "v2_remediation_candidate_ready": True,
        "independent_v2_implementation_review_passed": False,
        "v3_execution_successor_present": False,
        "confirmatory_execution_ready": False,
        "confirmatory_pilot_executed": False,
        "cross_solver_confirmation_completed": False,
        "formal_execution_ready": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }:
        raise ValueError("v2 gates drifted")
    for relative, expected in _authority_hashes(config).items():
        _ordinary(relative, expected, "v2 predecessor authority")


def _validate_bundle() -> tuple[dict[str, str], str]:
    bundle = _mapping(_load_json_strict(BUNDLE, "v2 bundle"), "v2 bundle")
    if bundle.get("schema") != "rq2_public_solver_confirmatory_bundle_manifest_v2":
        raise ValueError("v2 bundle schema drifted")
    files = _mapping(bundle.get("files"), "v2 bundle files")
    if set(files) != BUNDLE_INVENTORY:
        raise ValueError("v2 bundle inventory drifted")
    for relative, expected in files.items():
        _ordinary(relative, expected, "v2 bundle member")
    bundle_sha = _sha256(BUNDLE)
    outer = _mapping(_load_json_strict(OUTER, "v2 outer manifest"), "v2 outer")
    if outer != {
        "schema": "rq2_public_solver_confirmatory_outer_manifest_v2",
        "files": {BUNDLE_RELATIVE: bundle_sha},
    }:
        raise ValueError("v2 outer manifest drifted")
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
        raise ValueError("v2 result path is not an ordinary directory")
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
        raise ValueError("v2 result top-level inventory drifted")
    if any(item.is_symlink() for item in children):
        raise ValueError("v2 result top-level symlink is forbidden")
    manifest_path = result / "SHA256SUMS.json"
    if not manifest_path.is_file():
        raise ValueError("v2 result manifest must be an ordinary file")
    manifest = _mapping(
        _load_json_strict(manifest_path, "v2 result manifest"), "result manifest"
    )
    if set(manifest) != _expected_result_members():
        raise ValueError("v2 result recursive manifest inventory drifted")
    observed_files: set[str] = set()
    for path in result.rglob("*"):
        if path.is_symlink():
            raise ValueError("v2 result tree contains a symlink")
        if path.is_file() and path != manifest_path:
            observed_files.add(path.relative_to(result).as_posix())
    if observed_files != set(manifest):
        raise ValueError("v2 result exact file tree drifted")
    for relative, expected in manifest.items():
        path = result / relative
        if not path.is_file() or path.is_symlink() or _sha256(path) != expected:
            raise ValueError(f"v2 result member drifted: {relative}")
    if _sha256(result / "config.yaml") != _sha256(CONFIG):
        raise ValueError("published v2 config drifted")
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
        _load_json_strict(result / "semantic_validation.json", "semantic validation"),
        "semantic validation",
    )
    expected_semantic = {
        "schema": SEMANTIC_VALIDATION_SCHEMA,
        "semantic_successor_config_sha256": _sha256(SEMANTIC_CONFIG),
        "semantic_authority_sha256": config["semantic_authority"][
            "manifest_sha256"
        ],
        "evaluator_report": evaluator_report,
        "fresh_execution_run_ids": EXPECTED_RUNS,
        "fresh_worker_pids": worker_pids,
        "controller_identity_sha256": controller["controller_identity_sha256"],
        "controller_receipt_sha256": controller["receipt_sha256"],
        "durable_process_provenance_verified": True,
        "runs_reconstructed_exactly_from_worker_payloads": True,
        "process_evidence_scope": PROCESS_EVIDENCE_SCOPE,
        "semantic_contract_passed": True,
        "cross_solver_confirmation_completed": True,
        "formal_grid_execution_started": False,
        "security_certified": False,
    }
    if semantic != expected_semantic:
        raise ValueError("v2 semantic validation wrapper drifted")
    summary = _mapping(
        _load_json_strict(result / "summary.json", "summary"), "summary"
    )
    expected_summary = {
        "schema": "rq2_public_solver_confirmatory_pilot_v2",
        "config_sha256": _sha256(CONFIG),
        "runner_sha256": _sha256(ROOT / RUNNER_RELATIVE),
        "semantic_authority_sha256": config["semantic_authority"][
            "manifest_sha256"
        ],
        "fresh_execution_status": "passed",
        "fresh_execution_passed": True,
        "fresh_execution_failed": False,
        "run_count": 4,
        "unique_worker_process_count": 4,
        "durable_process_provenance_verified": True,
        "runs_reconstructed_exactly_from_worker_payloads": True,
        "semantic_contract_passed": True,
        "cross_solver_confirmation_completed": True,
        "formal_grid_execution_started": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    if summary != expected_summary:
        raise ValueError("v2 summary drifted")
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
        raise ValueError("only canonical v2 artifacts are accepted")
    files, bundle_sha = _validate_bundle()
    if files.get(CONFIG_RELATIVE) != _sha256(CONFIG):
        raise ValueError("canonical v2 config hash drifted")
    config = _mapping(
        yaml.safe_load(CONFIG.read_text(encoding="utf-8")), "v2 config"
    )
    _validate_config(config)
    _validate_review_and_activation(config)
    v1_report = validate_confirmatory_v1()
    semantic_report = validate_semantic_successor()
    environment_report = validate_environment_successor(runtime=False)
    result = _validate_result(config)
    return {
        "schema": "rq2_public_solver_confirmatory_preexecution_validation_v2",
        "config_sha256": _sha256(CONFIG),
        "bundle_manifest_sha256": bundle_sha,
        "outer_manifest_sha256": _sha256(OUTER),
        "bundle_member_count": len(files),
        "v1_confirmatory_predecessor_validation_passed": v1_report[
            "validation_passed"
        ],
        "semantic_successor_review_verdict": "PASS",
        "semantic_successor_validation_passed": semantic_report["validation_passed"],
        "environment_successor_validation_passed": environment_report[
            "validation_passed"
        ],
        "rework_verdict": "REWORK",
        "v2_remediation_candidate_ready": True,
        "independent_v2_implementation_review_passed": False,
        "v3_execution_successor_present": False,
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
