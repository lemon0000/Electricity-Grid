"""Append-only local H1 projection journal; no executable cursor or run authority."""
from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import sqlite3
from threading import Lock

from . import episode_store as local
from . import normal_h1_replay as replay


SCHEMA = 'h1_common_projection_development_journal_v1'
APPLICATION_ID = 0x48315031
MAX_JOURNAL_BYTES = 64 * 1024**2
TABLES = (
    'CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id=1), header BLOB NOT NULL) STRICT',
    'CREATE TABLE records (seq INTEGER PRIMARY KEY, predecessor TEXT NOT NULL, request_key TEXT NOT NULL, archive_sha256 TEXT NOT NULL, archive BLOB NOT NULL, head TEXT NOT NULL UNIQUE) STRICT',
)


def _bytes(value):
    return replay.native.capture.encode(value)


def _head(sequence, before, key, pin):
    return sha256(_bytes([SCHEMA, sequence, before, key, pin])).hexdigest()


@dataclass(frozen=True, init=False)
class H1StoredProjection(replay.current.source._Owned):
    store_identity: str
    head: str
    request_key: str
    status: str
    witness_count: int
    projection_identity: str | None
    projection_payload: bytes | None
    native_execution_authenticated: bool
    formal_result: bool
    executable_boundary_restored: bool


class DevelopmentH1ProjectionStore:
    """Bounded NTFS journal for already-completed evidence, under one owner.

    Every read replays all witnesses for the requested key. Any different
    projection permanently conflicts that key; the first record is preserved.
    This journal does not admit native invocations or advance an episode head.
    """
    def __init__(self, root, *, create=False, expected_head=None, max_records=64):
        if type(create) is not bool or type(max_records) is not int or not 1 <= max_records <= 64:
            raise ValueError('explicit create flag and short record budget 1..64 required')
        if create and expected_head is not None:
            raise ValueError('new store cannot have retained head')
        if not create:
            replay.native._pin(expected_head)
        self._limit, self._closed, self._poisoned = max_records, False, False
        self._guard = Lock()
        self._lease = local._Lease(root, create)
        try:
            self._header = self._header_bytes()
            self.identity = sha256(self._header).hexdigest()
            self._genesis = sha256(_bytes([SCHEMA, self.identity, 'genesis'])).hexdigest()
            self._database = self._lease.root/'h1_projections.sqlite3'
            if create:
                with self._database.open('xb') as stream:
                    os.fsync(stream.fileno())
            self._file_identity = local._file_identity(self._database)
            if create:
                connection = self._connect()
                try:
                    connection.execute('BEGIN IMMEDIATE')
                    for sql in TABLES:
                        connection.execute(sql)
                    connection.execute('PRAGMA application_id='+str(APPLICATION_ID))
                    connection.execute('INSERT INTO metadata VALUES (1, ?)', (self._header,))
                    connection.execute('COMMIT')
                finally:
                    connection.close()
            self._head = self._genesis if create else expected_head
            connection = self._connect()
            try:
                self._rows(connection)
            finally:
                connection.close()
        except BaseException:
            self._lease.close()
            raise

    def _header_bytes(self):
        return _bytes(dict(schema=SCHEMA, root=os.path.normcase(str(self._lease.root)),
            max_records=self._limit, max_archive_bytes=replay.MAX_ARCHIVE_BYTES,
            max_journal_bytes=MAX_JOURNAL_BYTES,
            implementation=sha256(Path(__file__).read_bytes()).hexdigest(),
            local_lease_implementation=sha256(Path(local.__file__).read_bytes()).hexdigest(),
            replay_implementation=replay.implementation_identity(), sqlite=sqlite3.sqlite_version,
            tables=TABLES, formal_result=False))

    @property
    def head(self):
        return self._head

    def _check(self):
        if self._closed or self._poisoned:
            raise ValueError('closed or unresolved H1 journal owner')
        self._lease.check()
        if (self._header != self._header_bytes()
                or local._file_identity(self._database) != self._file_identity):
            raise ValueError('H1 journal implementation or file identity drift')
        for suffix in ('-journal', '-wal', '-shm'):
            path = local._path(str(self._database)+suffix)
            if path.exists():
                local._file_identity(path)
                if suffix != '-journal':
                    raise ValueError('unexpected WAL sidecar')

    def _connect(self):
        self._check()
        connection = sqlite3.connect(self._database.as_uri()+'?mode=rw', uri=True,
                                    timeout=0, isolation_level=None, check_same_thread=False)
        try:
            connection.execute('PRAGMA synchronous=FULL')
            if (connection.execute('PRAGMA journal_mode').fetchone()[0] != 'delete'
                    or connection.execute('PRAGMA synchronous').fetchone()[0] != 2):
                raise ValueError('DELETE/FULL journal required')
            return connection
        except BaseException:
            connection.close()
            raise

    def _rows(self, connection):
        if (connection.execute('PRAGMA integrity_check').fetchall() != [('ok',)]
                or connection.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID
                or set(r[0] for r in connection.execute('SELECT sql FROM sqlite_master WHERE sql IS NOT NULL')) != set(TABLES)
                or connection.execute('SELECT id,header FROM metadata').fetchall() != [(1, self._header)]):
            raise ValueError('H1 journal schema/header/integrity mismatch')
        # Check count and byte budgets before materializing archived blobs.
        summary = connection.execute('SELECT count(*), max(length(archive)), coalesce(sum(length(archive)),0) FROM records').fetchone()
        if (summary[0] > self._limit or (summary[1] is not None and summary[1] > replay.MAX_ARCHIVE_BYTES)
                or summary[2] > MAX_JOURNAL_BYTES):
            raise ValueError('H1 journal byte or record budget exceeded')
        rows = connection.execute('SELECT seq,predecessor,request_key,archive_sha256,archive,head FROM records ORDER BY seq').fetchall()
        head = self._genesis
        for expected, (seq, before, key, pin, archive, after) in enumerate(rows, 1):
            replay.native._pin(key)
            replay.native._pin(pin)
            if (seq != expected or before != head or type(archive) is not bytes
                    or sha256(archive).hexdigest() != pin or after != _head(seq, before, key, pin)):
                raise ValueError('H1 journal history or archive hash mismatch')
            head = after
        if head != self._head:
            raise ValueError('independently retained H1 journal head mismatch')
        return rows

    def _projection(self, rows, packet, specification, budget, key, head):
        projections = []
        for _, _, row_key, pin, archive, _ in rows:
            if row_key == key:
                value = replay.replay_archive(packet, specification, budget, archive,
                    expected_key=key, expected_archive_sha256=pin)
                self._validate_projection(value, key)
                projections.append(value)
        first = projections[0] if projections else None
        conflict = any((p.projection_identity, p.projection_payload) !=
                       (first.projection_identity, first.projection_payload) for p in projections)
        available = first is not None and not conflict
        return replay.current.source._owned(H1StoredProjection, store_identity=self.identity, head=head,
            request_key=key, status='unresolved_conflict' if conflict else 'available' if available else 'absent',
            witness_count=len(projections), projection_identity=first.projection_identity if available else None,
            projection_payload=first.projection_payload if available else None,
            native_execution_authenticated=False, formal_result=False, executable_boundary_restored=False)

    @staticmethod
    def _validate_projection(value, key):
        if (type(value) is not replay.H1ReplayedProjection or value.request_key != key
                or any(getattr(value, name) is not False for name in (
                    'native_execution_authenticated', 'published', 'formal_result'))
                or type(value.solver_calls_by_replay) is not int or value.solver_calls_by_replay != 0
                or value.numerical_chain_recomputed is not True
                or type(value.projection_payload) is not bytes or not value.projection_payload):
            raise ValueError('H1 replay projection type or authority drift')
        replay.native._pin(value.projection_identity)

    def inspect(self, packet, specification, budget, *, expected_key):
        with self._guard:
            if replay.current.request_key(packet, specification, budget) != expected_key:
                raise ValueError('H1 store request key mismatch')
            connection = self._connect()
            try:
                rows = self._rows(connection)
                result = self._projection(rows, packet, specification, budget, expected_key, self._head)
                self._check()
                return result
            finally:
                connection.close()

    def _commit(self, connection):
        connection.execute('COMMIT')

    def append(self, packet, specification, budget, archive, *, expected_key, expected_archive_sha256):
        with self._guard:
            self._check()
            value = replay.replay_archive(packet, specification, budget, archive,
                expected_key=expected_key, expected_archive_sha256=expected_archive_sha256)
            self._validate_projection(value, expected_key)
            connection = self._connect()
            try:
                connection.execute('BEGIN IMMEDIATE')
                rows = self._rows(connection)
                # Replay existing evidence too, including already conflicted keys.
                self._projection(rows, packet, specification, budget, expected_key, self._head)
                if any(row[2:4] == (expected_key, expected_archive_sha256) for row in rows):
                    result = self._projection(rows, packet, specification, budget, expected_key, self._head)
                    expected_rows = rows
                else:
                    if len(rows) >= self._limit:
                        raise ValueError('H1 journal record budget exhausted')
                    if sum(len(row[4]) for row in rows)+len(archive) > MAX_JOURNAL_BYTES:
                        raise ValueError('H1 journal aggregate byte budget exhausted')
                    seq = len(rows)+1
                    head = _head(seq, self._head, expected_key, expected_archive_sha256)
                    row = (seq, self._head, expected_key, expected_archive_sha256, archive, head)
                    expected_rows = [*rows, row]
                    result = self._projection(expected_rows, packet, specification, budget, expected_key, head)
                    connection.execute('INSERT INTO records VALUES (?,?,?,?,?,?)', row)
                self._check()
                self._commit(connection)
                self._head = result.head
                connection.close()
                connection = None
                readback = self._connect()
                try:
                    if self._rows(readback) != expected_rows:
                        raise ValueError('H1 commit readback differs from verified archive history')
                finally:
                    readback.close()
                self._check()
                return result
            except BaseException:
                # Includes the commit/return ambiguity window: this owner cannot
                # retry; recovery requires an independently retained exact head.
                self._poisoned = True
                raise
            finally:
                if connection is not None:
                    connection.close()

    def close(self):
        with self._guard:
            if not self._closed:
                self._closed = True
                self._lease.close()

    def __copy__(self):
        raise TypeError('H1 journal owner cannot be copied')

    def __deepcopy__(self, memo):
        raise TypeError('H1 journal owner cannot be copied')

    def __reduce_ex__(self, protocol):
        raise TypeError('H1 journal owner cannot be pickled')
