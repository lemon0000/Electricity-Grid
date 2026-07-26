"""Benchmark AC replay support for native RTS-GMLC dispatch results."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from math import acos, isfinite, tan
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from pypower.api import ppoption, runpf
from pypower.idx_brch import (
    ANGMAX,
    ANGMIN,
    BR_B,
    BR_R,
    BR_STATUS,
    BR_X,
    F_BUS,
    PF,
    PT,
    QF,
    QT,
    RATE_A,
    RATE_B,
    RATE_C,
    SHIFT,
    TAP,
    T_BUS,
)
from pypower.idx_bus import (
    BASE_KV,
    BS,
    BUS_AREA,
    BUS_I,
    BUS_TYPE,
    GS,
    PD,
    PQ,
    PV,
    QD,
    REF,
    VA,
    VM,
    VMAX,
    VMIN,
    ZONE,
)
from pypower.idx_gen import (
    APF,
    GEN_BUS,
    GEN_STATUS,
    MBASE,
    PC1,
    PC2,
    PG,
    PMAX,
    PMIN,
    QC1MAX,
    QC1MIN,
    QC2MAX,
    QC2MIN,
    QG,
    QMAX,
    QMIN,
    RAMP_10,
    RAMP_30,
    RAMP_AGC,
    RAMP_Q,
    VG,
)


@dataclass(frozen=True)
class RtsGmlcAcTemplate:
    base_mva: float
    case_template: dict[str, object]
    bus_row_by_uid: dict[int, int]
    generator_row_by_uid: dict[str, int]
    branch_row_by_uid: dict[str, int]
    generator_uid_by_row: tuple[str, ...]
    branch_uid_by_row: tuple[str, ...]
    generator_unit_type_by_uid: dict[str, str]
    generator_initial_q_mvar_by_uid: dict[str, float]
    bus_static_p_mw: dict[int, float]
    bus_static_q_mvar: dict[int, float]
    source_reference_bus: int
    dc_branch_endpoints: dict[str, tuple[int, int]]
    dc_branch_limit_mw: dict[str, float]


@dataclass(frozen=True)
class RtsGmlcConfiguredAcCase:
    case: dict[str, object]
    target_generation_mw_by_row: tuple[float, ...]
    active_generator_uids: tuple[str, ...]
    reference_bus: int
    reference_generator_uid: str
    native_reactive_demand_mvar: float
    data_center_reactive_demand_mvar: float
    dc_flow_mw: dict[str, float]


@dataclass(frozen=True)
class RtsGmlcAcReplayResult:
    evaluated: bool
    converged: bool
    secure: bool
    status: str
    branch_rating: str
    min_voltage_pu: float | None
    min_voltage_bus: int | None
    max_voltage_pu: float | None
    max_voltage_bus: int | None
    max_voltage_violation_pu: float | None
    max_branch_loading_fraction: float | None
    max_loaded_branch_uid: str | None
    max_active_power_violation_mw: float | None
    max_active_power_violation_generator_uid: str | None
    max_reactive_power_violation_mvar: float | None
    max_reactive_power_violation_generator_uid: str | None
    max_non_slack_pg_deviation_mw: float | None
    reference_bus: int
    reference_generator_uid: str
    active_generator_count: int
    requested_generation_mw: float | None
    ac_generation_mw: float | None
    slack_and_loss_adjustment_mw: float | None


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def _number(row: Mapping[str, str], field: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid RTS-GMLC AC field {field}") from error
    if not isfinite(value):
        raise ValueError(f"RTS-GMLC AC field {field} must be finite")
    return value


def load_rts_gmlc_ac_template(
    upstream_root: Path,
    *,
    base_mva: float = 100.0,
    voltage_minimum_pu: float = 0.95,
    voltage_maximum_pu: float = 1.05,
) -> RtsGmlcAcTemplate:
    """Build a PYPOWER case template from the pinned RTS-GMLC SourceData."""

    if base_mva != 100.0:
        raise ValueError("The RTS-GMLC AC benchmark requires a 100 MVA base")
    if not 0.0 < voltage_minimum_pu < voltage_maximum_pu:
        raise ValueError("RTS-GMLC AC voltage limits are invalid")
    source = upstream_root / "RTS_Data" / "SourceData"
    bus_rows = _read_csv(source / "bus.csv")
    generator_rows = _read_csv(source / "gen.csv")
    branch_rows = _read_csv(source / "branch.csv")
    dc_rows = _read_csv(source / "dc_branch.csv")
    if (len(bus_rows), len(generator_rows), len(branch_rows), len(dc_rows)) != (
        73,
        158,
        120,
        1,
    ):
        raise ValueError("RTS-GMLC AC SourceData counts drifted")

    bus_type = {"PQ": PQ, "PV": PV, "Ref": REF}
    bus = np.zeros((len(bus_rows), 13), dtype=float)
    bus_row_by_uid: dict[int, int] = {}
    static_p: dict[int, float] = {}
    static_q: dict[int, float] = {}
    reference_buses = []
    for index, row in enumerate(bus_rows):
        uid = int(row["Bus ID"])
        if uid in bus_row_by_uid or row["Bus Type"] not in bus_type:
            raise ValueError("RTS-GMLC AC bus identity drifted")
        bus_row_by_uid[uid] = index
        static_p[uid] = _number(row, "MW Load")
        static_q[uid] = _number(row, "MVAR Load")
        bus[index, BUS_I] = uid
        bus[index, BUS_TYPE] = bus_type[row["Bus Type"]]
        bus[index, PD] = static_p[uid]
        bus[index, QD] = static_q[uid]
        bus[index, GS] = _number(row, "MW Shunt G")
        bus[index, BS] = _number(row, "MVAR Shunt B")
        bus[index, BUS_AREA] = int(row["Area"])
        bus[index, VM] = _number(row, "V Mag")
        bus[index, VA] = _number(row, "V Angle")
        bus[index, BASE_KV] = _number(row, "BaseKV")
        bus[index, ZONE] = int(float(row["Zone"]))
        bus[index, VMAX] = voltage_maximum_pu
        bus[index, VMIN] = voltage_minimum_pu
        if row["Bus Type"] == "Ref":
            reference_buses.append(uid)
    if len(reference_buses) != 1:
        raise ValueError("RTS-GMLC AC data require exactly one source reference bus")

    generator = np.zeros((len(generator_rows), 21), dtype=float)
    generator_row_by_uid: dict[str, int] = {}
    generator_uids = []
    generator_types = {}
    generator_initial_q = {}
    for index, row in enumerate(generator_rows):
        uid = row["GEN UID"]
        bus_uid = int(row["Bus ID"])
        if uid in generator_row_by_uid or bus_uid not in bus_row_by_uid:
            raise ValueError("RTS-GMLC AC generator identity drifted")
        generator_row_by_uid[uid] = index
        generator_uids.append(uid)
        generator_types[uid] = row["Unit Type"]
        generator_initial_q[uid] = _number(row, "MVAR Inj")
        generator[index, GEN_BUS] = bus_uid
        generator[index, PG] = _number(row, "MW Inj")
        generator[index, QG] = generator_initial_q[uid]
        generator[index, QMAX] = _number(row, "QMax MVAR")
        generator[index, QMIN] = _number(row, "QMin MVAR")
        generator[index, VG] = _number(row, "V Setpoint p.u.")
        # The official RTS_GMLC.m conversion uses the system base here.
        generator[index, MBASE] = base_mva
        generator[index, GEN_STATUS] = 1.0
        generator[index, PMAX] = _number(row, "PMax MW")
        generator[index, PMIN] = _number(row, "PMin MW")
        generator[index, PC1] = 0.0
        generator[index, PC2] = 0.0
        generator[index, QC1MIN] = 0.0
        generator[index, QC1MAX] = 0.0
        generator[index, QC2MIN] = 0.0
        generator[index, QC2MAX] = 0.0
        ramp = _number(row, "Ramp Rate MW/Min")
        generator[index, RAMP_AGC] = ramp
        generator[index, RAMP_10] = ramp
        generator[index, RAMP_30] = ramp
        generator[index, RAMP_Q] = ramp
        generator[index, APF] = 0.0

    branch = np.zeros((len(branch_rows), 13), dtype=float)
    branch_row_by_uid: dict[str, int] = {}
    branch_uids = []
    for index, row in enumerate(branch_rows):
        uid = row["UID"]
        from_bus = int(row["From Bus"])
        to_bus = int(row["To Bus"])
        if (
            uid in branch_row_by_uid
            or from_bus not in bus_row_by_uid
            or to_bus not in bus_row_by_uid
        ):
            raise ValueError("RTS-GMLC AC branch identity drifted")
        branch_row_by_uid[uid] = index
        branch_uids.append(uid)
        branch[index, F_BUS] = from_bus
        branch[index, T_BUS] = to_bus
        branch[index, BR_R] = _number(row, "R")
        branch[index, BR_X] = _number(row, "X")
        branch[index, BR_B] = _number(row, "B")
        branch[index, RATE_A] = _number(row, "Cont Rating")
        branch[index, RATE_B] = _number(row, "LTE Rating")
        branch[index, RATE_C] = _number(row, "STE Rating")
        branch[index, TAP] = _number(row, "Tr Ratio")
        branch[index, SHIFT] = 0.0
        branch[index, BR_STATUS] = 1.0
        branch[index, ANGMIN] = -180.0
        branch[index, ANGMAX] = 180.0

    dc_endpoints = {}
    dc_limits = {}
    for row in dc_rows:
        uid = row["UID"]
        endpoints = (int(row["From Bus"]), int(row["To Bus"]))
        if uid in dc_endpoints or any(item not in bus_row_by_uid for item in endpoints):
            raise ValueError("RTS-GMLC AC DC-branch identity drifted")
        dc_endpoints[uid] = endpoints
        dc_limits[uid] = abs(_number(row, "MW Load"))

    case = {
        "version": "2",
        "baseMVA": float(base_mva),
        "bus": bus,
        "gen": generator,
        "branch": branch,
    }
    return RtsGmlcAcTemplate(
        base_mva=float(base_mva),
        case_template=case,
        bus_row_by_uid=bus_row_by_uid,
        generator_row_by_uid=generator_row_by_uid,
        branch_row_by_uid=branch_row_by_uid,
        generator_uid_by_row=tuple(generator_uids),
        branch_uid_by_row=tuple(branch_uids),
        generator_unit_type_by_uid=generator_types,
        generator_initial_q_mvar_by_uid=generator_initial_q,
        bus_static_p_mw=static_p,
        bus_static_q_mvar=static_q,
        source_reference_bus=reference_buses[0],
        dc_branch_endpoints=dc_endpoints,
        dc_branch_limit_mw=dc_limits,
    )


def reconstruct_rts_gmlc_dc_flows(
    data: Any,
    *,
    demand_by_bus_mw: Mapping[int, float],
    generation_mw: Mapping[str, float],
    ac_branch_flows_mw: Mapping[str, float],
    tolerance_mw: float = 1.0e-6,
) -> tuple[dict[str, float], float]:
    """Recover each saved SCUC HVDC flow from endpoint nodal balances."""

    bus_uids = {int(bus.uid) for bus in data.buses}
    if set(demand_by_bus_mw) != bus_uids:
        raise ValueError("RTS-GMLC AC reconstruction demand keys drifted")
    if set(generation_mw) != {generator.uid for generator in data.generators}:
        raise ValueError("RTS-GMLC AC reconstruction generator keys drifted")
    if set(ac_branch_flows_mw) != {branch.uid for branch in data.branches}:
        raise ValueError("RTS-GMLC AC reconstruction branch keys drifted")
    generation_by_bus = {bus: 0.0 for bus in bus_uids}
    for generator in data.generators:
        generation_by_bus[int(generator.bus)] += float(generation_mw[generator.uid])
    ac_export = {bus: 0.0 for bus in bus_uids}
    for branch in data.branches:
        flow = float(ac_branch_flows_mw[branch.uid])
        ac_export[int(branch.from_bus)] += flow
        ac_export[int(branch.to_bus)] -= flow

    flows = {}
    maximum_residual = 0.0
    for branch in data.dc_branches:
        from_bus = int(branch.from_bus)
        to_bus = int(branch.to_bus)
        from_value = (
            generation_by_bus[from_bus]
            - float(demand_by_bus_mw[from_bus])
            - ac_export[from_bus]
        )
        to_value = -(
            generation_by_bus[to_bus]
            - float(demand_by_bus_mw[to_bus])
            - ac_export[to_bus]
        )
        residual = abs(from_value - to_value)
        maximum_residual = max(maximum_residual, residual)
        if residual > tolerance_mw:
            raise RuntimeError(
                f"RTS-GMLC reconstructed DC flow {branch.uid} disagrees by {residual} MW"
            )
        flows[branch.uid] = 0.5 * (from_value + to_value)
    return flows, maximum_residual


def configure_rts_gmlc_ac_case(
    template: RtsGmlcAcTemplate,
    data: Any,
    point: Any,
    *,
    generation_mw: Mapping[str, float],
    commitment: Mapping[str, bool],
    dc_bus: int,
    data_center_power_mw: float,
    data_center_power_factor: float,
    dc_flows_mw: Mapping[str, float],
    outaged_branch_uid: str | None = None,
    outaged_generator_uid: str | None = None,
    tolerance: float = 1.0e-6,
) -> RtsGmlcConfiguredAcCase:
    """Apply one hourly SCUC state to an independent PYPOWER AC case."""

    generator_uids = {generator.uid for generator in data.generators}
    if set(generation_mw) != generator_uids or set(commitment) != generator_uids:
        raise ValueError("RTS-GMLC AC dispatch generator keys drifted")
    if any(type(value) is not bool for value in commitment.values()):
        raise ValueError("RTS-GMLC AC commitment values must be bool")
    if dc_bus not in template.bus_row_by_uid:
        raise ValueError("RTS-GMLC AC data-center bus is unknown")
    if not 0.0 < data_center_power_factor <= 1.0:
        raise ValueError("RTS-GMLC AC data-center power factor must be in (0, 1]")
    if set(dc_flows_mw) != set(template.dc_branch_endpoints):
        raise ValueError("RTS-GMLC AC DC-flow keys drifted")
    if (
        outaged_branch_uid is not None
        and outaged_branch_uid not in template.branch_row_by_uid
    ):
        raise ValueError("RTS-GMLC AC branch outage is unknown")
    if (
        outaged_generator_uid is not None
        and outaged_generator_uid not in template.generator_row_by_uid
    ):
        raise ValueError("RTS-GMLC AC generator outage is unknown")

    case = {
        "version": template.case_template["version"],
        "baseMVA": template.case_template["baseMVA"],
        "bus": np.array(template.case_template["bus"], copy=True),
        "gen": np.array(template.case_template["gen"], copy=True),
        "branch": np.array(template.case_template["branch"], copy=True),
    }
    bus = case["bus"]
    generator = case["gen"]
    branch = case["branch"]
    if set(point.demand_by_bus_mw) != set(template.bus_row_by_uid):
        raise ValueError("RTS-GMLC AC hourly demand keys drifted")
    native_q = 0.0
    for uid, row_index in template.bus_row_by_uid.items():
        active_power = float(point.demand_by_bus_mw[uid])
        static_power = template.bus_static_p_mw[uid]
        static_reactive = template.bus_static_q_mvar[uid]
        if static_power <= tolerance:
            if abs(active_power) > tolerance or abs(static_reactive) > tolerance:
                raise ValueError(
                    "Cannot scale RTS-GMLC reactive demand at a zero-load bus"
                )
            reactive_power = 0.0
        else:
            reactive_power = active_power * static_reactive / static_power
        bus[row_index, PD] = active_power
        bus[row_index, QD] = reactive_power
        native_q += reactive_power

    dc_q = (
        0.0
        if data_center_power_factor == 1.0
        else float(data_center_power_mw) * tan(acos(float(data_center_power_factor)))
    )
    dc_bus_row = template.bus_row_by_uid[dc_bus]
    bus[dc_bus_row, PD] += float(data_center_power_mw)
    bus[dc_bus_row, QD] += dc_q
    for uid, flow in dc_flows_mw.items():
        limit = template.dc_branch_limit_mw[uid]
        if abs(float(flow)) > limit + tolerance:
            raise ValueError(f"RTS-GMLC AC DC flow {uid} exceeds its public limit")
        from_bus, to_bus = template.dc_branch_endpoints[uid]
        bus[template.bus_row_by_uid[from_bus], PD] += float(flow)
        bus[template.bus_row_by_uid[to_bus], PD] -= float(flow)

    data_generator_by_uid = {item.uid: item for item in data.generators}
    active_uids = []
    target_by_row = []
    for uid in template.generator_uid_by_row:
        row = template.generator_row_by_uid[uid]
        item = data_generator_by_uid[uid]
        target = float(generation_mw[uid])
        unit_type = template.generator_unit_type_by_uid[uid]
        if unit_type == "SYNC_COND":
            active = outaged_generator_uid != uid
            lower = upper = 0.0
        elif not item.enabled:
            active = False
            lower = upper = 0.0
        elif item.dispatch_mode == "committable":
            active = commitment[uid] and outaged_generator_uid != uid
            lower = float(point.generator_min_mw[uid])
            upper = float(point.generator_max_mw[uid])
        else:
            active = outaged_generator_uid != uid
            lower = float(point.generator_min_mw[uid])
            upper = float(point.generator_max_mw[uid])
        if not active and abs(target) > tolerance:
            raise ValueError(f"Inactive AC generator {uid} has a nonzero target")
        generator[row, GEN_STATUS] = int(active)
        generator[row, PG] = target if active else 0.0
        generator[row, PMIN] = lower
        generator[row, PMAX] = upper
        if active:
            initial_q = template.generator_initial_q_mvar_by_uid[uid]
            generator[row, QG] = min(
                max(initial_q, float(generator[row, QMIN])),
                float(generator[row, QMAX]),
            )
            active_uids.append(uid)
        else:
            generator[row, QG] = 0.0
        target_by_row.append(target if active else 0.0)

    if outaged_branch_uid is not None:
        branch[template.branch_row_by_uid[outaged_branch_uid], BR_STATUS] = 0.0

    bus[:, BUS_TYPE] = PQ
    active_q_buses = {
        int(generator[row, GEN_BUS])
        for row in range(len(generator))
        if generator[row, GEN_STATUS] > 0.0
        and generator[row, QMAX] - generator[row, QMIN] > tolerance
    }
    for uid in active_q_buses:
        bus[template.bus_row_by_uid[uid], BUS_TYPE] = PV
    active_real_rows = [
        row
        for row in range(len(generator))
        if generator[row, GEN_STATUS] > 0.0 and generator[row, PMAX] > tolerance
    ]
    if not active_real_rows:
        raise ValueError("RTS-GMLC AC case has no active real-power generator")
    source_reference_rows = [
        row
        for row in active_real_rows
        if int(generator[row, GEN_BUS]) == template.source_reference_bus
    ]
    if source_reference_rows:
        reference_bus = template.source_reference_bus
        reference_row = source_reference_rows[0]
    else:
        reference_row = max(
            active_real_rows,
            key=lambda row: (
                float(generator[row, PMAX] - generator[row, PG]),
                float(generator[row, PG] - generator[row, PMIN]),
                -row,
            ),
        )
        reference_bus = int(generator[reference_row, GEN_BUS])
    bus[template.bus_row_by_uid[reference_bus], BUS_TYPE] = REF
    reference_uid = template.generator_uid_by_row[reference_row]
    return RtsGmlcConfiguredAcCase(
        case=case,
        target_generation_mw_by_row=tuple(target_by_row),
        active_generator_uids=tuple(active_uids),
        reference_bus=reference_bus,
        reference_generator_uid=reference_uid,
        native_reactive_demand_mvar=native_q,
        data_center_reactive_demand_mvar=dc_q,
        dc_flow_mw={uid: float(flow) for uid, flow in dc_flows_mw.items()},
    )


def _not_evaluated(
    configured: RtsGmlcConfiguredAcCase,
    *,
    status: str,
    branch_rating: str,
    evaluated: bool = False,
) -> RtsGmlcAcReplayResult:
    return RtsGmlcAcReplayResult(
        evaluated=evaluated,
        converged=False,
        secure=False,
        status=status,
        branch_rating=branch_rating,
        min_voltage_pu=None,
        min_voltage_bus=None,
        max_voltage_pu=None,
        max_voltage_bus=None,
        max_voltage_violation_pu=None,
        max_branch_loading_fraction=None,
        max_loaded_branch_uid=None,
        max_active_power_violation_mw=None,
        max_active_power_violation_generator_uid=None,
        max_reactive_power_violation_mvar=None,
        max_reactive_power_violation_generator_uid=None,
        max_non_slack_pg_deviation_mw=None,
        reference_bus=configured.reference_bus,
        reference_generator_uid=configured.reference_generator_uid,
        active_generator_count=len(configured.active_generator_uids),
        requested_generation_mw=None,
        ac_generation_mw=None,
        slack_and_loss_adjustment_mw=None,
    )


def validate_rts_gmlc_ac_power_flow(
    template: RtsGmlcAcTemplate,
    configured: RtsGmlcConfiguredAcCase,
    *,
    branch_rating: str,
    voltage_tolerance_pu: float = 1.0e-6,
    power_tolerance: float = 1.0e-4,
    loading_tolerance: float = 1.0e-6,
) -> RtsGmlcAcReplayResult:
    """Run and audit one direct AC power-flow replay without restoration."""

    rating_column = {
        "continuous": RATE_A,
        "long_term": RATE_B,
        "short_term": RATE_C,
    }.get(branch_rating)
    if rating_column is None:
        raise ValueError(f"Unknown RTS-GMLC AC branch rating {branch_rating}")
    try:
        result, success = runpf(
            configured.case,
            ppoption(
                VERBOSE=0,
                OUT_ALL=0,
                PF_ALG=1,
                PF_TOL=1.0e-8,
                PF_MAX_IT=20,
                ENFORCE_Q_LIMS=0,
            ),
        )
    except Exception as error:
        return _not_evaluated(
            configured,
            status=f"ac_error:{type(error).__name__}",
            branch_rating=branch_rating,
        )
    if not success:
        return _not_evaluated(
            configured,
            status="not_converged",
            branch_rating=branch_rating,
            evaluated=True,
        )

    bus = result["bus"]
    generator = result["gen"]
    branch = result["branch"]
    active_generators = generator[:, GEN_STATUS] > 0.0
    active_branches = branch[:, BR_STATUS] > 0.0
    voltage_violation = np.maximum(bus[:, VM] - bus[:, VMAX], bus[:, VMIN] - bus[:, VM])
    max_voltage_violation = float(max(np.max(voltage_violation), 0.0))
    min_voltage_row = int(np.argmin(bus[:, VM]))
    max_voltage_row = int(np.argmax(bus[:, VM]))

    loading = np.zeros(len(branch))
    loading[active_branches] = (
        np.maximum(
            np.hypot(branch[active_branches, PF], branch[active_branches, QF]),
            np.hypot(branch[active_branches, PT], branch[active_branches, QT]),
        )
        / branch[active_branches, rating_column]
    )
    max_branch_row = int(np.argmax(loading))
    active_power_violation = np.maximum(
        generator[:, PG] - generator[:, PMAX],
        generator[:, PMIN] - generator[:, PG],
    )
    reactive_power_violation = np.maximum(
        generator[:, QG] - generator[:, QMAX],
        generator[:, QMIN] - generator[:, QG],
    )
    active_rows = np.flatnonzero(active_generators)
    max_p_row = int(active_rows[np.argmax(active_power_violation[active_generators])])
    max_q_row = int(active_rows[np.argmax(reactive_power_violation[active_generators])])
    max_p_violation = float(max(active_power_violation[max_p_row], 0.0))
    max_q_violation = float(max(reactive_power_violation[max_q_row], 0.0))

    reference_row = template.generator_row_by_uid[configured.reference_generator_uid]
    target = np.asarray(configured.target_generation_mw_by_row)
    deviations = np.abs(generator[:, PG] - target)
    non_slack_active = active_generators.copy()
    non_slack_active[reference_row] = False
    max_non_slack_deviation = (
        float(np.max(deviations[non_slack_active])) if np.any(non_slack_active) else 0.0
    )
    requested_generation = float(np.sum(target[active_generators]))
    ac_generation = float(np.sum(generator[active_generators, PG]))
    secure = (
        max_voltage_violation <= voltage_tolerance_pu
        and float(loading[max_branch_row]) <= 1.0 + loading_tolerance
        and max_p_violation <= power_tolerance
        and max_q_violation <= power_tolerance
        and max_non_slack_deviation <= power_tolerance
    )
    return RtsGmlcAcReplayResult(
        evaluated=True,
        converged=True,
        secure=secure,
        status="secure" if secure else "constraint_violation",
        branch_rating=branch_rating,
        min_voltage_pu=float(bus[min_voltage_row, VM]),
        min_voltage_bus=int(bus[min_voltage_row, BUS_I]),
        max_voltage_pu=float(bus[max_voltage_row, VM]),
        max_voltage_bus=int(bus[max_voltage_row, BUS_I]),
        max_voltage_violation_pu=max_voltage_violation,
        max_branch_loading_fraction=float(loading[max_branch_row]),
        max_loaded_branch_uid=template.branch_uid_by_row[max_branch_row],
        max_active_power_violation_mw=max_p_violation,
        max_active_power_violation_generator_uid=template.generator_uid_by_row[
            max_p_row
        ],
        max_reactive_power_violation_mvar=max_q_violation,
        max_reactive_power_violation_generator_uid=template.generator_uid_by_row[
            max_q_row
        ],
        max_non_slack_pg_deviation_mw=max_non_slack_deviation,
        reference_bus=configured.reference_bus,
        reference_generator_uid=configured.reference_generator_uid,
        active_generator_count=len(configured.active_generator_uids),
        requested_generation_mw=requested_generation,
        ac_generation_mw=ac_generation,
        slack_and_loss_adjustment_mw=ac_generation - requested_generation,
    )


__all__ = [
    "RtsGmlcAcReplayResult",
    "RtsGmlcAcTemplate",
    "RtsGmlcConfiguredAcCase",
    "configure_rts_gmlc_ac_case",
    "load_rts_gmlc_ac_template",
    "reconstruct_rts_gmlc_dc_flows",
    "validate_rts_gmlc_ac_power_flow",
]
