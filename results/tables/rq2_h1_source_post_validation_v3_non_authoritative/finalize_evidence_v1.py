"""Exact draft evidence checkpoint; no production seal or review receipt."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import os
import subprocess

import psutil

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def load(path):return json.loads(Path(path).read_bytes())
def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def save(name,value):
    with (HERE/name).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2);stream.write('\n')


def main():
    post=load(HERE/'postcheck_v1.json')
    budget=load(HERE/'whole_workflow_budget_v7.json')
    state=load(HERE/'formal_preparation_state_v7.json')
    reconciliation=load(HERE/'metadata_reconciliation_v1.json')
    assert all(pin(path)==value for path,value in reconciliation['after'].items())
    assert len(state['gates'])==16 and all(gate['complete'] is False for gate in state['gates'])
    assert state['current_episode_scaling']['conditional_unadopted_source_v3']==budget['target_work_units']['192']['conditional_unadopted_source_v3']
    assert state['current_whole_workflow_budget']['sha256']==pin(HERE/'whole_workflow_budget_v7.json')
    source_paths=[REPO/name for name in (
        'experiments/h1_constructor_runtime_guard_development_v1.py',
        'experiments/h1_phase_historical_batch_development_v3.py',
        'experiments/h1_phase_exact_source_batch_development_v3.py',
        'experiments/h1_constructor_source_batch_validation_development_v2.py',
        'tests/test_h1_source_post_validation_development_v3.py',
    )]+list(HERE.glob('*.py'))
    for path in source_paths:
        text=path.read_text(encoding='utf-8');ast.parse(text,filename=str(path))
        assert all(line==line.rstrip() for line in text.splitlines())
    check=subprocess.run(['git','diff','--check'],cwd=REPO,capture_output=True,text=True)
    assert check.returncode==0
    status=subprocess.check_output(['git','status','--porcelain=v1','-z'],cwd=REPO)
    (HERE/'workspace_status_v1.bin').write_bytes(status)
    related=[]
    for item in psutil.process_iter(['pid','name','cmdline','create_time']):
        try:
            info=item.info
            if item.pid!=os.getpid() and any(word in (info['name'] or '').lower()
                    for word in ('python','gurobi','cplex','ipopt','highs')):
                related.append(info)
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    save('workspace_checkpoint_v1.json',dict(status='DRAFT_NONAUTHORITATIVE',
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        status_file='workspace_status_v1.bin',status_sha256=pin(HERE/'workspace_status_v1.bin'),
        worktree_clean=not status,related_processes=related,self_checker_pid=os.getpid(),
        git_diff_check_exit=check.returncode,python_sources_parsed=len(source_paths),
        git_commit_or_push_performed=False,canonical_plan_blocker_preserved=True,
        no_current_owned_probe_process=True,new_normal_jobs=0,real_native_calls=0))
    save('preseal_report_reconciliation_v1.json',dict(status='DRAFT_NONAUTHORITATIVE',
        review_kind='read_only_non_authoritative_PRE_SEAL_findings',reviewer='/root/phase_budget_review',
        metadata_findings_reconciled=True,new_concrete_contradiction_identified=False,
        reviewed_sha256={str(HERE/name):pin(HERE/name) for name in (
            'whole_workflow_budget_v7.json','formal_preparation_state_v7.json','acceptance_report.md',
            'continuation_handoff_20261021.md','postcheck_v1.json','source_adoption_decision_v3.json')},
        review_scope='finite diagnostic evidence, cost arithmetic, provenance and limits',
        official_verdict_issued=False,official_receipt_created=False,formal_gate_changes=[],
        terminal_event_suggestion_withdrawn_after_original_code_and_enumeration_check=True,
        evidence_limits=['dynamic closure and private checker reflection','unobserved ABA',
            'real saved Reader file/owner failure matrix','M232/H192 retention',
            'aggregate wall/RSS/physical storage','owner integration/failure/terminal/reopen',
            'source-connected H168/F<=24 and formal authority']))
    bindings={}
    def merge(mapping):
        for name,value in mapping.items():
            if name in bindings and bindings[name]!=value:
                raise ValueError('conflicting current evidence binding: '+name)
            if pin(name)!=value:raise ValueError('current evidence changed: '+name)
            bindings[name]=value
    for record in (post,budget,state):merge(record['bindings'])
    for path in HERE.rglob('*'):
        if path.is_file() and path.name not in ('development_acceptance_v1.json','final_verification.json'):
            merge({str(path):pin(path)})
    for path in source_paths:merge({str(path):pin(path)})
    total=len(bindings)
    save('development_acceptance_v1.json',dict(status='DRAFT_NONAUTHORITATIVE',
        scope='PRE_SEAL evidence checkpoint; not production seal or official review',
        bindings=bindings,bindings_verified=total,unit_tests=294,saved_detached_rejection_cases=21,
        prior_950_bindings_preserved=True,saved_case_files_unchanged=465,owned_pins_unchanged=444,
        launch_pins_unchanged=1322,postcheck_fresh_bindings=2261,
        saved_H3_dual_Reader_completed=True,source_v3_owner_adopted=False,
        normal_native_calls=0,new_normal_jobs=0,remaining_open_gates=16,
        total_wall_admission_seconds=None,peak_rss_admission_bytes=None,total_storage_admission_bytes=None,
        overall_performance_review_complete=False,long_connected_launch_admitted=False,
        resource_admission=False,formal_execution_ready=False,formal_result=False,
        full_192_hour_execution_verified=False,native_execution_authorized=False))
    core=HERE/'development_acceptance_v1.json'
    bindings[str(core)]=pin(core)
    assert all(pin(name)==value for name,value in bindings.items())
    save('final_verification.json',dict(status='DRAFT_NONAUTHORITATIVE',latest_core=str(core),
        latest_core_sha256=pin(core),core_bindings_verified=total,bindings=bindings,
        implementation_matches_unit_07_and_saved_probe=True,
        source_successor_adopted=False,overall_performance_review_complete=False,
        resource_admission=False,formal_execution_ready=False,formal_result=False,
        full_192_hour_execution_verified=False,native_execution_authorized=False,
        official_verdict_or_run_authority=False))
    print(json.dumps(dict(core_bindings=total,final_bindings=len(bindings),
        core_sha256=pin(core),final_sha256=pin(HERE/'final_verification.json'),
        related_processes=related,worktree_clean=not status,formal_ready=False)))


if __name__=='__main__':main()
