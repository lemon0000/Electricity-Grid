"""Bounded zero-solver H25 streaming source candidate probe."""
from argparse import ArgumentParser
from dataclasses import asdict, replace
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from experiments import diagnose_rq2_normal_prepare_v1 as prior
from src.rq2_joint_deliverability_boundary_v1 import source_normal_stream as source

c = prior.c
SCHEMA = 'rq2_stream_source_probe_v2'
write, read = prior.write, prior.read


def implementation_identity():
    return source.stream.digest(SCHEMA, source.implementation_identity(),
        tuple((Path(m.__file__).name, sha256(Path(m.__file__).read_bytes()).hexdigest())
            for m in (prior, prior.audit)), sha256(Path(__file__).read_bytes()).hexdigest())


def assemble(request, expected_implementation):
    """Decode pinned mechanism inputs, then build only the streaming source."""
    inputs = c.worker.inputs
    if inputs.task_source_identity(request.source) != request.expected_source_request_identity:
        raise ValueError('source declaration implementation drift')
    spec = request.source
    raw = inputs._read_pinned(spec.normal_record_path, spec.expected_normal_record_sha256,
        spec.max_normal_record_bytes)
    record = inputs._json(raw)
    if (type(record) is not dict or set(record) != inputs.BUILD_FIELDS or record['status'] != 'DRAFT_NONAUTHORITATIVE'
            or record['mode'] != 'verify' or record['formal_result'] is not False
            or record['external_assembly_identity_verified'] is not True
            or type(record['model_builds']) is not int or record['model_builds'] != 1
            or c.worker.kernel._digest(record['model_scale']) != c.worker.kernel._digest(asdict(spec.expected_scale))
            or type(record['solver_calls']) is not int or record['solver_calls'] != 0
            or record['normal_assignment_verified'] is not False
            or record['declaration_role'] != 'explicit_mechanism_input_not_executable_checkpoint'):
        raise ValueError('pinned build-only mechanism declaration required')
    for name, expected in (('normal_assembly_identity', spec.expected_assembly_identity),
            ('expected_assembly_identity', spec.expected_assembly_identity),
            ('normal_input_identity', spec.expected_input_identity), ('pair_identity', spec.expected_pair_identity),
            ('pair_declaration_sha256', spec.expected_pair_declaration_sha256)):
        if record[name] != expected: raise ValueError('mechanism declaration external pin mismatch')
    binding = dict(record['binding'])
    binding_pin = binding.pop('binding_identity')
    if binding_pin != spec.expected_binding_identity or inputs.source.source_window._hash(binding) != binding_pin:
        raise ValueError('mechanism binding body mismatch')
    power = record['binding']['power_binding']
    record['source_manifest_sha256'] = power['grid_source_manifest_sha256']
    normal, initial, carry = inputs.declaration_reader.declared_inputs(record, dict(
        split=power['split'], outage_seed=power['outage_seed'], chain={'chain_id': power['trajectory_id']}))
    result = source.assemble_source_normal(spec.upstream_root, tuple(power['raw_source_hours']),
        normal, initial, carry, source_time_basis=record['source_time_basis'],
        expected_implementation_identity=expected_implementation)
    if (result.normal_identity != spec.expected_input_identity
            or result.legacy_content_assembly_identity != spec.expected_assembly_identity
            or len(result.raw_source_hours) != 25):
        raise ValueError('streaming source differs from retained H25 content pins')
    if (inputs._read_pinned(spec.normal_record_path, spec.expected_normal_record_sha256,
            spec.max_normal_record_bytes) != raw
            or inputs.task_source_identity(spec) != request.expected_source_request_identity):
        raise ValueError('source declaration drift')
    return result


def child(root, request, pin, stream_pin):
    def forbidden(*args, **kwargs): raise AssertionError('solver forbidden in source probe')
    c.worker.kernel.native.create_solver = forbidden
    c.worker.kernel.run_normal_only = forbidden
    c.worker.journal.execution.run_source_normal = forbidden
    started = perf_counter()
    try:
        write(root/'started.json', dict(schema=SCHEMA, pid=os.getpid(), formal_result=False))
        result = assemble(request, stream_pin)
        if implementation_identity() != pin: raise ValueError('probe implementation drift')
        write(root/'source.json', dict(schema=SCHEMA, pid=os.getpid(),
            normal_identity=result.normal_identity,
            legacy_content_assembly_identity=result.legacy_content_assembly_identity,
            assembly_identity=result.assembly_identity, implementation_identity=result.implementation_identity,
            probe_implementation_identity=pin, source_manifest_sha256=result.source_manifest_sha256,
            raw_source_hours=list(result.raw_source_hours), source_hours=list(result.inputs.source_hours),
            annual_source_hours=len(result.inputs.data.hourly_points),
            elapsed_seconds=perf_counter()-started,
            lifetime_peak_working_set_bytes=c.worker.kernel._peak_working_set_bytes(),
            solver_calls=0, mechanism_initial_state=True, observed_power_mapping=False,
            formal_result=False, whole_task_resources_verified=False))
    except BaseException as error:
        try:
            failure = prior.failure_record(error, 'stream_source_assembly')
            failure['schema'] = SCHEMA
            write(root/'failure.json', failure)
        except BaseException:
            try: write(root/'failure_write_failed.json', dict(schema=SCHEMA, formal_result=False))
            except BaseException: pass
        raise


def validate_content(content, request, pin, stream_pin, pid):
    if type(content) is not dict: raise ValueError('source diagnostic object required')
    spec = request.source
    record = c.worker.inputs._json(c.worker.inputs._read_pinned(spec.normal_record_path,
        spec.expected_normal_record_sha256, spec.max_normal_record_bytes))
    power = record['binding']['power_binding']
    hours = power['raw_source_hours']
    if (type(hours) is not list or len(hours) != 25 or any(type(h) is not int or h < 0 for h in hours)
            or hours != list(range(hours[0], hours[0]+25))
            or power['grid_source_manifest_sha256'] != source.legacy.RTS_GMLC_MANIFEST_SHA256
            or source.stream.digest('draft_pinned_source_normal_assembly_v1',
                power['grid_source_manifest_sha256'], tuple(hours), spec.expected_input_identity,
                sha256(Path(source.legacy.__file__).read_bytes()).hexdigest()) != spec.expected_assembly_identity):
        raise ValueError('retained source metadata mismatch')
    assembly_pin = source.stream.digest(source.CONTRACT, power['grid_source_manifest_sha256'],
        tuple(hours), spec.expected_input_identity, spec.expected_assembly_identity, stream_pin)
    expected = dict(schema=SCHEMA, pid=pid, normal_identity=spec.expected_input_identity,
        legacy_content_assembly_identity=spec.expected_assembly_identity, assembly_identity=assembly_pin,
        implementation_identity=stream_pin, probe_implementation_identity=pin,
        source_manifest_sha256=power['grid_source_manifest_sha256'], raw_source_hours=hours,
        source_hours=[h+1 for h in hours], annual_source_hours=8784,
        elapsed_seconds=content.get('elapsed_seconds'),
        lifetime_peak_working_set_bytes=content.get('lifetime_peak_working_set_bytes'),
        solver_calls=0, mechanism_initial_state=True, observed_power_mapping=False,
        formal_result=False, whole_task_resources_verified=False)
    if (c.journal._bytes(content) != c.journal._bytes(expected)
            or type(content['elapsed_seconds']) is not float or not math.isfinite(content['elapsed_seconds'])
            or content['elapsed_seconds'] < 0
            or type(content['lifetime_peak_working_set_bytes']) is not int
            or content['lifetime_peak_working_set_bytes'] <= 0):
        raise ValueError('source diagnostic content mismatch')


def summarize(root, request, implementation, stream_pin, pin, launch, observation):
    content, failure, observation_digest, errors = None, None, None, []
    try:
        if type(observation) is c.process.TaskProcessObservation:
            observation_digest = sha256(c.journal._bytes(asdict(observation))).hexdigest()
        if (root/'failure.json').exists():
            failure = read(root/'failure.json')
            if (type(failure) is not dict or set(failure) != {'schema','status','stage','exception_type',
                    'frames','formal_result','normal_attempt_exception_identified'}
                    or failure['schema'] != SCHEMA or failure['status'] != 'preparation_exception'
                    or failure['stage'] != 'stream_source_assembly' or failure['formal_result'] is not False
                    or failure['normal_attempt_exception_identified'] is not False
                    or type(failure['exception_type']) is not str or len(failure['exception_type']) > 128
                    or type(failure['frames']) is not list or len(failure['frames']) > 8
                    or any(type(frame) is not dict or set(frame) != {'file','function','line'}
                        or type(frame['file']) is not str or len(frame['file']) > 256
                        or type(frame['function']) is not str or len(frame['function']) > 128
                        or type(frame['line']) is not int for frame in failure['frames'])):
                raise ValueError('source failure record mismatch')
        if not (type(observation) is c.process.TaskProcessObservation
                and observation.whole_job_quiescent is True and observation.reason == 'child_exited'
                and type(observation.exit_code) is int and observation.exit_code == 0
                and observation.process_identity == pin and observation.pid == launch['pid']
                and observation.creation_filetime == launch['creation_filetime']
                and observation.job_commit_limits_configured is True
                and type(observation.elapsed_seconds) is float and math.isfinite(observation.elapsed_seconds)
                and observation.elapsed_seconds >= 0
                and all(type(getattr(observation, field)) is int and getattr(observation, field) > 0
                    for field in ('runtime_samples', 'job_peak_process_commit_bytes',
                        'job_peak_total_commit_bytes', 'minimum_runtime_commit_available_bytes'))
                and observation.job_peak_total_commit_bytes >= observation.job_peak_process_commit_bytes
                and observation.last_resource_errors == () and observation.observation_error_type is None
                and all(getattr(observation, field) is False for field in ('formal_result',
                    'hard_disk_quota_enforced', 'whole_task_resources_verified', 'numerical_evidence_verified'))):
            raise ValueError('unsuccessful source process')
        content = read(root/'source.json')
        validate_content(content, request, implementation, stream_pin, launch['pid'])
        if failure is not None or (root/'failure_write_failed.json').exists():
            raise ValueError('source failure present')
    except Exception as error:
        errors.append(type(error).__name__)
    return dict(schema=SCHEMA, status='unresolved_probe' if errors else 'source_content_reproduced',
        observation_sha256=observation_digest,
        source_sha256=sha256(c.journal._bytes(content)).hexdigest() if content is not None else None,
        content=content, failure=failure, errors=errors, formal_result=False, whole_task_resources_verified=False)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--declaration', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--expected-implementation', required=True)
    parser.add_argument('--diagnostic-root', type=Path, required=True)
    parser.add_argument('--execute-development', action='store_true')
    parser.add_argument('--child', action='store_true')
    args = parser.parse_args()
    c.worker.kernel._pin(args.expected_implementation)
    if implementation_identity() != args.expected_implementation:
        raise ValueError('probe implementation drift')
    original, request, budget, environment, _ = prior.audit.read_declaration(args.declaration, args.expected_sha256)
    root = c.journal.local._path(args.diagnostic_root)
    if root == original or root.parent != original.parent or not root.name.endswith('_non_authoritative'):
        raise ValueError('separate development diagnostic root required')
    phase = replace(budget.execute, max_elapsed_seconds=120.-budget.execute.max_quiescence_seconds)
    stream_pin = source.implementation_identity()
    if args.child:
        packet, launch = read(root/'request.json'), read(root/'launch.json')
        expected_host = c._host(root, budget, phase.max_job_commit_bytes, budget.scratch_bytes_per_phase)
        expected_process = c.process.task_process_identity(list(sys.orig_argv), cwd=root,
            environment=dict(environment, TEMP=str(root), TMP=str(root)), budget=phase, host_budget=expected_host,
            expected_host_identity=c.resources.resource_identity(expected_host))
        expected_packet = dict(schema=SCHEMA, argv=list(sys.orig_argv), environment=dict(os.environ),
            implementation_identity=args.expected_implementation, stream_implementation_identity=stream_pin,
            source_request_identity=request.expected_source_request_identity, process_identity=expected_process,
            root_identity=[root.stat().st_dev, root.stat().st_ino], phase_budget=asdict(phase),
            host_budget=asdict(expected_host), declaration_sha256=args.expected_sha256, formal_result=False)
        if (not args.execute_development or Path.cwd() != root
                or c.journal._bytes(packet) != c.journal._bytes(expected_packet)
                or c.journal._bytes(launch) != c.journal._bytes(dict(pid=os.getpid(),
                    creation_filetime=c.worker._creation_filetime(), process_identity=expected_process, formal_result=False))):
            raise ValueError('source child differs from retained launch')
        child(root, request, args.expected_implementation, stream_pin)
        return
    host = c._host(root.parent, budget, phase.max_job_commit_bytes+budget.controller_additional_commit_bytes,
        budget.scratch_bytes_per_phase)
    headroom = c.resources.observe_headroom(host, expected_request_identity=c.resources.resource_identity(host))
    if not args.execute_development:
        print(json.dumps(asdict(headroom), sort_keys=True)); return
    if not headroom.observed_headroom_sufficient: raise ValueError('insufficient diagnostic headroom')
    lease = object.__new__(c.journal.local._Lease)
    try:
        c.journal.local._Lease.__init__(lease, root, True)
        env = dict(environment, TEMP=str(root), TMP=str(root))
        host = c._host(root, budget, phase.max_job_commit_bytes, budget.scratch_bytes_per_phase)
        argv = [sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--declaration', str(args.declaration.resolve()),
            '--expected-sha256', args.expected_sha256, '--expected-implementation', args.expected_implementation,
            '--diagnostic-root', str(root), '--execute-development', '--child']
        arguments = dict(cwd=root, environment=env, budget=phase, host_budget=host,
            expected_host_identity=c.resources.resource_identity(host))
        pin = c.process.task_process_identity(argv, **arguments)
        write(root/'request.json', dict(schema=SCHEMA, argv=argv, environment=env,
            implementation_identity=args.expected_implementation, stream_implementation_identity=stream_pin,
            source_request_identity=request.expected_source_request_identity, process_identity=pin,
            root_identity=list(lease.root_identity), phase_budget=asdict(phase),
            host_budget=asdict(host), declaration_sha256=args.expected_sha256, formal_result=False))
        with c.process.normal_task_child(argv, expected_process_identity=pin, **arguments) as process:
            launch = dict(pid=process.pid, creation_filetime=process.creation_filetime,
                process_identity=pin, formal_result=False)
            write(root/'launch.json', launch)
            process.release()
            observation = process.wait()
        write(root/'observation.json', asdict(observation))
        write(root/'summary.json', summarize(root, request, args.expected_implementation,
            stream_pin, pin, launch, observation))
        print(json.dumps(read(root/'summary.json'), sort_keys=True))
    finally:
        if getattr(lease, 'stream', None) is not None: lease.close()


if __name__ == '__main__': main()
