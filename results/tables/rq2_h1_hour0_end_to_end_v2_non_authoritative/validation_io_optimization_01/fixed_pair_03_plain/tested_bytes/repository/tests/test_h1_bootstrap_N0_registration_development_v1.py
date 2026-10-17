"""Journal protocol faults with explicit fake numerical evidence; zero Jobs.

The separate numerical registration test exercises the real evidence builder.
These tests isolate retention/replay/reconciliation, not numerical acceptance.
"""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from tests.test_h1_bootstrap_integration_development_v1 import (
    m, example, setup, enable_post_claim, retained,
)


@pytest.fixture
def protocol(setup,monkeypatch):
    s=setup;declaration,_=enable_post_claim(s,monkeypatch)
    metadata=m.BootstrapOwner._continue_bootstrap
    def observe(owner,root,declaration,observed):
        observed.setdefault('test_only_fake_numerical_evidence','0'*64)
    def build(owner,claim_head,claim,release_head,ready_row,local_release_head,observed,check):
        check();observe(owner,None,None,observed);check()
        pins={key:'0'*64 for key in m.N0_PINS}
        pins.update(slot_id=claim['slot_id'],claim_head=claim_head,claim_proposal_id=claim['claim_proposal_id'],
            global_release_head=release_head,bootstrap_release_head=local_release_head,
            controller_ready_head=ready_row[0],exact_n0_topology_identity=m.digest(observed))
        return m._N0_body(claim['proposal']['roots']['controller'],pins)
    def continue_(owner):
        try:metadata(owner)
        except ValueError as error:
            if str(error)!='bootstrap release/capability entry not implemented; controller genesis retained':raise
        else:raise AssertionError('metadata stop expected')
        owner._record_release()
        return owner._finish_N0_terminal(create_local=True)
    monkeypatch.setattr(m.BootstrapOwner,'_observe_N0',observe)
    monkeypatch.setattr(m.BootstrapOwner,'_build_N0_terminal',build)
    monkeypatch.setattr(m.BootstrapOwner,'_continue_bootstrap',continue_)
    return s,declaration


def test_terminal_protocol_commit_foreign_replay_and_capacity(protocol):
    s,d=protocol;o=s.open(declaration=d)
    try:
        bounds=o._N0_record_sizes();result=o.bootstrap()
        assert result['state']=='pending_post_N'
        assert o.inspect()['N0_numerical_evidence_audited']
        assert o._remaining_global_records()==0
        assert len(o._bootstrap.rows())==5 and len(o._global.rows())==3
        local=o._bootstrap.root/'00000000000000000005.json'
        global_=o._global.root/'00000000000000000003.json'
        assert local.stat().st_size==bounds[0] and global_.stat().st_size<=bounds[1]
        assert all(result[k] is False for k in m.FLAGS)
        heads=retained(o,s)
    finally:o.close()
    other=s.open(create=True,create_study=False,declaration=replace(d,ordinal=1),global_head=heads['global_head'])
    try:
        assert other.inspect()['state']=='new'
        registry=other._registry()
        assert len(registry)==1 and next(iter(registry.values()))['terminal'] is not None
        assert other._remaining_global_records()==0
    finally:other.close()


@pytest.mark.parametrize('where',['local_before','local_after','global_before','global_after'])
def test_terminal_unknown_writes_and_retained_recovery(protocol,monkeypatch,where):
    s,d=protocol
    def retain(root,before,after):
        target=o._bootstrap.root if where.startswith('local') else o._global.root
        sequence=5 if where.startswith('local') else 3
        if Path(root)==target and (target/f'{sequence:020d}.json').exists():
            if where.endswith('after'):s.retain(root,before,after)
            raise RuntimeError('injected terminal retention failure')
        return s.retain(root,before,after)
    o=m.BootstrapOwner(d,create=True,create_study=True,retain_global_head=retain,retain_bootstrap_head=retain)
    try:
        with pytest.raises(RuntimeError,match='terminal retention failure'):o.bootstrap()
        heads=retained(o,s)
        local_records=list(o._bootstrap.root.glob('[0-9]*.json'))
        assert len(local_records)==5
        assert not list(Path(o.roots['controller']).glob('job_*'))
    finally:o.close()
    if where.endswith('before'):
        with pytest.raises(ValueError,match='retained journal head'):
            s.open(create=False,create_study=False,declaration=d,**heads)
        return
    reopened=s.open(create=False,create_study=False,declaration=d,**heads)
    try:
        expected='local_N_terminal_uncommitted' if where=='local_after' else 'pending_post_N'
        assert reopened.inspect()['state']==expected
        if where=='local_after':
            local_before=[p.read_bytes() for p in sorted(local_records)]
            # The only allowed recovery effect is a global metadata append.
            def no_execution(*a,**k):raise AssertionError('N execution retried during reconciliation')
            monkeypatch.setattr(m.BootstrapOwner,'_continue_owned_development',no_execution)
            assert reopened.reconcile_N0_terminal()['state']=='pending_post_N'
            assert local_before==[p.read_bytes() for p in sorted(local_records)]
            assert reopened._remaining_global_records()==0
        with pytest.raises(ValueError,match='no automatic retry'):reopened.bootstrap()
    finally:reopened.close()


@pytest.mark.parametrize('lane',['local','global'])
def test_terminal_retainer_cannot_replace_nonce(protocol,lane):
    s,d=protocol
    def retain(root,before,after):
        result=s.retain(root,before,after)
        target=o._bootstrap.root if lane=='local' else o._global.root
        sequence=5 if lane=='local' else 3
        if Path(root)==target and (target/f'{sequence:020d}.json').exists():o._operation_nonce=object()
        return result
    o=m.BootstrapOwner(d,create=True,create_study=True,retain_global_head=retain,retain_bootstrap_head=retain)
    try:
        with pytest.raises(ValueError,match='N0 registration operation changed'):o.bootstrap()
        heads=retained(o,s)
    finally:o.close()
    reopened=s.open(create=False,create_study=False,declaration=d,**heads)
    try:
        assert reopened.inspect()['state']==('local_N_terminal_uncommitted' if lane=='local' else 'pending_post_N')
    finally:reopened.close()


@pytest.mark.parametrize('mutation',['global_digest','local_digest','unknown_seq6'])
def test_foreign_terminal_corruption_is_rejected(protocol,mutation):
    s,d=protocol;o=s.open(declaration=d)
    try:
        o.bootstrap();heads=retained(o,s);journal=o._bootstrap.root;global_=o._global.root
    finally:o.close()
    if mutation=='global_digest':
        path=global_/'00000000000000000003.json';value=json.loads(path.read_bytes())
        value['body']['bootstrap_terminal_body_sha256']='0'*64
        raw=m.encode(value);path.write_bytes(raw);heads['global_head']=m.sha256(raw).hexdigest()
    elif mutation=='local_digest':
        path=journal/'00000000000000000005.json';value=json.loads(path.read_bytes())
        value['body']['evidence_identity']='1'*64;path.write_bytes(m.encode(value))
    else:
        (journal/'00000000000000000006.json').write_bytes(m.encode(dict(sequence=6,
            previous=heads['bootstrap_head'],body={'kind':'unimplemented'})))
    with pytest.raises(ValueError):
        s.open(create=True,create_study=False,declaration=replace(d,ordinal=1),global_head=heads['global_head'])


def test_terminal_byte_gate_precedes_attempt(protocol,monkeypatch):
    s,d=protocol;o=s.open(declaration=d)
    try:
        monkeypatch.setattr(o,'_N0_record_sizes',lambda:(o._bootstrap.cap+1,1))
        with pytest.raises(ValueError,match='complete N0 terminal records exceed'):o.bootstrap()
        assert not list(o._bootstrap.root.glob('[0-9]*.json'))
        assert not list(o._global.root.glob('[0-9]*.json'))
        assert not Path(o.roots['controller']).exists()
    finally:o.close()
