"""Horizon-level integration boundary for chronological SCUC/SCED evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite
from typing import TYPE_CHECKING, Mapping, Protocol

if TYPE_CHECKING:
    from src.evaluation.chronology_inputs import (
        BusinessChronology,
        GridIncident,
        IncidentChronology,
    )
    from src.evaluation.flexibility_envelope import (
        ChronologicalFlexibilityEnvelope,
        ChronologicalFlexibilityTrace,
    )


@dataclass(frozen=True)
class ChronologicalDispatchRequest:
    timestamps: tuple[datetime, ...]
    periods: tuple[str, ...]
    time_step_hours: float
    system_demand_by_bus_mw: tuple[Mapping[int, float], ...]
    generator_availability: tuple[Mapping[str, bool], ...]
    dc_bus: int
    dc_requested_mw: tuple[float, ...]
    dc_flexible_demand_mw: tuple[float, ...]
    dc_recoverable_flexible_mw: tuple[float, ...]
    dc_physical_maximum_mw: tuple[float, ...]
    dc_connected_capacity_mw: tuple[float, ...]
    dc_call_limit_mw: tuple[float, ...]
    recovery_headroom_mw: tuple[float, ...]
    flexibility_envelope: ChronologicalFlexibilityEnvelope
    flexibility_boundary_state_status: str
    completed_periods: frozenset[str]
    initial_has_prior_event: bool
    initial_recovery_debt_mwh: float
    initial_grid_call_mw: float
    initial_active_event_duration_hours: float
    initial_interevent_rest_hours: float | None
    initial_event_count_by_period: Mapping[str, int]
    initial_curtailment_energy_mwh_by_period: Mapping[str, float]
    require_terminal_event_inactive: bool
    incidents: tuple[GridIncident, ...]
    initial_commitment: Mapping[str, bool]
    initial_generation_mw: Mapping[str, float]
    initial_time_in_state_hours: Mapping[str, float]


@dataclass(frozen=True)
class ChronologicalDispatchResult:
    feasible: bool
    timestamps: tuple[datetime, ...]
    grid_call_mw: tuple[float, ...]
    recovery_power_mw: tuple[float, ...]
    dc_power_mw: tuple[float, ...]
    generation_mw: tuple[Mapping[str, float], ...]
    commitment: tuple[Mapping[str, bool], ...]
    load_shed_mw: tuple[float, ...]
    network_losses_mw: tuple[float, ...]
    commitment_feasible_by_step: tuple[bool, ...]
    ramp_feasible_by_step: tuple[bool, ...]
    reserve_feasible_by_step: tuple[bool, ...]
    normal_secure_by_step: tuple[bool, ...]
    contingency_secure_by_step: tuple[bool, ...]
    security_state_count_by_step: tuple[int, ...]
    checked_security_state_ids_by_step: tuple[tuple[str, ...], ...]
    termination_condition: str
    dispatch_scope: str
    security_scope: str


class ChronologicalDispatchSolver(Protocol):
    def solve(self, request: ChronologicalDispatchRequest) -> ChronologicalDispatchResult:
        """Solve the complete horizon without discarding intertemporal state."""


def build_chronological_dispatch_request(
    business: BusinessChronology,
    incidents: IncidentChronology,
    *,
    system_demand_by_bus_mw: tuple[Mapping[int, float], ...],
    generator_availability: tuple[Mapping[str, bool], ...],
    dc_bus: int,
    contract_call_limit_mw: tuple[float, ...],
    connected_capacity_mw: tuple[float, ...],
    flexibility_envelope: ChronologicalFlexibilityEnvelope,
    flexibility_boundary_state_status: str,
    completed_periods: frozenset[str],
    initial_commitment: Mapping[str, bool],
    initial_generation_mw: Mapping[str, float],
    initial_time_in_state_hours: Mapping[str, float],
    initial_recovery_debt_mwh: float = 0.0,
    initial_has_prior_event: bool = False,
    initial_grid_call_mw: float = 0.0,
    initial_active_event_duration_hours: float = 0.0,
    initial_interevent_rest_hours: float | None = None,
    initial_event_count_by_period: Mapping[str, int] | None = None,
    initial_curtailment_energy_mwh_by_period: Mapping[str, float] | None = None,
    require_terminal_event_inactive: bool = True,
) -> ChronologicalDispatchRequest:
    """Bind sourced business evidence to grid inputs without caller-defined proxies."""

    from src.evaluation.chronology_inputs import (
        validate_incidents_against_business_timeline,
    )

    validate_incidents_against_business_timeline(incidents, business)
    if (
        len(contract_call_limit_mw) != len(business.points)
        or len(connected_capacity_mw) != len(business.points)
    ):
        raise ValueError("Contract inputs must match the business chronology")
    contract_limits = tuple(
        _finite(value, f"contract_call_limit_mw[{index}]", minimum=0.0)
        for index, value in enumerate(contract_call_limit_mw)
    )
    connected_capacity = tuple(
        _finite(value, f"connected_capacity_mw[{index}]", minimum=0.0)
        for index, value in enumerate(connected_capacity_mw)
    )
    for index, (capacity, point) in enumerate(
        zip(connected_capacity, business.points)
    ):
        if capacity < point.requested_demand_mw:
            raise ValueError(
                f"Connected capacity is below dispatched business demand at step {index}"
            )
    if (
        flexibility_envelope.maximum_recovery_power_mw
        != business.recovery.maximum_recovery_power_mw
        or flexibility_envelope.recovery_efficiency
        != business.recovery.recovery_efficiency
    ):
        raise ValueError("Flexibility envelope does not match sourced recovery parameters")
    request = ChronologicalDispatchRequest(
        timestamps=tuple(point.timestamp for point in business.points),
        periods=tuple(point.period for point in business.points),
        time_step_hours=business.time_step_hours,
        system_demand_by_bus_mw=system_demand_by_bus_mw,
        generator_availability=generator_availability,
        dc_bus=dc_bus,
        dc_requested_mw=tuple(point.requested_demand_mw for point in business.points),
        dc_flexible_demand_mw=tuple(
            point.flexible_demand_mw for point in business.points
        ),
        dc_recoverable_flexible_mw=tuple(
            point.recoverable_flexible_mw for point in business.points
        ),
        dc_physical_maximum_mw=tuple(
            point.physical_maximum_demand_mw for point in business.points
        ),
        dc_connected_capacity_mw=connected_capacity,
        dc_call_limit_mw=tuple(
            min(contract_limit, point.recoverable_flexible_mw)
            for contract_limit, point in zip(contract_limits, business.points)
        ),
        recovery_headroom_mw=tuple(
            min(
                point.recovery_headroom_mw,
                capacity - point.requested_demand_mw,
            )
            for point, capacity in zip(business.points, connected_capacity)
        ),
        flexibility_envelope=flexibility_envelope,
        flexibility_boundary_state_status=flexibility_boundary_state_status,
        completed_periods=completed_periods,
        initial_has_prior_event=initial_has_prior_event,
        initial_recovery_debt_mwh=initial_recovery_debt_mwh,
        initial_grid_call_mw=initial_grid_call_mw,
        initial_active_event_duration_hours=initial_active_event_duration_hours,
        initial_interevent_rest_hours=initial_interevent_rest_hours,
        initial_event_count_by_period=dict(initial_event_count_by_period or {}),
        initial_curtailment_energy_mwh_by_period=dict(
            initial_curtailment_energy_mwh_by_period or {}
        ),
        require_terminal_event_inactive=require_terminal_event_inactive,
        incidents=incidents.incidents,
        initial_commitment=initial_commitment,
        initial_generation_mw=initial_generation_mw,
        initial_time_in_state_hours=initial_time_in_state_hours,
    )
    _validate_request(request)
    return request


def dispatch_result_to_flexibility_trace(
    request: ChronologicalDispatchRequest,
    result: ChronologicalDispatchResult,
    *,
    name: str = "chronological_dispatch_business_audit",
) -> ChronologicalFlexibilityTrace:
    """Preserve the dispatcher's call and recovery decisions for business audit."""

    from src.evaluation.flexibility_envelope import ChronologicalFlexibilityTrace

    return ChronologicalFlexibilityTrace(
        name=name,
        timestamps=request.timestamps,
        periods=request.periods,
        grid_call_mw=result.grid_call_mw,
        call_limit_mw=request.dc_call_limit_mw,
        recovery_headroom_mw=request.recovery_headroom_mw,
        boundary_state_status=request.flexibility_boundary_state_status,
        completed_periods=request.completed_periods,
        initial_has_prior_event=request.initial_has_prior_event,
        prescribed_recovery_power_mw=result.recovery_power_mw,
        initial_recovery_debt_mwh=request.initial_recovery_debt_mwh,
        initial_grid_call_mw=request.initial_grid_call_mw,
        initial_active_event_duration_hours=(
            request.initial_active_event_duration_hours
        ),
        initial_interevent_rest_hours=request.initial_interevent_rest_hours,
        initial_event_count_by_period=request.initial_event_count_by_period,
        initial_curtailment_energy_mwh_by_period=(
            request.initial_curtailment_energy_mwh_by_period
        ),
        require_terminal_event_inactive=request.require_terminal_event_inactive,
    )


def _finite(value: object, label: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not isfinite(number) or (minimum is not None and number < minimum):
        qualifier = "finite" if minimum is None else f"finite and at least {minimum}"
        raise ValueError(f"{label} must be {qualifier}")
    return number


def _validate_request(request: ChronologicalDispatchRequest) -> tuple[str, ...]:
    if not request.timestamps:
        raise ValueError("Chronological dispatch horizon must be nonempty")
    if any(timestamp.utcoffset() is None for timestamp in request.timestamps):
        raise ValueError("Dispatch request timestamps must include a UTC offset")
    dt = _finite(request.time_step_hours, "time_step_hours", minimum=0.0)
    if dt <= 0.0:
        raise ValueError("time_step_hours must be positive")
    if any(
        later - earlier != timedelta(hours=dt)
        for earlier, later in zip(request.timestamps, request.timestamps[1:])
    ):
        raise ValueError("Dispatch request timestamps must be continuous")
    lengths = {
        len(request.timestamps),
        len(request.periods),
        len(request.system_demand_by_bus_mw),
        len(request.generator_availability),
        len(request.dc_requested_mw),
        len(request.dc_flexible_demand_mw),
        len(request.dc_recoverable_flexible_mw),
        len(request.dc_physical_maximum_mw),
        len(request.dc_connected_capacity_mw),
        len(request.dc_call_limit_mw),
        len(request.recovery_headroom_mw),
    }
    if len(lengths) != 1:
        raise ValueError("Dispatch request arrays must have equal length")
    if any(not isinstance(period, str) or not period for period in request.periods):
        raise ValueError("Dispatch periods must be nonempty strings")
    if request.flexibility_envelope.time_step_hours != dt:
        raise ValueError("Dispatch and flexibility-envelope time steps must match")
    if isinstance(request.dc_bus, bool) or not isinstance(request.dc_bus, int):
        raise ValueError("dc_bus must be an integer")
    if request.dc_bus < 0:
        raise ValueError("dc_bus must be nonnegative")

    initial_keys = set(request.initial_commitment)
    if not initial_keys:
        raise ValueError("Initial commitment must contain at least one generator")
    if set(request.initial_generation_mw) != initial_keys:
        raise ValueError("Initial generation keys must match initial commitment")
    if set(request.initial_time_in_state_hours) != initial_keys:
        raise ValueError("Initial time-in-state keys must match initial commitment")
    if any(not isinstance(uid, str) or not uid for uid in initial_keys):
        raise ValueError("Generator IDs must be nonempty strings")
    for uid in initial_keys:
        if not isinstance(request.initial_commitment[uid], bool):
            raise ValueError("Initial commitment values must be booleans")
        _finite(request.initial_generation_mw[uid], f"initial generation {uid}", minimum=0.0)
        _finite(
            request.initial_time_in_state_hours[uid],
            f"initial time in state {uid}",
            minimum=0.0,
        )
        if (
            not request.initial_commitment[uid]
            and request.initial_generation_mw[uid] > 0.0
        ):
            raise ValueError(f"Initially offline generator {uid} has positive output")
    for index, availability in enumerate(request.generator_availability):
        if set(availability) != initial_keys:
            raise ValueError(
                f"Generator availability keys at step {index} do not match initial state"
            )
        if any(not isinstance(value, bool) for value in availability.values()):
            raise ValueError("Generator availability values must be booleans")
    for index, demand in enumerate(request.system_demand_by_bus_mw):
        if request.dc_bus not in demand:
            raise ValueError(f"System demand at step {index} omits the DC bus")
        for bus, value in demand.items():
            if isinstance(bus, bool) or not isinstance(bus, int):
                raise ValueError("System-demand bus IDs must be integers")
            _finite(value, f"system demand at step {index}, bus {bus}", minimum=0.0)
    for name, values in (
        ("dc_requested_mw", request.dc_requested_mw),
        ("dc_flexible_demand_mw", request.dc_flexible_demand_mw),
        ("dc_recoverable_flexible_mw", request.dc_recoverable_flexible_mw),
        ("dc_physical_maximum_mw", request.dc_physical_maximum_mw),
        ("dc_connected_capacity_mw", request.dc_connected_capacity_mw),
        ("dc_call_limit_mw", request.dc_call_limit_mw),
        ("recovery_headroom_mw", request.recovery_headroom_mw),
    ):
        for index, value in enumerate(values):
            _finite(value, f"{name}[{index}]", minimum=0.0)
    for index, (
        call_limit,
        recoverable,
        flexible,
        requested,
        physical,
        connected,
        headroom,
    ) in enumerate(
        zip(
            request.dc_call_limit_mw,
            request.dc_recoverable_flexible_mw,
            request.dc_flexible_demand_mw,
            request.dc_requested_mw,
            request.dc_physical_maximum_mw,
            request.dc_connected_capacity_mw,
            request.recovery_headroom_mw,
        )
    ):
        if not (
            call_limit
            <= recoverable
            <= flexible
            <= requested
            <= min(physical, connected)
        ):
            raise ValueError(f"DC business power hierarchy fails at step {index}")
        if headroom > min(physical, connected) - requested:
            raise ValueError(f"DC recovery headroom exceeds deliverable headroom at step {index}")
    boundaries = set(request.timestamps) | {
        request.timestamps[-1] + timedelta(hours=dt)
    }
    active_counts = [0] * len(request.timestamps)
    event_ids = [incident.event_id for incident in request.incidents]
    if len(set(event_ids)) != len(event_ids):
        raise ValueError("Dispatch request contains duplicate incident IDs")
    for incident in request.incidents:
        if (
            not incident.event_id
            or not incident.element_id
            or incident.kind not in {"branch", "generator"}
        ):
            raise ValueError("Dispatch incidents must have valid IDs and kinds")
        if (
            incident.start_timestamp not in boundaries
            or incident.end_timestamp not in boundaries
            or incident.end_timestamp <= incident.start_timestamp
        ):
            raise ValueError(f"Incident {incident.event_id} is not aligned to the horizon")
        for index, timestamp in enumerate(request.timestamps):
            if incident.start_timestamp <= timestamp < incident.end_timestamp:
                active_counts[index] += 1
                if active_counts[index] > 1:
                    raise ValueError("Dispatch request contains overlapping N-1 incidents")
                if incident.kind == "generator":
                    if incident.element_id not in initial_keys:
                        raise ValueError(
                            f"Generator incident {incident.event_id} has an unknown element"
                        )
                    if request.generator_availability[index][incident.element_id]:
                        raise ValueError(
                            f"Generator incident {incident.event_id} is not reflected "
                            "in availability"
                        )
    return tuple(sorted(initial_keys))


def validate_chronological_dispatch(
    request: ChronologicalDispatchRequest,
    result: ChronologicalDispatchResult,
    *,
    tolerance_mw: float = 1.0e-6,
) -> None:
    """Fail closed unless one result preserves the full horizon contract."""

    generator_uids = _validate_request(request)
    tolerance = _finite(tolerance_mw, "tolerance_mw", minimum=0.0)
    if result.timestamps != request.timestamps:
        raise ValueError("Dispatch result timestamps must exactly match the request")
    lengths = {
        len(request.timestamps),
        len(result.grid_call_mw),
        len(result.recovery_power_mw),
        len(result.dc_power_mw),
        len(result.generation_mw),
        len(result.commitment),
        len(result.load_shed_mw),
        len(result.network_losses_mw),
        len(result.commitment_feasible_by_step),
        len(result.ramp_feasible_by_step),
        len(result.reserve_feasible_by_step),
        len(result.normal_secure_by_step),
        len(result.contingency_secure_by_step),
        len(result.security_state_count_by_step),
        len(result.checked_security_state_ids_by_step),
    }
    if len(lengths) != 1:
        raise ValueError("Dispatch result arrays must match the request horizon")
    if not isinstance(result.feasible, bool):
        raise ValueError("Dispatch feasibility flag must be boolean")
    if not result.feasible:
        raise ValueError("Chronological dispatch did not return a feasible result")
    if not result.termination_condition:
        raise ValueError("Dispatch termination condition must be explicit")
    if not result.dispatch_scope or not result.security_scope:
        raise ValueError("Dispatch and security scopes must be explicit")
    boolean_series = {
        "commitment": result.commitment_feasible_by_step,
        "ramp": result.ramp_feasible_by_step,
        "reserve": result.reserve_feasible_by_step,
        "normal security": result.normal_secure_by_step,
        "contingency security": result.contingency_secure_by_step,
    }
    for label, values in boolean_series.items():
        if any(not isinstance(value, bool) for value in values):
            raise ValueError(f"{label.title()} flags must be booleans")
        if not all(values):
            raise ValueError(f"Chronological dispatch contains a {label} failure")

    for index in range(len(request.timestamps)):
        call = _finite(result.grid_call_mw[index], f"grid_call_mw[{index}]", minimum=0.0)
        recovery = _finite(
            result.recovery_power_mw[index],
            f"recovery_power_mw[{index}]",
            minimum=0.0,
        )
        dc_power = _finite(result.dc_power_mw[index], f"dc_power_mw[{index}]", minimum=0.0)
        load_shed = _finite(result.load_shed_mw[index], f"load_shed_mw[{index}]", minimum=0.0)
        losses = _finite(
            result.network_losses_mw[index],
            f"network_losses_mw[{index}]",
            minimum=0.0,
        )
        state_count = result.security_state_count_by_step[index]
        if isinstance(state_count, bool) or not isinstance(state_count, int):
            raise ValueError("Security-state counts must be integers")
        if state_count < 2:
            raise ValueError(
                "Normal state plus at least one contingency must be checked per step"
            )
        state_ids = result.checked_security_state_ids_by_step[index]
        if (
            not isinstance(state_ids, tuple)
            or any(not isinstance(state_id, str) or not state_id for state_id in state_ids)
            or len(set(state_ids)) != len(state_ids)
        ):
            raise ValueError("Checked security-state IDs must be unique nonempty strings")
        if len(state_ids) != state_count or "normal" not in state_ids:
            raise ValueError("Security-state IDs do not match the declared state count")
        active_incident_ids = {
            incident.event_id
            for incident in request.incidents
            if incident.start_timestamp <= request.timestamps[index] < incident.end_timestamp
        }
        if not active_incident_ids.issubset(state_ids):
            raise ValueError(f"Active incident is missing from security checks at step {index}")
        if call > request.dc_call_limit_mw[index] + tolerance:
            raise ValueError(f"Grid call exceeds the business/contract limit at step {index}")
        if recovery > request.recovery_headroom_mw[index] + tolerance:
            raise ValueError(f"Recovery exceeds business headroom at step {index}")
        if (
            recovery
            > request.flexibility_envelope.maximum_recovery_power_mw + tolerance
        ):
            raise ValueError(f"Recovery exceeds the power limit at step {index}")
        if call > tolerance and recovery > tolerance:
            raise ValueError(f"Call and recovery overlap at step {index}")
        expected_dc_power = request.dc_requested_mw[index] - call + recovery
        if abs(dc_power - expected_dc_power) > tolerance:
            raise ValueError(f"DC service balance fails at step {index}")
        if dc_power > request.dc_physical_maximum_mw[index] + tolerance:
            raise ValueError(f"DC power exceeds the physical maximum at step {index}")
        if dc_power > request.dc_connected_capacity_mw[index] + tolerance:
            raise ValueError(f"DC power exceeds connected capacity at step {index}")
        if load_shed > tolerance:
            raise ValueError(f"System load shedding is not allowed at step {index}")

        generation = result.generation_mw[index]
        commitment = result.commitment[index]
        if set(generation) != set(generator_uids) or set(commitment) != set(generator_uids):
            raise ValueError(f"Generator result keys are incomplete at step {index}")
        for uid in generator_uids:
            _finite(generation[uid], f"generation {uid} at step {index}", minimum=0.0)
            if not isinstance(commitment[uid], bool):
                raise ValueError("Commitment values must be booleans")
            if generation[uid] > tolerance and not commitment[uid]:
                raise ValueError(f"Offline generator {uid} produces at step {index}")
            if not request.generator_availability[index][uid] and (
                commitment[uid] or generation[uid] > tolerance
            ):
                raise ValueError(f"Unavailable generator {uid} is used at step {index}")
        total_generation = sum(float(value) for value in generation.values())
        required_generation = (
            sum(float(value) for value in request.system_demand_by_bus_mw[index].values())
            + dc_power
            + losses
        )
        if abs(total_generation - required_generation) > tolerance:
            raise ValueError(f"System power balance fails at step {index}")

    from src.evaluation.flexibility_envelope import evaluate_chronological_flexibility

    flexibility_audit = evaluate_chronological_flexibility(
        dispatch_result_to_flexibility_trace(request, result),
        request.flexibility_envelope,
        tolerance=tolerance,
    )
    if not flexibility_audit.feasible:
        raise ValueError(
            "Chronological dispatch violates the business envelope: "
            f"{list(flexibility_audit.violations)}"
        )
