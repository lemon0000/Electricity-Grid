"""Current Source re-admission after PRE_SEAL bootstrap positive-case addition."""
import ast
from hashlib import sha256
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
previous=read(OUT/'admission_r2.json');captured=read(OUT/'collection_r3.exit.json');collection=read(OUT/'collection_r3.harness.json')
assert captured['accepted'] and collection['pytest_exit_code']==0 and not collection['unexpected_new_collection_nodes']
sources={n:pin((ROOT/n).read_bytes()) for n in previous['source_pins']};assert sources==captured['source_pins']
old={n for k,v in previous['groups'].items() if '_old_' in k for n in v};assert len(old)==480
new=[n for n in collection['collected_nodes'] if '::test_saved_wire_' in n]
assert len(set(collection['collected_nodes']))==len(collection['collected_nodes'])==480+len(new)
assert set(collection['collected_nodes'])==old|set(new)
baseline=read(OUT/'baseline.json')
for name,before in baseline['old_nodes'].items():
    tree=ast.parse((ROOT/name).read_bytes());after=[sha256(ast.dump(n,include_attributes=False).encode()).hexdigest() for n in tree.body]
    if name.startswith('experiments/'):assert after[:len(before)-1]==before[:-1] and after[-1]==before[-1]
    elif name.startswith('tests/'):assert after[:len(before)]==before
    else:assert after==before
groups={k.replace('r2_','r3_',1):v for k,v in previous['groups'].items() if '_old_' in k}
caps={k.replace('r2_','r3_',1):v for k,v in previous['caps'].items() if '_old_' in k}
smoke_names=('test_saved_wire_literal_roots','test_saved_wire_root_globals','test_saved_wire_ram_startup_join','test_saved_wire_ram_authority_stays_false')
smoke=[n for n in new if any(n.endswith('::'+name) or '::'+name+'[' in n for name in smoke_names)]
groups['r3_new_smoke']=smoke;caps['r3_new_smoke']=18
rest=[n for n in new if n not in smoke]
for i in range(3):groups['r3_new_'+str(i+1)]=rest[i::3];caps['r3_new_'+str(i+1)]=23
assert sum(caps.values())==376
plan={**previous,'plan_id':'root_repair_03','source_pins':sources,'source_epoch':sha256(raw(sources)).hexdigest(),
    'groups':groups,'caps':caps,'run_order':[k for k in groups if '_new_' in k]+[k for k in groups if '_old_' in k],
    'new_nodes':len(new),'current_nodes':480+len(new),'collection_reused_for_identical_Source':False,
    'collection_pin':pin((OUT/'collection_r3.harness.json').read_bytes()),'previous_plan_pin':pin((OUT/'admission_r2.json').read_bytes()),
    'helper_pins':{p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in OUT.glob('*.py')}}
with (OUT/'admission_r3.json').open('xb') as f:f.write(raw(plan))
print(json.dumps(dict(source_epoch=plan['source_epoch'],new_nodes=len(new),current_nodes=plan['current_nodes']),sort_keys=True))
