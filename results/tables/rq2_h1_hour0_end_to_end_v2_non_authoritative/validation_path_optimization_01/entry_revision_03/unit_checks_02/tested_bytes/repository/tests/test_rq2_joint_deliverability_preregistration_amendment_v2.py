from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from experiments import (
    validate_rq2_joint_deliverability_preregistration_amendment_v2 as validator,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = (
    ROOT / "configs/rq2_joint_deliverability_preregistration_amendment_v2.yaml"
)
PLAN = ROOT / "docs/plan/RQ2_联合服务可交付前沿确认性方案_v2.md"
INNER = ROOT / (
    "configs/rq2_joint_deliverability_preregistration_amendment_v2."
    "SHA256SUMS.json"
)
OUTER = ROOT / (
    "configs/rq2_joint_deliverability_preregistration_amendment_v2."
    "OUTER.SHA256SUMS.json"
)


def _design() -> dict:
    value = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_validator_accepts_sealed_amendment() -> None:
    report = validator.validate_design(_design(), require_sealed=True)
    assert report == {
        "design_valid": True,
        "scientific_changes": 0,
        "corrected_acceptance_items": 1,
        "solver_calls": 0,
        "result_files_written": 0,
    }


def test_amendment_preserves_scientific_protocol() -> None:
    design = _design()
    scope = design["scope"]
    assert scope["changes_scientific_question"] is False
    assert scope["changes_estimands"] is False
    assert scope["changes_registered_cells"] is False
    assert scope["changes_thresholds"] is False
    assert scope["changes_solver_contract"] is False
    assert scope["changes_execution_authority"] is False


def test_amendment_corrects_only_the_acceptance_item() -> None:
    design = _design()
    correction = design["correction"]
    assert correction["location"] == "predecessor_plan_section_5_item_3"
    assert correction["cross_arm_capacity_ordering_assumed"] is False
    assert correction["exact_capacity_identity"] == (
        "I_joint == I_sep + A_B6"
    )
    assert "signed four-arm decomposition" in correction[
        "corrected_acceptance_item"
    ]
    assert "CFE-compatible recovery" in correction[
        "corrected_acceptance_item"
    ]


def test_predecessor_outer_is_exact_and_still_valid() -> None:
    design = _design()
    predecessor = design["predecessor"]
    assert predecessor["outer_sha256"] == validator._sha256(
        ROOT / predecessor["outer_path"]
    )
    report = validator.predecessor_validator.validate()
    assert report["validation_passed"] is True
    assert report["formal_execution_ready"] is False


def test_cross_arm_ordering_drift_fails_closed() -> None:
    drifted = copy.deepcopy(_design())
    drifted["correction"]["cross_arm_capacity_ordering_assumed"] = True
    with pytest.raises(ValueError, match="cross-arm ordering"):
        validator.validate_design(drifted, require_sealed=True)


def test_execution_gates_remain_closed() -> None:
    design = _design()
    gates = design["gates"]
    for key in (
        "independent_R4_review_passed",
        "implementation_bound",
        "user_formal_run_authorized",
        "formal_execution_ready",
        "formal_result",
        "paper_claim",
    ):
        assert gates[key] is False
    assert design["scope"]["runs_solver"] is False
    assert design["scope"]["publishes_result"] is False


def test_sealed_files_and_manifests_are_consistent() -> None:
    design = _design()
    assert design["status"] == "SEALED_READY_FOR_INDEPENDENT_REVIEW"
    assert design["gates"]["pre_seal_audit_complete"] is True
    assert design["gates"]["sealed_ready_for_independent_review"] is True
    assert "`SEALED_READY_FOR_INDEPENDENT_REVIEW`" in PLAN.read_text(
        encoding="utf-8"
    )
    assert INNER.is_file()
    assert OUTER.is_file()
    report = validator.validate()
    assert report["validation_passed"] is True
    assert report["sealed_file_count"] == 4
    assert report["independent_R4_review_passed"] is False
    assert report["formal_execution_ready"] is False
