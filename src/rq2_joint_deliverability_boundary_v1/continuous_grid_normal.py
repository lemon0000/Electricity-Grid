"""Draft continuous normal-state SCUC and canonical assignment witness.

No solve, contingency certificate, production manifest or formal gate is emitted.
The original RTS-GMLC core is reused with explicit incoming dwell obligations.
"""
from copy import deepcopy
from dataclasses import dataclass, fields, is_dataclass
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
from math import ceil, isfinite
from pathlib import Path
import platform

from pyomo.environ import ConstraintList, Var

from ..grid.chronological_dispatch import _validate_request
from ..grid import rts_gmlc_scuc as scuc
from ..evaluation.flexibility_envelope import ChronologicalFlexibilityTrace, evaluate_chronological_flexibility
from .grid_carry import GridCarry, GridHour, UnitLimits, UnitPoint, replay_grid_chunk


TOLERANCE = 1e-6
CONTRACT = 'continuous_normal_fixed_initial_integer_age_ceil_minimum_open_terminal_v1'
SOURCE_DEPENDENCIES = ('src/__init__.py', *(f'src/{group}/{name}.py' for group, names in (
    ('evaluation', ('__init__', 'capacity_metrics', 'chronology_inputs', 'economic_holdout',
                    'flexibility_envelope', 'service_risk', 'stochastic_policy')),
    ('grid', ('__init__', 'ac_case', 'ac_restoration', 'ac_validation', 'chronological_dispatch',
              'contingency', 'dc_opf', 'network_grid_need', 'rts24', 'rts_gmlc', 'rts_gmlc_scuc', 'scopf')),
    ('models', ('__init__', 'deterministic_baselines', 'deterministic_expansion', 'deterministic_fx',
                'economic_stochastic', 'rq2_network_grid_need', 'stochastic_baselines')),
    ('rq2_joint_deliverability_boundary_v1', ('__init__', 'continuous_grid_normal', 'grid_carry')),
    ('scenarios', ('__init__', 'common_input_signature', 'frozen_tree', 'rts_gmlc_cfe_deficit',
                   'scenario_reduction', 'temporal_scenario_reduction',
                   'temporal_trace_scenario_generator', 'trace_scenario_generator')),
    ('solvers', ('__init__', 'osqp_qp')),
) for name in names))
RUNTIME_DISTRIBUTIONS = ('Pyomo', 'highspy', 'numpy', 'scipy', 'PYPOWER', 'PyYAML', 'osqp')


def _number(x, name):
    if type(x) not in (int, float) or not isfinite(x):
        raise ValueError(f'{name}: finite built-in number required')
    return x


def _encode(x):
    if is_dataclass(x):
        return [type(x).__name__, [[f.name, _encode(getattr(x, f.name))] for f in fields(x)]]
    if isinstance(x, datetime):
        return ['datetime', x.isoformat()]
    if isinstance(x, dict):
        return ['mapping', sorted([[_encode(k), _encode(v)] for k, v in x.items()], key=repr)]
    if isinstance(x, (tuple, list)):
        return [type(x).__name__, [_encode(v) for v in x]]
    if isinstance(x, (set, frozenset)):
        return ['set', sorted([_encode(v) for v in x], key=repr)]
    if type(x) is float:
        _number(x, 'identity')
        return ['float', x.hex()]
    if x is None or type(x) in (str, int, bool):
        return x
    raise ValueError(f'unsupported input identity type: {type(x).__name__}')


def _digest(*items):
    return sha256(json.dumps(_encode(items), ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def _dependencies():
    root = Path(__file__).resolve().parents[2]
    sources = tuple((name, sha256((root / name).read_bytes()).hexdigest()) for name in SOURCE_DEPENDENCIES)
    runtime = (('python', platform.python_version()), ('implementation', platform.python_implementation()),
               *((name, version(name)) for name in RUNTIME_DISTRIBUTIONS))
    return sources, runtime


@dataclass(frozen=True)
class ContinuousNormalInputs:
    data: object
    request: object
    initial: scuc.RtsGmlcInitialState
    carry: GridCarry
    source_hours: tuple[int, ...]
    source_time_basis: str

    def __post_init__(self):
        # Own caller dictionaries; subsequent mutation of these copies is detected
        # against the caller-held identity at each build/audit entry.
        for name in ('data', 'request', 'initial'):
            object.__setattr__(self, name, deepcopy(getattr(self, name)))
        _validate(self)


def normal_input_identity(inputs):
    _validate(inputs)
    return _digest(CONTRACT, inputs, _dependencies())


def _validate(inputs):
    if type(inputs) is not ContinuousNormalInputs or type(inputs.carry) is not GridCarry:
        raise ValueError('typed continuous normal inputs and carry required')
    data, request, initial, carry = inputs.data, inputs.request, inputs.initial, inputs.carry
    if (type(initial) is not scuc.RtsGmlcInitialState
            or type(initial.source_scope) is not str or not initial.source_scope.strip()):
        raise ValueError('explicit fixed initial source scope required')
    status = request.flexibility_envelope.parameter_status
    if type(status) is not str or not status.strip():
        raise ValueError('explicit business parameter evidence status required')
    _validate_request(request)
    if request.time_step_hours != 1 or request.incidents:
        raise ValueError('one-hour normal counterfactual required')
    zeros = (*request.dc_flexible_demand_mw, *request.dc_recoverable_flexible_mw,
             *request.dc_call_limit_mw, *request.recovery_headroom_mw,
             request.initial_recovery_debt_mwh, request.initial_grid_call_mw,
             request.initial_active_event_duration_hours,
             *request.initial_event_count_by_period.values(),
             *request.initial_curtailment_energy_mwh_by_period.values(),
             request.flexibility_envelope.maximum_recovery_power_mw,
             request.flexibility_envelope.maximum_recovery_debt_mwh)
    if request.initial_has_prior_event or any(_number(x, 'normal flexibility') != 0 for x in zeros):
        raise ValueError('normal baseline requires zero business flexibility and recovery')
    # Reuse the existing business contract, including boundary, period and
    # envelope validation, on the explicitly zero-call normal counterfactual.
    trace_overrides = {'name': 'continuous_normal_zero_business',
        'grid_call_mw': (0.,) * len(request.timestamps),
        'prescribed_recovery_power_mw': (0.,) * len(request.timestamps),
        'call_limit_mw': request.dc_call_limit_mw,
        'boundary_state_status': request.flexibility_boundary_state_status}
    trace = ChronologicalFlexibilityTrace(**{f.name: trace_overrides[f.name]
        if f.name in trace_overrides else getattr(request, f.name)
        for f in fields(ChronologicalFlexibilityTrace)})
    if not evaluate_chronological_flexibility(trace, request.flexibility_envelope, tolerance=TOLERANCE).feasible:
        raise ValueError('invalid normal zero-business boundary or envelope')
    horizon = len(request.timestamps)
    hours = inputs.source_hours
    if (type(hours) is not tuple or len(hours) != horizon
            or any(type(h) is not int for h in hours)
            or hours != tuple(range(carry.source_hour + 1, carry.source_hour + 1 + horizon))
            or hours[-1] > len(data.hourly_points)):
        raise ValueError('source hours must be consecutive one-based source indices after carry')
    if inputs.source_time_basis not in {'aware_source', 'naive_source_labelled_utc'}:
        raise ValueError('explicit source time basis required')
    buses = {b.uid for b in data.buses}
    generators = {g.uid: g for g in data.generators}
    if (len(buses) != len(data.buses) or len(generators) != len(data.generators)
            or not generators or request.dc_bus not in buses or data.reference_bus not in buses):
        raise ValueError('unique complete bus/generator inventory required')
    if _number(data.base_mva, 'base MVA') <= 0:
        raise ValueError('positive base MVA required')
    for group in (data.branches, data.dc_branches):
        if len({b.uid for b in group}) != len(group):
            raise ValueError('duplicate branch inventory')
        for branch in group:
            if branch.from_bus not in buses or branch.to_bus not in buses:
                raise ValueError('branch endpoint absent')
    for branch in data.branches:
        if (_number(branch.reactance_pu, 'reactance') == 0
                or _number(branch.tap_ratio, 'tap') <= 0
                or _number(branch.continuous_rating_mw, 'rating') <= 0):
            raise ValueError('invalid normal AC branch parameters')
    if (len(data.dc_branches) != 1 or data.dc_branches[0].uid != 'DC1'
            or data.dc_branches[0].p_min_mw != -100 or data.dc_branches[0].p_max_mw != 100):
        raise ValueError('RTS-GMLC lossless DC1 +/-100 MW required')
    for left, right in ((initial.commitment, request.initial_commitment),
                        (initial.generation_mw, request.initial_generation_mw),
                        (initial.time_in_state_hours, request.initial_time_in_state_hours)):
        if set(left) != set(generators) or left != right:
            raise ValueError('fixed initial/request inventory or values differ')
    thermal = tuple(sorted(g.uid for g in data.generators if g.dispatch_mode == 'committable'))
    limits = tuple(UnitLimits(uid, generators[uid].p_min_mw, generators[uid].p_max_mw,
        generators[uid].ramp_mw_per_hour, generators[uid].minimum_up_time_hours,
        generators[uid].minimum_down_time_hours) for uid in thermal)
    if carry.limits != limits:
        raise ValueError('carry limits differ from source generator parameters')
    expected_points = tuple(UnitPoint(uid, initial.commitment[uid], initial.generation_mw[uid])
                            for uid in thermal)
    ages = tuple(initial.time_in_state_hours[uid] for uid in thermal)
    if any(type(age) is not int or age < 0 for age in ages):
        raise ValueError('committable initial age must be nonnegative integer')
    if carry.points != expected_points or carry.elapsed_state_hours != ages:
        raise ValueError('carry differs from fixed initial state')
    for generator in data.generators:
        if (generator.bus not in buses or type(generator.enabled) is not bool
                or generator.dispatch_mode not in {'committable', 'fixed', 'curtailable', 'disabled'}
                or generator.enabled != (generator.dispatch_mode != 'disabled')):
            raise ValueError('invalid generator bus/mode/availability')
        for name in ('ramp_mw_per_minute', 'ramp_mw_per_hour', 'cold_start_cost_usd', 'shutdown_cost_usd'):
            if _number(getattr(generator, name), name) < 0:
                raise ValueError('nonnegative ramp and transition costs required')
    points = tuple(data.hourly_points[h - 1] for h in hours)
    areas = {b.area for b in data.buses}
    for t, point in enumerate(points):
        stamp = point.timestamp
        if inputs.source_time_basis == 'naive_source_labelled_utc':
            if stamp.tzinfo is not None:
                raise ValueError('naive source clock declaration inconsistent')
            stamp = stamp.replace(tzinfo=timezone.utc)
        elif stamp.utcoffset() is None:
            raise ValueError('aware source clock required')
        if stamp != request.timestamps[t]:
            raise ValueError('request/source timestamp mismatch')
        if (set(point.demand_by_bus_mw) != buses
                or dict(request.system_demand_by_bus_mw[t]) != point.demand_by_bus_mw):
            raise ValueError('request/source demand mismatch')
        if dict(request.generator_availability[t]) != {g.uid: g.enabled for g in data.generators}:
            raise ValueError('normal generator availability mismatch')
        if set(point.generator_min_mw) != set(generators) or set(point.generator_max_mw) != set(generators):
            raise ValueError('hourly generator bounds inventory mismatch')
        for g in data.generators:
            lower, upper = scuc._generator_bounds(point, g)
            if upper > g.p_max_mw or (g.dispatch_mode == 'committable' and lower < g.p_min_mw):
                raise ValueError('hourly bounds outside static source envelope')
        if set(point.spin_up_requirement_by_area_mw) != areas:
            raise ValueError('complete area reserve requirements required')
        for requirement in point.spin_up_requirement_by_area_mw.values():
            if _number(requirement, 'reserve requirement') < 0:
                raise ValueError('negative reserve requirement')
    return points


def build_continuous_normal_model(inputs, *, expected_identity):
    if (type(expected_identity) is not str or len(expected_identity) != 64
            or any(c not in '0123456789abcdef' for c in expected_identity)):
        raise ValueError('expected identity must be built-in lowercase SHA256 string')
    points = _validate(inputs)
    if normal_input_identity(inputs) != expected_identity:
        raise ValueError('continuous normal input/dependency identity mismatch')
    context = scuc._build_context(inputs.data, inputs.request, points, scuc._security_states((), ()))
    model = scuc._build_model(context, inputs.initial)
    model.initial_residual_dwell = ConstraintList()
    for limit, point, age in zip(inputs.carry.limits, inputs.carry.points,
                                 inputs.carry.elapsed_state_hours, strict=True):
        minimum = ceil(limit.minimum_up_hours if point.committed else limit.minimum_down_hours)
        for t in range(min(len(points), max(minimum - age, 0))):
            model.initial_residual_dwell.add(model.commitment[t, point.uid] == int(point.committed))
    return model


@dataclass(frozen=True, init=False)
class NormalAssignmentWitness:
    input_identity: str
    assignment_identity: str
    maximum_constraint_violation: float
    maximum_integrality_violation: float
    errors: tuple[str, ...]
    terminal_carry: GridCarry | None
    evidence_role: str = 'derived_normal_assignment_development_witness'

    def __init__(self, *args, **kwargs):
        raise TypeError('normal witness is created only by canonical assignment audit')


def audit_normal_assignment(inputs, assignment, *, expected_identity):
    """Rebuild every normal constraint, then independently replay unit chronology.

    This witnesses supplied values only, not their solver origin or optimality.
    Every canonical variable is required, including flows, reserves and segments.
    """
    model = build_continuous_normal_model(inputs, expected_identity=expected_identity)
    variables = {v.name: v for v in model.component_data_objects(Var)}
    if type(assignment) is not dict or set(assignment) != set(variables):
        raise ValueError('complete canonical variable assignment required')
    errors = []
    for name, variable in variables.items():
        candidate = _number(assignment[name], name)
        if variable.fixed and abs(candidate - variable.value) > TOLERANCE:
            errors.append(f'fixed_variable_violation: {name}')
        variable.set_value(candidate, skip_validation=True)
    residual = scuc._constraint_violation(model)
    integer = scuc._integrality_violation(model)
    if residual > TOLERANCE:
        errors.append('canonical_normal_constraint_violation')
    if integer > TOLERANCE:
        errors.append('commitment_integrality_violation')
    terminal = None
    if not errors:
        try:
            hours = tuple(GridHour(inputs.carry.identity, source_hour, tuple(
                UnitPoint(p.uid, bool(round(model.commitment[t, p.uid].value)),
                          model.generation['normal', t, p.uid].value)
                for p in inputs.carry.points)) for t, source_hour in enumerate(inputs.source_hours))
            terminal = replay_grid_chunk(inputs.carry, hours)
        except ValueError as error:
            errors.append(f'unit_chronology: {error}')
    result = object.__new__(NormalAssignmentWitness)
    payload = (expected_identity, _digest(assignment), residual, integer, tuple(errors), terminal,
               'derived_normal_assignment_development_witness')
    for field, item in zip(fields(NormalAssignmentWitness), payload, strict=True):
        object.__setattr__(result, field.name, item)
    return result
