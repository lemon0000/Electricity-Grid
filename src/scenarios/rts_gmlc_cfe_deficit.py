"""Derive hourly data-center CFE calls from RTS-GMLC renewable scarcity."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import datetime
from itertools import pairwise
from math import fsum, isfinite
from pathlib import Path

from src.grid.rts_gmlc import RtsGmlcChronologicalData

RENEWABLE_UNIT_TYPES = frozenset({"WIND", "PV", "RTPV", "HYDRO", "ROR"})
CFE_DEFICIT_FORMULA = (
    "share_t=min(renewable_available_mw_t/system_load_mw_t,1);"
    "attributed_cfe_mw_t=share_t*dc_demand_mw;"
    "cfe_deficit_mw_t=max(alpha_hr*dc_demand_mw-attributed_cfe_mw_t,0);"
    "green_call_mw_t=cfe_deficit_mw_t/alpha_hr"
)
CFE_DEFICIT_PARAMETER_STATUS = (
    "rts_gmlc_renewable_availability_and_system_load_derived_cfe_scarcity_"
    "proportional_system_mix_attribution_not_procurement_or_delivery_evidence"
)
CFE_DEFICIT_COLUMNS = (
    "timestamp",
    "system_load_mw",
    "renewable_available_mw",
    "renewable_share",
    "dc_demand_mw",
    "hourly_cfe_target",
    "attributed_cfe_mw",
    "cfe_deficit_mw",
    "green_call_mw",
    "green_call_fraction",
)


@dataclass(frozen=True)
class RtsGmlcCfeDeficitPoint:
    timestamp: datetime
    system_load_mw: float
    renewable_available_mw: float
    renewable_share: float
    dc_demand_mw: float
    hourly_cfe_target: float
    attributed_cfe_mw: float
    cfe_deficit_mw: float
    green_call_mw: float


@dataclass(frozen=True)
class RtsGmlcCfeDeficitProfile:
    points: tuple[RtsGmlcCfeDeficitPoint, ...]
    source: str
    parameter_status: str = CFE_DEFICIT_PARAMETER_STATUS
    formula: str = CFE_DEFICIT_FORMULA

    @property
    def values(self) -> tuple[float, ...]:
        return tuple(point.green_call_mw for point in self.points)


@dataclass(frozen=True)
class CfeOperatingLimit:
    green_call_mw: float
    cfe_compatible_recovery_headroom_mw: float
    effective_recovery_headroom_mw: float


def _validate_scalar(name: str, value: float, *, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be numeric, not boolean")
    number = float(value)
    if not isfinite(number) or number < 0.0 or (positive and number <= 0.0):
        qualifier = "positive" if positive else "nonnegative"
        raise ValueError(f"{name} must be finite and {qualifier}")
    return number


def derive_cfe_operating_limit(
    point: RtsGmlcCfeDeficitPoint,
    *,
    hourly_cfe_target: float,
    business_recovery_headroom_mw: float,
) -> CfeOperatingLimit:
    """Convert an RTS-GMLC renewable share into call and recovery limits.

    Recovery is restricted to clean-energy headroom above the hourly target.
    This prevents deferred load from escaping the CFE accounting boundary.
    """

    target = _validate_scalar("hourly_cfe_target", hourly_cfe_target, positive=True)
    if target > 1.0:
        raise ValueError("hourly_cfe_target must not exceed 1")
    business_headroom = _validate_scalar(
        "business_recovery_headroom_mw",
        business_recovery_headroom_mw,
    )
    demand = _validate_scalar("dc_demand_mw", point.dc_demand_mw, positive=True)
    share = _validate_scalar("renewable_share", point.renewable_share)
    if share > 1.0:
        raise ValueError("renewable_share must not exceed 1")

    attributed_cfe = share * demand
    deficit = max(target * demand - attributed_cfe, 0.0)
    green_call = deficit / target
    cfe_headroom = max(attributed_cfe / target - demand, 0.0)
    return CfeOperatingLimit(
        green_call_mw=min(green_call, demand),
        cfe_compatible_recovery_headroom_mw=cfe_headroom,
        effective_recovery_headroom_mw=min(
            business_headroom,
            cfe_headroom,
        ),
    )


def derive_rts_gmlc_cfe_deficit(
    data: RtsGmlcChronologicalData,
    *,
    dc_demand_mw: float,
    hourly_cfe_target: float,
    renewable_unit_types: frozenset[str] = RENEWABLE_UNIT_TYPES,
    source: str,
) -> RtsGmlcCfeDeficitProfile:
    """Build an hourly load-shift request from the RTS-GMLC renewable share.

    The system renewable share is used as a transparent proportional
    attribution benchmark. ``green_call_mw`` is the load reduction required to
    close the resulting CFE deficit, not the CFE deficit itself.
    """

    demand = _validate_scalar("dc_demand_mw", dc_demand_mw, positive=True)
    target = _validate_scalar("hourly_cfe_target", hourly_cfe_target, positive=True)
    if target > 1.0:
        raise ValueError("hourly_cfe_target must not exceed 1")
    if not source:
        raise ValueError("source must be explicit")
    if not renewable_unit_types:
        raise ValueError("renewable_unit_types must be nonempty")

    renewable_uids = tuple(
        generator.uid
        for generator in data.generators
        if generator.enabled and generator.unit_type in renewable_unit_types
    )
    if not renewable_uids:
        raise ValueError("RTS-GMLC data has no enabled renewable generators")
    unknown_types = renewable_unit_types - {
        generator.unit_type for generator in data.generators
    }
    if unknown_types:
        raise ValueError(
            "renewable_unit_types are absent from RTS-GMLC data: "
            + ", ".join(sorted(unknown_types))
        )
    if len(data.hourly_points) < 2:
        raise ValueError("RTS-GMLC CFE profile requires at least two hours")

    points = []
    previous_timestamp = None
    for hour in data.hourly_points:
        if (
            previous_timestamp is not None
            and (hour.timestamp - previous_timestamp).total_seconds() != 3600
        ):
            raise ValueError("RTS-GMLC CFE source chronology is not hourly")
        previous_timestamp = hour.timestamp
        system_load = _validate_scalar(
            "system_load_mw", fsum(hour.demand_by_bus_mw.values()), positive=True
        )
        renewable_available = _validate_scalar(
            "renewable_available_mw",
            fsum(hour.generator_max_mw[uid] for uid in renewable_uids),
        )
        renewable_share = min(renewable_available / system_load, 1.0)
        attributed_cfe = renewable_share * demand
        deficit = max(target * demand - attributed_cfe, 0.0)
        green_call = deficit / target
        if green_call > demand + 1.0e-9:
            raise RuntimeError("derived green call exceeds data-center demand")
        points.append(
            RtsGmlcCfeDeficitPoint(
                timestamp=hour.timestamp,
                system_load_mw=system_load,
                renewable_available_mw=renewable_available,
                renewable_share=renewable_share,
                dc_demand_mw=demand,
                hourly_cfe_target=target,
                attributed_cfe_mw=attributed_cfe,
                cfe_deficit_mw=deficit,
                green_call_mw=min(green_call, demand),
            )
        )
    return RtsGmlcCfeDeficitProfile(points=tuple(points), source=source)


def load_rts_gmlc_cfe_deficit_profile(
    path: str | Path,
    *,
    expected_sha256: str,
    source: str | None = None,
) -> RtsGmlcCfeDeficitProfile:
    """Load a generated CFE profile after exact schema and hash validation."""

    path = Path(path)
    observed_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    if observed_sha256 != expected_sha256:
        raise ValueError("RTS-GMLC CFE deficit profile SHA-256 drifted")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != CFE_DEFICIT_COLUMNS:
            raise ValueError("RTS-GMLC CFE deficit CSV schema drifted")
        rows = list(reader)
    if len(rows) < 2:
        raise ValueError("RTS-GMLC CFE deficit profile requires at least two rows")

    points = []
    for row in rows:
        timestamp = datetime.fromisoformat(row["timestamp"])
        point = RtsGmlcCfeDeficitPoint(
            timestamp=timestamp,
            system_load_mw=float(row["system_load_mw"]),
            renewable_available_mw=float(row["renewable_available_mw"]),
            renewable_share=float(row["renewable_share"]),
            dc_demand_mw=float(row["dc_demand_mw"]),
            hourly_cfe_target=float(row["hourly_cfe_target"]),
            attributed_cfe_mw=float(row["attributed_cfe_mw"]),
            cfe_deficit_mw=float(row["cfe_deficit_mw"]),
            green_call_mw=float(row["green_call_mw"]),
        )
        green_call_fraction = float(row["green_call_fraction"])
        numeric_values = (
            point.system_load_mw,
            point.renewable_available_mw,
            point.renewable_share,
            point.dc_demand_mw,
            point.hourly_cfe_target,
            point.attributed_cfe_mw,
            point.cfe_deficit_mw,
            point.green_call_mw,
            green_call_fraction,
        )
        expected_deficit = max(
            point.hourly_cfe_target * point.dc_demand_mw - point.attributed_cfe_mw,
            0.0,
        )
        expected_share = min(point.renewable_available_mw / point.system_load_mw, 1.0)
        if (
            any(not isfinite(value) for value in numeric_values)
            or point.system_load_mw <= 0.0
            or not 0.0 < point.hourly_cfe_target <= 1.0
            or point.dc_demand_mw <= 0.0
            or point.renewable_available_mw < 0.0
            or not 0.0 <= point.renewable_share <= 1.0
            or abs(point.renewable_share - expected_share) > 1.0e-10
            or abs(point.attributed_cfe_mw - point.renewable_share * point.dc_demand_mw)
            > 1.0e-8
            or abs(point.cfe_deficit_mw - expected_deficit) > 1.0e-8
            or abs(point.green_call_mw - point.cfe_deficit_mw / point.hourly_cfe_target)
            > 1.0e-8
            or abs(green_call_fraction - point.green_call_mw / point.dc_demand_mw)
            > 1.0e-10
            or not 0.0 <= point.green_call_mw <= point.dc_demand_mw + 1.0e-9
        ):
            raise ValueError("RTS-GMLC CFE deficit row failed formula audit")
        points.append(point)
    if any(
        (later.timestamp - earlier.timestamp).total_seconds() != 3600
        for earlier, later in pairwise(points)
    ):
        raise ValueError("RTS-GMLC CFE deficit profile is not continuous hourly")
    reference_demand = points[0].dc_demand_mw
    reference_target = points[0].hourly_cfe_target
    if any(
        point.dc_demand_mw != reference_demand
        or point.hourly_cfe_target != reference_target
        for point in points[1:]
    ):
        raise ValueError("RTS-GMLC CFE deficit demand and target must be constant")
    return RtsGmlcCfeDeficitProfile(
        points=tuple(points),
        source=source or f"{path}::sha256={observed_sha256}",
    )
