"""Conditional exact-serializer grammar bound, not a native acceptance rule.

The producer has NOT been proven to always emit this grammar. A mismatch is a
resource-development finding; raw bytes remain unchanged under the old cap.
"""
import json
import math
import re

MAX_VARIABLES = 891
MAX_TERMS = 362
UID_TOKEN_BYTES = 38


def encode(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()


def fraction_limits(terms=MAX_TERMS):
    if type(terms) is not int or not 1 <= terms <= MAX_VARIABLES:
        raise ValueError('bounded exact term count required')
    # |float| < 2**1024, denominator divides 2**1074. Products have
    # denominator dividing 2**2148. Integer arithmetic avoids log rounding.
    denominator = len(str(2**1074))
    product_denominator = len(str(2**2148))
    aggregate_numerator = len(str(terms * 2**2098 - 1))
    product_numerator = len(str((terms+1) * 2**4196 - 1))
    difference_numerator = len(str((terms+2) * 2**4196 - 1))
    return dict(aggregate_fraction=aggregate_numerator+denominator+2,
                objective_numerator=product_numerator+1,
                objective_denominator=product_denominator,
                exact_difference=difference_numerator+product_denominator+2,
                float_difference=len(str(2**2099-1))+denominator+2,
                # A conservative common-denominator bound for one float.
                single_fraction=len(str(2**2098-1))+denominator+2)


def literal(value): return ('literal', value)
def nullable(rule): return ('nullable', rule)
def sequence(count, rule): return ('list', count, rule)
def pair(*rules): return ('tuple', rules)
def string(size, pattern=None): return ('string', size, pattern)


def grammar(max_terms=MAX_TERMS):
    limits = fraction_limits(max_terms)
    uid = string(UID_TOKEN_BYTES)
    hexf = ('hexfloat',)
    digest = string(66, '[0-9a-f]{64}')
    integer = ('int', 0, 2147483647)
    boolean = ('bool',)
    floating = ('float',)
    status = string(66, '[A-Za-z_][A-Za-z_0-9]*')
    rational = lambda n: string(n+2, '-?[0-9]+(?:/[1-9][0-9]*)?')
    assignment = sequence(MAX_VARIABLES, pair(uid, hexf))
    terms = sequence(max_terms, pair(uid, hexf, hexf))
    algebra = pair(rational(limits['single_fraction']),
                   sequence(max_terms, pair(uid, rational(limits['aggregate_fraction']))))
    exact = {'numerator': string(limits['objective_numerator']+2, '-?[0-9]+'),
             'denominator': string(limits['objective_denominator']+2, '[1-9][0-9]*')}
    attribute = {'available': boolean, 'hex': nullable(hexf),
                 'error': ('enum', (None, 'AttributeError', 'GurobiError:DATA_NOT_AVAILABLE'))}
    comparisons = {key: boolean for key in ('native_to_pyomo_lower_hex_equal',
        'native_to_pyomo_upper_hex_equal', 'lower_le_upper', 'lower_le_canonical', 'lower_le_exact')}
    comparisons.update(exact_minus_lower=rational(limits['exact_difference']),
                       canonical_minus_native_objective=rational(limits['float_difference']))
    provenance = dict(schema=literal('rq2_objective_provenance_v1'),
        adapter_identity=digest, collector_sha256=digest,
        native={key: attribute for key in ('ObjVal', 'ObjBound', 'ObjBoundC', 'Runtime')},
        native_status=integer, native_solution_count=integer,
        native_model_sense=literal(1), is_mip=boolean, pyomo_status=status,
        pyomo_termination=status, pyomo_solution_status=status,
        optimal_status_channels_consistent=boolean, pyomo_lower_hex=hexf,
        pyomo_upper_hex=hexf, pyomo_lower_source=('enum', ('ObjBound', 'ObjVal')),
        canonical_objective_hex=hexf, exact_objective=exact,
        constant_hex=hexf, ordered_objective_terms=terms,
        native_constant_hex=hexf, ordered_native_objective_terms=terms,
        native_exact_objective=exact, native_exact_value_equals_canonical_exact_value=boolean,
        canonical_objective_algebra=algebra, native_objective_algebra=algebra,
        native_algebra_equals_canonical_algebra=boolean,
        referenced_assignment=assignment, assignment_sha256=digest,
        comparisons=comparisons, formal_result=literal(False),
        optimality_certified=literal(False), native_execution_authenticated=literal(False),
        solver_calls_by_collector=literal(0))
    options = dict(FeasibilityTol=1e-9, IntFeasTol=1e-9, MIPGap=1e-8,
                   MIPGapAbs=0.0, OptimalityTol=1e-9, Seed=0, Threads=1, TimeLimit=5.0)
    return dict(schema=literal('rq2_objective_provenance_owned_solve_v1'),
        implementation_identity=digest, model_structure_identity=digest,
        solver_calls=literal(1), variables=('int', 0, MAX_VARIABLES),
        constraints=('int', 0, 1211), solver_options={k: literal(v) for k, v in options.items()},
        pyomo_status=status, pyomo_termination=status, native_status=integer,
        native_solution_count=integer, provenance=nullable(provenance),
        assignment=nullable(assignment), maximum_residual=nullable(floating),
        maximum_integrality_violation=nullable(floating), assignment_valid=boolean,
        formal_result=literal(False), normal_accepted=literal(False), optimality_certified=literal(False))


def bound(rule):
    if type(rule) is dict:
        return 2 + max(0, len(rule)-1) + sum(len(encode(k))+1+bound(v) for k, v in rule.items())
    kind = rule[0]
    if kind == 'literal': return len(encode(rule[1]))
    if kind == 'nullable': return max(4, bound(rule[1]))
    if kind == 'enum': return max(len(encode(v)) for v in rule[1])
    if kind == 'string': return rule[1]
    if kind == 'hexfloat': return 26
    if kind == 'float': return 24
    if kind == 'bool': return 5
    if kind == 'int': return max(len(str(rule[1])), len(str(rule[2])))
    if kind == 'list': return 2 + max(0, rule[1]-1) + rule[1]*bound(rule[2])
    if kind == 'tuple': return 2 + max(0, len(rule[1])-1) + sum(map(bound, rule[1]))
    raise ValueError('unknown grammar')


def validate(value, rule):
    """Reject unbounded shape before serialization; no scientific feasibility check."""
    if type(rule) is dict:
        if type(value) is not dict or set(value) != set(rule):
            raise ValueError('exact object keys required')
        for key, child in rule.items(): validate(value[key], child)
        return
    kind = rule[0]
    if kind == 'nullable':
        if value is not None: validate(value, rule[1])
        return
    if kind == 'literal': valid = type(value) is type(rule[1]) and value == rule[1]
    elif kind == 'enum': valid = any(type(value) is type(v) and value == v for v in rule[1])
    elif kind == 'bool': valid = type(value) is bool
    elif kind == 'int': valid = type(value) is int and rule[1] <= value <= rule[2]
    elif kind == 'float': valid = type(value) is float and math.isfinite(value) and len(encode(value)) <= 24
    elif kind == 'string':
        valid = type(value) is str and len(encode(value)) <= rule[1]
        if valid and rule[2] is not None: valid = re.fullmatch(rule[2], value) is not None
    elif kind == 'hexfloat':
        valid = type(value) is str and len(value) <= 24
        if valid:
            try:
                number = float.fromhex(value)
                valid = math.isfinite(number) and number.hex() == value
            except ValueError: valid = False
    elif kind in ('list', 'tuple'):
        valid = type(value) is list and (len(value) <= rule[1] if kind == 'list' else len(value) == len(rule[1]))
        if valid:
            rules = [rule[2]]*len(value) if kind == 'list' else rule[1]
            for item, child in zip(value, rules): validate(item, child)
    else: raise ValueError('unknown grammar')
    if not valid: raise ValueError('value outside conditional grammar: '+kind)


def check_raw(raw):
    if type(raw) is not bytes:
        raise ValueError('original raw bytes required')
    value = json.loads(raw)
    rules = grammar()
    validate(value, rules)
    if encode(value) != raw:
        raise ValueError('exact original serializer bytes required')
    limit = bound(rules)
    if len(raw) > limit:
        raise AssertionError('grammar bound violated')
    return dict(schema='h1_report_byte_bound_development_v1', raw_bytes=len(raw),
                conditional_bound_bytes=limit, producer_coverage_proven=False,
                collector_integrated=False, resource_admission=False, formal_result=False)
