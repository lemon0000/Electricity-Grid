"""User-authorized, separately audited generation-domain projection.

Raw assignments remain immutable evidence. This rule supplies a candidate, not
native provenance or an exact mathematical certificate. No solver is called.
"""
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from pyomo.environ import Var, value

from . import normal_h1_model as model_api

SCHEMA = 'h1_generation_domain_projection_v2'
EPSILON = 1e-9
RAW_DOMAIN_ERROR = 'unit_chronology: generation_mw must be a finite nonnegative number'


class ProjectionRejected(ValueError):
    def __init__(self, message, receipt):
        super().__init__(message)
        self.receipt = receipt


def implementation_identity():
    return model_api._digest(SCHEMA, EPSILON.hex(),
        sha256(Path(model_api.__file__).read_bytes()).hexdigest(),
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
    if type(EPSILON) is not float or EPSILON.hex() != float(1e-9).hex():
        raise ValueError('frozen generation-domain epsilon drift')
    raw_audit = model_api.audit_h1_assignment(request, assignment,
                                             expected_identity=expected_identity)
    if (raw_audit.canonical_objective.hex() != raw_objective_hex
            or any(error != RAW_DOMAIN_ERROR for error in raw_audit.errors)):
        raise ValueError('raw objective or non-domain assignment audit rejected')
    model = model_api.build_h1_stage_model(request, expected_identity=expected_identity)
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
    audit = model_api.audit_h1_assignment(request, candidate,
                                         expected_identity=expected_identity)
    for variable in model.component_data_objects(Var):
        variable.set_value(candidate[variable.name], skip_validation=True)
    if any(not constraint.equality for constraint in model.power_balance.values()):
        raise ValueError('canonical equality power-balance rows required')
    balance = max((abs(float(value(constraint.body))-float(value(constraint.lower)))
                   for constraint in model.power_balance.values()), default=0.0)
    accepted = (not audit.errors and audit.canonical_objective.hex() == raw_objective_hex
                and balance <= EPSILON and all(r <= EPSILON for r in audit.lock_residuals))
    receipt = dict(schema=SCHEMA, rule_identity=implementation_identity(),
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
