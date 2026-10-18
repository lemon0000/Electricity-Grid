from dataclasses import fields, replace
from hashlib import sha256
import json
from pathlib import Path

import pytest

from tests.test_rq2_normal_declared_execution_gurobi_ordered_v1 import supplied as declared_source
from tests.test_rq2_normal_task_inputs_stream_v1 import supplied as prepared_source, encoded
from tests.test_rq2_pair_normal_stream_v1 import supplied as bound_source
from tests.test_rq2_source_normal_v1 import supplied as source_supplied
from test_rq2_scale_normal_v1 import arguments
from src.rq2_joint_deliverability_boundary_v1 import scale_normal_source as api


@pytest.fixture
def supplied(declared_source):
    source, old = declared_source
    prepared = api.prepare.prepare_task_inputs(source,
        expected_request_identity=api.prepare.task_source_identity(source))
    args = arguments(prepared.assembly.inputs, seconds=1)
    request = api.ScaleNormalSourceRequest(source, old['expected_request_identity'],
        old['expected_assembly_identity'], old['expected_binding_identity'], old['expected_source_implementation_identity'],
        old['expected_binding_implementation_identity'], args['expected_execution_identity'],
        args['specification'], args['budget'], args['resource_plan'])
    return request, api.request_identity(request)


def run(supplied, **kw):
    request, pin = supplied
    return api.run_source(request, expected_request_identity=pin, **kw)


def audit(supplied, result):
    request, pin = supplied
    data = api.replay._bytes(result)
    return api.audit_source(data, request, expected_sha256=sha256(data).hexdigest(),
        expected_request_identity=pin, max_record_bytes=32*1024**2)


def test_source_native_and_replay_use_rebuilt_inputs(supplied, monkeypatch):
    result=run(supplied)
    assert result['accepted'] and result['solver_calls']==1, result['errors']
    assert result['source_before']==result['source_after']
    assert result['mechanism_initial_state'] and not result['observed_power_mapping']
    def forbidden(*a,**kw): raise AssertionError('solver in independent source audit')
    monkeypatch.setattr(api.kernel,'run_normal_only',forbidden)
    monkeypatch.setattr(api.kernel.native,'_solve',forbidden)
    monkeypatch.setattr(api.kernel.native,'create_solver',forbidden)
    report=audit(supplied,result)
    assert report['record_consistent'] and report['accepted_record_reproduced'],report
    assert report['solver_calls_by_replay']==0 and not report['formal_result']


@pytest.mark.parametrize('name', ['expected_source_request_identity','expected_assembly_identity',
    'expected_binding_identity','expected_source_implementation_identity','expected_binding_implementation_identity',
    'expected_normal_execution_identity'])
def test_external_pins_not_inferred_from_preparation(supplied,monkeypatch,name):
    request,pin=supplied
    monkeypatch.setattr(api.kernel,'run_normal_only',lambda *a,**kw:pytest.fail('kernel reached'))
    with pytest.raises(ValueError): run((replace(request,**{name:'0'*64}),pin))


def test_runtime_callback_outside_missing_return_catch(supplied,monkeypatch):
    called=[]
    def callback():
        called.append('callback')
        raise RuntimeError('runtime rejected')
    monkeypatch.setattr(api.kernel,'run_normal_only',lambda *a,**kw:pytest.fail('kernel reached'))
    with pytest.raises(RuntimeError,match='runtime rejected'): run(supplied,before_kernel=callback)
    assert called==['callback']


def test_source_change_in_callback_prevents_kernel(supplied,monkeypatch):
    def changed():
        p=Path(supplied[0].source.pair_declaration_path)
        p.write_bytes(p.read_bytes()+b'\n')
    monkeypatch.setattr(api.kernel,'run_normal_only',lambda *a,**kw:pytest.fail('kernel reached'))
    with pytest.raises(ValueError): run(supplied,before_kernel=changed)


@pytest.mark.parametrize('interruption',[False,True])
def test_missing_kernel_return_still_rechecks_source_and_keeps_unknown_calls(supplied,monkeypatch,interruption):
    original=api._prepare
    count=[]
    def prepared(*a,**kw):
        count.append(1)
        return original(*a,**kw)
    def failed(*a,**kw):
        if interruption: raise KeyboardInterrupt('injected')
        raise RuntimeError('injected')
    monkeypatch.setattr(api,'_prepare',prepared)
    monkeypatch.setattr(api.kernel,'run_normal_only',failed)
    result=run(supplied)
    assert len(count)==2 and result['source_correspondence_verified']
    assert result['solver_calls'] is None and not result['call_count_complete'] and not result['accepted']
    assert result['status']==('interrupted_source_bound_normal' if interruption else 'unresolved_source_bound_normal')
    report=audit(supplied,result)
    assert report['record_consistent'] and not report['accepted_record_reproduced']


def test_post_kernel_source_drift_preserves_numeric_result(supplied,monkeypatch):
    original=api.kernel.run_normal_only
    def changed(*a,**kw):
        result=original(*a,**kw)
        p=Path(supplied[0].source.pair_declaration_path)
        p.write_bytes(p.read_bytes()+b'\n')
        return result
    monkeypatch.setattr(api.kernel,'run_normal_only',changed)
    result=run(supplied)
    assert result['normal_record'] is not None and result['solver_calls']==1
    assert not result['accepted'] and not result['source_correspondence_verified'] and result['source_after'] is None
    assert any(e.startswith('post_source:') for e in result['errors'])
    with pytest.raises(ValueError): audit(supplied,result)


@pytest.mark.parametrize('field,value',[('formal_result',True),('solver_calls',0),('accepted',False),
    ('mechanism_initial_state',False),('schema','legacy'),('observed_wall_seconds',0.)])
def test_rehash_cannot_change_source_record_projection(supplied,field,value):
    result=run(supplied)
    result[field]=value
    with pytest.raises(ValueError): audit(supplied,result)


def test_replay_rechecks_source_after_numerical_reconstruction(supplied,monkeypatch):
    result=run(supplied)
    original=api.replay.replay_record
    def changed(*a,**kw):
        answer=original(*a,**kw)
        p=Path(supplied[0].source.config_path)
        p.write_bytes(p.read_bytes()+b'\n')
        return answer
    monkeypatch.setattr(api.replay,'replay_record',changed)
    with pytest.raises(ValueError): audit(supplied,result)


def test_false_source_flag_cannot_be_reencoded_as_zero(supplied):
    result=run(supplied)
    result['source_before']['observed_power_mapping']=0
    with pytest.raises(ValueError): audit(supplied,result)


def test_inconsistent_owned_normal_acceptance_rejected(supplied,monkeypatch):
    original=api.kernel.run_normal_only
    def changed(*a,**kw):
        normal=original(*a,**kw)
        values={f.name:getattr(normal,f.name) for f in fields(normal)}
        values['formal_result']=True
        return api.kernel.native._make(type(normal),**values)
    monkeypatch.setattr(api.kernel,'run_normal_only',changed)
    result=run(supplied)
    assert not result['accepted'] and 'normal_return_acceptance_inconsistent' in result['errors']


@pytest.mark.parametrize('marker',['normal_return_binding_mismatch','normal_return_acceptance_inconsistent','source_binding_changed'])
def test_false_error_cannot_downgrade_valid_result_after_rehash(supplied,marker):
    result=run(supplied)
    assert result['accepted']
    result.update(errors=[marker],accepted=False,status='unresolved_source_bound_normal')
    with pytest.raises(ValueError,match='not reproduced'):
        audit(supplied,result)
