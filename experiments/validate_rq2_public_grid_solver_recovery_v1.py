"""Read-only validation for the RQ2 public-grid solver recovery candidate."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE = "configs/rq2_public_grid_solver_recovery_preregistration_v1.yaml"
CONTRACT = ROOT / CONTRACT_RELATIVE


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return dict(value)


def _load_yaml(path: Path, label: str) -> dict[str, Any]:
    return _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), label)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    return _mapping(json.loads(path.read_text(encoding="utf-8")), label)


def _repo_path(raw: object, label: str, *, root: Path = ROOT) -> Path:
    if not isinstance(raw, str) or not raw or raw.startswith(("/", "\\")):
        raise ValueError(f"{label} must be repository-relative")
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{label} must not escape repository")
    return root / relative


def _require_hash(path: Path, expected: object, label: str) -> None:
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError(f"{label} must be a SHA-256 digest")
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} is not an ordinary file")
    if _sha256(path) != expected:
        raise ValueError(f"{label} drifted")


def _require_bound_file(
    section: Mapping[str, Any], path_key: str, hash_key: str, label: str
) -> Path:
    path = _repo_path(section[path_key], f"{label} path")
    _require_hash(path, section[hash_key], label)
    return path


def _verify_manifest(result_root: Path, manifest_path: Path) -> dict[str, str]:
    manifest_raw = _load_json(manifest_path, "successor acceptance manifest")
    manifest: dict[str, str] = {}
    for relative, digest in manifest_raw.items():
        if not isinstance(relative, str) or not isinstance(digest, str):
            raise TypeError("successor acceptance manifest entry drifted")
        member = result_root / relative
        _require_hash(member, digest, f"successor acceptance member {relative}")
        manifest[relative] = digest
    if set(manifest) != {
        "holdout_s20260822_0008.worker.json",
        "holdout_s20260822_0009.worker.json",
        "summary.json",
    }:
        raise ValueError("successor acceptance member set drifted")
    return manifest


def _verify_acceptance_evidence(section: Mapping[str, Any]) -> dict[str, object]:
    result_root = _repo_path(section["result_directory"], "acceptance result directory")
    manifest_path = _require_bound_file(
        section, "result_manifest_path", "result_manifest_sha256", "acceptance manifest"
    )
    manifest = _verify_manifest(result_root, manifest_path)
    summary_path = _require_bound_file(
        section, "summary_path", "summary_sha256", "acceptance summary"
    )
    if manifest.get("summary.json") != section["summary_sha256"]:
        raise ValueError("acceptance summary is not bound by its manifest")
    _require_bound_file(
        section,
        "diagnostic_runner_path",
        "diagnostic_runner_sha256",
        "diagnostic runner",
    )
    summary = _load_json(summary_path, "acceptance summary")
    if summary.get("formal_artifacts_unchanged") is not True:
        raise ValueError("diagnostic changed formal artifacts")
    if summary.get("diagnostic_runner_sha256") != section["diagnostic_runner_sha256"]:
        raise ValueError("diagnostic runner summary binding drifted")
    solver = _mapping(summary.get("diagnostic_solver"), "diagnostic solver")
    expected_solver = {
        "name": "highs",
        "expected_package_version": "1.15.1",
        "threads": 4,
        "mip_relative_gap": 1e-6,
        "feasibility_tolerance": 1e-6,
        "optimality_tolerance": 1e-6,
        "integer_feasibility_tolerance": 1e-6,
        "random_seed": 0,
        "time_limit_seconds": 600.0,
        "tolerance_mw": 1e-6,
        "tee": True,
    }
    if solver != expected_solver:
        raise ValueError("diagnostic successor solver contract drifted")
    expected_blocks = list(section["accepted_blocks"])
    if summary.get("block_ids") != expected_blocks or len(expected_blocks) != 2:
        raise ValueError("accepted block set drifted")
    blocks = summary.get("blocks")
    if not isinstance(blocks, list) or len(blocks) != 2:
        raise ValueError("acceptance block records drifted")
    for block in blocks:
        record = _mapping(block, "acceptance block")
        block_id = record.get("block_id")
        if block_id not in expected_blocks or record.get("exit_code") != 0:
            raise ValueError("acceptance worker did not exit cleanly")
        worker = _mapping(record.get("worker"), f"acceptance worker {block_id}")
        audit = _mapping(worker.get("baseline_audit"), f"baseline audit {block_id}")
        solver_log = _mapping(record.get("solver_log"), f"solver log {block_id}")
        if (
            worker.get("accepted") is not True
            or worker.get("formal_checkpoint_written") is not False
            or worker.get("formal_output_written") is not False
            or audit.get("accepted") is not True
            or audit.get("solver_name") != "highs"
            or float(audit.get("relative_gap", 1.0)) > 1e-6
            or float(audit.get("maximum_constraint_violation", 1.0)) > 1e-6
            or float(audit.get("maximum_integrality_violation", 1.0)) > 1e-6
            or record.get("terminated_by_parent_watchdog") is not False
            or solver_log.get("time_limit_reached") is not False
            or solver_log.get("numerical_warning_reported") is not False
            or solver_log.get("out_of_memory_reported") is not False
        ):
            raise ValueError(f"successor acceptance failed for {block_id}")
        for path_key, hash_key, label in (
            ("worker_result_path", "worker_result_sha256", "worker result"),
            ("memory_log_path", "memory_log_sha256", "memory log"),
            ("native_log_path", "native_log_sha256", "native solver log"),
        ):
            _require_hash(
                _repo_path(record[path_key], f"{label} path"),
                record[hash_key],
                f"{label} {block_id}",
            )
    return {
        "accepted_blocks": expected_blocks,
        "target_block_accepted": section["target_block"] in expected_blocks,
    }


def _verify_predecessor(section: Mapping[str, Any]) -> dict[str, object]:
    for prefix, label in (
        ("preregistration", "predecessor preregistration"),
        ("activation", "predecessor activation"),
        ("activated_config", "predecessor activated config"),
        ("runner", "formal runner"),
    ):
        _require_bound_file(section, f"{prefix}_path", f"{prefix}_sha256", label)
    checkpoint_root = _repo_path(section["checkpoint_directory"], "predecessor checkpoint")
    expected = _mapping(section["checkpoint_sha256"], "predecessor checkpoint hashes")
    observed = {
        path.name: _sha256(path)
        for path in sorted(checkpoint_root.glob("*.json"))
        if path.is_file() and not path.is_symlink()
    }
    if observed != expected or len(observed) != section["completed_checkpoint_count"]:
        raise ValueError("predecessor checkpoint set drifted")
    if _repo_path(section["output_directory"], "predecessor output").exists():
        raise ValueError("predecessor output existence drifted")
    if section.get("output_exists") is not False or section.get("checkpoint_reuse_allowed") is not False:
        raise ValueError("predecessor fail-closed fields drifted")
    return {"checkpoint_count": len(observed), "output_exists": False}


def _verify_root_cause_evidence(section: Mapping[str, Any]) -> None:
    if section.get("classification") != (
        "gurobi_specific_branch_and_bound_tree_growth_with_virtual_memory_pressure"
    ):
        raise ValueError("root-cause classification drifted")
    if section.get("checkpoint_logic_corrupted") is not False:
        raise ValueError("checkpoint corruption was asserted")
    if section.get("mathematical_infeasibility_inferred") is not False:
        raise ValueError("resource stop was reinterpreted as infeasibility")
    for prefix, label in (
        ("default_gurobi_result_manifest", "default Gurobi manifest"),
        ("default_gurobi_summary", "default Gurobi summary"),
        ("bound_focus_result_manifest", "bound-focus manifest"),
        ("bound_focus_summary", "bound-focus summary"),
    ):
        _require_bound_file(section, f"{prefix}_path", f"{prefix}_sha256", label)


def _verify_successor_template(
    contract: Mapping[str, Any], predecessor: Mapping[str, Any], template: Mapping[str, Any]
) -> None:
    for key in ("input", "grid_source", "model", "provenance"):
        if template.get(key) != predecessor.get(key):
            raise ValueError(f"successor {key} drifted")
    old_solver = _mapping(predecessor.get("solver"), "predecessor solver")
    new_solver = _mapping(template.get("solver"), "successor solver")
    declared_unchanged = _mapping(
        contract["unchanged_solver_parameters"], "unchanged solver parameters"
    )
    for key, expected in declared_unchanged.items():
        if old_solver.get(key) != expected or new_solver.get(key) != expected:
            raise ValueError(f"successor solver parameter drifted: {key}")
    if old_solver.get("name") != "gurobi" or new_solver.get("name") != "highs":
        raise ValueError("successor solver identity drifted")
    if (
        old_solver.get("expected_package_version") != "13.0.2"
        or new_solver.get("expected_package_version") != "1.15.1"
    ):
        raise ValueError("successor solver version drifted")
    if old_solver.get("tee") is not False or new_solver.get("tee") is not True:
        raise ValueError("successor observability change drifted")
    allowed_solver_keys = set(declared_unchanged) | {
        "name",
        "expected_package_version",
        "tee",
    }
    if set(old_solver) != allowed_solver_keys or set(new_solver) != allowed_solver_keys:
        raise ValueError("successor solver field set drifted")
    old_output = _mapping(predecessor.get("output"), "predecessor output")
    new_output = _mapping(template.get("output"), "successor output")
    if old_output.get("schema") != new_output.get("schema"):
        raise ValueError("successor output schema drifted")
    if new_output.get("directory") != contract["output_directory"]:
        raise ValueError("successor output directory drifted")
    execution = _mapping(template.get("execution"), "successor execution")
    if (
        execution.get("formal_execution_ready") is not False
        or execution.get("independent_R4_review_passed") is not False
        or execution.get("user_formal_run_authorized") is not True
        or execution.get("require_all_blocks_resolved") is not True
        or execution.get("predecessor_Gurobi_checkpoint_reuse_allowed") is not False
        or execution.get("predecessor_HiGHS_checkpoint_reuse_allowed") is not False
        or execution.get("checkpoint_directory") != contract["checkpoint_directory"]
    ):
        raise ValueError("successor template execution gate drifted")
    old_execution = _mapping(predecessor.get("execution"), "predecessor execution")
    for key in ("forbidden_hostnames", "required_environment_value"):
        if execution.get(key) != old_execution.get(key):
            raise ValueError(f"successor host contract drifted: {key}")
    if "activation_authority" in template:
        raise ValueError("closed successor template already has activation authority")


def _verify_fresh_targets(section: Mapping[str, Any], *, root: Path = ROOT) -> None:
    if section.get("starts_from_block_zero") is not True:
        raise ValueError("successor is not registered to start at block zero")
    if (
        section.get("predecessor_gurobi_checkpoint_reuse_allowed") is not False
        or section.get("predecessor_highs_checkpoint_reuse_allowed") is not False
    ):
        raise ValueError("successor checkpoint reuse gate drifted")
    for key in (
        "checkpoint_directory",
        "output_directory",
        "activated_config_path",
        "activation_record_path",
    ):
        if _repo_path(section[key], f"successor {key}", root=root).exists():
            raise ValueError(f"successor target already exists: {key}")


def validate(config_path: Path = CONTRACT) -> dict[str, object]:
    if config_path.resolve() != CONTRACT.resolve():
        raise ValueError("only canonical solver recovery preregistration v1 is accepted")
    config = _load_yaml(CONTRACT, "solver recovery preregistration")
    if config.get("schema") != "rq2_public_grid_solver_recovery_preregistration_v1":
        raise ValueError("solver recovery schema drifted")
    if config.get("status") != "frozen_candidate_execution_closed":
        raise ValueError("solver recovery status drifted")
    execution = _mapping(config.get("execution"), "solver recovery execution")
    if (
        execution.get("candidate_validation_only") is not True
        or execution.get("formal_execution_ready") is not False
        or execution.get("independent_R4_review_passed") is not False
        or execution.get("user_formal_run_authorized") is not True
        or execution.get("require_all_blocks_resolved") is not True
    ):
        raise ValueError("solver recovery execution gate drifted")
    user = _mapping(config.get("user_authority"), "user authority")
    if (
        user.get("explicit_authorization_observed") is not True
        or user.get("authorized_scope")
        != "repair_grid_stage_then_continue_formal_rq2_pipeline"
    ):
        raise ValueError("solver recovery user authority drifted")
    predecessor_section = _mapping(config.get("predecessor"), "predecessor")
    predecessor_report = _verify_predecessor(predecessor_section)
    root_cause = _mapping(config.get("root_cause_evidence"), "root cause evidence")
    _verify_root_cause_evidence(root_cause)
    acceptance = _mapping(
        config.get("successor_acceptance_evidence"), "successor acceptance evidence"
    )
    acceptance_report = _verify_acceptance_evidence(acceptance)
    successor = _mapping(config.get("successor"), "successor")
    template_path = _repo_path(successor["template_path"], "successor template")
    _require_hash(template_path, successor["template_sha256"], "successor template")
    predecessor_path = _repo_path(
        predecessor_section["activated_config_path"], "predecessor activated config"
    )
    _verify_successor_template(
        successor,
        _load_yaml(predecessor_path, "predecessor activated config"),
        _load_yaml(template_path, "successor template"),
    )
    _verify_fresh_targets(successor)
    review = _mapping(config.get("review"), "review")
    if (
        review.get("independent_R4_review_required") is not True
        or review.get("verdict") != "pending"
    ):
        raise ValueError("solver recovery review gate drifted")
    claims = _mapping(config.get("claims"), "claims")
    if any(value is not False for value in claims.values()):
        raise ValueError("solver recovery claim gate drifted")
    return {
        "schema": "rq2_public_grid_solver_recovery_validation_v1",
        "config_sha256": _sha256(CONTRACT),
        "template_sha256": successor["template_sha256"],
        "predecessor_checkpoint_count": predecessor_report["checkpoint_count"],
        "accepted_blocks": acceptance_report["accepted_blocks"],
        "target_block_accepted": acceptance_report["target_block_accepted"],
        "starts_from_block_zero": True,
        "solver_calls": 0,
        "result_files_written": 0,
        "candidate_ready_for_independent_review": True,
        "formal_execution_ready": False,
        "validation_passed": True,
    }


def main() -> None:
    print(json.dumps(validate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
