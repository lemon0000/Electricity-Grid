"""AC power-flow validation for feasible DC dispatches."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

import numpy as np
from pypower.api import case24_ieee_rts, ppoption, runpf
from pypower.idx_brch import (
    BR_STATUS,
    PF,
    PT,
    QF,
    QT,
    RATE_A,
    RATE_B,
    RATE_C,
)
from pypower.idx_bus import VM, VMAX, VMIN
from pypower.idx_gen import GEN_STATUS, PG, PMAX, PMIN, QG, QMAX, QMIN

from .ac_case import configure_rts24_ac_case
from .dc_opf import DcOpfResult
from .rts24 import Rts24Data


@dataclass(frozen=True)
class AcValidationResult:
    evaluated: bool
    converged: bool
    secure: bool
    status: str
    branch_rating: str
    min_voltage_pu: float | None
    max_voltage_pu: float | None
    max_voltage_violation_pu: float | None
    max_branch_loading_fraction: float | None
    max_loaded_branch_index: int | None
    max_active_power_violation_mw: float | None
    max_reactive_power_violation_mvar: float | None
    reference_bus: int | None
    active_generator_indices: tuple[int, ...]
    generator_commitment_applied: bool
    requested_generation_mw: float | None
    ac_generation_mw: float | None
    slack_and_loss_adjustment_mw: float | None


def _not_evaluated(
    status: str,
    branch_rating: str,
    *,
    reference_bus: int | None = None,
    active_generator_indices: tuple[int, ...] = (),
    generator_commitment_applied: bool = False,
) -> AcValidationResult:
    return AcValidationResult(
        evaluated=False,
        converged=False,
        secure=False,
        status=status,
        branch_rating=branch_rating,
        min_voltage_pu=None,
        max_voltage_pu=None,
        max_voltage_violation_pu=None,
        max_branch_loading_fraction=None,
        max_loaded_branch_index=None,
        max_active_power_violation_mw=None,
        max_reactive_power_violation_mvar=None,
        reference_bus=reference_bus,
        active_generator_indices=active_generator_indices,
        generator_commitment_applied=generator_commitment_applied,
        requested_generation_mw=None,
        ac_generation_mw=None,
        slack_and_loss_adjustment_mw=None,
    )


def validate_ac_power_flow(
    data: Rts24Data,
    dc_result: DcOpfResult,
    *,
    generator_commitment: Mapping[int, bool] | None = None,
    branch_rating: str = "rate_a",
    voltage_tolerance_pu: float = 1.0e-6,
    power_tolerance_mw: float = 1.0e-4,
    loading_tolerance: float = 1.0e-6,
) -> AcValidationResult:
    """Run an AC power flow using a feasible DC dispatch as the set point."""

    if not dc_result.feasible:
        return _not_evaluated("dc_infeasible", branch_rating)
    if len(dc_result.reference_buses) != 1:
        return _not_evaluated("islanding", branch_rating)

    rating_column = {
        "rate_a": RATE_A,
        "rate_b": RATE_B,
        "rate_c": RATE_C,
    }.get(branch_rating)
    if rating_column is None:
        raise ValueError(f"Unknown branch rating '{branch_rating}'")

    case = case24_ieee_rts()
    if len(case["gen"]) != len(data.generators) or len(case["branch"]) != len(
        data.branches
    ):
        raise ValueError("DC result does not align with the PYPOWER RTS-24 case")

    case["gen"][:, PG] = [
        dc_result.generation_mw[generator.index] for generator in data.generators
    ]
    for index in dc_result.outaged_branch_indices:
        case["branch"][index, BR_STATUS] = 0
    active_generator_indices, reference_bus = configure_rts24_ac_case(
        case,
        data,
        generator_commitment=generator_commitment,
        outaged_generator_indices=dc_result.outaged_generator_indices,
    )
    active_generator_set = set(active_generator_indices)
    inconsistent = [
        generator.index
        for generator in data.generators
        if generator.index not in active_generator_set
        and abs(dc_result.generation_mw[generator.index]) > power_tolerance_mw
    ]
    if inconsistent:
        raise ValueError(
            f"Inactive AC generators have nonzero DC targets: {inconsistent}"
        )

    try:
        ac_result, success = runpf(
            case,
            ppoption(VERBOSE=0, OUT_ALL=0),
        )
    except Exception as error:
        return _not_evaluated(
            f"ac_error:{type(error).__name__}",
            branch_rating,
            reference_bus=reference_bus,
            active_generator_indices=active_generator_indices,
            generator_commitment_applied=generator_commitment is not None,
        )
    if not success:
        failed = _not_evaluated(
            "not_converged",
            branch_rating,
            reference_bus=reference_bus,
            active_generator_indices=active_generator_indices,
            generator_commitment_applied=generator_commitment is not None,
        )
        return replace(failed, evaluated=True)

    bus = ac_result["bus"]
    generator = ac_result["gen"]
    branch = ac_result["branch"]
    active_generators = generator[:, GEN_STATUS] > 0
    active_branches = branch[:, BR_STATUS] > 0

    voltage_violation = np.maximum(bus[:, VM] - bus[:, VMAX], bus[:, VMIN] - bus[:, VM])
    max_voltage_violation = float(max(np.max(voltage_violation), 0.0))

    from_mva = np.hypot(branch[:, PF], branch[:, QF])
    to_mva = np.hypot(branch[:, PT], branch[:, QT])
    loading = np.zeros(len(branch))
    loading[active_branches] = np.maximum(
        from_mva[active_branches],
        to_mva[active_branches],
    ) / branch[active_branches, rating_column]
    max_loaded_branch_index = int(np.argmax(loading))
    max_loading = float(loading[max_loaded_branch_index])

    active_power_violation = np.maximum(
        generator[:, PG] - generator[:, PMAX],
        generator[:, PMIN] - generator[:, PG],
    )
    reactive_power_violation = np.maximum(
        generator[:, QG] - generator[:, QMAX],
        generator[:, QMIN] - generator[:, QG],
    )
    max_active_violation = float(
        max(np.max(active_power_violation[active_generators]), 0.0)
    )
    max_reactive_violation = float(
        max(np.max(reactive_power_violation[active_generators]), 0.0)
    )

    requested_generation = sum(
        dc_result.generation_mw[index] for index in active_generator_indices
    )
    ac_generation = float(np.sum(generator[active_generators, PG]))
    secure = (
        max_voltage_violation <= voltage_tolerance_pu
        and max_loading <= 1.0 + loading_tolerance
        and max_active_violation <= power_tolerance_mw
        and max_reactive_violation <= power_tolerance_mw
    )
    return AcValidationResult(
        evaluated=True,
        converged=True,
        secure=secure,
        status="secure" if secure else "constraint_violation",
        branch_rating=branch_rating,
        min_voltage_pu=float(np.min(bus[:, VM])),
        max_voltage_pu=float(np.max(bus[:, VM])),
        max_voltage_violation_pu=max_voltage_violation,
        max_branch_loading_fraction=max_loading,
        max_loaded_branch_index=max_loaded_branch_index,
        max_active_power_violation_mw=max_active_violation,
        max_reactive_power_violation_mvar=max_reactive_violation,
        reference_bus=reference_bus,
        active_generator_indices=active_generator_indices,
        generator_commitment_applied=generator_commitment is not None,
        requested_generation_mw=requested_generation,
        ac_generation_mw=ac_generation,
        slack_and_loss_adjustment_mw=ac_generation - requested_generation,
    )
