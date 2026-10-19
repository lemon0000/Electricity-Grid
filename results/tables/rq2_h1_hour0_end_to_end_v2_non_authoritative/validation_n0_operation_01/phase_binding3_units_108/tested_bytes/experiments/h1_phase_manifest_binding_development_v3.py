"""Detached phase binding with stable science and separate bookend execution.

This draft acquires its own diagnostic phase-data window. Its output is data,
never an owner credential, and does not alter the predecessor verifier route.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import sys
from types import FunctionType

from experiments import h1_phase_manifest_binding_development_v2 as prior
from experiments import h1_phase_dependency_validation_operation_development_v1 as observation
from experiments import h1_validation_runtime_closure_development_v2 as runtime


SCHEMA='h1_phase_manifest_binding_development_v3'
io=prior.io
group=prior.group
configuration=prior.configuration
owner=prior.owner
ArchiveCapacityDeclaration=prior.ArchiveCapacityDeclaration
ARMS=prior.ARMS
TERMINAL=prior.TERMINAL
ENVELOPE=prior.ENVELOPE
FLAGS=dict(executable_manifest=False,resource_admission=False,formal_execution_ready=False,
    formal_result=False,native_execution_authorized=False,owner_consumption_authorized=False)


@dataclass(frozen=True)
class PreparedManifest:
    manifest: owner.Manifest | None
    audit_payload: bytes
    audit_identity: str
    execution_receipt_payload: bytes


def implementation_identity(selector_configuration):
    return io.digest(owner.encode([SCHEMA,sha256(Path(__file__).read_bytes()).hexdigest(),
        prior._implementation(selector_configuration),observation.implementation_identity()]))


def _validate(family,ordinal,c,archive):
    if family!='training_ub' or type(family) is not str or type(ordinal) is not int or ordinal<0:
        raise ValueError('training_ub and nonnegative exact ordinal required')
    if type(c) is not configuration.SelectorRunConfiguration or type(archive) is not ArchiveCapacityDeclaration:
        raise ValueError('exact typed selector and archive declarations required')
    c.__post_init__();archive.__post_init__()


def _evidence(science):
    if (type(science) is not dict or set(science)!=set(('predecessor_group','dependency_sha256',
            'observed_file_count','observed_total_bytes','verifier_sha256',
            'verifier_implementation','verifier_implementation_sha256'))
            or science['observed_file_count']!=len(science['dependency_sha256'])):
        raise ValueError('complete phase science inventory required')
    return dict(schema=observation.SCHEMA,active_implementation=observation.implementation_identity(),
        **{key:science[key] for key in ('verifier_sha256','verifier_implementation',
            'verifier_implementation_sha256','observed_file_count','observed_total_bytes')},
        dependency_inventory_sha256=io.digest(owner.encode(science['dependency_sha256'])),
        predecessor_group_sha256=io.digest(owner.encode(science['predecessor_group'])),
        observation_schedule='held_entry_exit',per_call_physical_freshness=False,
        canonical_equivalence_verified=False,between_bookend_ABA_covered=False,
        detached_data=True,**FLAGS)


def _project(family,ordinal,c,archive,science,implementation):
    """Pure binding projection; caller must acquire and authenticate its input."""
    g=science['predecessor_group']
    if (g['family']!=family or not any(type(s['ordinal']) is int and s['ordinal']==ordinal
            for s in g['siblings'])):
        raise ValueError('requested phase obligation absent from observed group')
    lanes,classifications=prior._lanes(g)
    reserved=prior._record_reservation(c,[lane.lane_id for lane in lanes]) if lanes else 0
    if archive.max_event_bytes<reserved:
        raise ValueError('declared selector record envelope exceeds event declaration')
    manifest=owner.Manifest(lanes,c.reference_selector,c.actual_selector,c.specification,c.limits,
        archive.max_events,archive.max_event_bytes,archive.max_archive_bytes,
        g['accounting_period_id']) if lanes else None
    audit=dict(schema=SCHEMA,implementation_sha256=implementation,family=family,ordinal=ordinal,
        group=g,dependency_verifier=_evidence(science),arm_classifications=classifications,
        selector_configuration=c.binding(),archive_declaration=asdict(archive),
        manifest=asdict(manifest) if manifest else None,
        archive_derivation=dict(full_192h_primary_event_upper_bound=576,origin_events=2,
            subsequent_hours=191,events_per_subsequent_hour=3,terminal_events=1,
            events_per_alternate_witness=2,conditional_required_events=576+2*archive.reserved_alternate_witnesses,
            reserved_selector_record_bytes=reserved,conditional_on_witness_count_within_reservation=True,
            archive_used=bool(lanes),alternate_witness_limit_enforced=False,
            full_event_size_bound_proven=False,full_path_archive_sufficiency_proven=False,
            physical_storage_bound_proven=False),detached_declaration=True,
        group_obligations_complete=False,capacity_is_feasible_certificate=False,
        producer_archive_bound_proven=False,paired_owner_authenticated=False,
        selector_producer_connected=False,normal_source_correspondence_verified=False,
        solver_reuse_verified=False,per_call_physical_freshness=False,
        observation_schedule='held_entry_exit',**FLAGS)
    payload=owner.encode(audit)
    return manifest,payload,io.digest(payload)


def prepare(family,ordinal,selector_configuration,archive):
    """Acquire, project and close; return stable data plus a closed execution record."""
    _RUNTIME();c=selector_configuration;_validate(family,ordinal,c,archive)
    request=owner.encode([family,ordinal,c.binding(),asdict(archive)])
    implementation=implementation_identity(c)
    window=observation.PhaseDependencyValidationOperation(
        plan=((family,ordinal),(family,ordinal)),diagnostic_only=True)
    with window:
        science=json.loads(window.prepare_group(family,ordinal))['scientific_projection']
        _RUNTIME()
        result=_project(family,ordinal,c,archive,science,implementation)
        repeated=json.loads(window.prepare_group(family,ordinal))['scientific_projection']
        _RUNTIME();_validate(family,ordinal,c,archive)
        if (owner.encode(science)!=owner.encode(repeated) or implementation_identity(c)!=implementation
                or owner.encode([family,ordinal,c.binding(),asdict(archive)])!=request):
            raise ValueError('phase binding inputs or implementation changed during projection')
    receipt=window.receipt();_RUNTIME()
    if not (receipt['lifecycle_complete'] and receipt['all_handles_closed']
            and receipt['immutable_bytes_cleared'] and receipt['original_guard_released']):
        raise ValueError('complete closed phase data window required')
    execution=owner.encode(dict(schema=SCHEMA,active_implementation=implementation,
        stable_audit_sha256=result[2],phase_window_receipt=receipt,detached_data=True,
        consumer_bound=False,canonical_independent_differential_verified=False,**FLAGS))
    return PreparedManifest(*result,execution)


_RUNTIME,_ARM=runtime.make_runtime(globals(),'phase binding data projection',alias='_RUNTIME')
_MODULES=tuple((m.__name__,m) for m in (sys.modules[__name__],prior,observation,runtime,
    configuration,owner,group,io))


def _routes():
    if any(sys.modules.get(name) is not module for name,module in _MODULES):
        raise ValueError('canonical phase binding module registry changed')


def _attributes():
    rows=[]
    for module,names in ((prior,('_lanes','_record_reservation','_implementation','ARMS','TERMINAL','ENVELOPE')),
            (observation,('PhaseDependencyValidationOperation','implementation_identity','SCHEMA')),
            (io,('encode','digest')),(json,('loads',)),(owner,('encode','Manifest','LaneConfig'))):
        rows.extend((module,name,getattr(module,name)) for name in names)
    for cls in (PreparedManifest,ArchiveCapacityDeclaration,configuration.SelectorRunConfiguration,
            owner.Manifest,owner.LaneConfig):
        rows.extend((cls,name,value) for name,value in vars(cls).items()
            if isinstance(value,(FunctionType,property,staticmethod,classmethod)))
    for _,module in _MODULES:
        rows.extend((module,name,getattr(module,name)) for name in
            ('__name__','__file__','__spec__','__loader__','__package__'))
    return tuple(rows)


_ARM(attributes=_attributes(),checks=(_routes,),ignored=('_ARM',))
del _ARM
