"""Deterministic MW-only F/X contract execution and certification evaluator."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, radians
from numbers import Real
from typing import Iterable, Mapping

from pyomo.environ import (
    Block,
    ConcreteModel,
    Constraint,
    ConstraintList,
    NonNegativeReals,
    Objective,
    Set,
    SolverFactory,
    Var,
    minimize,
    value,
)
from pyomo.opt import TerminationCondition

from ..evaluation.capacity_metrics import (
    CapacityMilestones,
    calculate_capacity_milestones,
)
from ..grid.dc_opf import DcOpfResult
from ..grid.rts24 import Rts24Data
from ..grid.scopf import (
    SecurityState,
    build_security_states,
    non_islanding_branch_indices,
)
from ..solvers import (
    linear_expression_after_fixing_quadratics,
    solve_separable_convex_qp,
)
from .deterministic_expansion import (
    ExistingBranchUpgrade,
    FixedPoi,
    _rating_increases,
    _validate_nonnegative_finite,
)


_RESPONSE_MODEL = "mw_only_sustained_states_no_duration_or_energy_limits"


@dataclass(frozen=True)
class FxQuarter:
    name: str
    system_load_multiplier: float
    data_center_demand_mw: float
    operating_hours: float
    continuous_validation_hours: float
    discount_factor: float


@dataclass(frozen=True)
class FixedFxPlan:
    firm_capacity_mw: Mapping[str, float]
    conditional_capacity_mw: Mapping[str, float]
    project_start_quarter: str | None
    parameter_status: str


@dataclass(frozen=True)
class FxServiceEnvelope:
    max_conditional_capacity_mw: float
    minimum_operational_block_mw: float
    minimum_validation_hours: float
    response_model: str
    parameter_status: str


@dataclass(frozen=True)
class DeterministicFxResult:
    feasible: bool
    termination_condition: str
    solver_status: str
    solver_message: str
    objective: float | None
    primary_optimization_objective: float | None
    canonical_dispatch_primary_objective: float | None
    primary_qp_solver: str
    primary_qp_status: str
    primary_qp_iterations: int | None
    primary_qp_primal_residual: float | None
    primary_qp_dual_residual: float | None
    primary_qp_max_constraint_violation: float | None
    primary_qp_max_bound_projection: float | None
    primary_qp_solve_seconds: float | None
    primary_linear_repair_objective_deviation: float | None
    primary_linear_repair_objective_deviation_tolerance: float | None
    primary_linear_repair_total_generation_movement_mw: float | None
    primary_linear_repair_max_generation_movement_mw: float | None
    primary_linear_repair_generation_movement_tolerance_mw: float | None
    primary_linear_repair_acceptance_interpretation: str
    investment_cost: float | None
    operating_cost: float | None
    access_shortfall_cost: float | None
    minimum_call_certificate_mw_sum: float | None
    project_started: bool
    start_quarter: str | None
    commissioned_by_quarter: dict[str, bool]
    firm_capacity_mw: dict[str, float]
    conditional_capacity_mw: dict[str, float]
    total_capacity_mw: dict[str, float]
    connected_demand_mw: dict[str, float]
    firm_demand_mw: dict[str, float]
    active_conditional_demand_mw: dict[str, float]
    access_shortfall_mw: dict[str, float]
    actual_grid_curtailment_mw: dict[str, dict[str, float]]
    actual_poi_load_mw: dict[str, dict[str, float]]
    certified_grid_curtailment_mw: dict[str, dict[str, float]]
    certified_poi_load_mw: dict[str, dict[str, float]]
    firm_breach_mw: dict[str, dict[str, float]]
    conditional_breach_mw: dict[str, dict[str, float]]
    actual_state_results: dict[str, dict[str, DcOpfResult]]
    certified_state_results: dict[str, dict[str, DcOpfResult]]
    effective_branch_ratings_mw: dict[str, dict[str, dict[int, float]]]
    base_operating_cost_per_hour: dict[str, float]
    unused_capacity_mw_year: float | None
    milestones: CapacityMilestones | None
    states: tuple[SecurityState, ...]
    excluded_branch_indices: tuple[int, ...]
    plan_parameter_status: str
    service_parameter_status: str
    response_model: str
    capacity_interpretation: str
    certified_dispatch_interpretation: str
    cost_interpretation: str
    breach_diagnostics_enabled: bool


def _is_optimal(termination: object) -> bool:
    return termination in {
        TerminationCondition.optimal,
        TerminationCondition.globallyOptimal,
        TerminationCondition.locallyOptimal,
    }


def _add_dispatch_layer(
    model: ConcreteModel,
    *,
    name: str,
    data: Rts24Data,
    quarters: tuple[FxQuarter, ...],
    states: tuple[SecurityState, ...],
    poi: FixedPoi,
    poi_load: Var,
    project: ExistingBranchUpgrade,
    commissioned_by_quarter: Mapping[str, bool],
    redispatch_up_mw: Mapping[int, float],
    redispatch_down_mw: Mapping[int, float],
) -> Block:
    quarter_by_name = {quarter.name: quarter for quarter in quarters}
    state_by_name = {state.name: state for state in states}
    bus_by_index = {bus.index: bus for bus in data.buses}
    branch_by_index = {branch.index: branch for branch in data.branches}
    generator_by_index = {generator.index: generator for generator in data.generators}
    generators_at_bus = {bus.index: [] for bus in data.buses}
    outgoing_at_bus = {bus.index: [] for bus in data.buses}
    incoming_at_bus = {bus.index: [] for bus in data.buses}
    for generator in data.generators:
        generators_at_bus[generator.bus].append(generator.index)
    for branch in data.branches:
        outgoing_at_bus[branch.from_bus].append(branch.index)
        incoming_at_bus[branch.to_bus].append(branch.index)

    block = Block()
    setattr(model, name, block)

    def generation_bounds(
        _block: Block,
        _quarter_name: str,
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

    block.generation = Var(
        model.QUARTER,
        model.STATE,
        model.GEN,
        bounds=generation_bounds,
    )
    # Degrees keep the network matrix well scaled; extracted angles use radians.
    block.angle = Var(model.QUARTER, model.STATE, model.BUS)
    block.flow = Var(model.QUARTER, model.STATE, model.BRANCH)

    def branch_flow_rule(
        block: Block,
        quarter_name: str,
        state_name: str,
        branch_index: int,
    ) -> object:
        state = state_by_name[state_name]
        branch = branch_by_index[branch_index]
        if (
            not branch.in_service
            or branch_index in state.outaged_branch_indices
        ):
            return block.flow[quarter_name, state_name, branch_index] == 0.0
        susceptance_mw_per_rad = data.base_mva / (
            branch.reactance_pu * branch.tap_ratio
        )
        return block.flow[
            quarter_name, state_name, branch_index
        ] == susceptance_mw_per_rad * (
            radians(1.0)
            * (
                block.angle[quarter_name, state_name, branch.from_bus]
                - block.angle[quarter_name, state_name, branch.to_bus]
            )
            - branch.phase_shift_rad
        )

    block.branch_flow = Constraint(
        model.QUARTER,
        model.STATE,
        model.BRANCH,
        rule=branch_flow_rule,
    )
    block.thermal_limits = ConstraintList()
    for quarter in quarters:
        for state in states:
            increases = _rating_increases(project, state.branch_rating)
            for branch in data.branches:
                rating = branch.rating_mw(state.branch_rating)
                if commissioned_by_quarter[quarter.name]:
                    rating += increases.get(branch.index, 0.0)
                flow = block.flow[quarter.name, state.name, branch.index]
                block.thermal_limits.add(flow <= rating)
                block.thermal_limits.add(-flow <= rating)

    def balance_rule(
        block: Block,
        quarter_name: str,
        state_name: str,
        bus: int,
    ) -> object:
        generation = sum(
            block.generation[quarter_name, state_name, index]
            for index in generators_at_bus[bus]
        )
        outgoing = sum(
            block.flow[quarter_name, state_name, index]
            for index in outgoing_at_bus[bus]
        )
        incoming = sum(
            block.flow[quarter_name, state_name, index]
            for index in incoming_at_bus[bus]
        )
        demand = (
            bus_by_index[bus].demand_mw
            * quarter_by_name[quarter_name].system_load_multiplier
        )
        if bus == poi.bus:
            demand += poi_load[quarter_name, state_name]
        return generation - demand == outgoing - incoming

    block.power_balance = Constraint(
        model.QUARTER,
        model.STATE,
        model.BUS,
        rule=balance_rule,
    )
    for quarter in quarters:
        for state in states:
            block.angle[quarter.name, state.name, data.reference_bus].fix(0.0)

    block.response = ConstraintList()
    for quarter in quarters:
        for state in states:
            if state.response_mode == "base":
                continue
            for generator in data.generators:
                if generator.index in state.outaged_generator_indices:
                    continue
                contingency = block.generation[
                    quarter.name, state.name, generator.index
                ]
                base = block.generation[quarter.name, "base", generator.index]
                if state.response_mode == "fixed":
                    block.response.add(contingency == base)
                elif state.response_mode == "bounded":
                    block.response.add(
                        contingency - base <= redispatch_up_mw[generator.index]
                    )
                    block.response.add(
                        base - contingency <= redispatch_down_mw[generator.index]
                    )
                else:
                    raise ValueError(
                        f"Unknown security response mode '{state.response_mode}'"
                    )
    return block


def _extract_layer_results(
    *,
    block: Block,
    data: Rts24Data,
    quarters: tuple[FxQuarter, ...],
    states: tuple[SecurityState, ...],
    poi: FixedPoi,
    poi_load_mw: Mapping[str, Mapping[str, float]],
    termination: object,
    solver_status: str,
    solver_message: str,
) -> dict[str, dict[str, DcOpfResult]]:
    bus_indices = tuple(bus.index for bus in data.buses)
    generator_indices = tuple(generator.index for generator in data.generators)
    branch_indices = tuple(branch.index for branch in data.branches)
    generators_at_bus = {bus.index: [] for bus in data.buses}
    outgoing_at_bus = {bus.index: [] for bus in data.buses}
    incoming_at_bus = {bus.index: [] for bus in data.buses}
    for generator in data.generators:
        generators_at_bus[generator.bus].append(generator.index)
    for branch in data.branches:
        outgoing_at_bus[branch.from_bus].append(branch.index)
        incoming_at_bus[branch.to_bus].append(branch.index)

    results = {}
    for quarter in quarters:
        quarter_results = {}
        native_demand = {
            bus.index: bus.demand_mw * quarter.system_load_multiplier
            for bus in data.buses
        }
        for state in states:
            generation = {
                index: float(
                    value(block.generation[quarter.name, state.name, index])
                )
                for index in generator_indices
            }
            angles = {
                index: radians(
                    float(value(block.angle[quarter.name, state.name, index]))
                )
                for index in bus_indices
            }
            flows = {
                index: float(value(block.flow[quarter.name, state.name, index]))
                for index in branch_indices
            }
            residuals = {}
            for bus in bus_indices:
                bus_generation = sum(
                    generation[index] for index in generators_at_bus[bus]
                )
                outgoing = sum(flows[index] for index in outgoing_at_bus[bus])
                incoming = sum(flows[index] for index in incoming_at_bus[bus])
                demand = native_demand[bus]
                if bus == poi.bus:
                    demand += poi_load_mw[quarter.name][state.name]
                residuals[bus] = bus_generation - demand - outgoing + incoming
            state_cost = sum(
                generator.cost_quadratic * generation[generator.index] ** 2
                + generator.cost_linear * generation[generator.index]
                + generator.cost_constant
                for generator in data.generators
                if generator.in_service
                and generator.index not in state.outaged_generator_indices
            )
            quarter_results[state.name] = DcOpfResult(
                feasible=True,
                termination_condition=str(termination),
                solver_status=solver_status,
                solver_message=solver_message,
                objective=state_cost,
                generation_mw=generation,
                bus_angles_rad=angles,
                branch_flows_mw=flows,
                power_balance_residuals_mw=residuals,
                reference_buses=(data.reference_bus,),
                outaged_branch_indices=state.outaged_branch_indices,
                outaged_generator_indices=state.outaged_generator_indices,
                branch_rating=state.branch_rating,
            )
        results[quarter.name] = quarter_results
    return results


def evaluate_deterministic_fx_plan(
    data: Rts24Data,
    *,
    quarters: Iterable[FxQuarter],
    poi: FixedPoi,
    project: ExistingBranchUpgrade,
    plan: FixedFxPlan,
    service_envelope: FxServiceEnvelope,
    redispatch_up_mw: Mapping[int, float],
    redispatch_down_mw: Mapping[int, float],
    access_shortfall_cost_per_mwh: float,
    branch_indices: Iterable[int] | None = None,
    generator_indices: Iterable[int] | None = None,
    immediate_rating: str = "rate_c",
    sustained_rating: str = "rate_a",
    primary_objective_tolerance: float = 1.0e-5,
    solver_name: str = "highs",
    tee: bool = False,
) -> DeterministicFxResult:
    """Evaluate one fixed quarterly F/X and project-start policy.

    This M3 gate proves MW-only service logic. It deliberately does not choose
    F/X capacity, because their relative economic value and event frequency are
    not yet evidenced. Sustained-state call minimization is only a canonical
    feasibility certificate and is excluded from the reported economic cost.
    """

    quarters = tuple(quarters)
    if not quarters:
        raise ValueError("At least one F/X quarter is required")
    quarter_names = tuple(quarter.name for quarter in quarters)
    if any(not name for name in quarter_names) or len(set(quarter_names)) != len(
        quarter_names
    ):
        raise ValueError("F/X quarter names must be nonempty and unique")
    for quarter in quarters:
        _validate_nonnegative_finite(
            "System load multiplier", quarter.system_load_multiplier
        )
        _validate_nonnegative_finite(
            "Data-center demand", quarter.data_center_demand_mw
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
        if not isfinite(quarter.discount_factor) or quarter.discount_factor <= 0.0:
            raise ValueError("Quarter discount factors must be finite and positive")

    if not plan.parameter_status:
        raise ValueError("F/X plan parameter status must be explicit")
    expected_quarters = set(quarter_names)
    for name, values in (
        ("Firm plan", plan.firm_capacity_mw),
        ("Conditional plan", plan.conditional_capacity_mw),
    ):
        if set(values) != expected_quarters:
            raise ValueError(f"{name} must contain every quarter exactly once")
        for capacity in values.values():
            _validate_nonnegative_finite(name, capacity)
    if plan.project_start_quarter not in {None, *quarter_names}:
        raise ValueError("Project start quarter is not in the planning horizon")

    if not service_envelope.parameter_status:
        raise ValueError("F/X service parameter status must be explicit")
    if service_envelope.response_model != _RESPONSE_MODEL:
        raise ValueError("Unsupported F/X response model")
    _validate_nonnegative_finite(
        "Maximum conditional capacity",
        service_envelope.max_conditional_capacity_mw,
    )
    if (
        not isfinite(service_envelope.minimum_operational_block_mw)
        or service_envelope.minimum_operational_block_mw <= 0.0
    ):
        raise ValueError("Minimum operational block must be finite and positive")
    if (
        not isfinite(service_envelope.minimum_validation_hours)
        or service_envelope.minimum_validation_hours <= 0.0
    ):
        raise ValueError("Minimum validation hours must be finite and positive")
    _validate_nonnegative_finite(
        "Access shortfall cost", access_shortfall_cost_per_mwh
    )
    _validate_nonnegative_finite(
        "Primary objective tolerance", primary_objective_tolerance
    )
    bus_indices = tuple(bus.index for bus in data.buses)
    if poi.bus not in bus_indices:
        raise ValueError(f"Unknown POI bus {poi.bus}")
    _validate_nonnegative_finite("Initial POI capacity", poi.initial_capacity_mw)
    _validate_nonnegative_finite(
        "Application capacity", poi.application_capacity_mw
    )
    if poi.initial_capacity_mw > poi.application_capacity_mw + 1.0e-9:
        raise ValueError("Initial POI capacity cannot exceed application capacity")
    if (
        service_envelope.minimum_operational_block_mw
        > poi.application_capacity_mw + 1.0e-9
    ):
        raise ValueError("Minimum operational block cannot exceed application capacity")
    if (
        service_envelope.max_conditional_capacity_mw
        > poi.application_capacity_mw + 1.0e-9
    ):
        raise ValueError(
            "Maximum conditional capacity cannot exceed application capacity"
        )

    firm_capacity = {
        name: float(plan.firm_capacity_mw[name]) for name in quarter_names
    }
    conditional_capacity = {
        name: float(plan.conditional_capacity_mw[name]) for name in quarter_names
    }
    total_capacity = {
        name: firm_capacity[name] + conditional_capacity[name]
        for name in quarter_names
    }
    for position, name in enumerate(quarter_names):
        if (
            conditional_capacity[name]
            > service_envelope.max_conditional_capacity_mw + 1.0e-9
        ):
            raise ValueError("Conditional plan exceeds the certified MW envelope")
        if total_capacity[name] > poi.application_capacity_mw + 1.0e-9:
            raise ValueError("F/X plan exceeds the application capacity")
        if position:
            previous = quarter_names[position - 1]
            if firm_capacity[name] < firm_capacity[previous] - 1.0e-9:
                raise ValueError("Firm capacity cannot decrease")
            if total_capacity[name] < total_capacity[previous] - 1.0e-9:
                raise ValueError("Total contract capacity cannot decrease")

    if (
        isinstance(project.lead_time_quarters, bool)
        or not isinstance(project.lead_time_quarters, int)
        or project.lead_time_quarters < 0
    ):
        raise ValueError("Project lead time must be a nonnegative integer")
    if not project.name or not project.parameter_status:
        raise ValueError("Project name and parameter status must be explicit")
    _validate_nonnegative_finite(
        "POI capacity increase", project.poi_capacity_increase_mw
    )
    _validate_nonnegative_finite("Investment cost", project.investment_cost)

    branch_by_index = {branch.index: branch for branch in data.branches}
    generator_by_index = {generator.index: generator for generator in data.generators}
    for rating in (immediate_rating, sustained_rating):
        _rating_increases(project, rating)
        for branch in data.branches:
            branch.rating_mw(rating)
    upgrade_branch_indices = set(project.rate_a_increase_mw) | set(
        project.rate_c_increase_mw
    )
    unknown_upgrade_branches = upgrade_branch_indices - branch_by_index.keys()
    if unknown_upgrade_branches:
        unknown = sorted(unknown_upgrade_branches)
        raise ValueError(
            f"Project contains unknown branch indices: {unknown}"
        )
    for mapping_name, increases in (
        ("RATE_A increase", project.rate_a_increase_mw),
        ("RATE_C increase", project.rate_c_increase_mw),
    ):
        for increase in increases.values():
            _validate_nonnegative_finite(mapping_name, increase)

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
    islanding = sorted(
        set(selected_branches) - set(non_islanding_branch_indices(data))
    )
    if islanding:
        raise ValueError(
            f"Security set cannot contain islanding branches: {islanding}"
        )

    generator_indices_all = tuple(generator_by_index)
    expected_generators = set(generator_indices_all)
    for name, limits in (
        ("Up redispatch", redispatch_up_mw),
        ("Down redispatch", redispatch_down_mw),
    ):
        if set(limits) != expected_generators:
            raise ValueError(f"{name} must contain every generator index")
        for limit in limits.values():
            _validate_nonnegative_finite(name, limit)
    for generator in data.generators:
        if generator.p_min_mw > generator.p_max_mw + 1.0e-9:
            raise ValueError(
                f"Generator {generator.index} has inconsistent output limits"
            )
        if not all(
            isfinite(number)
            for number in (
                generator.cost_quadratic,
                generator.cost_linear,
                generator.cost_constant,
            )
        ):
            raise ValueError("The direct QP requires finite generator costs")
        if generator.cost_quadratic < 0.0:
            raise ValueError("The direct QP requires convex generator costs")

    start_position = (
        None
        if plan.project_start_quarter is None
        else quarter_names.index(plan.project_start_quarter)
    )
    commissioned = {
        name: start_position is not None
        and position >= start_position + project.lead_time_quarters
        for position, name in enumerate(quarter_names)
    }
    connected_demand = {}
    firm_demand = {}
    active_conditional_demand = {}
    access_shortfall = {}
    for quarter in quarters:
        connected = min(quarter.data_center_demand_mw, total_capacity[quarter.name])
        active_firm = min(quarter.data_center_demand_mw, firm_capacity[quarter.name])
        connected_demand[quarter.name] = connected
        firm_demand[quarter.name] = active_firm
        active_conditional_demand[quarter.name] = connected - active_firm
        access_shortfall[quarter.name] = quarter.data_center_demand_mw - connected

    states = build_security_states(
        selected_branches,
        selected_generators,
        immediate_rating,
        sustained_rating,
    )
    state_names = tuple(state.name for state in states)
    branch_indices_all = tuple(branch_by_index)

    model = ConcreteModel()
    model.QUARTER = Set(initialize=quarter_names, ordered=True)
    model.STATE = Set(initialize=state_names, ordered=True)
    model.BUS = Set(initialize=bus_indices, ordered=True)
    model.GEN = Set(initialize=generator_indices_all, ordered=True)
    model.BRANCH = Set(initialize=branch_indices_all, ordered=True)

    model.firm_capacity = Var(model.QUARTER, domain=NonNegativeReals)
    model.conditional_capacity = Var(model.QUARTER, domain=NonNegativeReals)
    for name in quarter_names:
        model.firm_capacity[name].fix(firm_capacity[name])
        model.conditional_capacity[name].fix(conditional_capacity[name])
    model.contract_limits = ConstraintList()
    for quarter in quarters:
        name = quarter.name
        total = model.firm_capacity[name] + model.conditional_capacity[name]
        model.contract_limits.add(total <= poi.application_capacity_mw)
        model.contract_limits.add(
            total
            <= poi.initial_capacity_mw
            + project.poi_capacity_increase_mw * int(commissioned[name])
        )
        model.contract_limits.add(
            model.conditional_capacity[name]
            <= service_envelope.max_conditional_capacity_mw
        )

    model.actual_grid_curtailment = Var(
        model.QUARTER, model.STATE, domain=NonNegativeReals
    )
    model.certified_grid_curtailment = Var(
        model.QUARTER, model.STATE, domain=NonNegativeReals
    )
    model.firm_breach = Var(
        model.QUARTER, model.STATE, domain=NonNegativeReals
    )
    model.conditional_breach = Var(
        model.QUARTER, model.STATE, domain=NonNegativeReals
    )
    model.actual_poi_load = Var(
        model.QUARTER, model.STATE, domain=NonNegativeReals
    )
    model.certified_poi_load = Var(
        model.QUARTER, model.STATE, domain=NonNegativeReals
    )
    model.service_balance = ConstraintList()
    for quarter in quarters:
        for state in states:
            key = (quarter.name, state.name)
            model.firm_breach[key].fix(0.0)
            model.conditional_breach[key].fix(0.0)
            if state.response_mode in {"base", "fixed"}:
                model.actual_grid_curtailment[key].fix(0.0)
                model.certified_grid_curtailment[key].fix(0.0)
            else:
                model.service_balance.add(
                    model.actual_grid_curtailment[key]
                    <= active_conditional_demand[quarter.name]
                )
                model.service_balance.add(
                    model.certified_grid_curtailment[key]
                    <= model.conditional_capacity[quarter.name]
                )
            model.service_balance.add(
                model.actual_poi_load[key]
                == connected_demand[quarter.name]
                - model.actual_grid_curtailment[key]
                - model.firm_breach[key]
                - model.conditional_breach[key]
            )
            model.service_balance.add(
                model.actual_poi_load[key] >= firm_demand[quarter.name]
            )
            model.service_balance.add(
                model.certified_poi_load[key]
                == model.firm_capacity[quarter.name]
                + model.conditional_capacity[quarter.name]
                - model.certified_grid_curtailment[key]
            )
            model.service_balance.add(
                model.certified_poi_load[key]
                >= model.firm_capacity[quarter.name]
            )

    actual = _add_dispatch_layer(
        model,
        name="actual",
        data=data,
        quarters=quarters,
        states=states,
        poi=poi,
        poi_load=model.actual_poi_load,
        project=project,
        commissioned_by_quarter=commissioned,
        redispatch_up_mw=redispatch_up_mw,
        redispatch_down_mw=redispatch_down_mw,
    )
    certified = _add_dispatch_layer(
        model,
        name="certified",
        data=data,
        quarters=quarters,
        states=states,
        poi=poi,
        poi_load=model.certified_poi_load,
        project=project,
        commissioned_by_quarter=commissioned,
        redispatch_up_mw=redispatch_up_mw,
        redispatch_down_mw=redispatch_down_mw,
    )

    investment_cost_expression = 0.0
    if plan.project_start_quarter is not None:
        start_quarter = quarters[start_position]
        investment_cost_expression = (
            project.investment_cost * start_quarter.discount_factor
        )
    model.primary_cost = Objective(
        expr=investment_cost_expression
        + sum(
            quarter.discount_factor
            * quarter.operating_hours
            * (
                sum(
                    generator.cost_quadratic
                    * actual.generation[
                        quarter.name, "base", generator.index
                    ]
                    ** 2
                    + generator.cost_linear
                    * actual.generation[
                        quarter.name, "base", generator.index
                    ]
                    + generator.cost_constant
                    for generator in data.generators
                    if generator.in_service
                )
                + access_shortfall_cost_per_mwh
                * access_shortfall[quarter.name]
            )
            for quarter in quarters
        ),
        sense=minimize,
    )

    linear_solver_probe = SolverFactory(solver_name)
    if not linear_solver_probe.available(exception_flag=False):
        raise RuntimeError(f"Solver '{solver_name}' is not available")
    primary_qp = solve_separable_convex_qp(model, verbose=tee)
    excluded_branches = tuple(
        branch.index
        for branch in data.branches
        if branch.in_service and branch.index not in selected_branches
    )
    common_result = {
        "project_started": plan.project_start_quarter is not None,
        "start_quarter": plan.project_start_quarter,
        "commissioned_by_quarter": dict(commissioned),
        "firm_capacity_mw": dict(firm_capacity),
        "conditional_capacity_mw": dict(conditional_capacity),
        "total_capacity_mw": dict(total_capacity),
        "connected_demand_mw": dict(connected_demand),
        "firm_demand_mw": dict(firm_demand),
        "active_conditional_demand_mw": dict(active_conditional_demand),
        "access_shortfall_mw": dict(access_shortfall),
        "states": states,
        "excluded_branch_indices": excluded_branches,
        "plan_parameter_status": plan.parameter_status,
        "service_parameter_status": service_envelope.parameter_status,
        "response_model": service_envelope.response_model,
        "capacity_interpretation": (
            "fixed_contract_capacity_separate_from_actual_connected_demand"
        ),
        "certified_dispatch_interpretation": (
            "independent_counterfactual_dispatch_not_transition_from_actual"
        ),
        "cost_interpretation": (
            "direct_convex_qp_numerical_solution_then_l1_linear_"
            "feasibility_projection_and_minimum_call"
        ),
        "breach_diagnostics_enabled": False,
    }

    def infeasible_result(
        *,
        termination_condition: object,
        solver_status: object,
        solver_message: object,
        repair_deviation: float | None = None,
        repair_deviation_tolerance: float | None = None,
        repair_total_movement: float | None = None,
        repair_max_movement: float | None = None,
        repair_movement_tolerance: float | None = None,
    ) -> DeterministicFxResult:
        return DeterministicFxResult(
            feasible=False,
            termination_condition=str(termination_condition),
            solver_status=str(solver_status),
            solver_message=str(solver_message),
            objective=None,
            primary_optimization_objective=None,
            canonical_dispatch_primary_objective=None,
            primary_qp_solver="osqp",
            primary_qp_status=primary_qp.status,
            primary_qp_iterations=primary_qp.iterations,
            primary_qp_primal_residual=primary_qp.primal_residual,
            primary_qp_dual_residual=primary_qp.dual_residual,
            primary_qp_max_constraint_violation=(
                primary_qp.max_constraint_violation
            ),
            primary_qp_max_bound_projection=primary_qp.max_bound_projection,
            primary_qp_solve_seconds=primary_qp.solve_seconds,
            primary_linear_repair_objective_deviation=repair_deviation,
            primary_linear_repair_objective_deviation_tolerance=(
                repair_deviation_tolerance
            ),
            primary_linear_repair_total_generation_movement_mw=(
                repair_total_movement
            ),
            primary_linear_repair_max_generation_movement_mw=(
                repair_max_movement
            ),
            primary_linear_repair_generation_movement_tolerance_mw=(
                repair_movement_tolerance
            ),
            primary_linear_repair_acceptance_interpretation=(
                "numerical_feasibility_projection_envelopes_not_"
                "optimality_gap_or_error_certificate"
            ),
            investment_cost=None,
            operating_cost=None,
            access_shortfall_cost=None,
            minimum_call_certificate_mw_sum=None,
            actual_grid_curtailment_mw={},
            actual_poi_load_mw={},
            certified_grid_curtailment_mw={},
            certified_poi_load_mw={},
            firm_breach_mw={},
            conditional_breach_mw={},
            actual_state_results={},
            certified_state_results={},
            effective_branch_ratings_mw={},
            base_operating_cost_per_hour={},
            unused_capacity_mw_year=None,
            milestones=None,
            **common_result,
        )

    if not primary_qp.solved or primary_qp.objective_value is None:
        return infeasible_result(
            termination_condition=primary_qp.status,
            solver_status="warning",
            solver_message=(
                "OSQP primary QP did not pass the configured status and "
                "feasibility audit"
            ),
        )

    osqp_primary_objective = primary_qp.objective_value
    # Project the audited OSQP point onto the exact linear feasible set with
    # the smallest aggregate movement in base-generation coordinates.  Exact
    # fixing can make the feasibility LP infeasible when the numerical QP point
    # has a small accepted balance residual.  Movement and original-objective
    # changes are both audited below; neither is an optimality-gap certificate.
    repair_targets = {}
    repair_indices = []
    for quarter in quarters:
        for generator in data.generators:
            index = (quarter.name, generator.index)
            repair_indices.append(index)
            repair_targets[index] = float(
                value(actual.generation[quarter.name, "base", generator.index])
            )
    model.PRIMARY_REPAIR_INDEX = Set(
        dimen=2,
        initialize=repair_indices,
        ordered=True,
    )
    model.primary_repair_positive_movement = Var(
        model.PRIMARY_REPAIR_INDEX,
        domain=NonNegativeReals,
    )
    model.primary_repair_negative_movement = Var(
        model.PRIMARY_REPAIR_INDEX,
        domain=NonNegativeReals,
    )
    model.primary_repair_balance = ConstraintList()
    for quarter_name, generator_index in repair_indices:
        model.primary_repair_balance.add(
            actual.generation[quarter_name, "base", generator_index]
            - repair_targets[quarter_name, generator_index]
            == model.primary_repair_positive_movement[
                quarter_name, generator_index
            ]
            - model.primary_repair_negative_movement[
                quarter_name, generator_index
            ]
        )
    model.primary_cost.deactivate()
    model.primary_repair_cost = Objective(
        expr=sum(
            model.primary_repair_positive_movement[index]
            + model.primary_repair_negative_movement[index]
            for index in repair_indices
        ),
        sense=minimize,
    )
    repair_solver = SolverFactory(solver_name)
    repair_results = repair_solver.solve(
        model,
        load_solutions=False,
        tee=tee,
    )
    repair_termination = repair_results.solver.termination_condition
    if not _is_optimal(repair_termination):
        return infeasible_result(
            termination_condition=repair_termination,
            solver_status=repair_results.solver.status,
            solver_message=repair_results.solver.message,
        )
    model.solutions.load_from(repair_results)
    repair_movements = {
        index: abs(
            float(value(actual.generation[index[0], "base", index[1]]))
            - repair_targets[index]
        )
        for index in repair_indices
    }
    repair_total_movement = sum(repair_movements.values())
    repair_max_movement = max(repair_movements.values(), default=0.0)
    qp_numerical_residual = max(
        primary_qp.max_constraint_violation or 0.0,
        primary_qp.max_bound_projection,
    )
    repair_movement_tolerance = max(1.0e-5, 10.0 * qp_numerical_residual)
    if repair_max_movement > repair_movement_tolerance:
        raise RuntimeError(
            "OSQP primary solution required excessive generation movement "
            "during L1 linear feasibility projection: "
            f"movement={repair_max_movement}, "
            f"tolerance={repair_movement_tolerance}"
        )
    primary_objective = float(value(model.primary_cost.expr))
    repair_deviation = primary_objective - osqp_primary_objective
    repair_tolerance = max(
        primary_objective_tolerance,
        1.0e-8 * max(abs(primary_objective), 1.0),
    )
    if abs(repair_deviation) > repair_tolerance:
        raise RuntimeError(
            "OSQP primary solution required excessive objective deviation "
            "during L1 linear feasibility projection: "
            f"deviation={repair_deviation}, tolerance={repair_tolerance}"
        )

    for name in (
        "primary_repair_cost",
        "primary_repair_balance",
        "primary_repair_negative_movement",
        "primary_repair_positive_movement",
        "PRIMARY_REPAIR_INDEX",
    ):
        model.del_component(name)
    for quarter in quarters:
        for generator in data.generators:
            if generator.in_service and generator.cost_quadratic > 0.0:
                base_generation = actual.generation[
                    quarter.name, "base", generator.index
                ]
                base_generation.fix(float(value(base_generation)))
    linear_primary_cost = linear_expression_after_fixing_quadratics(
        model.primary_cost.expr
    )
    if not isinstance(linear_primary_cost, Real):
        model.primary_cost_cap = Constraint(
            expr=(
                linear_primary_cost
                <= primary_objective + primary_objective_tolerance
            )
        )
    model.minimum_call = Objective(
        expr=sum(
            model.actual_grid_curtailment[quarter.name, state.name]
            + model.certified_grid_curtailment[quarter.name, state.name]
            for quarter in quarters
            for state in states
            if state.response_mode == "bounded"
        ),
        sense=minimize,
    )
    # Rebuild the persistent HiGHS interface so the primary QP Hessian is not
    # retained when the linear minimum-call stage is loaded.
    secondary_solver = SolverFactory(solver_name)
    secondary_results = secondary_solver.solve(
        model,
        load_solutions=False,
        tee=tee,
    )
    secondary_termination = secondary_results.solver.termination_condition
    if not _is_optimal(secondary_termination):
        return infeasible_result(
            termination_condition=secondary_termination,
            solver_status=secondary_results.solver.status,
            solver_message=secondary_results.solver.message,
            repair_deviation=repair_deviation,
            repair_deviation_tolerance=repair_tolerance,
            repair_total_movement=repair_total_movement,
            repair_max_movement=repair_max_movement,
            repair_movement_tolerance=repair_movement_tolerance,
        )
    model.solutions.load_from(secondary_results)
    solver_status = str(secondary_results.solver.status)
    solver_message = str(secondary_results.solver.message)

    actual_grid_curtailment = {
        quarter.name: {
            state.name: float(
                value(model.actual_grid_curtailment[quarter.name, state.name])
            )
            for state in states
        }
        for quarter in quarters
    }
    certified_grid_curtailment = {
        quarter.name: {
            state.name: float(
                value(model.certified_grid_curtailment[quarter.name, state.name])
            )
            for state in states
        }
        for quarter in quarters
    }
    actual_poi_load = {
        quarter.name: {
            state.name: float(value(model.actual_poi_load[quarter.name, state.name]))
            for state in states
        }
        for quarter in quarters
    }
    certified_poi_load = {
        quarter.name: {
            state.name: float(
                value(model.certified_poi_load[quarter.name, state.name])
            )
            for state in states
        }
        for quarter in quarters
    }
    firm_breach = {
        quarter.name: {
            state.name: float(value(model.firm_breach[quarter.name, state.name]))
            for state in states
        }
        for quarter in quarters
    }
    conditional_breach = {
        quarter.name: {
            state.name: float(
                value(model.conditional_breach[quarter.name, state.name])
            )
            for state in states
        }
        for quarter in quarters
    }
    actual_results = _extract_layer_results(
        block=actual,
        data=data,
        quarters=quarters,
        states=states,
        poi=poi,
        poi_load_mw=actual_poi_load,
        termination=secondary_termination,
        solver_status=solver_status,
        solver_message=solver_message,
    )
    certified_results = _extract_layer_results(
        block=certified,
        data=data,
        quarters=quarters,
        states=states,
        poi=poi,
        poi_load_mw=certified_poi_load,
        termination=secondary_termination,
        solver_status=solver_status,
        solver_message=solver_message,
    )
    effective_ratings = {}
    for quarter in quarters:
        quarter_ratings = {}
        for state in states:
            increases = _rating_increases(project, state.branch_rating)
            quarter_ratings[state.name] = {
                branch.index: branch.rating_mw(state.branch_rating)
                + increases.get(branch.index, 0.0) * commissioned[quarter.name]
                for branch in data.branches
            }
        effective_ratings[quarter.name] = quarter_ratings

    base_operating_cost_per_hour = {
        quarter.name: actual_results[quarter.name]["base"].objective
        for quarter in quarters
    }
    investment_cost = float(investment_cost_expression)
    operating_cost = sum(
        quarter.discount_factor
        * quarter.operating_hours
        * base_operating_cost_per_hour[quarter.name]
        for quarter in quarters
    )
    access_cost = sum(
        quarter.discount_factor
        * quarter.operating_hours
        * access_shortfall_cost_per_mwh
        * access_shortfall[quarter.name]
        for quarter in quarters
    )
    unused_mw_year = sum(
        quarter.operating_hours
        * max(total_capacity[quarter.name] - quarter.data_center_demand_mw, 0.0)
        / 8760.0
        for quarter in quarters
    )
    milestones = calculate_capacity_milestones(
        quarter_names=quarter_names,
        total_capacity_mw=total_capacity,
        model_validated_by_quarter={name: True for name in quarter_names},
        continuous_validation_hours={
            quarter.name: quarter.continuous_validation_hours
            for quarter in quarters
        },
        application_capacity_mw=poi.application_capacity_mw,
        minimum_operational_block_mw=(
            service_envelope.minimum_operational_block_mw
        ),
        minimum_validation_hours=service_envelope.minimum_validation_hours,
    )
    return DeterministicFxResult(
        feasible=True,
        termination_condition=str(secondary_termination),
        solver_status=solver_status,
        solver_message=solver_message,
        objective=investment_cost + operating_cost + access_cost,
        primary_optimization_objective=primary_objective,
        canonical_dispatch_primary_objective=float(value(model.primary_cost.expr)),
        primary_qp_solver="osqp",
        primary_qp_status=primary_qp.status,
        primary_qp_iterations=primary_qp.iterations,
        primary_qp_primal_residual=primary_qp.primal_residual,
        primary_qp_dual_residual=primary_qp.dual_residual,
        primary_qp_max_constraint_violation=primary_qp.max_constraint_violation,
        primary_qp_max_bound_projection=primary_qp.max_bound_projection,
        primary_qp_solve_seconds=primary_qp.solve_seconds,
        primary_linear_repair_objective_deviation=repair_deviation,
        primary_linear_repair_objective_deviation_tolerance=repair_tolerance,
        primary_linear_repair_total_generation_movement_mw=(
            repair_total_movement
        ),
        primary_linear_repair_max_generation_movement_mw=(
            repair_max_movement
        ),
        primary_linear_repair_generation_movement_tolerance_mw=(
            repair_movement_tolerance
        ),
        primary_linear_repair_acceptance_interpretation=(
            "numerical_feasibility_projection_envelopes_not_"
            "optimality_gap_or_error_certificate"
        ),
        investment_cost=investment_cost,
        operating_cost=operating_cost,
        access_shortfall_cost=access_cost,
        minimum_call_certificate_mw_sum=float(value(model.minimum_call)),
        actual_grid_curtailment_mw=actual_grid_curtailment,
        actual_poi_load_mw=actual_poi_load,
        certified_grid_curtailment_mw=certified_grid_curtailment,
        certified_poi_load_mw=certified_poi_load,
        firm_breach_mw=firm_breach,
        conditional_breach_mw=conditional_breach,
        actual_state_results=actual_results,
        certified_state_results=certified_results,
        effective_branch_ratings_mw=effective_ratings,
        base_operating_cost_per_hour=base_operating_cost_per_hour,
        unused_capacity_mw_year=unused_mw_year,
        milestones=milestones,
        **common_result,
    )
