"""Saved source parent with explicit bounded event-file persistence.

Source/carry chronology is unchanged; event lookup uses an external-head checked
file journal. A new declaration prevents interpreting this as a legacy store.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json

from experiments import h1_attested_source_parent_development_v1 as prior
from experiments import h1_file_parent_journal_development_v1 as journal
from experiments import h1_child_storage_classes_development_v1 as child_storage

source, chunks, replay = prior.prior.source, prior.prior.chunks, prior.replay
binding, anchor, Inspection = prior.prior.binding, prior.prior.anchor, prior.prior.Inspection
SCHEMA = prior.prior.SCHEMA
PARENT_SCHEMA = 'h1_bounded_file_parent_development_v1'


def implementation_identity():
    return source._digest(PARENT_SCHEMA,prior.implementation_identity(),
        journal.implementation_identity(),sha256(Path(__file__).read_bytes()).hexdigest())


class SavedSourceParent(prior.SavedSourceParent):
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
        self._root_lease = None
        self._declaration = self._declare()
        self.identity = sha256(chunks.base._bytes(self._declaration)).hexdigest()
        n = 2 * hours
        budget = chunks.ChunkContentBudget(n, 2*chunks.METADATA_BYTES, n*2*chunks.METADATA_BYTES)
        try:
            self._root_lease = chunks.base.local._Lease(self._root,create)
            if create:
                self._journal = journal.Journal(self._root/'parent_events_non_authoritative', budget, binding_identity=self.identity, create=True)
            self._anchor = anchor.DevelopmentH1FullAttemptAnchor(self._root/'parent_anchor_non_authoritative',
                self.identity, max_records=n+1, create=create, expected_record_sha256=expected_anchor_record)
            if create:
                self._anchor.advance(self._journal.head, sha256(b'genesis').hexdigest(), expected_previous=None)
            else:
                receipt = self._anchor.inspect()
                if receipt is None:
                    raise ValueError('parent anchor lacks genesis')
                self._journal = journal.Journal(self._root/'parent_events_non_authoritative', budget,
                    binding_identity=self.identity, expected_head=receipt.registry_head)
            self._restore()
        except BaseException:
            self.close()
            raise

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
                head = self._journal.event_head(seq,expected_head=physical.head)
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

    def _declare(self):
        result=super()._declare()
        result.update(schema=PARENT_SCHEMA,implementation_identity=implementation_identity(),
                      parent_journal_protocol=journal.SCHEMA)
        return result

    def _check(self):
        if self._root_lease is not None:self._root_lease.check()
        super()._check()

    def close(self):
        try:super().close()
        finally:
            if self._root_lease is not None:self._root_lease.close()


def storage_bound(hours,stages):
    children=child_storage.envelope(hours,stages)
    events=journal.storage_bound(2*hours)
    # Root lease plus existing anchor header, numbered records and its lease.
    anchor_files=2*hours+3
    anchor_bytes=(2*hours+2)*anchor.MAX_RECORD_BYTES+1
    return dict(schema=PARENT_SCHEMA,hours=hours,stages_per_hour=stages,
        logical_bytes=children['retained_children_logical_bytes']+events['logical_bytes']+anchor_bytes+1,
        files=children['files']+events['files']+anchor_files+1,
        directories=children['directories']+events['directories']+2,
        children=children,parent_events=events,anchor_logical_bytes=anchor_bytes,
        job_storage_included=False,filesystem_allocation_bound_proven=False,
        resource_admission=False,formal_execution_ready=False,formal_result=False)
