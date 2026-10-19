import hashlib
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import experiments.run_rts_gmlc_zero_dc_ac_ipopt_diagnostic as runner
from experiments.run_rts_gmlc_zero_dc_ac_ipopt_diagnostic import (
    _CONFIG_SHA256,
    _build_context,
    _case_row,
    _detail_rows,
    _read_config,
    _sensitivity_witness,
    _validate_result_rows,
    _verify_voltage_reference,
    prepare_preregistration,
)
from src.grid.rts_gmlc_ac_ipopt import (
    _FROZEN_IPOPT_OPTIONS,
    solve_ac_feasibility_ipopt,
)
from src.grid.rts_gmlc_ac_step_control import _FROZEN_AUDIT_TOLERANCES

CONFIG = Path("configs/rts_gmlc_google_day0_zero_dc_ac_ipopt_diagnostic.yaml")


@pytest.fixture(scope="module")
def context():
    return _build_context(CONFIG)


def test_ipopt_diagnostic_config_freezes_all_24_post_outcome_modes():
    config = _read_config(CONFIG)

    assert hashlib.sha256(CONFIG.read_bytes()).hexdigest() == _CONFIG_SHA256
    assert config["solver"]["ipopt_options"] == _FROZEN_IPOPT_OPTIONS
    assert {
        key: config["postsolve_audit"][key] for key in _FROZEN_AUDIT_TOLERANCES
    } == _FROZEN_AUDIT_TOLERANCES
    assert config["preregistration"]["partial_ipopt_protocol_probes_observed"]
    assert not config["preregistration"]["formal_full_24_mode_outcomes_observed"]
    assert not config["preregistration"]["all_formal_cases_blind"]
    assert config["case_scope"]["expected_runs"] == 96
    assert [mode["id"] for mode in config["case_scope"]["run_modes"]] == [
        "original_source",
        "original_midpoint",
        "original_flat_target_midq",
        "voltage_plus_0p01_source",
    ]
    assert config["interpretation"][
        "voltage_sensitivity_cannot_replace_official_bounds"
    ]
    assert not config["observed_probe_disclosure"][
        "solver_reported_infeasibility_is_global_proof"
    ]


def test_ipopt_context_binds_parent_cases_solver_and_official_voltage_limits(context):
    assert len(context.step_context.cases) == 24
    assert len(context.run_modes) == 4
    assert len(context.input_contract["case_contracts"]) == 24
    assert context.step_summary["step_control_feasibility_witness_count"] == 22
    reference = context.input_contract["verified_voltage_reference"]
    assert reference["bus_count"] == 73
    assert reference["uniform_vmax_pu"] == 1.05
    assert reference["uniform_vmin_pu"] == 0.95
    assert context.input_contract["casadi_identity"]["version"] == "3.7.2"


def test_official_voltage_reference_rejects_config_or_file_drift(context):
    reference = _verify_voltage_reference(context.config)
    assert reference["uniform_vmax_pu"] == 1.05

    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["official_voltage_limit_reference"]["expected_uniform_vmax_pu"] = 1.06
    with pytest.raises(RuntimeError, match="voltage limits drifted"):
        _verify_voltage_reference(config)


def test_prepare_ipopt_preregistration_is_atomic_and_idempotent(tmp_path):
    first = prepare_preregistration(CONFIG, output_directory=tmp_path)
    second = prepare_preregistration(CONFIG, output_directory=tmp_path)

    assert first == second
    assert first["partial_ipopt_protocol_probes_observed"] is True
    assert first["formal_full_24_mode_outcomes_observed"] is False
    assert first["all_formal_cases_blind"] is False
    assert (tmp_path / "preregistration" / "SHA256SUMS").exists()
    assert (
        tmp_path / "preregistration" / "config.yaml"
    ).read_bytes() == CONFIG.read_bytes()


def test_ipopt_config_byte_drift_and_missing_result_coverage_are_rejected(
    context, tmp_path
):
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["solver"]["ipopt_options"]["ipopt.max_iter"] = 999
    drifted = tmp_path / "drifted.yaml"
    drifted.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(ValueError, match="config SHA-256 drifted"):
        _read_config(drifted)

    with pytest.raises(RuntimeError, match="result coverage drifted"):
        _validate_result_rows(context, [], [], [], [])


def test_voltage_sensitivity_requires_success_and_relaxed_algebraic_audit():
    class Audit:
        solver_result_fixed_fields_preserved = True
        reference_structure_valid = True
        max_active_power_bound_violation_mw = 0.0
        max_reactive_power_bound_violation_mvar = 0.0
        max_offline_pg_mw = 0.0
        max_offline_qg_mvar = 0.0
        max_offline_branch_flow_mva = 0.0
        max_voltage_violation_pu = 0.01
        max_branch_loading_fraction = 1.0
        max_branch_angle_violation_degree = 0.0
        max_fixed_pg_deviation_mw = 0.0
        max_p_balance_residual_mw = 0.0
        max_q_balance_residual_mvar = 0.0
        max_ybus_terminal_shunt_identity_mismatch_mva = 0.0
        max_returned_recomputed_branch_flow_mismatch_mva = 0.0
        max_reference_angle_drift_degree = 0.0
        max_output_vg_bus_vm_mismatch_pu = 0.0

    class Result:
        solver_success = True
        maximum_nlp_constraint_violation = 0.0
        maximum_nlp_variable_bound_violation = 0.0
        voltage_bound_expansion_pu = 0.01
        audit = Audit()

    assert _sensitivity_witness(Result())
    Result.solver_success = False
    assert not _sensitivity_witness(Result())


def test_persisted_success_is_reconstructed_and_vm_tampering_is_rejected(
    context, monkeypatch
):
    mode = context.run_modes[0]
    case = context.step_context.cases[0]
    result = solve_ac_feasibility_ipopt(
        case.prepared,
        initial_strategy=mode.initial_strategy,
        envelope=mode.envelope,
    )
    assert result.original_envelope_feasibility_witnessed
    case_rows = [_case_row(mode, case, result)]
    generator_rows, bus_rows, branch_rows = _detail_rows(mode, case, result)
    small_context = replace(
        context,
        run_modes=(mode,),
        step_context=SimpleNamespace(cases=(case,)),
    )
    monkeypatch.setattr(runner, "_EXPECTED_RUNS", 1)

    _validate_result_rows(
        small_context, case_rows, generator_rows, bus_rows, branch_rows
    )

    tampered_bus_rows = deepcopy(bus_rows)
    tampered_bus_rows[0]["vm_pu"] += 1.0e-3
    with pytest.raises(RuntimeError, match="drifted"):
        _validate_result_rows(
            small_context,
            case_rows,
            generator_rows,
            tampered_bus_rows,
            branch_rows,
        )
