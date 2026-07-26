from collections import Counter
from pathlib import Path

import pytest
import yaml

from src.evaluation.stochastic_policy import (
    load_stochastic_holdout_protocol,
    map_fixed_policy_path,
    map_observed_history_to_group,
    map_q2_demand_class,
    map_q4_terminal_outcome,
)


CONFIG_PATH = Path("configs/rts24_stochastic_holdout.yaml")


@pytest.fixture(scope="module")
def protocol():
    return load_stochastic_holdout_protocol(CONFIG_PATH)


def _leaf_name(demand_path, project_state):
    return f"{demand_path}__{project_state}"


def test_holdout_is_balanced_disjoint_and_deterministic(protocol):
    assert len(protocol.demand_paths) == 6
    assert len(protocol.project_states) == 2
    assert len(protocol.leaves) == 12
    assert sum(leaf.probability for leaf in protocol.leaves) == pytest.approx(1.0)

    training_paths = {
        state.demand_mw for state in protocol.training_tree.demand_states
    }
    assert all(path.demand_mw not in training_paths for path in protocol.demand_paths)
    cells = Counter(
        (
            map_q2_demand_class(protocol, path.demand_mw[1]),
            map_q4_terminal_outcome(protocol, path.demand_mw[3]),
        )
        for path in protocol.demand_paths
    )
    assert cells == {
        ("delayed", "lower"): 1,
        ("delayed", "upper"): 1,
        ("baseline", "lower"): 1,
        ("baseline", "upper"): 1,
        ("accelerated", "lower"): 1,
        ("accelerated", "upper"): 1,
    }


def test_mapping_uses_only_information_revealed_before_each_decision(protocol):
    lower_on_time = map_fixed_policy_path(
        protocol,
        policy="B4",
        endpoint="minimum_x",
        holdout_leaf=_leaf_name("holdout_delayed_lower", "on_time"),
    )
    upper_on_time = map_fixed_policy_path(
        protocol,
        policy="B4",
        endpoint="minimum_x",
        holdout_leaf=_leaf_name("holdout_delayed_upper", "on_time"),
    )
    lower_delayed = map_fixed_policy_path(
        protocol,
        policy="B4",
        endpoint="minimum_x",
        holdout_leaf=_leaf_name(
            "holdout_delayed_lower", "delayed_one_quarter"
        ),
    )

    assert lower_on_time.decision_group_by_quarter["q1"] == "q1_g0"
    assert lower_on_time.decision_group_by_quarter["q2"] == "q2_g0"
    assert upper_on_time.decision_group_by_quarter["q2"] == "q2_g0"
    assert lower_delayed.decision_group_by_quarter["q2"] == "q2_g0"
    assert (
        lower_on_time.decision_group_by_quarter["q3"]
        == upper_on_time.decision_group_by_quarter["q3"]
        == "q3_g0"
    )
    assert lower_delayed.decision_group_by_quarter["q3"] == "q3_g1"
    assert lower_on_time.decision_group_by_quarter["q4"] == "q4_g0"
    assert upper_on_time.decision_group_by_quarter["q4"] == "q4_g2"


@pytest.mark.parametrize(
    ("quarter", "kwargs", "message"),
    (
        ("q1", {"q2_demand_mw": 60.0}, "q2 demand cannot"),
        (
            "q2",
            {"q2_demand_mw": 60.0, "project_extra_lead_time_quarters": 0},
            "Project state cannot",
        ),
        (
            "q3",
            {
                "q2_demand_mw": 60.0,
                "project_extra_lead_time_quarters": 0,
                "q4_demand_mw": 210.0,
            },
            "Terminal demand cannot",
        ),
    ),
)
def test_mapping_rejects_future_information(protocol, quarter, kwargs, message):
    with pytest.raises(ValueError, match=message):
        map_observed_history_to_group(
            protocol,
            policy="B4",
            quarter=quarter,
            **kwargs,
        )


def test_mapping_boundaries_are_frozen_to_upper_bucket(protocol):
    assert map_q2_demand_class(protocol, 74.999) == "delayed"
    assert map_q2_demand_class(protocol, 75.0) == "baseline"
    assert map_q2_demand_class(protocol, 150.0) == "accelerated"
    assert map_q4_terminal_outcome(protocol, 224.999) == "lower"
    assert map_q4_terminal_outcome(protocol, 225.0) == "upper"


@pytest.mark.parametrize("policy", ("B3", "B4"))
@pytest.mark.parametrize("endpoint", ("minimum_x", "maximum_x"))
def test_every_frozen_implementable_endpoint_maps_without_reoptimization(
    protocol,
    policy,
    endpoint,
):
    mapped = [
        map_fixed_policy_path(
            protocol,
            policy=policy,
            endpoint=endpoint,
            holdout_leaf=leaf.name,
        )
        for leaf in protocol.leaves
    ]

    assert len(mapped) == 12
    assert all(item.project_start_quarter == "q1" for item in mapped)
    assert all(
        item.parameter_status.endswith("without_planning_reoptimization")
        for item in mapped
    )
    if policy == "B3":
        for quarter in protocol.quarters:
            assert len(
                {item.decision_group_by_quarter[quarter] for item in mapped}
            ) == 1


def test_b5_cannot_be_mapped_as_an_implementable_holdout_policy(protocol):
    with pytest.raises(ValueError, match="Only implementable B3/B4"):
        map_observed_history_to_group(
            protocol,
            policy="B5",
            quarter="q1",
        )
    with pytest.raises(ValueError, match="Unknown frozen policy endpoint"):
        protocol.policy_endpoint("B5", "minimum_x")


def test_training_endpoint_hash_drift_closes_the_holdout_gate(tmp_path):
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    source = Path(config["training_artifacts"]["endpoint_path"])
    drifted = tmp_path / "drifted_endpoints.csv"
    drifted.write_bytes(source.read_bytes() + b"\n")
    config["training_artifacts"]["endpoint_path"] = str(drifted)
    config_path = tmp_path / "holdout.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    with pytest.raises(ValueError, match="SHA-256 does not match"):
        load_stochastic_holdout_protocol(config_path)
