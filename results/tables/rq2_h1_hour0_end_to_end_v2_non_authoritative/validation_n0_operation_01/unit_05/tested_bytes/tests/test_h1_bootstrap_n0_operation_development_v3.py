"""Actual registration algorithm with isolated journals and synthetic numerical seams.

These protocol units do not claim a native Job, durable archive, or full chain.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import FunctionType, SimpleNamespace

import pytest

from experiments import h1_bootstrap_integration_development_v3 as bootstrap
from tests.test_h1_historical_n0_verifier_development_v2 import case


class Journal:
    def __init__(self,rows,lane,fault):self.saved=rows;self.lane=lane;self.fault=fault
    def rows(self):return deepcopy(self.saved)
    def reserve(self,count):pass
    def append(self,body,*,expected_head):
        assert expected_head==self.saved[-1][0]
        if self.fault==self.lane+'_before':raise OSError('injected '+self.fault)
        head=sha256(bootstrap.encode(body)).hexdigest();self.saved.append((head,deepcopy(body)))
        if self.fault==self.lane+'_after':raise OSError('injected '+self.fault)
        return head


def inner(method):
    return next(cell.cell_contents for cell in method.__closure__ if type(cell.cell_contents) is FunctionType)


def protocol(case,*,fault=None):
    m=case.m;owner=case.owner();root=Path(owner.roots['controller']);events=[];operations=[]
    obligation=root/'obligation_non_authoritative';obligation.mkdir()
    terminal=b'unit-only-terminal';(obligation/'000.terminal.json').write_bytes(terminal)
    terminal_pin=sha256(terminal).hexdigest()
    claim=dict(slot_id=owner._slot['slot_id'],claim_proposal_id='a'*64,
        proposal=dict(roots=dict(controller=str(root))))
    ready=('c'*64,dict(parent_declaration={},files_sha256={
        'obligation_non_authoritative/binding.json':'a'*64}))
    owner._bootstrap=Journal([('a'*64,{}),('b'*64,{}),ready,('d'*64,{})],'local',fault)
    owner._global=Journal([('e'*64,{}),('f'*64,{})],'global',fault)
    owner._check=lambda:None;owner._reserve_N0_bytes=lambda:None
    owner._remaining_global_records=lambda:1
    def build(*args,n0_operation=None,n0_site=None):
        events.append(n0_site)
        token=n0_operation.begin_build(owner,n0_site) if n0_operation is not None else None
        envelope=m.prepare(root,expected_binding_sha256='a'*64,expected_terminal_sha256=terminal_pin,
            completed_hours=1,n0_operation=n0_operation)
        if fault==n0_site+'_tail':raise OSError('injected '+fault)
        pins={key:'a'*64 for key in bootstrap.N0_PINS}
        pins.update(controller_terminal_sha256=terminal_pin,audit_payload_sha256=m.io.digest(envelope.audit_payload),
            historical_verifier_identity=envelope.verifier_identity)
        body=bootstrap._N0_body(str(root),pins)
        if n0_operation is not None:n0_operation.confirm_build(token,body)
        return body
    owner._build_N0_terminal=build
    def registry(*,n0_operation=None,n0_site=None):
        if len(owner._bootstrap.saved)==5:build(n0_operation=n0_operation,n0_site=n0_site)
        return {owner._slot['slot_id']:dict(claim=('a'*64,claim),release=('b'*64,{}))}
    def replay(*,n0_operation=None):
        if len(owner._global.saved)==3:
            registry(n0_operation=n0_operation,n0_site='registry_before')
            registry(n0_operation=n0_operation,n0_site='registry_after')
            return 'pending_post_N'
        return 'execution_indeterminate'
    checks=[0]
    def observe(*args):
        checks[0]+=1
        if fault=='final_observe' and checks[0]==5:raise OSError('injected final_observe')
    owner._registry=registry;owner._replay=replay;owner._observe_N0=observe
    # Keep the production algorithm and its cleanup factory code. Only fixture
    # dependencies are supplied in a separate globals dictionary, with no alias
    # installed in the actual module or scientific identity.
    namespace=dict(vars(bootstrap),historical_verifier=m,_check_N0_contract=lambda owner:None)
    factory=FunctionType(bootstrap._bind_N0_scope.__code__,namespace)
    run=factory()
    def capture(owner,root,binding_pin,terminal_pin,execute):
        def tracked(operation):operations.append(operation);return execute(operation)
        return run(owner,root,binding_pin,terminal_pin,tracked)
    namespace['_run_N0_operation']=capture
    if fault=='result':
        class BrokenFlags:
            def keys(self):raise OSError('injected result')
        namespace['FLAGS']=BrokenFlags()
    finish=FunctionType(inner(bootstrap.BootstrapOwner._finish_N0_terminal).__code__,namespace)
    return SimpleNamespace(owner=owner,run=lambda:finish(owner,create_local=True),events=events,
        operations=operations,checks=checks)


def test_registration_uses_four_distinct_builds_and_publishes_actual_receipt(case):
    p=protocol(case)
    try:
        result=p.run();receipt=case.m.json.loads(result['N0_validation_execution_receipt'])
        assert result['state']=='pending_post_N' and receipt['complete']
        assert p.events==list(case.m.BUILD_SITES) and p.checks[0]==5
        assert receipt['bootstrap_operation_bound'] and not receipt['diagnostic_only']
        assert receipt['context_observations']==64 and len(case.calls)==4
        assert len(p.owner._bootstrap.saved)==5 and len(p.owner._global.saved)==3
        assert all(result[key] is False for key in bootstrap.FLAGS)
    finally:p.owner._operation.release()


@pytest.mark.parametrize('fault',['explicit_primary_tail','explicit_after_local_tail',
    'registry_before_tail','registry_after_tail','local_before','local_after','global_before',
    'global_after','final_observe','result'])
def test_registration_failure_windows_clear_proof_and_release_private_guard(case,fault):
    p=protocol(case,fault=fault)
    try:
        with pytest.raises(OSError,match='injected'):p.run()
        assert len(p.operations)==1
        operation=p.operations[0];receipt=operation.receipt()
        assert not receipt['complete'] and receipt['first_failure'] and receipt['proof_cleared']
        assert not operation._original_guard.locked() and operation._candidate_proof is None
        assert p.owner._operation.locked()  # The enclosing bootstrap still owns its guard.
        if fault.startswith('local_'):assert len(p.owner._global.saved)==2
        if fault=='global_after':assert len(p.owner._global.saved)==3
    finally:p.owner._operation.release()


@pytest.mark.parametrize('fault',['method','method_code','method_defaults','prepare','checker','scope',
    'sites','instance'])
def test_actual_bootstrap_contract_rejects_route_drift_before_entry(monkeypatch,fault):
    owner=SimpleNamespace()
    with monkeypatch.context() as patch:
        if fault=='method':patch.setattr(bootstrap.BootstrapOwner,'_registry',lambda *a:None)
        elif fault=='method_code':
            fn=bootstrap.BootstrapOwner._registry
            patch.setattr(fn,'__code__',fn.__code__.replace(co_name='changed'))
        elif fault=='method_defaults':patch.setattr(bootstrap.BootstrapOwner._replay,'__defaults__',('changed',))
        elif fault=='prepare':patch.setattr(bootstrap,'_prepare_N0',lambda *a:None)
        elif fault=='checker':patch.setattr(bootstrap,'_check_N0_contract',lambda *a:None)
        elif fault=='scope':patch.setattr(bootstrap.historical_verifier,'N0ValidationOperation',object)
        elif fault=='sites':patch.setattr(bootstrap.historical_verifier,'BUILD_SITES',('changed',))
        else:owner._registry=lambda:None
        with pytest.raises(ValueError,match='N0 bootstrap route'):
            bootstrap.BootstrapOwner._replay(owner)
