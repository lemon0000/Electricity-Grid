"""Source-parent successor using a bounded readonly scope for child reopens."""
from hashlib import sha256
from pathlib import Path

from . import normal_h1_anchored_source_episode as old
from . import normal_h1_scoped_child_inspection as reader


def implementation_identity():
    return old.source._digest('h1_scoped_source_parent_development_v1',old.implementation_identity(),
        reader.implementation_identity(),sha256(Path(__file__).read_bytes()).hexdigest())


class _ParentAuditAdapter:
    def __init__(self,owner):self._owner=owner

    def inspect(self):
        result=self._owner.inspect()
        if type(result) is not reader.H1ScopedChildAudit or result.auditor_identity!=reader.implementation_identity():
            raise ValueError('independent scoped auditor identity required')
        inner=result.inspection
        if type(inner) is not reader.base.H1CollectorInspection or any(
                getattr(inner,name) is not False for name in (
                    'resumable','source_authenticated','native_execution_authenticated',
                    'parent_intent_verified','published','formal_result','formal_execution_ready')):
            raise ValueError('exact non-authoritative collector inspection required')
        return inner

    def close(self):self._owner.close()


class DevelopmentH1ScopedSourceEpisode(old.DevelopmentH1AnchoredSourceEpisode):
    def _declare(self):
        value=super()._declare()
        value['scoped_parent_implementation']=implementation_identity()
        return value

    def _collector(self,hour,packet,intent_head,lineage,*,create=False,expected_anchor_record=None):
        if create:
            return super()._collector(hour,packet,intent_head,lineage,create=True)
        root,anchor_root=self._paths(hour)
        return _ParentAuditAdapter(reader.DevelopmentH1ScopedChildInspection(root,packet,self._spec,self._hour_budget,self._limits,
            anchor_root=anchor_root,parent_intent_head=intent_head,source_lineage_identity=lineage,
            expected_anchor_record=expected_anchor_record))
