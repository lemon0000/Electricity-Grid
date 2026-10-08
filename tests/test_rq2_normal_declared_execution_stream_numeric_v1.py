from dataclasses import asdict, fields, replace
from hashlib import sha256
from pathlib import Path

import pytest

from tests.test_rq2_normal_task_inputs_stream_v1 import supplied as prepared_source, encoded
from tests.test_rq2_pair_normal_stream_v1 import supplied as bound_source
from tests.test_rq2_source_normal_v1 import supplied as source_supplied
from tests.test_rq2_continuous_grid_normal_v1 import model_for
from tests.test_rq2_normal_execution_stream_numeric_v1 import BUDGET, SPEC
from src.rq2_joint_deliverability_boundary_v1 import normal_declared_execution_stream_numeric as api


@pytest.fixture
def supplied(prepared_source):
    request, record = prepared_source
    prepared = api.prepare.prepare_task_inputs(request,
        expected_request_identity=api.prepare.task_source_identity(request))
    scale = api.kernel.model_scale(model_for(prepared.assembly.inputs))
    record['model_scale'] = asdict(scale)
    raw = encoded(record)
    Path(request.normal_record_path).write_bytes(raw)
    request = replace(request, expected_scale=scale, expected_normal_record_sha256=sha256(raw).hexdigest())
    request_pin = api.prepare.task_source_identity(request)
    normal_pin = api.kernel.normal_execution_identity(request.expected_input_identity, scale, SPEC, BUDGET)
    lineage = dict(expected_assembly_identity=prepared.assembly.assembly_identity,
        expected_source_implementation_identity=prepared.assembly.implementation_identity,
        expected_binding_implementation_identity=prepared.binding.implementation_identity)
    source_pin = api.source.source_execution_identity(prepared.binding.binding_identity, normal_pin,
        prepared.declaration, expected_pair_identity=request.expected_pair_identity, **lineage)
    options = dict(**lineage, expected_request_identity=request_pin,
        expected_binding_identity=prepared.binding.binding_identity, expected_normal_execution_identity=normal_pin,
        expected_source_execution_identity=source_pin, expected_declared_execution_identity=api.declared_execution_identity(
            request, expected_request_identity=request_pin, expected_source_execution_identity=source_pin),
        specification=SPEC, budget=BUDGET)
    return request, options


def run(supplied, **changes):
    request, options = supplied
    return api.run_declared_normal(request, **{**options, **changes})


def test_prior_declared_pin_cannot_authorize_fast_entry(supplied, monkeypatch):
    from src.rq2_joint_deliverability_boundary_v1 import normal_declared_execution_stream as prior
    request, options = supplied
    old_pin = prior.declared_execution_identity(request,
        expected_request_identity=options['expected_request_identity'],
        expected_source_execution_identity=options['expected_source_execution_identity'])
    monkeypatch.setattr(api.prepare, 'prepare_task_inputs', lambda *a, **k: pytest.fail('prepare entered'))
    with pytest.raises(ValueError, match='identity drift'):
        run(supplied, expected_declared_execution_identity=old_pin)


def test_before_source_failure_after_prepare_and_rechecks(supplied, monkeypatch):
    events = []
    prepare = api.prepare.prepare_task_inputs
    lineage = api.source.source_execution_identity
    read = api.prepare._read_pinned
    def prepared(*a, **k):
        result = prepare(*a, **k)
        events.append('prepared')
        return result
    def checked(*a, **k):
        result = lineage(*a, **k)
        events.append('lineage')
        return result
    def pinned(*a, **k):
        result = read(*a, **k)
        if 'prepared' in events:
            events.append('declaration')
        return result
    def callback():
        events.append('callback')
        raise RuntimeError('runtime context rejected')
    monkeypatch.setattr(api.prepare, 'prepare_task_inputs', prepared)
    monkeypatch.setattr(api.source, 'source_execution_identity', checked)
    monkeypatch.setattr(api.prepare, '_read_pinned', pinned)
    monkeypatch.setattr(api.source, 'run_source_normal', lambda *a, **k: pytest.fail('source entered'))
    monkeypatch.setattr(api.kernel.native, 'create_solver', lambda *a, **k: pytest.fail('solver entered'))
    with pytest.raises(RuntimeError, match='runtime context rejected'):
        run(supplied, before_source=callback)
    assert events.index('prepared') < events.index('lineage') < events.index('callback')
    assert events.count('declaration') >= 3 and events[-1] == 'callback'


def test_noncallable_callback_rejected_before_prepare(supplied, monkeypatch):
    monkeypatch.setattr(api.prepare, 'prepare_task_inputs', lambda *a, **k: pytest.fail('prepare entered'))
    with pytest.raises(TypeError, match='callable runtime check'):
        run(supplied, before_source=42)


@pytest.mark.parametrize('fault', ['lineage', 'declaration'])
def test_pre_source_drift_prevents_callback_and_source(supplied, monkeypatch, fault):
    prepare = api.prepare.prepare_task_inputs
    def changed(*a, **k):
        result = prepare(*a, **k)
        if fault == 'lineage':
            monkeypatch.setattr(api.source, 'source_execution_identity', lambda *a, **k: '0'*64)
        else:
            path = Path(supplied[0].pair_declaration_path)
            path.write_bytes(path.read_bytes()+b'\n')
        return result
    monkeypatch.setattr(api.prepare, 'prepare_task_inputs', changed)
    monkeypatch.setattr(api.source, 'run_source_normal', lambda *a, **k: pytest.fail('source entered'))
    with pytest.raises(ValueError):
        run(supplied, before_source=lambda: pytest.fail('callback before rechecks'))


def test_full_tiny_prepare_source_binding_and_native_solve(supplied):
    result = run(supplied)
    assert result.accepted, (result.errors, result.source_result)
    assert result.solver_calls == 1 and result.call_count_complete
    assert result.source_result.normal_result.witness.terminal_carry.source_hour == 3
    assert result.source_result.normal_result.normal.objective == pytest.approx(120.)
    assert result.mechanism_initial_state is True
    assert not any((result.formal_result, result.observed_power_mapping,
        result.hard_resource_limits_enforced, result.durable_invocation_tracking))
    assert len(result.identity) == 64
    with pytest.raises(TypeError): api.DeclaredNumericStreamingNormalResult()


@pytest.mark.parametrize('pin', ['expected_request_identity', 'expected_declared_execution_identity',
    'expected_assembly_identity', 'expected_binding_identity', 'expected_source_implementation_identity',
    'expected_binding_implementation_identity', 'expected_normal_execution_identity', 'expected_source_execution_identity'])
def test_external_pins_prevent_native_call(supplied, monkeypatch, pin):
    calls=[]
    def forbidden(*args, **kwargs):
        calls.append(1)
        raise AssertionError('native forbidden')
    monkeypatch.setattr(api.kernel.native, 'create_solver', forbidden)
    try:
        result=run(supplied, **{pin:'0'*64})
        assert not result.accepted
    except ValueError:
        pass
    assert calls == []


@pytest.mark.parametrize('fault', ['file', 'implementation', 'source_implementation', 'interrupt'])
def test_post_declaration_failure_preserves_solve(supplied, monkeypatch, fault):
    original=api.source.run_source_normal
    def changed(*args, **kwargs):
        result=original(*args, **kwargs)
        if fault=='file': Path(supplied[0].normal_record_path).write_bytes(b'changed')
        elif fault=='implementation': monkeypatch.setattr(api.prepare,'task_source_identity',lambda *a:'0'*64)
        elif fault=='source_implementation': monkeypatch.setattr(api.source,'source_execution_identity',lambda *a,**k:'0'*64)
        else:
            def interrupted(*a, **k): raise KeyboardInterrupt('post interrupted')
            monkeypatch.setattr(api.prepare,'_read_pinned',interrupted)
        return result
    monkeypatch.setattr(api.source,'run_source_normal',changed)
    result=run(supplied)
    assert not result.accepted and result.source_result.source_bound_normal_accepted
    assert result.solver_calls==1 and result.call_count_complete
    assert result.errors[0].startswith('post_declaration:')
    if fault=='interrupt': assert result.status=='interrupted_declared_normal'


@pytest.mark.parametrize('fault',['missing','interrupt','nonowned'])
def test_missing_source_return_cannot_infer_zero_calls(supplied,monkeypatch,fault):
    def missing(*a,**k):
        if fault=='nonowned': return {'accepted':True}
        if fault=='interrupt': raise KeyboardInterrupt()
        raise RuntimeError('lost return')
    monkeypatch.setattr(api.source,'run_source_normal',missing)
    result=run(supplied)
    assert not result.accepted and result.source_result is None
    assert result.solver_calls is None and not result.call_count_complete


@pytest.mark.parametrize('field,value', [('execution_identity','0'*64),('expected_binding_identity','0'*64),
    ('source_correspondence_verified',False),('source_bound_normal_accepted',1),('binding_after_json','{}'),
    ('formal_result',True),('solver_calls',0),('errors',('failure',))])
def test_inconsistent_typed_source_success_rejected(supplied,monkeypatch,field,value):
    original=api.source.run_source_normal
    def changed(*a,**k):
        result=original(*a,**k)
        payload={f.name:getattr(result,f.name) for f in fields(result)}
        payload[field]=value
        return api.kernel.native._make(api.source.NumericStreamingSourceNormalExecutionResult,**payload)
    monkeypatch.setattr(api.source,'run_source_normal',changed)
    result=run(supplied)
    assert not result.accepted and result.errors


def test_legacy_full_input_paths_not_used(supplied,monkeypatch):
    def forbidden(*a,**k): raise AssertionError('legacy annual path')
    for module,names in ((api.source.legacy,('run_source_normal',)),
        (api.kernel.legacy,('run_normal_only','normal_input_identity')),
        (api.prepare.legacy,('prepare_task_inputs',)),
        (api.source.binding.old_pair,('bind_pair_normal',))):
        for name in names: monkeypatch.setattr(module,name,forbidden)
    assert run(supplied).accepted


@pytest.mark.parametrize('field,value', [('request_identity','0'*64),('solver_calls',False),
    ('mechanism_initial_state',False),('normal_assignment_verified',True),('formal_result',True)])
def test_prepared_role_or_pin_rejected_before_source(supplied,monkeypatch,field,value):
    original=api.prepare.prepare_task_inputs
    def changed(*a,**k):
        result=original(*a,**k)
        payload={f.name:getattr(result,f.name) for f in fields(result)}
        payload[field]=value
        return api.kernel.native._make(api.prepare.PreparedStreamingNormalTaskInputs,**payload)
    monkeypatch.setattr(api.prepare,'prepare_task_inputs',changed)
    monkeypatch.setattr(api.source,'run_source_normal',lambda *a,**k:pytest.fail('source entered'))
    with pytest.raises(ValueError,match='independent pins or role'):run(supplied)


def test_inner_kernel_binding_mismatch_not_hidden_by_source_success(supplied,monkeypatch):
    original=api.source.run_source_normal
    def changed(*a,**k):
        result=original(*a,**k)
        inner={f.name:getattr(result.normal_result,f.name) for f in fields(result.normal_result)}
        inner['execution_identity']='0'*64
        payload={f.name:getattr(result,f.name) for f in fields(result)}
        payload['normal_result']=api.kernel.native._make(api.kernel.NumericStreamingNormalExecutionResult,**inner)
        return api.kernel.native._make(api.source.NumericStreamingSourceNormalExecutionResult,**payload)
    monkeypatch.setattr(api.source,'run_source_normal',changed)
    result=run(supplied)
    assert not result.accepted and 'normal_result_binding_mismatch' in result.errors


def test_fast_declaration_pin_cannot_authorize_numeric_declaration(supplied, monkeypatch):
    from src.rq2_joint_deliverability_boundary_v1 import normal_declared_execution_stream_fast as prior
    request, options = supplied
    pin = prior.declared_execution_identity(request,
        expected_request_identity=options['expected_request_identity'],
        expected_source_execution_identity=options['expected_source_execution_identity'])
    monkeypatch.setattr(api.prepare, 'prepare_task_inputs', lambda *a, **k: pytest.fail('prepare entered'))
    with pytest.raises(ValueError, match='identity drift'):
        run(supplied, expected_declared_execution_identity=pin)
