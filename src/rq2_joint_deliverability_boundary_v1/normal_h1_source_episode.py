"""Source-bound short normal episode; one atomic source/normal intent record."""
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from datetime import timedelta
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
from threading import Lock

from . import normal_h1_episode as base
from . import normal_h1_source_binding as binding

journal, replay, current, source = base.journal, base.replay, base.current, base.source
H1EpisodeBudget = base.H1EpisodeBudget
MAX_METADATA_BYTES, TEXT_PREFIX_BYTES, FRAME = base.MAX_METADATA_BYTES, base.TEXT_PREFIX_BYTES, base.FRAME
MAX_SOURCE_AUDIT_BYTES = 256 * 1024
_encode_event, _decode_event = base._encode_event, base._decode_event
_observation, _row = base._observation, base._row
_exception, _failure = base._exception, base._failure
_validate_failure, _validate_descriptor = base._validate_failure, base._validate_descriptor
SCHEMA = 'h1_source_bound_normal_episode_development_v1'
APPLICATION_ID = 0x48453132
TABLES = base.TABLES


def _head(seq, before, key, pin):
    return sha256(journal._bytes([SCHEMA, seq, before, key, pin])).hexdigest()


@dataclass(frozen=True, init=False)
class H1SourceEpisodeInspection(source._Owned):
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
    source_bound_hours: int
    selection_registered: bool


class DevelopmentH1SourceEpisode:
    """Own each normal invocation; failed/pending records can never be retried.

    Numerical replay, binary evidence and lease primitives are reused. This has an independent
    database, application ID, tables, header and API. Prefix restoration stays private
    to this owner and is never a caller-provided before-state shortcut.
    """
    def __init__(self, root, network, specification, hour_budget, episode_budget, *, dc_bus,
                 origin, upstream_root, config_path=binding.windows.audit.DEFAULT_CONFIG,
                 create=False, expected_head=None):
        if type(origin) is not binding.H1SourceDeclaration:
            raise ValueError('exact source-bound episode origin required')
        origin.__post_init__()
        self._origin = deepcopy(origin)
        self._upstream_root = Path(upstream_root).resolve(strict=True)
        self._config_path = Path(config_path).resolve(strict=True)
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
            self._stages*replay.native.MAX_PAYLOAD_BYTES, MAX_SOURCE_AUDIT_BYTES)
        self._journal_bytes = (2*episode_budget.planned_hours*self._frame_overhead
            + episode_budget.planned_hours*replay.MAX_ARCHIVE_BYTES
            + episode_budget.max_reserved_solver_calls*replay.native.MAX_PAYLOAD_BYTES
            + episode_budget.planned_hours*MAX_SOURCE_AUDIT_BYTES)
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
            self._database = self._lease.root/'h1_source_normal_episode.sqlite3'
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
            normal_episode_implementation=sha256(Path(base.__file__).read_bytes()).hexdigest(),
            source_binding_implementation=binding.implementation_identity(),
            source_origin=asdict(self._origin), upstream_root=str(self._upstream_root), config_path=str(self._config_path),
            max_source_audit_bytes=MAX_SOURCE_AUDIT_BYTES,
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

    def _load_source(self, hour, expected_identity):
        replay.native._pin(expected_identity)
        declaration = replace(self._origin, power_raw_hour=self._origin.power_raw_hour+hour,
                              workload_raw_hour=self._origin.workload_raw_hour+hour)
        receipt = binding.load_pinned_current(declaration, self._upstream_root, config_path=self._config_path)
        if (type(receipt) is not binding.H1PinnedObservation or type(receipt.audit_payload) is not bytes
                or receipt.identity != expected_identity or binding._identity(receipt) != expected_identity
                or receipt.network.identity != self._network.identity
                or len(receipt.audit_payload) > MAX_SOURCE_AUDIT_BYTES):
            raise ValueError('source-bound episode receipt/network/byte admission mismatch')
        return receipt

    @staticmethod
    def _source_chains(receipt):
        audit = json.loads(receipt.audit_payload)
        return (audit['power_chain_identity'], audit['workload_chain_identity'])

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
        source_chains = None
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
                        'reserved_solver_seconds_exact','source_binding_identity','source_binding_audit'}:
                    raise ValueError('H1 episode requires alternating intent/outcome')
                attempts += 1
                self._reserve(attempts)
                observation = item['observation']
                receipt = self._load_source(completed, item['source_binding_identity'])
                expected_observation = _observation(receipt.row, receipt.raw_workload, receipt.source_time_basis)
                if (item['source_binding_audit'] != receipt.audit_payload
                        or journal._bytes(observation) != journal._bytes(expected_observation)):
                    raise ValueError('source-bound intent observation or audit differs from pinned source')
                chains = self._source_chains(receipt)
                if source_chains is not None and chains != source_chains:
                    raise ValueError('source-bound episode cannot cross a verified source chain')
                source_chains = chains
                observation = expected_observation
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
        snapshot = source._owned(H1SourceEpisodeInspection, store_identity=self.identity, head=self._head,
            completed_hours=completed, status='unresolved_intent' if pending else 'halted' if stopped
                else 'complete' if completed == self._episode_budget.planned_hours else 'ready',
            reserved_solver_calls=attempts*self._stages, reserved_solver_seconds=float(attempts*self._seconds),
            last_projection_identity=last_projection,
            planned_solver_calls=self._episode_budget.planned_hours*self._stages,
            planned_solver_seconds=float(self._episode_budget.planned_hours*self._seconds), source_authenticated=False,
            native_execution_authenticated=False, formal_result=False, published=False,
            complete_service_certificate=False, hard_wall_time_verified=False,
            source_bound_hours=attempts, selection_registered=False)
        self._check()
        return snapshot, before, last_observation, source_chains

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

    def step(self, *, expected_source_identity, expected_head):
        with self._guard:
            if type(expected_head) is not str or expected_head != self._head:
                raise ValueError('H1 step requires exact retained predecessor head')
            snapshot, before, last_observation, source_chains = self._restore_checked()
            if snapshot.status != 'ready':
                raise ValueError('pending or halted H1 episode cannot retry')
            self._reserve(snapshot.completed_hours+1)
            receipt = self._load_source(snapshot.completed_hours, expected_source_identity)
            if source_chains is not None and self._source_chains(receipt) != source_chains:
                raise ValueError('source-bound episode cannot cross a verified source chain')
            row, raw_workload, source_time_basis = receipt.row, receipt.raw_workload, receipt.source_time_basis
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
                source_binding_identity=receipt.identity, source_binding_audit=receipt.audit_payload,
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
