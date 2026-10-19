"""Preserve actual saved-data postchecks and their producer plan exception."""
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys

H=Path(__file__).resolve().parent;D=H/'whole_workflow_optimization_01_non_authoritative'
number,=sys.argv[1:]
choices={
    '176':('saved174_numerical_oracle_176',('saved174_candidate_oracle_profile.json','saved174_numerical_audit.json','saved174_numerical_oracle.prof')),
    '177':('saved174_readonly_reopen_177',('saved174_readonly_reopen.json','saved174_readonly_inspection.json','saved_reopen_timing.jsonl','saved174_consumer_read_observations.json')),
}
label,names=choices[number];base=Path('D:/h1_'+label+'_non_authoritative')
plan_path=D/('saved174_postcheck_plan_'+number+'.json');plan=json.loads(plan_path.read_bytes())
terminal=json.loads((H/label/'terminal.json').read_bytes())
assert terminal['exit_code']==0 and terminal['source_unchanged']
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors']
assert not terminal['storage_read_errors'] and terminal['final_storage_observation_complete']
drift=[p for p,pin in plan['files_sha256'].items() if sha256(Path(p).read_bytes()).hexdigest()!=pin]
assert not drift,drift
closed_path=base/'unit_code_read_lease_closed.json';closed=json.loads(closed_path.read_bytes())
for key in ('all_code_handles_closed','original_read_alias_restored','all_metadata_handles_closed',
        'original_metadata_version_alias_restored','all_path_handles_closed','canonical_path_alias_restored'):
    assert closed[key] is True
assert closed['canonical_path_state']=='closed' and closed['pending_path_handles']==0
saved=Path('D:/h1_bootstrap6_retained_174_non_authoritative');pending=[saved];actual=set()
while pending:
    directory=pending.pop()
    for entry in os.scandir(directory):
        info=entry.stat(follow_symlinks=False);assert not info.st_file_attributes&0x400
        if entry.is_dir(follow_symlinks=False):
            if entry.name!='scratch_non_authoritative':pending.append(Path(entry.path))
        else:actual.add(Path(entry.path))
expected={Path(p) for p in plan['files_sha256'] if Path(p).is_relative_to(saved)}
assert actual==expected and len(actual)==plan['saved_input_files']
paths=[closed_path];observations={}
for name in names:
    matches=list(base.glob('*/'+name));assert len(matches)==1
    paths.extend(matches)
    if name.endswith('.json'):observations[name]=json.loads(matches[0].read_bytes())
archive=D/('saved174_postcheck_'+number+'_preserved_non_authoritative');archive.mkdir(exist_ok=False)
copies=[]
for source in paths:
    target=archive/source.name;raw=source.read_bytes()
    with target.open('xb') as stream:stream.write(raw)
    assert source.read_bytes()==target.read_bytes()==raw
    copies.append(dict(source=str(source),saved=str(target),sha256=sha256(raw).hexdigest()))
stdout=(H/label/'stdout.log').read_text(encoding='utf-8');match=re.search(r'(\d+) passed in ([\d.]+)s',stdout)
assert match is not None and int(match[1])==1
if number=='176':
    observation=observations['saved174_candidate_oracle_profile.json']
    assert observation['numerical_candidate_equal_to_local_record']
    assert observation['new_N0_Jobs']==observation['real_native_calls']==0
else:
    observation=observations['saved174_readonly_reopen.json']
    assert observation['read_only_reopen_state_verified'] and observation['new_read_only_owner_closed']
    assert observation['inspection']['state']=='pending_post_N'
    reads=observations['saved174_consumer_read_observations.json']
    assert reads['successful_reads']==2 and reads['failed_read_count']==0 and reads['pending_registry_records']==0
value=dict(schema='h1_saved174_postcheck_result_'+number,status='VERIFIED_SCOPED_SAVED_DATA_OBSERVATION',
    plan_sha256=sha256(plan_path.read_bytes()).hexdigest(),terminal=terminal,
    pytest_cases=int(match[1]),pytest_seconds=float(match[2]),planned_pins=len(plan['files_sha256']),pin_drift=drift,
    producer_result_sha256=plan['producer_result_sha256'],producer_plan_metadata_exception_sha256=plan['producer_plan_metadata_exception_sha256'],
    producer_actual_public_return_and_close_previously_verified=True,
    producer_exact_planned_invocation_metadata_matched=False,producer_plan_provenance_fields_all_current=False,
    saved_file_names_and_bytes_unchanged=len(actual),scratch_enumerated=False,empty_directory_namespace_equality_proven=False,
    observations=observations,archive_files=copies,entry_closed={k:v for k,v in closed.items() if k not in ('files_sha256','hits_by_path')},
    original_numerical_oracle_verified=number=='176',genuine_numerical_public_consumer_reopen_verified=number=='177',
    independent_observation=True,independent_scientific_algorithm=False,
    new_N0_Jobs=0,real_native_calls=0,production_seal=False,official_review=False,review_receipt=False,
    full_optimized_workflow_accepted=False,whole_workflow_performance_review_complete=False,
    formal_execution_ready=False,formal_run_authority=False,formal_result=False,resource_admission=False,native_execution_authorized=False)
out=D/('saved174_postcheck_result_'+number+'.json')
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),pytest_seconds=value['pytest_seconds'],
    outer_seconds=terminal['elapsed_seconds'],saved_files=len(actual),archive_files=len(copies))))
