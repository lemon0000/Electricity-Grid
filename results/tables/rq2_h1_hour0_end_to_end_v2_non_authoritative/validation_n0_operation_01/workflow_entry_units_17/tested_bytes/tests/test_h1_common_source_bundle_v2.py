"""Bundle projection parity over explicit fake historical prefixes; no Jobs."""
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from tests.test_h1_phase_exact_source_current_development_v2 import inputs,scenario,supplied,load
from experiments import h1_historical_n0_verifier_development_v1 as verifier


@pytest.fixture
def complete(inputs,monkeypatch):
    root,args,calls,captured,proof,observation=inputs
    proof.update(parent_head='d'*64,evidence_identity='e'*64)
    payload=verifier.io.encode(dict(value=dict(canonical_locks=['synthetic-lock'])))
    captured.update(count=3,result=SimpleNamespace(head='a'*64,archive_identity='b'*64,
        projection=SimpleNamespace(payload=payload,projection_identity='c'*64)))
    from tests.test_rq2_normal_h1_hour_archive_v1 import spec,LIMITS
    original=verifier._replay_prefix
    def replay(*a,**kw):
        proof,value,header=original(*a,**kw)
        declaration=dict(header['parent_declaration'],specification=asdict(spec()),limits=asdict(LIMITS))
        return proof,value,dict(header,parent_declaration=declaration)
    monkeypatch.setattr(verifier,'_replay_prefix',replay)
    return inputs


def test_bundle_matches_independent_historical_and_exact_projections(complete,monkeypatch):
    root,args,calls,*_=complete
    module=load(monkeypatch)
    historical_args={k:v for k,v in args.items() if k!='expected_registry_identity'}
    decision,audit=verifier._projection(root,**historical_args)
    assert len(calls)==2;calls.clear()
    current=module.prepare(root,**args)
    assert len(calls)==2;calls.clear()
    bundle=module.prepare_common_bundle(root,**args)
    assert len(calls)==2 and calls[0] is calls[1]
    assert type(bundle) is module.CommonSourceBundle
    assert type(bundle) is not verifier.VerifiedHistoricalEnvelope
    assert bundle.audit_payload==audit and bundle.decision.decision_bytes==decision.decision_bytes
    assert bundle.current.source_projection_audit_payload==current.source_projection_audit_payload
    assert bundle.current.exogenous_scientific_payload==current.exogenous_scientific_payload
    assert bundle.current.prepared_current.decision.decision_bytes==current.prepared_current.decision.decision_bytes
    assert asdict(bundle.current.prepared_current.frame)==asdict(current.prepared_current.frame)
    assert bundle.current.prepared_current.source_action==current.prepared_current.source_action
    execution=json.loads(bundle.verification_execution_payload)
    assert execution['full_numerical_hour_replays']==execution['fresh_byte_context_revalidations']==4
    assert execution['projection_consumers']==['historical','exact_source']
    assert execution['active_implementation_identity']==module.implementation_identity()
    assert execution['historical_projection_sha256']==module.io.digest(audit)
    assert execution['exact_source_audit_sha256']==module.io.digest(current.source_projection_audit_payload)
    assert not execution['cross_call_reuse'] and not execution['formal_result']


@pytest.mark.parametrize('target',['request_key','specification','limits','prepare','prepare_common_bundle'])
def test_bundle_rejects_replaced_dependency_before_prefix(complete,monkeypatch,target):
    root,args,calls,*_=complete
    module=load(monkeypatch)
    owner,name={
        'request_key':(verifier.binding.replay,'request_key'),
        'specification':(verifier.history.prior,'Rq2SolverSpec'),
        'limits':(verifier.history.replay,'H1HourReplayLimits'),
        'prepare':(module,'prepare'),
        'prepare_common_bundle':(module,'prepare_common_bundle')}[target]
    entry=module.prepare if target=='prepare_common_bundle' else module.prepare_common_bundle
    monkeypatch.setattr(owner,name,lambda *a,**kw:None)
    with pytest.raises(ValueError,match='dispatch changed'):entry(root,**args)
    assert not calls


@pytest.mark.parametrize('target',['spec_init','limits_init','limits_post','asdict','request_code'])
def test_bundle_rejects_same_class_method_or_projection_helper_drift(complete,monkeypatch,target):
    root,args,calls,*_=complete
    module=load(monkeypatch)
    owner,name={'spec_init':(verifier.history.prior.Rq2SolverSpec,'__init__'),
        'limits_init':(verifier.history.replay.H1HourReplayLimits,'__init__'),
        'limits_post':(verifier.history.replay.H1HourReplayLimits,'__post_init__'),
        'asdict':(module,'asdict'),
        'request_code':(verifier.binding.replay.request_key,'__code__')}[target]
    replacement=lambda *a,**kw:None
    monkeypatch.setattr(owner,name,replacement.__code__ if target=='request_code' else replacement)
    with pytest.raises(ValueError,match='dispatch changed'):module.prepare_common_bundle(root,**args)
    assert not calls


@pytest.mark.parametrize('boundary',['second_prefix','registry_second','validate','final_observe'])
def test_bundle_retains_original_failure_boundaries(complete,monkeypatch,boundary):
    root,args,calls,*_=complete
    # Use the actual exact-source aliases; fixtures install these seams before guard capture.
    from experiments import h1_phase_exact_source_current_development_v2 as source
    owner,name={'second_prefix':(verifier,'_replay_prefix'),
        'registry_second':(source.registry,'prepare'),
        'validate':(source.source,'validate_pinned_current'),
        'final_observe':(verifier,'_observe_sources')}[boundary]
    original=getattr(owner,name);seen=[]
    def fault(*a,**kw):
        seen.append(1)
        if len(seen)==(2 if boundary in ('second_prefix','registry_second') else 1):
            raise RuntimeError('injected boundary failure')
        return original(*a,**kw)
    monkeypatch.setattr(owner,name,fault)
    module=load(monkeypatch)
    with pytest.raises(RuntimeError,match='injected boundary'):module.prepare_common_bundle(root,**args)
    assert len(seen)==(2 if boundary in ('second_prefix','registry_second') else 1)


@pytest.fixture
def common_case(complete,monkeypatch):
    root,args,calls,*_=complete
    source=load(monkeypatch)
    bundle=source.prepare_common_bundle(root,**args)
    audit=json.loads(bundle.audit_payload)
    reference=dict(local_terminal=dict(body=dict(
        controller_root=str(root),controller_binding_sha256=args['expected_binding_sha256'],
        controller_terminal_sha256=args['expected_terminal_sha256'],
        historical_verifier_identity=verifier.verifier_identity(),historical_verifier_schema=verifier.VERIFIER_SCHEMA,
        full_numerical_hour_replays=4,fresh_byte_context_revalidations=4,recomputed_on_revalidation=False,
        audit_payload_sha256=source.io.digest(bundle.audit_payload),historical_implementation=audit['implementation'],
        **{k:audit[k] for k in ('decision_identity','normal_request_key','child_head','child_archive_identity',
                              'projection_identity','projection_payload_sha256')},
        **{k:audit['historical_controller'][k] for k in ('parent_head','evidence_identity')})))
    from experiments import h1_phase_owner_development_v2 as phase
    seen=[]
    def prepared(*a,**kw):seen.append((a,kw));return bundle
    monkeypatch.setattr(source,'prepare_common_bundle',prepared)
    monkeypatch.setattr(phase,'source',source)
    monkeypatch.setattr(phase,'_initial',lambda *a:SimpleNamespace(scientific={'synthetic_state':True}))
    monkeypatch.setattr(phase,'_request',lambda *a:{'synthetic_request':True})
    name='experiments.common_bundle_routing_test_alias'
    spec=importlib.util.spec_from_file_location(name,Path(phase.__file__).with_name('h1_group_n0_common_input_binding_development_v2.py'))
    common=importlib.util.module_from_spec(spec);monkeypatch.setitem(sys.modules,name,common);spec.loader.exec_module(common)
    return common,reference,args['expected_registry_identity'],seen


def test_common_arm_consumes_one_fresh_bundle_each_time(common_case):
    common,ref,registry,seen=common_case
    first=common._arm(ref,registry,None);second=common._arm(ref,registry,None)
    assert len(seen)==2 and first==second
    assert first[2]['verification_execution']['projection_consumers']==['historical','exact_source']
    assert all(kw['completed_hours']==1 for _,kw in seen)


@pytest.mark.parametrize('field,value',[
    ('historical_verifier_identity','f'*64),('historical_verifier_schema','foreign'),
    ('full_numerical_hour_replays',3),('fresh_byte_context_revalidations',3),
    ('recomputed_on_revalidation',True),('audit_payload_sha256','f'*64),('decision_identity','f'*64)])
def test_common_bundle_retained_contract_drift_rejected(common_case,field,value):
    common,ref,registry,seen=common_case
    ref['local_terminal']['body'][field]=value
    with pytest.raises(ValueError):common._arm(ref,registry,None)
    assert len(seen)==1


def test_common_bundle_route_replaced_before_effect_rejected(common_case,monkeypatch):
    common,ref,registry,seen=common_case
    monkeypatch.setattr(common.phase.source,'prepare_common_bundle',lambda *a,**kw:None)
    with pytest.raises(ValueError,match='bundle route changed'):common._arm(ref,registry,None)
    assert not seen
