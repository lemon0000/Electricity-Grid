"""Versioned preparation and whole-workflow accounting, never admission."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PRIOR=HERE.parent/'rq2_h1_source_post_validation_v3_non_authoritative'


def load(path):return json.loads(Path(path).read_bytes())
def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def save(name,value):
    with (HERE/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def ref(path):return dict(path=str(path),sha256=pin(path))


def main():
    post=load(HERE/'combination_postcheck.json')
    assert post['enumerated_nine_fault_combination_verified'] and post['accepted_case_count']==9
    assert post['original_suite_accepted'] is False
    reused=load(HERE/'saved_M232_evidence_reuse_v1.json')
    assert all(pin(path)==value for path,value in reused['bindings'].items())
    inherited=load(PRIOR/'final_verification.json')['bindings']
    assert len(inherited)==2483 and all(pin(path)==value for path,value in inherited.items())
    budget=deepcopy(load(PRIOR/'whole_workflow_budget_v7.json'))
    state=deepcopy(load(PRIOR/'formal_preparation_state_v7.json'))
    assert len(state['gates'])==16 and all(gate['complete'] is False for gate in state['gates'])
    decision=deepcopy(load(PRIOR/'source_adoption_decision_v3.json'))
    decision['prior_decision']=ref(PRIOR/'source_adoption_decision_v3.json')
    decision['scope']='source v3 with nine finite saved-M5 single-Reader faults; no owner adoption'
    decision['constructor_failure_evidence']='five actual saved Reader pre-inspect faults plus actual postconstructor fault; real inner/outer cleanup observed'
    decision['current_saved_failure_evidence']=ref(HERE/'combination_postcheck.json')
    decision['enumerated_nine_fault_combination_verified']=True
    decision['complete_real_saved_Reader_file_fault_matrix_verified']=False
    decision['two_Reader_prepare_many_failure_matrix_complete']=False
    decision['M232_H192_source_or_retention_applicability_proved']=False
    decision['production_speedup_established']=False
    decision['source_successor_adopted']=False
    decision['next_work']=[
        'bound source-v3 applicability/retention for M232 and target packet/namespace scale using existing evidence',
        'freeze applicable source and two-Reader failure-window criteria before source/owner integration',
        'versioned owner route and full failure/terminal/reopen net cost before new connected body',
        'H168/F<=24 source-connected boundary and episode termination remain open']
    save('source_adoption_decision_v4.json',decision)
    budget['prior_budget']=ref(PRIOR/'whole_workflow_budget_v7.json')
    budget['source_adoption_decision']=ref(HERE/'source_adoption_decision_v4.json')
    budget['current_saved_Reader_failure_observation']=dict(
        postcheck=ref(HERE/'combination_postcheck.json'),accepted_cases=9,
        scope=post['scope'],attempts=post['attempts'],
        accepted_case_actual_counters=post['accepted_case_actual_counters'],
        cumulative_attempt_outer_seconds=post['cumulative_attempt_outer_seconds'],
        interrupted_original_case_counters_unknown=True,
        original_suite_accepted=False,original_suite_budget_extended=False,
        worker_same_exact_sha256=post['same_exact_worker_sha256'],
        diagnostic_trace_profile_overhead_included=True,
        production_timing_or_complete_failure_budget=False,
        observed_sampled_RSS_is_not_RSS_bound=True)
    budget['current_M232_evidence_reuse']=ref(HERE/'saved_M232_evidence_reuse_v1.json')
    budget['remaining_source_work']=[
        'applicable dependency and failure-window evidence beyond the finite named endpoint guard and nine saved-M5 faults',
        'M232/all-hour packet retention and target namespace/source scale resource evidence',
        'two-Reader source failure windows and versioned owner integration/full failure-terminal-reopen net cost']
    newrefs=[PRIOR/'whole_workflow_budget_v7.json',PRIOR/'formal_preparation_state_v7.json',
        HERE/'source_adoption_decision_v4.json',HERE/'combination_postcheck.json',
        HERE/'saved_M232_evidence_reuse_v1.json',HERE/'attempt01_postcheck.json',
        HERE/'plan_remaining_v1.json',HERE/'preseal_findings_attempt01.json',
        HERE/'preseal_findings_combination_v1.json']
    budget['bindings'].update({str(path):pin(path) for path in newrefs})
    for row in budget['target_work_units'].values():
        assert row['total_wall_admission_seconds'] is None
        assert row['peak_rss_admission_bytes'] is None and row['total_storage_admission_bytes'] is None
    save('whole_workflow_budget_v8.json',budget)
    state['prior_preparation_state']=ref(PRIOR/'formal_preparation_state_v7.json')
    state['current_whole_workflow_budget']=ref(HERE/'whole_workflow_budget_v8.json')
    state['current_source_adoption_decision']=ref(HERE/'source_adoption_decision_v4.json')
    state['current_development_evidence']['saved_Reader_finite_failure_combination']=dict(
        postcheck=ref(HERE/'combination_postcheck.json'),accepted_cases=9,
        source_and_fixture_same_exact_contract=True,original_suite_exit_code=1,
        original_suite_accepted_cases=8,remaining_attempt_exit_code=0,
        remaining_attempt_accepted_cases=1,
        actual_inner_and_outer_cleanup_observed=True,ReadViews_are_OS_writer_leases=False,
        real_Reader_failure_matrix_complete=False,two_Reader_failure_matrix_complete=False,
        owner_integrated=False,source_successor_adopted=False)
    state['current_development_evidence']['M232_existing_evidence_reuse']=ref(HERE/'saved_M232_evidence_reuse_v1.json')
    for gate in state['gates']:
        if gate['id']=='source_path_performance_and_freshness':
            gate['remaining_work']='Nine enumerated saved-M5 single-Reader faults now have actual cleanup evidence. M232/target retention, applicable source/two-Reader failure criteria and versioned owner/full net cost remain; no adoption/discount.'
        if gate['id']=='episode_workflow_budget':
            gate['remaining_work']='v8 reuses v7 work units and records diagnostic budget-stop/completion separately. Old M232251-file evidence retained. Full-owner/native producer/failure/terminal/reopen and physical admission remain unknown; aggregate wall/RSS/storage stay null.'
    state['bindings'].update({str(path):pin(path) for path in (*newrefs,HERE/'whole_workflow_budget_v8.json')})
    state['formal_gate_changes']=[]
    state['canonical_plan_and_blocker_bytes_retained']=True
    state['objective_complete']=False
    save('formal_preparation_state_v8.json',state)
    print(json.dumps(dict(open_gates=16,accepted_finite_fault_cases=9,
        whole_workflow_budget_admitted=False,source_adopted=False,objective_complete=False)))


if __name__=='__main__':main()
