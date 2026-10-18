"""Bridge lifecycle unit fixtures; no real Parent/roster or numeric admission."""
from pathlib import Path
import sys
from threading import Lock
from types import ModuleType, SimpleNamespace

import pytest

import experiments
from experiments import h1_common_validation_operation_development_v1 as original


@pytest.fixture
def case(tmp_path,monkeypatch):
    events=[];tokens={};fault=[None];all_guards=[]
    class Bundle:
        def __init__(self):
            self.held=[];self.marked=[];self.guards=(Lock(),Lock());all_guards.extend(self.guards)
            self.actual=SimpleNamespace(_reference_held=False)
        def enter(self):
            for guard in self.guards:guard.acquire();self.held.append(guard)
            self.actual._reference_held=True;self.marked=[self.actual]
            events.append('bundle_enter')
    class Genesis:
        def __init__(self):
            self.guards=(Lock(),Lock(),Lock());all_guards.extend(self.guards)
            self._original_operation=self.guards[0]
            attached={arm:dict(reference=dict(local_terminal=dict(body=dict(
                controller_root=str(tmp_path/arm),controller_binding_sha256='a'*64,
                controller_terminal_sha256='b'*64)))) for arm in ('cfe-only','joint-correct','network-only')}
            self._original_roster=SimpleNamespace(_direct=tuple(sorted(attached)),
                _replay=lambda:(attached,attached,'c'*64))
        def _enter(self):
            held=[]
            try:
                for i,guard in enumerate(self.guards):
                    if fault[0]=='common_enter_'+str(i):raise RuntimeError('common enter')
                    guard.acquire();held.append(guard)
                events.append('common_enter')
            except BaseException:
                for guard in reversed(held):guard.release()
                raise
    class Handoff:
        def __init__(self):
            self._guard=Lock();all_guards.append(self._guard)
            self._bundle=Bundle();self._genesis=Genesis();self._state='new'
        def _check(self):
            if self._state not in ('new','running'):raise ValueError('closed owner')
    def check():events.append('original_check')
    def begin(h):
        assert h._guard.locked() and id(h) not in tokens
        token=object();tokens[id(h)]=token;events.append('begin');return token
    def end(h,token):
        assert h._guard.locked() and tokens[id(h)] is token
        events.append('end');del tokens[id(h)]
        if fault[0]=='end':raise RuntimeError('end cleanup')
    def verify(h):
        if not h._guard.locked() or id(h) not in tokens:raise ValueError('original active token required')
    def record_bundle(h,token):
        assert tokens[id(h)] is token and all(g.locked() for g in h._bundle.held)
        events.append('record_bundle')
    def record_predecessor(h,token,guards,aliases):
        assert tokens[id(h)] is token and all(g.locked() for g in guards)
        events.append('record_predecessor')
    def resources(g):return g.guards,((g,'_original_operation',g._original_operation),)
    api=ModuleType('experiments.h1_selector_phase_handoff_development_v2')
    for name,value in dict(Handoff=Handoff,_CHECK=check,_VERIFY_OWNER=verify,_BEGIN=begin,_END=end,
            _RECORD_BUNDLE=record_bundle,_RECORD_PREDECESSOR=record_predecessor,
            _common_resources=resources,_Bundle=Bundle,
            common=SimpleNamespace(CommonOwnerGenesis=Genesis)).items():setattr(api,name,value)
    monkeypatch.setitem(sys.modules,api.__name__,api)
    monkeypatch.setattr(experiments,'h1_selector_phase_handoff_development_v2',api)
    name='experiments._common_operation_bridge_unit_'+tmp_path.name
    path=Path(original.__file__);module=ModuleType(name);module.__file__=str(path);module.__package__='experiments'
    monkeypatch.setitem(sys.modules,name,module)
    exec(compile(path.read_bytes(),str(path),'exec'),vars(module))
    witness=ModuleType('experiments.h1_operation_historical_witness_development_v2')
    class Session:
        def __init__(self,lease):
            self.lease=lease;self.closed=False;self.failure=None
            module._CLAIM_SESSION(lease,self);events.append('session_created')
            if fault[0]=='session_constructor':raise RuntimeError('session constructor')
        def close(self):
            self.closed=True;events.append('session_close')
            if fault[0]=='session_close':raise RuntimeError('session cleanup')
        def _poison(self,error):self.failure=repr(error)
        def receipt(self):return dict(closed=self.closed,first_failure=self.failure)
    witness.GroupWitnessSession=Session
    monkeypatch.setitem(sys.modules,witness.__name__,witness)
    monkeypatch.setattr(experiments,'h1_operation_historical_witness_development_v2',witness,raising=False)
    common=ModuleType('experiments.h1_group_n0_common_input_binding_development_v3')
    def prepare(session):
        module._VERIFY_LEASE(session.lease)
        if fault[0]=='prepare':raise RuntimeError('common preparation')
        return 'unit-only-result'
    common.prepare=prepare
    monkeypatch.setitem(sys.modules,common.__name__,common)
    monkeypatch.setattr(experiments,'h1_group_n0_common_input_binding_development_v3',common,raising=False)
    owner=Handoff();operation=module.GuardedCommonOperation(owner)
    return SimpleNamespace(m=module,owner=owner,operation=operation,events=events,tokens=tokens,
        fault=fault,guards=all_guards,api=api)


def released(case):
    assert not any(g.locked() for g in case.guards)
    assert not case.owner._bundle.actual._reference_held
    assert not case.owner._bundle.held and not case.owner._bundle.marked
    assert not case.tokens


def test_only_bridge_entry_issues_token_lease_and_holds_all_original_guards(case):
    with case.operation as scope:
        lease=scope._lease
        assert all(g.locked() for g in case.guards)
        roster,declarations,limit=case.m._VERIFY_LEASE(lease)
        assert len(declarations)==3 and limit==2
        assert scope.prepare_common()=='unit-only-result'
        assert case.events.index('begin')<case.events.index('bundle_enter')<case.events.index('common_enter')
        assert case.events.index('record_predecessor')<case.events.index('session_created')
    released(case)
    assert scope.receipt()['closed'] and case.owner._state=='failed'
    with pytest.raises(ValueError,match='absent or closed'):case.m._VERIFY_LEASE(lease)


def test_foreign_or_unissued_lease_is_never_a_token_credential(case):
    with pytest.raises(TypeError):case.m._Lease()
    forged=object.__new__(case.m._Lease)
    with pytest.raises(ValueError,match='absent or closed'):case.m._VERIFY_LEASE(forged)
    with pytest.raises(TypeError):case.m._VERIFY_LEASE(object())
    assert not case.tokens


@pytest.mark.parametrize('index',[0,1,2])
def test_partial_common_acquisition_failure_releases_only_captured_acquired_guards(case,index):
    case.fault[0]='common_enter_'+str(index)
    with pytest.raises(RuntimeError,match='common enter'):case.operation.__enter__()
    released(case)
    assert 'end' in case.events and 'session_created' not in case.events


def test_constructor_failure_after_claim_cleans_session_and_original_locks(case):
    case.fault[0]='session_constructor'
    with pytest.raises(RuntimeError,match='session constructor'):case.operation.__enter__()
    released(case);assert 'session_close' in case.events


@pytest.mark.parametrize('fault',['session_close','end'])
def test_cleanup_failure_still_releases_all_guards_and_preserves_body_exception(case,fault):
    with pytest.raises(ValueError,match='body failure') as caught:
        with case.operation:
            case.fault[0]=fault
            raise ValueError('body failure')
    released(case)
    assert caught.value.__notes__ and case.operation.receipt()['first_failure']


def test_cleanup_failure_cannot_return_success(case):
    with pytest.raises(RuntimeError,match='session cleanup'):
        with case.operation:case.fault[0]='session_close'
    released(case)
    assert case.operation.receipt()['first_failure']


def test_common_failure_poisons_original_session_then_cleans(case):
    with pytest.raises(RuntimeError,match='common preparation'):
        with case.operation as scope:
            case.fault[0]='prepare';scope.prepare_common()
    released(case)
    assert scope.receipt()['first_failure']


def test_bridge_method_drift_fails_checks_but_original_cleanup_still_runs(case,monkeypatch):
    with case.operation as scope:
        monkeypatch.setattr(case.m.GuardedCommonOperation,'_release',lambda *a:(_ for _ in ()).throw(AssertionError('replaced cleanup')))
        with pytest.raises(ValueError,match='dispatch changed'):scope.prepare_common()
    released(case)


def test_original_begin_function_drift_is_rejected_before_acquisition(case,monkeypatch):
    monkeypatch.setattr(case.api,'_BEGIN',lambda *a:None)
    with pytest.raises(ValueError,match='dispatch changed'):case.operation.__enter__()
    released(case)


def test_same_operation_cannot_reenter_and_never_issues_second_token(case):
    with case.operation:
        with pytest.raises(ValueError,match='single-use'):case.operation.__enter__()
        assert case.events.count('begin')==1
    released(case)
