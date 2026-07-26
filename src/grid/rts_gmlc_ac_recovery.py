"""Bounded active/reactive/voltage AC-OPF recovery with independent audits."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from hashlib import sha256
from math import isfinite, sqrt
from typing import Any, Literal, Mapping, Sequence

import numpy as np
from pypower.api import ppoption, runopf
from pypower.idx_brch import (
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
    PV,
    QD,
    REF,
    VA,
    VM,
    VMAX,
    VMIN,
)
from pypower.idx_cost import COST, MODEL, NCOST, POLYNOMIAL, SHUTDOWN, STARTUP
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


RecoveryMode = Literal["reference_provider", "distributed_committable"]
_RECOVERY_MODES = frozenset({"reference_provider", "distributed_committable"})
_FROZEN_SOLVER_OPTIONS = {
    "PF_DC": False,
    "OPF_ALG": 560,
    "OPF_FLOW_LIM": 0,
    "OPF_IGNORE_ANG_LIM": False,
    "OPF_VIOLATION": 1.0e-8,
    "PDIPM_FEASTOL": 1.0e-8,
    "PDIPM_GRADTOL": 1.0e-6,
    "PDIPM_COMPTOL": 1.0e-6,
    "PDIPM_COSTTOL": 1.0e-6,
    "PDIPM_MAX_IT": 150,
}
_RECOVERY_CASE_KEYS = frozenset(
    {"version", "baseMVA", "bus", "gen", "branch", "gencost"}
)


@dataclass(frozen=True)
class AcRecoveryInput:
    mode: RecoveryMode
    case: dict[str, object]
    target_generation_mw_by_row: tuple[float, ...]
    generator_uid_by_row: tuple[str, ...]
    branch_uid_by_row: tuple[str, ...]
    adjustable_generator_rows: tuple[int, ...]
    fixed_generator_rows: tuple[int, ...]
    reference_generator_row: int
    reference_generator_uid: str
    reference_bus: int
    source_controller_vg_by_bus: tuple[tuple[int, float], ...]
    source_case_sha256: str
    recovery_case_sha256: str
    fixed_inputs_preserved: bool
    active_power_envelope: str


@dataclass(frozen=True)
class AcRecoveryGeneratorRecord:
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
    q_bound_utilization: float | None
    source_vg_pu: float
    output_vg_pu: float
    optimized_bus_vm_pu: float
    source_vg_to_optimized_vm_adjustment_pu: float | None


@dataclass(frozen=True)
class AcRecoveryBusRecord:
    bus: int
    bus_type: int
    pd_mw: float
    qd_mvar: float
    gs_mw_at_1pu: float
    bs_mvar_at_1pu: float
    vm_pu: float
    va_degree: float
    p_balance_residual_mw: float
    q_balance_residual_mvar: float


@dataclass(frozen=True)
class AcRecoveryBranchRecord:
    branch_row: int
    branch_uid: str
    from_bus: int
    to_bus: int
    online: bool
    rate_a_mva: float
    pf_mw: float
    qf_mvar: float
    pt_mw: float
    qt_mvar: float
    from_mva: float
    to_mva: float
    loading_fraction: float


@dataclass(frozen=True)
class AcRecoveryResult:
    evaluated: bool
    solver_success: bool
    independent_audit_passed: bool
    recovered: bool
    status: str
    solver_error_type: str | None
    solver_error_message: str | None
    solver_algorithm: int
    solver_elapsed_seconds: float | None
    solver_iterations: int | None
    solver_message: str | None
    solver_final_feasibility_condition: float | None
    solver_final_gradient_condition: float | None
    solver_final_complementarity_condition: float | None
    solver_final_cost_condition: float | None
    solver_objective_mw2: float | None
    independent_objective_mw2: float | None
    objective_mismatch_mw2: float | None
    squared_target_deviation_mw2: float | None
    l1_target_deviation_mw: float | None
    l2_target_deviation_mw: float | None
    max_target_deviation_mw: float | None
    total_up_redispatch_mw: float | None
    total_down_redispatch_mw: float | None
    reference_redispatch_mw: float | None
    total_generation_mw: float | None
    total_active_demand_mw: float | None
    ac_losses_mw: float | None
    max_active_power_bound_violation_mw: float | None
    max_reactive_power_bound_violation_mvar: float | None
    max_offline_pg_mw: float | None
    max_offline_qg_mvar: float | None
    max_offline_branch_flow_mva: float | None
    max_voltage_violation_pu: float | None
    max_branch_loading_fraction: float | None
    max_branch_loading_violation_fraction: float | None
    max_fixed_pg_deviation_mw: float | None
    max_p_balance_residual_mw: float | None
    max_q_balance_residual_mvar: float | None
    max_source_vg_to_optimized_vm_adjustment_pu: float | None
    max_output_vg_bus_vm_mismatch_pu: float | None
    solver_input_case_unchanged: bool
    recovery_input_fixed_fields_preserved: bool
    solver_result_fixed_fields_preserved: bool
    generator_records: tuple[AcRecoveryGeneratorRecord, ...]
    bus_records: tuple[AcRecoveryBusRecord, ...]
    branch_records: tuple[AcRecoveryBranchRecord, ...]


def _case_sha256(case: Mapping[str, object]) -> str:
    digest = sha256()
    digest.update(str(case.get("version", "")).encode("utf-8"))
    digest.update(np.asarray([float(case["baseMVA"])], dtype=np.float64).tobytes())
    for name in ("bus", "gen", "branch", "gencost"):
        if name not in case:
            digest.update(f"{name}:missing".encode("ascii"))
            continue
        values = np.ascontiguousarray(np.asarray(case[name], dtype=np.float64))
        digest.update(name.encode("ascii"))
        digest.update(str(values.shape).encode("ascii"))
        digest.update(values.tobytes())
    return digest.hexdigest()


def _equal_except_columns(
    left: np.ndarray,
    right: np.ndarray,
    excluded_columns: Sequence[int],
) -> bool:
    if left.shape != right.shape:
        return False
    retained = [
        column for column in range(left.shape[1]) if column not in excluded_columns
    ]
    return np.array_equal(left[:, retained], right[:, retained])


def prepare_ac_recovery_case(
    source_case: Mapping[str, object],
    *,
    target_generation_mw_by_row: Sequence[float],
    generator_uid_by_row: Sequence[str],
    branch_uid_by_row: Sequence[str],
    mode: RecoveryMode,
    adjustable_generator_rows: Sequence[int],
    reference_generator_row: int,
    reference_generator_uid: str,
    reference_bus: int,
    voltage_limits_pu: tuple[float, float] = (0.95, 1.05),
    tolerance: float = 1.0e-6,
) -> AcRecoveryInput:
    """Copy a configured case and apply only pre-specified P and V bounds/costs."""

    if mode not in _RECOVERY_MODES:
        raise ValueError(f"Unknown AC recovery mode {mode}")
    lower_voltage, upper_voltage = map(float, voltage_limits_pu)
    if not 0.0 < lower_voltage < upper_voltage:
        raise ValueError("AC recovery voltage limits are invalid")

    source_bus = np.asarray(source_case["bus"], dtype=float)
    source_gen = np.asarray(source_case["gen"], dtype=float)
    source_branch = np.asarray(source_case["branch"], dtype=float)
    targets = tuple(float(value) for value in target_generation_mw_by_row)
    generator_uids = tuple(str(value) for value in generator_uid_by_row)
    branch_uids = tuple(str(value) for value in branch_uid_by_row)
    if (
        source_bus.ndim != 2
        or source_gen.ndim != 2
        or source_branch.ndim != 2
        or len(targets) != len(source_gen)
        or len(generator_uids) != len(source_gen)
        or len(branch_uids) != len(source_branch)
    ):
        raise ValueError("AC recovery case dimensions drifted")
    if len(set(generator_uids)) != len(generator_uids) or len(set(branch_uids)) != len(
        branch_uids
    ):
        raise ValueError("AC recovery element identifiers must be unique")
    if not all(
        np.all(np.isfinite(np.asarray(source_case[name], dtype=float)))
        for name in ("bus", "gen", "branch")
    ) or not np.all(np.isfinite(targets)):
        raise ValueError("AC recovery source case contains non-finite values")
    active_branch_rows = source_branch[:, BR_STATUS] > 0.0
    if np.any(source_branch[active_branch_rows, RATE_A] <= 0.0):
        raise ValueError("AC recovery active branch has a nonpositive RATE_A")

    active_rows = set(np.flatnonzero(source_gen[:, GEN_STATUS] > 0.0).tolist())
    adjustable_rows = tuple(sorted({int(row) for row in adjustable_generator_rows}))
    adjustable_set = set(adjustable_rows)
    if adjustable_set - active_rows:
        raise ValueError("AC recovery adjustable rows must be online")
    if reference_generator_row not in active_rows:
        raise ValueError("AC recovery reference generator must be online")
    if generator_uids[reference_generator_row] != reference_generator_uid:
        raise ValueError("AC recovery reference generator identity drifted")
    if int(source_gen[reference_generator_row, GEN_BUS]) != int(reference_bus):
        raise ValueError("AC recovery reference bus drifted")
    if mode == "reference_provider" and adjustable_set != {reference_generator_row}:
        raise ValueError(
            "Reference-provider mode must adjust only the reference generator"
        )
    if (
        mode == "distributed_committable"
        and reference_generator_row not in adjustable_set
    ):
        raise ValueError("Distributed mode must contain the reference generator")
    for row, target in enumerate(targets):
        active = row in active_rows
        if active and not (
            float(source_gen[row, PMIN]) - tolerance
            <= target
            <= float(source_gen[row, PMAX]) + tolerance
        ):
            raise ValueError(
                f"AC recovery target is outside physical bounds at row {row}"
            )
        if not active and abs(target) > tolerance:
            raise ValueError(f"Offline AC recovery target is nonzero at row {row}")

    source_controller_vg_by_bus = []
    for bus_row in range(len(source_bus)):
        if int(source_bus[bus_row, BUS_TYPE]) not in (PV, REF):
            continue
        bus_uid = int(source_bus[bus_row, BUS_I])
        online_rows = [
            row for row in active_rows if int(source_gen[row, GEN_BUS]) == bus_uid
        ]
        controller_rows = [
            row
            for row in online_rows
            if source_gen[row, QMAX] - source_gen[row, QMIN] > tolerance
        ]
        if not controller_rows:
            raise ValueError(
                f"Controlled AC recovery bus {bus_uid} has no Q controller"
            )
        controller_vg = [float(source_gen[row, VG]) for row in controller_rows]
        if max(controller_vg) - min(controller_vg) > tolerance:
            raise ValueError(f"Controlled AC recovery bus {bus_uid} has conflicting VG")
        target_vg = controller_vg[0]
        if any(
            abs(float(source_gen[row, VG]) - target_vg) > tolerance
            for row in online_rows
        ):
            raise ValueError(
                f"Controlled AC recovery bus {bus_uid} is not VG-harmonized"
            )
        source_controller_vg_by_bus.append((bus_uid, target_vg))

    case = {
        "version": source_case["version"],
        "baseMVA": float(source_case["baseMVA"]),
        "bus": np.array(source_bus, copy=True),
        "gen": np.array(source_gen, copy=True),
        "branch": np.array(source_branch, copy=True),
    }
    bus = case["bus"]
    generator = case["gen"]
    for row, target in enumerate(targets):
        active = row in active_rows
        generator[row, PG] = target if active else 0.0
        if not active:
            generator[row, PMIN] = 0.0
            generator[row, PMAX] = 0.0
        elif row not in adjustable_set:
            generator[row, PMIN] = target
            generator[row, PMAX] = target

    bus[:, VMIN] = lower_voltage
    bus[:, VMAX] = upper_voltage
    gencost = np.zeros((len(generator), 7), dtype=float)
    for row, target in enumerate(targets):
        gencost[row, MODEL] = POLYNOMIAL
        gencost[row, STARTUP] = 0.0
        gencost[row, SHUTDOWN] = 0.0
        gencost[row, NCOST] = 3
        gencost[row, COST : COST + 3] = (1.0, -2.0 * target, target**2)
    case["gencost"] = gencost

    fixed_inputs_preserved = (
        float(case["baseMVA"]) == float(source_case["baseMVA"])
        and case.get("version") == source_case.get("version")
        and np.array_equal(case["branch"], source_branch)
        and _equal_except_columns(case["bus"], source_bus, (VMIN, VMAX))
        and _equal_except_columns(case["gen"], source_gen, (PG, PMIN, PMAX))
    )
    fixed_rows = tuple(sorted(active_rows - adjustable_set))
    return AcRecoveryInput(
        mode=mode,
        case=case,
        target_generation_mw_by_row=targets,
        generator_uid_by_row=generator_uids,
        branch_uid_by_row=branch_uids,
        adjustable_generator_rows=adjustable_rows,
        fixed_generator_rows=fixed_rows,
        reference_generator_row=int(reference_generator_row),
        reference_generator_uid=str(reference_generator_uid),
        reference_bus=int(reference_bus),
        source_controller_vg_by_bus=tuple(source_controller_vg_by_bus),
        source_case_sha256=_case_sha256(source_case),
        recovery_case_sha256=_case_sha256(case),
        fixed_inputs_preserved=bool(fixed_inputs_preserved),
        active_power_envelope="physical_envelope_no_response_time",
    )


def prepare_rts_gmlc_ac_recovery(
    configured: Any,
    template: Any,
    data: Any,
    *,
    mode: RecoveryMode,
    voltage_limits_pu: tuple[float, float] = (0.95, 1.05),
    tolerance: float = 1.0e-6,
) -> AcRecoveryInput:
    """Select the frozen RTS-GMLC active-P envelope for one configured hour."""

    reference_row = int(
        template.generator_row_by_uid[configured.reference_generator_uid]
    )
    generator_by_uid = {generator.uid: generator for generator in data.generators}
    if set(generator_by_uid) != set(template.generator_uid_by_row):
        raise ValueError("RTS-GMLC recovery generator mapping drifted")
    reference_item = generator_by_uid[configured.reference_generator_uid]
    if reference_item.dispatch_mode != "committable":
        raise ValueError("RTS-GMLC recovery reference generator is not committable")

    generator = np.asarray(configured.case["gen"])
    if mode == "reference_provider":
        adjustable_rows = (reference_row,)
    elif mode == "distributed_committable":
        adjustable_rows = tuple(
            row
            for row, uid in enumerate(template.generator_uid_by_row)
            if generator[row, GEN_STATUS] > 0.0
            and generator_by_uid[uid].dispatch_mode == "committable"
        )
    else:
        raise ValueError(f"Unknown AC recovery mode {mode}")
    return prepare_ac_recovery_case(
        configured.case,
        target_generation_mw_by_row=configured.target_generation_mw_by_row,
        generator_uid_by_row=template.generator_uid_by_row,
        branch_uid_by_row=template.branch_uid_by_row,
        mode=mode,
        adjustable_generator_rows=adjustable_rows,
        reference_generator_row=reference_row,
        reference_generator_uid=configured.reference_generator_uid,
        reference_bus=configured.reference_bus,
        voltage_limits_pu=voltage_limits_pu,
        tolerance=tolerance,
    )


def _failed_result(
    prepared: AcRecoveryInput,
    *,
    solver_algorithm: int,
    evaluated: bool,
    solver_error_type: str | None,
    solver_error_message: str | None,
    input_unchanged: bool,
) -> AcRecoveryResult:
    return AcRecoveryResult(
        evaluated=evaluated,
        solver_success=False,
        independent_audit_passed=False,
        recovered=False,
        status="not_recovered_by_local_solver",
        solver_error_type=solver_error_type,
        solver_error_message=solver_error_message,
        solver_algorithm=solver_algorithm,
        solver_elapsed_seconds=None,
        solver_iterations=None,
        solver_message=None,
        solver_final_feasibility_condition=None,
        solver_final_gradient_condition=None,
        solver_final_complementarity_condition=None,
        solver_final_cost_condition=None,
        solver_objective_mw2=None,
        independent_objective_mw2=None,
        objective_mismatch_mw2=None,
        squared_target_deviation_mw2=None,
        l1_target_deviation_mw=None,
        l2_target_deviation_mw=None,
        max_target_deviation_mw=None,
        total_up_redispatch_mw=None,
        total_down_redispatch_mw=None,
        reference_redispatch_mw=None,
        total_generation_mw=None,
        total_active_demand_mw=None,
        ac_losses_mw=None,
        max_active_power_bound_violation_mw=None,
        max_reactive_power_bound_violation_mvar=None,
        max_offline_pg_mw=None,
        max_offline_qg_mvar=None,
        max_offline_branch_flow_mva=None,
        max_voltage_violation_pu=None,
        max_branch_loading_fraction=None,
        max_branch_loading_violation_fraction=None,
        max_fixed_pg_deviation_mw=None,
        max_p_balance_residual_mw=None,
        max_q_balance_residual_mvar=None,
        max_source_vg_to_optimized_vm_adjustment_pu=None,
        max_output_vg_bus_vm_mismatch_pu=None,
        solver_input_case_unchanged=input_unchanged,
        recovery_input_fixed_fields_preserved=prepared.fixed_inputs_preserved,
        solver_result_fixed_fields_preserved=False,
        generator_records=(),
        bus_records=(),
        branch_records=(),
    )


def _with_solver_failure_diagnostics(
    failed: AcRecoveryResult,
    solved: Mapping[str, object],
) -> AcRecoveryResult:
    updates: dict[str, object] = {}
    try:
        elapsed = float(solved["et"])
        if isfinite(elapsed):
            updates["solver_elapsed_seconds"] = elapsed
    except (KeyError, TypeError, ValueError):
        pass
    raw = solved.get("raw")
    output = raw.get("output") if isinstance(raw, Mapping) else None
    if isinstance(output, Mapping):
        if "message" in output:
            updates["solver_message"] = str(output["message"])
        try:
            iterations = int(output["iterations"])
            if iterations >= 0:
                updates["solver_iterations"] = iterations
        except (KeyError, TypeError, ValueError):
            pass
        history = output.get("hist")
        final = history[-1] if isinstance(history, Sequence) and history else None
        if isinstance(final, Mapping):
            for result_field, source_field in (
                ("solver_final_feasibility_condition", "feascond"),
                ("solver_final_gradient_condition", "gradcond"),
                ("solver_final_complementarity_condition", "compcond"),
                ("solver_final_cost_condition", "costcond"),
            ):
                try:
                    value = float(final[source_field])
                    if isfinite(value):
                        updates[result_field] = value
                except (KeyError, TypeError, ValueError):
                    pass
    return replace(failed, **updates)


def solve_and_audit_ac_recovery(
    prepared: AcRecoveryInput,
    *,
    solver_options: Mapping[str, object] | None = None,
    power_tolerance_mw: float = 1.0e-4,
    reactive_power_tolerance_mvar: float = 1.0e-4,
    voltage_tolerance_pu: float = 1.0e-6,
    loading_tolerance: float = 1.0e-6,
    fixed_pg_tolerance_mw: float = 1.0e-6,
    offline_tolerance_mw: float = 1.0e-6,
    offline_branch_tolerance_mva: float = 1.0e-6,
    balance_tolerance_mw: float = 1.0e-4,
    objective_tolerance_mw2: float = 1.0e-4,
    objective_relative_tolerance: float = 1.0e-8,
) -> AcRecoveryResult:
    """Run local AC-OPF and independently audit every claimed recovery condition."""

    if set(prepared.case) != _RECOVERY_CASE_KEYS:
        raise ValueError("AC recovery prepared case schema drifted")
    input_hash = _case_sha256(prepared.case)
    if input_hash != prepared.recovery_case_sha256:
        raise ValueError("AC recovery prepared case changed after preparation")
    options = dict(_FROZEN_SOLVER_OPTIONS if solver_options is None else solver_options)
    if options != _FROZEN_SOLVER_OPTIONS:
        raise ValueError("AC recovery solver options drifted from the frozen protocol")
    algorithm = 560
    try:
        solved = runopf(
            deepcopy(prepared.case),
            ppoption(VERBOSE=0, OUT_ALL=0, **options),
        )
    except Exception as error:
        return _failed_result(
            prepared,
            solver_algorithm=algorithm,
            evaluated=False,
            solver_error_type=type(error).__name__,
            solver_error_message=str(error) or repr(error),
            input_unchanged=_case_sha256(prepared.case) == input_hash,
        )
    input_unchanged = _case_sha256(prepared.case) == prepared.recovery_case_sha256
    if not isinstance(solved, Mapping):
        raise RuntimeError("AC recovery solver returned a malformed result")
    if not bool(solved.get("success", False)):
        failed = _with_solver_failure_diagnostics(
            _failed_result(
                prepared,
                solver_algorithm=algorithm,
                evaluated=True,
                solver_error_type=None,
                solver_error_message=None,
                input_unchanged=input_unchanged,
            ),
            solved,
        )
        if not failed.solver_message:
            raise RuntimeError("AC recovery solver failure omitted diagnostics")
        return failed

    try:
        bus = np.asarray(solved["bus"], dtype=float)
        generator = np.asarray(solved["gen"], dtype=float)
        branch = np.asarray(solved["branch"], dtype=float)
        solved_gencost = np.asarray(solved["gencost"], dtype=float)
        solver_objective = float(solved["f"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("AC recovery solver result structure drifted") from error
    finite = (
        np.all(np.isfinite(bus))
        and np.all(np.isfinite(generator))
        and np.all(np.isfinite(branch))
        and np.all(np.isfinite(solved_gencost))
        and np.isfinite(solver_objective)
    )
    if not finite:
        raise RuntimeError("AC recovery solver result contains non-finite values")

    try:
        solver_elapsed = float(solved["et"])
        raw_output = solved["raw"]["output"]
        solver_iterations = int(raw_output["iterations"])
        solver_message = str(raw_output["message"])
        final_history = raw_output["hist"][-1]
        final_feasibility = float(final_history["feascond"])
        final_gradient = float(final_history["gradcond"])
        final_complementarity = float(final_history["compcond"])
        final_cost = float(final_history["costcond"])
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise RuntimeError("AC recovery solver diagnostics drifted") from error
    if solver_iterations < 0 or not all(
        isfinite(value)
        for value in (
            solver_elapsed,
            final_feasibility,
            final_gradient,
            final_complementarity,
            final_cost,
        )
    ):
        raise RuntimeError("AC recovery solver diagnostics contain non-finite values")

    source_bus = np.asarray(prepared.case["bus"])
    source_generator = np.asarray(prepared.case["gen"])
    source_branch = np.asarray(prepared.case["branch"])
    result_fixed_fields_preserved = (
        bus.ndim == 2
        and generator.ndim == 2
        and branch.ndim == 2
        and solved_gencost.ndim == 2
        and bus.shape[0] == source_bus.shape[0]
        and bus.shape[1] >= source_bus.shape[1]
        and generator.shape[0] == source_generator.shape[0]
        and generator.shape[1] >= source_generator.shape[1]
        and branch.shape[0] == source_branch.shape[0]
        and branch.shape[1] >= source_branch.shape[1]
        and _equal_except_columns(bus[:, : source_bus.shape[1]], source_bus, (VM, VA))
        and _equal_except_columns(
            generator[:, : source_generator.shape[1]],
            source_generator,
            (PG, QG, VG),
        )
        and np.array_equal(branch[:, : source_branch.shape[1]], source_branch)
        and np.array_equal(solved_gencost, prepared.case["gencost"])
    )
    if not result_fixed_fields_preserved:
        raise RuntimeError("AC recovery solver changed fixed result fields")

    bus_row_by_uid = {int(row[BUS_I]): index for index, row in enumerate(bus)}
    if len(bus_row_by_uid) != len(bus):
        raise RuntimeError("AC recovery result contains duplicate bus identifiers")
    active_generator = generator[:, GEN_STATUS] > 0.0
    active_branch = branch[:, BR_STATUS] > 0.0
    active_bus = bus[:, BUS_TYPE] != NONE
    targets = np.asarray(prepared.target_generation_mw_by_row, dtype=float)
    deviations = generator[:, PG] - targets

    p_violation = np.maximum(
        np.maximum(
            generator[:, PG] - generator[:, PMAX], generator[:, PMIN] - generator[:, PG]
        ),
        0.0,
    )
    q_violation = np.maximum(
        np.maximum(
            generator[:, QG] - generator[:, QMAX], generator[:, QMIN] - generator[:, QG]
        ),
        0.0,
    )
    offline = ~active_generator
    max_offline_pg = (
        float(np.max(np.abs(generator[offline, PG]))) if np.any(offline) else 0.0
    )
    max_offline_qg = (
        float(np.max(np.abs(generator[offline, QG]))) if np.any(offline) else 0.0
    )
    voltage_violation = np.maximum(
        np.maximum(bus[:, VM] - bus[:, VMAX], bus[:, VMIN] - bus[:, VM]),
        0.0,
    )

    branch_from_mva = np.hypot(branch[:, PF], branch[:, QF])
    branch_to_mva = np.hypot(branch[:, PT], branch[:, QT])
    branch_terminal_mva = np.maximum(branch_from_mva, branch_to_mva)
    branch_loading = np.zeros(len(branch), dtype=float)
    for row in np.flatnonzero(active_branch):
        rating = float(branch[row, RATE_A])
        if rating > 0.0:
            branch_loading[row] = branch_terminal_mva[row] / rating
    max_loading = float(np.max(branch_loading)) if len(branch_loading) else 0.0
    max_offline_branch_flow = (
        float(np.max(branch_terminal_mva[~active_branch]))
        if np.any(~active_branch)
        else 0.0
    )

    p_residual = np.zeros(len(bus), dtype=float)
    q_residual = np.zeros(len(bus), dtype=float)
    for row in np.flatnonzero(active_generator):
        bus_row = bus_row_by_uid[int(generator[row, GEN_BUS])]
        p_residual[bus_row] += generator[row, PG]
        q_residual[bus_row] += generator[row, QG]
    p_residual -= bus[:, PD] + bus[:, GS] * bus[:, VM] ** 2
    q_residual -= bus[:, QD] - bus[:, BS] * bus[:, VM] ** 2
    for row in np.flatnonzero(active_branch):
        p_residual[bus_row_by_uid[int(branch[row, F_BUS])]] -= branch[row, PF]
        q_residual[bus_row_by_uid[int(branch[row, F_BUS])]] -= branch[row, QF]
        p_residual[bus_row_by_uid[int(branch[row, T_BUS])]] -= branch[row, PT]
        q_residual[bus_row_by_uid[int(branch[row, T_BUS])]] -= branch[row, QT]

    fixed_rows = np.asarray(prepared.fixed_generator_rows, dtype=int)
    max_fixed_deviation = (
        float(np.max(np.abs(deviations[fixed_rows]))) if len(fixed_rows) else 0.0
    )
    independent_objective = float(np.sum(deviations**2))
    objective_mismatch = abs(solver_objective - independent_objective)

    generator_records = []
    controller_adjustments = [
        abs(float(bus[bus_row_by_uid[bus_uid], VM]) - source_vg)
        for bus_uid, source_vg in prepared.source_controller_vg_by_bus
    ]
    output_vg_bus_vm_mismatch = [
        abs(
            float(generator[row, VG])
            - float(bus[bus_row_by_uid[int(generator[row, GEN_BUS])], VM])
        )
        for row in np.flatnonzero(active_generator)
    ]
    adjustable_set = set(prepared.adjustable_generator_rows)
    for row, uid in enumerate(prepared.generator_uid_by_row):
        bus_uid = int(generator[row, GEN_BUS])
        optimized_vm = float(bus[bus_row_by_uid[bus_uid], VM])
        q_range = float(generator[row, QMAX] - generator[row, QMIN])
        online = bool(active_generator[row])
        controller_adjustment = (
            optimized_vm - float(source_generator[row, VG])
            if online and q_range > reactive_power_tolerance_mvar
            else None
        )
        generator_records.append(
            AcRecoveryGeneratorRecord(
                generator_row=row,
                generator_uid=uid,
                bus=bus_uid,
                online=online,
                adjustable_active_power=row in adjustable_set,
                target_pg_mw=float(targets[row]),
                pg_mw=float(generator[row, PG]),
                pg_deviation_mw=float(deviations[row]),
                pmin_mw=float(generator[row, PMIN]),
                pmax_mw=float(generator[row, PMAX]),
                qg_mvar=float(generator[row, QG]),
                qmin_mvar=float(generator[row, QMIN]),
                qmax_mvar=float(generator[row, QMAX]),
                q_bound_utilization=(
                    float((generator[row, QG] - generator[row, QMIN]) / q_range)
                    if q_range > reactive_power_tolerance_mvar
                    else None
                ),
                source_vg_pu=float(source_generator[row, VG]),
                output_vg_pu=float(generator[row, VG]),
                optimized_bus_vm_pu=optimized_vm,
                source_vg_to_optimized_vm_adjustment_pu=controller_adjustment,
            )
        )
    bus_records = tuple(
        AcRecoveryBusRecord(
            bus=int(row[BUS_I]),
            bus_type=int(row[BUS_TYPE]),
            pd_mw=float(row[PD]),
            qd_mvar=float(row[QD]),
            gs_mw_at_1pu=float(row[GS]),
            bs_mvar_at_1pu=float(row[BS]),
            vm_pu=float(row[VM]),
            va_degree=float(row[VA]),
            p_balance_residual_mw=float(p_residual[index]),
            q_balance_residual_mvar=float(q_residual[index]),
        )
        for index, row in enumerate(bus)
    )
    branch_records = tuple(
        AcRecoveryBranchRecord(
            branch_row=row,
            branch_uid=prepared.branch_uid_by_row[row],
            from_bus=int(branch[row, F_BUS]),
            to_bus=int(branch[row, T_BUS]),
            online=bool(active_branch[row]),
            rate_a_mva=float(branch[row, RATE_A]),
            pf_mw=float(branch[row, PF]),
            qf_mvar=float(branch[row, QF]),
            pt_mw=float(branch[row, PT]),
            qt_mvar=float(branch[row, QT]),
            from_mva=float(branch_from_mva[row]),
            to_mva=float(branch_to_mva[row]),
            loading_fraction=float(branch_loading[row]),
        )
        for row in range(len(branch))
    )

    max_p_violation = (
        float(np.max(p_violation[active_generator]))
        if np.any(active_generator)
        else 0.0
    )
    max_q_violation = (
        float(np.max(q_violation[active_generator]))
        if np.any(active_generator)
        else 0.0
    )
    max_voltage_violation = (
        float(np.max(voltage_violation[active_bus])) if np.any(active_bus) else 0.0
    )
    max_p_residual = float(np.max(np.abs(p_residual[active_bus])))
    max_q_residual = float(np.max(np.abs(q_residual[active_bus])))
    max_output_vg_mismatch = max(output_vg_bus_vm_mismatch, default=0.0)
    audit_passed = (
        input_unchanged
        and prepared.fixed_inputs_preserved
        and result_fixed_fields_preserved
        and max_p_violation <= power_tolerance_mw
        and max_q_violation <= reactive_power_tolerance_mvar
        and max_offline_pg <= offline_tolerance_mw
        and max_offline_qg <= offline_tolerance_mw
        and max_offline_branch_flow <= offline_branch_tolerance_mva
        and max_voltage_violation <= voltage_tolerance_pu
        and max_output_vg_mismatch <= voltage_tolerance_pu
        and max_loading <= 1.0 + loading_tolerance
        and max_fixed_deviation <= fixed_pg_tolerance_mw
        and max_p_residual <= balance_tolerance_mw
        and max_q_residual <= balance_tolerance_mw
        and objective_mismatch
        <= objective_tolerance_mw2
        + objective_relative_tolerance * max(1.0, independent_objective)
    )

    active_deviations = deviations[active_generator]
    total_generation = float(np.sum(generator[active_generator, PG]))
    total_demand = float(np.sum(bus[:, PD]))
    return AcRecoveryResult(
        evaluated=True,
        solver_success=True,
        independent_audit_passed=bool(audit_passed),
        recovered=bool(audit_passed),
        status=(
            "recovered_by_local_solver"
            if audit_passed
            else "solver_success_independent_audit_failed"
        ),
        solver_error_type=None,
        solver_error_message=None,
        solver_algorithm=algorithm,
        solver_elapsed_seconds=solver_elapsed,
        solver_iterations=solver_iterations,
        solver_message=solver_message,
        solver_final_feasibility_condition=final_feasibility,
        solver_final_gradient_condition=final_gradient,
        solver_final_complementarity_condition=final_complementarity,
        solver_final_cost_condition=final_cost,
        solver_objective_mw2=solver_objective,
        independent_objective_mw2=independent_objective,
        objective_mismatch_mw2=objective_mismatch,
        squared_target_deviation_mw2=independent_objective,
        l1_target_deviation_mw=float(np.sum(np.abs(active_deviations))),
        l2_target_deviation_mw=sqrt(independent_objective),
        max_target_deviation_mw=(
            float(np.max(np.abs(active_deviations))) if len(active_deviations) else 0.0
        ),
        total_up_redispatch_mw=float(np.sum(np.maximum(active_deviations, 0.0))),
        total_down_redispatch_mw=float(np.sum(np.maximum(-active_deviations, 0.0))),
        reference_redispatch_mw=float(deviations[prepared.reference_generator_row]),
        total_generation_mw=total_generation,
        total_active_demand_mw=total_demand,
        ac_losses_mw=total_generation - total_demand,
        max_active_power_bound_violation_mw=max_p_violation,
        max_reactive_power_bound_violation_mvar=max_q_violation,
        max_offline_pg_mw=max_offline_pg,
        max_offline_qg_mvar=max_offline_qg,
        max_offline_branch_flow_mva=max_offline_branch_flow,
        max_voltage_violation_pu=max_voltage_violation,
        max_branch_loading_fraction=max_loading,
        max_branch_loading_violation_fraction=max(max_loading - 1.0, 0.0),
        max_fixed_pg_deviation_mw=max_fixed_deviation,
        max_p_balance_residual_mw=max_p_residual,
        max_q_balance_residual_mvar=max_q_residual,
        max_source_vg_to_optimized_vm_adjustment_pu=max(
            controller_adjustments, default=0.0
        ),
        max_output_vg_bus_vm_mismatch_pu=max_output_vg_mismatch,
        solver_input_case_unchanged=input_unchanged,
        recovery_input_fixed_fields_preserved=prepared.fixed_inputs_preserved,
        solver_result_fixed_fields_preserved=result_fixed_fields_preserved,
        generator_records=tuple(generator_records),
        bus_records=bus_records,
        branch_records=branch_records,
    )


__all__ = [
    "AcRecoveryBranchRecord",
    "AcRecoveryBusRecord",
    "AcRecoveryGeneratorRecord",
    "AcRecoveryInput",
    "AcRecoveryResult",
    "RecoveryMode",
    "prepare_ac_recovery_case",
    "prepare_rts_gmlc_ac_recovery",
    "solve_and_audit_ac_recovery",
]
