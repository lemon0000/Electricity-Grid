"""Independent canonical binding science differential; no owner or execution."""
from dataclasses import asdict
import json

import pytest

from experiments import h1_phase_manifest_binding_development_v3 as m
from tests.test_h1_selector_configuration_development_v1 import configuration


def archive():return m.ArchiveCapacityDeclaration(576,2**20,576*2**20,0)


def test_stable_phase3_binding_matches_canonical_science_and_closed_execution(tmp_path):
    c=configuration();a=archive()
    old=m.prior.prepare('training_ub',0,c,a)
    first=m.prepare('training_ub',0,c,a);second=m.prepare('training_ub',0,c,a)
    assert first.audit_payload==second.audit_payload and first.audit_identity==second.audit_identity
    assert first.audit_identity==m.io.digest(first.audit_payload)
    current=json.loads(first.audit_payload);previous=json.loads(old.audit_payload)
    changed={'schema','implementation_sha256','dependency_verifier','observation_schedule','per_call_physical_freshness'}
    assert m.owner.encode({k:v for k,v in current.items() if k not in changed})==m.owner.encode(
        {k:v for k,v in previous.items() if k not in changed})
    assert m.owner.encode(asdict(first.manifest))==m.owner.encode(asdict(old.manifest))
    assert current['dependency_verifier']['dependency_inventory_sha256']==previous['dependency_verifier']['dependency_inventory_sha256']
    assert current['dependency_verifier']['predecessor_group_sha256']==previous['dependency_verifier']['predecessor_group_sha256']
    assert current['dependency_verifier']['per_call_physical_freshness'] is False
    assert 'fresh_at_return_only' not in current['dependency_verifier']
    assert 'phase_window_receipt' not in current
    for value in (first,second):
        execution=json.loads(value.execution_receipt_payload)
        assert execution['stable_audit_sha256']==value.audit_identity
        receipt=execution['phase_window_receipt']
        assert receipt['lifecycle_complete'] and receipt['all_handles_closed']
        assert receipt['immutable_bytes_cleared'] and receipt['original_guard_released']
        assert receipt['maximum_prepares']==receipt['completed_prepares']==2
        assert execution['consumer_bound'] is False and execution['canonical_independent_differential_verified'] is False
        assert all(execution[key] is False and current[key] is False for key in m.FLAGS)
    cleanup=m.observation._CLEANUP_DIAGNOSTICS()
    assert cleanup['active_operations']==0 and cleanup['abandoned_pending_operations']==0
    (tmp_path/'phase_binding3_differential.json').write_text(json.dumps(dict(
        canonical_audit_sha256=old.audit_identity,stable_audit_sha256=first.audit_identity,
        canonical_manifest_sha256=m.io.digest(m.owner.encode(asdict(old.manifest))),
        new_manifest_sha256=m.io.digest(m.owner.encode(asdict(first.manifest))),
        stable_across_two_windows=True,independent_scientific_differential_verified=True,
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
