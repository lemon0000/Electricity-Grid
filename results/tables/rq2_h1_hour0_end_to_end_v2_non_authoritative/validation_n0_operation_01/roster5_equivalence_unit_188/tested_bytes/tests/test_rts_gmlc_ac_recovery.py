from copy import deepcopy

import numpy as np
import pytest
from pypower.api import case9, ppoption, runopf
from pypower.idx_bus import PD
from pypower.idx_gen import GEN_STATUS, PG, PMAX, PMIN, VG

import src.grid.rts_gmlc_ac_recovery as recovery


def _case9_input(mode="distributed_committable"):
    source = case9()
    source["branch"][:, 5] = np.maximum(source["branch"][:, 5], 250.0)
    baseline = runopf(deepcopy(source), ppoption(VERBOSE=0, OUT_ALL=0, OPF_ALG=560))
    assert baseline["success"]
    source["gen"][:, PG] = baseline["gen"][:, PG]
    source["bus"][:, 7:9] = baseline["bus"][:, 7:9]
    targets = tuple(float(value) for value in baseline["gen"][:, PG])
    active_rows = tuple(np.flatnonzero(source["gen"][:, GEN_STATUS] > 0.0))
    adjustable = (0,) if mode == "reference_provider" else active_rows
    return recovery.prepare_ac_recovery_case(
        source,
        target_generation_mw_by_row=targets,
        generator_uid_by_row=("g1", "g2", "g3"),
        branch_uid_by_row=tuple(f"b{row}" for row in range(len(source["branch"]))),
        mode=mode,
        adjustable_generator_rows=adjustable,
        reference_generator_row=0,
        reference_generator_uid="g1",
        reference_bus=int(source["gen"][0, 0]),
    )


def test_case9_recovery_modes_apply_nested_active_power_bounds():
    reference = _case9_input("reference_provider")
    distributed = _case9_input("distributed_committable")

    assert reference.adjustable_generator_rows == (0,)
    assert set(reference.adjustable_generator_rows) < set(
        distributed.adjustable_generator_rows
    )
    for row in reference.fixed_generator_rows:
        assert (
            reference.case["gen"][row, PMIN]
            == reference.target_generation_mw_by_row[row]
        )
        assert (
            reference.case["gen"][row, PMAX]
            == reference.target_generation_mw_by_row[row]
        )
    assert reference.fixed_inputs_preserved
    assert distributed.fixed_inputs_preserved
    assert reference.active_power_envelope == "physical_envelope_no_response_time"


def test_case9_recovery_passes_independent_audit():
    prepared = _case9_input()
    result = recovery.solve_and_audit_ac_recovery(
        prepared,
        solver_options=recovery._FROZEN_SOLVER_OPTIONS,
    )

    assert result.solver_success
    assert result.independent_audit_passed
    assert result.recovered
    assert result.status == "recovered_by_local_solver"
    assert result.max_p_balance_residual_mw <= 1.0e-4
    assert result.max_q_balance_residual_mvar <= 1.0e-4
    assert result.objective_mismatch_mw2 <= 1.0e-4
    assert result.solver_input_case_unchanged
    assert result.solver_result_fixed_fields_preserved
    assert len(result.generator_records) == 3
    assert len(result.bus_records) == 9
    assert len(result.branch_records) == 9


def test_independent_audit_rejects_a_solver_success_with_pg_bound_drift(monkeypatch):
    prepared = _case9_input()
    solved = runopf(
        deepcopy(prepared.case),
        ppoption(VERBOSE=0, OUT_ALL=0, OPF_ALG=560, OPF_FLOW_LIM=0),
    )
    assert solved["success"]
    solved["gen"][0, PG] = solved["gen"][0, PMAX] + 1.0

    monkeypatch.setattr(recovery, "runopf", lambda *_args, **_kwargs: solved)
    result = recovery.solve_and_audit_ac_recovery(prepared)

    assert result.solver_success
    assert not result.independent_audit_passed
    assert not result.recovered
    assert result.status == "solver_success_independent_audit_failed"
    assert result.max_active_power_bound_violation_mw >= 1.0


def test_solver_rejects_a_prepared_case_changed_after_preparation():
    prepared = _case9_input()
    prepared.case["bus"][0, PD] += 1.0

    with pytest.raises(ValueError, match="changed after preparation"):
        recovery.solve_and_audit_ac_recovery(prepared)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("OPF_ALG", 565),
        ("OPF_ALG", 0),
        ("OPF_FLOW_LIM", 1),
        ("PF_DC", True),
    ),
)
def test_solver_rejects_protocol_drift_before_runopf(field, value, monkeypatch):
    prepared = _case9_input()
    options = dict(recovery._FROZEN_SOLVER_OPTIONS)
    options[field] = value
    called = False

    def unexpected_runopf(*_args, **_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(recovery, "runopf", unexpected_runopf)
    with pytest.raises(ValueError, match="solver options drifted"):
        recovery.solve_and_audit_ac_recovery(prepared, solver_options=options)
    assert not called


@pytest.mark.parametrize(
    ("field", "value"),
    (("et", float("nan")), ("feascond", float("inf"))),
)
def test_independent_audit_rejects_nonfinite_solver_diagnostics(
    field, value, monkeypatch
):
    prepared = _case9_input()
    solved = runopf(
        deepcopy(prepared.case),
        ppoption(VERBOSE=0, OUT_ALL=0, **recovery._FROZEN_SOLVER_OPTIONS),
    )
    assert solved["success"]
    if field == "et":
        solved["et"] = value
    else:
        solved["raw"]["output"]["hist"][-1][field] = value
    monkeypatch.setattr(recovery, "runopf", lambda *_args, **_kwargs: solved)

    with pytest.raises(RuntimeError, match="diagnostics contain non-finite"):
        recovery.solve_and_audit_ac_recovery(prepared)


def test_independent_audit_rejects_output_vg_bus_vm_drift(monkeypatch):
    prepared = _case9_input()
    solved = runopf(
        deepcopy(prepared.case),
        ppoption(VERBOSE=0, OUT_ALL=0, **recovery._FROZEN_SOLVER_OPTIONS),
    )
    assert solved["success"]
    solved["gen"][0, VG] += 0.1
    monkeypatch.setattr(recovery, "runopf", lambda *_args, **_kwargs: solved)

    result = recovery.solve_and_audit_ac_recovery(prepared)

    assert result.solver_success
    assert not result.recovered
    assert result.max_output_vg_bus_vm_mismatch_pu >= 0.09


def test_runopf_exception_is_reported_without_an_infeasibility_claim(monkeypatch):
    prepared = _case9_input()

    def failed_invocation(*_args, **_kwargs):
        raise RuntimeError("synthetic invocation failure")

    monkeypatch.setattr(recovery, "runopf", failed_invocation)
    result = recovery.solve_and_audit_ac_recovery(prepared)

    assert not result.evaluated
    assert not result.solver_success
    assert not result.recovered
    assert result.status == "not_recovered_by_local_solver"
    assert result.solver_error_type == "RuntimeError"
    assert result.solver_error_message == "synthetic invocation failure"


def test_runopf_failure_retains_finite_solver_diagnostics(monkeypatch):
    prepared = _case9_input()
    solved = runopf(
        deepcopy(prepared.case),
        ppoption(VERBOSE=0, OUT_ALL=0, **recovery._FROZEN_SOLVER_OPTIONS),
    )
    assert solved["success"]
    solved["success"] = False
    solved["raw"]["output"]["message"] = "Numerically failed"
    monkeypatch.setattr(recovery, "runopf", lambda *_args, **_kwargs: solved)

    result = recovery.solve_and_audit_ac_recovery(prepared)

    assert result.evaluated
    assert not result.solver_success
    assert result.status == "not_recovered_by_local_solver"
    assert result.solver_message == "Numerically failed"
    assert result.solver_iterations is not None
    assert result.solver_elapsed_seconds is not None


def test_prepare_rejects_a_nonzero_offline_target():
    source = case9()
    baseline = runopf(deepcopy(source), ppoption(VERBOSE=0, OUT_ALL=0, OPF_ALG=560))
    assert baseline["success"]
    source["gen"][:, PG] = baseline["gen"][:, PG]
    source["gen"][2, GEN_STATUS] = 0.0
    targets = tuple(float(value) for value in source["gen"][:, PG])

    try:
        recovery.prepare_ac_recovery_case(
            source,
            target_generation_mw_by_row=targets,
            generator_uid_by_row=("g1", "g2", "g3"),
            branch_uid_by_row=tuple(f"b{row}" for row in range(len(source["branch"]))),
            mode="reference_provider",
            adjustable_generator_rows=(0,),
            reference_generator_row=0,
            reference_generator_uid="g1",
            reference_bus=int(source["gen"][0, 0]),
        )
    except ValueError as error:
        assert "Offline AC recovery target is nonzero" in str(error)
    else:
        raise AssertionError("nonzero offline target was accepted")
