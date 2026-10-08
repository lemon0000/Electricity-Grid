"""Zero-solver source preparation probe; never resumes a normal attempt."""
from argparse import ArgumentParser
from dataclasses import asdict, replace
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from experiments import audit_rq2_normal_task_v1 as audit

c = audit.controller
SCHEMA = 'rq2_normal_prepare_probe_v1'
LIMIT = 16384
STAGES = ('before_prepare', 'source_assembly_enter', 'source_assembly_return', 'source_binding_enter',
    'source_assembly_enter', 'source_assembly_return', 'source_binding_return', 'prepare_return')
TIMINGS = ('declaration_seconds', 'source_assembly_seconds', 'source_binding_seconds',
    'post_check_seconds', 'observed_total_seconds')


def failure_record(error, stage):
    frames, cursor = [], error.__traceback__
    while cursor is not None:
        code = cursor.tb_frame.f_code
        frames.append(dict(file=code.co_filename[-256:], function=code.co_name[:128], line=cursor.tb_lineno))
        if len(frames) > 8: del frames[0]
        cursor = cursor.tb_next
    return dict(schema=SCHEMA, status='preparation_exception', stage=stage,
        exception_type=type(error).__name__[:128], frames=frames, formal_result=False,
        normal_attempt_exception_identified=False)


def write(path, body):
    raw = c.journal._bytes(body)
    if len(raw) > LIMIT: raise ValueError('probe diagnostic byte limit exceeded')
    c.worker.codec._write_once(path, raw)


def read(path):
    identity = c.journal.local._file_identity(path)
    with path.open('rb') as stream: raw = stream.read(LIMIT+1)
    if len(raw) > LIMIT or c.journal.local._file_identity(path) != identity:
        raise ValueError('bounded diagnostic file required')
    return c.journal._decoded(raw)


def child_context(root, request, args):
    packet, intent, launch = (read(root/name) for name in ('probe.request.json', 'probe.intent.json', 'probe.launch.json'))
    info = root.stat()
    expected_intent = dict(schema=SCHEMA, process_identity=packet['process_identity'],
        request_sha256=sha256(c.journal._bytes(packet)).hexdigest(),
        status='zero_solver_preparation_intended', formal_result=False)
    expected_launch = dict(pid=os.getpid(), creation_filetime=c.worker._creation_filetime(),
        process_identity=packet['process_identity'], formal_result=False)
    if (intent != expected_intent or launch != expected_launch
            or packet['environment'] != dict(os.environ) or packet['argv'] != list(sys.orig_argv)
            or packet['root_identity'] != [info.st_dev, info.st_ino]
            or packet['source_request_identity'] != request.expected_source_request_identity
            or packet['declaration_sha256'] != args.expected_sha256
            or packet['script_sha256'] != args.expected_script_sha256):
        raise ValueError('diagnostic child differs from retained launch')


def summarize(root, request, pin, launch, observation):
    stages, failure, prepared, errors = [], None, None, []
    try:
        if (type(observation) is not c.process.TaskProcessObservation
                or observation.process_identity != pin or observation.pid != launch['pid']
                or observation.creation_filetime != launch['creation_filetime']
                or observation.whole_job_quiescent is not True
                or observation.job_commit_limits_configured is not True
                or any(getattr(observation, field) is not False for field in ('formal_result',
                    'hard_disk_quota_enforced', 'whole_task_resources_verified', 'numerical_evidence_verified'))):
            raise ValueError('diagnostic process observation mismatch')
        for index in range(17):
            path = root/('stage_%02d.json' % index)
            if not path.exists(): break
            if index == 16: raise ValueError('too many diagnostic stages')
            value = read(path)
            if (set(value) != {'schema', 'stage', 'pid', 'lifetime_peak_working_set_bytes', 'formal_result'}
                    or value['schema'] != SCHEMA or value['pid'] != launch['pid']
                    or type(value['pid']) is not int or value['formal_result'] is not False
                    or type(value['lifetime_peak_working_set_bytes']) is not int
                    or value['lifetime_peak_working_set_bytes'] <= 0
                    or value['stage'] not in ('before_prepare', 'source_assembly_enter', 'source_assembly_return',
                        'source_binding_enter', 'source_binding_return', 'prepare_return')):
                raise ValueError('diagnostic stage mismatch')
            stages.append(value)
        count = 0
        with os.scandir(root) as entries:
            for entry in entries:
                if entry.name.startswith('stage_') and entry.name.endswith('.json'):
                    count += 1
                    if count > 16: raise ValueError('too many diagnostic stage files')
        if count != len(stages) or tuple(value['stage'] for value in stages) != STAGES[:len(stages)]:
            raise ValueError('nonconsecutive diagnostic stages')
        if (root/'failure.json').exists():
            failure = read(root/'failure.json')
            if (set(failure) != {'schema', 'status', 'stage', 'exception_type', 'frames', 'formal_result',
                    'normal_attempt_exception_identified'} or failure['schema'] != SCHEMA
                    or failure['status'] != 'preparation_exception' or failure['formal_result'] is not False
                    or failure['normal_attempt_exception_identified'] is not False
                    or type(failure['exception_type']) is not str or len(failure['exception_type']) > 128
                    or type(failure['frames']) is not list or len(failure['frames']) > 8
                    or any(type(frame) is not dict or set(frame) != {'file', 'function', 'line'}
                        or type(frame['file']) is not str or type(frame['function']) is not str
                        or type(frame['line']) is not int for frame in failure['frames'])
                    or not stages or failure['stage'] != stages[-1]['stage']):
                raise ValueError('diagnostic failure record mismatch')
        if observation.reason != 'child_exited' or type(observation.exit_code) is not int or observation.exit_code != 0:
            errors.append('child_not_successful')
        else:
            prepared = read(root/'prepared.json')
            expected = dict(schema=SCHEMA, status='source_prepared', pid=launch['pid'],
                assembly_identity=request.source.expected_assembly_identity,
                input_identity=request.source.expected_input_identity,
                binding_identity=request.source.expected_binding_identity,
                source_request_identity=request.expected_source_request_identity,
                timings=prepared.get('timings'), solver_calls_by_preparation=0,
                formal_result=False, normal_attempt_exception_identified=False)
            if (c.journal._bytes(prepared) != c.journal._bytes(expected) or failure is not None
                    or (root/'failure_write_failed.json').exists() or not stages
                    or len(stages) != len(STAGES)
                    or type(prepared['timings']) is not dict or set(prepared['timings']) != set(TIMINGS)
                    or any(type(value) is not float or not math.isfinite(value) or value < 0
                        for value in prepared['timings'].values())):
                raise ValueError('missing or mismatched completed preparation')
    except Exception as error:
        errors.append(type(error).__name__)
    return dict(schema=SCHEMA, status='unresolved_probe' if errors else 'source_prepared',
        source_request_identity=request.expected_source_request_identity, process_identity=pin,
        observation_sha256=sha256(c.journal._bytes(asdict(observation))).hexdigest()
            if type(observation) is c.process.TaskProcessObservation else None,
        launch=launch, stages=stages, failure=failure, prepared=prepared, errors=errors,
        formal_result=False, normal_attempt_exception_identified=False)


def prepare_probe(root, request):
    """Instrument preparation only. All marker values are development claims."""
    stage, index = 'before_prepare', 0
    def mark(value):
        nonlocal stage, index
        if index >= 16: raise ValueError('diagnostic stage count exceeded')
        stage = value
        write(root/('stage_%02d.json' % index), dict(schema=SCHEMA, stage=stage,
            pid=os.getpid(), lifetime_peak_working_set_bytes=c.worker.kernel._peak_working_set_bytes(),
            formal_result=False))
        index += 1
    def forbidden(*args, **kwargs): raise AssertionError('solver forbidden in preparation probe')
    c.worker.kernel.native.create_solver = forbidden
    c.worker.kernel.run_normal_only = forbidden
    c.worker.journal.execution.run_source_normal = forbidden
    assembly = c.worker.inputs.source_normal.assemble_source_normal
    binding = c.worker.inputs.source.binding.bind_pair_normal
    def assemble(*args, **kwargs):
        mark('source_assembly_enter')
        result = assembly(*args, **kwargs)
        mark('source_assembly_return')
        return result
    def bind(*args, **kwargs):
        mark('source_binding_enter')
        result = binding(*args, **kwargs)
        mark('source_binding_return')
        return result
    c.worker.inputs.source_normal.assemble_source_normal = assemble
    c.worker.inputs.source.binding.bind_pair_normal = bind
    try:
        mark('before_prepare')
        result = c.worker.inputs.prepare_task_inputs(request.source,
            expected_request_identity=request.expected_source_request_identity)
        mark('prepare_return')
        write(root/'prepared.json', dict(schema=SCHEMA, status='source_prepared',
            pid=os.getpid(), input_identity=result.assembly.normal_identity,
            binding_identity=json.loads(result.binding_json)['binding_identity'],
            assembly_identity=result.assembly.assembly_identity, source_request_identity=result.request_identity,
            timings=dict(result.timings), solver_calls_by_preparation=result.solver_calls,
            formal_result=False, normal_attempt_exception_identified=False))
    except BaseException as error:
        try: write(root/'failure.json', failure_record(error, stage))
        except BaseException:
            # Separate best-effort marker; never overwrite a partial failure file.
            try:
                c.worker.codec._write_once(root/'failure_write_failed.json',
                    b'{"status":"diagnostic_write_failed","formal_result":false}')
            except BaseException: pass
        raise


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--declaration', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--expected-script-sha256', required=True)
    parser.add_argument('--expected-audit-script-sha256', required=True)
    parser.add_argument('--diagnostic-root', type=Path, required=True)
    parser.add_argument('--execute-development', action='store_true')
    parser.add_argument('--child', action='store_true', help='internal zero-solver probe branch')
    args = parser.parse_args()
    for pin in (args.expected_script_sha256, args.expected_audit_script_sha256): c.worker.kernel._pin(pin)
    if (sha256(Path(__file__).read_bytes()).hexdigest() != args.expected_script_sha256
            or sha256(Path(audit.__file__).read_bytes()).hexdigest() != args.expected_audit_script_sha256):
        raise ValueError('external diagnostic implementation identity mismatch')
    original, request, budget, environment, controller_pin = audit.read_declaration(args.declaration, args.expected_sha256)
    root = c.journal.local._path(args.diagnostic_root)
    if root == original or root.parent != original.parent or not root.name.endswith('_non_authoritative'):
        raise ValueError('separate development diagnostic root required')
    phase = replace(budget.execute, max_elapsed_seconds=120.-budget.execute.max_quiescence_seconds)
    if args.child:
        if not args.execute_development or Path.cwd() != root:
            raise ValueError('explicit diagnostic child context required')
        child_context(root, request, args)
        prepare_probe(root, request)
        return
    host = c._host(root.parent, budget, phase.max_job_commit_bytes+budget.controller_additional_commit_bytes,
        budget.scratch_bytes_per_phase)
    observed = c.resources.observe_headroom(host, expected_request_identity=c.resources.resource_identity(host))
    if not args.execute_development:
        print(json.dumps(asdict(observed), sort_keys=True))
        return
    if not observed.observed_headroom_sufficient: raise ValueError('insufficient diagnostic headroom')
    lease = object.__new__(c.journal.local._Lease)
    try:
        c.journal.local._Lease.__init__(lease, root, True)
        env = dict(environment, TEMP=str(root), TMP=str(root))
        host = c._host(root, budget, phase.max_job_commit_bytes, budget.scratch_bytes_per_phase)
        host_pin = c.resources.resource_identity(host)
        argv = [sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--declaration', str(args.declaration.resolve()),
            '--expected-sha256', args.expected_sha256, '--expected-script-sha256', args.expected_script_sha256,
            '--expected-audit-script-sha256', args.expected_audit_script_sha256,
            '--diagnostic-root', str(root), '--execute-development', '--child']
        arguments = dict(cwd=root, environment=env, budget=phase, host_budget=host, expected_host_identity=host_pin)
        pin = c.process.task_process_identity(argv, **arguments)
        write(root/'probe.request.json', dict(schema=SCHEMA, argv=argv, process_identity=pin,
            declaration_sha256=args.expected_sha256, script_sha256=args.expected_script_sha256,
            referenced_controller_identity=controller_pin, phase_budget=asdict(phase),
            source_request_identity=request.expected_source_request_identity, environment=env,
            root_identity=list(lease.root_identity),
            host_budget=asdict(host), host_identity=host_pin, formal_result=False))
        write(root/'probe.intent.json', dict(schema=SCHEMA, process_identity=pin,
            request_sha256=sha256((root/'probe.request.json').read_bytes()).hexdigest(),
            status='zero_solver_preparation_intended', formal_result=False))
        with c.process.normal_task_child(argv, expected_process_identity=pin, **arguments) as child:
            launch = dict(pid=child.pid, creation_filetime=child.creation_filetime, process_identity=pin, formal_result=False)
            write(root/'probe.launch.json', launch)
            child.release()
            result = child.wait()
            if result.whole_job_quiescent is not True:
                raise ValueError('diagnostic Job quiescence unconfirmed')
        write(root/'probe.observation.json', asdict(result))
        summary = summarize(root, request, pin, launch, result)
        write(root/'probe.summary.json', summary)
        print(json.dumps(summary, sort_keys=True))
    finally:
        if getattr(lease, 'stream', None) is not None: lease.close()


if __name__ == '__main__': main()
