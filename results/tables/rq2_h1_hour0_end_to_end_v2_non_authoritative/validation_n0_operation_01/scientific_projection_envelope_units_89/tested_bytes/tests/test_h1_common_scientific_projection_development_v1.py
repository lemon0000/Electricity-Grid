"""Data-only projection checks, not N0, numerical or live-owner evidence."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json

import pytest

from experiments import h1_common_scientific_projection_development_v1 as p
from experiments import h1_bootstrap_integration_development_v4 as bootstrap
from experiments import h1_raw_ingress_development_v1 as source_io


def pin(label):
    return sha256(label.encode()).hexdigest()


def execution(contract,call=1,limit=None):
    limit=limit or (15 if contract.role=='genesis' else 22)
    value=dict(schema=p.ROUTES[contract.role][0]+'/execution_v1',
        active_source_identity=contract.source_identity,
        active_historical_verifier_schema=p.OPERATION_SCHEMAS[contract.role],
        active_historical_verifier_identity=contract.operation_verifier_identity,
        session_identity=pin(contract.role+'session'),common_call=call,common_call_limit=limit,
        full_numerical_hour_replays=24 if call==1 else 0,
        within_prefix_revalidations=24 if call==1 else 0,
        cross_common_numerical_proof_reuses=0 if call==1 else 48,
        context_evaluations=96,registry_preparations=12,
        first_complete_common_proof_committed=call>1,proof_cache_cleared=False,
        observation_closed=False,formal_result=False,resource_admission=False,native_execution_authorized=False)
    if contract.role=='genesis':value['consumer_scope']='one_public_Genesis_method'
    else:value['handoff_common_sites']=22
    return value


def rebind(report,contract):
    science={name:value for name,value in report.items() if name!='execution'}
    own={name:value for name,value in report['execution'].items() if name not in p.EXECUTION_BINDING_FIELDS}
    return p.bind_execution(bootstrap.encode(science),bootstrap.encode(own),contract)


@pytest.fixture
def example(tmp_path):
    contract=p.ProjectionContract('genesis',*(pin(name) for name in ('common','source',
        'protected_source','protected_verifier','retained_verifier','historical','operation_verifier','projector')))
    audits={}
    for ordinal,arm in enumerate(('a','b','c')):
        episode=tmp_path/arm
        roots={name:str(episode/(name+'_non_authoritative'))
            for name in ('bootstrap','controller','owner','holder')}
        pins={name:pin(arm+name) for name in bootstrap.N0_PINS}
        pins['historical_verifier_identity']=contract.retained_verifier_identity
        pins['historical_implementation']=contract.historical_identity
        historical={name:{'data_only':name} for name in p.HISTORICAL_FIELDS}
        historical.update(schema=bootstrap.historical.SCHEMA,implementation=contract.historical_identity,
            controller_header_sha256=pins['controller_binding_sha256'],
            controller_terminal_sha256=pins['controller_terminal_sha256'])
        historical.update({name:pins[name] for name in ('decision_identity','normal_request_key',
            'child_head','child_archive_identity','projection_identity','projection_payload_sha256')})
        for name in ('policy_visible','common_prefix_publication_verified','detached_consumer_authenticated',
                'reference_or_actual_ready','formal_execution_ready','formal_result','resource_admission',
                'native_execution_authorized'):
            historical[name]=False
        historical['historical_controller']=dict(parent_head=pins['parent_head'],evidence_identity=pins['evidence_identity'])
        historical['completed_stages']=1
        pins['audit_payload_sha256']=sha256(source_io.encode(historical)).hexdigest()
        proposal=dict(study={'data_only':True},family='training_ub',ordinal=ordinal,
            slot_id=pins['slot_id'],profile={},roots=roots,bootstrap_genesis=pin(arm+'genesis'),
            phase_manifest_audit_identity=pin('phase_manifest'))
        pins['claim_proposal_id']=bootstrap.digest(proposal)
        claim=dict(kind='claim',slot_id=pins['slot_id'],proposal=proposal,
            claim_proposal_id=pins['claim_proposal_id'],bootstrap_attempt_head=pin(arm+'attempt'))
        local=bootstrap._N0_body(roots['controller'],pins)
        local_head=pin(arm+'local_head')
        release=dict(kind='release_intent',slot_id=pins['slot_id'],claim_head=pins['claim_head'],
            claim_proposal_id=pins['claim_proposal_id'],bootstrap_release_head=pins['bootstrap_release_head'],
            bootstrap_release_body_sha256=pin(arm+'release_body'),controller_ready_head=pins['controller_ready_head'],
            **bootstrap.FLAGS)
        reference=dict(arm_id=arm,ordinal=ordinal,obligation_sha256=pin(arm+'obligation'),
            slot_id=pins['slot_id'],episode_root=str(episode),reuse_edge=None,
            claim=dict(head=pins['claim_head'],body=claim),
            release=dict(head=pins['global_release_head'],body=release),
            local_terminal=dict(head=local_head,body=local),
            global_terminal=dict(head=pin(arm+'global_head'),body=bootstrap._global_N0_body(local_head,local)))
        binding=dict(root=roots['controller'],binding_sha256=pins['controller_binding_sha256'],
            registry_identity=pin('registry'),genesis_terminal_sha256=pins['controller_terminal_sha256'])
        core={name:{'data_only':name} for name in p.CORE_FIELDS}
        core.update(schema='h1_phase_exact_source_current_development_v2',
            implementation_identity=contract.protected_source_identity,completed_hours=1,
            historical_verifier_schema='h1_historical_n0_verifier_development_v1',
            historical_verifier_identity=contract.protected_verifier_identity,
            predecessor_scientific_schema='h1_phase_exact_source_current_development_v1',
            full_numerical_hour_replays=4,fresh_byte_context_revalidations=4,recomputed_on_revalidation=False,
            controller_binding_sha256=binding['binding_sha256'],
            controller_terminal_sha256=binding['genesis_terminal_sha256'],registry_identity=binding['registry_identity'])
        for name in ('policy_visible','shared_observed_clock','accepted_real_RTS_root_integration_verified',
                'detached_consumer_authenticated','persistent_lane_owner_implemented','common_publication_verified',
                'full_192_hour_execution_verified','resource_admission','formal_execution_ready','formal_result',
                'native_execution_authorized'):
            core[name]=False
        for name in ('current_source_correspondence_checked','registry_action_and_cap_lookup_checked',
                'exact_source_projection_checked'):
            core[name]=True
        audits[arm]=dict(reference=reference,source_binding=binding,historical_audit=historical,
            exact_current_audit=wrap(core,contract),historical_decision_payload_sha256=pin('historical_decision'),
            current_decision_payload_sha256=pin('current_decision'),exogenous_payload_sha256=pin('exogenous'))
    common=dict(data_only=True,label='Unicode '+chr(233))
    report=dict(schema=p.ROUTES[contract.role][0],implementation=contract.common_identity,
        phase_implementation=pin('phase'),roster_root=str(tmp_path/'roster_non_authoritative'),
        roster_head=pin('roster_head'),global_head=pin('global_head'),
        phase_manifest_candidate={'data_only':True},arm_audits=audits,
        common_scientific_payload=common,common_scientific_identity=bootstrap.digest(common),
        canonical_arm='a',canonical_source_binding=deepcopy(audits['a']['source_binding']),
        independent_N0_scientific_correspondence_checked=True,fresh_at_return_only=True,reuse_edge=None,
        **{name:False for name in p.FALSE_FIELDS})
    full=p.bind_execution(bootstrap.encode(report),bootstrap.encode(execution(contract)),contract)
    return json.loads(full),contract


def wrap(core,contract):
    current={name:value for name,value in core.items() if name not in p.SOURCE_EXECUTION_FIELDS}
    current.update(schema=p.ROUTES[contract.role][1],implementation_identity=contract.source_identity,
        predecessor_compatibility=dict(compatibility_payload_scope='predecessor_projection_metadata_only',
            compatibility_counts_describe_actual_execution=False,schema=core['schema'],
            implementation_identity=contract.protected_source_identity,
            payload_sha256=sha256(source_io.encode(core)).hexdigest(),payload=core))
    return current


def test_encoders_match_original_independent_functions():
    value={'unicode':chr(233),'nested':[False,None,4]}
    assert p._encode(value)==bootstrap.encode(value)
    assert p._source_encode(value)==source_io.encode(value)
    assert p._encode(value)!=p._source_encode(value)


def test_projection_preserves_all_declared_science(example):
    report,contract=example
    projected=json.loads(p.project(bootstrap.encode(report),contract))
    assert projected['schema']==p.SCHEMA
    science=projected['science']
    assert set(science)==p.SCIENCE_FIELDS
    for name in set(science)-{'arm_audits'}:
        assert science[name]==report[name]
    for arm,audit in report['arm_audits'].items():
        expected=dict(audit,exact_current_audit=audit['exact_current_audit']['predecessor_compatibility']['payload'])
        assert science['arm_audits'][arm]==expected


def test_two_authenticated_route_profiles_have_equal_science_and_different_reports(example):
    genesis,first=example
    second=replace(first,role='handoff',common_identity=pin('handoff_common'),source_identity=pin('handoff_source'),
        operation_verifier_identity=pin('handoff_operation'))
    handoff=deepcopy(genesis);handoff.update(schema=p.ROUTES['handoff'][0],implementation=second.common_identity)
    for audit in handoff['arm_audits'].values():
        audit['exact_current_audit']=wrap(audit['exact_current_audit']['predecessor_compatibility']['payload'],second)
    handoff['execution']=execution(second,call=7)
    handoff=json.loads(rebind(handoff,second))
    assert set(genesis['execution'])!=set(handoff['execution'])
    assert genesis['execution']['common_call_limit']!=handoff['execution']['common_call_limit']
    assert genesis['execution']['full_numerical_hour_replays']!=handoff['execution']['full_numerical_hour_replays']
    assert bootstrap.encode(genesis)!=bootstrap.encode(handoff)
    assert p.project(bootstrap.encode(genesis),first)==p.project(bootstrap.encode(handoff),second)
    with pytest.raises(ValueError):p.project(bootstrap.encode(handoff),first)


@pytest.mark.parametrize('name',sorted(p.SCIENCE_FIELDS))
def test_each_declared_science_field_changes_projection_or_is_rejected(example,name):
    report,contract=example;before=p.project(bootstrap.encode(report),contract)
    report[name]={'drift':name}
    try:after=p.project(rebind(report,contract),contract)
    except (ValueError,TypeError,KeyError):return
    assert after!=before


@pytest.mark.parametrize('name',sorted(p.ARM_FIELDS))
def test_each_arm_field_changes_projection_or_is_rejected(example,name):
    report,contract=example;before=p.project(bootstrap.encode(report),contract)
    report['arm_audits']['a'][name]={'drift':name}
    try:after=p.project(rebind(report,contract),contract)
    except (ValueError,TypeError,KeyError):return
    assert after!=before


@pytest.mark.parametrize('name',sorted(p.CORE_FIELDS))
def test_each_core_field_changes_projection_or_is_rejected(example,name):
    report,contract=example;before=p.project(bootstrap.encode(report),contract)
    core=deepcopy(report['arm_audits']['a']['exact_current_audit']['predecessor_compatibility']['payload'])
    core[name]={'drift':name};report['arm_audits']['a']['exact_current_audit']=wrap(core,contract)
    try:after=p.project(rebind(report,contract),contract)
    except (ValueError,TypeError,KeyError):return
    assert after!=before


@pytest.mark.parametrize('scope',('report','arm','source_wrapper','core','historical','reference','local','compatibility'))
@pytest.mark.parametrize('change',('missing','extra'))
def test_unknown_and_missing_fields_fail_closed(example,scope,change):
    report,contract=example;audit=report['arm_audits']['a'];current=audit['exact_current_audit']
    target={'report':report,'arm':audit,'source_wrapper':current,
        'core':current['predecessor_compatibility']['payload'],'historical':audit['historical_audit'],
        'reference':audit['reference'],'local':audit['reference']['local_terminal']['body'],
        'compatibility':current['predecessor_compatibility']}[scope]
    if change=='extra':target['unexpected']=False
    else:del target[next(iter(target))]
    with pytest.raises((ValueError,KeyError)):p.project(bootstrap.encode(report),contract)


@pytest.mark.parametrize('name',('common_identity','source_identity','protected_source_identity',
    'protected_verifier_identity','retained_verifier_identity','historical_identity',
    'operation_verifier_identity','projector_identity'))
def test_each_identity_layer_is_independently_validated(example,name):
    report,contract=example
    with pytest.raises(ValueError):p.project(bootstrap.encode(report),replace(contract,**{name:pin('foreign')}))


@pytest.mark.parametrize('change',('no_newline','duplicate_key','noncanonical','mutable','nan','depth','cap'))
def test_encoding_and_graph_bounds(example,change,monkeypatch):
    report,contract=example;raw=bootstrap.encode(report)
    if change=='no_newline':raw=raw[:-1]
    elif change=='duplicate_key':raw=raw.replace(b'{',b'{"schema":"duplicate",',1)
    elif change=='noncanonical':raw=json.dumps(report).encode()
    elif change=='mutable':raw=bytearray(raw)
    elif change=='nan':report['phase_manifest_candidate']=float('nan');raw=json.dumps(report).encode()+b'\n'
    elif change=='depth':monkeypatch.setattr(p,'MAX_JSON_DEPTH',2)
    else:monkeypatch.setattr(p,'MAX_REPORT_BYTES',len(raw)-1)
    with pytest.raises((ValueError,TypeError)):p.project(raw,contract)


def test_projection_has_no_filesystem_read_or_callback(example,monkeypatch):
    report,contract=example
    def deny(*args,**kwargs):raise AssertionError('data projection must not read files')
    monkeypatch.setattr(p.Path,'read_bytes',deny)
    assert type(p.project(bootstrap.encode(report),contract)) is bytes


@pytest.mark.parametrize('call,limit',((1,2),(2,2),(1,3),(3,3),(1,15),(15,15)))
def test_valid_different_Genesis_execution_reports_preserve_same_science(example,call,limit):
    report,contract=example;before=p.project(bootstrap.encode(report),contract)
    report['execution']=execution(contract,call=call,limit=limit)
    raw=rebind(report,contract)
    assert p.project(raw,contract)==before
    own=json.loads(raw)['execution']
    assert own['shared_projection_sha256']==sha256(before).hexdigest()
    assert own['projector_identity']==contract.projector_identity


@pytest.mark.parametrize('field',sorted(p.EXECUTION_FIELDS|p.EXECUTION_ROLE_FIELDS['genesis']|p.EXECUTION_BINDING_FIELDS))
def test_missing_or_changed_execution_fields_rejected(example,field):
    report,contract=example
    for change in ('missing','changed'):
        altered=deepcopy(report)
        if change=='missing':del altered['execution'][field]
        else:altered['execution'][field]=None
        with pytest.raises((ValueError,TypeError)):p.project(bootstrap.encode(altered),contract)


@pytest.mark.parametrize('field',('unexpected_execution','handoff_common_sites','closed','all_proofs_cleared'))
def test_unknown_execution_fields_are_rejected(example,field):
    report,contract=example;report['execution'][field]=True
    with pytest.raises(ValueError):p.project(bootstrap.encode(report),contract)


@pytest.mark.parametrize('field,value',(('common_call',True),('common_call',0),('common_call',16),
    ('common_call_limit',22),('full_numerical_hour_replays',True),('context_evaluations',95),
    ('proof_cache_cleared',True),('observation_closed',True),('first_complete_common_proof_committed',True),
    ('shared_projection_sha256','0'*64)))
def test_execution_counts_state_and_projection_binding_must_be_honest(example,field,value):
    report,contract=example;report['execution'][field]=value
    with pytest.raises(ValueError):p.project(bootstrap.encode(report),contract)


def test_unbound_science_envelope_is_not_a_complete_report(example):
    report,contract=example;del report['execution']
    with pytest.raises(ValueError):p.project(bootstrap.encode(report),contract)
