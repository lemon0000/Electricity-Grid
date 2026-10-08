"""Draft common-reference LP and fixed-power projection audit.

A declared origin or an owned selected reference state is required. An arbitrary
feasible assignment neither selects a request nor advances the reference state.
"""
from dataclasses import dataclass
from fractions import Fraction as Q
from hashlib import sha256
from pathlib import Path

from pyomo.environ import NonNegativeReals, Var

from .continuous_grid_normal import _digest
from .current_grid_step import (ActualStepCarry, CurrentGridWitness, PrescribedDcPower,
    initialize_actual_carry, current_step_identity, build_current_grid_model,
    audit_current_grid_assignment, _finite, _owned, _Owned)


CONTRACT = 'common_reference_baseline_power_lp_projection_audit_v1'


@dataclass(frozen=True)
class ReferenceProtocol:
    reference_rule: str
    invocation_scope: str
    evidence_role: str

    def __post_init__(self):
        for field, expected in (
            ('reference_rule', 'common_baseline_no_cfe_no_recovery_assumed_prior_reference_fulfilment'),
            ('invocation_scope', 'all_current_hours_mechanism'),
            ('evidence_role', 'mechanism_assumption')):
            if type(getattr(self, field)) is not str or getattr(self, field) != expected:
                raise ValueError('explicit reference mechanism required: '+field)


@dataclass(frozen=True, init=False)
class ReferenceGridOrigin(_Owned):
    contract: str
    protocol: ReferenceProtocol
    physical_origin: ActualStepCarry

    @property
    def identity(self):
        return _digest(self)


@dataclass(frozen=True, init=False)
class ReferenceGridState(_Owned):
    contract: str
    protocol: ReferenceProtocol
    origin_identity: str
    previous_state_identity: str
    selector_policy_identity: str
    selection_identity: str
    physical_carry: ActualStepCarry

    @property
    def identity(self):
        return _digest(self)


@dataclass(frozen=True, init=False)
class ReferenceAssignmentWitness(_Owned):
    contract: str
    input_identity: str
    assignment: tuple
    reference_power_mw: float
    candidate_grid_request_exact: tuple[str, str] | None
    canonical_objective: float | None
    physical_witness: CurrentGridWitness | None
    physical_assignment_valid: bool
    errors: tuple[str, ...]
    selected_request: None
    next_reference_state: None
    minimum_request_certificate: None
    causal_certificate: None
    infeasibility_certificate: None
    formal_result: bool
    security_certified: bool

    @property
    def identity(self):
        return _digest(self)


def _contract():
    if type(CONTRACT) is not str or CONTRACT != 'common_reference_baseline_power_lp_projection_audit_v1':
        raise ValueError('reference contract drift')


def initialize_reference_origin(info, disclosure, *, reference_protocol, grid_protocol,
                                generation_mw, base_availability):
    _contract()
    if type(reference_protocol) is not ReferenceProtocol:
        raise ValueError('typed reference mechanism required')
    reference_protocol.__post_init__()
    physical = initialize_actual_carry(info, disclosure, protocol=grid_protocol,
        generation_mw=generation_mw, base_availability=base_availability, evidence_role='mechanism_assumption')
    return _owned(ReferenceGridOrigin, contract=CONTRACT, protocol=reference_protocol, physical_origin=physical)


def _zero(info):
    return PrescribedDcPower(info.current.source_hour, '0', '1', 'mechanism_assumption')


def _physical(before):
    if type(before) not in (ReferenceGridOrigin, ReferenceGridState) or before.contract != CONTRACT:
        raise ValueError('owned reference state required; arm actual carry is not a reference origin')
    before.protocol.__post_init__()
    if type(before) is ReferenceGridOrigin:
        physical = before.physical_origin
        if physical.predecessor_identity is not None or physical.evidence_role != 'mechanism_assumption':
            raise ValueError('declared reference origin required')
    else:
        for name in ('origin_identity', 'previous_state_identity', 'selector_policy_identity', 'selection_identity'):
            item = getattr(before, name)
            if type(item) is not str or len(item) != 64 or any(c not in '0123456789abcdef' for c in item):
                raise ValueError('canonical reference selection lineage required')
        physical = before.physical_carry
        if physical.predecessor_identity is None or physical.evidence_role != 'derived_current_network_assignment':
            raise ValueError('selected reference requires audited physical carry')
    return physical


def reference_input_identity(info, disclosure, before):
    _contract()
    physical = _physical(before)
    source = sha256(Path(__file__).read_bytes()).hexdigest()
    return _digest(CONTRACT, before, source, current_step_identity(info, disclosure, physical, _zero(info)))


def build_reference_grid_model(info, disclosure, before, *, expected_identity):
    if (type(expected_identity) is not str or len(expected_identity) != 64
            or any(c not in '0123456789abcdef' for c in expected_identity)):
        raise ValueError('canonical lowercase SHA256 reference identity required')
    if reference_input_identity(info, disclosure, before) != expected_identity:
        raise ValueError('reference input identity mismatch')
    physical, zero = _physical(before), _zero(info)
    model = build_current_grid_model(info, disclosure, physical, zero,
        expected_identity=current_step_identity(info, disclosure, physical, zero))
    model.reference_power = Var(domain=NonNegativeReals, bounds=(0., info.current.dc_baseline_mw))
    # All network/response/ramp/repair rows remain inherited; only DC load varies.
    model.balance.clear()
    n, c = info.network, info.current
    for bus in n.buses:
        generated = sum(model.generation[g.uid] for g in n.units if g.bus == bus)
        exported = sum(model.branch_flow[b.uid]*((b.from_bus == bus)-(b.to_bus == bus)) for b in n.ac_branches)
        exported += sum(model.dc_flow[b.uid]*((b.from_bus == bus)-(b.to_bus == bus)) for b in n.dc_branches)
        demand = dict(c.demand_by_bus_mw)[bus]+(model.reference_power if bus == n.dc_bus else 0.)
        model.balance.add(generated-demand == exported)
    model.objective.set_value(c.dc_baseline_mw-model.reference_power)
    return model


def audit_reference_assignment(info, disclosure, before, assignment, *, expected_identity):
    model = build_reference_grid_model(info, disclosure, before, expected_identity=expected_identity)
    names = {v.name for v in model.component_data_objects(Var)}
    if type(assignment) is not dict or set(assignment) != names or any(type(k) is not str for k in assignment):
        raise ValueError('complete reference assignment required')
    assignment = dict(assignment)
    for number in assignment.values():
        _finite(number)
    p = Q(str(assignment['reference_power']))
    baseline = Q(str(info.current.dc_baseline_mw))
    witness = request = objective = None
    errors = ()
    if not 0 <= p <= baseline:
        errors = ('reference_power_outside_exact_domain',)
    else:
        power = PrescribedDcPower(info.current.source_hour, str(p.numerator), str(p.denominator), 'mechanism_assumption')
        physical_values = {k: v for k, v in assignment.items() if k != 'reference_power'}
        physical = _physical(before)
        witness = audit_current_grid_assignment(info, disclosure, physical, power, physical_values,
            expected_identity=current_step_identity(info, disclosure, physical, power))
        errors = witness.errors
        q = baseline-p
        objective = float(q)
        if witness.physical_assignment_valid:
            request = (str(q.numerator), str(q.denominator))
    if reference_input_identity(info, disclosure, before) != expected_identity:
        raise ValueError('reference input identity changed during audit')
    return _owned(ReferenceAssignmentWitness, contract=CONTRACT, input_identity=expected_identity,
        assignment=tuple(sorted(assignment.items())), reference_power_mw=float(p),
        candidate_grid_request_exact=request, canonical_objective=objective, physical_witness=witness,
        physical_assignment_valid=witness is not None and witness.physical_assignment_valid,
        errors=errors, selected_request=None, next_reference_state=None, minimum_request_certificate=None,
        causal_certificate=None, infeasibility_certificate=None, formal_result=False, security_certified=False)
