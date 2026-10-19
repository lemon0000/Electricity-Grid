"""Validated frozen scenario data for the B3--B5 stochastic baselines."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import isclose, isfinite
from numbers import Real
from pathlib import Path

import yaml

from .common_input_signature import COMMON_INPUT_SIGNATURE_SCHEMA


_PROBABILITY_TOLERANCE = 1.0e-10
_FROZEN_QUARTERS = ("q1", "q2", "q3", "q4")
_FROZEN_DEMAND_PATHS = {
    "delayed_lower": ("delayed", "lower", (50.0, 50.0, 100.0, 200.0)),
    "delayed_upper": ("delayed", "upper", (50.0, 50.0, 100.0, 250.0)),
    "baseline_lower": ("baseline", "lower", (50.0, 100.0, 200.0, 200.0)),
    "baseline_upper": ("baseline", "upper", (50.0, 100.0, 200.0, 250.0)),
    "accelerated_lower": (
        "accelerated",
        "lower",
        (50.0, 200.0, 200.0, 200.0),
    ),
    "accelerated_upper": (
        "accelerated",
        "upper",
        (50.0, 200.0, 200.0, 250.0),
    ),
}
_FROZEN_Q2_SIGNALS = ("delayed", "baseline", "accelerated")
_FROZEN_TERMINAL_OUTCOMES = ("lower", "upper")
_FROZEN_PROJECT_DELAYS = {
    "on_time": 0,
    "delayed_one_quarter": 1,
}
_FROZEN_POLICIES = ("B3", "B4", "B5")
_FROZEN_POLICY_ROLES = {
    "B3": "two_stage_root_commitment",
    "B4": "multistage_nonanticipative_policy",
    "B5": "perfect_information_bound",
}
_FROZEN_POLICY_IMPLEMENTABLE = {"B3": True, "B4": True, "B5": False}
_FROZEN_DECISION_VARIABLES = ("F", "X", "z_start")
_FROZEN_METADATA = {
    "id": "rts24_b3_b5_synthetic_tree_v1",
    "parameter_status": (
        "synthetic_scenario_structure_mechanism_gate_not_site_evidence"
    ),
    "probability_basis": (
        "balanced_synthetic_factorial_mechanism_design_not_empirical_probability"
    ),
    "common_input_config": "configs/rts24_deterministic_baselines.yaml",
    "common_input_signature_id": "rts24_b0_b2_common_inputs_v1",
    "common_input_signature_schema": COMMON_INPUT_SIGNATURE_SCHEMA,
    "common_input_signature_sha256": (
        "76cda29db68705cc3f2ef5025f32d30ef07ceea62a552a97c45b01bf83287794"
    ),
}
_FROZEN_OBJECTIVE_HIERARCHY = (
    "minimize_probability_weighted_physical_access_shortfall",
    "report_min_and_max_probability_weighted_total_contract_capacity_exposure",
    "fix_minimum_total_contract_capacity_exposure_for_display",
    "report_min_and_max_probability_weighted_conditional_capacity_exposure",
    "apply_non_economic_project_normalization_only_after_physical_faces_are_locked",
)
_FROZEN_PROJECT_SIGNAL = "exogenous_delivery_regime_or_progress_signal"


@dataclass(frozen=True)
class DemandState:
    name: str
    probability: float
    q2_signal: str
    terminal_outcome: str
    demand_mw: tuple[float, ...]


@dataclass(frozen=True)
class ProjectState:
    name: str
    probability: float
    extra_lead_time_quarters: int


@dataclass(frozen=True)
class ScenarioLeaf:
    name: str
    demand_state: str
    project_state: str
    probability: float


@dataclass(frozen=True)
class ScenarioNode:
    name: str
    quarter: str
    parent: str | None
    probability: float
    leaves: tuple[str, ...]


@dataclass(frozen=True)
class QuarterDecisionGroups:
    quarter: str
    groups: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class PlanningPolicy:
    name: str
    role: str
    implementable: bool
    decision_variables: tuple[str, ...]
    decision_groups: tuple[QuarterDecisionGroups, ...]


@dataclass(frozen=True)
class ProjectTiming:
    base_lead_time_quarters: int
    signal_interpretation: str
    decision_dependent_project_progress_modeled: bool


@dataclass(frozen=True)
class FrozenScenarioTree:
    id: str
    parameter_status: str
    probability_basis: str
    common_input_config: str
    common_input_signature_id: str
    common_input_signature_schema: str
    common_input_signature_sha256: str
    objective_hierarchy: tuple[str, ...]
    security_certified: bool
    project_timing: ProjectTiming
    quarters: tuple[str, ...]
    q2_signal_reveal_before: str
    project_state_reveal_before: str
    terminal_outcome_reveal_before: str
    demand_states: tuple[DemandState, ...]
    project_states: tuple[ProjectState, ...]
    leaves: tuple[ScenarioLeaf, ...]
    nodes: tuple[ScenarioNode, ...]
    policies: tuple[PlanningPolicy, ...]

    @property
    def leaf_names(self) -> tuple[str, ...]:
        return tuple(leaf.name for leaf in self.leaves)

    def nodes_for_quarter(self, quarter: str) -> tuple[ScenarioNode, ...]:
        return tuple(node for node in self.nodes if node.quarter == quarter)

    def decision_groups(
        self,
        policy: str,
        quarter: str,
    ) -> tuple[tuple[str, ...], ...]:
        for planning_policy in self.policies:
            if planning_policy.name != policy:
                continue
            for quarter_groups in planning_policy.decision_groups:
                if quarter_groups.quarter == quarter:
                    return quarter_groups.groups
        raise KeyError((policy, quarter))

    def information_groups(
        self,
        policy: str,
        quarter: str,
    ) -> tuple[tuple[str, ...], ...]:
        """Compatibility alias for planning ``decision_groups``."""

        return self.decision_groups(policy, quarter)


def _as_mapping(value: object, path: str) -> Mapping[object, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be a mapping")
    return value


def _as_sequence(value: object, path: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{path} must be a sequence")
    return value


def _exact_keys(
    value: Mapping[object, object],
    expected: set[str],
    path: str,
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(str(key) for key in actual - expected)
        raise ValueError(
            f"{path} fields must match the frozen schema; "
            f"missing={missing}, extra={extra}"
        )


def _name(value: object, path: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{path} must be a nonempty trimmed string")
    return value


def _finite_number(value: object, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValueError(f"{path} must be a finite number")
    return float(value)


def _probability(value: object, path: str) -> float:
    probability = _finite_number(value, path)
    if probability < 0.0 or probability > 1.0:
        raise ValueError(f"{path} must be between zero and one")
    return probability


def _close(first: float, second: float) -> bool:
    return isclose(
        first,
        second,
        rel_tol=0.0,
        abs_tol=_PROBABILITY_TOLERANCE,
    )


def _require_unique(values: Sequence[str], path: str) -> None:
    if len(set(values)) != len(values):
        raise ValueError(f"{path} contains duplicate names")


def _parse_demand_states(
    raw_states: object,
    quarter_count: int,
) -> tuple[DemandState, ...]:
    states = []
    for index, raw_state in enumerate(_as_sequence(raw_states, "demand_states")):
        path = f"demand_states[{index}]"
        state = _as_mapping(raw_state, path)
        _exact_keys(
            state,
            {
                "name",
                "probability",
                "q2_signal",
                "terminal_outcome",
                "demand_mw",
            },
            path,
        )
        name = _name(state["name"], f"{path}.name")
        probability = _probability(state["probability"], f"{path}.probability")
        q2_signal = _name(state["q2_signal"], f"{path}.q2_signal")
        terminal_outcome = _name(
            state["terminal_outcome"], f"{path}.terminal_outcome"
        )
        raw_demand = _as_sequence(state["demand_mw"], f"{path}.demand_mw")
        if len(raw_demand) != quarter_count:
            raise ValueError(
                f"{path}.demand_mw must have one value per quarter"
            )
        demand_mw = tuple(
            _finite_number(value, f"{path}.demand_mw[{position}]")
            for position, value in enumerate(raw_demand)
        )
        if any(value < 0.0 for value in demand_mw):
            raise ValueError(f"{path}.demand_mw must be nonnegative")
        if any(
            next_value < value
            for value, next_value in zip(demand_mw, demand_mw[1:])
        ):
            raise ValueError(f"{path}.demand_mw must be nondecreasing")
        states.append(
            DemandState(
                name=name,
                probability=probability,
                q2_signal=q2_signal,
                terminal_outcome=terminal_outcome,
                demand_mw=demand_mw,
            )
        )

    names = [state.name for state in states]
    _require_unique(names, "demand_states")
    if set(names) != set(_FROZEN_DEMAND_PATHS):
        raise ValueError("demand_states must contain the six frozen demand paths")
    if not _close(sum(state.probability for state in states), 1.0):
        raise ValueError("demand path probabilities must sum to 1")
    for state in states:
        if not _close(state.probability, 1.0 / 6.0):
            raise ValueError(
                f"demand path {state.name} probability must equal 1/6"
            )
        expected_signal, expected_outcome, expected_path = _FROZEN_DEMAND_PATHS[
            state.name
        ]
        if state.q2_signal != expected_signal:
            raise ValueError(
                f"demand path {state.name} has the wrong frozen q2_signal"
            )
        if state.terminal_outcome != expected_outcome:
            raise ValueError(
                f"demand path {state.name} has the wrong frozen terminal_outcome"
            )
        if state.demand_mw != expected_path:
            raise ValueError(
                f"demand path {state.name} does not match its frozen demand path"
            )
    for signal in _FROZEN_Q2_SIGNALS:
        signal_probability = sum(
            state.probability for state in states if state.q2_signal == signal
        )
        if not _close(signal_probability, 1.0 / 3.0):
            raise ValueError(f"q2_signal {signal} probability must equal 1/3")
        outcomes = {
            state.terminal_outcome for state in states if state.q2_signal == signal
        }
        if outcomes != set(_FROZEN_TERMINAL_OUTCOMES):
            raise ValueError(
                f"q2_signal {signal} must retain lower and upper terminal outcomes"
            )
    return tuple(states)


def _parse_project_states(raw_states: object) -> tuple[ProjectState, ...]:
    states = []
    for index, raw_state in enumerate(_as_sequence(raw_states, "project_states")):
        path = f"project_states[{index}]"
        state = _as_mapping(raw_state, path)
        _exact_keys(
            state,
            {"name", "probability", "extra_lead_time_quarters"},
            path,
        )
        delay = state["extra_lead_time_quarters"]
        if type(delay) is not int or delay not in (0, 1):
            raise ValueError(
                f"{path}.extra_lead_time_quarters must be integer 0 or 1"
            )
        states.append(
            ProjectState(
                name=_name(state["name"], f"{path}.name"),
                probability=_probability(
                    state["probability"], f"{path}.probability"
                ),
                extra_lead_time_quarters=delay,
            )
        )

    names = [state.name for state in states]
    _require_unique(names, "project_states")
    if set(names) != set(_FROZEN_PROJECT_DELAYS):
        raise ValueError("project_states must contain the two frozen project states")
    if not _close(sum(state.probability for state in states), 1.0):
        raise ValueError("project state probabilities must sum to 1")
    for state in states:
        if not _close(state.probability, 0.5):
            raise ValueError(
                f"project state {state.name} probability must equal 1/2"
            )
        if state.extra_lead_time_quarters != _FROZEN_PROJECT_DELAYS[state.name]:
            raise ValueError(
                f"project state {state.name} has the wrong frozen delay"
            )
    return tuple(states)


def _parse_leaves(
    raw_leaves: object,
    demand_states: tuple[DemandState, ...],
    project_states: tuple[ProjectState, ...],
) -> tuple[ScenarioLeaf, ...]:
    leaves = []
    for index, raw_leaf in enumerate(_as_sequence(raw_leaves, "leaves")):
        path = f"leaves[{index}]"
        leaf = _as_mapping(raw_leaf, path)
        _exact_keys(
            leaf,
            {"name", "demand_state", "project_state", "probability"},
            path,
        )
        leaves.append(
            ScenarioLeaf(
                name=_name(leaf["name"], f"{path}.name"),
                demand_state=_name(
                    leaf["demand_state"], f"{path}.demand_state"
                ),
                project_state=_name(
                    leaf["project_state"], f"{path}.project_state"
                ),
                probability=_probability(
                    leaf["probability"], f"{path}.probability"
                ),
            )
        )

    _require_unique([leaf.name for leaf in leaves], "leaves")
    demand_by_name = {state.name: state for state in demand_states}
    project_by_name = {state.name: state for state in project_states}
    pairs = [(leaf.demand_state, leaf.project_state) for leaf in leaves]
    if len(set(pairs)) != len(pairs):
        raise ValueError("leaves contain a duplicate demand/project state pair")
    expected_pairs = {
        (demand_name, project_name)
        for demand_name in demand_by_name
        for project_name in project_by_name
    }
    actual_pairs = set(pairs)
    if actual_pairs != expected_pairs:
        missing = sorted(expected_pairs - actual_pairs)
        extra = sorted(actual_pairs - expected_pairs)
        raise ValueError(
            "leaves must be the complete demand/project Cartesian product; "
            f"missing={missing}, extra={extra}"
        )
    for leaf in leaves:
        factor_probability = (
            demand_by_name[leaf.demand_state].probability
            * project_by_name[leaf.project_state].probability
        )
        if not _close(leaf.probability, factor_probability):
            raise ValueError(
                f"leaf {leaf.name} probability must equal "
                "its factor probability product"
            )
    if not _close(sum(leaf.probability for leaf in leaves), 1.0):
        raise ValueError("leaf probabilities must sum to 1")
    return tuple(leaves)


def _parse_nodes(raw_nodes: object) -> tuple[ScenarioNode, ...]:
    nodes = []
    for index, raw_node in enumerate(_as_sequence(raw_nodes, "nodes")):
        path = f"nodes[{index}]"
        node = _as_mapping(raw_node, path)
        _exact_keys(
            node,
            {"name", "quarter", "parent", "probability", "leaves"},
            path,
        )
        parent = node["parent"]
        if parent is not None:
            parent = _name(parent, f"{path}.parent")
        raw_node_leaves = _as_sequence(node["leaves"], f"{path}.leaves")
        node_leaves = tuple(
            _name(leaf, f"{path}.leaves[{leaf_index}]")
            for leaf_index, leaf in enumerate(raw_node_leaves)
        )
        if not node_leaves:
            raise ValueError(f"{path}.leaves must be nonempty")
        if len(set(node_leaves)) != len(node_leaves):
            raise ValueError(f"{path}.leaves contains duplicate leaves")
        nodes.append(
            ScenarioNode(
                name=_name(node["name"], f"{path}.name"),
                quarter=_name(node["quarter"], f"{path}.quarter"),
                parent=parent,
                probability=_probability(
                    node["probability"], f"{path}.probability"
                ),
                leaves=node_leaves,
            )
        )
    _require_unique([node.name for node in nodes], "nodes")
    return tuple(nodes)


def _partition_signature(
    groups: Sequence[Sequence[str]],
) -> frozenset[frozenset[str]]:
    return frozenset(frozenset(group) for group in groups)


def _validate_leaf_partition(
    groups: Sequence[Sequence[str]],
    leaf_names: frozenset[str],
    path: str,
) -> None:
    seen = set()
    for group in groups:
        if not group:
            raise ValueError(f"{path} contains an empty leaf group")
        for leaf in group:
            if leaf not in leaf_names:
                raise ValueError(f"{path} references unknown leaf {leaf}")
            if leaf in seen:
                raise ValueError(f"{path} is not a partition; duplicate leaf {leaf}")
            seen.add(leaf)
    if seen != leaf_names:
        raise ValueError(
            f"{path} is not a partition; missing leaves={sorted(leaf_names - seen)}"
        )


def _natural_partitions(
    leaves: tuple[ScenarioLeaf, ...],
    demand_states: tuple[DemandState, ...],
    project_states: tuple[ProjectState, ...],
) -> dict[str, tuple[tuple[str, ...], ...]]:
    all_leaves = tuple(leaf.name for leaf in leaves)
    demand_by_name = {state.name: state for state in demand_states}
    signal_groups = tuple(
        tuple(
            leaf.name
            for leaf in leaves
            if demand_by_name[leaf.demand_state].q2_signal == signal
        )
        for signal in _FROZEN_Q2_SIGNALS
    )
    signal_project_groups = tuple(
        tuple(
            leaf.name
            for leaf in leaves
            if demand_by_name[leaf.demand_state].q2_signal == signal
            and leaf.project_state == project_state.name
        )
        for signal in _FROZEN_Q2_SIGNALS
        for project_state in project_states
    )
    singletons = tuple((leaf.name,) for leaf in leaves)
    return {
        "q1": (all_leaves,),
        "q2": signal_groups,
        "q3": signal_project_groups,
        "q4": singletons,
    }


def _validate_nodes(
    nodes: tuple[ScenarioNode, ...],
    quarters: tuple[str, ...],
    leaves: tuple[ScenarioLeaf, ...],
    demand_states: tuple[DemandState, ...],
    project_states: tuple[ProjectState, ...],
) -> None:
    leaf_names = frozenset(leaf.name for leaf in leaves)
    leaf_probability = {leaf.name: leaf.probability for leaf in leaves}
    node_by_name = {node.name: node for node in nodes}
    expected_partitions = _natural_partitions(
        leaves, demand_states, project_states
    )

    for node in nodes:
        if node.quarter not in quarters:
            raise ValueError(f"node {node.name} has unknown quarter {node.quarter}")
        expected_probability = sum(
            leaf_probability[name]
            for name in node.leaves
            if name in leaf_probability
        )
        unknown = set(node.leaves) - leaf_names
        if unknown:
            raise ValueError(
                f"node {node.name} references unknown leaves {sorted(unknown)}"
            )
        if not _close(node.probability, expected_probability):
            raise ValueError(
                f"node {node.name} probability does not equal its leaf probability sum"
            )

    nodes_by_quarter = {
        quarter: tuple(node for node in nodes if node.quarter == quarter)
        for quarter in quarters
    }
    for quarter in quarters:
        quarter_nodes = nodes_by_quarter[quarter]
        groups = tuple(node.leaves for node in quarter_nodes)
        _validate_leaf_partition(groups, leaf_names, f"nodes at {quarter}")
        if _partition_signature(groups) != _partition_signature(
            expected_partitions[quarter]
        ):
            raise ValueError(
                f"nodes at {quarter} do not match the frozen natural-tree partition"
            )
        if not _close(sum(node.probability for node in quarter_nodes), 1.0):
            raise ValueError(f"node probabilities at {quarter} must sum to 1")

    quarter_index = {quarter: index for index, quarter in enumerate(quarters)}
    for node in nodes:
        position = quarter_index[node.quarter]
        if position == 0:
            if node.parent is not None:
                raise ValueError(f"root node {node.name} must have no parent")
            continue
        if node.parent not in node_by_name:
            raise ValueError(f"node {node.name} references an unknown parent")
        parent = node_by_name[node.parent]
        expected_parent_quarter = quarters[position - 1]
        if parent.quarter != expected_parent_quarter:
            raise ValueError(
                f"node {node.name} parent must be in {expected_parent_quarter}"
            )
        if not set(node.leaves).issubset(parent.leaves):
            raise ValueError(
                f"node {node.name} leaves are inconsistent with parent {parent.name}"
            )

    for quarter in quarters[:-1]:
        for parent in nodes_by_quarter[quarter]:
            children = tuple(node for node in nodes if node.parent == parent.name)
            child_groups = tuple(child.leaves for child in children)
            _validate_leaf_partition(
                child_groups,
                frozenset(parent.leaves),
                f"children of node {parent.name}",
            )


def _parse_policies(
    raw_policy_data: object,
    quarters: tuple[str, ...],
    leaves: tuple[ScenarioLeaf, ...],
    demand_states: tuple[DemandState, ...],
    project_states: tuple[ProjectState, ...],
) -> tuple[PlanningPolicy, ...]:
    raw_policies = _as_mapping(raw_policy_data, "policies")
    _exact_keys(raw_policies, set(_FROZEN_POLICIES), "policies")
    leaf_names = frozenset(leaf.name for leaf in leaves)
    natural = _natural_partitions(leaves, demand_states, project_states)
    all_group = natural["q1"]
    singletons = natural["q4"]
    expected = {
        "B3": {quarter: all_group for quarter in quarters},
        "B4": natural,
        "B5": {quarter: singletons for quarter in quarters},
    }
    policies = []
    for policy in _FROZEN_POLICIES:
        policy_path = f"policies.{policy}"
        raw_policy = _as_mapping(raw_policies[policy], policy_path)
        _exact_keys(
            raw_policy,
            {"role", "implementable", "decision_variables", "decision_groups"},
            policy_path,
        )
        role = _name(raw_policy["role"], f"{policy_path}.role")
        if role != _FROZEN_POLICY_ROLES[policy]:
            raise ValueError(
                f"{policy_path}.role must equal the frozen v1 role "
                f"{_FROZEN_POLICY_ROLES[policy]}"
            )
        implementable = raw_policy["implementable"]
        if type(implementable) is not bool:
            raise ValueError(f"{policy_path}.implementable must be bool")
        if implementable is not _FROZEN_POLICY_IMPLEMENTABLE[policy]:
            raise ValueError(
                f"{policy_path}.implementable must remain "
                f"{_FROZEN_POLICY_IMPLEMENTABLE[policy]}"
            )
        decision_variables = tuple(
            _name(variable, f"{policy_path}.decision_variables[{index}]")
            for index, variable in enumerate(
                _as_sequence(
                    raw_policy["decision_variables"],
                    f"{policy_path}.decision_variables",
                )
            )
        )
        if decision_variables != _FROZEN_DECISION_VARIABLES:
            raise ValueError(
                f"{policy_path}.decision_variables must be exactly "
                "[F, X, z_start]"
            )
        raw_quarters = _as_mapping(
            raw_policy["decision_groups"], f"{policy_path}.decision_groups"
        )
        _exact_keys(
            raw_quarters,
            set(quarters),
            f"{policy_path}.decision_groups",
        )
        quarter_sets = []
        for quarter in quarters:
            path = f"{policy_path}.decision_groups.{quarter}"
            raw_groups = _as_sequence(raw_quarters[quarter], path)
            groups = tuple(
                tuple(
                    _name(leaf, f"{path}[{group_index}][{leaf_index}]")
                    for leaf_index, leaf in enumerate(
                        _as_sequence(raw_group, f"{path}[{group_index}]")
                    )
                )
                for group_index, raw_group in enumerate(raw_groups)
            )
            _validate_leaf_partition(groups, leaf_names, path)
            if _partition_signature(groups) != _partition_signature(
                expected[policy][quarter]
            ):
                raise ValueError(
                    f"{path} does not match the frozen {policy} revelation rule"
                )
            quarter_sets.append(
                QuarterDecisionGroups(quarter=quarter, groups=groups)
            )
        policies.append(
            PlanningPolicy(
                name=policy,
                role=role,
                implementable=implementable,
                decision_variables=decision_variables,
                decision_groups=tuple(quarter_sets),
            )
        )
    return tuple(policies)


def parse_frozen_scenario_tree(config: Mapping[object, object]) -> FrozenScenarioTree:
    """Validate a loaded configuration and return immutable scenario data."""

    root = _as_mapping(config, "config")
    if "scenario_tree" not in root:
        raise ValueError("config must contain scenario_tree")
    raw_tree = _as_mapping(root["scenario_tree"], "scenario_tree")
    _exact_keys(
        raw_tree,
        {
            "id",
            "parameter_status",
            "probability_basis",
            "common_input_config",
            "common_input_signature_id",
            "common_input_signature_schema",
            "common_input_signature_sha256",
            "objective_hierarchy",
            "security_certified",
            "project_timing",
            "quarters",
            "revelation",
            "demand_states",
            "project_states",
            "leaves",
            "nodes",
            "policies",
        },
        "scenario_tree",
    )

    metadata = {
        field: _name(raw_tree[field], f"scenario_tree.{field}")
        for field in (
            "id",
            "parameter_status",
            "probability_basis",
            "common_input_config",
            "common_input_signature_id",
            "common_input_signature_schema",
            "common_input_signature_sha256",
        )
    }
    for field, expected in _FROZEN_METADATA.items():
        if metadata[field] != expected:
            raise ValueError(
                f"scenario_tree.{field} must equal the frozen v1 value {expected}"
            )
    objective_hierarchy = tuple(
        _name(label, f"scenario_tree.objective_hierarchy[{index}]")
        for index, label in enumerate(
            _as_sequence(
                raw_tree["objective_hierarchy"],
                "scenario_tree.objective_hierarchy",
            )
        )
    )
    if not objective_hierarchy:
        raise ValueError("scenario_tree.objective_hierarchy must be nonempty")
    if objective_hierarchy != _FROZEN_OBJECTIVE_HIERARCHY:
        raise ValueError(
            "scenario_tree.objective_hierarchy must match the frozen v1 order"
        )
    security_certified = raw_tree["security_certified"]
    if type(security_certified) is not bool:
        raise ValueError("scenario_tree.security_certified must be bool")
    if security_certified:
        raise ValueError(
            "scenario_tree.security_certified must remain false "
            "for this frozen benchmark"
        )
    raw_project_timing = _as_mapping(
        raw_tree["project_timing"], "scenario_tree.project_timing"
    )
    _exact_keys(
        raw_project_timing,
        {
            "base_lead_time_quarters",
            "signal_interpretation",
            "decision_dependent_project_progress_modeled",
        },
        "scenario_tree.project_timing",
    )
    base_lead_time = raw_project_timing["base_lead_time_quarters"]
    if type(base_lead_time) is not int or base_lead_time < 0:
        raise ValueError(
            "scenario_tree.project_timing.base_lead_time_quarters "
            "must be a nonnegative integer"
        )
    if base_lead_time != 2:
        raise ValueError(
            "scenario_tree.project_timing.base_lead_time_quarters "
            "must equal the frozen common-input value 2"
        )
    decision_dependent_progress = raw_project_timing[
        "decision_dependent_project_progress_modeled"
    ]
    if type(decision_dependent_progress) is not bool:
        raise ValueError(
            "scenario_tree.project_timing."
            "decision_dependent_project_progress_modeled must be bool"
        )
    if decision_dependent_progress:
        raise ValueError(
            "scenario_tree.project_timing."
            "decision_dependent_project_progress_modeled must remain false"
        )
    signal_interpretation = _name(
        raw_project_timing["signal_interpretation"],
        "scenario_tree.project_timing.signal_interpretation",
    )
    if signal_interpretation != _FROZEN_PROJECT_SIGNAL:
        raise ValueError(
            "scenario_tree.project_timing.signal_interpretation must match "
            "the frozen exogenous-signal label"
        )
    project_timing = ProjectTiming(
        base_lead_time_quarters=base_lead_time,
        signal_interpretation=signal_interpretation,
        decision_dependent_project_progress_modeled=decision_dependent_progress,
    )

    quarters = tuple(
        _name(quarter, f"scenario_tree.quarters[{index}]")
        for index, quarter in enumerate(
            _as_sequence(raw_tree["quarters"], "scenario_tree.quarters")
        )
    )
    _require_unique(quarters, "scenario_tree.quarters")
    if quarters != _FROZEN_QUARTERS:
        raise ValueError("scenario_tree.quarters must be exactly q1, q2, q3, q4")

    revelation = _as_mapping(raw_tree["revelation"], "scenario_tree.revelation")
    _exact_keys(
        revelation,
        {
            "q2_signal_before",
            "project_state_before",
            "terminal_outcome_before",
        },
        "scenario_tree.revelation",
    )
    q2_signal_reveal_before = _name(
        revelation["q2_signal_before"],
        "scenario_tree.revelation.q2_signal_before",
    )
    project_state_reveal_before = _name(
        revelation["project_state_before"],
        "scenario_tree.revelation.project_state_before",
    )
    terminal_outcome_reveal_before = _name(
        revelation["terminal_outcome_before"],
        "scenario_tree.revelation.terminal_outcome_before",
    )
    if (
        q2_signal_reveal_before != "q2"
        or project_state_reveal_before != "q3"
        or terminal_outcome_reveal_before != "q4"
    ):
        raise ValueError(
            "scenario_tree revelation must be q2_signal before q2, "
            "project_state before q3, and terminal_outcome before q4"
        )

    demand_states = _parse_demand_states(
        raw_tree["demand_states"], len(quarters)
    )
    project_states = _parse_project_states(raw_tree["project_states"])
    leaves = _parse_leaves(raw_tree["leaves"], demand_states, project_states)
    nodes = _parse_nodes(raw_tree["nodes"])
    _validate_nodes(nodes, quarters, leaves, demand_states, project_states)
    policies = _parse_policies(
        raw_tree["policies"],
        quarters,
        leaves,
        demand_states,
        project_states,
    )
    return FrozenScenarioTree(
        id=metadata["id"],
        parameter_status=metadata["parameter_status"],
        probability_basis=metadata["probability_basis"],
        common_input_config=metadata["common_input_config"],
        common_input_signature_id=metadata["common_input_signature_id"],
        common_input_signature_schema=metadata["common_input_signature_schema"],
        common_input_signature_sha256=metadata["common_input_signature_sha256"],
        objective_hierarchy=objective_hierarchy,
        security_certified=security_certified,
        project_timing=project_timing,
        quarters=quarters,
        q2_signal_reveal_before=q2_signal_reveal_before,
        project_state_reveal_before=project_state_reveal_before,
        terminal_outcome_reveal_before=terminal_outcome_reveal_before,
        demand_states=demand_states,
        project_states=project_states,
        leaves=leaves,
        nodes=nodes,
        policies=policies,
    )


def load_frozen_scenario_tree(path: str | Path) -> FrozenScenarioTree:
    """Load YAML with ``safe_load`` and validate its frozen scenario section."""

    with Path(path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    return parse_frozen_scenario_tree(config)


__all__ = [
    "DemandState",
    "FrozenScenarioTree",
    "PlanningPolicy",
    "ProjectTiming",
    "ProjectState",
    "QuarterDecisionGroups",
    "ScenarioLeaf",
    "ScenarioNode",
    "load_frozen_scenario_tree",
    "parse_frozen_scenario_tree",
]
