"""Attach a bounded component observation without admitting the whole workflow."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_bytes())
def save(name,value):
    target=HERE/name;expected=(json.dumps(value,indent=2)+'\n').encode('utf-8')
    if target.exists() and target.read_bytes()!=expected:
        assert target.read_bytes()==(HERE/'preseal_before_contract_fix'/name).read_bytes()
    target.write_bytes(expected)


def main():
    terminal=load(HERE/'cost_01/terminal.json')
    post=load(HERE/'postcheck_v1.json')
    overlay=load(HERE/'parameter_overlay_verification_v1.json')
    assert terminal['exit_code']==0 and terminal['junit']['accepted'] and terminal['reason'] is None
    assert not terminal.get('error') and terminal['changed_sources']==terminal['observed_processes_remaining']==[]
    assert post['actual_encoded_parameter_mapping_verified'] and overlay['source_authenticated_boundary_anchor'] is False
    assert overlay['initial_zero_business_state_verified'] is True
    assert post['source_pins']==1306 and len(post['tested_snapshots'])==14
    assert post['saved_case_files']==465 and post['saved_owned_files']==444
    assert post['saved_case_and_owned_sha256_unchanged']
    fact=terminal['fact'];assert [r['hours'] for r in fact['rows']]==[168,192]
    assert fact['final_recovery']=='1/50' and fact['final_debt']==fact['deadline_snapshot']=='0'
    prior=HERE.parent/'rq2_h1_constructor_window_fault_v1_non_authoritative'
    state=load(prior/'formal_preparation_state_v4.json')
    assert len(state['gates'])==16 and all(g['complete'] is False for g in state['gates'])
    observation=dict(status='DRAFT_NONAUTHORITATIVE',
        scope=overlay['parameter_scope'], benchmark_alpha='1/2',benchmark_D='1/2',
        histories=1,cohorts=1,lanes=1,repetitions_per_target=1,rows=fact['rows'],
        complete_prepare_advance_build_seconds=fact['build_seconds'],
        build_prepare_calls_by_fixed_code=fact['build_prepare_calls_by_fixed_code'],
        build_validate_history_length_sum_by_fixed_code=fact['build_validate_history_length_sum_by_fixed_code'],
        original_validator_internal_work_instrumented=False,
        scientific_payloads_unchanged=all(r['scientific_payload_unchanged'] for r in fact['rows']),
        actual_parameter_overlay_verified=True,source_authenticated_boundary_anchor=False,
        initial_zero_business_state_verified=overlay['initial_zero_business_state_verified'],
        availability_rule='q_le_f_times_w',physical_capacity_rule='q_plus_r_le_D',
        current_live_pins=1306,explicit_tested_byte_snapshots=14,
        owned_tree_peak_sampled_rss_bytes=terminal['peak_sampled_tree_rss_bytes'],
        observed_base_plus_out_logical_bytes=terminal['peak_logical_bytes'],
        logical_bytes_include_retained_copies=True,complete_owner_event_size_measured=False,
        component_or_whole_wall_upper_bound_established=False,
        whole_192h_wall_admission_seconds=None,whole_peak_rss_admission_bytes=None,whole_storage_admission_bytes=None,
        retained_whole_workflow_budget=str(prior/'whole_workflow_budget_v4.json'),
        retained_preparation_state=str(prior/'formal_preparation_state_v4.json'),
        remaining_open_gates=16,overall_performance_review_complete=False,long_connected_launch_admitted=False,
        resource_admission=False,native_execution_authorized=False,formal_execution_ready=False,
        full_192_hour_execution_verified=False,formal_result=False)
    save('budget_component_observation_v1.json',observation)
    excluded={'development_acceptance_v1.json','final_verification.json'}
    files=[p for p in HERE.rglob('*') if p.is_file() and p.relative_to(HERE).as_posix() not in excluded]
    files += [prior/'final_verification.json',prior/'development_acceptance_v1.json',
        prior/'whole_workflow_budget_v4.json',prior/'formal_preparation_state_v4.json',
        REPO/'configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml']
    core=dict(status='DRAFT_NONAUTHORITATIVE',task_risk='R3',unique_writer='root',
        objective_complete=False,scope='target_length_detached_business_component_observation',
        observation=observation,open_preparation_gates=16,
        saved_case_and_owned_sha256_unchanged=post['saved_case_and_owned_sha256_unchanged'],
        source_candidate_adopted=False,owner_connected=False,real_phase_terminal_reopen_verified=False,
        preserved_superseded_draft_final=str(HERE/'preseal_before_contract_fix/final_verification.json'),
        overall_performance_review_complete=False,resource_admission=False,
        native_execution_authorized=False,formal_execution_ready=False,full_192_hour_execution_verified=False,
        sealed=False,official_review_pass=False,new_normal_jobs=0,real_native_calls=0,formal_result=False,
        bindings={str(p):pin(p) for p in sorted(set(files))})
    save('development_acceptance_v1.json',core)
    print(json.dumps(dict(bindings=len(core['bindings']),open_gates=16,whole_workflow_admitted=False)))


if __name__=='__main__':main()
