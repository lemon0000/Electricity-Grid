import csv
import hashlib
from math import acos, tan
from pathlib import Path

import pytest
from pypower.idx_brch import BR_STATUS, RATE_A, RATE_B, RATE_C
from pypower.idx_bus import PD, QD
from pypower.idx_gen import GEN_STATUS

from experiments.run_rts_gmlc_multi_poi_scan import _build_scan_context
from src.grid.rts_gmlc_ac import (
    configure_rts_gmlc_ac_case,
    load_rts_gmlc_ac_template,
    reconstruct_rts_gmlc_dc_flows,
    validate_rts_gmlc_ac_power_flow,
)

SCAN_CONFIG = Path("configs/rts_gmlc_google_day0_multi_poi_scan.yaml")
UPSTREAM_ROOT = Path("data/raw/rts_gmlc/v0.2.3/upstream")
AC_REFERENCE = Path("data/raw/rts_gmlc/v0.2.3/ac_reference/RTS_GMLC.m")
BUS_108_RESULT = Path(
    "results/tables/rts_gmlc_google_day0_multi_poi_selected_n1_dc_scuc_v1/"
    "candidates/bus_108"
)


requires_ac_inputs = pytest.mark.skipif(
    not UPSTREAM_ROOT.exists() or not AC_REFERENCE.exists(),
    reason="Fetch the pinned RTS-GMLC source and AC reference first",
)
requires_bus_108 = pytest.mark.skipif(
    not (BUS_108_RESULT / "summary.json").exists(),
    reason="Run the pre-registered multi-POI scan first",
)


def _rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


@requires_ac_inputs
def test_ac_template_matches_the_pinned_source_and_public_conversion_conventions():
    template = load_rts_gmlc_ac_template(UPSTREAM_ROOT)

    assert hashlib.sha256(AC_REFERENCE.read_bytes()).hexdigest() == (
        "10573aee70f793c28a0602516f85c4345e6f171512852f1162c3bb3b02ba575b"
    )
    assert template.source_reference_bus == 113
    assert template.case_template["bus"].shape == (73, 13)
    assert template.case_template["gen"].shape == (158, 21)
    assert template.case_template["branch"].shape == (120, 13)
    a1 = template.case_template["branch"][template.branch_row_by_uid["A1"]]
    assert tuple(a1[[RATE_A, RATE_B, RATE_C]]) == (175.0, 193.0, 200.0)
    assert template.dc_branch_endpoints == {"DC1": (113, 316)}
    assert template.dc_branch_limit_mw == {"DC1": 100.0}


@requires_ac_inputs
@requires_bus_108
def test_saved_nodal_balances_reconstruct_hvdc_and_configure_reactive_assumptions():
    context = _build_scan_context(SCAN_CONFIG)
    template = load_rts_gmlc_ac_template(UPSTREAM_ROOT)
    hourly = _rows(BUS_108_RESULT / "hourly_dispatch.csv")[0]
    timestamp = hourly["timestamp"]
    generator_rows = [
        row
        for row in _rows(BUS_108_RESULT / "generator_dispatch.csv")
        if row["timestamp"] == timestamp
    ]
    branch_rows = [
        row
        for row in _rows(BUS_108_RESULT / "normal_branch_flows.csv")
        if row["timestamp"] == timestamp
    ]
    generation = {
        row["generator_uid"]: float(row["generation_mw"]) for row in generator_rows
    }
    commitment = {
        row["generator_uid"]: row["commitment"] == "true" for row in generator_rows
    }
    branch_flows = {row["branch_uid"]: float(row["flow_mw"]) for row in branch_rows}
    point = context.data.hourly_points[0]
    data_center_power = float(hourly["data_center_power_mw"])
    total_demand = dict(point.demand_by_bus_mw)
    total_demand[108] += data_center_power

    dc_flows, residual = reconstruct_rts_gmlc_dc_flows(
        context.data,
        demand_by_bus_mw=total_demand,
        generation_mw=generation,
        ac_branch_flows_mw=branch_flows,
    )

    assert residual <= 1.0e-6
    assert dc_flows["DC1"] == pytest.approx(
        float(hourly["hvdc_dc1_flow_mw"]), abs=1.0e-6
    )
    configured = configure_rts_gmlc_ac_case(
        template,
        context.data,
        point,
        generation_mw=generation,
        commitment=commitment,
        dc_bus=108,
        data_center_power_mw=data_center_power,
        data_center_power_factor=0.95,
        dc_flows_mw=dc_flows,
    )
    assert configured.data_center_reactive_demand_mvar == pytest.approx(
        data_center_power * tan(acos(0.95))
    )
    assert sum(configured.case["bus"][:, PD]) == pytest.approx(
        sum(point.demand_by_bus_mw.values()) + data_center_power
    )
    assert sum(configured.case["bus"][:, QD]) == pytest.approx(
        configured.native_reactive_demand_mvar
        + configured.data_center_reactive_demand_mvar
    )
    for uid in ("114_SYNC_COND_1", "214_SYNC_COND_1", "314_SYNC_COND_1"):
        assert (
            configured.case["gen"][template.generator_row_by_uid[uid], GEN_STATUS] == 1
        )
    for uid in ("212_CSP_1", "313_STORAGE_1"):
        assert (
            configured.case["gen"][template.generator_row_by_uid[uid], GEN_STATUS] == 0
        )


@requires_ac_inputs
@requires_bus_108
def test_one_saved_normal_state_runs_a_structured_direct_ac_replay():
    context = _build_scan_context(SCAN_CONFIG)
    template = load_rts_gmlc_ac_template(UPSTREAM_ROOT)
    hourly = _rows(BUS_108_RESULT / "hourly_dispatch.csv")[0]
    timestamp = hourly["timestamp"]
    generator_rows = [
        row
        for row in _rows(BUS_108_RESULT / "generator_dispatch.csv")
        if row["timestamp"] == timestamp
    ]
    branch_rows = [
        row
        for row in _rows(BUS_108_RESULT / "normal_branch_flows.csv")
        if row["timestamp"] == timestamp
    ]
    generation = {
        row["generator_uid"]: float(row["generation_mw"]) for row in generator_rows
    }
    commitment = {
        row["generator_uid"]: row["commitment"] == "true" for row in generator_rows
    }
    branch_flows = {row["branch_uid"]: float(row["flow_mw"]) for row in branch_rows}
    point = context.data.hourly_points[0]
    data_center_power = float(hourly["data_center_power_mw"])
    total_demand = dict(point.demand_by_bus_mw)
    total_demand[108] += data_center_power
    dc_flows, _residual = reconstruct_rts_gmlc_dc_flows(
        context.data,
        demand_by_bus_mw=total_demand,
        generation_mw=generation,
        ac_branch_flows_mw=branch_flows,
    )
    configured = configure_rts_gmlc_ac_case(
        template,
        context.data,
        point,
        generation_mw=generation,
        commitment=commitment,
        dc_bus=108,
        data_center_power_mw=data_center_power,
        data_center_power_factor=1.0,
        dc_flows_mw=dc_flows,
    )
    result = validate_rts_gmlc_ac_power_flow(
        template,
        configured,
        branch_rating="continuous",
    )

    assert result.evaluated
    assert result.converged
    assert result.max_non_slack_pg_deviation_mw == pytest.approx(0.0, abs=1.0e-6)
    assert result.slack_and_loss_adjustment_mw is not None
    assert result.max_voltage_violation_pu is not None
    assert result.max_reactive_power_violation_mvar is not None


@requires_ac_inputs
def test_ac_case_rejects_an_unknown_or_invalid_reactive_assumption():
    template = load_rts_gmlc_ac_template(UPSTREAM_ROOT)
    assert (
        template.case_template["branch"][template.branch_row_by_uid["A1"], BR_STATUS]
        == 1
    )

    with pytest.raises(ValueError, match="power factor"):
        # Input validation occurs before dispatch maps are inspected.
        configure_rts_gmlc_ac_case(
            template,
            type("Data", (), {"generators": ()})(),
            type("Point", (), {"demand_by_bus_mw": {}})(),
            generation_mw={},
            commitment={},
            dc_bus=108,
            data_center_power_mw=1.0,
            data_center_power_factor=0.0,
            dc_flows_mw={"DC1": 0.0},
        )
