"""Reuse eight verified cases; register one remaining saved Reader case."""
import ast
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def load(path):return json.loads(Path(path).read_bytes())
def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n')


def main():
    prior=load(HERE/'plan_v2.json')
    checked=load(HERE/'attempt01_postcheck.json')
    assert checked['accepted_case_count']==8 and checked['original_suite_accepted'] is False
    assert checked['open_case']=='final_namespace_read_result'
    original_request=load(HERE/'suite_01/request.json')
    assert all(pin(path)==value for path,value in original_request['sources_sha256'].items())
    support=load(HERE/'support_04/terminal.json')
    assert support['exit_code']==0 and support['changed']==[]
    assert support['source_before']==support['source_after']
    assert all(pin(path)==value for path,value in support['source_after'].items())
    # Exact worker, acceptance function and stop/cleanup implementation reused.
    old=(HERE/'run_faults_v1.py').read_text(encoding='utf-8')
    replacements=[("plan_path=HERE/'plan_v2.json'","plan_path=HERE/'plan_remaining_v1.json'"),
        ("non_solver_Win32_API_case='final_read_sharing_error',",
         "non_solver_Win32_API_cases=[],attempt_scope='one_remaining_namespace_case',")]
    new=old
    for before,after in replacements:
        assert new.count(before)==1
        new=new.replace(before,after)
    runner=HERE/'run_remaining_v1.py'
    with runner.open('x',encoding='utf-8') as stream:stream.write(new)
    old_ast=ast.parse(old);new_ast=ast.parse(new)
    function=lambda tree:next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='accepted_worker')
    assert ast.dump(function(old_ast))==ast.dump(function(new_ast))
    inherited=dict(original_request['sources_sha256'])
    for root in (HERE/'suite_01',HERE/'support_04'):
        for path in root.rglob('*'):
            if path.is_file():inherited[str(path)]=pin(path)
    paths=[Path(__file__),runner,HERE/'postcheck_attempt01_v1.py',HERE/'attempt01_postcheck.json',
           HERE/'remaining_design_v1.md',HERE/'preseal_findings_attempt01.json']
    row=next(case for case in prior['cases'] if case['case']=='final_namespace_read_result')
    plan=dict(status='DRAFT_NONAUTHORITATIVE',risk='R3',sole_writer='root',
        scope='single remaining case with exact v1 worker; original failed suite immutable',
        cases=[row],maximum_Reader_invocations=1,maximum_completed_numeric_prefix_hours=1,
        derived_maximum_saved_job_inspections=2,derived_maximum_M5_stage_inspections=10,
        whole_suite_wall_limit_seconds=90,per_case_wall_limit_seconds=90,
        no_case_read_activity_limit_seconds=60,owned_tree_sampled_rss_limit_bytes=768*1024**2,
        output_logical_limit_bytes=64*1024**2,sample_seconds=2,heartbeat_seconds=30,
        stop_on_first_failed_case=True,automatic_retry=False,
        original_suite_accepted=False,original_suite_budget_extended=False,
        original_case_definition_and_worker_bytes_changed=False,
        worker_sha256=pin(HERE/'fault_worker_v1.py'),
        accepted_evidence_reused=checked['accepted_cases'],
        last_attempt_failure_retained=str(HERE/'suite_01/09_final_namespace_read_result/terminal.json'),
        expected_wall_basis_seconds=[44.89099999999962,47.09299999999712],
        expected_wall_basis_scope='two accepted H1 late-fault cases with the same trace/profile worker; not a guaranteed upper bound',
        elapsed_stopping_is_sampled_not_absolute=True,
        inherited_bindings=inherited,source_sha256={str(path):pin(path) for path in paths},
        new_normal_jobs=0,real_native_solver_calls=0,non_solver_Win32_file_API_used=False,
        source_successor_adopted=False,overall_performance_review_complete=False,
        resource_admission=False,formal_execution_ready=False,
        full_192_hour_execution_verified=False,formal_result=False,native_execution_authorized=False)
    save(HERE/'plan_remaining_v1.json',plan)
    save(HERE/'remaining_generation_v1.json',dict(
        runner_path=str(runner),runner_sha256=pin(runner),
        source_runner_sha256=pin(HERE/'run_faults_v1.py'),replacements=replacements,
        acceptance_function_AST_unchanged=True,worker_bytes_unchanged=True,
        plan_sha256=pin(HERE/'plan_remaining_v1.json'),inherited_bindings=len(inherited),
        maximum_saved_Reader_invocations=1,formal_result=False))
    print(json.dumps(dict(registered_cases=1,whole_wall=90,per_case_wall=90,
        inherited_pins=len(inherited),worker_sha256=plan['worker_sha256'])))


if __name__=='__main__':main()
