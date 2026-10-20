"""Step-controlled AC-OPF feasibility witness with algebraic post-solve audits."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite, sqrt
from typing import Mapping, Sequence

import numpy as np
from pypower.api import ppoption, runopf
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
    SHIFT,
    TAP,
    T_BUS,
)
from pypower.idx_bus import (
    BS,
    BUS_I,
    BUS_TYPE,
    GS,
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

_FROZEN_SOLVER_OPTIONS = {
    "PF_DC": False,
    "OPF_ALG": 565,
    "OPF_FLOW_LIM": 0,
    "OPF_IGNORE_ANG_LIM": False,
    "OPF_VIOLATION": 1.0e-8,
    "PDIPM_FEASTOL": 1.0e-8,
    "PDIPM_GRADTOL": 1.0e-6,
    "PDIPM_COMPTOL": 1.0e-6,
    "PDIPM_COSTTOL": 1.0e-6,
    "PDIPM_MAX_IT": 150,
    "SCPDIPM_RED_IT": 20,
}

_FROZEN_AUDIT_TOLERANCES = {
    "active_power_bound_tolerance_mw": 1.0e-4,
    "reactive_power_bound_tolerance_mvar": 1.0e-4,
    "voltage_bound_tolerance_pu": 1.0e-6,
    "branch_loading_tolerance_fraction": 1.0e-6,
    "branch_angle_tolerance_degree": 1.0e-6,
    "fixed_generator_pg_tolerance_mw": 1.0e-6,
    "offline_pg_qg_tolerance_mw_mvar": 1.0e-6,
    "offline_branch_flow_tolerance_mva": 1.0e-6,
    "nodal_p_q_balance_tolerance_mw_mvar": 1.0e-4,
    "ybus_terminal_shunt_identity_tolerance_mva": 1.0e-6,
    "returned_recomputed_branch_flow_tolerance_mva": 1.0e-6,
    "reference_angle_tolerance_degree": 1.0e-6,
    "objective_absolute_tolerance_mw2": 1.0e-4,
    "objective_relative_tolerance": 1.0e-8,
}

_CASE_KEYS = frozenset({"version", "baseMVA", "bus", "gen", "branch", "gencost"})


@dataclass(frozen=True)
class StepControlGeneratorRecord:
    generator_row: int
    generator_uid: str
    bus: int
    online: bool
    adjustable_active_power: bool
    target_pg_mw: float
    pg_mw: float
    pg_deviation_mw: float
    pmin_mw: float
    pmax_mw: float
    qg_mvar: float
    qmin_mvar: float
    qmax_mvar: float
    source_vg_pu: float
    output_vg_pu: float
    optimized_bus_vm_pu: float


@dataclass(frozen=True)
class StepControlBusRecord:
    bus_row: int
    bus: int
    bus_type: int
    pd_mw: float
    qd_mvar: float
    gs_mw_at_1pu: float
    bs_mvar_at_1pu: float
    vm_pu: float
    va_degree: float
    specified_p_injection_mw: float
    specified_q_injection_mvar: float
    reconstructed_p_injection_mw: float
    reconstructed_q_injection_mvar: float
    p_balance_residual_mw: float
    q_balance_residual_mvar: float


@dataclass(frozen=True)
class StepControlBranchRecord:
    branch_row: int
    branch_uid: str
    from_bus: int
    to_bus: int
    online: bool
    rate_a_mva: float
    tap_ratio_source_value: float
    phase_shift_degree: float
    angle_difference_degree: float
    angle_lower_violation_degree: float
    angle_upper_violation_degree: float
    returned_pf_mw: float
    returned_qf_mvar: float
    returned_pt_mw: float
    returned_qt_mvar: float
    reconstructed_pf_mw: float
    reconstructed_qf_mvar: float
    reconstructed_pt_mw: float
    reconstructed_qt_mvar: float
    from_mva: float
    to_mva: float
    loading_fraction: float
    returned_reconstructed_from_mismatch_mva: float
    returned_reconstructed_to_mismatch_mva: float


@dataclass(frozen=True)
class StepControlAudit:
    postsolve_network_equation_reconstruction_audit_passed: bool
    solver_result_fixed_fields_preserved: bool
    solver_result_fixed_case_sha256: str
    external_bus_mapping_sha256: str
    active_bus_count: int
    isolated_bus_count: int
    connected_component_count: int
    reference_bus_count: int
    reference_structure_valid: bool
    online_branch_count: int
    offline_branch_count: int
    nonunity_tap_count: int
    nonzero_shift_count: int
    nonzero_gs_count: int
    nonzero_bs_count: int
    solver_objective_mw2: float
    reconstructed_objective_mw2: float
    objective_mismatch_mw2: float
    l1_target_deviation_mw: float
    l2_target_deviation_mw: float
    max_target_deviation_mw: float
    total_up_redispatch_mw: float
    total_down_redispatch_mw: float
    total_generation_mw: float
    total_active_demand_mw: float
    total_generation_minus_demand_mw: float
    max_active_power_bound_violation_mw: float
    max_reactive_power_bound_violation_mvar: float
    max_offline_pg_mw: float
    max_offline_qg_mvar: float
    max_offline_branch_flow_mva: float
    max_voltage_violation_pu: float
    max_branch_loading_fraction: float
    max_branch_loading_violation_fraction: float
    max_branch_angle_violation_degree: float
    max_fixed_pg_deviation_mw: float
    max_p_balance_residual_mw: float
    max_q_balance_residual_mvar: float
    max_ybus_terminal_shunt_identity_mismatch_mva: float
    max_returned_recomputed_branch_flow_mismatch_mva: float
    max_reference_angle_drift_degree: float
    max_source_vg_to_optimized_vm_adjustment_pu: float
    max_output_vg_bus_vm_mismatch_pu: float
    generator_records: tuple[StepControlGeneratorRecord, ...]
    bus_records: tuple[StepControlBusRecord, ...]
    branch_records: tuple[StepControlBranchRecord, ...]


@dataclass(frozen=True)
class StepControlSolveResult:
    evaluated: bool
    solver_success: bool
    feasibility_witnessed: bool
    status: str
    solver_error_type: str | None
    solver_error_message: str | None
    solver_algorithm: int
    solver_reported_algorithm: int | None
    solver_elapsed_seconds: float | None
    solver_iterations: int | None
    solver_message: str | None
    solver_final_feasibility_condition: float | None
    solver_final_gradient_condition: float | None
    solver_final_complementarity_condition: float | None
    solver_final_cost_condition: float | None
    solver_input_case_unchanged: bool
    recovery_input_fixed_fields_preserved: bool
    audit: StepControlAudit | None


def _equal_except_columns(
    left: np.ndarray, right: np.ndarray, excluded_columns: Sequence[int]
) -> bool:
    if left.shape != right.shape:
        return False
    retained = [
        column for column in range(left.shape[1]) if column not in excluded_columns
    ]
    return np.array_equal(left[:, retained], right[:, retained])


def _integer_values(values: np.ndarray, *, label: str) -> np.ndarray:
    numeric = np.asarray(values, dtype=float)
    integer = numeric.astype(np.int64)
    if not np.all(np.isfinite(numeric)) or not np.array_equal(numeric, integer):
        raise RuntimeError(f"Step-control {label} identifiers are not finite integers")
    return integer


def _mapping_sha256(bus_ids: np.ndarray) -> str:
    digest = sha256()
    digest.update(b"external_bus_id_to_compact_row_v1")
    digest.update(np.ascontiguousarray(bus_ids, dtype=np.int64).tobytes())
    digest.update(
        np.ascontiguousarray(np.arange(len(bus_ids)), dtype=np.int64).tobytes()
    )
    return digest.hexdigest()


def _topology_components(
    bus_count: int, from_rows: np.ndarray, to_rows: np.ndarray, online: np.ndarray
) -> tuple[tuple[int, ...], ...]:
    adjacency = [set() for _ in range(bus_count)]
    for branch_row in np.flatnonzero(online):
        left = int(from_rows[branch_row])
        right = int(to_rows[branch_row])
        adjacency[left].add(right)
        adjacency[right].add(left)
    unseen = set(range(bus_count))
    components = []
    while unseen:
        root = min(unseen)
        stack = [root]
        component = []
        unseen.remove(root)
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in sorted(adjacency[current], reverse=True):
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
        components.append(tuple(sorted(component)))
    return tuple(components)


def _normalized_fixed_case_hash(
    prepared: AcRecoveryInput,
    bus: np.ndarray,
    generator: np.ndarray,
    branch: np.ndarray,
    gencost: np.ndarray,
) -> str:
    source_bus = np.asarray(prepared.case["bus"])
    source_generator = np.asarray(prepared.case["gen"])
    source_branch = np.asarray(prepared.case["branch"])
    normalized_bus = np.array(bus[:, : source_bus.shape[1]], copy=True)
    normalized_generator = np.array(
        generator[:, : source_generator.shape[1]], copy=True
    )
    normalized_branch = np.array(branch[:, : source_branch.shape[1]], copy=True)
    normalized_bus[:, (VM, VA)] = source_bus[:, (VM, VA)]
    normalized_generator[:, (PG, QG, VG)] = source_generator[:, (PG, QG, VG)]
    for column in (PF, QF, PT, QT):
        if column < normalized_branch.shape[1]:
            normalized_branch[:, column] = source_branch[:, column]
    normalized = {
        "version": prepared.case["version"],
        "baseMVA": float(prepared.case["baseMVA"]),
        "bus": normalized_bus,
        "gen": normalized_generator,
        "branch": normalized_branch,
        "gencost": np.array(gencost, copy=True),
    }
    return _case_sha256(normalized)


def audit_step_control_solution(
    prepared: AcRecoveryInput,
    solved: Mapping[str, object],
    *,
    solver_objective_mw2: float,
    audit_tolerances: Mapping[str, float] | None = None,
) -> StepControlAudit:
    """Rebuild AC equations and flows from frozen inputs plus returned state."""

    tolerances = dict(
        _FROZEN_AUDIT_TOLERANCES if audit_tolerances is None else audit_tolerances
    )
    if tolerances != _FROZEN_AUDIT_TOLERANCES:
        raise ValueError("Step-control audit tolerances drifted from frozen protocol")
    if set(prepared.case) != _CASE_KEYS:
        raise ValueError("Step-control prepared case schema drifted")
    if _case_sha256(prepared.case) != prepared.recovery_case_sha256:
        raise ValueError("Step-control prepared case changed before audit")

    try:
        bus = np.asarray(solved["bus"], dtype=float)
        generator = np.asarray(solved["gen"], dtype=float)
        branch = np.asarray(solved["branch"], dtype=float)
        gencost = np.asarray(solved["gencost"], dtype=float)
        solver_objective = float(solver_objective_mw2)
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("Step-control solver result structure drifted") from error
    source_bus = np.asarray(prepared.case["bus"], dtype=float)
    source_generator = np.asarray(prepared.case["gen"], dtype=float)
    source_branch = np.asarray(prepared.case["branch"], dtype=float)
    source_gencost = np.asarray(prepared.case["gencost"], dtype=float)
    if (
        bus.ndim != 2
        or generator.ndim != 2
        or branch.ndim != 2
        or gencost.ndim != 2
        or bus.shape[0] != source_bus.shape[0]
        or bus.shape[1] < source_bus.shape[1]
        or generator.shape[0] != source_generator.shape[0]
        or generator.shape[1] < source_generator.shape[1]
        or branch.shape[0] != source_branch.shape[0]
        or branch.shape[1] <= QT
        or gencost.shape != source_gencost.shape
    ):
        raise RuntimeError("Step-control solver result dimensions drifted")
    if not (
        np.all(np.isfinite(bus))
        and np.all(np.isfinite(generator))
        and np.all(np.isfinite(branch))
        and np.all(np.isfinite(gencost))
        and isfinite(solver_objective)
    ):
        raise RuntimeError("Step-control solver result contains non-finite values")

    bus_ids = _integer_values(source_bus[:, BUS_I], label="bus")
    if len(set(bus_ids.tolist())) != len(bus_ids):
        raise RuntimeError("Step-control prepared case contains duplicate bus IDs")
    if not np.array_equal(bus[:, BUS_I], source_bus[:, BUS_I]):
        raise RuntimeError("Step-control solver changed bus row identity")
    if np.any(source_bus[:, BUS_TYPE] == NONE):
        raise RuntimeError("Step-control protocol does not admit BUS_TYPE=NONE")
    row_by_bus = {int(bus_id): row for row, bus_id in enumerate(bus_ids)}
    generator_bus_ids = _integer_values(
        source_generator[:, GEN_BUS], label="generator bus"
    )
    from_bus_ids = _integer_values(source_branch[:, F_BUS], label="branch from-bus")
    to_bus_ids = _integer_values(source_branch[:, T_BUS], label="branch to-bus")
    if any(int(bus_id) not in row_by_bus for bus_id in generator_bus_ids):
        raise RuntimeError("Step-control generator references an unknown bus")
    if any(
        int(bus_id) not in row_by_bus
        for bus_id in np.concatenate((from_bus_ids, to_bus_ids))
    ):
        raise RuntimeError("Step-control branch references an unknown bus")
    if not np.all(np.isin(source_generator[:, GEN_STATUS], (0.0, 1.0))):
        raise RuntimeError("Step-control generator status is not binary")
    if not np.all(np.isin(source_branch[:, BR_STATUS], (0.0, 1.0))):
        raise RuntimeError("Step-control branch status is not binary")

    fixed_fields_preserved = (
        _equal_except_columns(bus[:, : source_bus.shape[1]], source_bus, (VM, VA))
        and _equal_except_columns(
            generator[:, : source_generator.shape[1]],
            source_generator,
            (PG, QG, VG),
        )
        and np.array_equal(branch[:, : source_branch.shape[1]], source_branch)
        and np.array_equal(gencost, source_gencost)
    )
    fixed_case_hash = _normalized_fixed_case_hash(
        prepared, bus, generator, branch, gencost
    )

    from_rows = np.asarray([row_by_bus[int(bus_id)] for bus_id in from_bus_ids])
    to_rows = np.asarray([row_by_bus[int(bus_id)] for bus_id in to_bus_ids])
    internal_bus = np.array(source_bus, copy=True)
    internal_branch = np.array(source_branch, copy=True)
    internal_bus[:, BUS_I] = np.arange(len(internal_bus))
    internal_branch[:, F_BUS] = from_rows
    internal_branch[:, T_BUS] = to_rows
    base_mva = float(prepared.case["baseMVA"])
    ybus, yf, yt = makeYbus(base_mva, internal_bus, internal_branch)
    voltage = bus[:, VM] * np.exp(1j * np.deg2rad(bus[:, VA]))
    network_injection = base_mva * voltage * np.conj(ybus @ voltage)
    from_flow = base_mva * voltage[from_rows] * np.conj(yf @ voltage)
    to_flow = base_mva * voltage[to_rows] * np.conj(yt @ voltage)

    active_generator = generator[:, GEN_STATUS] > 0.0
    active_branch = source_branch[:, BR_STATUS] > 0.0
    specified_injection = -(bus[:, PD] + 1j * bus[:, QD])
    for row in np.flatnonzero(active_generator):
        bus_row = row_by_bus[int(generator_bus_ids[row])]
        specified_injection[bus_row] += generator[row, PG] + 1j * generator[row, QG]
    balance_residual = specified_injection - network_injection

    terminal_injection = np.zeros(len(bus), dtype=complex)
    for row in range(len(branch)):
        terminal_injection[from_rows[row]] += from_flow[row]
        terminal_injection[to_rows[row]] += to_flow[row]
    shunt_injection = (bus[:, GS] - 1j * bus[:, BS]) * bus[:, VM] ** 2
    ybus_identity_mismatch = network_injection - (terminal_injection + shunt_injection)

    targets = np.asarray(prepared.target_generation_mw_by_row, dtype=float)
    deviations = generator[:, PG] - targets
    p_violation = np.maximum(
        np.maximum(
            generator[:, PG] - source_generator[:, PMAX],
            source_generator[:, PMIN] - generator[:, PG],
        ),
        0.0,
    )
    q_violation = np.maximum(
        np.maximum(
            generator[:, QG] - source_generator[:, QMAX],
            source_generator[:, QMIN] - generator[:, QG],
        ),
        0.0,
    )
    voltage_violation = np.maximum(
        np.maximum(bus[:, VM] - source_bus[:, VMAX], source_bus[:, VMIN] - bus[:, VM]),
        0.0,
    )
    offline_generator = ~active_generator
    max_offline_pg = (
        float(np.max(np.abs(generator[offline_generator, PG])))
        if np.any(offline_generator)
        else 0.0
    )
    max_offline_qg = (
        float(np.max(np.abs(generator[offline_generator, QG])))
        if np.any(offline_generator)
        else 0.0
    )

    returned_from = branch[:, PF] + 1j * branch[:, QF]
    returned_to = branch[:, PT] + 1j * branch[:, QT]
    returned_from_mismatch = np.abs(returned_from - from_flow)
    returned_to_mismatch = np.abs(returned_to - to_flow)
    from_mva = np.abs(from_flow)
    to_mva = np.abs(to_flow)
    terminal_mva = np.maximum(from_mva, to_mva)
    loading = np.zeros(len(branch), dtype=float)
    for row in np.flatnonzero(active_branch):
        rating = float(source_branch[row, RATE_A])
        if rating <= 0.0:
            raise RuntimeError("Step-control active branch has nonpositive RATE_A")
        loading[row] = terminal_mva[row] / rating

    angle_difference = bus[from_rows, VA] - bus[to_rows, VA]
    lower_used = (
        (source_branch[:, ANGMIN] != 0.0)
        & (source_branch[:, ANGMIN] > -360.0)
        & active_branch
    )
    upper_used = (
        (source_branch[:, ANGMAX] != 0.0)
        & (source_branch[:, ANGMAX] < 360.0)
        & active_branch
    )
    lower_angle_violation = np.where(
        lower_used,
        np.maximum(source_branch[:, ANGMIN] - angle_difference, 0.0),
        0.0,
    )
    upper_angle_violation = np.where(
        upper_used,
        np.maximum(angle_difference - source_branch[:, ANGMAX], 0.0),
        0.0,
    )

    fixed_rows = np.asarray(prepared.fixed_generator_rows, dtype=int)
    max_fixed_pg_deviation = (
        float(np.max(np.abs(deviations[fixed_rows]))) if len(fixed_rows) else 0.0
    )
    reconstructed_objective = float(np.sum(deviations**2))
    objective_mismatch = abs(solver_objective - reconstructed_objective)
    bus_vm_by_id = {
        int(bus_id): float(bus[row, VM]) for row, bus_id in enumerate(bus_ids)
    }
    source_controller_adjustments = [
        abs(bus_vm_by_id[int(bus_id)] - float(source_vg))
        for bus_id, source_vg in prepared.source_controller_vg_by_bus
    ]
    output_vg_vm_mismatch = [
        abs(float(generator[row, VG]) - bus_vm_by_id[int(generator_bus_ids[row])])
        for row in np.flatnonzero(active_generator)
    ]

    components = _topology_components(len(bus), from_rows, to_rows, active_branch)
    reference_rows = set(np.flatnonzero(source_bus[:, BUS_TYPE] == REF).tolist())
    reference_counts = [
        len(reference_rows.intersection(component)) for component in components
    ]
    reference_structure_valid = all(count == 1 for count in reference_counts)
    isolated_bus_count = sum(len(component) == 1 for component in components)
    reference_angle_drift = [
        abs(float(bus[row, VA]) - float(source_bus[row, VA])) for row in reference_rows
    ]

    adjustable_set = set(prepared.adjustable_generator_rows)
    generator_records = tuple(
        StepControlGeneratorRecord(
            generator_row=row,
            generator_uid=uid,
            bus=int(generator_bus_ids[row]),
            online=bool(active_generator[row]),
            adjustable_active_power=row in adjustable_set,
            target_pg_mw=float(targets[row]),
            pg_mw=float(generator[row, PG]),
            pg_deviation_mw=float(deviations[row]),
            pmin_mw=float(source_generator[row, PMIN]),
            pmax_mw=float(source_generator[row, PMAX]),
            qg_mvar=float(generator[row, QG]),
            qmin_mvar=float(source_generator[row, QMIN]),
            qmax_mvar=float(source_generator[row, QMAX]),
            source_vg_pu=float(source_generator[row, VG]),
            output_vg_pu=float(generator[row, VG]),
            optimized_bus_vm_pu=bus_vm_by_id[int(generator_bus_ids[row])],
        )
        for row, uid in enumerate(prepared.generator_uid_by_row)
    )
    bus_records = tuple(
        StepControlBusRecord(
            bus_row=row,
            bus=int(bus_ids[row]),
            bus_type=int(source_bus[row, BUS_TYPE]),
            pd_mw=float(source_bus[row, PD]),
            qd_mvar=float(source_bus[row, QD]),
            gs_mw_at_1pu=float(source_bus[row, GS]),
            bs_mvar_at_1pu=float(source_bus[row, BS]),
            vm_pu=float(bus[row, VM]),
            va_degree=float(bus[row, VA]),
            specified_p_injection_mw=float(specified_injection[row].real),
            specified_q_injection_mvar=float(specified_injection[row].imag),
            reconstructed_p_injection_mw=float(network_injection[row].real),
            reconstructed_q_injection_mvar=float(network_injection[row].imag),
            p_balance_residual_mw=float(balance_residual[row].real),
            q_balance_residual_mvar=float(balance_residual[row].imag),
        )
        for row in range(len(bus))
    )
    branch_records = tuple(
        StepControlBranchRecord(
            branch_row=row,
            branch_uid=uid,
            from_bus=int(from_bus_ids[row]),
            to_bus=int(to_bus_ids[row]),
            online=bool(active_branch[row]),
            rate_a_mva=float(source_branch[row, RATE_A]),
            tap_ratio_source_value=float(source_branch[row, TAP]),
            phase_shift_degree=float(source_branch[row, SHIFT]),
            angle_difference_degree=float(angle_difference[row]),
            angle_lower_violation_degree=float(lower_angle_violation[row]),
            angle_upper_violation_degree=float(upper_angle_violation[row]),
            returned_pf_mw=float(branch[row, PF]),
            returned_qf_mvar=float(branch[row, QF]),
            returned_pt_mw=float(branch[row, PT]),
            returned_qt_mvar=float(branch[row, QT]),
            reconstructed_pf_mw=float(from_flow[row].real),
            reconstructed_qf_mvar=float(from_flow[row].imag),
            reconstructed_pt_mw=float(to_flow[row].real),
            reconstructed_qt_mvar=float(to_flow[row].imag),
            from_mva=float(from_mva[row]),
            to_mva=float(to_mva[row]),
            loading_fraction=float(loading[row]),
            returned_reconstructed_from_mismatch_mva=float(returned_from_mismatch[row]),
            returned_reconstructed_to_mismatch_mva=float(returned_to_mismatch[row]),
        )
        for row, uid in enumerate(prepared.branch_uid_by_row)
    )

    max_loading = float(np.max(loading)) if len(loading) else 0.0
    max_angle_violation = (
        float(max(np.max(lower_angle_violation), np.max(upper_angle_violation)))
        if len(branch)
        else 0.0
    )
    max_flow_mismatch = (
        float(max(np.max(returned_from_mismatch), np.max(returned_to_mismatch)))
        if len(branch)
        else 0.0
    )
    objective_limit = tolerances["objective_absolute_tolerance_mw2"] + tolerances[
        "objective_relative_tolerance"
    ] * max(1.0, reconstructed_objective)
    max_p_residual = float(np.max(np.abs(balance_residual.real)))
    max_q_residual = float(np.max(np.abs(balance_residual.imag)))
    max_ybus_identity = float(np.max(np.abs(ybus_identity_mismatch)))
    max_reference_drift = max(reference_angle_drift, default=0.0)
    passed = (
        prepared.fixed_inputs_preserved
        and fixed_fields_preserved
        and fixed_case_hash == prepared.recovery_case_sha256
        and reference_structure_valid
        and float(np.max(p_violation)) <= tolerances["active_power_bound_tolerance_mw"]
        and float(np.max(q_violation))
        <= tolerances["reactive_power_bound_tolerance_mvar"]
        and max_offline_pg <= tolerances["offline_pg_qg_tolerance_mw_mvar"]
        and max_offline_qg <= tolerances["offline_pg_qg_tolerance_mw_mvar"]
        and (
            float(np.max(terminal_mva[~active_branch]))
            if np.any(~active_branch)
            else 0.0
        )
        <= tolerances["offline_branch_flow_tolerance_mva"]
        and float(np.max(voltage_violation)) <= tolerances["voltage_bound_tolerance_pu"]
        and max_loading <= 1.0 + tolerances["branch_loading_tolerance_fraction"]
        and max_angle_violation <= tolerances["branch_angle_tolerance_degree"]
        and max_fixed_pg_deviation <= tolerances["fixed_generator_pg_tolerance_mw"]
        and max_p_residual <= tolerances["nodal_p_q_balance_tolerance_mw_mvar"]
        and max_q_residual <= tolerances["nodal_p_q_balance_tolerance_mw_mvar"]
        and max_ybus_identity
        <= tolerances["ybus_terminal_shunt_identity_tolerance_mva"]
        and max_flow_mismatch
        <= tolerances["returned_recomputed_branch_flow_tolerance_mva"]
        and max_reference_drift <= tolerances["reference_angle_tolerance_degree"]
        and max(output_vg_vm_mismatch, default=0.0)
        <= tolerances["voltage_bound_tolerance_pu"]
        and objective_mismatch <= objective_limit
    )
    return StepControlAudit(
        postsolve_network_equation_reconstruction_audit_passed=bool(passed),
        solver_result_fixed_fields_preserved=bool(fixed_fields_preserved),
        solver_result_fixed_case_sha256=fixed_case_hash,
        external_bus_mapping_sha256=_mapping_sha256(bus_ids),
        active_bus_count=len(bus),
        isolated_bus_count=isolated_bus_count,
        connected_component_count=len(components),
        reference_bus_count=len(reference_rows),
        reference_structure_valid=reference_structure_valid,
        online_branch_count=int(np.count_nonzero(active_branch)),
        offline_branch_count=int(np.count_nonzero(~active_branch)),
        nonunity_tap_count=int(
            np.count_nonzero(
                active_branch
                & (source_branch[:, TAP] != 0.0)
                & (np.abs(source_branch[:, TAP] - 1.0) > 1.0e-12)
            )
        ),
        nonzero_shift_count=int(
            np.count_nonzero(active_branch & (source_branch[:, SHIFT] != 0.0))
        ),
        nonzero_gs_count=int(np.count_nonzero(source_bus[:, GS] != 0.0)),
        nonzero_bs_count=int(np.count_nonzero(source_bus[:, BS] != 0.0)),
        solver_objective_mw2=solver_objective,
        reconstructed_objective_mw2=reconstructed_objective,
        objective_mismatch_mw2=objective_mismatch,
        l1_target_deviation_mw=float(np.sum(np.abs(deviations))),
        l2_target_deviation_mw=sqrt(reconstructed_objective),
        max_target_deviation_mw=float(np.max(np.abs(deviations))),
        total_up_redispatch_mw=float(np.sum(np.maximum(deviations, 0.0))),
        total_down_redispatch_mw=float(np.sum(np.maximum(-deviations, 0.0))),
        total_generation_mw=float(np.sum(generator[active_generator, PG])),
        total_active_demand_mw=float(np.sum(source_bus[:, PD])),
        total_generation_minus_demand_mw=float(
            np.sum(generator[active_generator, PG]) - np.sum(source_bus[:, PD])
        ),
        max_active_power_bound_violation_mw=float(np.max(p_violation)),
        max_reactive_power_bound_violation_mvar=float(np.max(q_violation)),
        max_offline_pg_mw=max_offline_pg,
        max_offline_qg_mvar=max_offline_qg,
        max_offline_branch_flow_mva=(
            float(np.max(terminal_mva[~active_branch]))
            if np.any(~active_branch)
            else 0.0
        ),
        max_voltage_violation_pu=float(np.max(voltage_violation)),
        max_branch_loading_fraction=max_loading,
        max_branch_loading_violation_fraction=max(max_loading - 1.0, 0.0),
        max_branch_angle_violation_degree=max_angle_violation,
        max_fixed_pg_deviation_mw=max_fixed_pg_deviation,
        max_p_balance_residual_mw=max_p_residual,
        max_q_balance_residual_mvar=max_q_residual,
        max_ybus_terminal_shunt_identity_mismatch_mva=max_ybus_identity,
        max_returned_recomputed_branch_flow_mismatch_mva=max_flow_mismatch,
        max_reference_angle_drift_degree=max_reference_drift,
        max_source_vg_to_optimized_vm_adjustment_pu=max(
            source_controller_adjustments, default=0.0
        ),
        max_output_vg_bus_vm_mismatch_pu=max(output_vg_vm_mismatch, default=0.0),
        generator_records=generator_records,
        bus_records=bus_records,
        branch_records=branch_records,
    )


def _failure_result(
    prepared: AcRecoveryInput,
    *,
    evaluated: bool,
    solver_error_type: str | None,
    solver_error_message: str | None,
    input_unchanged: bool,
) -> StepControlSolveResult:
    return StepControlSolveResult(
        evaluated=evaluated,
        solver_success=False,
        feasibility_witnessed=False,
        status=(
            "not_witnessed_by_registered_step_control_pipeline"
            if evaluated
            else "solver_invocation_exception_no_witness"
        ),
        solver_error_type=solver_error_type,
        solver_error_message=solver_error_message,
        solver_algorithm=565,
        solver_reported_algorithm=None,
        solver_elapsed_seconds=None,
        solver_iterations=None,
        solver_message=None,
        solver_final_feasibility_condition=None,
        solver_final_gradient_condition=None,
        solver_final_complementarity_condition=None,
        solver_final_cost_condition=None,
        solver_input_case_unchanged=input_unchanged,
        recovery_input_fixed_fields_preserved=prepared.fixed_inputs_preserved,
        audit=None,
    )


def _solver_diagnostics(solved: Mapping[str, object]) -> dict[str, object]:
    try:
        elapsed = float(solved["et"])
        output = solved["raw"]["output"]
        iterations = int(output["iterations"])
        message = str(output["message"])
        algorithm = int(output["alg"])
        final = output["hist"][-1]
        feasibility = float(final["feascond"])
        gradient = float(final["gradcond"])
        complementarity = float(final["compcond"])
        cost = float(final["costcond"])
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise RuntimeError("Step-control solver diagnostics drifted") from error
    if iterations < 0 or not all(
        isfinite(value)
        for value in (elapsed, feasibility, gradient, complementarity, cost)
    ):
        raise RuntimeError("Step-control solver diagnostics contain non-finite values")
    if algorithm != 565:
        raise RuntimeError("Step-control solver reported the wrong algorithm")
    return {
        "solver_reported_algorithm": algorithm,
        "solver_elapsed_seconds": elapsed,
        "solver_iterations": iterations,
        "solver_message": message,
        "solver_final_feasibility_condition": feasibility,
        "solver_final_gradient_condition": gradient,
        "solver_final_complementarity_condition": complementarity,
        "solver_final_cost_condition": cost,
    }


def solve_and_audit_step_control(
    prepared: AcRecoveryInput,
    *,
    solver_options: Mapping[str, object] | None = None,
    audit_tolerances: Mapping[str, float] | None = None,
) -> StepControlSolveResult:
    """Run exactly one PIPS-sc call and audit a successful returned point."""

    options = dict(_FROZEN_SOLVER_OPTIONS if solver_options is None else solver_options)
    tolerances = dict(
        _FROZEN_AUDIT_TOLERANCES if audit_tolerances is None else audit_tolerances
    )
    if options != _FROZEN_SOLVER_OPTIONS:
        raise ValueError("Step-control solver options drifted from frozen protocol")
    if tolerances != _FROZEN_AUDIT_TOLERANCES:
        raise ValueError("Step-control audit tolerances drifted from frozen protocol")
    if set(prepared.case) != _CASE_KEYS:
        raise ValueError("Step-control prepared case schema drifted")
    input_hash = _case_sha256(prepared.case)
    if input_hash != prepared.recovery_case_sha256:
        raise ValueError("Step-control prepared case changed before solve")
    try:
        solved = runopf(
            deepcopy(prepared.case),
            ppoption(VERBOSE=0, OUT_ALL=0, **options),
        )
    except Exception as error:
        return _failure_result(
            prepared,
            evaluated=False,
            solver_error_type=type(error).__name__,
            solver_error_message=str(error) or repr(error),
            input_unchanged=_case_sha256(prepared.case) == input_hash,
        )
    input_unchanged = _case_sha256(prepared.case) == input_hash
    if not isinstance(solved, Mapping):
        raise RuntimeError("Step-control solver returned a malformed result")
    diagnostics = _solver_diagnostics(solved)
    if not bool(solved.get("success", False)):
        failed = _failure_result(
            prepared,
            evaluated=True,
            solver_error_type=None,
            solver_error_message=None,
            input_unchanged=input_unchanged,
        )
        return StepControlSolveResult(
            **{
                **failed.__dict__,
                **diagnostics,
            }
        )
    try:
        solver_objective = float(solved["f"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("Step-control solver objective drifted") from error
    audit = audit_step_control_solution(
        prepared,
        solved,
        solver_objective_mw2=solver_objective,
        audit_tolerances=tolerances,
    )
    witnessed = bool(
        input_unchanged
        and prepared.fixed_inputs_preserved
        and audit.postsolve_network_equation_reconstruction_audit_passed
    )
    return StepControlSolveResult(
        evaluated=True,
        solver_success=True,
        feasibility_witnessed=witnessed,
        status=(
            "audited_numerical_feasibility_witness"
            if witnessed
            else "solver_success_postsolve_audit_failed"
        ),
        solver_error_type=None,
        solver_error_message=None,
        solver_algorithm=565,
        solver_input_case_unchanged=input_unchanged,
        recovery_input_fixed_fields_preserved=prepared.fixed_inputs_preserved,
        audit=audit,
        **diagnostics,
    )
