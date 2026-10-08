from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import diagnose_rq2_stream_source_v2 as api


@pytest.fixture(scope='module')
def declared_request():
    return api.prior.audit.read_declaration(Path('configs/rq2_normal_task_h25_development_v1.DRAFT.yaml'),
        '9a49cccf52e23d91a43511322a5abaf569e6cd2dfbf8d6db67b7d43d3c228aa6')[1]


def test_decode_retains_h25_and_checks_external_content(declared_request, monkeypatch):
    captured = []
    def assemble(root, hours, normal, initial, carry, **kwargs):
        captured.append((hours, normal, initial, carry, kwargs))
        return SimpleNamespace(normal_identity=declared_request.source.expected_input_identity,
            legacy_content_assembly_identity=declared_request.source.expected_assembly_identity,
            raw_source_hours=hours)
    monkeypatch.setattr(api.source, 'assemble_source_normal', assemble)
    api.assemble(declared_request, '1'*64)
    hours, normal, initial, carry, kwargs = captured[0]
    assert len(hours) == 25 and hours == tuple(range(hours[0], hours[0]+25))
    assert len(normal.timestamps) == 25 and carry.source_hour == hours[0]
    assert kwargs['expected_implementation_identity'] == '1'*64
    monkeypatch.setattr(api.source, 'assemble_source_normal', lambda *a, **kw:
        SimpleNamespace(normal_identity='0'*64,
            legacy_content_assembly_identity=declared_request.source.expected_assembly_identity, raw_source_hours=hours))
    with pytest.raises(ValueError, match='content pins'): api.assemble(declared_request, '1'*64)


@pytest.fixture
def content(declared_request):
    spec = declared_request.source
    record = api.c.worker.inputs._json(api.c.worker.inputs._read_pinned(spec.normal_record_path,
        spec.expected_normal_record_sha256, spec.max_normal_record_bytes))
    power = record['binding']['power_binding']
    hours = power['raw_source_hours']
    return dict(schema=api.SCHEMA, pid=123, normal_identity=spec.expected_input_identity,
        legacy_content_assembly_identity=spec.expected_assembly_identity,
        assembly_identity=api.source.stream.digest(api.source.CONTRACT, power['grid_source_manifest_sha256'],
            tuple(hours), spec.expected_input_identity, spec.expected_assembly_identity, '2'*64),
        implementation_identity='2'*64, probe_implementation_identity='1'*64,
        source_manifest_sha256=power['grid_source_manifest_sha256'], raw_source_hours=hours,
        source_hours=[h+1 for h in hours], annual_source_hours=8784, elapsed_seconds=1.,
        lifetime_peak_working_set_bytes=123, solver_calls=0, mechanism_initial_state=True,
        observed_power_mapping=False, formal_result=False, whole_task_resources_verified=False)


def test_content_success(declared_request, content):
    api.validate_content(content, declared_request, '1'*64, '2'*64, 123)


@pytest.mark.parametrize('field,value', [('normal_identity','0'*64), ('assembly_identity','0'*64),
    ('pid',True), ('solver_calls',False), ('formal_result',True), ('whole_task_resources_verified',True),
    ('annual_source_hours',25), ('raw_source_hours',[0]), ('source_hours',[1]),
    ('observed_power_mapping',True), ('elapsed_seconds',float('nan')), ('elapsed_seconds',1),
    ('lifetime_peak_working_set_bytes',0), ('lifetime_peak_working_set_bytes',True), ('extra',1)])
def test_content_fault(declared_request, content, field, value):
    content[field] = value
    with pytest.raises(ValueError): api.validate_content(content, declared_request, '1'*64, '2'*64,123)


@pytest.mark.parametrize('entry', ['create_solver','run_normal_only','run_source_normal'])
def test_solver_guards_and_failure_preservation(tmp_path, declared_request, monkeypatch, entry):
    w = api.c.worker
    objects = dict(create_solver=w.kernel.native, run_normal_only=w.kernel, run_source_normal=w.journal.execution)
    for name, obj in objects.items(): monkeypatch.setattr(obj, name, getattr(obj,name))
    monkeypatch.setattr(api, 'assemble', lambda *a: getattr(objects[entry],entry)())
    with pytest.raises(AssertionError, match='solver forbidden'):
        api.child(tmp_path, declared_request, '1'*64, '2'*64)
    assert api.read(tmp_path/'failure.json')['exception_type'] == 'AssertionError'
    assert api.read(tmp_path/'failure.json')['schema'] == api.SCHEMA
    assert not (tmp_path/'source.json').exists()


@pytest.mark.parametrize('fault', ['none','type','pid','identity','exit','quiet','limits','formal',
    'disk','whole','numerical','missing','malformed','failure','fallback',
    'nan_elapsed','integer_elapsed','samples','peak','total_peak','reserve','resource_error','api_error'])
def test_parent_unresolved_faults(tmp_path, declared_request, content, fault):
    observation = api.c.process.TaskProcessObservation('3'*64,123,456,0,'child_exited',1.,2,
        999999,(),(),None,(),100,100,True)
    changes = {'pid':dict(pid=124),'identity':dict(process_identity='0'*64),'exit':dict(exit_code=1),
        'quiet':dict(whole_job_quiescent=False),'limits':dict(job_commit_limits_configured=False),
        'formal':dict(formal_result=True),'disk':dict(hard_disk_quota_enforced=True),
        'whole':dict(whole_task_resources_verified=True),'numerical':dict(numerical_evidence_verified=True),
        'nan_elapsed':dict(elapsed_seconds=float('nan')),'integer_elapsed':dict(elapsed_seconds=1),
        'samples':dict(runtime_samples=0),'peak':dict(job_peak_process_commit_bytes=0),
        'total_peak':dict(job_peak_total_commit_bytes=99),'reserve':dict(minimum_runtime_commit_available_bytes=None),
        'resource_error':dict(last_resource_errors=('reserve',)),'api_error':dict(observation_error_type='OSError')}
    observation = replace(observation,**changes.get(fault,{}))
    if fault == 'type': observation = SimpleNamespace(**vars(observation))
    if fault == 'malformed': content = {'schema':api.SCHEMA}
    if fault != 'missing': api.write(tmp_path/'source.json',content)
    if fault == 'failure':
        failure = api.prior.failure_record(ValueError(), 'stream_source_assembly')
        failure['schema'] = api.SCHEMA
        api.write(tmp_path/'failure.json',failure)
    if fault == 'fallback': api.write(tmp_path/'failure_write_failed.json',{})
    report = api.summarize(tmp_path,declared_request,'1'*64,'2'*64,'3'*64,
        dict(pid=123,creation_filetime=456),observation)
    assert report['status'] == ('source_content_reproduced' if fault == 'none' else 'unresolved_probe')
    assert report['formal_result'] is False and report['whole_task_resources_verified'] is False


@pytest.mark.parametrize('fault', ['none','argv','environment','root_identity','phase_budget','host_budget',
    'process_identity','implementation_identity','pid','creation_filetime','extra','nested'])
def test_main_order_child_context_and_existing_root(tmp_path, declared_request, content, monkeypatch, fault):
    from contextlib import contextmanager
    from hashlib import sha256
    import os
    import sys
    declared = api.prior.audit.read_declaration(Path('configs/rq2_normal_task_h25_development_v1.DRAFT.yaml'),
        '9a49cccf52e23d91a43511322a5abaf569e6cd2dfbf8d6db67b7d43d3c228aa6')
    original = tmp_path/'original_non_authoritative'
    original.mkdir()
    (original/'preserved').write_bytes(b'original bytes')
    root = (original if fault == 'nested' else tmp_path)/'probe_non_authoritative'
    monkeypatch.setattr(api.prior.audit, 'read_declaration', lambda *a: (original,*declared[1:]))
    monkeypatch.setattr(api.c.resources, 'observe_headroom', lambda *a,**k:
        SimpleNamespace(observed_headroom_sufficient=True))
    pin, stream_pin = api.implementation_identity(), api.source.implementation_identity()
    events = []
    def fake_source(target, *args):
        events.append('source')
        body = dict(content, pid=os.getpid(), probe_implementation_identity=pin,
            implementation_identity=stream_pin)
        body['assembly_identity'] = api.source.stream.digest(api.source.CONTRACT, body['source_manifest_sha256'],
            tuple(body['raw_source_hours']),body['normal_identity'],body['legacy_content_assembly_identity'],stream_pin)
        api.write(target/'source.json',body)
    monkeypatch.setattr(api, 'child', fake_source)
    @contextmanager
    def owner(argv, **kwargs):
        events.append('spawn')
        assert (root/'request.json').exists() and not (root/'launch.json').exists()
        class Child:
            pid = os.getpid()
            creation_filetime = api.c.worker._creation_filetime()
            failed = False
            def release(self):
                events.append('release')
                assert api.read(root/'launch.json')['pid'] == self.pid
                packet, launch = api.read(root/'request.json'), api.read(root/'launch.json')
                if fault in ('pid','creation_filetime'): launch[fault] += 1
                elif fault != 'none': packet[fault] = 'incorrect'
                saved_read = api.read
                with monkeypatch.context() as m:
                    m.chdir(root)
                    for key in tuple(os.environ): m.delenv(key)
                    for key,value in sorted(kwargs['environment'].items(), key=lambda item: item[0].upper()): m.setenv(key,value)
                    m.setattr(sys, 'argv', [argv[3],*argv[4:]])
                    m.setattr(sys, 'orig_argv', argv)
                    m.setattr(api,'read',lambda path: packet if path.name == 'request.json'
                        else launch if path.name == 'launch.json' else saved_read(path))
                    if fault == 'none': api.main()
                    else:
                        with pytest.raises(ValueError,match='retained launch'): api.main()
                        self.failed = True
            def wait(self):
                return api.c.process.TaskProcessObservation(kwargs['expected_process_identity'],self.pid,
                    self.creation_filetime,int(self.failed),'child_exited',.1,1,1024,(),(),None,(),1024,1024,True)
        yield Child()
    monkeypatch.setattr(api.c.process,'normal_task_child',owner)
    monkeypatch.setattr(sys,'argv',[api.__file__,'--declaration',str(tmp_path/'unused.yaml'),
        '--expected-sha256','0'*64,'--expected-implementation',pin,'--diagnostic-root',str(root),'--execute-development'])
    if fault == 'nested':
        with pytest.raises(ValueError,match='separate'): api.main()
        assert not root.exists()
    else:
        api.main()
        summary = api.read(root/'summary.json')
        assert summary['status'] == ('source_content_reproduced' if fault == 'none' else 'unresolved_probe')
        assert summary['observation_sha256'] == sha256((root/'observation.json').read_bytes()).hexdigest()
        if fault == 'none': assert summary['source_sha256'] == sha256((root/'source.json').read_bytes()).hexdigest()
        before = {p.name:p.read_bytes() for p in root.iterdir()}
        with pytest.raises(FileExistsError): api.main()
        assert {p.name:p.read_bytes() for p in root.iterdir()} == before
        assert events == ['spawn','release'] + (['source'] if fault == 'none' else [])
    assert (original/'preserved').read_bytes() == b'original bytes'
