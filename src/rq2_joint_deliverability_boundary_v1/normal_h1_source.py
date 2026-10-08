"""Current-row H1 assembly and feasible boundary replay, for development.

Source authentication, origin outage disclosure, numerical lex acceptance and
atomic publication belong to the enclosing controller. A replayed boundary here
is a feasible candidate, never a committed common-normal decision.
"""
from copy import deepcopy
from dataclasses import dataclass, fields, replace
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from math import ceil
from pathlib import Path

from ..evaluation import ChronologicalFlexibilityEnvelope
from ..grid.chronological_dispatch import ChronologicalDispatchRequest
from ..grid.rts_gmlc import RtsGmlcChronologicalData, RtsGmlcHourlyPoint
from ..grid.rts_gmlc_scuc import RtsGmlcInitialState
from . import normal_h1_model as model_api
from . import workload_projection
from .continuous_grid_normal import ContinuousNormalInputs, normal_input_identity, _digest
from .grid_carry import GridCarry, GridIdentity, UnitLimits, UnitPoint


CONTRACT = 'h1_current_base_normal_source_v1'
_CLOCK_ORIGIN = datetime(2000, 1, 1, tzinfo=timezone.utc)


class _Owned:
    def __init__(self, *args, **kwargs):
        raise TypeError('H1 source objects require assembly or audited replay')


def _owned(cls, **values):
    result = object.__new__(cls)
    for field in fields(cls):
        object.__setattr__(result, field.name, values[field.name])
    return result


@dataclass(frozen=True, init=False)
class H1StaticNetwork(_Owned):
    data: RtsGmlcChronologicalData
    identity: str


@dataclass(frozen=True, init=False)
class H1NormalBoundary(_Owned):
    network_identity: str
    completed_hours: int
    # Sorted all-generator (UID, commitment, generation MW, elapsed hours).
    units: tuple
    evidence_role: str


@dataclass(frozen=True, init=False)
class H1CurrentNormal(_Owned):
    network: H1StaticNetwork
    before: H1NormalBoundary
    relative_hour: int
    inputs: ContinuousNormalInputs
    input_identity: str
    # Audit-only fields; never included in the causal computational key.
    source_timestamp: str
    source_time_basis: str
    workload_projection_payload: bytes
    audit_identity: str


@dataclass(frozen=True, init=False)
class H1FeasibleTransition(_Owned):
    input_identity: str
    before_identity: str
    assignment_audit: model_api.H1AssignmentAudit
    candidate_boundary: H1NormalBoundary
    numerical_lex_accepted: bool
    published: bool


def static_network(data):
    """Extract static fields only; never inspect, copy or hash hourly_points."""
    if type(data) is not RtsGmlcChronologicalData:
        raise ValueError('exact RTS chronological data required')
    static = RtsGmlcChronologicalData(data.base_mva, data.reference_bus,
        tuple(sorted(deepcopy(data.buses), key=lambda x: x.uid)),
        tuple(sorted(deepcopy(data.branches), key=lambda x: x.uid)),
        tuple(sorted(deepcopy(data.dc_branches), key=lambda x: x.uid)),
        model_api._generators(deepcopy(data.generators)), ())
    return _owned(H1StaticNetwork, data=static, identity=_digest(CONTRACT, static))


def _network(network):
    if (type(network) is not H1StaticNetwork or network.data.hourly_points != ()
            or _digest(CONTRACT, network.data) != network.identity):
        raise ValueError('H1 static network drift or wrong type')
    return network.data


def _initial(network, current):
    initial = model_api.declared_normal_initial(network.data.generators, current)
    return _owned(H1NormalBoundary, network_identity=network.identity, completed_hours=0,
        units=tuple((g.uid, initial.commitment[g.uid], initial.generation_mw[g.uid],
                     initial.time_in_state_hours[g.uid]) for g in network.data.generators),
        evidence_role='declared_mechanism_initial')


def _boundary(network, before, relative_hour):
    if (type(before) is not H1NormalBoundary or before.network_identity != network.identity
            or type(before.completed_hours) is not int or before.completed_hours != relative_hour):
        raise ValueError('H1 boundary network or relative-hour mismatch')
    if ((relative_hour == 0 and before.evidence_role != 'declared_mechanism_initial')
            or (relative_hour > 0 and before.evidence_role != 'numerical_lex_candidate')):
        raise ValueError('next H1 hour requires a complete numerical lex candidate')
    if (type(before.units) is not tuple
            or tuple(row[0] for row in before.units) != tuple(g.uid for g in network.data.generators)):
        raise ValueError('complete sorted H1 boundary inventory required')
    for g, (uid, on, power, age) in zip(network.data.generators, before.units, strict=True):
        if type(on) is not bool or type(age) is not int or age < 0:
            raise ValueError('invalid H1 boundary commitment or age')
        model_api._number(power, 'boundary power')
        if power > g.p_max_mw + model_api.RESIDUAL_LIMIT:
            raise ValueError('H1 boundary exceeds static power maximum')
        if g.dispatch_mode == 'committable':
            if ((not on and power != 0.)
                    or (on and power < g.p_min_mw-model_api.RESIDUAL_LIMIT)):
                raise ValueError('H1 committable boundary power/state mismatch')
            maximum_age = relative_hour if on else ceil(g.minimum_down_time_hours)+relative_hour
            if relative_hour > 0 and not 1 <= age <= maximum_age:
                raise ValueError('H1 boundary elapsed time is unreachable from declared initial')
        elif age != 0 or on != g.enabled or (g.dispatch_mode == 'disabled' and power != 0.):
            raise ValueError('H1 noncommittable boundary mode/state mismatch')
    return RtsGmlcInitialState(
        {uid: on for uid, on, _, _ in before.units},
        {uid: p for uid, _, p, _ in before.units},
        {uid: age for uid, _, _, age in before.units}, 'h1_normal_physical_boundary_v1')


def _projection_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')


def _audit_identity(timestamp, basis, projection, input_identity):
    return _digest('h1_current_source_audit_v1', timestamp, basis, projection.decode('ascii'),
                   input_identity, sha256(Path(__file__).read_bytes()).hexdigest())


def _time_basis(timestamp, basis):
    if (type(timestamp) is not datetime or type(basis) is not str
            or (basis == 'naive_source_labelled_utc' and timestamp.tzinfo is not None)
            or (basis == 'aware_source' and timestamp.utcoffset() is None)
            or basis not in ('naive_source_labelled_utc', 'aware_source')):
        raise ValueError('explicit matching source time basis required')


def assemble_current_normal(network, current, raw_workload, *, relative_hour, dc_bus,
                            source_time_basis, before=None):
    """Assemble only the revealed current base row, with a relative kernel clock.

    The caller authenticates the row and records its source/pair/split mapping
    separately. No data-set index or hidden label is an algorithm input here.
    raw workload above one remains an unresolved mapping error, without clipping.
    """
    data = _network(network)
    if type(relative_hour) is not int or not 0 <= relative_hour < 192:
        raise ValueError('v2 relative hour must be an integer in [0,192)')
    if type(current) is not RtsGmlcHourlyPoint or type(current.timestamp) is not datetime:
        raise ValueError('one typed current base row and timestamp required')
    _time_basis(current.timestamp, source_time_basis)
    if type(dc_bus) is not int:
        raise ValueError('integer DC bus required')
    projection = workload_projection.project_workload_power(raw_workload, '250', decimal_places=12)
    if projection['status'] != 'projected':
        raise ValueError('unresolved H1 workload mapping: '+projection['reason'])
    if before is None:
        if relative_hour != 0:
            raise ValueError('normal history cannot be reset after the first hour')
        before = _initial(network, current)
    initial = _boundary(network, before, relative_hour)
    if relative_hour == 0 and before != _initial(network, current):
        raise ValueError('first H1 boundary differs from the declared current-row initial')
    # One-row local indexing is independent of the full physical incoming state.
    point = replace(deepcopy(current), timestamp=_CLOCK_ORIGIN+timedelta(hours=relative_hour))
    thermal = tuple(g for g in data.generators if g.dispatch_mode == 'committable')
    carry = GridCarry(GridIdentity('training', 'h1_neutral_kernel_tag', 0, network.identity), 0,
        tuple(UnitLimits(g.uid, g.p_min_mw, g.p_max_mw, g.ramp_mw_per_hour,
                         g.minimum_up_time_hours, g.minimum_down_time_hours) for g in thermal),
        tuple(UnitPoint(g.uid, initial.commitment[g.uid], initial.generation_mw[g.uid]) for g in thermal),
        tuple(initial.time_in_state_hours[g.uid] for g in thermal),
        'mechanism_assumption' if relative_hour == 0 else 'derived_dispatch_witness')
    # These zero-business constants are internal normal-kernel plumbing. They
    # never stand in for the v2 service budget or any arm's business state.
    envelope = ChronologicalFlexibilityEnvelope(
        time_step_hours=1., maximum_event_duration_hours=1., minimum_recovery_hours=1.,
        maximum_events_by_period={'h1': 0}, maximum_curtailment_energy_mwh_by_period={'h1': 0.},
        maximum_recovery_debt_mwh=0., maximum_recovery_power_mw=0., minimum_event_power_mw=1.,
        response_time_hours=1., curtailment_ramp_mw_per_hour=1., recovery_efficiency=1.,
        terminal_debt_limit_mwh_by_period={'h1': 0.}, parameter_status='h1_normal_zero_business_kernel')
    request = ChronologicalDispatchRequest(
        timestamps=(point.timestamp,), periods=('h1',), time_step_hours=1.,
        system_demand_by_bus_mw=(dict(point.demand_by_bus_mw),),
        generator_availability=({g.uid: g.enabled for g in data.generators},), dc_bus=dc_bus,
        dc_requested_mw=(projection['dc_baseline_mw'],), dc_flexible_demand_mw=(0.,),
        dc_recoverable_flexible_mw=(0.,), dc_physical_maximum_mw=(250.,),
        dc_connected_capacity_mw=(250.,), dc_call_limit_mw=(0.,), recovery_headroom_mw=(0.,),
        flexibility_envelope=envelope, flexibility_boundary_state_status='clean_boundary_with_zero_carry_in',
        completed_periods=frozenset(), initial_has_prior_event=False, initial_recovery_debt_mwh=0.,
        initial_grid_call_mw=0., initial_active_event_duration_hours=0., initial_interevent_rest_hours=None,
        initial_event_count_by_period={}, initial_curtailment_energy_mwh_by_period={},
        require_terminal_event_inactive=False, incidents=(), initial_commitment=initial.commitment,
        initial_generation_mw=initial.generation_mw, initial_time_in_state_hours=initial.time_in_state_hours)
    inputs = ContinuousNormalInputs(replace(data, hourly_points=(point,)), request, initial, carry,
                                    (1,), 'aware_source')
    model_api.stage_order(inputs)
    input_id = normal_input_identity(inputs)
    timestamp, payload = current.timestamp.isoformat(), _projection_bytes(projection)
    return _owned(H1CurrentNormal, network=network, before=before, relative_hour=relative_hour,
        inputs=inputs, input_identity=input_id, source_timestamp=timestamp,
        source_time_basis=source_time_basis, workload_projection_payload=payload,
        audit_identity=_audit_identity(timestamp, source_time_basis, payload, input_id))


def validate_current(packet):
    if type(packet) is not H1CurrentNormal:
        raise ValueError('exact current H1 packet required')
    data = _network(packet.network)
    initial = _boundary(packet.network, packet.before, packet.relative_hour)
    if (initial != packet.inputs.initial or replace(packet.inputs.data, hourly_points=()) != data
            or packet.inputs.request.timestamps != (_CLOCK_ORIGIN+timedelta(hours=packet.relative_hour),)):
        raise ValueError('H1 packet boundary/static/relative-clock binding mismatch')
    if normal_input_identity(packet.inputs) != packet.input_identity:
        raise ValueError('H1 current input drift')
    if (type(packet.workload_projection_payload) is not bytes or type(packet.source_timestamp) is not str
            or _audit_identity(packet.source_timestamp, packet.source_time_basis,
                packet.workload_projection_payload, packet.input_identity) != packet.audit_identity):
        raise ValueError('H1 source audit drift')
    _time_basis(datetime.fromisoformat(packet.source_timestamp), packet.source_time_basis)
    projection = json.loads(packet.workload_projection_payload)
    rebuilt = workload_projection.project_workload_power(projection['raw_workload_fraction'], '250', decimal_places=12)
    if (rebuilt['status'] != 'projected' or _projection_bytes(rebuilt) != packet.workload_projection_payload
            or packet.inputs.request.dc_requested_mw != (rebuilt['dc_baseline_mw'],)):
        raise ValueError('H1 source workload audit mismatch')
    model_api.stage_order(packet.inputs)


def causal_key(packet, specification, budget):
    """Common-normal computational key, distinct from source audit identity."""
    from . import normal_h1_short_solve as native
    validate_current(packet)
    return _digest(CONTRACT, packet.relative_hour,
        native.chain_identity(packet.inputs, specification, budget),
        sha256(Path(__file__).read_bytes()).hexdigest(),
        sha256(Path(workload_projection.__file__).read_bytes()).hexdigest())


def replay_feasible_boundary(packet, assignment, *, expected_input_identity):
    """Strict feasibility replay only; no numerical lex acceptance/publication.

    The caller must complete all native stages before publishing a decision.
    A failed assignment raises and produces no successor boundary.
    """
    validate_current(packet)
    if type(expected_input_identity) is not str or expected_input_identity != packet.input_identity:
        raise ValueError('H1 current input identity mismatch')
    req = model_api.H1StageRequest(packet.inputs)
    audit = model_api.audit_h1_assignment(req, assignment, expected_identity=model_api.h1_stage_identity(req))
    if audit.errors:
        raise ValueError('H1 boundary assignment rejected: '+repr(audit.errors))
    prior = {uid: (on, age) for uid, on, _, age in packet.before.units}
    units = []
    for g in packet.inputs.data.generators:
        if g.dispatch_mode == 'committable':
            on = bool(round(assignment[f'commitment[0,{g.uid}]']))
            age = prior[g.uid][1]+1 if prior[g.uid][0] == on else 1
        else:
            on, age = g.enabled, 0
        units.append((g.uid, on, assignment[f'generation[normal,0,{g.uid}]'], age))
    after = _owned(H1NormalBoundary, network_identity=packet.network.identity,
        completed_hours=packet.relative_hour+1, units=tuple(units),
        evidence_role='strict_feasible_assignment_candidate')
    # A tolerance-feasible assignment may still lie outside the exact domain of
    # a consumable carry (e.g. off+positive or negative generation). Never round
    # continuous values to make a boundary admissible; reject before emitting it.
    check = _owned(H1NormalBoundary, network_identity=after.network_identity,
        completed_hours=after.completed_hours, units=after.units, evidence_role='numerical_lex_candidate')
    _boundary(packet.network, check, check.completed_hours)
    return _owned(H1FeasibleTransition, input_identity=packet.input_identity,
        before_identity=_digest(packet.before), assignment_audit=audit,
        candidate_boundary=after, numerical_lex_accepted=False, published=False)
