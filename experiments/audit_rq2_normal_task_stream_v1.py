"""Pinned H25 declaration for a one-second, non-authoritative normal task."""
from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

import yaml
from src.rq2_joint_deliverability_boundary_v1 import normal_task_controller_stream as controller


SCHEMA = 'rq2_streaming_normal_task_development_declaration_v1'


def read_declaration(path, expected_sha256):
    controller.worker.kernel._pin(expected_sha256)
    raw = controller.worker.inputs._read_pinned(path, expected_sha256, controller.worker.PACKET_LIMIT)
    body = yaml.load(raw.decode('utf-8'), Loader=controller.worker.inputs.source.source_window.audit._UniqueKeyLoader)
    expected = {'schema', 'formal_result', 'declaration_role', 'task_root', 'request', 'budget',
        'environment', 'expected_controller_identity'}
    if (type(body) is not dict or set(body) != expected or body['schema'] != SCHEMA
            or body['formal_result'] is not False or body['declaration_role'] != 'development_execution_declaration'):
        raise ValueError('exact non-authoritative development declaration required')
    request = controller.worker.decode_request(body['request'])
    values = dict(body['budget'])
    values['execute'] = controller.process.TaskProcessBudget(**values['execute'])
    values['replay'] = controller.process.TaskProcessBudget(**values['replay'])
    values['capture'] = controller.capture.ArchiveCaptureBudget(**values['capture'])
    budget = controller.NormalTaskBudget(**values)
    if (request.source.expected_scale != controller.worker.kernel.Rq2ModelScale(22275, 28004)
            or request.specification.name != 'highs' or request.specification.expected_package_version != '1.15.1'
            or type(request.specification.time_limit_seconds) is not float
            or request.specification.time_limit_seconds != 1. or request.specification.threads != 1
            or request.execution_budget.max_seconds_per_solve != 1.
            or request.execution_budget.max_threads != 1 or request.execution_budget.max_horizon != 25
            or request.execution_budget.max_observed_wall_seconds != 60.
            or budget.max_total_elapsed_seconds > 600):
        raise ValueError('H25 single-thread one-second development scope required')
    root = controller.journal.local._path(body['task_root'])
    pin = controller.controller_identity(root, request, budget, body['environment'])
    if pin != body['expected_controller_identity']:
        raise ValueError('retained controller identity differs from declaration')
    return root, request, budget, body['environment'], pin


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--declaration', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--expected-script-sha256', required=True)
    parser.add_argument('--execute-development', action='store_true')
    args = parser.parse_args()
    controller.worker.kernel._pin(args.expected_script_sha256)
    if sha256(Path(__file__).read_bytes()).hexdigest() != args.expected_script_sha256:
        raise ValueError('external development script identity mismatch')
    root, request, budget, environment, pin = read_declaration(args.declaration, args.expected_sha256)
    print(json.dumps(dict(schema='development_caller_metadata_v1', declaration_sha256=args.expected_sha256,
        script_sha256=args.expected_script_sha256, controller_identity=pin,
        source_request_identity=request.expected_source_request_identity, formal_result=False), sort_keys=True), flush=True)
    if not args.execute_development:
        host = controller._host(root.parent, budget,
            max(budget.execute.max_job_commit_bytes, budget.replay.max_job_commit_bytes)+budget.controller_additional_commit_bytes,
            budget.archive_disk_bytes+2*budget.scratch_bytes_per_phase)
        observation = controller.resources.observe_headroom(host,
            expected_request_identity=controller.resources.resource_identity(host))
        print(json.dumps(dict(mode='read_only_declaration_inspection', controller_identity=pin,
            target_exists=root.exists(), host_observation=asdict(observation), formal_result=False), sort_keys=True))
        return
    result = controller.supervise_normal_task(root, request, budget=budget, environment=environment,
        expected_controller_identity=pin)
    print(json.dumps(asdict(result), sort_keys=True))


if __name__ == '__main__': main()
