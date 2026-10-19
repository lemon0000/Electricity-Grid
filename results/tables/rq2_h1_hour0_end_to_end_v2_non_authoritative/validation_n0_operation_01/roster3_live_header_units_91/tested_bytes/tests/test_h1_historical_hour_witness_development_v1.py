"""Witness lifetime and dispatch faults; numerical equivalence is tested separately."""
import copy
from dataclasses import replace
import pickle
import threading
from types import SimpleNamespace
from pathlib import Path

import pytest

from experiments import h1_historical_hour_witness_development_v1 as m
from experiments import h1_historical_n0_verifier_development_v1 as verifier


class Lease:
    def __init__(self):self.closed=False
    def check(self):
        if self.closed:raise ValueError('closed lease')


@pytest.fixture
def scope(tmp_path, monkeypatch):
    monkeypatch.setattr(m, '_dispatch_view', lambda caller=None: ('test-only-dispatch',))
    leases=tuple(Lease() for _ in range(4))
    result=m._HourScope(tmp_path, leases)
    calls=[];context=['original']
    raw=dict(projection_payload=b'payload',canonical_locks=(0.,20.),native_total_ns=2,
             timing_vector_sha256='a'*64,full_hour_chain_recomputed=True)
    def full(*a, **kw):calls.append('full');return copy.deepcopy(raw)
    monkeypatch.setattr(m.hour,'inspect',full)
    def observe(*a,**kw):result._check();return tuple(context)
    monkeypatch.setattr(result,'_context',observe)
    yield result,leases,calls,context,raw
    result.close()


def promote(s):
    for _ in range(2):s.inspect(None,None,None,None)
    s.promote(mint_child(s,2))


def mint_child(s,count):
    # Deliberate private fixture mint; public construction is separately rejected.
    payload=b'payload'
    projection=m.parent.Projection(m.io.digest(m.io.encode([m.parent.CHILD_SCHEMA,m.io.digest(payload)])),payload)
    return m.RevalidatedChildInspection('accepted','a'*64,'a'*64,count,projection,
        _token=m._CHILD_TOKEN,_scope=s)


def test_independent_full_checks_then_bounded_fresh_revalidation(scope):
    s,leases,calls,context,raw=scope
    promote(s)
    for _ in range(2):
        value=s.inspect(None,None,None,None)
        assert value['projection_payload']==raw['projection_payload']
        assert value['canonical_locks']==raw['canonical_locks']
        assert value['full_hour_chain_recomputed'] is False
        value['projection_payload']=b'caller mutation'
    assert calls==['full','full']
    assert (s.full_calls,s.revalidation_calls)==(2,2)
    with pytest.raises(ValueError,match='count exceeded'):s.inspect(None,None,None,None)
    assert s._poisoned and s._value is None


def test_second_full_disagreement_rejects(scope):
    s,_,_,_,raw=scope
    s.inspect(None,None,None,None)
    raw['native_total_ns']=3
    with pytest.raises(ValueError,match='full numerical results differ'):s.inspect(None,None,None,None)
    assert s._poisoned


def test_after_failure_cannot_promote_or_reuse(scope):
    s,*_=scope
    for _ in range(2):s.inspect(None,None,None,None)
    with pytest.raises(ValueError,match='unconfirmed'):s.inspect(None,None,None,None)
    assert s._poisoned


@pytest.mark.parametrize('fault',['close','nonce','root','lease_replace','lease_close','payload','context'])
def test_lifetime_and_retained_input_faults(scope,fault):
    s,leases,_,context,_=scope
    promote(s)
    if fault=='close':s.close()
    elif fault=='nonce':s._nonce=object()
    elif fault=='root':s._root=s._root/'foreign'
    elif fault=='lease_replace':s._leases=(Lease(),*leases[1:])
    elif fault=='lease_close':leases[2].closed=True
    elif fault=='payload':s._value[1]['projection_payload']=b'changed'
    elif fault=='context':context[0]='changed'
    with pytest.raises(ValueError):s.inspect(None,None,None,None)
    assert s._poisoned and s._value is None


def test_thread_escape_rejects(scope):
    s,*_=scope
    promote(s);errors=[]
    def run():
        try:s._check()
        except ValueError as error:errors.append(str(error))
    t=threading.Thread(target=run);t.start();t.join()
    assert errors==['numerical witness lifetime changed']


@pytest.mark.parametrize('operation',[copy.copy,copy.deepcopy,pickle.dumps])
def test_scope_cannot_be_exported(scope,operation):
    with pytest.raises(TypeError):operation(scope[0])


def test_revalidation_remains_solver_denied(scope,monkeypatch):
    s,*_=scope;promote(s)
    def context(*a,**kw):m.hour.prior.guard.current.solve_current()
    monkeypatch.setattr(s,'_context',context)
    with pytest.raises(RuntimeError,match='solver entry forbidden'):s.inspect(None,None,None,None)
    assert s._poisoned


def test_guard_closures_have_stable_normalized_dispatch():
    with m.hour.prior.guard.solver_calls_forbidden():first=m._dispatch_view()
    with m.hour.prior.guard.solver_calls_forbidden():second=m._dispatch_view()
    assert first==second
    modules={v[0] for v in first[1]}
    assert 'src.rq2_joint_deliverability_boundary_v1.continuous_grid_normal' in modules


@pytest.mark.parametrize('target',['function','constant','builtin','descriptor'])
def test_dispatch_observes_direct_bindings(monkeypatch,target):
    with m.hour.prior.guard.solver_calls_forbidden():
        before=m._dispatch_view()
        if target=='function':monkeypatch.setattr(m.hour,'request_key',lambda *a:'0'*64)
        elif target=='constant':monkeypatch.setattr(m.hour,'PROJECTION_CAP',1)
        elif target=='builtin':monkeypatch.setattr(m.hour.science,'isinstance',lambda *a:True,raising=False)
        else:monkeypatch.setattr(m._HourScope,'close',lambda self:None)
        assert m._dispatch_view()!=before


@pytest.fixture
def real_context(tmp_path,monkeypatch):
    """Real context/snapshot checks, fabricated numeric result to isolate faults."""
    from tests.test_rq2_normal_h1_hour_archive_v1 import packet,spec
    p=packet();s=replace(spec(),time_limit_seconds=5.)
    limits=m.hour.prior.H1HourReplayLimits(3,100,500)
    root=tmp_path/'prefix';h=root/'job_000_non_authoritative/worker_non_authoritative/hour_non_authoritative'
    files={'binding.json','projection.bin','terminal.json'}
    for i in range(3):
        files.add(f'commits/{i:03d}.json')
        files.update(f'stages/{i:03d}/'+name for name in m.hour.stage._FILES)
    for name in files:
        path=h/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'{}')
    value=dict(projection_payload=b'payload',canonical_locks=(20.,1.,20.),native_total_ns=2,
        timing_vector_sha256='a'*64,full_hour_chain_recomputed=True)
    monkeypatch.setattr(m.hour,'inspect',lambda *a,**k:copy.deepcopy(value))
    scope=m._HourScope(root,tuple(Lease() for _ in range(4)),caller=verifier)
    pins=dict(expected_terminal_sha='a'*64,expected_implementation='b'*64)
    args=(h,p,s,limits)
    for _ in range(2):scope.inspect(*args,**pins)
    scope.promote(mint_child(scope,3))
    yield scope,args,pins,monkeypatch
    scope.close()


@pytest.mark.parametrize('name',[
    'binding.json','terminal.json','projection.bin','commits/000.json',
    'stages/000/native_raw/000/raw.bin','stages/000/science/numerical.bin',
    'stages/000/science/mapping.bin','stages/000/native_timing/terminal.json'])
@pytest.mark.parametrize('change',['bytes','same_bytes_replace'])
def test_real_snapshot_file_drift_rejects(real_context,name,change):
    scope,args,pins,_=real_context
    path=args[0]/name
    if change=='bytes':path.write_bytes(b'[]')
    else:
        saved=path.with_name(path.name+'.replaced');raw=path.read_bytes()
        path.replace(saved);path.write_bytes(raw);saved.unlink()
    with pytest.raises(ValueError):scope.inspect(*args,**pins)
    assert scope._poisoned and scope._value is None


@pytest.mark.parametrize('fault',['extra_file','directory_replace','packet','spec','limits',
    'root','terminal_pin','implementation_pin','threshold','dependency_function','vendor','pid'])
def test_real_context_dynamic_drift_rejects(real_context,fault):
    scope,args,pins,patch=real_context
    h,p,s,limits=args
    if fault=='extra_file':(h/'unexpected').write_bytes(b'x')
    elif fault=='directory_replace':
        d=h/'stages/000/native_timing';old=d.with_name('retained_timing');d.replace(old);d.mkdir()
        for file in old.iterdir():(d/file.name).write_bytes(file.read_bytes());file.unlink()
        old.rmdir()
    elif fault=='packet':p.inputs.request.system_demand_by_bus_mw[0][1]=999.
    elif fault=='spec':s=replace(s,time_limit_seconds=6.)
    elif fault=='limits':limits=replace(limits,max_constraints=501)
    elif fault=='root':h=h.parent/'foreign'
    elif fault=='terminal_pin':pins['expected_terminal_sha']='c'*64
    elif fault=='implementation_pin':pins['expected_implementation']='d'*64
    elif fault=='threshold':patch.setattr(m.hour.prior.generation_projection,'EPSILON',1e-3)
    elif fault=='dependency_function':
        from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_normal as normal
        patch.setattr(normal,'_dependencies',lambda:())
    elif fault=='vendor':patch.setattr(m.hour.stage.capture.timing.vendor,'_set_options',lambda *a:None)
    elif fault=='pid':patch.setattr(m.os,'getpid',lambda:-1)
    with pytest.raises(ValueError):scope.inspect(h,p,s,limits,**pins)
    assert scope._poisoned and scope._value is None


def test_real_revalidation_exit_drift_rejects(real_context):
    scope,args,pins,patch=real_context
    original=scope._context;calls=[]
    def context(*a,**kw):
        result=original(*a,**kw);calls.append(1)
        if len(calls)==1:(args[0]/'projection.bin').write_bytes(b'[]')
        return result
    patch.setattr(scope,'_context',context)
    with pytest.raises(ValueError,match='changed during use'):scope.inspect(*args,**pins)
    assert scope._poisoned


@pytest.mark.parametrize('name',['_observe_sources','_observe_prefix','_obligation_inventory','_replay_prefix','_projection'])
def test_verifier_alias_replacement_rejects_before_read(monkeypatch,tmp_path,name):
    monkeypatch.setattr(verifier,name,lambda *a,**k:None)
    with pytest.raises(ValueError,match='verifier dispatch changed'):
        verifier.prepare(tmp_path,expected_binding_sha256='a'*64,expected_terminal_sha256='b'*64,completed_hours=1)


@pytest.mark.parametrize('target',['verifier','bridge','reader'])
def test_scope_observes_caller_and_reader_bindings(real_context,target):
    scope,args,pins,patch=real_context
    if target=='verifier':patch.setattr(verifier,'_observe_sources',lambda *a:None)
    elif target=='bridge':patch.setattr(m,'inspect_bridge',lambda *a,**k:None)
    else:patch.setattr(verifier.legacy.HistoricalTimedSnapshot,'_outcome',lambda *a:None)
    with pytest.raises(ValueError,match='dispatch or source changed'):scope.inspect(*args,**pins)


def test_public_results_cannot_be_constructed():
    with pytest.raises(TypeError,match='owned child'):
        m.RevalidatedChildInspection('accepted','a'*64,'a'*64,2,None)
    with pytest.raises(TypeError,match='owned historical'):
        verifier.VerifiedHistoricalEnvelope(None,b'{}','a'*64,verifier.SCHEMA,4,4)


@pytest.mark.parametrize('operation',[copy.copy,copy.deepcopy,pickle.dumps])
def test_owned_child_cannot_be_exported(scope,operation):
    s,*_=scope;promote(s)
    with pytest.raises(TypeError):operation(mint_child(s,2))


def test_foreign_scope_promotion_rejects(scope,tmp_path):
    s,*_=scope;promote(s)
    other=m._HourScope(tmp_path,tuple(Lease() for _ in range(4)))
    other.full_calls=2;other._value=s._value
    try:
        with pytest.raises(ValueError,match='accepted child'):other.promote(mint_child(s,2))
    finally:other.close()
