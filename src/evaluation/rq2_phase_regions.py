"""Fail-closed classification for the three-region RQ2 phase diagram."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

REGION_NO_CONFLICT = "R1_no_conflict"
REGION_DOUBLE_COMMITMENT = "R2_double_commitment_risk"
REGION_COMMON_INSUFFICIENCY = "R3_common_insufficiency"
REGION_MIXED = "diagnostic_mixed"
REGION_UNRESOLVED = "unresolved"
PHASE_REGIONS = (
    REGION_NO_CONFLICT,
    REGION_DOUBLE_COMMITMENT,
    REGION_COMMON_INSUFFICIENCY,
)


@dataclass(frozen=True)
class PhaseRegionInputs:
    correct_training_feasible: bool
    b6_training_feasible: bool
    correct_training_unresolved: bool
    b6_training_unresolved: bool
    h2_evaluated: bool
    correct_failure_probability: float
    b6_failure_probability: float
    correct_expected_shortfall_mwh: float
    b6_expected_shortfall_mwh: float
    correct_committed_flexibility_mw: float | None
    b6_committed_flexibility_mw: float | None


@dataclass(frozen=True)
class PhaseRegionResult:
    region: str
    scientific_region: bool
    reason: str
    delta_failure_probability: float | None
    delta_expected_shortfall_mwh: float | None
    flexibility_underprovisioning_mw: float | None


def classify_phase_region(
    inputs: PhaseRegionInputs,
    *,
    probability_tolerance: float = 1.0e-9,
    energy_tolerance_mwh: float = 1.0e-6,
    capacity_tolerance_mw: float = 1.0e-6,
) -> PhaseRegionResult:
    """Classify one cell without forcing unresolved or contradictory evidence."""

    numeric = (
        inputs.correct_failure_probability,
        inputs.b6_failure_probability,
        inputs.correct_expected_shortfall_mwh,
        inputs.b6_expected_shortfall_mwh,
        probability_tolerance,
        energy_tolerance_mwh,
        capacity_tolerance_mw,
    )
    if any(not isfinite(value) or value < 0.0 for value in numeric):
        raise ValueError("phase-region metrics and tolerances must be finite")
    if inputs.correct_training_unresolved or inputs.b6_training_unresolved:
        return PhaseRegionResult(
            region=REGION_UNRESOLVED,
            scientific_region=False,
            reason="training_solver_unresolved",
            delta_failure_probability=None,
            delta_expected_shortfall_mwh=None,
            flexibility_underprovisioning_mw=None,
        )
    if not inputs.correct_training_feasible and not inputs.b6_training_feasible:
        return PhaseRegionResult(
            region=REGION_COMMON_INSUFFICIENCY,
            scientific_region=True,
            reason="both_training_models_proven_infeasible",
            delta_failure_probability=None,
            delta_expected_shortfall_mwh=None,
            flexibility_underprovisioning_mw=None,
        )
    if not inputs.correct_training_feasible and inputs.b6_training_feasible:
        return PhaseRegionResult(
            region=REGION_DOUBLE_COMMITMENT,
            scientific_region=True,
            reason="b6_certifies_when_shared_envelope_is_infeasible",
            delta_failure_probability=None,
            delta_expected_shortfall_mwh=None,
            flexibility_underprovisioning_mw=None,
        )
    if inputs.correct_training_feasible and not inputs.b6_training_feasible:
        return PhaseRegionResult(
            region=REGION_MIXED,
            scientific_region=False,
            reason="unexpected_b6_only_training_infeasibility",
            delta_failure_probability=None,
            delta_expected_shortfall_mwh=None,
            flexibility_underprovisioning_mw=None,
        )
    if not inputs.h2_evaluated:
        return PhaseRegionResult(
            region=REGION_UNRESOLVED,
            scientific_region=False,
            reason="holdout_not_fully_evaluable",
            delta_failure_probability=None,
            delta_expected_shortfall_mwh=None,
            flexibility_underprovisioning_mw=None,
        )

    delta_failure = inputs.b6_failure_probability - inputs.correct_failure_probability
    delta_shortfall = (
        inputs.b6_expected_shortfall_mwh - inputs.correct_expected_shortfall_mwh
    )
    if (
        inputs.correct_committed_flexibility_mw is None
        or inputs.b6_committed_flexibility_mw is None
    ):
        return PhaseRegionResult(
            region=REGION_UNRESOLVED,
            scientific_region=False,
            reason="missing_committed_flexibility",
            delta_failure_probability=delta_failure,
            delta_expected_shortfall_mwh=delta_shortfall,
            flexibility_underprovisioning_mw=None,
        )
    underprovisioning = (
        inputs.correct_committed_flexibility_mw - inputs.b6_committed_flexibility_mw
    )
    b6_not_better = (
        delta_failure >= -probability_tolerance
        and delta_shortfall >= -energy_tolerance_mwh
        and underprovisioning >= -capacity_tolerance_mw
    )
    b6_strictly_worse = (
        delta_failure > probability_tolerance
        or delta_shortfall > energy_tolerance_mwh
        or underprovisioning > capacity_tolerance_mw
    )
    if b6_not_better and b6_strictly_worse:
        return PhaseRegionResult(
            region=REGION_DOUBLE_COMMITMENT,
            scientific_region=True,
            reason="b6_weakly_dominated_with_strict_capacity_or_service_loss",
            delta_failure_probability=delta_failure,
            delta_expected_shortfall_mwh=delta_shortfall,
            flexibility_underprovisioning_mw=underprovisioning,
        )

    correct_fails = (
        inputs.correct_failure_probability > probability_tolerance
        or inputs.correct_expected_shortfall_mwh > energy_tolerance_mwh
    )
    equivalent = (
        abs(delta_failure) <= probability_tolerance
        and abs(delta_shortfall) <= energy_tolerance_mwh
        and abs(underprovisioning) <= capacity_tolerance_mw
    )
    if equivalent and correct_fails:
        return PhaseRegionResult(
            region=REGION_COMMON_INSUFFICIENCY,
            scientific_region=True,
            reason="both_policies_fail_equivalently_under_shared_execution",
            delta_failure_probability=delta_failure,
            delta_expected_shortfall_mwh=delta_shortfall,
            flexibility_underprovisioning_mw=underprovisioning,
        )
    if equivalent:
        return PhaseRegionResult(
            region=REGION_NO_CONFLICT,
            scientific_region=True,
            reason="both_policies_succeed_equivalently",
            delta_failure_probability=delta_failure,
            delta_expected_shortfall_mwh=delta_shortfall,
            flexibility_underprovisioning_mw=underprovisioning,
        )
    return PhaseRegionResult(
        region=REGION_MIXED,
        scientific_region=False,
        reason="metrics_are_not_order_consistent",
        delta_failure_probability=delta_failure,
        delta_expected_shortfall_mwh=delta_shortfall,
        flexibility_underprovisioning_mw=underprovisioning,
    )
