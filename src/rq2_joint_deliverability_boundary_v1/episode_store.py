"""Local NTFS development journal with per-root exclusion and audited resume.

This is not a production lease or formal-run authority. An unresolved intent
is never retried, even if its process exited before starting native work.
"""
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import stat
from threading import Lock

from . import episode_replay as replay
from . import episode_coordinator as ep
from . import hourly_transaction as tx
from .prefix_handoff import _encoded


SCHEMA = 'rq2_local_ntfs_episode_journal_v1'
APPLICATION_ID = 0x45504731
TABLES = (
    'CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id=1), header BLOB NOT NULL) STRICT',
    'CREATE TABLE intents (seq INTEGER PRIMARY KEY, predecessor TEXT NOT NULL UNIQUE, payload BLOB NOT NULL, digest TEXT NOT NULL UNIQUE) STRICT',
    'CREATE TABLE results (seq INTEGER PRIMARY KEY REFERENCES intents(seq), archive BLOB NOT NULL, archive_digest TEXT NOT NULL, head TEXT NOT NULL UNIQUE) STRICT',
)
_REGISTRY = set()
_REGISTRY_LOCK = Lock()


def _implementation():
    if SCHEMA != 'rq2_local_ntfs_episode_journal_v1':
        raise ValueError('episode store schema drift')
    return tx._identity(SCHEMA, sha256(Path(__file__).read_bytes()).hexdigest(),
        replay._implementation(), sqlite3.sqlite_version, TABLES, APPLICATION_ID)


def _path(path):
    path = Path(os.path.abspath(path))
    for item in (path, *path.parents):
        if item.exists() or item.is_symlink():
            info = item.lstat()
            if info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise ValueError('reparse paths are not supported by the local store')
    if path.resolve() != path:
        raise ValueError('canonical local store path required')
    return path


def _local_ntfs(path):
    if os.name != 'nt':
        raise ValueError('development store currently requires local Windows NTFS')
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetDriveTypeW.argtypes = (wintypes.LPCWSTR,)
    kernel.GetDriveTypeW.restype = wintypes.UINT
    kernel.GetVolumeInformationW.argtypes = (wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
        wintypes.LPWSTR, wintypes.DWORD)
    kernel.GetVolumeInformationW.restype = wintypes.BOOL
    filesystem = ctypes.create_unicode_buffer(64)
    if (kernel.GetDriveTypeW(path.anchor) != 3
            or not kernel.GetVolumeInformationW(path.anchor, None, 0, None, None, None, filesystem, len(filesystem))
            or filesystem.value != 'NTFS'):
        raise ValueError('local fixed NTFS volume required')


def _file_identity(path):
    info = _path(path).stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError('regular single-link journal file required')
    return info.st_dev, info.st_ino


class _Lease:
    def __init__(self, root, create):
        _local_ntfs(Path(os.path.abspath(root)))
        self.root = _path(root)
        if not self.root.name.endswith('_non_authoritative'):
            raise ValueError('explicit non_authoritative store directory required')
        self.key = os.path.normcase(str(self.root))
        self.pid, self.stream, self.locked = os.getpid(), None, False
        with _REGISTRY_LOCK:
            if self.key in _REGISTRY:
                raise ValueError('episode store is already held in this process')
            _REGISTRY.add(self.key)
        try:
            if create:
                self.root.mkdir()
            if not self.root.is_dir():
                raise ValueError('existing episode directory required')
            info = self.root.stat()
            self.root_identity = info.st_dev, info.st_ino
            path = self.root/'execution.lock'
            _path(path)
            self.stream = path.open('x+b' if create else 'r+b', buffering=0)
            os.set_inheritable(self.stream.fileno(), False)
            if create:
                self.stream.write(b'0')
                os.fsync(self.stream.fileno())
            import msvcrt
            self.stream.seek(0)
            msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            self.locked = True
            if self.stream.read() != b'0':
                raise ValueError('invalid episode lock file')
            self.file_identity = _file_identity(path)
            self.check()
        except BaseException:
            self.close()
            raise

    def check(self):
        if self.pid != os.getpid() or self.stream is None or not self.locked:
            raise ValueError('live same-process store lease required')
        info = _path(self.root).stat()
        current = os.fstat(self.stream.fileno())
        if ((info.st_dev, info.st_ino) != self.root_identity
                or (current.st_dev, current.st_ino) != self.file_identity
                or _file_identity(self.root/'execution.lock') != self.file_identity):
            raise ValueError('episode store or lock identity changed')

    def close(self):
        try:
            if self.stream is not None:
                try:
                    if self.locked and self.pid == os.getpid():
                        import msvcrt
                        self.stream.seek(0)
                        msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
                finally:
                    self.stream.close()
        finally:
            self.stream, self.locked = None, False
            with _REGISTRY_LOCK:
                _REGISTRY.discard(self.key)


@dataclass(frozen=True)
class StoreInspection:
    store_identity: str
    head: str
    completed_attempts: int
    status: str
    pending_intent: bool
    archive_reproduced: bool
    development_continuation_available: bool
    formal_result: bool = False
    security_certified: bool = False
    formal_run_authorized: bool = False
    native_execution_authenticated: bool = False


def _header(root, common, arms, hours, config):
    if type(hours) is not tuple or len(hours) != config['budget'].planned_hours:
        raise ValueError('independent complete planned input window required')
    identity = replay.episode_replay_input_identity(common, arms, hours, **config)
    return dict(schema=SCHEMA, status='DRAFT_NONAUTHORITATIVE', root=os.path.normcase(str(root)),
        input_window_identity=identity, implementation_identity=_implementation(),
        genesis_identity=ep.EpisodeSession(common, arms, **config).snapshot.identity,
        formal_result=False, security_certified=False, formal_run_authorized=False)


def _intent(identity, sequence, head, before, h, config):
    replay._admit_hour(before, h)
    active = tuple(a for a in before.arms if not a.halted)
    calls, seconds = ep._requirements(len(h.info.network.units), active, config['solver_specification'])
    if (sequence > config['budget'].planned_hours
            or before.reserved_solver_calls+calls > config['budget'].max_reserved_solver_calls
            or before.reserved_solver_seconds+seconds > config['budget'].max_reserved_solver_seconds):
        raise ValueError('invocation exceeds admitted episode budget')
    return _encoded(dict(store_identity=identity, sequence=sequence, predecessor_head=head,
        predecessor_snapshot_identity=before.identity, hour_input=h,
        reserved_solver_calls=calls, reserved_solver_seconds=seconds))


class DevelopmentEpisodeStore:
    """Only explicit short-development inputs can enter this per-root owner."""
    def __init__(self, root, common, arms, hours, *, create=False, expected_head=None, **config):
        self._lease = _Lease(root, create)
        self._guard = Lock()
        self._poisoned, self._closed = False, False
        try:
            self._common, self._arms, self._hours, self._config = common, arms, hours, dict(config)
            self._header = _encoded(_header(self._lease.root, common, arms, hours, config))
            self._identity = sha256(self._header).hexdigest()
            self._genesis = tx._identity(SCHEMA, self._identity, 'genesis')
            self._database = self._lease.root/'journal.sqlite3'
            if create:
                with self._database.open('xb') as stream:
                    os.fsync(stream.fileno())
            self._database_identity = _file_identity(self._database)
            if create:
                self._initialize()
            self._session = ep.EpisodeSession(common, arms, **config)
            inspection, snapshot = self._audit()
            if expected_head is not None:
                replay.selectors.native._hash(expected_head)
                if inspection.head != expected_head:
                    raise ValueError('independently retained journal head mismatch')
            elif not create:
                raise ValueError('independently retained journal head required for continuation')
            if inspection.pending_intent or not inspection.archive_reproduced:
                raise ValueError('unresolved journal boundary cannot resume or retry')
            self._session._snapshot = snapshot
            self._inspection = inspection
        except BaseException:
            self._lease.close()
            raise

    def __copy__(self):
        raise TypeError('episode store owner cannot be copied')

    def __deepcopy__(self, memo):
        raise TypeError('episode store owner cannot be copied')

    def __reduce_ex__(self, protocol):
        raise TypeError('episode store owner cannot be pickled')

    def _check(self):
        self._lease.check()
        if _file_identity(self._database) != self._database_identity:
            raise ValueError('episode database identity changed')
        for suffix in ('-journal', '-wal', '-shm'):
            sidecar = _path(str(self._database)+suffix)
            if sidecar.exists():
                _file_identity(sidecar)
                if suffix != '-journal':
                    raise ValueError('WAL sidecars are outside the DELETE journal contract')
        if self._header != _encoded(_header(self._lease.root, self._common, self._arms, self._hours, self._config)):
            raise ValueError('episode source or implementation changed')

    def _connect(self):
        self._check()
        connection = sqlite3.connect(self._database.as_uri()+'?mode=rw', uri=True,
            timeout=0, isolation_level=None, check_same_thread=False)
        try:
            connection.execute('PRAGMA busy_timeout=0')
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('PRAGMA synchronous=FULL')
            mode = connection.execute('PRAGMA journal_mode').fetchone()[0]
            if mode != 'delete' or connection.execute('PRAGMA synchronous').fetchone()[0] != 2:
                raise ValueError('DELETE/FULL SQLite journal contract required')
            if connection.execute('PRAGMA foreign_keys').fetchone()[0] != 1:
                raise ValueError('SQLite foreign keys required')
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
            connection.execute('INSERT INTO metadata VALUES (1, ?)', (self._header,))
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
            raise ValueError('journal schema, integrity or header mismatch')
        intents = connection.execute('SELECT seq, predecessor, payload, digest FROM intents ORDER BY seq').fetchall()
        results = connection.execute('SELECT seq, archive, archive_digest, head FROM results ORDER BY seq').fetchall()
        return intents, results

    def _read(self):
        connection = self._connect()
        try:
            connection.execute('BEGIN IMMEDIATE')
            rows = self._rows(connection)
            connection.execute('COMMIT')
        finally:
            connection.close()
        self._check()
        return rows

    def _audit(self):
        intents, results = self._read()
        if (len(intents) > len(self._hours) or len(results) not in (len(intents), len(intents)-1)
                or tuple(r[0] for r in intents) != tuple(range(1, len(intents)+1))
                or tuple(r[0] for r in results) != tuple(range(1, len(results)+1))):
            raise ValueError('journal must be a unique contiguous invocation prefix')
        before = ep.EpisodeSession(self._common, self._arms, **self._config).snapshot
        head, reproduced, pending = self._genesis, True, False
        for index, row in enumerate(intents):
            intent = _intent(self._identity, index+1, head, before, self._hours[index], self._config)
            if row != (index+1, head, intent, sha256(intent).hexdigest()):
                raise ValueError('journal intent differs from independent input or predecessor')
            if index == len(results):
                pending = True
                break
            seq, archive, digest, saved_head = results[index]
            if type(archive) is not bytes or sha256(archive).hexdigest() != digest:
                raise ValueError('journal archive digest mismatch')
            next_head = tx._identity(self._identity, head, row[3], digest)
            if saved_head != next_head:
                raise ValueError('journal commit hash chain mismatch')
            prefix = self._hours[:index+1]
            report, snapshot = replay._verify(archive, self._common, self._arms, prefix,
                expected_sha256=digest,
                expected_input_identity=replay.episode_replay_input_identity(self._common, self._arms, prefix, **self._config),
                **self._config)
            saved = json.loads(archive)['snapshot']
            replay._same(before.attempts, saved['attempts'][:-1], 'journal committed history')
            replay._same(before.identity, saved['attempts'][-1]['before_identity'], 'journal result predecessor')
            head = next_head
            if not report.archive_reproduced:
                if index != len(intents)-1:
                    raise ValueError('partial archive cannot authorize a journal suffix')
                reproduced = False
                before = None
                break
            before = snapshot
        status = ('unresolved_intent' if pending else 'partial_episode_evidence' if not reproduced else before.status)
        inspection = StoreInspection(self._identity, head, len(results), status, pending, reproduced,
            not pending and reproduced and not before.halted)
        return inspection, before

    @property
    def inspection(self):
        return self._inspection

    def _append(self, intent, sequence, head, archive=None):
        connection = self._connect()
        try:
            connection.execute('BEGIN IMMEDIATE')
            intents, results = self._rows(connection)
            if (results[-1][3] if results else self._genesis) != head:
                raise ValueError('journal predecessor head changed before append')
            if archive is None:
                if len(intents) != sequence-1 or len(results) != sequence-1:
                    raise ValueError('journal intent already exists or predecessor incomplete')
                connection.execute('INSERT INTO intents VALUES (?, ?, ?, ?)',
                    (sequence, head, intent, sha256(intent).hexdigest()))
            else:
                if (len(intents) != sequence or len(results) != sequence-1
                        or intents[-1] != (sequence, head, intent, sha256(intent).hexdigest())):
                    raise ValueError('result requires the exact unique pending intent')
                digest = sha256(archive).hexdigest()
                new_head = tx._identity(self._identity, head, sha256(intent).hexdigest(), digest)
                connection.execute('INSERT INTO results VALUES (?, ?, ?, ?)', (sequence, archive, digest, new_head))
            connection.execute('COMMIT')
        finally:
            connection.close()

    def advance(self):
        if not self._guard.acquire(blocking=False):
            raise ValueError('episode store operation already in progress')
        try:
            if self._closed or self._poisoned:
                raise ValueError('closed or indeterminate store cannot execute')
            self._check()
            current, audited = self._audit()
            if current != self._inspection or not current.development_continuation_available:
                raise ValueError('journal changed or does not permit development continuation')
            if audited.identity != self._session.snapshot.identity:
                raise ValueError('in-memory state differs from committed source-bound replay')
            sequence = len(audited.attempts)+1
            h = self._hours[sequence-1]
            intent = _intent(self._identity, sequence, current.head, audited, h, self._config)
            # From here every failure poisons this owner. Fresh inspection may
            # reconcile a committed result; a bare intent never permits retry.
            self._poisoned = True
            self._append(intent, sequence, current.head)
            intents, results = self._read()
            if (len(intents) != sequence or len(results) != sequence-1
                    or intents[-1] != (sequence, current.head, intent, sha256(intent).hexdigest())):
                raise ValueError('durable intent readback failed before invocation')
            try:
                self._session.advance(h.info, h.disclosure, h.source_hour, h.source_audit,
                    limits=h.limits, due_hour=h.due_hour, available_flexibility=h.available_flexibility)
            except BaseException:
                self._publish_result(intent, sequence, current.head)
                raise
            self._publish_result(intent, sequence, current.head)
            return self._inspection
        finally:
            self._guard.release()

    def _publish_result(self, intent, sequence, head):
        prefix = self._hours[:sequence]
        if len(self._session.snapshot.attempts) != sequence:
            raise ValueError('invocation did not produce a complete attempt record')
        replay._same(prefix[-1], self._session.snapshot.attempts[-1].hour_input, 'result current invocation input')
        archive = replay.export_episode_archive(self._session.snapshot,
            input_identity=replay.episode_replay_input_identity(self._common, self._arms, prefix, **self._config))
        self._append(intent, sequence, head, archive)
        inspection, snapshot = self._audit()
        if inspection.completed_attempts != sequence:
            raise ValueError('result commit readback incomplete')
        self._inspection = inspection
        self._poisoned = not inspection.archive_reproduced or inspection.pending_intent
        if snapshot is not None:
            self._session._snapshot = snapshot

    def close(self):
        if not self._guard.acquire(blocking=False):
            raise ValueError('cannot close store during an invocation')
        try:
            if not self._closed:
                self._closed = True
                self._lease.close()
        finally:
            self._guard.release()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def inspect_episode_store(root, common, arms, hours, **config):
    """Journal reconciliation; no business/solver execution or state returned."""
    lease = _Lease(root, False)
    try:
        owner = object.__new__(DevelopmentEpisodeStore)
        owner._lease = lease
        owner._common, owner._arms, owner._hours, owner._config = common, arms, hours, dict(config)
        owner._header = _encoded(_header(lease.root, common, arms, hours, config))
        owner._identity = sha256(owner._header).hexdigest()
        owner._genesis = tx._identity(SCHEMA, owner._identity, 'genesis')
        owner._database = lease.root/'journal.sqlite3'
        owner._database_identity = _file_identity(owner._database)
        return owner._audit()[0]
    finally:
        lease.close()
