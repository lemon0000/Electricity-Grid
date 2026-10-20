"""Successor5 N0 protocol faults with synthetic science; saved science is separate."""
from copy import deepcopy
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import threading

import pytest

from experiments import h1_historical_n0_verifier_development_v5 as original
from experiments import h1_bootstrap_integration_development_v6 as bootstrap
from tests.test_rq2_normal_h1_source_v1 import packet


class Lease:
    def __init__(self):self.closed=False
    def check(self):
        if self.closed:raise ValueError('closed lease')


@pytest.fixture
def case(tmp_path,monkeypatch,request):
    calls=[];contexts=[];fault=[None];dispatch=[('unit-only-dispatch',)];retire_fault=[True]
    owned_leases=[]
    def release_leases():
        for lease in reversed(owned_leases):lease.close()
    request.addfinalizer(release_leases)
    def dispatch_view(caller=None):
        key=(original.lease_store.__name__,'_REGISTRY')
        return ((key,'constant',original._freeze(original.lease_store._REGISTRY)),),dispatch[0]
    monkeypatch.setattr(original.prior_witness,'_dispatch_view',dispatch_view)
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
    binding_start=source.index('(RegistryValidationScope,registry_validation_scope,')
    binding_end=source.index('=_bind_registry_scope()',binding_start)+len('=_bind_registry_scope()')
    source=source[:binding_start]+source[binding_end:]
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
    m._projection=project
    fault_mode=getattr(request,'param',None)
    if fault_mode is not None:
        kind,index=fault_mode.split('_');target='root_'+index
        attribute={'poison':'_poison_operation','close':'_close_operation','retire':'_retire_operation'}[kind]
        original_method=getattr(m,attribute)
        def faulted(operation,*args,**kwargs):
            if kind=='close':result=original_method(operation,*args,**kwargs)
            if Path(operation._exact_root).name==target and (kind!='retire' or retire_fault[0]):
                raise OSError('injected '+fault_mode)
            return result if kind=='close' else original_method(operation,*args,**kwargs)
        setattr(m,attribute,faulted)
    (m.RegistryValidationScope,m.registry_validation_scope,m._registry_declare_operation,
        m._registry_check_operation,m._close_registry_scope,m._poison_registry_scope,
        m._registry_scope_receipt,m._bind_registry_bootstrap,m._retire_registry_scope)=m._bind_registry_scope()
    # Definition-before seam for protocol units only. Production's one-time
    # binding captures the real, initialized BootstrapOwner._check instead.
    with monkeypatch.context() as patch:
        patch.setattr(bootstrap.BootstrapOwner,'_check',lambda owner:None)
        open_scope=m._bind_registry_bootstrap(bootstrap.BootstrapOwner,bootstrap.BootstrapOwner._check)
    m._install_runtime_checks()
    def create(*,reuse=True,owner=None):
        return m.N0ValidationOperation(tmp_path,arm_id='a'*64,expected_binding_sha256='a'*64,
            expected_terminal_sha256='b'*64,reuse_numerical_proof=reuse,maximum_prepares=4,
            _bootstrap_owner=owner,diagnostic_only=reuse and owner is None)
    def body(envelope):
        return dict(controller_root=str(tmp_path),historical_verifier_schema=m.VERIFIER_SCHEMA,
            historical_validation_contract=m.VERIFIER_SCHEMA,
            historical_verifier_identity=envelope.verifier_identity,
            audit_payload_sha256=m.io.digest(envelope.audit_payload))
    def build(operation,index=None,*,confirm=True):
        if index is None:index=operation._attempts
        ticket=operation.begin_build(operation._bootstrap_owner,'build_'+str(index+1).zfill(3))
        envelope=operation.prepare()
        if confirm:operation.confirm_build(ticket,body(envelope))
        return ticket,envelope
    def owner():
        value=object.__new__(bootstrap.BootstrapOwner)
        value.closed=False;value.poisoned=False;value._operation=threading.Lock()
        value._original_operation=value._operation;value._operation.acquire()
        value._operation_nonce=object();value.declaration=object()
        value.roots={'controller':str(tmp_path)};value._slot={'slot_id':'a'*64}
        for name in ('_global','_bootstrap'):
            lease=m.lease_store._Lease(tmp_path/('owner_'+str(len(owned_leases))+'_non_authoritative'),True)
            owned_leases.append(lease)
            journal=SimpleNamespace(_lease=lease,_original_lease=lease)
            setattr(value,name,journal);setattr(value,'_original'+name,journal)
        return value
    return SimpleNamespace(m=m,create=create,build=build,body=body,owner=owner,scope=open_scope,
        calls=calls,contexts=contexts,fault=fault,dispatch=dispatch,raw=raw,retire_fault=retire_fault)


def build_root(case,scope,root,arm,*,site='registry'):
    scope.begin_build(scope_owner(scope),root,arm,site)
    envelope=case.m.prepare(root,expected_binding_sha256='a'*64,expected_terminal_sha256='b'*64,
        completed_hours=1,registry_scope=scope)
    body=case.body(envelope);body.update(controller_root=str(root),slot_id=arm,
        controller_binding_sha256='a'*64,controller_terminal_sha256='b'*64)
    scope.confirm_build(body);return envelope


def scope_record(scope):
    # Inspect the original private record only in this fault-test fixture.
    fn=scope.begin_build.__func__
    closure=dict(zip(fn.__code__.co_freevars,(c.cell_contents for c in fn.__closure__)))
    check=closure['check'];view=dict(zip(check.__code__.co_freevars,(c.cell_contents for c in check.__closure__)))
    return view['row'](scope)


def scope_owner(scope):return scope_record(scope)['owner']


def test_retirement_requires_exact_closed_scope_and_releases_arm_records(case,tmp_path):
    owner=case.owner();root,arm=roots(case,tmp_path,1)[0]
    scope=case.scope(owner)
    try:
        with pytest.raises(ValueError,match='closed original'):case.m._retire_registry_scope(scope)
        with scope:
            build_root(case,scope,root,arm)
            with pytest.raises(ValueError,match='closed original'):case.m._retire_registry_scope(scope)
        proof=case.m._registry_scope_receipt(scope)
        assert proof['complete']
        operations=list(scope_record(scope)['operations'].values())
        with pytest.raises(ValueError,match='original registry'):case.m._retire_registry_scope(object())
        case.m._retire_registry_scope(scope)
        with pytest.raises(ValueError,match='original registry'):case.m._retire_registry_scope(scope)
        for op in operations:
            with pytest.raises(ValueError,match='original N0 resource'):case.m._retire_operation(op)
    finally:owner._operation.release()


def test_retirement_checks_scope_identity_even_if_a_foreign_key_is_present(case,tmp_path):
    owner=case.owner();scope=case.scope(owner)
    try:
        with scope:pass
        closure=dict(zip(case.m._retire_registry_scope.__code__.co_freevars,
            (cell.cell_contents for cell in case.m._retire_registry_scope.__closure__)))
        row=closure['row']
        records=dict(zip(row.__code__.co_freevars,(cell.cell_contents for cell in row.__closure__)))['records']
        foreign=object();records[id(foreign)]=records[id(scope)]
        try:
            with pytest.raises(ValueError,match='original registry'):case.m._retire_registry_scope(foreign)
        finally:del records[id(foreign)]
        case.m._retire_registry_scope(scope)
        assert not records
    finally:owner._operation.release()


def test_retirement_rejects_any_foreign_active_capsule_for_same_owner(case):
    owner=case.owner();scope=case.scope(owner)
    try:
        with scope:pass
        closure=dict(zip(case.m._retire_registry_scope.__code__.co_freevars,
            (cell.cell_contents for cell in case.m._retire_registry_scope.__closure__)))
        active=closure['active'];active[id(owner)]=object()
        try:
            with pytest.raises(ValueError,match='closed original'):case.m._retire_registry_scope(scope)
        finally:del active[id(owner)]
        case.m._retire_registry_scope(scope)
    finally:owner._operation.release()


def test_runtime_registry_missing_owner_key_rejects_binding(case,tmp_path):
    owner=case.owner();root,arm=roots(case,tmp_path,1)[0]
    store=case.m.lease_store;key=owner._global._lease.key
    try:
        with store._REGISTRY_LOCK:store._REGISTRY.remove(key)
        with pytest.raises(ValueError,match='lease missing from runtime registry'):
            with case.scope(owner) as scope:build_root(case,scope,root,arm)
    finally:
        with store._REGISTRY_LOCK:store._REGISTRY.add(key)
        owner._operation.release()


def test_runtime_registry_drift_between_builds_poison_scope(case,tmp_path):
    owner=case.owner();root,arm=roots(case,tmp_path,1)[0]
    store=case.m.lease_store;foreign=str(tmp_path/'foreign_non_authoritative')
    try:
        with pytest.raises(ValueError,match='store registry membership changed'):
            with case.scope(owner) as scope:
                build_root(case,scope,root,arm)
                with store._REGISTRY_LOCK:store._REGISTRY.add(foreign)
                build_root(case,scope,root,arm)
        receipt=scope.receipt()
        assert not receipt['complete'] and receipt['confirmed_builds']==1
        assert all(not row['complete'] for row in receipt['root_receipts'])
    finally:
        with store._REGISTRY_LOCK:store._REGISTRY.discard(foreign)
        owner._operation.release()


def test_runtime_registry_drift_before_build_confirmation_rejects_publication(case,tmp_path):
    store=case.m.lease_store;foreign=str(tmp_path/'foreign_non_authoritative')
    try:
        with pytest.raises(ValueError,match='store registry membership changed'):
            with case.create() as operation:
                ticket,envelope=case.build(operation,confirm=False)
                with store._REGISTRY_LOCK:store._REGISTRY.add(foreign)
                operation.confirm_build(ticket,case.body(envelope))
        receipt=operation.receipt()
        assert receipt['closed'] and receipt['proof_cleared'] and not receipt['complete']
        assert not receipt['confirmed_builds']
    finally:
        with store._REGISTRY_LOCK:store._REGISTRY.discard(foreign)


def roots(case,tmp_path,count=3):
    result=[]
    for i in range(count):
        path=tmp_path/('root_'+str(i));path.mkdir();result.append((path,str(i+1)*64))
    return result


def test_three_roots_reuse_independent_proofs_across_26_registry_rounds(case,tmp_path):
    owner=case.owner();declared=roots(case,tmp_path)
    try:
        with case.scope(owner) as scope:
            assert case.m.registry_validation_scope(owner) is scope
            for iteration in range(26):
                for root,arm in declared:build_root(case,scope,root,arm)
        receipt=scope.receipt()
        assert receipt['complete'] and receipt['confirmed_builds']==78
        assert receipt['full_numerical_hour_replays']==12
        assert receipt['fresh_byte_context_revalidations']==3*(4+25*8)
        assert receipt['context_observations']==78*16 and len(case.calls)==12
        assert len(receipt['root_receipts'])==3 and case.m.registry_validation_scope(owner) is None
        assert all(r['closed'] and r['proof_cleared'] and r['complete'] for r in receipt['root_receipts'])
        assert len({r['controller_root_exact'] for r in receipt['root_receipts']})==3
        assert not receipt['formal_result'] and not receipt['native_execution_authorized']
    finally:owner._operation.release()


@pytest.mark.parametrize('edge',range(96))
def test_first_and_reused_context_edges_fail_closed_for_all_roots(case,tmp_path,edge):
    owner=case.owner();declared=roots(case,tmp_path);case.fault[0]=edge
    try:
        with pytest.raises(OSError,match='context read failure'):
            with case.scope(owner) as scope:
                for _ in range(2):
                    for root,arm in declared:build_root(case,scope,root,arm)
        receipt=scope.receipt()
        assert not receipt['complete'] and receipt['first_failure']
        assert all(r['closed'] and r['proof_cleared'] for r in receipt['root_receipts'])
        assert case.m.registry_validation_scope(owner) is None and len(case.contexts)==edge+1
    finally:owner._operation.release()


@pytest.mark.parametrize('fault',['root','binding','terminal','arm','fourth_root','nonce','guard','declaration'])
def test_registry_slot_binding_caps_and_owner_drift_rejected(case,tmp_path,fault):
    owner=case.owner();guard=owner._operation;declared=roots(case,tmp_path,4)
    try:
        with pytest.raises(ValueError):
            with case.scope(owner) as scope:
                build_root(case,scope,*declared[0])
                if fault=='fourth_root':
                    for root,arm in declared[1:]:build_root(case,scope,root,arm)
                elif fault in ('nonce','guard','declaration'):
                    if fault=='nonce':owner._operation_nonce=object()
                    elif fault=='guard':owner._operation=threading.Lock()
                    else:owner.declaration=object()
                    build_root(case,scope,*declared[0])
                else:
                    root,arm=declared[1] if fault=='root' else declared[0]
                    if fault=='root':arm=declared[0][1]
                    if fault=='arm':arm='f'*64
                    scope.begin_build(owner,root,arm,'registry')
                    case.m.prepare(root,expected_binding_sha256=('c'*64 if fault=='binding' else 'a'*64),
                        expected_terminal_sha256=('c'*64 if fault=='terminal' else 'b'*64),
                        completed_hours=1,registry_scope=scope)
        assert not scope.receipt()['complete'] and case.m.registry_validation_scope(owner) is None
    finally:
        if guard.locked():guard.release()


def test_per_root_prepare_limit_is_finite_and_does_not_fall_back(case,tmp_path):
    owner=case.owner();root,arm=roots(case,tmp_path,1)[0]
    try:
        with pytest.raises(ValueError,match='ordinal|bounded'):
            with case.scope(owner) as scope:
                for _ in range(65):build_root(case,scope,root,arm)
        assert len(case.calls)==4 and not scope.receipt()['complete']
        assert case.m.registry_validation_scope(owner) is None
    finally:owner._operation.release()


def test_first_build_must_be_confirmed_before_another_root_can_start(case,tmp_path):
    owner=case.owner();declared=roots(case,tmp_path,2)
    try:
        with pytest.raises(ValueError,match='nonreentrant'):
            with case.scope(owner) as scope:
                root,arm=declared[0];scope.begin_build(owner,root,arm,'registry')
                case.m.prepare(root,expected_binding_sha256='a'*64,expected_terminal_sha256='b'*64,
                    completed_hours=1,registry_scope=scope)
                scope.begin_build(owner,*declared[1],'registry')
        assert not scope.receipt()['complete'] and case.m.registry_validation_scope(owner) is None
    finally:owner._operation.release()


def test_caught_scope_error_cannot_be_repaired_and_reused(case,tmp_path):
    owner=case.owner();root,arm=roots(case,tmp_path,1)[0]
    try:
        with pytest.raises(ValueError):
            with case.scope(owner) as scope:
                build_root(case,scope,root,arm)
                scope.begin_build(owner,root,arm,'registry')
                with pytest.raises(ValueError):
                    case.m.prepare(root.parent,expected_binding_sha256='a'*64,expected_terminal_sha256='b'*64,
                        completed_hours=1,registry_scope=scope)
                with pytest.raises(ValueError,match='lifetime'):
                    case.m.prepare(root,expected_binding_sha256='a'*64,expected_terminal_sha256='b'*64,
                        completed_hours=1,registry_scope=scope)
        assert not scope.receipt()['complete'] and case.m.registry_validation_scope(owner) is None
    finally:owner._operation.release()


def test_uninitialized_exact_owner_cannot_mint_scope_without_private_bootstrap_entry(case):
    owner=case.owner()
    try:
        with pytest.raises(ValueError,match='private authenticated'):
            case.m.RegistryValidationScope(owner)
        with pytest.raises(ValueError,match='definition-time'):
            case.m._bind_registry_bootstrap(bootstrap.BootstrapOwner,bootstrap.BootstrapOwner._check)
    finally:owner._operation.release()


@pytest.mark.parametrize('case',[f'{kind}_{i}' for kind in ('poison','close') for i in range(3)],indirect=True)
def test_each_root_cleanup_failure_still_clears_all_original_guards_and_proofs(case,tmp_path):
    owner=case.owner();declared=roots(case,tmp_path)
    try:
        with pytest.raises(RuntimeError,match='original body failure') as caught:
            with case.scope(owner) as scope:
                for root,arm in declared:build_root(case,scope,root,arm)
                raise RuntimeError('original body failure')
        receipt=scope.receipt()
        assert not receipt['complete'] and receipt['first_failure']==repr(caught.value)
        assert caught.value.__notes__
        operations=scope_record(scope)['operations'].values()
        assert all(op._proof is op._candidate_proof is None and not op._original_guard.locked() for op in operations)
        assert case.m.registry_validation_scope(owner) is None and owner._operation.locked()
    finally:owner._operation.release()

