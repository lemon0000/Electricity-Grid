"""Real journals and fake N0 evidence: protocol mapping only, zero native/Job."""
from dataclasses import asdict, replace
import json
from pathlib import Path
from threading import Thread

import pytest

from experiments import h1_group_execution_roster_development_v1 as r
from tests.test_h1_bootstrap_integration_development_v1 import m, example, setup, retained
from tests.test_h1_bootstrap_N0_registration_development_v1 import protocol
from tests.test_h1_bootstrap_selector_configuration_development_v1 import bound
from tests.test_h1_selector_configuration_development_v1 import no_execution


@pytest.fixture
def cached_declarations(monkeypatch):
    # Protocol tests reuse real initial immutable declaration observations.
    # They make no runtime freshness or performance claim. Reader faults below
    # exercise the wrapper's mandatory fresh preparation boundaries separately.
    implementation=m.selector_config.implementation_identity()
    monkeypatch.setattr(m.selector_config,'implementation_identity',lambda:implementation)
    fingerprint=m._phase_input_fingerprint; fingerprints={}
    def observe(c):
        key=id(c)
        if key not in fingerprints:fingerprints[key]=fingerprint(c)
        return fingerprints[key]
    monkeypatch.setattr(m,'_phase_input_fingerprint',observe)
    prepare=m.phase_manifest.prepare; candidates={}
    def candidate(family,ordinal,c,a):
        key=m.encode([family,ordinal,c.binding(),asdict(a)])
        if key not in candidates:candidates[key]=prepare(family,ordinal,c,a)
        return candidates[key]
    monkeypatch.setattr(m.phase_manifest,'prepare',candidate)


def declaration(d):
    return replace(bound(d),phase_archive=m.phase_manifest.ArchiveCapacityDeclaration(576,2**20,576*2**20,0))


@pytest.fixture
def environment(protocol,cached_declarations,monkeypatch):
    s,d=protocol
    # The original one-episode fixture asserts one claim. This group fixture
    # explicitly permits several synthetic static inventories, never source/Job.
    monkeypatch.setattr(m.phase.binding.source_binding.rts,'load_rts_gmlc_chronological_data',lambda root:s.data)
    return s,declaration(d)


def roster(o,s,**kw):
    return r.GroupRoster(o,create=kw.pop('create',True),max_record_bytes=kw.pop('max_record_bytes',65536),
                         retain_head=kw.pop('retain_head',s.retain),**kw)


def test_three_independent_entries_and_partial_reopen(environment):
    s,d=environment;heads=None;group_head=None;group_identity=None;ordinals=None;group_root=None
    for index in range(3):
        current=d if index==0 else replace(d,ordinal=ordinals[index])
        kw={} if heads is None else dict(create_study=False,global_head=heads['global_head'])
        o=s.open(declaration=current,**kw)
        g=None
        try:
            assert o.bootstrap()['state']=='pending_post_N'
            g=roster(o,s,create=index==0,expected_head=group_head)
            view=g.inspect()
            if index==0:
                direct=[e['sibling'] for e in view['entries'] if e['classification']=='direct_shared_lane']
                ordinals=sorted(x['ordinal'] for x in direct)
                assert ordinals[0]==d.ordinal
                group_identity=view['group_identity'];group_root=g.root
            assert view['group_identity']==group_identity and g.root==group_root
            assert len(view['entries'])==4
            assert sum(e['attachment'] is not None for e in view['entries'])==index
            assert not view['independent_N0_mapping_complete']
            arm=next(e['sibling']['arm_id'] for e in view['entries'] if e['sibling']['ordinal']==current.ordinal)
            group_head=g.attach(arm,expected_head=view['head'])
            after=g.inspect()
            assert after['independent_N0_mapping_complete']==(index==2)
            assert all(after[k] is False for k in r.FLAGS)
            b6=next(e for e in after['entries'] if e['sibling']['arm_id']=='joint-B6')
            assert b6['classification']=='pending_separate_B6_planning' and b6['attachment'] is None
            refs=[e['attachment']['reference'] for e in after['entries'] if e['attachment'] is not None]
            assert len({x['slot_id'] for x in refs})==index+1
            assert len({x['episode_root'] for x in refs})==index+1
            assert all(x['reuse_edge'] is None for x in refs)
            heads=retained(o,s)
            if index==2:
                with pytest.raises(ValueError,match='already attached'):g.attach(arm,expected_head=group_head)
                assert len(list(group_root.glob('[0-9]*.json')))==3
        finally:
            if g is not None:g.close()
            o.close()
    reopened=s.open(declaration=current,create_study=False,create=False,**heads)
    try:
        with_roster=roster(reopened,s,create=False,expected_head=group_head)
        try:assert with_roster.inspect()['independent_N0_mapping_complete']
        finally:with_roster.close()
    finally:reopened.close()


@pytest.mark.parametrize('arm',['network-only','joint-B6'])
def test_missing_or_non_direct_never_attaches(setup,cached_declarations,arm):
    s=setup;o=s.open(declaration=declaration(s.declaration));g=roster(o,s)
    try:
        view=g.inspect()
        assert not view['independent_N0_mapping_complete']
        assert not any(e['independent_N0_available'] for e in view['entries'])
        with pytest.raises(ValueError,match='terminal required|direct sibling'):
            g.attach(arm,expected_head=view['head'])
        assert g.poisoned and not list(g.root.glob('[0-9]*.json'))
        assert not list(o._bootstrap.root.glob('[0-9]*.json'))
    finally:g.close();o.close()


def test_group_header_capacity_precedes_group_directory(setup,cached_declarations):
    s=setup;o=s.open(declaration=declaration(s.declaration))
    try:
        with pytest.raises(ValueError,match='header exceeds'):roster(o,s,max_record_bytes=1024)
        assert not (o.study_root/'groups_non_authoritative').exists()
    finally:o.close()


@pytest.mark.parametrize('change',['head','cap'])
def test_stale_head_and_reopen_capacity_conflict(setup,cached_declarations,change):
    s=setup;o=s.open(declaration=declaration(s.declaration));g=roster(o,s)
    root=g.root;head=g._journal.head;g.close()
    try:
        kw=dict(create=False,expected_head='0'*64 if change=='head' else head)
        if change=='cap':kw['max_record_bytes']=65537
        with pytest.raises(ValueError,match='retained journal head|declaration changed'):roster(o,s,**kw)
        assert (root/'header.json').exists() and not list(root.glob('[0-9]*.json'))
    finally:o.close()


def test_same_group_lease_and_owner_guard(setup,cached_declarations):
    s=setup;o=s.open(declaration=declaration(s.declaration));g=roster(o,s)
    try:
        with pytest.raises(ValueError,match='already held'):roster(o,s,create=False,expected_head=g._journal.head)
        o._operation.acquire()
        try:
            with pytest.raises(ValueError,match='bootstrap operation active'):g.inspect()
        finally:o._operation.release()
        errors=[]
        def foreign():
            try:g.inspect()
            except ValueError as e:errors.append(str(e))
        t=Thread(target=foreign);t.start();t.join()
        assert errors and not g._operation.locked() and not o._operation.locked()
    finally:g.close();o.close()


@pytest.mark.parametrize('where',['before','after'])
def test_retention_failure_preserves_exact_suffix(environment,where):
    s,d=environment;o=s.open(declaration=d);assert o.bootstrap()['state']=='pending_post_N'
    def retain(root,before,after):
        if where=='after':s.retain(root,before,after)
        raise RuntimeError('group retention fault')
    g=roster(o,s,retain_head=retain);before=g._journal.head;root=g.root
    try:
        with pytest.raises(RuntimeError,match='retention fault'):g.attach('network-only',expected_head=before)
        assert g.poisoned and len(list(root.glob('[0-9]*.json')))==1
    finally:g.close()
    head=s.heads.get(str(root),before)
    try:
        if where=='before':
            with pytest.raises(ValueError,match='retained journal head'):roster(o,s,create=False,expected_head=head)
        else:
            recovered=roster(o,s,create=False,expected_head=head)
            try:
                assert sum(e['attachment'] is not None for e in recovered.inspect()['entries'])==1
                with pytest.raises(ValueError,match='already attached'):
                    recovered.attach('network-only',expected_head=head)
            finally:recovered.close()
        assert len(o._global.rows())==3
    finally:o.close()


def test_retention_configuration_change_detected(environment):
    s,d=environment;o=s.open(declaration=d);o.bootstrap()
    def retain(root,before,after):
        value=s.retain(root,before,after)
        object.__setattr__(d.phase_archive,'max_archive_bytes',d.phase_archive.max_archive_bytes+1)
        return value
    g=roster(o,s,retain_head=retain)
    try:
        with pytest.raises(ValueError,match='declaration|configuration'):
            g.attach('network-only',expected_head=g._journal.head)
        assert g.poisoned and len(list(g.root.glob('[0-9]*.json')))==1
        assert not o._operation.locked()
    finally:g.close();o.close()


def test_canonical_prepare_substitution_rejected_before_directory(setup,cached_declarations,monkeypatch):
    s=setup;o=s.open(declaration=declaration(s.declaration));prepare=m.phase_manifest.prepare
    def changed(*a,**kw):
        value=prepare(*a,**kw);audit=json.loads(value.audit_payload)
        audit['manifest']['accounting_period_id']='changed'
        raw=m.encode(audit)
        return m.phase_manifest.PreparedManifest(value.manifest,raw,m.sha256(raw).hexdigest())
    monkeypatch.setattr(m.phase_manifest,'prepare',changed)
    try:
        with pytest.raises(ValueError,match='canonical sibling'):roster(o,s)
        assert not (o.study_root/'groups_non_authoritative').exists()
    finally:o.close()


@pytest.mark.parametrize('target',['group','global','local'])
def test_retained_reference_tamper_rejected(environment,target):
    s,d=environment;o=s.open(declaration=d);o.bootstrap();g=roster(o,s)
    try:
        head=g.attach('network-only',expected_head=g._journal.head)
        if target=='group':path=g.root/'00000000000000000001.json'
        elif target=='global':path=o._global.root/'00000000000000000003.json'
        else:path=o._bootstrap.root/'00000000000000000005.json'
        path.write_bytes(path.read_bytes()+b' ')
        with pytest.raises(ValueError):g.inspect()
        assert path.exists()
    finally:g.close();o.close()


def test_complete_event_envelope_checked_before_write(environment,monkeypatch):
    s,d=environment;o=s.open(declaration=d);o.bootstrap();g=roster(o,s)
    encode=m.encode
    def oversized(value):
        if (type(value) is dict and set(value)=={'sequence','previous','body'}
                and value['body'].get('kind')=='attach_independent_N0'):
            return b'x'*(g.max_record_bytes+1)
        return encode(value)
    monkeypatch.setattr(m,'encode',oversized)
    try:
        with pytest.raises(ValueError,match='record exceeds cap'):
            g.attach('network-only',expected_head=g._journal.head)
        assert not list(g.root.glob('[0-9]*.json')) and len(o._global.rows())==3
    finally:g.close();o.close()


def test_B6_owner_cannot_register_nonempty_direct_group(setup,cached_declarations):
    s=setup;d=declaration(s.declaration);o=s.open(declaration=d)
    try:
        candidate=o._phase_candidate(d)
        ordinal=next(x['ordinal'] for x in candidate['audit']['group']['siblings'] if x['arm_id']=='joint-B6')
        global_head=o._global.head
    finally:o.close()
    b6=s.open(declaration=replace(d,ordinal=ordinal),create_study=False,global_head=global_head)
    try:
        with pytest.raises(ValueError,match='direct sibling'):roster(b6,s)
        assert not (b6.study_root/'groups_non_authoritative').exists()
    finally:b6.close()


def test_header_only_semantics_reject_every_event(setup,cached_declarations,monkeypatch):
    # Synthetic zero-direct wrapper state only; not a claim that this coordinate
    # is a proof-discharged group in the pinned catalog. Binder proof mapping is
    # separately tested by its closed unit.
    s=setup;d=declaration(s.declaration);o=s.open(declaration=d);candidate=r._candidate(o)
    ordinal=next(x['ordinal'] for x in candidate['audit']['group']['siblings'] if x['arm_id']=='joint-B6')
    global_head=o._global.head;o.close()
    o=s.open(declaration=replace(d,ordinal=ordinal),create_study=False,global_head=global_head)
    audit=candidate['audit'];audit['manifest']=None
    for row in audit['arm_classifications']:
        row['classification']='pending_separate_B6_planning' if row['arm_id']=='joint-B6' else 'proof_terminal'
    for sibling in audit['group']['siblings']:
        sibling['disposition']='unresolved_no_certificate' if sibling['arm_id']=='joint-B6' else 'direct_analytic_witness'
    assert r._canonical_ordinal(audit,ordinal)==min(x['ordinal'] for x in audit['group']['siblings'])
    with pytest.raises(ValueError,match='header-only'):
        r._canonical_ordinal(audit,d.ordinal)
    candidate['audit_identity']=m.digest(audit)
    monkeypatch.setattr(r,'_candidate',lambda owner:json.loads(m.encode(candidate)))
    g=roster(o,s)
    try:
        view=g.inspect()
        assert view['maximum_attach_events']==0 and not view['independent_N0_mapping_complete']
        assert g._journal.max_events==1 and not any(e['attachment'] for e in view['entries'])
        with pytest.raises(ValueError,match='direct sibling'):
            g.attach('joint-B6',expected_head=view['head'])
        assert not list(g.root.glob('[0-9]*.json'))
        root=g.root;head=g._journal.head
    finally:g.close()
    raw=m.encode(dict(sequence=1,previous=head,body=dict(kind='attach_independent_N0',arm_id='joint-B6')))
    (root/'00000000000000000001.json').write_bytes(raw)
    try:
        with pytest.raises(ValueError,match='non-direct'):
            roster(o,s,create=False,expected_head=m.sha256(raw).hexdigest())
    finally:o.close()


def test_nonce_rejects_creation_and_live_operations(setup,cached_declarations):
    s=setup;o=s.open(declaration=declaration(s.declaration));nonce=object();g=None
    try:
        o._operation_nonce=nonce
        with pytest.raises(ValueError,match='nonce'):roster(o,s)
        assert not (o.study_root/'groups_non_authoritative').exists()
        o._operation_nonce=None;g=roster(o,s);head=g._journal.head
        o._operation_nonce=nonce
        for operation in (g.inspect,lambda:g.attach('network-only',expected_head=head)):
            with pytest.raises(ValueError,match='nonce'):operation()
        assert not g._operation.locked() and not o._operation.locked()
        assert o._operation_nonce is nonce and not list(g.root.glob('[0-9]*.json'))
    finally:
        if g is not None:g.close()
        o.close()


def test_retention_nonce_change_rejects_acceptance(environment):
    s,d=environment;o=s.open(declaration=d);o.bootstrap();nonce=object()
    def retain(root,before,after):
        value=s.retain(root,before,after);o._operation_nonce=nonce;return value
    g=roster(o,s,retain_head=retain)
    try:
        with pytest.raises(ValueError,match='nonce'):
            g.attach('network-only',expected_head=g._journal.head)
        assert g.poisoned and len(list(g.root.glob('[0-9]*.json')))==1
        assert o._operation_nonce is nonce
        assert not o._operation.locked() and not g._operation.locked()
    finally:g.close();o.close()


def test_release_alias_rejected_before_second_write(environment,monkeypatch):
    s,d=environment;o=s.open(declaration=d);o.bootstrap();g=roster(o,s)
    view=g.inspect();first=next(e['sibling'] for e in view['entries'] if e['sibling']['ordinal']==d.ordinal)
    other=next(e['sibling'] for e in view['entries'] if e['classification']=='direct_shared_lane'
               and e['sibling']['ordinal']!=d.ordinal)
    head=g.attach(first['arm_id'],expected_head=view['head']);heads=retained(o,s);g.close();o.close()
    o=s.open(declaration=replace(d,ordinal=other['ordinal']),create_study=False,global_head=heads['global_head'])
    o.bootstrap();g=roster(o,s,create=False,expected_head=head)
    original=r._reference;registry=o._registry()
    first_reference=original(o,first,registry)
    def aliased(owner,sibling,registry):
        value=original(owner,sibling,registry)
        if value is not None and sibling['arm_id']==other['arm_id']:
            value['release']['head']=first_reference['release']['head']
        return value
    monkeypatch.setattr(r,'_reference',aliased)
    try:
        with pytest.raises(ValueError,match='cross-arm'):
            g.attach(other['arm_id'],expected_head=head)
        assert g.poisoned and len(list(g.root.glob('[0-9]*.json')))==1
    finally:g.close();o.close()


def test_claim_only_stays_pending(environment,monkeypatch):
    s,d=environment
    monkeypatch.setattr(m.BootstrapOwner,'_continue_bootstrap',lambda self:dict(state='test_claim_only'))
    o=s.open(declaration=d);o.bootstrap();g=roster(o,s)
    try:
        assert len(o._global.rows())==1
        assert not any(e['independent_N0_available'] for e in g.inspect()['entries'])
        with pytest.raises(ValueError,match='terminal required'):
            g.attach('network-only',expected_head=g._journal.head)
        assert not list(g.root.glob('[0-9]*.json'))
    finally:g.close();o.close()


def test_local_terminal_without_global_commit_stays_pending(environment,monkeypatch):
    s,d=environment;o=s.open(declaration=d);append=o._global.append
    def fail_terminal(body,**kw):
        if body['kind']=='normal_terminal':raise RuntimeError('before global terminal')
        return append(body,**kw)
    monkeypatch.setattr(o._global,'append',fail_terminal)
    try:
        with pytest.raises(RuntimeError,match='before global terminal'):o.bootstrap()
        assert len(o._bootstrap.rows())==5 and len(o._global.rows())==2
        heads=retained(o,s)
    finally:o.close()
    o=s.open(declaration=d,create=False,create_study=False,**heads);g=roster(o,s)
    try:
        assert o.inspect()['state']=='local_N_terminal_uncommitted'
        assert not any(e['independent_N0_available'] for e in g.inspect()['entries'])
        with pytest.raises(ValueError,match='terminal required'):
            g.attach('network-only',expected_head=g._journal.head)
        assert not list(g.root.glob('[0-9]*.json'))
    finally:g.close();o.close()


def test_foreign_arm_terminal_cannot_supply_sibling(environment):
    s,d=environment;o=s.open(declaration=d);o.bootstrap()
    try:
        siblings=r._candidate(o)['audit']['group']['siblings']
        other=next(x for x in siblings if x['arm_id']=='CFE-only')
        registry=o._registry();state=next(iter(registry.values()))
        slot=o._manifest.resolve(d.family,other['ordinal']*192)
        with pytest.raises(ValueError,match='another sibling'):
            r._reference(o,other,{slot['slot_id']:state})
    finally:o.close()
