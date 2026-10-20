"""Read closed synthetic-chain artifacts; write one new non-authoritative report."""
from collections import Counter, defaultdict
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


def load(path):return json.loads(path.read_text(encoding='utf-8'))
def pin(path):return sha256(path.read_bytes()).hexdigest()
def encoded(value):
    return (json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode('utf-8')


def inventory(roots):
    return {str(p):pin(p) for root in roots for p in root.rglob('*') if p.is_file()}


def read_owner(root):
    path=root/'owner_non_authoritative/owner.sqlite'
    with closing(sqlite3.connect('file:'+path.as_posix()+'?mode=ro',uri=True)) as db:
        header=json.loads(db.execute('SELECT body FROM header WHERE id=1').fetchone()[0])
        rows=[(seq,kind,json.loads(body),head) for seq,kind,body,head in
              db.execute('SELECT seq,kind,body,head FROM events ORDER BY seq')]
    return header,rows


terminal=load(attempt/'terminal.json');request=load(attempt/'request.json')
assert terminal['exit_code']==0 and terminal['reason'] is None
assert terminal['source_unchanged'] and terminal['observed_processes_absent']
assert terminal['monitor_errors']==terminal['cleanup_events']==[]
assert request['mode']=='connected' and request['diagnostic_only']
assert request['native_calls_authorized'] is False
assert all(pin(Path(name))==expected for name,expected in request['sources_sha256'].items())
base=Path(terminal['retained_root'])
cases=list(base.glob('test_two_hour_three_lane_batch*'))
assert len(cases)==1
root=cases[0];result_path=root/'cross_hour_result.json';result=load(result_path)
roots=[root/name for name in ('normal_non_authoritative','owner_non_authoritative','holder_non_authoritative')]
before=inventory(roots)
assert before==result['saved_files_sha256'] and len(before)==result['saved_file_count']==212
assert result['reopen_all_saved_bytes_match'] and result['all_owned_lease_handles_closed']
assert result['real_native_calls']==0 and result['normal_jobs']==2 and result['selector_stages']==18
assert result['formal_result'] is False and result['full_192_hour_execution_verified'] is False

metrics=result['batch_observations']
assert len(metrics)==result['batch_historical_calls']==20
assert sum(row['completed_hours'] for row in metrics)==result['historical_prefix_hour_weight']==28
assert sum(row['parent_inspect_traversals'] for row in metrics)==result['parent_inspect_traversals']==40
assert sum(row['parent_inspect_traversals']*row['completed_hours'] for row in metrics)==56
assert len({row['observation_token'] for row in metrics})==20
assert all(row['parent_inspect_traversals']==2 for row in metrics)
assert metrics[-2:][0]['selected_hours']==metrics[-2:][1]['selected_hours']==[0,1]

baseline=Path('D:/h1_cross_connected_06_non_authoritative/test_two_hour_three_lane_conne0')
prior_result=load(baseline/'cross_hour_result.json')
prior_roots=[baseline/name for name in ('normal_non_authoritative','owner_non_authoritative','holder_non_authoritative')]
prior_before=inventory(prior_roots)
assert prior_before==prior_result['saved_files_sha256']
header,rows=read_owner(root);prior_header,prior_rows=read_owner(baseline)
assert header['schema']=='h1_cross_hour_owner_development_v2'
assert header['source_replay_contract']=='h1_phase_exact_source_batch_development_v1'
assert prior_header['schema']=='h1_cross_hour_owner_development_v1'
assert [row[1] for row in rows]==['intent','outcome','attempt','intent','outcome']
assert [row[1] for row in rows]==[row[1] for row in prior_rows]
outcomes=[row[2] for row in rows if row[1]=='outcome']
prior_outcomes=[row[2] for row in prior_rows if row[1]=='outcome']
scientific=[]
for body,old in zip(outcomes,prior_outcomes,strict=True):
    projection=body['projection'];prior_projection=old['projection']
    assert projection['request_contract']==header['schema']
    assert projection['request_key']==body['key'] and body['key']!=old['key']
    assert sha256(encoded(projection)).hexdigest()==body['projection_sha256']
    current_science={k:v for k,v in projection.items() if k not in ('request_key','request_contract')}
    prior_science={k:v for k,v in prior_projection.items() if k!='request_key'}
    assert current_science==prior_science
    scientific.append(sha256(encoded(current_science)).hexdigest())
assert result['state']==prior_result['state'] and result['reopen_scientific_match']
for body,old in zip([row[2] for row in rows if row[1]=='intent'],
                    [row[2] for row in prior_rows if row[1]=='intent'],strict=True):
    audit=body['source_audit'];prior_audit=old['source_audit']
    assert audit['schema']=='h1_phase_exact_source_batch_development_v1'
    assert audit['historical_controller']['replay_contract']=='h1_phase_historical_batch_development_v1'
    for field in ('decision_identity','exogenous_scientific_identity','registry_identity'):
        assert audit[field]==prior_audit[field]


def fraction(value):return Q(int(value['numerator']),int(value['denominator']))


oracle=[]
for lane in ('cfe','joint','network'):
    details=[next(v for v in body['projection']['lanes'] if v['lane_id']==lane) for body in outcomes]
    actions=[detail['business_candidate']['action'] for detail in details]
    calls=[fraction(a['grid_served'])+fraction(a['cfe_served']) for a in actions]
    recovery=[fraction(a['recovery']) for a in actions]
    powers=[fraction(detail['actual_power_mw']) for detail in details]
    debt=Q(0)
    for q,r,p in zip(calls,recovery,powers,strict=True):
        assert q+r<=min(Q(1,2),Q(1,20))
        assert p==250*(Q(1,10)-q+r)
        debt+=q-Q(85,100)*r
    if lane in ('cfe','joint'):
        assert calls==[Q(1,50),Q(0)] and recovery[0]==0
        assert recovery[1]==Q((Q(1,50)/Q(85,100)*10**12).__floor__(),10**12)
        assert debt==Q(3,5_000_000_000_000)
    else:
        assert calls==recovery==[Q(0),Q(0)] and debt==0
    assert all(d['paired_committed'] and not d['halted'] for d in details)
    oracle.append(dict(lane=lane,q=list(map(str,calls)),r=list(map(str,recovery)),
                       remaining_debt=str(debt),actual_power_mw=list(map(str,powers))))
assert all(fraction(body['projection']['reference_request_mw'])==0 for body in outcomes)
jobs=result['normal_job_observations']
assert len(jobs)==2 and len({job['pid'] for job in jobs})==2
for job in jobs:
    assert job['exit_code']==0 and job['whole_job_quiescent']

book=load(root/'static_identity_bookends.json')
assert book['errors']==[] and all(row['original_callable_restored'] for row in book['functions'])
assert book['production_overhead_measured'] is False
remaining=[]
for pid,created in terminal['observed_processes'].items():
    try:
        process=psutil.Process(int(pid))
        if process.create_time()==created and process.is_running():remaining.append(int(pid))
    except psutil.NoSuchProcess:pass
assert remaining==[]

trace=[json.loads(line) for line in (root/'cross_hour_timing.jsonl').read_text(encoding='utf-8').splitlines()]
assert [row['label'] for row in trace]==['start','N0_terminal','hour0_paired','hour1_paired','closed_before_reopen','reopen_verified']
stage_seconds={right['label']:right['monotonic']-left['monotonic'] for left,right in zip(trace,trace[1:])}
owner_seconds=defaultdict(float)
for name,seconds in result['owner_stage_timings']:owner_seconds[name]+=seconds
old_terminal=load(REPO/'results/tables/rq2_h1_cross_hour_v1_non_authoritative/connected_06/terminal.json')
old_request=load(REPO/'results/tables/rq2_h1_cross_hour_v1_non_authoritative/connected_06/request.json')
preserved={}
for name in ('experiments/h1_phase_owner_development_v1.py',
        'experiments/h1_phase_obligation_controller_development_v1.py',
        'experiments/h1_phase_exact_source_current_development_v1.py',
        'experiments/h1_exact_business_development_v1.py',
        'experiments/h1_cross_hour_owner_development_v1.py',
        'tests/test_h1_cross_hour_owner_development_v1.py'):
    path=REPO/name;expected=old_request['sources_sha256'][str(path)]
    assert pin(path)==expected;preserved[name]=expected

original_tests=ast.parse((REPO/'tests/test_h1_cross_hour_owner_development_v1.py').read_text(encoding='utf-8'))
guard_names={node.name for node in original_tests.body if isinstance(node,ast.FunctionDef)
             and node.name.startswith('test_') and node.name!='test_two_hour_three_lane_connected_chain'}
unit02=ET.parse(HERE/'units_02/junit.xml')
guards=[case for case in unit02.iter('testcase') if case.attrib['name'].split('[')[0] in guard_names]
assert len(guards)==36 and all(case.find('failure') is None and case.find('error') is None for case in guards)
unit03=ET.parse(HERE/'units_03/junit.xml')
assert len(list(unit03.iter('testcase')))==23
assert all(case.find('failure') is None and case.find('error') is None for case in unit03.iter('testcase'))
unit02_request=load(HERE/'units_02/request.json')
unit03_request=load(HERE/'units_03/request.json')
for package,source_request,names in (
    ('units_02',unit02_request,tuple(preserved)),
    ('units_03',unit03_request,('experiments/h1_cross_hour_owner_development_v2.py',
        'experiments/h1_phase_exact_source_batch_development_v1.py',
        'experiments/h1_phase_historical_batch_development_v1.py',
        'tests/test_h1_cross_hour_owner_development_v1.py'))):
    for name in names:
        expected=source_request['sources_sha256'][str(REPO/name)]
        assert pin(REPO/name)==expected
        assert pin(HERE/package/'tested_bytes'/name)==expected
unit_test_name='tests/test_h1_cross_hour_batch_development_v2.py'
unit_test_snapshot=HERE/'units_03/tested_bytes'/unit_test_name
assert pin(unit_test_snapshot)==unit03_request['sources_sha256'][str(REPO/unit_test_name)]
# After units_03, only the unselected saved-probe body acquired extra faults.
# Compare the full remaining AST, including imports and unit fixture context.
def unit_ast(path):
    tree=ast.parse(path.read_text(encoding='utf-8'))
    tree.body=[node for node in tree.body if not (isinstance(node,ast.FunctionDef)
        and node.name=='test_saved_two_hour_batch_matches_independent_prefix_oracle')]
    return ast.dump(tree,include_attributes=False)
assert unit_ast(unit_test_snapshot)==unit_ast(REPO/unit_test_name)
selected_unit_names={arg.split('::',1)[1] for arg in unit03_request['command'] if '::' in arg}
assert all(case.attrib['name'].split('[')[0] in selected_unit_names for case in unit03.iter('testcase'))
assert inventory(roots)==before and inventory(prior_roots)==prior_before

report=dict(status='DRAFT_NONAUTHORITATIVE',attempt=label,terminal=terminal,
    bindings={str(path):pin(path) for path in (Path(__file__),attempt/'request.json',attempt/'terminal.json',
        result_path,root/'owner_non_authoritative/owner.sqlite',baseline/'owner_non_authoritative/owner.sqlite',
        HERE/'units_02/junit.xml',HERE/'units_03/junit.xml',HERE/'units_02/request.json',
        HERE/'units_03/request.json',unit_test_snapshot,HERE/'saved_probe_02/terminal.json')},
    saved_file_count=len(before),all_saved_bytes_match=True,baseline_saved_bytes_unchanged=True,
    paired_lane_hours=6,oracle=oracle,scientific_projections_equal_to_v1=True,
    scientific_projection_sha256=scientific,request_namespace_changed=True,final_scientific_state_equal_to_v1=True,
    preserved_predecessor_code_sha256=preserved,
    inherited_v1_guard_passes=36,current_v2_boundary_passes=23,
    reused_unit_source_and_test_snapshot_sha_bound=True,unit03_selected_module_ast_unchanged=True,
    unit02_failed_new_test_retained=True,unit03_fixed_records_packing_test=True,
    historical_api_calls=20,historical_api_prefix_hour_weight=28,
    parent_inspect_traversals=40,parent_inspect_prefix_hour_weight=56,
    excludes_independent_historical_snapshot_anchor_traversals=True,
    max_selected_frame_bytes=max(row['selected_frame_bytes'] for row in metrics),
    nonoverlapping_trace_seconds=stage_seconds,nested_owner_stage_seconds=dict(owner_seconds),
    baseline_outer_seconds=old_terminal['outer_seconds'],outer_seconds=terminal['outer_seconds'],
    single_observed_wall_ratio=terminal['outer_seconds']/old_terminal['outer_seconds'],
    wall_ratio_is_not_production_or_causal_estimate=True,production_overhead_measured=False,
    observed_processes_still_remaining=remaining,complete_process_tree_absence_proven=False,
    formal_execution_ready=False,resource_admission=False,formal_result=False,native_execution_authorized=False)
with output.open('x',encoding='utf-8') as stream:
    json.dump(report,stream,indent=2,ensure_ascii=False);stream.write('\n')
print(json.dumps(dict(output=str(output),saved_files=len(before),scientific_equivalence=True,
    outer_seconds=terminal['outer_seconds'],historical_api_weight=28,formal_result=False)))
