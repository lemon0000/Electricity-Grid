"""Preventive-corrective security-constrained DC optimal power flow."""

from __future__ import annotations

from dataclasses import dataclass
from math import radians
from typing import Iterable, Mapping

from pyomo.environ import (
    Binary,
    ConcreteModel,
    Constraint,
    ConstraintList,
    Objective,
    Set,
    SolverFactory,
    Var,
    minimize,
    value,
)
from pyomo.opt import TerminationCondition

from .dc_opf import DcOpfResult
from .rts24 import Rts24Data


@dataclass(frozen=True)
class SecurityState:
    name: str
    kind: str
    element_index: int | None
    branch_rating: str
    outaged_branch_indices: frozenset[int]
    outaged_generator_indices: frozenset[int]
    response_mode: str


@dataclass(frozen=True)
class SecurityConstrainedResult:
    feasible: bool
    termination_condition: str
    solver_status: str
    solver_message: str
    objective: float | None
    base_result: DcOpfResult | None
    state_results: dict[str, DcOpfResult]
    states: tuple[SecurityState, ...]
    excluded_branch_indices: tuple[int, ...]
    cost_breakpoints: int
    commitment_model: str
    generator_commitment: dict[int, bool] | None


def _component_count(data: Rts24Data, outaged_branch_index: int) -> int:
    adjacency = {bus.index: set() for bus in data.buses}
    for branch in data.branches:
        if not branch.in_service or branch.index == outaged_branch_index:
            continue
        adjacency[branch.from_bus].add(branch.to_bus)
        adjacency[branch.to_bus].add(branch.from_bus)

    unseen = set(adjacency)
    count = 0
    while unseen:
        count += 1
        stack = [min(unseen)]
        component = set()
        while stack:
            bus = stack.pop()
            if bus in component:
                continue
            component.add(bus)
            stack.extend(adjacency[bus] - component)
        unseen -= component
    return count


def non_islanding_branch_indices(data: Rts24Data) -> tuple[int, ...]:
    """Return active branches whose individual outage keeps the grid connected."""

    return tuple(
        branch.index
        for branch in data.branches
        if branch.in_service and _component_count(data, branch.index) == 1
    )


def build_security_states(
    branch_indices: tuple[int, ...],
    generator_indices: tuple[int, ...],
    immediate_rating: str,
    sustained_rating: str,
) -> tuple[SecurityState, ...]:
    states = [
        SecurityState(
            name="base",
            kind="base",
            element_index=None,
            branch_rating="rate_a",
            outaged_branch_indices=frozenset(),
            outaged_generator_indices=frozenset(),
            response_mode="base",
        )
    ]
    for index in branch_indices:
        states.extend(
            (
                SecurityState(
                    name=f"branch_{index}_immediate",
                    kind="branch",
                    element_index=index,
                    branch_rating=immediate_rating,
                    outaged_branch_indices=frozenset((index,)),
                    outaged_generator_indices=frozenset(),
                    response_mode="fixed",
                ),
                SecurityState(
                    name=f"branch_{index}_sustained",
                    kind="branch",
                    element_index=index,
                    branch_rating=sustained_rating,
                    outaged_branch_indices=frozenset((index,)),
                    outaged_generator_indices=frozenset(),
                    response_mode="bounded",
                ),
            )
        )
    for index in generator_indices:
        states.append(
            SecurityState(
                name=f"generator_{index}_sustained",
                kind="generator",
                element_index=index,
                branch_rating=sustained_rating,
                outaged_branch_indices=frozenset(),
                outaged_generator_indices=frozenset((index,)),
                response_mode="bounded",
            )
        )
    return tuple(states)


def solve_security_constrained_dc_opf(
    data: Rts24Data,
    *,
    redispatch_up_mw: Mapping[int, float],
    redispatch_down_mw: Mapping[int, float],
    branch_indices: Iterable[int] | None = None,
    generator_indices: Iterable[int] | None = None,
    immediate_rating: str = "rate_c",
    sustained_rating: str = "rate_a",
    cost_breakpoints: int = 65,
    optimize_unit_selection: bool = False,
    solver_name: str = "highs",
    tee: bool = False,
) -> SecurityConstrainedResult:
    """Jointly optimize one base dispatch and all selected corrective states.

    Optional unit selection is shared by every state in this single snapshot.
    It does not model startup trajectories or intertemporal commitment limits.
    """

    branch_by_index = {branch.index: branch for branch in data.branches}
    generator_by_index = {generator.index: generator for generator in data.generators}
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
    if set(selected_branches) - branch_by_index.keys():
        raise ValueError("SCOPF branch set contains an unknown index")
    if set(selected_generators) - generator_by_index.keys():
        raise ValueError("SCOPF generator set contains an unknown index")
    islanding = [
        index for index in selected_branches if _component_count(data, index) != 1
    ]
    if islanding:
        raise ValueError(
            f"SCOPF main set cannot contain islanding branches: {islanding}"
        )

    generator_indices_all = tuple(generator_by_index)
    expected_generators = set(generator_indices_all)
    for name, limits in (
        ("up redispatch", redispatch_up_mw),
        ("down redispatch", redispatch_down_mw),
    ):
        if set(limits) != expected_generators:
            raise ValueError(f"{name} must contain every generator index")
        if any(limit < 0.0 for limit in limits.values()):
            raise ValueError(f"{name} limits must be nonnegative")
    for branch in data.branches:
        branch.rating_mw(immediate_rating)
        branch.rating_mw(sustained_rating)
    if cost_breakpoints < 2:
        raise ValueError("At least two cost breakpoints are required")
    commitment_model = (
        "single_snapshot_static_unit_selection"
        if optimize_unit_selection
        else "fixed_online"
    )

    states = build_security_states(
        selected_branches,
        selected_generators,
        immediate_rating,
        sustained_rating,
    )
    excluded_branches = tuple(
        branch.index
        for branch in data.branches
        if branch.in_service and branch.index not in selected_branches
    )
    state_by_name = {state.name: state for state in states}
    state_names = tuple(state_by_name)
    bus_indices = tuple(bus.index for bus in data.buses)
    branch_indices_all = tuple(branch_by_index)
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
    model.STATE = Set(initialize=state_names, ordered=True)
    model.BUS = Set(initialize=bus_indices, ordered=True)
    model.GEN = Set(initialize=generator_indices_all, ordered=True)
    model.BRANCH = Set(initialize=branch_indices_all, ordered=True)

    def generation_bounds(
        _model: ConcreteModel,
        state_name: str,
        generator_index: int,
    ) -> tuple[float, float]:
        state = state_by_name[state_name]
        generator = generator_by_index[generator_index]
        if (
            not generator.in_service
            or generator_index in state.outaged_generator_indices
        ):
            return 0.0, 0.0
        if optimize_unit_selection:
            return 0.0, generator.p_max_mw
        return generator.p_min_mw, generator.p_max_mw

    def flow_bounds(
        _model: ConcreteModel,
        state_name: str,
        branch_index: int,
    ) -> tuple[float, float]:
        state = state_by_name[state_name]
        rating = branch_by_index[branch_index].rating_mw(state.branch_rating)
        return -rating, rating

    model.generation = Var(model.STATE, model.GEN, bounds=generation_bounds)
    if optimize_unit_selection:
        model.commitment = Var(model.GEN, domain=Binary)
        for generator in data.generators:
            if not generator.in_service or generator.p_max_mw <= 0.0:
                model.commitment[generator.index].fix(0)
        model.commitment_generation = ConstraintList()
        for state in states:
            for generator in data.generators:
                if (
                    not generator.in_service
                    or generator.index in state.outaged_generator_indices
                ):
                    continue
                model.commitment_generation.add(
                    model.generation[state.name, generator.index]
                    >= generator.p_min_mw * model.commitment[generator.index]
                )
                model.commitment_generation.add(
                    model.generation[state.name, generator.index]
                    <= generator.p_max_mw * model.commitment[generator.index]
                )
    # Degrees keep the network matrix scaled; extracted results use radians.
    model.angle = Var(model.STATE, model.BUS)
    model.flow = Var(model.STATE, model.BRANCH, bounds=flow_bounds)

    def branch_flow_rule(
        model: ConcreteModel,
        state_name: str,
        branch_index: int,
    ) -> object:
        state = state_by_name[state_name]
        branch = branch_by_index[branch_index]
        if (
            not branch.in_service
            or branch_index in state.outaged_branch_indices
        ):
            return model.flow[state_name, branch_index] == 0.0
        susceptance_mw_per_rad = (
            data.base_mva / (branch.reactance_pu * branch.tap_ratio)
        )
        return model.flow[state_name, branch_index] == susceptance_mw_per_rad * (
            radians(1.0)
            * (
                model.angle[state_name, branch.from_bus]
                - model.angle[state_name, branch.to_bus]
            )
            - branch.phase_shift_rad
        )

    model.branch_flow = Constraint(
        model.STATE,
        model.BRANCH,
        rule=branch_flow_rule,
    )

    def balance_rule(
        model: ConcreteModel,
        state_name: str,
        bus: int,
    ) -> object:
        generation = sum(
            model.generation[state_name, index]
            for index in generators_at_bus[bus]
        )
        outgoing = sum(
            model.flow[state_name, index] for index in outgoing_at_bus[bus]
        )
        incoming = sum(
            model.flow[state_name, index] for index in incoming_at_bus[bus]
        )
        return generation - bus_by_index[bus].demand_mw == outgoing - incoming

    model.power_balance = Constraint(model.STATE, model.BUS, rule=balance_rule)
    for state_name in state_names:
        model.angle[state_name, data.reference_bus].fix(0.0)

    model.response = ConstraintList()
    for state in states:
        if state.response_mode == "base":
            continue
        for generator_index in generator_indices_all:
            if generator_index in state.outaged_generator_indices:
                continue
            contingency_generation = model.generation[state.name, generator_index]
            base_generation = model.generation["base", generator_index]
            if state.response_mode == "fixed":
                model.response.add(contingency_generation == base_generation)
            else:
                up_limit = redispatch_up_mw[generator_index]
                down_limit = redispatch_down_mw[generator_index]
                if optimize_unit_selection:
                    up_limit *= model.commitment[generator_index]
                    down_limit *= model.commitment[generator_index]
                model.response.add(
                    contingency_generation - base_generation
                    <= up_limit
                )
                model.response.add(
                    base_generation - contingency_generation
                    <= down_limit
                )
                if optimize_unit_selection and state.kind == "generator":
                    outage_commitment = model.commitment[state.element_index]
                    model.response.add(
                        contingency_generation - base_generation
                        <= redispatch_up_mw[generator_index]
                        * outage_commitment
                    )
                    model.response.add(
                        base_generation - contingency_generation
                        <= redispatch_down_mw[generator_index]
                        * outage_commitment
                    )

    model.generation_cost = Var(model.GEN)
    model.cost_envelope = ConstraintList()
    for generator in data.generators:
        if not generator.in_service:
            model.generation_cost[generator.index].fix(0.0)
            continue
        span = generator.p_max_mw - generator.p_min_mw
        points = (
            (generator.p_min_mw,)
            if generator.cost_quadratic == 0.0 or span == 0.0
            else tuple(
                generator.p_min_mw + span * step / (cost_breakpoints - 1)
                for step in range(cost_breakpoints)
            )
        )
        for point in points:
            slope = 2.0 * generator.cost_quadratic * point + generator.cost_linear
            intercept = (
                generator.cost_constant
                - generator.cost_quadratic * point**2
            )
            commitment = (
                model.commitment[generator.index]
                if optimize_unit_selection
                else 1.0
            )
            model.cost_envelope.add(
                model.generation_cost[generator.index]
                >= slope * model.generation["base", generator.index]
                + intercept * commitment
            )
    model.total_cost = Objective(
        expr=sum(
            model.generation_cost[generator.index]
            for generator in data.generators
            if generator.in_service
        ),
        sense=minimize,
    )

    solver = SolverFactory(solver_name)
    if not solver.available(exception_flag=False):
        raise RuntimeError(f"Solver '{solver_name}' is not available")
    solver_results = solver.solve(model, load_solutions=False, tee=tee)
    termination = solver_results.solver.termination_condition
    is_optimal = termination in {
        TerminationCondition.optimal,
        TerminationCondition.globallyOptimal,
        TerminationCondition.locallyOptimal,
    }
    if not is_optimal:
        return SecurityConstrainedResult(
            feasible=False,
            termination_condition=str(termination),
            solver_status=str(solver_results.solver.status),
            solver_message=str(solver_results.solver.message),
            objective=None,
            base_result=None,
            state_results={},
            states=states,
            excluded_branch_indices=excluded_branches,
            cost_breakpoints=cost_breakpoints,
            commitment_model=commitment_model,
            generator_commitment=None,
        )

    model.solutions.load_from(solver_results)
    generator_commitment = {
        generator.index: (
            bool(round(float(value(model.commitment[generator.index]))))
            if optimize_unit_selection
            else generator.in_service and generator.p_max_mw > 0.0
        )
        for generator in data.generators
    }
    results = {}
    for state in states:
        generation = {
            index: float(value(model.generation[state.name, index]))
            for index in generator_indices_all
        }
        angles = {
            index: radians(float(value(model.angle[state.name, index])))
            for index in bus_indices
        }
        flows = {
            index: float(value(model.flow[state.name, index]))
            for index in branch_indices_all
        }
        residuals = {}
        for bus in bus_indices:
            bus_generation = sum(
                generation[index] for index in generators_at_bus[bus]
            )
            outgoing = sum(flows[index] for index in outgoing_at_bus[bus])
            incoming = sum(flows[index] for index in incoming_at_bus[bus])
            residuals[bus] = (
                bus_generation - bus_by_index[bus].demand_mw - outgoing + incoming
            )
        state_cost = sum(
            generator.cost_quadratic * generation[generator.index] ** 2
            + generator.cost_linear * generation[generator.index]
            + generator.cost_constant
            for generator in data.generators
            if generator_commitment[generator.index]
            and generator.index not in state.outaged_generator_indices
        )
        results[state.name] = DcOpfResult(
            feasible=True,
            termination_condition=str(termination),
            solver_status=str(solver_results.solver.status),
            solver_message=str(solver_results.solver.message),
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

    return SecurityConstrainedResult(
        feasible=True,
        termination_condition=str(termination),
        solver_status=str(solver_results.solver.status),
        solver_message=str(solver_results.solver.message),
        objective=results["base"].objective,
        base_result=results["base"],
        state_results=results,
        states=states,
        excluded_branch_indices=excluded_branches,
        cost_breakpoints=cost_breakpoints,
        commitment_model=commitment_model,
        generator_commitment=generator_commitment,
    )
