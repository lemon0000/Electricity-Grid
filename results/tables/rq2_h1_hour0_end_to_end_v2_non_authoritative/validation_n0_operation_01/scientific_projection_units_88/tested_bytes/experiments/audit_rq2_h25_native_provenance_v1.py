"""One-shot H25 native provenance diagnostic; not a formal experiment."""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import os
from math import isfinite
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.solvers import rq2_objective_provenance_run_v1 as run
from src.rq2_joint_deliverability_boundary_v1 import scale_normal_transport as transport
from src.rq2_joint_deliverability_boundary_v1 import normal_task_process as process
from src.rq2_joint_deliverability_boundary_v1 import scale_episode_controller as supervision

SOURCE_PACKET = ROOT/'configs/rq2_scale_normal_h25_600s_request_v1.DRAFT.json'
PACKET_PIN = 'da633e1120ed768ab1b6a8d1030338c328bd9f56e6cd2917e4305bdf48ac2ade'
STRUCTURE = 'e18f8f95846b33f4c358fe8d2a47082660ea19f161e317ca672ccd657e3f40f0'
OUTPUT = ROOT/'results/tables/rq2_h25_native_provenance_attempt1_non_authoritative'
LIMIT = 16*1024**2


def write_new(path, report):
    raw = report if type(report) is bytes else run.encode(report)
    if len(raw) > LIMIT:
        raise ValueError('bounded diagnostic file required')
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != raw:
        raise ValueError('diagnostic publication readback differs')
    return sha256(raw).hexdigest()


def check(expected_script, expected_runner):
    if sha256(Path(__file__).read_bytes()).hexdigest() != expected_script:
        raise ValueError('diagnostic script drift')
    if run.implementation_identity() != expected_runner:
        raise ValueError('diagnostic runner drift')
    request = transport.read_request(SOURCE_PACKET, expected_sha256=PACKET_PIN,
                                     max_request_bytes=transport.LIMIT)
    return request, transport.source.request_identity(request)


def worker(expected_script, expected_runner, expected_request):
    if {path.name for path in OUTPUT.iterdir()} != {'intent.json', 'launch.json', 'scratch'}:
        raise ValueError('fresh parent-owned diagnostic inventory required')
    intent = json.loads((OUTPUT/'intent.json').read_bytes())
    launch = json.loads((OUTPUT/'launch.json').read_bytes())
    if (launch['pid'] != os.getpid() or intent['script_sha256'] != expected_script
            or intent['runner_identity'] != expected_runner or intent['request_identity'] != expected_request):
        raise ValueError('parent launch/intent binding differs')
    request, identity = check(expected_script, expected_runner)
    if identity != expected_request:
        raise ValueError('source request identity drift')
    source = transport.source
    inputs, _ = source._prepare(request, identity)
    stream = source.kernel.streaming
    def builder():
        return stream.build_continuous_normal_model(inputs,
            expected_identity=request.source.expected_input_identity,
            expected_implementation_identity=stream.implementation_identity())
    raw = run.solve_once(builder, request.specification, expected_structure=STRUCTURE,
        max_variables=22275, max_constraints=28004, max_payload_bytes=LIMIT,
        expected_implementation=expected_runner)
    if check(expected_script, expected_runner)[1] != identity:
        raise ValueError('source drift after solve')
    report = dict(schema='rq2_h25_native_provenance_diagnostic_v1',
        source_request_sha256=PACKET_PIN, source_request_identity=identity,
        source_input_identity=request.source.expected_input_identity,
        script_sha256=expected_script, runner_identity=expected_runner,
        numerical=json.loads(raw), formal_result=False, normal_accepted=False)
    write_new(OUTPUT/'native_record.json', report)


def validate_record(report, request, identity, expected_script, expected_runner):
    expected = dict(schema='rq2_h25_native_provenance_diagnostic_v1',
        source_request_sha256=PACKET_PIN, source_request_identity=identity,
        source_input_identity=request.source.expected_input_identity,
        script_sha256=expected_script, runner_identity=expected_runner,
        formal_result=False, normal_accepted=False)
    if (set(report) != set(expected) | {'numerical'} or any(report[k] != v for k, v in expected.items())
            or report['formal_result'] is not False or report['normal_accepted'] is not False):
        raise ValueError('worker record source/schema mismatch')
    n = report['numerical']
    numeric_keys = {'schema', 'implementation_identity', 'model_structure_identity', 'solver_calls',
        'variables', 'constraints', 'solver_options', 'pyomo_status', 'pyomo_termination',
        'native_status', 'native_solution_count', 'provenance', 'assignment', 'maximum_residual',
        'maximum_integrality_violation', 'assignment_valid', 'formal_result', 'normal_accepted',
        'optimality_certified'}
    scale = request.source.expected_scale
    if type(n) is not dict or set(n) != numeric_keys:
        raise ValueError('worker numerical schema mismatch')
    if (n['schema'] != 'rq2_objective_provenance_owned_solve_v1'
            or n['implementation_identity'] != expected_runner or n['model_structure_identity'] != STRUCTURE
            or type(n['solver_calls']) is not int or n['solver_calls'] != 1
            or n['variables'] != scale.variables or n['constraints'] != scale.constraints
            or n['solver_options'] != run.audit.solver_options(request.specification)
            or any(n[k] is not False for k in ('formal_result', 'normal_accepted', 'optimality_certified'))):
        raise ValueError('worker numerical binding mismatch')
    if type(n['assignment_valid']) is not bool:
        raise ValueError('typed assignment validity required')
    p = n['provenance']
    if p is None:
        if n['assignment'] is not None or n['assignment_valid'] is not False:
            raise ValueError('missing incumbent cannot have accepted assignment')
        return
    provenance_keys = {'schema', 'adapter_identity', 'collector_sha256', 'native', 'native_status',
        'native_solution_count', 'native_model_sense', 'is_mip', 'pyomo_status', 'pyomo_termination',
        'pyomo_solution_status', 'optimal_status_channels_consistent', 'pyomo_lower_hex',
        'pyomo_upper_hex', 'pyomo_lower_source', 'canonical_objective_hex', 'exact_objective',
        'constant_hex', 'ordered_objective_terms', 'native_constant_hex', 'ordered_native_objective_terms',
        'native_exact_objective', 'native_exact_value_equals_canonical_exact_value',
        'canonical_objective_algebra', 'native_objective_algebra', 'native_algebra_equals_canonical_algebra',
        'referenced_assignment', 'assignment_sha256', 'comparisons', 'formal_result',
        'optimality_certified', 'native_execution_authenticated', 'solver_calls_by_collector'}
    if type(p) is not dict or set(p) != provenance_keys or set(p['native']) != {'ObjVal','ObjBound','ObjBoundC','Runtime'}:
        raise ValueError('worker provenance schema mismatch')
    if (p['schema'] != 'rq2_objective_provenance_v1'
            or p['collector_sha256'] != sha256(Path(run.provenance.__file__).read_bytes()).hexdigest()
            or p['adapter_identity'] != run.provenance.adapter.implementation_identity()
            or any(p[k] is not False for k in ('formal_result', 'optimality_certified', 'native_execution_authenticated'))
            or type(p['solver_calls_by_collector']) is not int or p['solver_calls_by_collector'] != 0
            or p['native_status'] != n['native_status'] or p['native_solution_count'] != n['native_solution_count']
            or p['pyomo_status'] != n['pyomo_status'] or p['pyomo_termination'] != n['pyomo_termination']
            or p['native_model_sense'] != 1 or p['is_mip'] is not True or p['pyomo_lower_source'] != 'ObjBound'):
        raise ValueError('worker direct provenance mismatch')
    for name in ('ObjVal', 'ObjBound', 'ObjBoundC', 'Runtime'):
        channel = p['native'][name]
        if channel['available'] is not True or not isfinite(float.fromhex(channel['hex'])):
            raise ValueError('H25 direct native channel missing')
    if len(n['assignment']) != scale.variables or len(dict(n['assignment'])) != scale.variables:
        raise ValueError('incomplete assignment inventory')
    for k in ('maximum_residual', 'maximum_integrality_violation'):
        if type(n[k]) not in (int, float) or not isfinite(n[k]) or n[k] < 0:
            raise ValueError('invalid residual evidence')
    if n['assignment_valid'] and (n['maximum_residual'] > request.specification.feasibility_tolerance
            or n['maximum_integrality_violation'] > request.specification.integer_feasibility_tolerance):
        raise ValueError('assignment flag inconsistent with residuals')


def retained(path):
    identity = process.resources.local._file_identity(path)
    with path.open('rb') as stream:
        raw = stream.read(LIMIT+1)
    if len(raw) > LIMIT or process.resources.local._file_identity(path) != identity:
        raise ValueError('bounded stable evidence required')
    return identity, sha256(raw).hexdigest(), raw


def validate_observation(observation, args, launch, process_identity):
    if type(observation) is not process.TaskProcessObservation:
        raise ValueError('typed process observation required')
    supervision._successful_observation(observation, args['budget'], args['host_budget'])
    if (observation.process_identity != process_identity or observation.pid != launch['pid']
            or observation.creation_filetime != launch['creation_filetime']):
        raise ValueError('worker process crosslink mismatch')


def supervise(root, argv, args, intent, validator, post_check):
    process_identity = process.task_process_identity(argv, **args)
    intent = dict(intent, process_identity=process_identity)
    write_new(root/'intent.json', intent)
    pins = {'intent.json': retained(root/'intent.json')}
    with process.normal_task_child(argv, **args, expected_process_identity=process_identity) as owner:
        launch = dict(pid=owner.pid, creation_filetime=owner.creation_filetime)
        write_new(root/'launch.json', launch)
        pins['launch.json'] = retained(root/'launch.json')
        owner.release()
        observation = owner.wait()
    write_new(root/'observation.json', asdict(observation))
    pins['observation.json'] = retained(root/'observation.json')
    validate_observation(observation, args, launch, process_identity)
    pins['native_record.json'] = retained(root/'native_record.json')
    report = json.loads(pins['native_record.json'][2])
    validator(report)
    post_check()
    for name, before in pins.items():
        if retained(root/name) != before:
            raise ValueError('retained evidence replaced or changed')
    summary = dict(schema='rq2_h25_native_provenance_observation_v1',
        file_sha256={name: item[1] for name, item in pins.items()},
        request_identity=intent['request_identity'], script_sha256=intent['script_sha256'],
        runner_identity=intent['runner_identity'], process_identity=process_identity,
        record_sha256=pins['native_record.json'][1], observation=asdict(observation),
        solver_calls=report['numerical']['solver_calls'],
        assignment_valid=report['numerical']['assignment_valid'],
        direct_provenance_observed=report['numerical']['provenance'] is not None,
        formal_result=False, normal_accepted=False, whole_task_resources_verified=False,
        independent_numerical_replay_completed=False)
    write_new(root/'result.json', summary)
    return summary


def execute(expected_script, expected_runner):
    request, identity = check(expected_script, expected_runner)
    OUTPUT.mkdir()  # Exclusive attempt reservation; never resume or overwrite.
    scratch = OUTPUT/'scratch'
    scratch.mkdir()
    environment = dict(os.environ, TEMP=str(scratch), TMP=str(scratch),
        OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    budget = process.TaskProcessBudget(900., 1., 1024**3, 1024**3, 3.)
    host = process.resources.HostResourceBudget(1280*1024**2, 256*1024**2, (
        process.resources.DirectoryDemand('scratch', str(scratch), 16*1024**2, 64*1024**2),
        process.resources.DirectoryDemand('archive', str(OUTPUT), 64*1024**2, 64*1024**2)))
    argv = [sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--worker',
        '--expected-script-sha256', expected_script, '--expected-runner-identity', expected_runner,
        '--expected-request-identity', identity]
    args = dict(cwd=scratch, environment=environment, budget=budget, host_budget=host,
        expected_host_identity=process.resources.resource_identity(host))
    intent = dict(schema='rq2_h25_native_provenance_intent_v1',
        script_sha256=expected_script, runner_identity=expected_runner,
        request_identity=identity, request_sha256=PACKET_PIN, budget=asdict(budget),
        host_budget=asdict(host),
        native_seconds=request.specification.time_limit_seconds, planned_solver_calls=1,
        max_payload_bytes=LIMIT, formal_result=False)
    def post_check():
        if check(expected_script, expected_runner)[1] != identity:
            raise ValueError('source drift after worker')
    return supervise(OUTPUT, argv, args, intent,
        lambda report: validate_record(report, request, identity, expected_script, expected_runner), post_check)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--execute-development', action='store_true')
    modes.add_argument('--worker', action='store_true')
    parser.add_argument('--expected-script-sha256', required=True)
    parser.add_argument('--expected-runner-identity', required=True)
    parser.add_argument('--expected-request-identity')
    args = parser.parse_args()
    if args.worker:
        try:
            worker(args.expected_script_sha256, args.expected_runner_identity, args.expected_request_identity)
        except BaseException as error:
            write_new(OUTPUT/'worker_failure.json', dict(error_type=type(error).__name__,
                solver_calls=None, call_count_complete=False, retry_allowed=False, formal_result=False))
            raise
    elif args.execute_development:
        print(json.dumps(execute(args.expected_script_sha256, args.expected_runner_identity)))
    else:
        _, identity = check(args.expected_script_sha256, args.expected_runner_identity)
        print(json.dumps(dict(mode='read_only', source_request_identity=identity,
            target_exists=OUTPUT.exists(), formal_result=False)))


if __name__ == '__main__':
    main()
