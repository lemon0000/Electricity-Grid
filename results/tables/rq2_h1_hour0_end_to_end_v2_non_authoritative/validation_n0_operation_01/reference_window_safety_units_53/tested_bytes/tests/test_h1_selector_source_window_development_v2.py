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
from tests.h1_reference_window_test_helpers_v1 import seed_reference
from experiments import h1_selector_parent_controller_development_v2 as predecessor


@pytest.fixture
def case(tmp_path,monkeypatch,request):
    with make_post_case(tmp_path,monkeypatch) as case:
        parent=case.parent
        seed_reference(case,tmp_path)
        if getattr(request,'param',None)=='genuine_guard':
            from src.rq2_joint_deliverability_boundary_v1 import normal_h1_resource_shape as guard
            targets=((type(guard.SolverFactory),'__call__'),(guard.current,'solve_current'),
                (guard.current.native,'run_h1_chain'),(guard.current.native.capture,'solve_once'),
                (guard.current.native.capture.provenance.adapter,'create_solver'))
            originals=tuple((obj,name,getattr(obj,name)) for obj,name in targets)
            def checker():
                if any(getattr(obj,name) is not value for obj,name,value in originals):
                    raise ValueError('full checker requires restored original solver bindings')
            parent._CHECK=checker
            @contextmanager
            def guarded():
                with guard.solver_calls_forbidden():yield
                if case.faults.get('bad_restore'):
                    obj,name,value=originals[1]
                    monkeypatch.setattr(obj,name,lambda:None)
            snapshot=parent.worker.snapshot
            namespace=dict(snapshot.rebuild.__globals__,guarded=guarded,guard=guard,faults=case.faults)
            exec('def rebuild(raw,*,expected_sha256):\n'
                ' with guarded():\n'
                '  if faults.get("solver_entry"):guard.current.solve_current()\n'
                '  d=json.loads(raw)["declaration"]\n'
                '  _build(d)\n  _build(d)\n  return Rebuilt()\n',namespace)
            snapshot.rebuild=namespace['rebuild']
            case.restore_solver_bindings=lambda:[setattr(obj,name,value) for obj,name,value in originals]
        parent.Parent._check=lambda self:None  # Transport is deliberately fake.
        fn=predecessor.Parent._validate
        namespace=dict(case.ref._validate.__func__.__globals__,_completion_bytes=parent._completion_bytes)
        parent.Parent._validate=FunctionType(fn.__code__,namespace,fn.__name__,fn.__defaults__,fn.__closure__)
        for index,obj in enumerate(case.parents):
            obj._nonce='explicit-unit-'+str(index);obj._source_windows=()
        engine=load(str(Path(predecessor.__file__).with_name('h1_selector_source_window_development_v2.py')),
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
        case.api_globals=phase.__globals__
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
    reference=receipt['reference_window']
    eligible=actual and kind in case.engine.reference_windows.COUNTS
    assert receipt['reference_window_enabled'] is eligible
    if eligible:
        expected=case.engine.reference_windows.COUNTS[kind]
        assert case.reference_counts['original']==2
        assert reference['logical_reference_inspects']==expected
        assert reference['original_reference_inspects']==2
        assert reference['borrowed_reference_results']==expected-1
        assert reference['entry_original_fresh']==reference['exit_original_fresh']==1
        assert reference['cache_cleared'] and reference['bookend_only_freshness']
        assert not reference['per_call_fresh_at_return'] and not reference['actual_output_inspection_cached']
        assert not reference['canonical_reference_sequence']  # Explicit synthetic numerical fixture.
        assert len(case.reference_payloads)==expected
        assert all(set(value)=={'request_sha256','replay'} for value in case.reference_payloads)
    else:
        assert reference is None
        assert case.reference_counts['original']==({'construct_prepare':4,'construct_finish':20}[kind] if actual else 0)
    assert all(receipt[k] is False for k in ('formal_result','resource_admission','native_execution_authorized',
        'source_reuse_across_job_or_callback_boundary','cross_window_source_reuse',
        'complete_dynamic_input_closure_proved','unobserved_between_bookends_ABA_covered'))
    case.api.assert_idle(owner)
    assert all(not obj._guard.locked() for obj in case.parents)


@pytest.mark.parametrize('kind',['construct_prepare','construct_finish','run_pre','run_release','run_quiet','run_post','validate'])
@pytest.mark.parametrize('at',[1,2])
@pytest.mark.parametrize('actual',[False,True])
def test_every_window_bookend_failure_clears_cache_and_guards(case,kind,at,actual):
    failure=RuntimeError('source bookend fault')
    def fault(number):
        if number==at:raise failure
    case.faults['full_source']=fault
    with pytest.raises(RuntimeError) as caught:case.run(kind,actual)
    assert caught.value is failure and len(case.values)==at-1
    assert all(not obj._guard.locked() for obj in case.parents)
    case.api.assert_idle(case.ref)
    assert not (case.actuals[0] if actual else case.ref)._source_windows


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


@pytest.mark.parametrize('target',('build','rebuild','inspection'))
@pytest.mark.parametrize('mutation',('builtin_shadow','defaults_identity'))
def test_clone_routes_reject_late_globals_defaults_and_closure_changes(case,target,mutation):
    restore=[]
    def change(value):
        case.faults.pop('borrowed_reference',None)
        frame=sys._getframe(1)
        try:
            while frame is not None and frame.f_code.co_name!='dispatch':frame=frame.f_back
            assert frame is not None
            routes=frame.f_locals['row']['routes']
            fn={'build':routes['rebuild'].__globals__['_build'],
                'rebuild':routes['rebuild'],
                'inspection':routes['inspect'].__globals__['inspection'].inspect}[target]
            if mutation=='builtin_shadow':
                assert 'dict' not in fn.__globals__
                fn.__globals__['dict']=dict
                restore.append(lambda:fn.__globals__.pop('dict'))
            elif mutation=='defaults_identity':
                old=fn.__defaults__;fn.__defaults__=(None,) if old is None else tuple(list(old)+[None])
                restore.append(lambda:setattr(fn,'__defaults__',old))
        finally:del frame
    case.faults['borrowed_reference']=change
    try:
        with pytest.raises(ValueError):case.run('validate',True)
        assert not case.actuals[0]._source_windows
        assert all(not obj._guard.locked() for obj in case.parents)
    finally:
        for reset in reversed(restore):reset()


def test_source_module_runtime_rejects_a_new_builtin_shadow(case):
    assert 'dict' not in vars(case.engine)
    vars(case.engine)['dict']=dict
    try:
        with pytest.raises(ValueError):case.engine._RUNTIME()
    finally:vars(case.engine).pop('dict')


@pytest.mark.parametrize('mutation',('defaults_identity','kwdefaults_identity','closure_cell'))
def test_functional_clone_tracks_equal_default_objects_and_original_closure(case,mutation):
    def factory():
        callback=lambda value:value
        def operation(value=(1,),*,option=(2,)):
            return callback((value,option))
        return operation
    original=factory();clone=case.engine.clone(original)
    records=case.engine.reference_windows._function_rows((original,clone))
    assert clone()==((1,),(2,))
    if mutation=='defaults_identity':clone.__defaults__=tuple(list(clone.__defaults__))
    elif mutation=='kwdefaults_identity':clone.__kwdefaults__=dict(clone.__kwdefaults__)
    else:clone.__closure__[0].cell_contents=lambda value:('changed',value)
    with pytest.raises(ValueError):case.engine.reference_windows._verify_functions(records)


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
    path=Path(predecessor.__file__).with_name('h1_selector_parent_controller_development_v4.py')
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
@pytest.mark.parametrize('actual',[False,True])
def test_body_failure_skips_tail_for_all_phase_boundaries(case,kind,actual):
    failure=RuntimeError('fixed body fault');case.faults['body_error']=failure
    with pytest.raises(RuntimeError) as caught:case.run(kind,actual)
    assert caught.value is failure and len(case.values)==1
    assert all(not obj._guard.locked() for obj in case.parents)
    case.api.assert_idle(case.ref)


@pytest.mark.parametrize('case',['genuine_guard'],indirect=True)
@pytest.mark.parametrize('fault',[None,'solver_entry','bad_restore'])
def test_real_solver_guard_nested_dispatch_and_restoration_cleanup(case,fault):
    if fault is not None:case.faults[fault]=True
    try:
        if fault=='solver_entry':
            with pytest.raises(RuntimeError,match='solver entry forbidden'):case.run('validate',True)
        elif fault=='bad_restore':
            with pytest.raises(ValueError,match='restored original'):case.run('validate',True)
        else:
            owner=case.run('validate',True)
            assert case.api.receipts(owner)[0]['complete']
    finally:
        case.restore_solver_bindings()
    assert all(not obj._guard.locked() for obj in case.parents)
    case.api.assert_idle(case.ref)
    if fault is not None:assert not case.actuals[0]._source_windows


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
    from experiments import h1_selector_parent_controller_development_v4 as parent
    parent._CHECK()
    with monkeypatch.context() as patch:
        patch.setattr(parent,'_WINDOWS',NS())
        with pytest.raises(ValueError):parent._CHECK()
    with monkeypatch.context() as patch:
        patch.setattr(parent,'source_windows',NS())
        with pytest.raises(ValueError):parent._CHECK()
    parent._CHECK()
