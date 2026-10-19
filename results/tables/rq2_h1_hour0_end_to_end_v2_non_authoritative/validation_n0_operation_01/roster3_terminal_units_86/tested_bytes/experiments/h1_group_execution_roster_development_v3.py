"""DRAFT Bootstrap4 per-arm N0 correspondence under one live bootstrap guard.

This journal grants no producer, group execution or reuse capability. Its
complete state means only that all direct N0 references have been registered.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
from threading import Lock, get_ident

from experiments import h1_bootstrap_integration_development_v4 as bootstrap

encode = bootstrap.encode
SCHEMA = 'h1_group_execution_roster_development_v3'
FLAGS = dict(group_execution_ready=False, selector_producer_authorized=False,
    N_reuse_verified=False, Rref_reuse_verified=False, resource_discounts_applied=False,
    common_reference_input_verified=False, paired_owner_authenticated=False,
    resource_admission=False, formal_execution_ready=False, formal_result=False,
    native_execution_authorized=False,full_family_group_registry_complete=False,
    all_catalog_groups_enumerated=False)


def implementation_identity():
    return bootstrap.digest([SCHEMA, sha256(Path(__file__).read_bytes()).hexdigest(),
                             bootstrap.implementation_identity()])


def _canonical_ordinal(audit, selected_ordinal):
    siblings = audit['group']['siblings']
    classifications = {x['arm_id']:x['classification'] for x in audit['arm_classifications']}
    direct = {arm for arm,kind in classifications.items() if kind=='direct_shared_lane'}
    selected = next(x for x in siblings if x['ordinal']==selected_ordinal)
    if direct:
        if selected['arm_id'] not in direct:
            raise ValueError('bootstrap owner must be a direct sibling')
        return min(x['ordinal'] for x in siblings if x['arm_id'] in direct)
    if (selected['arm_id']!='joint-B6'
            or classifications[selected['arm_id']]!='pending_separate_B6_planning'
            or selected['disposition']!='unresolved_no_certificate'
            or any(classifications[x['arm_id']]!='proof_terminal'
                   or x['disposition'] not in bootstrap.phase_manifest.TERMINAL
                   for x in siblings if x['arm_id']!='joint-B6')):
        raise ValueError('header-only group requires unresolved B6 owner and proof-terminal siblings')
    return min(x['ordinal'] for x in siblings)


def _idle(owner):
    if owner._operation_nonce is not None:
        raise ValueError('bootstrap operation nonce active')


def _reference_keys(reference):
    return {('slot',reference['slot_id']),('episode',reference['episode_root']),
            *((key,reference[key]['head']) for key in
              ('claim','release','local_terminal','global_terminal'))}


def _candidate(owner):
    """Use the checked current header and freshly prepare the canonical sibling."""
    _idle(owner); owner._check()
    selected = owner._phase_candidate(owner.declaration)
    if selected is None: raise ValueError('phase manifest binding required')
    owner._check_phase_header()
    stored = json.loads(owner._bootstrap._header)['declaration']['phase_manifest_candidate']
    if encode(selected) != encode(stored): raise ValueError('current phase audit differs from header')
    audit = selected['audit']
    d = owner.declaration
    # A B6-only unresolved group is header-only. Fully proof-discharged groups
    # have no BootstrapOwner and remain represented by the closed binder.
    ordinal = _canonical_ordinal(audit,d.ordinal)
    prepared = bootstrap.phase_manifest.prepare(d.family,ordinal,d.selector_configuration,d.phase_archive)
    expected = dict(audit,ordinal=ordinal)
    if (prepared.audit_payload != encode(expected)
            or prepared.audit_identity != bootstrap.digest(expected)):
        raise ValueError('canonical sibling phase audit differs')
    owner._check()
    if encode(owner._phase_candidate(d)) != encode(selected):
        raise ValueError('phase audit changed during group preparation')
    owner._check_phase_header()
    _idle(owner)
    return dict(audit=expected,audit_identity=prepared.audit_identity)


def _retained_local(local, controller_root, verifier_identity):
    """Check terminal-bound verifier3 lineage, not a detached execution receipt."""
    if type(local) is not dict:
        raise ValueError('exact retained N0 terminal mapping required')
    if not set(bootstrap.N0_PINS).issubset(local):
        raise ValueError('retained N0 terminal pin fields missing')
    expected = bootstrap._N0_body(controller_root,
        {name: local[name] for name in bootstrap.N0_PINS})
    if (encode(local) != encode(expected)
            or local['historical_verifier_identity'] != verifier_identity):
        raise ValueError('retained Bootstrap4 N0 terminal lineage differs')


def _reference(owner, sibling, registry, verifier_identity):
    """Only a full fresh foreign replay can supply a reference for this arm."""
    ordinal = sibling['ordinal']
    mapping = owner._manifest.obligation(owner.declaration.family,ordinal)
    if encode(mapping['obligation_node']) != encode(sibling['obligation_node']):
        raise ValueError('sibling differs from symbolic obligation')
    slot = owner._manifest.resolve(owner.declaration.family,ordinal*192)
    if slot['kind'] != 'potential_N_slot': raise ValueError('direct lane has no N slot')
    state = registry.get(slot['slot_id'])
    if state is None or state['terminal'] is None: return None
    if state['release'] is None or state['local_terminal'] is None:
        raise ValueError('independent N0 terminal prefix incomplete')
    claim_head,claim = state['claim']; proposal = claim['proposal']
    episode = owner.study_root/'episodes'/sibling['obligation_sha256']
    roots = {k:str(episode/(k+'_non_authoritative')) for k in ('bootstrap','controller','owner','holder')}
    local_head,local = state['local_terminal']
    _retained_local(local, roots['controller'], verifier_identity)
    if (proposal['ordinal'] != ordinal or proposal['family'] != owner.declaration.family
            or proposal['slot_id'] != slot['slot_id'] or proposal['roots'] != roots
            or encode(proposal['study']) != owner._study_binding_bytes
            or local['controller_root'] != roots['controller'] or local['claim_head'] != claim_head
            or local['claim_proposal_id'] != claim['claim_proposal_id']
            or claim['claim_proposal_id'] != bootstrap.digest(proposal)
            or local['global_release_head'] != state['release'][0]
            or local['slot_id'] != slot['slot_id'] or local['completed_hours'] != 1
            or local['outcome'] != 'accepted_N0_numerical_candidate'
            or encode(state['terminal'][1]) != encode(bootstrap._global_N0_body(local_head,local))):
        raise ValueError('independent N0 reference belongs to another sibling')
    return dict(arm_id=sibling['arm_id'],ordinal=ordinal,obligation_sha256=sibling['obligation_sha256'],
        slot_id=slot['slot_id'],episode_root=str(episode),reuse_edge=None,
        claim=dict(head=claim_head,body=claim),release=dict(head=state['release'][0],body=state['release'][1]),
        local_terminal=dict(head=local_head,body=local),
        global_terminal=dict(head=state['terminal'][0],body=state['terminal'][1]))


class _RosterJournal(bootstrap._Journal):
    """Bootstrap storage protocol plus roster checks at its write boundaries."""
    def __init__(self,roster,*args,**kwargs):
        self._roster=self._original_roster=roster
        super().__init__(*args,**kwargs)

    def check(self):
        super().check()
        if self._roster is not self._original_roster: raise ValueError('roster journal owner changed')
        self._roster._check_live()


class GroupRoster:
    """Bounded append-only correspondence journal; exact live owner required."""
    def __init__(self, owner, *, create, expected_head=None, retain_head, max_record_bytes):
        if type(owner) is not bootstrap.BootstrapOwner:
            raise ValueError('exact live bootstrap owner required')
        _idle(owner)
        if (type(create) is not bool or type(max_record_bytes) is not int
                or not 1024<=max_record_bytes<=1024**2 or not callable(retain_head)):
            raise ValueError('exact group journal declaration required')
        if create and expected_head is not None: raise ValueError('create cannot adopt group head')
        if not create: bootstrap.storage._pin(expected_head)
        self._owner=self._original_owner=owner
        self._owner_guard=owner._original_operation
        self._pid,self._thread=os.getpid(),get_ident()
        self._operation=self._original_operation=Lock()
        self.closed=self.poisoned=False; self._journal=self._original_journal=None
        self._retain=self._original_retain=retain_head
        self._pending_observation=None
        self.max_record_bytes=max_record_bytes
        if owner._operation is not self._owner_guard or not self._owner_guard.acquire(False):
            raise ValueError('bootstrap operation active or replaced')
        try:
            self._implementation=implementation_identity()
            self._retained_verifier_identity=bootstrap.historical_verifier.verifier_identity()
            owner._replay()
            candidate=_candidate(owner)
            audit=candidate['audit']; group=audit['group']
            self._direct=tuple(x['arm_id'] for x in audit['arm_classifications']
                               if x['classification']=='direct_shared_lane')
            self._siblings={x['arm_id']:x for x in group['siblings']}
            self.root=bootstrap.local._path(owner.study_root/'groups_non_authoritative'/
                                            (group['group_identity']+'_non_authoritative'))
            self._declaration=encode(dict(schema=SCHEMA,study=json.loads(owner._study_binding_bytes),
                global_genesis=owner._global.genesis,phase_manifest_candidate=candidate,
                retained_historical_verifier=dict(schema=bootstrap.historical_verifier.VERIFIER_SCHEMA,
                    identity=self._retained_verifier_identity),
                implementation=self._implementation,max_record_bytes=max_record_bytes,
                max_events=max(1,len(self._direct)),maximum_attach_events=len(self._direct),
                bootstrap_addressable_groups_only=True,reuse_edge=None,**FLAGS))
            self._configuration=(self.root,max_record_bytes,self._direct,encode(self._siblings),self._declaration,
                self._retained_verifier_identity)
            raw=bootstrap._journal_header(self.root,json.loads(self._declaration),max(1,len(self._direct)),
                                          max_record_bytes,bootstrap.implementation_identity())
            if len(raw)>max_record_bytes: raise ValueError('group header exceeds journal byte cap')
            if encode(_candidate(owner))!=encode(candidate): raise ValueError('group inputs changed before creation')
            if implementation_identity()!=self._implementation: raise ValueError('group implementation changed')
            owner._check()
            _idle(owner)
            if create:
                self.root.parent.mkdir(exist_ok=True)
                bootstrap.local._path(self.root)
            self._journal=_RosterJournal(self,self.root,json.loads(self._declaration),
                max_events=max(1,len(self._direct)),max_record_bytes=max_record_bytes,
                create=create,expected_head=expected_head,retain_head=self._retain_group_head)
            self._original_journal=self._journal
            self._replay()
        except BaseException:
            self.close(); raise
        finally: self._owner_guard.release()

    def _check_live(self):
        implementation=implementation_identity()
        owner=self._owner
        _idle(owner)
        owner._check()
        if (self.closed or self.poisoned or (os.getpid(),get_ident())!=(self._pid,self._thread)
                or owner is not self._original_owner or owner._operation is not self._owner_guard
                or not self._owner_guard.locked() or self._retain is not self._original_retain
                or self._operation is not self._original_operation
                or self._journal is not self._original_journal
                or implementation!=self._implementation
                or (self.root,self.max_record_bytes,self._direct,encode(self._siblings),self._declaration,
                    self._retained_verifier_identity)!=self._configuration):
            raise ValueError('group live owner or configuration changed')

    def _check(self):
        self._check_live()
        self._journal.check()
        if (self._journal.cap!=self.max_record_bytes
                or self._journal._declaration!=self._declaration
                or encode(json.loads(self._journal._header)['declaration'])!=self._declaration):
            raise ValueError('group journal declaration changed')

    def _retain_group_head(self,root,before,after):
        expected=self._pending_observation
        if expected is None or encode(self._view())!=expected:
            raise ValueError('group observation changed before retention')
        result=self._retain(root,before,after)
        if encode(self._view())!=expected: raise ValueError('group observation changed during retention')
        return result

    def _view(self):
        self._check(); owner=self._owner
        candidate=_candidate(owner)
        if encode(candidate)!=encode(json.loads(self._declaration)['phase_manifest_candidate']):
            raise ValueError('group phase declaration changed')
        head=owner._global.head
        registry=owner._registry()
        available={arm:_reference(owner,self._siblings[arm],registry,self._retained_verifier_identity)
                   for arm in self._direct}
        self._check()
        if owner._global.head!=head: raise ValueError('global head changed during group observation')
        return available,head

    def _replay(self):
        available,global_head=self._view(); rows=self._journal.rows(); attached={};used=set()
        for head,body in rows:
            arm=body.get('arm_id')
            if type(arm) is not str or arm not in self._direct or arm in attached:
                raise ValueError('duplicate or non-direct group attachment')
            reference=available[arm]
            if reference is None or encode(body)!=encode(dict(kind='attach_independent_N0',
                    arm_id=arm,reference=reference,**FLAGS)):
                raise ValueError('group reference differs from fresh independent terminal')
            keys=_reference_keys(reference)
            if any(key in used for key in keys): raise ValueError('cross-arm group reference alias')
            used.update(keys);attached[arm]=dict(head=head,reference=reference)
        if self._view()!=(available,global_head) or self._journal.rows()!=rows:
            raise ValueError('group evidence changed during replay')
        return attached,available,global_head

    def _enter(self):
        _idle(self._original_owner)
        if (self.closed or self.poisoned or (os.getpid(),get_ident())!=(self._pid,self._thread)
                or self._owner is not self._original_owner or self._operation is not self._original_operation
                or self._owner._operation is not self._owner_guard):
            raise ValueError('group live owner or operation changed')
        if not self._operation.acquire(False): raise ValueError('group operation active')
        if not self._owner_guard.acquire(False):
            self._operation.release(); raise ValueError('bootstrap operation active')

    def _leave(self):
        self._owner_guard.release(); self._original_operation.release()

    def inspect(self):
        self._enter()
        try:
            attached,available,global_head=self._replay()
            audit=json.loads(self._declaration)['phase_manifest_candidate']['audit']
            entries=[]
            for classification in audit['arm_classifications']:
                arm=classification['arm_id']
                entries.append(dict(sibling=json.loads(encode(self._siblings[arm])),classification=classification['classification'],
                    attachment=attached.get(arm),independent_N0_available=available.get(arm) is not None,
                    reuse_edge=None))
            return dict(schema=SCHEMA,root=str(self.root),head=self._journal.head,global_head=global_head,
                retained_historical_verifier=dict(schema=bootstrap.historical_verifier.VERIFIER_SCHEMA,
                    identity=self._retained_verifier_identity),
                group_identity=audit['group']['group_identity'],entries=entries,
                independent_N0_mapping_complete=bool(self._direct) and len(attached)==len(self._direct),
                maximum_attach_events=len(self._direct),bootstrap_addressable_groups_only=True,
                fresh_at_return_only=True,reuse_edge=None,**FLAGS)
        finally:self._leave()

    def attach(self, arm_id, *, expected_head):
        self._enter()
        try:
            bootstrap.storage._pin(expected_head)
            if self._journal.head!=expected_head: raise ValueError('stale group head')
            attached,available,global_head=self._replay()
            if type(arm_id) is not str or arm_id not in self._direct:
                raise ValueError('direct sibling arm required')
            if arm_id in attached: raise ValueError('group sibling already attached')
            reference=available[arm_id]
            if reference is None: raise ValueError('independent pending_post_N terminal required')
            if any(_reference_keys(reference) & _reference_keys(entry['reference'])
                   for entry in attached.values()):
                raise ValueError('cross-arm group reference alias')
            body=dict(kind='attach_independent_N0',arm_id=arm_id,reference=reference,**FLAGS)
            self._journal.reserve(1)
            if self._view()!=(available,global_head): raise ValueError('group changed before attachment')
            self._pending_observation=encode((available,global_head))
            head=self._journal.append(body,expected_head=expected_head)
            fresh,after,after_global=self._replay()
            if (after!=available or after_global!=global_head
                    or fresh!={**attached,arm_id:dict(head=head,reference=reference)}):
                raise ValueError('group attachment readback differs')
            return head
        except BaseException:
            self.poisoned=True; raise
        finally:self._pending_observation=None;self._leave()

    def close(self):
        if (os.getpid(),get_ident())!=(self._pid,self._thread): raise ValueError('group close owner differs')
        if self.closed:return
        if not self._original_operation.acquire(False): raise ValueError('group operation active')
        try:
            self.closed=True
            if self._original_journal is not None:self._original_journal.close()
        finally:self._original_operation.release()
