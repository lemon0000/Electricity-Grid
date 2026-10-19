"""Bind the completed diagnostic operation without authenticating owner heads."""
from hashlib import sha256
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = HERE/'whole_workflow_optimization_01_non_authoritative'
plan_path = D/'saved137_n0_operation_diagnostic_plan_146.json'
plan = json.loads(plan_path.read_bytes())
terminal_path = HERE/'saved137_operation_profile_146/terminal.json'
terminal = json.loads(terminal_path.read_bytes())
drift = [p for p,pin in plan['files_sha256'].items() if sha256(Path(p).read_bytes()).hexdigest()!=pin]
assert not drift and terminal['exit_code']==0 and terminal['source_unchanged']
assert terminal['observed_owned_processes_absent'] and not terminal['cleanup_errors']
base = Path('D:/h1_saved137_operation_146_non_authoritative')
profile_path = next(base.glob('*/saved137_operation_profile.json'))
profile = json.loads(profile_path.read_bytes())
closed_path = base/'unit_code_read_lease_closed.json'
closed = json.loads(closed_path.read_bytes())
archive = D/'saved137_operation_146_preserved_non_authoritative'
archive.mkdir(exist_ok=False)
pins = {}
for source in [profile_path,closed_path,*profile_path.parent.glob('prepare_*_profile.json'),
               *profile_path.parent.glob('prepare_*.prof')]:
    target = archive/source.name
    raw = source.read_bytes()
    with target.open('xb') as stream:stream.write(raw)
    assert target.read_bytes()==raw and source.read_bytes()==raw
    pins[str(target)] = sha256(raw).hexdigest()
receipt = profile['operation_receipt']
assert receipt['complete'] and receipt['closed'] and receipt['proof_cleared']
assert receipt['diagnostic_only'] and not receipt['bootstrap_operation_bound']
assert receipt['completed_prepares']==len(receipt['confirmed_builds'])==4
assert receipt['context_observations']==64
value = dict(schema='h1_saved137_n0_operation_diagnostic_result_146',
    status='VERIFIED_DIAGNOSTIC_ONLY_OPERATION',
    plan_sha256=sha256(plan_path.read_bytes()).hexdigest(), terminal=terminal,
    terminal_sha256=sha256(terminal_path.read_bytes()).hexdigest(),
    planned_pins=len(plan['files_sha256']),pin_drift=drift,candidate_files=plan['candidate_files'],
    profile=profile,entry_closed_sha256=sha256(closed_path.read_bytes()).hexdigest(),archive_files_sha256=pins,
    observation='4 original begin_build/prepare/confirm_build cycles on saved candidate; first4 full+4 fresh, then3x8 fresh;64 complete contexts. All audits match. No public Bootstrap owner exists in this diagnostic.',
    cost='First29.823s, reused20.471/20.599/20.688s under cProfile. Each reused cycle still invokes101426 Path.stat,13448 read/open and3486 episode_store._path calls. Cumulative times overlap.',
    next_question='Measure the unchanged existing CanonicalPathLease around this same saved four-build program; keep leaf bytes/stamps and ancestor reparse/case observations fresh.',
    public_bootstrap_return_verified=False,registered_N0_owner_authenticated=False,
    new_N0_Jobs=0,real_native_calls=0,independent_scientific_algorithm=False,
    whole_workflow_performance_review_complete=False,full_optimized_workflow_accepted=False,
    formal_result=False,formal_execution_ready=False,resource_admission=False,native_execution_authorized=False)
target = D/'saved137_n0_operation_diagnostic_result_146.json'
with target.open('x',encoding='utf-8',newline='\n') as stream:
    json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(target),sha256=sha256(target.read_bytes()).hexdigest(),pins=len(plan['files_sha256']),drift=drift)))
