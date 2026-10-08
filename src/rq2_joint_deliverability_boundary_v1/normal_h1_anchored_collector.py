"""Local durable root integration for the bounded H1 collector."""
from hashlib import sha256
from pathlib import Path

from . import normal_h1_stage_collector as base
from . import normal_h1_attempt_anchor as anchor


def implementation_identity():
    return base.replay.current.source._digest('h1_anchored_collector_development_v1',
        base.implementation_identity(),anchor.implementation_identity(),sha256(Path(__file__).read_bytes()).hexdigest())


class DevelopmentH1AnchoredCollector(base.DevelopmentH1StageCollector):
    """Trust the declared local anchor root; no rollback-proof executable resume."""
    def __init__(self,root,packet,specification,budget,limits,*,anchor_root,
                 parent_intent_head,source_lineage_identity,create=False,expected_anchor_record=None):
        self._anchor_root=str(Path(anchor_root).resolve())
        self._anchor=None
        value=base.declaration(packet,specification,budget,limits,parent_intent_head,source_lineage_identity)
        value.update(anchor_root=self._anchor_root,anchored_implementation=implementation_identity())
        binding=sha256(base.chunks.base._bytes(value)).hexdigest()
        holder=anchor.DevelopmentH1AttemptAnchor(anchor_root,binding,
            max_records=len(value['stage_order'])+4,create=create,
            expected_record_sha256=expected_anchor_record)
        try:
            receipt=holder.inspect()
            if not create and receipt is None:raise ValueError('anchor lacks registry genesis; unresolved attempt')
            super().__init__(root,packet,specification,budget,limits,
                parent_intent_head=parent_intent_head,source_lineage_identity=source_lineage_identity,
                create=create,expected_head=None if create else receipt.registry_head)
            self._anchor=holder
            if create:
                receipt=holder.advance(self._registry.head,sha256(b'genesis').hexdigest(),expected_previous=None)
            holder.confirm(receipt)
        except BaseException:
            holder.close()
            if hasattr(self,'_guard'):self.close()
            raise

    def _declare(self):
        value=super()._declare()
        value.update(anchor_root=self._anchor_root,anchored_implementation=implementation_identity())
        return value

    def _check(self):
        super()._check()
        if self._anchor is not None:
            receipt=self._anchor.inspect()
            if receipt is None or receipt.registry_head!=self._registry.head:
                raise ValueError('current registry lacks fresh durable anchor')
            self._anchor.confirm(receipt)

    def _append(self,metadata):
        if type(self._anchor) is not anchor.DevelopmentH1AttemptAnchor:
            raise ValueError('exact durable anchor required')
        previous=self._registry.head
        prior=self._anchor.inspect()
        if prior is None or prior.registry_head!=previous:raise ValueError('registry not anchored')
        result=super()._append(metadata)
        receipt=self._anchor.advance(self._registry.head,
            sha256(base.chunks.base._bytes(metadata)).hexdigest(),expected_previous=previous)
        self._anchor.confirm(receipt)
        return result

    def run(self,*,expected_head):
        if type(self._anchor) is not anchor.DevelopmentH1AttemptAnchor:
            raise ValueError('exact durable anchor required')
        receipt=self._anchor.inspect()
        if receipt is None or receipt.registry_head!=expected_head:raise ValueError('independent anchored head required')
        self._anchor.confirm(receipt)
        return self._run_checkpoint_development(expected_head=expected_head)

    def close(self):
        try:super().close()
        finally:
            if self._anchor is not None:self._anchor.close()
