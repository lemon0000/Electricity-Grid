"""Fresh per-arm N0 science correspondence under the live roster guards.

Returned diagnostics are not owner, producer, publication or reuse credentials.
"""
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from experiments import h1_group_execution_roster_development_v2 as roster_api
from experiments import h1_phase_owner_development_v1 as phase

bootstrap = roster_api.bootstrap
encode = bootstrap.encode
SCHEMA = 'h1_group_n0_common_input_binding_development_v2'
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
        roster_api.implementation_identity(),phase.source.implementation_identity(),
        sha256(Path(phase.__file__).read_bytes()).hexdigest()])


@bootstrap._guard_N0_route
def _historical(reference):
    local = reference['local_terminal']['body']
    value = bootstrap._prepare_N0(local['controller_root'],
        expected_binding_sha256=local['controller_binding_sha256'],
        expected_terminal_sha256=local['controller_terminal_sha256'],completed_hours=1)
    if (value.verifier_identity!=local['historical_verifier_identity']
            or local['historical_verifier_schema']!=bootstrap.historical_verifier.VERIFIER_SCHEMA
            or local['full_numerical_hour_replays']!=value.full_numerical_hour_replays
            or local['fresh_byte_context_revalidations']!=value.fresh_byte_context_revalidations
            or local['recomputed_on_revalidation'] is not value.recomputed_on_revalidation):
        raise ValueError('retained historical verifier differs')
    audit = json.loads(value.audit_payload)
    direct = ('decision_identity','normal_request_key','child_head','child_archive_identity',
              'projection_identity','projection_payload_sha256')
    if (bootstrap.historical.io.encode(audit)!=value.audit_payload
            or sha256(value.audit_payload).hexdigest()!=local['audit_payload_sha256']
            or audit['implementation']!=local['historical_implementation']
            or audit['implementation']!=bootstrap.historical.implementation_identity()
            or audit['controller_header_sha256']!=local['controller_binding_sha256']
            or audit['controller_terminal_sha256']!=local['controller_terminal_sha256']
            or any(audit[k]!=local[k] for k in direct)
            or any(audit['historical_controller'][k]!=local[k] for k in ('parent_head','evidence_identity'))
            or audit['decision_identity']!=value.decision.decision_identity
            or value.decision.relative_hour!=0
            or type(audit['historical_controller']['completed_hours']) is not int
            or audit['historical_controller']['completed_hours']!=1):
        raise ValueError('fresh historical N0 differs from retained terminal')
    return value,audit


def _joined(binding,reference,historical,normal_audit):
    current = phase._fresh(binding,0,binding.genesis_terminal_sha256)
    if type(current) is not phase.source.ExactSourceCurrent:
        raise ValueError('internally prepared exact current required')
    audit = json.loads(current.source_projection_audit_payload)
    local = reference['local_terminal']['body']
    decision = current.prepared_current.decision
    if (phase.source.io.encode(audit)!=current.source_projection_audit_payload
            or audit['implementation_identity']!=phase.source.implementation_identity()
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


def _arm(reference,registry_identity,manifest):
    local = reference['local_terminal']['body']
    binding = phase.SourceBinding(local['controller_root'],local['controller_binding_sha256'],
                                  registry_identity,local['controller_terminal_sha256'])
    historical,normal = _historical(reference)
    current,exact = _joined(binding,reference,historical,normal)
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


def _prepare_locked(roster):
    """Private composition seam; caller must hold both original live guards."""
    if type(roster) is not roster_api.GroupRoster or not roster._original_operation.locked():
        raise ValueError('exact guarded live group roster required')
    roster._check()
    own = implementation_identity()
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
        roster._check()
        if (implementation_identity()!=own or phase.implementation_identity(manifest)!=phase_identity
                or encode(asdict(manifest))!=manifest_bytes
                or roster._journal.head!=group_head
                or replay and encode(roster._replay())!=original):
            raise ValueError('group N0 evidence or implementation changed')

    def round_():
        result={};bindings={};common=None
        for arm in sorted(roster._direct):
            check()
            binding,science,audit=_arm(attached[arm]['reference'],registry_identity,manifest)
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
    return manifest,bindings[canonical],report


def inspect(roster):
    """Recompute a diagnostic only; no caller envelope or detached input accepted."""
    if type(roster) is not roster_api.GroupRoster:
        raise ValueError('exact live group roster required')
    roster._enter()
    try:
        _,_,report=_prepare_locked(roster)
        return report
    finally:roster._leave()
