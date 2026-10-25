"""Exact current collection plus all 184 prior regressions; no science imports."""
import ast
import json
from common import ROOT,OUT,PRIOR,SOURCE_PATHS,read,selected,epoch,save

nodes=[line for line in (OUT/'collection_03.stdout.log').read_text(encoding='utf-8').splitlines()
    if line.startswith('tests/') and '::test_' in line]
new=[n for n in nodes if '::test_saved_self_anchor_' in n]
smoke=[n for n in new if 'observes_real_current' in n or 'closed_constructor' in n]
old=json.loads((PRIOR/'group_admission_02.json').read_bytes())['groups']
groups=dict(self_smoke_05=smoke,self_rest_06=[n for n in new if n not in smoke],
    data_smoke_07=old['successor_smoke_12'],data_a_08=old['successor_a_13'],data_b_09=old['successor_b_07'],
    source_expectation_10=old['source_expectation_08'],expectation_a_11=old['expectation_a_09'],
    expectation_b_12=old['expectation_b_10'],binding_13=old['binding_11'])
caps=dict(self_smoke_05=12,self_rest_06=25,data_smoke_07=12,data_a_08=25,data_b_09=25,
    source_expectation_10=23,expectation_a_11=32,expectation_b_12=26,binding_13=40)
flat=[n for group in groups.values() for n in group]
assert len(smoke)==2 and len(flat)==len(set(flat))==184+len(new) and set(flat)<=set(nodes)
assert sum(caps.values())==220 and 240-sum(caps.values())>=20
ast_report={}
for name,item in read('baseline_01.snapshot.json')['sources'].items():
    def defs(raw):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    before=defs((ROOT/item['snapshot']).read_bytes());after=defs((ROOT/name).read_bytes())
    assert all(after.get(k)==v for k,v in before.items()),name
    ast_report[name]=dict(previous_definitions=len(before),all_unchanged=True,added=sorted(set(after)-set(before)))
source=selected()
save('legacy_ast_check.json',dict(sources=ast_report,unchanged_dependencies=47))
save('collected_nodes.json',nodes)
save('group_admission.json',dict(authority='DRAFT_NONAUTHORITATIVE',groups=groups,caps=caps,
    new_nodes=len(new),regression_nodes=184,source_pins=source,source_epoch=epoch(source),
    pytest_cap_seconds=240,static_cap_seconds=60,total_cap_seconds=300,
    failed_group_reserve_seconds=20,actual_saved_F_execution=False,F_launch_admitted=False))
print(json.dumps(dict(groups={k:len(v) for k,v in groups.items()},new_nodes=len(new),regression_nodes=184,
    planned_caps_seconds=sum(caps.values()),source_epoch=epoch(source))))
