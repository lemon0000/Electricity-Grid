"""Candidate numerical predicate only; no execution or acceptance authority.

    All original solver/witness/source gates remain the caller's obligation.
    This evaluates a provenance report, not an authenticated solve certificate.
"""
from fractions import Fraction
from hashlib import sha256
import json
from math import isfinite
from . import rq2_objective_provenance_v1 as provenance


def evaluate(numerical, *, expected_implementation, expected_collector, expected_adapter):
    """Conditional predicate on a complete report; source/replay gates external.

    Pins must be retained independently by the caller. This recomputes archived
    algebra/assignment consistency, not the original model's feasibility.
    """
    for pin in (expected_implementation,expected_collector,expected_adapter):
        if type(pin) is not str or len(pin)!=64 or any(c not in '0123456789abcdef' for c in pin):
            raise ValueError('external canonical implementation pins required')
    if numerical['implementation_identity']!=expected_implementation:
        raise ValueError('runner identity mismatch')
    p = numerical['provenance']
    if p is None:
        return dict(candidate_numeric_predicate_passed=False, missing_provenance=True,
            formal_acceptance_authorized=False, rigorous_exact_optimality_certified=False)
    def number(x):
        if type(x) is not str:
            raise ValueError('canonical hex string required')
        result = float.fromhex(x)
        if not isfinite(result) or result.hex()!=x:
            raise ValueError('finite numeric channel required')
        return Fraction.from_float(result)
    if (p['schema']!='rq2_objective_provenance_v1' or p['collector_sha256']!=expected_collector
            or p['adapter_identity']!=expected_adapter):
        raise ValueError('collector/adapter identity mismatch')
    for key in ('maximum_residual','maximum_integrality_violation'):
        if type(numerical[key]) not in (int,float) or not isfinite(numerical[key]):
            raise ValueError('finite built-in residual required')
    for key in ('native_model_sense','native_status','native_solution_count'):
        if type(p[key]) is not int:
            raise ValueError('integer native metadata required')
    if type(numerical['assignment_valid']) is not bool or type(p['is_mip']) is not bool:
        raise ValueError('typed flags required')
    assignment=numerical['assignment']
    if type(assignment) is not list or any(type(row) is not list or len(row)!=2 for row in assignment):
        raise ValueError('complete assignment inventory required')
    values=dict(assignment)
    if len(values)!=len(assignment) or len(values)!=numerical['variables']:
        raise ValueError('unique complete assignment required')
    for name,assigned in assignment:
        if type(name) is not str: raise ValueError('variable name required')
        number(assigned)
    referenced=p['referenced_assignment']
    reference_values=dict(referenced)
    if (len(reference_values)!=len(referenced) or sorted(referenced)!=referenced
            or any(values.get(name)!=assigned for name,assigned in referenced)
            or sha256(repr(tuple(tuple(row) for row in referenced)).encode()).hexdigest()!=p['assignment_sha256']):
        raise ValueError('referenced/native assignment mismatch')
    def algebra(prefix):
        constant=number(p[prefix+'constant_hex'])
        terms=p['ordered_'+prefix+'objective_terms']
        total=constant
        for name,coefficient,assigned in terms:
            if values.get(name)!=assigned or name not in reference_values:
                raise ValueError('objective/native assignment mismatch')
            total+=number(coefficient)*number(assigned)
        return provenance._algebra(float(constant),terms), {'numerator':str(total.numerator),'denominator':str(total.denominator)}
    canonical_algebra,canonical_exact=algebra('')
    native_algebra,native_exact=algebra('native_')
    encode=lambda x: json.dumps(x,sort_keys=True,allow_nan=False)
    if (encode(canonical_algebra)!=encode(p['canonical_objective_algebra'])
            or encode(native_algebra)!=encode(p['native_objective_algebra'])
            or canonical_exact!=p['exact_objective'] or native_exact!=p['native_exact_objective']
            or p['native_algebra_equals_canonical_algebra'] is not (native_algebra==canonical_algebra)):
        raise ValueError('objective algebra/exact value inventory mismatch')
    for name in ('ObjBound','ObjVal','ObjBoundC'):
        if p['native'][name]['available'] is not True:
            raise ValueError('complete direct bound channels required')
        number(p['native'][name]['hex'])
    lower = number(p['native']['ObjBound']['hex'])
    upper = number(p['native']['ObjVal']['hex'])
    canonical = number(p['canonical_objective_hex'])
    tau = Fraction.from_float(1e-9)
    gap_limit = Fraction.from_float(1e-8)
    gap = (upper-lower)/abs(upper) if upper else Fraction(0) if lower == 0 else None
    checks = {
        'linear_mip_minimization_scope': p['is_mip'] is True and p['native_model_sense'] == 1,
        'optimal_status': p['native_status'] == 2 and p['pyomo_status'] == 'ok'
            and p['pyomo_termination'] == 'optimal' and p['pyomo_solution_status'] == 'optimal'
            and p['native_solution_count'] >= 1,
        'native_to_pyomo_bound_hex_equal': p['native']['ObjBound']['hex'] == p['pyomo_lower_hex']
            and p['native']['ObjVal']['hex'] == p['pyomo_upper_hex'],
        'objective_algebra_equal': native_algebra == canonical_algebra,
        'assignment_valid': numerical['assignment_valid'] is True,
        'residual_within_original_limit': 0 <= numerical['maximum_residual'] <= 1e-9,
        'integrality_within_original_limit': 0 <= numerical['maximum_integrality_violation'] <= 1e-9,
        'raw_bounds_ordered': lower <= upper,
        'objective_channel_consistent': abs(canonical-upper) <= tau,
        'raw_relative_gap_within_original_limit': gap is not None and 0 <= gap <= gap_limit,
    }
    return dict(candidate_numeric_predicate_passed=all(checks.values()), checks=checks,
        raw_relative_gap_exact=None if gap is None else str(gap),
        canonical_minus_native_objective_exact=str(canonical-upper),
        strict_legacy_lower_le_canonical=lower <= canonical,
        formal_acceptance_authorized=False, rigorous_exact_optimality_certified=False,
        native_execution_authenticated=False)
