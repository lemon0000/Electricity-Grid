"""Exact zero-L1 objective proof with separately numerical physical feasibility.

No solver evidence is fabricated. The owner must authenticate the native prefix.
"""
from dataclasses import dataclass
from fractions import Fraction as Q
from hashlib import sha256
from math import isfinite
from pathlib import Path

from pyomo.environ import Var, Objective, minimize, value
from pyomo.repn import generate_standard_repn
from . import scale_selector as scale


def implementation_identity():
    return scale._digest('draft_selector_zero_face_v1',
        sha256(Path(__file__).read_bytes()).hexdigest(),
        tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest())
              for m in (scale, scale.reference, scale.actual, scale.native)))


def _linear(expression):
    repn = generate_standard_repn(expression, compute_values=True)
    if not repn.is_linear():
        raise ValueError('linear zero-face algebra required')
    coefficients = {}
    for variable, coefficient in zip(repn.linear_vars, repn.linear_coefs, strict=True):
        coefficients[variable.name] = coefficients.get(variable.name, Q(0)) + Q.from_float(float(coefficient))
    return Q.from_float(float(repn.constant)), {k: v for k, v in coefficients.items() if v}


def _prove_model_face(model, plan, reference, index):
    """Inspect actual rows: nonnegative deviations, both sides, zero equality.

    Objective constants follow from these rows even if other physical rows are
    infeasible. Feasibility is a separate numerical witness obligation.
    """
    if (not model.objective.active or model.objective.sense != minimize
            or tuple(model.component_data_objects(Objective, active=True)) != (model.objective,)):
        raise ValueError('single active minimization objective required')
    rows = tuple(model.selector_constraints.values())
    if len(rows) != 2*len(plan):
        raise ValueError('complete two-sided deviation rows required')
    for position, (uid, planned) in enumerate(plan):
        deviation = model.selector_deviation[uid]
        if deviation.lb is None or value(deviation.lb) < 0:
            raise ValueError('nonnegative deviation domain required')
        for row, sign in zip(rows[2*position:2*position+2], (1, -1), strict=True):
            expected = (-sign*Q.from_float(float(planned)),
                        {f'generation[{uid}]': Q(sign), f'selector_deviation[{uid}]': Q(-1)})
            if (not row.active or row.lower is not None or row.upper is None
                    or value(row.upper) != 0 or _linear(row.body) != expected):
                raise ValueError('two-sided deviation algebra differs')
    offset = 2 if reference else 1
    if len(model.selector_fixed) != index:
        raise ValueError('complete previous-objective locks required')
    zero_lock = model.selector_fixed[offset]
    if (not zero_lock.active or not zero_lock.equality or value(zero_lock.lower) != 0
            or _linear(zero_lock.body) != (Q(0), {f'selector_deviation[{uid}]': Q(1) for uid, _ in plan})):
        raise ValueError('exact zero L1 equality required')
    if _linear(model.objective.expr) != (Q(0), {f'generation[{plan[index-offset][0]}]': Q(1)}):
        raise ValueError('registered generation-only suffix objective required')


@dataclass(frozen=True, init=False)
class AnalyticStage(scale._Owned):
    index: int
    objective_label: str
    fixed_previous_objectives: tuple
    fixed_previous_objective_hex: tuple
    canonical_objective_hex: str
    evidence_kind: str
    input_identity: str
    policy_identity: str
    implementation_identity: str
    model_structure_identity: str
    assignment: tuple
    assignment_identity: str
    generator_uids: tuple
    objective_exact: tuple
    assignment_witness: object
    maximum_residual: float
    maximum_integrality_violation: float
    solver_calls_by_certificate: int
    analytic_lexicographic_objective_proved: bool
    rigorous_exact_physical_feasibility: bool
    formal_result: bool
    security_certified: bool
    accepted: bool
    errors: tuple


def certify_suffix(info, disclosure, before, *, power, budget, selector, specification,
                   expected_identity, policy_identity, frozen, assignment,
                   expected_implementation):
    """Rebuild every suffix stage. Preconditions include an accepted native prefix.

    Zero means exact decimal-rational zero, matching existing selector witnesses.
    Every generation value must equal its plan exactly, not just within tolerance.
    """
    if implementation_identity() != expected_implementation:
        raise ValueError('zero-face implementation mismatch')
    module = scale._module(budget)
    reference = module is scale.reference
    offset = 2 if reference else 1
    args = (info, disclosure, before) if reference else (info, disclosure, before, power)
    identity = module.reference_input_identity if reference else module.dispatch_input_identity
    if (identity(*args) != expected_identity or (reference and power is not None)
            or (not reference and power is None)):
        raise ValueError('zero-face current input mismatch')
    uids = tuple(g.uid for g in info.network.units)
    scale._admit(selector, specification, budget, len(uids)+offset)
    scale.actual._hash(policy_identity)
    from .scale_selector_zero_face import policy_identity as current_policy_identity
    if (current_policy_identity(selector, specification, budget) != policy_identity
            or (hasattr(before, 'selector_policy_identity')
                and before.selector_policy_identity != policy_identity)):
        raise ValueError('zero-face policy correspondence required')
    plan = info.normal.generation_mw
    if (uids != budget.generator_uids or tuple(uid for uid, _ in plan) != uids
            or uids != tuple(sorted(set(uids))) or info.current.source_hour != budget.source_hour):
        raise ValueError('zero-face complete UID/hour correspondence required')
    if (type(frozen) is not tuple or len(frozen) != offset
            or any(type(x) not in (int, float) or not isfinite(x) for x in frozen)
            or Q(str(frozen[-1])) != 0):
        raise ValueError('exact zero L1 native prefix required')
    if type(assignment) is not tuple or any(type(row) is not tuple or len(row) != 2 for row in assignment):
        raise ValueError('complete immutable assignment required')
    values = dict(assignment)
    if len(values) != len(assignment) or any(type(x) not in (int, float) or not isfinite(x) for x in values.values()):
        raise ValueError('unique finite assignment required')
    for uid, planned in plan:
        if (Q(str(values[f'selector_deviation[{uid}]'])) != 0
                or Q(str(values[f'generation[{uid}]'])) != Q(str(planned))):
            raise ValueError('exact zero deviation and planned generation required')
    physical = {name: x for name, x in values.items() if not name.startswith('selector_deviation[')}
    if reference:
        witness = module.audit_reference_assignment(*args, physical, expected_identity=expected_identity)
        request_value = Q(str(info.current.dc_baseline_mw))-Q(str(values['reference_power']))
        if abs(request_value-Q(str(frozen[0]))) > Q(str(selector.lock_tolerance_mw)):
            raise ValueError('reference prefix lock mismatch')
    else:
        state = module._physical(before)
        witness = module.audit_current_grid_assignment(info, disclosure, state, power, physical,
            expected_identity=module.current_step_identity(info, disclosure, state, power))
    if witness.errors or not witness.physical_assignment_valid:
        raise ValueError('zero-face physical witness failed')
    stages = []
    for position, (uid, planned) in enumerate(plan):
        index = offset+position
        model = (module._stage_model(*args, expected_identity, index, frozen) if reference
                 else module._stage_model(*args, index, frozen))
        variables = {v.name: v for v in model.component_data_objects(Var)}
        if set(variables) != set(values) or tuple(model.GEN) != uids:
            raise ValueError('zero-face full model assignment inventory mismatch')
        _prove_model_face(model, plan, reference, index)
        for name, variable in variables.items():
            if variable.fixed and abs(values[name]-value(variable)) > specification.feasibility_tolerance:
                raise ValueError('fixed variable mismatch')
            variable.set_value(values[name], skip_validation=True)
        residual = scale.native._constraint_violation(model)
        integer = scale.native._integrality_violation(model)
        if residual > specification.feasibility_tolerance or integer > specification.integer_feasibility_tolerance:
            raise ValueError('zero-face canonical feasibility failed')
        if float(value(model.objective)).hex() != float(planned).hex():
            raise ValueError('zero-face objective differs from fixed generation')
        exact = Q.from_float(float(planned))
        stages.append(scale._owned(AnalyticStage, index=index, objective_label='generation:'+uid,
            fixed_previous_objectives=frozen,
            fixed_previous_objective_hex=tuple(float(x).hex() for x in frozen),
            canonical_objective_hex=float(planned).hex(), evidence_kind='analytic_zero_face',
            input_identity=expected_identity, policy_identity=policy_identity,
            implementation_identity=expected_implementation,
            model_structure_identity=scale.native._structure(model),
            assignment=assignment if position == len(plan)-1 else (),
            assignment_identity=scale._digest(assignment), generator_uids=uids,
            objective_exact=(str(exact.numerator), str(exact.denominator)),
            assignment_witness=witness if position == len(plan)-1 else None,
            maximum_residual=residual, maximum_integrality_violation=integer,
            solver_calls_by_certificate=0, analytic_lexicographic_objective_proved=True,
            rigorous_exact_physical_feasibility=False, formal_result=False, security_certified=False,
            accepted=True, errors=()))
        frozen += (float(planned),)
    if (implementation_identity() != expected_implementation or identity(*args) != expected_identity
            or current_policy_identity(selector, specification, budget) != policy_identity
            or (hasattr(before, 'selector_policy_identity')
                and before.selector_policy_identity != policy_identity)):
        raise ValueError('zero-face source or implementation drift')
    return tuple(stages)
