"""H1 normal model and declared initial state; no solve or acceptance certificate.

Locked values must ultimately come from independently audited prior stages.
This construction API alone does not establish their provenance or causality.
"""
from dataclasses import dataclass, fields
from hashlib import sha256
from math import ceil, isfinite, copysign
from pathlib import Path

from pyomo.environ import ConstraintList, Var, value

from ..grid.rts_gmlc import RtsGmlcChronologicalGenerator, RtsGmlcHourlyPoint
from ..grid.rts_gmlc_scuc import RtsGmlcInitialState, _constraint_violation, _integrality_violation
from .continuous_grid_normal import (
    ContinuousNormalInputs, _digest, normal_input_identity, build_continuous_normal_model,
    audit_normal_assignment,
)


CONTRACT = 'h1_normal_incumbent_anchored_lex_model_v1'
RESIDUAL_LIMIT = 1e-9


def _number(x, name):
    if type(x) not in (int, float) or not isfinite(x) or x < 0:
        raise ValueError(f'{name}: finite nonnegative built-in number required')
    return x


def _generators(items):
    if (type(items) is not tuple or not items
            or any(type(g) is not RtsGmlcChronologicalGenerator for g in items)):
        raise ValueError('typed nonempty generator tuple required')
    names = [g.uid for g in items]
    if any(type(uid) is not str or not uid for uid in names) or len(set(names)) != len(names):
        raise ValueError('unique nonempty generator UID required')
    for g in items:
        if (g.dispatch_mode not in ('committable', 'fixed', 'curtailable', 'disabled')
                or type(g.enabled) is not bool or g.enabled != (g.dispatch_mode != 'disabled')):
            raise ValueError('generator mode/enabled mismatch')
    return tuple(sorted(items, key=lambda g: g.uid))


def declared_normal_initial(generators, current):
    """Unique mechanism initial state, using only the revealed first base row."""
    units = _generators(generators)
    if type(current) is not RtsGmlcHourlyPoint:
        raise ValueError('typed current base row required')
    names = {g.uid for g in units}
    if set(current.generator_min_mw) != names or set(current.generator_max_mw) != names:
        raise ValueError('complete current generation bounds required')
    on, power, age = {}, {}, {}
    for g in units:
        lo = _number(current.generator_min_mw[g.uid], 'current lower')
        hi = _number(current.generator_max_mw[g.uid], 'current upper')
        maximum = _number(g.p_max_mw, 'static maximum')
        if lo > hi or hi > maximum:
            raise ValueError('invalid current/static generation bounds')
        if g.dispatch_mode == 'committable':
            on[g.uid], power[g.uid] = False, 0.0
            age[g.uid] = ceil(_number(g.minimum_down_time_hours, 'minimum down'))
        elif g.dispatch_mode == 'disabled':
            if lo != 0 or hi != 0:
                raise ValueError('disabled generator requires zero current bounds')
            on[g.uid], power[g.uid], age[g.uid] = False, 0.0, 0
        else:
            if g.dispatch_mode == 'fixed' and abs(hi - lo) > 1e-9:
                raise ValueError('fixed generator has unequal bounds')
            on[g.uid] = True
            power[g.uid] = float(hi if g.dispatch_mode == 'fixed' else lo)
            age[g.uid] = 0
    return RtsGmlcInitialState(on, power, age, 'h1_declared_first_base_row_mechanism_v1')


def stage_order(inputs):
    """Canonical objective sequence; not a decision identity or source adapter."""
    if type(inputs) is not ContinuousNormalInputs:
        raise ValueError('exact typed normal input required')
    if (len(inputs.request.timestamps) != 1 or len(inputs.source_hours) != 1
            or len(inputs.data.hourly_points) != 1):
        raise ValueError('H1 requires exactly one base row and one request hour')
    units = _generators(inputs.data.generators)
    return (('operating_cost', None),
            *(('commitment', g.uid) for g in units if g.dispatch_mode == 'committable'),
            *(('generation', g.uid) for g in units))


@dataclass(frozen=True)
class H1StageRequest:
    inputs: ContinuousNormalInputs
    locked_values: tuple[float, ...] = ()

    def __post_init__(self):
        order = stage_order(self.inputs)
        if type(self.locked_values) is not tuple or len(self.locked_values) >= len(order):
            raise ValueError('one unfinished H1 stage required')
        for (kind, _), amount in zip(order, self.locked_values):
            if type(amount) is not float:
                raise ValueError('binary64 lock value required')
            _number(amount, 'lock value')
            if amount == 0 and copysign(1.0, amount) < 0:
                raise ValueError('negative zero lock is not canonical')
            if kind == 'commitment' and amount not in (0.0, 1.0):
                raise ValueError('commitment lock must be audited zero or one')


def h1_stage_identity(request):
    """Audit/model identity. Deliberately not a causal shared-prefix key."""
    if type(request) is not H1StageRequest:
        raise ValueError('exact H1 stage request required')
    request.__post_init__()
    return _digest(CONTRACT, normal_input_identity(request.inputs),
                   stage_order(request.inputs), tuple(x.hex() for x in request.locked_values),
                   sha256(Path(__file__).read_bytes()).hexdigest())


def _expressions(model, order):
    return tuple(model.operating_cost if kind == 'operating_cost'
                 else model.commitment[0, uid] if kind == 'commitment'
                 else model.generation['normal', 0, uid] for kind, uid in order)


def build_h1_stage_model(request, *, expected_identity):
    if (type(expected_identity) is not str or len(expected_identity) != 64
            or any(c not in '0123456789abcdef' for c in expected_identity)):
        raise ValueError('built-in lowercase H1 SHA256 identity required')
    if h1_stage_identity(request) != expected_identity:
        raise ValueError('H1 stage input/lock/dependency identity mismatch')
    inputs = request.inputs
    model = build_continuous_normal_model(inputs, expected_identity=normal_input_identity(inputs))
    expressions = _expressions(model, stage_order(inputs))
    model.h1_prior_objective_locks = ConstraintList()
    for expression, amount in zip(expressions, request.locked_values):
        model.h1_prior_objective_locks.add(expression == amount)
    model.objective.set_value(expressions[len(request.locked_values)])
    return model


@dataclass(frozen=True, init=False)
class H1AssignmentAudit:
    stage_identity: str
    assignment_identity: str
    canonical_objective: float
    lock_residuals: tuple[float, ...]
    maximum_constraint_violation: float
    maximum_integrality_violation: float
    errors: tuple[str, ...]
    evidence_role: str = 'derived_h1_assignment_audit_no_native_optimality'

    def __init__(self, *args, **kwargs):
        raise TypeError('H1 assignment audit requires canonical reconstruction')


def audit_h1_assignment(request, assignment, *, expected_identity):
    """Rebuild all original and lock constraints; no native optimality claim."""
    if RESIDUAL_LIMIT != 1e-9 or type(RESIDUAL_LIMIT) is not float:
        raise ValueError('H1 normal residual gate drift')
    model = build_h1_stage_model(request, expected_identity=expected_identity)
    variables = {v.name: v for v in model.component_data_objects(Var)}
    if type(assignment) is not dict or set(assignment) != set(variables):
        raise ValueError('complete H1 assignment required')
    errors = []
    for name, variable in variables.items():
        amount = assignment[name]
        if type(amount) not in (float, int) or not isfinite(amount):
            raise ValueError('finite built-in H1 assignment values required')
        if variable.fixed and abs(amount - value(variable)) > RESIDUAL_LIMIT:
            errors.append(f'fixed_variable_violation: {name}')
        if ((variable.lb is not None and amount < value(variable.lb)-RESIDUAL_LIMIT)
                or (variable.ub is not None and amount > value(variable.ub)+RESIDUAL_LIMIT)):
            errors.append(f'variable_bound_violation: {name}')
        variable.set_value(amount, skip_validation=True)
    residual, integer = _constraint_violation(model), _integrality_violation(model)
    if residual > RESIDUAL_LIMIT:
        errors.append('h1_normal_constraint_violation')
    if integer > RESIDUAL_LIMIT:
        errors.append('h1_normal_integrality_violation')
    expressions = _expressions(model, stage_order(request.inputs))
    locks = tuple(abs(float(value(expr))-locked)
                  for expr, locked in zip(expressions, request.locked_values))
    # This replay validates chronology too; its older tolerance never overrides
    # the stricter checks above, and it supplies no solve provenance.
    legacy = audit_normal_assignment(request.inputs, assignment,
                                    expected_identity=normal_input_identity(request.inputs))
    errors.extend(legacy.errors)
    result = object.__new__(H1AssignmentAudit)
    payload = (expected_identity, _digest(assignment), float(value(model.objective)),
               locks, residual, integer, tuple(errors), 'derived_h1_assignment_audit_no_native_optimality')
    for field, item in zip(fields(H1AssignmentAudit), payload, strict=True):
        object.__setattr__(result, field.name, item)
    return result
