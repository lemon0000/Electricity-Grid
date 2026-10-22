"""Preserve the draft evidence chain, including stopped attempts; no research run."""
import ast
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from xml.etree import ElementTree

import psutil

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
PRIOR=HERE.parent/'rq2_h1_source_post_validation_v3_non_authoritative'


def load(path):return json.loads(Path(path).read_bytes())
def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def save(name,value):
    with (HERE/name).open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n')


def main():
    prior=load(PRIOR/'final_verification.json')['bindings']
    assert len(prior)==2483 and all(pin(path)==value for path,value in prior.items())
    contract=load(HERE/'source_contract_reconciliation_v1.json')
    assert contract['suite_source_pins_verified']==2492 and contract['completion_source_pins_verified']==2584
    assert contract['common_source_pins']==2492 and contract['common_hash_mismatches']==0
    assert contract['added_pin_classification']==dict(original_suite_archive=77,support_archive=8,completion_execution_or_registration=7)
    requests=[load(HERE/f'{label}/request.json')['sources_sha256'] for label in ('suite_01','remaining_01')]
    assert set(requests[0])<=set(requests[1])
    assert all(requests[1][name]==value==pin(name) for name,value in requests[0].items())
    assert all(pin(name)==value for name,value in requests[1].items())
    assert load(HERE/'combination_postcheck.json')['accepted_case_actual_counters']==dict(job_inspections=10,stage_inspections=50,normal_after_returns=5)
    budget=load(HERE/'whole_workflow_budget_v8.json');old=load(PRIOR/'whole_workflow_budget_v7.json')
    assert all(budget[name]==old[name] for name in ('target_work_units','whole_study_reuse','execution_path'))
    state=load(HERE/'formal_preparation_state_v8.json')
    assert len(state['gates'])==16 and all(gate['complete'] is False for gate in state['gates'])
    assert state['formal_gate_changes']==[] and state['objective_complete'] is False
    for row in budget['target_work_units'].values():
        assert all(row[name] is None for name in ('total_wall_admission_seconds','peak_rss_admission_bytes','total_storage_admission_bytes'))
    for name in ('whole_workflow_budget_v8.json','formal_preparation_state_v8.json',
                 'saved_M232_evidence_reuse_v1.json','source_contract_reconciliation_v1.json'):
        assert all(pin(path)==value for path,value in load(HERE/name)['bindings'].items())
    support=load(HERE/'support_04/terminal.json')
    assert support['exit_code']==0 and support['changed']==[] and support['source_before']==support['source_after']
    assert all(pin(path)==value for path,value in support['source_after'].items())
    suites=list(ElementTree.parse(HERE/'support_04/pytest.xml').getroot().iter('testsuite'))
    assert sum(int(item.attrib['tests']) for item in suites)==16
    assert all(int(item.attrib[key])==0 for item in suites for key in ('failures','errors','skipped'))
    parsed=0
    for path in HERE.glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'),filename=str(path));parsed+=1
    proc=[]
    for item in psutil.process_iter(['pid','ppid','name','create_time']):
        if item.pid!=os.getpid() and re.fullmatch(r'(pythonw?|gurobi_cl|cplex|ipopt|highs|scip)(\.exe)?',item.info['name'] or '',re.I):
            proc.append(item.info)
    assert not proc,proc
    diff=subprocess.run(['git','diff','--check'],cwd=REPO,capture_output=True)
    assert diff.returncode==0,(diff.stdout,diff.stderr)
    status=subprocess.run(['git','status','--porcelain=v1','-z'],cwd=REPO,capture_output=True,check=True).stdout
    head=subprocess.run(['git','rev-parse','HEAD'],cwd=REPO,capture_output=True,text=True,check=True).stdout.strip()
    save('workspace_verification_v1.json',dict(verifier_pid=os.getpid(),other_observed_related_processes=proc,
        process_snapshot_is_not_unobserved_tree_proof=True,git_diff_check_exit=0,
        git_porcelain_v1_z_decoded=status.decode('utf-8',errors='surrogateescape'),
        head=head,worktree_clean=status==b'',commit_or_push_this_scope=False,
        Python=sys.version,psutil_version=psutil.__version__,top_level_Python_AST_files_checked=parsed,
        reused_support_tests=16,new_research_Reader_invocations=0,new_native_solver_calls=0,formal_result=False))
    pins=dict(prior)
    def merge(items):
        for name,value in items.items():
            assert name not in pins or pins[name]==value,(name,pins.get(name),value)
            pins[name]=value
    merge({str(PRIOR/'final_verification.json'):pin(PRIOR/'final_verification.json')})
    merge(requests[1]);merge(load(HERE/'saved_M232_evidence_reuse_v1.json')['bindings'])
    merge({str(path):pin(path) for path in HERE.rglob('*') if path.is_file()})
    assert all(pin(name)==value for name,value in pins.items())
    save('core_verification.json',dict(status='DRAFT_NONAUTHORITATIVE',bindings=pins,
        all_bindings_current=True,inherited_source_v3_bindings=2483,
        accepted_enumerated_fault_cases=9,original_suite_exit_code=1,
        source_contract_reconciliation='source_contract_reconciliation_v1.json',
        scope='immutable diagnostic evidence, not a production inner/outer/seal',
        formal_gate_changes=[],source_successor_adopted=False,resource_admission=False,
        formal_execution_ready=False,full_192_hour_execution_verified=False,formal_result=False))
    pins[str(HERE/'core_verification.json')]=pin(HERE/'core_verification.json')
    assert all(pin(name)==value for name,value in pins.items())
    save('final_verification.json',dict(status='DRAFT_NONAUTHORITATIVE',bindings=pins,
        bindings_count=len(pins),all_bindings_current=True,
        source_successor_adopted=False,resource_admission=False,formal_execution_ready=False,
        full_192_hour_execution_verified=False,native_execution_authorized=False,formal_result=False))
    print(json.dumps(dict(bindings=len(pins),final_sha256=pin(HERE/'final_verification.json'),
        accepted_fault_cases=9,open_formal_gates=16,git_diff_check=0,
        other_observed_related_processes=0,objective_complete=False)))


if __name__=='__main__':main()
