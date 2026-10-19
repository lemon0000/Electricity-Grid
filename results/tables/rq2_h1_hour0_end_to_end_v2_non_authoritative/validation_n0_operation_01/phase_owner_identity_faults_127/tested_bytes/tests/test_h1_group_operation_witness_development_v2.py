"""Synthetic ownership/counter failures; not a saved/common integration result.

Private drivers exercise the real scopes and receipts, while explicit context,
numeric and lease fixtures are installed before fresh guarded definitions.
The source core's complete numerical and I/O path is a separate acceptance gate.
"""
from copy import deepcopy
from fractions import Fraction as Q
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from threading import Thread

import pytest

import experiments
from experiments import h1_operation_historical_witness_development_v2 as original
from tests.test_rq2_normal_h1_source_v1 import packet


def fresh(monkeypatch,name):
    path=Path(original.__file__).with_name(name+'.py')
    canonical='experiments.'+name
    module=ModuleType(canonical);module.__file__=str(path);module.__package__='experiments'
    monkeypatch.setitem(sys.modules,canonical,module)
    monkeypatch.setattr(experiments,name,module,raising=False)
    exec(compile(path.read_bytes(),str(path),'exec'),vars(module))
    return module


@pytest.fixture
def case(tmp_path,monkeypatch,request):
    calls=[];contexts=[];dispatch=[('explicit-unit-only-dispatch',)]
    prior=original.prior_witness
    monkeypatch.setattr(prior,'_dispatch_view',lambda caller=None:dispatch[0])
    def context(scope,*args):
        scope._check();contexts.append(str(scope._root))
        return (str(scope._root),)*8+({'snapshot':'explicit-unit-only'},)
    monkeypatch.setattr(prior._HourScope,'_context',context)
    raw=dict(projection_payload=b'payload',canonical_locks=(20.,1.,20.),
        native_total_ns=2,full_hour_chain_recomputed=True)
    def full(*args,**kwargs):calls.append('full');return deepcopy(raw)
    monkeypatch.setattr(original.hour,'inspect',full)
    bridge=original.operation_bridge
    lease=object();roster=object();declarations=[];lease_state=[True];claimed=[]
    for arm in ('cfe-only','joint-correct','network-only'):
        root=tmp_path/arm;root.mkdir()
        declarations.append((arm,str(root.resolve()),'a'*64,'b'*64))
    def verify(candidate):
        if candidate is not lease or not lease_state[0]:raise ValueError('closed unit lease')
        return roster,tuple(declarations),2
    def claim(candidate,session):
        verify(candidate)
        if claimed:raise ValueError('one session')
        claimed.append(session)
    monkeypatch.setattr(bridge,'_VERIFY_LEASE',verify)
    monkeypatch.setattr(bridge,'_CLAIM_SESSION',claim)
    monkeypatch.setattr(bridge,'_BOOKEND',verify)
    routes={}
    def source_result(candidate,value):
        verify(candidate)
        if type(value) is not routes['source'].CommonSourceBundle:raise TypeError('exact unit source result')
    def common_result(candidate,value,session):
        verify(candidate)
        if type(value) is not routes['common'].PreparedCommonInput or value._session_nonce is not session._nonce:
            raise ValueError('original unit common result')
    monkeypatch.setattr(bridge,'_SOURCE_RESULT',source_result)
    monkeypatch.setattr(bridge,'_COMMON_RESULT',common_result)
    partial=getattr(request,'param',None);made_guards=[]
    if partial is not None:
        real_lock=original.threading.Lock
        class EntryFaultGuard:
            def __init__(self):self.raw=real_lock();self.index=len(made_guards);made_guards.append(self)
            def acquire(self,*args):
                if self.index==partial:raise RuntimeError('partial original arm entry')
                return self.raw.acquire(*args)
            def locked(self):return self.raw.locked()
            def release(self):return self.raw.release()
        monkeypatch.setattr(original.threading,'Lock',EntryFaultGuard)
    m=fresh(monkeypatch,'h1_operation_historical_witness_development_v2')
    source=fresh(monkeypatch,'h1_phase_exact_source_current_development_v3')
    common=fresh(monkeypatch,'h1_group_n0_common_input_binding_development_v3')
    routes.update(source=source,common=common)
    p=packet();api=m.parent.source
    boundary=api._owned(api.H1NormalBoundary,network_identity=p.before.network_identity,
        completed_hours=1,units=(('G1',True,20.,1),),evidence_role='numerical_lex_candidate')
    decision=m.current._decision(p,boundary)
    audit=m.io.encode(dict(schema=m.SCHEMA,implementation=m.implementation_identity(),
        decision_identity=decision.decision_identity,**{name:False for name in ('policy_visible',
            'common_prefix_publication_verified','detached_consumer_authenticated','reference_or_actual_ready',
            'formal_execution_ready','formal_result','resource_admission','native_execution_authorized')}))
    if partial is not None:
        with pytest.raises(RuntimeError,match='partial original arm entry') as caught:m.GroupWitnessSession(lease)
        assert len(claimed)==1
        yield SimpleNamespace(m=m,session=claimed[0],guards=made_guards,error=caught.value)
        assert all(not guard.locked() for guard in made_guards)
        return
    session=m.GroupWitnessSession(lease)
    resources=session._resource_caps
    try:
        yield SimpleNamespace(m=m,source=source,common=common,session=session,decision=decision,
            audit=audit,calls=calls,contexts=contexts,lease_state=lease_state,dispatch=dispatch)
    finally:
        try:session.close()
        except ValueError:
            # Deliberately corrupt aliases still have to release every original
            # resource; the test body already verifies the expected failure.
            if session._failure is None:raise
        assert all(not guard.locked() and owner._proof is None for owner,guard in resources)


class Lease:
    def check(self):pass


def prefix(case,owner,ticket,index,*,fail_site=None):
    m=case.m
    scope=m._OperationHourScope(owner._declaration[0],tuple(Lease() for _ in range(4)),
        caller=m,_operation=owner,_ticket=ticket,_prefix_index=index)
    try:
        for site in range(4):
            if site==fail_site:raise RuntimeError('injected prefix failure')
            scope.inspect(None,None,None,None)
            if site in (1,3):
                projection=m.parent.Projection(m.io.digest(m.io.encode([m.parent.CHILD_SCHEMA,
                    m.io.digest(b'payload')])),b'payload')
                result=m.RevalidatedChildInspection('accepted','a'*64,'a'*64,3,projection,
                    _token=m._CHILD_TOKEN,_scope=scope)
                scope.promote(result)
        owner._record_prefix(ticket,index,scope)
    finally:scope.close()


def arm_prepare(case,owner,*,fail_prefix=None):
    m=case.m;source=case.source
    try:
        ticket=owner._start()
        for index in range(2):prefix(case,owner,ticket,index,fail_site=2 if fail_prefix==index else None)
        full=sum(row[3] for row in owner._pending);fresh_count=sum(row[4] for row in owner._pending)
        identity=m.verifier_identity()
        raw=owner._execution(case.decision,case.audit,identity,full,fresh_count)
        historical=m.VerifiedHistoricalEnvelope(case.decision,case.audit,identity,full,fresh_count,raw,
            _token=m._ENVELOPE_TOKEN,_operation=owner,_ticket=ticket)
        owner._finish(ticket,case.decision,case.audit,envelope=historical)
        audit=m.io.encode(dict(schema=source.SCHEMA,unit_counter_fixture=True))
        current=source.normal._owned(source.ExactSourceCurrent,
            prepared_current=SimpleNamespace(audit_payload=audit),source_projection_audit_payload=audit,
            workload_exact=Q(0),source_cfe_at_alpha_one_exact=Q(1),exogenous_scientific_payload=b'{}',
            source_observation_identity='d'*64)
        execution=m.io.encode(dict(historical_execution=json.loads(raw),
            exact_source_audit_sha256=m.io.digest(audit),prepared_current_audit_sha256=m.io.digest(audit)))
        bundle=source.normal._owned(source.CommonSourceBundle,current=current,historical=historical,
            decision=case.decision,audit_payload=case.audit,verification_execution_payload=execution)
        case.session._record_source(owner,bundle)
        return historical
    except BaseException as error:
        owner._poison(error);raise


def common_prepare(case,*,fail_arm=None,fail_round=1):
    session=case.session;m=case.m
    try:
        ticket=session._start_common()
        for round_ in range(2):
            for arm,_ in session._original_arms:
                owner=session._arm(arm,ticket)
                arm_prepare(case,owner,fail_prefix=1 if (arm,round_)==(fail_arm,fail_round) else None)
                if session._common_calls==0:assert not session._reuse_active
        payload=m.io.encode(dict(unit_counter_fixture=True))
        result=case.source.normal._owned(case.common.PreparedCommonInput,
            manifest=None,source_binding=None,scientific_report_payload=payload,
            execution_receipt=session._execution(ticket,payload),_session_nonce=session._nonce)
        session._finish_common(ticket,result)
        return result
    except BaseException as error:
        session._poison(error);raise


def test_first_whole_common_full_then_second_reuses_all_slots(case):
    first=common_prepare(case);assert len(case.calls)==24 and len(case.contexts)==96
    assert case.session._reuse_active
    second=common_prepare(case);assert len(case.calls)==24 and len(case.contexts)==192
    a,b=map(json.loads,(first.execution_receipt,second.execution_receipt))
    assert (a['full_numerical_hour_replays'],a['within_prefix_revalidations'],a['cross_common_numerical_proof_reuses'])==(24,24,0)
    assert (b['full_numerical_hour_replays'],b['within_prefix_revalidations'],b['cross_common_numerical_proof_reuses'])==(0,0,48)
    assert a['context_evaluations']==b['context_evaluations']==96
    assert all(row['execution']['arm_label_authenticated'] for row in a['arm_prepares']+b['arm_prepares'])
    assert not case.session.receipt()['complete']
    case.session.close();receipt=case.session.receipt()
    assert receipt['complete'] and all(row['proof_cleared'] for row in receipt['arm_receipts'].values())


@pytest.mark.parametrize('arm',['cfe-only','joint-correct','network-only'])
@pytest.mark.parametrize('round_',[0,1])
def test_failure_any_arm_round_poisons_all_staged_slots(case,arm,round_):
    with pytest.raises(RuntimeError,match='prefix failure'):common_prepare(case,fail_arm=arm,fail_round=round_)
    assert not case.session._reuse_active and case.session._failure
    assert all(owner._proof is None for owner in case.session._arms.values())
    with pytest.raises(ValueError):case.session._start_common()


@pytest.mark.parametrize('fault',['arm_swap','proof_swap','closed_lease','project_drift','nonce','source_record_gap'])
def test_cross_common_context_and_ownership_faults(case,fault):
    common_prepare(case);session=case.session
    left,right=list(session._arms.values())[:2]
    if fault=='arm_swap':session._arms=dict(reversed(list(session._arms.items())))
    elif fault=='proof_swap':left._proof=right._proof
    elif fault=='closed_lease':case.lease_state[0]=False
    elif fault=='project_drift':case.dispatch[0]=('changed',)
    elif fault=='nonce':session._nonce=object()
    else:
        ticket=session._start_common()
        with pytest.raises(ValueError,match='six independent'):session._execution(ticket,b'{}')
        session._poison(ValueError('missing source records'));return
    with pytest.raises(ValueError):common_prepare(case)
    assert session._failure and all(owner._proof is None for owner in session._arms.values())


def test_third_call_is_diagnostic_budget_and_never_a_production_limit(case):
    common_prepare(case);common_prepare(case)
    with pytest.raises(ValueError,match='two nonreentrant'):common_prepare(case)
    assert case.session._failure


def test_source_audit_has_no_false_actual_counts_or_nested_prepared_counts(case):
    s=case.source
    old=dict(schema=s.predecessor.SCHEMA,implementation_identity=s.predecessor.implementation_identity(),
        historical_verifier_schema='old',historical_verifier_identity='c'*64,
        full_numerical_hour_replays=4,fresh_byte_context_revalidations=4,recomputed_on_revalidation=False,
        normal_audit_payload=dict(unit_only=True),source_observation_audit_payload=dict(unit_only=True))
    raw=s.io.encode(old)
    audit=json.loads(s._scientific_audit(SimpleNamespace(source_projection_audit_payload=raw),s.implementation_identity()))
    assert all(key not in audit for key in s._EXECUTION_FIELDS)
    assert audit['normal_audit_payload']==old['normal_audit_payload']
    compatibility=audit['predecessor_compatibility']
    assert compatibility['payload']==old
    assert compatibility['compatibility_counts_describe_actual_execution'] is False
    assert compatibility['payload_sha256']==s.io.digest(raw)


@pytest.mark.parametrize('target',['core','core_code','source_loader','registry','final_observe','core_public_entry','new_helper'])
def test_source_guard_rejects_changed_original_or_new_routes_before_prefix(case,monkeypatch,target):
    source=case.source;old=source.predecessor
    owner=next(iter(case.session._arms.values()))
    if target=='core':monkeypatch.setattr(old,'_prepare',lambda *a,**kw:None)
    elif target=='core_code':monkeypatch.setattr(old._prepare,'__code__',(lambda *a,**kw:None).__code__)
    elif target=='source_loader':monkeypatch.setattr(old.source,'load_pinned_current',lambda *a,**kw:None)
    elif target=='registry':monkeypatch.setattr(old.registry,'prepare',lambda *a,**kw:None)
    elif target=='final_observe':monkeypatch.setattr(old.historical,'_observe_sources',lambda *a,**kw:None)
    elif target=='core_public_entry':monkeypatch.setattr(old,'prepare_common_bundle',lambda *a,**kw:None)
    else:monkeypatch.setattr(source,'_scientific_audit',lambda *a,**kw:b'{}')
    with pytest.raises(ValueError,match='dispatch changed'):source.prepare_common_bundle(owner,expected_registry_identity='c'*64)
    assert not case.calls and case.session._failure


def test_original_context_check_and_inspect_remain_inherited(case):
    m=case.m
    assert all(getattr(m._OperationHourScope,name) is getattr(m.prior_witness._HourScope,name)
        for name in ('_context','_check','inspect'))
    assert m._CONTEXT is m.prior_witness._HourScope._context


@pytest.mark.parametrize('fault',['remove_arm','replace_arm','close_shadow','poison_shadow',
    'class_close_code','guard_alias','creator','session_creator','creator_deleted',
    'caps_empty','caps_deleted','original_arms_empty','original_arms_deleted','arms_deleted','arm_session'])
def test_fixed_original_resources_clear_and_release_after_corruption(case,monkeypatch,fault):
    session=case.session;owner=session._original_arms[0][1]
    captured=session._resource_caps
    if fault=='remove_arm':session._arms.pop(next(iter(session._arms)))
    elif fault=='replace_arm':session._arms[next(iter(session._arms))]=object()
    elif fault=='close_shadow':owner.close=lambda:None
    elif fault=='poison_shadow':owner._poison=lambda *a:None
    elif fault=='class_close_code':monkeypatch.setattr(case.m.ArmWitness.close,'__code__',(lambda self:None).__code__)
    elif fault=='guard_alias':owner._original_guard=object()
    elif fault=='creator':owner._owner=(0,0)
    elif fault=='session_creator':session._creator=(0,0)
    elif fault=='creator_deleted':del session._creator
    elif fault=='caps_empty':session._resource_caps=()
    elif fault=='caps_deleted':del session._resource_caps
    elif fault=='original_arms_empty':session._original_arms=()
    elif fault=='original_arms_deleted':del session._original_arms
    elif fault=='arms_deleted':del session._arms
    else:owner._session=object()
    # Poison and cleanup are direct fixed callables; no mutated owner map or
    # instance/class method is allowed to redirect either operation.
    session._poison(ValueError('injected corruption'))
    if fault in ('guard_alias','creator','remove_arm','replace_arm','session_creator','creator_deleted',
            'caps_empty','caps_deleted','original_arms_empty','original_arms_deleted','arms_deleted','arm_session'):
        with pytest.raises(ValueError):session.close()
    else:session.close()
    assert all(not guard.locked() and value._proof is None for value,guard in captured)


@pytest.mark.parametrize('entry',['source','common'])
def test_public_failure_uses_definition_poison_despite_exact_instance_shadow(case,entry):
    called=[];session=case.session
    if entry=='source':
        owner=session._original_arms[0][1];owner._poison=lambda error:called.append(error)
        with pytest.raises(ValueError):case.source.prepare_common_bundle(owner,expected_registry_identity='c'*64)
    else:
        session._poison=lambda error:called.append(error);session._nonce=object()
        with pytest.raises(ValueError):case.common.prepare(session)
    assert not called and session._failure and all(owner._proof is None for owner,_ in session._resource_caps)


@pytest.mark.parametrize('entry',['source','common'])
def test_wrong_type_never_accesses_untrusted_poison(case,entry):
    class Foreign:
        @property
        def _poison(self):raise AssertionError('untrusted poison accessed')
    with pytest.raises(TypeError):
        if entry=='source':case.source.prepare_common_bundle(Foreign(),expected_registry_identity='c'*64)
        else:case.common.prepare(Foreign())


@pytest.mark.parametrize('case',[0,1,2],indirect=True)
def test_partial_arm_entry_failure_releases_all_previously_registered_original_resources(case):
    assert len(case.guards)==3 and all(not guard.locked() for guard in case.guards)
    receipt=case.session.receipt()
    assert receipt['closed'] and not receipt['complete'] and receipt['first_failure']
    assert len(receipt['arm_receipts'])==3
    assert all(value['proof_cleared'] for value in receipt['arm_receipts'].values())
    case.session.close()


@pytest.mark.parametrize('calls',[0,1,2])
def test_poison_after_close_updates_private_terminal_summary_and_keeps_resources_cleared(case,calls):
    for _ in range(calls):common_prepare(case)
    session=case.session;session.close()
    session._poison(ValueError('late body or cleanup failure'))
    receipt=session.receipt()
    assert receipt['closed'] and not receipt['complete'] and receipt['first_failure']
    assert all(value['proof_cleared'] and not value['complete'] and value['first_failure']
        for value in receipt['arm_receipts'].values())
    # Caller mutation of a returned receipt cannot erase the retained failure.
    receipt['first_failure']=None;receipt['complete']=True
    assert session.receipt()['first_failure'] and not session.receipt()['complete']


def test_foreign_thread_arm_cleanup_reports_failure_after_releasing_all_private_resources(case):
    common_prepare(case)
    session=case.session;resources=session._resource_caps;failures=[]
    assert all(owner._proof is not None and guard.locked() for owner,guard in resources)
    def cleanup():
        try:session.close()
        except BaseException as error:failures.append(error)
    thread=Thread(target=cleanup,daemon=True);thread.start();thread.join(timeout=10)
    assert not thread.is_alive() and len(failures)==1
    assert isinstance(failures[0],ValueError) and 'creating thread' in str(failures[0])
    assert all(owner._proof is None and not guard.locked() for owner,guard in resources)
    receipt=session.receipt()
    assert receipt['closed'] and receipt['first_failure'] and not receipt['complete']
    session.close()
