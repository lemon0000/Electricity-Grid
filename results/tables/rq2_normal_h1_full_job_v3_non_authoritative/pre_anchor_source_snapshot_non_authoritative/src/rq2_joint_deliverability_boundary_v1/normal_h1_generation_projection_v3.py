"""User-authorized, separately audited generation-domain projection.

Raw assignments remain immutable evidence. This rule supplies a candidate, not
native provenance or an exact mathematical certificate. No solver is called.
"""
from dataclasses import asdict, fields
from hashlib import sha256
from pathlib import Path
from math import isfinite
from pyomo.environ import Var, value

from . import normal_h1_model as model_api
from . import continuous_grid_normal as normal
from . import normal_h1_generation_projection_v2 as rule

SCHEMA = rule.SCHEMA
EPSILON = 1e-9
RAW_DOMAIN_ERROR = 'unit_chronology: generation_mw must be a finite nonnegative number'


class ProjectionRejected(ValueError):
    def __init__(self, message, receipt):
        super().__init__(message)
        self.receipt = receipt


def implementation_identity():
    return model_api._digest('h1_scoped_assignment_audit_v3', rule.implementation_identity(), EPSILON.hex(),
        sha256(Path(model_api.__file__).read_bytes()).hexdigest(),
        sha256(Path(normal.__file__).read_bytes()).hexdigest(),
        sha256(Path(__file__).read_bytes()).hexdigest())


def assignment_identity(assignment):
    return model_api._digest(tuple(sorted((name, float(value).hex())
                                         for name, value in assignment.items())))


def project_and_audit(request, assignment, *, expected_identity, raw_objective_hex):
    """Change only normal generation in [-1e-9,0); fully re-audit the candidate.

An original objective hex mismatch, other raw audit error, or any candidate
error rejects. In particular, clipping the active generation objective usually
changes its hex and is rejected; this rule is not an optimization repair.
"""
    _frozen_thresholds()
    if model_api.RESIDUAL_LIMIT != 1e-9 or type(model_api.RESIDUAL_LIMIT) is not float:
        raise ValueError('H1 normal residual gate drift')
    model = model_api.build_h1_stage_model(request, expected_identity=expected_identity)
    return _project_and_audit_built(request, assignment, model,
        expected_identity=expected_identity, raw_objective_hex=raw_objective_hex)


def _project_and_audit_built(request, assignment, model, *, expected_identity, raw_objective_hex):
    """Private canonical build/clone before any assignment load; no shared state."""
    _frozen_thresholds()
    variables = {v.name: v for v in model.component_data_objects(Var)}
    fixed = {name: value(v) for name, v in variables.items() if v.fixed}
    raw_audit = _audit_on_model(request, assignment, model, variables, fixed, expected_identity)
    if (raw_audit.canonical_objective.hex() != raw_objective_hex
            or any(error != RAW_DOMAIN_ERROR for error in raw_audit.errors)):
        raise ValueError('raw objective or non-domain assignment audit rejected')
    names = {variable.name for key, variable in model.generation.items()
             if key[0] == 'normal' and key[1] == 0}
    candidate = dict(assignment)
    changes = []
    for name in sorted(names):
        amount = assignment[name]
        if -EPSILON <= amount < 0:
            candidate[name] = 0.0
            changes.append([name, float(amount).hex(), 0.0.hex(), float(-amount).hex()])
    if raw_audit.errors and not changes:
        raise ValueError('raw chronology error has no authorized generation mapping')
    audit = _audit_on_model(request, candidate, model, variables, fixed, expected_identity)
    for variable in model.component_data_objects(Var):
        variable.set_value(candidate[variable.name], skip_validation=True)
    if any(not constraint.equality for constraint in model.power_balance.values()):
        raise ValueError('canonical equality power-balance rows required')
    balance = max((abs(float(value(constraint.body))-float(value(constraint.lower)))
                   for constraint in model.power_balance.values()), default=0.0)
    accepted = (not audit.errors and audit.canonical_objective.hex() == raw_objective_hex
                and balance <= EPSILON and all(r <= EPSILON for r in audit.lock_residuals))
    _frozen_thresholds()
    if model_api.h1_stage_identity(request) != expected_identity:
        raise ValueError('H1 stage input/lock/dependency identity changed during audit')
    receipt = dict(schema=SCHEMA, rule_identity=rule.implementation_identity(),
        epsilon_hex=EPSILON.hex(), raw_assignment_identity=assignment_identity(assignment),
        candidate_assignment_identity=assignment_identity(candidate), changes=changes,
        normalization_applied=bool(changes), candidate_accepted=accepted,
        raw_audit=asdict(raw_audit), candidate_audit=asdict(audit),
        maximum_power_balance_residual=balance,
        raw_objective_hex=raw_objective_hex, solver_calls=0,
        exact_mathematical_certificate=False, native_execution_authenticated=False,
        formal_result=False)
    if not accepted:
        raise ProjectionRejected('normalized candidate full assignment/objective audit rejected', receipt)
    return candidate, audit, receipt


def _audit_on_model(request, assignment, model, variables, fixed, expected_identity):
    """Private call-local canonical model; independently evaluate both assignments.

    Fixed baselines precede either assignment. Deactivating only added H1 locks
    reproduces the original normal-model residual, then restores the same rows.
    No model, assignment, identity or audit cache survives project_and_audit.
    """
    _frozen_thresholds()
    if type(assignment) is not dict or set(assignment) != set(variables):
        raise ValueError('complete H1 assignment required')
    errors = []
    legacy_errors = []
    for name, variable in variables.items():
        amount = assignment[name]
        if type(amount) not in (float, int) or not isfinite(amount):
            raise ValueError('finite built-in H1 assignment values required')
        if name in fixed and abs(amount-fixed[name]) > model_api.RESIDUAL_LIMIT:
            errors.append(f'fixed_variable_violation: {name}')
        if ((variable.lb is not None and amount < value(variable.lb)-model_api.RESIDUAL_LIMIT)
                or (variable.ub is not None and amount > value(variable.ub)+model_api.RESIDUAL_LIMIT)):
            errors.append(f'variable_bound_violation: {name}')
        if name in fixed and abs(amount-fixed[name]) > normal.TOLERANCE:
            legacy_errors.append(f'fixed_variable_violation: {name}')
        variable.set_value(amount, skip_validation=True)
    residual = model_api._constraint_violation(model)
    integer = model_api._integrality_violation(model)
    if residual > model_api.RESIDUAL_LIMIT:
        errors.append('h1_normal_constraint_violation')
    if integer > model_api.RESIDUAL_LIMIT:
        errors.append('h1_normal_integrality_violation')
    expressions = model_api._expressions(model, model_api.stage_order(request.inputs))
    locks = tuple(abs(float(value(expr))-locked)
                  for expr, locked in zip(expressions, request.locked_values))
    model.h1_prior_objective_locks.deactivate()
    try:
        legacy_residual = model_api._constraint_violation(model)
    finally:
        model.h1_prior_objective_locks.activate()
    if legacy_residual > normal.TOLERANCE:
        legacy_errors.append('canonical_normal_constraint_violation')
    if integer > normal.TOLERANCE:
        legacy_errors.append('commitment_integrality_violation')
    if not legacy_errors:
        inputs = request.inputs
        try:
            hours = tuple(normal.GridHour(inputs.carry.identity, source_hour, tuple(
                normal.UnitPoint(p.uid, bool(round(model.commitment[t, p.uid].value)),
                                 model.generation['normal', t, p.uid].value)
                for p in inputs.carry.points)) for t, source_hour in enumerate(inputs.source_hours))
            normal.replay_grid_chunk(inputs.carry, hours)
        except ValueError as error:
            legacy_errors.append(f'unit_chronology: {error}')
    errors.extend(legacy_errors)
    result = object.__new__(model_api.H1AssignmentAudit)
    payload = (expected_identity, model_api._digest(assignment), float(value(model.objective)),
               locks, residual, integer, tuple(errors), 'derived_h1_assignment_audit_no_native_optimality')
    for field, item in zip(fields(model_api.H1AssignmentAudit), payload, strict=True):
        object.__setattr__(result, field.name, item)
    return result


def _frozen_thresholds():
    if (type(EPSILON) is not float or EPSILON.hex()!=float(1e-9).hex()
            or type(rule.EPSILON) is not float or rule.EPSILON.hex()!=float(1e-9).hex()):
        raise ValueError('frozen generation-domain epsilon drift')
    if type(model_api.RESIDUAL_LIMIT) is not float or model_api.RESIDUAL_LIMIT.hex()!=float(1e-9).hex():
        raise ValueError('H1 normal residual gate drift')
    if type(normal.TOLERANCE) is not float or normal.TOLERANCE.hex()!=float(1e-6).hex():
        raise ValueError('legacy normal tolerance drift')
