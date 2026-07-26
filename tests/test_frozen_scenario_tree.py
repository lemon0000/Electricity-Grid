from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml

from experiments.run_rts24_deterministic_baselines import (
    common_input_signature_for_config,
)
from src.scenarios import (
    FrozenScenarioTree,
    load_frozen_scenario_tree,
    parse_frozen_scenario_tree,
)


DEMAND_PATHS = {
    "delayed_lower": (
        "delayed",
        "lower",
        [50.0, 50.0, 100.0, 200.0],
    ),
    "delayed_upper": (
        "delayed",
        "upper",
        [50.0, 50.0, 100.0, 250.0],
    ),
    "baseline_lower": (
        "baseline",
        "lower",
        [50.0, 100.0, 200.0, 200.0],
    ),
    "baseline_upper": (
        "baseline",
        "upper",
        [50.0, 100.0, 200.0, 250.0],
    ),
    "accelerated_lower": (
        "accelerated",
        "lower",
        [50.0, 200.0, 200.0, 200.0],
    ),
    "accelerated_upper": (
        "accelerated",
        "upper",
        [50.0, 200.0, 200.0, 250.0],
    ),
}
Q2_SIGNALS = ("delayed", "baseline", "accelerated")
PROJECT_DELAYS = {"on_time": 0, "delayed_one_quarter": 1}
QUARTERS = ("q1", "q2", "q3", "q4")


def _valid_config():
    leaves = [
        {
            "name": f"{demand}__{project}",
            "demand_state": demand,
            "project_state": project,
            "probability": 1.0 / 12.0,
        }
        for demand in DEMAND_PATHS
        for project in PROJECT_DELAYS
    ]
    leaf_names = [leaf["name"] for leaf in leaves]
    signal_groups = {
        signal: [
            leaf["name"]
            for leaf in leaves
            if DEMAND_PATHS[leaf["demand_state"]][0] == signal
        ]
        for signal in Q2_SIGNALS
    }
    signal_project_groups = {
        (signal, project): [
            leaf["name"]
            for leaf in leaves
            if DEMAND_PATHS[leaf["demand_state"]][0] == signal
            and leaf["project_state"] == project
        ]
        for signal in Q2_SIGNALS
        for project in PROJECT_DELAYS
    }
    singletons = [[leaf_name] for leaf_name in leaf_names]

    nodes = [
        {
            "name": "q1_root",
            "quarter": "q1",
            "parent": None,
            "probability": 1.0,
            "leaves": leaf_names,
        }
    ]
    nodes.extend(
        {
            "name": f"q2_{signal}",
            "quarter": "q2",
            "parent": "q1_root",
            "probability": 1.0 / 3.0,
            "leaves": signal_groups[signal],
        }
        for signal in Q2_SIGNALS
    )
    nodes.extend(
        {
            "name": f"q3_{signal}_{project}",
            "quarter": "q3",
            "parent": f"q2_{signal}",
            "probability": 1.0 / 6.0,
            "leaves": signal_project_groups[(signal, project)],
        }
        for signal in Q2_SIGNALS
        for project in PROJECT_DELAYS
    )
    nodes.extend(
        {
            "name": f"q4_{leaf['name']}",
            "quarter": "q4",
            "parent": (
                f"q3_{DEMAND_PATHS[leaf['demand_state']][0]}_"
                f"{leaf['project_state']}"
            ),
            "probability": 1.0 / 12.0,
            "leaves": [leaf["name"]],
        }
        for leaf in leaves
    )

    all_group = [leaf_names]
    natural_groups = {
        "q1": all_group,
        "q2": [signal_groups[signal] for signal in Q2_SIGNALS],
        "q3": [
            signal_project_groups[(signal, project)]
            for signal in Q2_SIGNALS
            for project in PROJECT_DELAYS
        ],
        "q4": singletons,
    }
    policies = {
        "B3": {
            "role": "two_stage_root_commitment",
            "implementable": True,
            "decision_variables": ["F", "X", "z_start"],
            "decision_groups": {quarter: all_group for quarter in QUARTERS},
        },
        "B4": {
            "role": "multistage_nonanticipative_policy",
            "implementable": True,
            "decision_variables": ["F", "X", "z_start"],
            "decision_groups": natural_groups,
        },
        "B5": {
            "role": "perfect_information_bound",
            "implementable": False,
            "decision_variables": ["F", "X", "z_start"],
            "decision_groups": {
                quarter: singletons for quarter in QUARTERS
            },
        },
    }

    return {
        "scenario_tree": {
            "id": "rts24_b3_b5_synthetic_tree_v1",
            "parameter_status": (
                "synthetic_scenario_structure_mechanism_gate_not_site_evidence"
            ),
            "probability_basis": (
                "balanced_synthetic_factorial_mechanism_design_not_empirical_probability"
            ),
            "common_input_config": "configs/rts24_deterministic_baselines.yaml",
            "common_input_signature_id": "rts24_b0_b2_common_inputs_v1",
            "common_input_signature_schema": "rts24_common_fair_inputs_v2",
            "common_input_signature_sha256": (
                "76cda29db68705cc3f2ef5025f32d30ef07ceea62a552a97c45b01bf83287794"
            ),
            "objective_hierarchy": [
                "minimize_probability_weighted_physical_access_shortfall",
                "report_min_and_max_probability_weighted_total_contract_capacity_exposure",
                "fix_minimum_total_contract_capacity_exposure_for_display",
                "report_min_and_max_probability_weighted_conditional_capacity_exposure",
                "apply_non_economic_project_normalization_only_after_physical_faces_are_locked",
            ],
            "security_certified": False,
            "project_timing": {
                "base_lead_time_quarters": 2,
                "signal_interpretation": (
                    "exogenous_delivery_regime_or_progress_signal"
                ),
                "decision_dependent_project_progress_modeled": False,
            },
            "quarters": list(QUARTERS),
            "revelation": {
                "q2_signal_before": "q2",
                "project_state_before": "q3",
                "terminal_outcome_before": "q4",
            },
            "demand_states": [
                {
                    "name": name,
                    "probability": 1.0 / 6.0,
                    "q2_signal": signal,
                    "terminal_outcome": outcome,
                    "demand_mw": list(path),
                }
                for name, (signal, outcome, path) in DEMAND_PATHS.items()
            ],
            "project_states": [
                {
                    "name": name,
                    "probability": 0.5,
                    "extra_lead_time_quarters": delay,
                }
                for name, delay in PROJECT_DELAYS.items()
            ],
            "leaves": leaves,
            "nodes": nodes,
            "policies": policies,
        }
    }


def _policy_by_name(tree, name):
    return next(policy for policy in tree.policies if policy.name == name)


def test_valid_tree_is_loaded_as_immutable_model_ready_data(tmp_path):
    path = tmp_path / "frozen.yaml"
    path.write_text(
        yaml.safe_dump(_valid_config(), sort_keys=False),
        encoding="utf-8",
    )

    tree = load_frozen_scenario_tree(path)

    assert isinstance(tree, FrozenScenarioTree)
    assert tree.objective_hierarchy[0] == (
        "minimize_probability_weighted_physical_access_shortfall"
    )
    assert not tree.security_certified
    assert tree.project_timing.base_lead_time_quarters == 2
    assert tree.quarters == QUARTERS
    assert len(tree.leaves) == 12
    assert [len(tree.nodes_for_quarter(quarter)) for quarter in tree.quarters] == [
        1,
        3,
        6,
        12,
    ]
    assert [len(tree.decision_groups("B4", quarter)) for quarter in QUARTERS] == [
        1,
        3,
        6,
        12,
    ]
    assert len(tree.decision_groups("B3", "q4")) == 1
    assert len(tree.decision_groups("B5", "q1")) == 12
    assert tree.information_groups("B4", "q3") == tree.decision_groups(
        "B4", "q3"
    )
    assert _policy_by_name(tree, "B5").implementable is False
    assert _policy_by_name(tree, "B4").decision_variables == (
        "F",
        "X",
        "z_start",
    )
    with pytest.raises(FrozenInstanceError):
        tree.q2_signal_reveal_before = "q1"


def test_repository_frozen_scenario_config_loads():
    repository_root = Path(__file__).resolve().parents[1]
    config_path = (
        repository_root / "configs" / "rts24_stochastic_baselines.yaml"
    )

    tree = load_frozen_scenario_tree(config_path)

    assert tree.id == "rts24_b3_b5_synthetic_tree_v1"
    assert tree.leaf_names == tuple(
        f"{demand}__{project}"
        for demand in DEMAND_PATHS
        for project in PROJECT_DELAYS
    )
    assert [leaf.probability for leaf in tree.leaves] == pytest.approx(
        [1.0 / 12.0] * 12
    )

    common_path = repository_root / tree.common_input_config
    common = yaml.safe_load(common_path.read_text(encoding="utf-8"))
    live_signature = common_input_signature_for_config(common_path)
    assert tree.common_input_signature_id == live_signature[
        "common_input_signature_id"
    ]
    assert tree.common_input_signature_schema == live_signature[
        "common_input_signature_schema"
    ]
    assert tree.common_input_signature_sha256 == live_signature[
        "common_input_signature_sha256"
    ]
    baseline_demand = tuple(
        float(quarter["data_center_demand_mw"])
        for quarter in common["planning"]["quarters"]
    )
    demand_by_name = {state.name: state for state in tree.demand_states}
    assert demand_by_name["baseline_upper"].demand_mw == baseline_demand
    assert (
        tree.project_timing.base_lead_time_quarters
        == common["existing_branch_upgrade"]["lead_time_quarters"]
    )
    assert max(
        value
        for state in tree.demand_states
        for value in state.demand_mw
    ) <= float(common["fixed_poi"]["application_capacity_mw"])
    assert common["validation"]["security_certified"] is False


def test_natural_nodes_preserve_unrevealed_terminal_outcomes():
    tree = parse_frozen_scenario_tree(_valid_config())
    leaf_by_name = {leaf.name: leaf for leaf in tree.leaves}
    demand_by_name = {state.name: state for state in tree.demand_states}

    for node in tree.nodes_for_quarter("q2"):
        paths = [
            demand_by_name[leaf_by_name[name].demand_state]
            for name in node.leaves
        ]
        assert {path.q2_signal for path in paths} in (
            {"delayed"},
            {"baseline"},
            {"accelerated"},
        )
        assert {path.terminal_outcome for path in paths} == {"lower", "upper"}
        assert {leaf_by_name[name].project_state for name in node.leaves} == set(
            PROJECT_DELAYS
        )

    for node in tree.nodes_for_quarter("q3"):
        paths = [
            demand_by_name[leaf_by_name[name].demand_state]
            for name in node.leaves
        ]
        assert len({path.q2_signal for path in paths}) == 1
        assert {path.terminal_outcome for path in paths} == {"lower", "upper"}
        assert len({leaf_by_name[name].project_state for name in node.leaves}) == 1


def test_natural_nodes_are_distinct_from_planning_decision_groups():
    tree = parse_frozen_scenario_tree(_valid_config())

    assert len(tree.nodes_for_quarter("q4")) == 12
    assert len(tree.decision_groups("B3", "q4")) == 1
    assert len(tree.decision_groups("B4", "q4")) == 12
    assert len(tree.decision_groups("B5", "q4")) == 12


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        (
            lambda config: config["scenario_tree"]["leaves"].append(
                deepcopy(config["scenario_tree"]["leaves"][0])
            ),
            "duplicate names",
        ),
        (
            lambda config: config["scenario_tree"]["leaves"].pop(),
            "complete demand/project Cartesian product",
        ),
    ),
)
def test_duplicate_or_missing_leaves_are_rejected(mutation, message):
    config = _valid_config()
    mutation(config)

    with pytest.raises(ValueError, match=message):
        parse_frozen_scenario_tree(config)


def test_factor_probabilities_must_be_normalized():
    config = _valid_config()
    config["scenario_tree"]["demand_states"][0]["probability"] = 0.2

    with pytest.raises(ValueError, match="probabilities must sum to 1"):
        parse_frozen_scenario_tree(config)


def test_leaf_probability_must_equal_factor_product():
    config = _valid_config()
    config["scenario_tree"]["leaves"][0]["probability"] = 0.2

    with pytest.raises(ValueError, match="factor probability product"):
        parse_frozen_scenario_tree(config)


@pytest.mark.parametrize(
    ("values", "message"),
    (
        ([50.0, float("nan"), 100.0, 200.0], "finite number"),
        ([50.0, -1.0, 100.0, 200.0], "nonnegative"),
        ([50.0, 100.0, 90.0, 200.0], "nondecreasing"),
    ),
)
def test_invalid_demand_paths_are_rejected(values, message):
    config = _valid_config()
    config["scenario_tree"]["demand_states"][0]["demand_mw"] = values

    with pytest.raises(ValueError, match=message):
        parse_frozen_scenario_tree(config)


def test_non_frozen_but_monotone_demand_path_is_rejected():
    config = _valid_config()
    config["scenario_tree"]["demand_states"][0]["demand_mw"][-1] = 210.0

    with pytest.raises(ValueError, match="frozen demand path"):
        parse_frozen_scenario_tree(config)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("q2_signal", "baseline", "wrong frozen q2_signal"),
        ("terminal_outcome", "upper", "wrong frozen terminal_outcome"),
    ),
)
def test_demand_revelation_labels_are_frozen(field, value, message):
    config = _valid_config()
    config["scenario_tree"]["demand_states"][0][field] = value

    with pytest.raises(ValueError, match=message):
        parse_frozen_scenario_tree(config)


def test_illegal_project_delay_is_rejected():
    config = _valid_config()
    config["scenario_tree"]["project_states"][1][
        "extra_lead_time_quarters"
    ] = 2

    with pytest.raises(ValueError, match="integer 0 or 1"):
        parse_frozen_scenario_tree(config)


def test_tree_parent_must_be_consistent_with_leaf_history():
    config = _valid_config()
    q3_node = next(
        node
        for node in config["scenario_tree"]["nodes"]
        if node["name"] == "q3_delayed_on_time"
    )
    q3_node["parent"] = "q2_baseline"

    with pytest.raises(ValueError, match="inconsistent with parent"):
        parse_frozen_scenario_tree(config)


def test_node_probability_must_equal_covered_leaf_probability():
    config = _valid_config()
    config["scenario_tree"]["nodes"][0]["probability"] = 0.9

    with pytest.raises(ValueError, match="leaf probability sum"):
        parse_frozen_scenario_tree(config)


def test_nodes_must_cover_every_leaf_once_per_quarter():
    config = _valid_config()
    q2_node = next(
        node
        for node in config["scenario_tree"]["nodes"]
        if node["name"] == "q2_delayed"
    )
    q2_node["leaves"].pop()
    q2_node["probability"] = 0.25

    with pytest.raises(ValueError, match="not a partition"):
        parse_frozen_scenario_tree(config)


def test_q2_cannot_split_by_unrevealed_terminal_outcome():
    config = _valid_config()
    leaves = config["scenario_tree"]["leaves"]
    nodes = config["scenario_tree"]["nodes"]
    nodes[:] = [node for node in nodes if node["quarter"] != "q2"]
    nodes.extend(
        {
            "name": f"q2_{demand}",
            "quarter": "q2",
            "parent": "q1_root",
            "probability": 1.0 / 6.0,
            "leaves": [
                leaf["name"]
                for leaf in leaves
                if leaf["demand_state"] == demand
            ],
        }
        for demand in DEMAND_PATHS
    )

    with pytest.raises(ValueError, match="frozen natural-tree partition"):
        parse_frozen_scenario_tree(config)


def test_decision_groups_must_be_partitions():
    config = _valid_config()
    groups = config["scenario_tree"]["policies"]["B5"]["decision_groups"]["q1"]
    groups[1][0] = groups[0][0]

    with pytest.raises(ValueError, match="not a partition"):
        parse_frozen_scenario_tree(config)


def test_decision_partition_must_match_policy_revelation_rule():
    config = _valid_config()
    leaves = config["scenario_tree"]["leaves"]
    config["scenario_tree"]["policies"]["B4"]["decision_groups"]["q2"] = [
        [leaf["name"] for leaf in leaves if leaf["project_state"] == project]
        for project in PROJECT_DELAYS
    ]

    with pytest.raises(ValueError, match="frozen B4 revelation rule"):
        parse_frozen_scenario_tree(config)


@pytest.mark.parametrize(
    ("policy", "value", "message"),
    (
        ("B5", True, "must remain False"),
        ("B3", 1, "must be bool"),
    ),
)
def test_policy_implementability_is_strict_and_frozen(policy, value, message):
    config = _valid_config()
    config["scenario_tree"]["policies"][policy]["implementable"] = value

    with pytest.raises(ValueError, match=message):
        parse_frozen_scenario_tree(config)


def test_natural_project_state_v_is_not_a_planning_decision_variable():
    config = _valid_config()
    config["scenario_tree"]["policies"]["B4"]["decision_variables"].append("v")

    with pytest.raises(ValueError, match=r"exactly \[F, X, z_start\]"):
        parse_frozen_scenario_tree(config)


def test_policy_roles_are_frozen():
    config = _valid_config()
    config["scenario_tree"]["policies"]["B3"]["role"] = (
        "multistage_nonanticipative_policy"
    )

    with pytest.raises(ValueError, match="frozen v1 role"):
        parse_frozen_scenario_tree(config)


def test_revelation_quarters_are_frozen():
    config = _valid_config()
    config["scenario_tree"]["revelation"]["terminal_outcome_before"] = "q3"

    with pytest.raises(ValueError, match="terminal_outcome before q4"):
        parse_frozen_scenario_tree(config)


def test_objective_hierarchy_metadata_must_be_present_and_nonempty():
    config = _valid_config()
    config["scenario_tree"]["objective_hierarchy"] = []

    with pytest.raises(ValueError, match="objective_hierarchy must be nonempty"):
        parse_frozen_scenario_tree(config)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("id", "rts24_b3_b5_synthetic_tree_v2", "frozen v1 value"),
        (
            "probability_basis",
            "empirical_probability",
            "frozen v1 value",
        ),
        (
            "common_input_signature_id",
            "changed_inputs",
            "frozen v1 value",
        ),
        (
            "common_input_signature_schema",
            "rts24_common_fair_inputs_v3",
            "frozen v1 value",
        ),
        (
            "common_input_signature_sha256",
            "0" * 64,
            "frozen v1 value",
        ),
        (
            "objective_hierarchy",
            ["minimize_probability_weighted_physical_access_shortfall"],
            "frozen v1 order",
        ),
    ),
)
def test_frozen_metadata_cannot_drift(field, value, message):
    config = _valid_config()
    config["scenario_tree"][field] = value

    with pytest.raises(ValueError, match=message):
        parse_frozen_scenario_tree(config)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        (
            "base_lead_time_quarters",
            3,
            "must equal the frozen common-input value 2",
        ),
        (
            "decision_dependent_project_progress_modeled",
            True,
            "must remain false",
        ),
        (
            "signal_interpretation",
            "project_specific_realized_progress",
            "frozen exogenous-signal label",
        ),
    ),
)
def test_project_timing_semantics_are_frozen(field, value, message):
    config = _valid_config()
    config["scenario_tree"]["project_timing"][field] = value

    with pytest.raises(ValueError, match=message):
        parse_frozen_scenario_tree(config)
