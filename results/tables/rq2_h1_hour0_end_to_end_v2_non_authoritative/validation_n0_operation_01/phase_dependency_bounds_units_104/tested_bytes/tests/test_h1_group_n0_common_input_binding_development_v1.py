"""Explicit synthetic adapter/guard seams; no actual accepted RTS claim."""
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from threading import Lock
from types import SimpleNamespace as NS

import pytest

from experiments import h1_group_n0_common_input_binding_development_v1 as m
from tests.test_h1_selector_configuration_development_v1 import no_execution
from tests.test_h1_origin_current_information_development_v1 import scenario, supplied
from tests.test_h1_bootstrap_integration_development_v1 import example, setup as bootstrap_setup
from tests.test_h1_group_execution_roster_development_v1 import cached_declarations, declaration, roster


@dataclass(frozen=True)
class Decision:
    relative_hour: int = 0
    generation: int = 45

    @property
    def decision_bytes(self):return m.encode(dict(hour=self.relative_hour,generation=self.generation))
    @property
    def decision_identity(self):return m.bootstrap.digest(json.loads(self.decision_bytes))


@dataclass(frozen=True)
class Manifest:
    label: str = 'synthetic orchestration only'


@pytest.fixture
def evidence(tmp_path,monkeypatch):
    histories={};currents={};references={};normal_audits={};exact_audits={}
    for arm in ('network-only','CFE-only'):
        root=str(tmp_path/arm);normal=Decision()
        proof=dict(completed_hours=1,parent_head=m.bootstrap.digest([arm,'parent']),
                   evidence_identity=m.bootstrap.digest([arm,'evidence']))
        audit=dict(implementation='1'*64,decision_identity=normal.decision_identity,
            controller_header_sha256=m.bootstrap.digest([arm,'binding']),
            controller_terminal_sha256=m.bootstrap.digest([arm,'terminal']),
            normal_request_key='2'*64,normal_input_identity='3'*64,
            normal_before=dict(completed_hours=0,generation=0),normal_after=dict(completed_hours=1,generation=45),
            canonical_locks=[['cost',1]],parent_declaration=dict(root=root),historical_controller=proof,
            packet_audit_identity=m.bootstrap.digest([arm,'packet']),source_timestamp='synthetic timestamp',
            source_time_basis='synthetic hourly',child_head=m.bootstrap.digest([arm,'child']),
            child_archive_identity=m.bootstrap.digest([arm,'archive']),projection_identity=m.bootstrap.digest(['projection']),
            projection_payload_sha256=m.bootstrap.digest(['projection payload']))
        raw=m.bootstrap.historical.io.encode(audit)
        local=dict(controller_root=root,controller_binding_sha256=audit['controller_header_sha256'],
            controller_terminal_sha256=audit['controller_terminal_sha256'],audit_payload_sha256=sha256(raw).hexdigest(),
            historical_implementation=audit['implementation'],parent_head=proof['parent_head'],
            evidence_identity=proof['evidence_identity'])
        local.update({k:audit[k] for k in ('decision_identity','normal_request_key','child_head',
            'child_archive_identity','projection_identity','projection_payload_sha256')})
        references[arm]=dict(arm_id=arm,local_terminal=dict(head=m.bootstrap.digest([arm,'local']),body=local))
        histories[root]=m.bootstrap.historical.current._owned(
            m.bootstrap.historical.current.H1NormalAuditEnvelope,decision=normal,audit_payload=raw)
        decision=m.phase.source.normal._owned(m.phase.source.origin_join.CurrentDecision,
            normal=normal,outage_payload=m.encode(dict(active=None)))
        scientific=m.encode(dict(workload_exact=['1','5'],cfe=['2','5']))
        exact=dict(implementation_identity='4'*64,controller_binding_sha256=local['controller_binding_sha256'],
            controller_terminal_sha256=local['controller_terminal_sha256'],registry_identity='5'*64,completed_hours=1,
            normal_audit_payload={k:audit[k] for k in m.SHARED_NORMAL_FIELDS},
            decision_identity=decision.decision_identity,exogenous_scientific_identity=sha256(scientific).hexdigest(),
            registry_prefix_decision_identity='6'*64,source_action_audit_identity=m.bootstrap.digest([arm,'labels']),
            current_source_correspondence_checked=True,registry_action_and_cap_lookup_checked=True,
            exact_source_projection_checked=True)
        currents[root]=m.phase.source.normal._owned(m.phase.source.ExactSourceCurrent,
            prepared_current=NS(decision=decision),workload_exact=None,source_cfe_at_alpha_one_exact=None,
            exogenous_scientific_payload=scientific,source_observation_identity=m.bootstrap.digest([arm,'source']),
            source_projection_audit_payload=m.phase.source.io.encode(exact))
        normal_audits[root]=audit;exact_audits[root]=exact
    calls=[]
    def historical(root,**kw):
        calls.append(('H',root));assert kw['completed_hours']==1
        return histories[str(root)]
    def fresh(binding,hour,terminal):
        calls.append(('E',binding.root));assert hour==0 and terminal==binding.genesis_terminal_sha256
        return currents[binding.root]
    monkeypatch.setattr(m.bootstrap.historical,'prepare',historical)
    monkeypatch.setattr(m.bootstrap.historical,'implementation_identity',lambda:'1'*64)
    monkeypatch.setattr(m.phase.source,'implementation_identity',lambda:'4'*64)
    monkeypatch.setattr(m.phase,'_fresh',fresh)
    monkeypatch.setattr(m.phase,'_initial',lambda manifest,current:NS(scientific=dict(genesis='same')))
    monkeypatch.setattr(m.phase,'_request',lambda manifest,state,current:'7'*64)
    return NS(references=references,histories=histories,currents=currents,calls=calls,
              normal=normal_audits,exact=exact_audits)


@pytest.fixture
def guarded(evidence,monkeypatch,tmp_path):
    # Explicit orchestration seam. This does not certify a real retained roster.
    g=object.__new__(m.roster_api.GroupRoster)
    g._original_operation=Lock();g._direct=tuple(evidence.references)
    g._siblings={arm:dict(ordinal=i) for i,arm in enumerate(g._direct)}
    g.root=tmp_path/'synthetic_roster';g._journal=NS(head='8'*64)
    g._owner=NS(_study_binding_bytes=m.encode(dict(registry_declaration=dict(expected_registry_identity='5'*64))))
    attached={arm:dict(reference=ref,head=m.bootstrap.digest([arm,'attachment'])) for arm,ref in evidence.references.items()}
    available=dict(evidence.references);global_head='9'*64
    def check():
        if not g._original_operation.locked():raise ValueError('synthetic guard absent')
    g._check=check
    g._replay=lambda:(deepcopy(attached),deepcopy(available),global_head)
    def enter():
        if not g._original_operation.acquire(False):raise ValueError('synthetic operation active')
    g._enter=enter;g._leave=g._original_operation.release
    monkeypatch.setattr(m,'implementation_identity',lambda:'a'*64)
    monkeypatch.setattr(m.phase,'implementation_identity',lambda manifest:'b'*64)
    monkeypatch.setattr(m,'_manifest',lambda roster:(Manifest(),dict(audit='synthetic candidate')))
    return g,attached,available


def test_two_rounds_compare_science_and_preserve_distinct_audits(evidence,guarded):
    g,_,_=guarded;report=m.inspect(g)
    assert report['independent_N0_scientific_correspondence_checked']
    assert all(report[k] is False for k in m.FLAGS)
    assert report['canonical_arm']=='network-only' and report['reuse_edge'] is None
    assert [kind for kind,root in evidence.calls]==['H','E']*4
    assert report['arm_audits']['network-only']!=report['arm_audits']['CFE-only']
    assert not g._original_operation.locked()


@pytest.mark.parametrize('field',['audit_payload_sha256','historical_implementation','decision_identity',
    'normal_request_key','child_head','child_archive_identity','projection_identity','projection_payload_sha256',
    'parent_head','evidence_identity','controller_binding_sha256','controller_terminal_sha256'])
def test_retained_pin_mismatch_rejected(evidence,field):
    ref=deepcopy(evidence.references['network-only']);ref['local_terminal']['body'][field]='f'*64
    with pytest.raises(ValueError,match='retained terminal'):m._historical(ref)


@pytest.mark.parametrize('field',m.SHARED_NORMAL_FIELDS)
def test_shortened_audit_shared_fields_must_match(evidence,monkeypatch,field):
    ref=evidence.references['network-only'];root=ref['local_terminal']['body']['controller_root']
    current=evidence.currents[root];audit=deepcopy(evidence.exact[root]);audit['normal_audit_payload'][field]='changed'
    object.__setattr__(current,'source_projection_audit_payload',m.phase.source.io.encode(audit))
    h,n=m._historical(ref);binding=m.phase.SourceBinding(root,n['controller_header_sha256'],'5'*64,n['controller_terminal_sha256'])
    with pytest.raises(ValueError,match='correspondence'):m._joined(binding,ref,h,n)


@pytest.mark.parametrize('difference',['normal','current','exogenous','registry','state','request'])
def test_cross_arm_scientific_difference_rejects_whole_report(evidence,guarded,monkeypatch,difference):
    original=m._arm
    def changed(ref,*args):
        binding,science,audit=original(ref,*args)
        if ref['arm_id']=='CFE-only':
            key={'normal':'normal','current':'current_decision','exogenous':'exogenous',
                 'registry':'registry_prefix_decision_identity','state':'initial_state','request':'initial_request'}[difference]
            science[key]={'changed':True}
        return binding,science,audit
    monkeypatch.setattr(m,'_arm',changed)
    with pytest.raises(ValueError,match='across siblings'):m.inspect(guarded[0])
    assert not guarded[0]._original_operation.locked()


@pytest.mark.parametrize('target',['historical','exact','global','group','manifest','implementation'])
def test_round_bookends_reject_changes(evidence,guarded,monkeypatch,target):
    g,attached,available=guarded;original=m._arm;count=0;changed=False
    def arm(*args):
        nonlocal count,changed
        result=original(*args);count+=1
        if count==3:
            changed=True
            if target in ('historical','exact'):
                key='historical_audit' if target=='historical' else 'exact_current_audit'
                result[2][key]['round_fault']=True
            if target=='global':attached['network-only']['head']='c'*64
            if target=='group':g._journal.head='c'*64
        return result
    monkeypatch.setattr(m,'_arm',arm)
    if target=='implementation':monkeypatch.setattr(m,'implementation_identity',lambda:'c'*64 if changed else 'a'*64)
    if target=='manifest':monkeypatch.setattr(m,'_manifest',lambda roster:(Manifest('changed' if changed else 'synthetic orchestration only'),dict(audit='synthetic candidate')))
    with pytest.raises(ValueError,match='changed'):m.inspect(g)
    assert not g._original_operation.locked()


def test_missing_attachment_precedes_source_read(evidence,guarded):
    g,attached,_=guarded;attached.pop('CFE-only')
    with pytest.raises(ValueError,match='every direct'):m.inspect(g)
    assert evidence.calls==[] and not g._original_operation.locked()


def test_missing_registry_precedes_source_read(evidence,guarded):
    g,_,_=guarded;g._owner._study_binding_bytes=m.encode(dict(registry_declaration=None))
    with pytest.raises(ValueError,match='registry declaration'):m.inspect(g)
    assert evidence.calls==[]


def test_detached_input_is_not_an_entry_credential():
    with pytest.raises(ValueError,match='exact live'):m.inspect(dict(independent_N0_mapping_complete=True))


def test_real_roster_guard_and_manifest_reject_incomplete_before_source(
        bootstrap_setup,cached_declarations,monkeypatch):
    s=bootstrap_setup;o=s.open(declaration=declaration(s.declaration));g=roster(o,s)
    def denied(*args,**kw):raise AssertionError('incomplete roster reached historical source')
    monkeypatch.setattr(m.bootstrap.historical,'prepare',denied)
    try:
        with pytest.raises(ValueError,match='every direct'):m.inspect(g)
        assert not g._original_operation.locked() and not o._original_operation.locked()
        assert not list(g.root.glob('[0-9]*.json'))
        assert not list(o._global.root.glob('[0-9]*.json'))
    finally:g.close();o.close()


def test_real_adapter_payloads_join_despite_different_audit_schemas(scenario,monkeypatch):
    # Real historical.prepare and exact-current.prepare, synthetic accepted-prefix
    # seam below them. This proves API/schema composition, not actual RTS acceptance.
    from tests.test_rq2_objective_provenance_run_v1 import spec
    root,state,_,build,_=scenario
    load=m.phase.source.source.windows.load_source_window
    def complete_trace(kind,*args,**kw):
        value=deepcopy(load(kind,*args,**kw))
        value['chain']['chain_id']='explicit-synthetic-'+kind+'-chain'
        if kind=='workload':
            value['chain']['trace_identity_basis']=dict(source='explicit synthetic trace')
        value.pop('window_identity')
        value['window_identity']=m.phase.source.source.windows._hash(value)
        return value
    monkeypatch.setattr(m.phase.source.source.windows,'load_source_window',complete_trace)
    envelope,args=build()
    audit=json.loads(envelope.audit_payload);parent=audit['parent_declaration']
    parent.update(specification=asdict(spec()),limits=asdict(m.bootstrap.historical.history.replay.H1HourReplayLimits(3,100,500)))
    observation=m.phase.source.source.load_pinned_current(
        m.phase.source.origin_join.predecessor._coordinates(envelope,1)[3],root,config_path=parent['config_path'])
    before=m.phase.source.origin_join.predecessor._boundary(audit['normal_before'])
    packet=m.phase.source.source.h1.assemble_current_normal(observation.network,observation.row,observation.raw_workload,
        relative_hour=0,dc_bus=1,source_time_basis=observation.source_time_basis,before=before)
    projection=m.encode(dict(value=dict(canonical_locks=[])))
    captured=dict(packet=packet,after=m.phase.source.origin_join.predecessor._boundary(audit['normal_after']),count=3,
        result=NS(head='1'*64,archive_identity='2'*64,projection=NS(projection_identity='3'*64,payload=projection)))
    proof=dict(completed_hours=1,parent_head='4'*64,evidence_identity='5'*64,
        historical_parent_prefix_verified=True,historical_obligation_prefix_verified=True,historical_job_clock_prefix_verified=True)
    def replay(root_,**kw):
        assert str(root_)==str(root) and kw['completed_hours']==1
        kw['_observed'].setdefault('identities',{})
        return deepcopy(proof),dict(captured),dict(parent_declaration=deepcopy(parent))
    monkeypatch.setattr(m.bootstrap.historical,'_replay_prefix',replay)
    monkeypatch.setattr(m.bootstrap.historical,'_observe_sources',lambda *args:None)
    historic=m.bootstrap.historical.prepare(root,**{k:v for k,v in args.items() if k!='expected_registry_identity'})
    h=json.loads(historic.audit_payload)
    assert m.bootstrap.historical.io.encode(h)==historic.audit_payload
    assert m.encode(h)!=historic.audit_payload  # Journal framing adds a newline.
    local=dict(controller_root=str(root),controller_binding_sha256=args['expected_binding_sha256'],
        controller_terminal_sha256=args['expected_terminal_sha256'],audit_payload_sha256=sha256(historic.audit_payload).hexdigest(),
        historical_implementation=h['implementation'],parent_head=proof['parent_head'],evidence_identity=proof['evidence_identity'])
    local.update({k:h[k] for k in ('decision_identity','normal_request_key','child_head','child_archive_identity',
                                  'projection_identity','projection_payload_sha256')})
    ref=dict(local_terminal=dict(body=local));checked,normal=m._historical(ref)
    binding=m.phase.SourceBinding(str(root),args['expected_binding_sha256'],args['expected_registry_identity'],args['expected_terminal_sha256'])
    current,exact=m._joined(binding,ref,checked,normal)
    assert exact['normal_audit_payload']['schema']!=normal['schema']
    assert sha256(m.encode(exact['normal_audit_payload'])).hexdigest()!=local['audit_payload_sha256']
    assert current.prepared_current.decision.normal.decision_bytes==checked.decision.decision_bytes
    assert all(m.encode(exact['normal_audit_payload'][k])==m.encode(normal[k]) for k in m.SHARED_NORMAL_FIELDS)
    from tests.test_h1_selector_configuration_development_v1 import configuration
    from tests.test_h1_phase_manifest_binding_development_v1 import archive
    manifest=m.bootstrap.phase_manifest.prepare('training_ub',0,configuration(),archive()).manifest
    actual_binding,science,arm_audit=m._arm(ref,binding.registry_identity,manifest)
    assert actual_binding==binding
    assert len(science['initial_state']['lanes'])==3 and science['initial_request']
    assert arm_audit['historical_audit']==normal
