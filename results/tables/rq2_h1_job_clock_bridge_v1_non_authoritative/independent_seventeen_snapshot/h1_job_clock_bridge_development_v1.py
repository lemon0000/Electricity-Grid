"""Owned QPC envelopes around the timed Job transaction; development only.

Persisted records are conditional evidence, never live process authority.
The observed residual includes observer work and excludes the confirmation tail.
No complete lifecycle, physical-clock error bound or component budget is proved.
"""
from dataclasses import dataclass
from pathlib import Path
import sys
import threading
import time

from experiments import h1_timed_job_controller_development_v1 as base

io, worker = base.io, base.worker
SCHEMA = 'h1_job_clock_bridge_development_v1'
FLAGS = dict(base.parent.FLAGS)
CAP = base.entry.CAP
_CLOCK = time.perf_counter_ns
_TOKEN = object()


def implementation_identity():
    return io.digest(io.encode([SCHEMA,base.parent.implementation_identity(),io.digest(Path(__file__).read_bytes())]))


def profile():
    if sys.version_info < (3,10) or _CLOCK is not worker._CLOCK or time.perf_counter_ns is not _CLOCK:
        raise ValueError('system-wide fixed CPython QPC clock required')
    return worker.clock_profile()


def tick(previous):
    value = worker._integer(_CLOCK())
    if value < previous: raise ValueError('controller clock reversal')
    return value


def analyse(*, transaction_start, job_start, worker_start, worker_end, job_end, transaction_end, native_total):
    values = tuple(worker._integer(x) for x in
        (transaction_start,job_start,worker_start,worker_end,job_end,transaction_end,native_total))
    if list(values[:6]) != sorted(values[:6]) or native_total > worker_end-worker_start:
        raise ValueError('contained shared-clock intervals required')
    return dict(transaction_wall_ns=transaction_end-transaction_start,
        job_window_ns=job_end-job_start,worker_window_ns=worker_end-worker_start,
        native_total_ns=native_total,observed_non_native_ns=transaction_end-transaction_start-native_total)


def additional_content_bound(hours):
    if type(hours) is not int or not 1 <= hours <= 192: raise ValueError('bounded hours required')
    return dict(logical_bytes=(1+3*hours)*CAP+1,files=2+3*hours,directories=1+hours,
        filesystem_allocation_bound_proven=False,resource_admission=False)


def inspect(root,index,packet,specification,limits,*,binding_pin,intent_pin,terminal_pin):
    """Fresh full science plus conditional timing arithmetic; no live receipt."""
    root = Path(root).absolute()
    if type(index) is not int or not 0 <= index < 192: raise ValueError('hour index required')
    directory = root/f'{index:03d}'
    identity = worker.hour._directory(directory,{'intent.json','job.json','terminal.json'})
    binding,bv = base.entry.read(root/'binding.json',binding_pin)
    intent,iv = base.entry.read(directory/'intent.json',intent_pin)
    terminal,tv = base.entry.read(directory/'terminal.json',terminal_pin)
    if (set(binding) != {'schema','implementation','parent_identity','pid','creation_filetime','thread_id','clock','hours',*FLAGS}
            or binding['schema'] != SCHEMA or binding['implementation'] != implementation_identity()
            or binding['clock'] != profile() or type(binding['hours']) is not int or not index < binding['hours'] <= 192
            or any(binding[k] is not False for k in FLAGS)):
        raise ValueError('clock binding differs')
    for name in ('pid','creation_filetime','thread_id'):
        if worker._integer(binding[name]) == 0: raise ValueError('controller owner required')
    io.pin(binding['parent_identity'])
    if (set(intent) != {'schema','binding_sha256','index','start_ns','expected_head','source_identity','previous_sha256'}
            or intent['schema'] != SCHEMA or intent['binding_sha256'] != binding_pin
            or type(intent['index']) is not int or intent['index'] != index):
        raise ValueError('clock intent differs')
    for name in ('expected_head','source_identity','previous_sha256'): io.pin(intent[name])
    if (set(terminal) != {'schema','intent_sha256','end_ns','job_start_ns','job_end_ns','job_pins','outcome_head','job_record_sha256','outcome_anchor_sha256',*FLAGS}
            or terminal['schema'] != SCHEMA or terminal['intent_sha256'] != intent_pin
            or any(terminal[k] is not False for k in FLAGS)):
        raise ValueError('clock terminal differs')
    io.pin(terminal['outcome_head'])
    previous_views = {}
    if index == 0:
        if intent['previous_sha256'] != binding_pin: raise ValueError('first timing predecessor differs')
    else:
        previous_path = root/f'{index-1:03d}'/'terminal.json'
        previous,pv = base.entry.read(previous_path,intent['previous_sha256'])
        previous_views[previous_path] = (CAP,pv)
        if (previous['schema'] != SCHEMA or previous['outcome_head'] != intent['expected_head']
                or worker._integer(previous['end_ns']) > worker._integer(intent['start_ns'])):
            raise ValueError('timing predecessor/order differs')
    job_record,jv = base.entry.read(directory/'job.json',terminal['job_record_sha256'])
    if not io.same(job_record,dict(schema=SCHEMA,intent_sha256=intent_pin,start_ns=terminal['job_start_ns'],
            end_ns=terminal['job_end_ns'],job_pins=terminal['job_pins'])):
        raise ValueError('job timing record differs')
    job = root.parent/f'job_{index:03d}_non_authoritative'
    count = len(worker.hour.prior.native.model_api.stage_order(packet.inputs))
    view = base.parent.job_view(job,count)
    pins = terminal['job_pins']
    req,_ = base.entry.read(job/'request.json',pins['request.json'])
    if (req['parent_identity'] != binding['parent_identity']
            or req['pending_arguments']['expected_source_identity'] != intent['source_identity']):
        raise ValueError('timing source/parent differs')
    anchor_root = Path(req['parent_declaration']['root'])/'parent_anchor_non_authoritative'
    intent_anchor,iav = base.entry.read(anchor_root/f'{2*index+1:03d}.json',req['anchor_record'])
    outcome_anchor,oav = base.entry.read(anchor_root/f'{2*index+2:03d}.json',terminal['outcome_anchor_sha256'])
    if (intent_anchor['previous_registry_head'] != intent['expected_head']
            or outcome_anchor['registry_head'] != terminal['outcome_head']
            or outcome_anchor['previous_registry_head'] != req['pending_arguments']['expected_head']):
        raise ValueError('timing parent anchor transition differs')
    base.parent.inspect_job(job,packet,specification,limits,pins=pins,parent_declaration=req['parent_declaration'],
        intent_head=req['pending_arguments']['expected_head'],lineage=intent['source_identity'])
    child,_ = base.entry.read(job/'child.json',pins['child.json'])
    result,_ = base.entry.read(job/'worker_result.json',pins['worker_result.json'])
    wr = job/'worker_non_authoritative'
    wb,_ = base.entry.read(wr/'binding.json',result['worker_binding_sha256'])
    wt,_ = base.entry.read(wr/'terminal.json',result['worker_terminal_sha256'])
    if (wb['clock'] != binding['clock'] or wb['pid'] != child['pid']
            or wb['creation_filetime'] != child['creation_filetime'] or wb['pid'] == binding['pid']):
        raise ValueError('same-clock independent worker identity required')
    values = analyse(transaction_start=intent['start_ns'],job_start=terminal['job_start_ns'],
        worker_start=wb['start_ns'],worker_end=wt['end_ns'],job_end=terminal['job_end_ns'],
        transaction_end=terminal['end_ns'],native_total=wt['native_total_ns'])
    base.entry.unchanged({root/'binding.json':(CAP,bv),directory/'intent.json':(CAP,iv),directory/'terminal.json':(CAP,tv),directory/'job.json':(CAP,jv),
        anchor_root/f'{2*index+1:03d}.json':(CAP,iav),anchor_root/f'{2*index+2:03d}.json':(CAP,oav)})
    base.entry.unchanged(previous_views)
    if base.parent.job_view(job,count) != view or worker.hour._directory(directory,{'intent.json','job.json','terminal.json'}) != identity:
        raise ValueError('clock evidence changed during inspection')
    return dict(values,live_clock_bridge_authenticated=False,parent_prefix_verified=False,
        confirmation_tail_ns=None,**FLAGS)


@dataclass(frozen=True,init=False)
class Observation:
    index: int
    outcome_head: str
    terminal_sha256: str
    transaction_wall_ns: int
    native_total_ns: int
    observed_non_native_ns: int
    confirmation_tail_ns: int
    live_clock_profile_and_containment_checked: bool

    def __init__(self,values,*,_token=None):
        if _token is not _TOKEN: raise TypeError('owned controller return required')
        for name,value in zip(self.__annotations__,values,strict=True): object.__setattr__(self,name,value)


class Controller(base.Controller):
    def __init__(self,*args,**kwargs):
        self._clock_owner = worker.job._current_process()+(threading.get_ident(),)
        self._clock_profile = profile()
        self._clock_guard = threading.Lock()
        self._clock_lease = None
        self._clock_poisoned = self._clock_closed = False
        self._clock_views = {}
        self._clock_directories = {}
        self._clock_last = tick(0)
        self._clock_index = 0
        self._clock_pending = None
        self.last_observation = None
        self._clock_implementation = implementation_identity()
        super().__init__(*args,**kwargs)
        try:
            self.clock_root = self._lease.root/'clock_bridge_non_authoritative'
            self._clock_lease = base.old.bounded.chunks.base.local._Lease(self.clock_root,True)
            self._clock_hours = kwargs.get('hours',192)
            if type(self._clock_hours) is not int or self._clock_hours != self._parent._declaration['hours']:
                raise ValueError('exact parent clock hour count required')
            self.binding_pin = self._save(self.clock_root/'binding.json',dict(schema=SCHEMA,
                implementation=self._clock_implementation,parent_identity=self._parent.identity,
                pid=self._clock_owner[0],creation_filetime=self._clock_owner[1],thread_id=self._clock_owner[2],
                clock=self._clock_profile,hours=self._clock_hours,**FLAGS))
            self._clock_previous = self.binding_pin
        except BaseException:
            self.close();raise

    def _save(self,path,doc):
        pin = base.entry.write(path,doc)
        _,view = base.entry.read(path,pin)
        self._clock_views[path] = (CAP,view)
        return pin

    def _clock_check(self):
        if (self._clock_poisoned or self._clock_closed or self._clock_lease is None
                or worker.job._current_process()+(threading.get_ident(),) != self._clock_owner
                or profile() != self._clock_profile or implementation_identity() != self._clock_implementation):
            raise ValueError('clock controller state/owner differs')
        self._clock_lease.check()
        base.entry.unchanged(self._clock_views)
        names = {'execution.lock'}|{p.name if p.parent == self.clock_root else p.parent.name for p in self._clock_views}
        worker.hour._directory(self.clock_root,names)
        for p in {p.parent for p in self._clock_views if p.parent != self.clock_root}:
            if worker.hour._directory(p,{v.name for v in self._clock_views if v.parent == p}) != self._clock_directories[p]:
                raise ValueError('clock hour directory replaced')

    def inspect(self):
        if not self._clock_guard.acquire(blocking=False): raise ValueError('clock controller active')
        try:
            self._clock_check()
            return super().inspect()
        except BaseException:
            self._clock_poisoned = True
            self._parent._poisoned = True
            raise
        finally: self._clock_guard.release()

    def _headroom(self):
        # Combined same-volume demands include future clock records; observation
        # is neither reservation nor FS-allocation/full-task admission.
        r = base.old.process.resources
        budget = r.HostResourceBudget(self._budget.max_job_commit_bytes+256*base.old.MIB,32*base.old.MIB,(
            r.DirectoryDemand('job_content',str(self._lease.root),base.job_content_bound(self._parent._stages)['logical_bytes'],32*base.old.MIB),
            r.DirectoryDemand('parent_updates',str(self._parent._root),base.parent_update_bound(),32*base.old.MIB),
            r.DirectoryDemand('clock_remaining',str(self.clock_root),3*(self._clock_hours-self._clock_index)*CAP,32*base.old.MIB),
            r.DirectoryDemand('scratch',str(self._lease.root),8*base.old.MIB,32*base.old.MIB)))
        identity = r.resource_identity(budget)
        result = r.observe_headroom(budget,expected_request_identity=identity)
        if (type(result) is not r.HostHeadroomObservation or result.request_identity != identity
                or any(getattr(result,k) is not False for k in ('resource_reservation_held',
                    'hard_resource_limits_enforced','whole_task_resources_verified','formal_run_authorized','formal_result'))):
            raise ValueError('exact nonauthoritative headroom observation required')
        if result.errors or not result.observed_headroom_sufficient: raise ValueError('clock combined headroom unavailable')

    def _job(self,index,item,pending,anchor):
        if self._clock_pending is not None or not self._clock_guard.locked(): raise ValueError('single owned Job envelope required')
        self._clock_check()
        start = tick(self._clock_start)
        pins = super()._job(index,item,pending,anchor)
        end = tick(start)
        self._clock_check()
        root = self._lease.root/f'job_{index:03d}_non_authoritative'
        result,_ = base.entry.read(root/'worker_result.json',pins['worker_result.json'])
        wr = root/'worker_non_authoritative'
        wb,_ = base.entry.read(wr/'binding.json',result['worker_binding_sha256'])
        wt,_ = base.entry.read(wr/'terminal.json',result['worker_terminal_sha256'])
        if wb['clock'] != self._clock_profile: raise ValueError('worker clock profile differs')
        analyse(transaction_start=self._clock_start,job_start=start,worker_start=wb['start_ns'],
            worker_end=wt['end_ns'],job_end=end,transaction_end=end,native_total=wt['native_total_ns'])
        pin = self._save(self.clock_root/f'{index:03d}'/'job.json',dict(schema=SCHEMA,
            intent_sha256=self._clock_intent,start_ns=start,end_ns=end,job_pins=pins))
        self._clock_pending = (index,item,pins,start,end,pin)
        return pins

    def step(self,*,expected_source_identity,expected_head):
        if not self._clock_guard.acquire(blocking=False): raise ValueError('clock controller active')
        try:
            self.last_observation = None
            self._clock_check()
            index = self._clock_index
            if index >= self._clock_hours: raise ValueError('clock hour cap')
            self._clock_start = tick(self._clock_last)
            self._headroom()
            path = self.clock_root/f'{index:03d}';path.mkdir(exist_ok=False)
            self._clock_directories[path] = worker.hour._directory(path,set())
            intent = self._save(path/'intent.json',dict(schema=SCHEMA,binding_sha256=self.binding_pin,
                index=index,start_ns=self._clock_start,expected_head=io.pin(expected_head),
                source_identity=io.pin(expected_source_identity),previous_sha256=self._clock_previous))
            self._clock_intent = intent
            result = super().step(expected_source_identity=expected_source_identity,expected_head=expected_head)
            hour,item,pins,start,end,job_pin = self._clock_pending
            if hour != index or result.completed_hours != index+1: raise ValueError('clock outcome hour differs')
            job = self._lease.root/f'job_{index:03d}_non_authoritative'
            view = base.parent.job_view(job,self._parent._stages)
            self._clock_check()
            finish = tick(end)
            terminal = self._save(path/'terminal.json',dict(schema=SCHEMA,intent_sha256=intent,end_ns=finish,
                job_start_ns=start,job_end_ns=end,job_pins=pins,outcome_head=result.head,
                job_record_sha256=job_pin,outcome_anchor_sha256=self._parent._anchor.inspect().record_sha256,**FLAGS))
            checked = inspect(self.clock_root,index,item.packet,item.specification,item.limits,
                binding_pin=self.binding_pin,intent_pin=intent,terminal_pin=terminal)
            if self._parent.inspect() != result: raise ValueError('parent changed before clock return')
            self._clock_check()
            if base.parent.job_view(job,self._parent._stages) != view: raise ValueError('Job changed before clock return')
            self._check()
            final = tick(finish)
            self.last_observation = Observation((index,result.head,terminal,checked['transaction_wall_ns'],
                checked['native_total_ns'],checked['observed_non_native_ns'],final-finish,True),_token=_TOKEN)
            self._clock_last = final
            self._clock_previous = terminal
            self._clock_index += 1
            return result
        except BaseException:
            self._clock_poisoned = True
            self._parent._poisoned = True
            raise
        finally:
            self._clock_pending = None
            self._clock_guard.release()

    def close(self):
        if worker.job._current_process()+(threading.get_ident(),) != self._clock_owner: raise ValueError('clock close owner differs')
        if not self._clock_guard.acquire(blocking=False): raise ValueError('clock controller active')
        try:
            self._clock_closed = True
            try: super().close()
            finally:
                lease,self._clock_lease = self._clock_lease,None
                if lease is not None: lease.close()
        finally: self._clock_guard.release()
