import csv
import json
from pathlib import Path

import pytest
import yaml

from datetime import datetime, timedelta

from experiments.run_rts24_flexibility_envelope import _mw_only, run
from src.evaluation import ChronologicalFlexibilityTrace


CONFIG_PATH = Path("configs/rts24_flexibility_envelope.yaml")


def test_mw_only_energy_uses_the_configured_time_step():
    start = datetime(2020, 1, 1)
    trace = ChronologicalFlexibilityTrace(
        name="half_hour_unit_check",
        timestamps=(start, start + timedelta(minutes=30)),
        periods=("q1", "q1"),
        grid_call_mw=(20.0, 20.0),
        call_limit_mw=(20.0, 20.0),
        recovery_headroom_mw=(0.0, 0.0),
        boundary_state_status="clean_boundary_with_zero_carry_in",
        completed_periods=frozenset({"q1"}),
        initial_has_prior_event=False,
    )

    result = _mw_only(trace, tolerance=1.0e-7, time_step_hours=0.5)

    assert result["curtailment_energy_mwh_by_period"]["q1"] == pytest.approx(20.0)
    assert result["event_count_by_period"]["q1"] == 1
    assert result["terminal_recovery_debt_mwh_by_period"]["q1"] is None


def _temporary_config(tmp_path):
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config["output"] = {
        "quarter_path": str(tmp_path / "quarters.csv"),
        "hourly_path": str(tmp_path / "hourly.csv"),
        "summary_path": str(tmp_path / "summary.json"),
    }
    config_path = tmp_path / "m6.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config_path


@pytest.mark.skipif(
    not Path("data/raw/rts_gmlc/v0.2.3/upstream").exists(),
    reason="Run scripts/fetch_rts_gmlc.ps1 to enable chronology integration",
)
def test_m6_network_replay_and_f1_f3_ablation_gate(tmp_path):
    summary = run(_temporary_config(tmp_path))

    assert summary["timeline_hours"] == 8784
    assert summary["source_security_state_count"] == 107
    assert summary["network_call_magnitude_coupled"]
    assert not summary["chronological_grid_dispatch_coupled"]
    assert summary["network_replay_is_degenerate_zero_call"]
    assert all(
        call == 0.0
        for layer in summary["network_call_mw_by_layer_quarter"].values()
        for call in layer.values()
    )
    assert summary["m6_mechanism_gate_passed"]
    replay = summary["ablation_results"]["network_minimum_call_replay"]
    assert all(
        result["actual_feasible"]
        and result["contract_counterfactual_feasible"]
        for result in replay.values()
    )
    stress = summary["ablation_results"]["full_x_contract_stress"]
    assert stress["F1_mw_only"]["actual_feasible"]
    assert stress["F1_mw_only"]["contract_counterfactual_feasible"]
    assert stress["F2_temporal_no_recovery"]["actual_feasible"]
    assert stress["F2_temporal_no_recovery"]["contract_counterfactual_feasible"]
    assert not stress["F3_full_recovery"]["actual_feasible"]
    assert not stress["F3_full_recovery"]["contract_counterfactual_feasible"]
    assert stress["F2_temporal_no_recovery"]["T100"]["quarter"] == "q3"
    assert stress["F3_full_recovery"]["T100"]["right_censored"]

    saved = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert saved == summary
    with (tmp_path / "quarters.csv").open(
        encoding="utf-8", newline=""
    ) as output:
        quarter_rows = list(csv.reader(output))
    with (tmp_path / "hourly.csv").open(
        encoding="utf-8", newline=""
    ) as output:
        hourly_rows = list(csv.reader(output))
    assert len(quarter_rows) == 49
    assert all(len(row) == len(quarter_rows[0]) for row in quarter_rows)
    assert len(hourly_rows) == 2 * 2 * 2 * 8784 + 1
    assert all(len(row) == len(hourly_rows[0]) for row in hourly_rows)


def test_m6_source_hash_drift_is_rejected(tmp_path):
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    source = Path(config["source"]["m3_state_path"])
    drifted = tmp_path / "states.csv"
    drifted.write_bytes(source.read_bytes() + b"\n")
    config["source"]["m3_state_path"] = str(drifted)
    config["output"] = {
        "quarter_path": str(tmp_path / "quarters.csv"),
        "hourly_path": str(tmp_path / "hourly.csv"),
        "summary_path": str(tmp_path / "summary.json"),
    }
    config_path = tmp_path / "m6.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    with pytest.raises(ValueError, match="SHA-256 does not match"):
        run(config_path)


@pytest.mark.skipif(
    not Path("data/raw/rts_gmlc/v0.2.3/upstream").exists(),
    reason="Run scripts/fetch_rts_gmlc.ps1 to enable chronology integration",
)
def test_m6_gate_fails_if_the_preregistered_mechanism_pattern_is_not_met(
    tmp_path,
):
    config_path = _temporary_config(tmp_path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["ablation"]["mechanism_gate_expectation"][
        "full_x_contract_stress"
    ]["F3_full_recovery"]["actual"] = True
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    summary = run(config_path)

    assert not summary["m6_mechanism_gate_passed"]
