"""Controlled incremental hour archive; terminal still replays all evidence."""
from dataclasses import dataclass,fields
from hashlib import sha256
from pathlib import Path

from . import normal_h1_hour_archive_v2 as base

chunks,replay=base.chunks,base.replay
SCHEMA='h1_incremental_hour_archive_development_v2'


@dataclass(frozen=True)
class H1IncrementalArchiveInspection(base.H1HourArchiveInspection):
    incremental_writer_protocol: str = 'persistent_sqlite_data_version_and_changes_v1'


def _convert(value):
    return H1IncrementalArchiveInspection(**{f.name:getattr(value,f.name) for f in fields(base.H1HourArchiveInspection)})


class DevelopmentH1IncrementalArchive(base.DevelopmentH1HourArchive):
    """Cache only audited, durably read-back locks; keep one writer connection.

    No hostile raw-file/ABA claim. External SQL commits and unexpected own DML
    fail closed. Reads/terminal retain full replay; no native invocation here.
    """
    def __init__(self,*args,**kwargs):
        self._writer=self._epoch=None
        self._epoch_probe=None
        try:
            super().__init__(*args,**kwargs)
            self._writer=self._journal._connect()
            if kwargs.get('create',False):self._probe_epoch_semantics()
            self._writer.execute('BEGIN IMMEDIATE')
            self._epoch=self._version()
            self._state=self._restore()
            self._counts_cache=self._counts(self._writer)
            self._tail_cache=self._tail(self._writer)
            self._changes_cache=self._writer.total_changes
            self._fast_check(self._writer,self._counts_cache,self._tail_cache,self._changes_cache)
            self._writer.execute('ROLLBACK')
            self._cache_digest=self._cache_identity()
        except BaseException:
            if self._writer is not None:self._writer.close()
            self._writer=None
            if hasattr(self,'_journal'):self._journal.close()
            raise

    def _cache_identity(self):
        state=self._state
        if (type(state) is not H1IncrementalArchiveInspection or state.head!=self._journal._head
                or state.archive_identity!=self._binding):
            raise ValueError('incremental cache type/head mismatch')
        tail=self._tail_cache
        tail_pin=None if tail is None else sha256(chunks.base._bytes(
            [*tail[:2],sha256(tail[2]).hexdigest(),*tail[3:]])).hexdigest()
        return replay.current.source._digest(SCHEMA,repr(state),self._counts_cache,tail_pin,
            self._changes_cache,self._epoch)

    def _verify_cache(self):
        self._check()
        if self._cache_identity()!=self._cache_digest:
            raise ValueError('incremental audited cache changed')

    @property
    def head(self):
        with self._guard:
            try:
                self._verify_cache()
                return self._journal._head
            except BaseException:
                self._poisoned=self._journal._poisoned=True
                raise

    def _binding_identity(self):
        return replay.current.source._digest(SCHEMA,super()._binding_identity(),
            sha256(Path(__file__).read_bytes()).hexdigest(),
            'persistent_sqlite_data_version_and_changes_v1')

    def _stage_metadata(self,*args):
        value=super()._stage_metadata(*args)
        value['schema']=SCHEMA
        return value

    def _terminal_metadata(self,*args):
        value=super()._terminal_metadata(*args)
        value['schema']=SCHEMA
        return value

    def _version(self):
        value=self._writer.execute('PRAGMA data_version').fetchone()[0]
        if type(value) is not int:raise ValueError('exact SQLite data_version required')
        return value

    def _probe_epoch_semantics(self):
        # New empty development DB only. Reopens never modify the stored bytes.
        v0=self._version()
        self._writer.execute('PRAGMA user_version=1')
        v1=self._version()
        peer=self._journal._connect()
        try:peer.execute('PRAGMA user_version=2')
        finally:peer.close()
        v2=self._version()
        self._writer.execute('PRAGMA user_version=0')
        v3=self._version()
        if v0!=v1 or v1==v2 or v2!=v3:
            raise ValueError('SQLite connection epoch semantics not observed')
        self._epoch_probe=(v0,v1,v2,v3)

    def _check(self):
        super()._check()
        if self._epoch is not None and self._version()!=self._epoch:
            raise ValueError('external SQLite commit changed writer epoch')

    @staticmethod
    def _counts(connection):
        events=connection.execute('SELECT count(*),coalesce(sum(length(metadata)),0) FROM events').fetchone()
        raw=connection.execute('SELECT count(*),coalesce(sum(length(payload)),0) FROM chunks').fetchone()
        return (*events,*raw)

    @staticmethod
    def _tail(connection):
        return connection.execute('SELECT * FROM events ORDER BY seq DESC LIMIT 1').fetchone()

    def _fast_check(self,connection,counts,tail,changes):
        self._check()
        self._journal._check()
        if (connection.execute('PRAGMA user_version').fetchone()[0]!=0
                or connection.execute('PRAGMA application_id').fetchone()[0]!=chunks.APPLICATION_ID
                or set(r[0] for r in connection.execute('SELECT sql FROM sqlite_master WHERE sql IS NOT NULL'))!=set(chunks.TABLES)
                or connection.execute('SELECT id,header FROM metadata').fetchall()!=[(1,self._journal._header)]
                or self._counts(connection)!=counts or self._tail(connection)!=tail
                or self._writer.total_changes!=changes):
            raise ValueError('incremental schema/count/tail/own-DML drift')

    def _restore(self):
        return _convert(super()._restore())

    def _protected_restore(self):
        self._check()
        self._writer.execute('BEGIN IMMEDIATE')
        try:
            self._fast_check(self._writer,self._counts_cache,self._tail_cache,self._changes_cache)
            result=self._restore()
            self._check()
            return result
        finally:self._writer.execute('ROLLBACK')

    def inspect(self):
        with self._guard:
            try:
                self._verify_cache()
                self._state=self._protected_restore()
                self._cache_digest=self._cache_identity()
                return self._state
            except BaseException:
                self._poisoned=self._journal._poisoned=True
                raise

    def _append_incremental(self,metadata,raw):
        """Only current event payload is read back; cached prefix has stable epoch."""
        with self._journal._guard:
            readback=None
            try:
                self._check()
                self._writer.execute('BEGIN IMMEDIATE')
                self._fast_check(self._writer,self._counts_cache,self._tail_cache,self._changes_cache)
                meta=chunks.base._bytes(metadata)
                size=len(raw)
                budget=self._journal._budget
                seq=self._counts_cache[0]+1
                n=(size+chunks.CHUNK_BYTES-1)//chunks.CHUNK_BYTES
                counts=(seq,self._counts_cache[1]+len(meta),self._counts_cache[2]+n,self._counts_cache[3]+size)
                if (len(meta)>chunks.METADATA_BYTES or seq>budget.max_events
                        or len(meta)+size>budget.max_event_bytes or counts[1]+counts[3]>budget.max_total_bytes):
                    raise ValueError('incremental content budget exhausted')
                before=self._journal._head
                chain=sha256(chunks.base._bytes([chunks.SCHEMA,seq,before,'chunks'])).hexdigest()
                for index,start in enumerate(range(0,size,chunks.CHUNK_BYTES)):
                    part=raw[start:start+chunks.CHUNK_BYTES]
                    chain=chunks._chunk_head(seq,index,chain,part)
                    self._writer.execute('INSERT INTO chunks VALUES (?,?,?,?,?)',
                        (seq,index,part,sha256(part).hexdigest(),chain))
                pin=sha256(raw).hexdigest()
                head=chunks._head(seq,before,meta,size,n,pin,chain)
                row=(seq,before,meta,size,n,pin,chain,head)
                self._writer.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?,?)',row)
                changes=self._changes_cache+n+1
                self._check()
                self._journal._commit(self._writer)
                # Re-acquire writer exclusion before opening a fresh reader.
                # A competing commit in the gap is detected by this writer's epoch.
                self._writer.execute('BEGIN IMMEDIATE')
                self._fast_check(self._writer,counts,row,changes)
                readback=self._journal._connect()
                readback.execute('BEGIN')
                self._fast_check(readback,counts,row,changes)
                actual=sha256()
                fresh_raw=bytearray()
                actual_chain=sha256(chunks.base._bytes([chunks.SCHEMA,seq,before,'chunks'])).hexdigest()
                seen=length=0
                for index,part,part_pin,part_chain in readback.execute(
                        'SELECT chunk_index,payload,payload_sha,chunk_chain FROM chunks WHERE event_seq=? ORDER BY chunk_index',(seq,)):
                    if (index!=seen or type(part) is not bytes or not 0<len(part)<=chunks.CHUNK_BYTES
                            or sha256(part).hexdigest()!=part_pin):
                        raise ValueError('incremental fresh chunk mismatch')
                    actual_chain=chunks._chunk_head(seq,index,actual_chain,part)
                    if part_chain!=actual_chain:raise ValueError('incremental fresh chain mismatch')
                    actual.update(part)
                    fresh_raw.extend(part)
                    length+=len(part)
                    seen+=1
                if (seen!=n or length!=size or actual.hexdigest()!=pin or actual_chain!=chain):
                    raise ValueError('incremental fresh event mismatch')
                self._check()
                readback.close()
                readback=None
                self._writer.execute('ROLLBACK')
                self._check()
                # Public owner guard excludes observation of partial cache updates.
                self._journal._head=head
                self._counts_cache,self._tail_cache,self._changes_cache=counts,row,changes
                return head,bytes(fresh_raw)
            except BaseException:
                self._poisoned=self._journal._poisoned=True
                raise
            finally:
                if readback is not None:readback.close()
                if self._writer.in_transaction:self._writer.execute('ROLLBACK')

    def record_report(self,raw,*,expected_head):
        with self._guard:
            try:
                self._verify_cache()
                replay.native._pin(expected_head)
                if expected_head!=self._journal._head:raise ValueError('independent incremental predecessor required')
                prior=self._state
                if prior.status!='collecting':raise ValueError('terminal or complete incremental prefix')
                if type(raw) is not bytes or not 0<len(raw)<=base.MAX_RAW:raise ValueError('bounded immutable raw required')
                stage=error=None
                index=len(prior.canonical_locks)
                try:stage=replay._audit_stage(self._packet,self._spec,self._limits,index,prior.canonical_locks,raw)
                except replay.H1ReportAuditRejected as rejected:error=rejected
                metadata=self._stage_metadata(index,prior.canonical_locks,raw,stage,error)
                head,fresh_raw=self._append_incremental(metadata,raw)
                fresh_stage=fresh_error=None
                try:fresh_stage=replay._audit_stage(self._packet,self._spec,self._limits,index,prior.canonical_locks,fresh_raw)
                except replay.H1ReportAuditRejected as rejected:fresh_error=rejected
                if self._stage_metadata(index,prior.canonical_locks,fresh_raw,fresh_stage,fresh_error)!=metadata:
                    raise ValueError('fresh raw semantic audit changed')
                self._check()
                stage=fresh_stage
                locks=prior.canonical_locks if stage is None else (*prior.canonical_locks,stage['lock'])
                status='rejected' if stage is None else 'awaiting_terminal' if len(locks)==len(self._order) else 'collecting'
                self._state=H1IncrementalArchiveInspection(self._binding,head,status,prior.stored_reports+1,locks,None)
                self._cache_digest=self._cache_identity()
                return self._state
            except BaseException:
                self._poisoned=self._journal._poisoned=True
                raise

    def finish(self,*,expected_head):
        with self._guard:
            try:
                self._verify_cache()
                replay.native._pin(expected_head)
                if expected_head!=self._journal._head:raise ValueError('independent incremental terminal head required')
                prior=self._protected_restore()
                if prior!=self._state:raise ValueError('terminal cache differs from complete replay')
                if prior.status!='awaiting_terminal':raise ValueError('complete accepted prefix required')
                self._writer.execute('BEGIN IMMEDIATE')
                try:
                    self._fast_check(self._writer,self._counts_cache,self._tail_cache,self._changes_cache)
                    projection=self._replay_complete_prefix()
                    self._check()
                finally:self._writer.execute('ROLLBACK')
                self._append_incremental(self._terminal_metadata(projection),b'')
                restored=self._protected_restore()
                if restored.status!='accepted':raise ValueError('incremental terminal replay failed')
                self._state=restored
                self._cache_digest=self._cache_identity()
                return restored
            except BaseException:
                self._poisoned=self._journal._poisoned=True
                raise

    def close(self):
        with self._guard:
            if not self._closed:
                try:
                    if self._writer is not None:self._writer.close()
                finally:
                    self._writer=None
                    self._journal.close()
                    self._closed=True
