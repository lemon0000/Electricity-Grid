"""Fallback protocol cases; promoted to tests after the active saved diagnostic."""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import h1_bootstrap_integration_development_v3 as bootstrap
from tests.test_h1_bootstrap_n0_operation_development_v3 import case,protocol,inner


def cells(function):return dict(zip(function.__code__.co_freevars,(c.cell_contents for c in function.__closure__)))


def test_reconcile_uses_full_fallback_and_preserves_retained_body(case):
    p=protocol(case);owner=p.owner
    try:
        body=owner._build_N0_terminal(n0_operation=None,n0_site='seed')
        local_head=sha256(bootstrap.encode(body)).hexdigest();owner._bootstrap.saved.append((local_head,body))
        preserved=bootstrap.encode(owner._bootstrap.saved)
        original_registry=owner._registry;claim=cells(original_registry)['claim']
        def registry(*,n0_operation=None,n0_site=None):
            assert n0_operation is None
            owner._build_N0_terminal(n0_operation=None,n0_site=n0_site or 'fallback_registry')
            return {owner._slot['slot_id']:dict(claim=('a'*64,claim),release=('b'*64,{}))}
        def replay(*,n0_operation=None):
            assert n0_operation is None
            if len(owner._global.saved)==2:return 'local_N_terminal_uncommitted'
            registry(n0_site='registry_before');registry(n0_site='registry_after')
            return 'pending_post_N'
        owner._registry=registry;owner._replay=replay
        finish=cells(p.run)['finish'];result=finish(owner,create_local=False)
        assert result['state']=='pending_post_N' and 'N0_validation_execution_receipt' not in result
        assert bootstrap.encode(owner._bootstrap.saved)==preserved and not p.operations
        assert p.events==['seed','fallback_registry',*case.m.BUILD_SITES]
        assert len(case.calls)==4*len(p.events) and len(case.contexts)==16*len(p.events)
        assert len(owner._global.saved)==3
    finally:owner._operation.release()


@dataclass(frozen=True)
class Declaration:
    study_root:str
    ordinal:int=0
    family:str='training_ub'
    max_record_bytes:int=65536


def test_actual_registry_only_current_slot_receives_operation(tmp_path,monkeypatch):
    raw=inner(bootstrap.BootstrapOwner._registry)
    slots=('a'*64,'b'*64);heads=('c'*64,'d'*64);views={};rows=[];proposals={};seen=[]
    declaration=Declaration(str(tmp_path))
    def candidate(d):return None
    def episode(d,slot,roots,candidate):return {}
    def proposal(d,slot,roots,genesis,candidate):return proposals[d.ordinal]
    for ordinal,slot in enumerate(slots):
        root=tmp_path/'episodes'/slot
        roots={name:str(root/(name+'_non_authoritative')) for name in ('bootstrap','controller','owner','holder')}
        header=bootstrap._journal_header(roots['bootstrap'],{},8,65536,'e'*64)
        genesis=sha256(header).hexdigest()
        value=dict(study={},family='training_ub',ordinal=ordinal,slot_id=slot,profile={},roots=roots,
            bootstrap_genesis=genesis,phase_manifest_audit_identity='f'*64)
        proposals[ordinal]=value
        attempt=bootstrap.encode(dict(sequence=1,previous=genesis,
            body=dict(kind='attempt',proposal=value,claim_proposal_id=bootstrap.digest(value))))
        claim=dict(kind='claim',slot_id=slot,proposal=value,claim_proposal_id=bootstrap.digest(value),
            bootstrap_attempt_head=sha256(attempt).hexdigest())
        rows.append((heads[ordinal],claim))
        for name,blob in (('header.json',header),('00000000000000000001.json',attempt)):
            views[Path(roots['bootstrap'])/name]=(blob,('unit-only-view',))
        rows.append(('f'*64,dict(kind='release_intent',slot_id=slot,claim_head=heads[ordinal],
            claim_proposal_id=claim['claim_proposal_id'],bootstrap_release_head='1'*64,
            bootstrap_release_body_sha256='2'*64,controller_ready_head='3'*64,**bootstrap.FLAGS)))
    manifest=SimpleNamespace(resolve=lambda family,hour:dict(kind='potential_N_slot',slot_id=slots[hour//192]),
        obligation=lambda family,ordinal:dict(obligation_node=dict(record=dict(payload=dict(obligation_sha256=slots[ordinal])))))
    def release(claim_head,claim,*maps):
        return '1'*64,('3'*64,dict(parent_declaration={})), '2'*64,('4'*64,dict(slot=claim['slot_id']))
    operation=object()
    def build(claim_head,claim,*args,n0_operation=None,n0_site=None):
        seen.append((claim['slot_id'],n0_operation,n0_site));return dict(slot=claim['slot_id'])
    owner=SimpleNamespace(declaration=declaration,_manifest=manifest,_implementation='e'*64,
        _global=SimpleNamespace(rows=lambda:rows),_slot=dict(slot_id=slots[0]),_phase_candidate=candidate,
        _episode_declaration=episode,_proposal_for=proposal,_release_cross_reference=release,
        _build_N0_terminal=build,_check=lambda:None,_observe_N0=lambda *a:None)
    monkeypatch.setattr(bootstrap.storage,'_read',lambda path,cap:views[path])
    state=raw(owner,n0_operation=operation,n0_site='registry_before')
    assert tuple(state)==slots
    assert seen==[(slots[0],operation,'registry_before'),(slots[1],None,'registry_before')]
