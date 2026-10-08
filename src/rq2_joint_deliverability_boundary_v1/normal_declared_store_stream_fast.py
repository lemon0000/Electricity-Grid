"""One-shot local normal invocation journal; no restored executable result."""
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import sqlite3
from threading import Lock

from . import episode_store as local, normal_declared_execution_stream_fast as execution


SCHEMA = 'draft_local_ntfs_one_declared_fast_streaming_normal_invocation_v1'
APPLICATION_ID = 0x4e465331
TABLES = (
    'CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id=1), header BLOB NOT NULL) STRICT',
    'CREATE TABLE intent (id INTEGER PRIMARY KEY CHECK(id=1), payload BLOB NOT NULL) STRICT',
    'CREATE TABLE result (id INTEGER PRIMARY KEY CHECK(id=1) REFERENCES intent(id), payload BLOB NOT NULL, digest TEXT NOT NULL) STRICT',
)


def _bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def _decoded(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate normal journal JSON key')
            result[key] = value
        return result
    item = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    if _bytes(item) != raw:
        raise ValueError('canonical normal journal JSON required')
    return item


def _result_identity(encoded):
    # Exact wire equivalent of continuous_grid_normal._digest(result).
    return sha256(json.dumps(['tuple', [encoded]], ensure_ascii=True, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class DeclaredFastNormalStoreInspection:
    store_identity: str
    genesis: str
    head: str
    status: str
    intent_present: bool
    result_present: bool
    result_identity: str | None
    archived_result_sha256: str | None
    numerical_evidence_replayed: bool = False
    native_execution_authenticated: bool = False
    formal_result: bool = False


class DevelopmentDeclaredFastNormalStore:
    """Cooperative one-shot owner in one canonical local NTFS directory.

    A pending intent is unknown even after process death. A returned record is
    integrity-checked diagnostic data, not an executable cursor or certificate.
    """
    def __init__(self, root, request, *, create=False,
                 expected_head=None, max_record_bytes, **arguments):
        if type(max_record_bytes) is not int or max_record_bytes <= 0:
            raise ValueError('positive explicit full journal record byte budget required')
        if type(create) is not bool:
            raise ValueError('explicit create boolean required')
        if create and expected_head is not None:
            raise ValueError('new normal store cannot supply a previous head')
        self._request = deepcopy(request)
        self._arguments = deepcopy(arguments)
        self._max_record_bytes = max_record_bytes
        self._guard = Lock()
        self._closed = self._poisoned = False
        self._lease = local._Lease(root, create)
        try:
            self._header = self._current_header()
            self._identity = sha256(self._header).hexdigest()
            self._genesis = sha256(_bytes([SCHEMA, self._identity, 'genesis'])).hexdigest()
            self._intent = _bytes(dict(schema=SCHEMA, store_identity=self._identity,
                predecessor=self._genesis, declared_execution_identity=arguments['expected_declared_execution_identity']))
            self._database = self._lease.root/'normal.sqlite3'
            if create:
                with self._database.open('xb') as stream:
                    os.fsync(stream.fileno())
            self._database_identity = local._file_identity(self._database)
            if create:
                self._initialize()
            inspection = self._inspect()
            if not create:
                execution.kernel._pin(expected_head)
                # An independently held genesis can reconcile a lost result
                # response. It never permits retry once an intent exists.
                if expected_head not in (self._genesis, inspection.head):
                    raise ValueError('independent normal journal head mismatch')
        except BaseException:
            self._lease.close()
            raise

    def _current_header(self):
        a = self._arguments
        required = {'expected_request_identity', 'expected_declared_execution_identity',
            'expected_assembly_identity', 'expected_binding_identity', 'expected_source_implementation_identity',
            'expected_binding_implementation_identity', 'expected_normal_execution_identity',
            'expected_source_execution_identity', 'specification', 'budget'}
        request = self._request
        if set(a) != required or type(request) is not execution.prepare.legacy.NormalTaskSourceRequest:
            raise ValueError('complete exact declared normal execution request required')
        request.__post_init__()
        for key in required - {'specification', 'budget'}:
            execution.kernel._pin(a[key])
        execution.kernel._validate(a['specification'], a['budget'], request.expected_scale)
        if execution.prepare.task_source_identity(request) != a['expected_request_identity']:
            raise ValueError('journal prepared request identity differs')
        if execution.declared_execution_identity(request,
                expected_request_identity=a['expected_request_identity'],
                expected_source_execution_identity=a['expected_source_execution_identity']) != a['expected_declared_execution_identity']:
            raise ValueError('journal declared execution identity differs')
        if (execution.source.binding.source.implementation_identity() != a['expected_source_implementation_identity']
                or execution.source.binding.implementation_identity() != a['expected_binding_implementation_identity']
                or execution.kernel.normal_execution_identity(request.expected_input_identity, request.expected_scale,
                    a['specification'], a['budget']) != a['expected_normal_execution_identity']):
            raise ValueError('journal source/binder/kernel implementation differs')
        if SCHEMA != 'draft_local_ntfs_one_declared_fast_streaming_normal_invocation_v1':
            raise ValueError('normal journal schema drift')
        return _bytes(dict(schema=SCHEMA, root=os.path.normcase(str(self._lease.root)),
            root_identity=list(self._lease.root_identity),
            arguments=execution.kernel._encode(a), request=asdict(request),
            execution_source_sha256=sha256(Path(execution.source.__file__).read_bytes()).hexdigest(),
            max_record_bytes=self._max_record_bytes, source_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
            lease_source_sha256=sha256(Path(local.__file__).read_bytes()).hexdigest(),
            sqlite_version=sqlite3.sqlite_version, python_version=platform.python_version(),
            formal_result=False, native_execution_authenticated=False))

    def _check(self):
        if self._closed:
            raise ValueError('normal store is closed')
        self._lease.check()
        if local._file_identity(self._database) != self._database_identity:
            raise ValueError('normal database identity changed')
        for suffix in ('-journal', '-wal', '-shm'):
            path = local._path(str(self._database)+suffix)
            if path.exists():
                local._file_identity(path)
                if suffix != '-journal':
                    raise ValueError('normal store requires DELETE journal mode')
        if self._current_header() != self._header:
            raise ValueError('normal journal source or implementation drift')

    def _connect(self):
        self._check()
        connection = sqlite3.connect(self._database.as_uri()+'?mode=rw', uri=True,
            timeout=0, isolation_level=None, check_same_thread=False)
        try:
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('PRAGMA synchronous=FULL')
            if (connection.execute('PRAGMA journal_mode').fetchone()[0] != 'delete'
                    or connection.execute('PRAGMA synchronous').fetchone()[0] != 2
                    or connection.execute('PRAGMA foreign_keys').fetchone()[0] != 1):
                raise ValueError('normal journal requires DELETE/FULL and foreign keys')
            return connection
        except BaseException:
            connection.close()
            raise

    def _initialize(self):
        connection = self._connect()
        try:
            connection.execute('BEGIN IMMEDIATE')
            for sql in TABLES:
                connection.execute(sql)
            connection.execute('PRAGMA user_version=1')
            connection.execute('PRAGMA application_id='+str(APPLICATION_ID))
            connection.execute('INSERT INTO metadata VALUES(1, ?)', (self._header,))
            connection.execute('COMMIT')
        finally:
            connection.close()

    def _rows(self, connection):
        if (connection.execute('PRAGMA integrity_check').fetchall() != [('ok',)]
                or connection.execute('PRAGMA foreign_key_check').fetchall()
                or connection.execute('PRAGMA user_version').fetchone()[0] != 1
                or connection.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID
                or set(r[0] for r in connection.execute('SELECT sql FROM sqlite_master WHERE sql IS NOT NULL')) != set(TABLES)
                or connection.execute('SELECT id, header FROM metadata').fetchall() != [(1, self._header)]):
            raise ValueError('normal journal metadata/schema/integrity mismatch')
        intents = connection.execute('SELECT id, payload FROM intent').fetchall()
        results = connection.execute('SELECT id, payload, digest FROM result').fetchall()
        if intents not in ([], [(1, self._intent)]) or len(results) > 1 or (results and not intents):
            raise ValueError('normal invocation inventory mismatch')
        if results:
            index, raw, digest = results[0]
            if index != 1 or len(raw) > self._max_record_bytes or sha256(raw).hexdigest() != digest:
                raise ValueError('normal result size/digest mismatch')
            record = _decoded(raw)
            if (set(record) != {'schema', 'store_identity', 'declared_execution_identity', 'result_identity', 'encoded_result'}
                    or record['schema'] != SCHEMA or record['store_identity'] != self._identity
                    or record['declared_execution_identity'] != self._arguments['expected_declared_execution_identity']
                    or _result_identity(record['encoded_result']) != record['result_identity']):
                raise ValueError('normal archived result identity mismatch')
        return intents, results

    def _inspect(self):
        connection = self._connect()
        try:
            intents, results = self._rows(connection)
        finally:
            connection.close()
        digest = results[0][2] if results else None
        head = self._genesis if not results else sha256(_bytes([self._genesis, sha256(self._intent).hexdigest(), digest])).hexdigest()
        return DeclaredFastNormalStoreInspection(self._identity, self._genesis, head,
            'returned_record_unreplayed' if results else ('unresolved_intent' if intents else 'unused'),
            bool(intents), bool(results), _decoded(results[0][1])['result_identity'] if results else None, digest)

    def inspect(self):
        if not self._guard.acquire(blocking=False):
            raise ValueError('normal journal operation already in progress')
        try:
            return self._inspect()
        finally:
            self._guard.release()

    def _append(self, raw=None):
        connection = self._connect()
        try:
            connection.execute('BEGIN IMMEDIATE')
            intents, results = self._rows(connection)
            if raw is None:
                if intents or results:
                    raise ValueError('normal invocation already reserved')
                connection.execute('INSERT INTO intent VALUES(1, ?)', (self._intent,))
            else:
                if intents != [(1, self._intent)] or results:
                    raise ValueError('exact pending normal intent required')
                connection.execute('INSERT INTO result VALUES(1, ?, ?)', (raw, sha256(raw).hexdigest()))
            connection.execute('COMMIT')
        finally:
            connection.close()

    def execute(self, *, before_source=None):
        if before_source is not None and not callable(before_source):
            raise TypeError('before_source must be a callable runtime check')
        if not self._guard.acquire(blocking=False):
            raise ValueError('normal journal operation already in progress')
        try:
            if self._poisoned or self._inspect().intent_present:
                raise ValueError('reserved normal invocation cannot retry')
            self._poisoned = True
            self._append()
            if self._inspect().status != 'unresolved_intent':
                raise ValueError('normal intent readback failed before invocation')
            runtime = {} if before_source is None else dict(before_source=before_source)
            result = execution.run_declared_normal(self._request, **self._arguments, **runtime)
            if (type(result) is not execution.DeclaredFastStreamingNormalResult
                    or result.execution_identity != self._arguments['expected_declared_execution_identity']
                    or result.request_identity != self._arguments['expected_request_identity']):
                raise ValueError('owned normal result from reserved execution required')
            raw = _bytes(dict(schema=SCHEMA, store_identity=self._identity,
                declared_execution_identity=result.execution_identity, result_identity=result.identity,
                encoded_result=execution.kernel._encode(result)))
            if len(raw) > self._max_record_bytes:
                raise ValueError('complete normal result record exceeds byte budget; intent remains unresolved')
            self._append(raw)
            observed = self._inspect()
            if observed.archived_result_sha256 != sha256(raw).hexdigest():
                raise ValueError('normal result commit readback failed')
            return result, observed
        finally:
            self._guard.release()

    def close(self):
        if not self._guard.acquire(blocking=False):
            raise ValueError('cannot close normal store during an operation')
        try:
            if not self._closed:
                self._closed = True
                self._lease.close()
        finally:
            self._guard.release()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __copy__(self):
        raise TypeError('normal store owner cannot be copied')

    def __deepcopy__(self, memo):
        raise TypeError('normal store owner cannot be copied')

    def __reduce_ex__(self, protocol):
        raise TypeError('normal store owner cannot be pickled')
