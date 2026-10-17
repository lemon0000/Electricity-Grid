"""Fresh historical N/outage/current exact exogenous join; not a lane owner."""
from dataclasses import asdict,dataclass
from fractions import Fraction as Q
from pathlib import Path
import json
import sys
import types

from experiments import h1_historical_n0_verifier_development_v1 as historical
from experiments import h1_phase_exact_source_current_development_v1 as predecessor
from experiments import h1_origin_current_information_development_v1 as origin_join

normal,source,registry,physical,io=(origin_join.normal,origin_join.source,origin_join.registry,
    origin_join.physical,origin_join.io)
SCHEMA='h1_phase_exact_source_current_development_v2'
PROJECTION_SCHEMA=predecessor.SCHEMA
CFE_RULE='source_cfe_at_alpha_one_from_current_power_cfe_call_fraction_v1'


def implementation_identity():
    return io.digest(io.encode([SCHEMA,historical.verifier_identity(),predecessor.implementation_identity(),origin_join.implementation_identity(),
        io.digest(Path(source.h1.workload_projection.__file__).read_bytes()),io.digest(Path(__file__).read_bytes())]))


def _ratio(value):return [str(value.numerator),str(value.denominator)]


@dataclass(frozen=True,init=False)
class ExactSourceCurrent(normal._Owned):
    prepared_current: origin_join.PreparedCurrent
    workload_exact: Q
    source_cfe_at_alpha_one_exact: Q
    exogenous_scientific_payload: bytes
    source_observation_identity: str
    source_projection_audit_payload: bytes

    @property
    def exogenous_scientific_identity(self):return io.digest(self.exogenous_scientific_payload)

    @property
    def source_projection_audit_identity(self):return io.digest(self.source_projection_audit_payload)


def _envelope(header,captured,proof):
    if any(proof.get(k) is not True for k in ('historical_parent_prefix_verified',
            'historical_obligation_prefix_verified','historical_job_clock_prefix_verified')):
        raise ValueError('fresh complete historical controller replay required')
    packet,after=captured['packet'],captured['after']
    decision=normal._decision(packet,after)
    audit=io.encode(dict(schema=PROJECTION_SCHEMA,parent_declaration=header['parent_declaration'],
        historical_controller=proof,decision_identity=decision.decision_identity,
        normal_before=asdict(packet.before),normal_after=asdict(after),normal_input_identity=packet.input_identity,
        packet_audit_identity=packet.audit_identity,source_timestamp=packet.source_timestamp,
        source_time_basis=packet.source_time_basis))
    return normal._owned(normal.H1NormalAuditEnvelope,decision=decision,audit_payload=audit)


def _project(observation,frame,packet):
    projection=source.h1.workload_projection.project_workload_power(observation.raw_workload,'250',decimal_places=12)
    if projection['status']!='projected':raise ValueError('business_input_unresolved: '+projection['reason'])
    if io.encode(projection)!=packet.workload_projection_payload:
        raise ValueError('exact source projection differs from accepted N packet')
    w=Q(*map(int,projection['projected_fraction_exact']))
    baseline=Q(str(frame.info.current.dc_baseline_mw))
    if baseline!=w*250 or baseline!=Q(str(projection['dc_baseline_mw'])):
        raise ValueError('business_input_unresolved: exact N baseline correspondence')
    field=json.loads(observation.audit_payload)['power_source_row']['cfe_call_fraction']
    if type(field) is not str:raise ValueError('source CFE decimal string required')
    cfe=Q(field)
    if not 0<=cfe<=1:raise ValueError('business_input_unresolved: CFE source domain')
    return w,cfe,projection


def _prepare(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours,expected_registry_identity,
             _check,_replay):
    """Accept root and external pins only; construct all source/physical inputs here."""
    if type(completed_hours) is not int or completed_hours!=1:
        raise ValueError('N0 exact-source witness requires one completed hour')
    historical.old.additional_content_bound(completed_hours)
    for pin in (expected_binding_sha256,expected_terminal_sha256,expected_registry_identity):io.pin(pin)
    own=implementation_identity();observed={}
    args=dict(expected_binding_sha256=expected_binding_sha256,expected_terminal_sha256=expected_terminal_sha256,
        completed_hours=completed_hours)
    _check()
    first,captured,header=_replay(root,**args,_observed=observed)
    _check()
    envelope=_envelope(header,captured,first)
    _,declaration,origin,current=origin_join.predecessor._coordinates(envelope,completed_hours)
    registry_args=dict(split=origin.split,raw_start=origin.power_raw_hour,hours=completed_hours,
        outage_seed=origin.outage_seed,expected_registry_identity=expected_registry_identity)
    prefix=registry.prepare(**registry_args)
    if prefix.audit['registry_identity']!=expected_registry_identity:raise ValueError('registry identity differs')
    observation=source.load_pinned_current(current,declaration['upstream_root'],config_path=declaration['config_path'])
    decision,frame,action=origin_join._join(envelope,prefix,observation,completed_hours=completed_hours)
    w,cfe,projection=_project(observation,frame,captured['packet'])
    scientific=io.encode(dict(schema=PROJECTION_SCHEMA,relative_hour=completed_hours-1,
        current_decision_identity=decision.decision_identity,workload_exact=_ratio(w),
        source_cfe_at_alpha_one_exact=_ratio(cfe),projection_rule=projection['projection_rule'],
        power_rule=projection['power_rule'],decimal_places=12,normalized_unit_mw='250',cfe_source_mapping_rule=CFE_RULE))
    _check()
    second,fresh,fresh_header=_replay(root,**args,_observed=observed)
    _check()
    repeated=_envelope(fresh_header,fresh,second)
    source.validate_pinned_current(observation,declaration['upstream_root'],expected_identity=observation.identity,
        config_path=declaration['config_path'])
    if (first!=second or envelope.audit_payload!=repeated.audit_payload
            or envelope.decision.decision_bytes!=repeated.decision.decision_bytes
            or registry.prepare(**registry_args)!=prefix or implementation_identity()!=own):
        raise ValueError('historical N, source, registry or implementation changed during exact join')
    # Validate the final source view against the same call-level observation.
    historical._observe_sources(observed['identities'],declaration)
    verified_historical_identity=_check()
    if implementation_identity()!=own:raise ValueError('implementation changed after final source observation')
    audit=io.encode(dict(schema=SCHEMA,implementation_identity=own,completed_hours=completed_hours,
        historical_verifier_schema=historical.VERIFIER_SCHEMA,historical_verifier_identity=verified_historical_identity,
        predecessor_scientific_schema=PROJECTION_SCHEMA,full_numerical_hour_replays=4,
        fresh_byte_context_revalidations=4,recomputed_on_revalidation=False,
        controller_binding_sha256=expected_binding_sha256,controller_terminal_sha256=expected_terminal_sha256,
        historical_controller=first,normal_audit_identity=envelope.audit_identity,
        normal_audit_payload=json.loads(envelope.audit_payload),
        source_observation_identity=observation.identity,registry_identity=expected_registry_identity,
        source_observation_audit_payload=json.loads(observation.audit_payload),
        registry_audit_payload=prefix.audit,
        registry_audit_identity=io.digest(io.encode(prefix.audit)),registry_prefix_decision_identity=prefix.decision_identity,
        decision_identity=decision.decision_identity,exogenous_scientific_identity=io.digest(scientific),
        source_action_audit_identity=physical._digest(action),origin_kind=prefix.audit['origin_kind'],
        source_cap_table_sha256=prefix.audit['cap_table_sha256'],workload_projection=projection,
        source_cfe_at_alpha_one_exact=_ratio(cfe),current_source_correspondence_checked=True,
        registry_action_and_cap_lookup_checked=True,exact_source_projection_checked=True,policy_visible=False,
        shared_observed_clock=False,accepted_real_RTS_root_integration_verified=False,
        detached_consumer_authenticated=False,persistent_lane_owner_implemented=False,common_publication_verified=False,
        full_192_hour_execution_verified=False,resource_admission=False,formal_execution_ready=False,
        formal_result=False,native_execution_authorized=False))
    if len(audit)>historical.binding.CAP:raise ValueError('exact source audit exceeds bounded record cap')
    prepared=normal._owned(origin_join.PreparedCurrent,decision=decision,frame=frame,source_origin=prefix.origin,
        source_action=action,audit_payload=audit)
    return normal._owned(ExactSourceCurrent,prepared_current=prepared,workload_exact=w,
        source_cfe_at_alpha_one_exact=cfe,exogenous_scientific_payload=scientific,
        source_observation_identity=observation.identity,source_projection_audit_payload=audit)


def _guard_prepare(operation):
    module=sys.modules[__name__]
    names=('historical','predecessor','origin_join','normal','source','registry','physical','io',
           'SCHEMA','PROJECTION_SCHEMA','CFE_RULE','_envelope','_project','_ratio','_prepare',
           'ExactSourceCurrent','implementation_identity')
    own=tuple((name,getattr(module,name)) for name in names)
    replay=historical._replay_prefix
    verifier_names=('_replay_prefix','verifier_identity','_observe_sources','legacy','witness',
                    'old','history','current','io','binding','bridge','base','_observe',
                    '_observe_prefix','_obligation_inventory','implementation_identity','VERIFIER_SCHEMA')
    verifier=tuple((name,getattr(historical,name)) for name in verifier_names)
    dispatch=historical.witness._dispatch_view
    dependencies=((source,('load_pinned_current','validate_pinned_current')),
        (registry,('prepare',)),(origin_join,('_join',)),
        (origin_join.predecessor,('_coordinates',)),(normal,('_owned','_decision')),
        (physical,('_digest',)),(io,('encode','digest','pin')),
        (source.h1.workload_projection,('project_workload_power',)),
        (historical.old,('additional_content_bound',)),
        (historical.history.replay.guard,('solver_calls_forbidden',)),
        (historical.witness,('_dispatch_view',)))
    direct=tuple((owner,name,getattr(owner,name)) for owner,fields in dependencies for name in fields)
    functions=[value for _,value in own+verifier]+[value for _,_,value in direct]
    codes=tuple((value,value.__code__,repr(value.__defaults__),repr(value.__kwdefaults__))
                for value in functions if type(value) is types.FunctionType)
    def fixed():
        if (module.prepare is not guarded
                or any(getattr(module,name) is not value for name,value in own)
                or any(getattr(historical,name) is not value for name,value in verifier)
                or any(getattr(owner,name) is not value for owner,name,value in direct)
                or any(value.__code__ is not code or repr(value.__defaults__)!=defaults
                       or repr(value.__kwdefaults__)!=keywords for value,code,defaults,keywords in codes)
                or historical.witness._dispatch_view is not dispatch):
            raise ValueError('exact-source verifier dispatch changed')
    def guarded(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours,expected_registry_identity):
        fixed()
        if type(completed_hours) is not int or completed_hours!=1:
            raise ValueError('N0 exact-source witness requires one completed hour')
        with historical.history.replay.guard.solver_calls_forbidden():
            baseline=dispatch(module)
            verifier_identity=historical.verifier_identity()
            def check():
                fixed()
                if dispatch(module)!=baseline or historical.verifier_identity()!=verifier_identity:
                    raise ValueError('exact-source verification context changed')
                return verifier_identity
            check()
            result=operation(root,expected_binding_sha256=expected_binding_sha256,
                expected_terminal_sha256=expected_terminal_sha256,completed_hours=completed_hours,
                expected_registry_identity=expected_registry_identity,_check=check,_replay=replay)
            check()
            return result
    return guarded


prepare=_guard_prepare(_prepare)
