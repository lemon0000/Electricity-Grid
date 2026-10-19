"""Detached H1 physical mathematics and candidate carry; no operational owner.

All entry points are development-only. Neither a frame nor an audited candidate
authenticates N selection, lane history, publication, or a native execution.
"""
from dataclasses import dataclass
from fractions import Fraction as Q
from hashlib import sha256
from math import isfinite, radians
from pathlib import Path

from pyomo.environ import ConcreteModel, Constraint, ConstraintList, NonNegativeReals, Objective, Set, Var, value

from experiments import h1_current_grid_information_development_v1 as information
from src.rq2_joint_deliverability_boundary_v1 import current_grid_step as old
from src.rq2_joint_deliverability_boundary_v1 import event_disclosure as events
from src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal import _digest, _dependencies
from src.rq2_joint_deliverability_boundary_v1.event_disclosure import DisclosureState, DisclosureStep, OutageComponent, disclose_current

CONTRACT = 'h1_current_only_fixed_power_physical_candidate_v1'
TOLERANCE = 1e-6
_Owned, _owned = information._Owned, information._owned
_finite, _q, _inventory, _effective = old._finite, old._q, old._inventory, old._effective


def implementation_identity():
    return _digest(information.implementation_identity(), _dependencies(),
        tuple((Path(m.__file__).name, sha256(Path(m.__file__).read_bytes()).hexdigest()) for m in (old, events)),
        sha256(Path(__file__).read_bytes()).hexdigest())


@dataclass(frozen=True)
class Lane:
    role: str
    arm: str | None

    def __post_init__(self):
        if type(self.role) is not str or (self.arm is not None and type(self.arm) is not str):
            raise ValueError('built-in lane role and arm strings required')
        if not ((self.role == 'Rref' and self.arm is None) or (self.role == 'A' and self.arm in (
                'network_only_shared', 'cfe_only_shared', 'joint_correct_shared',
                'joint_b6_separate_planning_shared_execution'))):
            raise ValueError('explicit common reference or public actual arm required')


@dataclass(frozen=True, init=False)
class NormalFrame(_Owned):
    info: information.H1CurrentInformation
    normal_network_identity: str
    normal_before: information.source.H1NormalBoundary
    normal_after: information.source.H1NormalBoundary


def _frame(packet, after):
    """Private synthetic/validated-packet seam; does not authenticate selection."""
    return _owned(NormalFrame, info=information._decision(packet, after),
        normal_network_identity=packet.network.identity, normal_before=packet.before, normal_after=after)


def _pin(item):
    if type(item) is not str or len(item) != 64 or any(c not in '0123456789abcdef' for c in item):
        raise ValueError('canonical lowercase SHA256 identity required')


def _information(frame):
    if type(frame) is not NormalFrame or type(frame.info) is not information.H1CurrentInformation:
        raise ValueError('development H1 frame required')
    info = frame.info
    _pin(frame.normal_network_identity)
    if info.contract != information.SCHEMA or type(info.relative_hour) is not int or not 0 <= info.relative_hour < 192:
        raise ValueError('H1 information contract/hour mismatch')
    names = tuple(g.uid for g in info.network.units)
    for boundary, hour, commitment in ((frame.normal_before, info.relative_hour, info.normal.previous_commitment),
                                      (frame.normal_after, info.relative_hour+1, info.normal.commitment)):
        if (type(boundary) is not information.source.H1NormalBoundary or boundary.completed_hours != hour
                or tuple(u[0] for u in boundary.units) != names
                or tuple((u[0], u[1]) for u in boundary.units) != commitment):
            raise ValueError('normal boundary clock/inventory/commitment mismatch')
    if (frame.normal_before.network_identity != frame.normal_network_identity
            or frame.normal_after.network_identity != frame.normal_network_identity
            or tuple((u[0], u[2]) for u in frame.normal_after.units) != info.normal.generation_mw):
        raise ValueError('normal boundary network/generation mismatch')
    return info.network


@dataclass(frozen=True, init=False)
class PhysicalCandidateCarry(_Owned):
    protocol: str
    lane: Lane
    network_identity: str
    origin_identity: str
    completed_hours: int
    normal_boundary_identity: str
    decision_identity: str | None
    generation_mw: tuple
    base_availability: tuple
    effective_availability: tuple
    planned_commitment: tuple
    disclosure: DisclosureState
    previous_carry_identity: str | None
    step_input_identity: str | None

    @property
    def identity(self):
        return _digest(self)


def _components(network, disclosure):
    allowed = {OutageComponent('generator', g.uid) for g in network.units if g.enabled}
    allowed.update(OutageComponent('branch', b.uid) for b in network.ac_branches)
    if not set(disclosure.protocol.components) <= allowed:
        raise ValueError('disclosure component absent from enabled network inventory')


def initialize_development_carry(frame, disclosure, *, lane):
    """Declared H1 origin, requiring an explicit incoming outage state.

    No caller-selected generation: available units inherit approved N initial
    output, unavailable units get zero. This is a detached candidate only.
    """
    n = _information(frame)
    if type(lane) is not Lane:
        raise ValueError('typed lane required')
    lane.__post_init__()
    if type(disclosure) is not DisclosureState:
        raise ValueError('explicit incoming disclosure required')
    disclosure.__post_init__()
    if frame.info.relative_hour != 0 or disclosure.origin_hour != 0 or disclosure.source_hour != 0:
        raise ValueError('H1 origin requires neutral boundary zero')
    _components(n, disclosure)
    base = frame.info.current.generator_available
    effective = _effective(n, base, disclosure)
    initial = {u[0]: u[2] for u in frame.normal_before.units}
    generation = tuple((g.uid, initial[g.uid] if dict(effective)[g.uid] else 0.) for g in n.units)
    for g in n.units:
        on = dict(frame.info.normal.previous_commitment)[g.uid]
        enabled = dict(effective)[g.uid]
        lower = g.minimum_power_mw if enabled and on and g.dispatch_mode == 'committable' else 0.
        upper = g.maximum_power_mw if enabled and on else 0.
        if not lower <= dict(generation)[g.uid] <= upper:
            raise ValueError('declared origin violates static availability bounds')
    origin = _digest(CONTRACT, lane, n, frame.normal_before, disclosure, base, generation)
    return _owned(PhysicalCandidateCarry, protocol=CONTRACT, lane=lane, network_identity=_digest(n),
        origin_identity=origin, completed_hours=0, normal_boundary_identity=_digest(frame.normal_before),
        decision_identity=None, generation_mw=generation, base_availability=base, effective_availability=effective,
        planned_commitment=frame.info.normal.previous_commitment, disclosure=disclosure,
        previous_carry_identity=None, step_input_identity=None)


def _validate(frame, disclosure, before, power, lane):
    if CONTRACT != 'h1_current_only_fixed_power_physical_candidate_v1' or type(TOLERANCE) is not float or TOLERANCE != 1e-6:
        raise ValueError('H1 physical contract or tolerance drift')
    n = _information(frame)
    info = frame.info
    if (type(before) is not PhysicalCandidateCarry or type(disclosure) is not DisclosureStep
            or type(power) is not RelativeDcPower or type(lane) is not Lane):
        raise ValueError('typed development carry/disclosure/power/lane required')
    lane.__post_init__()
    power.__post_init__()
    if before.lane != lane:
        raise ValueError('cross-lane carry rejected')
    if (before.protocol != CONTRACT or before.network_identity != _digest(n)
            or before.normal_boundary_identity != _digest(frame.normal_before)
            or before.completed_hours != info.relative_hour or power.relative_hour != info.relative_hour
            or before.planned_commitment != info.normal.previous_commitment):
        raise ValueError('H1 carry network/normal boundary/clock mismatch')
    if (disclosure.before != before.disclosure or before.disclosure.origin_hour != 0
            or before.disclosure.source_hour != info.relative_hour
            or disclosure.after.source_hour != info.relative_hour+1
            or disclose_current(disclosure.before, disclosure.report) != disclosure):
        raise ValueError('neutral current disclosure does not extend carry')
    _components(n, disclosure.after)
    if before.base_availability != info.current.generator_available:
        raise ValueError('base availability transition has no registered trip/repair contract')
    names = tuple(g.uid for g in n.units)
    _inventory(before.generation_mw, names, float)
    _inventory(before.base_availability, names, bool)
    if before.effective_availability != _effective(n, before.base_availability, before.disclosure):
        raise ValueError('prior effective availability mismatch')
    if power.exact_mw > min(_q(info.current.dc_physical_maximum_mw), _q(info.current.dc_connected_capacity_mw)):
        raise ValueError('fixed power exceeds current physical or connected limit')
    effective = _effective(n, info.current.generator_available, disclosure.after)
    for g in n.units:
        if (dict(effective)[g.uid] and g.dispatch_mode == 'fixed'
                and dict(info.current.generator_min_mw)[g.uid] != dict(info.current.generator_max_mw)[g.uid]):
            raise ValueError('available fixed generator requires equal current bounds')
    cap = disclosure.repaired_generator_return_limit_mw
    if cap is not None:
        unit = next(g for g in n.units if g.uid == disclosure.ended.component.uid)
        if cap > unit.maximum_power_mw:
            raise ValueError('repair return limit exceeds source nameplate')
    return effective


def development_step_identity(frame, disclosure, before, power, *, lane):
    _validate(frame, disclosure, before, power, lane)
    return _digest(CONTRACT, TOLERANCE, frame, disclosure, before, power, lane, implementation_identity())


@dataclass(frozen=True)
class RelativeDcPower:
    relative_hour: int
    numerator: str
    denominator: str
    evidence_role: str

    def __post_init__(self):
        if type(self.relative_hour) is not int or not 0 <= self.relative_hour < 192:
            raise ValueError('relative hour in 0..191 required')
        if type(self.numerator) is not str or type(self.denominator) is not str:
            raise ValueError('canonical exact MW ratio strings required')
        try:
            q = Q(int(self.numerator), int(self.denominator))
        except (ValueError, ZeroDivisionError):
            raise ValueError('valid exact MW ratio required') from None
        if q < 0 or (str(q.numerator), str(q.denominator)) != (self.numerator, self.denominator):
            raise ValueError('canonical nonnegative exact MW ratio required')
        try:
            projected = float(q)
        except OverflowError:
            raise ValueError('finite non-underflowing power projection required') from None
        if not isfinite(projected) or (q > 0 and projected == 0):
            raise ValueError('finite non-underflowing power projection required')
        if type(self.evidence_role) is not str or self.evidence_role != 'mechanism_assumption':
            raise ValueError('explicit fixed-power mechanism role required')

    @property
    def exact_mw(self):
        return Q(int(self.numerator), int(self.denominator))


@dataclass(frozen=True, init=False)
class PhysicalCandidateWitness(_Owned):
    contract: str
    tolerance_mw: float
    input_identity: str
    assignment: tuple
    maximum_fixed_violation: float | None
    maximum_bound_violation: float | None
    maximum_constraint_violation: float | None
    maximum_exact_violation: float | None
    errors: tuple[str, ...]
    next_carry: PhysicalCandidateCarry | None
    physical_assignment_valid: bool
    causal_certificate: None
    infeasibility_certificate: None
    formal_result: bool
    security_certified: bool
    detached_consumer_authenticated: bool
    normal_selection_authenticated: bool
    common_publication_verified: bool
    reference_or_actual_ready: bool

    @property
    def identity(self):
        return _digest(self)


def build_development_model(frame, disclosure, before, power, *, lane, expected_identity):
    """Build detached development mathematics; no authenticated runtime input."""
    _pin(expected_identity)
    info = frame.info
    available = dict(_validate(frame, disclosure, before, power, lane))
    if development_step_identity(frame, disclosure, before, power, lane=lane) != expected_identity:
        raise ValueError('current network input identity mismatch')
    n, c, plan = info.network, info.current, info.normal
    on, old_on = dict(plan.commitment), dict(plan.previous_commitment)
    previous, prior_available = dict(before.generation_mw), dict(before.effective_availability)
    lower, upper = dict(c.generator_min_mw), dict(c.generator_max_mw)
    model = ConcreteModel()
    model.GEN = Set(initialize=tuple(g.uid for g in n.units), ordered=True)
    model.BUS = Set(initialize=n.buses, ordered=True)
    model.BRANCH = Set(initialize=tuple(b.uid for b in n.ac_branches), ordered=True)
    model.DC_BRANCH = Set(initialize=tuple(b.uid for b in n.dc_branches), ordered=True)
    units = {g.uid: g for g in n.units}
    def bounds(_m, uid):
        if not available[uid] or not on[uid]:
            return 0., 0.
        return (upper[uid] if units[uid].dispatch_mode == 'fixed' else lower[uid]), upper[uid]
    model.generation = Var(model.GEN, domain=NonNegativeReals, bounds=bounds)
    model.angle_degrees = Var(model.BUS)
    model.branch_flow = Var(model.BRANCH)
    model.dc_flow = Var(model.DC_BRANCH)
    model.angle_degrees[n.reference_bus].fix(0.)
    model.network = ConstraintList()
    model.response = ConstraintList()
    model.actual_ramp = ConstraintList()
    model.balance = ConstraintList()
    active = disclosure.after.active
    for b in n.ac_branches:
        f = model.branch_flow[b.uid]
        if active is not None and active.component == OutageComponent('branch', b.uid):
            f.setlb(0.); f.setub(0.)
        else:
            f.setlb(-b.continuous_rating_mw); f.setub(b.continuous_rating_mw)
            model.network.add(f == n.base_mva/(b.reactance_pu*b.tap_ratio)*radians(1.)
                *(model.angle_degrees[b.from_bus]-model.angle_degrees[b.to_bus]))
    for b in n.dc_branches:
        model.dc_flow[b.uid].setlb(b.minimum_power_mw)
        model.dc_flow[b.uid].setub(b.maximum_power_mw)
    for g in n.units:
        if not g.enabled:
            continue
        p, uid, ramp = model.generation[g.uid], g.uid, g.ramp_mw_per_hour
        if available[uid] and g.dispatch_mode != 'fixed':
            base = dict(plan.generation_mw)[uid]
            model.response.add(p-base <= ramp)
            model.response.add(base-p <= ramp)
        startup = int(g.dispatch_mode == 'committable' and on[uid] and not old_on[uid])
        shutdown = int(g.dispatch_mode == 'committable' and old_on[uid] and not on[uid])
        if not prior_available[uid] and available[uid]:
            if disclosure.ended is None or disclosure.ended.component != OutageComponent('generator', uid):
                raise ValueError('generator return lacks current repair disclosure')
            model.actual_ramp.add(p-previous[uid] <= disclosure.repaired_generator_return_limit_mw)
        elif g.dispatch_mode == 'committable':
            model.actual_ramp.add(p-previous[uid] <= ramp+g.maximum_power_mw*startup)
        if g.dispatch_mode == 'committable' and not (prior_available[uid] and not available[uid]):
            model.actual_ramp.add(previous[uid]-p <= ramp+g.maximum_power_mw*shutdown)
    for bus in n.buses:
        generated = sum(model.generation[g.uid] for g in n.units if g.bus == bus)
        exported = sum(model.branch_flow[b.uid]*((b.from_bus == bus)-(b.to_bus == bus)) for b in n.ac_branches)
        exported += sum(model.dc_flow[b.uid]*((b.from_bus == bus)-(b.to_bus == bus)) for b in n.dc_branches)
        demand = dict(c.demand_by_bus_mw)[bus]+(float(power.exact_mw) if bus == n.dc_bus else 0.)
        model.balance.add(generated-demand == exported)
    model.objective = Objective(expr=0.)
    return model


def audit_development_assignment(frame, disclosure, before, power, assignment, *, lane, expected_identity):
    """Audit feasibility only; returned carry is detached and nonpublished."""
    info = frame.info
    model = build_development_model(frame, disclosure, before, power, lane=lane, expected_identity=expected_identity)
    variables = {v.name: v for v in model.component_data_objects(Var)}
    if type(assignment) is not dict or set(assignment) != set(variables) or any(type(k) is not str for k in assignment):
        raise ValueError('complete current network assignment required')
    assignment = dict(assignment)
    fixed = bounds = residual = 0.
    for name, v in variables.items():
        x = _finite(assignment[name])
        if v.fixed:
            fixed = max(fixed, abs(x-value(v)))
        if v.lb is not None:
            bounds = max(bounds, value(v.lb)-x)
        if v.ub is not None:
            bounds = max(bounds, x-value(v.ub))
        v.set_value(x, skip_validation=True)
    for constraint in model.component_data_objects(Constraint, active=True):
        body = value(constraint.body, exception=False)
        if body is None or not isfinite(body):
            residual = float('inf'); break
        if constraint.lower is not None:
            residual = max(residual, value(constraint.lower)-body)
        if constraint.upper is not None:
            residual = max(residual, body-value(constraint.upper))
    exact = _exact_residual(info, disclosure, before, power, assignment)
    if development_step_identity(frame, disclosure, before, power, lane=lane) != expected_identity:
        raise ValueError('current network input identity changed during audit')
    errors = tuple('current_grid_'+label+'_violation' for label, amount in
        (('fixed', fixed), ('bound', bounds), ('constraint', residual), ('exact', exact)) if amount > Q('1e-6'))
    next_carry = None
    if not errors:
        next_carry = _owned(PhysicalCandidateCarry, protocol=before.protocol, lane=before.lane,
            network_identity=before.network_identity, origin_identity=before.origin_identity,
            completed_hours=info.relative_hour+1, normal_boundary_identity=_digest(frame.normal_after),
            decision_identity=info.decision_identity,
            generation_mw=tuple((g.uid, assignment[f'generation[{g.uid}]']) for g in info.network.units),
            base_availability=info.current.generator_available,
            effective_availability=_effective(info.network, info.current.generator_available, disclosure.after),
            planned_commitment=info.normal.commitment, disclosure=disclosure.after,
            previous_carry_identity=before.identity, step_input_identity=expected_identity)
    def report(x):
        try:
            return float(x) if isfinite(float(x)) else None
        except OverflowError:
            return None
    return _owned(PhysicalCandidateWitness, contract=CONTRACT, tolerance_mw=TOLERANCE, input_identity=expected_identity,
        assignment=tuple(sorted(assignment.items())), maximum_fixed_violation=report(fixed), maximum_bound_violation=report(bounds),
        maximum_constraint_violation=report(residual), maximum_exact_violation=report(exact), errors=errors,
        next_carry=next_carry, physical_assignment_valid=not errors, causal_certificate=None, infeasibility_certificate=None,
        formal_result=False, security_certified=False, detached_consumer_authenticated=False,
        normal_selection_authenticated=False, common_publication_verified=False, reference_or_actual_ready=False)


def _exact_residual(info, disclosure, before, power, assignment):
    n, c, plan = info.network, info.current, info.normal
    available = dict(_effective(n, c.generator_available, disclosure.after))
    prior_available = dict(before.effective_availability)
    on, prior_on = dict(plan.commitment), dict(plan.previous_commitment)
    exact = Q(0)
    for bus in n.buses:
        generated = sum((_q(assignment[f'generation[{g.uid}]']) for g in n.units if g.bus == bus), Q(0))
        exported = Q(0)
        for prefix, branches in (('branch_flow', n.ac_branches), ('dc_flow', n.dc_branches)):
            for b in branches:
                exported += _q(assignment[f'{prefix}[{b.uid}]'])*((b.from_bus == bus)-(b.to_bus == bus))
        demand = _q(dict(c.demand_by_bus_mw)[bus])+(power.exact_mw if bus == n.dc_bus else Q(0))
        exact = max(exact, abs(generated-exported-demand))
    for g in n.units:
        uid = g.uid
        p, prev = _q(assignment[f'generation[{uid}]']), _q(dict(before.generation_mw)[uid])
        if not available[uid] or not on[uid]:
            exact = max(exact, abs(p))
        else:
            lower, upper = _q(dict(c.generator_min_mw)[uid]), _q(dict(c.generator_max_mw)[uid])
            if g.dispatch_mode == 'fixed':
                lower = upper
            exact = max(exact, lower-p, p-upper)
        if not g.enabled:
            continue
        ramp = _q(g.ramp_mw_per_hour)
        if available[uid] and g.dispatch_mode != 'fixed':
            exact = max(exact, abs(p-_q(dict(plan.generation_mw)[uid]))-ramp)
        startup = int(g.dispatch_mode == 'committable' and on[uid] and not prior_on[uid])
        shutdown = int(g.dispatch_mode == 'committable' and prior_on[uid] and not on[uid])
        if not prior_available[uid] and available[uid]:
            exact = max(exact, p-prev-_q(disclosure.repaired_generator_return_limit_mw))
        elif g.dispatch_mode == 'committable':
            exact = max(exact, p-prev-ramp-_q(g.maximum_power_mw)*startup)
        if g.dispatch_mode == 'committable' and not (prior_available[uid] and not available[uid]):
            exact = max(exact, prev-p-ramp-_q(g.maximum_power_mw)*shutdown)
    return exact
