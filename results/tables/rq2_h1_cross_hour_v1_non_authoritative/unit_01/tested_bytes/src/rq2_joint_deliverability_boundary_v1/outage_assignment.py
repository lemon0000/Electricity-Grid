"""Draft canonical outage assignment audit and replay of one bound offline path.

No solver provenance, optimal bound, causal policy or new-window origin is issued.
"""
from dataclasses import dataclass, fields
from hashlib import sha256
from math import isfinite
from pathlib import Path

from pyomo.environ import Constraint, Var, value

from .continuous_grid_normal import _digest
from .grid_carry import GridCarry, GridHour, UnitPoint, replay_grid_chunk
from .outage_trajectory import build_outage_trajectory_model, _validate, _sha
from ..scenarios.rts_gmlc_n1_chronology import N1OutageEvent


TOLERANCE = 1e-6
CONTRACT = 'canonical_outage_assignment_same_full_offline_path_replay_v1'


def _owned(kind, *items):
    result = object.__new__(kind)
    for field, item in zip(fields(kind), items, strict=True):
        object.__setattr__(result, field.name, item)
    return result


@dataclass(frozen=True, init=False)
class OutageAssignmentWitness:
    contract: str
    feasibility_tolerance: float
    input_identity: str
    assignment: tuple[tuple[str, float], ...]
    maximum_fixed_violation: float | None
    maximum_bound_violation: float | None
    maximum_constraint_violation: float | None
    objective_value: float | None
    errors: tuple[str, ...]
    implementation_identity: str
    evidence_role: str

    def __init__(self, *args, **kwargs):
        raise TypeError('outage witness requires canonical audit')

    @property
    def result_id(self):
        return _digest(self)


@dataclass(frozen=True, init=False)
class OutageReplayCarry:
    full_input_identity: str
    full_assignment_identity: str
    normal_candidate_id: str
    source_hour: int
    generation_mw: tuple[tuple[str, float], ...]
    availability: tuple[tuple[str, bool], ...]
    active_event: N1OutageEvent | None
    normal_carry: GridCarry
    evidence_role: str

    def __init__(self, *args, **kwargs):
        raise TypeError('outage carry requires verified same-path replay')


def _finite(number):
    if type(number) not in (int, float) or not isfinite(number):
        raise ValueError('assignment requires finite built-in numbers')
    return number


def audit_outage_assignment(inputs, assignment, *, expected_identity):
    """Audit supplied original values against a fresh complete canonical model."""
    if (type(CONTRACT) is not str or CONTRACT != 'canonical_outage_assignment_same_full_offline_path_replay_v1'
            or type(TOLERANCE) is not float or TOLERANCE != 1e-6):
        raise ValueError('outage assignment audit contract or tolerance drift')
    model = build_outage_trajectory_model(inputs, expected_identity=expected_identity)
    variables = {v.name: v for v in model.component_data_objects(Var)}
    if (type(assignment) is not dict or any(type(k) is not str for k in assignment)
            or set(assignment) != set(variables)):
        raise ValueError('complete canonical outage variable inventory required')
    fixed = bounds = residual = 0.
    errors = []
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
            residual = float('inf')
            break
        if constraint.lower is not None:
            residual = max(residual, value(constraint.lower) - body)
        if constraint.upper is not None:
            residual = max(residual, body - value(constraint.upper))
    for label, amount in (('fixed', fixed), ('bound', bounds), ('constraint', residual)):
        if amount > TOLERANCE:
            errors.append('canonical_outage_' + label + '_violation')
    objective = value(model.objective, exception=False)
    if objective is None or not isfinite(objective):
        objective = None
        errors.append('nonfinite_outage_objective')
    # Preserve raw assignment and a finite identity even for numerical overflow.
    fixed, bounds, residual = (x if isfinite(x) else None for x in (fixed, bounds, residual))
    return _owned(OutageAssignmentWitness, CONTRACT, TOLERANCE, expected_identity, tuple(sorted(assignment.items())),
        fixed, bounds, residual, objective, tuple(errors), sha256(Path(__file__).read_bytes()).hexdigest(),
        'derived_offline_assignment_witness')


def _carry_at(inputs, witness, source_hour):
    normal = inputs.normal_inputs
    last = normal.source_hours.index(source_hour)
    baseline = dict(inputs.normal_candidate.normal.loaded_values)
    hours = tuple(GridHour(normal.carry.identity, normal.source_hours[t], tuple(
        UnitPoint(p.uid, bool(round(baseline[f'commitment[{t},{p.uid}]'])),
                  baseline[f'generation[normal,{t},{p.uid}]'])
        for p in normal.carry.points)) for t in range(last + 1))
    normal_carry = replay_grid_chunk(normal.carry, hours)
    events, _ = _validate(inputs)
    event = events[last]
    generators = sorted(normal.data.generators, key=lambda g: g.uid)
    assignment = dict(witness.assignment)
    generation = tuple((g.uid, assignment[f'generation[{last},{g.uid}]']) for g in generators)
    availability = tuple((g.uid, g.enabled and not (event is not None
        and event.component_type == 'generator' and event.uid == g.uid)) for g in generators)
    return _owned(OutageReplayCarry, witness.input_identity, witness.result_id,
        inputs.normal_candidate.result_id, source_hour, generation, availability, event, normal_carry,
        'derived_offline_assignment_witness')


def replay_outage_chunk(inputs, witness, source_hours, *, expected_identity, before=None):
    """Replay a contiguous slice of the same accepted full offline assignment.

    Re-audit the complete original assignment on import. A carry is not accepted
    as an origin for another problem or as permission to re-optimize a suffix.
    """
    _sha(expected_identity)
    if type(witness) is not OutageAssignmentWitness:
        raise ValueError('typed outage assignment witness required')
    fresh = audit_outage_assignment(inputs, dict(witness.assignment), expected_identity=expected_identity)
    if witness != fresh or fresh.errors:
        raise ValueError('accepted current full outage assignment required')
    if (type(source_hours) is not tuple or not source_hours
            or any(type(h) is not int for h in source_hours)):
        raise ValueError('nonempty integer source-hour slice required')
    normal = inputs.normal_inputs
    first = normal.source_hours[0]
    if before is not None:
        if type(before) is not OutageReplayCarry or before.source_hour not in normal.source_hours:
            raise ValueError('same-path actual carry required')
        if before != _carry_at(inputs, fresh, before.source_hour):
            raise ValueError('outage carry does not match full assignment prefix')
        first = before.source_hour + 1
    if (source_hours != tuple(range(first, first + len(source_hours)))
            or source_hours[-1] > normal.source_hours[-1]):
        raise ValueError('outage replay source-hour gap or range mismatch')
    return _carry_at(inputs, fresh, source_hours[-1])
