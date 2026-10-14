"""Fresh enrollment N + approved outage registry join, before persistent ownership."""
from dataclasses import dataclass
import json
from pathlib import Path

from experiments import h1_current_outage_information_development_v1 as predecessor
from experiments import h1_origin_grid_step_development_v1 as physical
from experiments import h1_outage_registry_development_v1 as registry

normal, source, io = predecessor.normal, predecessor.source, predecessor.io
SCHEMA = 'h1_origin_current_information_development_v1'


def implementation_identity():
    return io.digest(io.encode([SCHEMA,normal.implementation_identity(),source.implementation_identity(),
        predecessor.implementation_identity(),registry.implementation_identity(),physical.implementation_identity(),
        io.digest(Path(__file__).read_bytes())]))


@dataclass(frozen=True,init=False)
class CurrentDecision(normal._Owned):
    normal: normal.H1CurrentInformation
    outage_payload: bytes

    @property
    def decision_bytes(self):
        return io.encode(dict(normal=json.loads(self.normal.decision_bytes),outage=json.loads(self.outage_payload)))

    @property
    def decision_identity(self):
        return io.digest(self.decision_bytes)


@dataclass(frozen=True,init=False)
class PreparedCurrent(normal._Owned):
    decision: CurrentDecision
    frame: physical.NormalFrame
    source_origin: registry.events.DisclosureState
    source_action: registry.FirstAction | registry.TransitionAction
    chronology_origin: bool
    audit_payload: bytes

    @property
    def audit_identity(self):
        return io.digest(self.audit_payload)


def _join(envelope,prefix,observation,*,completed_hours):
    """Private synthetic seam; public prepare supplies all freshly verified inputs."""
    audit,declaration,origin,current = predecessor._coordinates(envelope,completed_hours)
    if type(prefix) is not registry.Prefix or type(observation) is not source.H1PinnedObservation:
        raise ValueError('fresh typed registry/current source inputs required')
    t=completed_hours-1
    if (origin.config_sha256 != registry.catalog.CONFIG_SHA or observation.declaration != current
            or len(prefix.actions) != completed_hours or prefix.audit['hours'] != completed_hours
            or prefix.audit['completed_actions'] != completed_hours
            or prefix.audit['split'] != origin.split or prefix.audit['outage_seed'] != origin.outage_seed
            or prefix.audit['raw_start'] != origin.power_raw_hour
            or prefix.audit['raw_current_hours'] != list(range(origin.power_raw_hour,current.power_raw_hour+1))
            or prefix.audit['last_revealed_raw_hour'] != current.power_raw_hour
            or len(prefix.audit['current_rows']) != completed_hours):
        raise ValueError('registry prefix does not end at accepted N source progress')
    if prefix.decision_identity != registry.old.source._hash([registry.decision_view(a) for a in prefix.actions]):
        raise ValueError('registry decision projection differs')
    observed=json.loads(observation.audit_payload)
    if (prefix.audit['current_rows'][-1] != observed['power_source_row']
            or observed['power_package_manifest_sha256'] != registry.frozen.PACKAGE_SHA):
        raise ValueError('N and registry raw current power source differ')
    before,after=map(predecessor._boundary,(audit['normal_before'],audit['normal_after']))
    packet=source.h1.assemble_current_normal(observation.network,observation.row,observation.raw_workload,
        relative_hour=t,dc_bus=declaration['dc_bus'],source_time_basis=observation.source_time_basis,before=before)
    rebuilt=normal._decision(packet,after)
    if (packet.input_identity != audit['normal_input_identity']
            or rebuilt.decision_bytes != envelope.decision.decision_bytes
            or packet.source_timestamp != audit['source_timestamp']
            or packet.source_time_basis != audit['source_time_basis']):
        raise ValueError('current source does not reproduce accepted N input')
    frame=physical._frame(packet,after)
    network=physical._information(frame)
    physical._components(network,prefix.origin)
    units={u.uid:u for u in network.units}
    for a in prefix.actions:
        if type(a) is registry.TransitionAction:
            cap=a.step.repaired_generator_return_limit_mw
            if cap is not None and cap > units[a.step.ended.component.uid].maximum_power_mw:
                raise ValueError('registry repair cap exceeds N source nameplate')
    chronology=origin.power_raw_hour==0
    expected_kind='chronology_origin' if chronology else None
    if (chronology and prefix.audit['origin_kind'] != expected_kind
            or not chronology and prefix.audit['origin_kind'] not in (
                'existing_same_chain_boundary','generated_same_split_boundary')):
        raise ValueError('origin kind differs from source chronology')
    action=prefix.actions[-1]
    if action.relative_hour != t:
        raise ValueError('current action progress differs')
    if chronology and t==0:
        if type(action) is not registry.FirstAction or action.current_state != prefix.origin:
            raise ValueError('raw0 requires the registry first action')
    else:
        offset=0 if chronology else 1
        if (type(action) is not registry.TransitionAction or action.step.after.source_hour != t+offset
                or action.step.before.source_hour != t+offset-1):
            raise ValueError('current transition clock differs')
    decision=normal._owned(CurrentDecision,normal=envelope.decision,
        outage_payload=io.encode(registry.decision_view(action)))
    return decision,frame,action,chronology


def prepare(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours,expected_registry_identity):
    """No caller coordinates, cap, mode or detached action accepted. Fresh at return."""
    if type(completed_hours) is not int or not 1 <= completed_hours <= 168:
        raise ValueError('accepted enrollment progress must be one through 168')
    for pin in (expected_binding_sha256,expected_terminal_sha256,expected_registry_identity):
        registry.old.source._sha(pin)
    before=implementation_identity()
    args=dict(expected_binding_sha256=expected_binding_sha256,
        expected_terminal_sha256=expected_terminal_sha256,completed_hours=completed_hours)
    envelope=normal.prepare(root,**args)
    _,declaration,origin,current=predecessor._coordinates(envelope,completed_hours)
    registry_args=dict(split=origin.split,raw_start=origin.power_raw_hour,hours=completed_hours,
        outage_seed=origin.outage_seed,expected_registry_identity=expected_registry_identity)
    prefix=registry.prepare(**registry_args)
    if prefix.audit['registry_identity'] != expected_registry_identity:
        raise ValueError('returned registry identity differs')
    observation=source.load_pinned_current(current,declaration['upstream_root'],config_path=declaration['config_path'])
    decision,frame,action,chronology=_join(envelope,prefix,observation,completed_hours=completed_hours)
    repeated=normal.prepare(root,**args)
    source.validate_pinned_current(observation,declaration['upstream_root'],
        expected_identity=observation.identity,config_path=declaration['config_path'])
    if (repeated.audit_payload != envelope.audit_payload
            or repeated.decision.decision_bytes != envelope.decision.decision_bytes
            or registry.prepare(**registry_args) != prefix or implementation_identity() != before):
        raise ValueError('accepted N, registry or implementation changed during current join')
    audit=io.encode(dict(schema=SCHEMA,implementation_identity=before,completed_hours=completed_hours,
        controller_binding_sha256=expected_binding_sha256,controller_terminal_sha256=expected_terminal_sha256,
        normal_audit_identity=envelope.audit_identity,source_observation_identity=observation.identity,
        registry_identity=expected_registry_identity,registry_audit_identity=io.digest(io.encode(prefix.audit)),
        registry_prefix_decision_identity=prefix.decision_identity,decision_identity=decision.decision_identity,
        source_action_audit_identity=physical._digest(action),origin_kind=prefix.audit['origin_kind'],
        source_cap_table_sha256=prefix.audit['cap_table_sha256'],current_source_correspondence_checked=True,
        registry_action_and_cap_lookup_checked=True,policy_visible=False,accepted_root_integration_verified=False,
        detached_consumer_authenticated=False,persistent_lane_owner_implemented=False,common_publication_verified=False,
        full_192_hour_execution_verified=False,resource_admission=False,formal_execution_ready=False,
        formal_result=False,native_execution_authorized=False))
    return normal._owned(PreparedCurrent,decision=decision,frame=frame,source_origin=prefix.origin,
        source_action=action,chronology_origin=chronology,audit_payload=audit)
