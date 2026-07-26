"""Frozen-policy mapping for the M5c synthetic holdout gate."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Mapping

import yaml

from ..scenarios import FrozenScenarioTree, load_frozen_scenario_tree


_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_POLICIES = ("B3", "B4")
_ENDPOINTS = ("minimum_x", "maximum_x")
_ENDPOINT_FIELDS = (
    "policy",
    "role",
    "implementable",
    "endpoint",
    "leaf",
    "leaf_probability",
    "quarter",
    "demand_mw",
    "decision_group",
    "firm_capacity_mw",
    "conditional_capacity_mw",
    "total_capacity_mw",
    "connected_demand_mw",
    "firm_demand_mw",
    "active_conditional_demand_mw",
    "access_shortfall_mw",
    "project_start",
    "project_start_quarter",
    "project_available",
    "normalization_label",
)


@dataclass(frozen=True)
class HoldoutDemandPath:
    name: str
    probability: float
    demand_mw: tuple[float, ...]


@dataclass(frozen=True)
class HoldoutProjectState:
    name: str
    probability: float
    extra_lead_time_quarters: int


@dataclass(frozen=True)
class HoldoutLeaf:
    name: str
    demand_path: str
    project_state: str
    probability: float


@dataclass(frozen=True)
class FrozenPolicyDecision:
    quarter: str
    decision_group: str
    firm_capacity_mw: float
    conditional_capacity_mw: float
    total_capacity_mw: float
    project_start: bool


@dataclass(frozen=True)
class FrozenPolicyEndpoint:
    policy: str
    endpoint: str
    role: str
    implementable: bool
    normalization_label: str
    decisions: Mapping[tuple[str, str], FrozenPolicyDecision]


@dataclass(frozen=True)
class MappedFixedPolicy:
    policy: str
    endpoint: str
    holdout_leaf: str
    mapped_demand_class: str
    mapped_terminal_outcome: str
    mapped_project_state: str
    decision_group_by_quarter: Mapping[str, str]
    firm_capacity_mw: Mapping[str, float]
    conditional_capacity_mw: Mapping[str, float]
    total_capacity_mw: Mapping[str, float]
    project_start_by_quarter: Mapping[str, bool]
    project_start_quarter: str | None
    parameter_status: str


@dataclass(frozen=True)
class StochasticHoldoutProtocol:
    id: str
    parameter_status: str
    probability_basis: str
    selection_rule: str
    training_tree: FrozenScenarioTree
    training_summary_path: Path
    training_summary_sha256: str
    training_endpoint_path: Path
    training_endpoint_sha256: str
    quarters: tuple[str, ...]
    demand_paths: tuple[HoldoutDemandPath, ...]
    project_states: tuple[HoldoutProjectState, ...]
    leaves: tuple[HoldoutLeaf, ...]
    policy_endpoints: Mapping[tuple[str, str], FrozenPolicyEndpoint]
    q1_required_demand_mw: float
    q2_thresholds_mw: tuple[float, float]
    q2_labels: tuple[str, str, str]
    q4_threshold_mw: float
    q4_labels: tuple[str, str]
    project_state_mapping: Mapping[int, str]
    primary_objective_tolerance: float
    power_balance_tolerance_mw: float
    contract_breach_tolerance_mw: float
    path_output: Path
    summary_output: Path

    def demand_path(self, name: str) -> HoldoutDemandPath:
        return next(path for path in self.demand_paths if path.name == name)

    def project_state(self, name: str) -> HoldoutProjectState:
        return next(state for state in self.project_states if state.name == name)

    def policy_endpoint(self, policy: str, endpoint: str) -> FrozenPolicyEndpoint:
        try:
            return self.policy_endpoints[policy, endpoint]
        except KeyError as error:
            raise ValueError(f"Unknown frozen policy endpoint: {policy}/{endpoint}") from error


def _resolve_path(configured: object) -> Path:
    path = Path(str(configured))
    return path if path.is_absolute() else _REPOSITORY_ROOT / path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strict_json(path: Path) -> dict[str, object]:
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key in training summary: {key}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError(f"Non-finite JSON value in training summary: {value}")

    parsed = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicates,
        parse_constant=reject_constant,
    )
    if not isinstance(parsed, dict):
        raise ValueError("Training summary must be a JSON object")
    return parsed


def _finite_number(value: object, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _strict_bool(value: object, label: str) -> bool:
    if value == "True" or value is True:
        return True
    if value == "False" or value is False:
        return False
    raise ValueError(f"{label} must be True or False")


def _validate_hash(path: Path, expected: object, label: str) -> str:
    expected = str(expected).lower()
    actual = _sha256(path)
    if len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
        raise ValueError(f"{label} SHA-256 must contain 64 hexadecimal characters")
    if actual != expected:
        raise ValueError(f"{label} SHA-256 does not match the frozen artifact")
    return actual


def _load_policy_endpoints(
    path: Path,
    tree: FrozenScenarioTree,
) -> dict[tuple[str, str], FrozenPolicyEndpoint]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != _ENDPOINT_FIELDS:
            raise ValueError("Training endpoint CSV schema does not match M5b")
        rows = list(reader)

    endpoints = {}
    for policy in _POLICIES:
        planning_policy = next(item for item in tree.policies if item.name == policy)
        if not planning_policy.implementable:
            raise ValueError(f"Holdout policy {policy} must be implementable")
        for endpoint_name in _ENDPOINTS:
            selected = [
                row
                for row in rows
                if row["policy"] == policy and row["endpoint"] == endpoint_name
            ]
            if len(selected) != len(tree.leaves) * len(tree.quarters):
                raise ValueError(f"Incomplete training endpoint: {policy}/{endpoint_name}")
            decisions = {}
            labels = set()
            roles = set()
            implementable_values = set()
            for row in selected:
                quarter = row["quarter"]
                group = row["decision_group"]
                firm = _finite_number(row["firm_capacity_mw"], "Firm capacity")
                conditional = _finite_number(
                    row["conditional_capacity_mw"], "Conditional capacity"
                )
                total = _finite_number(row["total_capacity_mw"], "Total capacity")
                if min(firm, conditional, total) < 0.0:
                    raise ValueError("Frozen policy capacities must be nonnegative")
                if abs(total - firm - conditional) > 1.0e-7:
                    raise ValueError("Frozen policy total capacity must equal F + X")
                decision = FrozenPolicyDecision(
                    quarter=quarter,
                    decision_group=group,
                    firm_capacity_mw=firm,
                    conditional_capacity_mw=conditional,
                    total_capacity_mw=total,
                    project_start=_strict_bool(row["project_start"], "Project start"),
                )
                key = (quarter, group)
                if key in decisions and decisions[key] != decision:
                    raise ValueError("A frozen decision group contains inconsistent decisions")
                decisions[key] = decision
                labels.add(row["normalization_label"])
                roles.add(row["role"])
                implementable_values.add(
                    _strict_bool(row["implementable"], "Policy implementability")
                )

            expected_keys = {
                (quarter, f"{quarter}_g{position}")
                for quarter in tree.quarters
                for position, _group in enumerate(
                    tree.decision_groups(policy, quarter)
                )
            }
            if set(decisions) != expected_keys:
                raise ValueError("Frozen endpoint decision groups do not match the tree")
            if len(labels) != 1 or len(roles) != 1 or implementable_values != {True}:
                raise ValueError("Frozen endpoint metadata is inconsistent")
            endpoints[policy, endpoint_name] = FrozenPolicyEndpoint(
                policy=policy,
                endpoint=endpoint_name,
                role=roles.pop(),
                implementable=True,
                normalization_label=labels.pop(),
                decisions=decisions,
            )
    return endpoints


def load_stochastic_holdout_protocol(
    config_path: str | Path,
) -> StochasticHoldoutProtocol:
    config_path = Path(config_path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    evaluation = config["evaluation"]
    if evaluation["role"] != "fixed_policy_out_of_sample_mechanism_gate":
        raise ValueError("Unsupported stochastic holdout role")
    if evaluation["security_certified"] is not False:
        raise ValueError("Synthetic holdout cannot claim security certification")
    if evaluation["formal_vma_claimed"] is not False:
        raise ValueError("Synthetic holdout cannot claim formal VMA")
    if evaluation["planning_reoptimization_allowed"] is not False:
        raise ValueError("Holdout planning reoptimization must remain disabled")
    if evaluation["runtime_recourse_only"] is not True:
        raise ValueError("Holdout execution must allow runtime recourse only")
    if evaluation["random_seed"] is not None:
        raise ValueError("Deterministic holdout design must not claim random sampling")

    artifacts = config["training_artifacts"]
    if tuple(artifacts["policy_order"]) != _POLICIES:
        raise ValueError("Holdout must compare B3 and B4 in order")
    if tuple(artifacts["endpoint_order"]) != _ENDPOINTS:
        raise ValueError("Holdout must execute both X endpoints")
    if artifacts["required_training_endpoint_face"] != "minimum_total_contract_exposure":
        raise ValueError("Unsupported training contract-exposure face")
    tree_path = _resolve_path(artifacts["scenario_config"])
    tree = load_frozen_scenario_tree(tree_path)
    summary_path = _resolve_path(artifacts["summary_path"])
    endpoint_path = _resolve_path(artifacts["endpoint_path"])
    summary_hash = _validate_hash(
        summary_path, artifacts["summary_sha256"], "Training summary"
    )
    endpoint_hash = _validate_hash(
        endpoint_path, artifacts["endpoint_sha256"], "Training endpoint"
    )
    summary = _strict_json(summary_path)
    if not (
        summary.get("all_policies_feasible") is True
        and summary.get("information_ordering_passed") is True
        and summary.get("formal_endpoints_published") is True
    ):
        raise ValueError("Training M5b gate did not publish valid endpoints")
    if summary.get("security_certified") is not False:
        raise ValueError("Training M5b summary cannot claim certification")
    if summary.get("scenario_tree_id") != tree.id:
        raise ValueError("Training summary scenario tree does not match the config")
    if summary.get("security_state_count") != 107:
        raise ValueError("Holdout requires the complete 107-state training gate")
    policy_endpoints = _load_policy_endpoints(endpoint_path, tree)

    mapping = config["history_mapping"]
    q2_mapping = mapping["q2_demand_class"]
    q4_mapping = mapping["q4_terminal_outcome"]
    q2_thresholds = tuple(
        _finite_number(value, "q2 threshold")
        for value in q2_mapping["thresholds_mw"]
    )
    if len(q2_thresholds) != 2 or not q2_thresholds[0] < q2_thresholds[1]:
        raise ValueError("q2 mapping requires two increasing thresholds")
    q2_labels = tuple(q2_mapping["labels"])
    if q2_labels != ("delayed", "baseline", "accelerated"):
        raise ValueError("q2 mapping labels must match the training signals")
    if q2_mapping["boundary_rule"] != "upper_bucket_on_equal":
        raise ValueError("q2 boundary rule is not frozen")
    if q4_mapping["boundary_rule"] != "upper_bucket_on_equal":
        raise ValueError("q4 boundary rule is not frozen")
    q4_labels = (q4_mapping["lower_label"], q4_mapping["upper_label"])
    if q4_labels != ("lower", "upper"):
        raise ValueError("q4 mapping labels must match the training outcomes")
    project_mapping = {
        int(delay): str(name)
        for delay, name in mapping["q3_project_state"]["exact_mapping"].items()
    }
    if project_mapping != {0: "on_time", 1: "delayed_one_quarter"}:
        raise ValueError("Project-state mapping must match the training support")
    if mapping["q3_demand_is_not_an_additional_training_partition"] is not True:
        raise ValueError("q3 demand cannot create an untrained policy partition")
    if mapping["unseen_history_manual_override_allowed"] is not False:
        raise ValueError("Manual holdout-history overrides must remain disabled")

    design = config["holdout_design"]
    quarters = tuple(design["quarters"])
    if quarters != tree.quarters:
        raise ValueError("Holdout quarters must match the training tree")
    demand_paths = tuple(
        HoldoutDemandPath(
            name=str(row["name"]),
            probability=_finite_number(row["probability"], "Demand probability"),
            demand_mw=tuple(
                _finite_number(value, "Holdout demand") for value in row["demand_mw"]
            ),
        )
        for row in design["demand_paths"]
    )
    if len({path.name for path in demand_paths}) != len(demand_paths):
        raise ValueError("Holdout demand-path names must be unique")
    if abs(sum(path.probability for path in demand_paths) - 1.0) > 1.0e-9:
        raise ValueError("Holdout demand probabilities must sum to one")
    training_paths = {state.demand_mw for state in tree.demand_states}
    q1_required = _finite_number(
        mapping["q1_required_demand_mw"], "Required q1 demand"
    )
    for path in demand_paths:
        if path.probability <= 0.0 or len(path.demand_mw) != len(quarters):
            raise ValueError("Every holdout demand path must be positive and complete")
        if path.demand_mw[0] != q1_required:
            raise ValueError("Every holdout path must match the frozen q1 demand")
        if any(next_value < value for value, next_value in zip(path.demand_mw, path.demand_mw[1:])):
            raise ValueError("Holdout demand paths must be nondecreasing")
        if path.demand_mw in training_paths:
            raise ValueError("Holdout demand paths must be disjoint from training")

    project_states = tuple(
        HoldoutProjectState(
            name=str(row["name"]),
            probability=_finite_number(row["probability"], "Project probability"),
            extra_lead_time_quarters=int(row["extra_lead_time_quarters"]),
        )
        for row in design["project_states"]
    )
    if abs(sum(state.probability for state in project_states) - 1.0) > 1.0e-9:
        raise ValueError("Holdout project probabilities must sum to one")
    if {
        state.extra_lead_time_quarters: state.name for state in project_states
    } != project_mapping:
        raise ValueError("Holdout project states must match the frozen mapping")
    if design["full_factorial_cross"] is not True:
        raise ValueError("Holdout demand and project states must be fully crossed")
    leaves = tuple(
        HoldoutLeaf(
            name=f"{demand.name}__{project.name}",
            demand_path=demand.name,
            project_state=project.name,
            probability=demand.probability * project.probability,
        )
        for demand in demand_paths
        for project in project_states
    )
    if len(leaves) != int(design["expected_leaf_count"]):
        raise ValueError("Holdout leaf count does not match the freeze")
    if abs(sum(leaf.probability for leaf in leaves) - 1.0) > 1.0e-9:
        raise ValueError("Holdout leaf probabilities must sum to one")

    execution = config["execution"]
    if execution["fixed_policy_source"] != "frozen_training_endpoint_csv":
        raise ValueError("Holdout must execute the frozen endpoint CSV")
    if execution["evaluator"] != "m3_fixed_fx_actual_and_contract_counterfactual":
        raise ValueError("Unsupported holdout fixed-policy evaluator")
    if execution["service_validation"] != "actual_and_contract_counterfactual_all_107_security_states":
        raise ValueError("Holdout must retain both 107-state service layers")
    if execution["primary_objective_tolerance_source"] != "m3_m4_tested_default_numerical_acceptance":
        raise ValueError("Holdout numerical tolerance source is not frozen")
    primary_tolerance = _finite_number(
        execution["primary_objective_tolerance"],
        "Primary objective tolerance",
    )
    if primary_tolerance != 1.0e-5:
        raise ValueError("Holdout must retain the tested M3/M4 tolerance")
    power_balance_tolerance = _finite_number(
        execution["power_balance_tolerance_mw"],
        "Power-balance tolerance",
    )
    breach_tolerance = _finite_number(
        execution["contract_breach_tolerance_mw"],
        "Contract-breach tolerance",
    )
    if power_balance_tolerance != 1.0e-6 or breach_tolerance != 1.0e-7:
        raise ValueError("Holdout physical audit tolerances are not frozen")
    if execution["value_metric"] != "set_valued_synthetic_holdout_access_shortfall_difference":
        raise ValueError("Holdout value metric must remain set-valued")
    if execution["value_orientation"] != "b3_minus_b4_positive_means_multistage_improves":
        raise ValueError("Holdout value orientation is not frozen")
    if execution["economic_optimum_claimed"] is not False:
        raise ValueError("Holdout cannot claim an economic optimum")

    output = config["output"]
    return StochasticHoldoutProtocol(
        id=str(evaluation["id"]),
        parameter_status=str(evaluation["parameter_status"]),
        probability_basis=str(evaluation["probability_basis"]),
        selection_rule=str(evaluation["selection_rule"]),
        training_tree=tree,
        training_summary_path=summary_path,
        training_summary_sha256=summary_hash,
        training_endpoint_path=endpoint_path,
        training_endpoint_sha256=endpoint_hash,
        quarters=quarters,
        demand_paths=demand_paths,
        project_states=project_states,
        leaves=leaves,
        policy_endpoints=policy_endpoints,
        q1_required_demand_mw=q1_required,
        q2_thresholds_mw=q2_thresholds,
        q2_labels=q2_labels,
        q4_threshold_mw=_finite_number(q4_mapping["threshold_mw"], "q4 threshold"),
        q4_labels=q4_labels,
        project_state_mapping=project_mapping,
        primary_objective_tolerance=primary_tolerance,
        power_balance_tolerance_mw=power_balance_tolerance,
        contract_breach_tolerance_mw=breach_tolerance,
        path_output=_resolve_path(output["path_results"]),
        summary_output=_resolve_path(output["summary_path"]),
    )


def map_q2_demand_class(protocol: StochasticHoldoutProtocol, demand_mw: float) -> str:
    demand = _finite_number(demand_mw, "Observed q2 demand")
    lower, upper = protocol.q2_thresholds_mw
    if demand < lower:
        return protocol.q2_labels[0]
    if demand < upper:
        return protocol.q2_labels[1]
    return protocol.q2_labels[2]


def map_q4_terminal_outcome(
    protocol: StochasticHoldoutProtocol,
    demand_mw: float,
) -> str:
    demand = _finite_number(demand_mw, "Observed q4 demand")
    return (
        protocol.q4_labels[0]
        if demand < protocol.q4_threshold_mw
        else protocol.q4_labels[1]
    )


def map_observed_history_to_group(
    protocol: StochasticHoldoutProtocol,
    *,
    policy: str,
    quarter: str,
    q2_demand_mw: float | None = None,
    project_extra_lead_time_quarters: int | None = None,
    q4_demand_mw: float | None = None,
) -> str:
    if policy not in _POLICIES:
        raise ValueError("Only implementable B3/B4 policies can be mapped")
    try:
        position = protocol.quarters.index(quarter)
    except ValueError as error:
        raise ValueError(f"Unknown holdout quarter: {quarter}") from error
    if position < 1 and q2_demand_mw is not None:
        raise ValueError("q2 demand cannot be supplied before q2")
    if position < 2 and project_extra_lead_time_quarters is not None:
        raise ValueError("Project state cannot be supplied before q3")
    if position < 3 and q4_demand_mw is not None:
        raise ValueError("Terminal demand cannot be supplied before q4")
    if position >= 1 and q2_demand_mw is None:
        raise ValueError("Observed q2 demand is required from q2 onward")
    if position >= 2 and project_extra_lead_time_quarters is None:
        raise ValueError("Observed project state is required from q3 onward")
    if position >= 3 and q4_demand_mw is None:
        raise ValueError("Observed terminal demand is required at q4")

    demand_class = (
        None if q2_demand_mw is None else map_q2_demand_class(protocol, q2_demand_mw)
    )
    project_state = (
        None
        if project_extra_lead_time_quarters is None
        else protocol.project_state_mapping.get(project_extra_lead_time_quarters)
    )
    if project_extra_lead_time_quarters is not None and project_state is None:
        raise ValueError("Observed project state lies outside the frozen mapping")
    terminal = (
        None
        if q4_demand_mw is None
        else map_q4_terminal_outcome(protocol, q4_demand_mw)
    )
    demand_by_name = {
        state.name: state for state in protocol.training_tree.demand_states
    }
    candidates = set()
    for leaf in protocol.training_tree.leaves:
        demand_state = demand_by_name[leaf.demand_state]
        if demand_class is not None and demand_state.q2_signal != demand_class:
            continue
        if project_state is not None and leaf.project_state != project_state:
            continue
        if terminal is not None and demand_state.terminal_outcome != terminal:
            continue
        candidates.add(leaf.name)
    if not candidates:
        raise ValueError("Observed history does not map to any training leaf")
    matches = []
    for index, group in enumerate(
        protocol.training_tree.decision_groups(policy, quarter)
    ):
        if candidates <= set(group):
            matches.append(f"{quarter}_g{index}")
    if len(matches) != 1:
        raise ValueError("Observed history does not map to exactly one policy group")
    return matches[0]


def map_fixed_policy_path(
    protocol: StochasticHoldoutProtocol,
    *,
    policy: str,
    endpoint: str,
    holdout_leaf: str,
) -> MappedFixedPolicy:
    leaf = next((item for item in protocol.leaves if item.name == holdout_leaf), None)
    if leaf is None:
        raise ValueError(f"Unknown holdout leaf: {holdout_leaf}")
    demand_path = protocol.demand_path(leaf.demand_path)
    project_state = protocol.project_state(leaf.project_state)
    frozen_endpoint = protocol.policy_endpoint(policy, endpoint)
    demand_class = map_q2_demand_class(protocol, demand_path.demand_mw[1])
    terminal = map_q4_terminal_outcome(protocol, demand_path.demand_mw[3])
    groups = {}
    decisions = {}
    for position, quarter in enumerate(protocol.quarters):
        group = map_observed_history_to_group(
            protocol,
            policy=policy,
            quarter=quarter,
            q2_demand_mw=(demand_path.demand_mw[1] if position >= 1 else None),
            project_extra_lead_time_quarters=(
                project_state.extra_lead_time_quarters if position >= 2 else None
            ),
            q4_demand_mw=(demand_path.demand_mw[3] if position >= 3 else None),
        )
        groups[quarter] = group
        decisions[quarter] = frozen_endpoint.decisions[quarter, group]
    starts = {
        quarter: decisions[quarter].project_start for quarter in protocol.quarters
    }
    start_quarters = [quarter for quarter in protocol.quarters if starts[quarter]]
    if len(start_quarters) > 1:
        raise ValueError("Mapped fixed policy starts the project more than once")
    return MappedFixedPolicy(
        policy=policy,
        endpoint=endpoint,
        holdout_leaf=holdout_leaf,
        mapped_demand_class=demand_class,
        mapped_terminal_outcome=terminal,
        mapped_project_state=project_state.name,
        decision_group_by_quarter=groups,
        firm_capacity_mw={
            quarter: decisions[quarter].firm_capacity_mw
            for quarter in protocol.quarters
        },
        conditional_capacity_mw={
            quarter: decisions[quarter].conditional_capacity_mw
            for quarter in protocol.quarters
        },
        total_capacity_mw={
            quarter: decisions[quarter].total_capacity_mw
            for quarter in protocol.quarters
        },
        project_start_by_quarter=starts,
        project_start_quarter=start_quarters[0] if start_quarters else None,
        parameter_status=(
            "frozen_m5b_policy_endpoint_mapped_by_observed_holdout_history_"
            "without_planning_reoptimization"
        ),
    )


__all__ = [
    "FrozenPolicyDecision",
    "FrozenPolicyEndpoint",
    "HoldoutDemandPath",
    "HoldoutLeaf",
    "HoldoutProjectState",
    "MappedFixedPolicy",
    "StochasticHoldoutProtocol",
    "load_stochastic_holdout_protocol",
    "map_fixed_policy_path",
    "map_observed_history_to_group",
    "map_q2_demand_class",
    "map_q4_terminal_outcome",
]
