"""Verify retained numerical diagnostic, accounting, untouched bytes and cleanup."""
from hashlib import sha256
import json
import msvcrt
from pathlib import Path
import psutil

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
OUT=HERE/'saved_four_01_non_authoritative';MON=HERE/'saved_four_monitor_01'
def read(p):return json.loads(p.read_bytes())
def encode(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
inner=read(OUT/'terminal.json');outer=read(MON/'terminal.json');request=read(OUT/'request.json')
assert inner['exit_code']==outer['exit_code']==0 and outer['stop_reason'] is None
assert inner['sources_unchanged'] and inner['saved_unchanged'] and inner['old_chain_unchanged']
assert not inner['formal_result'] and not inner['full_hour0_chain_passed'] and not inner['actual_bootstrap_registration']
assert inner['scientific_bytes_equal_predecessor'] and inner['code_lease_files']==159
baseline=[read(OUT/f'baseline_{i}.json') for i in range(1,5)]
candidate=[read(OUT/f'candidate_{i}.json') for i in range(1,5)]
receipt=read(OUT/'operation_receipt.json');fallback=read(OUT/'fallback.json')
assert receipt['complete'] and receipt['proof_cleared'] and receipt['closed']
assert receipt['context_observations']==64 and receipt['diagnostic_only'] and not receipt['bootstrap_operation_bound']
assert [r['site'] for r in receipt['confirmed_builds']]==[r['site'] for r in candidate]
science=(baseline[0]['decision_sha256'],baseline[0]['audit_sha256'])
previous=None
for i,(b,c,row,build) in enumerate(zip(baseline,candidate,receipt['prepares'],receipt['confirmed_builds'])):
    execution=c['execution'];counts=(4,4) if i==0 else (0,8)
    assert (b['decision_sha256'],b['audit_sha256'])==science
    assert (execution['decision_sha256'],execution['predecessor_audit_sha256'])==science
    assert (execution['full_numerical_hour_replays'],execution['reused_numerical_inspections_total'])==counts
    assert execution==row['execution'] and row['context_evaluations']==16
    assert sha256(encode(execution)).hexdigest()==row['execution_receipt_sha256']==build['execution_receipt_sha256']
    assert c['envelope_identity']==row['envelope_identity']==build['envelope_identity']
    assert build['proof_basis_identity']==row['proof_basis_identity']==receipt['prepares'][0]['proof_basis_identity']
    assert execution['session_identity']==receipt['session_identity']
    assert execution['active_validation_identity']==receipt['active_validation_identity']
    assert build['previous_receipt_sha256']==previous
    record={k:v for k,v in build.items() if k!='receipt_sha256'}
    assert sha256(encode(record)).hexdigest()==build['receipt_sha256'];previous=build['receipt_sha256']
assert (fallback['execution']['decision_sha256'],fallback['execution']['predecessor_audit_sha256'])==science
assert fallback['execution']['mode']=='full_only' and fallback['execution']['full_numerical_hour_replays']==4
assert len({r['body_sha256'] for r in receipt['confirmed_builds']})==1
saved=Path('D:/h1_chain_06_non_authoritative')
assert {str(p):sha256(p.read_bytes()).hexdigest() for p in saved.rglob('*') if p.is_file()}==request['saved_sha256']
assert all(sha256(Path(p).read_bytes()).hexdigest()==h for p,h in request['old_chain_sha256'].items())
locks=[]
for path in sorted(saved.rglob('*.lock')):
    with path.open('r+b',buffering=0) as stream:
        stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        try:locks.append(str(path))
        finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
assert len(locks)==33
started=read(MON/'started.json')
try:assert psutil.Process(started['pid']).create_time()!=started['creation_time']
except psutil.NoSuchProcess:pass
drift=[name for name,pin in request['source_sha256'].items() if sha256(Path(name).read_bytes()).hexdigest()!=pin]
allowed=str(REPO/'experiments/h1_bootstrap_integration_development_v3.py')
assert drift==[allowed],drift
# The post-diagnostic change only hardens receipt publication in the bootstrap
# owner. This saved entry never constructs that owner; numerical verifier and
# all its tested dependencies remain exact. The new bootstrap gets unit_07.
snapshots={}
for name,pin in request['source_sha256'].items():
    path=Path(name);relative=path.relative_to(REPO) if path.is_relative_to(REPO) else Path('vendor')/path.relative_to(Path('D:/'))
    snap=OUT/'tested_bytes'/relative;assert sha256(snap.read_bytes()).hexdigest()==pin
    snapshots[name]=pin
value=dict(status='DRAFT_NONAUTHORITATIVE',diagnostic_verified=True,
    baseline_four_seconds=inner['baseline_four_seconds'],candidate_four_seconds=inner['candidate_four_seconds'],
    fraction_saved=1-inner['candidate_four_seconds']/inner['baseline_four_seconds'],
    numerical_counts_before=[16,16],numerical_counts_after=[4,28],context_evaluations_each=64,
    source_snapshot_files=len(snapshots),saved_files=len(request['saved_sha256']),saved_locks_reacquired_and_released=locks,
    saved_process_absent=True,old_chain_pins_unchanged=len(request['old_chain_sha256']),
    source_changes_after_diagnostic=drift,post_diagnostic_change_scope='bootstrap receipt publication only; saved numerical scope unchanged',
    exact_numerical_verifier_sha256=request['source_sha256'][str(REPO/'experiments/h1_historical_n0_verifier_development_v2.py')],
    evidence_sha256={str(p.relative_to(REPO)):sha256(p.read_bytes()).hexdigest() for p in (
        OUT/'terminal.json',OUT/'request.json',OUT/'operation_receipt.json',MON/'terminal.json',MON/'started.json',Path(__file__))},
    actual_bootstrap_registration=False,full_hour0_chain_passed=False,formal_execution_ready=False,
    formal_result=False,resource_admission=False,native_execution_authorized=False)
with (HERE/'saved_four_comparison_01.json').open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps({k:v for k,v in value.items() if k not in ('evidence_sha256','saved_locks_reacquired_and_released')}),flush=True)
