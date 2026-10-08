"""Bounded opaque normal archive capture for a controller after Job quiescence.

The result identity is a claim for the independent replayer, not checked here.
No assembly, encoded assignment, or executable owner is reconstructed.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
import os
from pathlib import Path
import sqlite3
import time

from . import normal_declared_store_stream_numeric as journal, normal_archive_capture as legacy


HEADER_LIMIT = 1024**2
CHUNK_BYTES = 64*1024
SCHEMA = 'draft_numeric_streaming_declared_normal_opaque_archive_capture_v1'


ArchiveCaptureBudget = legacy.ArchiveCaptureBudget


@dataclass(frozen=True)
class NumericStreamingNormalArchivePins:
    capture_identity: str
    store_identity: str
    genesis: str
    head: str
    status: str
    intent_present: bool
    record_sha256: str | None
    record_bytes: int
    claimed_result_identity: str | None
    result_identity_verified: bool = False
    numerical_evidence_replayed: bool = False
    native_execution_authenticated: bool = False
    whole_job_quiescence_verified: bool = False
    formal_result: bool = False


def capture_identity(root, *, budget, expected_store_identity, expected_declared_execution_identity,
                     claimed_result_identity):
    if type(budget) is not ArchiveCaptureBudget:
        raise ValueError('typed archive capture budget required')
    budget.__post_init__()
    for pin in (expected_store_identity, expected_declared_execution_identity):
        journal.execution.kernel._pin(pin)
    if claimed_result_identity is not None:
        journal.execution.kernel._pin(claimed_result_identity)
    path = journal.local._path(root)
    return sha256(journal._bytes((SCHEMA, str(path), asdict(budget), expected_store_identity,
        expected_declared_execution_identity, claimed_result_identity, sqlite3.sqlite_version,
        tuple((str(Path(module.__file__).resolve()), sha256(Path(module.__file__).read_bytes()).hexdigest())
              for module in (journal, journal.local, journal.execution.kernel, legacy)),
        sha256(Path(__file__).read_bytes()).hexdigest()))).hexdigest()


def capture_normal_archive(root, *, budget, expected_store_identity, expected_declared_execution_identity,
                           claimed_result_identity, expected_capture_identity):
    """Read under the existing cooperative lease; never writes or retries a task.

    Caller must establish whole-Job quiescence before calling. The supplied
    result identity remains an opaque claim until replay_normal_store checks it.
    """
    started = time.monotonic()
    arguments = dict(budget=budget, expected_store_identity=expected_store_identity,
        expected_declared_execution_identity=expected_declared_execution_identity,
        claimed_result_identity=claimed_result_identity)
    if capture_identity(root, **arguments) != expected_capture_identity:
        raise ValueError('archive capture request/implementation mismatch')

    def deadline():
        if time.monotonic()-started >= budget.max_elapsed_seconds:
            raise TimeoutError('archive capture deadline reached')

    lease = object.__new__(journal.local._Lease)
    connection = None
    try:
        # The reused lease reads its lock marker as a whole. Bound that file
        # before entering it; cooperative writers never alter the marker.
        lock_path = journal.local._path(root)/'execution.lock'
        lock_identity = journal.local._file_identity(lock_path)
        if lock_path.stat().st_size != 1:
            raise ValueError('one-byte normal archive lock marker required')
        journal.local._Lease.__init__(lease, root, False)
        if lease.file_identity != lock_identity:
            raise ValueError('normal archive lock replaced during acquisition')
        database = lease.root/'normal.sqlite3'
        original_file = journal.local._file_identity(database)
        original_stat = database.stat()

        def check_files():
            deadline()
            lease.check()
            if journal.local._file_identity(database) != original_file:
                raise ValueError('normal archive database identity changed')
            current_stat = database.stat()
            if not 0 < current_stat.st_size <= budget.max_database_bytes:
                raise ValueError('normal archive database byte budget exceeded')
            if (current_stat.st_size, current_stat.st_mtime_ns) != (original_stat.st_size, original_stat.st_mtime_ns):
                raise ValueError('normal archive database changed during capture')
            # A read-only capture does not attempt crash recovery or consume
            # uncommitted state. The task remains unresolved if cleanup is needed.
            for suffix in ('-journal', '-wal', '-shm'):
                sidecar = journal.local._path(str(database)+suffix)
                if sidecar.exists() or sidecar.is_symlink():
                    raise ValueError('normal archive sidecar requires unresolved reconciliation')

        check_files()
        connection = sqlite3.connect(database.as_uri()+'?mode=ro', uri=True, timeout=0, isolation_level=None)
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, HEADER_LIMIT)
        connection.set_progress_handler(lambda: int(time.monotonic()-started >= budget.max_elapsed_seconds), 1000)
        connection.execute('PRAGMA query_only=ON')
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA trusted_schema=OFF')
        connection.execute('PRAGMA temp_store=MEMORY')
        connection.execute('PRAGMA cache_size=-1024')
        connection.execute('PRAGMA mmap_size=0')
        connection.execute('BEGIN')
        if (connection.execute('PRAGMA journal_mode').fetchone() != ('delete',)
                or connection.execute('PRAGMA application_id').fetchone() != (journal.APPLICATION_ID,)
                or connection.execute('PRAGMA user_version').fetchone() != (1,)
                or connection.execute('PRAGMA foreign_keys').fetchone() != (1,)
                or connection.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY name LIMIT 4').fetchall()
                    != sorted(('table', name, name, sql) for name, sql in zip(
                        ('metadata', 'intent', 'result'), journal.TABLES))):
            raise ValueError('normal archive schema mismatch')
        for query in ('PRAGMA integrity_check(1)', 'PRAGMA foreign_key_check'):
            rows = connection.execute(query).fetchmany(2)
            if rows != ([('ok',)] if 'integrity' in query else []):
                raise ValueError('normal archive integrity mismatch')
        def blocks(table, column, size):
            with connection.blobopen(table, column, 1, readonly=True) as blob:
                if len(blob) != size:
                    raise ValueError('normal archive blob length changed')
                remaining = size
                while remaining:
                    deadline()
                    block = blob.read(min(CHUNK_BYTES, remaining))
                    deadline()
                    if not block:
                        raise ValueError('normal archive truncated blob')
                    remaining -= len(block)
                    yield block

        metadata = connection.execute('SELECT id, length(header), typeof(header) FROM metadata LIMIT 2').fetchall()
        if (len(metadata) != 1 or metadata[0][0] != 1
                or metadata[0][2] != 'blob' or not 0 < metadata[0][1] <= HEADER_LIMIT):
            raise ValueError('bounded normal archive metadata required')
        header = b''.join(blocks('metadata', 'header', metadata[0][1]))
        if sha256(header).hexdigest() != expected_store_identity:
            raise ValueError('normal archive store identity mismatch')
        decoded = journal._decoded(header)
        arguments_wire = decoded.get('arguments')
        if (type(arguments_wire) is not list or len(arguments_wire) != 2 or arguments_wire[0] != 'mapping'
                or type(arguments_wire[1]) is not list
                or any(type(row) is not list or len(row) != 2 or type(row[0]) is not str
                    for row in arguments_wire[1])
                or len({row[0] for row in arguments_wire[1]}) != len(arguments_wire[1])
                or dict(arguments_wire[1]).get('expected_declared_execution_identity') != expected_declared_execution_identity):
            raise ValueError('normal archive header declared execution pin mismatch')
        if (decoded.get('schema') != journal.SCHEMA
                or decoded.get('root') != os.path.normcase(str(lease.root))
                or decoded.get('root_identity') != list(lease.root_identity)
                or decoded.get('formal_result') is not False
                or decoded.get('native_execution_authenticated') is not False
                or decoded.get('max_record_bytes') != budget.max_record_bytes):
            raise ValueError('normal archive header binding mismatch')
        genesis = sha256(journal._bytes([journal.SCHEMA, expected_store_identity, 'genesis'])).hexdigest()
        intent = journal._bytes(dict(schema=journal.SCHEMA, store_identity=expected_store_identity,
            predecessor=genesis, declared_execution_identity=expected_declared_execution_identity))
        inventory = connection.execute('SELECT id, length(payload), typeof(payload) FROM intent LIMIT 2').fetchall()
        if inventory not in ([], [(1, len(intent), 'blob')]):
            raise ValueError('normal archive intent inventory mismatch')
        if inventory and b''.join(blocks('intent', 'payload', len(intent))) != intent:
            raise ValueError('normal archive intent mismatch')
        records = connection.execute('SELECT id, length(payload), length(digest), typeof(payload), typeof(digest) '
            'FROM result LIMIT 2').fetchall()
        digest, size, head = None, 0, genesis
        if records:
            if (not inventory or len(records) != 1 or records[0][0] != 1
                    or not 0 < records[0][1] <= budget.max_record_bytes or records[0][2] != 64
                    or records[0][3:] != ('blob', 'text')
                    or claimed_result_identity is None):
                raise ValueError('bounded complete normal archive and result claim required')
            size = records[0][1]
            recorded_digest = connection.execute('SELECT digest FROM result WHERE id=1').fetchone()[0]
            journal.execution.kernel._pin(recorded_digest)
            hasher = sha256()
            connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, max(HEADER_LIMIT, budget.max_record_bytes+1024))
            for block in blocks('result', 'payload', size):
                hasher.update(block)
            digest = hasher.hexdigest()
            if digest != recorded_digest:
                raise ValueError('normal archive record digest mismatch')
            head = sha256(journal._bytes([genesis, sha256(intent).hexdigest(), digest])).hexdigest()
        elif claimed_result_identity is not None:
            raise ValueError('normal archive result claim has no record')
        check_files()
        if capture_identity(root, **arguments) != expected_capture_identity:
            raise ValueError('archive capture implementation drift')
        deadline()
        return NumericStreamingNormalArchivePins(expected_capture_identity, expected_store_identity, genesis, head,
            'opaque_record_captured' if records else ('unresolved_intent' if inventory else 'unused'),
            bool(inventory), digest, size, claimed_result_identity)
    finally:
        try:
            if connection is not None:
                connection.close()
        finally:
            if getattr(lease, 'stream', None) is not None:
                lease.close()
