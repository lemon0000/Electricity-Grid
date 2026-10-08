"""Draft fixed business trajectory mapped into the continuous outage network.

The linear normalization and source pairing are explicit mechanism assumptions.
No business action, external grid request, or network dispatch is optimized here.
"""
from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction as Q
from hashlib import sha256
from math import isfinite
from pathlib import Path
from re import fullmatch

from pyomo.environ import Constraint, ConstraintList, Objective, Param, Var, value

from .capacity_policy import CapacityPolicyCursor
from .four_arm_replay import NETWORK, CFE
from .prefix_handoff import export_prefix_handoff, prefix_digest
from .continuous_grid_normal import _digest
from .outage_trajectory import OutageTrajectoryInputs, build_outage_trajectory_model, outage_trajectory_identity, _sha
from .outage_assignment import _owned, _finite


CONTRACT = 'fixed_committed_business_power_continuous_network_assignment_v1'


@dataclass(frozen=True)
class BusinessGridInputs:
    network: OutageTrajectoryInputs
    business_prefix: CapacityPolicyCursor
    expected_business_prefix_sha256: str
    normalized_unit_mw: str
    power_mapping: str
    source_pairing: str
    parameter_role: str

    def __post_init__(self):
        object.__setattr__(self, 'network', deepcopy(self.network))
        object.__setattr__(self, 'business_prefix', deepcopy(self.business_prefix))
        _validated(self)


@dataclass(frozen=True)
class BusinessPowerHour:
    power_source_hour: int
    workload_source_hour: int
    exact_mw: tuple
    projected_mw: tuple
    projected_hex: tuple
    projection_error_mw: tuple
    baseline_alignment_error_mw: float


def _q(x):
    if type(x) is Q:
        return x
    if type(x) not in (int, float) or not isfinite(x):
        raise ValueError('finite exact or built-in business scalar required')
    return Q(str(x))


def _validated(inputs):
    if type(CONTRACT) is not str or CONTRACT != 'fixed_committed_business_power_continuous_network_assignment_v1':
        raise ValueError('business grid contract drift')
    if (type(inputs) is not BusinessGridInputs or type(inputs.network) is not OutageTrajectoryInputs
            or type(inputs.business_prefix) is not CapacityPolicyCursor):
        raise ValueError('typed network and committed business prefix required')
    _sha(inputs.expected_business_prefix_sha256)
    labels = ((inputs.power_mapping, 'linear_workload_power_no_idle_offset_v1'),
              (inputs.source_pairing, 'declared_power_source_and_workload_pairing_mechanism_v1'),
              (inputs.parameter_role, 'mechanism_assumption'))
    if any(type(actual) is not str or actual != expected for actual, expected in labels):
        raise ValueError('explicit mechanism power mapping and source pairing required')
    if (type(inputs.normalized_unit_mw) is not str
            or fullmatch(r'(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?', inputs.normalized_unit_mw) is None
            or Q(inputs.normalized_unit_mw) <= 0):
        raise ValueError('positive canonical decimal string MW unit required')
    if inputs.network.objective_mode != 'weighted_total_curtailment':
        raise ValueError('network envelope template cannot carry a fixed curtailment vector')
    grid_id = outage_trajectory_identity(inputs.network)
    prefix = export_prefix_handoff(inputs.business_prefix)
    if prefix_digest(prefix) != inputs.expected_business_prefix_sha256:
        raise ValueError('business prefix identity mismatch')
    normal = inputs.network.normal_inputs
    records = inputs.business_prefix.records
    if len(records) != len(normal.source_hours):
        raise ValueError('complete business and network horizon alignment required')
    anchor = inputs.business_prefix.initial.tracks[0][1].physical.anchor
    identity = normal.carry.identity
    if ((anchor.split, anchor.power_outage_seed) != (identity.split, identity.outage_seed)
            or anchor.power_source_hour != normal.carry.source_hour):
        raise ValueError('business/network split, seed or initial-hour mismatch')
    # Source object hashes and trace names may belong to different namespaces.
    # Their declared pairing is bound through both original input identities.
    scale = Q(inputs.normalized_unit_mw)
    rows = []
    for t, record in enumerate(records):
        hour = record.current.observation.hour
        response, action = record.response, record.response.action
        if hour.power_source_hour != normal.source_hours[t]:
            raise ValueError('business/network absolute source-hour mismatch')
        quantities = {
            'baseline': _q(hour.workload_occupancy),
            'original_grid_request': _q(hour.grid_request),
            'original_cfe_request': _q(hour.cfe_request),
            'grid_served': action.grid_served, 'cfe_served': action.cfe_served,
            'recovery': action.recovery, 'actual_power': action.actual_service_power,
            'grid_shortfall': response.grid_shortfall, 'cfe_shortfall': response.cfe_shortfall}
        exact, projected, hex_values, errors = [], [], [], []
        for label, number in quantities.items():
            if number is None:
                exact.append((label, None)); projected.append((label, None)); hex_values.append((label, None)); errors.append((label, None))
                continue
            mw = _q(number) * scale
            represented = float(mw)
            if not isfinite(represented) or (mw > 0 and represented == 0):
                raise ValueError('nonfinite or underflowed MW projection')
            error = abs(Q.from_float(represented) - mw)
            exact.append((label, (str(mw.numerator), str(mw.denominator))))
            projected.append((label, represented)); hex_values.append((label, represented.hex())); errors.append((label, float(error)))
        baseline = _q(hour.workload_occupancy) * scale
        if baseline != _q(normal.request.dc_requested_mw[t]):
            raise ValueError('normal requested baseline differs from mapped business baseline')
        alignment = abs(baseline - Q.from_float(float(normal.request.dc_requested_mw[t])))
        actual = action.actual_service_power * scale
        if actual > min(_q(normal.request.dc_physical_maximum_mw[t]), _q(normal.request.dc_connected_capacity_mw[t])):
            raise ValueError('actual business power exceeds physical or connected capacity')
        rows.append(BusinessPowerHour(hour.power_source_hour, hour.workload_source_hour,
            tuple(exact), tuple(projected), tuple(hex_values), tuple(errors), float(alignment)))
    return grid_id, prefix, tuple(rows)


def business_grid_identity(inputs):
    grid_id, prefix, rows = _validated(inputs)
    # The prefix bytes bind the full business replay, Fraction ledger, sources,
    # normalization provenance, policy, and all business implementation hashes.
    root = Path(__file__).resolve().parent
    implementation = tuple((name, sha256((root / name).read_bytes()).hexdigest())
        for name in ('business_grid.py', 'outage_assignment.py'))
    return _digest(CONTRACT, grid_id, prefix_digest(prefix), inputs.normalized_unit_mw,
        inputs.power_mapping, inputs.source_pairing, inputs.parameter_role, rows, implementation)


def build_business_grid_model(inputs, *, expected_identity):
    _sha(expected_identity)
    grid_id, _, rows = _validated(inputs)
    if business_grid_identity(inputs) != expected_identity:
        raise ValueError('business grid identity mismatch')
    model = build_outage_trajectory_model(inputs.network, expected_identity=grid_id)
    # Reuse only generation/redispatch/ramp/repair/topology constraints. Replace
    # the old net-curtailment problem with prescribed actual load at every hour.
    model.del_component(model.balance)
    model.del_component(model.objective)
    model.del_component(model.curtailment)
    model.actual_dc_power = Param(model.TIME, initialize={t: dict(row.projected_mw)['actual_power'] for t, row in enumerate(rows)})
    model.business_balance = ConstraintList()
    normal = inputs.network.normal_inputs
    data = normal.data
    for t, h in enumerate(normal.source_hours):
        point = data.hourly_points[h - 1]
        for bus in model.BUS:
            generated = sum(model.generation[t, g.uid] for g in data.generators if g.bus == bus)
            exported = sum(model.branch_flow[t, b.uid] for b in data.branches if b.from_bus == bus)
            exported -= sum(model.branch_flow[t, b.uid] for b in data.branches if b.to_bus == bus)
            exported += sum(model.dc_flow[t, b.uid] for b in data.dc_branches if b.from_bus == bus)
            exported -= sum(model.dc_flow[t, b.uid] for b in data.dc_branches if b.to_bus == bus)
            demand = point.demand_by_bus_mw[bus]
            if bus == normal.request.dc_bus:
                demand += model.actual_dc_power[t]
            model.business_balance.add(generated - demand == exported)
    model.objective = Objective(expr=0.)
    return model


@dataclass(frozen=True, init=False)
class BusinessGridWitness:
    contract: str
    input_identity: str
    business_prefix_sha256: str
    policy_id: str
    arm_id: str
    mapped_hours: tuple[BusinessPowerHour, ...]
    network_assignment: tuple
    maximum_fixed_violation: float | None
    maximum_bound_violation: float | None
    maximum_constraint_violation: float | None
    maximum_exact_power_balance_violation: float | None
    errors: tuple[str, ...]
    grid_service_applicable: bool
    cfe_service_applicable: bool
    effective_applicable_requests_fully_served: bool
    grid_obligation_certificate: None
    causal_grid_dispatch_certificate: None
    information_mode: str
    full_service_completion: None
    formal_result: bool
    security_certified: bool

    def __init__(self, *args, **kwargs):
        raise TypeError('business grid witness requires canonical joint audit')

    @property
    def result_id(self):
        return _digest(self)

    @property
    def physical_network_assignment_valid(self):
        return not self.errors


def audit_business_grid_assignment(inputs, assignment, *, expected_identity):
    model = build_business_grid_model(inputs, expected_identity=expected_identity)
    variables = {v.name: v for v in model.component_data_objects(Var)}
    if (type(assignment) is not dict or any(type(k) is not str for k in assignment)
            or set(assignment) != set(variables)):
        raise ValueError('complete canonical business network assignment required')
    fixed = bounds = residual = 0.
    for name, variable in variables.items():
        raw = _finite(assignment[name])
        if variable.fixed:
            fixed = max(fixed, abs(raw - value(variable)))
        if variable.lb is not None:
            bounds = max(bounds, value(variable.lb) - raw)
        if variable.ub is not None:
            bounds = max(bounds, raw - value(variable.ub))
        variable.set_value(raw, skip_validation=True)
    for constraint in model.component_data_objects(Constraint, active=True):
        body = value(constraint.body, exception=False)
        if body is None or not isfinite(body):
            residual = float('inf'); break
        if constraint.lower is not None:
            residual = max(residual, value(constraint.lower) - body)
        if constraint.upper is not None:
            residual = max(residual, body - value(constraint.upper))
    errors = tuple('canonical_business_grid_' + label + '_violation' for label, amount in
        (('fixed', fixed), ('bound', bounds), ('constraint', residual)) if amount > 1e-6)
    fixed, bounds, residual = (x if isfinite(x) else None for x in (fixed, bounds, residual))
    _, prefix, rows = _validated(inputs)
    # Independently check nodal power using decimal-exact original business MW,
    # rather than trusting the binary64 load projection in the Pyomo expression.
    exact_residual = Q(0)
    normal = inputs.network.normal_inputs
    data = normal.data
    for t, row in enumerate(rows):
        numerator, denominator = dict(row.exact_mw)['actual_power']
        actual = Q(int(numerator), int(denominator))
        point = data.hourly_points[normal.source_hours[t] - 1]
        for bus in data.buses:
            generated = sum((_q(assignment[f'generation[{t},{g.uid}]']) for g in data.generators if g.bus == bus.uid), Q(0))
            exported = Q(0)
            for label, branches in (('branch_flow', data.branches), ('dc_flow', data.dc_branches)):
                for branch in branches:
                    flow = _q(assignment[f'{label}[{t},{branch.uid}]'])
                    exported += flow * ((branch.from_bus == bus.uid) - (branch.to_bus == bus.uid))
            demand = _q(point.demand_by_bus_mw[bus.uid]) + (actual if bus.uid == normal.request.dc_bus else Q(0))
            exact_residual = max(exact_residual, abs(generated - exported - demand))
    if exact_residual > Q('1e-6'):
        errors += ('exact_mapped_power_balance_violation',)
    try:
        exact_report = float(exact_residual)
    except OverflowError:
        exact_report = None
    if exact_report is not None and not isfinite(exact_report):
        exact_report = None
    served = all(x is None or x == 0 for record in inputs.business_prefix.records
        for x in (record.response.grid_shortfall, record.response.cfe_shortfall))
    return _owned(BusinessGridWitness, CONTRACT, expected_identity, prefix_digest(prefix),
        inputs.business_prefix.policy_id, inputs.business_prefix.spec.arm_id, rows, tuple(sorted(assignment.items())),
        fixed, bounds, residual, exact_report, errors, inputs.business_prefix.spec.arm_id != CFE,
        inputs.business_prefix.spec.arm_id != NETWORK, served, None, None, inputs.network.information_mode, None, False, False)
