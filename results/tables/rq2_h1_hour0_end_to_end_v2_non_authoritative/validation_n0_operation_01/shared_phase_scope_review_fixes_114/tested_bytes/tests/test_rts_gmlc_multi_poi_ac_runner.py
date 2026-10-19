from pathlib import Path

import pytest
import yaml

from experiments.run_rts_gmlc_multi_poi_ac_replay import (
    _build_context,
    _load_candidate_dispatch,
    _read_config,
)
from src.grid.rts_gmlc_ac import reconstruct_rts_gmlc_dc_flows

CONFIG_PATH = Path("configs/rts_gmlc_google_day0_multi_poi_ac_replay.yaml")
PARENT_RESULTS = Path(
    "results/tables/rts_gmlc_google_day0_multi_poi_selected_n1_dc_scuc_v1"
)


requires_parent_results = pytest.mark.skipif(
    not (PARENT_RESULTS / "aggregate" / "summary.json").exists(),
    reason="Run the pre-registered multi-POI scan first",
)


def test_ac_replay_config_freezes_all_representatives_states_and_pf_cases():
    config = _read_config(CONFIG_PATH)

    assert config["parent_scan"]["representative_bus_order"] == [120, 108]
    assert config["case_scope"]["hours"] == "all_24"
    assert config["case_scope"]["security_states"] == "all_24_common_states"
    assert config["case_scope"]["power_factor_cases"] == [
        {"id": "unity", "value": 1.0, "direction": "lagging"},
        {"id": "lagging_095", "value": 0.95, "direction": "lagging"},
    ]
    assert not config["ac_assumptions"]["q_limit_switching"]
    assert not config["ac_assumptions"]["restoration_or_redispatch"]
    assert not config["preregistration"]["all_ac_cases_blind"]


def test_ac_replay_config_rejects_post_probe_restoration_scope_creep(tmp_path):
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config["ac_assumptions"]["restoration_or_redispatch"] = True
    path = tmp_path / "invalid-ac.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="ac_assumptions contract drifted"):
        _read_config(path)


@requires_parent_results
def test_ac_runner_loads_complete_parent_dispatch_tables_and_security_dc_balance():
    context = _build_context(CONFIG_PATH)
    dispatch = _load_candidate_dispatch(context, 120)

    assert len(dispatch.timestamps) == 24
    assert len(dispatch.state_ids) == 24
    assert len(dispatch.security_generation) == 24 * 23
    assert len(dispatch.security_branch_flows) == 24 * 23
    assert len(dispatch.state_metadata) == 24 * 24
    assert set(context.input_contract["implementation_sha256"]) == {
        "experiments/run_rts_gmlc_multi_poi_ac_replay.py",
        "src/grid/rts_gmlc_ac.py",
    }

    timestamp = dispatch.timestamps[0]
    state_id = "branch_A11_immediate"
    point = context.scan_context.data.hourly_points[0]
    data_center_power = float(
        dispatch.hourly_by_timestamp[timestamp]["data_center_power_mw"]
    )
    total_demand = dict(point.demand_by_bus_mw)
    total_demand[120] += data_center_power
    dc_flows, residual = reconstruct_rts_gmlc_dc_flows(
        context.scan_context.data,
        demand_by_bus_mw=total_demand,
        generation_mw=dispatch.security_generation[(timestamp, state_id)],
        ac_branch_flows_mw=dispatch.security_branch_flows[(timestamp, state_id)],
    )

    assert set(dc_flows) == {"DC1"}
    assert abs(dc_flows["DC1"]) <= 100.0 + 1.0e-6
    assert residual <= 1.0e-6
