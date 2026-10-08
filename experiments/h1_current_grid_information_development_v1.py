"""Read accepted N history into a current-only physical decision view.

No reference/actual dispatch, common-prefix publication, or run authorization.
Audit/source/solver identities are deliberately outside the decision view.
"""
from dataclasses import dataclass, asdict
from pathlib import Path
import json

from experiments import rq2_v2_normal_obligation_controller_development_v1 as controller
from src.rq2_joint_deliverability_boundary_v1 import grid_information as legacy

binding, io = controller.binding, controller.io
parent, source = controller.base.parent, controller.base.parent.source
SCHEMA = 'h1_current_grid_information_development_v1'


def implementation_identity():
    return io.digest(io.encode([SCHEMA,controller.implementation_identity(),
        io.digest(Path(legacy.__file__).read_bytes()),io.digest(Path(__file__).read_bytes())]))


class _Owned:
    def __init__(self,*a,**k): raise TypeError('fresh H1 information preparation required')
    __copy__ = controller.ObligationObservation.__copy__
    __deepcopy__ = controller.ObligationObservation.__deepcopy__
    __reduce_ex__ = controller.ObligationObservation.__reduce_ex__


def _owned(cls,**values):
    obj=object.__new__(cls)
    for name in cls.__dataclass_fields__: object.__setattr__(obj,name,values[name])
    return obj


@dataclass(frozen=True,init=False)
class H1CurrentNormalView(_Owned):
    previous_commitment: tuple
    commitment: tuple
    generation_mw: tuple


@dataclass(frozen=True,init=False)
class H1CurrentConditions(_Owned):
    demand_by_bus_mw: tuple
    generator_min_mw: tuple
    generator_max_mw: tuple
    generator_available: tuple
    dc_baseline_mw: float
    dc_physical_maximum_mw: float
    dc_connected_capacity_mw: float


@dataclass(frozen=True,init=False)
class H1CurrentInformation(_Owned):
    contract: str
    relative_hour: int
    network: legacy.StaticNetwork
    current: H1CurrentConditions
    normal: H1CurrentNormalView

    @property
    def decision_bytes(self): return io.encode(asdict(self))

    @property
    def decision_identity(self): return io.digest(self.decision_bytes)


@dataclass(frozen=True,init=False)
class H1NormalAuditEnvelope(_Owned):
    decision: H1CurrentInformation
    audit_payload: bytes

    @property
    def audit_identity(self): return io.digest(self.audit_payload)


def _decision(packet,after):
    """Private pure projection; the public prepare supplies replayed evidence."""
    source.validate_current(packet)
    source._boundary(packet.network,after,packet.relative_hour+1)
    data=packet.inputs.data
    point=data.hourly_points[0]
    request=packet.inputs.request
    units=tuple(legacy._owned(legacy.StaticUnit,uid=g.uid,bus=g.bus,dispatch_mode=g.dispatch_mode,enabled=g.enabled,
        minimum_power_mw=g.p_min_mw,maximum_power_mw=g.p_max_mw,ramp_mw_per_hour=g.ramp_mw_per_hour)
        for g in sorted(data.generators,key=lambda g:g.uid))
    network=legacy._owned(legacy.StaticNetwork,base_mva=data.base_mva,reference_bus=data.reference_bus,
        buses=tuple(sorted(b.uid for b in data.buses)),units=units,
        ac_branches=tuple(legacy._owned(legacy.StaticAcBranch,uid=b.uid,from_bus=b.from_bus,to_bus=b.to_bus,
            reactance_pu=b.reactance_pu,tap_ratio=b.tap_ratio,continuous_rating_mw=b.continuous_rating_mw)
            for b in sorted(data.branches,key=lambda b:b.uid)),
        dc_branches=tuple(legacy._owned(legacy.StaticDcBranch,uid=b.uid,from_bus=b.from_bus,to_bus=b.to_bus,
            minimum_power_mw=b.p_min_mw,maximum_power_mw=b.p_max_mw)
            for b in sorted(data.dc_branches,key=lambda b:b.uid)),dc_bus=request.dc_bus)
    current=_owned(H1CurrentConditions,demand_by_bus_mw=tuple(sorted(point.demand_by_bus_mw.items())),
        generator_min_mw=tuple(sorted(point.generator_min_mw.items())),
        generator_max_mw=tuple(sorted(point.generator_max_mw.items())),
        generator_available=tuple((g.uid,g.enabled) for g in units),dc_baseline_mw=request.dc_requested_mw[0],
        dc_physical_maximum_mw=request.dc_physical_maximum_mw[0],dc_connected_capacity_mw=request.dc_connected_capacity_mw[0])
    normal=_owned(H1CurrentNormalView,previous_commitment=tuple((u[0],u[1]) for u in packet.before.units),
        commitment=tuple((u[0],u[1]) for u in after.units),generation_mw=tuple((u[0],u[2]) for u in after.units))
    return _owned(H1CurrentInformation,contract=SCHEMA,relative_hour=packet.relative_hour,network=network,current=current,normal=normal)


def prepare(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours):
    """Freshly replay the accepted prefix; never accepts a detached candidate."""
    own=implementation_identity()
    root=Path(root).resolve(strict=True)
    args=dict(expected_binding_sha256=expected_binding_sha256,expected_terminal_sha256=expected_terminal_sha256,
        completed_hours=completed_hours)
    # This verifies obligation, complete source/carry prefix, Job, and clock chain.
    initial=controller.inspect(root,**args)
    header,hview=controller.base.entry.read(root/'obligation_non_authoritative'/'binding.json',expected_binding_sha256)
    terminal,tview=controller.base.entry.read(root/'obligation_non_authoritative'/f'{completed_hours-1:03d}.terminal.json',expected_terminal_sha256)
    declaration=header['parent_declaration']
    captured={}
    class Reader(binding.snapshot.Snapshot):
        def _after(self,packet,result):
            if type(result) is not parent.ChildInspection or result.status!='accepted':
                raise ValueError('fresh accepted timed child required')
            count=len(binding.replay.native.model_api.stage_order(packet.inputs))
            if (result.stored_reports!=count or type(result.projection) is not parent.Projection
                    or result.projection.projection_identity!=io.digest(io.encode([parent.CHILD_SCHEMA,io.digest(result.projection.payload)]))):
                raise ValueError('complete normal projection differs')
            after=super()._after(packet,result)
            if packet.relative_hour==completed_hours-1:
                captured.update(packet=packet,result=result,after=after,count=count)
            return after
    old=binding.snapshot.old
    origin=old.binding.H1SourceDeclaration(**declaration['origin'])
    with old.replay.guard.solver_calls_forbidden():
        row=old.binding.load_pinned_current(origin,declaration['upstream_root'],config_path=declaration['config_path'])
        reader=Reader(declaration['root'],row.network,old.Rq2SolverSpec(**declaration['specification']),
            old.replay.H1HourReplayLimits(**declaration['limits']),origin=origin,upstream_root=declaration['upstream_root'],
            config_path=declaration['config_path'],dc_bus=declaration['dc_bus'],hours=168,
            expected_anchor_record=terminal['parent_anchor_sha256'],expected_parent_identity=header['parent_identity'])
        try:
            state=reader.inspect()
            if (state.completed_hours!=completed_hours or state.head!=terminal['parent_head'] or not captured
                    or state.status!=('complete' if completed_hours==168 else 'ready')):
                raise ValueError('complete accepted normal prefix required')
            packet,result,after=captured['packet'],captured['result'],captured['after']
            decision=_decision(packet,after)
            projection=json.loads(result.projection.payload)
            audit=io.encode(dict(schema=SCHEMA,implementation=own,decision_identity=decision.decision_identity,
                parent_declaration=declaration,controller_header_sha256=expected_binding_sha256,
                controller_terminal_sha256=expected_terminal_sha256,normal_input_identity=packet.input_identity,
                packet_audit_identity=packet.audit_identity,source_timestamp=packet.source_timestamp,
                source_time_basis=packet.source_time_basis,child_head=result.head,child_archive_identity=result.archive_identity,
                projection_identity=result.projection.projection_identity,projection_payload_sha256=io.digest(result.projection.payload),
                normal_request_key=binding.replay.request_key(packet,reader._spec,reader._limits),
                normal_before=asdict(packet.before),normal_after=asdict(after),canonical_locks=projection['value']['canonical_locks'],
                completed_stages=captured['count'],policy_visible=False,common_prefix_publication_verified=False,
                detached_consumer_authenticated=False,
                reference_or_actual_ready=False,formal_result=False,resource_admission=False,native_execution_authorized=False))
            if len(audit)>binding.CAP: raise ValueError('H1 information audit byte cap')
            if controller.inspect(root,**args)!=initial: raise ValueError('normal prefix changed during preparation')
            controller.base.entry.unchanged({root/'obligation_non_authoritative'/'binding.json':(binding.CAP,hview),
                root/'obligation_non_authoritative'/f'{completed_hours-1:03d}.terminal.json':(binding.CAP,tview)})
            if reader.inspect()!=state or implementation_identity()!=own:
                raise ValueError('H1 information evidence changed during preparation')
            return _owned(H1NormalAuditEnvelope,decision=decision,audit_payload=audit)
        finally:reader.close()
