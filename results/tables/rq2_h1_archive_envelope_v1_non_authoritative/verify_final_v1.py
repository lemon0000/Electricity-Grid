"""Verify exact development bytes and preserve a non-authoritative checkpoint."""
import ast
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

import psutil

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def save(path,value):
    raw=(json.dumps(value,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode('utf-8')
    if path.exists():assert path.read_bytes()==raw,('existing checkpoint differs',str(path))
    else:
        with path.open('xb') as stream:stream.write(raw)


def main():
    audit_path=HERE/'archive_audit_v2.json';audit=load(audit_path)
    assert all(pin(name)==value for name,value in audit['bindings'].items())
    assert audit['old_holder']['final_owner_and_holder_heads_equal_external_preclose_checkpoint'] is True
    unit=load(HERE/'unit_02/terminal.json')
    assert unit['exit_code']==0 and unit['changed_code']==[]
    assert unit['junit']==dict(tests=38,failures=0,errors=0,skipped=0)
    assert len(unit['code_bindings_before'])==len(unit['explicit_tested_snapshots'])==8
    assert all(pin(name)==value for name,value in unit['code_bindings_before'].items())
    assert all(pin(name)==value for name,value in unit['explicit_tested_snapshots'].items())
    for path,value in unit['code_bindings_before'].items():
        assert pin(HERE/'unit_02/tested_bytes'/Path(path).name)==value
    observed=load(HERE/'audit_03/terminal.json')
    assert observed['exit_code']==0 and observed['changed_code']==[]
    assert len(observed['code_bindings_before'])==4
    for path,value in observed['code_bindings_before'].items():
        assert pin(path)==pin(HERE/'audit_03'/Path(path).name)==value
    for attempt in ('audit_01','audit_02'):
        old=load(HERE/attempt/'terminal.json')
        assert old['changed_code']==[]
        for path,value in old['code_bindings_before'].items():
            assert pin(HERE/attempt/Path(path).name)==value
    preserved=load(HERE/'before_review_01/snapshot_bindings.json')
    assert len(preserved)==9 and all(pin(path)==value for path,value in preserved.items())
    outputs=[HERE/name for name in ('whole_workflow_budget_v5.json','formal_preparation_state_v5.json',
        'acceptance_report.md','continuation_handoff_20261021.md')]
    before={str(path):pin(path) for path in outputs}
    rebuilt=subprocess.run([sys.executable,'-B',str(HERE/'build_status_v1.py')],cwd=REPO,
        text=True,capture_output=True,encoding='utf-8',timeout=30)
    assert rebuilt.returncode==0,rebuilt.stderr
    assert all(pin(path)==value for path,value in before.items())
    state=load(HERE/'formal_preparation_state_v5.json')
    assert len(state['gates'])==16 and all(g['complete'] is False for g in state['gates'])
    assert all(pin(path)==value for path,value in state['bindings'].items())
    budget=load(HERE/'whole_workflow_budget_v5.json')
    assert all(pin(path)==value for path,value in budget['bindings'].items())
    assert budget['overall_performance_review_complete'] is False
    for target in budget['target_work_units'].values():
        assert all(target[key] is None for key in ('total_wall_admission_seconds',
            'peak_rss_admission_bytes','total_storage_admission_bytes'))
    task_files=[REPO/'experiments/h1_owner_archive_budget_development_v1.py',
        REPO/'tests/test_h1_owner_archive_budget_development_v1.py']
    current_py=[HERE/name for name in ('audit_v1.py','build_status_v1.py','verify_final_v1.py')]
    for path in task_files+current_py:ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
    related=[]
    for process in psutil.process_iter(['pid','name','cmdline','create_time']):
        try:
            if process.pid==os.getpid():continue
            name=process.info['name'] or ''
            command=' '.join(process.info['cmdline'] or [])
            if name.lower() in ('python.exe','pythonw.exe','gurobi_cl.exe','cplex.exe','ipopt.exe','highs.exe','scip.exe'):
                if 'h1_' in command or 'rq2_' in command:
                    related.append(dict(pid=process.pid,name=name,creation_time=process.info['create_time'],command=command))
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    assert not related,related
    review=load(HERE/'preseal_review_summary.json')
    assert review['status']=='NONAUTHORITATIVE_PRE_SEAL_FINDINGS_ONLY'
    assert review['remaining_concrete_findings']==[] and review['official_review'] is False
    bindings=dict(audit['bindings']);bindings[str(audit_path)]=pin(audit_path)
    for path in HERE.rglob('*'):
        if path.is_file() and path.name not in ('development_acceptance_v1.json','final_verification.json'):
            bindings[str(path)]=pin(path)
    bindings.update({str(path):pin(path) for path in task_files})
    assert all(pin(path)==value for path,value in bindings.items())
    core=dict(status='DRAFT_NONAUTHORITATIVE',scope='archive_logical_envelopes_and_budget_reconciliation',
        bindings=bindings,latest_audit=str(audit_path),latest_audit_sha256=pin(audit_path),
        prior_constructor_bindings_verified=208,prior_business_bindings_verified=69,
        saved_case_files=465,saved_owned_files=444,old_case_names_and_sha256_unchanged=True,
        external_preclose_heads_compared=True,unit_tests=38,unit_tested_byte_snapshots=8,
        unit_code_prepost_bindings=8,audit_code_prepost_bindings=4,
        budget_state_and_report_rebuilt_identical=True,open_preparation_gates=16,
        integer_and_encoding_bounds_conditionally_verified=True,
        physical_sqlite_or_filesystem_upper_bound_proved=False,
        objective_complete=False,overall_performance_review_complete=False,
        long_connected_launch_admitted=False,resource_admission=False,
        formal_execution_ready=False,full_192_hour_execution_verified=False,
        source_successor_adopted=False,native_execution_authorized=False,
        sealed=False,independent_official_review_performed=False,new_normal_jobs=0,
        real_native_calls=0,formal_result=False)
    core_path=HERE/'development_acceptance_v1.json';save(core_path,core)
    final_bindings=dict(bindings);final_bindings[str(core_path)]=pin(core_path)
    final=dict(status='DRAFT_NONAUTHORITATIVE',latest_core=str(core_path),latest_core_sha256=pin(core_path),
        core_bindings_verified=len(bindings),bindings=final_bindings,
        observed_related_processes=related,complete_unobserved_process_tree_proof=False,
        open_preparation_gates=16,objective_complete=False,
        overall_performance_review_complete=False,resource_admission=False,formal_execution_ready=False,
        full_192_hour_execution_verified=False,native_execution_authorized=False,
        independent_official_review_performed=False,sealed=False,new_normal_jobs=0,real_native_calls=0,formal_result=False)
    save(HERE/'final_verification.json',final)
    print(json.dumps(dict(core_bindings=len(bindings),final_bindings=len(final_bindings),
        core_sha256=pin(core_path),final_sha256=pin(HERE/'final_verification.json'),open_gates=16)))


if __name__=='__main__':main()
