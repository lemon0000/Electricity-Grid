"""Real Genesis journals/SQLite with explicit fake roster and numerical routes.

Counts test the bridge's state machine, not historical numerical execution.
The separate cold definition check uses the actual pinned local route modules.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
from threading import Lock,Thread
from types import ModuleType,SimpleNamespace as NS

import pytest

from tests.h1_hour0_synthetic_harness_v2 import load
from tests import test_h1_common_owner_genesis_development_v1 as cases
from tests.test_h1_hour0_persistence_faults_development_v2 import setup,legacy_setup


@pytest.fixture
def case(setup,tmp_path,monkeypatch):
    root=Path(cases.m.__file__).parent
    host=load(str(root/'h1_common_owner_genesis_development_v2.py'),'explicit_genesis_adapter_host',monkeypatch)
    old_cases=cases.m;monkeypatch.setattr(cases,'m',host)
    c=cases.case.__wrapped__(setup,tmp_path,monkeypatch)
    monkeypatch.setattr(cases,'m',old_cases)
    extra=Lock();owner=object.__new__(host.bootstrap.BootstrapOwner)
    vars(owner).update(vars(c.roster._owner));owner._operation=extra
    c.roster._owner=c.roster._original_owner=owner
    c.roster._operation=c.roster._original_operation=c.guard;c.roster._owner_guard=extra
    def enter():
        if not c.guard.acquire(False):raise ValueError('roster active')
        if not extra.acquire(False):c.guard.release();raise ValueError('bootstrap active')
    def leave():extra.release();c.guard.release()
    c.roster._enter=enter;c.roster._leave=leave
    c.roster._direct=('cfe','joint','network')
    declarations={arm:dict(reference=dict(local_terminal=dict(body=dict(
        controller_root=str(tmp_path/(arm+'_n0_non_authoritative')),
        controller_binding_sha256='a'*64,controller_terminal_sha256='b'*64)))) for arm in c.roster._direct}
    c.roster._replay=lambda:(deepcopy(declarations),(),c.global_.head)
    faults={};sessions=[];calls=[]
    from experiments import h1_group_n0_common_input_binding_development_v2 as common_api
    kernel=ModuleType('explicit_fake_Genesis_numerical_route_kernel')
    kernel.implementation_identity=lambda:'a'*64
    def routes(bridge):
        class Result:pass
        class Source:pass
        class Session:
            def __init__(self,lease):
                self._lease=lease;self._nonce=object();self._common_calls=0;self.rows=[]
                self.failure=None;self.closed=False
                self.roster,_,self.limit=bridge._VERIFY_LEASE(lease)
                sessions.append(self);bridge._CLAIM_SESSION(lease,self)
            def _poison(self,error):
                if self.failure is None:self.failure=repr(error)
            def close(self):self.closed=True
            def receipt(self):
                return dict(closed=self.closed,complete=self.closed and self.failure is None
                    and self._common_calls==self.limit,common_calls=self._common_calls,
                    common_executions=deepcopy(self.rows),first_failure=self.failure,
                    arm_receipts={arm:dict(proof_cleared=self.closed) for arm in self.roster._direct},
                    explicit_fake_numerical_routes=True,formal_result=False)
        def common(session):
            bridge._BOOKEND(session._lease);index=session._common_calls+1
            if faults.get('prepare_at')==index:raise RuntimeError('first synthetic common failure')
            manifest,binding,report=common_api._prepare_locked(session.roster)
            value=Result();value.manifest=manifest;value.source_binding=binding
            value.validation_report_payload=common_api.encode(report)
            value.predecessor_report_payload=common_api.encode(report);value._session_nonce=session._nonce
            bridge._COMMON_RESULT(session._lease,value,session)
            session._common_calls+=1;calls.append(index)
            session.rows.append(dict(full_numerical_hour_replays=24 if index==1 else 0,
                within_prefix_revalidations=24 if index==1 else 0,
                cross_common_numerical_proof_reuses=0 if index==1 else 48,context_evaluations=96))
            return value
        return dict(check=lambda:None,session_type=Session,source_type=Source,common_type=Result,
            common_entry=common,source_entry=lambda *a,**kw:Source(),
            unload=lambda:dict(all_route_aliases_removed=True,removed_aliases=[],errors=[]),
            manifest=dict(explicit_fake_numerical_routes=True,formal_result=False))
    kernel.load=routes
    adapter=load(str(root/'h1_common_genesis_validation_operation_development_v1.py'),
        'explicit_genesis_adapter_test',monkeypatch,
        {'h1_common_genesis_validation_routes_development_v1':kernel})
    c.host=host;c.adapter=adapter;c.extra=extra;c.faults=faults;c.sessions=sessions;c.calls=calls
    c.original={name:getattr(host.CommonOwnerGenesis,name) for name in
        ('__init__','_enter','_leave','_correspondence','inspect')}
    return c


def create(c,**options):return c.host.CommonOwnerGenesis(c.roster,create=True,**(c.options|options))
def reopen(c):
    return c.host.CommonOwnerGenesis(c.roster,create=False,**c.options,expected_head=c.retained['head'],
        holder_receipt=c.retained['holder'],owner_receipt=c.retained['owner'])


def test_create_inspect_reopen_have_fixed_plans_and_active_persistent_identity(case):
    c=case;old=c.host.implementation_identity();context,receipt=c.adapter.operation(c.host)
    with pytest.raises(ValueError,match='closed'):receipt()
    with context:
        active=c.host.implementation_identity();assert active!=old
        with create(c) as owner:
            assert owner._implementation==active
            assert json.loads(owner._journal._header)['declaration']['implementation']==active
            assert owner.inspect()['stage']==3
        with reopen(c) as owner:assert owner.inspect()['stage']==3
    assert c.host.implementation_identity()==old
    for name,fn in c.original.items():assert getattr(c.host.CommonOwnerGenesis,name) is fn
    r=receipt();assert r['all_aliases_restored'] and r['all_private_sessions_cleared']
    assert [item['plan'] for item in r['method_receipts']]==['create','inspect','reopen','inspect']
    assert [item['common_calls'] for item in r['method_receipts']]==[15,2,3,2]
    assert all(s.closed for s in c.sessions)
    assert not c.guard.locked() and not c.extra.locked()
    assert r['post_scope_consumer_reuse_allowed'] is False
    with pytest.raises(ValueError):reopen(c)


@pytest.mark.parametrize('fault',['prepare','callback','caught_reentry','callback_correspondence','metadata'])
def test_failure_poison_clears_session_preserves_first_error_and_releases_guards(case,fault):
    c=case;context,receipt=c.adapter.operation(c.host);seen=[];nested=[]
    original=c.options['retain_binder_head']
    def retain(root,before,after):
        owner=sys._getframe(1).f_locals['self'];seen.append(owner)
        if fault=='callback':raise RuntimeError('first callback failure')
        if fault in ('caught_reentry','callback_correspondence'):
            try:owner.inspect() if fault=='caught_reentry' else owner._correspondence()
            except ValueError as error:nested.append(str(error))
        if fault=='metadata':c.report['common_scientific_identity']='e'*64
        return original(root,before,after)
    with context:
        if fault=='prepare':c.faults['prepare_at']=3
        with pytest.raises((ValueError,RuntimeError)) as failure:create(c,retain_binder_head=retain)
        assert not c.guard.locked() and not c.extra.locked() and all(s.closed for s in c.sessions)
        if seen:assert seen[0].closed and seen[0].poisoned
        if fault=='callback':assert 'first callback failure' in str(failure.value)
        if fault=='prepare':assert 'first synthetic common failure' in str(failure.value)
        if fault.startswith('caught') or fault=='callback_correspondence':assert nested
    r=receipt();assert r['all_private_sessions_cleared']
    assert not r['method_receipts'][0]['complete'] and r['method_receipts'][0]['first_failure']


def test_preloaded_consumer_descriptor_rejected_before_any_patch(case,monkeypatch):
    c=case;consumer=ModuleType('explicit_preloaded_Genesis_consumer')
    consumer.__file__=__file__;consumer.pinned=(c.host.CommonOwnerGenesis.inspect,)
    monkeypatch.setitem(sys.modules,consumer.__name__,consumer)
    with pytest.raises(ValueError,match='precede every project consumer'):c.adapter.operation(c.host)
    assert c.host.CommonOwnerGenesis.inspect is c.original['inspect']


def test_foreign_thread_rejected_without_poisoning_creator(case):
    c=case;context,receipt=c.adapter.operation(c.host);errors=[]
    with context:
        with create(c) as owner:
            def foreign():
                try:owner.inspect()
                except ValueError as error:errors.append(str(error))
            thread=Thread(target=foreign);thread.start();thread.join(timeout=3)
            assert errors and not thread.is_alive()
            assert owner.inspect()['stage']==3
    assert all(row['complete'] for row in receipt()['method_receipts'])


def test_foreign_replacement_is_preserved_at_restore(case):
    c=case;context,receipt=c.adapter.operation(c.host);foreign=lambda self:None
    with pytest.raises(ValueError,match='host/dispatch'):
        with context:
            with create(c):pass
            c.host.CommonOwnerGenesis.inspect=foreign
    assert c.host.CommonOwnerGenesis.inspect is foreign
    r=receipt();assert not r['all_aliases_restored'] and r['cleanup_errors']
    assert r['all_private_sessions_cleared']
