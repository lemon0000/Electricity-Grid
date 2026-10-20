"""Pure report payload for RQ2 four-arm partial identification."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from math import isfinite
from pathlib import Path

from src.evaluation.rq2_baseline_robustness_identification_v1 import (
    ATTRIBUTION_PRIORITY,
    B6_JOINT_FAILURE,
    B6_JOINT_SHORTFALL,
    B6_SPECIFIC,
    B6_UNDERPROVISIONING,
    CATEGORY_DECIDING_METRICS,
    CFE_FAILURE,
    CFE_SHORTFALL,
    COMMON_PI_BRANCHES,
    COMPARISON_TOLERANCE,
    DESCRIPTIVE_DEBT_METRICS,
    EXOGENOUS_GRID_INFEASIBILITY,
    FINITE_GRID_NEED,
    JOINT_FAILURE,
    JOINT_INTERACTION_CAPACITY,
    JOINT_ONLY,
    JOINT_SHORTFALL,
    NETWORK_FAILURE,
    NETWORK_SHORTFALL,
    NO_MECHANISM,
    PARTIALLY_IDENTIFIED,
    SINGLE_SERVICE,
    TRAINING_INFEASIBLE,
    UNRESOLVED,
    canonical_identification_payload_sha256,
    classify_registered_attribution,
    validate_identification_payload,
)

CLAIM_GATES_FALSE = {
    "empirical_contract_overlap_or_incidence": False,
    "population_joint_law": False,
    "causal_attribution": False,
    "interconnection_capacity_X_overstatement": False,
    "absolute_Alibaba_MW": False,
    "empirical_outage_probability": False,
    "full_N_minus_1_security_certification": False,
    "AC_security_certification": False,
    "security_certification": False,
    "formal_result": False,
    "claim": False,
}

REPORT_CELL_FIELDS = {
    "cell_id",
    "classification",
    "identified",
    "reason",
    "common_pi_branch",
    "crossing_metrics",
    "certified_incompatible_branches",
}

_IDENTIFIED_CATEGORIES = {
    SINGLE_SERVICE,
    JOINT_ONLY,
    B6_SPECIFIC,
    NO_MECHANISM,
}
_CATEGORY_REASONS = {
    UNRESOLVED: {
        "global_precondition_failed",
        "unknown_training_disposition",
        "scalar_or_common_pi_inventory_unresolved",
        "scalar_transport_certificate_unresolved",
        "exclusive_attribution_conditions_incomplete",
    },
    TRAINING_INFEASIBLE: {
        "proven_training_infeasibility_estimand_undefined",
    },
    SINGLE_SERVICE: {"single_service_risk_robust_positive"},
    JOINT_ONLY: {"joint_only_capacity_or_service_risk_robust_positive"},
    B6_SPECIFIC: {"b6_capacity_or_service_risk_robust_positive"},
    PARTIALLY_IDENTIFIED: {
        "transport_sign_crosses_tolerance",
        "metricwise_statements_lack_one_common_pi",
    },
    NO_MECHANISM: {
        "all_registered_category_determinants_robust_nonpositive",
    },
}
_CATEGORY_BRANCHES = {
    SINGLE_SERVICE: {
        "single_network_failure",
        "single_network_shortfall",
        "single_cfe_failure",
        "single_cfe_shortfall",
    },
    JOINT_ONLY: {"joint_capacity", "joint_failure", "joint_shortfall"},
    B6_SPECIFIC: {"b6_capacity", "b6_failure", "b6_shortfall"},
    NO_MECHANISM: {"no_mechanism"},
}
_PROVENANCE_FIELDS = {
    "schema",
    "resume_identity",
    "source_provenance",
    "formal_result",
    "claim",
}
_SCALAR_CERTIFICATE_FIELDS = {
    "schema",
    "metric",
    "resolved",
    "sharp",
    "unresolved_reason",
    "lower",
    "upper",
}


def _canonical_bytes(value: object) -> bytes:
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError("report evidence is not canonical JSON") from error


def _required_sha256(value: object, label: str) -> str:
    digest = str(value)
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError(f"{label} must be a lowercase SHA256 digest")
    return digest


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return dict(value)


def _sequence(value: object, label: str) -> list[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{label} must be a sequence")
    return list(value)


def _report_cell(value: Mapping[str, object]) -> dict[str, object]:
    item = dict(value)
    required = REPORT_CELL_FIELDS - {
        "crossing_metrics",
        "certified_incompatible_branches",
    }
    if not required <= set(item) <= REPORT_CELL_FIELDS:
        raise ValueError("cell result inventory drifted")
    cell_id = str(item.get("cell_id"))
    classification = item.get("classification")
    if not cell_id or classification not in ATTRIBUTION_PRIORITY:
        raise ValueError("cell result contains an invalid identity or classification")
    identified = item.get("identified")
    reason = item.get("reason")
    common_pi_branch = item.get("common_pi_branch")
    if not isinstance(identified, bool) or not isinstance(reason, str) or not reason:
        raise ValueError("cell result status evidence is incomplete")
    if common_pi_branch is not None and (
        not isinstance(common_pi_branch, str) or not common_pi_branch
    ):
        raise ValueError("cell result common-pi branch is invalid")
    crossing = [
        str(metric)
        for metric in _sequence(item.get("crossing_metrics", ()), "crossing metrics")
    ]
    incompatible = [
        str(branch)
        for branch in _sequence(
            item.get("certified_incompatible_branches", ()),
            "certified incompatible branches",
        )
    ]
    if len(crossing) != len(set(crossing)) or not set(crossing) <= set(
        CATEGORY_DECIDING_METRICS
    ):
        raise ValueError("cell result crossing-metric inventory drifted")
    if len(incompatible) != len(set(incompatible)) or not set(incompatible) <= set(
        COMMON_PI_BRANCHES
    ):
        raise ValueError("cell result incompatible-branch inventory drifted")
    if identified is not (classification in _IDENTIFIED_CATEGORIES):
        raise ValueError("cell result identified semantics drifted")
    if reason not in _CATEGORY_REASONS[classification]:
        raise ValueError("cell result reason semantics drifted")
    expected_branches = _CATEGORY_BRANCHES.get(classification)
    if expected_branches is None:
        if common_pi_branch is not None:
            raise ValueError("cell result common-pi branch semantics drifted")
    elif common_pi_branch not in expected_branches:
        raise ValueError("cell result common-pi branch semantics drifted")
    if classification != PARTIALLY_IDENTIFIED and (crossing or incompatible):
        raise ValueError("non-partial cell contains partial-identification evidence")
    if classification == PARTIALLY_IDENTIFIED:
        if reason == "transport_sign_crosses_tolerance" and not crossing:
            raise ValueError("partial cell is missing crossing evidence")
        if reason == "metricwise_statements_lack_one_common_pi" and not incompatible:
            raise ValueError("partial cell is missing common-pi evidence")
    return {
        "cell_id": cell_id,
        "classification": classification,
        "identified": identified,
        "reason": reason,
        "common_pi_branch": common_pi_branch,
        "crossing_metrics": crossing,
        "certified_incompatible_branches": incompatible,
    }


def _validated_provenance(value: object) -> dict[str, object]:
    provenance = _mapping(value, "provenance")
    if (
        set(provenance) != _PROVENANCE_FIELDS
        or provenance.get("schema") != "provenance"
        or provenance.get("formal_result") is not False
        or provenance.get("claim") is not False
        or not isinstance(provenance.get("resume_identity"), Mapping)
        or not isinstance(provenance.get("source_provenance"), Mapping)
    ):
        raise ValueError("report provenance claim gate or schema drifted")
    return provenance


def _validated_debt_entry(
    value: object,
    *,
    training_infeasible: bool,
) -> dict[str, object]:
    entry = _mapping(value, "descriptive debt cell")
    if set(entry) != {"bounds", "right_censored_pair_ids"}:
        raise ValueError("descriptive debt cell inventory drifted")
    bounds = _mapping(entry["bounds"], "descriptive debt bounds")
    expected_metrics = set() if training_infeasible else set(DESCRIPTIVE_DEBT_METRICS)
    if set(bounds) != expected_metrics:
        raise ValueError("descriptive debt metric inventory drifted")
    for metric, raw_certificate in bounds.items():
        certificate = _mapping(raw_certificate, f"descriptive debt certificate {metric}")
        if (
            set(certificate) != _SCALAR_CERTIFICATE_FIELDS
            or certificate.get("schema")
            != "rq2_baseline_scalar_transport_certificate_v1"
            or certificate.get("metric") != metric
            or not isinstance(certificate.get("resolved"), bool)
            or certificate.get("sharp") is not certificate.get("resolved")
        ):
            raise ValueError("descriptive debt certificate schema drifted")
    right_censored = [
        str(pair_id)
        for pair_id in _sequence(
            entry["right_censored_pair_ids"], "right-censored pair IDs"
        )
    ]
    if (
        any(not pair_id for pair_id in right_censored)
        or len(right_censored) != len(set(right_censored))
        or (training_infeasible and right_censored)
    ):
        raise ValueError("right-censored pair inventory drifted")
    return {"bounds": bounds, "right_censored_pair_ids": right_censored}


def _bound_interval(value: object, metric: str) -> tuple[float, float] | None:
    bound = _mapping(value, f"cell bound {metric}")
    if set(bound) != {"resolved", "lower", "upper"}:
        raise ValueError("cell bound schema drifted")
    if bound["resolved"] is not True:
        if bound["lower"] is not None or bound["upper"] is not None:
            raise ValueError("unresolved cell bound contains endpoint values")
        return None
    lower = float(bound["lower"])
    upper = float(bound["upper"])
    if not isfinite(lower) or not isfinite(upper) or lower > upper:
        raise ValueError("cell bound interval drifted")
    return lower, upper


def _probability_vector(value: object, label: str) -> list[float]:
    probabilities = [float(item) for item in _sequence(value, label)]
    if (
        not probabilities
        or any(not isfinite(item) or item < 0.0 for item in probabilities)
        or abs(sum(probabilities) - 1.0) > 1.0e-9
    ):
        raise ValueError(f"{label} drifted")
    return probabilities


def _validated_marginal_evidence(value: object) -> tuple[dict[str, object], float]:
    marginal = _mapping(value, "marginal evidence")
    if set(marginal) != {
        "row_ids",
        "row_probabilities",
        "row_states",
        "finite_row_ids",
        "finite_row_probabilities",
        "column_ids",
        "column_probabilities",
        "E0_unconditional_probability_mass",
        "E0_conditional_service_metrics_defined",
    } or marginal.get("E0_conditional_service_metrics_defined") is not False:
        raise ValueError("identification payload E0 semantics drifted")
    row_ids = [str(item) for item in _sequence(marginal["row_ids"], "row IDs")]
    row_states = [
        str(item) for item in _sequence(marginal["row_states"], "row states")
    ]
    rows = _probability_vector(marginal["row_probabilities"], "row probabilities")
    column_ids = [
        str(item) for item in _sequence(marginal["column_ids"], "column IDs")
    ]
    _probability_vector(marginal["column_probabilities"], "column probabilities")
    finite_row_ids = [
        str(item)
        for item in _sequence(marginal["finite_row_ids"], "finite row IDs")
    ]
    finite_probabilities = _probability_vector(
        marginal["finite_row_probabilities"], "finite row probabilities"
    )
    if (
        any(not item for item in (*row_ids, *column_ids, *finite_row_ids))
        or len(row_ids) != len(set(row_ids))
        or len(column_ids) != len(set(column_ids))
        or len(finite_row_ids) != len(set(finite_row_ids))
        or len(row_ids) != len(rows)
        or len(row_ids) != len(row_states)
        or len(finite_row_ids) != len(finite_probabilities)
        or any(
            state not in {FINITE_GRID_NEED, EXOGENOUS_GRID_INFEASIBILITY}
            for state in row_states
        )
        or finite_row_ids
        != [
            row_id
            for row_id, state in zip(row_ids, row_states, strict=True)
            if state == FINITE_GRID_NEED
        ]
    ):
        raise ValueError("identification payload marginal inventory drifted")
    e0_mass = float(marginal["E0_unconditional_probability_mass"])
    rebuilt_e0_mass = sum(
        probability
        for probability, state in zip(rows, row_states, strict=True)
        if state == EXOGENOUS_GRID_INFEASIBILITY
    )
    finite_mass = 1.0 - rebuilt_e0_mass
    rebuilt_finite = [
        probability / finite_mass
        for probability, state in zip(rows, row_states, strict=True)
        if state == FINITE_GRID_NEED
    ]
    if (
        not isfinite(e0_mass)
        or not 0.0 <= e0_mass <= 1.0
        or finite_mass <= 1.0e-9
        or abs(e0_mass - rebuilt_e0_mass) > 1.0e-9
        or any(
            abs(observed - expected) > 1.0e-9
            for observed, expected in zip(
                finite_probabilities, rebuilt_finite, strict=True
            )
        )
    ):
        raise ValueError("identification payload E0 mass drifted")
    return marginal, e0_mass


def _metricwise_possible_incompatible_branches(
    bounds: Mapping[str, object],
    branches: Mapping[str, object],
) -> tuple[str, ...]:
    intervals = {
        metric: _bound_interval(bounds[metric], metric)
        for metric in CATEGORY_DECIDING_METRICS
    }
    if any(interval is None for interval in intervals.values()):
        return ()
    typed = {
        metric: interval
        for metric, interval in intervals.items()
        if interval is not None
    }
    singles = (NETWORK_FAILURE, NETWORK_SHORTFALL, CFE_FAILURE, CFE_SHORTFALL)
    joint = (*singles, JOINT_FAILURE, JOINT_SHORTFALL)
    risk_metrics = tuple(
        metric
        for metric in CATEGORY_DECIDING_METRICS
        if metric not in {JOINT_INTERACTION_CAPACITY, B6_UNDERPROVISIONING}
    )
    specs = {
        "single_network_failure": ((), NETWORK_FAILURE),
        "single_network_shortfall": ((), NETWORK_SHORTFALL),
        "single_cfe_failure": ((), CFE_FAILURE),
        "single_cfe_shortfall": ((), CFE_SHORTFALL),
        "joint_capacity": (singles, JOINT_INTERACTION_CAPACITY),
        "joint_failure": (singles, JOINT_FAILURE),
        "joint_shortfall": (singles, JOINT_SHORTFALL),
        "b6_capacity": (joint, B6_UNDERPROVISIONING),
        "b6_failure": (joint, B6_JOINT_FAILURE),
        "b6_shortfall": (joint, B6_JOINT_SHORTFALL),
    }
    possible = []
    for branch_name, (mandatory, candidate) in specs.items():
        branch = _mapping(branches[branch_name], f"common-pi branch {branch_name}")
        if (
            branch.get("status") == "certified_incompatible"
            and typed[candidate][1] > COMPARISON_TOLERANCE
            and all(typed[metric][0] <= COMPARISON_TOLERANCE for metric in mandatory)
        ):
            possible.append(branch_name)
    no_mechanism = _mapping(
        branches["no_mechanism"], "common-pi branch no_mechanism"
    )
    if (
        no_mechanism.get("status") == "certified_incompatible"
        and all(typed[metric][1] <= COMPARISON_TOLERANCE for metric in (
            JOINT_INTERACTION_CAPACITY,
            B6_UNDERPROVISIONING,
        ))
        and all(typed[metric][0] <= COMPARISON_TOLERANCE for metric in risk_metrics)
    ):
        possible.append("no_mechanism")
    return tuple(possible)


def _build_identification_report(
    *,
    expected_cell_ids: Sequence[str],
    cell_results: Sequence[Mapping[str, object]],
    descriptive_debt_by_cell: Mapping[str, object],
    exogenous_grid_infeasibility_mass: float,
    provenance: Mapping[str, object],
    identification_payload_sha256: str,
    upstream_package_manifest_sha256: str,
    upstream_provenance_sha256: str,
) -> dict[str, object]:
    """Build one exhaustive, negative-result-preserving report payload."""

    cells = tuple(str(item) for item in expected_cell_ids)
    if not cells or len(cells) != len(set(cells)):
        raise ValueError("expected cell inventory must be nonempty and unique")
    by_cell = {}
    for raw in cell_results:
        item = _report_cell(raw)
        cell_id = str(item["cell_id"])
        if cell_id in by_cell:
            raise ValueError("cell result inventory contains duplicates")
        by_cell[cell_id] = item
    if set(by_cell) != set(cells):
        raise ValueError("cell result inventory is missing or extra")
    if set(descriptive_debt_by_cell) != set(cells):
        raise ValueError("descriptive debt inventory is missing or extra")
    e0_mass = float(exogenous_grid_infeasibility_mass)
    if not isfinite(e0_mass) or not 0.0 <= e0_mass <= 1.0:
        raise ValueError("E0 probability mass must lie in [0, 1]")
    provenance_mapping = _validated_provenance(provenance)
    payload_digest = _required_sha256(
        identification_payload_sha256, "identification payload SHA256"
    )
    manifest_digest = _required_sha256(
        upstream_package_manifest_sha256, "upstream package manifest SHA256"
    )
    provenance_digest = _required_sha256(
        upstream_provenance_sha256, "upstream provenance SHA256"
    )
    ordered = [by_cell[cell] for cell in cells]
    debt_by_cell = {
        cell: _validated_debt_entry(
            descriptive_debt_by_cell[cell],
            training_infeasible=(
                by_cell[cell]["classification"] == TRAINING_INFEASIBLE
            ),
        )
        for cell in cells
    }
    classification_counts = {
        category: sum(item["classification"] == category for item in ordered)
        for category in ATTRIBUTION_PRIORITY
    }
    inventories = {
        "negative_cell_ids": [
            item["cell_id"]
            for item in ordered
            if item["classification"] == NO_MECHANISM
        ],
        "partially_identified_cell_ids": [
            item["cell_id"]
            for item in ordered
            if item["classification"] == PARTIALLY_IDENTIFIED
        ],
        "training_infeasible_undefined_cell_ids": [
            item["cell_id"]
            for item in ordered
            if item["classification"] == TRAINING_INFEASIBLE
        ],
        "unresolved_cell_ids": [
            item["cell_id"]
            for item in ordered
            if item["classification"] == UNRESOLVED
        ],
    }
    return {
        "schema": "rq2_baseline_robustness_report_v1",
        "identification_evidence": {
            "schema": "rq2_baseline_identification_evidence_v1",
            "identification_payload_sha256": payload_digest,
            "upstream_package_manifest_sha256": manifest_digest,
            "upstream_provenance_sha256": provenance_digest,
            "canonical_package_revalidated": True,
        },
        "exclusive_attribution_by_cell": {
            "schema": "exclusive_attribution_by_cell",
            "priority": list(ATTRIBUTION_PRIORITY),
            "cells": ordered,
            "classification_counts": classification_counts,
        },
        "negative_and_unresolved_cell_inventory": {
            "schema": "negative_and_unresolved_cell_inventory",
            **inventories,
        },
        "descriptive_recovery_debt": {
            "schema": "descriptive_recovery_debt",
            "category_deciding": False,
            "right_censored_terminal_debt_is_failure": False,
            "by_cell": debt_by_cell,
        },
        "E0_outcomes": {
            "schema": "E0_outcomes",
            "unconditional_probability_mass": e0_mass,
            "conditional_service_metrics_defined": False,
            "included_in_R3_common_insufficiency": False,
        },
        "claim_gate_report": {
            "schema": "claim_gate_report",
            **CLAIM_GATES_FALSE,
        },
        "provenance": provenance_mapping,
    }


def _build_report_from_validated_identification_payload(
    payload: Mapping[str, object],
) -> dict[str, object]:
    """Project an already package-revalidated identification payload."""

    identification = dict(payload)
    if set(identification) != {
        "schema",
        "package_validation",
        "upstream_package_authority",
        "marginal_evidence",
        "cells",
        "T1_mw_only_reference",
        "provenance",
        "formal_result",
        "claim",
    }:
        raise ValueError("identification payload inventory drifted")
    if (
        identification["schema"]
        != "rq2_baseline_robustness_identification_payload_v1"
        or identification["formal_result"] is not False
        or identification["claim"] is not False
    ):
        raise ValueError("identification payload authority drifted")
    upstream_authority = _mapping(
        identification["upstream_package_authority"], "upstream package authority"
    )
    if (
        set(upstream_authority)
        != {
            "schema",
            "manifest_sha256",
            "stable_snapshot_verified",
            "package_validation_sha256",
            "provenance_sha256",
        }
        or upstream_authority.get("schema")
        != "rq2_baseline_upstream_package_authority_v1"
        or upstream_authority.get("stable_snapshot_verified") is not True
    ):
        raise ValueError("identification upstream package authority drifted")
    package_validation = _mapping(
        identification["package_validation"], "package validation"
    )
    if (
        set(package_validation)
        != {"schema", "validation_passed", "file_count", "formal_result", "claim"}
        or package_validation.get("schema")
        != "rq2_baseline_package_validation_v1"
        or package_validation.get("validation_passed") is not True
        or package_validation.get("formal_result") is not False
        or package_validation.get("claim") is not False
        or isinstance(package_validation.get("file_count"), bool)
        or not isinstance(package_validation.get("file_count"), int)
        or int(package_validation["file_count"]) < 6
    ):
        raise ValueError("identification package validation authority drifted")
    marginal, e0_mass = _validated_marginal_evidence(
        identification["marginal_evidence"]
    )
    t1 = _mapping(identification["T1_mw_only_reference"], "T1 reference")
    if t1 != {
        "raw_grid_call_trajectory_path": None,
        "raw_cfe_call_trajectory_path": None,
        "implementation_bound": False,
        "status": "future_raw_trajectory_input_required",
    }:
        raise ValueError("identification payload T1 authority drifted")
    cells = []
    debt_by_cell = {}
    expected_cell_ids = []
    for raw in _sequence(identification["cells"], "identification cells"):
        item = _mapping(raw, "identification cell")
        if set(item) != {
            "cell_id",
            "training_disposition",
            "scalar_transport_endpoints",
            "arm_and_contrast_cell_bounds",
            "common_pi_multimetric_witnesses",
            "descriptive_recovery_debt_bounds",
            "right_censored_pair_ids",
            "classification",
        }:
            raise ValueError("identification cell inventory drifted")
        cell_id = str(item["cell_id"])
        if not cell_id or cell_id in debt_by_cell:
            raise ValueError("identification cell identity is empty or duplicated")
        disposition = str(item["training_disposition"])
        if disposition not in {"resolved", TRAINING_INFEASIBLE}:
            raise ValueError("identification training disposition drifted")
        endpoints = _mapping(
            item["scalar_transport_endpoints"], "scalar transport endpoints"
        )
        scalar_bounds = _mapping(
            item["arm_and_contrast_cell_bounds"], "cell scalar bounds"
        )
        branches = _mapping(
            item["common_pi_multimetric_witnesses"], "common-pi branches"
        )
        debt_bounds = _mapping(
            item["descriptive_recovery_debt_bounds"], "debt bounds"
        )
        expected_metric_inventory = (
            set() if disposition == TRAINING_INFEASIBLE else set(CATEGORY_DECIDING_METRICS)
        )
        expected_branch_inventory = (
            set() if disposition == TRAINING_INFEASIBLE else set(COMMON_PI_BRANCHES)
        )
        expected_debt_inventory = (
            set() if disposition == TRAINING_INFEASIBLE else set(DESCRIPTIVE_DEBT_METRICS)
        )
        if (
            set(endpoints) != expected_metric_inventory
            or set(scalar_bounds) != expected_metric_inventory
            or set(branches) != expected_branch_inventory
            or set(debt_bounds) != expected_debt_inventory
        ):
            raise ValueError("identification cell evidence inventory drifted")
        endpoints_resolved = disposition == "resolved"
        for metric, raw_certificate in endpoints.items():
            certificate = _mapping(raw_certificate, f"scalar certificate {metric}")
            if (
                set(certificate) != _SCALAR_CERTIFICATE_FIELDS
                or certificate.get("schema")
                != "rq2_baseline_scalar_transport_certificate_v1"
                or certificate.get("metric") != metric
                or not isinstance(certificate.get("resolved"), bool)
                or certificate.get("sharp") is not certificate.get("resolved")
            ):
                raise ValueError("scalar transport certificate schema drifted")
            endpoints_resolved = endpoints_resolved and certificate["resolved"] is True
        for metric in scalar_bounds:
            if (_bound_interval(scalar_bounds[metric], metric) is None) != (
                not endpoints[metric]["resolved"]
            ):
                raise ValueError("scalar endpoint and bound-view status drifted")
        for branch_name, raw_branch in branches.items():
            branch = _mapping(raw_branch, f"common-pi branch {branch_name}")
            if branch.get("branch") != branch_name or branch.get("status") not in {
                "compatible",
                "not_compatible",
                "certified_incompatible",
                "unknown",
            }:
                raise ValueError("common-pi branch status drifted")
        classification = _mapping(item["classification"], "cell classification")
        classification_expected_fields = {
            "classification",
            "identified",
            "reason",
            "common_pi_branch",
        }
        if classification.get("classification") == PARTIALLY_IDENTIFIED:
            classification_expected_fields |= {
                "crossing_metrics",
                "certified_incompatible_branches",
            }
        if set(classification) != classification_expected_fields:
            raise ValueError("identification classification inventory drifted")
        projected = _report_cell({"cell_id": cell_id, **classification})
        global_preconditions_hold = (
            disposition == "resolved"
            and endpoints_resolved
            and all(
                _mapping(branch, "common-pi branch").get("status") != "unknown"
                for branch in branches.values()
            )
        )
        incompatible = (
            _metricwise_possible_incompatible_branches(scalar_bounds, branches)
            if global_preconditions_hold
            else ()
        )
        rebuilt_classification = classify_registered_attribution(
            training_disposition=disposition,
            scalar_bounds=scalar_bounds,
            common_pi_branches=branches,
            global_preconditions_hold=(
                disposition == TRAINING_INFEASIBLE or global_preconditions_hold
            ),
            metricwise_possible_incompatible_branches=incompatible,
        )
        if classification != rebuilt_classification:
            raise ValueError("identification classification drifted from evidence")
        cells.append(projected)
        right_censored = [
            str(pair_id)
            for pair_id in _sequence(
                item["right_censored_pair_ids"], "right-censored pair IDs"
            )
        ]
        debt_by_cell[cell_id] = _validated_debt_entry(
            {
                "bounds": debt_bounds,
                "right_censored_pair_ids": right_censored,
            },
            training_infeasible=disposition == TRAINING_INFEASIBLE,
        )
        expected_cell_ids.append(cell_id)
    provenance = _validated_provenance(identification["provenance"])
    return _build_identification_report(
        expected_cell_ids=expected_cell_ids,
        cell_results=cells,
        descriptive_debt_by_cell=debt_by_cell,
        exogenous_grid_infeasibility_mass=e0_mass,
        provenance=provenance,
        identification_payload_sha256=(
            canonical_identification_payload_sha256(identification)
        ),
        upstream_package_manifest_sha256=str(
            upstream_authority["manifest_sha256"]
        ),
        upstream_provenance_sha256=str(upstream_authority["provenance_sha256"]),
    )


def build_report_from_identification_payload(
    payload: Mapping[str, object],
    *,
    package_directory: Path | None = None,
    package_manifest_sha256: str | None = None,
) -> dict[str, object]:
    """Reidentify the canonical package, then build a non-publishing report."""

    if package_directory is None or package_manifest_sha256 is None:
        raise ValueError("canonical upstream package authority is required")
    canonical_payload = validate_identification_payload(
        payload,
        package_directory=package_directory,
        package_manifest_sha256=package_manifest_sha256,
    )
    return _build_report_from_validated_identification_payload(canonical_payload)


def validate_identification_report(
    value: Mapping[str, object],
    *,
    identification_payload: Mapping[str, object] | None = None,
    package_directory: Path | None = None,
    package_manifest_sha256: str | None = None,
) -> dict[str, object]:
    """Rebuild all report inventories and fail closed on any drift."""

    if (
        identification_payload is None
        or package_directory is None
        or package_manifest_sha256 is None
    ):
        raise ValueError(
            "identification payload and canonical upstream package authority are required"
        )
    expected_report = build_report_from_identification_payload(
        identification_payload,
        package_directory=package_directory,
        package_manifest_sha256=package_manifest_sha256,
    )
    report = dict(value)
    if _canonical_bytes(report) != _canonical_bytes(expected_report):
        raise ValueError("report drifted from canonical identification evidence")
    if set(report) != {
        "schema",
        "identification_evidence",
        "exclusive_attribution_by_cell",
        "negative_and_unresolved_cell_inventory",
        "descriptive_recovery_debt",
        "E0_outcomes",
        "claim_gate_report",
        "provenance",
    }:
        raise ValueError("report inventory drifted")
    if report["schema"] != "rq2_baseline_robustness_report_v1":
        raise ValueError("report schema drifted")
    evidence = _mapping(report["identification_evidence"], "identification evidence")
    if evidence != expected_report["identification_evidence"]:
        raise ValueError("identification evidence binding drifted")
    attribution = _mapping(
        report["exclusive_attribution_by_cell"], "exclusive attribution"
    )
    if set(attribution) != {
        "schema",
        "priority",
        "cells",
        "classification_counts",
    } or attribution["schema"] != "exclusive_attribution_by_cell":
        raise ValueError("exclusive attribution inventory drifted")
    if attribution["priority"] != list(ATTRIBUTION_PRIORITY):
        raise ValueError("exclusive attribution priority drifted")
    cells = [
        _mapping(item, "report cell")
        for item in _sequence(attribution["cells"], "report cells")
    ]
    if any(set(item) != REPORT_CELL_FIELDS for item in cells):
        raise ValueError("report cell inventory drifted")
    rebuilt_cells = [_report_cell(item) for item in cells]
    if cells != rebuilt_cells:
        raise ValueError("report cell evidence drifted")
    cell_ids = [str(item["cell_id"]) for item in cells]
    if not cell_ids or len(cell_ids) != len(set(cell_ids)):
        raise ValueError("report cell identity is empty or duplicated")
    counts = {
        category: sum(item["classification"] == category for item in cells)
        for category in ATTRIBUTION_PRIORITY
    }
    if attribution["classification_counts"] != counts:
        raise ValueError("classification counts drifted")
    expected_inventories = {
        "negative_cell_ids": [
            item["cell_id"]
            for item in cells
            if item["classification"] == NO_MECHANISM
        ],
        "partially_identified_cell_ids": [
            item["cell_id"]
            for item in cells
            if item["classification"] == PARTIALLY_IDENTIFIED
        ],
        "training_infeasible_undefined_cell_ids": [
            item["cell_id"]
            for item in cells
            if item["classification"] == TRAINING_INFEASIBLE
        ],
        "unresolved_cell_ids": [
            item["cell_id"]
            for item in cells
            if item["classification"] == UNRESOLVED
        ],
    }
    inventories = _mapping(
        report["negative_and_unresolved_cell_inventory"],
        "negative and unresolved inventory",
    )
    if inventories != {
        "schema": "negative_and_unresolved_cell_inventory",
        **expected_inventories,
    }:
        raise ValueError("negative and unresolved inventory drifted")
    gates = report["claim_gate_report"]
    if not isinstance(gates, Mapping) or dict(gates) != {
        "schema": "claim_gate_report",
        **CLAIM_GATES_FALSE,
    }:
        raise ValueError("claim gate report drifted")
    debt = _mapping(report["descriptive_recovery_debt"], "descriptive debt")
    if (
        set(debt) != {
            "schema",
            "category_deciding",
            "right_censored_terminal_debt_is_failure",
            "by_cell",
        }
        or debt.get("schema") != "descriptive_recovery_debt"
        or debt.get("category_deciding") is not False
        or debt.get("right_censored_terminal_debt_is_failure") is not False
    ):
        raise ValueError("descriptive debt semantics drifted")
    debt_by_cell = _mapping(debt["by_cell"], "descriptive debt by cell")
    if set(debt_by_cell) != set(cell_ids):
        raise ValueError("descriptive debt cell inventory drifted")
    rebuilt_debt = {
        cell_id: _validated_debt_entry(
            debt_by_cell[cell_id],
            training_infeasible=(
                cells[cell_ids.index(cell_id)]["classification"]
                == TRAINING_INFEASIBLE
            ),
        )
        for cell_id in cell_ids
    }
    if debt_by_cell != rebuilt_debt:
        raise ValueError("descriptive debt evidence drifted")
    e0 = _mapping(report["E0_outcomes"], "E0 outcomes")
    if set(e0) != {
        "schema",
        "unconditional_probability_mass",
        "conditional_service_metrics_defined",
        "included_in_R3_common_insufficiency",
    } or e0.get("schema") != "E0_outcomes":
        raise ValueError("E0 report inventory drifted")
    mass = float(e0["unconditional_probability_mass"])
    if (
        not isfinite(mass)
        or not 0.0 <= mass <= 1.0
        or e0["conditional_service_metrics_defined"] is not False
        or e0["included_in_R3_common_insufficiency"] is not False
    ):
        raise ValueError("E0 report semantics drifted")
    _validated_provenance(report["provenance"])
    return report
