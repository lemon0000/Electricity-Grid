"""Validation and minimal parsing for the pinned RTS-GMLC source data."""

from __future__ import annotations

import csv
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from math import fsum, isclose, isfinite
from pathlib import Path
from typing import Literal

RTS_GMLC_REPOSITORY = "https://github.com/GridMod/RTS-GMLC"
RTS_GMLC_RELEASE = "v0.2.3"
RTS_GMLC_COMMIT = "3ece0d3725c844056132393ee252b3083dd4eab4"
RTS_GMLC_MANIFEST_SHA256 = (
    "95c1294626cdf00ee029659108bf1f30d4ec176a258192b784f097462226a914"
)
_RTS_GMLC_BASE_MVA = 100.0
_RTS_GMLC_DAY_AHEAD_HOURS = 8784
_TIME_COLUMNS = frozenset({"Year", "Month", "Day", "Period"})


DispatchMode = Literal["committable", "fixed", "curtailable", "disabled"]


@dataclass(frozen=True)
class RtsGmlcGenerator:
    uid: str
    bus: int
    unit_type: str
    p_max_mw: float
    p_min_mw: float
    ramp_mw_per_minute: float


@dataclass(frozen=True)
class HourlyLoadPoint:
    timestamp: datetime
    region_mw: dict[int, float]


@dataclass(frozen=True)
class RtsGmlcBus:
    uid: int
    name: str
    base_kv: float
    bus_type: str
    area: int
    static_load_mw: float


@dataclass(frozen=True)
class RtsGmlcBranch:
    uid: str
    from_bus: int
    to_bus: int
    resistance_pu: float
    reactance_pu: float
    charging_susceptance_pu: float
    continuous_rating_mw: float
    long_term_rating_mw: float
    short_term_rating_mw: float
    tap_ratio: float


@dataclass(frozen=True)
class RtsGmlcDcBranch:
    uid: str
    from_bus: int
    to_bus: int
    control_mode: str
    resistance_ohm: float
    p_min_mw: float
    p_max_mw: float


@dataclass(frozen=True)
class RtsGmlcChronologicalGenerator:
    uid: str
    bus: int
    unit_type: str
    category: str
    fuel: str
    dispatch_mode: DispatchMode
    enabled: bool
    disabled_reason: str | None
    p_min_mw: float
    p_max_mw: float
    minimum_down_time_hours: float
    minimum_up_time_hours: float
    ramp_mw_per_minute: float
    ramp_mw_per_hour: float
    start_time_cold_hours: float
    start_time_warm_hours: float
    start_time_hot_hours: float
    start_heat_cold_mmbtu: float
    start_heat_warm_mmbtu: float
    start_heat_hot_mmbtu: float
    non_fuel_start_cost_usd: float
    shutdown_cost_usd: float
    fuel_price_usd_per_mmbtu: float
    variable_om_usd_per_mwh: float
    cold_start_cost_usd: float
    warm_start_cost_usd: float
    hot_start_cost_usd: float
    cost_breakpoints_mw: tuple[float, ...]
    cost_values_usd_per_hour: tuple[float, ...]


@dataclass(frozen=True)
class RtsGmlcHourlyPoint:
    timestamp: datetime
    demand_by_bus_mw: dict[int, float]
    generator_min_mw: dict[str, float]
    generator_max_mw: dict[str, float]
    spin_up_requirement_by_area_mw: dict[int, float]


@dataclass(frozen=True)
class RtsGmlcChronologicalData:
    base_mva: float
    reference_bus: int
    buses: tuple[RtsGmlcBus, ...]
    branches: tuple[RtsGmlcBranch, ...]
    dc_branches: tuple[RtsGmlcDcBranch, ...]
    generators: tuple[RtsGmlcChronologicalGenerator, ...]
    hourly_points: tuple[RtsGmlcHourlyPoint, ...]


@dataclass(frozen=True)
class RtsGmlcSummary:
    source_repository: str
    source_release: str
    source_commit: str
    source_manifest_sha256: str
    sha256_manifest_valid: bool
    buses: int
    generators: int
    ac_branches: int
    static_load_mw: float
    generators_with_positive_ramp: int
    ramp_min_mw_per_minute: float
    ramp_max_mw_per_minute: float
    day_ahead_hours: int
    first_timestamp: datetime
    last_timestamp: datetime
    day_ahead_rows: dict[str, int]
    day_ahead_series_timestamp_continuous: dict[str, bool]
    day_ahead_series_common_calendar: bool
    day_ahead_core_pointer_columns_complete: bool


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def _timestamps(rows: list[dict[str, str]]) -> tuple[datetime, ...]:
    return tuple(
        datetime(
            int(row["Year"]),
            int(row["Month"]),
            int(row["Day"]),
            int(row["Period"]) - 1,
        )
        for row in rows
    )


def _is_continuous_hourly(timestamps: tuple[datetime, ...]) -> bool:
    return bool(timestamps) and all(
        (later - earlier).total_seconds() == 3600
        for earlier, later in zip(timestamps, timestamps[1:])
    )


def validate_rts_gmlc_source_identity(source: Mapping[str, object]) -> None:
    """Reject any repository, release, or commit outside the pinned identity."""

    if not isinstance(source, Mapping):
        raise ValueError("RTS-GMLC source identity must be a mapping")
    expected = {
        "repository": RTS_GMLC_REPOSITORY,
        "release": RTS_GMLC_RELEASE,
        "commit": RTS_GMLC_COMMIT,
    }
    mismatched = [key for key, value in expected.items() if source.get(key) != value]
    if mismatched:
        raise ValueError("RTS-GMLC source identity drifted: " + ", ".join(mismatched))


def verify_sha256_manifest(upstream_root: Path) -> bool:
    manifest = upstream_root / "SHA256SUMS"
    if not manifest.exists():
        return False
    for line in manifest.read_text(encoding="ascii").splitlines():
        expected, relative_path = line.split("  ", maxsplit=1)
        path = upstream_root / Path(relative_path)
        if not path.exists():
            return False
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            return False
    return True


def load_rts_gmlc_generators(upstream_root: Path) -> tuple[RtsGmlcGenerator, ...]:
    path = upstream_root / "RTS_Data" / "SourceData" / "gen.csv"
    generators = []
    for row in _read_csv(path):
        generators.append(
            RtsGmlcGenerator(
                uid=row["GEN UID"],
                bus=int(row["Bus ID"]),
                unit_type=row["Unit Type"],
                p_max_mw=float(row["PMax MW"]),
                p_min_mw=float(row["PMin MW"]),
                ramp_mw_per_minute=float(row["Ramp Rate MW/Min"]),
            )
        )
    return tuple(generators)


def load_day_ahead_regional_load(
    upstream_root: Path,
) -> tuple[HourlyLoadPoint, ...]:
    path = (
        upstream_root
        / "RTS_Data"
        / "timeseries_data_files"
        / "Load"
        / "DAY_AHEAD_regional_Load.csv"
    )
    rows = _read_csv(path)
    timestamps = _timestamps(rows)
    points = []
    for row, timestamp in zip(rows, timestamps):
        points.append(
            HourlyLoadPoint(
                timestamp=timestamp,
                region_mw={region: float(row[str(region)]) for region in (1, 2, 3)},
            )
        )
    if not _is_continuous_hourly(timestamps):
        raise ValueError("RTS-GMLC day-ahead load is not a continuous hourly series")
    return tuple(points)


def load_rts24_area1_load_multipliers(
    upstream_root: Path,
    *,
    static_peak_mw: float = 2850.0,
) -> tuple[tuple[datetime, float], ...]:
    """Return the same-lineage Area 1 load series as an RTS-24 load proxy."""

    if static_peak_mw <= 0.0:
        raise ValueError("Static peak load must be positive")
    return tuple(
        (point.timestamp, point.region_mw[1] / static_peak_mw)
        for point in load_day_ahead_regional_load(upstream_root)
    )


def summarize_rts_gmlc(upstream_root: Path) -> RtsGmlcSummary:
    source_data = upstream_root / "RTS_Data" / "SourceData"
    timeseries = upstream_root / "RTS_Data" / "timeseries_data_files"
    buses = _read_csv(source_data / "bus.csv")
    branches = _read_csv(source_data / "branch.csv")
    generators = load_rts_gmlc_generators(upstream_root)
    load_points = load_day_ahead_regional_load(upstream_root)
    series_paths = {
        "load": timeseries / "Load" / "DAY_AHEAD_regional_Load.csv",
        "wind": timeseries / "WIND" / "DAY_AHEAD_wind.csv",
        "pv": timeseries / "PV" / "DAY_AHEAD_pv.csv",
        "rtpv": timeseries / "RTPV" / "DAY_AHEAD_rtpv.csv",
        "hydro": timeseries / "Hydro" / "DAY_AHEAD_hydro.csv",
    }
    series_data = {name: _read_csv(path) for name, path in series_paths.items()}
    series_rows = {name: len(rows) for name, rows in series_data.items()}
    series_timestamps = {name: _timestamps(rows) for name, rows in series_data.items()}
    series_continuity = {
        name: _is_continuous_hourly(timestamps)
        for name, timestamps in series_timestamps.items()
    }
    first_calendar = next(iter(series_timestamps.values()))
    common_calendar = all(
        timestamps == first_calendar for timestamps in series_timestamps.values()
    )
    pointers = _read_csv(source_data / "timeseries_pointers.csv")
    pointer_objects_by_file: dict[str, set[str]] = {}
    for row in pointers:
        if row["Simulation"] != "DAY_AHEAD":
            continue
        pointer_objects_by_file.setdefault(Path(row["Data File"]).name, set()).add(
            row["Object"]
        )
    pointer_columns_complete = all(
        bool(series_data[name])
        and set(series_data[name][0]) - {"Year", "Month", "Day", "Period"}
        == pointer_objects_by_file.get(path.name, set())
        for name, path in series_paths.items()
    )
    ramps = [generator.ramp_mw_per_minute for generator in generators]
    return RtsGmlcSummary(
        source_repository=RTS_GMLC_REPOSITORY,
        source_release=RTS_GMLC_RELEASE,
        source_commit=RTS_GMLC_COMMIT,
        source_manifest_sha256=(
            hashlib.sha256((upstream_root / "SHA256SUMS").read_bytes()).hexdigest()
            if (upstream_root / "SHA256SUMS").is_file()
            else ""
        ),
        sha256_manifest_valid=verify_sha256_manifest(upstream_root),
        buses=len(buses),
        generators=len(generators),
        ac_branches=len(branches),
        static_load_mw=sum(float(row["MW Load"]) for row in buses),
        generators_with_positive_ramp=sum(ramp > 0.0 for ramp in ramps),
        ramp_min_mw_per_minute=min(ramps),
        ramp_max_mw_per_minute=max(ramps),
        day_ahead_hours=len(load_points),
        first_timestamp=load_points[0].timestamp,
        last_timestamp=load_points[-1].timestamp,
        day_ahead_rows=series_rows,
        day_ahead_series_timestamp_continuous=series_continuity,
        day_ahead_series_common_calendar=common_calendar,
        day_ahead_core_pointer_columns_complete=pointer_columns_complete,
    )


def _finite_csv_value(
    row: dict[str, str],
    key: str,
    *,
    minimum: float | None = None,
) -> float:
    try:
        value = float(row[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"RTS-GMLC field {key!r} must be numeric") from exc
    if not isfinite(value) or (minimum is not None and value < minimum):
        raise ValueError(f"RTS-GMLC field {key!r} has invalid value {value}")
    return value


def _optional_csv_value(row: dict[str, str], key: str) -> float | None:
    try:
        raw_value = row[key]
    except KeyError as exc:
        raise ValueError(f"RTS-GMLC field {key!r} is missing") from exc
    if raw_value in {"", "NA"}:
        return None
    return _finite_csv_value(row, key)


def _parse_chronological_buses(rows: list[dict[str, str]]) -> tuple[RtsGmlcBus, ...]:
    buses = tuple(
        RtsGmlcBus(
            uid=int(row["Bus ID"]),
            name=row["Bus Name"],
            base_kv=_finite_csv_value(row, "BaseKV", minimum=0.0),
            bus_type=row["Bus Type"],
            area=int(row["Area"]),
            static_load_mw=_finite_csv_value(row, "MW Load", minimum=0.0),
        )
        for row in rows
    )
    if len({bus.uid for bus in buses}) != len(buses):
        raise ValueError("RTS-GMLC bus IDs must be unique")
    if any(bus.base_kv <= 0.0 for bus in buses):
        raise ValueError("RTS-GMLC bus base voltages must be positive")
    reference_buses = [bus.uid for bus in buses if bus.bus_type == "Ref"]
    if len(reference_buses) != 1:
        raise ValueError("RTS-GMLC must contain exactly one reference bus")
    return buses


def _parse_chronological_branches(
    rows: list[dict[str, str]],
) -> tuple[RtsGmlcBranch, ...]:
    branches = []
    for row in rows:
        source_tap = _finite_csv_value(row, "Tr Ratio", minimum=0.0)
        tap_ratio = 1.0 if source_tap == 0.0 else source_tap
        branch = RtsGmlcBranch(
            uid=row["UID"],
            from_bus=int(row["From Bus"]),
            to_bus=int(row["To Bus"]),
            resistance_pu=_finite_csv_value(row, "R", minimum=0.0),
            reactance_pu=_finite_csv_value(row, "X", minimum=0.0),
            charging_susceptance_pu=_finite_csv_value(row, "B"),
            continuous_rating_mw=_finite_csv_value(row, "Cont Rating", minimum=0.0),
            long_term_rating_mw=_finite_csv_value(row, "LTE Rating", minimum=0.0),
            short_term_rating_mw=_finite_csv_value(row, "STE Rating", minimum=0.0),
            tap_ratio=tap_ratio,
        )
        if branch.from_bus == branch.to_bus:
            raise ValueError(f"RTS-GMLC branch {branch.uid} is a self-loop")
        if (
            branch.reactance_pu <= 0.0
            or branch.continuous_rating_mw <= 0.0
            or branch.long_term_rating_mw <= 0.0
            or branch.short_term_rating_mw <= 0.0
        ):
            raise ValueError(
                f"RTS-GMLC branch {branch.uid} has invalid electrical limits"
            )
        branches.append(branch)
    if len({branch.uid for branch in branches}) != len(branches):
        raise ValueError("RTS-GMLC AC branch IDs must be unique")
    return tuple(branches)


def _parse_chronological_dc_branches(
    rows: list[dict[str, str]],
) -> tuple[RtsGmlcDcBranch, ...]:
    dc_branches = []
    for row in rows:
        power_limit_mw = _finite_csv_value(row, "MW Load", minimum=0.0)
        if power_limit_mw <= 0.0:
            raise ValueError("RTS-GMLC DC branch power limits must be positive")
        dc_branches.append(
            RtsGmlcDcBranch(
                uid=row["UID"],
                from_bus=int(row["From Bus"]),
                to_bus=int(row["To Bus"]),
                control_mode=row["Control Mode"],
                resistance_ohm=_finite_csv_value(row, "R Line", minimum=0.0),
                p_min_mw=-power_limit_mw,
                p_max_mw=power_limit_mw,
            )
        )
    if len({branch.uid for branch in dc_branches}) != len(dc_branches):
        raise ValueError("RTS-GMLC DC branch IDs must be unique")
    return tuple(dc_branches)


def _generator_dispatch_mode(unit_type: str) -> DispatchMode:
    if unit_type in {"CT", "STEAM", "CC", "NUCLEAR"}:
        return "committable"
    if unit_type in {"HYDRO", "ROR", "RTPV"}:
        return "fixed"
    if unit_type in {"PV", "WIND"}:
        return "curtailable"
    if unit_type in {"CSP", "STORAGE", "SYNC_COND"}:
        return "disabled"
    raise ValueError(f"Unsupported RTS-GMLC unit type {unit_type!r}")


def _generator_disabled_reason(unit_type: str) -> str | None:
    return {
        "CSP": "thermal_energy_storage_state_not_modeled",
        "STORAGE": "electrical_storage_energy_state_not_modeled",
        "SYNC_COND": "zero_active_power_synchronous_condenser",
    }.get(unit_type)


def _build_generator_cost_curve(
    row: dict[str, str],
    *,
    p_min_mw: float,
    p_max_mw: float,
    fuel_price_usd_per_mmbtu: float,
    variable_om_usd_per_mwh: float,
    required: bool,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    percentages = tuple(
        _optional_csv_value(row, f"Output_pct_{index}") for index in range(5)
    )
    active_percentages = tuple(value for value in percentages if value is not None)
    if any(value is not None for value in percentages[len(active_percentages) :]):
        raise ValueError(f"Generator {row['GEN UID']} has a non-contiguous cost curve")
    raw_breakpoints = tuple(value * p_max_mw for value in active_percentages)
    has_positive_widths = len(raw_breakpoints) >= 2 and all(
        later > earlier for earlier, later in zip(raw_breakpoints, raw_breakpoints[1:])
    )
    if not required and not has_positive_widths:
        return (), ()
    if not has_positive_widths:
        raise ValueError(
            f"Generator {row['GEN UID']} cost segments must have positive width"
        )
    if not isclose(raw_breakpoints[0], p_min_mw, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError(
            f"Generator {row['GEN UID']} cost curve does not start at PMin"
        )
    if not isclose(raw_breakpoints[-1], p_max_mw, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError(f"Generator {row['GEN UID']} cost curve does not end at PMax")
    breakpoints = (p_min_mw, *raw_breakpoints[1:-1], p_max_mw)
    heat_rate_average = _finite_csv_value(row, "HR_avg_0", minimum=0.0)
    incremental_heat_rates = tuple(
        _finite_csv_value(row, f"HR_incr_{index}", minimum=0.0)
        for index in range(1, len(breakpoints))
    )
    values = [
        breakpoints[0]
        * (
            fuel_price_usd_per_mmbtu * heat_rate_average / 1000.0
            + variable_om_usd_per_mwh
        )
    ]
    for index, incremental_heat_rate in enumerate(incremental_heat_rates, start=1):
        width_mw = breakpoints[index] - breakpoints[index - 1]
        marginal_cost = (
            fuel_price_usd_per_mmbtu * incremental_heat_rate / 1000.0
            + variable_om_usd_per_mwh
        )
        values.append(values[-1] + width_mw * marginal_cost)
    if not all(isfinite(value) for value in (*breakpoints, *values)):
        raise ValueError(f"Generator {row['GEN UID']} has a non-finite cost curve")
    slopes = tuple(
        (later_cost - earlier_cost) / (later_mw - earlier_mw)
        for earlier_mw, later_mw, earlier_cost, later_cost in zip(
            breakpoints,
            breakpoints[1:],
            values,
            values[1:],
        )
    )
    if any(later + 1e-9 < earlier for earlier, later in zip(slopes, slopes[1:])):
        raise ValueError(f"Generator {row['GEN UID']} cost curve is not convex")
    return tuple(breakpoints), tuple(values)


def _parse_chronological_generators(
    rows: list[dict[str, str]],
) -> tuple[RtsGmlcChronologicalGenerator, ...]:
    generators = []
    for row in rows:
        unit_type = row["Unit Type"]
        dispatch_mode = _generator_dispatch_mode(unit_type)
        p_max_mw = _finite_csv_value(row, "PMax MW", minimum=0.0)
        p_min_mw = _finite_csv_value(row, "PMin MW", minimum=0.0)
        if p_min_mw > p_max_mw:
            raise ValueError(f"Generator {row['GEN UID']} has PMin above PMax")
        ramp_mw_per_minute = _finite_csv_value(row, "Ramp Rate MW/Min", minimum=0.0)
        if dispatch_mode != "disabled" and ramp_mw_per_minute <= 0.0:
            raise ValueError(
                f"Enabled generator {row['GEN UID']} has no ramp capability"
            )
        fuel_price = _finite_csv_value(row, "Fuel Price $/MMBTU", minimum=0.0)
        variable_om = _finite_csv_value(row, "VOM", minimum=0.0)
        non_fuel_start_cost = _finite_csv_value(
            row, "Non Fuel Start Cost $", minimum=0.0
        )
        start_heat_cold = _finite_csv_value(row, "Start Heat Cold MBTU", minimum=0.0)
        start_heat_warm = _finite_csv_value(row, "Start Heat Warm MBTU", minimum=0.0)
        start_heat_hot = _finite_csv_value(row, "Start Heat Hot MBTU", minimum=0.0)
        cost_breakpoints, cost_values = _build_generator_cost_curve(
            row,
            p_min_mw=p_min_mw,
            p_max_mw=p_max_mw,
            fuel_price_usd_per_mmbtu=fuel_price,
            variable_om_usd_per_mwh=variable_om,
            required=dispatch_mode == "committable" or unit_type == "CSP",
        )
        generators.append(
            RtsGmlcChronologicalGenerator(
                uid=row["GEN UID"],
                bus=int(row["Bus ID"]),
                unit_type=unit_type,
                category=row["Category"],
                fuel=row["Fuel"],
                dispatch_mode=dispatch_mode,
                enabled=dispatch_mode != "disabled",
                disabled_reason=_generator_disabled_reason(unit_type),
                p_min_mw=p_min_mw,
                p_max_mw=p_max_mw,
                minimum_down_time_hours=_finite_csv_value(
                    row, "Min Down Time Hr", minimum=0.0
                ),
                minimum_up_time_hours=_finite_csv_value(
                    row, "Min Up Time Hr", minimum=0.0
                ),
                ramp_mw_per_minute=ramp_mw_per_minute,
                ramp_mw_per_hour=60.0 * ramp_mw_per_minute,
                start_time_cold_hours=_finite_csv_value(
                    row, "Start Time Cold Hr", minimum=0.0
                ),
                start_time_warm_hours=_finite_csv_value(
                    row, "Start Time Warm Hr", minimum=0.0
                ),
                start_time_hot_hours=_finite_csv_value(
                    row, "Start Time Hot Hr", minimum=0.0
                ),
                start_heat_cold_mmbtu=start_heat_cold,
                start_heat_warm_mmbtu=start_heat_warm,
                start_heat_hot_mmbtu=start_heat_hot,
                non_fuel_start_cost_usd=non_fuel_start_cost,
                shutdown_cost_usd=_finite_csv_value(
                    row, "Non Fuel Shutdown Cost $", minimum=0.0
                ),
                fuel_price_usd_per_mmbtu=fuel_price,
                variable_om_usd_per_mwh=variable_om,
                cold_start_cost_usd=start_heat_cold * fuel_price + non_fuel_start_cost,
                warm_start_cost_usd=start_heat_warm * fuel_price + non_fuel_start_cost,
                hot_start_cost_usd=start_heat_hot * fuel_price + non_fuel_start_cost,
                cost_breakpoints_mw=cost_breakpoints,
                cost_values_usd_per_hour=cost_values,
            )
        )
    if len({generator.uid for generator in generators}) != len(generators):
        raise ValueError("RTS-GMLC generator IDs must be unique")
    return tuple(generators)


def _validate_chronological_topology(
    buses: tuple[RtsGmlcBus, ...],
    branches: tuple[RtsGmlcBranch, ...],
    dc_branches: tuple[RtsGmlcDcBranch, ...],
    generators: tuple[RtsGmlcChronologicalGenerator, ...],
) -> None:
    bus_ids = {bus.uid for bus in buses}
    for branch in branches:
        if branch.from_bus not in bus_ids or branch.to_bus not in bus_ids:
            raise ValueError(f"RTS-GMLC branch {branch.uid} references an unknown bus")
    for branch in dc_branches:
        if branch.from_bus not in bus_ids or branch.to_bus not in bus_ids:
            raise ValueError(
                f"RTS-GMLC DC branch {branch.uid} references an unknown bus"
            )
        if branch.from_bus == branch.to_bus:
            raise ValueError(f"RTS-GMLC DC branch {branch.uid} is a self-loop")
    for generator in generators:
        if generator.bus not in bus_ids:
            raise ValueError(
                f"RTS-GMLC generator {generator.uid} references an unknown bus"
            )

    adjacency = {bus_id: set() for bus_id in bus_ids}
    for branch in branches:
        adjacency[branch.from_bus].add(branch.to_bus)
        adjacency[branch.to_bus].add(branch.from_bus)
    visited: set[int] = set()
    pending = [next(iter(bus_ids))]
    while pending:
        bus_id = pending.pop()
        if bus_id in visited:
            continue
        visited.add(bus_id)
        pending.extend(adjacency[bus_id] - visited)
    if visited != bus_ids:
        raise ValueError("RTS-GMLC AC network must be connected")


def _timeseries_file_lookup(timeseries_root: Path) -> dict[str, Path]:
    lookup: dict[str, Path] = {}
    for path in timeseries_root.rglob("*.csv"):
        key = path.name.casefold()
        if key in lookup:
            raise ValueError(f"Duplicate RTS-GMLC timeseries filename {path.name}")
        lookup[key] = path
    return lookup


def _pointer_file(
    pointer: dict[str, str],
    file_lookup: dict[str, Path],
) -> Path:
    key = Path(pointer["Data File"].replace("\\", "/")).name.casefold()
    try:
        return file_lookup[key]
    except KeyError as exc:
        raise ValueError(
            f"RTS-GMLC pointer file {pointer['Data File']!r} is unavailable"
        ) from exc


def _validate_pointer_scaling(pointer: dict[str, str]) -> None:
    scaling = _finite_csv_value(pointer, "Scaling Factor", minimum=0.0)
    if scaling <= 0.0:
        raise ValueError("RTS-GMLC pointer scaling factors must be positive")


def _read_hourly_pointer_series(
    path: Path,
    *,
    expected_columns: set[str],
    expected_calendar: tuple[datetime, ...] | None = None,
) -> tuple[list[dict[str, str]], tuple[datetime, ...]]:
    rows = _read_csv(path)
    if len(rows) != _RTS_GMLC_DAY_AHEAD_HOURS:
        raise ValueError(
            f"RTS-GMLC day-ahead file {path.name} must contain "
            f"{_RTS_GMLC_DAY_AHEAD_HOURS} hours"
        )
    if not rows:
        raise ValueError(f"RTS-GMLC day-ahead file {path.name} is empty")
    columns = set(rows[0])
    if not _TIME_COLUMNS.issubset(columns):
        raise ValueError(f"RTS-GMLC day-ahead file {path.name} lacks timestamp columns")
    actual_columns = columns - _TIME_COLUMNS
    if actual_columns != expected_columns:
        raise ValueError(
            f"RTS-GMLC pointer columns do not match {path.name}: "
            f"expected {sorted(expected_columns)}, found {sorted(actual_columns)}"
        )
    timestamps = _timestamps(rows)
    if not _is_continuous_hourly(timestamps):
        raise ValueError(
            f"RTS-GMLC day-ahead file {path.name} is not hourly-continuous"
        )
    if expected_calendar is not None and timestamps != expected_calendar:
        raise ValueError(
            f"RTS-GMLC day-ahead file {path.name} uses a different calendar"
        )
    return rows, timestamps


def _load_regional_demand(
    pointers: list[dict[str, str]],
    file_lookup: dict[str, Path],
    buses: tuple[RtsGmlcBus, ...],
) -> tuple[tuple[dict[int, float], ...], tuple[datetime, ...]]:
    load_pointers = [
        pointer
        for pointer in pointers
        if pointer["Simulation"] == "DAY_AHEAD"
        and pointer["Category"] == "Area"
        and pointer["Parameter"] == "MW Load"
    ]
    pointers_by_area = {int(pointer["Object"]): pointer for pointer in load_pointers}
    if len(pointers_by_area) != len(load_pointers) or set(pointers_by_area) != {
        1,
        2,
        3,
    }:
        raise ValueError("RTS-GMLC must provide one day-ahead load pointer per area")
    load_files = {_pointer_file(pointer, file_lookup) for pointer in load_pointers}
    if len(load_files) != 1:
        raise ValueError("RTS-GMLC regional load pointers must share one file")
    rows, calendar = _read_hourly_pointer_series(
        load_files.pop(),
        expected_columns={str(area) for area in pointers_by_area},
    )

    static_load_by_area = {
        area: fsum(bus.static_load_mw for bus in buses if bus.area == area)
        for area in pointers_by_area
    }
    for area, pointer in pointers_by_area.items():
        _validate_pointer_scaling(pointer)
        scaling = _finite_csv_value(pointer, "Scaling Factor")
        if not isclose(
            scaling,
            static_load_by_area[area],
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise ValueError(
                f"RTS-GMLC load pointer scaling does not match Area {area} static load"
            )
    regional_demand = tuple(
        {
            area: _finite_csv_value(row, str(area), minimum=0.0)
            for area in pointers_by_area
        }
        for row in rows
    )
    return regional_demand, calendar


def _load_generator_bound_profiles(
    pointers: list[dict[str, str]],
    file_lookup: dict[str, Path],
    calendar: tuple[datetime, ...],
    generators: tuple[RtsGmlcChronologicalGenerator, ...],
) -> dict[tuple[str, str], tuple[float, ...]]:
    generators_by_uid = {generator.uid: generator for generator in generators}
    bound_pointers = [
        pointer
        for pointer in pointers
        if pointer["Simulation"] == "DAY_AHEAD"
        and pointer["Category"] == "Generator"
        and pointer["Parameter"] in {"PMin MW", "PMax MW"}
    ]
    pointers_by_file: dict[Path, list[dict[str, str]]] = {}
    seen_targets: set[tuple[str, str]] = set()
    for pointer in bound_pointers:
        uid = pointer["Object"]
        target = (uid, pointer["Parameter"])
        if uid not in generators_by_uid:
            raise ValueError(f"RTS-GMLC pointer references unknown generator {uid}")
        if target in seen_targets:
            raise ValueError(f"Duplicate RTS-GMLC generator pointer {target}")
        seen_targets.add(target)
        _validate_pointer_scaling(pointer)
        pointers_by_file.setdefault(_pointer_file(pointer, file_lookup), []).append(
            pointer
        )

    profiles: dict[tuple[str, str], tuple[float, ...]] = {}
    for path, file_pointers in pointers_by_file.items():
        objects = {pointer["Object"] for pointer in file_pointers}
        rows, _ = _read_hourly_pointer_series(
            path,
            expected_columns=objects,
            expected_calendar=calendar,
        )
        values_by_object = {
            uid: tuple(_finite_csv_value(row, uid, minimum=0.0) for row in rows)
            for uid in objects
        }
        for pointer in file_pointers:
            profiles[(pointer["Object"], pointer["Parameter"])] = values_by_object[
                pointer["Object"]
            ]

    for generator in generators:
        actual_parameters = {
            parameter for uid, parameter in profiles if uid == generator.uid
        }
        expected_parameters: set[str]
        if generator.dispatch_mode == "fixed":
            expected_parameters = {"PMin MW", "PMax MW"}
        elif generator.dispatch_mode == "curtailable":
            expected_parameters = {"PMax MW"}
        else:
            expected_parameters = set()
        if actual_parameters != expected_parameters:
            raise ValueError(
                f"Generator {generator.uid} pointer parameters are "
                f"{sorted(actual_parameters)}, expected {sorted(expected_parameters)}"
            )
        if not expected_parameters:
            continue
        maximum_profile = profiles[(generator.uid, "PMax MW")]
        if any(value > generator.p_max_mw + 1e-6 for value in maximum_profile):
            raise ValueError(f"Generator {generator.uid} profile exceeds static PMax")
        if generator.dispatch_mode == "fixed":
            minimum_profile = profiles[(generator.uid, "PMin MW")]
            if any(
                not isclose(minimum, maximum, rel_tol=0.0, abs_tol=1e-9)
                for minimum, maximum in zip(minimum_profile, maximum_profile)
            ):
                raise ValueError(f"Fixed generator {generator.uid} must have PMin=PMax")
    return profiles


def _load_spin_up_profiles(
    pointers: list[dict[str, str]],
    file_lookup: dict[str, Path],
    calendar: tuple[datetime, ...],
) -> dict[int, tuple[float, ...]]:
    object_to_area = {"Spin_Up_R1": 1, "Spin_Up_R2": 2, "Spin_Up_R3": 3}
    spin_pointers = [
        pointer
        for pointer in pointers
        if pointer["Simulation"] == "DAY_AHEAD"
        and pointer["Category"] == "Reserve"
        and pointer["Parameter"] == "Requirement"
        and pointer["Object"] in object_to_area
    ]
    pointers_by_object = {pointer["Object"]: pointer for pointer in spin_pointers}
    if len(pointers_by_object) != len(spin_pointers) or set(pointers_by_object) != set(
        object_to_area
    ):
        raise ValueError("RTS-GMLC must provide one Spin Up pointer per area")
    profiles = {}
    for reserve_object, area in object_to_area.items():
        pointer = pointers_by_object[reserve_object]
        _validate_pointer_scaling(pointer)
        rows, _ = _read_hourly_pointer_series(
            _pointer_file(pointer, file_lookup),
            expected_columns={reserve_object},
            expected_calendar=calendar,
        )
        profiles[area] = tuple(
            _finite_csv_value(row, reserve_object, minimum=0.0) for row in rows
        )
    return profiles


def load_rts_gmlc_chronological_data(
    upstream_root: Path,
    *,
    base_mva: float = _RTS_GMLC_BASE_MVA,
) -> RtsGmlcChronologicalData:
    """Load the pinned 2020 day-ahead RTS-GMLC chronology in native MW units."""

    if not isfinite(base_mva) or base_mva != _RTS_GMLC_BASE_MVA:
        raise ValueError("RTS-GMLC chronological data requires a 100 MVA base")
    source_data = upstream_root / "RTS_Data" / "SourceData"
    timeseries_root = upstream_root / "RTS_Data" / "timeseries_data_files"
    buses = _parse_chronological_buses(_read_csv(source_data / "bus.csv"))
    branches = _parse_chronological_branches(_read_csv(source_data / "branch.csv"))
    dc_branches = _parse_chronological_dc_branches(
        _read_csv(source_data / "dc_branch.csv")
    )
    generators = _parse_chronological_generators(_read_csv(source_data / "gen.csv"))
    _validate_chronological_topology(buses, branches, dc_branches, generators)

    pointers = _read_csv(source_data / "timeseries_pointers.csv")
    file_lookup = _timeseries_file_lookup(timeseries_root)
    regional_demand, calendar = _load_regional_demand(pointers, file_lookup, buses)
    generator_profiles = _load_generator_bound_profiles(
        pointers,
        file_lookup,
        calendar,
        generators,
    )
    spin_up_profiles = _load_spin_up_profiles(pointers, file_lookup, calendar)

    buses_by_area = {
        area: tuple(bus for bus in buses if bus.area == area) for area in (1, 2, 3)
    }
    if any(not area_buses for area_buses in buses_by_area.values()) or any(
        bus.area not in buses_by_area for bus in buses
    ):
        raise ValueError("RTS-GMLC bus areas must be exactly 1, 2, and 3")
    static_load_by_area = {
        area: fsum(bus.static_load_mw for bus in area_buses)
        for area, area_buses in buses_by_area.items()
    }
    if any(total <= 0.0 for total in static_load_by_area.values()):
        raise ValueError("RTS-GMLC areas must have positive static load")

    hourly_points = []
    for index, timestamp in enumerate(calendar):
        demand_by_bus_mw = {
            bus.uid: regional_demand[index][bus.area]
            * bus.static_load_mw
            / static_load_by_area[bus.area]
            for bus in buses
        }
        for area, area_buses in buses_by_area.items():
            reconstructed = fsum(demand_by_bus_mw[bus.uid] for bus in area_buses)
            if not isclose(
                reconstructed,
                regional_demand[index][area],
                rel_tol=1e-12,
                abs_tol=1e-8,
            ):
                raise ValueError(
                    f"RTS-GMLC nodal load does not reconstruct Area {area} at {timestamp}"
                )

        generator_min_mw: dict[str, float] = {}
        generator_max_mw: dict[str, float] = {}
        for generator in generators:
            if generator.dispatch_mode == "disabled":
                minimum = maximum = 0.0
            elif generator.dispatch_mode == "fixed":
                minimum = generator_profiles[(generator.uid, "PMin MW")][index]
                maximum = generator_profiles[(generator.uid, "PMax MW")][index]
            elif generator.dispatch_mode == "curtailable":
                minimum = 0.0
                maximum = generator_profiles[(generator.uid, "PMax MW")][index]
            else:
                minimum = generator.p_min_mw
                maximum = generator.p_max_mw
            if not isfinite(minimum) or not isfinite(maximum) or minimum > maximum:
                raise ValueError(
                    f"Generator {generator.uid} has invalid bounds at {timestamp}"
                )
            generator_min_mw[generator.uid] = minimum
            generator_max_mw[generator.uid] = maximum
        hourly_points.append(
            RtsGmlcHourlyPoint(
                timestamp=timestamp,
                demand_by_bus_mw=demand_by_bus_mw,
                generator_min_mw=generator_min_mw,
                generator_max_mw=generator_max_mw,
                spin_up_requirement_by_area_mw={
                    area: profile[index] for area, profile in spin_up_profiles.items()
                },
            )
        )

    reference_bus = next(bus.uid for bus in buses if bus.bus_type == "Ref")
    return RtsGmlcChronologicalData(
        base_mva=base_mva,
        reference_bus=reference_bus,
        buses=buses,
        branches=branches,
        dc_branches=dc_branches,
        generators=generators,
        hourly_points=tuple(hourly_points),
    )
