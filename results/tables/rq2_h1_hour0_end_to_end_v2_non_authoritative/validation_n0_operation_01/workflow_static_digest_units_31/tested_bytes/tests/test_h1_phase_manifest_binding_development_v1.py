"""Pinned declaration mapping and fail-closed boundaries; zero solver/Job."""
from copy import deepcopy
from dataclasses import asdict, replace
from fractions import Fraction
import json

import pytest

from experiments import h1_phase_manifest_binding_development_v1 as m
from tests.test_h1_selector_configuration_development_v1 import configuration


@pytest.fixture(autouse=True)
def deny_execution(monkeypatch):
    def denied(*a, **k):
        raise AssertionError('declaration reached execution')
    monkeypatch.setattr(m.configuration.inspector.bridge.capture.old.provenance.adapter, 'create_solver', denied)
    monkeypatch.setattr(m.configuration.inspector.bridge, '_run_stage', denied)
    monkeypatch.setattr(m.configuration.inspector.bridge.capture, 'StageCapture', denied)
    monkeypatch.setattr(m.configuration.process, 'normal_task_child', denied)


@pytest.fixture(scope='module')
def projection():
    return m.group.prepare('training_ub', 0)


def archive(w=0):
    count = 576+2*w
    return m.ArchiveCapacityDeclaration(count, 2**20, count*2**20, w)


def test_fresh_pinned_binding_and_all_obligations():
    c=configuration(); a=archive(2)
    result=m.prepare('training_ub',0,c,a)
    audit=json.loads(result.audit_payload)
    assert result.audit_identity==m.io.digest(result.audit_payload)
    assert len(audit['group']['siblings'])==4
    assert {x['classification'] for x in audit['arm_classifications']}=={'direct_shared_lane','pending_separate_B6_planning'}
    manifest=result.manifest
    assert tuple(x.lane_id for x in manifest.lanes)==('cfe_only_shared','joint_correct_shared','network_only_shared')
    assert manifest.accounting_period_id==audit['group']['accounting_period_id']
    for lane in manifest.lanes:
        assert lane.policy.committed_capacity==0
        assert lane.mechanism.alpha==Fraction(1,100)
        assert lane.mechanism.flexible_fraction==Fraction(1,20)
        assert lane.policy.capacity_declaration_id in audit['group']['capacity_declaration_ids'].values()
        assert dict(lane.envelope)['recovery_efficiency']==.85
    assert audit['selector_configuration']['configuration']['network_sha256']==c.network_sha256
    assert audit['archive_derivation']['conditional_required_events']==580
    assert audit['archive_derivation']['alternate_witness_limit_enforced'] is False
    assert audit['archive_derivation']['full_path_archive_sufficiency_proven'] is False
    for key in ('executable_manifest','resource_admission','formal_result','formal_execution_ready',
                'native_execution_authorized','owner_consumption_authorized','group_obligations_complete'):
        assert audit[key] is False


def test_proof_dispositions_and_empty_roster_preserve_classification(projection):
    g=deepcopy(projection)
    for sibling,disposition in zip(g['siblings'], sorted(m.TERMINAL)*2):
        sibling['disposition']=disposition
        sibling['missing_dependency']=None
    lanes,classes=m._lanes(g)
    assert lanes==()
    assert len(classes)==4 and all(x['classification']=='proof_terminal' for x in classes)


@pytest.mark.parametrize('field,value', [('candidate_capacity','1/3'),('candidate_capacity',True),
    ('candidate_capacity','-1'),('candidate_capacity','2')])
def test_capacity_cannot_be_rounded_or_bool(projection,field,value):
    g=deepcopy(projection);g[field]=value;g['coordinate']['capacity']=value
    with pytest.raises(ValueError):m._lanes(g)


@pytest.mark.parametrize('mutation', ['missing','duplicate','disposition'])
def test_obligation_inventory_fail_closed(projection,mutation):
    g=deepcopy(projection)
    if mutation=='missing':g['siblings'].pop()
    elif mutation=='duplicate':g['siblings'][-1]=g['siblings'][0]
    else:g['siblings'][0]['disposition']='unknown'
    with pytest.raises(ValueError):m._lanes(g)


@pytest.mark.parametrize('field,value', [('max_events',575),('max_events',1000000),
    ('max_events',True),('max_event_bytes',0),('max_event_bytes',True),
    ('max_archive_bytes',576*2**20-1),('reserved_alternate_witnesses',1),
    ('reserved_alternate_witnesses',True),('reserved_alternate_witnesses',-1)])
def test_archive_capacity_bounds(field,value):
    with pytest.raises(ValueError):replace(archive(),**{field:value})


def test_record_envelope_exact_base64_oracle():
    from base64 import b64encode
    c=configuration();ids=('cfe_only_shared','network_only_shared')
    record=b64encode(b'x'*c.limits.max_record_bytes).decode('ascii')
    value=dict(reference=[record]*3,actual={k:[record]*2 for k in ids})
    assert m._record_reservation(c,ids)==len(m.owner.encode(value))


@pytest.mark.parametrize('family,ordinal', [('holdout',0),('training_lb',0),('training_b6_actual',0),
    ('training_ub',True),('training_ub',-1)])
def test_other_families_do_not_become_actual(family,ordinal):
    with pytest.raises(ValueError):m.prepare(family,ordinal,configuration(),archive())


def test_tampered_pinned_group_is_rejected(monkeypatch,projection):
    g=deepcopy(projection);g['siblings'].pop()
    monkeypatch.setattr(m.group,'prepare',lambda *a:g)
    with pytest.raises(ValueError,match='pinned obligation projection'):
        m.prepare('training_ub',0,configuration(),archive())


def test_implementation_bookend_rejects_drift(monkeypatch,projection):
    monkeypatch.setattr(m.group,'prepare',lambda *a:deepcopy(projection))
    calls=iter(('a'*64,'b'*64))
    monkeypatch.setattr(m,'_implementation',lambda c:next(calls))
    with pytest.raises(ValueError,match='changed during preparation'):
        m.prepare('training_ub',0,configuration(),archive())


def test_event_declaration_must_hold_saved_record_envelope(monkeypatch,projection):
    monkeypatch.setattr(m.group,'prepare',lambda *a:deepcopy(projection))
    with pytest.raises(ValueError,match='record envelope'):
        m.prepare('training_ub',0,configuration(),m.ArchiveCapacityDeclaration(576,1,576,0))


@pytest.mark.parametrize('section', [None,'mechanism','policy','envelope'])
@pytest.mark.parametrize('change', ['extra','missing'])
def test_scientific_inventory_fail_closed(projection,section,change):
    g=deepcopy(projection);value=g['known_scientific_fields']
    if section is not None:value=value[section]
    if change=='extra':value['new_scientific_parameter']='1'
    else:value.pop(next(iter(value)))
    with pytest.raises(ValueError,match='inventories'):m._lanes(g)


@pytest.mark.parametrize('key,value', [('family','holdout'),('capacity_is_feasible_certificate',True),
    ('execution_lanes',[]),('audit_labels_are_policy_inputs',True),('family_dependency','other'),
    *((key,True) for key in m.group.FLAGS)])
def test_group_semantic_claims_fail_closed(projection,key,value):
    g=deepcopy(projection);g[key]=value
    with pytest.raises(ValueError,match='semantic boundaries'):m._lanes(g)


@pytest.mark.parametrize('terminal', [False,True])
def test_disposition_dependency_must_correspond(projection,terminal):
    g=deepcopy(projection);s=g['siblings'][0]
    if terminal:s['disposition']='not_scheduled_due_to_parent_cell_proof'
    else:s['missing_dependency']=None
    with pytest.raises(ValueError,match='dependency differs'):m._lanes(g)


def test_real_nonzero_capacity_mixed_proof_group_complete_mapping():
    result=m.prepare('training_ub',11832353,configuration(),archive())
    audit=json.loads(result.audit_payload);g=audit['group'];manifest=result.manifest
    assert len(manifest.lanes)==1
    lane=manifest.lanes[0]
    assert lane.lane_id==lane.policy.arm_id=='network_only_shared'
    assert lane.policy.committed_capacity==.01
    assert lane.policy.capacity_declaration_id==g['capacity_declaration_ids']['network-only']
    fixed=g['known_scientific_fields'];p=fixed['policy'];e=fixed['envelope'];mechanism=fixed['mechanism']
    assert lane.mechanism==m.owner.business.Mechanism(Fraction(mechanism['alpha']),
        Fraction(mechanism['flexible_fraction']),Fraction(mechanism['recovery_headroom_coefficient']),
        Fraction(mechanism['normalized_unit_mw']))
    assert {key:Fraction(str(getattr(lane.policy,key))) for key in
        ('minimum_event_power','curtailment_ramp_per_hour','response_time_hours','maximum_recovery_power')}=={
        'minimum_event_power':Fraction(p['minimum_event_power']),
        'curtailment_ramp_per_hour':Fraction(p['curtailment_up_ramp_per_hour']),
        'response_time_hours':Fraction(p['response_time_hours']),
        'maximum_recovery_power':Fraction(p['maximum_recovery_power'])}
    assert lane.policy.recovery_decimal_places==p['recovery_decimal_places']==12
    assert tuple(key for key,_ in lane.envelope)==('maximum_event_count','maximum_event_duration_hours',
        'minimum_recovery_hours','normalized_debt_limit','normalized_energy_budget',
        'recovery_efficiency','time_step_hours')
    assert {key:Fraction(str(value)) for key,value in lane.envelope}=={key:Fraction(value) for key,value in e.items()}
    assert type(dict(lane.envelope)['maximum_event_count']) is int
    assert manifest.accounting_period_id==g['accounting_period_id']
    assert m.owner.encode(audit['manifest'])==m.owner.encode(asdict(manifest))
    assert len(g['siblings'])==4
    for sibling,classified in zip(g['siblings'],audit['arm_classifications']):
        assert sibling['arm_id']==classified['arm_id']
        assert classified['classification']==('direct_shared_lane' if sibling['arm_id']=='network-only' else 'proof_terminal')
        assert sibling['missing_dependency']==('named_causal_policy_full_training_witness_missing' if sibling['arm_id']=='network-only' else None)
