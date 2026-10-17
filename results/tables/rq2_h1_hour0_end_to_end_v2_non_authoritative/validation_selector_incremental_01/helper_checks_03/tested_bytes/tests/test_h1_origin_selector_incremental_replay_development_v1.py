"""Differential oracles use the unchanged legacy replay and fabricated solves."""
from copy import copy, deepcopy
from dataclasses import replace
from hashlib import sha256
import inspect
import json
import pickle
import sys
from threading import Thread

import pytest

from experiments import h1_origin_selector_incremental_replay_development_v1 as m
from tests import test_h1_origin_selector_replay_development_v1 as fixtures
from tests import test_h1_hour0_zero_workload_oracle_v2 as zero
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


def pins(records):
    return tuple(sha256(r).hexdigest() for r in records)


def verify(bundle, records):
    f, d, b, args = bundle[:4]
    return m.verify_prefix(f, d, b, records, **args,
        expected_identity=m.legacy.input_identity(f, d, b, lane=args['lane'], power=args['power']),
        expected_policy_identity=b.policy_identity, expected_report_sha256=pins(records))


def append(token, bundle, prefix, record, **changes):
    f, d, b, args = bundle[:4]
    options = dict(args)
    options.update(changes)
    return m.append_verified_stage(token, f, d, b, prefix, record, **options,
        expected_report_sha256=pins(prefix + (record,)))


def exact_equal(left, right):
    assert m.legacy.native._encoded(left) == m.legacy.native._encoded(right)
    assert left == right


@pytest.fixture(scope='module', autouse=True)
def static_identity_bookends():
    """Test-only static DAG shortcut; this suite supplies no runtime estimate.

    Full upstream identities are evaluated and compared at both bookends.
    Selector/native/helper identities and all mathematical checks remain real.
    """
    targets = ((m.legacy.physical, 'implementation_identity'),
        (m.legacy, 'implementation_identity'), (m.legacy.native, '_identity'))
    originals = {(module, name): getattr(module, name) for module, name in targets}
    observed = []

    def memo(original):
        values = {}
        def call(*a, **kw):
            key = m.legacy.native._encoded((a, kw))
            if key not in values:
                values[key] = original(*a, **kw)
                observed.append((original, a, kw, values[key]))
            return values[key]
        return call

    with pytest.MonkeyPatch.context() as patch:
        for (module, name), original in originals.items():
            patch.setattr(module, name, memo(original))
        yield
    for (module, name), original in originals.items():
        assert getattr(module, name) is original
    for original, a, kw, value in observed:
        assert original(*a, **kw) == value


@pytest.fixture(scope='module', params=[fixtures.R, fixtures.A])
def bundle(request):
    with pytest.MonkeyPatch.context() as patch:
        result = fixtures.records(patch, request.param)
    assert len(result[-1]) == len(result[4])
    return result


def test_every_prefix_matches_legacy_all_result_bytes(bundle, no_solver):
    f, d, b, args, records, _ = bundle
    for count in range(len(records)):
        prefix = records[:count]
        token = verify(bundle, prefix)
        result = append(token, bundle, prefix, records[count])
        exact_equal(result, fixtures.replay(bundle, records[:count + 1]))
        assert m.revalidate_prefix(token, f, d, b, prefix, **args) == tuple(
            float.fromhex(x) for x in result.canonical_lock_hex[:count])
        with pytest.raises(ValueError, match='already consumed'):
            append(token, bundle, prefix, records[count])


def test_each_stage_numerically_replayed_once_and_fresh_tail_does_not_replay(bundle, no_solver):
    records = bundle[4]
    prefix = records[:-1]
    calls = []
    code = m.legacy.native._replay.__code__
    previous = sys.getprofile()

    def profile(frame, event, arg):
        if event == 'call' and frame.f_code is code:
            calls.append(frame.f_locals['purpose'])

    try:
        sys.setprofile(profile)
        token = verify(bundle, prefix)
        assert len(calls) == len(prefix)
        append(token, bundle, prefix, records[-1])
        assert len(calls) == len(records)
        f, d, b, args = bundle[:4]
        m.revalidate_prefix(token, f, d, b, prefix, **args)
        assert len(calls) == len(records)
    finally:
        sys.setprofile(previous)
    assert len(set(calls)) == len(records)


@pytest.mark.parametrize('lane,fault', [
    (lane, fault) for lane in (fixtures.R, fixtures.A)
    for fault in ('timeout', 'gap', 'strict_lock', 'l1_slack')
    if not (lane == fixtures.A and fault == 'strict_lock')])
def test_failure_diagnostics_and_suffix_chronology_match(monkeypatch, no_solver, fault, lane):
    bundle = fixtures.records(monkeypatch, lane, fault=fault)
    records = bundle[4]
    token = verify(bundle, records[:-1])
    exact_equal(append(token, bundle, records[:-1], records[-1]), fixtures.replay(bundle))
    with pytest.raises(ValueError, match='forbidden suffix'):
        verify(bundle, records + records[-1:])


@pytest.mark.parametrize('field', ['canonical_objective_hex', 'raw_objective', 'calls',
    'solution_count', 'lower', 'upper', 'maximum_residual', 'maximum_integrality_violation',
    'index', 'frozen_hex', 'predecessor_audit_identity'])
def test_corrupt_new_stage_matches_original_error_bytes(bundle, no_solver, field):
    records = bundle[4]
    prefix = records[:1]
    body = json.loads(records[1])
    if field == 'raw_objective':
        body['raw']['objective'] += 1.
    elif field in ('calls', 'solution_count'):
        body['raw'][field] = 0
    elif field in ('lower', 'upper', 'maximum_residual', 'maximum_integrality_violation'):
        body['raw'][field] = 999.
    elif field == 'index':
        body[field] = 0
    elif field == 'frozen_hex':
        body[field] = []
    else:
        body[field] = '0' * 64
    record = m.legacy.native._encoded(body)
    token = verify(bundle, prefix)
    exact_equal(append(token, bundle, prefix, record), fixtures.replay(bundle, prefix + (record,)))


@pytest.mark.parametrize('lane', [fixtures.R, fixtures.A])
def test_zero_sign_and_zero_sign_substitution_match(monkeypatch, no_solver, lane):
    records, oracle = zero.bundle(monkeypatch, lane)
    captured = inspect.getclosurevars(oracle).nonlocals
    bundle = captured['frame'], captured['disclosure'], captured['before'], captured['args'], records, ()
    for count in range(len(records)):
        token = verify(bundle, records[:count])
        exact_equal(append(token, bundle, records[:count], records[count]), oracle(records[:count + 1]))
    body = json.loads(records[0])
    body['canonical_objective_hex'] = (0. if body['canonical_objective_hex'].startswith('-') else -0.).hex()
    changed = m.legacy.native._encoded(body)
    token = verify(bundle, ())
    exact_equal(append(token, bundle, (), changed), oracle((changed,)))


@pytest.mark.parametrize('fault', ['frame', 'before', 'lane', 'power', 'selector', 'specification', 'limits',
    'record', 'builder', 'replay_code', 'versions', 'options', 'threshold', 'implementation'])
def test_drift_after_prefix_rejected_and_poisoned(bundle, monkeypatch, no_solver, fault):
    f, d, b, args, records, _ = bundle
    prefix = records[:1]
    token = verify(bundle, prefix)
    call_args = dict(args)
    if fault == 'frame':
        f = replace(f, normal_network_identity='0' * 64) if f.__dataclass_params__.init else m.legacy._owned(
            type(f), **dict(vars(f), normal_network_identity='0' * 64))
    elif fault == 'before':
        b = m.legacy._owned(type(b), **dict(vars(b), previous_audit_identity='0' * 64))
    elif fault == 'lane':
        call_args['lane'] = fixtures.A if args['lane'] == fixtures.R else fixtures.R
    elif fault == 'power':
        call_args['power'] = m.legacy.physical.RelativeDcPower(0, '1', '1', 'mechanism_assumption')
    elif fault in ('selector', 'specification', 'limits'):
        field = {'selector': 'relative_gap', 'specification': 'threads', 'limits': 'max_variables'}[fault]
        changed = 1e-3 if fault == 'selector' else getattr(args[fault], field) + 1
        call_args[fault] = replace(args[fault], **{field: changed})
    elif fault == 'record':
        prefix = (prefix[0] + b' ',)
    elif fault == 'builder':
        monkeypatch.setattr(m.legacy, 'build_development_stage', lambda *a, **k: None)
    elif fault == 'replay_code':
        def changed(*a, **k):
            return None
        monkeypatch.setattr(m.legacy.native._replay, '__code__', changed.__code__)
    elif fault == 'versions':
        original = m.legacy.native.version
        monkeypatch.setattr(m.legacy.native, 'version', lambda name: original(name) + '.changed')
    elif fault == 'options':
        monkeypatch.setattr(m.legacy.native.capture, 'solver_options', lambda spec: {'changed': 1})
    elif fault == 'threshold':
        monkeypatch.setattr(m.legacy.physical, 'TOLERANCE', 1e-3)
    else:
        original = m.Path.read_bytes
        def read(path):
            raw = original(path)
            return raw + b' ' if path == m.Path(m.__file__) else raw
        monkeypatch.setattr(m.Path, 'read_bytes', read)
    with pytest.raises((ValueError, TypeError, KeyError)):
        m.revalidate_prefix(token, f, d, b, prefix, **call_args)
    with pytest.raises(ValueError, match='unavailable after failure'):
        m.revalidate_prefix(token, *bundle[:3], records[:1], **args)


def test_private_state_cannot_be_constructed_copied_serialized_or_cross_thread(bundle, no_solver):
    token = verify(bundle, ())
    for action in (m.VerifiedPrefix, lambda: copy(token), lambda: deepcopy(token), lambda: pickle.dumps(token)):
        with pytest.raises(TypeError):
            action()
    with pytest.raises(ValueError, match='private verified prefix'):
        m.prefix_locks(object.__new__(m.VerifiedPrefix))
    failures = []
    def other_thread():
        try:
            m.prefix_locks(token)
        except Exception as error:
            failures.append(str(error))
    thread = Thread(target=other_thread)
    thread.start()
    thread.join()
    assert failures == ['verified prefix process/thread changed']


@pytest.mark.parametrize('boundary', ['entry', 'return'])
@pytest.mark.parametrize('fault', ['frame', 'before', 'lane', 'power', 'selector', 'specification', 'limits',
    'helper', 'threshold', 'versions', 'options'])
def test_append_boundaries_reject_drift_and_poison(bundle, monkeypatch, no_solver, boundary, fault):
    f, d, b, args, records, _ = bundle
    prefix = records[:1]
    resets = []

    def mutate(options):
        if fault in ('frame', 'before'):
            target, field = (f, 'normal_network_identity') if fault == 'frame' else (b, 'previous_audit_identity')
            resets.append((target, field, getattr(target, field)))
            object.__setattr__(target, field, '0' * 64)
        elif fault == 'lane':
            options['lane'] = fixtures.A if args['lane'] == fixtures.R else fixtures.R
        elif fault == 'power':
            options['power'] = m.legacy.physical.RelativeDcPower(0, '1', '1', 'mechanism_assumption')
        elif fault in ('selector', 'specification', 'limits'):
            field = {'selector': 'relative_gap', 'specification': 'threads', 'limits': 'max_variables'}[fault]
            changed = 1e-3 if fault == 'selector' else getattr(options[fault], field) + 1
            options[fault] = replace(options[fault], **{field: changed})
        elif fault == 'helper':
            monkeypatch.setattr(m, '_finish', lambda *a, **k: None)
        elif fault == 'threshold':
            monkeypatch.setattr(m.legacy.physical, 'TOLERANCE', 1e-3)
        elif fault == 'versions':
            monkeypatch.setattr(m.legacy.native, 'version', lambda name: 'changed')
        else:
            monkeypatch.setattr(m.legacy.native.capture, 'solver_options', lambda spec: {'changed': 1})

    original = m._replay_one
    if boundary == 'return':
        def replay_one(*a, **kwargs):
            result = original(*a, **kwargs)
            mutate(kwargs['args'])
            return result
        monkeypatch.setattr(m, '_replay_one', replay_one)
    token = verify(bundle, prefix)
    options = dict(args)
    if boundary == 'entry':
        mutate(options)
    try:
        with pytest.raises((ValueError, TypeError, KeyError)):
            append(token, (f, d, b, options), prefix, records[1])
        with pytest.raises(ValueError, match='unavailable after failure'):
            m.revalidate_prefix(token, f, d, b, prefix, **args)
    finally:
        for target, field, value in resets:
            object.__setattr__(target, field, value)


def test_changed_prefix_bytes_at_append_entry_are_rejected_and_poisoned(bundle, no_solver):
    prefix = bundle[4][:1]
    token = verify(bundle, prefix)
    with pytest.raises(ValueError, match='external pin mismatch'):
        append(token, bundle, (prefix[0] + b' ',), bundle[4][1])
    with pytest.raises(ValueError, match='unavailable after failure'):
        m.revalidate_prefix(token, *bundle[:3], prefix, **bundle[3])
