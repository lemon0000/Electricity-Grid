"""New namespace lineage and original coordinator with tiny actual-handle scope.

The coordinator seam does not construct a genuine BootstrapOwner or run N0.
The separately required real public lifecycle remains an integration acceptance.
"""
import ast
from dataclasses import asdict,dataclass
import json
import os
from pathlib import Path
from threading import Lock,get_ident
from types import SimpleNamespace
import types
from weakref import WeakKeyDictionary

import pytest

from experiments import h1_bootstrap_integration_development_v5 as m
from tests.test_h1_phase_manifest_segment_faults_development_v1 import shared
from tests.test_h1_phase_dependency_window_faults_development_v1 import tiny
from tests.test_h1_selector_configuration_development_v1 import configuration


def test_fresh_exact_namespace_preserves_predecessor_science_schema_and_record_fields(tmp_path):
    from experiments import h1_bootstrap_integration_development_v4 as prior
    from experiments import h1_group_execution_roster_development_v4 as roster
    assert m.SCHEMA=='h1_bootstrap_integration_development_v5'
    assert m.historical_verifier.VERIFIER_SCHEMA=='h1_historical_n0_verifier_development_v4'
    assert m.historical_verifier.SCHEMA==prior.historical_verifier.SCHEMA
    assert m.BootstrapOwner is not prior.BootstrapOwner
    assert m.owned.OwnedController is not prior.owned.OwnedController
    assert roster.bootstrap is m and roster.SCHEMA=='h1_group_execution_roster_development_v4'
    pins={name:'a'*64 for name in m.N0_PINS};root='D:/unit_controller_non_authoritative'
    new=m._N0_body(root,pins);old=prior._N0_body(root,pins)
    changed={'historical_verifier_schema','historical_validation_contract'}
    assert set(new)==set(old)
    assert m.encode({k:v for k,v in new.items() if k not in changed})==m.encode({k:v for k,v in old.items() if k not in changed})
    new_global=m._global_N0_body('b'*64,new);old_global=prior._global_N0_body('b'*64,old)
    assert new_global['bootstrap_terminal_body_sha256']==m.digest(new)
    assert old_global['bootstrap_terminal_body_sha256']==prior.digest(old)
    assert m.encode({k:v for k,v in new_global.items() if k!='bootstrap_terminal_body_sha256'})==m.encode(
        {k:v for k,v in old_global.items() if k!='bootstrap_terminal_body_sha256'})
    old_text=Path(prior.historical_verifier.__file__).read_text(encoding='utf-8')
    expected=old_text.replace('h1_historical_n0_verifier_development_v3','h1_historical_n0_verifier_development_v4').replace(
        'h1_bootstrap_integration_development_v4','h1_bootstrap_integration_development_v5')
    assert Path(m.historical_verifier.__file__).read_text(encoding='utf-8')==expected


@pytest.fixture
def coordinator(shared,tmp_path):
    @dataclass(frozen=True)
    class Declaration:
        study_root:str
        selector_configuration:object
        phase_archive:object
        family:str='training_ub'
        ordinal:int=0
        def __post_init__(self):pass
    class Owner:pass
    owner=Owner();declaration=Declaration(str(tmp_path/'dynamic_non_authoritative'),configuration(),
        m.phase_manifest.ArchiveCapacityDeclaration(576,2**20,576*2**20,0))
    owner.declaration=declaration;owner._operation=owner._original_operation=Lock()
    owner.closed=owner.poisoned=False
    tree=ast.parse(Path(m.__file__).read_bytes())
    function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='_bind_phase_segments')
    space=dict(WeakKeyDictionary=WeakKeyDictionary,types=types,phase_operation=SimpleNamespace(
        PhaseManifestValidationOperation=shared.m.PhaseManifestValidationOperation,MAX_PROJECTS=256,MAX_CHECKS=4096),
        BootstrapOwner=Owner,BootstrapDeclaration=Declaration,_PHASE_RUNTIME=lambda:None,
        os=os,get_ident=get_ident,asdict=asdict,encode=m.encode,json=json,SCHEMA='unit_only_Bootstrap5',FLAGS=m.FLAGS,
        local=SimpleNamespace(_path=Path),_phase_seed_plan=lambda owner,d:((d.family,d.ordinal),))
    exec(compile(ast.Module(body=[function],type_ignores=[]),m.__file__,'exec'),space)
    run,current,external,cleanup,receipt,prepare,fingerprint=space['_bind_phase_segments']()
    space['_phase_current']=current
    value=SimpleNamespace(owner=owner,declaration=declaration,run=run,current=current,external=external,
        cleanup=cleanup,receipt=receipt,prepare=prepare,fingerprint=fingerprint,shared=shared,root=Path(declaration.study_root))
    return value


def test_original_coordinator_borrows_scope_closes_for_callback_and_reacquires_without_caching_dynamic_facts(coordinator):
    c=coordinator;trace=[]
    def body():
        first=c.current(c.owner);trace.append(('body',c.shared.tiny.m._CLEANUP_DIAGNOSTICS()['active_operations']))
        result=c.prepare(c.owner,'training_ub',0)
        assert c.run(c.owner,lambda:c.current(c.owner)) is first
        def callback():
            trace.append(('callback',c.shared.tiny.m._CLEANUP_DIAGNOSTICS()['active_operations']))
            c.root.mkdir();(c.root/'retained.json').write_bytes(b'{"unit_only":true}')
            def nested():
                trace.append(('nested',c.shared.tiny.m._CLEANUP_DIAGNOSTICS()['active_operations']))
                assert c.current(c.owner) is not first
                return c.prepare(c.owner,'training_ub',0).audit_payload
            assert c.run(c.owner,nested,site='nested callback observation')==result.audit_payload
            assert c.shared.tiny.m._CLEANUP_DIAGNOSTICS()['active_operations']==0
            return 'external result'
        assert c.external(c.owner,callback)=='external result'
        assert c.current(c.owner) is not first
        assert c.prepare(c.owner,'training_ub',0).audit_payload==result.audit_payload
        return 7
    assert c.run(c.owner,body,declaration=c.declaration,site='unit outer')==7
    assert trace==[('body',1),('callback',0),('nested',1)]
    receipt=c.receipt(c.owner)
    assert receipt['segments_opened']==len(receipt['segments'])==3
    assert receipt['lifecycle_complete'] and receipt['all_segments_closed']
    assert receipt['pending_cleanup_windows']==0 and receipt['consumer_bound'] is False
    assert all(row['receipt']['phase_kernel_receipt']['all_handles_closed'] for row in receipt['segments'])
    assert not c.shared.tiny.state['live'] and (c.root/'retained.json').read_bytes()==b'{"unit_only":true}'


@pytest.mark.parametrize('failure',['body','callback','callback_configuration','close_handle','body_and_close'])
def test_coordinator_primary_pending_retry_and_callback_drift_are_honest(coordinator,failure):
    c=coordinator;primary=RuntimeError('public segment primary')
    def body():
        c.prepare(c.owner,'training_ub',0)
        if failure in ('close_handle','body_and_close'):c.shared.tiny.state['close_fail']={1}
        if failure in ('body','body_and_close'):raise primary
        if failure=='callback':
            def fail():
                assert c.shared.tiny.m._CLEANUP_DIAGNOSTICS()['active_operations']==0
                raise primary
            c.external(c.owner,fail)
        elif failure=='callback_configuration':
            c.external(c.owner,lambda:object.__setattr__(c.declaration,'ordinal',101))
    expected=ValueError if failure=='callback_configuration' else OSError if failure=='close_handle' else RuntimeError
    with pytest.raises(expected) as caught:c.run(c.owner,body,declaration=c.declaration)
    if failure in ('body','callback','body_and_close'):assert caught.value is primary
    receipt=c.receipt(c.owner)
    assert c.owner.poisoned and receipt['first_failure'] is not None and not receipt['lifecycle_complete']
    if failure in ('close_handle','body_and_close'):
        assert receipt['pending_cleanup_windows']==1 and len(c.shared.tiny.state['live'])==1
        c.cleanup(c.owner);receipt=c.receipt(c.owner)
    assert receipt['all_segments_closed'] and receipt['pending_cleanup_windows']==0
    assert not c.shared.tiny.state['live']
    with pytest.raises(ValueError,match='unpoisoned'):c.run(c.owner,lambda:None)
