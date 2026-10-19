"""Fresh per-arm N0 science correspondence under the live roster guards.

Returned diagnostics are not owner, producer, publication or reuse credentials.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import sys
import types

from experiments import h1_group_execution_roster_development_v5 as roster_api
from experiments import h1_phase_owner_development_v2 as phase
from experiments import h1_group_n0_common_input_binding_development_v2 as predecessor
from experiments import h1_phase_exact_source_current_development_v7 as source
from experiments import h1_operation_historical_witness_development_v6 as witness

bootstrap = roster_api.bootstrap
encode = bootstrap.encode
SCHEMA = 'h1_group_n0_common_input_binding_development_v10'
FLAGS = dict(roster_api.FLAGS, detached_consumer_authenticated=False,
             persistent_common_owner_bound=False, common_publication_verified=False,
             full_192_hour_execution_verified=False)
SHARED_NORMAL_FIELDS = ('decision_identity','parent_declaration','historical_controller',
    'normal_before','normal_after','normal_input_identity','packet_audit_identity',
    'source_timestamp','source_time_basis')
SCIENCE_NORMAL_FIELDS = ('normal_request_key','normal_input_identity',
                        'normal_before','normal_after','canonical_locks')
def implementation_identity():
    return bootstrap.digest([SCHEMA,sha256(Path(__file__).read_bytes()).hexdigest(),
        predecessor.implementation_identity(),source.implementation_identity(),witness.verifier_identity()])


@dataclass(frozen=True,init=False)
class PreparedCommonInput(source.normal._Owned):
    manifest: phase.Manifest
    source_binding: phase.SourceBinding
    predecessor_report_payload: bytes
    validation_report_payload: bytes
    execution_receipt: bytes
    _session_nonce: object


def _compatibility_report(report, *, common_identity, source_identity,
        predecessor_identity, predecessor_source_identity):
    """Reconstruct v2 science bytes; its work counts are compatibility only.

    The issuing preparation captures all four identities under its original
    guards. This pure projection cannot issue a result, lease or credential.
    """
    if report['schema'] != SCHEMA or report['implementation'] != common_identity:
        raise ValueError('active common report identity differs')
    fields = {'reference', 'source_binding', 'historical_audit', 'exact_current_audit',
        'historical_decision_payload_sha256', 'current_decision_payload_sha256',
        'exogenous_payload_sha256'}
    rebuilt = {}
    for arm, audit in report['arm_audits'].items():
        if set(audit) != fields:
            raise ValueError('exact current common arm shape required')
        current_audit = audit['exact_current_audit']
        old = current_audit['predecessor_compatibility']['payload']
        raw = source.io.encode(old)
        compatibility = dict(compatibility_payload_scope='predecessor_projection_metadata_only',
            compatibility_counts_describe_actual_execution=False,
            schema=source.predecessor.SCHEMA, implementation_identity=predecessor_source_identity,
            payload_sha256=source.io.digest(raw), payload=old)
        projected = {key: value for key, value in old.items() if key not in source._EXECUTION_FIELDS}
        projected.update(schema=source.SCHEMA, implementation_identity=source_identity,
            predecessor_compatibility=compatibility)
        if (encode(current_audit) != encode(projected)
                or old['schema'] != source.predecessor.SCHEMA
                or old['implementation_identity'] != predecessor_source_identity
                or old['historical_verifier_schema'] != bootstrap.historical_verifier.VERIFIER_SCHEMA
                or old['historical_verifier_identity'] != bootstrap.historical_verifier.verifier_identity()
                or (old['full_numerical_hour_replays'], old['fresh_byte_context_revalidations'],
                    old['recomputed_on_revalidation']) != (4, 4, False)):
            raise ValueError('current and predecessor source projections differ')
        historical = audit['historical_audit']
        historical_raw = bootstrap.historical.io.encode(historical)
        local = audit['reference']['local_terminal']['body']
        if (historical['schema'] != bootstrap.historical.SCHEMA
                or sha256(historical_raw).hexdigest() != local['audit_payload_sha256']):
            raise ValueError('retained historical projection differs')
        execution = dict(schema='h1_common_arm_shared_verification_v1',
            active_implementation_identity=predecessor_source_identity,
            active_historical_verifier_identity=old['historical_verifier_identity'],
            active_historical_verifier_schema=old['historical_verifier_schema'],
            historical_projection_schema=bootstrap.historical.SCHEMA,
            historical_projection_sha256=sha256(historical_raw).hexdigest(),
            exact_source_audit_sha256=sha256(raw).hexdigest(),
            full_numerical_hour_replays=4, fresh_byte_context_revalidations=4,
            recomputed_on_revalidation=False, projection_consumers=['historical', 'exact_source'],
            cross_call_reuse=False, formal_result=False)
        rebuilt[arm] = dict(audit, exact_current_audit=old, verification_execution=execution)
    return encode(dict(report, schema=predecessor.SCHEMA, implementation=predecessor_identity,
        arm_audits=rebuilt))


def _historical_payload(reference,decision,payload):
    local=reference['local_terminal']['body']
    audit = json.loads(payload)
    direct = ('decision_identity','normal_request_key','child_head','child_archive_identity',
              'projection_identity','projection_payload_sha256')
    if (bootstrap.historical.io.encode(audit)!=payload
            or sha256(payload).hexdigest()!=local['audit_payload_sha256']
            or audit['implementation']!=local['historical_implementation']
            or audit['implementation']!=bootstrap.historical.implementation_identity()
            or audit['controller_header_sha256']!=local['controller_binding_sha256']
            or audit['controller_terminal_sha256']!=local['controller_terminal_sha256']
            or any(audit[k]!=local[k] for k in direct)
            or any(audit['historical_controller'][k]!=local[k] for k in ('parent_head','evidence_identity'))
            or audit['decision_identity']!=decision.decision_identity
            or decision.relative_hour!=0
            or type(audit['historical_controller']['completed_hours']) is not int
            or audit['historical_controller']['completed_hours']!=1):
        raise ValueError('fresh historical N0 differs from retained terminal')
    return audit


def _joined(binding,reference,historical,normal_audit,*,current):
    if type(current) is not source.ExactSourceCurrent:
        raise ValueError('internally prepared exact current required')
    audit = json.loads(current.source_projection_audit_payload)
    local = reference['local_terminal']['body']
    decision = current.prepared_current.decision
    if (source.io.encode(audit)!=current.source_projection_audit_payload
            or audit['implementation_identity']!=source.implementation_identity()
            or audit['controller_binding_sha256']!=local['controller_binding_sha256']
            or audit['controller_terminal_sha256']!=local['controller_terminal_sha256']
            or audit['registry_identity']!=binding.registry_identity
            or type(audit['completed_hours']) is not int or audit['completed_hours']!=1
            or decision.normal.decision_bytes!=historical.decision.decision_bytes
            or any(encode(audit['normal_audit_payload'][k])!=encode(normal_audit[k])
                   for k in SHARED_NORMAL_FIELDS)
            or audit['decision_identity']!=decision.decision_identity
            or audit['exogenous_scientific_identity']!=current.exogenous_scientific_identity
            or any(audit[k] is not True for k in ('current_source_correspondence_checked',
                    'registry_action_and_cap_lookup_checked','exact_source_projection_checked'))):
        raise ValueError('historical N0 and exact current correspondence differs')
    return current,audit


def _arm(reference,registry_identity,manifest,*,session,ticket,arm):
    local=reference['local_terminal']['body']
    binding=phase.SourceBinding(local['controller_root'],local['controller_binding_sha256'],
        registry_identity,local['controller_terminal_sha256'])
    binding.__post_init__();source.io.pin(binding.genesis_terminal_sha256)
    owner=session._arm(arm,ticket)
    if owner._fixed_declaration[:5]!=(Path(binding.root),arm,binding.binding_sha256,
            binding.genesis_terminal_sha256,1):
        raise ValueError('source binding differs from authenticated independent arm')
    historical=owner.prepare(expected_registry_identity=registry_identity)
    if type(historical) is not source.CommonSourceBundle:
        raise TypeError('owned operation common source bundle required')
    execution=json.loads(historical.verification_execution_payload)
    expected_counts=(0,0,8) if session._reuse_active else (4,4,0)
    if (source.io.encode(execution)!=historical.verification_execution_payload
            or execution['active_validation_identity']!=source.implementation_identity()
            or execution['active_historical_verifier_identity']!=witness.verifier_identity()
            or execution['protected_core_identity']!=source.predecessor.implementation_identity()
            or (execution['full_numerical_hour_replays'],execution['within_prefix_revalidations'],
                execution['cross_common_numerical_proof_reuses'])!=expected_counts
            or execution['historical_execution']['declared_arm_label']!=arm
            or execution['historical_execution']['arm_label_authenticated'] is not True
            or execution['historical_execution']['controller_root_exact']!=str(Path(binding.root))
            or execution['historical_projection_sha256']!=sha256(historical.audit_payload).hexdigest()
            or execution['exact_source_audit_sha256']!=sha256(historical.current.source_projection_audit_payload).hexdigest()
            or local['historical_verifier_identity']!=bootstrap.historical_verifier.verifier_identity()
            or local['historical_verifier_schema']!=bootstrap.historical_verifier.VERIFIER_SCHEMA
            or local['full_numerical_hour_replays']!=4 or local['fresh_byte_context_revalidations']!=4
            or local['recomputed_on_revalidation'] is not False):
        raise ValueError('operation execution or retained historical compatibility contract differs')
    normal=_historical_payload(reference,historical.decision,historical.audit_payload)
    current,exact = _joined(binding,reference,historical,normal,current=historical.current)
    state = phase._initial(manifest,current)
    request = phase._request(manifest,state,current)
    scientific = dict(normal={k:normal[k] for k in SCIENCE_NORMAL_FIELDS},
        normal_decision=json.loads(historical.decision.decision_bytes),
        current_decision=json.loads(current.prepared_current.decision.decision_bytes),
        exogenous=json.loads(current.exogenous_scientific_payload),
        registry_prefix_decision_identity=exact['registry_prefix_decision_identity'],
        initial_state=state.scientific,initial_request=request)
    # Full audits remain distinct per arm and are also compared across fresh rounds.
    audit = dict(reference=reference,source_binding=asdict(binding),
        historical_audit=normal,exact_current_audit=exact,
        historical_decision_payload_sha256=sha256(historical.decision.decision_bytes).hexdigest(),
        current_decision_payload_sha256=sha256(current.prepared_current.decision.decision_bytes).hexdigest(),
        exogenous_payload_sha256=sha256(current.exogenous_scientific_payload).hexdigest())
    return binding,scientific,audit


def _manifest(roster):
    owner = roster._owner
    candidate = roster_api._candidate(owner)
    if encode(candidate)!=encode(json.loads(roster._declaration)['phase_manifest_candidate']):
        raise ValueError('group candidate differs from retained header')
    d = owner.declaration
    prepared = bootstrap.phase_manifest.prepare(d.family,candidate['audit']['ordinal'],
                                                d.selector_configuration,d.phase_archive)
    manifest = prepared.manifest
    if (prepared.audit_payload!=encode(candidate['audit'])
            or prepared.audit_identity!=candidate['audit_identity']
            or type(manifest) is not phase.Manifest
            or encode(asdict(manifest))!=encode(candidate['audit']['manifest'])
            or tuple(c.lane_id for c in manifest.lanes)!=tuple(sorted(
                bootstrap.phase_manifest.ARMS[arm] for arm in roster._direct))):
        raise ValueError('fresh nonempty typed group manifest required')
    manifest.__post_init__()
    return manifest,candidate


def _prepare_locked(session,ticket):
    """Private composition seam; caller must hold both original live guards."""
    session._check()
    roster=session._roster
    if type(roster) is not roster_api.GroupRoster or not roster._original_operation.locked():
        raise ValueError('exact guarded live group roster required')
    roster._check()
    own = implementation_identity()
    compatibility_identities = dict(common_identity=own, source_identity=source.implementation_identity(),
        predecessor_identity=predecessor.implementation_identity(),
        predecessor_source_identity=source.predecessor.implementation_identity())
    manifest,candidate = _manifest(roster)
    manifest_bytes = encode(asdict(manifest))
    phase_identity = phase.implementation_identity(manifest)
    attached,available,global_head = roster._replay()
    if not roster._direct or set(attached)!=set(roster._direct):
        raise ValueError('every direct sibling must have independent retained N0')
    group_head = roster._journal.head
    original = encode((attached,available,global_head))
    owner = roster._owner
    registry = json.loads(owner._study_binding_bytes)['registry_declaration']
    if registry is None:raise ValueError('bound outage registry declaration required')
    registry_identity = registry['expected_registry_identity']
    bootstrap.storage._pin(registry_identity)

    def check(*, replay=False):
        _FIXED();session._check();roster._check()
        if (ticket is not session._common_ticket or implementation_identity()!=own or phase.implementation_identity(manifest)!=phase_identity
                or encode(asdict(manifest))!=manifest_bytes
                or roster._journal.head!=group_head
                or replay and encode(roster._replay())!=original):
            raise ValueError('group N0 evidence or implementation changed')

    def round_():
        result={};bindings={};common=None
        for arm in sorted(roster._direct):
            check()
            binding,science,audit=_arm(attached[arm]['reference'],registry_identity,manifest,
                session=session,ticket=ticket,arm=arm)
            raw=encode(science)
            if common is not None and raw!=common:
                raise ValueError('independent N0 scientific inputs differ across siblings')
            common=raw;result[arm]=audit;bindings[arm]=binding
            check()
        check(replay=True)
        return common,encode(result),bindings

    first,audits,bindings=round_()
    second,repeated,repeated_bindings=round_()
    if first!=second or audits!=repeated or bindings!=repeated_bindings:
        raise ValueError('historical or exact current changed between group observations')
    fresh_manifest,fresh_candidate=_manifest(roster)
    if encode(asdict(fresh_manifest))!=manifest_bytes or encode(fresh_candidate)!=encode(candidate):
        raise ValueError('group manifest changed after source correspondence')
    check(replay=True)
    canonical = min(roster._direct,key=lambda arm:roster._siblings[arm]['ordinal'])
    report = dict(schema=SCHEMA,implementation=own,phase_implementation=phase_identity,
        roster_root=str(roster.root),roster_head=group_head,global_head=global_head,
        phase_manifest_candidate=candidate,arm_audits=json.loads(audits),
        common_scientific_payload=json.loads(first),common_scientific_identity=bootstrap.digest(json.loads(first)),
        canonical_arm=canonical,canonical_source_binding=asdict(bindings[canonical]),
        independent_N0_scientific_correspondence_checked=True,fresh_at_return_only=True,
        reuse_edge=None,**FLAGS)
    validation_payload=encode(report)
    predecessor_payload=_compatibility_report(report, **compatibility_identities)
    result=source.normal._owned(PreparedCommonInput,manifest=manifest,
        source_binding=bindings[canonical],predecessor_report_payload=predecessor_payload,
        validation_report_payload=validation_payload,
        execution_receipt=session._execution(ticket,validation_payload),_session_nonce=session._nonce)
    check(replay=True)
    return result


def prepare(session):
    """Return a typed result only after every complete common/return bookend."""
    if type(session) is not witness.GroupWitnessSession:
        raise TypeError('original operation-owned grouped witness session required')
    try:
        _FIXED(full=True)
        with witness.hour.prior.guard.solver_calls_forbidden():
            ticket=session._start_common()
            result=_prepare_locked(session,ticket)
            _FIXED(full=True);session._check()
            session._finish_common(ticket,result)
            _FIXED(full=True);session._check()
            return result
    except BaseException as error:
        _POISON(session,error)
        raise


def _install():
    module=sys.modules[__name__];expected=[];baseline=None
    owner_type=witness.GroupWitnessSession
    original_poison=owner_type._poison
    poison_call=types.FunctionType(original_poison.__code__,original_poison.__globals__,
        original_poison.__name__,original_poison.__defaults__,original_poison.__closure__)
    def poison(owner,error):
        if type(owner) is owner_type:
            try:poison_call(owner,error)
            except BaseException as failure:error.add_note('operation common poison: '+repr(failure))
    module._POISON=poison
    for owner in (module,predecessor,source,PreparedCommonInput):
        for name,value in tuple(vars(owner).items()):
            if isinstance(value,(types.FunctionType,types.ModuleType,type,property,staticmethod,classmethod)):
                state=(value.__code__,repr(value.__defaults__),repr(value.__kwdefaults__)) if type(value) is types.FunctionType else None
                expected.append((owner,name,value,state))
    dispatch=witness.prior_witness._dispatch_view
    def fixed(full=False):
        if (module._FIXED is not fixed or module._POISON is not poison or any(vars(owner).get(name) is not value
                or state is not None and (value.__code__,repr(value.__defaults__),repr(value.__kwdefaults__))!=state
                for owner,name,value,state in expected)):
            raise ValueError('definition-time operation common dispatch changed')
        if full:
            with witness.hour.prior.guard.solver_calls_forbidden():observed=dispatch(module)
            if observed!=baseline:
                raise ValueError('definition-time operation common project/source view changed')
    module._FIXED=fixed
    with witness.hour.prior.guard.solver_calls_forbidden():baseline=dispatch(module)
    return fixed


_FIXED=_install()

# A fixed definition-time handshake; never bind from a prepare call.
bootstrap._bind_common_registry_reader(sys.modules[__name__])
