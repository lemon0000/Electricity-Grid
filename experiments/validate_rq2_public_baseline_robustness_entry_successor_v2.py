"""Pure-read validation of the RQ2 four-arm external entry successor."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = "configs/rq2_public_baseline_robustness_entry_successor_v2.yaml"
MANIFEST_RELATIVE = (
    "configs/rq2_public_baseline_robustness_entry_successor_v2.SHA256SUMS.json"
)
CONFIG = ROOT / CONFIG_RELATIVE
MANIFEST = ROOT / MANIFEST_RELATIVE
MANIFEST_SCHEMA = "rq2_public_baseline_robustness_entry_successor_manifest_v2"
VALIDATION_PATHS = {
    "validator_path": (
        "experiments/validate_rq2_public_baseline_robustness_entry_successor_v2.py"
    ),
    "runner_path": (
        "experiments/run_rq2_public_baseline_robustness_entry_successor_v2.py"
    ),
    "test_path": "tests/test_rq2_public_baseline_robustness_entry_successor_v2.py",
    "manifest_path": MANIFEST_RELATIVE,
}
PREDECESSOR_AUTHORITIES = {
    "package_contract_config": {
        "path": "configs/rq2_public_baseline_robustness_successor_v1.yaml",
        "sha256": "2d7a801b2cc0b078650a6b9917a45d282a3d9f273a0eb6043361a89a6c5f7d9a",
    },
    "package_contract_manifest": {
        "path": (
            "configs/rq2_public_baseline_robustness_successor_v1.SHA256SUMS.json"
        ),
        "sha256": "0234ed0eb54b30f15891ff49df7f74fea678e6f05309a8c1e4473a9ea7d34954",
    },
}
IMPLEMENTATION_AUTHORITIES = {
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
    "public_replay_api": {
        "path": "src/scenarios/rq2_public_replay.py",
        "sha256": "2d1668b43c21ecdbf851cb750b3a6979d7942e6abe4255ebf0a0f9a1c6297028",
    },
    "public_replay_successor_api": {
        "path": "src/scenarios/rq2_public_replay_successor.py",
        "sha256": "c239ad337130781f97afd74b562045104a98060f67ac3632d997218c0548b8cd",
    },
    "solver_adapter": {
        "path": "src/solvers/rq2_solver_adapter.py",
        "sha256": "bec0a6e58ba35d3f262a0df04d7695e91794d02c754ee939b75774c1cd3e6611",
    },
    "provenance_api": {
        "path": "src/evaluation/rq2_provenance_v3.py",
        "sha256": "c4376be60fda2499266f7593ca92eb1163c7ee156d7970dc1975d0e060f4bcec",
    },
    "execution_lease": {
        "path": "src/solvers/execution_lease.py",
        "sha256": "cb454d0eea168bbafdf75b89b07b8a5541077b05063c61d414a416c0cd2ab908",
    },
    "execution_machine": {
        "path": "src/evaluation/execution_machine.py",
        "sha256": "f5a1ee567c6127c4dc85da7c5ca40d1974a2ee4cdad6cceca2b4e67a54102e7f",
    },
    "repository_paths": {
        "path": "src/evaluation/repository_paths.py",
        "sha256": "e090d639289d93f0fb8cd292f60434d6379f5feaa6ab7396840ac72d8f000959",
    },
    "runner": {
        "path": VALIDATION_PATHS["runner_path"],
        "sha256": "70e883dfb86fdf68d216a95192785cd7ae6d8ab6f41bc4db2061994d00998726",
    },
}
FROZEN_AUTHORITIES = {
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
    "grid_dispatch_v4_config": {
        "path": "configs/rts_gmlc_public_grid_need_dispatch_v4.yaml",
        "sha256": "84db8e7ad47bf51dd1ec94db1ebb7d3edc068b587afb4fba8d596861d58e6beb",
    },
    "provenance_contract_v3": {
        "path": "configs/rq2_public_pipeline_provenance_contract_v3.yaml",
        "sha256": "9a890f6cebf6a2b87b6cee97ec9b3a5074bb40892cee917c98fe58644ff178f9",
    },
}
FALSE_GATES = {
    "external_inputs_ready",
    "independent_review",
    "user_execution_authorized",
    "execution_ready",
    "formal_result",
    "claim",
}


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return dict(value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_yaml(path: Path) -> dict[str, Any]:
    return _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "config")


def _load_json(path: Path) -> dict[str, Any]:
    return _mapping(json.loads(path.read_text(encoding="utf-8")), "manifest")


def _equal(observed: object, expected: object, label: str) -> None:
    if observed != expected:
        raise ValueError(f"{label} drifted: {observed!r} != {expected!r}")


def _safe(relative: object, label: str) -> str:
    if not isinstance(relative, str) or not relative:
        raise ValueError(f"{label} must be a nonempty path")
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or str(path) != relative:
        raise ValueError(f"{label} must be a canonical repository-relative path")
    return relative


def _validate_authorities(
    observed: object, expected: Mapping[str, Mapping[str, str]], label: str
) -> None:
    section = _mapping(observed, label)
    _equal(set(section), set(expected), f"{label} exact authority inventory")
    for name, authority in expected.items():
        _equal(section[name], authority, f"{label}.{name}")
        relative = _safe(authority["path"], f"{label}.{name}.path")
        _equal(_sha256(ROOT / relative), authority["sha256"], f"{label}.{name} live hash")


def _validate_contract(config: dict[str, Any]) -> None:
    _equal(config.get("schema"), "rq2_public_baseline_robustness_entry_successor_v2", "schema")
    _equal(
        config.get("status"),
        "external_preflight_blocked_validate_only_not_executable",
        "status",
    )
    scope = _mapping(config.get("scope"), "scope")
    for key in (
        "changes_scientific_protocol",
        "runs_solver_during_contract_validation",
        "writes_during_contract_validation",
        "runs_identification",
        "writes_report",
        "formal_result",
        "claim",
    ):
        _equal(scope.get(key), False, f"scope {key}")
    _validate_authorities(
        config.get("predecessor_authority"), PREDECESSOR_AUTHORITIES, "predecessor"
    )
    _validate_authorities(
        config.get("implementation_authority"),
        IMPLEMENTATION_AUTHORITIES,
        "implementation",
    )
    _validate_authorities(
        config.get("frozen_scientific_authority"), FROZEN_AUTHORITIES, "frozen"
    )
    activation = _mapping(config.get("activation_authority"), "activation_authority")
    _equal(
        activation,
        {"path": None, "sha256": None, "activated": False},
        "activation authority",
    )
    external = _mapping(config.get("external_inputs"), "external_inputs")
    workload = _mapping(external.get("workload"), "workload")
    _equal(workload.get("manifest_sha256"), "62f2ec5eefd0c651d8b970a16fce4fb6336ccb75ab09e3d2c67386cc26edb524", "workload manifest")
    _equal(workload.get("training_blocks"), 34, "workload training count")
    _equal(workload.get("holdout_blocks"), 34, "workload holdout count")
    _equal(workload.get("block_hours"), 24, "workload block hours")
    grid = _mapping(external.get("grid"), "grid")
    _equal(grid.get("frozen_authority_gate"), False, "grid authority gate")
    for key in ("manifest_sha256", "config_sha256", "provenance_sha256"):
        _equal(grid.get(key), None, f"grid {key}")
    _equal(grid.get("checkpoint_count"), 1071, "grid checkpoint count")
    _equal(grid.get("training_blocks"), 541, "grid training count")
    _equal(grid.get("holdout_blocks"), 530, "grid holdout count")
    _equal(grid.get("block_hours"), 24, "grid block hours")
    design = _mapping(config.get("runtime_design"), "runtime_design")
    selection = _mapping(design.get("training_selection"), "training_selection")
    _equal(selection.get("power_system_representatives"), 8, "power reps")
    _equal(selection.get("workload_representatives"), 8, "workload reps")
    _equal(selection.get("selection_uses_holdout_outcomes"), False, "holdout selection")
    solver = _mapping(design.get("solver"), "solver")
    _equal(solver.get("name"), "gurobi", "solver name")
    _equal(solver.get("threads"), 4, "solver threads")
    _equal(solver.get("mip_relative_gap"), 1.0e-6, "solver gap")
    execution = _mapping(config.get("execution"), "execution")
    for key in FALSE_GATES - {"formal_result", "claim"}:
        _equal(execution.get(key), False, f"execution gate {key}")
    gates = _mapping(config.get("gates"), "gates")
    _equal(set(gates), FALSE_GATES, "gate inventory")
    if any(value is not False for value in gates.values()):
        raise ValueError("entry successor gate opened")
    validation = _mapping(config.get("validation_contract"), "validation_contract")
    _equal(
        set(validation),
        {*VALIDATION_PATHS, "validator_imports_runtime_core", "validator_writes_files"},
        "validation inventory",
    )
    for key, expected in VALIDATION_PATHS.items():
        _equal(validation.get(key), expected, f"validation {key}")
    _equal(validation.get("validator_imports_runtime_core"), False, "runtime import flag")
    _equal(validation.get("validator_writes_files"), False, "validator writes flag")


def _expected_manifest(config_path: Path) -> dict[str, str]:
    files = {CONFIG_RELATIVE: _sha256(config_path)}
    for section in (
        PREDECESSOR_AUTHORITIES,
        IMPLEMENTATION_AUTHORITIES,
        FROZEN_AUTHORITIES,
    ):
        for item in section.values():
            files[item["path"]] = item["sha256"]
    for key in ("validator_path", "test_path"):
        relative = VALIDATION_PATHS[key]
        files[relative] = _sha256(ROOT / relative)
    return files


def validate(
    config_path: Path = CONFIG, manifest_path: Path = MANIFEST
) -> dict[str, object]:
    config = _load_yaml(config_path)
    _validate_contract(config)
    manifest = _load_json(manifest_path)
    _equal(set(manifest), {"schema", "files"}, "manifest top-level inventory")
    _equal(manifest.get("schema"), MANIFEST_SCHEMA, "manifest schema")
    files = _mapping(manifest.get("files"), "manifest files")
    expected = _expected_manifest(config_path)
    _equal(files, expected, "manifest exact inventory")
    if MANIFEST_RELATIVE in files:
        raise ValueError("manifest must not contain itself")
    for relative, digest in files.items():
        path = config_path if relative == CONFIG_RELATIVE else ROOT / _safe(relative, relative)
        _equal(_sha256(path), digest, f"manifest live hash {relative}")
    return {
        "schema": "rq2_public_baseline_robustness_entry_validation_v2",
        "validation_passed": True,
        "manifest_file_count": len(files),
        "solver_calls": 0,
        "result_files_written": 0,
        "activation_authority_present": False,
        "external_inputs_ready": False,
        "execution_ready": False,
        "formal_result": False,
        "claim": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    arguments = parser.parse_args()
    print(json.dumps(validate(arguments.config, arguments.manifest), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
