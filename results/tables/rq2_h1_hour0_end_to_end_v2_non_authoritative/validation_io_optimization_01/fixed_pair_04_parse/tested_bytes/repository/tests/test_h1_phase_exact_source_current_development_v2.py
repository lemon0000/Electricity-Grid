"""Exact-source successor: synthetic prefix seams, real current-source science."""
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import sys

import pytest

from experiments import h1_phase_exact_source_current_development_v1 as legacy
from experiments import h1_historical_n0_verifier_development_v1 as verifier
from tests import test_h1_exact_source_current_development_v1 as cases
from tests.test_h1_exact_source_current_development_v1 import scenario, supplied


def load(monkeypatch):
    name = 'experiments.exact_source_successor_test_alias'
    path = Path(legacy.__file__).with_name('h1_phase_exact_source_current_development_v2.py')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def inputs(scenario, monkeypatch):
    monkeypatch.setattr(cases, 'm', legacy)
    data = cases.bind(scenario, monkeypatch)
    # The explicit fake prefix is installed before loading the guarded alias.
    # These tests do not establish the real full/fresh replay call counts.
    monkeypatch.setattr(verifier, '_replay_prefix', legacy.historical._replay_prefix)
    monkeypatch.setattr(verifier, '_observe_sources', legacy.historical._observe_sources)
    return data


def test_exact_scientific_projection_preserved_and_validation_identity_separate(inputs, monkeypatch):
    root, args, calls, *_ = inputs
    module = load(monkeypatch)
    old = legacy.prepare(root, **args)
    old_calls = list(calls)
    calls.clear()
    fresh = module.prepare(root, **args)
    assert len(old_calls) == len(calls) == 2
    assert old_calls[0] is old_calls[1] and calls[0] is calls[1]
    assert old_calls[0] is not calls[0]
    assert type(fresh) is module.ExactSourceCurrent and type(fresh) is not legacy.ExactSourceCurrent
    assert fresh.exogenous_scientific_payload == old.exogenous_scientific_payload
    assert fresh.prepared_current.decision.decision_bytes == old.prepared_current.decision.decision_bytes
    assert asdict(fresh.prepared_current.frame) == asdict(old.prepared_current.frame)
    assert fresh.prepared_current.source_action == old.prepared_current.source_action
    assert fresh.prepared_current.source_origin == old.prepared_current.source_origin
    assert fresh.source_observation_identity == old.source_observation_identity
    assert fresh.workload_exact == old.workload_exact
    assert fresh.source_cfe_at_alpha_one_exact == old.source_cfe_at_alpha_one_exact
    a, b = map(json.loads, (old.source_projection_audit_payload, fresh.source_projection_audit_payload))
    for field in ('normal_audit_payload', 'normal_audit_identity', 'historical_controller',
                  'source_observation_audit_payload', 'registry_audit_payload', 'workload_projection'):
        assert b[field] == a[field]
    assert b['schema'] == module.SCHEMA != a['schema']
    assert b['historical_verifier_identity'] == verifier.verifier_identity()
    assert b['predecessor_scientific_schema'] == legacy.SCHEMA
    assert b['full_numerical_hour_replays'] == b['fresh_byte_context_revalidations'] == 4
    assert b['recomputed_on_revalidation'] is False
    assert all(b[k] is False for k in ('formal_result', 'resource_admission', 'formal_execution_ready'))


def test_both_registry_reads_and_source_validation_remain(inputs, monkeypatch):
    counts = dict(registry=0, source=0, validate=0, final=0)
    for owner, name, key in ((legacy.registry, 'prepare', 'registry'),
                             (legacy.source, 'load_pinned_current', 'source'),
                             (legacy.source, 'validate_pinned_current', 'validate')):
        original = getattr(owner, name)
        def wrapper(*a, _call=original, _key=key, **kw):
            counts[_key] += 1
            return _call(*a, **kw)
        monkeypatch.setattr(owner, name, wrapper)
    def observe(*a):
        counts['final'] += 1
    monkeypatch.setattr(verifier, '_observe_sources', observe)
    module = load(monkeypatch)
    module.prepare(inputs[0], **inputs[1])
    # validate_pinned_current performs its own fresh load.
    assert counts == dict(registry=2, source=2, validate=1, final=1)


@pytest.mark.parametrize('target', ['prefix', 'verifier_identity', 'helper', 'helper_code', 'schema', 'source_loader'])
def test_dispatch_drift_between_historical_bookends_rejected(inputs, monkeypatch, target):
    original = legacy.registry.prepare
    changed = []
    module = None
    def registry(**kw):
        result = original(**kw)
        if not changed:
            changed.append(True)
            if target == 'prefix':
                monkeypatch.setattr(verifier, '_replay_prefix', lambda *a, **k: None)
            elif target == 'verifier_identity':
                monkeypatch.setattr(verifier, 'verifier_identity', lambda: 'f' * 64)
            elif target == 'helper':
                monkeypatch.setattr(module, '_envelope', lambda *a: None)
            elif target == 'helper_code':
                monkeypatch.setattr(module._ratio, '__code__', (lambda value: ['0','1']).__code__)
            elif target == 'schema':
                monkeypatch.setattr(module, 'SCHEMA', 'foreign')
            else:
                monkeypatch.setattr(legacy.source, 'load_pinned_current', lambda *a, **k: None)
        return result
    monkeypatch.setattr(legacy.registry, 'prepare', registry)
    module = load(monkeypatch)
    with pytest.raises((ValueError, AttributeError)):
        module.prepare(inputs[0], **inputs[1])
    assert len(inputs[2]) == 1


@pytest.mark.parametrize('target', ['prefix', 'identity', 'namespace', 'source_loader', 'registry', 'dispatch_code', 'defaults', 'predecessor_identity', 'join_identity', 'cap'])
def test_replaced_verifier_refused_before_effects(inputs, monkeypatch, target):
    module = load(monkeypatch)
    if target == 'prefix':
        monkeypatch.setattr(verifier, '_replay_prefix', lambda *a, **kw: None)
    elif target == 'identity':
        monkeypatch.setattr(verifier, 'verifier_identity', lambda: 'f' * 64)
    elif target == 'namespace':
        monkeypatch.setattr(module, 'historical', legacy.historical)
    elif target == 'source_loader':
        monkeypatch.setattr(module.source, 'load_pinned_current', lambda *a, **kw: None)
    elif target == 'registry':
        monkeypatch.setattr(module.registry, 'prepare', lambda *a, **kw: None)
    elif target == 'dispatch_code':
        monkeypatch.setattr(verifier.witness._dispatch_view, '__code__', (lambda caller=None: ()).__code__)
    elif target == 'defaults':
        monkeypatch.setattr(module.source.load_pinned_current, '__kwdefaults__', {'foreign': True})
    elif target == 'predecessor_identity':
        monkeypatch.setattr(module.predecessor,'implementation_identity',lambda:'f'*64)
    elif target == 'join_identity':
        monkeypatch.setattr(module.origin_join,'implementation_identity',lambda:'f'*64)
    else:
        monkeypatch.setattr(verifier.binding,'CAP',verifier.binding.CAP+1)
    with pytest.raises(ValueError, match='dispatch changed'):
        module.prepare(inputs[0], **inputs[1])
    assert not inputs[2]


@pytest.mark.parametrize('hours', [0, 2, 192, True])
def test_N0_scope_checked_before_prefix(inputs, monkeypatch, hours):
    module = load(monkeypatch)
    args = dict(inputs[1], completed_hours=hours)
    with pytest.raises(ValueError, match='one completed hour'):
        module.prepare(inputs[0], **args)
    assert not inputs[2]


@pytest.mark.parametrize('boundary', ['second_prefix', 'second_registry', 'validate', 'final_observation'])
def test_original_failure_boundaries_remain(inputs, monkeypatch, boundary):
    if boundary == 'second_prefix':
        owner, name, number = verifier, '_replay_prefix', 2
    elif boundary == 'second_registry':
        owner, name, number = legacy.registry, 'prepare', 2
    elif boundary == 'validate':
        owner, name, number = legacy.source, 'validate_pinned_current', 1
    else:
        owner, name, number = verifier, '_observe_sources', 1
    original = getattr(owner, name)
    calls = []
    def fail(*a, **kw):
        calls.append(True)
        if len(calls) == number:
            raise RuntimeError('injected exact source boundary')
        return original(*a, **kw)
    monkeypatch.setattr(owner, name, fail)
    module = load(monkeypatch)
    with pytest.raises(RuntimeError, match='injected exact source boundary'):
        module.prepare(inputs[0], **inputs[1])
    assert len(calls) == number
