from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from src.evaluation import rq2_baseline_robustness_identification_v1 as identification
from src.evaluation import rq2_baseline_robustness_package_v1 as package
from src.evaluation.rq2_baseline_robustness_report_v1 import (
    build_report_from_identification_payload,
    validate_identification_report,
)

ROOT = Path(__file__).resolve().parents[1]
SUCCESSOR_CONFIG = (
    ROOT
    / "configs/rq2_public_baseline_robustness_identification_successor_v1.yaml"
)
SUCCESSOR_MANIFEST = (
    ROOT
    / "configs/rq2_public_baseline_robustness_identification_successor_v1."
    "SHA256SUMS.json"
)
SUCCESSOR_VALIDATOR = (
    ROOT
    / "experiments/validate_rq2_public_baseline_robustness_identification_"
    "successor_v1.py"
)
TEST_PACKAGE_MANIFEST_SHA256 = "a" * 64


def _validator_namespace() -> dict[str, object]:
    source = SUCCESSOR_VALIDATOR.read_text(encoding="utf-8")
    namespace: dict[str, object] = {
        "__name__": "identification_successor_validator_test",
        "__file__": str(SUCCESSOR_VALIDATOR),
    }
    exec(compile(source, str(SUCCESSOR_VALIDATOR), "exec"), namespace)
    return namespace


def _resolved(lower: float = 0.0, upper: float = 0.0) -> dict[str, object]:
    return {"resolved": True, "lower": lower, "upper": upper}


def _bounds() -> dict[str, object]:
    return {metric: _resolved() for metric in identification.CATEGORY_DECIDING_METRICS}


def _branches(status: str = "compatible") -> dict[str, dict[str, object]]:
    return {
        name: {"status": status}
        for name in (
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
        )
    }


def _classify(
    bounds: dict[str, object],
    branches: dict[str, dict[str, object]] | None = None,
    **kwargs: object,
) -> dict[str, object]:
    return identification.classify_registered_attribution(
        training_disposition=str(kwargs.pop("training_disposition", "resolved")),
        scalar_bounds=bounds,
        common_pi_branches=_branches() if branches is None else branches,
        global_preconditions_hold=bool(kwargs.pop("global_preconditions_hold", True)),
        **kwargs,
    )


def _raw_outcome(*, debt: float = 0.0) -> dict[str, object]:
    return {
        "name": "synthetic",
        "committed_flexibility": 0.2,
        "resolved": True,
        "hard_grid_failure": False,
        "physical_policy_failure": False,
        "service_shortfall_failure": False,
        "access_shortfall": 0.0,
        "peak_recovery_debt": debt,
        "terminal_recovery_debt": debt,
        "combined_call": [0.0],
        "green_served": [0.0],
        "physical_violations": [],
    }


def _finite_arm(arm_id: str, *, right_censored: bool, debt: float = 0.0) -> dict[str, object]:
    raw = _raw_outcome(debt=debt)
    return {
        "arm_id": arm_id,
        "committed_capacity": 0.2,
        "raw_causal_policy_outcome": raw,
        "registered_service_risk_outcome": {
            "schema": "rq2_baseline_registered_service_risk_v1",
            "resolved": True,
            "unresolved_reason": None,
            "registered_failure": False,
            "registered_physical_failure": False,
            "service_shortfall_failure": False,
            "service_shortfall_amount": 0.0,
            "registered_physical_violations": [],
            "excluded_debt_violations": [],
            "excluded_terminal_condition_violations": [],
            "right_censored": right_censored,
            "raw_outcome": raw,
        },
    }


def _synthetic_package_documents(*, debt: float = 0.0) -> dict[str, object]:
    cell_id = "base"
    expected_pairs = []
    finite_pairs = []
    e0_pairs = []
    for power_id, power_probability, state in (
        ("p0", 0.25, identification.EXOGENOUS_GRID_INFEASIBILITY),
        ("p1", 0.75, identification.FINITE_GRID_NEED),
    ):
        for workload_id, workload_probability in (("w0", 0.4), ("w1", 0.6)):
            right_censored = workload_id == "w1"
            common = {
                "cell_id": cell_id,
                "power_block_id": power_id,
                "workload_block_id": workload_id,
                "grid_state": state,
                "power_probability": power_probability,
                "workload_probability": workload_probability,
                "right_censored": right_censored,
                "boundary_state_status": (
                    "right_censored" if right_censored else "complete"
                ),
                "terminal_period_completed": not right_censored,
                "require_terminal_event_inactive": not right_censored,
            }
            expected_pairs.append(common)
            checkpoint_common = {
                **common,
                "unconditional_pair_probability": (
                    power_probability * workload_probability
                ),
                "resume_identity": {},
                "provenance": {},
            }
            if state == identification.FINITE_GRID_NEED:
                finite_pairs.append(
                    {
                        "schema": "rq2_baseline_finite_pair_checkpoint_v1",
                        **checkpoint_common,
                        "arms": [
                            _finite_arm(
                                arm_id,
                                right_censored=right_censored,
                                debt=debt,
                            )
                            for arm_id in identification.FOUR_ARM_IDS
                        ],
                    }
                )
            else:
                e0_pairs.append(
                    {
                        "schema": "rq2_baseline_E0_checkpoint_v1",
                        **checkpoint_common,
                        "resolved": True,
                        "unresolved_reason": None,
                        "service_metrics_defined": False,
                    }
                )
    training_arms = [
        {
            "arm_id": arm_id,
            "status": "passed",
            "pair_count": 2,
            "failed_pair_ids": [],
            "unresolved_pair_ids": [],
            "reason": None,
        }
        for arm_id in identification.FOUR_ARM_IDS
    ]
    planning_arms = [
        {
            "arm_id": arm_id,
            "status": "resolved",
            "minimum_capacity": 0.2,
            "estimand_defined": True,
            "certificate": {},
        }
        for arm_id in identification.FOUR_ARM_IDS
    ]
    return {
        "four_arm_training_status": {
            "schema": "four_arm_training_status",
            "cells": [
                {
                    "cell_id": cell_id,
                    "disposition": "resolved",
                    "arms": training_arms,
                }
            ],
        },
        "four_arm_minimum_flexibility": {
            "schema": "four_arm_minimum_flexibility",
            "cells": [
                {
                    "cell_id": cell_id,
                    "disposition": "resolved",
                    "arms": planning_arms,
                }
            ],
        },
        "four_arm_pairwise_outcomes": {
            "schema": "four_arm_pairwise_outcomes",
            "pairs": finite_pairs,
        },
        "E0_outcomes": {
            "schema": "E0_outcomes",
            "pairs": e0_pairs,
            "unconditional_probability_mass_by_cell": {cell_id: 0.25},
            "public_marginal_mass_once": 0.25,
        },
        "checkpoint_inventory": {
            "schema": "checkpoint_inventory",
            "probability_tolerance": 1.0e-9,
            "expected_pairs": expected_pairs,
            "planning": [],
            "pairs": [],
        },
        "provenance": {
            "schema": "provenance",
            "resume_identity": {},
            "source_provenance": {},
            "formal_result": False,
            "claim": False,
        },
    }


def _synthetic_package_validation() -> dict[str, object]:
    return {
        "schema": "rq2_baseline_package_validation_v1",
        "validation_passed": True,
        "file_count": 10,
        "formal_result": False,
        "claim": False,
    }


def _synthetic_identification_payload(*, debt: float = 0.0) -> dict[str, object]:
    return identification._identify_validated_package_documents(
        package_validation=_synthetic_package_validation(),
        package_documents=_synthetic_package_documents(debt=debt),
        package_manifest_sha256=TEST_PACKAGE_MANIFEST_SHA256,
        stable_snapshot_verified=True,
    )


def _install_package_authority(
    monkeypatch: pytest.MonkeyPatch,
    authoritative_payload: dict[str, object],
) -> None:
    def rebuild(
        package_directory: Path,
        *,
        expected_manifest_sha256: str,
    ) -> dict[str, object]:
        assert isinstance(package_directory, Path)
        assert expected_manifest_sha256 == TEST_PACKAGE_MANIFEST_SHA256
        return copy.deepcopy(authoritative_payload)

    monkeypatch.setattr(identification, "identify_final_package", rebuild)


def _build_authoritative_report(
    payload: dict[str, object],
    *,
    monkeypatch: pytest.MonkeyPatch,
    package_directory: Path,
) -> dict[str, object]:
    _install_package_authority(monkeypatch, payload)
    return build_report_from_identification_payload(
        payload,
        package_directory=package_directory,
        package_manifest_sha256=TEST_PACKAGE_MANIFEST_SHA256,
    )


def _validate_authoritative_report(
    report: dict[str, object],
    payload: dict[str, object],
    *,
    package_directory: Path,
) -> dict[str, object]:
    return validate_identification_report(
        report,
        identification_payload=payload,
        package_directory=package_directory,
        package_manifest_sha256=TEST_PACKAGE_MANIFEST_SHA256,
    )


def test_scalar_transport_has_attaining_primal_dual_certificates() -> None:
    result = identification.certify_scalar_transport(
        (0.5, 0.5),
        (0.5, 0.5),
        ((0.0, 1.0), (1.0, 0.0)),
        metric_name="analytic",
    )

    assert result["resolved"] is True
    assert result["sharp"] is True
    assert result["lower"]["value"] == pytest.approx(0.0)
    assert result["upper"]["value"] == pytest.approx(1.0)
    for endpoint in (result["lower"], result["upper"]):
        assert endpoint["primal_dual_gap"] <= identification.CERTIFICATE_TOLERANCE
        assert max(endpoint["residuals"].values()) <= identification.CERTIFICATE_TOLERANCE
        coupling = np.asarray(endpoint["coupling"])
        assert coupling.sum(axis=1) == pytest.approx((0.5, 0.5))
        assert coupling.sum(axis=0) == pytest.approx((0.5, 0.5))


def test_common_pi_phase_one_certifies_feasible_and_incompatible() -> None:
    diagonal = ((1.0, 0.0), (0.0, 1.0))
    off_diagonal = ((0.0, 1.0), (1.0, 0.0))
    feasible = identification.certify_common_pi_phase_one(
        (0.5, 0.5),
        (0.5, 0.5),
        (identification.LinearInequality("diagonal", diagonal, 0.5),),
    )
    incompatible = identification.certify_common_pi_phase_one(
        (0.5, 0.5),
        (0.5, 0.5),
        (
            identification.LinearInequality("diagonal", diagonal, 0.0),
            identification.LinearInequality("off_diagonal", off_diagonal, 0.0),
        ),
    )

    assert feasible["status"] == "compatible"
    assert feasible["phase_one_optimum"] == pytest.approx(0.0)
    assert incompatible["status"] == "certified_incompatible"
    assert incompatible["phase_one_optimum"] == pytest.approx(0.5)
    certificate = incompatible["certificate"]
    assert certificate["primal_objective"] == pytest.approx(0.5)
    assert certificate["dual_objective"] == pytest.approx(0.5)
    assert certificate["primal_dual_gap"] <= identification.CERTIFICATE_TOLERANCE
    assert max(certificate["residuals"].values()) <= identification.CERTIFICATE_TOLERANCE


def test_common_pi_branch_uses_one_candidate_witness() -> None:
    diagonal = ((1.0, 0.0), (0.0, 1.0))
    off_diagonal = ((0.0, 1.0), (1.0, 0.0))
    result = identification.certify_common_pi_branch(
        (0.5, 0.5),
        (0.5, 0.5),
        branch_name="joint_failure",
        mandatory_inequalities=(
            identification.LinearInequality("off_diagonal", off_diagonal, 0.0),
        ),
        candidate_matrix=diagonal,
    )

    assert result["status"] == "compatible"
    witness = np.asarray(result["candidate"]["coupling"])
    assert float(np.sum(witness * np.asarray(off_diagonal))) <= 1.0e-9
    assert float(np.sum(witness * np.asarray(diagonal))) > 1.0e-6


def test_uncertified_or_ambiguous_common_pi_is_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    real = identification._standard_form_certificate
    monkeypatch.setattr(
        identification,
        "_standard_form_certificate",
        lambda *args, **kwargs: {"resolved": False, "unresolved_reason": "synthetic"},
    )
    unknown = identification.certify_common_pi_phase_one((1.0,), (1.0,), ())
    assert unknown["status"] == "unknown"

    monkeypatch.setattr(identification, "_standard_form_certificate", real)
    monkeypatch.setattr(identification, "PHASE_ONE_POSITIVE_TOLERANCE", 1.0)
    ambiguous = identification.certify_common_pi_phase_one(
        (0.5, 0.5),
        (0.5, 0.5),
        (
            identification.LinearInequality(
                "diagonal",
                ((1.0, 0.0), (0.0, 1.0)),
                -5.0e-9,
            ),
        ),
    )
    assert ambiguous["status"] == "unknown"


def test_phase_one_solver_status_two_alone_is_not_incompatibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailedResult:
        status = 2
        success = False
        x = None
        message = "synthetic infeasible status without a certificate"

    monkeypatch.setattr(identification, "linprog", lambda *args, **kwargs: FailedResult())
    result = identification.certify_common_pi_phase_one(
        (1.0,),
        (1.0,),
        (
            identification.LinearInequality(
                "synthetic",
                ((1.0,),),
                0.0,
            ),
        ),
    )

    assert result["status"] == "unknown"
    assert result["certificate"]["resolved"] is False


def test_marginals_are_cross_cell_consistent_and_E0_is_separate() -> None:
    pairs = []
    for cell in ("a", "b"):
        for row, probability, state in (
            ("p0", 0.25, identification.EXOGENOUS_GRID_INFEASIBILITY),
            ("p1", 0.75, identification.FINITE_GRID_NEED),
        ):
            for column, workload_probability in (("w0", 0.4), ("w1", 0.6)):
                pairs.append(
                    {
                        "cell_id": cell,
                        "power_block_id": row,
                        "workload_block_id": column,
                        "grid_state": state,
                        "power_probability": probability,
                        "workload_probability": workload_probability,
                        "right_censored": True,
                        "boundary_state_status": "right_censored",
                    }
                )
    result = identification.derive_marginal_evidence(pairs, ("a", "b"))

    assert result.exogenous_grid_infeasibility_mass == pytest.approx(0.25)
    assert result.finite_row_ids == ("p1",)
    assert result.finite_row_probabilities == pytest.approx((1.0,))
    assert result.column_probabilities == pytest.approx((0.4, 0.6))

    drifted = copy.deepcopy(pairs)
    drifted[-1]["right_censored"] = False
    with pytest.raises(ValueError, match="drifted across cells"):
        identification.derive_marginal_evidence(drifted, ("a", "b"))


@pytest.mark.parametrize(
    ("mutate", "expected"),
    (
        ((identification.NETWORK_FAILURE, 0.2, 0.3), identification.SINGLE_SERVICE),
        ((identification.JOINT_INTERACTION_CAPACITY, 0.2, 0.2), identification.JOINT_ONLY),
        ((identification.B6_UNDERPROVISIONING, 0.2, 0.2), identification.B6_SPECIFIC),
        ((identification.NETWORK_FAILURE, 0.0, 0.2), identification.PARTIALLY_IDENTIFIED),
        (None, identification.NO_MECHANISM),
    ),
)
def test_registered_category_priority_cases(mutate, expected) -> None:
    bounds = _bounds()
    if mutate is not None:
        metric, lower, upper = mutate
        bounds[metric] = _resolved(lower, upper)
    result = _classify(bounds)
    assert result["classification"] == expected


def test_unresolved_and_training_infeasible_precede_scientific_categories() -> None:
    positive = _bounds()
    positive[identification.NETWORK_FAILURE] = _resolved(0.2, 0.3)

    assert _classify(positive, global_preconditions_hold=False)["classification"] == identification.UNRESOLVED
    assert _classify(
        positive,
        training_disposition=identification.TRAINING_INFEASIBLE,
    )["classification"] == identification.TRAINING_INFEASIBLE


def test_tolerance_boundaries_are_not_silently_promoted() -> None:
    bounds = _bounds()
    bounds[identification.NETWORK_FAILURE] = _resolved(
        identification.COMPARISON_TOLERANCE,
        identification.COMPARISON_TOLERANCE,
    )
    assert _classify(bounds)["classification"] == identification.NO_MECHANISM

    bounds[identification.NETWORK_FAILURE] = _resolved(
        identification.COMPARISON_TOLERANCE,
        2.0 * identification.COMPARISON_TOLERANCE,
    )
    assert _classify(bounds)["classification"] == identification.PARTIALLY_IDENTIFIED


def test_debt_perturbation_and_right_censor_do_not_change_classification(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload_a = _synthetic_identification_payload(debt=0.0)
    report_a = _build_authoritative_report(
        payload_a,
        monkeypatch=monkeypatch,
        package_directory=tmp_path,
    )
    payload_b = _synthetic_identification_payload(debt=999.0)
    report_b = _build_authoritative_report(
        payload_b,
        monkeypatch=monkeypatch,
        package_directory=tmp_path,
    )

    assert report_a["exclusive_attribution_by_cell"] == report_b["exclusive_attribution_by_cell"]
    assert report_a["claim_gate_report"] == report_b["claim_gate_report"]
    assert report_a["E0_outcomes"]["conditional_service_metrics_defined"] is False
    assert report_b["descriptive_recovery_debt"]["category_deciding"] is False
    assert (
        _validate_authoritative_report(
            report_b,
            payload_b,
            package_directory=tmp_path,
        )
        == report_b
    )


def test_metricwise_possible_but_phase_one_incompatible_is_partial() -> None:
    bounds = _bounds()
    bounds[identification.JOINT_FAILURE] = _resolved(0.0, 0.5)
    branches = _branches()
    branches["joint_failure"] = {"status": "certified_incompatible"}

    result = _classify(
        bounds,
        branches,
        metricwise_possible_incompatible_branches=("joint_failure",),
    )
    assert result["classification"] == identification.PARTIALLY_IDENTIFIED


def test_unknown_branch_forces_global_unresolved() -> None:
    branches = _branches()
    branches["joint_failure"] = {"status": "unknown"}
    result = _classify(_bounds(), branches)
    assert result["classification"] == identification.UNRESOLVED


def test_validated_package_adapter_builds_exact_identification_inventory() -> None:
    result = identification._identify_validated_package_documents(
        package_validation=_synthetic_package_validation(),
        package_documents=_synthetic_package_documents(),
    )

    assert result["schema"] == "rq2_baseline_robustness_identification_payload_v1"
    assert result["formal_result"] is False
    assert result["claim"] is False
    assert result["marginal_evidence"]["E0_unconditional_probability_mass"] == pytest.approx(0.25)
    assert result["marginal_evidence"]["E0_conditional_service_metrics_defined"] is False
    cell = result["cells"][0]
    assert set(cell["scalar_transport_endpoints"]) == set(
        identification.CATEGORY_DECIDING_METRICS
    )
    assert set(cell["common_pi_multimetric_witnesses"]) == set(
        identification.COMMON_PI_BRANCHES
    )
    assert set(cell["descriptive_recovery_debt_bounds"]) == set(
        identification.DESCRIPTIVE_DEBT_METRICS
    )
    assert cell["classification"]["classification"] == identification.NO_MECHANISM
    assert cell["right_censored_pair_ids"] == ["p1::w1"]
    assert result["T1_mw_only_reference"] == {
        "raw_grid_call_trajectory_path": None,
        "raw_cfe_call_trajectory_path": None,
        "implementation_bound": False,
        "status": "future_raw_trajectory_input_required",
    }


def test_adapter_debt_perturbation_cannot_change_classification() -> None:
    baseline = identification._identify_validated_package_documents(
        package_validation=_synthetic_package_validation(),
        package_documents=_synthetic_package_documents(debt=0.0),
    )
    perturbed = identification._identify_validated_package_documents(
        package_validation=_synthetic_package_validation(),
        package_documents=_synthetic_package_documents(debt=99.0),
    )

    assert baseline["cells"][0]["classification"] == perturbed["cells"][0]["classification"]
    assert (
        baseline["cells"][0]["descriptive_recovery_debt_bounds"]
        != perturbed["cells"][0]["descriptive_recovery_debt_bounds"]
    )


def test_adapter_rejects_six_schema_inventory_or_E0_tamper() -> None:
    missing = _synthetic_package_documents()
    missing.pop("provenance")
    with pytest.raises(ValueError, match="missing or extra"):
        identification._identify_validated_package_documents(
            package_validation=_synthetic_package_validation(),
            package_documents=missing,
        )

    tampered = _synthetic_package_documents()
    tampered["E0_outcomes"]["public_marginal_mass_once"] = 0.5
    with pytest.raises(ValueError, match="E0 marginal mass"):
        identification._identify_validated_package_documents(
            package_validation=_synthetic_package_validation(),
            package_documents=tampered,
        )


def test_report_adapter_and_rebuild_validator_close_all_inventories(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = _synthetic_identification_payload()
    report = _build_authoritative_report(
        payload,
        monkeypatch=monkeypatch,
        package_directory=tmp_path,
    )

    assert (
        _validate_authoritative_report(
            report,
            payload,
            package_directory=tmp_path,
        )
        == report
    )
    cell = report["exclusive_attribution_by_cell"]["cells"][0]
    assert cell["classification"] == identification.NO_MECHANISM
    assert cell["reason"] == "all_registered_category_determinants_robust_nonpositive"
    assert cell["common_pi_branch"] == "no_mechanism"
    assert report["negative_and_unresolved_cell_inventory"]["negative_cell_ids"] == [
        "base"
    ]
    assert set(report["descriptive_recovery_debt"]["by_cell"]) == {"base"}
    evidence = report["identification_evidence"]
    assert evidence["identification_payload_sha256"] == (
        identification.canonical_identification_payload_sha256(payload)
    )
    assert evidence["upstream_package_manifest_sha256"] == (
        TEST_PACKAGE_MANIFEST_SHA256
    )
    assert evidence["upstream_provenance_sha256"] == payload[
        "upstream_package_authority"
    ]["provenance_sha256"]


@pytest.mark.parametrize(
    "mutation",
    ("classification", "debt", "right_censor", "E0", "T1", "provenance"),
)
def test_report_adapter_rejects_identification_payload_tamper(
    mutation: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    authoritative = _synthetic_identification_payload()
    payload = copy.deepcopy(authoritative)
    if mutation == "classification":
        payload["cells"][0]["classification"]["classification"] = (
            identification.UNRESOLVED
        )
    elif mutation == "debt":
        payload["cells"][0]["descriptive_recovery_debt_bounds"].pop(
            identification.DESCRIPTIVE_DEBT_METRICS[0]
        )
    elif mutation == "right_censor":
        payload["cells"][0]["right_censored_pair_ids"] *= 2
    elif mutation == "E0":
        payload["marginal_evidence"]["E0_unconditional_probability_mass"] = 0.5
    elif mutation == "T1":
        payload["T1_mw_only_reference"]["implementation_bound"] = True
    else:
        payload["provenance"]["claim"] = True
    _install_package_authority(monkeypatch, authoritative)
    with pytest.raises(ValueError, match="drifted from the canonical package"):
        build_report_from_identification_payload(
            payload,
            package_directory=tmp_path,
            package_manifest_sha256=TEST_PACKAGE_MANIFEST_SHA256,
        )


def test_report_adapter_rejects_coordinated_forged_b6_bound_and_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    authoritative = _synthetic_identification_payload()
    forged = copy.deepcopy(authoritative)
    cell = forged["cells"][0]
    endpoint = cell["scalar_transport_endpoints"][
        identification.B6_UNDERPROVISIONING
    ]
    assert endpoint["lower"]["value"] == pytest.approx(0.0)
    assert endpoint["upper"]["value"] == pytest.approx(0.0)
    cell["arm_and_contrast_cell_bounds"][identification.B6_UNDERPROVISIONING] = {
        "resolved": True,
        "lower": 2.0,
        "upper": 2.0,
    }
    cell["common_pi_multimetric_witnesses"]["b6_capacity"][
        "status"
    ] = "compatible"
    cell["classification"] = {
        "classification": identification.B6_SPECIFIC,
        "identified": True,
        "reason": "b6_capacity_or_service_risk_robust_positive",
        "common_pi_branch": "b6_capacity",
    }
    _install_package_authority(monkeypatch, authoritative)

    with pytest.raises(ValueError, match="drifted from the canonical package"):
        build_report_from_identification_payload(
            forged,
            package_directory=tmp_path,
            package_manifest_sha256=TEST_PACKAGE_MANIFEST_SHA256,
        )


def test_report_validator_rejects_coordinated_classification_and_provenance_forgery(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = _synthetic_identification_payload()
    report = _build_authoritative_report(
        payload,
        monkeypatch=monkeypatch,
        package_directory=tmp_path,
    )
    cell = report["exclusive_attribution_by_cell"]["cells"][0]
    cell.update(
        {
            "classification": identification.B6_SPECIFIC,
            "identified": True,
            "reason": "b6_capacity_or_service_risk_robust_positive",
            "common_pi_branch": "b6_capacity",
        }
    )
    counts = report["exclusive_attribution_by_cell"]["classification_counts"]
    counts[identification.NO_MECHANISM] = 0
    counts[identification.B6_SPECIFIC] = 1
    report["negative_and_unresolved_cell_inventory"]["negative_cell_ids"] = []
    report["provenance"]["source_provenance"] = {"forged": True}
    report["identification_evidence"]["upstream_provenance_sha256"] = "b" * 64

    with pytest.raises(ValueError, match="drifted from canonical identification"):
        _validate_authoritative_report(
            report,
            payload,
            package_directory=tmp_path,
        )


def test_debt_certificate_and_report_value_tamper_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    authoritative = _synthetic_identification_payload(debt=1.0)
    forged_payload = copy.deepcopy(authoritative)
    metric = identification.DESCRIPTIVE_DEBT_METRICS[0]
    forged_payload["cells"][0]["descriptive_recovery_debt_bounds"][metric][
        "lower"
    ]["value"] = 999.0
    _install_package_authority(monkeypatch, authoritative)
    with pytest.raises(ValueError, match="drifted from the canonical package"):
        build_report_from_identification_payload(
            forged_payload,
            package_directory=tmp_path,
            package_manifest_sha256=TEST_PACKAGE_MANIFEST_SHA256,
        )

    report = _build_authoritative_report(
        authoritative,
        monkeypatch=monkeypatch,
        package_directory=tmp_path,
    )
    report["descriptive_recovery_debt"]["by_cell"]["base"]["bounds"][metric][
        "upper"
    ]["value"] = 999.0
    with pytest.raises(ValueError, match="drifted from canonical identification"):
        _validate_authoritative_report(
            report,
            authoritative,
            package_directory=tmp_path,
        )


def test_report_validator_rejects_missing_identification_or_package_authority() -> None:
    payload = _synthetic_identification_payload()
    with pytest.raises(ValueError, match="upstream package authority is required"):
        build_report_from_identification_payload(payload)
    with pytest.raises(ValueError, match="identification payload.*required"):
        validate_identification_report({})


@pytest.mark.parametrize(
    "mutation",
    (
        "count",
        "negative_inventory",
        "cell_category",
        "identified_semantics",
        "debt_cell",
        "debt_metric",
        "right_censor",
        "E0",
        "provenance",
    ),
)
def test_report_rebuild_validator_rejects_tamper(
    mutation: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = _synthetic_identification_payload()
    report = _build_authoritative_report(
        payload,
        monkeypatch=monkeypatch,
        package_directory=tmp_path,
    )
    if mutation == "count":
        report["exclusive_attribution_by_cell"]["classification_counts"][
            identification.NO_MECHANISM
        ] = 0
    elif mutation == "negative_inventory":
        report["negative_and_unresolved_cell_inventory"]["negative_cell_ids"] = []
    elif mutation == "cell_category":
        report["exclusive_attribution_by_cell"]["cells"][0][
            "classification"
        ] = identification.UNRESOLVED
    elif mutation == "identified_semantics":
        report["exclusive_attribution_by_cell"]["cells"][0]["identified"] = False
    elif mutation == "debt_cell":
        report["descriptive_recovery_debt"]["by_cell"] = {"other": {}}
    elif mutation == "debt_metric":
        report["descriptive_recovery_debt"]["by_cell"]["base"]["bounds"].pop(
            identification.DESCRIPTIVE_DEBT_METRICS[0]
        )
    elif mutation == "right_censor":
        report["descriptive_recovery_debt"]["by_cell"]["base"][
            "right_censored_pair_ids"
        ] *= 2
    elif mutation == "E0":
        report["E0_outcomes"]["conditional_service_metrics_defined"] = True
    else:
        report["provenance"]["claim"] = True
    with pytest.raises(ValueError, match="drifted from canonical identification"):
        _validate_authoritative_report(
            report,
            payload,
            package_directory=tmp_path,
        )


def test_adapter_preserves_proven_training_infeasible_as_undefined(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    documents = _synthetic_package_documents()
    documents["four_arm_pairwise_outcomes"]["pairs"] = []
    documents["E0_outcomes"]["pairs"] = []
    for name in ("four_arm_training_status", "four_arm_minimum_flexibility"):
        documents[name]["cells"][0]["disposition"] = identification.TRAINING_INFEASIBLE
    for arm in documents["four_arm_training_status"]["cells"][0]["arms"]:
        arm["status"] = "not_applicable"
        arm["pair_count"] = None
        arm["reason"] = "planning_estimand_undefined"

    result = identification._identify_validated_package_documents(
        package_validation=_synthetic_package_validation(),
        package_documents=documents,
        package_manifest_sha256=TEST_PACKAGE_MANIFEST_SHA256,
        stable_snapshot_verified=True,
    )

    cell = result["cells"][0]
    assert cell["classification"]["classification"] == identification.TRAINING_INFEASIBLE
    assert cell["scalar_transport_endpoints"] == {}
    assert cell["common_pi_multimetric_witnesses"] == {}
    report = _build_authoritative_report(
        result,
        monkeypatch=monkeypatch,
        package_directory=tmp_path,
    )
    assert (
        _validate_authoritative_report(
            report,
            result,
            package_directory=tmp_path,
        )
        == report
    )
    assert report["negative_and_unresolved_cell_inventory"][
        "training_infeasible_undefined_cell_ids"
    ] == ["base"]


def test_successor_contract_is_validate_only_with_future_T1_inputs() -> None:
    config = yaml.safe_load(SUCCESSOR_CONFIG.read_text(encoding="utf-8"))
    assert config["activation_authority"] == {
        "path": None,
        "sha256": None,
        "activated": False,
    }
    assert not any(config["gates"].values())
    assert config["upstream_four_arm_package"]["path"] is None
    assert config["upstream_four_arm_package"]["ready"] is False
    t1 = config["registered_estimands"]["T1_mw_only_reference"]
    assert t1["raw_grid_call_trajectory_path"] is None
    assert t1["raw_cfe_call_trajectory_path"] is None
    assert t1["derivation_from_pairwise_outcomes_allowed"] is False
    machine = config["machine_contract"]
    assert machine["report_sections"][0] == "identification_evidence"
    assert machine["canonical_package_reidentification_before_report_required"] is True
    assert machine["standalone_report_scientific_validation_allowed"] is False
    assert machine["synthetic_document_adapter_is_public_validation_authority"] is False


def test_pure_validator_has_zero_solver_calls_and_zero_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tree = ast.parse(SUCCESSOR_VALIDATOR.read_text(encoding="utf-8"))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any(name.startswith(("src", "scipy", "numpy")) for name in imports)
    namespace = _validator_namespace()
    monkeypatch.setattr(Path, "write_text", lambda *args, **kwargs: pytest.fail("write"))
    monkeypatch.setattr(Path, "write_bytes", lambda *args, **kwargs: pytest.fail("write"))
    result = namespace["validate"](SUCCESSOR_CONFIG, SUCCESSOR_MANIFEST)
    assert result["validation_passed"] is True
    assert result["solver_calls"] == 0
    assert result["result_files_written"] == 0
    assert result["upstream_package_ready"] is False
    assert result["activation_authority_present"] is False


def test_validator_rejects_alternate_self_signed_config_and_manifest(
    tmp_path: Path,
) -> None:
    config = yaml.safe_load(SUCCESSOR_CONFIG.read_text(encoding="utf-8"))
    config["activation_authority"] = {
        "path": "forged-activation.json",
        "sha256": "7" * 64,
        "activated": True,
    }
    config["gates"]["execution_ready"] = True
    config_path = tmp_path / "alternate.yaml"
    config_path.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    manifest = json.loads(SUCCESSOR_MANIFEST.read_text(encoding="utf-8"))
    manifest["files"][
        "configs/rq2_public_baseline_robustness_identification_successor_v1.yaml"
    ] = hashlib.sha256(config_path.read_bytes()).hexdigest()
    manifest_path = tmp_path / "alternate.SHA256SUMS.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    namespace = _validator_namespace()
    with pytest.raises(ValueError, match="canonical repository file"):
        namespace["validate"](config_path, manifest_path)


def test_validator_rejects_manifest_tamper_and_reparse_component(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = json.loads(SUCCESSOR_MANIFEST.read_text(encoding="utf-8"))
    manifest["files"].pop(next(iter(manifest["files"])))
    manifest_path = tmp_path / "tampered.SHA256SUMS.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    namespace = _validator_namespace()
    with pytest.raises(ValueError, match="canonical repository file"):
        namespace["validate"](SUCCESSOR_CONFIG, manifest_path)

    real_reparse = namespace["_is_reparse"]
    monkeypatch.setitem(
        namespace,
        "_is_reparse",
        lambda path: Path(path) == SUCCESSOR_CONFIG or real_reparse(path),
    )
    with pytest.raises(ValueError, match="reparse component"):
        namespace["validate"](SUCCESSOR_CONFIG, SUCCESSOR_MANIFEST)


def test_identify_final_package_rejects_capture_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    member_bytes = {}
    for name in identification.PACKAGE_SCHEMAS:
        payload = b"{}"
        (tmp_path / f"{name}.json").write_bytes(payload)
        member_bytes[f"{name}.json"] = hashlib.sha256(payload).hexdigest()
    manifest_path = tmp_path / "SHA256SUMS.json"
    manifest_path.write_text(
        json.dumps(
            {"schema": "rq2_baseline_package_manifest_v1", "files": member_bytes}
        ),
        encoding="utf-8",
    )
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    validation = _synthetic_package_validation()
    calls = 0

    def fake_validate(directory: Path) -> dict[str, object]:
        nonlocal calls
        assert directory == tmp_path
        calls += 1
        if calls == 2:
            manifest_path.write_text(
                manifest_path.read_text(encoding="utf-8") + " ", encoding="utf-8"
            )
        return validation

    monkeypatch.setattr(package, "validate_final_package", fake_validate)
    with pytest.raises(ValueError, match="manifest drifted during capture"):
        identification.identify_final_package(
            tmp_path,
            expected_manifest_sha256=manifest_sha256,
        )


def test_identify_final_package_requires_matching_manifest_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = {}
    for name in identification.PACKAGE_SCHEMAS:
        payload = b"{}"
        (tmp_path / f"{name}.json").write_bytes(payload)
        files[f"{name}.json"] = hashlib.sha256(payload).hexdigest()
    (tmp_path / "SHA256SUMS.json").write_text(
        json.dumps({"schema": "rq2_baseline_package_manifest_v1", "files": files}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        package,
        "validate_final_package",
        lambda directory: _synthetic_package_validation(),
    )

    with pytest.raises(ValueError, match="supplied authority"):
        identification.identify_final_package(
            tmp_path,
            expected_manifest_sha256="f" * 64,
        )


def test_identify_final_package_rejects_captured_member_hash_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = {}
    for name in identification.PACKAGE_SCHEMAS:
        payload = b"{}"
        (tmp_path / f"{name}.json").write_bytes(payload)
        files[f"{name}.json"] = "0" * 64
    manifest_path = tmp_path / "SHA256SUMS.json"
    manifest_path.write_text(
        json.dumps({"schema": "rq2_baseline_package_manifest_v1", "files": files}),
        encoding="utf-8",
    )
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    monkeypatch.setattr(
        package,
        "validate_final_package",
        lambda directory: _synthetic_package_validation(),
    )
    with pytest.raises(ValueError, match="captured package member hash drifted"):
        identification.identify_final_package(
            tmp_path,
            expected_manifest_sha256=manifest_sha256,
        )


def test_identify_final_package_rejects_member_drift_after_second_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    files = {}
    for name in identification.PACKAGE_SCHEMAS:
        payload = b"{}"
        (tmp_path / f"{name}.json").write_bytes(payload)
        files[f"{name}.json"] = hashlib.sha256(payload).hexdigest()
    manifest_path = tmp_path / "SHA256SUMS.json"
    manifest_path.write_text(
        json.dumps({"schema": "rq2_baseline_package_manifest_v1", "files": files}),
        encoding="utf-8",
    )
    manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    calls = 0

    def fake_validate(directory: Path) -> dict[str, object]:
        nonlocal calls
        assert directory == tmp_path
        calls += 1
        if calls == 2:
            (tmp_path / "provenance.json").write_bytes(b'{"drifted":true}')
        return _synthetic_package_validation()

    monkeypatch.setattr(package, "validate_final_package", fake_validate)
    with pytest.raises(ValueError, match="package member drifted during capture"):
        identification.identify_final_package(
            tmp_path,
            expected_manifest_sha256=manifest_sha256,
        )
