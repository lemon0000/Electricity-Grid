"""Selected-contingency chronological DC-SCUC for native RTS-GMLC data.

The model is deliberately a benchmark backend. It uses a free-boundary
normal-state solve to derive an auditable first-hour state and freeze a small
critical contingency set. Strict constraint generation adds every state that
rejects the same fixed base dispatch, then a joint all-state LP verifies the
final commitment. It does not claim full N-1 or AC security.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import ceil, inf, isfinite, radians
from typing import Any, Mapping

from highspy import Highs
from pyomo.environ import (
    Binary,
    ConcreteModel,
    Constraint,
    ConstraintList,
    Expression,
    NonNegativeReals,
    Objective,
    RangeSet,
    Set,
    SolverFactory,
    UnitInterval,
    Var,
    minimize,
    value,
)
from pyomo.opt import TerminationCondition

from .chronological_dispatch import (
    ChronologicalDispatchRequest,
    ChronologicalDispatchResult,
)

_THERMAL_RESERVE_CATEGORIES = frozenset(
    {
        "Coal",
        "Gas CC",
        "Gas CT",
        "Oil CT",
        "Oil ST",
        "Solar PV",
        "Wind",
    }
)
_NORMAL_STATE_ID = "normal"
_RESULT_CLEAN_TOLERANCE = 1.0e-6


@dataclass(frozen=True)
class RtsGmlcSecurityState:
    state_id: str
    kind: str
    element_uid: str | None
    response_mode: str
    branch_rating: str


@dataclass(frozen=True)
class RtsGmlcCriticalSelection:
    branch_uids: tuple[str, ...]
    generator_uids: tuple[str, ...]
    excluded_islanding_branch_uids: tuple[str, ...]
    states: tuple[RtsGmlcSecurityState, ...]
    selection_scope: str


@dataclass(frozen=True)
class RtsGmlcContingencyPrescreen:
    initial_state: RtsGmlcInitialState
    critical_selection: RtsGmlcCriticalSelection
    solver_audit: RtsGmlcSolverAudit
    normal_branch_flows_mw: tuple[dict[str, float], ...]


@dataclass(frozen=True)
class RtsGmlcInitialState:
    commitment: dict[str, bool]
    generation_mw: dict[str, float]
    time_in_state_hours: dict[str, float]
    source_scope: str


@dataclass(frozen=True)
class RtsGmlcSolverAudit:
    accepted: bool
    termination_condition: str
    solver_status: str
    solver_message: str
    objective_usd: float | None
    lower_bound_usd: float | None
    upper_bound_usd: float | None
    absolute_gap_usd: float | None
    gap_tolerance_usd: float | None
    maximum_constraint_violation: float | None
    maximum_integrality_violation: float | None
    solver_threads: int
    configured_mip_relative_gap: float


@dataclass(frozen=True)
class RtsGmlcConstraintGenerationIterationAudit:
    iteration: int
    active_state_ids: tuple[str, ...]
    added_state_ids: tuple[str, ...]
    state_screen_terminations: dict[str, str]
    active_mip_audit: RtsGmlcSolverAudit


@dataclass(frozen=True)
class RtsGmlcConstraintGenerationAudit:
    converged: bool
    maximum_refinement_iterations: int
    iterations: tuple[RtsGmlcConstraintGenerationIterationAudit, ...]
    final_active_state_ids: tuple[str, ...]
    pre_registered_state_ids: tuple[str, ...]
    verified_state_ids: tuple[str, ...]
    relaxed_mip_lower_bound_usd: float
    full_feasible_objective_usd: float
    certified_absolute_gap_usd: float
    certified_relative_gap: float


@dataclass(frozen=True)
class RtsGmlcResidualAudit:
    maximum_balance_residual_mw: float
    maximum_dc_flow_bound_violation_mw: float
    maximum_branch_flow_equation_residual_mw: float
    maximum_branch_rating_violation_mw: float
    maximum_outage_flow_mw: float
    maximum_generation_bound_violation_mw: float
    maximum_commitment_logic_violation: float
    maximum_minimum_time_violation: float
    maximum_online_ramp_violation_mw: float
    maximum_reserve_bound_violation_mw: float
    maximum_reserve_shortfall_mw: float
    maximum_security_response_violation_mw: float
    commitment_feasible_by_step: tuple[bool, ...]
    ramp_feasible_by_step: tuple[bool, ...]
    reserve_feasible_by_step: tuple[bool, ...]
    normal_secure_by_step: tuple[bool, ...]
    contingency_secure_by_step: tuple[bool, ...]


@dataclass(frozen=True)
class RtsGmlcScucResult:
    dispatch_request: ChronologicalDispatchRequest
    dispatch_result: ChronologicalDispatchResult
    initial_state: RtsGmlcInitialState
    critical_selection: RtsGmlcCriticalSelection
    prescreen_audit: RtsGmlcSolverAudit
    scuc_audit: RtsGmlcSolverAudit
    sced_audit: RtsGmlcSolverAudit
    constraint_generation_audit: RtsGmlcConstraintGenerationAudit
    residual_audit: RtsGmlcResidualAudit
    normal_branch_flows_mw: tuple[dict[str, float], ...]
    normal_dc_flows_mw: tuple[dict[str, float], ...]
    reserve_up_mw: tuple[dict[str, float], ...]
    security_branch_flows_mw: dict[str, tuple[dict[str, float], ...]]
    security_generation_mw: dict[str, tuple[dict[str, float], ...]]
    dispatch_scope: str
    security_scope: str


@dataclass(frozen=True)
class _ModelContext:
    data: Any
    request: ChronologicalDispatchRequest
    points: tuple[Any, ...]
    states: tuple[RtsGmlcSecurityState, ...]
    total_demand_by_bus_mw: tuple[dict[int, float], ...]
    bus_by_uid: dict[int, Any]
    generator_by_uid: dict[str, Any]
    branch_by_uid: dict[str, Any]
    dc_branch_by_uid: dict[str, Any]
    generators_at_bus: dict[int, tuple[str, ...]]
    outgoing_branches: dict[int, tuple[str, ...]]
    incoming_branches: dict[int, tuple[str, ...]]
    outgoing_dc_branches: dict[int, tuple[str, ...]]
    incoming_dc_branches: dict[int, tuple[str, ...]]
    thermal_uids: tuple[str, ...]
    reserve_uids: tuple[str, ...]
    segment_pairs: tuple[tuple[str, int], ...]


def _number(value_: object) -> float:
    number = float(value_)
    if not isfinite(number):
        raise ValueError("RTS-GMLC SCUC inputs must be finite")
    return number


def _positive_part(number: float) -> float:
    return max(float(number), 0.0)


def _clean_nonnegative(number: float, label: str) -> float:
    candidate = float(number)
    if candidate < -_RESULT_CLEAN_TOLERANCE:
        raise RuntimeError(f"{label} is negative beyond the solver tolerance")
    return max(candidate, 0.0)


def _clean_to_bounds(number: float, lower: float, upper: float, label: str) -> float:
    candidate = float(number)
    if not isfinite(candidate):
        raise RuntimeError(f"{label} is not finite")
    if candidate < lower - _RESULT_CLEAN_TOLERANCE:
        raise RuntimeError(f"{label} is below its variable lower bound")
    if candidate > upper + _RESULT_CLEAN_TOLERANCE:
        raise RuntimeError(f"{label} is above its variable upper bound")
    return min(max(candidate, lower), upper)


def _timestamp_key(timestamp: Any) -> tuple[int, int, int, int, int, int]:
    return (
        timestamp.year,
        timestamp.month,
        timestamp.day,
        timestamp.hour,
        timestamp.minute,
        timestamp.second,
    )


def _profile_value(mapping: Mapping[str, float], uid: str, label: str) -> float:
    if uid not in mapping:
        raise ValueError(f"Hourly RTS-GMLC point omits {label} for {uid}")
    return _number(mapping[uid])


def _generator_bounds(point: Any, generator: Any) -> tuple[float, float]:
    lower = _profile_value(point.generator_min_mw, generator.uid, "minimum")
    upper = _profile_value(point.generator_max_mw, generator.uid, "maximum")
    if lower < 0.0 or upper < lower:
        raise ValueError(f"Invalid hourly generation bounds for {generator.uid}")
    return lower, upper


def _validate_inputs(
    data: Any,
    request: ChronologicalDispatchRequest,
    tolerance_mw: float,
) -> tuple[Any, ...]:
    tolerance = _number(tolerance_mw)
    if tolerance <= 0.0:
        raise ValueError("tolerance_mw must be positive")
    if not request.timestamps or len(request.timestamps) > 24:
        raise ValueError("RTS-GMLC short-window SCUC requires 1 to 24 hours")
    if abs(_number(request.time_step_hours) - 1.0) > tolerance:
        raise ValueError("RTS-GMLC benchmark supports one-hour steps only")
    if request.incidents:
        raise ValueError("Selected-N-1 enumeration does not accept incident chronology")
    zero_only = (
        request.dc_flexible_demand_mw,
        request.dc_recoverable_flexible_mw,
        request.dc_call_limit_mw,
        request.recovery_headroom_mw,
    )
    if any(abs(_number(item)) > tolerance for values in zero_only for item in values):
        raise ValueError(
            "RTS-GMLC benchmark accepts zero flexibility and recovery only"
        )
    carry_in_values = (
        request.initial_recovery_debt_mwh,
        request.initial_grid_call_mw,
        request.initial_active_event_duration_hours,
        *request.initial_event_count_by_period.values(),
        *request.initial_curtailment_energy_mwh_by_period.values(),
    )
    if (
        request.initial_has_prior_event
        or any(abs(_number(item)) > tolerance for item in carry_in_values)
        or abs(_number(request.flexibility_envelope.maximum_recovery_power_mw))
        > tolerance
        or abs(_number(request.flexibility_envelope.maximum_recovery_debt_mwh))
        > tolerance
    ):
        raise ValueError("RTS-GMLC benchmark requires a zero recovery boundary")
    if len(request.dc_requested_mw) != len(request.timestamps):
        raise ValueError("Data-center demand must match the dispatch horizon")

    generators = tuple(data.generators)
    generator_uids = {generator.uid for generator in generators}
    if len(generator_uids) != len(generators):
        raise ValueError("RTS-GMLC generator UIDs must be unique")
    for generator in generators:
        if generator.dispatch_mode == "committable" and (
            _number(generator.cold_start_cost_usd) < 0.0
            or _number(generator.shutdown_cost_usd) < 0.0
        ):
            raise ValueError(
                "RTS-GMLC prescreen reuse requires nonnegative startup/shutdown costs"
            )
    buses = tuple(data.buses)
    bus_uids = {int(bus.uid) for bus in buses}
    if request.dc_bus not in bus_uids:
        raise ValueError("The data-center bus is absent from RTS-GMLC")
    dc_branches = tuple(data.dc_branches)
    if (
        len(dc_branches) != 1
        or dc_branches[0].uid != "DC1"
        or abs(_number(dc_branches[0].p_min_mw) + 100.0) > tolerance
        or abs(_number(dc_branches[0].p_max_mw) - 100.0) > tolerance
    ):
        raise ValueError("RTS-GMLC benchmark requires lossless DC1 at +/-100 MW")
    if set(request.initial_commitment) != generator_uids:
        raise ValueError("Initial-state generator keys must match RTS-GMLC")
    if set(request.initial_generation_mw) != generator_uids:
        raise ValueError("Initial-generation keys must match RTS-GMLC")
    if set(request.initial_time_in_state_hours) != generator_uids:
        raise ValueError("Initial-duration keys must match RTS-GMLC")

    point_by_timestamp = {
        _timestamp_key(point.timestamp): point for point in data.hourly_points
    }
    points = []
    for index, timestamp in enumerate(request.timestamps):
        try:
            point = point_by_timestamp[_timestamp_key(timestamp)]
        except KeyError as error:
            raise ValueError(
                f"RTS-GMLC chronology does not contain request hour {timestamp}"
            ) from error
        demand = request.system_demand_by_bus_mw[index]
        if set(demand) != bus_uids:
            raise ValueError("System-demand bus keys must exactly match RTS-GMLC")
        if set(point.demand_by_bus_mw) != bus_uids:
            raise ValueError("RTS-GMLC hourly bus-demand keys are incomplete")
        for bus in bus_uids:
            if (
                abs(_number(demand[bus]) - _number(point.demand_by_bus_mw[bus]))
                > tolerance
            ):
                raise ValueError("Request system demand drifted from RTS-GMLC")
        availability = request.generator_availability[index]
        if set(availability) != generator_uids:
            raise ValueError("Generator-availability keys must match RTS-GMLC")
        for generator in generators:
            if generator.enabled and not availability[generator.uid]:
                raise ValueError(
                    "Unexpected generator unavailability requires an incident chronology"
                )
            _generator_bounds(point, generator)
        points.append(point)
    return tuple(points)


def _connected_components(data: Any, excluded_branch_uid: str | None) -> int:
    adjacency = {int(bus.uid): set() for bus in data.buses}
    for branch in data.branches:
        if branch.uid == excluded_branch_uid:
            continue
        adjacency[int(branch.from_bus)].add(int(branch.to_bus))
        adjacency[int(branch.to_bus)].add(int(branch.from_bus))
    unseen = set(adjacency)
    component_count = 0
    while unseen:
        component_count += 1
        stack = [min(unseen)]
        component: set[int] = set()
        while stack:
            bus = stack.pop()
            if bus in component:
                continue
            component.add(bus)
            stack.extend(adjacency[bus] - component)
        unseen -= component
    return component_count


def _security_states(
    branch_uids: tuple[str, ...],
    generator_uids: tuple[str, ...],
) -> tuple[RtsGmlcSecurityState, ...]:
    states = [
        RtsGmlcSecurityState(
            state_id=_NORMAL_STATE_ID,
            kind="normal",
            element_uid=None,
            response_mode="base",
            branch_rating="continuous",
        )
    ]
    for uid in branch_uids:
        states.extend(
            (
                RtsGmlcSecurityState(
                    state_id=f"branch_{uid}_immediate",
                    kind="branch",
                    element_uid=uid,
                    response_mode="fixed",
                    branch_rating="short_term",
                ),
                RtsGmlcSecurityState(
                    state_id=f"branch_{uid}_sustained",
                    kind="branch",
                    element_uid=uid,
                    response_mode="bounded",
                    branch_rating="continuous",
                ),
            )
        )
    for uid in generator_uids:
        states.append(
            RtsGmlcSecurityState(
                state_id=f"generator_{uid}_sustained",
                kind="generator",
                element_uid=uid,
                response_mode="bounded",
                branch_rating="continuous",
            )
        )
    return tuple(states)


def select_rts_gmlc_critical_contingencies(
    data: Any,
    normal_branch_flows_mw: tuple[Mapping[str, float], ...],
) -> RtsGmlcCriticalSelection:
    """Freeze one loaded internal branch per area, one tie, and one thermal per area."""

    if not normal_branch_flows_mw:
        raise ValueError("Critical-contingency selection requires normal flows")
    branch_by_uid = {branch.uid: branch for branch in data.branches}
    expected = set(branch_by_uid)
    if any(set(hour) != expected for hour in normal_branch_flows_mw):
        raise ValueError("Normal-flow rows must contain every RTS-GMLC AC branch")
    bus_area = {int(bus.uid): int(bus.area) for bus in data.buses}
    islanding = tuple(
        sorted(
            branch.uid
            for branch in data.branches
            if _connected_components(data, branch.uid) != 1
        )
    )
    eligible = [branch for branch in data.branches if branch.uid not in islanding]

    def maximum_loading(branch: Any) -> float:
        rating = _number(branch.continuous_rating_mw)
        if rating <= 0.0:
            raise ValueError(f"Branch {branch.uid} has a nonpositive rating")
        return max(
            abs(_number(hour[branch.uid])) / rating for hour in normal_branch_flows_mw
        )

    selected_branches: list[str] = []
    for area in sorted(set(bus_area.values())):
        candidates = [
            branch
            for branch in eligible
            if bus_area[int(branch.from_bus)] == area
            and bus_area[int(branch.to_bus)] == area
        ]
        if not candidates:
            raise ValueError(f"Area {area} has no non-islanding internal branch")
        selected = min(candidates, key=lambda item: (-maximum_loading(item), item.uid))
        selected_branches.append(selected.uid)
    ties = [
        branch
        for branch in eligible
        if bus_area[int(branch.from_bus)] != bus_area[int(branch.to_bus)]
    ]
    if not ties:
        raise ValueError("RTS-GMLC has no non-islanding inter-area branch")
    selected_tie = min(ties, key=lambda item: (-maximum_loading(item), item.uid))
    if selected_tie.uid not in selected_branches:
        selected_branches.append(selected_tie.uid)

    generator_uids = _select_critical_generator_uids(data)

    branch_uids = tuple(selected_branches)
    return RtsGmlcCriticalSelection(
        branch_uids=branch_uids,
        generator_uids=generator_uids,
        excluded_islanding_branch_uids=islanding,
        states=_security_states(branch_uids, generator_uids),
        selection_scope=(
            "maximum_normal_loading_internal_branch_per_area_plus_interarea_"
            "branch_and_largest_thermal_per_area_excluding_islanding"
        ),
    )


def _select_critical_generator_uids(data: Any) -> tuple[str, ...]:
    bus_area = {int(bus.uid): int(bus.area) for bus in data.buses}
    selected_generators = []
    for area in sorted(set(bus_area.values())):
        candidates = [
            generator
            for generator in data.generators
            if generator.dispatch_mode == "committable"
            and bus_area[int(generator.bus)] == area
        ]
        if not candidates:
            raise ValueError(f"Area {area} has no committable generator")
        selected = min(
            candidates,
            key=lambda item: (-_number(item.p_max_mw), item.uid),
        )
        selected_generators.append(selected.uid)
    return tuple(selected_generators)


def build_rts_gmlc_pre_registered_contingencies(
    data: Any,
    *,
    branch_uids: tuple[str, ...],
    generator_uids: tuple[str, ...],
) -> RtsGmlcCriticalSelection:
    """Build one explicit selected-N-1 set for reuse across comparable runs."""

    if not branch_uids or not generator_uids:
        raise ValueError("Pre-registered contingencies require branches and generators")
    if len(set(branch_uids)) != len(branch_uids):
        raise ValueError("Pre-registered branch contingencies must be unique")
    if len(set(generator_uids)) != len(generator_uids):
        raise ValueError("Pre-registered generator contingencies must be unique")

    branch_by_uid = {branch.uid: branch for branch in data.branches}
    generator_by_uid = {generator.uid: generator for generator in data.generators}
    missing_branches = sorted(set(branch_uids) - set(branch_by_uid))
    if missing_branches:
        raise ValueError(
            "Pre-registered contingencies reference unknown branches: "
            + ", ".join(missing_branches)
        )
    missing_generators = sorted(set(generator_uids) - set(generator_by_uid))
    if missing_generators:
        raise ValueError(
            "Pre-registered contingencies reference unknown generators: "
            + ", ".join(missing_generators)
        )

    islanding = tuple(
        sorted(
            branch.uid
            for branch in data.branches
            if _connected_components(data, branch.uid) != 1
        )
    )
    selected_islanding = sorted(set(branch_uids) & set(islanding))
    if selected_islanding:
        raise ValueError(
            "Pre-registered branch contingencies cannot island the AC network: "
            + ", ".join(selected_islanding)
        )
    invalid_generators = sorted(
        uid
        for uid in generator_uids
        if generator_by_uid[uid].dispatch_mode != "committable"
    )
    if invalid_generators:
        raise ValueError(
            "Pre-registered generator contingencies must be committable: "
            + ", ".join(invalid_generators)
        )

    return RtsGmlcCriticalSelection(
        branch_uids=branch_uids,
        generator_uids=generator_uids,
        excluded_islanding_branch_uids=islanding,
        states=_security_states(branch_uids, generator_uids),
        selection_scope=(
            "pre_registered_common_nonislanding_ac_branches_and_committable_"
            "generators"
        ),
    )


def _build_context(
    data: Any,
    request: ChronologicalDispatchRequest,
    points: tuple[Any, ...],
    states: tuple[RtsGmlcSecurityState, ...],
) -> _ModelContext:
    buses = tuple(data.buses)
    bus_by_uid = {int(bus.uid): bus for bus in buses}
    generators = tuple(data.generators)
    generator_by_uid = {generator.uid: generator for generator in generators}
    branches = tuple(data.branches)
    branch_by_uid = {branch.uid: branch for branch in branches}
    dc_branches = tuple(data.dc_branches)
    dc_branch_by_uid = {branch.uid: branch for branch in dc_branches}
    generators_at_bus = {bus: [] for bus in bus_by_uid}
    outgoing_branches = {bus: [] for bus in bus_by_uid}
    incoming_branches = {bus: [] for bus in bus_by_uid}
    outgoing_dc_branches = {bus: [] for bus in bus_by_uid}
    incoming_dc_branches = {bus: [] for bus in bus_by_uid}
    for generator in generators:
        generators_at_bus[int(generator.bus)].append(generator.uid)
    for branch in branches:
        outgoing_branches[int(branch.from_bus)].append(branch.uid)
        incoming_branches[int(branch.to_bus)].append(branch.uid)
    for branch in dc_branches:
        outgoing_dc_branches[int(branch.from_bus)].append(branch.uid)
        incoming_dc_branches[int(branch.to_bus)].append(branch.uid)
    total_demand = []
    for index, point in enumerate(points):
        demand = {
            int(bus): _number(power) for bus, power in point.demand_by_bus_mw.items()
        }
        demand[request.dc_bus] += _number(request.dc_requested_mw[index])
        total_demand.append(demand)
    thermal_uids = tuple(
        generator.uid
        for generator in generators
        if generator.dispatch_mode == "committable"
    )
    reserve_uids = tuple(
        generator.uid
        for generator in generators
        if generator.enabled
        and generator.dispatch_mode in {"committable", "curtailable"}
        and generator.category in _THERMAL_RESERVE_CATEGORIES
    )
    segment_pairs = []
    for uid in thermal_uids:
        generator = generator_by_uid[uid]
        if (
            len(generator.cost_breakpoints_mw) != 4
            or len(generator.cost_values_usd_per_hour) != 4
        ):
            raise ValueError(f"Thermal generator {uid} requires four cost points")
        points_mw = tuple(_number(item) for item in generator.cost_breakpoints_mw)
        if any(later <= earlier for earlier, later in zip(points_mw, points_mw[1:])):
            raise ValueError(f"Thermal generator {uid} cost points must increase")
        for segment in range(3):
            segment_pairs.append((uid, segment))
    return _ModelContext(
        data=data,
        request=request,
        points=points,
        states=states,
        total_demand_by_bus_mw=tuple(total_demand),
        bus_by_uid=bus_by_uid,
        generator_by_uid=generator_by_uid,
        branch_by_uid=branch_by_uid,
        dc_branch_by_uid=dc_branch_by_uid,
        generators_at_bus={
            key: tuple(items) for key, items in generators_at_bus.items()
        },
        outgoing_branches={
            key: tuple(items) for key, items in outgoing_branches.items()
        },
        incoming_branches={
            key: tuple(items) for key, items in incoming_branches.items()
        },
        outgoing_dc_branches={
            key: tuple(items) for key, items in outgoing_dc_branches.items()
        },
        incoming_dc_branches={
            key: tuple(items) for key, items in incoming_dc_branches.items()
        },
        thermal_uids=thermal_uids,
        reserve_uids=reserve_uids,
        segment_pairs=tuple(segment_pairs),
    )


def _rating_mw(branch: Any, state: RtsGmlcSecurityState) -> float:
    if state.branch_rating == "short_term":
        return _number(branch.short_term_rating_mw)
    if state.branch_rating == "continuous":
        return _number(branch.continuous_rating_mw)
    raise ValueError(f"Unknown RTS-GMLC branch rating {state.branch_rating}")


def _state_outages_branch(state: RtsGmlcSecurityState, branch_uid: str) -> bool:
    return state.kind == "branch" and state.element_uid == branch_uid


def _state_outages_generator(state: RtsGmlcSecurityState, uid: str) -> bool:
    return state.kind == "generator" and state.element_uid == uid


def _build_model(
    context: _ModelContext,
    fixed_initial: RtsGmlcInitialState | None,
) -> ConcreteModel:
    horizon = len(context.points)
    state_by_id = {state.state_id: state for state in context.states}
    generator_uids = tuple(context.generator_by_uid)
    branch_uids = tuple(context.branch_by_uid)
    dc_branch_uids = tuple(context.dc_branch_by_uid)
    bus_uids = tuple(context.bus_by_uid)
    model = ConcreteModel()
    model.TIME = RangeSet(0, horizon - 1)
    model.STATE = Set(initialize=tuple(state_by_id), ordered=True)
    model.BUS = Set(initialize=bus_uids, ordered=True)
    model.GEN = Set(initialize=generator_uids, ordered=True)
    model.THERMAL = Set(initialize=context.thermal_uids, ordered=True)
    model.BRANCH = Set(initialize=branch_uids, ordered=True)
    model.DC_BRANCH = Set(initialize=dc_branch_uids, ordered=True)
    model.RESERVE_GEN = Set(initialize=context.reserve_uids, ordered=True)
    model.SEGMENT = Set(initialize=context.segment_pairs, dimen=2, ordered=True)

    # Pointwise ordering of identical units deletes valid crossing UC trajectories;
    # leave multi-period symmetry handling to the MIP solver.
    model.commitment = Var(model.TIME, model.THERMAL, domain=Binary)
    # With binary commitment, transition indicators are exactly determined by
    # the linked bounds below; keeping them continuous removes redundant MIP
    # branching without relaxing the integer commitment feasible set.
    model.startup = Var(model.TIME, model.THERMAL, domain=UnitInterval)
    model.shutdown = Var(model.TIME, model.THERMAL, domain=UnitInterval)

    def generation_bounds(
        _model: ConcreteModel, state_id: str, time: int, uid: str
    ) -> tuple[float, float]:
        generator = context.generator_by_uid[uid]
        lower, upper = _generator_bounds(context.points[time], generator)
        state = state_by_id[state_id]
        if (
            _state_outages_generator(state, uid)
            or generator.dispatch_mode == "disabled"
        ):
            return 0.0, 0.0
        if generator.dispatch_mode == "fixed":
            if abs(upper - lower) > 1.0e-9:
                raise ValueError(f"Fixed generator {uid} has unequal hourly bounds")
            return upper, upper
        if generator.dispatch_mode == "curtailable":
            return lower, upper
        if generator.dispatch_mode == "committable":
            return 0.0, upper
        raise ValueError(f"Unknown dispatch mode for {uid}")

    model.generation = Var(
        model.STATE,
        model.TIME,
        model.GEN,
        domain=NonNegativeReals,
        bounds=generation_bounds,
    )
    model.angle_degrees = Var(model.STATE, model.TIME, model.BUS)

    def branch_bounds(
        _model: ConcreteModel, state_id: str, _time: int, uid: str
    ) -> tuple[float, float]:
        rating = _rating_mw(context.branch_by_uid[uid], state_by_id[state_id])
        return -rating, rating

    model.branch_flow = Var(model.STATE, model.TIME, model.BRANCH, bounds=branch_bounds)

    def dc_bounds(
        _model: ConcreteModel, _state: str, _time: int, uid: str
    ) -> tuple[float, float]:
        branch = context.dc_branch_by_uid[uid]
        return _number(branch.p_min_mw), _number(branch.p_max_mw)

    model.dc_flow = Var(model.STATE, model.TIME, model.DC_BRANCH, bounds=dc_bounds)

    def reserve_bounds(
        _model: ConcreteModel, _time: int, uid: str
    ) -> tuple[float, float]:
        return 0.0, 10.0 * _number(context.generator_by_uid[uid].ramp_mw_per_minute)

    model.reserve_up = Var(model.TIME, model.RESERVE_GEN, bounds=reserve_bounds)
    model.segment_power = Var(model.TIME, model.SEGMENT, domain=NonNegativeReals)

    model.commitment_logic = ConstraintList()
    for uid in context.thermal_uids:
        generator = context.generator_by_uid[uid]
        minimum_up = ceil(_number(generator.minimum_up_time_hours))
        minimum_down = ceil(_number(generator.minimum_down_time_hours))
        if fixed_initial is None:
            model.startup[0, uid].fix(0)
            model.shutdown[0, uid].fix(0)
        else:
            model.commitment_logic.add(
                model.commitment[0, uid] - int(fixed_initial.commitment[uid])
                == model.startup[0, uid] - model.shutdown[0, uid]
            )
            model.commitment_logic.add(
                model.startup[0, uid] <= model.commitment[0, uid]
            )
            model.commitment_logic.add(
                model.shutdown[0, uid] <= 1 - model.commitment[0, uid]
            )
        for time in range(1, horizon):
            model.commitment_logic.add(
                model.commitment[time, uid] - model.commitment[time - 1, uid]
                == model.startup[time, uid] - model.shutdown[time, uid]
            )
            model.commitment_logic.add(
                model.startup[time, uid] <= model.commitment[time, uid]
            )
            model.commitment_logic.add(
                model.shutdown[time, uid] <= 1 - model.commitment[time, uid]
            )
            if minimum_up > 0:
                first = max(
                    0 if fixed_initial is not None else 1,
                    time - minimum_up + 1,
                )
                model.commitment_logic.add(
                    sum(model.startup[index, uid] for index in range(first, time + 1))
                    <= model.commitment[time, uid]
                )
            if minimum_down > 0:
                first = max(
                    0 if fixed_initial is not None else 1,
                    time - minimum_down + 1,
                )
                model.commitment_logic.add(
                    sum(model.shutdown[index, uid] for index in range(first, time + 1))
                    <= 1 - model.commitment[time, uid]
                )

    model.generation_limits = ConstraintList()
    for state in context.states:
        for time, point in enumerate(context.points):
            for uid, generator in context.generator_by_uid.items():
                generation = model.generation[state.state_id, time, uid]
                lower, upper = _generator_bounds(point, generator)
                if (
                    _state_outages_generator(state, uid)
                    or generator.dispatch_mode == "disabled"
                ):
                    continue
                elif generator.dispatch_mode == "committable":
                    breakpoints = tuple(
                        _number(item) for item in generator.cost_breakpoints_mw
                    )
                    normal_cost_curve_implies_bounds = (
                        state.state_id == _NORMAL_STATE_ID
                        and abs(lower - breakpoints[0]) <= 1.0e-9
                        and abs(upper - breakpoints[-1]) <= 1.0e-9
                    )
                    if normal_cost_curve_implies_bounds:
                        continue
                    model.generation_limits.add(
                        generation >= lower * model.commitment[time, uid]
                    )
                    model.generation_limits.add(
                        generation <= upper * model.commitment[time, uid]
                    )
                elif generator.dispatch_mode == "fixed":
                    continue
                elif generator.dispatch_mode == "curtailable":
                    continue
                else:
                    raise ValueError(f"Unknown dispatch mode for {uid}")

    model.cost_curve = ConstraintList()
    for time in range(horizon):
        for uid in context.thermal_uids:
            generator = context.generator_by_uid[uid]
            breakpoints = tuple(_number(item) for item in generator.cost_breakpoints_mw)
            model.cost_curve.add(
                model.generation[_NORMAL_STATE_ID, time, uid]
                == breakpoints[0] * model.commitment[time, uid]
                + sum(model.segment_power[time, uid, segment] for segment in range(3))
            )
            for segment in range(3):
                model.cost_curve.add(
                    model.segment_power[time, uid, segment]
                    <= (breakpoints[segment + 1] - breakpoints[segment])
                    * model.commitment[time, uid]
                )

    model.normal_ramp = ConstraintList()
    if fixed_initial is not None:
        for uid in context.thermal_uids:
            generator = context.generator_by_uid[uid]
            ramp = _number(generator.ramp_mw_per_hour)
            p_max = _number(generator.p_max_mw)
            initial_generation = fixed_initial.generation_mw[uid]
            model.normal_ramp.add(
                model.generation[_NORMAL_STATE_ID, 0, uid] - initial_generation
                <= ramp + p_max * model.startup[0, uid]
            )
            model.normal_ramp.add(
                initial_generation - model.generation[_NORMAL_STATE_ID, 0, uid]
                <= ramp + p_max * model.shutdown[0, uid]
            )
    for time in range(1, horizon):
        for uid in context.thermal_uids:
            generator = context.generator_by_uid[uid]
            ramp = _number(generator.ramp_mw_per_hour)
            p_max = _number(generator.p_max_mw)
            current = model.generation[_NORMAL_STATE_ID, time, uid]
            previous = model.generation[_NORMAL_STATE_ID, time - 1, uid]
            model.normal_ramp.add(
                current - previous <= ramp + p_max * model.startup[time, uid]
            )
            model.normal_ramp.add(
                previous - current <= ramp + p_max * model.shutdown[time, uid]
            )

    model.branch_equations = ConstraintList()
    for state in context.states:
        for time in range(horizon):
            for uid, branch in context.branch_by_uid.items():
                flow = model.branch_flow[state.state_id, time, uid]
                if _state_outages_branch(state, uid):
                    model.branch_equations.add(flow == 0.0)
                else:
                    coefficient = _number(context.data.base_mva) / (
                        _number(branch.reactance_pu) * _number(branch.tap_ratio)
                    )
                    model.branch_equations.add(
                        flow
                        == coefficient
                        * radians(1.0)
                        * (
                            model.angle_degrees[
                                state.state_id, time, int(branch.from_bus)
                            ]
                            - model.angle_degrees[
                                state.state_id, time, int(branch.to_bus)
                            ]
                        )
                    )
            model.angle_degrees[
                state.state_id, time, int(context.data.reference_bus)
            ].fix(0.0)

    model.power_balance = ConstraintList()
    for state in context.states:
        for time in range(horizon):
            for bus in bus_uids:
                generation = sum(
                    model.generation[state.state_id, time, uid]
                    for uid in context.generators_at_bus[bus]
                )
                ac_net_export = sum(
                    model.branch_flow[state.state_id, time, uid]
                    for uid in context.outgoing_branches[bus]
                ) - sum(
                    model.branch_flow[state.state_id, time, uid]
                    for uid in context.incoming_branches[bus]
                )
                dc_net_export = sum(
                    model.dc_flow[state.state_id, time, uid]
                    for uid in context.outgoing_dc_branches[bus]
                ) - sum(
                    model.dc_flow[state.state_id, time, uid]
                    for uid in context.incoming_dc_branches[bus]
                )
                model.power_balance.add(
                    generation - context.total_demand_by_bus_mw[time][bus]
                    == ac_net_export + dc_net_export
                )

    model.security_response = ConstraintList()
    for state in context.states:
        if state.response_mode == "base":
            continue
        for time in range(horizon):
            if state.response_mode == "fixed":
                for uid in generator_uids:
                    model.security_response.add(
                        model.generation[state.state_id, time, uid]
                        == model.generation[_NORMAL_STATE_ID, time, uid]
                    )
                for uid in dc_branch_uids:
                    model.security_response.add(
                        model.dc_flow[state.state_id, time, uid]
                        == model.dc_flow[_NORMAL_STATE_ID, time, uid]
                    )
            else:
                for uid, generator in context.generator_by_uid.items():
                    if _state_outages_generator(state, uid):
                        continue
                    limit = (
                        _number(generator.ramp_mw_per_hour)
                        if generator.enabled
                        else 0.0
                    )
                    correction = (
                        model.generation[state.state_id, time, uid]
                        - model.generation[_NORMAL_STATE_ID, time, uid]
                    )
                    model.security_response.add(correction <= limit)
                    model.security_response.add(correction >= -limit)

    reserve_commitment_pairs = []
    for time, point in enumerate(context.points):
        for uid in context.reserve_uids:
            generator = context.generator_by_uid[uid]
            if generator.dispatch_mode != "committable":
                continue
            lower, upper = _generator_bounds(point, generator)
            ten_minute_cap = 10.0 * _number(generator.ramp_mw_per_minute)
            if ten_minute_cap < upper - lower:
                reserve_commitment_pairs.append((time, uid))
    model.RESERVE_COMMITMENT_PAIR = Set(
        initialize=reserve_commitment_pairs,
        dimen=2,
        ordered=True,
    )

    def reserve_commitment_envelope_rule(
        model_: ConcreteModel, time: int, uid: str
    ) -> Any:
        ten_minute_cap = 10.0 * _number(
            context.generator_by_uid[uid].ramp_mw_per_minute
        )
        return (
            model_.reserve_up[time, uid]
            <= ten_minute_cap * model_.commitment[time, uid]
        )

    # This is implied when commitment is binary and tightens only its LP relaxation.
    model.reserve_commitment_envelope = Constraint(
        model.RESERVE_COMMITMENT_PAIR,
        rule=reserve_commitment_envelope_rule,
    )

    model.reserve_constraints = ConstraintList()
    bus_area = {int(bus.uid): int(bus.area) for bus in context.data.buses}
    for time, point in enumerate(context.points):
        for uid in context.reserve_uids:
            generator = context.generator_by_uid[uid]
            _lower, upper = _generator_bounds(point, generator)
            if generator.dispatch_mode == "committable":
                headroom = (
                    upper * model.commitment[time, uid]
                    - model.generation[_NORMAL_STATE_ID, time, uid]
                )
            else:
                headroom = upper - model.generation[_NORMAL_STATE_ID, time, uid]
            model.reserve_constraints.add(model.reserve_up[time, uid] <= headroom)
        for area, requirement in point.spin_up_requirement_by_area_mw.items():
            eligible = [
                uid
                for uid in context.reserve_uids
                if bus_area[int(context.generator_by_uid[uid].bus)] == int(area)
            ]
            model.reserve_constraints.add(
                sum(model.reserve_up[time, uid] for uid in eligible)
                >= _number(requirement)
            )

    production_terms = []
    for time in range(horizon):
        for uid in context.thermal_uids:
            generator = context.generator_by_uid[uid]
            breakpoints = tuple(_number(item) for item in generator.cost_breakpoints_mw)
            costs = tuple(_number(item) for item in generator.cost_values_usd_per_hour)
            production_terms.append(costs[0] * model.commitment[time, uid])
            for segment in range(3):
                slope = (costs[segment + 1] - costs[segment]) / (
                    breakpoints[segment + 1] - breakpoints[segment]
                )
                production_terms.append(slope * model.segment_power[time, uid, segment])
            production_terms.append(
                _number(generator.cold_start_cost_usd) * model.startup[time, uid]
            )
            production_terms.append(
                _number(generator.shutdown_cost_usd) * model.shutdown[time, uid]
            )
    model.operating_cost = Expression(expr=sum(production_terms))
    model.objective = Objective(expr=model.operating_cost, sense=minimize)
    return model


def _constraint_violation(model: ConcreteModel) -> float:
    maximum = 0.0
    for constraint in model.component_data_objects(
        Constraint, active=True, descend_into=True
    ):
        body = value(constraint.body, exception=False)
        if body is None or not isfinite(float(body)):
            return inf
        body_number = float(body)
        if constraint.lower is not None:
            lower = value(constraint.lower, exception=False)
            if lower is None or not isfinite(float(lower)):
                return inf
            maximum = max(maximum, float(lower) - body_number)
        if constraint.upper is not None:
            upper = value(constraint.upper, exception=False)
            if upper is None or not isfinite(float(upper)):
                return inf
            maximum = max(maximum, body_number - float(upper))
    for variable in model.component_data_objects(Var, active=True, descend_into=True):
        candidate = value(variable, exception=False)
        if candidate is None or not isfinite(float(candidate)):
            return inf
        candidate_number = float(candidate)
        if variable.lb is not None:
            lower = value(variable.lb, exception=False)
            if lower is None or not isfinite(float(lower)):
                return inf
            maximum = max(maximum, float(lower) - candidate_number)
        if variable.ub is not None:
            upper = value(variable.ub, exception=False)
            if upper is None or not isfinite(float(upper)):
                return inf
            maximum = max(maximum, candidate_number - float(upper))
    return max(maximum, 0.0)


def _integrality_violation(model: ConcreteModel) -> float:
    maximum = 0.0
    for variable in model.component_data_objects(Var, active=True, descend_into=True):
        if variable.is_continuous():
            continue
        candidate = value(variable, exception=False)
        if candidate is None or not isfinite(float(candidate)):
            return inf
        maximum = max(maximum, abs(float(candidate) - round(float(candidate))))
    return maximum


def _optional_finite(value_: object | None) -> float | None:
    if value_ is None:
        return None
    candidate = float(value_)
    return candidate if isfinite(candidate) else None


def _solve(
    model: ConcreteModel,
    *,
    solver_name: str,
    tee: bool,
    tolerance: float,
    solver_threads: int,
    mip_relative_gap: float,
) -> RtsGmlcSolverAudit:
    solver = SolverFactory(solver_name)
    if not solver.available(exception_flag=False):
        raise RuntimeError(f"Solver '{solver_name}' is not available")
    if isinstance(solver_threads, bool) or solver_threads <= 0:
        raise ValueError("solver_threads must be a positive integer")
    mip_gap = _number(mip_relative_gap)
    if not 0.0 <= mip_gap <= 1.0e-3:
        raise ValueError("mip_relative_gap must lie in [0, 1e-3]")
    options: dict[str, float | int] = {}
    if solver_name.lower() in {"highs", "appsi_highs"}:
        options = {
            "mip_rel_gap": mip_gap,
            "mip_abs_gap": 0.0,
            "random_seed": 0,
            "threads": solver_threads,
            "primal_feasibility_tolerance": tolerance,
            "dual_feasibility_tolerance": tolerance,
            "mip_feasibility_tolerance": tolerance,
        }
    results = solver.solve(
        model,
        load_solutions=False,
        tee=tee,
        options=options,
    )
    termination = results.solver.termination_condition
    optimal = termination in {
        TerminationCondition.optimal,
        TerminationCondition.globallyOptimal,
    }
    lower = _optional_finite(results.problem.lower_bound)
    upper = _optional_finite(results.problem.upper_bound)
    gap = abs(upper - lower) if lower is not None and upper is not None else None
    scale = max(abs(lower or 0.0), abs(upper or 0.0), 1.0)
    gap_tolerance = max(tolerance, max(mip_gap, 1.0e-8) * scale)
    objective = None
    constraint_violation = None
    integrality_violation = None
    if optimal:
        model.solutions.load_from(results)
        objective_candidate = value(model.operating_cost, exception=False)
        objective = _optional_finite(objective_candidate)
        constraint_violation = _constraint_violation(model)
        integrality_violation = _integrality_violation(model)
    accepted = bool(
        optimal
        and objective is not None
        and gap is not None
        and gap <= gap_tolerance
        and constraint_violation is not None
        and constraint_violation <= tolerance
        and integrality_violation is not None
        and integrality_violation <= tolerance
    )
    return RtsGmlcSolverAudit(
        accepted=accepted,
        termination_condition=str(termination),
        solver_status=str(results.solver.status),
        solver_message=str(results.solver.message),
        objective_usd=objective,
        lower_bound_usd=lower,
        upper_bound_usd=upper,
        absolute_gap_usd=gap,
        gap_tolerance_usd=gap_tolerance,
        maximum_constraint_violation=constraint_violation,
        maximum_integrality_violation=integrality_violation,
        solver_threads=solver_threads,
        configured_mip_relative_gap=mip_gap,
    )


def _extract_generation(
    model: ConcreteModel,
    context: _ModelContext,
    state_id: str,
) -> tuple[dict[str, float], ...]:
    return tuple(
        {
            uid: _clean_nonnegative(
                float(value(model.generation[state_id, time, uid])),
                f"generation[{state_id},{time},{uid}]",
            )
            for uid in context.generator_by_uid
        }
        for time in range(len(context.points))
    )


def _extract_branch_flows(
    model: ConcreteModel,
    context: _ModelContext,
    state_id: str,
) -> tuple[dict[str, float], ...]:
    return tuple(
        {
            uid: float(value(model.branch_flow[state_id, time, uid]))
            for uid in context.branch_by_uid
        }
        for time in range(len(context.points))
    )


def _extract_dc_flows(
    model: ConcreteModel,
    context: _ModelContext,
    state_id: str,
) -> tuple[dict[str, float], ...]:
    return tuple(
        {
            uid: float(value(model.dc_flow[state_id, time, uid]))
            for uid in context.dc_branch_by_uid
        }
        for time in range(len(context.points))
    )


def _extract_commitment(
    model: ConcreteModel,
    context: _ModelContext,
) -> tuple[dict[str, bool], ...]:
    rows = []
    for time in range(len(context.points)):
        row = {}
        for uid, generator in context.generator_by_uid.items():
            if generator.dispatch_mode == "committable":
                row[uid] = bool(round(float(value(model.commitment[time, uid]))))
            else:
                row[uid] = bool(generator.enabled)
        rows.append(row)
    return tuple(rows)


def _derive_initial_state(
    model: ConcreteModel,
    context: _ModelContext,
) -> RtsGmlcInitialState:
    commitment = _extract_commitment(model, context)[0]
    generation = _extract_generation(model, context, _NORMAL_STATE_ID)[0]
    duration = {}
    for uid, generator in context.generator_by_uid.items():
        if generator.dispatch_mode == "committable":
            if not commitment[uid]:
                if generation[uid] > _RESULT_CLEAN_TOLERANCE:
                    raise RuntimeError(
                        f"Prescreen offline generator {uid} has positive output"
                    )
                generation[uid] = 0.0
            duration[uid] = _number(
                ceil(_number(generator.minimum_up_time_hours))
                if commitment[uid]
                else ceil(_number(generator.minimum_down_time_hours))
            )
        else:
            duration[uid] = 0.0
    return RtsGmlcInitialState(
        commitment=commitment,
        generation_mw=generation,
        time_in_state_hours=duration,
        source_scope="optimization_derived_free_boundary_not_observed_chronology",
    )


def _audit_solution(
    model: ConcreteModel,
    context: _ModelContext,
    initial_state: RtsGmlcInitialState,
    tolerance: float,
) -> RtsGmlcResidualAudit:
    horizon = len(context.points)
    commitment = _extract_commitment(model, context)
    generation = {
        state.state_id: _extract_generation(model, context, state.state_id)
        for state in context.states
    }
    branch_flows = {
        state.state_id: _extract_branch_flows(model, context, state.state_id)
        for state in context.states
    }
    dc_flows = {
        state.state_id: _extract_dc_flows(model, context, state.state_id)
        for state in context.states
    }
    bus_area = {int(bus.uid): int(bus.area) for bus in context.data.buses}
    max_balance = 0.0
    max_dc_bound = 0.0
    max_flow_equation = 0.0
    max_rating = 0.0
    max_outage_flow = 0.0
    max_generation_bound = 0.0
    max_commitment = 0.0
    max_minimum_time = 0.0
    max_ramp = 0.0
    max_reserve_bound = 0.0
    max_reserve_shortfall = 0.0
    max_response = 0.0
    commitment_step = [0.0] * horizon
    ramp_step = [0.0] * horizon
    reserve_step = [0.0] * horizon
    normal_step = [0.0] * horizon
    contingency_step = [0.0] * horizon

    for uid in context.thermal_uids:
        generator = context.generator_by_uid[uid]
        u_now = float(commitment[0][uid])
        u_initial = float(initial_state.commitment[uid])
        startup = float(value(model.startup[0, uid]))
        shutdown = float(value(model.shutdown[0, uid]))
        logic = max(
            abs(u_now - u_initial - startup + shutdown),
            _positive_part(startup + shutdown - 1.0),
            _positive_part(startup - u_now),
            _positive_part(shutdown - (1.0 - u_now)),
        )
        max_commitment = max(max_commitment, logic)
        commitment_step[0] = max(commitment_step[0], logic)
        output = generation[_NORMAL_STATE_ID][0][uid]
        initial_output = initial_state.generation_mw[uid]
        ramp = _number(generator.ramp_mw_per_hour)
        p_max = _number(generator.p_max_mw)
        violation = max(
            output - initial_output - ramp - p_max * startup,
            initial_output - output - ramp - p_max * shutdown,
            0.0,
        )
        max_ramp = max(max_ramp, violation)
        ramp_step[0] = max(ramp_step[0], violation)

    for state in context.states:
        for time, point in enumerate(context.points):
            for uid, generator in context.generator_by_uid.items():
                observed = generation[state.state_id][time][uid]
                lower, upper = _generator_bounds(point, generator)
                if (
                    _state_outages_generator(state, uid)
                    or generator.dispatch_mode == "disabled"
                ):
                    violation = abs(observed)
                elif generator.dispatch_mode == "committable":
                    online = float(commitment[time][uid])
                    violation = max(
                        lower * online - observed, observed - upper * online, 0.0
                    )
                elif generator.dispatch_mode == "fixed":
                    violation = abs(observed - upper)
                else:
                    violation = max(lower - observed, observed - upper, 0.0)
                max_generation_bound = max(max_generation_bound, violation)
                target = (
                    normal_step
                    if state.state_id == _NORMAL_STATE_ID
                    else contingency_step
                )
                target[time] = max(target[time], violation)
            for uid, branch in context.branch_by_uid.items():
                flow = branch_flows[state.state_id][time][uid]
                rating_violation = _positive_part(abs(flow) - _rating_mw(branch, state))
                max_rating = max(max_rating, rating_violation)
                target = (
                    normal_step
                    if state.state_id == _NORMAL_STATE_ID
                    else contingency_step
                )
                target[time] = max(target[time], rating_violation)
                if _state_outages_branch(state, uid):
                    max_outage_flow = max(max_outage_flow, abs(flow))
                    contingency_step[time] = max(contingency_step[time], abs(flow))
                else:
                    coefficient = _number(context.data.base_mva) / (
                        _number(branch.reactance_pu) * _number(branch.tap_ratio)
                    )
                    expected = (
                        coefficient
                        * radians(1.0)
                        * (
                            float(
                                value(
                                    model.angle_degrees[
                                        state.state_id, time, int(branch.from_bus)
                                    ]
                                )
                            )
                            - float(
                                value(
                                    model.angle_degrees[
                                        state.state_id, time, int(branch.to_bus)
                                    ]
                                )
                            )
                        )
                    )
                    residual = abs(flow - expected)
                    max_flow_equation = max(max_flow_equation, residual)
                    target[time] = max(target[time], residual)
            for uid, branch in context.dc_branch_by_uid.items():
                flow = dc_flows[state.state_id][time][uid]
                violation = max(
                    _number(branch.p_min_mw) - flow,
                    flow - _number(branch.p_max_mw),
                    0.0,
                )
                max_dc_bound = max(max_dc_bound, violation)
                target = (
                    normal_step
                    if state.state_id == _NORMAL_STATE_ID
                    else contingency_step
                )
                target[time] = max(target[time], violation)
            for bus in context.bus_by_uid:
                produced = sum(
                    generation[state.state_id][time][uid]
                    for uid in context.generators_at_bus[bus]
                )
                ac_export = sum(
                    branch_flows[state.state_id][time][uid]
                    for uid in context.outgoing_branches[bus]
                ) - sum(
                    branch_flows[state.state_id][time][uid]
                    for uid in context.incoming_branches[bus]
                )
                dc_export = sum(
                    dc_flows[state.state_id][time][uid]
                    for uid in context.outgoing_dc_branches[bus]
                ) - sum(
                    dc_flows[state.state_id][time][uid]
                    for uid in context.incoming_dc_branches[bus]
                )
                residual = abs(
                    produced
                    - context.total_demand_by_bus_mw[time][bus]
                    - ac_export
                    - dc_export
                )
                max_balance = max(max_balance, residual)
                target = (
                    normal_step
                    if state.state_id == _NORMAL_STATE_ID
                    else contingency_step
                )
                target[time] = max(target[time], residual)
            if state.response_mode == "fixed":
                for uid in context.generator_by_uid:
                    violation = abs(
                        generation[state.state_id][time][uid]
                        - generation[_NORMAL_STATE_ID][time][uid]
                    )
                    max_response = max(max_response, violation)
                    contingency_step[time] = max(contingency_step[time], violation)
                for uid in context.dc_branch_by_uid:
                    violation = abs(
                        dc_flows[state.state_id][time][uid]
                        - dc_flows[_NORMAL_STATE_ID][time][uid]
                    )
                    max_response = max(max_response, violation)
                    contingency_step[time] = max(contingency_step[time], violation)
            elif state.response_mode == "bounded":
                for uid, generator in context.generator_by_uid.items():
                    if _state_outages_generator(state, uid):
                        continue
                    limit = (
                        _number(generator.ramp_mw_per_hour)
                        if generator.enabled
                        else 0.0
                    )
                    correction = abs(
                        generation[state.state_id][time][uid]
                        - generation[_NORMAL_STATE_ID][time][uid]
                    )
                    violation = _positive_part(correction - limit)
                    max_response = max(max_response, violation)
                    contingency_step[time] = max(contingency_step[time], violation)

    for time in range(1, horizon):
        for uid in context.thermal_uids:
            u_now = float(commitment[time][uid])
            u_previous = float(commitment[time - 1][uid])
            startup = float(value(model.startup[time, uid]))
            shutdown = float(value(model.shutdown[time, uid]))
            logic = max(
                abs(u_now - u_previous - startup + shutdown),
                _positive_part(startup + shutdown - 1.0),
            )
            max_commitment = max(max_commitment, logic)
            commitment_step[time] = max(commitment_step[time], logic)
            generator = context.generator_by_uid[uid]
            minimum_up = ceil(_number(generator.minimum_up_time_hours))
            minimum_down = ceil(_number(generator.minimum_down_time_hours))
            if minimum_up > 0:
                first = max(0, time - minimum_up + 1)
                violation = _positive_part(
                    sum(
                        float(value(model.startup[index, uid]))
                        for index in range(first, time + 1)
                    )
                    - u_now
                )
                max_minimum_time = max(max_minimum_time, violation)
                commitment_step[time] = max(commitment_step[time], violation)
            if minimum_down > 0:
                first = max(0, time - minimum_down + 1)
                violation = _positive_part(
                    sum(
                        float(value(model.shutdown[index, uid]))
                        for index in range(first, time + 1)
                    )
                    - (1.0 - u_now)
                )
                max_minimum_time = max(max_minimum_time, violation)
                commitment_step[time] = max(commitment_step[time], violation)
            if commitment[time][uid] and commitment[time - 1][uid]:
                movement = abs(
                    generation[_NORMAL_STATE_ID][time][uid]
                    - generation[_NORMAL_STATE_ID][time - 1][uid]
                )
                violation = _positive_part(
                    movement - _number(generator.ramp_mw_per_hour)
                )
                max_ramp = max(max_ramp, violation)
                ramp_step[time] = max(ramp_step[time], violation)

    reserve_rows = tuple(
        {
            uid: _clean_nonnegative(
                float(value(model.reserve_up[time, uid])),
                f"reserve_up[{time},{uid}]",
            )
            for uid in context.reserve_uids
        }
        for time in range(horizon)
    )
    for time, point in enumerate(context.points):
        for uid in context.reserve_uids:
            generator = context.generator_by_uid[uid]
            reserve = reserve_rows[time][uid]
            _lower, upper = _generator_bounds(point, generator)
            if generator.dispatch_mode == "committable":
                headroom = (
                    upper * float(commitment[time][uid])
                    - generation[_NORMAL_STATE_ID][time][uid]
                )
            else:
                headroom = upper - generation[_NORMAL_STATE_ID][time][uid]
            violation = max(
                -reserve,
                reserve - headroom,
                reserve - 10.0 * _number(generator.ramp_mw_per_minute),
                0.0,
            )
            max_reserve_bound = max(max_reserve_bound, violation)
            reserve_step[time] = max(reserve_step[time], violation)
        for area, requirement in point.spin_up_requirement_by_area_mw.items():
            provided = sum(
                reserve_rows[time][uid]
                for uid in context.reserve_uids
                if bus_area[int(context.generator_by_uid[uid].bus)] == int(area)
            )
            shortfall = _positive_part(_number(requirement) - provided)
            max_reserve_shortfall = max(max_reserve_shortfall, shortfall)
            reserve_step[time] = max(reserve_step[time], shortfall)

    return RtsGmlcResidualAudit(
        maximum_balance_residual_mw=max_balance,
        maximum_dc_flow_bound_violation_mw=max_dc_bound,
        maximum_branch_flow_equation_residual_mw=max_flow_equation,
        maximum_branch_rating_violation_mw=max_rating,
        maximum_outage_flow_mw=max_outage_flow,
        maximum_generation_bound_violation_mw=max_generation_bound,
        maximum_commitment_logic_violation=max_commitment,
        maximum_minimum_time_violation=max_minimum_time,
        maximum_online_ramp_violation_mw=max_ramp,
        maximum_reserve_bound_violation_mw=max_reserve_bound,
        maximum_reserve_shortfall_mw=max_reserve_shortfall,
        maximum_security_response_violation_mw=max_response,
        commitment_feasible_by_step=tuple(
            value_ <= tolerance for value_ in commitment_step
        ),
        ramp_feasible_by_step=tuple(value_ <= tolerance for value_ in ramp_step),
        reserve_feasible_by_step=tuple(value_ <= tolerance for value_ in reserve_step),
        normal_secure_by_step=tuple(value_ <= tolerance for value_ in normal_step),
        contingency_secure_by_step=tuple(
            value_ <= tolerance for value_ in contingency_step
        ),
    )


def _fix_commitment_decisions(
    target_model: ConcreteModel,
    source_model: ConcreteModel,
    context: _ModelContext,
) -> None:
    for time in range(len(context.points)):
        for uid in context.thermal_uids:
            target_model.commitment[time, uid].fix(
                round(float(value(source_model.commitment[time, uid])))
            )
            target_model.startup[time, uid].fix(
                round(float(value(source_model.startup[time, uid])))
            )
            target_model.shutdown[time, uid].fix(
                round(float(value(source_model.shutdown[time, uid])))
            )


def _fix_normal_dispatch(
    target_model: ConcreteModel,
    source_model: ConcreteModel,
    context: _ModelContext,
) -> None:
    for time in range(len(context.points)):
        for uid in context.generator_by_uid:
            target_generation = target_model.generation[_NORMAL_STATE_ID, time, uid]
            target_model.generation[_NORMAL_STATE_ID, time, uid].fix(
                _clean_to_bounds(
                    float(
                        value(
                            source_model.generation[
                                _NORMAL_STATE_ID,
                                time,
                                uid,
                            ]
                        )
                    ),
                    float(target_generation.lb),
                    float(target_generation.ub),
                    f"screen_base_generation[{time},{uid}]",
                )
            )
        for uid in context.dc_branch_by_uid:
            target_flow = target_model.dc_flow[_NORMAL_STATE_ID, time, uid]
            target_model.dc_flow[_NORMAL_STATE_ID, time, uid].fix(
                _clean_to_bounds(
                    float(value(source_model.dc_flow[_NORMAL_STATE_ID, time, uid])),
                    float(target_flow.lb),
                    float(target_flow.ub),
                    f"screen_base_dc_flow[{time},{uid}]",
                )
            )


def _solve_active_state_model(
    data: Any,
    request: ChronologicalDispatchRequest,
    points: tuple[Any, ...],
    initial_state: RtsGmlcInitialState,
    states: tuple[RtsGmlcSecurityState, ...],
    *,
    solver_name: str,
    tee: bool,
    tolerance: float,
    solver_threads: int,
    mip_relative_gap: float,
) -> tuple[_ModelContext, ConcreteModel, RtsGmlcSolverAudit]:
    context = _build_context(data, request, points, states)
    model = _build_model(context, fixed_initial=initial_state)
    audit = _solve(
        model,
        solver_name=solver_name,
        tee=tee,
        tolerance=tolerance,
        solver_threads=solver_threads,
        mip_relative_gap=mip_relative_gap,
    )
    if not audit.accepted:
        raise RuntimeError(
            "RTS-GMLC active-state SCUC was not accepted: "
            f"{audit.termination_condition}"
        )
    return context, model, audit


def _screen_inactive_state(
    data: Any,
    request: ChronologicalDispatchRequest,
    points: tuple[Any, ...],
    initial_state: RtsGmlcInitialState,
    normal_state: RtsGmlcSecurityState,
    state: RtsGmlcSecurityState,
    active_model: ConcreteModel,
    *,
    solver_name: str,
    tee: bool,
    tolerance: float,
    solver_threads: int,
    mip_relative_gap: float,
) -> RtsGmlcSolverAudit:
    context = _build_context(data, request, points, (normal_state, state))
    model = _build_model(context, fixed_initial=initial_state)
    _fix_commitment_decisions(model, active_model, context)
    _fix_normal_dispatch(model, active_model, context)
    return _solve(
        model,
        solver_name=solver_name,
        tee=tee,
        tolerance=tolerance,
        solver_threads=solver_threads,
        mip_relative_gap=mip_relative_gap,
    )


def _run_constraint_generation(
    data: Any,
    request: ChronologicalDispatchRequest,
    points: tuple[Any, ...],
    initial_state: RtsGmlcInitialState,
    selection: RtsGmlcCriticalSelection,
    *,
    solver_name: str,
    tee: bool,
    tolerance: float,
    solver_threads: int,
    mip_relative_gap: float,
    initial_model: ConcreteModel,
    initial_audit: RtsGmlcSolverAudit,
) -> tuple[
    _ModelContext,
    ConcreteModel,
    RtsGmlcSolverAudit,
    tuple[RtsGmlcConstraintGenerationIterationAudit, ...],
]:
    normal_state = selection.states[0]
    if normal_state.state_id != _NORMAL_STATE_ID:
        raise ValueError("Constraint generation requires normal as the first state")
    state_by_id = {state.state_id: state for state in selection.states}
    pre_registered_ids = tuple(state_by_id)
    active_ids = [_NORMAL_STATE_ID]
    # The free-boundary prescreen and this fixed-initial normal master have the
    # same optimum under the current contract: carry-in time obligations are
    # not modeled and all startup/shutdown costs are nonnegative. The prescreen
    # solution therefore supplies a valid first master incumbent and bound.
    context = _build_context(data, request, points, (normal_state,))
    model = initial_model
    audit = initial_audit
    iteration_audits = []
    maximum_iterations = len(selection.states) - 1
    converged = False
    for iteration in range(1, maximum_iterations + 1):
        inactive_states = tuple(
            state for state in selection.states if state.state_id not in active_ids
        )
        if not inactive_states:
            converged = True
            break
        terminations: dict[str, str] = {}
        added_ids = []
        for state in inactive_states:
            screen = _screen_inactive_state(
                data,
                request,
                points,
                initial_state,
                normal_state,
                state,
                model,
                solver_name=solver_name,
                tee=tee,
                tolerance=tolerance,
                solver_threads=solver_threads,
                mip_relative_gap=mip_relative_gap,
            )
            terminations[state.state_id] = screen.termination_condition
            if screen.accepted:
                continue
            if screen.termination_condition == str(TerminationCondition.infeasible):
                added_ids.append(state.state_id)
                continue
            raise RuntimeError(
                f"RTS-GMLC state screen {state.state_id} failed without an "
                f"infeasibility certificate: {screen.termination_condition}"
            )
        iteration_audits.append(
            RtsGmlcConstraintGenerationIterationAudit(
                iteration=iteration,
                active_state_ids=tuple(active_ids),
                added_state_ids=tuple(added_ids),
                state_screen_terminations=terminations,
                active_mip_audit=audit,
            )
        )
        if not added_ids:
            converged = True
            break
        added = set(added_ids)
        active_ids.extend(
            state_id
            for state_id in pre_registered_ids
            if state_id in added and state_id not in active_ids
        )
        active_states = tuple(state_by_id[state_id] for state_id in active_ids)
        context, model, audit = _solve_active_state_model(
            data,
            request,
            points,
            initial_state,
            active_states,
            solver_name=solver_name,
            tee=tee,
            tolerance=tolerance,
            solver_threads=solver_threads,
            mip_relative_gap=mip_relative_gap,
        )
        if len(active_ids) == len(pre_registered_ids):
            converged = True
            break
    if not converged:
        raise RuntimeError(
            "RTS-GMLC constraint generation exceeded its iteration limit"
        )
    return context, model, audit, tuple(iteration_audits)


def _solve_normal_prescreen(
    data: Any,
    request: ChronologicalDispatchRequest,
    points: tuple[Any, ...],
    *,
    solver_name: str,
    tee: bool,
    tolerance: float,
    solver_threads: int,
    mip_relative_gap: float,
) -> tuple[
    _ModelContext,
    ConcreteModel,
    RtsGmlcSolverAudit,
    RtsGmlcInitialState,
    tuple[dict[str, float], ...],
]:
    prescreen_states = _security_states((), ())
    context = _build_context(data, request, points, prescreen_states)
    model = _build_model(context, fixed_initial=None)
    audit = _solve(
        model,
        solver_name=solver_name,
        tee=tee,
        tolerance=tolerance,
        solver_threads=solver_threads,
        mip_relative_gap=mip_relative_gap,
    )
    if not audit.accepted:
        raise RuntimeError(
            "RTS-GMLC normal-state prescreen was not accepted: "
            f"{audit.termination_condition}; "
            f"status={audit.solver_status}; "
            f"message={audit.solver_message}"
        )
    initial_state = _derive_initial_state(model, context)
    flows = _extract_branch_flows(model, context, _NORMAL_STATE_ID)
    return context, model, audit, initial_state, flows


def prescreen_rts_gmlc_critical_contingencies(
    data: Any,
    request: ChronologicalDispatchRequest,
    *,
    solver_name: str = "highs",
    tee: bool = False,
    tolerance_mw: float = 1.0e-6,
    solver_threads: int = 1,
    mip_relative_gap: float = 0.0,
) -> RtsGmlcContingencyPrescreen:
    """Run only the normal-state screen used by the critical-state rule."""

    tolerance = _number(tolerance_mw)
    points = _validate_inputs(data, request, tolerance)
    if solver_name.lower() in {"highs", "appsi_highs"}:
        Highs.resetGlobalScheduler(True)
    _context, _model, audit, initial_state, flows = _solve_normal_prescreen(
        data,
        request,
        points,
        solver_name=solver_name,
        tee=tee,
        tolerance=tolerance,
        solver_threads=solver_threads,
        mip_relative_gap=mip_relative_gap,
    )
    return RtsGmlcContingencyPrescreen(
        initial_state=initial_state,
        critical_selection=select_rts_gmlc_critical_contingencies(data, flows),
        solver_audit=audit,
        normal_branch_flows_mw=flows,
    )


def solve_rts_gmlc_scuc(
    data: Any,
    request: ChronologicalDispatchRequest,
    *,
    solver_name: str = "highs",
    tee: bool = False,
    tolerance_mw: float = 1.0e-6,
    solver_threads: int = 1,
    mip_relative_gap: float = 0.0,
    pre_registered_branch_uids: tuple[str, ...] | None = None,
    pre_registered_generator_uids: tuple[str, ...] | None = None,
) -> RtsGmlcScucResult:
    """Solve selected-N-1 SCUC and a fixed-commitment SCED replay."""

    tolerance = _number(tolerance_mw)
    points = _validate_inputs(data, request, tolerance)
    if solver_name.lower() in {"highs", "appsi_highs"}:
        Highs.resetGlobalScheduler(True)
    if (pre_registered_branch_uids is None) != (pre_registered_generator_uids is None):
        raise ValueError(
            "Pre-registered branch and generator contingencies must be supplied together"
        )
    (
        prescreen_context,
        prescreen_model,
        prescreen_audit,
        initial_state,
        prescreen_flows,
    ) = _solve_normal_prescreen(
        data,
        request,
        points,
        solver_name=solver_name,
        tee=tee,
        tolerance=tolerance,
        solver_threads=solver_threads,
        mip_relative_gap=mip_relative_gap,
    )
    bound_request = replace(
        request,
        initial_commitment=dict(initial_state.commitment),
        initial_generation_mw=dict(initial_state.generation_mw),
        initial_time_in_state_hours=dict(initial_state.time_in_state_hours),
    )
    if pre_registered_branch_uids is None:
        selection = select_rts_gmlc_critical_contingencies(data, prescreen_flows)
    else:
        selection = build_rts_gmlc_pre_registered_contingencies(
            data,
            branch_uids=pre_registered_branch_uids,
            generator_uids=pre_registered_generator_uids,
        )

    active_context, active_model, scuc_audit, iteration_audits = (
        _run_constraint_generation(
            data,
            bound_request,
            points,
            initial_state,
            selection,
            solver_name=solver_name,
            tee=tee,
            tolerance=tolerance,
            solver_threads=solver_threads,
            mip_relative_gap=mip_relative_gap,
            initial_model=prescreen_model,
            initial_audit=prescreen_audit,
        )
    )

    context = _build_context(data, bound_request, points, selection.states)
    model = _build_model(context, fixed_initial=initial_state)
    _fix_commitment_decisions(model, active_model, context)
    sced_audit = _solve(
        model,
        solver_name=solver_name,
        tee=tee,
        tolerance=tolerance,
        solver_threads=solver_threads,
        mip_relative_gap=mip_relative_gap,
    )
    if not sced_audit.accepted:
        raise RuntimeError(
            "RTS-GMLC all-state fixed-commitment SCED was not accepted: "
            f"{sced_audit.termination_condition}"
        )
    relaxed_lower_bound = scuc_audit.lower_bound_usd
    full_feasible_objective = sced_audit.objective_usd
    if relaxed_lower_bound is None or full_feasible_objective is None:
        raise RuntimeError(
            "RTS-GMLC constraint generation did not produce finite gap bounds"
        )
    if full_feasible_objective < relaxed_lower_bound - tolerance:
        raise RuntimeError(
            "RTS-GMLC full-state objective is below its valid lower bound"
        )
    certified_gap = max(full_feasible_objective - relaxed_lower_bound, 0.0)
    if (
        scuc_audit.gap_tolerance_usd is None
        or certified_gap > scuc_audit.gap_tolerance_usd + tolerance
    ):
        raise RuntimeError("RTS-GMLC full-state gap certificate exceeds tolerance")
    constraint_generation_audit = RtsGmlcConstraintGenerationAudit(
        converged=True,
        maximum_refinement_iterations=len(selection.states) - 1,
        iterations=iteration_audits,
        final_active_state_ids=tuple(state.state_id for state in active_context.states),
        pre_registered_state_ids=tuple(state.state_id for state in selection.states),
        verified_state_ids=tuple(state.state_id for state in selection.states),
        relaxed_mip_lower_bound_usd=relaxed_lower_bound,
        full_feasible_objective_usd=full_feasible_objective,
        certified_absolute_gap_usd=certified_gap,
        certified_relative_gap=certified_gap / max(abs(full_feasible_objective), 1.0),
    )
    residual = _audit_solution(model, context, initial_state, tolerance)
    all_residual_flags = (
        residual.commitment_feasible_by_step
        + residual.ramp_feasible_by_step
        + residual.reserve_feasible_by_step
        + residual.normal_secure_by_step
        + residual.contingency_secure_by_step
    )
    if not all(all_residual_flags):
        raise RuntimeError("RTS-GMLC independent residual audit failed")

    commitment = _extract_commitment(model, context)
    normal_generation = _extract_generation(model, context, _NORMAL_STATE_ID)
    normal_branch_flows = _extract_branch_flows(model, context, _NORMAL_STATE_ID)
    normal_dc_flows = _extract_dc_flows(model, context, _NORMAL_STATE_ID)
    reserve_rows = tuple(
        {
            uid: _clean_nonnegative(
                float(value(model.reserve_up[time, uid])),
                f"reserve_up[{time},{uid}]",
            )
            for uid in context.reserve_uids
        }
        for time in range(len(points))
    )
    security_generation = {
        state.state_id: _extract_generation(model, context, state.state_id)
        for state in selection.states
        if state.state_id != _NORMAL_STATE_ID
    }
    security_flows = {
        state.state_id: _extract_branch_flows(model, context, state.state_id)
        for state in selection.states
        if state.state_id != _NORMAL_STATE_ID
    }
    state_ids = tuple(state.state_id for state in selection.states)
    dispatch_scope = (
        "native_rts_gmlc_24h_or_shorter_selected_n_minus_one_pwl_dc_scuc_"
        "constraint_generation_all_pre_registered_states_verified_"
        "fixed_commitment_all_state_sced_"
        "free_boundary_derived_initial_state_fractional_minimum_times_"
        "ceiled_to_hour"
    )
    security_scope = (
        "constraint_generation_all_pre_registered_states_verified_selected_"
        "nonislanding_ac_branch_immediate_and_sustained_plus_largest_thermal_"
        "per_area_dc_n_minus_one_not_full_security_certification"
    )
    dispatch_result = ChronologicalDispatchResult(
        feasible=True,
        timestamps=bound_request.timestamps,
        grid_call_mw=tuple(0.0 for _ in points),
        recovery_power_mw=tuple(0.0 for _ in points),
        dc_power_mw=tuple(_number(item) for item in bound_request.dc_requested_mw),
        generation_mw=normal_generation,
        commitment=commitment,
        load_shed_mw=tuple(0.0 for _ in points),
        network_losses_mw=tuple(0.0 for _ in points),
        commitment_feasible_by_step=residual.commitment_feasible_by_step,
        ramp_feasible_by_step=residual.ramp_feasible_by_step,
        reserve_feasible_by_step=residual.reserve_feasible_by_step,
        normal_secure_by_step=residual.normal_secure_by_step,
        contingency_secure_by_step=residual.contingency_secure_by_step,
        security_state_count_by_step=tuple(len(state_ids) for _ in points),
        checked_security_state_ids_by_step=tuple(state_ids for _ in points),
        termination_condition=sced_audit.termination_condition,
        dispatch_scope=dispatch_scope,
        security_scope=security_scope,
    )
    return RtsGmlcScucResult(
        dispatch_request=bound_request,
        dispatch_result=dispatch_result,
        initial_state=initial_state,
        critical_selection=selection,
        prescreen_audit=prescreen_audit,
        scuc_audit=scuc_audit,
        sced_audit=sced_audit,
        constraint_generation_audit=constraint_generation_audit,
        residual_audit=residual,
        normal_branch_flows_mw=normal_branch_flows,
        normal_dc_flows_mw=normal_dc_flows,
        reserve_up_mw=reserve_rows,
        security_branch_flows_mw=security_flows,
        security_generation_mw=security_generation,
        dispatch_scope=dispatch_scope,
        security_scope=security_scope,
    )
