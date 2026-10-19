"""Create a mechanically versioned typed graph; authorization remains denied."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import re

H=Path(__file__).resolve().parent;R=H.parents[3];E=R/'experiments'
D=H/'whole_workflow_optimization_01_non_authoritative'
def n(stem,version):return 'h1_'+stem+'_development_v'+str(version)
rows=[]
def add(stem,old,new,*edges,extra=()):
    changes={n(stem,old):n(stem,new),**dict((n(s,a),n(s,b)) for s,a,b in edges),**dict(extra)}
    rows.append((n(stem,old),n(stem,new),changes))
add('group_n0_common_input_binding',2,11,('group_execution_roster',2,5))
add('common_owner_genesis',2,3,('group_n0_common_input_binding',2,11))
add('selector_input_snapshot',2,3,('common_owner_genesis',2,3))
add('selector_released_worker',2,3,('selector_input_snapshot',2,3))
add('selector_launch_preparation',2,3,('selector_released_worker',2,3))
add('selector_job_lifecycle',2,3,('selector_released_worker',2,3),
    extra=(('h1_selector_job_inspection_diagnostic_v2','h1_selector_job_inspection_diagnostic_v3'),))
add('selector_worker_output_inspection',2,3,('selector_released_worker',2,3),('selector_job_lifecycle',2,3))
add('selector_parent_controller',4,5,('selector_launch_preparation',2,3),
    ('selector_job_lifecycle',2,3),('selector_worker_output_inspection',2,3),extra=(('Parent4','Parent5'),))
add('selector_parent_validation_operation',4,5,('selector_phase_handoff',6,7))
add('selector_post_negative_validation',3,4,('selector_parent_controller',4,5),('selector_parent_validation_operation',4,5))
add('selector_phase_handoff',6,7,('selector_parent_controller',4,5),('common_owner_genesis',2,3),
    ('common_validation_operation',4,5),('selector_parent_validation_operation',4,5),
    extra=(('_development_genesis_external_finalize_v2','_development_genesis_external_finalize_v3'),))
add('common_genesis_validation_operation',2,3,('common_genesis_validation_routes',2,3),
    ('selector_input_snapshot',2,3),('selector_phase_handoff',6,7),('common_owner_genesis',2,3),
    extra=(('Gen2','Gen3'),('_development_genesis_external_finalize_v2','_development_genesis_external_finalize_v3')))
add('common_genesis_validation_routes',2,3,('operation_historical_witness',7,8),
    ('phase_exact_source_current',8,9),('group_n0_common_input_binding',7,9))
add('common_validation_operation',4,5,('selector_phase_handoff',6,7),('operation_historical_witness',6,9),
    ('phase_exact_source_current',7,10),('group_n0_common_input_binding',8,10))
add('operation_historical_witness',7,8,('common_genesis_validation_operation',2,3))
add('operation_historical_witness',6,9,('common_validation_operation',4,5))
add('phase_exact_source_current',8,9,('operation_historical_witness',7,8))
add('phase_exact_source_current',7,10,('operation_historical_witness',6,9))
rows.extend((n('group_n0_common_input_binding',version),n('group_n0_common_input_binding',version),changes)
    for version,changes in ((9,{n('phase_exact_source_current',8):n('phase_exact_source_current',9),
        n('operation_historical_witness',7):n('operation_historical_witness',8)}),
        (10,{n('phase_exact_source_current',7):n('phase_exact_source_current',10),
        n('operation_historical_witness',6):n('operation_historical_witness',9)})))
original={old:(E/(old+'.py')).read_bytes() for old,_,_ in rows}
for old,new,_ in rows:
    target=E/(new+'.py')
    if old!=new:assert not target.exists(),target
    else:assert target.read_bytes()==(D/'roster_scoped_source_202_non_authoritative'/target.name).read_bytes()
created={};observations=[]
for old,new,changes in rows:
    text=original[old].decode('utf-8')
    pattern=re.compile('|'.join(re.escape(key) for key in sorted(changes,key=len,reverse=True)))
    projected=pattern.sub(lambda match:changes[match[0]],text)
    ast.parse(projected);created[new]=projected
    observations.append(dict(source=str((E/(old+'.py')).relative_to(R)),
        target=str((E/(new+'.py')).relative_to(R)),before_sha256=sha256(original[old]).hexdigest(),
        namespace_schema_substitutions=changes,original_path_modified=old==new,
        mechanical_ast_projection_equal=True))
# Refresh literal route pins from the projected consumer bytes, in dependency
# order. Bridge source pins are subsequently fixed by the independent registry
# manifest when the authenticated route implementation is ready.
genesis_names=(n('operation_historical_witness',8),n('phase_exact_source_current',9),n('group_n0_common_input_binding',9))
handoff_names=(n('operation_historical_witness',9),n('phase_exact_source_current',10),n('group_n0_common_input_binding',10))
route_key=n('common_genesis_validation_routes',3)
route_value=tuple((name,sha256(created[name].encode('utf-8')).hexdigest()) for name in genesis_names)
created[route_key]=re.sub(r'^ROUTES = .*$',lambda _: 'ROUTES = '+repr(route_value),created[route_key],flags=re.M)
bridge_key=n('common_validation_operation',5)
bridge_value=tuple(('experiments.'+name,name+'.py',sha256(created[name].encode('utf-8')).hexdigest()) for name in handoff_names)
created[bridge_key]=re.sub(r'^_PINNED_ROUTES = .*$',lambda _: '_PINNED_ROUTES = '+repr(bridge_value),created[bridge_key],flags=re.M)
for row,(_,new,_) in zip(observations,rows,strict=True):
    target=E/(new+'.py');data=created[new].encode('utf-8');compile(data,str(target),'exec',dont_inherit=True)
    if row['original_path_modified']:target.write_bytes(data)
    else:
        with target.open('xb') as stream:stream.write(data)
    assert target.read_bytes()==data
    row['after_sha256']=sha256(data).hexdigest()
    row['additional_literal_route_pin_refresh']=new in (route_key,bridge_key)
    if row['additional_literal_route_pin_refresh']:
        row['mechanical_ast_projection_equal']=False
        row['scientific_bodies_namespace_substitution_only']=True
for old,new,_ in rows:
    if old!=new:assert (E/(old+'.py')).read_bytes()==original[old]
value=dict(schema='h1_common_typed_graph_origin_205',status='DRAFT_NONAUTHORITATIVE',
    root_sole_writer=True,scope='Twenty explicit source/schema/import successors; Common registry entry remains denied.',
    files=observations,new_files=18,existing_provisional_drafts_updated=2,
    common_authorized=False,loader_integration_tested=False,numerical_Roster_verified=False,
    new_N0_Jobs=0,real_native_calls=0,production_seal=False,official_review=False,
    full_optimized_workflow_accepted=False,whole_workflow_performance_review_complete=False,
    formal_execution_ready=False,formal_run_authority=False,formal_result=False,resource_admission=False)
out=D/'common_typed_graph_origin_205.json'
with out.open('x',encoding='utf-8',newline='\n') as stream:json.dump(value,stream,indent=2);stream.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha256(out.read_bytes()).hexdigest(),files=len(observations))))
