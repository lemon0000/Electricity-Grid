"""Joint-coupling region checks and marginal bootstrap for RQ2."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isfinite

import numpy as np
from scipy.optimize import linprog

from src.scenarios.block_coupling import bound_transport_expectation

R1 = "R1_no_conflict"
R2 = "R2_double_commitment_risk"
R3 = "R3_common_insufficiency"

_DELTA_METRICS = (
    "delta_failure_probability",
    "delta_expected_shortfall",
    "flexibility_underprovisioning",
    "delta_peak_recovery_debt",
    "delta_terminal_recovery_debt",
)


@dataclass(frozen=True)
class JointRegionCompatibility:
    compatible_regions: tuple[str, ...]
    witness_couplings: dict[str, tuple[tuple[float, ...], ...]]
    solver_status: dict[str, str]


@dataclass(frozen=True)
class BootstrapTransportInterval:
    confidence_level: float
    replicates: int
    seed: int
    lower_endpoint_interval: tuple[float, float]
    upper_endpoint_interval: tuple[float, float]


def _probabilities(values: Sequence[float], label: str) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    if (
        result.ndim != 1
        or result.size == 0
        or not np.all(np.isfinite(result))
        or np.any(result < 0.0)
        or abs(float(result.sum()) - 1.0) > 1.0e-9
    ):
        raise ValueError(f"{label} must be a finite probability vector")
    return result


def _metric_matrices(
    metrics: Mapping[str, Sequence[Sequence[float]]],
    shape: tuple[int, int],
) -> dict[str, np.ndarray]:
    required = {
        *_DELTA_METRICS,
        "correct_failure_probability",
        "correct_expected_shortfall",
    }
    if set(metrics) != required:
        raise ValueError("joint-region metric inventory drifted")
    result = {}
    for name, values in metrics.items():
        matrix = np.asarray(values, dtype=float)
        if matrix.shape != shape or not np.all(np.isfinite(matrix)):
            raise ValueError(f"{name} must be a finite matrix with shape {shape}")
        result[name] = matrix
    return result


def _transport_equalities(
    rows: np.ndarray,
    columns: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    n_rows = rows.size
    n_columns = columns.size
    constraints = []
    rhs = []
    for row in range(n_rows):
        values = np.zeros((n_rows, n_columns))
        values[row, :] = 1.0
        constraints.append(values.ravel())
        rhs.append(rows[row])
    for column in range(n_columns - 1):
        values = np.zeros((n_rows, n_columns))
        values[:, column] = 1.0
        constraints.append(values.ravel())
        rhs.append(columns[column])
    return np.asarray(constraints), np.asarray(rhs)


def _solve(
    objective: np.ndarray,
    rows: np.ndarray,
    columns: np.ndarray,
    inequalities: list[tuple[np.ndarray, float]],
) -> tuple[bool, np.ndarray | None, str, float | None]:
    a_eq, b_eq = _transport_equalities(rows, columns)
    a_ub = (
        np.asarray([coefficients.ravel() for coefficients, _ in inequalities])
        if inequalities
        else None
    )
    b_ub = (
        np.asarray([bound for _, bound in inequalities])
        if inequalities
        else None
    )
    result = linprog(
        objective.ravel(),
        A_ub=a_ub,
        b_ub=b_ub,
        A_eq=a_eq,
        b_eq=b_eq,
        bounds=(0.0, None),
        method="highs",
    )
    if result.success and result.x is not None:
        return (
            True,
            result.x.reshape(objective.shape),
            str(result.message),
            float(np.sum(result.x.reshape(objective.shape) * objective)),
        )
    if result.status == 2:
        return False, None, str(result.message), None
    raise RuntimeError(f"joint-region LP unresolved: {result.message}")


def _band(
    matrix: np.ndarray,
    tolerance: float,
) -> list[tuple[np.ndarray, float]]:
    return [(matrix, tolerance), (-matrix, tolerance)]


def joint_region_compatibility(
    row_probabilities: Sequence[float],
    column_probabilities: Sequence[float],
    metrics: Mapping[str, Sequence[Sequence[float]]],
    *,
    probability_tolerance: float = 1.0e-9,
    outcome_tolerance: float = 1.0e-6,
) -> JointRegionCompatibility:
    """Test each region using one common transport coupling."""

    rows = _probabilities(row_probabilities, "row_probabilities")
    columns = _probabilities(column_probabilities, "column_probabilities")
    if (
        not isfinite(probability_tolerance)
        or probability_tolerance < 0.0
        or not isfinite(outcome_tolerance)
        or outcome_tolerance < 0.0
    ):
        raise ValueError("tolerances must be finite and nonnegative")
    matrices = _metric_matrices(metrics, (rows.size, columns.size))

    def tolerance(metric: str) -> float:
        return (
            probability_tolerance
            if metric in {
                "delta_failure_probability",
                "correct_failure_probability",
            }
            else outcome_tolerance
        )

    zero = np.zeros((rows.size, columns.size))
    compatible = []
    witnesses: dict[str, tuple[tuple[float, ...], ...]] = {}
    statuses = {}

    r1_constraints = []
    for metric in _DELTA_METRICS:
        r1_constraints.extend(_band(matrices[metric], tolerance(metric)))
    r1_constraints.extend(
        (
            (
                matrices["correct_failure_probability"],
                probability_tolerance,
            ),
            (
                matrices["correct_expected_shortfall"],
                outcome_tolerance,
            ),
        )
    )
    feasible, witness, status, _ = _solve(
        zero,
        rows,
        columns,
        r1_constraints,
    )
    statuses[R1] = status
    if feasible and witness is not None:
        compatible.append(R1)
        witnesses[R1] = tuple(
            tuple(float(value) for value in row) for row in witness
        )

    r2_constraints = [
        (-matrices[metric], tolerance(metric)) for metric in _DELTA_METRICS
    ]
    feasible, witness, status, _ = _solve(
        zero,
        rows,
        columns,
        r2_constraints,
    )
    statuses[R2] = status
    r2_witness = None
    if feasible:
        for metric in _DELTA_METRICS:
            strict, candidate, strict_status, minimized_negative = _solve(
                -matrices[metric],
                rows,
                columns,
                r2_constraints,
            )
            statuses[f"{R2}:{metric}"] = strict_status
            maximum = (
                None if minimized_negative is None else -minimized_negative
            )
            if strict and maximum is not None and maximum > tolerance(metric):
                r2_witness = candidate
                break
    if r2_witness is not None:
        compatible.append(R2)
        witnesses[R2] = tuple(
            tuple(float(value) for value in row) for row in r2_witness
        )

    r3_constraints = []
    for metric in _DELTA_METRICS:
        r3_constraints.extend(_band(matrices[metric], tolerance(metric)))
    r3_witness = None
    for metric in (
        "correct_failure_probability",
        "correct_expected_shortfall",
    ):
        feasible, candidate, status, minimized_negative = _solve(
            -matrices[metric],
            rows,
            columns,
            r3_constraints,
        )
        statuses[f"{R3}:{metric}"] = status
        maximum = None if minimized_negative is None else -minimized_negative
        if feasible and maximum is not None and maximum > tolerance(metric):
            r3_witness = candidate
            break
    if r3_witness is not None:
        compatible.append(R3)
        witnesses[R3] = tuple(
            tuple(float(value) for value in row) for row in r3_witness
        )
    return JointRegionCompatibility(
        compatible_regions=tuple(compatible),
        witness_couplings=witnesses,
        solver_status=statuses,
    )


def bootstrap_transport_interval(
    row_probabilities: Sequence[float],
    column_probabilities: Sequence[float],
    metric: Sequence[Sequence[float]],
    *,
    replicates: int,
    seed: int,
    confidence_level: float,
) -> BootstrapTransportInterval:
    """Bootstrap marginal blocks and recompute both transport endpoints."""

    rows = _probabilities(row_probabilities, "row_probabilities")
    columns = _probabilities(column_probabilities, "column_probabilities")
    matrix = np.asarray(metric, dtype=float)
    if matrix.shape != (rows.size, columns.size) or not np.all(
        np.isfinite(matrix)
    ):
        raise ValueError("metric shape must match both marginals")
    if isinstance(replicates, bool) or not isinstance(replicates, int) or replicates <= 0:
        raise ValueError("replicates must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    if not isfinite(confidence_level) or not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must lie in (0, 1)")
    generator = np.random.default_rng(seed)
    lower_endpoints = []
    upper_endpoints = []
    for _ in range(replicates):
        row_counts = generator.multinomial(rows.size, rows)
        column_counts = generator.multinomial(columns.size, columns)
        bound = bound_transport_expectation(
            row_counts / rows.size,
            column_counts / columns.size,
            matrix,
        )
        lower_endpoints.append(bound.minimum)
        upper_endpoints.append(bound.maximum)
    alpha = (1.0 - confidence_level) / 2.0
    return BootstrapTransportInterval(
        confidence_level=confidence_level,
        replicates=replicates,
        seed=seed,
        lower_endpoint_interval=(
            float(np.quantile(lower_endpoints, alpha)),
            float(np.quantile(lower_endpoints, 1.0 - alpha)),
        ),
        upper_endpoint_interval=(
            float(np.quantile(upper_endpoints, alpha)),
            float(np.quantile(upper_endpoints, 1.0 - alpha)),
        ),
    )
