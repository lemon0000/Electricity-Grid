"""Zero-execution complete H1 inventory from retained, hash-bound shape evidence."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    output=args.output.resolve()
    if output.exists() or not output.parent.name.endswith('_non_authoritative'):
        raise ValueError('new non-authoritative output required')
    from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_resource_contract as api
    from src.rq2_joint_deliverability_boundary_v1.normal_h1_resource_shape import solver_calls_forbidden
    root=ROOT/'results/tables/rq2_normal_h1_shape_v1_non_authoritative'
    manifest=root/'development_checks.json'
    members=json.loads(manifest.read_bytes())['files']
    def verify():
        for name,pin in members.items():
            if sha256((ROOT/name).read_bytes()).hexdigest()!=pin:
                raise ValueError('retained shape member drift: '+name)
    verify()
    path=root/'scratch_non_authoritative/shape_result.json'
    if path.relative_to(ROOT).as_posix() not in members:
        raise ValueError('shape result not hash-bound')
    shape=json.loads(path.read_bytes())
    order=tuple(tuple(row) for row in shape['stage_order'])
    stages=api.validate_stage_order(order)
    if stages!=232 or shape['stage_count']!=stages or shape['solver_calls']!=0:
        raise ValueError('expected retained zero-solver RTS shape inventory')
    if (sum(kind=='commitment' for kind,_ in order)!=73
            or sum(kind=='generation' for kind,_ in order)!=158):
        raise ValueError('expected complete RTS UID inventory required')
    with solver_calls_forbidden():
        reports=[api.content_inventory(stages,hours) for hours in (1,192)]
        result=dict(schema='h1_full_normal_inventory_audit_v1',status='DRAFT_NONAUTHORITATIVE',
            shape_manifest_sha256=sha256(manifest.read_bytes()).hexdigest(),
            shape_result_sha256=sha256(path.read_bytes()).hexdigest(),
            preserved_shape_members=len(members),drift_count=0,stage_order=order,inventory=reports,
            implementation_identity=api.implementation_identity(),runner_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
            per_stage_time_limit_seconds=None,non_solver_seconds=None,archive_overhead_bytes=None,
            process_commit_bytes=None,job_commit_bytes=None,host_volume_binding=None,
            source_role='retained_single_origin_RTS_shape_probe',solver_calls=0,
            complete_resource_contract_present=False,physical_space_reserved=False,
            source_authenticated=False,selection_registered=False,execution_authorized=False,
            formal_result=False,formal_execution_ready=False,
            limitations=['Complete normal inventory only; no reference or actual work included.',
                'Content ceilings are not measured bytes or sufficient physical disk reservations.',
                'No future carry or per-stage native cost has been measured.'])
    verify()
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(path=str(output),sha256=sha256(output.read_bytes()).hexdigest(),inventory=reports)))


if __name__=='__main__':main()
