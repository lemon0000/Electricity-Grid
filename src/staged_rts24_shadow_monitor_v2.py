"""Strict str/int-key successor with bounded failure context, preserving v1."""
from hashlib import sha256
import sys

from src import staged_rts24_shadow_monitor_v1 as base
from src import staged_rts24_plain_v2 as candidate

legacy=base.legacy
ShadowIncomplete=base.ShadowIncomplete
ForbiddenEffect=base.ForbiddenEffect


def _root_tag(value):
    kind=type(value)
    for cls,name in ((str,'str'),(int,'int'),(float,'float'),(bool,'bool'),(type(None),'none'),
        (dict,'dict'),(list,'list'),(tuple,'tuple'),(candidate.Fraction,'Fraction')):
        if kind is cls:return name
    for cls in candidate.CLASSES.values():
        if kind is cls:return 'registered/'+cls.__name__
    return 'unknown_exact_type'


class ShadowMonitor(base.ShadowMonitor):
    NAME='electricity-grid-saved-digest-shadow-v2'

    def __init__(self,stages,forbidden,expected,progress=None):
        super().__init__(stages,forbidden,expected,progress)
        self.context=None

    def _fail(self,reason,code=None):
        first=self.first_error is None
        super()._fail(reason,code)
        if first and self.context is not None:self.first_error.update(self.context)

    def _start(self,code,offset):
        if code in self.forbidden:
            self._fail('forbidden/'+self.forbidden[code],code)
            raise ForbiddenEffect('read-only shadow forbids '+self.forbidden[code])
        try:
            frame=sys._getframe(1);key=self._frame_key(frame,code)
            if code is self.digest_code:
                self.counts['digest_started']+=1
                if key in self.pending:raise ShadowIncomplete('duplicate digest frame')
                caller=frame.f_back.f_code
                label=caller.co_filename+'|'+caller.co_qualname+'|'+str(caller.co_firstlineno)
                self.callers[label]+=1
                context=dict(digest_ordinal=self.counts['digest_started'],caller=label,root_type=_root_tag(frame.f_locals['value']))
                self.pending[key]=dict(json_returns=0,old_sha=None,new_sha=None,context=context)
            elif code in self.stages:self.counts[self.stages[code]+'/started']+=1
        except MemoryError:raise
        except Exception:self._fail('observer_error',code)

    def _returned(self,code,offset,value):
        try:
            frame=sys._getframe(1);key=self._frame_key(frame,code)
            if code is self.dumps_code:
                self.counts['json_returns']+=1
                parent=frame.f_back
                if parent is None or parent.f_code is not self.digest_code:return
                self.counts['parent_json_returns']+=1
                item=self.pending[(self.thread,id(parent))];self.context=item['context']
                item['json_returns']+=1
                if item['json_returns']!=1 or type(value) is not str:raise ShadowIncomplete('digest JSON pairing differs')
                old_bytes=value.encode('utf-8');item['old_sha']=sha256(old_bytes).hexdigest()
                try:plain=candidate._walk(parent.f_locals['value'],0,set())
                except candidate._Unsupported:
                    self._fail('strict_unsupported',code);return
                new_bytes=self.dumps(plain,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
                item['new_sha']=sha256(new_bytes).hexdigest();self.counts['strict_byte_compares']+=1
                if new_bytes!=old_bytes:self._fail('byte_mismatch',code)
            elif code is self.digest_code:
                self.counts['digest_returned']+=1
                item=self.pending.pop(key);self.context=item['context']
                if item['json_returns']!=1 or item['old_sha'] is None:raise ShadowIncomplete('missing digest JSON sample')
                if type(value) is not str or value!=item['old_sha']:self._fail('legacy_digest_mismatch',code)
                if item['new_sha'] is not None and value!=item['new_sha']:self._fail('candidate_digest_mismatch',code)
                if self.progress is not None and self.counts['digest_returned']%128==0:self.progress(self.counts['digest_returned'])
            elif code in self.stages:self.counts[self.stages[code]+'/returned']+=1
        except MemoryError:raise
        except Exception:self._fail('observer_error',code)
        finally:self.context=None
