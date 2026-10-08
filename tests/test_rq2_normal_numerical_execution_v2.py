from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path

import pytest

from tests.test_rq2_scale_normal_source_v1 import (
    supplied as legacy_request, declared_source, prepared_source, bound_source, source_supplied)
from tests.test_rq2_grid_information_v1 import declaration
from src.rq2_joint_deliverability_boundary_v1 import normal_numerical_execution_v2 as api
from src.rq2_joint_deliverability_boundary_v1 import normal_numerical_worker_v2 as worker


@pytest.fixture
def supplied(legacy_request):
    normal, _ = legacy_request
    return api.NumericalNormalRequest(normal, declaration(), api.projection.LIMIT)


def run(request, **kw):
    return api.run_source(request, expected_request_identity=api.request_identity(request), **kw)


def audit(request, record):
    raw = api.replay._bytes(record)
    return api.audit_source(raw, request, expected_sha256=sha256(raw).hexdigest(),
        expected_request_identity=api.request_identity(request), max_record_bytes=32*1024**2)


def setup(request, tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp('numerical_worker')
    raw = worker.transport.export_request(request)
    path = tmp_path/'request.json'
    path.write_bytes(raw)
    return dict(mode='execute', request_path=path, expected_request_sha256=sha256(raw).hexdigest(),
        expected_request_identity=api.request_identity(request), max_request_bytes=worker.transport.LIMIT,
        root=tmp_path/'normal_non_authoritative', receipt_path=tmp_path/'execute_receipt_non_authoritative.json',
        expected_environment_identity=worker.environment_identity(),
        expected_implementation_identity=worker.implementation_identity(request), max_record_bytes=32*1024**2)


def audit_args(args, executed):
    return dict(args, mode='audit', receipt_path=args['root'].parent/'audit_receipt_non_authoritative.json',
        expected_intent_sha256=executed['intent_sha256'], expected_record_sha256=executed['record_sha256'],
        expected_execution_environment_identity=executed['environment_identity'])


def test_owned_invocation_and_replay_bind_source_and_plan(supplied, monkeypatch):
    calls, boundary = [], []
    original = api.projection.capture.solve_once
    def solve(*a, **kw):
        assert boundary == ['intent']
        calls.append(1)
        return original(*a, **kw)
    monkeypatch.setattr(api.projection.capture, 'solve_once', solve)
    record = run(supplied, before_kernel=lambda: boundary.append('intent'))
    assert record['accepted'] and record['solver_calls'] == 1 and calls == [1]
    assert record['projection']['prepared_information_identity']
    with api.solver_free(): result = audit(supplied, record)
    assert result['accepted_record_reproduced'] and result['solver_calls_by_replay'] == 0
    assert result['numerical'] == record['projection']
    assert calls == [1] and not record['formal_result']


def test_collector_exception_is_unknown_and_never_retried(supplied, monkeypatch):
    calls = []
    def fail(*a, **kw):
        calls.append(1)
        raise RuntimeError('lost return')
    monkeypatch.setattr(api.projection.capture, 'solve_once', fail)
    record = run(supplied)
    assert calls == [1] and record['solver_calls'] is None and not record['call_count_complete']
    assert record['status'] == 'numerical_invocation_unknown' and record['projection'] is None
    assert not record['accepted']
    report = audit(supplied, record)
    assert report['record_consistent'] and not report['accepted_record_reproduced']
    assert report['numerical'] is None and calls == [1]
    changed = dict(record, solver_calls=0, call_count_complete=True)
    with pytest.raises(ValueError): audit(supplied, changed)


@pytest.mark.parametrize('fault', ['accepted', 'projection', 'plan', 'source', 'calls', 'extra', 'authority', 'elapsed'])
def test_reencoded_record_forgery_refused(supplied, monkeypatch, fault):
    # One retained tiny record supplies all cases; independent pins do not excuse a forgery.
    record = run(supplied)
    changed = deepcopy(record)
    if fault == 'accepted': changed['accepted'] = False
    elif fault == 'projection': changed['projection']['allowed_plan_identity'] = '0'*64
    elif fault == 'plan': changed['prepared_information'] = None
    elif fault == 'source': changed['source_after'] = {}
    elif fault == 'calls': changed['solver_calls'] = True
    elif fault == 'extra': changed['extra'] = False
    elif fault == 'authority': changed['native_execution_authenticated'] = True
    else: changed['observed_wall_seconds'] = float(supplied.budget.max_observed_wall_seconds+1)
    with api.solver_free(), pytest.raises(ValueError): audit(supplied, changed)


def test_future_plan_and_invalid_payload_refused_before_solver(supplied, monkeypatch):
    def forbidden(*a, **kw): pytest.fail('invalid request reached solver')
    monkeypatch.setattr(api.projection.capture, 'solve_once', forbidden)
    with pytest.raises(ValueError): run(replace(supplied, declaration=declaration(999)))
    with pytest.raises(ValueError): api.request_identity(replace(supplied, numerical_byte_limit=api.projection.LIMIT+1))


def test_source_change_after_solve_prevents_publication(supplied, monkeypatch):
    original = api.projection.capture.solve_once
    def changed(*a, **kw):
        raw = original(*a, **kw)
        p = Path(supplied.source.pair_declaration_path)
        p.write_bytes(p.read_bytes()+b'\n')
        return raw
    monkeypatch.setattr(api.projection.capture, 'solve_once', changed)
    with pytest.raises(ValueError): run(supplied)


def test_source_change_in_preinvoke_hook_prevents_solver(supplied, monkeypatch):
    def forbidden(*a, **kw): pytest.fail('changed source consumed native call')
    monkeypatch.setattr(api.projection.capture, 'solve_once', forbidden)
    def change():
        p = Path(supplied.source.pair_declaration_path)
        p.write_bytes(p.read_bytes()+b'\n')
    with pytest.raises(ValueError): run(supplied, before_kernel=change)


def test_replay_exposes_the_complete_bound_typed_plan(supplied):
    record = run(supplied)
    raw = api.replay._bytes(record)
    report, plan = api.replay_information(raw, supplied, expected_sha256=sha256(raw).hexdigest(),
        expected_request_identity=api.request_identity(supplied), max_record_bytes=32*1024**2)
    assert type(plan) is api.projection.information.PreparedNormalInformation
    assert report['prepared_information'] == record['prepared_information'] == api.kernel._encode(plan)
    assert plan.audit_identity == report['numerical']['prepared_information_identity']
    assert plan.allowed_plan_identity == report['numerical']['allowed_plan_identity']


def test_worker_execute_audit_one_shot_and_legacy_isolation(supplied, tmp_path_factory, monkeypatch):
    args = setup(supplied, tmp_path_factory)
    record = worker.run_worker(**args)
    assert record['outcome']['accepted'] and record['outcome']['solver_calls'] == 1
    snapshot = {p.name:p.read_bytes() for p in args['root'].iterdir()}
    report = worker.run_worker(**audit_args(args, record))
    assert report['outcome']['accepted_record_reproduced']
    assert report['outcome']['solver_calls_by_replay'] == 0
    assert snapshot == {p.name:p.read_bytes() for p in args['root'].iterdir()}
    with pytest.raises((ValueError, FileExistsError)): worker.run_worker(**args)
    legacy_transport = worker.transport.legacy
    with pytest.raises(ValueError): legacy_transport.decode_request(args['request_path'].read_bytes())
    with pytest.raises(ValueError): worker.transport.decode_request(legacy_transport.export_request(supplied.normal))


@pytest.mark.parametrize('where', ['intent', 'archive'])
def test_failed_persistence_never_retries_or_publishes_receipt(supplied, tmp_path_factory, monkeypatch, where):
    args = setup(supplied, tmp_path_factory)
    calls = []
    original = api.projection.capture.solve_once
    def solve(*a, **kw): calls.append(1); return original(*a, **kw)
    def fail(*a, **kw): raise OSError('injected persistence failure')
    monkeypatch.setattr(api.projection.capture, 'solve_once', solve)
    if where == 'intent': monkeypatch.setattr(worker.files, '_write', fail)
    else: monkeypatch.setattr(worker, '_write_record', fail)
    with pytest.raises(OSError, match='injected'): worker.run_worker(**args)
    assert calls == ([] if where == 'intent' else [1])
    assert not args['receipt_path'].exists()
    with pytest.raises((ValueError, FileExistsError)): worker.run_worker(**args)


@pytest.mark.parametrize('target', range(7))
def test_audit_worker_guards_all_execution_entries(supplied, tmp_path_factory, monkeypatch, target):
    args = setup(supplied, tmp_path_factory)
    executed = worker.run_worker(**args)
    entries = api.execution_targets()
    originals = [getattr(o,n) for o,n in entries]
    def attempted(*a, **kw):
        obj, name = entries[target]
        return getattr(obj, name)()
    monkeypatch.setattr(api, 'audit_source', attempted)
    with pytest.raises(RuntimeError, match='audit execution forbidden'):
        worker.run_worker(**audit_args(args, executed))
    assert [getattr(o,n) for o,n in entries] == originals
    assert not audit_args(args, executed)['receipt_path'].exists()


@pytest.mark.parametrize('fault', ['environment', 'implementation', 'request', 'source_path', 'receipt_inside'])
def test_worker_context_rejected_before_root_creation(supplied, tmp_path_factory, monkeypatch, fault):
    args = setup(supplied, tmp_path_factory)
    if fault in ('environment','implementation'): args['expected_'+fault+'_identity'] = '0'*64
    elif fault == 'request': args['expected_request_sha256'] = '0'*64
    elif fault == 'source_path': args['root'] = Path(supplied.source.upstream_root)/'bad_non_authoritative'
    else: args['receipt_path'] = args['root']/'receipt_non_authoritative.json'
    monkeypatch.setattr(api, 'run_source', lambda *a,**kw:pytest.fail('unexpected execution'))
    with pytest.raises(ValueError): worker.run_worker(**args)
    assert not args['root'].exists()
