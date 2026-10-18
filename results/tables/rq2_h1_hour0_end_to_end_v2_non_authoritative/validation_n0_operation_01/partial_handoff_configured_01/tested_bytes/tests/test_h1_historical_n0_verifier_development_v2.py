"""Isolated N0 proof-lifetime tests; the science oracle is a separate saved replay."""
from copy import deepcopy
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import threading

import pytest

from experiments import h1_historical_n0_verifier_development_v2 as original
from experiments import h1_bootstrap_integration_development_v3 as bootstrap
from tests.test_rq2_normal_h1_source_v1 import packet


class Lease:
    def __init__(self):self.closed=False
    def check(self):
        if self.closed:raise ValueError('closed lease')


@pytest.fixture
def case(tmp_path,monkeypatch):
    calls=[];contexts=[];fault=[None];dispatch=[('unit-only-dispatch',)]
    monkeypatch.setattr(original.prior_witness,'_dispatch_view',lambda caller=None:dispatch[0])
    def observe(scope,*args):
        scope._check();contexts.append(len(contexts))
        if len(contexts)-1==fault[0]:raise OSError('injected context read failure')
        return ('unit-only-context',)*8+({'snapshot':'unit-only'},)
    monkeypatch.setattr(original.prior_witness._HourScope,'_context',observe)
    raw=dict(projection_payload=b'payload',canonical_locks=(20.,1.,20.),native_total_ns=2,
        full_hour_chain_recomputed=True)
    def full(*args,**kwargs):calls.append('full');return deepcopy(raw)
    monkeypatch.setattr(original.hour,'inspect',full)
    path=Path(original.__file__);name='experiments._h1_n0_unit_'+tmp_path.name
    fresh=ModuleType(name);fresh.__file__=str(path);fresh.__package__='experiments'
    monkeypatch.setitem(sys.modules,name,fresh)
    # Synthetic dependencies are fixed before the definition-time guards. This
    # fixture exercises the public lifetime without claiming numerical evidence.
    source=path.read_text(encoding='utf-8')
    marker='\n_install_runtime_checks()\n';assert source.count(marker)==1
    exec(compile(source.replace(marker,'\n'),str(path),'exec'),vars(fresh))
    m=fresh
    m.implementation_identity=lambda:'c'*64
    m.verifier_identity=lambda:'d'*64
    p=packet();boundary=m.parent.source._owned(m.parent.source.H1NormalBoundary,
        network_identity=p.before.network_identity,completed_hours=1,
        units=(('G1',True,20.,1),),evidence_role='numerical_lex_candidate')
    decision=m.current._decision(p,boundary)
    audit=m.io.encode(dict(schema=m.SCHEMA,implementation=m.implementation_identity(),
        decision_identity=decision.decision_identity,**{key:False for key in (
            'policy_visible','common_prefix_publication_verified','detached_consumer_authenticated',
            'reference_or_actual_ready','formal_execution_ready','formal_result','resource_admission',
            'native_execution_authorized')}))
    def project(root,*,_operation,_ticket,**kwargs):
        for index in range(2):
            scope=m._OperationHourScope(root,tuple(Lease() for _ in range(4)),caller=m,
                _operation=_operation,_ticket=_ticket,_prefix_index=index)
            try:
                for site in range(4):
                    scope.inspect(None,None,None,None)
                    if site in (1,3):
                        payload=b'payload';projection=m.parent.Projection(m.io.digest(m.io.encode(
                            [m.parent.CHILD_SCHEMA,m.io.digest(payload)])),payload)
                        child=m.RevalidatedChildInspection('accepted','a'*64,'a'*64,3,projection,
                            _token=m._CHILD_TOKEN,_scope=scope)
                        scope.promote(child)
                _operation._record_prefix(_ticket,index,scope)
            finally:scope.close()
        return decision,audit
    m._projection=project;m._install_runtime_checks()
    def create(*,reuse=True,owner=None):
        return m.N0ValidationOperation(tmp_path,arm_id='a'*64,expected_binding_sha256='a'*64,
            expected_terminal_sha256='b'*64,reuse_numerical_proof=reuse,
            _bootstrap_owner=owner,diagnostic_only=reuse and owner is None)
    def body(envelope):
        return dict(controller_root=str(tmp_path),historical_verifier_schema=m.VERIFIER_SCHEMA,
            historical_validation_contract=m.VERIFIER_SCHEMA,
            historical_verifier_identity=envelope.verifier_identity,
            audit_payload_sha256=m.io.digest(envelope.audit_payload))
    def build(operation,index=None,*,confirm=True):
        if index is None:index=operation._attempts
        ticket=operation.begin_build(operation._bootstrap_owner,m.BUILD_SITES[index])
        envelope=operation.prepare()
        if confirm:operation.confirm_build(ticket,body(envelope))
        return ticket,envelope
    def owner():
        value=object.__new__(bootstrap.BootstrapOwner)
        value.closed=False;value.poisoned=False;value._operation=threading.Lock()
        value._original_operation=value._operation;value._operation.acquire()
        value._operation_nonce=object();value.declaration=object()
        value.roots={'controller':str(tmp_path)};value._slot={'slot_id':'a'*64}
        return value
    return SimpleNamespace(m=m,create=create,build=build,body=body,owner=owner,
        calls=calls,contexts=contexts,fault=fault,dispatch=dispatch,raw=raw)


def test_four_builds_keep_all_observations_and_defer_proof_until_confirmation(case):
    m=case.m
    with case.create() as operation:
        ticket,envelope=case.build(operation,confirm=False)
        assert operation._proof is None and len(operation._candidate_proof)==2
        operation.confirm_build(ticket,case.body(envelope))
        assert len(operation._proof)==2 and operation._candidate_proof is None
        for _ in range(3):case.build(operation)
        assert not operation.receipt()['complete']
    receipt=operation.receipt()
    assert receipt['complete'] and receipt['proof_cleared'] and not operation._original_guard.locked()
    assert len(case.calls)==4 and len(case.contexts)==64
    assert [(r['full_numerical_hour_replays'],r['fresh_byte_context_revalidations'])
        for r in receipt['prepares']]==[(4,4),(0,8),(0,8),(0,8)]
    assert [r['site'] for r in receipt['confirmed_builds']]==list(m.BUILD_SITES)
    rows=receipt['confirmed_builds'];assert rows[0]['previous_receipt_sha256'] is None
    assert all(rows[i]['previous_receipt_sha256']==rows[i-1]['receipt_sha256'] for i in range(1,4))
    assert len({r['body_sha256'] for r in rows})==1
    assert len({r['proof_basis_identity'] for r in rows})==1
    assert not receipt['formal_result'] and not receipt['native_execution_authorized']


@pytest.mark.parametrize('edge',range(64))
def test_each_fresh_context_failure_poisoned_without_numerical_fallback(case,edge):
    case.fault[0]=edge
    with case.create() as operation:
        with pytest.raises(OSError,match='context read failure'):
            for _ in range(4):case.build(operation)
        assert operation._proof is None and operation._candidate_proof is None and operation._failure
        before=len(case.calls)
        with pytest.raises(ValueError):operation.prepare()
        assert len(case.calls)==before
    assert not operation.receipt()['complete'] and not operation._original_guard.locked()
    assert len(case.contexts)==edge+1


@pytest.mark.parametrize('fault',['early','wrong_ticket','wrong_body','duplicate','next_prepare','wrong_site','fifth'])
def test_build_confirmation_and_ordinal_faults(case,fault):
    with case.create() as operation:
        with pytest.raises(ValueError):
            if fault=='early':
                token=operation.begin_build(None,case.m.BUILD_SITES[0]);operation.confirm_build(token,{})
            elif fault=='wrong_site':operation.begin_build(None,case.m.BUILD_SITES[1])
            elif fault=='fifth':
                for _ in range(4):case.build(operation)
                operation.begin_build(None,case.m.BUILD_SITES[0])
            else:
                token,envelope=case.build(operation,confirm=False);body=case.body(envelope)
                if fault=='wrong_ticket':operation.confirm_build(object(),body)
                elif fault=='wrong_body':body['audit_payload_sha256']='e'*64;operation.confirm_build(token,body)
                elif fault=='duplicate':operation.confirm_build(token,body);operation.confirm_build(token,body)
                elif fault=='next_prepare':operation.prepare()
        assert operation._failure and operation._proof is None and operation._candidate_proof is None


@pytest.mark.parametrize('completed',range(4))
def test_early_close_releases_guard_without_complete_receipt(case,completed):
    with case.create() as operation:
        for _ in range(completed):case.build(operation)
    assert not operation.receipt()['complete'] and not operation._original_guard.locked()
    assert operation._proof is operation._candidate_proof is None


@pytest.mark.parametrize('field',['nonce','declaration','root','slot','guard','closed','poisoned'])
def test_live_bootstrap_binding_drift_poisoned(case,field):
    owner=case.owner();held=owner._operation
    try:
        with case.create(owner=owner) as operation:
            case.build(operation)
            if field=='nonce':owner._operation_nonce=object()
            elif field=='declaration':owner.declaration=object()
            elif field=='root':owner.roots['controller']+='changed'
            elif field=='slot':owner._slot['slot_id']='e'*64
            elif field=='guard':owner._operation=threading.Lock()
            else:setattr(owner,field,True)
            with pytest.raises(ValueError):case.build(operation)
            assert operation._failure and operation._proof is None
    finally:
        if held.locked():held.release()


@pytest.mark.parametrize('field',['root','binding','terminal','hours'])
def test_explicit_entry_refuses_foreign_pins_and_poison(case,field):
    with case.create() as operation:
        case.build(operation)
        args=dict(root=operation._exact_root,expected_binding_sha256='a'*64,
            expected_terminal_sha256='b'*64,completed_hours=1,n0_operation=operation)
        args[dict(root='root',binding='expected_binding_sha256',terminal='expected_terminal_sha256',hours='completed_hours')[field]]='changed'
        with pytest.raises(ValueError):case.m.prepare(**args)
        assert operation._failure and operation._proof is None


@pytest.mark.parametrize('field',['_CONTEXT','deepcopy','_projection','dispatch','prepare_code','confirm_default'])
def test_definition_time_helper_and_method_drift_poisoned(case,monkeypatch,field):
    with case.create() as operation:
        case.build(operation)
        with monkeypatch.context() as patch:
            if field=='dispatch':case.dispatch[0]=('changed',)
            elif field=='prepare_code':
                fn=case.m.N0ValidationOperation.prepare
                patch.setattr(fn,'__code__',fn.__code__.replace(co_name='changed'))
            elif field=='confirm_default':
                patch.setattr(case.m.N0ValidationOperation.confirm_build,'__defaults__',('changed',))
            else:patch.setattr(case.m,field,lambda *a,**k:None)
            with pytest.raises(ValueError,match='definition-time'):case.build(operation)
            case.dispatch[0]=('unit-only-dispatch',)
        assert operation._failure and operation._proof is None


def test_foreign_thread_cannot_consume_proof(case):
    with case.create() as operation:
        case.build(operation);errors=[]
        def use():
            try:operation.prepare()
            except ValueError as error:errors.append(error)
        thread=threading.Thread(target=use);thread.start();thread.join(timeout=5)
        assert not thread.is_alive() and errors and operation._failure and operation._proof is None


def test_full_fallback_is_independent_and_honest(case):
    for _ in range(2):
        envelope=case.m.prepare(case.create()._exact_root,expected_binding_sha256='a'*64,
            expected_terminal_sha256='b'*64,completed_hours=1)
        assert (envelope.full_numerical_hour_replays,envelope.fresh_byte_context_revalidations)==(4,4)
        execution=case.m.json.loads(envelope.execution_receipt)
        assert execution['mode']=='full_only' and not execution['bootstrap_operation_bound']
    assert len(case.calls)==8 and len(case.contexts)==32


def test_receipt_is_owned_copy_and_stable_body_cannot_change(case):
    with case.create() as operation:
        case.build(operation);view=operation.receipt();view['prepares'][0]['context_evaluations']=0
        assert operation.receipt()['prepares'][0]['context_evaluations']==16
        token,envelope=case.build(operation,confirm=False)
        body=case.body(envelope);body['extra']='changed'
        with pytest.raises(ValueError,match='body/science'):operation.confirm_build(token,body)
        assert operation._proof is None


def test_unbound_reuse_requires_explicit_diagnostic_only(case):
    with pytest.raises(ValueError,match='diagnostic-only'):
        case.m.N0ValidationOperation(case.create()._exact_root,arm_id='declared-only',
            expected_binding_sha256='a'*64,expected_terminal_sha256='b'*64)


@pytest.mark.parametrize('fault',['instance_close','instance_poison','instance_receipt','class_close',
    'class_close_code','guard_alias','ended','owner_alias'])
def test_cleanup_uses_original_guard_and_preserves_body_failure(case,monkeypatch,fault):
    operation=case.create();guard=operation._original_guard
    with pytest.raises(RuntimeError,match='first body failure') as caught:
        with operation:
            case.build(operation)
            if fault.startswith('instance_'):setattr(operation,fault.removeprefix('instance_').replace('poison','_poison'),lambda *a:None)
            elif fault=='class_close':monkeypatch.setattr(case.m.N0ValidationOperation,'close',lambda *a:None)
            elif fault=='class_close_code':
                fn=case.m.N0ValidationOperation.close
                monkeypatch.setattr(fn,'__code__',fn.__code__.replace(co_name='changed'))
            elif fault=='guard_alias':operation._original_guard=threading.Lock()
            elif fault=='ended':operation._ended=True
            else:operation._owner=(0,0)
            raise RuntimeError('first body failure')
    assert not guard.locked() and operation._proof is operation._candidate_proof is None
    assert operation._failure==repr(caught.value) and caught.value.__notes__


@pytest.mark.parametrize('fault',['prepare_count','prepare_execution','build_digest','build_chain',
    'build_science','contexts','attempts'])
def test_receipt_evidence_mutation_rejected_and_cannot_be_refrozen(case,fault):
    operation=case.create();guard=operation._original_guard
    with pytest.raises(ValueError):
        with operation:
            case.build(operation)
            if fault=='prepare_count':operation._rows[0]['context_evaluations']=0
            elif fault=='prepare_execution':operation._rows[0]['execution']['mode']='changed'
            elif fault=='build_digest':operation._confirmed_builds[0]['receipt_sha256']='0'*64
            elif fault=='build_chain':operation._confirmed_builds[0]['previous_receipt_sha256']='0'*64
            elif fault=='build_science':operation._confirmed_builds[0]['body_sha256']='0'*64
            elif fault=='contexts':operation._contexts+=16
            else:operation._attempts+=1
            operation.receipt()
    assert not guard.locked() and operation._proof is operation._candidate_proof is None and operation._failure


def test_site_constant_rebinding_fails_closed(case,monkeypatch):
    operation=case.create();guard=operation._original_guard
    with pytest.raises(ValueError,match='definition-time'):
        with operation:
            case.build(operation)
            monkeypatch.setattr(case.m,'BUILD_SITES',tuple(reversed(case.m.BUILD_SITES)))
            case.build(operation)
    assert not guard.locked() and operation._proof is None
