from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import numpy as np
import pytest
from pypower.api import case9, ppoption, runopf
from pypower.idx_brch import RATE_A
from pypower.idx_bus import BUS_TYPE, PD, PV, QD, REF, VA, VM, VMAX, VMIN
from pypower.idx_gen import GEN_STATUS, PG, PMAX, QG, VG

from experiments import run_rts_gmlc_zero_dc_ac_aware_commitment as runner
from src.grid.rts_gmlc_ac_aware_commitment import (
    AcAwareChronology,
    AcAwareCommitmentUnit,
    solve_ac_aware_commitment,
)
from src.grid.rts_gmlc_ac_ipopt import solve_ac_feasibility_ipopt
from src.grid.rts_gmlc_ac_recovery import _case_sha256, prepare_ac_recovery_case


def _prepared_case9(load_scale: float = 1.0):
    source = case9()
    source["bus"][:, PD] *= load_scale
    source["bus"][:, QD] *= load_scale
    source["bus"][:, VMIN] = 0.95
    source["bus"][:, VMAX] = 1.05
    source["branch"][:, RATE_A] = np.maximum(source["branch"][:, RATE_A], 250.0)
    baseline = runopf(deepcopy(source), ppoption(VERBOSE=0, OUT_ALL=0, OPF_ALG=560))
    assert baseline["success"]
    source["bus"][:, (VM, VA)] = baseline["bus"][:, (VM, VA)]
    source["gen"][:, (PG, QG, VG)] = baseline["gen"][:, (PG, QG, VG)]
    targets = tuple(float(value) for value in baseline["gen"][:, PG])
    active_rows = tuple(np.flatnonzero(source["gen"][:, GEN_STATUS] > 0.0))
    return prepare_ac_recovery_case(
        source,
        target_generation_mw_by_row=targets,
        generator_uid_by_row=("g1", "g2", "g3"),
        branch_uid_by_row=tuple(f"b{row}" for row in range(len(source["branch"]))),
        mode="distributed_committable",
        adjustable_generator_rows=active_rows,
        reference_generator_row=0,
        reference_generator_uid="g1",
        reference_bus=int(source["gen"][0, 0]),
    )


def _chronology(
    prepared_cases,
    *,
    ramp_mw_per_hour: float = 1000.0,
    ramp_mw_per_minute: float = 100.0,
    spin_requirement_mw: float = 10.0,
):
    cases = tuple(prepared_cases)
    horizon = len(cases)
    first_generator = np.asarray(cases[0].case["gen"])
    units = []
    for row, uid in enumerate(cases[0].generator_uid_by_row):
        commitment = tuple(
            bool(np.asarray(case.case["gen"])[row, GEN_STATUS] > 0.0) for case in cases
        )
        initial_commitment = commitment[0]
        previous = initial_commitment
        startup = []
        shutdown = []
        for online in commitment:
            startup.append(bool(online and not previous))
            shutdown.append(bool(previous and not online))
            previous = online
        units.append(
            AcAwareCommitmentUnit(
                generator_uid=uid,
                area=1,
                p_max_mw=float(first_generator[row, PMAX]),
                ramp_mw_per_hour=ramp_mw_per_hour,
                ramp_mw_per_minute=ramp_mw_per_minute,
                reserve_eligible=True,
                initial_generation_mw=float(cases[0].target_generation_mw_by_row[row]),
                initial_commitment=initial_commitment,
                commitment_by_hour=commitment,
                startup_by_hour=tuple(startup),
                shutdown_by_hour=tuple(shutdown),
            )
        )
    start = datetime(2020, 1, 1, tzinfo=UTC)
    return AcAwareChronology(
        timestamps=tuple(start + timedelta(hours=hour) for hour in range(horizon)),
        time_step_hours=1.0,
        units=tuple(units),
        spin_up_requirement_by_hour_area_mw=tuple(
            {1: spin_requirement_mw} for _ in range(horizon)
        ),
    )


def test_joint_ac_commitment_witnesses_all_24_hours():
    prepared = _prepared_case9()
    cases = (prepared,) * 24

    result = solve_ac_aware_commitment(cases, _chronology(cases))

    assert result.solver_success
    assert result.feasibility_witnessed
    assert result.return_status == "Solve_Succeeded"
    assert len(result.hour_results) == 24
    assert result.solver_input_cases_unchanged
    assert result.maximum_ramp_violation_mw <= 1.0e-6
    assert result.maximum_reserve_bound_violation_mw <= 1.0e-6
    assert result.maximum_reserve_headroom_violation_mw <= 1.0e-6
    assert result.maximum_reserve_shortfall_mw <= 1.0e-6
    assert all(
        hour.audit.postsolve_network_equation_reconstruction_audit_passed
        for hour in result.hour_results
    )


def test_joint_result_rows_reconstruct_and_reject_tampering():
    prepared = _prepared_case9()
    cases = (prepared,)
    chronology = _chronology(cases)
    result = solve_ac_aware_commitment(cases, chronology)
    commitment = {
        unit.generator_uid: unit.commitment_by_hour[0] for unit in chronology.units
    }
    startup = {unit.generator_uid: unit.startup_by_hour[0] for unit in chronology.units}
    shutdown = {
        unit.generator_uid: unit.shutdown_by_hour[0] for unit in chronology.units
    }
    candidate = runner._LoadedCandidate(
        candidate_id="candidate_00",
        requested_candidate_id="test_candidate",
        relative_cost_budget_delta=0.0,
        operating_cost_usd=1.0,
        reactive_proxy_fraction=1.0,
        commitment_sha256="commitment",
        dispatch_sha256="dispatch",
        commitment=(commitment,),
        startup=(startup,),
        shutdown=(shutdown,),
        generation_mw=(
            dict(
                zip(
                    prepared.generator_uid_by_row,
                    prepared.target_generation_mw_by_row,
                    strict=True,
                )
            ),
        ),
        branch_flows_mw=({},),
        dc_flows_mw=({},),
    )
    context = SimpleNamespace(
        config={
            "joint_ac": {"initial_strategies": ["source"], "expected_hours": 1},
            "independent_audit": runner._EXPECTED_INDEPENDENT_AUDIT,
        },
        request=SimpleNamespace(timestamps=chronology.timestamps),
    )
    rows = runner._joint_result_rows(candidate, result)
    prepared_by_candidate = {candidate.candidate_id: cases}
    chronology_by_candidate = {candidate.candidate_id: chronology}

    runner._validate_joint_result_rows(
        context,
        [candidate],
        prepared_by_candidate,
        chronology_by_candidate,
        [rows[0]],
        rows[1],
        rows[2],
        rows[3],
        rows[4],
        rows[5],
    )

    with pytest.raises(RuntimeError, match="hour coverage"):
        runner._validate_joint_result_rows(
            context,
            [candidate],
            prepared_by_candidate,
            chronology_by_candidate,
            [rows[0]],
            [],
            rows[2],
            rows[3],
            rows[4],
            rows[5],
        )

    changed_bus = deepcopy(rows[3])
    changed_bus[0]["vm_pu"] += 0.01
    changed_bus_run = dict(rows[0])
    changed_bus_run["joint_solution_sha256"] = runner._joint_solution_sha256(
        rows[1], rows[2], changed_bus, rows[4], rows[5]
    )
    with pytest.raises(RuntimeError, match="drifted"):
        runner._validate_joint_result_rows(
            context,
            [candidate],
            prepared_by_candidate,
            chronology_by_candidate,
            [changed_bus_run],
            rows[1],
            rows[2],
            changed_bus,
            rows[4],
            rows[5],
        )

    changed_reserve = deepcopy(rows[5])
    changed_reserve[0]["reserve_up_mw"] += 1000.0
    changed_reserve_run = dict(rows[0])
    changed_reserve_run["joint_solution_sha256"] = runner._joint_solution_sha256(
        rows[1], rows[2], rows[3], rows[4], changed_reserve
    )
    with pytest.raises(RuntimeError, match="maximum_reserve"):
        runner._validate_joint_result_rows(
            context,
            [candidate],
            prepared_by_candidate,
            chronology_by_candidate,
            [changed_reserve_run],
            rows[1],
            rows[2],
            rows[3],
            rows[4],
            changed_reserve,
        )


def test_joint_allows_hourly_reference_bus_changes():
    first = _prepared_case9()
    shifted_source = deepcopy(first.case)
    shifted_source["bus"][0, BUS_TYPE] = PV
    shifted_source["bus"][1, BUS_TYPE] = REF
    active_rows = tuple(np.flatnonzero(shifted_source["gen"][:, GEN_STATUS] > 0.0))
    shifted = prepare_ac_recovery_case(
        shifted_source,
        target_generation_mw_by_row=first.target_generation_mw_by_row,
        generator_uid_by_row=first.generator_uid_by_row,
        branch_uid_by_row=first.branch_uid_by_row,
        mode="distributed_committable",
        adjustable_generator_rows=active_rows,
        reference_generator_row=1,
        reference_generator_uid="g2",
        reference_bus=int(shifted_source["gen"][1, 0]),
    )
    cases = (first, shifted)

    result = solve_ac_aware_commitment(cases, _chronology(cases))

    assert result.feasibility_witnessed
    assert [hour.audit.reference_bus_count for hour in result.hour_results] == [1, 1]


def test_joint_rejects_zero_or_multiple_reference_buses():
    prepared = _prepared_case9()
    for reference_count in (0, 2):
        changed = deepcopy(prepared)
        changed.case["bus"][:, BUS_TYPE] = PV
        if reference_count:
            changed.case["bus"][:reference_count, BUS_TYPE] = REF
        changed = replace(changed, recovery_case_sha256=_case_sha256(changed.case))

        with pytest.raises(ValueError, match="exactly one reference bus"):
            solve_ac_aware_commitment((changed,), _chronology((prepared,)))


def test_joint_ramp_constraints_reject_independently_feasible_hour_splice():
    low = _prepared_case9(1.0)
    high = _prepared_case9(1.35)
    assert solve_ac_feasibility_ipopt(low).original_envelope_feasibility_witnessed
    assert solve_ac_feasibility_ipopt(high).original_envelope_feasibility_witnessed
    cases = (low, high)

    unconstrained = solve_ac_aware_commitment(
        cases, _chronology(cases, ramp_mw_per_hour=1000.0)
    )
    blocked = solve_ac_aware_commitment(
        cases,
        _chronology(
            cases,
            ramp_mw_per_hour=0.0,
            ramp_mw_per_minute=100.0,
            spin_requirement_mw=0.0,
        ),
    )

    assert unconstrained.feasibility_witnessed
    assert not blocked.feasibility_witnessed
    assert not blocked.solver_success or blocked.maximum_nlp_constraint_violation > 1e-6


def test_joint_spin_reserve_shortfall_fails_the_witness():
    prepared = _prepared_case9()
    cases = (prepared, prepared)
    chronology = _chronology(
        cases,
        ramp_mw_per_hour=1000.0,
        ramp_mw_per_minute=1.0,
        spin_requirement_mw=1000.0,
    )

    result = solve_ac_aware_commitment(cases, chronology)

    assert not result.feasibility_witnessed
    assert result.maximum_reserve_shortfall_mw > 1.0


def test_joint_solver_rejects_prepared_input_drift():
    prepared = _prepared_case9()
    changed = deepcopy(prepared)
    changed.case["bus"][0, PD] += 1.0

    with pytest.raises(ValueError, match="changed before solve"):
        solve_ac_aware_commitment((changed,), _chronology((prepared,)))


def test_joint_solver_rejects_noncontinuous_or_inconsistent_chronology():
    prepared = _prepared_case9()
    cases = (prepared, prepared)
    chronology = _chronology(cases)
    broken_timestamps = replace(
        chronology,
        timestamps=(
            chronology.timestamps[0],
            chronology.timestamps[1] + timedelta(hours=1),
        ),
    )
    with pytest.raises(ValueError, match="not continuous"):
        solve_ac_aware_commitment(cases, broken_timestamps)

    first = chronology.units[0]
    broken_unit = replace(
        first,
        commitment_by_hour=(False, True),
        startup_by_hour=(False, True),
        shutdown_by_hour=(True, False),
    )
    broken_commitment = replace(chronology, units=(broken_unit, *chronology.units[1:]))
    with pytest.raises(ValueError, match="adjustable rows"):
        solve_ac_aware_commitment(cases, broken_commitment)
