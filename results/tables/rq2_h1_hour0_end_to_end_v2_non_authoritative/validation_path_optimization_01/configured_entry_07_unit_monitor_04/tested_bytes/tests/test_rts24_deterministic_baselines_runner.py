import csv
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

import experiments.run_rts24_deterministic_baselines as runner
from src.models import BaselinePolicy
from src.scenarios.common_input_signature import (
    COMMON_INPUT_SIGNATURE_SCHEMA,
    common_input_signature_sha256,
)


def _milestone(name):
    thresholds = {
        "module": 50.0,
        "T20": 50.0,
        "T50": 125.0,
        "T100": 250.0,
    }
    return SimpleNamespace(
        threshold_mw=thresholds[name],
        reached=False,
        quarter=None,
        right_censored=True,
        censor_quarter="q4",
        display_label=f">q4 ({name} right-censored)",
    )


def _dispatch(quarters, endpoint, feasible=True):
    milestones = SimpleNamespace(
        metric_scope=(
            "released_capacity_threshold_in_static_dc_state_set_with_"
            "declared_window_assumption"
        ),
        t_module=_milestone("module"),
        t20=_milestone("T20"),
        t50=_milestone("T50"),
        t100=_milestone("T100"),
    )
    state = SimpleNamespace(name="base", response_mode="base")
    state_result = SimpleNamespace(
        feasible=feasible,
        termination_condition="optimal" if feasible else "infeasible",
        max_balance_residual_mw=0.0,
    )
    state_results = {
        quarter.name: {"base": state_result} for quarter in quarters
    }
    zero_states = {
        quarter.name: {"base": 0.0} for quarter in quarters
    }
    poi_loads = {
        quarter.name: {"base": endpoint.total_capacity_mw[quarter.name]}
        for quarter in quarters
    }
    return SimpleNamespace(
        feasible=feasible,
        termination_condition="evaluated" if feasible else "dispatch_failed",
        solver_status="ok" if feasible else "warning",
        solver_message="synthetic dispatch",
        objective=10.0 if feasible else None,
        primary_optimization_objective=10.0 if feasible else None,
        canonical_dispatch_primary_objective=10.0 if feasible else None,
        primary_qp_solver="osqp",
        primary_qp_status="solved" if feasible else "time limit reached",
        primary_qp_iterations=25,
        primary_qp_primal_residual=1.0e-8,
        primary_qp_dual_residual=1.0e-8,
        primary_qp_max_constraint_violation=1.0e-8,
        primary_qp_max_bound_projection=0.0,
        primary_qp_solve_seconds=0.01,
        primary_linear_repair_objective_deviation=0.0,
        investment_cost=0.0,
        operating_cost=10.0,
        access_shortfall_cost=0.0,
        minimum_call_certificate_mw_sum=0.0,
        project_started=endpoint.project_started,
        start_quarter=endpoint.project_start_quarter,
        commissioned_by_quarter=endpoint.commissioned_by_quarter,
        firm_capacity_mw=endpoint.firm_capacity_mw,
        conditional_capacity_mw=endpoint.conditional_capacity_mw,
        total_capacity_mw=endpoint.total_capacity_mw,
        connected_demand_mw=endpoint.total_capacity_mw,
        firm_demand_mw=endpoint.firm_capacity_mw,
        active_conditional_demand_mw=endpoint.conditional_capacity_mw,
        access_shortfall_mw=endpoint.access_shortfall_mw,
        actual_grid_curtailment_mw=zero_states,
        actual_poi_load_mw=poi_loads,
        certified_grid_curtailment_mw=zero_states,
        certified_poi_load_mw=poi_loads,
        firm_breach_mw=zero_states,
        conditional_breach_mw=zero_states,
        actual_state_results=state_results,
        certified_state_results=state_results,
        effective_branch_ratings_mw={},
        base_operating_cost_per_hour={
            quarter.name: 1.0 for quarter in quarters
        },
        cost_interpretation="posthoc_displayed_plan_dispatch",
        capacity_interpretation=(
            "fixed_contract_capacity_separate_from_actual_connected_demand"
        ),
        certified_dispatch_interpretation=(
            "independent_counterfactual_dispatch_not_transition_from_actual"
        ),
        plan_parameter_status=(
            "deterministic_baseline_displayed_endpoint_non_economic_"
            "normalization"
        ),
        service_parameter_status=(
            "synthetic_mw_only_envelope_not_contract_evidence"
        ),
        response_model=(
            "mw_only_sustained_states_no_duration_or_energy_limits"
        ),
        excluded_branch_indices=(10,),
        breach_diagnostics_enabled=False,
        states=(state,),
        milestones=milestones,
    )


def _endpoint(quarters, *, x_exposure, normalization):
    quarter_names = tuple(quarter.name for quarter in quarters)
    conditional = {
        name: x_exposure / sum(quarter.operating_hours for quarter in quarters)
        for name in quarter_names
    }
    firm = {
        name: quarter.data_center_demand_mw - conditional[name]
        for name, quarter in zip(quarter_names, quarters)
    }
    total = {
        name: firm[name] + conditional[name] for name in quarter_names
    }
    calls = {name: {"base": 0.0} for name in quarter_names}
    return SimpleNamespace(
        access_shortfall_mwh=0.0,
        conditional_capacity_exposure_mwh=x_exposure,
        firm_capacity_mw=firm,
        conditional_capacity_mw=conditional,
        total_capacity_mw=total,
        access_shortfall_mw={name: 0.0 for name in quarter_names},
        project_started=True,
        project_start_quarter="q1",
        commissioned_by_quarter={
            name: position >= 2 for position, name in enumerate(quarter_names)
        },
        state_call_mw=calls,
        state_poi_load_mw={
            name: {"base": total[name]} for name in quarter_names
        },
        state_call_interpretation="feasible_witness_not_canonical_minimum",
        primary_target_mwh=0.0,
        primary_tolerance_mwh=1.0e-6,
        primary_deviation_mwh=0.0,
        primary_band_violation_mwh=0.0,
        x_exposure_target_mwh=x_exposure,
        x_exposure_tolerance_mwh=1.0e-6,
        x_exposure_deviation_mwh=0.0,
        x_band_violation_mwh=0.0,
        maximum_original_constraint_violation=1.0e-9,
        maximum_integrality_violation=0.0,
        normalization_label=normalization,
        planning_variable_indexing="quarter_root_only_no_state_or_scenario",
    )


def _result(policy, quarters, *, feasible=True, expose_failed_endpoint=False):
    minimum = _endpoint(
        quarters,
        x_exposure=10.0,
        normalization=(
            "conservative_minimum_x_normalization_not_economic_optimum"
        ),
    )
    maximum = _endpoint(
        quarters,
        x_exposure=20.0,
        normalization=(
            "conservative_maximum_x_normalization_not_economic_optimum"
        ),
    )
    dispatch = _dispatch(quarters, minimum, feasible=feasible) if feasible else None
    displayed = minimum if feasible or expose_failed_endpoint else None
    stage_names = (
        "primary_access_shortfall",
        "minimum_x_exposure",
        "maximum_x_exposure",
        "x_exposure_interval_audit",
        "minimum_x_project_count",
        "minimum_x_commissioning_exposure",
        "minimum_x_endpoint_audit",
        "maximum_x_project_count",
        "maximum_x_commissioning_exposure",
        "maximum_x_endpoint_audit",
    )
    stages = tuple(
        SimpleNamespace(
            stage=name,
            accepted=feasible,
            failure_reason=None if feasible else "synthetic_failure",
            termination_condition="optimal" if feasible else "infeasible",
            solver_status="ok" if feasible else "warning",
            solver_message="synthetic stage",
            lower_bound=0.0,
            upper_bound=0.0,
            absolute_gap=0.0,
            gap_tolerance=1.0e-6,
            maximum_constraint_violation=0.0,
            maximum_integrality_violation=0.0,
        )
        for name in stage_names
    )
    return SimpleNamespace(
        policy=policy,
        feasible=feasible,
        termination_condition="baseline_feasible" if feasible else "infeasible",
        solver_status="ok" if feasible else "warning",
        solver_message="synthetic baseline",
        primary_access_shortfall_mwh=0.0 if feasible else None,
        primary_tolerance_mwh=1.0e-6 if feasible else None,
        minimum_x_exposure_mwh=10.0 if feasible else None,
        maximum_x_exposure_mwh=20.0 if feasible else None,
        x_exposure_tolerance_mwh=1.0e-6 if feasible else None,
        minimum_x_endpoint=minimum if feasible or expose_failed_endpoint else None,
        maximum_x_endpoint=maximum if feasible or expose_failed_endpoint else None,
        displayed_endpoint=displayed,
        displayed_endpoint_name=("minimum_x_endpoint" if displayed else None),
        normalization_label=(minimum.normalization_label if displayed else None),
        failure_stage=None if feasible else "primary_access_shortfall",
        stage_diagnostics=stages,
        planning_variable_indexing="quarter_root_only_no_state_or_scenario",
        states=() if dispatch is None else dispatch.states,
        excluded_branch_indices=(10,),
        dispatch_result=dispatch,
    )


def _temporary_config(tmp_path):
    config = yaml.safe_load(
        Path("configs/rts24_deterministic_baselines.yaml").read_text(
            encoding="utf-8"
        )
    )
    config["output"] = {
        "policy_endpoint_path": str(tmp_path / "policy_endpoints.csv"),
        "quarter_path": str(tmp_path / "quarters.csv"),
        "summary_path": str(tmp_path / "summary.json"),
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config_path


def _data():
    generator = SimpleNamespace(index=0, in_service=True, p_max_mw=100.0)
    return SimpleNamespace(
        generators=(generator,),
        source_package="synthetic_runner_test",
        source_version="1",
    )


def test_runner_uses_identical_inputs_and_writes_auditable_outputs(
    tmp_path,
    monkeypatch,
):
    config_path = _temporary_config(tmp_path)
    calls = []

    def fake_solve(_data, **kwargs):
        calls.append(kwargs)
        return _result(kwargs["policy"], kwargs["quarters"])

    monkeypatch.setattr(runner, "load_rts24", _data)
    monkeypatch.setattr(
        runner,
        "non_islanding_branch_indices",
        lambda _data: (11, 12),
    )
    monkeypatch.setattr(runner, "solve_deterministic_baseline", fake_solve)

    summary = runner.run(config_path)

    assert [call["policy"] for call in calls] == [
        BaselinePolicy.B0_WAIT,
        BaselinePolicy.B1_FIRM,
        BaselinePolicy.B2_STATIC_FX,
    ]
    for field in (
        "quarters",
        "poi",
        "project",
        "service_envelope",
        "redispatch_up_mw",
        "redispatch_down_mw",
        "branch_indices",
        "generator_indices",
    ):
        assert len({id(call[field]) for call in calls}) == 1
    assert calls[0]["branch_indices"] == (11, 12)
    assert calls[0]["generator_indices"] == (0,)
    assert calls[0]["immediate_rating"] == "rate_c"
    assert calls[0]["sustained_rating"] == "rate_a"
    assert calls[0]["redispatch_up_mw"] == {0: 50.0}
    assert summary["demand_path_source"] == (
        "rts24_m2_frozen_nondecreasing_path"
    )
    assert summary["demand_path_mw"] == [50.0, 100.0, 200.0, 250.0]
    assert summary["quarter_operating_hours"] == [2184.0, 2184.0, 2208.0, 2208.0]
    assert summary["continuous_validation_hours"] == [0.0, 0.0, 0.0, 0.0]
    assert summary["feasible"]
    assert summary["run_status"] == "completed_non_certifying"
    assert not summary["security_certified"]
    assert all(
        policy["displayed_endpoint_name"] == "minimum_x_endpoint"
        for policy in summary["policy_results"]
    )
    assert all(policy["stage_diagnostics"] for policy in summary["policy_results"])
    assert all(
        policy["m3_dispatch_diagnostics"]["milestones"]["T100"][
            "right_censored"
        ]
        for policy in summary["policy_results"]
    )
    signature = summary["common_input_signature"]
    signature_hash = summary["common_input_signature_sha256"]
    assert summary["common_input_signature_schema"] == (
        COMMON_INPUT_SIGNATURE_SCHEMA
    )
    assert signature["quarters"][0]["operating_hours"] == 2184.0
    assert signature["quarters"][0]["system_load_multiplier"] == 0.8
    assert signature["quarters"][0]["data_center_demand_mw"] == 50.0
    assert signature["poi"]["application_capacity_mw"] == 250.0
    assert signature["project"]["poi_capacity_increase_mw"] == 200.0
    assert signature["service_envelope"]["max_conditional_capacity_mw"] == 75.0
    assert signature["immediate_rating"] == "rate_c"
    assert signature["sustained_rating"] == "rate_a"
    assert signature["redispatch_up_mw"] == {"0": 50.0}
    assert signature["security_states"][0]["name"] == "base"
    assert signature["security_states"][-1]["name"] == "generator_0_sustained"
    assert signature["objective"]["planning_objectives"] == (
        "lexicographic_min_u_then_min_max_x_no_economic_weights"
    )
    assert signature["solver"] == {"name": "highs"}
    assert signature_hash == common_input_signature_sha256(signature)
    assert all(
        policy["common_input_signature_sha256"] == signature_hash
        and policy["common_input_signature_schema"]
        == COMMON_INPUT_SIGNATURE_SCHEMA
        for policy in summary["policy_results"]
    )
    saved = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert saved["common_input_signature"] == summary["common_input_signature"]
    assert saved["common_input_signature_sha256"] == signature_hash
    with (tmp_path / "policy_endpoints.csv").open(
        encoding="utf-8", newline=""
    ) as output:
        endpoint_rows = list(csv.DictReader(output))
    with (tmp_path / "quarters.csv").open(
        encoding="utf-8", newline=""
    ) as output:
        quarter_rows = list(csv.DictReader(output))
    assert len(endpoint_rows) == 6
    assert len(quarter_rows) == 24
    assert all(row["security_certified"] == "False" for row in endpoint_rows)
    assert all(row["continuous_validation_hours"] == "0.0" for row in quarter_rows)
    assert all(json.loads(row["endpoint_audit_json"]) for row in endpoint_rows)
    assert all(json.loads(row["stage_diagnostics_json"]) for row in endpoint_rows)
    assert all(json.loads(row["T100_json"])["right_censored"] for row in quarter_rows)


def test_runner_fails_closed_and_hides_all_displayed_endpoints(
    tmp_path,
    monkeypatch,
):
    config_path = _temporary_config(tmp_path)
    calls = []

    def fake_solve(_data, **kwargs):
        calls.append(kwargs["policy"])
        if kwargs["policy"] is BaselinePolicy.B1_FIRM:
            raise RuntimeError("synthetic solver exception")
        return _result(
            kwargs["policy"],
            kwargs["quarters"],
            feasible=kwargs["policy"] is BaselinePolicy.B0_WAIT,
            expose_failed_endpoint=True,
        )

    monkeypatch.setattr(runner, "load_rts24", _data)
    monkeypatch.setattr(
        runner,
        "non_islanding_branch_indices",
        lambda _data: (11, 12),
    )
    monkeypatch.setattr(runner, "solve_deterministic_baseline", fake_solve)

    summary = runner.run(config_path)

    assert calls == list(
        (
            BaselinePolicy.B0_WAIT,
            BaselinePolicy.B1_FIRM,
            BaselinePolicy.B2_STATIC_FX,
        )
    )
    assert not summary["feasible"]
    assert not summary["all_policies_feasible"]
    assert summary["run_status"] == "failed_closed"
    assert "one_or_more_baseline_policies_failed_closed" in summary[
        "certification_blockers"
    ]
    assert all(
        policy["displayed_endpoint"] is None
        and policy["displayed_endpoint_name"] is None
        for policy in summary["policy_results"]
    )
    by_policy = {row["policy"]: row for row in summary["policy_results"]}
    assert by_policy["B1_FIRM"]["exception_type"] == "RuntimeError"
    assert not by_policy["B2_STATIC_FX"]["feasible"]
    with (tmp_path / "policy_endpoints.csv").open(
        encoding="utf-8", newline=""
    ) as output:
        endpoint_rows = list(csv.DictReader(output))
    with (tmp_path / "quarters.csv").open(
        encoding="utf-8", newline=""
    ) as output:
        quarter_rows = list(csv.DictReader(output))
    assert all(row["run_feasible"] == "False" for row in endpoint_rows)
    assert all(row["endpoint_is_displayed"] == "False" for row in endpoint_rows)
    assert all(row["run_feasible"] == "False" for row in quarter_rows)
    assert json.loads(
        (tmp_path / "summary.json").read_text(encoding="utf-8")
    )["run_status"] == "failed_closed"


def test_runner_rejects_nonzero_static_continuous_validation_hours(tmp_path):
    config_path = _temporary_config(tmp_path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    for quarter in config["planning"]["quarters"]:
        quarter["continuous_validation_hours"] = 24.0
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    with pytest.raises(ValueError, match="continuous validation hours at zero"):
        runner.run(config_path)


def test_runner_rejects_malformed_feasible_result_contract(
    tmp_path,
    monkeypatch,
):
    config_path = _temporary_config(tmp_path)

    def fake_solve(_data, **kwargs):
        result = _result(kwargs["policy"], kwargs["quarters"])
        if kwargs["policy"] is BaselinePolicy.B2_STATIC_FX:
            result.stage_diagnostics[0].accepted = False
            result.dispatch_result.firm_capacity_mw = {
                **result.dispatch_result.firm_capacity_mw,
                "q1": result.dispatch_result.firm_capacity_mw["q1"] + 1.0,
            }
            result.dispatch_result.firm_breach_mw = {"q1": {"base": 0.0}}
            result.dispatch_result.milestones.t100.censor_quarter = "q1"
        return result

    monkeypatch.setattr(runner, "load_rts24", _data)
    monkeypatch.setattr(
        runner,
        "non_islanding_branch_indices",
        lambda _data: (11, 12),
    )
    monkeypatch.setattr(runner, "solve_deterministic_baseline", fake_solve)

    summary = runner.run(config_path)

    assert not summary["feasible"]
    b2 = next(
        policy
        for policy in summary["policy_results"]
        if policy["policy"] == "B2_STATIC_FX"
    )
    assert "one_or_more_stages_not_accepted" in b2["runner_contract_audit"][
        "failure_reasons"
    ]
    assert "m3_firm_capacity_mismatch" in b2["runner_contract_audit"][
        "failure_reasons"
    ]
    assert "m3_firm_breach_mw_quarter_set_mismatch" in b2[
        "runner_contract_audit"
    ]["failure_reasons"]
    assert "m3_t100_censor_quarter_mismatch" in b2["runner_contract_audit"][
        "failure_reasons"
    ]
    assert b2["displayed_endpoint"] is None


def test_all_policy_exceptions_use_failed_status_and_stable_csv_schema(
    tmp_path,
    monkeypatch,
):
    config_path = _temporary_config(tmp_path)
    monkeypatch.setattr(runner, "load_rts24", _data)
    monkeypatch.setattr(
        runner,
        "non_islanding_branch_indices",
        lambda _data: (11, 12),
    )
    monkeypatch.setattr(
        runner,
        "solve_deterministic_baseline",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("forced policy failure")
        ),
    )

    summary = runner.run(config_path)

    assert summary["all_policies_attempted"]
    assert not summary["all_policies_completed"]
    assert not summary["feasible"]
    with (tmp_path / "quarters.csv").open(encoding="utf-8", newline="") as output:
        reader = csv.DictReader(output)
        assert tuple(reader.fieldnames) == runner._QUARTER_FIELDS
        assert list(reader) == []


def test_cli_exits_nonzero_for_failed_closed_summary(monkeypatch, capsys):
    monkeypatch.setattr(runner, "run", lambda _path: {"feasible": False})
    monkeypatch.setattr("sys.argv", ["baseline-runner"])

    with pytest.raises(SystemExit) as error:
        runner.main()

    assert error.value.code == 1
    assert '"feasible": false' in capsys.readouterr().out


def test_compact_json_rejects_nonfinite_numbers():
    with pytest.raises(ValueError, match="non-finite"):
        runner._compact_json({"invalid": float("nan")})
