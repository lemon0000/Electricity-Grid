"""Original consumer coordinator plus real protocol, with synthetic science.

AST extraction and fake replay bodies isolate guard/nonce/lifetime faults.
This does not construct a genuine public BootstrapOwner; header acceptance
and saved-data numerical equivalence are separate integration checks.
"""
import ast
import gc
import json
import os
from pathlib import Path
from threading import Lock,Thread,get_ident
from types import SimpleNamespace
from weakref import ref

import pytest

from experiments import h1_bootstrap_integration_development_v6 as original
from tests.test_h1_registry_validation_operation_development_v5 import (
    case,build_root,roots,scope_record)


@pytest.fixture
def consumer(case,tmp_path):
    owner=case.owner();owner._operation.release();owner._operation_nonce=None
    owner._pid,owner._thread=os.getpid(),get_ident()
    owner.declaration=SimpleNamespace(phase_archive=None)
    root,arm=roots(case,tmp_path,1)[0]
    scopes=[];retired=[];checks=[]
    state=dict(body_error=None,phase_error=None,exit_error=None,mode='normal',cleanup_faults=set())
    def replay():
        scope=case.m.registry_validation_scope(owner);scopes.append(scope)
        if state['mode']=='empty':return 'empty'
        build_root(case,scope,root,arm)
        if state['body_error'] is not None:raise state['body_error']
        if state['mode']=='reentrant':return read(owner,'inspect')
        if state['mode']=='unconfirmed':
            scope.begin_build(owner,root,arm,'registry')
            case.m.prepare(root,expected_binding_sha256='a'*64,
                expected_terminal_sha256='b'*64,completed_hours=1,registry_scope=scope)
        else:build_root(case,scope,root,arm)
        return 'replayed'
    owner._replay=replay
    owner._inspect_read_body=lambda:dict(state=owner._replay())
    def check(value):
        checks.append(value)
        if state['exit_error'] is not None:raise state['exit_error']
    def current(value):
        if state['phase_error'] is not None:raise state['phase_error']
        return 'unit phase frame'
    def close(scope,error=None):
        result=case.m._close_registry_scope(scope,error)
        if 'close' in state['cleanup_faults']:raise OSError('injected scope close failure')
        return result
    def receipt(scope):
        result=case.m._registry_scope_receipt(scope)
        if 'receipt' in state['cleanup_faults']:raise OSError('injected scope receipt failure')
        return result
    def retire(scope):
        if 'retire' in state['cleanup_faults']:raise OSError('injected record retirement failure')
        proof=case.m._registry_scope_receipt(scope)
        operations=list(scope_record(scope)['operations'].values())
        case.m._retire_registry_scope(scope);retired.append((proof,operations))
    def open_scope(value):
        scope=case.scope(value)
        hook=state.get('after_open')
        if hook is not None:hook()
        return scope
    verifier=SimpleNamespace(_bind_registry_bootstrap=lambda cls,method:open_scope,
        _close_registry_scope=close,_poison_registry_scope=case.m._poison_registry_scope,
        _registry_scope_receipt=receipt,_retire_registry_scope=retire)
    space=dict(historical_verifier=verifier,BootstrapOwner=type(owner),
        _snapshot=original._snapshot,_check_N0_contract=check,
        historical=SimpleNamespace(io=case.m.io),_PHASE_RUNTIME=lambda:None,
        _phase_current=current,os=os,get_ident=get_ident,ref=ref,json=json,Lock=Lock,
        SCHEMA='unit_Bootstrap6_consumer',FLAGS=original.FLAGS)
    tree=ast.parse(Path(original.__file__).read_bytes())
    function=next(row for row in tree.body if isinstance(row,ast.FunctionDef) and row.name=='_bind_registry_run')
    exec(compile(ast.Module(body=[function],type_ignores=[]),original.__file__,'exec'),space)
    run,read,receipt,cleanup=space['_bind_registry_run']()
    return SimpleNamespace(case=case,owner=owner,root=root,arm=arm,scopes=scopes,
        run=run,read=read,receipt=receipt,cleanup=cleanup,state=state,checks=checks,space=space,verifier=verifier,retired=retired)


def private_records(function,helper):
    value=dict(zip(function.__code__.co_freevars,(c.cell_contents for c in function.__closure__)))
    while helper not in value:
        function=value['original_method']
        value=dict(zip(function.__code__.co_freevars,(c.cell_contents for c in function.__closure__)))
    lookup=value[helper]
    return dict(zip(lookup.__code__.co_freevars,(c.cell_contents for c in lookup.__closure__)))['records']


def assert_closed(c):
    assert not c.owner._original_operation.locked() and c.owner._operation_nonce is None
    assert c.case.m.registry_validation_scope(c.owner) is None
    assert not private_records(c.case.m._retire_registry_scope,'row')
    assert not private_records(c.case.m._retire_operation,'record')
    for proof,operations in c.retired:
        assert proof['closed']
        for operation in operations:
            assert operation._proof is operation._candidate_proof is None
            assert not operation._original_guard.locked()


def test_consumer_two_methods_produce_separate_proofs_and_detached_observations(consumer):
    c=consumer
    assert c.read(c.owner,'constructor')=='replayed'
    assert c.read(c.owner,'inspect')==dict(state='replayed')
    assert_closed(c)
    observed=c.receipt(c.owner)
    assert observed['successful_reads']==2 and not observed['cached_numerical_proofs_retained']
    assert not observed['detached_consumer_credential'] and not c.owner.poisoned
    reads=observed['reads'];assert [row['mode'] for row in reads]==['constructor','inspect']
    proofs=[row['registry_execution'] for row in reads]
    assert len({row['session_identity'] for row in proofs})==2
    for row in reads:
        p=row['registry_execution']
        assert row['purpose']=='consumer_read' and row['metadata_read_complete']
        assert row['numerical_roots']==1 and not row['producer_nonce_borrowed']
        assert p['complete'] and p['confirmed_builds']==2
        assert (p['full_numerical_hour_replays'],p['fresh_byte_context_revalidations'],p['context_observations'])==(4,12,32)
        assert [v['execution']['proof_role'] for v in p['builds']]==['produced','consumed']
        assert all(row[name] is False for name in original.FLAGS)
    assert len(c.case.calls)==8 and len(c.case.contexts)==64
    observed['reads'].clear()
    assert c.receipt(c.owner)['successful_reads']==2


def test_empty_registry_is_complete_metadata_read_but_no_numerical_proof(consumer):
    c=consumer;c.state['mode']='empty'
    assert c.read(c.owner,'constructor')=='empty'
    row,=c.receipt(c.owner)['reads'];p=row['registry_execution']
    assert row['metadata_read_complete'] and row['numerical_roots']==0
    assert not p['complete'] and p['closed'] and p['confirmed_builds']==0
    assert not p['root_receipts'] and not p['builds'] and not c.case.calls
    assert_closed(c)


@pytest.mark.parametrize('failure',['body','exit_check','unconfirmed','reentrant'])
def test_failed_read_clears_original_proof_nonce_and_guard_without_success_observation(consumer,failure):
    c=consumer;primary=RuntimeError('consumer read primary')
    if failure=='body':c.state['body_error']=primary
    elif failure=='exit_check':c.state['exit_error']=primary
    else:c.state['mode']=failure
    with pytest.raises(RuntimeError if failure in ('body','exit_check') else ValueError) as caught:
        c.read(c.owner,'inspect')
    if failure in ('body','exit_check'):assert caught.value is primary
    assert c.owner.poisoned and c.receipt(c.owner)['successful_reads']==0
    assert_closed(c)
    assert all(not proof['complete'] for proof,_ in c.retired)
    failed,=c.receipt(c.owner)['failed_reads']
    assert failed['cleanup']['scope_closed'] and failed['cleanup']['scope_retired']
    assert failed['original_guard_unlocked'] and failed['nonce_cleared']
    assert not failed['metadata_read_complete'] and not failed['detached_consumer_credential']


@pytest.mark.parametrize('fault',['nonce','busy','guard','phase','foreign_thread','foreign_owner','mode'])
def test_unborrowed_original_creator_and_fixed_route_required_before_scope(consumer,fault):
    c=consumer;owner=c.owner
    if fault=='nonce':owner._operation_nonce=object()
    elif fault=='busy':owner._operation.acquire()
    elif fault=='guard':owner._operation=Lock()
    elif fault=='phase':
        owner.declaration=SimpleNamespace(phase_archive=object());c.state['phase_error']=ValueError('no original phase')
    errors=[]
    # Keep the regular call separate from the arbitrary-callable rejection.
    def checked_attempt():
        try:c.read(SimpleNamespace() if fault=='foreign_owner' else owner,(lambda:None) if fault=='mode' else 'inspect')
        except ValueError as error:errors.append(error)
    if fault=='foreign_thread':
        thread=Thread(target=checked_attempt);thread.start();thread.join(timeout=5)
        assert not thread.is_alive()
    else:checked_attempt()
    assert len(errors)==1 and not c.scopes and not owner.poisoned
    owner._operation_nonce=None;owner._operation=owner._original_operation
    if owner._operation.locked():owner._operation.release()
    assert c.receipt(owner)['successful_reads']==0


def test_method_read_count_is_bounded_even_for_empty_metadata(consumer):
    c=consumer;c.state['mode']='empty'
    for _ in range(128):assert c.read(c.owner,'constructor')=='empty'
    with pytest.raises(ValueError,match='bounded'):c.read(c.owner,'inspect')
    assert c.receipt(c.owner)['successful_reads']==128 and not c.owner.poisoned
    assert_closed(c)


@pytest.mark.parametrize('primary_body',[False,True])
def test_composite_cleanup_failures_keep_first_error_and_save_honest_observation(consumer,primary_body):
    c=consumer;primary=RuntimeError('composite body primary')
    c.state['cleanup_faults']={'close','receipt','retire'}
    if primary_body:c.state['body_error']=primary
    with pytest.raises(RuntimeError if primary_body else OSError) as caught:c.read(c.owner,'inspect')
    if primary_body:assert caught.value is primary
    else:assert 'scope close failure' in str(caught.value)
    assert len(caught.value.__notes__)>=2
    assert c.receipt(c.owner)['pending_registry_records']==1
    failed,=c.receipt(c.owner)['failed_reads']
    assert c.receipt(c.owner)['failed_read_count']==1 and c.receipt(c.owner)['successful_reads']==0
    assert len(failed['cleanup']['cleanup_failures'])==3
    # Close/receipt faults are after the real operation; retirement fails before
    # deleting anything and must keep its original retry route available.
    assert not failed['cleanup']['scope_closed'] and not failed['cleanup']['scope_retired']
    assert failed['original_guard_unlocked'] and failed['nonce_cleared']
    c.state['cleanup_faults'].clear();c.cleanup(c.owner);assert_closed(c)
    assert c.receipt(c.owner)['pending_registry_records']==0


@pytest.mark.parametrize('primary_body',[False,True])
def test_foreign_thread_releasing_live_guard_cannot_mask_body_primary(consumer,primary_body):
    c=consumer;primary=RuntimeError('foreign release body primary')
    original_replay=c.owner._replay
    def replay():
        result=original_replay()
        thread=Thread(target=c.owner._original_operation.release)
        thread.start();thread.join(timeout=5);assert not thread.is_alive()
        if primary_body:raise primary
        return result
    c.owner._replay=replay
    with pytest.raises(RuntimeError if primary_body else ValueError) as caught:c.read(c.owner,'inspect')
    if primary_body:assert caught.value is primary
    assert any('original guard release' in note for note in caught.value.__notes__)
    assert_closed(c)
    failed,=c.receipt(c.owner)['failed_reads']
    assert failed['cleanup']['scope_retired'] and failed['original_guard_unlocked']
    assert any('unlocked lock' in error for error in failed['cleanup']['cleanup_failures'])


def test_entry_dispatch_failure_still_closes_and_retires_original_scope(consumer,monkeypatch):
    c=consumer
    c.state['after_open']=lambda:monkeypatch.setattr(c.case.m.N0ValidationOperation,'_check',lambda *args:None)
    with pytest.raises(ValueError,match='definition-time historical dispatch'):c.read(c.owner,'constructor')
    assert_closed(c)
    failed,=c.receipt(c.owner)['failed_reads']
    assert failed['cleanup']['scope_closed'] and failed['cleanup']['scope_retired']
    assert not c.scopes and len(c.retired)==1


def test_open_dispatch_failure_cannot_leave_a_scope_record(consumer,monkeypatch):
    c=consumer
    monkeypatch.setattr(c.case.m.N0ValidationOperation,'_check',lambda *args:None)
    with pytest.raises(ValueError,match='definition-time historical dispatch'):c.read(c.owner,'constructor')
    assert_closed(c)
    failed,=c.receipt(c.owner)['failed_reads']
    assert not failed['cleanup']['scope_closed'] and not failed['cleanup']['scope_retired']
    assert not c.scopes and not c.retired


def test_retired_scope_and_operations_release_owner_and_private_weak_history(consumer):
    c=consumer;c.read(c.owner,'constructor');assert_closed(c)
    owner_ref=ref(c.owner)
    history=dict(zip(c.read.__code__.co_freevars,(cell.cell_contents for cell in c.read.__closure__)))['record']
    records=dict(zip(history.__code__.co_freevars,(cell.cell_contents for cell in history.__closure__)))['records']
    assert len(records)==1
    c.retired.clear();c.scopes.clear();c.checks.clear();c.owner=None
    gc.collect()
    assert owner_ref() is None and not records


def test_many_empty_owners_leave_no_scope_operation_or_consumer_history_records(consumer):
    c=consumer
    history=dict(zip(c.read.__code__.co_freevars,(cell.cell_contents for cell in c.read.__closure__)))['record']
    records=dict(zip(history.__code__.co_freevars,(cell.cell_contents for cell in history.__closure__)))['records']
    for _ in range(16):
        owner=c.case.owner();owner._operation.release();owner._operation_nonce=None
        owner._pid,owner._thread=os.getpid(),get_ident()
        owner.declaration=SimpleNamespace(phase_archive=None)
        owner._replay=lambda:'empty';owner._inspect_read_body=lambda:dict(state='empty')
        owner_ref=ref(owner)
        assert c.read(owner,'constructor')=='empty'
        assert c.read(owner,'inspect')==dict(state='empty')
        owner.closed=True;c.checks.clear();del owner
        c.retired.clear();gc.collect()
        assert owner_ref() is None and not records
        assert_closed(c)


def original_close(c,owner):
    tree=ast.parse(Path(original.__file__).read_bytes())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='BootstrapOwner')
    function=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='close')
    space=dict(os=os,get_ident=get_ident,_phase_cleanup=lambda value:None,_cleanup_registry_records=c.cleanup)
    exec(compile(ast.Module(body=[function],type_ignores=[]),original.__file__,'exec'),space)
    owner._original_controller=None
    for name in ('_global','_bootstrap'):
        journal=getattr(owner,name);journal.close=journal._original_lease.close
    space['close'](owner)


@pytest.mark.parametrize('case',['retire_0'],indirect=True)
@pytest.mark.parametrize('producer',[False,True])
def test_partial_arm_retirement_has_original_owner_close_retry_route(consumer,producer):
    c=consumer;second=c.root.parent/'root_1';second.mkdir()
    def replay():
        scope=c.case.m.registry_validation_scope(c.owner);c.scopes.append(scope)
        for _ in range(2):
            build_root(c.case,scope,c.root,c.arm)
            build_root(c.case,scope,second,'2'*64)
        return 'replayed'
    c.owner._replay=replay
    if producer:
        c.owner._operation.acquire();c.owner._operation_nonce=object()
        try:
            with pytest.raises(OSError,match='injected retire_0'):
                c.run(c.owner,lambda:dict(state='pending_post_N',value=replay()))
        finally:c.owner._operation_nonce=None;c.owner._operation.release()
    else:
        with pytest.raises(OSError,match='injected retire_0'):c.read(c.owner,'inspect')
    assert c.receipt(c.owner)['pending_registry_records']==1
    rows=private_records(c.case.m._retire_registry_scope,'row');assert len(rows)==1
    value,=rows.values()
    assert len(value['operations'])==1
    operation,=value['operations'].values()
    assert operation._exact_root==str(c.root) and operation._proof is operation._candidate_proof is None
    assert not c.case.m._registry_scope_receipt(c.scopes[0])['complete']
    assert len(private_records(c.case.m._retire_operation,'record'))==1
    with pytest.raises(OSError,match='injected retire_0'):original_close(c,c.owner)
    assert c.owner.closed and c.receipt(c.owner)['pending_registry_records']==1
    c.case.retire_fault[0]=False
    original_close(c,c.owner)
    assert c.receipt(c.owner)['pending_registry_records']==0
    assert_closed(c)


def test_process_wide_pending_capacity_is_bounded_and_closed_owners_can_retry(consumer):
    c=consumer;c.state['cleanup_faults']={'retire'};owners=[]
    for _ in range(16):
        owner=c.case.owner();owner._operation.release();owner._operation_nonce=None
        owner._pid,owner._thread=os.getpid(),get_ident()
        owner.declaration=SimpleNamespace(phase_archive=None)
        owner._replay=lambda:'empty';owner._inspect_read_body=lambda:dict(state='empty')
        with pytest.raises(OSError,match='record retirement failure'):c.read(owner,'constructor')
        owners.append(owner)
        assert c.receipt(owner)['pending_registry_records']==1
    with pytest.raises(ValueError,match='cleanup capacity exhausted'):c.read(c.owner,'constructor')
    assert not c.owner._operation.locked() and c.owner._operation_nonce is None
    assert len(private_records(c.case.m._retire_registry_scope,'row'))==16
    c.state['cleanup_faults'].clear()
    for owner in owners:original_close(c,owner)
    assert_closed(c)


@pytest.mark.parametrize('body_failure',[False,True])
def test_original_producer_returns_detached_receipt_then_retires_without_releasing_callers_guard(consumer,body_failure):
    c=consumer;primary=RuntimeError('producer body primary')
    c.owner._operation.acquire();nonce=object();c.owner._operation_nonce=nonce
    def execute():
        c.owner._replay()
        if body_failure:raise primary
        return dict(state='pending_post_N')
    try:
        if body_failure:
            with pytest.raises(RuntimeError) as caught:c.run(c.owner,execute)
            assert caught.value is primary
        else:
            result=c.run(c.owner,execute)
            proof=json.loads(result['N0_validation_execution_receipt'])
            assert proof['complete'] and proof['confirmed_builds']==2
            assert c.receipt(c.owner)['successful_reads']==0
        assert c.owner._operation.locked() and c.owner._operation_nonce is nonce
    finally:c.owner._operation_nonce=None;c.owner._operation.release()
    assert_closed(c)


def test_successor_science_functions_and_owned_graph_are_only_namespace_substitutions():
    from experiments import h1_bootstrap_integration_development_v5 as old
    substitutions=(('h1_bootstrap_integration_development_v5','h1_bootstrap_integration_development_v6'),
        ('h1_owned_bootstrap_controller_development_v5','h1_owned_bootstrap_controller_development_v6'),
        ('h1_historical_n0_verifier_development_v4','h1_historical_n0_verifier_development_v5'))
    def renamed(text):
        for before,after in substitutions:text=text.replace(before,after)
        return text.replace('Bootstrap5','Bootstrap6').replace('Owned5','Owned6')
    assert Path(original.owned.__file__).read_text(encoding='utf-8')==renamed(Path(old.owned.__file__).read_text(encoding='utf-8'))
    prior_verifier=ast.parse(renamed(Path(old.historical_verifier.__file__).read_text(encoding='utf-8')))
    new_verifier=ast.parse(Path(original.historical_verifier.__file__).read_bytes())
    unchanged=lambda tree:{n.name:ast.dump(n,include_attributes=False) for n in tree.body
        if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name not in ('_bind_resources','_bind_registry_scope')}
    assert unchanged(prior_verifier)==unchanged(new_verifier)
    before=ast.parse(Path(old.__file__).read_bytes());after=ast.parse(Path(original.__file__).read_bytes())
    changed={'_bind_registry_run','BootstrapOwner','_install_N0_contract'}
    old_functions={n.name:n for n in before.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    new_functions={n.name:n for n in after.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    assert set(old_functions)==set(new_functions)
    for name,node in old_functions.items():
        if name not in changed:
            assert ast.dump(ast.parse(renamed(ast.unparse(node))),include_attributes=False)==ast.dump(
                ast.parse(ast.unparse(new_functions[name])),include_attributes=False),name
    old_methods={n.name:n for n in old_functions['BootstrapOwner'].body if isinstance(n,ast.FunctionDef)}
    new_methods={n.name:n for n in new_functions['BootstrapOwner'].body if isinstance(n,ast.FunctionDef)}
    assert set(new_methods)-set(old_methods)=={'_inspect_read_body','registry_read_validation_receipt'}
    for name,node in old_methods.items():
        if name not in ('__init__','inspect','close'):
            assert ast.dump(ast.parse(renamed(ast.unparse(node))),include_attributes=False)==ast.dump(
                ast.parse(ast.unparse(new_methods[name])),include_attributes=False),name
    old_inspect=next(n for n in old_methods['inspect'].body if isinstance(n,ast.Try))
    assert [ast.dump(n,include_attributes=False) for n in old_inspect.body]==[
        ast.dump(n,include_attributes=False) for n in new_methods['_inspect_read_body'].body]
    expected=ast.parse(renamed(ast.unparse(old_methods['__init__']))).body[0]
    calls=[n for n in ast.walk(expected) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
        and isinstance(n.func.value,ast.Name) and n.func.value.id=='self' and n.func.attr=='_replay']
    assert len(calls)==1
    calls[0].func=ast.Name(id='_run_registry_read',ctx=ast.Load())
    calls[0].args=[ast.Name(id='self',ctx=ast.Load()),ast.Constant(value='constructor')]
    assert ast.dump(expected,include_attributes=False)==ast.dump(new_methods['__init__'],include_attributes=False)
    assert original.historical_verifier.SCHEMA==old.historical_verifier.SCHEMA
    pins={name:'a'*64 for name in original.N0_PINS}
    root='D:/consumer_unit_non_authoritative'
    new=original._N0_body(root,pins);prior=old._N0_body(root,pins)
    changed_fields={'historical_verifier_schema','historical_validation_contract'}
    assert original.encode({k:v for k,v in new.items() if k not in changed_fields})==old.encode(
        {k:v for k,v in prior.items() if k not in changed_fields})
