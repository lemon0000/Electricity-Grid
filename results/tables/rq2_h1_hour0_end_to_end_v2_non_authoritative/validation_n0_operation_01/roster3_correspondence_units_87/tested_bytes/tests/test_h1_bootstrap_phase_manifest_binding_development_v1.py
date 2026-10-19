"""Owner-bound declarations with real journal bytes; zero producer/Job/native."""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from tests.test_h1_bootstrap_integration_development_v1 import m, example, setup, retained
from tests.test_h1_bootstrap_selector_configuration_development_v1 import bound
from tests.test_h1_selector_configuration_development_v1 import no_execution


def declaration(s):
    return replace(bound(s.declaration),phase_archive=m.phase_manifest.ArchiveCapacityDeclaration(576,2**20,576*2**20,0))


@pytest.fixture
def fingerprint_cache(monkeypatch):
    # Owner protocol tests reuse real initial immutable dependency observations.
    # Separate tests below exercise the actual fresh reader and drift rejection.
    original=m._phase_input_fingerprint;cache={};calls=[]
    implementation=m.selector_config.implementation_identity()
    monkeypatch.setattr(m.selector_config,'implementation_identity',lambda:implementation)
    def fingerprint(c):
        key=id(c);calls.append(key)
        if key not in cache:cache[key]=original(c)
        return cache[key]
    monkeypatch.setattr(m,'_phase_input_fingerprint',fingerprint)
    return calls


def test_fresh_fingerprint_matches_closed_preparation(setup):
    d=declaration(setup);c=d.selector_configuration
    value=m.phase_manifest.prepare(d.family,d.ordinal,c,d.phase_archive)
    audit=json.loads(value.audit_payload)
    assert m._phase_input_fingerprint(c)==(audit['group']['implementation_sha256'],audit['implementation_sha256'])


def test_header_claim_foreign_reopen_and_cache(setup,monkeypatch,fingerprint_cache):
    s=setup;d=declaration(s);prepare=m.phase_manifest.prepare;ordinals=[]
    def observe(family,ordinal,*args):
        ordinals.append(ordinal);return prepare(family,ordinal,*args)
    monkeypatch.setattr(m.phase_manifest,'prepare',observe)
    o=s.open(declaration=d)
    try:
        header=json.loads((o._bootstrap.root/'header.json').read_bytes())
        candidate=header['declaration']['phase_manifest_candidate']
        assert m.sha256(m.encode(candidate['audit'])).hexdigest()==candidate['audit_identity']
        selected=next(x for x in candidate['audit']['group']['siblings'] if x['ordinal']==0)
        assert selected['obligation_node']==s.snapshot.obligation('training_ub',0)['obligation_node']
        assert len(candidate['audit']['manifest']['lanes'])==3
        assert o._proposal()['phase_manifest_audit_identity']==candidate['audit_identity']
        assert 'phase_manifest_candidate' not in o._proposal()
        assert 'phase_manifest_candidate' not in o._study_binding
        for _ in range(2):o._check()
        assert ordinals==[0] and len(fingerprint_cache)>=4
        info=o.inspect()
        assert info['phase_manifest_candidate_bound']
        for key in ('phase_manifest_owner_attached','group_execution_roster_authenticated',
                    'all_sibling_execution_verified','normal_reuse_verified','selector_producer_connected',
                    'formal_result','formal_execution_ready','resource_admission'):
            assert info[key] is False
        with pytest.raises(ValueError,match='producer not implemented'):o.bootstrap()
        assert len(o._global.rows())==1 and len(o._bootstrap.rows())==1
        assert not Path(o.roots['owner']).exists() and not Path(o.roots['holder']).exists()
        heads=retained(o,s)
    finally:o.close()
    other=s.open(declaration=replace(d,ordinal=1),create_study=False,global_head=heads['global_head'])
    try:
        assert len(other._registry())==1
        assert ordinals==[0,1,0]
    finally:other.close()
    reopened=s.open(declaration=d,create_study=False,create=False,**heads)
    try:
        assert reopened.inspect()['state']=='claimed_pre_source'
        assert ordinals==[0,1,0,0]
    finally:reopened.close()


@pytest.mark.parametrize('change',['missing_selector','wrong_type'])
def test_archive_typing_precedes_files(setup,change):
    s=setup;d=bound(s.declaration)
    with pytest.raises(ValueError,match='phase archive'):
        if change=='missing_selector':replace(s.declaration,phase_archive=declaration(s).phase_archive)
        else:replace(d,phase_archive={})
    assert not Path(s.declaration.study_root).exists()


def test_selector_without_archive_does_not_prepare_candidate(setup,monkeypatch):
    def denied(*a,**k):raise AssertionError('None phase archive reached preparation')
    monkeypatch.setattr(m.phase_manifest,'prepare',denied)
    monkeypatch.setattr(m,'_phase_input_fingerprint',denied)
    o=setup.open(declaration=bound(setup.declaration))
    try:
        assert not o.inspect()['phase_manifest_candidate_bound']
        assert o._proposal()['phase_manifest_audit_identity'] is None
    finally:o.close()


@pytest.mark.parametrize('change',['mapping','bytes','hash','key'])
def test_cache_mutation_rejected_before_attempt(setup,fingerprint_cache,change):
    s=setup;o=s.open(declaration=declaration(s));key=next(iter(o._phase_cache));value=o._phase_cache[key]
    try:
        if change=='mapping':o._phase_cache=dict(o._phase_cache)
        elif change=='bytes':o._phase_cache[key]=(value[0]+b' ',value[1])
        elif change=='hash':o._phase_cache[key]=(value[0],'a'*64)
        else:o._phase_cache[(key[0],key[1]+1,key[2],key[3])]=o._phase_cache.pop(key)
        with pytest.raises(ValueError,match='cache'):o.bootstrap()
        assert o.poisoned and not list(o._bootstrap.root.glob('[0-9]*.json'))
    finally:o.close()


@pytest.mark.parametrize('where',['before','local_retention','global_retention'])
def test_dependency_drift_stops_next_effect(setup,monkeypatch,fingerprint_cache,where):
    s=setup;d=declaration(s);original=m._phase_input_fingerprint;changed=False
    def fingerprint(c):return ('a'*64,'b'*64) if changed else original(c)
    monkeypatch.setattr(m,'_phase_input_fingerprint',fingerprint)
    def retain(root,before,after):
        nonlocal changed
        result=s.retain(root,before,after)
        if (where=='local_retention' and Path(root)==o._bootstrap.root
                or where=='global_retention' and Path(root)==o._global.root):changed=True
        return result
    o=m.BootstrapOwner(d,create=True,create_study=True,retain_global_head=retain,retain_bootstrap_head=retain)
    try:
        if where=='before':changed=True
        with pytest.raises(ValueError,match='dependencies changed'):o.bootstrap()
        assert o.poisoned
        assert len(list(o._bootstrap.root.glob('[0-9]*.json')))==(0 if where=='before' else 1)
        assert len(list(o._global.root.glob('[0-9]*.json')))==(1 if where=='global_retention' else 0)
        assert not Path(o.roots['controller']).exists()
    finally:o.close()


@pytest.mark.parametrize('change',['selected','identity','canonical','fingerprint'])
def test_prepare_mismatch_before_directories(setup,monkeypatch,fingerprint_cache,change):
    original=m.phase_manifest.prepare
    def changed(*a,**k):
        result=original(*a,**k);audit=json.loads(result.audit_payload)
        if change=='selected':audit['group']['siblings'][-1]['obligation_node']['extra']=True
        elif change=='fingerprint':audit['implementation_sha256']='0'*64
        raw=m.encode(audit)
        if change=='canonical':raw+=b' '
        pin='0'*64 if change=='identity' else m.sha256(raw).hexdigest()
        return m.phase_manifest.PreparedManifest(result.manifest,raw,pin)
    monkeypatch.setattr(m.phase_manifest,'prepare',changed)
    with pytest.raises(ValueError,match='phase candidate'):
        setup.open(declaration=declaration(setup))
    assert not Path(setup.declaration.study_root).exists()


def test_exact_header_size_boundary_before_directories(setup,monkeypatch,fingerprint_cache):
    s=setup;d=declaration(s);sizes=[];original=m._journal_header
    def observe(*args):
        raw=original(*args);sizes.append(len(raw));return raw
    monkeypatch.setattr(m,'_journal_header',observe)
    # Derive the fixed point: cap digits are themselves in header declarations.
    first=replace(d,max_record_bytes=1024)
    for _ in range(3):
        sizes.clear()
        with pytest.raises(ValueError,match='journal byte cap'):s.open(declaration=first)
        assert not Path(d.study_root).exists()
        cap=max(sizes)
        first=replace(d,max_record_bytes=cap-1)
    assert cap==max(sizes)
    accepted=replace(d,max_record_bytes=cap)
    o=s.open(declaration=accepted)
    try:assert len((o._bootstrap.root/'header.json').read_bytes())==cap
    finally:o.close()


@pytest.mark.parametrize('field',['archive','selector'])
@pytest.mark.parametrize('mode',['substitute','mutate_after'])
def test_prepare_cannot_substitute_or_change_request(setup,monkeypatch,fingerprint_cache,field,mode):
    s=setup;d=declaration(s);original=m.phase_manifest.prepare
    def prepare(family,ordinal,c,a):
        if mode=='substitute':
            if field=='archive':a=replace(a,max_archive_bytes=a.max_archive_bytes+1)
            else:c=replace(c,reference_non_solver_seconds=1)
        result=original(family,ordinal,c,a)
        if mode=='mutate_after':
            if field=='archive':object.__setattr__(a,'max_archive_bytes',a.max_archive_bytes+1)
            else:object.__setattr__(c,'reference_non_solver_seconds',1)
        return result
    monkeypatch.setattr(m.phase_manifest,'prepare',prepare)
    with pytest.raises(ValueError,match='phase candidate'):s.open(declaration=d)
    assert not Path(d.study_root).exists()


def test_preflight_callback_drift_rejected_before_directories(setup,monkeypatch,fingerprint_cache):
    s=setup;d=declaration(s);original=m.BootstrapOwner._preflight_journal_bytes
    def preflight(self,*args):
        original(self,*args)
        object.__setattr__(d.phase_archive,'max_archive_bytes',d.phase_archive.max_archive_bytes+1)
    monkeypatch.setattr(m.BootstrapOwner,'_preflight_journal_bytes',preflight)
    with pytest.raises(ValueError,match='declaration'):s.open(declaration=d)
    assert not Path(d.study_root).exists()


def test_cache_and_snapshot_cannot_replace_durable_header_candidate(setup,fingerprint_cache):
    s=setup;o=s.open(declaration=declaration(s));key=next(iter(o._phase_cache))
    try:
        audit=json.loads(o._phase_cache[key][0]);audit['manifest']['max_archive_bytes']+=1
        raw=m.encode(audit);o._phase_cache[key]=(raw,m.sha256(raw).hexdigest())
        o._phase_cache_snapshot=tuple(sorted(o._phase_cache.items()))
        with pytest.raises(ValueError,match='retained header'):o.bootstrap()
        assert o.poisoned and not list(o._bootstrap.root.glob('[0-9]*.json'))
        assert not list(o._global.root.glob('[0-9]*.json'))
    finally:o.close()


def test_same_group_other_arm_is_separate_ordinal_and_claim(setup,monkeypatch,fingerprint_cache):
    s=setup;d=declaration(s);o=s.open(declaration=d)
    try:
        original_slot=o._slot['slot_id']
        candidate=o._phase_candidate(d);g=candidate['audit']['group']
        sibling=next(x for x in g['siblings'] if x['arm_id']=='CFE-only')
        other_d=replace(d,ordinal=sibling['ordinal'])
        other=o._phase_candidate(other_d)
        assert other['audit']['group']['group_identity']==g['group_identity']
        assert other['audit_identity']!=candidate['audit_identity']
        assert len(o._phase_cache)==2
        with pytest.raises(ValueError,match='producer not implemented'):o.bootstrap()
        heads=retained(o,s)
    finally:o.close()
    foreign=s.open(declaration=other_d,create_study=False,global_head=heads['global_head'])
    try:
        assert foreign._slot['slot_id']!=original_slot
        assert not foreign.inspect()['normal_reuse_verified']
        with pytest.raises(ValueError,match='producer not implemented'):foreign.bootstrap()
        assert len(foreign._global.rows())==2
        assert len(foreign._registry())==2
    finally:foreign.close()


@pytest.mark.parametrize('field',['audit','identity'])
def test_foreign_header_candidate_tamper_is_rejected(setup,fingerprint_cache,field):
    s=setup;d=declaration(s);o=s.open(declaration=d)
    try:
        with pytest.raises(ValueError,match='producer not implemented'):o.bootstrap()
        heads=retained(o,s);path=o._bootstrap.root/'header.json'
    finally:o.close()
    value=json.loads(path.read_bytes());candidate=value['declaration']['phase_manifest_candidate']
    if field=='audit':candidate['audit']['manifest']['max_archive_bytes']+=1
    else:candidate['audit_identity']='0'*64
    path.write_bytes(m.encode(value))
    with pytest.raises(ValueError,match='cross-reference'):
        s.open(declaration=replace(d,ordinal=1),create_study=False,global_head=heads['global_head'])


def test_fingerprint_drift_after_prepare_precedes_cache_and_files(setup,monkeypatch,fingerprint_cache):
    original=m.phase_manifest.prepare;fingerprint=m._phase_input_fingerprint;changed=False
    def prepare(*args):
        nonlocal changed
        result=original(*args);changed=True;return result
    monkeypatch.setattr(m.phase_manifest,'prepare',prepare)
    monkeypatch.setattr(m,'_phase_input_fingerprint',lambda c:('0'*64,'1'*64) if changed else fingerprint(c))
    with pytest.raises(ValueError,match='dependencies changed'):setup.open(declaration=declaration(setup))
    assert not Path(setup.declaration.study_root).exists()


@pytest.mark.parametrize('target',['attempt','claim'])
def test_preflight_includes_both_record_envelopes(setup,monkeypatch,fingerprint_cache,target):
    # Isolate record sizing from the larger header; no production bytes are written.
    d=declaration(setup);original=m.encode;seen=[]
    def encode(value):
        if type(value) is dict and set(value)=={'sequence','previous','body'} and value['body'].get('kind')==target:
            seen.append(target);return b'x'*(d.max_record_bytes+1)
        return original(value)
    monkeypatch.setattr(m,'encode',encode)
    with pytest.raises(ValueError,match='journal byte cap'):setup.open(declaration=d)
    assert seen==[target]
    assert not Path(d.study_root).exists()


@pytest.mark.parametrize('target',['protocol','proof','group','binder'])
def test_real_fingerprint_reader_detects_changed_view(setup,monkeypatch,target):
    group=m.phase_manifest.group;original=group.io.read_stable
    if target=='binder':
        identities=iter(('0'*64,'1'*64))
        monkeypatch.setattr(m.phase_manifest,'_implementation',lambda c:next(identities))
        with pytest.raises(ValueError,match='implementation changed'):
            m._phase_input_fingerprint(declaration(setup).selector_configuration)
        return
    path={'protocol':group.ROOT/group.PROTOCOL,'proof':group.ROOT/group.symbolic.PROOF,
          'group':Path(group.__file__)}[target]
    count=0
    def read(p,cap):
        nonlocal count
        view=original(p,cap)
        if p==path:
            count+=1
            if count>=2:return view[0]+b' ',view[1]
        return view
    monkeypatch.setattr(group.io,'read_stable',read)
    with pytest.raises(ValueError,match='phase|pinned'):
        m._phase_input_fingerprint(declaration(setup).selector_configuration)


@pytest.mark.parametrize('change',['cache_snapshot','normal_configuration'])
def test_proposal_fingerprint_callback_cannot_cross_header_anchor(setup,monkeypatch,fingerprint_cache,change):
    s=setup;d=declaration(s);o=s.open(declaration=d)
    original=m._phase_input_fingerprint;proposal=m.BootstrapOwner._proposal;armed=False;changed=False
    def fingerprint(c):
        nonlocal changed
        result=original(c)
        if armed and not changed:
            changed=True
            if change=='cache_snapshot':
                key=next(iter(o._phase_cache));audit=json.loads(o._phase_cache[key][0])
                audit['manifest']['max_archive_bytes']+=1
                raw=m.encode(audit);o._phase_cache[key]=(raw,m.sha256(raw).hexdigest())
                o._phase_cache_snapshot=tuple(sorted(o._phase_cache.items()))
            else:
                config=d.run_configuration
                object.__setattr__(d,'run_configuration',replace(config,budget=replace(config.budget,max_elapsed_seconds=299.)))
        return result
    def wrapped(self):
        nonlocal armed
        armed=True
        try:return proposal(self)
        finally:armed=False
    monkeypatch.setattr(m,'_phase_input_fingerprint',fingerprint)
    monkeypatch.setattr(m.BootstrapOwner,'_proposal',wrapped)
    try:
        with pytest.raises(ValueError,match='retained header|declaration'):o.bootstrap()
        assert changed and o.poisoned
        assert not list(o._bootstrap.root.glob('[0-9]*.json'))
        assert not list(o._global.root.glob('[0-9]*.json'))
    finally:o.close()


def test_returned_candidate_cannot_replace_header_candidate(setup,monkeypatch,fingerprint_cache):
    s=setup;o=s.open(declaration=declaration(s));original=m.BootstrapOwner._phase_candidate
    def candidate(self,d):
        value=original(self,d);value['audit_identity']='0'*64;return value
    monkeypatch.setattr(m.BootstrapOwner,'_phase_candidate',candidate)
    try:
        with pytest.raises(ValueError,match='proposal differs'):o.bootstrap()
        assert o.poisoned and not list(o._bootstrap.root.glob('[0-9]*.json'))
        assert not list(o._global.root.glob('[0-9]*.json'))
    finally:o.close()
