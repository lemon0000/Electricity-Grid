"""Draft coupled-hour outage LP with explicit actual origin and repair limits.

Fixed normal commitment is retained as a schedule, not an actual-UC certificate.
This builds a feasibility region or explicitly weighted objective; it never
declares its curtailment vector a unique, causal external network request.
"""
from copy import deepcopy
from dataclasses import dataclass
from math import isfinite, radians
from pathlib import Path
from hashlib import sha256

from pyomo.environ import ConcreteModel, ConstraintList, NonNegativeReals, Objective, Set, Var, minimize

from ..scenarios.rts_gmlc_n1_chronology import N1OutageEvent, event_by_hour
from .grid_carry import GridIdentity
from .continuous_grid_normal import ContinuousNormalInputs, audit_normal_assignment, normal_input_identity, _digest
from .continuous_grid_candidate import ContinuousGridCandidate, _execution_identity


CONTRACT = 'fixed_normal_commitment_outage_availability_coupled_actual_generation_v1'


def _number(x, label):
    if type(x) not in (int, float) or not isfinite(x) or x < 0:
        raise ValueError(label + ' requires finite nonnegative built-in number')
    return x


def _sha(x):
    if type(x) is not str or len(x) != 64 or any(c not in '0123456789abcdef' for c in x):
        raise ValueError('built-in lowercase SHA256 required')


@dataclass(frozen=True)
class ActualGridOrigin:
    identity: GridIdentity
    source_hour: int
    generation_mw: tuple[tuple[str, float], ...]
    availability: tuple[tuple[str, bool], ...]
    evidence_role: str


@dataclass(frozen=True)
class OutageTrajectoryInputs:
    normal_inputs: ContinuousNormalInputs
    normal_candidate: ContinuousGridCandidate
    expected_normal_candidate_id: str
    events: tuple[N1OutageEvent, ...]
    actual_origin: ActualGridOrigin
    commitment_response_mode: str
    interhour_ramp_scope: str
    information_mode: str
    forced_trip_rule: str
    repair_return_limits_mw: tuple[tuple[str, str, float], ...]
    parameter_role: str
    objective_mode: str
    curtailment_weights: tuple[float, ...]
    fixed_curtailment_mw: tuple[float, ...]

    def __post_init__(self):
        object.__setattr__(self, 'normal_inputs', deepcopy(self.normal_inputs))
        _validate(self)


def _validate(inputs):
    if type(inputs) is not OutageTrajectoryInputs or type(inputs.normal_inputs) is not ContinuousNormalInputs:
        raise ValueError('typed outage trajectory and normal inputs required')
    normal, candidate, origin = inputs.normal_inputs, inputs.normal_candidate, inputs.actual_origin
    _sha(inputs.expected_normal_candidate_id)
    if type(candidate) is not ContinuousGridCandidate or candidate.result_id != inputs.expected_normal_candidate_id:
        raise ValueError('owned normal candidate identity mismatch')
    identity = normal_input_identity(normal)
    if (candidate.input_identity != identity or not candidate.normal.optimal
            or candidate.execution_identity != _execution_identity(candidate.specification, candidate.budget)):
        raise ValueError('normal origin/optimality/execution binding mismatch')
    witness = audit_normal_assignment(normal, dict(candidate.normal.loaded_values), expected_identity=identity)
    if witness.errors or witness != candidate.normal_witness:
        raise ValueError('normal assignment witness mismatch')
    labels = (inputs.commitment_response_mode, inputs.interhour_ramp_scope, inputs.information_mode,
              inputs.forced_trip_rule, inputs.parameter_role, inputs.objective_mode)
    if (any(type(label) is not str for label in labels)
            or inputs.commitment_response_mode != 'fixed_normal_commitment__outage_as_availability'
            or inputs.interhour_ramp_scope != 'committable_only_inherited_normal_scuc'
            or inputs.information_mode != 'offline_full_event_path'
            or inputs.forced_trip_rule != 'generation_zero__downward_ramp_exempt_on_1_to_0_availability'
            or inputs.parameter_role != 'mechanism_assumption'):
        raise ValueError('explicit fixed-commitment, trip and mechanism contracts required')
    data, request = normal.data, normal.request
    generators = {g.uid: g for g in data.generators}
    if type(inputs.events) is not tuple or any(type(e) is not N1OutageEvent for e in inputs.events):
        raise ValueError('typed immutable original event table required')
    event_ids = [e.event_id for e in inputs.events]
    if len(set(event_ids)) != len(event_ids):
        raise ValueError('duplicate original event identity')
    for e in inputs.events:
        if (type(e.seed) is not int or e.seed != normal.carry.identity.outage_seed
                or type(e.event_id) is not str or not e.event_id.strip() or type(e.component_type) is not str
                or type(e.start_hour) is not int or type(e.end_hour_exclusive) is not int):
            raise ValueError('event identity/seed/integer interval mismatch')
        available = {b.uid for b in data.branches} if e.component_type == 'branch' else (
            {g.uid for g in data.generators if g.enabled} if e.component_type == 'generator' else set())
        if type(e.uid) is not str or e.uid not in available:
            raise ValueError('unknown or disabled outage component')
    timeline = event_by_hour(inputs.events, horizon_hours=len(data.hourly_points))
    events = tuple(timeline[h - 1] for h in normal.source_hours)
    if (type(origin) is not ActualGridOrigin or type(origin.identity) is not GridIdentity
            or origin.identity != normal.carry.identity or type(origin.source_hour) is not int
            or origin.source_hour != normal.carry.source_hour or type(origin.evidence_role) is not str
            or origin.evidence_role != 'mechanism_assumption'):
        raise ValueError('explicit same-boundary mechanism actual origin required')
    names = tuple(sorted(generators))
    for rows in (origin.generation_mw, origin.availability):
        if (type(rows) is not tuple or any(type(row) is not tuple or len(row) != 2 for row in rows)
                or tuple(uid for uid, _ in rows) != names):
            raise ValueError('complete sorted immutable actual-origin inventory required')
    generation, availability = dict(origin.generation_mw), dict(origin.availability)
    if any(type(a) is not bool for a in availability.values()):
        raise ValueError('actual availability must be boolean')
    previous_index = normal.source_hours[0] - 2
    previous_event = timeline[previous_index] if previous_index >= 0 else None
    for uid, g in generators.items():
        p = _number(generation[uid], 'actual origin generation')
        expected_available = g.enabled and not (previous_event is not None
            and previous_event.component_type == 'generator' and previous_event.uid == uid)
        if previous_index >= 0:
            if availability[uid] != expected_available:
                raise ValueError('actual-origin availability conflicts with preceding source event')
        else:
            # A source-origin stationary-down event is already active, not
            # evidence of a newly observed trip at index zero.
            first = events[0]
            expected_available = g.enabled and not (first is not None
                and first.component_type == 'generator' and first.uid == uid)
            if availability[uid] != expected_available:
                raise ValueError('source-origin availability must preserve already-active event')
        upper = g.p_max_mw if availability[uid] else 0.
        lower = 0.
        if g.dispatch_mode == 'committable':
            on = request.initial_commitment[uid]
            upper = upper if on else 0.
            lower = g.p_min_mw if availability[uid] and on else 0.
        if p < lower or p > upper:
            raise ValueError('actual origin outside source availability/commitment bounds')
        if previous_index >= 0 and availability[uid]:
            point = data.hourly_points[previous_index]
            if g.dispatch_mode == 'committable':
                on = request.initial_commitment[uid]
                if not (point.generator_min_mw[uid] * on <= p <= point.generator_max_mw[uid] * on):
                    raise ValueError('committable actual origin differs from preceding source bounds')
            if g.dispatch_mode == 'fixed' and p != point.generator_max_mw[uid]:
                raise ValueError('fixed actual origin differs from preceding source profile')
            if g.dispatch_mode == 'curtailable' and not point.generator_min_mw[uid] <= p <= point.generator_max_mw[uid]:
                raise ValueError('curtailable actual origin differs from preceding source bounds')
    repairs = inputs.repair_return_limits_mw
    if (type(repairs) is not tuple or any(type(row) is not tuple or len(row) != 3 for row in repairs)
            or tuple((row[0], row[1]) for row in repairs) != tuple(sorted(
                (e.event_id, e.uid) for e in inputs.events if e.component_type == 'generator'))):
        raise ValueError('explicit sorted repair return limit for every generator event required')
    for event_id, uid, limit in repairs:
        if _number(limit, 'repair return limit') > generators[uid].p_max_mw:
            raise ValueError('repair return limit exceeds source nameplate')
    horizon = len(normal.source_hours)
    if inputs.objective_mode == 'weighted_total_curtailment':
        if (type(inputs.curtailment_weights) is not tuple or len(inputs.curtailment_weights) != horizon
                or inputs.fixed_curtailment_mw != ()):
            raise ValueError('explicit positive objective weights and empty fixed vector required')
        if any(_number(w, 'objective weight') <= 0 for w in inputs.curtailment_weights):
            raise ValueError('positive objective weights required')
    elif inputs.objective_mode == 'fixed_curtailment_vector':
        if (type(inputs.fixed_curtailment_mw) is not tuple or len(inputs.fixed_curtailment_mw) != horizon
                or inputs.curtailment_weights != ()):
            raise ValueError('complete fixed vector and empty objective weights required')
        for t, q in enumerate(inputs.fixed_curtailment_mw):
            if _number(q, 'fixed curtailment') > request.dc_requested_mw[t] or (events[t] is None and q != 0):
                raise ValueError('fixed curtailment exceeds demand or no-outage calling domain')
    else:
        raise ValueError('explicit objective mode required')
    return events, previous_event


def outage_trajectory_identity(inputs):
    _validate(inputs)
    return _digest(CONTRACT, inputs, sha256(Path(__file__).read_bytes()).hexdigest())


def build_outage_trajectory_model(inputs, *, expected_identity):
    _sha(expected_identity)
    events, previous_event = _validate(inputs)
    if outage_trajectory_identity(inputs) != expected_identity:
        raise ValueError('outage trajectory identity mismatch')
    normal = inputs.normal_inputs
    data, request = normal.data, normal.request
    points = tuple(data.hourly_points[h - 1] for h in normal.source_hours)
    baseline = dict(inputs.normal_candidate.normal.loaded_values)
    generators = {g.uid: g for g in data.generators}
    on = {(t, g.uid): (bool(round(baseline[f'commitment[{t},{g.uid}]']))
        if g.dispatch_mode == 'committable' else g.enabled) for t in range(len(points)) for g in data.generators}
    available = {(t, g.uid): g.enabled and not (e is not None and e.component_type == 'generator' and e.uid == g.uid)
        for t, e in enumerate(events) for g in data.generators}
    model = ConcreteModel()
    model.TIME = Set(initialize=range(len(points)), ordered=True)
    model.GEN = Set(initialize=tuple(generators), ordered=True)
    model.BUS = Set(initialize=tuple(b.uid for b in data.buses), ordered=True)
    model.BRANCH = Set(initialize=tuple(b.uid for b in data.branches), ordered=True)
    model.DC_BRANCH = Set(initialize=tuple(b.uid for b in data.dc_branches), ordered=True)
    def bounds(_model, t, uid):
        g = generators[uid]
        if not available[t, uid] or not on[t, uid]:
            return 0., 0.
        upper = points[t].generator_max_mw[uid]
        return (upper if g.dispatch_mode == 'fixed' else points[t].generator_min_mw[uid]), upper
    model.generation = Var(model.TIME, model.GEN, domain=NonNegativeReals, bounds=bounds)
    model.curtailment = Var(model.TIME, domain=NonNegativeReals,
        bounds=lambda _m, t: (0., request.dc_requested_mw[t] if events[t] is not None else 0.))
    model.angle_degrees = Var(model.TIME, model.BUS)
    model.branch_flow = Var(model.TIME, model.BRANCH)
    model.dc_flow = Var(model.TIME, model.DC_BRANCH)
    model.network = ConstraintList()
    model.redispatch = ConstraintList()
    model.actual_ramp = ConstraintList()
    model.balance = ConstraintList()
    repairs = {(event_id, uid): cap for event_id, uid, cap in inputs.repair_return_limits_mw}
    for t, (point, event) in enumerate(zip(points, events, strict=True)):
        model.angle_degrees[t, data.reference_bus].fix(0.)
        if inputs.objective_mode == 'fixed_curtailment_vector':
            model.curtailment[t].fix(inputs.fixed_curtailment_mw[t])
        for b in data.branches:
            flow = model.branch_flow[t, b.uid]
            if event is not None and event.component_type == 'branch' and event.uid == b.uid:
                flow.setlb(0.); flow.setub(0.)
            else:
                flow.setlb(-b.continuous_rating_mw); flow.setub(b.continuous_rating_mw)
                model.network.add(flow == data.base_mva / (b.reactance_pu * b.tap_ratio) * radians(1.)
                                  * (model.angle_degrees[t, b.from_bus] - model.angle_degrees[t, b.to_bus]))
        for b in data.dc_branches:
            model.dc_flow[t, b.uid].setlb(b.p_min_mw)
            model.dc_flow[t, b.uid].setub(b.p_max_mw)
        for uid, g in generators.items():
            if not g.enabled:
                continue
            p = model.generation[t, uid]
            previous_p = dict(inputs.actual_origin.generation_mw)[uid] if t == 0 else model.generation[t - 1, uid]
            prior_available = dict(inputs.actual_origin.availability)[uid] if t == 0 else available[t - 1, uid]
            prior_on = request.initial_commitment[uid] if t == 0 else on[t - 1, uid]
            startup = int(g.dispatch_mode == 'committable' and on[t, uid] and not prior_on)
            shutdown = int(g.dispatch_mode == 'committable' and prior_on and not on[t, uid])
            ramp = g.ramp_mw_per_hour
            if available[t, uid] and g.dispatch_mode != 'fixed':
                base = baseline[f'generation[normal,{t},{uid}]']
                model.redispatch.add(p - base <= ramp)
                model.redispatch.add(base - p <= ramp)
            if not prior_available and available[t, uid]:
                prior_event = previous_event if t == 0 else events[t - 1]
                if prior_event is None or prior_event.component_type != 'generator' or prior_event.uid != uid:
                    raise ValueError('repair edge lacks its original generator event')
                model.actual_ramp.add(p - previous_p <= repairs[prior_event.event_id, uid])
            elif g.dispatch_mode == 'committable':
                model.actual_ramp.add(p - previous_p <= ramp + g.p_max_mw * startup)
            if g.dispatch_mode == 'committable' and not (prior_available and not available[t, uid]):
                model.actual_ramp.add(previous_p - p <= ramp + g.p_max_mw * shutdown)
        for bus in model.BUS:
            generated = sum(model.generation[t, g.uid] for g in data.generators if g.bus == bus)
            exported = sum(model.branch_flow[t, b.uid] for b in data.branches if b.from_bus == bus)
            exported -= sum(model.branch_flow[t, b.uid] for b in data.branches if b.to_bus == bus)
            exported += sum(model.dc_flow[t, b.uid] for b in data.dc_branches if b.from_bus == bus)
            exported -= sum(model.dc_flow[t, b.uid] for b in data.dc_branches if b.to_bus == bus)
            demand = point.demand_by_bus_mw[bus]
            if bus == request.dc_bus:
                demand += request.dc_requested_mw[t] - model.curtailment[t]
            model.balance.add(generated - demand == exported)
    objective = (sum(inputs.curtailment_weights[t] * model.curtailment[t] for t in model.TIME)
                 if inputs.objective_mode == 'weighted_total_curtailment' else 0.)
    model.objective = Objective(expr=objective, sense=minimize)
    return model
