"""CasADi/IPOPT AC feasibility search for frozen recovery cases."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal

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
    BUS_I,
    BUS_TYPE,
    NONE,
    PD,
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

from src.grid.rts_gmlc_ac_recovery import AcRecoveryInput, _case_sha256
from src.grid.rts_gmlc_ac_step_control import (
    StepControlAudit,
    audit_step_control_solution,
)

IpoptInitialStrategy = Literal["source", "midpoint", "flat_target_midq"]
_INITIAL_STRATEGIES = frozenset({"source", "midpoint", "flat_target_midq"})
_FROZEN_IPOPT_OPTIONS = {
    "ipopt.print_level": 0,
    "print_time": False,
    "ipopt.max_iter": 1000,
    "ipopt.tol": 1.0e-9,
    "ipopt.constr_viol_tol": 1.0e-8,
    "ipopt.acceptable_tol": 1.0e-7,
    "ipopt.acceptable_constr_viol_tol": 1.0e-6,
    "ipopt.mu_strategy": "adaptive",
    "ipopt.fixed_variable_treatment": "make_constraint",
}


@dataclass(frozen=True)
class AcIpoptEnvelope:
    branch_rate_multiplier: float = 1.0
    reactive_power_bound_expansion_mvar: float = 0.0
    voltage_bound_expansion_pu: float = 0.0


@dataclass(frozen=True)
class AcIpoptResult:
    evaluated: bool
    solver_success: bool
    original_envelope_feasibility_witnessed: bool
    return_status: str
    iterations: int
    normalized_objective: float
    independent_squared_target_deviation_mw2: float
    maximum_nlp_constraint_violation: float
    maximum_nlp_variable_bound_violation: float
    initial_strategy: str
    branch_rate_multiplier: float
    reactive_power_bound_expansion_mvar: float
    voltage_bound_expansion_pu: float
    solver_input_case_unchanged: bool
    audit: StepControlAudit
    solved_case: dict[str, object]


def _integer_ids(values: np.ndarray, *, label: str) -> np.ndarray:
    numeric = np.asarray(values, dtype=float)
    integer = numeric.astype(np.int64)
    if not np.all(np.isfinite(numeric)) or not np.array_equal(numeric, integer):
        raise ValueError(f"IPOPT AC {label} identifiers must be finite integers")
    return integer


def _validate_envelope(envelope: AcIpoptEnvelope) -> None:
    if (
        not isfinite(envelope.branch_rate_multiplier)
        or envelope.branch_rate_multiplier < 1.0
        or not isfinite(envelope.reactive_power_bound_expansion_mvar)
        or envelope.reactive_power_bound_expansion_mvar < 0.0
        or not isfinite(envelope.voltage_bound_expansion_pu)
        or envelope.voltage_bound_expansion_pu < 0.0
    ):
        raise ValueError("IPOPT AC feasibility envelope is invalid")


def _constraint_violation(
    values: np.ndarray, lower: np.ndarray, upper: np.ndarray
) -> float:
    return float(np.max(np.maximum(np.maximum(lower - values, values - upper), 0.0)))


def _initial_point(
    strategy: IpoptInitialStrategy,
    *,
    bus: np.ndarray,
    generator: np.ndarray,
    adjustable_rows: np.ndarray,
    q_variable_rows: np.ndarray,
    lower_voltage: np.ndarray,
    upper_voltage: np.ndarray,
    lower_q: np.ndarray,
    upper_q: np.ndarray,
) -> np.ndarray:
    source_angle = np.deg2rad(bus[:, VA])
    target_pg = np.clip(
        generator[adjustable_rows, PG],
        generator[adjustable_rows, PMIN],
        generator[adjustable_rows, PMAX],
    )
    source_q = np.clip(generator[q_variable_rows, QG], lower_q, upper_q)
    if strategy == "source":
        angle = source_angle
        voltage = np.clip(bus[:, VM], lower_voltage, upper_voltage)
        pg = target_pg
        qg = source_q
    elif strategy == "midpoint":
        angle = source_angle
        voltage = 0.5 * (lower_voltage + upper_voltage)
        pg = 0.5 * (generator[adjustable_rows, PMIN] + generator[adjustable_rows, PMAX])
        qg = 0.5 * (lower_q + upper_q)
    elif strategy == "flat_target_midq":
        angle = np.zeros(len(bus))
        reference_rows = np.flatnonzero(bus[:, BUS_TYPE] == REF)
        angle[reference_rows] = source_angle[reference_rows]
        voltage = np.clip(np.ones(len(bus)), lower_voltage, upper_voltage)
        pg = target_pg
        qg = 0.5 * (lower_q + upper_q)
    else:
        raise ValueError(f"Unknown IPOPT AC initial strategy {strategy}")
    return np.concatenate((angle, voltage, pg, qg))


def solve_ac_feasibility_ipopt(
    prepared: AcRecoveryInput,
    *,
    initial_strategy: IpoptInitialStrategy = "source",
    envelope: AcIpoptEnvelope = AcIpoptEnvelope(),
    solver_options: dict[str, object] | None = None,
) -> AcIpoptResult:
    """Solve one AC feasibility NLP and audit the returned point."""

    if initial_strategy not in _INITIAL_STRATEGIES:
        raise ValueError(f"Unknown IPOPT AC initial strategy {initial_strategy}")
    _validate_envelope(envelope)
    options = dict(_FROZEN_IPOPT_OPTIONS if solver_options is None else solver_options)
    if options != _FROZEN_IPOPT_OPTIONS:
        raise ValueError("IPOPT AC solver options drifted from the frozen protocol")
    input_hash = _case_sha256(prepared.case)
    if input_hash != prepared.recovery_case_sha256:
        raise ValueError("IPOPT AC prepared case changed before solve")

    bus = np.asarray(prepared.case["bus"], dtype=float)
    generator = np.asarray(prepared.case["gen"], dtype=float)
    branch = np.asarray(prepared.case["branch"], dtype=float)
    base_mva = float(prepared.case["baseMVA"])
    if (
        bus.ndim != 2
        or generator.ndim != 2
        or branch.ndim != 2
        or np.any(bus[:, BUS_TYPE] == NONE)
    ):
        raise ValueError("IPOPT AC prepared case dimensions or bus types drifted")
    bus_ids = _integer_ids(bus[:, BUS_I], label="bus")
    if len(set(bus_ids.tolist())) != len(bus_ids):
        raise ValueError("IPOPT AC prepared case has duplicate bus IDs")
    row_by_bus = {int(bus_id): row for row, bus_id in enumerate(bus_ids)}
    generator_bus_ids = _integer_ids(generator[:, GEN_BUS], label="generator bus")
    from_bus_ids = _integer_ids(branch[:, F_BUS], label="branch from-bus")
    to_bus_ids = _integer_ids(branch[:, T_BUS], label="branch to-bus")
    if any(
        int(bus_id) not in row_by_bus
        for bus_id in np.concatenate((generator_bus_ids, from_bus_ids, to_bus_ids))
    ):
        raise ValueError("IPOPT AC prepared case contains an unknown element bus")
    if not np.all(np.isin(generator[:, GEN_STATUS], (0.0, 1.0))) or not np.all(
        np.isin(branch[:, BR_STATUS], (0.0, 1.0))
    ):
        raise ValueError("IPOPT AC prepared case status is not binary")

    bus_count = len(bus)
    generator_count = len(generator)
    branch_count = len(branch)
    from_rows = np.asarray([row_by_bus[int(value)] for value in from_bus_ids])
    to_rows = np.asarray([row_by_bus[int(value)] for value in to_bus_ids])
    internal_bus = np.array(bus, copy=True)
    internal_branch = np.array(branch, copy=True)
    internal_bus[:, BUS_I] = np.arange(bus_count)
    internal_branch[:, F_BUS] = from_rows
    internal_branch[:, T_BUS] = to_rows
    ybus, yf, yt = makeYbus(base_mva, internal_bus, internal_branch)
    ybus = ybus.toarray()
    yf = yf.toarray()
    yt = yt.toarray()

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

    voltage_lower = bus[:, VMIN] - envelope.voltage_bound_expansion_pu
    voltage_upper = bus[:, VMAX] + envelope.voltage_bound_expansion_pu
    q_lower = (
        generator[q_variable_rows, QMIN] - envelope.reactive_power_bound_expansion_mvar
    )
    q_upper = (
        generator[q_variable_rows, QMAX] + envelope.reactive_power_bound_expansion_mvar
    )
    if np.any(voltage_lower <= 0.0) or np.any(voltage_lower >= voltage_upper):
        raise ValueError("IPOPT AC relaxed voltage bounds are invalid")

    angle = ca.MX.sym("angle", bus_count)
    voltage_magnitude = ca.MX.sym("voltage_magnitude", bus_count)
    pg = ca.MX.sym("pg", len(adjustable_rows))
    qg = ca.MX.sym("qg", len(q_variable_rows))
    variables = ca.vertcat(angle, voltage_magnitude, pg, qg)
    voltage_real = ca.times(voltage_magnitude, ca.cos(angle))
    voltage_imag = ca.times(voltage_magnitude, ca.sin(angle))
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

    constraints = [specified_p - network_p, specified_q - network_q]
    lower_constraints = [0.0] * (2 * bus_count)
    upper_constraints = [0.0] * (2 * bus_count)
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
    online_branch_rows = np.flatnonzero(active_branch)
    rate_limits = envelope.branch_rate_multiplier * branch[online_branch_rows, RATE_A]
    constraints.extend(
        (
            ca.power(branch_pf[online_branch_rows], 2)
            + ca.power(branch_qf[online_branch_rows], 2),
            ca.power(branch_pt[online_branch_rows], 2)
            + ca.power(branch_qt[online_branch_rows], 2),
        )
    )
    lower_constraints.extend([-ca.inf] * (2 * len(online_branch_rows)))
    upper_constraints.extend(list(rate_limits**2) + list(rate_limits**2))
    for row in online_branch_rows:
        if branch[row, ANGMIN] != 0.0 and branch[row, ANGMIN] > -360.0:
            constraints.append(angle[from_rows[row]] - angle[to_rows[row]])
            lower_constraints.append(np.deg2rad(branch[row, ANGMIN]))
            upper_constraints.append(ca.inf)
        if branch[row, ANGMAX] != 0.0 and branch[row, ANGMAX] < 360.0:
            constraints.append(angle[from_rows[row]] - angle[to_rows[row]])
            lower_constraints.append(-ca.inf)
            upper_constraints.append(np.deg2rad(branch[row, ANGMAX]))

    targets = np.asarray(prepared.target_generation_mw_by_row, dtype=float)
    normalized_objective = ca.sumsqr((pg - ca.DM(targets[adjustable_rows])) / base_mva)
    problem = {
        "x": variables,
        "f": normalized_objective,
        "g": ca.vertcat(*constraints),
    }
    solver = ca.nlpsol("ac_feasibility", "ipopt", problem, options)

    variable_lower = np.concatenate(
        (
            np.full(bus_count, -np.inf),
            voltage_lower,
            generator[adjustable_rows, PMIN],
            q_lower,
        )
    )
    variable_upper = np.concatenate(
        (
            np.full(bus_count, np.inf),
            voltage_upper,
            generator[adjustable_rows, PMAX],
            q_upper,
        )
    )
    source_angle = np.deg2rad(bus[:, VA])
    reference_rows = np.flatnonzero(bus[:, BUS_TYPE] == REF)
    if len(reference_rows) == 0:
        raise ValueError("IPOPT AC prepared case has no reference bus")
    variable_lower[reference_rows] = source_angle[reference_rows]
    variable_upper[reference_rows] = source_angle[reference_rows]
    initial = _initial_point(
        initial_strategy,
        bus=bus,
        generator=generator,
        adjustable_rows=adjustable_rows,
        q_variable_rows=q_variable_rows,
        lower_voltage=voltage_lower,
        upper_voltage=voltage_upper,
        lower_q=q_lower,
        upper_q=q_upper,
    )
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
        raise RuntimeError("IPOPT AC solver returned non-finite values")
    maximum_constraint_violation = _constraint_violation(
        constraint_values, lower_constraints_array, upper_constraints_array
    )
    maximum_bound_violation = _constraint_violation(
        point, variable_lower, variable_upper
    )

    angle_value = point[:bus_count]
    voltage_value = point[bus_count : 2 * bus_count]
    pg_start = 2 * bus_count
    pg_value = point[pg_start : pg_start + len(adjustable_rows)]
    qg_value = point[pg_start + len(adjustable_rows) :]
    complex_voltage = voltage_value * np.exp(1j * angle_value)
    from_flow = base_mva * complex_voltage[from_rows] * np.conj(yf @ complex_voltage)
    to_flow = base_mva * complex_voltage[to_rows] * np.conj(yt @ complex_voltage)
    solved_bus = np.array(bus, copy=True)
    solved_generator = np.array(generator, copy=True)
    solved_branch = np.zeros((branch_count, max(branch.shape[1], QT + 1)))
    solved_branch[:, : branch.shape[1]] = branch
    solved_bus[:, VM] = voltage_value
    solved_bus[:, VA] = np.rad2deg(angle_value)
    solved_generator[adjustable_rows, PG] = pg_value
    solved_generator[q_variable_rows, QG] = qg_value
    for row in np.flatnonzero(active_generator):
        solved_generator[row, VG] = voltage_value[
            row_by_bus[int(generator_bus_ids[row])]
        ]
    solved_branch[:, PF] = from_flow.real
    solved_branch[:, QF] = from_flow.imag
    solved_branch[:, PT] = to_flow.real
    solved_branch[:, QT] = to_flow.imag
    solved_case = {
        "version": prepared.case["version"],
        "baseMVA": base_mva,
        "bus": solved_bus,
        "gen": solved_generator,
        "branch": solved_branch,
        "gencost": np.array(prepared.case["gencost"], copy=True),
    }
    squared_deviation = float(np.sum((solved_generator[:, PG] - targets) ** 2))
    audit = audit_step_control_solution(
        prepared,
        solved_case,
        solver_objective_mw2=squared_deviation,
    )
    normalized_value = float(solution["f"])
    if not math_isclose(
        normalized_value,
        squared_deviation / base_mva**2,
        absolute_tolerance=1.0e-8,
        relative_tolerance=1.0e-8,
    ):
        raise RuntimeError("IPOPT AC objective reconstruction drifted")
    solver_success = bool(stats.get("success", False))
    original_witness = bool(
        solver_success
        and envelope == AcIpoptEnvelope()
        and maximum_constraint_violation <= 1.0e-6
        and maximum_bound_violation <= 1.0e-8
        and audit.postsolve_network_equation_reconstruction_audit_passed
    )
    return AcIpoptResult(
        evaluated=True,
        solver_success=solver_success,
        original_envelope_feasibility_witnessed=original_witness,
        return_status=str(stats.get("return_status", "")),
        iterations=int(stats.get("iter_count", -1)),
        normalized_objective=normalized_value,
        independent_squared_target_deviation_mw2=squared_deviation,
        maximum_nlp_constraint_violation=maximum_constraint_violation,
        maximum_nlp_variable_bound_violation=maximum_bound_violation,
        initial_strategy=initial_strategy,
        branch_rate_multiplier=envelope.branch_rate_multiplier,
        reactive_power_bound_expansion_mvar=(
            envelope.reactive_power_bound_expansion_mvar
        ),
        voltage_bound_expansion_pu=envelope.voltage_bound_expansion_pu,
        solver_input_case_unchanged=(
            _case_sha256(prepared.case) == prepared.recovery_case_sha256
        ),
        audit=audit,
        solved_case=solved_case,
    )


def math_isclose(
    left: float,
    right: float,
    *,
    absolute_tolerance: float,
    relative_tolerance: float,
) -> bool:
    return abs(left - right) <= absolute_tolerance + relative_tolerance * max(
        1.0, abs(left), abs(right)
    )
