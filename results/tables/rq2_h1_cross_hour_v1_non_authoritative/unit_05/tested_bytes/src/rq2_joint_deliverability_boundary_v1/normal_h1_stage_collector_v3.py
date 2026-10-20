"""One-attempt short H1 collector with durable intent and ordered raw receipts."""
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path

from . import normal_h1_incremental_archive_v3 as sink

chunks,replay=sink.chunks,sink.replay
native=replay.native
SCHEMA='h1_durable_stage_collector_development_v3'
EMPTY_SHA=sha256(b'').hexdigest()


def implementation_identity():
    return replay.current.source._digest(SCHEMA,sink.base.implementation_identity(),
        sha256(Path(sink.__file__).read_bytes()).hexdigest(),sha256(Path(__file__).read_bytes()).hexdigest())


def declaration(packet,specification,budget,limits,parent_intent_head,source_lineage_identity):
    native._pin(parent_intent_head)
    native._pin(source_lineage_identity)
    key=replay.request_key(packet,specification,limits)
    chain=native.chain_identity(packet.inputs,specification,budget)
    return dict(schema=SCHEMA,request_key=key,chain_identity=chain,
        input_identity=packet.input_identity,relative_hour=packet.relative_hour,
        before_identity=replay.current.source._digest(packet.before),
        planned_solver_calls=len(native.model_api.stage_order(packet.inputs)),
        planned_solver_seconds_hex=(len(native.model_api.stage_order(packet.inputs))*float(specification.time_limit_seconds)).hex(),
        max_native_payload_bytes=native.MAX_PAYLOAD_BYTES,
        packet_audit_identity=packet.audit_identity,parent_intent_head=parent_intent_head,
        source_lineage_identity=source_lineage_identity,
        stage_order=[list(v) for v in native.model_api.stage_order(packet.inputs)],
        specification=asdict(specification),budget=asdict(budget),limits=asdict(limits),
        implementation_identity=implementation_identity())


class _CollectorArchive(sink.DevelopmentH1IncrementalArchive):
    def __init__(self,*args,collector_binding,**kwargs):
        self._collector_binding=collector_binding
        super().__init__(*args,**kwargs)

    def _binding_identity(self):
        return replay.current.source._digest(SCHEMA,super()._binding_identity(),self._collector_binding)


@dataclass(frozen=True)
class H1CollectorInspection:
    attempt_identity: str
    registry_head: str
    child_head: str
    status: str
    stored_reports: int
    solver_calls: int | None
    projection: object | None
    resumable: bool = False
    source_authenticated: bool = False
    native_execution_authenticated: bool = False
    parent_intent_verified: bool = False
    published: bool = False
    formal_result: bool = False
    formal_execution_ready: bool = False


class DevelopmentH1StageCollector:
    """Create once per registry root; reopened owners are inspection-only.

    Pending intent conservatively means unknown, even if no call actually began.
    This local attempt registry does not deduplicate requests across other roots;
    that requires the source-normal parent controller.
    """
    def __init__(self,root,packet,specification,budget,limits,*,parent_intent_head,
                 source_lineage_identity,create=False,expected_head=None,expected_child_head=None):
        self._packet,self._spec,self._budget,self._limits=deepcopy((packet,specification,budget,limits))
        self._parent,self._source=parent_intent_head,source_lineage_identity
        self._declaration=self._declare()
        self._binding=sha256(chunks.base._bytes(self._declaration)).hexdigest()
        self._guard=chunks._Exclusive()
        self._closed=self._poisoned=False
        self._armed=False
        self._registry=self._child=None
        if type(create) is not bool or (create and expected_child_head is not None):
            raise ValueError('explicit create and independent child reopen head required')
        if expected_child_head is not None:native._pin(expected_child_head)
        try:
            self._registry=chunks.DevelopmentH1ChunkJournal(root,
                chunks.ChunkContentBudget(len(self._declaration['stage_order'])+3,chunks.METADATA_BYTES,
                    (len(self._declaration['stage_order'])+3)*chunks.METADATA_BYTES),
                binding_identity=self._binding,create=create,expected_head=expected_head)
            self._attempt=replay.current.source._digest(SCHEMA,self._registry.identity,'attempt')
            candidates=[expected_child_head]
            if not create:
                observed=self._registry.inspect()
                if observed.events:
                    import json
                    last=json.loads(self._registry.event_metadata(observed.events,expected_head=observed.head))
                    if last.get('kind')=='child_checkpoint':
                        candidates=[last['expected_child_head'],last['previous_child_head']]
                    elif last.get('kind')=='attempt_outcome':candidates=[last['child_head']]
                    elif last.get('kind')=='attempt_intent':candidates=[last['child_genesis_head']]
                if expected_child_head is not None:
                    if expected_child_head not in candidates:raise ValueError('child head not registered')
                    candidates=[expected_child_head]
            for candidate in candidates:
                try:
                    self._child=_CollectorArchive(Path(root)/'stages_non_authoritative',
                        self._packet,self._spec,self._limits,parent_intent_head=self._parent,
                        source_lineage_identity=self._source,collector_binding=self._attempt,
                        create=create,expected_head=candidate)
                    break
                except ValueError:
                    if candidate==candidates[-1]:raise
            self._restore()
            self._armed=create
        except BaseException:
            self.close()
            raise

    def _declare(self):
        return declaration(self._packet,self._spec,self._budget,self._limits,self._parent,self._source)

    def _check(self):
        if self._closed or self._poisoned:raise ValueError('closed or unresolved collector owner')
        if self._declare()!=self._declaration:raise ValueError('collector declaration drift')

    def _intent(self):
        return dict(schema=SCHEMA,kind='attempt_intent',attempt_identity=self._attempt,
            declaration=self._declaration,child_identity=self._child._binding,
            child_genesis_head=self._child._journal._genesis,
            child_root=str(self._child._journal._lease.root),
            child_content_budget=asdict(self._child._journal._budget))

    def _outcome(self,state):
        if state.status not in ('accepted','rejected'):raise ValueError('durable child terminal required')
        return dict(schema=SCHEMA,kind='attempt_outcome',attempt_identity=self._attempt,
            status=state.status,child_head=state.head,stored_reports=state.stored_reports,
            solver_calls=state.stored_reports if state.status=='accepted' else None,
            projection_identity=None if state.projection is None else state.projection.projection_identity)

    def _registry_state(self):
        self._check()
        observed=self._registry.inspect()
        if observed.payload_bytes!=0 or observed.chunks!=0:raise ValueError('metadata-only attempt registry required')
        if observed.events:
            raw=self._registry.event_metadata(1,expected_head=observed.head)
            if raw!=chunks.base._bytes(self._intent()):raise ValueError('durable attempt intent mismatch')
        return observed

    def _restore(self):
        observed=self._registry_state()
        state=self._child.inspect()
        status='empty' if observed.events==0 else 'pending_unknown'
        projection=calls=None
        if not observed.events and (state.stored_reports or state.status!='collecting'):
            raise ValueError('child reports without durable attempt intent')
        import json
        previous=self._child._journal._genesis
        child_events=state.stored_reports+(state.status=='accepted')
        checkpoints=0
        for seq in range(2,observed.events+1):
            raw=self._registry.event_metadata(seq,expected_head=observed.head)
            item=json.loads(raw)
            if item.get('kind')=='attempt_outcome':
                if (seq!=observed.events or checkpoints!=child_events
                        or raw!=chunks.base._bytes(self._outcome(state))):
                    raise ValueError('attempt outcome mismatch')
                status=state.status
                projection=state.projection
                calls=state.stored_reports if status=='accepted' else None
                continue
            checkpoints+=1
            keys={'schema','kind','attempt_identity','child_event','previous_child_head',
                  'expected_child_head','raw_sha256','metadata_sha256'}
            if (set(item)!=keys or item['schema']!=SCHEMA or item['kind']!='child_checkpoint'
                    or item['attempt_identity']!=self._attempt or type(item['child_event']) is not int
                    or item['child_event']!=checkpoints or item['previous_child_head']!=previous):
                raise ValueError('ordered child checkpoint required')
            for key in ('expected_child_head','raw_sha256','metadata_sha256'):native._pin(item[key])
            if checkpoints<=child_events:
                conn=self._child._journal._connect()
                try:
                    row=conn.execute('SELECT metadata,payload_sha,head FROM events WHERE seq=?',(checkpoints,)).fetchone()
                finally:conn.close()
                if (row is None or sha256(row[0]).hexdigest()!=item['metadata_sha256']
                        or row[1]!=item['raw_sha256'] or row[2]!=item['expected_child_head']):
                    raise ValueError('child checkpoint evidence mismatch')
            previous=item['expected_child_head']
        if checkpoints not in (child_events,child_events+1):raise ValueError('unregistered child prefix')
        self._child._check()
        return H1CollectorInspection(self._attempt,observed.head,state.head,status,state.stored_reports,calls,projection)

    def _checkpoint(self,metadata,raw):
        before=self._child.head
        seq=self._child._counts_cache[0]+1
        meta=chunks.base._bytes(metadata)
        chain=sha256(chunks.base._bytes([chunks.SCHEMA,seq,before,'chunks'])).hexdigest()
        count=0
        for index,start in enumerate(range(0,len(raw),chunks.CHUNK_BYTES)):
            chain=chunks._chunk_head(seq,index,chain,raw[start:start+chunks.CHUNK_BYTES])
            count+=1
        pin=sha256(raw).hexdigest()
        head=chunks._head(seq,before,meta,len(raw),count,pin,chain)
        self._append(dict(schema=SCHEMA,kind='child_checkpoint',attempt_identity=self._attempt,
            child_event=seq,previous_child_head=before,expected_child_head=head,
            raw_sha256=pin,metadata_sha256=sha256(meta).hexdigest()))
        self._registry_state()
        return head

    def inspect(self):
        with self._guard:
            try:return self._restore()
            except BaseException:
                self._poisoned=True
                raise

    def _append(self,metadata):
        return self._registry.append(metadata,(),expected_head=self._registry.head,
            declared_payload_bytes=0,expected_payload_sha256=EMPTY_SHA)

    def run(self,*,expected_head):
        raise ValueError('durable parent registry anchor integration required before execution')

    def _run_checkpoint_development(self,*,expected_head):
        """Private control-flow test seam; public execution awaits parent anchor."""
        with self._guard:
            try:
                self._check()
                if not self._armed:raise ValueError('attempt cannot be retried or resumed')
                self._armed=False
                native._pin(expected_head)
                prior=self._restore()
                if prior.registry_head!=expected_head or prior.status!='empty':
                    raise ValueError('fresh independent attempt predecessor required')
                self._append(self._intent())
                if self._registry_state().events!=1:raise ValueError('durable intent required before native call')
                receipt=self._child.inspect()
                for index in range(len(self._declaration['stage_order'])):
                    self._check()
                    if self._registry_state().events!=index+1:raise ValueError('active durable attempt required')
                    if (self._child.head!=receipt.head or receipt.status!='collecting'
                            or len(receipt.canonical_locks)!=index):
                        raise ValueError('durable ordered receipt required before native call')
                    request=native.model_api.H1StageRequest(self._packet.inputs,receipt.canonical_locks)
                    pin=native.model_api.h1_stage_identity(request)
                    def builder(request=request,pin=pin):
                        return native.model_api.build_h1_stage_model(request,expected_identity=pin)
                    structure=native.capture.audit._structure(builder())
                    raw=native.capture.solve_once(builder,self._spec,expected_structure=structure,
                        max_variables=self._budget.max_variables,max_constraints=self._budget.max_constraints,
                        max_payload_bytes=native.MAX_PAYLOAD_BYTES,
                        expected_implementation=native.capture.implementation_identity())
                    self._check()
                    if type(raw) is not bytes or not 0<len(raw)<=native.MAX_PAYLOAD_BYTES:
                        raise ValueError('bounded immutable native report required')
                    stage=error=None
                    try:stage=replay._audit_stage(self._packet,self._spec,self._limits,index,receipt.canonical_locks,raw)
                    except replay.H1ReportAuditRejected as rejected:error=rejected
                    metadata=self._child._stage_metadata(index,receipt.canonical_locks,raw,stage,error)
                    expected=self._checkpoint(metadata,raw)
                    receipt=self._child.record_report(raw,expected_head=receipt.head)
                    if receipt.head!=expected:raise ValueError('committed receipt differs from checkpoint')
                    if receipt.status=='rejected':break
                if receipt.status=='awaiting_terminal':
                    projection=self._child._replay_complete_prefix()
                    self._child._check()
                    expected=self._checkpoint(self._child._terminal_metadata(projection),b'')
                    receipt=self._child.finish(expected_head=receipt.head)
                    if receipt.head!=expected:raise ValueError('terminal differs from checkpoint')
                fresh=self._child.inspect()
                if fresh!=receipt:raise ValueError('child terminal changed before attempt outcome')
                self._append(self._outcome(fresh))
                return self._restore()
            except BaseException:
                self._poisoned=True
                raise

    def close(self):
        with self._guard:
            if not self._closed:
                try:
                    if self._child is not None:self._child.close()
                finally:
                    if self._registry is not None:self._registry.close()
                    self._closed=True

    __copy__=chunks.DevelopmentH1ChunkJournal.__copy__
    __deepcopy__=chunks.DevelopmentH1ChunkJournal.__deepcopy__
    __reduce_ex__=chunks.DevelopmentH1ChunkJournal.__reduce_ex__
