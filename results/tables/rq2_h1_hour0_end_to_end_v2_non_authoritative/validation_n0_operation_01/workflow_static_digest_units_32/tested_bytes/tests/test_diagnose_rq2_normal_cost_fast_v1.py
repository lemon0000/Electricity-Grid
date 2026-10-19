from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import diagnose_rq2_normal_cost_fast_v1 as api
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
    body.update(component_timings=[[name,0.] for name in api.COMPONENTS], model_builds=1,
        fast_encoder_sha256=sha256(Path(api.fast.__file__).read_bytes()).hexdigest(),
        fast_input_identity=spec.expected_input_identity, post_fast_input_identity=spec.expected_input_identity,
        model_scale=vars(spec.expected_scale), initial_snapshot_variables=spec.expected_scale.variables,
        model_implementation_identity=api.kernel.streaming.implementation_identity(),
        normal_execution_identity=api.kernel.normal_execution_identity(spec.expected_input_identity,
            spec.expected_scale,declared_request.specification,declared_request.execution_budget),
        model_structure_identity='6'*64, initial_snapshot_identity='7'*64,
        component_costs_are_kernel_total=False, numerical_execution_performed=False,
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
        lifetime_peak_working_set_bytes=123, solver_calls=0, mechanism_initial_state=True,
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
    assert not (tmp_path/'costs.json').exists()


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
    if fault != 'missing': api.write(tmp_path/'costs.json',content)
    if fault == 'failure':
        failure = api.prior.failure_record(ValueError(), 'normal_component_costs')
        failure['schema'] = api.SCHEMA
        api.write(tmp_path/'failure.json',failure)
    if fault == 'fallback': api.write(tmp_path/'failure_write_failed.json',{})
    report = api.summarize(tmp_path,declared_request,'1'*64,'2'*64,'3'*64,
        dict(pid=123,creation_filetime=456),observation)
    assert report['status'] == ('normal_identity_comparison_observed' if fault == 'none' else 'unresolved_probe')
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
        api.write(target/'costs.json',extra(body,declared_request))
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
        assert summary['status'] == ('normal_identity_comparison_observed' if fault == 'none' else 'unresolved_probe')
        assert summary['observation_sha256'] == sha256((root/'observation.json').read_bytes()).hexdigest()
        if fault == 'none': assert summary['costs_sha256'] == sha256((root/'costs.json').read_bytes()).hexdigest()
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
        execution_budget=options['budget'])
    return prepared, request


def test_tiny_components_build_once_without_solver(tiny_inputs, monkeypatch):
    prepared, request = tiny_inputs
    def forbidden(*a, **k): raise AssertionError('component probe cannot solve')
    monkeypatch.setattr(api.kernel.native, 'create_solver', forbidden)
    monkeypatch.setattr(api.kernel, 'run_normal_only', forbidden)
    original = api.kernel.streaming.build_continuous_normal_model
    calls = []
    def build(*args, **kwargs):
        calls.append(1)
        return original(*args, **kwargs)
    monkeypatch.setattr(api.kernel.streaming, 'build_continuous_normal_model', build)
    result = api.component_costs(prepared, request)
    assert calls == [1] and result['model_builds'] == 1
    assert tuple(row[0] for row in result['component_timings']) == api.COMPONENTS
    assert all(type(row[1]) is float and row[1] >= 0 for row in result['component_timings'])
    assert result['model_scale'] == vars(request.source.expected_scale)
    assert result['initial_snapshot_variables'] == request.source.expected_scale.variables
    assert not result['numerical_execution_performed'] and not result['component_costs_are_kernel_total']
    assert result['fast_input_identity'] == result['post_fast_input_identity'] == request.source.expected_input_identity
    assert api.kernel.normal_input_identity(prepared.assembly.inputs) == request.source.expected_input_identity


def test_component_post_identity_detects_owned_data_mutation(tiny_inputs, monkeypatch):
    prepared, request = tiny_inputs
    original = api.kernel.streaming.build_continuous_normal_model
    def build(owned, **kwargs):
        model = original(owned, **kwargs)
        owned.data.hourly_points[0].demand_by_bus_mw[1] += 1.
        return model
    monkeypatch.setattr(api.kernel.streaming, 'build_continuous_normal_model', build)
    with pytest.raises(ValueError): api.component_costs(prepared, request)
    assert api.kernel.normal_input_identity(prepared.assembly.inputs) == request.source.expected_input_identity


def test_component_actual_scale_required(tiny_inputs, monkeypatch):
    prepared, request = tiny_inputs
    original = api.kernel.model_scale
    monkeypatch.setattr(api.kernel, 'model_scale', lambda model: replace(original(model), variables=1))
    with pytest.raises(ValueError, match='actual model scale'): api.component_costs(prepared, request)


def test_component_failure_retained_without_success(tmp_path, tiny_inputs, monkeypatch):
    prepared, request = tiny_inputs
    monkeypatch.setattr(api, 'assemble', lambda *a: prepared)
    def failed(*a): raise MemoryError('component allocation failed')
    monkeypatch.setattr(api, 'component_costs', failed)
    with pytest.raises(MemoryError): api.child(tmp_path, request, api.implementation_identity(), api.source.implementation_identity())
    failure = api.read(tmp_path/'failure.json')
    assert failure['exception_type'] == 'MemoryError' and failure['stage'] == 'normal_component_costs'
    assert not (tmp_path/'costs.json').exists()


@pytest.mark.parametrize('fault', ['missing', 'order', 'integer', 'negative', 'nan', 'sum', 'extra'])
def test_component_timing_faults(declared_request, content, fault):
    rows = content['component_timings']
    if fault == 'missing': rows.pop()
    if fault == 'order': rows.reverse()
    if fault == 'integer': rows[0][1] = 0
    if fault == 'negative': rows[0][1] = -1.
    if fault == 'nan': rows[0][1] = float('nan')
    if fault == 'sum': rows[0][1] = 10.
    if fault == 'extra': rows.append(['unregistered', 0.])
    with pytest.raises(ValueError): api.validate_content(content, declared_request, '1'*64, '2'*64, 123)


@pytest.mark.parametrize('field,value', [('model_builds', True), ('initial_snapshot_variables', 1),
    ('fast_encoder_sha256', '0'*64), ('fast_input_identity', '0'*64), ('post_fast_input_identity', '0'*64),
    ('model_structure_identity', 'not a pin'), ('initial_snapshot_identity', True),
    ('normal_execution_identity', '0'*64), ('model_implementation_identity', '0'*64),
    ('component_costs_are_kernel_total', True), ('numerical_execution_performed', True)])
def test_component_metadata_faults(declared_request, content, field, value):
    content[field] = value
    with pytest.raises(ValueError): api.validate_content(content, declared_request, '1'*64, '2'*64, 123)


@pytest.mark.parametrize('phase', ['before', 'after'])
def test_fast_encoder_mismatch_rejected(tiny_inputs, monkeypatch, phase):
    prepared, request = tiny_inputs
    original = api.fast.normal_input_identity
    calls = []
    def identity(value):
        calls.append(1)
        if len(calls) == (1 if phase == 'before' else 2):
            return '0'*64
        return original(value)
    monkeypatch.setattr(api.fast, 'normal_input_identity', identity)
    with pytest.raises(ValueError, match='identity mismatch|implementation drift'):
        api.component_costs(prepared, request)
