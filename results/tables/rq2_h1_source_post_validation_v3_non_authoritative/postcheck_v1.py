"""Reconcile saved diagnostic terminals and exact evidence, without a Reader."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_bytes())


def main():
    predecessor=HERE.parent/'rq2_h1_source_callable_gap_v1_non_authoritative/final_verification.json'
    previous=load(predecessor)
    assert pin(predecessor)=='8a28fdb3e213842522e8397c2a64ceded3a4d48e27faa6dded31379ecab783df'
    assert len(previous['bindings'])==950
    assert all(pin(path)==value for path,value in previous['bindings'].items())
    request=load(HERE/'oracle_01/request.json')
    terminal=load(HERE/'oracle_01/terminal.json')
    worker=load(HERE/'oracle_01/oracle_terminal.json')
    assert terminal['exit_code']==0 and terminal['worker_accepted'] is True
    assert terminal['worker']==worker and terminal['reason'] is None and not terminal.get('error')
    assert terminal['changed_sources']==[] and terminal['observed_processes_remaining']==[]
    assert terminal['source_pins']==len(request['sources_sha256'])==1322
    assert all(pin(path)==value for path,value in request['sources_sha256'].items())
    assert worker['exit_code']==0 and worker['saved_case_sha256_equal'] is True
    assert worker['saved_identity_bound_science_reconstruction_equal'] is True
    assert worker['old_raw_science_bytes_directly_read'] is False
    assert worker['independent_scientific_implementation'] is False
    assert len(worker['validator_faults'])==21 and 'old_owner_rejects_new_type' in worker['validator_faults']
    metrics=worker['observations']
    assert len(metrics)==2 and metrics[0]['observation_token']!=metrics[1]['observation_token']
    expected_stages={'pre_constructor','constructor','first_post_constructor_bookends',
        'all_hour_packet_revalidation','final_bookends','proof_encoding','cleanup'}
    for metric in metrics:
        assert metric['completed_hours']==metric['all_hour_packet_count']==3
        assert metric['parent_inspect_traversals']==1 and metric['parent_namespace_observations']==3
        assert metric['combined_retained_bytes']==metric['all_hour_packet_bytes']+metric['selected_frame_bytes']
        assert 0<metric['combined_retained_bytes']<=metric['retained_cap_bytes']==128*1024**2
        assert set(metric['stage_seconds'])==expected_stages
        assert all(type(value) is float and value>=0 for value in metric['stage_seconds'].values())
        assert all(metric[name] is True for name in ('constructor_inspection_reused',
            'normal_model_dependency_bookends_verified','all_hour_packet_revalidation_verified',
            'parent_namespace_bookends_verified','final_post_revalidation_bookends_verified',
            'named_runtime_bookends_verified'))
        assert all(metric[name] is False for name in ('complete_dynamic_input_closure_proved',
            'unobserved_between_bookends_ABA_covered'))
    prior=load(REPO/'results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03_postcheck.json')
    case_pins=prior['diagnostic_case_files_sha256']
    assert len(case_pins)==465 and all(pin(path)==value for path,value in case_pins.items())
    case=Path('D:/h1_outage_connected_03_non_authoritative/test_three_hour_connected_outa0')
    assert len([p for p in case.rglob('*') if p.is_file()])==465
    owned=load(case/'external_preclose_checkpoint.json')['saved_files_sha256']
    assert len(owned)==444 and all(pin(path)==value for path,value in owned.items())
    unit=load(HERE/'unit_07/terminal.json')
    assert unit['exit_code']==0 and unit['source_before']==unit['source_after'] and not unit['changed']
    assert len(unit['source_after'])==18 and all(pin(path)==value for path,value in unit['source_after'].items())
    suite=ET.parse(HERE/'unit_07/pytest.xml').getroot().find('testsuite')
    junit={key:int(suite.attrib[key]) for key in ('tests','failures','errors','skipped')}
    assert junit==dict(tests=294,failures=0,errors=0,skipped=0)
    snapshots=[]
    for folder in ('unit_07','oracle_01'):
        files=[p for p in (HERE/folder/'tested_bytes').rglob('*') if p.is_file()]
        assert all(path.read_bytes()==(REPO/path.relative_to(HERE/folder/'tested_bytes')).read_bytes() for path in files)
        snapshots.append(dict(folder=folder,count=len(files)))
    # Literal callsites on the clean-success path; not runtime instrumentation.
    tree=ast.parse((REPO/'experiments/h1_phase_historical_batch_development_v3.py').read_text(encoding='utf-8'))
    replay=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='replay_prefixes')
    direct=sum(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='check_dependencies' for n in ast.walk(replay))
    assert direct==7
    source_tree=ast.parse((REPO/'experiments/h1_phase_exact_source_batch_development_v3.py').read_text(encoding='utf-8'))
    prepare=next(n for n in source_tree.body if isinstance(n,ast.FunctionDef) and n.name=='prepare_many')
    source_checks=sum(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='check_entry' for n in ast.walk(prepare))
    assert source_checks==5
    bindings=previous['bindings']|request['sources_sha256']|unit['source_after']|case_pins|owned
    for path in (predecessor,Path(__file__),HERE/'oracle_01/terminal.json',HERE/'oracle_01/oracle_terminal.json',
                 HERE/'oracle_01/request.json',HERE/'unit_07/terminal.json',HERE/'preseal_findings_v1.json',
                 HERE/'probe_budget_v1.json'):
        bindings[str(path)]=pin(path)
    result=dict(status='DRAFT_NONAUTHORITATIVE',scope='terminal_reconciliation_and_fresh_exact_byte_reuse',
        predecessor_bindings_verified=950,launch_bindings_verified=1322,saved_case_files=465,owned_files=444,
        tested_byte_snapshots=snapshots,junit=junit,unit_outer_seconds=unit['outer_seconds'],
        batch_seconds=worker['successor_batch_seconds'],worker_seconds=worker['elapsed_seconds'],
        runner_seconds=terminal['outer_seconds'],peak_sampled_tree_rss_bytes=terminal['peak_sampled_tree_rss_bytes'],
        peak_output_logical_bytes=terminal['peak_logical_bytes'],
        output_peak_is_loop_sample_not_final_or_case_disk=True,
        complete_unobserved_process_tree_proof=terminal['complete_unobserved_process_tree_proof'],
        case_read_opens=worker['source_activity']['case_read_opens'],observed_rejected_mutations=worker['source_activity']['rejected_mutations'],
        source_activity_is_not_scientific_progress=True,observations=metrics,
        static_clean_success_callsites=dict(reader_local_guard_checks=direct,
            model_snapshots_per_reader=3,guard_checks_per_model_snapshot=2,source_entry_checks_per_batch=source_checks),
        static_work_units_not_runtime_counters=dict(saved_job_artifact_replays=12,M5_stage_replays=60),
        provenance_correction=dict(worker_text_substitution_list_is_not_exhaustive=True,
            additional_output_field_rename=['old_saved_science_bytes_equal','saved_identity_bound_science_reconstruction_equal'],
            numerical_path_changed_by_field_rename=False,
            reconstruction_uses_new_current_normal_decision=True,
            scientific_scope='saved audit identity-bound internal consistency using original join/projection',
            directly_read_predecessor_raw_scientific_payload=False,independently_implemented_scientific_oracle=False),
        source_successor_adopted=False,owner_integrated=False,resource_admission=False,
        overall_performance_review_complete=False,long_connected_launch_admitted=False,
        full_192_hour_execution_verified=False,formal_execution_ready=False,formal_result=False,
        native_execution_authorized=False,new_normal_jobs=0,real_native_calls=0,bindings=bindings)
    with (HERE/'postcheck_v1.json').open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(fresh_bindings=len(bindings),junit=junit,case_files=465,owned_files=444,
        batch_seconds=result['batch_seconds'],runner_seconds=result['runner_seconds'])))


if __name__=='__main__':main()
