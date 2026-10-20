"""Freeze successful detached replay evidence without granting reopen authority."""
from contextlib import closing
from fractions import Fraction as Q
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as ET

import psutil

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[2]
load=lambda p:json.loads(p.read_bytes())
pin=lambda p:sha256(p.read_bytes()).hexdigest()
label='detached_03';attempt=HERE/label
request=load(attempt/'request.json');terminal=load(attempt/'terminal.json')
assert terminal['exit_code']==0 and terminal['reason'] is None and terminal['source_unchanged']
assert terminal['observed_processes_absent'] and not terminal['monitor_errors'] and not terminal['cleanup_events']
for name,expected in request['sources_sha256'].items():
    assert pin(Path(name))==pin(attempt/'tested_bytes'/Path(name).relative_to(REPO))==expected
snapshot=load(HERE/'connected_02_closed_snapshot.json')
assert all(pin(Path(name))==expected for name,expected in snapshot['files_sha256'].items())
root=Path(snapshot['case']);cases=list(Path(terminal['retained_root']).glob('test_frozen_three_hour_prefix_*'))
assert len(cases)==1
result_path=cases[0]/'detached_saved_replay.json';result=load(result_path)
assert result['original_attempt_exit_code']==15 and result['original_attempt_reason']=='no_progress'
for name in ('original_authenticated_reopen','independent_retained_heads','original_reopen_before_after_equality_verified',
        'original_static_bookend_verified','original_RAM_scientific_equality_verified','owner_or_holder_constructor_called',
        'live_continuation_or_adoption_authorized','formal_result'):
    assert result[name] is False
assert result['new_normal_jobs']==result['new_selector_calls']==result['real_native_calls']==0
assert result['all_462_saved_bytes_unchanged'] and result['detached_three_hour_projection_bytes_equal']
tests=list(ET.parse(attempt/'junit.xml').iter('testcase'))
assert len(tests)==1 and tests[0].attrib['name']=='test_frozen_three_hour_prefix_detached_replay'
assert tests[0].find('failure') is None and tests[0].find('error') is None
book_path=cases[0]/'static_identity_bookends.json';book=load(book_path)
assert book['errors']==[] and len(book['functions'])==15
active=[]
for row in book['functions']:
    assert row['original_callable_restored'] and len(row['bookends'])==row['original_computations']
    if row['calls']:
        assert row['original_computations']>0;active.append(row['function'])
    assert all(pair['before']==pair['after'] for pair in row['bookends'])
assert active and book['dynamic_source_or_history_or_state_cached'] is False
with closing(sqlite3.connect((root/'owner_non_authoritative/owner.sqlite').as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
    outcomes=[json.loads(raw) for (raw,) in db.execute("SELECT body FROM events WHERE kind='outcome' ORDER BY seq")]
fraction=lambda v:Q(int(v['numerator']),int(v['denominator']))
quantities=[];debts={}
for key in ('cfe','joint','network'):
    debt=Q(0)
    for hour,outcome in enumerate(outcomes):
        detail=next(v for v in outcome['projection']['lanes'] if v['lane_id']==key)
        if not detail['paired_committed']:continue
        action=detail['business_candidate']['action']
        q=fraction(action['grid_served'])+fraction(action['cfe_served']);r=fraction(action['recovery'])
        power=fraction(detail['actual_power_mw'])
        assert 0<=q<=Q(1,20) and q+r<=Q(1,2) and 0<=r<=Q(9,100) and r<=debt/Q(85,100)
        if key!='network':assert r<=max(Q(0),(1-(Q(3,5) if hour<2 else Q(1,5)))*Q(1,10)/Q(1,2)-Q(1,10))
        assert power==250*(Q(1,10)-q+r);debt+=q-Q(85,100)*r
        quantities.append(dict(hour=hour,lane=key,q=str(q),r=str(r),power_mw=str(power)))
    debts[key]=str(debt)
unit_terminal=load(HERE/'units_06/terminal.json')
kernel_path=next(Path(unit_terminal['retained_root']).glob('*/outage_kernel_oracle.json'));kernel=load(kernel_path)
assert debts==kernel['debts']==result['debts']
assert sorted(quantities,key=lambda v:(v['hour'],v['lane']))==sorted(kernel['quantities'],key=lambda v:(v['hour'],v['lane']))
metrics=result['batch_observations'];assert len(metrics)==2 and sum(v['completed_hours'] for v in metrics)==6
assert sum(v['parent_inspect_traversals'] for v in metrics)==4
for pid,created in terminal['observed_processes'].items():
    try:assert psutil.Process(int(pid)).create_time()!=created
    except psutil.NoSuchProcess:pass
assert all(pin(Path(name))==expected for name,expected in snapshot['files_sha256'].items())
bindings=[Path(__file__),attempt/'request.json',attempt/'terminal.json',attempt/'junit.xml',result_path,book_path,
    HERE/'connected_02_closed_snapshot.json',HERE/'connected_02/request.json',HERE/'connected_02/terminal.json',kernel_path]
report=dict(status='DRAFT_NONAUTHORITATIVE',bindings={str(p):pin(p) for p in bindings},outer_seconds=terminal['outer_seconds'],
    saved_files_preserved=462,independent_arithmetic_matches_unit06=True,quantities=quantities,debts=debts,
    detached_projection_bytes_equal=True,paired_lane_hours=7,saved_selector_records=34,
    active_static_identity_targets_bookended=active,new_normal_jobs=0,new_selector_calls=0,real_native_calls=0,
    original_attempt_exit_code=15,original_attempt_reason='no_progress',original_authenticated_reopen=False,
    independent_retained_heads=False,original_RAM_scientific_equality_verified=False,
    original_reopen_before_after_equality_verified=False,original_static_bookend_verified=False,
    formal_execution_ready=False,resource_admission=False,formal_result=False)
with (HERE/'detached_03_postcheck.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2);stream.write('\n')
print(json.dumps(dict(detached_projection_bytes_equal=True,preserved_files=462,original_authenticated_reopen=False)))
