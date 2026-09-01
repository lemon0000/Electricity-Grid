"""Pure-read validation of the RQ2 identification/report successor contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = (
    "configs/rq2_public_baseline_robustness_identification_successor_v1.yaml"
)
MANIFEST_RELATIVE = (
    "configs/rq2_public_baseline_robustness_identification_successor_v1."
    "SHA256SUMS.json"
)
CONFIG = ROOT / CONFIG_RELATIVE
MANIFEST = ROOT / MANIFEST_RELATIVE
CONFIG_SHA256 = "0bfa8e9fc08204c294fc160744ef208ab6bafeb32982f6912d89908c07970579"
MANIFEST_SCHEMA = (
    "rq2_public_baseline_robustness_identification_successor_manifest_v1"
)

PREDECESSOR_AUTHORITIES = {
    "preregistration": {
        "path": "configs/rq2_public_baseline_robustness_preregistration_v1.yaml",
        "sha256": "017708b25c3e1702c938a108af070a7047517bd128552500d3ffcac6a3ee3554",
    },
    "preregistration_manifest": {
        "path": (
            "configs/rq2_public_baseline_robustness_preregistration_v1."
            "SHA256SUMS.json"
        ),
        "sha256": "da6d13055ccfcd03c00939ab7fa61f43e05052556211f725b4550a09d33f64c9",
    },
    "package_successor": {
        "path": "configs/rq2_public_baseline_robustness_successor_v1.yaml",
        "sha256": "2d7a801b2cc0b078650a6b9917a45d282a3d9f273a0eb6043361a89a6c5f7d9a",
    },
    "package_successor_manifest": {
        "path": "configs/rq2_public_baseline_robustness_successor_v1.SHA256SUMS.json",
        "sha256": "0234ed0eb54b30f15891ff49df7f74fea678e6f05309a8c1e4473a9ea7d34954",
    },
}
IMPLEMENTATION_AUTHORITIES = {
    "package_core": {
        "path": "src/evaluation/rq2_baseline_robustness_package_v1.py",
        "sha256": "9075751220797c86270cc5877584d2aeb5ea128afe16a54befeb7831e7033e5f",
    },
    "transport_core": {
        "path": "src/scenarios/block_coupling.py",
        "sha256": "e18e025c6482ecb38f745bb993d346f49c4bdd99802cdb1675e4bd7ab5243cc4",
    },
    "identification_core": {
        "path": "src/evaluation/rq2_baseline_robustness_identification_v1.py",
        "sha256": "8f29faf7788a3f7c2578104fd34ff7e3301af47de55d66f3210907a3fe6d7722",
    },
    "report_core": {
        "path": "src/evaluation/rq2_baseline_robustness_report_v1.py",
        "sha256": "fd57bd03fea2a5e83d4b150cc941167bfbc37c80b4cf892d298361304bcbd56b",
    },
    "theoretical_propositions": {
        "path": "docs/model_spec/rq2_theoretical_propositions_v1.md",
        "sha256": "fc7ab30614a3d34a4d6740fc132679cb49f14e80137d6e420a20fdb23640edc8",
    },
}
VALIDATION_PATHS = {
    "validator_path": (
        "experiments/validate_rq2_public_baseline_robustness_identification_"
        "successor_v1.py"
    ),
    "test_path": (
        "tests/test_rq2_public_baseline_robustness_identification_successor_v1.py"
    ),
    "manifest_path": MANIFEST_RELATIVE,
}
FALSE_GATES = {
    "upstream_package_ready",
    "activation_authority_present",
    "implementation_bound",
    "independent_review",
    "execution_ready",
    "formal_identification_run",
    "report_published",
    "formal_result",
    "claim",
}
EXPECTED_BRANCHES = [
    "single_network_failure",
    "single_network_shortfall",
    "single_cfe_failure",
    "single_cfe_shortfall",
    "joint_capacity",
    "joint_failure",
    "joint_shortfall",
    "b6_capacity",
    "b6_failure",
    "b6_shortfall",
    "no_mechanism",
]
EXPECTED_PRIORITY = [
    "unresolved",
    "training_infeasible_estimand_undefined",
    "single_service_insufficiency_supported",
    "joint_only_interaction_supported",
    "b6_specific_underprovisioning_supported",
    "partially_identified",
    "no_registered_mechanism_supported",
]
EXPECTED_MANIFEST_PATHS = {
    CONFIG_RELATIVE,
    *(item["path"] for item in PREDECESSOR_AUTHORITIES.values()),
    *(item["path"] for item in IMPLEMENTATION_AUTHORITIES.values()),
    VALIDATION_PATHS["validator_path"],
    VALIDATION_PATHS["test_path"],
}


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return dict(value)


def _equal(observed: object, expected: object, label: str) -> None:
    if observed != expected:
        raise ValueError(f"{label} drifted: {observed!r} != {expected!r}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe(relative: object, label: str) -> str:
    if not isinstance(relative, str) or not relative:
        raise ValueError(f"{label} must be a nonempty path")
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or str(path) != relative:
        raise ValueError(f"{label} must be a canonical repository-relative path")
    return relative


def _is_reparse(path: Path) -> bool:
    status = path.lstat()
    return path.is_symlink() or bool(getattr(status, "st_file_attributes", 0) & 0x400)


def _assert_canonical_regular(path: Path, expected: Path, label: str) -> None:
    try:
        resolved = path.resolve(strict=True)
        expected_resolved = expected.resolve(strict=True)
        relative = resolved.relative_to(ROOT.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise ValueError(f"{label} is not the canonical repository file") from error
    if resolved != expected_resolved or not resolved.is_file():
        raise ValueError(f"{label} is not the canonical repository file")
    current = ROOT.resolve(strict=True)
    if _is_reparse(current):
        raise ValueError("repository root cannot be a reparse point")
    for part in relative.parts:
        current /= part
        if _is_reparse(current):
            raise ValueError(f"{label} contains a reparse component")


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        return _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "config")
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        raise ValueError("cannot load successor config") from error


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")), "manifest")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("cannot load successor manifest") from error


def _validate_authorities(
    observed: object,
    expected: Mapping[str, Mapping[str, str]],
    label: str,
) -> None:
    section = _mapping(observed, label)
    _equal(section, dict(expected), f"{label} exact authority inventory")
    for name, authority in expected.items():
        relative = _safe(authority["path"], f"{label}.{name}.path")
        path = ROOT / relative
        _assert_canonical_regular(path, path, f"{label}.{name}")
        _equal(_sha256(path), authority["sha256"], f"{label}.{name} live hash")


def _validate_contract(config: dict[str, Any]) -> None:
    _equal(
        set(config),
        {
            "schema",
            "version",
            "frozen_on",
            "status",
            "scope",
            "predecessor_authority",
            "implementation_authority",
            "activation_authority",
            "upstream_four_arm_package",
            "identification_contract",
            "registered_estimands",
            "classification_contract",
            "machine_contract",
            "validation_contract",
            "gates",
        },
        "config top-level inventory",
    )
    _equal(
        config["schema"],
        "rq2_public_baseline_robustness_identification_successor_v1",
        "schema",
    )
    _equal(
        config["status"],
        "implementation_binding_validate_only_upstream_package_absent",
        "status",
    )
    _validate_authorities(
        config["predecessor_authority"], PREDECESSOR_AUTHORITIES, "predecessor"
    )
    _validate_authorities(
        config["implementation_authority"],
        IMPLEMENTATION_AUTHORITIES,
        "implementation",
    )
    _equal(
        config["activation_authority"],
        {"path": None, "sha256": None, "activated": False},
        "activation authority",
    )
    upstream = _mapping(config["upstream_four_arm_package"], "upstream package")
    for key in (
        "path",
        "manifest_path",
        "manifest_sha256",
        "provenance_sha256",
        "validation_receipt_path",
    ):
        _equal(upstream.get(key), None, f"upstream {key}")
    _equal(upstream.get("ready"), False, "upstream ready")
    identification = _mapping(config["identification_contract"], "identification")
    _equal(identification.get("comparison_tolerance"), 1.0e-6, "comparison tolerance")
    _equal(identification.get("certificate_tolerance"), 1.0e-9, "certificate tolerance")
    _equal(
        identification.get("phase_one_positive_tolerance"),
        1.0e-8,
        "phase-one positive tolerance",
    )
    _equal(
        _mapping(identification.get("common_pi"), "common pi").get(
            "exact_branch_inventory"
        ),
        EXPECTED_BRANCHES,
        "common-pi branch inventory",
    )
    estimands = _mapping(config["registered_estimands"], "estimands")
    _equal(estimands.get("exact_category_deciding_metric_count"), 14, "metric count")
    _equal(estimands.get("debt_category_deciding"), False, "debt semantics")
    _equal(
        estimands.get("right_censored_terminal_debt_is_failure"),
        False,
        "right-censor semantics",
    )
    t1 = _mapping(estimands.get("T1_mw_only_reference"), "T1 reference")
    for key in ("raw_grid_call_trajectory_path", "raw_cfe_call_trajectory_path"):
        _equal(t1.get(key), None, f"T1 {key}")
    _equal(t1.get("implementation_bound"), False, "T1 implementation gate")
    _equal(
        t1.get("derivation_from_pairwise_outcomes_allowed"),
        False,
        "T1 derivation rule",
    )
    classification = _mapping(config["classification_contract"], "classification")
    _equal(
        classification.get("exact_exclusive_priority"),
        EXPECTED_PRIORITY,
        "exclusive classification priority",
    )
    _equal(classification.get("comparison_tolerance"), 1.0e-6, "classification tolerance")
    machine = _mapping(config["machine_contract"], "machine contract")
    _equal(
        machine.get("upstream_package_authority_schema"),
        "rq2_baseline_upstream_package_authority_v1",
        "upstream package authority schema",
    )
    _equal(
        machine.get("report_sections"),
        [
            "identification_evidence",
            "exclusive_attribution_by_cell",
            "negative_and_unresolved_cell_inventory",
            "descriptive_recovery_debt",
            "E0_outcomes",
            "claim_gate_report",
            "provenance",
        ],
        "report section inventory",
    )
    for key in (
        "report_build_requires_canonical_upstream_package_directory",
        "report_build_requires_manifest_sha256_authority",
        "report_validation_requires_identification_payload_and_upstream_package",
        "canonical_package_reidentification_before_report_required",
    ):
        _equal(machine.get(key), True, f"machine contract {key}")
    for key in (
        "standalone_report_scientific_validation_allowed",
        "synthetic_document_adapter_is_public_validation_authority",
    ):
        _equal(machine.get(key), False, f"machine contract {key}")
    validation = _mapping(config["validation_contract"], "validation contract")
    for key, expected in VALIDATION_PATHS.items():
        _equal(validation.get(key), expected, f"validation {key}")
    for key in (
        "validator_imports_identification_or_solver_core",
        "validator_runs_solver",
        "validator_writes_files",
    ):
        _equal(validation.get(key), False, f"validation {key}")
    gates = _mapping(config["gates"], "gates")
    _equal(set(gates), FALSE_GATES, "gate inventory")
    if any(value is not False for value in gates.values()):
        raise ValueError("identification successor gate opened")


def _expected_manifest() -> dict[str, str]:
    files = {CONFIG_RELATIVE: CONFIG_SHA256}
    for section in (PREDECESSOR_AUTHORITIES, IMPLEMENTATION_AUTHORITIES):
        for authority in section.values():
            files[authority["path"]] = authority["sha256"]
    for key in ("validator_path", "test_path"):
        relative = VALIDATION_PATHS[key]
        files[relative] = _sha256(ROOT / relative)
    _equal(set(files), EXPECTED_MANIFEST_PATHS, "expected manifest inventory")
    return files


def validate(
    config_path: Path = CONFIG,
    manifest_path: Path = MANIFEST,
) -> dict[str, object]:
    """Validate only the canonical frozen successor without solver imports or writes."""

    _assert_canonical_regular(config_path, CONFIG, "successor config")
    _assert_canonical_regular(manifest_path, MANIFEST, "successor manifest")
    _equal(_sha256(CONFIG), CONFIG_SHA256, "canonical config fixed hash")
    config = _load_yaml(CONFIG)
    _validate_contract(config)
    manifest = _load_json(MANIFEST)
    _equal(set(manifest), {"schema", "files"}, "manifest top-level inventory")
    _equal(manifest.get("schema"), MANIFEST_SCHEMA, "manifest schema")
    files = _mapping(manifest.get("files"), "manifest files")
    _equal(set(files), EXPECTED_MANIFEST_PATHS, "manifest exact path inventory")
    _equal(files, _expected_manifest(), "manifest exact hash inventory")
    if MANIFEST_RELATIVE in files:
        raise ValueError("manifest must not contain itself")
    for relative, digest in files.items():
        path = ROOT / _safe(relative, f"manifest path {relative}")
        _assert_canonical_regular(path, path, f"manifest file {relative}")
        _equal(_sha256(path), digest, f"manifest live hash {relative}")
    return {
        "schema": (
            "rq2_public_baseline_robustness_identification_successor_validation_v1"
        ),
        "validation_passed": True,
        "manifest_file_count": len(files),
        "solver_calls": 0,
        "result_files_written": 0,
        "upstream_package_ready": False,
        "activation_authority_present": False,
        "execution_ready": False,
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
