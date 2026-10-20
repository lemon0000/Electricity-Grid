"""V5 capacity, holdout, transport, and bootstrap semantics for RQ2."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import shutil
import stat
import uuid
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import _highspy, linprog
from scipy.sparse import csr_matrix

from src.models.rq2_joint_deliverability import FOUR_ARM_IDS
from src.solvers.rq2_solver_adapter import Rq2SolverSpec, solver_options

CAPACITY_SYMBOL_BY_ARM = {
    "network_only_shared": "D_N",
    "cfe_only_shared": "D_C",
    "joint_correct_shared": "D_J",
    "joint_b6_separate_planning_shared_execution": "D_B",
}
OPERATIONAL_METRICS = (
    "B6_minus_correct_joint_service_failure",
    "B6_minus_correct_total_service_shortfall",
    "B6_minus_correct_cfe_shortfall",
)
REGISTERED_METRICS = (
    "network_only_joint_service_failure",
    "network_only_hard_grid_failure",
    "network_only_cfe_service_failure",
    "network_only_total_service_shortfall",
    "network_only_cfe_shortfall",
    "cfe_only_joint_service_failure",
    "cfe_only_hard_grid_failure",
    "cfe_only_cfe_service_failure",
    "cfe_only_total_service_shortfall",
    "cfe_only_cfe_shortfall",
    "joint_correct_joint_service_failure",
    "joint_correct_hard_grid_failure",
    "joint_correct_cfe_service_failure",
    "joint_correct_total_service_shortfall",
    "joint_correct_cfe_shortfall",
    "joint_b6_joint_service_failure",
    "joint_b6_hard_grid_failure",
    "joint_b6_cfe_service_failure",
    "joint_b6_total_service_shortfall",
    "joint_b6_cfe_shortfall",
    *OPERATIONAL_METRICS,
)
RESOLVED = "resolved"
STRUCTURAL_INFEASIBLE = "structural_recovery_infeasible_estimand_undefined"
TRAINING_SUPPORT_FAILURE = "training_support_failure_estimand_undefined"
PROVEN_INFEASIBLE = "proven_infeasible_at_registered_cap_estimand_undefined"
UNRESOLVED = "unresolved"
_CAPACITY_STATUSES = {
    RESOLVED,
    STRUCTURAL_INFEASIBLE,
    TRAINING_SUPPORT_FAILURE,
    PROVEN_INFEASIBLE,
    UNRESOLVED,
}
_SOLVER_CERTIFICATE_FIELDS = {
    "arm_id",
    "status",
    "incumbent_capacity",
    "objective_lower_bound",
    "objective_upper_bound",
    "absolute_gap",
    "incumbent_relative_gap",
    "maximum_constraint_residual",
    "termination_condition",
    "solver_status",
    "model_variables",
    "model_constraints",
    "solver_name",
    "solver_version",
    "solver_options",
}
_SIGNED_ATTRIBUTION_LABELS = {
    "joint_extra_requirement",
    "joint_portfolio_relief",
    "joint_interaction_near_zero",
    "joint_interaction_indeterminate",
    "b6_capacity_underprovisioning",
    "b6_capacity_overprovisioning",
    "b6_capacity_near_zero",
    "b6_capacity_indeterminate",
}
OUTPUT_SCHEMAS = {
    "capacity_frontier.json": "rq2_joint_deliverability_capacity_frontier_v3",
    "holdout.json": "rq2_joint_deliverability_holdout_v3",
    "identification.json": "rq2_joint_deliverability_identification_v3",
    "report.json": "rq2_joint_deliverability_report_v3",
    "provenance.json": "rq2_joint_deliverability_provenance_v1",
}


@dataclass(frozen=True)
class CapacityInterval:
    lower: float
    upper: float


@dataclass(frozen=True)
class CellArmCapacity:
    arm_id: str
    status: str
    interval: CapacityInterval | None
    reported_point: float | None
    solver_certificate: Mapping[str, object] | None
    structural_witness: Mapping[str, object] | None
    training_support_failures: tuple[str, ...]


@dataclass(frozen=True)
class TransportEndpoint:
    extremum: str
    value: float
    coupling_row_major: tuple[float, ...]
    dual_equality_variables: tuple[float, ...]
    primal_objective_min_form: float
    dual_objective_min_form: float
    primal_dual_gap: float
    marginal_residual: float
    dual_feasibility_residual: float
    solver_status: str


@dataclass(frozen=True)
class ScalarTransportCertificate:
    schema: str
    metric: str
    resolved: bool
    sharp: bool
    lower: TransportEndpoint | None
    upper: TransportEndpoint | None
    unresolved_reason: str | None


def _finite(raw: object, label: str, *, minimum: float | None = None) -> float:
    if isinstance(raw, bool):
        raise TypeError(f"{label} must be numeric")
    try:
        number = float(raw)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not math.isfinite(number) or (minimum is not None and number < minimum):
        raise ValueError(f"{label} is outside its registered domain")
    return number


def capacity_contrast_intervals(
    bounds: Mapping[str, CapacityInterval | tuple[float, float]],
) -> dict[str, CapacityInterval]:
    """Propagate four certified arm intervals without a nesting assumption."""

    if set(bounds) != {"D_N", "D_C", "D_J", "D_B"}:
        raise ValueError("capacity interval inventory drifted")

    def interval(symbol: str) -> CapacityInterval:
        raw = bounds[symbol]
        if isinstance(raw, CapacityInterval):
            lower, upper = raw.lower, raw.upper
        else:
            lower, upper = raw
        lower = _finite(lower, f"{symbol} lower")
        upper = _finite(upper, f"{symbol} upper")
        if lower > upper:
            raise ValueError(f"{symbol} lower bound exceeds upper bound")
        return CapacityInterval(lower, upper)

    normalized = {symbol: interval(symbol) for symbol in bounds}
    network = normalized["D_N"]
    cfe = normalized["D_C"]
    joint = normalized["D_J"]
    b6 = normalized["D_B"]
    single = CapacityInterval(
        max(network.lower, cfe.lower),
        max(network.upper, cfe.upper),
    )
    return {
        "D_single": single,
        "I_joint": CapacityInterval(
            joint.lower - single.upper,
            joint.upper - single.lower,
        ),
        "I_sep": CapacityInterval(
            b6.lower - single.upper,
            b6.upper - single.lower,
        ),
        "A_B6": CapacityInterval(
            joint.lower - b6.upper,
            joint.upper - b6.lower,
        ),
    }


def classify_interval(
    interval: CapacityInterval | tuple[float, float],
    *,
    tolerance: float = 1.0e-6,
) -> str:
    """Apply the four registered signed interval labels."""

    if not isinstance(interval, CapacityInterval):
        interval = CapacityInterval(*interval)
    lower = _finite(interval.lower, "interval lower")
    upper = _finite(interval.upper, "interval upper")
    threshold = _finite(tolerance, "interval tolerance", minimum=0.0)
    if lower > upper:
        raise ValueError("interval lower bound exceeds upper bound")
    if lower > threshold:
        return "robust_positive"
    if upper < -threshold:
        return "robust_negative"
    if lower >= -threshold and upper <= threshold:
        return "certified_near_zero"
    return "numerically_indeterminate"


def finalize_capacity_certificate(
    *,
    arm_id: str,
    candidate: Mapping[str, object] | None = None,
    structural_witness: Mapping[str, object] | None = None,
    training_support_failures: Sequence[str] = (),
    training_support_unresolved: bool = False,
    tolerance: float = 1.0e-6,
) -> CellArmCapacity:
    """Convert solver and audit evidence into one fail-closed arm estimand."""

    if arm_id not in FOUR_ARM_IDS:
        raise ValueError("unknown arm ID")
    failures = tuple(str(item) for item in training_support_failures)
    if len(set(failures)) != len(failures) or any(not item for item in failures):
        raise ValueError("training support failures are invalid")
    if not isinstance(training_support_unresolved, bool):
        raise TypeError("training-support unresolved flag must be boolean")
    if structural_witness is not None:
        if candidate is not None or failures or training_support_unresolved:
            raise ValueError("structural status cannot carry solver/audit evidence")
        return CellArmCapacity(
            arm_id=arm_id,
            status=STRUCTURAL_INFEASIBLE,
            interval=None,
            reported_point=None,
            solver_certificate=None,
            structural_witness=dict(structural_witness),
            training_support_failures=(),
        )
    if candidate is None:
        return CellArmCapacity(
            arm_id=arm_id,
            status=UNRESOLVED,
            interval=None,
            reported_point=None,
            solver_certificate=None,
            structural_witness=None,
            training_support_failures=failures,
        )
    certificate = dict(candidate)
    if set(certificate) != _SOLVER_CERTIFICATE_FIELDS:
        raise ValueError("solver certificate field inventory drifted")
    if certificate.get("arm_id") != arm_id:
        raise ValueError("solver certificate arm identity drifted")
    for key in ("model_variables", "model_constraints"):
        value_ = certificate[key]
        if isinstance(value_, bool) or not isinstance(value_, int) or value_ <= 0:
            raise ValueError(f"solver certificate {key} is invalid")
    for key in (
        "termination_condition",
        "solver_status",
        "solver_name",
        "solver_version",
    ):
        if not isinstance(certificate[key], str) or not certificate[key]:
            raise ValueError(f"solver certificate {key} is invalid")
    if not isinstance(certificate["solver_options"], Mapping):
        raise TypeError("solver certificate options are invalid")
    candidate_status = certificate.get("status")
    if candidate_status == PROVEN_INFEASIBLE:
        null_numeric_fields = (
            "incumbent_capacity",
            "objective_lower_bound",
            "objective_upper_bound",
            "absolute_gap",
            "incumbent_relative_gap",
            "maximum_constraint_residual",
        )
        if (
            any(certificate[field] is not None for field in null_numeric_fields)
            or certificate["termination_condition"] != "infeasible"
            or certificate["solver_status"] not in {"ok", "warning"}
            or failures
            or training_support_unresolved
        ):
            raise ValueError("proven-infeasible certificate is inconsistent")
        return CellArmCapacity(
            arm_id=arm_id,
            status=PROVEN_INFEASIBLE,
            interval=None,
            reported_point=None,
            solver_certificate=certificate,
            structural_witness=None,
            training_support_failures=(),
        )
    if candidate_status == UNRESOLVED:
        return CellArmCapacity(
            arm_id=arm_id,
            status=UNRESOLVED,
            interval=None,
            reported_point=None,
            solver_certificate=certificate,
            structural_witness=None,
            training_support_failures=failures,
        )
    if candidate_status != "candidate_resolved":
        raise ValueError("solver certificate status is unregistered")
    lower = _finite(
        certificate.get("objective_lower_bound"),
        "objective lower bound",
        minimum=0.0,
    )
    incumbent = _finite(
        certificate.get("incumbent_capacity"),
        "incumbent capacity",
        minimum=0.0,
    )
    upper = _finite(
        certificate.get("objective_upper_bound"),
        "objective upper bound",
        minimum=0.0,
    )
    absolute_gap = _finite(
        certificate.get("absolute_gap"),
        "absolute gap",
        minimum=0.0,
    )
    relative_gap = _finite(
        certificate.get("incumbent_relative_gap"),
        "incumbent relative gap",
        minimum=0.0,
    )
    residual = _finite(
        certificate.get("maximum_constraint_residual"),
        "maximum constraint residual",
        minimum=0.0,
    )
    solver_options = certificate["solver_options"]
    solver_name = certificate["solver_name"]
    gap_key = {"gurobi": "MIPGap", "highs": "mip_rel_gap"}.get(solver_name)
    if gap_key is None or gap_key not in solver_options:
        raise ValueError("resolved capacity certificate has no registered gap option")
    maximum_relative_gap = _finite(
        solver_options[gap_key],
        "solver MIP relative gap",
        minimum=0.0,
    )
    expected_gap = upper - lower
    expected_relative_gap = expected_gap / max(abs(incumbent), 1.0e-12)
    if (
        certificate["termination_condition"] not in {"optimal", "globallyOptimal"}
        or certificate["solver_status"] != "ok"
        or lower > upper
        or lower > incumbent
        or abs(upper - incumbent) > tolerance
        or not math.isclose(
            absolute_gap,
            expected_gap,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
        or not math.isclose(
            relative_gap,
            expected_relative_gap,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
        or relative_gap > maximum_relative_gap + 1.0e-12
        or residual > tolerance
        or incumbent > 1.0 + tolerance
    ):
        raise ValueError("resolved capacity certificate is inconsistent")
    if failures:
        return CellArmCapacity(
            arm_id=arm_id,
            status=TRAINING_SUPPORT_FAILURE,
            interval=None,
            reported_point=None,
            solver_certificate=certificate,
            structural_witness=None,
            training_support_failures=failures,
        )
    if training_support_unresolved:
        return CellArmCapacity(
            arm_id=arm_id,
            status=UNRESOLVED,
            interval=None,
            reported_point=None,
            solver_certificate=certificate,
            structural_witness=None,
            training_support_failures=(),
        )
    return CellArmCapacity(
        arm_id=arm_id,
        status=RESOLVED,
        interval=CapacityInterval(lower, incumbent),
        reported_point=incumbent,
        solver_certificate=certificate,
        structural_witness=None,
        training_support_failures=(),
    )


def capacity_attribution(
    arms: Mapping[str, CellArmCapacity],
    *,
    tolerance: float = 1.0e-6,
) -> dict[str, object]:
    """Build all signed capacity estimands only when all four arms resolve."""

    if set(arms) != set(FOUR_ARM_IDS):
        raise ValueError("four-arm capacity inventory drifted")
    if any(item.status not in _CAPACITY_STATUSES for item in arms.values()):
        raise ValueError("unregistered arm status")
    labels: dict[str, bool | str] = {
        "network_single_service_binding": (
            True
            if arms["network_only_shared"].status
            in {STRUCTURAL_INFEASIBLE, PROVEN_INFEASIBLE}
            else "not_evaluable"
        ),
        "cfe_single_service_binding": (
            True
            if arms["cfe_only_shared"].status
            in {STRUCTURAL_INFEASIBLE, PROVEN_INFEASIBLE}
            else "not_evaluable"
        ),
        **{name: "not_evaluable" for name in _SIGNED_ATTRIBUTION_LABELS},
        "b6_operational_penalty": "not_evaluable",
        "b6_operational_relief": "not_evaluable",
    }
    if any(item.status != RESOLVED or item.interval is None for item in arms.values()):
        return {
            "resolved": False,
            "contrasts": None,
            "interval_labels": None,
            "labels": labels,
            "decomposition_residual": None,
        }
    by_symbol = {
        CAPACITY_SYMBOL_BY_ARM[arm_id]: item.interval
        for arm_id, item in arms.items()
        if item.interval is not None
    }
    contrasts = capacity_contrast_intervals(by_symbol)
    points = {
        CAPACITY_SYMBOL_BY_ARM[arm_id]: float(item.reported_point)
        for arm_id, item in arms.items()
        if item.reported_point is not None
    }
    d_single = max(points["D_N"], points["D_C"])
    i_joint = points["D_J"] - d_single
    i_sep = points["D_B"] - d_single
    a_b6 = points["D_J"] - points["D_B"]
    residual = i_joint - (i_sep + a_b6)
    if abs(residual) > tolerance:
        raise ValueError("point capacity decomposition failed")
    interval_labels = {
        name: classify_interval(interval, tolerance=tolerance)
        for name, interval in contrasts.items()
        if name != "D_single"
    }
    joint_label = interval_labels["I_joint"]
    b6_label = interval_labels["A_B6"]
    labels.update(
        {
            "joint_extra_requirement": joint_label == "robust_positive",
            "joint_portfolio_relief": joint_label == "robust_negative",
            "joint_interaction_near_zero": joint_label == "certified_near_zero",
            "joint_interaction_indeterminate": (
                joint_label == "numerically_indeterminate"
            ),
            "b6_capacity_underprovisioning": b6_label == "robust_positive",
            "b6_capacity_overprovisioning": b6_label == "robust_negative",
            "b6_capacity_near_zero": b6_label == "certified_near_zero",
            "b6_capacity_indeterminate": b6_label == "numerically_indeterminate",
        }
    )
    return {
        "resolved": True,
        "arm_intervals": {
            symbol: asdict(interval) for symbol, interval in by_symbol.items()
        },
        "reported_points": points,
        "contrasts": {name: asdict(interval) for name, interval in contrasts.items()},
        "interval_labels": interval_labels,
        "labels": labels,
        "decomposition_residual": residual,
    }


def finalize_operational_attribution(
    capacity_attribution_payload: Mapping[str, object],
    arm_statuses: Mapping[str, str],
    transport_intervals: Mapping[str, CapacityInterval],
    *,
    tolerance: float = 1.0e-6,
) -> dict[str, object]:
    """Complete the registered attribution vector from certified transport bounds."""

    if set(arm_statuses) != set(FOUR_ARM_IDS):
        raise ValueError("attribution arm status inventory drifted")
    if set(transport_intervals) != set(REGISTERED_METRICS):
        raise ValueError("attribution transport metric inventory drifted")
    result = dict(capacity_attribution_payload)
    raw_labels = result.get("labels")
    if not isinstance(raw_labels, Mapping):
        raise TypeError("capacity attribution labels are missing")
    labels = dict(raw_labels)
    if arm_statuses["network_only_shared"] == RESOLVED:
        labels["network_single_service_binding"] = (
            transport_intervals["network_only_joint_service_failure"].lower > tolerance
        )
    if arm_statuses["cfe_only_shared"] == RESOLVED:
        labels["cfe_single_service_binding"] = (
            transport_intervals["cfe_only_joint_service_failure"].lower > tolerance
        )
    labels.update(
        operational_labels(
            {metric: transport_intervals[metric] for metric in OPERATIONAL_METRICS},
            tolerance=tolerance,
        )
    )
    result["labels"] = labels
    return result


def execute_holdout_policy(
    *,
    committed_capacity: float,
    grid_request: Sequence[float],
    cfe_request: Sequence[float],
    available_flexibility: Sequence[float],
    connected_demand: Sequence[float],
    current_recovery_headroom: Sequence[float],
    maximum_recovery_power: float,
    recovery_efficiency: float,
    maximum_event_duration_hours: float,
    maximum_event_count: int,
    minimum_recovery_hours: float,
    normalized_energy_budget: float,
    normalized_debt_limit: float,
    terminal_recovery_debt_limit: float,
    time_step_hours: float,
    minimum_event_power: float,
    curtailment_ramp_per_hour: float,
    response_time_hours: float,
    service_shortfall_tolerance: float,
) -> dict[str, object]:
    """Execute the registered current-state-only lexicographic policy."""

    length = len(grid_request)
    vectors = {
        "grid request": grid_request,
        "CFE request": cfe_request,
        "available flexibility": available_flexibility,
        "connected demand": connected_demand,
        "recovery headroom": current_recovery_headroom,
    }
    if length == 0 or any(len(vector) != length for vector in vectors.values()):
        raise ValueError("holdout trajectory inventory drifted")
    normalized_vectors = {
        name: tuple(_finite(value, name, minimum=0.0) for value in vector)
        for name, vector in vectors.items()
    }
    capacity = _finite(
        committed_capacity,
        "committed capacity",
        minimum=0.0,
    )
    max_recovery = _finite(
        maximum_recovery_power,
        "maximum recovery power",
        minimum=0.0,
    )
    efficiency = _finite(
        recovery_efficiency,
        "recovery efficiency",
        minimum=0.0,
    )
    max_duration = _finite(
        maximum_event_duration_hours,
        "maximum event duration",
        minimum=0.0,
    )
    minimum_rest = _finite(
        minimum_recovery_hours,
        "minimum recovery hours",
        minimum=0.0,
    )
    energy_budget = _finite(
        normalized_energy_budget,
        "energy budget",
        minimum=0.0,
    )
    debt_limit = _finite(
        normalized_debt_limit,
        "debt limit",
        minimum=0.0,
    )
    terminal_limit = _finite(
        terminal_recovery_debt_limit,
        "terminal debt limit",
        minimum=0.0,
    )
    dt = _finite(time_step_hours, "time step", minimum=0.0)
    minimum_power = _finite(
        minimum_event_power,
        "minimum event power",
        minimum=0.0,
    )
    ramp = _finite(
        curtailment_ramp_per_hour,
        "curtailment ramp",
        minimum=0.0,
    )
    response = _finite(
        response_time_hours,
        "response time",
        minimum=0.0,
    )
    tolerance = _finite(
        service_shortfall_tolerance,
        "service tolerance",
        minimum=0.0,
    )
    if (
        dt <= 0.0
        or minimum_power <= 0.0
        or response <= 0.0
        or ramp <= 0.0
        or not 0.0 < efficiency <= 1.0
        or isinstance(maximum_event_count, bool)
        or not isinstance(maximum_event_count, int)
        or maximum_event_count < 0
    ):
        raise ValueError("holdout scalar contract is invalid")

    raw_grid = normalized_vectors["grid request"]
    raw_cfe = normalized_vectors["CFE request"]
    grid = tuple(0.0 if value <= tolerance else value for value in raw_grid)
    cfe = tuple(0.0 if value <= tolerance else value for value in raw_cfe)
    available = normalized_vectors["available flexibility"]
    connected = normalized_vectors["connected demand"]
    headroom = normalized_vectors["recovery headroom"]

    previous_call = 0.0
    previous_active = False
    active_duration = 0.0
    event_count = 0
    interevent_rest: float | None = None
    cumulative_energy = 0.0
    debt = 0.0
    has_prior_event = False
    peak_debt = 0.0
    trajectory: list[dict[str, object]] = []

    for hour in range(length):
        terminal = hour == length - 1
        can_continue = (
            previous_active and active_duration + dt <= max_duration + 1.0e-12
        )
        can_start = (
            not previous_active
            and event_count < maximum_event_count
            and (
                not has_prior_event
                or (
                    interevent_rest is not None
                    and interevent_rest + 1.0e-12 >= minimum_rest
                )
            )
        )
        active_permitted = not terminal and (can_continue or can_start)
        call_cap = min(
            capacity,
            available[hour],
            connected[hour],
            max(0.0, (energy_budget - cumulative_energy) / dt),
            max(0.0, (debt_limit - debt) / dt),
            previous_call + min(ramp * dt, ramp * response),
        )
        candidate = min(grid[hour] + cfe[hour], max(call_cap, 0.0))
        active = active_permitted and candidate >= minimum_power
        if active:
            grid_served = min(grid[hour], candidate)
            cfe_served = min(cfe[hour], candidate - grid_served)
        else:
            grid_served = 0.0
            cfe_served = 0.0
        total_call = grid_served + cfe_served
        event_start = active and not previous_active
        event_stop = previous_active and not active
        debt_before_recovery = debt + total_call * dt
        recovery = (
            0.0
            if active
            else min(
                max_recovery,
                headroom[hour],
                debt_before_recovery / (efficiency * dt),
            )
        )
        debt_after_recovery = max(
            debt_before_recovery - efficiency * recovery * dt,
            0.0,
        )
        if debt_after_recovery > debt_limit + 1.0e-12:
            raise ValueError("holdout action exceeded the recovery-debt limit")
        next_duration = (
            active_duration + dt
            if active and previous_active
            else (dt if active else 0.0)
        )
        next_event_count = event_count + int(event_start)
        if active:
            next_rest = None
        elif previous_active:
            next_rest = dt
        elif has_prior_event:
            if interevent_rest is None:
                raise ValueError("holdout rest state is inconsistent")
            next_rest = interevent_rest + dt
        else:
            next_rest = None
        next_energy = cumulative_energy + total_call * dt
        next_has_prior_event = has_prior_event or event_start
        peak_debt = max(peak_debt, debt_after_recovery)
        trajectory.append(
            {
                "hour": hour,
                "raw_grid_request": raw_grid[hour],
                "raw_cfe_request": raw_cfe[hour],
                "effective_grid_request": grid[hour],
                "effective_cfe_request": cfe[hour],
                "grid_served": grid_served,
                "cfe_served": cfe_served,
                "total_call": total_call,
                "active": active,
                "event_start": event_start,
                "event_stop": event_stop,
                "recovery": recovery,
                "recovery_debt": debt_after_recovery,
                "active_event_duration": next_duration,
                "event_count": next_event_count,
                "interevent_rest": next_rest,
                "cumulative_call_energy": next_energy,
                "has_prior_event": next_has_prior_event,
            }
        )
        previous_call = total_call
        previous_active = active
        active_duration = next_duration
        event_count = next_event_count
        interevent_rest = next_rest
        cumulative_energy = next_energy
        debt = debt_after_recovery
        has_prior_event = next_has_prior_event

    grid_shortfall = (
        math.fsum(
            max(request - float(row["grid_served"]), 0.0)
            for request, row in zip(grid, trajectory, strict=True)
        )
        * dt
    )
    cfe_shortfall = (
        math.fsum(
            max(request - float(row["cfe_served"]), 0.0)
            for request, row in zip(cfe, trajectory, strict=True)
        )
        * dt
    )
    recovery_failure = debt > terminal_limit + tolerance
    return {
        "schema": "rq2_joint_deliverability_holdout_trajectory_v3",
        "trajectory": trajectory,
        "metrics": {
            "grid_shortfall": grid_shortfall,
            "cfe_shortfall": cfe_shortfall,
            "total_service_shortfall": grid_shortfall + cfe_shortfall,
            "hard_grid_failure": grid_shortfall > tolerance,
            "cfe_service_failure": cfe_shortfall > tolerance,
            "recovery_completion_failure": recovery_failure,
            "joint_service_failure": bool(
                grid_shortfall > tolerance
                or cfe_shortfall > tolerance
                or recovery_failure
            ),
            "peak_recovery_debt": peak_debt,
            "terminal_recovery_debt": debt,
        },
    }


def sealed_holdout_probe_projection(
    outcome: Mapping[str, object],
) -> dict[str, object]:
    """Project the extended trajectory onto the exact sealed V5 golden payload."""

    trajectory_fields = (
        "hour",
        "grid_served",
        "cfe_served",
        "total_call",
        "active",
        "event_start",
        "event_stop",
        "recovery",
        "recovery_debt",
        "active_event_duration",
        "event_count",
        "interevent_rest",
        "cumulative_call_energy",
        "has_prior_event",
    )
    metric_fields = (
        "grid_shortfall",
        "cfe_shortfall",
        "total_service_shortfall",
        "hard_grid_failure",
        "cfe_service_failure",
        "recovery_completion_failure",
        "joint_service_failure",
    )
    trajectory = outcome.get("trajectory")
    metrics = outcome.get("metrics")
    if (
        not isinstance(trajectory, Sequence)
        or isinstance(trajectory, (str, bytes))
        or not isinstance(metrics, Mapping)
    ):
        raise TypeError("holdout outcome cannot be projected onto the sealed probe")
    projected_trajectory = []
    for row in trajectory:
        if not isinstance(row, Mapping) or any(
            field not in row for field in trajectory_fields
        ):
            raise ValueError("holdout trajectory is missing a sealed probe field")
        projected_trajectory.append({field: row[field] for field in trajectory_fields})
    if any(field not in metrics for field in metric_fields):
        raise ValueError("holdout metrics are missing a sealed probe field")
    return {
        "trajectory": projected_trajectory,
        "metrics": {field: metrics[field] for field in metric_fields},
    }


def finite_conditioning(
    row_ids: Sequence[str],
    row_probabilities: Sequence[float],
    state_by_id: Mapping[str, str],
    *,
    tolerance: float = 1.0e-9,
) -> dict[str, object]:
    """Separate E0 mass and return the finite conditional marginal."""

    if (
        not row_ids
        or len(row_ids) != len(row_probabilities)
        or len(set(row_ids)) != len(row_ids)
        or set(row_ids) != set(state_by_id)
    ):
        raise ValueError("power marginal inventory drifted")
    probabilities = tuple(
        _finite(value, "power probability", minimum=0.0) for value in row_probabilities
    )
    if not math.isclose(
        math.fsum(probabilities),
        1.0,
        rel_tol=0.0,
        abs_tol=tolerance,
    ):
        raise ValueError("power probabilities must sum to one")
    e0_mass = math.fsum(
        probability
        for block_id, probability in zip(row_ids, probabilities, strict=True)
        if state_by_id[block_id] == "exogenous_grid_infeasibility"
    )
    if any(
        state not in {"finite_grid_need", "exogenous_grid_infeasibility"}
        for state in state_by_id.values()
    ):
        raise ValueError("power state inventory contains an unresolved state")
    if e0_mass >= 1.0 - tolerance:
        return {
            "status": "finite_service_identification_unresolved",
            "E0_mass": e0_mass,
            "finite_row_ids": [],
            "finite_row_probabilities": [],
            "transport_solver_called": False,
        }
    finite_mass = 1.0 - e0_mass
    finite = tuple(
        (block_id, probability / finite_mass)
        for block_id, probability in zip(row_ids, probabilities, strict=True)
        if state_by_id[block_id] == "finite_grid_need"
    )
    return {
        "status": "resolved",
        "E0_mass": e0_mass,
        "finite_row_ids": [block_id for block_id, _ in finite],
        "finite_row_probabilities": [probability for _, probability in finite],
        "transport_solver_called": None,
    }


def _probabilities(values: Sequence[float], label: str) -> np.ndarray:
    result = np.asarray(values, dtype=np.float64)
    if (
        result.ndim != 1
        or result.size == 0
        or not np.all(np.isfinite(result))
        or np.any(result < 0.0)
        or abs(float(result.sum()) - 1.0) > 1.0e-9
    ):
        raise ValueError(f"{label} must be a finite probability vector")
    return result


def _transport_equalities(
    rows: np.ndarray,
    columns: np.ndarray,
) -> tuple[csr_matrix, np.ndarray]:
    row_count = rows.size
    column_count = columns.size
    constraint_rows: list[int] = []
    variable_columns: list[int] = []
    for row in range(row_count):
        for column in range(column_count):
            constraint_rows.append(row)
            variable_columns.append(row * column_count + column)
    for column in range(column_count - 1):
        for row in range(row_count):
            constraint_rows.append(row_count + column)
            variable_columns.append(row * column_count + column)
    matrix = csr_matrix(
        (
            np.ones(len(constraint_rows), dtype=np.float64),
            (constraint_rows, variable_columns),
        ),
        shape=(row_count + column_count - 1, row_count * column_count),
    )
    return matrix, np.concatenate((rows, columns[:-1]))


def _transport_endpoint(
    objective: np.ndarray,
    a_eq: csr_matrix,
    b_eq: np.ndarray,
    *,
    extremum: str,
    options: Mapping[str, object],
) -> TransportEndpoint:
    result = linprog(
        objective,
        A_eq=a_eq,
        b_eq=b_eq,
        bounds=(0.0, None),
        method="highs-ds",
        options=dict(options),
    )
    if (
        result.success is not True
        or result.status != 0
        or result.x is None
        or result.eqlin.marginals is None
    ):
        raise RuntimeError(f"transport endpoint unresolved: {result.message}")
    primal = np.asarray(result.x, dtype=np.float64)
    dual = np.asarray(result.eqlin.marginals, dtype=np.float64)
    primal_objective = float(objective @ primal)
    dual_objective = float(b_eq @ dual)
    marginal_residual = float(np.max(np.abs(a_eq @ primal - b_eq)))
    dual_residual = max(
        0.0,
        float(np.max(np.asarray(a_eq.T @ dual).ravel() - objective)),
    )
    gap = abs(primal_objective - dual_objective)
    if (
        np.any(primal < -1.0e-9)
        or marginal_residual > 1.0e-8
        or dual_residual > 1.0e-8
        or gap > 1.0e-8
    ):
        raise RuntimeError("transport primal/dual certificate failed")
    return TransportEndpoint(
        extremum=extremum,
        value=(primal_objective if extremum == "lower" else -primal_objective),
        coupling_row_major=tuple(float(value_) for value_ in primal),
        dual_equality_variables=tuple(float(value_) for value_ in dual),
        primal_objective_min_form=primal_objective,
        dual_objective_min_form=dual_objective,
        primal_dual_gap=gap,
        marginal_residual=marginal_residual,
        dual_feasibility_residual=dual_residual,
        solver_status=str(result.message),
    )


def certify_scalar_transport(
    row_probabilities: Sequence[float],
    column_probabilities: Sequence[float],
    metric: Sequence[Sequence[float]],
    *,
    metric_name: str,
    require_registered_environment: bool = True,
) -> ScalarTransportCertificate:
    """Certify both scalar endpoints over the complete transport polytope."""

    if require_registered_environment and os.environ.get("OMP_NUM_THREADS") != "1":
        raise RuntimeError("transport requires OMP_NUM_THREADS=1")
    rows = _probabilities(row_probabilities, "row probabilities")
    columns = _probabilities(column_probabilities, "column probabilities")
    matrix = np.asarray(metric, dtype=np.float64)
    if matrix.shape != (rows.size, columns.size) or not np.all(np.isfinite(matrix)):
        raise ValueError("transport metric shape or values drifted")
    a_eq, b_eq = _transport_equalities(rows, columns)
    options = {
        "presolve": True,
        "dual_feasibility_tolerance": 1.0e-9,
        "primal_feasibility_tolerance": 1.0e-9,
    }
    endpoints: dict[str, TransportEndpoint] = {}
    errors: list[str] = []
    for extremum, objective in (
        ("lower", matrix.ravel()),
        ("upper", -matrix.ravel()),
    ):
        try:
            endpoints[extremum] = _transport_endpoint(
                objective,
                a_eq,
                b_eq,
                extremum=extremum,
                options=options,
            )
        except Exception as error:  # noqa: BLE001 - retain both endpoint attempts
            errors.append(f"{extremum}:{type(error).__name__}:{error}")
    if errors:
        return ScalarTransportCertificate(
            schema="rq2_joint_deliverability_transport_certificate_v3",
            metric=metric_name,
            resolved=False,
            sharp=False,
            lower=endpoints.get("lower"),
            upper=endpoints.get("upper"),
            unresolved_reason=";".join(errors),
        )
    lower = endpoints["lower"]
    upper = endpoints["upper"]
    if lower.value > upper.value + 1.0e-8:
        return ScalarTransportCertificate(
            schema="rq2_joint_deliverability_transport_certificate_v3",
            metric=metric_name,
            resolved=False,
            sharp=False,
            lower=lower,
            upper=upper,
            unresolved_reason="lower_endpoint_exceeds_upper_endpoint",
        )
    return ScalarTransportCertificate(
        schema="rq2_joint_deliverability_transport_certificate_v3",
        metric=metric_name,
        resolved=True,
        sharp=True,
        lower=lower,
        upper=upper,
        unresolved_reason=None,
    )


def validate_transport_runtime(
    expected: Mapping[str, object],
    *,
    require_thread_environment: bool,
) -> dict[str, str]:
    """Verify the exact Python, NumPy, SciPy, and bundled HiGHS identity."""

    observed = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "scipy_bundled_highs": (
            f"{_highspy._core.HIGHS_VERSION_MAJOR}."
            f"{_highspy._core.HIGHS_VERSION_MINOR}."
            f"{_highspy._core.HIGHS_VERSION_PATCH}"
        ),
    }
    if dict(expected) != observed:
        raise RuntimeError(
            f"transport software identity drifted: expected {dict(expected)!r}, "
            f"observed {observed!r}"
        )
    if require_thread_environment and os.environ.get("OMP_NUM_THREADS") != "1":
        raise RuntimeError("transport requires OMP_NUM_THREADS=1")
    return observed


def operational_labels(
    intervals: Mapping[str, CapacityInterval | tuple[float, float]],
    *,
    tolerance: float = 1.0e-6,
) -> dict[str, bool]:
    """Apply exists-metric, then for-all-admissible-couplings semantics."""

    if set(intervals) != set(OPERATIONAL_METRICS):
        raise ValueError("operational metric inventory drifted")
    threshold = _finite(tolerance, "operational tolerance", minimum=0.0)
    normalized = {}
    for metric in OPERATIONAL_METRICS:
        raw = intervals[metric]
        interval = raw if isinstance(raw, CapacityInterval) else CapacityInterval(*raw)
        if (
            not math.isfinite(interval.lower)
            or not math.isfinite(interval.upper)
            or interval.lower > interval.upper
        ):
            raise ValueError(f"operational interval is invalid: {metric}")
        normalized[metric] = interval
    return {
        "b6_operational_penalty": any(
            interval.lower > threshold for interval in normalized.values()
        ),
        "b6_operational_relief": any(
            interval.upper < -threshold for interval in normalized.values()
        ),
    }


def _canonical_ids(
    ids: Sequence[str],
    probabilities: Sequence[float],
    label: str,
) -> tuple[np.ndarray, np.ndarray]:
    if len(ids) != len(probabilities) or len(set(ids)) != len(ids):
        raise ValueError(f"{label} ID inventory drifted")
    order = sorted(range(len(ids)), key=lambda index: ids[index].encode("utf-8"))
    ordered_ids = np.asarray([ids[index] for index in order])
    raw = [_finite(probabilities[index], label, minimum=0.0) for index in order]
    total = math.fsum(raw)
    if total <= 0.0:
        raise ValueError(f"{label} probability mass must be positive")
    normalized = np.asarray([value / total for value in raw], dtype=np.float64)
    return ordered_ids, normalized


def bootstrap_draw_stream(
    power_ids: Sequence[str],
    power_probabilities: Sequence[float],
    workload_ids: Sequence[str],
    workload_probabilities: Sequence[float],
    *,
    power_draw_count: int = 530,
    workload_draw_count: int = 34,
    replicates: int = 200,
    seed: int = 20260825,
) -> tuple[dict[str, object], ...]:
    """Produce collapsed empirical marginals from the registered draw stream."""

    raw_draws = bootstrap_raw_draw_stream(
        power_ids,
        power_probabilities,
        workload_ids,
        workload_probabilities,
        power_draw_count=power_draw_count,
        workload_draw_count=workload_draw_count,
        replicates=replicates,
        seed=seed,
    )
    canonical_power = sorted(power_ids, key=lambda item: item.encode("utf-8"))
    canonical_workload = sorted(
        workload_ids,
        key=lambda item: item.encode("utf-8"),
    )
    result = []
    for draw in raw_draws:
        power_counts = Counter(str(item) for item in draw["power"])
        workload_counts = Counter(str(item) for item in draw["workload"])
        result.append(
            {
                "replicate": draw["replicate"],
                "power": {
                    block_id: power_counts.get(block_id, 0) / power_draw_count
                    for block_id in canonical_power
                },
                "workload": {
                    block_id: workload_counts.get(block_id, 0) / workload_draw_count
                    for block_id in canonical_workload
                },
            }
        )
    return tuple(result)


def bootstrap_raw_draw_stream(
    power_ids: Sequence[str],
    power_probabilities: Sequence[float],
    workload_ids: Sequence[str],
    workload_probabilities: Sequence[float],
    *,
    power_draw_count: int = 530,
    workload_draw_count: int = 34,
    replicates: int = 200,
    seed: int = 20260825,
) -> list[dict[str, object]]:
    """Return raw IDs in the exact registered RNG consumption order."""

    for value, label in (
        (power_draw_count, "power draw count"),
        (workload_draw_count, "workload draw count"),
        (replicates, "replicate count"),
        (seed, "seed"),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{label} must be a nonnegative integer")
    if min(power_draw_count, workload_draw_count, replicates) <= 0:
        raise ValueError("draw counts and replicates must be positive")
    power, power_probability = _canonical_ids(
        power_ids,
        power_probabilities,
        "power",
    )
    workload, workload_probability = _canonical_ids(
        workload_ids,
        workload_probabilities,
        "workload",
    )
    generator = np.random.Generator(np.random.PCG64DXSM(seed))
    result = []
    for replicate in range(replicates):
        result.append(
            {
                "replicate": replicate,
                "power": generator.choice(
                    power,
                    size=power_draw_count,
                    replace=True,
                    p=power_probability,
                ).tolist(),
                "workload": generator.choice(
                    workload,
                    size=workload_draw_count,
                    replace=True,
                    p=workload_probability,
                ).tolist(),
            }
        )
    return result


def bootstrap_transport_intervals(
    *,
    draws: Sequence[Mapping[str, object]],
    state_by_power_id: Mapping[str, str],
    metric_matrices: Mapping[
        str,
        Mapping[str, Mapping[tuple[str, str], float]],
    ],
    metric_order: Sequence[str] = REGISTERED_METRICS,
    endpoint_solver: Callable[
        [Sequence[float], Sequence[float], Sequence[Sequence[float]], str],
        ScalarTransportCertificate,
    ],
) -> dict[str, object]:
    """Recompute all registered endpoints for every marginal resample."""

    cells = tuple(sorted(metric_matrices, key=lambda item: item.encode("utf-8")))
    metrics = tuple(metric_order)
    if not cells or metrics != REGISTERED_METRICS or len(set(metrics)) != len(metrics):
        raise ValueError("bootstrap cell or metric inventory drifted")
    endpoint_samples = {
        cell: {metric: {"lower": [], "upper": []} for metric in metrics}
        for cell in cells
    }
    endpoint_solver_calls = 0
    for expected_replicate, draw in enumerate(draws):
        if draw.get("replicate") != expected_replicate:
            raise ValueError("bootstrap replicate order drifted")
        power = dict(draw["power"])
        workload = dict(draw["workload"])
        conditioning = finite_conditioning(
            list(power),
            [float(power[key]) for key in power],
            state_by_power_id,
        )
        if conditioning["status"] != RESOLVED:
            return {
                "status": "unresolved",
                "reason": "empty_finite_support_in_at_least_one_replicate",
                "replicate": expected_replicate,
                "endpoint_solver_calls": endpoint_solver_calls,
                "intervals": None,
            }
        finite_ids = list(conditioning["finite_row_ids"])
        row_probability = list(conditioning["finite_row_probabilities"])
        column_ids = [
            block_id for block_id, probability in workload.items() if probability > 0
        ]
        column_probability_raw = [float(workload[block_id]) for block_id in column_ids]
        column_total = math.fsum(column_probability_raw)
        if column_total <= 0.0:
            raise ValueError("bootstrap workload support is empty")
        column_probability = [
            probability / column_total for probability in column_probability_raw
        ]
        for cell in cells:
            if set(metric_matrices[cell]) != set(metrics):
                raise ValueError("bootstrap metric inventory drifted")
            for metric in metrics:
                pair_values = metric_matrices[cell][metric]
                matrix = [
                    [
                        _finite(
                            pair_values[(power_id, workload_id)],
                            "bootstrap metric",
                        )
                        for workload_id in column_ids
                    ]
                    for power_id in finite_ids
                ]
                certificate = endpoint_solver(
                    row_probability,
                    column_probability,
                    matrix,
                    metric_name=metric,
                )
                endpoint_solver_calls += 2
                if (
                    not certificate.resolved
                    or certificate.lower is None
                    or certificate.upper is None
                ):
                    return {
                        "status": "unresolved",
                        "reason": "transport_endpoint_unresolved",
                        "replicate": expected_replicate,
                        "cell_id": cell,
                        "metric": metric,
                        "endpoint_solver_calls": endpoint_solver_calls,
                        "intervals": None,
                    }
                endpoint_samples[cell][metric]["lower"].append(certificate.lower.value)
                endpoint_samples[cell][metric]["upper"].append(certificate.upper.value)
    intervals = {
        cell: {
            metric: {
                endpoint: [
                    float(value)
                    for value in np.quantile(
                        np.asarray(values, dtype=np.float64),
                        q=[0.025, 0.975],
                        axis=0,
                        method="linear",
                    )
                ]
                for endpoint, values in endpoints.items()
            }
            for metric, endpoints in by_metric.items()
        }
        for cell, by_metric in endpoint_samples.items()
    }
    return {
        "status": RESOLVED,
        "replicates": len(draws),
        "endpoint_solver_calls": endpoint_solver_calls,
        "intervals": intervals,
    }


def canonical_certificate_payload(value: object) -> bytes:
    """Serialize every finite float by IEEE-754 ``float.hex`` authority."""

    def convert(item: object) -> object:
        if isinstance(item, bool) or item is None or isinstance(item, (str, int)):
            return item
        if isinstance(item, float):
            if not math.isfinite(item):
                raise ValueError("certificate contains a nonfinite float")
            return item.hex()
        if hasattr(item, "__dataclass_fields__"):
            return convert(asdict(item))
        if isinstance(item, Mapping):
            if any(not isinstance(key, str) for key in item):
                raise TypeError("certificate mapping keys must be strings")
            return {key: convert(child) for key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [convert(child) for child in item]
        raise TypeError("certificate contains an unsupported value")

    return (
        json.dumps(
            convert(value),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def canonical_certificate_sha256(value: object) -> str:
    return hashlib.sha256(canonical_certificate_payload(value)).hexdigest()


def _canonical_json_payload(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _assert_safe_path(path: Path, *, leaf_may_be_absent: bool) -> None:
    absolute = Path(os.path.abspath(path))
    ancestors = (
        absolute.parents if leaf_may_be_absent else (absolute, *absolute.parents)
    )
    for item in reversed(ancestors):
        try:
            mode = os.lstat(item).st_mode
        except FileNotFoundError:
            continue
        attributes = getattr(os.lstat(item), "st_file_attributes", 0)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        if stat.S_ISLNK(mode) or (reparse_flag and attributes & reparse_flag):
            raise ValueError(f"unsafe symlink or reparse point in output path: {item}")
        if item != absolute and not stat.S_ISDIR(mode):
            raise ValueError(f"unsafe non-directory output ancestor: {item}")


def _stable_regular_bytes(path: Path, label: str) -> bytes:
    _assert_safe_path(path, leaf_may_be_absent=False)
    before = os.stat(path, follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"{label} must be an ordinary file")
    first = path.read_bytes()
    middle = os.stat(path, follow_symlinks=False)
    second = path.read_bytes()
    after = os.stat(path, follow_symlinks=False)
    identity = lambda item: (
        item.st_dev,
        item.st_ino,
        item.st_size,
        item.st_mtime_ns,
    )
    if identity(before) != identity(middle) or identity(middle) != identity(after):
        raise ValueError(f"{label} identity changed during stable read")
    if first != second:
        raise ValueError(f"{label} bytes changed during stable read")
    return first


def _validate_live_digest_mapping(
    values: object,
    *,
    root: Path,
    label: str,
) -> dict[str, str]:
    if not isinstance(values, Mapping) or not values:
        raise ValueError(f"provenance {label} inventory is empty")
    result: dict[str, str] = {}
    for relative, digest in values.items():
        if (
            not isinstance(relative, str)
            or not relative
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ValueError(f"provenance {label} digest is invalid")
        path = root / relative
        if hashlib.sha256(_stable_regular_bytes(path, label)).hexdigest() != digest:
            raise ValueError(f"provenance {label} live bytes drifted: {relative}")
        result[relative] = digest
    return result


def validate_provenance(
    payload: Mapping[str, object],
    *,
    expected: Mapping[str, object],
    root: Path,
) -> dict[str, object]:
    """Validate the recursive provenance identity required by V5."""

    payload_fields = {
        "schema",
        "scientific_outer_sha256",
        "scientific_review_sha256",
        "implementation_outer_sha256",
        "code_sha256",
        "input_manifest_sha256",
        "software",
    }
    if set(payload) != payload_fields:
        raise ValueError("provenance inventory drifted")
    if payload["schema"] != "rq2_joint_deliverability_provenance_v1":
        raise ValueError("provenance schema drifted")
    expected_keys = payload_fields - {"schema"}
    if set(expected) != expected_keys:
        raise ValueError("expected provenance inventory drifted")
    if any(payload[key] != expected[key] for key in expected_keys):
        raise ValueError("provenance does not match the expected authority")
    for key in (
        "scientific_outer_sha256",
        "scientific_review_sha256",
        "implementation_outer_sha256",
    ):
        value_ = payload[key]
        if (
            not isinstance(value_, str)
            or len(value_) != 64
            or any(character not in "0123456789abcdef" for character in value_)
        ):
            raise ValueError(f"invalid provenance digest: {key}")
    code = _validate_live_digest_mapping(
        payload["code_sha256"],
        root=root,
        label="code",
    )
    inputs = _validate_live_digest_mapping(
        payload["input_manifest_sha256"],
        root=root,
        label="input manifest",
    )
    software = payload["software"]
    if (
        not isinstance(software, Mapping)
        or not software
        or any(
            not isinstance(name, str)
            or not name
            or not isinstance(release, str)
            or not release
            for name, release in software.items()
        )
    ):
        raise ValueError("provenance software identity is invalid")
    return {
        **dict(payload),
        "code_sha256": code,
        "input_manifest_sha256": inputs,
    }


def _sequence(value: object, label: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError(f"{label} must be a sequence")
    return value


def _exact_mapping(
    value: object,
    fields: set[str],
    label: str,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{label} field inventory drifted")
    return value


def _canonical_equal(left: object, right: object) -> bool:
    return _canonical_json_payload(left) == _canonical_json_payload(right)


def _digest_string(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} is not a canonical SHA-256 digest")
    return value


def _validate_structural_witness(
    value: object,
    *,
    cell: Mapping[str, object],
    arm_id: str,
) -> None:
    witness = _exact_mapping(
        value,
        {
            "cell_id",
            "arm_id",
            "track_id",
            "power_block_id",
            "workload_block_id",
            "total_required_call_energy",
            "eligible_recovery_power_by_hour",
            "maximum_eligible_recovery_energy",
            "recovery_efficiency",
            "initial_recovery_debt",
            "terminal_recovery_debt_limit",
            "terminal_debt_lower_bound",
            "tolerance",
            "debt_balance_identity",
        },
        "structural recovery witness",
    )
    valid_tracks = (
        {"grid", "cfe"}
        if arm_id == "joint_b6_separate_planning_shared_execution"
        else {"shared"}
    )
    if (
        witness["cell_id"] != cell["cell_id"]
        or witness["arm_id"] != arm_id
        or witness["track_id"] not in valid_tracks
        or not isinstance(witness["power_block_id"], str)
        or not witness["power_block_id"]
        or not isinstance(witness["workload_block_id"], str)
        or not witness["workload_block_id"]
        or witness["debt_balance_identity"]
        != (
            "initial_debt+required_call_energy-"
            "recovery_efficiency*maximum_eligible_recovery_energy"
        )
    ):
        raise ValueError("structural recovery witness identity drifted")
    eligible = tuple(
        _finite(value_, "eligible recovery power", minimum=0.0)
        for value_ in _sequence(
            witness["eligible_recovery_power_by_hour"],
            "eligible recovery power",
        )
    )
    total_call = _finite(
        witness["total_required_call_energy"],
        "total required call energy",
        minimum=0.0,
    )
    recovery_energy = _finite(
        witness["maximum_eligible_recovery_energy"],
        "maximum eligible recovery energy",
        minimum=0.0,
    )
    efficiency = _finite(
        witness["recovery_efficiency"],
        "witness recovery efficiency",
        minimum=0.0,
    )
    initial_debt = _finite(
        witness["initial_recovery_debt"],
        "initial recovery debt",
        minimum=0.0,
    )
    terminal_limit = _finite(
        witness["terminal_recovery_debt_limit"],
        "terminal recovery debt limit",
        minimum=0.0,
    )
    terminal_lower = _finite(
        witness["terminal_debt_lower_bound"],
        "terminal debt lower bound",
    )
    tolerance = _finite(witness["tolerance"], "witness tolerance", minimum=0.0)
    expected_lower = initial_debt + total_call - efficiency * recovery_energy
    if (
        len(eligible) != 24
        or any(
            recovery > float(cell["normalized_recovery_headroom"]) + 1.0e-12
            for recovery in eligible
        )
        or not math.isclose(
            recovery_energy,
            math.fsum(eligible),
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
        or not math.isclose(
            efficiency,
            float(cell["recovery_efficiency"]),
            rel_tol=0.0,
            abs_tol=0.0,
        )
        or initial_debt != 0.0
        or terminal_limit != 0.0
        or tolerance != 1.0e-12
        or not math.isclose(
            terminal_lower,
            expected_lower,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
        or terminal_lower <= terminal_limit + tolerance
    ):
        raise ValueError("structural recovery witness arithmetic drifted")


def _validate_capacity_cells(
    capacity: Mapping[str, object],
    expected_cells: Sequence[Mapping[str, object]],
    expected_solver_specification: Rq2SolverSpec,
) -> dict[str, Mapping[str, object]]:
    expected_solver_options = solver_options(expected_solver_specification)

    def validate_solver_binding(certificate: Mapping[str, object]) -> None:
        if (
            certificate.get("solver_name") != expected_solver_specification.name
            or certificate.get("solver_version")
            != expected_solver_specification.expected_package_version
            or certificate.get("solver_options") != expected_solver_options
        ):
            raise ValueError("output solver certificate binding drifted")

    expected_by_id = {}
    expected_order = []
    for raw in expected_cells:
        expected = _exact_mapping(
            raw,
            {
                "cell_id",
                "family",
                "hourly_cfe_target",
                "flexible_fraction",
                "normalized_recovery_headroom",
                "recovery_efficiency",
                "maximum_event_duration_hours",
                "maximum_event_count",
                "normalized_energy_budget",
                "normalized_debt_limit",
            },
            "expected registered cell",
        )
        cell_id = str(expected["cell_id"])
        if not cell_id or cell_id in expected_by_id:
            raise ValueError("expected registered cell IDs are invalid")
        expected_order.append(cell_id)
        expected_by_id[cell_id] = expected
    if len(expected_order) != 46:
        raise ValueError("expected registered cell inventory drifted")

    cells = _sequence(capacity["cells"], "capacity cells")
    if len(cells) != 46:
        raise ValueError("capacity output must contain all 46 cells")
    observed_order = [str(cell["cell_id"]) for cell in cells]
    if observed_order != expected_order:
        raise ValueError("capacity cell order or identity drifted")

    by_id: dict[str, Mapping[str, object]] = {}
    for raw_cell in cells:
        cell = _exact_mapping(
            raw_cell,
            {
                "cell_id",
                "family",
                "parameters",
                "arms",
                "capacity_attribution",
            },
            "capacity cell",
        )
        cell_id = str(cell["cell_id"])
        parameters = _exact_mapping(
            cell["parameters"],
            set(expected_by_id[cell_id]),
            "capacity cell parameters",
        )
        if (
            not _canonical_equal(parameters, expected_by_id[cell_id])
            or cell["family"] != parameters["family"]
        ):
            raise ValueError("capacity cell parameters drifted")
        raw_arms = _exact_mapping(cell["arms"], set(FOUR_ARM_IDS), "capacity arms")
        typed_arms: dict[str, CellArmCapacity] = {}
        for arm_id in FOUR_ARM_IDS:
            arm = _exact_mapping(
                raw_arms[arm_id],
                {
                    "arm_id",
                    "status",
                    "interval",
                    "reported_point",
                    "solver_certificate",
                    "structural_witness",
                    "training_support_failures",
                    "planning_input_sha256",
                    "full_support_audit",
                },
                "capacity arm",
            )
            if arm["arm_id"] != arm_id:
                raise ValueError("capacity arm identity drifted")
            _digest_string(arm["planning_input_sha256"], "planning input digest")
            audit = _exact_mapping(
                arm["full_support_audit"],
                {
                    "status",
                    "failures",
                    "fallback_scenario_count",
                    "fallback_solver_calls",
                    "fallback_certificates",
                },
                "full-support audit",
            )
            failures = tuple(
                str(item) for item in _sequence(audit["failures"], "failures")
            )
            fallback = _sequence(
                audit["fallback_certificates"],
                "fallback certificates",
            )
            fallback_count = audit["fallback_scenario_count"]
            fallback_calls = audit["fallback_solver_calls"]
            if (
                isinstance(fallback_count, bool)
                or not isinstance(fallback_count, int)
                or fallback_count < 0
                or isinstance(fallback_calls, bool)
                or not isinstance(fallback_calls, int)
                or fallback_calls < 0
                or fallback_calls != len(fallback)
                or fallback_calls
                != ((fallback_count + 255) // 256 if fallback_count else 0)
            ):
                raise ValueError("full-support fallback accounting drifted")
            for certificate in fallback:
                if not isinstance(certificate, Mapping):
                    raise TypeError("fallback certificate is not a mapping")
                validate_solver_binding(certificate)
                finalize_capacity_certificate(
                    arm_id=arm_id,
                    candidate=certificate,
                )

            status = str(arm["status"])
            certificate = arm["solver_certificate"]
            witness = arm["structural_witness"]
            if isinstance(witness, Mapping):
                _validate_structural_witness(
                    witness,
                    cell=parameters,
                    arm_id=arm_id,
                )
            arm_failures = tuple(
                str(item)
                for item in _sequence(
                    arm["training_support_failures"],
                    "training-support failures",
                )
            )
            if arm_failures != failures:
                raise ValueError(
                    "capacity arm and full-support failure inventories disagree"
                )
            support_unresolved = (
                status == UNRESOLVED
                and isinstance(certificate, Mapping)
                and certificate.get("status") == "candidate_resolved"
                and audit["status"] == "unresolved"
            )
            if isinstance(certificate, Mapping):
                validate_solver_binding(certificate)
            finalized = finalize_capacity_certificate(
                arm_id=arm_id,
                candidate=certificate if isinstance(certificate, Mapping) else None,
                structural_witness=witness if isinstance(witness, Mapping) else None,
                training_support_failures=arm_failures,
                training_support_unresolved=support_unresolved,
            )
            expected_arm = asdict(finalized)
            observed_arm = {
                key: arm[key]
                for key in (
                    "arm_id",
                    "status",
                    "interval",
                    "reported_point",
                    "solver_certificate",
                    "structural_witness",
                    "training_support_failures",
                )
            }
            if not _canonical_equal(observed_arm, expected_arm):
                raise ValueError("capacity arm evidence does not reproduce its status")
            if status == RESOLVED:
                expected_audit_status = "passed"
            elif status == STRUCTURAL_INFEASIBLE:
                expected_audit_status = "not_applicable_structural_infeasibility"
            elif status == TRAINING_SUPPORT_FAILURE:
                expected_audit_status = "failed"
            elif (
                status == UNRESOLVED
                and isinstance(certificate, Mapping)
                and certificate.get("status") == "candidate_resolved"
            ):
                expected_audit_status = "unresolved"
            else:
                expected_audit_status = "not_applicable_candidate_unresolved"
            if (
                audit["status"] != expected_audit_status
                or (status == TRAINING_SUPPORT_FAILURE and not failures)
                or (status != TRAINING_SUPPORT_FAILURE and failures)
            ):
                raise ValueError("capacity arm and full-support audit disagree")
            typed_arms[arm_id] = finalized
        expected_attribution = capacity_attribution(typed_arms)
        if not _canonical_equal(cell["capacity_attribution"], expected_attribution):
            raise ValueError(
                "capacity attribution does not reproduce from arm evidence"
            )
        by_id[cell_id] = cell
    return by_id


def _validate_holdout_payload(
    holdout: Mapping[str, object],
    capacity_by_id: Mapping[str, Mapping[str, object]],
    expected_cell_ids: Sequence[str],
) -> dict[str, Mapping[str, object]]:
    power_rows = _sequence(holdout["power_marginal"], "power marginal")
    workload_rows = _sequence(holdout["workload_marginal"], "workload marginal")
    if not power_rows or not workload_rows:
        raise ValueError("holdout marginal support is empty")
    power_ids = []
    power_probabilities = []
    power_states = {}
    for raw in power_rows:
        row = _exact_mapping(
            raw,
            {"block_id", "probability", "state"},
            "power marginal row",
        )
        block_id = str(row["block_id"])
        power_ids.append(block_id)
        power_probabilities.append(
            _finite(row["probability"], "power probability", minimum=0.0)
        )
        power_states[block_id] = str(row["state"])
    workload_ids = []
    workload_probabilities = []
    for raw in workload_rows:
        row = _exact_mapping(
            raw,
            {"block_id", "probability"},
            "workload marginal row",
        )
        workload_ids.append(str(row["block_id"]))
        workload_probabilities.append(
            _finite(row["probability"], "workload probability", minimum=0.0)
        )
    if (
        len(set(power_ids)) != len(power_ids)
        or len(set(workload_ids)) != len(workload_ids)
        or power_ids != sorted(power_ids, key=lambda item: item.encode("utf-8"))
        or workload_ids != sorted(workload_ids, key=lambda item: item.encode("utf-8"))
        or not math.isclose(math.fsum(workload_probabilities), 1.0, abs_tol=1.0e-9)
    ):
        raise ValueError("holdout marginal identity or ordering drifted")
    conditioning = finite_conditioning(
        power_ids,
        power_probabilities,
        power_states,
    )
    finite_ids = list(conditioning["finite_row_ids"])
    e0_ids = [
        block_id
        for block_id in power_ids
        if power_states[block_id] == "exogenous_grid_infeasibility"
    ]
    if (
        not math.isclose(
            _finite(holdout["E0_mass"], "holdout E0 mass", minimum=0.0),
            float(conditioning["E0_mass"]),
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
        or list(holdout["E0_power_block_ids"]) != e0_ids
        or list(holdout["finite_power_block_ids"]) != finite_ids
        or list(holdout["workload_block_ids"]) != workload_ids
    ):
        raise ValueError("holdout E0 or finite conditioning drifted")

    cell_rows = _sequence(holdout["cells"], "holdout cells")
    if [str(row["cell_id"]) for row in cell_rows] != list(expected_cell_ids):
        raise ValueError("holdout cell order or identity drifted")
    trajectories_retained = holdout["trajectories_retained"]
    if not isinstance(trajectories_retained, bool):
        raise TypeError("holdout trajectory retention flag must be boolean")
    trajectory_stream = hashlib.sha256()
    trajectory_count = 0
    by_id: dict[str, Mapping[str, object]] = {}
    conditioned_probability = dict(
        zip(
            conditioning["finite_row_ids"],
            conditioning["finite_row_probabilities"],
            strict=True,
        )
    )
    for raw_cell in cell_rows:
        cell = _exact_mapping(
            raw_cell,
            {"cell_id", "status", "pairs"},
            "holdout cell",
        )
        cell_id = str(cell["cell_id"])
        capacity_arms = capacity_by_id[cell_id]["arms"]
        capacity_resolved = all(
            capacity_arms[arm_id]["status"] == RESOLVED for arm_id in FOUR_ARM_IDS
        )
        expected_status = (
            "not_evaluable_capacity_unresolved"
            if not capacity_resolved
            else (
                RESOLVED
                if conditioning["status"] == RESOLVED
                else "finite_service_identification_unresolved"
            )
        )
        if cell["status"] != expected_status:
            raise ValueError("holdout status disagrees with capacity or E0 state")
        pairs = _sequence(cell["pairs"], "holdout pairs")
        if expected_status != RESOLVED:
            if pairs:
                raise ValueError("non-evaluable holdout cell contains pair outcomes")
            by_id[cell_id] = cell
            continue
        expected_pairs = [
            (power_id, workload_id)
            for power_id in finite_ids
            for workload_id in workload_ids
        ]
        observed_pairs = [
            (str(pair["power_block_id"]), str(pair["workload_block_id"]))
            for pair in pairs
        ]
        if observed_pairs != expected_pairs:
            raise ValueError("holdout Cartesian pair inventory drifted")
        for pair in pairs:
            pair = _exact_mapping(
                pair,
                {
                    "power_block_id",
                    "workload_block_id",
                    "conditioned_power_probability",
                    "workload_probability",
                    "arms",
                },
                "holdout pair",
            )
            power_id = str(pair["power_block_id"])
            workload_id = str(pair["workload_block_id"])
            workload_probability = workload_probabilities[
                workload_ids.index(workload_id)
            ]
            if not math.isclose(
                float(pair["conditioned_power_probability"]),
                float(conditioned_probability[power_id]),
                rel_tol=0.0,
                abs_tol=1.0e-12,
            ) or not math.isclose(
                float(pair["workload_probability"]),
                workload_probability,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            ):
                raise ValueError("holdout pair marginal probability drifted")
            arms = _exact_mapping(pair["arms"], set(FOUR_ARM_IDS), "holdout pair arms")
            for arm_id in FOUR_ARM_IDS:
                expected_arm_fields = {
                    "capacity",
                    "metrics",
                    "trajectory_sha256",
                }
                if trajectories_retained:
                    expected_arm_fields.add("trajectory")
                arm = _exact_mapping(
                    arms[arm_id],
                    expected_arm_fields,
                    "holdout arm outcome",
                )
                if not math.isclose(
                    float(arm["capacity"]),
                    float(capacity_arms[arm_id]["reported_point"]),
                    rel_tol=0.0,
                    abs_tol=0.0,
                ):
                    raise ValueError("holdout capacity drifted from frozen frontier")
                metrics = _exact_mapping(
                    arm["metrics"],
                    {
                        "grid_shortfall",
                        "cfe_shortfall",
                        "total_service_shortfall",
                        "hard_grid_failure",
                        "cfe_service_failure",
                        "recovery_completion_failure",
                        "joint_service_failure",
                        "peak_recovery_debt",
                        "terminal_recovery_debt",
                    },
                    "holdout arm metrics",
                )
                grid_shortfall = _finite(
                    metrics["grid_shortfall"],
                    "grid shortfall",
                    minimum=0.0,
                )
                cfe_shortfall = _finite(
                    metrics["cfe_shortfall"],
                    "CFE shortfall",
                    minimum=0.0,
                )
                terminal_debt = _finite(
                    metrics["terminal_recovery_debt"],
                    "terminal recovery debt",
                    minimum=0.0,
                )
                _finite(
                    metrics["peak_recovery_debt"], "peak recovery debt", minimum=0.0
                )
                if (
                    not math.isclose(
                        float(metrics["total_service_shortfall"]),
                        grid_shortfall + cfe_shortfall,
                        rel_tol=0.0,
                        abs_tol=1.0e-12,
                    )
                    or metrics["hard_grid_failure"] is not (grid_shortfall > 1.0e-6)
                    or metrics["cfe_service_failure"] is not (cfe_shortfall > 1.0e-6)
                    or metrics["recovery_completion_failure"]
                    is not (terminal_debt > 1.0e-6)
                    or metrics["joint_service_failure"]
                    is not (
                        grid_shortfall > 1.0e-6
                        or cfe_shortfall > 1.0e-6
                        or terminal_debt > 1.0e-6
                    )
                ):
                    raise ValueError("holdout metric identities drifted")
                trajectory_digest = _digest_string(
                    arm["trajectory_sha256"],
                    "holdout trajectory digest",
                )
                if (
                    trajectories_retained
                    and hashlib.sha256(
                        _canonical_json_payload(arm["trajectory"])
                    ).hexdigest()
                    != trajectory_digest
                ):
                    raise ValueError("retained holdout trajectory hash drifted")
                trajectory_key = f"{cell_id}/{power_id}/{workload_id}/{arm_id}"
                trajectory_stream.update(
                    f"{trajectory_key}\0{trajectory_digest}\n".encode()
                )
                trajectory_count += 1
        by_id[cell_id] = cell
    if (
        holdout["trajectory_hash_count"] != trajectory_count
        or holdout["trajectory_hash_stream_sha256"] != trajectory_stream.hexdigest()
    ):
        raise ValueError("holdout trajectory hash accounting drifted")
    return by_id


def _hex_float(value: object, label: str) -> float:
    if not isinstance(value, str):
        raise TypeError(f"{label} is not a hexadecimal float")
    try:
        decoded = float.fromhex(value)
    except ValueError as error:
        raise ValueError(f"{label} is not a hexadecimal float") from error
    if not math.isfinite(decoded) or decoded.hex() != value:
        raise ValueError(f"{label} is not canonical finite float.hex")
    return decoded


def _holdout_pair_metric_values(arms: object) -> dict[str, float]:
    typed_arms = _exact_mapping(arms, set(FOUR_ARM_IDS), "holdout pair arms")
    prefixes = {
        "network_only_shared": "network_only",
        "cfe_only_shared": "cfe_only",
        "joint_correct_shared": "joint_correct",
        "joint_b6_separate_planning_shared_execution": "joint_b6",
    }
    result: dict[str, float] = {}
    metrics_by_arm = {}
    for arm_id, prefix in prefixes.items():
        arm = typed_arms[arm_id]
        if not isinstance(arm, Mapping):
            raise TypeError("holdout pair arm must be a mapping")
        metrics = arm["metrics"]
        if not isinstance(metrics, Mapping):
            raise TypeError("holdout pair metrics must be a mapping")
        metrics_by_arm[arm_id] = metrics
        for source in (
            "joint_service_failure",
            "hard_grid_failure",
            "cfe_service_failure",
            "total_service_shortfall",
            "cfe_shortfall",
        ):
            raw_metric = metrics[source]
            if source.endswith("_failure"):
                if not isinstance(raw_metric, bool):
                    raise TypeError(f"{prefix} {source} must be boolean")
                metric_value = float(raw_metric)
            else:
                metric_value = _finite(
                    raw_metric,
                    f"{prefix} {source}",
                    minimum=0.0,
                )
            result[f"{prefix}_{source}"] = metric_value
    correct = metrics_by_arm["joint_correct_shared"]
    b6 = metrics_by_arm["joint_b6_separate_planning_shared_execution"]
    result.update(
        {
            "B6_minus_correct_joint_service_failure": float(b6["joint_service_failure"])
            - float(correct["joint_service_failure"]),
            "B6_minus_correct_total_service_shortfall": float(
                b6["total_service_shortfall"]
            )
            - float(correct["total_service_shortfall"]),
            "B6_minus_correct_cfe_shortfall": float(b6["cfe_shortfall"])
            - float(correct["cfe_shortfall"]),
        }
    )
    if set(result) != set(REGISTERED_METRICS):
        raise ValueError("holdout pair metric inventory drifted")
    return result


def _validate_transport_certificate(
    certificate: object,
    metric: str,
    *,
    row_probabilities: Sequence[float],
    column_probabilities: Sequence[float],
    metric_matrix: Sequence[Sequence[float]],
) -> CapacityInterval | None:
    value = _exact_mapping(
        certificate,
        {
            "schema",
            "metric",
            "resolved",
            "sharp",
            "lower",
            "upper",
            "unresolved_reason",
        },
        "transport certificate",
    )
    if (
        value["schema"] != "rq2_joint_deliverability_transport_certificate_v3"
        or value["metric"] != metric
        or not isinstance(value["resolved"], bool)
        or not isinstance(value["sharp"], bool)
    ):
        raise ValueError("transport certificate identity drifted")

    rows = _probabilities(row_probabilities, "transport row probabilities")
    columns = _probabilities(column_probabilities, "transport column probabilities")
    matrix = np.asarray(metric_matrix, dtype=np.float64)
    if matrix.shape != (rows.size, columns.size) or not np.all(np.isfinite(matrix)):
        raise ValueError("transport validation metric matrix drifted")
    equality_matrix, equality_rhs = _transport_equalities(rows, columns)

    def endpoint(raw: object, extremum: str) -> float:
        item = _exact_mapping(
            raw,
            {
                "extremum",
                "value",
                "coupling_row_major",
                "dual_equality_variables",
                "primal_objective_min_form",
                "dual_objective_min_form",
                "primal_dual_gap",
                "marginal_residual",
                "dual_feasibility_residual",
                "solver_status",
            },
            "transport endpoint",
        )
        if (
            item["extremum"] != extremum
            or not isinstance(item["solver_status"], str)
            or not item["solver_status"]
        ):
            raise ValueError("transport endpoint identity drifted")
        coupling = _sequence(item["coupling_row_major"], "transport coupling")
        dual = _sequence(
            item["dual_equality_variables"],
            "transport dual variables",
        )
        if len(coupling) != rows.size * columns.size or len(dual) != equality_rhs.size:
            raise ValueError("transport endpoint vector dimensions drifted")
        primal_vector = np.asarray(
            [_hex_float(raw_value, "transport coupling") for raw_value in coupling],
            dtype=np.float64,
        )
        dual_vector = np.asarray(
            [_hex_float(raw_value, "transport dual variable") for raw_value in dual],
            dtype=np.float64,
        )
        if np.any(primal_vector < -1.0e-9):
            raise ValueError("transport coupling is negative")
        endpoint_value = _hex_float(item["value"], "transport endpoint value")
        primal = _hex_float(
            item["primal_objective_min_form"],
            "transport primal objective",
        )
        dual_objective = _hex_float(
            item["dual_objective_min_form"],
            "transport dual objective",
        )
        gap = _hex_float(item["primal_dual_gap"], "transport primal-dual gap")
        marginal = _hex_float(
            item["marginal_residual"],
            "transport marginal residual",
        )
        dual_residual = _hex_float(
            item["dual_feasibility_residual"],
            "transport dual residual",
        )
        objective = matrix.ravel() if extremum == "lower" else -matrix.ravel()
        expected_primal = float(objective @ primal_vector)
        expected_dual = float(equality_rhs @ dual_vector)
        expected_gap = abs(expected_primal - expected_dual)
        expected_marginal = float(
            np.max(np.abs(equality_matrix @ primal_vector - equality_rhs))
        )
        expected_dual_residual = max(
            0.0,
            float(
                np.max(np.asarray(equality_matrix.T @ dual_vector).ravel() - objective)
            ),
        )
        if (
            not math.isclose(primal, expected_primal, rel_tol=0.0, abs_tol=1.0e-12)
            or not math.isclose(
                dual_objective,
                expected_dual,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            )
            or not math.isclose(gap, expected_gap, rel_tol=0.0, abs_tol=1.0e-12)
            or not math.isclose(
                marginal,
                expected_marginal,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            )
            or not math.isclose(
                dual_residual,
                expected_dual_residual,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            )
            or gap < 0.0
            or gap > 1.0e-8
            or marginal < 0.0
            or marginal > 1.0e-8
            or dual_residual < 0.0
            or dual_residual > 1.0e-8
            or not math.isclose(
                endpoint_value,
                primal if extremum == "lower" else -primal,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            )
        ):
            raise ValueError("transport endpoint certificate is inconsistent")
        return endpoint_value

    if value["resolved"] is True:
        if (
            value["sharp"] is not True
            or value["unresolved_reason"] is not None
            or value["lower"] is None
            or value["upper"] is None
        ):
            raise ValueError("resolved transport certificate is incomplete")
        lower = endpoint(value["lower"], "lower")
        upper = endpoint(value["upper"], "upper")
        if lower > upper + 1.0e-8:
            raise ValueError("transport lower endpoint exceeds upper endpoint")
        return CapacityInterval(lower, upper)
    if (
        value["sharp"] is not False
        or not isinstance(value["unresolved_reason"], str)
        or not value["unresolved_reason"]
    ):
        raise ValueError("unresolved transport certificate is inconsistent")
    if value["lower"] is not None:
        endpoint(value["lower"], "lower")
    if value["upper"] is not None:
        endpoint(value["upper"], "upper")
    return None


def _validate_identification_payload(
    identification: Mapping[str, object],
    holdout: Mapping[str, object],
    capacity_by_id: Mapping[str, Mapping[str, object]],
    holdout_by_id: Mapping[str, Mapping[str, object]],
    expected_cell_ids: Sequence[str],
) -> None:
    e0_mass = _finite(identification["E0_mass"], "identification E0 mass", minimum=0.0)
    if not math.isclose(e0_mass, float(holdout["E0_mass"]), abs_tol=1.0e-12):
        raise ValueError("identification E0 mass drifted")
    cells = _sequence(identification["cells"], "identification cells")
    if [str(row["cell_id"]) for row in cells] != list(expected_cell_ids):
        raise ValueError("identification cell order or identity drifted")
    all_e0 = not holdout["finite_power_block_ids"]
    resolved_cell_count = 0
    for raw_cell in cells:
        cell = _exact_mapping(
            raw_cell,
            {
                "cell_id",
                "status",
                "capacity_attribution",
                "transport_certificates",
                "operational_labels",
            },
            "identification cell",
        )
        cell_id = str(cell["cell_id"])
        base_attribution = capacity_by_id[cell_id]["capacity_attribution"]
        if all_e0:
            if (
                cell["status"] != "finite_service_identification_unresolved"
                or cell["transport_certificates"] is not None
                or cell["operational_labels"] is not None
                or not _canonical_equal(cell["capacity_attribution"], base_attribution)
            ):
                raise ValueError("all-E0 identification cell drifted")
            continue
        if holdout_by_id[cell_id]["status"] != RESOLVED:
            if (
                cell["status"] != "not_evaluable"
                or cell["transport_certificates"] is not None
                or cell["operational_labels"] is not None
                or not _canonical_equal(cell["capacity_attribution"], base_attribution)
            ):
                raise ValueError("non-evaluable identification cell drifted")
            continue
        finite_power_ids = list(holdout["finite_power_block_ids"])
        workload_ids = list(holdout["workload_block_ids"])
        pair_lookup = {
            (str(pair["power_block_id"]), str(pair["workload_block_id"])): pair
            for pair in holdout_by_id[cell_id]["pairs"]
        }
        row_probabilities = [
            float(
                pair_lookup[(power_id, workload_ids[0])][
                    "conditioned_power_probability"
                ]
            )
            for power_id in finite_power_ids
        ]
        column_probabilities = [
            float(
                pair_lookup[(finite_power_ids[0], workload_id)]["workload_probability"]
            )
            for workload_id in workload_ids
        ]
        pair_metrics = {
            pair_id: _holdout_pair_metric_values(pair["arms"])
            for pair_id, pair in pair_lookup.items()
        }
        certificates = _exact_mapping(
            cell["transport_certificates"],
            set(REGISTERED_METRICS),
            "transport certificates",
        )
        intervals = {
            metric: interval
            for metric in REGISTERED_METRICS
            if (
                interval := _validate_transport_certificate(
                    certificates[metric],
                    metric,
                    row_probabilities=row_probabilities,
                    column_probabilities=column_probabilities,
                    metric_matrix=[
                        [
                            pair_metrics[(power_id, workload_id)][metric]
                            for workload_id in workload_ids
                        ]
                        for power_id in finite_power_ids
                    ],
                )
            )
            is not None
        }
        if set(intervals) == set(REGISTERED_METRICS):
            resolved_cell_count += 1
            expected_labels = operational_labels(
                {metric: intervals[metric] for metric in OPERATIONAL_METRICS}
            )
            if (
                cell["status"] != RESOLVED
                or cell["operational_labels"] != expected_labels
            ):
                raise ValueError("resolved operational labels drifted")
            arm_statuses = {
                arm_id: str(capacity_by_id[cell_id]["arms"][arm_id]["status"])
                for arm_id in FOUR_ARM_IDS
            }
            expected_attribution = finalize_operational_attribution(
                base_attribution,
                arm_statuses,
                intervals,
            )
            if not _canonical_equal(
                cell["capacity_attribution"],
                expected_attribution,
            ):
                raise ValueError("operational attribution drifted")
        elif (
            cell["status"] != "transport_unresolved"
            or cell["operational_labels"] is not None
            or not _canonical_equal(cell["capacity_attribution"], base_attribution)
        ):
            raise ValueError("unresolved transport cell drifted")

    expected_transport_calls = (
        0
        if all_e0
        else 2
        * len(REGISTERED_METRICS)
        * sum(row["status"] == RESOLVED for row in holdout_by_id.values())
    )
    if identification["transport_solver_calls"] != expected_transport_calls:
        raise ValueError("point transport endpoint call count drifted")
    expected_status = (
        "finite_service_identification_unresolved"
        if all_e0
        else ("resolved" if resolved_cell_count == 46 else "partially_unresolved")
    )
    if identification["status"] != expected_status:
        raise ValueError("identification aggregate status drifted")
    bootstrap = identification["bootstrap"]
    if not isinstance(bootstrap, Mapping):
        raise TypeError("bootstrap must be a mapping")
    status = bootstrap.get("status")
    if status not in {
        RESOLVED,
        UNRESOLVED,
        "not_evaluable_no_resolved_cells",
    }:
        raise ValueError("formal identification bootstrap is incomplete")
    calls = bootstrap.get("endpoint_solver_calls")
    if isinstance(calls, bool) or not isinstance(calls, int) or calls < 0:
        raise ValueError("bootstrap endpoint call count is invalid")
    evaluated_cell_ids = sorted(
        (
            cell_id
            for cell_id in expected_cell_ids
            if holdout_by_id[cell_id]["status"] == RESOLVED
        ),
        key=lambda item: item.encode("utf-8"),
    )
    not_evaluable_cell_ids = sorted(
        (cell_id for cell_id in expected_cell_ids if cell_id not in evaluated_cell_ids),
        key=lambda item: item.encode("utf-8"),
    )
    if status == RESOLVED:
        bootstrap = _exact_mapping(
            bootstrap,
            {
                "status",
                "replicates",
                "endpoint_solver_calls",
                "intervals",
                "evaluated_cell_ids",
                "not_evaluable_cell_ids",
            },
            "resolved bootstrap",
        )
        evaluated = list(bootstrap["evaluated_cell_ids"])
        if (
            bootstrap["replicates"] != 200
            or calls != 200 * len(evaluated) * len(REGISTERED_METRICS) * 2
            or evaluated != evaluated_cell_ids
            or list(bootstrap["not_evaluable_cell_ids"]) != not_evaluable_cell_ids
        ):
            raise ValueError("resolved bootstrap accounting drifted")
        intervals = _exact_mapping(
            bootstrap["intervals"],
            set(evaluated),
            "bootstrap intervals",
        )
        for cell_id in evaluated:
            by_metric = _exact_mapping(
                intervals[cell_id],
                set(REGISTERED_METRICS),
                "bootstrap metric intervals",
            )
            for metric in REGISTERED_METRICS:
                endpoints = _exact_mapping(
                    by_metric[metric],
                    {"lower", "upper"},
                    "bootstrap endpoint intervals",
                )
                for endpoint in ("lower", "upper"):
                    bounds = _sequence(
                        endpoints[endpoint],
                        "bootstrap confidence interval",
                    )
                    if len(bounds) != 2:
                        raise ValueError("bootstrap confidence interval drifted")
                    lower, upper = (
                        _finite(bound, "bootstrap confidence bound") for bound in bounds
                    )
                    if lower > upper:
                        raise ValueError("bootstrap confidence interval is reversed")
    elif status == "not_evaluable_no_resolved_cells":
        bootstrap = _exact_mapping(
            bootstrap,
            {
                "status",
                "endpoint_solver_calls",
                "intervals",
                "evaluated_cell_ids",
                "not_evaluable_cell_ids",
            },
            "non-evaluable bootstrap",
        )
        if (
            calls != 0
            or bootstrap["intervals"] is not None
            or list(bootstrap["evaluated_cell_ids"]) != []
            or list(bootstrap["not_evaluable_cell_ids"]) != not_evaluable_cell_ids
            or evaluated_cell_ids
        ):
            raise ValueError("non-evaluable bootstrap accounting drifted")
    elif all_e0:
        bootstrap = _exact_mapping(
            bootstrap,
            {
                "status",
                "reason",
                "endpoint_solver_calls",
                "intervals",
            },
            "all-E0 bootstrap",
        )
        if (
            bootstrap["reason"] != "empty_finite_support"
            or calls != 0
            or bootstrap["intervals"] is not None
        ):
            raise ValueError("all-E0 bootstrap accounting drifted")
    else:
        reason = bootstrap.get("reason")
        common_fields = {
            "status",
            "reason",
            "replicate",
            "endpoint_solver_calls",
            "intervals",
            "evaluated_cell_ids",
            "not_evaluable_cell_ids",
        }
        expected_fields = (
            common_fields
            if reason == "empty_finite_support_in_at_least_one_replicate"
            else common_fields | {"cell_id", "metric"}
        )
        bootstrap = _exact_mapping(
            bootstrap,
            expected_fields,
            "unresolved bootstrap",
        )
        replicate = bootstrap["replicate"]
        if (
            isinstance(replicate, bool)
            or not isinstance(replicate, int)
            or not 0 <= replicate < 200
            or bootstrap["intervals"] is not None
            or list(bootstrap["evaluated_cell_ids"]) != evaluated_cell_ids
            or list(bootstrap["not_evaluable_cell_ids"]) != not_evaluable_cell_ids
        ):
            raise ValueError("unresolved bootstrap accounting drifted")
        calls_per_replicate = len(evaluated_cell_ids) * len(REGISTERED_METRICS) * 2
        expected_calls = replicate * calls_per_replicate
        if reason == "transport_endpoint_unresolved":
            cell_id = bootstrap["cell_id"]
            metric = bootstrap["metric"]
            if cell_id not in evaluated_cell_ids or metric not in REGISTERED_METRICS:
                raise ValueError("unresolved bootstrap location drifted")
            expected_calls += (
                evaluated_cell_ids.index(cell_id) * len(REGISTERED_METRICS) * 2
                + (REGISTERED_METRICS.index(metric) + 1) * 2
            )
        elif reason != "empty_finite_support_in_at_least_one_replicate":
            raise ValueError("unresolved bootstrap reason drifted")
        if calls != expected_calls:
            raise ValueError("unresolved bootstrap endpoint count drifted")


def _reproduce_frontier_summary(
    cells: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    primary: dict[tuple[float, float], list[Mapping[str, object]]] = {}
    oat = []
    for cell in cells:
        parameters = cell["parameters"]
        if not isinstance(parameters, Mapping):
            raise TypeError("frontier cell parameters must be a mapping")
        if cell["family"] == "primary_factorial":
            key = (
                float(parameters["flexible_fraction"]),
                float(parameters["normalized_recovery_headroom"]),
            )
            primary.setdefault(key, []).append(cell)
        else:
            oat.append(
                {
                    "cell_id": cell["cell_id"],
                    "capacity_attribution": cell["capacity_attribution"],
                }
            )
    strata = []
    for (flexible, headroom), rows in sorted(primary.items()):
        ordered = sorted(
            rows,
            key=lambda item: float(item["parameters"]["hourly_cfe_target"]),
        )
        first_positive = next(
            (
                float(item["parameters"]["hourly_cfe_target"])
                for item in ordered
                if item["capacity_attribution"]["resolved"]
                and item["capacity_attribution"]["interval_labels"]["I_joint"]
                == "robust_positive"
            ),
            None,
        )
        first_negative = next(
            (
                float(item["parameters"]["hourly_cfe_target"])
                for item in ordered
                if item["capacity_attribution"]["resolved"]
                and item["capacity_attribution"]["interval_labels"]["I_joint"]
                == "robust_negative"
            ),
            None,
        )
        deliverable = [
            float(item["parameters"]["hourly_cfe_target"])
            for item in ordered
            if item["arms"]["joint_correct_shared"]["status"] == RESOLVED
            and float(item["arms"]["joint_correct_shared"]["interval"]["upper"]) <= 1.0
        ]
        strata.append(
            {
                "flexible_fraction": flexible,
                "normalized_recovery_headroom": headroom,
                "cell_ids": [item["cell_id"] for item in ordered],
                "first_registered_robust_positive_joint_interaction": (
                    first_positive
                    if first_positive is not None
                    else "no_interval_supported_crossing_on_registered_grid"
                ),
                "first_registered_robust_negative_joint_interaction": (
                    first_negative
                    if first_negative is not None
                    else "no_interval_supported_crossing_on_registered_grid"
                ),
                "highest_registered_deliverable_target": (
                    max(deliverable) if deliverable else None
                ),
            }
        )
    return {
        "primary_strata": strata,
        "secondary_oat": sorted(
            oat,
            key=lambda item: str(item["cell_id"]).encode("utf-8"),
        ),
        "interpolation_used": False,
        "target_monotonicity_assumed": False,
    }


def validate_output_payloads(
    payloads: Mapping[str, Mapping[str, object]],
    *,
    expected_provenance: Mapping[str, object],
    provenance_root: Path,
    expected_cells: Sequence[Mapping[str, object]],
    expected_solver_specification: Rq2SolverSpec,
) -> None:
    """Require all four outputs plus provenance with exact schema identities."""

    if set(payloads) != set(OUTPUT_SCHEMAS):
        raise ValueError("output payload inventory drifted")
    for filename, schema in OUTPUT_SCHEMAS.items():
        payload = payloads[filename]
        if not isinstance(payload, Mapping) or payload.get("schema") != schema:
            raise ValueError(f"output schema drifted: {filename}")
    capacity = payloads["capacity_frontier.json"]
    holdout = payloads["holdout.json"]
    identification = payloads["identification.json"]
    report = payloads["report.json"]
    if set(capacity) != {
        "schema",
        "cell_count",
        "arm_output_count",
        "representative_solver_calls",
        "full_support_fallback_solver_calls",
        "total_solver_calls",
        "network_alpha_reuse_count",
        "training_E0_mass",
        "representative_power_ids",
        "representative_workload_ids",
        "frontier_summary",
        "cells",
    }:
        raise ValueError("capacity output inventory drifted")
    if set(holdout) != {
        "schema",
        "E0_mass",
        "E0_power_block_ids",
        "finite_power_block_ids",
        "workload_block_ids",
        "power_marginal",
        "workload_marginal",
        "trajectories_retained",
        "trajectory_hash_count",
        "trajectory_hash_stream_sha256",
        "cells",
    }:
        raise ValueError("holdout output inventory drifted")
    if set(identification) != {
        "schema",
        "status",
        "E0_mass",
        "transport_solver_calls",
        "bootstrap",
        "cells",
    }:
        raise ValueError("identification output inventory drifted")
    if set(report) != {
        "schema",
        "registered_cell_count",
        "capacity_resolved_cell_count",
        "holdout_resolved_cell_count",
        "identification_status",
        "capacity_frontier_sha256",
        "holdout_sha256",
        "identification_sha256",
        "provenance_sha256",
        "formal_result",
        "paper_claim",
        "security_certified",
    }:
        raise ValueError("report output inventory drifted")
    expected_cell_ids = [str(cell["cell_id"]) for cell in expected_cells]
    capacity_by_id = _validate_capacity_cells(
        capacity,
        expected_cells,
        expected_solver_specification,
    )
    representative_keys = {
        (arm_id, str(arm["planning_input_sha256"]))
        for cell in capacity["cells"]
        for arm_id, arm in cell["arms"].items()
        if arm["solver_certificate"] is not None
    }
    network_certificate_hashes = [
        str(cell["arms"]["network_only_shared"]["planning_input_sha256"])
        for cell in capacity["cells"]
        if cell["arms"]["network_only_shared"]["solver_certificate"] is not None
    ]
    expected_network_reuse_count = len(network_certificate_hashes) - len(
        set(network_certificate_hashes)
    )
    expected_fallback_calls = sum(
        int(arm["full_support_audit"]["fallback_solver_calls"])
        for cell in capacity["cells"]
        for arm in cell["arms"].values()
    )
    if (
        capacity["cell_count"] != 46
        or capacity["arm_output_count"] != 184
        or isinstance(capacity["representative_solver_calls"], bool)
        or not isinstance(capacity["representative_solver_calls"], int)
        or capacity["representative_solver_calls"] < 0
        or isinstance(capacity["full_support_fallback_solver_calls"], bool)
        or not isinstance(capacity["full_support_fallback_solver_calls"], int)
        or capacity["full_support_fallback_solver_calls"] < 0
        or capacity["representative_solver_calls"] != len(representative_keys)
        or capacity["full_support_fallback_solver_calls"] != expected_fallback_calls
        or capacity["total_solver_calls"]
        != capacity["representative_solver_calls"]
        + capacity["full_support_fallback_solver_calls"]
        or isinstance(capacity["network_alpha_reuse_count"], bool)
        or not isinstance(capacity["network_alpha_reuse_count"], int)
        or capacity["network_alpha_reuse_count"] < 0
        or capacity["network_alpha_reuse_count"] != expected_network_reuse_count
        or not 0.0 <= _finite(capacity["training_E0_mass"], "training E0 mass") <= 1.0
    ):
        raise ValueError("capacity output counts or E0 mass drifted")
    for label in ("representative_power_ids", "representative_workload_ids"):
        values = _sequence(capacity[label], label)
        if (
            len(values) != 8
            or len(set(values)) != 8
            or any(not isinstance(value, str) or not value for value in values)
        ):
            raise ValueError(f"{label} inventory drifted")
    frontier_summary = _exact_mapping(
        capacity["frontier_summary"],
        {
            "primary_strata",
            "secondary_oat",
            "interpolation_used",
            "target_monotonicity_assumed",
        },
        "frontier summary",
    )
    if not _canonical_equal(
        frontier_summary,
        _reproduce_frontier_summary(capacity["cells"]),
    ):
        raise ValueError("frontier summary does not reproduce from capacity cells")
    holdout_by_id = _validate_holdout_payload(
        holdout,
        capacity_by_id,
        expected_cell_ids,
    )
    _validate_identification_payload(
        identification,
        holdout,
        capacity_by_id,
        holdout_by_id,
        expected_cell_ids,
    )
    if (
        report["registered_cell_count"] != 46
        or report["capacity_resolved_cell_count"]
        != sum(
            bool(row["capacity_attribution"]["resolved"]) for row in capacity["cells"]
        )
        or report["holdout_resolved_cell_count"]
        != sum(row["status"] == RESOLVED for row in holdout["cells"])
        or report["identification_status"] != identification["status"]
        or report["capacity_frontier_sha256"]
        != hashlib.sha256(_canonical_json_payload(capacity)).hexdigest()
        or report["holdout_sha256"]
        != hashlib.sha256(_canonical_json_payload(holdout)).hexdigest()
        or report["identification_sha256"]
        != hashlib.sha256(_canonical_json_payload(identification)).hexdigest()
        or report["provenance_sha256"]
        != hashlib.sha256(
            _canonical_json_payload(payloads["provenance.json"])
        ).hexdigest()
        or report["formal_result"] is not False
        or report["paper_claim"] is not False
        or report["security_certified"] is not False
    ):
        raise ValueError("report bindings or closed claims drifted")
    validate_provenance(
        payloads["provenance.json"],
        expected=expected_provenance,
        root=provenance_root,
    )


def recursive_manifest(directory: Path) -> dict[str, object]:
    """Hash the exact typed output tree except the manifest itself."""

    _assert_safe_path(directory, leaf_may_be_absent=False)
    if not directory.is_dir():
        raise ValueError("manifest root must be a directory")
    directories = ["."]
    files: dict[str, str] = {}
    for path in sorted(directory.rglob("*")):
        relative = path.relative_to(directory).as_posix()
        if relative == "SHA256SUMS.json":
            continue
        mode = os.lstat(path).st_mode
        if stat.S_ISLNK(mode):
            raise ValueError(f"output bundle contains a symlink: {relative}")
        if stat.S_ISDIR(mode):
            directories.append(relative)
            continue
        if not stat.S_ISREG(mode):
            raise ValueError(f"output bundle contains a non-regular file: {relative}")
        files[relative] = hashlib.sha256(
            _stable_regular_bytes(path, f"output member {relative}")
        ).hexdigest()
    if set(files) != set(OUTPUT_SCHEMAS) or directories != ["."]:
        raise ValueError("recursive output typed-tree inventory drifted")
    return {
        "schema": "rq2_joint_deliverability_output_manifest_v1",
        "directories": directories,
        "files": files,
    }


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_durable(path: Path, payload: bytes) -> None:
    with path.open("xb") as target:
        target.write(payload)
        target.flush()
        os.fsync(target.fileno())


def _success_payload(target: Path, manifest: Mapping[str, object]) -> dict[str, object]:
    manifest_payload = _canonical_json_payload(manifest)
    return {
        "schema": "rq2_joint_deliverability_output_success_v1",
        "result_directory_name": target.name,
        "result_manifest_sha256": hashlib.sha256(manifest_payload).hexdigest(),
        "published": True,
        "formal_result": False,
        "paper_claim": False,
        "security_certified": False,
    }


def _validate_committed_output(
    target: Path,
    success: Path,
) -> dict[str, object]:
    _assert_safe_path(target, leaf_may_be_absent=False)
    _assert_safe_path(success, leaf_may_be_absent=False)
    if not target.is_dir() or not success.is_dir():
        raise ValueError("published output or success commit is not a directory")
    result_manifest = json.loads(
        _stable_regular_bytes(
            target / "SHA256SUMS.json",
            "published output manifest",
        )
    )
    observed = recursive_manifest(target)
    if result_manifest != observed:
        raise ValueError("published output manifest failed stable readback")
    success_members = sorted(path.name for path in success.iterdir())
    if success_members != ["success.json"]:
        raise ValueError("published success commit inventory drifted")
    success_payload = json.loads(
        _stable_regular_bytes(
            success / "success.json",
            "published success commit",
        )
    )
    if success_payload != _success_payload(target, observed):
        raise ValueError("published success commit binding drifted")
    return observed


def publish_output_bundle(
    target: Path,
    payloads: Mapping[str, Mapping[str, object]],
    *,
    expected_provenance: Mapping[str, object],
    provenance_root: Path,
    expected_cells: Sequence[Mapping[str, object]],
    expected_solver_specification: Rq2SolverSpec,
) -> dict[str, object]:
    """Publish an exact result tree followed by an immutable success commit."""

    validate_output_payloads(
        payloads,
        expected_provenance=expected_provenance,
        provenance_root=provenance_root,
        expected_cells=expected_cells,
        expected_solver_specification=expected_solver_specification,
    )
    _assert_safe_path(target, leaf_may_be_absent=True)
    success = target.with_name(f"{target.name}.PUBLISHED")
    _assert_safe_path(success, leaf_may_be_absent=True)
    if os.path.lexists(target) or os.path.lexists(success):
        raise FileExistsError("output target or success commit already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path(target.parent, leaf_may_be_absent=False)
    lock = target.with_name(f".{target.name}.publish.lock")
    _assert_safe_path(lock, leaf_may_be_absent=True)
    lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    lock_token = uuid.uuid4().hex.encode("ascii")
    os.write(lock_fd, lock_token)
    os.fsync(lock_fd)
    os.close(lock_fd)
    staging = target.with_name(f".{target.name}.staging-{uuid.uuid4().hex}")
    success_staging = success.with_name(f".{success.name}.staging-{uuid.uuid4().hex}")
    result_appeared = False
    try:
        staging.mkdir()
        for filename in sorted(payloads):
            _write_durable(
                staging / filename,
                _canonical_json_payload(payloads[filename]),
            )
        manifest = recursive_manifest(staging)
        _write_durable(
            staging / "SHA256SUMS.json",
            _canonical_json_payload(manifest),
        )
        _fsync_directory(staging)
        if os.path.lexists(target) or os.path.lexists(success):
            raise FileExistsError(
                "output target or success appeared before result rename"
            )
        os.rename(staging, target)
        result_appeared = True
        _fsync_directory(target.parent)
        observed = recursive_manifest(target)
        expected = json.loads(
            _stable_regular_bytes(
                target / "SHA256SUMS.json",
                "published output manifest",
            )
        )
        if observed != expected:
            raise RuntimeError("published output manifest failed readback")
        success_staging.mkdir()
        _write_durable(
            success_staging / "success.json",
            _canonical_json_payload(_success_payload(target, observed)),
        )
        _fsync_directory(success_staging)
        if os.path.lexists(success):
            raise FileExistsError("success commit appeared before rename")
        os.rename(success_staging, success)
        _fsync_directory(success.parent)
        observed = _validate_committed_output(target, success)
    except BaseException:
        if os.path.lexists(target) or os.path.lexists(success):
            try:
                observed = _validate_committed_output(target, success)
            except Exception as reconciliation_error:
                raise RuntimeError(
                    "output publication is commit_indeterminate"
                ) from reconciliation_error
            else:
                if os.path.lexists(lock):
                    try:
                        if lock.read_bytes() == lock_token:
                            lock.unlink()
                    except OSError:
                        pass
                return observed
        if staging.exists() and staging.is_dir() and not staging.is_symlink():
            shutil.rmtree(staging)
        if (
            success_staging.exists()
            and success_staging.is_dir()
            and not success_staging.is_symlink()
        ):
            shutil.rmtree(success_staging)
        raise
    finally:
        if not result_appeared and os.path.lexists(lock):
            try:
                if lock.read_bytes() == lock_token:
                    lock.unlink()
            except OSError:
                pass
    if os.path.lexists(lock):
        try:
            if lock.read_bytes() == lock_token:
                lock.unlink()
        except OSError:
            pass
    return observed


__all__ = [
    "CAPACITY_SYMBOL_BY_ARM",
    "OPERATIONAL_METRICS",
    "OUTPUT_SCHEMAS",
    "REGISTERED_METRICS",
    "CapacityInterval",
    "CellArmCapacity",
    "ScalarTransportCertificate",
    "TransportEndpoint",
    "bootstrap_draw_stream",
    "bootstrap_raw_draw_stream",
    "bootstrap_transport_intervals",
    "canonical_certificate_payload",
    "canonical_certificate_sha256",
    "capacity_attribution",
    "capacity_contrast_intervals",
    "certify_scalar_transport",
    "classify_interval",
    "execute_holdout_policy",
    "finalize_capacity_certificate",
    "finalize_operational_attribution",
    "finite_conditioning",
    "operational_labels",
    "publish_output_bundle",
    "recursive_manifest",
    "sealed_holdout_probe_projection",
    "validate_output_payloads",
    "validate_provenance",
    "validate_transport_runtime",
]
