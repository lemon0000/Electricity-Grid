"""Non-authoritative hourly mechanism model; scalar supply, no F/X certificate.

All rates use MW_c, all task balances MWh_c, and each step is exactly one hour.
The policy receives only the current observation. Old frozen models are untouched.
"""
from dataclasses import asdict, dataclass, is_dataclass, replace
from fractions import Fraction as Q
import json
from pathlib import Path

import yaml

from src.rq2_joint_deliverability_boundary_v1.debt_cohorts import (
    DebtLedger, advance_debt_ledger, assess_debt_cohorts,
)

METHODS = ("instantaneous", "fixed_headroom", "full_temporal")
ZERO = Q(0)


def _integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")


def _quantity(value, name):
    if not isinstance(value, Q) or value < 0:
        raise ValueError(f"{name} must be a nonnegative Fraction")


def _exact(value, name):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must use an exact string quantity")
    return Q(value)


def _keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected.split()):
        raise ValueError("fixture fields differ from the declared mechanism schema")


@dataclass(frozen=True)
class Parameters:
    capacity: Q
    alpha: Q
    eta: Q
    beta: Q
    facility_factor: Q
    auxiliary_mw: Q
    fixed_headroom: Q
    max_recovery: Q
    max_debt: Q
    max_call_energy: Q
    call_ramp: Q
    max_events: int
    max_duration: int
    minimum_rest: int

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if name in ("max_events", "max_duration", "minimum_rest"):
                _integer(value, name)
                if value < 0 or (name == "max_duration" and value == 0):
                    raise ValueError("invalid event envelope")
            else:
                _quantity(value, name)
        if not 0 < self.eta <= 1 or self.alpha > 1:
            raise ValueError("invalid efficiency or CFE target")
        if self.beta <= 0 or self.facility_factor < 1:
            raise ValueError("invalid IT/facility mapping")

    @property
    def slope(self):
        return self.beta * self.facility_factor


@dataclass(frozen=True)
class HourInput:
    hour: int
    due: int
    workload: Q
    flexible_fraction: Q
    compute_capacity: Q
    idle_mw: Q
    clean_mwh: Q
    supply_mw: Q
    equipment_online: tuple[str, ...]
    grid_online: bool

    def __post_init__(self):
        _integer(self.hour, "hour")
        _integer(self.due, "due")
        if self.due < self.hour:
            raise ValueError("deadline precedes task arrival")
        for name in ("workload", "flexible_fraction", "compute_capacity",
                     "idle_mw", "clean_mwh", "supply_mw"):
            _quantity(getattr(self, name), name)
        if self.flexible_fraction > 1:
            raise ValueError("flexible fraction exceeds one")
        if (not isinstance(self.grid_online, bool)
                or not isinstance(self.equipment_online, tuple)
                or any(not isinstance(v, str) or not v for v in self.equipment_online)
                or len(set(self.equipment_online)) != len(self.equipment_online)):
            raise ValueError("explicit equipment and grid states required")


@dataclass(frozen=True)
class StepRecord:
    observation: HourInput
    reference_mw: Q
    grid_request_mw: Q
    cfe_request_mw: Q
    grid_served: Q
    cfe_served: Q
    recovery: Q
    allocations: tuple[tuple[int, Q], ...]  # physical birth hour, effective work
    activity: Q
    power_mw: Q
    attributed_clean_mwh: Q
    grid_shortfall_mw: Q
    cfe_call_shortfall_mw: Q
    cfe_shortfall_mwh: Q
    violations: tuple[str, ...]
    ledger_applied: bool  # Hypothetical schedule only for the two approximations.

    @property
    def deferred(self):
        return self.grid_served + self.cfe_served


@dataclass(frozen=True)
class StageState:
    method: str
    first_hour: int
    trajectory_id: str
    ledger: DebtLedger
    records: tuple[StepRecord, ...] = ()
    call_energy: Q = ZERO
    previous_call: Q = ZERO
    events: int = 0
    duration: int = 0
    rest: int = 0
    stopped: bool = False
    parameters: Parameters | None = None

    @property
    def hour_offset(self):
        # The legacy ledger requires nonnegative hours, including initial hour 0.
        return 1 - self.first_hour

    @property
    def next_hour(self):
        return self.ledger.last_hour + 1 - self.hour_offset


def initialize(params, method, trajectory_id, first_hour=-2):
    if method not in METHODS or not isinstance(trajectory_id, str) or not trajectory_id:
        raise ValueError("explicit method and trajectory required")
    _integer(first_hour, "first_hour")
    return StageState(method, first_hour, trajectory_id,
                      DebtLedger(trajectory_id, "continuous_case", 0),
                      rest=params.minimum_rest, parameters=params)


def power_mapping(params, observation, deferred=ZERO, recovery=ZERO):
    """Return activity, IT load and meter load; idle remains when activity is zero."""
    for name, value in (("deferred", deferred), ("recovery", recovery)):
        _quantity(value, name)
    activity = observation.workload - deferred + recovery
    it = observation.idle_mw + params.beta * activity
    return activity, it, params.facility_factor * it + params.auxiliary_mw


def advance(params, state, observation):
    """One causal step; approximate methods retain diagnostic, not physical, plans."""
    if state.parameters != params:
        raise ValueError("parameters changed within trajectory")
    if state.stopped or observation.hour != state.next_hour:
        raise ValueError("stopped or nonconsecutive trajectory")
    o, p = observation, params
    _, _, reference = power_mapping(p, o)
    grid = max(reference - o.supply_mw, ZERO)
    green = max(reference - o.clean_mwh / p.alpha, ZERO) if p.alpha else ZERO
    room = min(p.capacity, o.workload * o.flexible_fraction, o.workload,
               max(p.max_call_energy - state.call_energy, ZERO),
               max(p.max_debt - state.ledger.debt, ZERO),
               state.previous_call + p.call_ramp)
    if ((state.duration >= p.max_duration)
            or (not state.previous_call and
                (state.rest < p.minimum_rest or state.events >= p.max_events))):
        room = ZERO
    if state.method == "instantaneous":
        room = min(p.capacity, o.workload * o.flexible_fraction, o.workload)
    grid_served = min(grid / p.slope, room)
    cfe_served = min(green / p.slope, room - grid_served)
    q = grid_served + cfe_served
    recovery, allocations = ZERO, []
    if grid + green == 0 and state.method != "instantaneous":
        limit = min(p.capacity, p.max_recovery, state.ledger.debt / p.eta)
        if state.method == "fixed_headroom":
            limit = min(limit, p.fixed_headroom)
        else:
            limit = min(limit, max(o.compute_capacity - o.workload, ZERO),
                        max((o.supply_mw - reference) / p.slope, ZERO))
            if p.alpha:
                limit = min(limit, max((o.clean_mwh / p.alpha - reference) / p.slope, ZERO))
        for cohort in sorted(state.ledger.cohorts,
                             key=lambda c: (c.due_hour, c.created_hour)):
            effective = min(cohort.remaining, max(limit - recovery, ZERO) * p.eta)
            if effective:
                allocations.append((cohort.created_hour - state.hour_offset, effective))
                recovery += effective / p.eta
    activity, _, power = power_mapping(p, o, q, recovery)
    events = state.events + int(q > 0 and state.previous_call == 0)
    duration = state.duration + 1 if q else 0
    energy = state.call_energy + q
    grid_short = grid - p.slope * grid_served
    green_short = green - p.slope * cfe_served
    cfe_short = max(p.alpha * power - o.clean_mwh, ZERO)
    violations = []
    for failed, code in (
        (grid_short > 0, "grid_service_shortfall"),
        (green_short > 0, "cfe_call_shortfall"),
        (activity < 0 or activity > o.compute_capacity, "device_capacity"),
        (power > o.supply_mw, "scalar_supply"),
        (cfe_short > 0, "hourly_cfe"),
        (abs(q - state.previous_call) > p.call_ramp, "call_ramp"),
        (events > p.max_events or duration > p.max_duration or
         (q > 0 and not state.previous_call and state.rest < p.minimum_rest), "event_envelope"),
        (energy > p.max_call_energy, "call_energy"),
        (state.ledger.debt + q - p.eta * recovery > p.max_debt, "recovery_debt"),
    ):
        if failed:
            violations.append(code)
    # A failed mandatory/physical step is an attempted action, not completed work.
    blocking = set(violations) - {"hourly_cfe", "cfe_call_shortfall"}
    committed = not (state.method == "full_temporal" and blocking)
    ledger = state.ledger
    if committed:
        ledger = advance_debt_ledger(
            ledger, hour=o.hour + state.hour_offset,
            trajectory_identity=state.trajectory_id, accounting_period_id="continuous_case",
            incurred=q, due_hour=o.due + state.hour_offset if q else None,
            deadline_evidence="mechanism_assumption" if q else "unidentified",
            allocations=tuple((birth + state.hour_offset, amount) for birth, amount in allocations),
        )
    record = StepRecord(o, reference, grid, green, grid_served, cfe_served,
                        recovery, tuple(allocations), activity, power,
                        min(o.clean_mwh, max(power, ZERO)), grid_short,
                        green_short, cfe_short, tuple(violations), committed)
    if not committed:
        return replace(state, records=state.records + (record,), stopped=True)
    return replace(state, ledger=ledger, records=state.records + (record,),
                   call_energy=energy, previous_call=q, events=events, duration=duration,
                   rest=0 if q else state.rest + 1)


def execute(params, observations, method="full_temporal", trajectory_id="mechanism", state=None):
    if state is None:
        if not observations:
            raise ValueError("nonempty observations required")
        state = initialize(params, method, trajectory_id, observations[0].hour)
    for observation in observations:
        state = advance(params, state, observation)
        if state.stopped:
            break
    return state


def task_balances(state):
    """Include every arrived task, even those never deferred; exclude failed attempts."""
    cohorts = {c.created_hour - state.hour_offset: c for c in state.ledger.cohorts}
    statuses = dict(assess_debt_cohorts(state.ledger))
    rows = []
    for record in state.records:
        if not record.ledger_applied:
            continue
        o, q = record.observation, record.deferred
        cohort = cohorts.get(o.hour)
        remaining = cohort.remaining if cohort else ZERO
        recovered = q - remaining
        rows.append(dict(birth=o.hour, due=o.due, original=o.workload,
                         balance_scope="scalar_policy_execution" if state.method == "full_temporal"
                         else "hypothetical_approximation",
                         immediate=o.workload - q, recovered=recovered, remaining=remaining,
                         deadline_miss=cohort.missed_at_deadline if cohort else ZERO,
                         status=statuses[cohort.created_hour] if cohort else "completed_on_arrival"))
    return tuple(rows)


def assessment(state, registration_end=4, expected_last_hour=7):
    tasks = task_balances(state)
    primary = [r for r in tasks if 0 <= r["birth"] < registration_end]
    missed = sum((r["deadline_miss"] or ZERO for r in primary), ZERO)
    censored = any(r["status"] == "right_censored_before_deadline" for r in primary)
    instant_codes = {"grid_service_shortfall", "cfe_call_shortfall", "device_capacity",
                     "scalar_supply", "hourly_cfe"}
    # Constant headroom deliberately omits actual recovery-resource checks.
    relevant = [v for r in state.records for v in r.violations
                if not (state.method == "fixed_headroom" and r.recovery
                        and v in {"device_capacity", "scalar_supply", "hourly_cfe"})]
    if state.method == "instantaneous":
        satisfied = not any(v in instant_codes for v in relevant)
        label = "instantaneous_conditions_only"
    else:
        satisfied = not relevant and not missed and not state.stopped
        label = "constant_headroom_approximation" if state.method == "fixed_headroom" else "scalar_fixed_policy"
    complete = not state.stopped and state.next_hour - 1 >= expected_last_hour
    if satisfied and (not complete or (censored and state.method != "instantaneous")):
        satisfied = None
    return dict(method=state.method, scope=label, method_conditions_satisfied=satisfied,
                coverage_complete=complete, observed_through=state.next_hour - 1,
                observed_primary_deadline_miss=missed, primary_right_censored=censored,
                stopped=state.stopped, remaining_debt=state.ledger.debt,
                physical_replay_violations=tuple((r.observation.hour, r.violations)
                                                  for r in state.records if r.violations),
                fx_contract_status="not_assessed_scalar_stub")


def plain(value):
    if isinstance(value, Q):
        return str(value)
    if is_dataclass(value):
        return plain(asdict(value))
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def checkpoint_payload(params, state):
    return dict(schema="staged_mechanism_checkpoint_v1", status="DRAFT_NONAUTHORITATIVE",
                parameters=plain(params), state=plain(state),
                observations=plain(tuple(r.observation for r in state.records)))


def save_checkpoint(path, params, state):
    data = json.dumps(checkpoint_payload(params, state), sort_keys=True, indent=2,
                      allow_nan=False)
    if len(data.encode("utf-8")) > 1024 * 1024:
        raise ValueError("development checkpoint exceeds 1 MiB")
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(data + "\n")


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read_checkpoint(path, params, expected_prefix, method, trajectory_id):
    """Replay a caller-bound prefix; no untrusted deserialization or future input.

    This performs len(expected_prefix) EXTRA policy steps, explicitly budgeted.
    It verifies local deterministic replay, not production publication/authenticity.
    """
    path = Path(path)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("development checkpoint exceeds 1 MiB")
    saved = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs,
                       parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
    if not isinstance(saved, dict) or saved.get("observations") != plain(expected_prefix):
        raise ValueError("checkpoint differs from caller-bound observed prefix")
    state = execute(params, expected_prefix, method, trajectory_id)
    if json.dumps(saved, sort_keys=True) != json.dumps(checkpoint_payload(params, state), sort_keys=True):
        raise ValueError("checkpoint differs from caller-bound deterministic replay")
    return state


def load_small_case(path, plan="on_time", clean="early"):
    """Build current-hour observations from the declared mechanism fixture only."""
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    _keys(cfg, "status source_class first_hour last_hour deadline_lag flexible_fraction prehistory_clean parameters equipment workload grid clean_paths")
    _keys(cfg["workload"], "before after change_hour")
    _keys(cfg["grid"], "start lead delays before after temporary_hour temporary_limit")
    _keys(cfg["grid"]["delays"], "on_time delayed")
    _keys(cfg["clean_paths"], "early late")
    for m in cfg["equipment"]:
        _keys(m, "id capacity idle_mw start lead delay")
        _exact(m["capacity"], "module capacity")
        _exact(m["idle_mw"], "module idle")
    for name in ("before", "after"):
        _exact(cfg["workload"][name], name)
        _exact(cfg["grid"][name], name)
    for values in cfg["clean_paths"].values():
        if not isinstance(values, list):
            raise ValueError("clean path must be an hourly list")
        for value in values:
            _exact(value, "clean")
    if cfg["status"] != "DRAFT_NONAUTHORITATIVE" or cfg["source_class"] != "mechanism_assumption":
        raise ValueError("development-only fixture required")
    for name in ("first_hour", "last_hour", "deadline_lag"):
        _integer(cfg[name], name)
    if cfg["first_hour"] > cfg["last_hour"] or cfg["deadline_lag"] < 0:
        raise ValueError("invalid observation window/deadline lag")
    for name in ("change_hour",):
        _integer(cfg["workload"][name], name)
    _integer(cfg["grid"]["temporary_hour"], "temporary_hour")
    raw = cfg["parameters"]
    if any(not isinstance(v, str) for k, v in raw.items()
           if k not in ("max_events", "max_duration", "minimum_rest")):
        raise ValueError("physical parameters must use exact string quantities")
    params = Parameters(**{k: v if k in ("max_events", "max_duration", "minimum_rest")
                           else _exact(v, k) for k, v in raw.items()})
    delay = cfg["grid"]["delays"][plan]
    for value in cfg["grid"]["delays"].values():
        _integer(value, "grid delay")
    for asset in [*cfg["equipment"], dict(cfg["grid"], delay=delay)]:
        for name in ("start", "lead", "delay"):
            _integer(asset[name], name)
        if asset["lead"] < 0 or asset["delay"] < 0:
            raise ValueError("negative construction duration/delay")
    clean_values = cfg["clean_paths"][clean]
    if len(clean_values) != cfg["last_hour"] + 1:
        raise ValueError("incomplete hourly clean path")
    observations = []
    for hour in range(cfg["first_hour"], cfg["last_hour"] + 1):
        online = [m for m in cfg["equipment"]
                  if hour >= m["start"] + m["lead"] + m["delay"]]
        commissioned = hour >= cfg["grid"]["start"] + cfg["grid"]["lead"] + delay
        w = _exact(cfg["workload"]["before"] if hour < cfg["workload"]["change_hour"]
                   else cfg["workload"]["after"], "workload")
        supply = _exact(cfg["grid"]["after"] if commissioned else cfg["grid"]["before"], "supply")
        if hour == cfg["grid"]["temporary_hour"]:
            supply = min(supply, _exact(cfg["grid"]["temporary_limit"], "temporary_limit"))
        observations.append(HourInput(
            hour, min(hour + cfg["deadline_lag"], cfg["last_hour"]) if hour >= 0 else hour,
            w, _exact(cfg["flexible_fraction"], "flexible_fraction"),
            sum((_exact(m["capacity"], "module capacity") for m in online), ZERO),
            sum((_exact(m["idle_mw"], "module idle") for m in online), ZERO),
            _exact(clean_values[hour], "clean") if hour >= 0 else _exact(cfg["prehistory_clean"], "prehistory_clean"),
            supply, tuple(m["id"] for m in online), commissioned,
        ))
    return params, tuple(observations)
