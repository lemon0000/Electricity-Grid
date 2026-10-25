"""Cross-check saved fields/census scope and freeze external dependency bytes."""
import ast
from common import ROOT,EXE,SOURCE_PATHS,pin,selected,read,save,snapshot

source=selected();tree=ast.parse((ROOT/SOURCE_PATHS[1]).read_bytes())
gates=next(n.value for n in tree.body if isinstance(n,ast.Assign)
    and any(isinstance(t,ast.Name) and t.id=='GATES' for t in n.targets))
assert isinstance(gates,ast.Call) and isinstance(gates.func,ast.Name) and gates.func.id=='dict'
gate_names=[k.arg for k in gates.keywords]
assert all(isinstance(k.value,ast.Constant) and k.value.value is False for k in gates.keywords)
validator=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_expectation_context')
keys_call=next(n.value for n in validator.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
    and isinstance(n.value.func,ast.Name) and n.value.func.id=='keys')
expression=keys_call.args[1]
assert isinstance(expression,ast.BinOp) and isinstance(expression.op,ast.Add) and isinstance(expression.left,ast.Constant)
assert isinstance(expression.right,ast.Call) and isinstance(expression.right.func,ast.Attribute)
assert expression.right.func.attr=='join' and isinstance(expression.right.func.value,ast.Constant)
assert expression.right.func.value.value==' ' and len(expression.right.args)==1
assert isinstance(expression.right.args[0],ast.Name) and expression.right.args[0].id=='GATES'
old_fields=set(expression.left.value.split()+gate_names)
spec=read('successor_context_spec.json');extra={'request_sha','broker_identity','runtime_binding_contract_sha','deadline_profile_sha'}
assert set(spec['fields'])==old_fields|extra and len(old_fields)==27 and len(spec['fields'])==31
v1=read('python_census.json');v2=read('python_census_v2.json')
def index(value): return {(r['source'],r['code_path']):r for r in value['code_objects']}
left,right=index(v1),index(v2)
assert len(left)==len(v1['code_objects']) and len(right)==len(v2['code_objects']) and set(left)==set(right)
mismatch=sum(left[k]['code_sha']!=right[k]['code_sha'] for k in left)
assert all({n:v for n,v in left[k].items() if n!='code_sha'}=={n:v for n,v in right[k].items() if n!='code_sha'} for k in left)
witness=read('global_binding_witness_v2.json')
assert witness['all_preregistered_acceptances_established'] is True and len(witness['cases'])==5
external=witness['external_source_pins']
assert set(external)=={str(EXE.parent/'Lib/site-packages/numpy/testing/_private/utils.py'),str(EXE.parent/'Lib/subprocess.py')}
runtime=read('runtime_pin_v2.json');external=dict(external,**{str(EXE):runtime['pin']})
images={}
for name,expected in external.items():
    path=__import__('pathlib').Path(name);assert pin(path.read_bytes())==expected
    images[name]=snapshot(path);assert images[name]['pin']==expected
save('external_source_snapshots.json',images)
save('mechanical_crosscheck.json',dict(authority='DRAFT_NONAUTHORITATIVE',legacy_expectation_fields=len(old_fields),
    successor_fields=31,added_fields=sorted(extra),code_object_keys_match=True,v1_code_sha_differences=mismatch,
    v1_metadata_except_code_sha_matches=True,v2_is_current_census=True,external_current_bytes_match_observation=True,
    external_snapshots=len(images),runtime_closure_proved=False,actual_saved_F_execution=False))
print(__import__('json').dumps(dict(legacy_fields=27,successor_fields=31,code_objects=len(right),
    v1_code_sha_differences=mismatch,external_source_snapshots=len(images),actual_saved_F_execution=False)))
