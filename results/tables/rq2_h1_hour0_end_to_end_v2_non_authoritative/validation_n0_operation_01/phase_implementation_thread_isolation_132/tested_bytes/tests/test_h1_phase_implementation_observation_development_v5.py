"""Original private coordinator, controlled identity oracle, actual data handles.

These tests establish observation/failure boundaries, not a genuine N0 run.
"""
from dataclasses import replace
from threading import Event, Lock, Thread

import pytest

from tests.test_h1_phase_dependency_window_faults_development_v1 import tiny
from tests.test_h1_phase_manifest_segment_faults_development_v1 import shared
from tests.test_h1_bootstrap_phase_segments_development_v5 import coordinator


def closed(c, *, complete):
    value = c.receipt(c.owner)
    assert value['all_segments_closed'] and value['lifecycle_complete'] is complete
    assert value['implementation_observation'] == 'segment_entry_exit'
    assert value['per_call_implementation_freshness'] is False
    assert value['implementation_path_ABA_covered'] is False
    assert not c.shared.tiny.state['live']
    assert c.shared.tiny.m._CLEANUP_DIAGNOSTICS()['active_operations'] == 0
    return value


def test_identity_reuse_is_per_segment_and_each_call_still_checks_runtime(coordinator):
    c = coordinator
    assert c.identity() == 'a'*64 and c.state['raw_calls'] == 1
    def body():
        before = c.state['runtime_calls']
        assert all(c.identity() == 'a'*64 for _ in range(100))
        assert c.state['runtime_calls'] - before >= 100
        assert c.state['raw_calls'] == 2
        thread = Thread(target=lambda: c.identity())
        thread.start();thread.join(timeout=5)
        assert not thread.is_alive() and c.state['raw_calls'] == 3
        assert c.run(c.owner, lambda: c.identity()) == 'a'*64
    c.run(c.owner, body, declaration=c.declaration)
    value = closed(c, complete=True)
    observation = value['segments'][0]['implementation_observation']
    assert observation['entry_raw_attempts'] == observation['exit_raw_attempts'] == 1
    assert observation['cached_calls'] == 101 and observation['entry_exit_equal']
    assert c.state['raw_calls'] == 4
    assert c.identity() == 'a'*64 and c.state['raw_calls'] == 5


def test_callback_gap_and_nested_child_have_distinct_identity_bookends(coordinator):
    c = coordinator
    def body():
        def callback():
            assert not c.shared.tiny.state['live']
            assert c.identity() == 'a'*64  # Outside the outer segment.
            assert c.run(c.owner, lambda: c.identity(), site='callback child') == 'a'*64
            assert not c.shared.tiny.state['live']
        c.external(c.owner, callback)
        assert c.identity() == 'a'*64
    c.run(c.owner, body, declaration=c.declaration)
    value = closed(c, complete=True)
    assert c.state['raw_calls'] == 7 and value['segments_opened'] == 3
    assert all(x['implementation_observation']['entry_exit_equal'] for x in value['segments'])


def test_two_owners_restore_the_correct_outer_identity_frame(coordinator):
    c = coordinator;other = type(c.owner)()
    declaration = replace(c.declaration, study_root=str(c.root.parent/'second_non_authoritative'))
    other.declaration=declaration;other._operation=other._original_operation=Lock()
    other.closed=other.poisoned=False
    def body():
        assert c.identity() == 'a'*64
        c.run(other, lambda: [c.identity() for _ in range(7)], declaration=declaration)
        assert c.identity() == 'a'*64
    c.run(c.owner, body, declaration=c.declaration)
    outer = closed(c, complete=True);inner = c.receipt(other)
    assert c.state['raw_calls'] == 4
    assert outer['segments'][0]['implementation_observation']['cached_calls'] == 2
    assert inner['segments'][0]['implementation_observation']['cached_calls'] == 7


@pytest.mark.parametrize('body_primary', [False, True])
def test_overlapping_creator_threads_can_close_in_either_order(coordinator, body_primary):
    c=coordinator;a_entered=Event();b_entered=Event();a_closed=Event()
    receipts={};errors=[];primary=RuntimeError('thread A body primary')
    def execute(label):
        owner=type(c.owner)()
        declaration=replace(c.declaration,study_root=str(c.root.parent/(label+'_non_authoritative')))
        owner.declaration=declaration;owner._operation=owner._original_operation=Lock()
        owner.closed=owner.poisoned=False
        def body():
            assert c.identity()=='a'*64
            if label=='a':
                a_entered.set();assert b_entered.wait(10)
                assert c.identity()=='a'*64
                if body_primary:raise primary
            else:
                b_entered.set();assert a_closed.wait(10)
                assert c.identity()=='a'*64
        try:
            try:c.run(owner,body,declaration=declaration)
            except BaseException as error:
                if label!='a' or not body_primary or error is not primary:raise
                assert not getattr(error,'__notes__',())
            receipts[label]=c.receipt(owner)
        except BaseException as error:errors.append(error)
        finally:
            if label=='a':a_closed.set()
    a=Thread(target=execute,args=('a',));b=Thread(target=execute,args=('b',))
    a.start();assert a_entered.wait(10);b.start()
    a.join(timeout=20);b.join(timeout=20)
    assert not a.is_alive() and not b.is_alive() and not errors
    assert set(receipts)=={'a','b'} and c.state['raw_calls']==4
    for label,value in receipts.items():
        assert value['all_segments_closed']
        assert value['lifecycle_complete'] is (label!='a' or not body_primary)
        identity=value['segments'][0]['implementation_observation']
        assert identity['cached_calls']==2 and identity['entry_exit_equal']
    assert c.identity()=='a'*64 and c.state['raw_calls']==5
    assert not c.shared.tiny.state['live']
    assert c.shared.tiny.m._CLEANUP_DIAGNOSTICS()['active_operations']==0


@pytest.mark.parametrize('primary', [False, True])
def test_exit_identity_drift_rejects_return_and_preserves_body_primary(coordinator, primary):
    c = coordinator;body_error = RuntimeError('body primary')
    def body():
        c.state['raw_value'] = 'b'*64
        if primary:raise body_error
        return 'must not return'
    with pytest.raises(RuntimeError if primary else ValueError) as caught:
        c.run(c.owner, body, declaration=c.declaration)
    if primary:assert caught.value is body_error and caught.value.__notes__
    value = closed(c, complete=False)
    assert c.owner.poisoned and value['segments'][0]['implementation_observation']['exit_identity'] == 'b'*64
    assert not value['segments'][0]['implementation_observation']['entry_exit_equal']
    assert c.identity() == 'b'*64  # Failure did not leave an active memo.


@pytest.mark.parametrize('primary', [False, True])
def test_exit_raw_exception_and_close_failure_clear_memo_and_allow_cleanup(coordinator, primary):
    c=coordinator;body_error=RuntimeError('body primary');raw_error=OSError('raw exit failure')
    def body():
        c.state['raw_error']=raw_error;c.shared.tiny.state['close_fail']={1}
        if primary:raise body_error
    with pytest.raises(RuntimeError if primary else OSError) as caught:
        c.run(c.owner,body,declaration=c.declaration)
    assert caught.value is (body_error if primary else raw_error)
    assert c.receipt(c.owner)['pending_cleanup_windows'] == 1
    with pytest.raises(OSError) as outside: c.identity()
    assert outside.value is raw_error
    c.state['raw_error']=None;c.cleanup(c.owner)
    closed(c,complete=False)


@pytest.mark.parametrize('during_callback', [False, True])
def test_implementation_drift_never_returns_a_successful_retention(coordinator, during_callback):
    c=coordinator;called=[]
    def callback():
        called.append(True);c.root.mkdir();(c.root/'retained.json').write_bytes(b'{}')
        c.state['raw_value']='b'*64
        return 'retained but caller must not accept'
    def body():
        if not during_callback:c.state['raw_value']='b'*64
        return c.external(c.owner,callback)
    with pytest.raises(ValueError,match='implementation'):
        c.run(c.owner,body,declaration=c.declaration)
    assert bool(called) is during_callback
    assert (c.root/'retained.json').exists() is during_callback
    closed(c,complete=False)
    assert c.identity() == 'b'*64


@pytest.mark.parametrize('where', ['plan', 'exit_runtime'])
def test_plan_or_runtime_failure_still_discards_identity_and_closes_handles(coordinator, where):
    c=coordinator;error=ValueError('injected '+where)
    if where == 'plan':c.state['plan_error']=error
    def body():c.state['runtime_error']=error
    with pytest.raises(ValueError) as caught:
        c.run(c.owner,body,declaration=c.declaration)
    assert caught.value is error
    value=closed(c,complete=False)
    c.state['runtime_error']=None
    assert c.identity() == 'a'*64
    observation=value['segments'][0]['implementation_observation']
    assert observation['entry_raw_attempts']==1
    assert observation['exit_raw_attempts']==(1 if where=='plan' else 0)
