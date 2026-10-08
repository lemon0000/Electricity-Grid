"""Hour-local stage archive with independent replay and no native invocation."""
from copy import deepcopy
from dataclasses import asdict,dataclass
from hashlib import sha256
from pathlib import Path

from . import normal_h1_chunk_journal as chunks
from . import normal_h1_hour_replay_v2 as replay

SCHEMA='h1_hour_stage_archive_development_v2'
MAX_RAW=replay.native.MAX_PAYLOAD_BYTES


def implementation_identity():
    return replay.current.source._digest(SCHEMA,replay.implementation_identity(),
        sha256(Path(chunks.__file__).read_bytes()).hexdigest(),sha256(Path(__file__).read_bytes()).hexdigest())


def _error(error):
    raw=(type(error).__name__+':'+str(error)).encode('utf-8','backslashreplace')
    return dict(sha256=sha256(raw).hexdigest(),bytes=len(raw),prefix_hex=raw[:1024].hex())


@dataclass(frozen=True)
class H1HourArchiveInspection:
    archive_identity: str
    head: str
    status: str
    stored_reports: int
    canonical_locks: tuple
    projection: replay.H1HourReplayedProjection | None
    solver_calls_by_archive: int = 0
    native_execution_authenticated: bool = False
    source_authenticated: bool = False
    parent_intent_verified: bool = False
    executable_boundary_restored: bool = False
    published: bool = False
    formal_result: bool = False
    formal_execution_ready: bool = False


class DevelopmentH1HourArchive:
    """Archive supplied raw reports in order; not a native stage runner.

    A successful append proves persistence, not when/how a solver was called.
    Writing currently rescans/replays prefixes; full-scale write resources are unknown.
    """
    def __init__(self,root,packet,specification,limits,*,parent_intent_head,source_lineage_identity,
                 create=False,expected_head=None):
        replay.native._pin(parent_intent_head)
        replay.native._pin(source_lineage_identity)
        self._packet,self._spec,self._limits=deepcopy(packet),deepcopy(specification),deepcopy(limits)
        self._parent,self._source=parent_intent_head,source_lineage_identity
        self._key=replay.request_key(self._packet,self._spec,self._limits)
        self._order=replay.native.model_api.stage_order(self._packet.inputs)
        self._binding=self._binding_identity()
        self._guard=chunks._Exclusive()
        self._poisoned=self._closed=False
        n=len(self._order)
        self._journal=chunks.DevelopmentH1ChunkJournal(root,
            chunks.ChunkContentBudget(n+1,MAX_RAW+chunks.METADATA_BYTES,n*MAX_RAW+(n+1)*chunks.METADATA_BYTES),
            binding_identity=self._binding,create=create,expected_head=expected_head)
        try:self._state=self._restore()
        except BaseException:
            self._journal.close()
            raise

    def _binding_identity(self):
        return replay.current.source._digest(SCHEMA,self._key,self._packet.audit_identity,
            self._parent,self._source,self._order,MAX_RAW,implementation_identity())

    def _check(self):
        if self._closed or self._poisoned:raise ValueError('closed or unresolved hour archive owner')
        if (replay.request_key(self._packet,self._spec,self._limits)!=self._key
                or self._binding_identity()!=self._binding):
            raise ValueError('hour archive declaration or implementation drift')

    @property
    def head(self):
        with self._guard:
            self._check()
            return self._journal.head

    def close(self):
        with self._guard:
            if not self._closed:
                self._journal.close()
                self._closed=True

    __copy__=chunks.DevelopmentH1ChunkJournal.__copy__
    __deepcopy__=chunks.DevelopmentH1ChunkJournal.__deepcopy__
    __reduce_ex__=chunks.DevelopmentH1ChunkJournal.__reduce_ex__

    def _stage_metadata(self,index,locks,raw,stage,error):
        req=replay.native.model_api.H1StageRequest(self._packet.inputs,locks)
        return dict(schema=SCHEMA,kind='stage_accepted' if stage is not None else 'stage_rejected',
            request_key=self._key,index=index,objective=list(self._order[index]),
            stage_identity=replay.native.model_api.h1_stage_identity(req),
            prior_locks_sha256=sha256(chunks.base._bytes([v.hex() for v in locks])).hexdigest(),
            raw_sha256=sha256(raw).hexdigest(),lock_hex=None if stage is None else stage['lock'].hex(),
            numeric_sha256=None if stage is None else stage['numeric_sha256'],
            generation_mapping=getattr(error,'generation_mapping',None) if stage is None else stage['generation_mapping'],
            rejection=None if error is None else _error(error))

    def _terminal_metadata(self,projection):
        return dict(schema=SCHEMA,kind='accepted_terminal',request_key=self._key,
            stored_reports=len(self._order),projection_identity=projection.projection_identity,
            projection_sha256=sha256(projection.projection_payload).hexdigest(),
            canonical_locks=[v.hex() for v in projection.canonical_locks])

    def _projection(self,locks,assignment,hashes,pins,numeric):
        return replay._projection(self._packet,locks,assignment,hashes,pins,numeric,key=self._key,
            implementation=replay.implementation_identity())

    def _restore(self):
        """One verified chunk scan plus one ordered read pass in the same snapshot."""
        self._check()
        with self._journal._guard:
            connection=None
            try:
                connection=self._journal._connect()
                connection.execute('BEGIN')
                physical=self._journal._scan(connection)
                locks=()
                hashes,pins,numeric=[],[],[]
                assignment=projection=None
                status='collecting'
                stored=0
                for seq,metadata,size in connection.execute('SELECT seq,metadata,payload_bytes FROM events ORDER BY seq'):
                    if status in ('accepted','rejected'):raise ValueError('event after terminal hour archive')
                    if type(size) is not int or not 0<=size<=MAX_RAW:
                        raise ValueError('bounded per-stage raw payload required')
                    # Only one native report (<=16MiB) is assembled, never the full hour.
                    buffer=bytearray()
                    for (part,) in connection.execute('SELECT payload FROM chunks WHERE event_seq=? ORDER BY chunk_index',(seq,)):
                        buffer.extend(part)
                    raw=bytes(buffer)
                    del buffer
                    if len(raw)!=size:raise ValueError('hour raw payload length mismatch')
                    meta=replay.old._decode(metadata,chunks.METADATA_BYTES)
                    if type(meta) is not dict:raise ValueError('hour event metadata object required')
                    if meta.get('kind')=='accepted_terminal':
                        if len(locks)!=len(self._order) or raw:
                            raise ValueError('incomplete accepted terminal')
                        projection=self._projection(locks,assignment,hashes,pins,numeric)
                        expected=self._terminal_metadata(projection)
                        status='accepted'
                    else:
                        index=len(locks)
                        if index>=len(self._order) or not raw:raise ValueError('unexpected stage report')
                        stage=error=None
                        try:stage=replay._audit_stage(self._packet,self._spec,self._limits,index,locks,raw)
                        except replay.H1ReportAuditRejected as rejected:error=rejected
                        expected=self._stage_metadata(index,locks,raw,stage,error)
                        stored+=1
                        if stage is None:status='rejected'
                        else:
                            locks=(*locks,stage['lock'])
                            assignment=stage['assignment']
                            hashes.append(stage['native_sha256'])
                            pins.append(stage['stage_identity'])
                            numeric.append(stage['numeric_sha256'])
                    if metadata!=chunks.base._bytes(expected):raise ValueError('hour metadata differs from raw reconstruction')
                if status=='collecting' and len(locks)==len(self._order):status='awaiting_terminal'
                self._journal._check()
                self._check()
                return H1HourArchiveInspection(self._binding,physical.head,status,stored,locks,projection)
            finally:
                if connection is not None:connection.close()

    def inspect(self):
        with self._guard:
            try:
                self._state=self._restore()
                return self._state
            except BaseException:
                self._poisoned=True
                raise

    def record_report(self,raw,*,expected_head):
        """Numerically check and durably append; advance locks only after readback."""
        with self._guard:
            try:
                self._check()
                replay.native._pin(expected_head)
                if expected_head!=self._journal.head:raise ValueError('hour report requires independent predecessor head')
                prior=self._restore()
                if prior.status!='collecting':raise ValueError('terminal or complete stage prefix cannot accept report')
                if type(raw) is not bytes or not 0<len(raw)<=MAX_RAW:raise ValueError('bounded immutable raw report required')
                index=len(prior.canonical_locks)
                stage=error=None
                try:stage=replay._audit_stage(self._packet,self._spec,self._limits,index,prior.canonical_locks,raw)
                except replay.H1ReportAuditRejected as rejected:error=rejected
                self._check()
                metadata=self._stage_metadata(index,prior.canonical_locks,raw,stage,error)
                self._journal.append(metadata,(raw[i:i+chunks.CHUNK_BYTES] for i in range(0,len(raw),chunks.CHUNK_BYTES)),
                    expected_head=expected_head,declared_payload_bytes=len(raw),expected_payload_sha256=sha256(raw).hexdigest())
                restored=self._restore()
                if restored.stored_reports!=prior.stored_reports+1:raise ValueError('hour receipt fresh readback mismatch')
                self._state=restored
                return restored
            except BaseException:
                self._poisoned=True
                raise

    def finish(self,*,expected_head):
        """Publish only a diagnostic terminal inside this development archive."""
        with self._guard:
            try:
                self._check()
                replay.native._pin(expected_head)
                if expected_head!=self._journal.head:raise ValueError('hour terminal requires independent predecessor head')
                prior=self._restore()
                if prior.status!='awaiting_terminal':raise ValueError('complete accepted report prefix required')
                # Replay the prefix via one snapshot, and derive the final projection there.
                projection=self._replay_complete_prefix()
                metadata=self._terminal_metadata(projection)
                self._journal.append(metadata,iter(()),expected_head=expected_head,declared_payload_bytes=0,
                    expected_payload_sha256=sha256(b'').hexdigest())
                restored=self._restore()
                if restored.status!='accepted':raise ValueError('hour terminal fresh readback mismatch')
                self._state=restored
                return restored
            except BaseException:
                self._poisoned=True
                raise

    def _replay_complete_prefix(self):
        with self._journal._guard:
            connection=self._journal._connect()
            try:
                connection.execute('BEGIN')
                physical=self._journal._scan(connection)
                if physical.events!=len(self._order):raise ValueError('complete ordered stage prefix required')
                def reports():
                    for seq,size in connection.execute('SELECT seq,payload_bytes FROM events ORDER BY seq'):
                        if not 0<size<=MAX_RAW:raise ValueError('bounded prefix stage required')
                        buffer=bytearray()
                        for (part,) in connection.execute('SELECT payload FROM chunks WHERE event_seq=? ORDER BY chunk_index',(seq,)):
                            buffer.extend(part)
                        yield bytes(buffer)
                result=replay.replay_stream(self._packet,self._spec,self._limits,reports(),expected_key=self._key)
                self._journal._check()
                self._check()
                return result
            finally:connection.close()
