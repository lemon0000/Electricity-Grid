import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import yaml
from pypower.api import ppoption, runpf
from pypower.idx_bus import BUS_TYPE
from pypower.idx_gen import GEN_BUS, GEN_STATUS, PG

from experiments.run_rts_gmlc_multi_poi_ac_replay import _load_candidate_dispatch
from experiments.run_rts_gmlc_multi_poi_ac_replay_slack_amended import (
    _configure_unambiguous_slack,
    _read_config,
    _reproduce_parent_slack_failure,
)
from experiments.run_rts_gmlc_multi_poi_ac_replay_timezone_amended import (
    _amended_context,
)
from src.grid.rts_gmlc_ac import (
    configure_rts_gmlc_ac_case,
    reconstruct_rts_gmlc_dc_flows,
    validate_rts_gmlc_ac_power_flow,
)

AMENDMENT_PATH = Path(
    "configs/rts_gmlc_google_day0_multi_poi_ac_replay_slack_amendment.yaml"
)
PARENT_CONFIG = Path("configs/rts_gmlc_google_day0_multi_poi_ac_replay.yaml")
PARENT_BATCH = Path(
    "results/tables/rts_gmlc_google_day0_multi_poi_ac_replay_v1/results"
)
CORRECTED_BATCH = Path(
    "results/tables/rts_gmlc_google_day0_multi_poi_ac_replay_v1/"
    "results_unambiguous_slack"
)
DEMONSTRATED_TIMESTAMP = "2020-01-01T18:00:00+00:00"
DEMONSTRATED_STATE = "branch_CA-1_immediate"


requires_parent_batch = pytest.mark.skipif(
    not (PARENT_BATCH / "SHA256SUMS").exists(),
    reason="Run the invalidated parent AC batch first",
)
requires_corrected_batch = pytest.mark.skipif(
    not (CORRECTED_BATCH / "SHA256SUMS").exists(),
    reason="Run the unambiguous-slack corrected AC batch first",
)


def test_slack_amendment_forbids_scientific_input_or_acceptance_changes():
    config = _read_config(AMENDMENT_PATH)

    assert config["observed_before_amendment"]["full_parent_batch_outcomes_observed"]
    assert config["observed_before_amendment"]["parent_batch_status"] == (
        "invalidated_for_final_ac_conclusions_retained_as_diagnostic"
    )
    assert config["scope"]["permitted_change"] == (
        "select_reference_bus_with_exactly_one_online_generator_and_that_"
        "generator_committable"
    )
    assert set(config["scope"]["forbidden_changes"]) >= {
        "representative_candidates",
        "hours_or_security_states",
        "power_factor_cases",
        "load_or_hvdc_mapping",
        "voltage_q_or_rating_assumptions",
        "power_flow_options",
        "q_limit_switching",
        "restoration_or_redispatch",
        "result_acceptance_or_summary_rules",
    }


def test_slack_amendment_rejects_power_flow_scope_creep(tmp_path):
    config = yaml.safe_load(AMENDMENT_PATH.read_text(encoding="utf-8"))
    config["scope"]["forbidden_changes"].remove("power_flow_options")
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="scope drifted"):
        _read_config(path)


@requires_parent_batch
def test_parent_slack_failure_is_mechanically_reproduced():
    reproduced = _reproduce_parent_slack_failure(PARENT_CONFIG)

    assert reproduced["reported_reference_generator_uid"] == "213_CC_3"
    assert reproduced["actual_slack_generator_uid"] == "213_RTPV_1"
    assert reproduced["actual_slack_adjustment_mw"] == pytest.approx(
        236.37316929152658,
        abs=1.0e-6,
    )
    assert reproduced["maximum_pg_deviation_mw"] == pytest.approx(
        236.37316929152658,
        abs=1.0e-6,
    )


@requires_corrected_batch
def test_corrected_batch_is_complete_pinned_and_retains_the_failed_security_gate():
    manifest_digest = hashlib.sha256(
        (CORRECTED_BATCH / "SHA256SUMS").read_bytes()
    ).hexdigest()
    assert manifest_digest == (
        "2b5b705d2074ddb8f846b7a8d897ed87d32021446fd867825b7dd3a0982e2a7e"
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
    converged = [row for row in rows if row["converged"] == "true"]
    normal = [row for row in rows if row["state_id"] == "normal"]

    assert len(rows) == len(keys) == 2304
    assert len(converged) == 2276
    assert sum(row["converged"] == "false" for row in rows) == 28
    assert not any(row["secure"] == "true" for row in rows)
    assert all(
        value.lower() not in {"nan", "inf", "-inf"}
        for row in rows
        for value in row.values()
    )
    assert (
        sum(float(row["max_voltage_violation_pu"]) > 1.0e-6 for row in converged)
        == 2276
    )
    assert (
        sum(
            float(row["max_reactive_power_violation_mvar"]) > 1.0e-4
            for row in converged
        )
        == 2276
    )
    assert (
        sum(
            float(row["max_branch_loading_fraction"]) > 1.0 + 1.0e-6
            for row in converged
        )
        == 642
    )
    assert (
        sum(float(row["max_active_power_violation_mw"]) > 1.0e-4 for row in converged)
        == 1509
    )
    assert max(float(row["max_non_slack_pg_deviation_mw"]) for row in converged) == 0.0
    assert len(normal) == 96
    assert all(row["converged"] == "true" for row in normal)
    assert all(float(row["max_voltage_violation_pu"]) > 1.0e-6 for row in normal)
    assert all(
        float(row["max_reactive_power_violation_mvar"]) > 1.0e-4 for row in normal
    )
    assert summary["case_count"] == 2304
    assert summary["converged_case_count"] == 2276
    assert summary["secure_case_count"] == 0
    assert summary["maximum_dc_flow_reconstruction_residual_mw"] <= 3.0e-9
    assert summary["maximum_non_slack_pg_deviation_mw"] == 0.0


@requires_parent_batch
def test_demonstrated_case_uses_the_configured_unique_committable_slack():
    context = _amended_context(PARENT_CONFIG)
    dispatch = _load_candidate_dispatch(context, 108)
    point = next(
        item
        for item in context.scan_context.business.points
        if item.timestamp.isoformat() == DEMONSTRATED_TIMESTAMP
    )
    metadata = dispatch.state_metadata[(DEMONSTRATED_TIMESTAMP, DEMONSTRATED_STATE)]
    generation = dispatch.security_generation[
        (DEMONSTRATED_TIMESTAMP, DEMONSTRATED_STATE)
    ]
    branch_flows = dispatch.security_branch_flows[
        (DEMONSTRATED_TIMESTAMP, DEMONSTRATED_STATE)
    ]
    commitment = dispatch.commitment_by_timestamp[DEMONSTRATED_TIMESTAMP]
    data_center_power = float(
        dispatch.hourly_by_timestamp[DEMONSTRATED_TIMESTAMP]["data_center_power_mw"]
    )
    total_demand = dict(point.demand_by_bus_mw)
    total_demand[108] += data_center_power
    dc_flows, residual = reconstruct_rts_gmlc_dc_flows(
        context.scan_context.data,
        demand_by_bus_mw=total_demand,
        generation_mw=generation,
        ac_branch_flows_mw=branch_flows,
        tolerance_mw=1.0e-6,
    )
    kwargs = {
        "generation_mw": generation,
        "commitment": commitment,
        "dc_bus": 108,
        "data_center_power_mw": data_center_power,
        "data_center_power_factor": 0.95,
        "dc_flows_mw": dc_flows,
        "outaged_branch_uid": metadata["element_uid"],
    }

    parent = configure_rts_gmlc_ac_case(
        context.template,
        context.scan_context.data,
        point,
        **kwargs,
    )
    configured = _configure_unambiguous_slack(
        context.template,
        context.scan_context.data,
        point,
        **kwargs,
    )

    assert residual <= 1.0e-6
    np.testing.assert_array_equal(configured.case["gen"], parent.case["gen"])
    np.testing.assert_array_equal(configured.case["branch"], parent.case["branch"])
    np.testing.assert_array_equal(
        np.delete(configured.case["bus"], BUS_TYPE, axis=1),
        np.delete(parent.case["bus"], BUS_TYPE, axis=1),
    )
    reference_row = context.template.generator_row_by_uid[
        configured.reference_generator_uid
    ]
    online_at_reference_bus = np.flatnonzero(
        (configured.case["gen"][:, GEN_STATUS] > 0.0)
        & (configured.case["gen"][:, GEN_BUS] == configured.reference_bus)
    )
    committable = {
        generator.uid
        for generator in context.scan_context.data.generators
        if generator.dispatch_mode == "committable"
    }
    assert online_at_reference_bus.tolist() == [reference_row]
    assert configured.reference_generator_uid in committable

    solved, success = runpf(
        configured.case,
        ppoption(
            VERBOSE=0,
            OUT_ALL=0,
            PF_ALG=1,
            PF_TOL=1.0e-8,
            PF_MAX_IT=20,
            ENFORCE_Q_LIMS=0,
        ),
    )
    assert success
    pg_deviation = np.abs(
        solved["gen"][:, PG] - np.asarray(configured.target_generation_mw_by_row)
    )
    assert pg_deviation[reference_row] > 1.0e-6
    assert int(np.argmax(pg_deviation)) == reference_row
    assert np.max(np.delete(pg_deviation, reference_row)) <= 1.0e-6

    result = validate_rts_gmlc_ac_power_flow(
        context.template,
        configured,
        branch_rating=metadata["branch_rating"],
    )
    assert result.converged
    assert result.reference_generator_uid == configured.reference_generator_uid
    assert result.max_non_slack_pg_deviation_mw <= 1.0e-6
