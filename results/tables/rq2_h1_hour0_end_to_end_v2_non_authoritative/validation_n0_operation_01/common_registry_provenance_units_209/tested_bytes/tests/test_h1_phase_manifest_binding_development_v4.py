"""Predecessor-helper projection regression and composition faults; no owner/Job."""
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType

import pytest

import experiments
from experiments import h1_phase_manifest_binding_development_v4 as m
from tests.test_h1_phase_dependency_window_faults_development_v2 import tiny
from tests.test_h1_selector_configuration_development_v1 import configuration


def archive():return m.ArchiveCapacityDeclaration(576,2**20,576*2**20,0)


@pytest.mark.parametrize('ordinal',[0,101,11832352])
def test_stable_phase3_binding_matches_predecessor_science_and_closed_execution(tmp_path,ordinal):
    c=configuration();a=archive()
    old=m.prior.prepare('training_ub',ordinal,c,a)
    first=m.prepare('training_ub',ordinal,c,a);second=m.prepare('training_ub',ordinal,c,a)
    assert first.audit_payload==second.audit_payload and first.audit_identity==second.audit_identity
    assert first.audit_identity==m.io.digest(first.audit_payload)
    current=json.loads(first.audit_payload);previous=json.loads(old.audit_payload)
    changed={'schema','implementation_sha256','dependency_verifier','observation_schedule','per_call_physical_freshness'}
    assert m.owner.encode({k:v for k,v in current.items() if k not in changed})==m.owner.encode(
        {k:v for k,v in previous.items() if k not in changed})
    assert m.owner.encode(asdict(first.manifest))==m.owner.encode(asdict(old.manifest))
    assert set(current)==set(previous)|{'per_call_physical_freshness','observation_schedule'}
    flags={'executable_manifest','resource_admission','formal_execution_ready','formal_result',
        'native_execution_authorized','owner_consumption_authorized'}
    assert set(m.FLAGS)==flags
    evidence=current['dependency_verifier'];prior_evidence=previous['dependency_verifier']
    preserved={'verifier_sha256','verifier_implementation','verifier_implementation_sha256',
        'observed_file_count','observed_total_bytes','dependency_inventory_sha256','predecessor_group_sha256'}
    assert set(evidence)==preserved|flags|{'schema','active_implementation','observation_schedule',
        'per_call_physical_freshness','canonical_equivalence_verified','between_bookend_ABA_covered','detached_data'}
    for key in preserved:assert m.owner.encode(evidence[key])==m.owner.encode(prior_evidence[key])
    assert evidence['schema']==m.observation.SCHEMA
    assert evidence['active_implementation']==m.observation.implementation_identity()
    assert evidence['observation_schedule']=='held_entry_exit' and evidence['detached_data'] is True
    assert all(evidence[key] is False for key in flags|{'per_call_physical_freshness',
        'canonical_equivalence_verified','between_bookend_ABA_covered'})
    assert 'phase_window_receipt' not in current
    for value in (first,second):
        execution=json.loads(value.execution_receipt_payload)
        assert set(execution)==flags|{'schema','active_implementation','stable_audit_sha256',
            'phase_window_receipt','detached_data','consumer_bound','canonical_independent_differential_verified'}
        assert execution['stable_audit_sha256']==value.audit_identity
        receipt=execution['phase_window_receipt']
        assert receipt['lifecycle_complete'] and receipt['all_handles_closed']
        assert receipt['immutable_bytes_cleared'] and receipt['original_guard_released']
        assert receipt['maximum_prepares']==receipt['completed_prepares']==2
        assert execution['consumer_bound'] is False and execution['canonical_independent_differential_verified'] is False
        assert all(execution[key] is False and current[key] is False for key in m.FLAGS)
    classifications={row['classification'] for row in current['arm_classifications']}
    if ordinal==11832352:assert classifications=={'direct_shared_lane','proof_terminal'}
    else:assert classifications=={'direct_shared_lane','pending_separate_B6_planning'}
    cleanup=m.observation._CLEANUP_DIAGNOSTICS()
    assert cleanup['active_operations']==0 and cleanup['abandoned_pending_operations']==0
    (tmp_path/'phase_binding3_differential.json').write_text(json.dumps(dict(
        canonical_audit_sha256=old.audit_identity,stable_audit_sha256=first.audit_identity,
        canonical_manifest_sha256=m.io.digest(m.owner.encode(asdict(old.manifest))),
        new_manifest_sha256=m.io.digest(m.owner.encode(asdict(first.manifest))),
        stable_across_two_windows=True,predecessor_projection_differential_verified=True,
        independent_scientific_algorithm_verified=False,
        new_audit=current,closed_execution=json.loads(first.execution_receipt_payload),
        consumer_bound=False,formal_result=False,resource_admission=False),indent=2),encoding='utf-8')


@pytest.mark.parametrize('family,ordinal',[('holdout',0),('training_ub',True),('training_ub',-1)])
def test_invalid_phase_request_refused(family,ordinal):
    with pytest.raises(ValueError):m.prepare(family,ordinal,configuration(),archive())


@pytest.mark.parametrize('which',['selector','archive'])
def test_exact_declaration_types_required(which):
    c=configuration();a=archive()
    with pytest.raises(ValueError,match='exact typed'):
        m.prepare('training_ub',0,object() if which=='selector' else c,object() if which=='archive' else a)


def load_binding(monkeypatch,tmp_path):
    name='experiments._binding3_fault_'+tmp_path.name
    spec=importlib.util.spec_from_file_location(name,m.__file__)
    value=importlib.util.module_from_spec(spec);monkeypatch.setitem(sys.modules,name,value)
    spec.loader.exec_module(value)
    return value


def test_source_read_descriptor_replacement_is_rejected_before_any_window(tmp_path,monkeypatch):
    fresh=load_binding(monkeypatch,tmp_path)
    with monkeypatch.context() as patch:
        patch.setattr(Path,'read_bytes',lambda self:b'forged source bytes')
        with pytest.raises(ValueError,match='definition-time'):
            fresh.prepare('training_ub',0,configuration(),archive())
    diagnostics=m.observation._CLEANUP_DIAGNOSTICS()
    assert diagnostics['active_operations']==0 and diagnostics['abandoned_pending_operations']==0


@pytest.mark.parametrize('failure',['body','second_projection','exit_read','close_handle'])
def test_binding_composition_failure_preserves_error_and_cleans_real_handles(tiny,tmp_path,monkeypatch,failure):
    # Deliberate pre-definition unit protocol seams, not canonical group evidence.
    class PrimaryFailure(RuntimeError):pass
    primary=PrimaryFailure('binding body primary')
    def lanes(group):
        if failure=='body':raise primary
        return (),[]
    monkeypatch.setattr(m.prior,'_lanes',lanes)
    proxy=ModuleType('experiments._binding3_observation_'+tmp_path.name)
    proxy.__file__=tiny.m.__file__;proxy.__spec__=None;proxy.__loader__=None;proxy.__package__='experiments'
    proxy.PhaseDependencyValidationOperation=lambda **kwargs:tiny.operation(kwargs['plan'])
    proxy.implementation_identity=tiny.m.implementation_identity;proxy.SCHEMA=tiny.m.SCHEMA
    monkeypatch.setitem(sys.modules,proxy.__name__,proxy)
    monkeypatch.setattr(experiments,'h1_phase_dependency_validation_operation_development_v2',proxy)
    def fault(value,index):
        if index!=2:return
        if failure=='second_projection':value['unit_only']='changed between projections'
        elif failure=='exit_read':tiny.state['read_fail']=tiny.state['reads']+1
        elif failure=='close_handle':tiny.state['close_fail']={1}
    tiny.state['on_project']=fault
    fresh=load_binding(monkeypatch,tmp_path)
    expected=PrimaryFailure if failure=='body' else ValueError if failure=='second_projection' else OSError
    with pytest.raises(expected) as caught:fresh.prepare('training_ub',0,configuration(),archive())
    if failure=='body':assert caught.value is primary
    operation=tiny.state['operations'][-1];receipt=operation.receipt()
    if failure=='close_handle':
        assert receipt['state']=='cleanup_pending' and receipt['pending_handles']==1
        assert tiny.m._CLEANUP_DIAGNOSTICS()['active_operations']==1
        operation.retry_cleanup();receipt=operation.receipt()
        assert not receipt['lifecycle_complete']
    assert receipt['all_handles_closed'] and receipt['original_guard_released']
    assert not tiny.state['live']
    diagnostics=tiny.m._CLEANUP_DIAGNOSTICS()
    assert diagnostics['active_operations']==0 and diagnostics['abandoned_pending_operations']==0
