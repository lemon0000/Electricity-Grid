"""Original consumer coordinator plus real protocol, with synthetic science.

AST extraction and fake replay bodies isolate guard/nonce/lifetime faults.
This does not construct a genuine public BootstrapOwner; header acceptance
and saved-data numerical equivalence are separate integration checks.
"""
import ast
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
    scopes=[];checks=[];state=dict(body_error=None,phase_error=None,exit_error=None,mode='normal')
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
    owner._inspect_read_body=lambda:dict(state=replay())
    def check(value):
        checks.append(value)
        if state['exit_error'] is not None:raise state['exit_error']
    def current(value):
        if state['phase_error'] is not None:raise state['phase_error']
        return 'unit phase frame'
    verifier=SimpleNamespace(_bind_registry_bootstrap=lambda cls,method:case.scope,
        _close_registry_scope=case.m._close_registry_scope,
        _poison_registry_scope=case.m._poison_registry_scope,
        _registry_scope_receipt=case.m._registry_scope_receipt)
    space=dict(historical_verifier=verifier,BootstrapOwner=type(owner),
        _snapshot=original._snapshot,_check_N0_contract=check,
        historical=SimpleNamespace(io=case.m.io),_PHASE_RUNTIME=lambda:None,
        _phase_current=current,os=os,get_ident=get_ident,ref=ref,json=json,
        SCHEMA='unit_Bootstrap6_consumer',FLAGS=original.FLAGS)
    tree=ast.parse(Path(original.__file__).read_bytes())
    function=next(row for row in tree.body if isinstance(row,ast.FunctionDef) and row.name=='_bind_registry_run')
    exec(compile(ast.Module(body=[function],type_ignores=[]),original.__file__,'exec'),space)
    run,read,receipt=space['_bind_registry_run']()
    return SimpleNamespace(case=case,owner=owner,root=root,arm=arm,scopes=scopes,
        read=read,receipt=receipt,state=state,checks=checks,space=space,verifier=verifier)


def assert_closed(c):
    assert not c.owner._original_operation.locked() and c.owner._operation_nonce is None
    assert c.case.m.registry_validation_scope(c.owner) is None
    for scope in c.scopes:
        proof=c.case.m._registry_scope_receipt(scope)
        assert proof['closed']
        for operation in scope_record(scope)['operations'].values():
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
    assert all(not c.case.m._registry_scope_receipt(scope)['complete'] for scope in c.scopes)


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


def test_successor_science_functions_and_owned_graph_are_only_namespace_substitutions():
    from experiments import h1_bootstrap_integration_development_v5 as old
    substitutions=(('h1_bootstrap_integration_development_v5','h1_bootstrap_integration_development_v6'),
        ('h1_owned_bootstrap_controller_development_v5','h1_owned_bootstrap_controller_development_v6'),
        ('h1_historical_n0_verifier_development_v4','h1_historical_n0_verifier_development_v5'))
    def renamed(text):
        for before,after in substitutions:text=text.replace(before,after)
        return text
    for before,after in ((old.historical_verifier,original.historical_verifier),(old.owned,original.owned)):
        assert Path(after.__file__).read_text(encoding='utf-8')==renamed(Path(before.__file__).read_text(encoding='utf-8'))
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
        if name not in ('__init__','inspect'):
            assert ast.dump(ast.parse(renamed(ast.unparse(node))),include_attributes=False)==ast.dump(
                ast.parse(ast.unparse(new_methods[name])),include_attributes=False),name
    assert ast.dump(old_methods['inspect'].body[0],include_attributes=False)==ast.dump(new_methods['_inspect_read_body'].body[0],include_attributes=False)
    assert ast.dump(old_methods['inspect'].body[1],include_attributes=False)==ast.dump(new_methods['_inspect_read_body'].body[1],include_attributes=False)
    assert original.historical_verifier.SCHEMA==old.historical_verifier.SCHEMA
    pins={name:'a'*64 for name in original.N0_PINS}
    root='D:/consumer_unit_non_authoritative'
    new=original._N0_body(root,pins);prior=old._N0_body(root,pins)
    changed_fields={'historical_verifier_schema','historical_validation_contract'}
    assert original.encode({k:v for k,v in new.items() if k not in changed_fields})==old.encode(
        {k:v for k,v in prior.items() if k not in changed_fields})
