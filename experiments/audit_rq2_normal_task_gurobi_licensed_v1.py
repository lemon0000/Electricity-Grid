"""Pinned H25 declaration for a five-second, non-authoritative normal task."""
from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

import yaml
from src.rq2_joint_deliverability_boundary_v1 import normal_task_controller_gurobi_licensed as controller


SCHEMA = 'rq2_gurobi_licensed_normal_task_development_declaration_v1'


def read_declaration(path, expected_sha256):
    controller.worker.kernel._pin(expected_sha256)
    raw = controller.worker.inputs._read_pinned(path, expected_sha256, controller.worker.PACKET_LIMIT)
    body = yaml.load(raw.decode('utf-8'), Loader=controller.worker.inputs.source.source_window.audit._UniqueKeyLoader)
    expected = {'schema', 'formal_result', 'declaration_role', 'task_root', 'request', 'budget',
        'environment', 'expected_controller_identity'}
    if (type(body) is not dict or set(body) != expected or body['schema'] != SCHEMA
            or body['formal_result'] is not False or body['declaration_role'] != 'development_execution_declaration'):
        raise ValueError('exact non-authoritative development declaration required')
    baseline_raw = controller.worker.inputs._read_pinned(
        ROOT/'configs/rq2_normal_task_gurobi_direct_h25_development_v1.DRAFT.yaml',
        'bd48dcdd47ac45ef3c667e1bbeada8626d923215b1f3e77e5e32d48199e37c08',
        controller.worker.PACKET_LIMIT)
    baseline = yaml.load(baseline_raw.decode('utf-8'),
        Loader=controller.worker.inputs.source.source_window.audit._UniqueKeyLoader)
    controller.worker.codec._environment(body['environment'])
    baseline['environment']['GRB_LICENSE_FILE'] = body['environment']['GRB_LICENSE_FILE']
    if (body['budget'] != baseline['budget'] or body['environment'] != baseline['environment']
            or controller.journal._bytes(body['request']) != controller.journal._bytes(baseline['request'])
            or body['task_root'] != str(Path(baseline['task_root']).parent/
                'rq2_normal_task_gurobi_licensed_h25_attempt1_non_authoritative')):
        raise ValueError('five-second successor must preserve pinned model and acceptance scope')
    request = controller.worker.decode_request(body['request'])
    worker = controller.worker
    pair_raw = worker.inputs._read_pinned(request.source.pair_declaration_path,
        request.source.expected_pair_declaration_sha256, request.source.max_pair_declaration_bytes)
    pair = worker.inputs.source.PairDeclaration(**yaml.load(pair_raw.decode('utf-8'),
        Loader=worker.inputs.source.source_window.audit._UniqueKeyLoader))
    normal_pin = worker.kernel.normal_execution_identity(request.source.expected_input_identity,
        request.source.expected_scale, request.specification, request.execution_budget)
    source_pin = worker.journal.execution.source.source_execution_identity(
        request.expected_binding_identity, normal_pin, pair,
        expected_assembly_identity=request.expected_assembly_identity,
        expected_pair_identity=request.source.expected_pair_identity,
        expected_source_implementation_identity=request.expected_source_implementation_identity,
        expected_binding_implementation_identity=request.expected_binding_implementation_identity)
    declared_pin = worker.journal.execution.declared_execution_identity(request.source,
        expected_request_identity=request.expected_source_request_identity,
        expected_source_execution_identity=source_pin)
    replay_pin = worker.replay.replay_identity(declared_pin, request.specification, request.execution_budget)
    if (request.expected_normal_execution_identity, request.expected_source_execution_identity,
            request.expected_declared_execution_identity, request.expected_replay_identity) != (
            normal_pin, source_pin, declared_pin, replay_pin):
        raise ValueError('derived normal/source/declared/replay identity chain mismatch')
    values = dict(body['budget'])
    values['execute'] = controller.process.TaskProcessBudget(**values['execute'])
    values['replay'] = controller.process.TaskProcessBudget(**values['replay'])
    values['capture'] = controller.capture.ArchiveCaptureBudget(**values['capture'])
    budget = controller.NormalTaskBudget(**values)
    if (request.source.expected_scale != controller.worker.kernel.Rq2ModelScale(22275, 28004)
            or request.specification.name != 'gurobi' or request.specification.expected_package_version != '13.0.2'
            or type(request.specification.time_limit_seconds) is not float
            or request.specification.time_limit_seconds != 5. or request.specification.threads != 1
            or request.execution_budget.max_seconds_per_solve != 5.
            or request.execution_budget.max_threads != 1 or request.execution_budget.max_horizon != 25
            or request.execution_budget.max_observed_wall_seconds != 60.
            or budget.max_total_elapsed_seconds > 600):
        raise ValueError('H25 single-thread five-second development scope required')
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
