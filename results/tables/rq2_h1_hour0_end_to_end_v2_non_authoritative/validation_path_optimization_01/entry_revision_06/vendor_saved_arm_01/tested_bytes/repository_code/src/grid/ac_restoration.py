"""Minimum-dispatch-deviation AC feasibility restoration."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Iterable, Mapping

import numpy as np
from pypower.api import case24_ieee_rts, ppoption, runopf
from pypower.idx_brch import (
    BR_STATUS,
    F_BUS,
    PF,
    PT,
    QF,
    QT,
    RATE_A,
    RATE_B,
    RATE_C,
    T_BUS,
)
from pypower.idx_bus import BS, BUS_I, BUS_TYPE, NONE, PD, QD, VA, VM, VMAX, VMIN
from pypower.idx_cost import COST, MODEL, NCOST, POLYNOMIAL, SHUTDOWN, STARTUP
from pypower.idx_gen import GEN_BUS, GEN_STATUS, PG, PMAX, PMIN, QG, QMAX, QMIN

from .ac_case import configure_rts24_ac_case
from .dc_opf import DcOpfResult
from .rts24 import Rts24Data


@dataclass(frozen=True)
class AcRestorationResult:
    evaluated: bool
    converged: bool
    secure: bool
    status: str
    branch_rating: str
    generation_mw: dict[int, float]
    reactive_generation_mvar: dict[int, float]
    bus_voltage_pu: dict[int, float]
    max_voltage_violation_pu: float | None
    max_branch_loading_fraction: float | None
    max_loaded_branch_index: int | None
    max_active_power_violation_mw: float | None
    max_reactive_power_violation_mvar: float | None
    reference_bus: int | None
    active_generator_indices: tuple[int, ...]
    generator_commitment_applied: bool
    squared_target_deviation_mw2: float | None
    max_target_deviation_mw: float | None
    max_reference_redispatch_mw: float | None
    total_up_redispatch_mw: float | None
    total_down_redispatch_mw: float | None
    ac_generation_mw: float | None
    ac_losses_mw: float | None
    corrective_open_branch_indices: tuple[int, ...]
    shunt_injections_mvar: dict[int, float]
    branch_rating_overrides_mva: dict[int, float]
    minimum_deviation_solved: bool
    fallback_seed_used: bool


def _not_evaluated(
    status: str,
    branch_rating: str,
    *,
    reference_bus: int | None = None,
    active_generator_indices: tuple[int, ...] = (),
    generator_commitment_applied: bool = False,
) -> AcRestorationResult:
    return AcRestorationResult(
        evaluated=False,
        converged=False,
        secure=False,
        status=status,
        branch_rating=branch_rating,
        generation_mw={},
        reactive_generation_mvar={},
        bus_voltage_pu={},
        max_voltage_violation_pu=None,
        max_branch_loading_fraction=None,
        max_loaded_branch_index=None,
        max_active_power_violation_mw=None,
        max_reactive_power_violation_mvar=None,
        reference_bus=reference_bus,
        active_generator_indices=active_generator_indices,
        generator_commitment_applied=generator_commitment_applied,
        squared_target_deviation_mw2=None,
        max_target_deviation_mw=None,
        max_reference_redispatch_mw=None,
        total_up_redispatch_mw=None,
        total_down_redispatch_mw=None,
        ac_generation_mw=None,
        ac_losses_mw=None,
        corrective_open_branch_indices=(),
        shunt_injections_mvar={},
        branch_rating_overrides_mva={},
        minimum_deviation_solved=False,
        fallback_seed_used=False,
    )


def restore_ac_feasibility(
    data: Rts24Data,
    dc_result: DcOpfResult,
    *,
    generator_commitment: Mapping[int, bool] | None = None,
    target_generation_mw: Mapping[int, float] | None = None,
    reference_generation_mw: Mapping[int, float] | None = None,
    redispatch_up_mw: Mapping[int, float] | None = None,
    redispatch_down_mw: Mapping[int, float] | None = None,
    branch_rating: str | None = None,
    corrective_open_branch_indices: Iterable[int] = (),
    shunt_injections_mvar: Mapping[int, float] | None = None,
    branch_rating_overrides_mva: Mapping[int, float] | None = None,
    tolerance: float = 1.0e-5,
) -> AcRestorationResult:
    """Find the closest AC-feasible dispatch to a DC state.

    Optional redispatch bounds are enforced around an AC reference dispatch.
    The quadratic objective is only a feasibility-restoration distance metric.
    """

    rating = branch_rating or dc_result.branch_rating
    if not dc_result.feasible:
        return _not_evaluated("dc_infeasible", rating)
    if len(dc_result.reference_buses) != 1:
        return _not_evaluated("islanding", rating)

    generator_indices = {generator.index for generator in data.generators}
    target = dict(target_generation_mw or dc_result.generation_mw)
    if set(target) != generator_indices:
        raise ValueError("Target dispatch must contain every generator index")
    if reference_generation_mw is None:
        if redispatch_up_mw is not None or redispatch_down_mw is not None:
            raise ValueError("Redispatch limits require an AC reference dispatch")
    else:
        if redispatch_up_mw is None or redispatch_down_mw is None:
            raise ValueError("An AC reference requires up and down limits")
        for name, values in (
            ("reference dispatch", reference_generation_mw),
            ("up redispatch", redispatch_up_mw),
            ("down redispatch", redispatch_down_mw),
        ):
            if set(values) != generator_indices:
                raise ValueError(f"{name} must contain every generator index")
        if any(value < 0.0 for value in redispatch_up_mw.values()) or any(
            value < 0.0 for value in redispatch_down_mw.values()
        ):
            raise ValueError("Redispatch limits must be nonnegative")

    rating_column = {
        "rate_a": RATE_A,
        "rate_b": RATE_B,
        "rate_c": RATE_C,
    }.get(rating)
    if rating_column is None:
        raise ValueError(f"Unknown branch rating '{rating}'")

    case = case24_ieee_rts()
    default_initial_pg = case["gen"][:, PG].copy()
    case["branch"][:, RATE_A] = case["branch"][:, rating_column]
    corrective_open = tuple(int(index) for index in corrective_open_branch_indices)
    unknown_open = set(corrective_open) - set(range(len(data.branches)))
    if unknown_open:
        raise ValueError(f"Unknown corrective-open branches: {sorted(unknown_open)}")
    shunt_injections = {
        int(bus): float(value) for bus, value in (shunt_injections_mvar or {}).items()
    }
    rating_overrides = {
        int(index): float(value)
        for index, value in (branch_rating_overrides_mva or {}).items()
    }
    bus_rows = {int(row[BUS_I]): position for position, row in enumerate(case["bus"])}
    if set(shunt_injections) - bus_rows.keys():
        raise ValueError("Shunt injection references an unknown bus")
    if set(rating_overrides) - set(range(len(data.branches))):
        raise ValueError("Rating override references an unknown branch")
    if any(value <= 0.0 for value in rating_overrides.values()):
        raise ValueError("Branch rating overrides must be positive")

    for index in dc_result.outaged_branch_indices | frozenset(corrective_open):
        case["branch"][index, BR_STATUS] = 0
    for index, value in rating_overrides.items():
        case["branch"][index, RATE_A] = value
    for bus, value in shunt_injections.items():
        case["bus"][bus_rows[bus], BS] += value
    case["gen"][:, PG] = [target[generator.index] for generator in data.generators]
    active_generator_indices, reference_bus = configure_rts24_ac_case(
        case,
        data,
        generator_commitment=generator_commitment,
        outaged_generator_indices=dc_result.outaged_generator_indices,
        tolerance=tolerance,
    )
    active_generator_set = set(active_generator_indices)
    inconsistent = [
        generator.index
        for generator in data.generators
        if generator.index not in active_generator_set
        and abs(target[generator.index]) > tolerance
    ]
    if inconsistent:
        raise ValueError(
            f"Inactive AC generators have nonzero targets: {inconsistent}"
        )

    for bus, position in bus_rows.items():
        connected = any(
            branch[BR_STATUS] > 0
            and (int(branch[F_BUS]) == bus or int(branch[T_BUS]) == bus)
            for branch in case["branch"]
        )
        has_generator = any(
            generator[GEN_STATUS] > 0 and int(generator[GEN_BUS]) == bus
            for generator in case["gen"]
        )
        zero_injection = (
            abs(case["bus"][position, PD]) <= tolerance
            and abs(case["bus"][position, QD]) <= tolerance
        )
        if not connected and not has_generator and zero_injection:
            case["bus"][position, BUS_TYPE] = NONE

    for generator in data.generators:
        index = generator.index
        if index not in active_generator_set:
            continue
        lower = generator.p_min_mw
        upper = generator.p_max_mw
        if reference_generation_mw is not None:
            lower = max(
                lower,
                reference_generation_mw[index] - redispatch_down_mw[index],
            )
            upper = min(
                upper,
                reference_generation_mw[index] + redispatch_up_mw[index],
            )
        if lower > upper + tolerance:
            raise ValueError(f"AC redispatch bounds are inconsistent for generator {index}")
        case["gen"][index, PMIN] = lower
        case["gen"][index, PMAX] = upper
        case["gen"][index, PG] = min(max(target[index], lower), upper)

    original_gencost = case["gencost"].copy()
    gencost = np.zeros((len(data.generators), 7))
    for generator in data.generators:
        index = generator.index
        target_mw = target[index]
        gencost[index, MODEL] = POLYNOMIAL
        gencost[index, STARTUP] = 0.0
        gencost[index, SHUTDOWN] = 0.0
        gencost[index, NCOST] = 3
        gencost[index, COST : COST + 3] = (1.0, -2.0 * target_mw, target_mw**2)
    case["gencost"] = gencost

    fallback_seed_used = False
    minimum_deviation_solved = False
    try:
        seed_case = deepcopy(case)
        seed_case["gencost"] = original_gencost
        seed_case["gen"][:, PG] = default_initial_pg
        if reference_generation_mw is not None:
            seed_case["gen"][:, PG] = np.minimum(
                np.maximum(default_initial_pg, seed_case["gen"][:, PMIN]),
                seed_case["gen"][:, PMAX],
            )
        seed_case["gen"][seed_case["gen"][:, GEN_STATUS] <= 0, PG] = 0.0
        seed = runopf(seed_case, ppoption(VERBOSE=0, OUT_ALL=0))
        if seed["success"]:
            fallback_seed_used = True
            warm_case = deepcopy(case)
            warm_case["bus"][:, (VM, VA)] = seed["bus"][:, (VM, VA)]
            warm_case["gen"][:, (PG, QG)] = seed["gen"][:, (PG, QG)]
            warm_result = runopf(
                warm_case,
                ppoption(VERBOSE=0, OUT_ALL=0),
            )
            if warm_result["success"]:
                result = warm_result
                minimum_deviation_solved = True
            else:
                result = seed
        else:
            result = runopf(deepcopy(case), ppoption(VERBOSE=0, OUT_ALL=0))
            if result["success"]:
                minimum_deviation_solved = True
    except Exception as error:
        return replace(
            _not_evaluated(
                f"ac_error:{type(error).__name__}",
                rating,
                reference_bus=reference_bus,
                active_generator_indices=active_generator_indices,
                generator_commitment_applied=generator_commitment is not None,
            ),
            corrective_open_branch_indices=corrective_open,
            shunt_injections_mvar=shunt_injections,
            branch_rating_overrides_mva=rating_overrides,
        )
    if not result["success"]:
        failed = _not_evaluated(
            "not_converged_or_infeasible",
            rating,
            reference_bus=reference_bus,
            active_generator_indices=active_generator_indices,
            generator_commitment_applied=generator_commitment is not None,
        )
        return replace(
            failed,
            evaluated=True,
            corrective_open_branch_indices=corrective_open,
            shunt_injections_mvar=shunt_injections,
            branch_rating_overrides_mva=rating_overrides,
        )

    bus = result["bus"]
    generator = result["gen"]
    branch = result["branch"]
    active_generators = generator[:, GEN_STATUS] > 0
    active_branches = branch[:, BR_STATUS] > 0
    voltage_violation = np.maximum(bus[:, VM] - bus[:, VMAX], bus[:, VMIN] - bus[:, VM])
    max_voltage_violation = float(max(np.max(voltage_violation), 0.0))

    branch_loading = np.zeros(len(branch))
    branch_loading[active_branches] = np.maximum(
        np.hypot(branch[active_branches, PF], branch[active_branches, QF]),
        np.hypot(branch[active_branches, PT], branch[active_branches, QT]),
    ) / branch[active_branches, RATE_A]
    max_loaded_branch_index = int(np.argmax(branch_loading))
    max_loading = float(branch_loading[max_loaded_branch_index])

    active_violation = np.maximum(
        generator[:, PG] - generator[:, PMAX],
        generator[:, PMIN] - generator[:, PG],
    )
    reactive_violation = np.maximum(
        generator[:, QG] - generator[:, QMAX],
        generator[:, QMIN] - generator[:, QG],
    )
    max_active_violation = float(max(np.max(active_violation[active_generators]), 0.0))
    max_reactive_violation = float(
        max(np.max(reactive_violation[active_generators]), 0.0)
    )

    generation_mw = {
        item.index: float(generator[item.index, PG])
        if generator[item.index, GEN_STATUS] > 0
        else 0.0
        for item in data.generators
    }
    reactive_generation = {
        item.index: float(generator[item.index, QG])
        if generator[item.index, GEN_STATUS] > 0
        else 0.0
        for item in data.generators
    }
    voltages = {
        item.index: float(bus[position, VM])
        for position, item in enumerate(data.buses)
    }
    target_deviations = {
        index: generation_mw[index] - target[index] for index in generator_indices
    }
    if reference_generation_mw is None:
        reference_deviations = target_deviations
    else:
        reference_deviations = {
            index: generation_mw[index] - reference_generation_mw[index]
            for index in active_generator_indices
        }
    ac_generation = sum(generation_mw.values())
    secure = (
        max_voltage_violation <= tolerance
        and max_loading <= 1.0 + tolerance
        and max_active_violation <= tolerance
        and max_reactive_violation <= tolerance
    )
    return AcRestorationResult(
        evaluated=True,
        converged=True,
        secure=secure,
        status=(
            "secure"
            if secure and minimum_deviation_solved
            else "secure_economic_seed_only"
            if secure
            else "constraint_violation"
        ),
        branch_rating=rating,
        generation_mw=generation_mw,
        reactive_generation_mvar=reactive_generation,
        bus_voltage_pu=voltages,
        max_voltage_violation_pu=max_voltage_violation,
        max_branch_loading_fraction=max_loading,
        max_loaded_branch_index=max_loaded_branch_index,
        max_active_power_violation_mw=max_active_violation,
        max_reactive_power_violation_mvar=max_reactive_violation,
        reference_bus=reference_bus,
        active_generator_indices=active_generator_indices,
        generator_commitment_applied=generator_commitment is not None,
        squared_target_deviation_mw2=sum(
            deviation**2 for deviation in target_deviations.values()
        ),
        max_target_deviation_mw=max(
            abs(deviation) for deviation in target_deviations.values()
        ),
        max_reference_redispatch_mw=max(
            abs(deviation) for deviation in reference_deviations.values()
        ),
        total_up_redispatch_mw=sum(
            max(deviation, 0.0) for deviation in reference_deviations.values()
        ),
        total_down_redispatch_mw=sum(
            max(-deviation, 0.0) for deviation in reference_deviations.values()
        ),
        ac_generation_mw=ac_generation,
        ac_losses_mw=ac_generation - data.total_demand_mw,
        corrective_open_branch_indices=corrective_open,
        shunt_injections_mvar=shunt_injections,
        branch_rating_overrides_mva=rating_overrides,
        minimum_deviation_solved=minimum_deviation_solved,
        fallback_seed_used=fallback_seed_used,
    )
