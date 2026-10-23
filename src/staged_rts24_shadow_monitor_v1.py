"""Code-local CPython monitoring; legacy execution remains the decision maker."""
from collections import Counter
from hashlib import sha256
import json
import sys
import threading

from src import staged_rts24_development_v1 as legacy,staged_rts24_plain_v1 as candidate


class ShadowIncomplete(ValueError):pass
class ForbiddenEffect(BaseException):pass


class ShadowMonitor:
    TOOL=3
    NAME='electricity-grid-saved-digest-shadow-v1'

    def __init__(self,stages,forbidden,expected,progress=None):
        self.stages={f.__code__ if callable(f) else f:label for label,f in stages.items()}
        self.forbidden={f.__code__:label for label,f in forbidden.items()}
        self.expected=dict(expected);self.progress=progress
        self.digest=legacy.digest;self.dumps=json.dumps
        self.digest_code,self.dumps_code=self.digest.__code__,self.dumps.__code__
        self.counts=Counter();self.callers=Counter();self.pending={};self.first_error=None
        self.thread=threading.get_ident();self.entered=False;self.cleaned=False
        self.installed=[];self.activated=[]
        events=sys.monitoring.events
        self.local={code:events.PY_START|events.PY_RETURN for code in self.stages}
        self.local.update({code:events.PY_START for code in self.forbidden})
        self.local[self.digest_code]=events.PY_START|events.PY_RETURN
        self.local[self.dumps_code]=events.PY_RETURN
        self.callbacks={events.PY_START:self._start,events.PY_RETURN:self._returned,events.PY_UNWIND:self._unwind}

    def _fail(self,reason,code=None):
        self.counts[reason]+=1
        if self.first_error is None:
            self.first_error=dict(reason=reason,function=code.co_qualname if code else None)

    def _frame_key(self,frame,code):
        if frame.f_code is not code:raise ShadowIncomplete('monitor callee frame differs')
        if threading.get_ident()!=self.thread:raise ShadowIncomplete('unexpected execution thread')
        return self.thread,id(frame)

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
                self.pending[key]=dict(json_returns=0,old_sha=None,new_sha=None)
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
                item=self.pending[(self.thread,id(parent))]
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
                item=self.pending.pop(key)
                if item['json_returns']!=1 or item['old_sha'] is None:raise ShadowIncomplete('missing digest JSON sample')
                if type(value) is not str or value!=item['old_sha']:self._fail('legacy_digest_mismatch',code)
                if item['new_sha'] is not None and value!=item['new_sha']:self._fail('candidate_digest_mismatch',code)
                if self.progress is not None and self.counts['digest_returned']%128==0:self.progress(self.counts['digest_returned'])
            elif code in self.stages:self.counts[self.stages[code]+'/returned']+=1
        except MemoryError:raise
        except Exception:self._fail('observer_error',code)

    def _unwind(self,code,offset,error):
        if code is self.digest_code or code is self.dumps_code or code in self.stages:
            self._fail('legacy_unwind',code)

    def __enter__(self):
        m=sys.monitoring
        if self.entered or any(m.get_tool(i) is not None or m.get_events(i) for i in range(6)):
            raise ShadowIncomplete('fresh unused monitoring scope required')
        if any(m.get_local_events(self.TOOL,code) for code in self.local):raise ShadowIncomplete('stale local monitoring mask')
        if sys.getprofile() is not None or sys.gettrace() is not None:raise ShadowIncomplete('foreign tracing/profiling scope')
        m.use_tool_id(self.TOOL,self.NAME);self.entered=True
        try:
            for event,callback in self.callbacks.items():
                previous=m.register_callback(self.TOOL,event,callback)
                if previous is not None:
                    m.register_callback(self.TOOL,event,previous)
                    raise ShadowIncomplete('stale monitoring callback')
                self.installed.append(event)
            m.set_events(self.TOOL,m.events.PY_UNWIND)
            for code,mask in self.local.items():
                m.set_local_events(self.TOOL,code,mask);self.activated.append(code)
        except BaseException:
            self._cleanup();raise
        return self

    def _intact(self):
        m=sys.monitoring
        if sys.getprofile() is not None or sys.gettrace() is not None:return False
        if any(m.get_tool(i) is not None or m.get_events(i) for i in range(6) if i!=self.TOOL):return False
        if m.get_tool(self.TOOL)!=self.NAME or m.get_events(self.TOOL)!=m.events.PY_UNWIND:return False
        if legacy.digest is not self.digest or json.dumps is not self.dumps:return False
        if any(m.get_local_events(self.TOOL,code)!=mask for code,mask in self.local.items()):return False
        # The API has no callback getter. Re-registering the same object returns
        # the prior object and therefore detects detach/replacement at closure.
        return all(m.register_callback(self.TOOL,event,callback) is callback for event,callback in self.callbacks.items())

    def _cleanup(self):
        m=sys.monitoring;errors=[]
        for code in self.activated:
            try:m.set_local_events(self.TOOL,code,0)
            except BaseException as exc:errors.append(type(exc).__name__)
        try:m.set_events(self.TOOL,0)
        except BaseException as exc:errors.append(type(exc).__name__)
        for event in self.installed:
            try:m.register_callback(self.TOOL,event,None)
            except BaseException as exc:errors.append(type(exc).__name__)
        try:m.free_tool_id(self.TOOL)
        except BaseException as exc:errors.append(type(exc).__name__)
        self.cleaned=not errors and m.get_tool(self.TOOL) is None and m.get_events(self.TOOL)==0
        if errors:self._fail('cleanup_error')

    def __exit__(self,kind,value,tb):
        try:
            if not self._intact():self._fail('monitor_detached')
        except BaseException:self._fail('monitor_detached')
        finally:self._cleanup()
        if kind is None:self.require_complete()
        return False

    def require_complete(self):
        if (not self.cleaned or self.first_error is not None or self.pending
            or any(self.counts[k]!=v for k,v in self.expected.items())):
            raise ShadowIncomplete('shadow comparison incomplete: '+str(self.first_error))

    def summary(self):
        return dict(authority='DRAFT_NONAUTHORITATIVE',counts=dict(self.counts),callers=dict(self.callers),
            pending=len(self.pending),first_error=self.first_error,monitor_cleaned=self.cleaned,
            scope='actual_legacy_JSON_bytes_and_digest_returns_not_CAS_blob_identity_or_speedup')
