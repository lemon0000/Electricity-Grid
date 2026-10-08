"""Create-once timed worker Jobs and source/carry outcomes; development only.

step() is native-capable. Actual native use needs a concrete admitted package
and new explicit authorization. Tests replace the launcher with synthetic code.
The short development ceiling is not the full research resource contract.
"""
from dataclasses import asdict
from pathlib import Path
import sys

from experiments import h1_timed_job_parent_development_v1 as parent
from experiments import h1_timed_job_snapshot_development_v1 as snapshot
from experiments import h1_timed_released_worker_development_v2 as entry

old,io,worker = parent.old,parent.io,parent.worker


def _argv(request,pin):
    repository = str(Path(__file__).resolve().parents[1])
    code = (f'import sys;sys.path.insert(0,{repository!r});'
        'from experiments.h1_timed_released_worker_development_v2 import execute;execute(*sys.argv[1:])')
    return [sys.executable,'-I','-B','-c',code,str(request),pin]


def job_content_bound(stages):
    if type(stages) is not int or not 1 <= stages <= 232: raise ValueError('bounded stages required')
    stage_files = worker.hour.stage._FILES
    hour_bytes = stages*(sum(stage_files.values())+io.META_CAP)+2*io.META_CAP+worker.hour.PROJECTION_CAP
    return dict(logical_bytes=hour_bytes+2*io.META_CAP+1+len(parent.RECORDS)*entry.CAP+1,
        files=stages*(len(stage_files)+1)+3+3+len(parent.RECORDS)+1,
        scratch_included=False,filesystem_allocation_bound_proven=False,resource_admission=False,formal_result=False)


class Controller:
    def __init__(self,root,network,specification,limits,*,origin,upstream_root,config_path,dc_bus,hours=192,budget):
        if type(budget) is not old.process.TaskProcessBudget: raise ValueError('exact short Job budget required')
        budget.__post_init__()
        if budget.max_elapsed_seconds > 300: raise ValueError('short development ceiling is 300 seconds')
        self._budget = budget
        self._guard = old.bounded.chunks._Exclusive()
        self._implementation = parent.implementation_identity()
        self._parent = None
        self._lease = old.bounded.chunks.base.local._Lease(Path(root),True)
        try:
            self._parent = parent.SourceParent(self._lease.root/'source_parent_non_authoritative',
                network,specification,limits,origin=origin,upstream_root=upstream_root,config_path=config_path,
                dc_bus=dc_bus,hours=hours,create=True)
        except BaseException:
            self.close();raise

    def _check(self):
        if self._lease is None: raise ValueError('closed timed Job controller')
        self._lease.check();self._parent._check()
        if parent.implementation_identity() != self._implementation: raise ValueError('controller implementation drift')

    def inspect(self):
        with self._guard:
            self._check();return self._parent.inspect()

    def step(self,*,expected_source_identity,expected_head):
        p = self._parent
        with self._guard,p._guard,old.replay.guard.solver_calls_forbidden():
            try:
                self._check()
                state,before,previous = p._restore()
                if not p._writable or state.status != 'ready' or state.head != expected_head:
                    raise ValueError('ready live timed parent required')
                hour = state.completed_hours
                source = p._load(hour,expected_source_identity)
                packet = p._packet(source,hour,before,previous)
                p._append(p._intent(hour,source,packet),source.audit_payload)
                head = p._journal.head
                pending = dict(expected_head=head,expected_source_identity=source.identity,
                    expected_request_key=old.replay.request_key(packet,p._spec,p._limits),expected_packet_audit=packet.audit_identity)
                anchor = p._anchor.inspect().record_sha256
                reader = snapshot.open_snapshot(p._declaration,expected_parent_identity=p.identity,expected_anchor_record=anchor)
                try: item = reader.pending_input(**pending)
                finally: reader.close()
                pins = self._job(hour,item,pending,anchor)
                self._check()
                job_root = self._lease.root/f'job_{hour:03d}_non_authoritative'
                view = parent.job_view(job_root,p._stages)
                parent.inspect_job(job_root,packet,p._spec,p._limits,pins=pins,parent_declaration=p._declaration,
                    intent_head=head,lineage=source.identity)
                # All source/clock/carry facts must still match after whole-Job exit.
                reader = snapshot.open_snapshot(p._declaration,expected_parent_identity=p.identity,expected_anchor_record=anchor)
                try: fresh = reader.pending_input(**pending)
                finally: reader.close()
                if fresh.receipt != item.receipt or fresh.packet != item.packet: raise ValueError('parent source changed after Job')
                if parent.job_view(job_root,p._stages) != view: raise ValueError('Job changed before child reference')
                child_root = p._root/f'hour_{hour:03d}_non_authoritative'
                child_root.mkdir(exist_ok=False)
                pin = entry.write(child_root/'reference.json',parent.reference(child_root,job_root,p._declaration,head,source.identity,pins))
                child = p._child(hour,packet,head,source.identity,expected_head=pin)
                try: result = child.inspect()
                finally: child.close()
                p._restore();self._check()
                if parent.job_view(job_root,p._stages) != view: raise ValueError('Job changed before parent outcome')
                p._append(p._outcome(hour,head,result))
                final = p._restore()[0]
                if parent.job_view(job_root,p._stages) != view: raise ValueError('Job changed before step return')
                return final
            except BaseException:
                p._poisoned = True
                raise

    def _job(self,hour,item,pending,anchor):
        lease = old.bounded.chunks.base.local._Lease(self._lease.root/f'job_{hour:03d}_non_authoritative',True)
        try:
            root = lease.root;scratch = root/'scratch_non_authoritative';scratch.mkdir()
            p = self._parent
            request = dict(schema=entry.SCHEMA,root=str(root),implementation=self._implementation,
                parent_declaration=p._declaration,parent_identity=p.identity,anchor_record=anchor,pending_arguments=pending,
                input_receipt=old.json.loads(item.receipt),input_receipt_sha256=item.receipt_sha256,
                budget=asdict(self._budget),route='owned_timed_hour_development',**entry.FLAGS)
            pins = {'request.json':entry.write(root/'request.json',request)}
            resources = old.process.resources
            host = resources.HostResourceBudget(self._budget.max_job_commit_bytes+256*old.MIB,32*old.MIB,(
                resources.DirectoryDemand('timed_job',str(root),job_content_bound(p._stages)['logical_bytes'],32*old.MIB),
                resources.DirectoryDemand('parent_reference',str(p._root),entry.CAP,32*old.MIB),
                resources.DirectoryDemand('scratch',str(scratch),8*old.MIB,32*old.MIB)))
            env = parent.environment(scratch)
            argv = _argv(root/'request.json',pins['request.json'])
            arguments = dict(cwd=scratch,environment=env,budget=self._budget,host_budget=host,
                expected_host_identity=resources.resource_identity(host))
            identity = old.process.task_process_identity(argv,**arguments)
            pins['launch.json'] = entry.write(root/'launch.json',dict(request_sha256=pins['request.json'],
                process_identity=identity,argv=argv,cwd=str(scratch),environment_sha256=io.digest(io.encode(env)),
                budget=asdict(self._budget),host=asdict(host)))
            views = {root/n:(entry.CAP,entry.read(root/n,h)[1]) for n,h in pins.items()}
            with old.process.normal_task_child(argv,**arguments,expected_process_identity=identity) as child:
                pid,creation = child.pid,child.creation_filetime
                initial = old.json.loads(io.encode(asdict(child.initial_observation)))
                old._validate_initial(initial,host)
                pins['initial_observation.json'] = entry.write(root/'initial_observation.json',initial)
                pins['child.json'] = entry.write(root/'child.json',dict(pid=pid,creation_filetime=creation,
                    process_identity=identity,request_sha256=pins['request.json'],initial_observation_sha256=pins['initial_observation.json']))
                self._check();lease.check()
                if p._restore()[0].head != pending['expected_head'] or p._anchor.inspect().record_sha256 != anchor:
                    raise ValueError('parent changed before Job release')
                pins['release_intent.json'] = entry.write(root/'release_intent.json',dict(request_sha256=pins['request.json'],
                    launch_sha256=pins['launch.json'],child_sha256=pins['child.json']))
                for name,pin in pins.items():
                    if root/name not in views: views[root/name] = (entry.CAP,entry.read(root/name,pin)[1])
                entry.unchanged(views)
                child.release();observed = child.wait()
            pins['observation.json'] = entry.write(root/'observation.json',asdict(observed))
            old._validate_observation(observed,identity,pid,creation,self._budget)
            self._check();lease.check();entry.unchanged(views)
            # Never read or adopt worker output until live exit0/whole-Job quiet.
            for name in ('consumed.json','worker_result.json'):
                pins[name] = io.digest(io.read_stable(root/name,entry.CAP)[0])
            parent.inspect_job(root,item.packet,item.specification,item.limits,pins=pins,parent_declaration=p._declaration,
                intent_head=pending['expected_head'],lineage=pending['expected_source_identity'])
            entry.unchanged(views);self._check();lease.check()
            return pins
        finally:
            owner,lease = lease,None
            if owner is not None: owner.close()

    def close(self):
        with self._guard:
            try:
                if self._parent is not None: self._parent.close()
            finally:
                lease,self._lease = self._lease,None
                if lease is not None: lease.close()

    __copy__ = old.bounded.chunks.DevelopmentH1ChunkJournal.__copy__
    __deepcopy__ = old.bounded.chunks.DevelopmentH1ChunkJournal.__deepcopy__
    __reduce_ex__ = old.bounded.chunks.DevelopmentH1ChunkJournal.__reduce_ex__
