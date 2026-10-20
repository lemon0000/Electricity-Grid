"""Deferred Parent proof state machine; numerical and host contexts are explicit fakes."""
from copy import deepcopy
from pathlib import Path
import sys
import threading
from types import ModuleType, SimpleNamespace

import pytest

from experiments import h1_historical_hour_witness_development_v1 as prior
from experiments import h1_historical_n0_verifier_development_v1 as verifier
from experiments import h1_selector_parent_validation_operation_development_v1 as host
from tests import test_h1_operation_historical_witness_development_v1 as protocol


@pytest.fixture
def case(tmp_path, monkeypatch):
    calls=[];context=['stable'];allowed=[False]
    owner=SimpleNamespace(root=tmp_path)
    lease=object()
    def lease_check(value, parent):
        if value is not lease or parent is not owner:
            raise ValueError('wrong unit-only Parent lease')
    monkeypatch.setattr(host,'_lease_check',lease_check)
    monkeypatch.setattr(host,'_parent_confirmed',lambda value,parent,witness:
        value is lease and parent is owner and allowed[0])
    monkeypatch.setattr(prior,'_dispatch_view',lambda caller=None:('explicit-unit-dispatch',))
    monkeypatch.setattr(verifier,'verifier_identity',lambda:'e'*64)
    def observe(scope,*args):
        scope._check()
        return (context[0],)*8+({'archive':'explicit-unit-only'},)
    monkeypatch.setattr(prior._HourScope,'_context',observe)
    raw=dict(projection_payload=b'payload',canonical_locks=(20.,1.,20.),
        native_total_ns=2,full_hour_chain_recomputed=True)
    def full(*args,**kwargs):
        calls.append('full')
        return deepcopy(raw)
    monkeypatch.setattr(prior.hour,'inspect',full)
    path=Path('experiments/h1_parent_source_n0_witness_development_v1.py').resolve()
    name='experiments._parent_source_n0_unit_'+tmp_path.name
    fresh=ModuleType(name);fresh.__file__=str(path);fresh.__package__='experiments'
    monkeypatch.setitem(sys.modules,name,fresh)
    exec(compile(path.read_bytes(),str(path),'exec'),vars(fresh))
    monkeypatch.setattr(protocol,'m',fresh)
    def create():
        return fresh.ParentSourceWitness(tmp_path,arm_id='explicit-unit-Parent',
            expected_binding_sha256='a'*64,expected_terminal_sha256='b'*64,
            _parent_lease=lease,_parent_owner=owner)
    return SimpleNamespace(m=fresh,create=create,calls=calls,context=context,
        allowed=allowed,owner=owner,lease=lease)


def drive(operation, *, fail_prefix=None):
    try:
        token=operation._start()
        for index in range(2):
            protocol.prefix(operation,token,index,fail_site=2 if index==fail_prefix else None)
        return operation._finish(token,SimpleNamespace(decision_bytes=b'current-science'),b'exact-source-compatibility')
    except BaseException as error:
        operation._poison(error)
        raise


def confirm(case,operation):
    for _ in range(16):assert drive(operation)==(4,4)
    assert operation._proof is None and operation._candidate_proof is not None
    case.allowed[0]=True
    operation.activate()


def test_only_complete_parent_can_activate_then_all_old_contexts_stay(case):
    with case.create() as operation:
        for _ in range(16):assert drive(operation)==(4,4)
        assert len(case.calls)==64 and operation._contexts==256
        assert operation._proof is None and operation._candidate_proof is not None
        case.allowed[0]=True
        operation.activate()
        assert drive(operation)==(0,8)
        assert len(case.calls)==64 and operation._contexts==272
    receipt=operation.receipt()
    assert receipt['complete'] and receipt['proof_cleared']
    assert receipt['full_numerical_hour_replays']==64
    assert receipt['reused_numerical_inspections']==72
    assert not receipt['compatibility_counts_describe_actual_execution']


@pytest.mark.parametrize('completed',[0,1,15,16])
def test_no_activation_before_full_parent_success(case,completed):
    with case.create() as operation:
        for _ in range(completed):drive(operation)
        with pytest.raises(ValueError,match='complete original Parent'):
            operation.activate()
        assert operation._proof is None and operation._candidate_proof is None


def test_last_prefix_failure_discards_all_pending_full_results(case):
    with case.create() as operation:
        for _ in range(15):drive(operation)
        with pytest.raises(RuntimeError,match='prefix failure'):drive(operation,fail_prefix=1)
        assert operation._proof is operation._candidate_proof is None
        case.allowed[0]=True
        with pytest.raises(ValueError):operation.activate()


def test_changed_input_after_commit_poisoned_without_full_fallback(case):
    with case.create() as operation:
        confirm(case,operation)
        case.context[0]='changed'
        with pytest.raises(ValueError,match='context changed'):drive(operation)
        assert len(case.calls)==64
        assert operation._proof is operation._candidate_proof is None


@pytest.mark.parametrize('field',['lease','owner','guard','proof'])
def test_cross_owner_or_mutated_proof_rejected(case,field):
    with case.create() as operation:
        confirm(case,operation)
        if field=='lease':operation._parent_lease=object()
        elif field=='owner':operation._parent_owner=SimpleNamespace(root=case.owner.root)
        elif field=='guard':operation._original_guard.release()
        else:operation._proof[0][2]['projection_payload']=b'mutated'
        with pytest.raises(ValueError):drive(operation)
        assert len(case.calls)==64 and operation._proof is operation._candidate_proof is None


def test_frozen_cleanup_does_not_depend_on_live_os_or_report_copy(case,monkeypatch):
    operation=case.create().__enter__()
    confirm(case,operation)
    monkeypatch.setattr(case.m,'os',SimpleNamespace(getpid=lambda:-1))
    monkeypatch.setattr(case.m,'deepcopy',lambda value:(_ for _ in ()).throw(RuntimeError('report copy failure')))
    operation.close()
    assert operation._proof is operation._candidate_proof is None
    assert operation._ended and not operation._original_guard.locked()


def test_wrong_thread_cannot_use_a_committed_parent_proof(case):
    with case.create() as operation:
        confirm(case,operation)
        errors=[]
        def foreign():
            try:drive(operation)
            except ValueError as error:errors.append(str(error))
        thread=threading.Thread(target=foreign);thread.start();thread.join()
        assert errors and operation._proof is operation._candidate_proof is None


def test_direct_diagnostic_prepare_is_not_an_owned_source_entry(case):
    with case.create() as operation:
        with pytest.raises(TypeError,match='bound Parent source'):operation.prepare()
