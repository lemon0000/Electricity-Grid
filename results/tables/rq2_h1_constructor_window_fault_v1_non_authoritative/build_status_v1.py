"""Reconcile current narrow evidence with the unchanged full preparation gates."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PRIOR = HERE.parent / 'rq2_h1_constructor_inspection_v2_non_authoritative'
sys.path.insert(0, str(REPO))
from experiments.h1_phase_boundary_budget_development_v1 import schedule, business_history_lower_bound
from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_normal as model


def load(path):
    return json.loads(Path(path).read_bytes())


def pin(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    target = HERE / name
    expected = (json.dumps(value, indent=2)+'\n').encode('utf-8')
    if target.exists():
        current = target.read_bytes()
        if current == expected:
            return
        preserved = [HERE / folder / name for folder in
                     ('status_before_review', 'status_before_idempotence_fix')]
        assert any(p.is_file() and p.read_bytes() == current for p in preserved)
    target.write_bytes(expected)


def main():
    prior_path = PRIOR / 'formal_preparation_state_v3.json'
    previous = load(prior_path)
    assert len(previous['gates']) == 16 and not any(g['complete'] for g in previous['gates'])
    # Preserve existing authority/proof sources; only the two canonical progress
    # documents may have received this scope's recorded insertion.
    for name, expected in previous['bindings'].items():
        path = Path(name)
        candidates = [path]
        try:
            candidates.append(HERE / 'canonical_before' / path.relative_to(REPO))
        except ValueError:
            pass
        assert any(p.is_file() and pin(p) == expected for p in candidates), name
    unit = load(HERE / 'model_units_02/terminal.json')
    alias = load(HERE / 'probe_02/probe_terminal.json')
    runtime = load(HERE / 'runtime_probe_01/probe_terminal.json')
    oracle = load(HERE / 'oracle_01/oracle_terminal.json')
    short = load(HERE / 'short_comparison_01/comparison_terminal.json')
    postcheck = load(HERE / 'postcheck_v1.json')
    outer_sources = [HERE / 'postcheck_v1.json']
    for label, accepted_key in (('probe_02', 'probe_complete'), ('runtime_probe_01', 'probe_complete'),
                                ('oracle_01', 'worker_accepted'), ('short_comparison_01', 'worker_accepted')):
        path = HERE / label / 'terminal.json'
        request_path = HERE / label / 'request.json'
        outer, request = load(path), load(request_path)
        assert outer['exit_code'] == 0 and outer[accepted_key] is True
        assert outer['reason'] is None and not outer.get('error')
        assert outer['changed_sources'] == outer['observed_processes_remaining'] == []
        assert outer['new_normal_jobs'] == outer['real_native_calls'] == 0
        assert outer['source_pins'] == len(request['sources_sha256'])
        assert postcheck['attempts'][label]['terminal_sha256'] == pin(path)
        assert postcheck['attempts'][label]['request_sha256'] == pin(request_path)
        outer_sources += [path, request_path]
    assert unit['junit'] == dict(tests=171, failures=0, errors=0, skipped=0, accepted=True)
    assert alias['exit_code'] == runtime['exit_code'] == oracle['exit_code'] == short['exit_code'] == 0
    assert alias['named_dependency_fault_rejected_by_both']
    assert runtime['named_runtime_distribution_fault_rejected_by_both']
    assert oracle['saved_identity_bound_science_reconstruction_equal']
    assert oracle['old_raw_science_bytes_directly_read'] is False
    assert oracle['independent_scientific_implementation'] is False
    assert len(oracle['validator_faults']) == 21
    assert [row['implementation'] for row in short['calls']] == ['old', 'new']
    assert all(row['equal_to_old_oracle'] for row in short['calls'])
    targets = {}
    for hours in (168, 170, 192):
        row = schedule(hours, terminal=True, public_inspect=True)
        weight = row['reader_prefix_hour_weight']
        readers = row['reader_observations']
        assert readers == 8*hours+10 and weight == 4*hours*hours+10*hours+4
        row.update(
            baseline_source_job_replays=4*weight,
            baseline_toy_M5_stage_replays=20*weight,
            conditional_M232_stage_replays=4*232*weight,
            conditional_unadopted_candidate=dict(
                parent_traversals=readers, parent_prefix_hour_weight=weight,
                source_job_replays=2*weight, toy_M5_stage_replays=10*weight,
                conditional_M232_stage_replays=2*232*weight,
                additional_model_dependency_snapshots=2*readers,
                additional_model_source_file_hashes=2*readers*len(model.SOURCE_DEPENDENCIES),
                additional_distribution_version_queries=2*readers*len(model.RUNTIME_DISTRIBUTIONS),
                additional_platform_version_queries=4*readers,
                guard_scans_inside_additional_model_snapshots=4*readers,
                other_entry_and_post_guard_scan_costs_exhaustively_counted=False,
                dynamic_dependency_closure_complete=False, owner_integrated=False),
            business_history_length_lower_bound_three_always_active_lanes=business_history_lower_bound(hours, 3),
            old_operational_event_cap=32, scientific_business_episode_event_cap=14,
            normal_M232_stage_slots=232*hours,
            counts_exclude_additional_public_historical_snapshot_probes_and_normal_internal_replay=True,
            replay_counts_imply_native_solves=0,
            total_wall_admission_seconds=None, peak_rss_admission_bytes=None,
            total_storage_admission_bytes=None)
        targets[str(hours)] = row
    assert targets['192']['minimum_events'] == 576
    assert targets['192']['baseline_source_job_replays'] == 597520
    assert targets['192']['conditional_unadopted_candidate']['source_job_replays'] == 298760
    budget = dict(status='DRAFT_NONAUTHORITATIVE', target_work_units=targets,
        execution_path='original_v2_owner_with_terminal_reopen_constructor_and_public_inspect',
        source_successor_adopted=False,
        observed_costs=dict(H1_fixed_order=['old', 'new'], repetitions_per_implementation=1,
            H1_batch_seconds=[row['elapsed_seconds'] for row in short['calls']],
            H3_new_batch_seconds=oracle['successor_batch_seconds'],
            static_identity_memo=False, shared_saved_manifest_resolver=True,
            real_manifest_sources_reaudited=False, production_speedup_established=False),
        stage_coverage=[
            dict(stage='enrollment_and_genesis', evidence='legacy bound 3h plus phase budget', target_scale_cost_known=False),
            dict(stage='ready_attempt_and_N_producer', evidence='legacy bound 3h fake Jobs; real 232-stage target absent', target_scale_cost_known=False),
            dict(stage='source_history_and_current_join', evidence='current H1 net pair/H3 reconstruction/named faults', target_scale_cost_known=False),
            dict(stage='shared_Rref_and_active_Actual', evidence='legacy 3h positive request/repair/timeout carry freeze', target_scale_cost_known=False),
            dict(stage='pre_paired_commit_post_history', evidence='legacy 3h plus cubic history lower bound', target_scale_cost_known=False),
            dict(stage='phase_terminal_and_missing_needed_followup', evidence='business-only boundary units; genuine terminal open', target_scale_cost_known=False),
            dict(stage='checkpoint_close_and_fresh_process_replay', evidence='legacy same-process readonly reopen only', target_scale_cost_known=False),
            dict(stage='uncertain_failure_cleanup_reports_and_archives', evidence='bounded diagnostics observed cleanup; writer/crash open', target_scale_cost_known=False),
        ],
        resource_registration_missing=['per-event/database/holder capacity', '232-stage normal archives',
            'Rref/Actual and failure archives', 'scratch/checkpoint/report/reserve/concurrency',
            'complete wall/RSS/storage including terminal/reopen and failure tails'],
        whole_study_reuse=deepcopy(previous['proof_reuse']),
        no_solver_discounts_from_logical_graph=True,
        overall_performance_review_complete=False, long_connected_launch_admitted=False,
        resource_admission=False, formal_execution_ready=False, native_execution_authorized=False,
        full_192_hour_execution_verified=False, formal_result=False)
    save('whole_workflow_budget_v4.json', budget)
    state = deepcopy(previous)
    state['current_development_evidence'].update(
        named_constructor_dependency_alias_fault_rejected=True,
        named_external_metadata_version_fault_rejected=True,
        full_actual_source_fault_matrix_verified=False,
        successor_3h_full_batch_seconds=oracle['successor_batch_seconds'],
        short_batch_seconds=[row['elapsed_seconds'] for row in short['calls']],
        model_dependency_bookend_negative_cases_evidence='model_units_02',
        H3_auxiliary_negative_cases=21,
        latest_unit_tests=171)
    state['current_episode_scaling']['conditional_unadopted_candidate'] = targets['192']['conditional_unadopted_candidate']
    state['prior_preparation_state'] = dict(path=str(prior_path), sha256=pin(prior_path),
        exact_inherited_bindings_verified=True, full_nested_source_reaudit_performed=False)
    for gate in state['gates']:
        if gate['id'] == 'source_path_performance_and_freshness':
            gate['remaining_work'] = ('Named constructor alias and external metadata faults now reject; '
                'complete applicable real file/runtime/determinism/cleanup coverage and choose valid source path. '
                'Current H3 identity reconstruction and fixed H1 timing retain saved resolver seam; owner still baseline.')
    state['bindings'] = {name: pin(name) for name in previous['bindings']}
    sources = [Path(__file__), prior_path, HERE / 'whole_workflow_budget_v4.json', *outer_sources,
        HERE / 'model_units_02/terminal.json', HERE / 'probe_02/probe_terminal.json',
        HERE / 'runtime_probe_01/probe_terminal.json', HERE / 'oracle_01/oracle_terminal.json',
        HERE / 'short_comparison_01/comparison_terminal.json']
    for path in sources:
        state['bindings'][str(path)] = pin(path)
    save('formal_preparation_state_v4.json', state)
    print(json.dumps(dict(targets=list(targets), open_gates=16,
        candidate_192_job_replays=298760, total_wall_admission_seconds=None,
        objective_complete=False)))


if __name__ == '__main__':
    main()
