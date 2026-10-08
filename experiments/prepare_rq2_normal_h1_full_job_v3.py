"""Materialize a reviewable, non-executing single-hour calibration proposal."""
import argparse
from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_job_v3 as api


def prepare(output):
    shape_root = ROOT/'results/tables/rq2_normal_h1_shape_v1_non_authoritative'
    manifest = json.loads((shape_root/'development_checks.json').read_bytes())
    members = manifest['files']
    def verify():
        for name, pin in members.items():
            if sha256((ROOT/name).read_bytes()).hexdigest() != pin:
                raise ValueError('retained shape member drift: '+name)
    verify()
    previous = json.loads((shape_root/'request.json').read_bytes())
    shape = json.loads((shape_root/'scratch_non_authoritative/shape_result.json').read_bytes())
    stage_order = tuple(tuple(row) for row in shape['stage_order'])
    if len(stage_order) != 232 or shape['solver_calls'] != 0:
        raise ValueError('complete retained RTS stage inventory required')
    spec = api.Rq2SolverSpec('gurobi', '13.0.2', 1, 1e-8, 1e-9, 1e-9, 1e-9, 0, 5., False)
    work = api.collector.resources.H1NormalWork('h1_origin_calibration', 1, stage_order, spec)
    limits = api.collector.base.replay.H1HourReplayLimits(232, 891, 1211)
    mib, gib = 1024**2, 1024**3
    content = api.collector.resources.content_inventory(232, 1)['total_content_limit_bytes']
    envelope = api.collector.resources.serial.TaskEnvelope(work.task_id, 3600, 2440, 2*gib,
        content+256*mib, 256*mib, 1, limits.max_variables, limits.max_constraints)
    resource = api.collector.resources.H1TaskResources(envelope, 256*mib)
    serial = api.collector.resources.serial.SerialResourceBudget(3660, 60, 256*mib, 2*gib,
        4*gib+256*mib, 2*gib, envelope.archive_bytes+envelope.scratch_bytes+2*gib, 1)
    plan = api.collector.resources.check_plan((work,), (resource,), serial)
    job = api.process.DeclaredTaskProcessBudget(plan['declaration_identity'], envelope,
        3598., .25, 2*gib, 2*gib, 2.)
    request = dict(schema=api.SCHEMA, implementation_identity=api.implementation_identity(),
        work=asdict(work), resource=asdict(resource), serial_budget=asdict(serial), limits=asdict(limits),
        job_budget=asdict(job), source_declaration=previous['declaration'],
        source_identity=previous['expected_source_identity'], network_identity=previous['expected_network_identity'],
        upstream_root=previous['upstream_root'], config_path=previous['config_path'], dc_bus=previous['dc_bus'],
        root=str(ROOT/'results/tables/rq2_normal_h1_origin_calibration_v3_non_authoritative'))
    with api.collector.base.replay.guard.solver_calls_forbidden():
        api._validate_request(request)
        packet = api._packet(request)
        current = api.collector.resources.bind_current_hour(work, resource, packet, limits)
    verify()
    output = Path(output).resolve()
    if not output.parent.name.endswith('_non_authoritative'):
        raise ValueError('explicit non-authoritative output location required')
    output.parent.mkdir(parents=True, exist_ok=True)
    pin = api._write(output, request)
    record = dict(schema='h1_calibration_draft_preparation_v3', status='DRAFT_NONAUTHORITATIVE',
        request_sha256=pin, shape_manifest_sha256=sha256((shape_root/'development_checks.json').read_bytes()).hexdigest(),
        preserved_shape_members=len(members), source_identity=request['source_identity'],
        current_shape=current, resources=plan, solver_calls=0, native_calibration_started=False,
        production_sealed=False, formal_execution_ready=False, formal_result=False,
        limitations=['Resource allowances are proposals, not measured sufficiency or hard disk quota.',
            'CLI and public controller remain closed until sealed execution and review gates exist.',
            'No complete study inventory, common Rref/A publication or full-support LB/UB is supplied.'])
    api._write(output.with_name('calibration_preparation.json'), record)
    print(json.dumps(dict(request=str(output), sha256=pin, solver_calls=0,
        stages=232, task_wall_seconds=3600, content_limit_bytes=content)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    prepare(parser.parse_args().output)
