"""Deterministic quarterly interconnection and existing-branch uprating MVP."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, radians
from time import perf_counter
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
    minimize,
    value,
)
from pyomo.opt import TerminationCondition

from ..grid.dc_opf import DcOpfResult
from ..grid.rts24 import Rts24Data
from ..grid.scopf import (
    SecurityState,
    build_security_states,
    non_islanding_branch_indices,
)
from ..solvers import (
    OsqpQpWorkspace,
    linear_expression_after_fixing_quadratics,
)


@dataclass(frozen=True)
class PlanningQuarter:
    name: str
    system_load_multiplier: float
    data_center_demand_mw: float
    operating_hours: float
    discount_factor: float


@dataclass(frozen=True)
class FixedPoi:
    bus: int
    initial_capacity_mw: float
    application_capacity_mw: float


@dataclass(frozen=True)
class ExistingBranchUpgrade:
    """One bundled project with a common start, lead time, and total cost."""

    name: str
    lead_time_quarters: int
    rate_a_increase_mw: Mapping[int, float]
    rate_c_increase_mw: Mapping[int, float]
    poi_capacity_increase_mw: float
    investment_cost: float
    parameter_status: str


@dataclass(frozen=True)
class DeterministicExpansionResult:
    feasible: bool
    termination_condition: str
    solver_status: str
    solver_message: str
    objective: float | None
    optimization_objective: float | None
    investment_cost: float | None
    operating_cost: float | None
    access_shortfall_cost: float | None
    project_started: bool | None
    start_quarter: str | None
    commissioned_by_quarter: dict[str, bool]
    connected_capacity_mw: dict[str, float]
    access_shortfall_mw: dict[str, float]
    base_operating_cost_per_hour: dict[str, float]
    state_results: dict[str, dict[str, DcOpfResult]]
    effective_branch_ratings_mw: dict[str, dict[str, dict[int, float]]]
    states: tuple[SecurityState, ...]
    excluded_branch_indices: tuple[int, ...]
    candidate_diagnostics: tuple[dict[str, object], ...]
    enumeration_method: str
    project_parameter_status: str
    capacity_interpretation: str


_M2_CAPACITY_INTERPRETATION = (
    "firm_connected_and_operating_demand_capped_by_quarter_request"
)


def _validate_nonnegative_finite(name: str, number: float) -> None:
    if not isfinite(number) or number < 0.0:
        raise ValueError(f"{name} must be finite and nonnegative")


def _is_accepted_linear_termination(termination: object) -> bool:
    return termination in {
        TerminationCondition.optimal,
        TerminationCondition.globallyOptimal,
        TerminationCondition.locallyOptimal,
    }


def _maximum_model_violation(model: ConcreteModel) -> float:
    maximum = 0.0
    for constraint in model.component_data_objects(
        Constraint,
        active=True,
        descend_into=True,
    ):
        body = float(value(constraint.body))
        if constraint.lower is not None:
            maximum = max(maximum, float(value(constraint.lower)) - body)
        if constraint.upper is not None:
            maximum = max(maximum, body - float(value(constraint.upper)))
    for variable in model.component_data_objects(
        Var,
        active=True,
        descend_into=True,
    ):
        variable_value = float(value(variable))
        if variable.lb is not None:
            maximum = max(maximum, float(value(variable.lb)) - variable_value)
        if variable.ub is not None:
            maximum = max(maximum, variable_value - float(value(variable.ub)))
    return max(maximum, 0.0)


def _run_linear_repair(
    model: ConcreteModel,
    *,
    quarters: tuple[PlanningQuarter, ...],
    data: Rts24Data,
    qp_objective_value: float,
    qp_hessian_nonzeros: int,
    qp_objective_scale: float,
    qp_feasibility_tolerance: float,
    solver_name: str,
    tee: bool,
) -> dict[str, object]:
    fixed_quadratic_generation = []
    try:
        for quarter in quarters:
            for generator in data.generators:
                if generator.in_service and generator.cost_quadratic > 0.0:
                    base_generation = model.generation[
                        quarter.name, "base", generator.index
                    ]
                    base_generation.fix(float(value(base_generation)))
                    fixed_quadratic_generation.append(base_generation)
        linear_cost = linear_expression_after_fixing_quadratics(
            model.total_cost.expr
        )
        model.total_cost.deactivate()
        model.candidate_linear_repair = Objective(
            expr=linear_cost,
            sense=minimize,
        )
        repair_solver = SolverFactory(solver_name)
        repair_started = perf_counter()
        repair_results = repair_solver.solve(
            model,
            load_solutions=False,
            tee=tee,
        )
        repair_seconds = perf_counter() - repair_started
        repair_termination = repair_results.solver.termination_condition
        audit: dict[str, object] = {
            "solver_status": str(repair_results.solver.status),
            "solver_message": str(repair_results.solver.message),
            "termination_condition": str(repair_termination),
            "termination_accepted": _is_accepted_linear_termination(
                repair_termination
            ),
            "solve_seconds": repair_seconds,
            "max_constraint_violation": None,
            "objective": None,
            "objective_deviation": None,
            "objective_deviation_applicable": qp_hessian_nonzeros > 0,
            "objective_deviation_assessment": None,
            "objective_deviation_absolute_threshold": None,
            "objective_deviation_relative_threshold": None,
            "objective_deviation_scaled_numerical_repair_envelope": None,
            "objective_deviation_threshold": None,
            "objective_deviation_passed": None,
            "objective_deviation_threshold_interpretation": (
                "numerical_acceptance_envelope_not_optimality_gap_or_"
                "error_certificate"
            ),
        }
        if not bool(audit["termination_accepted"]):
            return audit

        model.solutions.load_from(repair_results)
        repair_violation = _maximum_model_violation(model)
        repaired_objective = float(value(model.total_cost.expr))
        repair_deviation = repaired_objective - qp_objective_value
        repair_deviation_applicable = qp_hessian_nonzeros > 0
        if repair_deviation_applicable:
            absolute_threshold = 1.0e-6
            relative_threshold = 1.0e-8 * max(
                abs(qp_objective_value),
                abs(repaired_objective),
                1.0,
            )
            # This is a numerical repair acceptance envelope, not an
            # optimality-gap or error certificate.
            scaled_numerical_repair_envelope = (
                2.0 * qp_objective_scale * qp_feasibility_tolerance
            )
            repair_deviation_threshold = max(
                absolute_threshold,
                relative_threshold,
                scaled_numerical_repair_envelope,
            )
            repair_deviation_passed = (
                abs(repair_deviation) <= repair_deviation_threshold
            )
            if abs(repair_deviation) <= max(
                absolute_threshold,
                relative_threshold,
            ):
                repair_deviation_assessment = (
                    "within_absolute_or_relative_threshold"
                )
            elif (
                abs(repair_deviation)
                <= scaled_numerical_repair_envelope
            ):
                repair_deviation_assessment = (
                    "within_scaled_numerical_repair_envelope"
                )
            else:
                repair_deviation_assessment = "exceeds_threshold"
        else:
            absolute_threshold = None
            relative_threshold = None
            scaled_numerical_repair_envelope = None
            repair_deviation_threshold = None
            repair_deviation_passed = True
            repair_deviation_assessment = (
                "not_applicable_original_problem_is_linear"
            )
        audit.update(
            {
                "max_constraint_violation": repair_violation,
                "objective": repaired_objective,
                "objective_deviation": repair_deviation,
                "objective_deviation_assessment": (
                    repair_deviation_assessment
                ),
                "objective_deviation_absolute_threshold": (
                    absolute_threshold
                ),
                "objective_deviation_relative_threshold": (
                    relative_threshold
                ),
                "objective_deviation_scaled_numerical_repair_envelope": (
                    scaled_numerical_repair_envelope
                ),
                "objective_deviation_threshold": repair_deviation_threshold,
                "objective_deviation_passed": repair_deviation_passed,
            }
        )
        return audit
    finally:
        if model.component("candidate_linear_repair") is not None:
            model.del_component(model.candidate_linear_repair)
        model.total_cost.activate()
        for variable in fixed_quadratic_generation:
            variable.unfix()


def _rating_increases(
    project: ExistingBranchUpgrade,
    rating: str,
) -> Mapping[int, float]:
    if rating == "rate_a":
        return project.rate_a_increase_mw
    if rating == "rate_c":
        return project.rate_c_increase_mw
    raise ValueError(
        "The deterministic expansion MVP supports only rate_a and rate_c"
    )


def solve_deterministic_expansion(
    data: Rts24Data,
    *,
    quarters: Iterable[PlanningQuarter],
    poi: FixedPoi,
    project: ExistingBranchUpgrade,
    redispatch_up_mw: Mapping[int, float],
    redispatch_down_mw: Mapping[int, float],
    access_shortfall_cost_per_mwh: float,
    branch_indices: Iterable[int] | None = None,
    generator_indices: Iterable[int] | None = None,
    immediate_rating: str = "rate_c",
    sustained_rating: str = "rate_a",
    solver_name: str = "highs",
    tee: bool = False,
) -> DeterministicExpansionResult:
    """Jointly choose one branch uprating and firm POI capacity by quarter.

    Native system load has no shedding variable. In this M2 reduction,
    connected capacity is capped by quarterly requested demand and dispatched
    as firm load in every selected security state. It is not a separate unused
    contract-right variable. The only access slack is requested demand that has
    not yet been connected.
    """

    quarters = tuple(quarters)
    if not quarters:
        raise ValueError("At least one planning quarter is required")
    quarter_names = tuple(quarter.name for quarter in quarters)
    if any(not name for name in quarter_names) or len(set(quarter_names)) != len(
        quarter_names
    ):
        raise ValueError("Planning quarter names must be nonempty and unique")
    previous_demand = -1.0
    for quarter in quarters:
        _validate_nonnegative_finite(
            "System load multiplier", quarter.system_load_multiplier
        )
        _validate_nonnegative_finite(
            "Data-center demand", quarter.data_center_demand_mw
        )
        if quarter.data_center_demand_mw < previous_demand - 1.0e-9:
            raise ValueError("Data-center demand must be nondecreasing")
        previous_demand = quarter.data_center_demand_mw
        if not isfinite(quarter.operating_hours) or quarter.operating_hours <= 0.0:
            raise ValueError("Quarter operating hours must be finite and positive")
        if not isfinite(quarter.discount_factor) or quarter.discount_factor <= 0.0:
            raise ValueError("Quarter discount factors must be finite and positive")

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
        isinstance(project.lead_time_quarters, bool)
        or not isinstance(project.lead_time_quarters, int)
        or project.lead_time_quarters < 0
    ):
        raise ValueError("Project lead time must be a nonnegative integer")
    if not project.name:
        raise ValueError("Project name must be nonempty")
    if not project.parameter_status:
        raise ValueError("Project parameter status must be explicit")
    _validate_nonnegative_finite(
        "POI capacity increase", project.poi_capacity_increase_mw
    )
    _validate_nonnegative_finite("Investment cost", project.investment_cost)
    _validate_nonnegative_finite(
        "Access shortfall cost", access_shortfall_cost_per_mwh
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
    unknown_upgrade_branches = upgrade_branch_indices - branch_by_index.keys()
    if unknown_upgrade_branches:
        raise ValueError(
            f"Project contains unknown branch indices: {sorted(unknown_upgrade_branches)}"
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
    non_islanding = set(non_islanding_branch_indices(data))
    islanding = sorted(set(selected_branches) - non_islanding)
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
            raise ValueError("Candidate QPs require finite generator costs")
        if generator.cost_quadratic < 0.0:
            raise ValueError("Candidate QPs require convex generator costs")

    states = build_security_states(
        selected_branches,
        selected_generators,
        immediate_rating,
        sustained_rating,
    )
    state_by_name = {state.name: state for state in states}
    state_names = tuple(state_by_name)
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
    model.QUARTER = Set(initialize=quarter_names, ordered=True)
    model.STATE = Set(initialize=state_names, ordered=True)
    model.BUS = Set(initialize=bus_indices, ordered=True)
    model.GEN = Set(initialize=generator_indices_all, ordered=True)
    model.BRANCH = Set(initialize=branch_indices_all, ordered=True)

    model.project_start = Var(model.QUARTER, domain=Binary)
    model.project_available = Var(model.QUARTER, domain=Binary)
    model.connected_capacity = Var(model.QUARTER, domain=NonNegativeReals)
    model.access_shortfall = Var(model.QUARTER, domain=NonNegativeReals)

    model.one_start = Constraint(
        expr=sum(model.project_start[name] for name in quarter_names) <= 1
    )
    model.commissioning = ConstraintList()
    for quarter_position, quarter_name in enumerate(quarter_names):
        eligible_starts = quarter_names[
            : max(0, quarter_position - project.lead_time_quarters + 1)
        ]
        model.commissioning.add(
            model.project_available[quarter_name]
            == sum(model.project_start[name] for name in eligible_starts)
        )

    model.access = ConstraintList()
    for quarter_position, quarter in enumerate(quarters):
        name = quarter.name
        model.access.add(
            model.connected_capacity[name] + model.access_shortfall[name]
            == quarter.data_center_demand_mw
        )
        model.access.add(
            model.connected_capacity[name] <= poi.application_capacity_mw
        )
        model.access.add(
            model.connected_capacity[name]
            <= poi.initial_capacity_mw
            + project.poi_capacity_increase_mw * model.project_available[name]
        )
        if quarter_position:
            previous_name = quarters[quarter_position - 1].name
            model.access.add(
                model.connected_capacity[name]
                >= model.connected_capacity[previous_name]
            )

    def generation_bounds(
        _model: ConcreteModel,
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

    model.generation = Var(
        model.QUARTER,
        model.STATE,
        model.GEN,
        bounds=generation_bounds,
    )
    # Degrees keep the DC-flow coefficients well scaled; results use radians.
    model.angle = Var(model.QUARTER, model.STATE, model.BUS)
    model.flow = Var(model.QUARTER, model.STATE, model.BRANCH)

    def branch_flow_rule(
        model: ConcreteModel,
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
            return model.flow[quarter_name, state_name, branch_index] == 0.0
        susceptance_mw_per_rad = data.base_mva / (
            branch.reactance_pu * branch.tap_ratio
        )
        return model.flow[
            quarter_name, state_name, branch_index
        ] == susceptance_mw_per_rad * (
            radians(1.0)
            * (
                model.angle[quarter_name, state_name, branch.from_bus]
                - model.angle[quarter_name, state_name, branch.to_bus]
            )
            - branch.phase_shift_rad
        )

    model.branch_flow = Constraint(
        model.QUARTER,
        model.STATE,
        model.BRANCH,
        rule=branch_flow_rule,
    )

    model.thermal_limits = ConstraintList()
    for quarter_name in quarter_names:
        for state in states:
            increases = _rating_increases(project, state.branch_rating)
            for branch in data.branches:
                effective_rating = branch.rating_mw(state.branch_rating) + increases.get(
                    branch.index, 0.0
                ) * model.project_available[quarter_name]
                flow = model.flow[quarter_name, state.name, branch.index]
                model.thermal_limits.add(flow <= effective_rating)
                model.thermal_limits.add(-flow <= effective_rating)

    def balance_rule(
        model: ConcreteModel,
        quarter_name: str,
        state_name: str,
        bus: int,
    ) -> object:
        quarter = quarters[quarter_names.index(quarter_name)]
        generation = sum(
            model.generation[quarter_name, state_name, index]
            for index in generators_at_bus[bus]
        )
        outgoing = sum(
            model.flow[quarter_name, state_name, index]
            for index in outgoing_at_bus[bus]
        )
        incoming = sum(
            model.flow[quarter_name, state_name, index]
            for index in incoming_at_bus[bus]
        )
        demand = bus_by_index[bus].demand_mw * quarter.system_load_multiplier
        if bus == poi.bus:
            demand += model.connected_capacity[quarter_name]
        return generation - demand == outgoing - incoming

    model.power_balance = Constraint(
        model.QUARTER,
        model.STATE,
        model.BUS,
        rule=balance_rule,
    )
    for quarter_name in quarter_names:
        for state_name in state_names:
            model.angle[quarter_name, state_name, data.reference_bus].fix(0.0)

    model.response = ConstraintList()
    for quarter_name in quarter_names:
        for state in states:
            if state.response_mode == "base":
                continue
            for generator_index in generator_indices_all:
                if generator_index in state.outaged_generator_indices:
                    continue
                contingency_generation = model.generation[
                    quarter_name, state.name, generator_index
                ]
                base_generation = model.generation[
                    quarter_name, "base", generator_index
                ]
                if state.response_mode == "fixed":
                    model.response.add(contingency_generation == base_generation)
                else:
                    model.response.add(
                        contingency_generation - base_generation
                        <= redispatch_up_mw[generator_index]
                    )
                    model.response.add(
                        base_generation - contingency_generation
                        <= redispatch_down_mw[generator_index]
                    )

    model.total_cost = Objective(
        expr=project.investment_cost
        * sum(
            quarter.discount_factor * model.project_start[quarter.name]
            for quarter in quarters
        )
        + sum(
            quarter.discount_factor
            * quarter.operating_hours
            * (
                sum(
                    generator.cost_quadratic
                    * model.generation[
                        quarter.name, "base", generator.index
                    ]
                    ** 2
                    + generator.cost_linear
                    * model.generation[
                        quarter.name, "base", generator.index
                    ]
                    + generator.cost_constant
                    for generator in data.generators
                    if generator.in_service
                )
                + access_shortfall_cost_per_mwh
                * model.access_shortfall[quarter.name]
            )
            for quarter in quarters
        ),
        sense=minimize,
    )

    linear_solver_probe = SolverFactory(solver_name)
    if not linear_solver_probe.available(exception_flag=False):
        raise RuntimeError(f"Solver '{solver_name}' is not available")

    canonical_candidate_starts = (None, *quarter_names)
    canonical_index_by_start = {
        start_quarter: index
        for index, start_quarter in enumerate(canonical_candidate_starts)
    }
    latest_commissioning_start = (
        len(quarter_names) - 1 - project.lead_time_quarters
    )
    commissioning_starts = (
        tuple(reversed(quarter_names[: latest_commissioning_start + 1]))
        if latest_commissioning_start >= 0
        else ()
    )
    first_noncommissioning_start = max(latest_commissioning_start + 1, 0)
    noncommissioning_starts = quarter_names[first_noncommissioning_start:]
    solve_starts = (*commissioning_starts, None, *noncommissioning_starts)
    qp_workspace = OsqpQpWorkspace(
        feasibility_tolerance=1.0e-5,
        eps_abs=1.0e-6,
        eps_rel=1.0e-8,
        time_limit_seconds=120.0,
        verbose=tee,
    )

    diagnostics_by_index: list[dict[str, object] | None] = [
        None
    ] * len(canonical_candidate_starts)
    best_candidate_index = None
    best_objective = None
    best_variable_values = None
    best_solver_status = None
    best_solver_message = None
    unresolved_candidate = False
    for solve_order, start_quarter in enumerate(solve_starts):
        candidate_index = canonical_index_by_start[start_quarter]
        start_position = (
            None
            if start_quarter is None
            else quarter_names.index(start_quarter)
        )
        candidate_commissioned = {
            name: start_position is not None
            and position >= start_position + project.lead_time_quarters
            for position, name in enumerate(quarter_names)
        }
        for name in quarter_names:
            model.project_start[name].fix(int(name == start_quarter))
            model.project_available[name].fix(int(candidate_commissioned[name]))

        qp_result = qp_workspace.solve(model)
        candidate_solver_seconds = (
            qp_result.extraction_seconds
            + qp_result.setup_seconds
            + qp_result.update_seconds
            + qp_result.solve_seconds
        )
        repair_result = None
        if qp_result.solved and qp_result.objective_value is not None:
            repair_result = _run_linear_repair(
                model,
                quarters=quarters,
                data=data,
                qp_objective_value=qp_result.objective_value,
                qp_hessian_nonzeros=qp_result.hessian_nonzeros,
                qp_objective_scale=qp_result.objective_scale,
                qp_feasibility_tolerance=float(
                    qp_result.settings["feasibility_tolerance"]
                ),
                solver_name=solver_name,
                tee=tee,
            )
            candidate_solver_seconds += float(repair_result["solve_seconds"])
        diagnostic: dict[str, object] = {
            "candidate_index": candidate_index,
            "candidate": (
                "no_start"
                if start_quarter is None
                else f"start_{start_quarter}"
            ),
            "start_quarter": start_quarter,
            "commissioned_by_quarter": dict(candidate_commissioned),
            "solve_order": solve_order,
            "resolved": False,
            "feasible": False,
            "selected": False,
            "objective": None,
            "resolution_reason": None,
            "qp_settings": dict(qp_result.settings),
            "qp_workspace_reused": qp_result.workspace_reused,
            "qp_warm_started": qp_result.warm_started,
            "qp_status": qp_result.status,
            "qp_status_value": qp_result.status_value,
            "qp_objective_value": qp_result.objective_value,
            "qp_iterations": qp_result.iterations,
            "qp_variable_count": qp_result.variable_count,
            "qp_constraint_row_count": qp_result.constraint_row_count,
            "qp_hessian_nonzeros": qp_result.hessian_nonzeros,
            "qp_constraint_nonzeros": qp_result.constraint_nonzeros,
            "qp_objective_scale": qp_result.objective_scale,
            "qp_extraction_seconds": qp_result.extraction_seconds,
            "qp_setup_seconds": qp_result.setup_seconds,
            "qp_update_seconds": qp_result.update_seconds,
            "qp_solve_seconds": qp_result.solve_seconds,
            "qp_primal_residual": qp_result.primal_residual,
            "qp_dual_residual": qp_result.dual_residual,
            "qp_max_constraint_violation": (
                qp_result.max_constraint_violation
            ),
            "qp_bound_projection_count": qp_result.bound_projection_count,
            "qp_max_bound_projection": qp_result.max_bound_projection,
            "repair_solver_status": None,
            "repair_solver_message": None,
            "repair_termination_condition": None,
            "repair_solve_seconds": None,
            "candidate_solver_seconds": candidate_solver_seconds,
            "repair_max_constraint_violation": None,
            "repair_objective_deviation": None,
            "repair_objective_deviation_applicable": (
                qp_result.hessian_nonzeros > 0
            ),
            "repair_objective_deviation_assessment": None,
            "repair_objective_deviation_absolute_threshold": None,
            "repair_objective_deviation_relative_threshold": None,
            "repair_objective_deviation_scaled_numerical_repair_envelope": None,
            "repair_objective_deviation_threshold": None,
            "repair_objective_deviation_passed": None,
            "repair_objective_deviation_threshold_interpretation": (
                "numerical_acceptance_envelope_not_optimality_gap_or_"
                "error_certificate"
            ),
        }
        if repair_result is not None:
            diagnostic.update(
                {
                    "repair_solver_status": repair_result["solver_status"],
                    "repair_solver_message": repair_result["solver_message"],
                    "repair_termination_condition": repair_result[
                        "termination_condition"
                    ],
                    "repair_solve_seconds": repair_result["solve_seconds"],
                    "repair_max_constraint_violation": repair_result[
                        "max_constraint_violation"
                    ],
                    "repair_objective_deviation": repair_result[
                        "objective_deviation"
                    ],
                    "repair_objective_deviation_applicable": repair_result[
                        "objective_deviation_applicable"
                    ],
                    "repair_objective_deviation_assessment": repair_result[
                        "objective_deviation_assessment"
                    ],
                    "repair_objective_deviation_absolute_threshold": repair_result[
                        "objective_deviation_absolute_threshold"
                    ],
                    "repair_objective_deviation_relative_threshold": repair_result[
                        "objective_deviation_relative_threshold"
                    ],
                    "repair_objective_deviation_scaled_numerical_repair_envelope": repair_result[
                        "objective_deviation_scaled_numerical_repair_envelope"
                    ],
                    "repair_objective_deviation_threshold": repair_result[
                        "objective_deviation_threshold"
                    ],
                    "repair_objective_deviation_passed": repair_result[
                        "objective_deviation_passed"
                    ],
                    "repair_objective_deviation_threshold_interpretation": repair_result[
                        "objective_deviation_threshold_interpretation"
                    ],
                }
            )
        if not qp_result.solved or qp_result.objective_value is None:
            if qp_result.status_value == 3:
                diagnostic["resolved"] = True
                diagnostic["resolution_reason"] = "qp_primal_infeasible"
            else:
                unresolved_candidate = True
                diagnostic["resolution_reason"] = (
                    "qp_feasibility_check_failed"
                    if qp_result.status_value == 1
                    and qp_result.max_constraint_violation is not None
                    else "qp_not_resolved"
                )
            diagnostics_by_index[candidate_index] = diagnostic
            continue
        if repair_result is None or not bool(
            repair_result["termination_accepted"]
        ):
            unresolved_candidate = True
            diagnostic["resolution_reason"] = "linear_repair_not_resolved"
        elif float(repair_result["max_constraint_violation"]) > 1.0e-6:
            unresolved_candidate = True
            diagnostic["resolution_reason"] = (
                "linear_repair_constraint_violation"
            )
        elif repair_result["objective_deviation_passed"] is False:
            unresolved_candidate = True
            diagnostic["resolution_reason"] = "linear_repair_objective_deviation"
        else:
            repaired_objective = float(repair_result["objective"])
            diagnostic["resolved"] = True
            diagnostic["feasible"] = True
            diagnostic["objective"] = repaired_objective
            diagnostic["resolution_reason"] = "feasible_after_linear_repair"
            if (
                best_objective is None
                or repaired_objective < best_objective
                or (
                    repaired_objective == best_objective
                    and best_candidate_index is not None
                    and candidate_index < best_candidate_index
                )
            ):
                best_candidate_index = candidate_index
                best_objective = repaired_objective
                best_variable_values = tuple(
                    (variable, float(value(variable)))
                    for variable in model.component_data_objects(
                        Var,
                        active=True,
                        descend_into=True,
                    )
                )
                best_solver_status = str(repair_result["solver_status"])
                best_solver_message = str(repair_result["solver_message"])
        diagnostics_by_index[candidate_index] = diagnostic

    if any(diagnostic is None for diagnostic in diagnostics_by_index):
        raise RuntimeError("Fixed-start enumeration did not cover every candidate")
    diagnostics = tuple(
        diagnostic
        for diagnostic in diagnostics_by_index
        if diagnostic is not None
    )
    if not unresolved_candidate and best_candidate_index is not None:
        diagnostics[best_candidate_index]["selected"] = True
    excluded_branches = tuple(
        branch.index
        for branch in data.branches
        if branch.in_service and branch.index not in selected_branches
    )
    common_result = {
        "states": states,
        "excluded_branch_indices": excluded_branches,
        "candidate_diagnostics": diagnostics,
        "enumeration_method": (
            "exhaustive_fixed_start_direct_numerical_qp_with_linear_repair"
        ),
        "project_parameter_status": project.parameter_status,
        "capacity_interpretation": _M2_CAPACITY_INTERPRETATION,
    }
    if unresolved_candidate or best_variable_values is None:
        incomplete = unresolved_candidate
        return DeterministicExpansionResult(
            feasible=False,
            termination_condition=(
                "enumeration_incomplete"
                if incomplete
                else "all_enumerated_candidates_infeasible"
            ),
            solver_status="warning",
            solver_message=(
                "At least one fixed-start candidate was not resolved"
                if incomplete
                else "Every fixed-start candidate was reported primal infeasible"
            ),
            objective=None,
            optimization_objective=None,
            investment_cost=None,
            operating_cost=None,
            access_shortfall_cost=None,
            project_started=None,
            start_quarter=None,
            commissioned_by_quarter={},
            connected_capacity_mw={},
            access_shortfall_mw={},
            base_operating_cost_per_hour={},
            state_results={},
            effective_branch_ratings_mw={},
            **common_result,
        )

    for variable, variable_value in best_variable_values:
        variable.set_value(variable_value, skip_validation=True)
    termination = "enumerated_candidate_selected"
    solver_status = best_solver_status
    solver_message = best_solver_message
    commissioned_by_quarter = {
        name: bool(round(float(value(model.project_available[name]))))
        for name in quarter_names
    }
    connected_capacity_mw = {
        name: float(value(model.connected_capacity[name])) for name in quarter_names
    }
    access_shortfall_mw = {
        name: float(value(model.access_shortfall[name])) for name in quarter_names
    }
    starts = [
        name
        for name in quarter_names
        if float(value(model.project_start[name])) > 0.5
    ]
    state_results: dict[str, dict[str, DcOpfResult]] = {}
    effective_ratings: dict[str, dict[str, dict[int, float]]] = {}
    base_operating_cost_per_hour = {}
    for quarter in quarters:
        quarter_results = {}
        quarter_ratings = {}
        native_demand = {
            bus.index: bus.demand_mw * quarter.system_load_multiplier
            for bus in data.buses
        }
        for state in states:
            generation = {
                index: float(
                    value(model.generation[quarter.name, state.name, index])
                )
                for index in generator_indices_all
            }
            angles = {
                index: radians(
                    float(value(model.angle[quarter.name, state.name, index]))
                )
                for index in bus_indices
            }
            flows = {
                index: float(value(model.flow[quarter.name, state.name, index]))
                for index in branch_indices_all
            }
            residuals = {}
            for bus in bus_indices:
                generation_at_bus = sum(
                    generation[index] for index in generators_at_bus[bus]
                )
                outgoing = sum(flows[index] for index in outgoing_at_bus[bus])
                incoming = sum(flows[index] for index in incoming_at_bus[bus])
                demand = native_demand[bus]
                if bus == poi.bus:
                    demand += connected_capacity_mw[quarter.name]
                residuals[bus] = generation_at_bus - demand - outgoing + incoming
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
                solver_status=str(solver_status),
                solver_message=str(solver_message),
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
            increases = _rating_increases(project, state.branch_rating)
            quarter_ratings[state.name] = {
                branch.index: branch.rating_mw(state.branch_rating)
                + increases.get(branch.index, 0.0)
                * commissioned_by_quarter[quarter.name]
                for branch in data.branches
            }
        state_results[quarter.name] = quarter_results
        effective_ratings[quarter.name] = quarter_ratings
        base_operating_cost_per_hour[quarter.name] = quarter_results[
            "base"
        ].objective

    discount_by_quarter = {
        quarter.name: quarter.discount_factor for quarter in quarters
    }
    investment_cost = sum(
        project.investment_cost * discount_by_quarter[name] for name in starts
    )
    operating_cost = sum(
        quarter.discount_factor
        * quarter.operating_hours
        * base_operating_cost_per_hour[quarter.name]
        for quarter in quarters
    )
    shortfall_cost = sum(
        quarter.discount_factor
        * quarter.operating_hours
        * access_shortfall_cost_per_mwh
        * access_shortfall_mw[quarter.name]
        for quarter in quarters
    )
    return DeterministicExpansionResult(
        feasible=True,
        termination_condition=termination,
        solver_status=str(solver_status),
        solver_message=str(solver_message),
        objective=investment_cost + operating_cost + shortfall_cost,
        optimization_objective=best_objective,
        investment_cost=investment_cost,
        operating_cost=operating_cost,
        access_shortfall_cost=shortfall_cost,
        project_started=bool(starts),
        start_quarter=starts[0] if starts else None,
        commissioned_by_quarter=commissioned_by_quarter,
        connected_capacity_mw=connected_capacity_mw,
        access_shortfall_mw=access_shortfall_mw,
        base_operating_cost_per_hour=base_operating_cost_per_hour,
        state_results=state_results,
        effective_branch_ratings_mw=effective_ratings,
        **common_result,
    )
