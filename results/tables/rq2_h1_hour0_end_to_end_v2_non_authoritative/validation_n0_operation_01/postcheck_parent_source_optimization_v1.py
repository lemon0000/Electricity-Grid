"""Reconcile scoped development evidence without changing any milestone gate."""
from hashlib import sha256
import json
from pathlib import Path
import re
import traceback

import psutil

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
OUT=HERE/'parent_source_optimization_postcheck_02_non_authoritative'
OUT.mkdir(exist_ok=False)
evidence={}


def read(path):
    raw=path.read_bytes()
    evidence[str(path.relative_to(REPO))]=sha256(raw).hexdigest()
    return json.loads(raw)


def check_snapshot(folder,request):
    current_differences=[]
    for name,pin in request['source_sha256'].items():
        path=Path(name)
        relative=path.relative_to(REPO) if path.is_relative_to(REPO) else Path('vendor')/path.relative_to(Path('D:/'))
        saved=folder/'tested_bytes'/relative
        assert sha256(saved.read_bytes()).hexdigest()==pin,(folder,name,'tested bytes')
        if sha256(path.read_bytes()).hexdigest()!=pin:current_differences.append(name)
    return dict(tested_source_files=len(request['source_sha256']),snapshot_hashes_match=True,
        current_source_differences=current_differences,
        evidence_applies_to_exact_tested_bytes=True)


def absent(row):
    try:return psutil.Process(row['pid']).create_time()!=row['creation_time']
    except psutil.NoSuchProcess:return True


def monitor(name,inner):
    folder=HERE/name
    terminal=read(folder/'terminal.json')
    assert terminal['exit_code']==terminal['child_exit_code']==terminal['inner_exit_code']==0
    assert terminal['source_unchanged'] and terminal['old_chain_unchanged']
    assert terminal['observed_owned_processes_absent'] and not terminal['observed_owned_processes_remaining']
    assert not terminal['errors'] and terminal['stop_reason'] is None
    assert all(absent(row) for row in terminal['observed_owned_processes'])
    request=read(folder/'request.json')
    assert sha256((HERE/inner/'terminal.json').read_bytes()).hexdigest()==terminal['inner_terminal_sha256']
    snapshot=check_snapshot(folder,request)
    return dict(terminal=terminal,snapshot=snapshot,request=request)


result=dict(status='DEVELOPMENT_EVIDENCE_RECONCILIATION',formal_result=False,
    full_hour0_chain_passed=False,whole_workflow_performance_review_complete=False,
    complete_genuine_Parent_validation=False,resource_admission=False,
    native_execution_authorized=False,official_review_gate_closed=False)
try:
    oracle_name='parent_source_scientific_oracle_03_non_authoritative'
    oracle=read(HERE/oracle_name/'terminal.json')
    base=read(HERE/oracle_name/'baseline.json')
    baseline_raw=(HERE/oracle_name/'baseline_complete_source_projection.json').read_bytes()
    projection_pin=sha256(json.dumps(json.loads(baseline_raw),sort_keys=True,
        separators=(',',':'),allow_nan=False).encode()).hexdigest()
    measurements=[]
    for index in range(1,18):
        candidate=read(HERE/oracle_name/f'candidate_{index}.json')
        assert candidate['prepare']==index
        assert candidate['scientific_decision_and_audit_bytes_equal'] and candidate['complete_source_fields_equal']
        assert candidate['complete_source_projection_sha256']==projection_pin
        assert (candidate['full'],candidate['reused'])==((4,4) if index<=16 else (0,8))
        measurements.append(candidate)
    assert oracle['measurements']==measurements and oracle['baseline']==base
    assert oracle['exit_code']==0 and oracle['host_lease_and_activation_are_explicit_fakes']
    assert not oracle['complete_Parent_validation'] and not oracle['live_Parent_credential_issued']
    proof=read(HERE/oracle_name/'final_proof_receipt.json')
    assert proof['closed'] and proof['proof_cleared'] and proof['first_failure'] is None
    assert (proof['full_numerical_hour_replays'],proof['reused_numerical_inspections'],
        proof['context_observations'])==(64,72,272)
    oracle_monitor=monitor('parent_source_scientific_oracle_monitor_03',oracle_name)
    assert oracle_monitor['terminal']['saved_files_unchanged']
    result['saved_source_oracle']=dict(baseline_seconds=base['seconds'],
        reused_prepare_seconds=measurements[-1]['seconds'],complete_fields_sha256=projection_pin,
        baseline_decision_sha256=base['decision_sha256'],baseline_audit_sha256=base['audit_sha256'],
        snapshot=oracle_monitor['snapshot'],exact_source_fields_equal=True,all_17_comparisons_complete=True,
        genuine_Parent_activation=False,entry_import_window_fully_proven=False,
        path_coverage='repo only; active saved input root excluded',
        old_inherited_unused_plan_fields_do_not_prove_inspection=True)

    profile_name='parent_source_profile_03_non_authoritative'
    profile=read(HERE/profile_name/'terminal.json')
    assert profile['exit_code']==0 and profile['profiler_overhead_included']
    assert profile['unprofiled_decision_audit_bytes_equal'] and profile['unprofiled_complete_source_fields_equal']
    assert (HERE/profile_name/'baseline_complete_source_projection.json').read_bytes()==baseline_raw
    assert read(HERE/profile_name/'baseline.json')['decision_sha256']==base['decision_sha256']
    profile_monitor=monitor('parent_source_profile_monitor_03',profile_name)
    admission=read(HERE/profile_name/'fixture_path_admitted.json')
    imports=read(HERE/profile_name/'fixture_path_observation.json')
    assert admission['paths']==admission['configured_paths']==imports['expected_configured_paths']
    assert imports['imported_modules']==['parent_source_saved_fixture']
    assert len(imports['direct_origins'])==2
    for value in imports['direct_origins'].values():
        assert sha256(Path(value['file']).read_bytes()).hexdigest()==value['sha256']
    path_receipt=read(HERE/profile_name/'path_receipt.json')
    assert (path_receipt['hits'],path_receipt['fallback_calls'])==(4,3453)
    closed=read(HERE/profile_name/'bounded_closed_receipt.json')
    assert closed['code_owner_closed'] and closed['path_open_restored'] and closed['path_read_bytes_restored']
    assert closed['remaining_code_handles']==closed['remaining_streams']==closed['remaining_proxies']==0
    assert not closed['cleanup_errors'] and closed['first_failure'] is None
    rows=read(HERE/profile_name/'profile_functions.json')
    stat_row=next(row for row in rows if row['function']=='<built-in method nt.stat>')
    assert stat_row['total_calls']==127246
    result['source_profile']=dict(profiled_source_seconds=profile['profiled_source_seconds'],
        profiler_overhead_included=True,wall_time_share_inference_admitted=False,
        stat_calls=stat_row['total_calls'],stat_self_seconds=stat_row['self_seconds'],
        path_hits=4,path_fallbacks=3453,snapshot=profile_monitor['snapshot'],
        import_window_admission_proven=True,complete_target_path_coverage=False,
        compiled_dispatch_observer_adopted=False)

    unit_folder=HERE/'parent_common_regression_unit_02'
    unit=read(unit_folder/'terminal.json')
    request=read(unit_folder/'request.json')
    assert unit['exit_code']==0 and unit['source_unchanged'] and unit['stop_reason'] is None
    assert absent(read(unit_folder/'started.json'))
    assert re.search(r'\b93 passed\b',(unit_folder/'stdout.log').read_text(encoding='utf-8'))
    snapshot=check_snapshot(unit_folder,request)
    assert not snapshot['current_source_differences']
    result['current_scoped_regression']=dict(passed=93,outer_seconds=unit['elapsed_seconds'],
        snapshot=snapshot,scope='state machines, explicit fake functional route, real finally AST and common bridge')
    fresh_name='fresh_owned_source_cost_03_non_authoritative'
    fresh=monitor('fresh_owned_source_cost_monitor_03',fresh_name)
    assert fresh['terminal']['owned_lock_inventory_matches']
    assert len(fresh['terminal']['saved_locks_reacquired_and_released'])==10
    reports=list(Path(fresh['request']['basetemp']).rglob('n0_source_cost_report.json'))
    assert len(reports)==1
    cost=read(reports[0]) if reports[0].is_relative_to(REPO) else json.loads(reports[0].read_bytes())
    evidence[str(reports[0])]=sha256(reports[0].read_bytes()).hexdigest()
    fresh_paths=read(HERE/fresh_name/'path_receipt.json')
    fresh_closed=read(HERE/fresh_name/'path_closed_receipt.json')
    assert fresh_closed==dict(dispatch_restored=True,remaining_directory_handles=0,remaining_paths=0,state='closed')
    assert cost['synthetic_jobs']==cost['original_source_prepares']==1 and cost['real_native_calls']==0
    assert cost['owner_closed_before_source'] and not cost['full_hour0_chain_passed']
    result['fresh_owned_probe']=dict(plan='fresh_owned_source_cost_plan_03.json',
        outer_seconds=fresh['terminal']['elapsed_seconds'],timings=cost['times'],
        path_hits=fresh_paths['hits'],path_fallbacks=fresh_paths['fallback_calls'],
        snapshot=fresh['snapshot'],owned_processes_absent=True,exact_ten_locks_reacquired=True,
        scope='one Bootstrap2 N0 then owner close and one original source; no complete-chain credential')
    result['remaining_gates']=['genuine three-arm Handoff/Actual/paired/reopen with timing',
        'complete path performance and resource admission','192-hour producer/phase/failure coverage',
        'concrete experiment task DAG and budgets','seal and fresh official review','specific formal run authority']
    result['exit_code']=0
except BaseException:
    result.update(exit_code=1,error=traceback.format_exc())
result['evidence_sha256']=evidence
with (OUT/'terminal.json').open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
print(json.dumps({key:value for key,value in result.items() if key!='evidence_sha256'}))
raise SystemExit(result['exit_code'])
