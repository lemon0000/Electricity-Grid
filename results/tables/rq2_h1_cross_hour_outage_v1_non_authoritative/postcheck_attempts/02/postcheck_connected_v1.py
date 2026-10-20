"""Independent read-only arithmetic and artifact checks for the toy chain."""
from base64 import b64decode
from collections import defaultdict
from contextlib import closing
from fractions import Fraction as Q
from hashlib import sha256
import ast
import json
from pathlib import Path
import sqlite3
import sys
import xml.etree.ElementTree as ET

import psutil

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
label=sys.argv[1]
if not label.replace('_','').isalnum():raise ValueError('exact diagnostic label required')
attempt=HERE/label
output=HERE/(label+'_postcheck.json')
if output.exists():raise ValueError('preserve existing postcheck')


def load(path):return json.loads(path.read_bytes())
def pin(path):return sha256(path.read_bytes()).hexdigest()
def encoded(value):
    return (json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode('utf-8')
def digest(value):return sha256(encoded(value)).hexdigest()
def fraction(value):return Q(int(value['numerator']),int(value['denominator']))
def inventory(roots):
    return {str(p):pin(p) for root in roots for p in root.rglob('*') if p.is_file()}


terminal=load(attempt/'terminal.json');request=load(attempt/'request.json')
assert terminal['exit_code']==0 and terminal['reason'] is None
assert terminal['source_unchanged'] and terminal['observed_processes_absent']
assert terminal['monitor_errors']==terminal['cleanup_events']==[]
assert request['mode']=='connected' and request['diagnostic_only']
assert request['seconds']==1500 and request['native_calls_authorized'] is False
assert request['no_progress_seconds']==120
assert request['sampled_tree_rss_cap_bytes']==1024*1024**2 and request['logical_storage_cap_bytes']==128*1024**2
assert request['activity_policy']=='file_changes_or_sampled_tree_cpu_advance_0.25s__not_scientific_progress'
assert len(request['sources_sha256'])==1299
for name,expected in request['sources_sha256'].items():
    assert pin(Path(name))==expected
    assert pin(attempt/'tested_bytes'/Path(name).relative_to(REPO))==expected
cases=list(Path(terminal['retained_root']).glob('test_three_hour_connected_outa*'))
assert len(cases)==1
root=cases[0];result_path=root/'outage_chain_result.json';result=load(result_path)
case_before=inventory([root])
roots=[root/name for name in ('normal_non_authoritative','owner_non_authoritative','holder_non_authoritative')]
before=inventory(roots)
assert before==result['saved_files_sha256'] and len(before)==result['saved_file_count']
assert len(before)==444
assert result['reopen_all_saved_bytes_match'] and result['all_owned_lease_handles_closed']
assert result['synthetic_hours']==3 and result['normal_jobs']==3 and result['normal_stages']==15
assert result['selector_stages']==34 and result['paired_lane_hours']==7
for key in ('formal_result','formal_execution_ready','full_192_hour_execution_verified','resource_admission',
            'production_overhead_measured','writer_rehydration_implemented','persisted_atomic_live_join_authenticated'):
    assert result[key] is False
assert result['real_native_calls']==0 and result['reopen_scientific_match']
assert result['reopen_inputs_read_from_preclose_checkpoint'] and result['preclose_saved_bytes_match_closed_and_reopened']
assert result['clean_close_reopen_only'] and result['crash_durability_certified'] is False
checkpoint_path=Path(result['external_preclose_checkpoint'])
assert pin(checkpoint_path)==result['external_preclose_checkpoint_sha256']
checkpoint=load(checkpoint_path)
assert checkpoint['saved_files_sha256']==before and checkpoint['saved_file_count']==len(before)
assert checkpoint['scientific']==result['state'] and checkpoint['scientific_sha256']==digest(result['state'])
assert checkpoint['clean_close_reopen_inputs_only'] and checkpoint['crash_durability_certified'] is False
assert all(owned_root not in checkpoint_path.parents for owned_root in roots)

database=root/'owner_non_authoritative/owner.sqlite'
with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as db:
    assert db.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
    header_raw=db.execute('SELECT body FROM header WHERE id=1').fetchone()[0]
    saved=db.execute('SELECT seq,predecessor,kind,body,head FROM events ORDER BY seq').fetchall()
header=json.loads(header_raw)
assert header['schema']=='h1_cross_hour_owner_development_v2'
assert header['source_replay_contract']=='h1_phase_exact_source_batch_development_v1'
previous=digest(['owner_genesis',sha256(header_raw).hexdigest()])
rows=[]
for index,(seq,pred,kind,raw,head) in enumerate(saved,1):
    body=json.loads(raw)
    assert seq==index and pred==previous and encoded(body)==raw
    assert digest([seq,pred,kind,sha256(raw).hexdigest()])==head
    previous=head;rows.append((kind,body,head))
assert [row[0] for row in rows]==['intent','outcome','attempt','intent','outcome','attempt','intent','outcome','attempt']
assert rows[-1][1]['hour']==3
intents=[row[1] for row in rows if row[0]=='intent']
outcomes=[row[1] for row in rows if row[0]=='outcome']
assert [body['hour'] for body in intents]==[0,1,2]
assert [fraction(body['projection']['reference_request_mw']) for body in outcomes]==[5,5,0]
assert outcomes[-1]['projection']['after']==result['state']
assert checkpoint['owner_heads']==[next(row[4] for row in reversed(saved) if row[2]=='outcome'),saved[-1][4]]
assert checkpoint['holder_head']==pin(root/'holder_non_authoritative/000009.json')
assert checkpoint['binding']==header['storage']['storage']['binding']
assert checkpoint['manifest_sha256']==digest(header['storage']['storage']['manifest'])
# Parent io.encode uses compact JSON without the owner's trailing newline.
# Reproduce that separate byte contract and match all retained Job requests.
parent_identity=sha256(json.dumps(checkpoint['normal_parent_declaration'],sort_keys=True,
    allow_nan=False,separators=(',',':')).encode()).hexdigest()
assert checkpoint['parent_identity']==parent_identity
for hour in range(3):
    job_request=load(root/f'normal_non_authoritative/job_{hour:03d}_non_authoritative/request.json')
    assert job_request['parent_identity']==parent_identity
    assert job_request['parent_declaration']==checkpoint['normal_parent_declaration']
for body,intent in zip(outcomes,intents,strict=True):
    assert body['key']==intent['key']==body['projection']['request_key']
    assert digest(body['projection'])==body['projection_sha256']

source_rows=[];captured=[];source_audit_pins=[]
for hour,body in enumerate(intents):
    audit=body['source_audit'];observation=audit['source_observation_audit_payload']
    assert audit['source_cfe_at_alpha_one_exact']==(['3','5'] if hour<2 else ['1','5'])
    assert observation['declaration']['power_raw_hour']==observation['declaration']['workload_raw_hour']==hour
    assert observation['declaration']['split']=='training'
    row=observation['power_source_row'];source_rows.append(row)
    assert row['active_event_id']==('toy-G1-outage' if hour<2 else '')
    assert row['active_component_uid']==('G1' if hour<2 else '')
    assert row['active_component_type']==('generator' if hour<2 else '')
    assert row['cfe_call_fraction']==('0.6' if hour<2 else '0.2')
    assert audit['registry_audit_payload']['origin_onset_known'] is False
    assert audit['current_source_correspondence_checked']
    assert audit['historical_controller']['replay_contract']=='h1_phase_historical_batch_development_v1'
    source_audit_pins.append(digest(audit))
    records=body['records']
    assert len(records['reference'])==4
    assert [len(records['actual'][key]) for key in ('cfe','joint','network')]==([3,3,3] if hour==0 else [1,3,3] if hour==1 else [0,3,3])
    for lane,items in [('reference',records['reference'])]+[(key,records['actual'][key]) for key in ('cfe','joint','network')]:
        for item in items:
            record=json.loads(b64decode(item,validate=True));raw=record['raw']
            values=dict(raw['loaded_values'])
            g1,g2=values['generation[G1]'],values['generation[G2]']
            power=values['reference_power'] if lane=='reference' else float(fraction(record['power']))
            assert abs(g1+g2-20-power)<=1e-9
            assert 0<=g1<=24 and 10<=g2<=40
            assert g1==0 if hour<2 else g1==24
            assert raw['assignment_valid'] and raw['maximum_residual']<=1e-9
            assert record['native_execution_authenticated'] is False
            captured.append(dict(hour=hour,lane=lane,record=record,generation=[g1,g2],power=power))
assert len(captured)==34
timeouts=[(index,item) for index,item in enumerate(captured) if not item['record']['raw']['optimal']]
assert len(timeouts)==1 and timeouts[0][0]==17 and timeouts[0][1]['lane']=='cfe'
timeout_raw=timeouts[0][1]['record']['raw']
assert timeout_raw['solution_count']==1 and timeout_raw['native_infeasible'] is False
assert 'maxTimeLimit' in json.dumps(timeout_raw['solver_records'])

oracle=[];quantities=[];remaining_debt={}
expected={
    'cfe':([Q(1,50)],[Q(0)],Q(1,50)),
    'joint':([Q(1,25),Q(1,25),Q(0)],[Q(0),Q(0),Q(3,50)],Q(29,1000)),
    'network':([Q(1,50),Q(1,50),Q(0)],[Q(0),Q(0),Q(47058823529,10**12)],Q(7,20_000_000_000_000)),
}
for key,(expected_q,expected_r,expected_debt) in expected.items():
    details=[next(item for item in body['projection']['lanes'] if item['lane_id']==key) for body in outcomes]
    paired=[(hour,item) for hour,item in enumerate(details) if item['paired_committed']]
    q_values=[];r_values=[];powers=[];debt=Q(0)
    for hour,item in paired:
        action=item['business_candidate']['action']
        q=fraction(action['grid_served'])+fraction(action['cfe_served'])
        r=fraction(action['recovery']);power=fraction(item['actual_power_mw'])
        assert 0<=q<=Q(1,20) and 0<=q+r<=Q(1,2)
        assert 0<=r<=Q(9,100) and r<=debt/Q(85,100)
        if key!='network':
            cfe=Q(3,5) if hour<2 else Q(1,5)
            surplus=max(Q(0),(1-cfe)*Q(1,10)/Q(1,2)-Q(1,10))
            assert r<=surplus
        assert power==250*(Q(1,10)-q+r)
        debt+=q-Q(85,100)*r
        quantities.append(dict(hour=hour,lane=key,q=str(q),r=str(r),power_mw=str(power)))
        q_values.append(q);r_values.append(r);powers.append(power)
    assert q_values==expected_q and r_values==expected_r and debt==expected_debt
    assert Q(result['debts'][key])==debt
    if key=='cfe':
        assert [item['status'] for item in details]==['paired_committed','actual_unresolved','skipped_halted']
        for item in details[1:]:
            assert item['before_business']==item['after_business']==details[0]['after_business']
            assert item['before_actual']==item['after_actual']==details[0]['after_actual']
            assert item['halted'] and item['halt_reason']=='actual_unresolved'
    else:assert all(item['status']=='paired_committed' and not item['halted'] for item in details)
    remaining_debt[key]=str(debt)
    oracle.append(dict(lane=key,q=list(map(str,q_values)),r=list(map(str,r_values)),
        actual_power_mw=list(map(str,powers)),remaining_debt=str(debt)))

missing=result['missing_source'];reopened=result['reopen_inspection']
assert missing==dict(relative_hour=3,error_type='ValueError',message='window not contained in one verified same-split source chain',
    pending_attempt_retained=True,extra_normal_job_created=False,extra_selector_calls=0)
assert reopened==dict(completed_hours=3,pending_attempt=True,continuation_available=False,episode_terminal=False)
normal_root=root/'normal_non_authoritative'
assert not (normal_root/'job_003_non_authoritative').exists()
assert not (normal_root/'clock_bridge_non_authoritative/003').exists()
assert not (normal_root/'source_parent_non_authoritative/hour_003_non_authoritative').exists()
assert not list((normal_root/'obligation_non_authoritative').glob('003.*'))
jobs=result['normal_job_observations']
assert len(jobs)==3 and len({job['pid'] for job in jobs})==3
assert all(job['exit_code']==0 and job['whole_job_quiescent'] for job in jobs)

metrics=result['batch_observations']
assert len(metrics)==32 and len({row['observation_token'] for row in metrics})==32
assert sum(row['completed_hours'] for row in metrics)==64
assert sum(row['parent_inspect_traversals'] for row in metrics)==64
assert sum(row['parent_inspect_traversals']*row['completed_hours'] for row in metrics)==128
assert all(row['parent_inspect_traversals']==2 for row in metrics)
book=load(root/'static_identity_bookends.json')
assert book['errors']==[] and all(row['original_callable_restored'] for row in book['functions'])
assert book['production_overhead_measured'] is False
assert book['original_functions_bookended_after_all_aliases_restored']
assert book['dynamic_source_or_history_or_state_cached'] is False
assert len(book['functions'])==len({row['function'] for row in book['functions']})==15
for item in book['functions']:
    assert item['calls']>0 and item['original_computations']>0
    assert len(item['bookends'])==item['original_computations']
    for pair in item['bookends']:
        assert pair['before']==pair['after']
        assert len(pair['arguments_sha256'])==64 and int(pair['arguments_sha256'],16)>=0
remaining=[]
for pid,created in terminal['observed_processes'].items():
    try:
        process=psutil.Process(int(pid))
        if process.create_time()==created and process.is_running():remaining.append(int(pid))
    except psutil.NoSuchProcess:pass
assert remaining==[]

units=HERE/'units_06';unit_request=load(units/'request.json');unit_terminal=load(units/'terminal.json')
assert unit_terminal['exit_code']==0 and unit_terminal['source_unchanged'] and unit_terminal['observed_processes_absent']
assert unit_terminal['reason'] is None and unit_terminal['monitor_errors']==unit_terminal['cleanup_events']==[]
assert unit_request['mode']=='units' and unit_request['diagnostic_only']
assert unit_request['native_calls_authorized'] is False
test_name='tests/test_h1_cross_hour_outage_chain_development_v1.py'
assert unit_request['command'][-3:]==[test_name,'-k','not test_three_hour_connected_outage_repair_lane_stop_and_missing_source']
unit_cases=list(ET.parse(units/'junit.xml').iter('testcase'))
assert len(unit_cases)==6 and all(case.find('failure') is None and case.find('error') is None for case in unit_cases)
assert {case.attrib['name'] for case in unit_cases}=={
    'test_two_unit_normal_candidates_match_every_canonical_stage[0]',
    'test_two_unit_normal_candidates_match_every_canonical_stage[1]',
    'test_two_unit_normal_candidates_match_every_canonical_stage[2]',
    'test_three_hour_analytic_outage_repair_and_timeout_oracle',
    'test_missing_next_source_is_not_substituted',
    'test_connected_selector_budget_covers_two_unit_inventory'}
assert pin(units/'tested_bytes'/test_name)==unit_request['sources_sha256'][str(REPO/test_name)]
def unit_ast(path):
    tree=ast.parse(path.read_bytes())
    tree.body=[node for node in tree.body if not (isinstance(node,ast.FunctionDef)
        and node.name=='test_three_hour_connected_outage_repair_lane_stop_and_missing_source')]
    return ast.dump(tree,include_attributes=False)
assert unit_ast(REPO/test_name)==unit_ast(units/'tested_bytes'/test_name)
helper=REPO/'tests/h1_cross_hour_outage_fixture_v1.py'
assert pin(helper)==pin(units/'tested_bytes'/helper.relative_to(REPO))==unit_request['sources_sha256'][str(helper)]
kernel_paths=list(Path(unit_terminal['retained_root']).glob('*/outage_kernel_oracle.json'))
assert len(kernel_paths)==1
kernel_path=kernel_paths[0];kernel=load(kernel_path)
assert sorted(quantities,key=lambda r:(r['hour'],r['lane']))==sorted(kernel['quantities'],key=lambda r:(r['hour'],r['lane']))
assert result['selector_calls']==kernel['selector_calls'] and result['debts']==kernel['debts']
assert kernel['repair_cap_exceedance_rejected'] and kernel['timeout_is_unresolved']
assert kernel['source_actions']==[
    dict(relative_hour=0,active=dict(kind='generator',uid='G1'),started=None,ended=None,repair_cap_exact=None),
    dict(relative_hour=1,active=dict(kind='generator',uid='G1'),started=None,ended=None,repair_cap_exact=None),
    dict(relative_hour=2,active=None,started=None,ended=dict(kind='generator',uid='G1'),repair_cap_exact=['24','1'])]
predecessor=REPO/'results/tables/rq2_h1_cross_hour_batch_v2_non_authoritative'
predecessor_request=load(predecessor/'connected_01/request.json')
predecessor_check=load(predecessor/'connected_01_postcheck.json')
assert predecessor_check['inherited_v1_guard_passes']==36 and predecessor_check['current_v2_boundary_passes']==23
inherited_sources={}
for filename,expected_pin in predecessor_request['sources_sha256'].items():
    path=Path(filename);relative=path.relative_to(REPO)
    if relative.parts[0] in ('src','experiments','tests','configs'):
        assert pin(path)==pin(predecessor/'connected_01/tested_bytes'/relative)==expected_pin
        inherited_sources[relative.as_posix()]=expected_pin
for name in ('experiments/h1_cross_hour_owner_development_v2.py',
        'experiments/h1_phase_exact_source_batch_development_v1.py',
        'experiments/h1_phase_historical_batch_development_v1.py',
        'tests/test_h1_cross_hour_owner_development_v1.py','tests/test_h1_cross_hour_batch_development_v2.py'):
    expected_pin=predecessor_request['sources_sha256'][str(REPO/name)]
    assert pin(REPO/name)==pin(predecessor/'connected_01/tested_bytes'/name)==expected_pin
    inherited_sources[name]=expected_pin
assert len(inherited_sources)==1279
connected_cases=list(ET.parse(attempt/'junit.xml').iter('testcase'))
assert len(connected_cases)==1
assert connected_cases[0].attrib['name']=='test_three_hour_connected_outage_repair_lane_stop_and_missing_source'
assert connected_cases[0].find('failure') is None and connected_cases[0].find('error') is None

trace=[json.loads(line) for line in (root/'cross_hour_timing.jsonl').read_text(encoding='utf-8').splitlines()]
assert [row['label'] for row in trace]==['start','N0_terminal','hour0_paired','hour1_paired','hour2_paired',
    'missing_source_stopped','live_checkpoint_saved','closed_before_reopen','reopen_constructor_verified',
    'reopen_inspect_verified','historical_prefix_verified','parent_snapshot_verified','reopen_verified']
for row in trace:
    if row['label'] in ('live_checkpoint_saved','closed_before_reopen'):
        assert row['checkpoint_sha256']==pin(checkpoint_path)
stage_seconds={right['label']:right['monotonic']-left['monotonic'] for left,right in zip(trace,trace[1:])}
owner_seconds=defaultdict(float)
for name,seconds in result['owner_stage_timings']:owner_seconds[name]+=seconds
assert inventory(roots)==before
assert inventory([root])==case_before
failure=load(HERE/'failed_connected_01_findings.json')
assert failure['paired_lane_hours']==failure['selector_captures']==0
assert all(pin(Path(name))==expected for name,expected in failure['retained_files_sha256'].items())
partial=load(HERE/'connected_02_closed_snapshot.json')
assert all(pin(Path(name))==expected for name,expected in partial['files_sha256'].items())
with closing(sqlite3.connect((Path(partial['case'])/'owner_non_authoritative/owner.sqlite').as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
    partial_outcomes=[json.loads(raw) for (raw,) in db.execute("SELECT body FROM events WHERE kind='outcome' ORDER BY seq")]
for body,old in zip(outcomes,partial_outcomes,strict=True):
    science=lambda b:{k:v for k,v in b['projection'].items() if k not in ('request_key','request_contract')}
    assert science(body)==science(old)
detached=load(HERE/'detached_03_postcheck.json')
assert detached['detached_projection_bytes_equal'] and detached['original_authenticated_reopen'] is False
bindings=[Path(__file__),attempt/'request.json',attempt/'terminal.json',attempt/'junit.xml',result_path,database,
    units/'request.json',units/'terminal.json',units/'junit.xml',kernel_path,root/'static_identity_bookends.json',
    root/'cross_hour_timing.jsonl',HERE/'prelaunch_reuse_bindings_v3.json',HERE/'connected_01/terminal.json',
    HERE/'failed_connected_01_findings.json',predecessor/'connected_01/request.json',predecessor/'connected_01_postcheck.json',
    checkpoint_path,HERE/'connected_02_closed_snapshot.json',HERE/'detached_03_postcheck.json',attempt/'stdout.txt']
report=dict(status='DRAFT_NONAUTHORITATIVE',attempt=label,bindings={str(p):pin(p) for p in bindings},
    saved_file_count=len(before),all_saved_bytes_match=True,read_only_postcheck_preserved_all_saved_bytes=True,
    diagnostic_case_files_sha256=case_before,failed_connected_01_saved_bytes_preserved=True,
    partial_connected_02_saved_bytes_preserved=True,partial_connected_02_scientific_projections_equal=True,
    retained_heads_and_scientific_sha_verified_from_live_preclose_checkpoint=True,
    checkpoint_sha256=pin(checkpoint_path),clean_close_same_process_reopen_only=True,crash_durability_certified=False,
    paired_lane_hours=7,oracle=oracle,source_rows=source_rows,source_audit_sha256=source_audit_pins,
    selector_records=34,normal_jobs=3,normal_stages=15,timeout_with_incumbent_remains_unresolved=True,
    cfe_business_and_actual_identities_not_advanced=True,repair_dispatch_respects_cap_mw=24,
    missing_next_source=missing,reopen_inspection=reopened,independent_arithmetic_matches_kernel_oracle=True,
    inherited_v1_guard_passes=36,inherited_v2_boundary_passes=23,inherited_source_sha256=inherited_sources,
    historical_api_calls=32,historical_api_prefix_hour_weight=64,parent_inspect_traversals=64,
    parent_inspect_prefix_hour_weight=128,excludes_independent_historical_snapshot_anchor_traversals=True,
    nonoverlapping_trace_seconds=stage_seconds,nested_owner_stage_seconds=dict(owner_seconds),
    outer_seconds=terminal['outer_seconds'],peak_sampled_tree_rss_bytes=terminal['peak_sampled_tree_rss_bytes'],
    peak_logical_bytes=terminal['peak_logical_bytes'],observed_processes_still_remaining=remaining,
    complete_process_tree_absence_proven=False,production_overhead_measured=False,
    full_192_hour_execution_verified=False,formal_followup_right_censoring_metric_verified=False,
    formal_execution_ready=False,resource_admission=False,formal_result=False,real_native_calls=0)
with output.open('x',encoding='utf-8') as stream:
    json.dump(report,stream,indent=2);stream.write('\n')
print(json.dumps(dict(output=str(output),saved_files=len(before),paired_lane_hours=7,
    outer_seconds=terminal['outer_seconds'],formal_result=False)))
