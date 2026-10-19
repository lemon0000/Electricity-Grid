import csv
import json
from pathlib import Path

import pytest
import yaml

import experiments.run_rts24_stochastic_baselines as runner
from src.grid.scopf import SecurityState
from src.models import (
    BaselineSolveDiagnostic,
    StochasticBaselineEndpoint,
    StochasticBaselinePolicy,
    StochasticBaselineResult,
)


def _temporary_config(tmp_path: Path) -> Path:
    config = yaml.safe_load(
        Path("configs/rts24_stochastic_baselines.yaml").read_text(
            encoding="utf-8"
        )
    )
    config["output"] = {
        "policy_path": str(tmp_path / "policies.csv"),
        "endpoint_path": str(tmp_path / "endpoints.csv"),
        "summary_path": str(tmp_path / "summary.json"),
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config_path


def _endpoint(tree, policy, *, conditional_capacity_mw: float):
    leaf_by_name = {leaf.name: leaf for leaf in tree.leaves}
    demand_by_name = {state.name: state for state in tree.demand_states}
    firm = {}
    conditional = {}
    total = {}
    connected = {}
    firm_demand = {}
    active_conditional = {}
    shortfall = {}
    project_start = {}
    project_available = {}
    decision_group = {}
    project_start_quarter = {}

    for leaf in tree.leaf_names:
        demand_path = demand_by_name[leaf_by_name[leaf].demand_state].demand_mw
        firm[leaf] = {}
        conditional[leaf] = {}
        total[leaf] = {}
        connected[leaf] = {}
        firm_demand[leaf] = {}
        active_conditional[leaf] = {}
        shortfall[leaf] = {}
        project_start[leaf] = {}
        project_available[leaf] = {}
        decision_group[leaf] = {}
        project_start_quarter[leaf] = None
        for quarter, demand in zip(tree.quarters, demand_path):
            firm[leaf][quarter] = 40.0
            conditional[leaf][quarter] = conditional_capacity_mw
            total[leaf][quarter] = 40.0 + conditional_capacity_mw
            connected[leaf][quarter] = min(demand, total[leaf][quarter])
            firm_demand[leaf][quarter] = min(demand, firm[leaf][quarter])
            active_conditional[leaf][quarter] = (
                connected[leaf][quarter] - firm_demand[leaf][quarter]
            )
            shortfall[leaf][quarter] = demand - connected[leaf][quarter]
            project_start[leaf][quarter] = False
            project_available[leaf][quarter] = False
            group_index = next(
                index
                for index, group in enumerate(
                    tree.decision_groups(policy.value, quarter)
                )
                if leaf in group
            )
            decision_group[leaf][quarter] = f"{policy.value}_{quarter}_{group_index}"

    return StochasticBaselineEndpoint(
        access_shortfall_mwh=10.0,
        contract_capacity_exposure_mwh=100.0,
        conditional_capacity_exposure_mwh=conditional_capacity_mw * 10.0,
        firm_capacity_mw=firm,
        conditional_capacity_mw=conditional,
        total_capacity_mw=total,
        connected_demand_mw=connected,
        firm_demand_mw=firm_demand,
        active_conditional_demand_mw=active_conditional,
        access_shortfall_mw=shortfall,
        project_start_by_quarter=project_start,
        project_start_quarter=project_start_quarter,
        project_available_by_quarter=project_available,
        decision_group_by_quarter=decision_group,
        primary_target_mwh=10.0,
        primary_tolerance_mwh=1.0e-6,
        primary_deviation_mwh=0.0,
        primary_band_violation_mwh=0.0,
        contract_exposure_target_mwh=100.0,
        contract_exposure_tolerance_mwh=1.0e-6,
        contract_exposure_deviation_mwh=0.0,
        contract_exposure_band_violation_mwh=0.0,
        x_exposure_target_mwh=conditional_capacity_mw * 10.0,
        x_exposure_tolerance_mwh=1.0e-6,
        x_exposure_deviation_mwh=0.0,
        x_exposure_band_violation_mwh=0.0,
        expected_project_count=0.0,
        expected_commissioning_exposure_hours=0.0,
        maximum_actual_call_mw=conditional_capacity_mw,
        maximum_contract_call_mw=conditional_capacity_mw,
        maximum_original_constraint_violation=0.0,
        maximum_integrality_violation=0.0,
        normalization_label="synthetic_runner_endpoint",
        planning_variable_scope="policy_decision_groups_F_X_z_start_only",
    )


def _result(tree, policy, *, feasible=True, shortfall_mwh=None):
    roles = {
        StochasticBaselinePolicy.B3: "two_stage_root_commitment",
        StochasticBaselinePolicy.B4: "multistage_nonanticipative_policy",
        StochasticBaselinePolicy.B5: "perfect_information_bound",
    }
    default_shortfall = {
        StochasticBaselinePolicy.B3: 30.0,
        StochasticBaselinePolicy.B4: 20.0,
        StochasticBaselinePolicy.B5: 10.0,
    }
    primary = default_shortfall[policy] if shortfall_mwh is None else shortfall_mwh
    minimum = _endpoint(tree, policy, conditional_capacity_mw=10.0)
    maximum = _endpoint(tree, policy, conditional_capacity_mw=20.0)
    diagnostics = tuple(
        BaselineSolveDiagnostic(
            stage=f"stage_{index:02d}",
            accepted=feasible,
            failure_reason=None if feasible else "synthetic_failure",
            termination_condition="optimal" if feasible else "infeasible",
            solver_status="ok" if feasible else "warning",
            solver_message="synthetic runner result",
            lower_bound=0.0,
            upper_bound=0.0,
            absolute_gap=0.0,
            gap_tolerance=1.0e-6,
            maximum_constraint_violation=0.0,
            maximum_integrality_violation=0.0,
        )
        for index in range(13)
    )
    states = (
        SecurityState(
            name="base",
            kind="base",
            element_index=None,
            branch_rating="rate_a",
            outaged_branch_indices=frozenset(),
            outaged_generator_indices=frozenset(),
            response_mode="base",
        ),
    )
    return StochasticBaselineResult(
        policy=policy,
        role=roles[policy],
        implementable=policy is not StochasticBaselinePolicy.B5,
        feasible=feasible,
        termination_condition="evaluated" if feasible else "infeasible",
        solver_status="ok" if feasible else "warning",
        solver_message="synthetic runner result",
        primary_access_shortfall_mwh=primary,
        primary_tolerance_mwh=1.0e-6,
        minimum_contract_exposure_mwh=100.0,
        maximum_contract_exposure_mwh=120.0,
        contract_exposure_tolerance_mwh=1.0e-6,
        minimum_x_exposure_mwh=100.0,
        maximum_x_exposure_mwh=200.0,
        x_exposure_tolerance_mwh=1.0e-6,
        minimum_x_endpoint=minimum,
        maximum_x_endpoint=maximum,
        displayed_endpoint=minimum,
        displayed_endpoint_name="minimum_x",
        normalization_label=minimum.normalization_label,
        failure_stage=None if feasible else "stage_00",
        stage_diagnostics=diagnostics,
        planning_variable_scope="policy_decision_groups_F_X_z_start_only",
        natural_node_counts={
            quarter: len(tree.nodes_for_quarter(quarter))
            for quarter in tree.quarters
        },
        decision_group_counts={
            quarter: len(tree.decision_groups(policy.value, quarter))
            for quarter in tree.quarters
        },
        states=states,
        excluded_branch_indices=(10,),
        embedded_state_rows=96,
    )


def _strict_json_loads(raw: str):
    def reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError(f"non-finite JSON constant: {value}")

    return json.loads(
        raw,
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_constant,
    )


def test_runner_invokes_policies_in_order_and_writes_strict_outputs(
    tmp_path,
    monkeypatch,
):
    config_path = _temporary_config(tmp_path)
    calls = []

    def fake_solve(_data, **kwargs):
        calls.append(kwargs)
        return _result(kwargs["tree"], kwargs["policy"])

    monkeypatch.setattr(runner, "solve_stochastic_baseline", fake_solve)

    summary = runner.run(config_path)

    assert [call["policy"] for call in calls] == list(StochasticBaselinePolicy)
    for field in (
        "tree",
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
    assert summary["all_policies_feasible"]
    assert summary["information_ordering_passed"]
    assert summary["formal_endpoints_published"]
    assert not summary["security_certified"]
    assert next(
        row for row in summary["policy_results"] if row["policy"] == "B5"
    )["implementable"] is False

    raw_summary = (tmp_path / "summary.json").read_text(encoding="utf-8")
    saved_summary = _strict_json_loads(raw_summary)
    assert saved_summary == summary

    for name, expected_fields, expected_rows in (
        ("policies.csv", runner._POLICY_FIELDS, 3),
        ("endpoints.csv", runner._ENDPOINT_FIELDS, 288),
    ):
        with (tmp_path / name).open(encoding="utf-8", newline="") as output:
            rows = list(csv.reader(output))
        assert tuple(rows[0]) == expected_fields
        assert len(rows) == expected_rows + 1
        assert all(len(row) == len(expected_fields) for row in rows)

    with (tmp_path / "endpoints.csv").open(
        encoding="utf-8", newline=""
    ) as output:
        endpoint_rows = list(csv.DictReader(output))
    assert all(
        row["implementable"] == "False"
        for row in endpoint_rows
        if row["policy"] == "B5"
    )


@pytest.mark.parametrize(
    ("failed_policy", "shortfall_by_policy"),
    (
        (StochasticBaselinePolicy.B4, None),
        (
            None,
            {
                StochasticBaselinePolicy.B3: 10.0,
                StochasticBaselinePolicy.B4: 20.0,
                StochasticBaselinePolicy.B5: 5.0,
            },
        ),
    ),
)
def test_endpoint_publication_fails_closed_on_policy_or_ordering_failure(
    tmp_path,
    monkeypatch,
    failed_policy,
    shortfall_by_policy,
):
    config_path = _temporary_config(tmp_path)

    def fake_solve(_data, **kwargs):
        policy = kwargs["policy"]
        return _result(
            kwargs["tree"],
            policy,
            feasible=policy is not failed_policy,
            shortfall_mwh=(
                None
                if shortfall_by_policy is None
                else shortfall_by_policy[policy]
            ),
        )

    monkeypatch.setattr(runner, "solve_stochastic_baseline", fake_solve)

    summary = runner.run(config_path)

    assert not summary["formal_endpoints_published"]
    if failed_policy is None:
        assert summary["all_policies_feasible"]
        assert not summary["information_ordering_passed"]
    else:
        assert not summary["all_policies_feasible"]
        assert not summary["information_ordering_passed"]
    with (tmp_path / "endpoints.csv").open(
        encoding="utf-8", newline=""
    ) as output:
        reader = csv.DictReader(output)
        assert tuple(reader.fieldnames) == runner._ENDPOINT_FIELDS
        assert list(reader) == []


def test_runner_rejects_live_common_input_signature_drift(tmp_path, monkeypatch):
    config_path = _temporary_config(tmp_path)
    original = runner.common_input_signature_for_config

    def drifted_signature(path):
        signature = original(path)
        return {
            **signature,
            "common_input_signature_sha256": "0" * 64,
        }

    monkeypatch.setattr(
        runner,
        "common_input_signature_for_config",
        drifted_signature,
    )
    monkeypatch.setattr(
        runner,
        "solve_stochastic_baseline",
        lambda *_args, **_kwargs: pytest.fail("solver must not be called"),
    )

    with pytest.raises(ValueError, match="does not match M5 freeze"):
        runner.run(config_path)
