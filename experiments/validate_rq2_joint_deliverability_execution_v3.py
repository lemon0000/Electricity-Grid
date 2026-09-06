"""Static fail-closed validator for the RQ2 execution successor v3."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = "configs/rq2_joint_deliverability_execution_successor_v3.yaml"
CORE_RELATIVE = "src/rq2_joint_deliverability_execution_v3/core.py"
RUNNER_RELATIVE = "experiments/run_rq2_joint_deliverability_execution_v3.py"
VALIDATOR_RELATIVE = "experiments/validate_rq2_joint_deliverability_execution_v3.py"
TEST_RELATIVE = "tests/test_rq2_joint_deliverability_execution_v3.py"
ARCHITECTURE_RELATIVE = "docs/model_spec/rq2_joint_deliverability_execution_v3.md"
INNER_RELATIVE = (
    "configs/rq2_joint_deliverability_execution_successor_v3.SHA256SUMS.json"
)
OUTER_RELATIVE = (
    "configs/rq2_joint_deliverability_execution_successor_v3.OUTER.SHA256SUMS.json"
)
INNER = ROOT / INNER_RELATIVE
OUTER = ROOT / OUTER_RELATIVE

EXPECTED_AUTHORITIES = {
    "scientific_outer": {
        "path": "configs/rq2_joint_deliverability_preregistration_successor_v5.OUTER.SHA256SUMS.json",
        "sha256": "92a58498e1de5f84b132067e3d4a4443ae841747846785e9df54cd9afd7efdfd",
    },
    "scientific_review": {
        "path": "configs/rq2_joint_deliverability_preregistration_review_pass_v5.yaml",
        "sha256": "0ec073c38eac003255fa2d2753edb28f4d02e0f7756c34e185027ac23b140722",
    },
    "implementation_outer": {
        "path": "configs/rq2_joint_deliverability_implementation_successor_v2.OUTER.SHA256SUMS.json",
        "sha256": "e086f13cca12e198fd69553bc574662d615ab09b343ac6619e2448b94a7f2ee2",
    },
    "implementation_review": {
        "path": "configs/rq2_joint_deliverability_implementation_review_pass_v2.yaml",
        "sha256": "67beedbaa1c54118c0039acc1d8b038b7e0aada5ba416b6a9b5949d46ead30d3",
    },
    "executor_environment": {
        "path": "environments/rq2_executor_v2.yml",
        "sha256": "310b5c2f1261678269cf2e1424255f48582975aec7e492fe029f45cd5e73bdf6",
    },
}
EXPECTED_PREDECESSOR_AUTHORITY = {
    "execution_outer": {
        "path": (
            "configs/rq2_joint_deliverability_execution_successor_v2."
            "OUTER.SHA256SUMS.json"
        ),
        "sha256": "ff70b138f61833908c84763c3a6df06ad255f6f6f26adfbf1e4051865a0e5f93",
    },
    "official_review": {
        "path": "configs/rq2_joint_deliverability_execution_review_escalate_v2.yaml",
        "sha256": "969cd58f090cc9fa6dfba986715ec67a8e18dfcf8e188d97c11748f421895b6d",
        "verdict": "ESCALATE",
        "blocker_findings": 0,
        "major_findings": 1,
        "minor_findings": 0,
    },
    "superseded_review": {
        "path": (
            "configs/rq2_joint_deliverability_execution_review_pass_v2.superseded.yaml"
        ),
        "sha256": "20c13ff59f47a76eb9aad6962884b8605aa7de76833cdf00abc62229bc7f1a35",
        "original_verdict": "PASS",
        "current_authority": False,
    },
    "fixed_pass_authority": {
        "path": "configs/rq2_joint_deliverability_execution_review_pass_v2.yaml",
        "required_absent": True,
    },
}
EXPECTED_EXECUTION_REVIEW_AUTHORITY = {
    "path": "configs/rq2_joint_deliverability_execution_review_pass_v3.yaml",
    "schema": "rq2_joint_deliverability_execution_review_pass_v3",
    "review_scope": "rq2_joint_deliverability_execution_successor_v3_exact_outer",
    "reviewer_role": "independent_sol_reviewer",
    "required_verdict": "PASS",
    "required_effect": {
        "independent_v3_R3_review_passed": True,
        "independent_review_gate_closed": True,
        "formal_execution_authorized": False,
        "formal_result_exists": False,
        "paper_claim": False,
        "security_certified": False,
    },
}
EXPECTED_EXECUTION_RUNTIME_AUTHORITY = {
    "path": (
        "results/execution_configs/rq2_joint_deliverability_execution_v3/"
        "runtime_receipt.json"
    ),
    "schema": "rq2_joint_deliverability_execution_runtime_receipt_v3",
    "sha256": None,
    "ready": False,
}
EXPECTED_EXECUTION_ACTIVATION_AUTHORITY = {
    "path": "configs/rq2_joint_deliverability_execution_activation_pass_v3.yaml",
    "schema": "rq2_joint_deliverability_execution_activation_pass_v3",
    "sha256": None,
    "ready": False,
}
EXPECTED_IMPLEMENTATION = {
    "core": {"path": CORE_RELATIVE},
    "runner": {"path": RUNNER_RELATIVE},
    "validator": {"path": VALIDATOR_RELATIVE},
    "tests": {"path": TEST_RELATIVE},
    "architecture": {"path": ARCHITECTURE_RELATIVE},
}
EXPECTED_MEMBERS = {
    CONFIG_RELATIVE,
    CORE_RELATIVE,
    RUNNER_RELATIVE,
    VALIDATOR_RELATIVE,
    TEST_RELATIVE,
    ARCHITECTURE_RELATIVE,
    "src/rq2_joint_deliverability_execution_v3/__init__.py",
    "src/__init__.py",
    "experiments/__init__.py",
    *(item["path"] for item in EXPECTED_AUTHORITIES.values()),
    EXPECTED_PREDECESSOR_AUTHORITY["execution_outer"]["path"],
    EXPECTED_PREDECESSOR_AUTHORITY["official_review"]["path"],
    EXPECTED_PREDECESSOR_AUTHORITY["superseded_review"]["path"],
    "configs/rts_gmlc_public_grid_need_dispatch_v4.yaml",
    "results/execution_configs/rq2_public_successor_v2/grid.yaml",
    "results/execution_configs/rq2_public_successor_v2/grid.activation.json",
    "data/processed/model_inputs/rts_gmlc_public_power_system_blocks_v4/SHA256SUMS.json",
    "data/processed/model_inputs/alibaba_dimensionless_workload_blocks_v3/SHA256SUMS.json",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"YAML root must be a mapping: {path}")
    return payload


def _load_json(path: Path) -> dict[str, Any]:
    def reject_duplicate_keys(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON object key: {key}")
            result[key] = value
        return result

    def reject_nonfinite_constant(constant: str) -> None:
        raise ValueError(f"non-finite JSON number: {constant}")

    def parse_finite_float(raw: str) -> float:
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError(f"non-finite JSON number: {raw}")
        return value

    payload = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_nonfinite_constant,
        parse_float=parse_finite_float,
    )
    if not isinstance(payload, dict):
        raise TypeError(f"JSON root must be a mapping: {path}")
    return payload


def _regular(path: Path, label: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} is not a regular file")


def _definitions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }


def _validate_authorities(config: dict[str, Any]) -> None:
    if config.get("authority") != EXPECTED_AUTHORITIES:
        raise ValueError("execution authority binding drifted")
    for item in EXPECTED_AUTHORITIES.values():
        path = ROOT / item["path"]
        _regular(path, item["path"])
        if _sha256(path) != item["sha256"]:
            raise ValueError(f"execution authority SHA-256 drifted: {item['path']}")


def _validate_predecessor_authority(config: dict[str, Any]) -> None:
    if config.get("predecessor_authority") != EXPECTED_PREDECESSOR_AUTHORITY:
        raise ValueError("execution predecessor authority binding drifted")
    outer_item = EXPECTED_PREDECESSOR_AUTHORITY["execution_outer"]
    outer_path = ROOT / str(outer_item["path"])
    _regular(outer_path, str(outer_item["path"]))
    if _sha256(outer_path) != outer_item["sha256"]:
        raise ValueError("execution predecessor outer SHA-256 drifted")
    outer = _load_json(outer_path)
    inner_identity = outer.get("inner")
    if (
        outer.get("schema") != "rq2_joint_deliverability_execution_outer_v2"
        or outer.get("version") != 2
        or not isinstance(inner_identity, dict)
        or set(inner_identity) != {"path", "sha256"}
    ):
        raise ValueError("execution predecessor outer drifted")
    inner_path = ROOT / str(inner_identity["path"])
    _regular(inner_path, str(inner_identity["path"]))
    if _sha256(inner_path) != inner_identity["sha256"]:
        raise ValueError("execution predecessor inner SHA-256 drifted")
    inner = _load_json(inner_path)
    files = inner.get("files")
    if (
        inner.get("schema") != "rq2_joint_deliverability_execution_inner_v2"
        or inner.get("version") != 2
        or not isinstance(files, dict)
        or len(files) != 21
    ):
        raise ValueError("execution predecessor inner drifted")
    for relative, expected in files.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise TypeError("execution predecessor member identity drifted")
        member = ROOT / relative
        _regular(member, relative)
        if _sha256(member) != expected:
            raise ValueError(f"execution predecessor member drifted: {relative}")

    nested_outer_relative = (
        "configs/rq2_joint_deliverability_execution_successor_v1.OUTER.SHA256SUMS.json"
    )
    nested_outer = _load_json(ROOT / nested_outer_relative)
    nested_inner_identity = nested_outer.get("inner")
    if (
        nested_outer.get("schema") != "rq2_joint_deliverability_execution_outer_v1"
        or nested_outer.get("version") != 1
        or not isinstance(nested_inner_identity, dict)
        or set(nested_inner_identity) != {"path", "sha256"}
        or files.get(nested_outer_relative) != _sha256(ROOT / nested_outer_relative)
    ):
        raise ValueError("nested execution predecessor outer drifted")
    nested_inner_path = ROOT / str(nested_inner_identity["path"])
    _regular(nested_inner_path, str(nested_inner_identity["path"]))
    if _sha256(nested_inner_path) != nested_inner_identity["sha256"]:
        raise ValueError("nested execution predecessor inner SHA-256 drifted")
    nested_inner = _load_json(nested_inner_path)
    nested_files = nested_inner.get("files")
    if (
        nested_inner.get("schema") != "rq2_joint_deliverability_execution_inner_v1"
        or nested_inner.get("version") != 1
        or not isinstance(nested_files, dict)
        or len(nested_files) != 19
    ):
        raise ValueError("nested execution predecessor inner drifted")
    for relative, expected in nested_files.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise TypeError("nested execution predecessor member identity drifted")
        member = ROOT / relative
        _regular(member, relative)
        if _sha256(member) != expected:
            raise ValueError(f"nested execution predecessor member drifted: {relative}")

    review_item = EXPECTED_PREDECESSOR_AUTHORITY["official_review"]
    review_path = ROOT / str(review_item["path"])
    _regular(review_path, str(review_item["path"]))
    if _sha256(review_path) != review_item["sha256"]:
        raise ValueError("execution predecessor review SHA-256 drifted")
    escalation = _load_yaml(review_path)
    reviewed = escalation.get("reviewed_subject")
    effect = escalation.get("effect")
    findings = escalation.get("findings")
    if not isinstance(findings, list) or any(
        not isinstance(item, dict) for item in findings
    ):
        raise ValueError("execution predecessor review findings drifted")
    finding_counts = {
        severity: sum(item.get("severity") == severity for item in findings)
        for severity in ("blocker", "major", "minor")
    }
    if (
        escalation.get("schema")
        != "rq2_joint_deliverability_execution_review_escalate_v2"
        or escalation.get("review_scope")
        != "rq2_joint_deliverability_execution_successor_v2_post_review_state"
        or escalation.get("reviewer_role") != "independent_sol_reviewer"
        or escalation.get("verdict") != review_item["verdict"]
        or not isinstance(reviewed, dict)
        or reviewed.get("outer_path") != outer_item["path"]
        or reviewed.get("outer_sha256") != outer_item["sha256"]
        or reviewed.get("inner_sha256") != inner_identity["sha256"]
        or reviewed.get("sealed_member_count") != len(files)
        or finding_counts["blocker"] != review_item["blocker_findings"]
        or finding_counts["major"] != review_item["major_findings"]
        or finding_counts["minor"] != review_item["minor_findings"]
        or not isinstance(effect, dict)
        or effect.get("v2_bytes_immutable") is not True
        or effect.get("original_pass_receipt_current_authority") is not False
        or effect.get("independent_v2_R3_review_passed") is not False
        or effect.get("automatic_successor_allowed") is not False
        or effect.get("user_or_sol_modeler_escalation_required") is not True
        or effect.get("formal_execution_authorized") is not False
    ):
        raise ValueError("execution predecessor review receipt drifted")

    superseded_item = EXPECTED_PREDECESSOR_AUTHORITY["superseded_review"]
    superseded_path = ROOT / str(superseded_item["path"])
    _regular(superseded_path, str(superseded_item["path"]))
    if _sha256(superseded_path) != superseded_item["sha256"]:
        raise ValueError("execution predecessor superseded review SHA-256 drifted")
    superseded = _load_yaml(superseded_path)
    superseded_subject = superseded.get("reviewed_subject")
    superseded_effect = superseded.get("effect")
    escalation_supersession = escalation.get("superseded_review")
    if (
        superseded.get("schema") != "rq2_joint_deliverability_execution_review_pass_v2"
        or superseded.get("review_scope")
        != "rq2_joint_deliverability_execution_successor_v2_exact_outer"
        or superseded.get("verdict") != superseded_item["original_verdict"]
        or not isinstance(superseded_subject, dict)
        or superseded_subject.get("outer_path") != outer_item["path"]
        or superseded_subject.get("outer_sha256") != outer_item["sha256"]
        or superseded_subject.get("inner_sha256") != inner_identity["sha256"]
        or superseded_subject.get("sealed_member_count") != len(files)
        or not isinstance(superseded_effect, dict)
        or superseded_effect.get("independent_v2_R3_review_passed") is not True
        or not isinstance(escalation_supersession, dict)
        or escalation_supersession.get("original_path")
        != EXPECTED_PREDECESSOR_AUTHORITY["fixed_pass_authority"]["path"]
        or escalation_supersession.get("preserved_path") != superseded_item["path"]
        or escalation_supersession.get("sha256") != superseded_item["sha256"]
        or escalation_supersession.get("current_authority")
        is not superseded_item["current_authority"]
        or escalation_supersession.get("fixed_authority_path_absent") is not True
    ):
        raise ValueError("execution predecessor superseded review drifted")

    fixed_item = EXPECTED_PREDECESSOR_AUTHORITY["fixed_pass_authority"]
    fixed_path = ROOT / str(fixed_item["path"])
    if (
        fixed_item["required_absent"] is not True
        or fixed_path.exists()
        or fixed_path.is_symlink()
    ):
        raise ValueError("execution predecessor fixed PASS authority is not absent")


def _validate_execution_review_authority(config: dict[str, Any]) -> None:
    if config.get("execution_review_authority") != EXPECTED_EXECUTION_REVIEW_AUTHORITY:
        raise ValueError("execution review authority contract drifted")
    if (
        config.get("execution_runtime_authority")
        != EXPECTED_EXECUTION_RUNTIME_AUTHORITY
        or config.get("execution_activation_authority")
        != EXPECTED_EXECUTION_ACTIVATION_AUTHORITY
    ):
        raise ValueError("execution runtime or activation authority contract drifted")


def _validate_inputs(config: dict[str, Any]) -> None:
    inputs = config.get("registered_inputs")
    if not isinstance(inputs, dict) or set(inputs) != {
        "power_base",
        "workload",
        "dispatched_grid",
    }:
        raise ValueError("registered input inventory drifted")
    power = inputs["power_base"]
    workload = inputs["workload"]
    grid = inputs["dispatched_grid"]
    if (
        power
        != {
            "package": "data/processed/model_inputs/rts_gmlc_public_power_system_blocks_v4",
            "manifest_path": "data/processed/model_inputs/rts_gmlc_public_power_system_blocks_v4/SHA256SUMS.json",
            "manifest_sha256": "28bc2c3c1ee3ba0ef6c940aec56f66d49587b5f2895d0e6b0b83fb0b6360cc63",
            "hourly_file": "power_system_blocks.csv.gz",
            "training_blocks": 541,
            "holdout_blocks": 530,
        }
        or workload
        != {
            "package": "data/processed/model_inputs/alibaba_dimensionless_workload_blocks_v3",
            "manifest_path": "data/processed/model_inputs/alibaba_dimensionless_workload_blocks_v3/SHA256SUMS.json",
            "manifest_sha256": "62f2ec5eefd0c651d8b970a16fce4fb6336ccb75ab09e3d2c67386cc26edb524",
            "hourly_file": "workload_blocks.csv.gz",
            "training_blocks": 34,
            "holdout_blocks": 34,
        }
        or grid
        != {
            "package": "data/processed/model_inputs/rts_gmlc_public_grid_need_dispatch_v4_gurobi",
            "manifest_path": "data/processed/model_inputs/rts_gmlc_public_grid_need_dispatch_v4_gurobi/SHA256SUMS.json",
            "manifest_sha256": None,
            "hourly_file": "dispatched_power_system_blocks.csv.gz",
            "template_config_path": "configs/rts_gmlc_public_grid_need_dispatch_v4.yaml",
            "template_config_sha256": (
                "84db8e7ad47bf51dd1ec94db1ebb7d3edc068b587afb4fba8d596861d58e6beb"
            ),
            "config_path": "results/execution_configs/rq2_public_successor_v2/grid.yaml",
            "config_sha256": (
                "b8f7a71f8aaf8150c8515089e90e1946732d4476e0855d8677523577bc17f416"
            ),
            "activation_record_path": (
                "results/execution_configs/rq2_public_successor_v2/grid.activation.json"
            ),
            "activation_record_sha256": (
                "f2c76d5522e0501b76935611296aad8348adf178b396262f7a23ef83d7582df4"
            ),
            "dc_reference_demand_mw": 250.0,
            "ready": False,
        }
    ):
        raise ValueError("registered input contract drifted")
    for path_key, digest_key in (
        ("template_config_path", "template_config_sha256"),
        ("config_path", "config_sha256"),
        ("activation_record_path", "activation_record_sha256"),
    ):
        relative = grid[path_key]
        _regular(ROOT / relative, relative)
        if _sha256(ROOT / relative) != grid[digest_key]:
            raise ValueError(f"registered grid authority drifted: {relative}")
    activation_record = _load_json(ROOT / grid["activation_record_path"])
    if (
        activation_record.get("schema") != "rq2_public_grid_stage_activation_v2"
        or activation_record.get("activated_config_path") != grid["config_path"]
        or activation_record.get("activated_config_sha256") != grid["config_sha256"]
        or activation_record.get("template_path") != grid["template_config_path"]
        or activation_record.get("template_sha256") != grid["template_config_sha256"]
        or activation_record.get("formal_execution_ready") is not True
    ):
        raise ValueError("registered grid activation chain drifted")


def _validate_code_inventory(config: dict[str, Any]) -> None:
    if config.get("implementation") != EXPECTED_IMPLEMENTATION:
        raise ValueError("execution implementation inventory drifted")
    for item in EXPECTED_IMPLEMENTATION.values():
        _regular(ROOT / item["path"], item["path"])
    required_core = {
        "EvidenceStore",
        "aggregate_bootstrap_checkpoints",
        "audit_dispatched_grid_inventory",
        "audit_registered_inputs",
        "audit_split_inventory",
        "bootstrap_draw_stream_sha256",
        "capture_primal_evidence",
        "commit_bootstrap_cell",
        "commit_holdout_chunk",
        "commit_holdout_metric_matrices",
        "derive_static_authority",
        "execute_bootstrap_resumable",
        "execute_planning_stage_with_evidence",
        "_execute_planning_stage_with_evidence_from_audit",
        "measure_synthetic_streaming_profile",
        "metrics_from_trajectory",
        "load_holdout_metric_matrices",
        "planning_input_sha256",
        "replay_and_commit_holdout_metric_matrices",
        "replay_primal_evidence",
        "replay_holdout_metric_matrices",
        "run_identity",
        "stream_holdout_stage",
        "streaming_scale_projection",
        "verify_flat_manifest",
        "verify_outer_chain",
    }
    if not required_core.issubset(_definitions(ROOT / CORE_RELATIVE)):
        raise ValueError("execution core function inventory drifted")
    if not {"run", "validate_runtime_contract"}.issubset(
        _definitions(ROOT / RUNNER_RELATIVE)
    ):
        raise ValueError("execution runner function inventory drifted")


def _validate_closed_effects(config: dict[str, Any]) -> None:
    scope = config.get("scope")
    gates = config.get("gates")
    if not isinstance(scope, dict) or not isinstance(gates, dict):
        raise TypeError("execution scope or gates are malformed")
    if scope != {
        "task_risk": "R3",
        "purpose": "platform_neutral_execution_evidence_and_resume_infrastructure",
        "changes_scientific_protocol": False,
        "changes_reference_implementation": False,
        "runs_solver_during_validation": False,
        "writes_formal_results_during_validation": False,
        "formal_execution": False,
        "formal_result": False,
        "paper_claim": False,
        "security_certification": False,
    }:
        raise ValueError("execution scope drifted")
    lifecycle_status = config["lifecycle"]["status"]
    pre_seal_complete = lifecycle_status == "SEALED_READY_FOR_INDEPENDENT_REVIEW"
    if gates != {
        "execution_candidate_complete": pre_seal_complete,
        "pre_seal_audit_complete": pre_seal_complete,
        "independent_R3_review_passed": False,
        "upstream_grid_package_ready": False,
        "execution_machine_runtime_ready": False,
        "native_solver_replay_passed": False,
        "registered_memory_profile_passed": False,
        "transport_runtime_projection_accepted": False,
        "user_formal_run_authorized": False,
        "formal_execution_ready": False,
        "formal_result": False,
        "paper_claim": False,
        "security_certified": False,
    }:
        raise ValueError("execution gate inventory drifted")
    if config.get("activation_requirements") != [
        "exact_dispatched_grid_manifest_bound",
        "complete_grid_checkpoint_directory_bound_by_package_inventory",
        "upstream_grid_package_ready",
        "windows_x86_64_runtime_receipt",
        "gurobipy_13_0_2_and_license_preflight",
        "native_solver_evidence_probe_passed",
        "registered_dimension_memory_profile_passed",
        "measured_transport_runtime_projection_accepted",
        "canonical_fresh_output_root",
        "exclusive_run_lease_and_reviewed_resume_authority",
        "stdlib_first_fresh_process_runtime_import_closure",
        "independent_R3_execution_review_passed",
        "separate_user_formal_run_authorization",
    ]:
        raise ValueError("activation requirement inventory drifted")


def _validate_contracts(config: dict[str, Any]) -> None:
    if config.get("execution_contract") != {
        "exact_input_counts_and_split_disjointness": "implemented",
        "exact_dispatched_grid_schema_and_row_mapping": "implemented",
        "dispatched_grid_solver_certificate_replay": "implemented",
        "dispatched_grid_finite_and_no_event_semantic_contract_equivalence": (
            "implemented"
        ),
        "dispatched_grid_E0_semantic_contract_equivalence": "implemented",
        "dispatched_grid_checkpoint_exact_inventory_and_digest_replay": "implemented",
        "dispatched_grid_checkpoint_full_outcome_to_CSV_replay": "implemented",
        "dispatched_grid_baseline_certificate_replay": "implemented",
        "dispatched_grid_summary_normal_scuc_scale_reconstruction": "implemented",
        "dispatched_grid_checkpoint_typed_exact_CSV_projection": "implemented",
        "strict_external_JSON_duplicate_key_rejection": "implemented",
        "strict_external_JSON_nonfinite_rejection": (
            "implemented_including_exponent_overflow"
        ),
        "strict_CSV_header_and_row_width_rejection": "implemented",
        "sealed_and_draft_validation_paths_nonvacuous": "implemented",
        "review_authority_transition_tests_hermetic": "implemented",
        "live_repository_review_receipt_state_assumption": "prohibited",
        "recursive_input_manifest_validation": "implemented",
        "recursively_verified_sealed_authority": "implemented",
        "write_capable_public_stage_surface": (
            "closed_pending_fresh_process_activation_successor"
        ),
        "fresh_process_runtime_bootstrap": "deferred_to_activation_successor",
        "internally_derived_static_authority": "implemented",
        "public_stage_execution_outer_from_fixed_review_receipt": (
            "private_helper_implemented_public_surface_closed"
        ),
        "public_stage_rejects_caller_authority_digests": "implemented",
        "public_stage_rejects_caller_repository_root": "implemented",
        "public_stage_grid_manifest_loaded_from_sealed_registration": (
            "private_helper_implemented_public_surface_closed"
        ),
        "evidence_store_run_identity_from_bound_authorities": (
            "implemented_not_executed"
        ),
        "evidence_store_root_from_activation_authority": ("implemented_not_executed"),
        "public_stage_design_loaded_from_sealed_v5": (
            "private_helper_implemented_public_surface_closed"
        ),
        "public_stage_recursively_revalidates_upstream_authorities": (
            "private_helper_implemented_public_surface_closed"
        ),
        "native_solver_primal_capture": "implemented_not_executed",
        "nonoptimal_feasible_incumbent_capture": "implemented_not_executed",
        "independent_primal_replay": "implemented_synthetic_only",
        "native_solver_log_binding": "implemented_not_executed",
        "private_planning_orchestration": "implemented_not_executed",
        "planning_evidence_output_index": "implemented_not_executed",
        "planning_capacity_frontier_content_addressing": "implemented",
        "downstream_planning_solve_primal_replay_closure": "implemented",
        "planning_actual_input_fresh_model_primal_replay": ("implemented_not_executed"),
        "planning_authority_gate_precedes_solver": "implemented_not_executed",
        "planning_exact_empty_prestate_and_verified_poststate": (
            "implemented_not_executed"
        ),
        "fallback_invocation_input_replay_and_planning_hash_binding": (
            "implemented_not_executed"
        ),
        "registered_training_content_hash_binding": "implemented",
        "registered_input_audit_cross_stage_content_addressing": "implemented",
        "public_stage_inputs_reaudited_from_sealed_execution_authority": (
            "private_helper_implemented_public_surface_closed"
        ),
        "public_native_solver_adapter_injection": "rejected",
        "public_bootstrap_endpoint_solver_injection": "rejected",
        "stable_parse_of_hashed_authority_bytes": "implemented",
        "stable_snapshot_of_registered_input_package_bytes": "implemented",
        "stage_aware_evidence_inventory_pre_and_post": "implemented",
        "planning_index_required_before_holdout_or_bootstrap": "implemented",
        "content_addressed_holdout_chunks": "implemented",
        "content_addressed_holdout_summary": "implemented",
        "registered_holdout_dimension_gate": "implemented",
        "registered_holdout_content_hash_binding": "implemented",
        "holdout_summary_live_input_full_reconstruction": "implemented",
        "holdout_resume_full_prevalidation_before_write": "implemented",
        "holdout_metrics_independent_trajectory_recomputation": "implemented",
        "holdout_policy_and_metrics_replay_from_chunks": (
            "implemented_full_policy_reexecution"
        ),
        "resumable_bootstrap_cell_checkpoints": "implemented",
        "bootstrap_draw_stream_binding": (
            "internally_generated_from_sealed_v5_contract"
        ),
        "bootstrap_exact_audited_support_and_empty_finite_gate": "implemented",
        "bootstrap_metric_matrix_content_addressing": "implemented",
        "bootstrap_metric_matrix_rederived_before_resume_or_aggregation": "implemented",
        "bootstrap_non_evaluable_cell_propagation": "implemented",
        "bootstrap_all_E0_aggregate_propagation": "implemented",
        "bootstrap_resume_prevalidation_before_write": "implemented",
        "bootstrap_endpoint_iteration_order": ("replicate_cell_metric_lower_upper"),
        "bootstrap_checkpoint_global_endpoint_ordinal_binding": "implemented",
        "bootstrap_checkpoint_cross_stage_authority_binding": "implemented",
        "bootstrap_primal_dual_certificate_persistence": "implemented",
        "bootstrap_certificate_algebraic_replay": (
            "implemented_at_resume_and_CI_aggregation"
        ),
        "immutable_idempotent_checkpoint_writes": "implemented",
        "checkpoint_identity_and_drift_rejection": (
            "implemented_with_pointer_object_blob_closure"
        ),
        "bounded_working_set_design": (
            "includes_single_cell_metric_matrix_single_cell_bootstrap_samples_"
            "and_aggregate_interval_output"
        ),
        "synthetic_memory_profile": "implemented",
        "registered_dimension_memory_profile": "pending_execution_machine",
        "measured_transport_runtime_projection": "pending_execution_machine",
        "execution_machine_runtime_receipt": "pending_execution_machine",
        "formal_activation_wrapper": "not_present",
    }:
        raise ValueError("execution capability contract drifted")
    if config.get("persistence") != {
        "object_hash": "sha256",
        "canonical_json": "UTF8_sorted_keys_compact_newline",
        "trajectory_chunk_key": "cell_id_power_block_id",
        "trajectory_chunk_contains_all_workload_ids_and_four_arms": True,
        "holdout_summary_key": "registered",
        "bootstrap_checkpoint_key": "replicate_cell_id",
        "bootstrap_checkpoint_schema": ("rq2_joint_deliverability_bootstrap_cell_v2"),
        "bootstrap_checkpoint_contains_all_registered_metrics": True,
        "bootstrap_checkpoint_binds_metric_matrix_object": True,
        "bootstrap_checkpoint_binds_global_endpoint_invocation_range": True,
        "bootstrap_endpoint_iteration_order": ("replicate_cell_metric_lower_upper"),
        "metric_matrix_object_key": "cell_id",
        "metric_matrix_binds_holdout_chunk_stream": True,
        "atomic_replace_with_parent_fsync": True,
        "existing_identical_object_is_idempotent": True,
        "existing_different_pointer_is_rejected": True,
        "orphan_object_or_blob_allowed": ("inert_content_addressed_unreferenced_only"),
        "native_solve_record_key": "planning_input_sha256",
        "native_solve_invocation_order_required": True,
        "planning_output_index_required": True,
        "capacity_frontier_object_key": "registered",
        "planning_index_binds_capacity_frontier_object": True,
        "registered_input_audit_key": "registered",
        "planning_and_holdout_reference_same_input_audit_object": True,
        "dispatched_grid_checkpoint_working_set": "one_block",
        "durable_ancestor_directory_creation": True,
        "alias_rejected_before_directory_creation": True,
        "empty_or_unregistered_directory_allowed": False,
        "symlink_or_reparse_component_allowed": False,
    }:
        raise ValueError("execution persistence contract drifted")
    if config.get("formal_scale") != {
        "registered_cells": 46,
        "dispatched_grid_checkpoint_files": 1071,
        "power_training_blocks": 541,
        "power_holdout_blocks": 530,
        "workload_training_blocks": 34,
        "workload_holdout_blocks": 34,
        "holdout_trajectory_chunks_if_all_cells_resolved": 24380,
        "maximum_holdout_policy_executions": 3315680,
        "maximum_hourly_state_transitions": 79576320,
        "bootstrap_replicate_cell_checkpoints": 9200,
        "bootstrap_transport_endpoint_solves": 423200,
    }:
        raise ValueError("execution formal scale drifted")
    if config.get("validation_contract") != {
        "focused_test_command": (
            "python -m pytest -q tests/test_rq2_joint_deliverability_execution_v3.py"
        ),
        "solver_calls": 0,
        "formal_result_writes": 0,
        "adversarial_cases": [
            "input_manifest_member_drift",
            "cross_split_block_id_overlap",
            "cross_split_source_hour_overlap",
            "missing_dispatched_grid_package",
            "unbound_dispatched_grid_manifest",
            "unreachable_dispatched_grid_producer_config",
            "dispatched_grid_schema_or_row_mapping_drift",
            "dispatched_grid_solver_certificate_field_drift",
            "dispatched_grid_partial_bound_certificate",
            "dispatched_grid_E0_nonnull_bound",
            "dispatched_grid_E0_solver_status_mapping_drift",
            "dispatched_grid_E0_model_scale_mismatch",
            "dispatched_grid_checkpoint_file_missing_or_extra",
            "dispatched_grid_checkpoint_digest_drift",
            "dispatched_grid_checkpoint_row_projection_drift",
            "dispatched_grid_E0_unprojected_outcome_field_drift",
            "dispatched_grid_baseline_objective_drift",
            "dispatched_grid_baseline_bound_or_gap_drift",
            "dispatched_grid_baseline_residual_or_integrality_drift",
            "dispatched_grid_baseline_solver_or_options_drift",
            "dispatched_grid_baseline_model_scale_drift",
            "dispatched_grid_baseline_incumbent_interval_serialization_boundary",
            "dispatched_grid_baseline_gap_limit_serialization_boundary",
            "dispatched_grid_no_event_baseline_schema_drift",
            "dispatched_grid_summary_normal_scuc_scale_drift",
            "external_JSON_duplicate_key",
            "external_JSON_exponent_overflow",
            "external_JSON_nonfinite_constant",
            "sealed_lifecycle_validation_contract",
            "draft_lifecycle_explicit_fixture",
            "opened_gate_targeted_rejection",
            "predecessor_authority_drift",
            "predecessor_escalate_and_superseded_pass_binding",
            "predecessor_fixed_pass_authority_reappears",
            "predecessor_fixed_pass_authority_dangling_symlink",
            "review_receipt_absent_then_present_same_test",
            "review_receipt_present_advances_to_grid_gate",
            "live_review_receipt_state_independence",
            "dispatched_grid_finite_boolean_string_drift",
            "dispatched_grid_checkpoint_string_to_number_drift",
            "dispatched_grid_checkpoint_sub_1e_12_numeric_drift",
            "dispatched_grid_finite_incumbent_interval_drift",
            "dispatched_grid_finite_relative_gap_limit_drift",
            "dispatched_grid_no_event_nonzero_certificate",
            "dispatched_grid_unregistered_globally_optimal_status",
            "dispatched_grid_CSV_extra_trailing_column",
            "dispatched_grid_CSV_zero_field_header",
            "dispatched_grid_CSV_empty_header",
            "dispatched_grid_CSV_duplicate_header",
            "dispatched_grid_CSV_missing_column",
            "dispatched_grid_negative_objective_certificate",
            "dispatched_grid_config_or_summary_drift",
            "dispatched_grid_stage_provenance_drift",
            "checkpoint_identity_drift",
            "checkpoint_payload_drift",
            "corrupted_content_addressed_object",
            "inert_content_addressed_orphan_adoption",
            "referenced_content_addressed_object_or_blob_missing",
            "forged_primal_objective",
            "infeasible_primal_assignment",
            "primal_arm_or_schema_swap",
            "primal_certificate_arm_missing_or_drift",
            "nonoptimal_feasible_incumbent_loss",
            "planning_hash_or_output_index_drift",
            "fallback_invocation_order_or_planning_hash_drift",
            "registered_training_content_hash_drift",
            "registered_input_audit_object_reference_drift",
            "caller_supplied_registered_input_audit_rejected",
            "caller_supplied_scientific_design_rejected",
            "caller_supplied_execution_outer_digest_rejected",
            "caller_supplied_grid_manifest_digest_rejected",
            "caller_supplied_repository_root_rejected",
            "cached_implementation_module_public_stage_closed",
            "evidence_store_run_identity_drift",
            "evidence_store_root_drift",
            "fixed_execution_review_receipt_missing_or_drifted",
            "recursive_upstream_authority_member_drift",
            "missing_or_drifted_planning_index_authority",
            "forged_zero_record_planning_index",
            "self_signed_planning_primal_or_replay",
            "downstream_planning_full_reference_replay_drift",
            "private_planning_orchestration_order_drift",
            "planning_solver_before_authority_gate",
            "planning_same_stage_extra_checkpoint_before_solver",
            "public_synthetic_solver_driver_rejected",
            "public_bootstrap_endpoint_solver_rejected",
            "authority_verify_parse_TOCTOU",
            "registered_holdout_dimension_drift",
            "registered_holdout_content_hash_drift",
            "holdout_raw_request_replay_drift",
            "holdout_later_checkpoint_prevalidated_before_write",
            "holdout_metric_independent_trajectory_replay",
            "self_signed_holdout_summary_or_chunk_closure",
            "caller_supplied_bootstrap_draw_rejected",
            "caller_supplied_bootstrap_metric_loader_rejected",
            "preseeded_bootstrap_metric_matrix_rejected",
            "bootstrap_metric_matrix_blob_or_hash_drift",
            "bootstrap_empty_finite_support_unresolved",
            "bootstrap_non_evaluable_cell_propagation",
            "bootstrap_all_E0_aggregate_propagation",
            "bootstrap_all_E0_mixed_status_propagation",
            "bootstrap_invalid_existing_checkpoint_before_write",
            "bootstrap_all_E0_existing_matrix_or_checkpoint",
            "bootstrap_mixed_empty_replicate_existing_matrix_or_checkpoint",
            "bootstrap_extra_checkpoint_before_write",
            "bootstrap_transport_solver_status_drift",
            "bootstrap_checkpoint_cross_stage_authority_drift",
            "bootstrap_resume_order_drift",
            "bootstrap_replicate_major_endpoint_order",
            "bootstrap_endpoint_invocation_ordinal_drift",
            "bootstrap_metric_matrix_drift",
            "bootstrap_aggregate_endpoint_forgery",
            "native_solver_version_drift",
            "parent_fsync_commit_indeterminate",
            "ancestor_directory_fsync_omission",
            "mkdir_file_exists_race_fsync_omission",
            "internal_alias_external_write",
            "unregistered_empty_evidence_directory",
            "evidence_stage_inventory_drift",
            "stage_lock_rejected_before_holdout_or_bootstrap_effects",
            "bootstrap_single_cell_sample_working_set",
            "windows_native_directory_flush_execution_machine_probe",
            "fresh_process_local_import_closure",
            "symlink_or_reparse_path",
        ],
    }:
        raise ValueError("execution validation contract drifted")


def _validate_manifest(require_sealed: bool) -> None:
    if not require_sealed:
        return
    _regular(INNER, INNER_RELATIVE)
    inner = _load_json(INNER)
    if (
        set(inner) != {"schema", "version", "files"}
        or inner.get("schema") != "rq2_joint_deliverability_execution_inner_v3"
        or inner.get("version") != 3
        or set(inner.get("files", {})) != EXPECTED_MEMBERS
    ):
        raise ValueError("execution inner manifest drifted")
    for relative, expected in inner["files"].items():
        path = ROOT / relative
        _regular(path, relative)
        if _sha256(path) != expected:
            raise ValueError(f"execution sealed member drifted: {relative}")
    _regular(OUTER, OUTER_RELATIVE)
    outer = _load_json(OUTER)
    if outer != {
        "schema": "rq2_joint_deliverability_execution_outer_v3",
        "version": 3,
        "inner": {
            "path": INNER_RELATIVE,
            "sha256": _sha256(INNER),
        },
    }:
        raise ValueError("execution outer manifest drifted")


def validate(
    config: dict[str, Any],
    *,
    require_sealed: bool = False,
) -> dict[str, object]:
    if set(config) != {
        "schema",
        "version",
        "created_on",
        "lifecycle",
        "scope",
        "authority",
        "predecessor_authority",
        "execution_review_authority",
        "execution_runtime_authority",
        "execution_activation_authority",
        "registered_inputs",
        "implementation",
        "execution_contract",
        "persistence",
        "formal_scale",
        "activation_requirements",
        "validation_contract",
        "gates",
    }:
        raise ValueError("execution successor top-level schema drifted")
    if (
        config["schema"] != "rq2_joint_deliverability_execution_successor_v3"
        or config["version"] != 3
        or config["created_on"] != "2026-09-05"
    ):
        raise ValueError("execution successor identity drifted")
    lifecycle = config.get("lifecycle")
    if not isinstance(lifecycle, dict):
        raise TypeError("execution lifecycle must be a mapping")
    if require_sealed:
        if lifecycle != {
            "status": "SEALED_READY_FOR_INDEPENDENT_REVIEW",
            "sealed_on": "2026-09-05",
            "pre_seal_audit_complete": True,
            "sealed_ready_for_independent_review": True,
        }:
            raise ValueError("execution sealed lifecycle drifted")
    else:
        if lifecycle not in (
            {
                "status": "DRAFT_NONAUTHORITATIVE",
                "pre_seal_audit_complete": False,
                "sealed_ready_for_independent_review": False,
            },
            {
                "status": "PRE_SEAL_AUDIT",
                "pre_seal_audit_complete": False,
                "sealed_ready_for_independent_review": False,
            },
        ):
            raise ValueError("execution draft lifecycle drifted")
    _validate_authorities(config)
    _validate_predecessor_authority(config)
    _validate_execution_review_authority(config)
    _validate_inputs(config)
    _validate_code_inventory(config)
    _validate_closed_effects(config)
    _validate_contracts(config)
    _validate_manifest(require_sealed)
    return {
        "schema": "rq2_joint_deliverability_execution_static_validation_v3",
        "valid": True,
        "lifecycle": lifecycle["status"],
        "solver_calls": 0,
        "formal_result_files_written": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-sealed", action="store_true")
    arguments = parser.parse_args()
    config = _load_yaml(ROOT / CONFIG_RELATIVE)
    print(
        json.dumps(
            validate(config, require_sealed=arguments.require_sealed),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
