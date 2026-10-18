"""Bounded failure diagnostics and zero-solver guards, using synthetic prepare."""
import json
from contextlib import contextmanager
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import os
import sys
from types import SimpleNamespace

import pytest

from experiments import diagnose_rq2_normal_prepare_v1 as api


@pytest.fixture
def probe(monkeypatch):
    w = api.c.worker
    # Register restoration before the child-only function installs its guards.
    for obj, name in ((w.kernel.native, 'create_solver'), (w.kernel, 'run_normal_only'),
        (w.journal.execution, 'run_source_normal'), (w.inputs.source_normal, 'assemble_source_normal'),
        (w.inputs.source.binding, 'bind_pair_normal')):
        monkeypatch.setattr(obj, name, getattr(obj, name))
    monkeypatch.setattr(w.kernel, '_peak_working_set_bytes', lambda: 123)
    return SimpleNamespace(source=None, expected_source_request_identity='1'*64)


@pytest.mark.parametrize('entry', ['create_solver', 'run_normal_only', 'run_source_normal'])
def test_each_solver_entry_is_forbidden(tmp_path, probe, monkeypatch, entry):
    w = api.c.worker
    def prepare(*args, **kwargs):
        obj = {'create_solver': w.kernel.native, 'run_normal_only': w.kernel,
            'run_source_normal': w.journal.execution}[entry]
        return getattr(obj, entry)()
    monkeypatch.setattr(w.inputs, 'prepare_task_inputs', prepare)
    with pytest.raises(AssertionError, match='solver forbidden'): api.prepare_probe(tmp_path, probe)
    failure = json.loads((tmp_path/'failure.json').read_bytes())
    assert failure['exception_type'] == 'AssertionError' and failure['stage'] == 'before_prepare'
    assert not (tmp_path/'prepared.json').exists()
    assert not failure['formal_result'] and not failure['normal_attempt_exception_identified']


def test_memory_error_trace_is_bounded_and_has_no_message_or_locals(tmp_path, probe, monkeypatch):
    def fail(*args, **kwargs):
        def recurse(depth):
            if depth: return recurse(depth-1)
            raise MemoryError('sensitive message must not be serialized')
        return recurse(12)
    monkeypatch.setattr(api.c.worker.inputs, 'prepare_task_inputs', fail)
    with pytest.raises(MemoryError): api.prepare_probe(tmp_path, probe)
    raw = (tmp_path/'failure.json').read_bytes()
    failure = json.loads(raw)
    assert len(raw) <= api.LIMIT and len(failure['frames']) == 8
    assert failure['exception_type'] == 'MemoryError' and b'sensitive' not in raw
    assert all(set(frame) == {'file', 'function', 'line'} for frame in failure['frames'])


def test_diagnostic_write_failure_preserves_original_exception(tmp_path, probe, monkeypatch):
    def fail(*args, **kwargs): raise MemoryError('original')
    monkeypatch.setattr(api.c.worker.inputs, 'prepare_task_inputs', fail)
    original = api.write
    def write(path, body):
        if path.name == 'failure.json': raise OSError('disk failure')
        return original(path, body)
    monkeypatch.setattr(api, 'write', write)
    with pytest.raises(MemoryError, match='original'): api.prepare_probe(tmp_path, probe)
    assert json.loads((tmp_path/'failure_write_failed.json').read_bytes())['status'] == 'diagnostic_write_failed'


def test_payload_limit_and_existing_files_refuse_overwrite(tmp_path):
    path = tmp_path/'record.json'
    with pytest.raises(ValueError): api.write(path, {'data': 'x'*api.LIMIT})
    assert not path.exists()
    api.write(path, {'formal_result': False})
    before = path.read_bytes()
    with pytest.raises(FileExistsError): api.write(path, {'different': True})
    assert path.read_bytes() == before


@pytest.fixture(scope='module')
def declared():
    return api.audit.read_declaration(Path('configs/rq2_normal_task_h25_development_v1.DRAFT.yaml'),
        '9a49cccf52e23d91a43511322a5abaf569e6cd2dfbf8d6db67b7d43d3c228aa6')


@pytest.mark.parametrize('fault', ['none', 'zero_empty', 'nonzero', 'timeout', 'pid', 'identity', 'authority',
    'quiet', 'missing_stages', 'stage_order', 'zero_peak', 'missing_timings', 'integer_timing'])
def test_parent_orchestration_rejects_incomplete_or_mismatched_child(tmp_path, declared, monkeypatch, capsys, fault):
    root = tmp_path/'probe_non_authoritative'
    _, request, _, _, _ = declared
    monkeypatch.setattr(api.audit, 'read_declaration', lambda *a: (tmp_path/'original_non_authoritative', *declared[1:]))
    monkeypatch.setattr(api.c.resources, 'observe_headroom', lambda *a, **k: SimpleNamespace(observed_headroom_sufficient=True))
    events = []
    @contextmanager
    def owner(*a, **k):
        events.append('spawn')
        assert (root/'probe.intent.json').exists() and not (root/'probe.launch.json').exists()
        class Child:
            pid, creation_filetime = 23, 45
            def release(self):
                events.append('release')
                assert api.read(root/'probe.launch.json')['pid'] == self.pid
                if fault == 'zero_empty': return
                sequence = list(api.STAGES)
                if fault == 'missing_stages': sequence = ['before_prepare', 'prepare_return']
                if fault == 'stage_order': sequence[1], sequence[2] = sequence[2], sequence[1]
                for index, stage in enumerate(sequence):
                    api.write(root/('stage_%02d.json' % index), dict(schema=api.SCHEMA, stage=stage,
                        pid=self.pid, lifetime_peak_working_set_bytes=0 if fault == 'zero_peak' else 123, formal_result=False))
                timings = dict.fromkeys(api.TIMINGS, 0.)
                if fault == 'missing_timings': timings = {}
                if fault == 'integer_timing': timings['declaration_seconds'] = 0
                api.write(root/'prepared.json', dict(schema=api.SCHEMA, status='source_prepared', pid=self.pid,
                    assembly_identity=request.source.expected_assembly_identity,
                    input_identity=request.source.expected_input_identity,
                    binding_identity=request.source.expected_binding_identity,
                    source_request_identity=request.expected_source_request_identity,
                    timings=timings, solver_calls_by_preparation=0, formal_result=False,
                    normal_attempt_exception_identified=False))
            def wait(self):
                result = api.c.process.TaskProcessObservation(k['expected_process_identity'],23,45,
                    1 if fault == 'nonzero' else 0, 'task_deadline_stop' if fault == 'timeout' else 'child_exited',
                    .1,1,1024,(),(),None,(),1024,1024, fault != 'quiet')
                if fault == 'pid': result = replace(result,pid=24)
                if fault == 'identity': result = replace(result,process_identity='0'*64)
                if fault == 'authority': result = replace(result,formal_result=True)
                return result
        yield Child()
    monkeypatch.setattr(api.c.process, 'normal_task_child', owner)
    monkeypatch.setattr(sys, 'argv', [api.__file__, '--declaration', 'unused.yaml', '--expected-sha256', '0'*64,
        '--expected-script-sha256', sha256(Path(api.__file__).read_bytes()).hexdigest(),
        '--expected-audit-script-sha256', sha256(Path(api.audit.__file__).read_bytes()).hexdigest(),
        '--diagnostic-root', str(root), '--execute-development'])
    if fault == 'quiet':
        with pytest.raises(ValueError, match='quiescence'): api.main()
        assert not (root/'probe.summary.json').exists()
    else:
        api.main()
        result = api.read(root/'probe.summary.json')
        assert result['status'] == ('source_prepared' if fault == 'none' else 'unresolved_probe')
        assert result['observation_sha256'] == sha256((root/'probe.observation.json').read_bytes()).hexdigest()
        assert not result['formal_result'] and not result['normal_attempt_exception_identified']
    assert events == ['spawn', 'release']
    with pytest.raises(FileExistsError): api.main()


@pytest.mark.parametrize('fault', ['none', 'pid', 'environment', 'intent'])
def test_child_context_requires_actual_launch(tmp_path, declared, monkeypatch, fault):
    request = declared[1]
    packet = dict(process_identity='0'*64, environment=dict(os.environ), argv=list(sys.orig_argv),
        root_identity=[tmp_path.stat().st_dev,tmp_path.stat().st_ino],
        source_request_identity=request.expected_source_request_identity,
        declaration_sha256='1'*64, script_sha256='2'*64)
    launch = dict(pid=os.getpid(), creation_filetime=api.c.worker._creation_filetime(),
        process_identity=packet['process_identity'], formal_result=False)
    if fault == 'pid': launch['pid'] += 1
    if fault == 'environment': packet['environment'] = {}
    intent = dict(schema=api.SCHEMA, process_identity=packet['process_identity'],
        request_sha256=sha256(api.c.journal._bytes(packet)).hexdigest(),
        status='zero_solver_preparation_intended', formal_result=False)
    if fault == 'intent': intent['request_sha256'] = '3'*64
    for name, body in (('request', packet), ('launch', launch), ('intent', intent)):
        api.write(tmp_path/('probe.'+name+'.json'), body)
    args = SimpleNamespace(expected_sha256='1'*64,expected_script_sha256='2'*64)
    if fault == 'none': api.child_context(tmp_path,request,args)
    else:
        with pytest.raises(ValueError): api.child_context(tmp_path,request,args)


def test_success_markers_include_binding_reassembly(tmp_path, probe, monkeypatch):
    w = api.c.worker
    assembly = SimpleNamespace(assembly_identity='1'*64, normal_identity='2'*64)
    monkeypatch.setattr(w.inputs.source_normal, 'assemble_source_normal', lambda: assembly)
    def binding(): return w.inputs.source_normal.assemble_source_normal()
    monkeypatch.setattr(w.inputs.source.binding, 'bind_pair_normal', binding)
    def prepare(*args, **kwargs):
        result = w.inputs.source_normal.assemble_source_normal()
        w.inputs.source.binding.bind_pair_normal()
        return SimpleNamespace(assembly=result, request_identity=probe.expected_source_request_identity,
            binding_json=json.dumps({'binding_identity':'3'*64}), timings=tuple(dict.fromkeys(api.TIMINGS,0.).items()),
            solver_calls=0)
    monkeypatch.setattr(w.inputs, 'prepare_task_inputs', prepare)
    api.prepare_probe(tmp_path,probe)
    assert tuple(api.read(path)['stage'] for path in sorted(tmp_path.glob('stage_*.json'))) == api.STAGES
    assert api.read(tmp_path/'prepared.json')['solver_calls_by_preparation'] == 0


def test_probe_cannot_create_inside_original_attempt(tmp_path, declared, monkeypatch):
    original = tmp_path/'original_non_authoritative'
    original.mkdir()
    (original/'preserved').write_bytes(b'original attempt bytes')
    monkeypatch.setattr(api.audit, 'read_declaration', lambda *a: (original, *declared[1:]))
    monkeypatch.setattr(sys, 'argv', [api.__file__, '--declaration', 'unused.yaml', '--expected-sha256', '0'*64,
        '--expected-script-sha256', sha256(Path(api.__file__).read_bytes()).hexdigest(),
        '--expected-audit-script-sha256', sha256(Path(api.audit.__file__).read_bytes()).hexdigest(),
        '--diagnostic-root', str(original/'nested_non_authoritative'), '--execute-development'])
    with pytest.raises(ValueError, match='separate'): api.main()
    assert list(original.iterdir()) == [original/'preserved']
    assert (original/'preserved').read_bytes() == b'original attempt bytes'
