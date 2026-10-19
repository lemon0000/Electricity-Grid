"""Load the IEEE RTS-24 case distributed with PYPOWER."""

from __future__ import annotations

from dataclasses import dataclass, replace
from importlib.metadata import version
from math import isfinite, radians

from pypower.api import case24_ieee_rts
from pypower.idx_brch import (
    BR_STATUS,
    BR_X,
    F_BUS,
    RATE_A,
    RATE_B,
    RATE_C,
    SHIFT,
    TAP,
    T_BUS,
)
from pypower.idx_bus import BUS_I, BUS_TYPE, GS, PD, REF
from pypower.idx_cost import COST, MODEL, NCOST, POLYNOMIAL
from pypower.idx_gen import (
    GEN_BUS,
    GEN_STATUS,
    PMAX,
    PMIN,
    RAMP_10,
    RAMP_30,
)


@dataclass(frozen=True)
class Bus:
    index: int
    demand_mw: float


@dataclass(frozen=True)
class Generator:
    index: int
    bus: int
    p_min_mw: float
    p_max_mw: float
    cost_quadratic: float
    cost_linear: float
    cost_constant: float
    ramp_10_mw: float | None
    ramp_30_mw: float | None
    in_service: bool


@dataclass(frozen=True)
class Branch:
    index: int
    from_bus: int
    to_bus: int
    reactance_pu: float
    rate_a_mw: float
    rate_b_mw: float
    rate_c_mw: float
    tap_ratio: float
    phase_shift_rad: float
    in_service: bool

    @property
    def label(self) -> str:
        return f"{self.from_bus}-{self.to_bus}#{self.index}"

    def rating_mw(self, rating: str) -> float:
        try:
            return {
                "rate_a": self.rate_a_mw,
                "rate_b": self.rate_b_mw,
                "rate_c": self.rate_c_mw,
            }[rating]
        except KeyError as error:
            raise ValueError(f"Unknown branch rating '{rating}'") from error


@dataclass(frozen=True)
class Rts24Data:
    base_mva: float
    buses: tuple[Bus, ...]
    generators: tuple[Generator, ...]
    branches: tuple[Branch, ...]
    reference_bus: int
    source_package: str
    source_version: str

    @property
    def total_demand_mw(self) -> float:
        return sum(bus.demand_mw for bus in self.buses)


def _quadratic_cost(row: object) -> tuple[float, float, float]:
    if int(row[MODEL]) != POLYNOMIAL:
        raise ValueError("RTS-24 loader requires polynomial generator costs")

    coefficient_count = int(row[NCOST])
    coefficients = [float(value) for value in row[COST : COST + coefficient_count]]
    if coefficient_count > 3:
        raise ValueError("DC-OPF implementation supports costs up to degree two")

    padded = [0.0] * (3 - coefficient_count) + coefficients
    return padded[0], padded[1], padded[2]


def load_rts24() -> Rts24Data:
    """Return a typed, immutable view of PYPOWER's IEEE RTS-24 case."""

    case = case24_ieee_rts()
    bus_rows = case["bus"]
    generator_rows = case["gen"]
    cost_rows = case["gencost"]
    branch_rows = case["branch"]

    if len(generator_rows) != len(cost_rows):
        raise ValueError("Each generator must have exactly one cost row")

    buses = tuple(
        Bus(
            index=int(row[BUS_I]),
            demand_mw=float(row[PD] + row[GS]),
        )
        for row in bus_rows
    )
    reference_buses = [int(row[BUS_I]) for row in bus_rows if int(row[BUS_TYPE]) == REF]
    if len(reference_buses) != 1:
        raise ValueError("RTS-24 must contain exactly one reference bus")

    generators = []
    for index, (generator_row, cost_row) in enumerate(zip(generator_rows, cost_rows)):
        quadratic, linear, constant = _quadratic_cost(cost_row)
        generators.append(
            Generator(
                index=index,
                bus=int(generator_row[GEN_BUS]),
                p_min_mw=float(generator_row[PMIN]),
                p_max_mw=float(generator_row[PMAX]),
                cost_quadratic=quadratic,
                cost_linear=linear,
                cost_constant=constant,
                # PYPOWER uses zero when this RTS case does not specify ramps.
                ramp_10_mw=(
                    float(generator_row[RAMP_10])
                    if generator_row[RAMP_10] > 0
                    else None
                ),
                ramp_30_mw=(
                    float(generator_row[RAMP_30])
                    if generator_row[RAMP_30] > 0
                    else None
                ),
                in_service=bool(generator_row[GEN_STATUS] > 0),
            )
        )

    branches = []
    for index, row in enumerate(branch_rows):
        reactance = float(row[BR_X])
        ratings = {
            "rate_a": float(row[RATE_A]),
            "rate_b": float(row[RATE_B]),
            "rate_c": float(row[RATE_C]),
        }
        if reactance == 0.0:
            raise ValueError(f"Branch {index} has zero reactance")
        for name, rating in ratings.items():
            if rating <= 0.0:
                raise ValueError(f"Branch {index} requires a positive {name.upper()}")

        raw_tap = float(row[TAP])
        branches.append(
            Branch(
                index=index,
                from_bus=int(row[F_BUS]),
                to_bus=int(row[T_BUS]),
                reactance_pu=reactance,
                rate_a_mw=ratings["rate_a"],
                rate_b_mw=ratings["rate_b"],
                rate_c_mw=ratings["rate_c"],
                tap_ratio=raw_tap if raw_tap != 0.0 else 1.0,
                phase_shift_rad=radians(float(row[SHIFT])),
                in_service=bool(row[BR_STATUS] > 0),
            )
        )

    return Rts24Data(
        base_mva=float(case["baseMVA"]),
        buses=buses,
        generators=tuple(generators),
        branches=tuple(branches),
        reference_bus=reference_buses[0],
        source_package="pypower",
        source_version=version("pypower"),
    )


def scale_rts24_demand(data: Rts24Data, multiplier: float) -> Rts24Data:
    """Return a copy with every bus demand scaled by one nonnegative factor."""

    if not isfinite(multiplier) or multiplier < 0.0:
        raise ValueError("Demand multiplier must be finite and nonnegative")
    return replace(
        data,
        buses=tuple(
            replace(bus, demand_mw=bus.demand_mw * multiplier)
            for bus in data.buses
        ),
    )
