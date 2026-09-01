"""Read-only validator for the process-isolated RQ2 grid recovery v2."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from experiments import (
    run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_v1 as runner,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/rq2_public_grid_solver_recovery_preregistration_v2.yaml"
MANIFEST = ROOT / "configs/rq2_public_grid_solver_recovery_v2.SHA256SUMS.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be an object")
    return dict(value)


def _load_yaml(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} must be an ordinary file")
    return _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), label)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} must be an ordinary file")
    return _mapping(json.loads(path.read_text(encoding="utf-8")), label)


def _repo_path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a repository-relative path")
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} escapes the repository")
    return ROOT / path


def _require_hash(path: Path, expected: object, label: str) -> None:
    if (
        not isinstance(expected, str)
        or len(expected) != 64
        or not path.is_file()
        or path.is_symlink()
        or _sha256(path) != expected
    ):
        raise ValueError(f"{label} drifted")


def _verify_artifacts(contract: Mapping[str, Any]) -> None:
    artifacts = _mapping(contract["artifacts"], "artifacts")
    manifest = _load_json(MANIFEST, "v2 artifact manifest")
    expected_manifest: dict[str, str] = {
        CONTRACT.relative_to(ROOT).as_posix(): _sha256(CONTRACT)
    }
    for name, raw in artifacts.items():
        item = _mapping(raw, f"artifact {name}")
        path = _repo_path(item["path"], f"artifact {name}")
        _require_hash(path, item["sha256"], f"artifact {name}")
        expected_manifest[str(item["path"])] = str(item["sha256"])
    if manifest != expected_manifest:
        raise ValueError("v2 artifact manifest drifted")


def _verify_evidence(contract: Mapping[str, Any]) -> None:
    for name, raw in _mapping(contract["evidence"], "evidence").items():
        item = _mapping(raw, f"evidence {name}")
        _require_hash(
            _repo_path(item["path"], f"evidence {name}"),
            item["sha256"],
            f"evidence {name}",
        )
    semantics = _mapping(contract["diagnostic_semantics"], "diagnostic semantics")
    if semantics != {
        "gurobi_default_900_seconds": "diagnostic_timeout_unresolved_not_infeasible",
        "gurobi_bound_focus_1800_seconds": "diagnostic_timeout_unresolved_not_infeasible",
        "highs_fresh_child_acceptance": "normal_baseline_acceptance_only",
        "formal_process_route_supported_by_highs_acceptance": False,
    }:
        raise ValueError("diagnostic semantics drifted")


def _verify_predecessor(contract: Mapping[str, Any]) -> None:
    predecessor = _mapping(contract["predecessor"], "predecessor")
    checkpoint_root = _repo_path(
        predecessor["checkpoint_directory"], "predecessor checkpoint root"
    )
    expected = _mapping(predecessor["checkpoint_sha256"], "checkpoint hashes")
    observed = {
        path.name: _sha256(path)
        for path in checkpoint_root.iterdir()
        if path.is_file() and not path.is_symlink()
    }
    if observed != expected or len(observed) != 9:
        raise ValueError("predecessor nine-checkpoint inventory drifted")
    output = _repo_path(predecessor["output_directory"], "predecessor output")
    if output.exists():
        raise ValueError("predecessor formal output unexpectedly exists")


def _verify_template(contract: Mapping[str, Any]) -> dict[str, object]:
    successor = _mapping(contract["successor"], "successor")
    template_path = _repo_path(successor["template_path"], "successor template")
    template = _load_yaml(template_path, "successor template")
    execution = _mapping(template["execution"], "template execution")
    process = _mapping(execution["process_isolation"], "process isolation")
    activation = _mapping(template["activation"], "activation")
    claims = _mapping(template["claims"], "claims")
    if (
        execution.get("formal_execution_ready") is not False
        or execution.get("independent_R4_review_passed") is not False
        or execution.get("user_formal_run_authorized") is not False
        or process.get("two_block_full_process_pilot_post_result_passed") is not False
        or process.get("named_outage_comparison_passed") is not False
        or activation != {
            "independent_R4_pass_receipt_path": None,
            "full_process_pilot_result_manifest_path": None,
            "full_process_pilot_post_result_pass_receipt_path": None,
            "activation_authority_path": None,
            "activation_allowed": False,
        }
        or any(value is not False for value in claims.values())
    ):
        raise ValueError("v2 execution, activation, or claim gate is open")
    for key in ("checkpoint_directory",):
        if _repo_path(execution[key], key).exists():
            raise ValueError(f"fresh successor target already exists: {key}")
    if _repo_path(template["output"]["directory"], "output").exists():
        raise ValueError("fresh successor output already exists")
    for key in ("worker_staging_directory", "attempt_log_directory"):
        if _repo_path(process[key], key).exists():
            raise ValueError(f"fresh successor target already exists: {key}")
    report = runner.run(template_path, validate_only=True)
    if (
        report.get("solver_calls") != 0
        or report.get("formal_writes") != 0
        or report.get("power_system_block_count") != 1071
        or report.get("formal_execution_ready") is not False
        or report.get("independent_R4_review_passed") is not False
        or report.get("two_block_full_process_pilot_post_result_passed") is not False
        or report.get("dispatch_authority")
        != {
            "canonical_config": True,
            "config_hash_bound": True,
            "formal_execution_ready": False,
            "preregistered_formal_execution_ready": False,
            "independent_R4_review_passed": False,
            "full_process_pilot_passed": False,
            "named_outage_comparison_passed": False,
            "activation_allowed": False,
            "activation_bindings_complete": False,
            "user_formal_run_authorized": False,
            "predecessor_reuse_forbidden": True,
        }
    ):
        raise ValueError("process-isolated validate-only report drifted")
    return report


def validate(contract_path: Path = CONTRACT) -> dict[str, object]:
    if contract_path.resolve() != CONTRACT.resolve():
        raise ValueError("only the canonical recovery v2 preregistration is accepted")
    contract = _load_yaml(CONTRACT, "recovery v2 preregistration")
    if (
        contract.get("schema") != "rq2_public_grid_solver_recovery_preregistration_v2"
        or contract.get("status") != "frozen_candidate_execution_closed"
    ):
        raise ValueError("recovery v2 preregistration is not closed")
    _verify_artifacts(contract)
    _verify_evidence(contract)
    _verify_predecessor(contract)
    runner_report = _verify_template(contract)
    return {
        "schema": "rq2_public_grid_solver_recovery_validation_v2",
        "validation_passed": True,
        "implementation_ready": False,
        "execution_ready": False,
        "formal_execution_ready": False,
        "independent_R4_review_passed": False,
        "full_process_pilot_completed": False,
        "post_result_review_passed": False,
        "predecessor_checkpoint_count": 9,
        "expected_successor_block_count": 1071,
        "solver_calls": 0,
        "result_files_written": 0,
        "formal_writes": 0,
        "formal_result_exists": False,
        "paper_claim": False,
        "security_certified": False,
        "runner_validate_only": runner_report,
    }


def main() -> None:
    print(json.dumps(validate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
