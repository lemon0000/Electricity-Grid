from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import diagnose_rq2_normal_solver_phases_v1 as api
from test_rq2_normal_declared_execution_stream_v1 import (
    supplied as tiny_declared, prepared_source, bound_source, source_supplied)


@pytest.fixture(autouse=True)
def retain_guard_functions(monkeypatch):
    for obj,name in ((api.kernel,'run_normal_only'),(api.kernel.native,'create_solver'),
            (api.c.worker.kernel,'run_normal_only'),(api.c.worker.journal.execution,'run_source_normal')):
        monkeypatch.setattr(obj,name,getattr(obj,name))


@pytest.fixture(scope='module')
def declared_request():
    return api.prior.audit.read_declaration(Path('configs/rq2_normal_task_h25_development_v1.DRAFT.yaml'),
        '9a49cccf52e23d91a43511322a5abaf569e6cd2dfbf8d6db67b7d43d3c228aa6')[1]


def test_full_preparation_entry_receives_new_pin(declared_request, monkeypatch):
    seen = []
    def prepare(request, **kwargs):
        seen.append((request,kwargs)); return 'sentinel'
    monkeypatch.setattr(api.preparation,'prepare_task_inputs',prepare)
    assert api.assemble(declared_request,api.source.implementation_identity())=='sentinel'
    assert seen == [(declared_request.source, dict(expected_request_identity=
        api.preparation.task_source_identity(declared_request.source)))]
    with pytest.raises(ValueError,match='implementation drift'):
        api.assemble(declared_request,'0'*64)


def extra(body, declared_request):
    from hashlib import sha256
    spec=declared_request.source
    record=api.c.worker.inputs._json(api.c.worker.inputs._read_pinned(spec.normal_record_path,
        spec.expected_normal_record_sha256,spec.max_normal_record_bytes))
    wire=api.preparation.source._json(record['binding'])
    impl=api.preparation.stream_binding.implementation_identity()
    body.update(observation=dict(profile=dict(schema=api.profile.SCHEMA,
        legacy_status='aborted', legacy_termination='maxTimeLimit', solution_count=0,
        internal_termination='maxTimeLimit', internal_solution_status='noSolution',
        timers=[[name,1,0.] for name in ('set_instance','optimize','load solution')],
        internal_wall_seconds=0., highs_reported_seconds=0., solve_interface_seconds=0.,
        counters=dict.fromkeys(api.profile.COUNTERS), solver_log_bytes=1,
        solver_log_sha256=sha256(b'x').hexdigest(), solver_calls=1,
        model_values_loaded=False, normal_accepted=False, infeasibility_certificate=None,
        optimality_certificate=None, native_execution_authenticated=False,
        formal_result=False, security_certified=False), model_structure_identity='6'*64,
        input_identity=spec.expected_input_identity, implementation_identity=api.profile.implementation_identity()),
        prepared_request_identity=api.preparation.task_source_identity(spec),
        normal_assignment_verified=False,
        binding_implementation_identity=impl,legacy_content_binding_identity=spec.expected_binding_identity,
        legacy_binding_sha256=sha256(wire.encode()).hexdigest(),
        binding_identity=api.source.stream.digest(api.preparation.stream_binding.CONTRACT,
            spec.expected_input_identity,body['assembly_identity'],spec.expected_pair_identity,wire,impl),
        preparation_timings=dict.fromkeys(api.prior.TIMINGS,0.))
    return body


@pytest.fixture
def content(declared_request):
    spec = declared_request.source
    record = api.c.worker.inputs._json(api.c.worker.inputs._read_pinned(spec.normal_record_path,
        spec.expected_normal_record_sha256, spec.max_normal_record_bytes))
    power = record['binding']['power_binding']
    hours = power['raw_source_hours']
    body = dict(schema=api.SCHEMA, pid=123, normal_identity=spec.expected_input_identity,
        legacy_content_assembly_identity=spec.expected_assembly_identity,
        assembly_identity=api.source.stream.digest(api.source.CONTRACT, power['grid_source_manifest_sha256'],
            tuple(hours), spec.expected_input_identity, spec.expected_assembly_identity, '2'*64),
        implementation_identity='2'*64, probe_implementation_identity='1'*64,
        source_manifest_sha256=power['grid_source_manifest_sha256'], raw_source_hours=hours,
        source_hours=[h+1 for h in hours], annual_source_hours=8784, elapsed_seconds=1.,
        lifetime_peak_working_set_bytes=123, solver_calls=1, mechanism_initial_state=True,
        observed_power_mapping=False, formal_result=False, whole_task_resources_verified=False)

    return extra(body,declared_request)


def test_content_success(declared_request, content):
    api.validate_content(content, declared_request, '1'*64, '2'*64, 123)


@pytest.mark.parametrize('field',['prepared_request_identity','binding_identity','binding_implementation_identity',
    'legacy_content_binding_identity','legacy_binding_sha256','normal_assignment_verified'])
def test_prepare_metadata_fault(declared_request,content,field):
    content[field] = True if field=='normal_assignment_verified' else '0'*64
    with pytest.raises(ValueError): api.validate_content(content,declared_request,'1'*64,'2'*64,123)


@pytest.mark.parametrize('fault',['body','pin'])
def test_parent_rejects_self_consistent_wrong_legacy_wire(declared_request,content,monkeypatch,fault):
    spec=declared_request.source
    record=api.c.worker.inputs._json(api.c.worker.inputs._read_pinned(spec.normal_record_path,
        spec.expected_normal_record_sha256,spec.max_normal_record_bytes))
    if fault=='body': record['binding']['observed_power_mapping']=True
    else: record['binding']['binding_identity']='0'*64
    monkeypatch.setattr(api.c.worker.inputs,'_json',lambda raw:record)
    # Recompute all child metadata around the forged wire: its internal new
    # digest is consistent, but its legacy body is not the external old pin.
    extra(content,declared_request)
    with pytest.raises(ValueError,match='legacy binding external content'):
        api.validate_content(content,declared_request,'1'*64,'2'*64,123)


@pytest.mark.parametrize('fault',['missing','integer','negative','nan','sum','outer'])
def test_preparation_timing_fault(declared_request,content,fault):
    times=content['preparation_timings']
    if fault=='missing': times.pop('declaration_seconds')
    elif fault=='integer': times['declaration_seconds']=0
    elif fault=='negative': times['declaration_seconds']=-1.
    elif fault=='nan': times['declaration_seconds']=float('nan')
    elif fault=='sum': times['observed_total_seconds']=.5
    elif fault=='outer': times.update(declaration_seconds=2.,observed_total_seconds=2.)
    with pytest.raises(ValueError): api.validate_content(content,declared_request,'1'*64,'2'*64,123)


@pytest.mark.parametrize('field,value', [('normal_identity','0'*64), ('assembly_identity','0'*64),
    ('pid',True), ('solver_calls',False), ('formal_result',True), ('whole_task_resources_verified',True),
    ('annual_source_hours',25), ('raw_source_hours',[0]), ('source_hours',[1]),
    ('observed_power_mapping',True), ('elapsed_seconds',float('nan')), ('elapsed_seconds',1),
    ('lifetime_peak_working_set_bytes',0), ('lifetime_peak_working_set_bytes',True), ('extra',1)])
def test_content_fault(declared_request, content, field, value):
    content[field] = value
    with pytest.raises(ValueError): api.validate_content(content, declared_request, '1'*64, '2'*64,123)


@pytest.mark.parametrize('entry', ['run_normal_only','run_source_normal'])
def test_solver_guards_and_failure_preservation(tmp_path, declared_request, monkeypatch, entry):
    w = api.c.worker
    objects = dict(run_normal_only=w.kernel, run_source_normal=w.journal.execution)
    for name, obj in objects.items(): monkeypatch.setattr(obj, name, getattr(obj,name))
    monkeypatch.setattr(api, 'assemble', lambda *a: getattr(objects[entry],entry)())
    with pytest.raises(AssertionError, match='ordinary normal execution forbidden'):
        api.child(tmp_path, declared_request, '1'*64, '2'*64)
    assert api.read(tmp_path/'failure.json')['exception_type'] == 'AssertionError'
    assert api.read(tmp_path/'failure.json')['schema'] == api.SCHEMA
    assert not (tmp_path/'phases.json').exists()


@pytest.mark.parametrize('fault', ['none','type','pid','identity','exit','quiet','limits','formal',
    'disk','whole','numerical','missing','malformed','failure','fallback',
    'nan_elapsed','integer_elapsed','samples','peak','total_peak','reserve','resource_error','api_error',
    'implementation_before','implementation_after'])
def test_parent_unresolved_faults(tmp_path, declared_request, content, monkeypatch, fault):
    pins = iter(['0'*64] if fault == 'implementation_before' else
        ['1'*64, '0'*64] if fault == 'implementation_after' else ['1'*64]*2)
    monkeypatch.setattr(api, 'implementation_identity', lambda: next(pins))
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
    if fault != 'missing': api.write(tmp_path/'phases.json',content)
    api.write(tmp_path/'native.intent.json', api.invocation_intent(declared_request, '1'*64, 123))
    if fault == 'failure':
        failure = api.prior.failure_record(ValueError(), 'normal_solver_phases')
        failure['schema'] = api.SCHEMA
        api.write(tmp_path/'failure.json',failure)
    if fault == 'fallback': api.write(tmp_path/'failure_write_failed.json',{})
    report = api.summarize(tmp_path,declared_request,'1'*64,'2'*64,'3'*64,
        dict(pid=123,creation_filetime=456),observation)
    assert report['status'] == ('normal_solver_phases_observed' if fault == 'none' else 'unresolved_probe')
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
        api.write(target/'phases.json',extra(body,declared_request))
        api.write(target/'native.intent.json',api.invocation_intent(declared_request,pin,os.getpid()))
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
        assert summary['status'] == ('normal_solver_phases_observed' if fault == 'none' else 'unresolved_probe')
        assert summary['observation_sha256'] == sha256((root/'observation.json').read_bytes()).hexdigest()
        if fault == 'none': assert summary['phases_sha256'] == sha256((root/'phases.json').read_bytes()).hexdigest()
        before = {p.name:p.read_bytes() for p in root.iterdir()}
        with pytest.raises(FileExistsError): api.main()
        assert {p.name:p.read_bytes() for p in root.iterdir()} == before
        assert events == ['spawn','release'] + (['source'] if fault == 'none' else [])
    assert (original/'preserved').read_bytes() == b'original bytes'


@pytest.fixture
def tiny_inputs(tiny_declared):
    source, options = tiny_declared
    prepared = api.preparation.prepare_task_inputs(source,
        expected_request_identity=options['expected_request_identity'])
    request = SimpleNamespace(source=source, specification=options['specification'],
        execution_budget=options['budget'],
        expected_source_request_identity=api.c.worker.inputs.task_source_identity(source))
    return prepared, request


@pytest.mark.parametrize('fault', ['none', 'reservation', 'native', 'after_native'])
def test_tiny_call_reservation_failure_and_no_retry(tmp_path, tiny_inputs, monkeypatch, fault):
    prepared, request = tiny_inputs
    monkeypatch.setattr(api, 'assemble', lambda *a: prepared)
    pin = api.implementation_identity()
    original = api.kernel.native.create_solver
    calls = []
    def create(spec):
        solver, options = original(spec)
        solve = solver.solve
        def observed(model, **kwargs):
            assert api.read(tmp_path/'native.intent.json') == api.invocation_intent(request, pin, api.os.getpid())
            calls.append(1)
            if fault == 'native':
                raise RuntimeError('native call failed')
            return solve(model, **kwargs)
        monkeypatch.setattr(solver, 'solve', observed)
        return solver, options
    monkeypatch.setattr(api.kernel.native, 'create_solver', create)
    if fault == 'reservation':
        api.write(tmp_path/'native.intent.json', {'preserved': True})
    if fault == 'after_native':
        def failed(*a): raise ValueError('post-return extraction failed')
        monkeypatch.setattr(api.profile, 'extract', failed)
    if fault == 'none':
        api.child(tmp_path, request, pin, api.source.implementation_identity())
        content = api.read(tmp_path/'phases.json')
        api.profile.validate_profile(content['observation']['profile'])
        assert content['solver_calls'] == 1 and content['normal_assignment_verified'] is False
    else:
        with pytest.raises((FileExistsError, RuntimeError, ValueError)):
            api.child(tmp_path, request, pin, api.source.implementation_identity())
        assert api.read(tmp_path/'failure.json')['stage'] == 'normal_solver_phases'
        assert not (tmp_path/'phases.json').exists()
    assert len(calls) == (0 if fault == 'reservation' else 1)
    before = {p.name:p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(FileExistsError):
        api.child(tmp_path, request, pin, api.source.implementation_identity())
    assert len(calls) == (0 if fault == 'reservation' else 1)
    # A second invocation can add only a failure sidecar; existing evidence stays intact.
    assert all((tmp_path/name).read_bytes() == data for name,data in before.items())


@pytest.mark.parametrize('fault', ['missing', 'pid', 'input_identity', 'solver_calls', 'formal_result'])
def test_parent_requires_matching_invocation_and_reports_unknown(tmp_path, declared_request, content, monkeypatch, fault):
    monkeypatch.setattr(api, 'implementation_identity', lambda: '1'*64)
    api.write(tmp_path/'phases.json', content)
    intent = api.invocation_intent(declared_request, '1'*64, 123)
    if fault != 'missing':
        intent[fault] = 124 if fault == 'pid' else 'wrong'
        api.write(tmp_path/'native.intent.json', intent)
    observation = api.c.process.TaskProcessObservation('3'*64,123,456,0,'child_exited',1.,2,
        999999,(),(),None,(),100,100,True)
    report = api.summarize(tmp_path, declared_request, '1'*64, '2'*64, '3'*64,
        dict(pid=123,creation_filetime=456), observation)
    assert report['status'] == 'unresolved_probe'
    assert report['solver_calls'] is None and report['call_count_complete'] is False


@pytest.mark.parametrize('fault', ['extra', 'input', 'implementation', 'authority', 'timing', 'log_text'])
def test_parent_rejects_nested_profile_faults(declared_request, content, fault):
    observed = content['observation']
    if fault == 'extra': observed['extra'] = 1
    if fault == 'input': observed['input_identity'] = '0'*64
    if fault == 'implementation': observed['implementation_identity'] = '0'*64
    if fault == 'authority': observed['profile']['normal_accepted'] = True
    if fault == 'timing': observed['profile']['solve_interface_seconds'] = 2.
    if fault == 'log_text': observed['profile']['solver_log'] = 'objective 123'
    with pytest.raises(ValueError):
        api.validate_content(content, declared_request, '1'*64, '2'*64, 123)

