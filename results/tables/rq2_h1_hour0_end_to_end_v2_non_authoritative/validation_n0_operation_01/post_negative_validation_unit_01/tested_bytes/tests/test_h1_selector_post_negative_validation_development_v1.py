"""Standalone post-negative scope with real Parent method code, fake transport.

No Parent credential, native Job, formal result or full end-to-end claim.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from threading import Lock, Thread, get_ident
from types import FunctionType

import pytest

from experiments import h1_selector_parent_controller_development_v2 as predecessor
from tests.h1_hour0_synthetic_harness_v2 import load
from tests.test_h1_selector_parent_validation_operation_development_v2 import make_case, encode


@contextmanager
def make_post_case(tmp_path,monkeypatch,*,exact_source=None,source_binding=None):
    fixture=make_case(tmp_path,monkeypatch,exact_source=exact_source,source_binding=source_binding)
    case=next(fixture)
    try:
        case.abort(case.host,RuntimeError('detach explicit fake Handoff'))
        case.release()
        parent=sys.modules[case.module._HOST].parent
        parent.implementation_identity=lambda:'explicit-fake-parent-transport'
        parent.Parent._enter=FunctionType(predecessor.Parent._enter.__code__,{},'_enter')
        for index,obj in enumerate(case.parents):
            obj._pid,obj._thread=os.getpid(),get_ident()
            obj._reference_held=False
            declaration=json.loads(obj._raw)
            declaration['declaration'].update(role='reference' if index==0 else 'actual',
                lane_id=None if index==0 else str(index-1))
            obj._raw=encode(declaration)
            obj._issued.role='reference' if index==0 else 'actual'
            obj._issued_bytes=parent._completion_bytes(obj._issued)
        case.parent=parent
        case.reference=(case.ref,case.ref._issued)
        case.mapping={str(index):(obj,obj._issued) for index,obj in enumerate(case.actuals)}
        def install():
            case.operation=load(str(Path(predecessor.__file__).with_name(
                'h1_selector_post_negative_validation_development_v1.py')),
                'experiments.h1_selector_post_negative_validation_development_v1',monkeypatch,
                {'h1_selector_parent_controller_development_v2':parent,
                 'h1_selector_parent_validation_operation_development_v2':case.module})
        case.install=install
        install()
        case.invoke=lambda:case.operation.validate_completed_bundle(case.reference,case.mapping)
        yield case
    finally:
        fixture.close()


@pytest.fixture
def case(tmp_path,monkeypatch):
    with make_post_case(tmp_path,monkeypatch) as case:yield case


def released(case):
    assert all(not obj._guard.locked() and obj._reference_held is False for obj in case.parents)


def test_three_rounds_keep_all_retained_bodies_and_take_fresh_bookends(case):
    for index in range(3):
        receipt=case.invoke()
        assert len(case.values)==2*(index+1)
        assert (receipt['top_level_validations'],receipt['parent_validations'],receipt['source_prepares'],
            receipt['borrowed_source_returns'])==(4,10,2,160)
        assert [site['retained_bodies'] for site in receipt['parent_sites']]==[7,1,1,1]
        assert [site['root'] for site in receipt['parent_sites']]==[str(obj.root) for obj in case.parents]
        assert receipt['source_windows'][0]['window_cache_entry_cleared']
        assert all(receipt[key] is True for key in ('complete','closed','outer_cleanup_complete',
            'operation_registry_cleared','all_owned_guards_released','all_reference_marks_cleared'))
        declaration=receipt['declaration']
        assert declaration['source_result_reuse_scope']=='single_synchronous_window_without_external_callback'
        assert declaration['cleared_state_scope']=='window_cache_entry_only'
        assert all(declaration[key] is False for key in ('same_predecessor_per_nested_source_io_schedule',
            'same_predecessor_failure_order','cross_window_source_reuse',
            'unobserved_between_bookends_ABA_covered','complete_dynamic_input_closure_proved',
            'full_source_object_graph_destroyed'))
        assert all(receipt[key] is False for key in ('formal_result','resource_admission','native_execution_authorized'))
        assert json.loads(json.dumps(receipt))==receipt
        receipt['source_windows'].clear()  # A plain detached value, not internal authority.
        released(case)


@pytest.mark.parametrize('fault',['role','lane','reference','reference_receipt','duplicate_owner',
    'duplicate_guard','issued','issued_bytes','source_binding','pid','thread','incomplete','marked'])
def test_bad_admission_has_zero_source_io(case,fault):
    obj=case.actuals[0]
    if fault=='role':obj._issued.role='reference'
    elif fault=='lane':case.mapping={'wrong':case.mapping['0'],'1':case.mapping['1'],'2':case.mapping['2']}
    elif fault=='reference':obj._reference_owner=case.actuals[1]
    elif fault=='reference_receipt':obj._reference_completion=case.actuals[1]._issued
    elif fault=='duplicate_owner':case.mapping['1']=case.mapping['0']
    elif fault=='duplicate_guard':case.actuals[1]._guard=obj._guard
    elif fault=='issued':case.mapping['0']=(obj,deepcopy(obj._issued))
    elif fault=='issued_bytes':obj._issued_bytes=b'changed'
    elif fault=='source_binding':
        raw=json.loads(obj._raw);raw['declaration']['source_binding']['extra']='changed';obj._raw=encode(raw)
    elif fault=='pid':obj._pid+=1
    elif fault=='thread':obj._thread+=1
    elif fault=='incomplete':obj._state='prepared'
    elif fault=='marked':obj._reference_held=True
    with pytest.raises((ValueError,TypeError)):case.invoke()
    assert not case.values
    if fault=='marked':obj._reference_held=False
    released(case)


@pytest.mark.parametrize('index',range(4))
def test_partial_guard_acquisition_only_releases_owned_guards(case,index):
    order=[*case.actuals,case.ref]
    blocked=order[index]._guard;blocked.acquire()
    try:
        with pytest.raises(ValueError,match='already active'):case.invoke()
        assert blocked.locked() and not case.values
        assert all(not obj._guard.locked() for obj in order if obj._guard is not blocked)
        assert all(obj._reference_held is False for obj in order)
    finally:blocked.release()
    # No failed-operation cache survives.
    assert case.invoke()['complete']
    released(case)


@pytest.mark.parametrize('at',[1,2])
def test_source_entry_and_tail_errors_release_everything(case,at):
    failure=RuntimeError('source bookend failure')
    def fault(number):
        if number==at:raise failure
    case.faults['full_source']=fault
    with pytest.raises(RuntimeError) as caught:case.invoke()
    assert caught.value is failure
    assert len(case.values)==at-1
    released(case)


def test_body_error_skips_tail_and_preserves_first_error(case):
    case.faults['inspection']=str(case.actuals[1].worker_root)
    with pytest.raises(RuntimeError,match='inspection tail fault'):case.invoke()
    assert len(case.values)==1
    released(case)


@pytest.mark.parametrize('change',['tail_fields','retained_fields','raw','issued','guard','reference','binding','class'])
def test_mid_window_drift_fails_and_cleans_original_resources(case,change):
    original_guards=[obj._guard for obj in case.parents]
    if change=='tail_fields':case.faults['tail_difference']=True
    elif change=='class':
        old_type=case.source.ExactSourceCurrent
        # Same serialized name and fields, distinct actual nested class object.
        @dataclass(frozen=True)
        class Twin:
            value:list
        Twin.__module__=old_type.__module__;Twin.__qualname__=old_type.__qualname__
        case.faults['source_value']=lambda value,number:value if number==1 else Twin(value.value)
    else:
        def hook():
            case.faults.pop('hook',None)
            obj=case.actuals[0]
            if change=='retained_fields':case.values[0].value.append(b'drift')
            elif change=='raw':obj._raw=bytes(bytearray(obj._raw))
            elif change=='issued':obj._issued=deepcopy(obj._issued)
            elif change=='guard':obj._guard=Lock()
            elif change=='reference':obj._reference_owner=case.actuals[1]
            elif change=='binding':
                data=json.loads(obj._raw);data['declaration']['source_binding']['extra']=1;obj._raw=encode(data)
        case.faults['hook']=hook
    with pytest.raises((ValueError,TypeError,AssertionError)):case.invoke()
    assert all(not guard.locked() for guard in original_guards)
    assert all(obj._reference_held is False for obj in case.parents)


def test_caught_same_thread_reentry_poison_is_sticky(case):
    def hook():
        case.faults.pop('hook',None)
        with pytest.raises(ValueError,match='nonreentrant'):case.invoke()
    case.faults['hook']=hook
    with pytest.raises(ValueError,match='lifetime'):case.invoke()
    assert len(case.values)==1
    released(case)


def test_foreign_thread_cannot_poison_creator_operation(case):
    errors=[]
    def foreign():
        try:case.invoke()
        except BaseException as error:errors.append(error)
    def hook():
        case.faults.pop('hook',None)
        thread=Thread(target=foreign);thread.start();thread.join(timeout=3)
        assert not thread.is_alive()
    case.faults['hook']=hook
    assert case.invoke()['complete']
    assert len(errors)==1 and isinstance(errors[0],ValueError)
    released(case)


def test_guard_cleanup_error_never_returns_success_and_keeps_body_failure(case):
    class Guard:
        def __init__(self):self.inner=Lock()
        def acquire(self,**kw):return self.inner.acquire(**kw)
        def locked(self):return self.inner.locked()
        def release(self):self.inner.release();raise OSError('release fault after unlock')
    case.actuals[1]._guard=Guard()
    case.install()
    case.faults['inspection']=str(case.actuals[0].worker_root)
    with pytest.raises(RuntimeError,match='inspection tail fault') as caught:case.invoke()
    assert any('release fault' in note for note in caught.value.__notes__)
    released(case)
    case.faults.clear()
    with pytest.raises(OSError,match='release fault'):case.invoke()
    released(case)


def test_definition_replacement_rejected_before_source(case,monkeypatch):
    monkeypatch.setattr(case.parent.Parent,'_retained',lambda self:None)
    with pytest.raises(ValueError,match='definition-time'):case.invoke()
    assert not case.values
    released(case)
