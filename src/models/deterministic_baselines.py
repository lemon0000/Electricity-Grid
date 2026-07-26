"""Deterministic B0-B2 access baselines with lexicographic objectives."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import inf, isfinite, radians
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
from pyomo.opt import TerminationCondition

from ..grid.rts24 import Rts24Data
from ..grid.scopf import (
    SecurityState,
    build_security_states,
    non_islanding_branch_indices,
)
from .deterministic_expansion import (
    ExistingBranchUpgrade,
    FixedPoi,
    _rating_increases,
    _validate_nonnegative_finite,
)
from .deterministic_fx import (
    DeterministicFxResult,
    FixedFxPlan,
    FxQuarter,
    FxServiceEnvelope,
    _RESPONSE_MODEL,
    evaluate_deterministic_fx_plan,
)


_PLANNING_VARIABLE_INDEXING = "quarter_root_only_no_state_or_scenario"
_MINIMUM_X_NORMALIZATION = (
    "conservative_minimum_x_normalization_not_economic_optimum"
)
_MAXIMUM_X_NORMALIZATION = (
    "conservative_maximum_x_normalization_not_economic_optimum"
)
_MODEL_FEASIBILITY_TOLERANCE = 1.0e-6
_INTEGRALITY_TOLERANCE = 1.0e-6
_LEXICOGRAPHIC_BAND_AUDIT_TOLERANCE = 1.0e-8
_SOLVER_FEASIBILITY_TOLERANCE = 1.0e-9
_LEXICOGRAPHIC_COMPONENTS = frozenset(
    {
        "primary_access_shortfall_fix",
        "endpoint_x_fix",
        "endpoint_project_count_fix",
    }
)


class BaselinePolicy(str, Enum):
    B0_WAIT = "B0_WAIT"
    B1_FIRM = "B1_FIRM"
    B2_STATIC_FX = "B2_STATIC_FX"


@dataclass(frozen=True)
class BaselineEndpoint:
    access_shortfall_mwh: float
    conditional_capacity_exposure_mwh: float
    firm_capacity_mw: dict[str, float]
    conditional_capacity_mw: dict[str, float]
    total_capacity_mw: dict[str, float]
    access_shortfall_mw: dict[str, float]
    project_started: bool
    project_start_quarter: str | None
    commissioned_by_quarter: dict[str, bool]
    state_call_mw: dict[str, dict[str, float]]
    state_poi_load_mw: dict[str, dict[str, float]]
    state_call_interpretation: str
    primary_target_mwh: float
    primary_tolerance_mwh: float
    primary_deviation_mwh: float
    primary_band_violation_mwh: float
    x_exposure_target_mwh: float
    x_exposure_tolerance_mwh: float
    x_exposure_deviation_mwh: float
    x_band_violation_mwh: float
    maximum_original_constraint_violation: float
    maximum_integrality_violation: float
    normalization_label: str
    planning_variable_indexing: str


@dataclass(frozen=True)
class BaselineSolveDiagnostic:
    stage: str
    accepted: bool
    failure_reason: str | None
    termination_condition: str
    solver_status: str
    solver_message: str
    lower_bound: float | None
    upper_bound: float | None
    absolute_gap: float | None
    gap_tolerance: float | None
    maximum_constraint_violation: float | None
    maximum_integrality_violation: float | None


@dataclass(frozen=True)
class DeterministicBaselineResult:
    policy: BaselinePolicy
    feasible: bool
    termination_condition: str
    solver_status: str
    solver_message: str
    primary_access_shortfall_mwh: float | None
    primary_tolerance_mwh: float | None
    minimum_x_exposure_mwh: float | None
    maximum_x_exposure_mwh: float | None
    x_exposure_tolerance_mwh: float | None
    minimum_x_endpoint: BaselineEndpoint | None
    maximum_x_endpoint: BaselineEndpoint | None
    displayed_endpoint: BaselineEndpoint | None
    displayed_endpoint_name: str | None
    normalization_label: str | None
    failure_stage: str | None
    stage_diagnostics: tuple[BaselineSolveDiagnostic, ...]
    planning_variable_indexing: str
    states: tuple[SecurityState, ...]
    excluded_branch_indices: tuple[int, ...]
    dispatch_result: DeterministicFxResult | None


def _is_accepted_termination(termination: object) -> bool:
    return termination in {
        TerminationCondition.optimal,
        TerminationCondition.globallyOptimal,
    }


def _mwh_tolerance(number: float) -> float:
    return max(1.0e-6, 1.0e-8 * max(abs(number), 1.0))


def _finite_float(number: object) -> float | None:
    try:
        converted = float(number)
    except (TypeError, ValueError):
        return None
    return converted if isfinite(converted) else None


def _maximum_model_violation(
    model: ConcreteModel,
    *,
    ignored_constraint_components: frozenset[str] = frozenset(),
) -> float:
    maximum = 0.0
    for constraint in model.component_data_objects(
        Constraint,
        active=True,
        descend_into=True,
    ):
        if constraint.parent_component().name in ignored_constraint_components:
            continue
        body = _finite_float(value(constraint.body, exception=False))
        if body is None:
            return inf
        if constraint.lower is not None:
            lower = _finite_float(value(constraint.lower, exception=False))
            if lower is None:
                return inf
            maximum = max(maximum, lower - body)
        if constraint.upper is not None:
            upper = _finite_float(value(constraint.upper, exception=False))
            if upper is None:
                return inf
            maximum = max(maximum, body - upper)
    for variable in model.component_data_objects(
        Var,
        active=True,
        descend_into=True,
    ):
        variable_value = _finite_float(value(variable, exception=False))
        if variable_value is None:
            return inf
        if variable.lb is not None:
            lower = _finite_float(value(variable.lb, exception=False))
            if lower is None:
                return inf
            maximum = max(maximum, lower - variable_value)
        if variable.ub is not None:
            upper = _finite_float(value(variable.ub, exception=False))
            if upper is None:
                return inf
            maximum = max(maximum, variable_value - upper)
    return max(maximum, 0.0)


def _maximum_integrality_violation(model: ConcreteModel) -> float:
    maximum = 0.0
    for variable in model.component_data_objects(
        Var,
        active=True,
        descend_into=True,
    ):
        if variable.is_continuous():
            continue
        variable_value = _finite_float(value(variable, exception=False))
        if variable_value is None:
            return inf
        maximum = max(maximum, abs(variable_value - round(variable_value)))
    return maximum


def _solver_options(solver_name: str) -> dict[str, float]:
    if solver_name.lower() not in {"highs", "appsi_highs"}:
        return {}
    return {
        "mip_rel_gap": 0.0,
        "mip_abs_gap": 0.0,
        "primal_feasibility_tolerance": _SOLVER_FEASIBILITY_TOLERANCE,
        "dual_feasibility_tolerance": _SOLVER_FEASIBILITY_TOLERANCE,
        "mip_feasibility_tolerance": _SOLVER_FEASIBILITY_TOLERANCE,
    }


def _solve_loaded(
    model: ConcreteModel,
    solver_name: str,
    tee: bool,
    *,
    stage: str,
) -> tuple[object | None, BaselineSolveDiagnostic]:
    solver = SolverFactory(solver_name)
    try:
        results = solver.solve(
            model,
            load_solutions=False,
            tee=tee,
            options=_solver_options(solver_name),
        )
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

    termination = results.solver.termination_condition
    status = str(results.solver.status)
    message = str(results.solver.message)
    lower_bound = _finite_float(results.problem.lower_bound)
    upper_bound = _finite_float(results.problem.upper_bound)
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
    termination_accepted = _is_accepted_termination(termination)
    if not termination_accepted:
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
            model.solutions.load_from(results)
        except Exception as error:
            failure_reason = "solution_load_exception"
            message = str(error)
        else:
            maximum_constraint_violation = _maximum_model_violation(model)
            maximum_integrality_violation = _maximum_integrality_violation(model)
            if maximum_constraint_violation > _MODEL_FEASIBILITY_TOLERANCE:
                failure_reason = "model_constraint_violation"
            elif maximum_integrality_violation > _INTEGRALITY_TOLERANCE:
                failure_reason = "integrality_violation"

    diagnostic = BaselineSolveDiagnostic(
        stage=stage,
        accepted=failure_reason is None,
        failure_reason=failure_reason,
        termination_condition=str(termination),
        solver_status=status,
        solver_message=message,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        absolute_gap=absolute_gap,
        gap_tolerance=gap_tolerance,
        maximum_constraint_violation=maximum_constraint_violation,
        maximum_integrality_violation=maximum_integrality_violation,
    )
    return results, diagnostic


def _clean_nonnegative(number: object) -> float:
    converted = float(value(number))
    if converted < -_MODEL_FEASIBILITY_TOLERANCE:
        raise RuntimeError(
            "Endpoint extraction encountered an unaudited negative value: "
            f"{converted}"
        )
    return max(0.0, converted)


def _extract_endpoint(
    model: ConcreteModel,
    *,
    quarters: tuple[FxQuarter, ...],
    states: tuple[SecurityState, ...],
    primary_target_mwh: float,
    primary_tolerance_mwh: float,
    x_exposure_target_mwh: float,
    x_exposure_tolerance_mwh: float,
    normalization_label: str,
) -> BaselineEndpoint:
    firm = {
        quarter.name: _clean_nonnegative(model.firm_capacity[quarter.name])
        for quarter in quarters
    }
    conditional = {
        quarter.name: _clean_nonnegative(
            model.conditional_capacity[quarter.name]
        )
        for quarter in quarters
    }
    total = {
        quarter.name: _clean_nonnegative(model.total_capacity[quarter.name])
        for quarter in quarters
    }
    shortfall = {
        quarter.name: _clean_nonnegative(model.access_shortfall[quarter.name])
        for quarter in quarters
    }
    starts = [
        quarter.name
        for quarter in quarters
        if float(value(model.project_start[quarter.name])) > 0.5
    ]
    commissioned = {
        quarter.name: float(value(model.project_available[quarter.name])) > 0.5
        for quarter in quarters
    }
    state_call = {
        quarter.name: {
            state.name: _clean_nonnegative(
                model.state_call[quarter.name, state.name]
            )
            for state in states
        }
        for quarter in quarters
    }
    state_poi_load = {
        quarter.name: {
            state.name: _clean_nonnegative(
                total[quarter.name] - state_call[quarter.name][state.name],
            )
            for state in states
        }
        for quarter in quarters
    }
    access_shortfall_mwh = sum(
        quarter.operating_hours * shortfall[quarter.name]
        for quarter in quarters
    )
    x_exposure_mwh = sum(
        quarter.operating_hours * conditional[quarter.name]
        for quarter in quarters
    )
    primary_deviation_mwh = access_shortfall_mwh - primary_target_mwh
    x_exposure_deviation_mwh = x_exposure_mwh - x_exposure_target_mwh
    return BaselineEndpoint(
        access_shortfall_mwh=access_shortfall_mwh,
        conditional_capacity_exposure_mwh=x_exposure_mwh,
        firm_capacity_mw=firm,
        conditional_capacity_mw=conditional,
        total_capacity_mw=total,
        access_shortfall_mw=shortfall,
        project_started=bool(starts),
        project_start_quarter=starts[0] if starts else None,
        commissioned_by_quarter=commissioned,
        state_call_mw=state_call,
        state_poi_load_mw=state_poi_load,
        state_call_interpretation=(
            "feasible_planning_witness_not_canonical_minimum_call_dispatch"
        ),
        primary_target_mwh=primary_target_mwh,
        primary_tolerance_mwh=primary_tolerance_mwh,
        primary_deviation_mwh=primary_deviation_mwh,
        primary_band_violation_mwh=max(
            access_shortfall_mwh
            - (primary_target_mwh + primary_tolerance_mwh),
            0.0,
        ),
        x_exposure_target_mwh=x_exposure_target_mwh,
        x_exposure_tolerance_mwh=x_exposure_tolerance_mwh,
        x_exposure_deviation_mwh=x_exposure_deviation_mwh,
        x_band_violation_mwh=max(
            x_exposure_target_mwh
            - x_exposure_tolerance_mwh
            - x_exposure_mwh,
            x_exposure_mwh
            - x_exposure_target_mwh
            - x_exposure_tolerance_mwh,
            0.0,
        ),
        maximum_original_constraint_violation=_maximum_model_violation(
            model,
            ignored_constraint_components=_LEXICOGRAPHIC_COMPONENTS,
        ),
        maximum_integrality_violation=_maximum_integrality_violation(model),
        normalization_label=normalization_label,
        planning_variable_indexing=_PLANNING_VARIABLE_INDEXING,
    )


def _normalize_endpoint(
    model: ConcreteModel,
    *,
    quarters: tuple[FxQuarter, ...],
    states: tuple[SecurityState, ...],
    primary_target_mwh: float,
    primary_tolerance_mwh: float,
    x_exposure_expression: object,
    target_x_exposure_mwh: float,
    x_exposure_tolerance_mwh: float,
    normalization_label: str,
    stage_prefix: str,
    stage_diagnostics: list[BaselineSolveDiagnostic],
    solver_name: str,
    tee: bool,
) -> BaselineEndpoint | None:
    model.endpoint_x_fix = Constraint(
        expr=x_exposure_expression == target_x_exposure_mwh
    )
    project_count = sum(
        model.project_start[quarter.name] for quarter in quarters
    )
    model.endpoint_project_count = Objective(
        expr=project_count,
        sense=minimize,
    )
    try:
        _, project_diagnostic = _solve_loaded(
            model,
            solver_name,
            tee,
            stage=f"{stage_prefix}_project_count",
        )
        stage_diagnostics.append(project_diagnostic)
        if not project_diagnostic.accepted:
            return None
        minimum_project_count = int(round(float(value(project_count))))
        model.endpoint_project_count.deactivate()
        model.endpoint_project_count_fix = Constraint(
            expr=project_count == minimum_project_count
        )
        model.endpoint_commissioning_exposure = Objective(
            expr=sum(
                quarter.operating_hours
                * model.project_available[quarter.name]
                for quarter in quarters
            ),
            sense=minimize,
        )
        _, commissioning_diagnostic = _solve_loaded(
            model,
            solver_name,
            tee,
            stage=f"{stage_prefix}_commissioning_exposure",
        )
        stage_diagnostics.append(commissioning_diagnostic)
        if not commissioning_diagnostic.accepted:
            return None
        try:
            endpoint = _extract_endpoint(
                model,
                quarters=quarters,
                states=states,
                primary_target_mwh=primary_target_mwh,
                primary_tolerance_mwh=primary_tolerance_mwh,
                x_exposure_target_mwh=target_x_exposure_mwh,
                x_exposure_tolerance_mwh=x_exposure_tolerance_mwh,
                normalization_label=normalization_label,
            )
        except RuntimeError as error:
            endpoint = None
            failure_reason = "endpoint_extraction_violation"
            audit_message = str(error)
            maximum_original_violation = None
            maximum_integrality_violation = None
        else:
            maximum_original_violation = (
                endpoint.maximum_original_constraint_violation
            )
            maximum_integrality_violation = (
                endpoint.maximum_integrality_violation
            )
            if (
                maximum_original_violation
                > _MODEL_FEASIBILITY_TOLERANCE
            ):
                failure_reason = "original_constraint_violation"
            elif (
                maximum_integrality_violation
                > _INTEGRALITY_TOLERANCE
            ):
                failure_reason = "integrality_violation"
            elif (
                endpoint.primary_band_violation_mwh
                > _LEXICOGRAPHIC_BAND_AUDIT_TOLERANCE
            ):
                failure_reason = "primary_band_violation"
            elif (
                endpoint.x_band_violation_mwh
                > _LEXICOGRAPHIC_BAND_AUDIT_TOLERANCE
            ):
                failure_reason = "x_exposure_band_violation"
            else:
                failure_reason = None
            audit_message = (
                "Endpoint passed original-constraint, integrality, primary-"
                "band, and X-band audits"
                if failure_reason is None
                else f"Endpoint audit failed: {failure_reason}"
            )
        stage_diagnostics.append(
            BaselineSolveDiagnostic(
                stage=f"{stage_prefix}_endpoint_audit",
                accepted=failure_reason is None,
                failure_reason=failure_reason,
                termination_condition="not_applicable",
                solver_status="ok" if failure_reason is None else "warning",
                solver_message=audit_message,
                lower_bound=None,
                upper_bound=None,
                absolute_gap=None,
                gap_tolerance=None,
                maximum_constraint_violation=maximum_original_violation,
                maximum_integrality_violation=(
                    maximum_integrality_violation
                ),
            )
        )
        return endpoint if failure_reason is None else None
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


def solve_deterministic_baseline(
    data: Rts24Data,
    *,
    policy: BaselinePolicy,
    quarters: Iterable[FxQuarter],
    poi: FixedPoi,
    project: ExistingBranchUpgrade,
    service_envelope: FxServiceEnvelope,
    redispatch_up_mw: Mapping[int, float],
    redispatch_down_mw: Mapping[int, float],
    access_shortfall_cost_per_mwh: float,
    branch_indices: Iterable[int] | None = None,
    generator_indices: Iterable[int] | None = None,
    immediate_rating: str = "rate_c",
    sustained_rating: str = "rate_a",
    solver_name: str = "highs",
    tee: bool = False,
) -> DeterministicBaselineResult:
    """Compute non-economic B0-B2 access endpoints and canonical dispatch."""

    if not isinstance(policy, BaselinePolicy):
        policy = BaselinePolicy(policy)
    quarters = tuple(quarters)
    if not quarters:
        raise ValueError("At least one baseline quarter is required")
    quarter_names = tuple(quarter.name for quarter in quarters)
    if any(not name for name in quarter_names) or len(set(quarter_names)) != len(
        quarter_names
    ):
        raise ValueError("Baseline quarter names must be nonempty and unique")
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
        _validate_nonnegative_finite(
            "Continuous validation hours", quarter.continuous_validation_hours
        )
        if quarter.continuous_validation_hours > quarter.operating_hours + 1.0e-9:
            raise ValueError(
                "Continuous validation hours cannot exceed operating hours"
            )
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
    if not project.name or not project.parameter_status:
        raise ValueError("Project name and parameter status must be explicit")
    _validate_nonnegative_finite(
        "POI capacity increase", project.poi_capacity_increase_mw
    )
    _validate_nonnegative_finite("Investment cost", project.investment_cost)
    _validate_nonnegative_finite(
        "Access shortfall cost", access_shortfall_cost_per_mwh
    )

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
            "Project contains unknown branch indices: "
            f"{sorted(unknown_upgrade_branches)}"
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
            raise ValueError("Canonical dispatch requires finite generator costs")
        if generator.cost_quadratic < 0.0:
            raise ValueError("Canonical dispatch requires convex generator costs")

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
    stage_diagnostics: list[BaselineSolveDiagnostic] = []

    def failed_result(
        termination_condition: object,
        solver_status: object,
        solver_message: object,
        *,
        failure_stage: str,
        primary: float | None = None,
        primary_tolerance: float | None = None,
        minimum_x: float | None = None,
        maximum_x: float | None = None,
        x_tolerance: float | None = None,
        minimum_endpoint: BaselineEndpoint | None = None,
        maximum_endpoint: BaselineEndpoint | None = None,
        dispatch_result: DeterministicFxResult | None = None,
    ) -> DeterministicBaselineResult:
        return DeterministicBaselineResult(
            policy=policy,
            feasible=False,
            termination_condition=str(termination_condition),
            solver_status=str(solver_status),
            solver_message=str(solver_message),
            primary_access_shortfall_mwh=primary,
            primary_tolerance_mwh=primary_tolerance,
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
            planning_variable_indexing=_PLANNING_VARIABLE_INDEXING,
            states=states,
            excluded_branch_indices=excluded_branches,
            dispatch_result=dispatch_result,
        )

    def normalization_failure_diagnostic(
        fallback_stage: str,
    ) -> BaselineSolveDiagnostic:
        if stage_diagnostics and not stage_diagnostics[-1].accepted:
            return stage_diagnostics[-1]
        diagnostic = BaselineSolveDiagnostic(
            stage=fallback_stage,
            accepted=False,
            failure_reason="normalization_returned_no_endpoint",
            termination_condition="not_applicable",
            solver_status="warning",
            solver_message="Endpoint normalization returned no audited endpoint",
            lower_bound=None,
            upper_bound=None,
            absolute_gap=None,
            gap_tolerance=None,
            maximum_constraint_violation=None,
            maximum_integrality_violation=None,
        )
        stage_diagnostics.append(diagnostic)
        return diagnostic

    state_names = tuple(state.name for state in states)
    branch_indices_all = tuple(branch_by_index)
    generators_at_bus = {bus: [] for bus in bus_indices}
    outgoing_at_bus = {bus: [] for bus in bus_indices}
    incoming_at_bus = {bus: [] for bus in bus_indices}
    bus_by_index = {bus.index: bus for bus in data.buses}
    quarter_by_name = {quarter.name: quarter for quarter in quarters}
    state_by_name = {state.name: state for state in states}
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
    model.firm_capacity = Var(model.QUARTER, domain=NonNegativeReals)
    model.conditional_capacity = Var(model.QUARTER, domain=NonNegativeReals)
    model.total_capacity = Var(model.QUARTER, domain=NonNegativeReals)
    model.access_shortfall = Var(model.QUARTER, domain=NonNegativeReals)
    model.project_start = Var(model.QUARTER, domain=Binary)
    model.project_available = Var(model.QUARTER, domain=Binary)

    model.one_start = Constraint(
        expr=sum(model.project_start[name] for name in quarter_names) <= 1
    )
    model.commissioning = ConstraintList()
    for position, name in enumerate(quarter_names):
        eligible_starts = quarter_names[
            : max(0, position - project.lead_time_quarters + 1)
        ]
        model.commissioning.add(
            model.project_available[name]
            == sum(model.project_start[start] for start in eligible_starts)
        )

    model.contract = ConstraintList()
    for position, quarter in enumerate(quarters):
        name = quarter.name
        model.contract.add(
            model.total_capacity[name]
            == model.firm_capacity[name] + model.conditional_capacity[name]
        )
        model.contract.add(
            model.total_capacity[name] + model.access_shortfall[name]
            == quarter.data_center_demand_mw
        )
        model.contract.add(
            model.conditional_capacity[name]
            <= service_envelope.max_conditional_capacity_mw
        )
        model.contract.add(
            model.total_capacity[name] <= poi.application_capacity_mw
        )
        model.contract.add(
            model.total_capacity[name]
            <= poi.initial_capacity_mw
            + project.poi_capacity_increase_mw
            * model.project_available[name]
        )
        if policy is BaselinePolicy.B0_WAIT:
            model.contract.add(
                model.total_capacity[name]
                <= poi.application_capacity_mw * model.project_available[name]
            )
            model.conditional_capacity[name].fix(0.0)
        elif policy is BaselinePolicy.B1_FIRM:
            model.conditional_capacity[name].fix(0.0)
        if position:
            previous = quarter_names[position - 1]
            model.contract.add(
                model.firm_capacity[name] >= model.firm_capacity[previous]
            )
            model.contract.add(
                model.total_capacity[name] >= model.total_capacity[previous]
            )

    model.state_call = Var(
        model.QUARTER,
        model.STATE,
        domain=NonNegativeReals,
    )
    model.service = ConstraintList()
    for quarter in quarters:
        for state in states:
            call = model.state_call[quarter.name, state.name]
            if state.response_mode in {"base", "fixed"}:
                call.fix(0.0)
            else:
                model.service.add(
                    call <= model.conditional_capacity[quarter.name]
                )
            model.service.add(
                model.total_capacity[quarter.name] - call
                >= model.firm_capacity[quarter.name]
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
    for quarter in quarters:
        for state in states:
            increases = _rating_increases(project, state.branch_rating)
            for branch in data.branches:
                effective_rating = branch.rating_mw(state.branch_rating) + (
                    increases.get(branch.index, 0.0)
                    * model.project_available[quarter.name]
                )
                flow = model.flow[quarter.name, state.name, branch.index]
                model.thermal_limits.add(flow <= effective_rating)
                model.thermal_limits.add(-flow <= effective_rating)

    def balance_rule(
        model: ConcreteModel,
        quarter_name: str,
        state_name: str,
        bus: int,
    ) -> object:
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
        demand = (
            bus_by_index[bus].demand_mw
            * quarter_by_name[quarter_name].system_load_multiplier
        )
        if bus == poi.bus:
            demand += (
                model.total_capacity[quarter_name]
                - model.state_call[quarter_name, state_name]
            )
        return generation - demand == outgoing - incoming

    model.power_balance = Constraint(
        model.QUARTER,
        model.STATE,
        model.BUS,
        rule=balance_rule,
    )
    for quarter in quarters:
        for state in states:
            model.angle[
                quarter.name, state.name, data.reference_bus
            ].fix(0.0)

    model.response = ConstraintList()
    for quarter in quarters:
        for state in states:
            if state.response_mode == "base":
                continue
            for generator in data.generators:
                if generator.index in state.outaged_generator_indices:
                    continue
                contingency = model.generation[
                    quarter.name, state.name, generator.index
                ]
                base = model.generation[
                    quarter.name, "base", generator.index
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
    access_shortfall_expression = sum(
        quarter.operating_hours * model.access_shortfall[quarter.name]
        for quarter in quarters
    )
    x_exposure_expression = sum(
        quarter.operating_hours * model.conditional_capacity[quarter.name]
        for quarter in quarters
    )
    model.primary_access_shortfall = Objective(
        expr=access_shortfall_expression,
        sense=minimize,
    )
    _, primary_diagnostic = _solve_loaded(
        model,
        solver_name,
        tee,
        stage="primary_access_shortfall",
    )
    stage_diagnostics.append(primary_diagnostic)
    if not primary_diagnostic.accepted:
        return failed_result(
            primary_diagnostic.termination_condition,
            primary_diagnostic.solver_status,
            primary_diagnostic.solver_message,
            failure_stage=primary_diagnostic.stage,
        )
    primary_access_shortfall = float(value(access_shortfall_expression))
    primary_tolerance = _mwh_tolerance(primary_access_shortfall)
    model.primary_access_shortfall.deactivate()
    # The tolerance below is an audit envelope, not a budget that later
    # lexicographic objectives may intentionally consume.  Preserve the
    # primary optimum itself throughout all subsequent stages.
    model.primary_access_shortfall_fix = Constraint(
        expr=access_shortfall_expression == primary_access_shortfall
    )

    model.minimum_x_exposure = Objective(
        expr=x_exposure_expression,
        sense=minimize,
    )
    _, minimum_x_diagnostic = _solve_loaded(
        model,
        solver_name,
        tee,
        stage="minimum_x_exposure",
    )
    stage_diagnostics.append(minimum_x_diagnostic)
    if not minimum_x_diagnostic.accepted:
        return failed_result(
            minimum_x_diagnostic.termination_condition,
            minimum_x_diagnostic.solver_status,
            minimum_x_diagnostic.solver_message,
            failure_stage=minimum_x_diagnostic.stage,
            primary=primary_access_shortfall,
            primary_tolerance=primary_tolerance,
        )
    minimum_x_exposure = float(value(x_exposure_expression))
    model.minimum_x_exposure.deactivate()

    model.maximum_x_exposure = Objective(
        expr=x_exposure_expression,
        sense=maximize,
    )
    _, maximum_x_diagnostic = _solve_loaded(
        model,
        solver_name,
        tee,
        stage="maximum_x_exposure",
    )
    stage_diagnostics.append(maximum_x_diagnostic)
    if not maximum_x_diagnostic.accepted:
        return failed_result(
            maximum_x_diagnostic.termination_condition,
            maximum_x_diagnostic.solver_status,
            maximum_x_diagnostic.solver_message,
            failure_stage=maximum_x_diagnostic.stage,
            primary=primary_access_shortfall,
            primary_tolerance=primary_tolerance,
            minimum_x=minimum_x_exposure,
        )
    maximum_x_exposure = float(value(x_exposure_expression))
    model.maximum_x_exposure.deactivate()
    if minimum_x_exposure >= -_LEXICOGRAPHIC_BAND_AUDIT_TOLERANCE:
        minimum_x_exposure = max(0.0, minimum_x_exposure)
    if maximum_x_exposure >= -_LEXICOGRAPHIC_BAND_AUDIT_TOLERANCE:
        maximum_x_exposure = max(0.0, maximum_x_exposure)
    x_exposure_tolerance = _mwh_tolerance(
        max(abs(minimum_x_exposure), abs(maximum_x_exposure))
    )
    if minimum_x_exposure < 0.0:
        interval_failure = "minimum_x_exposure_is_negative"
    elif maximum_x_exposure < 0.0:
        interval_failure = "maximum_x_exposure_is_negative"
    elif minimum_x_exposure > maximum_x_exposure:
        interval_failure = "minimum_x_exceeds_maximum_x"
    else:
        interval_failure = None
    interval_diagnostic = BaselineSolveDiagnostic(
        stage="x_exposure_interval_audit",
        accepted=interval_failure is None,
        failure_reason=interval_failure,
        termination_condition="not_applicable",
        solver_status="ok" if interval_failure is None else "warning",
        solver_message=(
            "Minimum and maximum X endpoints are consistently ordered"
            if interval_failure is None
            else "Minimum X exposure exceeds maximum X exposure"
        ),
        lower_bound=minimum_x_exposure,
        upper_bound=maximum_x_exposure,
        absolute_gap=abs(maximum_x_exposure - minimum_x_exposure),
        gap_tolerance=x_exposure_tolerance,
        maximum_constraint_violation=None,
        maximum_integrality_violation=None,
    )
    stage_diagnostics.append(interval_diagnostic)
    if not interval_diagnostic.accepted:
        return failed_result(
            interval_diagnostic.termination_condition,
            interval_diagnostic.solver_status,
            interval_diagnostic.solver_message,
            failure_stage=interval_diagnostic.stage,
            primary=primary_access_shortfall,
            primary_tolerance=primary_tolerance,
            minimum_x=minimum_x_exposure,
            maximum_x=maximum_x_exposure,
            x_tolerance=x_exposure_tolerance,
        )

    minimum_endpoint = _normalize_endpoint(
        model,
        quarters=quarters,
        states=states,
        primary_target_mwh=primary_access_shortfall,
        primary_tolerance_mwh=primary_tolerance,
        x_exposure_expression=x_exposure_expression,
        target_x_exposure_mwh=minimum_x_exposure,
        x_exposure_tolerance_mwh=x_exposure_tolerance,
        normalization_label=_MINIMUM_X_NORMALIZATION,
        stage_prefix="minimum_x",
        stage_diagnostics=stage_diagnostics,
        solver_name=solver_name,
        tee=tee,
    )
    if minimum_endpoint is None:
        failed_diagnostic = normalization_failure_diagnostic(
            "minimum_x_normalization"
        )
        return failed_result(
            failed_diagnostic.termination_condition,
            failed_diagnostic.solver_status,
            failed_diagnostic.solver_message,
            failure_stage=failed_diagnostic.stage,
            primary=primary_access_shortfall,
            primary_tolerance=primary_tolerance,
            minimum_x=minimum_x_exposure,
            maximum_x=maximum_x_exposure,
            x_tolerance=x_exposure_tolerance,
        )
    maximum_endpoint = _normalize_endpoint(
        model,
        quarters=quarters,
        states=states,
        primary_target_mwh=primary_access_shortfall,
        primary_tolerance_mwh=primary_tolerance,
        x_exposure_expression=x_exposure_expression,
        target_x_exposure_mwh=maximum_x_exposure,
        x_exposure_tolerance_mwh=x_exposure_tolerance,
        normalization_label=_MAXIMUM_X_NORMALIZATION,
        stage_prefix="maximum_x",
        stage_diagnostics=stage_diagnostics,
        solver_name=solver_name,
        tee=tee,
    )
    if maximum_endpoint is None:
        failed_diagnostic = normalization_failure_diagnostic(
            "maximum_x_normalization"
        )
        return failed_result(
            failed_diagnostic.termination_condition,
            failed_diagnostic.solver_status,
            failed_diagnostic.solver_message,
            failure_stage=failed_diagnostic.stage,
            primary=primary_access_shortfall,
            primary_tolerance=primary_tolerance,
            minimum_x=minimum_x_exposure,
            maximum_x=maximum_x_exposure,
            x_tolerance=x_exposure_tolerance,
            minimum_endpoint=minimum_endpoint,
        )

    displayed_plan = FixedFxPlan(
        firm_capacity_mw=minimum_endpoint.firm_capacity_mw,
        conditional_capacity_mw=minimum_endpoint.conditional_capacity_mw,
        project_start_quarter=minimum_endpoint.project_start_quarter,
        parameter_status=(
            "deterministic_baseline_displayed_endpoint_non_economic_"
            "normalization"
        ),
    )
    try:
        dispatch_result = evaluate_deterministic_fx_plan(
            data,
            quarters=quarters,
            poi=poi,
            project=project,
            plan=displayed_plan,
            service_envelope=service_envelope,
            redispatch_up_mw=redispatch_up_mw,
            redispatch_down_mw=redispatch_down_mw,
            access_shortfall_cost_per_mwh=access_shortfall_cost_per_mwh,
            branch_indices=selected_branches,
            generator_indices=selected_generators,
            immediate_rating=immediate_rating,
            sustained_rating=sustained_rating,
            solver_name=solver_name,
            tee=tee,
        )
    except (RuntimeError, ValueError) as error:
        return failed_result(
            "displayed_dispatch_exception",
            "warning",
            error,
            failure_stage="displayed_dispatch",
            primary=primary_access_shortfall,
            primary_tolerance=primary_tolerance,
            minimum_x=minimum_x_exposure,
            maximum_x=maximum_x_exposure,
            x_tolerance=x_exposure_tolerance,
            minimum_endpoint=minimum_endpoint,
            maximum_endpoint=maximum_endpoint,
        )
    if not dispatch_result.feasible:
        return failed_result(
            f"displayed_dispatch_failed:{dispatch_result.termination_condition}",
            dispatch_result.solver_status,
            dispatch_result.solver_message,
            failure_stage="displayed_dispatch",
            primary=primary_access_shortfall,
            primary_tolerance=primary_tolerance,
            minimum_x=minimum_x_exposure,
            maximum_x=maximum_x_exposure,
            x_tolerance=x_exposure_tolerance,
            minimum_endpoint=minimum_endpoint,
            maximum_endpoint=maximum_endpoint,
            dispatch_result=dispatch_result,
        )

    return DeterministicBaselineResult(
        policy=policy,
        feasible=True,
        termination_condition="baseline_and_displayed_dispatch_feasible",
        solver_status=dispatch_result.solver_status,
        solver_message=dispatch_result.solver_message,
        primary_access_shortfall_mwh=primary_access_shortfall,
        primary_tolerance_mwh=primary_tolerance,
        minimum_x_exposure_mwh=minimum_x_exposure,
        maximum_x_exposure_mwh=maximum_x_exposure,
        x_exposure_tolerance_mwh=x_exposure_tolerance,
        minimum_x_endpoint=minimum_endpoint,
        maximum_x_endpoint=maximum_endpoint,
        displayed_endpoint=minimum_endpoint,
        displayed_endpoint_name="minimum_x_endpoint",
        normalization_label=_MINIMUM_X_NORMALIZATION,
        failure_stage=None,
        stage_diagnostics=tuple(stage_diagnostics),
        planning_variable_indexing=_PLANNING_VARIABLE_INDEXING,
        states=states,
        excluded_branch_indices=excluded_branches,
        dispatch_result=dispatch_result,
    )
