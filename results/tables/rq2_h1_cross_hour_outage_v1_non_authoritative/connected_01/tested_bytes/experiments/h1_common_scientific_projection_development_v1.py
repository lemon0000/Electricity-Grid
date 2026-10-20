"""DRAFT bytes-only science comparison for separately authenticated Common routes.

The caller must first authenticate its own typed result, execution receipt and
live observation. This module issues data, never a proof, owner or run authority.
The retained verifier3, protected verifier1 and active wrapper stay distinct.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType


SCHEMA = 'h1_common_scientific_projection_development_v1'
MAX_REPORT_BYTES = 8 * 1024**2
MAX_JSON_NODES = 1000000
MAX_JSON_DEPTH = 64
ROUTES = MappingProxyType({
    'genesis': ('h1_group_n0_common_input_binding_development_v9',
                'h1_phase_exact_source_current_development_v9'),
    'handoff': ('h1_group_n0_common_input_binding_development_v10',
                'h1_phase_exact_source_current_development_v10'),
})
FALSE_FIELDS = frozenset(('group_execution_ready','selector_producer_authorized',
    'N_reuse_verified','Rref_reuse_verified','resource_discounts_applied',
    'common_reference_input_verified','paired_owner_authenticated','resource_admission',
    'formal_execution_ready','formal_result','native_execution_authorized',
    'full_family_group_registry_complete','all_catalog_groups_enumerated',
    'detached_consumer_authenticated','persistent_common_owner_bound',
    'common_publication_verified','full_192_hour_execution_verified'))
BASE_REPORT_FIELDS = FALSE_FIELDS | frozenset(('schema','implementation','phase_implementation',
    'roster_root','roster_head','global_head','phase_manifest_candidate','arm_audits',
    'common_scientific_payload','common_scientific_identity','canonical_arm',
    'canonical_source_binding','independent_N0_scientific_correspondence_checked',
    'fresh_at_return_only','reuse_edge'))
SCIENCE_FIELDS = BASE_REPORT_FIELDS - {'schema','implementation'}
REPORT_FIELDS = BASE_REPORT_FIELDS | {'execution'}
EXECUTION_FIELDS = frozenset(('schema','active_source_identity','active_historical_verifier_schema',
    'active_historical_verifier_identity','session_identity','common_call','common_call_limit',
    'full_numerical_hour_replays','within_prefix_revalidations','cross_common_numerical_proof_reuses',
    'context_evaluations','registry_preparations','first_complete_common_proof_committed',
    'proof_cache_cleared','observation_closed','formal_result','resource_admission','native_execution_authorized'))
EXECUTION_ROLE_FIELDS = MappingProxyType({'genesis':frozenset(('consumer_scope',)),
    'handoff':frozenset(('handoff_common_sites',))})
EXECUTION_BINDING_FIELDS = frozenset(('projector_schema','projector_identity','shared_projection_sha256'))
OPERATION_SCHEMAS = MappingProxyType({'genesis':'h1_operation_historical_witness_development_v8',
    'handoff':'h1_operation_historical_witness_development_v9'})
ARM_FIELDS = frozenset(('reference','source_binding','historical_audit','exact_current_audit',
    'historical_decision_payload_sha256','current_decision_payload_sha256',
    'exogenous_payload_sha256'))
REFERENCE_FIELDS = frozenset(('arm_id','ordinal','obligation_sha256','slot_id','episode_root',
    'reuse_edge','claim','release','local_terminal','global_terminal'))
BINDING_FIELDS = frozenset(('root','binding_sha256','registry_identity','genesis_terminal_sha256'))
LOCAL_PINS = ('slot_id','claim_head','claim_proposal_id','global_release_head',
    'bootstrap_release_head','controller_ready_head','controller_binding_sha256',
    'controller_terminal_sha256','audit_payload_sha256','historical_implementation',
    'historical_verifier_identity','decision_identity','parent_head','evidence_identity',
    'normal_request_key','child_head','child_archive_identity','projection_identity',
    'projection_payload_sha256','exact_n0_topology_identity')
BOOTSTRAP_FALSE = frozenset(('formal_result','formal_execution_ready','resource_admission',
    'native_execution_authorized','full_study_registry_authenticated'))
LOCAL_LITERALS = MappingProxyType(dict(kind='normal_terminal',completed_hours=1,
    historical_verifier_schema='h1_historical_n0_verifier_development_v3',
    historical_validation_contract='h1_historical_n0_verifier_development_v3',
    outcome='accepted_N0_numerical_candidate',scratch_contents_audited=False,
    scratch_included_in_scientific_evidence=False,filesystem_allocation_bound_proven=False,
    exact_n0_topology_verified=True,retry_authorized=False,
    **{name:False for name in BOOTSTRAP_FALSE}))
COMPATIBILITY_COUNTS = MappingProxyType(dict(full_numerical_hour_replays=4,
    fresh_byte_context_revalidations=4,recomputed_on_revalidation=False,
    scope='predecessor_scientific_projection_only'))
SOURCE_EXECUTION_FIELDS = frozenset(('historical_verifier_schema','historical_verifier_identity',
    'full_numerical_hour_replays','fresh_byte_context_revalidations','recomputed_on_revalidation'))
CORE_FIELDS = frozenset(('schema','implementation_identity','completed_hours',
    'historical_verifier_schema','historical_verifier_identity','predecessor_scientific_schema',
    'full_numerical_hour_replays','fresh_byte_context_revalidations','recomputed_on_revalidation',
    'controller_binding_sha256','controller_terminal_sha256','historical_controller',
    'normal_audit_identity','normal_audit_payload','source_observation_identity','registry_identity',
    'source_observation_audit_payload','registry_audit_payload','registry_audit_identity',
    'registry_prefix_decision_identity','decision_identity','exogenous_scientific_identity',
    'source_action_audit_identity','origin_kind','source_cap_table_sha256','workload_projection',
    'source_cfe_at_alpha_one_exact','current_source_correspondence_checked',
    'registry_action_and_cap_lookup_checked','exact_source_projection_checked','policy_visible',
    'shared_observed_clock','accepted_real_RTS_root_integration_verified',
    'detached_consumer_authenticated','persistent_lane_owner_implemented','common_publication_verified',
    'full_192_hour_execution_verified','resource_admission','formal_execution_ready','formal_result',
    'native_execution_authorized'))
HISTORICAL_FIELDS = frozenset(('schema','implementation','decision_identity','parent_declaration',
    'controller_header_sha256','controller_terminal_sha256','normal_input_identity',
    'packet_audit_identity','source_timestamp','source_time_basis','child_head',
    'child_archive_identity','projection_identity','projection_payload_sha256','normal_request_key',
    'normal_before','normal_after','canonical_locks','completed_stages','policy_visible',
    'historical_controller','common_prefix_publication_verified','detached_consumer_authenticated',
    'reference_or_actual_ready','formal_execution_ready','formal_result','resource_admission',
    'native_execution_authorized'))


def _encode(value):
    # The report/journal encoder includes UTF-8 and a trailing newline.
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,
        allow_nan=False)+'\n').encode('utf-8')


def _source_encode(value):
    # Original historical/source audit bytes have no trailing newline.
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,
        allow_nan=False).encode('ascii')


def _digest(value):
    return sha256(_encode(value)).hexdigest()


def _pin(value):
    if type(value) is not str or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('exact projection SHA256 required')


def _keys(value, fields, label):
    if type(value) is not dict or set(value)!=set(fields):
        raise ValueError('exact '+label+' fields required')


def implementation_identity():
    return sha256(_source_encode([SCHEMA,sha256(Path(__file__).read_bytes()).hexdigest()])).hexdigest()


@dataclass(frozen=True)
class ProjectionContract:
    """Expected identities supplied by the already authenticated owning route."""
    role: str
    common_identity: str
    source_identity: str
    protected_source_identity: str
    protected_verifier_identity: str
    retained_verifier_identity: str
    historical_identity: str
    operation_verifier_identity: str
    projector_identity: str

    def __post_init__(self):
        if type(self.role) is not str or self.role not in ROUTES:
            raise ValueError('fixed Genesis or Handoff projection role required')
        for name in ('common_identity','source_identity','protected_source_identity',
                'protected_verifier_identity','retained_verifier_identity','historical_identity',
                'operation_verifier_identity','projector_identity'):
            _pin(getattr(self,name))


def _decode(raw):
    if type(raw) is not bytes or not 0<len(raw)<=MAX_REPORT_BYTES:
        raise ValueError('bounded immutable Common report bytes required')
    value=json.loads(raw)
    if _encode(value)!=raw:
        raise ValueError('canonical Common report encoding required')
    pending=[(value,0)];nodes=0
    while pending:
        item,depth=pending.pop();nodes+=1
        if depth>MAX_JSON_DEPTH or nodes>MAX_JSON_NODES:
            raise ValueError('Common projection graph bound exceeded')
        if type(item) is dict:pending.extend((x,depth+1) for x in item.values())
        elif type(item) is list:pending.extend((x,depth+1) for x in item)
        elif type(item) not in (str,int,float,bool,type(None)):
            raise ValueError('literal Common projection graph required')
    return value


def _reference(reference, arm, contract):
    _keys(reference,REFERENCE_FIELDS,'retained reference')
    if (reference['arm_id']!=arm or type(reference['ordinal']) is not int
            or reference['ordinal']<0 or reference['reuse_edge'] is not None
            or type(reference['episode_root']) is not str):
        raise ValueError('independent retained arm reference required')
    for name in ('obligation_sha256','slot_id'):_pin(reference[name])
    for name in ('claim','release','local_terminal','global_terminal'):
        _keys(reference[name],('head','body'),name+' reference');_pin(reference[name]['head'])
    local=reference['local_terminal']['body']
    _keys(local,set(LOCAL_PINS)|set(LOCAL_LITERALS)|{'controller_root',
        'legacy_compatibility_execution_metadata'},'Bootstrap4 local terminal')
    for name in LOCAL_PINS:_pin(local[name])
    separator='\\' if '\\' in reference['episode_root'] else '/'
    expected=dict(LOCAL_LITERALS,controller_root=reference['episode_root']+separator+'controller_non_authoritative',
        legacy_compatibility_execution_metadata=dict(COMPATIBILITY_COUNTS),
        **{name:local[name] for name in LOCAL_PINS})
    if (_encode(local)!=_encode(expected) or local['historical_verifier_identity']!=contract.retained_verifier_identity
            or local['historical_implementation']!=contract.historical_identity):
        raise ValueError('retained verifier3/Bootstrap4 lineage differs')
    claim=reference['claim']['body'];release=reference['release']['body']
    _keys(claim,('kind','slot_id','proposal','claim_proposal_id','bootstrap_attempt_head'),'claim')
    proposal=claim['proposal']
    _keys(proposal,('study','family','ordinal','slot_id','profile','roots','bootstrap_genesis',
        'phase_manifest_audit_identity'),'claim proposal')
    if (claim['kind']!='claim' or claim['slot_id']!=reference['slot_id']
            or claim['claim_proposal_id']!=_digest(proposal)
            or local['claim_proposal_id']!=claim['claim_proposal_id']
            or local['claim_head']!=reference['claim']['head']
            or local['global_release_head']!=reference['release']['head']
            or proposal['ordinal']!=reference['ordinal'] or proposal['slot_id']!=reference['slot_id']
            or proposal['roots']['controller']!=local['controller_root']):
        raise ValueError('retained claim and local terminal differ')
    _keys(release,{'kind','slot_id','claim_head','claim_proposal_id','bootstrap_release_head',
        'bootstrap_release_body_sha256','controller_ready_head'}|set(BOOTSTRAP_FALSE),'release')
    _pin(release['bootstrap_release_body_sha256'])
    expected_release=dict(kind='release_intent',slot_id=reference['slot_id'],claim_head=reference['claim']['head'],
        claim_proposal_id=claim['claim_proposal_id'],bootstrap_release_head=local['bootstrap_release_head'],
        bootstrap_release_body_sha256=release['bootstrap_release_body_sha256'],
        controller_ready_head=local['controller_ready_head'],**{name:False for name in BOOTSTRAP_FALSE})
    expected_global=dict(kind='normal_terminal',slot_id=local['slot_id'],claim_head=local['claim_head'],
        release_head=local['global_release_head'],bootstrap_terminal_head=reference['local_terminal']['head'],
        bootstrap_terminal_body_sha256=_digest(local),evidence_identity=local['evidence_identity'],
        outcome='accepted_N0_numerical_candidate',retry_authorized=False,
        **{name:False for name in BOOTSTRAP_FALSE})
    if _encode(release)!=_encode(expected_release) or _encode(reference['global_terminal']['body'])!=_encode(expected_global):
        raise ValueError('retained release/global terminal differs')
    return local


def _core_source(current, contract):
    if type(current) is not dict or 'predecessor_compatibility' not in current:
        raise ValueError('active exact-source wrapper required')
    compatibility=current['predecessor_compatibility']
    _keys(compatibility,('compatibility_payload_scope','compatibility_counts_describe_actual_execution',
        'schema','implementation_identity','payload_sha256','payload'),'protected-source compatibility')
    core=compatibility['payload'];_keys(core,CORE_FIELDS,'protected source audit')
    if (core['schema']!='h1_phase_exact_source_current_development_v2'
            or core['implementation_identity']!=contract.protected_source_identity
            or core['historical_verifier_schema']!='h1_historical_n0_verifier_development_v1'
            or core['historical_verifier_identity']!=contract.protected_verifier_identity
            or type(core['full_numerical_hour_replays']) is not int or core['full_numerical_hour_replays']!=4
            or type(core['fresh_byte_context_revalidations']) is not int or core['fresh_byte_context_revalidations']!=4
            or core['recomputed_on_revalidation'] is not False):
        raise ValueError('protected verifier1 compatibility contract differs')
    expected_compatibility=dict(compatibility_payload_scope='predecessor_projection_metadata_only',
        compatibility_counts_describe_actual_execution=False,schema=core['schema'],
        implementation_identity=contract.protected_source_identity,
        payload_sha256=sha256(_source_encode(core)).hexdigest(),payload=core)
    expected={name:value for name,value in core.items() if name not in SOURCE_EXECUTION_FIELDS}
    expected.update(schema=ROUTES[contract.role][1],implementation_identity=contract.source_identity,
        predecessor_compatibility=expected_compatibility)
    if _source_encode(current)!=_source_encode(expected):
        raise ValueError('active source wrapper and protected science differ')
    return core


def _science(report, contract):
    """Validate the complete declared science envelope before extraction."""
    if type(contract) is not ProjectionContract:
        raise TypeError('exact immutable projection contract required')
    contract.__post_init__()
    _keys(report,BASE_REPORT_FIELDS,'Common science envelope')
    if (report['schema']!=ROUTES[contract.role][0] or report['implementation']!=contract.common_identity
            or any(report[name] is not False for name in FALSE_FIELDS)
            or report['independent_N0_scientific_correspondence_checked'] is not True
            or report['fresh_at_return_only'] is not True or report['reuse_edge'] is not None
            or _digest(report['common_scientific_payload'])!=report['common_scientific_identity']):
        raise ValueError('own Common identity or science contract differs')
    for name in ('phase_implementation','roster_head','global_head','common_scientific_identity'):_pin(report[name])
    audits=report['arm_audits']
    if type(audits) is not dict or len(audits)!=3 or report['canonical_arm'] not in audits:
        raise ValueError('three independent arm audits and canonical arm required')
    projected={}
    for arm,audit in sorted(audits.items()):
        _keys(audit,ARM_FIELDS,'active arm audit')
        local=_reference(audit['reference'],arm,contract)
        binding=audit['source_binding'];_keys(binding,BINDING_FIELDS,'SourceBinding')
        if (binding['root']!=local['controller_root'] or binding['binding_sha256']!=local['controller_binding_sha256']
                or binding['genesis_terminal_sha256']!=local['controller_terminal_sha256']):
            raise ValueError('retained SourceBinding differs')
        _pin(binding['registry_identity'])
        historical=audit['historical_audit'];_keys(historical,HISTORICAL_FIELDS,'historical audit')
        if (historical['schema']!='h1_phase_historical_controller_development_v1'
                or historical['implementation']!=contract.historical_identity
                or sha256(_source_encode(historical)).hexdigest()!=local['audit_payload_sha256']
                or historical['controller_header_sha256']!=local['controller_binding_sha256']
                or historical['controller_terminal_sha256']!=local['controller_terminal_sha256']
                or any(historical[name]!=local[name] for name in ('decision_identity','normal_request_key',
                    'child_head','child_archive_identity','projection_identity','projection_payload_sha256'))):
            raise ValueError('retained historical science differs')
        for name in ('historical_decision_payload_sha256','current_decision_payload_sha256','exogenous_payload_sha256'):
            _pin(audit[name])
        core=_core_source(audit['exact_current_audit'],contract)
        if (core['controller_binding_sha256']!=binding['binding_sha256']
                or core['controller_terminal_sha256']!=binding['genesis_terminal_sha256']
                or core['registry_identity']!=binding['registry_identity']):
            raise ValueError('protected exact source and retained binding differ')
        projected[arm]=dict(audit,exact_current_audit=core)
    if report['canonical_source_binding']!=audits[report['canonical_arm']]['source_binding']:
        raise ValueError('canonical arm SourceBinding differs')
    science={name:report[name] for name in SCIENCE_FIELDS if name!='arm_audits'}
    science['arm_audits']=projected
    return _encode(dict(schema=SCHEMA,science=science))


def _execution(value,contract,*,bound):
    fields=EXECUTION_FIELDS | EXECUTION_ROLE_FIELDS[contract.role]
    _keys(value,fields | EXECUTION_BINDING_FIELDS if bound else fields,'own execution envelope')
    call,limit=value['common_call'],value['common_call_limit']
    if (type(call) is not int or type(limit) is not int or not 1<=call<=limit
            or limit not in ((2,3,15) if contract.role=='genesis' else (22,))):
        raise ValueError('fixed own execution call plan required')
    if (value['schema']!=ROUTES[contract.role][0]+'/execution_v1'
            or value['active_source_identity']!=contract.source_identity
            or value['active_historical_verifier_schema']!=OPERATION_SCHEMAS[contract.role]
            or value['active_historical_verifier_identity']!=contract.operation_verifier_identity):
        raise ValueError('own execution route identity differs')
    _pin(value['session_identity'])
    names=('full_numerical_hour_replays','within_prefix_revalidations',
        'cross_common_numerical_proof_reuses','context_evaluations','registry_preparations')
    expected=(24,24,0,96,12) if call==1 else (0,0,48,96,12)
    if (any(type(value[name]) is not int for name in names)
            or tuple(value[name] for name in names)!=expected
            or value['first_complete_common_proof_committed'] is not (call>1)
            or any(value[name] is not False for name in ('proof_cache_cleared','observation_closed',
                'formal_result','resource_admission','native_execution_authorized'))):
        raise ValueError('honest active Common work/proof/cleanup state required')
    if contract.role=='genesis':
        if value['consumer_scope']!='one_public_Genesis_method':
            raise ValueError('one Genesis method execution scope required')
    elif type(value['handoff_common_sites']) is not int or value['handoff_common_sites']!=22:
        raise ValueError('twenty-two Handoff observation sites required')
    if bound:
        if value['projector_schema']!=SCHEMA or value['projector_identity']!=contract.projector_identity:
            raise ValueError('own execution projector identity differs')
        _pin(value['shared_projection_sha256'])


def project(report_payload, contract):
    """Validate a full own report and return science bytes; this grants no authority."""
    if type(contract) is not ProjectionContract:
        raise TypeError('exact immutable projection contract required')
    contract.__post_init__()
    report=_decode(report_payload);_keys(report,REPORT_FIELDS,'active Common report')
    _execution(report['execution'],contract,bound=True)
    science=_science({name:report[name] for name in BASE_REPORT_FIELDS},contract)
    if sha256(science).hexdigest()!=report['execution']['shared_projection_sha256']:
        raise ValueError('own report and scientific projection binding differs')
    return science


def bind_execution(science_report_payload, execution_payload, contract):
    """Build only data bytes; the owning route must bind them in its real receipt."""
    if type(contract) is not ProjectionContract:
        raise TypeError('exact immutable projection contract required')
    contract.__post_init__()
    report=_decode(science_report_payload);science=_science(report,contract)
    execution=_decode(execution_payload);_execution(execution,contract,bound=False)
    execution.update(projector_schema=SCHEMA,projector_identity=contract.projector_identity,
        shared_projection_sha256=sha256(science).hexdigest())
    full=_encode(dict(report,execution=execution))
    if project(full,contract)!=science:
        raise ValueError('complete execution envelope changed the science projection')
    return full
