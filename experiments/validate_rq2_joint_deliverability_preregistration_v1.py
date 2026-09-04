"""Validate the sealed RQ2 joint-deliverability preregistration."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = "configs/rq2_joint_deliverability_preregistration_v1.yaml"
SPEC_RELATIVE = "docs/model_spec/rq2_joint_deliverability_estimands_v1.md"
PLAN_RELATIVE = "docs/plan/RQ2_联合服务可交付前沿确认性方案_v1.md"
VALIDATOR_RELATIVE = (
    "experiments/validate_rq2_joint_deliverability_preregistration_v1.py"
)
TEST_RELATIVE = "tests/test_rq2_joint_deliverability_preregistration_v1.py"
INNER_RELATIVE = (
    "configs/rq2_joint_deliverability_preregistration_v1.SHA256SUMS.json"
)
OUTER_RELATIVE = (
    "configs/rq2_joint_deliverability_preregistration_v1.OUTER.SHA256SUMS.json"
)

CONFIG = ROOT / CONFIG_RELATIVE
SPEC = ROOT / SPEC_RELATIVE
PLAN = ROOT / PLAN_RELATIVE
INNER = ROOT / INNER_RELATIVE
OUTER = ROOT / OUTER_RELATIVE

EXPECTED_ARMS = [
    "network_only_shared",
    "cfe_only_shared",
    "joint_correct_shared",
    "joint_b6_separate_planning_shared_execution",
]
EXPECTED_TARGETS = [0.50, 0.70, 0.85, 1.00]
EXPECTED_LABELS = {
    "network_single_service_binding",
    "cfe_single_service_binding",
    "joint_extra_requirement",
    "joint_portfolio_relief",
    "b6_capacity_underprovisioning",
    "b6_capacity_overprovisioning",
    "b6_operational_penalty",
    "b6_operational_relief",
}
EXPECTED_FALSE_GATES = {
    "independent_R4_review_passed",
    "implementation_bound",
    "upstream_grid_package_ready",
    "user_formal_run_authorized",
    "formal_execution_ready",
    "formal_result",
    "paper_claim",
}
EXPECTED_INNER_MEMBERS = {
    CONFIG_RELATIVE,
    SPEC_RELATIVE,
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


def _validate_predecessors(design: dict[str, Any]) -> None:
    predecessor = _mapping(
        design.get("predecessor_evidence"), "predecessor_evidence"
    )
    checks = (
        (
            predecessor["observed_phase_map"]["manifest_path"],
            predecessor["observed_phase_map"]["manifest_sha256"],
        ),
        (
            predecessor["observed_phase_map"]["summary_path"],
            predecessor["observed_phase_map"]["summary_sha256"],
        ),
        (
            predecessor["public_v6"]["preregistration_path"],
            predecessor["public_v6"]["preregistration_sha256"],
        ),
        (
            predecessor["public_v6"]["manifest_path"],
            predecessor["public_v6"]["manifest_sha256"],
        ),
        (
            predecessor["four_arm_v1"]["preregistration_path"],
            predecessor["four_arm_v1"]["preregistration_sha256"],
        ),
        (
            predecessor["four_arm_v1"]["manifest_path"],
            predecessor["four_arm_v1"]["manifest_sha256"],
        ),
    )
    for relative, expected in checks:
        path = ROOT / str(relative)
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"predecessor authority is missing or unsafe: {relative}")
        _assert_equal(_sha256(path), expected, f"predecessor hash {relative}")

    observed = predecessor["observed_phase_map"]
    _assert_equal(observed["total_cells"], 70, "predecessor cell count")
    _assert_equal(
        observed["region_counts"],
        {"R1": 0, "R2": 0, "R3": 69, "mixed": 1, "unresolved": 0},
        "predecessor region counts",
    )


def _validate_design_cells(design: dict[str, Any]) -> None:
    registered = _mapping(design.get("registered_design"), "registered_design")
    primary = _mapping(registered.get("primary_factorial"), "primary_factorial")
    factors = _mapping(primary.get("factors"), "primary factors")
    _assert_equal(
        factors.get("hourly_cfe_target"),
        EXPECTED_TARGETS,
        "primary CFE targets",
    )
    primary_count = 1
    for values in factors.values():
        if not isinstance(values, list):
            raise TypeError("primary factor levels must be lists")
        primary_count *= len(values)
    _assert_equal(primary_count, 36, "computed primary cell count")
    _assert_equal(primary.get("cell_count"), 36, "declared primary cell count")

    secondary = _mapping(registered.get("secondary_oat"), "secondary_oat")
    levels = _mapping(secondary.get("varied_levels"), "secondary OAT levels")
    added_count = sum(len(values) - 1 for values in levels.values())
    _assert_equal(added_count, 10, "computed secondary cell count")
    _assert_equal(
        secondary.get("added_unique_cell_count"),
        10,
        "declared secondary cell count",
    )
    _assert_equal(
        registered.get("exact_unique_cell_count"),
        primary_count + added_count,
        "total cell count",
    )
    _assert_equal(
        registered.get("selective_cell_reporting_allowed"),
        False,
        "selective reporting",
    )


def _validate_scientific_contract(design: dict[str, Any]) -> None:
    question = _mapping(design.get("research_question"), "research_question")
    _assert_equal(
        question.get("id"),
        "RQ2_joint_temporal_deliverability",
        "research question",
    )

    target = _mapping(design.get("hourly_cfe_target"), "hourly_cfe_target")
    _assert_equal(target.get("registered_levels"), EXPECTED_TARGETS, "CFE targets")
    _assert_equal(target.get("service_call_expression"), "raw_deficit", "CFE call")
    _assert_equal(
        target.get("service_call_truncated_to_available_flexibility"),
        False,
        "CFE call truncation",
    )
    _assert_equal(
        target.get("effective_recovery_headroom_expression"),
        "min(business_recovery_headroom, cfe_compatible_recovery_headroom)",
        "CFE-compatible recovery",
    )
    _assert_equal(
        target.get("network_call_scaled_with_alpha"),
        False,
        "network-call scaling",
    )

    arms = _mapping(design.get("arms"), "arms")
    _assert_equal(arms.get("canonical_order"), EXPECTED_ARMS, "arm order")
    definitions = _mapping(arms.get("definitions"), "arm definitions")
    _assert_equal(set(definitions), set(EXPECTED_ARMS), "arm definitions")
    _assert_equal(
        {item["execution_envelope"] for item in definitions.values()},
        {"shared"},
        "physical execution envelope",
    )

    estimands = _mapping(
        design.get("registered_capacity_estimands"),
        "registered_capacity_estimands",
    )
    _assert_equal(
        estimands["joint_interaction_contrast"]["expression"],
        "D_J - max(D_N, D_C)",
        "joint interaction",
    )
    _assert_equal(
        estimands["separate_envelope_interaction"]["expression"],
        "D_B - max(D_N, D_C)",
        "separate-envelope interaction",
    )
    _assert_equal(
        estimands["b6_capacity_bias"]["expression"],
        "D_J - D_B",
        "B6 capacity bias",
    )
    _assert_equal(
        estimands["exact_decomposition"]["expression"],
        "I_joint == I_sep + A_B6",
        "capacity decomposition",
    )
    _assert_equal(
        estimands.get("cross_arm_ordering_assumed"),
        False,
        "cross-arm ordering assumption",
    )

    attribution = _mapping(
        design.get("attribution_contract"), "attribution_contract"
    )
    _assert_equal(
        attribution.get("type"),
        "nonexclusive_bottleneck_vector",
        "attribution type",
    )
    _assert_equal(set(attribution.get("labels", {})), EXPECTED_LABELS, "labels")
    _assert_equal(
        attribution.get("one_label_suppresses_another"),
        False,
        "label suppression",
    )


def _validate_gates(design: dict[str, Any], *, require_sealed: bool) -> None:
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
            "seal gate",
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
            "seal gate",
        )

    implementation = _mapping(
        design.get("implementation_requirements"), "implementation_requirements"
    )
    for key in ("implementation_path", "runner_path", "output_path"):
        _assert_equal(implementation.get(key), None, key)


def validate_design(
    design: dict[str, Any],
    *,
    require_sealed: bool,
) -> dict[str, Any]:
    _assert_equal(
        design.get("schema"),
        "rq2_joint_deliverability_preregistration_v1",
        "schema",
    )
    _assert_equal(design.get("version"), 1, "version")
    _validate_predecessors(design)
    _validate_design_cells(design)
    _validate_scientific_contract(design)
    _validate_gates(design, require_sealed=require_sealed)
    return {
        "design_valid": True,
        "registered_cell_count": 46,
        "arm_count": 4,
        "solver_calls": 0,
        "result_files_written": 0,
    }


def _validate_manifests() -> dict[str, Any]:
    inner = _load_json(INNER)
    outer = _load_json(OUTER)
    _assert_equal(
        inner.get("schema"),
        "rq2_joint_deliverability_preregistration_manifest_v1",
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
        "rq2_joint_deliverability_preregistration_outer_v1",
        "outer schema",
    )
    _assert_equal(outer.get("version"), 1, "outer version")
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
