"""Real CPython monitoring, tiny legacy digests; no saved replay or native run."""
import json
import sys
import threading

import pytest

from src import staged_rts24_development_v1 as legacy
from src import staged_rts24_shadow_monitor_v2 as shadow


def monitor(n,**kwargs):
    return shadow.ShadowMonitor({}, {},dict(digest_started=n,digest_returned=n,
        parent_json_returns=n,strict_byte_compares=n),**kwargs)


def assert_clean(mon):
    m=sys.monitoring
    assert m.get_tool(mon.TOOL) is None and m.get_events(mon.TOOL)==0
    assert all(m.get_local_events(mon.TOOL,code)==0 for code in mon.local)


def test_start_return_frame_pair_and_direct_alias_are_preserved():
    before=(legacy.digest,legacy.plain,json.dumps)
    direct_alias=legacy.digest
    mon=monitor(2)
    with mon:
        assert legacy.digest({'q':1})==direct_alias({'q':1})
    mon.require_complete()
    assert mon.counts['json_returns']==2
    assert not mon.pending and not mon.first_error
    assert (legacy.digest,legacy.plain,json.dumps)==before
    assert_clean(mon)


def test_callback_serialization_does_not_reenter_or_count_as_legacy_json():
    mon=monitor(1)
    with mon:result=legacy.digest({'x':[1,2,3]})
    assert len(result)==64 and mon.counts['json_returns']==1
    assert mon.counts['strict_byte_compares']==1
    assert_clean(mon)


def test_exact_integer_key_calls_are_compared_strictly(monkeypatch):
    monkeypatch.setattr(shadow.candidate,'_legacy_plain',lambda v:pytest.fail('shadow used public fallback'))
    mon=monitor(2)
    with mon:
        legacy.digest({1:'first','1':'last'})
        legacy.digest({'bounds':{1:(0.,1.),2:(1.,2.)}})
    assert mon.counts['strict_byte_compares']==2 and mon.summary()['first_error'] is None
    assert_clean(mon)


def test_failure_summary_keeps_first_ordinal_and_caller_without_input():
    def caller(value):return legacy.digest(value)
    mon=monitor(3)
    with pytest.raises(shadow.ShadowIncomplete):
        with mon:
            caller({'supported':1});caller({True:2});caller({None:3})
    value=mon.summary();error=value['first_error']
    assert value['counts']['strict_unsupported']==2 and value['counts']['digest_returned']==3
    assert value['counts']['strict_byte_compares']==1 and value['pending']==0 and value['monitor_cleaned'] is True
    assert error==dict(reason='strict_unsupported',function='dumps',digest_ordinal=2,
        caller=caller.__code__.co_filename+'|'+caller.__qualname__+'|'+str(caller.__code__.co_firstlineno),root_type='dict')
    json.dumps(value,allow_nan=False)
    assert mon.context is None and not mon.pending


def test_unknown_root_tag_does_not_inspect_metaclass_names():
    observed=[]
    class Meta(type):
        def __getattribute__(self,name):observed.append(name);raise RuntimeError('no type introspection')
    class Unknown(metaclass=Meta):pass
    assert shadow._root_tag(Unknown())=='unknown_exact_type' and observed==[]


def test_progress_callback_json_is_not_counted_as_legacy_encoding():
    progress=[]
    mon=monitor(128,progress=lambda n:progress.append(json.dumps({'completed':n})))
    with mon:
        for n in range(128):legacy.digest({'x':n})
    assert mon.counts['json_returns']==128 and progress==['{"completed": 128}']
    assert_clean(mon)


@pytest.mark.parametrize('fault',['mismatch','unsupported','observer_error'])
def test_shadow_fault_latches_without_altering_legacy_result(monkeypatch,fault):
    expected=legacy.digest({'x':1})
    def changed(*args):
        if fault=='unsupported':raise shadow.candidate._Unsupported
        if fault=='observer_error':raise RuntimeError('observer failed')
        return {'different':True}
    monkeypatch.setattr(shadow.candidate,'_walk',changed)
    mon=monitor(1);observed=[]
    with pytest.raises(shadow.ShadowIncomplete):
        with mon:observed.append(legacy.digest({'x':1}))
    assert observed==[expected] and mon.first_error is not None
    assert_clean(mon)


def test_legacy_exception_is_not_replaced_by_shadow_validation():
    mon=monitor(1)
    with pytest.raises(ValueError,match='Out of range float values'):
        with mon:legacy.digest({'x':float('nan')})
    assert mon.counts['legacy_unwind']>=1
    with pytest.raises(shadow.ShadowIncomplete):mon.require_complete()
    assert_clean(mon)


@pytest.mark.parametrize('error',[MemoryError,SystemExit,KeyboardInterrupt,GeneratorExit])
def test_resource_and_control_exceptions_propagate(monkeypatch,error):
    def changed(*a):raise error('abort observer')
    monkeypatch.setattr(shadow.candidate,'_walk',changed)
    mon=monitor(1)
    with pytest.raises(error):
        with mon:legacy.digest({'x':1})
    assert_clean(mon)


@pytest.mark.parametrize('fault',['digest_mask','json_mask','callback','global_mask'])
def test_detach_cannot_be_adopted(fault):
    mon=monitor(1);m=sys.monitoring
    with pytest.raises(shadow.ShadowIncomplete):
        with mon:
            if fault=='digest_mask':m.set_local_events(mon.TOOL,mon.digest_code,0)
            elif fault=='json_mask':m.set_local_events(mon.TOOL,mon.dumps_code,0)
            elif fault=='callback':m.register_callback(mon.TOOL,m.events.PY_RETURN,None)
            else:m.set_events(mon.TOOL,0)
            legacy.digest({'x':1})
    assert_clean(mon)


def test_preexisting_tool_and_profile_are_refused_without_overwrite():
    m=sys.monitoring;m.use_tool_id(3,'foreign-tool')
    try:
        with pytest.raises(shadow.ShadowIncomplete):
            with monitor(1):pass
        assert m.get_tool(3)=='foreign-tool'
    finally:m.free_tool_id(3)
    def profiler(frame,event,arg):pass
    sys.setprofile(profiler)
    try:
        with pytest.raises(shadow.ShadowIncomplete):
            with monitor(1):pass
        assert sys.getprofile() is profiler
    finally:sys.setprofile(None)


def test_registered_forbidden_route_stops_before_body():
    body=[]
    def would_publish():body.append('effect')
    mon=shadow.ShadowMonitor({}, {'publication':would_publish},{})
    with pytest.raises(shadow.ForbiddenEffect):
        with mon:would_publish()
    assert not body and mon.counts['forbidden/publication']==1
    assert_clean(mon)


@pytest.mark.parametrize('residue',['callback','local_mask'])
def test_released_tool_residue_is_refused_and_preserved(residue):
    m=sys.monitoring;mon=monitor(1)
    def callback(*args):pass
    m.use_tool_id(mon.TOOL,'prior-owner')
    if residue=='callback':m.register_callback(mon.TOOL,m.events.PY_RETURN,callback)
    else:m.set_local_events(mon.TOOL,mon.digest_code,m.events.PY_RETURN)
    m.free_tool_id(mon.TOOL)
    try:
        with pytest.raises(shadow.ShadowIncomplete):
            with mon:pass
        assert m.get_tool(mon.TOOL) is None
        if residue=='callback':assert m.register_callback(mon.TOOL,m.events.PY_RETURN,None) is callback
        else:assert m.get_local_events(mon.TOOL,mon.digest_code)==m.events.PY_RETURN
    finally:
        m.use_tool_id(mon.TOOL,'test-cleanup')
        m.register_callback(mon.TOOL,m.events.PY_RETURN,None);m.set_local_events(mon.TOOL,mon.digest_code,0)
        m.free_tool_id(mon.TOOL)


@pytest.mark.parametrize('foreign',['tool','profile','trace'])
def test_foreign_scope_added_during_window_is_refused_and_preserved(foreign):
    mon=monitor(1);m=sys.monitoring
    def trace(frame,event,arg):return trace
    try:
        with pytest.raises(shadow.ShadowIncomplete):
            with mon:
                legacy.digest({'x':1})
                if foreign=='tool':m.use_tool_id(4,'late-foreign')
                elif foreign=='profile':sys.setprofile(trace)
                else:sys.settrace(trace)
        if foreign=='tool':assert m.get_tool(4)=='late-foreign'
        elif foreign=='profile':assert sys.getprofile() is trace
        else:assert sys.gettrace() is trace
    finally:
        if foreign=='tool':m.free_tool_id(4)
        elif foreign=='profile':sys.setprofile(None)
        else:sys.settrace(None)
    assert_clean(mon)


def test_stage_counts_and_incomplete_call_budget_are_enforced():
    def stage():return legacy.digest({'x':1})
    mon=shadow.ShadowMonitor({'stage':stage},{},dict(digest_started=1,digest_returned=1,
        parent_json_returns=1,strict_byte_compares=1,**{'stage/started':1,'stage/returned':1}))
    with mon:stage()
    assert_clean(mon)
    missing=monitor(2)
    with pytest.raises(shadow.ShadowIncomplete):
        with missing:legacy.digest({'x':1})
    assert_clean(missing)


def test_foreign_thread_target_is_unresolved_without_changing_old_result():
    answers=[];mon=monitor(0)
    with pytest.raises(shadow.ShadowIncomplete):
        with mon:
            thread=threading.Thread(target=lambda:answers.append(legacy.digest({'x':1})))
            thread.start();thread.join()
    assert len(answers)==1 and mon.first_error['reason']=='observer_error'
    assert_clean(mon)


def test_cleanup_failure_cannot_claim_complete(monkeypatch):
    mon=monitor(1);m=sys.monitoring;original=m.free_tool_id
    def failed(tool):raise OSError('simulated free failure')
    try:
        with pytest.raises(shadow.ShadowIncomplete):
            with mon:
                legacy.digest({'x':1});monkeypatch.setattr(m,'free_tool_id',failed)
        assert not mon.cleaned and mon.counts['cleanup_error']==1
    finally:
        monkeypatch.setattr(m,'free_tool_id',original);original(mon.TOOL)
    assert_clean(mon)
