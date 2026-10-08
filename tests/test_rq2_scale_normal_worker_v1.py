from dataclasses import replace
from hashlib import sha256
import json

import pytest

from tests.test_rq2_scale_normal_source_v1 import supplied, declared_source, prepared_source, bound_source, source_supplied
from src.rq2_joint_deliverability_boundary_v1 import scale_normal_worker as api


def setup(supplied,tmp_path_factory):
    request,pin=supplied
    parent=tmp_path_factory.mktemp('scale_normal_worker')
    path=parent/'request.json'
    raw=api.transport.export_request(request)
    path.write_bytes(raw)
    return dict(mode='execute',request_path=path,expected_request_sha256=sha256(raw).hexdigest(),
        expected_request_identity=pin,max_request_bytes=api.transport.LIMIT,root=parent/'normal_non_authoritative',
        receipt_path=parent/'execute_receipt_non_authoritative.json',expected_environment_identity=api.environment_identity(),
        expected_implementation_identity=api.implementation_identity(request),max_record_bytes=32*1024**2)


def test_fixed_worker_execute_then_independent_audit_preserves_files(supplied,tmp_path_factory,monkeypatch):
    args=setup(supplied,tmp_path_factory)
    executed=api.run_worker(**args)
    assert executed['outcome']['accepted'] and executed['outcome']['solver_calls']==1
    root=args['root']
    snapshots={p.name:p.read_bytes() for p in root.iterdir()}
    def forbidden(*a,**kw): raise AssertionError('solver from audit worker')
    monkeypatch.setattr(api.source.kernel,'run_normal_only',forbidden)
    monkeypatch.setattr(api.source.kernel.native,'_solve',forbidden)
    monkeypatch.setenv('TMP',str(root.parent))
    audit=dict(args,mode='audit',receipt_path=root.parent/'audit_receipt_non_authoritative.json',
        expected_intent_sha256=executed['intent_sha256'],expected_record_sha256=executed['record_sha256'],
        expected_execution_environment_identity=executed['environment_identity'],
        expected_environment_identity=api.environment_identity())
    report=api.run_worker(**audit)
    assert report['outcome']['record_consistent'] and report['outcome']['accepted_record_reproduced']
    assert report['outcome']['solver_calls_by_replay']==0 and not report['whole_task_resources_verified']
    assert snapshots=={p.name:p.read_bytes() for p in root.iterdir()}
    with pytest.raises((ValueError,FileExistsError)): api.run_worker(**args)


def test_intent_write_failure_stops_before_source(supplied,tmp_path_factory,monkeypatch):
    args=setup(supplied,tmp_path_factory)
    def failed(*a,**kw): raise OSError('injected intent write')
    monkeypatch.setattr(api.files,'_write',failed)
    monkeypatch.setattr(api.source,'run_source',lambda *a,**kw:pytest.fail('source entered'))
    with pytest.raises(OSError,match='injected'): api.run_worker(**args)
    assert not (args['root']/'normal_record.json').exists()
    lease=api.files.local._Lease(args['root'],False)
    lease.close()


def test_archive_failure_preserves_intent_and_releases_lease(supplied,tmp_path_factory,monkeypatch):
    args=setup(supplied,tmp_path_factory)
    def failed(*a,**kw): raise OSError('injected record write')
    monkeypatch.setattr(api,'_write_record',failed)
    with pytest.raises(OSError,match='injected'): api.run_worker(**args)
    assert (args['root']/'intent.json').exists() and not args['receipt_path'].exists()
    lease=api.files.local._Lease(args['root'],False)
    lease.close()


@pytest.mark.parametrize('fault',['environment','implementation','request','source_path','receipt_inside'])
def test_bad_worker_context_rejected_before_execution(supplied,tmp_path_factory,monkeypatch,fault):
    args=setup(supplied,tmp_path_factory)
    if fault in ('environment','implementation'): args['expected_'+fault+'_identity']='0'*64
    elif fault=='request': args['expected_request_sha256']='0'*64
    elif fault=='source_path': args['root']=api.Path(supplied[0].source.upstream_root)/'bad_non_authoritative'
    else: args['receipt_path']=args['root']/'receipt_non_authoritative.json'
    monkeypatch.setattr(api.source,'run_source',lambda *a,**kw:pytest.fail('source entered'))
    with pytest.raises(ValueError): api.run_worker(**args)
    assert not args['root'].exists()


def test_transport_exact_roundtrip_and_forbidden_owned_type(supplied):
    request,_=supplied
    raw=api.transport.export_request(request)
    assert api.transport.decode_request(raw)==request
    body=json.loads(raw)
    body['request'][0]='ScaleNormalExecutionResult'
    with pytest.raises(ValueError): api.transport.decode_request(api.source.replay._bytes(body))


@pytest.mark.parametrize('fault',['extra','duplicate','old_budget','bad_plan'])
def test_transport_rejects_noncanonical_or_unbound_request(supplied,fault):
    request,_=supplied
    raw=api.transport.export_request(request)
    body=json.loads(raw)
    if fault=='extra': body['extra']=False
    elif fault=='duplicate': body['request'][1].append(body['request'][1][0])
    elif fault=='old_budget':
        next(row for row in body['request'][1] if row[0]=='budget')[1][0]='NormalExecutionBudget'
    else:
        budget=replace(request.budget,resource_contract_identity='0'*64)
        with pytest.raises(ValueError): api.transport.export_request(replace(request,budget=budget))
        return
    with pytest.raises(ValueError): api.transport.decode_request(api.source.replay._bytes(body))


@pytest.mark.parametrize('target', ['source','kernel','native','factory'])
def test_audit_worker_itself_blocks_execution_and_restores_guards(supplied,tmp_path_factory,monkeypatch,target):
    args=setup(supplied,tmp_path_factory)
    executed=api.run_worker(**args)
    targets={'source':(api.source,'run_source'),'kernel':(api.source.kernel,'run_normal_only'),
        'native':(api.source.kernel.native,'_solve'),'factory':(api.source.kernel.native,'create_solver')}
    originals={key:getattr(obj,name) for key,(obj,name) in targets.items()}
    def attempted_execution(*a,**kw):
        obj,name=targets[target]
        return getattr(obj,name)()
    monkeypatch.setattr(api.source,'audit_source',attempted_execution)
    audit=dict(args,mode='audit',receipt_path=args['root'].parent/'audit_receipt_non_authoritative.json',
        expected_intent_sha256=executed['intent_sha256'],expected_record_sha256=executed['record_sha256'],
        expected_execution_environment_identity=executed['environment_identity'])
    with pytest.raises(RuntimeError,match='audit worker execution forbidden'):
        api.run_worker(**audit)
    assert all(getattr(obj,name) is originals[key] for key,(obj,name) in targets.items())
    assert not audit['receipt_path'].exists()
    lease=api.files.local._Lease(args['root'],False)
    lease.close()
