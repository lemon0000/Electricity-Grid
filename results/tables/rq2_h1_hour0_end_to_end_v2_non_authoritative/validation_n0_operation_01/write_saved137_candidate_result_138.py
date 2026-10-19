"""Record candidate-only scientific equality and attributed reader costs."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent;D=HERE/'whole_workflow_optimization_01_non_authoritative'
plan_path=D/'saved137_candidate_diagnostic_plan_138.json';plan=json.loads(plan_path.read_bytes())
out=HERE/'saved137_numerical_oracle_138';terminal_path=out/'terminal.json'
terminal=json.loads(terminal_path.read_bytes());base=Path('D:/h1_saved137_oracle_138_non_authoritative')
profile_path=next(base.glob('*/saved137_candidate_oracle_profile.json'))
closed_path=base/'unit_code_read_lease_closed.json'
drift=[p for p,pin in plan['files_sha256'].items() if sha256(Path(p).read_bytes()).hexdigest()!=pin]
assert terminal['exit_code']==0 and terminal['source_unchanged'] and not drift
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors']
value=dict(schema='h1_saved137_candidate_diagnostic_result_138',status='VERIFIED_NUMERICAL_CANDIDATE_ONLY',
    plan_sha256=sha256(plan_path.read_bytes()).hexdigest(),terminal=terminal,
    terminal_sha256=sha256(terminal_path.read_bytes()).hexdigest(),
    profile_sha256=sha256(profile_path.read_bytes()).hexdigest(),profile=json.loads(profile_path.read_bytes()),
    closed_receipt_sha256=sha256(closed_path.read_bytes()).hexdigest(),entry_receipt=json.loads(closed_path.read_bytes()),
    planned_pins=len(plan['files_sha256']),pin_drift=drift,candidate_files=plan['candidate_files'],
    new_N0_Jobs=0,real_native_calls=0,independent_observation=True,independent_scientific_algorithm=False,
    public_bootstrap_return_verified=False,externally_retained_owner_heads_verified=False,
    registered_N0_owner_authenticated=False,
    interpretation='Original predecessor numerical oracle, invoked separately against saved137 bytes, matches the local candidate audit SHA. No owner was opened and no Job rerun. '
        '28.093s profiled reader includes metadata.version6081 calls/8.420s and106644 Path.stat calls/7.396s. '
        '83.50s pytest total also includes expensive fixture construction outside the existing per-body metadata resolver. '
        'Do not add overlapping cumulative costs or treat profile time as an unprofiled speed estimate.',
    next_question='Safely reuse the existing original metadata resolver around the heavy fixture bodies as well as each test body; preserve stock discovery fallback and full scope cleanup.',
    profiler_enabled=True,matched_unprofiled_runtime_comparison=False,
    whole_workflow_performance_review_complete=False,full_optimized_workflow_accepted=False,
    formal_result=False,formal_execution_ready=False,resource_admission=False,native_execution_authorized=False)
target=D/'saved137_candidate_diagnostic_result_138.json'
with target.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(target),sha256=sha256(target.read_bytes()).hexdigest(),pins=len(plan['files_sha256']),pin_drift=drift)))
