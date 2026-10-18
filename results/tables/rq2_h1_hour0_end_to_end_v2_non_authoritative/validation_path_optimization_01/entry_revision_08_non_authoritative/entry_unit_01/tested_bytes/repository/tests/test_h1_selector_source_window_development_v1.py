"""Lifecycle windows with genuine Parent method code and explicit fake transport."""
from contextlib import contextmanager
import ast
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
from threading import Barrier, Lock, Thread, get_ident
from types import FunctionType, SimpleNamespace as NS

import pytest

from tests.h1_hour0_synthetic_harness_v2 import load
from tests.test_h1_selector_post_negative_validation_development_v1 import make_post_case
from experiments import h1_selector_parent_controller_development_v2 as predecessor


@pytest.fixture
def case(tmp_path,monkeypatch):
    with make_post_case(tmp_path,monkeypatch) as case:
        parent=case.parent
        parent.Parent._check=lambda self:None  # Transport is deliberately fake.
        fn=predecessor.Parent._validate
        namespace=dict(case.ref._validate.__func__.__globals__,_completion_bytes=parent._completion_bytes)
        parent.Parent._validate=FunctionType(fn.__code__,namespace,fn.__name__,fn.__defaults__,fn.__closure__)
        for index,obj in enumerate(case.parents):
            obj._nonce='explicit-unit-'+str(index);obj._source_windows=()
        engine=load(str(Path(predecessor.__file__).with_name('h1_selector_source_window_development_v1.py')),
            'lifecycle_source_window_unit',monkeypatch,
            {'h1_selector_parent_validation_operation_development_v2':case.module})
        # Fixed caller code, exercising unchanged source/inspect/retained bodies.
        def phase(self,kind):
            with api.window(self,kind):
                if case.faults.get('body_error'):raise case.faults['body_error']
                if kind=='construct_prepare':
                    api.prepare(self,self.root,self._raw,**self._options)
                elif kind=='construct_finish':
                    api.bind(self,self._declaration,self._raw)
                    self._state='prepared';self._source()
                elif kind in ('run_pre','run_release'):
                    self._source();self._reference()
                elif kind=='run_quiet':
                    outcome=json.loads(self._outcome)
                    self._inspect(dict(pid=outcome['pid'],creation_filetime=outcome['creation_filetime']))
                    self._source();self._reference()
                elif kind=='run_post':
                    self._source();self._reference();self._state='complete';self._retained()
                    self._issued=self._saved_issued;self._issued_bytes=self._saved_issued_bytes
                elif kind=='validate':self._validate(self._issued)
        api=engine._bind_parent(parent,parent.Parent._source,parent.Parent._inspect,
            {kind:phase.__code__ for kind in engine.COUNTS})
        parent.Parent._source,parent.Parent._inspect=api.source,api.inspect
        parent._WINDOWS=api
        api.arm(parent._CHECK)
        case.api,case.engine,case.phase=api,engine,phase
        def run(kind,actual=False):
            owner=case.actuals[0] if actual else case.ref
            held=[]
            try:
                if kind.startswith('construct_'):
                    owner._state='constructing';owner._issued=None;owner._issued_bytes=None
                elif kind!='validate':
                    owner._state='running';owner._saved_issued=owner._issued;owner._saved_issued_bytes=owner._issued_bytes
                    owner._issued=None;owner._issued_bytes=None
                if not kind.startswith('construct_'):
                    owner._guard.acquire();held.append(owner._guard)
                    if actual:
                        case.ref._guard.acquire();held.append(case.ref._guard);owner._reference_held=True
                phase(owner,kind)
                return owner
            finally:
                owner._reference_held=False
                for guard in reversed(held):guard.release()
        case.run=run
        yield case


@pytest.mark.parametrize('kind',['construct_prepare','construct_finish','run_pre','run_release','run_quiet','run_post','validate'])
@pytest.mark.parametrize('actual',[False,True])
def test_all_lifecycle_windows_keep_complete_source_counts(case,kind,actual):
    owner=case.run(kind,actual)
    assert len(case.values)==2
    receipts=case.api.receipts(owner)
    assert len(receipts)==1 and receipts[0]['kind']==kind
    receipt=receipts[0]
    assert receipt['logical_source_requests']==case.engine.COUNTS[kind][actual]
    assert receipt['original_source_prepares']==2 and receipt['source_window_cache_cleared']
    assert all(receipt[k] is False for k in ('formal_result','resource_admission','native_execution_authorized',
        'source_reuse_across_job_or_callback_boundary','cross_window_source_reuse',
        'complete_dynamic_input_closure_proved','unobserved_between_bookends_ABA_covered'))
    case.api.assert_idle(owner)
    assert all(not obj._guard.locked() for obj in case.parents)


@pytest.mark.parametrize('kind',['construct_prepare','construct_finish','run_pre','run_release','run_quiet','run_post','validate'])
@pytest.mark.parametrize('at',[1,2])
def test_every_window_bookend_failure_clears_cache_and_guards(case,kind,at):
    failure=RuntimeError('source bookend fault')
    def fault(number):
        if number==at:raise failure
    case.faults['full_source']=fault
    with pytest.raises(RuntimeError) as caught:case.run(kind)
    assert caught.value is failure and len(case.values)==at-1
    assert all(not obj._guard.locked() for obj in case.parents)
    case.api.assert_idle(case.ref)
    assert not case.ref._source_windows


@pytest.mark.parametrize('change',['raw','guard','binding','retained_fields','reference','source_tail'])
def test_drift_inside_actual_retained_body_is_fatal(case,change):
    original_guards=[obj._guard for obj in case.parents]
    if change=='source_tail':case.faults['tail_difference']=True
    else:
        def hook():
            case.faults.pop('hook',None);obj=case.actuals[0]
            if change=='raw':obj._raw=bytes(bytearray(obj._raw))
            elif change=='guard':obj._guard=Lock()
            elif change=='binding':
                value=json.loads(obj._raw);value['declaration']['source_binding']['extra']='changed'
                obj._raw=json.dumps(value).encode()
            elif change=='retained_fields':case.values[0].value.append(b'changed')
            elif change=='reference':obj._reference_owner=case.actuals[1]
        case.faults['hook']=hook
    with pytest.raises((ValueError,AssertionError)):case.run('validate',True)
    assert all(not guard.locked() for guard in original_guards)
    case.api.assert_idle(case.ref)


def test_wrong_caller_is_rejected_before_source_io(case):
    with pytest.raises(ValueError,match='call site'):case.api.window(case.ref,'validate')
    assert not case.values
    with pytest.raises(ValueError,match='requires its original'):case.api.source(case.ref)


def test_caught_nested_window_poisons_creator(case):
    def hook():
        case.faults.pop('hook',None)
        with pytest.raises(ValueError,match='nonreentrant'):case.api.window(case.ref,'validate')
    case.faults['hook']=hook
    with pytest.raises(ValueError,match='lifetime'):case.run('validate')
    assert len(case.values)==1
    case.api.assert_idle(case.ref)


def test_foreign_thread_cannot_mutate_borrowed_frame_stack(case):
    errors=[]
    def foreign():
        try:case.api.source(case.ref)
        except BaseException as error:errors.append(error)
    def hook():
        case.faults.pop('hook',None)
        thread=Thread(target=foreign);thread.start();thread.join(timeout=3)
        assert not thread.is_alive()
    case.faults['hook']=hook
    owner=case.run('validate')
    assert len(errors)==1 and isinstance(errors[0],ValueError)
    assert case.api.receipts(owner)[0]['complete']


def test_real_parent3_ast_places_windows_and_callback_barriers():
    path=Path(predecessor.__file__).with_name('h1_selector_parent_controller_development_v3.py')
    tree=ast.parse(path.read_bytes());kind=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Parent')
    methods={n.name:n for n in kind.body if isinstance(n,ast.FunctionDef)}
    observed={}
    for name in ('__init__','run','validate_completion'):
        node=methods[name]
        observed[name]=[call.args[1].value for call in ast.walk(node) if isinstance(call,ast.Call)
            and isinstance(call.func,ast.Attribute) and call.func.attr=='window']
    assert observed['__init__']==['construct_prepare','construct_finish']
    assert set(observed['run'])=={'run_pre','run_release','run_quiet','run_post'}
    assert observed['validate_completion']==['validate']
    run=methods['run']
    job=next(n for n in ast.walk(run) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='run_job')
    # No with block containing the Job call; source windows are only siblings.
    assert all(job not in set(ast.walk(n)) for n in ast.walk(run) if isinstance(n,ast.With))
    callbacks=[n for n in ast.walk(run) if isinstance(n,ast.FunctionDef) and n.name in ('before_release','on_quiescent')]
    assert len(callbacks)==2
    assert all(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='assert_idle'
        for n in ast.walk(callback)) for callback in callbacks)


@pytest.mark.parametrize('kind',['construct_prepare','construct_finish','run_pre','run_release','run_quiet','run_post','validate'])
def test_body_failure_skips_tail_for_all_phase_boundaries(case,kind):
    failure=RuntimeError('fixed body fault');case.faults['body_error']=failure
    with pytest.raises(RuntimeError) as caught:case.run(kind)
    assert caught.value is failure and len(case.values)==1
    assert all(not obj._guard.locked() for obj in case.parents)
    case.api.assert_idle(case.ref)


@pytest.mark.parametrize('field',['_WINDOWS','receipt_inventory'])
def test_definition_or_inventory_rebinding_rejected_before_source(case,monkeypatch,field):
    if field=='_WINDOWS':monkeypatch.setattr(case.parent,'_WINDOWS',NS())
    else:case.ref._source_windows=(b'{}',)
    with pytest.raises(ValueError):case.run('validate')
    assert not case.values


def test_completed_receipt_inventory_cannot_be_replaced_between_windows(case):
    owner=case.run('validate')
    owner._source_windows=()
    with pytest.raises(ValueError,match='inventory'):case.run('validate')
    assert len(case.values)==2


def test_independent_creator_windows_can_overlap(case):
    barrier=Barrier(2);seen=set();mutex=Lock();errors=[];results=[]
    owners=[]
    for _ in range(2):
        owner=case.parent.Parent();vars(owner).update(vars(case.ref));owner._guard=Lock()
        owners.append(owner)
    def source(number):
        with mutex:
            first=get_ident() not in seen;seen.add(get_ident())
        if first:barrier.wait(timeout=4)
    case.faults['full_source']=source
    def call(owner):
        owner._thread=get_ident();owner._guard.acquire()
        try:
            case.phase(owner,'validate')
            case.api.assert_idle(owner)
            results.append(case.api.receipts(owner))
        except BaseException as error:errors.append(error)
        finally:owner._guard.release()
    threads=[Thread(target=call,args=(owner,)) for owner in owners]
    for thread in threads:thread.start()
    for thread in threads:thread.join(timeout=8)
    assert all(not thread.is_alive() for thread in threads)
    assert not errors and len(results)==2 and len(case.values)==4
    assert all(items[0]['complete'] for items in results)


def test_foreign_idle_check_is_rejected_without_poisoning_creator(case):
    errors=[]
    def foreign():
        try:case.api.assert_idle(case.ref)
        except BaseException as error:errors.append(error)
    def hook():
        case.faults.pop('hook',None)
        thread=Thread(target=foreign);thread.start();thread.join(timeout=3)
        assert not thread.is_alive()
    case.faults['hook']=hook
    owner=case.run('validate')
    assert len(errors)==1 and isinstance(errors[0],ValueError)
    assert case.api.receipts(owner)[0]['complete']


def test_genuine_parent_anchor_rejects_engine_global_rebinding(monkeypatch):
    from experiments import h1_selector_parent_controller_development_v3 as parent
    parent._CHECK()
    with monkeypatch.context() as patch:
        patch.setattr(parent,'_WINDOWS',NS())
        with pytest.raises(ValueError):parent._CHECK()
    with monkeypatch.context() as patch:
        patch.setattr(parent,'source_windows',NS())
        with pytest.raises(ValueError):parent._CHECK()
    parent._CHECK()
