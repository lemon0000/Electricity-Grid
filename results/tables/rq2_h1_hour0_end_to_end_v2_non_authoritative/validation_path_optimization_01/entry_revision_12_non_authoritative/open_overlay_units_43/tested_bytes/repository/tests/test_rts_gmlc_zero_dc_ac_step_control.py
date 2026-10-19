import hashlib
from pathlib import Path

import pytest
import yaml

from experiments.run_rts_gmlc_zero_dc_ac_step_control import (
    _CONFIG_SHA256,
    _FROZEN_AUDIT_TOLERANCES,
    _FROZEN_SOLVER_OPTIONS,
    _build_context,
    _case_row,
    _read_config,
    _summary,
    _validate_result_rows,
    prepare_preregistration,
)
from src.grid.rts_gmlc_ac_step_control import StepControlSolveResult

CONFIG = Path("configs/rts_gmlc_google_day0_zero_dc_ac_step_control.yaml")


@pytest.fixture(scope="module")
def context():
    return _build_context(CONFIG)


def _invocation_failure():
    return StepControlSolveResult(
        evaluated=False,
        solver_success=False,
        feasibility_witnessed=False,
        status="solver_invocation_exception_no_witness",
        solver_error_type="RuntimeError",
        solver_error_message="synthetic invocation failure",
        solver_algorithm=565,
        solver_reported_algorithm=None,
        solver_elapsed_seconds=None,
        solver_iterations=None,
        solver_message=None,
        solver_final_feasibility_condition=None,
        solver_final_gradient_condition=None,
        solver_final_complementarity_condition=None,
        solver_final_cost_condition=None,
        solver_input_case_unchanged=True,
        recovery_input_fixed_fields_preserved=True,
        audit=None,
    )


def test_step_control_config_freezes_post_outcome_protocol_before_formal_cases():
    config = _read_config(CONFIG)

    assert hashlib.sha256(CONFIG.read_bytes()).hexdigest() == _CONFIG_SHA256
    assert config["solver_options"] == _FROZEN_SOLVER_OPTIONS
    assert {
        key: config["postsolve_audit"][key] for key in _FROZEN_AUDIT_TOLERANCES
    } == _FROZEN_AUDIT_TOLERANCES
    assert config["preregistration"]["primary_zero_recovery_outcomes_observed"]
    assert not config["preregistration"]["formal_zero_step_control_outcomes_observed"]
    assert config["preregistration"]["all_24_formal_step_control_cases_blind"]
    assert config["observed_outcomes_disclosure"]["primary_witnessed_count"] == 22
    assert config["observed_outcomes_disclosure"]["primary_failed_hour_indices"] == [
        15,
        21,
    ]
    assert (
        config["observed_outcomes_disclosure"]["case9_probe_formal_evidence_weight"]
        == "excluded"
    )
    assert config["numerical_protocol"]["exactly_one_solver_call_per_case"]
    assert not config["numerical_protocol"]["retry_allowed"]
    assert not config["numerical_protocol"]["fallback_allowed"]
    assert not config["numerical_protocol"]["independent_solver_claimed"]


def test_step_control_context_binds_all_24_primary_distributed_cases(context):
    assert len(context.cases) == 24
    assert len(context.primary_recovered_timestamps) == 22
    assert [case.hour_index for case in context.cases] == list(range(24))
    assert len({case.timestamp for case in context.cases}) == 24
    assert all(
        case.prepared.mode == "distributed_committable" for case in context.cases
    )
    assert all(case.prepared.fixed_inputs_preserved for case in context.cases)
    assert len(context.input_contract["case_contracts"]) == 24
    assert context.primary_summary["minimum_common_recovery_mode"] is None


def test_prepare_step_control_preregistration_is_atomic_and_idempotent(tmp_path):
    first = prepare_preregistration(CONFIG, output_directory=tmp_path)
    second = prepare_preregistration(CONFIG, output_directory=tmp_path)

    assert first == second
    assert first["formal_zero_step_control_outcomes_observed"] is False
    assert first["all_24_formal_step_control_cases_blind"] is True
    assert (tmp_path / "preregistration" / "SHA256SUMS").exists()
    assert (
        tmp_path / "preregistration" / "config.yaml"
    ).read_bytes() == CONFIG.read_bytes()


def test_step_control_config_byte_drift_is_rejected(tmp_path):
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["solver_options"]["OPF_ALG"] = 560
    drifted = tmp_path / "drifted.yaml"
    drifted.write_text(yaml.safe_dump(config), encoding="utf-8")

    with pytest.raises(ValueError, match="config SHA-256 drifted"):
        _read_config(drifted)


def test_result_validator_accepts_complete_invocation_failure_reporting(context):
    rows = [_case_row(case, _invocation_failure()) for case in context.cases]

    _validate_result_rows(context, rows, [], [], [])
    summary = _summary(
        context,
        {"input_contract_sha256": context.input_contract_sha256},
        rows,
    )

    assert summary["case_count"] == 24
    assert summary["solver_invocation_exception_count"] == 24
    assert summary["step_control_feasibility_witness_count"] == 0
    assert not summary["treatment_followup_existence_gate_passed"]


def test_result_validator_rejects_missing_or_favorable_case_deletion(context):
    rows = [_case_row(case, _invocation_failure()) for case in context.cases]

    with pytest.raises(RuntimeError, match="result coverage drifted"):
        _validate_result_rows(context, rows[:-1], [], [], [])

    rows[0]["feasibility_witnessed"] = True
    with pytest.raises(RuntimeError, match="failure state drifted"):
        _validate_result_rows(context, rows, [], [], [])
