"""Bind current outage information to a freshly replayed accepted N prefix.

Development correspondence only: no persistent Rref/A owner or publication.
The public entry accepts roots and external pins, never a detached Prefix.
"""
from dataclasses import asdict, dataclass
import json
from pathlib import Path

from experiments import h1_current_grid_information_development_v1 as normal
from experiments import h1_outage_source_development_v1 as outage

io = normal.io
source = normal.binding.snapshot.old.binding
SCHEMA = 'h1_current_outage_information_development_v1'


def implementation_identity():
    return io.digest(io.encode([SCHEMA, normal.implementation_identity(),
        outage.implementation_identity(), source.implementation_identity(),
        io.digest(Path(__file__).read_bytes())]))


@dataclass(frozen=True, init=False)
class CurrentEnvironment(normal._Owned):
    normal: normal.H1CurrentInformation
    outage: outage.events.DisclosureStep

    @property
    def decision_bytes(self):
        return io.encode(asdict(self))

    @property
    def decision_identity(self):
        return io.digest(self.decision_bytes)


@dataclass(frozen=True, init=False)
class EnvironmentEnvelope(normal._Owned):
    decision: CurrentEnvironment
    audit_payload: bytes


def _coordinates(envelope, completed_hours):
    if type(envelope) is not normal.H1NormalAuditEnvelope:
        raise ValueError('fresh normal audit envelope required')
    audit = json.loads(envelope.audit_payload)
    if (envelope.decision.relative_hour != completed_hours-1
            or audit['normal_before']['completed_hours'] != completed_hours-1
            or audit['normal_after']['completed_hours'] != completed_hours
            or audit['decision_identity'] != envelope.decision.decision_identity):
        raise ValueError('normal progress and decision differ')
    declaration = audit['parent_declaration']
    origin = source.H1SourceDeclaration(**declaration['origin'])
    current = source.H1SourceDeclaration(origin.split, origin.power_raw_hour+completed_hours-1,
        origin.workload_raw_hour+completed_hours-1, origin.outage_seed, origin.config_sha256)
    return audit, declaration, origin, current


def _boundary(value):
    fields = dict(value)
    fields['units'] = tuple(tuple(row) for row in fields['units'])
    return normal.source._owned(normal.source.H1NormalBoundary, **fields)


def _join(envelope, prefix, observation, *, completed_hours, protocol):
    """Private synthetic seam; public prepare owns all three fresh inputs."""
    audit, declaration, origin, current = _coordinates(envelope, completed_hours)
    if type(prefix) is not outage.Prefix or type(observation) is not source.H1PinnedObservation:
        raise ValueError('source preparation types differ')
    if observation.declaration != current or len(prefix.steps) != completed_hours:
        raise ValueError('outage prefix must end exactly at accepted N progress')
    if (prefix.audit['split'] != origin.split
            or prefix.audit['outage_seed'] != origin.outage_seed
            or prefix.audit['raw_boundary_hour'] != origin.power_raw_hour-1
            or prefix.audit['raw_current_hours'] != list(range(origin.power_raw_hour, current.power_raw_hour+1))
            or prefix.audit['config_sha256'] != origin.config_sha256
            or prefix.origin.protocol != protocol):
        raise ValueError('outage and normal source coordinates differ')
    observed = json.loads(observation.audit_payload)
    if (prefix.audit['rows'][-1] != observed['power_source_row']
            or prefix.audit['package_manifest_sha256'] != observed['power_package_manifest_sha256']):
        raise ValueError('outage and normal raw power row differ')
    # Reassemble N's exact current packet, including its prior boundary. No new
    # normal solution is selected and no caller-provided numerical view is used.
    packet = source.h1.assemble_current_normal(observation.network, observation.row,
        observation.raw_workload, relative_hour=completed_hours-1, dc_bus=declaration['dc_bus'],
        source_time_basis=observation.source_time_basis, before=_boundary(audit['normal_before']))
    rebuilt = normal._decision(packet, _boundary(audit['normal_after']))
    if (packet.input_identity != audit['normal_input_identity']
            or rebuilt.decision_bytes != envelope.decision.decision_bytes
            or packet.source_timestamp != audit['source_timestamp']
            or packet.source_time_basis != audit['source_time_basis']):
        raise ValueError('current source does not reproduce accepted normal input')
    units = {unit.uid: unit for unit in envelope.decision.network.units}
    branches = {branch.uid for branch in envelope.decision.network.ac_branches}
    protocol.__post_init__()
    for component in protocol.components:
        if ((component.kind == 'generator' and
                (component.uid not in units or not units[component.uid].enabled))
                or (component.kind == 'branch' and component.uid not in branches)):
            raise ValueError('outage inventory differs from normal static network')
    for step in prefix.steps:
        cap = step.repaired_generator_return_limit_mw
        if cap is not None and cap > units[step.ended.component.uid].maximum_power_mw:
            raise ValueError('repair return limit exceeds source nameplate')
    step = prefix.steps[-1]
    if step.before.source_hour != completed_hours-1 or step.after.source_hour != completed_hours:
        raise ValueError('current disclosure progress differs')
    # Only current normal conditions and one revealed transition leave this seam.
    return normal._owned(CurrentEnvironment, normal=envelope.decision, outage=step)


def prepare(root, *, expected_binding_sha256, expected_terminal_sha256, completed_hours,
            protocol, repair_limits, expected_outage_window_identity):
    """Fresh-at-return current bundle; caller cannot set raw coordinates/hours."""
    if type(completed_hours) is not int or not 1 <= completed_hours <= 168:
        raise ValueError('accepted enrollment N progress must be one through 168')
    for pin in (expected_binding_sha256, expected_terminal_sha256, expected_outage_window_identity):
        outage.source._sha(pin)
    before = implementation_identity()
    args = dict(expected_binding_sha256=expected_binding_sha256,
                expected_terminal_sha256=expected_terminal_sha256, completed_hours=completed_hours)
    envelope = normal.prepare(root, **args)
    audit, declaration, origin, current = _coordinates(envelope, completed_hours)
    outage_args = dict(split=origin.split, raw_start=origin.power_raw_hour, hours=completed_hours,
        outage_seed=origin.outage_seed, protocol=protocol, repair_limits=repair_limits,
        expected_window_identity=expected_outage_window_identity,
        expected_config_sha256=origin.config_sha256, config_path=declaration['config_path'])
    prefix = outage.prepare(**outage_args)
    observation = source.load_pinned_current(current, declaration['upstream_root'],
                                             config_path=declaration['config_path'])
    decision = _join(envelope, prefix, observation, completed_hours=completed_hours, protocol=protocol)
    rechecked = normal.prepare(root, **args)
    source.validate_pinned_current(observation, declaration['upstream_root'],
        expected_identity=observation.identity, config_path=declaration['config_path'])
    if (rechecked.audit_payload != envelope.audit_payload
            or rechecked.decision.decision_bytes != envelope.decision.decision_bytes
            or outage.prepare(**outage_args) != prefix or implementation_identity() != before):
        raise ValueError('normal, outage or implementation changed during current binding')
    payload = io.encode(dict(schema=SCHEMA, implementation=before,
        normal_audit_identity=envelope.audit_identity, observation_identity=observation.identity,
        normal_source_audit_identity=io.digest(observation.audit_payload),
        outage_window_identity=expected_outage_window_identity,
        outage_prefix_decision_identity=prefix.decision_identity,
        controller_binding_sha256=expected_binding_sha256,
        controller_terminal_sha256=expected_terminal_sha256,
        completed_hours=completed_hours, decision_identity=decision.decision_identity,
        current_source_correspondence_checked=True, policy_visible=False,
        repair_cap_source_registered=False, persistent_lane_owner_implemented=False,
        detached_consumer_authenticated=False, common_publication_verified=False,
        full_192_hour_coverage_verified=False, formal_execution_ready=False,
        formal_result=False, resource_admission=False, native_execution_authorized=False))
    return normal._owned(EnvironmentEnvelope, decision=decision, audit_payload=payload)
