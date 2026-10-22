"""Combine immutable fault evidence; no Reader, model assembly or solve."""
import ast
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def load(path):return json.loads(Path(path).read_bytes())
def pin(path):return sha256(Path(path).read_bytes()).hexdigest()


def main():
    prior=load(HERE/'attempt01_postcheck.json')
    suite=HERE/'remaining_01';terminal=load(suite/'terminal.json')
    pins=load(suite/'request.json')['sources_sha256']
    assert len(pins)==2584 and all(pin(path)==value for path,value in pins.items())
    assert terminal['exit_code']==0 and terminal['changed_sources']==[]
    assert terminal['registered_case_count']==terminal['completed_case_count']==1
    row=terminal['cases'][0];path=Path(row['terminal']);outer=load(path)
    worker=load(path.parent/'worker_terminal.json')
    assert row['case']==worker['case']=='final_namespace_read_result'
    assert outer['accepted'] is True and outer['worker_accepted'] is True
    assert outer['exit_code']==0 and outer['reason'] is None and outer['observed_processes_remaining']==[]
    assert worker==outer['worker'] and worker['exit_code']==0
    assert pin(path.parent/'tested_bytes/fault_worker_v1.py')==pin(HERE/'fault_worker_v1.py')
    tree=ast.parse((HERE/'run_faults_v1.py').read_text(encoding='utf-8'))
    function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='accepted_worker')
    namespace={};exec(compile(ast.Module(body=[function],type_ignores=[]),'<pinned saved acceptance>','exec'),namespace)
    case=load(HERE/'plan_remaining_v1.json')['cases'][0]
    assert namespace['accepted_worker'](worker,case)
    assert worker['namespace_observations_reached']==3 and worker['namespace_seam_reads']==1
    assert worker['primary_error_type']=='ValueError'
    assert worker['primary_error_text']=='unexpected or unbounded historical suffix name'
    assert any(item['function']=='_inventory' and item['file'].endswith('h1_historical_parent_prefix_development_v1.py')
               for item in worker['rejection_trace'])
    assert worker['observed_replay_call_counts']==dict(job_inspections=2,stage_inspections=10,normal_after_returns=1)
    assert worker['close_calls']==['frozen_parent','_journal','_anchor','_root_lease','outer_3','outer_2','outer_1','outer_0']
    for name in ('Reader_closed','Reader_owner_fields_cleared','constructor_capture_cleared','captured_cleared',
                 'all_packets_cleared','seen_hours_cleared'):
        assert worker[name] is True,name
    assert worker['outer_ReadViews_closed']==[True]*4
    assert all(item['closed'] is True and item.get('nested_ReadView_closed',True) is True
               for item in worker['actual_inner_states'].values())
    rows=list(prior['accepted_cases'])
    rows.append(dict(case=worker['case'],terminal_path=str(path),terminal_sha256=pin(path),
        worker_terminal_sha256=pin(path.parent/'worker_terminal.json'),
        observed_replay_call_counts=worker['observed_replay_call_counts'],
        primary_error_type=worker['primary_error_type'],outer_seconds=outer['case_outer_seconds']))
    assert len(rows)==9 and len({row['case'] for row in rows})==9
    totals={name:sum(row['observed_replay_call_counts'][name] for row in rows)
            for name in ('job_inspections','stage_inspections','normal_after_returns')}
    assert totals==dict(job_inspections=10,stage_inspections=50,normal_after_returns=5)
    first=load(HERE/'suite_01/terminal.json')
    assert first['exit_code']==1 and sum(row['accepted'] for row in first['cases'])==8
    result=dict(status='DRAFT_NONAUTHORITATIVE',scope='nine enumerated saved-M5 single-Reader faults across two immutable attempts',
        accepted_case_count=9,enumerated_nine_fault_combination_verified=True,
        original_suite_accepted=False,original_suite_accepted_count=8,original_suite_exit_code=1,
        completion_attempt_accepted_count=1,original_suite_budget_extended=False,
        same_exact_worker_sha256=pin(HERE/'fault_worker_v1.py'),source_pins_verified=len(pins),
        accepted_cases=rows,accepted_case_actual_counters=totals,
        interrupted_original_case_counters_unknown=True,
        all_attempts_planned_maximum_Reader_invocations=10,
        all_attempts_planned_maximum_completed_numeric_prefix_hours=6,
        all_attempts_planned_maximum_saved_job_inspections=12,
        all_attempts_planned_maximum_M5_stage_inspections=60,
        attempts=[dict(path=str(HERE/'suite_01/terminal.json'),sha256=pin(HERE/'suite_01/terminal.json'),
                    outer_seconds=first['outer_seconds'],peak_sampled_tree_rss_bytes=first['peak_sampled_tree_rss_bytes'],
                    peak_output_logical_bytes=first['peak_output_logical_bytes']),
                  dict(path=str(suite/'terminal.json'),sha256=pin(suite/'terminal.json'),
                    outer_seconds=terminal['outer_seconds'],peak_sampled_tree_rss_bytes=terminal['peak_sampled_tree_rss_bytes'],
                    peak_output_logical_bytes=terminal['peak_output_logical_bytes'])],
        cumulative_attempt_outer_seconds=first['outer_seconds']+terminal['outer_seconds'],
        cumulative_attempt_seconds_is_production_budget=False,peak_RSS_values_are_not_additive=True,
        actual_inner_and_outer_cleanup_observed=True,ReadViews_are_OS_writer_leases=False,
        only_explicit_cleared_containers_checked=['captured','all_packets','seen_hours'],
        sharing_fault='actual read-only Windows sharing handle; native conflict32 then Python PermissionError errno13',
        packet_fault='in-memory reflection of unselected hour0 before original all-H validate_current',
        namespace_fault='third-round first-root inventory read-result seam; no disk name created',
        saved_fixture_scope='original synthetic/shared manifest resolver and one-field projection stand-in retained',
        complete_actual_source_failure_matrix=False,arbitrary_reflection_or_ABA_covered=False,
        two_Reader_prepare_many_failure_matrix_complete=False,owner_integrated=False,
        M232_or_H192_applicability_proved=False,source_successor_adopted=False,
        resource_admission=False,formal_execution_ready=False,full_192_hour_execution_verified=False,
        real_native_solver_calls=0,new_normal_jobs=0,formal_result=False)
    with (HERE/'combination_postcheck.json').open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(accepted_cases=9,source_pins=len(pins),counters=totals,
        original_suite_accepted=False,outer_seconds=result['cumulative_attempt_outer_seconds'])))


if __name__=='__main__':main()
