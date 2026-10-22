"""Verify the bound tolerance source and distinguish business/source anchors."""
import ast
from fractions import Fraction as Q
from hashlib import sha256
import json
from pathlib import Path

import yaml
from postcheck_v1 import number

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
root=HERE/'cost_01'
request=json.loads((root/'request.json').read_bytes())
protocol_path=REPO/'configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml'
protocol=yaml.safe_load(protocol_path.read_bytes())
boundary_path=REPO/'src/rq2_joint_deliverability_boundary_v1/boundary.py'
raw=boundary_path.read_bytes()
assert sha256(raw).hexdigest()==request['sources_sha256'][str(boundary_path)]
tree=ast.parse(raw.decode('utf-8'))
assignments=[node for node in tree.body if isinstance(node,ast.Assign)
    and any(isinstance(target,ast.Name) and target.id=='SERVICE_TOLERANCE' for target in node.targets)]
assert len(assignments)==1
tolerance=ast.literal_eval(assignments[0].value)
assert type(tolerance) is float and Q(str(tolerance))==Q(protocol['business_anchor']['service_tolerance'])
bindings={str(boundary_path):sha256(raw).hexdigest(),str(protocol_path):sha256(protocol_path.read_bytes()).hexdigest()}
for name in ('cfe_preallocation.py','capacity_policy_bidirectional.py'):
    path=boundary_path.with_name(name)
    source=path.read_bytes()
    assert sha256(source).hexdigest()==request['sources_sha256'][str(path)]
    assert any(isinstance(node,ast.ImportFrom) and node.module=='boundary'
               and any(alias.name=='SERVICE_TOLERANCE' for alias in node.names)
               for node in ast.parse(source.decode('utf-8')).body)
    bindings[str(path)]=sha256(source).hexdigest()
post=json.loads((HERE/'postcheck_v1.json').read_bytes())
parameters=post['actual_parameters']
audit=json.loads(Path(parameters['192']['full_carry_path']).read_bytes())
source_anchor=audit['cursor']['initial']['tracks'][0][1]['physical']['anchor']
assert source_anchor['split']=='training' and source_anchor['power_source_hour']==0
assert source_anchor['workload_source_hour']==0
for record in audit['cursor']['records']:
    assert number(record['current']['observation']['limits']['call_limit'])==Q(protocol['business_anchor']['call_limit'])
last=audit['history'][-1]['allocation']
def exact(value):return Q(int(value['numerator']),int(value['denominator']))
assert exact(last['renewable_share'])==1
assert exact(last['compatible_surplus'])==Q(1,2)
assert exact(last['effective_request'])==0
assert exact(last['workload'])==Q(1,2)
result=dict(status='DRAFT_NONAUTHORITATIVE',
    parameter_scope='finite_v2_business_anchor_parameter_overlay_on_synthetic_training_fixture',
    service_tolerance=float(tolerance),tolerance_evidence='single literal in exact request-bound boundary source and direct imports',
    historical_runtime_tolerance_value_separately_captured=False,
    actual_call_limit_checked_in_all_192_encoded_observations=True,
    actual_boundary_anchor=source_anchor,source_authenticated_boundary_anchor=False,
    h192_input_source_cfe_at_alpha_one='0',h192_renewable_share='1',
    h192_compatible_surplus='1/2',h192_effective_cfe_request='0',
    fresh_live_source_pins=1306,explicit_tested_byte_snapshots=14,
    owned_tree_rss_is_two_second_sample=True,logical_bytes_include_base_and_retained_copies=True,
    owner_event_size_or_complete_resource_bound=False,bindings=bindings,formal_result=False)
with (HERE/'parameter_overlay_verification_v1.json').open('x',encoding='utf-8') as stream:
    json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(dict(tolerance_source_bound=True,actual_call_limits=192,
    synthetic_source_anchor=True,h192_surplus='1/2')))
