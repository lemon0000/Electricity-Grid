"""Read saved fault terminals and exact hashes; never invoke a Reader."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def load(path):return json.loads(Path(path).read_bytes())
def pin(path):return sha256(Path(path).read_bytes()).hexdigest()


def main():
    suite=HERE/'suite_01'
    plan=load(HERE/'plan_v2.json')
    terminal=load(suite/'terminal.json')
    request=load(suite/'request.json')
    pins=request['sources_sha256']
    assert len(pins)==2492 and all(pin(path)==value for path,value in pins.items())
    assert terminal['exit_code']==1 and terminal['changed_sources']==[]
    assert len(terminal['cases'])==len(plan['cases'])==9
    accepted=[]
    for case,row in zip(plan['cases'],terminal['cases']):
        path=Path(row['terminal'])
        outer=load(path)
        assert pin(path.parent/'tested_bytes/fault_worker_v1.py')==pin(HERE/'fault_worker_v1.py')
        assert outer['case']==case['case'] and outer['observed_processes_remaining']==[]
        if not row['accepted']:
            assert case['case']=='final_namespace_read_result' and outer['reason']=='suite_wall_limit'
            assert outer['accepted'] is False and not (path.parent/'worker_terminal.json').exists()
            assert outer['case_outer_seconds']<plan['per_case_wall_limit_seconds']
            samples=[json.loads(line) for line in (path.parent/'monitor.jsonl').read_text().splitlines()]
            last=samples[-1]
            assert last['suite_seconds']>240 and last['case_seconds']<90
            assert last['rss_bytes']<plan['owned_tree_sampled_rss_limit_bytes']
            assert last['output_logical_bytes']<plan['output_logical_limit_bytes']
            continue
        worker=load(path.parent/'worker_terminal.json')
        assert outer['accepted'] is True and outer['exit_code']==0 and outer['worker_accepted'] is True
        assert worker==outer['worker'] and worker['exit_code']==0
        assert worker['observed_replay_call_counts']==case['expected_runtime_counts']
        assert worker['namespace_observations_reached']==case['namespace_round_expected']
        assert worker['injection_count']==1 and type(worker['injection_count']) is int
        assert worker['instrumentation_errors']==worker['cleanup_errors']==[]
        for name in ('prior_trace_and_profile_restored','guard_usable_after_fault_restored',
                     'saved_case_sha256_equal','injection_reached','Reader_closed',
                     'Reader_owner_fields_cleared','constructor_capture_cleared','captured_cleared',
                     'all_packets_cleared','seen_hours_cleared'):
            assert worker[name] is True,(case['case'],name)
        assert worker['activity']['rejected_mutations']==0
        assert worker['outer_ReadViews_closed']==[True]*4
        assert all(item['closed'] is True and item.get('nested_ReadView_closed',True) is True
                   for item in worker['actual_inner_states'].values())
        closes=worker['close_calls']
        assert [name for name in closes if name in ('_journal','_anchor','_root_lease')]==['_journal','_anchor','_root_lease']
        assert [name for name in closes if name.startswith('outer_')]==['outer_3','outer_2','outer_1','outer_0']
        assert closes.count('frozen_parent')==1
        expected_dynamic=1 if case['case'] in ('constructor_primary','constructor_helper_alias','constructor_Path_alias') else 0
        assert closes.count('dynamic_parent')==expected_dynamic
        if case['case']=='final_read_sharing_error':
            assert worker['primary_error_type']=='PermissionError' and worker['primary_errno']==13
            assert worker['native_sharing_conflict_code']==32
            assert worker['read_only_sharing_handle_closed'] and worker['sharing_target_identity_before_after_equal']
        if case['case']=='unselected_packet_drift':
            assert worker['all_packet_keys_before_revalidation']==[0,1]
            assert worker['packet_digests_before_after'][0]!=worker['packet_digests_before_after'][1]
            assert 'H1 current input drift' in worker['primary_error_text']
            assert any(item['function']=='validate_current' and item['file'].endswith('normal_h1_source.py')
                       for item in worker['rejection_trace'])
        accepted.append(dict(case=case['case'],terminal_path=str(path),terminal_sha256=pin(path),
            worker_terminal_sha256=pin(path.parent/'worker_terminal.json'),
            observed_replay_call_counts=worker['observed_replay_call_counts'],
            primary_error_type=worker['primary_error_type'],outer_seconds=outer['case_outer_seconds']))
    assert len(accepted)==8
    result=dict(status='DRAFT_NONAUTHORITATIVE',suite_terminal_sha256=pin(suite/'terminal.json'),
        source_pins_verified=len(pins),changed_sources=[],accepted_cases=accepted,
        accepted_case_count=8,outer_case_terminal_count=9,original_suite_accepted=False,
        open_case='final_namespace_read_result',stop_reason='suite_wall_limit',
        sampled_stop_threshold_seconds=240,sample_seconds=2,
        outer_seconds_including_cleanup=terminal['outer_seconds'],
        timeout_worker_cleanup_or_injection_proved=False,
        secondary_archive_error='FileNotFoundError reading absent worker_terminal after watchdog termination',
        observed_processes_remaining=[],
        original_suite_restarted_or_budget_extended=False,
        trace_profile_review='A trace callback raising disables that trace. Independent profile remains necessary for the earlier callback-raised primary faults.',
        remaining_case_decision='Reuse exact v1 worker in a separately registered one-case attempt with original per-case 90s; reuse accepted eight by hash.',
        source_successor_adopted=False,resource_admission=False,formal_execution_ready=False,
        full_192_hour_execution_verified=False,formal_result=False,new_normal_jobs=0,real_native_solver_calls=0)
    with (HERE/'attempt01_postcheck.json').open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(accepted=8,open_case=result['open_case'],verified_pins=len(pins))))


if __name__=='__main__':main()
