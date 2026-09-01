"""Canonical pure-read validator for the RQ2 confirmatory-pilot bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from experiments.validate_rq2_public_executor_environment_successor_v1 import (
    validate as validate_environment_successor,
)
from experiments.validate_rq2_public_solver_pilot_semantic_successor_v1 import (
    evaluate_runs,
)
from experiments.validate_rq2_public_solver_pilot_semantic_successor_v1 import (
    validate as validate_semantic_successor,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = "configs/rq2_public_solver_confirmatory_pilot_v1.yaml"
REVIEW_RELATIVE = "configs/rq2_public_solver_confirmatory_pilot_review_v1.yaml"
ACTIVATION_RELATIVE = (
    "configs/rq2_public_solver_confirmatory_pilot_activation_v1.yaml"
)
BUNDLE_RELATIVE = (
    "configs/rq2_public_solver_confirmatory_pilot_bundle_v1.SHA256SUMS.json"
)
OUTER_RELATIVE = (
    "configs/rq2_public_solver_confirmatory_pilot_bundle_v1.OUTER.SHA256SUMS.json"
)
CONFIG = ROOT / CONFIG_RELATIVE
BUNDLE = ROOT / BUNDLE_RELATIVE
OUTER = ROOT / OUTER_RELATIVE
CONFIG_SHA256 = "c78bd3b901fdf9ff8dc1cc66c9adda6156ed1f889d3cc37a5870021b38ac3975"
RESULT_RELATIVE = "results/tables/rq2_public_solver_confirmatory_pilot_v1"
RESULT_MEMBERS = {
    "config.yaml",
    "runs.json",
    "semantic_validation.json",
    "summary.json",
}
EXPECTED_RUNS = ["highs_r1", "gurobi_r1", "gurobi_r2", "highs_r2"]
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
V1_RUNS_SHA256 = "dfdcbcced9f5ba6362856643e44e5e0fdd979334e0165c701a0c9fe3cc80a153"
BUNDLE_INVENTORY = {
    CONFIG_RELATIVE,
    REVIEW_RELATIVE,
    ACTIVATION_RELATIVE,
    "experiments/run_rq2_public_solver_confirmatory_pilot_v1.py",
    "experiments/validate_rq2_public_solver_confirmatory_pilot_v1.py",
    "tests/test_rq2_public_solver_confirmatory_pilot_v1.py",
    *SEMANTIC_HASHES,
    "configs/rq2_public_solver_pilot_v1.yaml",
    "experiments/run_rq2_public_solver_pilot_v1.py",
    "data/processed/model_inputs/rts_gmlc_public_power_system_blocks_v4/SHA256SUMS.json",
    "configs/rq2_public_executor_handoff_v2.yaml",
    "configs/rq2_public_executor_bundle_v2.SHA256SUMS.json",
    "configs/rq2_public_executor_bundle_v2.OUTER.SHA256SUMS.json",
    "scripts/rq2_public_executor.py",
    "scripts/run_experiment.ps1",
    "configs/rq2_public_executor_environment_successor_v1.yaml",
    "configs/rq2_public_executor_environment_successor_v1.SHA256SUMS.json",
    "environments/rq2_executor_v2.yml",
    "experiments/validate_rq2_public_executor_environment_successor_v1.py",
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


def _safe_path(relative: object, label: str) -> str:
    if not isinstance(relative, str) or not relative:
        raise ValueError(f"{label} must be a nonempty repository-relative path")
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or str(path) != relative:
        raise ValueError(f"{label} is not a canonical repository-relative path")
    return relative


def _ordinary(relative: str, expected: str, label: str) -> Path:
    path = ROOT / _safe_path(relative, label)
    if (
        not path.is_file()
        or path.is_symlink()
        or not isinstance(expected, str)
        or len(expected) != 64
        or _sha256(path) != expected
    ):
        raise ValueError(f"{label} live bytes drifted: {relative}")
    return path


def _load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load {label}") from error


def _authority_hashes(config: Mapping[str, Any]) -> dict[str, str]:
    predecessor = _mapping(config["predecessor_authority"], "predecessor authority")
    v1 = _mapping(predecessor["v1_pilot"], "v1 authority")
    windows = _mapping(predecessor["windows_executor_v2"], "Windows authority")
    environment = _mapping(
        predecessor["fresh_environment_successor"], "environment authority"
    )
    semantic = _mapping(config["semantic_authority"], "semantic authority")
    return {
        semantic["config_path"]: semantic["config_sha256"],
        semantic["validator_path"]: semantic["validator_sha256"],
        semantic["tests_path"]: semantic["tests_sha256"],
        semantic["manifest_path"]: semantic["manifest_sha256"],
        config["review_receipt"]["path"]: config["review_receipt"]["sha256"],
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
        config["implementation"]["runner_path"]: config["implementation"][
            "runner_sha256"
        ],
    }


def _validate_review_and_activation(config: Mapping[str, Any]) -> None:
    review = _mapping(
        yaml.safe_load((ROOT / REVIEW_RELATIVE).read_text(encoding="utf-8")),
        "review receipt",
    )
    if (
        review.get("schema")
        != "rq2_public_solver_confirmatory_pilot_review_receipt_v1"
        or review.get("reviewed_on") != "2026-08-28"
        or review.get("reviewer_role") != "independent_sol_reviewer"
        or review.get("verdict") != "PASS"
    ):
        raise ValueError("semantic review receipt drifted")
    reviewed = _mapping(review.get("reviewed_artifacts"), "reviewed artifacts")
    observed = {
        item["path"]: item["sha256"]
        for item in reviewed.values()
        if isinstance(item, Mapping)
    }
    if observed != SEMANTIC_HASHES:
        raise ValueError("semantic review artifact binding drifted")
    effect = _mapping(review.get("effect"), "review effect")
    if (
        effect.get("semantic_successor_review_passed") is not True
        or effect.get("confirmatory_implementation_reviewed") is not False
        or any(
            effect.get(field) is not False
            for field in (
                "v1_eligibility_changed",
                "confirmatory_pilot_executed",
                "cross_solver_confirmation_completed",
                "formal_execution_ready",
                "formal_result_exists",
                "claim",
                "security_certified",
            )
        )
    ):
        raise ValueError("semantic review effect drifted")

    activation = _mapping(
        yaml.safe_load((ROOT / ACTIVATION_RELATIVE).read_text(encoding="utf-8")),
        "confirmatory activation",
    )
    if (
        activation.get("schema")
        != "rq2_public_solver_confirmatory_pilot_activation_v1"
        or activation.get("authorized_on") != "2026-08-28"
    ):
        raise ValueError("confirmatory activation identity drifted")
    user = _mapping(activation.get("user_authority"), "user authority")
    if user != {
        "explicit_authorization_observed": True,
        "authorization_record": "继续做/按路径全部做完",
        "authorized_scope": "fresh_rq2_cross_solver_confirmatory_pilot_v1_only",
        "external_watchdog_seconds": 21600,
    }:
        raise ValueError("confirmatory user authority drifted")
    semantic_review = _mapping(
        activation.get("semantic_review_authority"), "semantic review authority"
    )
    if semantic_review != {
        "receipt_path": REVIEW_RELATIVE,
        "receipt_sha256": config["review_receipt"]["sha256"],
        "verdict": "PASS",
    }:
        raise ValueError("activation semantic review authority drifted")
    permissions = _mapping(activation.get("permissions"), "activation permissions")
    if permissions != {
        "prepare_versioned_confirmatory_artifacts": True,
        "execute_confirmatory_pilot_after_independent_implementation_review": True,
        "execute_formal_grid": False,
        "execute_pairwise": False,
        "execute_identification": False,
        "make_formal_result_claim": False,
        "make_security_claim": False,
    }:
        raise ValueError("activation permission scope drifted")
    expected_closed = {
        "independent_confirmatory_implementation_review_passed": False,
        "confirmatory_pilot_executed": False,
        "cross_solver_confirmation_completed": False,
        "formal_execution_ready": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    if activation.get("gates") != expected_closed:
        raise ValueError("activation gates drifted")


def _validate_config(config: Mapping[str, Any]) -> None:
    if (
        config.get("schema") != "rq2_public_solver_confirmatory_pilot_config_v1"
        or config.get("version") != 1
        or config.get("frozen_on") != "2026-08-28"
        or config.get("status")
        != "pre_execution_implementation_ready_independent_review_pending"
    ):
        raise ValueError("confirmatory config identity drifted")
    if _mapping(config["semantic_authority"], "semantic authority") != {
        "review_verdict": "PASS",
        "config_path": (
            "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml"
        ),
        "config_sha256": SEMANTIC_HASHES[
            "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml"
        ],
        "validator_path": (
            "experiments/validate_rq2_public_solver_pilot_semantic_successor_v1.py"
        ),
        "validator_sha256": SEMANTIC_HASHES[
            "experiments/validate_rq2_public_solver_pilot_semantic_successor_v1.py"
        ],
        "tests_path": (
            "tests/test_rq2_public_solver_pilot_semantic_successor_v1.py"
        ),
        "tests_sha256": SEMANTIC_HASHES[
            "tests/test_rq2_public_solver_pilot_semantic_successor_v1.py"
        ],
        "manifest_path": (
            "configs/rq2_public_solver_pilot_semantic_successor_v1.SHA256SUMS.json"
        ),
        "manifest_sha256": SEMANTIC_HASHES[
            "configs/rq2_public_solver_pilot_semantic_successor_v1.SHA256SUMS.json"
        ],
        "evaluator_function": "evaluate_runs",
    }:
        raise ValueError("semantic authority drifted")
    v1 = _mapping(
        yaml.safe_load(
            (ROOT / "configs/rq2_public_solver_pilot_v1.yaml").read_text(
                encoding="utf-8"
            )
        ),
        "v1 pilot config",
    )
    for field in ("input", "model", "pilot_blocks", "solvers"):
        if config.get(field) != v1.get(field):
            raise ValueError(f"confirmatory {field} does not inherit v1 exactly")
    execution = _mapping(config.get("execution"), "execution")
    v1_execution = _mapping(v1.get("execution"), "v1 execution")
    if (
        execution.get("repetitions") != v1_execution.get("repetitions")
        or execution.get("execution_order") != v1_execution.get("execution_order")
        or execution.get("forbidden_hostnames")
        != v1_execution.get("forbidden_hostnames")
        or execution.get("required_environment_value")
        != v1_execution.get("required_environment_value")
        or execution.get("external_watchdog_seconds") != 21600
        or execution.get("timeout_is_infeasibility_evidence") is not False
        or execution.get("unresolved_is_infeasibility_evidence") is not False
        or execution.get("pilot_execution_authorized_by_user") is not True
        or execution.get("independent_implementation_review_required") is not True
    ):
        raise ValueError("confirmatory execution contract drifted")
    if any(
        solver.get("threads") != 4
        or solver.get("random_seed") != 0
        or solver.get("time_limit_seconds") is not None
        for solver in config["solvers"].values()
    ):
        raise ValueError("solver threads, seed, or unlimited solver time drifted")
    acceptance = _mapping(config.get("acceptance"), "acceptance")
    v1_acceptance = _mapping(v1.get("acceptance"), "v1 acceptance")
    inherited = {
        "require_all_baselines_accepted": True,
        "require_all_hours_resolved_for_pipeline": True,
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
    for field, expected in inherited.items():
        if acceptance.get(field) != expected:
            raise ValueError(f"confirmatory acceptance field drifted: {field}")
    if acceptance.get("require_identical_semantic_state_classification") is not True:
        raise ValueError("semantic state comparison gate drifted")
    output = _mapping(config.get("output"), "output")
    if output != {
        "schema": "rq2_public_solver_confirmatory_pilot_v1",
        "directory": RESULT_RELATIVE,
        "directory_must_not_preexist": True,
        "publication": "same_parent_staging_then_atomic_rename",
        "required_files": [
            "config.yaml",
            "runs.json",
            "semantic_validation.json",
            "summary.json",
            "SHA256SUMS.json",
        ],
        "exact_inventory_required": True,
        "v1_run_reuse_allowed": False,
    }:
        raise ValueError("confirmatory output contract drifted")
    gates = _mapping(config.get("gates"), "gates")
    if gates != {
        "semantic_successor_review_passed": True,
        "user_confirmatory_authorization_recorded": True,
        "confirmatory_implementation_ready": True,
        "independent_confirmatory_implementation_review_passed": False,
        "confirmatory_pilot_executed": False,
        "cross_solver_confirmation_completed": False,
        "formal_execution_ready": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }:
        raise ValueError("confirmatory pre-execution gates drifted")
    for relative, expected in _authority_hashes(config).items():
        _ordinary(relative, expected, "confirmatory authority")


def _validate_bundle() -> tuple[int, str]:
    bundle = _mapping(_load_json(BUNDLE, "confirmatory bundle"), "bundle")
    if bundle.get("schema") != "rq2_public_solver_confirmatory_bundle_manifest_v1":
        raise ValueError("confirmatory bundle schema drifted")
    files = _mapping(bundle.get("files"), "bundle files")
    if set(files) != BUNDLE_INVENTORY:
        raise ValueError("confirmatory bundle inventory drifted")
    for relative, expected in files.items():
        _ordinary(relative, expected, "confirmatory bundle member")
    bundle_sha = _sha256(BUNDLE)
    outer = _mapping(_load_json(OUTER, "confirmatory outer manifest"), "outer")
    if outer != {
        "schema": "rq2_public_solver_confirmatory_outer_manifest_v1",
        "files": {BUNDLE_RELATIVE: bundle_sha},
    }:
        raise ValueError("confirmatory outer manifest drifted")
    if not OUTER.is_file() or OUTER.is_symlink():
        raise ValueError("confirmatory outer manifest is not an ordinary file")
    return len(files), bundle_sha


def _validate_result(config: Mapping[str, Any]) -> dict[str, object]:
    result = ROOT / RESULT_RELATIVE
    if not result.exists():
        return {
            "result_present": False,
            "result_manifest_sha256": None,
            "confirmatory_pilot_executed": False,
            "cross_solver_confirmation_completed": False,
        }
    if not result.is_dir() or result.is_symlink():
        raise ValueError("confirmatory result path is not an ordinary directory")
    children = list(result.iterdir())
    expected_inventory = {*RESULT_MEMBERS, "SHA256SUMS.json"}
    if {item.name for item in children} != expected_inventory:
        raise ValueError("confirmatory result inventory drifted")
    if any(not item.is_file() or item.is_symlink() for item in children):
        raise ValueError("confirmatory result contains a non-ordinary member")
    manifest = _mapping(
        _load_json(result / "SHA256SUMS.json", "result manifest"),
        "result manifest",
    )
    if set(manifest) != RESULT_MEMBERS:
        raise ValueError("confirmatory result manifest inventory drifted")
    for name, expected in manifest.items():
        if _sha256(result / name) != expected:
            raise ValueError(f"confirmatory result member drifted: {name}")
    if _sha256(result / "config.yaml") != CONFIG_SHA256:
        raise ValueError("published confirmatory config drifted")
    if _sha256(result / "runs.json") == V1_RUNS_SHA256:
        raise ValueError("frozen v1 runs cannot satisfy fresh confirmation")
    runs = _list(_load_json(result / "runs.json", "confirmatory runs"), "runs")
    run_ids = [item.get("run_id") for item in runs if isinstance(item, Mapping)]
    if run_ids != EXPECTED_RUNS or len(run_ids) != len(set(run_ids)):
        raise ValueError("published confirmatory run inventory drifted")
    semantic_config = _mapping(
        yaml.safe_load(
            (ROOT / "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml")
            .read_text(encoding="utf-8")
        ),
        "semantic successor config",
    )
    recomputed = evaluate_runs(semantic_config, runs)
    semantic = _mapping(
        _load_json(result / "semantic_validation.json", "semantic validation"),
        "semantic validation",
    )
    pids = semantic.get("fresh_worker_pids")
    if (
        semantic.get("schema")
        != "rq2_public_solver_confirmatory_semantic_validation_v1"
        or semantic.get("semantic_successor_config_sha256")
        != SEMANTIC_HASHES[
            "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml"
        ]
        or semantic.get("evaluator_report") != recomputed
        or semantic.get("fresh_execution_run_ids") != EXPECTED_RUNS
        or not isinstance(pids, list)
        or len(pids) != 4
        or len(set(pids)) != 4
        or any(isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0 for pid in pids)
        or semantic.get("fresh_process_isolation_verified") is not True
        or semantic.get("semantic_contract_passed") is not True
        or semantic.get("cross_solver_confirmation_completed") is not True
        or semantic.get("formal_grid_execution_started") is not False
        or semantic.get("security_certified") is not False
    ):
        raise ValueError("published semantic validation drifted")
    summary = _mapping(_load_json(result / "summary.json", "summary"), "summary")
    if (
        summary.get("schema") != "rq2_public_solver_confirmatory_pilot_v1"
        or summary.get("config_sha256") != CONFIG_SHA256
        or summary.get("implementation_sha256")
        != config["implementation"]["runner_sha256"]
        or summary.get("fresh_execution_status") != "passed"
        or summary.get("fresh_execution_passed") is not True
        or summary.get("fresh_execution_failed") is not False
        or summary.get("run_count") != 4
        or summary.get("unique_worker_process_count") != 4
        or summary.get("semantic_contract_passed") is not True
        or summary.get("cross_solver_confirmation_completed") is not True
        or any(
            summary.get(field) is not False
            for field in (
                "formal_grid_execution_started",
                "formal_result_exists",
                "claim",
                "security_certified",
            )
        )
    ):
        raise ValueError("published confirmatory summary drifted")
    return {
        "result_present": True,
        "result_manifest_sha256": _sha256(result / "SHA256SUMS.json"),
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
        raise ValueError("only canonical confirmatory artifacts are accepted")
    if _sha256(CONFIG) != CONFIG_SHA256:
        raise ValueError("confirmatory config hash drifted")
    config = _mapping(
        yaml.safe_load(CONFIG.read_text(encoding="utf-8")), "confirmatory config"
    )
    _validate_config(config)
    _validate_review_and_activation(config)
    semantic_report = validate_semantic_successor()
    environment_report = validate_environment_successor(runtime=False)
    bundle_count, bundle_sha = _validate_bundle()
    result = _validate_result(config)
    return {
        "schema": "rq2_public_solver_confirmatory_preexecution_validation_v1",
        "config_sha256": CONFIG_SHA256,
        "bundle_manifest_sha256": bundle_sha,
        "outer_manifest_sha256": _sha256(OUTER),
        "bundle_member_count": bundle_count,
        "semantic_successor_review_verdict": "PASS",
        "semantic_successor_validation_passed": semantic_report["validation_passed"],
        "environment_successor_validation_passed": environment_report[
            "validation_passed"
        ],
        "implementation_ready": True,
        "independent_confirmatory_implementation_review_passed": False,
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
    print(
        json.dumps(
            validate(args.config, args.bundle, args.outer),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
