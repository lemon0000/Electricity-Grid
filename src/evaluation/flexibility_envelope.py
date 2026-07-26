"""Chronological audit of a fixed recoverable-flexibility call trace."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite
from numbers import Integral, Real
from typing import Mapping


@dataclass(frozen=True)
class ChronologicalFlexibilityEnvelope:
    time_step_hours: float
    maximum_event_duration_hours: float
    minimum_recovery_hours: float
    maximum_events_by_period: Mapping[str, int]
    maximum_curtailment_energy_mwh_by_period: Mapping[str, float]
    maximum_recovery_debt_mwh: float
    maximum_recovery_power_mw: float
    minimum_event_power_mw: float
    response_time_hours: float
    curtailment_ramp_mw_per_hour: float
    recovery_efficiency: float
    terminal_debt_limit_mwh_by_period: Mapping[str, float]
    parameter_status: str


@dataclass(frozen=True)
class ChronologicalFlexibilityTrace:
    name: str
    timestamps: tuple[datetime, ...]
    periods: tuple[str, ...]
    grid_call_mw: tuple[float, ...]
    call_limit_mw: tuple[float, ...]
    recovery_headroom_mw: tuple[float, ...]
    boundary_state_status: str
    completed_periods: frozenset[str]
    initial_has_prior_event: bool
    prescribed_recovery_power_mw: tuple[float, ...] | None = None
    initial_recovery_debt_mwh: float = 0.0
    initial_grid_call_mw: float = 0.0
    initial_active_event_duration_hours: float = 0.0
    initial_interevent_rest_hours: float | None = None
    initial_event_count_by_period: Mapping[str, int] = field(default_factory=dict)
    initial_curtailment_energy_mwh_by_period: Mapping[str, float] = field(
        default_factory=dict
    )
    require_terminal_event_inactive: bool = True


@dataclass(frozen=True)
class ChronologicalFlexibilityResult:
    feasible: bool
    violations: tuple[str, ...]
    feasible_by_period: dict[str, bool]
    violations_by_period: dict[str, tuple[str, ...]]
    event_count_by_period: dict[str, int]
    curtailment_energy_mwh_by_period: dict[str, float]
    terminal_recovery_debt_mwh_by_period: dict[str, float]
    maximum_event_duration_hours: float
    minimum_interevent_recovery_hours: float | None
    peak_recovery_debt_mwh: float
    terminal_recovery_debt_mwh: float
    terminal_grid_call_mw: float
    terminal_active_event_duration_hours: float
    terminal_interevent_rest_hours: float | None
    terminal_has_prior_event: bool
    recovery_power_mw: tuple[float, ...]
    effective_recovery_power_mw: tuple[float, ...]
    recovery_debt_mwh: tuple[float, ...]


def _finite_number(name: str, value: object, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    number = float(value)
    if number < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return number


def _positive_number(name: str, value: object) -> float:
    number = _finite_number(name, value)
    if number <= 0.0:
        raise ValueError(f"{name} must be positive")
    return number


def _validate_period_mapping(
    name: str,
    values: Mapping[str, object],
    periods: tuple[str, ...],
) -> None:
    expected = set(periods)
    actual = set(values)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(
            f"{name} keys must match trace periods; missing={missing}, extra={extra}"
        )


def evaluate_chronological_flexibility(
    trace: ChronologicalFlexibilityTrace,
    envelope: ChronologicalFlexibilityEnvelope,
    *,
    tolerance: float = 1.0e-6,
) -> ChronologicalFlexibilityResult:
    """Audit one continuous fixed call trace and schedule recovery greedily.

    With fixed calls and no cost on recovery, using all available recovery
    headroom as early as possible weakly reduces debt at every later step. The
    resulting schedule is therefore feasible whenever any recovery schedule is
    feasible under the modeled power, debt, and terminal limits.
    """

    if not trace.name:
        raise ValueError("Trace name must be explicit")
    if trace.boundary_state_status not in {
        "clean_boundary_with_zero_carry_in",
        "linked_from_previous_window",
    }:
        raise ValueError("Trace boundary-state status must be explicit")
    if not envelope.parameter_status:
        raise ValueError("Envelope parameter status must be explicit")
    dt = _positive_number("time_step_hours", envelope.time_step_hours)
    max_duration = _positive_number(
        "maximum_event_duration_hours",
        envelope.maximum_event_duration_hours,
    )
    min_recovery = _finite_number(
        "minimum_recovery_hours", envelope.minimum_recovery_hours
    )
    max_debt = _finite_number(
        "maximum_recovery_debt_mwh", envelope.maximum_recovery_debt_mwh
    )
    max_recovery_power = _finite_number(
        "maximum_recovery_power_mw", envelope.maximum_recovery_power_mw
    )
    min_event_power = _positive_number(
        "minimum_event_power_mw", envelope.minimum_event_power_mw
    )
    response_time = _positive_number(
        "response_time_hours", envelope.response_time_hours
    )
    ramp = _positive_number(
        "curtailment_ramp_mw_per_hour",
        envelope.curtailment_ramp_mw_per_hour,
    )
    recovery_efficiency = _positive_number(
        "recovery_efficiency", envelope.recovery_efficiency
    )
    if recovery_efficiency > 1.0:
        raise ValueError("recovery_efficiency cannot exceed 1")
    tolerance = _finite_number("tolerance", tolerance)
    initial_debt = _finite_number(
        "initial_recovery_debt_mwh", trace.initial_recovery_debt_mwh
    )
    initial_call = _finite_number("initial_grid_call_mw", trace.initial_grid_call_mw)
    initial_active_duration = _finite_number(
        "initial_active_event_duration_hours",
        trace.initial_active_event_duration_hours,
    )
    initial_rest = (
        None
        if trace.initial_interevent_rest_hours is None
        else _finite_number(
            "initial_interevent_rest_hours", trace.initial_interevent_rest_hours
        )
    )
    if not isinstance(trace.require_terminal_event_inactive, bool):
        raise ValueError("require_terminal_event_inactive must be boolean")
    if not isinstance(trace.initial_has_prior_event, bool):
        raise ValueError("initial_has_prior_event must be boolean")
    if initial_call > tolerance:
        if not trace.initial_has_prior_event:
            raise ValueError("Active carry-in requires prior-event state")
        if initial_active_duration <= 0.0:
            raise ValueError("An active carry-in event must have positive duration")
        if initial_rest is not None:
            raise ValueError("An active carry-in event cannot also have rest time")
    elif initial_active_duration > 0.0:
        raise ValueError("Inactive carry-in state cannot have active-event duration")
    if trace.boundary_state_status == "clean_boundary_with_zero_carry_in" and (
        initial_debt > tolerance
        or initial_call > tolerance
        or initial_active_duration > tolerance
        or initial_rest is not None
        or trace.initial_has_prior_event
        or trace.initial_event_count_by_period
        or trace.initial_curtailment_energy_mwh_by_period
    ):
        raise ValueError("Clean trace boundary cannot contain carry-in state")
    if (
        not trace.initial_has_prior_event
        and (
            initial_debt > tolerance
            or any(value > 0 for value in trace.initial_event_count_by_period.values())
            or any(
                value > tolerance
                for value in trace.initial_curtailment_energy_mwh_by_period.values()
            )
        )
    ):
        raise ValueError("Carry-in history requires prior-event state")
    if (
        trace.boundary_state_status == "linked_from_previous_window"
        and initial_call <= tolerance
        and trace.initial_has_prior_event
        and initial_rest is None
    ):
        raise ValueError(
            "Linked inactive boundary must carry explicit interevent rest time"
        )
    if (
        initial_call <= tolerance
        and not trace.initial_has_prior_event
        and initial_rest is not None
    ):
        raise ValueError("Rest time is undefined when no prior event exists")

    lengths = {
        len(trace.timestamps),
        len(trace.periods),
        len(trace.grid_call_mw),
        len(trace.call_limit_mw),
        len(trace.recovery_headroom_mw),
    }
    if trace.prescribed_recovery_power_mw is not None:
        lengths.add(len(trace.prescribed_recovery_power_mw))
    if lengths == {0}:
        raise ValueError("Chronological trace must be nonempty")
    if len(lengths) != 1:
        raise ValueError("Chronological trace arrays must have equal length")
    if any(not isinstance(period, str) or not period for period in trace.periods):
        raise ValueError("Trace periods must be nonempty strings")
    ordered_periods = tuple(dict.fromkeys(trace.periods))
    if not isinstance(trace.completed_periods, frozenset):
        raise ValueError("completed_periods must be a frozenset")
    unknown_completed_periods = set(trace.completed_periods) - set(ordered_periods)
    if unknown_completed_periods:
        raise ValueError(
            "completed_periods contains unknown periods: "
            f"{sorted(unknown_completed_periods)}"
        )
    for period in ordered_periods:
        indices = [
            index for index, candidate in enumerate(trace.periods)
            if candidate == period
        ]
        if indices != list(range(indices[0], indices[-1] + 1)):
            raise ValueError("Each trace period must form one contiguous block")
    expected_seconds = dt * 3600.0
    for earlier, later in zip(trace.timestamps, trace.timestamps[1:]):
        if abs((later - earlier).total_seconds() - expected_seconds) > 1.0e-6:
            raise ValueError("Trace timestamps must be continuous at time_step_hours")

    _validate_period_mapping(
        "maximum_events_by_period",
        envelope.maximum_events_by_period,
        ordered_periods,
    )
    _validate_period_mapping(
        "maximum_curtailment_energy_mwh_by_period",
        envelope.maximum_curtailment_energy_mwh_by_period,
        ordered_periods,
    )
    terminal_periods = set(envelope.terminal_debt_limit_mwh_by_period)
    unknown_terminal_periods = terminal_periods - set(ordered_periods)
    if unknown_terminal_periods:
        raise ValueError(
            "terminal_debt_limit_mwh_by_period contains unknown periods: "
            f"{sorted(unknown_terminal_periods)}"
        )
    for name, values in (
        ("initial_event_count_by_period", trace.initial_event_count_by_period),
        (
            "initial_curtailment_energy_mwh_by_period",
            trace.initial_curtailment_energy_mwh_by_period,
        ),
    ):
        unknown = set(values) - set(ordered_periods)
        if unknown:
            raise ValueError(f"{name} contains unknown periods: {sorted(unknown)}")

    maximum_events = {}
    maximum_energy = {}
    terminal_limits = {}
    for period in ordered_periods:
        event_limit = envelope.maximum_events_by_period[period]
        if isinstance(event_limit, bool) or not isinstance(event_limit, Integral):
            raise ValueError("Maximum event counts must be integers")
        if event_limit < 0:
            raise ValueError("Maximum event counts must be nonnegative")
        maximum_events[period] = int(event_limit)
        maximum_energy[period] = _finite_number(
            f"maximum_curtailment_energy_mwh_by_period[{period}]",
            envelope.maximum_curtailment_energy_mwh_by_period[period],
        )
        if period in envelope.terminal_debt_limit_mwh_by_period:
            terminal_limits[period] = _finite_number(
                f"terminal_debt_limit_mwh_by_period[{period}]",
                envelope.terminal_debt_limit_mwh_by_period[period],
            )

    calls = tuple(
        _finite_number(f"grid_call_mw[{index}]", call)
        for index, call in enumerate(trace.grid_call_mw)
    )
    call_limits = tuple(
        _finite_number(f"call_limit_mw[{index}]", limit)
        for index, limit in enumerate(trace.call_limit_mw)
    )
    headroom = tuple(
        _finite_number(f"recovery_headroom_mw[{index}]", limit)
        for index, limit in enumerate(trace.recovery_headroom_mw)
    )
    prescribed_recovery = (
        None
        if trace.prescribed_recovery_power_mw is None
        else tuple(
            _finite_number(f"prescribed_recovery_power_mw[{index}]", power)
            for index, power in enumerate(trace.prescribed_recovery_power_mw)
        )
    )

    violations: list[str] = []
    period_violations: dict[str, list[str]] = {
        period: [] for period in ordered_periods
    }
    event_count = {period: 0 for period in ordered_periods}
    for period, value in trace.initial_event_count_by_period.items():
        if isinstance(value, bool) or not isinstance(value, Integral) or value < 0:
            raise ValueError("Initial event counts must be nonnegative integers")
        event_count[period] = int(value)
    energy = {period: 0.0 for period in ordered_periods}
    for period, value in trace.initial_curtailment_energy_mwh_by_period.items():
        energy[period] = _finite_number(
            f"initial_curtailment_energy_mwh_by_period[{period}]", value
        )
    recovery_power: list[float] = []
    effective_recovery_power: list[float] = []
    debt_path: list[float] = []
    debt = initial_debt
    peak_debt = initial_debt
    previous_call = initial_call
    active_duration = initial_active_duration
    maximum_active_duration = initial_active_duration
    interevent_rest = initial_rest
    has_prior_event = trace.initial_has_prior_event
    interevent_recovery_hours: list[float] = []
    if initial_debt > max_debt + tolerance:
        code = "initial_recovery_debt_exceeds_maximum"
        violations.append(code)
        period_violations[ordered_periods[0]].append(code)
    if initial_active_duration > max_duration + tolerance:
        code = "initial_event_duration_exceeds_maximum"
        violations.append(code)
        period_violations[ordered_periods[0]].append(code)

    for index, (period, call, limit, available_headroom) in enumerate(
        zip(trace.periods, calls, call_limits, headroom)
    ):
        active = call > tolerance
        previously_active = previous_call > tolerance
        if call > limit + tolerance:
            code = f"call_limit_exceeded_at_step_{index}"
            violations.append(code)
            period_violations[period].append(code)
        if active and call + tolerance < min_event_power:
            code = f"minimum_event_power_violated_at_step_{index}"
            violations.append(code)
            period_violations[period].append(code)

        increase = max(call - previous_call, 0.0)
        if increase > ramp * dt + tolerance:
            code = f"curtailment_ramp_exceeded_at_step_{index}"
            violations.append(code)
            period_violations[period].append(code)
        if increase > ramp * response_time + tolerance:
            code = f"response_deadline_exceeded_at_step_{index}"
            violations.append(code)
            period_violations[period].append(code)

        if active and not previously_active:
            has_prior_event = True
            event_count[period] += 1
            if interevent_rest is not None:
                interevent_recovery_hours.append(interevent_rest)
                if interevent_rest + tolerance < min_recovery:
                    code = (
                        f"minimum_interevent_recovery_violated_at_step_{index}"
                    )
                    violations.append(code)
                    period_violations[period].append(code)
            interevent_rest = None
        if active:
            active_duration = active_duration + dt if previously_active else dt
            maximum_active_duration = max(maximum_active_duration, active_duration)
            if active_duration > max_duration + tolerance:
                code = f"maximum_event_duration_exceeded_at_step_{index}"
                violations.append(code)
                period_violations[period].append(code)
        else:
            active_duration = 0.0
            if previously_active:
                interevent_rest = dt
            elif interevent_rest is not None:
                interevent_rest += dt

        energy[period] += call * dt
        debt += call * dt
        if prescribed_recovery is not None:
            requested_recovery = prescribed_recovery[index]
            recovery_is_valid = True
            if active and requested_recovery > tolerance:
                code = f"recovery_during_active_call_at_step_{index}"
                violations.append(code)
                period_violations[period].append(code)
                recovery_is_valid = False
            if requested_recovery > max_recovery_power + tolerance:
                code = f"recovery_power_exceeded_at_step_{index}"
                violations.append(code)
                period_violations[period].append(code)
                recovery_is_valid = False
            if requested_recovery > available_headroom + tolerance:
                code = f"recovery_headroom_exceeded_at_step_{index}"
                violations.append(code)
                period_violations[period].append(code)
                recovery_is_valid = False
            if requested_recovery * recovery_efficiency * dt > debt + tolerance:
                code = f"recovery_exceeds_debt_at_step_{index}"
                violations.append(code)
                period_violations[period].append(code)
                recovery_is_valid = False
            recovery = requested_recovery if recovery_is_valid else 0.0
        elif active:
            requested_recovery = 0.0
            recovery = 0.0
        else:
            recovery = min(
                max_recovery_power,
                available_headroom,
                debt / (recovery_efficiency * dt),
            )
            requested_recovery = recovery
        debt = max(debt - recovery_efficiency * recovery * dt, 0.0)
        peak_debt = max(peak_debt, debt)
        if debt > max_debt + tolerance:
            code = f"maximum_recovery_debt_exceeded_at_step_{index}"
            violations.append(code)
            period_violations[period].append(code)
        recovery_power.append(requested_recovery)
        effective_recovery_power.append(recovery)
        debt_path.append(debt)

        is_period_end = index == len(calls) - 1 or trace.periods[index + 1] != period
        period_is_complete = index < len(calls) - 1 or period in trace.completed_periods
        if (
            is_period_end
            and period_is_complete
            and period in terminal_limits
        ):
            if debt > terminal_limits[period] + tolerance:
                code = f"terminal_debt_exceeded_for_period_{period}"
                violations.append(code)
                period_violations[period].append(code)
        previous_call = call

    terminal_debt_by_period = {}
    for index, period in enumerate(trace.periods):
        if index == len(calls) - 1 or trace.periods[index + 1] != period:
            terminal_debt_by_period[period] = debt_path[index]
    if previous_call > tolerance and trace.require_terminal_event_inactive:
        code = "trace_ends_during_active_event"
        violations.append(code)
        period_violations[trace.periods[-1]].append(code)
    for period in ordered_periods:
        if event_count[period] > maximum_events[period]:
            code = f"maximum_events_exceeded_for_period_{period}"
            violations.append(code)
            period_violations[period].append(code)
        if energy[period] > maximum_energy[period] + tolerance:
            code = f"maximum_curtailment_energy_exceeded_for_period_{period}"
            violations.append(code)
            period_violations[period].append(code)

    return ChronologicalFlexibilityResult(
        feasible=not violations,
        violations=tuple(dict.fromkeys(violations)),
        feasible_by_period={
            period: not period_violations[period] for period in ordered_periods
        },
        violations_by_period={
            period: tuple(dict.fromkeys(period_violations[period]))
            for period in ordered_periods
        },
        event_count_by_period=event_count,
        curtailment_energy_mwh_by_period=energy,
        terminal_recovery_debt_mwh_by_period=terminal_debt_by_period,
        maximum_event_duration_hours=maximum_active_duration,
        minimum_interevent_recovery_hours=(
            min(interevent_recovery_hours) if interevent_recovery_hours else None
        ),
        peak_recovery_debt_mwh=peak_debt,
        terminal_recovery_debt_mwh=debt,
        terminal_grid_call_mw=previous_call,
        terminal_active_event_duration_hours=active_duration,
        terminal_interevent_rest_hours=interevent_rest,
        terminal_has_prior_event=has_prior_event,
        recovery_power_mw=tuple(recovery_power),
        effective_recovery_power_mw=tuple(effective_recovery_power),
        recovery_debt_mwh=tuple(debt_path),
    )
