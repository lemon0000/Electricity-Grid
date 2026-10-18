"""DRAFT phase controller records and numerical Job path for a192h root.

Native-capable private _step_development (public step is disabled): concrete resource admission and new user authority remain
required for actual native use. This development API does not grant either.
"""
from dataclasses import asdict, dataclass
from pathlib import Path
import threading

from experiments import h1_job_clock_bridge_development_v1 as bridge
from experiments import h1_phase_obligation_binding_development_v1 as binding

base, io = bridge.base, binding.io
SCHEMA = 'h1_phase_obligation_controller_development_v1'
CAP = binding.CAP
FLAGS = dict(binding.FLAGS,worker_obligation_authenticated=False)
_TOKEN = object()


@dataclass(frozen=True,init=False)
class ObligationObservation:
    relative_hour: int
    header_sha256: str
    terminal_sha256: str
    outcome_head: str
    controller_live_join_checked: bool

    def __init__(self,hour,header,terminal,head,*,_token=None):
        if _token is not _TOKEN: raise TypeError('owned obligation return required')
        if type(hour) is not int or not 0 <= hour < 192: raise ValueError('finite episode hour required')
        for value in (header,terminal,head): io.pin(value)
        for name,value in zip(self.__annotations__,(hour,header,terminal,head,True),strict=True):
            object.__setattr__(self,name,value)

    __copy__ = base.old.bounded.chunks.DevelopmentH1ChunkJournal.__copy__
    __deepcopy__ = base.old.bounded.chunks.DevelopmentH1ChunkJournal.__deepcopy__
    __reduce_ex__ = base.old.bounded.chunks.DevelopmentH1ChunkJournal.__reduce_ex__


def implementation_identity():
    return io.digest(io.encode([SCHEMA, bridge.implementation_identity(),
        io.digest(Path(binding.__file__).read_bytes()), io.digest(Path(__file__).read_bytes())]))


def additional_content_bound(hours):
    if type(hours) is not int or not 1 <= hours <= 192:
        raise ValueError('finite episode horizon in [1,192] required')
    return dict(files=3*hours+2, logical_bytes=(3*hours+1)*CAP+1,
        filesystem_allocation_bound_proven=False, resource_admission=False)


class Controller(bridge.Controller):
    def __init__(self, *args, resolver, family, ordinal, **kwargs):
        if kwargs.get('hours') != 192 or type(kwargs['hours']) is not int:
            raise ValueError('new 192-hour episode declaration required')
        additional_content_bound(kwargs['hours'])
        if type(resolver) is not binding.manifest.Resolver or resolver.identity != binding.MANIFEST_PIN:
            raise ValueError('exact pinned obligation Resolver required')
        self._obligation_guard = threading.Lock()
        self._obligation_lease = None
        self._obligation_resolver = resolver
        self._obligation_family, self._obligation_ordinal = family, ordinal
        self._obligation_identity = implementation_identity()
        self._obligation_views = {}
        self._active_request = None
        self.last_obligation_observation = None
        self._obligation_configuration = io.encode(dict(manifest=resolver.identity,family=family,ordinal=ordinal,
            budget=asdict(kwargs['budget'])))
        super().__init__(*args, **kwargs)
        try:
            binding.precheck(resolver,self._parent._declaration,family=family,ordinal=ordinal,relative_hour=0)
            self.obligation_root = self._lease.root/'obligation_non_authoritative'
            self._obligation_lease = base.old.bounded.chunks.base.local._Lease(self.obligation_root,True)
            self.obligation_binding_pin = self._save_obligation(self.obligation_root/'binding.json',dict(
                schema=SCHEMA,implementation=self._obligation_identity,parent_declaration=self._parent._declaration,
                parent_identity=self._parent.identity,manifest_sha256=resolver.identity,family=family,ordinal=ordinal,
                hours=192,budget=asdict(self._budget),clock_binding_sha256=self.binding_pin,**FLAGS))
            self._obligation_previous = self.obligation_binding_pin
        except BaseException:
            self.close(); raise

    def _check(self):
        super()._check()
        if (implementation_identity() != self._obligation_identity or
                io.encode(dict(manifest=self._obligation_resolver.identity,
                    family=self._obligation_family,ordinal=self._obligation_ordinal,budget=asdict(self._budget))) != self._obligation_configuration):
            raise ValueError('obligation controller configuration changed')
        base.entry.unchanged(self._obligation_views)
        if self._obligation_lease is not None:
            self._obligation_lease.check()
            bridge.worker.hour._directory(self.obligation_root,{'execution.lock'}|{p.name for p in self._obligation_views})
        if self._active_request is not None:
            path, pin = self._active_request
            # The inherited controller invokes this with the child suspended,
            # before release_intent and release(). A missing request also fails.
            base.entry.read(path,pin)

    def _save_obligation(self,path,value):
        raw = io.encode(value)
        if len(raw) > CAP: raise ValueError('obligation controller record cap')
        io.write_new(path,raw)
        pin = io.digest(raw)
        _,view = base.entry.read(path,pin,CAP)
        self._obligation_views[path] = (CAP,view)
        return pin

    def _headroom(self):
        self._check()
        binding.prevalidate_enrollment(self._obligation_resolver,self._parent._declaration,
            family=self._obligation_family,ordinal=self._obligation_ordinal,relative_hour=self._clock_index)
        super()._headroom()
        # Three controller records per remaining finite-episode hour.
        r = base.old.process.resources
        demand = r.HostResourceBudget(self._budget.max_job_commit_bytes+256*base.old.MIB,32*base.old.MIB,(
            r.DirectoryDemand('job_content',str(self._lease.root),base.job_content_bound(self._parent._stages)['logical_bytes'],32*base.old.MIB),
            r.DirectoryDemand('parent_updates',str(self._parent._root),base.parent_update_bound(),32*base.old.MIB),
            r.DirectoryDemand('clock_remaining',str(self.clock_root),3*(self._clock_hours-self._clock_index)*bridge.CAP,32*base.old.MIB),
            r.DirectoryDemand('obligation_remaining',str(self.obligation_root),3*(self._clock_hours-self._clock_index)*CAP,32*base.old.MIB),
            r.DirectoryDemand('scratch',str(self._lease.root),8*base.old.MIB,32*base.old.MIB)))
        identity = r.resource_identity(demand)
        observed = r.observe_headroom(demand,expected_request_identity=identity)
        if (type(observed) is not r.HostHeadroomObservation or observed.request_identity != identity
                or observed.errors or not observed.observed_headroom_sufficient
                or any(getattr(observed,k) is not False for k in ('resource_reservation_held',
                    'hard_resource_limits_enforced','whole_task_resources_verified','formal_run_authorized','formal_result'))):
            raise ValueError('combined obligation headroom unavailable')

    def _job(self,index,item,pending,anchor):
        p = self._parent
        if (not self._obligation_guard.locked() or not self._clock_guard.locked() or not self._guard._lock.locked()
                or not p._guard._lock.locked() or self._active_request is not None):
            raise ValueError('owned obligation release scope required')
        self._check(); self._clock_check()
        record = binding.bind(self._obligation_resolver,p._declaration,
            family=self._obligation_family,ordinal=self._obligation_ordinal,relative_hour=index,
            expected_parent_identity=p.identity,expected_anchor_record=anchor,
            pending_arguments=pending,expected_pending_receipt_sha256=item.receipt_sha256,job_budget=self._budget)
        if (record['normal_request_key'] != base.old.replay.request_key(item.packet,item.specification,item.limits)
                or record['source_parent_lineage']['pending_receipt'] != base.old.json.loads(item.receipt)):
            raise ValueError('obligation differs from typed pending input')
        root = self._lease.root/f'job_{index:03d}_non_authoritative'
        # Exact same request as the inherited writer; fail closed on divergence.
        request = dict(schema=base.entry.SCHEMA,root=str(root),implementation=self._implementation,
            parent_declaration=p._declaration,parent_identity=p.identity,anchor_record=anchor,pending_arguments=pending,
            input_receipt=base.old.json.loads(item.receipt),input_receipt_sha256=item.receipt_sha256,
            budget=asdict(self._budget),route='owned_timed_hour_development',**base.entry.FLAGS)
        request_pin = io.digest(io.encode(request))
        pin = self._save_obligation(self.obligation_root/f'{index:03d}.binding.json',dict(schema=SCHEMA,
            implementation=self._obligation_identity,obligation=record,expected_worker_request_sha256=request_pin,
            **FLAGS))
        self._check()
        if p._restore()[0].head != pending['expected_head'] or p._anchor.inspect().record_sha256 != anchor:
            raise ValueError('live obligation parent changed before Job')
        self._active_request = (root/'request.json',request_pin)
        try:
            pins = super()._job(index,item,pending,anchor)
            self._check()
            if pins['request.json'] != request_pin: raise ValueError('released request differs from obligation')
            self._save_obligation(self.obligation_root/f'{index:03d}.job.json',dict(schema=SCHEMA,
                obligation_binding_sha256=pin,job_pins=pins,**FLAGS))
            self._check()
            return pins
        finally:
            self._active_request = None

    def step(self,**kwargs):
        raise ValueError('phase controller public execution requires attached owner; not implemented')

    def _step_development(self,*,expected_source_identity,expected_head):
        # Private numerical fixture path. No owner need or bootstrap authority.
        if not self._obligation_guard.acquire(blocking=False): raise ValueError('obligation controller active')
        try:
            self.last_obligation_observation = None
            result = super().step(expected_source_identity=expected_source_identity,expected_head=expected_head)
            hour = result.completed_hours-1
            link = self.obligation_root/f'{hour:03d}.job.json'
            pin = self._save_obligation(self.obligation_root/f'{hour:03d}.terminal.json',dict(schema=SCHEMA,
                previous_sha256=self._obligation_previous,job_link_sha256=io.digest(self._obligation_views[link][1][0]),
                clock_terminal_sha256=self.last_observation.terminal_sha256,parent_head=result.head,
                parent_anchor_sha256=self._parent._anchor.inspect().record_sha256,relative_hour=hour,
                controller_live_join_checked=True,**FLAGS))
            self._check()
            self._obligation_previous = pin
            self.last_obligation_observation = ObligationObservation(hour,self.obligation_binding_pin,pin,result.head,_token=_TOKEN)
            return result
        except BaseException:
            self.last_observation = None
            self.last_obligation_observation = None
            self._clock_poisoned = True
            self._parent._poisoned = True
            raise
        finally: self._obligation_guard.release()

    def inspect(self):
        if not self._obligation_guard.acquire(blocking=False): raise ValueError('obligation controller active')
        try: return super().inspect()
        finally: self._obligation_guard.release()

    def close(self):
        if bridge.worker.job._current_process()+(threading.get_ident(),) != self._clock_owner:
            raise ValueError('obligation close owner differs')
        if not self._obligation_guard.acquire(blocking=False): raise ValueError('obligation controller active')
        try:
            try: super().close()
            finally:
                owner,self._obligation_lease = self._obligation_lease,None
                if owner is not None: owner.close()
        finally: self._obligation_guard.release()


def _historical_binding(packet,request,node,enrollment):
    """Independent reconstruction from a fully replayed historical packet."""
    point = node['record']['payload']['coordinate']
    hour = packet.relative_hour
    value = dict(schema=binding.SCHEMA,status='DRAFT_NONAUTHORITATIVE',
        role='normal_environment_prerequisite_for_B6_planning' if point['arm']=='joint-B6'
            else 'normal_environment_prerequisite_for_training_UB',
        manifest_sha256=binding.MANIFEST_PIN,obligation_node=node,phase=binding.phase(hour),relative_hour=hour,
        raw_source_hours=dict(power=point['power']['source_start']+hour,workload=point['workload']['source_start']+hour),
        display_source_hours=dict(power=point['power']['source_start']+hour+1,workload=point['workload']['source_start']+hour+1),
        model_timestamp=packet.inputs.request.timestamps[0].isoformat(),normal_input_identity=packet.input_identity,
        normal_request_key=request['pending_arguments']['expected_request_key'],
        specification=request['parent_declaration']['specification'],limits=request['parent_declaration']['limits'],
        source_parent_lineage=dict(parent_declaration=request['parent_declaration'],pending_receipt=request['input_receipt'],
            pending_receipt_sha256=request['input_receipt_sha256']),enrollment_prevalidation=enrollment,
        proposed_job_budget=request['budget'],proposed_job_budget_sha256=io.digest(io.encode(request['budget'])),
        implementation_sha256=io.digest(Path(binding.__file__).read_bytes()),baseline_checks_sha256=binding.BASELINE_PIN,
        runtime_task_id=None,launch_request=None,host_resource_admission=None,solver_calls=0,**binding.FLAGS)
    value['obligation_binding_id'] = io.digest(io.encode(value))
    return value

