"""Exact collection, Source/AST and fixed pytest-group admission; stdlib only."""
import ast
from hashlib import sha256
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
def nodes(p):return [sha256(ast.dump(n,include_attributes=False).encode()).hexdigest() for n in ast.parse(p.read_bytes()).body]

baseline=read(OUT/'baseline.json')
failed_collection=read(OUT/'collection_02.exit.json');successful_collection=read(OUT/'collection_retry_04.exit.json')
assert failed_collection['returncode']==1 and failed_collection['accepted'] is False and failed_collection['error']=='timeout'
assert successful_collection['returncode']==0 and successful_collection['accepted']
assert successful_collection['source_epoch']==failed_collection['source_epoch']
assert successful_collection['retry_of']==dict(path=(OUT/'collection_02.exit.json').relative_to(ROOT).as_posix(),pin=pin((OUT/'collection_02.exit.json').read_bytes()))
collection=read(OUT/'collection_retry_04.harness.json');assert collection['pytest_exit_code']==0
collected=collection['collected_nodes'];assert len(set(collected))==len(collected)
previous=read(ROOT/'results/tables/staged_rts24_saved_fresh_successor_direct_entry_v1_non_authoritative/checks_01/group_admission_03.json')
old_nodes=[node for group in previous['groups'].values() for node in group]
assert len(old_nodes)==len(set(old_nodes))==282 and set(old_nodes)<=set(collected)
new_nodes=[n for n in collected if '::test_saved_role_data_' in n]
assert len(new_nodes)==198 and not set(new_nodes).intersection(old_nodes),len(new_nodes)
assert len(collected)==480 and set(collected)==set(old_nodes)|set(new_nodes)
assert collection['unexpected_new_collection_nodes']==[]
for name,before in baseline['old_nodes'].items():
    after=nodes(ROOT/name)
    if name.startswith('experiments/'):
        assert after[:len(before)-1]==before[:-1] and after[-1]==before[-1]
    elif name.startswith('tests/'):assert after[:len(before)]==before
    else:assert after==before
sources={n:pin((ROOT/n).read_bytes()) for n in baseline['sources']}
assert sources==successful_collection['source_pins']
assert all(sources[n]==p for n,p in baseline['sources'].items() if not n.startswith(('experiments/','tests/test_staged_rts24_saved_fresh_adoption_v1')))
groups=dict(previous['groups']);caps=dict(previous['caps'])
fast_names=('data_smoke_08','self_smoke_06','self_rest_07','direct_compare_09')
fast=[n for label in fast_names for n in groups.pop(label)]
assert len(fast)==len(set(fast)) and set(fast)=={n for label in fast_names for n in previous['groups'][label]}
for label in fast_names:del caps[label]
groups['legacy_fast']=fast;caps.update(legacy_fast=24,binding_14=42,data_a_09=26,data_b_10=25,
    expectation_a_12=40,expectation_b_13=32,source_expectation_11=25)
smoke=[n for n in new_nodes if any('::'+name+'[' in n for name in ('test_saved_role_data_positive','test_saved_role_data_no_live_effects','test_saved_role_data_closed_result_type'))]
groups['role_smoke']=smoke;caps['role_smoke']=25
remaining=[n for n in new_nodes if n not in smoke]
for index in range(4):
    label='role_'+str(index+1);groups[label]=remaining[index::4];caps[label]=20
assert sum(caps.values())==319 and 360-sum(caps.values())>=40
selected=[n for group in groups.values() for n in group]
assert len(selected)==len(set(selected))==480 and set(selected)==set(old_nodes)|set(new_nodes)
helpers={p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in OUT.glob('*.py')}
value=dict(authority='DRAFT_NONAUTHORITATIVE',groups=groups,caps=caps,run_order=['role_smoke','legacy_fast',*[n for n in previous['groups'] if n not in fast_names],*[f'role_{n}' for n in range(1,5)]],
    source_pins=sources,source_epoch=sha256(raw(sources)).hexdigest(),helper_pins=helpers,new_nodes=198,regression_nodes=282,
    current_nodes=480,pytest_cap_seconds=360,static_cap_seconds=120,total_cap_seconds=480,failed_group_reserve_seconds=41,
    successful_collection_label='collection_retry_04',historical_collection_timeout='collection_02',
    actual_F=False,scientific_evidence_adopted=False,resource_admission=False,formal_result=False)
encoded=raw(value);assert len(encoded)<=256*1024
with (OUT/'admission.json').open('xb') as stream:stream.write(encoded)
print(json.dumps(dict(new_nodes=198,regression_nodes=282,current_nodes=480,groups=len(groups),group_caps=sum(caps.values()),
    reserve=41,source_epoch=value['source_epoch'],actual_F=False),sort_keys=True))
