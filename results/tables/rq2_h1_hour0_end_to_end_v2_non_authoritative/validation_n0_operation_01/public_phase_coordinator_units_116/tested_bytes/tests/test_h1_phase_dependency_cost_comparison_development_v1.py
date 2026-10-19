"""Matched unprofiled detached-data cost observations, never whole-chain timing."""
from hashlib import sha256
import json
from time import perf_counter

from experiments import h1_phase_dependency_validation_operation_development_v1 as m


def test_six_and_sixteen_requests_compare_full_window_cost_in_both_orders(tmp_path):
    canonical=m.predecessor.prepare_group('training_ub',0)
    expected=m.predecessor.io.encode(canonical)
    science_keys=('predecessor_group','dependency_sha256','observed_file_count',
        'observed_total_bytes','verifier_sha256','verifier_implementation','verifier_implementation_sha256')
    expected_science=m.predecessor.io.encode({key:canonical[key] for key in science_keys})
    expected_sha=sha256(expected).hexdigest();rows=[]
    for count in (6,16):
        for role in ('canonical','window','window','canonical'):
            start=perf_counter();receipt=None
            if role=='canonical':
                for _ in range(count):
                    raw=m.predecessor.io.encode(m.predecessor.prepare_group('training_ub',0))
                    assert sha256(raw).hexdigest()==expected_sha
            else:
                operation=m.PhaseDependencyValidationOperation(
                    plan=(('training_ub',0),)*count,diagnostic_only=True)
                with operation:
                    for _ in range(count):
                        report=json.loads(operation.prepare_group('training_ub',0))
                        assert report['execution']['legacy_shape_reference_sha256']==expected_sha
                        assert m.predecessor.io.encode(report['scientific_projection'])==expected_science
                        assert report['canonical_equivalence_verified'] is False
                        assert report['fresh_at_return_only'] is False
                receipt=operation.receipt()
                assert receipt['lifecycle_complete'] and receipt['all_handles_closed']
                assert receipt['immutable_bytes_cleared'] and receipt['original_guard_released']
                cleanup=m._CLEANUP_DIAGNOSTICS()
                assert cleanup['active_operations']==0 and cleanup['abandoned_pending_operations']==0
            elapsed=perf_counter()-start
            row=dict(requests=count,role=role,elapsed_seconds=elapsed,
                includes_entry_exit_and_cleanup=role=='window',closed_receipt=receipt)
            rows.append(row)
            print(json.dumps({key:value for key,value in row.items() if key!='closed_receipt'}),flush=True)
    comparisons=[]
    for count in (6,16):
        old=[r['elapsed_seconds'] for r in rows if r['requests']==count and r['role']=='canonical']
        new=[r['elapsed_seconds'] for r in rows if r['requests']==count and r['role']=='window']
        comparisons.append(dict(requests=count,canonical_seconds=old,window_seconds=new,
            mean_canonical_seconds=sum(old)/len(old),mean_window_seconds=sum(new)/len(new),
            mean_window_over_canonical=sum(new)/sum(old),
            measured_total_reduction_fraction=1-sum(new)/sum(old)))
    (tmp_path/'phase_dependency_unprofiled_comparison.json').write_text(json.dumps(dict(
        status='BOUNDED_COST_COMPARISON_NONAUTHORITATIVE',order='canonical-window-window-canonical',
        profiler=False,canonical_reference_sha256=expected_sha,observations=rows,comparisons=comparisons,
        scope='same process and ordinary code/metadata entry; detached phase data only; window acquisition and cleanup included',
        whole_workflow_performance_review_complete=False,full_optimized_workflow_accepted=False,
        formal_result=False,resource_admission=False,native_execution_authorized=False),indent=2),encoding='utf-8')
