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
from threading import Barrier, Event, Lock, Thread, get_ident
from types import FunctionType

import pytest

from experiments import h1_selector_parent_controller_development_v4 as predecessor
from tests.h1_hour0_synthetic_harness_v2 import load
from tests.test_h1_selector_parent_validation_operation_development_v4 import make_case, encode


@contextmanager
def make_post_case(tmp_path,monkeypatch,*,exact_source=None,source_binding=None):
    fixture=make_case(tmp_path,monkeypatch,exact_source=exact_source,source_binding=source_binding)
    case=next(fixture)
    try:
        case.abort(case.host,RuntimeError('detach explicit fake Handoff'))
        case.release()
        parent=sys.modules[case.module._HOST].parent
        parent.implementation_identity=lambda:'explicit-fake-parent-transport'
        parent.Parent._enter=FunctionType(predecessor.Parent._enter.__code__,
            dict(_release_operation_guards=predecessor._release_operation_guards),'_enter')
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
                'h1_selector_post_negative_validation_development_v3.py')),
                'experiments.h1_selector_post_negative_validation_development_v3',monkeypatch,
                {'h1_selector_parent_controller_development_v4':parent,
                 'h1_selector_parent_validation_operation_development_v4':case.module})
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


@pytest.mark.parametrize('fault',('runtime','type','any','code','registry','active'))
def test_definition_seal_rejects_before_first_source_or_reference_read(case,monkeypatch,fault):
    if fault=='runtime':monkeypatch.setattr(case.operation,'_RUNTIME',lambda:None)
    elif fault in ('type','any'):monkeypatch.setattr(case.operation,fault,lambda *a:False,raising=False)
    elif fault=='code':
        monkeypatch.setattr(case.operation._encode,'__code__',(lambda value:None).__code__)
    else:
        function=case.operation.validate_completed_bundle
        cells=dict(zip(function.__code__.co_freevars,function.__closure__))
        if fault=='registry':
            claim=cells['claim'].cell_contents
            cell=dict(zip(claim.__code__.co_freevars,claim.__closure__))['registry_lock']
            monkeypatch.setattr(cell,'cell_contents',Lock())
        else:
            monkeypatch.setattr(cells['active'],'cell_contents',dict(creator=(0,0),failure=None))
    with pytest.raises(ValueError,match='definition-time'):case.invoke()
    assert not case.values and case.reference_counts['original']==0
    released(case)


def test_foreign_active_clear_during_body_fails_and_cleans_all_owned_resources(case):
    public=case.operation.validate_completed_bundle
    cell=dict(zip(public.__code__.co_freevars,public.__closure__))['active']
    def hook():
        case.faults.pop('hook',None)
        cell.cell_contents=None
    case.faults['hook']=hook
    with pytest.raises(ValueError):case.invoke()
    assert cell.cell_contents is None and len(case.values)==1
    released(case)


def test_three_rounds_keep_all_retained_bodies_and_take_fresh_bookends(case):
    for index in range(3):
        receipt=case.invoke()
        assert len(case.values)==2*(index+1)
        assert (receipt['top_level_validations'],receipt['parent_validations'],receipt['source_prepares'],
            receipt['borrowed_source_returns'])==(4,10,2,160)
        assert [site['retained_bodies'] for site in receipt['parent_sites']]==[7,1,1,1]
        assert [site['root'] for site in receipt['parent_sites']]==[str(obj.root) for obj in case.parents]
        assert receipt['source_windows'][0]['window_cache_entry_cleared']
        ref=receipt['source_windows'][0]['reference_window']
        assert ref['logical_reference_inspects']==48 and ref['original_reference_inspects']==2
        assert [site['logical_reference_inspects'] for site in ref['parent_sites']]==[16]*3
        assert ref['cache_cleared'] and case.reference_counts['original']==2*(index+1)
        assert all(receipt[key] is True for key in ('complete','closed','outer_cleanup_complete',
            'operation_registry_cleared','all_owned_guards_released','all_reference_marks_cleared'))
        declaration=receipt['declaration']
        assert declaration['source_result_reuse_scope']=='single_synchronous_window_without_external_callback'
        assert declaration['cleared_state_scope']=='window_cache_entry_only'
        assert all(declaration[key] is False for key in ('same_predecessor_per_nested_source_io_schedule',
            'same_predecessor_failure_order','cross_window_source_reuse',
            'unobserved_between_bookends_ABA_covered','complete_dynamic_input_closure_proved',
            'full_source_object_graph_destroyed','same_public_parent_guard_schedule',
            'between_top_level_parent_validations_ABA_covered'))
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


@pytest.mark.parametrize('index',range(3))
def test_partial_mark_assignment_after_write_still_cleans_every_guard(case,index,monkeypatch):
    failure=RuntimeError('mark assignment after write')
    def assign(obj,name,value):
        object.__setattr__(obj,name,value)
        if obj is case.actuals[index] and name=='_reference_held' and value is True:raise failure
    monkeypatch.setattr(case.parent.Parent,'__setattr__',assign)
    case.install()
    with pytest.raises(RuntimeError) as caught:case.invoke()
    assert caught.value is failure and not case.values
    released(case)


def test_mark_cleanup_error_attempts_remaining_marks_and_all_guards(case,monkeypatch):
    failure=OSError('mark cleanup after clear')
    def assign(obj,name,value):
        object.__setattr__(obj,name,value)
        if obj is case.actuals[1] and name=='_reference_held' and value is False:raise failure
    monkeypatch.setattr(case.parent.Parent,'__setattr__',assign)
    case.install()
    with pytest.raises(OSError) as caught:case.invoke()
    assert caught.value is failure
    released(case)


def test_caught_reentry_during_cleanup_cannot_return_success(case):
    class Guard:
        def __init__(self):self.inner=Lock()
        def acquire(self,**kw):return self.inner.acquire(**kw)
        def locked(self):return self.inner.locked()
        def release(self):
            self.inner.release()
            with pytest.raises(ValueError,match='nonreentrant'):case.invoke()
    case.actuals[1]._guard=Guard()
    case.install()
    with pytest.raises(ValueError,match='poisoned'):case.invoke()
    released(case)


def test_same_named_nested_type_at_tail_is_not_equivalent(case):
    @dataclass(frozen=True)
    class Nested:
        value:bytes=b'unchanged'
    @dataclass(frozen=True)
    class Twin:
        value:bytes=b'unchanged'
    Twin.__module__=Nested.__module__;Twin.__qualname__=Nested.__qualname__
    def value(old,number):
        old.value[:]=[Nested() if number==1 else Twin()]
        return old
    case.faults['source_value']=value
    with pytest.raises(ValueError,match='source fields changed'):case.invoke()
    released(case)


def test_two_initial_callers_cannot_overwrite_registry(case):
    # Two independent fake bundles of the same exact Parent class, each owned
    # by its calling thread. Barrier forces both to pass the initial empty test.
    barrier=Barrier(2);source_entered=Event();loser_done=Event();local_done=set();mutex=Lock()
    real_bytes=case.parent._completion_bytes
    def completion_bytes(value):
        with mutex:
            first=get_ident() not in local_done
            local_done.add(get_ident())
        if first:barrier.wait(timeout=4)
        return real_bytes(value)
    case.parent._completion_bytes=completion_bytes
    case.install()
    bundles=[]
    for _ in range(2):
        owners=[]
        for obj in case.parents:
            fresh=case.parent.Parent();vars(fresh).update(vars(obj));fresh._guard=Lock()
            owners.append(fresh)
        for obj in owners[1:]:obj._reference_owner=owners[0]
        bundles.append(owners)
    results=[];errors=[]
    def source(number):
        if number==1:
            source_entered.set()
            assert loser_done.wait(timeout=4)
    case.faults['full_source']=source
    def call(owners):
        for obj in owners:obj._thread=get_ident()
        try:
            result=case.operation.validate_completed_bundle((owners[0],owners[0]._issued),
                {str(i):(obj,obj._issued) for i,obj in enumerate(owners[1:])})
            results.append(result)
        except BaseException as error:errors.append(error);loser_done.set()
    threads=[Thread(target=call,args=(owners,)) for owners in bundles]
    for thread in threads:thread.start()
    for thread in threads:thread.join(timeout=8)
    assert all(not thread.is_alive() for thread in threads)
    assert source_entered.is_set() and len(results)==len(errors)==1
    assert isinstance(errors[0],ValueError) and 'nonreentrant' in str(errors[0])
    assert results[0]['complete'] and len(case.values)==2
    assert all(not obj._guard.locked() and not obj._reference_held for owners in bundles for obj in owners)


def test_original_public_route_has_160_prepares_and_same_saved_bytes(case):
    from experiments import h1_selector_parent_controller_development_v2 as baseline
    phase=case.parent.worker.snapshot.phase
    fn=phase._fresh
    # The baseline also uses the explicit fake source. Keep its original full
    # call count; only the successor introduces a two-bookend window.
    phase._fresh=FunctionType(fn.__code__,dict(fn.__globals__,source=case.source),
        fn.__name__,fn.__defaults__,fn.__closure__)
    namespace=dict(case.ref._validate.__func__.__globals__)
    namespace.update(_CHECK=case.parent._CHECK,_completion_bytes=case.parent._completion_bytes)
    for name in ('_validate','validate_completion'):
        fn=getattr(baseline.Parent,name)
        # The public entry's closure enforces the canonical Parent class. This
        # explicit fake transport oracle executes its unchanged underlying body.
        while fn.__name__!=name:
            fn=next(cell.cell_contents for cell in fn.__closure__
                if type(cell.cell_contents) is FunctionType and cell.cell_contents.__name__==name)
        setattr(case.parent.Parent,name,FunctionType(fn.__code__,namespace,name,fn.__defaults__,fn.__closure__))
    before=[(obj._raw,obj._outcome,deepcopy(obj._records),obj._issued_bytes) for obj in case.parents]
    for obj in case.parents:obj.validate_completion(obj._issued)
    assert len(case.values)==160
    released(case)
    case.install()  # Definition guard is bound after the explicit predecessor oracle.
    result=case.invoke()
    assert len(case.values)==162 and result['source_prepares']==2
    assert before==[(obj._raw,obj._outcome,obj._records,obj._issued_bytes) for obj in case.parents]
    released(case)


def test_actual_three_round_integration_seam_uses_new_scope(case,tmp_path):
    import ast
    from types import SimpleNamespace as NS
    path=Path(__file__).with_name('h1_group_selector_integration_helpers_v6.py')
    tree=ast.parse(path.read_bytes())
    body=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='_consume')
    outer=next(node for node in body.body if isinstance(node,ast.With))
    loop=next(node for node in outer.body if isinstance(node,ast.For) and isinstance(node.target,ast.Name)
        and node.target.id=='missing')
    inspections=[];traces=[]
    class Absent:
        def __init__(self,*a,**kw):self.root=tmp_path/'missing_root_non_authoritative'
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def consume(self):raise ValueError('Actual execution missing or failed')
    common=NS(inspect=lambda:inspections.append(3) or dict(stage=3))
    namespace=dict(lane_ids=list(case.mapping),actuals=case.mapping,consumer=NS(Handoff=Absent),
        common_owner=common,reference=case.ref,ref=case.ref._issued,options={},retained=[],
        released=lambda:released(case),post_negative=case.operation,trace=traces.append,pytest=pytest,
        snapshot=NS(io=case.parent.io),h=NS(module=case.parent),json=json,post_negative_receipts=[])
    exec(compile(ast.Module(body=[loop],type_ignores=[]),str(path),'exec'),namespace)
    assert len(case.values)==6 and inspections==[3,3,3]
    assert traces==['missing_Actual_rejected_'+key for key in case.mapping]
    released(case)



def test_actual_helper_loader_binds_exact_parent_and_window_modules(case,monkeypatch):
    import ast
    from types import SimpleNamespace as NS
    import experiments
    path=Path(__file__).with_name('h1_group_selector_integration_helpers_v6.py')
    tree=ast.parse(path.read_bytes())
    body=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='_consume')
    index=next(i for i,node in enumerate(body.body) if isinstance(node,ast.Assign)
        and any(isinstance(target,ast.Name) and target.id=='post_negative' for target in node.targets))
    namespace=dict(load=load,directory=Path(predecessor.__file__).parent,patch=monkeypatch,
        h=NS(module=case.parent),consumer=NS(parent_validation=case.module),experiments=experiments)
    exec(compile(ast.Module(body=body.body[index:index+2],type_ignores=[]),str(path),'exec'),namespace)
    module=namespace['post_negative']
    assert module.parent is case.parent and module.kernel is case.module
    assert sys.modules[module.__name__] is module
    assert experiments.h1_selector_post_negative_validation_development_v3 is module
    receipt=module.validate_completed_bundle(case.reference,case.mapping)
    assert receipt['complete'] and receipt['implementation']==module.implementation_identity()
    released(case)
