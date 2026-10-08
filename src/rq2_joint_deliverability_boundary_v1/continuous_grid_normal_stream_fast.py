"""Streaming identity successor for unchanged normal model and assignment audit.

Input and witness content remain legacy-compatible; callers must independently
bind this implementation. No solve or source execution is authenticated here.
"""
from dataclasses import fields
from hashlib import sha256
from math import ceil
from pathlib import Path
from pyomo.environ import ConstraintList, Var

from . import continuous_grid_normal as legacy, identity_stream_fast as stream

CONTRACT = 'draft_fast_streaming_continuous_normal_model_v1'
ContinuousNormalInputs, NormalAssignmentWitness = legacy.ContinuousNormalInputs, legacy.NormalAssignmentWitness
scuc, GridHour, UnitPoint, replay_grid_chunk = legacy.scuc, legacy.GridHour, legacy.UnitPoint, legacy.replay_grid_chunk
_validate, _number, TOLERANCE = legacy._validate, legacy._number, legacy.TOLERANCE
normal_input_identity, _digest = stream.normal_input_identity, stream.digest


def implementation_identity():
    return stream.digest(CONTRACT, legacy._dependencies(),
        sha256(Path(__file__).read_bytes()).hexdigest(), sha256(Path(stream.__file__).read_bytes()).hexdigest())


def _check_implementation(expected):
    if (type(expected) is not str or len(expected) != 64
            or any(c not in '0123456789abcdef' for c in expected)
            or implementation_identity() != expected):
        raise ValueError('streaming normal model implementation drift')


def build_continuous_normal_model(inputs, *, expected_identity, expected_implementation_identity):
    if (type(expected_identity) is not str or len(expected_identity) != 64
            or any(c not in '0123456789abcdef' for c in expected_identity)):
        raise ValueError('expected identity must be built-in lowercase SHA256 string')
    _check_implementation(expected_implementation_identity)
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
    _check_implementation(expected_implementation_identity)
    return model


def audit_normal_assignment(inputs, assignment, *, expected_identity, expected_implementation_identity):
    """Rebuild every normal constraint, then independently replay unit chronology.

    This witnesses supplied values only, not their solver origin or optimality.
    Every canonical variable is required, including flows, reserves and segments.
    """
    model = build_continuous_normal_model(inputs, expected_identity=expected_identity,
        expected_implementation_identity=expected_implementation_identity)
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
    _check_implementation(expected_implementation_identity)
    return result
