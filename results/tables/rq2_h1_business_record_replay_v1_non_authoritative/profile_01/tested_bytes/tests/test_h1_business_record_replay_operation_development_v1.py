"""Original-validator oracle and failure boundaries for call-local record reuse."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from fractions import Fraction as Q
from hashlib import sha256
import importlib.util
from pathlib import Path
import sys
import struct
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from experiments import h1_exact_business_development_v1 as business
from tests import test_h1_exact_business_development_v1 as fixture
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


@pytest.fixture
def module(tmp_path):
    # Runtime drift irreversibly poisons one seal. Each adversarial case gets
    # a new private module instance, rather than trying to repair a poisoned one.
    name = 'experiments._record_operation_test_' + uuid4().hex
    source = Path('experiments/h1_business_record_replay_operation_development_v1.py').resolve()
    path = tmp_path / 'record_operation_non_authoritative.py'
    path.write_bytes(source.read_bytes())
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    try:
        yield value
    finally:
        sys.modules.pop(name, None)


@pytest.fixture
def carries():
    result = [fixture.origin()]
    for h in range(4):
        item = fixture.hour(result[-1], h, g=Q(17, 200) if h == 0 else Q(0),
                            source=Q(0) if h > 0 else Q(1, 2))
        result.append(fixture.advance(result[-1], item).next_candidate)
    assert all(value is not None for value in result)
    return result


def outcome(function, value):
    try:
        return ('accepted', function(value))
    except (TypeError, ValueError, AttributeError, IndexError) as error:
        return type(error), str(error)


def test_complete_prefixes_match_original_and_same_records_are_reused(module, carries, tmp_path):
    before = [value.scientific_payload for value in carries]
    with module.RecordReplayOperation() as operation:
        for value in carries:
            assert outcome(operation.validate, value) == outcome(business._validate, value)
        for value in carries:
            assert outcome(operation.validate, value) == outcome(business._validate, value)
        observed = operation.observation
        assert observed['original_record_replays'] == 4
        assert observed['record_reuses'] == 16
    assert [value.scientific_payload for value in carries] == before
    assert operation.observation['cache_cleared'] and not operation.observation['active']
    assert operation.observation['closed_cleanly']
    (tmp_path / 'validator_fact.json').write_text(json.dumps(dict(
        status='DRAFT_NONAUTHORITATIVE', original_and_successor_acceptance_equal=True,
        scientific_payload_sha256=[sha256(raw).hexdigest() for raw in before],
        observation=operation.observation, business_hours=4, paired_owner_authenticated=False,
        phase_events_written=0, real_native_calls=0, new_normal_jobs=0,
        formal_result=False), indent=2) + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match='closed'):
        operation.validate(carries[-1])


def test_equal_new_record_object_is_not_a_hit(module, carries):
    value = carries[1]
    duplicate = replace(value.cursor.records[0])
    cursor = replace(value.cursor, records=(duplicate,))
    other = business._owned(business.BusinessCarry, **(vars(value) | dict(cursor=cursor)))
    with module.RecordReplayOperation() as operation:
        operation.validate(value)
        operation.validate(other)
        assert operation.observation['original_record_replays'] == 2
        assert operation.observation['record_reuses'] == 0


@pytest.mark.parametrize('drift', ['implementation', 'history', 'observation', 'response', 'ledger'])
def test_original_failure_and_first_error_preserved(module, carries, drift):
    value = carries[2]
    if drift == 'implementation':
        value = business._owned(business.BusinessCarry, **(vars(value) | dict(implementation='0' * 64)))
    elif drift == 'history':
        value = business._owned(business.BusinessCarry, **(vars(value) | dict(history=value.history[:-1])))
    elif drift == 'observation':
        record = value.cursor.records[-1]
        object.__setattr__(record.current, 'available_flexibility', 0.125)
    elif drift == 'response':
        response = value.cursor.records[-1].response
        object.__setattr__(response.action, 'actual_service_power', Q(999))
    else:
        ledger = value.cursor.execution.tracks[0][1].ledger
        object.__setattr__(ledger, 'last_hour', 1)
    expected = outcome(business._validate, value)
    assert expected[0] != 'accepted'
    operation = module.RecordReplayOperation()
    assert outcome(operation.validate, value) == expected
    assert operation.observation['poisoned'] and operation.observation['cache_cleared']
    operation.close()


def test_nested_mutation_cannot_reuse_an_accepted_record(module, carries):
    value = carries[1]
    operation = module.RecordReplayOperation()
    operation.validate(value)
    response = value.cursor.records[0].response
    object.__setattr__(response.action, 'actual_service_power', Q(999))
    assert outcome(operation.validate, value) == outcome(business._validate, value)
    assert operation.observation['poisoned'] and operation.observation['cache_cleared']
    operation.close()


def test_instance_shadow_uses_original_dispatch_and_never_caches(module, carries):
    value = carries[1]
    record = value.cursor.records[0]
    calls = []
    object.__setattr__(record, '__post_init__', lambda: calls.append('original lookup'))
    with module.RecordReplayOperation() as operation:
        operation.validate(value)
        operation.validate(value)
        assert operation.observation['record_reuses'] == 0
    assert calls == ['original lookup', 'original lookup']


@pytest.mark.parametrize('drift', ['alias', 'code', 'default', 'field', 'class_added', 'module_added'])
def test_dependency_drift_is_rejected_before_reuse(module, carries, monkeypatch, drift):
    operation = module.RecordReplayOperation()
    operation.validate(carries[1])
    if drift == 'alias':
        monkeypatch.setattr(business.business, '_evaluate_policy', lambda *a: None)
    elif drift == 'code':
        monkeypatch.setattr(business.business._evaluate_policy, '__code__', (lambda *a: None).__code__)
    elif drift == 'default':
        monkeypatch.setattr(business._observation, '__defaults__', (True,))
    elif drift == 'field':
        field = business.business.BidirectionalPolicyRecord.__dataclass_fields__['stage']
        monkeypatch.setattr(field, 'name', 'different_stage')
    elif drift == 'class_added':
        monkeypatch.setattr(business.business.BidirectionalPolicyRecord, '_unexpected', True, raising=False)
    else:
        monkeypatch.setattr(business.business, '_unexpected', True, raising=False)
    with pytest.raises(ValueError, match='definition-time'):
        operation.validate(carries[1])
    assert operation.observation['poisoned'] and operation.observation['cache_cleared']
    with pytest.raises(ValueError):
        operation.close()
    assert not operation.observation['active']


def test_nested_mutable_constant_drift_is_rejected(module, carries):
    operation = module.RecordReplayOperation()
    operation.validate(carries[1])
    tracks = business.boundary._ARM_TRACKS[business.arms.JOINT]
    before = set(tracks)
    try:
        tracks.add('unexpected-track')
        with pytest.raises(ValueError, match='definition-time'):
            operation.validate(carries[1])
        assert operation.observation['poisoned'] and operation.observation['cache_cleared']
    finally:
        tracks.clear()
        tracks.update(before)
        try:
            operation.close()
        except ValueError:
            pass


def test_specialized_globals_are_original_and_cannot_be_shadowed(module, carries, monkeypatch):
    operation = module.RecordReplayOperation()
    assert operation._validator_globals is business._validate.__globals__
    operation.validate(carries[1])
    monkeypatch.setitem(operation._validator_globals, '_observation', lambda *a: None)
    with pytest.raises(ValueError, match='definition-time'):
        operation.validate(carries[1])
    assert operation.observation['poisoned'] and operation.observation['cache_cleared']
    with pytest.raises(ValueError):
        operation.close()


def test_caps_creator_private_entry_and_clearing(module, carries):
    for limits in (dict(max_records=True), dict(max_records=0),
                   dict(max_records=module.MAX_RECORDS + 1), dict(max_cache_bytes=True),
                   dict(max_cache_bytes=0), dict(max_cache_bytes=module.MAX_CACHE_BYTES + 1)):
        with pytest.raises(ValueError, match='resource limits'):
            module.RecordReplayOperation(**limits)
    operation = module.RecordReplayOperation(max_records=1)
    operation.validate(carries[1])
    with ThreadPoolExecutor(max_workers=1) as pool:
        for function in (lambda: operation.validate(carries[1]), operation.close):
            with pytest.raises(ValueError, match='creator'):
                pool.submit(function).result()
    assert operation.observation['active'] and not operation.observation['poisoned']
    with pytest.raises(ValueError, match='private validator'):
        operation._record(carries[1].cursor.records[0])
    with pytest.raises(ValueError, match='resource cap'):
        operation.validate(carries[2])
    assert operation.observation['poisoned'] and operation.observation['cache_cleared']
    operation.close()
    operation = module.RecordReplayOperation(max_cache_bytes=1)
    with pytest.raises(ValueError, match='resource cap'):
        operation.validate(carries[1])
    assert operation.observation['poisoned'] and operation.observation['cache_cleared']
    operation.close()


def test_snapshot_types_aliases_signed_zero_and_unsupported_layout(module, carries):
    assert module._snapshot((1,)) != module._snapshot((True,))
    assert module._snapshot((0.0,)) != module._snapshot((-0.0,))
    shared = []
    assert module._snapshot((shared, shared)) != module._snapshot(([], []))
    values = dict(a=1, b=2)
    before = module._snapshot(values)
    values['a'] = values.pop('a')
    assert module._snapshot(values) != before
    n1 = struct.unpack('>d', bytes.fromhex('7ff8000000000001'))[0]
    n2 = struct.unpack('>d', bytes.fromhex('7ff8000000000002'))[0]
    assert module._snapshot(n1) != module._snapshot(n2)
    with pytest.raises(module._Uncacheable):
        module._snapshot(SimpleNamespace(value=1))
    with pytest.raises(module._Uncacheable):
        module._snapshot([dict(key=SimpleNamespace(value=1))])
    with pytest.raises(ValueError, match='byte cap'):
        module._snapshot(b'x' * module.MAX_SNAPSHOT_BYTES)
    with pytest.raises(ValueError, match='node cap'):
        module._snapshot((None,) * module.MAX_NODES)


@pytest.mark.parametrize('where', ['validate', 'enter', 'close'])
def test_file_bookend_failure_poison_and_clean_close_state(module, carries, where):
    operation = module.RecordReplayOperation()
    operation.validate(carries[1])
    path = Path(module.__file__)
    original = path.read_bytes()
    try:
        path.write_bytes(original + b'\n')
        action = (lambda: operation.validate(carries[1])) if where == 'validate' else (
            operation.__enter__ if where == 'enter' else operation.close)
        with pytest.raises(ValueError, match='dependency bytes'):
            action()
        assert operation.observation['poisoned']
        assert operation.observation['cache_cleared'] and not operation.observation['closed_cleanly']
    finally:
        path.write_bytes(original)
        if operation.observation['active']:
            operation.close()
