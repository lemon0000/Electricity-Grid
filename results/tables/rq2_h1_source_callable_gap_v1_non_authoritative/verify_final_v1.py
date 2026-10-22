"""Fresh exact-byte reconciliation of detached development evidence only."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
sys.path.insert(0,str(REPO))


def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def save(path,value):
    raw=(json.dumps(value,indent=2)+'\n').encode('utf-8')
    if path.exists():assert path.read_bytes()==raw,('existing checkpoint differs',str(path))
    else:path.write_bytes(raw)


def main():
    prior_path=HERE.parent/'rq2_h1_archive_envelope_v1_non_authoritative/final_verification.json'
    assert pin(prior_path)=='2d3abb3493b8b6ac3c43c9e71014206ba24b47d38e22fa23c98d29d7f73aec2f'
    prior=load(prior_path)
    assert len(prior['bindings'])==809 and all(pin(p)==v for p,v in prior['bindings'].items())
    latest=load(HERE/'unit_06/terminal.json')
    assert latest['junit']==dict(tests=200,failures=0,errors=0,skipped=0)
    assert latest['exit_code']==0 and latest['changed_code']==[]
    assert latest['code_bindings_before']==latest['code_bindings_after']
    assert len(latest['code_bindings_before'])==len(latest['explicit_tested_snapshots'])==18
    assert all(pin(p)==v for p,v in latest['code_bindings_after'].items())
    attempts=[]
    for directory in sorted(HERE.glob('unit_*')):
        terminal=load(directory/'terminal.json')
        assert terminal['changed_code']==[]
        for original,expected in terminal['code_bindings_before'].items():
            snapshot=directory/'tested_bytes'/Path(original).name
            assert pin(snapshot)==expected
            assert terminal['explicit_tested_snapshots'][str(snapshot.resolve())]==expected
        attempts.append(dict(name=directory.name,exit_code=terminal['exit_code'],junit=terminal['junit'],
            tested_snapshots_verified=len(terminal['explicit_tested_snapshots'])))
    assert [x['exit_code'] for x in attempts]==[0,1,0,1,0,0]
    preserved=load(HERE/'before_review_01/snapshot_bindings.json')
    assert len(preserved)==8 and all(pin(p)==v for p,v in preserved.items())
    inventory=load(HERE/'global_inventory_v1.json')
    assert all(pin(p)==v for p,v in inventory['bindings'].items())
    observed=load(HERE/'inventory_01/terminal.json')
    assert observed['exit_code']==0
    assert observed['code_sha256_before']==observed['code_sha256_after']==pin(HERE/'inventory_globals_v1.py')
    assert pin(HERE/'inventory_01/inventory_globals_v1.py')==observed['code_sha256_before']
    # Both frozen programs are the exact predecessor code objects, with copied
    # required-builtin namespaces. The supported effect boundary remains narrow.
    from experiments import h1_constructor_rejection_support_development_v1 as support
    cells=dict(zip(support.close_replay.__code__.co_freevars,
        (cell.cell_contents for cell in support.close_replay.__closure__)))
    assert cells['frozen_parent'].__code__ is support.candidate.binding.snapshot.parent.SourceParent.close.__code__
    assert cells['frozen_driver'].__code__ is support.candidate.prior._close_replay.__code__
    assert cells['process_id'] is support.candidate.capture.os.getpid
    assert cells['thread_id'] is support.candidate.capture.get_ident
    outputs=[HERE/name for name in ('source_adoption_decision_v1.json','whole_workflow_budget_v6.json',
        'formal_preparation_state_v6.json','acceptance_report.md','continuation_handoff_20261021.md')]
    before={str(p):pin(p) for p in outputs}
    result=subprocess.run([sys.executable,'-B',str(HERE/'build_status_v1.py')],cwd=REPO,
        capture_output=True,text=True,encoding='utf-8',timeout=30)
    assert result.returncode==0,result.stderr
    assert all(pin(p)==v for p,v in before.items())
    state=load(HERE/'formal_preparation_state_v6.json');budget=load(HERE/'whole_workflow_budget_v6.json')
    assert len(state['gates'])==16 and all(g['complete'] is False for g in state['gates'])
    assert all(pin(p)==v for p,v in state['bindings'].items())
    assert all(pin(p)==v for p,v in budget['bindings'].items())
    assert budget['overall_performance_review_complete'] is False
    for target in budget['target_work_units'].values():
        assert all(target[k] is None for k in ('total_wall_admission_seconds',
            'peak_rss_admission_bytes','total_storage_admission_bytes'))
        assert target['conditional_unadopted_candidate']['usable_for_resource_discount'] is False
    decision=load(HERE/'source_adoption_decision_v1.json')
    launch=load(HERE/'launch_status_v1.json')
    assert decision['current_constructor_candidate_admissible'] is False
    assert decision['failed_owner_resource_release_proved'] is False
    assert launch['planned_H1_diagnostic_launched'] is launch['H1_diagnostic_launch_admitted'] is False
    review=load(HERE/'preseal_review_summary.json')
    assert review['official_review'] is False and review['remaining_component_findings']==[]
    task_files=[REPO/'experiments/h1_constructor_rejection_support_development_v1.py',
        REPO/'tests/test_h1_constructor_rejection_support_development_v1.py',
        REPO/'tests/test_h1_source_callable_gap_development_v1.py']
    for path in task_files+[HERE/name for name in ('build_status_v1.py','inventory_globals_v1.py','verify_final_v1.py')]:
        ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
    bindings=dict(prior['bindings']);bindings[str(prior_path)]=pin(prior_path)
    for path in HERE.rglob('*'):
        if path.is_file() and path.name not in ('development_acceptance_v1.json','final_verification.json'):
            bindings[str(path)]=pin(path)
    bindings.update({str(path):pin(path) for path in task_files})
    assert all(pin(p)==v for p,v in bindings.items())
    core=dict(status='DRAFT_NONAUTHORITATIVE',scope='detached_constructor_rejection_and_namespace_support',
        bindings=bindings,latest_unit='unit_06',latest_unit_junit=latest['junit'],
        current_live_after_pins_verified=18,explicit_tested_snapshots_verified=18,
        attempts=attempts,preserved_review_files=8,prior_archive_final_bindings_verified=809,
        original_frozen_parent_and_driver_code_objects_equal=True,
        budget_state_reports_rebuilt_identical=True,current_constructor_candidate_admissible=False,
        source_successor_adopted=False,failed_owner_resource_release_proved=False,
        complete_dynamic_dependency_closure_proved=False,full_saved_reader_executed=False,
        H1_diagnostic_launched=False,saved_case_files=465,saved_owned_files=444,
        old_case_names_and_sha256_unchanged=True,open_preparation_gates=16,
        objective_complete=False,overall_performance_review_complete=False,long_connected_launch_admitted=False,
        resource_admission=False,formal_execution_ready=False,full_192_hour_execution_verified=False,
        native_execution_authorized=False,sealed=False,independent_official_review_performed=False,
        new_normal_jobs=0,real_native_calls=0,formal_result=False)
    core_path=HERE/'development_acceptance_v1.json';save(core_path,core)
    final_bindings=dict(bindings);final_bindings[str(core_path)]=pin(core_path)
    final=dict(status='DRAFT_NONAUTHORITATIVE',latest_core=str(core_path),latest_core_sha256=pin(core_path),
        core_bindings_verified=len(bindings),bindings=final_bindings,
        source_successor_adopted=False,current_constructor_candidate_admissible=False,
        open_preparation_gates=16,objective_complete=False,overall_performance_review_complete=False,
        resource_admission=False,formal_execution_ready=False,full_192_hour_execution_verified=False,
        native_execution_authorized=False,independent_official_review_performed=False,sealed=False,
        new_normal_jobs=0,real_native_calls=0,formal_result=False)
    save(HERE/'final_verification.json',final)
    print(json.dumps(dict(core_bindings=len(bindings),final_bindings=len(final_bindings),
        core_sha256=pin(core_path),final_sha256=pin(HERE/'final_verification.json'),open_gates=16)))


if __name__=='__main__':main()
