"""Check the one-function scope and collect current nodes before execution."""
import ast
from capture_checks import ROOT,OUT,PRIOR,entry,read,save,capture
import json

baseline=read('baseline_01.snapshot.json')['sources']; report={}
for name,item in baseline.items():
    def definitions(raw):
        return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body
            if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    old=definitions((ROOT/item['snapshot']).read_bytes());new=definitions((ROOT/name).read_bytes())
    changed=sorted(k for k in old if old[k]!=new.get(k))
    assert changed==(['_expectation_adapter'] if name==entry.NEW_SOURCES[1] else []),(name,changed)
    report[name]=dict(previous_definitions=len(old),changed_definitions=changed,new_definitions=sorted(set(new)-set(old)))
selected=entry.source_pins();before=read('baseline_sources.json')
assert set(selected)==set(before) and all(selected[n]==before[n] for n in before if n not in entry.NEW_SOURCES[1:3])
save('legacy_ast_check.json',dict(authority='DRAFT_NONAUTHORITATIVE',sources=report,unchanged_dependency_paths=47))
capture('collection_03','static',[str(entry.EXE),'-B','-m','pytest','--collect-only','-q',
    'tests/test_staged_rts24_saved_fresh_adoption_v1.py','-p','no:cacheprovider'],7)
nodes=[line for line in (OUT/'collection_03.stdout.log').read_text(encoding='utf-8').splitlines()
    if line.startswith('tests/') and '::test_' in line]
previous=json.loads((PRIOR/'group_admission_02.json').read_bytes())['groups']
new=[n for n in nodes if '::test_saved_source_bytes_' in n]
assert len(new)==10
groups=dict(source_bytes_and_smoke_04=new+previous['expectation_smoke_09'],
    expectation_rest_05=previous['expectation_rest_05'],expectation_rest_06=previous['expectation_rest_06'],
    binding_regression_07=previous['binding_regression_07'])
flat=[n for group in groups.values() for n in group]
assert len(flat)==len(set(flat))==63 and set(flat)<=set(nodes)
save('collected_nodes.json',nodes)
save('group_admission.json',dict(authority='DRAFT_NONAUTHORITATIVE',groups=groups,
    caps=dict(source_bytes_and_smoke_04=35,expectation_rest_05=35,expectation_rest_06=35,binding_regression_07=40),
    pytest_cap_seconds=160,static_cap_seconds=40,total_cap_seconds=200,current_new_nodes=10,
    source_raw_bytes=sum(p['bytes'] for p in selected.values()),source_raw_cap_bytes=entry.EXPECTATION_SOURCE_RAW_CAP,
    actual_saved_F_execution=False,F_launch_admitted=False))
print(json.dumps(dict(groups={n:len(g) for n,g in groups.items()},source_raw_bytes=sum(p['bytes'] for p in selected.values()))))
