"""Analytic bounds for two services sharing one flexibility resource.

The results in this module deliberately cover only claims that do not depend
on a fitted job-to-power model. They operate on dimensionless or consistently
scaled traces and make no empirical-probability or engineering-certification
claim.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite
from numbers import Real


@dataclass(frozen=True)
class InstantaneousCommitmentBound:
    shared_required_capacity: float
    separately_committed_capacity: float
    duplicate_commitment_gap: float
    gap_upper_bound: float
    peak_overlap_witness_index: int


@dataclass(frozen=True)
class RecoveryDebtBound:
    minimum_peak_debt: float
    terminal_debt_lower_bound: float
    infeasible_under_debt_limit: bool
    infeasible_under_terminal_limit: bool


def _trace(name: str, values: Iterable[Real]) -> tuple[float, ...]:
    result = []
    for index, raw in enumerate(values):
        if isinstance(raw, bool) or not isinstance(raw, Real):
            raise TypeError(f"{name}[{index}] must be numeric")
        value = float(raw)
        if not isfinite(value) or value < 0.0:
            raise ValueError(f"{name}[{index}] must be finite and nonnegative")
        result.append(value)
    if not result:
        raise ValueError(f"{name} must be nonempty")
    return tuple(result)


def instantaneous_commitment_bound(
    grid_call: Iterable[Real],
    cfe_call: Iterable[Real],
) -> InstantaneousCommitmentBound:
    """Return the exact MW-only duplicate-commitment gap.

    For nonnegative service calls ``g`` and ``c``, a shared physical resource
    requires ``max_t(g_t + c_t)``. Two independently certified services would
    record only ``max(max_t g_t, max_t c_t)``. Their difference is nonnegative
    and cannot exceed the smaller individual peak.
    """

    grid = _trace("grid_call", grid_call)
    cfe = _trace("cfe_call", cfe_call)
    if len(grid) != len(cfe):
        raise ValueError("grid_call and cfe_call must have equal length")
    combined = tuple(g + c for g, c in zip(grid, cfe))
    witness = max(range(len(combined)), key=combined.__getitem__)
    shared = combined[witness]
    separate = max(max(grid), max(cfe))
    gap = shared - separate
    upper = min(max(grid), max(cfe))
    if gap < -1.0e-12 or gap > upper + 1.0e-12:
        raise AssertionError("analytic duplicate-commitment bound failed")
    return InstantaneousCommitmentBound(
        shared_required_capacity=shared,
        separately_committed_capacity=separate,
        duplicate_commitment_gap=max(gap, 0.0),
        gap_upper_bound=upper,
        peak_overlap_witness_index=witness,
    )


def recovery_debt_bound(
    combined_call: Iterable[Real],
    recovery_availability: Iterable[Real],
    *,
    time_step_hours: Real,
    recovery_efficiency: Real,
    maximum_debt: Real,
    terminal_debt_limit: Real,
) -> RecoveryDebtBound:
    """Compute the minimum debt implied by an exogenous call trajectory.

    ``recovery_availability`` is already net of all business, connection and
    CFE-compatible headroom limits. The recursion greedily applies all useful
    recovery after each call. This is optimal for minimizing every prefix debt
    when recovery has no intertemporal cost or ramp constraint.
    """

    call = _trace("combined_call", combined_call)
    recovery = _trace("recovery_availability", recovery_availability)
    if len(call) != len(recovery):
        raise ValueError(
            "combined_call and recovery_availability must have equal length"
        )
    scalars = {}
    for name, raw in (
        ("time_step_hours", time_step_hours),
        ("recovery_efficiency", recovery_efficiency),
        ("maximum_debt", maximum_debt),
        ("terminal_debt_limit", terminal_debt_limit),
    ):
        if isinstance(raw, bool) or not isinstance(raw, Real):
            raise TypeError(f"{name} must be numeric")
        value = float(raw)
        if not isfinite(value) or value < 0.0:
            raise ValueError(f"{name} must be finite and nonnegative")
        scalars[name] = value
    if scalars["time_step_hours"] <= 0.0:
        raise ValueError("time_step_hours must be positive")
    if not 0.0 < scalars["recovery_efficiency"] <= 1.0:
        raise ValueError("recovery_efficiency must lie in (0, 1]")

    debt = 0.0
    peak = 0.0
    dt = scalars["time_step_hours"]
    efficiency = scalars["recovery_efficiency"]
    for deferred, available in zip(call, recovery):
        if deferred > 1.0e-12 and available > 1.0e-12:
            raise ValueError(
                "recovery_availability must be zero during an active call"
            )
        debt += deferred * dt
        debt -= min(debt, efficiency * available * dt)
        peak = max(peak, debt)
    return RecoveryDebtBound(
        minimum_peak_debt=peak,
        terminal_debt_lower_bound=debt,
        infeasible_under_debt_limit=peak > scalars["maximum_debt"] + 1.0e-12,
        infeasible_under_terminal_limit=(
            debt > scalars["terminal_debt_limit"] + 1.0e-12
        ),
    )
