"""Diagnostic sequencing faults; real saved replay is a separate bounded entry."""
from copy import copy,deepcopy
from dataclasses import replace
import pickle
from pathlib import Path
from types import SimpleNamespace
import threading

import pytest

from experiments import h1_operation_historical_witness_development_v1 as m


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
    monkeypatch.setattr(m.prior_witness,'_dispatch_view',lambda caller=None:('unit-only-dispatch',))
    def observe(scope,*args):scope._check();return context[0],{'snapshot':'unit-only'}
    monkeypatch.setattr(m,'_CONTEXT',observe)
    raw=dict(projection_payload=b'payload',canonical_locks=(20.,1.,20.),native_total_ns=2,
        full_hour_chain_recomputed=True)
    def full(*args,**kwargs):calls.append('full');return deepcopy(raw)
    monkeypatch.setattr(m.hour,'inspect',full)
    def create(reuse=True):return m.OperationHistoricalWitness(tmp_path,arm_id='network-only',
        expected_binding_sha256='a'*64,expected_terminal_sha256='b'*64,reuse_numerical_proof=reuse)
    return SimpleNamespace(create=create,calls=calls,context=context,raw=raw)


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
    assert receipt['complete'] and receipt['closed'] and receipt['proof_cleared']
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
        if field=='context':operation._proof[0][0][1]['snapshot']='changed'
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
