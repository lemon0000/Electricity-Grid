"""Parent4 filesystem and live completion tests with explicit fake transport.

Use real successor Parent methods, leases, worker and replay. Source rows,
native solvers and lifecycle transport are test seams; no Job/native authority.
"""
import json
from dataclasses import dataclass, fields
from hashlib import sha256
from time import perf_counter

import pytest

from experiments import h1_selector_parent_controller_development_v4 as parent
from tests import test_h1_selector_parent_controller_development_v1 as predecessor
from tests.test_h1_hour0_persistence_faults_development_v2 import (
    case,context,setup as base_setup,legacy_setup,no_solver)
from tests.h1_hour0_synthetic_harness_v4 import harness
from tests.test_h1_selector_parent_controller_development_v1 import (
    sequence_factory,
    test_create_persists_binding_before_worker_and_close_preserves_files,
    test_reference_parent_issues_only_after_joint_terminal_and_replays,
    test_failed_attempt_never_issues_completion_or_retries,
    test_preflight_invalid_budget_has_no_parent_side_effects,
    test_actual_requires_live_reference_and_closing_reference_invalidates_completion,
    test_constructor_write_failure_preserves_partial_root_and_rejects_retry,
    test_run_write_failure_is_terminal_even_after_terminal_publication,
    test_same_byte_archive_replacement_invalidates_live_completion,
    test_captured_cleanup_survives_callback_replacement)


@pytest.fixture(autouse=True)
def route_successor(monkeypatch):
    monkeypatch.setattr(predecessor,'canonical',parent)


@dataclass(frozen=True)
class ExplicitSyntheticPreparedCurrent:
    frame: object
    source_origin: object
    source_action: object


@pytest.fixture
def setup(base_setup):
    # Keep the old synthetic values but use literal typed fields, as the
    # successor deliberately rejects SimpleNamespace source projections.
    source=parent.worker.snapshot.phase.source
    for hour,current in tuple(base_setup.currents.items()):
        values={field.name:getattr(current,field.name) for field in fields(current)}
        values['prepared_current']=ExplicitSyntheticPreparedCurrent(**vars(current.prepared_current))
        base_setup.currents[hour]=source.normal._owned(source.ExactSourceCurrent,**values)
    return base_setup


def assert_receipts(module,owner,expected):
    receipts=module._WINDOWS.receipts(owner)
    assert [item['kind'] for item in receipts]==expected
    assert receipts==[json.loads(raw) for raw in owner._source_windows]
    for item,raw in zip(receipts,owner._source_windows,strict=True):
        assert type(raw) is bytes and module.io.encode(item)==raw
        assert item['parent_implementation']==owner._own
        route=item['source_route_declaration']
        assert sha256(module.io.encode(route)).hexdigest()==item['source_route_sha256']
        assert item['complete'] and item['source_window_cache_cleared']
        assert item['original_source_prepares']==2
        assert not item['source_reuse_across_job_or_callback_boundary']
    return receipts


def test_actual_lifecycle_clears_each_external_boundary_and_binds_plain_receipts(harness):
    h=harness;m=h.module;c=h.context
    started=perf_counter()
    def trace(stage):
        print(json.dumps(dict(stage=stage,elapsed_seconds=perf_counter()-started)),flush=True)
    trace('reference_construct_start')
    with m.Parent(h.root,h.raw,**h.options) as ref:
        trace('reference_prepared')
        stages=[]
        def ref_probe(stage):
            m._WINDOWS.assert_idle(ref);stages.append(stage);trace('reference_'+stage)
        h.faults['boundary_probe']=ref_probe
        reference=ref.run()
        trace('reference_complete')
        assert stages==['job_entry','release_return','quiet_return','job_return']
        expected=['construct_prepare','construct_finish','run_pre','run_release','run_quiet','run_post']
        assert_receipts(m,ref,expected)
        raw=m.worker.snapshot.capture_actual(c.owner,c.config,max_archive_bytes=c.cap,lane_id='joint',
            reference_root=reference.scientific_root,
            reference_terminal_sha256=reference.scientific_terminal_sha256,
            reference_request_sha256=reference.scientific_request_sha256,
            reference_max_archive_bytes=reference.max_archive_bytes)
        root=h.root.parent/'actual_parent_non_authoritative'
        with m.Parent(root,raw,**h.options,reference_owner=ref,reference_completion=reference) as actual:
            trace('actual_prepared')
            stages.clear()
            def probe(stage):
                m._WINDOWS.assert_idle(actual);m._WINDOWS.assert_idle(ref)
                stages.append(stage);trace('actual_'+stage)
            h.faults['boundary_probe']=probe
            completed=actual.run()
            trace('actual_complete')
            assert stages==['job_entry','release_return','quiet_return','job_return']
            actual.validate_completion(completed)
            receipts=assert_receipts(m,actual,expected+['validate'])
            assert [item['logical_source_requests'] for item in receipts]==[4,20,28,28,32,76,48]
            assert all(item['role']=='actual' for item in receipts)
            windows=[item['reference_window'] for item in receipts]
            assert windows[:2]==[None,None]
            assert [item['logical_reference_inspects'] for item in windows[2:]]==[12,12,16,28,16]
            for item in windows[2:]:
                assert item['canonical_reference_sequence']
                assert item['original_reference_inspects']==2
                assert item['cache_cleared'] and item['bookend_only_freshness']
                assert not item['per_call_fresh_at_return']
                assert not item['actual_output_inspection_cached']
            m._WINDOWS.assert_idle(actual)
    trace('all_closed')


@pytest.mark.parametrize('fault',['before_worker','duplicate_release','duplicate_quiet',
    'observation_mismatch','inspection_mismatch'])
def test_actual_failed_transport_releases_reference_and_window(harness,fault):
    h=harness;m=h.module;c=h.context
    with m.Parent(h.root,h.raw,**h.options) as ref:
        receipt=ref.run()
        raw=m.worker.snapshot.capture_actual(c.owner,c.config,max_archive_bytes=c.cap,lane_id='joint',
            reference_root=receipt.scientific_root,reference_terminal_sha256=receipt.scientific_terminal_sha256,
            reference_request_sha256=receipt.scientific_request_sha256,
            reference_max_archive_bytes=receipt.max_archive_bytes)
        with m.Parent(h.root.parent/'failed_actual_non_authoritative',raw,**h.options,
                reference_owner=ref,reference_completion=receipt) as owner:
            h.faults[fault]=True
            with pytest.raises((ValueError,RuntimeError)):owner.run()
            m._WINDOWS.assert_idle(owner);m._WINDOWS.assert_idle(ref)
            assert owner._state=='failed' and owner._issued is None and not owner._reference_held
            assert not owner._guard.locked() and not ref._guard.locked()
            ref.validate_completion(receipt)
            assert (owner.root/'execution.lock').is_file()
        assert (owner.root/'execution.lock').read_bytes()==b'0'
