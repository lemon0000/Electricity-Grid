"""Hour-zero selector input reconstruction; no producer or execution capability.

Capture requires the live common genesis. Detached rebuild checks the retained
declaration and fresh source science, not a currently live owner or Job history.
"""
from dataclasses import asdict, dataclass, fields
from fractions import Fraction as Q
import json
from pathlib import Path
from types import MappingProxyType

from experiments import h1_common_owner_genesis_development_v3 as common
from experiments import h1_owned_selector_sequence_development_v1 as sequence

phase,selection,io=common.phase,sequence.selection,sequence.io
encode=phase.encode
SCHEMA='h1_selector_input_snapshot_development_v3'
CAP=4*1024**2
FLAGS=MappingProxyType(dict(native_execution_authenticated=False,live_owner_authenticated=False,
    detached_consumer_authenticated=False,owner_consumption_authorized=False,
    whole_job_quiescence_checked=False,selector_producer_connected=False,
    continuation_ready=False,resource_admission=False,formal_execution_ready=False,
    formal_result=False,native_execution_authorized=False))


def implementation_identity():
    if SCHEMA!='h1_selector_input_snapshot_development_v3' or any(v is not False for v in FLAGS.values()):
        raise ValueError('selector snapshot scope changed')
    return io.digest(encode([SCHEMA,io.digest(Path(__file__).read_bytes()),
                            common.implementation_identity(),sequence.implementation_identity()]))


def _object(value,names):
    if type(value) is not dict or set(value)!=set(names):raise ValueError('exact snapshot fields required')
    return dict(value)


def _fields(kind,value):return _object(value,(f.name for f in fields(kind)))


def _fraction(value):
    d=_object(value,('numerator','denominator'))
    if any(type(v) is not str for v in d.values()):raise ValueError('exact rational strings required')
    q=Q(int(d['numerator']),int(d['denominator']))
    if encode(q)!=encode(d):raise ValueError('canonical reduced rational required')
    return q


def _declarations(manifest,binding,configuration):
    """Explicit fixed dataclass graph; no executable type tags or carry decoder."""
    m=_fields(phase.Manifest,manifest)
    if type(m['lanes']) is not list:raise ValueError('canonical lane array required')
    lanes=[]
    for item in m['lanes']:
        c=_fields(phase.LaneConfig,item)
        c['policy']=phase.business.business.BidirectionalPolicy(**_fields(
            phase.business.business.BidirectionalPolicy,c['policy']))
        c['mechanism']=phase.business.Mechanism(**{k:_fraction(v) for k,v in
            _fields(phase.business.Mechanism,c['mechanism']).items()})
        if type(c['envelope']) is not list or any(type(p) is not list or len(p)!=2 for p in c['envelope']):
            raise ValueError('canonical envelope pairs required')
        c['envelope']=tuple((k,_fraction(v) if type(v) is dict else v) for k,v in c['envelope'])
        lanes.append(phase.LaneConfig(**c))
    m['lanes']=tuple(lanes)
    for name,kind in (('reference_selector',selection.reference.ReferenceSelectorSpec),
                      ('actual_selector',selection.actual.ActualDispatchSpec),
                      ('solver_specification',selection.native.capture.Rq2SolverSpec),
                      ('replay_limits',selection.ReplayLimits)):
        m[name]=kind(**_fields(kind,m[name]))
    m=phase.Manifest(**m)
    b=phase.SourceBinding(**_fields(phase.SourceBinding,binding))
    api=sequence.configuration_api;c=_fields(api.SelectorRunConfiguration,configuration)
    if type(c['generation_uids']) is not list:raise ValueError('canonical UID array required')
    c['generation_uids']=tuple(c['generation_uids'])
    for name,kind in (('reference_selector',selection.reference.ReferenceSelectorSpec),
                      ('actual_selector',selection.actual.ActualDispatchSpec),
                      ('specification',selection.native.capture.Rq2SolverSpec),
                      ('limits',selection.ReplayLimits),
                      ('reference_job_budget',api.process.TaskProcessBudget),
                      ('actual_job_budget',api.process.TaskProcessBudget)):
        c[name]=kind(**_fields(kind,c[name]))
    c=api.SelectorRunConfiguration(**c)
    if (encode(m)!=encode(manifest) or encode(b)!=encode(binding) or encode(c)!=encode(configuration)
            or m.reference_selector!=c.reference_selector or m.actual_selector!=c.actual_selector
            or m.solver_specification!=c.specification or m.replay_limits!=c.limits):
        raise ValueError('canonical manifest and selector configuration correspondence required')
    return m,b,c


def _provenance(value):
    p=_object(value,('root','binder_head','global_head','holder_receipt','owner_receipt'))
    if type(p['root']) is not str or str(common.bootstrap.local._path(p['root']))!=p['root']:
        raise ValueError('canonical absolute common root required')
    io.pin(p['binder_head']);io.pin(p['global_head'])
    h=common.HolderGenesisReceipt(**_fields(common.HolderGenesisReceipt,p['holder_receipt']))
    od=_fields(common.OwnerGenesisReceipt,p['owner_receipt'])
    if type(od['heads']) is not list:raise ValueError('canonical owner heads required')
    od['heads']=tuple(od['heads']);o=common.OwnerGenesisReceipt(**od)
    if encode(h)!=encode(p['holder_receipt']) or encode(o)!=encode(p['owner_receipt']):
        raise ValueError('canonical empty genesis receipts required')
    return p


def _args(manifest,lane,power=None):
    return dict(lane=lane,selector=manifest.reference_selector if lane.role=='Rref' else manifest.actual_selector,
                specification=manifest.solver_specification,limits=manifest.replay_limits,power=power)


@dataclass(frozen=True)
class RebuiltInput:
    """Constructible diagnostic container; never an owned execution credential."""
    frame: object
    disclosure: object
    before: object
    arguments: dict
    run_configuration: sequence.configuration_api.SelectorRunConfiguration
    max_archive_bytes: int
    snapshot: bytes
    authority_flags: tuple


def _build(declaration):
    d=_object(declaration,('hour','manifest','source_binding','run_configuration','provenance',
                           'role','lane_id','reference','max_archive_bytes'))
    if type(d['hour']) is not int or d['hour']!=0:raise ValueError('only hour-zero genesis supported')
    _provenance(d['provenance'])
    manifest,binding,config=_declarations(d['manifest'],d['source_binding'],d['run_configuration'])
    current=phase._fresh(binding,0,binding.genesis_terminal_sha256)
    state=phase._initial(manifest,current)
    if state.hour!=0:raise ValueError('empty scientific genesis required')
    prepared=current.prepared_current;frame,action=prepared.frame,prepared.source_action
    before=state.reference;args=_args(manifest,phase.RREF);dependency=None
    if d['role']=='reference':
        if d['lane_id'] is not None or d['reference'] is not None:raise ValueError('reference has no Actual dependency')
    elif d['role']=='actual':
        if type(d['lane_id']) is not str:raise ValueError('exact Actual lane required')
        lane=next((c for c in manifest.lanes if c.lane_id==d['lane_id']),None)
        if lane is None:raise ValueError('Actual lane absent from common manifest')
        ref=_object(d['reference'],('root','terminal_sha256','request_sha256','max_archive_bytes'))
        io.pin(ref['terminal_sha256']);io.pin(ref['request_sha256'])
        checked=sequence.inspect(sequence._root(ref['root']),frame,action,state.reference,
            expected_terminal_sha256=ref['terminal_sha256'],max_archive_bytes=ref['max_archive_bytes'],
            run_configuration=config,**args)
        if checked['request_sha256']!=ref['request_sha256']:raise ValueError('reference sequence request differs')
        replay=checked['replay']
        if replay.next_candidate is None or replay.candidate_request_exact is None:
            raise ValueError('complete reference candidate required')
        g=Q(*map(int,replay.candidate_request_exact))
        if not 0<=g<=current.workload_exact*250:raise ValueError('reference request outside exact baseline')
        previous=dict(state.lanes)[lane.lane_id]
        if previous.halted or previous.completed:raise ValueError('active Actual genesis required')
        item=phase.business.current(relative_hour=0,mechanism=lane.mechanism,workload=current.workload_exact,
            source_cfe_at_alpha_one=current.source_cfe_at_alpha_one_exact,grid_request_mw=g)
        candidate=phase.business.prepare_development(previous.business,item,expected_current_identity=item.identity)
        if candidate.next_candidate is None:raise ValueError('business candidate unresolved')
        power=candidate.actual_power_mw
        prescribed=selection.physical.RelativeDcPower(0,str(power.numerator),str(power.denominator),'mechanism_assumption')
        before=previous.actual;args=_args(manifest,lane.lane,prescribed)
        dependency=dict(reference_request_exact=g,actual_power_exact=power,
            reference_candidate=replay.next_candidate.identity,business_before=previous.business.identity,
            business_after=candidate.next_candidate.identity)
    else:raise ValueError('exact reference or actual role required')
    sequence_config=sequence._configuration(frame,action,before,args,d['max_archive_bytes'],config)
    projection=dict(declaration_sha256=io.digest(encode(d)),
        phase_request=phase._request(manifest,state,current),state=state.scientific,
        source_audit=current.source_projection_audit_identity,source_observation=current.source_observation_identity,
        exogenous=current.exogenous_scientific_identity,before_identity=before.identity,
        before_audit=before.audit_identity,selector_input=selection.input_identity(frame,action,before,
            lane=args['lane'],power=args['power']),initial_stage_request=sequence_config['initial_stage_request'],
        sequence_configuration=io.digest(encode(sequence_config)),dependency=dependency)
    return (frame,action,before,args,config,d['max_archive_bytes']),projection


def _document(declaration,projection,implementation):
    raw=encode(dict(schema=SCHEMA,implementation=implementation,declaration=declaration,
                    projection=projection,**FLAGS))
    if len(raw)>CAP:raise ValueError('bounded selector snapshot required')
    return raw


def rebuild(snapshot,*,expected_sha256):
    """Fresh source reconstruction only; no owner file writes or live capability."""
    if type(snapshot) is not bytes or len(snapshot)>CAP:raise ValueError('bounded immutable snapshot required')
    if io.digest(snapshot)!=io.pin(expected_sha256):raise ValueError('external snapshot pin differs')
    doc=_object(json.loads(snapshot),('schema','implementation','declaration','projection',*FLAGS))
    own=implementation_identity()
    if (encode(doc)!=snapshot or doc['schema']!=SCHEMA or doc['implementation']!=own
            or any(doc[k] is not False for k in FLAGS)):
        raise ValueError('canonical snapshot implementation and scope required')
    with sequence.bridge.science.prior.guard.solver_calls_forbidden():
        _,first=_build(doc['declaration'])
        context,second=_build(doc['declaration'])
        if (encode(first)!=encode(second) or encode(first)!=encode(doc['projection'])
                or implementation_identity()!=own):raise ValueError('snapshot source or scientific projection changed')
    return RebuiltInput(*context,snapshot,tuple(FLAGS.items()))


def _owner_view(owner):
    head=owner._correspondence()
    if owner._replay()!=3:raise ValueError('complete retained common genesis required')
    return dict(root=str(owner.root),binder_head=owner._journal.head,global_head=head,
                holder_receipt=asdict(owner._holder_receipt()),owner_receipt=asdict(owner._owner_receipt()))


def _capture(owner,config,max_archive_bytes,role,lane_id,reference):
    if type(owner) is not common.CommonOwnerGenesis:raise ValueError('exact live common owner required')
    if type(config) is not sequence.configuration_api.SelectorRunConfiguration:
        raise ValueError('exact typed selector configuration required')
    owner._enter()
    try:
        own=implementation_identity();view=_owner_view(owner)
        declaration=json.loads(encode(dict(hour=0,manifest=asdict(owner._manifest),
            source_binding=asdict(owner._binding),run_configuration=asdict(config),provenance=view,
            role=role,lane_id=lane_id,reference=reference,max_archive_bytes=max_archive_bytes)))
        with sequence.bridge.science.prior.guard.solver_calls_forbidden():
            _,projection=_build(declaration)
            raw=_document(declaration,projection,own)
            rebuild(raw,expected_sha256=io.digest(raw))
        if (encode(_owner_view(owner))!=encode(view) or implementation_identity()!=own
                or encode(config)!=encode(declaration['run_configuration'])):
            raise ValueError('common owner or configuration changed during snapshot capture')
        return raw
    finally:owner._leave()


def capture_reference(owner,run_configuration,*,max_archive_bytes):
    return _capture(owner,run_configuration,max_archive_bytes,'reference',None,None)


def capture_actual(owner,run_configuration,*,max_archive_bytes,lane_id,reference_root,
                   reference_terminal_sha256,reference_request_sha256,reference_max_archive_bytes):
    ref=dict(root=str(sequence._root(reference_root)),terminal_sha256=reference_terminal_sha256,
             request_sha256=reference_request_sha256,max_archive_bytes=reference_max_archive_bytes)
    return _capture(owner,run_configuration,max_archive_bytes,'actual',lane_id,ref)
