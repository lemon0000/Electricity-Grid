"""Materialize the independently reviewed RQ2 grid solver recovery config."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from experiments.run_rts_gmlc_public_grid_need_dispatch_v4 import run as run_grid
from experiments.validate_rq2_public_grid_solver_recovery_v1 import CONTRACT, validate

ROOT = Path(__file__).resolve().parents[1]
REVIEW_RELATIVE = "configs/rq2_public_grid_solver_recovery_review_pass_v1.yaml"
REVIEW = ROOT / REVIEW_RELATIVE
ACTIVATED_ROOT = ROOT / "results/execution_configs/rq2_public_grid_highs_recovery_v1"
VALIDATOR_RELATIVE = "experiments/validate_rq2_public_grid_solver_recovery_v1.py"
ACTIVATOR_RELATIVE = "experiments/activate_rq2_public_grid_solver_recovery_v1.py"
TEST_RELATIVE = "tests/test_rq2_public_grid_solver_recovery_v1.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return dict(value)


def _load_yaml(path: Path, label: str) -> dict[str, Any]:
    return _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), label)


def _repo_path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw or raw.startswith(("/", "\\")):
        raise ValueError(f"{label} must be repository-relative")
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{label} must not escape repository")
    return ROOT / relative


def _require_hash(path: Path, expected: object, label: str) -> None:
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError(f"{label} must be a SHA-256 digest")
    if not path.is_file() or path.is_symlink() or _sha256(path) != expected:
        raise ValueError(f"{label} drifted")


def _expected_review_artifacts(contract: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    successor = _mapping(contract["successor"], "successor")
    predecessor = _mapping(contract["predecessor"], "predecessor")
    paths = {
        "recovery_preregistration": str(CONTRACT.relative_to(ROOT)).replace("\\", "/"),
        "successor_template": str(successor["template_path"]),
        "validator": VALIDATOR_RELATIVE,
        "activator": ACTIVATOR_RELATIVE,
        "test": TEST_RELATIVE,
        "formal_runner": str(predecessor["runner_path"]),
    }
    return {
        name: {"path": relative, "sha256": _sha256(_repo_path(relative, name))}
        for name, relative in paths.items()
    }


def _verify_review_receipt(contract: Mapping[str, Any]) -> dict[str, Any]:
    if not REVIEW.is_file() or REVIEW.is_symlink():
        raise ValueError("independent recovery review receipt is absent")
    receipt = _load_yaml(REVIEW, "independent recovery review receipt")
    if (
        receipt.get("schema") != "rq2_public_grid_solver_recovery_review_pass_v1"
        or receipt.get("reviewer_role") != "independent_sol_reviewer"
        or receipt.get("verdict") != "PASS"
    ):
        raise ValueError("independent recovery review is not PASS")
    reviewed = _mapping(receipt.get("reviewed_artifacts"), "reviewed artifacts")
    expected = _expected_review_artifacts(contract)
    if reviewed != expected:
        raise ValueError("independent recovery reviewed artifact set drifted")
    for name, item in reviewed.items():
        _require_hash(_repo_path(item["path"], name), item["sha256"], name)
    validation = _mapping(receipt.get("candidate_validation"), "candidate validation")
    if (
        validation.get("validation_passed") is not True
        or validation.get("formal_execution_ready") is not False
        or validation.get("predecessor_checkpoint_count") != 9
        or validation.get("accepted_blocks")
        != ["holdout_s20260822_0008", "holdout_s20260822_0009"]
    ):
        raise ValueError("independent recovery validation binding drifted")
    assertions = _mapping(receipt.get("assertions"), "review assertions")
    for key in (
        "gurobi_resource_pathology_supported",
        "checkpoint_logic_corruption_rejected",
        "resource_stop_not_reinterpreted_as_infeasibility",
        "highs_control_and_target_blocks_accepted",
        "model_input_and_scientific_parameters_preserved",
        "solver_identity_is_only_scientific_change",
        "tee_is_observability_only",
        "new_checkpoint_and_output_roots_required",
        "predecessor_checkpoint_reuse_disabled",
        "successor_starts_from_block_zero",
        "closed_template_and_activation_fail_closed",
    ):
        if assertions.get(key) is not True:
            raise ValueError(f"independent recovery assertion is not true: {key}")
    effect = _mapping(receipt.get("effect"), "review effect")
    if effect != {
        "opens_recovery_activation_only": True,
        "does_not_execute_solver": True,
        "does_not_reuse_predecessor_checkpoints": True,
        "does_not_assert_formal_result_or_security_claim": True,
    }:
        raise ValueError("independent recovery review effect drifted")
    return receipt


def _write_json_atomic(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def _write_yaml_atomic(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)
        temporary = Path(handle.name)
    temporary.replace(path)


def _verify_materialized(
    *,
    target: Path,
    template: Mapping[str, Any],
    authority: Mapping[str, Any],
    expected_block_count: int,
    runner_validation: Mapping[str, Any],
) -> None:
    activated = _load_yaml(target, "activated recovery config")
    for key in ("input", "grid_source", "model", "solver", "provenance", "output"):
        if activated.get(key) != template.get(key):
            raise ValueError(f"activated recovery {key} drifted")
    execution = _mapping(activated.get("execution"), "activated recovery execution")
    if (
        execution.get("formal_execution_ready") is not True
        or execution.get("independent_R4_review_passed") is not True
        or execution.get("user_formal_run_authorized") is not True
        or execution.get("require_all_blocks_resolved") is not True
        or execution.get("predecessor_Gurobi_checkpoint_reuse_allowed") is not False
        or execution.get("predecessor_HiGHS_checkpoint_reuse_allowed") is not False
    ):
        raise ValueError("activated recovery execution gate drifted")
    if activated.get("activation_authority") != authority:
        raise ValueError("activated recovery authority drifted")
    if (
        runner_validation.get("config_sha256") != _sha256(target)
        or runner_validation.get("formal_execution_ready") is not True
        or runner_validation.get("independent_R4_review_passed") is not True
        or runner_validation.get("user_formal_run_authorized") is not True
        or runner_validation.get("power_system_block_count") != expected_block_count
    ):
        raise ValueError("formal runner rejected activated recovery config")


def _cleanup_failed_activation(target: Path, record_target: Path) -> None:
    target.unlink(missing_ok=True)
    record_target.unlink(missing_ok=True)
    if ACTIVATED_ROOT.is_dir() and not any(ACTIVATED_ROOT.iterdir()):
        ACTIVATED_ROOT.rmdir()


def activate(contract_path: Path = CONTRACT) -> dict[str, object]:
    if contract_path.resolve() != CONTRACT.resolve():
        raise ValueError("only canonical solver recovery preregistration v1 is accepted")
    validation = validate()
    contract = _load_yaml(CONTRACT, "solver recovery preregistration")
    review = _verify_review_receipt(contract)
    successor = _mapping(contract["successor"], "successor")
    template_path = _repo_path(successor["template_path"], "successor template")
    template = _load_yaml(template_path, "successor template")
    checkpoint = _repo_path(successor["checkpoint_directory"], "checkpoint directory")
    output = _repo_path(successor["output_directory"], "output directory")
    target = _repo_path(successor["activated_config_path"], "activated config")
    record_target = _repo_path(successor["activation_record_path"], "activation record")
    if checkpoint.exists() or output.exists():
        raise FileExistsError("recovery checkpoint/output directory must not preexist")
    if target.parent != ACTIVATED_ROOT or record_target.parent != ACTIVATED_ROOT:
        raise ValueError("activated recovery targets escaped their canonical root")
    if ACTIVATED_ROOT.exists() or target.exists() or record_target.exists():
        raise FileExistsError("activated recovery root must not preexist")
    execution = _mapping(template["execution"], "template execution")
    if (
        execution.get("formal_execution_ready") is not False
        or execution.get("independent_R4_review_passed") is not False
    ):
        raise ValueError("recovery template was already activated")
    execution["formal_execution_ready"] = True
    execution["independent_R4_review_passed"] = True
    template["execution"] = execution
    authority = {
        "recovery_preregistration_path": str(CONTRACT.relative_to(ROOT)).replace("\\", "/"),
        "recovery_preregistration_sha256": _sha256(CONTRACT),
        "independent_review_path": REVIEW_RELATIVE,
        "independent_review_sha256": _sha256(REVIEW),
        "acceptance_result_manifest_sha256": contract[
            "successor_acceptance_evidence"
        ]["result_manifest_sha256"],
        "predecessor_activation_sha256": contract["predecessor"][
            "activation_sha256"
        ],
    }
    template["activation_authority"] = authority
    try:
        _write_yaml_atomic(target, template)
        runner_validation = run_grid(target, validate_only=True)
        _verify_materialized(
            target=target,
            template=_load_yaml(template_path, "successor template"),
            authority=authority,
            expected_block_count=int(successor["expected_block_count"]),
            runner_validation=runner_validation,
        )
        record: dict[str, object] = {
            "schema": "rq2_public_grid_solver_recovery_activation_v1",
            "stage": "grid_need_dispatch_v4",
            "recovery_preregistration_path": authority[
                "recovery_preregistration_path"
            ],
            "recovery_preregistration_sha256": authority[
                "recovery_preregistration_sha256"
            ],
            "independent_review_path": REVIEW_RELATIVE,
            "independent_review_sha256": authority["independent_review_sha256"],
            "review_verdict": review["verdict"],
            "activated_config_path": successor["activated_config_path"],
            "activated_config_sha256": _sha256(target),
            "activation_record_path": successor["activation_record_path"],
            "checkpoint_directory": successor["checkpoint_directory"],
            "output_directory": successor["output_directory"],
            "starts_from_block_zero": True,
            "predecessor_checkpoint_reuse_allowed": False,
            "formal_execution_ready": True,
            "formal_result_exists": False,
            "security_certified": False,
            "candidate_validation": validation,
            "runner_validate_only": dict(runner_validation),
        }
        _write_json_atomic(record_target, record)
        if json.loads(record_target.read_text(encoding="utf-8")) != record:
            raise ValueError("activation record changed after publication")
    except Exception:
        _cleanup_failed_activation(target, record_target)
        raise
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    args = parser.parse_args()
    print(json.dumps(activate(args.contract), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
