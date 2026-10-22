"""Bind the development checkpoint; this creates no seal or run authority."""
from hashlib import sha256
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def load(path):
    return json.loads(Path(path).read_bytes())


def pin(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def main():
    unit = load(HERE / 'model_units_02/terminal.json')
    oracle = load(HERE / 'oracle_01/oracle_terminal.json')
    short = load(HERE / 'short_comparison_01/comparison_terminal.json')
    state = load(HERE / 'formal_preparation_state_v4.json')
    alias = load(HERE / 'probe_02/probe_terminal.json')
    runtime = load(HERE / 'runtime_probe_01/probe_terminal.json')
    postcheck = load(HERE / 'postcheck_v1.json')
    assert unit['junit'] == dict(tests=171, failures=0, errors=0, skipped=0, accepted=True)
    unit_time = re.search(r'171 passed in ([0-9.]+)s', (HERE / 'model_units_02/stdout.txt').read_text(encoding='utf-8'))
    assert unit_time is not None
    assert alias['exit_code'] == runtime['exit_code'] == oracle['exit_code'] == short['exit_code'] == 0
    assert alias['named_dependency_fault_rejected_by_both'] is True
    assert runtime['named_runtime_distribution_fault_rejected_by_both'] is True
    assert all(row['outcome'] == 'rejected' and not row['window']['instrumentation_errors']
               for packet in (alias, runtime) for row in packet['observations'])
    assert oracle['saved_identity_bound_science_reconstruction_equal'] is True
    assert oracle['old_raw_science_bytes_directly_read'] is False
    assert oracle['independent_scientific_implementation'] is False and len(oracle['validator_faults']) == 21
    assert [row['implementation'] for row in short['calls']] == ['old', 'new']
    assert all(row['equal_to_old_oracle'] is True for row in short['calls'])
    assert short['calls'][0]['scientific_summaries'] == short['calls'][1]['scientific_summaries']
    assert postcheck['saved_case_files'] == 465 and postcheck['saved_owned_files'] == 444
    assert postcheck['saved_case_and_owned_sha256_unchanged'] is True
    assert len(state['gates']) == 16 and not any(g['complete'] for g in state['gates'])
    assert (HERE / 'preseal_review_summary.json').is_file()
    excluded = {'development_acceptance_v1.json', 'final_verification.json'}
    files = [p for p in HERE.rglob('*') if p.is_file() and p.relative_to(HERE).as_posix() not in excluded]
    extras = ['agent.md', 'AGENTS.md', 'docs/plan/科研项目执行步骤.md', 'docs/model_spec/blocker_register.md',
        'configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml',
        'docs/model_spec/rq2_finite_mechanism_protocol_candidate_v2.md',
        'experiments/h1_constructor_inspection_capture_development_v1.py',
        'experiments/h1_phase_historical_batch_development_v2.py',
        'experiments/h1_phase_exact_source_batch_development_v2.py',
        'experiments/h1_constructor_source_batch_validation_development_v1.py',
        'tests/test_h1_constructor_inspection_capture_development_v1.py',
        'experiments/h1_cross_hour_owner_development_v2.py',
        'experiments/h1_phase_boundary_budget_development_v1.py',
        'results/tables/rq2_h1_phase_boundary_v1_non_authoritative/budget_audit_v1.json',
        'results/tables/rq2_h1_constructor_inspection_v2_non_authoritative/final_verification.json',
        'results/tables/rq2_h1_constructor_inspection_v2_non_authoritative/development_acceptance_v1.json',
        'results/tables/rq2_h1_constructor_inspection_v2_non_authoritative/compare_short_saved_v1.py',
        'results/tables/rq2_h1_source_replay_cost_v1_non_authoritative/final_verification.json',
        'results/tables/rq2_h1_source_replay_cost_v1_non_authoritative/call_dag_and_work_units.json',
    ]
    files += [REPO / name for name in extras]
    result = dict(status='DRAFT_NONAUTHORITATIVE', task_risk='R3', unique_writer='root',
        objective='complete_all_preparations_before_formal_experiment', objective_complete=False,
        scope='named_constructor_dependency_window_fix_and_revalidated_saved_source_path',
        latest_unit=unit['junit'], latest_unit_pytest_seconds=float(unit_time.group(1)),
        named_dependency_alias_window_rejected=alias['named_dependency_fault_rejected_by_both'],
        named_simulated_external_metadata_window_rejected=runtime['named_runtime_distribution_fault_rejected_by_both'],
        saved_H3_scientific_identity_reconstruction=dict(seconds=oracle['successor_batch_seconds'],
            direct_old_raw_science_read=False, independently_implemented_oracle=False,
            shared_saved_manifest_resolver=oracle['shared_saved_manifest_pin_resolver'],
            one_field_projection_standin=oracle['one_field_packet_projection_standin'],
            auxiliary_data_faults=len(oracle['validator_faults'])),
        H1_fixed_order_net_observation=dict(order=['old', 'new'], repetitions_per_implementation=1,
            seconds=[row['elapsed_seconds'] for row in short['calls']],
            science_summary_equal=short['calls'][0]['scientific_summaries'] == short['calls'][1]['scientific_summaries'],
            production_or_192h_speedup_established=False),
        source_successor_adopted=False, owner_integration_performed=False,
        saved_case_files=postcheck['saved_case_files'], saved_owned_files=postcheck['saved_owned_files'],
        saved_case_and_owned_sha256_unchanged=postcheck['saved_case_and_owned_sha256_unchanged'],
        cleanup_scope='only captured Reader/ReadView and owner fields in the two named fault windows',
        full_actual_source_fault_matrix_verified=False, complete_dynamic_closure_proved=False,
        unobserved_between_bookends_ABA_covered=False, arbitrary_runtime_rewrite_cleanup_proved=False,
        total_192h_wall_admission_seconds=None, peak_rss_admission_bytes=None, total_storage_admission_bytes=None,
        latest_preparation_inventory=str(HERE / 'formal_preparation_state_v4.json'), open_preparation_gates=16,
        overall_performance_review_complete=False, long_connected_launch_admitted=False,
        real_phase_terminal_reopen_verified=False, full_192_hour_execution_verified=False,
        typed_followup_right_censor_terminal_verified=False, writer_rehydration_verified=False,
        persistent_atomic_live_verified=False, crash_durability_verified=False,
        resource_admission=False, native_execution_authorized=False, formal_execution_ready=False,
        sealed=False, official_review_pass=False, formal_result=False,
        new_normal_jobs=0, real_native_calls=0,
        bindings={str(p): pin(p) for p in sorted(set(files))})
    with (HERE / 'development_acceptance_v1.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(bindings=len(result['bindings']), objective_complete=False,
        overall_performance_review_complete=False, formal_result=False)))


if __name__ == '__main__':
    main()
