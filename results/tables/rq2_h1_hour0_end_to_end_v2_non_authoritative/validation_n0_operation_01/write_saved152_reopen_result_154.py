"""Bind the successful read-only owner separately from152's stopped producer."""
from hashlib import sha256
import json
import os
from pathlib import Path

HERE=Path(__file__).resolve().parent;D=HERE/'whole_workflow_optimization_01_non_authoritative'
plan_path=D/'saved152_readonly_reopen_plan_154.json';plan=json.loads(plan_path.read_bytes())
terminal_path=HERE/'saved152_readonly_reopen_154/terminal.json';terminal=json.loads(terminal_path.read_bytes())
drift=[p for p,pin in plan['files_sha256'].items() if sha256(Path(p).read_bytes()).hexdigest()!=pin]
assert not drift and terminal['exit_code']==0 and terminal['source_unchanged']
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors']
base=Path('D:/h1_saved152_reopen_154_non_authoritative')
path=next(base.glob('*/saved152_readonly_reopen.json'));reopen=json.loads(path.read_bytes())
entry_path=base/'unit_code_read_lease_closed.json';entry=json.loads(entry_path.read_bytes())
assert reopen['read_only_reopen_state_verified'] and reopen['new_read_only_owner_closed']
assert not reopen['original_public_bootstrap_return_verified'] and not reopen['original_operation_graceful_cleanup_proven']
assert reopen['inspection']['state']=='pending_post_N' and not entry['diagnostic_validation_errors']
assert all(entry[key] for key in ('all_path_handles_closed','canonical_path_alias_restored',
    'all_code_handles_closed','original_read_alias_restored','all_metadata_handles_closed',
    'original_metadata_version_alias_restored'))
saved=Path('D:/h1_bootstrap5_retained_152_non_authoritative')
expected={Path(p) for p in plan['files_sha256'] if Path(p).is_relative_to(saved)}
pending=[saved];actual=set();directories=[]
while pending:
    directory=pending.pop();directories.append(str(directory))
    for row in os.scandir(directory):
        info=row.stat(follow_symlinks=False);assert not info.st_file_attributes&0x400
        if row.is_dir(follow_symlinks=False):
            if row.name!='scratch_non_authoritative':pending.append(Path(row.path))
        else:actual.add(Path(row.path))
    assert len(actual)<=2048
assert actual==expected
archive=D/'saved152_reopen_154_preserved_non_authoritative';archive.mkdir(exist_ok=False);pins={}
sources=[path,entry_path,path.parent/'saved152_readonly_inspection.json',path.parent/'saved_reopen_timing.jsonl',
         path.parent/'identity_bookends.json',HERE/'saved152_readonly_reopen_154/stdout.log',terminal_path]
for source in sources:
    raw=source.read_bytes();target=archive/source.name
    with target.open('xb') as stream:stream.write(raw)
    assert source.read_bytes()==target.read_bytes()==raw
    pins[str(target)]=sha256(raw).hexdigest()
value=dict(schema='h1_saved152_readonly_reopen_result_154',status='VERIFIED_READONLY_REOPEN_AND_NEW_OWNER_CLOSE',
    plan_sha256=sha256(plan_path.read_bytes()).hexdigest(),terminal=terminal,
    planned_pins=len(plan['files_sha256']),pin_drift=drift,archive_files_sha256=pins,
    saved_input_files=len(expected),saved_file_inventory_unchanged=True,
    new_saved_files=[],missing_saved_files=[],empty_directory_preinventory_not_recorded=True,
    inspection=reopen['inspection'],reopen=reopen,entry_closed=entry,
    static_call_model=plan['static_call_model'],observed_full_prepare_counts_available=False,
    original152_public_bootstrap_return_verified=False,original152_graceful_cleanup_proven=False,
    new_readonly_owner_reopen_verified=True,new_readonly_owner_closed=True,
    original_numerical_oracle_result_sha256=sha256((D/'saved152_numerical_postcheck_result_153.json').read_bytes()).hexdigest(),
    new_N0_Jobs=0,real_native_calls=0,full_optimized_workflow_accepted=False,
    whole_workflow_performance_review_complete=False,formal_result=False,formal_execution_ready=False,
    resource_admission=False,native_execution_authorized=False)
target=D/'saved152_readonly_reopen_result_154.json'
with target.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(target),sha256=sha256(target.read_bytes()).hexdigest(),pins=len(plan['files_sha256']),
    drift=drift,saved_files=len(expected),segments=reopen['receipt']['segments_opened'],
    elapsed=terminal['elapsed_seconds'],new_jobs=0)))
