"""Versioned source parent whose children reference fully replayed timed Jobs.

Stored Job observations are conditional evidence, not live process authority.
No old saved-report projection type is manufactured. No resume or formal gate.
"""
from dataclasses import asdict, dataclass
import json
from pathlib import Path

from experiments import h1_timed_released_worker_development_v1 as prior

old, worker, io = prior.old, prior.worker, prior.io
bounded, source, replay = old.bounded, old.bounded.source, old.replay
SCHEMA = 'h1_timed_job_parent_development_v1'
ENTRY_SCHEMA = 'h1_timed_released_worker_development_v2'
CHILD_SCHEMA = 'h1_timed_job_child_reference_development_v1'
FLAGS = dict(prior.FLAGS)
MEMBERS = ('h1_timed_job_parent_development_v1.py','h1_timed_job_snapshot_development_v1.py',
           'h1_timed_released_worker_development_v2.py','h1_timed_job_controller_development_v1.py')
RECORDS = ('request.json','launch.json','initial_observation.json','child.json',
           'release_intent.json','consumed.json','worker_result.json','observation.json')
_TOKEN = object()


def implementation_identity():
    return io.digest(io.encode([SCHEMA,prior.implementation_identity(),
        [[n,io.digest(Path(__file__).with_name(n).read_bytes())] for n in MEMBERS]]))


def environment(scratch):
    value = old.runtime.development_environment()
    value.update(TEMP=str(scratch),TMP=str(scratch))
    value = dict(sorted(value.items()));old.runtime._environment(value)
    return value


def observation(doc):
    value = dict(doc)
    value['minimum_runtime_disk_available_bytes'] = tuple(tuple(x) for x in value['minimum_runtime_disk_available_bytes'])
    for key in ('last_resource_errors','stop_markers'): value[key] = tuple(value[key])
    result = old.process.TaskProcessObservation(**value)
    if not io.same(asdict(result),doc): raise ValueError('exact observation required')
    return result


def job_view(root,count):
    """Bounded identity/byte snapshot, not a numerical or live Job certificate."""
    root = Path(root)
    names = set(RECORDS)|{'execution.lock','scratch_non_authoritative','worker_non_authoritative'}
    lock = io.identity(root/'execution.lock')
    if lock[2] != 1: raise ValueError('one-byte Job lock required')
    return (worker.hour._directory(root,names),lock,
        tuple(io.read_stable(root/n,prior.CAP) for n in RECORDS),
        prior.worker_view(root/'worker_non_authoritative',count))


def inspect_job(root,packet,specification,limits,*,pins,parent_declaration,intent_head,lineage):
    """Zero-solver conditional replay under external pins; no live receipt."""
    if type(pins) is not dict or set(pins) != set(RECORDS): raise ValueError('complete Job pins required')
    root = old.bounded.chunks.base.local._path(root)
    topology = worker.hour._directory(root,set(RECORDS)|{'execution.lock','scratch_non_authoritative','worker_non_authoritative'})
    views,docs = {},{}
    lock_view = io.identity(root/'execution.lock')
    if lock_view[2] != 1: raise ValueError('one-byte Job lock required')
    for name in RECORDS:
        docs[name],view = prior.read(root/name,pins[name])
        views[root/name] = (prior.CAP,view)
    req,launch,child,release,consume,result,observed = (docs[n] for n in
        ('request.json','launch.json','child.json','release_intent.json','consumed.json','worker_result.json','observation.json'))
    expected_parent = io.digest(io.encode(parent_declaration))
    args = dict(expected_head=intent_head,expected_source_identity=lineage,
        expected_request_key=replay.request_key(packet,specification,limits),expected_packet_audit=packet.audit_identity)
    anchor_path = Path(parent_declaration['root'])/'parent_anchor_non_authoritative'/f'{2*packet.relative_hour+1:03d}.json'
    anchor_view = io.read_stable(anchor_path,old.snapshot.anchor.MAX_RECORD_BYTES)
    anchor_pin = io.digest(anchor_view[0])
    views[anchor_path] = (old.snapshot.anchor.MAX_RECORD_BYTES,anchor_view)
    if (set(req) != prior.REQUEST_FIELDS or req['schema'] != ENTRY_SCHEMA
            or req['root'] != str(root) or req['implementation'] != implementation_identity()
            or req['route'] != 'owned_timed_hour_development' or req['parent_identity'] != expected_parent
            or req['parent_declaration'] != parent_declaration or req['pending_arguments'] != args
            or req['anchor_record'] != anchor_pin or any(req[k] is not False for k in FLAGS)):
        raise ValueError('Job request differs from source parent')
    item = old.snapshot.PendingWorkerInput(packet,specification,limits,io.encode(req['input_receipt']))
    item.validate(expected_receipt_sha256=req['input_receipt_sha256'])
    rec = req['input_receipt']
    if (rec['parent_identity'] != expected_parent or rec['anchor_record_sha256'] != anchor_pin
            or rec['journal_head'] != intent_head or rec['source_lineage_identity'] != lineage):
        raise ValueError('Job input receipt differs from parent intent')
    budget = old.process.TaskProcessBudget(**req['budget'])
    if budget.max_elapsed_seconds > 300 or not io.same(asdict(budget),req['budget']): raise ValueError('short exact Job budget required')
    resources = old.process.resources
    hv = launch['host']
    host = resources.HostResourceBudget(hv['additional_commit_bytes'],hv['commit_reserve_bytes'],
        tuple(resources.DirectoryDemand(**d) for d in hv['directories']))
    if not io.same(asdict(host),hv): raise ValueError('exact host inventory required')
    scratch = root/'scratch_non_authoritative'
    env = environment(scratch)
    identity = old.process.task_process_identity(launch['argv'],cwd=scratch,environment=env,budget=budget,
        host_budget=host,expected_host_identity=resources.resource_identity(host))
    expected_launch = dict(request_sha256=pins['request.json'],process_identity=identity,argv=launch['argv'],
        cwd=str(scratch),environment_sha256=io.digest(io.encode(env)),budget=asdict(budget),host=asdict(host))
    if not io.same(launch,expected_launch): raise ValueError('Job launch differs')
    old._validate_initial(docs['initial_observation.json'],host)
    pid,creation = child['pid'],child['creation_filetime']
    old._validate_observation(observation(observed),identity,pid,creation,budget)
    if not io.same(child,dict(pid=pid,creation_filetime=creation,process_identity=identity,
            request_sha256=pins['request.json'],initial_observation_sha256=pins['initial_observation.json'])):
        raise ValueError('Job child identity differs')
    if not io.same(release,dict(request_sha256=pins['request.json'],launch_sha256=pins['launch.json'],child_sha256=pins['child.json'])):
        raise ValueError('Job release differs')
    if not io.same(consume,dict(schema=ENTRY_SCHEMA,request_sha256=pins['request.json'],
            release_sha256=pins['release_intent.json'],child_sha256=pins['child.json'],pid=pid,creation_filetime=creation,**FLAGS)):
        raise ValueError('Job consumption differs')
    expected_result = dict(schema=ENTRY_SCHEMA,request_sha256=pins['request.json'],consume_sha256=pins['consumed.json'],
        input_receipt_sha256=item.receipt_sha256,pid=pid,creation_filetime=creation,
        worker_binding_sha256=result['worker_binding_sha256'],worker_terminal_sha256=result['worker_terminal_sha256'],
        worker_implementation=worker.implementation_identity(),projection_sha256=result['projection_sha256'],**FLAGS)
    if not io.same(result,expected_result): raise ValueError('Job result differs')
    wr = root/'worker_non_authoritative'
    count = len(worker.hour.prior.native.model_api.stage_order(packet.inputs))
    before = prior.worker_view(wr,count)
    checked = worker.inspect(wr,packet,specification,limits,expected_binding_sha=result['worker_binding_sha256'],
        expected_terminal_sha=result['worker_terminal_sha256'],expected_implementation=result['worker_implementation'])
    binding,_ = worker._read(wr/'binding.json')
    if (binding['pid'] != pid or binding['creation_filetime'] != creation
            or binding['controller_request_sha256'] != pins['request.json']
            or io.digest(checked['projection_payload']) != result['projection_sha256']):
        raise ValueError('worker result/process/request binding differs')
    prior.unchanged(views)
    if io.identity(root/'execution.lock') != lock_view or prior.worker_view(wr,count) != before or worker.hour._directory(root,set(RECORDS)|{
            'execution.lock','scratch_non_authoritative','worker_non_authoritative'}) != topology:
        raise ValueError('Job evidence changed during inspection')
    return checked['projection_payload']


@dataclass(frozen=True)
class Projection:
    projection_identity: str
    payload: bytes


@dataclass(frozen=True,init=False)
class ChildInspection:
    status: str
    head: str
    archive_identity: str
    stored_reports: int
    projection: Projection

    def __init__(self,values,*,_token=None):
        if _token is not _TOKEN: raise TypeError('fresh timed Job inspection required')
        for name,value in zip(self.__annotations__,values,strict=True):object.__setattr__(self,name,value)


class ChildReference:
    def __init__(self,root,job_root,packet,specification,limits,*,parent_declaration,intent_head,lineage,expected_head):
        self.root,self.job_root = Path(root),Path(job_root)
        self.context = packet,specification,limits
        self.parent,self.intent,self.lineage = parent_declaration,intent_head,lineage
        self.head = io.pin(expected_head);self.closed = False

    def inspect(self):
        if self.closed: raise ValueError('closed child reference')
        topology = worker.hour._directory(self.root,{'reference.json'})
        doc,view = prior.read(self.root/'reference.json',self.head)
        packet,specification,limits = self.context
        expected = reference(self.root,self.job_root,self.parent,self.intent,self.lineage,doc['job_pins'])
        if not io.same(doc,expected): raise ValueError('child reference context differs')
        payload = inspect_job(self.job_root,*self.context,pins=doc['job_pins'],parent_declaration=self.parent,
            intent_head=self.intent,lineage=self.lineage)
        if (io.read_stable(self.root/'reference.json',prior.CAP) != view
                or worker.hour._directory(self.root,{'reference.json'}) != topology):
            raise ValueError('child reference changed')
        projection = Projection(io.digest(io.encode([CHILD_SCHEMA,io.digest(payload)])),payload)
        return ChildInspection(('accepted',self.head,self.head,
            len(worker.hour.prior.native.model_api.stage_order(packet.inputs)),projection),_token=_TOKEN)

    def close(self): self.closed = True


def reference(root,job_root,parent,intent,lineage,pins):
    return dict(schema=CHILD_SCHEMA,root=str(root),job_root=str(job_root),parent_identity=io.digest(io.encode(parent)),
        intent_head=io.pin(intent),source_identity=io.pin(lineage),job_pins=pins,implementation=implementation_identity(),**FLAGS)


class SourceParent(bounded.SavedSourceParent):
    def _declare(self):
        value = super()._declare()
        value.update(schema=SCHEMA,implementation_identity=implementation_identity(),child_protocol=CHILD_SCHEMA)
        return value

    def _child(self,hour,packet,intent_head,lineage,*,expected_head,create=False):
        if create is not False: raise ValueError('Job reference must be published by controller')
        return ChildReference(self._root/f'hour_{hour:03d}_non_authoritative',
            self._root.parent/f'job_{hour:03d}_non_authoritative',packet,self._spec,self._limits,
            parent_declaration=self._declaration,intent_head=intent_head,lineage=lineage,expected_head=expected_head)

    def _outcome(self,hour,intent_head,result):
        if type(result) is not ChildInspection or result.status != 'accepted' or result.stored_reports != self._stages:
            raise ValueError('complete timed Job child required')
        return dict(schema=bounded.SCHEMA,kind='accepted',hour=hour,intent_head=intent_head,
            child_protocol=CHILD_SCHEMA,child_head=result.head,child_identity=result.archive_identity,
            stored_reports=result.stored_reports,projection_identity=result.projection.projection_identity)

    def _after(self,packet,result):
        if type(result) is not ChildInspection or type(result.projection) is not Projection: raise ValueError('timed child projection required')
        doc = json.loads(result.projection.payload)
        if (doc['schema'] != worker.hour.SCHEMA or doc['request_sha256'] != worker.hour.request_key(packet,self._spec,self._limits)
                or doc['before_identity'] != source._digest(packet.before)
                or len(doc['value']['canonical_locks']) != self._stages
                or any(doc[k] is not False for k in worker.hour.stage.capture.FLAGS)):
            raise ValueError('replayed timed projection differs')
        values = doc['value']
        after = source._owned(source.H1NormalBoundary,network_identity=values['network_identity'],
            completed_hours=values['completed_hours'],units=tuple((uid,on,float.fromhex(power),age)
                for uid,on,power,age in values['units']),evidence_role='numerical_lex_candidate')
        source._boundary(self._network,after,packet.relative_hour+1)
        return after

    def step_saved(self,*args,**kwargs): raise ValueError('timed parent requires Job controller')

    def close(self):
        with self._guard:
            self._closed = True
            errors = []
            for field in ('_journal','_anchor','_root_lease'):
                owner = getattr(self,field,None)
                setattr(self,field,None)
                if owner is not None:
                    try: owner.close()
                    except BaseException as error: errors.append(error)
            if errors: raise errors[0]
