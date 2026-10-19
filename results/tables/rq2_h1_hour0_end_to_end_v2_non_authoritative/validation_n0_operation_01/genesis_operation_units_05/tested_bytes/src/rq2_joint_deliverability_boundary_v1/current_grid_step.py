"""Current-hour prescribed-power DC model and assignment-derived actual carry.

No solver, request selection, dispatch policy, or security certificate is issued.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from fractions import Fraction as Q
from hashlib import sha256
from math import isfinite, radians
from pathlib import Path

from pyomo.environ import ConcreteModel, Constraint, ConstraintList, NonNegativeReals, Objective, Set, Var, value

from .continuous_grid_normal import _digest, _dependencies
from .grid_information import CurrentGridInformation
from .event_disclosure import DisclosureState, DisclosureStep, OutageComponent, disclose_current


CONTRACT = 'current_hour_fixed_power_normal_commitment_dc_actual_carry_v1'
TOLERANCE = 1e-6


def _finite(x):
    if type(x) not in (int, float) or not isfinite(x):
        raise ValueError('finite built-in quantity required')
    return x


def _q(x):
    return Q(str(_finite(x)))


def _owned(cls, **values):
    result = object.__new__(cls)
    for name, item in values.items():
        object.__setattr__(result, name, item)
    return result


class _Owned:
    def __init__(self, *args, **kwargs):
        raise TypeError('actual state/witness requires initialization or canonical audit')


@dataclass(frozen=True)
class CurrentGridProtocol:
    commitment_rule: str
    ramp_scope: str
    base_availability_rule: str
    reserve_scope: str
    information_mode: str
    parameter_role: str

    def __post_init__(self):
        for name, expected in (
            ('commitment_rule', 'fixed_normal_commitment__outage_as_availability'),
            ('ramp_scope', 'committable_only_actual_ramp__explicit_generator_repair_cap'),
            ('base_availability_rule', 'fixed_base_availability_for_episode'),
            ('reserve_scope', 'realtime_reserve_unregistered_not_modeled'),
            ('information_mode', 'current_report_only__declared_pre_episode_normal_plan'),
            ('parameter_role', 'mechanism_assumption')):
            if type(getattr(self, name)) is not str or getattr(self, name) != expected:
                raise ValueError('explicit current grid mechanism required: '+name)


@dataclass(frozen=True)
class PrescribedDcPower:
    source_hour: int
    numerator: str
    denominator: str
    evidence_role: str

    def __post_init__(self):
        if type(self.source_hour) is not int or self.source_hour < 1:
            raise ValueError('positive integer prescribed-power source hour required')
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
class ActualStepCarry(_Owned):
    protocol: CurrentGridProtocol
    network_identity: str
    allowed_plan_identity: str
    source_hour: int
    timestamp: str
    generation_mw: tuple
    base_availability: tuple
    effective_availability: tuple
    planned_commitment: tuple
    disclosure: DisclosureState
    predecessor_identity: str | None
    evidence_role: str

    @property
    def identity(self):
        return _digest(self)


@dataclass(frozen=True, init=False)
class CurrentGridWitness(_Owned):
    contract: str
    tolerance_mw: float
    input_identity: str
    assignment: tuple
    maximum_fixed_violation: float | None
    maximum_bound_violation: float | None
    maximum_constraint_violation: float | None
    maximum_exact_violation: float | None
    errors: tuple[str, ...]
    next_carry: ActualStepCarry | None
    physical_assignment_valid: bool
    causal_certificate: None
    infeasibility_certificate: None
    formal_result: bool
    security_certified: bool

    @property
    def identity(self):
        return _digest(self)


def _effective(network, base, disclosure):
    active = disclosure.active
    down = active.component.uid if active is not None and active.component.kind == 'generator' else None
    return tuple((g.uid, g.enabled and dict(base)[g.uid] and g.uid != down) for g in network.units)


def _information(info):
    if type(info) is not CurrentGridInformation:
        raise ValueError('isolated current grid information required')
    if info.contract != 'declared_pre_episode_normal_plan__separate_current_conditions_v1':
        raise ValueError('unsupported current information contract')
    info.current.__post_init__()
    info.normal.information.__post_init__()
    if info.current.source_hour != info.normal.source_hour or info.current.timestamp != info.normal.timestamp:
        raise ValueError('current information clock mismatch')
    return info.network


def _inventory(rows, names, kind):
    if (type(rows) is not tuple or any(type(r) is not tuple or len(r) != 2 or type(r[0]) is not str for r in rows)
            or tuple(k for k, _ in rows) != names):
        raise ValueError('complete sorted actual-state inventory required')
    for _, item in rows:
        if kind is bool:
            if type(item) is not bool:
                raise ValueError('boolean actual-state availability required')
        else:
            _finite(item)


def initialize_actual_carry(info, disclosure, *, protocol, generation_mw, base_availability, evidence_role):
    network = _information(info)
    if type(protocol) is not CurrentGridProtocol:
        raise ValueError('typed current grid protocol required')
    protocol.__post_init__()
    if type(disclosure) is not DisclosureState:
        raise ValueError('owned origin disclosure required')
    disclosure.__post_init__()
    allowed = {OutageComponent('generator', g.uid) for g in network.units if g.enabled}
    allowed.update(OutageComponent('branch', b.uid) for b in network.ac_branches)
    if not set(disclosure.protocol.components) <= allowed:
        raise ValueError('disclosure component absent from enabled network inventory')
    if disclosure.source_hour != disclosure.origin_hour or disclosure.source_hour != info.current.source_hour-1:
        raise ValueError('explicit same-boundary origin disclosure required')
    if type(evidence_role) is not str or evidence_role != 'mechanism_assumption':
        raise ValueError('actual origin is an explicit mechanism assumption')
    names = tuple(g.uid for g in network.units)
    _inventory(generation_mw, names, float)
    _inventory(base_availability, names, bool)
    effective = _effective(network, base_availability, disclosure)
    for g in network.units:
        if dict(base_availability)[g.uid] and not g.enabled:
            raise ValueError('origin cannot enable statically disabled unit')
        on = dict(info.normal.previous_commitment)[g.uid]
        available = dict(effective)[g.uid]
        upper = g.maximum_power_mw if available and on else 0.
        lower = g.minimum_power_mw if available and on and g.dispatch_mode == 'committable' else 0.
        if not lower <= dict(generation_mw)[g.uid] <= upper:
            raise ValueError('origin generation outside static availability/plan bounds')
    return _owned(ActualStepCarry, protocol=protocol, network_identity=_digest(network),
        allowed_plan_identity=info.normal.allowed_plan_identity, source_hour=disclosure.source_hour,
        timestamp=(datetime.fromisoformat(info.current.timestamp)-timedelta(hours=1)).isoformat(),
        generation_mw=generation_mw, base_availability=base_availability, effective_availability=effective,
        planned_commitment=info.normal.previous_commitment, disclosure=disclosure,
        predecessor_identity=None, evidence_role=evidence_role)


def _validate(info, disclosure, before, power):
    if (type(CONTRACT) is not str or CONTRACT != 'current_hour_fixed_power_normal_commitment_dc_actual_carry_v1'
            or type(TOLERANCE) is not float or TOLERANCE != 1e-6):
        raise ValueError('current grid contract or tolerance drift')
    network = _information(info)
    if type(before) is not ActualStepCarry or type(disclosure) is not DisclosureStep or type(power) is not PrescribedDcPower:
        raise ValueError('owned actual carry/disclosure and explicit fixed power required')
    before.protocol.__post_init__()
    power.__post_init__()
    if (before.network_identity != _digest(network) or before.allowed_plan_identity != info.normal.allowed_plan_identity
            or before.source_hour+1 != info.current.source_hour or power.source_hour != info.current.source_hour
            or datetime.fromisoformat(before.timestamp)+timedelta(hours=1) != datetime.fromisoformat(info.current.timestamp)
            or before.planned_commitment != info.normal.previous_commitment):
        raise ValueError('actual carry network/plan/clock mismatch')
    if (disclosure.before != before.disclosure or disclosure.after.source_hour != info.current.source_hour
            or disclose_current(disclosure.before, disclosure.report) != disclosure):
        raise ValueError('current disclosure does not extend actual carry')
    allowed = {OutageComponent('generator', g.uid) for g in network.units if g.enabled}
    allowed.update(OutageComponent('branch', b.uid) for b in network.ac_branches)
    if not set(disclosure.after.protocol.components) <= allowed:
        raise ValueError('disclosure component absent from enabled network inventory')
    if before.base_availability != info.current.generator_available:
        raise ValueError('base availability transition has no registered trip/repair contract')
    names = tuple(g.uid for g in network.units)
    _inventory(before.generation_mw, names, float)
    _inventory(before.base_availability, names, bool)
    if before.effective_availability != _effective(network, before.base_availability, before.disclosure):
        raise ValueError('prior effective availability mismatch')
    if power.exact_mw > min(_q(info.current.dc_physical_maximum_mw), _q(info.current.dc_connected_capacity_mw)):
        raise ValueError('fixed power exceeds current physical or connected limit')
    effective = _effective(network, info.current.generator_available, disclosure.after)
    for g in network.units:
        if (dict(effective)[g.uid] and g.dispatch_mode == 'fixed'
                and dict(info.current.generator_min_mw)[g.uid] != dict(info.current.generator_max_mw)[g.uid]):
            raise ValueError('available fixed generator requires equal current bounds')
    cap = disclosure.repaired_generator_return_limit_mw
    if cap is not None:
        unit = next(g for g in network.units if g.uid == disclosure.ended.component.uid)
        if cap > unit.maximum_power_mw:
            raise ValueError('repair return limit exceeds source nameplate')
    return effective


def current_step_identity(info, disclosure, before, power):
    _validate(info, disclosure, before, power)
    root = Path(__file__).resolve().parent
    sources = tuple((n, sha256((root/n).read_bytes()).hexdigest()) for n in
        ('current_grid_step.py', 'grid_information.py', 'event_disclosure.py'))
    return _digest(CONTRACT, TOLERANCE, info, disclosure, before, power, sources, _dependencies())


def build_current_grid_model(info, disclosure, before, power, *, expected_identity):
    available = dict(_validate(info, disclosure, before, power))
    if current_step_identity(info, disclosure, before, power) != expected_identity:
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


def audit_current_grid_assignment(info, disclosure, before, power, assignment, *, expected_identity):
    model = build_current_grid_model(info, disclosure, before, power, expected_identity=expected_identity)
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
    if current_step_identity(info, disclosure, before, power) != expected_identity:
        raise ValueError('current network input identity changed during audit')
    errors = tuple('current_grid_'+label+'_violation' for label, amount in
        (('fixed', fixed), ('bound', bounds), ('constraint', residual), ('exact', exact)) if amount > Q('1e-6'))
    next_carry = None
    if not errors:
        link = _digest(expected_identity, tuple(sorted(assignment.items())))
        next_carry = _owned(ActualStepCarry, protocol=before.protocol, network_identity=before.network_identity,
            allowed_plan_identity=before.allowed_plan_identity, source_hour=info.current.source_hour,
            timestamp=info.current.timestamp, generation_mw=tuple((g.uid, assignment[f'generation[{g.uid}]']) for g in info.network.units),
            base_availability=info.current.generator_available,
            effective_availability=_effective(info.network, info.current.generator_available, disclosure.after),
            planned_commitment=info.normal.commitment, disclosure=disclosure.after,
            predecessor_identity=link, evidence_role='derived_current_network_assignment')
    def report(x):
        try:
            return float(x) if isfinite(float(x)) else None
        except OverflowError:
            return None
    return _owned(CurrentGridWitness, contract=CONTRACT, tolerance_mw=TOLERANCE, input_identity=expected_identity,
        assignment=tuple(sorted(assignment.items())), maximum_fixed_violation=report(fixed), maximum_bound_violation=report(bounds),
        maximum_constraint_violation=report(residual), maximum_exact_violation=report(exact), errors=errors,
        next_carry=next_carry, physical_assignment_valid=not errors, causal_certificate=None, infeasibility_certificate=None,
        formal_result=False, security_certified=False)


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
