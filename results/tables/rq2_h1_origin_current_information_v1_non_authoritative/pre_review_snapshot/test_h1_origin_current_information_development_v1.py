from copy import copy,deepcopy
from dataclasses import asdict,replace
from datetime import timedelta
import json
import pickle

import pytest

from experiments import h1_origin_current_information_development_v1 as m
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_continuous_grid_normal_v1 import fixture


@pytest.fixture
def scenario(supplied,monkeypatch):
    root,config,initial,state=supplied
    state['data']=fixture(4).data
    observations={0:None,1:('one','generator','G1'),2:('one','generator','G1'),3:None}
    load_single=m.source.windows.load_source_window
    def load(kind,split,start,hours,**kwargs):
        v=load_single(kind,split,start,hours,**kwargs)
        if kind=='power':
            eid,typ,uid=observations[start] or ('','','')
            v['rows'][0].update(block_id='a',active_event_id=eid,active_component_type=typ,active_component_uid=uid)
        v.pop('window_identity');v['window_identity']=m.registry.old.source._hash(v)
        return v
    monkeypatch.setattr(m.source.windows,'load_source_window',load)
    manifest=load('power',initial.split,0,1,outage_seed=initial.outage_seed,
        expected_config_sha256=initial.config_sha256)['package_manifest_sha256']
    monkeypatch.setattr(m.registry.frozen,'PACKAGE_SHA',manifest)
    monkeypatch.setattr(m.registry.catalog,'CONFIG_SHA',initial.config_sha256)
    protocol=m.registry.events.DisclosureProtocol((m.registry.events.OutageComponent('generator','G1'),),
        'current_n1_outage_overlay_revealed_before_current_action',
        'complete_current_n1_outage_overlay__no_hidden_same_hour_replacement','mechanism_assumption')
    def registry_load(split):
        rows={h:load('power',split,h,1,outage_seed=initial.outage_seed,
            expected_config_sha256=initial.config_sha256)['rows'][0] for h in observations}
        return dict(split=split,protocol=protocol,caps={'G1':m.physical.Q(20)},components=(),
            rows={initial.outage_seed:rows},catalog_entries=[dict(source_start=s,observed_end_inclusive=3,
                outage_seed=initial.outage_seed,chain_id=f'power:{split}:outage_seed={initial.outage_seed}') for s in (0,1)],
            gaps=[dict(split=split,outage_seed=initial.outage_seed,raw_start=0)],identity='c'*64,
            split_hour=99,archive_member_sha256='d'*64,cap_table_sha256='e'*64)
    monkeypatch.setattr(m.registry,'_load',registry_load)
    monkeypatch.setattr(m.registry.frozen,'prefix_overlay',lambda components,seed,hour: (observations[0] or ('','',''),))
    normal_calls=[]
    def build(hours=1,start=0):
        origin=replace(initial,power_raw_hour=start)
        before=None
        for h in range(hours):
            d=replace(origin,power_raw_hour=start+h,workload_raw_hour=h)
            obs=m.source.load_pinned_current(d,root,config_path=config)
            packet=m.source.h1.assemble_current_normal(obs.network,obs.row,obs.raw_workload,
                relative_hour=h,dc_bus=1,source_time_basis=obs.source_time_basis,before=before)
            after=m.normal.source._owned(m.normal.source.H1NormalBoundary,
                network_identity=packet.network.identity,completed_hours=h+1,
                units=(('G1',True,20.,h+1),),evidence_role='numerical_lex_candidate')
            before=after
        decision=m.normal._decision(packet,after)
        audit=dict(parent_declaration=dict(origin=asdict(origin),config_path=str(config),upstream_root=str(root),dc_bus=1),
            decision_identity=decision.decision_identity,normal_before=asdict(packet.before),normal_after=asdict(after),
            normal_input_identity=packet.input_identity,source_timestamp=packet.source_timestamp,source_time_basis=packet.source_time_basis)
        env=m.normal._owned(m.normal.H1NormalAuditEnvelope,decision=decision,audit_payload=m.io.encode(audit))
        normal_calls.clear()
        def replay(root_,**kwargs):
            assert root_==root and kwargs['completed_hours']==hours
            normal_calls.append(kwargs)
            return env
        monkeypatch.setattr(m.normal,'prepare',replay)
        return env,dict(expected_binding_sha256='a'*64,expected_terminal_sha256='b'*64,
            completed_hours=hours,expected_registry_identity='c'*64)
    return root,state,observations,build,normal_calls


def test_first_action_join_is_current_only_and_noncopyable(scenario):
    root,_,_,build,calls=scenario;env,args=build()
    value=m.prepare(root,**args)
    assert len(calls)==2 and value.chronology_origin
    assert type(value.source_action) is m.registry.FirstAction
    assert value.frame.info.decision_bytes==env.decision.decision_bytes
    assert value.frame.normal_before.completed_hours==0 and value.frame.normal_after.completed_hours==1
    assert set(json.loads(value.decision.decision_bytes))=={'normal','outage'}
    for hidden in (b'raw_start',b'origin_kind',b'timestamp',b'outage_seed',b'event_id',b'rows',b'actions'):
        assert hidden not in value.decision.decision_bytes
    for copier in (copy,deepcopy,pickle.dumps):
        with pytest.raises(TypeError):copier(value)
    audit=json.loads(value.audit_payload)
    assert audit['current_source_correspondence_checked'] and audit['registry_action_and_cap_lookup_checked']
    for key in ('accepted_root_integration_verified','detached_consumer_authenticated','persistent_lane_owner_implemented',
                'common_publication_verified','full_192_hour_execution_verified','resource_admission',
                'formal_execution_ready','formal_result','native_execution_authorized'):
        assert audit[key] is False


@pytest.mark.parametrize('hours,start,expected',[(2,0,1),(3,0,2),(4,0,3),(1,1,1),(3,1,3)])
def test_current_action_tracks_N_progress_and_registry_cap(scenario,hours,start,expected):
    root,_,_,build,_=scenario;_,args=build(hours,start)
    value=m.prepare(root,**args)
    assert type(value.source_action) is m.registry.TransitionAction
    assert value.source_action.step.after.source_hour==expected
    assert value.source_action.relative_hour==hours-1
    if start+hours-1==3:
        assert value.source_action.step.repaired_generator_return_limit_mw==20.
        assert json.loads(value.decision.outage_payload)['repair_cap_exact']==['20','1']


def test_initial_down_is_not_a_trip_and_normal_bytes_unchanged(scenario):
    root,_,observations,build,_=scenario
    observations[0]=('incoming','generator','G1')
    env,args=build();v=m.prepare(root,**args)
    assert v.source_origin.active.observed_start_hour is None
    view=json.loads(v.decision.outage_payload)
    assert view['active']['uid']=='G1' and view['started'] is None and view['repair_cap_exact'] is None
    assert v.decision.normal.decision_bytes==env.decision.decision_bytes


def test_future_and_audit_clock_labels_do_not_affect_decision(scenario):
    root,state,observations,build,_=scenario;_,args=build(hours=2)
    first=m.prepare(root,**args)
    observations[2]=('future','bad','bad');observations[3]=('future2','bad','bad')
    assert m.prepare(root,**args).decision.decision_bytes==first.decision.decision_bytes
    observations[1]=('renamed','generator','G1')
    state['data']=replace(state['data'],hourly_points=tuple(replace(r,timestamp=r.timestamp+timedelta(days=5)) for r in state['data'].hourly_points))
    _,args=build(hours=2);second=m.prepare(root,**args)
    assert second.decision.decision_bytes==first.decision.decision_bytes and second.audit_identity!=first.audit_identity


@pytest.mark.parametrize('hours',[0,169,192,True,1.0])
def test_followup_cannot_be_created_by_relaxing_enrollment_limit(scenario,hours):
    root,_,_,build,calls=scenario;_,args=build()
    with pytest.raises(ValueError,match='progress'):m.prepare(root,**dict(args,completed_hours=hours))
    assert not calls


@pytest.mark.parametrize('field',['raw_start','outage_seed','split','hours','last_revealed_raw_hour','registry_identity'])
def test_spliced_registry_lineage_rejected(scenario,monkeypatch,field):
    root,_,_,build,_=scenario;_,args=build()
    original=m.registry.prepare
    def corrupt(**kwargs):
        p=original(**kwargs);p.audit[field]='changed';return p
    monkeypatch.setattr(m.registry,'prepare',corrupt)
    with pytest.raises(ValueError):m.prepare(root,**args)


def test_current_raw_row_mismatch_rejected(scenario,monkeypatch):
    root,_,_,build,_=scenario;_,args=build()
    original=m.registry.prepare
    def corrupt(**kwargs):
        p=original(**kwargs);p.audit['current_rows'][-1]['system_load_mw']='99';return p
    monkeypatch.setattr(m.registry,'prepare',corrupt)
    with pytest.raises(ValueError,match='raw current power'):m.prepare(root,**args)


@pytest.mark.parametrize('kind',['normal','registry','implementation','observation'])
def test_return_rechecks_all_owned_inputs(scenario,monkeypatch,kind):
    root,_,_,build,_=scenario;_,args=build()
    if kind=='normal':
        original=m.normal.prepare;count=[]
        def changed(*a,**kw):
            e=original(*a,**kw);count.append(1)
            return e if len(count)==1 else m.normal._owned(type(e),decision=e.decision,audit_payload=e.audit_payload+b' ')
        monkeypatch.setattr(m.normal,'prepare',changed)
    elif kind=='registry':
        original=m.registry.prepare;count=[]
        def changed(**kw):
            p=original(**kw);count.append(1)
            if len(count)>1:p.audit['changed']=True
            return p
        monkeypatch.setattr(m.registry,'prepare',changed)
    elif kind=='implementation':
        values=iter(('a'*64,'b'*64));monkeypatch.setattr(m,'implementation_identity',lambda:next(values))
    else:
        def changed(*a,**kw):raise ValueError('observation drift')
        monkeypatch.setattr(m.source,'validate_pinned_current',changed)
    with pytest.raises(ValueError,match='changed|drift'):m.prepare(root,**args)


def test_no_external_mode_cap_or_coordinates(scenario):
    root,_,_,build,_=scenario;_,args=build()
    for extra in ({'chronology_origin':False},{'repair_limits':(100.,)},{'raw_start':1}):
        with pytest.raises(TypeError):m.prepare(root,**args,**extra)
