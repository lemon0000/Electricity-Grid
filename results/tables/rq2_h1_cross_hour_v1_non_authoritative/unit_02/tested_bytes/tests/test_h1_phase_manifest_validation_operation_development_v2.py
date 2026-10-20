"""Shared static phase projection regressions and actual handle/write boundaries."""
from dataclasses import asdict
import gc
import json
from pathlib import Path
from threading import Thread
from weakref import ref

import pytest

from experiments import h1_phase_manifest_validation_operation_development_v2 as m
from tests.test_h1_selector_configuration_development_v1 import configuration


def operation(root,*,plan=(('training_ub',0),),projects=8,checks=32):
    return m.PhaseManifestValidationOperation(plan=plan,configuration=configuration(),
        archive=m.binding.ArchiveCapacityDeclaration(576,2**20,576*2**20,0),
        dynamic_roots=(root,),maximum_projects=projects,maximum_checks=checks,diagnostic_only=True)


def test_one_seed_projects_siblings_with_stable_predecessor_data_and_real_disjoint_writes(tmp_path):
    root=tmp_path/'journal_non_authoritative';observed=[]
    c=configuration();a=m.binding.ArchiveCapacityDeclaration(576,2**20,576*2**20,0)
    expected={ordinal:m.binding.prepare('training_ub',ordinal,c,a) for ordinal in (0,101)}
    with operation(root) as window:
        fingerprint=window.fingerprint()
        root.mkdir();(root/'header.json').write_bytes(b'{"unit_only":true}')
        for ordinal in (0,101,0,101):
            current=window.prepare('training_ub',ordinal);observed.append(current.audit_identity)
            assert current.audit_payload==expected[ordinal].audit_payload
            assert m.binding.owner.encode(asdict(current.manifest))==m.binding.owner.encode(asdict(expected[ordinal].manifest))
            assert json.loads(current.execution_receipt_payload)['closed'] is False
            assert json.loads(current.execution_receipt_payload)['consumer_bound'] is False
        audit=json.loads(expected[0].audit_payload)
        assert fingerprint==(audit['group']['implementation_sha256'],audit['implementation_sha256'],
            audit['dependency_verifier']['verifier_implementation_sha256'],
            audit['dependency_verifier']['dependency_inventory_sha256'])
    receipt=window.receipt()
    assert receipt['lifecycle_complete'] and receipt['closed']
    assert receipt['cached_science_cleared'] and receipt['original_guard_released']
    assert receipt['kernel_request_attempts']==receipt['kernel_payloads_returned']==1
    assert receipt['project_calls']==4 and receipt['project_cache_hits']==2
    assert receipt['phase_kernel_receipt']['completed_prepares']==1
    assert receipt['phase_kernel_receipt']['all_handles_closed']
    assert receipt['disjoint_checks']==2
    assert (root/'header.json').read_bytes()==b'{"unit_only":true}'
    with pytest.raises(ValueError,match='active'):window.prepare('training_ub',0)
    cleanup=m.kernel._CLEANUP_DIAGNOSTICS()
    assert cleanup['active_operations']==0 and cleanup['abandoned_pending_operations']==0
    (tmp_path/'shared_phase_observation.json').write_text(json.dumps(dict(
        observation=receipt,stable_audit_sha256=observed,predecessor_projection_differential_verified=True,
        independent_scientific_algorithm_verified=False,formal_result=False,resource_admission=False),indent=2),encoding='utf-8')


def test_nonzero_seed_and_two_distinct_groups_have_same_dependency_fingerprint(tmp_path):
    root=tmp_path/'journal_non_authoritative'
    with operation(root,plan=(('training_ub',101),('training_ub',11832352))) as window:
        first=window.prepare('training_ub',0);other=window.prepare('training_ub',11832352)
        a=json.loads(first.audit_payload);b=json.loads(other.audit_payload)
        assert a['group']['group_identity']!=b['group']['group_identity']
        assert a['group']['implementation_sha256']==b['group']['implementation_sha256']==window.fingerprint()[0]
        assert a['dependency_verifier']['dependency_inventory_sha256']==b['dependency_verifier']['dependency_inventory_sha256']
        assert window.fingerprint()[1]==a['implementation_sha256']==b['implementation_sha256']
    assert window.receipt()['lifecycle_complete']


def test_intersecting_dynamic_root_is_refused_without_resource_leak(tmp_path):
    root=Path(m.kernel.predecessor.prior.ROOT)/'experiments'
    window=operation(root)
    with pytest.raises(ValueError,match='intersects'):window.__enter__()
    receipt=window.receipt()
    assert receipt['closed'] and not receipt['lifecycle_complete']
    assert receipt['original_guard_released'] and receipt['phase_kernel_receipt']['all_handles_closed']


@pytest.mark.parametrize('mode',['unknown_group','project_bound','body','reentry'])
def test_failed_segment_preserves_primary_and_releases_kernel(tmp_path,mode):
    window=operation(tmp_path/'journal_non_authoritative',projects=1)
    primary=RuntimeError('shared segment primary')
    with pytest.raises((ValueError,RuntimeError)) as caught:
        with window:
            if mode=='unknown_group':window.prepare('training_ub',1)
            elif mode=='reentry':window.__enter__()
            else:
                window.prepare('training_ub',0)
                if mode=='body':raise primary
                window.prepare('training_ub',101)
    if mode=='body':assert caught.value is primary
    receipt=window.receipt()
    assert receipt['closed'] and not receipt['lifecycle_complete'] and receipt['first_failure'] is not None
    assert receipt['phase_kernel_receipt']['all_handles_closed'] and receipt['original_guard_released']
    assert receipt['cached_science_cleared']


def test_foreign_thread_cannot_poison_owner_or_use_fingerprint(tmp_path):
    window=operation(tmp_path/'journal_non_authoritative');errors=[]
    with window:
        def foreign():
            for function,args in ((window.fingerprint,()),(window.prepare,('training_ub',0)),(window.close,())):
                try:function(*args)
                except ValueError as error:errors.append(str(error))
        thread=Thread(target=foreign);thread.start();thread.join(timeout=5)
        assert not thread.is_alive() and len(errors)==3
        assert window.receipt()['first_failure'] is None
        window.prepare('training_ub',0)
    assert window.receipt()['lifecycle_complete']


def test_abandonment_reaches_kernel_finalizer_and_clears_cleanup_registry(tmp_path):
    window=operation(tmp_path/'journal_non_authoritative');window.__enter__()
    assert m.kernel._CLEANUP_DIAGNOSTICS()['active_operations']==1
    reference=ref(window);del window;gc.collect()
    assert reference() is None
    cleanup=m.kernel._CLEANUP_DIAGNOSTICS()
    assert cleanup['active_operations']==0 and cleanup['abandoned_pending_operations']==0
