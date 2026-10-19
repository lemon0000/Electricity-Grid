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
from types import FunctionType

import pytest

from tests.h1_hour0_synthetic_harness_v2 import load
from tests import test_h1_common_owner_genesis_development_v1 as cases
from tests.test_h1_hour0_persistence_faults_development_v2 import setup,legacy_setup


class FaultGuard:
    """Real lock with a single explicit test-only outer-release failure."""
    def __init__(self,faults):self.lock=Lock();self.faults=faults
    def acquire(self,*args):return self.lock.acquire(*args)
    def locked(self):return self.lock.locked()
    def release(self):
        if self.faults.pop('external_guard_release_once',False):
            raise RuntimeError('synthetic outer common guard release failure')
        return self.lock.release()


@pytest.fixture
def case(setup,tmp_path,monkeypatch):
    root=Path(cases.m.__file__).parent
    host=load(str(root/'h1_common_owner_genesis_development_v2.py'),'explicit_genesis_adapter_host',monkeypatch)
    old_cases=cases.m;monkeypatch.setattr(cases,'m',host)
    c=cases.case.__wrapped__(setup,tmp_path,monkeypatch)
    monkeypatch.setattr(cases,'m',old_cases)
    faults={};extra=FaultGuard(faults);owner=object.__new__(host.bootstrap.BootstrapOwner)
    vars(owner).update(vars(c.roster._owner));owner._operation=extra
    c.roster._owner=c.roster._original_owner=owner
    c.roster._operation=c.roster._original_operation=c.guard;c.roster._owner_guard=extra
    guard=c.guard;global_state=c.global_
    def enter():
        if not guard.acquire(False):raise ValueError('roster active')
        if not extra.acquire(False):guard.release();raise ValueError('bootstrap active')
    def leave():
        if faults.get('leave_before'):raise RuntimeError('synthetic original leave failure')
        extra.release()
        if faults.get('leave_partial'):raise RuntimeError('synthetic partial leave failure')
        guard.release()
    c.roster._enter=enter;c.roster._leave=leave
    c.roster._direct=('cfe','joint','network')
    declarations={arm:dict(reference=dict(local_terminal=dict(body=dict(
        controller_root=str(tmp_path/(arm+'_n0_non_authoritative')),
        controller_binding_sha256='a'*64,controller_terminal_sha256='b'*64)))) for arm in c.roster._direct}
    c.roster._replay=lambda:(deepcopy(declarations),(),global_state.head)
    sessions=[];calls=[]
    from experiments import h1_group_n0_common_input_binding_development_v2 as common_api
    kernel=ModuleType('explicit_fake_Genesis_numerical_route_kernel')
    kernel.implementation_identity=lambda:'a'*64
    def routes(bridge):
        class Result:pass
        class Source:pass
        class Session:
            def __init__(self,lease):
                if faults.get('ctor_preclaim'):raise RuntimeError('synthetic session preclaim failure')
                self._lease=lease;self._nonce=object();self._common_calls=0;self.rows=[]
                self.failure=None;self.closed=False
                self.roster,_,self.limit=bridge._VERIFY_LEASE(lease)
                sessions.append(self);bridge._CLAIM_SESSION(lease,self)
                if faults.get('ctor_postclaim'):raise RuntimeError('synthetic session postclaim failure')
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
            if faults.get('prepare_at')==index:
                error=faults.get('prepare_error')
                raise error if error is not None else RuntimeError('first synthetic common failure')
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
    adapter=load(str(root/'h1_common_genesis_validation_operation_development_v2.py'),
        'explicit_genesis_adapter_test',monkeypatch,
        {'h1_common_genesis_validation_routes_development_v2':kernel})
    c.host=host;c.adapter=adapter;c.extra=extra;c.faults=faults;c.sessions=sessions;c.calls=calls;c.phase_setup=setup
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


@pytest.mark.parametrize('capture',['instance','slots','dict_key','private_globals','annotation','function_attribute'])
def test_preloaded_ordinary_instances_and_private_globals_are_rejected(case,monkeypatch,capture):
    c=case;consumer=ModuleType('explicit_preloaded_Genesis_instance');consumer.__file__=__file__
    target=c.host.CommonOwnerGenesis.inspect
    if capture in ('instance','slots'):
        attrs={'__module__':__name__}
        if capture=='slots':attrs['__slots__']=('held',)
        value=type('Captured',(),attrs)();value.held=target
    elif capture=='dict_key':value={target:None}
    elif capture=='private_globals':
        def template():return common
        value=FunctionType(template.__code__,{'common':c.host})
    else:
        def value():return None
        if capture=='annotation':value.__annotations__={'return':target}
        else:value.saved=target
    consumer.held=value;monkeypatch.setitem(sys.modules,consumer.__name__,consumer)
    with pytest.raises(ValueError,match='precede every project consumer'):c.adapter.operation(c.host)
    assert c.host.CommonOwnerGenesis.inspect is c.original['inspect']


def test_empty_scope_does_not_claim_observed_method_success(case):
    context,receipt=case.adapter.operation(case.host)
    with context:pass
    r=receipt();assert r['observed_method_window_count']==0
    assert not r['all_observed_method_windows_successful'] and not r['complete_workflow_observed']
    assert r['all_aliases_restored'] and r['all_private_sessions_cleared']


@pytest.mark.parametrize('fault',['ctor_preclaim','ctor_postclaim','leave_before','leave_partial'])
def test_constructor_and_guard_release_faults_clear_original_resources(case,fault):
    c=case;context,receipt=c.adapter.operation(c.host)
    with context:
        c.faults[fault]=True
        with pytest.raises(RuntimeError,match='synthetic'):create(c)
        assert not c.guard.locked() and not c.extra.locked()
        assert all(s.closed for s in c.sessions)
    r=receipt();assert r['all_private_sessions_cleared']
    assert not r['method_receipts'][0]['complete']


def test_first_body_failure_survives_original_leave_failure(case):
    c=case;context,receipt=c.adapter.operation(c.host)
    with context:
        c.faults.update(prepare_at=3,leave_before=True)
        with pytest.raises(RuntimeError,match='first synthetic common failure') as error:create(c)
        assert any('leave' in note for note in error.value.__notes__)
        assert not c.guard.locked() and not c.extra.locked()
    assert receipt()['all_private_sessions_cleared']


def test_reconcile_is_rejected_before_any_genesis_write(case):
    c=case;context,receipt=c.adapter.operation(c.host)
    with context:
        with pytest.raises(ValueError,match='does not support reconcile'):
            c.host.CommonOwnerGenesis(c.roster,create=False,**c.options,expected_head='a'*64,reconcile=True)
    assert not (c.study/'common_owners_non_authoritative').exists()
    assert receipt()['observed_method_window_count']==0


@pytest.mark.parametrize('fault',['foreign_package','property_code'])
def test_real_cold_routes_restore_only_owned_aliases_and_check_property_code(monkeypatch,fault):
    import experiments
    from experiments import h1_common_genesis_validation_routes_development_v2 as kernel
    from experiments import h1_common_genesis_validation_operation_development_v2 as bridge
    routes=kernel.load(bridge)
    try:
        if fault=='foreign_package':
            name=kernel.ROUTES[-1][0];foreign=ModuleType('foreign_route_alias')
            setattr(experiments,name,foreign)
            with pytest.raises(ValueError,match='provenance'):routes['check']()
        else:
            source_module=sys.modules['experiments.'+kernel.ROUTES[1][0]]
            descriptor=next(value for kind in vars(source_module).values()
                if isinstance(kind,type) and kind.__module__==source_module.__name__
                for value in vars(kind).values() if isinstance(value,property))
            original=descriptor.fget.__code__
            def changed(self):return None
            descriptor.fget.__code__=changed.__code__
            try:
                with pytest.raises(ValueError,match='runtime route'):routes['check']()
            finally:descriptor.fget.__code__=original
    finally:closed=routes['unload']()
    if fault=='foreign_package':
        assert getattr(experiments,name) is foreign and closed['errors']
        delattr(experiments,name)
    else:assert closed['all_route_aliases_removed']
    assert all('experiments.'+name not in sys.modules for name,_ in kernel.ROUTES)


def test_existing_foreign_hook_rolls_back_half_installation(case,monkeypatch):
    c=case;old=c.host.implementation_identity;foreign=lambda *args:None
    monkeypatch.setattr(c.host,c.adapter.EXTERNAL_FINALIZER,foreign,raising=False)
    context,receipt=c.adapter.operation(c.host)
    with pytest.raises(ValueError,match='fresh Genesis external hook'):
        with context:pass
    assert c.host.implementation_identity is old
    assert getattr(c.host,c.adapter.EXTERNAL_FINALIZER) is foreign
    assert all(getattr(c.host.CommonOwnerGenesis,n) is f for n,f in c.original.items())
    r=receipt();assert r['all_host_aliases_restored'] and r['all_private_sessions_cleared']


def test_retained_resource_failure_cleans_registered_begin_and_keeps_first_error(case,monkeypatch):
    c=case;close=c.host.phase.DevelopmentOwner.close;faults=c.faults
    def failing_close(owner):
        close(owner)
        if faults.get('close_failure'):raise RuntimeError('secondary captured close failure')
    monkeypatch.setattr(c.host.phase.DevelopmentOwner,'close',failing_close)
    context,receipt=c.adapter.operation(c.host)
    with context:
        owner=create(c);replay=c.roster._replay
        def changed_replay():
            value=replay();owner._original_holder=object();return value
        monkeypatch.setattr(c.roster,'_replay',changed_replay)
        faults.update(close_failure=True,leave_before=True)
        with pytest.raises(ValueError,match='owned resource changed') as error:owner.inspect()
        assert any('cleanup' in note for note in error.value.__notes__)
        assert owner.closed and owner.poisoned
        assert not owner._operation.locked() and not c.guard.locked() and not c.extra.locked()
    r=receipt();assert r['all_private_sessions_cleared']
    assert r['method_receipts'][-1]['plan']=='inspect' and not r['method_receipts'][-1]['complete']


def test_unclosed_owner_is_retained_until_scope_cleanup(case):
    import gc,weakref
    c=case;context,receipt=c.adapter.operation(c.host)
    with pytest.raises(ValueError,match='all Genesis owners must close'):
        with context:
            owner=create(c);ref=weakref.ref(owner);del owner;gc.collect()
            assert ref() is not None
    r=receipt();assert r['all_private_sessions_cleared'] and r['first_failure']
    assert not c.guard.locked() and not c.extra.locked()


def test_same_schema_fabricated_consumer_cannot_acquire_genesis(case):
    c=case;context,receipt=c.adapter.operation(c.host)
    with context:
        with create(c) as owner:
            fake={'SCHEMA':'h1_selector_input_snapshot_development_v2','common':c.host}
            exec('def _capture(owner):\n    owner._enter()\n',fake)
            with pytest.raises(ValueError,match='fixed Genesis method or consumer'):fake['_capture'](owner)
            assert owner.inspect()['stage']==3
    assert receipt()['observed_external_window_count']==0


def test_preexisting_local_owner_cannot_enter_active_adapter(case):
    c=case;owner=create(c)
    try:
        context,receipt=c.adapter.operation(c.host)
        with context:
            with pytest.raises(ValueError,match='active observation identity'):owner.inspect()
            assert not owner._operation.locked() and not owner.closed
        assert receipt()['observed_method_window_count']==0
    finally:owner.close()


def test_falsey_body_error_survives_cleanup_errors(case):
    class FalseyFailure(RuntimeError):
        def __bool__(self):return False
    c=case;context,receipt=c.adapter.operation(c.host);original=FalseyFailure('first falsey failure')
    with context:
        c.faults.update(prepare_at=3,prepare_error=original,leave_before=True)
        with pytest.raises(FalseyFailure) as failure:create(c)
        assert failure.value is original
        assert not c.guard.locked() and not c.extra.locked()
    assert receipt()['method_receipts'][0]['first_failure']==repr(original)


@pytest.mark.parametrize('fault',['function_code','descriptor_code','spec_loader','spec_name',
    'function_delete','function_none','descriptor_delete','descriptor_none'])
def test_sequence_pre_operation_mutation_is_not_a_valid_baseline(case,monkeypatch,fault):
    from experiments import h1_owned_selector_sequence_development_v1 as sequence
    c=case
    with monkeypatch.context() as patch:
        if fault.startswith('spec_'):
            patch.setattr(sequence.__spec__,fault[5:],object() if fault=='spec_loader' else 'foreign.sequence')
            message='canonical Genesis sequence provenance'
        elif fault in ('function_code','descriptor_code'):
            target=sequence.inspect if fault=='function_code' else vars(sequence.OwnedSelectorSequence)['_receipt_snapshot'].__func__
            def changed(*args,**kwargs):return None
            patch.setattr(target,'__code__',changed.__code__)
            message='original Genesis sequence source function'
        else:
            target,field=(sequence,'inspect') if fault.startswith('function') else (sequence.OwnedSelectorSequence,'_receipt_snapshot')
            if fault.endswith('delete'):patch.delattr(target,field)
            else:patch.setattr(target,field,None)
            message='original Genesis sequence source function'
        with pytest.raises(ValueError,match=message):c.adapter.operation(c.host)
    assert all(getattr(c.host.CommonOwnerGenesis,name) is fn for name,fn in c.original.items())
    assert not (c.study/'common_owners_non_authoritative').exists()


def test_raw_stream_fallback_keeps_unattributed_registry_key(case,monkeypatch):
    c=case;faults={};original=c.host.phase.DevelopmentOwner.close
    def failed_close(owner):
        if faults.get('close'):
            owner.closed=True
            raise RuntimeError('synthetic typed close failure before raw stream')
        return original(owner)
    monkeypatch.setattr(c.host.phase.DevelopmentOwner,'close',failed_close)
    context,receipt=c.adapter.operation(c.host)
    registry=c.host.bootstrap.local._REGISTRY;guard=c.host.bootstrap.local._REGISTRY_LOCK
    key=None
    try:
        with pytest.raises(BaseExceptionGroup,match='Genesis adapter cleanup failed'):
            with context:
                owner=create(c);phase=owner._original_phase;lease=phase._lease_object
                raw=lease.stream;key=lease.key
                # Reproduce the failed closer's finally flags. The key is
                # deliberately unattributed; no owner token exists in this set.
                phase.closed=owner.closed=True;lease.stream=None;lease.locked=False
                faults['close']=True
                assert not raw.closed and key in registry
        assert raw.closed and lease.stream is None and not lease.locked
        assert key in registry
        closed=receipt();assert closed['all_private_sessions_cleared'] and closed['cleanup_errors']
        assert closed['all_aliases_restored']
    finally:
        # Remove only this test's deliberately retained registration after
        # proving that the adapter itself preserved it and closed the handle.
        if key is not None:
            with guard:registry.discard(key)
