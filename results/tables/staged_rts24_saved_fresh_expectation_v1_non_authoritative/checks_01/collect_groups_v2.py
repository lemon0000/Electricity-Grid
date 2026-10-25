"""Verify unchanged legacy ASTs, then collect the final local-probe epoch."""
import ast
import json
from capture_checks import ROOT,OUT,entry,capture,save

baseline=json.loads((OUT/'baseline_01.snapshot.json').read_bytes())['sources']
report={}
for name,item in baseline.items():
    old=ast.parse((ROOT/item['snapshot']).read_bytes());new=ast.parse((ROOT/name).read_bytes())
    old_defs={n.name:ast.dump(n,include_attributes=False) for n in old.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    new_defs={n.name:ast.dump(n,include_attributes=False) for n in new.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    assert all(new_defs.get(k)==v for k,v in old_defs.items()),name
    report[name]=dict(legacy_definitions=len(old_defs),unchanged=True,new_definitions=sorted(set(new_defs)-set(old_defs)))
before=json.loads((OUT/'baseline_sources.json').read_bytes());after=entry.source_pins()
mutable=set(entry.NEW_SOURCES[1:3])
assert set(before)==set(after) and all(before[n]==after[n] for n in before if n not in mutable)
save('legacy_ast_check.json',dict(authority='DRAFT_NONAUTHORITATIVE',sources=report,unchanged_dependency_paths=47))
target='tests/test_staged_rts24_saved_fresh_adoption_v1.py'
capture('collection_08','static',[str(entry.EXE),'-B','-m','pytest','--collect-only','-q',target,'-p','no:cacheprovider'],8)
nodes=[line for line in (OUT/'collection_08.stdout.log').read_text(encoding='utf-8').splitlines()
    if line.startswith('tests/') and '::test_' in line]
new=[n for n in nodes if '::test_saved_expectation_' in n]
smoke=[n for n in new if any(key in n for key in ('projection_has_equal_image','G0_G2_G3_and_H3'))]
remaining=[n for n in new if n not in smoke]
old=json.loads((OUT/'group_admission_01.json').read_bytes())
groups=dict(expectation_smoke_09=smoke,expectation_rest_05=remaining[::2],expectation_rest_06=remaining[1::2],
    binding_regression_07=old['groups']['binding_regression_07'])
caps=dict(expectation_smoke_09=25,expectation_rest_05=35,expectation_rest_06=35,binding_regression_07=40)
spent=sum(json.loads(p.read_bytes())['wall_seconds'] for p in OUT.glob('*.exit.json')
    if json.loads(p.read_bytes())['kind']=='pytest')
assert len(smoke)==2 and len(new)==35 and spent+sum(caps.values())<=160
save('collected_nodes_v2.json',nodes)
save('group_admission_02.json',dict(authority='DRAFT_NONAUTHORITATIVE',groups=groups,caps=caps,previous_pytest_seconds=spent,
    pytest_cap_seconds=160,static_cap_seconds=40,total_cap_seconds=200,production_input_gateway_open=False,
    transitive_global_binding_closed=False,actual_saved_F_execution=False,F_launch_admitted=False))
print(json.dumps(dict(groups={n:len(v) for n,v in groups.items()},previous_pytest_seconds=spent)))
