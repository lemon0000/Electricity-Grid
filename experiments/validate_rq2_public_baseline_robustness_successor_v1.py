"""Pure-read validation of the public RQ2 baseline package successor contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = "configs/rq2_public_baseline_robustness_successor_v1.yaml"
MANIFEST_RELATIVE = (
    "configs/rq2_public_baseline_robustness_successor_v1.SHA256SUMS.json"
)
CONFIG = ROOT / CONFIG_RELATIVE
MANIFEST = ROOT / MANIFEST_RELATIVE
EXPECTED_ARMS = [
    "network_only_shared",
    "cfe_only_shared",
    "joint_correct_shared",
    "joint_b6_separate_planning_shared_execution",
]
EXPECTED_SCHEMAS = [
    "four_arm_training_status",
    "four_arm_minimum_flexibility",
    "four_arm_pairwise_outcomes",
    "E0_outcomes",
    "checkpoint_inventory",
    "provenance",
]
FALSE_GATES = {
    "implementation_bound",
    "complete_external_orchestration",
    "ready",
    "independent_review",
    "independent_R3_review_passed",
    "independent_R4_review_passed",
    "user_authorized",
    "formal_result",
    "claim",
}
EXPECTED_PREDECESSOR_AUTHORITIES = {
    "preregistration": {
        "path": "configs/rq2_public_baseline_robustness_preregistration_v1.yaml",
        "sha256": "017708b25c3e1702c938a108af070a7047517bd128552500d3ffcac6a3ee3554",
    },
    "manifest": {
        "path": (
            "configs/rq2_public_baseline_robustness_preregistration_v1."
            "SHA256SUMS.json"
        ),
        "sha256": "da6d13055ccfcd03c00939ab7fa61f43e05052556211f725b4550a09d33f64c9",
    },
}
EXPECTED_IMPLEMENTATION_AUTHORITIES = {
    "planning_core": {
        "path": "src/models/rq2_baseline_robustness.py",
        "sha256": "14e935043d5bbc8116fef88c592d3c5eb6e949395e318248cbf2d97eae7ec1b5",
    },
    "replay_core": {
        "path": "src/scenarios/rq2_baseline_robustness.py",
        "sha256": "adc970ecb4f070f0079131988682d87b7f8e42a75b370116158413e099ca2331",
    },
    "package_core": {
        "path": "src/evaluation/rq2_baseline_robustness_package_v1.py",
        "sha256": "9075751220797c86270cc5877584d2aeb5ea128afe16a54befeb7831e7033e5f",
    },
}
EXPECTED_FROZEN_AUTHORITIES = {
    "v6_preregistration": {
        "path": "configs/rq2_public_data_robust_identification_preregistration_v6.yaml",
        "sha256": "ef25deabfcd51fbd667e48dcddcfbe4b19a2115c6d4bc40b0fc556b5c1f332f2",
    },
    "v6_manifest": {
        "path": (
            "configs/rq2_public_data_robust_identification_preregistration_v6."
            "SHA256SUMS.json"
        ),
        "sha256": "07bb735df3cc5ad547c7d4741c5f69929b39a37df9b65c3c2ae004e74b08cdcf",
    },
    "pairwise_v4": {
        "path": "configs/rq2_public_pairwise_replay_v4.yaml",
        "sha256": "4e4ea40e71742198ff9b70d527d6bae91df486c87b3a540bbbb23f6ba4f72cf3",
    },
    "identification_v4": {
        "path": "configs/rq2_public_identification_grid_v4.yaml",
        "sha256": "1081ed0e52201323e3df7c1a5c39d0409fdcef8c2cc29c49edcd207c93ed3308",
    },
}
EXPECTED_VALIDATION_PATHS = {
    "validator_path": (
        "experiments/validate_rq2_public_baseline_robustness_successor_v1.py"
    ),
    "test_path": "tests/test_rq2_public_baseline_robustness_successor_v1.py",
    "manifest_path": MANIFEST_RELATIVE,
}
EXPECTED_MANIFEST_PATHS = {
    CONFIG_RELATIVE,
    *(item["path"] for item in EXPECTED_PREDECESSOR_AUTHORITIES.values()),
    *(item["path"] for item in EXPECTED_IMPLEMENTATION_AUTHORITIES.values()),
    *(item["path"] for item in EXPECTED_FROZEN_AUTHORITIES.values()),
    EXPECTED_VALIDATION_PATHS["validator_path"],
    EXPECTED_VALIDATION_PATHS["test_path"],
}


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return dict(value)


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        return _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), str(path))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        raise ValueError(f"cannot load YAML: {path}") from error


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")), str(path))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load JSON: {path}") from error


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _equal(observed: object, expected: object, label: str) -> None:
    if observed != expected:
        raise ValueError(f"{label} drifted: {observed!r} != {expected!r}")


def _safe(relative: object, label: str) -> str:
    if not isinstance(relative, str):
        raise ValueError(f"{label} must be a repository-relative path")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or str(pure) != relative:
        raise ValueError(f"unsafe or noncanonical {label}: {relative}")
    return relative


def _authority(item: object, label: str) -> tuple[str, str]:
    authority = _mapping(item, label)
    _equal(set(authority), {"path", "sha256"}, f"{label} inventory")
    relative = _safe(authority["path"], f"{label} path")
    digest = authority["sha256"]
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError(f"{label} digest must be SHA-256")
    _equal(_sha256(ROOT / relative), digest, f"{label} live hash")
    return relative, digest


def _validate_authority_section(
    observed: object,
    expected: Mapping[str, Mapping[str, str]],
    label: str,
) -> None:
    section = _mapping(observed, label)
    _equal(section, dict(expected), f"{label} exact authority inventory")
    for name, item in expected.items():
        _authority(item, f"{label}.{name}")


def _validate_predecessor(config: dict[str, Any]) -> dict[str, Any]:
    predecessor = _mapping(config.get("predecessor"), "predecessor")
    _equal(
        set(predecessor),
        {"preregistration", "manifest", "future_bindings_remain_null"},
        "predecessor section inventory",
    )
    for name, expected in EXPECTED_PREDECESSOR_AUTHORITIES.items():
        _equal(predecessor.get(name), expected, f"predecessor {name} binding")
    prereg_path, _ = _authority(
        predecessor.get("preregistration"), "predecessor preregistration"
    )
    _authority(predecessor.get("manifest"), "predecessor manifest")
    preregistration = _load_yaml(ROOT / prereg_path)
    _equal(
        preregistration.get("schema"),
        "rq2_public_baseline_robustness_preregistration_v1",
        "predecessor schema",
    )
    _equal(
        preregistration.get("status"),
        "design_only_not_executable",
        "predecessor status",
    )
    future = _mapping(
        predecessor.get("future_bindings_remain_null"), "future null bindings"
    )
    expected_stage = _mapping(
        future.get("four_arm_planning_pairwise_package"), "future planning stage"
    )
    observed_stage = _mapping(
        _mapping(
            _mapping(preregistration.get("result_chain"), "result_chain").get(
                "stages"
            ),
            "result stages",
        ).get("four_arm_planning_pairwise_package"),
        "predecessor planning stage",
    )
    for key in ("implementation_path", "config_path", "runner_path", "output_path"):
        _equal(expected_stage.get(key), None, f"successor predecessor {key}")
        _equal(observed_stage.get(key), None, f"predecessor planning {key}")
    _equal(expected_stage.get("ready"), False, "successor predecessor ready")
    _equal(observed_stage.get("ready"), False, "predecessor planning ready")
    expected_t1 = _mapping(
        future.get("t1_mw_only_reference"), "future T1 binding"
    )
    observed_t1 = _mapping(
        _mapping(
            preregistration.get("coupling_contract"), "coupling contract"
        ).get("t1_mw_only_reference"),
        "predecessor T1 binding",
    )
    for key, expected in (
        ("future_implementation_path", None),
        ("implementation_bound", False),
    ):
        _equal(expected_t1.get(key), expected, f"successor predecessor T1 {key}")
        _equal(observed_t1.get(key), expected, f"predecessor T1 {key}")
    predecessor_gates = _mapping(
        preregistration.get("execution_gates"), "predecessor execution gates"
    )
    if any(value is not False for value in predecessor_gates.values()):
        raise ValueError("predecessor execution gate opened")
    return preregistration


def _validate_design_snapshot(
    config: dict[str, Any], preregistration: dict[str, Any]
) -> None:
    snapshot = _mapping(
        config.get("frozen_design_snapshot"), "frozen design snapshot"
    )
    inherited = _mapping(
        preregistration.get("same_design_inheritance"), "same-design inheritance"
    )
    _equal(snapshot.get("parameter_cell_count"), 15, "parameter cell count")
    _equal(
        snapshot.get("parameter_cell_count"),
        inherited.get("parameter_cell_count"),
        "inherited parameter cell count",
    )
    _equal(snapshot.get("block_hours"), inherited.get("block_hours"), "block hours")
    _equal(
        snapshot.get("block_splits"),
        inherited.get("block_splits"),
        "training/holdout splits",
    )
    representatives = _mapping(
        snapshot.get("representative_selection"), "representative selection"
    )
    inherited_representatives = _mapping(
        inherited.get("representative_selection"),
        "inherited representative selection",
    )
    for key in (
        "method",
        "power_system_representatives",
        "workload_representatives",
        "selection_uses_holdout_outcomes",
        "full_evaluable_training_support_audit",
    ):
        _equal(
            representatives.get(key),
            inherited_representatives.get(key),
            f"representative {key}",
        )
    _equal(snapshot.get("solver"), inherited.get("solver"), "solver contract")
    _equal(snapshot.get("arm_canonical_order"), EXPECTED_ARMS, "arm order")
    _equal(
        [arm.get("id") for arm in preregistration.get("arms", [])],
        EXPECTED_ARMS,
        "predecessor arm order",
    )
    identification = _load_yaml(
        ROOT / EXPECTED_FROZEN_AUTHORITIES["identification_v4"]["path"]
    )
    classification = _mapping(
        identification.get("classification"), "identification classification"
    )
    _equal(
        classification.get("probability_tolerance"),
        1.0e-9,
        "identification probability tolerance",
    )


def _validate_contract(config: dict[str, Any]) -> None:
    _equal(
        config.get("schema"),
        "rq2_public_baseline_robustness_successor_v1",
        "successor schema",
    )
    _equal(
        config.get("status"),
        "public_checkpoint_contract_validate_only_not_executable",
        "successor status",
    )
    scope = _mapping(config.get("scope"), "scope")
    for key in (
        "loads_external_data",
        "complete_external_orchestration",
        "runs_solver",
        "runs_identification",
        "writes_report",
        "amends_predecessor_preregistration",
    ):
        _equal(scope.get(key), False, f"scope {key}")
    checkpoint = _mapping(config.get("checkpoint_contract"), "checkpoint contract")
    planning = _mapping(checkpoint.get("planning"), "planning contract")
    _equal(planning.get("exact_four_arm_inventory"), True, "planning inventory")
    _equal(
        planning.get("timeout_or_unknown_is_proven_infeasible"),
        False,
        "timeout semantics",
    )
    _equal(
        planning.get("proven_infeasible_estimand_defined"),
        False,
        "infeasible estimand semantics",
    )
    pair = _mapping(checkpoint.get("pair"), "pair contract")
    for key in (
        "finite_requires_all_four_raw_and_registered_outcomes",
        "E0_preserves_unconditional_probability_mass",
        "unresolved_or_missing_blocks_publication",
    ):
        _equal(pair.get(key), True, f"pair {key}")
    _equal(pair.get("E0_has_conditional_service_metrics"), False, "E0 metrics")
    _equal(
        pair.get("probability_tolerance"),
        1.0e-9,
        "frozen probability tolerance",
    )
    _equal(
        pair.get("checkpoint_probability_matches_expected_exactly"),
        True,
        "checkpoint probability binding",
    )
    _equal(
        pair.get("all_cells_share_complete_cartesian_inventory"),
        True,
        "Cartesian pair binding",
    )
    _equal(
        planning.get("full_training_cartesian_pair_ids_and_hash"),
        True,
        "training Cartesian binding",
    )
    package = _mapping(config.get("package_contract"), "package contract")
    _equal(package.get("required_schemas"), EXPECTED_SCHEMAS, "package schemas")
    _equal(package.get("exact_recursive_inventory_required"), True, "inventory")
    gates = _mapping(config.get("gates"), "gates")
    _equal(set(gates), FALSE_GATES, "gate inventory")
    if any(value is not False for value in gates.values()):
        raise ValueError("successor gate opened")
    _validate_authority_section(
        config.get("implementation_authority"),
        EXPECTED_IMPLEMENTATION_AUTHORITIES,
        "implementation_authority",
    )
    _validate_authority_section(
        config.get("frozen_scientific_authority"),
        EXPECTED_FROZEN_AUTHORITIES,
        "frozen_scientific_authority",
    )
    validation = _mapping(config.get("validation_contract"), "validation contract")
    _equal(
        set(validation),
        {
            *EXPECTED_VALIDATION_PATHS,
            "validator_imports_solver_or_package_core",
            "validator_writes_files",
        },
        "validation contract inventory",
    )
    for key, expected in EXPECTED_VALIDATION_PATHS.items():
        _equal(validation.get(key), expected, f"validation {key}")
    _equal(
        validation.get("validator_imports_solver_or_package_core"),
        False,
        "validator runtime import flag",
    )
    _equal(
        validation.get("validator_writes_files"), False, "validator write flag"
    )


def _manifest_inventory(config: dict[str, Any], config_path: Path) -> dict[str, str]:
    inventory = {CONFIG_RELATIVE: _sha256(config_path)}
    for section_name, section in (
        ("predecessor", EXPECTED_PREDECESSOR_AUTHORITIES),
        ("implementation_authority", EXPECTED_IMPLEMENTATION_AUTHORITIES),
        ("frozen_scientific_authority", EXPECTED_FROZEN_AUTHORITIES),
    ):
        for name, item in section.items():
            relative, digest = _authority(item, f"{section_name}.{name}")
            inventory[relative] = digest
    for key in ("validator_path", "test_path"):
        relative = EXPECTED_VALIDATION_PATHS[key]
        inventory[relative] = _sha256(ROOT / relative)
    _equal(set(inventory), EXPECTED_MANIFEST_PATHS, "manifest path authority")
    return inventory


def validate(
    config_path: Path = CONFIG,
    manifest_path: Path = MANIFEST,
) -> dict[str, object]:
    """Read and validate the successor contract and exact live authority chain."""

    config = _load_yaml(config_path)
    _validate_contract(config)
    preregistration = _validate_predecessor(config)
    _validate_design_snapshot(config, preregistration)
    for section_name in ("implementation_authority", "frozen_scientific_authority"):
        for name, item in _mapping(config.get(section_name), section_name).items():
            _authority(item, f"{section_name}.{name}")
    manifest = _load_json(manifest_path)
    _equal(set(manifest), {"schema", "files"}, "manifest top-level inventory")
    _equal(
        manifest.get("schema"),
        "rq2_public_baseline_robustness_successor_manifest_v1",
        "manifest schema",
    )
    files = _mapping(manifest.get("files"), "manifest files")
    _equal(set(files), EXPECTED_MANIFEST_PATHS, "manifest path inventory")
    expected = _manifest_inventory(config, config_path)
    _equal(files, expected, "manifest exact inventory")
    if MANIFEST_RELATIVE in files:
        raise ValueError("manifest must not contain itself")
    if CONFIG_RELATIVE in {
        item["path"]
        for section in (
            EXPECTED_PREDECESSOR_AUTHORITIES,
            EXPECTED_IMPLEMENTATION_AUTHORITIES,
            EXPECTED_FROZEN_AUTHORITIES,
        )
        for item in section.values()
    }:
        raise ValueError("successor config must not bind itself as an authority")
    for relative, digest in files.items():
        _equal(_sha256(ROOT / relative), digest, f"manifest hash {relative}")
    return {
        "schema": "rq2_public_baseline_robustness_successor_validation_v1",
        "validation_passed": True,
        "registered_cell_count": 15,
        "arm_count": len(EXPECTED_ARMS),
        "manifest_file_count": len(files),
        "solver_calls": 0,
        "result_files_written": 0,
        "implementation_bound": False,
        "complete_external_orchestration": False,
        "formal_execution_ready": False,
        "formal_result": False,
        "claim": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    arguments = parser.parse_args()
    print(
        json.dumps(
            validate(arguments.config, arguments.manifest),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
