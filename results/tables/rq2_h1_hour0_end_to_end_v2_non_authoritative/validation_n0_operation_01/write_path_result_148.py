"""Archive exact path-composition results and limit the runtime comparison."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;D=HERE/'whole_workflow_optimization_01_non_authoritative'
plan_path=D/'saved137_path_diagnostic_plan_148.json';plan=json.loads(plan_path.read_bytes())
terminal_path=HERE/'saved137_path_profile_148/terminal.json';terminal=json.loads(terminal_path.read_bytes())
drift=[p for p,pin in plan['files_sha256'].items() if sha256(Path(p).read_bytes()).hexdigest()!=pin]
assert not drift and terminal['source_unchanged'] and terminal['exit_code']==0
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors']
base=Path('D:/h1_saved137_path_148_non_authoritative')
profile_path=next(base.glob('*/saved137_operation_profile.json'));profile=json.loads(profile_path.read_bytes())
closed_path=base/'unit_code_read_lease_closed.json';closed=json.loads(closed_path.read_bytes())
assert all(closed[key] for key in ('canonical_path_alias_restored','all_path_handles_closed',
    'canonical_paths_cleared','all_code_handles_closed','all_metadata_handles_closed',
    'original_read_alias_restored','original_metadata_version_alias_restored'))
assert closed['canonical_path_state']=='closed' and not closed['diagnostic_validation_errors']
assert profile['operation_receipt']['complete'] and profile['operation_receipt']['diagnostic_only']
archive=D/'saved137_path_148_preserved_non_authoritative';archive.mkdir(exist_ok=False);pins={}
for source in [profile_path,closed_path,*profile_path.parent.glob('prepare_*_profile.json'),
               *profile_path.parent.glob('prepare_*.prof')]:
    raw=source.read_bytes();target=archive/source.name
    with target.open('xb') as stream:stream.write(raw)
    assert source.read_bytes()==target.read_bytes()==raw
    pins[str(target)]=sha256(raw).hexdigest()
old_path=D/'saved137_n0_operation_diagnostic_result_146.json';old=json.loads(old_path.read_bytes())
left=old['profile']['prepares'];right=profile['prepares']
assert [r['execution']['predecessor_audit_sha256'] for r in left]==[r['execution']['predecessor_audit_sha256'] for r in right]
assert [r['execution']['decision_sha256'] for r in left]==[r['execution']['decision_sha256'] for r in right]
comparison=dict(baseline_pytest_seconds=151.08,current_pytest_seconds=129.65,
    baseline_outer_seconds=old['terminal']['elapsed_seconds'],current_outer_seconds=terminal['elapsed_seconds'],
    baseline_build_seconds=[r['seconds'] for r in left],current_build_seconds=[r['seconds'] for r in right],
    baseline_build_total=sum(r['seconds'] for r in left),current_build_total=sum(r['seconds'] for r in right),
    outer_elapsed_reduction_fraction=1-terminal['elapsed_seconds']/old['terminal']['elapsed_seconds'],
    decision_and_audit_sha256_equal=True,matched_unprofiled_runtime_comparison=False,
    repeated_randomized_benchmark=False,full_workflow_speedup_established=False)
value=dict(schema='h1_saved137_path_diagnostic_result_148',status='VERIFIED_DIAGNOSTIC_ONLY_PATH_COMPOSITION',
    plan_sha256=sha256(plan_path.read_bytes()).hexdigest(),terminal=terminal,
    planned_pins=len(plan['files_sha256']),pin_drift=drift,candidate_files=plan['candidate_files'],
    archive_files_sha256=pins,profile=profile,entry_closed=closed,comparison=comparison,
    interpretation='Same saved119 files and original verifier4 four-build cProfile test, exact4full/28fresh/64contexts and equal science. Observed outer153.984 to134.75s; single fixed-order profiled diagnostic only. No whole-chain ETA or resource admission follows.',
    pre_seal_review_input_sha256=sha256((D/'canonical_path_entry6_pre_seal_input_149.json').read_bytes()).hexdigest(),
    current_scoped_review_pending=True,public_bootstrap_return_verified=False,
    registered_N0_owner_authenticated=False,new_N0_Jobs=0,real_native_calls=0,
    whole_workflow_performance_review_complete=False,full_optimized_workflow_accepted=False,
    formal_result=False,formal_execution_ready=False,resource_admission=False,native_execution_authorized=False)
target=D/'saved137_path_diagnostic_result_148.json'
with target.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(target),sha256=sha256(target.read_bytes()).hexdigest(),pins=len(plan['files_sha256']),
                      drift=drift,path_hits=closed['canonical_path_receipt']['hits'],comparison=comparison)))
