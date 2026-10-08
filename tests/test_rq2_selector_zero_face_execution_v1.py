from dataclasses import replace
from hashlib import sha256
import os
import json
from pathlib import Path
import sqlite3

import pytest

from test_rq2_selector_zero_face_v1 import arguments
from src.rq2_joint_deliverability_boundary_v1 import scale_selector_zero_face_store as store
from src.rq2_joint_deliverability_boundary_v1 import scale_selector_zero_face_worker as worker
from src.rq2_joint_deliverability_boundary_v1 import scale_selector_zero_face_controller as controller
from src.rq2_joint_deliverability_boundary_v1 import scale_selector_zero_face_archive as archive
from src.rq2_joint_deliverability_boundary_v1 import scale_selector_store as old_store

LIMIT = 2*1024**2


def request(role='reference', zero=True):
    inputs, kw = arguments(role, zero=zero)
    return store.MixedSelectorRequest(*inputs, kw['expected_identity'], kw['selector'],
        kw['solver_specification'], kw['budget'], kw['expected_policy_identity'], kw['power'])


def replay_stored(root, pin, req):
    inspection, record = store._read(root/'selector.sqlite3', pin, LIMIT)
    data = store._bytes(record)
    return archive._verify(data, req, expected_sha256=sha256(data).hexdigest(),
        expected_binding_identity=pin, expected_implementation_identity=archive.implementation_identity(),
        max_record_bytes=LIMIT)


@pytest.mark.parametrize('role,calls', [('reference', 2), ('actual:0', 1)])
def test_store_keeps_full_reservation_and_replays_mixed_result(tmp_path, role, calls):
    req = request(role)
    root = tmp_path/'store_non_authoritative'
    with store.DevelopmentMixedSelectorStore(root, req, max_record_bytes=LIMIT) as owned:
        pin = owned.binding_identity
        result = owned.execute()
        inspection = owned.inspection()
        assert inspection['reported_solver_calls'] == calls
        assert inspection['charged_solver_calls'] == req.budget.max_solver_calls
        assert inspection['status'] == 'returned_unverified'
        with pytest.raises(ValueError): owned.execute()
    report, reconstructed = replay_stored(root, pin, req)
    assert report['selection_accepted'] and reconstructed == result
    assert report['solver_calls_by_replay_module'] == 0
    assert not report['whole_task_resources_verified'] and not report['native_execution_authenticated']


def test_namespace_prevents_old_request_and_old_store_read(tmp_path):
    req = request()
    old = old_store.SelectorRequest(*[getattr(req, field) for field in req.__dataclass_fields__])
    root = tmp_path/'store_non_authoritative'
    with pytest.raises(ValueError): store.DevelopmentMixedSelectorStore(root, old, max_record_bytes=LIMIT)
    assert not root.exists()
    with store.DevelopmentMixedSelectorStore(root, req, max_record_bytes=LIMIT) as owned:
        pin = owned.binding_identity
    with pytest.raises(ValueError, match='application'):
        old_store.inspect_scale_selector_store(root, expected_binding_identity=pin, max_record_bytes=LIMIT)


@pytest.mark.parametrize('error', [RuntimeError, KeyboardInterrupt])
def test_unreturned_execution_is_unknown_and_never_retried(tmp_path, monkeypatch, error):
    req = request()
    def failed(*args, **kwargs): raise error('injected')
    monkeypatch.setattr(store.selector, 'select_hour', failed)
    root = tmp_path/'store_non_authoritative'
    with store.DevelopmentMixedSelectorStore(root, req, max_record_bytes=LIMIT) as owned:
        with pytest.raises(error): owned.execute()
        assert owned.inspection()['status'] == 'pending_unknown'
        assert owned.inspection()['reported_solver_calls'] is None
        with pytest.raises(ValueError, match='retry'): owned.execute()


def test_lost_result_ack_preserves_record_without_retry(tmp_path, monkeypatch):
    req = request()
    root = tmp_path/'store_non_authoritative'
    with store.DevelopmentMixedSelectorStore(root, req, max_record_bytes=LIMIT) as owned:
        pin = owned.binding_identity
        append = owned._append
        def lost(result=None):
            append(result)
            if result is not None: raise OSError('lost ack')
        monkeypatch.setattr(owned, '_append', lost)
        with pytest.raises(OSError): owned.execute()
        with pytest.raises(ValueError, match='retry'): owned.execute()
    assert replay_stored(root, pin, req)[0]['selection_accepted']


@pytest.mark.parametrize('fault', ['binding', 'request', 'hash', 'implementation', 'size'])
def test_archive_external_binding_rejected(tmp_path, fault):
    req = request()
    root = tmp_path/'store_non_authoritative'
    with store.DevelopmentMixedSelectorStore(root, req, max_record_bytes=LIMIT) as owned:
        owned.execute()
        pin = owned.binding_identity
    _, record = store._read(root/'selector.sqlite3', pin, LIMIT)
    raw = store._bytes(record)
    kw = dict(expected_sha256=sha256(raw).hexdigest(), expected_binding_identity=pin,
        expected_implementation_identity=archive.implementation_identity(), max_record_bytes=LIMIT)
    if fault == 'binding': kw['expected_binding_identity'] = '0'*64
    if fault == 'hash': kw['expected_sha256'] = '0'*64
    if fault == 'implementation': kw['expected_implementation_identity'] = '0'*64
    if fault == 'size': kw['max_record_bytes'] = 1
    if fault == 'request': req = replace(req, expected_identity='0'*64)
    with pytest.raises(ValueError): archive.replay_record(raw, req, **kw)


@pytest.mark.parametrize('role', ['reference', 'actual:0'])
def test_worker_transport_roundtrip(role):
    req = request(role)
    raw = worker.export_request(req)
    assert worker.decode_request(raw) == req
    with pytest.raises(ValueError): worker.decode_request(raw+b'\n')


def setup(tmp_path, role='reference', zero=True):
    root = tmp_path/'task_non_authoritative'
    mib = 1024**2
    resources = controller.process.resources
    settings = dict(budget=controller.process.TaskProcessBudget(30., .1, 768*mib, 768*mib, 3.),
        host_budget=resources.HostResourceBudget(800*mib, 16*mib, (
            resources.DirectoryDemand('archive', str(root), 32*mib, 8*mib),
            resources.DirectoryDemand('scratch', str(root/'scratch'), 16*mib, 8*mib))),
        environment=dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1'),
        max_record_bytes=LIMIT)
    req = request(role, zero)
    pin = controller.controller_identity(root, req, **settings)
    return root, req, dict(settings, expected_controller_identity=pin)


@pytest.mark.parametrize('role,zero,calls', [('reference', True, 2), ('actual:0', True, 1), ('reference', False, 3)])
def test_real_job_worker_archive_and_replay(tmp_path, role, zero, calls):
    root, req, settings = setup(tmp_path, role, zero)
    result = controller.supervise_selector(root, req, **settings)
    assert result['observation']['whole_job_quiescent']
    assert result['inspection']['reported_solver_calls'] == calls
    assert result['status'] == 'returned_unverified'
    pin = result['inspection']['binding_identity']
    checked, reproduced = replay_stored(root/'selector_non_authoritative', pin, req)
    assert checked['selection_accepted'] and reproduced.solver_calls == calls
    assert not result['numerical_evidence_verified'] and not result['whole_task_resources_verified']
    with pytest.raises((ValueError, FileExistsError)): controller.supervise_selector(root, req, **settings)


@pytest.mark.parametrize('name', ['intent.json', 'launch.json'])
def test_failed_durable_record_prevents_worker_release(tmp_path, monkeypatch, name):
    root, req, settings = setup(tmp_path)
    write = controller._write
    def fail(path, body):
        if path.name == name: raise OSError('injected durable write failure')
        return write(path, body)
    monkeypatch.setattr(controller, '_write', fail)
    with pytest.raises(OSError): controller.supervise_selector(root, req, **settings)
    assert not (root/'selector_non_authoritative').exists()
    assert not (root/'result.json').exists()


def test_receipt_tamper_prevents_controller_completion(tmp_path, monkeypatch):
    root, req, settings = setup(tmp_path)
    read = controller._read
    def wrong(path, identity=None):
        body = read(path, identity)
        if path.name == 'receipt_non_authoritative.json': body['result_identity'] = '0'*64
        return body
    monkeypatch.setattr(controller, '_read', wrong)
    with pytest.raises(ValueError, match='request/result'):
        controller.supervise_selector(root, req, **settings)
    assert not (root/'result.json').exists()


def test_unresolved_archive_never_becomes_accepted(tmp_path, monkeypatch):
    req = request()
    root = tmp_path/'store_non_authoritative'
    def failed(*args, **kwargs): raise ValueError('injected analytic failure')
    monkeypatch.setattr(store.selector.analytic, 'certify_suffix', failed)
    with store.DevelopmentMixedSelectorStore(root, req, max_record_bytes=LIMIT) as owned:
        result = owned.execute()
        pin = owned.binding_identity
    assert result.status == 'unresolved'
    report, reproduced = replay_stored(root, pin, req)
    assert report['status'] == 'unresolved_archive_not_replayed'
    assert not report['selection_accepted'] and not report['archive_reproduced']
    assert reproduced is None


@pytest.mark.parametrize('fault', ['class', 'duplicate', 'extra', 'nan', 'result'])
def test_worker_input_vocabulary_is_closed(fault):
    packet = json.loads(worker.export_request(request()))
    if fault == 'class': packet['request'][0] = 'SelectorRequest'
    if fault == 'duplicate': packet['request'][1].append(packet['request'][1][0])
    if fault == 'extra': packet['command'] = 'unregistered'
    if fault == 'nan': packet['request'][1][0][1] = ['float', 'nan']
    if fault == 'result': packet['request'][0] = 'MixedSelectionResult'
    with pytest.raises((ValueError, TypeError)): worker.decode_request(store._bytes(packet))


def test_bad_worker_implementation_precedes_store_creation(tmp_path):
    raw = worker.export_request(request())
    packet = tmp_path/'request.json'
    packet.write_bytes(raw)
    root = tmp_path/'store_non_authoritative'
    with pytest.raises(ValueError, match='implementation'):
        worker.run_worker(request_path=packet, expected_request_sha256=sha256(raw).hexdigest(),
            max_request_bytes=LIMIT, store_root=root, receipt_path=tmp_path/'receipt_non_authoritative.json',
            max_record_bytes=LIMIT, expected_implementation_identity='0'*64)
    assert not root.exists()


def test_commit_limit_is_not_numerical_success(tmp_path, monkeypatch):
    root, req, settings = setup(tmp_path)
    child = controller.process.normal_task_child
    # Real owned Job still runs; only the terminal observation is fault-injected.
    class ChangedObservation:
        def __init__(self, *args, **kwargs): self.owner = child(*args, **kwargs)
        def __enter__(self):
            self.entered = self.owner.__enter__()
            return self
        def __getattr__(self, name): return getattr(self.entered, name)
        def wait(self):
            return replace(self.entered.wait(), reason='job_commit_limit', exit_code=1)
        def __exit__(self, *args): return self.owner.__exit__(*args)
    monkeypatch.setattr(controller.process, 'normal_task_child', ChangedObservation)
    with pytest.raises(ValueError, match='did not complete'):
        controller.supervise_selector(root, req, **settings)
    assert controller._read(root/'observation.json')['reason'] == 'job_commit_limit'
    assert not (root/'result.json').exists()


@pytest.fixture(scope='module')
def valid_observation(tmp_path_factory):
    root, req, settings = setup(tmp_path_factory.mktemp('mixed_observation'))
    result = controller.supervise_selector(root, req, **settings)
    observed = controller.process.TaskProcessObservation(**result['observation'])
    args = (settings['budget'], settings['host_budget'], observed.process_identity,
            observed.pid, observed.creation_filetime)
    controller._validate_observation(observed, *args)
    return observed, args


@pytest.mark.parametrize('change', [
    {'last_resource_errors': ('injected',)}, {'observation_error_type': 'OSError'},
    {'stop_markers': ('wrong',)}, {'job_commit_limits_configured': False},
    {'whole_task_resources_verified': True}, {'numerical_evidence_verified': True}, {'formal_result': True},
    {'hard_disk_quota_enforced': True}, {'job_peak_total_commit_bytes': 2**40},
    {'job_peak_process_commit_bytes': 2**40}, {'runtime_samples': True}, {'runtime_samples': 0},
    {'elapsed_seconds': float('nan')}, {'elapsed_seconds': 1e6}, {'exit_code': False},
    {'minimum_runtime_commit_available_bytes': 0}, {'minimum_runtime_disk_available_bytes': ()},
    {'process_identity': '0'*64}, {'pid': 1}, {'creation_filetime': 1},
])
def test_inconsistent_success_observation_rejected(valid_observation, change):
    observed, args = valid_observation
    with pytest.raises(ValueError): controller._validate_observation(replace(observed, **change), *args)


@pytest.mark.parametrize('target', ['scale', 'analytic', 'legacy'])
def test_new_worker_dependency_drift_precedes_store(tmp_path, monkeypatch, target):
    raw = worker.export_request(request())
    packet = tmp_path/'request.json'
    packet.write_bytes(raw)
    pin = worker.implementation_identity()
    module = worker.scale if target == 'scale' else getattr(worker.scale, target)
    path = Path(module.__file__)
    read = Path.read_bytes
    monkeypatch.setattr(Path, 'read_bytes', lambda p: read(p)+b' ' if p == path else read(p))
    root = tmp_path/'store_non_authoritative'
    with pytest.raises(ValueError, match='implementation'):
        worker.run_worker(request_path=packet, expected_request_sha256=sha256(raw).hexdigest(),
            max_request_bytes=LIMIT, store_root=root, receipt_path=tmp_path/'receipt_non_authoritative.json',
            max_record_bytes=LIMIT, expected_implementation_identity=pin)
    assert not root.exists()


def test_new_reader_rejects_legacy_application_id(tmp_path):
    req = request()
    root = tmp_path/'store_non_authoritative'
    with store.DevelopmentMixedSelectorStore(root, req, max_record_bytes=LIMIT) as owned:
        pin = owned.binding_identity
    with sqlite3.connect(root/'selector.sqlite3') as db:
        db.execute(f'PRAGMA application_id={old_store.APPLICATION_ID}')
    with pytest.raises(ValueError, match='application'):
        store.inspect_mixed_selector_store(root, expected_binding_identity=pin, max_record_bytes=LIMIT)


def test_legacy_result_tag_rejected_with_self_consistent_hash(tmp_path):
    req = request()
    root = tmp_path/'store_non_authoritative'
    with store.DevelopmentMixedSelectorStore(root, req, max_record_bytes=LIMIT) as owned:
        owned.execute()
        pin = owned.binding_identity
    _, record = store._read(root/'selector.sqlite3', pin, LIMIT)
    record['encoded_result'][0] = 'ScaleSelectionResult'
    record['result_identity'] = sha256(json.dumps(['tuple', [record['encoded_result']]],
        ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    raw = store._bytes(record)
    with pytest.raises(ValueError, match='typed encoded'):
        archive.replay_record(raw, req, expected_sha256=sha256(raw).hexdigest(),
            expected_binding_identity=pin, expected_implementation_identity=archive.implementation_identity(),
            max_record_bytes=LIMIT)
