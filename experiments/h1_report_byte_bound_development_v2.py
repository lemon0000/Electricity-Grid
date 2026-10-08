"""Conditional pinned-source future shape grammar; old v1 bytes stay intact."""
import json
from experiments import h1_report_byte_bound_development_v1 as prior

MAX_CONSTRAINTS = 1272


def grammar():
    rules = prior.grammar()
    rules['constraints'] = ('int', 0, MAX_CONSTRAINTS)
    return rules


def check_raw(raw):
    if type(raw) is not bytes:
        raise ValueError('original raw bytes required')
    document = json.loads(raw)
    rules = grammar()
    prior.validate(document, rules)
    if prior.encode(document) != raw:
        raise ValueError('exact original serializer bytes required')
    limit = prior.bound(rules)
    if len(raw) > limit:
        raise AssertionError('grammar byte bound violated')
    return dict(schema='h1_report_byte_bound_development_v2', raw_bytes=len(raw),
        conditional_bound_bytes=limit, constraints_limit=MAX_CONSTRAINTS,
        scope='fixed pinned-source family only; excludes arbitrary hourly bounds',
        producer_coverage_proven=False, collector_integrated=False,
        resource_admission=False, formal_result=False)
