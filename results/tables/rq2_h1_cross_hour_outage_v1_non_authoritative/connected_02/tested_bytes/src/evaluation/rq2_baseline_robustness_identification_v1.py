"""Pure RQ2 four-arm transport identification and attribution helpers.

The module does not load or publish a formal result.  It operates on already
validated machine-readable inputs, records explicit primal/dual certificates,
and fails closed whenever a transport certificate is incomplete.
"""

from __future__ import annotations

import json
import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import linprog

from src.scenarios.block_coupling import bound_transport_expectation

COMPARISON_TOLERANCE = 1.0e-6
CERTIFICATE_TOLERANCE = 1.0e-9
PHASE_ONE_POSITIVE_TOLERANCE = 1.0e-8

UNRESOLVED = "unresolved"
TRAINING_INFEASIBLE = "training_infeasible_estimand_undefined"
SINGLE_SERVICE = "single_service_insufficiency_supported"
JOINT_ONLY = "joint_only_interaction_supported"
B6_SPECIFIC = "b6_specific_underprovisioning_supported"
PARTIALLY_IDENTIFIED = "partially_identified"
NO_MECHANISM = "no_registered_mechanism_supported"

ATTRIBUTION_PRIORITY = (
    UNRESOLVED,
    TRAINING_INFEASIBLE,
    SINGLE_SERVICE,
    JOINT_ONLY,
    B6_SPECIFIC,
    PARTIALLY_IDENTIFIED,
    NO_MECHANISM,
)

FOUR_ARM_IDS = (
    "network_only_shared",
    "cfe_only_shared",
    "joint_correct_shared",
    "joint_b6_separate_planning_shared_execution",
)

COMMON_PI_BRANCHES = (
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

PACKAGE_SCHEMAS = (
    "four_arm_training_status",
    "four_arm_minimum_flexibility",
    "four_arm_pairwise_outcomes",
    "E0_outcomes",
    "checkpoint_inventory",
    "provenance",
)

FINITE_GRID_NEED = "finite_grid_need"
EXOGENOUS_GRID_INFEASIBILITY = "exogenous_grid_infeasibility"

NETWORK_FAILURE = "network_only_failure_probability"
NETWORK_SHORTFALL = "network_only_expected_shortfall"
CFE_FAILURE = "cfe_only_failure_probability"
CFE_SHORTFALL = "cfe_only_expected_shortfall"
JOINT_FAILURE = "joint_correct_failure_probability"
JOINT_SHORTFALL = "joint_correct_expected_shortfall"
JOINT_NETWORK_FAILURE = "joint_correct_minus_network_only_failure_probability"
JOINT_NETWORK_SHORTFALL = "joint_correct_minus_network_only_expected_shortfall"
JOINT_CFE_FAILURE = "joint_correct_minus_cfe_only_failure_probability"
JOINT_CFE_SHORTFALL = "joint_correct_minus_cfe_only_expected_shortfall"
B6_JOINT_FAILURE = "joint_b6_minus_joint_correct_failure_probability"
B6_JOINT_SHORTFALL = "joint_b6_minus_joint_correct_expected_shortfall"
JOINT_INTERACTION_CAPACITY = "joint_interaction_capacity"
B6_UNDERPROVISIONING = "b6_underprovisioning"

CATEGORY_DECIDING_METRICS = (
    NETWORK_FAILURE,
    NETWORK_SHORTFALL,
    CFE_FAILURE,
    CFE_SHORTFALL,
    JOINT_FAILURE,
    JOINT_SHORTFALL,
    JOINT_NETWORK_FAILURE,
    JOINT_NETWORK_SHORTFALL,
    JOINT_CFE_FAILURE,
    JOINT_CFE_SHORTFALL,
    B6_JOINT_FAILURE,
    B6_JOINT_SHORTFALL,
    JOINT_INTERACTION_CAPACITY,
    B6_UNDERPROVISIONING,
)

DESCRIPTIVE_DEBT_METRICS = (
    "network_only_peak_recovery_debt",
    "network_only_terminal_recovery_debt",
    "cfe_only_peak_recovery_debt",
    "cfe_only_terminal_recovery_debt",
    "joint_correct_peak_recovery_debt",
    "joint_correct_terminal_recovery_debt",
    "joint_b6_peak_recovery_debt",
    "joint_b6_terminal_recovery_debt",
)


@dataclass(frozen=True)
class LinearInequality:
    name: str
    matrix: tuple[tuple[float, ...], ...]
    upper_bound: float


@dataclass(frozen=True)
class MarginalEvidence:
    row_ids: tuple[str, ...]
    row_probabilities: tuple[float, ...]
    row_states: tuple[str, ...]
    finite_row_ids: tuple[str, ...]
    finite_row_probabilities: tuple[float, ...]
    column_ids: tuple[str, ...]
    column_probabilities: tuple[float, ...]
    exogenous_grid_infeasibility_mass: float


def _probabilities(values: Sequence[float], label: str) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    if (
        result.ndim != 1
        or result.size == 0
        or not np.all(np.isfinite(result))
        or np.any(result < 0.0)
        or abs(float(result.sum()) - 1.0) > CERTIFICATE_TOLERANCE
    ):
        raise ValueError(f"{label} must be a finite probability vector")
    return result


def _matrix(
    values: Sequence[Sequence[float]],
    shape: tuple[int, int],
    label: str,
) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    if result.shape != shape or not np.all(np.isfinite(result)):
        raise ValueError(f"{label} must be a finite matrix with shape {shape}")
    return result


def _transport_equalities(
    rows: np.ndarray,
    columns: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    n_rows = rows.size
    n_columns = columns.size
    coefficients = []
    rhs = []
    for row in range(n_rows):
        values = np.zeros((n_rows, n_columns))
        values[row, :] = 1.0
        coefficients.append(values.ravel())
        rhs.append(rows[row])
    for column in range(n_columns - 1):
        values = np.zeros((n_rows, n_columns))
        values[:, column] = 1.0
        coefficients.append(values.ravel())
        rhs.append(columns[column])
    return np.asarray(coefficients), np.asarray(rhs)


def _maximum_positive(values: np.ndarray) -> float:
    return max(0.0, float(np.max(values))) if values.size else 0.0


def _coupling_residuals(
    coupling: np.ndarray,
    rows: np.ndarray,
    columns: np.ndarray,
) -> dict[str, float]:
    return {
        "row_marginal_residual": float(
            np.max(np.abs(coupling.sum(axis=1) - rows))
        ),
        "column_marginal_residual": float(
            np.max(np.abs(coupling.sum(axis=0) - columns))
        ),
        "total_mass_residual": abs(float(coupling.sum()) - 1.0),
        "nonnegativity_residual": max(0.0, -float(np.min(coupling))),
    }


def _explicit_dual(
    objective: np.ndarray,
    a_eq: np.ndarray,
    b_eq: np.ndarray,
    a_ub: np.ndarray,
    b_ub: np.ndarray,
) -> Any:
    equality_count = b_eq.size
    inequality_count = b_ub.size
    dual_objective = np.concatenate((-b_eq, -b_ub))
    dual_constraints = np.hstack((a_eq.T, a_ub.T))
    dual_bounds = [
        *((None, None),) * equality_count,
        *((None, 0.0),) * inequality_count,
    ]
    return linprog(
        dual_objective,
        A_ub=dual_constraints,
        b_ub=objective,
        bounds=dual_bounds,
        method="highs",
    )


def _endpoint_certificate(
    *,
    extremum: str,
    value: float,
    coupling_values: Sequence[Sequence[float]],
    solver_status: str,
    metric: np.ndarray,
    rows: np.ndarray,
    columns: np.ndarray,
) -> dict[str, object]:
    transformed_objective = metric.ravel() if extremum == "minimum" else -metric.ravel()
    transformed_value = value if extremum == "minimum" else -value
    coupling = np.asarray(coupling_values, dtype=float)
    if coupling.shape != metric.shape or not np.all(np.isfinite(coupling)):
        return {
            "extremum": extremum,
            "resolved": False,
            "unresolved_reason": "primal_coupling_missing_or_nonfinite",
        }
    a_eq, b_eq = _transport_equalities(rows, columns)
    a_ub = np.empty((0, transformed_objective.size))
    b_ub = np.empty(0)
    try:
        dual = _explicit_dual(
            transformed_objective,
            a_eq,
            b_eq,
            a_ub,
            b_ub,
        )
    except Exception as error:  # solver exceptions are unresolved, not infeasible
        return {
            "extremum": extremum,
            "resolved": False,
            "unresolved_reason": f"dual_solver_exception:{type(error).__name__}",
        }
    if (
        dual.status != 0
        or dual.success is not True
        or dual.x is None
        or not np.all(np.isfinite(dual.x))
        or "optimal" not in solver_status.casefold()
    ):
        return {
            "extremum": extremum,
            "resolved": False,
            "unresolved_reason": "primal_or_dual_optimal_status_absent",
            "primal_solver_status": solver_status,
            "dual_solver_status": str(dual.message),
        }
    dual_variables = np.asarray(dual.x[: b_eq.size], dtype=float)
    primal_recomputed = float(coupling.ravel() @ transformed_objective)
    dual_recomputed = float(b_eq @ dual_variables)
    gap = primal_recomputed - dual_recomputed
    residuals = _coupling_residuals(coupling, rows, columns)
    residuals.update(
        {
            "objective_recomputation_residual": abs(
                primal_recomputed - transformed_value
            ),
            "dual_feasibility_residual": _maximum_positive(
                a_eq.T @ dual_variables - transformed_objective
            ),
            "primal_dual_gap": abs(gap),
        }
    )
    resolved = all(
        isfinite(number) and number <= CERTIFICATE_TOLERANCE
        for number in residuals.values()
    ) and gap >= -CERTIFICATE_TOLERANCE
    return {
        "extremum": extremum,
        "resolved": resolved,
        "unresolved_reason": None if resolved else "endpoint_certificate_residual_failed",
        "value": value,
        "primal_objective_min_form": primal_recomputed,
        "dual_objective_min_form": dual_recomputed,
        "primal_dual_gap": abs(gap),
        "primal_solver_status": solver_status,
        "dual_solver_status": str(dual.message),
        "coupling": tuple(tuple(float(x) for x in row) for row in coupling),
        "dual_variables": tuple(float(x) for x in dual_variables),
        "residuals": residuals,
    }


def certify_scalar_transport(
    row_probabilities: Sequence[float],
    column_probabilities: Sequence[float],
    metric: Sequence[Sequence[float]],
    *,
    metric_name: str,
) -> dict[str, object]:
    """Compute sharp scalar endpoints and independent explicit dual certificates."""

    rows = _probabilities(row_probabilities, "row_probabilities")
    columns = _probabilities(column_probabilities, "column_probabilities")
    matrix = _matrix(metric, (rows.size, columns.size), metric_name)
    try:
        bound = bound_transport_expectation(rows, columns, matrix)
    except Exception as error:
        return {
            "schema": "rq2_baseline_scalar_transport_certificate_v1",
            "metric": metric_name,
            "resolved": False,
            "sharp": False,
            "unresolved_reason": f"primal_solver_exception:{type(error).__name__}",
            "lower": None,
            "upper": None,
        }
    lower = _endpoint_certificate(
        extremum="minimum",
        value=float(bound.minimum),
        coupling_values=bound.minimizing_coupling,
        solver_status=bound.minimum_status,
        metric=matrix,
        rows=rows,
        columns=columns,
    )
    upper = _endpoint_certificate(
        extremum="maximum",
        value=float(bound.maximum),
        coupling_values=bound.maximizing_coupling,
        solver_status=bound.maximum_status,
        metric=matrix,
        rows=rows,
        columns=columns,
    )
    resolved = lower.get("resolved") is True and upper.get("resolved") is True
    if resolved and float(lower["value"]) > float(upper["value"]) + CERTIFICATE_TOLERANCE:
        resolved = False
    return {
        "schema": "rq2_baseline_scalar_transport_certificate_v1",
        "metric": metric_name,
        "resolved": resolved,
        "sharp": resolved,
        "unresolved_reason": None if resolved else "endpoint_certificate_incomplete",
        "lower": lower,
        "upper": upper,
    }


def _standard_form_certificate(
    objective: np.ndarray,
    a_eq: np.ndarray,
    b_eq: np.ndarray,
    a_ub: np.ndarray,
    b_ub: np.ndarray,
) -> dict[str, object]:
    try:
        primal = linprog(
            objective,
            A_ub=a_ub if b_ub.size else None,
            b_ub=b_ub if b_ub.size else None,
            A_eq=a_eq,
            b_eq=b_eq,
            bounds=(0.0, None),
            method="highs",
        )
        dual = _explicit_dual(objective, a_eq, b_eq, a_ub, b_ub)
    except Exception as error:
        return {
            "resolved": False,
            "unresolved_reason": f"solver_exception:{type(error).__name__}",
        }
    if (
        primal.status != 0
        or primal.success is not True
        or primal.x is None
        or dual.status != 0
        or dual.success is not True
        or dual.x is None
        or not np.all(np.isfinite(primal.x))
        or not np.all(np.isfinite(dual.x))
    ):
        return {
            "resolved": False,
            "unresolved_reason": "primal_or_dual_optimal_status_absent",
            "primal_solver_status": str(primal.message),
            "dual_solver_status": str(dual.message),
        }
    equality_count = b_eq.size
    y = np.asarray(dual.x[:equality_count], dtype=float)
    w = np.asarray(dual.x[equality_count:], dtype=float)
    primal_value = float(objective @ primal.x)
    dual_value = float(b_eq @ y + b_ub @ w)
    gap = primal_value - dual_value
    residuals = {
        "primal_equality_residual": float(
            np.max(np.abs(a_eq @ primal.x - b_eq))
        ),
        "primal_inequality_residual": _maximum_positive(a_ub @ primal.x - b_ub),
        "primal_nonnegativity_residual": max(0.0, -float(np.min(primal.x))),
        "dual_feasibility_residual": _maximum_positive(
            a_eq.T @ y + a_ub.T @ w - objective
        ),
        "dual_multiplier_sign_residual": _maximum_positive(w),
        "primal_dual_gap": abs(gap),
        "primal_objective_recomputation_residual": abs(primal_value - float(primal.fun)),
        "dual_objective_recomputation_residual": abs(dual_value + float(dual.fun)),
    }
    resolved = all(
        isfinite(number) and number <= CERTIFICATE_TOLERANCE
        for number in residuals.values()
    ) and gap >= -CERTIFICATE_TOLERANCE
    return {
        "resolved": resolved,
        "unresolved_reason": None if resolved else "primal_dual_certificate_residual_failed",
        "primal_solver_status": str(primal.message),
        "dual_solver_status": str(dual.message),
        "primal_objective": primal_value,
        "dual_objective": dual_value,
        "primal_dual_gap": abs(gap),
        "primal_variables": tuple(float(x) for x in primal.x),
        "dual_equality_variables": tuple(float(x) for x in y),
        "dual_inequality_variables": tuple(float(x) for x in w),
        "residuals": residuals,
    }


def certify_common_pi_phase_one(
    row_probabilities: Sequence[float],
    column_probabilities: Sequence[float],
    inequalities: Sequence[LinearInequality],
) -> dict[str, object]:
    """Use an always-feasible shared-slack LP to certify common-pi compatibility."""

    rows = _probabilities(row_probabilities, "row_probabilities")
    columns = _probabilities(column_probabilities, "column_probabilities")
    shape = (rows.size, columns.size)
    matrices = [_matrix(item.matrix, shape, item.name) for item in inequalities]
    bounds = np.asarray([float(item.upper_bound) for item in inequalities])
    if not np.all(np.isfinite(bounds)):
        raise ValueError("common-pi inequality bounds must be finite")
    transport_a_eq, b_eq = _transport_equalities(rows, columns)
    a_eq = np.hstack((transport_a_eq, np.zeros((b_eq.size, 1))))
    if matrices:
        a_ub = np.asarray(
            [np.concatenate((matrix.ravel(), (-1.0,))) for matrix in matrices]
        )
    else:
        a_ub = np.empty((0, rows.size * columns.size + 1))
    objective = np.zeros(rows.size * columns.size + 1)
    objective[-1] = 1.0
    certificate = _standard_form_certificate(objective, a_eq, b_eq, a_ub, bounds)
    if certificate.get("resolved") is not True:
        return {
            "schema": "rq2_baseline_common_pi_phase_one_certificate_v1",
            "status": "unknown",
            "certificate": certificate,
        }
    variables = np.asarray(certificate["primal_variables"], dtype=float)
    coupling = variables[:-1].reshape(shape)
    phase_one_slack = float(variables[-1])
    coupling_residuals = _coupling_residuals(coupling, rows, columns)
    expectations = {
        item.name: float(np.sum(coupling * matrix))
        for item, matrix in zip(inequalities, matrices, strict=True)
    }
    scientific_slacks = {
        item.name: float(item.upper_bound - expectations[item.name])
        for item in inequalities
    }
    phase_residual = max(
        (
            max(0.0, expectations[item.name] - phase_one_slack - item.upper_bound)
            for item in inequalities
        ),
        default=0.0,
    )
    certificate_residual = max((*coupling_residuals.values(), phase_residual))
    if certificate_residual > CERTIFICATE_TOLERANCE:
        status = "unknown"
        reason = "phase_one_witness_residual_failed"
    elif phase_one_slack <= CERTIFICATE_TOLERANCE:
        status = "compatible"
        reason = None
    elif phase_one_slack > PHASE_ONE_POSITIVE_TOLERANCE:
        status = "certified_incompatible"
        reason = "positive_phase_one_optimum"
    else:
        status = "unknown"
        reason = "phase_one_optimum_numerically_ambiguous"
    return {
        "schema": "rq2_baseline_common_pi_phase_one_certificate_v1",
        "status": status,
        "unresolved_reason": reason if status == "unknown" else None,
        "incompatibility_reason": reason if status == "certified_incompatible" else None,
        "phase_one_optimum": phase_one_slack,
        "coupling": tuple(tuple(float(x) for x in row) for row in coupling),
        "expectations": expectations,
        "scientific_constraint_slacks": scientific_slacks,
        "coupling_residuals": coupling_residuals,
        "certificate": certificate,
    }


def _certify_constrained_maximum(
    rows: np.ndarray,
    columns: np.ndarray,
    candidate: np.ndarray,
    inequalities: Sequence[LinearInequality],
) -> dict[str, object]:
    a_eq, b_eq = _transport_equalities(rows, columns)
    matrices = [_matrix(item.matrix, candidate.shape, item.name) for item in inequalities]
    a_ub = (
        np.asarray([matrix.ravel() for matrix in matrices])
        if matrices
        else np.empty((0, candidate.size))
    )
    b_ub = np.asarray([float(item.upper_bound) for item in inequalities])
    certificate = _standard_form_certificate(
        -candidate.ravel(),
        a_eq,
        b_eq,
        a_ub,
        b_ub,
    )
    if certificate.get("resolved") is not True:
        return {"status": "unknown", "certificate": certificate}
    coupling = np.asarray(certificate["primal_variables"], dtype=float).reshape(candidate.shape)
    maximum = float(np.sum(coupling * candidate))
    expectations = {
        item.name: float(np.sum(coupling * matrix))
        for item, matrix in zip(inequalities, matrices, strict=True)
    }
    if any(
        expectations[item.name] > item.upper_bound + CERTIFICATE_TOLERANCE
        for item in inequalities
    ):
        return {
            "status": "unknown",
            "unresolved_reason": "candidate_witness_violates_mandatory_constraint",
            "certificate": certificate,
        }
    return {
        "status": "resolved",
        "maximum": maximum,
        "coupling": tuple(tuple(float(x) for x in row) for row in coupling),
        "mandatory_expectations": expectations,
        "certificate": certificate,
    }


def certify_common_pi_branch(
    row_probabilities: Sequence[float],
    column_probabilities: Sequence[float],
    *,
    branch_name: str,
    mandatory_inequalities: Sequence[LinearInequality],
    candidate_matrix: Sequence[Sequence[float]] | None = None,
    candidate_constant: float | None = None,
    feasibility_only: bool = False,
    comparison_tolerance: float = COMPARISON_TOLERANCE,
) -> dict[str, object]:
    """Certify one multimetric branch with one transport matrix."""

    candidate_count = sum(
        (candidate_matrix is not None, candidate_constant is not None, feasibility_only)
    )
    if candidate_count != 1:
        raise ValueError("exactly one common-pi branch candidate is required")
    rows = _probabilities(row_probabilities, "row_probabilities")
    columns = _probabilities(column_probabilities, "column_probabilities")
    matrix = None
    phase_inequalities = tuple(mandatory_inequalities)
    if candidate_matrix is not None:
        matrix = _matrix(
            candidate_matrix,
            (rows.size, columns.size),
            f"{branch_name}.candidate",
        )
        phase_inequalities = (
            *phase_inequalities,
            LinearInequality(
                f"{branch_name}.candidate_at_least_tolerance",
                tuple(tuple(float(-value) for value in row) for row in matrix),
                -comparison_tolerance,
            ),
        )
    phase_one = certify_common_pi_phase_one(rows, columns, phase_inequalities)
    if phase_one["status"] == "unknown":
        return {
            "schema": "rq2_baseline_common_pi_branch_certificate_v1",
            "branch": branch_name,
            "status": "unknown",
            "phase_one": phase_one,
            "candidate": None,
        }
    if phase_one["status"] == "certified_incompatible":
        return {
            "schema": "rq2_baseline_common_pi_branch_certificate_v1",
            "branch": branch_name,
            "status": "certified_incompatible",
            "phase_one": phase_one,
            "candidate": None,
        }
    if feasibility_only:
        return {
            "schema": "rq2_baseline_common_pi_branch_certificate_v1",
            "branch": branch_name,
            "status": "compatible",
            "phase_one": phase_one,
            "candidate": {
                "kind": "feasibility_only",
                "coupling": phase_one["coupling"],
            },
        }
    if candidate_constant is not None:
        if not isfinite(candidate_constant):
            raise ValueError("candidate_constant must be finite")
        compatible = candidate_constant > comparison_tolerance
        candidate = {
            "kind": "constant",
            "value": candidate_constant,
            "strictly_positive": compatible,
            "coupling": phase_one["coupling"],
        }
    else:
        assert matrix is not None
        candidate = _certify_constrained_maximum(
            rows,
            columns,
            matrix,
            mandatory_inequalities,
        )
        if candidate["status"] == "unknown":
            return {
                "schema": "rq2_baseline_common_pi_branch_certificate_v1",
                "branch": branch_name,
                "status": "unknown",
                "phase_one": phase_one,
                "candidate": candidate,
            }
        compatible = float(candidate["maximum"]) > comparison_tolerance
        candidate = {
            **candidate,
            "kind": "matrix",
            "strictly_positive": compatible,
        }
    return {
        "schema": "rq2_baseline_common_pi_branch_certificate_v1",
        "branch": branch_name,
        "status": "compatible" if compatible else "not_compatible",
        "phase_one": phase_one,
        "candidate": candidate,
    }


def derive_marginal_evidence(
    expected_pairs: Sequence[Mapping[str, object]],
    expected_cell_ids: Sequence[str],
) -> MarginalEvidence:
    """Derive one cross-cell-consistent marginal contract from package pairs."""

    cells = tuple(str(item) for item in expected_cell_ids)
    if not cells or len(cells) != len(set(cells)):
        raise ValueError("cell inventory must be nonempty and unique")
    by_cell: dict[str, dict[tuple[str, str], Mapping[str, object]]] = {
        cell: {} for cell in cells
    }
    for item in expected_pairs:
        cell = str(item.get("cell_id"))
        if cell not in by_cell:
            raise ValueError("expected pair contains an unknown cell")
        key = (str(item.get("power_block_id")), str(item.get("workload_block_id")))
        if not all(key) or key in by_cell[cell]:
            raise ValueError("expected pair inventory contains a duplicate or empty ID")
        by_cell[cell][key] = item
    reference = by_cell[cells[0]]
    if not reference:
        raise ValueError("expected pair inventory is empty")
    for cell in cells[1:]:
        if set(by_cell[cell]) != set(reference):
            raise ValueError("Cartesian pair inventory drifted across cells")
        for key in reference:
            left = {name: value for name, value in reference[key].items() if name != "cell_id"}
            right = {name: value for name, value in by_cell[cell][key].items() if name != "cell_id"}
            if left != right:
                raise ValueError("pair marginal/state/boundary drifted across cells")
    row_ids = tuple(sorted({key[0] for key in reference}))
    column_ids = tuple(sorted({key[1] for key in reference}))
    if set(reference) != {(row, column) for row in row_ids for column in column_ids}:
        raise ValueError("expected pairs do not form a complete Cartesian product")
    row_probability = []
    row_states = []
    for row in row_ids:
        items = [reference[(row, column)] for column in column_ids]
        probabilities = {float(item["power_probability"]) for item in items}
        states = {str(item["grid_state"]) for item in items}
        if len(probabilities) != 1 or len(states) != 1:
            raise ValueError("row probability or grid state drifted across columns")
        probability = probabilities.pop()
        state = states.pop()
        if state not in {FINITE_GRID_NEED, EXOGENOUS_GRID_INFEASIBILITY}:
            raise ValueError("marginal contains an unresolved grid state")
        row_probability.append(probability)
        row_states.append(state)
    column_probability = []
    for column in column_ids:
        probabilities = {
            float(reference[(row, column)]["workload_probability"])
            for row in row_ids
        }
        if len(probabilities) != 1:
            raise ValueError("column probability drifted across rows")
        column_probability.append(probabilities.pop())
    rows = _probabilities(row_probability, "power marginal")
    columns = _probabilities(column_probability, "workload marginal")
    finite_indices = tuple(
        index for index, state in enumerate(row_states) if state == FINITE_GRID_NEED
    )
    e0_mass = sum(
        rows[index]
        for index, state in enumerate(row_states)
        if state == EXOGENOUS_GRID_INFEASIBILITY
    )
    finite_mass = 1.0 - float(e0_mass)
    if not finite_indices or finite_mass <= CERTIFICATE_TOLERANCE:
        raise ValueError("no finite-grid conditional support remains")
    return MarginalEvidence(
        row_ids=row_ids,
        row_probabilities=tuple(float(x) for x in rows),
        row_states=tuple(row_states),
        finite_row_ids=tuple(row_ids[index] for index in finite_indices),
        finite_row_probabilities=tuple(float(rows[index] / finite_mass) for index in finite_indices),
        column_ids=column_ids,
        column_probabilities=tuple(float(x) for x in columns),
        exogenous_grid_infeasibility_mass=float(e0_mass),
    )


def _interval(bounds: Mapping[str, object], metric: str) -> tuple[float, float]:
    item = bounds.get(metric)
    if not isinstance(item, Mapping) or item.get("resolved") is not True:
        raise ValueError(f"scalar bound is unresolved: {metric}")
    lower = float(item["lower"])
    upper = float(item["upper"])
    if not isfinite(lower) or not isfinite(upper) or lower > upper:
        raise ValueError(f"scalar bound is invalid: {metric}")
    return lower, upper


def _positive(bounds: Mapping[str, object], metric: str, tolerance: float) -> bool:
    return _interval(bounds, metric)[0] > tolerance


def _nonpositive(bounds: Mapping[str, object], metric: str, tolerance: float) -> bool:
    return _interval(bounds, metric)[1] <= tolerance


def _crossing(bounds: Mapping[str, object], metric: str, tolerance: float) -> bool:
    lower, upper = _interval(bounds, metric)
    return lower <= tolerance < upper


def _risk_positive(
    bounds: Mapping[str, object],
    failure: str,
    shortfall: str,
    tolerance: float,
) -> tuple[str, ...]:
    return tuple(
        metric for metric in (failure, shortfall) if _positive(bounds, metric, tolerance)
    )


def _risk_nonpositive(
    bounds: Mapping[str, object],
    failure: str,
    shortfall: str,
    tolerance: float,
) -> bool:
    return all(_nonpositive(bounds, metric, tolerance) for metric in (failure, shortfall))


def _compatible_branch(
    branches: Mapping[str, Mapping[str, object]],
    names: Sequence[str],
) -> str | None:
    for name in names:
        if branches.get(name, {}).get("status") == "compatible":
            return name
    return None


def classify_registered_attribution(
    *,
    training_disposition: str,
    scalar_bounds: Mapping[str, object],
    common_pi_branches: Mapping[str, Mapping[str, object]],
    global_preconditions_hold: bool,
    metricwise_possible_incompatible_branches: Sequence[str] = (),
    comparison_tolerance: float = COMPARISON_TOLERANCE,
) -> dict[str, object]:
    """Apply the preregistered seven-class exclusive priority."""

    if not global_preconditions_hold or training_disposition == UNRESOLVED:
        return {
            "classification": UNRESOLVED,
            "identified": False,
            "reason": "global_precondition_failed",
            "common_pi_branch": None,
        }
    if training_disposition == TRAINING_INFEASIBLE:
        return {
            "classification": TRAINING_INFEASIBLE,
            "identified": False,
            "reason": "proven_training_infeasibility_estimand_undefined",
            "common_pi_branch": None,
        }
    if training_disposition != "resolved":
        return {
            "classification": UNRESOLVED,
            "identified": False,
            "reason": "unknown_training_disposition",
            "common_pi_branch": None,
        }
    if (
        set(scalar_bounds) != set(CATEGORY_DECIDING_METRICS)
        or set(common_pi_branches) != set(COMMON_PI_BRANCHES)
        or any(branch.get("status") == "unknown" for branch in common_pi_branches.values())
    ):
        return {
            "classification": UNRESOLVED,
            "identified": False,
            "reason": "scalar_or_common_pi_inventory_unresolved",
            "common_pi_branch": None,
        }
    try:
        for metric in CATEGORY_DECIDING_METRICS:
            _interval(scalar_bounds, metric)
    except (KeyError, TypeError, ValueError):
        return {
            "classification": UNRESOLVED,
            "identified": False,
            "reason": "scalar_transport_certificate_unresolved",
            "common_pi_branch": None,
        }

    single_candidates = {
        NETWORK_FAILURE: "single_network_failure",
        NETWORK_SHORTFALL: "single_network_shortfall",
        CFE_FAILURE: "single_cfe_failure",
        CFE_SHORTFALL: "single_cfe_shortfall",
    }
    robust_single = [
        branch
        for metric, branch in single_candidates.items()
        if _positive(scalar_bounds, metric, comparison_tolerance)
        and common_pi_branches.get(branch, {}).get("status") == "compatible"
    ]
    if robust_single:
        return {
            "classification": SINGLE_SERVICE,
            "identified": True,
            "reason": "single_service_risk_robust_positive",
            "common_pi_branch": robust_single[0],
        }

    singles_nonpositive = all(
        (
            _risk_nonpositive(
                scalar_bounds,
                NETWORK_FAILURE,
                NETWORK_SHORTFALL,
                comparison_tolerance,
            ),
            _risk_nonpositive(
                scalar_bounds,
                CFE_FAILURE,
                CFE_SHORTFALL,
                comparison_tolerance,
            ),
        )
    )
    joint_branch = None
    if singles_nonpositive:
        if _positive(scalar_bounds, JOINT_INTERACTION_CAPACITY, comparison_tolerance):
            joint_branch = _compatible_branch(common_pi_branches, ("joint_capacity",))
        if joint_branch is None:
            joint_metrics = _risk_positive(
                scalar_bounds,
                JOINT_FAILURE,
                JOINT_SHORTFALL,
                comparison_tolerance,
            )
            joint_branch = _compatible_branch(
                common_pi_branches,
                tuple(
                    "joint_failure" if metric == JOINT_FAILURE else "joint_shortfall"
                    for metric in joint_metrics
                ),
            )
    if joint_branch is not None:
        return {
            "classification": JOINT_ONLY,
            "identified": True,
            "reason": "joint_only_capacity_or_service_risk_robust_positive",
            "common_pi_branch": joint_branch,
        }

    joint_nonpositive = _risk_nonpositive(
        scalar_bounds,
        JOINT_FAILURE,
        JOINT_SHORTFALL,
        comparison_tolerance,
    )
    b6_branch = None
    if singles_nonpositive and joint_nonpositive:
        if _positive(scalar_bounds, B6_UNDERPROVISIONING, comparison_tolerance):
            b6_branch = _compatible_branch(common_pi_branches, ("b6_capacity",))
        if b6_branch is None:
            b6_metrics = _risk_positive(
                scalar_bounds,
                B6_JOINT_FAILURE,
                B6_JOINT_SHORTFALL,
                comparison_tolerance,
            )
            b6_branch = _compatible_branch(
                common_pi_branches,
                tuple(
                    "b6_failure" if metric == B6_JOINT_FAILURE else "b6_shortfall"
                    for metric in b6_metrics
                ),
            )
    if b6_branch is not None:
        return {
            "classification": B6_SPECIFIC,
            "identified": True,
            "reason": "b6_capacity_or_service_risk_robust_positive",
            "common_pi_branch": b6_branch,
        }

    crossing_metrics = tuple(
        metric
        for metric in CATEGORY_DECIDING_METRICS
        if _crossing(scalar_bounds, metric, comparison_tolerance)
    )
    certified_incompatible = tuple(
        name
        for name in metricwise_possible_incompatible_branches
        if common_pi_branches.get(name, {}).get("status") == "certified_incompatible"
    )
    if crossing_metrics or certified_incompatible:
        return {
            "classification": PARTIALLY_IDENTIFIED,
            "identified": False,
            "reason": (
                "transport_sign_crosses_tolerance"
                if crossing_metrics
                else "metricwise_statements_lack_one_common_pi"
            ),
            "crossing_metrics": crossing_metrics,
            "certified_incompatible_branches": certified_incompatible,
            "common_pi_branch": None,
        }

    if all(
        _nonpositive(scalar_bounds, metric, comparison_tolerance)
        for metric in CATEGORY_DECIDING_METRICS
    ) and common_pi_branches.get("no_mechanism", {}).get("status") == "compatible":
        return {
            "classification": NO_MECHANISM,
            "identified": True,
            "reason": "all_registered_category_determinants_robust_nonpositive",
            "common_pi_branch": "no_mechanism",
        }
    return {
        "classification": UNRESOLVED,
        "identified": False,
        "reason": "exclusive_attribution_conditions_incomplete",
        "common_pi_branch": None,
    }


def _as_mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return dict(value)


def _as_sequence(value: object, label: str) -> list[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{label} must be a sequence")
    return list(value)


def _exact_keys(value: Mapping[str, object], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} inventory drifted")


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
        raise ValueError("identification evidence is not canonical JSON") from error


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _required_sha256(value: object, label: str) -> str:
    digest = str(value)
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError(f"{label} must be a lowercase SHA256 digest")
    return digest


def _validated_package_result(value: object) -> dict[str, Any]:
    result = _as_mapping(value, "package validation")
    _exact_keys(
        result,
        {
            "schema",
            "validation_passed",
            "file_count",
            "formal_result",
            "claim",
        },
        "package validation",
    )
    if (
        result["schema"] != "rq2_baseline_package_validation_v1"
        or result["validation_passed"] is not True
        or result["formal_result"] is not False
        or result["claim"] is not False
        or isinstance(result["file_count"], bool)
        or not isinstance(result["file_count"], int)
        or result["file_count"] < 6
    ):
        raise ValueError("package validation authority is incomplete")
    return result


def _package_documents(value: object) -> dict[str, dict[str, Any]]:
    documents = _as_mapping(value, "package documents")
    if set(documents) != set(PACKAGE_SCHEMAS):
        raise ValueError("package document inventory is missing or extra")
    parsed = {
        name: _as_mapping(documents[name], f"package document {name}")
        for name in PACKAGE_SCHEMAS
    }
    expected_top_level = {
        "four_arm_training_status": {"schema", "cells"},
        "four_arm_minimum_flexibility": {"schema", "cells"},
        "four_arm_pairwise_outcomes": {"schema", "pairs"},
        "E0_outcomes": {
            "schema",
            "pairs",
            "unconditional_probability_mass_by_cell",
            "public_marginal_mass_once",
        },
        "checkpoint_inventory": {
            "schema",
            "probability_tolerance",
            "expected_pairs",
            "planning",
            "pairs",
        },
        "provenance": {
            "schema",
            "resume_identity",
            "source_provenance",
            "formal_result",
            "claim",
        },
    }
    for name, expected in expected_top_level.items():
        _exact_keys(parsed[name], expected, name)
        if parsed[name]["schema"] != name:
            raise ValueError(f"package document schema drifted: {name}")
    provenance = parsed["provenance"]
    if provenance["formal_result"] is not False or provenance["claim"] is not False:
        raise ValueError("upstream package claim gate opened")
    if parsed["checkpoint_inventory"]["probability_tolerance"] != 1.0e-9:
        raise ValueError("upstream probability tolerance drifted")
    return parsed


def _canonical_cell_records(
    document: Mapping[str, object],
    *,
    label: str,
) -> tuple[tuple[str, ...], dict[str, dict[str, Any]]]:
    records = _as_sequence(document["cells"], f"{label} cells")
    order: list[str] = []
    by_cell: dict[str, dict[str, Any]] = {}
    for raw in records:
        item = _as_mapping(raw, f"{label} cell")
        _exact_keys(item, {"cell_id", "disposition", "arms"}, f"{label} cell")
        cell_id = str(item["cell_id"])
        if not cell_id or cell_id in by_cell:
            raise ValueError(f"{label} cell inventory is empty or duplicated")
        arms = _as_sequence(item["arms"], f"{label} arms")
        if [arm.get("arm_id") for arm in arms if isinstance(arm, Mapping)] != list(
            FOUR_ARM_IDS
        ):
            raise ValueError(f"{label} arm inventory drifted")
        order.append(cell_id)
        by_cell[cell_id] = item
    if not order:
        raise ValueError(f"{label} cell inventory is empty")
    return tuple(order), by_cell


def _planning_capacities(item: Mapping[str, object]) -> dict[str, float]:
    capacities: dict[str, float] = {}
    for raw in _as_sequence(item["arms"], "planning arms"):
        arm = _as_mapping(raw, "planning arm")
        _exact_keys(
            arm,
            {"arm_id", "status", "minimum_capacity", "estimand_defined", "certificate"},
            "planning arm",
        )
        if arm["status"] != "resolved" or arm["estimand_defined"] is not True:
            raise ValueError("resolved cell contains an undefined planning arm")
        capacity = float(arm["minimum_capacity"])
        if not isfinite(capacity) or capacity < 0.0:
            raise ValueError("planning capacity must be finite and nonnegative")
        capacities[str(arm["arm_id"])] = capacity
    if set(capacities) != set(FOUR_ARM_IDS):
        raise ValueError("planning capacity arm inventory drifted")
    return capacities


def _training_disposition(
    training: Mapping[str, object],
    planning: Mapping[str, object],
) -> str:
    if training["disposition"] != planning["disposition"]:
        raise ValueError("training/planning disposition drifted")
    disposition = str(training["disposition"])
    arms = _as_sequence(training["arms"], "training arms")
    for raw in arms:
        arm = _as_mapping(raw, "training arm")
        _exact_keys(
            arm,
            {
                "arm_id",
                "status",
                "pair_count",
                "failed_pair_ids",
                "unresolved_pair_ids",
                "reason",
            },
            "training arm",
        )
    if [str(arm["arm_id"]) for arm in arms] != list(FOUR_ARM_IDS):
        raise ValueError("training arm order drifted")
    if disposition == "resolved":
        if any(arm["status"] != "passed" for arm in arms):
            raise ValueError("resolved cell has a non-passing training arm")
        return "resolved"
    if disposition == TRAINING_INFEASIBLE:
        if any(arm["status"] != "not_applicable" for arm in arms):
            raise ValueError("training-infeasible cell status drifted")
        return TRAINING_INFEASIBLE
    raise ValueError("final package contains an unknown training disposition")


def _pair_key(value: Mapping[str, object]) -> tuple[str, str, str]:
    return (
        str(value["cell_id"]),
        str(value["power_block_id"]),
        str(value["workload_block_id"]),
    )


def _finite_pair_inventory(
    value: object,
) -> dict[tuple[str, str, str], dict[str, Any]]:
    pairs: dict[tuple[str, str, str], dict[str, Any]] = {}
    expected_pair_fields = {
        "schema",
        "cell_id",
        "power_block_id",
        "workload_block_id",
        "grid_state",
        "power_probability",
        "workload_probability",
        "unconditional_pair_probability",
        "right_censored",
        "boundary_state_status",
        "terminal_period_completed",
        "require_terminal_event_inactive",
        "resume_identity",
        "arms",
        "provenance",
    }
    expected_arm_fields = {
        "arm_id",
        "committed_capacity",
        "raw_causal_policy_outcome",
        "registered_service_risk_outcome",
    }
    expected_registered_fields = {
        "schema",
        "resolved",
        "unresolved_reason",
        "registered_failure",
        "registered_physical_failure",
        "service_shortfall_failure",
        "service_shortfall_amount",
        "registered_physical_violations",
        "excluded_debt_violations",
        "excluded_terminal_condition_violations",
        "right_censored",
        "raw_outcome",
    }
    expected_raw_fields = {
        "name",
        "committed_flexibility",
        "resolved",
        "hard_grid_failure",
        "physical_policy_failure",
        "service_shortfall_failure",
        "access_shortfall",
        "peak_recovery_debt",
        "terminal_recovery_debt",
        "combined_call",
        "green_served",
        "physical_violations",
    }
    for raw in _as_sequence(value, "finite pairs"):
        pair = _as_mapping(raw, "finite pair")
        _exact_keys(pair, expected_pair_fields, "finite pair")
        if (
            pair["schema"] != "rq2_baseline_finite_pair_checkpoint_v1"
            or pair["grid_state"] != FINITE_GRID_NEED
        ):
            raise ValueError("finite pair schema/state drifted")
        key = _pair_key(pair)
        if key in pairs:
            raise ValueError("finite pair inventory contains duplicates")
        arms = _as_sequence(pair["arms"], "finite pair arms")
        if [arm.get("arm_id") for arm in arms if isinstance(arm, Mapping)] != list(
            FOUR_ARM_IDS
        ):
            raise ValueError("finite pair arm inventory drifted")
        for raw_arm in arms:
            arm = _as_mapping(raw_arm, "finite pair arm")
            _exact_keys(arm, expected_arm_fields, "finite pair arm")
            registered = _as_mapping(
                arm["registered_service_risk_outcome"], "registered outcome"
            )
            raw_outcome = _as_mapping(
                arm["raw_causal_policy_outcome"], "raw outcome"
            )
            _exact_keys(raw_outcome, expected_raw_fields, "raw outcome")
            _exact_keys(registered, expected_registered_fields, "registered outcome")
            if (
                registered["schema"] != "rq2_baseline_registered_service_risk_v1"
                or registered["resolved"] is not True
                or registered["right_censored"] is not pair["right_censored"]
                or registered["raw_outcome"] != raw_outcome
                or not isinstance(registered["registered_failure"], bool)
                or not isinstance(registered["service_shortfall_failure"], bool)
            ):
                raise ValueError("registered outcome authority drifted")
        pairs[key] = pair
    return pairs


def _e0_pair_inventory(
    value: object,
) -> dict[tuple[str, str, str], dict[str, Any]]:
    pairs: dict[tuple[str, str, str], dict[str, Any]] = {}
    expected_fields = {
        "schema",
        "cell_id",
        "power_block_id",
        "workload_block_id",
        "grid_state",
        "resolved",
        "unresolved_reason",
        "power_probability",
        "workload_probability",
        "unconditional_pair_probability",
        "right_censored",
        "boundary_state_status",
        "terminal_period_completed",
        "require_terminal_event_inactive",
        "service_metrics_defined",
        "resume_identity",
        "provenance",
    }
    for raw in _as_sequence(value, "E0 pairs"):
        pair = _as_mapping(raw, "E0 pair")
        _exact_keys(pair, expected_fields, "E0 pair")
        if (
            pair["schema"] != "rq2_baseline_E0_checkpoint_v1"
            or pair["grid_state"] != EXOGENOUS_GRID_INFEASIBILITY
            or pair["resolved"] is not True
            or pair["unresolved_reason"] is not None
            or pair["service_metrics_defined"] is not False
        ):
            raise ValueError("E0 pair authority drifted")
        key = _pair_key(pair)
        if key in pairs:
            raise ValueError("E0 pair inventory contains duplicates")
        pairs[key] = pair
    return pairs


def _expected_pair_inventory(value: object) -> list[dict[str, Any]]:
    expected_fields = {
        "cell_id",
        "power_block_id",
        "workload_block_id",
        "grid_state",
        "power_probability",
        "workload_probability",
        "right_censored",
        "boundary_state_status",
        "terminal_period_completed",
        "require_terminal_event_inactive",
    }
    pairs: list[dict[str, Any]] = []
    keys: set[tuple[str, str, str]] = set()
    for raw in _as_sequence(value, "expected pairs"):
        pair = _as_mapping(raw, "expected pair")
        _exact_keys(pair, expected_fields, "expected pair")
        if pair["grid_state"] not in {
            FINITE_GRID_NEED,
            EXOGENOUS_GRID_INFEASIBILITY,
        }:
            raise ValueError("expected pair grid state is unresolved")
        key = _pair_key(pair)
        if key in keys:
            raise ValueError("expected pair inventory contains duplicates")
        keys.add(key)
        pairs.append(pair)
    return pairs


def _constant_matrix(value: float, shape: tuple[int, int]) -> tuple[tuple[float, ...], ...]:
    return tuple(tuple(float(value) for _ in range(shape[1])) for _ in range(shape[0]))


def _metric_matrices(
    *,
    cell_id: str,
    finite_pairs: Mapping[tuple[str, str, str], Mapping[str, object]],
    marginals: MarginalEvidence,
    capacities: Mapping[str, float],
) -> tuple[
    dict[str, tuple[tuple[float, ...], ...]],
    dict[str, tuple[tuple[float, ...], ...]],
    tuple[str, ...],
]:
    shape = (len(marginals.finite_row_ids), len(marginals.column_ids))
    risk_by_arm: dict[str, dict[str, list[list[float]]]] = {
        arm: {
            "failure": [[0.0] * shape[1] for _ in range(shape[0])],
            "shortfall": [[0.0] * shape[1] for _ in range(shape[0])],
            "peak_debt": [[0.0] * shape[1] for _ in range(shape[0])],
            "terminal_debt": [[0.0] * shape[1] for _ in range(shape[0])],
        }
        for arm in FOUR_ARM_IDS
    }
    right_censored: list[str] = []
    for row_index, power_id in enumerate(marginals.finite_row_ids):
        for column_index, workload_id in enumerate(marginals.column_ids):
            key = (cell_id, power_id, workload_id)
            pair = finite_pairs.get(key)
            if pair is None:
                raise ValueError("resolved cell is missing a finite Cartesian pair")
            if pair["right_censored"] is True:
                right_censored.append(f"{power_id}::{workload_id}")
            for raw_arm in _as_sequence(pair["arms"], "finite pair arms"):
                arm = _as_mapping(raw_arm, "finite pair arm")
                arm_id = str(arm["arm_id"])
                registered = _as_mapping(
                    arm["registered_service_risk_outcome"], "registered outcome"
                )
                raw_outcome = _as_mapping(
                    arm["raw_causal_policy_outcome"], "raw outcome"
                )
                values = risk_by_arm[arm_id]
                values["failure"][row_index][column_index] = float(
                    bool(registered["registered_failure"])
                )
                shortfall = float(registered["service_shortfall_amount"])
                peak_debt = float(raw_outcome["peak_recovery_debt"])
                terminal_debt = float(raw_outcome["terminal_recovery_debt"])
                if not all(isfinite(item) and item >= 0.0 for item in (shortfall, peak_debt, terminal_debt)):
                    raise ValueError("registered risk/debt metric must be nonnegative")
                values["shortfall"][row_index][column_index] = shortfall
                values["peak_debt"][row_index][column_index] = peak_debt
                values["terminal_debt"][row_index][column_index] = terminal_debt

    def frozen(values: Sequence[Sequence[float]]) -> tuple[tuple[float, ...], ...]:
        return tuple(tuple(float(value) for value in row) for row in values)

    def difference(left: str, right: str, metric: str) -> tuple[tuple[float, ...], ...]:
        return frozen(
            np.asarray(risk_by_arm[left][metric], dtype=float)
            - np.asarray(risk_by_arm[right][metric], dtype=float)
        )

    network = "network_only_shared"
    cfe = "cfe_only_shared"
    joint = "joint_correct_shared"
    b6 = "joint_b6_separate_planning_shared_execution"
    category = {
        NETWORK_FAILURE: frozen(risk_by_arm[network]["failure"]),
        NETWORK_SHORTFALL: frozen(risk_by_arm[network]["shortfall"]),
        CFE_FAILURE: frozen(risk_by_arm[cfe]["failure"]),
        CFE_SHORTFALL: frozen(risk_by_arm[cfe]["shortfall"]),
        JOINT_FAILURE: frozen(risk_by_arm[joint]["failure"]),
        JOINT_SHORTFALL: frozen(risk_by_arm[joint]["shortfall"]),
        JOINT_NETWORK_FAILURE: difference(joint, network, "failure"),
        JOINT_NETWORK_SHORTFALL: difference(joint, network, "shortfall"),
        JOINT_CFE_FAILURE: difference(joint, cfe, "failure"),
        JOINT_CFE_SHORTFALL: difference(joint, cfe, "shortfall"),
        B6_JOINT_FAILURE: difference(b6, joint, "failure"),
        B6_JOINT_SHORTFALL: difference(b6, joint, "shortfall"),
        JOINT_INTERACTION_CAPACITY: _constant_matrix(
            capacities[joint] - max(capacities[network], capacities[cfe]), shape
        ),
        B6_UNDERPROVISIONING: _constant_matrix(
            capacities[joint] - capacities[b6], shape
        ),
    }
    descriptive = {
        f"{prefix}_{suffix}": frozen(risk_by_arm[arm][field])
        for arm, prefix in (
            (network, "network_only"),
            (cfe, "cfe_only"),
            (joint, "joint_correct"),
            (b6, "joint_b6"),
        )
        for field, suffix in (
            ("peak_debt", "peak_recovery_debt"),
            ("terminal_debt", "terminal_recovery_debt"),
        )
    }
    if set(category) != set(CATEGORY_DECIDING_METRICS) or set(descriptive) != set(
        DESCRIPTIVE_DEBT_METRICS
    ):
        raise ValueError("derived metric inventory drifted")
    return category, descriptive, tuple(right_censored)


def _bound_views(
    matrices: Mapping[str, Sequence[Sequence[float]]],
    marginals: MarginalEvidence,
) -> tuple[dict[str, dict[str, object]], dict[str, dict[str, object]]]:
    certificates = {
        name: certify_scalar_transport(
            marginals.finite_row_probabilities,
            marginals.column_probabilities,
            matrix,
            metric_name=name,
        )
        for name, matrix in matrices.items()
    }
    views: dict[str, dict[str, object]] = {}
    for name, certificate in certificates.items():
        resolved = certificate.get("resolved") is True
        views[name] = {
            "resolved": resolved,
            "lower": certificate["lower"]["value"] if resolved else None,
            "upper": certificate["upper"]["value"] if resolved else None,
        }
    return certificates, views


def _upper_inequalities(
    matrices: Mapping[str, Sequence[Sequence[float]]],
    names: Sequence[str],
) -> tuple[LinearInequality, ...]:
    return tuple(
        LinearInequality(
            f"{name}_less_than_or_equal_to_tolerance",
            tuple(tuple(float(value) for value in row) for row in matrices[name]),
            COMPARISON_TOLERANCE,
        )
        for name in names
    )


def _common_pi_inventory(
    *,
    matrices: Mapping[str, Sequence[Sequence[float]]],
    scalar_bounds: Mapping[str, object],
    marginals: MarginalEvidence,
) -> tuple[dict[str, dict[str, object]], tuple[str, ...]]:
    rows = marginals.finite_row_probabilities
    columns = marginals.column_probabilities
    singles = (NETWORK_FAILURE, NETWORK_SHORTFALL, CFE_FAILURE, CFE_SHORTFALL)
    joint = (*singles, JOINT_FAILURE, JOINT_SHORTFALL)
    risk_metrics = tuple(
        metric
        for metric in CATEGORY_DECIDING_METRICS
        if metric not in {JOINT_INTERACTION_CAPACITY, B6_UNDERPROVISIONING}
    )
    branch_specs: dict[str, tuple[tuple[str, ...], str | None, str | None]] = {
        "single_network_failure": ((), NETWORK_FAILURE, None),
        "single_network_shortfall": ((), NETWORK_SHORTFALL, None),
        "single_cfe_failure": ((), CFE_FAILURE, None),
        "single_cfe_shortfall": ((), CFE_SHORTFALL, None),
        "joint_capacity": (singles, None, JOINT_INTERACTION_CAPACITY),
        "joint_failure": (singles, JOINT_FAILURE, None),
        "joint_shortfall": (singles, JOINT_SHORTFALL, None),
        "b6_capacity": (joint, None, B6_UNDERPROVISIONING),
        "b6_failure": (joint, B6_JOINT_FAILURE, None),
        "b6_shortfall": (joint, B6_JOINT_SHORTFALL, None),
    }
    branches: dict[str, dict[str, object]] = {}
    incompatible_metricwise_possible: list[str] = []
    for branch_name, (mandatory_names, candidate_name, constant_name) in branch_specs.items():
        mandatory = _upper_inequalities(matrices, mandatory_names)
        if candidate_name is not None:
            branch = certify_common_pi_branch(
                rows,
                columns,
                branch_name=branch_name,
                mandatory_inequalities=mandatory,
                candidate_matrix=matrices[candidate_name],
            )
            candidate_possible = _interval(scalar_bounds, candidate_name)[1] > COMPARISON_TOLERANCE
        else:
            assert constant_name is not None
            constant = float(np.asarray(matrices[constant_name], dtype=float)[0, 0])
            branch = certify_common_pi_branch(
                rows,
                columns,
                branch_name=branch_name,
                mandatory_inequalities=mandatory,
                candidate_constant=constant,
            )
            candidate_possible = constant > COMPARISON_TOLERANCE
        mandatory_possible = all(
            _interval(scalar_bounds, name)[0] <= COMPARISON_TOLERANCE
            for name in mandatory_names
        )
        if (
            branch["status"] == "certified_incompatible"
            and mandatory_possible
            and candidate_possible
        ):
            incompatible_metricwise_possible.append(branch_name)
        branches[branch_name] = branch

    capacity_nonpositive = all(
        _interval(scalar_bounds, name)[1] <= COMPARISON_TOLERANCE
        for name in (JOINT_INTERACTION_CAPACITY, B6_UNDERPROVISIONING)
    )
    if capacity_nonpositive:
        no_mechanism = certify_common_pi_branch(
            rows,
            columns,
            branch_name="no_mechanism",
            mandatory_inequalities=_upper_inequalities(matrices, risk_metrics),
            feasibility_only=True,
        )
        individually_possible = all(
            _interval(scalar_bounds, name)[0] <= COMPARISON_TOLERANCE
            for name in risk_metrics
        )
        if no_mechanism["status"] == "certified_incompatible" and individually_possible:
            incompatible_metricwise_possible.append("no_mechanism")
    else:
        no_mechanism = {
            "schema": "rq2_baseline_common_pi_branch_certificate_v1",
            "branch": "no_mechanism",
            "status": "not_compatible",
            "reason": "capacity_determinant_not_robust_nonpositive",
            "phase_one": None,
            "candidate": None,
        }
    branches["no_mechanism"] = no_mechanism
    if set(branches) != set(COMMON_PI_BRANCHES):
        raise ValueError("common-pi branch inventory drifted")
    return branches, tuple(incompatible_metricwise_possible)


def _identify_validated_package_documents(
    *,
    package_validation: Mapping[str, object],
    package_documents: Mapping[str, object],
    package_manifest_sha256: str | None = None,
    stable_snapshot_verified: bool = False,
) -> dict[str, object]:
    """Private test seam for documents already checked by the package validator."""

    validation = _validated_package_result(package_validation)
    documents = _package_documents(package_documents)
    if stable_snapshot_verified:
        manifest_sha256 = _required_sha256(
            package_manifest_sha256, "package manifest SHA256"
        )
    elif package_manifest_sha256 is not None:
        raise ValueError("an unverified package cannot carry a manifest authority")
    else:
        manifest_sha256 = None
    training_order, training_by_cell = _canonical_cell_records(
        documents["four_arm_training_status"], label="training"
    )
    planning_order, planning_by_cell = _canonical_cell_records(
        documents["four_arm_minimum_flexibility"], label="planning"
    )
    if planning_order != training_order:
        raise ValueError("training/planning cell order drifted")
    dispositions = {
        cell_id: _training_disposition(
            training_by_cell[cell_id], planning_by_cell[cell_id]
        )
        for cell_id in training_order
    }
    expected_pairs = _expected_pair_inventory(
        documents["checkpoint_inventory"]["expected_pairs"]
    )
    marginal_evidence = derive_marginal_evidence(expected_pairs, training_order)
    finite_pairs = _finite_pair_inventory(
        documents["four_arm_pairwise_outcomes"]["pairs"]
    )
    e0 = documents["E0_outcomes"]
    e0_pairs = _e0_pair_inventory(e0["pairs"])
    required_expected = {
        _pair_key(pair): pair
        for pair in expected_pairs
        if dispositions[str(pair["cell_id"])] == "resolved"
    }
    observed_pairs = {**finite_pairs, **e0_pairs}
    if len(observed_pairs) != len(finite_pairs) + len(e0_pairs):
        raise ValueError("finite and E0 pair inventories overlap")
    if set(observed_pairs) != set(required_expected):
        raise ValueError("resolved pair inventory is missing or extra")
    for key, pair in observed_pairs.items():
        expected = required_expected[key]
        for field in (
            "grid_state",
            "power_probability",
            "workload_probability",
            "right_censored",
            "boundary_state_status",
            "terminal_period_completed",
            "require_terminal_event_inactive",
        ):
            if pair[field] != expected[field]:
                raise ValueError(f"resolved pair {field} drifted")
    e0_mass_by_cell = _as_mapping(
        e0["unconditional_probability_mass_by_cell"], "E0 mass by cell"
    )
    if set(e0_mass_by_cell) != set(training_order) or any(
        abs(float(value) - marginal_evidence.exogenous_grid_infeasibility_mass)
        > CERTIFICATE_TOLERANCE
        for value in e0_mass_by_cell.values()
    ):
        raise ValueError("E0 marginal mass disagrees with expected pairs")
    if (
        abs(
            float(e0["public_marginal_mass_once"])
            - marginal_evidence.exogenous_grid_infeasibility_mass
        )
        > CERTIFICATE_TOLERANCE
    ):
        raise ValueError("public E0 marginal mass drifted")

    cells: list[dict[str, object]] = []
    for cell_id in training_order:
        disposition = dispositions[cell_id]
        if disposition == TRAINING_INFEASIBLE:
            classification = classify_registered_attribution(
                training_disposition=disposition,
                scalar_bounds={},
                common_pi_branches={},
                global_preconditions_hold=True,
            )
            cells.append(
                {
                    "cell_id": cell_id,
                    "training_disposition": disposition,
                    "scalar_transport_endpoints": {},
                    "arm_and_contrast_cell_bounds": {},
                    "common_pi_multimetric_witnesses": {},
                    "descriptive_recovery_debt_bounds": {},
                    "right_censored_pair_ids": [],
                    "classification": classification,
                }
            )
            continue
        capacities = _planning_capacities(planning_by_cell[cell_id])
        matrices, debt_matrices, right_censored = _metric_matrices(
            cell_id=cell_id,
            finite_pairs=finite_pairs,
            marginals=marginal_evidence,
            capacities=capacities,
        )
        endpoint_certificates, scalar_bounds = _bound_views(matrices, marginal_evidence)
        debt_certificates, _ = _bound_views(debt_matrices, marginal_evidence)
        endpoints_resolved = all(
            certificate.get("resolved") is True
            and certificate.get("sharp") is True
            for certificate in endpoint_certificates.values()
        )
        if endpoints_resolved:
            branches, incompatible = _common_pi_inventory(
                matrices=matrices,
                scalar_bounds=scalar_bounds,
                marginals=marginal_evidence,
            )
        else:
            branches = {
                name: {"branch": name, "status": "unknown"}
                for name in COMMON_PI_BRANCHES
            }
            incompatible = ()
        global_preconditions_hold = endpoints_resolved and all(
            branch.get("status") != "unknown" for branch in branches.values()
        )
        classification = classify_registered_attribution(
            training_disposition=disposition,
            scalar_bounds=scalar_bounds,
            common_pi_branches=branches,
            global_preconditions_hold=global_preconditions_hold,
            metricwise_possible_incompatible_branches=incompatible,
        )
        cells.append(
            {
                "cell_id": cell_id,
                "training_disposition": disposition,
                "scalar_transport_endpoints": endpoint_certificates,
                "arm_and_contrast_cell_bounds": scalar_bounds,
                "common_pi_multimetric_witnesses": branches,
                "descriptive_recovery_debt_bounds": debt_certificates,
                "right_censored_pair_ids": list(right_censored),
                "classification": classification,
            }
        )
    return {
        "schema": "rq2_baseline_robustness_identification_payload_v1",
        "package_validation": validation,
        "upstream_package_authority": {
            "schema": "rq2_baseline_upstream_package_authority_v1",
            "manifest_sha256": manifest_sha256,
            "stable_snapshot_verified": stable_snapshot_verified,
            "package_validation_sha256": _canonical_sha256(validation),
            "provenance_sha256": _canonical_sha256(documents["provenance"]),
        },
        "marginal_evidence": {
            "row_ids": list(marginal_evidence.row_ids),
            "row_probabilities": list(marginal_evidence.row_probabilities),
            "row_states": list(marginal_evidence.row_states),
            "finite_row_ids": list(marginal_evidence.finite_row_ids),
            "finite_row_probabilities": list(
                marginal_evidence.finite_row_probabilities
            ),
            "column_ids": list(marginal_evidence.column_ids),
            "column_probabilities": list(marginal_evidence.column_probabilities),
            "E0_unconditional_probability_mass": (
                marginal_evidence.exogenous_grid_infeasibility_mass
            ),
            "E0_conditional_service_metrics_defined": False,
        },
        "cells": cells,
        "T1_mw_only_reference": {
            "raw_grid_call_trajectory_path": None,
            "raw_cfe_call_trajectory_path": None,
            "implementation_bound": False,
            "status": "future_raw_trajectory_input_required",
        },
        "provenance": documents["provenance"],
        "formal_result": False,
        "claim": False,
    }


def identify_final_package(
    package_directory: Path,
    *,
    expected_manifest_sha256: str,
) -> dict[str, object]:
    """Validate then identify one canonical package without writing artifacts."""

    from src.evaluation.rq2_baseline_robustness_package_v1 import (
        validate_final_package,
    )

    directory = Path(package_directory)
    manifest_authority = _required_sha256(
        expected_manifest_sha256, "expected package manifest SHA256"
    )
    validation = validate_final_package(directory)
    captured_bytes = {
        name: (directory / f"{name}.json").read_bytes()
        for name in PACKAGE_SCHEMAS
    }
    captured_manifest_bytes = (directory / "SHA256SUMS.json").read_bytes()
    if hashlib.sha256(captured_manifest_bytes).hexdigest() != manifest_authority:
        raise ValueError("package manifest disagrees with the supplied authority")
    second_validation = validate_final_package(directory)
    if validation != second_validation:
        raise ValueError("package validation receipt drifted during capture")
    if (directory / "SHA256SUMS.json").read_bytes() != captured_manifest_bytes:
        raise ValueError("package manifest drifted during capture")
    try:
        captured_manifest = _as_mapping(
            json.loads(captured_manifest_bytes), "captured package manifest"
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("captured package manifest is invalid") from error
    _exact_keys(
        captured_manifest,
        {"schema", "files"},
        "captured package manifest",
    )
    if captured_manifest["schema"] != "rq2_baseline_package_manifest_v1":
        raise ValueError("captured package manifest schema drifted")
    manifest_files = _as_mapping(
        captured_manifest["files"], "captured manifest files"
    )
    for name, payload in captured_bytes.items():
        relative = f"{name}.json"
        digest = hashlib.sha256(payload).hexdigest()
        if manifest_files.get(relative) != digest:
            raise ValueError(f"captured package member hash drifted: {relative}")
        if (directory / relative).read_bytes() != payload:
            raise ValueError(f"package member drifted during capture: {relative}")
    try:
        documents = {
            name: json.loads(payload.decode("utf-8"))
            for name, payload in captured_bytes.items()
        }
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("captured package document is invalid") from error
    return _identify_validated_package_documents(
        package_validation=second_validation,
        package_documents=documents,
        package_manifest_sha256=manifest_authority,
        stable_snapshot_verified=True,
    )


def validate_identification_payload(
    payload: Mapping[str, object],
    *,
    package_directory: Path,
    package_manifest_sha256: str,
) -> dict[str, object]:
    """Reidentify the canonical package and reject any payload evidence drift."""

    observed = _as_mapping(payload, "identification payload")
    rebuilt = identify_final_package(
        package_directory,
        expected_manifest_sha256=package_manifest_sha256,
    )
    if _canonical_bytes(observed) != _canonical_bytes(rebuilt):
        raise ValueError("identification payload drifted from the canonical package")
    return rebuilt


def canonical_identification_payload_sha256(payload: Mapping[str, object]) -> str:
    """Return the canonical digest used by the report evidence binding."""

    return _canonical_sha256(_as_mapping(payload, "identification payload"))
