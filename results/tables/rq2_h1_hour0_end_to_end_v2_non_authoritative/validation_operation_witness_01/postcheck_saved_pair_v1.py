"""Check the two fixed diagnostic attempts before reporting any local benefit."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[3]
MANIFEST_PIN='5dec7d5766827cb56e3bc441c13d3205f10dd231f48fcab6ce508db298604378'


def read(path):return json.loads(path.read_bytes())


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')


if sha256((HERE/'diagnostic_source_manifest_v1.json').read_bytes()).hexdigest()!=MANIFEST_PIN:
    raise ValueError('fixed diagnostic manifest differs')
manifest=read(HERE/'diagnostic_source_manifest_v1.json')
for name,h in manifest['files_sha256'].items():
    if sha256((REPO/name).read_bytes()).hexdigest()!=h:raise ValueError('fixed diagnostic source/evidence drift')
attempts={};requests={};summary={};evidence={};oracles={};locks={}
for mode in ('full_only','operation'):
    root=HERE/(mode+'_01');out=root/'attempt_non_authoritative'
    outer=read(root/'terminal.json');inner=read(out/'terminal.json');request=read(root/'request.json')
    inner_request=read(out/'request.json')
    if (outer['exit_code']!=0 or inner['exit_code']!=0 or outer['stop_reason'] is not None
            or outer['errors'] or not outer['observed_owned_processes_absent']
            or not outer['saved_locks']['all_reacquired_and_released']
            or any(not obj[key] for obj in (outer,inner) for key in ('source_unchanged','saved_unchanged'))
            or sha256((out/'terminal.json').read_bytes()).hexdigest()!=outer['inner_terminal_sha256']
            or request['diagnostic_manifest_sha256']!=MANIFEST_PIN):
        raise ValueError('fixed attempt terminal/postcheck is incomplete: '+mode)
    if (inner_request['source_sha256']!=request['source_sha256']
            or inner_request['saved_sha256']!=request['saved_sha256']
            or inner_request['source_sha256'][str(HERE/'diagnostic_source_manifest_v1.json')]!=MANIFEST_PIN):
        raise ValueError('inner and outer input/source closures differ')
    if (request['wall_seconds']!=300 or request['sampled_rss_cap_bytes']!=512*1024**2
            or request['new_artifact_cap_bytes']!=64*1024**2
            or outer['peak_observed_process_tree_rss']>request['sampled_rss_cap_bytes']
            or outer['observed_new_artifact_bytes']>request['new_artifact_cap_bytes']
            or inner['elapsed_seconds']>request['wall_seconds']
            or outer['child_exit_code']!=0 or outer['inner_exit_code']!=0 or not outer['memory_is_sampled']
            or outer['observed_owned_processes_remaining']):
        raise ValueError('declared diagnostic budget/cleanup contract differs')
    if (not inner['scientific_bytes_equal_original'] or not inner['original_context_unchanged']
            or not inner['original_numerical_inspector_unchanged']
            or not inner['candidate_first_loaded_after_fixture_leases_and_oracle']
            or inner['context_observations']!=32):raise ValueError('original numerical/context contract differs')
    science=read(out/'oracle_scientific.json');oracles[mode]=science
    if sha256((out/'oracle_audit.json').read_bytes()).hexdigest()!=science['audit_sha256']:
        raise ValueError('oracle scientific audit file differs')
    rows=[read(out/('prepare_'+str(i)+'.json')) for i in (1,2)]
    receipt=read(out/'operation_receipt.json')
    if not receipt['complete'] or not receipt['closed'] or not receipt['proof_cleared']:
        raise ValueError('operation did not reach closed complete state')
    for i,row in enumerate(rows):
        execution=row['execution'];expected=(0,8) if mode=='operation' and i==1 else (4,4)
        role='produced' if i==0 else ('consumed' if mode=='operation' else 'reconfirmed')
        recorded=receipt['prepares'][i]
        if ((row['full_numerical_hour_replays'],row['reused_numerical_inspections_total'])!=expected
                or execution['context_evaluations']!=16 or execution['decision_sha256']!=science['decision_sha256']
                or execution['predecessor_audit_sha256']!=science['audit_sha256']
                or execution['full_numerical_hour_replays']!=expected[0]
                or execution['reused_numerical_inspections_total']!=expected[1]
                or execution['within_prefix_revalidations']!=(4 if expected[0] else 0)
                or execution['cross_prepare_proof_reuses']!=(0 if expected[0] else 8)
                or execution['mode']!=mode or execution['prepare']!=i+1 or execution['proof_role']!=role
                or any(execution[k] is not False for k in ('formal_result','resource_admission',
                    'native_execution_authorized','production_handoff_integrated'))
                or execution['proof_basis_identity']!=rows[0]['execution']['proof_basis_identity']
                or execution['session_identity']!=receipt['session_identity']
                or execution['active_validation_identity']!=receipt['active_validation_identity']
                or recorded['envelope_identity']!=row['envelope_identity']
                or recorded['proof_basis_identity']!=execution['proof_basis_identity']
                or recorded['execution_receipt_sha256']!=row['execution_receipt_sha256']
                or sha256(canonical(execution)).hexdigest()!=row['execution_receipt_sha256']):
            raise ValueError('mode execution/scientific record differs')
    locks[mode]=outer['saved_locks']
    if locks[mode]['files']!=len(locks[mode]['paths']) or len(set(locks[mode]['paths']))!=locks[mode]['files']:
        raise ValueError('saved lock inventory is not self-consistent')
    requests[mode]=request;attempts[mode]=rows
    summary[mode]=dict(oracle_seconds=inner['oracle_seconds'],prepare_seconds=[r['elapsed_seconds'] for r in rows],
        two_prepare_seconds=sum(r['elapsed_seconds'] for r in rows),full_calls=sum(r['full_numerical_hour_replays'] for r in rows),
        context_evaluations=inner['context_observations'],observed_peak_rss_bytes=outer['peak_observed_process_tree_rss'],
        observed_new_artifact_bytes=outer['observed_new_artifact_bytes'],saved_lock_files=outer['saved_locks']['files'])
    for path in (root/'request.json',root/'terminal.json',out/'request.json',out/'terminal.json',out/'operation_receipt.json',
            out/'oracle_scientific.json',out/'oracle_audit.json',out/'prepare_1.json',out/'prepare_2.json'):
        evidence[path.relative_to(REPO).as_posix()]=sha256(path.read_bytes()).hexdigest()
if requests['full_only']['source_sha256']!=requests['operation']['source_sha256']:
    raise ValueError('the two modes used different source closures')
if requests['full_only']['saved_sha256']!=requests['operation']['saved_sha256']:
    raise ValueError('the two modes used different saved inputs')
if (HERE/'full_only_01/attempt_non_authoritative/oracle_audit.json').read_bytes()!=(HERE/'operation_01/attempt_non_authoritative/oracle_audit.json').read_bytes():
    raise ValueError('original scientific audit differs across modes')
if oracles['full_only']!=oracles['operation'] or locks['full_only']!=locks['operation']:
    raise ValueError('cross-mode oracle/lock inventory differs')
shared=requests['full_only']
if {name:sha256(Path(name).read_bytes()).hexdigest() for name in shared['source_sha256']}!=shared['source_sha256']:
    raise ValueError('complete source closure changed after attempt terminal')
saved=Path('D:/h1_chain_06_non_authoritative')
if {str(p):sha256(p.read_bytes()).hexdigest() for p in saved.rglob('*') if p.is_file()}!=shared['saved_sha256']:
    raise ValueError('complete saved inventory changed after attempt terminal')
base=summary['full_only'];optimized=summary['operation']
gain=1-optimized['two_prepare_seconds']/base['two_prepare_seconds']
value=dict(schema='h1_operation_historical_saved_pair_development_v1',
    scope='one fixed saved arm; two historical-only prepares per fresh process; one pair',
    diagnostic_manifest_sha256=MANIFEST_PIN,summary=summary,source_files=len(requests['full_only']['source_sha256']),
    saved_files=len(requests['full_only']['saved_sha256']),source_and_saved_inputs_exact_equal=True,
    scientific_audit_exact_equal_across_modes=True,two_prepare_fraction_saved=gain,
    sampled_limits_observed=True,observed_owned_processes_absent=True,saved_lock_inventory_reacquired=True,
    process_cleanup_scope='PID plus creation time; observed owned tree only',real_native_calls=0,
    second_prepare_fraction_saved=1-optimized['prepare_seconds'][1]/base['prepare_seconds'][1],
    local_performance_gate='positive_single_pair' if gain>0 else 'reject_slower_candidate',
    effect_uncertainty='one pair only; no full-chain runtime estimate',evidence_sha256=evidence,
    production_handoff_integrated=False,whole_workflow_performance_review_complete=False,
    long_chain_launch_admitted=False,full_chain_passed=False,formal_result=False,resource_admission=False,
    native_execution_authorized=False)
with (HERE/'saved_pair_comparison_01.json').open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2)
print(json.dumps({k:v for k,v in value.items() if k!='evidence_sha256'}))
