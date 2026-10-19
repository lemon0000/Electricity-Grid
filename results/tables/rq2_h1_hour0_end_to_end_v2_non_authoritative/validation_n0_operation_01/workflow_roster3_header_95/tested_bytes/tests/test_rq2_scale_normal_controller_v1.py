from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
import os
from pathlib import Path

import pytest

from tests.test_rq2_scale_normal_source_v1 import (
    supplied, declared_source, prepared_source, bound_source, source_supplied, run, audit,
)
from src.rq2_joint_deliverability_boundary_v1 import scale_normal_controller as api
from src.rq2_joint_deliverability_boundary_v1 import scale_normal_budget as budgets


@pytest.fixture
def pipeline(supplied):
    request,_=supplied
    envelope=replace(request.budget.envelope,max_wall_seconds=600,non_solver_seconds=599,
        archive_bytes=256*1024**2,scratch_bytes=32*1024**2)
    plan=replace(request.resource_plan,envelopes=(envelope,request.resource_plan.envelopes[1]),
        serial_budget=replace(request.resource_plan.serial_budget,max_total_wall_seconds=6800))
    budget=budgets.budget_for_task(plan,task_id='normal',max_observed_wall_seconds=121.,
        max_process_peak_working_set_bytes=8*1024**3,max_core_evidence_payload_bytes=16*1024**2)
    pin=api.worker.source.kernel.normal_execution_identity(request.source.expected_input_identity,
        request.source.expected_scale,request.specification,budget)
    request=replace(request,budget=budget,resource_plan=plan,expected_normal_execution_identity=pin)
    process=api.declared.DeclaredTaskProcessBudget(budget.resource_contract_identity,envelope,180.,.05,
        1024**3,1024**3,3.)
    allocation=api.NormalPipelineBudget(process,process,60,30,32*1024**2,16*1024**2,16*1024**2,
        8*1024**3,1017,1000)
    return request,allocation


def test_pipeline_identity_binds_serializable_request_and_allocation(pipeline,tmp_path):
    request,allocation=pipeline
    root=tmp_path/'controller_non_authoritative'
    env=dict(os.environ)
    pin=api.controller_identity(root,request,allocation=allocation,environment=env)
    assert len(pin)==64 and not root.exists()
    assert pin!=api.controller_identity(root,request,allocation=replace(allocation,controller_seconds=61),environment=env)


@pytest.mark.parametrize('changes',[
    {'controller_seconds':300},
    {'execute_overhead_seconds':60},
    {'max_record_bytes':65*1024**2},
    {'execute_scratch_bytes':17*1024**2},
    {'max_tree_entries':1016},
])
def test_pipeline_rejects_incomplete_allocations_before_creation(pipeline,changes):
    request,allocation=pipeline
    api.admit(request,allocation)
    with pytest.raises(ValueError):
        api.admit(request,replace(allocation,**changes))


@pytest.mark.parametrize('numerical,calls,complete,accepted,consistent,status', [
    (None,None,False,False,True,'normal_invocation_unknown_not_replayed'),
    ({},None,False,False,True,'normal_invocation_unknown_not_replayed'),
    ({},1,True,True,True,'replayed_accepted_normal'),
    ({},1,True,False,True,'replayed_unresolved_normal'),
    ({},1,True,False,False,'unresolved_normal_record_not_reproduced'),
])
def test_completion_preserves_unknown_calls_and_full_reservation(numerical,calls,complete,accepted,consistent,status):
    outcome=dict(numerical=numerical,accepted_record_reproduced=accepted,record_consistent=consistent)
    record=dict(solver_calls=calls,call_count_complete=complete)
    result=api._completion(outcome,record,600)
    assert result==dict(status=status,solver_calls=calls,call_count_complete=complete,reserved_solver_seconds=600)


def test_parent_replay_rejects_reencoded_nested_audit(supplied,monkeypatch):
    record=run(supplied)
    assert record['accepted'],record['errors']
    raw=api.worker.source.replay._bytes(record)
    outcome=json.loads(api.base.worker.store._bytes(audit(supplied,record)))
    def forbidden(*args,**kwargs):
        raise AssertionError('parent audit invoked solver')
    monkeypatch.setattr(api.worker.source.kernel,'run_normal_only',forbidden)
    monkeypatch.setattr(api.worker.source.kernel.native,'_solve',forbidden)
    monkeypatch.setattr(api.worker.source.kernel.native,'create_solver',forbidden)
    args=(record,raw,supplied[0],supplied[1],sha256(raw).hexdigest(),32*1024**2)
    api._verify_audit(outcome,*args)
    changed=deepcopy(outcome)
    changed['numerical']['native_replay']['optimal_flag_reproduced']=False
    changed=json.loads(api.base.worker.store._bytes(changed))
    # This receipt still passes the original top-level projection checks.
    api._audit_outcome(changed,record)
    with pytest.raises(ValueError,match='independent parent replay'):
        api._verify_audit(changed,*args)


def test_missing_return_audit_is_consistent_but_not_replayed(supplied,monkeypatch):
    def interrupted(*args,**kwargs):
        raise RuntimeError('injected missing return')
    monkeypatch.setattr(api.worker.source.kernel,'run_normal_only',interrupted)
    record=run(supplied)
    raw=api.worker.source.replay._bytes(record)
    outcome=json.loads(api.base.worker.store._bytes(audit(supplied,record)))
    api._verify_audit(outcome,record,raw,supplied[0],supplied[1],sha256(raw).hexdigest(),32*1024**2)
    assert outcome['record_consistent'] and outcome['numerical'] is None
    result=api._completion(outcome,record,600)
    assert result['status']=='normal_invocation_unknown_not_replayed'
    assert result['solver_calls'] is None and result['call_count_complete'] is False
    assert result['reserved_solver_seconds']==600


@pytest.mark.parametrize('target',[0,1,2,3])
def test_parent_audit_blocks_execution_and_restores_functions(monkeypatch,target):
    source=api.worker.source
    targets=((source,'run_source'),(source.kernel,'run_normal_only'),
             (source.kernel.native,'_solve'),(source.kernel.native,'create_solver'))
    originals=[getattr(obj,name) for obj,name in targets]
    monkeypatch.setattr(api,'_audit_outcome',lambda *args:None)
    def injected(*args,**kwargs):
        obj,name=targets[target]
        return getattr(obj,name)()
    monkeypatch.setattr(source,'audit_source',injected)
    with pytest.raises(RuntimeError,match='parent audit execution forbidden'):
        api._verify_audit({}, {}, b'',None,'0'*64,'0'*64,1024)
    assert [getattr(obj,name) for obj,name in targets]==originals


@pytest.fixture
def subprocess_pipeline(pipeline,bound_source,tmp_path_factory,monkeypatch):
    from src.rq2_joint_deliverability_boundary_v1 import normal_worker as codec
    request,allocation=pipeline
    parent=tmp_path_factory.mktemp('normal_pipeline')
    context=parent/'synthetic_source.json'
    context.write_text(json.dumps(dict(inputs=codec._encode(bound_source[2].inputs),
        pair=bound_source[3],window=bound_source[4])),encoding='utf-8')
    bootstrap=parent/'synthetic_worker.py'
    repository=Path(__file__).resolve().parents[1]
    bootstrap.write_text('import sys\nsys.path.insert(0, '+repr(str(repository))+')\n'+'''
import json
from copy import deepcopy
from pathlib import Path
from src.rq2_joint_deliverability_boundary_v1 import normal_worker as codec
from src.rq2_joint_deliverability_boundary_v1 import source_normal as source
from src.rq2_joint_deliverability_boundary_v1 import pair_normal_stream as pair
from src.rq2_joint_deliverability_boundary_v1 import scale_normal_worker as worker
context=json.loads(Path(sys.argv.pop(1)).read_text(encoding='utf-8'))
inputs=codec._decode(context['inputs'])
source.RTS_GMLC_MANIFEST_SHA256=inputs.carry.identity.source_sha256
source.verify_sha256_manifest=lambda root: True
source.load_rts_gmlc_chronological_data=lambda root: inputs.data
pair.source_pair.prepare_source_pair=lambda *a,**k:deepcopy(context['pair'])
pair.source_window.load_source_window=lambda *a,**k:deepcopy(context['window'])
pair.source_window.audit._load_config=lambda *a:{'inputs':{'power':{}}}
pair.source_window.audit._verify_package=lambda *a:(None,{'grid_source_manifest_sha256':inputs.carry.identity.source_sha256})
pair.source_window.audit._verify_hash=lambda *a:None
worker.main()
''',encoding='utf-8')
    original=api._argv
    def synthetic_argv(*args):
        argv=original(*args)
        return argv[:3]+[str(bootstrap),str(context)]+argv[4:]
    monkeypatch.setattr(api,'_argv',synthetic_argv)
    root=parent/'pipeline_non_authoritative'
    environment=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    pin=api.controller_identity(root,request,allocation=allocation,environment=environment)
    return root,request,dict(allocation=allocation,environment=environment,expected_controller_identity=pin)


def test_real_subprocess_pipeline_with_synthetic_source(subprocess_pipeline,monkeypatch):
    root,request,settings=subprocess_pipeline
    original_read,original_write,measure=api.base._read,api.base._write,api.supervision._measure
    protected=[]
    def held():
        with pytest.raises(ValueError,match='already held'):
            api.local._Lease(root/'normal_non_authoritative',False)
    def read(path,identity=None):
        if path.name=='audit_receipt_non_authoritative.json':
            held()
            protected.append('audit')
        return original_read(path,identity)
    def write(path,body):
        if path.name=='result.json':
            held()
            protected.append('final')
        return original_write(path,body)
    def before_terminal(*args,**kwargs):
        assert not (root/'result.json').exists(),'validation after terminal publication'
        return measure(*args,**kwargs)
    monkeypatch.setattr(api.base,'_read',read)
    monkeypatch.setattr(api.base,'_write',write)
    monkeypatch.setattr(api.supervision,'_measure',before_terminal)
    result=api.supervise_normal(root,request,**settings)
    assert protected==['audit','final']
    assert result['status']=='replayed_accepted_normal'
    assert result['solver_calls']==1 and result['call_count_complete']
    assert result['audit']['solver_calls_by_replay']==0
    assert [p['mode'] for p in result['phases']]==['execute','audit']
    assert all(p['observation']['whole_job_quiescent'] for p in result['phases'])
    assert not result['formal_result'] and not result['whole_task_resources_verified']
    assert (root/'result.json').read_bytes()==api.base.worker.store._bytes(result)
    for directory in (root,root/'normal_non_authoritative'):
        lease=api.local._Lease(directory,False)
        lease.close()


@pytest.mark.parametrize('fault',['audit_intent','audit_launch','intent_tamper','record_replace','lock_replace'])
def test_audit_failure_window_preserves_evidence_and_blocks_release(subprocess_pipeline,monkeypatch,fault):
    root,request,settings=subprocess_pipeline
    original=api.base._write
    release=api.declared._DeclaredTaskChild.release
    released=[]
    def guarded_release(child):
        released.append(child.pid)
        assert len(released)==1,'audit worker released despite failed durable evidence'
        return release(child)
    def write(path,body):
        if path.name in ('audit_intent.json','audit_launch.json') and path.stem==fault:
            raise OSError('injected audit write failure')
        result=original(path,body)
        if path.name=='audit_launch.json' and fault=='intent_tamper':
            with (root/'audit_intent.json').open('ab') as stream: stream.write(b' ')
        if path.name=='audit_intent.json' and fault in ('record_replace','lock_replace'):
            target=root/'normal_non_authoritative'/('normal_record.json' if fault=='record_replace' else 'execution.lock')
            replacement=root/'replacement.json'
            replacement.write_bytes(target.read_bytes())
            os.replace(replacement,target)
        return result
    monkeypatch.setattr(api.base,'_write',write)
    monkeypatch.setattr(api.declared._DeclaredTaskChild,'release',guarded_release)
    with pytest.raises((OSError,ValueError)):
        api.supervise_normal(root,request,**settings)
    assert len(released)==1
    assert (root/'normal_non_authoritative'/'normal_record.json').is_file()
    assert not (root/'result.json').exists()
    for directory in (root,root/'normal_non_authoritative'):
        lease=api.local._Lease(directory,False)
        lease.close()


@pytest.mark.parametrize('name',['execute_intent.json','execute_launch.json'])
def test_durable_failure_prevents_normal_worker_release(pipeline,tmp_path_factory,monkeypatch,name):
    request,allocation=pipeline
    root=tmp_path_factory.mktemp('normal_write_failure')/'pipeline_non_authoritative'
    environment=dict(os.environ)
    pin=api.controller_identity(root,request,allocation=allocation,environment=environment)
    write=api.base._write
    def failed(path,body):
        if path.name==name: raise OSError('injected durable write failure')
        return write(path,body)
    monkeypatch.setattr(api.base,'_write',failed)
    monkeypatch.setattr(api.declared._DeclaredTaskChild,'release',lambda child:pytest.fail('unrecorded worker released'))
    with pytest.raises(OSError,match='injected durable write failure'):
        api.supervise_normal(root,request,allocation=allocation,environment=environment,
            expected_controller_identity=pin)
    assert not (root/'normal_non_authoritative').exists()
    assert not (root/'result.json').exists()
    lease=api.local._Lease(root,False)
    lease.close()
