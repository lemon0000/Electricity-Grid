"""Development-only streaming chunk journal; no numerical or execution authority."""
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from threading import Lock
import os
import sqlite3

from . import normal_h1_projection_store as base

SCHEMA = 'h1_chunk_journal_development_v1'
APPLICATION_ID = 0x48433131
CHUNK_BYTES = 1024**2
METADATA_BYTES = 256*1024
TABLES = (
    'CREATE TABLE metadata (id INTEGER PRIMARY KEY, header BLOB NOT NULL) STRICT',
    'CREATE TABLE events (seq INTEGER PRIMARY KEY, predecessor TEXT NOT NULL, metadata BLOB NOT NULL, payload_bytes INTEGER NOT NULL, chunk_count INTEGER NOT NULL, payload_sha TEXT NOT NULL, chunk_root TEXT NOT NULL, head TEXT NOT NULL) STRICT',
    'CREATE TABLE chunks (event_seq INTEGER NOT NULL, chunk_index INTEGER NOT NULL, payload BLOB NOT NULL, payload_sha TEXT NOT NULL, chunk_chain TEXT NOT NULL, PRIMARY KEY (event_seq, chunk_index)) STRICT',
)


def _pin(value):
    base.replay.native._pin(value)


def _chunk_head(seq, index, before, payload):
    return sha256(base._bytes([SCHEMA,seq,index,before,len(payload),sha256(payload).hexdigest()])).hexdigest()


def _head(seq, before, metadata, size, count, pin, root):
    return sha256(base._bytes([SCHEMA,seq,before,sha256(metadata).hexdigest(),size,count,pin,root])).hexdigest()


@dataclass(frozen=True)
class ChunkContentBudget:
    max_events: int
    max_event_bytes: int
    max_total_bytes: int

    def __post_init__(self):
        for value in asdict(self).values():
            if type(value) is not int or not 1 <= value < 2**63:
                raise ValueError('positive built-in bounded content budget required')
        if self.max_events > 384 or self.max_event_bytes > self.max_total_bytes:
            raise ValueError('bounded event count and consistent content budgets required')


@dataclass(frozen=True)
class ChunkInspection:
    store_identity: str
    head: str
    events: int
    content_bytes: int
    payload_bytes: int
    chunks: int
    content_verified: bool = True
    physical_space_reserved: bool = False
    numerical_chain_verified: bool = False
    native_execution_authenticated: bool = False
    formal_result: bool = False
    formal_execution_ready: bool = False


class _Exclusive:
    """Reject overlapping/reentrant API calls, including a live stream reader."""
    def __init__(self): self._lock=Lock()
    def __enter__(self):
        if not self._lock.acquire(blocking=False):
            raise ValueError('chunk journal operation already active')
        return self
    def __exit__(self, *args): self._lock.release()


class DevelopmentH1ChunkJournal:
    """Atomic event/chunks/head transactions and streaming verification.

    Content budgets include metadata and payload, not SQLite/index/journal space.
    This is an independent physical store, not an episode state machine.
    """
    def __init__(self, root, budget, *, binding_identity, create=False, expected_head=None):
        if type(budget) is not ChunkContentBudget:
            raise ValueError('exact chunk content budget required')
        budget.__post_init__()
        _pin(binding_identity)
        if type(create) is not bool or (create and expected_head is not None):
            raise ValueError('explicit create or independently pinned reopen required')
        if not create: _pin(expected_head)
        self._budget,self._binding=budget,binding_identity
        self._closed=self._poisoned=False
        self._guard=_Exclusive()
        self._lease=base.local._Lease(root,create)
        try:
            self._header=self._header_bytes()
            self.identity=sha256(self._header).hexdigest()
            self._genesis=sha256(base._bytes([SCHEMA,self.identity,'genesis'])).hexdigest()
            self._head=self._genesis if create else expected_head
            self._database=self._lease.root/'h1_chunk_journal.sqlite3'
            if create:
                with self._database.open('xb') as stream: os.fsync(stream.fileno())
            self._file_identity=base.local._file_identity(self._database)
            connection=self._connect()
            try:
                if create:
                    connection.execute('BEGIN IMMEDIATE')
                    for sql in TABLES: connection.execute(sql)
                    connection.execute('PRAGMA application_id='+str(APPLICATION_ID))
                    connection.execute('INSERT INTO metadata VALUES (1,?)',(self._header,))
                    self._commit(connection)
                self._scan(connection)
            finally: connection.close()
        except BaseException:
            self._lease.close()
            raise

    def _header_bytes(self):
        return base._bytes(dict(schema=SCHEMA,root=os.path.normcase(str(self._lease.root)),
            budget=asdict(self._budget),binding_identity=self._binding,chunk_bytes=CHUNK_BYTES,
            metadata_bytes=METADATA_BYTES,tables=TABLES,application_id=APPLICATION_ID,
            implementation=sha256(Path(__file__).read_bytes()).hexdigest(),
            base_implementation=sha256(Path(base.__file__).read_bytes()).hexdigest(),
            codec_validation_implementation=base.replay.implementation_identity(),
            lease_implementation=sha256(Path(base.local.__file__).read_bytes()).hexdigest(),
            sqlite_version=sqlite3.sqlite_version,formal_result=False))

    _check=base.DevelopmentH1ProjectionStore._check
    _connect=base.DevelopmentH1ProjectionStore._connect
    _commit=base.DevelopmentH1ProjectionStore._commit
    close=base.DevelopmentH1ProjectionStore.close
    __copy__=base.DevelopmentH1ProjectionStore.__copy__
    __deepcopy__=base.DevelopmentH1ProjectionStore.__deepcopy__
    __reduce_ex__=base.DevelopmentH1ProjectionStore.__reduce_ex__

    @property
    def head(self):
        with self._guard:
            self._check()
            return self._head

    def _scan(self, connection):
        if (connection.execute('PRAGMA integrity_check').fetchall()!=[('ok',)]
                or connection.execute('PRAGMA application_id').fetchone()[0]!=APPLICATION_ID
                or set(r[0] for r in connection.execute('SELECT sql FROM sqlite_master WHERE sql IS NOT NULL'))!=set(TABLES)
                or connection.execute('SELECT id,header FROM metadata').fetchall()!=[(1,self._header)]):
            raise ValueError('chunk journal schema/header/integrity mismatch')
        summary=connection.execute('SELECT count(*),coalesce(sum(length(metadata)),0),coalesce(max(length(metadata)),0) FROM events').fetchone()
        chunks=connection.execute('SELECT count(*),coalesce(sum(length(payload)),0),coalesce(max(length(payload)),0),coalesce(min(length(payload)),1) FROM chunks').fetchone()
        if (summary[0]>self._budget.max_events or summary[2]>METADATA_BYTES
                or summary[1]+chunks[1]>self._budget.max_total_bytes or chunks[2]>CHUNK_BYTES or chunks[3]<1):
            raise ValueError('chunk journal stored content budget exceeded')
        head=self._genesis
        count=total=payload_total=chunk_total=0
        for seq,before,metadata,size,n,pin,root,after in connection.execute('SELECT * FROM events ORDER BY seq'):
            count+=1
            decoded=base.replay._decode(metadata,METADATA_BYTES)
            if (type(decoded) is not dict or seq!=count or before!=head or type(size) is not int or size<0
                    or type(n) is not int or n<0 or len(metadata)+size>self._budget.max_event_bytes):
                raise ValueError('chunk event metadata/order/size mismatch')
            _pin(pin)
            digest=sha256()
            seen=actual=0
            chunk_head=sha256(base._bytes([SCHEMA,seq,before,'chunks'])).hexdigest()
            for index,payload,chunk_pin,chain in connection.execute('SELECT chunk_index,payload,payload_sha,chunk_chain FROM chunks WHERE event_seq=? ORDER BY chunk_index',(seq,)):
                if index!=seen or type(payload) is not bytes or not 0<len(payload)<=CHUNK_BYTES or sha256(payload).hexdigest()!=chunk_pin:
                    raise ValueError('chunk order/payload/hash mismatch')
                expected_chain=_chunk_head(seq,index,chunk_head,payload)
                if chain!=expected_chain: raise ValueError('chunk chain mismatch')
                chunk_head=chain
                digest.update(payload)
                seen+=1
                actual+=len(payload)
            if (seen!=n or actual!=size or digest.hexdigest()!=pin
                    or root!=chunk_head or after!=_head(seq,before,metadata,size,n,pin,root)):
                raise ValueError('chunk event descriptor/head mismatch')
            head=after
            total+=len(metadata)+size
            payload_total+=size
            chunk_total+=n
        if head!=self._head or chunk_total!=chunks[0] or payload_total!=chunks[1]:
            raise ValueError('independent chunk head or orphan chunk mismatch')
        return ChunkInspection(self.identity,head,count,total,payload_total,chunk_total)

    def inspect(self):
        with self._guard:
            connection=None
            try:
                connection=self._connect()
                connection.execute('BEGIN')
                result=self._scan(connection)
                self._check()
                return result
            except BaseException:
                self._poisoned=True
                raise
            finally:
                if connection is not None: connection.close()

    def append(self, metadata, payload_chunks, *, expected_head, declared_payload_bytes, expected_payload_sha256):
        """Consume bounded bytes chunks without joining an event in memory."""
        with self._guard:
            connection=None
            try:
                self._check()
                _pin(expected_head)
                if expected_head!=self._head:
                    raise ValueError('independently retained predecessor required')
                _pin(expected_payload_sha256)
                if type(declared_payload_bytes) is not int or not 0<=declared_payload_bytes<2**63:
                    raise ValueError('exact declared payload length required')
                if type(metadata) is not dict:
                    raise ValueError('canonical metadata object required')
                raw=base._bytes(metadata)
                if len(raw)>min(METADATA_BYTES,self._budget.max_event_bytes):
                    raise ValueError('metadata content limit exceeded')
                connection=self._connect()
                connection.execute('BEGIN IMMEDIATE')
                prior=self._scan(connection)
                if prior.events>=self._budget.max_events:
                    raise ValueError('chunk event count exhausted')
                if (len(raw)+declared_payload_bytes>self._budget.max_event_bytes
                        or prior.content_bytes+len(raw)+declared_payload_bytes>self._budget.max_total_bytes):
                    raise ValueError('declared content exceeds total budget or event budget')
                seq=prior.events+1
                chunk_head=sha256(base._bytes([SCHEMA,seq,self._head,'chunks'])).hexdigest()
                size=n=0
                digest=sha256()
                for chunk in payload_chunks:
                    if type(chunk) is not bytes or not 0<len(chunk)<=CHUNK_BYTES:
                        raise ValueError('nonempty bounded immutable chunks required')
                    size+=len(chunk)
                    if (size>declared_payload_bytes or len(raw)+size>self._budget.max_event_bytes
                            or prior.content_bytes+len(raw)+size>self._budget.max_total_bytes):
                        raise ValueError('chunk content budget exhausted')
                    chunk_head=_chunk_head(seq,n,chunk_head,chunk)
                    connection.execute('INSERT INTO chunks VALUES (?,?,?,?,?)',(seq,n,chunk,sha256(chunk).hexdigest(),chunk_head))
                    digest.update(chunk)
                    n+=1
                if prior.content_bytes+len(raw)+size>self._budget.max_total_bytes:
                    raise ValueError('chunk metadata exhausts total budget')
                if size!=declared_payload_bytes or digest.hexdigest()!=expected_payload_sha256:
                    raise ValueError('independent declared payload length/hash mismatch')
                head=_head(seq,self._head,raw,size,n,digest.hexdigest(),chunk_head)
                connection.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?,?)',(seq,self._head,raw,size,n,digest.hexdigest(),chunk_head,head))
                self._check()
                self._commit(connection)
                self._head=head
                connection.close()
                connection=None
                connection=self._connect()
                connection.execute('BEGIN')
                result=self._scan(connection)
                if (result.events!=seq or result.content_bytes!=prior.content_bytes+len(raw)+size):
                    raise ValueError('fresh chunk commit readback mismatch')
                self._check()
                return result
            except BaseException:
                self._poisoned=True
                raise
            finally:
                if connection is not None: connection.close()

    def event_metadata(self, seq, *, expected_head):
        """Return bounded canonical metadata only after full prefix verification."""
        with self._guard:
            connection=None
            try:
                _pin(expected_head)
                if type(seq) is not int or seq<1 or expected_head!=self._head:
                    raise ValueError('exact event sequence and independent head required')
                connection=self._connect()
                connection.execute('BEGIN')
                inspection=self._scan(connection)
                if seq>inspection.events: raise ValueError('absent chunk event')
                raw=connection.execute('SELECT metadata FROM events WHERE seq=?',(seq,)).fetchone()[0]
                self._check()
                return raw
            except BaseException:
                self._poisoned=True
                raise
            finally:
                if connection is not None: connection.close()

    def iter_event(self, seq, *, expected_head):
        """Yield verified bytes from one SQLite read snapshot; never a decision."""
        with self._guard:
            connection=None
            try:
                _pin(expected_head)
                if type(seq) is not int or seq<1 or expected_head!=self._head:
                    raise ValueError('exact event sequence and independent head required')
                connection=self._connect()
                connection.execute('BEGIN')
                inspection=self._scan(connection)
                if seq>inspection.events: raise ValueError('absent chunk event')
                self._check()
                for (payload,) in connection.execute('SELECT payload FROM chunks WHERE event_seq=? ORDER BY chunk_index',(seq,)):
                    yield payload
                self._check()
            except BaseException:
                self._poisoned=True
                raise
            finally:
                if connection is not None: connection.close()
