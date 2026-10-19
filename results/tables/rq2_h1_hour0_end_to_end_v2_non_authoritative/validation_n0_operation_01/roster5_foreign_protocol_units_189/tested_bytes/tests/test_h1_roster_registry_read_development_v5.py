"""Original Roster methods and Core7 coordinator with real Verifier6 protocol.

Pre-definition fake phase/storage/science isolate lifetime and failure windows.
Canonical production binding and a genuine public header are separate checks.
These fixtures grant no public-owner or scientific-result authority.
"""
import ast
import gc
import importlib.util
import json
import os
from pathlib import Path
import sys
from threading import Lock,Thread,get_ident
from types import FunctionType,ModuleType,SimpleNamespace
from weakref import ref

import pytest

from experiments import h1_bootstrap_integration_development_v7 as original
from tests.test_h1_registry_validation_operation_development_v6 import case,build_root,roots,scope_record


def cells(function):
    return dict(zip(function.__code__.co_freevars,(cell.cell_contents for cell in function.__closure__ or ())))


@pytest.fixture
def roster_case(case,tmp_path,monkeypatch):
    c=case;owner=c.owner();owner._operation.release();owner._operation_nonce=None
    owner._pid,owner._thread=os.getpid(),get_ident()
    owner.declaration=SimpleNamespace(phase_archive=None)
    owner._check=lambda:None;owner._study_binding_bytes=b'{"fixture":"unit"}'
    owner.study_root=tmp_path/'study_non_authoritative';owner.study_root.mkdir()
    owner._global.head='b'*64;owner._global.genesis='c'*64
    numerical=roots(c,tmp_path,3)
    state=dict(body_error=None,cleanup_faults=set(),phase_error=None,row_error=None,
        registry_error=None,retention_error=None,view_hook=None)
    scopes=[];retired=[];events=[]
    def registry():
        scope=c.m.registry_validation_scope(owner)
        if scope is None:raise ValueError('authenticated N0 registry scope required')
        events.append(('registry',id(scope),owner._operation_nonce))
        for root,arm in numerical:build_root(c,scope,root,arm)
        hook=state['view_hook']
        if hook is not None:hook()
        if state['registry_error'] is not None:raise state['registry_error']
        return dict(validated=True)
    owner._registry=registry
    def replay():
        registry()
        if state['body_error'] is not None:raise state['body_error']
        registry();return 'pending_post_N'
    owner._replay=replay
    bootstrap=ModuleType('experiments._h1_roster_bootstrap_'+tmp_path.name)
    bootstrap.__file__=str(tmp_path/'h1_bootstrap_integration_development_v7.py')
    bootstrap.__package__='experiments';bootstrap.__spec__=None;bootstrap.__loader__=None
    monkeypatch.setitem(sys.modules,bootstrap.__name__,bootstrap)
    Path(bootstrap.__file__).write_bytes(Path(original.__file__).read_bytes())
    def bind_consumer(actor_type,check):
        # Verifier's private bootstrap binder requires its canonical globals.
        # Only these unit-adapter globals differ; code and closure are original.
        adapted=FunctionType(check.__code__,vars(original),check.__name__,check.__defaults__,check.__closure__)
        return c.bind_consumer(actor_type,adapted)
    def open_scope(value):
        scope=c.scope(value);scopes.append(scope);return scope
    def close(scope,error=None):
        result=c.m._close_registry_scope(scope,error)
        if 'close' in state['cleanup_faults']:raise OSError('scope close failure')
        return result
    def receipt(scope):
        result=c.m._registry_scope_receipt(scope)
        if 'receipt' in state['cleanup_faults']:raise OSError('scope receipt failure')
        return result
    def retire(scope):
        if 'retire' in state['cleanup_faults']:raise OSError('scope retirement failure')
        proof=c.m._registry_scope_receipt(scope);operations=list(scope_record(scope)['operations'].values())
        c.m._retire_registry_scope(scope);retired.append((proof,operations))
    verifier=SimpleNamespace(_bind_registry_bootstrap=lambda cls,check:(open_scope,bind_consumer),
        _close_registry_scope=close,_poison_registry_scope=c.m._poison_registry_scope,
        _registry_scope_receipt=receipt,_retire_registry_scope=retire,
        verifier_identity=c.m.verifier_identity,VERIFIER_SCHEMA=c.m.VERIFIER_SCHEMA)
    def phase(owner,execute,**kwargs):
        events.append(('phase_enter',kwargs.get('site'),c.m.registry_validation_scope(owner) is not None))
        result=execute()
        if state['phase_error'] is not None:raise state['phase_error']
        events.append(('phase_exit',kwargs.get('site'),c.m.registry_validation_scope(owner) is not None))
        return result
    def external(value,callback,*args):
        assert c.m.registry_validation_scope(value) is None and value._operation_nonce is None
        events.append(('callback',None,None));return callback(*args)
    class Journal:
        def __init__(self,root,declaration,*,max_record_bytes,retain_head,**kwargs):
            self.cap=max_record_bytes;self._declaration=original.encode(declaration)
            self._header=original.encode(dict(declaration=declaration));self.head='e'*64
            self._rows=[];self._retain=retain_head;self.closed=False
        def check(self):
            if self.closed:raise ValueError('journal closed')
        def rows(self):
            self.check()
            if state['row_error'] is not None:raise state['row_error']
            return list(self._rows)
        def reserve(self,count):self.check()
        def append(self,body,*,expected_head):
            self.check();assert self.head==expected_head
            before=self.head;head=original.digest([before,body])
            self._rows.append((head,body));self.head=head;self._retain('unit_group',before,head)
            return head
        def close(self):self.closed=True
    candidate=dict(audit=dict(group=dict(group_identity='f'*64,
        siblings=[dict(arm_id=arm,ordinal=index) for index,(_,arm) in enumerate(numerical)]),
        arm_classifications=[dict(arm_id=arm,classification='direct_shared_lane') for _,arm in numerical]),
        audit_identity='a'*64)
    def reference(value,sibling,registry,identity):
        arm=sibling['arm_id'];pin=original.digest(arm)
        return dict(slot_id=arm,episode_root=arm,**{
            name:dict(head=original.digest([arm,name]))
            for name in ('claim','release','local_terminal','global_terminal')})
    vars(bootstrap).update(historical_verifier=verifier,BootstrapOwner=type(owner),
        _snapshot=original._snapshot,_check_N0_contract=lambda owner:None,
        historical=SimpleNamespace(io=c.m.io),_PHASE_RUNTIME=lambda:None,
        _phase_current=lambda owner:None,_phase_run=phase,_phase_external=external,
        _phase_prepare=lambda *args:None,validation_runtime=original.validation_runtime,
        os=os,get_ident=get_ident,ref=ref,json=json,Lock=Lock,sys=sys,types=__import__('types'),
        dis=__import__('dis'),Path=Path,encode=original.encode,SCHEMA='unit_Bootstrap7',FLAGS=original.FLAGS,
        implementation_identity=lambda:'a'*64,digest=original.digest,_Journal=Journal,
        _N0_body=original._N0_body,_global_N0_body=original._global_N0_body,
        storage=original.storage,local=SimpleNamespace(_path=lambda value:Path(value)),
        _journal_header=lambda root,declaration,*args:original.encode(dict(declaration=declaration)),
        _unit_candidate=lambda owner:json.loads(original.encode(candidate)),_unit_reference=reference)
    tree=ast.parse(Path(original.__file__).read_bytes())
    functions=[row for row in tree.body if isinstance(row,ast.FunctionDef)
        and row.name in ('_bind_registry_run','_bind_roster_registry_routes')]
    exec(compile(ast.Module(body=functions,type_ignores=[]),bootstrap.__file__,'exec'),vars(bootstrap))
    roster_path=tmp_path/'h1_group_execution_roster_development_v5.py'
    production=Path(original.__file__).with_name(roster_path.name).read_text(encoding='utf-8')
    roster_tree=ast.parse(production)
    roster_tree.body=[node for node in roster_tree.body if not (isinstance(node,ast.ImportFrom)
        and node.module=='experiments' and any(alias.asname=='bootstrap' for alias in node.names))]
    for name,body in (('_candidate','return bootstrap._unit_candidate(owner)'),
            ('_reference','return bootstrap._unit_reference(owner,sibling,registry,verifier_identity)')):
        node=next(node for node in roster_tree.body if isinstance(node,ast.FunctionDef) and node.name==name)
        node.body=ast.parse(body).body
    roster_path.write_text(ast.unparse(roster_tree)+'\n',encoding='utf-8')
    for number in (9,10):
        (tmp_path/f'h1_group_n0_common_input_binding_development_v{number}.py').write_text('# unit source only\n')
    routes=bootstrap._bind_registry_run()
    (bootstrap._run_registry_operation,bootstrap._run_registry_read,bootstrap._read_registry_receipts,
        bootstrap._cleanup_registry_records,bootstrap._run_roster_registry_read,bootstrap._bind_roster_registry_reader,
        bootstrap._bind_common_registry_reader,bootstrap._read_roster_registry_receipts,
        bootstrap._cleanup_roster_registry_records)=routes
    name='experiments.h1_group_execution_roster_development_v5'
    module=ModuleType(name);module.__file__=str(roster_path);module.__package__='experiments'
    module.__spec__=importlib.util.spec_from_file_location(name,roster_path);module.__loader__=module.__spec__.loader
    module.bootstrap=bootstrap;monkeypatch.setitem(sys.modules,name,module)
    exec(compile(roster_path.read_bytes(),module.__file__,'exec'),vars(module))
    def retain(*args):
        if state['retention_error'] is not None:raise state['retention_error']
    def create():
        return module.GroupRoster(owner,create=True,retain_head=retain,max_record_bytes=1024**2)
    def active_rows():return cells(bootstrap._run_roster_registry_read)['active']
    return SimpleNamespace(case=c,owner=owner,api=module,bootstrap=bootstrap,create=create,
        numerical=numerical,state=state,scopes=scopes,retired=retired,events=events,active_rows=active_rows)


def assert_retired(r):
    assert r.case.m.registry_validation_scope(r.owner) is None and r.owner._operation_nonce is None
    assert not r.active_rows()
    for proof,operations in r.retired:
        assert proof['closed']
        for operation in operations:
            assert operation._proof is operation._candidate_proof is None
            assert not operation._original_guard.locked()


def test_constructor_and_inspect_have_separate_retired_original_roster_scopes(roster_case):
    r=roster_case;actor=r.create()
    report=actor.inspect();observed=actor.registry_read_validation_receipt()
    assert report['maximum_attach_events']==3
    assert [row['mode'] for row in observed['reads']]==['constructor_owner_replay','replay','replay']
    proofs=[row['registry_execution'] for row in observed['reads']]
    assert len({p['session_identity'] for p in proofs})==3
    assert [row['replay_view_sites'] for row in observed['reads']]==[[],['replay_view_1','replay_view_2'],['replay_view_1','replay_view_2']]
    for proof in proofs:
        assert proof['complete'] and proof['consumer_route']=='roster_read'
        assert (proof['full_numerical_hour_replays'],proof['fresh_byte_context_revalidations'],proof['context_observations'])==(12,36,96)
    assert all(row[2] is None for row in r.events if row[0]=='registry')
    assert observed['pending_registry_records']==0 and observed['maximum_read_observations']==1024
    assert_retired(r);actor.close();r.bootstrap._cleanup_registry_records(r.owner)


def test_attach_scopes_end_before_callback_and_callback_direct_registry_is_denied(roster_case):
    r=roster_case;actor=r.create();before=actor.registry_read_validation_receipt()['successful_reads']
    actor.attach(r.numerical[0][1],expected_head=actor._journal.head)
    observed=actor.registry_read_validation_receipt();reads=observed['reads'][before:]
    assert [row['mode'] for row in reads]==['replay','view','view','view','replay']
    assert [row['caller_site'] for row in reads]==['attach_1','attach_1','_retain_group_head_1','_retain_group_head_2','attach_2']
    assert len({row['registry_execution']['session_identity'] for row in reads})==5
    assert any(row[0]=='callback' for row in r.events)
    assert_retired(r);actor.close()


@pytest.mark.parametrize('mode',['view','replay','constructor_owner_replay'])
def test_manually_held_guards_do_not_authorize_direct_consumer(roster_case,mode):
    r=roster_case;actor=r.create();before=len(r.case.contexts)
    actor._enter()
    try:
        with pytest.raises(ValueError,match='original|constructor'):
            if mode=='constructor_owner_replay':r.bootstrap._run_roster_registry_read(actor,mode)
            else:getattr(actor,'_'+mode)()
    finally:actor._leave()
    assert len(r.case.contexts)==before and not actor.poisoned
    assert_retired(r);actor.close()


@pytest.mark.parametrize('fault',['body','close','receipt','retire','composite'])
def test_original_constructor_primary_and_pending_cleanup_retry(roster_case,fault):
    r=roster_case;primary=RuntimeError('constructor primary')
    if fault in ('body','composite'):r.state['body_error']=primary
    if fault in ('close','receipt','retire'):r.state['cleanup_faults']={fault}
    elif fault=='composite':r.state['cleanup_faults']={'close','receipt','retire'}
    with pytest.raises(RuntimeError if fault in ('body','composite') else OSError) as caught:r.create()
    if fault in ('body','composite'):assert caught.value is primary
    assert not r.owner._original_operation.locked() and r.owner._operation_nonce is None
    assert not r.active_rows() and r.case.m.registry_validation_scope(r.owner) is None
    r.state['cleanup_faults'].clear();r.bootstrap._cleanup_registry_records(r.owner)
    assert_retired(r)


@pytest.mark.parametrize('fault',['producer_nonce','owner_guard','roster_guard','foreign_thread','shadow'])
def test_original_guard_nonce_creator_and_method_identity_fail_closed(roster_case,fault):
    r=roster_case;actor=r.create();before=len(r.case.contexts);errors=[]
    if fault=='producer_nonce':r.owner._operation_nonce=object()
    elif fault=='owner_guard':actor._owner_guard=Lock()
    elif fault=='roster_guard':actor._operation=Lock()
    elif fault=='shadow':actor._view=lambda:None
    def attempt():
        try:actor.inspect()
        except ValueError as error:errors.append(error)
    if fault=='foreign_thread':
        thread=Thread(target=attempt);thread.start();thread.join(timeout=5);assert not thread.is_alive()
    else:attempt()
    assert len(errors)==1 and len(r.case.contexts)==before
    r.owner._operation_nonce=None;actor._owner_guard=r.owner._original_operation
    actor._operation=actor._original_operation
    if fault=='shadow':del actor._view
    assert_retired(r);actor.close()
