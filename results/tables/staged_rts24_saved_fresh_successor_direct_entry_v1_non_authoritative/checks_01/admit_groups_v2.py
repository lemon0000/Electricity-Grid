"""Admit the exact current data regressions and new parent-comparator tests."""
import ast
import json
from common import ROOT,OUT,PRIOR,SOURCE_PATHS,read,selected,epoch,save

nodes=[line for line in (OUT/'collection_07.stdout.log').read_text(encoding='utf8').splitlines() if line.startswith('tests/') and '::test_' in line]
new=[n for n in nodes if '::test_saved_direct_entry_' in n]
previous=json.loads((PRIOR/'group_admission_04.json').read_bytes())['groups']
groups=dict(direct_compare_05=new,self_smoke_06=previous['self_smoke_19'],self_rest_07=previous['self_rest_20'],
    data_smoke_08=previous['data_smoke_07'],data_a_09=previous['data_a_08'],data_b_10=previous['data_b_09'],
    source_expectation_11=previous['source_expectation_10'],expectation_a_12=previous['expectation_a_11'],
    expectation_b_13=previous['expectation_b_12'],binding_14=previous['binding_13'])
caps=dict(direct_compare_05=12,self_smoke_06=10,self_rest_07=14,data_smoke_08=12,data_a_09=25,data_b_10=25,
    source_expectation_11=23,expectation_a_12=32,expectation_b_13=26,binding_14=40)
flat=[n for group in groups.values() for n in group]
assert len(flat)==len(set(flat))==218+len(new) and set(flat)<=set(nodes)
assert sum(caps.values())==219 and 240-sum(caps.values())>=20
report={}
for name,item in read('baseline_01.snapshot.json')['sources'].items():
    def defs(raw):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    before=defs((ROOT/item['snapshot']).read_bytes());after=defs((ROOT/name).read_bytes())
    assert all(after.get(k)==v for k,v in before.items()),name
    report[name]=dict(previous_definitions=len(before),all_unchanged=True,added=sorted(set(after)-set(before)))
source=selected()
save('legacy_ast_check_v2.json',dict(sources=report,unchanged_dependencies=47))
save('collected_nodes_v2.json',nodes)
save('group_admission_02.json',dict(authority='DRAFT_NONAUTHORITATIVE',groups=groups,caps=caps,new_nodes=len(new),regression_nodes=218,
    source_pins=source,source_epoch=epoch(source),pytest_cap_seconds=240,static_cap_seconds=80,total_cap_seconds=320,
    failed_group_reserve_seconds=21,actual_saved_F_execution=False,F_launch_admitted=False))
print(json.dumps(dict(new_nodes=len(new),regression_nodes=218,total_nodes=len(flat),caps_seconds=sum(caps.values()),source_epoch=epoch(source))))
