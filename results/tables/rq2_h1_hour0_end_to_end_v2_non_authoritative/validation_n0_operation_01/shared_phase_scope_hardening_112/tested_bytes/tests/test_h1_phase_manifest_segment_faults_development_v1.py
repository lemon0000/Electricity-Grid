"""Shared-segment fault composition with unit science and actual Windows handles."""
from hashlib import sha256
import gc
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from weakref import ref

import pytest

import experiments
from experiments import h1_phase_manifest_validation_operation_development_v1 as original
from tests.test_h1_phase_dependency_window_faults_development_v1 import tiny
from tests.test_h1_selector_configuration_development_v1 import configuration


def load_segment(monkeypatch,tmp_path):
    name='experiments._shared_segment_fault_'+tmp_path.name
    spec=importlib.util.spec_from_file_location(name,original.__file__)
    value=importlib.util.module_from_spec(spec);monkeypatch.setitem(sys.modules,name,value)
    spec.loader.exec_module(value)
    return value


@pytest.fixture
def shared(tiny,tmp_path,monkeypatch):
    # These proxies are declared before loading the segment. No canonical
    # science or public-owner equivalence is claimed by this tiny fixture.
    def proxy(label):
        value=ModuleType('experiments._shared_'+label+'_'+tmp_path.name)
        value.__file__=tiny.m.__file__;value.__spec__=None;value.__loader__=None;value.__package__='experiments'
        monkeypatch.setitem(sys.modules,value.__name__,value);return value
    b=proxy('binding');k=proxy('kernel');b.io=original.binding.io;b.owner=original.binding.owner
    b.PreparedManifest=original.binding.PreparedManifest;b._validate=original.binding._validate
    b._RUNTIME=lambda:None;b.implementation_identity=lambda c:'b'*64
    b._evidence=lambda data:dict(verifier_implementation_sha256=data['verifier_implementation_sha256'],
        dependency_inventory_sha256=sha256(b.owner.encode(data['dependency_sha256'])).hexdigest())
    faults=dict(project_error=None)
    def project(family,ordinal,c,archive,science,implementation):
        if faults['project_error'] is not None:raise faults['project_error']
        raw=b.owner.encode(dict(unit_only=True,family=family,ordinal=ordinal))
        return None,raw,sha256(raw).hexdigest()
    b._project=project
    for name in ('implementation_identity','_plain','predecessor','handles','MAX_PREPARES'):
        setattr(k,name,getattr(tiny.m,name))
    k.PhaseDependencyValidationOperation=tiny.m.PhaseDependencyValidationOperation
    def complete(value,index):
        value['group_identity']='a'*64;value['implementation_sha256']=value['implementation']
    tiny.state['on_project']=complete
    monkeypatch.setattr(experiments,'h1_phase_manifest_binding_development_v3',b)
    monkeypatch.setattr(experiments,'h1_phase_dependency_validation_operation_development_v1',k)
    m=load_segment(monkeypatch,tmp_path)
    def operation(*,root=None,checks=32):
        return m.PhaseManifestValidationOperation(plan=(('training_ub',0),),configuration=configuration(),
            archive=original.binding.ArchiveCapacityDeclaration(576,2**20,576*2**20,0),
            dynamic_roots=(tmp_path/'dynamic_non_authoritative' if root is None else root,),
            maximum_projects=4,maximum_checks=checks,diagnostic_only=True)
    return SimpleNamespace(m=m,operation=operation,tiny=tiny,faults=faults)


@pytest.mark.parametrize('failure',['project','body','exit_read','close_handle','body_and_close','check_bound'])
def test_shared_segment_failure_is_sticky_and_cleans_actual_resources(shared,failure):
    primary=RuntimeError('shared segment body primary')
    window=shared.operation(checks=1 if failure=='check_bound' else 32)
    if failure=='project':shared.faults['project_error']=primary
    expected=OSError if failure in ('exit_read','close_handle') else ValueError if failure=='check_bound' else RuntimeError
    with pytest.raises(expected) as caught:
        with window:
            window.prepare('training_ub',0)
            if failure=='exit_read':shared.tiny.state['read_fail']=shared.tiny.state['reads']+1
            elif failure in ('close_handle','body_and_close'):shared.tiny.state['close_fail']={1}
            if failure in ('body','body_and_close'):raise primary
    if failure in ('project','body','body_and_close'):assert caught.value is primary
    receipt=window.receipt()
    if failure in ('close_handle','body_and_close'):
        assert receipt['state']=='cleanup_pending' and not receipt['original_guard_released']
        assert receipt['phase_kernel_receipt']['pending_handles']==1
        window.retry_cleanup();receipt=window.receipt()
    assert receipt['closed'] and not receipt['lifecycle_complete'] and receipt['first_failure'] is not None
    assert receipt['cached_science_cleared'] and receipt['original_guard_released']
    assert receipt['phase_kernel_receipt']['all_handles_closed'] and not shared.tiny.state['live']
    cleanup=shared.tiny.m._CLEANUP_DIAGNOSTICS()
    assert cleanup['active_operations']==cleanup['abandoned_pending_operations']==0


@pytest.mark.parametrize('mutation',['registry','spec_origin','loader_path','prepare_method','source_descriptor'])
def test_shared_segment_definition_routes_are_checked_before_any_handle(shared,monkeypatch,mutation):
    m=shared.m
    if mutation=='registry':monkeypatch.setitem(sys.modules,m.__name__,ModuleType(m.__name__))
    elif mutation=='spec_origin':monkeypatch.setattr(m.__spec__,'origin','forged.py')
    elif mutation=='loader_path':monkeypatch.setattr(m.__loader__,'path','forged.py')
    elif mutation=='prepare_method':monkeypatch.setattr(m.PhaseManifestValidationOperation,'prepare',lambda *args:None)
    else:monkeypatch.setattr(Path,'read_bytes',lambda self:b'forged source')
    with pytest.raises(ValueError,match='definition-time'):shared.operation()
    assert shared.tiny.state['opens']==0


@pytest.mark.parametrize('method',['__exit__','receipt'])
def test_shared_segment_uses_original_kernel_cleanup_after_method_alias_drift(shared,monkeypatch,method):
    window=shared.operation();window.__enter__();window.prepare('training_ub',0)
    calls=[]
    monkeypatch.setattr(shared.tiny.m.PhaseDependencyValidationOperation,method,
        lambda *args:calls.append('forged kernel method'))
    with pytest.raises(ValueError,match='definition-time'):window.close()
    assert not calls and not shared.tiny.state['live']
    assert shared.tiny.m._CLEANUP_DIAGNOSTICS()['active_operations']==0
    # A retired runtime cannot issue a public clean receipt.
    with pytest.raises(ValueError,match='definition-time'):window.receipt()
    reference=ref(window);del window;gc.collect();assert reference() is None


@pytest.mark.parametrize('tiny',['separate'],indirect=True)
def test_dynamic_root_junction_to_static_inventory_is_refused(shared,tmp_path):
    root=tmp_path/'dynamic_alias_non_authoritative'
    result=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(root),str(shared.tiny.data.parent)],
        capture_output=True,timeout=5)
    assert result.returncode==0,result.stderr.decode(errors='replace')
    window=shared.operation(root=root)
    with pytest.raises(ValueError,match='reparse|plain|directory'):window.__enter__()
    receipt=window.receipt()
    assert receipt['closed'] and receipt['phase_kernel_receipt']['all_handles_closed']
    assert not receipt['lifecycle_complete'] and not shared.tiny.state['live']


@pytest.mark.parametrize('tiny',['separate'],indirect=True)
def test_dynamic_root_replaced_by_junction_at_exit_refuses_completion_and_preserves_bytes(shared,tmp_path):
    root=tmp_path/'dynamic_non_authoritative';window=shared.operation(root=root)
    with pytest.raises(ValueError,match='reparse|plain|directory'):
        with window:
            window.prepare('training_ub',0)
            result=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(root),str(shared.tiny.data.parent)],
                capture_output=True,timeout=5)
            assert result.returncode==0,result.stderr.decode(errors='replace')
    assert shared.tiny.data.read_bytes()==b'unit phase data'
    receipt=window.receipt()
    assert receipt['closed'] and not receipt['lifecycle_complete']
    assert receipt['phase_kernel_receipt']['all_handles_closed'] and not shared.tiny.state['live']
