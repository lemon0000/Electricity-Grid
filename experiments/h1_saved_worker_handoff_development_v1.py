"""Synchronous create-owner handoff to a fixed saved-report worker.

The parent guard remains held across reconstruction, consumption and acceptance.
This in-memory handoff is neither durable nor an independent Job/native permit.
"""
from hashlib import sha256
from pathlib import Path

from experiments import h1_parent_snapshot_development_v1 as snapshot

bounded, io, replay = snapshot.bounded, snapshot.io, snapshot.replay
SCHEMA = 'h1_saved_worker_handoff_development_v1'


def implementation_identity():
    return io.digest(io.encode([SCHEMA,snapshot.implementation_identity(),
        sha256(Path(__file__).read_bytes()).hexdigest()]))


class _SavedTransfer:
    """One local call opportunity; consumed even if validation or creation fails."""
    def __init__(self, worker_input, parent, intent_head, source_identity, *,
                 expected_receipt_sha256, expected_request_key, expected_packet_audit, expected_packet):
        self.worker_input = worker_input
        self.receipt_pin = expected_receipt_sha256
        self.request_key, self.packet_audit = expected_request_key, expected_packet_audit
        self.packet = expected_packet
        self.parent = parent
        self.intent_head, self.source_identity = intent_head, source_identity
        self.used = False

    def consume(self, reports):
        if self.used:raise ValueError('saved handoff already consumed')
        self.used = True
        item = self.worker_input
        if type(item) is not snapshot.PendingWorkerInput:raise ValueError('exact typed worker input required')
        item.validate(expected_receipt_sha256=self.receipt_pin)
        p = self.parent
        p._check()
        if (item.packet != self.packet or item.specification != p._spec or item.limits != p._limits):
            raise ValueError('saved worker values differ from live controller input')
        record = bounded.json.loads(item.receipt)
        if (record['parent_identity'] != p.identity or record['intent_head'] != self.intent_head
                or record['source_lineage_identity'] != self.source_identity
                or record['request_key'] != self.request_key or record['packet_audit_identity'] != self.packet_audit
                or record['anchor_record_sha256'] != p._anchor.inspect().record_sha256
                or p._journal.head != self.intent_head or not p._writable):
            raise ValueError('live saved handoff context differs')
        root = p._root/f'hour_{item.packet.relative_hour:03d}_non_authoritative'
        # Exact create-once worker implementation, not an arbitrary callback.
        owner = bounded.prior.AttestedChild(root,item.packet,item.specification,item.limits,
            parent_intent_head=self.intent_head,source_lineage_identity=self.source_identity,create=True)
        try:
            count = 0
            for raw in reports:
                if count >= record['stage_slots']:raise ValueError('extra saved report')
                owner.record_report(raw,expected_head=owner.head)
                count += 1
            if count != record['stage_slots']:raise ValueError('incomplete saved report prefix')
            return owner.finish(expected_head=owner.head)
        finally:
            owner.close()

    __copy__ = bounded.chunks.DevelopmentH1ChunkJournal.__copy__
    __deepcopy__ = bounded.chunks.DevelopmentH1ChunkJournal.__deepcopy__
    __reduce_ex__ = bounded.chunks.DevelopmentH1ChunkJournal.__reduce_ex__


class LiveSavedController:
    """Own a newly created parent; disk reopening never reconstructs this owner."""
    def __init__(self,root,network,specification,limits,*,origin,upstream_root,
                 config_path,dc_bus,hours=192):
        self._implementation = implementation_identity()
        self._parent = bounded.SavedSourceParent(root,network,specification,limits,
            origin=origin,upstream_root=upstream_root,config_path=config_path,
            dc_bus=dc_bus,hours=hours,create=True)
        self.last_input_receipt = None

    def _check(self):
        if implementation_identity() != self._implementation:
            raise ValueError('saved controller implementation drift')
        self._parent._check()

    def inspect(self):
        self._check()
        return self._parent.inspect()

    def step_saved(self,reports,*,expected_source_identity,expected_head):
        p = self._parent
        with p._guard,replay.guard.solver_calls_forbidden():
            try:
                self._check()
                state,before,previous = p._restore()
                if not p._writable or state.status != 'ready' or state.head != expected_head:
                    raise ValueError('live ready create-owner predecessor required')
                receipt = p._load(state.completed_hours,expected_source_identity)
                packet = p._packet(receipt,state.completed_hours,before,previous)
                p._append(p._intent(state.completed_hours,receipt,packet),receipt.audit_payload)
                head = p._journal.head
                reader = snapshot.open_snapshot(p._declaration,expected_parent_identity=p.identity,
                    expected_anchor_record=p._anchor.inspect().record_sha256)
                try:
                    item = reader.pending_input(expected_head=head,expected_source_identity=receipt.identity,
                        expected_request_key=replay.request_key(packet,p._spec,p._limits),
                        expected_packet_audit=packet.audit_identity)
                finally:
                    reader.close()
                self._check()
                transfer = _SavedTransfer(item,p,head,receipt.identity,
                    expected_receipt_sha256=item.receipt_sha256,
                    expected_request_key=replay.request_key(packet,p._spec,p._limits),
                    expected_packet_audit=packet.audit_identity,expected_packet=packet)
                result = transfer.consume(reports)
                reopened = p._child(state.completed_hours,packet,head,receipt.identity,expected_head=result.head)
                try:
                    if reopened.inspect() != result:raise ValueError('fresh saved worker result differs')
                finally:
                    reopened.close()
                p._restore()  # Revalidate the pinned source after worker completion.
                self._check()
                p._append(p._outcome(state.completed_hours,head,result))
                accepted = p._restore()[0]
                self.last_input_receipt = item.receipt
                return accepted
            except BaseException:
                p._poisoned = True
                raise

    def close(self):self._parent.close()

    __copy__ = bounded.chunks.DevelopmentH1ChunkJournal.__copy__
    __deepcopy__ = bounded.chunks.DevelopmentH1ChunkJournal.__deepcopy__
    __reduce_ex__ = bounded.chunks.DevelopmentH1ChunkJournal.__reduce_ex__
