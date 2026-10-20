"""Shared mapping from typed RTS-24 data to a PYPOWER AC case."""

from __future__ import annotations

from typing import Iterable, Mapping

from pypower.idx_bus import BUS_I, BUS_TYPE, GS, NONE, PD, PQ, PV, QD, REF
from pypower.idx_gen import (
    GEN_BUS,
    GEN_STATUS,
    PG,
    PMAX,
    PMIN,
    QG,
    QMAX,
    QMIN,
)

from .rts24 import Rts24Data


def configure_rts24_ac_case(
    case: dict[str, object],
    data: Rts24Data,
    *,
    generator_commitment: Mapping[int, bool] | None = None,
    outaged_generator_indices: Iterable[int] = (),
    tolerance: float = 1.0e-9,
) -> tuple[tuple[int, ...], int]:
    """Map snapshot load and real-power commitment into a PYPOWER case."""

    generator_indices = {generator.index for generator in data.generators}
    commitment = None
    if generator_commitment is not None:
        if set(generator_commitment) != generator_indices:
            raise ValueError("Generator commitment must contain every generator index")
        if any(type(status) is not bool for status in generator_commitment.values()):
            raise ValueError("Generator commitment values must be bool")
        commitment = dict(generator_commitment)
        invalid = [
            generator.index
            for generator in data.generators
            if commitment[generator.index]
            and (not generator.in_service or generator.p_max_mw <= 0.0)
        ]
        if invalid:
            raise ValueError(
                f"Real-power commitment includes unavailable generators: {invalid}"
            )

    outages = frozenset(int(index) for index in outaged_generator_indices)
    unknown_outages = outages - generator_indices
    if unknown_outages:
        raise ValueError(f"Unknown generator outages: {sorted(unknown_outages)}")
    if len(case["gen"]) != len(data.generators) or any(
        int(case["gen"][generator.index, GEN_BUS]) != generator.bus
        for generator in data.generators
    ):
        raise ValueError("Typed generator data do not align with the PYPOWER AC case")

    bus_rows = {
        int(row[BUS_I]): position for position, row in enumerate(case["bus"])
    }
    if set(bus_rows) != {bus.index for bus in data.buses}:
        raise ValueError("Typed bus data do not align with the PYPOWER AC case")
    for bus in data.buses:
        row = case["bus"][bus_rows[bus.index]]
        source_demand_mw = float(row[PD] + row[GS])
        if abs(source_demand_mw) <= tolerance:
            if abs(bus.demand_mw) > tolerance:
                raise ValueError(
                    f"Cannot infer reactive demand for newly loaded bus {bus.index}"
                )
            row[PD] = 0.0
            row[GS] = 0.0
            continue
        multiplier = bus.demand_mw / source_demand_mw
        row[PD] *= multiplier
        row[QD] *= multiplier
        row[GS] *= multiplier

    active_indices = []
    active_real_power_indices = []
    for generator in data.generators:
        # Pmax=0 units are reactive-only devices and are not controlled by the
        # real-power commitment mapping.
        selected = (
            generator.p_max_mw <= 0.0
            or commitment is None
            or commitment[generator.index]
        )
        active = (
            generator.in_service
            and selected
            and generator.index not in outages
        )
        case["gen"][generator.index, GEN_STATUS] = int(active)
        if not active:
            case["gen"][generator.index, PG] = 0.0
            case["gen"][generator.index, QG] = 0.0
            continue
        active_indices.append(generator.index)
        if generator.p_max_mw > 0.0:
            active_real_power_indices.append(generator.index)

    if not active_real_power_indices:
        raise ValueError("AC case requires at least one active real-power generator")

    active_buses = {
        int(case["gen"][index, GEN_BUS]) for index in active_indices
    }
    for row in case["bus"]:
        bus = int(row[BUS_I])
        if int(row[BUS_TYPE]) == NONE:
            continue
        row[BUS_TYPE] = PV if bus in active_buses else PQ

    candidate_buses = {
        int(case["gen"][index, GEN_BUS]) for index in active_real_power_indices
    }

    def reference_key(bus: int) -> tuple[float, float, float, int]:
        indices = [
            index
            for index in active_real_power_indices
            if int(case["gen"][index, GEN_BUS]) == bus
        ]
        # PYPOWER assigns the active-power slack to the first online generator
        # at the REF bus, rather than sharing it across colocated units.
        slack_index = indices[0]
        up_headroom = (
            case["gen"][slack_index, PMAX] - case["gen"][slack_index, PG]
        )
        down_headroom = (
            case["gen"][slack_index, PG] - case["gen"][slack_index, PMIN]
        )
        reactive_headroom = sum(
            case["gen"][index, QMAX] - case["gen"][index, QMIN]
            for index in indices
        )
        return -up_headroom, -down_headroom, -reactive_headroom, bus

    reference_bus = min(candidate_buses, key=reference_key)
    case["bus"][bus_rows[reference_bus], BUS_TYPE] = REF
    return tuple(active_indices), reference_bus
