"""Bundle projection parity over explicit fake historical prefixes; no Jobs."""
from dataclasses import asdict
import json
from types import SimpleNamespace

import pytest

from tests.test_h1_phase_exact_source_current_development_v2 import inputs,scenario,supplied,load
from experiments import h1_historical_n0_verifier_development_v1 as verifier


@pytest.fixture
def complete(inputs):
    root,args,calls,captured,proof,observation=inputs
    payload=verifier.io.encode(dict(value=dict(canonical_locks=['synthetic-lock'])))
    captured.update(count=3,result=SimpleNamespace(head='a'*64,archive_identity='b'*64,
        projection=SimpleNamespace(payload=payload,projection_identity='c'*64)))
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
