"""Tiny synthetic source boundary; worker wiring does not certify RTS execution."""
from dataclasses import asdict, fields, replace
from hashlib import sha256
import os
from pathlib import Path
import sys

import pytest

from test_rq2_normal_declared_execution_stream_numeric_v1 import supplied, prepared_source, bound_source, source_supplied
from test_rq2_normal_declared_replay_stream_numeric_v1 import no_solver
from src.rq2_joint_deliverability_boundary_v1 import normal_task_worker_stream_numeric as api
from src.rq2_joint_deliverability_boundary_v1 import normal_archive_capture_stream_numeric as capture


pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows task worker')


def test_prior_worker_request_type_cannot_authorize_fast_worker(task):
    from src.rq2_joint_deliverability_boundary_v1 import normal_task_worker_stream as prior
    old = prior.StreamingNormalTaskRequest(**{field.name: getattr(task, field.name) for field in fields(task)})
    with pytest.raises(ValueError, match='typed compact normal task request'):
        api.task_identity(old)


def test_fast_worker_request_type_cannot_authorize_numeric_worker(task):
    from src.rq2_joint_deliverability_boundary_v1 import normal_task_worker_stream_fast as prior
    old = prior.FastStreamingNormalTaskRequest(**{field.name: getattr(task, field.name) for field in fields(task)})
    with pytest.raises(ValueError, match='typed compact normal task request'):
        api.task_identity(old)


@pytest.fixture
def task(supplied):
    source, args = supplied
    return api.NumericStreamingNormalTaskRequest(source=source,
        expected_source_request_identity=args['expected_request_identity'],
        specification=args['specification'], execution_budget=args['budget'],
        **{name: args[name] for name in ('expected_normal_execution_identity',
            'expected_source_execution_identity', 'expected_declared_execution_identity',
            'expected_assembly_identity', 'expected_binding_identity',
            'expected_source_implementation_identity', 'expected_binding_implementation_identity')},
        expected_replay_identity=api.replay.replay_identity(args['expected_declared_execution_identity'],
            args['specification'], args['budget']), max_record_bytes=16*1024**2, max_replay_bytes=16*1024**2)


def ready(root, phase, task, monkeypatch, pins=None):
    root.mkdir(exist_ok=True)
    scratch = root/(phase+'_non_authoritative')
    scratch.mkdir()
    env = api.codec.development_environment()
    env.update(TEMP=str(scratch), TMP=str(scratch))
    raw = api.phase_packet(root, phase, task, env, expected_task_identity=api.task_identity(task), replay_pins=pins)
    digest = sha256(raw).hexdigest()
    path = root/(phase+'.request.json')
    api.codec._write_once(path, raw)
    argv = api.worker_argv(path, digest)
    monkeypatch.chdir(scratch)
    monkeypatch.setattr(os, 'environ', env)
    monkeypatch.setattr(sys, 'orig_argv', argv)
    intent = dict(schema=api.SCHEMA, phase=phase, packet_sha256=digest, task_identity=api.task_identity(task))
    api._write(root/(phase+'.intent.json'), intent)
    launch = dict(**intent, pid=os.getpid(), creation_filetime=api._creation_filetime(),
        argv_sha256=sha256(api.journal._bytes(argv)).hexdigest(),
        root_identity=[root.stat().st_dev, root.stat().st_ino],
        scratch_identity=[scratch.stat().st_dev, scratch.stat().st_ino])
    api._write(root/(phase+'.launch.json'), launch)
    return path, digest


def stub_prepare(monkeypatch, supplied):
    calls = []
    original = api.inputs.prepare_task_inputs
    def prepare(source, *, expected_request_identity):
        calls.append((source, expected_request_identity))
        return original(source, expected_request_identity=expected_request_identity)
    monkeypatch.setattr(api.inputs, 'prepare_task_inputs', prepare)
    return calls


def test_compact_codec_and_identity_do_not_prepare_or_solve(task, monkeypatch):
    def forbidden(*a, **k): raise AssertionError('compact controller work cannot prepare or solve')
    monkeypatch.setattr(api.inputs, 'prepare_task_inputs', forbidden)
    monkeypatch.setattr(api.kernel.native, 'create_solver', forbidden)
    body = asdict(task)
    assert api.decode_request(body) == task
    assert len(api.journal._bytes(body)) < api.PACKET_LIMIT
    assert len(api.task_identity(task)) == 64
    for extra in ('assembly', 'encoded_result', 'owned_cursor'):
        with pytest.raises(ValueError, match='field inventory'):
            api.decode_request(dict(body, **{extra: {}}))


def test_execution_capture_and_replay_phase_wiring(tmp_path, supplied, task, monkeypatch):
    root = tmp_path/'task_non_authoritative'
    calls = stub_prepare(monkeypatch, supplied)
    path, digest = ready(root, 'execute', task, monkeypatch)
    api.worker(path, digest)
    completion = api._read(root/'execute.complete.json')
    claim = completion['completion']
    assert not completion['formal_result'] and not completion['numerical_acceptance_by_controller']
    normal_root = root/'normal_non_authoritative'
    cap = dict(budget=capture.ArchiveCaptureBudget(32*1024**2, task.max_record_bytes, 10.),
        expected_store_identity=claim['store_identity'],
        expected_declared_execution_identity=task.expected_declared_execution_identity,
        claimed_result_identity=claim['claimed_result_identity'])
    pins = capture.capture_normal_archive(normal_root,
        expected_capture_identity=capture.capture_identity(normal_root, **cap), **cap)
    assert pins.head == claim['head'] and pins.record_sha256 == claim['record_sha256']
    retained = dict(store_identity=pins.store_identity, head=pins.head,
        record_sha256=pins.record_sha256, claimed_result_identity=pins.claimed_result_identity)
    no_solver(monkeypatch)
    path, digest = ready(root, 'replay', task, monkeypatch, retained)
    api.worker(path, digest)
    replay_completion = api._read(root/'replay.complete.json')['completion']
    assert replay_completion['accepted_record_reproduced'] and replay_completion['archive_consistent']
    report = (root/'replay.result.json').read_bytes()
    assert len(report) == replay_completion['replay_result_bytes']
    assert sha256(report).hexdigest() == replay_completion['replay_result_sha256']
    assert len(calls) == 2  # Independent preparation per phase, no assembly transport.
    with pytest.raises(FileExistsError): api.worker(path, digest)
    assert len(calls) == 2


@pytest.mark.parametrize('fault', ['environment', 'cwd', 'argv', 'pid', 'creation', 'root_identity',
    'scratch_identity', 'intent', 'packet_digest'])
def test_runtime_drift_prevents_claim_and_preparation(tmp_path, task, monkeypatch, fault):
    root = tmp_path/'drift_non_authoritative'
    path, digest = ready(root, 'execute', task, monkeypatch)
    def forbidden(*a, **k): raise AssertionError('drift may not reach preparation')
    monkeypatch.setattr(api.inputs, 'prepare_task_inputs', forbidden)
    if fault == 'environment': monkeypatch.setattr(os, 'environ', dict(os.environ, EXTRA='bad'))
    if fault == 'cwd': monkeypatch.chdir(root)
    if fault == 'argv': monkeypatch.setattr(sys, 'orig_argv', ['wrong'])
    if fault == 'packet_digest': digest = '0'*64
    if fault in ('pid', 'creation', 'root_identity', 'scratch_identity'):
        launch_path = root/'execute.launch.json'
        launch = api._read(launch_path)
        name = 'creation_filetime' if fault == 'creation' else fault
        launch[name] = [0, 0] if fault.endswith('identity') else 0
        launch_path.write_bytes(api.journal._bytes(launch))
    if fault == 'intent': (root/'execute.intent.json').write_bytes(b'{}')
    with pytest.raises(ValueError): api.worker(path, digest)
    assert not (root/'execute.claim.json').exists()


@pytest.mark.parametrize('fault', ['prepare', 'interrupt', 'wrong_source_pin', 'claim_fsync', 'complete_write'])
def test_failure_retains_intent_and_claim_without_retry(tmp_path, supplied, task, monkeypatch, fault):
    root = tmp_path/'failure_non_authoritative'
    if fault == 'wrong_source_pin':
        declared = api.journal.execution.declared_execution_identity(task.source,
            expected_request_identity=task.expected_source_request_identity,
            expected_source_execution_identity='a'*64)
        task = replace(task, expected_source_execution_identity='a'*64,
            expected_declared_execution_identity=declared,
            expected_replay_identity=api.replay.replay_identity(declared, task.specification, task.execution_budget))
    path, digest = ready(root, 'execute', task, monkeypatch)
    calls = stub_prepare(monkeypatch, supplied)
    if fault in ('prepare', 'interrupt'):
        def fail(*a, **k): raise KeyboardInterrupt() if fault == 'interrupt' else OSError('source unavailable')
        monkeypatch.setattr(api.inputs, 'prepare_task_inputs', fail)
    if fault == 'claim_fsync':
        monkeypatch.setattr(api.codec.os, 'fsync', lambda *a: (_ for _ in ()).throw(OSError('fsync failed')))
    if fault == 'complete_write':
        original = api._write
        def fail(path, *args, **kwargs):
            if path.name.endswith('.complete.json'): raise OSError('completion unavailable')
            return original(path, *args, **kwargs)
        monkeypatch.setattr(api, '_write', fail)
    with pytest.raises((OSError, ValueError, KeyboardInterrupt)): api.worker(path, digest)
    assert (root/'execute.intent.json').exists() and (root/'execute.claim.json').exists()
    assert not (root/'execute.complete.json').exists()
    previous = len(calls)
    with pytest.raises(FileExistsError): api.worker(path, digest)
    assert len(calls) == previous


def test_preparation_postcheck_prevents_execution_after_packet_change(tmp_path, supplied, task, monkeypatch):
    root = tmp_path/'post_non_authoritative'
    path, digest = ready(root, 'execute', task, monkeypatch)
    original = api.inputs.prepare_task_inputs
    def prepare(*a, **k):
        prepared = original(*a, **k)
        path.write_bytes(b'{}')
        return prepared
    monkeypatch.setattr(api.inputs, 'prepare_task_inputs', prepare)
    with pytest.raises(ValueError): api.worker(path, digest)
    assert (root/'normal_non_authoritative').exists()


def test_invalid_phase_pins_and_budgets_refused(tmp_path, task):
    root = tmp_path/'invalid_non_authoritative'
    env = api.codec.development_environment()
    env.update(TEMP=str(root/'replay_non_authoritative'), TMP=str(root/'replay_non_authoritative'))
    with pytest.raises(ValueError, match='captured replay pins'):
        api.phase_packet(root, 'replay', task, env, expected_task_identity=api.task_identity(task))
    for change in (dict(max_record_bytes=True), dict(max_replay_bytes=0)):
        with pytest.raises(ValueError): replace(task, **change)
    with pytest.raises(ValueError, match='external implementation pins'):
        api.task_identity(replace(task, expected_normal_execution_identity='0'*64))


def test_wire_preserves_numeric_types_and_rejects_coercion(task):
    body = asdict(task)
    body['execution_budget']['max_seconds_per_solve'] = 1
    decoded = api.decode_request(body)
    assert type(decoded.execution_budget.max_seconds_per_solve) is int
    body['execution_budget']['max_seconds_per_solve'] = 1.0
    other = api.decode_request(body)
    assert type(other.execution_budget.max_seconds_per_solve) is float
    assert api.journal._bytes(asdict(decoded)) != api.journal._bytes(asdict(other))
    body['execution_budget']['max_threads'] = True
    with pytest.raises(ValueError): api.decode_request(body)


@pytest.mark.parametrize('fault', ['report_budget', 'report_fsync', 'replay_completion'])
def test_replay_write_failure_does_not_publish_completion(tmp_path, supplied, task, monkeypatch, fault):
    root = tmp_path/'replay_failure_non_authoritative'
    if fault == 'report_budget': task = replace(task, max_replay_bytes=1)
    stub_prepare(monkeypatch, supplied)
    path, digest = ready(root, 'execute', task, monkeypatch)
    api.worker(path, digest)
    pins = api._read(root/'execute.complete.json')['completion']
    no_solver(monkeypatch)
    path, digest = ready(root, 'replay', task, monkeypatch, pins)
    original = api._write
    def write(path, *args, **kwargs):
        if fault == 'report_fsync' and path.name == 'replay.result.json':
            with monkeypatch.context() as local:
                local.setattr(api.codec.os, 'fsync', lambda *a: (_ for _ in ()).throw(OSError('replay fsync failed')))
                return original(path, *args, **kwargs)
        if fault == 'replay_completion' and path.name == 'replay.complete.json':
            raise OSError('replay completion unavailable')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(api, '_write', write)
    with pytest.raises((ValueError, OSError)): api.worker(path, digest)
    assert (root/'replay.claim.json').exists() and not (root/'replay.complete.json').exists()
    assert (root/'replay.result.json').exists() == (fault != 'report_budget')
    with pytest.raises(FileExistsError): api.worker(path, digest)


def test_fixed_worker_in_real_suspended_task_job_keeps_source_failure(tmp_path, task):
    from src.rq2_joint_deliverability_boundary_v1 import normal_task_process as process
    # Child has no synthetic loader monkeypatch; source reconstruction must fail.
    root = tmp_path/'real_child_non_authoritative'
    root.mkdir()
    scratch = root/'execute_non_authoritative'
    scratch.mkdir()
    env = api.codec.development_environment()
    env.update(TEMP=str(scratch), TMP=str(scratch))
    task_pin = api.task_identity(task)
    raw = api.phase_packet(root, 'execute', task, env, expected_task_identity=task_pin)
    path, digest = root/'execute.request.json', sha256(raw).hexdigest()
    api.codec._write_once(path, raw)
    intent = dict(schema=api.SCHEMA, phase='execute', packet_sha256=digest, task_identity=task_pin)
    api._write(root/'execute.intent.json', intent)  # Controller side, before creating a child.
    argv = api.worker_argv(path, digest)
    mib = 1024**2
    budget = process.TaskProcessBudget(25., .05, 256*mib, 384*mib, 3.)
    host = process.resources.HostResourceBudget(384*mib, 32*mib,
        (process.resources.DirectoryDemand('scratch', str(scratch), 16*mib, mib),))
    kw = dict(cwd=scratch, environment=env, budget=budget, host_budget=host,
        expected_host_identity=process.resources.resource_identity(host))
    with process.normal_task_child(argv, expected_process_identity=process.task_process_identity(argv, **kw), **kw) as owner:
        assert not (root/'execute.claim.json').exists()
        api._write(root/'execute.launch.json', dict(**intent, pid=owner.pid,
            creation_filetime=owner.creation_filetime, argv_sha256=sha256(api.journal._bytes(argv)).hexdigest(),
            root_identity=[root.stat().st_dev, root.stat().st_ino],
            scratch_identity=[scratch.stat().st_dev, scratch.stat().st_ino]))
        owner.release()
        observed = owner.wait()
    assert observed.whole_job_quiescent and observed.reason == 'child_exited' and observed.exit_code != 0
    assert (root/'execute.claim.json').exists()  # Actual runtime handshake succeeded before source reconstruction failure.
    assert (root/'normal_non_authoritative').exists()


@pytest.mark.parametrize('fault', ['cwd', 'environment', 'argv', 'intent', 'launch', 'claim'])
def test_runtime_changed_during_preparation_prevents_source(tmp_path, supplied, task, monkeypatch, fault):
    root = tmp_path/'runtime_post_non_authoritative'
    path, digest = ready(root, 'execute', task, monkeypatch)
    original = api.inputs.prepare_task_inputs
    source_calls = []
    retained = {}
    original_execute = api.journal.DevelopmentDeclaredNumericNormalStore.execute
    def execute(store, **kwargs):
        retained['head'] = store.inspect().head
        return original_execute(store, **kwargs)
    monkeypatch.setattr(api.journal.DevelopmentDeclaredNumericNormalStore, 'execute', execute)
    monkeypatch.setattr(api.journal.execution.source, 'run_source_normal',
        lambda *a, **k: source_calls.append(1))
    def prepare(*a, **k):
        prepared = original(*a, **k)
        if fault in ('intent', 'launch', 'claim'):
            (root/('execute.'+fault+'.json')).write_bytes(b'{}')
        if fault == 'cwd': monkeypatch.chdir(root)
        if fault == 'environment': monkeypatch.setattr(os, 'environ', dict(os.environ, EXTRA='drift'))
        if fault == 'argv': monkeypatch.setattr(sys, 'orig_argv', ['drift'])
        return prepared
    monkeypatch.setattr(api.inputs, 'prepare_task_inputs', prepare)
    with pytest.raises(ValueError, match='path drift'): api.worker(path, digest)
    assert (root/'execute.claim.json').exists()
    assert (root/'normal_non_authoritative').exists()
    assert not (root/'execute.complete.json').exists()
    assert source_calls == []
    with api.journal.DevelopmentDeclaredNumericNormalStore(root/'normal_non_authoritative', task.source,
            create=False, expected_head=retained['head'], max_record_bytes=task.max_record_bytes,
            **api._execution_arguments(task)) as store:
        assert store.inspect().status == 'unresolved_intent'
        with pytest.raises(ValueError, match='cannot retry'): store.execute()
