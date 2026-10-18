"""Close the saved-arm comparison with current pins, full bytes and real lock checks."""
from hashlib import sha256
import json
import msvcrt
from pathlib import Path
import psutil

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
ENTRY=HERE.parent/'validation_path_optimization_01/entry_revision_07'
plan=json.loads((HERE/'bounded_common_arm_plan_04.json').read_bytes())
outer=HERE/'bounded_common_arm_monitor_03'
inner=HERE/'bounded_common_arm_03_non_authoritative'
out=HERE/'common_entry_postcheck_04_non_authoritative'
out.mkdir(exist_ok=False)

def digest(path):return sha256(path.read_bytes()).hexdigest()

terminal=json.loads((outer/'terminal.json').read_bytes())
assert terminal['exit_code']==terminal['inner_exit_code']==terminal['child_exit_code']==0
assert terminal['source_unchanged'] and terminal['old_chain_unchanged']
assert terminal['observed_owned_processes_absent'] and not terminal['errors']
for item in terminal['observed_owned_processes']:
    try:
        process=psutil.Process(item['pid'])
        assert process.create_time()!=item['creation_time'] or not process.is_running()
    except psutil.NoSuchProcess:pass
for path,pin in {**plan['source_sha256'],**plan['old_chain_sha256']}.items():
    assert digest(Path(path))==pin
for name,pin in plan['source_sha256'].items():
    path=Path(name)
    relative=path.relative_to(REPO) if path.is_relative_to(REPO) else Path('vendor')/path.relative_to(Path('D:/'))
    assert digest(outer/'tested_bytes'/relative)==pin
saved=Path(plan['saved_root'])
actual={str(p):digest(p) for p in saved.rglob('*') if p.is_file()}
assert actual==plan['saved_sha256'] and len(actual)==461
locks=[]
for path in sorted(saved.rglob('*.lock')):
    with path.open('r+b',buffering=0) as stream:
        stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        try:locks.append(str(path))
        finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
assert len(locks)==33
assert {str(p):digest(p) for p in saved.rglob('*') if p.is_file()}==actual
for name in ('scientific.json','audit.json'):
    assert (inner/name).read_bytes()==(ENTRY/'vendor_saved_arm_01'/name).read_bytes()
closed=json.loads((inner/'bounded_closed_receipt.json').read_bytes())
assert closed['code_owner_closed'] and closed['path_open_restored'] and closed['path_read_bytes_restored']
assert closed['remaining_code_handles']==closed['remaining_streams']==closed['remaining_proxies']==0
assert not closed['cleanup_errors'] and closed['first_failure'] is None
parsed=json.loads((inner/'metadata_receipt.json').read_bytes())
assert parsed['hits']==7265 and parsed['misses']==0
path_closed=json.loads((inner/'path_closed_receipt.json').read_bytes())
assert path_closed==dict(dispatch_restored=True,remaining_directory_handles=0,remaining_paths=0,state='closed')
path_execution=json.loads((inner/'path_receipt.json').read_bytes())
assert path_execution['hits']==3421 and path_execution['canonical_paths']==36
assert path_execution['leaf_lstat_fresh'] and path_execution['ancestor_reparse_and_case_flags_fresh']
prior_current=json.loads((HERE/'bounded_common_arm_02_non_authoritative/terminal.json').read_bytes())
measured=json.loads((inner/'terminal.json').read_bytes())
broken=json.loads((HERE/'bounded_common_arm_01_non_authoritative/terminal.json').read_bytes())
baseline=json.loads((ENTRY/'vendor_saved_arm_01/terminal.json').read_bytes())
value=dict(exit_code=0,status='DRAFT_NONAUTHORITATIVE',
    script_sha256=digest(Path(__file__)),sources_and_tested_bytes=len(plan['source_sha256']),
    saved_files_unchanged=len(actual),saved_locks_reacquired_and_released=locks,
    old_chain_pins_unchanged=len(plan['old_chain_sha256']),observed_owned_processes_absent=True,
    science_and_full_audit_exact_equal=True,metadata_hits=parsed['hits'],metadata_misses=parsed['misses'],
    hook_and_resource_cleanup_verified=True,path_hook_and_resources_closed=True,
    canonical_path_hits=path_execution['hits'],
    seconds=dict(historical_entry07=baseline['arm_seconds'],broken_metadata_window=broken['arm_seconds'],
        corrected_metadata_window=prior_current['arm_seconds'],combined_path_entry=measured['arm_seconds']),
    reduction_vs_corrected_metadata_window=1-measured['arm_seconds']/prior_current['arm_seconds'],
    reduction_vs_broken_window=1-measured['arm_seconds']/broken['arm_seconds'],
    reduction_vs_historical_entry07=1-measured['arm_seconds']/baseline['arm_seconds'],
    evidence_scope='one saved common arm; historical baseline plus cause-specific fixed-order corrected observation',
    full_hour0_chain_passed=False,whole_workflow_performance_review_complete=False,
    resource_admission=False,formal_result=False,native_execution_authorized=False)
with (out/'terminal.json').open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps({k:v for k,v in value.items() if k!='saved_locks_reacquired_and_released'}))
