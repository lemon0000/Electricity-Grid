"""Diagnostic sequencing faults; real saved replay is a separate bounded entry."""
from copy import copy,deepcopy
from dataclasses import replace
import pickle
from pathlib import Path
import sys
from types import ModuleType
from types import SimpleNamespace
import threading

import pytest

from experiments import h1_operation_historical_witness_development_v1 as m
from tests.test_rq2_normal_h1_source_v1 import packet


class Lease:
    def __init__(self):self.closed=False
    def check(self):
        if self.closed:raise ValueError('closed lease')


def mint(scope):
    # Deliberately private fixture; no saved numerical-science claim.
    payload=b'payload';projection=m.parent.Projection(m.io.digest(m.io.encode(
        [m.parent.CHILD_SCHEMA,m.io.digest(payload)])),payload)
    return m.RevalidatedChildInspection('accepted','a'*64,'a'*64,3,projection,
        _token=m._CHILD_TOKEN,_scope=scope)


def prefix(operation,ticket,index,*,fail_site=None):
    scope=m._OperationHourScope(operation._fixed_declaration[0],tuple(Lease() for _ in range(4)),
        caller=m,_operation=operation,_ticket=ticket,_prefix_index=index)
    try:
        for site in range(4):
            if site==fail_site:raise RuntimeError('injected prefix failure')
            scope.inspect(None,None,None,None)
            if site in (1,3):scope.promote(mint(scope))
        operation._record_prefix(ticket,index,scope)
    finally:scope.close()


def drive(operation,*,fail_prefix=None):
    try:
        ticket=operation._start()
        for index in range(2):prefix(operation,ticket,index,fail_site=2 if index==fail_prefix else None)
        return operation._finish(ticket,SimpleNamespace(decision_bytes=b'science'),b'compatibility payload')
    except BaseException as error:
        operation._poison(error);raise


@pytest.fixture
def case(tmp_path,monkeypatch):
    calls=[];context=['unchanged']
    dispatch=[('unit-only-dispatch',)]
    monkeypatch.setattr(m.prior_witness,'_dispatch_view',lambda caller=None:dispatch[0])
    def observe(scope,*args):scope._check();return (context[0],)*8+({'snapshot':'unit-only'},)
    # Install synthetic dependencies before a fresh prototype module is defined.
    # No test replaces a guard after its definition-time baseline is installed.
    monkeypatch.setattr(m.prior_witness._HourScope,'_context',observe)
    raw=dict(projection_payload=b'payload',canonical_locks=(20.,1.,20.),native_total_ns=2,
        full_hour_chain_recomputed=True)
    def full(*args,**kwargs):calls.append('full');return deepcopy(raw)
    monkeypatch.setattr(m.hour,'inspect',full)
    path=Path(m.__file__);name='experiments._h1_operation_unit_'+tmp_path.name
    fresh=ModuleType(name);fresh.__file__=str(path);fresh.__package__='experiments'
    monkeypatch.setitem(sys.modules,name,fresh)
    exec(compile(path.read_bytes(),str(path),'exec'),vars(fresh))
    monkeypatch.setattr(sys.modules[__name__],'m',fresh)
    def create(reuse=True):return m.OperationHistoricalWitness(tmp_path,arm_id='network-only',
        expected_binding_sha256='a'*64,expected_terminal_sha256='b'*64,reuse_numerical_proof=reuse)
    return SimpleNamespace(create=create,calls=calls,context=context,raw=raw,dispatch=dispatch)


@pytest.mark.parametrize('reuse,expected',[(True,[(4,4),(0,8)]),(False,[(4,4),(4,4)])])
def test_operation_witness_exact_sites_contexts_and_separate_prefix_slots(case,reuse,expected):
    with case.create(reuse) as operation:
        assert drive(operation)==expected[0]
        assert len(operation._proof)==2
        assert operation._proof[0] is not operation._proof[1]
        assert drive(operation)==expected[1]
        assert operation._contexts==32
        assert len(case.calls)==(4 if reuse else 8)
    receipt=operation.receipt()
    assert receipt['prepares_complete'] and receipt['closed'] and receipt['proof_cleared']
    assert not receipt['complete']  # Private fixture commits are not public envelopes.
    assert all(row['context_evaluations']==16 for row in receipt['prepares'])
    assert all(p['context_evaluations']==8 for row in receipt['prepares'] for p in row['prefixes'])
    assert not receipt['production_handoff_integrated'] and not receipt['formal_result']


def test_second_prefix_failure_never_commits_proof(case):
    with case.create() as operation:
        with pytest.raises(RuntimeError,match='prefix failure'):drive(operation,fail_prefix=1)
        assert operation._proof is None and operation._failure
        with pytest.raises(ValueError,match='lifetime changed'):drive(operation)


def test_context_drift_between_prepares_poisoned_without_fallback(case):
    with case.create() as operation:
        drive(operation);case.context[0]='changed'
        with pytest.raises(ValueError,match='context changed'):drive(operation)
        assert len(case.calls)==4 and operation._proof is None and operation._failure


@pytest.mark.parametrize('field',['context','result'])
def test_retained_proof_mutation_rejected(case,field):
    with case.create() as operation:
        drive(operation)
        if field=='context':operation._proof[0][0][8]['snapshot']='changed'
        else:operation._proof[0][2]['projection_payload']=b'changed'
        with pytest.raises(ValueError,match='retained numerical proof changed'):drive(operation)
        assert operation._proof is None


@pytest.mark.parametrize('fault',['nonce','arm','root','binding','terminal','mode','unlock'])
def test_owner_declaration_and_guard_faults(case,fault):
    with case.create() as operation:
        drive(operation)
        if fault=='nonce':operation._nonce=object()
        elif fault=='unlock':operation._original_guard.release()
        else:
            index={'root':0,'arm':1,'binding':2,'terminal':3,'mode':5}[fault]
            values=list(operation._declaration);values[index]='changed';operation._declaration=tuple(values)
        with pytest.raises(ValueError,match='lifetime changed'):drive(operation)
        assert operation._proof is None


def test_wrong_thread_cannot_use_proof(case):
    with case.create() as operation:
        drive(operation);errors=[]
        def wrong():
            try:operation.prepare()
            except ValueError as error:errors.append(str(error))
        thread=threading.Thread(target=wrong);thread.start();thread.join()
        assert errors and operation._proof is None and operation._failure


def test_third_prepare_and_close_reuse_refused(case):
    with case.create() as operation:
        drive(operation);drive(operation)
        with pytest.raises(ValueError,match='two nonreentrant'):drive(operation)
    with pytest.raises(ValueError):operation.prepare()
    assert operation.receipt()['closed']


@pytest.mark.parametrize('export',[copy,deepcopy,pickle.dumps])
def test_operation_cannot_be_copied_or_serialized(case,export):
    with case.create() as operation:
        with pytest.raises(TypeError):export(operation)


@pytest.mark.parametrize('kind',['wrong_ticket','wrong_prefix','wrong_root','extra_site','early_promotion'])
def test_strict_prefix_site_and_promotion_sequence(case,kind):
    with case.create() as operation:
        ticket=operation._start();root=operation._declaration[0]
        args=dict(caller=m,_operation=operation,_ticket=ticket,_prefix_index=0)
        if kind=='wrong_ticket':args['_ticket']=object()
        elif kind=='wrong_prefix':args['_prefix_index']=1
        elif kind=='wrong_root':root=root.parent
        if kind.startswith('wrong'):
            with pytest.raises(ValueError):m._OperationHourScope(root,tuple(Lease() for _ in range(4)),**args)
            return
        scope=m._OperationHourScope(root,tuple(Lease() for _ in range(4)),**args)
        try:
            if kind=='early_promotion':
                with pytest.raises(ValueError):scope.promote(SimpleNamespace())
            else:
                for site in range(4):
                    scope.inspect(None,None,None,None)
                    if site in (1,3):scope.promote(mint(scope))
                with pytest.raises(ValueError,match='site order'):scope.inspect(None,None,None,None)
        finally:scope.close()


def test_context_check_and_public_inspect_are_inherited_unchanged():
    for name in ('_context','_check','inspect'):
        assert getattr(m._OperationHourScope,name) is getattr(m.prior_witness._HourScope,name)
    assert m._CONTEXT is m.prior_witness._HourScope._context
    assert m.RevalidatedChildInspection is not m.prior_witness.RevalidatedChildInspection
    assert not issubclass(m.DiagnosticVerifiedHistoricalEnvelope,m.prior_verifier.VerifiedHistoricalEnvelope)


def test_old_child_token_cannot_accept_new_scope(case):
    with case.create() as operation:
        ticket=operation._start();scope=m._OperationHourScope(operation._declaration[0],tuple(Lease() for _ in range(4)),
            caller=m,_operation=operation,_ticket=ticket,_prefix_index=0)
        try:
            with pytest.raises(TypeError):m.prior_witness.RevalidatedChildInspection(
                'accepted','a'*64,'a'*64,3,None,_token=m.prior_witness._CHILD_TOKEN,_scope=scope)
        finally:scope.close()


def test_proof_cannot_cross_diagnostic_operations(case):
    with case.create() as first:
        drive(first);foreign=first._proof
    with case.create() as second:
        second._proof=foreign
        with pytest.raises(ValueError,match='retained numerical proof changed'):drive(second)
        assert second._proof is None and second._failure


def test_prefix_slots_cannot_be_swapped(case):
    with case.create() as operation:
        drive(operation);operation._proof=tuple(reversed(operation._proof))
        with pytest.raises(ValueError,match='retained numerical proof changed'):drive(operation)


def test_prepare_reentry_is_refused(case):
    with case.create() as operation:
        operation._start()
        with pytest.raises(ValueError,match='nonreentrant'):operation.prepare()
        assert operation._failure and operation._proof is None


def test_prefix_cleanup_attempts_every_resource_and_preserves_body_error():
    calls=[]
    class Resource:
        def __init__(self,name,fail=False):self.name,self.fail=name,fail
        def close(self):
            calls.append(self.name)
            if self.fail:raise RuntimeError('cleanup '+self.name)
    body=ValueError('original body')
    m._close_prefix_resources(Resource('scope',True),Resource('reader',True),
        [Resource('lease0'),Resource('lease1',True)],body)
    assert calls==['scope','reader','lease1','lease0']
    assert len(body.__notes__)==3 and str(body)=='original body'


def test_prefix_cleanup_failure_stops_success_after_all_attempts():
    calls=[]
    class Resource:
        def close(self):calls.append(1);raise RuntimeError('cleanup')
    with pytest.raises(RuntimeError,match='cleanup'):
        m._close_prefix_resources(Resource(),Resource(),[Resource(),Resource()],None)
    assert len(calls)==4


@pytest.mark.parametrize('name',['_CONTEXT','_projection','_replay_prefix','_freeze',
    'verifier_identity','after','outcome','inspect_job','inspect_bridge','_runtime_check'])
def test_definition_time_helper_replacement_before_enter_is_rejected(case,monkeypatch,name):
    operation=case.create()
    monkeypatch.setattr(m,name,lambda *args,**kwargs:None)
    with pytest.raises(ValueError,match='definition-time'):operation.__enter__()
    assert operation._proof is None and operation._failure
    assert not operation._original_guard.locked()


def test_definition_time_function_defaults_change_is_rejected(case,monkeypatch):
    operation=case.create()
    monkeypatch.setattr(m._CONTEXT,'__defaults__',('changed',))
    with pytest.raises(ValueError,match='definition-time'):operation.__enter__()


@pytest.mark.parametrize('fault',['binding','project_view'])
def test_dispatch_change_after_last_context_before_commit_poisons(case,monkeypatch,fault):
    with case.create() as operation:
        ticket=operation._start()
        for index in range(2):prefix(operation,ticket,index)
        assert operation._contexts==16 and operation._proof is None
        if fault=='binding':monkeypatch.setattr(m,'_projection',lambda *args,**kwargs:None)
        else:case.dispatch[0]=('changed-project-view',)
        with pytest.raises(ValueError,match='definition-time'):
            operation._finish(ticket,SimpleNamespace(decision_bytes=b'science'),b'compatibility payload')
        assert operation._proof is None and operation._failure
    assert not operation._original_guard.locked()


@pytest.mark.parametrize('field',['decision','audit'])
def test_second_prepare_binds_first_complete_scientific_bytes(case,field):
    with case.create() as operation:
        drive(operation);ticket=operation._start()
        for index in range(2):prefix(operation,ticket,index)
        decision=b'changed' if field=='decision' else b'science'
        audit=b'changed' if field=='audit' else b'compatibility payload'
        with pytest.raises(ValueError,match='first complete historical scientific proof differs'):
            operation._finish(ticket,SimpleNamespace(decision_bytes=decision),audit)
        assert operation._proof is None and operation._failure


@pytest.mark.parametrize('adapter',['child','after','outcome','reference'])
def test_adapters_immediately_reject_foreign_thread_owner_and_poison(case,adapter):
    with case.create() as operation:
        ticket=operation._start()
        scope=m._OperationHourScope(operation._declaration[0],tuple(Lease() for _ in range(4)),
            caller=m,_operation=operation,_ticket=ticket,_prefix_index=0)
        try:
            operation._owner=(0,0)
            args=dict(child=lambda:mint(scope),after=lambda:m.after(None,None,None,scope=scope),
                outcome=lambda:m.outcome(None,0,None,None,scope=scope),
                reference=lambda:m.ChildReference.inspect(SimpleNamespace(_scope=scope)))
            with pytest.raises(ValueError,match='lifetime changed'):args[adapter]()
            assert operation._failure and operation._proof is None
        finally:
            operation._owner=(m.os.getpid(),threading.get_ident());scope.close()


def complete_science():
    p=packet();source=m.parent.source
    boundary=source._owned(source.H1NormalBoundary,network_identity=p.before.network_identity,
        completed_hours=1,units=(('G1',True,20.,1),),evidence_role='numerical_lex_candidate')
    decision=m.current._decision(p,boundary)
    audit=m.io.encode(dict(schema=m.SCHEMA,implementation=m.implementation_identity(),
        decision_identity=decision.decision_identity,**{name:False for name in ('policy_visible',
            'common_prefix_publication_verified','detached_consumer_authenticated','reference_or_actual_ready',
            'formal_execution_ready','formal_result','resource_admission','native_execution_authorized')}))
    return decision,audit


def make_envelope(operation,ticket,decision,audit,execution=None):
    own=m.verifier_identity();full=sum(row[3] for row in operation._pending)
    fresh=sum(row[4] for row in operation._pending)
    if execution is None:execution=operation._execution(decision,audit,own,full,fresh)
    return m.DiagnosticVerifiedHistoricalEnvelope(decision,audit,own,full,fresh,execution,
        _token=m._ENVELOPE_TOKEN,_operation=operation,_ticket=ticket)


@pytest.mark.parametrize('fault',['formal_result','resource_admission','native_execution_authorized',
    'production_handoff_integrated','extra','missing','schema','mode','prepare','session_identity',
    'proof_basis_identity','active_validation_identity','full_numerical_hour_replays'])
def test_execution_receipt_requires_all_exact_canonical_fields(case,fault):
    decision,audit=complete_science()
    with case.create() as operation:
        ticket=operation._start()
        for index in range(2):prefix(operation,ticket,index)
        execution=m.json.loads(operation._execution(decision,audit,m.verifier_identity(),4,4))
        if fault=='extra':execution['extra']='changed'
        elif fault=='missing':del execution['context_evaluations']
        else:execution[fault]='changed'
        with pytest.raises(ValueError,match='projection/execution binding differs'):
            make_envelope(operation,ticket,decision,audit,m.io.encode(execution))
        assert operation._failure and operation._proof is None


def test_session_receipt_links_two_envelopes_and_first_proof_basis(case):
    decision,audit=complete_science();envelopes=[]
    with case.create() as operation:
        for ordinal in range(2):
            ticket=operation._start()
            for index in range(2):prefix(operation,ticket,index)
            envelope=make_envelope(operation,ticket,decision,audit)
            operation._finish(ticket,decision,audit,envelope=envelope);envelopes.append(envelope)
        assert operation.receipt()['public_envelopes_complete'] and not operation.receipt()['complete']
    receipt=operation.receipt();rows=receipt['prepares']
    assert receipt['complete'] and receipt['public_envelopes_complete']
    assert len(receipt['session_identity'])==64
    assert [row['envelope_identity'] for row in rows]==[e.envelope_identity for e in envelopes]
    assert rows[0]['proof_basis_identity']==rows[1]['proof_basis_identity']
    assert rows[0]['active_validation_identity']==rows[1]['active_validation_identity']==receipt['active_validation_identity']
    assert [m.json.loads(e.execution_receipt)['proof_role'] for e in envelopes]==['produced','consumed']


def test_proof_basis_identity_commits_full_context_key(case):
    with case.create() as operation:
        ticket=operation._start()
        for index in range(2):prefix(operation,ticket,index)
        decision=SimpleNamespace(decision_bytes=b'science');audit=b'compatibility payload'
        first=operation._basis(decision,audit)[2]
        original=operation._pending[0];changed=list(original);changed[5]=('different-context-key',)
        operation._pending[0]=tuple(changed)
        assert operation._basis(decision,audit)[2]!=first
        operation._pending[0]=original;operation._finish(ticket,decision,audit)
        ticket=operation._start()
        for index in range(2):prefix(operation,ticket,index)
        changed=list(operation._pending[0]);changed[5]=('different-context-key',)
        operation._pending[0]=tuple(changed)
        with pytest.raises(ValueError,match='first complete historical scientific proof differs'):
            operation._finish(ticket,decision,audit)
        assert operation._proof is None and operation._failure


def test_public_session_identity_is_unique_and_immutable(case):
    first=case.create();second=case.create()
    assert first._public_session!=second._public_session
    with first:
        first._public_session='0'*64
        with pytest.raises(ValueError,match='lifetime changed'):drive(first)


def test_receipt_rejects_post_close_dispatch_drift(case,monkeypatch):
    with case.create() as operation:drive(operation)
    monkeypatch.setattr(m,'deepcopy',lambda value:value)
    with pytest.raises(ValueError,match='definition-time'):operation.receipt()


@pytest.mark.skipif(sys.platform!='win32',reason='Windows case-insensitive path spelling')
def test_controller_root_case_variant_is_rejected(case):
    operation=case.create();original=operation._exact_root
    changed=Path(original[0].swapcase()+original[1:])
    if str(changed)==str(changed.resolve(strict=True)):pytest.skip('volume preserves supplied drive case')
    with pytest.raises(ValueError,match='exact canonical root spelling'):
        m.OperationHistoricalWitness(changed,arm_id='declared-only',expected_binding_sha256='a'*64,
            expected_terminal_sha256='b'*64)
