import copy
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import yaml
from pypower.idx_bus import BUS_I, BUS_TYPE, PV, REF
from pypower.idx_gen import GEN_BUS, GEN_STATUS, QMAX, QMIN, VG

from experiments.run_rts_gmlc_multi_poi_ac_replay_voltage_control_amended import (
    _CONTROLLER_TOLERANCE,
    _case_keys,
    _demonstrated_configurations,
    _harmonize_online_q_controller_vg,
    _read_config,
    _reproduce_parent_voltage_control_failure,
    _require_exact_case_scope,
    _require_finite_rows,
    _require_non_slack_pg_control,
)

AMENDMENT_PATH = Path(
    "configs/rts_gmlc_google_day0_multi_poi_ac_replay_" "voltage_control_amendment.yaml"
)
PARENT_CONFIG = Path("configs/rts_gmlc_google_day0_multi_poi_ac_replay.yaml")
PARENT_BATCH = Path(
    "results/tables/rts_gmlc_google_day0_multi_poi_ac_replay_v1/"
    "results_unambiguous_slack"
)
CORRECTED_BATCH = Path(
    "results/tables/rts_gmlc_google_day0_multi_poi_ac_replay_v1/"
    "results_q_capable_voltage_control"
)

requires_parent_batch = pytest.mark.skipif(
    not (PARENT_BATCH / "SHA256SUMS").exists(),
    reason="Run the unambiguous-slack parent AC batch first",
)
requires_corrected_batch = pytest.mark.skipif(
    not (CORRECTED_BATCH / "SHA256SUMS").exists(),
    reason="Run the q-capable voltage-control corrected AC batch first",
)


@pytest.fixture(scope="module")
def probe_cases():
    return _demonstrated_configurations(PARENT_CONFIG)


def test_voltage_control_amendment_freezes_only_the_q_inert_vg_mapping():
    config = _read_config(AMENDMENT_PATH)

    observed = config["observed_before_amendment"]
    assert observed["full_parent_batch_outcomes_observed"]
    assert observed["voltage_control_corrected_probe_outcomes_observed_before_freeze"]
    assert not observed["full_voltage_control_corrected_batch_outcomes_observed"]
    assert observed["parent_batch_status"] == (
        "invalidated_for_final_ac_outcome_conclusions_retained_as_diagnostic"
    )
    assert config["scope"]["permitted_change"] == (
        "copy_unique_online_q_capable_source_vg_to_colocated_online_q_inert_"
        "rows_at_pv_or_ref_buses"
    )
    assert set(config["scope"]["forbidden_changes"]) >= {
        "generator_active_power_or_commitment",
        "generator_q_limits",
        "q_capable_controller_source_vg",
        "bus_vm_or_va_initial_values",
        "bus_type_or_slack_selection",
        "power_flow_options",
        "q_limit_switching",
        "restoration_or_redispatch",
        "result_acceptance_or_summary_rules",
    }


def test_voltage_control_amendment_rejects_scope_creep(tmp_path):
    config = yaml.safe_load(AMENDMENT_PATH.read_text(encoding="utf-8"))
    config["scope"]["forbidden_changes"].remove("generator_q_limits")
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="scope drifted"):
        _read_config(path)


@requires_parent_batch
def test_parent_voltage_control_failure_and_disclosed_probe_are_reproduced():
    reproduced = _reproduce_parent_voltage_control_failure(PARENT_CONFIG)

    assert reproduced["control_bus"] == 314
    assert reproduced["controller_generator_uid"] == "314_SYNC_COND_1"
    assert reproduced["controller_source_vg_pu"] == pytest.approx(1.05)
    assert reproduced["q_inert_source_vg_pu"] == pytest.approx(1.0)
    assert reproduced["parent_solved_control_bus_voltage_pu"] == pytest.approx(1.0)
    assert reproduced["parent_controller_q_mvar"] == pytest.approx(
        -102.20498757079912,
        abs=1.0e-8,
    )
    assert reproduced["parent_controller_q_limit_violation_mvar"] == pytest.approx(
        52.20498757079912,
        abs=1.0e-8,
    )
    assert reproduced["amended_probe_solved_control_bus_voltage_pu"] == pytest.approx(
        1.05,
    )
    assert reproduced["amended_probe_controller_q_mvar"] == pytest.approx(
        9.163432253344993,
        abs=1.0e-8,
    )
    assert reproduced["amended_probe_max_reactive_power_violation_mvar"] == (
        pytest.approx(26.49335061366679, abs=1.0e-8)
    )
    assert (
        reproduced["amended_probe_max_reactive_power_violation_generator_uid"]
        == "116_STEAM_1"
    )
    assert reproduced["amended_probe_max_voltage_violation_pu"] == pytest.approx(
        0.05714149350909459,
        abs=1.0e-8,
    )
    assert reproduced["amended_probe_secure"] is False


@requires_parent_batch
def test_amendment_changes_only_online_q_inert_vg_cells(probe_cases):
    context, parent, amended = probe_cases
    parent_gen = parent.case["gen"]
    amended_gen = amended.case["gen"]

    np.testing.assert_array_equal(amended.case["bus"], parent.case["bus"])
    np.testing.assert_array_equal(amended.case["branch"], parent.case["branch"])
    np.testing.assert_array_equal(
        np.delete(amended_gen, VG, axis=1),
        np.delete(parent_gen, VG, axis=1),
    )
    assert amended.target_generation_mw_by_row == parent.target_generation_mw_by_row
    assert amended.active_generator_uids == parent.active_generator_uids
    assert amended.reference_bus == parent.reference_bus
    assert amended.reference_generator_uid == parent.reference_generator_uid
    assert amended.native_reactive_demand_mvar == parent.native_reactive_demand_mvar
    assert amended.data_center_reactive_demand_mvar == (
        parent.data_center_reactive_demand_mvar
    )
    assert amended.dc_flow_mw == parent.dc_flow_mw

    changed_rows = np.flatnonzero(parent_gen[:, VG] != amended_gen[:, VG])
    changed_buses = set()
    for row in changed_rows:
        bus_uid = int(parent_gen[row, GEN_BUS])
        changed_buses.add(bus_uid)
        bus_row = context.template.bus_row_by_uid[bus_uid]
        assert parent_gen[row, GEN_STATUS] > 0.0
        assert parent_gen[row, QMAX] - parent_gen[row, QMIN] <= _CONTROLLER_TOLERANCE
        assert int(parent.case["bus"][bus_row, BUS_TYPE]) in (PV, REF)
    assert len(changed_rows) == 12
    assert changed_buses == {101, 102, 122, 215, 314}


@requires_parent_batch
def test_every_controlled_bus_has_one_effective_online_controller_vg(probe_cases):
    _context, _parent, amended = probe_cases
    bus = amended.case["bus"]
    generator = amended.case["gen"]

    controlled_count = 0
    for bus_row in range(len(bus)):
        if int(bus[bus_row, BUS_TYPE]) not in (PV, REF):
            continue
        controlled_count += 1
        bus_uid = int(bus[bus_row, BUS_I])
        online = np.flatnonzero(
            (generator[:, GEN_STATUS] > 0.0) & (generator[:, GEN_BUS] == bus_uid)
        )
        controllers = [
            row
            for row in online
            if generator[row, QMAX] - generator[row, QMIN] > _CONTROLLER_TOLERANCE
        ]
        assert controllers
        assert len({float(generator[row, VG]) for row in controllers}) == 1
        assert len({float(generator[row, VG]) for row in online}) == 1
    assert controlled_count > 0


@requires_parent_batch
def test_missing_or_conflicting_online_q_controller_fails_before_power_flow(
    probe_cases,
):
    context, parent, _amended = probe_cases
    bus_uid = 101
    generator_rows = [
        row
        for row in range(len(parent.case["gen"]))
        if parent.case["gen"][row, GEN_STATUS] > 0.0
        and int(parent.case["gen"][row, GEN_BUS]) == bus_uid
    ]
    controller_rows = [
        row
        for row in generator_rows
        if parent.case["gen"][row, QMAX] - parent.case["gen"][row, QMIN]
        > _CONTROLLER_TOLERANCE
    ]
    assert len(controller_rows) >= 2

    conflicting = copy.deepcopy(parent)
    conflicting.case["gen"][controller_rows[-1], VG] += 0.01
    with pytest.raises(RuntimeError, match="ambiguous controller VG"):
        _harmonize_online_q_controller_vg(
            conflicting,
            tolerance=_CONTROLLER_TOLERANCE,
        )

    missing = copy.deepcopy(parent)
    for row in generator_rows:
        missing.case["gen"][row, QMAX] = missing.case["gen"][row, QMIN]
    with pytest.raises(RuntimeError, match=f"controlled bus {bus_uid} has no"):
        _harmonize_online_q_controller_vg(
            missing,
            tolerance=_CONTROLLER_TOLERANCE,
        )
    assert context.template.bus_row_by_uid[bus_uid] >= 0


def test_batch_publication_audits_reject_nonfinite_scope_and_non_slack_drift():
    rows = [
        {
            "dc_bus": 120,
            "power_factor_case": "unity",
            "timestamp": "2020-01-01T00:00:00+00:00",
            "state_id": "normal",
            "converged": True,
            "max_non_slack_pg_deviation_mw": 0.0,
            "metric": 1.0,
        },
        {
            "dc_bus": 108,
            "power_factor_case": "lagging_095",
            "timestamp": "2020-01-01T01:00:00+00:00",
            "state_id": "branch_A",
            "converged": False,
            "max_non_slack_pg_deviation_mw": None,
            "metric": None,
        },
    ]
    expected = _case_keys(rows)

    _require_finite_rows(rows)
    _require_exact_case_scope(rows, expected_keys=expected)
    _require_non_slack_pg_control(rows)

    nonfinite = copy.deepcopy(rows)
    nonfinite[0]["metric"] = float("nan")
    with pytest.raises(RuntimeError, match="is not finite"):
        _require_finite_rows(nonfinite)

    with pytest.raises(RuntimeError, match="batch scope drifted"):
        _require_exact_case_scope(rows, expected_keys={next(iter(expected))})

    non_slack = copy.deepcopy(rows)
    non_slack[0]["max_non_slack_pg_deviation_mw"] = 1.1e-6
    with pytest.raises(RuntimeError, match="non-slack PG drift"):
        _require_non_slack_pg_control(non_slack)


@requires_corrected_batch
def test_voltage_control_corrected_batch_is_complete_and_pinned():
    manifest_digest = hashlib.sha256(
        (CORRECTED_BATCH / "SHA256SUMS").read_bytes()
    ).hexdigest()
    assert manifest_digest == (
        "ee4894bba4e65433ffed4b31e4d96c78035bd2413dd4fa6accb3eb9f16c0609a"
    )
    with (CORRECTED_BATCH / "ac_replay_cases.csv").open(
        "r", encoding="utf-8", newline=""
    ) as source:
        rows = list(csv.DictReader(source))
    summary = json.loads((CORRECTED_BATCH / "summary.json").read_text(encoding="utf-8"))
    keys = {
        (
            row["dc_bus"],
            row["power_factor_case"],
            row["timestamp"],
            row["state_id"],
        )
        for row in rows
    }
    with (PARENT_BATCH / "ac_replay_cases.csv").open(
        "r", encoding="utf-8", newline=""
    ) as source:
        parent_rows = list(csv.DictReader(source))
    parent_keys = {
        (
            row["dc_bus"],
            row["power_factor_case"],
            row["timestamp"],
            row["state_id"],
        )
        for row in parent_rows
    }
    converged = [row for row in rows if row["converged"] == "true"]
    normal = [row for row in rows if row["state_id"] == "normal"]

    assert len(rows) == len(keys) == len(parent_keys) == 2304
    assert keys == parent_keys
    assert len(converged) == 2296
    assert sum(row["converged"] == "false" for row in rows) == 8
    assert not any(row["secure"] == "true" for row in rows)
    assert all(
        value.lower() not in {"nan", "inf", "-inf"}
        for row in rows
        for value in row.values()
    )
    assert (
        max(float(row["max_non_slack_pg_deviation_mw"]) for row in converged) <= 1.0e-6
    )
    assert (
        sum(float(row["max_voltage_violation_pu"]) > 1.0e-6 for row in converged)
        == 2296
    )
    assert (
        sum(
            float(row["max_reactive_power_violation_mvar"]) > 1.0e-4
            for row in converged
        )
        == 2217
    )
    assert len(normal) == 96
    assert all(row["converged"] == "true" for row in normal)
    assert not any(row["secure"] == "true" for row in normal)
    assert all(float(row["max_voltage_violation_pu"]) > 1.0e-6 for row in normal)
    assert summary["case_count"] == 2304
    assert summary["converged_case_count"] == 2296
    assert summary["secure_case_count"] == 0
    assert summary["all_cases_reported"]
    assert summary["maximum_dc_flow_reconstruction_residual_mw"] <= 1.0e-6
    assert summary["all_converged_cases_pass_non_slack_pg_audit"]
