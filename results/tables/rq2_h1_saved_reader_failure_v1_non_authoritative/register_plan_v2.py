"""Fixed bounded failure package and exact evidence reuse, not run authority."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def load(path):return json.loads(Path(path).read_bytes())
def pin(path):return sha256(Path(path).read_bytes()).hexdigest()


def main():
    support=load(HERE/'support_04/terminal.json')
    assert support['exit_code']==0 and support['changed']==[] and support['source_before']==support['source_after']
    assert all(pin(path)==value for path,value in support['source_after'].items())
    prior=HERE.parent/'rq2_h1_source_post_validation_v3_non_authoritative/final_verification.json'
    inherited=load(prior)['bindings']
    assert len(inherited)==2483 and all(pin(path)==value for path,value in inherited.items())
    spec=importlib.util.spec_from_file_location('saved_failure_plan',HERE/'fault_worker_v1.py')
    worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
    rows=[]
    for case in worker.CASES:
        H=2 if case=='unselected_packet_drift' else 1
        complete=0 if case.startswith('constructor_') else H
        phase=('actual three inner/four outer acquired, before first inspect; explicit independent guard call after drift'
            if case.startswith('constructor_') else 'after constructor, before capture take' if case=='post_constructor_primary'
            else 'all-H entry before validation of unselected hour0' if case=='unselected_packet_drift'
            else 'all-H returned; final unchanged(views) read denied' if case=='final_read_sharing_error'
            else 'third namespace round, first root; root inventory ordinal7')
        rows.append(dict(case=case,completed_prefix_hours=H,selected_hours=[H-1],
            expected_completed_numeric_hours=complete,
            expected_runtime_counts=dict(job_inspections=2*complete,stage_inspections=10*complete,normal_after_returns=complete),
            injection_phase=phase,expected_inner_objects=3,expected_outer_ReadViews=4,
            inner_close_order=['_journal','_anchor','_root_lease'],outer_close_order=[3,2,1,0],
            private_containers_checked=['captured','all_packets','seen_hours'],
            namespace_round_expected=(1 if case.startswith('constructor_') or case=='post_constructor_primary' else 2 if case!='final_namespace_read_result' else 3),
            physical_content_mutation=False,
            in_memory_reflection=case=='unselected_packet_drift',
            namespace_read_result_seam=case=='final_namespace_read_result',
            temporary_read_only_sharing_handle=case=='final_read_sharing_error'))
    assert sum(row['expected_completed_numeric_hours'] for row in rows)==5
    paths=[Path(__file__),HERE/'fault_worker_v1.py',HERE/'run_faults_v1.py',
        HERE/'design_and_budget.md',HERE/'test_probe_support_v1.py',
        HERE/'support_04/request.json',HERE/'support_04/terminal.json',HERE/'support_04/pytest.xml',
        REPO/'agent.md',REPO/'AGENTS.md',
        HERE.parent/'rq2_h1_source_replay_cost_v1_non_authoritative/profile_saved_v1.py']
    plan=dict(status='DRAFT_NONAUTHORITATIVE',risk='R3',sole_writer='root',
        scope='nine fresh-process single-saved-Reader failure cases',cases=rows,
        maximum_Reader_invocations=9,maximum_completed_numeric_prefix_hours=5,
        derived_maximum_saved_job_inspections=10,derived_maximum_M5_stage_inspections=50,
        no_native_solver_or_new_source_Job=True,whole_suite_wall_limit_seconds=240,
        per_case_wall_limit_seconds=90,no_case_read_activity_limit_seconds=60,
        owned_tree_sampled_rss_limit_bytes=768*1024**2,output_logical_limit_bytes=64*1024**2,
        sample_seconds=2,heartbeat_seconds=30,stop_on_first_failed_case=True,automatic_retry=False,
        sharing_target=str(worker.CASE/'normal_non_authoritative/obligation_non_authoritative/000.terminal.json'),
        sharing_parameters=dict(desired_access='GENERIC_READ',share_mode=0,creation='OPEN_EXISTING',
            expected_native_conflict_error=32,expected_Python_error='PermissionError errno13'),
        observations_are_identity_ReadViews_not_OS_writer_leases=True,
        diagnostic_holds_only_selected_refs_and_exception_until_report=True,
        no_frame_locals_or_raw_scientific_payload_dumped=True,
        prior_final_path=str(prior),prior_final_sha256=pin(prior),inherited_bindings=inherited,
        source_sha256={str(path):pin(path) for path in paths},
        source_successor_adopted=False,overall_performance_review_complete=False,
        long_connected_launch_admitted=False,resource_admission=False,formal_execution_ready=False,
        full_192_hour_execution_verified=False,formal_result=False,native_execution_authorized=False)
    with (HERE/'plan_v2.json').open('x',encoding='utf-8') as stream:
        json.dump(plan,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(cases=len(rows),completed_numeric_prefix_hours=5,inherited_bindings=2483,
        registered=True,normal_jobs=0,native_solver_calls=0)))


if __name__=='__main__':main()
