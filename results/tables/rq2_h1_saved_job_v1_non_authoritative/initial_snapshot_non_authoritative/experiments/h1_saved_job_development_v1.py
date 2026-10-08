"""Create-once independent Windows Jobs for bounded saved-report hours only."""
import ctypes as c
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from math import isfinite
import os
from pathlib import Path
import sys

from experiments import h1_parent_snapshot_development_v1 as snapshot
from src.rq2_joint_deliverability_boundary_v1 import normal_task_process as process
from src.rq2_joint_deliverability_boundary_v1 import normal_worker as runtime

bounded, io, replay = snapshot.bounded, snapshot.io, snapshot.replay
SCHEMA = 'h1_saved_job_development_v1'
CONTENT_CAP = 262144
MIB = 1024**2
WORKER = Path(__file__).with_name('run_h1_saved_job_worker_development_v1.py')


def implementation_identity():
    return io.digest(io.encode([SCHEMA,snapshot.implementation_identity(),
        *[(str(Path(m.__file__).resolve()),sha256(Path(m.__file__).read_bytes()).hexdigest())
          for m in (process,process.process,process.resources,runtime)],
        sha256(Path(__file__).read_bytes()).hexdigest(),sha256(WORKER.read_bytes()).hexdigest()]))


def _write(path,value,cap=io.META_CAP):
    raw=io.encode(value)
    if len(raw)>cap:raise ValueError('saved Job record cap exceeded')
    io.write_new(path,raw)
    return io.digest(raw)


def _read(path,pin,cap=io.META_CAP):
    raw=io.read_stable(path,cap)[0]
    if io.digest(raw)!=io.pin(pin):raise ValueError('saved Job record pin differs')
    result=json.loads(raw)
    if io.encode(result)!=raw:raise ValueError('canonical saved Job record required')
    return result


@dataclass(frozen=True)
class SavedRaw:
    path: str
    sha256: str
    size: int

    def __post_init__(self):
        if (type(self.path) is not str or len(self.path)>1024 or not Path(self.path).is_absolute()
                or str(bounded.chunks.base.local._path(self.path))!=self.path
                or type(self.size) is not int or not 0<self.size<=io.RAW_CAP):
            raise ValueError('bounded absolute saved raw declaration required')
        io.pin(self.sha256)

    def read(self):
        self.__post_init__()
        raw,stamp=io.read_stable(Path(self.path),io.RAW_CAP)
        if len(raw)!=self.size or io.digest(raw)!=self.sha256:raise ValueError('saved source raw differs')
        return raw,stamp


def _current_process():
    native=process.process
    k=native._api()
    creation,end,kernel,user=(native.w.FILETIME() for _ in range(4))
    handle=native.HANDLE(-1)
    native._check(k.GetProcessTimes(handle,c.byref(creation),c.byref(end),c.byref(kernel),c.byref(user)))
    return os.getpid(),creation.dwLowDateTime | (creation.dwHighDateTime<<32)


def execute_saved_worker(request_path,request_pin):
    """Fixed saved route. No native solver gate or resume parameter exists."""
    with replay.guard.solver_calls_forbidden():
        path=bounded.chunks.base.local._path(request_path)
        request=_read(path,request_pin,CONTENT_CAP)
        root=path.parent
        if (path.name!='request.json' or request['schema']!=SCHEMA or request['root']!=str(root)
                or Path.cwd().resolve()!=root/'scratch_non_authoritative'
                or request['implementation']!=implementation_identity()
                or request['route']!='saved_reports_only'
                or any(request[k] is not False for k in ('native_execution_authorized','formal_execution_ready','formal_result'))):
            raise ValueError('exact saved-only worker request required')
        release_raw=io.read_stable(root/'release_intent.json',io.META_CAP)[0]
        release_pin=io.digest(release_raw)
        release=_read(root/'release_intent.json',release_pin)
        launch=_read(root/'launch.json',release['launch_sha256'],CONTENT_CAP)
        child=_read(root/'child.json',release['child_sha256'])
        pid,creation=_current_process()
        environment=dict(os.environ)
        runtime._environment(environment)
        if (release!=dict(request_sha256=request_pin,launch_sha256=release['launch_sha256'],child_sha256=release['child_sha256'])
                or launch['request_sha256']!=request_pin or child!=dict(pid=pid,creation_filetime=creation,
                    process_identity=launch['process_identity'],request_sha256=request_pin)
                or launch['argv']!=sys.orig_argv or launch['cwd']!=str(Path.cwd().resolve())
                or launch['environment_sha256']!=io.digest(io.encode(environment))
                or request['budget']!=launch['budget']):
            raise ValueError('released exact child identity required')
        consumed=dict(request_sha256=request_pin,release_sha256=release_pin,
            child_sha256=release['child_sha256'],pid=pid,creation_filetime=creation)
        consume_pin=_write(root/'consumed.json',consumed)  # Before snapshot or any child creation.
        reader=snapshot.open_snapshot(request['parent_declaration'],
            expected_parent_identity=request['parent_identity'],expected_anchor_record=request['anchor_record'])
        try:item=reader.pending_input(**request['pending_arguments'])
        finally:reader.close()
        item.validate(expected_receipt_sha256=request['input_receipt_sha256'])
        if io.encode(request['input_receipt'])!=item.receipt:raise ValueError('worker reconstructed input differs')
        raws=tuple(SavedRaw(**value) for value in request['saved_raws'])
        if len(raws)!=json.loads(item.receipt)['stage_slots']:raise ValueError('complete saved stage inventory required')
        child_root=Path(request['parent_declaration']['root'])/f'hour_{item.packet.relative_hour:03d}_non_authoritative'
        owner=bounded.prior.AttestedChild(child_root,item.packet,item.specification,item.limits,
            parent_intent_head=request['pending_arguments']['expected_head'],
            source_lineage_identity=request['pending_arguments']['expected_source_identity'],create=True)
        try:
            for raw in raws:owner.record_report(raw.read()[0],expected_head=owner.head)
            result=owner.finish(expected_head=owner.head)
        finally:owner.close()
        # These checks precede the only worker result publication.
        _read(path,request_pin,CONTENT_CAP)
        _read(root/'release_intent.json',release_pin)
        _read(root/'consumed.json',consume_pin)
        if request['implementation']!=implementation_identity():raise ValueError('saved worker implementation drift')
        _write(root/'worker_result.json',dict(schema=SCHEMA,request_sha256=request_pin,
            input_receipt_sha256=item.receipt_sha256,consume_sha256=consume_pin,child_head=result.head,
            child_identity=result.archive_identity,pid=pid,creation_filetime=creation,
            solver_calls=0,native_execution_authorized=False,formal_result=False))


def _argv(request,pin):return [sys.executable,'-I','-B',str(WORKER),str(request),pin]


def _validate_observation(observed,identity,pid,creation,budget):
    if (type(observed) is not process.TaskProcessObservation or observed.process_identity!=identity
            or type(observed.pid) is not int or observed.pid!=pid
            or type(observed.creation_filetime) is not int or observed.creation_filetime!=creation
            or type(observed.exit_code) is not int or observed.exit_code!=0 or observed.reason!='child_exited'
            or observed.whole_job_quiescent is not True or observed.job_commit_limits_configured is not True
            or type(observed.last_resource_errors) is not tuple or observed.last_resource_errors
            or observed.observation_error_type is not None
            or type(observed.runtime_samples) is not int or observed.runtime_samples<0
            or type(observed.elapsed_seconds) not in (int,float) or not isfinite(observed.elapsed_seconds)
            or not 0<=observed.elapsed_seconds<=budget.max_elapsed_seconds+budget.max_quiescence_seconds
            or type(observed.job_peak_process_commit_bytes) is not int
            or not 0<observed.job_peak_process_commit_bytes<=budget.max_process_commit_bytes
            or type(observed.job_peak_total_commit_bytes) is not int
            or not 0<observed.job_peak_total_commit_bytes<=budget.max_job_commit_bytes
            or any(getattr(observed,k) is not False for k in ('hard_disk_quota_enforced',
                'whole_task_resources_verified','numerical_evidence_verified','formal_result'))):
        raise ValueError('saved Job unresolved; no retry or parent outcome')


class SavedJobController:
    def __init__(self,root,network,specification,limits,*,origin,upstream_root,config_path,dc_bus,hours=192,
                 budget):
        if type(budget) is not process.TaskProcessBudget:raise ValueError('exact short saved Job budget required')
        budget.__post_init__()
        if budget.max_elapsed_seconds>300:raise ValueError('short saved Job development ceiling is 300 seconds')
        self._budget=budget
        self._guard=bounded.chunks._Exclusive()
        self._implementation=implementation_identity()
        self._parent=None
        self._lease=bounded.chunks.base.local._Lease(Path(root),True)
        try:
            self._parent=bounded.SavedSourceParent(self._lease.root/'source_parent_non_authoritative',
                network,specification,limits,origin=origin,upstream_root=upstream_root,
                config_path=config_path,dc_bus=dc_bus,hours=hours,create=True)
        except BaseException:
            self._lease.close()
            raise

    def _check(self):
        if self._lease is None:raise ValueError('closed saved Job controller')
        self._lease.check()
        self._parent._check()
        if implementation_identity()!=self._implementation:raise ValueError('saved Job controller implementation drift')

    def inspect(self):
        with self._guard:
            self._check()
            return self._parent.inspect()

    def step_saved_job(self,saved_raws,*,expected_source_identity,expected_head):
        p=self._parent
        with self._guard,p._guard,replay.guard.solver_calls_forbidden():
            try:
                self._check()
                if type(saved_raws) is not tuple or len(saved_raws)!=p._stages or any(type(r) is not SavedRaw for r in saved_raws):
                    raise ValueError('exact complete saved raw tuple required')
                raw_views=tuple(raw.read()[1] for raw in saved_raws)
                state,before,previous=p._restore()
                if not p._writable or state.status!='ready' or state.head!=expected_head:raise ValueError('ready live parent required')
                receipt=p._load(state.completed_hours,expected_source_identity)
                packet=p._packet(receipt,state.completed_hours,before,previous)
                p._append(p._intent(state.completed_hours,receipt,packet),receipt.audit_payload)
                head=p._journal.head
                pending=dict(expected_head=head,expected_source_identity=receipt.identity,
                    expected_request_key=replay.request_key(packet,p._spec,p._limits),expected_packet_audit=packet.audit_identity)
                anchor=p._anchor.inspect().record_sha256
                reader=snapshot.open_snapshot(p._declaration,expected_parent_identity=p.identity,expected_anchor_record=anchor)
                try:item=reader.pending_input(**pending)
                finally:reader.close()
                job_result=self._job(state.completed_hours,item,pending,anchor,saved_raws)
                self._check()
                if tuple(raw.read()[1] for raw in saved_raws)!=raw_views:raise ValueError('saved input file view changed')
                reopened=p._child(state.completed_hours,packet,head,receipt.identity,expected_head=job_result['child_head'])
                try:result=reopened.inspect()
                finally:reopened.close()
                if result.archive_identity!=job_result['child_identity']:raise ValueError('worker child identity differs from replay')
                p._restore()
                self._check()
                p._append(p._outcome(state.completed_hours,head,result))
                return p._restore()[0]
            except BaseException:
                p._poisoned=True
                raise

    def _job(self,hour,item,pending,anchor,raws):
        p=self._parent
        lease=bounded.chunks.base.local._Lease(self._lease.root/f'job_{hour:03d}_non_authoritative',True)
        try:
            root=lease.root;scratch=root/'scratch_non_authoritative';scratch.mkdir()
            request=dict(schema=SCHEMA,root=str(root),implementation=self._implementation,
                parent_declaration=p._declaration,parent_identity=p.identity,anchor_record=anchor,pending_arguments=pending,
                input_receipt=json.loads(item.receipt),input_receipt_sha256=item.receipt_sha256,
                saved_raws=[asdict(r) for r in raws],route='saved_reports_only',budget=asdict(self._budget),
                native_execution_authorized=False,formal_execution_ready=False,formal_result=False)
            request_pin=_write(root/'request.json',request,CONTENT_CAP)
            resources=process.resources
            host=resources.HostResourceBudget(self._budget.max_job_commit_bytes+256*MIB,32*MIB,(
                resources.DirectoryDemand('child',str(p._root),bounded.prior.child_storage_bound(p._stages)['logical_bytes'],32*MIB),
                resources.DirectoryDemand('records',str(root),job_storage_bound()['logical_bytes'],32*MIB),
                resources.DirectoryDemand('scratch',str(scratch),8*MIB,32*MIB)))
            env=runtime.development_environment();env.update(TEMP=str(scratch),TMP=str(scratch));runtime._environment(env)
            argv=_argv(root/'request.json',request_pin)
            arguments=dict(cwd=scratch,environment=env,budget=self._budget,host_budget=host,
                expected_host_identity=resources.resource_identity(host))
            identity=process.task_process_identity(argv,**arguments)
            launch_pin=_write(root/'launch.json',dict(request_sha256=request_pin,process_identity=identity,
                argv=argv,cwd=str(scratch),environment_sha256=io.digest(io.encode(env)),
                budget=asdict(self._budget),host=asdict(host)),CONTENT_CAP)
            with process.normal_task_child(argv,**arguments,expected_process_identity=identity) as child:
                pid,creation=child.pid,child.creation_filetime
                child_pin=_write(root/'child.json',dict(pid=pid,creation_filetime=creation,
                    process_identity=identity,request_sha256=request_pin))
                self._check();lease.check()
                current=p._restore()[0]
                if (current.status!='pending_unknown' or current.head!=pending['expected_head']
                        or p._anchor.inspect().record_sha256!=anchor
                        or (p._root/f'hour_{hour:03d}_non_authoritative').exists()):
                    raise ValueError('parent changed before saved Job release')
                release_pin=_write(root/'release_intent.json',dict(request_sha256=request_pin,launch_sha256=launch_pin,child_sha256=child_pin))
                child.release()
                observed=child.wait()
            observation_pin=_write(root/'observation.json',asdict(observed),CONTENT_CAP)
            _validate_observation(observed,identity,pid,creation,self._budget)
            self._check();lease.check()
            for name,pin,cap in (('request',request_pin,CONTENT_CAP),('launch',launch_pin,CONTENT_CAP),
                                  ('child',child_pin,io.META_CAP),('release_intent',release_pin,io.META_CAP)):
                _read(root/(name+'.json'),pin,cap)
            consumed=dict(request_sha256=request_pin,release_sha256=release_pin,child_sha256=child_pin,pid=pid,creation_filetime=creation)
            consumed_pin=io.digest(io.encode(consumed))
            if _read(root/'consumed.json',consumed_pin)!=consumed:raise ValueError('saved consumption record differs')
            raw=io.read_stable(root/'worker_result.json',io.META_CAP)[0];result_pin=io.digest(raw)
            result=_read(root/'worker_result.json',result_pin)
            io.pin(result['child_head']);io.pin(result['child_identity'])
            expected=dict(schema=SCHEMA,request_sha256=request_pin,input_receipt_sha256=item.receipt_sha256,
                consume_sha256=consumed_pin,child_head=result['child_head'],child_identity=result['child_identity'],
                pid=pid,creation_filetime=creation,solver_calls=0,native_execution_authorized=False,formal_result=False)
            if not io.same(result,expected):raise ValueError('saved worker report differs')
            _write(root/'job_checks.json',dict(request_sha256=request_pin,worker_result_sha256=result_pin,
                consumed_sha256=consumed_pin,observation_sha256=observation_pin,saved_job_quiescent=True,
                native_execution_authorized=False,whole_task_resources_verified=False,formal_result=False))
            return result
        finally:lease.close()

    def close(self):
        with self._guard:
            self._parent.close()
            lease,self._lease=self._lease,None
            if lease is not None:lease.close()

    __copy__=bounded.chunks.DevelopmentH1ChunkJournal.__copy__
    __deepcopy__=bounded.chunks.DevelopmentH1ChunkJournal.__deepcopy__
    __reduce_ex__=bounded.chunks.DevelopmentH1ChunkJournal.__reduce_ex__


def job_storage_bound():
    return dict(logical_bytes=3*CONTENT_CAP+5*io.META_CAP+4096+1,files=10,directories=2,
        filesystem_allocation_bound_proven=False,resource_admission=False,formal_result=False)
