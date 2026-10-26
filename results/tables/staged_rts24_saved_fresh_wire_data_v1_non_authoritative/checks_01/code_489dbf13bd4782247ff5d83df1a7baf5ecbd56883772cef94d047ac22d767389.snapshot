"""Create-only exact collection/Source admission; all old480 retained for final regression."""
import ast
from hashlib import sha256
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
baseline=read(OUT/'baseline.json');collection=read(OUT/'collection_02.harness.json');captured=read(OUT/'collection_02.exit.json')
assert captured['accepted'] and captured['returncode']==0 and collection['pytest_exit_code']==0
assert collection['unexpected_new_collection_nodes']==[]
previous=read(ROOT/'results/tables/staged_rts24_saved_fresh_role_data_v1_non_authoritative/checks_01/admission.json')
old_nodes=[n for group in previous['groups'].values() for n in group];assert len(old_nodes)==len(set(old_nodes))==480
new_nodes=[n for n in collection['collected_nodes'] if '::test_saved_wire_' in n]
assert new_nodes and not set(new_nodes)&set(old_nodes)
assert len(collection['collected_nodes'])==len(set(collection['collected_nodes']))==480+len(new_nodes)
assert set(collection['collected_nodes'])==set(old_nodes)|set(new_nodes)
for n,before in baseline['old_nodes'].items():
    after=[sha256(ast.dump(v,include_attributes=False).encode()).hexdigest() for v in ast.parse((ROOT/n).read_bytes()).body]
    if n.startswith('experiments/'):assert after[:len(before)-1]==before[:-1] and after[-1]==before[-1]
    elif n.startswith('tests/'):assert after[:len(before)]==before
    else:assert after==before
sources={n:pin((ROOT/n).read_bytes()) for n in baseline['sources']};assert sources==captured['source_pins']
assert all(sources[n]==p for n,p in baseline['sources'].items() if n not in ('experiments/staged_rts24_saved_fresh_adoption_v1.py','tests/test_staged_rts24_saved_fresh_adoption_v1.py'))
groups={};caps={}
labels=dict(legacy_fast=18,binding_14=36,data_a_09=22,data_b_10=22,expectation_a_12=32,expectation_b_13=26,source_expectation_11=22)
fast=[n for label in ('data_smoke_08','self_smoke_06','self_rest_07','direct_compare_09') for n in []]
# The role-data admission already merged these four older groups into legacy_fast.
for label,cap in labels.items():groups['r1_old_'+label]=previous['groups'][label];caps['r1_old_'+label]=cap
role_nodes=[n for n in old_nodes if '::test_saved_role_data_' in n];assert len(role_nodes)==198
assert not set(role_nodes)&{n for g in groups.values() for n in g}
for i in range(3):groups['r1_old_roles_'+str(i+1)]=role_nodes[i::3];caps['r1_old_roles_'+str(i+1)]=37
smoke_names=('test_saved_wire_literal_roots','test_saved_wire_root_globals','test_saved_wire_ram_startup_join','test_saved_wire_ram_authority_stays_false')
smoke=[n for n in new_nodes if any(('::'+name+'[' in n or n.endswith('::'+name)) for name in smoke_names)]
assert smoke;groups['r1_new_smoke']=smoke;caps['r1_new_smoke']=18
remaining=[n for n in new_nodes if n not in smoke]
for i in range(3):
    part=remaining[i::3]
    if part:groups['r1_new_'+str(i+1)]=part;caps['r1_new_'+str(i+1)]=23
selected=[n for g in groups.values() for n in g]
assert len(selected)==len(set(selected))==480+len(new_nodes) and set(selected)==set(collection['collected_nodes'])
assert sum(caps.values())<=376
value=dict(authority='DRAFT_NONAUTHORITATIVE',plan_id='root_repair_01',source_pins=sources,source_epoch=sha256(raw(sources)).hexdigest(),
    groups=groups,caps=caps,run_order=['r1_new_smoke',*[n for n in groups if n.startswith('r1_new_') and n!='r1_new_smoke'],*[n for n in groups if n.startswith('r1_old_')]],
    new_nodes=len(new_nodes),regression_nodes=480,current_nodes=len(selected),pytest_cap_seconds=420,static_cap_seconds=120,total_cap_seconds=540,
    helper_pins={p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in OUT.glob('*.py')},collection_pin=pin((OUT/'collection_02.harness.json').read_bytes()),
    actual_F=False,scientific_evidence_adopted=False,resource_admission=False,formal_result=False)
with (OUT/'admission.json').open('xb') as f:f.write(raw(value))
print(json.dumps(dict(current_nodes=len(selected),new_nodes=len(new_nodes),old_nodes=480,groups=len(groups),group_caps=sum(caps.values()),reserve=420-sum(caps.values()),source_epoch=value['source_epoch']),sort_keys=True))
