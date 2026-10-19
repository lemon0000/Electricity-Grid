from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from experiments import h1_phase_obligation_binding_development_v1 as m
from src.solvers.rq2_solver_adapter import Rq2SolverSpec


def prepare(root,resolver):
    """Real pinned RTS/marginal input, zero solver, no worker or Job launch."""
    catalog = resolver.data()['catalog'];axes = catalog['axes']['training_ub']
    coordinate = {k:v[0] for k,v in axes.items()}
    coordinate['power'],coordinate['workload'] = axes['power'][8],axes['workload'][17]
    ordinal = resolver.encode_coordinate('training_ub',coordinate)
    calibration = json.loads((m.ROOT/'configs/rq2_normal_h1_calibration_v3.json').read_bytes())
    origin = m.source_binding.H1SourceDeclaration('training',192,408,20260822,m.SOURCE_CONFIG_PIN)
    receipt = m.source_binding.load_pinned_current(origin,calibration['upstream_root'],config_path=calibration['config_path'])
    parent = m.snapshot.parent.SourceParent(root,receipt.network,Rq2SolverSpec(**calibration['work']['specification']),
        m.replay.H1HourReplayLimits(232,891,1272),origin=origin,upstream_root=calibration['upstream_root'],
        config_path=calibration['config_path'],dc_bus=calibration['dc_bus'],hours=192,create=True)
    try:
        m.prevalidate_enrollment(resolver,parent._declaration,family='training_ub',ordinal=ordinal,relative_hour=0)
        state,before,previous = parent._restore()
        receipt = parent._load(0,receipt.identity)
        packet = parent._packet(receipt,0,before,previous)
        parent._append(parent._intent(0,receipt,packet),receipt.audit_payload)
        pending = dict(expected_head=parent._journal.head,expected_source_identity=receipt.identity,
            expected_request_key=m.replay.request_key(packet,parent._spec,parent._limits),
            expected_packet_audit=packet.audit_identity)
        anchor = parent._anchor.inspect().record_sha256
        reader = m.snapshot.open_snapshot(parent._declaration,expected_parent_identity=parent.identity,expected_anchor_record=anchor)
        try: item = reader.pending_input(**pending)
        finally: reader.close()
        arguments = dict(resolver=resolver,declaration=parent._declaration,family='training_ub',ordinal=ordinal,
            relative_hour=0,expected_parent_identity=parent.identity,expected_anchor_record=anchor,
            pending_arguments=pending,expected_pending_receipt_sha256=item.receipt_sha256,
            job_budget=m.process.TaskProcessBudget(300,.05,512*1024**2,768*1024**2,2))
        return parent,arguments,catalog,item
    except BaseException:
        parent.close();raise


@pytest.fixture(scope='module')
def context(tmp_path_factory):
    with m.replay.guard.solver_calls_forbidden():
        resolver = m.open_manifest()
        parent,args,catalog,item = prepare(tmp_path_factory.mktemp('normal_binding')/'parent_non_authoritative',resolver)
        try:
            value = m.bind(**args)
            yield parent,args,catalog,item,value
        finally: parent.close()


def test_real_pending_origin_binding_and_fresh_inspection(context,tmp_path):
    parent,args,catalog,item,value = context
    assert value['normal_request_key'] == m.replay.request_key(item.packet,item.specification,item.limits)
    assert value['normal_input_identity'] == item.packet.input_identity
    assert value['raw_source_hours'] == dict(power=192,workload=408)
    assert value['display_source_hours'] == dict(power=193,workload=409)
    assert value['model_timestamp'] == '2000-01-01T00:00:00+00:00'
    assert value['source_parent_lineage']['pending_receipt']['stage_slots'] == 232
    assert value['enrollment_prevalidation']['hours'] == 168
    assert value['enrollment_prevalidation']['whole_enrollment_marginal_domains_and_workload_projection_checked'] is True
    assert value['enrollment_prevalidation']['whole_enrollment_RTS_correspondence_checked'] is False
    assert value['enrollment_prevalidation']['future_dispatch_mapping_checked'] is False
    assert all(value[k] is False for k in m.FLAGS)
    assert value['runtime_task_id'] is value['launch_request'] is value['host_resource_admission'] is None
    assert value['solver_calls'] == 0
    assert parent.inspect().status == 'pending_unknown'
    assert not (parent._root/'hour_000_non_authoritative').exists()
    raw = m.io.encode(value);path=tmp_path/'binding.json';m.io.write_new(path,raw)
    assert m.inspect(path,expected_sha256=m.io.digest(raw),**args) == value
    altered=deepcopy(value);altered['normal_input_identity']='0'*64
    bad=m.io.encode(altered);other=tmp_path/'changed.json';m.io.write_new(other,bad)
    with pytest.raises(ValueError,match='fresh pending obligation binding differs'):
        m.inspect(other,expected_sha256=m.io.digest(bad),**args)


def test_cell_capacity_arm_change_binding_not_normal_key(context):
    parent,args,catalog,item,value = context
    point = deepcopy(value['obligation_node']['record']['payload']['coordinate'])
    axes=catalog['axes']['training_ub']
    # Full declared coordinate changes are controller bookkeeping only.
    for name,index in [('theta',1),('alpha',1),('arm',3),('capacity',100)]:
        changed=dict(point,**{name:axes[name][index]})
        ordinal=args['resolver'].encode_coordinate('training_ub',changed)
        node=m.precheck(args['resolver'],args['declaration'],family='training_ub',ordinal=ordinal,relative_hour=0)
        assert node['node_id'] != value['obligation_node']['node_id']
    variant=dict(point,theta=axes['theta'][1],alpha=axes['alpha'][1],arm='joint-B6',capacity='1')
    ordinal=args['resolver'].encode_coordinate('training_ub',variant)
    new=m.bind(**dict(args,ordinal=ordinal))
    assert new['normal_request_key'] == value['normal_request_key']
    assert new['normal_input_identity'] == value['normal_input_identity']
    assert new['obligation_binding_id'] != value['obligation_binding_id']
    assert new['proposed_job_budget_sha256'] == value['proposed_job_budget_sha256']
    assert new['source_parent_lineage'] == value['source_parent_lineage']
    assert new['role'] == 'normal_environment_prerequisite_for_B6_planning'


def test_budget_alone_changes_binding_not_normal_key(context):
    _,args,_,_,value=context
    new=m.bind(**dict(args,job_budget=replace(args['job_budget'],max_elapsed_seconds=299)))
    assert new['normal_request_key'] == value['normal_request_key']
    assert new['normal_input_identity'] == value['normal_input_identity']
    assert new['obligation_node'] == value['obligation_node']
    assert new['source_parent_lineage'] == value['source_parent_lineage']
    assert new['proposed_job_budget_sha256'] != value['proposed_job_budget_sha256']
    assert new['obligation_binding_id'] != value['obligation_binding_id']


@pytest.mark.parametrize('family',['training_lb','holdout','training_b6_actual',True])
def test_wrong_family_rejected_before_source_reads(context,monkeypatch,family):
    _,args,_,_,_=context
    monkeypatch.setattr(m,'_views',lambda:pytest.fail('static error reached source verification'))
    with pytest.raises(ValueError,match='training UB'):m.bind(**dict(args,family=family))


@pytest.mark.parametrize('hour',[True,-1,192,193,1.0])
def test_invalid_episode_hour_is_rejected(context,hour):
    _,args,_,_,_=context
    with pytest.raises(ValueError,match='finite episode hour'):m.bind(**dict(args,relative_hour=hour))


@pytest.mark.parametrize('field,value',[('split','holdout'),('power_raw_hour',193),('workload_raw_hour',409),
    ('outage_seed',20260823),('config_sha256','1'*64)])
def test_origin_mismatch_and_raw_plus_one_confusion(context,field,value):
    _,args,_,_,_=context
    declaration=deepcopy(args['declaration']);declaration['origin'][field]=value
    with pytest.raises(ValueError,match='parent origin'):m.bind(**dict(args,declaration=declaration))


def test_excluded_cell_and_forged_resolver_rejected(context):
    _,args,catalog,_,value=context
    point=deepcopy(value['obligation_node']['record']['payload']['coordinate'])
    point.update(alpha='1',arm='CFE-only')
    ordinal=args['resolver'].encode_coordinate('training_ub',point)
    with pytest.raises(ValueError,match='cell proof'):m.bind(**dict(args,ordinal=ordinal))
    with pytest.raises(ValueError,match='manifest snapshot'):m.bind(**dict(args,resolver=args['resolver'].data()))


@pytest.mark.parametrize('bad',['head','anchor','receipt','relative_hour'])
def test_pending_join_rejects_external_identity_or_clock_mismatch(context,bad):
    _,args,_,_,_=context
    changes={}
    if bad=='head':changes['pending_arguments']=dict(args['pending_arguments'],expected_head='1'*64)
    elif bad=='anchor':changes['expected_anchor_record']='1'*64
    elif bad=='receipt':changes['expected_pending_receipt_sha256']='1'*64
    else:changes['relative_hour']=1
    with pytest.raises(ValueError):m.bind(**dict(args,**changes))


def test_existing_receipt_rejects_before_spec_limits_and_source_changes(context):
    _,args,_,item,_=context
    for field in ('before_identity','request_key','packet_audit_identity'):
        record=json.loads(item.receipt);record[field]='1'*64
        with pytest.raises(ValueError):replace(item,receipt=m.io.encode(record))
    record=json.loads(item.receipt);record['source_lineage_identity']='1'*64
    forged=replace(item,receipt=m.io.encode(record))
    with pytest.raises(ValueError):forged.validate(expected_receipt_sha256=item.receipt_sha256)
    with pytest.raises(ValueError):replace(item,specification=replace(item.specification,time_limit_seconds=4.))
    with pytest.raises(ValueError):replace(item,limits=replace(item.limits,max_constraints=1273))


def test_late_binding_implementation_drift_rejected(context,monkeypatch):
    _,args,_,_,_=context
    original_open,original_read=m.snapshot.open_snapshot,m.io.read_stable
    def open_reader(*a,**k):
        owner=original_open(*a,**k);original_pending=owner.pending_input;calls=0
        def pending(**kw):
            nonlocal calls
            result=original_pending(**kw);calls+=1
            if calls==2:
                def changed(path,cap):
                    raw,stamp=original_read(path,cap)
                    return (raw+b' ',stamp) if path==Path(m.__file__) else (raw,stamp)
                monkeypatch.setattr(m.io,'read_stable',changed)
            return result
        owner.pending_input=pending
        return owner
    monkeypatch.setattr(m.snapshot,'open_snapshot',open_reader)
    with pytest.raises(ValueError,match='binding evidence changed'):m.bind(**args)


@pytest.mark.parametrize('hour,phase',[(0,'enrollment'),(167,'enrollment'),(168,'followup'),(191,'followup')])
def test_phase_keeps_exact_catalog_node_and_enrollment_window(context,monkeypatch,hour,phase):
    _,args,_,_,value=context
    node=m.precheck(args['resolver'],args['declaration'],family='training_ub',ordinal=args['ordinal'],relative_hour=hour)
    assert node==value['obligation_node'] and m.phase(hour)==phase
    seen=[];load=m.source_binding.windows.load_source_window
    def observe(*a,**kw):
        seen.append(a[:4]);return load(*a,**kw)
    monkeypatch.setattr(m.source_binding.windows,'load_source_window',observe)
    proof=m.prevalidate_enrollment(args['resolver'],args['declaration'],family='training_ub',ordinal=args['ordinal'],relative_hour=hour)
    assert seen==[('power','training',192,168),('workload','training',408,168)]
    assert proof==value['enrollment_prevalidation']


@pytest.mark.parametrize('hours',[168,191,193,True])
def test_existing_or_wrong_horizon_cannot_be_extended(context,monkeypatch,hours):
    _,args,_,_,_=context
    monkeypatch.setattr(m,'_views',lambda:pytest.fail('bad horizon reached source join'))
    with pytest.raises(ValueError):m.bind(**dict(args,declaration=dict(args['declaration'],hours=hours)))


@pytest.fixture
def tail_pending(tmp_path,context):
    parent,args,catalog,item=prepare(tmp_path/'independent_tail_parent_non_authoritative',context[1]['resolver'])
    try:yield parent,args,catalog,item
    finally:parent.close()


@pytest.mark.parametrize('hour',[167,168,191])
def test_tail_binding_with_explicit_synthetic_pending_seam_and_real_current_rows(tail_pending,monkeypatch,hour):
    """No accepted 192h prefix claimed: replace only the pending N snapshot seam."""
    from types import SimpleNamespace
    parent,args,_,original=tail_pending
    d=args['declaration'];origin=m.source_binding.H1SourceDeclaration('training',192+hour,408+hour,20260822,m.SOURCE_CONFIG_PIN)
    observed=m.source_binding.load_pinned_current(origin,d['upstream_root'],config_path=d['config_path'])
    key=m.io.digest(m.io.encode(['explicit_test_pending_seam',hour]))
    packet=SimpleNamespace(relative_hour=hour,inputs=original.packet.inputs,input_identity=original.packet.input_identity)
    receipt=m.io.encode(dict(source_lineage_identity=observed.identity,request_key=key,test_only_pending_seam=True))
    pin=m.io.digest(receipt);calls=[]
    def validate(*,expected_receipt_sha256):assert expected_receipt_sha256==pin
    item=SimpleNamespace(packet=packet,specification=original.specification,limits=original.limits,
        receipt=receipt,receipt_sha256=pin,validate=validate)
    class Reader:
        def pending_input(self,**kw):calls.append('pending');return item
        def _check(self):calls.append('check')
        def close(self):calls.append('close')
    with monkeypatch.context() as patch:
        patch.setattr(m.snapshot,'open_snapshot',lambda *a,**k:Reader())
        patch.setattr(m.replay,'request_key',lambda *a:key)
        result=m.bind(**dict(args,relative_hour=hour,expected_pending_receipt_sha256=pin))
    assert result['phase']==('enrollment' if hour==167 else 'followup')
    assert result['relative_hour']==hour and result['raw_source_hours']==dict(power=192+hour,workload=408+hour)
    assert result['obligation_node']==m.precheck(args['resolver'],d,family='training_ub',ordinal=args['ordinal'],relative_hour=0)
    assert result['source_parent_lineage']['parent_declaration']==d
    assert result['enrollment_prevalidation']['hours']==168
    assert result['proposed_job_budget']==m.asdict(args['job_budget'])
    assert all(result[k] is False for k in m.FLAGS)
    assert calls==['pending','pending','check','close'] and parent.inspect().completed_hours==0
