import hashlib
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml
from pypower.api import case9, ppoption, runopf
from pypower.idx_gen import GEN_STATUS, PG

from experiments.run_rts_gmlc_zero_dc_ac_recovery import (
    _CASE_FIELDS,
    _build_context,
    _expected_case_metadata,
    _read_config,
    _summary,
    _validate_detail_aggregates,
    _validate_result_rows,
    prepare_preregistration,
)
from src.grid.rts_gmlc_ac_recovery import (
    _FROZEN_SOLVER_OPTIONS,
    prepare_ac_recovery_case,
    solve_and_audit_ac_recovery,
)


CONFIG = Path("configs/rts_gmlc_google_day0_zero_dc_ac_recovery.yaml")


@pytest.fixture(scope="module")
def context():
    return _build_context(CONFIG)


def test_recovery_config_discloses_observed_zero_outcomes_and_freezes_blind_cases():
    config = _read_config(CONFIG)
    preregistration = config["preregistration"]

    assert preregistration["zero_normal_ac_outcomes_observed"]
    assert preregistration["zero_normal_ac_converged_count_observed"] == 24
    assert preregistration["zero_normal_ac_secure_count_observed"] == 0
    assert not preregistration["zero_recovery_outcomes_observed"]
    assert preregistration["all_zero_recovery_cases_blind"]
    assert preregistration["legacy_vg_treatment_ac_opf_implementation_probe_observed"]
    assert (
        preregistration["treatment_probe_evidence_role"]
        == "disclosed_implementation_diagnostic_excluded_from_zero_recovery_evidence"
    )
    assert config["case_scope"]["modes"] == [
        "reference_provider",
        "distributed_committable",
    ]
    assert config["case_scope"]["expected_unique_cases"] == 48
    assert config["recovery_modes"]["shared_envelope_evidence"] == (
        "physical_envelope_no_response_time"
    )
    assert not config["recovery_modes"]["response_time_or_ramp_constraint_used"]
    assert config["interpretation"]["solver_failure_label"] == (
        "not_recovered_by_local_solver"
    )


def test_recovery_context_binds_all_frozen_zero_artifacts(context):
    parent = context.config["parent_zero_control"]

    assert context.zero.input_contract_sha256 == parent["input_contract_sha256"]
    assert context.input_contract["parent_zero_control"] == parent
    assert context.input_contract["observed_evidence_disclosure"] == {
        "zero_normal_ac_case_count": 24,
        "zero_normal_ac_converged_count": 24,
        "zero_normal_ac_secure_count": 0,
        "amendment_004_voltage_control_probe_source_amendment_id": (
            "rts_gmlc_ac_replay_q_capable_voltage_control_amendment_004"
        ),
        "amendment_004_voltage_control_probe_case": (
            "bus120_unity_2020-01-01T00:00:00+00:00_normal"
        ),
        "amendment_004_voltage_control_probe_secure": False,
        "amendment_004_voltage_control_probe_formal_evidence_weight": "excluded",
        "legacy_vg_treatment_ac_opf_implementation_probe_observed": True,
        "legacy_vg_treatment_ac_opf_probe_voltage_semantics": (
            "superseded_pre_amendment_004_vg_semantics"
        ),
        "legacy_vg_treatment_ac_opf_probe_artifact_status": (
            "not_formally_registered_implementation_probe"
        ),
        "legacy_vg_treatment_ac_opf_probe_outcomes_used": False,
        "legacy_vg_treatment_ac_opf_probe_formal_evidence_weight": "excluded",
    }
    for subdirectory, expected in (
        ("preregistration", parent["preregistration_manifest_sha256"]),
        ("dc_dispatch", parent["dc_dispatch_manifest_sha256"]),
        ("ac_normal", parent["normal_ac_manifest_sha256"]),
    ):
        manifest = (
            Path(parent["output_directory"]) / subdirectory / "SHA256SUMS"
        ).read_bytes()
        assert hashlib.sha256(manifest).hexdigest() == expected


def test_prepare_recovery_preregistration_is_atomic_and_idempotent(tmp_path):
    first = prepare_preregistration(CONFIG, output_directory=tmp_path)
    second = prepare_preregistration(CONFIG, output_directory=tmp_path)

    assert first == second
    assert first["zero_normal_ac_outcomes_observed"]
    assert not first["zero_recovery_outcomes_observed"]
    assert (tmp_path / "preregistration" / "SHA256SUMS").exists()
    assert (tmp_path / "preregistration" / "config.yaml").read_bytes() == (
        CONFIG.read_bytes()
    )
    assert not (tmp_path / "recovery").exists()


def test_recovery_config_byte_drift_is_rejected(tmp_path):
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["solver_options"]["OPF_ALG"] = 565
    changed = tmp_path / "changed.yaml"
    changed.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="config SHA-256 drifted"):
        _read_config(changed)


def test_result_validator_rejects_missing_hour_mode_coverage(context):
    with pytest.raises(RuntimeError, match="case coverage drifted"):
        _validate_result_rows(context, [], [], [], [])


def _solver_failure_rows(context):
    rows = []
    for (timestamp, mode), metadata in _expected_case_metadata(context).items():
        row = {field: "" for field in _CASE_FIELDS}
        row.update(metadata)
        row.update(
            {
                "timestamp": timestamp,
                "mode": mode,
                "state_id": "normal",
                "zero_data_center": True,
                "evaluated": True,
                "solver_success": False,
                "independent_audit_passed": False,
                "recovered": False,
                "status": "not_recovered_by_local_solver",
                "solver_algorithm": 560,
                "solver_message": "Numerically failed",
                "solver_input_case_unchanged": True,
                "recovery_input_fixed_fields_preserved": True,
                "solver_result_fixed_fields_preserved": False,
            }
        )
        rows.append(row)
    return rows


def test_result_validator_enforces_exact_failure_state_and_frozen_identity(context):
    rows = _solver_failure_rows(context)
    _validate_result_rows(context, rows, [], [], [])

    rows[0]["independent_audit_passed"] = True
    with pytest.raises(RuntimeError, match="acceptance semantics drifted"):
        _validate_result_rows(context, rows, [], [], [])
    rows[0]["independent_audit_passed"] = False

    original_reference_uid = rows[0]["reference_generator_uid"]
    rows[0]["reference_generator_uid"] = "bogus"
    with pytest.raises(RuntimeError, match="frozen case metadata drifted"):
        _validate_result_rows(context, rows, [], [], [])
    rows[0]["reference_generator_uid"] = original_reference_uid

    rows[0]["hour_index"] = 0.5
    with pytest.raises(RuntimeError, match="is not an integer"):
        _validate_result_rows(context, rows, [], [], [])


def test_summary_preserves_nested_mode_numerical_anomaly(context):
    metric_fields = (
        "squared_target_deviation_mw2",
        "max_target_deviation_mw",
        "max_voltage_violation_pu",
        "max_branch_loading_fraction",
        "max_active_power_bound_violation_mw",
        "max_reactive_power_bound_violation_mvar",
        "max_fixed_pg_deviation_mw",
        "max_offline_branch_flow_mva",
        "max_p_balance_residual_mw",
        "max_q_balance_residual_mvar",
        "objective_mismatch_mw2",
        "max_source_vg_to_optimized_vm_adjustment_pu",
        "max_output_vg_bus_vm_mismatch_pu",
    )
    rows = []
    first_timestamp = context.zero.zero_business.points[0].timestamp.isoformat()
    for point in context.zero.zero_business.points:
        timestamp = point.timestamp.isoformat()
        for mode in ("reference_provider", "distributed_committable"):
            recovered = not (
                timestamp == first_timestamp and mode == "distributed_committable"
            )
            rows.append(
                {
                    "timestamp": timestamp,
                    "mode": mode,
                    "evaluated": "true",
                    "solver_success": "true" if recovered else "false",
                    "independent_audit_passed": "true" if recovered else "false",
                    "recovered": "true" if recovered else "false",
                    "status": (
                        "recovered_by_local_solver"
                        if recovered
                        else "not_recovered_by_local_solver"
                    ),
                    **{field: 0.0 for field in metric_fields},
                }
            )

    summary = _summary(
        context,
        {"input_contract_sha256": context.input_contract_sha256},
        rows,
    )

    assert summary["nested_mode_numerical_anomaly"]
    assert summary["nested_mode_numerical_anomaly_timestamps"] == [first_timestamp]
    assert summary["minimum_common_recovery_mode"] is None
    assert not summary["all_24_zero_hours_recovered_under_common_mode"]


def test_detail_aggregate_rejects_a_tampered_success_bus_voltage():
    source = case9()
    source["branch"][:, 5] = np.maximum(source["branch"][:, 5], 250.0)
    baseline = runopf(
        deepcopy(source),
        ppoption(VERBOSE=0, OUT_ALL=0, OPF_ALG=560),
    )
    assert baseline["success"]
    source["gen"][:, PG] = baseline["gen"][:, PG]
    source["bus"][:, 7:9] = baseline["bus"][:, 7:9]
    prepared = prepare_ac_recovery_case(
        source,
        target_generation_mw_by_row=tuple(
            float(value) for value in baseline["gen"][:, PG]
        ),
        generator_uid_by_row=("g1", "g2", "g3"),
        branch_uid_by_row=tuple(f"b{row}" for row in range(len(source["branch"]))),
        mode="distributed_committable",
        adjustable_generator_rows=tuple(
            np.flatnonzero(source["gen"][:, GEN_STATUS] > 0.0)
        ),
        reference_generator_row=0,
        reference_generator_uid="g1",
        reference_bus=int(source["gen"][0, 0]),
    )
    result = solve_and_audit_ac_recovery(
        prepared,
        solver_options=_FROZEN_SOLVER_OPTIONS,
    )
    assert result.recovered
    key = ("case9", "distributed_committable")
    case = asdict(result)
    case.pop("generator_records")
    case.pop("bus_records")
    case.pop("branch_records")
    case["reference_generator_uid"] = "g1"
    generator_rows = [
        {"timestamp": key[0], "mode": key[1], **asdict(record)}
        for record in result.generator_records
    ]
    bus_rows = [
        {"timestamp": key[0], "mode": key[1], **asdict(record)}
        for record in result.bus_records
    ]
    branch_rows = [
        {"timestamp": key[0], "mode": key[1], **asdict(record)}
        for record in result.branch_records
    ]
    synthetic_context = SimpleNamespace(
        config={"ac_opf": {"voltage_limits_pu": [0.95, 1.05]}}
    )
    _validate_detail_aggregates(
        synthetic_context,
        {key: case},
        {key},
        generator_rows,
        bus_rows,
        branch_rows,
    )

    bus_rows[0]["vm_pu"] = 2.0
    with pytest.raises(RuntimeError, match="drifted"):
        _validate_detail_aggregates(
            synthetic_context,
            {key: case},
            {key},
            generator_rows,
            bus_rows,
            branch_rows,
        )
