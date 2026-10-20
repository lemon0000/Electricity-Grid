"""Quadratic DC optimal power flow solved with Pyomo."""

from __future__ import annotations

from dataclasses import dataclass
from math import radians
from typing import Iterable, Mapping

from pyomo.environ import (
    ConcreteModel,
    Constraint,
    Expression,
    Objective,
    Set,
    SolverFactory,
    Var,
    minimize,
    value,
)
from pyomo.opt import TerminationCondition

from .rts24 import Rts24Data


@dataclass(frozen=True)
class DcOpfResult:
    feasible: bool
    termination_condition: str
    solver_status: str
    solver_message: str
    objective: float | None
    generation_mw: dict[int, float]
    bus_angles_rad: dict[int, float]
    branch_flows_mw: dict[int, float]
    power_balance_residuals_mw: dict[int, float]
    reference_buses: tuple[int, ...]
    outaged_branch_indices: frozenset[int]
    outaged_generator_indices: frozenset[int]
    branch_rating: str

    @property
    def max_balance_residual_mw(self) -> float | None:
        if not self.feasible:
            return None
        return max(abs(value) for value in self.power_balance_residuals_mw.values())


def _connected_components(
    data: Rts24Data,
    outaged_branch_indices: frozenset[int],
) -> tuple[tuple[int, ...], ...]:
    adjacency = {bus.index: set() for bus in data.buses}
    for branch in data.branches:
        if not branch.in_service or branch.index in outaged_branch_indices:
            continue
        adjacency[branch.from_bus].add(branch.to_bus)
        adjacency[branch.to_bus].add(branch.from_bus)

    unseen = set(adjacency)
    components = []
    while unseen:
        start = min(unseen)
        stack = [start]
        component = set()
        while stack:
            bus = stack.pop()
            if bus in component:
                continue
            component.add(bus)
            stack.extend(adjacency[bus] - component)
        unseen -= component
        components.append(tuple(sorted(component)))
    return tuple(components)


def _reference_buses(
    data: Rts24Data,
    components: tuple[tuple[int, ...], ...],
) -> tuple[int, ...]:
    references = []
    for component in components:
        if data.reference_bus in component:
            references.append(data.reference_bus)
        else:
            references.append(component[0])
    return tuple(references)


def solve_dc_opf(
    data: Rts24Data,
    *,
    outaged_branch_indices: Iterable[int] = (),
    outaged_generator_indices: Iterable[int] = (),
    branch_rating: str = "rate_a",
    reference_generation_mw: Mapping[int, float] | None = None,
    redispatch_up_mw: Mapping[int, float] | None = None,
    redispatch_down_mw: Mapping[int, float] | None = None,
    allow_islanding: bool = False,
    solver_name: str = "highs",
    tee: bool = False,
) -> DcOpfResult:
    """Solve one DC-OPF state without load-shedding variables.

    When a reference dispatch is supplied, both redispatch mappings are
    required and bound every available generator relative to that dispatch.
    """

    branch_outages = frozenset(int(index) for index in outaged_branch_indices)
    generator_outages = frozenset(int(index) for index in outaged_generator_indices)
    branch_by_index = {branch.index: branch for branch in data.branches}
    generator_by_index = {generator.index: generator for generator in data.generators}
    unknown_branches = branch_outages - branch_by_index.keys()
    unknown_generators = generator_outages - generator_by_index.keys()
    if unknown_branches:
        raise ValueError(f"Unknown branch indices: {sorted(unknown_branches)}")
    if unknown_generators:
        raise ValueError(f"Unknown generator indices: {sorted(unknown_generators)}")
    for branch in data.branches:
        branch.rating_mw(branch_rating)

    components = _connected_components(data, branch_outages)
    reference_buses = _reference_buses(data, components)
    bus_indices = tuple(bus.index for bus in data.buses)
    generator_indices = tuple(generator.index for generator in data.generators)
    branch_indices = tuple(branch.index for branch in data.branches)
    bus_by_index = {bus.index: bus for bus in data.buses}

    if not allow_islanding and len(components) > 1:
        return DcOpfResult(
            feasible=False,
            termination_condition="islanding",
            solver_status="not_run",
            solver_message="Unplanned islanding is rejected by policy",
            objective=None,
            generation_mw={},
            bus_angles_rad={},
            branch_flows_mw={},
            power_balance_residuals_mw={},
            reference_buses=reference_buses,
            outaged_branch_indices=branch_outages,
            outaged_generator_indices=generator_outages,
            branch_rating=branch_rating,
        )

    expected_generators = set(generator_indices)
    if reference_generation_mw is None:
        if redispatch_up_mw is not None or redispatch_down_mw is not None:
            raise ValueError("Redispatch limits require a reference dispatch")
    else:
        if redispatch_up_mw is None or redispatch_down_mw is None:
            raise ValueError("A reference dispatch requires up and down limits")
        for name, values in (
            ("reference dispatch", reference_generation_mw),
            ("up redispatch", redispatch_up_mw),
            ("down redispatch", redispatch_down_mw),
        ):
            if set(values) != expected_generators:
                raise ValueError(f"{name} must contain every generator index")
        if any(value < 0 for value in redispatch_up_mw.values()) or any(
            value < 0 for value in redispatch_down_mw.values()
        ):
            raise ValueError("Redispatch limits must be nonnegative")

    generators_at_bus = {bus: [] for bus in bus_indices}
    outgoing_at_bus = {bus: [] for bus in bus_indices}
    incoming_at_bus = {bus: [] for bus in bus_indices}
    for generator in data.generators:
        generators_at_bus[generator.bus].append(generator.index)
    for branch in data.branches:
        outgoing_at_bus[branch.from_bus].append(branch.index)
        incoming_at_bus[branch.to_bus].append(branch.index)

    model = ConcreteModel()
    model.BUS = Set(initialize=bus_indices, ordered=True)
    model.GEN = Set(initialize=generator_indices, ordered=True)
    model.BRANCH = Set(initialize=branch_indices, ordered=True)

    def generation_bounds(_model: ConcreteModel, index: int) -> tuple[float, float]:
        generator = generator_by_index[index]
        if not generator.in_service or index in generator_outages:
            return 0.0, 0.0
        lower = generator.p_min_mw
        upper = generator.p_max_mw
        if reference_generation_mw is not None:
            lower = max(
                lower,
                reference_generation_mw[index] - redispatch_down_mw[index],
            )
            upper = min(
                upper,
                reference_generation_mw[index] + redispatch_up_mw[index],
            )
        if lower > upper + 1.0e-9:
            raise ValueError(f"Redispatch bounds are inconsistent for generator {index}")
        return lower, upper

    def flow_bounds(_model: ConcreteModel, index: int) -> tuple[float, float]:
        rating = branch_by_index[index].rating_mw(branch_rating)
        return -rating, rating

    model.generation = Var(model.GEN, bounds=generation_bounds)
    # Degrees keep DC-flow matrix coefficients well scaled; results use radians.
    model.angle = Var(model.BUS)
    model.flow = Var(model.BRANCH, bounds=flow_bounds)

    def branch_flow_rule(model: ConcreteModel, index: int) -> object:
        branch = branch_by_index[index]
        if not branch.in_service or index in branch_outages:
            return model.flow[index] == 0.0
        susceptance_mw_per_rad = (
            data.base_mva / (branch.reactance_pu * branch.tap_ratio)
        )
        return model.flow[index] == susceptance_mw_per_rad * (
            radians(1.0)
            * (model.angle[branch.from_bus] - model.angle[branch.to_bus])
            - branch.phase_shift_rad
        )

    model.branch_flow = Constraint(model.BRANCH, rule=branch_flow_rule)

    def balance_rule(model: ConcreteModel, bus: int) -> object:
        generation = sum(model.generation[index] for index in generators_at_bus[bus])
        outgoing = sum(model.flow[index] for index in outgoing_at_bus[bus])
        incoming = sum(model.flow[index] for index in incoming_at_bus[bus])
        return generation - bus_by_index[bus].demand_mw == outgoing - incoming

    model.power_balance = Constraint(model.BUS, rule=balance_rule)
    for bus in reference_buses:
        model.angle[bus].fix(0.0)

    model.operating_cost = Expression(
        expr=sum(
            generator.cost_quadratic * model.generation[generator.index] ** 2
            + generator.cost_linear * model.generation[generator.index]
            + generator.cost_constant
            for generator in data.generators
            if generator.in_service and generator.index not in generator_outages
        )
    )
    # HiGHS' active-set QP solver needs a unique tie-break among identical
    # linear-cost units. This term is excluded from the reported cost.
    model.total_cost = Objective(
        expr=model.operating_cost
        + 1.0e-8
        * sum(
            model.generation[generator.index] ** 2
            for generator in data.generators
            if generator.in_service and generator.index not in generator_outages
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
        return DcOpfResult(
            feasible=False,
            termination_condition=str(termination),
            solver_status=str(solver_results.solver.status),
            solver_message=str(solver_results.solver.message),
            objective=None,
            generation_mw={},
            bus_angles_rad={},
            branch_flows_mw={},
            power_balance_residuals_mw={},
            reference_buses=reference_buses,
            outaged_branch_indices=branch_outages,
            outaged_generator_indices=generator_outages,
            branch_rating=branch_rating,
        )

    model.solutions.load_from(solver_results)
    generation_mw = {
        index: float(value(model.generation[index])) for index in generator_indices
    }
    bus_angles_rad = {
        index: radians(float(value(model.angle[index]))) for index in bus_indices
    }
    branch_flows_mw = {
        index: float(value(model.flow[index])) for index in branch_indices
    }

    residuals = {}
    for bus in bus_indices:
        generation = sum(generation_mw[index] for index in generators_at_bus[bus])
        outgoing = sum(branch_flows_mw[index] for index in outgoing_at_bus[bus])
        incoming = sum(branch_flows_mw[index] for index in incoming_at_bus[bus])
        residuals[bus] = generation - bus_by_index[bus].demand_mw - outgoing + incoming

    return DcOpfResult(
        feasible=True,
        termination_condition=str(termination),
        solver_status=str(solver_results.solver.status),
        solver_message=str(solver_results.solver.message),
        objective=float(value(model.operating_cost)),
        generation_mw=generation_mw,
        bus_angles_rad=bus_angles_rad,
        branch_flows_mw=branch_flows_mw,
        power_balance_residuals_mw=residuals,
        reference_buses=reference_buses,
        outaged_branch_indices=branch_outages,
        outaged_generator_indices=generator_outages,
        branch_rating=branch_rating,
    )
