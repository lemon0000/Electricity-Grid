from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('byte_bound_dev', ROOT/'experiments/h1_report_byte_bound_development_v1.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
DB = ROOT/'results/tables/rq2_normal_h1_origin_calibration_v3_non_authoritative/collector_non_authoritative/stages_non_authoritative/h1_chunk_journal.sqlite3'


@pytest.fixture(scope='module')
def reports():
    assert sha256(DB.read_bytes()).hexdigest() == 'bc9ff4270ec834347f440444fdbf0d0d328705b4d4a6c4c7aad8114e8fcd2115'
    result = []
    with sqlite3.connect(DB.resolve().as_uri()+'?mode=ro&immutable=1', uri=True) as db:
        for seq, size, digest in db.execute('SELECT seq,payload_bytes,payload_sha FROM events WHERE payload_bytes>0 ORDER BY seq'):
            raw = b''.join(row[0] for row in db.execute('SELECT payload FROM chunks WHERE event_seq=? ORDER BY chunk_index', (seq,)))
            assert len(raw) == size and sha256(raw).hexdigest() == digest
            result.append(raw)
    assert len(result) == 232
    return result


def test_all_original_raw_reports_unchanged(reports):
    results = [api.check_raw(raw) for raw in reports]
    assert max(r['raw_bytes'] for r in results) == 177312
    assert {r['conditional_bound_bytes'] for r in results} == {929218}
    assert all(not r['producer_coverage_proven'] and not r['resource_admission'] for r in results)


@pytest.mark.parametrize('mutation', ['extra', 'bool_int', 'variables', 'constraints',
    'name_unicode', 'name_escape', 'terms', 'fraction', 'numerator', 'nan',
    'hex_noncanonical', 'hex_infinity', 'solver_option', 'status', 'extra_provenance',
    'missing_field', 'int_overflow', 'authority'])
def test_grammar_rejects_unbounded_or_unregistered_values(reports, mutation):
    doc = json.loads(reports[0])
    p = doc['provenance']
    if mutation == 'extra': doc['extra'] = 'x'
    elif mutation == 'bool_int': doc['variables'] = True
    elif mutation == 'variables': doc['variables'] = 892
    elif mutation == 'constraints': doc['constraints'] = 1212
    elif mutation == 'name_unicode': doc['assignment'][0][0] = '\U0001f600'*4
    elif mutation == 'name_escape': doc['assignment'][0][0] = '\n'*19
    elif mutation == 'terms': p['ordered_native_objective_terms'] *= 2
    elif mutation == 'fraction': p['canonical_objective_algebra'][1][0][1] = '9'*962
    elif mutation == 'numerator': p['exact_objective']['numerator'] = '9'*1268
    elif mutation == 'nan': doc['maximum_residual'] = float('nan')
    elif mutation == 'hex_noncanonical': doc['assignment'][0][1] = '0x0p0'
    elif mutation == 'hex_infinity': doc['assignment'][0][1] = 'inf'
    elif mutation == 'solver_option': doc['solver_options']['Threads'] = True
    elif mutation == 'status': doc['pyomo_status'] = 'x'*65
    elif mutation == 'extra_provenance': p['native']['Runtime']['message'] = 'unbounded'
    elif mutation == 'missing_field': del p['constant_hex']
    elif mutation == 'int_overflow': p['native_solution_count'] = 2**31
    elif mutation == 'authority': doc['formal_result'] = True
    with pytest.raises(ValueError):
        api.validate(doc, api.grammar())


def test_raw_serializer_equality_duplicate_keys_and_whitespace(reports):
    raw = reports[0]
    for changed in (b' '+raw, raw[:-1]+b',"solver_calls":1}', json.dumps(json.loads(raw), indent=2).encode()):
        with pytest.raises(ValueError, match='serializer'):
            api.check_raw(changed)


def test_failure_no_incumbent_shape_is_bounded(reports):
    doc = json.loads(reports[0])
    doc.update(provenance=None, assignment=None, maximum_residual=None,
               maximum_integrality_violation=None, assignment_valid=False,
               native_solution_count=0, native_status=9, pyomo_termination='maxTimeLimit')
    assert api.check_raw(api.encode(doc))['conditional_bound_bytes'] == 929218


def test_exact_fraction_extremes_and_cancellation():
    limits = api.fraction_limits()
    big, tiny = map(Fraction.from_float, (sys.float_info.max, float.fromhex('0x0.0000000000001p-1022')))
    samples = (big, -big, tiny, -tiny, Fraction(0))
    for f in samples:
        assert len(str(f)) <= limits['single_fraction']
    aggregate = 361*big + tiny
    product = 361*big*big + tiny*tiny + big
    assert len(str(aggregate)) <= limits['aggregate_fraction']
    assert len(str(product.numerator)) <= limits['objective_numerator']
    assert len(str(product.denominator)) <= limits['objective_denominator']
    assert len(str(product+big)) <= limits['exact_difference']
    assert len(str(big-tiny)) <= limits['float_difference']
    assert big-big == 0


def test_variable_count_alone_is_not_one_mib_term_bound():
    assert api.bound(api.grammar(891)) > 1024*1024
    for bad in (True, 0, 892):
        with pytest.raises(ValueError):
            api.grammar(bad)


def test_grammar_bound_matches_independent_max_length_construction():
    # This witness is a grammar extremum, not a scientific/native witness.
    def maximum(rule):
        if isinstance(rule, dict): return {k: maximum(v) for k, v in rule.items()}
        kind = rule[0]
        if kind == 'literal': return rule[1]
        if kind == 'nullable':
            v = maximum(rule[1])
            return v if len(api.encode(v)) >= 4 else None
        if kind == 'enum': return max(rule[1], key=lambda v: len(api.encode(v)))
        if kind == 'string':
            pattern = rule[2]
            if pattern == '[0-9a-f]{64}': return 'a'*64
            if pattern == '[A-Za-z_][A-Za-z_0-9]*': return 'a'*(rule[1]-2)
            return '9'*(rule[1]-2)
        if kind == 'hexfloat': return '-0x1.fffffffffffffp+1023'
        if kind == 'float': return -1.2345678901234567e-100
        if kind == 'int': return rule[2]
        if kind == 'bool': return False
        if kind == 'list': return [maximum(rule[2]) for _ in range(rule[1])]
        if kind == 'tuple': return [maximum(r) for r in rule[1]]
        raise AssertionError(kind)
    rules = api.grammar()
    doc = maximum(rules)
    api.validate(doc, rules)
    assert len(api.encode(doc)) <= api.bound(rules) < 1024*1024
    # Float repr cap is conservative; exact independent serialized witness
    # should nearly saturate the compositional bound.
    assert api.bound(rules)-len(api.encode(doc)) <= 20
