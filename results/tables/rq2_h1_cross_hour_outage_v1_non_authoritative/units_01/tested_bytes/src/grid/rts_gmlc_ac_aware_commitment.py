"""Joint chronological AC feasibility search for a fixed commitment schedule."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Mapping, Sequence

import casadi as ca
import numpy as np
from pypower.idx_brch import (
    ANGMAX,
    ANGMIN,
    BR_STATUS,
    F_BUS,
    PF,
    PT,
    QF,
    QT,
    RATE_A,
    T_BUS,
)
from pypower.idx_bus import (
    BS,
    BUS_I,
    BUS_TYPE,
    GS,
    NONE,
    PD,
    PQ,
    PV,
    QD,
    REF,
    VA,
    VM,
    VMAX,
    VMIN,
)
from pypower.idx_gen import (
    GEN_BUS,
    GEN_STATUS,
    PG,
    PMAX,
    PMIN,
    QG,
    QMAX,
    QMIN,
    VG,
)
from pypower.makeYbus import makeYbus

from src.grid.rts_gmlc_ac_ipopt import (
    IpoptInitialStrategy,
    _FROZEN_IPOPT_OPTIONS,
    _INITIAL_STRATEGIES,
    _constraint_violation,
    _initial_point,
    _integer_ids,
    math_isclose,
)
from src.grid.rts_gmlc_ac_recovery import AcRecoveryInput, _case_sha256
from src.grid.rts_gmlc_ac_step_control import (
    StepControlAudit,
    audit_step_control_solution,
)

_NLP_CONSTRAINT_TOLERANCE = 1.0e-6
_NLP_BOUND_TOLERANCE = 1.0e-8
_CHRONOLOGY_AUDIT_TOLERANCE_MW = 1.0e-6


@dataclass(frozen=True)
class AcAwareCommitmentUnit:
    """Fixed chronological metadata for one committable generator."""

    generator_uid: str
    area: int
    p_max_mw: float
    ramp_mw_per_hour: float
    ramp_mw_per_minute: float
    reserve_eligible: bool
    initial_generation_mw: float
    initial_commitment: bool
    commitment_by_hour: tuple[bool, ...]
    startup_by_hour: tuple[bool, ...]
    shutdown_by_hour: tuple[bool, ...]


@dataclass(frozen=True)
class AcAwareChronology:
    """Continuous timestamps, fixed unit states, and regional Spin requirements."""

    timestamps: tuple[datetime, ...]
    time_step_hours: float
    units: tuple[AcAwareCommitmentUnit, ...]
    spin_up_requirement_by_hour_area_mw: tuple[Mapping[int, float], ...]


@dataclass(frozen=True)
class AcAwareHourResult:
    timestamp: datetime
    solved_case: dict[str, object]
    reserve_up_mw_by_generator_uid: dict[str, float]
    audit: StepControlAudit


@dataclass(frozen=True)
class AcAwareCommitmentResult:
    evaluated: bool
    solver_success: bool
    feasibility_witnessed: bool
    return_status: str
    iterations: int
    initial_strategy: str
    normalized_objective: float
    independent_squared_target_deviation_mw2: float
    maximum_nlp_constraint_violation: float
    maximum_nlp_variable_bound_violation: float
    maximum_ramp_violation_mw: float
    maximum_reserve_bound_violation_mw: float
    maximum_reserve_headroom_violation_mw: float
    maximum_reserve_shortfall_mw: float
    solver_input_cases_unchanged: bool
    hour_results: tuple[AcAwareHourResult, ...]


@dataclass(frozen=True)
class _HourLayout:
    prepared: AcRecoveryInput
    timestamp: datetime
    bus: np.ndarray
    generator: np.ndarray
    branch: np.ndarray
    base_mva: float
    bus_ids: np.ndarray
    generator_bus_ids: np.ndarray
    from_rows: np.ndarray
    to_rows: np.ndarray
    yf: np.ndarray
    yt: np.ndarray
    active_generator: np.ndarray
    adjustable_rows: np.ndarray
    q_variable_rows: np.ndarray
    reserve_uids: tuple[str, ...]
    reserve_rows: np.ndarray
    angle_slice: slice
    voltage_slice: slice
    pg_slice: slice
    qg_slice: slice
    reserve_slice: slice


def _finite_nonnegative(value: object, *, label: str) -> float:
    number = float(value)
    if not isfinite(number) or number < 0.0:
        raise ValueError(f"{label} must be finite and nonnegative")
    return number


def _validate_chronology(
    prepared_cases: tuple[AcRecoveryInput, ...],
    chronology: AcAwareChronology,
    initial_strategy: IpoptInitialStrategy,
    solver_options: Mapping[str, object] | None,
) -> dict[str, AcAwareCommitmentUnit]:
    horizon = len(prepared_cases)
    if horizon == 0:
        raise ValueError("AC-aware commitment requires at least one hour")
    if initial_strategy not in _INITIAL_STRATEGIES:
        raise ValueError(f"Unknown IPOPT AC initial strategy {initial_strategy}")
    options = dict(_FROZEN_IPOPT_OPTIONS if solver_options is None else solver_options)
    if options != _FROZEN_IPOPT_OPTIONS:
        raise ValueError("IPOPT AC solver options drifted from the frozen protocol")
    step_hours = float(chronology.time_step_hours)
    if not isfinite(step_hours) or step_hours <= 0.0:
        raise ValueError("AC-aware chronology time step must be finite and positive")
    if (
        len(chronology.timestamps) != horizon
        or len(chronology.spin_up_requirement_by_hour_area_mw) != horizon
    ):
        raise ValueError("AC-aware chronology length does not match prepared cases")
    if any(timestamp.utcoffset() is None for timestamp in chronology.timestamps):
        raise ValueError("AC-aware chronology timestamps require UTC offsets")
    expected_seconds = 3600.0 * step_hours
    for earlier, later in zip(chronology.timestamps, chronology.timestamps[1:]):
        if abs((later - earlier).total_seconds() - expected_seconds) > 1.0e-6:
            raise ValueError("AC-aware chronology timestamps are not continuous")

    unit_by_uid = {unit.generator_uid: unit for unit in chronology.units}
    if len(unit_by_uid) != len(chronology.units):
        raise ValueError("AC-aware chronology has duplicate generator UIDs")
    for unit in chronology.units:
        if not unit.generator_uid:
            raise ValueError("AC-aware chronology has an empty generator UID")
        if not isinstance(unit.area, int):
            raise ValueError(f"Generator {unit.generator_uid} area must be an integer")
        p_max = _finite_nonnegative(unit.p_max_mw, label="generator p_max_mw")
        _finite_nonnegative(unit.ramp_mw_per_hour, label="generator ramp_mw_per_hour")
        _finite_nonnegative(
            unit.ramp_mw_per_minute, label="generator ramp_mw_per_minute"
        )
        initial_pg = _finite_nonnegative(
            unit.initial_generation_mw, label="generator initial_generation_mw"
        )
        if initial_pg > p_max + _CHRONOLOGY_AUDIT_TOLERANCE_MW:
            raise ValueError(f"Generator {unit.generator_uid} initial PG exceeds Pmax")
        if not unit.initial_commitment and initial_pg > _CHRONOLOGY_AUDIT_TOLERANCE_MW:
            raise ValueError(f"Offline generator {unit.generator_uid} has initial PG")
        sequences = (
            unit.commitment_by_hour,
            unit.startup_by_hour,
            unit.shutdown_by_hour,
        )
        if any(len(sequence) != horizon for sequence in sequences):
            raise ValueError(
                f"Generator {unit.generator_uid} chronology length drifted"
            )
        previous = bool(unit.initial_commitment)
        for hour in range(horizon):
            online = bool(unit.commitment_by_hour[hour])
            startup = bool(unit.startup_by_hour[hour])
            shutdown = bool(unit.shutdown_by_hour[hour])
            if startup and shutdown:
                raise ValueError(
                    f"Generator {unit.generator_uid} starts and shuts down together"
                )
            if int(online) - int(previous) != int(startup) - int(shutdown):
                raise ValueError(
                    f"Generator {unit.generator_uid} transition logic drifted"
                )
            previous = online

    canonical_generator_uids = prepared_cases[0].generator_uid_by_row
    canonical_branch_uids = prepared_cases[0].branch_uid_by_row
    canonical_bus = np.asarray(prepared_cases[0].case["bus"], dtype=float)
    canonical_generator = np.asarray(prepared_cases[0].case["gen"], dtype=float)
    canonical_branch = np.asarray(prepared_cases[0].case["branch"], dtype=float)
    canonical_base_mva = float(prepared_cases[0].case["baseMVA"])
    if set(unit_by_uid) - set(canonical_generator_uids):
        raise ValueError("AC-aware chronology references an unknown generator")
    static_bus_columns = (BUS_I, GS, BS, VMIN, VMAX)
    static_generator_columns = (GEN_BUS, QMIN, QMAX)
    for hour, prepared in enumerate(prepared_cases):
        if prepared.mode != "distributed_committable":
            raise ValueError("AC-aware commitment requires distributed recovery inputs")
        if not prepared.fixed_inputs_preserved:
            raise ValueError("AC-aware prepared input did not preserve frozen fields")
        if _case_sha256(prepared.case) != prepared.recovery_case_sha256:
            raise ValueError("AC-aware prepared case changed before solve")
        if (
            prepared.generator_uid_by_row != canonical_generator_uids
            or prepared.branch_uid_by_row != canonical_branch_uids
        ):
            raise ValueError("AC-aware element mapping drifted across hours")
        bus = np.asarray(prepared.case["bus"], dtype=float)
        generator = np.asarray(prepared.case["gen"], dtype=float)
        branch = np.asarray(prepared.case["branch"], dtype=float)
        if (
            bus.shape != canonical_bus.shape
            or generator.shape != canonical_generator.shape
            or branch.shape != canonical_branch.shape
            or float(prepared.case["baseMVA"]) != canonical_base_mva
        ):
            raise ValueError("AC-aware network dimensions drifted across hours")
        if not np.array_equal(branch, canonical_branch):
            raise ValueError("AC-aware normal-state branch inputs drifted across hours")
        if not np.array_equal(
            bus[:, static_bus_columns], canonical_bus[:, static_bus_columns]
        ) or not np.array_equal(
            generator[:, static_generator_columns],
            canonical_generator[:, static_generator_columns],
        ):
            raise ValueError("AC-aware static bus or generator inputs drifted")
        if not np.all(np.isin(bus[:, BUS_TYPE], (PQ, PV, REF))):
            raise ValueError("AC-aware prepared case has an invalid bus type")
        if np.count_nonzero(bus[:, BUS_TYPE] == REF) != 1:
            raise ValueError(
                "AC-aware prepared case requires exactly one reference bus"
            )
        uid_by_row = prepared.generator_uid_by_row
        row_by_uid = {uid: row for row, uid in enumerate(uid_by_row)}
        expected_adjustable = {
            row_by_uid[uid]
            for uid, unit in unit_by_uid.items()
            if unit.commitment_by_hour[hour]
        }
        if set(prepared.adjustable_generator_rows) != expected_adjustable:
            raise ValueError(
                "AC-aware adjustable rows do not match online committable units"
            )
        for uid, unit in unit_by_uid.items():
            row = row_by_uid[uid]
            online = bool(generator[row, GEN_STATUS] > 0.0)
            if online != bool(unit.commitment_by_hour[hour]):
                raise ValueError(f"Generator {uid} commitment differs from AC case")
            if generator[row, PMAX] > unit.p_max_mw + 1.0e-9:
                raise ValueError(f"Generator {uid} hourly Pmax exceeds chronology Pmax")
        for area, requirement in chronology.spin_up_requirement_by_hour_area_mw[
            hour
        ].items():
            if not isinstance(area, int):
                raise ValueError("Spin reserve area identifiers must be integers")
            _finite_nonnegative(requirement, label="Spin reserve requirement")
    return unit_by_uid


def _build_hour_block(
    prepared: AcRecoveryInput,
    timestamp: datetime,
    unit_by_uid: Mapping[str, AcAwareCommitmentUnit],
    hour: int,
    initial_strategy: IpoptInitialStrategy,
    offset: int,
    constraints: list[ca.MX],
    lower_constraints: list[float],
    upper_constraints: list[float],
) -> tuple[
    _HourLayout,
    ca.MX,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    dict[str, ca.MX],
    ca.MX,
]:
    bus = np.asarray(prepared.case["bus"], dtype=float)
    generator = np.asarray(prepared.case["gen"], dtype=float)
    branch = np.asarray(prepared.case["branch"], dtype=float)
    base_mva = float(prepared.case["baseMVA"])
    if np.any(bus[:, BUS_TYPE] == NONE):
        raise ValueError("AC-aware prepared case contains BUS_TYPE=NONE")
    bus_ids = _integer_ids(bus[:, BUS_I], label="bus")
    if len(set(bus_ids.tolist())) != len(bus_ids):
        raise ValueError("AC-aware prepared case has duplicate bus IDs")
    row_by_bus = {int(bus_id): row for row, bus_id in enumerate(bus_ids)}
    generator_bus_ids = _integer_ids(generator[:, GEN_BUS], label="generator bus")
    from_bus_ids = _integer_ids(branch[:, F_BUS], label="branch from-bus")
    to_bus_ids = _integer_ids(branch[:, T_BUS], label="branch to-bus")
    if any(
        int(bus_id) not in row_by_bus
        for bus_id in np.concatenate((generator_bus_ids, from_bus_ids, to_bus_ids))
    ):
        raise ValueError("AC-aware case contains an unknown element bus")
    if not np.all(np.isin(generator[:, GEN_STATUS], (0.0, 1.0))) or not np.all(
        np.isin(branch[:, BR_STATUS], (0.0, 1.0))
    ):
        raise ValueError("AC-aware case status is not binary")

    bus_count = len(bus)
    generator_count = len(generator)
    from_rows = np.asarray([row_by_bus[int(value)] for value in from_bus_ids])
    to_rows = np.asarray([row_by_bus[int(value)] for value in to_bus_ids])
    internal_bus = np.array(bus, copy=True)
    internal_branch = np.array(branch, copy=True)
    internal_bus[:, BUS_I] = np.arange(bus_count)
    internal_branch[:, F_BUS] = from_rows
    internal_branch[:, T_BUS] = to_rows
    ybus, yf_sparse, yt_sparse = makeYbus(base_mva, internal_bus, internal_branch)
    ybus = ybus.toarray()
    yf = yf_sparse.toarray()
    yt = yt_sparse.toarray()

    active_generator = generator[:, GEN_STATUS] > 0.0
    active_branch = branch[:, BR_STATUS] > 0.0
    adjustable_rows = np.asarray(prepared.adjustable_generator_rows, dtype=int)
    adjustable_set = set(adjustable_rows.tolist())
    q_variable_rows = np.flatnonzero(
        active_generator & (generator[:, QMAX] - generator[:, QMIN] > 1.0e-10)
    )
    q_variable_set = set(q_variable_rows.tolist())
    fixed_p_by_bus = np.zeros(bus_count)
    fixed_q_by_bus = np.zeros(bus_count)
    adjustable_incidence = np.zeros((bus_count, len(adjustable_rows)))
    q_incidence = np.zeros((bus_count, len(q_variable_rows)))
    adjustable_position = {
        row: position for position, row in enumerate(adjustable_rows.tolist())
    }
    q_position = {
        row: position for position, row in enumerate(q_variable_rows.tolist())
    }
    for row in range(generator_count):
        bus_row = row_by_bus[int(generator_bus_ids[row])]
        if row in adjustable_set:
            adjustable_incidence[bus_row, adjustable_position[row]] = 1.0
        elif active_generator[row]:
            fixed_p_by_bus[bus_row] += generator[row, PG]
        if row in q_variable_set:
            q_incidence[bus_row, q_position[row]] = 1.0
        elif active_generator[row]:
            fixed_q_by_bus[bus_row] += generator[row, QG]

    voltage_lower = np.array(bus[:, VMIN], copy=True)
    voltage_upper = np.array(bus[:, VMAX], copy=True)
    q_lower = np.array(generator[q_variable_rows, QMIN], copy=True)
    q_upper = np.array(generator[q_variable_rows, QMAX], copy=True)
    if np.any(voltage_lower <= 0.0) or np.any(voltage_lower >= voltage_upper):
        raise ValueError("AC-aware voltage bounds are invalid")
    online_branch_rows = np.flatnonzero(active_branch)
    if np.any(branch[online_branch_rows, RATE_A] <= 0.0):
        raise ValueError("AC-aware active branch has nonpositive RATE_A")

    reserve_uids = tuple(
        unit.generator_uid for unit in unit_by_uid.values() if unit.reserve_eligible
    )
    row_by_uid = {uid: row for row, uid in enumerate(prepared.generator_uid_by_row)}
    reserve_rows = np.asarray([row_by_uid[uid] for uid in reserve_uids], dtype=int)

    angle = ca.MX.sym(f"angle_{hour}", bus_count)
    voltage = ca.MX.sym(f"voltage_{hour}", bus_count)
    pg = ca.MX.sym(f"pg_{hour}", len(adjustable_rows))
    qg = ca.MX.sym(f"qg_{hour}", len(q_variable_rows))
    reserve = ca.MX.sym(f"reserve_{hour}", len(reserve_uids))
    variables = ca.vertcat(angle, voltage, pg, qg, reserve)

    angle_slice = slice(offset, offset + bus_count)
    voltage_slice = slice(angle_slice.stop, angle_slice.stop + bus_count)
    pg_slice = slice(voltage_slice.stop, voltage_slice.stop + len(adjustable_rows))
    qg_slice = slice(pg_slice.stop, pg_slice.stop + len(q_variable_rows))
    reserve_slice = slice(qg_slice.stop, qg_slice.stop + len(reserve_uids))

    voltage_real = ca.times(voltage, ca.cos(angle))
    voltage_imag = ca.times(voltage, ca.sin(angle))
    conductance = ca.DM(ybus.real)
    susceptance = ca.DM(ybus.imag)
    current_real = conductance @ voltage_real - susceptance @ voltage_imag
    current_imag = susceptance @ voltage_real + conductance @ voltage_imag
    network_p = base_mva * (
        ca.times(voltage_real, current_real) + ca.times(voltage_imag, current_imag)
    )
    network_q = base_mva * (
        ca.times(voltage_imag, current_real) - ca.times(voltage_real, current_imag)
    )
    specified_p = (
        ca.DM(fixed_p_by_bus) + ca.DM(adjustable_incidence) @ pg - ca.DM(bus[:, PD])
    )
    specified_q = ca.DM(fixed_q_by_bus) + ca.DM(q_incidence) @ qg - ca.DM(bus[:, QD])
    constraints.extend((specified_p - network_p, specified_q - network_q))
    lower_constraints.extend([0.0] * (2 * bus_count))
    upper_constraints.extend([0.0] * (2 * bus_count))

    from_conductance = ca.DM(yf.real)
    from_susceptance = ca.DM(yf.imag)
    to_conductance = ca.DM(yt.real)
    to_susceptance = ca.DM(yt.imag)
    from_current_real = (
        from_conductance @ voltage_real - from_susceptance @ voltage_imag
    )
    from_current_imag = (
        from_susceptance @ voltage_real + from_conductance @ voltage_imag
    )
    to_current_real = to_conductance @ voltage_real - to_susceptance @ voltage_imag
    to_current_imag = to_susceptance @ voltage_real + to_conductance @ voltage_imag
    branch_pf = base_mva * (
        ca.times(voltage_real[from_rows], from_current_real)
        + ca.times(voltage_imag[from_rows], from_current_imag)
    )
    branch_qf = base_mva * (
        ca.times(voltage_imag[from_rows], from_current_real)
        - ca.times(voltage_real[from_rows], from_current_imag)
    )
    branch_pt = base_mva * (
        ca.times(voltage_real[to_rows], to_current_real)
        + ca.times(voltage_imag[to_rows], to_current_imag)
    )
    branch_qt = base_mva * (
        ca.times(voltage_imag[to_rows], to_current_real)
        - ca.times(voltage_real[to_rows], to_current_imag)
    )
    rate_limits = branch[online_branch_rows, RATE_A]
    constraints.extend(
        (
            ca.power(branch_pf[online_branch_rows], 2)
            + ca.power(branch_qf[online_branch_rows], 2),
            ca.power(branch_pt[online_branch_rows], 2)
            + ca.power(branch_qt[online_branch_rows], 2),
        )
    )
    lower_constraints.extend([-np.inf] * (2 * len(online_branch_rows)))
    upper_constraints.extend(list(rate_limits**2) + list(rate_limits**2))
    for row in online_branch_rows:
        if branch[row, ANGMIN] != 0.0 and branch[row, ANGMIN] > -360.0:
            constraints.append(angle[from_rows[row]] - angle[to_rows[row]])
            lower_constraints.append(np.deg2rad(branch[row, ANGMIN]))
            upper_constraints.append(np.inf)
        if branch[row, ANGMAX] != 0.0 and branch[row, ANGMAX] < 360.0:
            constraints.append(angle[from_rows[row]] - angle[to_rows[row]])
            lower_constraints.append(-np.inf)
            upper_constraints.append(np.deg2rad(branch[row, ANGMAX]))

    pg_by_uid: dict[str, ca.MX] = {}
    for row, uid in enumerate(prepared.generator_uid_by_row):
        if row in adjustable_set:
            pg_by_uid[uid] = pg[adjustable_position[row]]
        else:
            pg_by_uid[uid] = ca.DM(float(generator[row, PG]))
    for position, uid in enumerate(reserve_uids):
        unit = unit_by_uid[uid]
        row = row_by_uid[uid]
        online = float(unit.commitment_by_hour[hour])
        reserve_cap = 10.0 * unit.ramp_mw_per_minute * online
        constraints.append(reserve[position] + pg_by_uid[uid])
        lower_constraints.append(-np.inf)
        upper_constraints.append(float(generator[row, PMAX]))
        constraints.append(reserve[position])
        lower_constraints.append(0.0)
        upper_constraints.append(reserve_cap)
    targets = np.asarray(prepared.target_generation_mw_by_row, dtype=float)
    objective = ca.sumsqr((pg - ca.DM(targets[adjustable_rows])) / base_mva)
    variable_lower = np.concatenate(
        (
            np.full(bus_count, -np.inf),
            voltage_lower,
            generator[adjustable_rows, PMIN],
            q_lower,
            np.zeros(len(reserve_uids)),
        )
    )
    reserve_upper = np.asarray(
        [
            10.0
            * unit_by_uid[uid].ramp_mw_per_minute
            * float(unit_by_uid[uid].commitment_by_hour[hour])
            for uid in reserve_uids
        ]
    )
    variable_upper = np.concatenate(
        (
            np.full(bus_count, np.inf),
            voltage_upper,
            generator[adjustable_rows, PMAX],
            q_upper,
            reserve_upper,
        )
    )
    source_angle = np.deg2rad(bus[:, VA])
    reference_rows = np.flatnonzero(bus[:, BUS_TYPE] == REF)
    if len(reference_rows) != 1:
        raise ValueError("AC-aware prepared case requires exactly one reference bus")
    variable_lower[reference_rows] = source_angle[reference_rows]
    variable_upper[reference_rows] = source_angle[reference_rows]
    initial = np.concatenate(
        (
            _initial_point(
                initial_strategy,
                bus=bus,
                generator=generator,
                adjustable_rows=adjustable_rows,
                q_variable_rows=q_variable_rows,
                lower_voltage=voltage_lower,
                upper_voltage=voltage_upper,
                lower_q=q_lower,
                upper_q=q_upper,
            ),
            np.zeros(len(reserve_uids)),
        )
    )
    layout = _HourLayout(
        prepared=prepared,
        timestamp=timestamp,
        bus=bus,
        generator=generator,
        branch=branch,
        base_mva=base_mva,
        bus_ids=bus_ids,
        generator_bus_ids=generator_bus_ids,
        from_rows=from_rows,
        to_rows=to_rows,
        yf=yf,
        yt=yt,
        active_generator=active_generator,
        adjustable_rows=adjustable_rows,
        q_variable_rows=q_variable_rows,
        reserve_uids=reserve_uids,
        reserve_rows=reserve_rows,
        angle_slice=angle_slice,
        voltage_slice=voltage_slice,
        pg_slice=pg_slice,
        qg_slice=qg_slice,
        reserve_slice=reserve_slice,
    )
    return (
        layout,
        variables,
        variable_lower,
        variable_upper,
        initial,
        pg_by_uid,
        objective,
    )


def solve_ac_aware_commitment(
    prepared_cases: Sequence[AcRecoveryInput],
    chronology: AcAwareChronology,
    *,
    initial_strategy: IpoptInitialStrategy = "source",
    solver_options: Mapping[str, object] | None = None,
) -> AcAwareCommitmentResult:
    """Solve one joint normal-state AC NLP under a fixed chronological commitment."""

    cases = tuple(prepared_cases)
    unit_by_uid = _validate_chronology(
        cases, chronology, initial_strategy, solver_options
    )
    options = dict(_FROZEN_IPOPT_OPTIONS if solver_options is None else solver_options)
    constraints: list[ca.MX] = []
    lower_constraints: list[float] = []
    upper_constraints: list[float] = []
    variable_blocks = []
    variable_lower_blocks = []
    variable_upper_blocks = []
    initial_blocks = []
    layouts = []
    pg_by_hour_uid = []
    objective = ca.DM(0.0)
    offset = 0
    for hour, (prepared, timestamp) in enumerate(
        zip(cases, chronology.timestamps, strict=True)
    ):
        (
            layout,
            variables,
            variable_lower,
            variable_upper,
            initial,
            pg_by_uid,
            hour_objective,
        ) = _build_hour_block(
            prepared,
            timestamp,
            unit_by_uid,
            hour,
            initial_strategy,
            offset,
            constraints,
            lower_constraints,
            upper_constraints,
        )
        layouts.append(layout)
        variable_blocks.append(variables)
        variable_lower_blocks.append(variable_lower)
        variable_upper_blocks.append(variable_upper)
        initial_blocks.append(initial)
        pg_by_hour_uid.append(pg_by_uid)
        objective += hour_objective
        offset += len(variable_lower)

    step_ramp_mw = {
        uid: unit.ramp_mw_per_hour * chronology.time_step_hours
        for uid, unit in unit_by_uid.items()
    }
    for hour, unit_requirements in enumerate(
        chronology.spin_up_requirement_by_hour_area_mw
    ):
        layout = layouts[hour]
        reserve_position = {
            uid: position for position, uid in enumerate(layout.reserve_uids)
        }
        reserve_symbol = variable_blocks[hour][
            len(layout.bus) * 2
            + len(layout.adjustable_rows)
            + len(layout.q_variable_rows) :
        ]
        for area, requirement in sorted(unit_requirements.items()):
            eligible = [
                uid for uid in layout.reserve_uids if unit_by_uid[uid].area == area
            ]
            expression = sum(
                (reserve_symbol[reserve_position[uid]] for uid in eligible),
                ca.DM(0.0),
            )
            constraints.append(expression)
            lower_constraints.append(float(requirement))
            upper_constraints.append(np.inf)

    for uid, unit in unit_by_uid.items():
        previous_pg: ca.MX = ca.DM(unit.initial_generation_mw)
        for hour in range(len(cases)):
            current_pg = pg_by_hour_uid[hour][uid]
            startup = float(unit.startup_by_hour[hour])
            shutdown = float(unit.shutdown_by_hour[hour])
            constraints.append(current_pg - previous_pg)
            lower_constraints.append(-step_ramp_mw[uid] - unit.p_max_mw * shutdown)
            upper_constraints.append(step_ramp_mw[uid] + unit.p_max_mw * startup)
            previous_pg = current_pg

    variables = ca.vertcat(*variable_blocks)
    problem = {"x": variables, "f": objective, "g": ca.vertcat(*constraints)}
    solver = ca.nlpsol("ac_aware_commitment", "ipopt", problem, options)
    variable_lower = np.concatenate(variable_lower_blocks)
    variable_upper = np.concatenate(variable_upper_blocks)
    initial = np.concatenate(initial_blocks)
    lower_constraints_array = np.asarray(lower_constraints, dtype=float)
    upper_constraints_array = np.asarray(upper_constraints, dtype=float)
    solution = solver(
        x0=initial,
        lbx=variable_lower,
        ubx=variable_upper,
        lbg=lower_constraints_array,
        ubg=upper_constraints_array,
    )
    stats = solver.stats()
    point = np.asarray(solution["x"], dtype=float).reshape(-1)
    constraint_values = np.asarray(solution["g"], dtype=float).reshape(-1)
    if not np.all(np.isfinite(point)) or not np.all(np.isfinite(constraint_values)):
        raise RuntimeError("AC-aware IPOPT solver returned non-finite values")
    maximum_constraint_violation = _constraint_violation(
        constraint_values, lower_constraints_array, upper_constraints_array
    )
    maximum_bound_violation = _constraint_violation(
        point, variable_lower, variable_upper
    )

    hour_results = []
    independent_objective = 0.0
    solved_pg_by_hour_uid: list[dict[str, float]] = []
    for layout in layouts:
        angle = point[layout.angle_slice]
        voltage = point[layout.voltage_slice]
        pg = point[layout.pg_slice]
        qg = point[layout.qg_slice]
        reserve = point[layout.reserve_slice]
        complex_voltage = voltage * np.exp(1j * angle)
        from_flow = (
            layout.base_mva
            * complex_voltage[layout.from_rows]
            * np.conj(layout.yf @ complex_voltage)
        )
        to_flow = (
            layout.base_mva
            * complex_voltage[layout.to_rows]
            * np.conj(layout.yt @ complex_voltage)
        )
        solved_bus = np.array(layout.bus, copy=True)
        solved_generator = np.array(layout.generator, copy=True)
        solved_branch = np.zeros(
            (len(layout.branch), max(layout.branch.shape[1], QT + 1))
        )
        solved_branch[:, : layout.branch.shape[1]] = layout.branch
        solved_bus[:, VM] = voltage
        solved_bus[:, VA] = np.rad2deg(angle)
        solved_generator[layout.adjustable_rows, PG] = pg
        solved_generator[layout.q_variable_rows, QG] = qg
        row_by_bus = {int(bus_id): row for row, bus_id in enumerate(layout.bus_ids)}
        for row in np.flatnonzero(layout.active_generator):
            solved_generator[row, VG] = voltage[
                row_by_bus[int(layout.generator_bus_ids[row])]
            ]
        solved_branch[:, PF] = from_flow.real
        solved_branch[:, QF] = from_flow.imag
        solved_branch[:, PT] = to_flow.real
        solved_branch[:, QT] = to_flow.imag
        solved_case = {
            "version": layout.prepared.case["version"],
            "baseMVA": layout.base_mva,
            "bus": solved_bus,
            "gen": solved_generator,
            "branch": solved_branch,
            "gencost": np.array(layout.prepared.case["gencost"], copy=True),
        }
        targets = np.asarray(layout.prepared.target_generation_mw_by_row, dtype=float)
        squared_deviation = float(np.sum((solved_generator[:, PG] - targets) ** 2))
        independent_objective += squared_deviation
        audit = audit_step_control_solution(
            layout.prepared,
            solved_case,
            solver_objective_mw2=squared_deviation,
        )
        pg_by_uid = {
            uid: float(solved_generator[row, PG])
            for row, uid in enumerate(layout.prepared.generator_uid_by_row)
        }
        solved_pg_by_hour_uid.append(pg_by_uid)
        hour_results.append(
            AcAwareHourResult(
                timestamp=layout.timestamp,
                solved_case=solved_case,
                reserve_up_mw_by_generator_uid={
                    uid: float(reserve[position])
                    for position, uid in enumerate(layout.reserve_uids)
                },
                audit=audit,
            )
        )

    normalized_objective = float(solution["f"])
    base_mva = layouts[0].base_mva
    if not math_isclose(
        normalized_objective,
        independent_objective / base_mva**2,
        absolute_tolerance=1.0e-8,
        relative_tolerance=1.0e-8,
    ):
        raise RuntimeError("AC-aware IPOPT objective reconstruction drifted")

    maximum_ramp_violation = 0.0
    maximum_reserve_bound_violation = 0.0
    maximum_reserve_headroom_violation = 0.0
    maximum_reserve_shortfall = 0.0
    for uid, unit in unit_by_uid.items():
        previous = unit.initial_generation_mw
        for hour, pg_by_uid in enumerate(solved_pg_by_hour_uid):
            current = pg_by_uid[uid]
            delta = current - previous
            lower = -step_ramp_mw[uid] - unit.p_max_mw * float(
                unit.shutdown_by_hour[hour]
            )
            upper = step_ramp_mw[uid] + unit.p_max_mw * float(
                unit.startup_by_hour[hour]
            )
            maximum_ramp_violation = max(
                maximum_ramp_violation, lower - delta, delta - upper, 0.0
            )
            previous = current
    for hour, (layout, hour_result) in enumerate(
        zip(layouts, hour_results, strict=True)
    ):
        row_by_uid = {
            uid: row for row, uid in enumerate(layout.prepared.generator_uid_by_row)
        }
        area_reserve: dict[int, float] = {}
        for uid, reserve in hour_result.reserve_up_mw_by_generator_uid.items():
            unit = unit_by_uid[uid]
            row = row_by_uid[uid]
            cap = 10.0 * unit.ramp_mw_per_minute * float(unit.commitment_by_hour[hour])
            headroom = (
                float(layout.generator[row, PMAX]) - solved_pg_by_hour_uid[hour][uid]
            )
            maximum_reserve_bound_violation = max(
                maximum_reserve_bound_violation, -reserve, reserve - cap, 0.0
            )
            maximum_reserve_headroom_violation = max(
                maximum_reserve_headroom_violation, reserve - headroom, 0.0
            )
            area_reserve[unit.area] = area_reserve.get(unit.area, 0.0) + reserve
        for area, requirement in chronology.spin_up_requirement_by_hour_area_mw[
            hour
        ].items():
            maximum_reserve_shortfall = max(
                maximum_reserve_shortfall,
                float(requirement) - area_reserve.get(area, 0.0),
                0.0,
            )

    solver_success = bool(stats.get("success", False))
    feasibility_witnessed = bool(
        solver_success
        and maximum_constraint_violation <= _NLP_CONSTRAINT_TOLERANCE
        and maximum_bound_violation <= _NLP_BOUND_TOLERANCE
        and maximum_ramp_violation <= _CHRONOLOGY_AUDIT_TOLERANCE_MW
        and maximum_reserve_bound_violation <= _CHRONOLOGY_AUDIT_TOLERANCE_MW
        and maximum_reserve_headroom_violation <= _CHRONOLOGY_AUDIT_TOLERANCE_MW
        and maximum_reserve_shortfall <= _CHRONOLOGY_AUDIT_TOLERANCE_MW
        and all(
            result.audit.postsolve_network_equation_reconstruction_audit_passed
            for result in hour_results
        )
    )
    return AcAwareCommitmentResult(
        evaluated=True,
        solver_success=solver_success,
        feasibility_witnessed=feasibility_witnessed,
        return_status=str(stats.get("return_status", "")),
        iterations=int(stats.get("iter_count", -1)),
        initial_strategy=initial_strategy,
        normalized_objective=normalized_objective,
        independent_squared_target_deviation_mw2=independent_objective,
        maximum_nlp_constraint_violation=maximum_constraint_violation,
        maximum_nlp_variable_bound_violation=maximum_bound_violation,
        maximum_ramp_violation_mw=maximum_ramp_violation,
        maximum_reserve_bound_violation_mw=maximum_reserve_bound_violation,
        maximum_reserve_headroom_violation_mw=(maximum_reserve_headroom_violation),
        maximum_reserve_shortfall_mw=maximum_reserve_shortfall,
        solver_input_cases_unchanged=all(
            _case_sha256(prepared.case) == prepared.recovery_case_sha256
            for prepared in cases
        ),
        hour_results=tuple(hour_results),
    )
