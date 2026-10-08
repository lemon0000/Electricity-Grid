"""Inspect a pinned H25 diagnostic; execute only with an explicit CLI action."""
from argparse import ArgumentParser
from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
import yaml
from src.rq2_joint_deliverability_boundary_v1 import scale_normal_controller as api
from src.rq2_joint_deliverability_boundary_v1 import normal_task_worker_gurobi_ordered as predecessor

SCHEMA='rq2_scale_normal_h25_diagnostic_v1'
OLD_PATH=ROOT/'configs/rq2_normal_task_gurobi_ordered_h25_development_v1.DRAFT.yaml'
OLD_PIN='688c2090f8e26c08b744fea7f61dfef38726d29ed69163727efa23575ccca03d'


def _read(path,pin):
    raw=api.worker.source.prepare._read_pinned(path,pin,api.base.LIMIT)
    return yaml.load(raw.decode('utf-8'),Loader=predecessor.inputs.source.source_window.audit._UniqueKeyLoader)


def read_declaration(path,pin):
    body=_read(path,pin)
    keys={'schema','scope','formal_result','episode_execution_allowed','task_root','request_path',
        'request_sha256','request_identity','allocation','environment','controller_identity'}
    if (type(body) is not dict or set(body)!=keys or body['schema']!=SCHEMA
            or body['scope']!='single_H25_normal_diagnostic_only' or body['formal_result'] is not False
            or body['episode_execution_allowed'] is not False):
        raise ValueError('exact normal-only diagnostic declaration required')
    old=_read(OLD_PATH,OLD_PIN)
    baseline=predecessor.decode_request(old['request'])
    request=api.worker.transport.read_request(Path(body['request_path']),
        expected_sha256=body['request_sha256'],max_request_bytes=api.worker.transport.LIMIT)
    if (type(request.resource_plan) is not api.worker.source.budgets.SingleNormalResourcePlan
            or request.source!=baseline.source
            or request.specification!=replace(baseline.specification,time_limit_seconds=600.)
            or request.budget.max_seconds_per_solve!=600
            or request.budget.max_horizon!=25
            or body['environment']!=old['environment']):
        raise ValueError('diagnostic must preserve old H25 source, numerical gates and environment')
    for name in ('expected_source_request_identity','expected_assembly_identity','expected_binding_identity',
                 'expected_source_implementation_identity','expected_binding_implementation_identity'):
        if getattr(request,name)!=getattr(baseline,name):
            raise ValueError('old H25 source linkage changed')
    values=dict(body['allocation'])
    for name in ('execute','audit'):
        fields=dict(values[name])
        fields['envelope']=api.worker.source.budgets.resources.TaskEnvelope(**fields['envelope'])
        values[name]=api.declared.DeclaredTaskProcessBudget(**fields)
    allocation=api.NormalPipelineBudget(**values)
    root=api.local._path(body['task_root'])
    if root!=ROOT/'results/tables/rq2_scale_normal_h25_600s_attempt1_non_authoritative':
        raise ValueError('dedicated new H25 diagnostic root required')
    if root.exists(): raise FileExistsError('H25 diagnostic is one-shot; existing root retained')
    request_pin=api.worker.source.request_identity(request)
    controller_pin=api.controller_identity(root,request,allocation=allocation,environment=body['environment'])
    if request_pin!=body['request_identity'] or controller_pin!=body['controller_identity']:
        raise ValueError('diagnostic request/controller identity changed')
    if (request.budget.max_observed_wall_seconds!=720.
            or request.budget.envelope.max_wall_seconds!=1500
            or allocation.execute.max_elapsed_seconds!=900.
            or allocation.audit.max_elapsed_seconds!=300.
            or allocation.controller_seconds!=180):
        raise ValueError('explicit reviewed H25 diagnostic timing required')
    return root,request,allocation,body['environment'],controller_pin


def verify_outer(path,declaration_pin,script_pin):
    if sha256(Path(__file__).read_bytes()).hexdigest()!=script_pin:
        raise ValueError('external diagnostic runner SHA mismatch')
    body=_read(path,declaration_pin)
    api.worker.source.prepare._read_pinned(Path(body['request_path']),body['request_sha256'],
        api.worker.transport.LIMIT)
    _read(OLD_PATH,OLD_PIN)


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--declaration',type=Path,required=True)
    parser.add_argument('--expected-sha256',required=True)
    parser.add_argument('--expected-script-sha256',required=True)
    parser.add_argument('--execute-development',action='store_true')
    args=parser.parse_args()
    if sha256(Path(__file__).read_bytes()).hexdigest()!=args.expected_script_sha256:
        raise ValueError('external diagnostic runner SHA mismatch')
    root,request,allocation,environment,pin=read_declaration(args.declaration,args.expected_sha256)
    verify_outer(args.declaration,args.expected_sha256,args.expected_script_sha256)
    if args.execute_development:
        report=api.supervise_normal(root,request,allocation=allocation,environment=environment,
            expected_controller_identity=pin)
    else:
        host=api.supervision._host(root.parent,request,allocation)
        observed=api.process.resources.observe_headroom(host,
            expected_request_identity=api.process.resources.resource_identity(host))
        report=dict(mode='read_only_diagnostic_inspection',request_identity=api.worker.source.request_identity(request),
            controller_identity=pin,target_exists=root.exists(),host_observation=asdict(observed),
            scheduled_solver_calls=1,episode_execution_allowed=False,formal_result=False,execution_authorized=False)
    # Inner controller evidence remains separate if this final outer check fails.
    # Complete every fallible outer check before publishing the CLI report.
    verify_outer(args.declaration,args.expected_sha256,args.expected_script_sha256)
    print(json.dumps(report,sort_keys=True,allow_nan=False),flush=True)


if __name__=='__main__': main()
