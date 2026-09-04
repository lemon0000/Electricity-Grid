"""Validate the RQ2 joint-deliverability preregistration amendment v2."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from experiments import (
    validate_rq2_joint_deliverability_preregistration_v1 as predecessor_validator,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = (
    "configs/rq2_joint_deliverability_preregistration_amendment_v2.yaml"
)
PLAN_RELATIVE = "docs/plan/RQ2_联合服务可交付前沿确认性方案_v2.md"
VALIDATOR_RELATIVE = (
    "experiments/validate_rq2_joint_deliverability_preregistration_"
    "amendment_v2.py"
)
TEST_RELATIVE = (
    "tests/test_rq2_joint_deliverability_preregistration_amendment_v2.py"
)
INNER_RELATIVE = (
    "configs/rq2_joint_deliverability_preregistration_amendment_v2."
    "SHA256SUMS.json"
)
OUTER_RELATIVE = (
    "configs/rq2_joint_deliverability_preregistration_amendment_v2."
    "OUTER.SHA256SUMS.json"
)

CONFIG = ROOT / CONFIG_RELATIVE
PLAN = ROOT / PLAN_RELATIVE
INNER = ROOT / INNER_RELATIVE
OUTER = ROOT / OUTER_RELATIVE

EXPECTED_PREDECESSOR = {
    "outer_path": (
        "configs/rq2_joint_deliverability_preregistration_v1."
        "OUTER.SHA256SUMS.json"
    ),
    "outer_sha256": (
        "a1208841e5997f55095858e07b1592b5899e45e74d2da23406663491d590b958"
    ),
    "config_path": "configs/rq2_joint_deliverability_preregistration_v1.yaml",
    "config_sha256": (
        "2efd3fa275cccde2aee701662bb2718386b2fb54d2846b090d0828d8409bdc4f"
    ),
    "specification_path": (
        "docs/model_spec/rq2_joint_deliverability_estimands_v1.md"
    ),
    "specification_sha256": (
        "28d38744d782aa9e9a8db239801b8ec44ef6290d41c4635ea6b76c208c9b5883"
    ),
    "plan_path": "docs/plan/RQ2_联合服务可交付前沿确认性方案_v1.md",
    "plan_sha256": (
        "940dbb01ef654b93aaa28958c049fe9568b67825a3c8eb3a87d268dd2408cb9d"
    ),
}
EXPECTED_FALSE_GATES = {
    "independent_R4_review_passed",
    "implementation_bound",
    "user_formal_run_authorized",
    "formal_execution_ready",
    "formal_result",
    "paper_claim",
}
EXPECTED_INNER_MEMBERS = {
    CONFIG_RELATIVE,
    PLAN_RELATIVE,
    VALIDATOR_RELATIVE,
    TEST_RELATIVE,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be a mapping")
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    return _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), str(path))


def _load_json(path: Path) -> dict[str, Any]:
    return _mapping(json.loads(path.read_text(encoding="utf-8")), str(path))


def _assert_equal(observed: object, expected: object, label: str) -> None:
    if observed != expected:
        raise ValueError(
            f"{label} drifted: expected {expected!r}, observed {observed!r}"
        )


def _validate_predecessor(design: dict[str, Any]) -> None:
    predecessor = _mapping(design.get("predecessor"), "predecessor")
    _assert_equal(predecessor, EXPECTED_PREDECESSOR, "predecessor authority")
    for key in ("outer", "config", "specification", "plan"):
        relative = predecessor[f"{key}_path"]
        expected = predecessor[f"{key}_sha256"]
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"predecessor member is missing or unsafe: {relative}")
        _assert_equal(_sha256(path), expected, f"predecessor hash {relative}")
    predecessor_report = predecessor_validator.validate()
    _assert_equal(
        predecessor_report.get("validation_passed"),
        True,
        "predecessor validation",
    )


def validate_design(
    design: dict[str, Any],
    *,
    require_sealed: bool,
) -> dict[str, Any]:
    _assert_equal(
        design.get("schema"),
        "rq2_joint_deliverability_preregistration_amendment_v2",
        "schema",
    )
    _assert_equal(design.get("version"), 2, "version")
    _validate_predecessor(design)

    scope = _mapping(design.get("scope"), "scope")
    for key in (
        "changes_scientific_question",
        "changes_estimands",
        "changes_registered_cells",
        "changes_thresholds",
        "changes_solver_contract",
        "changes_execution_authority",
        "runs_solver",
        "publishes_result",
        "formal_result",
        "claim",
    ):
        _assert_equal(scope.get(key), False, key)

    correction = _mapping(design.get("correction"), "correction")
    _assert_equal(
        correction.get("location"),
        "predecessor_plan_section_5_item_3",
        "correction location",
    )
    _assert_equal(
        correction.get("cross_arm_capacity_ordering_assumed"),
        False,
        "cross-arm ordering",
    )
    _assert_equal(
        correction.get("exact_capacity_identity"),
        "I_joint == I_sep + A_B6",
        "capacity identity",
    )
    corrected = str(correction.get("corrected_acceptance_item"))
    for required in (
        "signed four-arm decomposition",
        "target-specific CFE reconstruction",
        "CFE-compatible recovery",
        "fail-closed outcome states",
    ):
        if required not in corrected:
            raise ValueError(f"corrected acceptance item is incomplete: {required}")

    authority = _mapping(
        design.get("authoritative_combination"),
        "authoritative_combination",
    )
    _assert_equal(
        authority.get("scientific_config"),
        EXPECTED_PREDECESSOR["config_path"],
        "scientific config authority",
    )
    _assert_equal(
        authority.get("estimand_specification"),
        EXPECTED_PREDECESSOR["specification_path"],
        "estimand specification authority",
    )
    _assert_equal(
        authority.get("execution_plan"),
        PLAN_RELATIVE,
        "execution plan authority",
    )
    _assert_equal(
        authority.get("all_other_predecessor_bytes_and_semantics_unchanged"),
        True,
        "predecessor preservation",
    )

    gates = _mapping(design.get("gates"), "gates")
    for key in EXPECTED_FALSE_GATES:
        _assert_equal(gates.get(key), False, key)
    if require_sealed:
        _assert_equal(
            design.get("status"),
            "SEALED_READY_FOR_INDEPENDENT_REVIEW",
            "sealed status",
        )
        _assert_equal(gates.get("pre_seal_audit_complete"), True, "pre-seal gate")
        _assert_equal(
            gates.get("sealed_ready_for_independent_review"),
            True,
            "sealed gate",
        )
    else:
        _assert_equal(
            design.get("status"),
            "DRAFT_NONAUTHORITATIVE",
            "draft status",
        )
        _assert_equal(gates.get("pre_seal_audit_complete"), False, "pre-seal gate")
        _assert_equal(
            gates.get("sealed_ready_for_independent_review"),
            False,
            "sealed gate",
        )
    return {
        "design_valid": True,
        "scientific_changes": 0,
        "corrected_acceptance_items": 1,
        "solver_calls": 0,
        "result_files_written": 0,
    }


def _validate_manifests() -> dict[str, Any]:
    inner = _load_json(INNER)
    outer = _load_json(OUTER)
    _assert_equal(
        inner.get("schema"),
        "rq2_joint_deliverability_preregistration_amendment_manifest_v2",
        "inner schema",
    )
    files = _mapping(inner.get("files"), "inner files")
    _assert_equal(set(files), EXPECTED_INNER_MEMBERS, "inner inventory")
    for relative, expected in files.items():
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"sealed member is missing or unsafe: {relative}")
        _assert_equal(_sha256(path), expected, f"sealed member hash {relative}")

    _assert_equal(
        outer.get("schema"),
        "rq2_joint_deliverability_preregistration_amendment_outer_v2",
        "outer schema",
    )
    _assert_equal(outer.get("version"), 2, "outer version")
    outer_inner = _mapping(outer.get("inner"), "outer inner")
    _assert_equal(outer_inner.get("path"), INNER_RELATIVE, "outer inner path")
    _assert_equal(outer_inner.get("sha256"), _sha256(INNER), "outer inner hash")
    return {
        "inner_manifest_sha256": _sha256(INNER),
        "outer_manifest_sha256": _sha256(OUTER),
        "sealed_file_count": len(files),
    }


def validate() -> dict[str, Any]:
    design = _load_yaml(CONFIG)
    report = validate_design(design, require_sealed=True)
    report.update(_validate_manifests())
    report.update(
        {
            "validation_passed": True,
            "status": design["status"],
            "independent_R4_review_passed": False,
            "formal_execution_ready": False,
            "formal_result": False,
        }
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    print(json.dumps(validate(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
