"""Draft audit-side normal-plan preparation and isolated current-hour inputs.

The declared forecast is a mechanism input, not evidence of a real forecast.
This module neither solves dispatch nor generates a grid request.
"""
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path

from .continuous_grid_normal import (
    ContinuousNormalInputs, audit_normal_assignment, normal_input_identity, _digest)


CONTRACT = 'declared_pre_episode_normal_plan__separate_current_conditions_v1'


def _number(x):
    if type(x) not in (int, float) or not isfinite(x):
        raise ValueError('finite built-in number required')
    return x


def _hour(x):
    if type(x) is not int or x < 0:
        raise ValueError('nonnegative integer source hour required')


def _rows(rows, key_type):
    if (type(rows) is not tuple or not rows
            or any(type(r) is not tuple or len(r) != 2 or type(r[0]) is not key_type for r in rows)):
        raise ValueError('immutable typed current inventory required')
    names = tuple(key for key, _ in rows)
    if names != tuple(sorted(set(names))):
        raise ValueError('unique sorted current inventory required')
    for _, number in rows:
        if _number(number) < 0:
            raise ValueError('nonnegative current quantity required')


class _Owned:
    def __init__(self, *args, **kwargs):
        raise TypeError('grid information output requires audited preparation')


def _owned(cls, **values):
    result = object.__new__(cls)
    for name, value in values.items():
        object.__setattr__(result, name, value)
    return result


@dataclass(frozen=True)
class PlanInformationDeclaration:
    issued_at_source_hour: int
    forecast_rule: str
    plan_rule: str
    evidence_role: str

    def __post_init__(self):
        _hour(self.issued_at_source_hour)
        for name, expected in (
            ('forecast_rule', 'supplied_normal_profiles_declared_as_pre_episode_forecast'),
            ('plan_rule', 'fixed_normal_schedule_issued_before_first_action'),
            ('evidence_role', 'mechanism_assumption')):
            if type(getattr(self, name)) is not str or getattr(self, name) != expected:
                raise ValueError('explicit normal information mechanism required: '+name)


@dataclass(frozen=True, init=False)
class StaticUnit(_Owned):
    uid: str
    bus: int
    dispatch_mode: str
    enabled: bool
    minimum_power_mw: float
    maximum_power_mw: float
    ramp_mw_per_hour: float


@dataclass(frozen=True, init=False)
class StaticAcBranch(_Owned):
    uid: str
    from_bus: int
    to_bus: int
    reactance_pu: float
    tap_ratio: float
    continuous_rating_mw: float


@dataclass(frozen=True, init=False)
class StaticDcBranch(_Owned):
    uid: str
    from_bus: int
    to_bus: int
    minimum_power_mw: float
    maximum_power_mw: float


@dataclass(frozen=True, init=False)
class StaticNetwork(_Owned):
    base_mva: float
    reference_bus: int
    buses: tuple[int, ...]
    units: tuple[StaticUnit, ...]
    ac_branches: tuple[StaticAcBranch, ...]
    dc_branches: tuple[StaticDcBranch, ...]
    dc_bus: int


@dataclass(frozen=True, init=False)
class NormalHourView(_Owned):
    source_hour: int
    timestamp: str
    information: PlanInformationDeclaration
    generation_mw: tuple[tuple[str, float], ...]
    commitment: tuple[tuple[str, bool], ...]
    previous_commitment: tuple[tuple[str, bool], ...]
    allowed_plan_identity: str


@dataclass(frozen=True, init=False)
class PreparedNormalInformation(_Owned):
    contract: str
    source_input_identity: str
    normal_assignment_identity: str
    implementation_sha256: str
    allowed_plan_identity: str
    network: StaticNetwork
    hours: tuple[NormalHourView, ...]
    normal_witness: object
    causal_certificate: None
    formal_result: bool

    @property
    def audit_identity(self):
        return _digest(self)


@dataclass(frozen=True)
class CurrentGridConditions:
    source_hour: int
    timestamp: str
    demand_by_bus_mw: tuple[tuple[int, float], ...]
    generator_min_mw: tuple[tuple[str, float], ...]
    generator_max_mw: tuple[tuple[str, float], ...]
    generator_available: tuple[tuple[str, bool], ...]
    dc_baseline_mw: float
    dc_physical_maximum_mw: float
    dc_connected_capacity_mw: float
    evidence_role: str

    def __post_init__(self):
        _hour(self.source_hour)
        if type(self.timestamp) is not str or not self.timestamp:
            raise ValueError('explicit current timestamp required')
        _rows(self.demand_by_bus_mw, int)
        _rows(self.generator_min_mw, str)
        _rows(self.generator_max_mw, str)
        if tuple(k for k, _ in self.generator_min_mw) != tuple(k for k, _ in self.generator_max_mw):
            raise ValueError('current generator bounds inventory mismatch')
        if (type(self.generator_available) is not tuple
                or any(type(r) is not tuple or len(r) != 2 or type(r[0]) is not str or type(r[1]) is not bool
                       for r in self.generator_available)
                or tuple(k for k, _ in self.generator_available) != tuple(k for k, _ in self.generator_min_mw)):
            raise ValueError('complete sorted boolean base availability required')
        if any(a > b for (_, a), (_, b) in zip(self.generator_min_mw, self.generator_max_mw, strict=True)):
            raise ValueError('inverted current generator bounds')
        for x in (self.dc_baseline_mw, self.dc_physical_maximum_mw, self.dc_connected_capacity_mw):
            if _number(x) < 0:
                raise ValueError('nonnegative current DC quantity required')
        if self.dc_baseline_mw > min(self.dc_physical_maximum_mw, self.dc_connected_capacity_mw):
            raise ValueError('current DC baseline exceeds physical or connected limit')
        if type(self.evidence_role) is not str or self.evidence_role != 'mechanism_assumption':
            raise ValueError('explicit current mechanism input role required')


@dataclass(frozen=True, init=False)
class CurrentGridInformation(_Owned):
    contract: str
    network: StaticNetwork
    normal: NormalHourView
    current: CurrentGridConditions

    @property
    def visible_identity(self):
        return _digest(self)


def _contract():
    if type(CONTRACT) is not str or CONTRACT != 'declared_pre_episode_normal_plan__separate_current_conditions_v1':
        raise ValueError('grid information contract drift')


def prepare_normal_information(inputs, assignment, *, expected_input_identity, declaration):
    """Audit the complete normal assignment, then construct immutable projections.

    Source hashes/witnesses stay in this audit-side envelope; only the isolated
    CurrentGridInformation output is intended for a future decision kernel.
    """
    _contract()
    if type(inputs) is not ContinuousNormalInputs or type(declaration) is not PlanInformationDeclaration:
        raise ValueError('typed normal inputs and information declaration required')
    inputs, assignment = deepcopy(inputs), deepcopy(assignment)
    declaration.__post_init__()
    if declaration.issued_at_source_hour > inputs.carry.source_hour:
        raise ValueError('normal schedule must be issued by the incoming boundary')
    if normal_input_identity(inputs) != expected_input_identity:
        raise ValueError('normal source identity mismatch')
    witness = audit_normal_assignment(inputs, assignment, expected_identity=expected_input_identity)
    if witness.errors or witness.terminal_carry is None:
        raise ValueError('normal assignment lacks a valid complete witness')
    data = inputs.data
    buses = tuple(sorted(b.uid for b in data.buses))
    if any(type(b) is not int for b in buses):
        raise ValueError('built-in integer bus inventory required')
    units = []
    for g in sorted(data.generators, key=lambda x: x.uid):
        if (type(g.uid) is not str or not g.uid.strip() or type(g.bus) is not int
                or type(g.dispatch_mode) is not str):
            raise ValueError('static unit UID required')
        lower, upper, ramp = map(_number, (g.p_min_mw, g.p_max_mw, g.ramp_mw_per_hour))
        if lower < 0 or upper < lower or ramp < 0:
            raise ValueError('invalid static unit bounds or ramp')
        units.append(_owned(StaticUnit, uid=g.uid, bus=g.bus, dispatch_mode=g.dispatch_mode,
            enabled=g.enabled, minimum_power_mw=lower, maximum_power_mw=upper, ramp_mw_per_hour=ramp))
    for b in (*data.branches, *data.dc_branches):
        if (type(b.uid) is not str or not b.uid.strip()
                or type(b.from_bus) is not int or type(b.to_bus) is not int):
            raise ValueError('typed static branch inventory required')
    ac = tuple(_owned(StaticAcBranch, uid=b.uid, from_bus=b.from_bus, to_bus=b.to_bus,
        reactance_pu=b.reactance_pu, tap_ratio=b.tap_ratio, continuous_rating_mw=b.continuous_rating_mw)
        for b in sorted(data.branches, key=lambda x: x.uid))
    dc = tuple(_owned(StaticDcBranch, uid=b.uid, from_bus=b.from_bus, to_bus=b.to_bus,
        minimum_power_mw=b.p_min_mw, maximum_power_mw=b.p_max_mw)
        for b in sorted(data.dc_branches, key=lambda x: x.uid))
    network = _owned(StaticNetwork, base_mva=data.base_mva, reference_bus=data.reference_bus,
        buses=buses, units=tuple(units), ac_branches=ac, dc_branches=dc, dc_bus=inputs.request.dc_bus)
    prior = tuple((g.uid, inputs.initial.commitment[g.uid] if g.dispatch_mode == 'committable' else g.enabled)
                  for g in units)
    rows = []
    for t, hour in enumerate(inputs.source_hours):
        on = tuple((g.uid, bool(round(assignment[f'commitment[{t},{g.uid}]']))
            if g.dispatch_mode == 'committable' else g.enabled) for g in units)
        generation = tuple((g.uid, assignment[f'generation[normal,{t},{g.uid}]']) for g in units)
        rows.append((hour, inputs.request.timestamps[t].isoformat(), generation, on, prior))
        prior = on
    # Identity of the explicitly allowed pre-episode information. Never hash a
    # raw source/candidate ID into this policy-visible identity.
    forecasts = tuple((hour, inputs.request.timestamps[t].isoformat(),
        tuple(sorted(data.hourly_points[hour-1].demand_by_bus_mw.items())),
        tuple(sorted(data.hourly_points[hour-1].generator_min_mw.items())),
        tuple(sorted(data.hourly_points[hour-1].generator_max_mw.items())),
        tuple(sorted(data.hourly_points[hour-1].spin_up_requirement_by_area_mw.items())),
        inputs.request.dc_requested_mw[t], inputs.request.dc_physical_maximum_mw[t],
        inputs.request.dc_connected_capacity_mw[t]) for t, hour in enumerate(inputs.source_hours))
    initial = tuple((g.uid, inputs.initial.commitment[g.uid], inputs.initial.generation_mw[g.uid],
        inputs.initial.time_in_state_hours[g.uid]) for g in units)
    planning_parameters = (tuple(sorted((b.uid, b.area) for b in data.buses)),
        tuple((g.uid, g.category, g.ramp_mw_per_minute, g.minimum_up_time_hours, g.minimum_down_time_hours,
               g.cold_start_cost_usd, g.shutdown_cost_usd, g.cost_breakpoints_mw, g.cost_values_usd_per_hour)
              for g in sorted(data.generators, key=lambda x: x.uid)))
    allowed = _digest(CONTRACT, declaration, network, forecasts, initial, planning_parameters, tuple(rows))
    hours = tuple(_owned(NormalHourView, source_hour=hour, timestamp=stamp, information=declaration,
        generation_mw=generation, commitment=on, previous_commitment=previous, allowed_plan_identity=allowed)
        for hour, stamp, generation, on, previous in rows)
    if normal_input_identity(inputs) != expected_input_identity:
        raise ValueError('normal source changed during preparation')
    return _owned(PreparedNormalInformation, contract=CONTRACT, source_input_identity=expected_input_identity,
        normal_assignment_identity=witness.assignment_identity,
        implementation_sha256=sha256(Path(__file__).read_bytes()).hexdigest(), allowed_plan_identity=allowed,
        network=network, hours=hours, normal_witness=witness, causal_certificate=None, formal_result=False)


def current_grid_information(prepared, current, *, expected_audit_identity):
    """Audit-side selection: the returned value has no full-plan/source linkage."""
    _contract()
    if type(prepared) is not PreparedNormalInformation or type(current) is not CurrentGridConditions:
        raise ValueError('owned prepared plan and typed current conditions required')
    if prepared.audit_identity != expected_audit_identity:
        raise ValueError('prepared normal audit identity mismatch')
    if (prepared.contract != CONTRACT
            or prepared.implementation_sha256 != sha256(Path(__file__).read_bytes()).hexdigest()):
        raise ValueError('prepared information implementation drift')
    current.__post_init__()
    matches = tuple(h for h in prepared.hours if h.source_hour == current.source_hour)
    if len(matches) != 1 or matches[0].timestamp != current.timestamp:
        raise ValueError('current source hour/timestamp outside issued schedule')
    network = prepared.network
    if tuple(k for k, _ in current.demand_by_bus_mw) != network.buses:
        raise ValueError('current demand differs from network bus inventory')
    if tuple(k for k, _ in current.generator_min_mw) != tuple(g.uid for g in network.units):
        raise ValueError('current generator inventory differs from network')
    for g, (_, lower), (_, upper), (_, available) in zip(network.units, current.generator_min_mw,
            current.generator_max_mw, current.generator_available, strict=True):
        if upper > g.maximum_power_mw or (g.dispatch_mode == 'committable' and lower < g.minimum_power_mw):
            raise ValueError('current generator bounds exceed static envelope')
        if available and not g.enabled:
            raise ValueError('current report cannot enable a statically disabled generator')
    return _owned(CurrentGridInformation, contract=CONTRACT, network=network, normal=matches[0], current=current)
