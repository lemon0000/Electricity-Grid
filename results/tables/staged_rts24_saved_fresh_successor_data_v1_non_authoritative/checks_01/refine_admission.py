"""Admit two explicit decorator cases and stronger metadata-denial coverage."""
import ast
from common import ROOT,OUT,SOURCE_PATHS,read,selected,epoch,save

old=read('group_admission.json');prior_nodes=read('collected_nodes.json')
test_name='tests/test_staged_rts24_saved_fresh_adoption_v1.py'
function='test_saved_successor_result_all_accessors_recheck_commit'
new_nodes=[test_name+'::'+function+'['+name+']' for name in ('anchor_sha','commit')]
nodes=prior_nodes+new_nodes
snapshot=read('successor_a_06.snapshot.json')['sources'][SOURCE_PATHS[2]]['snapshot']
def defs(raw):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
before=defs((ROOT/snapshot).read_bytes());after=defs((ROOT/SOURCE_PATHS[2]).read_bytes())
changed={n for n in before if before[n]!=after[n]}
assert changed=={function,'test_saved_successor_version_is_frozen_and_io_is_not_observed'}
current_test=next(n for n in ast.parse((ROOT/test_name).read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name==function)
parameters=ast.literal_eval(current_test.decorator_list[0].args[1])
assert parameters==['_raw','_request_raw','_expectation_raw','basis_sha','anchor_sha','spec_pin','contract_shas','declared_now','commit']
groups={k:v for k,v in old['groups'].items() if k not in ('successor_smoke_05','successor_a_06','successor_b_07')}
fresh=[n for n in nodes if '::test_saved_successor_' in n];smoke=old['groups']['successor_smoke_05'];rest=[n for n in fresh if n not in smoke]
groups.update(successor_smoke_12=smoke,successor_a_13=rest[::2],successor_b_07=rest[1::2])
caps={k:v for k,v in old['caps'].items() if k in groups}
caps.update(successor_smoke_12=12,successor_a_13=25,successor_b_07=25)
spent=sum(read(p.name)['wall_seconds'] for p in OUT.glob('*.exit.json') if read(p.name)['kind']=='pytest')
assert spent+sum(caps.values())<=200 and len(fresh)==121
flat=[n for g in groups.values() for n in g];assert len(flat)==len(set(flat))==184
source=selected()
save('group_admission_02.json',dict(old,groups=groups,caps=caps,new_nodes=121,source_pins=source,source_epoch=epoch(source),
    previous_pytest_seconds=spent,unused_cap_seconds=200-spent-sum(caps.values()),
    refinement='two result-state cases plus metadata denial; only those two new test definitions changed'))
save('refined_nodes.json',nodes)
print(__import__('json').dumps(dict(new_nodes=121,total_nodes=184,prior_epoch_pytest_seconds=spent,
    planned_caps=sum(caps.values()),source_epoch=epoch(source))))
