"""Source-bound parent of anchored hour collectors, within existing short budgets."""
from copy import deepcopy
from dataclasses import asdict,dataclass
from datetime import timedelta
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

from . import normal_h1_source_episode as old
from . import normal_h1_anchored_collector as child

chunks=child.base.chunks
source=old.source
SCHEMA='h1_anchored_source_parent_development_v1'


def implementation_identity():
    return source._digest(SCHEMA,child.implementation_identity(),old.binding.implementation_identity(),
        sha256(Path(old.__file__).read_bytes()).hexdigest(),sha256(Path(__file__).read_bytes()).hexdigest())


@dataclass(frozen=True)
class H1AnchoredSourceInspection:
    parent_identity: str
    head: str
    completed_hours: int
    status: str
    reserved_solver_calls: int
    reserved_solver_seconds: float
    last_projection_identity: str | None
    source_authenticated: bool=False
    native_execution_authenticated: bool=False
    published: bool=False
    formal_result: bool=False
    formal_execution_ready: bool=False


class DevelopmentH1AnchoredSourceEpisode:
    """One parent namespace owns each hourly child path and reserves it before calls.

    Reopening audits only. Independent parent namespaces are not globally deduplicated.
    """
    _load_source=old.DevelopmentH1SourceEpisode._load_source
    _source_chains=staticmethod(old.DevelopmentH1SourceEpisode._source_chains)
    _reserve=old.DevelopmentH1SourceEpisode._reserve
    _packet=old.DevelopmentH1SourceEpisode._packet

    def __init__(self,root,network,specification,hour_budget,episode_budget,limits,*,dc_bus,
                 origin,upstream_root,config_path=old.binding.windows.audit.DEFAULT_CONFIG,
                 create=False,expected_anchor_record=None):
        if type(create) is not bool:raise ValueError('exact create flag required')
        if type(origin) is not old.binding.H1SourceDeclaration:raise ValueError('exact source origin required')
        origin.__post_init__()
        if type(episode_budget) is not old.H1EpisodeBudget:raise ValueError('exact short episode budget required')
        episode_budget.__post_init__()
        if type(hour_budget) is not old.replay.native.GridDevelopmentBudget or hour_budget.purpose!=old.replay.native.PURPOSE:
            raise ValueError('exact short hourly budget required')
        hour_budget.__post_init__()
        source._network(network)
        old.replay.native.capture.provenance.adapter.validate_spec(specification)
        if type(limits) is not child.base.replay.H1HourReplayLimits:raise ValueError('exact replay limits required')
        limits.__post_init__()
        if type(dc_bus) is not int or dc_bus not in {b.uid for b in network.data.buses}:raise ValueError('declared DC bus required')
        self._network,self._spec,self._hour_budget,self._episode_budget,self._limits,self._origin=deepcopy(
            (network,specification,hour_budget,episode_budget,limits,origin))
        self._dc_bus=dc_bus
        self._upstream_root=Path(upstream_root).resolve(strict=True)
        self._config_path=Path(config_path).resolve(strict=True)
        self._root=Path(root).resolve()
        self._stages=1+len(network.data.generators)+sum(g.dispatch_mode=='committable' for g in network.data.generators)
        self._seconds=self._stages*Fraction.from_float(float(specification.time_limit_seconds))
        self._reserve(episode_budget.planned_hours)
        if (hour_budget.max_horizon!=1 or self._stages>hour_budget.max_solver_calls
                or self._stages>limits.max_stages or specification.threads>hour_budget.max_threads
                or specification.time_limit_seconds>hour_budget.max_seconds_per_solve
                or self._seconds>Fraction.from_float(float(hour_budget.max_total_solver_seconds))
                or 2*episode_budget.planned_hours+1>24):
            raise ValueError('complete source parent exceeds existing short budgets')
        self._guard=chunks._Exclusive()
        self._closed=self._poisoned=False
        self._writable=create
        self._journal=self._anchor=None
        self._declaration=self._declare()
        self.identity=sha256(chunks.base._bytes(self._declaration)).hexdigest()
        n=2*episode_budget.planned_hours
        budget=chunks.ChunkContentBudget(n,2*chunks.METADATA_BYTES,n*2*chunks.METADATA_BYTES)
        try:
            if create:
                self._journal=chunks.DevelopmentH1ChunkJournal(root,budget,binding_identity=self.identity,create=True)
            self._anchor=child.anchor.DevelopmentH1AttemptAnchor(self._root/'parent_anchor_non_authoritative',
                self.identity,max_records=n+1,create=create,expected_record_sha256=expected_anchor_record)
            if create:
                self._anchor.advance(self._journal.head,sha256(b'genesis').hexdigest(),expected_previous=None)
            else:
                receipt=self._anchor.inspect()
                if receipt is None:raise ValueError('parent anchor lacks genesis')
                self._journal=chunks.DevelopmentH1ChunkJournal(root,budget,binding_identity=self.identity,expected_head=receipt.registry_head)
            self._restore()
        except BaseException:
            self.close()
            raise

    def _declare(self):
        return dict(schema=SCHEMA,root=str(self._root),network_identity=self._network.identity,
            specification=asdict(self._spec),hour_budget=asdict(self._hour_budget),episode_budget=asdict(self._episode_budget),
            limits=asdict(self._limits),origin=asdict(self._origin),dc_bus=self._dc_bus,
            upstream_root=str(self._upstream_root),config_path=str(self._config_path),implementation=implementation_identity())

    def _check(self):
        if self._closed or self._poisoned:raise ValueError('closed or unresolved source parent')
        if self._declare()!=self._declaration:raise ValueError('source parent declaration drift')
        receipt=self._anchor.inspect()
        if receipt is None or receipt.registry_head!=self._journal.head:raise ValueError('source parent head not anchored')
        self._anchor.confirm(receipt)

    def _paths(self,hour):
        return self._root/f'hour_{hour:03d}_non_authoritative',self._root/f'hour_{hour:03d}_anchor_non_authoritative'

    def _intent(self,hour,receipt,packet):
        paths=self._paths(hour)
        return dict(schema=SCHEMA,kind='intent',hour=hour,source_identity=receipt.identity,
            source_audit_sha256=sha256(receipt.audit_payload).hexdigest(),
            observation=old._observation(receipt.row,receipt.raw_workload,receipt.source_time_basis),
            before_identity=source._digest(packet.before),packet_audit_identity=packet.audit_identity,
            request_key=child.base.replay.request_key(packet,self._spec,self._limits),
            chain_identity=old.replay.native.chain_identity(packet.inputs,self._spec,self._hour_budget),
            collector_root=str(paths[0]),collector_anchor_root=str(paths[1]),
            collector_implementation=child.implementation_identity(),reserved_calls=self._stages,
            reserved_seconds_exact=[str(self._seconds.numerator),str(self._seconds.denominator)])

    def _collector(self,hour,packet,intent_head,lineage,*,create=False,expected_anchor_record=None):
        root,anchor_root=self._paths(hour)
        return child.DevelopmentH1AnchoredCollector(root,packet,self._spec,self._hour_budget,self._limits,
            anchor_root=anchor_root,parent_intent_head=intent_head,source_lineage_identity=lineage,
            create=create,expected_anchor_record=expected_anchor_record)

    def _outcome(self,hour,intent_head,result,anchor_pin):
        if result.status not in ('accepted','rejected'):raise ValueError('complete child outcome required')
        return dict(schema=SCHEMA,kind=result.status,hour=hour,intent_head=intent_head,
            attempt_identity=result.attempt_identity,registry_head=result.registry_head,child_head=result.child_head,
            anchor_record_sha256=anchor_pin,stored_reports=result.stored_reports,
            projection_identity=None if result.projection is None else result.projection.projection_identity)

    def _append(self,metadata,payload=b''):
        self._check()
        previous=self._journal.head
        self._journal.append(metadata,() if not payload else (payload,),expected_head=previous,
            declared_payload_bytes=len(payload),expected_payload_sha256=sha256(payload).hexdigest())
        receipt=self._anchor.advance(self._journal.head,sha256(chunks.base._bytes(metadata)).hexdigest(),expected_previous=previous)
        self._anchor.confirm(receipt)
        self._check()

    def _continuity(self,receipt,last_observation,chains):
        current_chains=self._source_chains(receipt)
        observation=old._observation(receipt.row,receipt.raw_workload,receipt.source_time_basis)
        if chains is not None and current_chains!=chains:raise ValueError('source chain changed')
        if last_observation is not None and (observation['source_time_basis']!=last_observation['source_time_basis']
                or old._row(observation).timestamp-old._row(last_observation).timestamp!=timedelta(hours=1)):
            raise ValueError('source clock continuity failed')
        return observation,current_chains

    def _restore(self):
        self._check()
        observed=self._journal.inspect()
        before=last_observation=chains=pending=last_projection=None
        completed=attempts=0
        halted=False
        for seq in range(1,observed.events+1):
            raw=self._journal.event_metadata(seq,expected_head=observed.head)
            item=json.loads(raw)
            payload=b''.join(self._journal.iter_event(seq,expected_head=observed.head))
            if halted or item.get('schema')!=SCHEMA or type(item.get('hour')) is not int or item['hour']!=completed:
                raise ValueError('source parent event order mismatch')
            if item.get('kind')=='intent':
                if pending is not None:raise ValueError('source parent intent already pending')
                attempts+=1
                self._reserve(attempts)
                receipt=self._load_source(completed,item['source_identity'])
                observation,chains=self._continuity(receipt,last_observation,chains)
                packet=self._packet(observation,completed,before)
                if raw!=chunks.base._bytes(self._intent(completed,receipt,packet)) or payload!=receipt.audit_payload:
                    raise ValueError('source intent differs from freshly pinned observation')
                conn=self._journal._connect()
                try:intent_head=conn.execute('SELECT head FROM events WHERE seq=?',(seq,)).fetchone()[0]
                finally:conn.close()
                pending=(packet,receipt,observation,intent_head)
            elif item.get('kind') in ('accepted','rejected'):
                if pending is None or payload:raise ValueError('source parent outcome lacks intent')
                packet,receipt,observation,intent_head=pending
                owner=self._collector(completed,packet,intent_head,receipt.identity,expected_anchor_record=item['anchor_record_sha256'])
                try:result=owner.inspect()
                finally:owner.close()
                if raw!=chunks.base._bytes(self._outcome(completed,intent_head,result,item['anchor_record_sha256'])):
                    raise ValueError('source parent outcome differs from durable child')
                if result.status=='accepted':
                    projection=result.projection
                    if (type(projection) is not child.base.replay.H1HourReplayedProjection
                            or projection.request_key!=child.base.replay.request_key(packet,self._spec,self._limits)
                            or projection.before_identity!=source._digest(packet.before)
                            or len(projection.canonical_locks)!=self._stages):
                        raise ValueError('owned child projection binding mismatch')
                    values=json.loads(projection.projection_payload)
                    before=source._owned(source.H1NormalBoundary,network_identity=values['network_identity'],
                        completed_hours=values['completed_hours'],units=tuple((uid,on,float.fromhex(power),age)
                            for uid,on,power,age in values['units']),evidence_role='numerical_lex_candidate')
                    source._boundary(self._network,before,completed+1)
                    completed+=1
                    last_observation=observation
                    last_projection=projection.projection_identity
                else:halted=True
                pending=None
            else:raise ValueError('unknown source parent event')
        self._check()
        state=H1AnchoredSourceInspection(self.identity,observed.head,completed,
            'pending_unknown' if pending else 'halted' if halted else 'complete' if completed==self._episode_budget.planned_hours else 'ready',
            attempts*self._stages,float(attempts*self._seconds),last_projection)
        return state,before,last_observation,chains

    def inspect(self):
        with self._guard:
            try:return self._restore()[0]
            except BaseException:
                self._poisoned=True
                raise

    def step(self,*,expected_source_identity,expected_head):
        with self._guard:
            try:
                if not self._writable:raise ValueError('reopened source parent cannot execute')
                state,before,last_observation,chains=self._restore()
                if state.head!=expected_head or state.status!='ready':raise ValueError('ready source parent predecessor required')
                receipt=self._load_source(state.completed_hours,expected_source_identity)
                observation,_=self._continuity(receipt,last_observation,chains)
                packet=self._packet(observation,state.completed_hours,before)
                intent=self._intent(state.completed_hours,receipt,packet)
                self._append(intent,receipt.audit_payload)
                intent_head=self._journal.head
                if self._restore()[0].status!='pending_unknown':raise ValueError('durable source intent required')
                owner=self._collector(state.completed_hours,packet,intent_head,receipt.identity,create=True)
                try:
                    result=owner.run(expected_head=owner.inspect().registry_head)
                    fresh=owner.inspect()
                    if result!=fresh:raise ValueError('collector outcome changed')
                    anchor_pin=owner._anchor.inspect().record_sha256
                finally:owner.close()
                reopened=self._collector(state.completed_hours,packet,intent_head,receipt.identity,
                    expected_anchor_record=anchor_pin)
                try:
                    fresh=reopened.inspect()
                    if fresh!=result or fresh.status not in ('accepted','rejected'):
                        raise ValueError('fresh reopened child outcome changed')
                finally:reopened.close()
                # Reload source and prior committed prefix before publishing the child reference.
                self._restore()
                self._append(self._outcome(state.completed_hours,intent_head,fresh,anchor_pin))
                return self._restore()[0]
            except BaseException:
                self._poisoned=True
                raise

    def close(self):
        with self._guard:
            if not self._closed:
                try:
                    if self._journal is not None:self._journal.close()
                finally:
                    if self._anchor is not None:self._anchor.close()
                    self._closed=True

    __copy__=chunks.DevelopmentH1ChunkJournal.__copy__
    __deepcopy__=chunks.DevelopmentH1ChunkJournal.__deepcopy__
    __reduce_ex__=chunks.DevelopmentH1ChunkJournal.__reduce_ex__
