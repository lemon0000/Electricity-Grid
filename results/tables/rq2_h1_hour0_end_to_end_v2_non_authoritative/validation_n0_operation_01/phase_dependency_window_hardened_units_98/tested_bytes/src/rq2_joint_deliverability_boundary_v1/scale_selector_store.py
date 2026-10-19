"""One-shot selector journal using the existing cooperative local NTFS lease.

An outer intent reserves every stage before any numerical work. No per-stage
checkpoint or executable resume is provided. Pending means unknown, never zero.
"""
from copy import deepcopy
from dataclasses import dataclass, fields
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
from threading import Lock

from . import episode_store as local, scale_selector as selector
from . import continuous_grid_normal as codec
from .continuous_grid_normal import _encode

SCHEMA = 'draft_one_shot_scale_selector_store_v1'
APPLICATION_ID = 0x53534331
TABLES = (
    'CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id=1), payload BLOB NOT NULL) STRICT',
    'CREATE TABLE intent (id INTEGER PRIMARY KEY CHECK(id=1), payload BLOB NOT NULL) STRICT',
    'CREATE TABLE result (id INTEGER PRIMARY KEY CHECK(id=1) REFERENCES intent(id), payload BLOB NOT NULL, digest TEXT NOT NULL) STRICT',
)


@dataclass(frozen=True)
class SelectorRequest:
    info: object
    disclosure: object
    before: object
    expected_identity: str
    selection_spec: object
    solver_specification: object
    budget: selector.ScaleSelectorBudget
    expected_policy_identity: str
    power: object = None


def _bytes(item):
    return json.dumps(item, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def _decoded(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate journal key')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs)
    if _bytes(value) != raw:
        raise ValueError('canonical journal bytes required')
    return value


def _positive(value):
    if type(value) is not int or value <= 0:
        raise ValueError('explicit positive record byte limit required')


def _fields(wire, cls):
    if type(wire) is not list or len(wire) != 2 or wire[0] != cls.__name__ or type(wire[1]) is not list:
        raise ValueError('typed encoded journal record required')
    pairs = wire[1]
    if any(type(p) is not list or len(p) != 2 or type(p[0]) is not str for p in pairs):
        raise ValueError('invalid encoded fields')
    result = dict(pairs)
    if len(result) != len(pairs) or set(result) != {f.name for f in fields(cls)}:
        raise ValueError('exact unique encoded field inventory required')
    return result


def _validate_record(record, header, binding):
    if set(record) != {'schema', 'binding_identity', 'encoded_result', 'result_identity'}:
        raise ValueError('exact result record required')
    if record['binding_identity'] != binding or record['schema'] != SCHEMA:
        raise ValueError('returned record belongs to another invocation')
    wire = record['encoded_result']
    expected = sha256(json.dumps(['tuple', [wire]], ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    if record['result_identity'] != expected:
        raise ValueError('encoded result identity mismatch')
    result = _fields(wire, selector.ScaleSelectionResult)
    request = _fields(header['request'], SelectorRequest)
    for key, source in (('input_identity', 'expected_identity'), ('policy_identity', 'expected_policy_identity'),
                        ('budget', 'budget'), ('selector', 'selection_spec'), ('specification', 'solver_specification')):
        if result[key] != request[source]:
            raise ValueError('returned result request binding mismatch: '+key)
    planned = len(header['planned_stages'])
    known, calls = result['completed_solver_calls'], result['solver_calls']
    if (type(result['planned_solver_calls']) is not int or result['planned_solver_calls'] != planned
            or type(known) is not int or not 0 <= known <= planned
            or (calls is not None and (type(calls) is not int or calls != known))):
        raise ValueError('invalid returned call accounting')
    if result['contract'] != selector.CONTRACT or any(result[name] is not False for name in (
            'durable_invocation_tracking', 'hard_resource_limits_enforced', 'formal_result', 'security_certified')):
        raise ValueError('unexpected selector authority flags')
    return result


def _connect(path, readonly=False):
    db = sqlite3.connect(path.as_uri()+('?mode=ro&immutable=1' if readonly else '?mode=rw'), uri=True, timeout=0)
    try:
        db.execute('PRAGMA foreign_keys=ON')
        if not readonly:
            if db.execute('PRAGMA journal_mode=DELETE').fetchone()[0] != 'delete':
                raise ValueError('DELETE journal required')
            db.execute('PRAGMA synchronous=FULL')
        return db
    except BaseException:
        db.close()
        raise


def _read(path, binding_identity, max_record_bytes):
    selector.actual._hash(binding_identity)
    _positive(max_record_bytes)
    db = _connect(path, True)
    try:
        if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise ValueError('journal integrity failure')
        if db.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID:
            raise ValueError('wrong selector journal application')
        definitions = db.execute("SELECT sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
        if len(definitions) != 3 or {row[0] for row in definitions} != set(TABLES):
            raise ValueError('unexpected journal schema')
        heads = db.execute('SELECT id,payload FROM metadata').fetchall()
        intents = db.execute('SELECT id,payload FROM intent').fetchall()
        rows = db.execute('SELECT id,length(payload),digest FROM result').fetchall()
        if len(heads) != 1 or heads[0][0] != 1 or sha256(heads[0][1]).hexdigest() != binding_identity:
            raise ValueError('external journal binding mismatch')
        header = _decoded(heads[0][1])
        if header['schema'] != SCHEMA or header['max_record_bytes'] != max_record_bytes:
            raise ValueError('journal declaration mismatch')
        root_stat = path.parent.stat()
        if header['root'] != str(path.parent) or header['root_identity'] != [root_stat.st_dev, root_stat.st_ino]:
            raise ValueError('selector journal root identity mismatch')
        expected_intent = _bytes(dict(schema=SCHEMA, binding_identity=binding_identity,
                                     planned_stages=header['planned_stages']))
        if intents not in ([], [(1, expected_intent)]):
            raise ValueError('unexpected invocation intent')
        record = reported = None
        if rows:
            if not intents or len(rows) != 1 or rows[0][0] != 1 or not 0 < rows[0][1] <= max_record_bytes:
                raise ValueError('invalid bounded result inventory')
            raw = db.execute('SELECT payload FROM result WHERE id=1').fetchone()[0]
            if sha256(raw).hexdigest() != rows[0][2]:
                raise ValueError('result digest mismatch')
            record = _decoded(raw)
            reported = _validate_record(record, header, binding_identity)
        return dict(binding_identity=binding_identity,
                    status='returned_unverified' if rows else 'pending_unknown' if intents else 'unused',
                    intent_present=bool(intents), result_present=bool(rows),
                    planned_solver_calls=len(header['planned_stages']),
                    reserved_solver_seconds=header['reserved_solver_seconds'],
                    charged_solver_calls=len(header['planned_stages']) if intents else 0,
                    charged_solver_seconds=header['reserved_solver_seconds'] if intents else 0,
                    reported_solver_calls=None if reported is None else reported['solver_calls'],
                    reported_completed_solver_calls=None if reported is None else reported['completed_solver_calls'],
                    actual_solver_calls_verified=False, numerical_evidence_replayed=False,
                    native_execution_authenticated=False, executable_resume_available=False,
                    formal_result=False), record
    finally:
        db.close()


class DevelopmentScaleSelectorStore:
    def __init__(self, root, request, *, max_record_bytes):
        if type(request) is not SelectorRequest:
            raise ValueError('typed selector request required')
        _positive(max_record_bytes)
        self._request = deepcopy(request)
        self._limit = max_record_bytes
        self._guard = Lock()
        self._closed = self._poisoned = False
        self._lease = local._Lease(root, True)
        try:
            self._header = self._current_header()
            self.binding_identity = sha256(self._header).hexdigest()
            self._path = self._lease.root/'selector.sqlite3'
            with self._path.open('xb') as stream:
                os.fsync(stream.fileno())
            self._file_identity = local._file_identity(self._path)
            db = _connect(self._path)
            try:
                with db:
                    db.execute(f'PRAGMA application_id={APPLICATION_ID}')
                    for sql in TABLES:
                        db.execute(sql)
                    db.execute('INSERT INTO metadata VALUES(1,?)', (self._header,))
            finally:
                db.close()
            self._check()
            self.inspection()
        except BaseException:
            self._lease.close()
            raise

    def _current_header(self):
        request = self._request
        selector.actual._hash(request.expected_identity)
        selector.actual._hash(request.expected_policy_identity)
        module = selector._admit(request.selection_spec, request.solver_specification,
                                  request.budget, request.budget.max_solver_calls)
        if selector.policy_identity(request.selection_spec, request.solver_specification, request.budget) != request.expected_policy_identity:
            raise ValueError('selector policy identity changed')
        uids = request.budget.generator_uids
        labels = (('grid_request', 'l1_normal_deviation') if module is selector.reference else ('l1_normal_deviation',))
        labels += tuple('generation:'+uid for uid in uids)
        if len(labels) != request.budget.max_solver_calls:
            raise ValueError('intent must reserve the complete stage inventory')
        return _bytes(dict(schema=SCHEMA, request=_encode(request), planned_stages=labels,
            reserved_solver_seconds=request.budget.max_total_solver_seconds,
            max_record_bytes=self._limit, root=str(self._lease.root), root_identity=self._lease.root_identity,
            implementation=tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest())
                                 for m in (selector, local, codec)),
            store_sha256=sha256(Path(__file__).read_bytes()).hexdigest(), sqlite_version=sqlite3.sqlite_version))

    def _check(self):
        if self._closed:
            raise ValueError('selector store is closed')
        self._lease.check()
        if local._file_identity(self._path) != self._file_identity or self._current_header() != self._header:
            raise ValueError('selector store source, request or file drift')

    def inspection(self):
        if not self._guard.acquire(False):
            raise ValueError('cannot inspect an active selector invocation')
        try:
            self._check()
            report = _read(self._path, self.binding_identity, self._limit)[0]
            self._check()
            return report
        finally:
            self._guard.release()

    def _append(self, result=None):
        self._check()
        state, _ = _read(self._path, self.binding_identity, self._limit)
        if state['status'] != ('unused' if result is None else 'pending_unknown'):
            raise ValueError('one-shot selector invocation already consumed')
        header = _decoded(self._header)
        payload = (_bytes(dict(schema=SCHEMA, binding_identity=self.binding_identity,
                                planned_stages=header['planned_stages'])) if result is None else
                   _bytes(dict(schema=SCHEMA, binding_identity=self.binding_identity,
                               encoded_result=_encode(result), result_identity=result.identity)))
        if result is not None and len(payload) > self._limit:
            raise ValueError('complete selector result exceeds declared record limit')
        if result is not None:
            _validate_record(_decoded(payload), header, self.binding_identity)
        db = _connect(self._path)
        try:
            with db:
                db.execute('INSERT INTO intent VALUES(1,?)', (payload,)) if result is None else db.execute(
                    'INSERT INTO result VALUES(1,?,?)', (payload, sha256(payload).hexdigest()))
        finally:
            db.close()
        self._check()
        observed, returned = _read(self._path, self.binding_identity, self._limit)
        expected_status = 'pending_unknown' if result is None else 'returned_unverified'
        if observed['status'] != expected_status or (result is not None and _bytes(returned) != payload):
            raise ValueError('committed selector record readback mismatch')
        self._check()

    def execute(self):
        if not self._guard.acquire(False):
            raise ValueError('selector invocation is already active')
        try:
            if self._poisoned:
                raise ValueError('interrupted selector store cannot retry')
            self._append()
            request = self._request
            result = selector.select_hour(request.info, request.disclosure, request.before,
                expected_identity=request.expected_identity, selector=request.selection_spec,
                solver_specification=request.solver_specification, budget=request.budget,
                expected_policy_identity=request.expected_policy_identity, power=request.power)
            if type(result) is not selector.ScaleSelectionResult:
                raise ValueError('owned scale selector result required')
            self._append(result)
            return result
        except BaseException:
            self._poisoned = True
            raise
        finally:
            self._guard.release()

    def close(self):
        if not self._guard.acquire(False):
            raise ValueError('cannot close an active selector invocation')
        try:
            if not self._closed:
                self._lease.close()
                self._closed = True
        finally:
            self._guard.release()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __copy__(self):
        raise TypeError('selector store cannot be copied')

    def __deepcopy__(self, memo):
        raise TypeError('selector store cannot be copied')

    def __reduce_ex__(self, protocol):
        raise TypeError('selector store cannot be serialized')


def inspect_scale_selector_store(root, *, expected_binding_identity, max_record_bytes):
    lease = local._Lease(root, False)
    try:
        path = lease.root/'selector.sqlite3'
        before = local._file_identity(path)
        report, _ = _read(path, expected_binding_identity, max_record_bytes)
        lease.check()
        if local._file_identity(path) != before:
            raise ValueError('selector journal changed during inspection')
        return report
    finally:
        lease.close()
