"""Archive the separate numerical postcheck without upgrading152 public status."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;D=HERE/'whole_workflow_optimization_01_non_authoritative'
plan_path=D/'saved152_numerical_postcheck_plan_153.json';plan=json.loads(plan_path.read_bytes())
terminal_path=HERE/'saved152_numerical_oracle_153/terminal.json';terminal=json.loads(terminal_path.read_bytes())
drift=[p for p,pin in plan['files_sha256'].items() if sha256(Path(p).read_bytes()).hexdigest()!=pin]
assert not drift and terminal['exit_code']==0 and terminal['source_unchanged']
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors']
base=Path('D:/h1_saved152_oracle_153_non_authoritative')
profile_path=next(base.glob('*/saved152_candidate_oracle_profile.json'));profile=json.loads(profile_path.read_bytes())
entry_path=base/'unit_code_read_lease_closed.json';entry=json.loads(entry_path.read_bytes())
assert not entry['diagnostic_validation_errors'] and entry['all_path_handles_closed']
archive=D/'saved152_oracle_153_preserved_non_authoritative';archive.mkdir(exist_ok=False);pins={}
for source in (profile_path,entry_path,profile_path.parent/'saved152_numerical_audit.json',
               profile_path.parent/'saved152_numerical_oracle.prof'):
    raw=source.read_bytes();target=archive/source.name
    with target.open('xb') as stream:stream.write(raw)
    assert source.read_bytes()==target.read_bytes()==raw
    pins[str(target)]=sha256(raw).hexdigest()
value=dict(schema='h1_saved152_numerical_postcheck_result_153',status='VERIFIED_NUMERICAL_CANDIDATE_ONLY',
    plan_sha256=sha256(plan_path.read_bytes()).hexdigest(),terminal=terminal,profile=profile,
    planned_pins=len(plan['files_sha256']),pin_drift=drift,candidate_files=plan['candidate_files'],
    archive_files_sha256=pins,entry_closed=entry,new_N0_Jobs=0,real_native_calls=0,
    numerical_candidate_equal=True,independent_observation=True,independent_scientific_algorithm=False,
    public_bootstrap_return_verified=False,read_only_owner_reopen_verified=False,
    original_operation_graceful_cleanup_proven=False,full_optimized_workflow_accepted=False,
    whole_workflow_performance_review_complete=False,formal_result=False,formal_execution_ready=False,
    resource_admission=False,native_execution_authorized=False)
target=D/'saved152_numerical_postcheck_result_153.json'
with target.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(target),sha256=sha256(target.read_bytes()).hexdigest(),pins=len(plan['files_sha256']),
    drift=drift,oracle_seconds=profile['oracle_seconds'],audit_sha256=profile['predecessor_audit_sha256'])))
