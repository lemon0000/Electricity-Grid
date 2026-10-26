"""Preserve the failed fixture attempt and re-admit unchanged Source/nodeids."""
import importlib.util
import json
from hashlib import sha256
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
plan=json.loads((OUT/'admission.json').read_bytes())
assert {n:pin((ROOT/n).read_bytes()) for n in plan['source_pins']}==plan['source_pins']
failed=json.loads((OUT/'r1_new_smoke.exit.json').read_bytes());assert not failed['accepted']
path=OUT/'fixture_builder.py';spec=importlib.util.spec_from_file_location('fixture_static_repair',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);case=module.build()
assert set(case['roles'])=={'controller','parent','fresh'}
plan.update(plan_id='root_repair_02',groups={n.replace('r1_','r2_',1):v for n,v in plan['groups'].items()},
    caps={n.replace('r1_','r2_',1):v for n,v in plan['caps'].items()},run_order=[n.replace('r1_','r2_',1) for n in plan['run_order']],
    previous_plan_pin=pin((OUT/'admission.json').read_bytes()),preserved_failure_pin=pin((OUT/'r1_new_smoke.exit.json').read_bytes()),
    helper_pins={p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in OUT.glob('*.py')},
    collection_reused_for_identical_Source=True,fixture_built_without_production_import=True)
with (OUT/'admission_r2.json').open('xb') as stream:stream.write(raw(plan))
print(json.dumps(dict(source_epoch=plan['source_epoch'],fixture_roles=3,new_nodes=plan['new_nodes'],current_nodes=plan['current_nodes']),sort_keys=True))
