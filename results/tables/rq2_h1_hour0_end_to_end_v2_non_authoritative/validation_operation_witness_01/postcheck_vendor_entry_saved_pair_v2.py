"""Verify the completed combined-entry comparison and fresh saved/source bytes."""
from hashlib import sha256
import json
import msvcrt
import os
import sys
from pathlib import Path
import psutil

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
P=HERE.parent/'validation_path_optimization_01'


def read(path):return json.loads(path.read_bytes())
def digest(path):return sha256(path.read_bytes()).hexdigest()


pins={}
def bind(path):pins[str(path)]=digest(path)


plan=read(HERE/'vendor_code_entry_plan_05.json')
inputs=read(HERE/'vendor_saved_arm_inputs_02.json')
assert digest(HERE/'vendor_code_entry_plan_05.json')==inputs['plan_sha256']
assert digest(P/'entry_revision_07/package_manifest_v1.json')==plan['package_manifest_sha256']
assert digest(P/plan['monitor'])==plan['monitor_sha256']
assert plan['predecessor_package_manifest_sha256']=='6c0db76dd3bbcfb8281e69d7ad70cc18caaf7adef4d120c0aebb30bbcedef03d'
for name,pin in inputs['source_sha256'].items():assert digest(Path(name))==pin
assert read(HERE/'vendor_saved_pair_postcheck_01_tool_terminal.json')['exit_code']==0
rows=[]
for entry_name,outer_name in (
        ('entry_revision_06','configured_entry_06_vendor_saved_arm_monitor_01'),
        ('entry_revision_07','configured_entry_07_vendor_saved_arm_monitor_01')):
    entry=P/entry_name;root=P/outer_name;inner=entry/'vendor_saved_arm_01'
    request,outer,terminal=read(root/'request.json'),read(root/'terminal.json'),read(inner/'terminal.json')
    inner_request=read(inner/'request.json')
    expected_manifest=(plan['predecessor_package_manifest_sha256'] if entry_name=='entry_revision_06'
        else plan['package_manifest_sha256'])
    assert digest(entry/'package_manifest_v1.json')==expected_manifest
    assert inner_request['package_manifest_sha256']==expected_manifest
    assert inner_request['active_validation_identity']['package_manifest_sha256']==expected_manifest
    assert inner_request['kind']=='arm' and inner_request['mode']=='parse' and inner_request['targets']==[]
    assert inner_request['launcher_sha256']==digest(entry/'launch_validation.py')
    assert request['runner_sha256']==plan['monitor_sha256']
    assert request['command']==[str(Path(sys.executable)),'-B','-I',
        (entry/'launch_validation.py').relative_to(REPO).as_posix(),'arm','parse','vendor_saved_arm_01']
    assert request['seconds']==120 and request['sampled_rss_cap_bytes']==512*1024**2 and request['storage_cap_bytes']==64*1024**2
    assert request['storage_roots']==[str(root),str(inner)]
    assert outer['exit_code']==terminal['exit_code']==0 and outer['stop_reason'] is None
    assert outer['source_unchanged'] and outer['source_snapshot_complete']
    assert outer['final_storage_observation_complete'] and not outer['storage_read_errors']
    assert not outer['cleanup_errors'] and outer['observed_owned_processes_absent']
    assert not outer['complete_process_tree_absence_proven']
    assert outer['observed_storage_bytes']==sum(path.stat().st_size for name in request['storage_roots']
        for path in Path(name).rglob('*') if path.is_file())
    assert outer['elapsed_seconds']<120 and outer['peak_observed_process_tree_rss']<512*1024**2
    assert outer['observed_storage_bytes']<64*1024**2
    for name,pin in request['source_sha256'].items():
        path=Path(name)
        snapshot=(root/'tested_bytes'/path.relative_to(REPO) if path.is_relative_to(REPO)
            else root/'tested_bytes/external'/path.drive[:1]/Path(*path.parts[1:]))
        assert digest(path)==pin and digest(snapshot)==pin
    for row in outer['observed_owned_processes']:
        try:
            process=psutil.Process(row['pid'])
            assert process.create_time()!=row['creation_time'] or not process.is_running()
        except psutil.NoSuchProcess:pass
    assert all(terminal[key] for key in ('saved_files_unchanged','candidate_bytes_unchanged',
        'repository_code_unchanged','repository_test_closure_unchanged','interpreter_settings_restored',
        'scientific_payload_and_projected_audit_equal_saved'))
    assert terminal['saved_file_count']==461 and terminal['real_native_calls']==0
    assert terminal['repository_code_file_count']==149 and terminal['repository_test_closure_file_count']==614
    lease=read(inner/'lease_receipt.json')
    if entry_name=='entry_revision_07':
        assert terminal['vendor_code_unchanged'] and terminal['vendor_code_file_count']==7
        assert lease['file_count']==156 and len(lease['vendor_module_origins'])==7
        assert terminal['vendor_module_origins_at_exit']==lease['vendor_module_origins']
        vendor=read(entry/'vendor_code_allowlist_v1.json')['files_sha256']
        for name,pin in vendor.items():
            assert lease['files_sha256'][name]==pin
            assert lease['hits_by_path'].get(os.path.normcase(name),0)>0
            path=Path(name);relative=path.relative_to(Path(read(entry/'vendor_code_allowlist_v1.json')['root']))
            assert digest(inner/'tested_bytes/vendor_code/pyomo'/relative)==pin
    else:assert lease['file_count']==149
    for path in (root/'request.json',root/'started.json',root/'terminal.json',inner/'request.json',
            inner/'terminal.json',inner/'scientific.json',inner/'audit.json',inner/'lease_receipt.json',inner/'metadata_receipt.json'):
        bind(path)
    rows.append(dict(entry=entry_name,arm_seconds=terminal['arm_seconds'],inner_elapsed_seconds=terminal['elapsed_seconds'],
        outer_elapsed_seconds=outer['elapsed_seconds'],sampled_peak_rss_bytes=outer['peak_observed_process_tree_rss'],
        final_storage_bytes=outer['observed_storage_bytes'],source_and_tested_copies=len(request['source_sha256']),
        code_lease_files=lease['file_count'],observed_owned_pids_absent=True))
for name in ('scientific.json','audit.json','metadata_receipt.json'):
    assert (P/'entry_revision_06/vendor_saved_arm_01'/name).read_bytes()==(P/'entry_revision_07/vendor_saved_arm_01'/name).read_bytes()
for name,pin in inputs['saved_files_sha256'].items():assert digest(Path(name))==pin
locks=sorted(Path(name) for name in inputs['saved_files_sha256'] if Path(name).name=='execution.lock')
assert len(locks)==33
for path in locks:
    before=path.read_bytes()
    with path.open('r+b') as stream:
        stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        try:pass
        finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
    assert path.read_bytes()==before
for name,pin in inputs['saved_files_sha256'].items():assert digest(Path(name))==pin
for name,pin in inputs['old_chain_07_inputs'].items():assert digest(Path(name))==pin
unit=read(P/'entry_revision_07/unit_checks_09/terminal.json')
assert unit['exit_code']==0 and unit['tests_run']==94 and unit['skipped']==1 and unit['failures']==unit['errors']==0
for path in (Path(__file__),HERE/'vendor_code_entry_plan_05.json',HERE/'vendor_saved_arm_inputs_02.json',
        HERE/'vendor_code_entry_preseal_summary_01.json',HERE/'vendor_monitor_admission_checks_01/result.json',
        P/'entry_revision_07/package_manifest_v1.json',P/'entry_revision_07/unit_checks_09/terminal.json',
        P/'configured_entry_07_unit_monitor_04/terminal.json',P/plan['monitor'],
        HERE/'vendor_saved_baseline_tool_terminal.json',HERE/'vendor_saved_candidate_tool_terminal.json',
        HERE/'vendor_saved_pair_postcheck_01_tool_terminal.json'):
    bind(path)
assert read(HERE/'vendor_saved_baseline_tool_terminal.json')['exit_code']==0
assert read(HERE/'vendor_saved_candidate_tool_terminal.json')['exit_code']==0
gain=1-rows[1]['arm_seconds']/rows[0]['arm_seconds']
result=dict(status='COMBINED_ENTRY_SAVED_ARM_COMPARISON_COMPLETE',rows=rows,
    scientific_payload_and_full_audit_exact_equal=True,metadata_receipts_exact_equal=True,exact_entry_roles_and_manifests_verified=True,saved_files_fresh_unchanged=461,
    saved_locks_reacquired_and_released=33,old_chain_inputs_fresh_unchanged=36,
    arm_reduction_fraction=gain,outer_total_reduction_fraction=1-rows[1]['outer_elapsed_seconds']/rows[0]['outer_elapsed_seconds'],
    decision='retain_for_followup_diagnostics' if gain>0 else 'do_not_integrate_slower_successor',
    attribution='one pair measures the combined entry successor, including earlier code-lease lifetime; isolated seven-file evidence is identity micro only',
    effect_uncertainty='one pair; concurrent unchanged chain07; no complete N0/common/Genesis/Rref/Actual/commit/reopen measurement',
    complete_process_tree_absence_proven=False,files_sha256=pins,real_native_calls=0,
    full_hour0_chain_passed=False,full_chain_performance_review_complete=False,official_review_verdict=None,
    formal_execution_ready=False,formal_result=False,resource_admission=False,native_execution_authorized=False)
out=HERE/'vendor_saved_arm_comparison_02.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(result,stream,indent=2)
print(json.dumps(dict(output=str(out),rows=rows,arm_reduction_fraction=gain,decision=result['decision'],
    scientific_payload_and_full_audit_exact_equal=True,saved_files=461,locks=33)),flush=True)
