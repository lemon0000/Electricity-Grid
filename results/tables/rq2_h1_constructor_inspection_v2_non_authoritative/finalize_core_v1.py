"""Bind current draft evidence. No production seal, receipt or authority."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def load(path):
    return json.loads(Path(path).read_bytes())


def main():
    output = HERE/'development_acceptance_v1.json'
    if output.exists():
        raise ValueError('fresh development core required')
    unit = load(HERE/'unit_04/terminal.json')
    oracle = load(HERE/'oracle_01/oracle_terminal.json')
    comparison = load(HERE/'short_comparison_01/comparison_terminal.json')
    before, after = [row['elapsed_seconds'] for row in comparison['calls']]
    assert unit['junit']['accepted'] and oracle['exit_code'] == comparison['exit_code'] == 0
    paths = {p for p in HERE.rglob('*') if p.is_file()}
    paths.update(REPO/relative for relative in (
        'experiments/h1_constructor_inspection_capture_development_v1.py',
        'experiments/h1_phase_historical_batch_development_v2.py',
        'experiments/h1_phase_exact_source_batch_development_v2.py',
        'experiments/h1_constructor_source_batch_validation_development_v1.py',
        'tests/test_h1_constructor_inspection_capture_development_v1.py',
        'experiments/h1_cross_hour_owner_development_v2.py',
        'experiments/h1_phase_exact_source_batch_development_v1.py',
        'experiments/h1_phase_historical_batch_development_v1.py',
        'docs/plan/科研项目执行步骤.md', 'docs/model_spec/blocker_register.md',
        'agent.md', 'configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml',
        'docs/model_spec/rq2_finite_mechanism_protocol_candidate_v2.md',
        'results/tables/rq2_h1_source_replay_cost_v1_non_authoritative/final_verification.json',
        'results/tables/rq2_v2_obligation_manifest_v1_non_authoritative/obligation_manifest_v2_final.json',
        'results/tables/rq2_v2_cfe_exclusion_v1_non_authoritative/cell_exclusion_audit_v2_final.json',
        'results/tables/rq2_finite_enrollment_support_v1_non_authoritative/coverage_168_24_verified.json'))
    bindings = {str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    result = dict(status='DRAFT_NONAUTHORITATIVE', task_risk='R3', unique_writer='root',
        objective='complete_all_formal_experiment_preparations', objective_complete=False,
        scope='constructor_inspection_successor_limited_development_and_budget_evidence',
        latest_unit=dict(tests=110, pytest_seconds=3.03, outer_seconds=unit['outer_seconds'],
            full_actual_source_fault_matrix_verified=False),
        saved_scientific_reconstruction=dict(H=3, M=5, independent_readers=2, parent_traversals=2,
            seconds=oracle['successor_batch_seconds'], saved_identity_bound=True,
            canonical_science_reconstructed_with_original_join_projection=True,
            direct_predecessor_raw_science_payload_read=False, independently_implemented_oracle=False,
            auxiliary_data_faults=21, interpretation=str(HERE/'oracle_01_interpretation.json')),
        net_path_observation=dict(H=1, M=5, order=['old','new'], repetitions_per_implementation=1,
            old_seconds=before, successor_seconds=after, observed_seconds_reduced=before-after,
            observed_fraction_reduced=(before-after)/before, production_speedup_established=False,
            representative_192h_cost_established=False, static_identity_memo=False,
            shared_saved_manifest_resolver_seam_retained=True, real_manifest_sources_reaudited=False),
        failed_attempt=dict(path=str(HERE/'comparison_01'), child_exit_code=15,
            reason='no_progress_limit_before_first_full_batch', completed_batches=0,
            scientific_or_performance_comparison_supported=False,
            separate_after_postcheck=str(HERE/'comparison_01_failed_postcheck.json')),
        source_cost_counts_remain_conditional=True, source_successor_implemented=True,
        source_successor_adopted=False, owner_integration_performed=False,
        saved_case_files=465, saved_owned_files=444, saved_case_sha256_unchanged=True,
        latest_preparation_inventory=str(HERE/'formal_preparation_state_v3.json'),
        inventory_scope='current_reconciled_draft_not_exhaustive_authoritative_acceptance',
        actual_source_file_faults_complete=False, complete_dynamic_closure_proved=False,
        unobserved_ABA_covered=False, arbitrary_runtime_rewrite_cleanup_proved=False,
        overall_performance_review_complete=False, long_connected_launch_admitted=False,
        total_192h_wall_admission_seconds=None, peak_rss_admission_bytes=None, total_storage_admission_bytes=None,
        full_192_hour_execution_verified=False, real_phase_terminal_reopen_verified=False,
        typed_followup_right_censor_terminal_verified=False, writer_rehydration_verified=False,
        persistent_atomic_live_verified=False, crash_durability_verified=False,
        resource_admission=False, native_execution_authorized=False,
        formal_execution_ready=False, formal_result=False, sealed=False, official_review_pass=False,
        new_normal_jobs=0, real_native_calls=0, bindings=bindings)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    assert all(sha256(Path(p).read_bytes()).hexdigest() == value for p,value in bindings.items())
    print(json.dumps(dict(core=str(output), sha256=sha256(output.read_bytes()).hexdigest(),
        bindings=len(bindings), observed_fraction_reduced=result['net_path_observation']['observed_fraction_reduced'])))


if __name__ == '__main__':
    main()
