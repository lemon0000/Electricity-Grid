"""Synthetic roster/source seam, real journal, ticket holder and SQLite genesis."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from threading import Lock
from types import SimpleNamespace

import pytest

from experiments import h1_common_owner_genesis_development_v1 as m
from tests.test_h1_persistent_owner_development_v1 import setup as legacy_setup
from tests.test_h1_phase_owner_development_v1 import setup
from tests.test_h1_bootstrap_integration_development_v1 import example, setup as bootstrap_setup
from tests.test_h1_group_execution_roster_development_v1 import cached_declarations, declaration, roster


@pytest.fixture
def case(setup,tmp_path,monkeypatch):
    s=setup
    # Explicit orchestration seam; never represents accepted real group evidence.
    roster=object.__new__(m.common.roster_api.GroupRoster)
    guard=Lock();global_=SimpleNamespace(genesis='a'*64,head='a'*64,history=[])
    global_.rows=lambda:list(global_.history)
    study=tmp_path/'study';study.mkdir()
    episode=study/'episode_non_authoritative';episode.mkdir()
    roster._owner=SimpleNamespace(study_root=study,_global=global_)
    def enter():
        if not guard.acquire(False):raise ValueError('roster active')
    def check():
        if not guard.locked():raise ValueError('roster guard missing')
    monkeypatch.setattr(roster,'_enter',enter)
    monkeypatch.setattr(roster,'_leave',guard.release)
    monkeypatch.setattr(roster,'_check',check)
    report=dict(global_head=global_.head,canonical_arm='joint',
        phase_manifest_candidate=dict(audit=dict(group=dict(group_identity='b'*64))),
        arm_audits=dict(joint=dict(reference=dict(episode_root=str(episode)))),
        common_scientific_identity='c'*64)
    def prepare(r):
        assert r is roster;check()
        fresh=deepcopy(report);fresh['global_head']=global_.head
        return s.manifest,s.binding,fresh
    monkeypatch.setattr(m.common,'_prepare_locked',prepare)
    # Cache only unchanged dependency hashing. Real state and persistence checks run.
    for module in (m.bootstrap,m.common):
        pin=module.implementation_identity()
        monkeypatch.setattr(module,'implementation_identity',lambda pin=pin:pin)
    phase_pin=m.phase.implementation_identity(s.manifest)
    monkeypatch.setattr(m.phase,'implementation_identity',lambda manifest:phase_pin)
    retained={}
    def head(root,before,after):retained['head']=after;return after
    def holder(receipt):retained['holder']=receipt;return receipt
    def owner(receipt):retained['owner']=receipt;return receipt
    options=dict(retain_binder_head=head,retain_holder_receipt=holder,
                 retain_owner_receipt=owner,max_record_bytes=1024**2)
    return SimpleNamespace(roster=roster,options=options,retained=retained,global_=global_,
        report=report,study=study,episode=episode,guard=guard)


def create(c,**kw):return m.CommonOwnerGenesis(c.roster,create=True,**(c.options|kw))


def reopen(c,**kw):
    args=dict(expected_head=c.retained['head'],holder_receipt=c.retained.get('holder'),
              owner_receipt=c.retained.get('owner'))
    return m.CommonOwnerGenesis(c.roster,create=False,**(c.options|args|kw))


def test_real_empty_genesis_reopen_and_global_extension(case):
    c=case
    with create(c) as o:
        result=o.inspect();assert result['stage']==3 and result['persistent_empty_genesis_bound']
        assert not result['formal_execution_ready'] and not result['continuation_ready']
        assert o._holder.inspect()==() and o._phase.heads==(o._phase.genesis,)*2
        with pytest.raises(ValueError,match='no phase mutation'):o._deny_ticket()
        root=o.root
    c.global_.head='d'*64;c.global_.history.append((c.global_.head,{'other_group':True}))
    with reopen(c) as o:assert o.inspect()['global_head']=='d'*64
    assert root.exists() and not c.guard.locked()


@pytest.mark.parametrize('which',['holder','owner'])
def test_retained_child_receipt_failure_reconciles_metadata_only(case,which):
    c=case;key='retain_'+which+'_receipt';original=c.options[key]
    def fail(receipt):original(receipt);raise RuntimeError('retained then interrupted')
    with pytest.raises(RuntimeError,match='interrupted'):create(c,**{key:fail})
    before={str(p):p.read_bytes() for p in c.episode.rglob('*') if p.is_file()}
    with reopen(c,reconcile=True) as o:
        assert o.inspect()['stage']==(2 if which=='holder' else 3)
    assert before=={str(p):p.read_bytes() for p in c.episode.rglob('*') if p.is_file()}
    if which=='holder':assert not (c.episode/'owner_non_authoritative').exists()


@pytest.mark.parametrize('which',['holder','owner'])
def test_missing_external_receipt_rejected_for_committed_binding(case,which):
    c=case
    with create(c):pass
    args={which+'_receipt':None}
    if which=='holder':args['owner_receipt']=None
    with pytest.raises(ValueError,match='external .* receipt required'):reopen(c,**args)


@pytest.mark.parametrize('failure_at',[1,2,3])
def test_unknown_binder_suffix_preserved_and_rejected(case,failure_at):
    c=case;original=c.options['retain_binder_head'];calls=[]
    def fail(root,before,after):
        calls.append(after)
        if len(calls)==failure_at:
            c.retained.setdefault('head',before)
            raise RuntimeError('unretained suffix')
        return original(root,before,after)
    with pytest.raises(RuntimeError,match='suffix'):create(c,retain_binder_head=fail)
    paths=list(c.study.rglob(f'{failure_at:020d}.json'));assert len(paths)==1
    raw=paths[0].read_bytes()
    with pytest.raises(ValueError,match='external retained journal head'):reopen(c)
    assert paths[0].read_bytes()==raw


@pytest.mark.parametrize('mutation',['science','ancestor','receipt','child_suffix'])
def test_reopen_rejects_changed_correspondence_or_child(case,mutation):
    c=case
    with create(c):pass
    if mutation=='science':c.report['common_scientific_identity']='e'*64
    elif mutation=='ancestor':c.global_.genesis=c.global_.head='e'*64
    elif mutation=='receipt':c.retained['holder']=replace(c.retained['holder'],binding_sha256='e'*64)
    else:(c.episode/'holder_non_authoritative'/'unknown.json').write_text('{}')
    with pytest.raises(ValueError):reopen(c)


@pytest.mark.parametrize('cap',[1024,4096])
def test_complete_branch_preflight_has_no_directory_effect(case,cap):
    c=case
    with pytest.raises(ValueError,match='byte cap'):create(c,max_record_bytes=cap)
    assert not (c.study/'common_owners_non_authoritative').exists()
    assert list(c.episode.iterdir())==[]


def test_oversized_full_report_is_never_truncated(case):
    c=case;c.report['audit_padding']='x'*(1024**2)
    with pytest.raises(ValueError,match='byte cap'):create(c)
    assert not (c.study/'common_owners_non_authoritative').exists()


def test_callback_reentry_rejected_and_original_guard_released(case):
    c=case;original=c.options['retain_holder_receipt'];seen=[]
    def retain(receipt):
        with pytest.raises(ValueError,match='roster active'):c.roster._enter()
        seen.append(True);return original(receipt)
    with create(c,retain_holder_receipt=retain) as o:assert o.inspect()['stage']==3
    assert seen==[True] and not c.guard.locked()


def test_global_change_during_receipt_retention_is_rejected(case):
    c=case;original=c.options['retain_holder_receipt']
    def retain(receipt):
        original(receipt);c.global_.head='d'*64;c.global_.history.append(('d'*64,{}));return receipt
    with pytest.raises(ValueError,match='retention changed'):create(c,retain_holder_receipt=retain)
    assert not (c.episode/'owner_non_authoritative').exists()


def test_detached_diagnostic_cannot_create_owner(tmp_path):
    with pytest.raises(ValueError,match='exact live group roster'):
        m.CommonOwnerGenesis({},create=True,retain_binder_head=lambda *a:None,
            retain_holder_receipt=lambda x:x,retain_owner_receipt=lambda x:x,max_record_bytes=1024**2)


@pytest.mark.parametrize('mutation',['declaration','header','genesis','retainer','wrapper_retainer','cap','events','root'])
def test_journal_must_remain_bound_to_wrapper(case,mutation):
    c=case
    with create(c) as o:
        journal=o._journal;o._enter()
        try:
            if mutation=='declaration':journal._declaration=m.encode({})
            elif mutation=='header':
                value=json.loads(journal._header)
                value['declaration']['initial_report']['common_scientific_identity']='e'*64
                journal._header=m.encode(value)
                (journal.root/'header.json').write_bytes(journal._header)
                _,journal._header_identity=m.bootstrap.storage._read(journal.root/'header.json',journal.cap)
                journal.genesis=sha256(journal._header).hexdigest()
            elif mutation=='genesis':o._binder_genesis='e'*64
            elif mutation=='retainer':journal._retain=journal._original_retain=lambda *args:args[-1]
            elif mutation=='wrapper_retainer':o._binder_retainer=lambda *args:args[-1]
            else:
                if mutation=='cap':journal.cap-=1
                elif mutation=='events':journal.max_events=4
                else:journal.root=c.episode
                journal._configuration=(journal.root,journal.max_events,journal.cap)
            with pytest.raises((ValueError,FileNotFoundError)):
                journal.check()
        finally:o._leave()


@pytest.mark.parametrize('which',['holder','owner'])
def test_wrong_receipt_return_preserves_pending_state(case,which):
    c=case;key='retain_'+which+'_receipt';original=c.options[key]
    def wrong(receipt):original(receipt);return None
    with pytest.raises(ValueError,match='retention changed'):create(c,**{key:wrong})
    with reopen(c) as o:assert o.inspect()['stage']==(1 if which=='holder' else 2)


@pytest.mark.parametrize('which',['holder','owner'])
def test_partial_child_construction_has_no_automatic_retry(case,monkeypatch,which):
    c=case
    def partial(self,create,**kw):
        assert create
        root=self.holder_root if which=='holder' else self.owner_root
        root.mkdir();(root/'partial_failure.txt').write_text('retained failure')
        raise RuntimeError('partial child')
    with monkeypatch.context() as patch:
        patch.setattr(m.CommonOwnerGenesis,'_'+which+'_open',partial)
        with pytest.raises(RuntimeError,match='partial child'):create(c)
    before={str(p):p.read_bytes() for p in c.episode.rglob('*') if p.is_file()}
    with reopen(c) as o:
        assert o.inspect()['stage']==(1 if which=='holder' else 2)
        assert not o.inspect()['persistent_empty_genesis_bound']
    with pytest.raises(ValueError,match='absent fixed child roots'):create(c)
    assert before=={str(p):p.read_bytes() for p in c.episode.rglob('*') if p.is_file()}


def test_real_roster_incomplete_input_rejected_before_child_creation(
        bootstrap_setup,cached_declarations,monkeypatch):
    s=bootstrap_setup;parent=s.open(declaration=declaration(s.declaration));group=roster(parent,s)
    def denied(*args,**kw):raise AssertionError('incomplete roster reached historical source')
    monkeypatch.setattr(m.bootstrap.historical,'prepare',denied)
    try:
        with pytest.raises(ValueError,match='every direct'):
            m.CommonOwnerGenesis(group,create=True,retain_binder_head=lambda *args:args[-1],
                retain_holder_receipt=lambda r:r,retain_owner_receipt=lambda r:r,max_record_bytes=1024**2)
        assert not (parent.study_root/'common_owners_non_authoritative').exists()
        assert not group._original_operation.locked() and not parent._original_operation.locked()
        assert not list(group.root.glob('[0-9]*.json'))
    finally:group.close();parent.close()
