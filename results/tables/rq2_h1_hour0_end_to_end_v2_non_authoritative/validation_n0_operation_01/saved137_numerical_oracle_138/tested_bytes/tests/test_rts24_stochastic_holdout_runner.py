import csv
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import experiments.run_rts24_stochastic_holdout as runner


CONFIG_PATH = Path("configs/rts24_stochastic_holdout.yaml")


def _temporary_config(tmp_path):
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config["output"] = {
        "path_results": str(tmp_path / "paths.csv"),
        "summary_path": str(tmp_path / "summary.json"),
    }
    config_path = tmp_path / "holdout.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config_path


def _states():
    return tuple(
        SimpleNamespace(
            name="base" if index == 0 else f"state_{index}",
            response_mode="base" if index == 0 else "bounded",
        )
        for index in range(107)
    )


def _fake_result(kwargs, *, feasible=True):
    quarters = kwargs["quarters"]
    plan = kwargs["plan"]
    project = kwargs["project"]
    states = _states()
    quarter_names = tuple(quarter.name for quarter in quarters)
    firm = {name: float(plan.firm_capacity_mw[name]) for name in quarter_names}
    conditional = {
        name: float(plan.conditional_capacity_mw[name]) for name in quarter_names
    }
    total = {name: firm[name] + conditional[name] for name in quarter_names}
    connected = {
        quarter.name: min(quarter.data_center_demand_mw, total[quarter.name])
        for quarter in quarters
    }
    firm_demand = {
        quarter.name: min(quarter.data_center_demand_mw, firm[quarter.name])
        for quarter in quarters
    }
    active_x = {
        name: connected[name] - firm_demand[name] for name in quarter_names
    }
    shortfall = {
        quarter.name: quarter.data_center_demand_mw - connected[quarter.name]
        for quarter in quarters
    }
    start_position = quarter_names.index(plan.project_start_quarter)
    commissioned = {
        name: position >= start_position + project.lead_time_quarters
        for position, name in enumerate(quarter_names)
    }
    state_result = SimpleNamespace(feasible=True, max_balance_residual_mw=0.0)
    state_results = {
        quarter: {state.name: state_result for state in states}
        for quarter in quarter_names
    }
    zero_states = {
        quarter: {state.name: 0.0 for state in states}
        for quarter in quarter_names
    }
    return SimpleNamespace(
        feasible=feasible,
        termination_condition="evaluated" if feasible else "infeasible",
        states=states,
        firm_capacity_mw=firm,
        conditional_capacity_mw=conditional,
        total_capacity_mw=total,
        connected_demand_mw=connected,
        firm_demand_mw=firm_demand,
        active_conditional_demand_mw=active_x,
        access_shortfall_mw=shortfall,
        commissioned_by_quarter=commissioned,
        actual_state_results=state_results,
        certified_state_results=state_results,
        firm_breach_mw=zero_states,
        conditional_breach_mw=zero_states,
        actual_grid_curtailment_mw=zero_states,
        certified_grid_curtailment_mw=zero_states,
    )


def _strict_json_loads(raw):
    def no_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result

    def no_constants(value):
        raise ValueError(f"non-finite constant: {value}")

    return json.loads(
        raw,
        object_pairs_hook=no_duplicates,
        parse_constant=no_constants,
    )


def test_runner_executes_every_fixed_policy_endpoint_and_writes_strict_outputs(
    tmp_path,
    monkeypatch,
):
    config_path = _temporary_config(tmp_path)
    calls = []

    def fake_evaluate(_data, **kwargs):
        calls.append(kwargs)
        return _fake_result(kwargs)

    monkeypatch.setattr(runner, "evaluate_deterministic_fx_plan", fake_evaluate)

    summary = runner.run(config_path)

    assert len(calls) == 48
    assert [call["plan"].parameter_status.split("_")[2] for call in calls[:1]] == [
        "policy"
    ]
    assert {call["project"].lead_time_quarters for call in calls} == {2, 3}
    assert all(len(call["branch_indices"]) > 0 for call in calls)
    assert all(len(call["generator_indices"]) > 0 for call in calls)
    assert summary["policy_order"] == ["B3", "B4"]
    assert summary["endpoint_order"] == ["minimum_x", "maximum_x"]
    assert summary["all_executions_attempted"]
    assert summary["all_executions_feasible"]
    assert summary["synthetic_holdout_value_published"]
    assert not summary["formal_vma_published"]
    assert not summary["planning_reoptimization_allowed"]
    assert not summary["security_certified"]
    assert set(summary["endpoint_expected_access_shortfall_mwh"]) == {"B3", "B4"}
    assert len(summary["set_valued_holdout_adaptivity_value_interval_mwh"]) == 2

    raw_summary = (tmp_path / "summary.json").read_text(encoding="utf-8")
    assert _strict_json_loads(raw_summary) == summary
    with (tmp_path / "paths.csv").open(encoding="utf-8", newline="") as output:
        rows = list(csv.reader(output))
    assert tuple(rows[0]) == runner._PATH_FIELDS
    assert len(rows) == 193
    assert all(len(row) == len(runner._PATH_FIELDS) for row in rows)


@pytest.mark.parametrize("failure_mode", ("infeasible", "exception"))
def test_runner_fails_closed_if_any_fixed_execution_fails(
    tmp_path,
    monkeypatch,
    failure_mode,
):
    config_path = _temporary_config(tmp_path)
    call_count = 0

    def fake_evaluate(_data, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 7:
            if failure_mode == "exception":
                raise RuntimeError("synthetic holdout failure")
            return _fake_result(kwargs, feasible=False)
        return _fake_result(kwargs)

    monkeypatch.setattr(runner, "evaluate_deterministic_fx_plan", fake_evaluate)

    summary = runner.run(config_path)

    assert call_count == 48
    assert not summary["all_executions_feasible"]
    assert not summary["synthetic_holdout_value_published"]
    assert summary["endpoint_expected_access_shortfall_mwh"] is None
    assert summary["paired_endpoint_adaptivity_value_mwh"] is None
    assert summary["set_valued_holdout_adaptivity_value_interval_mwh"] is None
    assert any(not record["passed"] for record in summary["execution_results"])
    with (tmp_path / "paths.csv").open(
        encoding="utf-8", newline=""
    ) as output:
        rows = list(csv.DictReader(output))
    assert len(rows) == 192
    assert all(row["run_feasible"] == "False" for row in rows)


def test_cli_exits_nonzero_when_holdout_fails_closed(monkeypatch, capsys):
    monkeypatch.setattr(
        runner,
        "run",
        lambda _path: {"all_executions_feasible": False},
    )
    monkeypatch.setattr("sys.argv", ["holdout-runner"])

    with pytest.raises(SystemExit) as error:
        runner.main()

    assert error.value.code == 1
    assert '"all_executions_feasible": false' in capsys.readouterr().out
