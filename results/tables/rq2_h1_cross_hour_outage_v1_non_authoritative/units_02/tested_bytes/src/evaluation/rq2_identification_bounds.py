"""Partial-identification rules for RQ2 under unknown marginal coupling."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

IDENTIFIED_R1 = "identified_R1_no_conflict"
IDENTIFIED_R2 = "identified_R2_double_commitment_risk"
IDENTIFIED_R3 = "identified_R3_common_insufficiency"
PARTIALLY_IDENTIFIED = "partially_identified"
UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class Interval:
    lower: float
    upper: float


@dataclass(frozen=True)
class IdentificationInputs:
    delta_failure_probability: Interval
    delta_expected_shortfall: Interval
    flexibility_underprovisioning: Interval
    correct_failure_probability: Interval
    correct_expected_shortfall: Interval
    all_optimization_resolved: bool
    delta_peak_recovery_debt: Interval = Interval(0.0, 0.0)
    delta_terminal_recovery_debt: Interval = Interval(0.0, 0.0)


@dataclass(frozen=True)
class IdentificationResult:
    classification: str
    identified: bool
    compatible_regions: tuple[str, ...]
    reason: str


def _validate_interval(name: str, interval: Interval) -> None:
    if not isfinite(interval.lower) or not isfinite(interval.upper):
        raise ValueError(f"{name} bounds must be finite")
    if interval.lower > interval.upper:
        raise ValueError(f"{name} lower bound exceeds upper bound")


def _contains_zero(interval: Interval, tolerance: float) -> bool:
    return interval.lower <= tolerance and interval.upper >= -tolerance


def classify_identification_bounds(
    inputs: IdentificationInputs,
    *,
    probability_tolerance: float = 1.0e-9,
    outcome_tolerance: float = 1.0e-6,
) -> IdentificationResult:
    """Classify only conclusions that hold over the complete ambiguity set."""

    intervals = {
        "delta_failure_probability": inputs.delta_failure_probability,
        "delta_expected_shortfall": inputs.delta_expected_shortfall,
        "flexibility_underprovisioning": inputs.flexibility_underprovisioning,
        "correct_failure_probability": inputs.correct_failure_probability,
        "correct_expected_shortfall": inputs.correct_expected_shortfall,
        "delta_peak_recovery_debt": inputs.delta_peak_recovery_debt,
        "delta_terminal_recovery_debt": inputs.delta_terminal_recovery_debt,
    }
    for name, interval in intervals.items():
        _validate_interval(name, interval)
    if (
        not isfinite(probability_tolerance)
        or probability_tolerance < 0.0
        or not isfinite(outcome_tolerance)
        or outcome_tolerance < 0.0
    ):
        raise ValueError("tolerances must be finite and nonnegative")
    if not inputs.all_optimization_resolved:
        return IdentificationResult(
            classification=UNRESOLVED,
            identified=False,
            compatible_regions=(),
            reason="at_least_one_bound_optimization_unresolved",
        )

    delta_probability = inputs.delta_failure_probability
    delta_shortfall = inputs.delta_expected_shortfall
    capacity = inputs.flexibility_underprovisioning
    weak_dominance_everywhere = (
        delta_probability.lower >= -probability_tolerance
        and delta_shortfall.lower >= -outcome_tolerance
        and capacity.lower >= -outcome_tolerance
        and inputs.delta_peak_recovery_debt.lower >= -outcome_tolerance
        and inputs.delta_terminal_recovery_debt.lower >= -outcome_tolerance
    )
    strict_worsening_everywhere = (
        delta_probability.lower > probability_tolerance
        or delta_shortfall.lower > outcome_tolerance
        or capacity.lower > outcome_tolerance
        or inputs.delta_peak_recovery_debt.lower > outcome_tolerance
        or inputs.delta_terminal_recovery_debt.lower > outcome_tolerance
    )
    if weak_dominance_everywhere and strict_worsening_everywhere:
        return IdentificationResult(
            classification=IDENTIFIED_R2,
            identified=True,
            compatible_regions=("R2_double_commitment_risk",),
            reason="b6_is_weakly_dominated_and_strictly_worse_over_all_couplings",
        )

    deltas_zero_everywhere = (
        abs(delta_probability.lower) <= probability_tolerance
        and abs(delta_probability.upper) <= probability_tolerance
        and abs(delta_shortfall.lower) <= outcome_tolerance
        and abs(delta_shortfall.upper) <= outcome_tolerance
        and abs(capacity.lower) <= outcome_tolerance
        and abs(capacity.upper) <= outcome_tolerance
        and abs(inputs.delta_peak_recovery_debt.lower) <= outcome_tolerance
        and abs(inputs.delta_peak_recovery_debt.upper) <= outcome_tolerance
        and abs(inputs.delta_terminal_recovery_debt.lower) <= outcome_tolerance
        and abs(inputs.delta_terminal_recovery_debt.upper) <= outcome_tolerance
    )
    correct_fails_everywhere = (
        inputs.correct_failure_probability.lower > probability_tolerance
        or inputs.correct_expected_shortfall.lower > outcome_tolerance
    )
    correct_succeeds_everywhere = (
        inputs.correct_failure_probability.upper <= probability_tolerance
        and inputs.correct_expected_shortfall.upper <= outcome_tolerance
    )
    if deltas_zero_everywhere and correct_fails_everywhere:
        return IdentificationResult(
            classification=IDENTIFIED_R3,
            identified=True,
            compatible_regions=("R3_common_insufficiency",),
            reason="both_policies_fail_equivalently_over_all_couplings",
        )
    if deltas_zero_everywhere and correct_succeeds_everywhere:
        return IdentificationResult(
            classification=IDENTIFIED_R1,
            identified=True,
            compatible_regions=("R1_no_conflict",),
            reason="both_policies_succeed_equivalently_over_all_couplings",
        )

    delta_zero_is_compatible = (
        _contains_zero(delta_probability, probability_tolerance)
        and _contains_zero(delta_shortfall, outcome_tolerance)
        and _contains_zero(capacity, outcome_tolerance)
        and _contains_zero(inputs.delta_peak_recovery_debt, outcome_tolerance)
        and _contains_zero(
            inputs.delta_terminal_recovery_debt,
            outcome_tolerance,
        )
    )
    correct_success_is_compatible = (
        _contains_zero(
            inputs.correct_failure_probability,
            probability_tolerance,
        )
        and _contains_zero(
            inputs.correct_expected_shortfall,
            outcome_tolerance,
        )
    )
    compatible = []
    if delta_zero_is_compatible and correct_success_is_compatible:
        compatible.append("R1_no_conflict")
    if (
        delta_probability.upper >= -probability_tolerance
        and delta_shortfall.upper >= -outcome_tolerance
        and capacity.upper >= -outcome_tolerance
        and inputs.delta_peak_recovery_debt.upper >= -outcome_tolerance
        and inputs.delta_terminal_recovery_debt.upper >= -outcome_tolerance
        and (
            delta_probability.upper > probability_tolerance
            or delta_shortfall.upper > outcome_tolerance
            or capacity.upper > outcome_tolerance
            or inputs.delta_peak_recovery_debt.upper > outcome_tolerance
            or inputs.delta_terminal_recovery_debt.upper > outcome_tolerance
        )
    ):
        compatible.append("R2_double_commitment_risk")
    if (
        delta_zero_is_compatible
        and (
            inputs.correct_failure_probability.upper > probability_tolerance
            or inputs.correct_expected_shortfall.upper > outcome_tolerance
        )
    ):
        compatible.append("R3_common_insufficiency")
    return IdentificationResult(
        classification=PARTIALLY_IDENTIFIED,
        identified=False,
        compatible_regions=tuple(compatible),
        reason="ambiguity_set_spans_multiple_or_directionally_inconsistent_regions",
    )
