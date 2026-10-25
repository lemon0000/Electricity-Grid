"""Admit exact independent data tests plus the 63 prior relevant regressions."""
import ast
import json
from common import ROOT,OUT,PRIOR,SOURCE_PATHS,read,selected,epoch,save

baseline=read('baseline_01.snapshot.json')['sources'];ast_report={}
for name,item in baseline.items():
    def definitions(raw):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    old=definitions((ROOT/item['snapshot']).read_bytes());new=definitions((ROOT/name).read_bytes())
    assert all(new.get(k)==v for k,v in old.items()),name
    ast_report[name]=dict(previous_definitions=len(old),all_unchanged=True,added=sorted(set(new)-set(old)))
save('legacy_ast_check.json',dict(authority='DRAFT_NONAUTHORITATIVE',sources=ast_report,unchanged_dependencies=47))
nodes=[line for line in (OUT/'collection_03.stdout.log').read_text(encoding='utf-8').splitlines() if line.startswith('tests/') and '::test_' in line]
fresh=[n for n in nodes if '::test_saved_successor_' in n]
smoke=[n for n in fresh if any(s in n for s in ('positive_is_immutable','version_is_frozen','has_no_legacy'))]
rest=[n for n in fresh if n not in smoke]
prior=ROOT/'results/tables/staged_rts24_saved_fresh_source_bytes_reuse_v1_non_authoritative/checks_01'
old=json.loads((prior/'group_admission_02.json').read_bytes())['groups']
groups=dict(successor_smoke_05=smoke,successor_a_06=rest[::2],successor_b_07=rest[1::2],
    source_expectation_08=old['source_bytes_and_smoke_09'],expectation_a_09=old['expectation_rest_05'],
    expectation_b_10=old['expectation_rest_06'],binding_11=old['binding_regression_07'])
caps=dict(successor_smoke_05=12,successor_a_06=25,successor_b_07=25,source_expectation_08=23,
    expectation_a_09=32,expectation_b_10=26,binding_11=35)
flat=[n for group in groups.values() for n in group]
assert len(smoke)==3 and len(flat)==len(set(flat))==len(fresh)+63 and set(flat)<=set(nodes)
assert sum(caps.values())==178 and 200-sum(caps.values())>=22
source=selected()
save('collected_nodes.json',nodes)
save('group_admission.json',dict(authority='DRAFT_NONAUTHORITATIVE',groups=groups,caps=caps,
    new_nodes=len(fresh),regression_nodes=63,source_pins=source,source_epoch=epoch(source),
    pytest_cap_seconds=200,static_cap_seconds=40,total_cap_seconds=240,
    failed_narrow_group_reserve_seconds=22,static_finalization_reserve_seconds=24,
    actual_saved_F_execution=False,F_launch_admitted=False))
print(json.dumps(dict(groups={k:len(v) for k,v in groups.items()},new_nodes=len(fresh),regression_nodes=63,
    admitted_caps_seconds=178,failure_reserve_seconds=22,source_epoch=epoch(source))))
