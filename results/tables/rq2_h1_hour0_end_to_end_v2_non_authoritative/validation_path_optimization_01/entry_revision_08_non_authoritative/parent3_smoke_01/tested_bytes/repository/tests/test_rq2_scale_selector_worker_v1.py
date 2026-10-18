from hashlib import sha256
import json
import os
from pathlib import Path
import sys

import pytest

from test_rq2_scale_selector_store_v1 import request, LIMIT
from test_rq2_scale_selector_v1 import actual_inputs, budget, ACT, SPEC
from src.rq2_joint_deliverability_boundary_v1 import scale_selector_worker as worker
from src.rq2_joint_deliverability_boundary_v1 import normal_task_process as process


def actual_request():
    b = budget('actual:0')
    info, disclosure, before, power = actual_inputs(b)
    return worker.store.SelectorRequest(info, disclosure, before,
        worker.actual.dispatch_input_identity(info, disclosure, before, power), ACT, SPEC, b,
        worker.scale.policy_identity(ACT, SPEC, b), power)


@pytest.mark.parametrize('factory', [request, actual_request])
def test_input_transport_roundtrip_preserves_full_identity(factory):
    original = factory()
    raw = worker.export_request(original)
    decoded = worker.decode_request(raw)
    assert decoded == original
    assert worker.codec._digest(decoded) == worker.codec._digest(original)


@pytest.mark.parametrize('mutation', ['class', 'duplicate', 'extra', 'nan', 'noncanonical', 'result'])
def test_closed_input_vocabulary_and_canonical_encoding(mutation):
    packet = json.loads(worker.export_request(request()))
    if mutation == 'class':
        packet['request'][0] = 'os.system'
    elif mutation == 'duplicate':
        packet['request'][1].append(packet['request'][1][0])
    elif mutation == 'extra':
        packet['command'] = 'unregistered'
    elif mutation == 'nan':
        packet['request'][1][0][1] = ['float', 'nan']
    elif mutation == 'result':
        packet['request'][0] = 'ScaleSelectionResult'
    raw = worker.store._bytes(packet)
    if mutation == 'noncanonical': raw += b'\n'
    with pytest.raises((ValueError, TypeError)):
        worker.decode_request(raw)


def test_depth_bound_and_wrong_file_pin(tmp_path):
    wire = None
    for _ in range(40): wire = ['tuple', [wire]]
    with pytest.raises(ValueError, match='bounded'):
        worker.decode_request(worker.store._bytes(dict(schema=worker.SCHEMA, request=wire)))
    path = tmp_path/'request.json'
    path.write_bytes(worker.export_request(request()))
    with pytest.raises(ValueError, match='size/hash'):
        worker.read_request(path, expected_sha256='a'*64, max_request_bytes=LIMIT)
    with pytest.raises(ValueError, match='size/hash'):
        worker.read_request(path, expected_sha256=sha256(path.read_bytes()).hexdigest(), max_request_bytes=1)


def test_worker_implementation_mismatch_precedes_store_creation(tmp_path):
    path = tmp_path/'request.json'
    raw = worker.export_request(request())
    path.write_bytes(raw)
    root = tmp_path/'selector_non_authoritative'
    with pytest.raises(ValueError, match='implementation'):
        worker.run_worker(request_path=path, expected_request_sha256=sha256(raw).hexdigest(),
            max_request_bytes=LIMIT, store_root=root, receipt_path=tmp_path/'receipt_non_authoritative.json',
            max_record_bytes=LIMIT, expected_implementation_identity='a'*64)
    assert not root.exists()


def test_reference_selector_source_drift_precedes_store(tmp_path, monkeypatch):
    raw = worker.export_request(request())
    path = tmp_path/'request.json'
    path.write_bytes(raw)
    impl = worker.implementation_identity()
    original = Path.read_bytes
    target = Path(worker.scale.reference.__file__)
    monkeypatch.setattr(Path, 'read_bytes', lambda p: original(p)+b' ' if p == target else original(p))
    root = tmp_path/'selector_non_authoritative'
    with pytest.raises(ValueError, match='implementation'):
        worker.run_worker(request_path=path, expected_request_sha256=sha256(raw).hexdigest(),
            max_request_bytes=LIMIT, store_root=root, receipt_path=tmp_path/'receipt_non_authoritative.json',
            max_record_bytes=LIMIT, expected_implementation_identity=impl)
    assert not root.exists()


@pytest.mark.parametrize('fault', ['noop', 'short', 'wrong', 'read_error'])
def test_receipt_failure_preserves_store_without_retry(tmp_path, monkeypatch, fault):
    raw = worker.export_request(request())
    path = tmp_path/'request.json'
    path.write_bytes(raw)
    root = tmp_path/'selector_non_authoritative'
    receipt = tmp_path/'receipt_non_authoritative.json'
    impl = worker.implementation_identity()
    original = Path.open
    class FaultStream:
        def __init__(self, stream): self.stream = stream
        def __enter__(self): return self
        def __exit__(self, *args): return self.stream.__exit__(*args)
        def __getattr__(self, name): return getattr(self.stream, name)
        def write(self, data):
            if fault == 'noop': return len(data)
            if fault == 'short': return self.stream.write(data[:1])
            return self.stream.write(b'x'*len(data))
    def opened(p, mode='r', *args, **kwargs):
        if p == receipt and mode == 'rb' and fault == 'read_error':
            raise OSError('receipt read fault')
        stream = original(p, mode, *args, **kwargs)
        return FaultStream(stream) if p == receipt and mode == 'xb' and fault != 'read_error' else stream
    settings = dict(request_path=path, expected_request_sha256=sha256(raw).hexdigest(),
        max_request_bytes=LIMIT, store_root=root, receipt_path=receipt,
        max_record_bytes=LIMIT, expected_implementation_identity=impl)
    monkeypatch.setattr(Path, 'open', opened)
    with pytest.raises((OSError, ValueError), match='receipt'):
        worker.run_worker(**settings)
    monkeypatch.setattr(Path, 'open', original)
    import sqlite3
    with sqlite3.connect(root/'selector.sqlite3') as connection:
        assert connection.execute('SELECT count(*) FROM result').fetchone()[0] == 1
    with pytest.raises(ValueError, match='receipt'):
        worker.run_worker(**settings)


@pytest.mark.parametrize('factory,expected_calls', [(request, 3), (actual_request, 2)])
def test_real_fixed_worker_inside_existing_windows_job(tmp_path, factory, expected_calls):
    raw = worker.export_request(factory())
    request_path = tmp_path/'request_non_authoritative.json'
    request_path.write_bytes(raw)
    root = tmp_path/'selector_non_authoritative'
    receipt = tmp_path/'receipt_non_authoritative.json'
    scratch = tmp_path/'scratch'
    scratch.mkdir()
    impl = worker.implementation_identity()
    argv = [sys.executable, '-I', '-B', str(Path(worker.__file__).resolve()),
        '--request-path', str(request_path), '--expected-request-sha256', sha256(raw).hexdigest(),
        '--store-root', str(root), '--receipt-path', str(receipt), '--max-request-bytes', str(LIMIT),
        '--max-record-bytes', str(LIMIT), '--expected-implementation-identity', impl]
    mib = 1024**2
    resources = process.resources
    host = resources.HostResourceBudget(800*mib, 16*mib, (
        resources.DirectoryDemand('scratch', str(scratch), 16*mib, 8*mib),
        resources.DirectoryDemand('archive', str(tmp_path), 32*mib, 8*mib)))
    settings = dict(cwd=scratch,
        environment=dict(os.environ, TEMP=str(scratch), TMP=str(scratch),
                         OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1'),
        budget=process.TaskProcessBudget(30., .1, 768*mib, 768*mib, 3.),
        host_budget=host, expected_host_identity=resources.resource_identity(host))
    settings['expected_process_identity'] = process.task_process_identity(argv, **settings)
    with process.normal_task_child(argv, **settings) as child:
        assert not root.exists()
        child.release()
        observation = child.wait()
        assert observation.whole_job_quiescent
        assert observation.reason == 'child_exited' and observation.exit_code == 0
    # Artifact reads occur only after the owned whole-Job quiet observation.
    assert worker.implementation_identity() == impl
    body = worker.store._decoded(receipt.read_bytes())
    assert body['request_sha256'] == sha256(raw).hexdigest()
    assert body['implementation_identity'] == impl and body['reported_status'] == 'selected'
    archived = worker.store.inspect_scale_selector_store(root,
        expected_binding_identity=body['store_binding_identity'], max_record_bytes=LIMIT)
    assert archived['reported_solver_calls'] == expected_calls
    assert archived['status'] == 'returned_unverified'
    assert not body['formal_result'] and not body['whole_task_resources_verified']
