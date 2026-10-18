"""Bridge lifecycle fixtures with a pre-definition AST-only route constant seam.

These fixtures do not test production byte admission or a real Parent/roster.
The public bridge accepts no caller paths, hashes, callbacks or loaders.
"""
import ast
import json
from pathlib import Path
from hashlib import sha256
import sys
from threading import Lock
from types import ModuleType, SimpleNamespace

import pytest

import experiments
from experiments import h1_common_validation_operation_development_v1 as original


@pytest.fixture
def case(tmp_path,monkeypatch,request):
    events=[];tokens={};fault=[None];all_guards=[]
    class Guard:
        def __init__(self,tag):self.raw=Lock();self.tag=tag;all_guards.append(self)
        def acquire(self,*a):return self.raw.acquire(*a)
        def locked(self):return self.raw.locked()
        def release(self):
            self.raw.release();events.append('release '+self.tag)
            if fault[0]=='guard_'+self.tag:raise RuntimeError('guard cleanup '+self.tag)
    class Mark:
        def __init__(self):self._reference_held=False
        def __setattr__(self,name,value):
            object.__setattr__(self,name,value)
            if name=='_reference_held' and value is False and fault[0]=='mark_reset':
                raise RuntimeError('mark cleanup')
    class Bundle:
        def __init__(self):
            self.held=[];self.marked=[];self.guards=(Guard('parent0'),Guard('parent1'))
            self.actual=Mark()
        def __setattr__(self,name,value):
            object.__setattr__(self,name,value)
            if name in ('held','marked') and value==[] and fault[0]=='bundle_'+name:
                raise RuntimeError('bundle cleanup '+name)
        def enter(self):
            for guard in self.guards:guard.acquire();self.held.append(guard)
            self.actual._reference_held=True;self.marked=[self.actual]
            events.append('bundle_enter')
    class Genesis:
        def __init__(self):
            self.guards=tuple(Guard('common'+str(i)) for i in range(3))
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
            self._guard=Guard('outer')
            self._bundle=Bundle();self._genesis=Genesis();self._state='new'
        def __setattr__(self,name,value):
            object.__setattr__(self,name,value)
            if name=='_state' and value=='failed' and fault[0]=='owner_state':
                raise RuntimeError('owner state cleanup')
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
    monkeypatch.setattr(experiments,name.rsplit('.',1)[1],module,raising=False)
    class Session:
        def __init__(self,lease):
            self.lease=lease;self.closed=False;self.failure=None;self._common_calls=0;self._nonce=object()
            module._CLAIM_SESSION(lease,self);events.append('session_created')
            if fault[0]=='session_constructor':raise RuntimeError('session constructor')
        def close(self):
            self.closed=True;events.append('session_close')
            if fault[0]=='session_close':raise RuntimeError('session cleanup')
        def _poison(self,error):self.failure=repr(error)
        def receipt(self):return dict(closed=self.closed,first_failure=self.failure,
            complete=self.closed and self.failure is None and self._common_calls==2)
    class Arm:pass
    class SourceBundle:pass
    class CommonResult:
        def __init__(self,session):self._session_nonce=session._nonce
    def source_prepare(*args,**kwargs):raise AssertionError('unit bridge must not perform numerical source replay')
    def prepare(session):
        module._VERIFY_LEASE(session.lease)
        if fault[0]=='prepare':raise RuntimeError('common preparation')
        session._common_calls+=1
        return CommonResult(session)
    helper_name='unit_common_routes_'+tmp_path.name
    helper=ModuleType(helper_name)
    for field,value in dict(Session=Session,Arm=Arm,SourceBundle=SourceBundle,CommonResult=CommonResult,
            prepare=prepare,source_prepare=source_prepare,bridge=module).items():setattr(helper,field,value)
    monkeypatch.setitem(sys.modules,helper_name,helper)
    route_names=original._ROUTE_NAMES
    bodies=[f'from {helper_name} import Session as GroupWitnessSession, Arm as ArmWitness, bridge as operation_bridge\n',
        f'from {helper_name} import SourceBundle as CommonSourceBundle, source_prepare as prepare_common_bundle\nfrom experiments import h1_operation_historical_witness_development_v2 as witness\n',
        f'from {helper_name} import CommonResult as PreparedCommonInput, prepare\nfrom experiments import h1_operation_historical_witness_development_v2 as witness\nfrom experiments import h1_phase_exact_source_current_development_v3 as source\n']
    variant=getattr(request,'param',None)
    if variant:
        kind,index=variant;index=int(index)
        if kind=='compile':bodies[index]+='invalid python syntax !\n'
        elif kind=='exec':bodies[index]+='raise RuntimeError("original route execution")\n'
        elif kind=='edge':bodies[index]+='source=object()\n'
        elif kind=='observation':bodies[index]+='__file__="foreign-route"\n'
        elif kind=='foreign':bodies[index]+=(
            'import sys, experiments\nfrom types import ModuleType\n'
            'foreign=ModuleType("foreign-preserved")\n'
            'sys.modules[__name__]=foreign\n'
            'setattr(experiments,__name__.rsplit(".",1)[1],foreign)\n'
            'raise RuntimeError("original route execution")\n')
    sources={name:dict(path=str(path.resolve()),sha256=sha256(path.read_bytes()).hexdigest())}
    for route,body in zip(route_names,bodies):
        monkeypatch.delitem(sys.modules,route,raising=False)
        monkeypatch.delattr(experiments,route.rsplit('.',1)[1],raising=False)
        source_path=tmp_path/(route.rsplit('.',1)[1]+'.py');source_path.write_text(body,encoding='utf-8')
        sources[route]=dict(path=str(source_path.resolve()),sha256=sha256(source_path.read_bytes()).hexdigest())
    # Only this unit fixture changes the expected literal before definition;
    # no equivalent override exists in the real public constructor or loader.
    tree=ast.parse(path.read_bytes(),filename=str(path))
    replacement=tuple((route,sources[route]['path'],sources[route]['sha256']) for route in route_names)
    targets=[node for node in tree.body if isinstance(node,ast.Assign)
        and any(isinstance(t,ast.Name) and t.id=='_PINNED_ROUTES' for t in node.targets)]
    assert len(targets)==1
    targets[0].value=ast.parse(repr(replacement),mode='eval').body
    ast.fix_missing_locations(tree)
    exec(compile(tree,str(path),'exec'),vars(module))
    owner=Handoff();operation=module.GuardedCommonOperation(owner)
    return SimpleNamespace(m=module,owner=owner,operation=operation,events=events,tokens=tokens,
        fault=fault,guards=all_guards,api=api,source_inputs=sources)


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
        first=scope.prepare_common();second=scope.prepare_common()
        assert type(first) is type(second)
        assert case.events.index('begin')<case.events.index('bundle_enter')<case.events.index('common_enter')
        assert case.events.index('record_predecessor')<case.events.index('session_created')
    released(case)
    assert scope.receipt()['closed'] and case.owner._state=='failed'
    receipt=scope.receipt()
    rows=sorted((value['module'],value['path'],value['sha256']) for value in receipt['validation_route_sources'])
    raw=json.dumps(rows,ensure_ascii=True,separators=(',',':')).encode('ascii')
    assert sha256(raw).hexdigest()==receipt['validation_route_manifest_sha256']
    assert len(rows)==4 and {value[0] for value in rows}==set(case.source_inputs)
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
    with pytest.raises(ValueError,match='dispatch changed'):
        with case.operation as scope:
            monkeypatch.setattr(case.m.GuardedCommonOperation,'_release',lambda *a:(_ for _ in ()).throw(AssertionError('replaced cleanup')))
            scope.prepare_common()
    released(case)


def test_original_begin_function_drift_is_rejected_before_acquisition(case,monkeypatch):
    monkeypatch.setattr(case.api,'_BEGIN',lambda *a:None)
    with pytest.raises(ValueError,match='dispatch changed'):case.operation.__enter__()
    released(case)


def test_same_operation_cannot_reenter_and_never_issues_second_token(case):
    with case.operation:
        with pytest.raises(ValueError,match='single-use'):case.operation.__enter__()
        assert case.events.count('begin')==1
        case.operation.prepare_common();case.operation.prepare_common()
    released(case)


@pytest.mark.parametrize('calls',[0,1])
def test_normal_early_exit_fails_after_all_cleanup(case,calls):
    with pytest.raises(ValueError,match='two complete common'):
        with case.operation as scope:
            for _ in range(calls):scope.prepare_common()
    released(case)
    assert scope.receipt()['first_failure']


@pytest.mark.parametrize('route',original._ROUTE_NAMES)
@pytest.mark.parametrize('kind',['package_attribute','sys_modules','source_file'])
def test_fixed_import_route_drift_is_rejected_and_original_cleanup_runs(case,monkeypatch,route,kind):
    with pytest.raises(ValueError,match='import route changed'):
        with case.operation as scope:
            if kind=='package_attribute':monkeypatch.setattr(experiments,route.rsplit('.',1)[1],ModuleType('foreign'))
            elif kind=='sys_modules':monkeypatch.setitem(sys.modules,route,ModuleType('foreign'))
            else:
                source=Path(case.source_inputs[route]['path'])
                source.write_bytes(source.read_bytes()+b'\n# unit drift\n')
            scope.prepare_common()
    released(case)


def test_preloaded_route_rejected_before_any_session_and_original_locks_released(case,monkeypatch):
    route=original._ROUTE_NAMES[0]
    monkeypatch.setitem(sys.modules,route,ModuleType(route))
    with pytest.raises(ValueError,match='must not be preloaded'):case.operation.__enter__()
    released(case)
    assert 'session_created' not in case.events


def test_entry_alias_drift_does_not_redirect_cleanup(case):
    with pytest.raises(ValueError,match='aliases changed'):
        with case.operation as scope:
            scope._lease=None;scope._session=object();scope._owner=object()
            scope.prepare_common()
    released(case)


@pytest.mark.parametrize('fault',['mark_reset','bundle_held','bundle_marked','owner_state',
    'guard_common0','guard_common1','guard_common2','guard_parent0','guard_parent1','guard_outer'])
def test_each_cleanup_edge_failure_keeps_body_error_and_attempts_all_resources(case,fault):
    with pytest.raises(ValueError,match='original body') as caught:
        with case.operation:
            case.fault[0]=fault
            raise ValueError('original body')
    released(case)
    assert caught.value.__notes__ and 'end' in case.events
    assert case.operation.receipt()['first_failure']


def test_closed_flag_setter_failure_still_ends_token_and_releases_all_original_guards(case,monkeypatch):
    with pytest.raises(ValueError,match='original body') as caught:
        with case.operation as scope:
            def set_closed(self,value):
                self.__dict__['_closed']=value
                raise RuntimeError('closed flag cleanup')
            monkeypatch.setattr(case.m.GuardedCommonOperation,'_closed',property(
                lambda self:self.__dict__.get('_closed',False),set_closed),raising=False)
            raise ValueError('original body')
    released(case)
    assert caught.value.__notes__


def test_public_constructor_rejects_caller_route_sources_even_when_self_consistent(case):
    with pytest.raises(TypeError,match='route_sources'):
        case.m.GuardedCommonOperation(case.owner,route_sources=case.source_inputs)
    released(case)


def test_changed_expected_literal_is_rejected_before_original_lock_acquisition(case,monkeypatch):
    monkeypatch.setattr(case.m,'_PINNED_ROUTES',())
    with pytest.raises(ValueError,match='dispatch changed'):case.operation.__enter__()
    released(case)


@pytest.mark.parametrize('case',[(kind,index) for kind in ('compile','exec') for index in range(3)]
    +[('edge',2),('observation',2)],indirect=True)
def test_loader_failure_rolls_back_every_binding_created_by_this_attempt(case):
    with pytest.raises((SyntaxError,RuntimeError,ValueError)):case.operation.__enter__()
    released(case)
    assert 'session_created' not in case.events and 'end' in case.events
    for name in original._ROUTE_NAMES:
        assert name not in sys.modules and name.rsplit('.',1)[1] not in vars(experiments)


@pytest.mark.parametrize('case',[('foreign',index) for index in range(3)],indirect=True)
def test_loader_rollback_preserves_foreign_replacement_and_original_exception(case):
    with pytest.raises(RuntimeError,match='original route execution'):case.operation.__enter__()
    released(case)
    for name in original._ROUTE_NAMES:
        binding=sys.modules.get(name);attribute=vars(experiments).get(name.rsplit('.',1)[1])
        assert binding is attribute
        assert binding is None or binding.__name__=='foreign-preserved'
