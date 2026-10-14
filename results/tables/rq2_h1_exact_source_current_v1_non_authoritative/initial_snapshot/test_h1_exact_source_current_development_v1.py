from copy import copy,deepcopy
from fractions import Fraction as Q
import json
import pickle

import pytest

from experiments import h1_exact_source_current_development_v1 as m
from tests.test_h1_origin_current_information_development_v1 import scenario,supplied


def bind(scenario,monkeypatch,*,hours=1,start=0):
    root,state,_,build,_=scenario;envelope,args=build(hours,start)
    audit,declaration,_,current=m.origin_join.predecessor._coordinates(envelope,hours)
    observation=m.source.load_pinned_current(current,root,config_path=declaration['config_path'])
    before=m.origin_join.predecessor._boundary(audit['normal_before'])
    packet=m.source.h1.assemble_current_normal(observation.network,observation.row,observation.raw_workload,
        relative_hour=hours-1,dc_bus=1,source_time_basis=observation.source_time_basis,before=before)
    captured=dict(packet=packet,after=m.origin_join.predecessor._boundary(audit['normal_after']))
    proof=dict(completed_hours=hours,historical_parent_prefix_verified=True,historical_obligation_prefix_verified=True,
        historical_job_clock_prefix_verified=True,suffix_chain_verified=False)
    calls=[]
    def replay(root_,**kw):
        assert root_==root and kw['completed_hours']==hours
        observed=kw['_observed'];observed.setdefault('identities',{})
        if calls:assert observed is calls[0]
        calls.append(observed)
        return dict(proof),dict(captured),dict(parent_declaration=declaration)
    # Explicit detached integration seam: no accepted root/Job is authenticated.
    monkeypatch.setattr(m.historical,'_replay_prefix',replay)
    monkeypatch.setattr(m.historical,'_observe_sources',lambda observed,d:None)
    return root,args,calls,captured,proof,observation


def test_fresh_exact_projection_and_owned_boundary(scenario,monkeypatch):
    root,args,calls,_,_,_=bind(scenario,monkeypatch)
    value=m.prepare(root,**args)
    assert len(calls)==2 and calls[0] is calls[1]
    assert value.workload_exact==Q(1,5) and value.source_cfe_at_alpha_one_exact==Q(2,5)
    assert Q(str(value.prepared_current.frame.info.current.dc_baseline_mw))==value.workload_exact*250
    for copier in (copy,deepcopy,pickle.dumps):
        with pytest.raises(TypeError):copier(value)
    scientific=json.loads(value.exogenous_scientific_payload);audit=json.loads(value.source_projection_audit_payload)
    assert scientific['workload_exact']==['1','5']
    assert audit['exact_source_projection_checked'] and not audit['shared_observed_clock']
    for key in ('accepted_real_RTS_root_integration_verified','persistent_lane_owner_implemented',
                'formal_result','formal_execution_ready','resource_admission','native_execution_authorized'):
        assert audit[key] is False
    for hidden in (b'raw_start',b'split',b'outage_seed',b'timestamp',b'package',b'inode',b'raw_workload'):
        assert hidden not in value.exogenous_scientific_payload


@pytest.mark.parametrize('raw',['0','0.2000000000000','0.3333333333337','0.5000000000005','1'])
def test_reuses_frozen_projection_instead_of_reinterpreting_float(scenario,monkeypatch,raw):
    scenario[1]['workload']=raw
    root,args,*_=bind(scenario,monkeypatch)
    value=m.prepare(root,**args)
    projection=m.source.h1.workload_projection.project_workload_power(raw,'250',decimal_places=12)
    assert value.workload_exact==Q(*map(int,projection['projected_fraction_exact']))
    assert json.loads(value.source_projection_audit_payload)['workload_projection']==projection


@pytest.mark.parametrize('raw',['1.0000000000001','0.00000000000001'])
def test_unresolved_raw_source_is_not_clipped_or_dropped(scenario,monkeypatch,raw):
    scenario[1]['workload']=raw
    with pytest.raises(ValueError,match='unresolved H1 workload mapping'):bind(scenario,monkeypatch)


@pytest.mark.parametrize('hours,start',[(1,0),(1,1),(2,0),(3,1)])
def test_current_registry_origin_and_progress_are_preserved(scenario,monkeypatch,hours,start):
    root,args,*_=bind(scenario,monkeypatch,hours=hours,start=start)
    value=m.prepare(root,**args)
    assert value.prepared_current.decision.normal.relative_hour==hours-1
    assert value.prepared_current.source_action.relative_hour==hours-1
    assert json.loads(value.exogenous_scientific_payload)['relative_hour']==hours-1


@pytest.mark.parametrize('field',['historical_parent_prefix_verified','historical_obligation_prefix_verified',
                                   'historical_job_clock_prefix_verified'])
def test_incomplete_controller_proof_rejected(scenario,monkeypatch,field):
    root,args,_,_,proof,_=bind(scenario,monkeypatch);proof[field]=False
    with pytest.raises(ValueError,match='complete historical'):m.prepare(root,**args)


def test_registry_drift_between_reads_rejected(scenario,monkeypatch):
    root,args,*_=bind(scenario,monkeypatch)
    original=m.registry.prepare;calls=[]
    def read(**kw):
        value=original(**kw);calls.append(1)
        if len(calls)==2:raise ValueError('registry/source changed')
        return value
    monkeypatch.setattr(m.registry,'prepare',read)
    with pytest.raises(ValueError,match='registry/source changed'):m.prepare(root,**args)


def test_projection_must_match_packet_and_baseline(scenario,monkeypatch):
    root,args,_,captured,_,obs=bind(scenario,monkeypatch)
    value=m.prepare(root,**args)
    fields=dict(captured['packet'].__dict__);fields['workload_projection_payload']=b'{}'
    bad=m.source.h1._owned(type(captured['packet']),**fields)
    with pytest.raises(ValueError,match='accepted N packet'):m._project(obs,value.prepared_current.frame,bad)
