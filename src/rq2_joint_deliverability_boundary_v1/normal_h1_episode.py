"""Short normal-only episode owner with durable intent and exact prefix replay.

Inputs are caller-declared observations, not authenticated data-set observations.
This development owner neither restores nor advances reference/actual state.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime, timedelta
from fractions import Fraction
from hashlib import sha256
import json
from math import isfinite
import os
from pathlib import Path
import sqlite3
from threading import Lock

from ..grid.rts_gmlc import RtsGmlcHourlyPoint
from . import normal_h1_projection_store as journal


replay = journal.replay
current = replay.current
source = current.source
SCHEMA = 'h1_normal_episode_intent_outcome_development_v1'
APPLICATION_ID = 0x48453131
TABLES = (
    'CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id=1), header BLOB NOT NULL) STRICT',
    'CREATE TABLE events (seq INTEGER PRIMARY KEY, predecessor TEXT NOT NULL, request_key TEXT NOT NULL, archive_sha256 TEXT NOT NULL, archive BLOB NOT NULL, head TEXT NOT NULL UNIQUE) STRICT',
)
MAX_METADATA_BYTES = 256 * 1024
TEXT_PREFIX_BYTES = 1024
FRAME = b'H1EP1\x00'


def _head(seq, before, key, pin):
    return sha256(journal._bytes([SCHEMA, seq, before, key, pin])).hexdigest()


def _descriptor(raw):
    return dict(length=len(raw), sha256=sha256(raw).hexdigest())


def _text(raw):
    return dict(**_descriptor(raw), prefix_hex=raw[:TEXT_PREFIX_BYTES].hex(),
                complete=len(raw) <= TEXT_PREFIX_BYTES)


def _encode_event(item):
    """Separate binary evidence from bounded canonical metadata; no JSON expansion."""
    blobs = []
    def encode(value):
        if type(value) is bytes:
            index = len(blobs)
            blobs.append(value)
            return dict(blob=index, **_descriptor(value))
        if type(value) is dict:
            return {key: encode(value[key]) for key in sorted(value)}
        if type(value) in (list, tuple):
            return [encode(v) for v in value]
        return value
    metadata = journal._bytes(encode(item))
    if len(metadata) > MAX_METADATA_BYTES:
        raise ValueError('H1 episode metadata byte budget exceeded')
    return FRAME + len(metadata).to_bytes(8, 'big') + metadata + b''.join(blobs)


def _decode_event(raw):
    if type(raw) is not bytes or raw[:len(FRAME)] != FRAME:
        raise ValueError('H1 episode binary frame required')
    start = len(FRAME)+8
    size = int.from_bytes(raw[len(FRAME):start], 'big')
    if not 0 < size <= MAX_METADATA_BYTES or start+size > len(raw):
        raise ValueError('H1 episode metadata size mismatch')
    metadata = replay._decode(raw[start:start+size], MAX_METADATA_BYTES)
    offset, index = start+size, 0
    def decode(value):
        nonlocal offset, index
        if type(value) is dict and 'blob' in value:
            if (set(value) != {'blob','length','sha256'} or type(value['blob']) is not int
                    or value['blob'] != index or type(value['length']) is not int or value['length'] < 0):
                raise ValueError('H1 episode binary descriptor mismatch')
            blob = raw[offset:offset+value['length']]
            if _descriptor(blob) != {k:value[k] for k in ('length','sha256')}:
                raise ValueError('H1 episode binary evidence mismatch')
            offset += len(blob)
            index += 1
            return blob
        if type(value) is dict:
            return {k:decode(v) for k,v in value.items()}
        if type(value) is list:
            return [decode(v) for v in value]
        return value
    result = decode(metadata)
    if offset != len(raw) or _encode_event(result) != raw:
        raise ValueError('H1 episode noncanonical or trailing binary evidence')
    return result


@dataclass(frozen=True)
class H1EpisodeBudget:
    planned_hours: int
    max_reserved_solver_calls: int
    max_reserved_solver_seconds: float

    def __post_init__(self):
        if (type(self.planned_hours) is not int or not 1 <= self.planned_hours <= 24
                or type(self.max_reserved_solver_calls) is not int or not 1 <= self.max_reserved_solver_calls <= 20
                or type(self.max_reserved_solver_seconds) is not float
                or not isfinite(self.max_reserved_solver_seconds) or not 0 < self.max_reserved_solver_seconds <= 60):
            raise ValueError('explicit short H1 episode budget required: <=24h/20calls/60s')


def _number_wire(value):
    if type(value) is int:
        return ['int', value]
    if type(value) is float and isfinite(value):
        return ['float', value.hex()]
    raise ValueError('finite built-in observation value required')


def _number_value(value):
    if type(value) is not list or len(value) != 2:
        raise ValueError('typed observation number required')
    if value[0] == 'int' and type(value[1]) is int:
        return value[1]
    if value[0] == 'float' and type(value[1]) is str:
        number = float.fromhex(value[1])
        if isfinite(number) and number.hex() == value[1]:
            return number
    raise ValueError('canonical finite observation number required')


_MAPS = (('demand_by_bus_mw', int), ('generator_min_mw', str),
         ('generator_max_mw', str), ('spin_up_requirement_by_area_mw', int))


def _observation(row, workload, basis):
    result = dict(timestamp=row.timestamp.isoformat(), raw_workload=workload, source_time_basis=basis)
    for name, kind in _MAPS:
        values = getattr(row, name)
        if type(values) is not dict or any(type(key) is not kind for key in values):
            raise ValueError('typed observation mapping required')
        result[name] = [[key, _number_wire(value)] for key, value in sorted(values.items())]
    return result


def _row(observation):
    if type(observation) is not dict or set(observation) != {'timestamp', 'raw_workload', 'source_time_basis', *[n for n, _ in _MAPS]}:
        raise ValueError('exact H1 observation schema required')
    values = {}
    for name, kind in _MAPS:
        pairs = observation[name]
        if type(pairs) is not list or any(type(x) is not list or len(x) != 2 or type(x[0]) is not kind for x in pairs):
            raise ValueError('typed observation pairs required')
        keys = [x[0] for x in pairs]
        if keys != sorted(set(keys)):
            raise ValueError('sorted unique observation keys required')
        values[name] = {key: _number_value(number) for key, number in pairs}
    return RtsGmlcHourlyPoint(datetime.fromisoformat(observation['timestamp']), **values)


def _wire(value):
    """Canonical derived-summary encoding; deliberately no object decoder."""
    if is_dataclass(value):
        return {f.name: _wire(getattr(value, f.name)) for f in fields(value)}
    if type(value) is bytes:
        return {'bytes_hex': value.hex()}
    if type(value) is float:
        return {'float_hex': value.hex()}
    if type(value) is tuple:
        return [_wire(x) for x in value]
    if value is None or type(value) in (bool, int, str):
        return value
    raise ValueError('unsupported H1 failure diagnostic type')


def _exception(error):
    try:
        message = str(error)
        rendered = True
    except BaseException:
        message, rendered = '', False
    return dict(type=_text((type(error).__module__+'.'+type(error).__name__).encode('utf-8', 'surrogatepass')),
                message=_text(message.encode('utf-8', 'surrogatepass')), rendered=rendered)


def _failure(result, key, chain, stages):
    """Keep native bytes; derived diagnostics are explicitly summaries, not replay."""
    if type(result) is not current.H1CurrentSolve or result.request_key != key:
        raise ValueError('owned failure result required')
    evidence = result.evidence
    if (type(evidence) is not replay.native.H1ChainEvidence or evidence.chain_identity != chain
            or any(getattr(evidence, name) is not False for name in
                   ('exact_mathematical_certificate','formal_result','hard_process_resources_verified'))
            or type(evidence.collector_attempts) is not int or not 0 <= evidence.collector_attempts <= stages
            or len(evidence.stages) > stages):
        raise ValueError('failure chain or negative authority mismatch')
    records = []
    for index, stage in enumerate(evidence.stages):
        if type(stage) is not replay.native.H1StageEvidence or stage.index != index:
            raise ValueError('failure stage order mismatch')
        raw = stage.native_payload
        if raw is not None and (type(raw) is not bytes or len(raw) > replay.native.MAX_PAYLOAD_BYTES):
            raise ValueError('failure native byte bound mismatch')
        records.append(dict(index=index, stage_identity=stage.stage_identity, accepted=stage.accepted,
            native_payload=raw, errors=_text(journal._bytes(stage.errors)),
            numeric_summary=None if stage.numeric_predicate_payload is None else _descriptor(stage.numeric_predicate_payload),
            audit_summary=None if stage.assignment_audit is None else _descriptor(journal._bytes(_wire(stage.assignment_audit)))))
    return dict(request_key=key, chain_identity=chain, collector_attempts=evidence.collector_attempts,
        solver_calls=evidence.solver_calls, stages=records, errors=_text(journal._bytes(result.errors)),
        current_decision_accepted=result.current_decision_accepted,
        native_execution_authenticated=False, derived_diagnostics_replayed=False, formal_result=False)


def _validate_descriptor(value, *, text=False):
    keys = {'length','sha256'} | ({'prefix_hex','complete'} if text else set())
    if type(value) is not dict or set(value) != keys or type(value['length']) is not int or value['length'] < 0:
        raise ValueError('failure descriptor schema mismatch')
    replay.native._pin(value['sha256'])
    if text:
        prefix = bytes.fromhex(value['prefix_hex'])
        if (prefix.hex() != value['prefix_hex'] or len(prefix) != min(value['length'], TEXT_PREFIX_BYTES)
                or value['complete'] is not (value['length'] <= TEXT_PREFIX_BYTES)
                or (value['complete'] and _descriptor(prefix) != {k:value[k] for k in ('length','sha256')})):
            raise ValueError('failure text descriptor mismatch')


def _validate_failure(value, key, chain, stages):
    if (type(value) is not dict or set(value) != {'request_key','chain_identity','collector_attempts','solver_calls',
            'stages','errors','current_decision_accepted','native_execution_authenticated','derived_diagnostics_replayed','formal_result'}
            or value['request_key'] != key or value['chain_identity'] != chain
            or type(value['collector_attempts']) is not int or not 0 <= value['collector_attempts'] <= stages
            or (value['solver_calls'] is not None and (type(value['solver_calls']) is not int
                or not 0 <= value['solver_calls'] <= value['collector_attempts']))
            or type(value['current_decision_accepted']) is not bool
            or any(value[k] is not False for k in ('native_execution_authenticated','derived_diagnostics_replayed','formal_result'))
            or type(value['stages']) is not list or len(value['stages']) > stages):
        raise ValueError('failure diagnostic binding/schema mismatch')
    _validate_descriptor(value['errors'], text=True)
    payloads = 0
    for index, stage in enumerate(value['stages']):
        if (type(stage) is not dict or set(stage) != {'index','stage_identity','accepted','native_payload','errors','numeric_summary','audit_summary'}
                or type(stage['index']) is not int or stage['index'] != index or type(stage['accepted']) is not bool):
            raise ValueError('failure diagnostic stage schema mismatch')
        replay.native._pin(stage['stage_identity'])
        raw = stage['native_payload']
        if raw is not None:
            if type(raw) is not bytes or len(raw) > replay.native.MAX_PAYLOAD_BYTES:
                raise ValueError('failure diagnostic native byte bound mismatch')
            payloads += 1
        _validate_descriptor(stage['errors'], text=True)
        for name in ('numeric_summary','audit_summary'):
            if stage[name] is not None:
                _validate_descriptor(stage[name])
    if payloads > value['collector_attempts']:
        raise ValueError('failure diagnostic report count exceeds attempts')


@dataclass(frozen=True, init=False)
class H1EpisodeInspection(source._Owned):
    store_identity: str
    head: str
    completed_hours: int
    status: str
    reserved_solver_calls: int
    reserved_solver_seconds: float
    last_projection_identity: str | None
    planned_solver_calls: int
    planned_solver_seconds: float
    source_authenticated: bool
    native_execution_authenticated: bool
    formal_result: bool
    published: bool
    complete_service_certificate: bool
    hard_wall_time_verified: bool


class DevelopmentH1NormalEpisode:
    """Own each normal invocation; failed/pending records can never be retried.

    Only the lease/connection/check primitives are reused. This has an independent
    database, application ID, tables, header and API. Prefix restoration stays private
    to this owner and is never a caller-provided before-state shortcut.
    """
    def __init__(self, root, network, specification, hour_budget, episode_budget, *, dc_bus,
                 create=False, expected_head=None):
        if type(episode_budget) is not H1EpisodeBudget:
            raise ValueError('exact H1 episode budget required')
        episode_budget.__post_init__()
        if type(hour_budget) is not replay.native.GridDevelopmentBudget or hour_budget.purpose != replay.native.PURPOSE:
            raise ValueError('exact H1 per-hour budget required')
        hour_budget.__post_init__()
        replay.native.capture.provenance.adapter.validate_spec(specification)
        source._network(network)
        if type(dc_bus) is not int or dc_bus not in {b.uid for b in network.data.buses}:
            raise ValueError('declared static DC bus required')
        self._network, self._spec = deepcopy(network), deepcopy(specification)
        self._hour_budget, self._episode_budget, self._dc_bus = deepcopy(hour_budget), episode_budget, dc_bus
        self._stages = 1+len(network.data.generators)+sum(g.dispatch_mode == 'committable' for g in network.data.generators)
        self._seconds = self._stages*Fraction.from_float(float(specification.time_limit_seconds))
        self._reserve(episode_budget.planned_hours)
        # Logical content capacity, not disk-space reservation. Binary framing
        # stores accepted archives and rejected raw reports without expansion.
        self._frame_overhead = len(FRAME)+8+MAX_METADATA_BYTES
        self._event_bytes = self._frame_overhead+max(replay.MAX_ARCHIVE_BYTES,
            self._stages*replay.native.MAX_PAYLOAD_BYTES)
        self._journal_bytes = (2*episode_budget.planned_hours*self._frame_overhead
            + episode_budget.planned_hours*replay.MAX_ARCHIVE_BYTES
            + episode_budget.max_reserved_solver_calls*replay.native.MAX_PAYLOAD_BYTES)
        if (hour_budget.max_horizon != 1 or self._stages > hour_budget.max_solver_calls
                or self._seconds > Fraction.from_float(float(hour_budget.max_total_solver_seconds))
                or specification.threads > hour_budget.max_threads
                or specification.time_limit_seconds > hour_budget.max_seconds_per_solve):
            raise ValueError('complete H1 per-hour stages exceed short budget')
        if type(create) is not bool or (create and expected_head is not None):
            raise ValueError('explicit create flag and independent reopen head required')
        if not create:
            replay.native._pin(expected_head)
        self._limit = 2*episode_budget.planned_hours
        self._closed = self._poisoned = False
        self._guard = Lock()
        self._lease = journal.local._Lease(root, create)
        try:
            self._header = self._header_bytes()
            self.identity = sha256(self._header).hexdigest()
            self._genesis = sha256(journal._bytes([SCHEMA, self.identity, 'genesis'])).hexdigest()
            self._database = self._lease.root/'h1_normal_episode.sqlite3'
            if create:
                with self._database.open('xb') as stream:
                    os.fsync(stream.fileno())
            self._file_identity = journal.local._file_identity(self._database)
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
            self._restore()
        except BaseException:
            self._lease.close()
            raise

    def _header_bytes(self):
        source._network(self._network)
        return journal._bytes(dict(schema=SCHEMA, root=os.path.normcase(str(self._lease.root)),
            episode_implementation=sha256(Path(__file__).read_bytes()).hexdigest(),
            physical_journal_implementation=sha256(Path(journal.__file__).read_bytes()).hexdigest(),
            lease_implementation=sha256(Path(journal.local.__file__).read_bytes()).hexdigest(),
            replay_implementation=replay.implementation_identity(), sqlite=sqlite3.sqlite_version,
            application_id=APPLICATION_ID, tables=TABLES, max_records=self._limit,
            max_event_bytes=self._event_bytes, max_journal_bytes=self._journal_bytes,
            max_metadata_bytes=MAX_METADATA_BYTES, text_prefix_bytes=TEXT_PREFIX_BYTES,
            max_native_stage_bytes=replay.native.MAX_PAYLOAD_BYTES, frame=FRAME.hex(),
            network_identity=self._network.identity, dc_bus=self._dc_bus,
            solver_specification=asdict(self._spec), hour_budget=asdict(self._hour_budget),
            episode_budget=asdict(self._episode_budget), source_authenticated=False, formal_result=False))

    _check = journal.DevelopmentH1ProjectionStore._check
    _connect = journal.DevelopmentH1ProjectionStore._connect
    _commit = journal.DevelopmentH1ProjectionStore._commit
    close = journal.DevelopmentH1ProjectionStore.close
    __copy__ = journal.DevelopmentH1ProjectionStore.__copy__
    __deepcopy__ = journal.DevelopmentH1ProjectionStore.__deepcopy__
    __reduce_ex__ = journal.DevelopmentH1ProjectionStore.__reduce_ex__

    @property
    def head(self):
        return self._head

    def _rows(self, connection):
        if (connection.execute('PRAGMA integrity_check').fetchall() != [('ok',)]
                or connection.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID
                or set(r[0] for r in connection.execute('SELECT sql FROM sqlite_master WHERE sql IS NOT NULL')) != set(TABLES)
                or connection.execute('SELECT id,header FROM metadata').fetchall() != [(1, self._header)]):
            raise ValueError('H1 episode schema/header/integrity mismatch')
        count, largest, total = connection.execute('SELECT count(*),max(length(archive)),coalesce(sum(length(archive)),0) FROM events').fetchone()
        if count > self._limit or (largest is not None and largest > self._event_bytes) or total > self._journal_bytes:
            raise ValueError('H1 episode stored byte/record budget exceeded')
        rows = connection.execute('SELECT seq,predecessor,request_key,archive_sha256,archive,head FROM events ORDER BY seq').fetchall()
        head = self._genesis
        for expected, (seq, predecessor, key, pin, payload, after) in enumerate(rows, 1):
            replay.native._pin(key)
            replay.native._pin(pin)
            if (seq != expected or predecessor != head or type(payload) is not bytes
                    or sha256(payload).hexdigest() != pin or after != _head(seq, predecessor, key, pin)):
                raise ValueError('H1 episode event hash/sequence mismatch')
            head = after
        if head != self._head:
            raise ValueError('independently retained H1 episode head mismatch')
        return rows

    def append(self, *args, **kwargs):
        raise TypeError('normal episode requires owned step; arbitrary archives cannot advance it')

    def _packet(self, observation, completed, before):
        return source.assemble_current_normal(self._network, _row(observation), observation['raw_workload'],
            relative_hour=completed, dc_bus=self._dc_bus, source_time_basis=observation['source_time_basis'], before=before)

    def _reserve(self, attempts):
        if (attempts > self._episode_budget.planned_hours
                or attempts*self._stages > self._episode_budget.max_reserved_solver_calls
                or attempts*self._seconds > Fraction.from_float(self._episode_budget.max_reserved_solver_seconds)):
            raise ValueError('H1 episode reservation budget exhausted')

    def _restore(self):
        connection = self._connect()
        try:
            rows = self._rows(connection)
        finally:
            connection.close()
        before, pending, last_observation, last_projection = None, None, None, None
        completed, attempts, stopped = 0, 0, False
        for seq, previous_head, key, _, payload, record_head in rows:
            item = _decode_event(payload)
            if (type(item) is not dict or item.get('schema') != SCHEMA or stopped
                    or item.get('hour') != completed or type(item.get('hour')) is not int
                    or item.get('request_key') != key):
                raise ValueError('H1 episode event order/schema/key mismatch')
            if item.get('kind') == 'intent':
                if pending is not None or set(item) != {'schema','kind','hour','request_key','observation',
                        'before_identity','source_audit_identity','chain_identity','reserved_solver_calls',
                        'reserved_solver_seconds_exact'}:
                    raise ValueError('H1 episode requires alternating intent/outcome')
                attempts += 1
                self._reserve(attempts)
                observation = item['observation']
                if last_observation is not None:
                    if (observation['source_time_basis'] != last_observation['source_time_basis']
                            or _row(observation).timestamp-_row(last_observation).timestamp != timedelta(hours=1)):
                        raise ValueError('H1 observed source clock gap or basis change')
                packet = self._packet(observation, completed, before)
                if (current.request_key(packet, self._spec, self._hour_budget) != key
                        or source._digest(packet.before) != item['before_identity']
                        or packet.audit_identity != item['source_audit_identity']
                        or replay.native.chain_identity(packet.inputs, self._spec, self._hour_budget) != item['chain_identity']
                        or type(item['reserved_solver_calls']) is not int or item['reserved_solver_calls'] != self._stages
                        or item['reserved_solver_seconds_exact'] != [str(self._seconds.numerator), str(self._seconds.denominator)]):
                    raise ValueError('H1 episode predecessor/source/request binding mismatch')
                pending = (packet, observation, record_head)
            elif item.get('kind') in ('accepted', 'rejected', 'exception'):
                if pending is None or item.get('intent_head') != pending[2] or previous_head != pending[2]:
                    raise ValueError('H1 outcome has no exact immediately preceding intent')
                packet, observation, _ = pending
                if key != current.request_key(packet, self._spec, self._hour_budget):
                    raise ValueError('H1 outcome request differs from intent')
                if item['kind'] == 'accepted':
                    if set(item) != {'schema','kind','hour','request_key','intent_head','archive','archive_sha256'}:
                        raise ValueError('H1 accepted outcome schema mismatch')
                    verified = replay.replay_archive(packet, self._spec, self._hour_budget,
                        item['archive'], expected_key=key, expected_archive_sha256=item['archive_sha256'])
                    values = json.loads(verified.projection_payload)
                    before = source._owned(source.H1NormalBoundary, network_identity=values['network_identity'],
                        completed_hours=values['completed_hours'],
                        units=tuple((uid, on, float.fromhex(power), age) for uid, on, power, age in values['units']),
                        evidence_role='numerical_lex_candidate')
                    source._boundary(self._network, before, completed+1)
                    completed += 1
                    last_projection = verified.projection_identity
                    last_observation = observation
                else:
                    if set(item) != {'schema','kind','hour','request_key','intent_head','diagnostic'}:
                        raise ValueError('H1 rejected outcome schema mismatch')
                    diagnostic = item['diagnostic']
                    chain = replay.native.chain_identity(packet.inputs, self._spec, self._hour_budget)
                    if item['kind'] == 'rejected':
                        _validate_failure(diagnostic, key, chain, self._stages)
                        if diagnostic['current_decision_accepted'] is not False:
                            raise ValueError('rejected diagnostic claims accepted decision')
                    else:
                        if (type(diagnostic) is not dict or set(diagnostic) != {'exception','returned_result','actual_solver_calls_known'}
                                or diagnostic['actual_solver_calls_known'] is not False):
                            raise ValueError('exception diagnostic schema mismatch')
                        description = diagnostic['exception']
                        if (type(description) is not dict or set(description) != {'type','message','rendered'}
                                or type(description['rendered']) is not bool):
                            raise ValueError('exception descriptor schema mismatch')
                        for name in ('type','message'):
                            _validate_descriptor(description[name], text=True)
                        if diagnostic['returned_result'] is not None:
                            _validate_failure(diagnostic['returned_result'], key, chain, self._stages)
                    stopped = True
                pending = None
            else:
                raise ValueError('unknown H1 episode event')
        snapshot = source._owned(H1EpisodeInspection, store_identity=self.identity, head=self._head,
            completed_hours=completed, status='unresolved_intent' if pending else 'halted' if stopped
                else 'complete' if completed == self._episode_budget.planned_hours else 'ready',
            reserved_solver_calls=attempts*self._stages, reserved_solver_seconds=float(attempts*self._seconds),
            last_projection_identity=last_projection,
            planned_solver_calls=self._episode_budget.planned_hours*self._stages,
            planned_solver_seconds=float(self._episode_budget.planned_hours*self._seconds), source_authenticated=False,
            native_execution_authenticated=False, formal_result=False, published=False,
            complete_service_certificate=False, hard_wall_time_verified=False)
        self._check()
        return snapshot, before, last_observation

    def inspect(self):
        with self._guard:
            return self._restore_checked()[0]

    def _restore_checked(self):
        try:
            return self._restore()
        except BaseException:
            self._poisoned = True
            raise

    def _append_event(self, event):
        payload = _encode_event(event)
        if len(payload) > self._event_bytes:
            raise ValueError('H1 episode event byte budget exceeded')
        connection = self._connect()
        try:
            connection.execute('BEGIN IMMEDIATE')
            rows = self._rows(connection)
            if len(rows) >= self._limit or sum(len(row[4]) for row in rows)+len(payload) > self._journal_bytes:
                raise ValueError('H1 episode journal record/byte budget exhausted')
            pin = sha256(payload).hexdigest()
            new_head = _head(len(rows)+1, self._head, event['request_key'], pin)
            row = (len(rows)+1, self._head, event['request_key'], pin, payload, new_head)
            connection.execute('INSERT INTO events VALUES (?,?,?,?,?,?)', row)
            self._check()
            self._commit(connection)
            self._head = new_head
            connection.close()
            connection = None
            readback = self._connect()
            try:
                if self._rows(readback) != [*rows, row]:
                    raise ValueError('H1 episode commit readback mismatch')
            finally:
                readback.close()
            self._check()
        except BaseException:
            self._poisoned = True
            raise
        finally:
            if connection is not None:
                connection.close()

    def step(self, row, raw_workload, *, source_time_basis, expected_head):
        with self._guard:
            if type(expected_head) is not str or expected_head != self._head:
                raise ValueError('H1 step requires exact retained predecessor head')
            snapshot, before, last_observation = self._restore_checked()
            if snapshot.status != 'ready':
                raise ValueError('pending or halted H1 episode cannot retry')
            self._reserve(snapshot.completed_hours+1)
            row = deepcopy(row)
            packet = source.assemble_current_normal(self._network, row, raw_workload,
                relative_hour=snapshot.completed_hours, dc_bus=self._dc_bus,
                source_time_basis=source_time_basis, before=before)
            observation = _observation(row, raw_workload, source_time_basis)
            if last_observation is not None and (source_time_basis != last_observation['source_time_basis']
                    or row.timestamp-_row(last_observation).timestamp != timedelta(hours=1)):
                raise ValueError('H1 observed source clock gap or basis change')
            key = current.request_key(packet, self._spec, self._hour_budget)
            chain = replay.native.chain_identity(packet.inputs, self._spec, self._hour_budget)
            self._append_event(dict(schema=SCHEMA, kind='intent', hour=snapshot.completed_hours, request_key=key,
                observation=observation, before_identity=source._digest(packet.before), source_audit_identity=packet.audit_identity,
                chain_identity=chain,
                reserved_solver_calls=self._stages,
                reserved_solver_seconds_exact=[str(self._seconds.numerator), str(self._seconds.denominator)]))
            intent_head = self._head
            if self._restore_checked()[0].status != 'unresolved_intent':
                self._poisoned = True
                raise ValueError('H1 intent readback required before native invocation')
            result = None
            failure = None
            try:
                result = current.solve_current(packet, self._spec, self._hour_budget, expected_key=key)
                if type(result) is not current.H1CurrentSolve or result.request_key != key:
                    raise ValueError('owned current result does not match episode intent')
                failure = _failure(result, key, chain, self._stages)
                _validate_failure(failure, key, chain, self._stages)
                if result.current_decision_accepted:
                    archive = replay.archive_current(packet, self._spec, self._hour_budget, result)
                    outcome = dict(kind='accepted', archive=archive, archive_sha256=sha256(archive).hexdigest())
                else:
                    outcome = dict(kind='rejected', diagnostic=failure)
            except Exception as error:
                outcome = dict(kind='exception', diagnostic=dict(exception=_exception(error),
                    returned_result=failure,
                    actual_solver_calls_known=False))
            self._append_event(dict(schema=SCHEMA, hour=snapshot.completed_hours, request_key=key,
                                    intent_head=intent_head, **outcome))
            restored = self._restore_checked()[0]
            return (result if outcome['kind'] == 'accepted' else None), restored
