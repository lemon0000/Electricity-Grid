"""Complete H1 normal workload arithmetic; no execution or resource admission."""
from dataclasses import asdict, dataclass
from fractions import Fraction
from hashlib import sha256
from math import ceil, isfinite
from pathlib import Path

from . import execution_resource_contract as serial
from . import normal_h1_full_attempt_anchor as anchor
from . import normal_h1_hour_replay_v3 as replay

SCHEMA='h1_full_normal_resource_declaration_v3'


@dataclass(frozen=True)
class H1NormalWork:
    task_id: str
    hours: int
    stage_order: tuple
    specification: object


@dataclass(frozen=True)
class H1TaskResources:
    envelope: serial.TaskEnvelope
    archive_overhead_bytes: int


def implementation_identity():
    return replay.current.source._digest(SCHEMA,replay.implementation_identity(),anchor.implementation_identity(),
        sha256(Path(serial.__file__).read_bytes()).hexdigest(),sha256(Path(__file__).read_bytes()).hexdigest())


def validate_stage_order(order):
    if (type(order) is not tuple or not 2<=len(order)<=232
            or any(type(row) is not tuple or len(row)!=2 for row in order)
            or order[0]!=('operating_cost',None)):
        raise ValueError('complete canonical H1 stage inventory required')
    commits=tuple(uid for kind,uid in order[1:] if kind=='commitment')
    generation=tuple(uid for kind,uid in order[1:] if kind=='generation')
    if (not generation or any(type(uid) is not str or not uid for uid in commits+generation)
            or commits!=tuple(sorted(set(commits))) or generation!=tuple(sorted(set(generation)))
            or not set(commits)<=set(generation)
            or order!=(('operating_cost',None),*(('commitment',u) for u in commits),*(('generation',u) for u in generation))):
        raise ValueError('complete ordered UID stages required')
    return len(order)


def validate_work(work):
    if type(work) is not H1NormalWork:
        raise ValueError('exact full H1 workload required')
    if (type(work.task_id) is not str or not work.task_id.strip()
            or type(work.hours) is not int or not 1<=work.hours<=192):
        raise ValueError('named H1 task with 1..192 hours required')
    stages=validate_stage_order(work.stage_order)
    replay.native.capture.provenance.adapter.validate_spec(work.specification)
    seconds=float(work.specification.time_limit_seconds)
    if not isfinite(seconds):raise ValueError('finite stage time required')
    return stages,Fraction(work.specification.time_limit_seconds)


def _validate_resource(item):
    if type(item) is not H1TaskResources or type(item.envelope) is not serial.TaskEnvelope:
        raise ValueError('exact H1 task envelope required')
    serial._validate_positive_fields(item.envelope,('task_id',))
    if type(item.archive_overhead_bytes) is not int or item.archive_overhead_bytes<=0:
        raise ValueError('explicit positive archive overhead allowance required')


def content_inventory(stages,hours):
    if (type(stages) is not int or not 2<=stages<=232
            or type(hours) is not int or not 1<=hours<=192):
        raise ValueError('bounded full H1 stage/hour inventory required')
    metadata=anchor.chunks.METADATA_BYTES
    raw=replay.native.MAX_PAYLOAD_BYTES
    child=stages*raw+(stages+1)*metadata
    registry=(stages+3)*metadata
    hour_anchor=(stages+5)*anchor.MAX_RECORD_BYTES # genesis + events + header
    parent=2*hours*2*metadata
    parent_anchor=(2*hours+2)*anchor.MAX_RECORD_BYTES
    return dict(stages_per_hour=stages,hours=hours,solver_calls=stages*hours,
        child_events_per_hour=stages+1,registry_events_per_hour=stages+3,
        anchor_records_per_hour=stages+4,parent_events=2*hours,parent_anchor_records=2*hours+1,
        stage_raw_limit_bytes=raw,chunk_limit_bytes=anchor.chunks.CHUNK_BYTES,
        metadata_limit_bytes=metadata,anchor_record_limit_bytes=anchor.MAX_RECORD_BYTES,
        child_content_per_hour_bytes=child,registry_content_per_hour_bytes=registry,
        hour_anchor_content_bytes=hour_anchor,parent_content_bytes=parent,
        parent_anchor_content_bytes=parent_anchor,
        total_content_limit_bytes=hours*(child+registry+hour_anchor)+parent+parent_anchor)


def check_plan(work,resources,budget):
    """Serial declared capacity, reserving every stage and retaining all files.

    Archive overhead is supplied, not measured. Content bounds omit SQLite pages,
    journals, directory allocation and controller files; overhead must cover them.
    Non-solver allowance includes audits, shutdown and solver TimeLimit overshoot.
    No sharing hit rate, early stopping, retries or disk reclamation is assumed.
    """
    if type(work) is not tuple or not work or type(resources) is not tuple:
        raise ValueError('explicit full H1 task/resource tuples required')
    if type(budget) is not serial.SerialResourceBudget:
        raise ValueError('exact serial resource budget required')
    serial._validate_positive_fields(budget)
    for item in resources:
        _validate_resource(item)
    inventory=[validate_work(item) for item in work]
    by_id={item.envelope.task_id:item for item in resources}
    ids=[item.task_id for item in work]
    if len(set(ids))!=len(ids) or len(by_id)!=len(resources) or set(by_id)!=set(ids):
        raise ValueError('exactly one resource envelope per unique H1 task required')
    rows=[]
    errors=[]
    for item,(stages,seconds) in zip(work,inventory):
        resource=by_id[item.task_id]
        envelope=resource.envelope
        content=content_inventory(stages,item.hours)
        total_seconds=seconds*content['solver_calls']
        wall=ceil(total_seconds+envelope.non_solver_seconds)
        archive=content['total_content_limit_bytes']+resource.archive_overhead_bytes
        for observed,limit,name in (
            (wall,envelope.max_wall_seconds,'task_wall_shortfall'),
            (archive,envelope.archive_bytes,'archive_content_and_overhead_shortfall'),
            (item.specification.threads,envelope.max_threads,'task_thread_shortfall'),
            (envelope.max_threads,budget.max_threads,'plan_thread_shortfall')):
            if observed>limit:errors.append((item.task_id,name))
        rows.append(dict(task_id=item.task_id,content=content,
            reserved_solver_seconds_ratio=(total_seconds.numerator,total_seconds.denominator),
            required_declared_wall_seconds=wall,required_declared_archive_bytes=archive))
    envelopes=[r.envelope for r in resources]
    wall=sum(e.max_wall_seconds for e in envelopes)+budget.controller_seconds
    commit=max(e.max_job_commit_bytes for e in envelopes)+budget.supervisor_additional_commit_bytes+budget.commit_reserve_bytes
    disk=sum(e.archive_bytes+e.scratch_bytes for e in envelopes)+budget.disk_reserve_bytes
    for observed,limit,name in ((wall,budget.max_total_wall_seconds,'total_wall_shortfall'),
            (commit,budget.max_additional_commit_bytes,'serial_commit_shortfall'),
            (disk,budget.max_additional_disk_bytes,'retained_disk_shortfall')):
        if observed>limit:errors.append(('serial_plan',name))
    result=dict(schema=SCHEMA,work=tuple(asdict(w) for w in work),resources=tuple(asdict(r) for r in resources),
        budget=asdict(budget),tasks=tuple(rows),solver_calls=sum(r['content']['solver_calls'] for r in rows),
        reserved_total_wall_seconds=wall,required_additional_commit_bytes=commit,required_additional_disk_bytes=disk,
        errors=tuple(errors),declaration_consistent=not errors,implementation_identity=implementation_identity(),
        assumptions=('one_quiescent_job_at_a_time','full_inventory_no_sharing_credit','no_retries','no_scratch_reclamation'),
        model_shape_verified=False,physical_space_reserved=False,whole_task_resources_verified=False,
        execution_authorized=False,formal_ready=False)
    result['declaration_identity']=replay.current.source._digest(result)
    return result


def bind_current_hour(work,resource,packet,limits):
    """Check actual current packet/order/model against one declared task envelope.

    This does not materialize future carry or admit an execution. Later stages
    still require independent runtime size and strict numerical checks.
    """
    stages,_=validate_work(work)
    _validate_resource(resource)
    envelope=resource.envelope
    serial._validate_positive_fields(envelope,('task_id',))
    if envelope.task_id!=work.task_id:raise ValueError('task envelope identity mismatch')
    key=replay.request_key(packet,work.specification,limits)
    if packet.relative_hour>=work.hours:
        raise ValueError('current hour outside declared task')
    if replay.native.model_api.stage_order(packet.inputs)!=work.stage_order:
        raise ValueError('actual H1 full stage inventory mismatch')
    request=replay.native.model_api.H1StageRequest(packet.inputs)
    model=replay.native.model_api.build_h1_stage_model(request,
        expected_identity=replay.native.model_api.h1_stage_identity(request))
    scale=replay.native.capture.audit.model_scale(model)
    last_request=replay.native.model_api.H1StageRequest(packet.inputs,(0.,)*(stages-1))
    last_model=replay.native.model_api.build_h1_stage_model(last_request,
        expected_identity=replay.native.model_api.h1_stage_identity(last_request))
    last=replay.native.capture.audit.model_scale(last_model)
    if last.variables!=scale.variables or last.constraints!=scale.constraints+stages-1:
        raise ValueError('H1 endpoint shape or lock-row increment mismatch')
    if (stages>limits.max_stages or scale.variables>min(envelope.max_variables,limits.max_variables)
            or last.constraints>min(envelope.max_constraints,limits.max_constraints)):
        raise ValueError('complete H1 model exceeds declared shape limits')
    return dict(request_key=key,task_id=work.task_id,stage_order=work.stage_order,
        variables=scale.variables,first_stage_constraints=scale.constraints,
        last_stage_constraints=last.constraints,solver_calls=stages,
        model_shape_verified=True,shape_only_placeholder_locks=True,complete_chain_shape_verified=False,
        numerical_certificate=False,execution_authorized=False,formal_ready=False)
