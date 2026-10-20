"""Single full replay per protected readonly child inspection scope."""
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

from . import normal_h1_anchored_collector as legacy

base=legacy.base
sink=base.sink
chunks=base.chunks
SCHEMA='h1_scoped_readonly_child_inspection_development_v1'
_DEFERRED=object()


@dataclass(frozen=True,init=False)
class H1ScopedChildAudit(base.replay.current.source._Owned):
    auditor_identity: str
    inspection: base.H1CollectorInspection


class _ConstructionToken:
    def __init__(self,owner,fingerprint):
        self.owner,self.fingerprint=owner,fingerprint
        self.consumed=False


def implementation_identity():
    return base.replay.current.source._digest(SCHEMA,legacy.implementation_identity(),
        sha256(Path(__file__).read_bytes()).hexdigest())


class _ConstructionArchive(base._CollectorArchive):
    def __init__(self,*args,**kwargs):
        try:
            super().__init__(*args,**kwargs)
            if type(self._state) is not sink.H1IncrementalArchiveInspection:
                raise ValueError('full construction inspection required')
            self._token=_ConstructionToken(self,self._token_fingerprint())
        except BaseException:
            if hasattr(self,'_journal'):
                self._poisoned=self._journal._poisoned=True
                self.close()
            raise

    def _token_fingerprint(self):
        return base.replay.current.source._digest(implementation_identity(),self._binding,self._key,
            self._packet.audit_identity,self._cache_digest,self._epoch,self._writer.total_changes,
            self._journal._file_identity,id(self._writer))

    def _restore(self):
        # No state is exposed by the base constructor. The incremental constructor
        # immediately performs the full replay under its persistent writer lock.
        if self._writer is None:return _DEFERRED
        return super()._restore()

    def inspect(self):
        if self._token is None:return super().inspect()
        with self._guard:
            token,self._token=self._token,None
            try:
                if (type(token) is not _ConstructionToken or token.consumed or token.owner is not self
                        or token.fingerprint!=self._token_fingerprint()):
                    raise ValueError('owned construction token changed')
                token.consumed=True
                self._verify_cache()
                self._writer.execute('BEGIN IMMEDIATE')
                try:
                    self._fast_check(self._writer,self._counts_cache,self._tail_cache,self._changes_cache)
                    result=self._state
                    self._check()
                finally:self._writer.execute('ROLLBACK')
                self._check()
                return result
            except BaseException:
                self._poisoned=self._journal._poisoned=True
                raise


class DevelopmentH1ScopedChildInspection(base.DevelopmentH1StageCollector):
    """Read an existing exact legacy binding; never create, append, or execute.

    Construction through first inspect is one verification scope. Its single full
    numerical replay remains protected by the persistent SQLite epoch and lease.
    Later inspect calls independently perform full replay again.
    """
    def __init__(self,root,packet,specification,budget,limits,*,anchor_root,
                 parent_intent_head,source_lineage_identity,expected_anchor_record):
        self._packet,self._spec,self._budget,self._limits=deepcopy((packet,specification,budget,limits))
        self._parent,self._source=parent_intent_head,source_lineage_identity
        self._anchor_root=str(Path(anchor_root).resolve())
        self._reader_identity=implementation_identity()
        self._guard=chunks._Exclusive()
        self._closed=self._poisoned=self._armed=False
        self._registry=self._child=self._anchor=None
        self._declaration=self._declare()
        self._binding=sha256(chunks.base._bytes(self._declaration)).hexdigest()
        n=len(self._declaration['stage_order'])
        base.native._pin(expected_anchor_record)
        try:
            self._anchor=legacy.anchor.DevelopmentH1AttemptAnchor(anchor_root,self._binding,
                max_records=n+4,expected_record_sha256=expected_anchor_record)
            retained=self._anchor.inspect()
            if retained is None:raise ValueError('existing anchored collector required')
            self._registry=chunks.DevelopmentH1ChunkJournal(root,
                chunks.ChunkContentBudget(n+3,chunks.METADATA_BYTES,(n+3)*chunks.METADATA_BYTES),
                binding_identity=self._binding,expected_head=retained.registry_head)
            self._attempt=base.replay.current.source._digest(base.SCHEMA,self._registry.identity,'attempt')
            observed=self._registry.inspect()
            if not observed.events:raise ValueError('existing durable attempt intent required')
            last=json.loads(self._registry.event_metadata(observed.events,expected_head=observed.head))
            if last.get('kind')=='child_checkpoint':
                candidates=[last['expected_child_head'],last['previous_child_head']]
            elif last.get('kind')=='attempt_outcome':candidates=[last['child_head']]
            elif last.get('kind')=='attempt_intent':candidates=[last['child_genesis_head']]
            else:raise ValueError('known anchored collector record required')
            for index,candidate in enumerate(candidates):
                try:
                    self._child=_ConstructionArchive(Path(root)/'stages_non_authoritative',
                        self._packet,self._spec,self._limits,parent_intent_head=self._parent,
                        source_lineage_identity=self._source,collector_binding=self._attempt,expected_head=candidate)
                    break
                except ValueError:
                    if index==len(candidates)-1:raise
            self._check()
        except BaseException:
            self.close()
            raise

    def _declare(self):
        value=super()._declare()
        value.update(anchor_root=self._anchor_root,anchored_implementation=legacy.implementation_identity())
        return value

    def _check(self):
        super()._check()
        if implementation_identity()!=self._reader_identity:raise ValueError('readonly inspection implementation drift')
        receipt=self._anchor.inspect()
        if receipt is None or receipt.registry_head!=self._registry.head:raise ValueError('readonly registry anchor drift')
        self._anchor.confirm(receipt)

    def inspect(self):
        result=super().inspect()
        return base.replay.current.source._owned(H1ScopedChildAudit,
            auditor_identity=self._reader_identity,inspection=result)

    def run(self,**kwargs):
        raise TypeError('readonly child inspection cannot execute')

    def _append(self,*args,**kwargs):
        raise TypeError('readonly child inspection cannot append')

    def close(self):
        try:super().close()
        finally:
            if self._anchor is not None:self._anchor.close()
