from copy import deepcopy

import numpy as np
import pytest
from pypower.api import case9, ppoption, runopf
from pypower.idx_brch import PF, RATE_A, SHIFT, TAP
from pypower.idx_bus import BS, BUS_I, PD, VA, VM
from pypower.idx_gen import GEN_BUS, GEN_STATUS, PG, VG

import src.grid.rts_gmlc_ac_step_control as step_control
from src.grid.rts_gmlc_ac_recovery import prepare_ac_recovery_case


@pytest.fixture(scope="module")
def prepared_case9():
    source = case9()
    source["bus"][:, BUS_I] += 100
    source["gen"][:, GEN_BUS] += 100
    source["branch"][:, :2] += 100
    source["branch"][:, RATE_A] = np.maximum(source["branch"][:, RATE_A], 250.0)
    source["branch"][0, TAP] = 1.03
    source["branch"][0, SHIFT] = 2.0
    source["bus"][4, BS] = 5.0
    baseline = runopf(deepcopy(source), ppoption(VERBOSE=0, OUT_ALL=0, OPF_ALG=560))
    assert baseline["success"]
    source["gen"][:, PG] = baseline["gen"][:, PG]
    source["bus"][:, (VM, VA)] = baseline["bus"][:, (VM, VA)]
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
        reference_bus=int(source["gen"][0, GEN_BUS]),
    )


def _solved_565(prepared):
    solved = runopf(
        deepcopy(prepared.case),
        ppoption(
            VERBOSE=0,
            OUT_ALL=0,
            **step_control._FROZEN_SOLVER_OPTIONS,
        ),
    )
    assert solved["success"]
    return solved


def test_step_control_reconstructs_noncontiguous_case_with_tap_shift_and_shunt(
    prepared_case9,
):
    result = step_control.solve_and_audit_step_control(prepared_case9)

    assert result.solver_success
    assert result.feasibility_witnessed
    assert result.status == "audited_numerical_feasibility_witness"
    assert result.solver_reported_algorithm == 565
    audit = result.audit
    assert audit is not None
    assert audit.postsolve_network_equation_reconstruction_audit_passed
    assert audit.nonunity_tap_count == 1
    assert audit.nonzero_shift_count == 1
    assert audit.nonzero_bs_count == 1
    assert audit.connected_component_count == 1
    assert audit.reference_structure_valid
    assert audit.max_p_balance_residual_mw <= 1.0e-4
    assert audit.max_q_balance_residual_mvar <= 1.0e-4
    assert audit.max_ybus_terminal_shunt_identity_mismatch_mva <= 1.0e-6
    assert audit.max_returned_recomputed_branch_flow_mismatch_mva <= 1.0e-6


def test_reconstruction_rejects_tampered_returned_branch_flow(
    prepared_case9, monkeypatch
):
    solved = _solved_565(prepared_case9)
    solved["branch"][0, PF] += 1.0
    monkeypatch.setattr(step_control, "runopf", lambda *_args, **_kwargs: solved)

    result = step_control.solve_and_audit_step_control(prepared_case9)

    assert result.solver_success
    assert not result.feasibility_witnessed
    assert result.audit is not None
    assert result.audit.max_returned_recomputed_branch_flow_mismatch_mva >= 0.99


def test_reconstruction_rejects_tampered_voltage_state(prepared_case9, monkeypatch):
    solved = _solved_565(prepared_case9)
    solved["bus"][1, VM] += 0.01
    for row in range(len(solved["gen"])):
        bus_id = int(solved["gen"][row, GEN_BUS])
        bus_row = np.flatnonzero(solved["bus"][:, BUS_I] == bus_id)[0]
        solved["gen"][row, VG] = solved["bus"][bus_row, VM]
    monkeypatch.setattr(step_control, "runopf", lambda *_args, **_kwargs: solved)

    result = step_control.solve_and_audit_step_control(prepared_case9)

    assert result.solver_success
    assert not result.feasibility_witnessed
    assert result.audit is not None
    assert result.audit.max_p_balance_residual_mw > 1.0e-4


def test_step_control_rejects_prepared_input_drift(prepared_case9):
    prepared = deepcopy(prepared_case9)
    prepared.case["bus"][0, PD] += 1.0

    with pytest.raises(ValueError, match="changed before solve"):
        step_control.solve_and_audit_step_control(prepared)


@pytest.mark.parametrize(
    ("field", "value"),
    (("OPF_ALG", 560), ("SCPDIPM_RED_IT", 19), ("PF_DC", True)),
)
def test_step_control_rejects_solver_protocol_drift(
    prepared_case9, field, value, monkeypatch
):
    options = dict(step_control._FROZEN_SOLVER_OPTIONS)
    options[field] = value
    called = False

    def unexpected_runopf(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(step_control, "runopf", unexpected_runopf)
    with pytest.raises(ValueError, match="solver options drifted"):
        step_control.solve_and_audit_step_control(
            prepared_case9, solver_options=options
        )
    assert not called


def test_angle_sentinel_limits_are_not_treated_as_zero_degree(prepared_case9):
    solved = _solved_565(prepared_case9)
    audit = step_control.audit_step_control_solution(
        prepared_case9,
        solved,
        solver_objective_mw2=float(solved["f"]),
    )

    assert any(
        abs(record.angle_difference_degree) > 0.1 for record in audit.branch_records
    )
    assert audit.max_branch_angle_violation_degree == 0.0
