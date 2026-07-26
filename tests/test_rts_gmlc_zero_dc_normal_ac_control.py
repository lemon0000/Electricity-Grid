import copy
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from experiments.run_rts_gmlc_multi_poi_ac_replay import _load_candidate_dispatch
from experiments.run_rts_gmlc_zero_dc_normal_ac_control import (
    _AC_FINITE_FIELDS,
    _AC_NULLABLE_FINITE_FIELDS,
    _CASE_SCOPE,
    _HOURLY_ZERO_FIELDS,
    _POWER_FLOW,
    _ZERO_CONTROL,
    _build_context,
    _configure_q_capable_voltage_control,
    _read_config,
    _require_ac_case_numerics,
    _require_finite_fields,
    _require_non_slack_pg_control,
    _validate_and_index_zero_dispatch,
    _zero_business,
    _zero_request,
    prepare_preregistration,
)

CONFIG = Path("configs/rts_gmlc_google_day0_zero_dc_normal_ac_control.yaml")
OUTPUT_ROOT = Path("results/tables/rts_gmlc_google_day0_zero_dc_normal_ac_control_v1")

requires_zero_artifacts = pytest.mark.skipif(
    not (OUTPUT_ROOT / "ac_normal" / "SHA256SUMS").exists(),
    reason="Run the zero-data-center DC and normal-state AC control first",
)


@pytest.fixture(scope="module")
def context():
    return _build_context(CONFIG)


def test_zero_dc_config_freezes_a_nonblind_reoptimized_control():
    config = _read_config(CONFIG)

    assert config["preregistration"]["parent_treatment_outcomes_observed"]
    assert not config["preregistration"]["zero_control_outcomes_observed"]
    assert config["zero_control"]["connected_capacity_mw"] == 0.0
    assert config["zero_control"]["fixed_treatment_commitment_used"] is False
    assert config["zero_control"]["common_selected_n_minus_one_states_retained"]
    assert config["case_scope"]["expected_unique_ac_cases"] == 24
    assert config["case_scope"]["ac_security_states"] == "normal_only"
    assert config["ac_assumptions"]["colocated_q_inert_vg_normalized"]
    assert config["ac_assumptions"]["voltage_control_target"] == (
        "common_online_q_capable_generator_vg"
    )
    assert config["power_flow"]["non_slack_pg_audit_tolerance_mw"] == 1.0e-6
    assert not config["ac_assumptions"]["q_limit_switching"]
    assert not config["ac_assumptions"]["restoration_or_redispatch"]


def test_zero_dc_config_rejects_a_fixed_treatment_commitment_scope_change(tmp_path):
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    config["zero_control"]["fixed_treatment_commitment_used"] = True
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="zero_control drifted"):
        _read_config(path)


def test_zero_transform_preserves_clock_and_zeroes_every_business_power_field(context):
    zero = _zero_business(context.scan.business)

    assert len(zero.points) == 24
    for source, changed in zip(context.scan.business.points, zero.points):
        assert changed.timestamp == source.timestamp
        assert changed.period == source.period
        for field in _ZERO_CONTROL["zero_fields"]:
            assert getattr(changed, field) == 0.0
    request = _zero_request(context)
    assert request.dc_bus == _ZERO_CONTROL["dc_bus_api_placeholder"]
    assert all(value == 0.0 for value in request.dc_requested_mw)
    assert all(value == 0.0 for value in request.dc_connected_capacity_mw)
    assert request.system_demand_by_bus_mw == tuple(
        point.demand_by_bus_mw for point in context.scan.data.hourly_points[:24]
    )
    assert (
        tuple(context.common_security["common_security_contract"]["state_ids"])[0]
        == "normal"
    )
    assert len(context.common_security["common_security_contract"]["state_ids"]) == 24


def test_zero_request_is_identical_for_the_two_former_poi_placeholders(context):
    bus_108 = _zero_request(context, dc_bus=108)
    bus_120 = _zero_request(context, dc_bus=120)

    assert bus_108.dc_requested_mw == bus_120.dc_requested_mw
    assert bus_108.system_demand_by_bus_mw == bus_120.system_demand_by_bus_mw
    assert bus_108.generator_availability == bus_120.generator_availability


def test_zero_ac_configuration_is_invariant_to_placeholder_bus_and_pf(context):
    dispatch = _load_candidate_dispatch(context.ac, 120)
    timestamp = dispatch.timestamps[0]
    point = context.ac.scan_context.business.points[0]
    generation = dispatch.normal_generation[timestamp]
    commitment = dispatch.commitment_by_timestamp[timestamp]
    configured = []
    for dc_bus in (108, 120):
        for power_factor in (1.0, 0.95):
            configured.append(
                _configure_q_capable_voltage_control(
                    context.ac.template,
                    context.ac.scan_context.data,
                    point,
                    generation_mw=generation,
                    commitment=commitment,
                    dc_bus=dc_bus,
                    data_center_power_mw=0.0,
                    data_center_power_factor=power_factor,
                    dc_flows_mw={"DC1": 0.0},
                )
            )

    first = configured[0]
    assert _CASE_SCOPE["power_factor_case"] == "not_applicable_zero_active_power"
    assert all(item.data_center_reactive_demand_mvar == 0.0 for item in configured)
    for item in configured[1:]:
        np.testing.assert_array_equal(item.case["bus"], first.case["bus"])
        np.testing.assert_array_equal(item.case["gen"], first.case["gen"])
        np.testing.assert_array_equal(item.case["branch"], first.case["branch"])
        assert item.reference_bus == first.reference_bus
        assert item.reference_generator_uid == first.reference_generator_uid


def _synthetic_zero_dispatch_rows():
    timestamps = ("2020-01-01T00:00:00+00:00", "2020-01-01T01:00:00+00:00")
    native = (100.0, 110.0)
    hourly = []
    for timestamp, demand in zip(timestamps, native):
        row = {
            "timestamp": timestamp,
            "native_grid_demand_mw": demand,
            "total_demand_mw": demand,
            "network_losses_mw": 0.0,
            "total_generation_mw": demand,
            "generation_balance_residual_mw": 0.0,
            "committed_thermal_units": 1,
            "spin_requirement_mw": 0.0,
            "spin_provided_mw": 0.0,
            "maximum_normal_branch_loading_fraction": 0.5,
            "hvdc_dc1_flow_mw": 0.0,
            "commitment_feasible": True,
            "ramp_feasible": True,
            "reserve_feasible": True,
            "normal_secure": True,
            "selected_contingencies_secure": True,
        }
        row.update({field: 0.0 for field in _HOURLY_ZERO_FIELDS})
        hourly.append(row)
    generators = [
        {
            "timestamp": timestamp,
            "generator_uid": uid,
            "bus": 101,
            "commitment": commitment,
            "generation_mw": 50.0,
            "minimum_mw": 0.0,
            "maximum_mw": 100.0,
            "spin_up_mw": 0.0,
        }
        for timestamp in timestamps
        for uid, commitment in (("G1", "true"), ("G2", "false"))
    ]
    branches = [
        {
            "timestamp": timestamp,
            "branch_uid": uid,
            "from_bus": 101,
            "to_bus": 102,
            "flow_mw": 10.0,
            "continuous_rating_mw": 100.0,
            "loading_fraction": 0.1,
        }
        for timestamp in timestamps
        for uid in ("B1", "B2")
    ]
    security = [
        {
            "timestamp": timestamp,
            "state_id": state_id,
            "total_generation_mw": demand,
            "maximum_branch_loading_fraction": 0.5,
            "maximum_branch_rating_violation_mw": 0.0,
            "outaged_element_output_mw": 0.0,
        }
        for timestamp, demand in zip(timestamps, native)
        for state_id in ("normal", "branch_A")
    ]
    security_generators = [
        {
            "timestamp": timestamp,
            "state_id": "branch_A",
            "generator_uid": uid,
            "generation_mw": 50.0,
        }
        for timestamp in timestamps
        for uid in ("G1", "G2")
    ]
    security_branches = [
        {
            "timestamp": timestamp,
            "state_id": "branch_A",
            "branch_uid": uid,
            "flow_mw": 10.0,
            "rating_mw": 100.0,
            "loading_fraction": 0.1,
        }
        for timestamp in timestamps
        for uid in ("B1", "B2")
    ]
    return (
        timestamps,
        native,
        hourly,
        generators,
        branches,
        security,
        security_generators,
        security_branches,
    )


def _validate_synthetic_zero_dispatch(
    hourly,
    generators,
    branches,
    security=None,
    security_generators=None,
    security_branches=None,
):
    (
        timestamps,
        native,
        _hourly,
        _generators,
        _branches,
        default_security,
        default_security_generators,
        default_security_branches,
    ) = _synthetic_zero_dispatch_rows()
    return _validate_and_index_zero_dispatch(
        hourly_rows=hourly,
        generator_rows=generators,
        branch_rows=branches,
        security_rows=default_security if security is None else security,
        security_generator_rows=(
            default_security_generators
            if security_generators is None
            else security_generators
        ),
        security_branch_rows=(
            default_security_branches
            if security_branches is None
            else security_branches
        ),
        expected_timestamps=timestamps,
        expected_native_demand_mw=native,
        generator_uids=frozenset({"G1", "G2"}),
        branch_uids=frozenset({"B1", "B2"}),
        expected_state_ids=("normal", "branch_A"),
        tolerance_mw=1.0e-6,
    )


def test_zero_dispatch_artifact_contract_rejects_coverage_and_numeric_drift():
    (
        _timestamps,
        _native,
        hourly,
        generators,
        branches,
        security,
        security_generators,
        security_branches,
    ) = _synthetic_zero_dispatch_rows()
    generation, commitment, flows = _validate_synthetic_zero_dispatch(
        hourly,
        generators,
        branches,
    )
    assert generation[hourly[0]["timestamp"]]["G1"] == 50.0
    assert commitment[hourly[0]["timestamp"]]["G2"] is False
    assert flows[hourly[1]["timestamp"]]["B2"] == 10.0

    duplicate = copy.deepcopy(generators)
    duplicate.append(copy.deepcopy(duplicate[0]))
    with pytest.raises(RuntimeError, match="duplicate generator"):
        _validate_synthetic_zero_dispatch(hourly, duplicate, branches)

    bad_timestamps = copy.deepcopy(hourly)
    bad_timestamps[1]["timestamp"] = "2020-01-02T00:00:00+00:00"
    with pytest.raises(RuntimeError, match="timestamp coverage"):
        _validate_synthetic_zero_dispatch(bad_timestamps, generators, branches)

    nonzero = copy.deepcopy(hourly)
    nonzero[0]["data_center_recovery_power_mw"] = 1.0e-9
    with pytest.raises(RuntimeError, match="power field is not zero"):
        _validate_synthetic_zero_dispatch(nonzero, generators, branches)

    native_drift = copy.deepcopy(hourly)
    native_drift[0]["native_grid_demand_mw"] += 1.0
    with pytest.raises(RuntimeError, match="native demand drifted"):
        _validate_synthetic_zero_dispatch(native_drift, generators, branches)

    residual_drift = copy.deepcopy(hourly)
    residual_drift[0]["generation_balance_residual_mw"] = 1.1e-6
    with pytest.raises(RuntimeError, match="generation balance residual drifted"):
        _validate_synthetic_zero_dispatch(residual_drift, generators, branches)

    insecure = copy.deepcopy(hourly)
    insecure[0]["selected_contingencies_secure"] = False
    with pytest.raises(RuntimeError, match="feasibility flag is false"):
        _validate_synthetic_zero_dispatch(insecure, generators, branches)

    nonfinite = copy.deepcopy(branches)
    nonfinite[0]["flow_mw"] = float("nan")
    with pytest.raises(RuntimeError, match="is not finite"):
        _validate_synthetic_zero_dispatch(hourly, generators, nonfinite)

    missing_security = copy.deepcopy(security[:-1])
    with pytest.raises(RuntimeError, match="security audit coverage"):
        _validate_synthetic_zero_dispatch(
            hourly,
            generators,
            branches,
            security=missing_security,
        )

    security_violation = copy.deepcopy(security)
    security_violation[0]["maximum_branch_rating_violation_mw"] = 1.1e-6
    with pytest.raises(RuntimeError, match="security audit violation"):
        _validate_synthetic_zero_dispatch(
            hourly,
            generators,
            branches,
            security=security_violation,
        )

    with pytest.raises(RuntimeError, match="security generator coverage"):
        _validate_synthetic_zero_dispatch(
            hourly,
            generators,
            branches,
            security_generators=security_generators[:-1],
        )

    with pytest.raises(RuntimeError, match="security branch coverage"):
        _validate_synthetic_zero_dispatch(
            hourly,
            generators,
            branches,
            security_branches=security_branches[:-1],
        )


def test_ac_publication_audits_reject_nonfinite_and_non_slack_drift():
    rows = [
        {
            "converged": True,
            "max_non_slack_pg_deviation_mw": 1.0e-6,
            "metric": 1.0,
        },
        {
            "converged": False,
            "max_non_slack_pg_deviation_mw": None,
            "metric": None,
        },
    ]
    _require_finite_fields(
        rows,
        ("metric",),
        label="test AC",
        nullable_fields=frozenset({"metric"}),
    )
    _require_non_slack_pg_control(
        rows,
        tolerance_mw=float(_POWER_FLOW["non_slack_pg_audit_tolerance_mw"]),
    )

    nonfinite = copy.deepcopy(rows)
    nonfinite[0]["metric"] = float("inf")
    with pytest.raises(RuntimeError, match="is not finite"):
        _require_finite_fields(
            nonfinite,
            ("metric",),
            label="test AC",
            nullable_fields=frozenset({"metric"}),
        )

    drift = copy.deepcopy(rows)
    drift[0]["max_non_slack_pg_deviation_mw"] = 1.1e-6
    with pytest.raises(RuntimeError, match="non-slack PG drift"):
        _require_non_slack_pg_control(drift, tolerance_mw=1.0e-6)

    converged_missing = {field: 0.0 for field in _AC_FINITE_FIELDS}
    converged_missing["converged"] = True
    converged_missing["min_voltage_pu"] = None
    with pytest.raises(RuntimeError, match="converged AC case 0 is missing metrics"):
        _require_ac_case_numerics([converged_missing])

    nonconverged = {field: 0.0 for field in _AC_FINITE_FIELDS}
    nonconverged["converged"] = False
    for field in _AC_NULLABLE_FINITE_FIELDS:
        nonconverged[field] = None
    _require_ac_case_numerics([nonconverged])


def test_prepare_preregistration_is_atomic_and_reproducible(tmp_path):
    first = prepare_preregistration(CONFIG, output_directory=tmp_path)
    second = prepare_preregistration(CONFIG, output_directory=tmp_path)

    assert first == second
    assert first["input_contract_sha256"]
    assert first["zero_control_outcomes_observed"] is False
    assert (tmp_path / "preregistration" / "SHA256SUMS").exists()
    assert (tmp_path / "preregistration" / "config.yaml").read_bytes() == (
        CONFIG.read_bytes()
    )


@requires_zero_artifacts
def test_zero_control_artifacts_are_complete_pinned_and_fail_the_direct_ac_gate():
    manifest_hashes = {
        name: hashlib.sha256(
            (OUTPUT_ROOT / name / "SHA256SUMS").read_bytes()
        ).hexdigest()
        for name in ("preregistration", "dc_dispatch", "ac_normal")
    }
    assert manifest_hashes == {
        "preregistration": (
            "ee456378a822f0a97461546a385c1230d6d40e82920399599e4050f0ef812ec8"
        ),
        "dc_dispatch": (
            "c7c5cb7f418382472f2adf949e62ce4e1abb399dfe906903bacc24037d40ca4d"
        ),
        "ac_normal": (
            "68aaa104312d7ef9966649e31759a59cd874eadf5fedab1147728ace9b8b68a6"
        ),
    }
    registration = json.loads(
        (OUTPUT_ROOT / "preregistration" / "registration.json").read_text(
            encoding="utf-8"
        )
    )
    dc_summary = json.loads(
        (OUTPUT_ROOT / "dc_dispatch" / "summary.json").read_text(encoding="utf-8")
    )
    ac_summary = json.loads(
        (OUTPUT_ROOT / "ac_normal" / "summary.json").read_text(encoding="utf-8")
    )
    with (OUTPUT_ROOT / "dc_dispatch" / "hourly_dispatch.csv").open(
        "r", encoding="utf-8", newline=""
    ) as source:
        hourly = list(csv.DictReader(source))
    with (OUTPUT_ROOT / "dc_dispatch" / "security_audit.csv").open(
        "r", encoding="utf-8", newline=""
    ) as source:
        security = list(csv.DictReader(source))
    with (OUTPUT_ROOT / "ac_normal" / "ac_normal_cases.csv").open(
        "r", encoding="utf-8", newline=""
    ) as source:
        ac_rows = list(csv.DictReader(source))

    assert registration["input_contract_sha256"] == (
        "ea17c09e2dde55aef9f1376dc3670e1d32e1f8fd1af0426382af64c293bc3cd9"
    )
    assert dc_summary["hours"] == 24
    assert dc_summary["security_state_count_per_hour"] == 24
    assert dc_summary["all_data_center_power_fields_zero"]
    assert dc_summary["dispatch_artifact_contract_validated"]
    assert dc_summary["constraint_generation_audit"]["converged"]
    assert dc_summary["constraint_generation_audit"]["certified_relative_gap"] <= (
        1.0e-6
    )
    assert dc_summary["fixed_commitment_ed_audit"]["absolute_gap_usd"] == 0.0
    assert dc_summary["residual_audit"]["maximum_balance_residual_mw"] == 0.0
    assert len(hourly) == len({row["timestamp"] for row in hourly}) == 24
    assert len(security) == 24 * 24
    assert all(
        float(row[field]) == 0.0 for row in hourly for field in _HOURLY_ZERO_FIELDS
    )
    assert all(
        row[field] == "true"
        for row in hourly
        for field in (
            "commitment_feasible",
            "ramp_feasible",
            "reserve_feasible",
            "normal_secure",
            "selected_contingencies_secure",
        )
    )

    assert ac_summary["dc_dispatch_manifest_sha256"] == manifest_hashes["dc_dispatch"]
    assert ac_summary["case_count"] == ac_summary["converged_case_count"] == 24
    assert ac_summary["not_converged_case_count"] == 0
    assert ac_summary["secure_case_count"] == 0
    assert ac_summary["voltage_violation_count"] == 24
    assert ac_summary["reactive_power_violation_count"] == 24
    assert ac_summary["active_power_violation_count"] == 10
    assert ac_summary["branch_loading_violation_count"] == 11
    assert ac_summary["maximum_non_slack_pg_deviation_mw"] == 0.0
    assert ac_summary["maximum_dc_flow_reconstruction_residual_mw"] <= 2.0e-9
    assert len(ac_rows) == len({row["timestamp"] for row in ac_rows}) == 24
    assert all(row["converged"] == "true" for row in ac_rows)
    assert not any(row["secure"] == "true" for row in ac_rows)
    assert all(float(row["max_voltage_violation_pu"]) > 1.0e-6 for row in ac_rows)
    assert all(
        float(row["max_reactive_power_violation_mvar"]) > 1.0e-4 for row in ac_rows
    )
    assert all(
        value.lower() not in {"nan", "inf", "-inf"}
        for row in ac_rows
        for value in row.values()
    )
