"""One H25 full-input identity comparison; no model build or solver."""
from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from experiments import audit_rq2_normal_task_gurobi_licensed_v1 as declaration
from src.rq2_joint_deliverability_boundary_v1 import identity_stream_ordered as fast, identity_stream_numeric as baseline

c = declaration.controller
CONFIG = ROOT/'configs/rq2_normal_task_gurobi_licensed_h25_development_v1.DRAFT.yaml'
CONFIG_SHA = '49d64f99823e3a7ed0620dba65cc6632d60f3c766e891ed99ea8c242d58cd694'
NUMERIC_SHA = '97afd233d5510cf12ab38f2c9cd654f2b28f822a87cf7ef2e2b17e29e18348e3'
INPUT_IDENTITY = 'd9959966c52fe618e73974fc53203ad2caed5169bd7f360fc79e0ecafd06780c'
TARGET = ROOT/'results/tables/rq2_identity_ordered_probe1_non_authoritative'
ORDER = ('numeric', 'ordered', 'ordered', 'numeric')


def solver_entrypoints():
    return ((c.worker.kernel.native.legacy, 'create_solver'), (c.worker.kernel.native, 'create_solver'),
        (c.worker.kernel, 'run_normal_only'), (c.worker.journal.execution, 'run_declared_normal'),
        (c.worker.journal.execution.source, 'run_source_normal'),
        (c.worker.kernel.streaming, 'build_continuous_normal_model'),
        (fast.legacy, 'build_continuous_normal_model'))


def guard_solver_calls():
    state = {'forbidden_calls': 0}
    def forbidden(*_args, **_kwargs):
        state['forbidden_calls'] += 1
        raise AssertionError('solver forbidden in identity comparison')
    for module, name in solver_entrypoints(): setattr(module, name, forbidden)
    return state


def execution_bindings(request):
    return dict(task_identity=c.worker.task_identity(request),
        numeric_encoder_sha256=sha256(Path(baseline.__file__).read_bytes()).hexdigest(),
        source_request_identity=c.worker.inputs.task_source_identity(request.source),
        model_implementation_identity=c.worker.kernel.streaming.implementation_identity(),
        preparation_sha256=sha256(Path(c.worker.inputs.__file__).read_bytes()).hexdigest(),
        normal_execution_identity=c.worker.kernel.normal_execution_identity(
            request.source.expected_input_identity, request.source.expected_scale,
            request.specification, request.execution_budget))


def check_bindings(request, expected):
    if execution_bindings(request) != expected:
        raise ValueError('preparation or model execution identity drift')


def validate_process(observation, pin, launch):
    if not (type(observation) is c.process.TaskProcessObservation
            and observation.process_identity == pin and observation.pid == launch['pid']
            and observation.creation_filetime == launch['creation_filetime']
            and observation.whole_job_quiescent is True
            and observation.job_commit_limits_configured is True
            and observation.reason == 'child_exited'
            and type(observation.exit_code) is int and observation.exit_code == 0
            and type(observation.elapsed_seconds) is float and math.isfinite(observation.elapsed_seconds)
            and observation.elapsed_seconds >= 0.
            and all(type(getattr(observation, k)) is int and getattr(observation, k) > 0
                for k in ('pid', 'creation_filetime', 'runtime_samples',
                    'job_peak_process_commit_bytes', 'job_peak_total_commit_bytes',
                    'minimum_runtime_commit_available_bytes'))
            and 0 < observation.job_peak_process_commit_bytes <= observation.job_peak_total_commit_bytes <= 768*1024**2
            and observation.last_resource_errors == () and observation.observation_error_type is None
            and all(getattr(observation, k) is False for k in ('formal_result',
                'hard_disk_quota_enforced', 'whole_task_resources_verified', 'numerical_evidence_verified'))):
        raise ValueError('unsuccessful bounded identity process')


def write(path, body):
    raw = json.dumps(body, sort_keys=True, allow_nan=False).encode()
    with path.open('xb') as f: f.write(raw)
    return sha256(raw).hexdigest()


def validate(body, input_identity, bindings):
    if type(body) is not dict or set(body) != {'schema', 'input_identity', 'expected_scale', 'observations',
            'solver_calls', 'formal_result', 'normal_accepted', 'preparation_seconds', 'model_builds', 'execution_bindings'}:
        raise ValueError('exact identity comparison required')
    if (body['schema'] != 'rq2_h25_identity_comparison_v1' or body['input_identity'] != input_identity
            or body['execution_bindings'] != bindings
            or body['expected_scale'] != {'variables': 22275, 'constraints': 28004}
            or any(type(v) is not int for v in body['expected_scale'].values())
            or type(body['solver_calls']) is not int or body['solver_calls'] != 0
            or type(body['model_builds']) is not int or body['model_builds'] != 0
            or body['formal_result'] is not False or body['normal_accepted'] is not False):
        raise ValueError('fixed build-only source and scope required')
    rows = body['observations']
    if type(rows) is not list or len(rows) != 4:
        raise ValueError('four ordered observations required')
    for row, method in zip(rows, ORDER, strict=True):
        if (type(row) is not dict or set(row) != {'method', 'input_identity', 'seconds'}
                or row['method'] != method or row['input_identity'] != INPUT_IDENTITY):
            raise ValueError('ordered byte-equivalent input identity required')
    for number in [body['preparation_seconds'], *(r['seconds'] for r in rows)]:
        if type(number) is not float or not math.isfinite(number) or number < 0.:
            raise ValueError('finite observed duration required')


def main():
    parser = ArgumentParser()
    parser.add_argument('--expected-script-sha256', required=True)
    parser.add_argument('--expected-helper-identity', required=True)
    parser.add_argument('--child', action='store_true')
    args = parser.parse_args()
    bound = None
    def check():
        if (sha256(Path(__file__).read_bytes()).hexdigest() != args.expected_script_sha256
                or fast.implementation_identity() != args.expected_helper_identity
                or sha256(Path(baseline.__file__).read_bytes()).hexdigest() != NUMERIC_SHA
                or sha256(Path(declaration.__file__).read_bytes()).hexdigest()
                    != '6e86dc80e92bf692a3a9a47e0aefc9f00d8378c456052512f92037905f22c683'):
            raise ValueError('external implementation pin mismatch')
        if bound is not None: check_bindings(request, bound)
    check()
    _, request, _, environment, _ = declaration.read_declaration(CONFIG, CONFIG_SHA)
    bound = execution_bindings(request)
    if args.child:
        guard = guard_solver_calls()
        check()
        started = perf_counter()
        prepared = c.worker.inputs.prepare_task_inputs(request.source,
            expected_request_identity=request.expected_source_request_identity)
        preparation_seconds = perf_counter()-started
        check()
        if prepared.solver_calls != 0 or prepared.normal_assignment_verified or prepared.formal_result:
            raise ValueError('build-only preparation required')
        rows = []
        for method in ORDER:
            check()
            started = perf_counter()
            digest = (fast.normal_input_identity if method == 'ordered' else baseline.normal_input_identity)(prepared.assembly.inputs)
            rows.append(dict(method=method, input_identity=digest, seconds=perf_counter()-started))
        body = dict(schema='rq2_h25_identity_comparison_v1', input_identity=prepared.assembly.normal_identity,
            expected_scale=asdict(request.source.expected_scale), observations=rows, solver_calls=0,
            formal_result=False, normal_accepted=False, preparation_seconds=preparation_seconds,
            model_builds=0, execution_bindings=bound)
        if guard['forbidden_calls'] != 0:
            raise ValueError('forbidden solver entry was attempted')
        validate(body, request.source.expected_input_identity, bound)
        check()
        write(TARGET/'comparison.json', body)
        return
    TARGET.mkdir(exist_ok=False)
    environment.update(TEMP=str(TARGET), TMP=str(TARGET))
    budget = c.process.TaskProcessBudget(120., .2, 768*1024**2, 768*1024**2, 3.)
    host = c.resources.HostResourceBudget(768*1024**2, 64*1024**2,
        (c.resources.DirectoryDemand('scratch', str(TARGET), 16*1024**2, 64*1024**2),))
    argv = [sys.executable, '-I', '-B', str(Path(__file__).resolve()),
        '--expected-script-sha256', args.expected_script_sha256,
        '--expected-helper-identity', args.expected_helper_identity, '--child']
    launch = dict(cwd=TARGET, environment=environment, budget=budget, host_budget=host,
        expected_host_identity=c.resources.resource_identity(host))
    pin = c.process.task_process_identity(argv, **launch)
    request_sha = write(TARGET/'request.json', dict(argv=argv, environment=environment,
        budget=asdict(budget), host_budget=asdict(host), process_identity=pin,
        config_sha256=CONFIG_SHA, script_sha256=args.expected_script_sha256,
        helper_identity=args.expected_helper_identity, execution_bindings=bound, formal_result=False))
    check()
    with c.process.normal_task_child(argv, **launch, expected_process_identity=pin) as owner:
        launched = dict(pid=owner.pid, creation_filetime=owner.creation_filetime)
        launch_sha = write(TARGET/'launch.json', launched)
        owner.release(); observation = owner.wait()
    process_sha = write(TARGET/'process.json', asdict(observation))
    validate_process(observation, pin, launched)
    check()
    raw = (TARGET/'comparison.json').read_bytes()
    body = json.loads(raw); validate(body, request.source.expected_input_identity, bound)
    check()
    write(TARGET/'summary.json', dict(request_sha256=request_sha, process_sha256=process_sha,
        comparison_sha256=sha256(raw).hexdigest(), comparison_bytes=len(raw), process_identity=pin,
        script_sha256=args.expected_script_sha256, helper_identity=args.expected_helper_identity,
        execution_bindings=bound, launch_sha256=launch_sha,
        solver_calls=0, formal_result=False, normal_accepted=False))
    print(json.dumps(body, sort_keys=True))
    print(json.dumps(asdict(observation), sort_keys=True))


if __name__ == '__main__': main()
