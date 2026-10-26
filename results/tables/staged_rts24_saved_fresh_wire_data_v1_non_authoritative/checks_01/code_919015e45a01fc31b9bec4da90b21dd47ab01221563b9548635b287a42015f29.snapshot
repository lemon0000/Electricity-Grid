"""Syntax/old-definition/preservation snapshot only; never import or execute ENTRY."""
import ast
from hashlib import sha256
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
baseline=read(OUT/'baseline.json')
assert len(baseline['preserved'])==4333
assert all(pin((ROOT/n).read_bytes())==p for n,p in baseline['preserved'].items())
sources={n:pin((ROOT/n).read_bytes()) for n in baseline['sources']}
entry='experiments/staged_rts24_saved_fresh_adoption_v1.py'
assert {n for n,p in sources.items() if p!=baseline['sources'][n]}=={entry}
new_names=[]
for n,before in baseline['old_nodes'].items():
    data=(ROOT/n).read_bytes();tree=ast.parse(data,filename=n)
    after=[sha256(ast.dump(v,include_attributes=False).encode()).hexdigest() for v in tree.body]
    if n==entry:
        assert after[:len(before)-1]==before[:-1] and after[-1]==before[-1]
        new_names=[v.name for v in tree.body[len(before)-1:-1] if isinstance(v,(ast.FunctionDef,ast.ClassDef))]
    else:assert after==before
    compile(tree,n,'exec',dont_inherit=True)
snapshots={}
for n,p in sources.items():
    path=OUT/('code_'+p['sha256']+'.snapshot')
    if not path.exists():path=ROOT/baseline['source_snapshots'][n]
    assert pin(path.read_bytes())==p;snapshots[n]=path.relative_to(ROOT).as_posix()
missing=[n for n in ('validate_saved_controller_startup_join_data','validate_saved_parent_startup_join_data',
    'validate_saved_fresh_startup_join_data','validate_saved_stage_transcript_data','validate_saved_stage_failure_data',
    'validate_saved_wire_failure_data','compose_saved_failure_event_data','validate_saved_controller_binding_data',
    'validate_saved_controller_return_data','validate_saved_broker_return_data','validate_saved_constructor_diagnostic_data') if n not in new_names]
assert len(missing)==11
value=dict(authority='DRAFT_NONAUTHORITATIVE',status='SYNTAX_ONLY_WIP',source_pins=sources,
    source_epoch=sha256(raw(sources)).hexdigest(),source_snapshots=snapshots,preserved_paths=4333,
    old_definitions_AST_unchanged=True,scientific_adapter_unchanged=True,CLI_guard_unchanged=True,
    syntax_compiled_without_execution=True,production_module_imported=False,pytest_executed_nodes=0,
    ordinary_cold_probes=0,new_simulated_hours=0,new_symbols=new_names,required_missing_functions=missing,
    fixture_harness_admission_missing=True,connected_wire_pipeline_verified=False,
    upstream_completed_wire_contract_head='cdcc931c9fee0939ec004e2f6de4aa380f663f80',
    reused_frozen_test_nodes=480,current_executed_test_nodes=0,goal_status='active',
    actual_F=False,actual_fresh=False,final_parent_adoption=False,scientific_evidence_adopted=False,
    resource_admission=False,formal_result=False,run_authority=False,native_authorized=False)
data=raw(value);assert len(data)<=1024**2
with (OUT/'wip_snapshot.json').open('xb') as f:f.write(data)
print(json.dumps(dict(status='SYNTAX_ONLY_WIP',preserved_paths=4333,changed_source_paths=1,
    new_symbols=len(new_names),missing_functions=len(missing),pytest_executed_nodes=0,production_module_imported=False,actual_F=False),sort_keys=True))
