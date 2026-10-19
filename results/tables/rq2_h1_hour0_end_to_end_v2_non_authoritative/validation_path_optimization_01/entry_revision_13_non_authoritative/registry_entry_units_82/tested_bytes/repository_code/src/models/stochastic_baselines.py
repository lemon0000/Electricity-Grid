"""B3--B5 stochastic access baselines on a frozen information tree."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from math import isfinite, radians
from typing import Iterable, Mapping

from pyomo.environ import (
    Binary,
    ConcreteModel,
    Constraint,
    ConstraintList,
    NonNegativeReals,
    Objective,
    Set,
    SolverFactory,
    Var,
    maximize,
    minimize,
    value,
)
from pyomo.contrib.appsi.solvers.highs import Highs

from ..grid.rts24 import Rts24Data
from ..grid.scopf import (
    SecurityState,
    build_security_states,
    non_islanding_branch_indices,
)
from ..scenarios import (
    FrozenScenarioTree,
    PlanningPolicy,
    QuarterDecisionGroups,
    ScenarioNode,
)
from .deterministic_baselines import (
    BaselineSolveDiagnostic,
    _INTEGRALITY_TOLERANCE,
    _LEXICOGRAPHIC_BAND_AUDIT_TOLERANCE,
    _MODEL_FEASIBILITY_TOLERANCE,
    _clean_nonnegative,
    _maximum_integrality_violation,
    _maximum_model_violation,
    _mwh_tolerance,
    _solve_loaded,
    _solver_options,
)
from .deterministic_expansion import (
    ExistingBranchUpgrade,
    FixedPoi,
    _rating_increases,
    _validate_nonnegative_finite,
)
from .deterministic_fx import FxQuarter, FxServiceEnvelope, _RESPONSE_MODEL


_PLANNING_VARIABLE_SCOPE = "policy_decision_groups_F_X_z_start_only"
_MINIMUM_X_NORMALIZATION = (
    "minimum_expected_contract_then_minimum_x_non_economic_normalization"
)
_MAXIMUM_X_NORMALIZATION = (
    "minimum_expected_contract_then_maximum_x_non_economic_normalization"
)
_LEXICOGRAPHIC_COMPONENTS = frozenset(
    {
        "primary_access_shortfall_fix",
        "minimum_contract_exposure_fix",
        "endpoint_x_fix",
        "endpoint_project_count_fix",
    }
)
_LAYERS = ("actual", "contract")


class _StochasticSolveSession:
    def __init__(self, model: ConcreteModel, solver_name: str, tee: bool) -> None:
        self.model = model
        self.solver_name = solver_name
        self.tee = tee
        self.solver = None
        if solver_name.lower() in {"highs", "appsi_highs"}:
            solver = Highs()
            solver.config.load_solution = False
            solver.config.stream_solver = tee
            solver.highs_options.update(_solver_options(solver_name))
            self.solver = solver

    def solve(self, *, stage: str) -> tuple[object | None, BaselineSolveDiagnostic]:
        if self.solver is None:
            return _solve_loaded(
                self.model,
                self.solver_name,
                self.tee,
                stage=stage,
            )
        try:
            results = self.solver.solve(self.model)
        except Exception as error:
            return None, BaselineSolveDiagnostic(
                stage=stage,
                accepted=False,
                failure_reason="solver_exception",
                termination_condition="solver_exception",
                solver_status="error",
                solver_message=str(error),
                lower_bound=None,
                upper_bound=None,
                absolute_gap=None,
                gap_tolerance=None,
                maximum_constraint_violation=None,
                maximum_integrality_violation=None,
            )

        termination = results.termination_condition
        termination_name = getattr(termination, "name", str(termination))
        lower_bound = results.best_objective_bound
        upper_bound = results.best_feasible_objective
        lower_bound = (
            float(lower_bound)
            if lower_bound is not None and isfinite(float(lower_bound))
            else None
        )
        upper_bound = (
            float(upper_bound)
            if upper_bound is not None and isfinite(float(upper_bound))
            else None
        )
        absolute_gap = (
            abs(upper_bound - lower_bound)
            if lower_bound is not None and upper_bound is not None
            else None
        )
        gap_tolerance = (
            _mwh_tolerance(max(abs(lower_bound), abs(upper_bound)))
            if lower_bound is not None and upper_bound is not None
            else None
        )
        if termination_name not in {"optimal", "globallyOptimal"}:
            failure_reason = "termination_not_globally_accepted"
        elif absolute_gap is None or gap_tolerance is None:
            failure_reason = "missing_finite_objective_bound"
        elif absolute_gap > gap_tolerance:
            failure_reason = "objective_bound_gap_exceeds_tolerance"
        else:
            failure_reason = None

        maximum_constraint_violation = None
        maximum_integrality_violation = None
        if failure_reason is None:
            try:
                results.solution_loader.load_vars()
            except Exception as error:
                failure_reason = "solution_load_exception"
                solver_message = str(error)
            else:
                solver_message = "Persistent HiGHS solve completed"
                maximum_constraint_violation = _maximum_model_violation(self.model)
                maximum_integrality_violation = _maximum_integrality_violation(
                    self.model
                )
                if maximum_constraint_violation > _MODEL_FEASIBILITY_TOLERANCE:
                    failure_reason = "model_constraint_violation"
                elif maximum_integrality_violation > _INTEGRALITY_TOLERANCE:
                    failure_reason = "integrality_violation"
        else:
            solver_message = "Persistent HiGHS solve was not accepted"

        diagnostic = BaselineSolveDiagnostic(
            stage=stage,
            accepted=failure_reason is None,
            failure_reason=failure_reason,
            termination_condition=termination_name,
            solver_status="ok" if failure_reason is None else "warning",
            solver_message=solver_message,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            absolute_gap=absolute_gap,
            gap_tolerance=gap_tolerance,
            maximum_constraint_violation=maximum_constraint_violation,
            maximum_integrality_violation=maximum_integrality_violation,
        )
        return results, diagnostic


class StochasticBaselinePolicy(str, Enum):
    B3 = "B3"
    B4 = "B4"
    B5 = "B5"


@dataclass(frozen=True)
class StochasticBaselineEndpoint:
    access_shortfall_mwh: float
    contract_capacity_exposure_mwh: float
    conditional_capacity_exposure_mwh: float
    firm_capacity_mw: dict[str, dict[str, float]]
    conditional_capacity_mw: dict[str, dict[str, float]]
    total_capacity_mw: dict[str, dict[str, float]]
    connected_demand_mw: dict[str, dict[str, float]]
    firm_demand_mw: dict[str, dict[str, float]]
    active_conditional_demand_mw: dict[str, dict[str, float]]
    access_shortfall_mw: dict[str, dict[str, float]]
    project_start_by_quarter: dict[str, dict[str, bool]]
    project_start_quarter: dict[str, str | None]
    project_available_by_quarter: dict[str, dict[str, bool]]
    decision_group_by_quarter: dict[str, dict[str, str]]
    primary_target_mwh: float
    primary_tolerance_mwh: float
    primary_deviation_mwh: float
    primary_band_violation_mwh: float
    contract_exposure_target_mwh: float
    contract_exposure_tolerance_mwh: float
    contract_exposure_deviation_mwh: float
    contract_exposure_band_violation_mwh: float
    x_exposure_target_mwh: float
    x_exposure_tolerance_mwh: float
    x_exposure_deviation_mwh: float
    x_exposure_band_violation_mwh: float
    expected_project_count: float
    expected_commissioning_exposure_hours: float
    maximum_actual_call_mw: float
    maximum_contract_call_mw: float
    maximum_original_constraint_violation: float
    maximum_integrality_violation: float
    normalization_label: str
    planning_variable_scope: str


@dataclass(frozen=True)
class StochasticBaselineResult:
    policy: StochasticBaselinePolicy
    role: str
    implementable: bool
    feasible: bool
    termination_condition: str
    solver_status: str
    solver_message: str
    primary_access_shortfall_mwh: float | None
    primary_tolerance_mwh: float | None
    minimum_contract_exposure_mwh: float | None
    maximum_contract_exposure_mwh: float | None
    contract_exposure_tolerance_mwh: float | None
    minimum_x_exposure_mwh: float | None
    maximum_x_exposure_mwh: float | None
    x_exposure_tolerance_mwh: float | None
    minimum_x_endpoint: StochasticBaselineEndpoint | None
    maximum_x_endpoint: StochasticBaselineEndpoint | None
    displayed_endpoint: StochasticBaselineEndpoint | None
    displayed_endpoint_name: str | None
    normalization_label: str | None
    failure_stage: str | None
    stage_diagnostics: tuple[BaselineSolveDiagnostic, ...]
    planning_variable_scope: str
    natural_node_counts: dict[str, int]
    decision_group_counts: dict[str, int]
    states: tuple[SecurityState, ...]
    excluded_branch_indices: tuple[int, ...]
    embedded_state_rows: int


def _policy_data(
    tree: FrozenScenarioTree,
    policy: StochasticBaselinePolicy,
) -> PlanningPolicy:
    try:
        return next(item for item in tree.policies if item.name == policy.value)
    except StopIteration as error:
        raise ValueError(f"Tree does not define policy {policy.value}") from error


def _decision_structure(
    tree: FrozenScenarioTree,
    policy: StochasticBaselinePolicy,
    quarter_names: tuple[str, ...],
) -> tuple[
    tuple[tuple[str, str], ...],
    dict[tuple[str, str], str],
    dict[str, int],
]:
    decision_keys = []
    leaf_to_group = {}
    group_counts = {}
    leaf_names = set(tree.leaf_names)
    for quarter in quarter_names:
        groups = tree.decision_groups(policy.value, quarter)
        group_counts[quarter] = len(groups)
        seen = set()
        for position, group in enumerate(groups):
            group_name = f"{quarter}_g{position}"
            decision_keys.append((quarter, group_name))
            for leaf in group:
                if leaf not in leaf_names:
                    raise ValueError("Decision group references an unknown leaf")
                if leaf in seen:
                    raise ValueError("Decision groups must partition leaves")
                seen.add(leaf)
                leaf_to_group[leaf, quarter] = group_name
        if seen != leaf_names:
            raise ValueError("Decision groups must contain every leaf")
    return tuple(decision_keys), leaf_to_group, group_counts


def _operational_structure(
    tree: FrozenScenarioTree,
    policy: StochasticBaselinePolicy,
    quarter_names: tuple[str, ...],
) -> tuple[
    tuple[tuple[str, str], ...],
    dict[tuple[str, str], str],
    dict[tuple[str, str], str],
]:
    operation_keys = []
    leaf_to_operation = {}
    representative_leaf = {}
    if policy is StochasticBaselinePolicy.B5:
        for quarter in quarter_names:
            for leaf in tree.leaf_names:
                operation = leaf
                operation_keys.append((quarter, operation))
                leaf_to_operation[leaf, quarter] = operation
                representative_leaf[quarter, operation] = leaf
        return (
            tuple(operation_keys),
            leaf_to_operation,
            representative_leaf,
        )

    leaf_names = set(tree.leaf_names)
    for quarter in quarter_names:
        seen = set()
        for node in tree.nodes_for_quarter(quarter):
            if not node.leaves:
                raise ValueError("Natural operation nodes cannot be empty")
            operation_keys.append((quarter, node.name))
            representative_leaf[quarter, node.name] = node.leaves[0]
            for leaf in node.leaves:
                if leaf not in leaf_names:
                    raise ValueError("Natural operation node references an unknown leaf")
                if leaf in seen:
                    raise ValueError("Natural operation nodes must partition leaves")
                seen.add(leaf)
                leaf_to_operation[leaf, quarter] = node.name
        if seen != leaf_names:
            raise ValueError("Natural operation nodes must contain every leaf")
    return tuple(operation_keys), leaf_to_operation, representative_leaf


def _interval_diagnostic(
    *,
    stage: str,
    lower: float,
    upper: float,
    tolerance: float,
    label: str,
) -> BaselineSolveDiagnostic:
    if lower < -_LEXICOGRAPHIC_BAND_AUDIT_TOLERANCE:
        failure = f"minimum_{label}_is_negative"
    elif upper < -_LEXICOGRAPHIC_BAND_AUDIT_TOLERANCE:
        failure = f"maximum_{label}_is_negative"
    elif lower > upper + _LEXICOGRAPHIC_BAND_AUDIT_TOLERANCE:
        failure = f"minimum_{label}_exceeds_maximum"
    else:
        failure = None
    return BaselineSolveDiagnostic(
        stage=stage,
        accepted=failure is None,
        failure_reason=failure,
        termination_condition="not_applicable",
        solver_status="ok" if failure is None else "warning",
        solver_message=(
            f"Minimum and maximum {label} endpoints are consistently ordered"
            if failure is None
            else f"Invalid {label} exposure interval"
        ),
        lower_bound=lower,
        upper_bound=upper,
        absolute_gap=abs(upper - lower),
        gap_tolerance=tolerance,
        maximum_constraint_violation=None,
        maximum_integrality_violation=None,
    )


def _solve_stochastic_baseline_monolithic(
    data: Rts24Data,
    *,
    policy: StochasticBaselinePolicy,
    tree: FrozenScenarioTree,
    quarters: Iterable[FxQuarter],
    poi: FixedPoi,
    project: ExistingBranchUpgrade,
    service_envelope: FxServiceEnvelope,
    redispatch_up_mw: Mapping[int, float],
    redispatch_down_mw: Mapping[int, float],
    branch_indices: Iterable[int] | None = None,
    generator_indices: Iterable[int] | None = None,
    immediate_rating: str = "rate_c",
    sustained_rating: str = "rate_a",
    solver_name: str = "highs",
    tee: bool = False,
) -> StochasticBaselineResult:
    """Solve one physical B3/B4/B5 policy with embedded M3 service layers."""

    if not isinstance(policy, StochasticBaselinePolicy):
        policy = StochasticBaselinePolicy(policy)
    planning_policy = _policy_data(tree, policy)
    if planning_policy.decision_variables != ("F", "X", "z_start"):
        raise ValueError("M5 planning groups may contain only F, X, and z_start")

    quarters = tuple(quarters)
    if not quarters:
        raise ValueError("At least one stochastic planning quarter is required")
    quarter_names = tuple(quarter.name for quarter in quarters)
    if quarter_names != tree.quarters:
        raise ValueError("Planning quarters must match the frozen scenario tree")
    if len(set(quarter_names)) != len(quarter_names):
        raise ValueError("Planning quarter names must be unique")
    quarter_by_name = {quarter.name: quarter for quarter in quarters}
    for quarter in quarters:
        _validate_nonnegative_finite(
            "System load multiplier", quarter.system_load_multiplier
        )
        if not isfinite(quarter.operating_hours) or quarter.operating_hours <= 0.0:
            raise ValueError("Quarter operating hours must be finite and positive")
        _validate_nonnegative_finite(
            "Continuous validation hours", quarter.continuous_validation_hours
        )
        if quarter.continuous_validation_hours > quarter.operating_hours + 1.0e-9:
            raise ValueError(
                "Continuous validation hours cannot exceed operating hours"
            )

    leaf_names = tree.leaf_names
    if not leaf_names or len(set(leaf_names)) != len(leaf_names):
        raise ValueError("Scenario leaves must be nonempty and unique")
    demand_by_name = {state.name: state for state in tree.demand_states}
    project_state_by_name = {state.name: state for state in tree.project_states}
    if abs(sum(leaf.probability for leaf in tree.leaves) - 1.0) > 1.0e-9:
        raise ValueError("Scenario leaf probabilities must sum to one")
    leaf_probability = {}
    demand_path = {}
    extra_delay = {}
    for leaf in tree.leaves:
        if not isfinite(leaf.probability) or leaf.probability <= 0.0:
            raise ValueError("Scenario leaf probabilities must be finite and positive")
        if leaf.demand_state not in demand_by_name:
            raise ValueError("Scenario leaf references unknown demand state")
        if leaf.project_state not in project_state_by_name:
            raise ValueError("Scenario leaf references unknown project state")
        path = demand_by_name[leaf.demand_state].demand_mw
        if len(path) != len(quarters):
            raise ValueError("Every demand path must contain every quarter")
        if any(
            not isfinite(number)
            or number < 0.0
            for number in path
        ):
            raise ValueError("Demand paths must be finite and nonnegative")
        if any(next_value < value for value, next_value in zip(path, path[1:])):
            raise ValueError("Demand paths must be nondecreasing")
        leaf_probability[leaf.name] = float(leaf.probability)
        demand_path[leaf.name] = dict(zip(quarter_names, path))
        extra_delay[leaf.name] = project_state_by_name[
            leaf.project_state
        ].extra_lead_time_quarters

    bus_indices = tuple(bus.index for bus in data.buses)
    if poi.bus not in bus_indices:
        raise ValueError(f"Unknown POI bus {poi.bus}")
    _validate_nonnegative_finite("Initial POI capacity", poi.initial_capacity_mw)
    _validate_nonnegative_finite(
        "Application capacity", poi.application_capacity_mw
    )
    if poi.initial_capacity_mw > poi.application_capacity_mw + 1.0e-9:
        raise ValueError("Initial POI capacity cannot exceed application capacity")
    if project.lead_time_quarters != tree.project_timing.base_lead_time_quarters:
        raise ValueError("Project lead time must match frozen tree timing")
    if not project.name or not project.parameter_status:
        raise ValueError("Project name and parameter status must be explicit")
    _validate_nonnegative_finite(
        "POI capacity increase", project.poi_capacity_increase_mw
    )
    if not service_envelope.parameter_status:
        raise ValueError("F/X service parameter status must be explicit")
    if service_envelope.response_model != _RESPONSE_MODEL:
        raise ValueError("Unsupported F/X response model")
    _validate_nonnegative_finite(
        "Maximum conditional capacity",
        service_envelope.max_conditional_capacity_mw,
    )

    branch_by_index = {branch.index: branch for branch in data.branches}
    generator_by_index = {generator.index: generator for generator in data.generators}
    for rating in (immediate_rating, sustained_rating):
        _rating_increases(project, rating)
        for branch in data.branches:
            branch.rating_mw(rating)
    upgrade_branch_indices = set(project.rate_a_increase_mw) | set(
        project.rate_c_increase_mw
    )
    if upgrade_branch_indices - branch_by_index.keys():
        raise ValueError("Project contains unknown branch indices")

    selected_branches = (
        non_islanding_branch_indices(data)
        if branch_indices is None
        else tuple(int(index) for index in branch_indices)
    )
    selected_generators = (
        tuple(
            generator.index
            for generator in data.generators
            if generator.in_service and generator.p_max_mw > 0.0
        )
        if generator_indices is None
        else tuple(int(index) for index in generator_indices)
    )
    if len(set(selected_branches)) != len(selected_branches):
        raise ValueError("Security branch indices must be unique")
    if len(set(selected_generators)) != len(selected_generators):
        raise ValueError("Security generator indices must be unique")
    if set(selected_branches) - branch_by_index.keys():
        raise ValueError("Security branch set contains an unknown index")
    if set(selected_generators) - generator_by_index.keys():
        raise ValueError("Security generator set contains an unknown index")
    islanding = set(selected_branches) - set(non_islanding_branch_indices(data))
    if islanding:
        raise ValueError("Security set cannot contain islanding branches")
    generator_indices_all = tuple(generator_by_index)
    for name, limits in (
        ("Up redispatch", redispatch_up_mw),
        ("Down redispatch", redispatch_down_mw),
    ):
        if set(limits) != set(generator_indices_all):
            raise ValueError(f"{name} must contain every generator index")
        for limit in limits.values():
            _validate_nonnegative_finite(name, limit)

    states = build_security_states(
        selected_branches,
        selected_generators,
        immediate_rating,
        sustained_rating,
    )
    state_names = tuple(state.name for state in states)
    state_by_name = {state.name: state for state in states}
    if "base" not in state_by_name:
        raise ValueError("Security states must contain the base state")
    excluded_branches = tuple(
        branch.index
        for branch in data.branches
        if branch.in_service and branch.index not in selected_branches
    )
    natural_node_counts = {
        quarter: len(tree.nodes_for_quarter(quarter)) for quarter in quarter_names
    }
    decision_keys, leaf_to_group, decision_group_counts = _decision_structure(
        tree,
        policy,
        quarter_names,
    )
    (
        operation_keys,
        leaf_to_operation,
        representative_leaf,
    ) = _operational_structure(tree, policy, quarter_names)
    stage_diagnostics: list[BaselineSolveDiagnostic] = []

    def failed_result(
        termination_condition: object,
        solver_status: object,
        solver_message: object,
        *,
        failure_stage: str,
        primary: float | None = None,
        primary_tolerance: float | None = None,
        minimum_contract: float | None = None,
        maximum_contract: float | None = None,
        contract_tolerance: float | None = None,
        minimum_x: float | None = None,
        maximum_x: float | None = None,
        x_tolerance: float | None = None,
        minimum_endpoint: StochasticBaselineEndpoint | None = None,
        maximum_endpoint: StochasticBaselineEndpoint | None = None,
    ) -> StochasticBaselineResult:
        return StochasticBaselineResult(
            policy=policy,
            role=planning_policy.role,
            implementable=planning_policy.implementable,
            feasible=False,
            termination_condition=str(termination_condition),
            solver_status=str(solver_status),
            solver_message=str(solver_message),
            primary_access_shortfall_mwh=primary,
            primary_tolerance_mwh=primary_tolerance,
            minimum_contract_exposure_mwh=minimum_contract,
            maximum_contract_exposure_mwh=maximum_contract,
            contract_exposure_tolerance_mwh=contract_tolerance,
            minimum_x_exposure_mwh=minimum_x,
            maximum_x_exposure_mwh=maximum_x,
            x_exposure_tolerance_mwh=x_tolerance,
            minimum_x_endpoint=minimum_endpoint,
            maximum_x_endpoint=maximum_endpoint,
            displayed_endpoint=None,
            displayed_endpoint_name=None,
            normalization_label=None,
            failure_stage=failure_stage,
            stage_diagnostics=tuple(stage_diagnostics),
            planning_variable_scope=_PLANNING_VARIABLE_SCOPE,
            natural_node_counts=natural_node_counts,
            decision_group_counts=decision_group_counts,
            states=states,
            excluded_branch_indices=excluded_branches,
            embedded_state_rows=len(operation_keys) * len(_LAYERS) * len(states),
        )

    bus_by_index = {bus.index: bus for bus in data.buses}
    generators_at_bus = {bus: [] for bus in bus_indices}
    outgoing_at_bus = {bus: [] for bus in bus_indices}
    incoming_at_bus = {bus: [] for bus in bus_indices}
    for generator in data.generators:
        generators_at_bus[generator.bus].append(generator.index)
    for branch in data.branches:
        outgoing_at_bus[branch.from_bus].append(branch.index)
        incoming_at_bus[branch.to_bus].append(branch.index)

    model = ConcreteModel()
    model.LEAF = Set(initialize=leaf_names, ordered=True)
    model.QUARTER = Set(initialize=quarter_names, ordered=True)
    model.DECISION = Set(dimen=2, initialize=decision_keys, ordered=True)
    model.OPERATION = Set(dimen=2, initialize=operation_keys, ordered=True)
    model.LAYER = Set(initialize=_LAYERS, ordered=True)
    model.STATE = Set(initialize=state_names, ordered=True)
    model.BUS = Set(initialize=bus_indices, ordered=True)
    model.GEN = Set(initialize=generator_indices_all, ordered=True)
    model.BRANCH = Set(initialize=tuple(branch_by_index), ordered=True)

    model.firm_capacity = Var(model.DECISION, domain=NonNegativeReals)
    model.conditional_capacity = Var(model.DECISION, domain=NonNegativeReals)
    model.total_capacity = Var(model.DECISION, domain=NonNegativeReals)
    model.project_start = Var(model.DECISION, domain=Binary)
    model.project_available = Var(model.LEAF, model.QUARTER, domain=Binary)
    model.connected_demand = Var(model.LEAF, model.QUARTER, domain=NonNegativeReals)
    model.firm_demand = Var(model.LEAF, model.QUARTER, domain=NonNegativeReals)
    model.access_shortfall = Var(model.LEAF, model.QUARTER, domain=NonNegativeReals)
    model.connected_selector = Var(model.LEAF, model.QUARTER, domain=Binary)
    model.firm_selector = Var(model.LEAF, model.QUARTER, domain=Binary)

    model.project_logic = ConstraintList()
    for leaf in leaf_names:
        model.project_logic.add(
            sum(
                model.project_start[quarter, leaf_to_group[leaf, quarter]]
                for quarter in quarter_names
            )
            <= 1
        )
        for position, quarter in enumerate(quarter_names):
            lead_time = project.lead_time_quarters + extra_delay[leaf]
            eligible = quarter_names[: max(0, position - lead_time + 1)]
            model.project_logic.add(
                model.project_available[leaf, quarter]
                == sum(
                    model.project_start[start, leaf_to_group[leaf, start]]
                    for start in eligible
                )
            )

    model.contract = ConstraintList()
    big_m = max(
        poi.application_capacity_mw,
        max(demand_path[leaf][quarter] for leaf in leaf_names for quarter in quarter_names),
    )
    for quarter, group in decision_keys:
        model.contract.add(
            model.total_capacity[quarter, group]
            == model.firm_capacity[quarter, group]
            + model.conditional_capacity[quarter, group]
        )
        model.contract.add(
            model.conditional_capacity[quarter, group]
            <= service_envelope.max_conditional_capacity_mw
        )
        model.contract.add(
            model.total_capacity[quarter, group] <= poi.application_capacity_mw
        )
    for leaf in leaf_names:
        for position, quarter in enumerate(quarter_names):
            group = leaf_to_group[leaf, quarter]
            total = model.total_capacity[quarter, group]
            firm = model.firm_capacity[quarter, group]
            demand = demand_path[leaf][quarter]
            connected = model.connected_demand[leaf, quarter]
            firm_demand = model.firm_demand[leaf, quarter]
            connected_selector = model.connected_selector[leaf, quarter]
            firm_selector = model.firm_selector[leaf, quarter]
            model.contract.add(
                total
                <= poi.initial_capacity_mw
                + project.poi_capacity_increase_mw
                * model.project_available[leaf, quarter]
            )
            model.contract.add(connected <= demand)
            model.contract.add(connected <= total)
            model.contract.add(
                connected >= demand - big_m * (1 - connected_selector)
            )
            model.contract.add(connected >= total - big_m * connected_selector)
            model.contract.add(
                demand - total <= big_m * (1 - connected_selector)
            )
            model.contract.add(
                total - demand <= big_m * connected_selector
            )
            model.contract.add(firm_demand <= demand)
            model.contract.add(firm_demand <= firm)
            model.contract.add(
                firm_demand >= demand - big_m * (1 - firm_selector)
            )
            model.contract.add(firm_demand >= firm - big_m * firm_selector)
            model.contract.add(demand - firm <= big_m * (1 - firm_selector))
            model.contract.add(firm - demand <= big_m * firm_selector)
            model.contract.add(
                model.access_shortfall[leaf, quarter] == demand - connected
            )
            if position:
                previous = quarter_names[position - 1]
                previous_group = leaf_to_group[leaf, previous]
                model.contract.add(
                    firm >= model.firm_capacity[previous, previous_group]
                )
                model.contract.add(
                    total >= model.total_capacity[previous, previous_group]
                )

    model.grid_call = Var(
        model.OPERATION,
        model.LAYER,
        model.STATE,
        domain=NonNegativeReals,
    )
    model.poi_load = Var(
        model.OPERATION,
        model.LAYER,
        model.STATE,
        domain=NonNegativeReals,
    )
    model.service = ConstraintList()
    for quarter, operation in operation_keys:
        leaf = representative_leaf[quarter, operation]
        group = leaf_to_group[leaf, quarter]
        total = model.total_capacity[quarter, group]
        firm = model.firm_capacity[quarter, group]
        active_x = (
            model.connected_demand[leaf, quarter]
            - model.firm_demand[leaf, quarter]
        )
        for layer in _LAYERS:
            for state in states:
                call = model.grid_call[quarter, operation, layer, state.name]
                load = model.poi_load[quarter, operation, layer, state.name]
                if state.response_mode in {"base", "fixed"}:
                    call.fix(0.0)
                elif layer == "actual":
                    model.service.add(call <= active_x)
                else:
                    model.service.add(
                        call <= model.conditional_capacity[quarter, group]
                    )
                if layer == "actual":
                    model.service.add(
                        load == model.connected_demand[leaf, quarter] - call
                    )
                    model.service.add(load >= model.firm_demand[leaf, quarter])
                else:
                    model.service.add(load == total - call)
                    model.service.add(load >= firm)

    def generation_bounds(
        _model: ConcreteModel,
        _quarter: str,
        _operation: str,
        _layer: str,
        state_name: str,
        generator_index: int,
    ) -> tuple[float, float]:
        generator = generator_by_index[generator_index]
        state = state_by_name[state_name]
        if (
            not generator.in_service
            or generator_index in state.outaged_generator_indices
        ):
            return 0.0, 0.0
        return generator.p_min_mw, generator.p_max_mw

    model.generation = Var(
        model.OPERATION,
        model.LAYER,
        model.STATE,
        model.GEN,
        bounds=generation_bounds,
    )
    model.angle = Var(
        model.OPERATION,
        model.LAYER,
        model.STATE,
        model.BUS,
    )
    model.flow = Var(
        model.OPERATION,
        model.LAYER,
        model.STATE,
        model.BRANCH,
    )

    def branch_flow_rule(
        _model: ConcreteModel,
        quarter: str,
        operation: str,
        layer: str,
        state_name: str,
        branch_index: int,
    ) -> object:
        state = state_by_name[state_name]
        branch = branch_by_index[branch_index]
        flow = _model.flow[quarter, operation, layer, state_name, branch_index]
        if (
            not branch.in_service
            or branch_index in state.outaged_branch_indices
        ):
            return flow == 0.0
        susceptance = data.base_mva / (branch.reactance_pu * branch.tap_ratio)
        return flow == susceptance * (
            radians(1.0)
            * (
                _model.angle[
                    quarter, operation, layer, state_name, branch.from_bus
                ]
                - _model.angle[
                    quarter, operation, layer, state_name, branch.to_bus
                ]
            )
            - branch.phase_shift_rad
        )

    model.branch_flow = Constraint(
        model.OPERATION,
        model.LAYER,
        model.STATE,
        model.BRANCH,
        rule=branch_flow_rule,
    )
    model.thermal_limits = ConstraintList()
    for quarter, operation in operation_keys:
        leaf = representative_leaf[quarter, operation]
        for layer in _LAYERS:
            for state in states:
                increases = _rating_increases(project, state.branch_rating)
                for branch in data.branches:
                    rating = branch.rating_mw(state.branch_rating) + (
                        increases.get(branch.index, 0.0)
                        * model.project_available[leaf, quarter]
                    )
                    flow = model.flow[
                        quarter, operation, layer, state.name, branch.index
                    ]
                    model.thermal_limits.add(flow <= rating)
                    model.thermal_limits.add(-flow <= rating)

    def balance_rule(
        _model: ConcreteModel,
        quarter: str,
        operation: str,
        layer: str,
        state_name: str,
        bus: int,
    ) -> object:
        generation = sum(
            _model.generation[quarter, operation, layer, state_name, index]
            for index in generators_at_bus[bus]
        )
        outgoing = sum(
            _model.flow[quarter, operation, layer, state_name, index]
            for index in outgoing_at_bus[bus]
        )
        incoming = sum(
            _model.flow[quarter, operation, layer, state_name, index]
            for index in incoming_at_bus[bus]
        )
        demand = (
            bus_by_index[bus].demand_mw
            * quarter_by_name[quarter].system_load_multiplier
        )
        if bus == poi.bus:
            demand += _model.poi_load[quarter, operation, layer, state_name]
        return generation - demand == outgoing - incoming

    model.power_balance = Constraint(
        model.OPERATION,
        model.LAYER,
        model.STATE,
        model.BUS,
        rule=balance_rule,
    )
    for quarter, operation in operation_keys:
        for layer in _LAYERS:
            for state in states:
                model.angle[
                    quarter,
                    operation,
                    layer,
                    state.name,
                    data.reference_bus,
                ].fix(0.0)

    model.response = ConstraintList()
    for quarter, operation in operation_keys:
        for layer in _LAYERS:
            for state in states:
                if state.response_mode == "base":
                    continue
                for generator in data.generators:
                    if generator.index in state.outaged_generator_indices:
                        continue
                    contingency = model.generation[
                        quarter, operation, layer, state.name, generator.index
                    ]
                    base = model.generation[
                        quarter, operation, layer, "base", generator.index
                    ]
                    if state.response_mode == "fixed":
                        model.response.add(contingency == base)
                    else:
                        model.response.add(
                            contingency - base
                            <= redispatch_up_mw[generator.index]
                        )
                        model.response.add(
                            base - contingency
                            <= redispatch_down_mw[generator.index]
                        )

    if not SolverFactory(solver_name).available(exception_flag=False):
        raise RuntimeError(f"Solver '{solver_name}' is not available")
    solve_session = _StochasticSolveSession(model, solver_name, tee)
    access_shortfall_expression = sum(
        leaf_probability[leaf]
        * quarter_by_name[quarter].operating_hours
        * model.access_shortfall[leaf, quarter]
        for leaf in leaf_names
        for quarter in quarter_names
    )
    contract_exposure_expression = sum(
        leaf_probability[leaf]
        * quarter_by_name[quarter].operating_hours
        * model.total_capacity[quarter, leaf_to_group[leaf, quarter]]
        for leaf in leaf_names
        for quarter in quarter_names
    )
    x_exposure_expression = sum(
        leaf_probability[leaf]
        * quarter_by_name[quarter].operating_hours
        * model.conditional_capacity[quarter, leaf_to_group[leaf, quarter]]
        for leaf in leaf_names
        for quarter in quarter_names
    )
    expected_project_count_expression = sum(
        leaf_probability[leaf]
        * model.project_start[quarter, leaf_to_group[leaf, quarter]]
        for leaf in leaf_names
        for quarter in quarter_names
    )
    commissioning_exposure_expression = sum(
        leaf_probability[leaf]
        * quarter_by_name[quarter].operating_hours
        * model.project_available[leaf, quarter]
        for leaf in leaf_names
        for quarter in quarter_names
    )

    def extract_endpoint(
        *,
        primary_target: float,
        primary_tolerance: float,
        contract_target: float,
        contract_tolerance: float,
        x_target: float,
        x_tolerance: float,
        normalization_label: str,
    ) -> StochasticBaselineEndpoint:
        firm_capacity = {}
        conditional_capacity = {}
        total_capacity = {}
        connected_demand = {}
        firm_demand = {}
        active_conditional = {}
        access_shortfall = {}
        starts = {}
        start_quarter = {}
        available = {}
        groups = {}
        for leaf in leaf_names:
            firm_capacity[leaf] = {}
            conditional_capacity[leaf] = {}
            total_capacity[leaf] = {}
            connected_demand[leaf] = {}
            firm_demand[leaf] = {}
            active_conditional[leaf] = {}
            access_shortfall[leaf] = {}
            starts[leaf] = {}
            available[leaf] = {}
            groups[leaf] = {}
            leaf_starts = []
            for quarter in quarter_names:
                group = leaf_to_group[leaf, quarter]
                groups[leaf][quarter] = group
                firm_value = _clean_nonnegative(model.firm_capacity[quarter, group])
                x_value = _clean_nonnegative(
                    model.conditional_capacity[quarter, group]
                )
                total_value = _clean_nonnegative(
                    model.total_capacity[quarter, group]
                )
                connected_value = _clean_nonnegative(
                    model.connected_demand[leaf, quarter]
                )
                firm_demand_value = _clean_nonnegative(
                    model.firm_demand[leaf, quarter]
                )
                start_value = float(
                    value(model.project_start[quarter, group])
                ) > 0.5
                firm_capacity[leaf][quarter] = firm_value
                conditional_capacity[leaf][quarter] = x_value
                total_capacity[leaf][quarter] = total_value
                connected_demand[leaf][quarter] = connected_value
                firm_demand[leaf][quarter] = firm_demand_value
                active_conditional[leaf][quarter] = max(
                    connected_value - firm_demand_value,
                    0.0,
                )
                access_shortfall[leaf][quarter] = _clean_nonnegative(
                    model.access_shortfall[leaf, quarter]
                )
                starts[leaf][quarter] = start_value
                if start_value:
                    leaf_starts.append(quarter)
                available[leaf][quarter] = float(
                    value(model.project_available[leaf, quarter])
                ) > 0.5
            start_quarter[leaf] = leaf_starts[0] if leaf_starts else None

        primary_value = float(value(access_shortfall_expression))
        contract_value = float(value(contract_exposure_expression))
        x_value = float(value(x_exposure_expression))
        maximum_actual_call = max(
            _clean_nonnegative(
                model.grid_call[quarter, operation, "actual", state]
            )
            for quarter, operation in operation_keys
            for state in state_names
        )
        maximum_contract_call = max(
            _clean_nonnegative(
                model.grid_call[quarter, operation, "contract", state]
            )
            for quarter, operation in operation_keys
            for state in state_names
        )
        return StochasticBaselineEndpoint(
            access_shortfall_mwh=primary_value,
            contract_capacity_exposure_mwh=contract_value,
            conditional_capacity_exposure_mwh=x_value,
            firm_capacity_mw=firm_capacity,
            conditional_capacity_mw=conditional_capacity,
            total_capacity_mw=total_capacity,
            connected_demand_mw=connected_demand,
            firm_demand_mw=firm_demand,
            active_conditional_demand_mw=active_conditional,
            access_shortfall_mw=access_shortfall,
            project_start_by_quarter=starts,
            project_start_quarter=start_quarter,
            project_available_by_quarter=available,
            decision_group_by_quarter=groups,
            primary_target_mwh=primary_target,
            primary_tolerance_mwh=primary_tolerance,
            primary_deviation_mwh=primary_value - primary_target,
            primary_band_violation_mwh=max(
                primary_value - primary_target - primary_tolerance,
                primary_target - primary_value - primary_tolerance,
                0.0,
            ),
            contract_exposure_target_mwh=contract_target,
            contract_exposure_tolerance_mwh=contract_tolerance,
            contract_exposure_deviation_mwh=contract_value - contract_target,
            contract_exposure_band_violation_mwh=max(
                contract_value - contract_target - contract_tolerance,
                contract_target - contract_value - contract_tolerance,
                0.0,
            ),
            x_exposure_target_mwh=x_target,
            x_exposure_tolerance_mwh=x_tolerance,
            x_exposure_deviation_mwh=x_value - x_target,
            x_exposure_band_violation_mwh=max(
                x_value - x_target - x_tolerance,
                x_target - x_value - x_tolerance,
                0.0,
            ),
            expected_project_count=float(value(expected_project_count_expression)),
            expected_commissioning_exposure_hours=float(
                value(commissioning_exposure_expression)
            ),
            maximum_actual_call_mw=maximum_actual_call,
            maximum_contract_call_mw=maximum_contract_call,
            maximum_original_constraint_violation=_maximum_model_violation(
                model,
                ignored_constraint_components=_LEXICOGRAPHIC_COMPONENTS,
            ),
            maximum_integrality_violation=_maximum_integrality_violation(model),
            normalization_label=normalization_label,
            planning_variable_scope=_PLANNING_VARIABLE_SCOPE,
        )

    def normalize_endpoint(
        *,
        primary_target: float,
        primary_tolerance: float,
        contract_target: float,
        contract_tolerance: float,
        x_target: float,
        x_tolerance: float,
        normalization_label: str,
        stage_prefix: str,
    ) -> StochasticBaselineEndpoint | None:
        model.endpoint_x_fix = Constraint(expr=x_exposure_expression == x_target)
        model.endpoint_project_count = Objective(
            expr=expected_project_count_expression,
            sense=minimize,
        )
        try:
            _, project_diagnostic = solve_session.solve(
                stage=f"{stage_prefix}_project_count"
            )
            stage_diagnostics.append(project_diagnostic)
            if not project_diagnostic.accepted:
                return None
            minimum_project_count = float(value(expected_project_count_expression))
            model.endpoint_project_count.deactivate()
            model.endpoint_project_count_fix = Constraint(
                expr=expected_project_count_expression == minimum_project_count
            )
            model.endpoint_commissioning_exposure = Objective(
                expr=commissioning_exposure_expression,
                sense=minimize,
            )
            _, commissioning_diagnostic = solve_session.solve(
                stage=f"{stage_prefix}_commissioning_exposure"
            )
            stage_diagnostics.append(commissioning_diagnostic)
            if not commissioning_diagnostic.accepted:
                return None
            try:
                endpoint = extract_endpoint(
                    primary_target=primary_target,
                    primary_tolerance=primary_tolerance,
                    contract_target=contract_target,
                    contract_tolerance=contract_tolerance,
                    x_target=x_target,
                    x_tolerance=x_tolerance,
                    normalization_label=normalization_label,
                )
            except RuntimeError as error:
                endpoint = None
                failure = "endpoint_extraction_violation"
                audit_message = str(error)
                maximum_constraint_violation = None
                maximum_integrality_violation = None
            else:
                maximum_constraint_violation = (
                    endpoint.maximum_original_constraint_violation
                )
                maximum_integrality_violation = endpoint.maximum_integrality_violation
                if maximum_constraint_violation > _MODEL_FEASIBILITY_TOLERANCE:
                    failure = "original_constraint_violation"
                elif maximum_integrality_violation > _INTEGRALITY_TOLERANCE:
                    failure = "integrality_violation"
                elif (
                    endpoint.primary_band_violation_mwh
                    > _LEXICOGRAPHIC_BAND_AUDIT_TOLERANCE
                ):
                    failure = "primary_band_violation"
                elif (
                    endpoint.contract_exposure_band_violation_mwh
                    > _LEXICOGRAPHIC_BAND_AUDIT_TOLERANCE
                ):
                    failure = "contract_exposure_band_violation"
                elif (
                    endpoint.x_exposure_band_violation_mwh
                    > _LEXICOGRAPHIC_BAND_AUDIT_TOLERANCE
                ):
                    failure = "x_exposure_band_violation"
                else:
                    failure = None
                audit_message = (
                    "Endpoint passed original, integrality, U, C, and X audits"
                    if failure is None
                    else f"Endpoint audit failed: {failure}"
                )
            stage_diagnostics.append(
                BaselineSolveDiagnostic(
                    stage=f"{stage_prefix}_endpoint_audit",
                    accepted=failure is None,
                    failure_reason=failure,
                    termination_condition="not_applicable",
                    solver_status="ok" if failure is None else "warning",
                    solver_message=audit_message,
                    lower_bound=None,
                    upper_bound=None,
                    absolute_gap=None,
                    gap_tolerance=None,
                    maximum_constraint_violation=maximum_constraint_violation,
                    maximum_integrality_violation=maximum_integrality_violation,
                )
            )
            return endpoint if failure is None else None
        finally:
            for name in (
                "endpoint_commissioning_exposure",
                "endpoint_project_count_fix",
                "endpoint_project_count",
                "endpoint_x_fix",
            ):
                component = model.component(name)
                if component is not None:
                    model.del_component(component)

    model.primary_access_shortfall = Objective(
        expr=access_shortfall_expression,
        sense=minimize,
    )
    _, diagnostic = solve_session.solve(stage="primary_access_shortfall")
    stage_diagnostics.append(diagnostic)
    if not diagnostic.accepted:
        return failed_result(
            diagnostic.termination_condition,
            diagnostic.solver_status,
            diagnostic.solver_message,
            failure_stage=diagnostic.stage,
        )
    primary = float(value(access_shortfall_expression))
    primary_tolerance = _mwh_tolerance(primary)
    model.primary_access_shortfall.deactivate()
    model.primary_access_shortfall_fix = Constraint(
        expr=access_shortfall_expression == primary
    )

    model.minimum_contract_exposure = Objective(
        expr=contract_exposure_expression,
        sense=minimize,
    )
    _, diagnostic = solve_session.solve(stage="minimum_contract_exposure")
    stage_diagnostics.append(diagnostic)
    if not diagnostic.accepted:
        return failed_result(
            diagnostic.termination_condition,
            diagnostic.solver_status,
            diagnostic.solver_message,
            failure_stage=diagnostic.stage,
            primary=primary,
            primary_tolerance=primary_tolerance,
        )
    minimum_contract = float(value(contract_exposure_expression))
    model.minimum_contract_exposure.deactivate()

    model.maximum_contract_exposure = Objective(
        expr=contract_exposure_expression,
        sense=maximize,
    )
    _, diagnostic = solve_session.solve(stage="maximum_contract_exposure")
    stage_diagnostics.append(diagnostic)
    if not diagnostic.accepted:
        return failed_result(
            diagnostic.termination_condition,
            diagnostic.solver_status,
            diagnostic.solver_message,
            failure_stage=diagnostic.stage,
            primary=primary,
            primary_tolerance=primary_tolerance,
            minimum_contract=minimum_contract,
        )
    maximum_contract = float(value(contract_exposure_expression))
    model.maximum_contract_exposure.deactivate()
    contract_tolerance = _mwh_tolerance(
        max(abs(minimum_contract), abs(maximum_contract))
    )
    contract_interval = _interval_diagnostic(
        stage="contract_exposure_interval_audit",
        lower=minimum_contract,
        upper=maximum_contract,
        tolerance=contract_tolerance,
        label="contract",
    )
    stage_diagnostics.append(contract_interval)
    if not contract_interval.accepted:
        return failed_result(
            contract_interval.termination_condition,
            contract_interval.solver_status,
            contract_interval.solver_message,
            failure_stage=contract_interval.stage,
            primary=primary,
            primary_tolerance=primary_tolerance,
            minimum_contract=minimum_contract,
            maximum_contract=maximum_contract,
            contract_tolerance=contract_tolerance,
        )
    minimum_contract = max(0.0, minimum_contract)
    maximum_contract = max(0.0, maximum_contract)
    model.minimum_contract_exposure_fix = Constraint(
        expr=contract_exposure_expression == minimum_contract
    )

    model.minimum_x_exposure = Objective(expr=x_exposure_expression, sense=minimize)
    _, diagnostic = solve_session.solve(stage="minimum_x_exposure")
    stage_diagnostics.append(diagnostic)
    if not diagnostic.accepted:
        return failed_result(
            diagnostic.termination_condition,
            diagnostic.solver_status,
            diagnostic.solver_message,
            failure_stage=diagnostic.stage,
            primary=primary,
            primary_tolerance=primary_tolerance,
            minimum_contract=minimum_contract,
            maximum_contract=maximum_contract,
            contract_tolerance=contract_tolerance,
        )
    minimum_x = float(value(x_exposure_expression))
    model.minimum_x_exposure.deactivate()

    model.maximum_x_exposure = Objective(expr=x_exposure_expression, sense=maximize)
    _, diagnostic = solve_session.solve(stage="maximum_x_exposure")
    stage_diagnostics.append(diagnostic)
    if not diagnostic.accepted:
        return failed_result(
            diagnostic.termination_condition,
            diagnostic.solver_status,
            diagnostic.solver_message,
            failure_stage=diagnostic.stage,
            primary=primary,
            primary_tolerance=primary_tolerance,
            minimum_contract=minimum_contract,
            maximum_contract=maximum_contract,
            contract_tolerance=contract_tolerance,
            minimum_x=minimum_x,
        )
    maximum_x = float(value(x_exposure_expression))
    model.maximum_x_exposure.deactivate()
    x_tolerance = _mwh_tolerance(max(abs(minimum_x), abs(maximum_x)))
    x_interval = _interval_diagnostic(
        stage="x_exposure_interval_audit",
        lower=minimum_x,
        upper=maximum_x,
        tolerance=x_tolerance,
        label="x",
    )
    stage_diagnostics.append(x_interval)
    if not x_interval.accepted:
        return failed_result(
            x_interval.termination_condition,
            x_interval.solver_status,
            x_interval.solver_message,
            failure_stage=x_interval.stage,
            primary=primary,
            primary_tolerance=primary_tolerance,
            minimum_contract=minimum_contract,
            maximum_contract=maximum_contract,
            contract_tolerance=contract_tolerance,
            minimum_x=minimum_x,
            maximum_x=maximum_x,
            x_tolerance=x_tolerance,
        )
    minimum_x = max(0.0, minimum_x)
    maximum_x = max(0.0, maximum_x)

    minimum_endpoint = normalize_endpoint(
        primary_target=primary,
        primary_tolerance=primary_tolerance,
        contract_target=minimum_contract,
        contract_tolerance=contract_tolerance,
        x_target=minimum_x,
        x_tolerance=x_tolerance,
        normalization_label=_MINIMUM_X_NORMALIZATION,
        stage_prefix="minimum_x",
    )
    if minimum_endpoint is None:
        last = stage_diagnostics[-1]
        return failed_result(
            last.termination_condition,
            last.solver_status,
            last.solver_message,
            failure_stage=last.stage,
            primary=primary,
            primary_tolerance=primary_tolerance,
            minimum_contract=minimum_contract,
            maximum_contract=maximum_contract,
            contract_tolerance=contract_tolerance,
            minimum_x=minimum_x,
            maximum_x=maximum_x,
            x_tolerance=x_tolerance,
        )
    maximum_endpoint = normalize_endpoint(
        primary_target=primary,
        primary_tolerance=primary_tolerance,
        contract_target=minimum_contract,
        contract_tolerance=contract_tolerance,
        x_target=maximum_x,
        x_tolerance=x_tolerance,
        normalization_label=_MAXIMUM_X_NORMALIZATION,
        stage_prefix="maximum_x",
    )
    if maximum_endpoint is None:
        last = stage_diagnostics[-1]
        return failed_result(
            last.termination_condition,
            last.solver_status,
            last.solver_message,
            failure_stage=last.stage,
            primary=primary,
            primary_tolerance=primary_tolerance,
            minimum_contract=minimum_contract,
            maximum_contract=maximum_contract,
            contract_tolerance=contract_tolerance,
            minimum_x=minimum_x,
            maximum_x=maximum_x,
            x_tolerance=x_tolerance,
            minimum_endpoint=minimum_endpoint,
        )

    return StochasticBaselineResult(
        policy=policy,
        role=planning_policy.role,
        implementable=planning_policy.implementable,
        feasible=True,
        termination_condition="stochastic_baseline_embedded_layers_feasible",
        solver_status="ok",
        solver_message=(
            "All lexicographic stages and embedded actual/contract state audits passed"
        ),
        primary_access_shortfall_mwh=primary,
        primary_tolerance_mwh=primary_tolerance,
        minimum_contract_exposure_mwh=minimum_contract,
        maximum_contract_exposure_mwh=maximum_contract,
        contract_exposure_tolerance_mwh=contract_tolerance,
        minimum_x_exposure_mwh=minimum_x,
        maximum_x_exposure_mwh=maximum_x,
        x_exposure_tolerance_mwh=x_tolerance,
        minimum_x_endpoint=minimum_endpoint,
        maximum_x_endpoint=maximum_endpoint,
        displayed_endpoint=minimum_endpoint,
        displayed_endpoint_name="minimum_contract_minimum_x",
        normalization_label=_MINIMUM_X_NORMALIZATION,
        failure_stage=None,
        stage_diagnostics=tuple(stage_diagnostics),
        planning_variable_scope=_PLANNING_VARIABLE_SCOPE,
        natural_node_counts=natural_node_counts,
        decision_group_counts=decision_group_counts,
        states=states,
        excluded_branch_indices=excluded_branches,
        embedded_state_rows=len(operation_keys) * len(_LAYERS) * len(states),
    )


def _single_leaf_b5_tree(
    tree: FrozenScenarioTree,
    leaf_name: str,
) -> FrozenScenarioTree:
    leaf = next(item for item in tree.leaves if item.name == leaf_name)
    demand_state = next(
        item for item in tree.demand_states if item.name == leaf.demand_state
    )
    project_state = next(
        item for item in tree.project_states if item.name == leaf.project_state
    )
    nodes = tuple(
        ScenarioNode(
            name=f"{leaf_name}__{quarter}",
            quarter=quarter,
            parent=(
                None
                if position == 0
                else f"{leaf_name}__{tree.quarters[position - 1]}"
            ),
            probability=1.0,
            leaves=(leaf_name,),
        )
        for position, quarter in enumerate(tree.quarters)
    )
    b5_policy = _policy_data(tree, StochasticBaselinePolicy.B5)
    b5_policy = replace(
        b5_policy,
        decision_groups=tuple(
            QuarterDecisionGroups(quarter=quarter, groups=((leaf_name,),))
            for quarter in tree.quarters
        ),
    )
    return replace(
        tree,
        demand_states=(replace(demand_state, probability=1.0),),
        project_states=(replace(project_state, probability=1.0),),
        leaves=(replace(leaf, probability=1.0),),
        nodes=nodes,
        policies=(b5_policy,),
    )


def _weighted_sum(values: Iterable[float], weights: tuple[float, ...]) -> float:
    return sum(weight * float(number) for weight, number in zip(weights, values))


def _aggregate_b5_diagnostics(
    results: tuple[StochasticBaselineResult, ...],
    weights: tuple[float, ...],
) -> tuple[BaselineSolveDiagnostic, ...]:
    diagnostics = []
    for leaf_stages in zip(*(result.stage_diagnostics for result in results)):
        stage_names = {item.stage for item in leaf_stages}
        if len(stage_names) != 1:
            raise RuntimeError("B5 leaf decomposition returned inconsistent stages")

        def weighted_optional(field: str) -> float | None:
            values = tuple(getattr(item, field) for item in leaf_stages)
            if any(item is None for item in values):
                return None
            return _weighted_sum(values, weights)

        def maximum_optional(field: str) -> float | None:
            values = tuple(
                getattr(item, field)
                for item in leaf_stages
                if getattr(item, field) is not None
            )
            return max(values) if values else None

        terminations = {item.termination_condition for item in leaf_stages}
        statuses = {item.solver_status for item in leaf_stages}
        diagnostics.append(
            BaselineSolveDiagnostic(
                stage=leaf_stages[0].stage,
                accepted=all(item.accepted for item in leaf_stages),
                failure_reason=None,
                termination_condition=(
                    leaf_stages[0].termination_condition
                    if len(terminations) == 1
                    else "decomposed_leaf_stages_accepted"
                ),
                solver_status=(
                    leaf_stages[0].solver_status
                    if len(statuses) == 1
                    else "decomposed"
                ),
                solver_message=(
                    f"Exact probability-weighted aggregation of {len(results)} "
                    "independent perfect-information leaves"
                ),
                lower_bound=weighted_optional("lower_bound"),
                upper_bound=weighted_optional("upper_bound"),
                absolute_gap=weighted_optional("absolute_gap"),
                gap_tolerance=weighted_optional("gap_tolerance"),
                maximum_constraint_violation=maximum_optional(
                    "maximum_constraint_violation"
                ),
                maximum_integrality_violation=maximum_optional(
                    "maximum_integrality_violation"
                ),
            )
        )
    return tuple(diagnostics)


def _aggregate_b5_endpoint(
    tree: FrozenScenarioTree,
    results: tuple[StochasticBaselineResult, ...],
    weights: tuple[float, ...],
    *,
    endpoint_name: str,
    primary_target: float,
    contract_target: float,
    x_target: float,
) -> StochasticBaselineEndpoint:
    sources = tuple(
        getattr(result, endpoint_name)
        for result in results
    )
    if any(source is None for source in sources):
        raise RuntimeError("Feasible B5 leaf result is missing an endpoint")

    def merged(field: str) -> dict:
        combined = {}
        for source in sources:
            combined.update(getattr(source, field))
        return combined

    primary_value = _weighted_sum(
        (source.access_shortfall_mwh for source in sources),
        weights,
    )
    contract_value = _weighted_sum(
        (source.contract_capacity_exposure_mwh for source in sources),
        weights,
    )
    x_value = _weighted_sum(
        (source.conditional_capacity_exposure_mwh for source in sources),
        weights,
    )
    primary_tolerance = _mwh_tolerance(primary_target)
    contract_tolerance = _mwh_tolerance(contract_target)
    x_tolerance = _mwh_tolerance(x_target)
    primary_deviation = abs(primary_value - primary_target)
    contract_deviation = abs(contract_value - contract_target)
    x_deviation = abs(x_value - x_target)
    _, leaf_to_group, _ = _decision_structure(
        tree,
        StochasticBaselinePolicy.B5,
        tree.quarters,
    )
    decision_groups = {
        leaf: {
            quarter: leaf_to_group[leaf, quarter] for quarter in tree.quarters
        }
        for leaf in tree.leaf_names
    }
    labels = {source.normalization_label for source in sources}
    if len(labels) != 1:
        raise RuntimeError("B5 leaf endpoints have inconsistent normalization labels")
    return StochasticBaselineEndpoint(
        access_shortfall_mwh=primary_value,
        contract_capacity_exposure_mwh=contract_value,
        conditional_capacity_exposure_mwh=x_value,
        firm_capacity_mw=merged("firm_capacity_mw"),
        conditional_capacity_mw=merged("conditional_capacity_mw"),
        total_capacity_mw=merged("total_capacity_mw"),
        connected_demand_mw=merged("connected_demand_mw"),
        firm_demand_mw=merged("firm_demand_mw"),
        active_conditional_demand_mw=merged("active_conditional_demand_mw"),
        access_shortfall_mw=merged("access_shortfall_mw"),
        project_start_by_quarter=merged("project_start_by_quarter"),
        project_start_quarter=merged("project_start_quarter"),
        project_available_by_quarter=merged("project_available_by_quarter"),
        decision_group_by_quarter=decision_groups,
        primary_target_mwh=primary_target,
        primary_tolerance_mwh=primary_tolerance,
        primary_deviation_mwh=primary_deviation,
        primary_band_violation_mwh=max(
            0.0, primary_deviation - primary_tolerance
        ),
        contract_exposure_target_mwh=contract_target,
        contract_exposure_tolerance_mwh=contract_tolerance,
        contract_exposure_deviation_mwh=contract_deviation,
        contract_exposure_band_violation_mwh=max(
            0.0, contract_deviation - contract_tolerance
        ),
        x_exposure_target_mwh=x_target,
        x_exposure_tolerance_mwh=x_tolerance,
        x_exposure_deviation_mwh=x_deviation,
        x_exposure_band_violation_mwh=max(0.0, x_deviation - x_tolerance),
        expected_project_count=_weighted_sum(
            (source.expected_project_count for source in sources), weights
        ),
        expected_commissioning_exposure_hours=_weighted_sum(
            (
                source.expected_commissioning_exposure_hours
                for source in sources
            ),
            weights,
        ),
        maximum_actual_call_mw=max(
            source.maximum_actual_call_mw for source in sources
        ),
        maximum_contract_call_mw=max(
            source.maximum_contract_call_mw for source in sources
        ),
        maximum_original_constraint_violation=max(
            source.maximum_original_constraint_violation for source in sources
        ),
        maximum_integrality_violation=max(
            source.maximum_integrality_violation for source in sources
        ),
        normalization_label=labels.pop(),
        planning_variable_scope=_PLANNING_VARIABLE_SCOPE,
    )


def _solve_b5_decomposed(
    data: Rts24Data,
    *,
    tree: FrozenScenarioTree,
    quarters: tuple[FxQuarter, ...],
    poi: FixedPoi,
    project: ExistingBranchUpgrade,
    service_envelope: FxServiceEnvelope,
    redispatch_up_mw: Mapping[int, float],
    redispatch_down_mw: Mapping[int, float],
    branch_indices: tuple[int, ...] | None,
    generator_indices: tuple[int, ...] | None,
    immediate_rating: str,
    sustained_rating: str,
    solver_name: str,
    tee: bool,
) -> StochasticBaselineResult:
    leaf_results = []
    for leaf in tree.leaves:
        result = _solve_stochastic_baseline_monolithic(
            data,
            policy=StochasticBaselinePolicy.B5,
            tree=_single_leaf_b5_tree(tree, leaf.name),
            quarters=quarters,
            poi=poi,
            project=project,
            service_envelope=service_envelope,
            redispatch_up_mw=redispatch_up_mw,
            redispatch_down_mw=redispatch_down_mw,
            branch_indices=branch_indices,
            generator_indices=generator_indices,
            immediate_rating=immediate_rating,
            sustained_rating=sustained_rating,
            solver_name=solver_name,
            tee=tee,
        )
        if not result.feasible:
            return replace(
                result,
                solver_message=(
                    f"Perfect-information leaf {leaf.name} failed: "
                    f"{result.solver_message}"
                ),
                natural_node_counts={
                    quarter: len(tree.nodes_for_quarter(quarter))
                    for quarter in tree.quarters
                },
                decision_group_counts={
                    quarter: len(tree.decision_groups("B5", quarter))
                    for quarter in tree.quarters
                },
                embedded_state_rows=(
                    len(tree.leaves)
                    * len(tree.quarters)
                    * len(_LAYERS)
                    * len(result.states)
                ),
            )
        leaf_results.append(result)

    results = tuple(leaf_results)
    weights = tuple(leaf.probability for leaf in tree.leaves)
    primary = _weighted_sum(
        (result.primary_access_shortfall_mwh for result in results), weights
    )
    minimum_contract = _weighted_sum(
        (result.minimum_contract_exposure_mwh for result in results), weights
    )
    maximum_contract = _weighted_sum(
        (result.maximum_contract_exposure_mwh for result in results), weights
    )
    minimum_x = _weighted_sum(
        (result.minimum_x_exposure_mwh for result in results), weights
    )
    maximum_x = _weighted_sum(
        (result.maximum_x_exposure_mwh for result in results), weights
    )
    minimum_endpoint = _aggregate_b5_endpoint(
        tree,
        results,
        weights,
        endpoint_name="minimum_x_endpoint",
        primary_target=primary,
        contract_target=minimum_contract,
        x_target=minimum_x,
    )
    maximum_endpoint = _aggregate_b5_endpoint(
        tree,
        results,
        weights,
        endpoint_name="maximum_x_endpoint",
        primary_target=primary,
        contract_target=minimum_contract,
        x_target=maximum_x,
    )
    planning_policy = _policy_data(tree, StochasticBaselinePolicy.B5)
    states = results[0].states
    return StochasticBaselineResult(
        policy=StochasticBaselinePolicy.B5,
        role=planning_policy.role,
        implementable=planning_policy.implementable,
        feasible=True,
        termination_condition="exact_perfect_information_leaf_decomposition",
        solver_status="ok",
        solver_message=(
            f"All {len(results)} independent perfect-information leaves and "
            "their probability-weighted lexicographic aggregation passed"
        ),
        primary_access_shortfall_mwh=primary,
        primary_tolerance_mwh=_mwh_tolerance(primary),
        minimum_contract_exposure_mwh=minimum_contract,
        maximum_contract_exposure_mwh=maximum_contract,
        contract_exposure_tolerance_mwh=_mwh_tolerance(
            max(abs(minimum_contract), abs(maximum_contract))
        ),
        minimum_x_exposure_mwh=minimum_x,
        maximum_x_exposure_mwh=maximum_x,
        x_exposure_tolerance_mwh=_mwh_tolerance(
            max(abs(minimum_x), abs(maximum_x))
        ),
        minimum_x_endpoint=minimum_endpoint,
        maximum_x_endpoint=maximum_endpoint,
        displayed_endpoint=minimum_endpoint,
        displayed_endpoint_name="minimum_contract_minimum_x",
        normalization_label=_MINIMUM_X_NORMALIZATION,
        failure_stage=None,
        stage_diagnostics=_aggregate_b5_diagnostics(results, weights),
        planning_variable_scope=_PLANNING_VARIABLE_SCOPE,
        natural_node_counts={
            quarter: len(tree.nodes_for_quarter(quarter))
            for quarter in tree.quarters
        },
        decision_group_counts={
            quarter: len(tree.decision_groups("B5", quarter))
            for quarter in tree.quarters
        },
        states=states,
        excluded_branch_indices=results[0].excluded_branch_indices,
        embedded_state_rows=(
            len(tree.leaves)
            * len(tree.quarters)
            * len(_LAYERS)
            * len(states)
        ),
    )


def solve_stochastic_baseline(
    data: Rts24Data,
    *,
    policy: StochasticBaselinePolicy,
    tree: FrozenScenarioTree,
    quarters: Iterable[FxQuarter],
    poi: FixedPoi,
    project: ExistingBranchUpgrade,
    service_envelope: FxServiceEnvelope,
    redispatch_up_mw: Mapping[int, float],
    redispatch_down_mw: Mapping[int, float],
    branch_indices: Iterable[int] | None = None,
    generator_indices: Iterable[int] | None = None,
    immediate_rating: str = "rate_c",
    sustained_rating: str = "rate_a",
    solver_name: str = "highs",
    tee: bool = False,
) -> StochasticBaselineResult:
    """Solve one B3/B4 model or the exactly decomposed B5 bound."""

    policy = StochasticBaselinePolicy(policy)
    quarters = tuple(quarters)
    selected_branches = None if branch_indices is None else tuple(branch_indices)
    selected_generators = (
        None if generator_indices is None else tuple(generator_indices)
    )
    if policy is StochasticBaselinePolicy.B5 and len(tree.leaves) > 1:
        return _solve_b5_decomposed(
            data,
            tree=tree,
            quarters=quarters,
            poi=poi,
            project=project,
            service_envelope=service_envelope,
            redispatch_up_mw=redispatch_up_mw,
            redispatch_down_mw=redispatch_down_mw,
            branch_indices=selected_branches,
            generator_indices=selected_generators,
            immediate_rating=immediate_rating,
            sustained_rating=sustained_rating,
            solver_name=solver_name,
            tee=tee,
        )
    return _solve_stochastic_baseline_monolithic(
        data,
        policy=policy,
        tree=tree,
        quarters=quarters,
        poi=poi,
        project=project,
        service_envelope=service_envelope,
        redispatch_up_mw=redispatch_up_mw,
        redispatch_down_mw=redispatch_down_mw,
        branch_indices=selected_branches,
        generator_indices=selected_generators,
        immediate_rating=immediate_rating,
        sustained_rating=sustained_rating,
        solver_name=solver_name,
        tee=tee,
    )


__all__ = [
    "StochasticBaselineEndpoint",
    "StochasticBaselinePolicy",
    "StochasticBaselineResult",
    "solve_stochastic_baseline",
]
