"""Optimal-transport couplings for independently observed trace marginals."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from numbers import Real

import numpy as np
from scipy.optimize import linprog

_TOLERANCE = 1.0e-9


@dataclass(frozen=True)
class TransportBound:
    minimum: float
    maximum: float
    minimizing_coupling: tuple[tuple[float, ...], ...]
    maximizing_coupling: tuple[tuple[float, ...], ...]
    minimum_status: str
    maximum_status: str


def _probabilities(name: str, values: Iterable[Real]) -> np.ndarray:
    result = np.asarray(tuple(values), dtype=float)
    if result.ndim != 1 or result.size == 0:
        raise ValueError(f"{name} must be a nonempty vector")
    if not np.all(np.isfinite(result)) or np.any(result < 0.0):
        raise ValueError(f"{name} must be finite and nonnegative")
    if abs(float(result.sum()) - 1.0) > _TOLERANCE:
        raise ValueError(f"{name} must sum to one")
    return result


def _cost_matrix(values: Iterable[Iterable[Real]]) -> np.ndarray:
    matrix = np.asarray(tuple(tuple(row) for row in values), dtype=float)
    if matrix.ndim != 2 or 0 in matrix.shape:
        raise ValueError("metric must be a nonempty matrix")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("metric must contain only finite values")
    return matrix


def _constraints(
    rows: np.ndarray,
    columns: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    n_rows = rows.size
    n_columns = columns.size
    equalities = []
    rhs = []
    for row in range(n_rows):
        coefficients = np.zeros((n_rows, n_columns))
        coefficients[row, :] = 1.0
        equalities.append(coefficients.ravel())
        rhs.append(rows[row])
    # The last column equation is redundant once all row sums are fixed.
    for column in range(n_columns - 1):
        coefficients = np.zeros((n_rows, n_columns))
        coefficients[:, column] = 1.0
        equalities.append(coefficients.ravel())
        rhs.append(columns[column])
    return np.asarray(equalities), np.asarray(rhs)


def _solve(
    cost: np.ndarray,
    rows: np.ndarray,
    columns: np.ndarray,
    support: np.ndarray,
    *,
    maximize: bool,
) -> tuple[float, np.ndarray, str]:
    objective = -cost.ravel() if maximize else cost.ravel()
    bounds = [
        (0.0, None) if allowed else (0.0, 0.0)
        for allowed in support.ravel()
    ]
    a_eq, b_eq = _constraints(rows, columns)
    result = linprog(
        objective,
        A_eq=a_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )
    if not result.success or result.x is None:
        raise ValueError(f"coupling polytope is infeasible: {result.message}")
    coupling = result.x.reshape(cost.shape)
    if (
        np.max(np.abs(coupling.sum(axis=1) - rows)) > _TOLERANCE
        or np.max(np.abs(coupling.sum(axis=0) - columns)) > _TOLERANCE
    ):
        raise AssertionError("transport solution violates marginal constraints")
    value = float(np.sum(coupling * cost))
    return value, coupling, str(result.message)


def bound_transport_expectation(
    row_probabilities: Iterable[Real],
    column_probabilities: Iterable[Real],
    metric: Iterable[Iterable[Real]],
    *,
    allowed_support: Iterable[Iterable[bool]] | None = None,
) -> TransportBound:
    """Bound an expected pairwise metric over every admissible coupling."""

    rows = _probabilities("row_probabilities", row_probabilities)
    columns = _probabilities("column_probabilities", column_probabilities)
    cost = _cost_matrix(metric)
    if cost.shape != (rows.size, columns.size):
        raise ValueError("metric shape must match both marginals")
    if allowed_support is None:
        support = np.ones(cost.shape, dtype=bool)
    else:
        support = np.asarray(
            tuple(tuple(row) for row in allowed_support), dtype=bool
        )
        if support.shape != cost.shape:
            raise ValueError("allowed_support shape must match metric")
    minimum, minimizing, minimum_status = _solve(
        cost, rows, columns, support, maximize=False
    )
    maximum, maximizing, maximum_status = _solve(
        cost, rows, columns, support, maximize=True
    )
    if minimum > maximum + _TOLERANCE:
        raise AssertionError("transport lower bound exceeds upper bound")
    return TransportBound(
        minimum=minimum,
        maximum=maximum,
        minimizing_coupling=tuple(tuple(float(x) for x in row) for row in minimizing),
        maximizing_coupling=tuple(tuple(float(x) for x in row) for row in maximizing),
        minimum_status=minimum_status,
        maximum_status=maximum_status,
    )


def quantile_coupling(
    row_probabilities: Iterable[Real],
    column_probabilities: Iterable[Real],
    row_scores: Iterable[Real],
    column_scores: Iterable[Real],
    *,
    reverse_columns: bool = False,
) -> tuple[tuple[float, ...], ...]:
    """Construct a comonotone or countermonotone discrete quantile coupling."""

    rows = _probabilities("row_probabilities", row_probabilities)
    columns = _probabilities("column_probabilities", column_probabilities)
    row_score = np.asarray(tuple(row_scores), dtype=float)
    column_score = np.asarray(tuple(column_scores), dtype=float)
    if row_score.shape != rows.shape or column_score.shape != columns.shape:
        raise ValueError("score vectors must match their marginals")
    if not np.all(np.isfinite(row_score)) or not np.all(np.isfinite(column_score)):
        raise ValueError("scores must be finite")
    row_order = np.argsort(row_score, kind="stable")
    column_order = np.argsort(column_score, kind="stable")
    if reverse_columns:
        column_order = column_order[::-1]
    remaining_rows = rows.copy()
    remaining_columns = columns.copy()
    coupling = np.zeros((rows.size, columns.size))
    i = j = 0
    while i < rows.size and j < columns.size:
        row = int(row_order[i])
        column = int(column_order[j])
        mass = min(remaining_rows[row], remaining_columns[column])
        coupling[row, column] += mass
        remaining_rows[row] -= mass
        remaining_columns[column] -= mass
        if remaining_rows[row] <= _TOLERANCE:
            i += 1
        if remaining_columns[column] <= _TOLERANCE:
            j += 1
    if abs(float(coupling.sum()) - 1.0) > _TOLERANCE:
        raise AssertionError("quantile coupling did not allocate all mass")
    return tuple(tuple(float(x) for x in row) for row in coupling)
