"""Pinned-source full-window parent for saved reports; never launches a Job.

Reopening is inspection only. Missing hours remain unresolved, and no returned
state supplies formal, native, resource, or future execution authority.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from datetime import timedelta
from hashlib import sha256
import json
from pathlib import Path

from src.rq2_joint_deliverability_boundary_v1 import normal_h1_source_binding as binding
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_hour_archive_v3 as child
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_attempt_anchor_v3 as anchor
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_source_episode as old

source, chunks, replay = binding.h1, child.chunks, child.replay
SCHEMA = 'h1_saved_source_parent_development_v1'


def implementation_identity():
    return source._digest(SCHEMA, binding.implementation_identity(),
        child.implementation_identity(), anchor.implementation_identity(),
        sha256(Path(old.__file__).read_bytes()).hexdigest(),
        sha256(Path(__file__).read_bytes()).hexdigest())


@dataclass(frozen=True)
class Inspection:
    parent_identity: str
    head: str
    completed_hours: int
    attempted_hours: int
    status: str
    declared_stage_slots: int
    last_projection_identity: str | None
    solver_calls_by_parent: int = 0
    source_solver_calls: int | None = None
    native_execution_authenticated: bool = False
    source_authenticated: bool = False
    published: bool = False
    independent_hour_jobs_integrated: bool = False
    producer_coverage_proven: bool = False
    resource_admission: bool = False
    formal_execution_ready: bool = False
    formal_result: bool = False


class SavedSourceParent:
    """Create-once offline parent with 2 events/hour and a retained local anchor.

    All children are independently reopened and numerically replayed. Content
    declaration is not a disk reservation. There is deliberately no run method.
    """
    def __init__(self, root, network, specification, limits, *, origin,
                 upstream_root, config_path, dc_bus, hours=192, create=False,
                 expected_anchor_record=None):
        if type(hours) is not int or not 1 <= hours <= 192:
            raise ValueError('exact planned hours in [1,192] required')
        if type(create) is not bool or (create and expected_anchor_record is not None):
            raise ValueError('exact create flag and separate reopen pin required')
        if not create:
            chunks._pin(expected_anchor_record)
        if type(origin) is not binding.H1SourceDeclaration:
            raise ValueError('exact pinned source origin required')
        origin.__post_init__()
        source._network(network)
        replay.native.capture.provenance.adapter.validate_spec(specification)
        if type(limits) is not replay.H1HourReplayLimits:
            raise ValueError('exact full hour replay limits required')
        limits.__post_init__()
        if type(dc_bus) is not int or dc_bus not in {b.uid for b in network.data.buses}:
            raise ValueError('declared static DC bus required')
        self._network, self._spec, self._limits, self._origin = deepcopy((network, specification, limits, origin))
        self._hours, self._dc_bus = hours, dc_bus
        self._upstream_root = Path(upstream_root).resolve(strict=True)
        self._config_path = Path(config_path).resolve(strict=True)
        self._root = Path(root).resolve()
        self._stages = 1 + len(network.data.generators) + sum(g.dispatch_mode == 'committable' for g in network.data.generators)
        if self._stages > limits.max_stages:
            raise ValueError('complete stage inventory exceeds replay limits')
        self._guard = chunks._Exclusive()
        self._closed = self._poisoned = False
        self._writable = create
        self._journal = self._anchor = None
        self._declaration = self._declare()
        self.identity = sha256(chunks.base._bytes(self._declaration)).hexdigest()
        n = 2 * hours
        budget = chunks.ChunkContentBudget(n, 2*chunks.METADATA_BYTES, n*2*chunks.METADATA_BYTES)
        try:
            if create:
                self._journal = chunks.DevelopmentH1ChunkJournal(self._root, budget, binding_identity=self.identity, create=True)
            self._anchor = anchor.DevelopmentH1FullAttemptAnchor(self._root/'parent_anchor_non_authoritative',
                self.identity, max_records=n+1, create=create, expected_record_sha256=expected_anchor_record)
            if create:
                self._anchor.advance(self._journal.head, sha256(b'genesis').hexdigest(), expected_previous=None)
            else:
                receipt = self._anchor.inspect()
                if receipt is None:
                    raise ValueError('parent anchor lacks genesis')
                self._journal = chunks.DevelopmentH1ChunkJournal(self._root, budget,
                    binding_identity=self.identity, expected_head=receipt.registry_head)
            self._restore()
        except BaseException:
            self.close()
            raise

    def _declare(self):
        return dict(schema=SCHEMA, root=str(self._root), network_identity=self._network.identity,
            specification=asdict(self._spec), limits=asdict(self._limits), origin=asdict(self._origin),
            dc_bus=self._dc_bus, hours=self._hours, declared_stage_slots=self._stages*self._hours,
            upstream_root=str(self._upstream_root), config_path=str(self._config_path),
            implementation_identity=implementation_identity())

    def _check(self):
        if self._closed or self._poisoned:
            raise ValueError('closed or unresolved saved source parent')
        source._network(self._network)
        if self._declare() != self._declaration:
            raise ValueError('saved source parent declaration drift')
        receipt = self._anchor.inspect()
        if receipt is None or receipt.registry_head != self._journal.head:
            raise ValueError('parent head not anchored')
        self._anchor.confirm(receipt)

    def _load(self, hour, pin):
        chunks._pin(pin)
        declaration = replace(self._origin, power_raw_hour=self._origin.power_raw_hour+hour,
                              workload_raw_hour=self._origin.workload_raw_hour+hour)
        receipt = binding.load_pinned_current(declaration, self._upstream_root, config_path=self._config_path)
        if (type(receipt) is not binding.H1PinnedObservation or receipt.declaration != declaration
                or receipt.identity != pin or binding._identity(receipt) != pin
                or receipt.network.identity != self._network.identity
                or type(receipt.audit_payload) is not bytes or len(receipt.audit_payload) > old.MAX_SOURCE_AUDIT_BYTES):
            raise ValueError('pinned current source/network differs')
        return receipt

    def _packet(self, receipt, hour, before, previous):
        if previous is not None:
            a, b = json.loads(previous.audit_payload), json.loads(receipt.audit_payload)
            for key in ('power_chain_identity', 'workload_chain_identity',
                        'power_package_manifest_sha256', 'workload_package_manifest_sha256', 'grid_manifest_sha256'):
                if a[key] != b[key]:
                    raise ValueError('source chain/package changed')
            if (receipt.source_time_basis != previous.source_time_basis
                    or receipt.row.timestamp-previous.row.timestamp != timedelta(hours=1)):
                raise ValueError('source clock continuity failed')
        packet = source.assemble_current_normal(receipt.network, receipt.row, receipt.raw_workload,
            relative_hour=hour, dc_bus=self._dc_bus, source_time_basis=receipt.source_time_basis, before=before)
        replay.request_key(packet, self._spec, self._limits)
        return packet

    def _intent(self, hour, receipt, packet):
        return dict(schema=SCHEMA, kind='intent', hour=hour, source_identity=receipt.identity,
            source_audit_sha256=sha256(receipt.audit_payload).hexdigest(), before_identity=source._digest(packet.before),
            packet_audit_identity=packet.audit_identity, request_key=replay.request_key(packet,self._spec,self._limits),
            child_root=str(self._root/f'hour_{hour:03d}_non_authoritative'), stage_slots=self._stages)

    def _child(self, hour, packet, intent_head, lineage, **kwargs):
        return child.DevelopmentH1HourArchive(self._root/f'hour_{hour:03d}_non_authoritative',
            packet,self._spec,self._limits,parent_intent_head=intent_head,source_lineage_identity=lineage,**kwargs)

    def _outcome(self, hour, intent_head, result):
        if type(result) is not child.H1HourArchiveInspection or result.status not in ('accepted','rejected'):
            raise ValueError('terminal saved child required')
        return dict(schema=SCHEMA, kind=result.status, hour=hour, intent_head=intent_head,
            child_head=result.head, child_identity=result.archive_identity, stored_reports=result.stored_reports,
            projection_identity=None if result.projection is None else result.projection.projection_identity)

    def _after(self, packet, result):
        p = result.projection
        if (type(p) is not replay.H1HourReplayedProjection or p.request_key != replay.request_key(packet,self._spec,self._limits)
                or p.before_identity != source._digest(packet.before) or len(p.canonical_locks) != self._stages
                or p.numerical_chain_recomputed is not True or p.solver_calls_by_replay != 0
                or any(getattr(p,k) is not False for k in ('published','formal_result','native_execution_authenticated','exact_mathematical_certificate'))):
            raise ValueError('independently replayed complete child projection required')
        values = json.loads(p.projection_payload)
        after = source._owned(source.H1NormalBoundary, network_identity=values['network_identity'],
            completed_hours=values['completed_hours'], units=tuple((uid,on,float.fromhex(power),age)
                for uid,on,power,age in values['units']), evidence_role='numerical_lex_candidate')
        source._boundary(self._network,after,packet.relative_hour+1)
        return after

    def _append(self, metadata, payload=b''):
        self._check()
        previous = self._journal.head
        self._journal.append(metadata, () if not payload else (payload,), expected_head=previous,
            declared_payload_bytes=len(payload),expected_payload_sha256=sha256(payload).hexdigest())
        receipt = self._anchor.advance(self._journal.head,sha256(chunks.base._bytes(metadata)).hexdigest(),expected_previous=previous)
        self._anchor.confirm(receipt)
        self._check()

    def _restore(self):
        self._check()
        physical = self._journal.inspect()
        completed = attempted = 0
        before = previous = pending = projection_pin = None
        halted = False
        for seq in range(1,physical.events+1):
            raw = self._journal.event_metadata(seq,expected_head=physical.head)
            item = json.loads(raw)
            payload = b''.join(self._journal.iter_event(seq,expected_head=physical.head))
            if (halted or item.get('schema') != SCHEMA or type(item.get('hour')) is not int
                    or item['hour'] != completed or completed >= self._hours):
                raise ValueError('parent event chronology mismatch')
            if item.get('kind') == 'intent':
                if pending is not None:
                    raise ValueError('parent intent already pending')
                receipt = self._load(completed,item['source_identity'])
                packet = self._packet(receipt,completed,before,previous)
                if raw != chunks.base._bytes(self._intent(completed,receipt,packet)) or payload != receipt.audit_payload:
                    raise ValueError('parent intent differs from pinned source')
                connection = self._journal._connect()
                try:
                    head = connection.execute('SELECT head FROM events WHERE seq=?',(seq,)).fetchone()[0]
                finally:
                    connection.close()
                pending = packet,receipt,head
                attempted += 1
            elif item.get('kind') in ('accepted','rejected'):
                if pending is None or payload:
                    raise ValueError('outcome lacks exact intent')
                packet,receipt,head = pending
                owner = self._child(completed,packet,head,receipt.identity,expected_head=item['child_head'])
                try:
                    result = owner.inspect()
                finally:
                    owner.close()
                if raw != chunks.base._bytes(self._outcome(completed,head,result)):
                    raise ValueError('outcome differs from fresh saved child')
                if result.status == 'accepted':
                    before = self._after(packet,result)
                    previous = receipt
                    projection_pin = result.projection.projection_identity
                    completed += 1
                else:
                    halted = True
                pending = None
            else:
                raise ValueError('unknown parent event kind')
        self._check()
        if self._journal.inspect() != physical:
            raise ValueError('parent physical view changed during replay')
        state = Inspection(self.identity,physical.head,completed,attempted,
            'pending_unknown' if pending else 'halted' if halted else 'complete' if completed == self._hours else 'ready',
            self._hours*self._stages,projection_pin)
        return state,before,previous

    def inspect(self):
        with self._guard, replay.guard.solver_calls_forbidden():
            try:
                return self._restore()[0]
            except BaseException:
                self._poisoned = True
                raise

    def step_saved(self, reports, *, expected_source_identity, expected_head):
        with self._guard, replay.guard.solver_calls_forbidden():
            try:
                if not self._writable:
                    raise ValueError('reopened parent is inspection only')
                state,before,previous = self._restore()
                if state.status != 'ready' or expected_head != state.head:
                    raise ValueError('ready exact parent predecessor required')
                hour = state.completed_hours
                receipt = self._load(hour,expected_source_identity)
                packet = self._packet(receipt,hour,before,previous)
                self._append(self._intent(hour,receipt,packet),receipt.audit_payload)
                head = self._journal.head
                if self._restore()[0].status != 'pending_unknown':
                    raise ValueError('anchored intent required before saved report consumption')
                owner = self._child(hour,packet,head,receipt.identity,create=True)
                try:
                    result = owner.inspect()
                    count = 0
                    for raw in reports:
                        if count >= self._stages:
                            raise ValueError('extra saved report')
                        result = owner.record_report(raw,expected_head=owner.head)
                        count += 1
                        if result.status == 'rejected':
                            break
                    if result.status != 'rejected':
                        if count != self._stages:
                            raise ValueError('incomplete saved report prefix')
                        result = owner.finish(expected_head=owner.head)
                finally:
                    owner.close()
                reopened = self._child(hour,packet,head,receipt.identity,expected_head=result.head)
                try:
                    if reopened.inspect() != result:
                        raise ValueError('fresh child replay differs')
                finally:
                    reopened.close()
                self._restore()  # Includes post-child source revalidation.
                self._append(self._outcome(hour,head,result))
                return self._restore()[0]
            except BaseException:
                self._poisoned = True
                raise

    def close(self):
        with self._guard:
            if not self._closed:
                try:
                    if self._journal is not None:
                        self._journal.close()
                finally:
                    if self._anchor is not None:
                        self._anchor.close()
                    self._closed = True

    __copy__ = chunks.DevelopmentH1ChunkJournal.__copy__
    __deepcopy__ = chunks.DevelopmentH1ChunkJournal.__deepcopy__
    __reduce_ex__ = chunks.DevelopmentH1ChunkJournal.__reduce_ex__
